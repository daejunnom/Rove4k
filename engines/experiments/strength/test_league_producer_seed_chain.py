"""Synthetic league producer-to-seed contract; never an engine qualification.

The Ubuntu/CI identity and strict source admission are fixture substitutions.
The exporter, archive bytes and seed.prepare are the actual implementation.
"""
from __future__ import annotations

import importlib.util
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

try:
    from . import league_source_bundle as exporter, seed
    from .test_seed import Fixture as SeedFixture, git
except ImportError:
    import league_source_bundle as exporter
    import seed
    from test_seed import Fixture as SeedFixture, git


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(sys.platform == 'linux', 'Linux source transport uses directory descriptors')
class LeagueProducerSeedChain(unittest.TestCase):
    def test_exported_source_bundle_is_consumed_by_seed_for_both_profiles(self):
        root_repo = Path(seed.__file__).resolve().parents[3]
        target_tests = load('league_chain_target_fixture', root_repo / 'engines/experiments/tcec-next/test_target_runtime.py')
        transport = load('league_chain_transport', root_repo / 'engines/scripts/production_source_bundle.py')
        ci_runner = '/home/runner/work/_temp'
        available_runner = (os.environ.get('RUNNER_TEMP') == ci_runner and
                            os.path.isdir(ci_runner) and os.access(ci_runner, os.W_OK))
        for profile in ('test-p16', 'test-p192'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory(
                    prefix='rove-league-chain-', dir=ci_runner if available_runner else None) as directory:
                root = Path(directory)
                fixture_root = root / 'seed-fixture'
                fixture_root.mkdir()
                fixture = SeedFixture(fixture_root)
                names = ['engines/experiments/strength/' + name + '.py' for name in seed.LEAGUE_HOST_MODULES]
                names += list(seed.LEAGUE_CORE_R)
                for name in names:
                    path = fixture.repo / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'# synthetic league transport source\n')
                git(fixture.repo, 'add', '--', *names)
                git(fixture.repo, '-c', 'user.name=Transport Fixture', '-c',
                    'user.email=fixture@example.invalid', 'commit', '-qm', 'synthetic league closure')
                head = git(fixture.repo, 'rev-parse', 'HEAD').decode().strip()
                fixture.config['checkout']['commit'] = head
                fixture.config['source_origin']['head_sha'] = head
                metadata = json.loads(Path(fixture.inputs['metadata/A-artifact.json']['path']).read_bytes())
                metadata['workflow_run']['head_sha'] = head
                fixture.rewrite('metadata/A-artifact.json', metadata)

                target_root = root / 'target-fixture'
                target_root.mkdir()
                source = target_tests.Fixture(target_root, profile_id='test-p4')
                league_profiles = load('league_chain_resources', root_repo / 'engines/scripts/league_resource_profiles.py')
                resources = league_profiles.resource_profile(target_tests.VERIFY.contracts(), profile).to_record(24)
                source.admitted = replace(source.admitted, profile_id=profile, resources=resources)
                source.manifest['resources'] = resources
                (source.build / 'build.json').write_text(json.dumps(source.manifest, sort_keys=True) + '\n')
                target = target_tests.TARGET
                runner = Path(ci_runner) if available_runner else root / 'runner-temp'
                out = root / 'league-output' if available_runner else runner / 'league-output'
                out.mkdir(parents=True)
                shutil.copytree(source.build, out / 'build')
                context = target.CIContext('fixture/Rove4k', head, '123', '1')
                environment = {**source.environment(), 'GITHUB_REPOSITORY': context.repository,
                               'GITHUB_SHA': head, 'RUNNER_TEMP': str(runner)}
                with patch.object(target, '_source_host', return_value={'ID': 'ubuntu', 'VERSION_ID': '24.04'}), \
                        patch.object(target, '_checkout_head', return_value=head), patch.dict(os.environ, environment):
                    result = exporter.export(source_out=out, build=out / 'build', family='A', profile=profile,
                        runner_temp=runner, ci_context=context, verify=source.verify, target=target, transport=transport)
                self.assertFalse(result['engine_executed'] or result['runtime_qualified'])
                bundle = Path(result['source_bundle']['path']).read_bytes()
                seal = json.loads(Path(result['source_seal']['path']).read_bytes())
                self.assertEqual(seal['bundle'], seed.pin(bundle))
                self.assertEqual(seal['profiles'][0]['archive_prefix'], 'build')

                # Exercise the unmodified seal on GitHub's fixed runner path.
                # Else translate only the local fixture's temporary path to
                # the logical CI location; never claim a live CI seal.
                ci_out = seal['restore_layout']['output_root'] if available_runner else ci_runner + '/league-output'
                if not available_runner:
                    seal['profiles'][0]['build_root'] = ci_out + '/build'
                    seal['restore_layout'] = {'runner_temp_root': ci_runner, 'output_root': ci_out,
                                              'builds': {'build': ci_out + '/build'}}
                bundle_path = Path(fixture.inputs['origin/A/source-bundle.zip']['path'])
                bundle_path.write_bytes(bundle)
                fixture.inputs['origin/A/source-bundle.zip'] = {'path': str(bundle_path), **seed.pin(bundle)}
                fixture.rewrite('origin/A/source-seal.json', seal)
                fixture.config['rove'][0].update(profile=profile, build='origin/A/build')
                fixture.config['original_layout']['roots'][0]['original_root'] = ci_out
                result_seed = fixture.prepare(root / 'seed-out')
                manifest = json.loads(Path(result_seed['seed_manifest']['path']).read_bytes())
                with zipfile.ZipFile(result_seed['archive']['path']) as archive:
                    for name in ('build.json', 'main.c', 'native/x', 'x'):
                        self.assertEqual(archive.read('origin/A/build/' + name), (out / 'build' / name).read_bytes())
                self.assertEqual(manifest['rove'][0]['profile'], profile)
                self.assertFalse(result_seed['engine_executed'] or result_seed['native_qualified'])

                # Re-pinning a substituted ZIP in the seed input map must not
                # make it match the separately exported source seal.
                altered = bundle + b'changed-transport'
                bundle_path.write_bytes(altered)
                fixture.inputs['origin/A/source-bundle.zip'] = {'path': str(bundle_path), **seed.pin(altered)}
                with self.assertRaisesRegex(ValueError, 'raw source bundle differs'):
                    fixture.prepare(root / 'seed-tampered')

                # Restore the bytes and reject a seal naming another profile.
                bundle_path.write_bytes(bundle)
                fixture.inputs['origin/A/source-bundle.zip'] = {'path': str(bundle_path), **seed.pin(bundle)}
                seal['profiles'][0]['profile'] = 'test-p192' if profile == 'test-p16' else 'test-p16'
                fixture.rewrite('origin/A/source-seal.json', seal)
                with self.assertRaisesRegex(ValueError, 'source profile is ambiguous'):
                    fixture.prepare(root / 'seed-wrong-profile')


if __name__ == '__main__':
    unittest.main()
