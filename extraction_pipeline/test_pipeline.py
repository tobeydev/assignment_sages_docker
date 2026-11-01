# connecting our Rpc

import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()
RPC_URL = os.environ.get("RPC_URL")

connect = Web3(Web3.HTTPProvider(RPC_URL))
#print(connect.is_connected()) # Used to check if the connection is established.


sig = 'Swap(address,address,int256,int256,uint160,uint128,int24)'


topic0 = Web3.keccak(text=sig).hex()


from_block = 26314971
to_block = 26314976

# Query the RPC node for Swap logs within a block window
logs = connect.eth.get_logs({
    "fromBlock": from_block,
    "toBlock": to_block,
    "topics": ['0x'+topic0],  
})

print(len(logs))

pool_address = '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640'
abi = [ {
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
        "type": "event"
  },]

print(logs)
contract = connect.eth.contract(address=pool_address,abi=abi)
print(contract.address)
events = contract.events.Swap()
print(events)

decoded = events.process_log(logs[0])

print(decoded)