"""Synthetic bootstrap-only fixtures; no AWS, filesystem or engine execution."""
from dataclasses import replace
import hashlib
import io
import json
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

try:
    from .league_pinned_bootstrap import (BootstrapRequest, LoaderPin, fetch_for_verified_loader,
                                          validate_declared_receipt)
except ImportError:
    from league_pinned_bootstrap import (BootstrapRequest, LoaderPin, fetch_for_verified_loader,
                                         validate_declared_receipt)

ACCOUNT = '123456789012'
INSTANCE = 'i-' + '1' * 17
BOOT = '12345678-1234-1234-1234-123456789abc'
TREE = 'source-tree'
LOADER = TREE + '/engines/experiments/strength/cloud_runtime.py'
DEPENDENCY = TREE + '/engines/experiments/strength/ledger.py'
PROGRAM = b'trusted outer bootstrap source fixture'
LOADER_BYTES = b'# fixture loader: not executed\n'
DEPENDENCY_BYTES = b'# fixture dependency: not executed\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(*, source=LOADER_BYTES, origin=None, duplicate=False, link=False, other='origin/A/build/main.c'):
    files = {LOADER: source, DEPENDENCY: DEPENDENCY_BYTES, other: b'intentionally not executed'}
    manifest = {'format': 'rove4k-cloud-seed-v1', 'source_tree': TREE,
                'source_origin': origin or {'repository': 'daejunnom/Rove4k', 'head_sha': 'a' * 40,
                                            'run_id': '17', 'run_attempt': '1'},
                'members': {name: {'bytes': len(raw), 'sha256': sha(raw), 'mode': 0o600}
                            for name, raw in files.items()}}
    manifest_raw = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('seed.json', manifest_raw)
        for name, data in files.items():
            if link and name == other:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = 0o120777 << 16
                archive.writestr(info, data)
            else:
                archive.writestr(name, data)
        if duplicate:
            with __import__('warnings').catch_warnings():
                __import__('warnings').simplefilter('ignore', UserWarning)
                archive.writestr(LOADER, source)
    return buffer.getvalue(), manifest_raw


def request(data, manifest):
    return BootstrapRequest(campaign='league-test', plan_sha256='b' * 64,
        bucket='league-campaign-bucket', bucket_region='ap-southeast-2', bucket_owner=ACCOUNT,
        key='league-test/seed/archive.zip', version_id='immutable-version', archive_sha256=sha(data),
        archive_bytes=len(data), manifest_sha256=sha(manifest), repository='daejunnom/Rove4k',
        source_head='a' * 40, producer_run_id='17', producer_run_attempt='1', host_account=ACCOUNT,
        host_region='ap-southeast-1', host_instance_id=INSTANCE, host_boot_id=BOOT,
        host_launch_token='second-host-token', profile='test-p16',
        host_role_arn=f'arn:aws:iam::{ACCOUNT}:role/team/league-host',
        caller_arn=f'arn:aws:sts::{ACCOUNT}:assumed-role/league-host/{INSTANCE}',
        transfer_quote_id='quote-for-regions', quote_observed_at=1700000000,
        bootstrap_sha256=sha(PROGRAM), loader_pins=(LoaderPin(LOADER, sha(LOADER_BYTES), len(LOADER_BYTES)),
                                                     LoaderPin(DEPENDENCY, sha(DEPENDENCY_BYTES), len(DEPENDENCY_BYTES))))


class Client:
    def __init__(self, data, *, region='ap-southeast-2', version='immutable-version', length=None):
        self.meta = SimpleNamespace(region_name=region)
        self.body = io.BytesIO(data)
        self.version = version
        self.length = len(data) if length is None else length
        self.calls = []

    def get_object(self, **kwargs):
        self.calls.append(kwargs)
        return {'Body': self.body, 'ContentLength': self.length, 'VersionId': self.version}


class BootstrapTests(unittest.TestCase):
    def test_exact_cross_region_bytes_are_returned_but_not_executed_or_authorized(self):
        data, manifest = fixture()
        req, client = request(data, manifest), Client(data)
        result = fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
        self.assertEqual(client.calls, [{'Bucket': req.bucket, 'Key': req.key, 'VersionId': req.version_id,
                                        'ExpectedBucketOwner': ACCOUNT}])
        self.assertTrue(client.body.closed)
        self.assertEqual(result.archive, data)
        self.assertEqual(dict(result.loader_sources), {LOADER: LOADER_BYTES, DEPENDENCY: DEPENDENCY_BYTES})
        self.assertEqual(result.receipt['host_launch_token'], 'second-host-token')
        self.assertEqual(result.receipt['transfer_quote_id'], 'quote-for-regions')
        self.assertEqual(result.receipt['bucket'], req.bucket)
        self.assertEqual(result.receipt['key'], req.key)
        self.assertEqual(result.receipt['declared_host_role_arn'], req.host_role_arn)
        self.assertEqual(result.receipt['bootstrap_sha256'], req.bootstrap_sha256)
        self.assertEqual(result.receipt['repository'], req.repository)
        self.assertEqual(result.receipt['source_head'], req.source_head)
        self.assertEqual(result.receipt['producer_run_id'], req.producer_run_id)
        checked = validate_declared_receipt(req, result.receipt_json)
        self.assertTrue(checked['matches_declared_request'])
        self.assertFalse(checked['actual_fetch_proven'])
        self.assertFalse(checked['receipt_origin_authenticated'])
        self.assertNotIn('fixture loader', repr(result))
        self.assertNotIn('intentionally not executed', repr(result))
        scope = result.receipt['scope']
        self.assertTrue(scope['archive_pin_checked'])
        for name in ('running_bootstrap_authenticated', 'complete_loader_closure_verified',
                     'host_authenticated', 'producer_authenticated', 'all_seed_members_verified',
                     'actual_cost_confirmed', 'materialized', 'go_authorized'):
            self.assertIs(scope[name], False)
        scope['go_authorized'] = True
        self.assertIs(result.receipt['scope']['go_authorized'], False)
        self.assertIsInstance(result.receipt_json, bytes)

    def test_wrong_bootstrap_pin_or_client_region_fails_before_network(self):
        data, manifest = fixture()
        req, client = request(data, manifest), Client(data)
        with self.assertRaises(ValueError):
            fetch_for_verified_loader(req, client, bootstrap_source=b'not-the-program')
        self.assertEqual(client.calls, [])
        client = Client(data, region='ap-southeast-1')
        with self.assertRaises(ValueError):
            fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
        self.assertEqual(client.calls, [])

    def test_host_and_owner_declarations_are_bound_without_claiming_authentication(self):
        data, manifest = fixture()
        req = request(data, manifest)
        for change in ({'bucket_owner': '999999999999'}, {'host_region': 'invalid'},
                       {'caller_arn': f'arn:aws:sts::{ACCOUNT}:assumed-role/other/{INSTANCE}'},
                       {'host_boot_id': '00000000-0000-0000-0000-000000000000'},
                       {'quote_observed_at': True}, {'profile': 'w256'},
                       {'host_role_arn': f'arn:aws:iam::{ACCOUNT}:role/a//b'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(req, **change)

    def test_wrong_version_length_or_archive_digest_never_returns_bytes(self):
        data, manifest = fixture()
        req = request(data, manifest)
        clients = (Client(data, version='other'), Client(data, length=len(data) + 1),
                   Client(data[:-1], length=len(data)))
        for client in clients:
            with self.subTest(version=client.version, length=client.length), self.assertRaises(ValueError):
                fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
            self.assertTrue(client.body.closed)

    def test_zip_duplicate_symlink_and_protected_path_are_refused(self):
        for options in ({'duplicate': True}, {'link': True}, {'other': 'source/.env'}):
            data, manifest = fixture(**options)
            with self.subTest(options=options), self.assertRaises(ValueError):
                fetch_for_verified_loader(request(data, manifest), Client(data), bootstrap_source=PROGRAM)

    def test_modified_loader_and_wrong_origin_are_refused_even_with_archive_repin(self):
        values = (fixture(source=b'different fixture loader'),
                  fixture(origin={'repository': 'daejunnom/Rove4k', 'head_sha': 'd' * 40,
                                  'run_id': '17', 'run_attempt': '1'}))
        for data, manifest in values:
            with self.subTest(archive=sha(data)), self.assertRaises(ValueError):
                fetch_for_verified_loader(request(data, manifest), Client(data), bootstrap_source=PROGRAM)

    def test_integer_origin_allowed_but_boolean_not_accepted(self):
        origin = {'repository': 'daejunnom/Rove4k', 'head_sha': 'a' * 40, 'run_id': 17, 'run_attempt': 1}
        data, manifest = fixture(origin=origin)
        fetch_for_verified_loader(request(data, manifest), Client(data), bootstrap_source=PROGRAM)
        origin['run_attempt'] = True
        data, manifest = fixture(origin=origin)
        with self.assertRaises(ValueError):
            fetch_for_verified_loader(request(data, manifest), Client(data), bootstrap_source=PROGRAM)

    def test_independent_runtime_pin_is_required(self):
        data, manifest = fixture()
        req = request(data, manifest)
        req = replace(req, loader_pins=(req.loader_pins[1],))
        with self.assertRaises(ValueError):
            fetch_for_verified_loader(req, Client(data), bootstrap_source=PROGRAM)

    def test_injected_client_exceptions_do_not_surface_raw_details(self):
        data, manifest = fixture()
        req = request(data, manifest)
        class ErrorClient(Client):
            def get_object(self, **_kwargs):
                raise RuntimeError('sensitive synthetic client error')
        with self.assertRaisesRegex(ValueError, '^S3 request failed$') as captured:
            fetch_for_verified_loader(req, ErrorClient(data), bootstrap_source=PROGRAM)
        self.assertTrue(captured.exception.__suppress_context__)

        class ErrorBody(io.BytesIO):
            def read(self, _wanted):
                raise RuntimeError('sensitive synthetic read error')
        client = Client(data)
        client.body = ErrorBody(data)
        with self.assertRaisesRegex(ValueError, '^S3 body read failed$') as captured:
            fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
        self.assertTrue(captured.exception.__suppress_context__)
        self.assertTrue(client.body.closed)

        class MetaFailure:
            @property
            def region_name(self):
                raise RuntimeError('sensitive synthetic region error')
        client = Client(data)
        client.meta = MetaFailure()
        with self.assertRaisesRegex(ValueError, '^S3 client region unavailable$') as captured:
            fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
        self.assertTrue(captured.exception.__suppress_context__)
        self.assertEqual(client.calls, [])

        class CloseFailure(io.BytesIO):
            def close(self):
                super().close()
                raise RuntimeError('sensitive synthetic close error')
        client = Client(data)
        client.body = CloseFailure(data)
        with self.assertRaisesRegex(ValueError, '^S3 body close failed$') as captured:
            fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
        self.assertTrue(captured.exception.__suppress_context__)

    def test_zip_metadata_count_and_directory_are_bounded_before_open(self):
        data, manifest = fixture()
        pos = data.rfind(b'PK\x05\x06')
        excessive = bytearray(data)
        struct.pack_into('<H', excessive, pos + 8, 20001)
        struct.pack_into('<H', excessive, pos + 10, 20001)
        for mutated in (bytes(excessive), data + b'trailer'):
            with self.subTest(length=len(mutated)), self.assertRaises(ValueError):
                fetch_for_verified_loader(request(mutated, manifest), Client(mutated), bootstrap_source=PROGRAM)

    def test_zip_truncated_original_name_is_rejected(self):
        data, manifest = fixture()
        original = zipfile.ZipFile.infolist
        def tampered(archive):
            rows = original(archive)
            rows[0].orig_filename = rows[0].filename + '\0hidden'
            return rows
        with patch.object(zipfile.ZipFile, 'infolist', tampered), self.assertRaises(ValueError):
            fetch_for_verified_loader(request(data, manifest), Client(data), bootstrap_source=PROGRAM)

    def test_nonstring_client_values_are_rejected_without_comparing_them(self):
        data, manifest = fixture()
        req = request(data, manifest)
        class MaliciousComparison:
            def __ne__(self, _other):
                raise RuntimeError('synthetic sensitive comparison')
        client = Client(data)
        client.meta.region_name = MaliciousComparison()
        with self.assertRaisesRegex(ValueError, '^S3 client region differs from source bucket$'):
            fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
        self.assertEqual(client.calls, [])
        client = Client(data)
        client.version = MaliciousComparison()
        with self.assertRaisesRegex(ValueError, '^S3 version or size differs$'):
            fetch_for_verified_loader(req, client, bootstrap_source=PROGRAM)
        self.assertTrue(client.body.closed)

    def test_receipt_forgery_and_same_archive_other_request_are_refused(self):
        data, manifest = fixture()
        req = request(data, manifest)
        result = fetch_for_verified_loader(req, Client(data), bootstrap_source=PROGRAM)
        canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=False, allow_nan=False).encode() + b'\n'
        for key, replacement in (
            ('bucket', 'other-campaign-bucket'),
            ('key', 'league-test/seed/other.zip'),
            ('declared_host_role_arn', f'arn:aws:iam::{ACCOUNT}:role/other-host'),
            ('bootstrap_sha256', 'd' * 64),
            ('source_head', 'e' * 40),
            ('producer_run_id', '99'),
        ):
            forged = result.receipt
            forged[key] = replacement
            with self.subTest(field=key), self.assertRaises(ValueError):
                validate_declared_receipt(req, canonical(forged))
        forged = result.receipt
        forged['scope']['go_authorized'] = True
        with self.assertRaises(ValueError):
            validate_declared_receipt(req, canonical(forged))
        for change in ({'bucket': 'other-campaign-bucket'}, {'key': 'league-test/seed/other.zip'},
                       {'bootstrap_sha256': 'd' * 64}, {'source_head': 'e' * 40},
                       {'producer_run_id': '99'}):
            other = replace(req, **change)
            self.assertEqual(other.archive_sha256, req.archive_sha256)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_declared_receipt(other, result.receipt_json)
        other_role = replace(req, host_role_arn=f'arn:aws:iam::{ACCOUNT}:role/other-host',
                             caller_arn=f'arn:aws:sts::{ACCOUNT}:assumed-role/other-host/{INSTANCE}')
        with self.assertRaises(ValueError):
            validate_declared_receipt(other_role, result.receipt_json)

    def test_duplicate_manifest_json_keys_are_refused(self):
        data, manifest = fixture()
        duplicated = manifest.replace(b'"format":', b'"format":"invalid", "format":', 1)
        # Remove the injected space to keep this a syntactically valid JSON
        # attack; duplicate keys are refused independently of canonical form.
        duplicated = duplicated.replace(b'", "format"', b'","format"')
        with zipfile.ZipFile(io.BytesIO(data)) as old:
            rows = [(info.filename, old.read(info)) for info in old.infolist() if info.filename != 'seed.json']
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as new:
            new.writestr('seed.json', duplicated)
            for name, raw in rows:
                new.writestr(name, raw)
        repinned = out.getvalue()
        with self.assertRaises(ValueError):
            fetch_for_verified_loader(request(repinned, duplicated), Client(repinned), bootstrap_source=PROGRAM)


if __name__ == '__main__':
    unittest.main()
