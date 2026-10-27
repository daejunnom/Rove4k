"""League EC2 recovery is read-only; mock responses are not AWS evidence."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from . import global_budget as g
    from .league_aws_recovery import RecoveryIntent, inspect_launch
    from .ledger import Journal
    from .shared_coordinator import SharedBudgetJournal
    from .test_global_budget import FakeS3
    from .test_league_controller import ACCOUNT, REGION, make_plan
except ImportError:
    import global_budget as g
    from league_aws_recovery import RecoveryIntent, inspect_launch
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

    def call(self, service, operation, request):
        self.calls.append((service, operation, request))
        if (service, operation) == ('sts', 'get-caller-identity'):
            return {'Account': self.account}
        if (service, operation) != ('ec2', 'describe-instances'):
            raise AssertionError('unexpected AWS mutation or operation')
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

    def inspect(self):
        return inspect_launch(self.plan, self.store, self.owner, self.intent, self.ec2)

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
                         [('sts', 'get-caller-identity'), ('ec2', 'describe-instances')])

    def test_no_result_is_unresolved_not_absence_or_retry(self):
        self.request(bound=False)
        self.ec2.instance = None
        report = self.inspect()
        self.assertEqual(report['ec2_state'], 'unresolved')
        self.assertIsNone(report['instance_id'])
        self.assertFalse(report['absence_proven'])
        self.assertFalse(report['launch_authorized'])
        self.assertEqual(len(self.ec2.calls), 2)

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

    def test_pages_must_not_hide_duplicate_owners_or_cycle(self):
        self.request()
        reservation = {'OwnerId': ACCOUNT, 'Instances': [self.instance]}
        self.ec2.pages = {None: {'Reservations': [reservation], 'NextToken': 'next'},
                          'next': {'Reservations': [reservation]}}
        with self.assertRaisesRegex(ValueError, 'multiple instances'):
            self.inspect()
        self.ec2.pages = {None: {'Reservations': [], 'NextToken': 'next'},
                          'next': {'Reservations': [], 'NextToken': 'next'}}
        with self.assertRaisesRegex(ValueError, 'pagination'):
            self.inspect()

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


if __name__ == '__main__':
    unittest.main()
