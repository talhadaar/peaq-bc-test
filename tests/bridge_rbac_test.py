from substrateinterface import SubstrateInterface, Keypair, KeypairType
from tools.utils import transfer, calculate_evm_account, calculate_evm_addr, calculate_evm_account_hex
from tools.utils import WS_URL, ETH_URL, get_eth_chain_id
from tools.peaq_eth_utils import call_eth_transfer_a_lot, get_contract, generate_random_hex
from tools.peaq_eth_utils import TX_SUCCESS_STATUS
from web3 import Web3

import unittest


import pprint
pp = pprint.PrettyPrinter(indent=4)
GAS_LIMIT = 4294967


# Keypair to use for dispatches
KP_SRC = Keypair.create_from_uri('//Alice')
# Address of RBAC precompile contract
RBAC_ADDRESS = '0x0000000000000000000000000000000000000802'
# H160 Address to use for EVM transactions
ETH_PRIVATE_KEY = '0xa2899b053679427c8c446dc990c8990c75052fd3009e563c6a613d982d6842fe'
# RBAC Precompile ABI
ABI_FILE = 'ETH/rbac/rbac.sol.json'
# Number of tokens with decimals
TOKEN_NUM = 10000 * pow(10, 15)

# A role and it's name
ROLE_ID_1 = generate_random_hex(15).encode("utf-8")
ROLE_ID_1_NAME = generate_random_hex(15).encode("utf-8")


def _calcualte_evm_basic_req(substrate, w3, addr):
    return {
        'from': addr,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': w3.eth.get_transaction_count(addr),
        'chainId': get_eth_chain_id(substrate)
    }


def _eth_add_role(substrate, w3, contract, eth_kp_src, role_id, name):
    tx = contract.functions.add_role(role_id, name).build_transaction(
        _calcualte_evm_basic_req(substrate, w3, eth_kp_src.ss58_address)
    )

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt


def _eth_fetch_role(substrate, w3, contract, eth_kp_src, owner, role):
    tx = contract.functions.fetch_role(owner, role).build_transaction(
        _calcualte_evm_basic_req(substrate, w3, eth_kp_src.ss58_address)
    )

    signed_txn = w3.eth.account.sign_transaction(tx, private_key=eth_kp_src.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt


class TestBridgeRbac(unittest.TestCase):

    def setUp(self):
        self._eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._substrate = SubstrateInterface(url=WS_URL)
        self._eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        self._account = calculate_evm_account_hex(self._eth_kp_src.ss58_address)

    def check_item_from_event(self, event, account, role_id, name):
        events = event.get_all_entries()
        self.assertEqual(f"0x{events[0]['args']['owner'].hex()}", account)
        self.assertEqual(f"0x{events[0]['args']['role_id'].hex()}", f"{role_id}")
        self.assertEqual(f"0x{events[0]['args']['name'].hex()}", f"{name}")

    def test_add_role_and_check(self):
        print("ROLE_ID ", ROLE_ID_1, "len: ", len(ROLE_ID_1))

        substrate = self._substrate
        eth_src = self._eth_src
        w3 = self._w3
        eth_kp_src = self._eth_kp_src
        account = self._account

        # Setup eth_ko_src with some tokens
        transfer(substrate, KP_SRC, calculate_evm_account(eth_src), TOKEN_NUM)
        bl_hash = call_eth_transfer_a_lot(substrate, KP_SRC, eth_src, eth_kp_src.ss58_address.lower())
        # verify tokens have been transferred
        self.assertTrue(bl_hash, f'Failed to transfer token to {eth_kp_src.ss58_address}')

        # populate contract interface
        contract = get_contract(w3, RBAC_ADDRESS, ABI_FILE)

        # Execute: Add Role
        tx_receipt = _eth_add_role(substrate, w3, contract, eth_kp_src, ROLE_ID_1, ROLE_ID_1_NAME)
        self.assertEqual(tx_receipt['status'], TX_SUCCESS_STATUS)
        block_idx = tx_receipt['blockNumber']

        # Check: Add Role
        event = contract.events.RoleAdded.create_filter(fromBlock=block_idx, toBlock=block_idx)
        self.check_item_from_event(event, account, ROLE_ID_1, ROLE_ID_1_NAME)

        # Execute: Fetch Role
        data = contract.functions.fetch_role(account, ROLE_ID_1).call()

        # Check: Fetch Role
        self.assertEqual(f'0x{data.hex()}', ROLE_ID_1_NAME)