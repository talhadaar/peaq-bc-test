import unittest
import time

from substrateinterface import SubstrateInterface, Keypair
from tools.utils import WS_URL, get_chain, get_collators, get_block_height, get_account_balance, get_block_hash
from tools.utils import KP_GLOBAL_SUDO, exist_pallet, KP_COLLATOR
from tools.payload import sudo_call_compose, sudo_extrinsic_send, user_extrinsic_send
from tools.utils import ExtrinsicBatch, get_event
from tools.runtime_upgrade import wait_until_block_height
from tests.utils_func import restart_parachain_and_runtime_upgrade
import warnings


@user_extrinsic_send
def add_delegator(substrate, kp_delegator, addr_collator, stake_number):
    return substrate.compose_call(
        call_module='ParachainStaking',
        call_function='join_delegators',
        call_params={
            'collator': addr_collator,
            'amount': stake_number,
        })


@user_extrinsic_send
def collator_stake_more(substrate, kp_collator, stake_number):
    return substrate.compose_call(
        call_module='ParachainStaking',
        call_function='candidate_stake_more',
        call_params={
            'more': stake_number,
        })


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_coefficient(substrate, coefficient):
    return substrate.compose_call(
        call_module='StakingCoefficientRewardCalculator',
        call_function='set_coefficient',
        call_params={
            'coefficient': coefficient,
        }
    )


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_max_candidate_stake(substrate, stake):
    return substrate.compose_call(
        call_module='ParachainStaking',
        call_function='set_max_candidate_stake',
        call_params={
            'new': stake,
        }
    )


@sudo_extrinsic_send(sudo_keypair=KP_GLOBAL_SUDO)
@sudo_call_compose(sudo_keypair=KP_GLOBAL_SUDO)
def set_reward_rate(substrate, collator, delegator):
    return substrate.compose_call(
        call_module='StakingFixedRewardCalculator',
        call_function='set_reward_rate',
        call_params={
            'collator_rate': collator,
            'delegator_rate': delegator,
        }
    )


class TestDelegator(unittest.TestCase):
    def setUp(self):
        restart_parachain_and_runtime_upgrade()
        wait_until_block_height(SubstrateInterface(url=WS_URL), 1)

        self.substrate = SubstrateInterface(
            url=WS_URL,
        )
        self.chain_name = get_chain(self.substrate)
        self.collator = [KP_COLLATOR]
        self.delegators = [
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic()),
            Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
        ]

    def get_block_reward(self):
        block_reward = self.substrate.query(
            module='BlockReward',
            storage_function='DailyBlockReward',
        )
        block_reward = int(str(block_reward['avg']))
        config = self.substrate.query(
            module='BlockReward',
            storage_function='RewardDistributionConfigStorage',
        )
        config = config.value
        collator_percent = config['collators_percent'] / sum(config.values())
        return block_reward * collator_percent

    def get_parachain_reward(self, block_hash):
        event = get_event(self.substrate, block_hash, 'ParachainStaking', 'Rewarded')
        if not event:
            return None
        return int(str(event[1][1][1]))

    def get_balance_difference(self, addr):
        current_height = get_block_height(self.substrate)
        current_block_hash = get_block_hash(self.substrate, current_height)
        now_balance = get_account_balance(self.substrate, addr, current_block_hash)

        previous_height = current_height - 1
        previous_block_hash = get_block_hash(self.substrate, previous_height)
        pre_balance = get_account_balance(self.substrate, addr, previous_block_hash)
        return now_balance - pre_balance

    def get_one_collator_without_delegator(self, keys):
        for key in keys:
            collator = get_collators(self.substrate, key)
            if str(collator['delegators']) == '[]':
                return collator
        return None

    def claim_delegate_reward(self, kp):
        batch = ExtrinsicBatch(self.substrate, kp)
        batch.compose_call(
            'ParachainStaking',
            'increment_delegator_rewards',
            {}
        )

        batch.compose_call(
            'ParachainStaking',
            'claim_rewards',
            {}
        )
        return batch.execute()

    def claim_collator_reward(self, kp):
        batch = ExtrinsicBatch(self.substrate, kp)
        batch.compose_call(
            'ParachainStaking',
            'increment_collator_rewards',
            {}
        )

        batch.compose_call(
            'ParachainStaking',
            'claim_rewards',
            {}
        )
        return batch.execute()

    def wait_get_reward(self, addr):
        time.sleep(12 * 2)
        count_down = 0
        wait_time = 120
        prev_balance = get_account_balance(self.substrate, addr)
        while count_down < wait_time:
            if prev_balance != get_account_balance(self.substrate, addr):
                return True
            print(f'already wait about {count_down} seconds')
            count_down += 12
            time.sleep(12)
        return False

    def batch_fund(self, batch, kp, amount):
        batch.compose_sudo_call('Balances', 'force_set_balance', {
            'who': kp.ss58_address,
            'new_free': amount,
            'new_reserved': 0
        })

    def internal_test_issue_coefficient(self, mega_tokens):
        if not exist_pallet(self.substrate, 'StakingCoefficientRewardCalculator'):
            warnings.warn('StakingCoefficientRewardCalculator pallet not exist, skip the test')
            return

        # Check it's the peaq-dev parachain
        self.assertTrue(self.chain_name in ['peaq-dev', 'peaq-dev-fork', 'krest', 'krest-network-fork'])

        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        batch.compose_sudo_call('BlockReward', 'set_max_currency_supply', {
            'limit': 10 ** 5 * mega_tokens
        })
        batch.compose_sudo_call('ParachainStaking', 'set_max_candidate_stake', {
            'new': 10 ** 5 * mega_tokens
        })
        batch.compose_sudo_call('StakingCoefficientRewardCalculator', 'set_coefficient', {
            'coefficient': 2,
        })
        self.batch_fund(batch, KP_COLLATOR, 20 * mega_tokens)
        self.batch_fund(batch, self.delegators[0], 10 * mega_tokens)
        self.batch_fund(batch, self.delegators[1], 10 * mega_tokens)
        bl_hash = batch.execute()
        self.assertTrue(bl_hash, 'Batch failed')

        # Get the collator account
        receipt = collator_stake_more(self.substrate, KP_COLLATOR, 5 * mega_tokens)
        self.assertTrue(receipt.is_success, 'Stake failed')
        bl_hash = self.claim_collator_reward(KP_COLLATOR)
        collator_0_start = get_block_height(self.substrate, bl_hash)
        self.assertTrue(bl_hash, 'Claim reward failed')

        collator = self.get_one_collator_without_delegator(self.collator)
        self.assertGreaterEqual(int(str(collator['stake'])), 5 * mega_tokens)
        self.assertNotEqual(collator, None)

        # Add the delegator
        receipt = add_delegator(self.substrate, self.delegators[0], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        delegator_0_start = get_block_height(self.substrate, receipt.block_hash)

        receipt = add_delegator(self.substrate, self.delegators[1], str(collator['id']), int(str(collator['stake'])))
        self.assertTrue(receipt.is_success, 'Add delegator failed')
        delegator_1_start = get_block_height(self.substrate, receipt.block_hash)

        self.assertTrue(bl_hash, 'Claim reward failed')

        bl_hash = self.claim_delegate_reward(self.delegators[0])
        delegator_0_reward = self.get_parachain_reward(bl_hash)
        delegator_0_end = get_block_height(self.substrate, bl_hash)
        self.assertTrue(bl_hash, 'Claim reward failed')

        bl_hash = self.claim_delegate_reward(self.delegators[1])
        delegator_1_reward = self.get_parachain_reward(bl_hash)
        delegator_1_end = get_block_height(self.substrate, bl_hash)
        self.assertTrue(bl_hash, 'Claim reward failed')

        bl_hash = self.claim_collator_reward(KP_COLLATOR)
        collator_0_reward = self.get_parachain_reward(bl_hash)
        collator_0_end = get_block_height(self.substrate, bl_hash)
        self.assertTrue(bl_hash, 'Claim reward failed')

        delegator_0_avg_reward = delegator_0_reward / (delegator_0_end - delegator_0_start)
        delegator_1_avg_reward = delegator_1_reward / (delegator_1_end - delegator_1_start)
        collator_avg_reward = collator_0_reward / (collator_0_end - collator_0_start)
        self.assertEqual(delegator_0_avg_reward, delegator_1_avg_reward,
                         'The reward is not equal')
        self.assertAlmostEqual(
            (delegator_0_avg_reward + delegator_1_avg_reward) / collator_avg_reward,
            1, 7,
            f'{delegator_0_avg_reward} + {delegator_1_avg_reward} v.s. {collator_avg_reward} is not equal')

    def test_issue_coeffective(self):
        self.internal_test_issue_coefficient(500000 * 10 ** 18)

    def test_issue_coeffective_large(self):
        self.internal_test_issue_coefficient(10 ** 15 * 10 ** 18)

    def test_collator_stake(self):
        block_reward = self.get_block_reward()

        mega_tokens = 500000 * 10 ** 18
        if not exist_pallet(self.substrate, 'StakingCoefficientRewardCalculator'):
            warnings.warn('StakingCoefficientRewardCalculator pallet not exist, skip the test')
            return

        # Check it's the peaq-dev parachain
        self.assertTrue(self.chain_name in ['peaq-dev', 'peaq-dev-fork', 'krest', 'krest-network-fork'])

        batch = ExtrinsicBatch(self.substrate, KP_GLOBAL_SUDO)
        batch.compose_sudo_call('BlockReward', 'set_max_currency_supply', {
            'limit': 10 ** 5 * mega_tokens
        })
        batch.compose_sudo_call('ParachainStaking', 'set_max_candidate_stake', {
            'new': 10 ** 5 * mega_tokens
        })
        batch.compose_sudo_call('StakingCoefficientRewardCalculator', 'set_coefficient', {
            'coefficient': 2,
        })
        self.batch_fund(batch, KP_COLLATOR, 20 * mega_tokens)
        bl_hash = batch.execute()
        self.assertTrue(bl_hash, 'Batch failed')

        # Get the collator account
        batch = ExtrinsicBatch(self.substrate, KP_COLLATOR)
        batch.compose_call(
            'ParachainStaking',
            'candidate_stake_more',
            {'more': 5 * mega_tokens},
        )
        batch.compose_call(
            'ParachainStaking',
            'claim_rewards',
            {}
        )
        bl_hash = batch.execute()
        self.assertTrue(bl_hash, 'Claim reward failed')
        collator_0_end = get_block_height(self.substrate, bl_hash)

        collator_0_reward = self.get_parachain_reward(bl_hash)
        collator_avg_reward = collator_0_reward / (collator_0_end - 0)
        self.assertAlmostEqual(
            collator_avg_reward / block_reward,
            1, 7,
            f'{collator_avg_reward} v.s. {block_reward} is not equal')
