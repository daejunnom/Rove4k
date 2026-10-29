"""Fault-injected tests of the S3 ledger contract; no AWS operations occur."""
import base64
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    from . import global_budget as g
except ImportError:
    import global_budget as g


class FakeError(Exception):
    def __init__(self, code):
        self.code = code


class FakeS3:
    region = 'ap-southeast-2'

    def __init__(self):
        self.doc = {'format': 'rove4k-shared-budget-v1', 'campaign': 'test-campaign',
                    'account': '123456789012', 'home_region': self.region,
                    'opening': {'prior_compute_usd': '0', 'prior_ancillary_usd': '0', 'prior_limit_confirmed': False, 'as_of': 900,
                        'source_sha256': 'a' * 64, 'excludes_opening_events': True, 'complete_identities': True,
                        'prior_game_ids': [], 'prior_pair_ids': [], 'prior_request_ids': [],
                        'prior_launch_tokens': [], 'prior_instance_ids': [], 'prior_receipts': [], 'events': []},
                    'events': []}
        self.versions = {}
        self.seq = 0
        self.conflict = False
        self.timeout_after_write = False
        self.error_after_write = None
        self.malformed_after_write = False
        self.fail_confirmation = False
        self.malformed_confirmation = False
        self._publish(g.canonical(self.doc))

    def _publish(self, body):
        self.seq += 1
        self.raw = body
        self.sha = hashlib.sha256(body).hexdigest()
        self.checksum = base64.b64encode(bytes.fromhex(self.sha)).decode('ascii')
        # Model the content-derived ETags which expose ABA on byte restoration.
        self.etag = '"' + self.sha + '"'
        self.version = 'version-' + str(self.seq)
        self.versions[self.version] = self._head()

    def _head(self):
        return {'Metadata': {'sha256': self.sha}, 'ChecksumSHA256': self.checksum,
                'ContentLength': len(self.raw), 'ETag': self.etag, 'VersionId': self.version}

    def call(self, service, operation, request):
        if (service, operation) != ('s3api', 'head-object') or request['ExpectedBucketOwner'] != '123456789012':
            raise AssertionError('unexpected API call')
        version = request.get('VersionId')
        if version is not None:
            if self.fail_confirmation:
                raise FakeError('ObservationTimeout')
            if self.malformed_confirmation:
                return dict(self.versions[version], Metadata=None)
            return dict(self.versions[version])
        return self._head()

    def get_file(self, bucket, key, path, etag, *, expected_owner):
        if expected_owner != '123456789012' or etag != self.etag:
            raise FakeError('PreconditionFailed')
        Path(path).write_bytes(self.raw)
        return {'ChecksumSHA256': self.checksum, 'VersionId': self.version}

    def put_file_if_match(self, bucket, key, path, sha, etag, *, expected_owner):
        if expected_owner != '123456789012' or self.conflict or etag != self.etag:
            raise FakeError('PreconditionFailed')
        data = Path(path).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise AssertionError('caller passed wrong bytes')
        self._publish(data)
        if self.timeout_after_write:
            raise FakeError('ObservationTimeout')
        if self.error_after_write:
            raise FakeError(self.error_after_write)
        if self.malformed_after_write:
            return None
        return {'ChecksumSHA256': self.checksum, 'VersionId': self.version, 'ETag': self.etag}


class SharedLedgerTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeS3()
        self.store = g.S3SharedBudget(self.client, bucket='valid-campaign-bucket',
            key='test-campaign/shared/budget.json', account='123456789012',
            region='ap-southeast-2', campaign='test-campaign')
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(self.client.doc['opening']))

    def append_launch(self, request='unique-request-001'):
        return self.store.append(trusted=self.genesis, request_id=request,
            event='budget.v2.launch_requested', data={'launch_token': 'first-token',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, at=1000)

    def test_verified_cas_advances_chain_and_owner_bound_read(self):
        result = self.append_launch()
        self.assertEqual(result.anchor.seq, 0)
        self.assertEqual(result.version_id, 'version-2')
        observed = self.store.load(self.genesis)
        self.assertEqual(observed.anchor, result.anchor)
        self.assertEqual(observed.rows[0]['request_id'], 'unique-request-001')
        second = self.store.append(trusted=result.anchor, request_id='unique-request-002',
            event='budget.v2.instance_bound', data={'launch_token': 'first-token',
                'instance_id': 'i-123'}, at=1001)
        self.assertEqual(second.anchor.seq, 1)
        self.assertEqual(self.store.load(result.anchor).anchor, second.anchor)

    def test_expected_head_rejects_extended_history_before_writing(self):
        self.append_launch()
        version = self.client.seq
        # A trusted prefix remains a valid rollback anchor, but is no longer
        # the precise snapshot this serialized owner is allowed to extend.
        with self.assertRaises(g.LedgerConflict):
            self.store.append(trusted=self.genesis, expected_head=self.genesis,
                request_id='unique-request-002', event='budget.v2.observe', data={}, at=1001)
        self.assertEqual(self.client.seq, version)
        self.assertEqual(len(self.store.load(self.genesis).rows), 1)

    def test_expected_head_conditional_put_rejects_a_racing_writer(self):
        original = self.client.put_file_if_match
        def interleave(bucket, key, path, sha, etag, *, expected_owner):
            # A different writer updates the same object after our exact head
            # read; the original ETag conditional must reject our PUT.
            self.client.put_file_if_match = original
            self.store.append(trusted=self.genesis, request_id='external-request-01',
                              event='budget.v2.observe', data={}, at=1000)
            return original(bucket, key, path, sha, etag, expected_owner=expected_owner)
        self.client.put_file_if_match = interleave
        with self.assertRaises(g.LedgerConflict):
            self.store.append(trusted=self.genesis, expected_head=self.genesis,
                              request_id='unique-request-001', event='budget.v2.observe', data={}, at=1000)
        rows = self.store.load(self.genesis).rows
        self.assertEqual([row['request_id'] for row in rows], ['external-request-01'])

    def test_temporary_upper_limit_can_recover_after_launch_absence(self):
        first = self.append_launch()
        observed = self.store.append(trusted=first.anchor, request_id='unique-request-002',
            event='budget.v2.observe', data={}, at=46000)
        absent = self.store.append(trusted=observed.anchor, request_id='unique-request-003',
            event='budget.v2.launch_absent', at=46001, data={'launch_token': 'first-token',
                'authoritative_absence': True, 'evidence': {'launch_token': 'first-token',
                    'region': 'ap-southeast-2', 'state': 'absent', 'observation_id': 'absence-1'}})
        reopened = self.store.append(trusted=absent.anchor, request_id='unique-request-004',
            event='budget.v2.launch_requested', at=46002, data={'launch_token': 'second-token',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
        self.assertEqual(self.store.load(reopened.anchor).anchor, reopened.anchor)

    def test_confirmed_limit_survives_ledger_replay(self):
        first = self.append_launch()
        confirmed = self.store.append(trusted=first.anchor, request_id='unique-request-002',
            event='budget.v2.limit_confirmed', at=1001, data={'actual_usd': '120',
                'evidence': {'source': 'billing', 'observation_id': 'bill-1'}})
        absent = self.store.append(trusted=confirmed.anchor, request_id='unique-request-003',
            event='budget.v2.launch_absent', at=1002, data={'launch_token': 'first-token',
                'authoritative_absence': True, 'evidence': {'launch_token': 'first-token',
                    'region': 'ap-southeast-2', 'state': 'absent', 'observation_id': 'absence-1'}})
        with self.assertRaisesRegex(ValueError, 'draining'):
            self.store.append(trusted=absent.anchor, request_id='unique-request-004',
                event='budget.v2.launch_requested', at=1003, data={'launch_token': 'second-token',
                    'region': 'ap-southeast-2', 'max_hourly_usd': '8'})

    def test_opening_checkpoint_preserves_prior_confirmed_limit(self):
        opening = self.client.doc['opening']
        opening['prior_limit_confirmed'] = True
        self.client._publish(g.canonical(self.client.doc))
        anchor = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        self.assertEqual(self.store.load(anchor).rows, ())
        with self.assertRaisesRegex(ValueError, 'draining'):
            self.store.append(trusted=anchor, request_id='unique-request-001',
                event='budget.v2.launch_requested', at=1000, data={'launch_token': 'first-token',
                    'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
        del opening['prior_limit_confirmed']
        self.client._publish(g.canonical(self.client.doc))
        incomplete = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        with self.assertRaisesRegex(ValueError, 'opening checkpoint'):
            self.store.load(incomplete)

    def test_admitted_ids_round_trip_as_checkpoint_history(self):
        first = self.append_launch()
        bound = self.store.append(trusted=first.anchor, request_id='unique-request-002',
            event='budget.v2.instance_bound', data={'launch_token': 'first-token', 'instance_id': 'i-123'}, at=1001)
        game_id, pair_id = 'A' + 'x' * 95, '9._-'
        admitted = self.store.append(trusted=bound.anchor, request_id='unique-request-003',
            event='budget.v2.game_admitted', data={'game_id': game_id, 'pair_id': pair_id,
                'launch_token': 'first-token'}, at=1002)
        saved_game = self.store.load(admitted.anchor).rows[-1]['data']
        # Model a trusted checkpoint after settlement, preserving the exact
        # admitted identifiers and a different active instance.
        opening = self.client.doc['opening']
        opening.update(as_of=1010, prior_game_ids=[saved_game['game_id']],
            prior_pair_ids=[saved_game['pair_id']], prior_launch_tokens=['first-token'],
            prior_instance_ids=['i-123'], prior_request_ids=['unique-request-001', 'unique-request-002', 'unique-request-003'])
        opening['events'] = [
            {'campaign': 'test-campaign', 'event': 'budget.v2.launch_requested', 'time_utc': 1008,
             'data': {'launch_token': 'second-token', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'}},
            {'campaign': 'test-campaign', 'event': 'budget.v2.instance_bound', 'time_utc': 1009,
             'data': {'launch_token': 'second-token', 'instance_id': 'i-456'}}]
        self.client._publish(g.canonical(self.client.doc))
        anchor = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        self.assertEqual(self.store.load(anchor).opening['prior_game_ids'], [game_id])
        with self.assertRaisesRegex(ValueError, 'admission denied'):
            self.store.append(trusted=anchor, request_id='unique-request-004', event='budget.v2.game_admitted',
                data={'game_id': game_id, 'pair_id': pair_id, 'launch_token': 'second-token'}, at=1011)
        result = self.store.append(trusted=anchor, request_id='unique-request-005', event='budget.v2.game_admitted',
            data={'game_id': 'next-game', 'pair_id': pair_id, 'launch_token': 'second-token'}, at=1011)
        self.assertEqual(result.rows[-1]['data']['pair_id'], pair_id)

    def test_conflict_is_not_auto_retried_or_treated_as_success(self):
        self.client.conflict = True
        with self.assertRaises(g.LedgerConflict):
            self.append_launch()
        self.assertEqual(self.client.seq, 1)
        self.assertEqual(self.store.load(self.genesis).rows, ())

    def test_timeout_after_write_requires_reconciliation_not_reissue(self):
        self.client.timeout_after_write = True
        with self.assertRaises(g.LedgerUncertain):
            self.append_launch()
        observed = self.store.load(self.genesis)
        self.assertEqual(observed.rows[0]['request_id'], 'unique-request-001')
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            self.append_launch()
        self.assertEqual(self.client.seq, 2)

    def test_version_confirmation_loss_stays_uncertain_even_after_put(self):
        self.client.fail_confirmation = True
        with self.assertRaises(g.LedgerUncertain):
            self.append_launch()
        self.assertEqual(self.client.seq, 2)
        self.assertEqual(len(self.store.load(self.genesis).rows), 1)

    def test_malformed_metadata_after_put_is_uncertain(self):
        self.client.malformed_confirmation = True
        with self.assertRaises(g.LedgerUncertain):
            self.append_launch()
        self.assertEqual(self.client.seq, 2)
        self.assertEqual(len(self.store.load(self.genesis).rows), 1)

    def test_other_post_put_errors_and_malformed_responses_are_uncertain(self):
        for failure in ('InternalError', 'ServiceUnavailable', 'RequestTimeout', 'malformed'):
            with self.subTest(failure=failure):
                self.setUp()
                if failure == 'malformed':
                    self.client.malformed_after_write = True
                else:
                    self.client.error_after_write = failure
                with self.assertRaises(g.LedgerUncertain):
                    self.append_launch()
                self.assertEqual(self.client.seq, 2)
                self.assertEqual(len(self.store.load(self.genesis).rows), 1)

    def test_cleanup_error_after_successful_put_is_uncertain(self):
        real = g.tempfile.TemporaryDirectory
        calls = []
        class FailingCleanup:
            def __init__(self, *args, **kwargs):
                self.inner = real(*args, **kwargs)
            def __enter__(self):
                return self.inner.__enter__()
            def __exit__(self, *error):
                self.inner.__exit__(*error)
                raise OSError('simulated cleanup failure')
        def factory(*args, **kwargs):
            calls.append(1)
            return real(*args, **kwargs) if len(calls) == 1 else FailingCleanup(*args, **kwargs)
        with patch.object(g.tempfile, 'TemporaryDirectory', side_effect=factory):
            with self.assertRaises(g.LedgerUncertain):
                self.append_launch()
        self.assertEqual(self.client.seq, 2)
        self.assertEqual(len(self.store.load(self.genesis).rows), 1)

    def test_trusted_anchor_rejects_rollback_and_divergence(self):
        committed = self.append_launch()
        self.client._publish(g.canonical(self.client.doc))
        with self.assertRaisesRegex(ValueError, 'rolled back'):
            self.store.load(committed.anchor)

    def test_head_without_real_version_or_corrupt_download_is_not_accepted(self):
        prior = self.client._head
        self.client._head = lambda: dict(prior(), VersionId='null')
        with self.assertRaisesRegex(ValueError, 'version'):
            self.store.load(self.genesis)
        self.client._head = prior
        self.client.raw += b'corrupted'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.store.load(self.genesis)

    def test_request_identity_is_unique_and_domain_reducer_checked(self):
        result = self.append_launch()
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            self.store.append(trusted=result.anchor, request_id='unique-request-001',
                event='budget.v2.observe', data={}, at=1001)
        with self.assertRaisesRegex(ValueError, 'unknown shared budget event'):
            self.store.append(trusted=result.anchor, request_id='unique-request-003',
                event='budget.v2.unknown', data={}, at=1001)

    def test_duplicate_json_keys_and_foreign_owner_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.store._parse(b'{"format":"one","format":"two"}', self.genesis)
        with self.assertRaisesRegex(ValueError, 'home region'):
            g.S3SharedBudget(self.client, bucket='valid-campaign-bucket', key='test-campaign/budget',
                             account='123456789012', region='ap-northeast-1', campaign='test-campaign')
        other = g.Anchor(-1, g.ZERO, '1' * 64, self.genesis.opening_sha256)
        with self.assertRaisesRegex(ValueError, 'another ledger authority'):
            self.store.load(other)

    def test_opening_prior_cost_is_counted_and_tampering_is_rejected(self):
        self.client.doc['opening']['prior_compute_usd'] = '100'
        self.client._publish(g.canonical(self.client.doc))
        with self.assertRaisesRegex(ValueError, 'opening checkpoint'):
            self.store.load(self.genesis)
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(self.client.doc['opening']))
        with self.assertRaisesRegex(ValueError, 'draining'):
            self.append_launch()
        self.assertEqual(self.client.seq, 2)

    def test_opening_preserves_unsettled_game_and_launch_owner(self):
        opening = self.client.doc['opening']
        opening['as_of'] = 904
        def record(event, data, at):
            return {'campaign': 'test-campaign', 'event': event, 'data': data, 'time_utc': at}
        opening['events'] = [
            record('budget.v2.launch_requested', {'launch_token': 'old-token',
                'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, 900),
            record('budget.v2.instance_bound', {'launch_token': 'old-token', 'instance_id': 'i-old'}, 901),
            record('budget.v2.game_admitted', {'game_id': 'old-game', 'pair_id': 'old-pair',
                'launch_token': 'old-token'}, 902),
            record('budget.v2.game_release_authorized', {'game_id': 'old-game'}, 903),
        ]
        self.client._publish(g.canonical(self.client.doc))
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        with self.assertRaisesRegex(ValueError, 'settled games'):
            self.store.append(trusted=self.genesis, request_id='unique-request-old',
                event='budget.v2.terminate_requested', data={'launch_token': 'old-token',
                    'instance_id': 'i-old'}, at=905)
        result = self.append_launch()
        self.assertEqual(result.anchor.seq, 0)

        # Carry-in at the checkpoint cannot erase or retroactively invalidate a
        # game whose GO was authorized before the threshold was reached.
        self.client.doc['opening']['prior_compute_usd'] = '100'
        self.client._publish(g.canonical(self.client.doc))
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        self.assertEqual(len(self.store.load(self.genesis).opening['events']), 4)
        with self.assertRaisesRegex(ValueError, 'settled games'):
            self.store.append(trusted=self.genesis, request_id='unique-request-old2',
                event='budget.v2.terminate_requested', data={'launch_token': 'old-token',
                    'instance_id': 'i-old'}, at=905)
        with self.assertRaisesRegex(ValueError, 'draining'):
            self.append_launch('unique-request-new')

    def test_opening_requires_excluded_prior_evidence_and_monotonic_time(self):
        opening = self.client.doc['opening']
        opening['excludes_opening_events'] = False
        self.client._publish(g.canonical(self.client.doc))
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        with self.assertRaisesRegex(ValueError, 'opening checkpoint'):
            self.store.load(self.genesis)

    def test_opening_retains_completed_identities_and_pair_cap(self):
        opening = self.client.doc['opening']
        opening['as_of'] = 902
        opening['prior_game_ids'] = ['finished-game']
        opening['prior_pair_ids'] = ['pair-' + str(i) for i in range(128)]
        opening['prior_request_ids'] = ['unique-request-001']
        opening['events'] = [
            {'campaign': 'test-campaign', 'event': 'budget.v2.launch_requested', 'time_utc': 900,
             'data': {'launch_token': 'old-token', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'}},
            {'campaign': 'test-campaign', 'event': 'budget.v2.instance_bound', 'time_utc': 901,
             'data': {'launch_token': 'old-token', 'instance_id': 'i-old'}},
        ]
        self.client._publish(g.canonical(self.client.doc))
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            self.store.append(trusted=self.genesis, request_id='unique-request-001',
                event='budget.v2.observe', data={}, at=1000)
        with self.assertRaisesRegex(ValueError, 'admission denied'):
            self.store.append(trusted=self.genesis, request_id='unique-request-002',
                event='budget.v2.game_admitted', data={'game_id': 'finished-game', 'pair_id': 'pair-0',
                    'launch_token': 'old-token'}, at=1000)
        with self.assertRaisesRegex(ValueError, 'admission denied'):
            self.store.append(trusted=self.genesis, request_id='unique-request-003',
                event='budget.v2.game_admitted', data={'game_id': 'new-game', 'pair_id': 'pair-new',
                    'launch_token': 'old-token'}, at=1000)
        result = self.store.append(trusted=self.genesis, request_id='unique-request-004',
            event='budget.v2.game_admitted', data={'game_id': 'new-game', 'pair_id': 'pair-0',
                'launch_token': 'old-token'}, at=1000)
        self.assertEqual(result.anchor.seq, 0)

    def test_opening_pair_cap_counts_prior_and_active_as_a_union(self):
        opening = self.client.doc['opening']
        opening['as_of'] = 904
        opening['prior_pair_ids'] = ['pair-' + str(i) for i in range(128)]
        opening['events'] = [
            {'campaign': 'test-campaign', 'event': 'budget.v2.launch_requested', 'time_utc': 900,
             'data': {'launch_token': 'old-token', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'}},
            {'campaign': 'test-campaign', 'event': 'budget.v2.instance_bound', 'time_utc': 901,
             'data': {'launch_token': 'old-token', 'instance_id': 'i-old'}},
            {'campaign': 'test-campaign', 'event': 'budget.v2.game_admitted', 'time_utc': 902,
             'data': {'game_id': 'active-game', 'pair_id': 'extra-pair', 'launch_token': 'old-token'}},
        ]
        self.client._publish(g.canonical(self.client.doc))
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        with self.assertRaisesRegex(ValueError, 'cumulative pair cap'):
            self.store.load(self.genesis)
        opening['events'][-1]['data']['pair_id'] = 'pair-0'
        self.client._publish(g.canonical(self.client.doc))
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        self.assertEqual(len(self.store.load(self.genesis).opening['events']), 3)

    def test_opening_preserves_closed_instance_and_receipt_identity(self):
        opening = self.client.doc['opening']
        opening['prior_launch_tokens'] = ['closed-token']
        opening['prior_instance_ids'] = ['i-previous']
        opening['prior_receipts'] = [['old-storage', '3']]
        opening['prior_ancillary_usd'] = '3'
        self.client._publish(g.canonical(self.client.doc))
        self.genesis = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(opening))
        with self.assertRaisesRegex(ValueError, 'closed launch token'):
            self.store.append(trusted=self.genesis, request_id='unique-request-001',
                event='budget.v2.launch_requested', data={'launch_token': 'closed-token',
                    'region': 'ap-southeast-2', 'max_hourly_usd': '8'}, at=1000)
        result = self.append_launch('unique-request-002')
        with self.assertRaisesRegex(ValueError, 'instance identity'):
            self.store.append(trusted=result.anchor, request_id='unique-request-003',
                event='budget.v2.instance_bound', data={'launch_token': 'first-token',
                    'instance_id': 'i-previous'}, at=1001)
        with self.assertRaisesRegex(ValueError, 'receipt identity changed'):
            self.store.append(trusted=result.anchor, request_id='unique-request-004',
                event='budget.v2.ancillary_charge', data={'receipt_id': 'old-storage', 'usd': '4'}, at=1001)
        replay = self.store.append(trusted=result.anchor, request_id='unique-request-005',
            event='budget.v2.ancillary_charge', data={'receipt_id': 'old-storage', 'usd': '3'}, at=1001)
        self.assertEqual(replay.anchor.seq, 1)


if __name__ == '__main__':
    unittest.main()
