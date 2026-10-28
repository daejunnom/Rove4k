"""Offline SSM receipt parsing: no AWS call or host process is performed."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from . import league_ssm_receipt as mod
except ImportError:
    import league_ssm_receipt as mod

COMMAND = '3f040442-01e3-444b-9812-ea2e4515ec50'
INSTANCE = 'i-1234567890abcdef0'
ATTEMPT = 'e' * 32
DISPATCH = 'f' * 64


def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


class Client:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def call(self, service, operation, args):
        self.calls.append((service, operation, args))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'state_dir': '/srv/rove/state', 'root': '/sys/fs/cgroup/rove.service',
                         'campaign': 'league1', 'candidates': '/srv/rove/candidates.json',
                         'candidates_sha256': 'a' * 64, 'profile': 'test-p16', 'artifact': 'engine-a',
                         'out': '/srv/rove/output', 'wall_seconds': 120}
        self.request = {k: v for k, v in self.expected.items() if k != 'state_dir'}
        self.request.update(format='rove4k-functional-host-request-v1', attempt=ATTEMPT,
                            pid=742, scored_game_admitted=False)
        self.body = {'format': 'rove4k-functional-candidate-v1', 'profile': 'test-p16',
                     'artifact_id': 'engine-a', 'candidate_set_sha256': 'a' * 64,
                     'complete': True, 'scored_game_admitted': False}
        self.request_path = '/srv/rove/state/' + ATTEMPT + '/request.json'
        self.report_path = '/srv/rove/output/functional-runtime.json'
        self.files = {self.request_path: raw(self.request), self.report_path: raw(self.body)}
        self.receipt = {'format': 'rove4k-functional-host-result-v1', 'attempt': ATTEMPT,
                        'request_sha256': hashlib.sha256(self.files[self.request_path]).hexdigest(),
                        'status': 'complete', 'error': None, 'cleanup_errors': [],
                        'scored_game_admitted': False, 'limitations': ['fixture only'],
                        'report': {'path': self.report_path, 'bytes': len(self.files[self.report_path]),
                                   'sha256': hashlib.sha256(self.files[self.report_path]).hexdigest()}}
        self.invocation = {'CommandId': COMMAND, 'InstanceId': INSTANCE, 'Status': 'Success',
                           'ResponseCode': 0, 'StandardOutputContent': self.stdout()}
        self.client = Client(self.invocation)
        self.reads = []

    def read(self, path, limit):
        self.reads.append((path, limit))
        return self.files[path]

    def observe(self):
        return mod.observe(self.client, COMMAND, INSTANCE, dispatch_sha256=DISPATCH,
                           expected=self.expected, read_file=self.read)

    def stdout(self):
        return json.dumps({'format': 'rove4k-ssm-functional-v1', 'request_sha256': DISPATCH,
                           'result': self.receipt})

    def test_exact_bound_receipt_and_bytes(self):
        got = self.observe()
        self.assertEqual(got['state'], 'verified_diagnostic_receipt')
        self.assertFalse(got['authorizes_go'])
        self.assertFalse(got['host_authenticated'])
        self.assertFalse(got['process_settlement_proven'])
        self.assertEqual([p for p, _ in self.reads], [self.request_path, self.report_path])
        self.assertEqual(self.client.calls, [('ssm', 'get-command-invocation',
                                              {'CommandId': COMMAND, 'InstanceId': INSTANCE})])

    def test_invocation_identity_and_success_required(self):
        for key, value in [('CommandId', '0' * 36), ('InstanceId', 'i-00000000'),
                           ('Status', 'InProgress'), ('ResponseCode', True), ('ResponseCode', 1)]:
            with self.subTest(key=key, value=value):
                original = self.invocation[key]
                self.invocation[key] = value
                self.assertEqual(self.observe()['state'], 'unresolved')
                self.assertEqual(self.reads, [])
                self.invocation[key] = original

    def test_ssm_failure_is_unresolved_without_retry(self):
        self.client.response = RuntimeError('transport failure')
        self.assertEqual(self.observe()['state'], 'unresolved')
        self.assertEqual(len(self.client.calls), 1)
        self.assertFalse(self.reads)

    def test_contradictory_status_details_rejected(self):
        self.invocation['StatusDetails'] = 'Delivery Timed Out'
        self.assertEqual(self.observe()['state'], 'unresolved')
        self.assertFalse(self.reads)

    def test_missing_or_truncated_stdout(self):
        for content in ('', 'x' * 24000, self.stdout()[:-1]):
            with self.subTest(length=len(content)):
                self.invocation['StandardOutputContent'] = content
                self.assertEqual(self.observe()['state'], 'unresolved')
                self.assertFalse(self.reads)

    def test_duplicate_json_key_rejected(self):
        self.invocation['StandardOutputContent'] = '{"status":"complete","status":"complete"}'
        self.assertEqual(self.observe()['state'], 'unresolved')

    def test_wrong_dispatch_hash_and_missing_result_fields_rejected(self):
        self.invocation['StandardOutputContent'] = json.dumps({
            'format': 'rove4k-ssm-functional-v1', 'request_sha256': '0' * 64, 'result': self.receipt})
        self.assertEqual(self.observe()['reason'], 'dispatch_identity_mismatch')
        del self.receipt['error']
        self.invocation['StandardOutputContent'] = self.stdout()
        self.assertEqual(self.observe()['reason'], 'host_receipt_not_complete')
        self.assertFalse(self.reads)

    def test_failed_or_quarantined_host_never_accepted(self):
        for status in ('quarantine', 'failed'):
            self.receipt['status'] = status
            self.invocation['StandardOutputContent'] = self.stdout()
            self.assertEqual(self.observe()['state'], 'unresolved')
            self.assertFalse(self.reads)

    def test_remote_report_path_is_not_controlled_by_stdout(self):
        self.receipt['report']['path'] = '/etc/passwd'
        self.invocation['StandardOutputContent'] = self.stdout()
        self.assertEqual(self.observe()['state'], 'unresolved')
        self.assertFalse(self.reads)

    def test_request_hash_and_identity_are_both_required(self):
        self.files[self.request_path] = b'changed'
        self.assertEqual(self.observe()['reason'], 'request_bytes_unverified')
        self.request['profile'] = 'test-p192'
        self.files[self.request_path] = raw(self.request)
        self.receipt['request_sha256'] = hashlib.sha256(self.files[self.request_path]).hexdigest()
        self.invocation['StandardOutputContent'] = self.stdout()
        self.assertEqual(self.observe()['reason'], 'request_identity_mismatch')

    def test_report_hash_length_and_identity_are_all_required(self):
        self.files[self.report_path] += b' '
        self.assertEqual(self.observe()['reason'], 'report_bytes_unverified')
        self.body['artifact_id'] = 'other'
        self.files[self.report_path] = raw(self.body)
        self.receipt['report']['bytes'] = len(self.files[self.report_path])
        self.receipt['report']['sha256'] = hashlib.sha256(self.files[self.report_path]).hexdigest()
        self.invocation['StandardOutputContent'] = self.stdout()
        self.assertEqual(self.observe()['reason'], 'report_identity_mismatch')

    def test_missing_host_file_is_unresolved(self):
        del self.files[self.report_path]
        self.assertEqual(self.observe()['reason'], 'observation_or_parse_uncertain')

    def test_unsafe_expected_configuration_rejected_before_aws_read(self):
        self.expected['state_dir'] = '/srv/rove/../other'
        with self.assertRaises(ValueError):
            self.observe()
        self.assertFalse(self.client.calls)

    def test_attempt_and_report_boundaries(self):
        for attempt in ('../other', 'E' * 32, 'e' * 31):
            self.receipt['attempt'] = attempt
            self.invocation['StandardOutputContent'] = self.stdout()
            self.assertEqual(self.observe()['state'], 'unresolved')
            self.assertFalse(self.reads)

    @unittest.skipUnless(sys.platform == 'linux', 'host file permissions and fsync require Linux')
    def test_actual_host_receipt_and_files_contract(self):
        try:
            from . import league_functional_host as host
            from .test_league_functional_host import FakeProbe
        except ImportError:
            import league_functional_host as host
            from test_league_functional_host import FakeProbe
        with tempfile.TemporaryDirectory(prefix='rove-ssm-contract-') as directory:
            base = Path(directory).resolve()
            state = base / 'state'
            state.mkdir(mode=0o700)
            os.chmod(state, 0o700)
            expected = {'state_dir': str(state), 'root': str(base / 'delegated'),
                        'campaign': 'league1', 'candidates': str(base / 'candidates.json'),
                        'candidates_sha256': 'a' * 64, 'profile': 'test-p16',
                        'artifact': 'engine-a', 'out': str(base / 'output'), 'wall_seconds': 120}
            result = host.run(**expected, _probe_factory=lambda **kw: FakeProbe(kw))
            invocation = dict(self.invocation, StandardOutputContent=json.dumps({
                'format': 'rove4k-ssm-functional-v1', 'request_sha256': DISPATCH, 'result': result}))
            def read_local(path, limit):
                data = Path(path).read_bytes()
                self.assertLessEqual(len(data), limit)
                return data
            got = mod.observe(Client(invocation), COMMAND, INSTANCE, dispatch_sha256=DISPATCH,
                              expected=expected, read_file=read_local)
            self.assertEqual(got['state'], 'verified_diagnostic_receipt')
            self.assertFalse(got['host_authenticated'])


if __name__ == '__main__':
    unittest.main()
