"""Pure local budget/intent transaction model; no AWS or engine is involved."""
import copy
import threading
import unittest

try:
    from . import league_budget_writer_trial as model
except ImportError:
    import league_budget_writer_trial as model


class MemoryStore:
    """Test double for compare-and-append, not an AWS or durability claim."""
    def __init__(self, root, head):
        self.root, self.head, self.events = root, head, []
        self.lock = threading.Lock()
        self.barrier = None
        self.fail_after_commit = False
        self.bad_ack = False
        self.calls = 0

    def read(self):
        with self.lock:
            return copy.deepcopy((self.root, self.events, self.head))

    def compare_append(self, old, event, new):
        if self.barrier:
            self.barrier.wait(timeout=5)
        with self.lock:
            self.calls += 1
            if old != self.head:
                raise model.Conflict('head changed')
            self.events.append(copy.deepcopy(event))
            self.head = copy.deepcopy(new)
            if self.fail_after_commit:
                raise TimeoutError('response lost after transaction')
            return {} if self.bad_ack else copy.deepcopy(new)


class BudgetWriterTrialTests(unittest.TestCase):
    def setUp(self):
        self.root, head = model.genesis('league-test')
        self.store = MemoryStore(self.root, head)
        self.writer = model.TrialWriter(self.store, self.root)

    def budget(self, event, data, at=1000):
        return self.writer.append('budget', {'event': 'budget.v2.' + event, 'data': data}, at=at)

    def hosts(self, rate='8'):
        for token, instance in (('first-token', 'i-first'), ('other-token', 'i-other')):
            self.budget('launch_requested', {'launch_token': token, 'region': 'ap-southeast-2', 'max_hourly_usd': rate})
            self.budget('instance_bound', {'launch_token': token, 'instance_id': instance})

    def intent(self, game='game-1', token='first-token', instance='i-first', start=1000, end=1060):
        return {'attempt_id': 'attempt-' + game, 'game_id': game, 'pair_id': 'pair-' + game,
                'launch_token': token, 'instance_id': instance, 'host_sha256': 'a' * 64,
                'job_sha256': 'b' * 64, 'request_sha256': 'c' * 64,
                'not_before_utc': start, 'expires_utc': end}

    def append_intent(self, payload, at=1000):
        return self.writer.append('intent', payload, at=at)

    def state(self):
        root, events, head = self.store.read()
        return model.replay(root, events, head)[0]

    def test_intent_atomically_admits_and_reserves_but_not_authority(self):
        self.hosts()
        receipt = self.append_intent(self.intent())
        game, = self.state().games
        self.assertTrue(game.release_authorized)
        self.assertEqual(game.release_valid_until, 1060)
        self.assertFalse(receipt['authorizes_go'])
        self.assertFalse(receipt['authorizes_launch'])
        self.assertFalse(receipt['authorizes_termination'])
        self.assertFalse(self.writer.provides_go_authority)

    def test_exact_crossing_of_two_host_upper_bound_rejects_intent(self):
        self.root, head = model.genesis('league-test', prior_compute_usd='99')
        self.store = MemoryStore(self.root, head)
        self.writer = model.TrialWriter(self.store, self.root)
        self.hosts()
        self.assertLess(model.projected_upper_micros(self.state(), 1170), 120_000_000)
        self.assertEqual(model.projected_upper_micros(self.state(), 1225), 120_000_000)
        before = self.store.read()
        with self.assertRaises(ValueError):
            self.append_intent(self.intent(start=1170, end=1225), at=1170)
        self.assertEqual(before, self.store.read())

    def test_projection_rounds_up_and_accounts_for_minimum_and_ancillary(self):
        self.hosts(rate='0.1')
        # Two 60-second minimum charges: 0.003333... dollars, plus $20 reserve.
        self.assertEqual(model.projected_upper_micros(self.state(), 1000), 20_003_334)
        self.budget('ancillary_charge', {'receipt_id': 'r1', 'usd': '21'})
        self.assertEqual(model.projected_upper_micros(self.state(), 1000), 21_003_334)

    def test_no_unbounded_expired_future_or_overlong_window(self):
        self.hosts()
        for start, end, at in ((1000, 1000, 1000), (1000, 1061, 1000),
                               (1001, 1060, 1000), (900, 960, 1000)):
            with self.subTest(start=start, end=end, at=at), self.assertRaises(ValueError):
                self.append_intent(self.intent(start=start, end=end), at=at)
        bad = self.intent()
        del bad['expires_utc']
        with self.assertRaises(ValueError):
            self.append_intent(bad)

    def test_bound_instance_and_digests_are_required(self):
        self.hosts()
        for field, value in (('instance_id', 'i-other'), ('launch_token', 'missing-token'),
                             ('host_sha256', 'a' * 63), ('job_sha256', 'x' * 64)):
            intent = self.intent()
            intent[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.append_intent(intent)

    def test_duplicate_attempt_and_game_are_rejected_across_hosts(self):
        self.hosts()
        first = self.intent()
        self.append_intent(first)
        other = self.intent('game-2', 'other-token', 'i-other')
        other['attempt_id'] = first['attempt_id']
        with self.assertRaises(ValueError):
            self.append_intent(other)
        other['attempt_id'] = 'attempt-distinct'
        other['game_id'] = first['game_id']
        with self.assertRaises(ValueError):
            self.append_intent(other)

    def test_competing_host_requests_compare_same_head_once(self):
        self.hosts()
        self.store.barrier = threading.Barrier(2)
        writers = [model.TrialWriter(self.store, self.root), model.TrialWriter(self.store, self.root)]
        requests = [self.intent(), self.intent('game-2', 'other-token', 'i-other')]
        outcomes = []
        def run(writer, request):
            try:
                outcomes.append(writer.append('intent', request, at=1000))
            except Exception as error:
                outcomes.append(error)
        threads = [threading.Thread(target=run, args=pair) for pair in zip(writers, requests)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=8)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sum(isinstance(value, dict) for value in outcomes), 1)
        self.assertEqual(sum(isinstance(value, model.Conflict) for value in outcomes), 1)
        self.assertEqual(len(self.state().games), 1)

    def test_limit_preserves_existing_game_and_rejects_new_game(self):
        self.hosts()
        self.append_intent(self.intent())
        self.budget('limit_confirmed', {'actual_usd': '120',
            'evidence': {'observation_id': 'test-observation', 'source': 'test'}})
        with self.assertRaises(ValueError):
            self.append_intent(self.intent('game-2', 'other-token', 'i-other'))
        self.assertEqual(len(self.state().unsettled_games), 1)
        self.assertFalse(self.state().may_terminate('first-token'))

    def test_limit_observation_racing_intent_cannot_both_commit_same_head(self):
        self.hosts()
        self.store.barrier = threading.Barrier(2)
        writers = [model.TrialWriter(self.store, self.root), model.TrialWriter(self.store, self.root)]
        requests = [('intent', self.intent()), ('budget', {'event': 'budget.v2.limit_confirmed',
            'data': {'actual_usd': '120', 'evidence': {'observation_id': 'r', 'source': 'test'}}})]
        outcomes = []
        def run(writer, request):
            try:
                outcomes.append((request[0], writer.append(*request, at=1000)))
            except Exception as error:
                outcomes.append((request[0], error))
        threads = [threading.Thread(target=run, args=pair) for pair in zip(writers, requests)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=8)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sum(isinstance(value, dict) for _, value in outcomes), 1)
        self.assertEqual(sum(isinstance(value, model.Conflict) for _, value in outcomes), 1)
        self.store.barrier = None
        if next(kind for kind, value in outcomes if isinstance(value, dict)) == 'budget':
            with self.assertRaises(ValueError):
                self.append_intent(self.intent())
        else:
            self.budget('limit_confirmed', {'actual_usd': '120',
                'evidence': {'observation_id': 'r', 'source': 'test'}})
            self.assertEqual(len(self.state().unsettled_games), 1)

    def test_elapsed_13_hours_is_not_an_independent_stop_rule(self):
        self.hosts(rate='0.1')
        now = 1000 + 13 * 3600
        self.append_intent(self.intent(start=now, end=now + 60), at=now)
        self.assertEqual(len(self.state().games), 1)

    def test_response_loss_quarantines_and_committed_game_cannot_be_replayed(self):
        self.hosts()
        self.store.fail_after_commit = True
        with self.assertRaises(model.Uncertain):
            self.append_intent(self.intent())
        calls = self.store.calls
        with self.assertRaises(model.Uncertain):
            self.append_intent(self.intent())
        self.assertEqual(calls, self.store.calls)
        self.store.fail_after_commit = False
        other = model.TrialWriter(self.store, self.root)
        with self.assertRaises(ValueError):
            other.append('intent', self.intent(), at=1000)
        self.assertEqual(len(self.state().games), 1)

    def test_invalid_acknowledgement_is_uncertain_even_if_write_committed(self):
        self.hosts()
        self.store.bad_ack = True
        with self.assertRaises(model.Uncertain):
            self.append_intent(self.intent())
        self.assertEqual(len(self.state().games), 1)
        with self.assertRaises(model.Uncertain):
            self.append_intent(self.intent('game-2'))

    def test_payload_snapshot_does_not_invoke_attacker_deepcopy(self):
        class ChangingDict(dict):
            def __deepcopy__(self, memo):
                changed = dict(self)
                changed['expires_utc'] = changed['not_before_utc']
                return changed
        self.hosts()
        self.append_intent(ChangingDict(self.intent()))
        self.assertEqual(self.state().games[0].release_valid_until, 1060)

    def test_pinned_root_is_the_validated_json_snapshot(self):
        class ChangingRoot(dict):
            def __deepcopy__(self, memo):
                changed = dict(self)
                changed['prior_compute_usd'] = '99'
                return changed
        writer = model.TrialWriter(self.store, ChangingRoot(self.root))
        self.assertEqual(writer.root['prior_compute_usd'], '0')
        writer.append('budget', {'event': 'budget.v2.observe', 'data': {}}, at=1000)

    def test_corrupted_or_incomplete_history_and_time_regression_fail(self):
        self.hosts()
        root, rows, head = self.store.read()
        rows[0]['at'] = 1001
        with self.assertRaises(ValueError):
            model.replay(root, rows, head)
        with self.assertRaises(ValueError):
            model.replay(root, rows[:-1], head)
        with self.assertRaises(ValueError):
            self.writer.append('budget', {'event': 'budget.v2.observe', 'data': {}}, at=999)


if __name__ == '__main__':
    unittest.main()
