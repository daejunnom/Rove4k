"""Pinned source-preparation contract; no AWS, engine or live network."""
import dataclasses
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

try:
    from . import league_ssm_source_prepare as p
except ImportError:
    import league_ssm_source_prepare as p


class SourcePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rove-prep-')
        self.root = Path(self.temp.name).resolve()
        self.archive = self.root / 'seed.zip'
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('seed.json', b'fixture')
        archive_bytes = stream.getvalue()
        self.archive.write_bytes(archive_bytes)
        self.manifest = self.root / 'seed.json'
        self.manifest.write_bytes(p.ledger.canonical({'workflow_provenance': {
            'kind': 'pull-request-merge', 'pull_request': 12}}))
        self.candidates = self.root / 'candidates.json'
        self.candidates.write_bytes(b'candidate fixture')
        self.request = p.ssm.Request(campaign_id='test-campaign', job_id='job-a',
            instance_id='i-' + 'a' * 17, account_id='123456789012', region='ap-southeast-2',
            seed_manifest_sha256=hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            source_head='a' * 40, candidates_sha256=hashlib.sha256(self.candidates.read_bytes()).hexdigest(),
            profile='test-p16', artifact_id='A-p16', artifact_bucket='test-bucket',
            repository='daejunnom/Rove4k', producer_run_id='123', producer_run_attempt='2',
            producer_artifact_id='456', seed_bucket='test-bucket', seed_key='test-campaign/seed/a.zip',
            seed_version_id='version-1', seed_archive_sha256=hashlib.sha256(archive_bytes).hexdigest(),
            seed_archive_bytes=len(archive_bytes), boot_id='9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb')
        self.observation = {'format':'rove4k.github-source-observation-v1', 'repository':'daejunnom/Rove4k',
            'run_id':123, 'run_attempt':2, 'artifact_id':456, 'source_head':'a' * 40,
            'family':'A', 'profile':'test-p16', 'variant':'control', 'candidate_pins_match':True,
            'candidate_files_observed':False, 'workflow_commit_reviewed':False, 'host_authenticated':False,
            'runtime_qualified':False, 'authorizes_go':False}
        self.run = {'event':'pull_request', 'id':123, 'run_attempt':2, 'status':'completed',
                    'conclusion':'success', 'repository':{'full_name':'daejunnom/Rove4k'}}
        self.patches = [
            patch.object(p.seed, 'inspect_archive', return_value={'manifest_sha256':self.request.seed_manifest_sha256}),
            patch.object(p.producer, 'observe_github_via_gh', return_value=self.observation),
            patch.object(p.producer, '_gh_api_json', return_value=self.run),
            patch.object(p.producer, '_live_pr_merge', return_value=True),
        ]
        self.mocks = [item.start() for item in self.patches]

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def call(self, request=None, **changes):
        request = request or self.request
        args = {'expected_request_sha256':p.ledger.digest(request.record()), 'expected_boot_id':request.boot_id,
                'expected_pr':12, 'archive_path':self.archive, 'seed_root':self.root,
                'candidate_path':self.candidates, 'family':'A', 'variant':'control'}
        args.update(changes)
        return p.prepare(request, **args)

    def test_prepares_exact_request_without_granting_authority(self):
        result = self.call()
        self.assertEqual(result['request_sha256'], p.ledger.digest(self.request.record()))
        self.assertEqual(result['github_observation_sha256'], p.ledger.digest(self.observation))
        self.assertEqual(result['expected_receipt_inputs'], p.ssm.expected_receipt_inputs(self.request))
        self.assertEqual(result['command_sha256'], hashlib.sha256(p.ssm.command(self.request).encode()).hexdigest())
        for flag in ('authorizes_dispatch', 'authorizes_go', 'host_authenticated', 'boot_authenticated',
                     'budget_authenticated', 's3_version_authenticated', 'runtime_qualified', 'candidate_files_observed'):
            self.assertIs(result[flag], False)
        self.mocks[1].assert_called_once_with(self.request, seed_root=self.root,
            candidate_path=self.candidates, family='A', variant='control')
        self.mocks[3].assert_called_once()
        with self.assertRaises(RuntimeError):
            p.ssm.dispatch(self.request, plan=None, journal=None, client=None)

    def test_expected_request_and_boot_and_pr_must_match(self):
        for update in ({'expected_request_sha256':'0' * 64}, {'expected_boot_id':'0' * 36},
                       {'expected_pr':13}, {'expected_pr':True}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.call(**update)
        self.mocks[1].assert_not_called()

    def test_archive_size_hash_and_manifest_pin_rejected(self):
        for request in (dataclasses.replace(self.request, seed_archive_bytes=8),
                        dataclasses.replace(self.request, seed_archive_sha256='0' * 64)):
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.call(request)
        self.mocks[0].return_value = {'manifest_sha256':'0' * 64}
        with self.assertRaises(ValueError):
            self.call()
        self.mocks[1].assert_not_called()

    def test_observation_run_attempt_artifact_and_head_and_scope_rejected(self):
        for field, value in (('run_id',124), ('run_attempt',3), ('artifact_id',457),
                             ('source_head','b' * 40), ('profile','test-p192'),
                             ('family','B'), ('variant','other'), ('candidate_pins_match',False),
                             ('authorizes_go',True), ('candidate_files_observed',True)):
            with self.subTest(field=field):
                self.mocks[1].return_value = {**self.observation, field:value}
                with self.assertRaises(ValueError):
                    self.call()

    def test_run_rechecked_after_github_observation(self):
        self.mocks[2].return_value = {**self.run, 'event':'push'}
        with self.assertRaises(ValueError):
            self.call()
        self.mocks[2].return_value = self.run
        self.mocks[3].side_effect = ValueError('PR head/base changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.call()

    def test_manifest_or_candidate_changes_during_observation_rejected(self):
        def changed_manifest(*args, **kwargs):
            self.manifest.write_bytes(b'changed')
            return self.observation
        self.mocks[1].side_effect = changed_manifest
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            self.call()
        self.manifest.write_bytes(p.ledger.canonical({'workflow_provenance': {
            'kind':'pull-request-merge', 'pull_request':12}}))
        def changed_candidate(*args, **kwargs):
            self.candidates.write_bytes(b'changed')
            return self.observation
        self.mocks[1].side_effect = changed_candidate
        with self.assertRaisesRegex(ValueError, 'candidate manifest changed'):
            self.call()

    def test_protected_paths_are_rejected_before_any_read(self):
        for name in ('.env', '.npmrc', '.netrc', 'id_rsa.pub', 'secret.key', 'credential.json'):
            for argument in ('archive_path', 'candidate_path'):
                with self.subTest(name=name, argument=argument), self.assertRaises(ValueError):
                    self.call(**{argument:self.root / name})
        self.mocks[1].assert_not_called()

    def test_protected_zip_names_rejected_without_opening_members(self):
        for name in ('.npmrc', 'config/id_rsa.pub', 'config/service-account.json', 'src/secret.pem'):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as archive:
                archive.writestr(name, b'synthetic')
            raw = stream.getvalue()
            self.archive.write_bytes(raw)
            request = dataclasses.replace(self.request, seed_archive_bytes=len(raw),
                                          seed_archive_sha256=hashlib.sha256(raw).hexdigest())
            with self.subTest(name=name), patch.object(zipfile.ZipFile, 'read', side_effect=AssertionError('read')):
                with self.assertRaises(ValueError):
                    self.call(request)
        self.mocks[0].assert_not_called()
        self.mocks[1].assert_not_called()

    def test_protected_request_rejected_before_file_read(self):
        args = ['--request', str(self.root / '.npmrc'), '--expected-request-sha256', '0' * 64,
                '--expected-boot-id', self.request.boot_id, '--expected-pr', '12', '--archive', str(self.archive),
                '--seed-root', str(self.root), '--candidates', str(self.candidates),
                '--family', 'A', '--variant', 'control']
        with patch.object(p.producer.cloud, 'ordinary', side_effect=AssertionError('read prohibited')):
            with self.assertRaises(ValueError):
                p.main(args)

    def test_isolated_cli_help_is_importable(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(Path(p.__file__).resolve()), '--help'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertIn(b'--expected-request-sha256', result.stdout)

    def test_exact_request_json_contract(self):
        raw = p.ledger.canonical(self.request.record())
        self.assertEqual(p._request_from_bytes(raw), self.request)
        with self.assertRaises(ValueError):
            p._request_from_bytes(p.ledger.canonical({**self.request.record(), 'extra':1}))
        with self.assertRaises(ValueError):
            p._request_from_bytes(p.ledger.canonical({**self.request.record(), 'format':'other'}))
        with self.assertRaises(ValueError):
            p._request_from_bytes(b'{"format":"x","format":"x"}')

    @unittest.skipUnless(sys.platform == 'linux', 'GitHub ZIP observation requires Linux')
    def test_real_observer_and_pr_change_with_fake_github(self):
        for index in (1, 2, 3):
            self.patches[index].stop()
        try:
            from .test_league_github_producer import SourceObservationTests, encode
        except ImportError:
            from test_league_github_producer import SourceObservationTests, encode
        fixture = SourceObservationTests(methodName='test_source_observation_is_explicitly_not_go')
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.run.update(event='pull_request', head_sha='b'*40, head_branch='feature',
                           head_repository={'id':42, 'full_name':p.producer._REPO})
        fixture.artifact['workflow_run']['head_sha'] = 'b'*40
        fixture.job['head_sha'] = 'b'*40
        fixture.metadata['workflow_run']['head_sha'] = 'b'*40
        fixture.contents['metadata/A.json'] = encode(fixture.metadata)
        (fixture.root / 'metadata/A.json').write_bytes(fixture.contents['metadata/A.json'])
        fixture.manifest['members']['metadata/A.json'] = {**p.producer.cloud.pin(fixture.contents['metadata/A.json']), 'mode':384}
        base = {'sha':'d'*40, 'ref':'develop', 'repo':{'id':42, 'full_name':p.producer._REPO}}
        head = {'sha':'b'*40, 'ref':'feature', 'repo':{'id':42, 'full_name':p.producer._REPO}}
        fixture.pull = {'number':17, 'merge_commit_sha':'a'*40, 'base':base, 'head':head}
        fixture.commit = {'sha':'a'*40, 'tree':{'sha':'c'*40}, 'parents':[{'sha':'d'*40}, {'sha':'b'*40}]}
        fixture.run['pull_requests'] = [{'number':17, 'base':base, 'head':head}]
        fixture.manifest['workflow_provenance'] = {'kind':'pull-request-merge', 'event':'pull_request',
            'repository':p.producer._REPO, 'repository_id':42, 'run_id':'123', 'run_attempt':'2',
            'checkout_sha':'a'*40, 'api_head_sha':'b'*40, 'pull_request':17,
            'execution_tree':'c'*40, 'execution_parents':['d'*40, 'b'*40],
            'head_repository_id':42, 'head_branch':'feature'}
        fixture._write_manifest()
        request = dataclasses.replace(self.request, seed_manifest_sha256=fixture.req.seed_manifest_sha256,
                    candidates_sha256=fixture.req.candidates_sha256)
        args = {'expected_request_sha256':p.ledger.digest(request.record()), 'expected_boot_id':request.boot_id,
                'expected_pr':17, 'archive_path':self.archive, 'seed_root':fixture.root,
                'candidate_path':fixture.candidate_path, 'family':'A', 'variant':'control'}
        with patch.object(p.seed, 'inspect_archive', return_value={'manifest_sha256':request.seed_manifest_sha256}), \
             patch.object(p.producer.cloud, 'validate_seed_manifest', return_value=None), \
             patch.object(p.producer, '_gh_api_json', side_effect=fixture.get), \
             patch.object(p.producer, '_gh_api_archive', return_value=fixture.artifact_zip), \
             patch.object(p.producer, '_api_headers', side_effect=AssertionError('token access prohibited')):
            result = p.prepare(request, **args)
            self.assertTrue(result['github_observation']['candidate_pins_match'])
            self.assertFalse(result['authorizes_dispatch'])
            fixture.pull['head']['sha'] = 'e' * 40
            with self.assertRaises(ValueError):
                p.prepare(request, **args)


if __name__ == '__main__':
    unittest.main()
