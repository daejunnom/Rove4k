"""Shared coordinator integration with the actual ledger and fsync journal.

S3, clocks, evidence and processes are fixtures; these tests do not authorize GO.
"""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import global_budget as g
    from . import shared_coordinator as coordinator
    from .ledger import Journal
    from .shared_coordinator import CoordinatorBlocked, SharedBudgetJournal
    from .test_global_budget import FakeS3
except ImportError:
    import global_budget as g
    import shared_coordinator as coordinator
    from ledger import Journal
    from shared_coordinator import CoordinatorBlocked, SharedBudgetJournal
    from test_global_budget import FakeS3


@unittest.skipUnless(sys.platform == 'linux', 'POSIX journal lock and Linux /proc are required')
class Integration(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='rove4k-coordinator-')
        self.path = Path(self.directory.name) / 'journal.jsonl'
        self.client = FakeS3()
        self.store = g.S3SharedBudget(self.client, bucket='valid-campaign-bucket',
            key='test-campaign/shared/budget.json', account='123456789012',
            region='ap-southeast-2', campaign='test-campaign')
        self.root = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(self.client.doc['opening']))
        self.journal = Journal(self.path, 'test-campaign')
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)

    def tearDown(self):
        self.journal.close()
        self.directory.cleanup()

    def record(self, n, event, data, at=1000):
        return self.owner.record(request_id=f'coordinator-request-{n:03}', event=event, data=data, at=at)

    def launch(self, n, token, instance):
        self.record(n, 'budget.v2.launch_requested', {'launch_token': token, 'region': 'ap-southeast-2',
            'max_hourly_usd': '8'})
        self.record(n + 1, 'budget.v2.instance_bound', {'launch_token': token, 'instance_id': instance})

    def test_actual_ledger_two_hosts_limit_and_settle_before_shutdown(self):
        self.launch(1, 'first-token', 'i-123')
        self.launch(3, 'other-token', 'i-456')
        for n, name, token in ((5, 'game-a', 'first-token'), (7, 'game-b', 'other-token')):
            self.record(n, 'budget.v2.game_admitted', {'game_id': name, 'pair_id': 'pair-a', 'launch_token': token})
            self.record(n + 1, 'budget.v2.game_release_authorized', {'game_id': name, 'valid_until_utc': 1005})
        self.record(9, 'budget.v2.limit_confirmed', {'actual_usd': '120',
            'evidence': {'source': 'fixture', 'observation_id': 'limit-1'}})
        for n, name, token, instance in ((10, 'game-a', 'first-token', 'i-123'),
                                         (11, 'game-b', 'other-token', 'i-456')):
            self.record(n, 'budget.v2.game_settled', {'game_id': name, 'launch_token': token,
                'physically_settled': True, 'evidence': {'game_id': name, 'instance_id': instance,
                'state': 'exited', 'observation_id': name + '-exit'}})
        self.record(12, 'budget.v2.terminate_requested', {'launch_token': 'first-token', 'instance_id': 'i-123'})
        self.record(13, 'budget.v2.terminate_requested', {'launch_token': 'other-token', 'instance_id': 'i-456'})
        self.assertEqual(self.owner.anchor.seq, 12)
        self.assertFalse(self.owner.provides_go_authority)
        self.assertEqual(self.store.load(self.root).anchor, self.owner.anchor)
        # Attempts after the limit are rejected and the written intent is held.
        with self.assertRaises(ValueError):
            self.record(14, 'budget.v2.game_admitted', {'game_id': 'game-c', 'pair_id': 'pair-a', 'launch_token': 'first-token'})
        self.assertTrue(self.owner.blocked)
        self.assertEqual(self.owner.inspect_pending()['status'], 'not_observed')

    def test_restart_loads_durable_anchor_without_adopting_extra_history(self):
        self.launch(1, 'first-token', 'i-123')
        expected = self.owner.anchor
        self.journal.close()
        self.journal = Journal(self.path, 'test-campaign')
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)
        self.assertEqual(self.owner.anchor, expected)
        self.assertFalse(self.owner.blocked)
        self.record(3, 'budget.v2.observe', {}, at=1001)

    def test_uncertain_write_survives_restart_and_never_retries(self):
        self.client.timeout_after_write = True
        with self.assertRaises(g.LedgerUncertain):
            self.record(1, 'budget.v2.launch_requested', {'launch_token': 'first-token',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
        self.assertTrue(self.owner.blocked)
        self.assertEqual(self.owner.inspect_pending()['status'], 'observed')
        version = self.client.seq
        with self.assertRaises(CoordinatorBlocked):
            self.record(2, 'budget.v2.observe', {})
        self.assertEqual(self.client.seq, version)
        self.journal.close()
        self.journal = Journal(self.path, 'test-campaign')
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)
        self.assertTrue(self.owner.blocked)
        self.assertEqual(self.owner.inspect_pending()['status'], 'observed')
        self.assertEqual(self.client.seq, version)

    def test_conflict_is_quarantined_even_if_absence_is_observed(self):
        self.client.conflict = True
        with self.assertRaises(g.LedgerConflict):
            self.record(1, 'budget.v2.launch_requested', {'launch_token': 'first-token',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
        self.assertEqual(self.owner.inspect_pending()['status'], 'not_observed')
        self.client.conflict = False
        with self.assertRaises(CoordinatorBlocked):
            self.record(2, 'budget.v2.observe', {})
        self.assertEqual(self.client.seq, 1)

    def test_thread_concurrency_serializes_actual_remote_events(self):
        self.launch(1, 'first-token', 'i-123')
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(self.record, n, 'budget.v2.observe', {}, 1000) for n in (3, 4)]
            for future in futures:
                future.result()
        snapshot = self.store.load(self.root)
        self.assertEqual(len(snapshot.rows), 4)
        self.assertEqual(snapshot.anchor, self.owner.anchor)

    def test_unjournaled_external_advance_fails_closed_on_restart(self):
        self.store.append(trusted=self.root, request_id='external-request-001', event='budget.v2.observe', data={}, at=1000)
        self.journal.close()
        self.journal = Journal(self.path, 'test-campaign')
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)
        self.assertTrue(self.owner.blocked)
        with self.assertRaises(CoordinatorBlocked):
            self.record(1, 'budget.v2.observe', {})

    def test_external_advance_after_start_is_rejected_before_remote_write(self):
        self.store.append(trusted=self.root, request_id='external-request-001', event='budget.v2.observe', data={}, at=1000)
        version = self.client.seq
        with self.assertRaises(g.LedgerConflict):
            self.record(1, 'budget.v2.observe', {})
        self.assertEqual(self.client.seq, version)
        self.assertTrue(self.owner.blocked)
        self.assertEqual(self.owner.inspect_pending()['status'], 'not_observed')

    def test_journal_handle_has_only_one_local_owner(self):
        with self.assertRaisesRegex(ValueError, 'already belongs'):
            SharedBudgetJournal(self.store, self.journal, self.root)
        self.record(1, 'budget.v2.observe', {})

    def test_another_open_journal_handle_cannot_bypass_posix_lock(self):
        with self.assertRaises(BlockingIOError):
            Journal(self.path, 'test-campaign')

    def test_new_journal_directory_entries_are_fsynced_before_remote_access(self):
        path = Path(self.directory.name) / 'new' / 'nested' / 'other.jsonl'
        journal = Journal(path, 'test-campaign')
        original = os.fsync
        directories = []
        def observe(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                directories.append(os.readlink(f'/proc/self/fd/{descriptor}'))
            return original(descriptor)
        try:
            with patch.object(coordinator.os, 'fsync', side_effect=observe):
                SharedBudgetJournal(self.store, journal, self.root)
            self.assertIn(str(path.parent), directories)
            self.assertIn(str(path.parent.parent), directories)
        finally:
            journal.close()

    def test_directory_fsync_failure_prevents_any_remote_write(self):
        journal = Journal(Path(self.directory.name) / 'other.jsonl', 'test-campaign')
        original = os.fsync
        def fault(descriptor):
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError('directory fsync failed')
            return original(descriptor)
        try:
            with patch.object(coordinator.os, 'fsync', side_effect=fault):
                with self.assertRaisesRegex(OSError, 'directory fsync failed'):
                    SharedBudgetJournal(self.store, journal, self.root)
            self.assertEqual(self.client.seq, 1)
            self.assertFalse(journal.rows)
        finally:
            journal.close()

    def test_failed_intent_fsync_quarantines_and_survives_process_restart(self):
        append = self.journal.append
        def uncertain_intent(event, data):
            append(event, data)
            raise OSError('intent fsync outcome uncertain')
        with patch.object(self.journal, 'append', side_effect=uncertain_intent):
            with self.assertRaisesRegex(OSError, 'intent fsync'):
                self.record(1, 'budget.v2.observe', {})
        self.assertTrue(self.owner.blocked)
        self.assertEqual(self.client.seq, 1)
        with self.assertRaises(CoordinatorBlocked):
            self.record(2, 'budget.v2.observe', {})
        self.journal.close()
        self.journal = Journal(self.path, 'test-campaign')
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)
        self.assertTrue(self.owner.blocked)
        self.assertEqual(self.owner.inspect_pending()['status'], 'not_observed')


if __name__ == '__main__':
    unittest.main()
