"""League EC2 recovery is read-only; mock responses are not AWS evidence."""
from dataclasses import asdict, replace
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from . import global_budget as g
    from .league_aws_recovery import RecoveryIntent, inspect_launch
    from .league_aws_launch import LeagueLaunchSpec, request_preview
    from .ledger import Journal
    from .shared_coordinator import SharedBudgetJournal
    from .test_global_budget import FakeS3
    from .test_league_controller import ACCOUNT, REGION, make_plan
except ImportError:
    import global_budget as g
    from league_aws_recovery import RecoveryIntent, inspect_launch
    from league_aws_launch import LeagueLaunchSpec, request_preview
    from ledger import Journal
    from shared_coordinator import SharedBudgetJournal
    from test_global_budget import FakeS3
    from test_league_controller import ACCOUNT, REGION, make_plan


class Ec2Reads:
    def __init__(self, instance=None):
        self.region = REGION
        self.instance = instance
        self.account = ACCOUNT
        self.calls = []
        self.pages = None
        self.on_describe = None
        self.spot_pages = None
        self.ssm_pages = None
        self.spot_error = False
        self.ssm_error = False
        self.instance_error = False

    def call(self, service, operation, request):
        self.calls.append((service, operation, request))
        if (service, operation) == ('sts', 'get-caller-identity'):
            return {'Account': self.account}
        if (service, operation) == ('ec2', 'describe-spot-instance-requests'):
            if self.spot_error:
                raise RuntimeError('denied or unavailable')
            if self.spot_pages is not None:
                return self.spot_pages.get(request.get('NextToken'), {'SpotInstanceRequests': []})
            return {'SpotInstanceRequests': []}
        if (service, operation) == ('ssm', 'describe-instance-information'):
            if self.ssm_error:
                raise RuntimeError('denied or unavailable')
            if self.ssm_pages is not None:
                return self.ssm_pages.get(request.get('NextToken'), {'InstanceInformationList': []})
            return {'InstanceInformationList': []}
        if (service, operation) != ('ec2', 'describe-instances'):
            raise AssertionError('unexpected AWS mutation or operation')
        if self.instance_error:
            raise RuntimeError('denied or unavailable')
        if self.on_describe is not None:
            callback, self.on_describe = self.on_describe, None
            callback()
        if self.pages is not None:
            return self.pages.get(request.get('NextToken'), {'Reservations': []})
        if self.instance is None:
            return {'Reservations': []}
        return {'Reservations': [{'OwnerId': ACCOUNT, 'Instances': [self.instance]}]}


class RecoveryS3(FakeS3):
    def __init__(self):
        super().__init__()
        self.account = ACCOUNT
        self.calls = []

    def call(self, service, operation, request):
        self.calls.append((service, operation, request))
        if (service, operation) == ('sts', 'get-caller-identity'):
            return {'Account': self.account}
        return super().call(service, operation, request)


@unittest.skipUnless(sys.platform == 'linux', 'requires the real POSIX journal')
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rove4k-recovery-test-')
        self.plan = make_plan()
        self.s3 = RecoveryS3()
        self.s3.doc['campaign'] = self.plan.campaign
        self.s3._publish(g.canonical(self.s3.doc))
        self.store = g.S3SharedBudget(self.s3, bucket=self.plan.bucket,
            key=self.plan.campaign + '/shared/budget.json', account=ACCOUNT,
            region=REGION, campaign=self.plan.campaign)
        self.root = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(self.s3.doc['opening']))
        self.journal = Journal(Path(self.temp.name) / 'journal.jsonl', self.plan.campaign)
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)
        self.intent = RecoveryIntent(plan_sha256=self.plan.sha256, launch_token='first-token',
            region=REGION, image_id='ami-12345678', subnet_id='subnet-12345678',
            vpc_id='vpc-12345678', security_group_ids=('sg-12345678',), owner_tag='league-owner-1')
        self.instance = {'InstanceId': 'i-12345678', 'InstanceType': 'm6a.48xlarge',
            'ClientToken': self.intent.launch_token, 'ImageId': self.intent.image_id,
            'SubnetId': self.intent.subnet_id, 'VpcId': self.intent.vpc_id,
            'SecurityGroups': [{'GroupId': 'sg-12345678'}],
            'InstanceLifecycle': 'spot', 'IamInstanceProfile': {'Arn': self.plan.profile_arn},
            'Tags': [{'Key': 'RoveLeagueCampaign', 'Value': self.plan.campaign},
                     {'Key': 'RoveLeagueOwner', 'Value': self.intent.owner_tag}],
            'State': {'Name': 'running'}}
        self.ec2 = Ec2Reads(self.instance)

    def tearDown(self):
        self.journal.close()
        self.temp.cleanup()

    def event(self, number, name, data):
        return self.owner.record(request_id=f'recovery-request-{number:04}', event=name, data=data, at=1000)

    def request(self, *, bound=True):
        self.event(1, 'budget.v2.launch_requested', {'launch_token': self.intent.launch_token,
                    'region': REGION, 'max_hourly_usd': '8'})
        if bound:
            self.event(2, 'budget.v2.instance_bound', {'launch_token': self.intent.launch_token,
                        'instance_id': self.instance['InstanceId']})

    def inspect(self, *, launch_spec=None):
        return inspect_launch(self.plan, self.store, self.owner, self.intent, self.ec2,
                              launch_spec=launch_spec)

    def test_reconcile_after_new_caller_preserves_running_game_without_mutation(self):
        self.request()
        self.event(3, 'budget.v2.game_admitted', {'game_id': 'game-1', 'pair_id': 'pair-1',
                    'launch_token': self.intent.launch_token})
        self.event(4, 'budget.v2.game_release_authorized', {'game_id': 'game-1', 'valid_until_utc': 1005})
        prior_anchor = self.owner.anchor
        report = self.inspect()
        self.assertEqual((report['ec2_state'], report['instance_id']), ('running', 'i-12345678'))
        self.assertEqual(report['ledger_games'], [{'game_id': 'game-1', 'ledger_release_authorized': True,
                                          'ledger_release_observed': False, 'ledger_settled': False}])
        for key in ('launch_authorized', 'scored_go_authorized', 'termination_authorized',
                    'aws_mutation_performed', 'physical_game_settlement_verified'):
            self.assertFalse(report[key])
        self.assertEqual(self.owner.anchor, prior_anchor)
        self.assertEqual([(s, op) for s, op, _ in self.ec2.calls],
                         [('sts', 'get-caller-identity'), ('ec2', 'describe-instances'),
                          ('ec2', 'describe-spot-instance-requests'),
                          ('ssm', 'describe-instance-information')])

    def test_no_result_is_unresolved_not_absence_or_retry(self):
        self.request(bound=False)
        self.ec2.instance = None
        report = self.inspect()
        self.assertEqual(report['ec2_state'], 'unresolved')
        self.assertIsNone(report['instance_id'])
        self.assertFalse(report['absence_proven'])
        self.assertFalse(report['launch_authorized'])
        self.assertEqual(len(self.ec2.calls), 3)

    def test_local_ledger_advance_during_ec2_read_is_explicit(self):
        self.request()
        self.ec2.on_describe = lambda: self.event(3, 'budget.v2.observe', {})
        report = self.inspect()
        self.assertTrue(report['local_journal_changed_during_observation'])
        self.assertFalse(report['scored_go_authorized'])
        self.assertFalse(report['termination_authorized'])

    def test_bound_but_missing_stays_unresolved_and_keeps_identity(self):
        self.request()
        self.ec2.instance = None
        report = self.inspect()
        self.assertEqual((report['ec2_state'], report['instance_id']), ('unresolved', 'i-12345678'))
        self.assertFalse(report['termination_authorized'])

    def test_wrong_project_and_identity_are_rejected(self):
        self.request()
        for field, bad in (('ImageId', 'ami-87654321'), ('SubnetId', 'subnet-87654321'),
                           ('VpcId', 'vpc-87654321'), ('InstanceType', 'm6a.32xlarge'),
                           ('ClientToken', 'other-token'), ('InstanceId', 'i-87654321'),
                           ('InstanceLifecycle', 'scheduled')):
            with self.subTest(field=field):
                original = self.instance[field]
                self.instance[field] = bad
                with self.assertRaises(ValueError):
                    self.inspect()
                self.instance[field] = original
        self.ec2.account = '999999999999'
        previous_s3_calls = len(self.s3.calls)
        with self.assertRaisesRegex(ValueError, 'caller'):
            self.inspect()
        self.assertEqual(self.s3.calls[previous_s3_calls:], [('sts', 'get-caller-identity', {})])
        self.ec2.account = ACCOUNT
        self.s3.account = '999999999999'
        previous_ec2_calls = len(self.ec2.calls)
        with self.assertRaisesRegex(ValueError, 'caller'):
            self.inspect()
        self.assertEqual(len(self.ec2.calls), previous_ec2_calls)

    def test_legacy_tags_and_duplicate_tag_keys_are_rejected(self):
        self.request()
        for extra in ([{'Key': 'RoveCampaign', 'Value': 'legacy'}],
                      [{'Key': 'RoveOwner', 'Value': 'legacy'}],
                      [{'Key': 'RoveLeagueOwner', 'Value': self.intent.owner_tag}]):
            with self.subTest(extra=extra):
                self.instance['Tags'].extend(extra)
                with self.assertRaises(ValueError):
                    self.inspect()
                del self.instance['Tags'][-len(extra):]

    def test_instance_digest_tag_is_checked_without_authenticating_legacy(self):
        self.request()
        self.assertEqual(self.inspect()['instance_launch_digest_tag'], 'missing')
        tag = {'Key': 'RoveLeagueLaunchDigest', 'Value': 'sha256:' +
               hashlib.sha256(self.intent.launch_token.encode('utf-8')).hexdigest()}
        self.instance['Tags'].append(tag)
        report = self.inspect()
        self.assertEqual(report['instance_launch_digest_tag'], 'matches')
        self.assertFalse(report['intent_authenticated'])
        tag['Value'] = 'sha256:' + hashlib.sha256(b'other-token').hexdigest()
        with self.assertRaisesRegex(ValueError, 'digest tag'):
            self.inspect()

    def test_pages_must_not_hide_duplicate_owners_or_cycle(self):
        self.request()
        reservation = {'OwnerId': ACCOUNT, 'Instances': [self.instance]}
        self.ec2.pages = {None: {'Reservations': [reservation], 'NextToken': 'next'},
                          'next': {'Reservations': [reservation]}}
        with self.assertRaisesRegex(ValueError, 'multiple instances'):
            self.inspect()
        self.ec2.pages = {None: {'Reservations': [], 'NextToken': 'next'},
                          'next': {'Reservations': [], 'NextToken': 'next'}}
        report = self.inspect()
        self.assertEqual((report['ec2_state'], report['ec2_observation_reason']),
                         ('unresolved', 'read_incomplete'))
        self.assertFalse(report['absence_proven'])

    def test_original_durable_request_and_plan_binding_are_required(self):
        with self.assertRaisesRegex(ValueError, 'original launch request'):
            self.inspect()
        self.request()
        with self.assertRaisesRegex(ValueError, 'plan'):
            inspect_launch(self.plan, self.store, self.owner, replace(self.intent, plan_sha256='a'*64), self.ec2)

    def test_one_observed_terminated_instance_is_not_permission_to_terminate(self):
        self.request()
        self.instance['State'] = {'Name': 'terminated'}
        report = self.inspect()
        self.assertEqual(report['ec2_state'], 'terminated')
        self.assertFalse(report['termination_authorized'])
        self.assertFalse(report['physical_game_settlement_verified'])

    def spot(self, request_id='sir-12345678', *, state='open', instance_id=None, token_digest=None):
        tags = [{'Key': 'RoveLeagueCampaign', 'Value': self.plan.campaign},
                {'Key': 'RoveLeagueOwner', 'Value': self.intent.owner_tag}]
        if token_digest is not None:
            tags.append({'Key': 'RoveLeagueLaunchDigest', 'Value': token_digest})
        result = {'SpotInstanceRequestId': request_id, 'State': state, 'Type': 'one-time',
                  'Status': {'Code': 'pending-evaluation'}, 'Tags': tags}
        if instance_id is not None:
            result['InstanceId'] = instance_id
        return result

    def test_open_spot_without_instance_is_observed_not_bound_or_absent(self):
        self.request(bound=False)
        self.ec2.instance = None
        token_digest = 'sha256:' + hashlib.sha256(self.intent.launch_token.encode('utf-8')).hexdigest()
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [self.spot(token_digest=token_digest)]}}
        report = self.inspect()
        spot = report['spot_request_observation']
        self.assertEqual((spot['status'], spot['potential_open_request']), ('observed', True))
        self.assertEqual(spot['candidates'][0]['launch_digest_tag'], 'matches')
        self.assertFalse(spot['candidates'][0]['instance_request_crosscheck'])
        self.assertFalse(spot['request_launch_token_verified'])
        self.assertEqual(report['ec2_state'], 'unresolved')
        self.assertFalse(report['absence_proven'])
        self.assertFalse(report['launch_authorized'])
        self.assertFalse(report['physical_game_settlement_verified'])
        self.assertEqual(self.ec2.calls[-1][2]['Filters'], [
            {'Name': 'tag:RoveLeagueCampaign', 'Values': [self.plan.campaign]},
            {'Name': 'tag:RoveLeagueOwner', 'Values': [self.intent.owner_tag]}])

    def test_shared_owner_old_tags_and_other_token_stay_ambiguous(self):
        self.request(bound=False)
        self.ec2.instance = None
        other = 'sha256:' + hashlib.sha256(b'another-token').hexdigest()
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [self.spot(),
            self.spot('sir-87654321', state='active', token_digest=other)]}}
        spot = self.inspect()['spot_request_observation']
        self.assertEqual([row['launch_digest_tag'] for row in spot['candidates']], ['missing', 'different'])
        self.assertFalse(spot['request_launch_token_verified'])
        self.assertTrue(spot['potential_open_request'])

    def test_only_closed_spot_requests_cannot_exclude_hidden_open_request(self):
        self.request(bound=False)
        self.ec2.instance = None
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [self.spot(state='closed')]}}
        spot = self.inspect()['spot_request_observation']
        self.assertEqual(spot['status'], 'observed')
        self.assertIsNone(spot['potential_open_request'])
        self.assertFalse(spot['request_launch_token_verified'])

    def test_bidirectional_spot_reference_and_ssm_ping_are_not_remote_provenance(self):
        self.request()
        self.instance['SpotInstanceRequestId'] = 'sir-12345678'
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [self.spot(state='active',
                                      instance_id='i-12345678')]}}
        self.ec2.ssm_pages = {None: {'InstanceInformationList': [
            {'InstanceId': 'i-12345678', 'PingStatus': 'Online', 'ResourceType': 'EC2Instance'}]}}
        report = self.inspect()
        spot = report['spot_request_observation']
        self.assertTrue(spot['candidates'][0]['instance_request_crosscheck'])
        self.assertFalse(spot['request_launch_token_verified'])
        ssm = report['ssm_agent_observation']
        self.assertEqual((ssm['status'], ssm['agent_ping']), ('observed_agent_only', 'Online'))
        self.assertEqual(ssm['remote_child_ownership'], 'unresolved')
        self.assertFalse(ssm['physical_game_settlement_verified'])
        self.assertFalse(report['remote_owner_authenticated'])
        self.assertFalse(report['physical_game_settlement_verified'])

    def test_one_sided_spot_link_and_unavailable_apis_remain_unresolved(self):
        self.request()
        self.instance['SpotInstanceRequestId'] = 'sir-12345678'
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [self.spot(state='active',
                                      instance_id='i-87654321')]}}
        self.assertFalse(self.inspect()['spot_request_observation']['candidates'][0]['instance_request_crosscheck'])
        self.ec2.spot_error = True
        self.ec2.ssm_error = True
        report = self.inspect()
        self.assertEqual(report['spot_request_observation']['status'], 'unresolved')
        self.assertEqual(report['spot_request_observation']['reason'], 'read_unavailable')
        self.assertIsNone(report['spot_request_observation']['potential_open_request'])
        self.assertEqual(report['ssm_agent_observation']['status'], 'unresolved')
        self.assertEqual(report['ssm_agent_observation']['reason'], 'read_unavailable')
        self.assertFalse(report['termination_authorized'])

    def test_spot_empty_page_continues_and_bad_pagination_fails_closed(self):
        self.request()
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [], 'NextToken': 'next'},
            'next': {'SpotInstanceRequests': [self.spot()]}}
        self.assertEqual(len(self.inspect()['spot_request_observation']['candidates']), 1)
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [], 'NextToken': 'next'},
                               'next': {'SpotInstanceRequests': [], 'NextToken': 'next'}}
        spot = self.inspect()['spot_request_observation']
        self.assertEqual((spot['status'], spot['reason']), ('unresolved', 'read_incomplete'))
        self.ec2.spot_pages = {None: {'SpotInstanceRequests': [self.spot()], 'NextToken': 'next'},
                               'next': {'SpotInstanceRequests': [self.spot()]}}
        self.assertEqual(self.inspect()['spot_request_observation']['status'], 'unresolved')

    def test_unavailable_or_incomplete_ec2_discovery_is_unresolved(self):
        self.request()
        self.ec2.instance_error = True
        report = self.inspect()
        self.assertEqual((report['ec2_state'], report['ec2_observation_reason']),
                         ('unresolved', 'read_unavailable'))
        self.assertEqual(report['instance_id'], 'i-12345678')
        self.assertEqual(report['ssm_agent_observation']['reason'], 'instance_unobserved')
        self.assertFalse(report['absence_proven'])
        self.ec2.instance_error = False
        self.ec2.pages = {None: {'Reservations': [{'OwnerId': ACCOUNT, 'Instances': [self.instance]}],
                                 'NextToken': 'next'},
                          'next': {'Reservations': 'malformed'}}
        report = self.inspect()
        self.assertEqual((report['ec2_state'], report['ec2_observation_reason']),
                         ('unresolved', 'read_incomplete'))
        self.assertFalse(report['absence_proven'])

    def test_launch_record_identity_digest_match_is_not_request_authentication(self):
        self.event(1, 'budget.v2.launch_requested', {'launch_token': self.intent.launch_token,
                   'region': REGION, 'max_hourly_usd': '8', 'plan_sha256': self.plan.sha256,
                   'identity_sha256': g.digest(asdict(self.intent)),
                   'request_sha256': 'a' * 64})
        record = self.inspect()['ledger_launch_record']
        self.assertEqual(record['observation'], 'identity_digest_match')
        self.assertTrue(record['identity_digest_matches'])
        self.assertFalse(record['request_digest_verified'])
        self.assertFalse(record['intent_authenticated'])

    def test_launch_record_legacy_is_unresolved(self):
        self.request(bound=False)
        record = self.inspect()['ledger_launch_record']
        self.assertEqual(record['observation'], 'unresolved')
        self.assertFalse(record['identity_digest_matches'])

    def test_launch_record_mismatched_digest_and_duplicate_token_are_unresolved(self):
        original = {'launch_token': self.intent.launch_token, 'region': REGION,
                    'max_hourly_usd': '8', 'plan_sha256': 'a' * 64,
                    'identity_sha256': g.digest(asdict(self.intent)), 'request_sha256': 'b' * 64}
        self.event(1, 'budget.v2.launch_requested', original)
        record = self.inspect()['ledger_launch_record']
        self.assertEqual(record['observation'], 'unresolved')
        self.assertFalse(record['identity_digest_matches'])
        self.event(2, 'budget.v2.launch_requested', {**original, 'plan_sha256': self.plan.sha256,
                   'identity_sha256': 'c' * 64})
        record = self.inspect()['ledger_launch_record']
        self.assertEqual((record['observation'], record['matching_events']), ('unresolved', 2))
        self.assertFalse(record['intent_authenticated'])

    def test_launch_record_wrong_identity_digest_alone_is_unresolved(self):
        self.event(1, 'budget.v2.launch_requested', {'launch_token': self.intent.launch_token,
                   'region': REGION, 'max_hourly_usd': '8', 'plan_sha256': self.plan.sha256,
                   'identity_sha256': 'c' * 64, 'request_sha256': 'b' * 64})
        record = self.inspect()['ledger_launch_record']
        self.assertEqual(record['observation'], 'unresolved')
        self.assertFalse(record['identity_digest_matches'])

    def test_legacy_request_hash_is_not_reinterpreted_as_new_digest_tag_request(self):
        spec = LeagueLaunchSpec(self.intent, '/dev/sda1', 32, '8', False)
        current = request_preview(self.plan, spec)
        self.assertTrue(all(any(tag['Key'] == 'RoveLeagueLaunchDigest' for tag in item['Tags'])
                            for item in current['TagSpecifications']))
        legacy = {**current, 'TagSpecifications': [
            {**item, 'Tags': [tag for tag in item['Tags'] if tag['Key'] != 'RoveLeagueLaunchDigest']}
            for item in current['TagSpecifications']]}
        self.event(1, 'budget.v2.launch_requested', {'launch_token': self.intent.launch_token,
                   'region': REGION, 'max_hourly_usd': '8', 'plan_sha256': self.plan.sha256,
                   'identity_sha256': g.digest(asdict(self.intent)), 'request_sha256': g.digest(legacy)})
        report = self.inspect(launch_spec=spec)
        record = report['ledger_launch_record']
        self.assertTrue(record['identity_digest_matches'])
        self.assertEqual(record['request_digest_comparison'], 'differs_current_preview')
        self.assertFalse(record['request_digest_verified'])
        self.assertFalse(record['intent_authenticated'])
        self.assertFalse(report['launch_authorized'])

    def test_current_preview_comparison_never_authenticates_a_request(self):
        spec = LeagueLaunchSpec(self.intent, '/dev/sda1', 32, '8', False)
        self.event(1, 'budget.v2.launch_requested', {'launch_token': self.intent.launch_token,
                   'region': REGION, 'max_hourly_usd': '8', 'plan_sha256': self.plan.sha256,
                   'identity_sha256': g.digest(asdict(self.intent)),
                   'request_sha256': g.digest(request_preview(self.plan, spec))})
        record = self.inspect(launch_spec=spec)['ledger_launch_record']
        self.assertEqual(record['request_digest_comparison'], 'matches_current_preview')
        self.assertFalse(record['request_digest_verified'])
        self.assertFalse(record['intent_authenticated'])
        wrong = replace(spec, identity=replace(self.intent, owner_tag='wrong-owner'))
        with self.assertRaisesRegex(ValueError, 'launch specification'):
            self.inspect(launch_spec=wrong)


if __name__ == '__main__':
    unittest.main()
