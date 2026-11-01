"""Swap extraction pipeline: Uniswap V3 pool Swap logs -> Postgres.

Usage:
    uv run --env-file .env swap_pipeline.py --from 20000000 --to 20000199

Environment variables (keep them in a .env file that is NOT committed):
    RPC_URL       Ethereum mainnet JSON-RPC endpoint (e.g. your Infura URL)
    DATABASE_URL  Postgres connection string,
                  e.g. postgresql://postgres:postgres@localhost:5432/swaps
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv
from web3 import Web3

# ==============================================================================
# Configuration
# ==============================================================================

POOLS = {
    "UNI/ETH": "0x1d42064Fc4Beb5F8aAF85F4617AE8b3b5B8Bd801",
    "ETH/USDC": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
    "WBTC/USDT": "0x56534741CD8B152df6d48AdF7ac51f75169A83b2",
}

DEFAULT_CHUNK_SIZE = 10  # blocks per eth_getLogs request

SWAP_SIGNATURE = "Swap(address,address,int256,int256,uint160,uint128,int24)"
SWAP_TOPIC0 = "0x" + bytes(Web3.keccak(text=SWAP_SIGNATURE)).hex()

# Swap event only: all Uniswap V3 pools share it.
SWAP_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "recipient", "type": "address"},
            {"indexed": False, "internalType": "int256", "name": "amount0", "type": "int256"},
            {"indexed": False, "internalType": "int256", "name": "amount1", "type": "int256"},
            {"indexed": False, "internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"indexed": False, "internalType": "uint128", "name": "liquidity", "type": "uint128"},
            {"indexed": False, "internalType": "int24", "name": "tick", "type": "int24"},
        ],
        "name": "Swap",
        "type": "event",
    },
]

# ==============================================================================
# SQL
# ==============================================================================
# NUMERIC(78,0) holds any uint256/int256 exactly. (BIGINT would overflow.)
# The primary key makes re-runs idempotent: (tx_hash, log_index) uniquely
# identifies a log on Ethereum.

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS swaps (
    pool_address  TEXT          NOT NULL,
    block_number  BIGINT        NOT NULL,
    tx_hash       TEXT          NOT NULL,
    log_index     INTEGER       NOT NULL,
    sender        TEXT          NOT NULL,
    recipient     TEXT          NOT NULL,
    amount0       NUMERIC(78,0) NOT NULL,
    amount1       NUMERIC(78,0) NOT NULL,
    sqrtPriceX96  NUMERIC(78,0) NOT NULL,
    liquidity     NUMERIC(78,0) NOT NULL,
    tick          INTEGER       NOT NULL,
    timestamp     TIMESTAMPTZ   NOT NULL,
    PRIMARY KEY (tx_hash, log_index)
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS swaps_pool_block_idx
    ON swaps (pool_address, block_number)
"""

INSERT_SQL = """
INSERT INTO swaps (
    pool_address, block_number, tx_hash, log_index, sender, recipient,
    amount0, amount1, sqrtPriceX96, liquidity, tick, timestamp
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (tx_hash, log_index) DO NOTHING
"""

COUNT_SQL = """
SELECT pool_address, COUNT(*)
FROM swaps
WHERE block_number BETWEEN %s AND %s
GROUP BY pool_address
"""

# ==============================================================================
# Helpers
# ==============================================================================


def with_retries(fn, *args, attempts: int = 5, **kwargs):
    """Call fn, retrying with exponential backoff on RPC/network errors."""
    for attempt in range(1, attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - RPC errors vary by provider
            if attempt == attempts:
                raise
            wait = 2**attempt
            print(f"    error: {exc} -> retry {attempt}/{attempts - 1} in {wait}s")
            time.sleep(wait)


def chunk_ranges(start: int, end: int, size: int):
    """Yield inclusive (lo, hi) block ranges of at most `size` blocks."""
    for lo in range(start, end + 1, size):
        yield lo, min(lo + size - 1, end)


def get_block_timestamp(w3: Web3, block_number: int, cache: dict) -> datetime:
    """Block timestamp as a UTC datetime, fetched once per block."""
    if block_number not in cache:
        block = with_retries(w3.eth.get_block, block_number)
        cache[block_number] = datetime.fromtimestamp(block["timestamp"], tz=timezone.utc)
    return cache[block_number]


def decode_swap(w3: Web3, event, log, ts_cache: dict) -> tuple:
    """Decode one raw log with the ABI and return a row tuple for INSERT_SQL."""
    decoded = event.process_log(log)
    args = decoded["args"]
    block_number = decoded["blockNumber"]
    return (
        decoded["address"],
        block_number,
        "0x" + bytes(decoded["transactionHash"]).hex(),
        decoded["logIndex"],
        args["sender"],
        args["recipient"],
        args["amount0"],
        args["amount1"],
        args["sqrtPriceX96"],
        args["liquidity"],
        args["tick"],
        get_block_timestamp(w3, block_number, ts_cache),
    )


# ==============================================================================
# Pipeline
# ==============================================================================


def extract_pool(w3: Web3, conn, name: str, address: str, start: int, end: int, chunk: int) -> int:
    """Fetch, decode and store all swaps for one pool. Returns swaps fetched."""
    address = Web3.to_checksum_address(address)
    event = w3.eth.contract(address=address, abi=SWAP_ABI).events.Swap()
    ts_cache: dict[int, datetime] = {}
    fetched = 0

    for lo, hi in chunk_ranges(start, end, chunk):
        logs = with_retries(
            w3.eth.get_logs,
            {
                "address": address,  # only this pool, never all contracts
                "topics": [SWAP_TOPIC0],
                "fromBlock": lo,
                "toBlock": hi,
            },
        )
        rows = [decode_swap(w3, event, log, ts_cache) for log in logs]
        if rows:
            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, rows)
        conn.commit()  # commit per chunk so a crash keeps earlier progress
        fetched += len(rows)
        print(f"  [{name}] blocks {lo}-{hi}: {len(rows)} swaps")

    return fetched


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Extract Uniswap V3 swaps into Postgres")
    parser.add_argument("--from", dest="from_block", type=int, required=True, help="first block (inclusive)")
    parser.add_argument("--to", dest="to_block", type=int, required=True, help="last block (inclusive)")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="blocks per getLogs request")
    args = parser.parse_args()

    if args.from_block > args.to_block:
        parser.error("--from must be <= --to")
    if args.chunk_size < 1:
        parser.error("--chunk-size must be >= 1")

    rpc_url = os.environ.get("RPC_URL")
    db_url = os.environ.get("DATABASE_URL")
    if not rpc_url or not db_url:
        sys.exit("Set RPC_URL and DATABASE_URL (e.g. in .env, run with: uv run --env-file .env ...)")

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        sys.exit("Could not connect to the RPC endpoint")

    print(f"Extracting blocks {args.from_block}-{args.to_block} ({args.chunk_size} blocks/request)")

    with psycopg.connect(db_url) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(CREATE_INDEX_SQL)
        conn.commit()

        for name, address in POOLS.items():
            print(f"{name} ({address})")
            extract_pool(w3, conn, name, address, args.from_block, args.to_block, args.chunk_size)

        # Row counts per pool in Postgres for this range (useful for the submission note)
        with conn.cursor() as cur:
            cur.execute(COUNT_SQL, (args.from_block, args.to_block))
            counts = dict(cur.fetchall())

    print(f"\nRow counts in Postgres for blocks {args.from_block}-{args.to_block}:")
    for name, address in POOLS.items():
        print(f"  {name:<10} {address}  {counts.get(Web3.to_checksum_address(address), 0)}")


if __name__ == "__main__":
    main()