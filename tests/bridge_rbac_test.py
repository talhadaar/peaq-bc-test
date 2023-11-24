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


def generate_random_id():
    return generate_random_hex(15).encode("utf-8")


# generates a tuple of (id, name) for a role, permission, or group
def generate_random_tuple():
    id = generate_random_id()
    name = f'NAME{id[:4]}'.encode("utf-8")
    return (id, name)


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

# NOTE: fetch_user_roles will return an error if the user has no roles
class TestBridgeRbac(unittest.TestCase):

    ##############################################################################
    # Wrapper functions for state chainging extrinsics
    ##############################################################################

    def _add_role(self, role_id, name):
        tx = self._contract.functions.add_role(role_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _update_role(self, role_id, name):
        tx = self._contract.functions.update_role(role_id, name).build_transaction(
            _calcualte_evm_basic_req(self._substrate, self._w3, self._eth_kp_src.ss58_address)
        )
        return _sign_and_submit_transaction(tx, self._w3, self._eth_kp_src)

    def _disable_role(self, role_id):
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

    ##############################################################################
    # Functions that verify events
    ##############################################################################

    # verify add/update role
    def _verify_role_add_update_event(self, events, account, role_id, name):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)
        self.assertEqual(events[0]['args']['name'], name)

    def _verify_role_disabled_event(self, events, account, role_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)

    # verify assign/unassign role to user
    def _verify_role_assign_or_unassign_event(self, events, account, role_id, user_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)
        self.assertEqual(events[0]['args']['user_id'], user_id)

    def _verify_permission_add_or_update_event(self, events, account, permission_id, name):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['permission_id'], permission_id)
        self.assertEqual(events[0]['args']['name'], name)

    def _verify_permission_disabled_event(self, events, account, permission_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['permission_id'], permission_id)

    def _verify_permission_assigned_or_unassigned_to_role_event(self, events, account, permission_id, role_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['permission_id'], permission_id)
        self.assertEqual(events[0]['args']['role_id'], role_id)

    def _verify_group_add_or_update_event(self, events, account, group_id, name):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['group_id'], group_id)
        self.assertEqual(events[0]['args']['name'], name)

    def _verify_group_disabled_event(self, events, account, group_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['group_id'], group_id)

    def _verify_role_assigned_or_unassigned_to_group_event(self, events, account, role_id, group_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['role_id'], role_id)
        self.assertEqual(events[0]['args']['group_id'], group_id)

    def _verify_user_assigned_or_unassigned_to_group_event(self, events, account, user_id, group_id):
        self.assertEqual(events[0]['args']['sender'], account)
        self.assertEqual(events[0]['args']['user_id'], user_id)
        self.assertEqual(events[0]['args']['group_id'], group_id)

    ##############################################################################
    # Functions that verify mutations
    ##############################################################################
    
    def _verify_add_role(self, tx, role_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleAdded.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_add_update_event(events, self._eth_kp_src.ss58_address, role_id, name)

        # fetch role and verify
        data = self._contract.functions.fetch_role(self._account, role_id).call()
        self.assertEqual(data[0], role_id)
        self.assertEqual(data[1], name)

        return tx
    
    def _verify_update_role(self, tx, role_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_add_update_event(events, self._eth_kp_src.ss58_address, role_id, name)

        # fetch role and verify
        data = self._contract.functions.fetch_role(self._account, role_id).call()
        self.assertEqual(data[0], role_id)
        self.assertEqual(data[1], name)

        return tx
    
    def _verify_disable_role(self, tx, role_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleRemoved.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_disabled_event(events, self._eth_kp_src.ss58_address, role_id)

        # fetch role and verify
        data = self._contract.functions.fetch_role(self._account, role_id).call()
        self.assertEqual(data[0], role_id)
        self.assertEqual(data[2], False)

        return tx

    def _verify_assign_role_to_user(self, tx, role_id, user_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleAssignedToUser.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assign_or_unassign_event(events, self._eth_kp_src.ss58_address, role_id, user_id)

        # verify fetch_user_roles returns correct data
        data = self._contract.functions.fetch_user_roles(self._account, user_id).call()
        if not any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} not assigned to user {user_id}')

        return tx

    def _verify_unassign_role_to_user(self, tx, role_id, user_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleUnassignedToUser.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assign_or_unassign_event(events, self._eth_kp_src.ss58_address, role_id, user_id)

        # verify fetch_user_roles returns correct data
        data = self._contract.functions.fetch_user_roles(self._account, user_id).call()
        if any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} still assigned to user {user_id}')

        
    def _verify_add_permission(self, tx, permission_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionAdded.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_add_or_update_event(events, self._eth_kp_src.ss58_address, permission_id, name)

        # fetch permission and verify
        data = self._contract.functions.fetch_permission(self._account, permission_id).call()
        self.assertEqual(data[0], permission_id)
        self.assertEqual(data[1], name)

        return tx
    
    def _verify_update_permission(self, tx, permission_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_add_or_update_event(events, self._eth_kp_src.ss58_address, permission_id, name)

        # fetch permission and verify
        data = self._contract.functions.fetch_permission(self._account, permission_id).call()
        self.assertEqual(data[0], permission_id)
        self.assertEqual(data[1], name)
        
        return tx
    
    def _verify_disable_permission(self, tx, permission_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionRemoved.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_disabled_event(events, self._eth_kp_src.ss58_address, permission_id)

        # fetch permission and verify
        data = self._contract.functions.fetch_permission(self._account, permission_id).call()
        self.assertEqual(data[0], permission_id)
        self.assertEqual(data[2], False)

        return tx

    def _verify_assign_permission_to_role(self, tx, permission_id, role_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionAssigned.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_assigned_or_unassigned_to_role_event(events, self._eth_kp_src.ss58_address, permission_id, role_id)

        # verify fetch_role_permissions returns correct data
        data = self._contract.functions.fetch_role_permissions(self._account, role_id).call()
        if not any(permission_id in permissions for permissions in data):
            self.fail(f'Permission {permission_id} not assigned to role {role_id}')
        
        return tx
    
    def _verify_unassign_permission_to_role(self, tx, permission_id, role_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.PermissionAssigned.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_permission_assigned_or_unassigned_to_role_event(events, self._eth_kp_src.ss58_address, permission_id, role_id)

        # verify fetch_role_permissions returns correct data
        data = self._contract.functions.fetch_role_permissions(self._account, role_id).call()
        if any(permission_id in permissions for permissions in data):
            self.fail(f'Permission {permission_id} still assigned to role {role_id}')

        return tx
    
    def _verify_add_group(self, tx, group_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.GroupAdded.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_group_add_or_update_event(events, self._eth_kp_src.ss58_address, group_id, name)

        # fetch group and verify
        data = self._contract.functions.fetch_group(self._account, group_id).call()
        self.assertEqual(data[0], group_id)
        self.assertEqual(data[1], name)

        return tx
    
    def _verify_update_group(self, tx, group_id, name):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.GroupUpdated.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_group_add_or_update_event(events, self._eth_kp_src.ss58_address, group_id, name)

        # fetch group and verify
        data = self._contract.functions.fetch_group(self._account, group_id).call()
        self.assertEqual(data[0], group_id)
        self.assertEqual(data[1], name)

    def _verify_disable_group(self, tx, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.GroupRemoved.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_group_disabled_event(events, self._eth_kp_src.ss58_address, group_id)

        # fetch group and verify
        data = self._contract.functions.fetch_group(self._account, group_id).call()
        self.assertEqual(data[0], group_id)
        self.assertEqual(data[2], False)

    def _verify_assign_role_to_group(self, tx, role_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)
        
        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleAssignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, role_id, group_id)

        # verify fetch_group_roles returns correct data
        data = self._contract.functions.fetch_group_roles(self._account, group_id).call()
        if not any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} not assigned to group {group_id}')

    def _verify_unassign_role_to_group(self, tx, role_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)
        
        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.RoleUnassignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_role_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, role_id, group_id)

        # verify fetch_group_roles returns correct data
        data = self._contract.functions.fetch_group_roles(self._account, group_id).call()
        if any(role_id in roles for roles in data):
            self.fail(f'Role {role_id} still assigned to group {group_id}')

    def _verify_assign_user_to_group(self, tx, user_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)

        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.UserAssignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_user_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, user_id, group_id)

        # verify fetch_group_users returns correct data
        data = self._contract.functions.fetch_user_groups(self._account, user_id).call()
        if any(group_id in groups for groups in data):
            self.fail(f'User {user_id} not assigned to group {group_id}')
    
    def _verify_unassign_user_to_group(self, tx, user_id, group_id):
        self.assertEqual(tx['status'], TX_SUCCESS_STATUS)
        
        # get block events and verify
        block_idx = tx['blockNumber']
        events = self._contract.events.UserUnassignedToGroup.create_filter(fromBlock=block_idx, toBlock=block_idx).get_all_entries()
        self._verify_user_assigned_or_unassigned_to_group_event(events, self._eth_kp_src.ss58_address, user_id, group_id)

        # verify fetch_group_users returns correct data
        data = self._contract.functions.fetch_user_groups(self._account, user_id).call()
        if any(group_id in groups for groups in data):
            self.fail(f'User {user_id} still assigned to group {group_id}')

    def fund_account(self):
        # Setup eth_ko_src with some tokens
        transfer(self._substrate, KP_SRC, calculate_evm_account(self._eth_src), TOKEN_NUM)
        bl_hash = call_eth_transfer_a_lot(self._substrate, KP_SRC, self._eth_src, self._eth_kp_src.ss58_address.lower())
        # verify tokens have been transferred
        self.assertTrue(bl_hash, f'Failed to transfer token to {self._eth_kp_src.ss58_address}')

    def setUp(self):
        self._eth_src = calculate_evm_addr(KP_SRC.ss58_address)
        self._w3 = Web3(Web3.HTTPProvider(ETH_URL))
        self._substrate = SubstrateInterface(url=WS_URL)
        self._eth_kp_src = Keypair.create_from_private_key(ETH_PRIVATE_KEY, crypto_type=KeypairType.ECDSA)
        self._account = calculate_evm_account_hex(self._eth_kp_src.ss58_address)
        self._contract = get_contract(self._w3, RBAC_ADDRESS, ABI_FILE)

    def test_rbac_bridge(self):

        users = [generate_random_tuple() for _ in range(3)]
        roles = [generate_random_tuple() for _ in range(3)]
        permissions = [generate_random_tuple() for _ in range(3)]
        groups = [generate_random_tuple() for _ in range(3)]

        # fund test account
        self.fund_account()

        # add roles, permissions and groups
        self._verify_add_role(self._add_role(*roles[0]), *roles[0])
        self._add_role(*roles[1])
        self._add_role(*roles[2])

        self._verify_add_permission(self._add_permission(*permissions[0]), *permissions[0])
        self._add_permission(*permissions[1])
        self._add_permission(*permissions[2])

        self._verify_add_group(self._add_group(*groups[0]), *groups[0])
        self._add_group(*groups[1])
        self._add_group(*groups[2])

        # update roles, permissions and groups - TODO replace updated values with newer values and check
        self._verify_update_role(self._update_role(*roles[1]), *roles[1])
        self._verify_update_permission(self._update_permission(*permissions[1]), *permissions[1])
        self._verify_update_group(self._update_group(*groups[1]), *groups[1])

        # disable roles, permissions and groups
        self._verify_disable_role(self._disable_role(roles[2]), roles[2])
        self._verify_disable_permission(self._disable_permission(permissions[2]), permissions[2])
        self._verify_disable_group(self._disable_group(groups[2]), groups[2])

        # assign role to user
        self._verify_assign_role_to_user(self._assign_role_to_user(roles[0][0], users[0][0]), roles[0][0], users[0][0])
        self._assign_role_to_user(roles[1][0], users[0][0])
        self._assign_role_to_user(roles[2][0], users[0][0])

        # unassign role to user
        self._verify_unassign_role_to_user(self._unassign_role_to_user(roles[0][0], users[0][0]),roles[0][0], users[0][0]) 

        # assign permission to role
        self._verify_assign_permission_to_role(self._assign_permission_to_role(permissions[0][0], roles[0][0]), permissions[0][0], roles[0][0])
        self._assign_permission_to_role(permissions[1][0], roles[0][0])
        self._assign_permission_to_role(permissions[2][0], roles[0][0])

        # unassign permission to role
        self._verify_unassign_permission_to_role(self._unassign_permission_to_role(permissions[0][0], roles[0][0]), permissions[0][0], roles[0][0])

        # assign role to group
        self._verify_assign_role_to_group(self._assign_role_to_group(roles[0][0], groups[0][0]), roles[0][0], groups[0][0])
        self._assign_role_to_group(roles[1][0], groups[0][0])
        self._assign_role_to_group(roles[2][0], groups[0][0])

        # unassign role to group
        self._verify_unassign_role_to_group(self._unassign_role_to_group(roles[0][0], groups[0][0]), roles[0][0], groups[0][0])

        # assign user to group
        self._verify_assign_user_to_group(self._assign_user_to_group(users[0][0], groups[0][0]), users[0][0], groups[0][0])
        self._assign_user_to_group(users[1][0], groups[0][0])
        self._assign_user_to_group(users[2][0], groups[0][0])

        # unassign user to group
        self._verify_unassign_user_to_group(self._unassign_user_to_group(users[0][0], groups[0][0]), users[0][0], groups[0][0])