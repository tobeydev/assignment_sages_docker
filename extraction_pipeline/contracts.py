"""Reference Smart Contract Configuration for the Uniswap V3 WETH/USDC pool.

Pool: UniswapV3Pool (USDC/WETH, 0.05% fee tier) on Ethereum mainnet.
Etherscan: https://etherscan.io/address/0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640

This file exports simple constants so extraction code stays clean and readable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# ==============================================================================
# Pool Constants
# ==============================================================================

_POOL_MAINNET_DEFAULT = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"

# Checksummed form: what web3.py needs for w3.eth.contract(address=...)
POOL_ADDRESS = os.getenv("UNIV3_WETH_USDC_POOL", _POOL_MAINNET_DEFAULT)
# Lowercase form: what raw log["address"] values are compared against
POOL_ADDRESS_LOWER = POOL_ADDRESS.lower()

POOL_NAME = "Uniswap V3 USDC/WETH 0.05%"
POOL_FEE = 500  # fee tier in hundredths of a bip (500 = 0.05%)
POOL_TICK_SPACING = 10

# Approximate block the pool was created at. Use it as the floor for
# eth_getLogs ranges so you never scan blocks before the pool existed.
# Verify on Etherscan (contract creation tx) before relying on it.
POOL_DEPLOY_BLOCK = 12_376_729

# ==============================================================================
# Pool Tokens
# ==============================================================================
# Uniswap orders tokens by address: token0 is the lower address, so USDC is
# token0 and WETH is token1 in this pool. Always check this before reading
# amount0 / amount1 from a Swap event.

TOKEN0_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".lower()  # USDC
TOKEN0_SYMBOL = "USDC"
TOKEN0_DECIMALS = 6

TOKEN1_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2".lower()  # WETH
TOKEN1_SYMBOL = "WETH"
TOKEN1_DECIMALS = 18

# ==============================================================================
# Event Topics
# ==============================================================================

# keccak256("Swap(address,address,int256,int256,uint160,uint128,int24)")
SWAP_TOPIC0 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"

# ==============================================================================
# Minimal Pool ABI (Swap event + the view methods extraction needs)
# ==============================================================================
# Trimmed from the full UniswapV3Pool ABI. Swap field layout:
#   topics[1] = sender (indexed), topics[2] = recipient (indexed)
#   data      = amount0 (int256), amount1 (int256), sqrtPriceX96 (uint160),
#               liquidity (uint128), tick (int24)
# amount0 / amount1 are signed from the POOL's perspective:
#   positive = tokens the pool received (trader paid in)
#   negative = tokens the pool sent out (trader received)

UNIV3_POOL_MINIMAL_ABI = [
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
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [{"internalType": "uint24", "name": "", "type": "uint24"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "tickSpacing",
        "outputs": [{"internalType": "int24", "name": "", "type": "int24"}],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass(frozen=True)
class PoolConfig:
    name: str = POOL_NAME
    chain: str = "mainnet"
    address: str = POOL_ADDRESS
    fee: int = POOL_FEE
    tick_spacing: int = POOL_TICK_SPACING
    deploy_block: int = POOL_DEPLOY_BLOCK
    token0_symbol: str = TOKEN0_SYMBOL
    token0_address: str = TOKEN0_ADDRESS
    token0_decimals: int = TOKEN0_DECIMALS
    token1_symbol: str = TOKEN1_SYMBOL
    token1_address: str = TOKEN1_ADDRESS
    token1_decimals: int = TOKEN1_DECIMALS
    swap_topic0: str = SWAP_TOPIC0
    abi: list = field(default_factory=lambda: UNIV3_POOL_MINIMAL_ABI)


_POOLS = {
    ("weth-usdc", "mainnet"): PoolConfig(),
}


def get_pool(pair: str = "weth-usdc", chain: str | None = None) -> PoolConfig:
    """Return the PoolConfig for the requested pair, or raise if unsupported."""
    key = (pair.lower(), (chain or "mainnet").lower())
    try:
        return _POOLS[key]
    except KeyError:
        raise ValueError(f"Unsupported pool/chain: {key}") from None


# ==============================================================================
# Helpers
# ==============================================================================


def sqrt_price_x96_to_usdc_per_eth(sqrt_price_x96: int) -> float:
    """Convert a Swap event's sqrtPriceX96 into a human USDC-per-WETH price.

    Raw price p = (sqrtPriceX96 / 2**96) ** 2 is token1/token0 in raw units
    (WETH wei per USDC unit). Inverting and adjusting for decimals gives USDC per ETH.
    """
    raw = (sqrt_price_x96 / 2**96) ** 2
    return 10 ** (TOKEN1_DECIMALS - TOKEN0_DECIMALS) / raw