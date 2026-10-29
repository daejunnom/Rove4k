"""Campaign accounting over real event sequences, including interrupted runs."""
from dataclasses import replace
from decimal import Decimal
import unittest

try:
    from .budget import BudgetPolicy, CampaignBudget, SharedCampaignBudget, timestamp
except ImportError:
    from budget import BudgetPolicy, CampaignBudget, SharedCampaignBudget, timestamp


TOKEN = 'launch-token-one'


class BudgetTests(unittest.TestCase):
    def launch(self, budget=None, at=1000, token=TOKEN, instance='i-1234567890abcdef0'):
        budget = budget or CampaignBudget('campaign-a')
        budget = budget.apply('budget.launch_requested', {'launch_token': token, 'max_hourly_usd': '8'}, at)
        return budget.apply('budget.instance_bound', {'launch_token': token, 'instance_id': instance}, at)

    def test_terminate_request_does_not_free_slot_or_stop_billing(self):
        budget = self.launch()
        budget = budget.apply('budget.terminate_requested', {'launch_token': TOKEN, 'instance_id': 'i-1234567890abcdef0'}, 4600)
        self.assertEqual(budget.admit(4900, 0).instance_seconds_used, 3900)
        self.assertEqual(budget.admit(4900, 0).compute_upper_usd, Decimal('8.666666666666666666666666667'))
        with self.assertRaisesRegex(ValueError, 'already owns'):
            budget.apply('budget.launch_requested', {'launch_token': 'different-token', 'max_hourly_usd': '8'}, 4900)
        budget = budget.apply('budget.instance_observed', {
            'launch_token': TOKEN, 'instance_id': 'i-1234567890abcdef0',
            'state': 'terminated', 'evidence': {'api': 'DescribeInstances', 'request_id': 'r1'}}, 5000)
        self.assertEqual(len(budget.active_instances), 0)
        self.assertEqual(budget.admit(20000, 0).instance_seconds_used, 4000)

    def test_restart_and_offline_gap_preserve_cumulative_time(self):
        first = self.launch()
        first = first.apply('budget.instance_observed', {
            'launch_token': TOKEN, 'instance_id': 'i-1234567890abcdef0',
            'state': 'terminated', 'evidence': 'EC2 observed'}, 4600)
        second = self.launch(first, 20000, 'launch-token-two', 'i-abcdef12345678900')
        self.assertEqual(second.admit(23600, 0).instance_seconds_used, 7200)
        self.assertEqual(second.admit(23600, 0).compute_upper_usd, Decimal(16))
        self.assertEqual(second.deadline(23600), 59300)
        self.assertFalse(second.admit(23600, 36000).allowed)
        # Calendar gaps are not free permission to reset already used time.
        self.assertTrue(second.admit(23600, 35000).allowed)

    def test_unknown_launch_counts_until_authoritative_absence(self):
        budget = CampaignBudget('campaign-a').apply('budget.launch_requested', {
            'launch_token': TOKEN, 'max_hourly_usd': '8'}, 1000)
        retry = budget.apply('budget.launch_requested', {'launch_token': TOKEN, 'max_hourly_usd': '8'}, 1100)
        self.assertEqual(retry.instances[0].requested_at, 1000)
        self.assertEqual(retry.admit(1200, 0).instance_seconds_used, 200)
        with self.assertRaisesRegex(ValueError, 'authoritative'):
            retry.apply('budget.launch_absent', {'launch_token': TOKEN, 'authoritative_absence': True}, 1200)
        absent = retry.apply('budget.launch_absent', {'launch_token': TOKEN,
            'authoritative_absence': True, 'evidence': 'original token reconciled absent'}, 1200)
        self.assertEqual(absent.admit(3000, 0).compute_upper_usd, 0)
        self.assertEqual(absent.admit(3000, 0).instance_seconds_used, 0)

    def test_pair_retries_are_idempotent_but_new_pairs_do_not_reset_cap(self):
        budget = CampaignBudget('campaign-a')
        for i in range(128):
            budget = budget.apply('budget.pair_started', {'pair_id': 'pair-' + str(i)}, i)
        repeated = budget.apply('budget.pair_started', {'pair_id': 'pair-0'}, 129)
        self.assertEqual(len(repeated.started_pairs), 128)
        self.assertTrue(repeated.admit(129, 0, pair_id='pair-0').allowed)
        self.assertFalse(repeated.admit(129, 0, pair_id='pair-new').allowed)
        with self.assertRaisesRegex(ValueError, 'pair cap'):
            repeated.apply('budget.pair_started', {'pair_id': 'pair-new'}, 130)
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            repeated.apply('budget.pair_completed', {'pair_id': 'unknown'}, 130)

    def test_ancillary_reserve_and_actual_receipts_are_not_double_counted(self):
        budget = self.launch().apply('budget.ancillary_charge', {'receipt_id': 'storage', 'usd': '3'}, 1000)
        self.assertEqual(budget.admit(4600, 0).total_upper_usd, 28)
        budget = budget.apply('budget.ancillary_charge', {'receipt_id': 'tax-and-transfer', 'usd': '110'}, 4600)
        self.assertIn('total-budget', budget.admit(4600, 0).reasons)
        with self.assertRaisesRegex(ValueError, 'changed'):
            budget.apply('budget.ancillary_charge', {'receipt_id': 'storage', 'usd': '4'}, 4600)

    def test_boundaries_deadline_slack_and_minimum_billing(self):
        budget = self.launch()
        self.assertEqual(budget.admit(1000, 0).compute_upper_usd, Decimal(2) / 15)
        self.assertEqual(budget.deadline(1000), 43900)
        self.assertTrue(budget.admit(43899, 0).allowed)
        self.assertFalse(budget.admit(43900, 0).allowed)
        self.assertFalse(budget.admit(43901, 0).allowed)
        self.assertEqual(budget.admit(44201, 0).remaining_seconds, 0)

    def test_utc_replay_is_same_as_live_reduction(self):
        events = [
            {'campaign': 'campaign-a', 'event': 'budget.launch_requested', 'time_utc': '2026-10-25T00:00:00Z',
             'data': {'launch_token': TOKEN, 'max_hourly_usd': '8'}},
            {'campaign': 'campaign-a', 'event': 'budget.instance_bound', 'time_utc': '2026-10-25T00:00:01Z',
             'data': {'launch_token': TOKEN, 'instance_id': 'i-1234567890abcdef0'}},
            {'campaign': 'campaign-a', 'event': 'budget.pair_started', 'time_utc': '2026-10-25T00:00:10Z',
             'data': {'pair_id': 'pair-one'}},
        ]
        replayed = CampaignBudget.replay('campaign-a', events)
        now = timestamp('2026-10-25T01:00:00Z')
        self.assertEqual(replayed.admit(now, 0).compute_upper_usd, 8)
        self.assertEqual(replayed.started_pairs, {'pair-one'})
        with self.assertRaisesRegex(ValueError, 'different campaign'):
            CampaignBudget.replay('campaign-b', events)
        with self.assertRaisesRegex(ValueError, 'UTC offset'):
            timestamp('2026-10-25T01:00:00')

    def test_policy_cannot_increase_caps_or_drop_termination_reserve(self):
        for change in ({'instance_seconds': 43201}, {'max_pairs': 129}, {'compute_usd': '101'},
                       {'total_usd': '121'}, {'max_hourly_usd': '8.01'}, {'max_hourly_usd': '0'},
                       {'ancillary_reserve_usd': '0'}, {'termination_slack_seconds': 0},
                       {'instance_seconds': True}, {'max_pairs': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                BudgetPolicy(**change)


class SharedBudgetTests(unittest.TestCase):
    def launch(self, budget, token, region, instance, at=1000, rate='8'):
        budget = budget.apply('budget.v2.launch_requested', {'launch_token': token,
            'region': region, 'max_hourly_usd': rate}, at)
        return budget.apply('budget.v2.instance_bound', {'launch_token': token,
            'instance_id': instance}, at)

    def test_prior_receipt_replay_does_not_double_count_opening_balance(self):
        state = SharedCampaignBudget('c', prior_ancillary_usd='25', prior_receipts=(('old-storage', '3'),))
        self.assertEqual(state.totals(1000)[1], Decimal('25'))
        state = state.apply('budget.v2.ancillary_charge', {'receipt_id': 'old-storage', 'usd': '3'}, 1000)
        self.assertEqual(state.totals(1000)[1], Decimal('25'))
        with self.assertRaisesRegex(ValueError, 'receipt identity changed'):
            state.apply('budget.v2.ancillary_charge', {'receipt_id': 'old-storage', 'usd': '4'}, 1001)

    def test_two_regions_sum_prices_no_twelve_hour_cutoff(self):
        state = SharedCampaignBudget('c')
        state = self.launch(state, 'token-one', 'ap-southeast-2', 'i-first', rate='3')
        state = self.launch(state, 'token-two', 'ap-northeast-1', 'i-second', rate='4')
        compute, total = state.totals(1000 + 13 * 3600)
        self.assertEqual(compute, Decimal('91'))
        self.assertEqual(total, Decimal('111'))
        self.assertTrue(state.can_admit_game(1000 + 13 * 3600, game_id='a', pair_id='p', launch_token='token-one'))
        with self.assertRaisesRegex(ValueError, 'both instance slots'):
            state.apply('budget.v2.launch_requested', {'launch_token': 'token-three',
                'region': 'ap-southeast-1', 'max_hourly_usd': '4'}, 1001)

    def test_game_and_pair_ids_share_checkpoint_validation(self):
        state = self.launch(SharedCampaignBudget('c'), 'token-one', 'ap-southeast-2', 'i-first')
        for value in ('', 'has space', '한글', '_prefix', 'a' * 97, 'a\n', None, 1):
            for field in ('game_id', 'pair_id'):
                data = {'game_id': 'game', 'pair_id': 'pair', 'launch_token': 'token-one'}
                data[field] = value
                with self.subTest(field=field, value=value):
                    self.assertFalse(state.can_admit_game(1001, **data))
                    with self.assertRaisesRegex(ValueError, 'admission denied'):
                        state.apply('budget.v2.game_admitted', data, 1001)
        game_id, pair_id = 'A' + 'x' * 95, '9._-'
        admitted = state.apply('budget.v2.game_admitted', {'game_id': game_id,
            'pair_id': pair_id, 'launch_token': 'token-one'}, 1001)
        restored = SharedCampaignBudget('c', prior_game_ids=frozenset({admitted.games[0].game_id}),
                                        prior_pair_ids=frozenset({admitted.games[0].pair_id}))
        self.assertEqual(restored.prior_game_ids, frozenset({game_id}))
        self.assertEqual(restored.prior_pair_ids, frozenset({pair_id}))

    def test_cap_denies_each_new_game_even_in_a_started_pair_and_drains_live_games(self):
        state = SharedCampaignBudget('c')
        state = self.launch(state, 'token-one', 'ap-southeast-2', 'i-first')
        state = self.launch(state, 'token-two', 'ap-northeast-1', 'i-second')
        state = state.apply('budget.v2.game_admitted', {'game_id': 'g1', 'pair_id': 'pair-a', 'launch_token': 'token-one'}, 1001)
        state = state.apply('budget.v2.game_admitted', {'game_id': 'g2', 'pair_id': 'pair-b', 'launch_token': 'token-two'}, 1002)
        state = state.apply('budget.v2.game_release_authorized', {'game_id': 'g1'}, 1003)
        state = state.apply('budget.v2.game_release_authorized', {'game_id': 'g2'}, 1004)
        state = state.apply('budget.v2.game_release_observed', {'game_id': 'g1', 'launch_token': 'token-one',
            'evidence': {'game_id': 'g1', 'instance_id': 'i-first', 'observation_id': 'GO-1'}}, 1005)
        state = state.apply('budget.v2.observe', {}, 23500)  # 2 x $8/h x 6.25h + $20 reserve
        self.assertEqual(state.totals(23500)[1], Decimal('120'))
        self.assertTrue(state.draining)
        self.assertFalse(state.can_admit_game(23500, game_id='g3', pair_id='pair-a', launch_token='token-one'))
        with self.assertRaisesRegex(ValueError, 'admission denied'):
            state.apply('budget.v2.game_admitted', {'game_id': 'g3', 'pair_id': 'pair-a', 'launch_token': 'token-one'}, 23500)
        self.assertEqual({row.game_id for row in state.unsettled_games}, {'g1', 'g2'})
        # Delayed durable observation of a previously authorized GO remains
        # recordable after draining; uncertainty must never be erased.
        state = state.apply('budget.v2.game_release_observed', {'game_id': 'g2', 'launch_token': 'token-two',
            'evidence': {'game_id': 'g2', 'instance_id': 'i-second', 'observation_id': 'GO-2'}}, 23500)
        with self.assertRaisesRegex(ValueError, 'settled games'):
            state.apply('budget.v2.terminate_requested', {'launch_token': 'token-one', 'instance_id': 'i-first'}, 23501)
        with self.assertRaisesRegex(ValueError, 'physical completion'):
            state.apply('budget.v2.game_settled', {'game_id': 'g1'}, 23502)
        state = state.apply('budget.v2.game_settled', {'game_id': 'g1', 'launch_token': 'token-one',
            'physically_settled': True, 'evidence': {'game_id': 'g1', 'instance_id': 'i-first',
                'state': 'exited', 'observation_id': 'waitpid-1'}}, 23503)
        self.assertTrue(state.may_terminate('token-one'))
        self.assertFalse(state.may_terminate('token-two'))
        state = state.apply('budget.v2.game_settled', {'game_id': 'g2', 'launch_token': 'token-two',
            'physically_settled': True, 'evidence': {'game_id': 'g2', 'instance_id': 'i-second',
                'state': 'exited', 'observation_id': 'waitpid-2'}}, 23504)
        self.assertTrue(state.may_terminate('token-two'))
        self.assertGreater(state.totals(23504)[1], Decimal('120'))

    def test_reserved_game_is_not_released_after_cap(self):
        state = SharedCampaignBudget('c')
        state = self.launch(state, 'token-one', 'ap-southeast-2', 'i-first')
        state = self.launch(state, 'token-two', 'ap-northeast-1', 'i-second')
        state = state.apply('budget.v2.game_admitted', {'game_id': 'unreleased', 'pair_id': 'p', 'launch_token': 'token-one'}, 1001)
        state = state.apply('budget.v2.observe', {}, 23500)
        with self.assertRaisesRegex(ValueError, 'game release denied'):
            state.apply('budget.v2.game_release_authorized', {'game_id': 'unreleased'}, 23501)
        self.assertFalse(state.may_terminate('token-one'))

    def test_settlement_requires_exact_boolean_game_and_instance_owner(self):
        state = self.launch(SharedCampaignBudget('c'), 'token-one', 'ap-southeast-2', 'i-first')
        state = state.apply('budget.v2.game_admitted', {'game_id': 'g', 'pair_id': 'p', 'launch_token': 'token-one'}, 1001)
        receipt = {'game_id': 'g', 'instance_id': 'i-first', 'state': 'exited', 'observation_id': 'waitpid'}
        for change in ({'physically_settled': 'false'}, {'launch_token': 'token-two'},
                       {'evidence': dict(receipt, instance_id='i-other')},
                       {'evidence': dict(receipt, game_id='other')}):
            data = {'game_id': 'g', 'launch_token': 'token-one', 'physically_settled': True, 'evidence': receipt}
            data.update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'physical completion'):
                state.apply('budget.v2.game_settled', data, 1002)
        self.assertFalse(state.may_terminate('token-one'))

    def test_go_authorization_cannot_be_relabelled_cancelled_before_go(self):
        state = self.launch(SharedCampaignBudget('c'), 'token-one', 'ap-southeast-2', 'i-first')
        state = state.apply('budget.v2.game_admitted', {'game_id': 'g', 'pair_id': 'p', 'launch_token': 'token-one'}, 1001)
        state = state.apply('budget.v2.game_release_authorized', {'game_id': 'g'}, 1002)
        data = {'game_id': 'g', 'launch_token': 'token-one', 'physically_settled': True,
                'evidence': {'game_id': 'g', 'instance_id': 'i-first',
                    'state': 'cancelled_before_go', 'observation_id': 'receipt'}}
        with self.assertRaisesRegex(ValueError, 'physical completion'):
            state.apply('budget.v2.game_settled', data, 1003)
        self.assertFalse(state.may_terminate('token-one'))

    def test_uncertain_launch_blocks_until_authoritative_absence(self):
        state = SharedCampaignBudget('c').apply('budget.v2.launch_requested', {
            'launch_token': 'token-one', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 1000)
        self.assertGreater(state.totals(1000)[0], 0)
        with self.assertRaisesRegex(ValueError, 'bound instance'):
            state.apply('budget.v2.instance_observed', {'launch_token': 'token-one', 'instance_id': None,
                'state': 'terminated', 'evidence': {'launch_token': 'token-one', 'region': 'ap-southeast-2',
                    'instance_id': None, 'state': 'terminated', 'observation_id': 'unbound'}}, 1001)
        state = state.apply('budget.v2.observe', {}, 46000)
        self.assertTrue(state.draining)
        with self.assertRaisesRegex(ValueError, 'draining'):
            state.apply('budget.v2.launch_requested', {'launch_token': 'token-one',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 46000)
        with self.assertRaisesRegex(ValueError, 'authoritative EC2 evidence'):
            state.apply('budget.v2.launch_absent', {'launch_token': 'token-one',
                'authoritative_absence': 'false', 'evidence': 'not found'}, 46001)
        state = state.apply('budget.v2.launch_absent', {'launch_token': 'token-one',
            'authoritative_absence': True, 'evidence': {'launch_token': 'token-one', 'region': 'ap-southeast-2',
                'state': 'absent', 'observation_id': 'ec2-reconciliation'}}, 46001)
        self.assertEqual(state.totals(46001)[0], 0)
        self.assertFalse(state.draining)
        state = state.apply('budget.v2.launch_requested', {'launch_token': 'token-two',
            'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 46002)
        self.assertEqual(len(state.active_instances), 1)

    def test_confirmed_actual_limit_stays_closed_even_if_upper_bound_is_corrected(self):
        state = SharedCampaignBudget('c').apply('budget.v2.launch_requested', {
            'launch_token': 'token-one', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 1000)
        with self.assertRaisesRegex(ValueError, 'confirmed limit'):
            state.apply('budget.v2.limit_confirmed', {'actual_usd': '119.99',
                'evidence': {'source': 'billing', 'observation_id': 'bill-1'}}, 1001)
        state = state.apply('budget.v2.limit_confirmed', {'actual_usd': '120',
            'evidence': {'source': 'billing', 'observation_id': 'bill-2'}}, 1001)
        state = state.apply('budget.v2.launch_absent', {'launch_token': 'token-one',
            'authoritative_absence': True, 'evidence': {'launch_token': 'token-one', 'region': 'ap-southeast-2',
                'state': 'absent', 'observation_id': 'ec2-reconciliation'}}, 1002)
        self.assertLess(state.totals(1002)[1], Decimal('120'))
        self.assertTrue(state.draining)
        with self.assertRaisesRegex(ValueError, 'draining'):
            state.apply('budget.v2.launch_requested', {'launch_token': 'token-two',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 1003)

    def test_confirmed_limit_keeps_started_games_until_physical_settlement(self):
        state = self.launch(SharedCampaignBudget('c'), 'token-one', 'ap-southeast-2', 'i-first')
        state = state.apply('budget.v2.game_admitted', {'game_id': 'g', 'pair_id': 'p', 'launch_token': 'token-one'}, 1001)
        state = state.apply('budget.v2.game_release_authorized', {'game_id': 'g'}, 1002)
        state = state.apply('budget.v2.limit_confirmed', {'actual_usd': '120.01',
            'evidence': {'source': 'billing', 'observation_id': 'bill-1'}}, 1003)
        self.assertTrue(state.draining)
        self.assertFalse(state.can_admit_game(1003, game_id='g2', pair_id='p', launch_token='token-one'))
        self.assertFalse(state.may_terminate('token-one'))
        state = state.apply('budget.v2.game_settled', {'game_id': 'g', 'launch_token': 'token-one',
            'physically_settled': True, 'evidence': {'game_id': 'g', 'instance_id': 'i-first',
                'state': 'exited', 'observation_id': 'waitpid-1'}}, 1004)
        self.assertTrue(state.may_terminate('token-one'))
        self.assertTrue(state.draining)

    def test_release_window_accounts_for_both_instances_without_sticky_draining(self):
        state = self.launch(SharedCampaignBudget('c'), 'token-one', 'ap-southeast-2', 'i-first')
        state = self.launch(state, 'token-two', 'ap-northeast-1', 'i-second')
        state = state.apply('budget.v2.game_admitted', {'game_id': 'g', 'pair_id': 'p', 'launch_token': 'token-one'}, 1001)
        self.assertTrue(state.release_window_fits(23499, 23499))
        self.assertFalse(state.release_window_fits(23499, 23500))
        with self.assertRaisesRegex(ValueError, 'crosses limit'):
            state.apply('budget.v2.game_release_authorized', {'game_id': 'g', 'valid_until_utc': 23500}, 23499)
        self.assertFalse(state.confirmed_limit)
        with self.assertRaisesRegex(ValueError, 'bounded release window'):
            state.release_window_fits(23499, 23560)
        state = state.apply('budget.v2.game_release_authorized', {'game_id': 'g', 'valid_until_utc': 23499}, 23499)
        self.assertFalse(state.may_terminate('token-one'))
        self.assertEqual(state.games[0].release_valid_until, 23499)

    def test_regional_identity_deduplication_and_legacy_replay_fail_closed(self):
        state = SharedCampaignBudget('c')
        state = self.launch(state, 'token-one', 'ap-southeast-2', 'i-first')
        with self.assertRaisesRegex(ValueError, 'region or price'):
            state.apply('budget.v2.launch_requested', {'launch_token': 'token-one',
                'region': 'ap-northeast-1', 'max_hourly_usd': '8'}, 1001)
        state = state.apply('budget.v2.launch_requested', {'launch_token': 'token-two',
            'region': 'ap-northeast-1', 'max_hourly_usd': '8'}, 1002)
        with self.assertRaisesRegex(ValueError, 'identity'):
            state.apply('budget.v2.instance_bound', {'launch_token': 'token-two', 'instance_id': 'i-first'}, 1003)
        with self.assertRaisesRegex(ValueError, 'explicit migration'):
            SharedCampaignBudget.replay('c', [{'campaign': 'c', 'event': 'budget.pair_started',
                'data': {'pair_id': 'p'}, 'time_utc': 1000}])

    def test_terminated_or_closing_owner_cannot_admit_or_reuse_token(self):
        state = self.launch(SharedCampaignBudget('c'), 'token-one', 'ap-southeast-2', 'i-first')
        state = state.apply('budget.v2.terminate_requested', {'launch_token': 'token-one', 'instance_id': 'i-first'}, 1001)
        self.assertFalse(state.can_admit_game(1001, game_id='g', pair_id='p', launch_token='token-one'))
        with self.assertRaisesRegex(ValueError, 'closed launch token'):
            state.apply('budget.v2.launch_requested', {'launch_token': 'token-one',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 1002)
        with self.assertRaisesRegex(ValueError, 'authoritative observation'):
            state.apply('budget.v2.instance_observed', {'launch_token': 'token-one',
                'instance_id': 'i-first', 'state': 'terminated', 'evidence': {'launch_token': 'token-one',
                    'region': 'ap-northeast-1', 'instance_id': 'i-first', 'state': 'terminated',
                    'observation_id': 'wrong-region'}}, 1003)
        state = state.apply('budget.v2.instance_observed', {'launch_token': 'token-one',
            'instance_id': 'i-first', 'state': 'terminated', 'evidence': {'launch_token': 'token-one',
                'region': 'ap-southeast-2', 'instance_id': 'i-first', 'state': 'terminated',
                'observation_id': 'ec2-termination'}}, 1003)
        self.assertFalse(state.can_admit_game(1003, game_id='g', pair_id='p', launch_token='token-one'))
        with self.assertRaisesRegex(ValueError, 'closed launch token'):
            state.apply('budget.v2.launch_requested', {'launch_token': 'token-one',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 1004)

    def test_external_stopping_observation_fences_new_games_and_release(self):
        state = self.launch(SharedCampaignBudget('c'), 'token-one', 'ap-southeast-2', 'i-first')
        state = state.apply('budget.v2.game_admitted', {'game_id': 'g', 'pair_id': 'p', 'launch_token': 'token-one'}, 1001)
        state = state.apply('budget.v2.instance_observed', {'launch_token': 'token-one',
            'instance_id': 'i-first', 'state': 'shutting-down'}, 1002)
        self.assertFalse(state.can_admit_game(1002, game_id='g2', pair_id='p', launch_token='token-one'))
        with self.assertRaisesRegex(ValueError, 'game release denied'):
            state.apply('budget.v2.game_release_authorized', {'game_id': 'g'}, 1003)


if __name__ == '__main__':
    unittest.main()
