"""Execute the deployed inline watchdog with fake AWS ports; never use AWS."""
import copy
from datetime import datetime, timezone
import io
import json
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

from aws_infrastructure import WATCHDOG_SOURCE, template


DEADLINE_TEXT = '2026-10-25T12:00:00'
DEADLINE = datetime.fromisoformat(DEADLINE_TEXT).replace(tzinfo=timezone.utc).timestamp()
CAMPAIGN = 'campaign-test'
ACCOUNT = '123456789012'
REGION = 'us-east-2'
NONCE = 'a' * 64
PROFILE = 'arn:aws:iam::123456789012:instance-profile/rove-test-profile'
IID = 'i-0123456789abcdef0'


def launch(token='launch-token-0001', requested_at=DEADLINE - 100, deadline=DEADLINE):
    return {'campaign_id': CAMPAIGN, 'account_id': ACCOUNT, 'region': REGION,
            'owner_nonce': NONCE, 'launch_token': token, 'requested_at': requested_at,
            'deadline_epoch': deadline, 'instance_type': 'm6a.48xlarge',
            'ami_id': 'ami-0123456789abcdef0', 'subnet_id': 'subnet-0123456789abcdef0',
            'instance_profile_arn': PROFILE, 'request_sha256': '1' * 64}


def row(value, prefix='launch#'):
    return {'campaign_id': {'S': CAMPAIGN},
            'record_id': {'S': prefix + value['launch_token']},
            'payload': {'S': json.dumps(value, sort_keys=True, separators=(',', ':'))}}


def instance(intent, instance_id=IID, state='running'):
    return {'InstanceId': instance_id, 'ClientToken': intent['launch_token'],
            'ImageId': intent['ami_id'], 'InstanceType': intent['instance_type'],
            'SubnetId': intent['subnet_id'], 'IamInstanceProfile': {'Arn': PROFILE},
            'LaunchTime': datetime.fromtimestamp(intent['requested_at'] + 1, timezone.utc),
            'State': {'Name': state}, 'Tags': [{'Key': 'RoveCampaign', 'Value': CAMPAIGN},
                                            {'Key': 'RoveOwner', 'Value': NONCE}]}


class Clock:
    def __init__(self, now=DEADLINE + 1):
        self.now = now
        self.tick = 0

    def time(self):
        return self.now + self.tick

    def monotonic(self):
        return self.tick

    def sleep(self, seconds):
        self.tick += seconds


class Dynamo:
    def __init__(self, records):
        self.records = records

    def query(self, **request):
        assert request['ConsistentRead'] is True
        return {'Items': [copy.deepcopy(value) for key, value in self.records.items()
                          if key.startswith('launch#')]}

    def get_item(self, **request):
        assert request['ConsistentRead'] is True
        record = self.records.get(request['Key']['record_id']['S'])
        return {'Item': copy.deepcopy(record)} if record else {}


class EC2:
    def __init__(self, items, *, settles=True):
        self.items = copy.deepcopy(items)
        self.terminated = []
        self.settles = settles
        self.describes = []

    def describe_instances(self, **request):
        self.describes.append(copy.deepcopy(request))
        if 'Filters' in request:
            assert request['Filters'][0]['Name'] == 'client-token'
            token = request['Filters'][0]['Values'][0]
            selected = [(owner, item) for owner, item in self.items if item['ClientToken'] == token]
        else:
            selected = [(owner, item) for owner, item in self.items if item['InstanceId'] in request['InstanceIds']]
            if self.settles:
                for _, item in selected:
                    if item['InstanceId'] in self.terminated:
                        item['State']['Name'] = 'terminated'
        return {'Reservations': [{'OwnerId': owner, 'Instances': [copy.deepcopy(item)]}
                                 for owner, item in selected]}

    def terminate_instances(self, **request):
        self.terminated.extend(request['InstanceIds'])
        return {'TerminatingInstances': [{'InstanceId': value,
                                         'CurrentState': {'Name': 'shutting-down'}}
                                        for value in request['InstanceIds']]}


def deployed(records, items, *, now=DEADLINE + 1, account=ACCOUNT, settles=True):
    """Compile and execute exactly the Lambda source embedded in the template."""
    ddb, ec2 = Dynamo(records), EC2(items, settles=settles)
    sdk = ModuleType('boto3')
    sts = SimpleNamespace(get_caller_identity=lambda: {'Account': account})
    sdk.client = lambda name, **kwargs: {'sts': sts, 'dynamodb': ddb, 'ec2': ec2}[name]
    core = ModuleType('botocore')
    core.__path__ = []
    config = ModuleType('botocore.config')
    config.Config = lambda **kwargs: kwargs
    namespace = {'__name__': 'deployed_deadline_fixture'}
    with patch.dict(sys.modules, {'boto3': sdk, 'botocore': core, 'botocore.config': config}):
        exec(compile(template()['Resources']['DeadlineFunction']['Properties']['Code']['ZipFile'],
                     '<deployed-deadline>', 'exec'), namespace)
    namespace['time'] = Clock(now)
    namespace['os'] = SimpleNamespace(environ={
        'CAMPAIGN_ID': CAMPAIGN, 'OWNER_NONCE': NONCE, 'EXPECTED_ACCOUNT': ACCOUNT,
        'EXPECTED_REGION': REGION, 'OWNERSHIP_TABLE': 'test-ownership',
        'INSTANCE_PROFILE_ARN': PROFILE, 'HARD_DEADLINE_UTC': DEADLINE_TEXT, 'AWS_REGION': REGION})
    event = {'campaign_id': CAMPAIGN, 'owner_nonce': NONCE, 'deadline_utc': DEADLINE_TEXT}
    return namespace, ec2, event


class DeadlineExecution(unittest.TestCase):
    def invoke(self, namespace, event):
        with redirect_stdout(io.StringIO()):
            return namespace['handler'](event, None)

    def test_lost_run_response_reconciles_exact_intent_and_observes_termination(self):
        intent = launch()
        ns, ec2, event = deployed({'launch#' + intent['launch_token']: row(intent)},
                                 [(ACCOUNT, instance(intent))])
        result = self.invoke(ns, event)
        self.assertEqual(ec2.terminated, [IID])
        self.assertEqual(result['terminated_instance_ids'], [IID])
        self.assertEqual(result['outcomes'][0]['state'], 'terminated')
        self.assertFalse(result['outcomes'][0]['bound'])
        self.assertTrue(any('InstanceIds' in request for request in ec2.describes))

    def test_bound_record_matches_immutable_intent(self):
        intent = launch()
        bound = {**intent, 'instance_id': IID}
        records = {'launch#' + intent['launch_token']: row(intent),
                   'owned#' + intent['launch_token']: row(bound, 'owned#')}
        ns, ec2, event = deployed(records, [(ACCOUNT, instance(intent))])
        result = self.invoke(ns, event)
        self.assertTrue(result['outcomes'][0]['bound'])
        self.assertEqual(ec2.terminated, [IID])

    def test_wrong_campaign_nonce_account_region_ami_profile_or_bound_id_cannot_terminate(self):
        for mutation in ('nonce', 'account', 'region', 'ami', 'profile', 'bound'):
            with self.subTest(mutation=mutation):
                intent = launch()
                actual = instance(intent)
                records = {'launch#' + intent['launch_token']: row(intent)}
                owner = ACCOUNT
                if mutation == 'nonce':
                    intent['owner_nonce'] = 'b' * 64
                    records['launch#' + intent['launch_token']] = row(intent)
                elif mutation == 'account':
                    owner = '999999999999'
                elif mutation == 'region':
                    intent['region'] = 'eu-west-1'
                    records['launch#' + intent['launch_token']] = row(intent)
                elif mutation == 'ami':
                    actual['ImageId'] = 'ami-11111111111111111'
                elif mutation == 'profile':
                    actual['IamInstanceProfile']['Arn'] = PROFILE + '-foreign'
                else:
                    records['owned#' + intent['launch_token']] = row(
                        {**intent, 'instance_id': 'i-11111111111111111'}, 'owned#')
                ns, ec2, event = deployed(records, [(owner, actual)])
                with self.assertRaises(ValueError):
                    self.invoke(ns, event)
                self.assertEqual(ec2.terminated, [])

    def test_matching_tags_without_client_token_are_not_ownership(self):
        intent = launch()
        actual = instance(intent)
        actual['ClientToken'] = 'not-the-recorded-token'
        ns, ec2, event = deployed({'launch#' + intent['launch_token']: row(intent)}, [(ACCOUNT, actual)])
        with self.assertRaisesRegex(RuntimeError, 'unresolved launch intents'):
            self.invoke(ns, event)
        self.assertEqual(ec2.terminated, [])

    def test_future_deadline_and_wrong_invocation_do_not_contact_ec2(self):
        intent = launch()
        for future, changed in ((True, False), (False, True)):
            ns, ec2, event = deployed({'launch#' + intent['launch_token']: row(intent)},
                                     [(ACCOUNT, instance(intent))], now=DEADLINE - 1 if future else DEADLINE + 1)
            if changed:
                event['owner_nonce'] = 'b' * 64
            with self.assertRaises(ValueError):
                self.invoke(ns, event)
            self.assertEqual(ec2.describes, [])
            self.assertEqual(ec2.terminated, [])

    def test_account_of_lambda_itself_must_match(self):
        ns, ec2, event = deployed({}, [], account='999999999999')
        with self.assertRaisesRegex(ValueError, 'Lambda account mismatch'):
            self.invoke(ns, event)
        self.assertEqual(ec2.describes, [])

    def test_request_success_is_not_physical_termination(self):
        intent = launch()
        ns, ec2, event = deployed({'launch#' + intent['launch_token']: row(intent)},
                                 [(ACCOUNT, instance(intent))], settles=False)
        with self.assertRaisesRegex(ValueError, 'physical termination not yet observed'):
            self.invoke(ns, event)
        self.assertEqual(ec2.terminated, [IID])

    def test_invisible_launch_raises_for_retry_then_late_visibility_is_settled(self):
        intent = launch()
        ns, ec2, event = deployed({'launch#' + intent['launch_token']: row(intent)}, [])
        with self.assertRaisesRegex(RuntimeError, 'unresolved launch intents'):
            self.invoke(ns, event)
        self.assertEqual(ec2.terminated, [])
        ec2.items.append((ACCOUNT, instance(intent)))
        result = self.invoke(ns, event)
        self.assertTrue(result['termination_observed'])
        self.assertEqual(ec2.terminated, [IID])

    def test_owned_allocation_after_deadline_is_still_cleaned(self):
        intent = launch()
        actual = instance(intent)
        actual['LaunchTime'] = datetime.fromtimestamp(DEADLINE + 5, timezone.utc)
        ns, ec2, event = deployed({'launch#' + intent['launch_token']: row(intent)},
                                 [(ACCOUNT, actual)], now=DEADLINE + 10)
        result = self.invoke(ns, event)
        self.assertEqual(ec2.terminated, [IID])
        self.assertEqual(result['terminated_instance_ids'], [IID])

    def test_optional_project_region_is_ownership_metadata_and_must_match_workload(self):
        for selected in (None, REGION, 'ap-southeast-2'):
            with self.subTest(project_region=selected):
                intent = launch()
                if selected is not None:
                    intent['project_region'] = selected
                ns, ec2, event = deployed({'launch#' + intent['launch_token']: row(intent)},
                                         [(ACCOUNT, instance(intent))])
                if selected not in (None, REGION):
                    with self.assertRaisesRegex(ValueError, 'ownership project region'):
                        self.invoke(ns, event)
                    self.assertEqual(ec2.terminated, [])
                else:
                    self.assertTrue(self.invoke(ns, event)['termination_observed'])
                    self.assertEqual(ec2.terminated, [IID])

    def test_old_unresolved_intent_does_not_prevent_current_owned_termination(self):
        old = launch('old-token-00000001', DEADLINE - 1000, DEADLINE - 500)
        current = launch()
        records = {'launch#' + old['launch_token']: row(old),
                   'launch#' + current['launch_token']: row(current)}
        ns, ec2, event = deployed(records, [(ACCOUNT, instance(current))])
        with self.assertRaisesRegex(RuntimeError, 'unresolved launch intents'):
            self.invoke(ns, event)
        self.assertEqual(ec2.terminated, [IID])

    def test_closed_old_lease_survives_history_expiry_and_different_current_deadline(self):
        old = launch('old-token-00000001', DEADLINE - 1000, DEADLINE - 500)
        bound = {**old, 'instance_id': 'i-11111111111111111'}
        closed = {**bound, 'terminal_state': 'terminated', 'observed_at': DEADLINE - 501,
                  'evidence': 'sha256:old-describe-result'}
        current = launch()
        records = {'launch#' + old['launch_token']: row(old),
                   'owned#' + old['launch_token']: row(bound, 'owned#'),
                   'closed#' + old['launch_token']: row(closed, 'closed#'),
                   'launch#' + current['launch_token']: row(current)}
        ns, ec2, event = deployed(records, [(ACCOUNT, instance(current))])
        result = self.invoke(ns, event)
        self.assertTrue(result['termination_observed'])
        self.assertEqual(ec2.terminated, [IID])
        self.assertEqual(len(result['terminated_instance_ids']), 2)

    def test_closed_record_without_terminal_evidence_cannot_hide_live_instance(self):
        intent = launch()
        closed = {**intent, 'instance_id': IID, 'terminal_state': 'stopped',
                  'observed_at': DEADLINE, 'evidence': 'a request is not termination'}
        records = {'launch#' + intent['launch_token']: row(intent),
                   'closed#' + intent['launch_token']: row(closed, 'closed#')}
        ns, ec2, event = deployed(records, [(ACCOUNT, instance(intent))])
        with self.assertRaisesRegex(ValueError, 'terminal observation'):
            self.invoke(ns, event)
        self.assertEqual(ec2.terminated, [])


class InfrastructureDefinition(unittest.TestCase):
    @staticmethod
    def region_rules_accept(value, stack_region, project_region=None):
        """Evaluate the emitted rule tree, not a copy of its region decision."""
        parameter = value['Parameters']['ProjectRegion']
        selected = parameter['Default'] if project_region is None else project_region
        if ('AllowedValues' in parameter and selected not in parameter['AllowedValues']
                or re.fullmatch(parameter['AllowedPattern'], selected) is None
                or len(selected) > parameter['MaxLength']):
            return False
        context = {'ProjectRegion': selected, 'AWS::Region': stack_region}

        def resolve(item):
            if not isinstance(item, dict):
                return item
            if set(item) == {'Ref'}:
                return context[item['Ref']]
            if set(item) == {'Fn::Equals'}:
                left, right = item['Fn::Equals']
                return resolve(left) == resolve(right)
            if set(item) == {'Fn::Or'}:
                return any(resolve(child) for child in item['Fn::Or'])
            raise AssertionError('unsupported rule expression: ' + repr(item))

        return all(resolve(assertion['Assert']) for rule in value['Rules'].values()
                   for assertion in rule['Assertions'])

    def test_explicit_project_region_rejects_other_stack_regions_and_parameter_override(self):
        value = template(project_region='ap-southeast-2')
        self.assertTrue(self.region_rules_accept(value, 'ap-southeast-2'))
        for wrong in ('us-east-1', 'us-east-2', 'ap-southeast-1'):
            with self.subTest(stack_region=wrong):
                self.assertFalse(self.region_rules_accept(value, wrong))
        # A generic blank default is useful, but cannot bypass a bound template.
        self.assertFalse(self.region_rules_accept(value, 'us-east-1', ''))
        self.assertFalse(self.region_rules_accept(value, 'us-east-1', 'us-east-1'))

    def test_generic_template_is_reusable_and_optional_parameter_still_guards_region(self):
        value = template()
        for region in ('us-east-1', 'ap-southeast-2', 'eu-west-1'):
            with self.subTest(stack_region=region):
                self.assertTrue(self.region_rules_accept(value, region))
        self.assertTrue(self.region_rules_accept(value, 'eu-west-1', 'eu-west-1'))
        self.assertFalse(self.region_rules_accept(value, 'us-east-1', 'eu-west-1'))
        for invalid in ('', 'AP-SOUTHEAST-2', ' ap-southeast-2', 'us-east-1\n',
                        'https://ap-southeast-2', True, [], 'a' * 64):
            with self.subTest(project_region=invalid):
                with self.assertRaisesRegex(ValueError, 'explicit AWS region'):
                    template(project_region=invalid)

    def test_paid_account_plan_is_explicit_pre_resource_gate_and_readonly_controller_action(self):
        value = template(project_region='ap-southeast-2')
        gate = value['Metadata']['Rove4k::DeploymentPrerequisites']['AccountPlan']
        self.assertEqual(gate['RequiredResponse']['accountPlanType'], 'PAID')
        self.assertIn('accountId', gate['RequiredResponse'])
        self.assertIn('CreateStack', gate['Before'])
        self.assertIn('UpdateStack', gate['Before'])
        self.assertIn('CloudFormation does not query', gate['Enforcement'])
        # Billing plan type and status are different API fields; a credit-status
        # expiration must not silently become a made-up PAID-account rejection.
        self.assertIn('accountPlanStatus', gate['RecordResponseFields'])
        self.assertEqual(set(gate['KnownStatusValues']), {'NOT_STARTED', 'ACTIVE', 'EXPIRED'})
        for name in ('ControllerRole', 'InstanceRole', 'DeadlineRole', 'SchedulerRole'):
            statements = value['Resources'][name]['Properties']['Policies'][0]['PolicyDocument']['Statement']
            freetier = [item for item in statements if any(action.startswith('freetier:')
                        for action in (item['Action'] if isinstance(item['Action'], list) else [item['Action']]))]
            if name == 'ControllerRole':
                self.assertEqual(freetier, [{'Effect': 'Allow', 'Action': 'freetier:GetAccountPlanState', 'Resource': '*'}])
            else:
                self.assertEqual(freetier, [])

    def test_one_off_deadline_and_no_paid_instance_is_created(self):
        value = template()
        resources = value['Resources']
        self.assertNotIn('AWS::EC2::Instance', {row['Type'] for row in resources.values()})
        schedule = resources['DeadlineSchedule']['Properties']
        self.assertEqual(schedule['ScheduleExpression'], {'Fn::Sub': 'at(${HardDeadlineUtc})'})
        self.assertEqual(schedule['ScheduleExpressionTimezone'], 'UTC')
        self.assertEqual(schedule['FlexibleTimeWindow'], {'Mode': 'OFF'})
        self.assertNotIn('ActionAfterCompletion', schedule)
        self.assertEqual(schedule['Target']['RetryPolicy']['MaximumEventAgeInSeconds'], 120)
        self.assertEqual(resources['DeadlineFunction']['Properties']['Code']['ZipFile'], WATCHDOG_SOURCE)

    def test_retention_and_github_trust_do_not_reuse_npm_identity(self):
        resources = template()['Resources']
        self.assertEqual(resources['ArtifactBucket']['DeletionPolicy'], 'Retain')
        self.assertEqual(resources['ArtifactBucket']['Properties']['LifecycleConfiguration']['Rules'][0]['ExpirationInDays'], 30)
        self.assertEqual(resources['DeadlineLogGroup']['Properties']['RetentionInDays'], 30)
        self.assertTrue(resources['OwnershipTable']['Properties']['TimeToLiveSpecification']['Enabled'])
        trust = resources['ControllerRole']['Properties']['AssumeRolePolicyDocument']['Statement'][0]
        self.assertEqual(trust['Condition']['StringEquals']['token.actions.githubusercontent.com:sub'],
                         'repo:daejunnom/Rove4k:environment:aws-evaluation')

    def test_controller_oidc_session_duration_is_six_hours(self):
        for region in (None, 'ap-southeast-2'):
            with self.subTest(project_region=region):
                resources = template(project_region=region)['Resources']
                duration = resources['ControllerRole']['Properties']['MaxSessionDuration']
                self.assertIs(type(duration), int)
                self.assertEqual(duration, 21600)
                for name in ('InstanceRole', 'DeadlineRole', 'SchedulerRole'):
                    self.assertNotIn('MaxSessionDuration', resources[name]['Properties'])

    def test_seed_bucket_versions_and_noncurrent_expiry_preserve_existing_protections(self):
        bucket = template()['Resources']['ArtifactBucket']
        props = bucket['Properties']
        self.assertEqual(props['VersioningConfiguration'], {'Status': 'Enabled'})
        rule = props['LifecycleConfiguration']['Rules'][0]
        self.assertEqual(rule['Status'], 'Enabled')
        self.assertEqual(rule['ExpirationInDays'], 30)
        self.assertEqual(rule['NoncurrentVersionExpiration'], {'NoncurrentDays': 30})
        # No retained-version count floor may keep old seed payloads indefinitely.
        self.assertNotIn('NewerNoncurrentVersions', rule['NoncurrentVersionExpiration'])
        self.assertEqual(rule['AbortIncompleteMultipartUpload'], {'DaysAfterInitiation': 1})
        self.assertEqual(bucket['DeletionPolicy'], 'Retain')
        self.assertEqual(bucket['UpdateReplacePolicy'], 'Retain')
        self.assertEqual(props['BucketEncryption']['ServerSideEncryptionConfiguration'],
                         [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}])
        self.assertTrue(all(props['PublicAccessBlockConfiguration'].values()))
        self.assertEqual(props['OwnershipControls'], {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]})

    def test_controller_limits_instance_type_market_and_tags_without_invalid_ami_conditions(self):
        policies = template()['Resources']['ControllerRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        runs = [row for row in policies if row['Action'] == 'ec2:RunInstances']
        self.assertEqual(len(runs), 2)
        scoped = [row for row in runs if 'ec2:InstanceType' in row.get('Condition', {}).get('StringEquals', {})]
        self.assertEqual(len(scoped), 1)
        self.assertIn(':instance/*', scoped[0]['Resource']['Fn::Sub'])
        self.assertEqual(scoped[0]['Condition']['StringEquals']['ec2:InstanceType'], 'm6a.48xlarge')
        self.assertEqual(scoped[0]['Condition']['StringEquals']['ec2:InstanceMarketType'], 'spot')
        self.assertIn('aws:RequestTag/RoveOwner', scoped[0]['Condition']['StringEquals'])

    def test_immutable_version_reads_stay_on_campaign_object_prefix(self):
        resources = template()['Resources']
        for name in ('InstanceRole', 'ControllerRole', 'DeadlineRole', 'SchedulerRole'):
            with self.subTest(role=name):
                statements = resources[name]['Properties']['Policies'][0]['PolicyDocument']['Statement']
                versions = [item for item in statements if 's3:GetObjectVersion' in
                            (item['Action'] if isinstance(item['Action'], list) else [item['Action']])]
                if name in ('InstanceRole', 'ControllerRole'):
                    self.assertEqual(len(versions), 1)
                    self.assertEqual(versions[0]['Resource'], {'Fn::Sub': '${ArtifactBucket.Arn}/${CampaignId}/*'})
                    self.assertIn('s3:GetObject', versions[0]['Action'])
                else:
                    self.assertEqual(versions, [])

    def test_controller_deployment_reads_are_exact_stack_and_function_only(self):
        resources = template()['Resources']
        expected = {'cloudformation:GetTemplate': {'Ref': 'AWS::StackId'},
                    'lambda:GetFunctionConfiguration': {'Fn::GetAtt': ['DeadlineFunction', 'Arn']}}
        for name in ('ControllerRole', 'InstanceRole', 'DeadlineRole', 'SchedulerRole'):
            statements = resources[name]['Properties']['Policies'][0]['PolicyDocument']['Statement']
            for action, resource in expected.items():
                with self.subTest(role=name, action=action):
                    matches = [item for item in statements if action in
                               (item['Action'] if isinstance(item['Action'], list) else [item['Action']])]
                    if name == 'ControllerRole':
                        self.assertEqual(matches, [{'Effect': 'Allow', 'Action': action, 'Resource': resource,
                            'Condition': {'StringEquals': {'aws:RequestedRegion': {'Ref': 'AWS::Region'}}}}])
                    else:
                        self.assertEqual(matches, [])

    def test_controller_ssm_readiness_permission_is_regional_read_only(self):
        resources = template()['Resources']
        for name in ('ControllerRole', 'InstanceRole', 'DeadlineRole', 'SchedulerRole'):
            with self.subTest(role=name):
                statements = resources[name]['Properties']['Policies'][0]['PolicyDocument']['Statement']
                matches = [item for item in statements if 'ssm:DescribeInstanceInformation' in
                           (item['Action'] if isinstance(item['Action'], list) else [item['Action']])]
                if name == 'ControllerRole':
                    self.assertEqual(matches, [{'Effect': 'Allow', 'Action': 'ssm:DescribeInstanceInformation',
                        'Resource': '*', 'Condition': {'StringEquals': {'aws:RequestedRegion': {'Ref': 'AWS::Region'}}}}])
                else:
                    self.assertEqual(matches, [])

    def test_watchdog_cannot_launch_or_rewrite_ownership(self):
        statements = template()['Resources']['DeadlineRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        actions = {action for row in statements for action in
                   (row['Action'] if isinstance(row['Action'], list) else [row['Action']])}
        self.assertNotIn('ec2:RunInstances', actions)
        self.assertNotIn('dynamodb:PutItem', actions)
        self.assertNotIn('dynamodb:UpdateItem', actions)
        self.assertIn('ec2:TerminateInstances', actions)
        trust = template()['Resources']['SchedulerRole']['Properties']['AssumeRolePolicyDocument']['Statement'][0]
        self.assertIn(':schedule-group/default', trust['Condition']['ArnEquals']['aws:SourceArn']['Fn::Sub'])

    def test_host_runner_can_read_its_lease_without_controller_mutation_rights(self):
        resources = template()['Resources']
        statements = resources['InstanceRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        actions = {action for item in statements for action in
                   (item['Action'] if isinstance(item['Action'], list) else [item['Action']])}
        self.assertTrue({'ec2:DescribeInstances', 'dynamodb:GetItem', 'scheduler:GetSchedule',
                         'cloudformation:DescribeStacks', 'iam:GetInstanceProfile'} <= actions)
        self.assertFalse({'ec2:RunInstances', 'ec2:TerminateInstances', 'dynamodb:PutItem',
                          'dynamodb:UpdateItem', 'scheduler:DeleteSchedule',
                          'cloudformation:DeleteStack', 'iam:PassRole'} & actions)
        inspect = next(item for item in statements if item['Action'] == 'iam:GetInstanceProfile')
        self.assertEqual(inspect['Resource'], {'Fn::Sub':
            'arn:${AWS::Partition}:iam::${AWS::AccountId}:instance-profile/rove4k-${CampaignId}-instance-profile'})
        self.assertEqual(resources['InstanceProfile']['Properties']['InstanceProfileName'],
                         {'Fn::Sub': 'rove4k-${CampaignId}-instance-profile'})

    def test_cloudformation_references_exist_and_no_resource_cycle(self):
        value = template()
        names = set(value['Resources'])
        known = names | set(value['Parameters'])
        graph = {}

        def refs(value):
            result = set()
            if isinstance(value, dict):
                if 'Ref' in value:
                    result.add(value['Ref'])
                if 'Fn::GetAtt' in value:
                    result.add(value['Fn::GetAtt'][0])
                if isinstance(value.get('Fn::Sub'), str):
                    result.update(re.findall(r'\$\{([A-Za-z][A-Za-z0-9]*)[.}]', value['Fn::Sub']))
                for item in value.values():
                    result.update(refs(item))
            elif isinstance(value, list):
                for item in value:
                    result.update(refs(item))
            return {item for item in result if not item.startswith('AWS::')}

        for name, item in value['Resources'].items():
            dependencies = refs(item) | set(item.get('DependsOn', []))
            self.assertFalse(dependencies - known, (name, dependencies - known))
            graph[name] = dependencies & names
        ready = set()
        while len(ready) < len(graph):
            next_nodes = {name for name, deps in graph.items() if deps <= ready}
            self.assertTrue(next_nodes - ready, 'CloudFormation resource cycle')
            ready |= next_nodes


if __name__ == '__main__':
    unittest.main()
