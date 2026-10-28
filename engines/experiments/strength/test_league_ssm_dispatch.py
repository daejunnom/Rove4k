"""Offline SSM dispatch contract; never contacts AWS or starts a host."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

try:
    from . import league_ssm_dispatch as dispatch, league_ssm_receipt as receipt, ledger
except ImportError:
    import league_ssm_dispatch as dispatch
    import league_ssm_receipt as receipt
    import ledger


class FakeClient:
    def __init__(self, journal):
        self.journal = journal
        self.calls = []
        self.ready = True
        self.raise_after_send = False
        self.reject_response = False

    def call(self, service, operation, request):
        self.calls.append((service, operation, request))
        if (service, operation) == ('ssm', 'describe-instance-information'):
            return {'InstanceInformationList': [{'InstanceId': request['Filters'][0]['Values'][0],
                     'PlatformType': 'Linux', 'AgentVersion': '3.3',
                     'PingStatus': 'Online' if self.ready else 'Inactive'}]}
        if (service, operation) == ('ssm', 'send-command'):
            assert self.journal.rows[-1]['event'] == 'league.functional_ssm_requested'
            if self.raise_after_send:
                raise TimeoutError('response may have been lost')
            ids = ['i-' + 'f' * 17] if self.reject_response else request['InstanceIds']
            return {'Command': {'CommandId': '01234567-89ab-cdef-0123-456789abcdef', 'InstanceIds': ids}}
        raise AssertionError((service, operation))


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = ledger.Journal(Path(self.temp.name).resolve() / 'events.jsonl', 'campaign-a')
        self.addCleanup(self.journal.close)
        self.client = FakeClient(self.journal)
        self.plan = SimpleNamespace(campaign_id='campaign-a', region='ap-southeast-2', account_id='123456789012', artifact_bucket='rove-artifacts')
        self.req = dispatch.Request('campaign-a', 'job-1', 'i-' + '1' * 17, '123456789012',
            'ap-southeast-2', 'a' * 64, 'b' * 40, 'c' * 64, 'test-p16', 'artifact-a', 'rove-artifacts')

    def authority(self, *, client, request):
        self.assertIs(client, self.client)
        return {'verified': True, 'campaign_id': request['campaign_id'], 'instance_id': request['instance_id'],
            'account_id': request['account_id'], 'region': request['region'],
            'seed_manifest_sha256': request['seed_manifest_sha256'], 'source_head': request['source_head'],
            'artifact_bucket': request['artifact_bucket'], 'request_sha256': ledger.digest(request)}

    def send(self, authority=None):
        return dispatch._dispatch_with_verified_authority(self.req, plan=self.plan, journal=self.journal, client=self.client,
                                 authority=self.authority if authority is None else authority)

    def test_fixed_systemd_command_contains_only_encoded_request(self):
        cmd = dispatch.command(self.req)
        args = shlex.split(cmd)
        self.assertEqual(args[0:2], ['exec', '/usr/bin/systemd-run'])
        self.assertIn('--property=Delegate=yes', args)
        self.assertIn('--slice=system.slice', args)
        self.assertIn('--wait', args)
        self.assertIn('/usr/bin/python3', args)
        self.assertEqual(args[-5:-2], ['/usr/bin/python3', '-I', '-B'])
        self.assertEqual(args[-2], '-c')
        compile(args[-1], '<remote-diagnostic>', 'exec')
        self.assertNotIn('job-1', args[-1])  # encoded payload is never shell-expanded
        self.assertIn('cloud_runtime.delegate_controller(root)', args[-1])
        self.assertIn('league_functional_host.run(', args[-1])
        self.assertIn(dispatch.expected_receipt_inputs(self.req)['root'], args[-1])

    def test_exact_binding_and_fsynced_intent_before_send(self):
        result = self.send()
        self.assertEqual(result['request_sha256'], ledger.digest(self.req.record()))
        self.assertEqual([row['event'] for row in self.journal.rows],
                         ['league.functional_ssm_requested', 'league.functional_ssm_sent'])
        self.assertFalse(result['scored_game_admitted'])
        self.assertTrue(result['transport_only'])
        request = self.client.calls[-1][2]
        self.assertEqual(request['InstanceIds'], [self.req.instance_id])
        self.assertEqual(request['DocumentName'], 'AWS-RunShellScript')
        self.assertEqual(request['Parameters']['commands'], [dispatch.command(self.req)])
        self.assertEqual(request['Parameters']['executionTimeout'], ['300'])
        self.assertEqual(self.journal.rows[0]['data']['ssm_request_sha256'], ledger.digest(request))
        with self.assertRaises(ValueError):
            self.send()
        self.assertEqual(sum(op == 'send-command' for _, op, _ in self.client.calls), 1)

    def test_authority_absent_mismatch_or_offline_never_sends(self):
        with self.assertRaises(RuntimeError):
            dispatch.dispatch(self.req, plan=self.plan, journal=self.journal, client=self.client)
        with self.assertRaises(ValueError):
            self.send(lambda **_: {'verified': True})
        self.client.ready = False
        with self.assertRaises(ValueError):
            self.send()
        self.assertEqual(self.journal.rows, [])
        self.assertFalse(any(op == 'send-command' for _, op, _ in self.client.calls))

    def test_lost_response_records_uncertainty_and_never_resends(self):
        self.client.raise_after_send = True
        with self.assertRaises(TimeoutError):
            self.send()
        self.assertEqual([row['event'] for row in self.journal.rows],
                         ['league.functional_ssm_requested', 'league.functional_ssm_uncertain'])
        self.client.raise_after_send = False
        with self.assertRaises(ValueError):
            self.send()
        self.assertEqual(sum(op == 'send-command' for _, op, _ in self.client.calls), 1)
        other = dispatch.Request('campaign-a', 'job-2', self.req.instance_id, self.req.account_id,
            self.req.region, self.req.seed_manifest_sha256, self.req.source_head,
            self.req.candidates_sha256, self.req.profile, self.req.artifact_id, self.req.artifact_bucket)
        with self.assertRaises(ValueError):
            dispatch._dispatch_with_verified_authority(other, plan=self.plan, journal=self.journal,
                                                        client=self.client, authority=self.authority)

    def test_malformed_send_response_is_uncertain(self):
        self.client.reject_response = True
        with self.assertRaises(ValueError):
            self.send()
        self.assertEqual(self.journal.rows[-1]['event'], 'league.functional_ssm_uncertain')
        with self.assertRaises(ValueError):
            self.send()

    def test_disallows_d_or_elf_and_command_injection(self):
        for profile in ('test-p4', 'test-p28', 'ELF', 'test-d'):
            with self.assertRaises(ValueError):
                dispatch.Request('campaign-a', 'job-1', 'i-' + '1' * 17, '123456789012',
                    'ap-southeast-2', 'a' * 64, 'b' * 40, 'c' * 64, profile, 'artifact-a', 'rove-artifacts')
        with self.assertRaises(ValueError):
            dispatch.Request('campaign-a', 'job-1; touch /tmp/x', 'i-' + '1' * 17, '123456789012',
                'ap-southeast-2', 'a' * 64, 'b' * 40, 'c' * 64, 'test-p192', 'artifact-a', 'rove-artifacts')

    def test_dispatch_derived_inputs_bind_receipt_without_trusting_stdout_paths(self):
        sent = self.send()
        fixed = dispatch.expected_receipt_inputs(self.req)
        attempt = 'e' * 32
        host_request = {k: v for k, v in fixed.items() if k != 'state_dir'}
        host_request.update(format='rove4k-functional-host-request-v1', attempt=attempt,
                            pid=42, scored_game_admitted=False)
        request_bytes = ledger.canonical(host_request) + b'\n'
        report_body = {'format': 'rove4k-functional-candidate-v1', 'profile': self.req.profile,
            'artifact_id': self.req.artifact_id, 'candidate_set_sha256': self.req.candidates_sha256,
            'complete': True, 'scored_game_admitted': False}
        report_bytes = ledger.canonical(report_body) + b'\n'
        host_result = {'format': 'rove4k-functional-host-result-v1', 'attempt': attempt,
            'request_sha256': hashlib.sha256(request_bytes).hexdigest(), 'status': 'complete',
            'report': {'path': fixed['out'] + '/functional-runtime.json', 'bytes': len(report_bytes),
                       'sha256': hashlib.sha256(report_bytes).hexdigest()}, 'error': None,
            'cleanup_errors': [], 'scored_game_admitted': False, 'limitations': []}
        envelope = {'format': 'rove4k-ssm-functional-v1', 'request_sha256': sent['request_sha256'],
                    'result': host_result}
        invocation = {'CommandId': sent['command_id'], 'InstanceId': self.req.instance_id,
            'Status': 'Success', 'ResponseCode': 0, 'StandardOutputContent': json.dumps(envelope)}
        client = SimpleNamespace(call=lambda service, op, args: invocation)
        files = {fixed['state_dir'] + '/' + attempt + '/request.json': request_bytes,
                 fixed['out'] + '/functional-runtime.json': report_bytes}
        found = receipt.observe(client, sent['command_id'], sent['instance_id'],
            dispatch_sha256=sent['request_sha256'], expected=fixed, read_file=lambda path, limit: files[path])
        self.assertEqual(found['state'], 'verified_diagnostic_receipt')
        self.assertFalse(found['authorizes_go'])
        self.assertFalse(found['host_authenticated'])

    @unittest.skipUnless(sys.platform == 'linux', 'fixed Linux remote loader')
    def test_remote_loader_runs_only_the_pinned_snapshot(self):
        base = Path(self.temp.name).resolve() / 'hosts' / 'campaign-a'
        base.mkdir(parents=True, mode=0o700)
        for name in ('state', 'inputs', 'results', 'snapshots', 'seed'):
            (base / name).mkdir(mode=0o700)
        files = {
            'source/engines/experiments/strength/cloud_runtime.py':
                b'def delegate_controller(root):\n assert str(root).startswith("/sys/fs/cgroup")\n',
            'source/engines/experiments/strength/league_functional_host.py':
                b'def run(**kwargs):\n return {"status":"complete","profile":kwargs["profile"]}\n',
        }
        members = {}
        for name, data in files.items():
            dest = base / 'seed' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            members[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'mode': 0o600}
        manifest = {'format': 'rove4k-cloud-seed-v1', 'source_origin': {'repository': 'daejunnom/Rove4k',
                    'head_sha': 'b' * 40}, 'source_tree': 'source', 'members': members}
        raw = ledger.canonical(manifest) + b'\n'
        (base / 'seed' / 'seed.json').write_bytes(raw)
        request = dispatch.Request('campaign-a', 'job-1', 'i-' + '1' * 17, '123456789012',
            'ap-southeast-2', hashlib.sha256(raw).hexdigest(), 'b' * 40, 'c' * 64, 'test-p16', 'artifact-a', 'rove-artifacts')
        program = shlex.split(dispatch.command(request))[-1]
        program = program.replace("'/var/lib/rove4k/diagnostics'", repr(str(base.parent)))
        actual_root = '/sys/fs/cgroup/' + Path('/proc/self/cgroup').read_text().strip()[3:].lstrip('/')
        actual_root = str(Path(actual_root))
        program = program.replace(repr(dispatch.expected_receipt_inputs(request)['root']), repr(actual_root))
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope['format'], 'rove4k-ssm-functional-v1')
        self.assertEqual(envelope['request_sha256'], ledger.digest(request.record()))
        self.assertEqual(envelope['result'], {'status': 'complete', 'profile': 'test-p16'})
        # Mutation after manifest pin fails before any copied source is imported.
        (base / 'seed' / next(iter(files))).write_bytes(b'raise AssertionError("unsafe")\n')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('seed member differs', result.stderr)


if __name__ == '__main__':
    unittest.main()
