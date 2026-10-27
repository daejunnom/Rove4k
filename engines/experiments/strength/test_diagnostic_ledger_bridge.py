"""Wave-to-ledger diagnostic wiring; fake S3 and toy runners only."""
import hashlib
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from . import global_budget as g, wave, run, diagnostic_ledger_bridge as bridge_module
    from .diagnostic_ledger_bridge import DiagnosticHost, DiagnosticLedgerMailbox, binding
    from .ledger import Journal
    from .shared_coordinator import SharedBudgetJournal
    from .test_global_budget import FakeS3
    from .test_wave import ASYNC_TOY
except ImportError:
    import diagnostic_ledger_bridge as bridge_module
    import global_budget as g
    import wave
    import run
    from diagnostic_ledger_bridge import DiagnosticHost, DiagnosticLedgerMailbox, binding
    from ledger import Journal
    from shared_coordinator import SharedBudgetJournal
    from test_global_budget import FakeS3
    from test_wave import ASYNC_TOY

BOOT = '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb'


@unittest.skipUnless(sys.platform == 'linux', 'Linux process/socket and POSIX journal required')
class DiagnosticBridgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='rove4k-bridge-')
        self.root = Path(self.directory.name)
        self.client = FakeS3()
        self.store = g.S3SharedBudget(self.client, bucket='valid-campaign-bucket',
            key='test-campaign/shared/budget.json', account='123456789012',
            region='ap-southeast-2', campaign='test-campaign')
        self.anchor = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(self.client.doc['opening']))
        self.journal = Journal(self.root / 'journal.jsonl', 'test-campaign')
        self.owner = SharedBudgetJournal(self.store, self.journal, self.anchor)
        self.host = DiagnosticHost('i-123', BOOT, 'first-token')
        self.script = self.root / 'toy.py'
        self.script.write_text(ASYNC_TOY)
        self.bridge = None
        self.intent_owner = None
        self.intent_main = None

    def tearDown(self):
        if self.bridge is not None:
            self.assertTrue(self.bridge.close(2), 'worker must finish before journal is closed')
        if self.intent_owner is not None:
            self.intent_owner.close()
        if self.intent_main is not None:
            self.intent_main.close()
        self.journal.close()
        self.directory.cleanup()

    def make_bridge(self, **kwargs):
        self.bridge = DiagnosticLedgerMailbox(self.owner, self.host, read_boot=lambda: BOOT,
                                              now_utc=lambda: 1000, **kwargs)
        return self.bridge

    def make_intent_owner(self):
        """Use the real registered POSIX writer; it grants no GO authority."""
        self.intent_main = Journal(self.root / 'wave-main.jsonl', 'test-campaign')
        self.intent_owner = run.IntentJournalOwner(self.root / 'release-intents.jsonl', 'test-campaign', 'i-123')
        marker = self.intent_main.append('campaign.intent_journal', {
            'path': str(self.intent_owner.path), 'instance_id': self.intent_owner.instance_id,
            'boot_id': self.intent_owner.boot_id, 'device': self.intent_owner.journal.identity[0],
            'inode': self.intent_owner.journal.identity[1]})
        self.intent_owner.bind_registration(self.intent_main, marker)
        return self.intent_owner

    def job(self, identity='game-1', attempt='attempt-00000001', fence='diag-fence-1'):
        return wave.WaveJob(identity, (sys.executable, str(self.script), 'ok'), {},
            {'attempt_id': attempt, 'probe_fence_id': fence, 'boot_id': BOOT,
             'instance_id': 'i-123', 'launch_token': 'first-token'}, self.root / identity)

    def test_real_wave_and_journal_worker_do_not_block_started_sibling(self):
        release_store = threading.Event()
        worker_entered = threading.Event()
        original = self.client.put_file_if_match
        def slow_store(*args, **kwargs):
            worker_entered.set()
            if not release_store.wait(4):
                raise TimeoutError('selector stopped while journal worker was blocked')
            return original(*args, **kwargs)
        self.client.put_file_if_match = slow_store
        bridge = self.make_bridge()
        first = wave.WaveJob('game-0', (sys.executable, str(self.script), 'ok'), {},
                             {'campaign': 'test-campaign', 'pair': 'pair-0', 'game': 'game-0',
                              'attempt': 0, 'attempt_id': 'attempt-00000000'}, self.root / 'game-0')
        second = self.job()
        events, transports = [], []
        intent_owner = self.make_intent_owner()

        class FixtureMailbox:
            """Test-only local approval for game-0; bridge itself always denies."""
            def __init__(self):
                self.decision = None
            def request(self, job, observed):
                if job.identity == first.identity:
                    payload = json.dumps({'identity': job.identity, 'start_job': job.start_job},
                        sort_keys=True, allow_nan=False, separators=(',', ':')).encode()
                    now = time.monotonic()
                    self.decision = wave.AsyncGateDecision(job.identity, True, wave.ReleaseFence(
                        job.identity, 'fixture-fence', hashlib.sha256(payload).hexdigest(), now, now + 3))
                else:
                    bridge.request(job, observed)
            def poll(self):
                decision, self.decision = self.decision, None
                return ([decision] if decision else []) + bridge.poll()

        def on_event(name, job, observation):
            events.append((name, job.identity))
            if (name, job.identity) == ('completed', first.identity):
                release_store.set()

        try:
            results = wave.WaveExecutor().run_wave([first, second], 5,
                async_authorizer=FixtureMailbox(), observe_transport=lambda job, obs: transports.append((job.identity, obs['gate_transport'])),
                intent_owner=intent_owner, on_drain=bridge.on_drain, on_event=on_event)
        finally:
            release_store.set()
        self.assertTrue(worker_entered.is_set())
        self.assertIn(('completed', first.identity), events)
        self.assertEqual(results[0]['returncode'], 0)
        self.assertFalse(results[0]['cleanup_forced'])
        self.assertTrue(results[0]['gate_intent_resolved'])
        intent_rows = run.ledger.read_journal(self.root / 'release-intents.jsonl', 'test-campaign')
        self.assertEqual(len(intent_rows), 1)
        self.assertEqual(intent_rows[0]['event'], 'game.release_intent')
        self.assertEqual(results[0]['gate_intent_sha256'], intent_rows[0]['sha256'])
        self.assertEqual(intent_rows[0]['data']['intent']['identity'], first.identity)
        self.assertEqual(results[1]['status'], 'cancelled_before_go')
        self.assertEqual(results[1]['gate_transport'], 'not_attempted')
        self.assertEqual(transports, [('game-0', 'sent')])
        self.assertFalse(bridge.provides_go_authority)
        snapshot = self.store.load(self.anchor)
        self.assertEqual(len(snapshot.rows), 1)
        self.assertEqual(snapshot.rows[0]['event'], 'budget.v2.observe')
        self.assertEqual(snapshot.rows[0]['data']['job_sha256'], binding(second, self.host)['job_sha256'])
        self.assertEqual(snapshot.rows[0]['data']['probe_fence_id'], 'diag-fence-1')
        self.assertEqual(snapshot.rows[0]['data']['boot_id'], BOOT)
        self.assertEqual([x['event'] for x in self.journal.rows], ['shared.genesis', 'shared.intent', 'shared.commit'])

    def test_uncertain_store_write_denies_without_retry_or_false_settlement(self):
        self.client.timeout_after_write = True
        bridge = self.make_bridge()
        intent_owner = self.make_intent_owner()
        result = wave.WaveExecutor().run_wave([self.job()], 4, async_authorizer=bridge,
                                              intent_owner=intent_owner, observe_transport=bridge.transport,
                                              on_drain=bridge.on_drain)[0]
        self.assertEqual(result['gate_transport'], 'not_attempted')
        self.assertEqual(intent_owner.journal.rows, [])
        self.assertTrue(self.owner.blocked)
        self.assertEqual(bridge.records()[0]['status'], 'unresolved')
        version = self.client.seq
        self.assertEqual(self.owner.inspect_pending()['status'], 'observed')
        self.assertEqual(self.client.seq, version)
        self.assertEqual(json.loads(self.client.raw)['events'][0]['event'], 'budget.v2.observe')

    def test_binding_rejects_other_host_and_duplicate_fence(self):
        bridge = self.make_bridge()
        job = self.job()
        ready = {'ready_monotonic': 123.0, 'ready': {'event': 'READY', 'job': job.start_job}}
        with self.assertRaisesRegex(ValueError, 'pinned diagnostic host'):
            binding(wave.WaveJob('game-x', job.argv, {}, dict(job.start_job, boot_id='00000000-0000-0000-0000-000000000000'),
                                self.root / 'game-x'), self.host)
        bridge.request(job, ready)
        with self.assertRaisesRegex(ValueError, 'duplicate game'):
            bridge.request(self.job('game-2', 'attempt-00000002', 'diag-fence-1'), {'ready_monotonic': 123.0, 'ready': {'event': 'READY', 'job': self.job('game-2', 'attempt-00000002', 'diag-fence-1').start_job}})

    def test_ready_snapshot_remains_the_hash_source_during_mutation(self):
        bridge = self.make_bridge()
        job = self.job()
        ready_job = json.loads(json.dumps(job.start_job))
        expected = binding(job, self.host)['job_sha256']
        original = bridge_module._binding
        def mutate_then_bind(identity, frozen_meta, host):
            job.start_job['after_snapshot'] = 'mutated'
            return original(identity, frozen_meta, host)
        with patch.object(bridge_module, '_binding', side_effect=mutate_then_bind):
            bridge.request(job, {'ready_monotonic': 123.0, 'ready': {'event': 'READY', 'job': ready_job}})
        deadline = time.monotonic() + 2
        while not bridge.records() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(bridge.records()[0]['binding']['job_sha256'], expected)
        self.assertNotEqual(binding(job, self.host)['job_sha256'], expected)

    def test_mutated_ready_job_is_rejected_and_no_request_is_written(self):
        bridge = self.make_bridge()
        job = self.job()
        copied = json.loads(json.dumps(job.start_job))
        job.start_job['additional'] = 'mutated-after-ready'
        with self.assertRaisesRegex(ValueError, 'READY job differs'):
            bridge.request(job, {'ready_monotonic': 123.0, 'ready': {'event': 'READY', 'job': copied}})
        self.assertEqual(self.client.seq, 1)
        self.assertEqual(bridge.records(), ())

    def test_close_during_inflight_write_keeps_journal_until_worker_joins(self):
        entered, release = threading.Event(), threading.Event()
        original = self.client.put_file_if_match
        def slow_store(*args, **kwargs):
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test store not released')
            return original(*args, **kwargs)
        self.client.put_file_if_match = slow_store
        bridge = self.make_bridge()
        job = self.job()
        bridge.request(job, {'ready_monotonic': 123.0, 'ready': {'event': 'READY', 'job': job.start_job}})
        self.assertTrue(entered.wait(2))
        try:
            self.assertFalse(bridge.close(0))
            with self.assertRaisesRegex(RuntimeError, 'closed or unavailable'):
                bridge.poll()
            self.assertFalse(self.journal.file.closed)
        finally:
            release.set()
        self.assertTrue(bridge.close(2))
        self.assertEqual(self.client.seq, 2)
        self.assertEqual([row['event'] for row in self.journal.rows], ['shared.genesis', 'shared.intent', 'shared.commit'])

    def test_request_limit_applies_to_entire_mailbox_lifetime(self):
        bridge = self.make_bridge(max_pending=1)
        job = self.job()
        bridge.request(job, {'ready_monotonic': 123.0, 'ready': {'event': 'READY', 'job': job.start_job}})
        next_job = self.job('game-2', 'attempt-00000002', 'diag-fence-2')
        with self.assertRaisesRegex(ValueError, 'wave request limit'):
            bridge.request(next_job, {'ready_monotonic': 123.0, 'ready': {'event': 'READY', 'job': next_job.start_job}})

    def test_boot_change_is_quarantined_before_ledger_write(self):
        values = iter([BOOT, '00000000-0000-0000-0000-000000000000'])
        self.bridge = DiagnosticLedgerMailbox(self.owner, self.host, read_boot=lambda: next(values), now_utc=lambda: 1000)
        intent_owner = self.make_intent_owner()
        result = wave.WaveExecutor().run_wave([self.job()], 4, async_authorizer=self.bridge,
                                              intent_owner=intent_owner, observe_transport=self.bridge.transport,
                                              on_drain=self.bridge.on_drain)[0]
        self.assertEqual(result['gate_transport'], 'not_attempted')
        self.assertEqual(intent_owner.journal.rows, [])
        self.assertEqual(self.client.seq, 1)
        self.assertEqual(self.bridge.records()[0]['status'], 'unresolved')
        self.assertFalse(self.owner.blocked)


if __name__ == '__main__':
    unittest.main()
