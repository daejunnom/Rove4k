"""Peer SSM preparation and dispatch using isolated fake host modules."""
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

try:
    from . import league_ssm_dispatch as dispatch, ledger
    from .test_league_ssm_dispatch import FakeClient
except ImportError:
    import league_ssm_dispatch as dispatch
    import ledger
    from test_league_ssm_dispatch import FakeClient


class PeerDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = ledger.Journal(Path(self.temp.name).resolve() / 'events.jsonl', 'campaign-a')
        self.addCleanup(self.journal.close)
        self.client = FakeClient(self.journal)
        self.plan = SimpleNamespace(campaign_id='campaign-a', region='ap-southeast-2',
                                    account_id='123456789012', artifact_bucket='rove-artifacts')
        self.req = dispatch.PeerRequest('campaign-a', 'job-1', 'i-' + '1' * 17, '123456789012',
            'ap-southeast-2', 'a' * 64, 'b' * 40, 'test-p16', 'rove-artifacts', 'daejunnom/Rove4k',
            '12345', '1', 'rove-seed-bucket', 'campaign-a/seed/object.zip', 'seed-version', 'd' * 64,
            10, '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb', 'ice4', 'MinusKelvin/ice4',
            '2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19')

    def authority(self, *, client, request):
        return {**request, 'verified': True, 'request_sha256': ledger.digest(request)}

    def test_request_has_distinct_peer_identity_without_rove_artifact(self):
        record = self.req.record()
        self.assertEqual(record['format'], 'rove4k-ssm-peer-request-v1')
        self.assertNotIn('producer_artifact_id', record)
        self.assertNotIn('artifact_id', record)
        self.assertNotIn('candidates_sha256', record)
        args = shlex.split(dispatch.command(self.req))
        self.assertIn('--property=RuntimeMaxSec=3780', args)
        compile(args[-1], '<peer-loader>', 'exec')
        self.assertIn('peer_diagnostic_prepare.prepare(', args[-1])
        self.assertIn('league_functional_host.run(', args[-1])
        for change in ({'family': 'D'}, {'upstream_repository': 'other/ice4'},
                       {'upstream_revision': '0' * 40}, {'preparation_seconds': 30},
                       {'profile': 'ELF'}, {'boot_id': '0' * 36}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.req, **change)

    def test_public_dispatch_stays_closed_and_private_transport_binds_peer(self):
        with self.assertRaises(RuntimeError):
            dispatch.dispatch(self.req, plan=self.plan, journal=self.journal, client=self.client)
        self.assertEqual(self.client.calls, [])
        def incorrect(*, client, request):
            return {**self.authority(client=client, request=request), 'upstream_revision': '0' * 40}
        with self.assertRaises(ValueError):
            dispatch._dispatch_with_verified_authority(self.req, plan=self.plan, journal=self.journal,
                                                        client=self.client, authority=incorrect)
        self.assertEqual(self.client.calls, [])
        result = dispatch._dispatch_with_verified_authority(self.req, plan=self.plan, journal=self.journal,
                                                             client=self.client, authority=self.authority)
        self.assertEqual(result['request_sha256'], ledger.digest(self.req.record()))
        self.assertFalse(result['scored_game_admitted'])
        self.assertEqual(self.client.calls[-1][2]['Parameters']['executionTimeout'], ['3900'])
        with self.assertRaises(ValueError):
            dispatch._dispatch_with_verified_authority(replace(self.req, job_id='job-2'), plan=self.plan,
                journal=self.journal, client=self.client, authority=self.authority)

    @unittest.skipUnless(sys.platform == 'linux', 'fixed Linux remote loader')
    def test_remote_loader_builds_peer_from_seed_then_passes_generated_candidate_to_host(self):
        base = Path(self.temp.name).resolve() / 'hosts' / 'campaign-a'
        base.mkdir(parents=True, mode=0o700)
        for name in ('state', 'inputs', 'results', 'snapshots', 'seed'):
            (base / name).mkdir(mode=0o700)
        files = {
            'source/engines/experiments/strength/cloud_runtime.py':
                b'def delegate_controller(root):\n assert str(root).startswith("/sys/fs/cgroup")\n',
            'source/engines/experiments/strength/league_functional_host.py':
                b'def run(**kw):\n return {"status":"complete","artifact":kw["artifact"],"candidates":str(kw["candidates"])}\n',
            'source/engines/experiments/strength/peer_diagnostic_prepare.py':
                b'def prepare(**kw):\n'
                b' out=kw["out"]; out.mkdir(); (out/"candidate.json").write_text("{}")\n'
                b' return {"family":kw["family"],"profile":kw["profile"],"seed_sha256":kw["seed_sha256"],'
                b'"candidate":{"path":str(out/"candidate.json"),"sha256":"c"*64},"artifact_id":"peer-generated"}\n',
            'external/ice4/source.c': b'upstream fixture bytes only',
        }
        members = {}
        for name, data in files.items():
            dest = base / 'seed' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            members[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'mode': 0o600}
        manifest = {'format': 'rove4k-cloud-seed-v1', 'source_origin': {'repository': 'daejunnom/Rove4k',
                    'head_sha': 'b' * 40, 'run_id': '12345', 'run_attempt': '1'}, 'source_tree': 'source',
                    'members': members, 'peers': [{'family': 'ice4', 'profile': 'test-p16',
                    'repository': self.req.upstream_repository, 'revision': self.req.upstream_revision,
                    'source': 'external/ice4'}]}
        raw = ledger.canonical(manifest) + b'\n'
        (base / 'seed' / 'seed.json').write_bytes(raw)
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        req = replace(self.req, seed_manifest_sha256=hashlib.sha256(raw).hexdigest(), boot_id=boot)
        def program_for(request):
            program = shlex.split(dispatch.command(request))[-1]
            program = program.replace("'/var/lib/rove4k/diagnostics'", repr(str(base.parent)))
            actual_root = str(Path('/sys/fs/cgroup/' + Path('/proc/self/cgroup').read_text().strip()[3:].lstrip('/')))
            return program.replace(repr(dispatch.expected_receipt_inputs(request)['root']), repr(actual_root))
        outcome = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(req)],
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(outcome.returncode, 0, outcome.stderr)
        envelope = json.loads(outcome.stdout)
        self.assertEqual(envelope['format'], 'rove4k-ssm-peer-functional-v1')
        self.assertEqual(envelope['request_sha256'], ledger.digest(req.record()))
        self.assertEqual(envelope['result']['artifact'], 'peer-generated')
        self.assertEqual(envelope['result']['candidates'], str(base / 'inputs' / 'peer-job-1' / 'candidate.json'))
        manifest['peers'][0]['revision'] = '0' * 40
        altered = ledger.canonical(manifest) + b'\n'
        (base / 'seed' / 'seed.json').write_bytes(altered)
        bad_req = replace(req, seed_manifest_sha256=hashlib.sha256(altered).hexdigest())
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(bad_req)],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('peer source identity differs', result.stderr)
        manifest['peers'][0]['revision'] = self.req.upstream_revision
        for name in ('x/.env', 'x/.npmrc', 'x/build/member', 'x/service-account.json', 'x/password.json', 'x/key.pem',
                     'x/id_ecdsa', 'x/id_dsa', 'x/id_ed25519.pub', 'x/ssh_host_ed25519_key'):
            with self.subTest(name=name):
                manifest['members'][name] = {'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest(), 'mode': 0o600}
                altered = ledger.canonical(manifest) + b'\n'
                (base / 'seed' / 'seed.json').write_bytes(altered)
                bad_req = replace(req, seed_manifest_sha256=hashlib.sha256(altered).hexdigest())
                result = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(bad_req)],
                                        capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('protected seed member', result.stderr)
                del manifest['members'][name]


if __name__ == '__main__':
    unittest.main()
