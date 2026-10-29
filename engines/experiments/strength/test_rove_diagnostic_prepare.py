import hashlib
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import rove_diagnostic_prepare as prepare


class PreparationBoundaryTests(unittest.TestCase):
    @staticmethod
    def static_fixture(profile):
        data = {'source_recompiled_native_identical': True, 'engine_executed': False,
                'live_pointer_observed': False, 'tt_semantics_proven': False,
                'physical_placement_qualified': False, 'runtime_qualified': False,
                'playing_strength_qualified': False, 'entry_bytes_compile_assertion': 24,
                'candidate_symbol_value': 4096, 'candidate_tt_bytes': 12 << 30,
                'source_allocation_alignment': 4096, 'source': {'bytes': 1}, 'native': {'bytes': 1}}
        raw = json.dumps(data).encode()
        selected = {'b-static-tt.json': raw, 'compiler-sha256.txt': b'a' * 64,
                    'linker-sha256.txt': b'b' * 64, 'main.c': b'source', 'native/x': b'native'}
        static = {'symbol': 'qq', 'elf_symbol_offset': 4096,
                  'tt_bytes': (12 if profile == 'test-p16' else 192) << 30,
                  'source_sha256': hashlib.sha256(b'source').hexdigest(),
                  'native_sha256': hashlib.sha256(b'native').hexdigest(),
                  'compiler_replay_independently_verified': False,
                  'producer_authenticated': False, 'tt_semantics_proven': False}
        report = {'format': 'rove4k.github-source-observation-v1', 'family': 'B', 'profile': profile,
                  'variant': 'league-atomic', 'candidate_pins_match': True, 'candidate_files_observed': False,
                  'runtime_qualified': False, 'authorizes_go': False, 'b_static_correlation': dict(
            static, report_sha256=hashlib.sha256(raw).hexdigest(), producer_artifact_observed=True)}
        return selected, static, report

    def test_b_static_seed_and_producer_are_correlated_for_both_profiles(self):
        for profile in ('test-p16', 'test-p192'):
            selected, static, report = self.static_fixture(profile)
            with self.subTest(profile=profile), mock.patch.object(
                    prepare.rove_b_static_tt, 'validate_report_bytes', return_value=static) as validate:
                result = prepare._b_static_evidence(family='B', profile=profile, selected=selected,
                    build_manifest={'compiler': ['fixture']}, report=report, legacy=False)
                self.assertEqual(result['mode'], 'sealed-static-correlated')
                self.assertFalse(result['producer_report_authenticated'])
                self.assertFalse(result['authorizes_go'])
                self.assertEqual(result['static_correlation']['report_sha256'],
                                 hashlib.sha256(selected['b-static-tt.json']).hexdigest())
                self.assertEqual(result['static_files'], {name: prepare.diagnostic_candidates._b_pin(selected[name])
                                 for name in prepare.diagnostic_candidates._B_STATIC_NAMES})
                self.assertEqual(validate.call_args.args[0], selected['b-static-tt.json'])
                self.assertEqual(validate.call_args.kwargs['source'], b'source')
                self.assertEqual(validate.call_args.kwargs['native'], b'native')
                self.assertEqual(validate.call_args.kwargs['profile'], profile)
                self.assertEqual(validate.call_args.kwargs['compiler_sha'], 'a' * 64)
                self.assertEqual(validate.call_args.kwargs['linker_sha'], 'b' * 64)

    def test_b_incomplete_evidence_never_uses_legacy_exception(self):
        selected, _, report = self.static_fixture('test-p16')
        names = ('b-static-tt.json', 'compiler-sha256.txt', 'linker-sha256.txt')
        for count in (1, 2):
            for missing in itertools.combinations(names, count):
                incomplete = dict(selected)
                for name in missing:
                    del incomplete[name]
                for legacy in (False, True):
                    with self.subTest(missing=missing, legacy=legacy), self.assertRaisesRegex(ValueError, 'incomplete B static'):
                        prepare._b_static_evidence(family='B', profile='test-p16', selected=incomplete,
                                                   build_manifest={}, report=report, legacy=legacy)

    def test_b_legacy_must_be_explicit_and_cannot_carry_new_static_claim(self):
        selected = {'main.c': b'source', 'native/x': b'native'}
        for report in (None, {'b_static_correlation': None}):
            with self.subTest(report=report):
                with self.assertRaisesRegex(ValueError, 'explicit legacy'):
                    prepare._b_static_evidence(family='B', profile='test-p16', selected=selected,
                                               build_manifest={}, report=report, legacy=False)
                result = prepare._b_static_evidence(family='B', profile='test-p16', selected=selected,
                                                    build_manifest={}, report=report, legacy=True)
                self.assertEqual(result['mode'], 'legacy-no-static')
                self.assertIsNone(result['static_correlation'])
                self.assertFalse(result['producer_report_authenticated'] or result['authorizes_go'])
        with self.assertRaisesRegex(ValueError, 'legacy seed cannot match'):
            prepare._b_static_evidence(family='B', profile='test-p16', selected=selected, build_manifest={},
                                       report={'b_static_correlation': {'symbol': 'qq'}}, legacy=True)
        full, _, report = self.static_fixture('test-p16')
        with self.assertRaisesRegex(ValueError, 'legacy mode cannot'):
            prepare._b_static_evidence(family='B', profile='test-p16', selected=full, build_manifest={},
                                       report=report, legacy=True)

    def test_b_producer_report_mismatch_is_rejected(self):
        selected, static, report = self.static_fixture('test-p16')
        for field, value in (('report_sha256', '0' * 64), ('elf_symbol_offset', 12),
                             ('native_sha256', '0' * 64), ('source_sha256', '0' * 64),
                             ('tt_bytes', 1), ('producer_artifact_observed', 1),
                             ('producer_authenticated', True)):
            altered = dict(report, b_static_correlation=dict(report['b_static_correlation'], **{field: value}))
            with self.subTest(field=field), mock.patch.object(prepare.rove_b_static_tt, 'validate_report_bytes',
                    return_value=dict(static)), self.assertRaisesRegex(ValueError, 'producer static correlation differs'):
                prepare._b_static_evidence(family='B', profile='test-p16', selected=selected,
                                           build_manifest={}, report=altered, legacy=False)
        for bad in (None, {'variant': 'other'}, {'variant': 'league-atomic'}):
            with self.subTest(report=bad), mock.patch.object(prepare.rove_b_static_tt, 'validate_report_bytes',
                    return_value=dict(static)), self.assertRaises(ValueError):
                prepare._b_static_evidence(family='B', profile='test-p16', selected=selected,
                                           build_manifest={}, report=bad, legacy=False)
    def test_virtual_build_is_not_a_disk_path_exception(self):
        prepare._virtual_name('origin/A/build/control/build.json')
        with self.assertRaises(ValueError):
            prepare.diagnostic_candidates._check_path_components(Path('/tmp/example/build/main.c'))
        for path in ('origin/A/build/.env', 'origin/A/build/node_modules/a',
                     'origin/A/build/credential.json', '../build/x'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                prepare._virtual_name(path)

    def test_archive_pin_failure_creates_nothing(self):
        with tempfile.TemporaryDirectory(prefix='rove-check-') as tmp:
            root = Path(tmp).resolve()
            archive = root / 'seed.zip'
            archive.write_bytes(b'not a seed')
            out = root / 'candidate'
            with self.assertRaisesRegex(ValueError, 'seed archive identity differs'):
                prepare.prepare(archive_path=archive, archive_sha256='0' * 64,
                                manifest_sha256='1' * 64, family='A', profile='test-p16', out=out)
            self.assertFalse(out.exists())

    def test_report_binding_and_fail_closed_scope(self):
        manifest = {'source_origin': {'repository': 'example/repo', 'run_id': '12', 'run_attempt': '1',
                                      'head_sha': 'a' * 40},
                    'members': {'seal.json': {'sha256': 'b' * 64}}}
        row = {'family': 'A', 'profile': 'test-p16', 'source_seal': 'seal.json'}
        seal = {'bundle': {'sha256': 'c' * 64},
                'profiles': [{'family': 'A', 'profile': 'test-p16',
                              'old_expected_contract': {'whole_sha256': 'd' * 64}}]}
        metadata = {'id': 7, 'digest': 'sha256:' + 'e' * 64}
        artifact = SimpleNamespace(sha256='d' * 64)
        report = {'format': 'rove4k.github-source-observation-v1', 'repository': 'example/repo',
                  'run_id': 12, 'run_attempt': 1, 'source_head': 'a' * 40, 'family': 'A',
                  'profile': 'test-p16', 'artifact_id': 7, 'artifact_sha256': 'e' * 64,
                  'source_bundle_sha256': 'c' * 64, 'source_seal_sha256': 'b' * 64,
                  'candidate_pins_match': True, 'candidate_files_observed': False,
                  'runtime_qualified': False, 'authorizes_go': False}
        prepare._report_matches(report, manifest, row, seal, metadata, artifact)
        for field, altered in [('artifact_id', 8), ('source_head', 'f' * 40),
                               ('source_bundle_sha256', 'f' * 64), ('candidate_pins_match', False),
                               ('candidate_files_observed', True), ('authorizes_go', True)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepare._report_matches({**report, field: altered}, manifest, row, seal, metadata, artifact)

    def test_report_digest_mismatch_fails_before_output(self):
        with tempfile.TemporaryDirectory(prefix='rove-check-') as tmp:
            root = Path(tmp).resolve()
            archive, report, out = root / 'seed.zip', root / 'observation.json', root / 'candidate'
            archive.write_bytes(b'bounded input')
            report.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'producer report pin differs'):
                prepare.prepare(archive_path=archive, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                                manifest_sha256='1' * 64, family='A', profile='test-p192', out=out,
                                producer_report=report, producer_report_sha256='0' * 64)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
