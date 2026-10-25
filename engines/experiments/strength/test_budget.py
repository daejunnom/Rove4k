"""Campaign accounting over real event sequences, including interrupted runs."""
from dataclasses import replace
from decimal import Decimal
import unittest

try:
    from .budget import BudgetPolicy, CampaignBudget, timestamp
except ImportError:
    from budget import BudgetPolicy, CampaignBudget, timestamp


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


if __name__ == '__main__':
    unittest.main()
