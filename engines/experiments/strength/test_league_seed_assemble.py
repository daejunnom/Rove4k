"""Offline producer collection through the actual seed consumer.

GitHub API responses, CI identity and inputs are synthetic.  These tests do
not run chess engines, authenticate a host, or grant release authority.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

try:
    from . import league_seed_assemble as collector, seed
    from .test_seed import Fixture, git
except ImportError:
    import league_seed_assemble as collector
    import seed
    from test_seed import Fixture, git


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def zip_bytes(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in files.items():
            target.writestr(name, data)
    return out.getvalue()


@unittest.skipUnless(sys.platform == 'linux', 'Linux seed transport path required')
class SeedAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rove-seed-assembly-')
        self.root = Path(self.tmp.name).resolve()
        fixture_root = self.root / 'fixture'
        fixture_root.mkdir()
        self.fixture = Fixture(fixture_root)
        # Synthetic league-specific checkout closure, as in the existing
        # exporter-to-seed tests. No committed engine or peer code is copied.
        names = ['engines/experiments/strength/' + n + '.py' for n in seed.LEAGUE_HOST_MODULES]
        names += list(seed.LEAGUE_CORE_R)
        for name in names:
            path = self.fixture.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'# synthetic league transport source\n')
        git(self.fixture.repo, 'add', '--', *names)
        git(self.fixture.repo, '-c', 'user.name=Transport Fixture', '-c',
            'user.email=fixture@example.invalid', 'commit', '-qm', 'league closure')
        head = git(self.fixture.repo, 'rev-parse', 'HEAD').decode().strip()
        self.base = copy.deepcopy(self.fixture.config)
        self.base['source_origin'] = {'repository': 'daejunnom/Rove4k', 'head_sha': head,
                                      'run_id': '123', 'run_attempt': '1'}
        self.base['checkout']['commit'] = head
        self.base['inputs'] = {n: v for n, v in self.base['inputs'].items()
                               if not n.startswith(('origin/', 'metadata/'))}
        self.base['rove'] = []
        self.base['original_layout'] = {'roots': []}
        self.selection = {'family': 'A', 'profile': 'test-p16', 'variant': 'control', 'artifact_id': 456}
        self.original = '/home/runner/work/_temp/rove4k-league-A-test-p16-control-1'
        self.files = {'build/build.json': b'{}\n', 'build/main.c': b'/* synthetic */\n'}
        bundle = zip_bytes(self.files)
        seal = {'format': 'rove4k.source-bundle-seal.v1', 'ci_context': self.base['source_origin'],
                'producer': {'ID': 'ubuntu', 'VERSION_ID': '24.04'}, 'bundle_format': 'zip',
                'bundle': seed.pin(bundle), 'members': {n: seed.pin(v) for n, v in self.files.items()},
                'profiles': [{'family': 'A', 'profile': 'test-p16', 'full': True,
                              'representation': 'source-jit', 'archive_prefix': 'build',
                              'build_root': self.original + '/build',
                              'input_manifest': seed.pin(self.files['build/build.json'])}],
                'restore_layout': {'runner_temp_root': '/home/runner/work/_temp',
                                   'output_root': self.original, 'builds': {'build': self.original + '/build'}}}
        tool = 'engines/scripts/production_input.py'
        report = {'family': 'A', 'profile': 'test-p16', 'complete': True,
                  'verifier_inputs': {tool: seed.pin((self.fixture.repo / tool).read_bytes())}}
        stream = b'fixture output\n'
        commands = {'stdout': {'path': self.original + '/rules/tool.stdout', **seed.pin(stream)}}
        self.outer = {'source-bundle.zip': bundle, 'source-seal.json': encoded(seal),
                      'rules/probe/rules.json': encoded(report), 'rules/probe/cases.json': b'[]',
                      'rules/probe/fixture.c': b'/* synthetic */', 'rules/commands.json': encoded(commands),
                      'rules/tool.stdout': stream}
        self.artifact_zip = zip_bytes(self.outer)
        self.digest = 'sha256:' + hashlib.sha256(self.artifact_zip).hexdigest()
        name = 'league-source-A-test-p16-control-' + head + '-1'
        self.artifact = {'id': 456, 'name': name, 'digest': self.digest, 'expired': False,
                         'workflow_run': {'id': 123, 'head_sha': head, 'repository_id': 42,
                                          'head_repository_id': 42, 'head_branch': 'feature'}}
        self.run = {'id': 123, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success',
                    'path': '.github/workflows/league-profile-bootstrap.yml', 'event': 'push',
                    'head_sha': head, 'repository': {'full_name': 'daejunnom/Rove4k', 'id': 42},
                    'head_repository': {'id': 42}, 'head_branch': 'feature'}
        raw_commit = git(self.fixture.repo, 'cat-file', 'commit', head)
        headers = raw_commit.split(b'\n\n', 1)[0].splitlines()
        self.commit = {'sha': head,
                       'tree': {'sha': next(x[5:].decode() for x in headers if x.startswith(b'tree '))},
                       'parents': [{'sha': x[7:].decode()} for x in headers if x.startswith(b'parent ')]}
        self.job = {'id': 789, 'run_id': 123, 'head_sha': head, 'name': 'source-A-test-p16-control',
                    'status': 'completed', 'conclusion': 'success', 'steps': [
                        {'name': 'Seal the admitted source for P16 and P192 seed transport',
                         'status': 'completed', 'conclusion': 'success'},
                        {'name': 'Preserve actual artifacts, bounded command logs and failures',
                         'status': 'completed', 'conclusion': 'success'}]}

    def tearDown(self):
        self.tmp.cleanup()

    def get(self, path):
        if '/pulls/' in path:
            return self.pull
        if '/git/commits/' in path:
            return self.commit
        if '/attempts/1/jobs?' in path:
            return {'total_count': 1, 'jobs': [self.job]}
        if '/runs/123/artifacts?' in path:
            return {'total_count': 1, 'artifacts': [self.artifact]}
        if '/actions/artifacts/456' in path:
            return self.artifact
        if '/runs/123/attempts/1' in path:
            return self.run
        raise AssertionError(path)

    def assemble(self, out, *, archive=None):
        return collector.assemble(self.base, [self.selection], out=out, get=self.get,
                                  archive=archive or (lambda artifact_id: self.artifact_zip))

    def set_profile(self, profile):
        old = self.selection['profile']
        self.selection['profile'] = profile
        self.original = self.original.replace(old, profile)
        seal = json.loads(self.outer['source-seal.json'])
        seal['profiles'][0]['profile'] = profile
        seal['profiles'][0]['build_root'] = self.original + '/build'
        seal['restore_layout']['output_root'] = self.original
        seal['restore_layout']['builds']['build'] = self.original + '/build'
        self.outer['source-seal.json'] = encoded(seal)
        report = json.loads(self.outer['rules/probe/rules.json'])
        report['profile'] = profile
        self.outer['rules/probe/rules.json'] = encoded(report)
        commands = json.loads(self.outer['rules/commands.json'])
        commands['stdout']['path'] = self.original + '/rules/tool.stdout'
        self.outer['rules/commands.json'] = encoded(commands)
        self.artifact_zip = zip_bytes(self.outer)
        self.artifact['digest'] = 'sha256:' + hashlib.sha256(self.artifact_zip).hexdigest()
        self.artifact['name'] = self.artifact['name'].replace(old, profile)
        self.job['name'] = self.job['name'].replace(old, profile)

    def test_collected_config_is_consumed_by_actual_seed_prepare(self):
        for profile in ('test-p16', 'test-p192'):
            with self.subTest(profile=profile):
                self.set_profile(profile)
                result = self.assemble(self.root / ('collected-' + profile))
                self.fixture.config = json.loads(Path(result['config']).read_bytes())
                receipt = self.fixture.prepare(self.root / ('seed-' + profile))
                manifest = json.loads(Path(receipt['seed_manifest']['path']).read_bytes())
                self.assertEqual([(row['family'], row['profile']) for row in manifest['rove']], [('A', profile)])
                self.assertFalse(receipt['engine_executed'] or receipt['aws_calls_performed'])
                with zipfile.ZipFile(receipt['archive']['path']) as package:
                    row = manifest['rove'][0]
                    self.assertEqual(package.read(row['build'] + '/main.c'), self.files['build/main.c'])
                    self.assertEqual(package.read(str(Path(row['rules']).parent.parent / 'tool.stdout')), b'fixture output\n')

    def test_bad_zip_digest_and_artifact_identity_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self.assemble(self.root / 'bad-digest', archive=lambda _: self.artifact_zip + b'x')
        self.artifact['id'] = 457
        with self.assertRaises((ValueError, RuntimeError)):
            self.assemble(self.root / 'bad-id')

    def test_bad_run_attempt_job_and_protected_zip_rejected(self):
        self.run['run_attempt'] = 2
        with self.assertRaises((ValueError, RuntimeError)):
            self.assemble(self.root / 'bad-attempt')
        self.run['run_attempt'] = 1
        self.job['conclusion'] = 'failure'
        with self.assertRaises((ValueError, RuntimeError)):
            self.assemble(self.root / 'bad-job')
        self.job['conclusion'] = 'success'
        bad = zip_bytes({**self.outer, '.env': b'fixture bytes are never read'})
        self.artifact['digest'] = 'sha256:' + hashlib.sha256(bad).hexdigest()
        with self.assertRaises((ValueError, RuntimeError)):
            self.assemble(self.root / 'protected', archive=lambda _: bad)

    def test_protected_nested_source_and_duplicate_selection_rejected(self):
        inner = zip_bytes({**self.files, 'build/.env': b'fixture bytes are never read'})
        forged = dict(self.outer)
        forged['source-bundle.zip'] = inner
        seal = json.loads(forged['source-seal.json'])
        seal['bundle'] = seed.pin(inner)
        forged['source-seal.json'] = encoded(seal)
        bad = zip_bytes(forged)
        self.artifact['digest'] = 'sha256:' + hashlib.sha256(bad).hexdigest()
        with self.assertRaises((ValueError, RuntimeError)):
            self.assemble(self.root / 'protected-nested', archive=lambda _: bad)
        self.artifact['digest'] = self.digest
        with self.assertRaises((ValueError, RuntimeError)):
            collector.assemble(self.base, [self.selection, self.selection], out=self.root / 'duplicate',
                               get=self.get, archive=lambda _: self.artifact_zip)

    def test_forged_seal_member_profile_and_restore_layout_rejected(self):
        original_seal = json.loads(self.outer['source-seal.json'])
        for label, mutate in (
                ('member', lambda value: value['members']['build/main.c'].update(sha256='0' * 64)),
                ('profile', lambda value: value['profiles'][0].update(profile='test-p192')),
                ('layout', lambda value: value['restore_layout'].update(output_root='/tmp/incorrect'))):
            with self.subTest(label=label):
                forged = copy.deepcopy(original_seal)
                mutate(forged)
                raw = zip_bytes({**self.outer, 'source-seal.json': encoded(forged)})
                self.artifact['digest'] = 'sha256:' + hashlib.sha256(raw).hexdigest()
                with self.assertRaises((ValueError, RuntimeError)):
                    self.assemble(self.root / ('forged-' + label), archive=lambda _: raw)

    def test_declared_large_size_and_remaining_budget_rejected_before_read(self):
        raw = bytearray(self.artifact_zip)
        # Change only the first entry's central-directory uncompressed size;
        # the payload is tiny. The collector must refuse the declared size
        # without attempting to decompress any member.
        index = raw.find(b'PK\x01\x02')
        self.assertGreaterEqual(index, 0)
        name_length = struct.unpack_from('<H', raw, index + 28)[0]
        self.assertEqual(bytes(raw[index + 46:index + 46 + name_length]), b'source-bundle.zip')
        struct.pack_into('<I', raw, index + 24, seed.MAX_MEMBER + 1)
        with patch.object(collector.producer, '_zip_members', side_effect=AssertionError('read attempted')):
            with self.assertRaisesRegex(ValueError, 'selected artifact member exceeds seed limit'):
                collector._selected_members(bytes(raw), remaining=seed.MAX_SEED)
            with self.assertRaisesRegex(ValueError, 'remaining seed budget'):
                collector._selected_members(self.artifact_zip, remaining=1)

    def test_cli_selection_duplicate_json_keys_rejected_before_network(self):
        base = self.root / 'base.json'
        base.write_bytes(encoded(self.base))
        selections = self.root / 'selections.json'
        selections.write_bytes(b'[{"family":"A","family":"B","profile":"test-p16",'
                               b'"variant":"control","artifact_id":456}]')
        with patch.object(collector, 'assemble', side_effect=AssertionError('network attempted')):
            with self.assertRaisesRegex(ValueError, 'duplicate selection JSON member'):
                collector.main(['--base', str(base), '--selections', str(selections), '--out', str(self.root / 'cli')])

    def test_pull_request_merge_is_bound_to_real_synthetic_git_objects(self):
        repo = self.fixture.repo
        original = git(repo, 'rev-parse', 'HEAD').decode().strip()
        git(repo, 'switch', '-qc', 'feature')
        (repo / 'feature.txt').write_text('fixture feature\n')
        git(repo, 'add', '--', 'feature.txt')
        git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '-qm', 'feature')
        head = git(repo, 'rev-parse', 'HEAD').decode().strip()
        git(repo, 'switch', '-qc', 'develop', original)
        (repo / 'base.txt').write_text('fixture base\n')
        git(repo, 'add', '--', 'base.txt')
        git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '-qm', 'base')
        base = git(repo, 'rev-parse', 'HEAD').decode().strip()
        git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'merge', '--no-ff', '-m', 'synthetic PR merge', head)
        merge = git(repo, 'rev-parse', 'HEAD').decode().strip()
        raw = git(repo, 'cat-file', 'commit', merge)
        headers = raw.split(b'\n\n', 1)[0].splitlines()
        self.commit = {'sha': merge,
                       'tree': {'sha': next(x[5:].decode() for x in headers if x.startswith(b'tree '))},
                       'parents': [{'sha': x[7:].decode()} for x in headers if x.startswith(b'parent ')]}
        self.assertEqual([item['sha'] for item in self.commit['parents']], [base, head])
        self.base['source_origin']['head_sha'] = merge
        self.base['checkout']['commit'] = merge
        seal = json.loads(self.outer['source-seal.json'])
        seal['ci_context'] = self.base['source_origin']
        self.outer['source-seal.json'] = encoded(seal)
        self.artifact_zip = zip_bytes(self.outer)
        self.artifact.update(name='league-source-A-test-p16-control-' + merge + '-1',
                             digest='sha256:' + hashlib.sha256(self.artifact_zip).hexdigest())
        self.artifact['workflow_run']['head_sha'] = head
        repository = {'id': 42, 'full_name': 'daejunnom/Rove4k'}
        pr_head = {'sha': head, 'ref': 'feature', 'repo': repository}
        pr_base = {'sha': base, 'ref': 'develop', 'repo': repository}
        self.run.update(event='pull_request', head_sha=head, head_repository=repository,
                        pull_requests=[{'number': 12, 'head': pr_head, 'base': pr_base}])
        self.job['head_sha'] = head
        self.pull = {'number': 12, 'merge_commit_sha': merge, 'head': pr_head, 'base': pr_base}
        result = self.assemble(self.root / 'pr-collected')
        self.fixture.config = json.loads(Path(result['config']).read_bytes())
        receipt = self.fixture.prepare(self.root / 'pr-seed')
        self.assertEqual(receipt['workflow_provenance']['kind'], 'pull-request-merge')
        self.assertFalse(receipt['engine_executed'] or receipt['aws_calls_performed'])
        self.pull['merge_commit_sha'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'live PR merge differs'):
            self.assemble(self.root / 'pr-stale')


if __name__ == '__main__':
    unittest.main()
