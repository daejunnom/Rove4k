"""Model-only checks; no engine, network, AWS client or authorization."""
import copy
import unittest

try:
    from . import league_atomic_admission_trial as model
    from . import league_budget_writer_trial as budget
except ImportError:
    import league_atomic_admission_trial as model
    import league_budget_writer_trial as budget


class FakeAtomicStore:
    """Sequential transaction model only; it is not a DynamoDB emulator."""
    def __init__(self, head):
        self.head, self.keys = copy.deepcopy(head), set()

    def commit(self, proposal):
        items = proposal['transaction']['TransactItems']
        update = items[0]['Update']
        values = update['ExpressionAttributeValues']
        fields = {':gen': 'generation', ':epoch': 'epoch', ':rev': 'revision',
                  ':owner': 'owner', ':mode': 'mode', ':br': 'budget_revision',
                  ':bh': 'budget_sha256', ':upper': 'budget_upper_micros', ':at': 'observed_at'}
        for placeholder, field in fields.items():
            actual = values[placeholder]
            expected = {'N': str(self.head[field])} if type(self.head[field]) is int else {'S': self.head[field]}
            if actual != expected:
                return False
        keys = [item['Put']['Item']['record_id']['S'] for item in items[1:]]
        if len(keys) != len(set(keys)) or self.keys.intersection(keys):
            return False
        # The assertions below also ensure the candidate next head corresponds
        # to the update's values, not just to a caller-provided result object.
        next_head = proposal['next_head']
        encoded = {':next': 'revision', ':br_next': 'budget_revision',
                   ':bh_next': 'budget_sha256', ':new_at': 'observed_at',
                   ':new_upper': 'budget_upper_micros', ':new_mode': 'mode', ':drain': 'mode'}
        for placeholder, field in encoded.items():
            if placeholder in values:
                expected = {'N': str(next_head[field])} if type(next_head[field]) is int else {'S': next_head[field]}
                if values[placeholder] != expected:
                    raise AssertionError('update values and proposed head differ')
        self.head = copy.deepcopy(next_head)
        self.keys.update(keys)
        return True


class AtomicAdmissionTrialTests(unittest.TestCase):
    def setUp(self):
        self.root, self.budget_head = budget.genesis('league-test')
        self.events = []
        for token, instance in (('first-token', 'i-first'), ('other-token', 'i-other')):
            self.budget_event('launch_requested', {'launch_token': token,
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
            self.budget_event('instance_bound', {'launch_token': token, 'instance_id': instance})
        self.owner = {'generation': 'a' * 64, 'epoch': 7, 'owner': 'b' * 64}
        self.head = self.make_head(1000)

    def budget_event(self, name, data, at=1000):
        core = {'revision': self.budget_head['revision'] + 1,
                'previous_sha256': self.budget_head['sha256'], 'at': at,
                'kind': 'budget', 'payload': {'event': 'budget.v2.' + name, 'data': data}}
        event = {**core, 'sha256': budget._hash(b'rove4k-budget-event\0', core)}
        next_head = {'revision': event['revision'], 'sha256': event['sha256']}
        budget.replay(self.root, self.events + [event], next_head)
        self.events.append(event)
        self.budget_head = next_head

    def make_head(self, at):
        state, _ = budget.replay(self.root, self.events, self.budget_head)
        return {'campaign': 'league-test', 'generation': 'a' * 64, 'epoch': 7,
                'revision': 21, 'owner': 'b' * 64, 'mode': 'active',
                'budget_revision': self.budget_head['revision'],
                'budget_sha256': self.budget_head['sha256'],
                'budget_upper_micros': budget.projected_upper_micros(state, at),
                'observed_at': at}

    def payload(self, game='game-1', token='first-token', instance='i-first', start=1000, end=1060):
        return {'attempt_id': 'attempt-' + game, 'game_id': game, 'pair_id': 'pair-' + game,
                'launch_token': token, 'instance_id': instance, 'host_sha256': 'c' * 64,
                'job_sha256': 'd' * 64, 'request_sha256': 'e' * 64,
                'not_before_utc': start, 'expires_utc': end}

    def proposal(self, payload=None, *, at=1000, write_state='clean', head=None, owner=None):
        return model.propose_admission('isolated-trial', self.root, self.events,
            self.head if head is None else head, self.payload() if payload is None else payload,
            at=at, write_state=write_state, owner_context=self.owner if owner is None else owner)

    def drain(self, *, at=1000, head=None, write_state='clean'):
        return model.propose_drain('isolated-trial', self.root, self.events,
            self.head if head is None else head, at=at, write_state=write_state,
            owner_context=self.owner)

    def observe(self, at, event='budget.v2.observe', data=None, *, head=None):
        return model.propose_budget_observation('isolated-trial', self.root, self.events,
            self.head if head is None else head, event, {} if data is None else data,
            at=at, write_state='clean', owner_context=self.owner)

    def test_single_request_binds_head_history_and_unique_indexes(self):
        before = copy.deepcopy((self.root, self.events, self.head))
        result = self.proposal()
        self.assertEqual(before, (self.root, self.events, self.head))
        self.assertEqual(result['write_state'], 'in_flight')
        self.assertFalse(result['write_performed'])
        self.assertFalse(result['authorizes_go'])
        self.assertFalse(result['inputs_authenticated'])
        self.assertFalse(result['recipient_fenced'])
        self.assertFalse(result['global_history_replayable'])
        self.assertFalse(result['ddb_item_size_verified'])
        items = result['transaction']['TransactItems']
        self.assertEqual(len(items), 4)
        update = items[0]['Update']
        for field in ('#gen', '#epoch', '#rev', '#owner', '#mode', '#br', '#bh', '#upper', '#at'):
            self.assertIn(field + ' = ', update['ConditionExpression'])
        self.assertEqual(update['ExpressionAttributeValues'][':rev'], {'N': '21'})
        rows = [item['Put'] for item in items[1:]]
        self.assertTrue(all('attribute_not_exists' in row['ConditionExpression'] for row in rows))
        keys = [row['Item']['record_id']['S'] for row in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(any('attempt#attempt-game-1' in key for key in keys))
        self.assertTrue(any('game#game-1' in key for key in keys))
        new_budget = {'revision': result['next_head']['budget_revision'],
                      'sha256': result['next_head']['budget_sha256']}
        state, _ = budget.replay(self.root, self.events + [result['event']], new_budget)
        self.assertEqual(state.games[0].game_id, 'game-1')
        self.assertTrue(state.games[0].release_authorized)  # Model state, not real GO.

    def test_two_hosts_and_exact_projected_limit(self):
        self.root, self.budget_head = budget.genesis('league-test', prior_compute_usd='99')
        self.events = []
        for token, instance in (('first-token', 'i-first'), ('other-token', 'i-other')):
            self.budget_event('launch_requested', {'launch_token': token,
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
            self.budget_event('instance_bound', {'launch_token': token, 'instance_id': instance})
        self.head = self.make_head(1170)
        with self.assertRaisesRegex(ValueError, 'limit|cap'):
            self.proposal(self.payload(start=1170, end=1225), at=1170)
        accepted = self.proposal(self.payload(start=1170, end=1224), at=1170)
        self.assertLess(accepted['projected_upper_micros'], 120_000_000)

    def test_generation_epoch_owner_and_bool_context_mismatch_rejected(self):
        for field, value in (('generation', 'f' * 64), ('epoch', 8), ('epoch', True),
                             ('owner', 'f' * 64)):
            with self.subTest(field=field, value=value):
                owner = {**self.owner, field: value}
                with self.assertRaises(ValueError):
                    self.proposal(owner=owner)

    def test_stale_budget_snapshot_or_wrong_history_fails(self):
        for field, value in (('budget_revision', self.head['budget_revision'] - 1),
                             ('budget_sha256', 'f' * 64),
                             ('budget_upper_micros', self.head['budget_upper_micros'] + 1),
                             ('observed_at', 999), ('observed_at', True)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.proposal(head={**self.head, field: value})
        with self.assertRaises(ValueError):
            self.proposal(at=1001)

    def test_draining_denies_new_games_without_settling_existing(self):
        admission = self.proposal()
        self.events.append(admission['event'])
        self.head = admission['next_head']
        state, _ = budget.replay(self.root, self.events,
            {'revision': self.head['budget_revision'], 'sha256': self.head['budget_sha256']})
        before = state.games
        drain = self.drain()
        self.assertEqual(drain['next_head']['mode'], 'draining')
        self.assertEqual(drain['next_head']['budget_sha256'], self.head['budget_sha256'])
        with self.assertRaises(ValueError):
            self.proposal(self.payload('game-2'), head=drain['next_head'])
        after, _ = budget.replay(self.root, self.events,
            {'revision': drain['next_head']['budget_revision'], 'sha256': drain['next_head']['budget_sha256']})
        self.assertEqual(before, after.games)
        self.assertFalse(after.games[0].settled)

    def test_competing_drain_and_start_compare_same_complete_head(self):
        admission, drain = self.proposal(), self.drain()
        a = admission['transaction']['TransactItems'][0]['Update']
        d = drain['transaction']['TransactItems'][0]['Update']
        self.assertEqual(a['ConditionExpression'], d['ConditionExpression'])
        for key in (':gen', ':epoch', ':rev', ':owner', ':mode', ':br', ':bh', ':upper', ':at'):
            self.assertEqual(a['ExpressionAttributeValues'][key], d['ExpressionAttributeValues'][key])
        for first, second in ((admission, drain), (drain, admission)):
            with self.subTest(first=first['next_head']['mode']):
                store = FakeAtomicStore(self.head)
                self.assertTrue(store.commit(first))
                before = copy.deepcopy((store.head, store.keys))
                self.assertFalse(store.commit(second))
                self.assertEqual(before, (store.head, store.keys))

    def test_later_drain_preserves_old_observation_and_rejects_time_regression(self):
        drain = self.drain(at=1100)
        self.assertEqual(drain['next_head']['mode'], 'draining')
        self.assertEqual(drain['next_head']['observed_at'], self.head['observed_at'])
        self.assertEqual(drain['next_head']['budget_upper_micros'], self.head['budget_upper_micros'])
        self.assertFalse(drain['authorizes_go'])
        record = drain['transaction']['TransactItems'][1]['Put']['Item']
        self.assertIn('"at":1100', record['body']['S'])
        for invalid in (999, True, -1):
            with self.subTest(at=invalid), self.assertRaises(ValueError):
                self.drain(at=invalid)

    def test_later_drain_and_observation_compete_on_same_prior_head(self):
        drain, observation = self.drain(at=1100), self.observe(1100)
        for first, second in ((drain, observation), (observation, drain)):
            with self.subTest(first=first['next_head']['mode']):
                store = FakeAtomicStore(self.head)
                self.assertTrue(store.commit(first))
                before = copy.deepcopy((store.head, store.keys))
                self.assertFalse(store.commit(second))
                self.assertEqual(before, (store.head, store.keys))

    def test_two_hosts_compete_on_one_head_without_partial_write(self):
        first = self.proposal()
        second = self.proposal(self.payload('game-2', 'other-token', 'i-other'))
        store = FakeAtomicStore(self.head)
        self.assertTrue(store.commit(first))
        before = copy.deepcopy((store.head, store.keys))
        self.assertFalse(store.commit(second))
        self.assertEqual(before, (store.head, store.keys))

    def test_observation_advances_budget_and_can_admit_at_later_time(self):
        earlier = self.head['budget_upper_micros']
        observation = self.observe(1100)
        self.assertEqual(observation['next_head']['observed_at'], 1100)
        self.assertGreater(observation['next_head']['budget_upper_micros'], earlier)
        self.assertEqual(observation['next_head']['mode'], 'active')
        self.events.append(observation['event'])
        self.head = observation['next_head']
        admission = self.proposal(self.payload(start=1100, end=1160), at=1100)
        self.assertEqual(admission['event']['at'], 1100)
        for at in (1100, 1099):
            with self.subTest(at=at), self.assertRaises(ValueError):
                self.observe(at)

    def test_observation_crossing_budget_atomically_drains(self):
        self.root, self.budget_head = budget.genesis('league-test', prior_compute_usd='99')
        self.events = []
        for token, instance in (('first-token', 'i-first'), ('other-token', 'i-other')):
            self.budget_event('launch_requested', {'launch_token': token,
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
            self.budget_event('instance_bound', {'launch_token': token, 'instance_id': instance})
        self.head = self.make_head(1170)
        observation = self.observe(1225)
        self.assertEqual(observation['next_head']['mode'], 'draining')
        self.assertEqual(observation['next_head']['budget_upper_micros'], 120_000_000)
        update = observation['transaction']['TransactItems'][0]['Update']
        self.assertIn('#mode = :new_mode', update['UpdateExpression'])
        self.events.append(observation['event'])
        self.head = observation['next_head']
        with self.assertRaises(ValueError):
            self.proposal(self.payload(start=1225, end=1285), at=1225)

    def test_active_start_reserves_last_revision_for_drain(self):
        last_usable = {**self.head, 'revision': model._MAX_REVISION - 1}
        with self.assertRaisesRegex(ValueError, 'room'):
            self.proposal(head=last_usable)
        drain = self.drain(head=last_usable)
        self.assertEqual(drain['next_head']['revision'], model._MAX_REVISION)
        self.assertEqual(drain['next_head']['mode'], 'draining')

    def test_duplicate_attempt_or_game_across_hosts_rejected_on_replay(self):
        first = self.proposal()
        self.events.append(first['event'])
        self.head = first['next_head']
        second = self.payload('game-2', 'other-token', 'i-other')
        for field, value in (('attempt_id', 'attempt-game-1'), ('game_id', 'game-1')):
            changed = {**second, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.proposal(changed)

    def test_window_host_identity_and_table_checks(self):
        for start, end, at in ((1000, 1000, 1000), (1000, 1061, 1000),
                               (1001, 1060, 1000), (900, 960, 1000)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.proposal(self.payload(start=start, end=end), at=at)
        with self.assertRaises(ValueError):
            self.proposal(self.payload(instance='i-other'))
        with self.assertRaises(ValueError):
            model.propose_admission('../other', self.root, self.events, self.head, self.payload(),
                at=1000, write_state='clean', owner_context=self.owner)

    def test_oversized_observation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'bounded body'):
            self.observe(1001, data={'untrusted': 'x' * (70 * 1024)})

    def test_lifecycle_after_drain_preserves_games_and_records_settlement(self):
        admission = self.proposal()
        self.events.append(admission['event'])
        self.head = admission['next_head']
        self.head = self.drain(at=1000)['next_head']
        with self.assertRaisesRegex(ValueError, 'settled games'):
            self.observe(1000, event='budget.v2.terminate_requested',
                data={'launch_token': 'first-token', 'instance_id': 'i-first'})
        release_data = {'game_id': 'game-1', 'launch_token': 'first-token',
            'evidence': {'game_id': 'game-1', 'instance_id': 'i-first', 'observation_id': 'go-1'}}
        release = self.observe(1000, event='budget.v2.game_release_observed', data=release_data)
        self.assertFalse(release['authorizes_go'])
        self.assertEqual(release['next_head']['mode'], 'draining')
        self.assertEqual(len(release['transaction']['TransactItems']), 3)
        self.events.append(release['event'])
        self.head = release['next_head']
        with self.assertRaisesRegex(ValueError, 'already applied'):
            self.observe(1000, event='budget.v2.game_release_observed', data=release_data)
        settle_data = {'game_id': 'game-1', 'launch_token': 'first-token', 'physically_settled': True,
            'evidence': {'game_id': 'game-1', 'instance_id': 'i-first', 'state': 'exited',
                         'observation_id': 'finish-1'}}
        settled = self.observe(1000, event='budget.v2.game_settled', data=settle_data)
        self.events.append(settled['event'])
        self.head = settled['next_head']
        state, _ = budget.replay(self.root, self.events,
            {'revision': self.head['budget_revision'], 'sha256': self.head['budget_sha256']})
        self.assertTrue(state.games[0].release_observed)
        self.assertTrue(state.games[0].settled)
        with self.assertRaisesRegex(ValueError, 'already applied'):
            self.observe(1000, event='budget.v2.game_settled', data=settle_data)
        termination = self.observe(1000, event='budget.v2.terminate_requested',
            data={'launch_token': 'first-token', 'instance_id': 'i-first'})
        self.assertFalse(termination['authorizes_termination'])
        self.events.append(termination['event'])
        self.head = termination['next_head']
        with self.assertRaisesRegex(ValueError, 'already recorded'):
            self.observe(1000, event='budget.v2.terminate_requested',
                data={'launch_token': 'first-token', 'instance_id': 'i-first'})
        closed = self.observe(1001, event='budget.v2.instance_observed', data={
            'launch_token': 'first-token', 'instance_id': 'i-first', 'state': 'terminated',
            'evidence': {'launch_token': 'first-token', 'region': 'ap-southeast-2',
                         'instance_id': 'i-first', 'state': 'terminated', 'observation_id': 'term-1'}})
        self.assertEqual(closed['next_head']['mode'], 'draining')
        self.assertFalse(closed['inputs_authenticated'])

    def test_spot_termination_does_not_settle_an_active_game(self):
        admission = self.proposal()
        self.events.append(admission['event'])
        self.head = admission['next_head']
        closed = self.observe(1001, event='budget.v2.instance_observed', data={
            'launch_token': 'first-token', 'instance_id': 'i-first', 'state': 'terminated',
            'evidence': {'launch_token': 'first-token', 'region': 'ap-southeast-2',
                         'instance_id': 'i-first', 'state': 'terminated', 'observation_id': 'spot-1'}})
        self.events.append(closed['event'])
        self.head = closed['next_head']
        state, _ = budget.replay(self.root, self.events,
            {'revision': self.head['budget_revision'], 'sha256': self.head['budget_sha256']})
        self.assertFalse(state.games[0].settled)
        with self.assertRaisesRegex(ValueError, 'settled games'):
            self.observe(1001, event='budget.v2.terminate_requested',
                data={'launch_token': 'first-token', 'instance_id': 'i-first'})

    def test_lifecycle_identity_uniqueness_time_and_uncertainty(self):
        first_data = {'launch_token': 'first-token', 'instance_id': 'i-first', 'state': 'terminated',
            'evidence': {'launch_token': 'first-token', 'region': 'ap-southeast-2',
                         'instance_id': 'i-first', 'state': 'terminated', 'observation_id': 'duplicate'}}
        first = self.observe(1001, event='budget.v2.instance_observed', data=first_data)
        rival = self.observe(1001, event='budget.v2.instance_observed', data=first_data)
        store = FakeAtomicStore(self.head)
        self.assertTrue(store.commit(first))
        self.assertFalse(store.commit(rival))
        self.events.append(first['event'])
        self.head = first['next_head']
        second_data = {'launch_token': 'other-token', 'instance_id': 'i-other', 'state': 'terminated',
            'evidence': {'launch_token': 'other-token', 'region': 'ap-southeast-2',
                         'instance_id': 'i-other', 'state': 'terminated', 'observation_id': 'duplicate'}}
        with self.assertRaisesRegex(ValueError, 'identity already recorded'):
            self.observe(1001, event='budget.v2.instance_observed', data=second_data)
        with self.assertRaises(ValueError):
            self.observe(1000, event='budget.v2.instance_observed', data=second_data)
        with self.assertRaises(ValueError):
            model.propose_budget_observation('isolated-trial', self.root, self.events,
                self.head, 'budget.v2.instance_observed', second_data, at=1001,
                write_state='quarantined', owner_context=self.owner)

    def test_drain_rejects_new_launch_but_allows_prior_binding(self):
        root, head = budget.genesis('league-new')
        state, _ = budget.replay(root, [], head)
        atomic_head = {'campaign': 'league-new', 'generation': 'a' * 64, 'epoch': 7,
            'revision': 1, 'owner': 'b' * 64, 'mode': 'active',
            'budget_revision': head['revision'], 'budget_sha256': head['sha256'],
            'budget_upper_micros': budget.projected_upper_micros(state, 1000), 'observed_at': 1000}
        launch = model.propose_budget_observation('isolated-trial', root, [], atomic_head,
            'budget.v2.launch_requested', {'launch_token': 'first-token', 'region': 'ap-southeast-2',
            'max_hourly_usd': '8'}, at=1000, write_state='clean', owner_context=self.owner)
        self.assertFalse(launch['authorizes_launch'])
        events = [launch['event']]
        with self.assertRaisesRegex(ValueError, 'reconcile before retry'):
            model.propose_budget_observation('isolated-trial', root, events, launch['next_head'],
                'budget.v2.launch_requested', {'launch_token': 'first-token', 'region': 'ap-southeast-2',
                'max_hourly_usd': '8'}, at=1000, write_state='clean', owner_context=self.owner)
        drain = model.propose_drain('isolated-trial', root, events, launch['next_head'],
            at=1000, write_state='clean', owner_context=self.owner)
        with self.assertRaisesRegex(ValueError, 'cannot request'):
            model.propose_budget_observation('isolated-trial', root, events, drain['next_head'],
                'budget.v2.launch_requested', {'launch_token': 'other-token', 'region': 'ap-southeast-2',
                'max_hourly_usd': '8'}, at=1000, write_state='clean', owner_context=self.owner)
        binding = model.propose_budget_observation('isolated-trial', root, events, drain['next_head'],
            'budget.v2.instance_bound', {'launch_token': 'first-token', 'instance_id': 'i-first'},
            at=1000, write_state='clean', owner_context=self.owner)
        self.assertEqual(binding['next_head']['mode'], 'draining')
        self.assertFalse(binding['authorizes_launch'])

    def test_unknown_write_permanently_quarantined_in_this_model(self):
        result = model.resolve_model_write('in_flight', 'timeout')
        self.assertEqual(result['write_state'], 'quarantined')
        self.assertFalse(result['authorizes_go'])
        with self.assertRaises(ValueError):
            self.proposal(write_state=result['write_state'])
        with self.assertRaises(ValueError):
            model.resolve_model_write('quarantined', 'verified_no_write')
        with self.assertRaises(ValueError):
            self.drain(write_state='in_flight')


if __name__ == '__main__':
    unittest.main()
