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


# generates list of `length` random utf-8 encoded hex strings of length 15
def generate_random_hex_list(strlen, listlen):
    return [generate_random_hex(strlen).encode("utf-8") for i in range(listlen)]


# returns list of utf-8 encoded hex strings from a list of strings
def str_to_utf8_encoded_list(strlist):
    return list(map(lambda name: name.encode("utf-8"), strlist))


##############################################################################
# Constants for global test-setup defaults
##############################################################################

USER_IDS = generate_random_hex_list(15, 5)

PERMISSION_IDS = generate_random_hex_list(15, 5)
PERMISSION_ID_NAMES = str_to_utf8_encoded_list(["PERMISSION1", "PERMISSION2", "PERMISSION3", "PERMISSION4", "PERMISSION5"])

ROLE_IDS = generate_random_hex_list(15, 5)
ROLE_ID_NAMES = str_to_utf8_encoded_list(["ROLE1", "ROLE2", "ROLE3", "ROLE4", "ROLE5"])

GROUP_IDS = generate_random_hex_list(15, 5)
GROUP_ID_NAMES = str_to_utf8_encoded_list(["GROUP1", "GROUP2", "GROUP3", "GROUP4", "GROUP5"])


##############################################################################
# Helper functions for submitting transactions
##############################################################################

def _calcualte_evm_basic_req(substrate, w3, addr):
    return {
        'from': addr,
        'gas': GAS_LIMIT,
        'maxFeePerGas': w3.to_wei(250, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
        'nonce': w3.eth.get_transaction_count(addr),
        'chainId': get_eth_chain_id(substrate)
    }


def _sign_and_submit_transaction(tx, w3, signer):
    signed_txn = w3.eth.account.sign_transaction(tx, private_key=signer.private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)


class TestBridgeRbac(unittest.TestCase):

    ##############################################################################
    # Wrapper functions for state chainging extrinsics
    ##############################################################################

    def _eth_add_role(self, role_id, name):
        tx = self._contract.functions.add_role(role_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _eth_update_role(self, role_id, name):
        tx = self._contract.functions.update_role(role_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _eth_disable_role(self, role_id):
        tx = self._contract.functions.disable_role(role_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_role_to_user(self, role_id, user_id):
        tx = self._contract.functions.assign_role_to_user(role_id, user_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_role_to_user(self, role_id, user_id):
        tx = self._contract.functions.unassign_role_to_user(role_id, user_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _add_permission(self, permission_id, name):
        tx = self._contract.functions.add_permission(permission_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _update_permission(self, permission_id, name):
        tx = self._contract.functions.update_permission(permission_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _disable_permission(self, permission_id):
        tx = self._contract.functions.disable_permission(permission_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_permission_to_role(self, permission_id, role_id):
        tx = self._contract.functions.assign_permission_to_role(permission_id, role_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_permission_to_role(self, permission_id, role_id):
        tx = self._contract.functions.unassign_permission_to_role(permission_id, role_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _add_group(self, group_id, name):
        tx = self._contract.functions.add_group(group_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _update_group(self, group_id, name):
        tx = self._contract.functions.update_group(group_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _disable_group(self, group_id):
        tx = self._contract.functions.disable_group(group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_role_to_group(self, role_id, group_id):
        tx = self._contract.functions.assign_role_to_group(role_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_role_to_group(self, role_id, group_id):
        tx = self._contract.functions.unassign_role_to_group(role_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _assign_user_to_group(self, user_id, group_id):
        tx = self._contract.functions.assign_user_to_group(user_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _unassign_user_to_group(self, user_id, group_id):
        tx = self._contract.functions.unassign_user_to_group(user_id, group_id).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def check_item_from_event(self, event, account, role_id, name):
        events = event.get_all_entries()
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)
        self.assertEqual(events[0]['args']['name'], name)

    def setUp(self):
        self._eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._substrate = SubstrateInterface(url=WS_URL)
        self._eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        self._account = calculate_evm_account_hex(self._eth_kp_src.ss58_address)
        self._contract = get_contract(self._w3, RBAC_ADDRESS, ABI_FILE)

    def test_add_role_and_check(self):

        # Setup eth_ko_src with some tokens
        transfer(self._substrate, KP_SRC, calculate_evm_account(self._eth_src), TOKEN_NUM)
        bl_hash = call_eth_transfer_a_lot(self._substrate, KP_SRC, self._eth_src, self._eth_kp_src.ss58_address.lower())

        # verify tokens have been transferred
        self.assertTrue(bl_hash, f'Failed to transfer token to {self._eth_kp_src.ss58_address}')

        # populate contract interface
        contract = get_contract(self._w3, RBAC_ADDRESS, ABI_FILE)

        # Execute: Add Role
        tx_receipt = self._eth_add_role(ROLE_IDS[0], ROLE_ID_NAMES[0])
        self.assertEqual(tx_receipt['status'], TX_SUCCESS_STATUS)
        block_idx = tx_receipt['blockNumber']

        # Check: Add Role
        event = contract.events.RoleAdded.create_filter(fromBlock=block_idx, toBlock=block_idx)
        self.check_item_from_event(event, self._eth_kp_src.ss58_address, ROLE_IDS[0], ROLE_ID_NAMES[0])

        # Execute: Fetch Role
        data = contract.functions.fetch_role(self._account, ROLE_IDS[0]).call()

        # Check: Fetch Role
        self.assertEqual(data[1], ROLE_ID_NAMES[0])
