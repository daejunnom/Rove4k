"""In-memory seed snapshot tests; no filesystem materialization or AWS calls."""
import hashlib
import io
import stat
import unittest
from unittest.mock import patch
import zipfile

try:
    from . import cloud_runtime as cloud
    from .league_seed_archive import inspect_snapshot
    from .test_cloud_runtime import archive_bytes, seed_fixture, WorkflowBytesFixture
except ImportError:
    import cloud_runtime as cloud
    from league_seed_archive import inspect_snapshot
    from test_cloud_runtime import archive_bytes, seed_fixture, WorkflowBytesFixture


def inspect(raw, manifest_sha, origin, **kwargs):
    return inspect_snapshot(raw, expected_archive_sha256=hashlib.sha256(raw).hexdigest(),
                            expected_archive_bytes=len(raw), expected_manifest_sha256=manifest_sha,
                            expected_origin=origin, **kwargs)


class SnapshotTests(unittest.TestCase):
    def test_proofed_seed_same_bytes_validates_without_claiming_authority(self):
        fixture = WorkflowBytesFixture()
        raw, manifest_sha = archive_bytes(fixture.seed, fixture.files)
        before = bytes(raw)
        with patch.object(cloud.urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')):
            result = inspect(raw, manifest_sha, fixture.seed['source_origin'])
        self.assertEqual(raw, before)
        self.assertEqual(result['archive_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['manifest_sha256'], manifest_sha)
        self.assertEqual(result['member_count'], len(fixture.files))
        self.assertTrue(result['scope']['workflow_proof_checked'])
        for key in ('host_authenticated', 'producer_authenticated', 'aws_cost_confirmed',
                    'materialized', 'runtime_qualified', 'launch_authorized', 'go_authorized'):
            self.assertIs(result['scope'][key], False)

    def test_legacy_seed_requires_explicit_unverified_mode(self):
        seed, files = seed_fixture()
        raw, manifest_sha = archive_bytes(seed, files)
        with self.assertRaisesRegex(ValueError, 'workflow proof'):
            inspect(raw, manifest_sha, seed['source_origin'])
        result = inspect(raw, manifest_sha, seed['source_origin'], require_workflow_proof=False)
        self.assertIs(result['scope']['workflow_proof_checked'], False)
        self.assertIs(result['scope']['producer_authenticated'], False)

    def test_archive_manifest_origin_and_input_types_are_pinned(self):
        seed, files = seed_fixture()
        raw, manifest_sha = archive_bytes(seed, files)
        base = dict(expected_archive_sha256=hashlib.sha256(raw).hexdigest(), expected_archive_bytes=len(raw),
                    expected_manifest_sha256=manifest_sha, expected_origin=seed['source_origin'],
                    require_workflow_proof=False)
        cases = ({'expected_archive_sha256': '0' * 64}, {'expected_archive_bytes': len(raw) + 1},
                 {'expected_archive_bytes': True}, {'expected_manifest_sha256': '0' * 64},
                 {'expected_origin': {**seed['source_origin'], 'head_sha': 'c' * 40}},
                 {'require_workflow_proof': 0})
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspect_snapshot(raw, **{**base, **change})
        with self.assertRaises(ValueError):
            inspect_snapshot(bytearray(raw), **base)

    def test_extra_duplicate_and_same_length_member_change_are_rejected(self):
        seed, files = seed_fixture()
        for extras in ([('unexpected', b'x')], [('rove/A/build.json', b'{}\n')]):
            raw, manifest_sha = archive_bytes(seed, files, extras)
            with self.subTest(extras=extras), self.assertRaises(ValueError):
                inspect(raw, manifest_sha, seed['source_origin'], require_workflow_proof=False)
        changed = dict(files)
        changed['rove/A/build.json'] = b'[]\n'
        raw, manifest_sha = archive_bytes(seed, changed)
        with self.assertRaisesRegex(ValueError, 'member differs'):
            inspect(raw, manifest_sha, seed['source_origin'], require_workflow_proof=False)

    def test_link_and_excessive_member_metadata_are_rejected(self):
        seed, files = seed_fixture()
        output = io.BytesIO()
        manifest_raw = cloud.ledger.canonical(seed) + b'\n'
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('seed.json', manifest_raw)
            for name, data in files.items():
                if name == 'rove/A/build.json':
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                    archive.writestr(entry, data)
                else:
                    archive.writestr(name, data)
        raw = output.getvalue()
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        with self.assertRaises(ValueError):
            inspect(raw, manifest_sha, seed['source_origin'], require_workflow_proof=False)
        normal, manifest_sha = archive_bytes(seed, files)
        with patch.object(cloud, 'MAX_MEMBER', 3), self.assertRaises(ValueError):
            inspect(normal, manifest_sha, seed['source_origin'], require_workflow_proof=False)

    def test_resealed_but_semantically_forged_workflow_is_rejected(self):
        fixture = WorkflowBytesFixture()
        fixture.run['head_sha'] = 'f' * 40
        fixture.write_documents()
        fixture.reseal()
        raw, manifest_sha = archive_bytes(fixture.seed, fixture.files)
        with self.assertRaises(ValueError):
            inspect(raw, manifest_sha, fixture.seed['source_origin'])

    def test_bad_zip_is_rejected_after_exact_archive_pin(self):
        seed, _ = seed_fixture()
        raw = b'not a zip file'
        with self.assertRaises(ValueError):
            inspect(raw, 'a' * 64, seed['source_origin'], require_workflow_proof=False)

    def test_nul_truncated_zip_name_is_not_accepted_as_manifest_alias(self):
        seed, files = seed_fixture()
        files['safe'] = b'payload'
        seed['members']['safe'] = {**cloud.pin(files['safe']), 'mode': 0o600}
        manifest_raw = cloud.ledger.canonical(seed) + b'\n'
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('seed.json', manifest_raw)
            for name, data in files.items():
                archive.writestr('safe!hidden' if name == 'safe' else name, data)
        original = output.getvalue()
        self.assertEqual(original.count(b'safe!hidden'), 2)
        malicious = original.replace(b'safe!hidden', b'safe\0hidden')
        with self.assertRaisesRegex(ValueError, 'name was normalized'):
            inspect(malicious, hashlib.sha256(manifest_raw).hexdigest(), seed['source_origin'],
                    require_workflow_proof=False)


if __name__ == '__main__':
    unittest.main()
