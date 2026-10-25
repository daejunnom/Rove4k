"""Actual AWS port logic with an in-memory service boundary, never an account."""
from dataclasses import replace
import base64
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from .aws import (ACCOUNT_PLAN_ENDPOINT, ACCOUNT_PLAN_REGION, ADVISOR_URL, AWSCLI, AWSPlan, AwsError,
                      account_plan_preflight, digest, iso, launch,
                      observe_termination, close_ownership, recover_launch, S3Evidence, verify_owned_lease, pages, preflight, terminate, verify_watchdog)
    from .budget import CampaignBudget
except ImportError:
    from aws import (ACCOUNT_PLAN_ENDPOINT, ACCOUNT_PLAN_REGION, ADVISOR_URL, AWSCLI, AWSPlan, AwsError,
                     account_plan_preflight, digest, iso, launch,
                     observe_termination, close_ownership, recover_launch, S3Evidence, verify_owned_lease, pages, preflight, terminate, verify_watchdog)
    from budget import CampaignBudget


def plan():
    return AWSPlan('campaign-a', '123456789012', 'us-east-2', 'a' * 32, 'launch-token-one',
        'ami-1234567890abcdef0', 'subnet-1234567890abcdef0', 'sg-1234567890abcdef0',
        'arn:aws:iam::123456789012:instance-profile/rove-instance',
        'arn:aws:iam::123456789012:role/rove-controller', 'rove-watchdog', 'rove-ownership',
        'rove-deadline', 'arn:aws:lambda:us-east-2:123456789012:function:rove-deadline',
        'rove-artifacts', 40000)


class FakeAWS:
    def __init__(self, configured=None):
        self.plan = configured or plan()
        self.region = self.plan.region
        self.stack_project_region = self.plan.project_region
        self.calls, self.records = [], {}
        self.instance = None
        self.schedule_enabled = True
        self.quota = 192
        self.price = '4.50'
        self.dryrun_code = 'DryRunOperation'
        self.lose_launch_response = False
        self.caller_account = self.plan.account_id
        self.caller_instance = False
        self.caller_instance_id = 'i-1234567890abcdef0'
        self.account_plan_response = {'accountId': self.plan.account_id,
            'accountPlanType': 'PAID', 'accountPlanStatus': 'ACTIVE'}
        self.account_plan_error = None

    def account_plan_state(self):
        return self.call('freetier', 'get-account-plan-state', {})

    def call(self, service, operation, request):
        self.calls.append((service, operation, request))
        p = self.plan
        if (service, operation) == ('freetier', 'get-account-plan-state'):
            if self.account_plan_error is not None:
                raise self.account_plan_error
            return self.account_plan_response
        if (service, operation) == ('sts', 'get-caller-identity'):
            if self.caller_instance:
                return {'Account': self.caller_account,
                    'Arn': 'arn:aws:sts::' + self.caller_account + ':assumed-role/rove-instance-role/' + self.caller_instance_id,
                    'UserId': 'AROAOWNEDROLE:' + self.caller_instance_id}
            return {'Account': self.caller_account,
                    'Arn': 'arn:aws:sts::' + self.caller_account + ':assumed-role/rove-controller/test'}
        if (service, operation) == ('cloudformation', 'describe-stacks'):
            parameters = {'CampaignId': p.campaign_id, 'OwnerNonce': p.owner_nonce,
                          'HardDeadlineUtc': iso(p.deadline_epoch)[:-1]}
            if self.stack_project_region is not None:
                parameters['ProjectRegion'] = self.stack_project_region
            outputs = {'OwnershipTable': p.ownership_table, 'ScheduleName': p.schedule_name,
                'WatchdogArn': p.watchdog_arn, 'InstanceProfileArn': p.instance_profile_arn,
                'SecurityGroupId': p.security_group_id, 'ArtifactBucket': p.artifact_bucket,
                'ControllerRoleArn': p.controller_role_arn}
            return {'Stacks': [{'StackStatus': 'CREATE_COMPLETE', 'StackId': 'owned-stack-id',
                'Parameters': [{'ParameterKey': k, 'ParameterValue': v} for k, v in parameters.items()],
                'Outputs': [{'OutputKey': k, 'OutputValue': v} for k, v in outputs.items()]}]}
        if (service, operation) == ('scheduler', 'get-schedule'):
            return {'State': 'ENABLED' if self.schedule_enabled else 'DISABLED',
                'ScheduleExpression': 'at(' + iso(p.deadline_epoch)[:-1] + ')',
                'ScheduleExpressionTimezone': 'UTC', 'FlexibleTimeWindow': {'Mode': 'OFF'},
                'Target': {'Arn': p.watchdog_arn}, 'Arn': 'owned-schedule-arn'}
        if (service, operation) == ('iam', 'get-role'):
            return {'Role': {'Arn': 'arn:aws:iam::' + p.account_id + ':role/aws-service-role/spot.amazonaws.com/AWSServiceRoleForEC2Spot'}}
        if (service, operation) == ('iam', 'get-instance-profile'):
            return {'InstanceProfile': {'Arn': p.instance_profile_arn, 'Roles': [{
                'Arn': 'arn:aws:iam::' + p.account_id + ':role/rove-instance-role',
                'RoleName': 'rove-instance-role', 'RoleId': 'AROAOWNEDROLE'}]}}
        if (service, operation) == ('ec2', 'describe-instance-types'):
            return {'InstanceTypes': [{'InstanceType': 'm6a.48xlarge', 'VCpuInfo': {'DefaultVCpus': 192},
                'MemoryInfo': {'SizeInMiB': 786432}, 'SupportedUsageClasses': ['on-demand', 'spot'],
                'ProcessorInfo': {'SupportedArchitectures': ['x86_64']}}]}
        if (service, operation) == ('ec2', 'describe-images'):
            return {'Images': [{'ImageId': p.ami_id, 'State': 'available', 'Architecture': 'x86_64',
                               'PlatformDetails': 'Linux/UNIX', 'RootDeviceName': '/dev/sda1'}]}
        if (service, operation) == ('ec2', 'describe-subnets'):
            return {'Subnets': [{'SubnetId': p.subnet_id, 'State': 'available', 'AvailableIpAddressCount': 10,
                                'AvailabilityZone': p.region + 'a', 'VpcId': 'vpc-owned'}]}
        if (service, operation) == ('ec2', 'describe-security-groups'):
            return {'SecurityGroups': [{'GroupId': p.security_group_id, 'VpcId': 'vpc-owned'}]}
        if (service, operation) == ('ec2', 'describe-instance-type-offerings'):
            return {'InstanceTypeOfferings': [{'InstanceType': 'm6a.48xlarge', 'Location': p.region + 'a'}]}
        if (service, operation) == ('service-quotas', 'get-service-quota'):
            return {'Quota': {'Value': self.quota}}
        if (service, operation) == ('ec2', 'describe-spot-price-history'):
            return {'SpotPriceHistory': [{'InstanceType': 'm6a.48xlarge',
                'AvailabilityZone': p.region + 'a', 'SpotPrice': self.price, 'Timestamp': iso(900)}]}
        if (service, operation) == ('ec2', 'describe-spot-instance-requests'):
            return {'SpotInstanceRequests': []}
        if (service, operation) == ('ec2', 'describe-instances'):
            if request['Filters'][0]['Name'] == 'client-token' and self.instance is not None:
                return {'Reservations': [{'OwnerId': p.account_id, 'Instances': [self.instance]}]}
            return {'Reservations': []}
        if (service, operation) == ('ec2', 'run-instances'):
            if request.get('DryRun'):
                raise AwsError(self.dryrun_code, 'ec2.run-instances')
            self.instance = {'InstanceId': 'i-1234567890abcdef0', 'ClientToken': p.launch_token,
                'InstanceType': 'm6a.48xlarge', 'ImageId': p.ami_id, 'SubnetId': p.subnet_id,
                'IamInstanceProfile': {'Arn': p.instance_profile_arn},
                'Tags': [{'Key': 'RoveCampaign', 'Value': p.campaign_id}, {'Key': 'RoveOwner', 'Value': p.owner_nonce}],
                'LaunchTime': iso(1000), 'State': {'Name': 'pending'}}
            if self.lose_launch_response:
                self.lose_launch_response = False
                raise AwsError('ObservationTimeout', 'ec2.run-instances')
            return {'OwnerId': p.account_id, 'Instances': [self.instance]}
        if service == 'dynamodb':
            if operation == 'get-item':
                key = request['Key']['record_id']['S']
                return {'Item': self.records[key]} if key in self.records else {}
            if operation == 'put-item':
                item = request['Item']
                key = item['record_id']['S']
                if key in self.records:
                    raise AwsError('ConditionalCheckFailedException', 'dynamodb.put-item')
                self.records[key] = item
                return {}
        if (service, operation) == ('ec2', 'terminate-instances'):
            self.instance['State'] = {'Name': 'shutting-down'}
            return {'TerminatingInstances': [{'InstanceId': self.instance['InstanceId'],
                                              'CurrentState': {'Name': 'shutting-down'}}]}
        raise AssertionError('unexpected AWS call ' + str((service, operation, request)))


class AWSTests(unittest.TestCase):
    def advisor(self, at=1000):
        return {'source_url': ADVISOR_URL, 'fetched_at': at, 'region': 'us-east-2',
                'instance_type': 'm6a.48xlarge', 'os': 'Linux', 'maximum_percent': 5,
                'band': '<5%', 'sha256': 'b' * 64, 'source_modified_at': at}

    def setup_launch(self):
        p, client = plan(), FakeAWS()
        receipt = preflight(client, p, self.advisor(), 1000)
        self.assertTrue(receipt['allowed'], receipt)
        budget = CampaignBudget(p.campaign_id).apply('budget.launch_requested', {
            'launch_token': p.launch_token, 'max_hourly_usd': p.max_hourly_usd}, 1000)
        return p, client, receipt, budget

    def test_plan_has_fixed_spot_caps_and_no_side_effects(self):
        p = plan()
        body = p.request()
        self.assertEqual(body['InstanceType'], 'm6a.48xlarge')
        self.assertEqual((body['MinCount'], body['MaxCount']), (1, 1))
        self.assertEqual(body['InstanceMarketOptions']['SpotOptions']['InstanceInterruptionBehavior'], 'terminate')
        self.assertEqual(body['ClientToken'], p.launch_token)
        self.assertTrue(body['BlockDeviceMappings'][0]['Ebs']['DeleteOnTermination'])
        self.assertEqual(body['InstanceInitiatedShutdownBehavior'], 'terminate')
        self.assertIn(str(p.deadline_epoch), base64.b64decode(body['UserData']).decode())
        self.assertFalse(p.as_dict()['paid_launch_performed'])
        self.assertEqual(AWSPlan.from_dict(p.as_dict()), p)
        changed = p.as_dict()
        changed['request']['MinCount'] = 2
        with self.assertRaisesRegex(ValueError, 'derived'):
            AWSPlan.from_dict(changed)
        with self.assertRaises(ValueError):
            replace(p, max_hourly_usd='8.1')

    def test_preflight_checks_dryrun_but_does_not_claim_capacity(self):
        p, client, receipt, _ = self.setup_launch()
        self.assertIsNone(receipt['capacity_available'])
        self.assertFalse(receipt['paid_launch_performed'])
        runs = [request for service, operation, request in client.calls if (service, operation) == ('ec2', 'run-instances')]
        self.assertEqual(len(runs), 1)
        self.assertIs(runs[0]['DryRun'], True)

    def test_project_region_is_explicit_and_cannot_fall_back(self):
        with self.assertRaisesRegex(ValueError, 'project region'):
            replace(plan(), project_region='ap-southeast-2')
        p = replace(plan(), region='ap-southeast-2', project_region='ap-southeast-2',
                    watchdog_arn='arn:aws:lambda:ap-southeast-2:123456789012:function:rove-deadline')
        self.assertEqual(AWSPlan.from_dict(p.as_dict()), p)
        self.assertEqual(p.intent(1000)['project_region'], 'ap-southeast-2')
        client = FakeAWS(p)
        advisor = {**self.advisor(), 'region': p.region}
        self.assertTrue(preflight(client, p, advisor, 1000)['allowed'])
        client.stack_project_region = 'us-east-1'
        self.assertIn('identity/deadline', ' '.join(preflight(client, p, advisor, 1000)['blockers']))
        client.calls.clear()
        client.region = 'us-east-1'
        receipt = preflight(client, p, advisor, 1000)
        self.assertFalse(receipt['allowed'])
        self.assertIn('no fallback', ' '.join(receipt['blockers']))
        self.assertEqual(client.calls, [])
        with self.assertRaisesRegex(ValueError, 'no fallback'):
            verify_watchdog(client, p, 1000)
        self.assertEqual(client.calls, [])
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'no fallback'):
                S3Evidence(client, p, Path(temporary))

    def test_account_plan_gate_is_readonly_and_records_free_or_unknown(self):
        for response, reason in (
                ({'accountId': plan().account_id, 'accountPlanType': 'FREE', 'accountPlanStatus': 'ACTIVE'}, 'PAID'),
                ({'accountId': plan().account_id, 'accountPlanType': 'TRIAL', 'accountPlanStatus': 'ACTIVE'}, 'PAID'),
                ({'accountId': plan().account_id, 'accountPlanType': 'PAID', 'accountPlanStatus': 'UNKNOWN'}, 'status'),
                ({'accountId': '999999999999', 'accountPlanType': 'PAID', 'accountPlanStatus': 'ACTIVE'}, 'account'),
                ({}, 'account')):
            with self.subTest(response=response):
                client = FakeAWS()
                client.account_plan_response = response
                receipt = preflight(client, plan(), self.advisor(), 1000)
                self.assertFalse(receipt['allowed'])
                self.assertEqual(receipt['account_plan']['account_plan_type'], response.get('accountPlanType'))
                self.assertIn(reason, ' '.join(receipt['blockers']))
                self.assertEqual([(s, o) for s, o, _ in client.calls],
                                 [('sts', 'get-caller-identity'), ('freetier', 'get-account-plan-state')])
        client = FakeAWS()
        client.account_plan_error = AwsError('AccessDeniedException', 'freetier.get-account-plan-state')
        report = account_plan_preflight(client, plan().account_id, 1000)
        self.assertFalse(report['allowed'])
        self.assertIn('AccessDeniedException', report['blockers'][0])
        self.assertFalse(report['automatic_upgrade_performed'])
        self.assertFalse(account_plan_preflight(object(), plan().account_id, 1000)['allowed'])

    def test_account_plan_can_be_checked_before_any_stack_or_instance_exists(self):
        client = FakeAWS()
        report = account_plan_preflight(client, plan().account_id, 1000)
        self.assertTrue(report['allowed'])
        self.assertEqual(report['source']['region'], ACCOUNT_PLAN_REGION)
        self.assertEqual(report['source']['endpoint'], ACCOUNT_PLAN_ENDPOINT)
        self.assertEqual(client.calls, [('freetier', 'get-account-plan-state', {})])
        client.account_plan_response['accountPlanStatus'] = 'EXPIRED'
        report = account_plan_preflight(client, plan().account_id, 1000)
        self.assertTrue(report['allowed'])
        self.assertEqual(report['account_plan_status'], 'EXPIRED')

    def test_launch_rechecks_paid_plan_before_persisting_or_running(self):
        p, client, receipt, budget = self.setup_launch()
        client.calls.clear()
        client.account_plan_response['accountPlanType'] = 'FREE'
        with self.assertRaisesRegex(ValueError, 'automatic upgrade is forbidden'):
            launch(client, p, budget, receipt, 1000)
        self.assertEqual(client.records, {})
        self.assertFalse(any(s == 'dynamodb' or (s == 'ec2' and o == 'run-instances')
                             for s, o, _ in client.calls))

    def test_global_billing_read_does_not_change_workload_transport(self):
        client = AWSCLI('ap-southeast-2', executable='awscli.exe')
        response = {'accountId': plan().account_id, 'accountPlanType': 'PAID', 'accountPlanStatus': 'ACTIVE'}
        completed = SimpleNamespace(returncode=0, stdout=json.dumps(response).encode(), stderr=b'')
        with patch('subprocess.run', return_value=completed) as run, patch.object(AWSCLI, 'command_prefix', return_value=['awscli.exe']):
            self.assertEqual(client.account_plan_state(), response)
        argv = run.call_args.args[0]
        self.assertEqual(argv[argv.index('--region') + 1], ACCOUNT_PLAN_REGION)
        self.assertEqual(argv[argv.index('--endpoint-url') + 1], ACCOUNT_PLAN_ENDPOINT)
        self.assertIn('get-account-plan-state', argv)
        self.assertNotIn('upgrade-account-plan', argv)
        self.assertEqual(client.region, 'ap-southeast-2')

    def test_publisher_declares_bounded_transport_budget_without_claiming_owner_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            client = AWSCLI(plan().region, timeout=30)
            evidence = S3Evidence(client, plan(), Path(temporary))
            self.assertEqual(evidence.max_publish_seconds, 65)
            client.timeout = float('inf')
            with self.assertRaisesRegex(ValueError, 'finite'):
                _ = evidence.max_publish_seconds
        for value in (0, -1, True, float('nan'), float('inf')):
            with self.subTest(timeout=value), self.assertRaisesRegex(ValueError, 'finite'):
                AWSCLI(plan().region, timeout=value)

    def test_preflight_denials_are_specific_and_no_paid_requests(self):
        for attribute, value, reason in (('quota', 191, '192'), ('price', '8.01', 'price'),
                                         ('dryrun_code', 'UnauthorizedOperation', 'UnauthorizedOperation'),
                                         ('schedule_enabled', False, 'schedule')):
            with self.subTest(attribute=attribute):
                client = FakeAWS()
                setattr(client, attribute, value)
                receipt = preflight(client, plan(), self.advisor(), 1000)
                self.assertFalse(receipt['allowed'])
                self.assertIn(reason, ' '.join(receipt['blockers']))
                self.assertFalse(any(operation == 'run-instances' and not request.get('DryRun') for _, operation, request in client.calls))
        client = FakeAWS()
        client.caller_account = '999999999999'
        self.assertFalse(preflight(client, plan(), self.advisor(), 1000)['allowed'])
        self.assertEqual(len(client.calls), 1)

    def test_launch_saves_intent_before_paid_request_and_binding_after(self):
        p, client, receipt, budget = self.setup_launch()
        output = launch(client, p, budget, receipt, 1000)
        operations = [(service, operation) for service, operation, _ in client.calls]
        paid = next(i for i, (_, operation, request) in enumerate(client.calls)
                    if operation == 'run-instances' and not request.get('DryRun'))
        self.assertIn(('dynamodb', 'put-item'), operations[:paid])
        self.assertIn(('dynamodb', 'put-item'), operations[paid + 1:])
        self.assertEqual(output['ownership']['instance_id'], 'i-1234567890abcdef0')
        self.assertFalse(output['termination_observed'])

    def test_lost_launch_response_reconciles_same_token_without_second_launch(self):
        p, client, receipt, budget = self.setup_launch()
        client.lose_launch_response = True
        with self.assertRaisesRegex(AwsError, 'ObservationTimeout'):
            launch(client, p, budget, receipt, 1000)
        self.assertNotIn('owned#' + p.launch_token, client.records)
        output = launch(client, p, budget, receipt, 1001)
        self.assertEqual(output['instance_id'], client.instance['InstanceId'])
        self.assertEqual(sum(operation == 'run-instances' and not request.get('DryRun') for _, operation, request in client.calls), 1)

    def test_termination_request_is_not_physical_termination(self):
        p, client, receipt, budget = self.setup_launch()
        instance_id = launch(client, p, budget, receipt, 1000)['instance_id']
        self.assertFalse(terminate(client, p, instance_id)['observed'])
        self.assertFalse(observe_termination(client, p, instance_id)['observed'])
        client.instance['State'] = {'Name': 'terminated'}
        self.assertTrue(observe_termination(client, p, instance_id)['observed'])
        closed = close_ownership(client, p, instance_id, 2000, 'DescribeInstances request1')
        self.assertEqual(closed['terminal_state'], 'terminated')
        self.assertEqual(close_ownership(client, p, instance_id, 3000, 'later query'), closed)

    def test_scored_jobs_require_actual_running_ownership_and_profile_session(self):
        p, client, receipt, budget = self.setup_launch()
        instance_id = launch(client, p, budget, receipt, 1000)['instance_id']
        budget = budget.apply('budget.instance_bound', {'launch_token': p.launch_token,
                                                       'instance_id': instance_id}, 1000)
        with self.assertRaisesRegex(ValueError, 'running'):
            verify_owned_lease(client, p, budget, 1000)
        client.instance['State'] = {'Name': 'running'}
        self.assertTrue(verify_owned_lease(client, p, budget, 1000)['verified'])
        client.caller_instance = True
        proof = verify_owned_lease(client, p, budget, 1000, caller_kind='instance')
        self.assertEqual(proof['instance_id'], instance_id)
        client.caller_instance_id = 'i-fffffffffffffffff'
        with self.assertRaisesRegex(ValueError, 'profile session'):
            verify_owned_lease(client, p, budget, 1000, caller_kind='instance')
        client.caller_instance_id = instance_id
        client.schedule_enabled = False
        with self.assertRaisesRegex(ValueError, 'schedule'):
            verify_owned_lease(client, p, budget, 1000, caller_kind='instance')

    def test_matching_tags_alone_cannot_authorize_termination(self):
        p, client, receipt, budget = self.setup_launch()
        instance_id = launch(client, p, budget, receipt, 1000)['instance_id']
        client.instance['ImageId'] = 'ami-fffffffffffffffff'
        with self.assertRaisesRegex(ValueError, 'ownership'):
            terminate(client, p, instance_id)
        self.assertFalse(any(operation == 'terminate-instances' for _, operation, _ in client.calls))

    def test_disarmed_or_changed_watchdog_prevents_launch(self):
        p, client, receipt, budget = self.setup_launch()
        client.schedule_enabled = False
        with self.assertRaisesRegex(ValueError, 'schedule'):
            launch(client, p, budget, receipt, 1000)
        self.assertNotIn('launch#' + p.launch_token, client.records)
        with self.assertRaisesRegex(ValueError, 'preflight'):
            launch(client, replace(p, deadline_epoch=39999), budget, receipt, 1000)

    def test_stale_source_cannot_be_refreshed_by_fetching_it_today(self):
        advisor = self.advisor(1_000_000)
        advisor['source_modified_at'] = 1
        # Use a future trigger to reach the source-age check, rather than an
        # unrelated expired-schedule rejection.
        p = replace(plan(), deadline_epoch=1_010_000)
        receipt = preflight(FakeAWS(p), p, advisor, 1_000_000)
        self.assertFalse(receipt['allowed'])
        self.assertIn('source freshness', ' '.join(receipt['blockers']))

    def test_uncertain_request_is_recoverable_after_launch_admission_expires(self):
        p, client, receipt, budget = self.setup_launch()
        client.lose_launch_response = True
        with self.assertRaises(AwsError):
            launch(client, p, budget, receipt, 1000)
        with self.assertRaisesRegex(ValueError, 'fresh'):
            launch(client, p, budget, receipt, 5000)
        recovered = recover_launch(client, p)
        self.assertEqual(recovered['instance_id'], client.instance['InstanceId'])
        self.assertFalse(recovered['paid_launch_request_sent'])
        self.assertEqual(sum(operation == 'run-instances' and not request.get('DryRun') for _, operation, request in client.calls), 1)

    def test_aws_cli_json_and_errors_never_forward_raw_auth_diagnostics(self):
        response = SimpleNamespace(returncode=255, stdout=b'', stderr=b'An error occurred (DryRunOperation) when calling secret-diagnostic')
        captured = {}
        def invoke(argv, **kwargs):
            uri = argv[argv.index('--cli-input-json') + 1]
            captured['uri'] = uri
            captured['request'] = json.loads(Path(uri.removeprefix('file://')).read_text())
            return response
        with patch('subprocess.run', side_effect=invoke) as run:
            with self.assertRaises(AwsError) as caught:
                AWSCLI('us-east-2', executable='aws-native-test.exe').call('ec2', 'run-instances', {'DryRun': True})
        self.assertEqual(caught.exception.code, 'DryRunOperation')
        self.assertNotIn('secret-diagnostic', str(caught.exception))
        self.assertNotIn('shell', run.call_args.kwargs)
        environment = run.call_args.kwargs['env']
        self.assertNotIn('AWS_PROFILE', environment)
        self.assertNotIn('AWS_WEB_IDENTITY_TOKEN_FILE', environment)
        import os
        self.assertEqual(environment['AWS_SHARED_CREDENTIALS_FILE'], os.devnull)
        self.assertEqual(environment['AWS_CONFIG_FILE'], os.devnull)
        self.assertEqual(captured['request'], {'DryRun': True})
        self.assertFalse(Path(captured['uri'].removeprefix('file://')).exists())

    def test_non_idempotent_ssm_transport_forces_one_attempt_without_mutating_ambient(self):
        import os
        response = SimpleNamespace(returncode=0, stdout=b'{}', stderr=b'')
        with patch.dict(os.environ, {'AWS_MAX_ATTEMPTS': '9'}):
            with patch('subprocess.run', return_value=response) as invoke:
                AWSCLI('ap-southeast-2', executable='aws-native-test.exe').call(
                    'ssm', 'send-command', {'InstanceIds': ['i-1234567890abcdef0'],
                                             'DocumentName': 'AWS-RunShellScript'})
            self.assertEqual(invoke.call_count, 1)
            self.assertEqual(invoke.call_args.kwargs['env']['AWS_MAX_ATTEMPTS'], '1')
            self.assertEqual(os.environ['AWS_MAX_ATTEMPTS'], '9')
            self.assertEqual(invoke.call_args.kwargs['timeout'], 30)

    def test_immutable_evidence_upload_reconciles_lost_ack_without_overwrite(self):
        class Store:
            def __init__(self):
                self.objects = {}
                self.lose_ack = True

            def put_file(self, bucket, key, path, sha):
                if key in self.objects:
                    raise AwsError('PreconditionFailed', 's3api.put-object')
                checksum = base64.b64encode(bytes.fromhex(sha)).decode('ascii')
                self.objects[key] = {'ContentLength': path.stat().st_size,
                    'Metadata': {'sha256': sha}, 'ChecksumSHA256': checksum,
                    'ETag': '"one-immutable-object"', 'raw': path.read_bytes()}
                if self.lose_ack:
                    self.lose_ack = False
                    raise AwsError('ObservationTimeout', 's3api.put-object')
                return {'ChecksumSHA256': checksum}

            def call(self, service, operation, request):
                if (service, operation) == ('s3api', 'list-objects-v2'):
                    return {'Contents': [{'Key': key} for key in self.objects if key.startswith(request['Prefix'])]}
                if (service, operation) != ('s3api', 'head-object'):
                    raise AssertionError('unexpected storage call')
                return self.objects[request['Key']]

            def get_file(self, bucket, key, path, etag):
                item = self.objects[key]
                if item['ETag'] != etag:
                    raise AwsError('PreconditionFailed', 's3api.get-object')
                path.write_bytes(item['raw'])
                return {'ChecksumSHA256': item['ChecksumSHA256']}

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'event.json'
            path.write_bytes(b'{"seq":1}\n')
            store = Store()
            evidence = S3Evidence(store, plan(), Path(temporary))
            with self.assertRaises(AwsError):
                evidence.publish(path, 'campaign-a/game-one/event-1.json')
            ack = evidence.publish(path, 'campaign-a/game-one/event-1.json')
            self.assertTrue(ack['acknowledged'])
            self.assertTrue(ack['reused_existing'])
            self.assertEqual(len(store.objects), 1)
            self.assertEqual(evidence.list_keys('campaign-a/game-one'), ['campaign-a/game-one/event-1.json'])
            self.assertEqual(evidence.read_verified('campaign-a/game-one/event-1.json', expected_sha=ack['sha256']), b'{"seq":1}\n')
            self.assertEqual(evidence.read_verified('campaign-a/game-one/event-1.json',
                             max_bytes=128 * 1024 * 1024), b'{"seq":1}\n')
            with self.assertRaisesRegex(ValueError, 'bounded recovery'):
                evidence.read_verified('campaign-a/game-one/event-1.json',
                                       max_bytes=128 * 1024 * 1024 + 1)
            store.objects['campaign-a/game-one/event-1.json']['raw'] = b'corrupt bytes'
            with self.assertRaisesRegex(ValueError, 'preserved at'):
                evidence.read_verified('campaign-a/game-one/event-1.json')
            self.assertEqual(len(list((Path(temporary) / 'recovered').glob('*.unverified'))), 1)
            path.write_bytes(b'{"seq":2}\n')
            with self.assertRaisesRegex(ValueError, 'differs'):
                evidence.publish(path, 'campaign-a/game-one/event-1.json')
            with self.assertRaisesRegex(ValueError, 'prefix'):
                evidence.publish(path, 'other-campaign/event.json')


if __name__ == '__main__':
    unittest.main()
