"""Offline SSM dispatch contract; never contacts AWS or starts a host."""
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
            'ap-southeast-2', 'a' * 64, 'b' * 40, 'c' * 64, 'test-p16', 'artifact-a', 'rove-artifacts',
            'daejunnom/Rove4k', '12345', '1', '6789', 'rove-seed-bucket', 'campaign-a/seed/object.zip',
            'seed+version/abc=', 'd' * 64, 10, '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb')

    def authority(self, *, client, request):
        self.assertIs(client, self.client)
        return {'verified': True, 'campaign_id': request['campaign_id'], 'instance_id': request['instance_id'],
            'account_id': request['account_id'], 'region': request['region'],
            'seed_manifest_sha256': request['seed_manifest_sha256'], 'source_head': request['source_head'],
            'artifact_bucket': request['artifact_bucket'], 'repository': request['repository'],
            'producer_run_id': request['producer_run_id'], 'producer_run_attempt': request['producer_run_attempt'],
            'producer_artifact_id': request['producer_artifact_id'], 'seed_bucket': request['seed_bucket'],
            'seed_key': request['seed_key'], 'seed_version_id': request['seed_version_id'],
            'seed_archive_sha256': request['seed_archive_sha256'], 'seed_archive_bytes': request['seed_archive_bytes'],
            'boot_id': request['boot_id'], 'request_sha256': ledger.digest(request)}

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
        other = replace(self.req, job_id='job-2')
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
                replace(self.req, profile=profile)
        with self.assertRaises(ValueError):
            replace(self.req, job_id='job-1; touch /tmp/x', profile='test-p192')

    def test_v2_requires_distinct_producer_seed_and_boot_declarations(self):
        # v1 callers cannot silently acquire invented provenance defaults.
        with self.assertRaises(TypeError):
            dispatch.Request('campaign-a', 'job-1', self.req.instance_id, self.req.account_id,
                self.req.region, self.req.seed_manifest_sha256, self.req.source_head,
                self.req.candidates_sha256, self.req.profile, self.req.artifact_id, self.req.artifact_bucket)
        invalid = {'repository': ['attacker/Rove4k', ''], 'producer_run_id': ['0', '01', 1],
                   'producer_run_attempt': ['', '0'], 'producer_artifact_id': ['0', 1],
                   'seed_bucket': ['', 'not a bucket'], 'seed_key': ['other/seed/x', 'campaign-a/seed/../x'],
                   'seed_version_id': ['', 'null', 'bad\nversion', '\ud800'],
                   'seed_archive_sha256': ['x' * 64], 'seed_archive_bytes': [0, True, (128 << 20) + 1],
                   'boot_id': ['00000000-0000-0000-0000-000000000000', 'bad', self.req.boot_id.upper()]}
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(self.req, **{field: value})
        alternatives = {'repository': 'daejunnom/Rove4k', 'producer_run_id': '12346',
                        'producer_run_attempt': '2', 'producer_artifact_id': '6790',
                        'seed_bucket': 'another-seed-bucket', 'seed_key': 'campaign-a/seed/another.zip',
                        'seed_version_id': 'another-version', 'seed_archive_sha256': 'e' * 64,
                        'seed_archive_bytes': 11, 'boot_id': '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabc'}
        for field, value in alternatives.items():
            if value != getattr(self.req, field):
                other = replace(self.req, **{field: value})
                self.assertNotEqual(ledger.digest(other.record()), ledger.digest(self.req.record()))
                self.assertNotEqual(dispatch.command(other), dispatch.command(self.req))
        self.assertEqual(self.req.record()['format'], 'rove4k-ssm-functional-request-v2')

    def test_each_producer_seed_and_boot_attestation_field_must_match(self):
        fields = ('repository', 'producer_run_id', 'producer_run_attempt', 'producer_artifact_id',
                  'seed_bucket', 'seed_key', 'seed_version_id', 'seed_archive_sha256', 'seed_archive_bytes', 'boot_id')
        for field in fields:
            def mismatched(*, client, request):
                result = self.authority(client=client, request=request)
                result[field] = None
                return result
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.send(mismatched)
        self.assertEqual(self.journal.rows, [])
        self.assertFalse(any(op == 'send-command' for _, op, _ in self.client.calls))

    def test_dispatch_derived_inputs_bind_receipt_without_trusting_stdout_paths(self):
        sent = self.send()
        fixed = dispatch.expected_receipt_inputs(self.req)
        attempt = 'e' * 32
        host_request = {k: v for k, v in fixed.items() if k not in ('state_dir', 'boot_id')}
        host_request.update(format='rove4k-functional-host-request-v1', attempt=attempt,
                            pid=42, scored_game_admitted=False)
        request_bytes = ledger.canonical(host_request) + b'\n'
        report_body = {'format': 'rove4k-functional-candidate-v1', 'profile': self.req.profile,
            'artifact_id': self.req.artifact_id, 'candidate_set_sha256': self.req.candidates_sha256,
            'boot_id': self.req.boot_id, 'complete': True, 'scored_game_admitted': False}
        report_bytes = ledger.canonical(report_body) + b'\n'
        host_result = {'format': 'rove4k-functional-host-result-v1', 'attempt': attempt,
            'request_sha256': hashlib.sha256(request_bytes).hexdigest(), 'status': 'complete',
            'report': {'path': fixed['out'] + '/functional-runtime.json', 'bytes': len(report_bytes),
                       'sha256': hashlib.sha256(report_bytes).hexdigest()}, 'error': None,
            'cleanup_errors': [], 'scored_game_admitted': False, 'limitations': []}
        envelope = {'format': 'rove4k-ssm-functional-v2', 'request_sha256': sent['request_sha256'],
                    'observed_boot_id': self.req.boot_id,
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
            'metadata/artifact.json': b'{"id":6789,"workflow_run":{"id":12345}}',
            'profiles/A/x': b'whole', 'profiles/A/main.c': b'source', 'profiles/A/native/x': b'native',
        }
        pins = {kind: {'bytes': len(files['profiles/A/' + name]),
                       'sha256': hashlib.sha256(files['profiles/A/' + name]).hexdigest()}
                for kind, name in [('whole', 'x'), ('source', 'main.c'), ('native', 'native/x')]}
        files['profiles/A/build.json'] = ledger.canonical({'expected_contract': {
            role + '_' + key: value for role, pin in pins.items() for key, value in pin.items()}})
        members = {}
        for name, data in files.items():
            dest = base / 'seed' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            members[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'mode': 0o600}
        manifest = {'format': 'rove4k-cloud-seed-v1', 'source_origin': {'repository': 'daejunnom/Rove4k',
                    'head_sha': 'b' * 40, 'run_id': '12345', 'run_attempt': '1'}, 'source_tree': 'source', 'members': members,
                    'rove': [{'family': 'A', 'profile': 'test-p16', 'build': 'profiles/A',
                              'artifact_metadata': 'metadata/artifact.json'}]}
        raw = ledger.canonical(manifest) + b'\n'
        (base / 'seed' / 'seed.json').write_bytes(raw)
        candidate_bytes = ledger.canonical({'profile': 'test-p16', 'candidates': [{'artifact': {
            'id': 'artifact-a', 'family': 'A', 'profile': 'test-p16', 'sha256': pins['whole']['sha256'],
            'whole_bytes': pins['whole']['bytes'], 'native_sha256': pins['native']['sha256']},
            'source': pins['source'], 'native': pins['native']}]})
        (base / 'inputs' / 'candidates.json').write_bytes(candidate_bytes)
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        request = replace(self.req, seed_manifest_sha256=hashlib.sha256(raw).hexdigest(),
                          candidates_sha256=hashlib.sha256(candidate_bytes).hexdigest(), boot_id=boot)
        program = shlex.split(dispatch.command(request))[-1]
        program = program.replace("'/var/lib/rove4k/diagnostics'", repr(str(base.parent)))
        actual_root = '/sys/fs/cgroup/' + Path('/proc/self/cgroup').read_text().strip()[3:].lstrip('/')
        actual_root = str(Path(actual_root))
        program = program.replace(repr(dispatch.expected_receipt_inputs(request)['root']), repr(actual_root))
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope['format'], 'rove4k-ssm-functional-v2')
        self.assertEqual(envelope['observed_boot_id'], boot)
        self.assertEqual(envelope['request_sha256'], ledger.digest(request.record()))
        self.assertEqual(envelope['result'], {'status': 'complete', 'profile': 'test-p16'})
        def program_for(candidate_request):
            source = shlex.split(dispatch.command(candidate_request))[-1]
            source = source.replace("'/var/lib/rove4k/diagnostics'", repr(str(base.parent)))
            return source.replace(repr(dispatch.expected_receipt_inputs(candidate_request)['root']), repr(actual_root))
        # Prior valid seed manifests may encode the same origin numbers as
        # JSON integers. Booleans and noncanonical numeric strings are not IDs.
        alternate_manifest = json.loads(raw)
        alternate_manifest['source_origin'].update(run_id=12345, run_attempt=1)
        alternate_raw = ledger.canonical(alternate_manifest) + b'\n'
        (base / 'seed' / 'seed.json').write_bytes(alternate_raw)
        alternate_request = replace(request, seed_manifest_sha256=hashlib.sha256(alternate_raw).hexdigest())
        compatible = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(alternate_request)],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(compatible.returncode, 0, compatible.stderr)
        for invalid_origin in (True, '012345'):
            alternate_manifest['source_origin']['run_id'] = invalid_origin
            invalid_raw = ledger.canonical(alternate_manifest) + b'\n'
            (base / 'seed' / 'seed.json').write_bytes(invalid_raw)
            invalid_request = replace(request, seed_manifest_sha256=hashlib.sha256(invalid_raw).hexdigest())
            failed = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(invalid_request)],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn('seed provenance differs', failed.stderr)
        (base / 'seed' / 'seed.json').write_bytes(raw)
        for change, expected_error in [({'producer_run_id': '12346'}, 'seed provenance differs'),
                ({'producer_artifact_id': '6790'}, 'producer artifact metadata differs'),
                ({'artifact_id': 'another-artifact'}, 'candidate identity differs'),
                ({'boot_id': '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabc'}, 'declared host boot differs')]:
            with self.subTest(change=change):
                failed = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(replace(request, **change))],
                                        capture_output=True, text=True, timeout=10)
                self.assertNotEqual(failed.returncode, 0)
                self.assertIn(expected_error, failed.stderr)
        altered = json.loads(candidate_bytes)
        altered['candidates'][0]['source']['sha256'] = '0' * 64
        altered_bytes = ledger.canonical(altered)
        (base / 'inputs' / 'candidates.json').write_bytes(altered_bytes)
        altered_request = replace(request, candidates_sha256=hashlib.sha256(altered_bytes).hexdigest())
        failed = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(altered_request)],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('candidate build pins differ', failed.stderr)
        for peer in ('ice4', 'c4ke'):
            altered = json.loads(candidate_bytes)
            altered['candidates'][0]['artifact']['family'] = peer
            altered_bytes = ledger.canonical(altered)
            (base / 'inputs' / 'candidates.json').write_bytes(altered_bytes)
            peer_request = replace(request, candidates_sha256=hashlib.sha256(altered_bytes).hexdigest())
            failed = subprocess.run([sys.executable, '-I', '-B', '-c', program_for(peer_request)],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn('peer producer artifact binding not implemented', failed.stderr)
        (base / 'inputs' / 'candidates.json').write_bytes(candidate_bytes)
        # Simulate a changed boot observation after the diagnostic completed:
        # the envelope must never report a successful result for that attempt.
        boot_file = base / 'boot-id'
        boot_file.write_text(boot)
        reboot_program = program_for(request).replace("'/proc/sys/kernel/random/boot_id'", repr(str(boot_file)))
        reboot_program = reboot_program.replace("\ncheck_boot()\nprint(json.dumps(",
            "\npathlib.Path(" + repr(str(boot_file)) + ").write_text('9c87985b-49cb-4c8e-9de5-3ea3d9c7fabc')\ncheck_boot()\nprint(json.dumps(")
        failed = subprocess.run([sys.executable, '-I', '-B', '-c', reboot_program],
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('declared host boot differs', failed.stderr)
        self.assertNotIn('rove4k-ssm-functional-v2', failed.stdout)
        # Mutation after manifest pin fails before any copied source is imported.
        (base / 'seed' / next(iter(files))).write_bytes(b'raise AssertionError("unsafe")\n')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('seed member differs', result.stderr)


class BootstrapIntentTests(unittest.TestCase):
    """In-memory fake SSM/S3: no network or remote source execution."""

    def setUp(self):
        try:
            from . import league_pinned_bootstrap as bootstrap, league_seed_archive as archive
            from .league_bootstrap_inspect import inspect_envelope
            from .league_seed_layout import build_layout
            from .league_controller import HostPlan
            from .test_league_seed_layout import pinned_fixture
            from .test_league_controller import make_plan
            from .test_league_pinned_bootstrap import Client, PROGRAM
        except ImportError:
            import league_pinned_bootstrap as bootstrap
            import league_seed_archive as archive
            from league_bootstrap_inspect import inspect_envelope
            from league_seed_layout import build_layout
            from league_controller import HostPlan
            from test_league_seed_layout import pinned_fixture
            from test_league_controller import make_plan
            from test_league_pinned_bootstrap import Client, PROGRAM
        self.bootstrap, self.archive, self.Client, self.program = bootstrap, archive, Client, PROGRAM
        self.inspect_envelope = inspect_envelope
        self.build_layout = build_layout
        # Logical archive names only; no source is loaded or written to disk.
        self.logical = 'origin/A/build/main.c'
        self.fixture, self.raw, self.pins = pinned_fixture()
        self.manifest_sha = self.pins['expected_manifest_sha256']
        self.plan = make_plan(hosts=(HostPlan(region='ap-southeast-1', profile='test-p16', slots=11,
                                              launch_token='second-host-token'),))
        origin = self.fixture.seed['source_origin']
        instance = 'i-' + '1' * 17
        boot = '12345678-1234-1234-1234-123456789abc'
        self.diagnostic = dispatch.Request(self.plan.campaign, 'test-job', instance, self.plan.account,
            'ap-southeast-1', self.manifest_sha, origin['head_sha'], 'c' * 64, 'test-p16', 'test-artifact',
            self.plan.bucket, origin['repository'], origin['run_id'], origin['run_attempt'], '18',
            self.plan.bucket, self.plan.campaign + '/seed/archive.zip', 'immutable-version',
            hashlib.sha256(self.raw).hexdigest(), len(self.raw), boot)
        loader = self.fixture.seed['source_tree'] + '/engines/experiments/strength/cloud_runtime.py'
        source = self.fixture.files[loader]
        pins = (bootstrap.LoaderPin(loader, hashlib.sha256(source).hexdigest(), len(source)),)
        self.b = bootstrap.BootstrapRequest(campaign=self.plan.campaign, plan_sha256=self.plan.sha256,
            bucket=self.plan.bucket, bucket_region=self.plan.home_region, bucket_owner=self.plan.account,
            key=self.diagnostic.seed_key, version_id=self.diagnostic.seed_version_id,
            archive_sha256=self.diagnostic.seed_archive_sha256, archive_bytes=len(self.raw),
            manifest_sha256=self.manifest_sha, repository=origin['repository'], source_head=origin['head_sha'],
            producer_run_id=origin['run_id'], producer_run_attempt=origin['run_attempt'],
            host_account=self.plan.account, host_region=self.diagnostic.region, host_instance_id=instance,
            host_boot_id=boot, host_launch_token='second-host-token', profile='test-p16',
            host_role_arn=f'arn:aws:iam::{self.plan.account}:role/team/league-host',
            caller_arn=f'arn:aws:sts::{self.plan.account}:assumed-role/league-host/{instance}',
            transfer_quote_id='quote-for-regions', quote_observed_at=1700000000,
            bootstrap_sha256=hashlib.sha256(PROGRAM).hexdigest(), loader_pins=pins)
        self.envelope = dispatch.BootstrapEnvelope(self.diagnostic, self.b, self.b.bootstrap_sha256,
            dispatch.bootstrap_loader_manifest_sha256(pins))

    def test_fake_ssm_and_fake_s3_bind_cross_region_same_snapshot_without_authority(self):
        sink = dispatch.DiagnosticSSMSink('ap-southeast-1')
        intent = dispatch.record_bootstrap_diagnostic(self.envelope, plan=self.plan, sink=sink,
            bootstrap_source=self.program, expected_bootstrap_sha256=self.envelope.expected_bootstrap_sha256,
            expected_loader_manifest_sha256=self.envelope.expected_loader_manifest_sha256)
        self.assertEqual(intent['request_sha256'], ledger.digest(self.envelope.record()))
        self.assertEqual(intent['bucket_region'], 'ap-southeast-2')
        self.assertEqual(intent['host_region'], 'ap-southeast-1')
        self.assertFalse(intent['scope']['ssm_contacted'])
        self.assertFalse(intent['scope']['go_authorized'])
        self.assertFalse(intent['scope']['complete_loader_closure_verified'])
        self.assertFalse(intent['scope']['aws_cost_confirmed'])
        self.assertFalse(intent['scope']['runtime_qualified'])
        # A fake receiver reconstructs only the serialized wire; it receives no
        # Python object, source contents, credential, or implicit authority.
        decoded = dispatch.parse_bootstrap_diagnostic(ledger.canonical(sink.records[0]['request']),
                                                       expected_request_sha256=intent['request_sha256'])
        self.assertEqual(decoded.record(), self.envelope.record())
        self.assertEqual(ledger.digest(decoded.record()), intent['request_sha256'])
        client = self.Client(self.raw)
        loaded = self.bootstrap.fetch_for_verified_loader(decoded.bootstrap, client, bootstrap_source=self.program)
        self.assertEqual(loaded.archive, self.raw)
        self.assertEqual(client.calls[0]['ExpectedBucketOwner'], self.plan.account)
        self.assertEqual(client.calls[0]['VersionId'], self.diagnostic.seed_version_id)
        checked, envelope_inspection = self.inspect_envelope(decoded.bootstrap, loaded, bootstrap_source=self.program)
        self.assertIs(checked, loaded.archive)
        self.assertTrue(envelope_inspection['scope']['declared_loader_bytes_compared'])
        self.assertTrue(envelope_inspection['scope']['all_seed_members_checked'])
        self.assertFalse(envelope_inspection['scope']['complete_loader_closure_verified'])
        self.assertFalse(envelope_inspection['scope']['go_authorized'])
        layout = self.build_layout(checked, expected_archive_sha256=decoded.bootstrap.archive_sha256,
            expected_archive_bytes=decoded.bootstrap.archive_bytes, expected_manifest_sha256=decoded.bootstrap.manifest_sha256,
            expected_origin=self.fixture.seed['source_origin'])
        mapped = layout.physical_for(self.logical)
        self.assertEqual(mapped, 'origin/A/__rove_seed_build_v1__/main.c')
        self.assertEqual(layout.logical_for(mapped), self.logical)
        self.assertEqual(layout.manifest['members'][self.logical]['sha256'],
                         hashlib.sha256(self.fixture.files[self.logical]).hexdigest())
        self.assertEqual(layout.manifest['rove'][0]['build'], 'origin/A/build')
        for logical in (self.logical, 'origin/A/build/x', 'origin/A/build/native/x'):
            physical = layout.physical_for(logical)
            self.assertEqual(layout.logical_for(physical), logical)
            self.assertNotIn('build', physical.split('/'))
            entry = next(item for item in layout.entries if item.logical == logical)
            self.assertEqual(entry.sha256, hashlib.sha256(self.fixture.files[logical]).hexdigest())
        self.assertIs(layout.verify_for(checked, **self.pins), layout)
        self.assertFalse(layout.scope()['materialized'])
        self.assertFalse(layout.scope()['go_authorized'])
        inspected = self.archive.inspect_snapshot(loaded.archive,
            expected_archive_sha256=self.b.archive_sha256, expected_archive_bytes=self.b.archive_bytes,
            expected_manifest_sha256=self.b.manifest_sha256,
            expected_origin=self.fixture.seed['source_origin'])
        self.assertTrue(inspected['scope']['workflow_proof_checked'])
        self.assertFalse(inspected['scope']['materialized'])
        self.assertFalse(inspected['scope']['go_authorized'])
        self.assertEqual(sink.records[0], intent)
        sink.records[0]['scope']['go_authorized'] = True
        self.assertFalse(sink.records[0]['scope']['go_authorized'])
        # Public dispatch remains closed even for this valid synthetic binding.
        with self.assertRaises(RuntimeError):
            dispatch.dispatch(self.envelope, plan=self.plan, journal=None, client=None)

    def test_bootstrap_and_original_request_mismatch_rejected(self):
        for change in ({'host_region': 'ap-southeast-2'}, {'host_boot_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'},
                       {'profile': 'test-p192'}, {'version_id': 'different'}, {'manifest_sha256': 'd' * 64},
                       {'producer_run_id': '999'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                dispatch.BootstrapEnvelope(self.diagnostic, replace(self.b, **change),
                    self.b.bootstrap_sha256, dispatch.bootstrap_loader_manifest_sha256(self.b.loader_pins))
        with self.assertRaises(ValueError):
            dispatch.BootstrapEnvelope(self.diagnostic, self.b, 'd' * 64,
                                       dispatch.bootstrap_loader_manifest_sha256(self.b.loader_pins))
        with self.assertRaises(ValueError):
            dispatch.BootstrapEnvelope(self.diagnostic, self.b, self.b.bootstrap_sha256, 'd' * 64)
        second = self.bootstrap.LoaderPin('source/extra.py', hashlib.sha256(b'x').hexdigest(), 1)
        ordered = tuple(sorted((*self.b.loader_pins, second), key=lambda pin: pin.name))
        ordered_request = replace(self.b, loader_pins=ordered)
        manifest_sha = dispatch.bootstrap_loader_manifest_sha256(ordered)
        dispatch.BootstrapEnvelope(self.diagnostic, ordered_request, self.b.bootstrap_sha256, manifest_sha)
        with self.assertRaises(ValueError):
            dispatch.BootstrapEnvelope(self.diagnostic, replace(self.b, loader_pins=tuple(reversed(ordered))),
                                       self.b.bootstrap_sha256, manifest_sha)

    def test_bad_plan_ssm_region_source_and_duplicate_do_not_send(self):
        wrong_sink = dispatch.DiagnosticSSMSink('ap-southeast-2')
        with self.assertRaises(ValueError):
            dispatch.record_bootstrap_diagnostic(self.envelope, plan=self.plan, sink=wrong_sink,
                bootstrap_source=self.program, expected_bootstrap_sha256=self.envelope.expected_bootstrap_sha256,
                expected_loader_manifest_sha256=self.envelope.expected_loader_manifest_sha256)
        self.assertEqual(wrong_sink.records, [])
        sink = dispatch.DiagnosticSSMSink('ap-southeast-1')
        with self.assertRaises(ValueError):
            dispatch.record_bootstrap_diagnostic(self.envelope, plan=self.plan, sink=sink,
                bootstrap_source=b'wrong', expected_bootstrap_sha256=self.envelope.expected_bootstrap_sha256,
                expected_loader_manifest_sha256=self.envelope.expected_loader_manifest_sha256)
        for changed in ('expected_bootstrap_sha256', 'expected_loader_manifest_sha256'):
            pins = {'expected_bootstrap_sha256': self.envelope.expected_bootstrap_sha256,
                    'expected_loader_manifest_sha256': self.envelope.expected_loader_manifest_sha256}
            pins[changed] = 'd' * 64
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                dispatch.record_bootstrap_diagnostic(self.envelope, plan=self.plan, sink=sink,
                                                       bootstrap_source=self.program, **pins)
        self.assertEqual(sink.records, [])
        dispatch.record_bootstrap_diagnostic(self.envelope, plan=self.plan, sink=sink,
            bootstrap_source=self.program, expected_bootstrap_sha256=self.envelope.expected_bootstrap_sha256,
            expected_loader_manifest_sha256=self.envelope.expected_loader_manifest_sha256)
        with self.assertRaises(ValueError):
            dispatch.record_bootstrap_diagnostic(self.envelope, plan=self.plan, sink=sink,
                bootstrap_source=self.program, expected_bootstrap_sha256=self.envelope.expected_bootstrap_sha256,
                expected_loader_manifest_sha256=self.envelope.expected_loader_manifest_sha256)
        self.assertEqual(len(sink.records), 1)

    def test_fake_wire_rejects_unknown_fields_and_pin_manipulation(self):
        valid = self.envelope.record()
        expected_sha = ledger.digest(valid)
        for changed in ({**valid, 'extra': 'not allowed'},
                        {**valid, 'diagnostic': {**valid['diagnostic'], 'extra': 1}},
                        {**valid, 'bootstrap': {**valid['bootstrap'], 'extra': 1}},
                        {**valid, 'expected_loader_manifest_sha256': 'f' * 64}):
            with self.subTest(changed=tuple(changed)), self.assertRaises(ValueError):
                dispatch.parse_bootstrap_diagnostic(ledger.canonical(changed), expected_request_sha256=ledger.digest(changed))
        resealed = {**valid, 'bootstrap': {**valid['bootstrap'], 'transfer_quote_id': 'different-quote'}}
        self.assertNotEqual(ledger.digest(resealed), expected_sha)
        with self.assertRaises(ValueError):
            dispatch.parse_bootstrap_diagnostic(ledger.canonical(resealed), expected_request_sha256=expected_sha)
        raw = ledger.canonical(valid)
        duplicate = b'{"format":"other",' + raw[1:]
        with self.assertRaises(ValueError):
            dispatch.parse_bootstrap_diagnostic(duplicate, expected_request_sha256=hashlib.sha256(duplicate).hexdigest())
        whitespace = raw + b'\n'
        with self.assertRaises(ValueError):
            dispatch.parse_bootstrap_diagnostic(whitespace, expected_request_sha256=hashlib.sha256(whitespace).hexdigest())


if __name__ == '__main__':
    unittest.main()
