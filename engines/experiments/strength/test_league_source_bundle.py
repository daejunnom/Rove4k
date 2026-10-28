"""Exercise source-only P16/P192 packaging with a tiny owned fixture.

The CI identity, strict admission and target seal authority are mocked here;
this does not claim actual GitHub, engine or target-runtime qualification.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

try:
    from . import league_source_bundle as source
except ImportError:
    import league_source_bundle as source


@unittest.skipUnless(os.name == 'posix', 'owned descriptor collection requires POSIX')
class LeagueSourceBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rove4k-source-bundle-test-')
        self.runner = Path(self.temp.name).resolve()
        self.out = self.runner / 'candidate'
        self.build = self.out / 'build'
        self.build.mkdir(parents=True)
        (self.build / 'build.json').write_text('{"family":"A"}\n', encoding='utf-8')
        (self.build / 'main.c').write_text('int main(void){return 0;}\n', encoding='utf-8')
        self.target = source._load('league_test_target_runtime', source.ROOT /
                                   'engines/experiments/tcec-next/target_runtime.py')
        self.transport = source._load('league_test_source_transport', source.ROOT /
                                      'engines/scripts/production_source_bundle.py')
        self.admitted = SimpleNamespace(family='A', profile_id='test-p16',
                                        representation='source-jit', full=True)
        self.verify = SimpleNamespace(admit_c_build=mock.Mock(return_value=self.admitted))
        self.context = {'repository': 'fixture/repo', 'head_sha': 'a' * 40,
                        'run_id': '42', 'run_attempt': '1'}
        self.patches = [
            mock.patch.object(self.transport, '_sources', return_value=('fixture-authority',)),
            mock.patch.object(self.transport, '_live_context', return_value=self.context),
            mock.patch.object(self.target, '_sealed_source'),
            mock.patch.object(self.target, 'build_source_seal', side_effect=self.make_seal),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp.cleanup()

    def make_seal(self, bundle, entries, *, verify, ci_context, restore_layout):
        self.assertEqual(Path(bundle), self.out / 'source-bundle.zip')
        self.assertEqual(entries, [(self.admitted, self.build, 'build')])
        self.assertIs(verify, self.verify)
        self.assertEqual(ci_context, self.context)
        self.assertEqual(restore_layout, {'runner_temp_root': str(self.runner),
                                          'output_root': str(self.out),
                                          'builds': {'build': str(self.build)}})
        return {'restore_layout': restore_layout,
                'profiles': [{'archive_prefix': 'build', 'build_root': str(self.build)}]}

    def run_export(self, **overrides):
        arguments = {'source_out': self.out, 'build': self.build, 'family': 'A',
                     'profile': 'test-p16', 'runner_temp': self.runner,
                     'ci_context': self.context, 'verify': self.verify,
                     'target': self.target, 'transport': self.transport}
        arguments.update(overrides)
        return source.export(**arguments)

    def test_owned_bytes_are_archived_under_actual_build_prefix(self):
        result = self.run_export()
        raw = (self.out / 'source-bundle.zip').read_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(set(archive.namelist()), {'build/build.json', 'build/main.c'})
            self.assertEqual(archive.read('build/main.c'), (self.build / 'main.c').read_bytes())
            self.assertTrue(all(item.compress_type == zipfile.ZIP_STORED for item in archive.infolist()))
        self.assertEqual(result['source_bundle']['bytes'], len(raw))
        self.assertEqual(result['source_bundle']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse(result['engine_executed'])
        self.assertFalse(result['runtime_qualified'])
        seal = json.loads((self.out / 'source-seal.json').read_bytes())
        self.assertEqual(seal['restore_layout']['builds']['build'], str(self.build))

    def test_family_profile_and_strict_admission_mismatch_are_rejected(self):
        for fields in ({'family': 'D'}, {'profile': 'test-p4'}, {'family': 'A', 'profile': 'test-p192'}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.run_export(**fields)
        self.assertFalse((self.out / 'source-bundle.zip').exists())

    def test_existing_outputs_are_never_replaced(self):
        bundle = self.out / 'source-bundle.zip'
        bundle.write_bytes(b'original')
        with self.assertRaisesRegex(ValueError, 'outputs must be new'):
            self.run_export()
        self.assertEqual(bundle.read_bytes(), b'original')
        self.assertFalse((self.out / 'source-seal.json').exists())

    def test_changed_build_after_seal_is_rejected_before_writing_seal(self):
        def mutate(*args, **kwargs):
            seal = self.make_seal(*args, **kwargs)
            (self.build / 'main.c').write_text('changed\n', encoding='utf-8')
            return seal
        self.target.build_source_seal.side_effect = mutate
        with self.assertRaisesRegex(ValueError, 'changed during collection'):
            self.run_export()
        self.assertFalse((self.out / 'source-seal.json').exists())

    def test_build_must_be_exact_owned_child(self):
        other = self.out / 'other'
        other.mkdir()
        with self.assertRaisesRegex(ValueError, 'exact build child'):
            self.run_export(build=other)
        self.assertFalse((self.out / 'source-bundle.zip').exists())

    def test_protected_components_are_rejected_before_open_or_read(self):
        # The directory entries are synthetic: no protected file or directory
        # is created, inspected, opened, or read by this test.
        class Scan:
            def __init__(self, name):
                self.name = name
            def __enter__(self):
                return iter([SimpleNamespace(name=self.name)])
            def __exit__(self, *unused):
                return False

        reader = SimpleNamespace(
            open_directory=lambda path: os.open(path, os.O_RDONLY | os.O_DIRECTORY),
            file_stamp=lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns),
            same_directory=lambda path, fd: None,
            read_regular_at=mock.Mock(side_effect=AssertionError('protected file read')))
        target = SimpleNamespace(input_reader=lambda: reader)
        for name in ('.npmrc', '.netrc', 'credentials', 'service_account',
                     'id_rsa.pub', 'build'):
            with self.subTest(component=name), \
                 mock.patch.object(source.os, 'scandir', return_value=Scan(name)), \
                 mock.patch.object(source.os, 'stat', side_effect=AssertionError('protected component stat')):
                with self.assertRaisesRegex(ValueError, 'protected or heavy'):
                    source._snapshot(self.build, target)
        reader.read_regular_at.assert_not_called()

    def test_protected_component_is_rejected_before_admission(self):
        # The entry exists only in the scandir mock; no protected file exists.
        class Scan:
            def __enter__(self):
                return iter([SimpleNamespace(name='credentials')])
            def __exit__(self, *unused):
                return False

        with mock.patch.object(source.os, 'scandir', return_value=Scan()):
            with self.assertRaisesRegex(ValueError, 'protected or heavy'):
                self.run_export()
        self.verify.admit_c_build.assert_not_called()
        self.assertFalse((self.out / 'source-bundle.zip').exists())

    def test_build_mutation_during_admission_is_rejected_before_archive(self):
        def mutate(record, build):
            (build / 'main.c').write_text('changed during admission\n', encoding='utf-8')
            return self.admitted
        self.verify.admit_c_build.side_effect = mutate
        with self.assertRaisesRegex(ValueError, 'changed during admission'):
            self.run_export()
        self.assertFalse((self.out / 'source-bundle.zip').exists())

    def test_seed_archive_32mib_boundary_before_writing(self):
        # A tiny byte payload reports a synthetic length; neither case writes
        # a large fixture or inspects generated output trees.
        class SizedBytes(bytes):
            def __new__(cls, size):
                instance = super().__new__(cls, b'small fixture')
                instance.size = size
                return instance
            def __len__(self):
                return self.size

        class ReachedWrite(Exception):
            pass

        with mock.patch.object(self.transport, '_zip_bytes', return_value=SizedBytes(32 << 20)), \
             mock.patch.object(self.transport, '_write_new', side_effect=ReachedWrite) as writer:
            with self.assertRaises(ReachedWrite):
                self.run_export()
            writer.assert_called_once()
        with mock.patch.object(self.transport, '_zip_bytes', return_value=SizedBytes((32 << 20) + 1)), \
             mock.patch.object(self.transport, '_write_new') as writer:
            with self.assertRaisesRegex(ValueError, 'seed member bound'):
                self.run_export()
            writer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
