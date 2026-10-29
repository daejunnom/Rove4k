"""Pure in-memory path mapping tests; no materialization or AWS calls."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import unicodedata
import unittest

try:
    from . import league_seed_layout as layout
    from .test_cloud_runtime import WorkflowBytesFixture, archive_bytes, seed_fixture
except ImportError:
    import league_seed_layout as layout
    from test_cloud_runtime import WorkflowBytesFixture, archive_bytes, seed_fixture


def pinned_fixture():
    fixture = WorkflowBytesFixture()
    fixture.files['origin/A/build/build.json'] = b'{}\n'
    fixture.files['origin/A/build/main.c'] = b'/* fixture */\n'
    fixture.files['origin/A/build/single'] = b'x'
    fixture.files['origin/A/build/x'] = b'fake whole\n'
    fixture.files['origin/A/build/native/x'] = b'fake native\n'
    fixture.seed['rove'][0]['build'] = 'origin/A/build'
    fixture.seed['rove'][0]['profile'] = 'test-p16'
    fixture.reseal()
    raw, manifest_sha = archive_bytes(fixture.seed, fixture.files)
    pins = {'expected_archive_sha256': hashlib.sha256(raw).hexdigest(), 'expected_archive_bytes': len(raw),
            'expected_manifest_sha256': manifest_sha, 'expected_origin': fixture.seed['source_origin']}
    return fixture, raw, pins


class LayoutTests(unittest.TestCase):
    def test_exact_snapshot_produces_injective_build_mapping_with_original_pins(self):
        fixture, raw, pins = pinned_fixture()
        result = layout.build_layout(raw, **pins)
        self.assertEqual(result.physical_for('origin/A/build'), 'origin/A/__rove_seed_build_v1__')
        self.assertEqual(result.physical_for('origin/A/build/main.c'),
                         'origin/A/__rove_seed_build_v1__/main.c')
        self.assertEqual(result.logical_for('origin/A/__rove_seed_build_v1__/native/x'),
                         'origin/A/build/native/x')
        self.assertEqual(result.physical_for('seed.json'), 'seed.json')
        entries = {entry.logical: entry for entry in result.entries}
        for name, body in fixture.files.items():
            self.assertEqual(entries[name].sha256, hashlib.sha256(body).hexdigest())
            self.assertEqual(entries[name].bytes, len(body))
        for name in ('origin/A/build/main.c', 'origin/A/build/x', 'origin/A/build/native/x'):
            physical = result.physical_for(name)
            self.assertNotIn('/build/', '/' + physical + '/')
            self.assertEqual(result.logical_for(physical), name)
            self.assertEqual(entries[name].sha256, hashlib.sha256(fixture.files[name]).hexdigest())
        self.assertEqual(entries['seed.json'].sha256, pins['expected_manifest_sha256'])
        self.assertEqual(result.manifest['rove'][0]['build'], 'origin/A/build')
        detached = result.manifest
        detached['rove'][0]['build'] = 'untrusted'
        self.assertEqual(result.manifest['rove'][0]['build'], 'origin/A/build')
        self.assertFalse(result.scope()['materialized'])
        self.assertFalse(result.scope()['go_authorized'])
        self.assertFalse(result.scope()['archive_pin_checked'])
        self.assertTrue(result.scope()['independent_snapshot_recheck_required'])
        self.assertIs(result.verify_for(raw, **pins), result)

    def test_alias_namespace_case_and_file_directory_collisions_are_rejected(self):
        cases = (
            ('origin/A/build/main.c', 'origin/A/__rove_seed_build_v1__/main.c'),
            ('A/x', 'a/y'), ('Name/x', 'name/y'), ('same', 'SAME'),
            ('foo', 'Foo/bar'), ('café/x', 'cafe\u0301/y'),
            ('same/x', 'same/x'), ('seed.json', 'Seed.json/file'),
        )
        for names in cases:
            with self.subTest(names=names), self.assertRaises(ValueError):
                layout._pairs_for(names)

    def test_protected_nonportable_and_unsafe_names_are_rejected(self):
        for value in ('../a', '/tmp/a', 'a//b', 'a\\b', 'a/.env.local', 'a/.git/x',
                      'a/credentials/x', 'a/password.bin', 'a/id_ed25519', 'a/id_rsa.pub',
                      'a/id_dsa', 'a/id_ecdsa', 'a/ssh_host_rsa_key.pub', 'a/node_modules/x',
                      'a/dist/x', 'a/file.pem', 'a/token', 'a/x-token', 'a/aux.txt',
                      'a/space /x', 'a/bad\x00name', 'a/file\x7fname'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                layout._pairs_for((value,))

    def test_other_literal_build_substrings_are_not_rewritten(self):
        pairs = dict(layout._pairs_for(('origin/build.json', 'origin/transport-build/a',
                                       'origin/build/native/x')))
        self.assertEqual(pairs['origin/build.json'], 'origin/build.json')
        self.assertEqual(pairs['origin/transport-build/a'], 'origin/transport-build/a')
        self.assertEqual(pairs['origin/build/native/x'], 'origin/__rove_seed_build_v1__/native/x')
        greek = '\u0390'
        self.assertEqual(layout._case_key((greek,)), layout._case_key((unicodedata.normalize('NFD', greek),)))

    def test_layout_replacement_cannot_pass_independent_snapshot_verification(self):
        _, raw, pins = pinned_fixture()
        result = layout.build_layout(raw, **pins)
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            result.entries = ()
        with self.assertRaises(ValueError):
            replace(result, _pairs=(('origin/A/build', 'stolen'),))
        forged = replace(result, archive_sha256='0' * 64)
        with self.assertRaises(ValueError):
            forged.verify_for(raw, **pins)
        with self.assertRaises(ValueError):
            replace(result, _manifest_raw=b'{}')
        single = next(entry for entry in result.entries if entry.logical.endswith('/single'))
        with self.assertRaises(ValueError):
            replace(single, bytes=True)
        with self.assertRaises(ValueError):
            replace(single, mode=True)
        with self.assertRaises(ValueError):
            result.physical_for('not/pinned')
        with self.assertRaises(ValueError):
            result.logical_for('unowned/path')

    def test_untrusted_or_legacy_inputs_do_not_create_a_layout(self):
        fixture, raw, pins = pinned_fixture()
        for changed in ({'expected_archive_sha256': '0' * 64}, {'expected_manifest_sha256': '0' * 64},
                        {'expected_archive_bytes': True}, {'expected_origin': {**fixture.seed['source_origin'],
                                                                             'head_sha': 'f' * 40}}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                layout.build_layout(raw, **{**pins, **changed})
        legacy, files = seed_fixture()
        legacy_raw, manifest_sha = archive_bytes(legacy, files)
        with self.assertRaisesRegex(ValueError, 'workflow proof'):
            layout.build_layout(legacy_raw, expected_archive_sha256=hashlib.sha256(legacy_raw).hexdigest(),
                                expected_archive_bytes=len(legacy_raw), expected_manifest_sha256=manifest_sha,
                                expected_origin=legacy['source_origin'])


if __name__ == '__main__':
    unittest.main()
