"""No AWS/network/process tests for a declared, diagnostic seed transfer."""
import hashlib
import io
import os
from pathlib import Path
import tempfile
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest import mock

try:
    from . import league_seed_transfer as transfer
    from .league_controller import HostPlan
    from .league_seed_transfer import (TransferQuote, TransferSpec, create_owned_stage,
                                      fetch_declared, _fetch_declared_with_fd as fetch_fd)
    from .league_ssm_dispatch import Request
    from .test_league_controller import ACCOUNT, make_plan
except ImportError:
    import league_seed_transfer as transfer
    from league_controller import HostPlan
    from league_seed_transfer import (TransferQuote, TransferSpec, create_owned_stage,
                                      fetch_declared, _fetch_declared_with_fd as fetch_fd)
    from league_ssm_dispatch import Request
    from test_league_controller import ACCOUNT, make_plan

DATA = b'declared seed archive for two regions'
INSTANCE = 'i-' + '1' * 17
BOOT = '12345678-1234-1234-1234-123456789abc'
HOME = 'ap-southeast-2'
HOST = 'ap-southeast-1'


def spec():
    plan = make_plan(hosts=(HostPlan(region=HOST, profile='test-p16', slots=11,
                                    launch_token='second-host-token'),))
    request = Request(campaign_id=plan.campaign, job_id='test-job', instance_id=INSTANCE,
                      account_id=ACCOUNT, region=HOST, seed_manifest_sha256='b' * 64,
                      source_head='a' * 40, candidates_sha256='c' * 64, profile='test-p16',
                      artifact_id='test-artifact', artifact_bucket=plan.bucket,
                      repository='daejunnom/Rove4k', producer_run_id='17', producer_run_attempt='1',
                      producer_artifact_id='18', seed_bucket=plan.bucket,
                      seed_key='league-test/seed/archive.zip', seed_version_id='opaque-version',
                      seed_archive_sha256=hashlib.sha256(DATA).hexdigest(), seed_archive_bytes=len(DATA),
                      boot_id=BOOT)
    return TransferSpec(plan=plan, request=request, host_launch_token='second-host-token',
                        bucket_region=HOME, bucket_owner=ACCOUNT,
                        host_role_arn=f'arn:aws:iam::{ACCOUNT}:role/team/league-host',
                        caller_arn=f'arn:aws:sts::{ACCOUNT}:assumed-role/league-host/{INSTANCE}',
                        quote=TransferQuote('test-quote', 1700000000, '0.1', '0.01'))


class Client:
    def __init__(self, data=DATA, version='opaque-version', length=None, region=HOME):
        self.meta = SimpleNamespace(region_name=region)
        self.body = io.BytesIO(data)
        self.version = version
        self.length = len(data) if length is None else length
        self.calls = []

    def get_object(self, **kwargs):
        self.calls.append(kwargs)
        return {'Body': self.body, 'VersionId': self.version, 'ContentLength': self.length}


@unittest.skipUnless(hasattr(os, 'pread') and hasattr(os, 'pwrite'), 'positioned I/O required')
class SeedTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'seed.bin'
        self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)

    def tearDown(self):
        os.close(self.fd)
        self.temp.cleanup()

    def test_cross_region_fetch_pins_owner_and_never_claims_authority(self):
        s, client = spec(), Client()
        result = fetch_fd(s, client, self.fd)
        self.assertEqual(client.calls, [{'Bucket': s.plan.bucket, 'Key': s.request.seed_key,
                                        'VersionId': 'opaque-version', 'ExpectedBucketOwner': ACCOUNT}])
        self.assertTrue(client.body.closed)
        self.assertEqual(self.path.read_bytes(), DATA)
        self.assertEqual(result['plan_sha256'], s.plan.sha256)
        self.assertEqual(result['request']['boot_id'], BOOT)
        self.assertEqual(result['archive_sha256'], hashlib.sha256(DATA).hexdigest())
        self.assertEqual(result['bucket_region'], HOME)
        self.assertEqual(result['request']['region'], HOST)
        for key in ('host_authenticated', 'producer_authenticated', 'materialized',
                    'aws_cost_confirmed', 'launch_authorized', 'go_authorized'):
            self.assertIs(result['scope'][key], False)
        self.assertGreater(float(result['quote']['estimated_usd']), .01)

    def test_region_owner_host_role_and_home_resources_must_match_before_get(self):
        base = spec()
        for changes in ({'bucket_region': HOST}, {'bucket_owner': '999999999999'},
                        {'host_launch_token': 'unknown-token'},
                        {'caller_arn': f'arn:aws:sts::{ACCOUNT}:assumed-role/other/{INSTANCE}'},
                        {'host_role_arn': f'arn:aws:iam::{ACCOUNT}:role/invalid//role'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(base, **changes)
        foreign_table = replace(base.plan, table=f'arn:aws:dynamodb:{HOST}:{ACCOUNT}:table/home-table')
        with self.assertRaises(ValueError):
            replace(base, plan=foreign_table)
        client = Client(region=HOST)
        with self.assertRaises(ValueError):
            fetch_fd(base, client, self.fd)
        self.assertEqual(client.calls, [])

    def test_response_metadata_mismatch_closes_body_before_any_write(self):
        for client in (Client(version='different'), Client(length=len(DATA) + 1)):
            with self.subTest(version=client.version, length=client.length), self.assertRaises(ValueError):
                fetch_fd(spec(), client, self.fd)
            self.assertTrue(client.body.closed)
            self.assertEqual(os.fstat(self.fd).st_size, 0)

    def test_short_long_and_wrong_body_never_gain_receipt(self):
        for data in (DATA[:-1], DATA + b'x', b'x' * len(DATA)):
            with self.subTest(data=len(data)), tempfile.NamedTemporaryFile(mode='w+b', dir=self.temp.name, delete=False) as out:
                client = Client(data=data, length=len(DATA))
                with self.assertRaises(ValueError):
                    fetch_fd(spec(), client, out.fileno())
                self.assertTrue(client.body.closed)
                # Caller owns any partial output; the transfer never removes it.
                self.assertLessEqual(os.fstat(out.fileno()).st_size, len(DATA))

    def test_nonempty_output_fails_before_get(self):
        os.write(self.fd, b'existing')
        client = Client()
        with self.assertRaises(ValueError):
            fetch_fd(spec(), client, self.fd)
        self.assertEqual(client.calls, [])
        self.assertEqual(self.path.read_bytes(), b'existing')

    def test_public_fetch_refuses_a_caller_owned_fd(self):
        client = Client()
        with self.assertRaises(ValueError):
            fetch_declared(spec(), client, self.fd)
        self.assertEqual(client.calls, [])
        self.assertEqual(self.path.read_bytes(), b'')

    def test_quote_fields_reject_invalid_numbers_and_boolean_time(self):
        for rate in ('NaN', 'Infinity', '-0.1', '1000001', '', 'x'):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                TransferQuote('q', 1700000000, rate, '0')
        with self.assertRaises(ValueError):
            TransferQuote('q', True, '0', '0')

    def test_readonly_output_fails_before_get(self):
        readonly = os.open(self.path, os.O_RDONLY)
        client = Client()
        try:
            with self.assertRaises(ValueError):
                fetch_fd(spec(), client, readonly)
        finally:
            os.close(readonly)
        self.assertEqual(client.calls, [])

    def test_injected_client_errors_are_not_forwarded_in_exception_text(self):
        class BadClient:
            meta = SimpleNamespace(region_name=HOME)

            def get_object(self, **_kwargs):
                raise RuntimeError('untrusted-client-message')

        with self.assertRaises(ValueError) as captured:
            fetch_fd(spec(), BadClient(), self.fd)
        self.assertNotIn('untrusted-client-message', str(captured.exception))
        self.assertTrue(captured.exception.__suppress_context__)

    def test_injected_body_error_closes_stream_without_forwarding_its_text(self):
        class BadBody(io.BytesIO):
            def read(self, count=-1):
                raise RuntimeError('untrusted-body-message')

        client = Client()
        client.body = BadBody(DATA)
        with self.assertRaises(ValueError) as captured:
            fetch_fd(spec(), client, self.fd)
        self.assertTrue(client.body.closed)
        self.assertNotIn('untrusted-body-message', str(captured.exception))
        self.assertTrue(captured.exception.__suppress_context__)

    def test_recycled_caller_fd_during_network_read_does_not_touch_replacement(self):
        other = Path(self.temp.name) / 'replacement.bin'
        other_fd = os.open(other, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        original = self.fd

        class SwappingBody(io.BytesIO):
            def __init__(body_self):
                super().__init__(DATA)
                body_self.swapped = False

            def read(body_self, count=-1):
                if not body_self.swapped:
                    os.dup2(other_fd, original)
                    body_self.swapped = True
                return super().read(count)

        client = Client()
        client.body = SwappingBody()
        try:
            result = fetch_fd(spec(), client, original)
            self.assertFalse(result['scope']['go_authorized'])
            self.assertEqual(self.path.read_bytes(), DATA)
            self.assertEqual(other.read_bytes(), b'')
        finally:
            os.close(other_fd)

    def test_caller_seek_during_network_read_does_not_change_write_offset(self):
        original = self.fd

        class SeekingBody(io.BytesIO):
            def __init__(body_self):
                super().__init__(DATA)
                body_self.shifted = False

            def read(body_self, count=-1):
                if not body_self.shifted:
                    os.lseek(original, 1 << 20, os.SEEK_SET)
                    body_self.shifted = True
                return super().read(count)

        client = Client()
        client.body = SeekingBody()
        fetch_fd(spec(), client, original)
        self.assertEqual(self.path.read_bytes(), DATA)


@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'pread') and hasattr(os, 'pwrite')
                     and hasattr(os, 'O_NOFOLLOW'), 'POSIX no-follow positioned I/O required')
class OwnedStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'private-stage'
        self.root.mkdir(mode=0o700)
        os.chmod(self.root, 0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_owned_stage_snapshot_and_close_preserve_the_created_file(self):
        lease = create_owned_stage(self.root)
        path = lease.quarantine_path
        self.assertFalse(path.is_symlink())
        try:
            receipt = lease.fetch(spec(), Client())
            self.assertTrue(receipt['scope']['exclusive_stage_inode_checked'])
            self.assertFalse(receipt['scope']['host_authenticated'])
            self.assertEqual(lease.snapshot(), DATA)
            with self.assertRaises(ValueError):
                lease.fetch(spec(), Client())
        finally:
            lease.close()
        lease.close()
        self.assertEqual(path.read_bytes(), DATA)

    def test_bad_body_leaves_new_file_for_quarantine_and_no_retry(self):
        lease = create_owned_stage(self.root)
        path = lease.quarantine_path
        try:
            client = Client(data=DATA[:-1], length=len(DATA))
            with self.assertRaises(ValueError):
                lease.fetch(spec(), client)
            self.assertTrue(client.body.closed)
            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(), DATA[:-1])
            with self.assertRaises(ValueError):
                lease.fetch(spec(), Client())
            with self.assertRaises(ValueError):
                lease.snapshot()
        finally:
            lease.close()
        self.assertTrue(path.exists())

    def test_root_exchange_is_rejected_before_network(self):
        lease = create_owned_stage(self.root)
        moved = self.root.with_name('previous-stage')
        os.rename(self.root, moved)
        self.root.mkdir(mode=0o700)
        os.chmod(self.root, 0o700)
        client = Client()
        try:
            with self.assertRaises(ValueError):
                lease.fetch(spec(), client)
            self.assertEqual(client.calls, [])
            self.assertTrue((moved / lease.name).is_file())
        finally:
            lease.close()

    def test_stage_path_exchange_never_writes_the_replacement(self):
        lease = create_owned_stage(self.root)
        path = lease.quarantine_path
        retained_name = path.with_suffix('.old')
        os.rename(path, retained_name)
        replacement = self.root / 'replacement'
        replacement.write_bytes(b'user data')
        os.symlink(replacement.name, path)
        client = Client()
        try:
            with self.assertRaises(ValueError):
                lease.fetch(spec(), client)
            self.assertEqual(client.calls, [])
            self.assertEqual(replacement.read_bytes(), b'user data')
            self.assertEqual(retained_name.read_bytes(), b'')
        finally:
            lease.close()

    def test_mutated_stage_never_becomes_a_verified_snapshot(self):
        lease = create_owned_stage(self.root)
        try:
            lease.fetch(spec(), Client())
            lease.quarantine_path.write_bytes(b'X' * len(DATA))
            with self.assertRaises(ValueError):
                lease.snapshot()
        finally:
            lease.close()

    def test_protected_roots_and_git_ancestry_are_rejected(self):
        protected = self.root / '.env.private'
        with self.assertRaises(ValueError):
            create_owned_stage(protected)
        (self.root / '.git').mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            create_owned_stage(self.root)
        self.assertEqual([item.name for item in self.root.iterdir()], ['.git'])

    def test_name_collision_does_not_overwrite_or_remove_existing_file(self):
        expected = self.root / ('seed-' + '00' * 16 + '.zip')
        expected.write_bytes(b'preserve me')
        with mock.patch.object(transfer.os, 'urandom', return_value=b'\0' * 16):
            with self.assertRaises(FileExistsError):
                create_owned_stage(self.root)
        self.assertEqual(expected.read_bytes(), b'preserve me')

    def test_constructor_requires_factory_and_exact_generated_name(self):
        directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        path = self.root / 'ordinary-file'
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        try:
            with self.assertRaises(ValueError):
                transfer.OwnedStage(self.root, directory, 'seed-' + '0' * 32 + '.zip', fd)
            with self.assertRaises(ValueError):
                transfer.OwnedStage(self.root, directory, '.env', fd, _factory=transfer._FACTORY_TOKEN)
            self.assertEqual(path.read_bytes(), b'')
        finally:
            os.close(fd)
            os.close(directory)

    def test_failure_after_creation_reports_untrusted_path_and_preserves_file(self):
        with mock.patch.object(transfer.os, 'fchmod', side_effect=OSError('simulated')):
            with self.assertRaises(transfer.StageCreationError) as captured:
                create_owned_stage(self.root)
        error = captured.exception
        self.assertFalse(error.path_verified)
        self.assertEqual(error.close_errors, ())
        self.assertTrue(error.candidate.is_file())
        self.assertEqual(error.candidate.read_bytes(), b'')

    def test_random_failure_creates_no_file(self):
        with mock.patch.object(transfer.os, 'urandom', side_effect=OSError('simulated')):
            with self.assertRaises(OSError):
                create_owned_stage(self.root)
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
