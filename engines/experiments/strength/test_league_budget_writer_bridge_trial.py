"""Existing DynamoRepository transaction exercised with its fake client only."""
import unittest

try:
    from . import league_budget_writer_bridge_trial as bridge
    from . import league_budget_writer_trial as trial
    from . import league_writer_lambda as diagnostic
    from .test_league_writer_lambda import Dynamo
except ImportError:
    import league_budget_writer_bridge_trial as bridge
    import league_budget_writer_trial as trial
    import league_writer_lambda as diagnostic
    from test_league_writer_lambda import Dynamo


class ExistingTransactionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.root, head = trial.genesis('league-test')
        self.client = Dynamo(self.root)
        self.client.rows[diagnostic.HEAD] = self.client.wire(diagnostic.HEAD, head)
        self.repo = diagnostic.DynamoRepository(self.client, 'unit-only', self.client.codec, self.client.codec)
        self.store = bridge.TrialTransactionBridge(self.repo, self.root)
        self.writer = trial.TrialWriter(self.store, self.root)

    def budget(self, event, data):
        self.writer.append('budget', {'event': 'budget.v2.' + event, 'data': data}, at=1000)

    def host(self):
        self.budget('launch_requested', {'launch_token': 'first-token', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
        self.budget('instance_bound', {'launch_token': 'first-token', 'instance_id': 'i-first'})

    def intent(self):
        return {'attempt_id': 'attempt-1', 'game_id': 'game-1', 'pair_id': 'pair-1',
                'launch_token': 'first-token', 'instance_id': 'i-first',
                'host_sha256': 'a' * 64, 'job_sha256': 'b' * 64, 'request_sha256': 'c' * 64,
                'not_before_utc': 1000, 'expires_utc': 1060}

    def test_actual_repository_builds_one_atomic_event_and_indexes(self):
        self.host()
        receipt = self.writer.append('intent', self.intent(), at=1000)
        self.assertFalse(receipt['authorizes_go'])
        transaction = self.client.transactions[-1]['TransactItems']
        self.assertEqual(len(transaction), 4)
        self.assertEqual(transaction[0]['Update']['ConditionExpression'], '#body = :old')
        self.assertTrue(all(entry['Put']['ConditionExpression'] == 'attribute_not_exists(#pk) AND attribute_not_exists(#sk)'
                            for entry in transaction[1:]))
        root, events, head = self.store.read()
        self.assertEqual(len(events), 3)
        self.assertEqual(len(trial.replay(root, events, head)[0].games), 1)

    def test_missing_index_or_extra_row_rejects_next_write(self):
        self.host()
        self.writer.append('intent', self.intent(), at=1000)
        count = len(self.client.transactions)
        key = diagnostic.PREFIX + 'subject#go#game-1'
        removed = self.client.rows.pop(key)
        with self.assertRaises(ValueError):
            self.writer.append('budget', {'event': 'budget.v2.observe', 'data': {}}, at=1001)
        self.client.rows[key] = removed
        self.client.rows[diagnostic.PREFIX + 'extra'] = self.client.wire(diagnostic.PREFIX + 'extra', {})
        with self.assertRaises(ValueError):
            self.store.read()
        self.assertEqual(len(self.client.transactions), count)

    def test_changed_head_between_reads_is_not_a_snapshot(self):
        self.host()
        self.client.replace_head_after_query = self.client.wire(diagnostic.HEAD, {'revision': 0, 'sha256': 'f' * 64})
        with self.assertRaises(ValueError):
            self.store.read()

    def test_lost_transaction_reply_quarantines_caller(self):
        self.host()
        self.client.fail_after_commit = True
        with self.assertRaises(trial.Uncertain):
            self.writer.append('intent', self.intent(), at=1000)
        count = len(self.client.transactions)
        with self.assertRaises(trial.Uncertain):
            self.writer.append('intent', self.intent(), at=1000)
        self.assertEqual(len(self.client.transactions), count)
        self.assertEqual(len(trial.replay(*self.store.read())[0].games), 1)

    def test_stale_head_cannot_append_a_second_transaction(self):
        self.host()
        _, _, stale = self.store.read()
        self.writer.append('intent', self.intent(), at=1000)
        _, events, current = self.store.read()
        with self.assertRaises(ValueError):
            self.store.compare_append(stale, events[-1], current)
        root, persisted, head = self.store.read()
        self.assertEqual(len(persisted), 3)
        self.assertEqual(len(trial.replay(root, persisted, head)[0].games), 1)

    def test_second_host_with_stale_head_is_quarantined_without_a_game(self):
        self.host()
        self.budget('launch_requested', {'launch_token': 'other-token', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
        self.budget('instance_bound', {'launch_token': 'other-token', 'instance_id': 'i-other'})
        primary = self.writer
        class RacingBridge(bridge.TrialTransactionBridge):
            def read(inner):
                snapshot = super().read()
                primary.append('intent', self.intent(), at=1000)
                return snapshot
        racing = trial.TrialWriter(RacingBridge(self.repo, self.root), self.root)
        second = self.intent()
        second.update({'attempt_id': 'attempt-2', 'game_id': 'game-2', 'pair_id': 'pair-2',
                       'launch_token': 'other-token', 'instance_id': 'i-other'})
        with self.assertRaises(trial.Uncertain):
            racing.append('intent', second, at=1000)
        count = len(self.client.transactions)
        with self.assertRaises(trial.Uncertain):
            racing.append('intent', second, at=1000)
        self.assertEqual(len(self.client.transactions), count)
        root, rows, head = self.store.read()
        self.assertEqual([game.game_id for game in trial.replay(root, rows, head)[0].games], ['game-1'])


if __name__ == '__main__':
    unittest.main()
