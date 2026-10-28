"""Offline fixtures for GitHub source-transport observation; no AWS or network."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

try:
    from . import league_github_producer as p
except ImportError:
    import league_github_producer as p


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def zipped(members):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return stream.getvalue()


class SourceObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.origin = {'repository': p._REPO, 'head_sha': 'a' * 40, 'run_id': '123', 'run_attempt': '2'}
        self.req = SimpleNamespace(repository=p._REPO, profile='test-p16', producer_run_id='123',
            producer_run_attempt='2', producer_artifact_id='456', source_head='a' * 40, artifact_id='A-p16')
        self.files = {'build/build.json': b'{"family":"A"}', 'build/main.c': b'int x;',
                      'build/native/x': b'ELF', 'build/x': b'#!/bin/sh\n'}
        self.bundle = zipped(self.files)
        self.seal = encode({'format': 'rove4k.source-bundle-seal.v1', 'ci_context': self.origin,
            'bundle': p.cloud.pin(self.bundle), 'members':{name:p.cloud.pin(data) for name,data in self.files.items()},
            'profiles': [{'family':'A', 'profile':'test-p16', 'archive_prefix':'build'}]})
        self.artifact_zip = zipped({**self.files, 'source-bundle.zip': self.bundle, 'source-seal.json': self.seal})
        self.digest = 'sha256:' + hashlib.sha256(self.artifact_zip).hexdigest()
        self.name = 'league-source-A-test-p16-control-' + 'a' * 40 + '-2'
        self.metadata = {'id': 456, 'name': self.name, 'digest': self.digest,
                         'workflow_run': {'id':123, 'repository_id':42, 'head_sha':'a'*40,
                                          'head_repository_id':42, 'head_branch':'feature'}}
        self.artifact = {**self.metadata, 'expired': False, 'workflow_run': dict(self.metadata['workflow_run'])}
        self.run = {'repository': {'full_name':p._REPO, 'id':42}, 'id':123, 'run_attempt':2,
                    'status':'completed', 'conclusion':'success', 'path':p._WORKFLOW,
                    'event':'push', 'head_sha':'a'*40, 'head_repository':{'id':42}, 'head_branch':'feature'}
        self.job = {'id':789, 'name':'source-A-test-p16-control', 'run_id':123, 'head_sha':'a'*40, 'status':'completed',
                    'conclusion':'success', 'steps': [
                        {'name':'Seal the admitted source for P16 and P192 seed transport','status':'completed','conclusion':'success'},
                        {'name':'Preserve actual artifacts, bounded command logs and failures','status':'completed','conclusion':'success'}]}
        self.contents = {'origin/A/source-bundle.zip': self.bundle, 'origin/A/source-seal.json': self.seal,
                         'metadata/A.json': encode(self.metadata)}
        self.contents.update({'origin/A/' + name: data for name, data in self.files.items()})
        self.manifest = {'source_origin':self.origin, 'rove':[{'family':'A','profile':'test-p16',
            'build':'origin/A/build', 'source_bundle':'origin/A/source-bundle.zip',
            'source_seal':'origin/A/source-seal.json', 'artifact_metadata':'metadata/A.json'}],
            'members': {name:{**p.cloud.pin(data), 'mode':384} for name,data in self.contents.items()}}
        self.candidate_path = self.root / 'candidates.json'
        self.candidate = {'format':'rove4k-diagnostic-candidate-set-v1', 'profile':'test-p16', 'candidates':[{
            'artifact':{'id':'A-p16', 'family':'A', 'profile':'test-p16', 'representation':'source-jit', 'full':True,
                        'sha256':p.cloud.pin(self.files['build/x'])['sha256'], 'whole_bytes':len(self.files['build/x']),
                        'native_sha256':p.cloud.pin(self.files['build/native/x'])['sha256']},
            'source':p.cloud.pin(self.files['build/main.c']), 'native':p.cloud.pin(self.files['build/native/x'])}]}
        self._write_candidate()
        for name, data in self.contents.items():
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        self._write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def _write_manifest(self):
        raw = encode(self.manifest)
        (self.root / 'seed.json').write_bytes(raw)
        self.req.seed_manifest_sha256 = hashlib.sha256(raw).hexdigest()

    def _write_candidate(self):
        raw = encode(self.candidate)
        self.candidate_path.write_bytes(raw)
        self.req.candidates_sha256 = hashlib.sha256(raw).hexdigest()

    def get(self, path):
        if '/git/commits/' in path:
            return self.commit
        if '/pulls/' in path:
            return self.pull
        if '/attempts/2/jobs?' in path:
            return {'total_count':1, 'jobs':[self.job]}
        if '/artifacts/456' in path:
            return self.artifact
        if '/runs/123/artifacts?' in path:
            return {'total_count':1, 'artifacts':[self.artifact]}
        if '/attempts/2' in path:
            return self.run
        raise AssertionError(path)

    def inspect(self):
        with patch.object(p.cloud, 'validate_seed_manifest', return_value=None):
            return p._inspect(self.req, seed_root=self.root, candidate_path=self.candidate_path, family='A', variant='control',
                              get=self.get, archive=lambda _: self.artifact_zip)

    def test_source_observation_is_explicitly_not_go(self):
        result = self.inspect()
        self.assertFalse(result['authorizes_go'])
        self.assertFalse(result['workflow_commit_reviewed'])
        self.assertFalse(result['host_authenticated'])
        self.assertFalse(result['runtime_qualified'])
        self.assertEqual(result['job_id'], 789)

    def test_failed_run_job_steps_and_expired_artifact_are_rejected(self):
        for item, key, value in ((self.run,'conclusion','failure'), (self.run,'run_attempt',1),
                                 (self.job,'conclusion','failure'), (self.job['steps'][0],'conclusion','skipped'),
                                 (self.artifact,'expired',True), (self.artifact,'digest',None)):
            before = item[key]
            item[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.inspect()
            item[key] = before

    def test_forged_artifact_or_changed_zip_is_rejected(self):
        self.artifact['id'] = 457
        with self.assertRaises(ValueError): self.inspect()
        self.artifact['id'] = 456
        self.artifact_zip += b'changed'
        with self.assertRaises(ValueError): self.inspect()

    def test_seed_file_and_zip_build_must_match(self):
        (self.root / 'origin/A/build/main.c').write_bytes(b'int y;')
        with self.assertRaises(ValueError): self.inspect()

    def test_candidate_identity_and_file_pins_are_bound(self):
        for field in ('id', 'sha256', 'native_sha256'):
            record = self.candidate['candidates'][0]['artifact']
            before = record[field]
            record[field] = 'other'
            self._write_candidate()
            with self.subTest(field=field), self.assertRaises(ValueError): self.inspect()
            record[field] = before
        self._write_candidate()

    def test_protected_seed_member_rejected_before_any_open(self):
        self.manifest['rove'][0]['artifact_metadata'] = '.npmrc'
        self.manifest['members']['.npmrc'] = {'bytes':1, 'sha256':'0'*64, 'mode':384}
        self._write_manifest()
        original = p.cloud.ordinary
        def checked(path, **kwargs):
            self.assertNotEqual(Path(path).name, '.npmrc')
            return original(path, **kwargs)
        with patch.object(p.cloud, 'ordinary', side_effect=checked):
            with self.assertRaises(ValueError): self.inspect()

    def test_protected_seed_root_rejected_before_any_open(self):
        with patch.object(p.cloud, 'ordinary', side_effect=AssertionError('should not open')):
            with self.assertRaises(ValueError):
                p._inspect(self.req, seed_root=self.root / '.npmrc', candidate_path=self.candidate_path,
                           family='A', variant='control', get=self.get, archive=lambda _: self.artifact_zip)

    def test_pr_head_is_distinct_from_checkout_and_requires_proof(self):
        self.run.update(event='pull_request', head_sha='b'*40)
        self.artifact['workflow_run']['head_sha'] = 'b'*40
        self.job['head_sha'] = 'b'*40
        self.metadata['workflow_run']['head_sha'] = 'b'*40
        self.contents['metadata/A.json'] = encode(self.metadata)
        (self.root / 'metadata/A.json').write_bytes(self.contents['metadata/A.json'])
        self.manifest['members']['metadata/A.json'] = {**p.cloud.pin(self.contents['metadata/A.json']), 'mode':384}
        self._write_manifest()
        # The actual cloud validator treats historical PR proof as absent.
        with self.assertRaises(ValueError): self.inspect()
        self.run.update(head_repository={'id':42}, head_branch='feature', pull_requests=[{
            'number':17, 'head':{'sha':'b'*40, 'ref':'feature', 'repo':{'id':42}}, 'base':{'sha':'d'*40}}])
        proof = {'api_head_sha':'b'*40, 'repository_id':42, 'head_repository_id':42, 'head_branch':'feature',
                 'pull_request':17, 'reported_base_sha':'d'*40}
        with patch.object(p.cloud, 'validate_workflow_provenance', return_value=proof):
            self.assertEqual(self.inspect()['api_head'], 'b'*40)
            self.run['head_repository']['id'] = 43
            with self.assertRaises(ValueError): self.inspect()

    def test_simple_pr_merge_uses_live_commit_and_pr_snapshots(self):
        self.run.update(event='pull_request', head_sha='b'*40, head_branch='feature',
                        head_repository={'id':42, 'full_name':p._REPO})
        self.artifact['workflow_run']['head_sha'] = 'b'*40
        self.job['head_sha'] = 'b'*40
        self.metadata['workflow_run']['head_sha'] = 'b'*40
        self.contents['metadata/A.json'] = encode(self.metadata)
        (self.root / 'metadata/A.json').write_bytes(self.contents['metadata/A.json'])
        self.manifest['members']['metadata/A.json'] = {**p.cloud.pin(self.contents['metadata/A.json']), 'mode':384}
        base = {'sha':'d'*40,'ref':'develop','repo':{'id':42,'full_name':p._REPO}}
        head = {'sha':'b'*40,'ref':'feature','repo':{'id':42,'full_name':p._REPO}}
        self.pull = {'number':17,'merge_commit_sha':'a'*40,'base':base,'head':head}
        self.commit = {'sha':'a'*40,'tree':{'sha':'c'*40},'parents':[{'sha':'d'*40},{'sha':'b'*40}]}
        self.run['pull_requests'] = [{'number':17,'base':base,'head':head}]
        self.manifest['workflow_provenance'] = {'kind':'pull-request-merge','event':'pull_request',
            'repository':p._REPO,'repository_id':42,'run_id':'123','run_attempt':'2','checkout_sha':'a'*40,
            'api_head_sha':'b'*40,'pull_request':17,'execution_tree':'c'*40,'execution_parents':['d'*40,'b'*40],
            'head_repository_id':42,'head_branch':'feature'}
        self._write_manifest()
        self.assertEqual(self.inspect()['api_head'], 'b'*40)
        for item, key, bad in ((self.commit,'sha','e'*40), (self.pull,'merge_commit_sha','e'*40),
                               (self.manifest['workflow_provenance'],'execution_tree','e'*40),
                               (self.pull['head']['repo'],'id',None), (self.pull['head'],'ref','')):
            old = item[key]
            item[key] = bad
            self._write_manifest()
            with self.subTest(key=key), self.assertRaises(ValueError): self.inspect()
            item[key] = old
        self._write_manifest()

    def test_api_error_propagates_without_false_observation(self):
        def fail(_): raise TimeoutError('test timeout')
        with patch.object(p.cloud, 'validate_seed_manifest', return_value=None):
            with self.assertRaises(TimeoutError):
                p._inspect(self.req, seed_root=self.root, candidate_path=self.candidate_path,
                           family='A', variant='control', get=fail, archive=lambda _: self.artifact_zip)


class ZipAndApiTests(unittest.TestCase):
    def test_directory_preflight_rejects_protected_and_escaping_names(self):
        for bad in ('.env', '.npmrc', '.netrc', 'x/id_dsa', 'x/signing.key', 'x/secret-data', '../x', 'x//y', '/x'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                p._zip_members(zipped({'source-bundle.zip':b'ok', bad:b'blocked'}), {'source-bundle.zip'})
        with self.assertRaises(ValueError): p._safe_name('x\\y', directory=False)
        if os.name == 'posix':
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as z:
                z.writestr('x\\y', b'blocked')
                z.writestr('source-bundle.zip', b'ok')
            with self.assertRaises(ValueError):
                p._zip_members(stream.getvalue(), {'source-bundle.zip'})

    def test_link_duplicate_and_file_directory_collision_rejected(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            info = zipfile.ZipInfo('symlink')
            info.create_system = 3
            info.external_attr = (0o120777 << 16)
            z.writestr(info, 'target')
            z.writestr('a', 'ok')
        with self.assertRaises(ValueError): p._zip_members(stream.getvalue(), {'a'})
        with self.assertRaises(ValueError): p._zip_members(zipped({'a':b'ok','a/b':b'bad'}), {'a'})

    def test_pagination_is_complete_and_duplicate_free(self):
        with self.assertRaises(ValueError): p._all_jobs(1, 1, lambda _: {'total_count':2,'jobs':[{'id':1}]})
        with self.assertRaises(ValueError): p._all_jobs(1, 1, lambda _: {'total_count':2,'jobs':[{'id':1},{'id':1}]})
        self.assertEqual(len(p._all_jobs(1, 1, lambda _: {'total_count':1,'jobs':[{'id':1}]})), 1)

    def test_redirect_storage_error_never_leaks_signed_url_or_bearer(self):
        signed = 'https://example.blob.core.windows.net/archive?sig=private'
        requests = []
        def fake(req, _limit):
            requests.append(req)
            if len(requests) == 1:
                raise urllib.error.HTTPError(req.full_url, 302, 'redirect', {'Location':signed}, None)
            raise urllib.error.URLError(signed)
        with patch.object(p, '_api_headers', return_value={'Authorization':'Bearer redacted'}), \
             patch.object(p, '_read_response', side_effect=fake):
            with self.assertRaises(RuntimeError) as result: p._api_archive(123)
        self.assertNotIn('sig=', str(result.exception))
        self.assertIsNone(requests[1].get_header('Authorization'))

    def test_redirect_storage_allowlist_does_not_accept_spoofed_host(self):
        self.assertTrue(p._storage_url('https://foo.blob.core.windows.net/path?secret=x'))
        for url in ('http://foo.blob.core.windows.net/x', 'https://blob.core.windows.net.evil.example/x',
                    'https://localhost/x', 'https://user@foo.blob.core.windows.net/x'):
            with self.subTest(url=url), self.assertRaises(ValueError): p._storage_url(url)

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaises(ValueError): p._json(b'{"id":1,"id":2}')


if __name__ == '__main__':
    unittest.main()
