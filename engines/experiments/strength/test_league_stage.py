"""Local-only league stage wiring: real POSIX journals, fake S3, toy runners.

No AWS resources, real engines, real budget authority or score admission.
"""
from pathlib import Path
import json
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

try:
    from . import global_budget as g, run, wave
    from .diagnostic_ledger_bridge import DiagnosticHost
    from .ledger import Journal
    from .league_stage import LeagueStage, OfflineS3, TRIAL_RUNNER
    from .shared_coordinator import SharedBudgetJournal
except ImportError:
    import global_budget as g
    import run
    import wave
    from diagnostic_ledger_bridge import DiagnosticHost
    from ledger import Journal
    from league_stage import LeagueStage, OfflineS3, TRIAL_RUNNER
    from shared_coordinator import SharedBudgetJournal


class MutableClock:
    def __init__(self, value):
        self._value = value
        self._lock = threading.Lock()
    def __call__(self):
        with self._lock:
            return self._value
    def set(self, value):
        with self._lock:
            self._value = value


@unittest.skipUnless(sys.platform == 'linux', 'real POSIX journals and Linux process/socket fixtures required')
class LocalLeagueStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rove4k-local-league-stage-')
        self.root = Path(self.temp.name).resolve()
        self.client = OfflineS3()
        self.client.doc['campaign'] = 'league-test'
        self.client.doc['opening']['prior_compute_usd'] = '99'
        self.client._publish(g.canonical(self.client.doc))
        self.store = g.S3SharedBudget(self.client, bucket='league-campaign-bucket',
            key='league-test/shared/budget.json', account='123456789012',
            region='ap-southeast-2', campaign='league-test')
        self.root_anchor = g.Anchor(-1, g.ZERO, self.store.authority,
                                    g.digest(self.client.doc['opening']))
        self.shared_journal = Journal(self.root / 'shared.jsonl', 'league-test')
        self.owner = SharedBudgetJournal(self.store, self.shared_journal, self.root_anchor)
        self.event_num = 0
        for token, instance in (('first-token', 'i-123'), ('other-token', 'i-456')):
            self.record('budget.v2.launch_requested', {'launch_token': token,
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
            self.record('budget.v2.instance_bound', {'launch_token': token, 'instance_id': instance})
        self.main_journal = Journal(self.root / 'main.jsonl', 'league-test')
        self.intent = run.IntentJournalOwner(self.root / 'intent.jsonl', 'league-test', 'i-123')
        marker = self.main_journal.append('campaign.intent_journal', {
            'path': str(self.intent.path), 'instance_id': self.intent.instance_id,
            'boot_id': self.intent.boot_id, 'device': self.intent.journal.identity[0],
            'inode': self.intent.journal.identity[1]})
        self.intent.bind_registration(self.main_journal, marker)
        self.host = DiagnosticHost('i-123', self.intent.boot_id, 'first-token')
        self.clock = MutableClock(1000)

    def tearDown(self):
        self.intent.close()
        self.main_journal.close()
        self.shared_journal.close()
        self.temp.cleanup()

    def record(self, event, data, at=1000):
        self.event_num += 1
        return self.owner.record(request_id=f'launch-setup-{self.event_num:06d}',
                                 event=event, data=data, at=at)

    def job(self, index):
        game = f'game-{index}'
        meta = {'campaign': 'league-test', 'pair': f'pair-{index}', 'game': game,
                'attempt': 0, 'attempt_id': f'attempt-{index:08d}-first', 'slot_id': index,
                'instance_id': self.host.instance_id, 'boot_id': self.host.boot_id,
                'launch_token': self.host.launch_token}
        return wave.WaveJob(game, (sys.executable, '-I', '-c', TRIAL_RUNNER, 'ok'), {}, meta, self.root / game)

    def stage(self, profile='test-p16'):
        return LeagueStage(self.owner, self.host, profile, read_boot=lambda: self.host.boot_id,
                           now_utc=self.clock, now_mono=time.monotonic, observe_interval=0.05)

    def test_two_host_upper_crossing_denies_new_go_and_preserves_started_game(self):
        events = []
        def on_event(name, job, observed):
            events.append((name, job.identity))
            if name == 'released' and job.identity == 'game-0':
                self.clock.set(1226)
        result = self.stage().run_wave([self.job(0), self.job(1)], 8,
            intent_owner=self.intent, on_event=on_event, local_trial=True)
        self.assertIn(('released', 'game-0'), events)
        self.assertIn(('completed', 'game-0'), events)
        rows = result['results']
        self.assertEqual(rows[0]['gate_receipt'], 'matched')
        self.assertEqual(rows[0]['returncode'], 0)
        self.assertFalse(rows[0]['cleanup_forced'])
        self.assertNotIn(('released', 'game-1'), events)
        self.assertEqual(rows[1]['gate_transport'], 'not_attempted')
        self.assertFalse(result['scored_go_allowed'])
        self.assertFalse(result['remote_authority_verified'])
        self.assertFalse(result['placement_verified'])
        self.assertFalse(result['billing_verified'])
        snapshot = self.store.load(self.root_anchor)
        released = [e['data']['game_id'] for e in snapshot.rows
                    if e['event'] == 'budget.v2.game_release_authorized']
        self.assertEqual(released, ['game-0'])

    def test_score_route_is_never_implicitly_enabled(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self.stage().run_wave([self.job(0)], 3, intent_owner=self.intent)
        self.assertFalse((self.root / 'game-0').exists())

    def test_eleven_p16_toy_runners_use_actual_wave_and_remain_unscored(self):
        events = []
        result = self.stage().run_wave([self.job(i) for i in range(11)], 20,
            intent_owner=self.intent, local_trial=True,
            on_event=lambda name, job, observed: events.append((name, job.identity)))
        self.assertEqual(len(result['results']), 11)
        self.assertTrue(all(row['returncode'] == 0 and row['gate_receipt'] == 'matched'
                            and not row['cleanup_forced'] for row in result['results']),
                        [(row.get('gate_transport'), row.get('drain_reason'), row.get('returncode'))
                         for row in result['results']])
        self.assertEqual(len([row for row in events if row[0] == 'released']), 11)
        self.assertFalse(result['placement_verified'])
        self.assertFalse(result['scored_go_allowed'])
        snapshot = self.store.load(self.root_anchor)
        self.assertEqual(len([e for e in snapshot.rows
                              if e['event'] == 'budget.v2.game_release_authorized']), 11)
        self.assertFalse(any(e['event'] == 'budget.v2.game_settled' for e in snapshot.rows))

    def test_thirteen_instance_hours_is_not_a_budget_deadline(self):
        client = OfflineS3()
        client.doc['campaign'] = 'league-test'
        client._publish(g.canonical(client.doc))
        store = g.S3SharedBudget(client, bucket='league-campaign-bucket',
            key='league-test/shared/budget.json', account='123456789012',
            region='ap-southeast-2', campaign='league-test')
        anchor = g.Anchor(-1, g.ZERO, store.authority, g.digest(client.doc['opening']))
        with Journal(self.root / 'other-shared.jsonl', 'league-test') as journal:
            owner = SharedBudgetJournal(store, journal, anchor)
            number = 0
            for token, instance in (('first-token', 'i-123'), ('other-token', 'i-456')):
                for event, data in (('budget.v2.launch_requested', {'launch_token': token,
                        'region': 'ap-southeast-2', 'max_hourly_usd': '1'}),
                        ('budget.v2.instance_bound', {'launch_token': token, 'instance_id': instance})):
                    number += 1
                    owner.record(request_id=f'other-launch-{number:06}', event=event, data=data, at=1000)
            elapsed = MutableClock(1000 + 13 * 3600)
            stage = LeagueStage(owner, self.host, 'test-p192', read_boot=lambda: self.host.boot_id,
                                now_utc=elapsed, now_mono=time.monotonic, observe_interval=.05)
            result = stage.run_wave([self.job(0)], 5, intent_owner=self.intent, local_trial=True)
            self.assertEqual(result['results'][0]['returncode'], 0)
            self.assertEqual(result['results'][0]['gate_receipt'], 'matched')
            self.assertFalse(result['scored_go_allowed'])
            self.assertFalse(result['billing_verified'])
            self.assertLess(float(result['budget']['observations'][0]['total_upper_usd']), 120)

    def test_p192_rejects_two_concurrent_slots_before_spawn(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self.stage('test-p192').run_wave([self.job(0), self.job(1)], 3,
                                             intent_owner=self.intent, local_trial=True)
        self.assertFalse((self.root / 'game-0').exists())

    def test_p16_rejects_twelfth_or_duplicate_slots_before_spawn(self):
        too_many = [self.job(i) for i in range(12)]
        with self.assertRaises((ValueError, RuntimeError)):
            self.stage().run_wave(too_many, 3, intent_owner=self.intent, local_trial=True)
        self.assertFalse((self.root / 'game-0').exists())
        duplicate = self.job(1)
        duplicate.start_job['slot_id'] = 0
        with self.assertRaises((ValueError, RuntimeError)):
            self.stage().run_wave([self.job(0), duplicate], 3, intent_owner=self.intent, local_trial=True)
        self.assertFalse((self.root / 'game-0').exists())

    def test_budget_drain_revokes_approved_but_unsent_intent(self):
        stage = self.stage()
        original_poll = self.intent.poll
        held = []
        crossed = threading.Event()
        def delay_until_observed():
            held.extend(original_poll())
            if held and not crossed.is_set():
                self.clock.set(1226)
                crossed.set()
            if not stage._mailbox._drain_requested.is_set():
                return []
            decisions = list(held)
            held.clear()
            return decisions
        events = []
        with patch.object(self.intent, 'poll', side_effect=delay_until_observed):
            result = stage.run_wave([self.job(0)], 8, intent_owner=self.intent,
                local_trial=True, on_event=lambda name, job, observed: events.append(name))
        self.assertTrue(crossed.is_set())
        self.assertTrue(result['budget']['draining'])
        self.assertNotIn('released', events)
        self.assertEqual(result['results'][0]['gate_transport'], 'not_attempted')
        self.assertFalse(result['scored_go_allowed'])

    def test_remote_cap_does_not_turn_local_trial_fence_into_scored_authority(self):
        # The two declared hosts share a journal, but this is one process and
        # the unmodified local trial deliberately has no cross-host fence.
        # Record the second host's limit observation after the first host has
        # an intent but before its local gate checks that intent.  Either a
        # future stricter trial may cancel or the current trial may issue toy
        # GO.  Neither outcome is proof of cross-host fencing or scored GO.
        stage = LeagueStage(self.owner, self.host, 'test-p16', read_boot=lambda: self.host.boot_id,
                            now_utc=self.clock, now_mono=time.monotonic,
                            observe_interval=60.0, window_seconds=10.0)
        with self.assertRaisesRegex(ValueError, 'restricted to explicit local trials'):
            stage.run_wave([self.job(0)], 5, intent_owner=self.intent)
        self.assertFalse((self.root / 'game-0').exists())

        original_poll = self.intent.poll
        marked = []
        def cap_before_local_gate():
            decisions = original_poll()
            if decisions and not marked:
                self.record('budget.v2.limit_confirmed', {
                    'actual_usd': '120',
                    'evidence': {'observation_id': 'host-b-cap-observation',
                                 'instance_id': 'i-456', 'source': 'test'}}, at=1001)
                marked.append(True)
            return decisions

        events = []
        with patch.object(self.intent, 'poll', side_effect=cap_before_local_gate):
            result = stage.run_wave([self.job(0)], 8, intent_owner=self.intent, local_trial=True,
                on_event=lambda name, job, observed: events.append(name))
        self.assertEqual(marked, [True])
        if 'released' in events:
            self.assertIn('completed', events)
            self.assertEqual(result['results'][0]['gate_receipt'], 'matched')
        else:
            self.assertEqual(result['results'][0]['gate_transport'], 'not_attempted')
        self.assertFalse(result['results'][0]['cleanup_forced'])
        self.assertFalse(result['scored_go_allowed'])
        self.assertFalse(result['remote_authority_verified'])
        snapshot = self.store.load(self.root_anchor)
        self.assertTrue(any(event['event'] == 'budget.v2.limit_confirmed' for event in snapshot.rows))

    def test_busy_budget_observer_does_not_stall_wave_selector(self):
        stage = self.stage()
        authorized = threading.Event()
        blocked = threading.Event()
        unblock = threading.Event()
        aborted = threading.Event()
        original_record = self.owner.record
        original_poll = self.intent.poll
        original_send = socket.socket.sendall
        held = []
        outcome, errors, observer_threads = [], [], []
        def slow_record(*args, **kwargs):
            event = kwargs.get('event')
            if event == 'budget.v2.observe' and authorized.is_set() and not blocked.is_set():
                self.clock.set(1226)
                blocked.set()
                if not unblock.wait(8):
                    raise TimeoutError('test observation was not released')
            value = original_record(*args, **kwargs)
            if event == 'budget.v2.game_release_authorized':
                authorized.set()
            return value
        def delayed_intent():
            held.extend(original_poll())
            if held and authorized.is_set() and not observer_threads:
                def observe():
                    try:
                        stage._mailbox._record_observation()
                    except Exception as error:
                        errors.append(error)
                observer = threading.Thread(target=observe)
                observer_threads.append(observer)
                observer.start()
            if not blocked.is_set():
                return []
            decisions = list(held)
            held.clear()
            return decisions
        def observe_send(sock, data, *args, **kwargs):
            value = original_send(sock, data, *args, **kwargs)
            if data == b'ABORT\n':
                aborted.set()
            return value
        def run_stage():
            try:
                outcome.append(stage.run_wave([self.job(0)], 8, intent_owner=self.intent,
                                              local_trial=True))
            except Exception as error:
                errors.append(error)
        with patch.object(self.owner, 'record', side_effect=slow_record), \
             patch.object(self.intent, 'poll', side_effect=delayed_intent), \
             patch.object(socket.socket, 'sendall', new=observe_send):
            thread = threading.Thread(target=run_stage)
            thread.start()
            try:
                self.assertTrue(blocked.wait(5), 'observation did not enter slow I/O')
                self.assertTrue(aborted.wait(4), 'selector failed to expire its fence while observation was blocked')
            finally:
                unblock.set()
                thread.join(10)
                for observer in observer_threads:
                    observer.join(10)
        self.assertTrue(observer_threads)
        self.assertTrue(all(not observer.is_alive() for observer in observer_threads))
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(outcome[0]['results'][0]['gate_transport'], 'not_attempted')
        self.assertFalse(outcome[0]['scored_go_allowed'])
        self.assertFalse(outcome[0]['billing_verified'])

    def test_busy_observer_then_safe_budget_allows_retry(self):
        stage = self.stage()
        authorized = threading.Event()
        blocked = threading.Event()
        unblock = threading.Event()
        aborted = threading.Event()
        original_record = self.owner.record
        original_poll = self.intent.poll
        original_send = socket.socket.sendall
        held = []
        outcome, errors, observer_threads = [], [], []
        def slow_record(*args, **kwargs):
            event = kwargs.get('event')
            if event == 'budget.v2.observe' and authorized.is_set() and not blocked.is_set():
                blocked.set()
                if not unblock.wait(8):
                    raise TimeoutError('test observation was not released')
            value = original_record(*args, **kwargs)
            if event == 'budget.v2.game_release_authorized':
                authorized.set()
            return value
        def delayed_intent():
            held.extend(original_poll())
            if held and authorized.is_set() and not observer_threads:
                def observe():
                    try:
                        stage._mailbox._record_observation()
                    except Exception as error:
                        errors.append(error)
                observer = threading.Thread(target=observe)
                observer_threads.append(observer)
                observer.start()
            if not blocked.is_set():
                return []
            decisions = list(held)
            held.clear()
            return decisions
        def observe_send(sock, data, *args, **kwargs):
            value = original_send(sock, data, *args, **kwargs)
            if data.startswith(b'GO2 '):
                aborted.set()
            return value
        def run_stage():
            try:
                outcome.append(stage.run_wave([self.job(0)], 8, intent_owner=self.intent,
                                              local_trial=True))
            except Exception as error:
                errors.append(error)
        with patch.object(self.owner, 'record', side_effect=slow_record), \
             patch.object(self.intent, 'poll', side_effect=delayed_intent), \
             patch.object(socket.socket, 'sendall', new=observe_send):
            thread = threading.Thread(target=run_stage)
            thread.start()
            try:
                self.assertTrue(blocked.wait(5), 'observation did not enter slow I/O')
                self.assertFalse(aborted.wait(.15), 'GO was sent while the observation held the gate')
            finally:
                unblock.set()
                thread.join(10)
                for observer in observer_threads:
                    observer.join(10)
        self.assertTrue(observer_threads)
        self.assertTrue(all(not observer.is_alive() for observer in observer_threads))
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(outcome[0]['results'][0]['gate_transport'], 'sent')
        self.assertEqual(outcome[0]['results'][0]['gate_receipt'], 'matched')
        self.assertEqual(outcome[0]['results'][0]['returncode'], 0)
        self.assertFalse(outcome[0]['scored_go_allowed'])
        self.assertFalse(outcome[0]['billing_verified'])

    def test_local_drain_observation_is_ordered_with_inflight_send(self):
        stage = self.stage()
        original_send = socket.socket.sendall
        drain_done = threading.Event()
        started = threading.Event()
        threads, timeline, observed_early, mailboxes = [], [], [], []
        def wrapped_send(sock, data, *args, **kwargs):
            if not data.startswith(b'GO2 '):
                return original_send(sock, data, *args, **kwargs)
            self.clock.set(1226)
            timeline.append('send-entered')
            def mark_drain():
                started.set()
                mailbox = stage._mailbox
                mailboxes.append(mailbox)
                mailbox.on_drain('shared_budget_reached', None, {})
                observed_early.append(mailbox._drain.is_set())
                timeline.append('drain-requested')
                drain_done.set()
            thread = threading.Thread(target=mark_drain)
            threads.append(thread)
            thread.start()
            if not started.wait(2):
                raise RuntimeError('drain test thread did not start')
            # The drain request itself is nonblocking; its observation is
            # committed after the guarded send. This is only local ordering,
            # not atomicity with an invoice or another host.
            if not drain_done.wait(2):
                raise RuntimeError('drain notification blocked the selector')
            value = original_send(sock, data, *args, **kwargs)
            timeline.append('send-completed')
            return value
        with patch.object(socket.socket, 'sendall', new=wrapped_send):
            result = stage.run_wave([self.job(0)], 5, intent_owner=self.intent, local_trial=True)
        for thread in threads:
            thread.join(3)
        self.assertTrue(threads)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(observed_early, [False])
        self.assertLess(timeline.index('drain-requested'), timeline.index('send-completed'))
        self.assertTrue(mailboxes[0]._drain.is_set())
        self.assertEqual(result['results'][0]['gate_receipt'], 'matched')
        self.assertFalse(result['results'][0]['cleanup_forced'])
        self.assertFalse(result['scored_go_allowed'])
        self.assertFalse(result['billing_verified'])

    def test_launch_identity_is_distinct_from_budget_game_identity(self):
        base = self.job(0)
        job = wave.WaveJob('launch-attempt-00001', base.argv, base.env, dict(base.start_job), base.out)
        events = []
        result = self.stage().run_wave([job], 5, intent_owner=self.intent, local_trial=True,
            on_event=lambda name, item, obs: events.append((name, item.identity)))
        self.assertEqual(result['results'][0]['returncode'], 0)
        self.assertEqual(result['results'][0]['gate_receipt'], 'matched')
        self.assertIn(('released', 'launch-attempt-00001'), events)
        self.assertFalse(result['scored_go_allowed'])
        rows = self.store.load(self.root_anchor).rows
        admitted = [row['data']['game_id'] for row in rows if row['event'] == 'budget.v2.game_admitted']
        authorized = [row['data']['game_id'] for row in rows if row['event'] == 'budget.v2.game_release_authorized']
        self.assertEqual(admitted, ['game-0'])
        self.assertEqual(authorized, ['game-0'])

    def test_duplicate_attempt_ids_rejected_before_spawn(self):
        first, second = self.job(0), self.job(1)
        second.start_job['attempt_id'] = first.start_job['attempt_id']
        with self.assertRaises((ValueError, TypeError)):
            self.stage().run_wave([first, second], 3, intent_owner=self.intent, local_trial=True)
        self.assertFalse((self.root / 'game-0').exists())
        self.assertFalse((self.root / 'game-1').exists())

    def test_preflight_limit_closes_without_spawning(self):
        self.clock.set(1226)
        result = self.stage().run_wave([self.job(0)], 3,
                                       intent_owner=self.intent, local_trial=True)
        self.assertEqual(result['results'], [])
        self.assertTrue(result['budget']['draining'])
        self.assertFalse(result['scored_go_allowed'])
        self.assertFalse((self.root / 'game-0').exists())

    def test_job_bindings_reject_forgery_before_spawning(self):
        for index, (field, bad) in enumerate((('campaign', 'other-campaign'), ('instance_id', 'i-456'),
                           ('boot_id', 'other-boot'), ('launch_token', 'other-token'),
                           ('game', 'invalid game'), ('slot_id', True), ('attempt', -1),
                           ('pair', None))):
            with self.subTest(field=field):
                job = self.job(index)
                job.start_job[field] = bad
                with self.assertRaises((ValueError, TypeError)):
                    self.stage().run_wave([job], 3, intent_owner=self.intent, local_trial=True)
                self.assertFalse((self.root / f'game-{index}').exists())

    def test_concurrent_use_of_one_stage_is_rejected_before_remote_or_spawn(self):
        entered, release = threading.Event(), threading.Event()
        original_put = self.client.put_file_if_match
        def hold_first_observation(bucket, key, path, sha, etag, *, expected_owner):
            event = json.loads(Path(path).read_bytes())['events'][-1]
            if event['event'] == 'budget.v2.observe' and not entered.is_set():
                entered.set()
                if not release.wait(8):
                    raise TimeoutError('test did not release preflight')
            return original_put(bucket, key, path, sha, etag, expected_owner=expected_owner)
        self.client.put_file_if_match = hold_first_observation
        stage = self.stage()
        outcome = []
        def first_run():
            try:
                outcome.append(stage.run_wave([self.job(0)], 5, intent_owner=self.intent, local_trial=True))
            except BaseException as error:
                outcome.append(error)
        thread = threading.Thread(target=first_run)
        thread.start()
        try:
            self.assertTrue(entered.wait(5), 'first stage did not enter preflight')
            before = self.client.seq
            with self.assertRaises((ValueError, RuntimeError)):
                stage.run_wave([self.job(1)], 3, intent_owner=self.intent, local_trial=True)
            self.assertEqual(self.client.seq, before)
            self.assertFalse((self.root / 'game-1').exists())
        finally:
            release.set()
            thread.join(8)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcome), 1)
        if isinstance(outcome[0], BaseException):
            raise outcome[0]
        self.assertEqual(outcome[0]['results'][0]['returncode'], 0)
        self.assertFalse(outcome[0]['scored_go_allowed'])

    def test_arbitrary_runner_and_non_offline_store_are_rejected(self):
        base = self.job(0)
        arbitrary = wave.WaveJob(base.identity, (sys.executable, '-c', 'print(1)'), {},
                                 dict(base.start_job), base.out)
        with self.assertRaises((ValueError, TypeError)):
            self.stage().run_wave([arbitrary], 3, intent_owner=self.intent, local_trial=True)
        self.assertFalse(base.out.exists())
        # Exact OfflineS3 transport is required: an arbitrary network-capable
        # S3-shaped object must not be accepted for local trial GO.
        original = self.store.client
        class NetworkShapedClient:
            pass
        try:
            self.store.client = NetworkShapedClient()
            with self.assertRaises((ValueError, TypeError)):
                self.stage()
        finally:
            self.store.client = original

    def test_blocked_admission_owner_handle_is_kept_and_no_late_authorization(self):
        blocked = threading.Event()
        release = threading.Event()
        original_put = self.client.put_file_if_match
        def hold_admission(bucket, key, path, sha, etag, *, expected_owner):
            event = json.loads(Path(path).read_bytes())['events'][-1]
            if event['event'] == 'budget.v2.game_admitted':
                blocked.set()
                if not release.wait(8):
                    raise TimeoutError('test did not release the fake S3 worker')
            return original_put(bucket, key, path, sha, etag, expected_owner=expected_owner)
        self.client.put_file_if_match = hold_admission
        stage = self.stage()
        try:
            result = stage.run_wave([self.job(0)], .8, intent_owner=self.intent, local_trial=True)
            self.assertTrue(blocked.is_set())
            self.assertFalse(result['worker_closed'])
            self.assertEqual(result['results'][0]['gate_transport'], 'not_attempted')
            self.assertTrue(self.owner.blocked)
            with self.assertRaises(ValueError):
                stage.run_wave([self.job(1)], 1, intent_owner=self.intent, local_trial=True)
        finally:
            release.set()
        self.assertTrue(stage.close_pending_worker(5))
        snapshot = self.store.load(self.root_anchor)
        self.assertTrue(any(e['event'] == 'budget.v2.game_admitted' for e in snapshot.rows))
        self.assertFalse(any(e['event'] == 'budget.v2.game_release_authorized' for e in snapshot.rows))
        self.assertFalse(any(e['event'] == 'budget.v2.game_settled' for e in snapshot.rows))

    def test_uncertain_preflight_write_never_spawns_a_runner(self):
        self.client.timeout_after_write = True
        with self.assertRaises(g.LedgerUncertain):
            self.stage().run_wave([self.job(0)], 4, intent_owner=self.intent, local_trial=True)
        self.assertTrue(self.owner.blocked)
        self.assertFalse((self.root / 'game-0').exists())
        self.assertEqual(self.owner.inspect_pending()['status'], 'observed')
        self.assertNotIn('budget.v2.game_release_observed',
                         [e['event'] for e in self.store.load(self.root_anchor).rows])

    def test_uncertain_game_admission_never_becomes_go(self):
        original_put = self.client.put_file_if_match
        def uncertain_admission(bucket, key, path, sha, etag, *, expected_owner):
            event = json.loads(Path(path).read_bytes())['events'][-1]
            if event['event'] == 'budget.v2.game_admitted':
                self.client.timeout_after_write = True
            return original_put(bucket, key, path, sha, etag, expected_owner=expected_owner)
        self.client.put_file_if_match = uncertain_admission
        result = self.stage().run_wave([self.job(0)], 4, intent_owner=self.intent, local_trial=True)
        self.assertTrue(self.owner.blocked)
        self.assertEqual(result['results'][0]['gate_transport'], 'not_attempted')
        self.assertFalse(result['scored_go_allowed'])
        self.assertFalse(result['remote_authority_verified'])
        self.assertEqual(self.owner.inspect_pending()['status'], 'observed')
        self.assertNotIn('budget.v2.game_release_observed',
                         [e['event'] for e in self.store.load(self.root_anchor).rows])


if __name__ == '__main__':
    unittest.main()
