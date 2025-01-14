import json
import binascii
import os
from tools.utils import ExtrinsicBatch

GAS_LIMIT = 4294967
TX_SUCCESS_STATUS = 1


def generate_random_hex(num_bytes=16):
    return f'0x{binascii.b2a_hex(os.urandom(num_bytes)).decode()}'


def get_contract(w3, address, file_name):
    with open(file_name) as f:
        abi = json.load(f)

    return w3.eth.contract(address, abi=abi)


def call_eth_transfer_a_lot(substrate, kp_src, eth_src, eth_dst):
    batch = ExtrinsicBatch(substrate, kp_src)
    batch.compose_call(
        'EVM',
        'call',
        {
            'source': eth_src,
            'target': eth_dst,
            'input': '0x',
            'value': int('0xfffffffffffffffff', 16),
            'gas_limit': GAS_LIMIT,
            'max_fee_per_gas': int('0xffffff', 16),
            'max_priority_fee_per_gas': None,
            'nonce': None,
            'access_list': []
        })
    return batch.execute()


def get_eth_balance(substrate, eth_src):
    bl_num = substrate.get_block_number(None)
    return int(substrate.rpc_request("eth_getBalance", [eth_src, bl_num]).get('result'), 16)
