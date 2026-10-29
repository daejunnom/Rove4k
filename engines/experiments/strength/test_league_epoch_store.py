"""Exercise epoch transactions with a simulated DynamoDB and real POSIX journals.

This fake serializes conditional writes but cannot prove AWS, IAM, clocks or
recipient fencing. It must never be treated as game or instance authority.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

try:
    from .league_epoch_store import DynamoEpochStore, EpochHead, AttemptIntent, FenceUncertain
    from .ledger import Journal, digest
except ImportError:
    from league_epoch_store import DynamoEpochStore, EpochHead, AttemptIntent, FenceUncertain
    from ledger import Journal, digest


ACCOUNT = '123456789012'
REGION = 'ap-southeast-2'
CAMPAIGN = 'test-league'
TABLE = 'rove4k-league-fence-test'
GENERATION = 'a' * 64
OWNER = 'b' * 64
BUDGET = 'c' * 64


def item_key(record):
    return {'campaign_id': {'S': CAMPAIGN}, 'record_id': {'S': record}}


def root_item(*, epoch=1, revision=0, owner=OWNER, mode='active', budget=0):
    return {**item_key('epoch#head'), 'generation': {'S': GENERATION},
            'epoch': {'N': str(epoch)}, 'revision': {'N': str(revision)},
            'owner': {'S': owner}, 'mode': {'S': mode}, 'budget_head': {'S': BUDGET},
            'budget_upper_micros': {'N': str(budget)}}


def attempt(name='attempt-1', subject='game-1', action='go'):
    return AttemptIntent(name, action, subject, 'd' * 64, 'e' * 64, 'f' * 64, 1000, 2000)


class FakeDynamo:
    """Implement only the actual conditional requests this module generates."""
    region = REGION

    def __init__(self):
        self.account = ACCOUNT
        self.items = {'epoch#head': root_item()}
        self.calls = []
        self.lock = threading.Lock()
        self.timeout_after_write = False
        self.timeout_before_write = False
        self.malformed_after_update = False
        self.after_write_seen = None
        self.continue_write = None
        self.fail_head_read = False

    def call(self, service, operation, request):
        with self.lock:
            self.calls.append((service, operation, deepcopy(request)))
            if (service, operation) == ('sts', 'get-caller-identity'):
                if request != {}:
                    raise AssertionError('unexpected STS request')
                return {'Account': self.account}
            if service != 'dynamodb':
                raise AssertionError('unexpected service or AWS mutation')
            if operation == 'get-item':
                if (request.get('TableName') != TABLE or request.get('ConsistentRead') is not True
                        or request['Key']['campaign_id'] != {'S': CAMPAIGN}):
                    raise AssertionError('strong account-scoped read required')
                row = self.items.get(request['Key']['record_id']['S'])
                if request['Key']['record_id']['S'] == 'epoch#head' and self.fail_head_read:
                    raise TimeoutError('head read unavailable')
                return {} if row is None else {'Item': deepcopy(row)}
            if operation not in ('update-item', 'transact-write-items'):
                raise AssertionError('unexpected DynamoDB operation')
            if self.timeout_before_write:
                raise TimeoutError('ambiguous transport outcome')
            if operation == 'update-item':
                result = self._update(request)
            else:
                result = self._transaction(request)
            if self.after_write_seen is not None:
                self.after_write_seen.set()
                if not self.continue_write.wait(5):
                    raise TimeoutError('test did not resume paused write')
            if self.timeout_after_write:
                raise TimeoutError('response lost after remote commit')
            return result

    def _matches(self, update):
        if update.get('TableName') != TABLE or update.get('Key') != item_key('epoch#head'):
            raise AssertionError('epoch target differs')
        names, values = update['ExpressionAttributeNames'], update['ExpressionAttributeValues']
        expected_names = {'#g': 'generation', '#e': 'epoch', '#r': 'revision', '#o': 'owner',
                          '#m': 'mode', '#b': 'budget_head', '#u': 'budget_upper_micros'}
        base = '#g = :g AND #e = :e AND #r = :r AND #o = :o AND #m = :m AND #b = :b AND #u = :u'
        condition = update['ConditionExpression']
        if names != expected_names or condition not in (base, base + ' AND #u < :cap'):
            raise AssertionError('exact epoch identity condition required')
        current = self.items['epoch#head']
        fields = {'#g': ':g', '#e': ':e', '#r': ':r', '#o': ':o', '#m': ':m', '#b': ':b', '#u': ':u'}
        matching = all(current[names[name]] == values[placeholder] for name, placeholder in fields.items())
        if condition.endswith(' AND #u < :cap'):
            matching &= int(current['budget_upper_micros']['N']) < int(values[':cap']['N'])
        return matching

    def _next(self, update):
        current = deepcopy(self.items['epoch#head'])
        expression, values = update['UpdateExpression'], update['ExpressionAttributeValues']
        if expression == 'SET #m = :drain, #r = :next':
            current.update(mode=deepcopy(values[':drain']), revision=deepcopy(values[':next']))
        elif expression == 'SET #e = :epoch_next, #o = :owner_next, #r = :next':
            current.update(epoch=deepcopy(values[':epoch_next']), owner=deepcopy(values[':owner_next']),
                           revision=deepcopy(values[':next']))
        elif expression == 'SET #r = :next':
            current['revision'] = deepcopy(values[':next'])
        else:
            raise AssertionError('unexpected update expression')
        return current

    def _update(self, request):
        if request.get('ReturnValues') != 'ALL_NEW' or not self._matches(request):
            raise RuntimeError('conditional update failed')
        self.items['epoch#head'] = self._next(request)
        if self.malformed_after_update:
            return {'Attributes': {'revision': {'N': 'garbled'}}}
        return {'Attributes': deepcopy(self.items['epoch#head'])}

    def _transaction(self, request):
        if set(request) != {'TransactItems'} or len(request['TransactItems']) != 3:
            raise AssertionError('exact epoch + two unique writes required')
        update, put_attempt, put_subject = request['TransactItems']
        if set(update) != {'Update'} or set(put_attempt) != {'Put'} or set(put_subject) != {'Put'}:
            raise AssertionError('unexpected transactional action')
        update, puts = update['Update'], [put_attempt['Put'], put_subject['Put']]
        ids = []
        for put in puts:
            if (put['TableName'] != TABLE or put['ConditionExpression'] !=
                    'attribute_not_exists(campaign_id) AND attribute_not_exists(record_id)'
                    or put['Item']['campaign_id'] != {'S': CAMPAIGN}):
                raise AssertionError('attempt must be immutable and campaign-scoped')
            if any(name in put['Item'] for name in ('ttl', 'expires_at')):
                raise AssertionError('replay protection must not use TTL')
            ids.append(put['Item']['record_id']['S'])
        if (len(set(ids + ['epoch#head'])) != 3 or not ids[0].startswith('attempt#')
                or not ids[1].startswith('subject#')):
            raise AssertionError('transaction must target three distinct items')
        if not self._matches(update) or any(key in self.items for key in ids):
            raise RuntimeError('transaction cancelled')
        next_root = self._next(update)
        self.items['epoch#head'] = next_root
        for put, name in zip(puts, ids):
            self.items[name] = deepcopy(put['Item'])
        return {}


@unittest.skipUnless(sys.platform == 'linux', 'requires POSIX locked and fsynced journals')
class EpochStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rove4k-epoch-test-')
        self.client = FakeDynamo()
        self.journals = []
        self.root_head = EpochHead(1, 0, OWNER, GENERATION, 'active', BUDGET, 0)

    def tearDown(self):
        for journal in self.journals:
            journal.close()
        self.temp.cleanup()

    def make_store(self, path='one.jsonl'):
        journal = Journal(Path(self.temp.name) / path, CAMPAIGN)
        self.journals.append(journal)
        return DynamoEpochStore(self.client, table=TABLE, account=ACCOUNT, region=REGION,
                                campaign=CAMPAIGN, generation=GENERATION, journal=journal,
                                root_head=self.root_head)

    def reopen(self, old, path='one.jsonl'):
        old.journal.close()
        self.journals.remove(old.journal)
        return self.make_store(path)

    def test_record_is_atomic_durable_and_not_authority(self):
        store = self.make_store()
        head = store.read_head()
        result = store.record_intent(head, attempt())
        self.assertEqual((result['state'], result['revision']), ('recorded', head.revision + 1))
        self.assertFalse(result['authorizes_go'])
        self.assertFalse(result['authorizes_launch'])
        self.assertFalse(store.provides_go_authority)
        self.assertFalse(store.provides_launch_authority)
        self.assertEqual(store.read_head(), replace(head, revision=head.revision + 1))
        observed = store.inspect_attempt('attempt-1')
        self.assertTrue(observed['present'])
        self.assertFalse(observed['authorizes_go'])
        self.assertEqual(observed['item']['host_sha256'], {'S': 'e' * 64})
        self.assertEqual([r['event'] for r in store.journal.rows], ['epoch.genesis', 'epoch.intent', 'epoch.commit'])
        self.assertFalse(self.reopen(store).blocked)

    def test_account_and_region_mismatch_refuse(self):
        self.client.account = '999999999999'
        with self.assertRaises(FenceUncertain):
            self.make_store()
        self.client.account = ACCOUNT
        self.client.region = 'ap-northeast-1'
        with self.assertRaisesRegex(ValueError, 'region'):
            self.make_store('two.jsonl')
        self.assertFalse(any(s == 'dynamodb' and op != 'get-item' for s, op, _ in self.client.calls))

    def test_cap_and_invalid_window_reject_without_remote_mutation(self):
        self.client.items['epoch#head'] = root_item(budget=120_000_000)
        self.root_head = replace(self.root_head, budget_upper_micros=120_000_000)
        store = self.make_store()
        with self.assertRaisesRegex(ValueError, 'budget'):
            store.record_intent(store.read_head(), attempt())
        with self.assertRaises(ValueError):
            AttemptIntent('bad', 'go', 'game', 'd' * 64, 'e' * 64, 'f' * 64, 1, 60002)
        self.assertFalse(any(op == 'transact-write-items' for _, op, _ in self.client.calls))

    def test_unique_attempt_and_subject_survive_revision_changes(self):
        store = self.make_store()
        store.record_intent(store.read_head(), attempt())
        next_head = store.read_head()
        calls = sum(op == 'transact-write-items' for _, op, _ in self.client.calls)
        with self.assertRaises(ValueError):
            store.record_intent(next_head, attempt('attempt-2', 'game-1'))
        self.assertFalse(store.blocked)
        self.assertEqual(sum(op == 'transact-write-items' for _, op, _ in self.client.calls), calls)
        self.assertNotIn('attempt#attempt-2', self.client.items)
        self.assertEqual(store.read_head(), next_head)
        self.assertFalse(self.reopen(store).blocked)

    def test_foreign_subject_conflict_leaves_unresolved_journal(self):
        self.client.items['subject#go#game-1'] = item_key('subject#go#game-1')
        store = self.make_store()
        with self.assertRaises(FenceUncertain):
            store.record_intent(store.read_head(), attempt())
        self.assertTrue(store.blocked)
        self.assertNotIn('attempt#attempt-1', self.client.items)
        self.assertTrue(self.reopen(store).blocked)

    def test_two_owners_race_exact_revision_only_one_records(self):
        first, second = self.make_store('one.jsonl'), self.make_store('two.jsonl')
        expected = first.read_head()
        barrier, outcomes = threading.Barrier(2), []
        def run(store, number):
            barrier.wait()
            try:
                store.record_intent(expected, attempt('attempt-' + str(number), 'game-' + str(number)))
                outcomes.append('ok')
            except FenceUncertain:
                outcomes.append('blocked')
        threads = [threading.Thread(target=run, args=(first, 1)), threading.Thread(target=run, args=(second, 2))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertCountEqual(outcomes, ['ok', 'blocked'])
        self.assertEqual(sum(key.startswith('attempt#') for key in self.client.items), 1)
        self.assertEqual(self.client.items['epoch#head']['revision'], {'N': '1'})

    def test_external_drain_and_budget_update_fence_stale_snapshot(self):
        for changed in ('drain', 'budget'):
            with self.subTest(changed=changed):
                self.client.items = {'epoch#head': root_item()}
                store = self.make_store(changed + '.jsonl')
                expected = store.read_head()
                if changed == 'drain':
                    self.client.items['epoch#head']['mode'] = {'S': 'draining'}
                else:
                    self.client.items['epoch#head']['budget_head'] = {'S': '1' * 64}
                    self.client.items['epoch#head']['budget_upper_micros'] = {'N': '120000000'}
                with self.assertRaises(FenceUncertain):
                    store.record_intent(expected, attempt())
                self.assertTrue(store.blocked)
                self.assertNotIn('attempt#attempt-1', self.client.items)
                self.assertNotIn('subject#go#game-1', self.client.items)

    def test_external_epoch_change_rejects_prior_owner(self):
        store = self.make_store()
        expected = store.read_head()
        self.client.items['epoch#head'].update(epoch={'N': '2'}, revision={'N': '1'}, owner={'S': '2' * 64})
        with self.assertRaises(FenceUncertain):
            store.record_intent(expected, attempt())
        self.assertTrue(store.blocked)
        self.assertNotIn('attempt#attempt-1', self.client.items)

    def test_lost_response_never_retries_or_unblocks_on_restart(self):
        store = self.make_store()
        expected = store.read_head()
        self.client.timeout_after_write = True
        with self.assertRaises(FenceUncertain):
            store.record_intent(expected, attempt())
        self.client.timeout_after_write = False
        self.assertTrue(store.inspect_attempt('attempt-1')['present'])
        restarted = self.reopen(store)
        self.assertTrue(restarted.blocked)
        calls = sum(op == 'transact-write-items' for _, op, _ in self.client.calls)
        with self.assertRaises(FenceUncertain):
            restarted.record_intent(expected, attempt())
        self.assertEqual(sum(op == 'transact-write-items' for _, op, _ in self.client.calls), calls)

    def test_missing_row_after_timeout_remains_unresolved(self):
        store = self.make_store()
        expected = store.read_head()
        self.client.timeout_before_write = True
        with self.assertRaises(FenceUncertain):
            store.record_intent(expected, attempt())
        self.client.timeout_before_write = False
        observed = store.inspect_attempt('attempt-1')
        self.assertEqual(observed, {'state': 'unresolved', 'present': False, 'authorizes_go': False,
                                    'authorizes_launch': False})
        self.assertTrue(self.reopen(store).blocked)

    def test_malformed_update_response_stays_blocked_across_restart(self):
        store = self.make_store()
        self.client.malformed_after_update = True
        with self.assertRaises(FenceUncertain):
            store.close_starts(store.read_head())
        self.assertEqual(self.client.items['epoch#head']['mode'], {'S': 'draining'})
        self.assertEqual([row['event'] for row in store.journal.rows], ['epoch.genesis', 'epoch.intent'])
        self.assertTrue(self.reopen(store).blocked)

    def test_drain_and_epoch_advance_do_not_reopen_go(self):
        store = self.make_store()
        active = store.read_head()
        draining = store.close_starts(active)
        self.assertEqual(draining.mode, 'draining')
        advanced = store.advance_epoch(draining, 'd' * 64)
        self.assertEqual((advanced.epoch, advanced.revision, advanced.mode), (2, 2, 'draining'))
        with self.assertRaises(ValueError):
            store.record_intent(advanced, attempt())
        with self.assertRaises(ValueError):
            store.advance_epoch(advanced, 'd' * 64)

    def test_journal_failure_precedes_remote_mutation(self):
        store = self.make_store()
        expected = store.read_head()
        with patch.object(store.journal, 'append', side_effect=OSError('fsync failed')):
            with self.assertRaises(FenceUncertain):
                store.record_intent(expected, attempt())
        self.assertTrue(store.blocked)
        self.assertFalse(any(op == 'transact-write-items' for _, op, _ in self.client.calls))

    def test_rolled_back_head_and_attempts_never_reopen_after_restart(self):
        store = self.make_store()
        store.record_intent(store.read_head(), attempt())
        # Model a remote table restoration to old bytes after a committed
        # transaction. Its validity must not be inferred from the new read.
        self.client.items = {'epoch#head': root_item()}
        reopened = self.reopen(store)
        self.assertTrue(reopened.blocked)
        count = sum(op == 'transact-write-items' for _, op, _ in self.client.calls)
        with self.assertRaises(FenceUncertain):
            reopened.record_intent(reopened.read_head(), attempt())
        self.assertEqual(sum(op == 'transact-write-items' for _, op, _ in self.client.calls), count)

    def test_head_divergence_then_restoration_keeps_durable_quarantine(self):
        store = self.make_store()
        self.client.items['epoch#head']['revision'] = {'N': '1'}
        store.read_head()
        self.assertTrue(store.blocked)
        self.assertEqual(store.journal.rows[-1]['event'], 'epoch.quarantine')
        self.client.items['epoch#head'] = root_item()
        restarted = self.reopen(store)
        self.assertTrue(restarted.blocked)
        with self.assertRaises(FenceUncertain):
            restarted.record_intent(restarted.read_head(), attempt())

    def test_unavailable_or_malformed_head_remains_quarantined_after_restoration(self):
        for fault in ('missing', 'bad_number', 'foreign_generation', 'read_error'):
            with self.subTest(fault=fault):
                self.client.items = {'epoch#head': root_item()}
                self.client.fail_head_read = False
                store = self.make_store(fault + '.jsonl')
                if fault == 'missing':
                    del self.client.items['epoch#head']
                elif fault == 'bad_number':
                    self.client.items['epoch#head']['epoch'] = {'N': '1.5'}
                elif fault == 'foreign_generation':
                    self.client.items['epoch#head']['generation'] = {'S': '9' * 64}
                else:
                    self.client.fail_head_read = True
                with self.assertRaises((FenceUncertain, ValueError, TimeoutError)):
                    store.read_head()
                self.assertTrue(store.blocked)
                self.client.items = {'epoch#head': root_item()}
                self.client.fail_head_read = False
                restarted = self.reopen(store, fault + '.jsonl')
                self.assertTrue(restarted.blocked)
                with self.assertRaises(FenceUncertain):
                    restarted.record_intent(restarted.read_head(), attempt())

    def test_initial_sts_account_mismatch_is_durably_quarantined(self):
        self.client.account = '999999999999'
        with self.assertRaises((FenceUncertain, ValueError)):
            self.make_store('account.jsonl')
        failed_journal = self.journals.pop()
        failed_journal.close()
        self.client.account = ACCOUNT
        restored = self.make_store('account.jsonl')
        self.assertTrue(restored.blocked)
        with self.assertRaises(FenceUncertain):
            restored.record_intent(restored.read_head(), attempt())

    def test_boolean_numeric_equivalence_cannot_forge_replayed_journal(self):
        store = self.make_store()
        store.record_intent(store.read_head(), attempt())
        saved = deepcopy(store.journal.rows)
        # Journal chain is valid: only the logical content, rather than the
        # line hash, is tampered with. Python considers True == 1, so replay
        # must compare typed canonical values instead of plain dict equality.
        for field in ('root', 'expected', 'committed'):
            with self.subTest(field=field):
                path = field + '-tamper.jsonl'
                journal = Journal(Path(self.temp.name) / path, CAMPAIGN)
                genesis, intent, committed = (deepcopy(row['data']) for row in saved)
                if field == 'root':
                    genesis['root_head']['epoch'] = True
                elif field == 'expected':
                    intent['operation']['expected']['epoch'] = True
                    intent['operation_sha256'] = digest(intent['operation'])
                    committed['operation_sha256'] = intent['operation_sha256']
                else:
                    committed['head']['revision'] = True
                journal.append('epoch.genesis', genesis)
                journal.append('epoch.intent', intent)
                journal.append('epoch.commit', committed)
                journal.close()
                with self.assertRaises(ValueError):
                    self.make_store(path)

    def test_concurrent_read_waits_for_local_remote_write_commit(self):
        store = self.make_store()
        expected = store.read_head()
        self.client.after_write_seen, self.client.continue_write = threading.Event(), threading.Event()
        read_done, results = threading.Event(), []
        def writer():
            try:
                results.append(('write', store.record_intent(expected, attempt())))
            except Exception as error:
                results.append(('error', error))
        def reader():
            try:
                results.append(('read', store.read_head()))
            except Exception as error:
                results.append(('error', error))
            finally:
                read_done.set()
        writing = threading.Thread(target=writer)
        reading = threading.Thread(target=reader)
        writing.start()
        try:
            self.assertTrue(self.client.after_write_seen.wait(5))
            reading.start()
            self.assertFalse(read_done.wait(0.05))
        finally:
            self.client.continue_write.set()
            writing.join(timeout=10)
            if reading.ident is not None:
                reading.join(timeout=10)
        self.assertFalse(writing.is_alive())
        self.assertFalse(reading.is_alive())
        self.assertCountEqual([kind for kind, _ in results], ['write', 'read'])
        self.assertFalse(store.blocked)
        self.assertFalse(any(row['event'] == 'epoch.quarantine' for row in store.journal.rows))

    def test_foreign_journal_owner_cannot_be_shared(self):
        journal = Journal(Path(self.temp.name) / 'foreign.jsonl', CAMPAIGN)
        self.journals.append(journal)
        journal._shared_coordinator_owner = object()
        with self.assertRaisesRegex(ValueError, 'owner|belongs|shared'):
            DynamoEpochStore(self.client, table=TABLE, account=ACCOUNT, region=REGION,
                             campaign=CAMPAIGN, generation=GENERATION, journal=journal,
                             root_head=self.root_head)
        self.assertFalse(any(s == 'dynamodb' and op != 'get-item' for s, op, _ in self.client.calls))

    def test_attempt_remains_used_if_remote_attempt_row_is_removed(self):
        store = self.make_store()
        store.record_intent(store.read_head(), attempt())
        current = store.read_head()
        # Removing only the immutable attempt row must not erase locally
        # committed history even if the external epoch head did not change.
        del self.client.items['attempt#attempt-1']
        restarted = self.reopen(store)
        calls = sum(op == 'transact-write-items' for _, op, _ in self.client.calls)
        with self.assertRaises((FenceUncertain, ValueError)):
            restarted.record_intent(current, attempt('attempt-1', 'different-game'))
        self.assertEqual(sum(op == 'transact-write-items' for _, op, _ in self.client.calls), calls)


if __name__ == '__main__':
    unittest.main()
