"""League request/recovery checks use fake AWS; no live launch is attempted."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import global_budget as g
    from . import league_aws_launch as launch
    from .aws import ADVISOR_URL, INSTANCE_TYPE, STANDARD_SPOT_QUOTA, iso
    from .league_aws_launch import LeagueLaunchSpec, advisor_recheck_data, inspect_environment, intent_data, request_preview, review_recorded_intent
    from .league_aws_recovery import RecoveryIntent
    from .ledger import Journal, digest
    from .shared_coordinator import SharedBudgetJournal
    from .test_global_budget import FakeS3
    from .test_league_controller import ACCOUNT, REGION, make_plan
except ImportError:
    import global_budget as g
    import league_aws_launch as launch
    from aws import ADVISOR_URL, INSTANCE_TYPE, STANDARD_SPOT_QUOTA, iso
    from league_aws_launch import LeagueLaunchSpec, advisor_recheck_data, inspect_environment, intent_data, request_preview, review_recorded_intent
    from league_aws_recovery import RecoveryIntent
    from ledger import Journal, digest
    from shared_coordinator import SharedBudgetJournal
    from test_global_budget import FakeS3
    from test_league_controller import ACCOUNT, REGION, make_plan


NOW = 1000000
CALLER = f'arn:aws:sts::{ACCOUNT}:assumed-role/league-controller/test'


class RoleS3(FakeS3):
    def __init__(self):
        super().__init__()
        self.caller = {'Account': ACCOUNT, 'Arn': CALLER}
        self.calls = []

    def call(self, service, operation, request):
        self.calls.append((service, operation))
        if (service, operation) == ('sts', 'get-caller-identity'):
            return self.caller
        return super().call(service, operation, request)


class Ec2Metadata:
    def __init__(self):
        self.region = REGION
        self.calls = []
        self.values = {
            ('sts', 'get-caller-identity'): {'Account': ACCOUNT, 'Arn': CALLER},
            ('iam', 'get-instance-profile'): {'InstanceProfile': {
                'Arn': f'arn:aws:iam::{ACCOUNT}:instance-profile/league-host',
                'Roles': [{'Arn': f'arn:aws:iam::{ACCOUNT}:role/league-host-role'}]}},
            ('iam', 'get-role'): {'Role': {'Arn':
                f'arn:aws:iam::{ACCOUNT}:role/aws-service-role/spot.amazonaws.com/AWSServiceRoleForEC2Spot'}},
            ('ec2', 'describe-instance-types'): {'InstanceTypes': [{'InstanceType': INSTANCE_TYPE,
                'VCpuInfo': {'DefaultVCpus': 192}, 'MemoryInfo': {'SizeInMiB': 786432},
                'SupportedUsageClasses': ['spot'], 'ProcessorInfo': {'SupportedArchitectures': ['x86_64']}}]},
            ('ec2', 'describe-images'): {'Images': [{'ImageId': 'ami-12345678', 'State': 'available',
                'Architecture': 'x86_64', 'PlatformDetails': 'Linux/UNIX', 'RootDeviceName': '/dev/sda1',
                'RootDeviceType': 'ebs', 'BlockDeviceMappings': [{'DeviceName': '/dev/sda1',
                    'Ebs': {'SnapshotId': 'snap-12345678', 'VolumeSize': 20}}]}]},
            ('ec2', 'describe-snapshots'): {'Snapshots': [{'SnapshotId': 'snap-12345678',
                'State': 'completed', 'VolumeSize': 20}]},
            ('ec2', 'describe-subnets'): {'Subnets': [{'SubnetId': 'subnet-12345678', 'VpcId': 'vpc-12345678',
                'State': 'available', 'AvailableIpAddressCount': 4, 'AvailabilityZone': REGION+'a'}]},
            ('ec2', 'describe-security-groups'): {'SecurityGroups': [{'GroupId': 'sg-12345678', 'VpcId': 'vpc-12345678'}]},
            ('ec2', 'describe-instance-type-offerings'): {'InstanceTypeOfferings': [{'InstanceType': INSTANCE_TYPE,
                'Location': REGION+'a'}]},
            ('service-quotas', 'get-service-quota'): {'Quota': {'Value': 192}},
            ('ec2', 'describe-instances'): {'Reservations': []},
            ('ec2', 'describe-spot-instance-requests'): {'SpotInstanceRequests': []},
            ('ec2', 'describe-spot-price-history'): {'SpotPriceHistory': [{'InstanceType': INSTANCE_TYPE,
                'AvailabilityZone': REGION+'a', 'Timestamp': iso(NOW-60), 'SpotPrice': '3.5'}]},
        }

    def call(self, service, operation, request):
        self.calls.append((service, operation, request))
        if (service, operation) not in self.values:
            raise AssertionError('unexpected AWS mutation or operation')
        return self.values[(service, operation)]


class RequestTests(unittest.TestCase):
    def setUp(self):
        self.plan = make_plan()
        self.identity = RecoveryIntent(plan_sha256=self.plan.sha256, launch_token='first-token',
            region=REGION, image_id='ami-12345678', subnet_id='subnet-12345678',
            vpc_id='vpc-12345678', security_group_ids=('sg-12345678',), owner_tag='league-owner-1')
        self.spec = LeagueLaunchSpec(self.identity, '/dev/sda1', 32, '8', False)
        self.advisor = {'source_url': ADVISOR_URL, 'fetched_at': NOW, 'region': REGION,
            'instance_type': INSTANCE_TYPE, 'os': 'Linux', 'band': '<5%',
            'maximum_percent': 5, 'sha256': 'b'*64, 'source_modified_at': NOW}

    def test_request_is_bounded_distinct_and_has_no_deadline_or_credential(self):
        request = request_preview(self.plan, self.spec)
        self.assertEqual((request['MinCount'], request['MaxCount'], request['ClientToken']), (1, 1, 'first-token'))
        self.assertEqual(request['IamInstanceProfile'], {'Arn': self.plan.profile_arn})
        self.assertEqual(request['InstanceMarketOptions']['SpotOptions'],
            {'MaxPrice': '8', 'SpotInstanceType': 'one-time', 'InstanceInterruptionBehavior': 'terminate'})
        self.assertEqual(request['MetadataOptions']['HttpTokens'], 'required')
        self.assertTrue(request['BlockDeviceMappings'][0]['Ebs']['Encrypted'])
        self.assertNotIn('UserData', request)
        self.assertNotIn('InstanceInitiatedShutdownBehavior', request)
        self.assertNotIn('ValidUntil', request['InstanceMarketOptions']['SpotOptions'])
        for resource in request['TagSpecifications']:
            tags = {tag['Key']: tag['Value'] for tag in resource['Tags']}
            self.assertEqual(len(tags), len(resource['Tags']))
            self.assertEqual(set(tags), {'RoveLeagueCampaign', 'RoveLeagueOwner', 'RoveLeagueLaunchDigest'})
            self.assertEqual(tags['RoveLeagueLaunchDigest'],
                'sha256:55b4b48f529c3d2daa027cbffa6cfb6a03690424550f22109e39917406c8243b')
        self.assertEqual({row['ResourceType'] for row in request['TagSpecifications']},
                         {'instance', 'volume', 'network-interface', 'spot-instances-request'})
        self.assertEqual(request['NetworkInterfaces'][0]['SubnetId'], self.identity.subnet_id)

    def test_different_host_has_different_token_and_declared_region(self):
        second = replace(self.identity, launch_token='other-token')
        request = request_preview(self.plan, replace(self.spec, identity=second))
        self.assertEqual(request['ClientToken'], 'other-token')
        for resource in request['TagSpecifications']:
            self.assertIn({'Key': 'RoveLeagueLaunchDigest', 'Value':
                'sha256:6c67163bbed989f232b31acc4f04df54b31285bfc01bd022c735b71e041a4754'}, resource['Tags'])
        with self.assertRaises(ValueError):
            request_preview(self.plan, replace(self.spec, identity=replace(second, region='ap-northeast-1')))

    def test_advisor_source_band_and_freshness_are_required(self):
        intent_data(self.plan, self.spec, self.advisor, NOW)
        changes = ({'band': '5-10%'}, {'maximum_percent': 6}, {'source_url': 'https://example.invalid/'},
                   {'region': 'ap-northeast-1'}, {'source_modified_at': NOW-604801},
                   {'fetched_at': NOW-86401}, {'source_modified_at': None},
                   {'fetched_at': NOW-60, 'source_modified_at': NOW-30},
                   {'fetched_at': NOW+1, 'source_modified_at': NOW})
        for change in changes:
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                intent_data(self.plan, self.spec, {**self.advisor, **change}, NOW)

    def test_advisor_source_modified_at_may_equal_fetch_time(self):
        same_time = {**self.advisor, 'fetched_at': NOW-10, 'source_modified_at': NOW-10}
        self.assertEqual(intent_data(self.plan, self.spec, same_time, NOW)['advisor_source_modified_at'], NOW-10)

    def test_ami_vpc_quota_price_and_role_are_read_before_any_launch(self):
        client = Ec2Metadata()
        report = inspect_environment(self.plan, self.spec, client, NOW)
        self.assertEqual((report['zone'], report['quota_used'], report['spot_price']), (REGION+'a', 0, '3.5'))
        self.assertIsNone(report['capacity_available'])
        self.assertFalse(report['launch_authorized'])
        self.assertFalse(report['aws_mutation_performed'])
        self.assertFalse(any(op in ('run-instances', 'terminate-instances') for _, op, _ in client.calls))
        self.assertEqual(client.calls[0][:2], ('sts', 'get-caller-identity'))
        self.assertIn(('service-quotas', 'get-service-quota', {'ServiceCode': 'ec2', 'QuotaCode': STANDARD_SPOT_QUOTA}), client.calls)

    def test_bad_live_metadata_is_rejected(self):
        for operation, field, value in (
            (('iam', 'get-instance-profile'), 'InstanceProfile', {'Arn': 'wrong', 'Roles': []}),
            (('iam', 'get-role'), 'Role', {'Arn': 'wrong'}),
            (('ec2', 'describe-images'), 'Images', []),
            (('ec2', 'describe-snapshots'), 'Snapshots', [{'SnapshotId': 'snap-12345678', 'State': 'completed', 'VolumeSize': 33}]),
            (('ec2', 'describe-security-groups'), 'SecurityGroups', []),
            (('service-quotas', 'get-service-quota'), 'Quota', {'Value': 191}),
            (('ec2', 'describe-spot-price-history'), 'SpotPriceHistory', []),
            (('sts', 'get-caller-identity'), 'Account', '999999999999'),
        ):
            with self.subTest(operation=operation, field=field):
                client = Ec2Metadata()
                client.values[operation][field] = value
                with self.assertRaises(ValueError):
                    inspect_environment(self.plan, self.spec, client, NOW)
                self.assertFalse(any(op == 'run-instances' for _, op, _ in client.calls))

    def test_last_price_change_before_query_window_remains_valid(self):
        client = Ec2Metadata()
        client.values[('ec2', 'describe-spot-price-history')]['SpotPriceHistory'][0]['Timestamp'] = iso(NOW-7200)
        report = inspect_environment(self.plan, self.spec, client, NOW)
        self.assertEqual(report['price_changed_at'], NOW-7200)
        self.assertEqual(report['observed_at'], NOW)
        self.assertEqual(report['spot_price'], '3.5')

    def test_extra_ami_ebs_volume_requires_explicit_cost_and_encryption_review(self):
        client = Ec2Metadata()
        client.values[('ec2', 'describe-images')]['Images'][0]['BlockDeviceMappings'].append(
            {'DeviceName': '/dev/sdb', 'Ebs': {'SnapshotId': 'snap-87654321', 'VolumeSize': 20}})
        with self.assertRaisesRegex(ValueError, 'additional AMI EBS'):
            inspect_environment(self.plan, self.spec, client, NOW)

    def test_invalid_spot_price_bounds_are_rejected(self):
        for price in ('0', '0.0001', '0.001', '8.1', 'NaN'):
            with self.subTest(price=price), self.assertRaises((ValueError, TypeError)):
                replace(self.spec, max_hourly_usd=price)
        self.assertEqual(replace(self.spec, max_hourly_usd='0.0011').max_hourly_usd, '0.0011')


@unittest.skipUnless(sys.platform == 'linux', 'requires the real POSIX journal')
class LedgerIntentTests(RequestTests):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix='rove4k-launch-test-')
        self.client = RoleS3()
        self.client.doc['campaign'] = self.plan.campaign
        self.client._publish(g.canonical(self.client.doc))
        self.store = g.S3SharedBudget(self.client, bucket=self.plan.bucket,
            key=self.plan.campaign + '/shared/budget.json', account=ACCOUNT,
            region=REGION, campaign=self.plan.campaign)
        self.root = g.Anchor(-1, g.ZERO, self.store.authority, g.digest(self.client.doc['opening']))
        self.journal = Journal(Path(self.temp.name) / 'journal.jsonl', self.plan.campaign)
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)

    def tearDown(self):
        self.journal.close()
        self.temp.cleanup()

    def record(self, request_id, data, at=NOW):
        return self.owner.record(request_id=request_id, event='budget.v2.launch_requested', data=data, at=at)

    def review(self, advisor=None, now=NOW):
        return review_recorded_intent(self.plan, self.spec, self.store, self.owner, advisor or self.advisor, now)

    def test_exact_durable_intent_required_and_still_no_authority(self):
        with self.assertRaisesRegex(ValueError, 'durable'):
            self.review()
        data = intent_data(self.plan, self.spec, self.advisor, NOW)
        self.assertEqual(data['request_format'], 'rove4k-league-run-instances-v1')
        self.assertEqual(data['request_canonical_json'],
                         g.canonical(request_preview(self.plan, self.spec)).decode('utf-8'))
        self.assertNotIn('UserData', data['request_canonical_json'])
        self.record('league-launch-request-01', data)
        report = self.review()
        self.assertTrue(report['exact_intent_recorded'])
        self.assertEqual(report['request_sha256'], data['request_sha256'])
        self.assertFalse(report['advisor_input_authenticated'])
        self.assertFalse(report['trusted_clock_verified'])
        self.assertFalse(report['global_fence_verified'])
        self.assertFalse(report['launch_authorized'])
        self.assertFalse(report['retry_authorized'])

    def test_duplicate_token_event_is_not_a_new_attempt(self):
        data = intent_data(self.plan, self.spec, self.advisor, NOW)
        self.record('league-launch-request-01', data)
        self.record('league-launch-request-02', data)
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.review()

    def test_producer_rejects_userdata_before_journal_write(self):
        original = request_preview(self.plan, self.spec)
        before = self.owner.anchor
        with patch.object(launch, 'request_preview', return_value={**original, 'UserData': 'untrusted'}):
            with self.assertRaisesRegex(ValueError, 'frozen v1'):
                intent_data(self.plan, self.spec, self.advisor, NOW)
        self.assertEqual(self.owner.anchor, before)

    def test_changed_request_or_recorded_binding_is_rejected(self):
        data = intent_data(self.plan, self.spec, self.advisor, NOW)
        self.record('league-launch-request-01', data)
        with self.assertRaisesRegex(ValueError, 'durable'):
            review_recorded_intent(self.plan, replace(self.spec, root_volume_gib=33),
                                   self.store, self.owner, self.advisor, NOW)
        changed_vpc = replace(self.spec, identity=replace(self.identity, vpc_id='vpc-87654321'))
        self.assertEqual(request_preview(self.plan, changed_vpc), request_preview(self.plan, self.spec))
        with self.assertRaisesRegex(ValueError, 'durable'):
            review_recorded_intent(self.plan, changed_vpc, self.store, self.owner, self.advisor, NOW)
        self.owner.record(request_id='league-launch-binding-01', event='budget.v2.instance_bound',
            data={'launch_token': 'first-token', 'instance_id': 'i-12345678'}, at=NOW)
        with self.assertRaisesRegex(ValueError, 'bound'):
            self.review()

    def test_legacy_untagged_intent_is_not_reinterpreted_as_tagged_request(self):
        # The token is not a new request when only its tags changed: EC2
        # idempotency and journal request identity must retain the old bytes.
        legacy_request = request_preview(self.plan, self.spec)
        for resource in legacy_request['TagSpecifications']:
            resource['Tags'] = [tag for tag in resource['Tags']
                                if tag['Key'] != 'RoveLeagueLaunchDigest']
        tagged = intent_data(self.plan, self.spec, self.advisor, NOW)
        old = {**tagged, 'request_sha256': digest(legacy_request)}
        self.assertNotEqual(old['request_sha256'], tagged['request_sha256'])
        self.record('legacy-untagged-request-01', old)
        before = self.owner.anchor
        with self.assertRaisesRegex(ValueError, 'durable'):
            self.review()
        self.assertEqual(before, self.owner.anchor)
        self.assertFalse(any(service == 'ec2' and op == 'run-instances' for service, op in self.client.calls))

    def test_aggregate_budget_ceiling_and_uncertain_owner_block(self):
        data = intent_data(self.plan, self.spec, self.advisor, NOW)
        self.record('league-launch-request-01', data)
        fresh = {**self.advisor, 'fetched_at': NOW+45000}
        with self.assertRaisesRegex(ValueError, 'ceiling'):
            self.review(advisor=fresh, now=NOW+45000)
        self.owner._blocked = True
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            self.review()

    def test_new_advisor_source_requires_a_durable_same_request_recheck(self):
        initial = intent_data(self.plan, self.spec, self.advisor, NOW)
        self.record('league-launch-request-01', initial)
        updated = {**self.advisor, 'sha256': 'c'*64, 'source_modified_at': NOW+1, 'fetched_at': NOW+1}
        with self.assertRaisesRegex(ValueError, 'recheck'):
            self.review(advisor=updated, now=NOW+1)
        self.owner.record(request_id='league-advisor-recheck-01', event='budget.v2.observe',
            data=advisor_recheck_data(self.plan, self.spec, updated, NOW+1), at=NOW+1)
        report = self.review(advisor=updated, now=NOW+1)
        self.assertTrue(report['advisor_source_recorded'])
        self.assertFalse(report['launch_authorized'])
        self.assertFalse(report['advisor_input_authenticated'])
        # A still-fresh older source must not override a later durable check.
        with self.assertRaisesRegex(ValueError, 'latest durable'):
            self.review(advisor={**self.advisor, 'fetched_at': NOW+1}, now=NOW+1)
        newer = {**updated, 'sha256': 'd'*64, 'source_modified_at': NOW+2, 'fetched_at': NOW+2}
        self.owner.record(request_id='league-advisor-recheck-02', event='budget.v2.observe',
            data=advisor_recheck_data(self.plan, self.spec, newer, NOW+2), at=NOW+2)
        with self.assertRaisesRegex(ValueError, 'latest durable'):
            self.review(advisor={**updated, 'fetched_at': NOW+2}, now=NOW+2)
        self.assertTrue(self.review(advisor=newer, now=NOW+2)['advisor_source_recorded'])

    def test_restarted_owner_accepts_original_exact_intent_without_sending(self):
        data = intent_data(self.plan, self.spec, self.advisor, NOW)
        self.record('league-launch-request-01', data)
        self.journal.close()
        self.journal = Journal(Path(self.temp.name) / 'journal.jsonl', self.plan.campaign)
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)
        report = self.review()
        self.assertEqual(report['ledger_anchor_sha256'], self.owner.anchor.sha256)
        self.assertFalse(report['prior_dispatch_absence_verified'])
        self.assertFalse(report['aws_mutation_performed'])

    def test_cap_blocks_second_owner_without_settling_an_existing_game(self):
        first = intent_data(self.plan, self.spec, self.advisor, NOW)
        self.record('league-launch-request-01', first)
        self.owner.record(request_id='league-launch-binding-01', event='budget.v2.instance_bound',
            data={'launch_token': 'first-token', 'instance_id': 'i-12345678'}, at=NOW)
        self.owner.record(request_id='league-game-admitted-01', event='budget.v2.game_admitted',
            data={'launch_token': 'first-token', 'game_id': 'game-1', 'pair_id': 'pair-1'}, at=NOW)
        self.owner.record(request_id='league-game-release-001', event='budget.v2.game_release_authorized',
            data={'game_id': 'game-1', 'valid_until_utc': NOW+1}, at=NOW)
        second = replace(self.spec, identity=replace(self.identity, launch_token='other-token'))
        self.record('league-launch-request-02', intent_data(self.plan, second, self.advisor, NOW))
        old = self.owner.anchor
        with self.assertRaisesRegex(ValueError, 'ceiling'):
            review_recorded_intent(self.plan, second, self.store, self.owner,
                                   {**self.advisor, 'fetched_at': NOW+22500}, NOW+22500)
        self.assertEqual(self.owner.anchor, old)
        snapshot = self.store.load(self.owner.anchor)
        self.assertEqual(snapshot.rows[-1]['event'], 'budget.v2.launch_requested')
        self.assertFalse(any(row['event'] == 'budget.v2.game_settled' for row in snapshot.rows))


if __name__ == '__main__':
    unittest.main()
