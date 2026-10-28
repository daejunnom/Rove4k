"""Peer SSM receipt consistency tests with an offline file reader."""
import copy
import hashlib
import json
import unittest

try:
    from . import league_ssm_receipt as mod
except ImportError:
    import league_ssm_receipt as mod

COMMAND = '3f040442-01e3-444b-9812-ea2e4515ec50'
INSTANCE = 'i-1234567890abcdef0'
ATTEMPT = 'e' * 32
DISPATCH = 'f' * 64
BOOT = '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb'


def raw(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


class FakeClient:
    def __init__(self, invocation):
        self.invocation = invocation
        self.calls = 0

    def call(self, service, operation, args):
        self.calls += 1
        if isinstance(self.invocation, Exception):
            raise self.invocation
        return self.invocation


class PeerReceiptTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'state_dir': '/srv/rove/state', 'root': '/sys/fs/cgroup/rove.service',
                         'campaign': 'league1', 'preparation_dir': '/srv/rove/inputs/job-peer',
                         'profile': 'test-p16', 'family': 'ice4', 'out': '/srv/rove/results/job',
                         'wall_seconds': 120, 'boot_id': BOOT, 'seed_manifest_sha256': 'a' * 64,
                         'upstream_repository': 'MinusKelvin/ice4', 'upstream_revision': '2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19'}
        base = self.expected['preparation_dir']
        self.paths = {'candidate': base + '/candidate.json', 'build': base + '/peer-build/peer.json',
                      'reference': base + '/peer-reference/reference.json'}
        whole_sha, native_sha, source_sha = 'b' * 64, 'c' * 64, 'd' * 64
        self.artifact_id = 'ice4-test-p16-bbbbbbbb-cccccccc'
        self.whole = {'path': base + '/peer-build/attempt-1/ice4-tcec', 'bytes': 4000, 'sha256': whole_sha}
        self.source = {'path': base + '/peer-reference/main.cpp', 'bytes': 100, 'sha256': source_sha}
        self.native = {'path': base + '/peer-reference/reference-1', 'bytes': 200, 'sha256': native_sha}
        self.layout = {'id': 'test-p16', 'purpose': 'test', 'workers': 16, 'entry_bytes': 8,
                       'tt_bits': 31, 'tt_entries': 1 << 31, 'tt_bytes': 16 << 30, 'tt_shift': 33}
        self.build = {'peer': 'ice4', 'artifact_kind': 'resource-tiny', 'resources': self.layout,
                      'revision': self.expected['upstream_revision'],
                      'source_url': 'https://github.com/' + self.expected['upstream_repository'] + '/tree/' + self.expected['upstream_revision'],
                      'complete': True, 'reproducible': True, 'whole': self.whole,
                      'attempts': [{'source': {'bytes': 100, 'sha256': source_sha}, 'whole': self.whole},
                                   {'source': {'bytes': 100, 'sha256': source_sha}, 'whole':
                                    {**self.whole, 'path': base + '/peer-build/attempt-2/ice4-tcec'}}]}
        self.reference = {'format': 'rove4k-peer-reference-v1', 'complete': True, 'engines_executed': 0,
                          'peer': 'ice4', 'resources': self.layout,
                          'source': {'bytes': 100, 'sha256': source_sha},
                          'native': {**self.native, 'layout_assertion': False},
                          'entry_size_compile_assertion': True,
                          'native_attempts': [{**self.native, 'path': base + '/peer-reference/reference-' + str(index),
                                               'layout_assertion': index == 3} for index in (1, 2, 3)]}
        self.artifact = {'id': self.artifact_id, 'family': 'ice4', 'path': self.whole['path'],
                         'purpose': 'test', 'profile': 'test-p16', 'workers': 16, 'entry_bytes': 8,
                         'tt_bytes': 16 << 30, 'representation': 'source-jit', 'full': True,
                         'sha256': whole_sha, 'whole_bytes': 4000, 'native_sha256': native_sha}
        self.candidate = {'format': 'rove4k-diagnostic-candidate-set-v1', 'profile': 'test-p16',
                          'candidates': [{'artifact': self.artifact, 'source': self.source,
                                          'native': self.native, 'evidence': {}}]}
        self.files = {}
        self.prep = {'format': 'rove4k-peer-diagnostic-preparation-v1', 'seed_sha256': 'a' * 64,
                     'family': 'ice4', 'profile': 'test-p16', 'artifact_id': self.artifact_id,
                     'scope': 'host source/whole/native preparation only; no engine execution or admission'}
        self.update_preparation()
        self.request = {'format': 'rove4k-functional-host-request-v1', 'attempt': ATTEMPT,
                        'root': self.expected['root'], 'campaign': 'league1', 'candidates': self.paths['candidate'],
                        'candidates_sha256': self.prep['candidate']['sha256'], 'profile': 'test-p16',
                        'artifact': self.artifact_id, 'out': self.expected['out'], 'wall_seconds': 120,
                        'pid': 101, 'scored_game_admitted': False}
        self.body = {'format': 'rove4k-functional-candidate-v1', 'profile': 'test-p16',
                     'artifact_id': self.artifact_id, 'candidate_set_sha256': self.prep['candidate']['sha256'],
                     'family': 'ice4', 'whole_sha256': whole_sha, 'native_sha256': native_sha,
                     'workers': 16, 'tt_bytes': 16 << 30, 'source_sha256': source_sha,
                     'source_evidence': {'kind': 'peer-reference-v1', 'build_sha256': self.prep['build']['sha256'],
                                         'reference_sha256': self.prep['reference']['sha256'],
                                         'source_contract_verified': True, 'native_reference_files_replay_verified': True},
                     'boot_id': BOOT, 'complete': True, 'scored_game_admitted': False}
        self.request_path = self.expected['state_dir'] + '/' + ATTEMPT + '/request.json'
        self.report_path = self.expected['out'] + '/functional-runtime.json'
        self.files[self.request_path] = raw(self.request)
        self.files[self.report_path] = raw(self.body)
        self.receipt = {'format': 'rove4k-functional-host-result-v1', 'attempt': ATTEMPT,
                        'request_sha256': digest(self.files[self.request_path]), 'status': 'complete',
                        'error': None, 'cleanup_errors': [], 'scored_game_admitted': False,
                        'limitations': [], 'report': {'path': self.report_path,
                            'bytes': len(self.files[self.report_path]), 'sha256': digest(self.files[self.report_path])}}
        self.envelope = {'format': 'rove4k-ssm-peer-functional-v1', 'request_sha256': DISPATCH,
                         'observed_boot_id': BOOT, 'preparation': self.prep, 'result': self.receipt}
        self.invocation = {'CommandId': COMMAND, 'InstanceId': INSTANCE, 'Status': 'Success', 'ResponseCode': 0}
        self.client = FakeClient(self.invocation)
        self.reads = []

    def update_preparation(self):
        data = raw(self.build)
        self.files[self.paths['build']] = data
        self.prep['build'] = {'path': self.paths['build'], 'bytes': len(data), 'sha256': digest(data)}
        self.reference['build'] = {'path': self.paths['build'], 'sha256': self.prep['build']['sha256']}
        data = raw(self.reference)
        self.files[self.paths['reference']] = data
        self.prep['reference'] = {'path': self.paths['reference'], 'bytes': len(data), 'sha256': digest(data)}
        self.candidate['candidates'][0]['evidence'] = {'kind': 'peer-reference-v1', 'build': self.prep['build'],
                                                        'reference': self.prep['reference']}
        data = raw(self.candidate)
        self.files[self.paths['candidate']] = data
        self.prep['candidate'] = {'path': self.paths['candidate'], 'bytes': len(data), 'sha256': digest(data)}

    def observe(self):
        self.invocation['StandardOutputContent'] = json.dumps(self.envelope)
        return mod.observe_peer(self.client, COMMAND, INSTANCE, dispatch_sha256=DISPATCH,
                                expected=self.expected, read_file=self.read)

    def read(self, path, limit):
        self.reads.append(path)
        return self.files[path]

    def test_exact_peer_binding_and_host_receipt(self):
        result = self.observe()
        self.assertEqual(result['state'], 'verified_diagnostic_receipt')
        self.assertEqual(result['peer_family'], 'ice4')
        self.assertFalse(result['host_authenticated'])
        self.assertFalse(result['authorizes_go'])
        self.assertFalse(result['process_settlement_proven'])
        self.assertEqual(self.client.calls, 1)
        self.assertEqual(self.reads, [self.paths['candidate'], self.paths['build'], self.paths['reference'],
                                      self.request_path, self.report_path])

    def test_c4ke_p192_uses_its_128gib_upstream_layout(self):
        self.expected.update(family='c4ke', profile='test-p192', upstream_repository='citrus610/c4ke',
                             upstream_revision='22e318f59b3a9eed1d2b8161da832222d4a51033')
        self.prep.update(family='c4ke', profile='test-p192', artifact_id='c4ke-test-p192-bbbbbbbb-cccccccc')
        self.artifact.update(id=self.prep['artifact_id'], family='c4ke', profile='test-p192', workers=192,
                             tt_bytes=128 << 30, path=self.whole['path'].replace('ice4-tcec', 'c4ke-tcec'))
        self.whole['path'] = self.whole['path'].replace('ice4-tcec', 'c4ke-tcec')
        self.layout.update(id='test-p192', workers=192, tt_bits=34, tt_entries=1 << 34,
                           tt_bytes=128 << 30, tt_shift=30)
        self.build['peer'] = self.reference['peer'] = 'c4ke'
        self.build['revision'] = self.expected['upstream_revision']
        self.build['source_url'] = 'https://github.com/' + self.expected['upstream_repository'] + '/tree/' + self.expected['upstream_revision']
        self.build['attempts'][1]['whole']['path'] = self.build['attempts'][1]['whole']['path'].replace('ice4-tcec', 'c4ke-tcec')
        self.candidate['profile'] = 'test-p192'
        self.update_preparation()
        self.request.update(profile='test-p192', artifact=self.prep['artifact_id'],
                            candidates_sha256=self.prep['candidate']['sha256'])
        self.body.update(profile='test-p192', artifact_id=self.prep['artifact_id'],
                         candidate_set_sha256=self.prep['candidate']['sha256'], family='c4ke',
                         workers=192, tt_bytes=128 << 30)
        self.body['source_evidence'].update(build_sha256=self.prep['build']['sha256'],
                                            reference_sha256=self.prep['reference']['sha256'])
        self.files[self.request_path] = raw(self.request)
        self.files[self.report_path] = raw(self.body)
        self.receipt['request_sha256'] = digest(self.files[self.request_path])
        self.receipt['report'].update(bytes=len(self.files[self.report_path]), sha256=digest(self.files[self.report_path]))
        self.assertEqual(self.observe()['state'], 'verified_diagnostic_receipt')

    def test_wrong_expected_and_envelope_values_fail_closed(self):
        for key, wrong in [('seed_sha256', '0' * 64), ('profile', 'test-p192'), ('family', 'c4ke')]:
            with self.subTest(key=key):
                original = self.prep[key]
                self.prep[key] = wrong
                self.assertEqual(self.observe()['state'], 'unresolved')
                self.prep[key] = original
        self.envelope['observed_boot_id'] = '00000000-0000-0000-0000-000000000000'
        self.assertEqual(self.observe()['reason'], 'dispatch_identity_mismatch')

    def test_paths_are_fixed_before_reader(self):
        for role in ('candidate', 'build', 'reference'):
            with self.subTest(role=role):
                original = self.prep[role]['path']
                self.prep[role]['path'] = '/etc/passwd'
                self.assertEqual(self.observe()['reason'], 'preparation_descriptor_invalid')
                self.assertNotIn('/etc/passwd', self.reads)
                self.prep[role]['path'] = original

    def test_preparation_bytes_length_and_hash_must_match(self):
        for role in ('candidate', 'build', 'reference'):
            with self.subTest(role=role):
                original = self.files[self.paths[role]]
                self.files[self.paths[role]] += b' '
                self.assertEqual(self.observe()['reason'], 'preparation_bytes_unverified')
                self.files[self.paths[role]] = original

    def test_untrusted_candidate_identity_is_not_admitted(self):
        for key, wrong in [('family', 'c4ke'), ('tt_bytes', 1), ('whole_bytes', 4097), ('path', '/elsewhere')]:
            with self.subTest(key=key):
                original = self.artifact[key]
                self.artifact[key] = wrong
                self.update_preparation()
                self.assertEqual(self.observe()['state'], 'unresolved')
                self.artifact[key] = original
        self.update_preparation()

    def test_build_and_reference_must_bind_selected_bytes(self):
        for target, key, wrong in [(self.build, 'peer', 'c4ke'), (self.build, 'revision', '0' * 40),
                                   (self.build, 'source_url', 'https://github.com/other/engine/tree/' + '0' * 40),
                                   (self.reference, 'engines_executed', 1),
                                   (self.reference, 'source', {'bytes': 3, 'sha256': '0' * 64})]:
            with self.subTest(key=key):
                original = target[key]
                target[key] = wrong
                self.update_preparation()
                self.assertEqual(self.observe()['state'], 'unresolved')
                target[key] = original
        self.update_preparation()

    def test_build_reference_layout_must_match_the_selected_profile(self):
        for key, wrong in [('workers', 999), ('tt_bytes', 1), ('entry_bytes', 24), ('tt_bits', 24)]:
            with self.subTest(key=key):
                original = self.layout[key]
                self.layout[key] = wrong
                self.update_preparation()
                self.assertEqual(self.observe()['reason'], 'build_reference_identity_mismatch')
                self.layout[key] = original
        self.update_preparation()

    def test_all_build_and_native_attempt_descriptors_must_agree(self):
        for target, key, wrong in [(self.build['attempts'][1]['whole'], 'sha256', '0' * 64),
                                   (self.build['attempts'][1]['source'], 'bytes', 1),
                                   (self.reference['native_attempts'][1], 'sha256', '0' * 64),
                                   (self.reference['native_attempts'][2], 'layout_assertion', False)]:
            with self.subTest(key=key):
                original = target[key]
                target[key] = wrong
                self.update_preparation()
                self.assertEqual(self.observe()['reason'], 'build_reference_identity_mismatch')
                target[key] = original
        self.update_preparation()

    def test_host_request_and_report_must_match_dynamic_candidate(self):
        self.request['artifact'] = 'different'
        self.files[self.request_path] = raw(self.request)
        self.receipt['request_sha256'] = digest(self.files[self.request_path])
        self.assertEqual(self.observe()['reason'], 'request_identity_mismatch')

    def test_host_report_must_report_peer_reference_evidence_and_family(self):
        for key, wrong in [('family', 'c4ke'), ('whole_sha256', '0' * 64),
                           ('native_sha256', '0' * 64), ('source_evidence', {'kind': 'file-pins-only'}),
                           ('workers', 999), ('tt_bytes', 1), ('source_sha256', '0' * 64),
                           ('boot_id', '00000000-0000-0000-0000-000000000000')]:
            with self.subTest(key=key):
                original = self.body[key]
                self.body[key] = wrong
                self.files[self.report_path] = raw(self.body)
                self.receipt['report']['bytes'] = len(self.files[self.report_path])
                self.receipt['report']['sha256'] = digest(self.files[self.report_path])
                self.assertEqual(self.observe()['reason'], 'report_identity_mismatch')
                self.body[key] = original

    def test_uncertain_transport_and_missing_file_never_authorize(self):
        self.client.invocation = RuntimeError('unavailable')
        self.assertEqual(self.observe()['state'], 'unresolved')
        self.client.invocation = self.invocation
        del self.files[self.paths['reference']]
        self.assertEqual(self.observe()['state'], 'unresolved')

    def test_invalid_expected_paths_rejected_before_network(self):
        self.expected['preparation_dir'] = '/srv/../tmp'
        with self.assertRaises(ValueError):
            self.observe()
        self.assertEqual(self.client.calls, 0)


if __name__ == '__main__':
    unittest.main()
