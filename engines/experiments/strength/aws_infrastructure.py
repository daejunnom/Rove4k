"""Reviewable, campaign-scoped CloudFormation and independent deadline worker.

This module only constructs source data. It never contacts AWS. The caller
deploys and verifies the one-time watchdog before EC2 RunInstances. Archive
resources are retained on stack removal and have 30-day retention policies;
their later explicit cleanup requires a verified local archive.

The deployment caller must verify the selected account-readiness contract
before creating or updating this stack. CloudFormation cannot perform those
observations itself; the prerequisite metadata does not claim to do so.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import types

sys.dont_write_bytecode = True


WATCHDOG_SOURCE = '''"""Terminate only instances proven by immutable launch intents, never tags alone."""
import json
import math
import os
import re
import time
from datetime import datetime, timezone

import boto3
from botocore.config import Config


def require(value, message):
    if not value:
        raise ValueError(message)


def epoch(value):
    require(not isinstance(value, bool) and isinstance(value, (float, int))
            and math.isfinite(value) and value >= 0, 'invalid epoch')
    return float(value)


def decode(row):
    require(isinstance(row, dict) and isinstance(row.get('payload', {}).get('S'), str),
            'ownership row has no canonical payload')
    value = json.loads(row['payload']['S'])
    require(isinstance(value, dict), 'ownership payload is not an object')
    return value


def rows(client, table, campaign):
    request = {'TableName': table,
               'KeyConditionExpression': 'campaign_id = :c AND begins_with(record_id, :p)',
               'ExpressionAttributeValues': {':c': {'S': campaign}, ':p': {'S': 'launch#'}},
               'ConsistentRead': True, 'Limit': 100}
    result = []
    for _ in range(100):
        response = client.query(**request)
        result.extend(response.get('Items', []))
        key = response.get('LastEvaluatedKey')
        if not key:
            return result
        request['ExclusiveStartKey'] = key
    raise ValueError('ownership query exceeded its finite page bound')


def intent(row, campaign, account, region, nonce, profile):
    value = decode(row)
    require(row.get('campaign_id') == {'S': campaign}, 'ownership partition mismatch')
    token = value.get('launch_token', '')
    require(isinstance(token, str) and re.fullmatch(r'[A-Za-z0-9_-]{8,64}', token),
            'invalid immutable launch token')
    require(row.get('record_id') == {'S': 'launch#' + token}, 'ownership sort key mismatch')
    expected = {'campaign_id': campaign, 'account_id': account, 'region': region,
                'owner_nonce': nonce, 'instance_type': 'm6a.48xlarge',
                'instance_profile_arn': profile}
    require(all(value.get(key) == item for key, item in expected.items()),
            'ownership intent does not match this deployed campaign')
    if 'project_region' in value:
        require(value['project_region'] == region, 'ownership project region differs from the workload region')
    require(re.fullmatch(r'ami-[0-9a-f]{8,17}', value.get('ami_id', '')) is not None,
            'invalid intent AMI')
    require(re.fullmatch(r'subnet-[0-9a-f]{8,17}', value.get('subnet_id', '')) is not None,
            'invalid intent subnet')
    require(re.fullmatch(r'[0-9a-f]{64}', value.get('request_sha256', '')) is not None,
            'missing request identity')
    start, end = epoch(value.get('requested_at')), epoch(value.get('deadline_epoch'))
    require(0 < end - start <= 43200, 'intent exceeds the accepted instance duration')
    return value


def instances(client, token):
    request = {'Filters': [{'Name': 'client-token', 'Values': [token]}]}
    result = []
    for _ in range(100):
        response = client.describe_instances(**request)
        for reservation in response.get('Reservations', []):
            for item in reservation.get('Instances', []):
                result.append((reservation.get('OwnerId'), item))
        token = response.get('NextToken')
        if not token:
            return result
        request['NextToken'] = token
    raise ValueError('instance query exceeded its finite page bound')


def validate_instance(owner, item, launch, bound, now):
    tags = item.get('Tags', [])
    tag_map = {tag['Key']: tag['Value'] for tag in tags}
    require(len(tag_map) == len(tags), 'ambiguous instance tags')
    expected = {'ClientToken': launch['launch_token'], 'ImageId': launch['ami_id'],
                'InstanceType': launch['instance_type'], 'SubnetId': launch['subnet_id']}
    require(owner == launch['account_id'] and all(item.get(key) == val for key, val in expected.items()),
            'EC2 identity differs from the immutable launch request')
    require(item.get('IamInstanceProfile', {}).get('Arn') == launch['instance_profile_arn'],
            'EC2 instance profile differs from the immutable request')
    require(tag_map.get('RoveCampaign') == launch['campaign_id']
            and tag_map.get('RoveOwner') == launch['owner_nonce'], 'EC2 ownership tags differ')
    instance_id = item.get('InstanceId', '')
    require(re.fullmatch(r'i-[0-9a-f]{8,17}', instance_id) is not None, 'invalid instance identity')
    if bound is not None:
        require({key: value for key, value in bound.items() if key != 'instance_id'} == launch,
                'bound record changed the immutable intent')
        require(bound.get('instance_id') == instance_id, 'bound instance identity mismatch')
    launched = item.get('LaunchTime')
    require(isinstance(launched, datetime) and launched.tzinfo is not None, 'missing AWS launch timestamp')
    stamp = launched.timestamp()
    # EC2 can allocate after an earlier, authorized RunInstances request lost
    # its response or took longer than the controller deadline. It is still
    # our exact request and must be stopped, not rejected as a foreign host.
    require(launch['requested_at'] - 2 <= stamp <= now + 2,
            'AWS launch time precedes the authorized request or is in the future')
    require(item.get('State', {}).get('Name') in
            ('pending', 'running', 'stopping', 'stopped', 'shutting-down', 'terminated'),
            'unknown EC2 physical state')
    return instance_id


def closed_record(row, launch, bound, now):
    value = decode(row)
    require(row.get('campaign_id') == {'S': launch['campaign_id']}
            and row.get('record_id') == {'S': 'closed#' + launch['launch_token']},
            'closed ownership key mismatch')
    extra = {'instance_id', 'terminal_state', 'observed_at', 'evidence'}
    require(set(value) == set(launch) | extra
            and {key: value[key] for key in launch} == launch,
            'closed record changed the immutable intent')
    require(value['terminal_state'] == 'terminated' and isinstance(value['evidence'], str)
            and 0 < len(value['evidence']) <= 4096, 'closed record lacks a terminal observation')
    require(re.fullmatch(r'i-[0-9a-f]{8,17}', value['instance_id']) is not None,
            'closed record has an invalid instance identity')
    require(launch['requested_at'] <= epoch(value['observed_at']) <= now + 2,
            'closed observation time is invalid')
    if bound is not None:
        require({key: item for key, item in bound.items() if key != 'instance_id'} == launch
                and bound.get('instance_id') == value['instance_id'],
                'closed and bound instance identities differ')
    return value


def handler(event, context):
    campaign, nonce = os.environ['CAMPAIGN_ID'], os.environ['OWNER_NONCE']
    account, region = os.environ['EXPECTED_ACCOUNT'], os.environ['EXPECTED_REGION']
    table, profile = os.environ['OWNERSHIP_TABLE'], os.environ['INSTANCE_PROFILE_ARN']
    deadline_text = os.environ['HARD_DEADLINE_UTC']
    deadline = datetime.strptime(deadline_text, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
    now = time.time()
    require(isinstance(event, dict) and event.get('campaign_id') == campaign
            and event.get('owner_nonce') == nonce and event.get('deadline_utc') == deadline_text,
            'deadline invocation does not match this deployed campaign')
    require(now >= deadline, 'refuse termination before the trusted deadline')
    require(os.environ.get('AWS_REGION') == region, 'Lambda region mismatch')
    config = Config(connect_timeout=3, read_timeout=5, retries={'max_attempts': 2})
    sts = boto3.client('sts', region_name=region, config=config)
    require(sts.get_caller_identity()['Account'] == account, 'Lambda account mismatch')
    ddb = boto3.client('dynamodb', region_name=region, config=config)
    ec2 = boto3.client('ec2', region_name=region, config=config)
    launches = [intent(row, campaign, account, region, nonce, profile)
                for row in rows(ddb, table, campaign)]
    # Validate all metadata and physical identities before the first mutation.
    outcomes, pending, unresolved = [], [], []
    for launch in launches:
        response = ddb.get_item(TableName=table, ConsistentRead=True,
                                Key={'campaign_id': {'S': campaign},
                                     'record_id': {'S': 'owned#' + launch['launch_token']}})
        bound_row = response.get('Item')
        if bound_row:
            require(bound_row.get('campaign_id') == {'S': campaign}
                    and bound_row.get('record_id') == {'S': 'owned#' + launch['launch_token']},
                    'bound ownership key mismatch')
        bound = decode(bound_row) if bound_row else None
        closure = ddb.get_item(TableName=table, ConsistentRead=True,
                               Key={'campaign_id': {'S': campaign},
                                    'record_id': {'S': 'closed#' + launch['launch_token']}}).get('Item')
        if closure:
            closed = closed_record(closure, launch, bound, now)
            outcomes.append({'launch_token': launch['launch_token'], 'instance_id': closed['instance_id'],
                             'state': 'terminated', 'bound': bound is not None,
                             'observation_source': 'immutable-closed-record',
                             'observed_at': closed['observed_at']})
            continue
        matches = instances(ec2, launch['launch_token'])
        require(len(matches) <= 1, 'one-instance launch intent matched multiple EC2 instances')
        if not matches:
            outcomes.append({'launch_token': launch['launch_token'], 'state': 'absent_at_observation',
                             'bound': bound is not None})
            unresolved.append(launch['launch_token'])
            continue
        owner, item = matches[0]
        instance_id = validate_instance(owner, item, launch, bound, now)
        state = item['State']['Name']
        outcomes.append({'launch_token': launch['launch_token'], 'instance_id': instance_id,
                         'state': state, 'bound': bound is not None})
        if state != 'terminated':
            pending.append(instance_id)
    pending = sorted(set(pending))
    requested = list(pending)
    if pending:
        ec2.terminate_instances(InstanceIds=pending)
        stop = time.monotonic() + 40
        while pending and time.monotonic() < stop:
            observed = ec2.describe_instances(InstanceIds=pending)
            states = {item['InstanceId']: item.get('State', {}).get('Name')
                      for row in observed.get('Reservations', []) for item in row.get('Instances', [])}
            require(set(states) == set(pending), 'termination observation omitted an owned instance')
            pending = [instance_id for instance_id in pending if states[instance_id] != 'terminated']
            if pending:
                time.sleep(1)
        require(not pending, 'termination requested but physical termination not yet observed')
    for outcome in outcomes:
        if outcome.get('instance_id') in requested:
            outcome['observed_state_before'] = outcome['state']
            outcome['state'] = 'terminated'
    result = {'campaign_id': campaign, 'deadline_epoch': deadline, 'observed_at': time.time(),
              'outcomes': outcomes, 'termination_requested_ids': requested,
              'terminated_instance_ids': sorted(row['instance_id'] for row in outcomes
                                                if row['state'] == 'terminated'),
              'unresolved_launch_tokens': unresolved, 'termination_observed': not unresolved}
    print(json.dumps(result, sort_keys=True))
    if unresolved:
        # A RunInstances response can be lost or EC2 visibility delayed. Retry
        # this one-time invocation after settling other proven owned resources.
        raise RuntimeError('unresolved launch intents remain at the deadline: ' + ','.join(unresolved))
    return result
'''


def sub(value):
    return {'Fn::Sub': value}


def ref(name):
    return {'Ref': name}


def arn(name):
    return {'Fn::GetAtt': [name, 'Arn']}


def policy(statements):
    return {'Version': '2012-10-17', 'Statement': statements}


def allow(actions, resources, condition=None):
    row = {'Effect': 'Allow', 'Action': actions, 'Resource': resources}
    if condition:
        row['Condition'] = condition
    return row


def readiness_type():
    """Load the approved sibling factory without using cwd or sys.path."""
    directory = Path(__file__).resolve().parent
    package_name = __package__ or 'rove4k_cloud_strength'
    package = sys.modules.get(package_name)
    if package is None:
        package = types.ModuleType(package_name)
        package.__path__ = [str(directory)]
        sys.modules[package_name] = package
    if list(getattr(package, '__path__', ())) != [str(directory)]:
        raise ValueError('infrastructure sibling package belongs to another source tree')
    module = importlib.import_module(package_name + '.aws')
    if Path(module.__file__).resolve() != directory / 'aws.py':
        raise ValueError('infrastructure readiness factory belongs to another source tree')
    return module.AdvancedMemberProjectReadiness


def template(project_region=None, account_readiness=None):
    """Construct source only; optionally bind this deployment to its project region.

    The default remains reusable. An explicit region pins the parameter and
    CloudFormation Rules reject a stack in any other region before resources
    are created. A service's global configuration or billing endpoint does not
    change the workload region.
    """
    region_pattern = r'[a-z][a-z0-9]*(?:-[a-z0-9]+)+-[0-9]+'
    if project_region is not None and (not isinstance(project_region, str)
            or len(project_region) > 63 or re.fullmatch(region_pattern, project_region) is None):
        raise ValueError('project_region must be an explicit AWS region name or None')
    readiness = (None if account_readiness is None else
                 readiness_type().from_dict(account_readiness).as_dict())
    if readiness is not None and project_region != 'ap-southeast-2':
        raise ValueError('configured Advanced project requires explicit ap-southeast-2')
    region_parameter = {'Type': 'String', 'Default': project_region or '',
        'AllowedPattern': '^$|' + region_pattern, 'MaxLength': 63,
        'Description': 'Optional project workload region; when set it must equal the stack region. No region fallback.'}
    if project_region is not None:
        region_parameter['AllowedValues'] = [project_region]
    campaign_tags = [{'Key': 'RoveCampaign', 'Value': ref('CampaignId')},
                     {'Key': 'RoveOwner', 'Value': ref('OwnerNonce')}]
    owned = {'StringEquals': {'ec2:ResourceTag/RoveCampaign': ref('CampaignId'),
                              'ec2:ResourceTag/RoveOwner': ref('OwnerNonce')}}
    instance_arn = sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:instance/*')
    schedule_arn = sub('arn:${AWS::Partition}:scheduler:${AWS::Region}:${AWS::AccountId}:schedule/default/rove4k-${CampaignId}-deadline')
    log_arn = sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/rove4k-${CampaignId}-deadline:*')
    prefix = sub('${ArtifactBucket.Arn}/${CampaignId}/*')
    scoped_keys = {'ForAllValues:StringEquals': {'dynamodb:LeadingKeys': [ref('CampaignId')]}}
    resources = {
        'ArtifactBucket': {
            'Type': 'AWS::S3::Bucket', 'DeletionPolicy': 'Retain', 'UpdateReplacePolicy': 'Retain',
            'Properties': {
                'BucketEncryption': {'ServerSideEncryptionConfiguration': [
                    {'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]},
                'PublicAccessBlockConfiguration': {key: True for key in (
                    'BlockPublicAcls', 'BlockPublicPolicy', 'IgnorePublicAcls', 'RestrictPublicBuckets')},
                'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]},
                'VersioningConfiguration': {'Status': 'Enabled'},
                'LifecycleConfiguration': {'Rules': [{'Id': 'campaign-evidence-30-days',
                    'Status': 'Enabled', 'ExpirationInDays': 30,
                    # This is age since becoming noncurrent, not creation age.
                    'NoncurrentVersionExpiration': {'NoncurrentDays': 30},
                    'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 1}}]},
                'Tags': campaign_tags}},
        'OwnershipTable': {
            'Type': 'AWS::DynamoDB::Table', 'DeletionPolicy': 'Retain', 'UpdateReplacePolicy': 'Retain',
            'Properties': {'BillingMode': 'PAY_PER_REQUEST',
                'AttributeDefinitions': [{'AttributeName': key, 'AttributeType': 'S'}
                                         for key in ('campaign_id', 'record_id')],
                'KeySchema': [{'AttributeName': 'campaign_id', 'KeyType': 'HASH'},
                              {'AttributeName': 'record_id', 'KeyType': 'RANGE'}],
                'TimeToLiveSpecification': {'AttributeName': 'expires_at', 'Enabled': True},
                'SSESpecification': {'SSEEnabled': True}, 'Tags': campaign_tags}},
        'ArtifactBucketPolicy': {'Type': 'AWS::S3::BucketPolicy', 'Properties': {
            'Bucket': ref('ArtifactBucket'), 'PolicyDocument': policy([{
                'Effect': 'Deny', 'Principal': '*', 'Action': 's3:*',
                'Resource': [arn('ArtifactBucket'), sub('${ArtifactBucket.Arn}/*')],
                'Condition': {'Bool': {'aws:SecureTransport': 'false'}}}])}},
        'SecurityGroup': {'Type': 'AWS::EC2::SecurityGroup', 'Properties': {
            'GroupDescription': 'Rove4k campaign outbound SSM and artifact access; no ingress',
            'VpcId': ref('VpcId'), 'SecurityGroupIngress': [], 'Tags': campaign_tags}},
        'InstanceRole': {'Type': 'AWS::IAM::Role', 'Properties': {
            'AssumeRolePolicyDocument': policy([{'Effect': 'Allow', 'Principal': {'Service': 'ec2.amazonaws.com'},
                                                'Action': 'sts:AssumeRole'}]),
            'ManagedPolicyArns': [sub('arn:${AWS::Partition}:iam::aws:policy/AmazonSSMManagedInstanceCore')],
            'Policies': [{'PolicyName': 'campaign-artifacts', 'PolicyDocument': policy([
                # Explicit VersionId seed reads require GetObjectVersion on
                # the same campaign object prefix, not bucket-wide access.
                allow(['s3:GetObject', 's3:GetObjectVersion', 's3:PutObject', 's3:AbortMultipartUpload'], prefix),
                allow('s3:ListBucket', arn('ArtifactBucket'),
                      {'StringLike': {'s3:prefix': [sub('${CampaignId}/*')]}}),
                # The on-host runner verifies its immutable lease and safety
                # cutoff using the instance role, not the GitHub controller.
                allow('ec2:DescribeInstances', '*', {'StringEquals': {'aws:RequestedRegion': ref('AWS::Region')}}),
                allow('dynamodb:GetItem', arn('OwnershipTable'), scoped_keys),
                allow('scheduler:GetSchedule', schedule_arn),
                allow('cloudformation:DescribeStacks', ref('AWS::StackId')),
                allow('iam:GetInstanceProfile', sub('arn:${AWS::Partition}:iam::${AWS::AccountId}:instance-profile/rove4k-${CampaignId}-instance-profile'))])}],
            'Tags': campaign_tags}},
        'InstanceProfile': {'Type': 'AWS::IAM::InstanceProfile',
                            'Properties': {
                                'InstanceProfileName': sub('rove4k-${CampaignId}-instance-profile'),
                                'Roles': [ref('InstanceRole')]}},
        'DeadlineRole': {'Type': 'AWS::IAM::Role', 'Properties': {
            'AssumeRolePolicyDocument': policy([{'Effect': 'Allow', 'Principal': {'Service': 'lambda.amazonaws.com'},
                                                'Action': 'sts:AssumeRole'}]),
            'Policies': [{'PolicyName': 'observe-and-terminate-owned-campaign', 'PolicyDocument': policy([
                allow(['dynamodb:Query', 'dynamodb:GetItem'], arn('OwnershipTable'), scoped_keys),
                allow('ec2:DescribeInstances', '*', {'StringEquals': {'aws:RequestedRegion': ref('AWS::Region')}}),
                allow('ec2:TerminateInstances', instance_arn, owned),
                allow(['logs:CreateLogStream', 'logs:PutLogEvents'], log_arn)])}],
            'Tags': campaign_tags}},
        'DeadlineFunction': {'Type': 'AWS::Lambda::Function', 'Properties': {
            'FunctionName': sub('rove4k-${CampaignId}-deadline'),
            'Runtime': 'python3.12', 'Handler': 'index.handler', 'Timeout': 60, 'MemorySize': 128,
            'Role': arn('DeadlineRole'), 'Code': {'ZipFile': WATCHDOG_SOURCE},
            'Environment': {'Variables': {'CAMPAIGN_ID': ref('CampaignId'), 'OWNER_NONCE': ref('OwnerNonce'),
                'EXPECTED_ACCOUNT': ref('AWS::AccountId'), 'EXPECTED_REGION': ref('AWS::Region'),
                'OWNERSHIP_TABLE': ref('OwnershipTable'), 'INSTANCE_PROFILE_ARN': arn('InstanceProfile'),
                'HARD_DEADLINE_UTC': ref('HardDeadlineUtc')}}, 'Tags': campaign_tags}},
        'DeadlineLogGroup': {'Type': 'AWS::Logs::LogGroup', 'DeletionPolicy': 'Retain',
            'UpdateReplacePolicy': 'Retain', 'Properties': {
                'LogGroupName': sub('/aws/lambda/rove4k-${CampaignId}-deadline'),
                'RetentionInDays': 30, 'Tags': campaign_tags}},
        'SchedulerRole': {'Type': 'AWS::IAM::Role', 'Properties': {
            'AssumeRolePolicyDocument': policy([{'Effect': 'Allow', 'Principal': {'Service': 'scheduler.amazonaws.com'},
                'Action': 'sts:AssumeRole', 'Condition': {
                    'StringEquals': {'aws:SourceAccount': ref('AWS::AccountId')},
                    'ArnEquals': {'aws:SourceArn': sub('arn:${AWS::Partition}:scheduler:${AWS::Region}:${AWS::AccountId}:schedule-group/default')}}}]),
            'Policies': [{'PolicyName': 'invoke-only-this-deadline', 'PolicyDocument': policy([
                allow('lambda:InvokeFunction', arn('DeadlineFunction'))])}], 'Tags': campaign_tags}},
        'DeadlineSchedule': {'Type': 'AWS::Scheduler::Schedule', 'DependsOn': ['DeadlineLogGroup'],
            'Properties': {'Name': sub('rove4k-${CampaignId}-deadline'), 'GroupName': 'default',
                'Description': 'One-time campaign cost safety; not a recurring job',
                'ScheduleExpression': sub('at(${HardDeadlineUtc})'), 'ScheduleExpressionTimezone': 'UTC',
                'FlexibleTimeWindow': {'Mode': 'OFF'}, 'State': 'ENABLED',
                'Target': {'Arn': arn('DeadlineFunction'), 'RoleArn': arn('SchedulerRole'),
                    'RetryPolicy': {'MaximumEventAgeInSeconds': 120, 'MaximumRetryAttempts': 3},
                    'Input': sub(json.dumps({'campaign_id': '${CampaignId}', 'owner_nonce': '${OwnerNonce}',
                                             'deadline_utc': '${HardDeadlineUtc}'}, separators=(',', ':')))}}},
    }
    run_resources = [instance_arn,
        sub('arn:${AWS::Partition}:ec2:${AWS::Region}::image/${AmiId}'),
        sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:subnet/${SubnetId}'),
        sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:security-group/${SecurityGroup.GroupId}'),
        sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:network-interface/*'),
        sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:volume/*')]
    resources['ControllerRole'] = {'Type': 'AWS::IAM::Role', 'Properties': {
        'MaxSessionDuration': 21600,
        'AssumeRolePolicyDocument': policy([{'Effect': 'Allow',
            'Principal': {'Federated': ref('GitHubOidcProviderArn')}, 'Action': 'sts:AssumeRoleWithWebIdentity',
            'Condition': {'StringEquals': {'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com',
                'token.actions.githubusercontent.com:sub': 'repo:daejunnom/Rove4k:environment:aws-evaluation'}}}]),
        'Policies': [{'PolicyName': 'one-campaign-execution', 'PolicyDocument': policy([
            allow('ec2:RunInstances', run_resources[1:], {'StringEquals': {
                'aws:RequestedRegion': ref('AWS::Region')}}),
            allow('ec2:RunInstances', instance_arn, {'StringEquals': {
                'ec2:InstanceType': 'm6a.48xlarge', 'ec2:InstanceMarketType': 'spot',
                'ec2:InstanceProfile': arn('InstanceProfile'),
                'aws:RequestedRegion': ref('AWS::Region'),
                'aws:RequestTag/RoveCampaign': ref('CampaignId'), 'aws:RequestTag/RoveOwner': ref('OwnerNonce')}}),
            allow('ec2:CreateTags', [instance_arn,
                sub('arn:${AWS::Partition}:ec2:${AWS::Region}:${AWS::AccountId}:volume/*')],
                {'StringEquals': {'ec2:CreateAction': 'RunInstances',
                    'aws:RequestTag/RoveCampaign': ref('CampaignId'), 'aws:RequestTag/RoveOwner': ref('OwnerNonce')}}),
            allow('ec2:TerminateInstances', instance_arn, owned),
            allow(['ec2:DescribeInstances', 'ec2:DescribeInstanceTypes', 'ec2:DescribeInstanceTypeOfferings', 'ec2:DescribeImages',
                   'ec2:DescribeSubnets', 'ec2:DescribeSecurityGroups', 'ec2:DescribeSpotInstanceRequests',
                   'ec2:DescribeSpotPriceHistory'], '*', {'StringEquals': {'aws:RequestedRegion': ref('AWS::Region')}}),
            allow('iam:PassRole', arn('InstanceRole'), {'StringEquals': {'iam:PassedToService': 'ec2.amazonaws.com'}}),
            allow('iam:GetInstanceProfile', arn('InstanceProfile')),
            allow('iam:GetRole', sub('arn:${AWS::Partition}:iam::${AWS::AccountId}:role/aws-service-role/spot.amazonaws.com/AWSServiceRoleForEC2Spot')),
            allow('servicequotas:GetServiceQuota', sub('arn:${AWS::Partition}:servicequotas:${AWS::Region}:${AWS::AccountId}:ec2/L-34B43A08')),
            # AWS Free Tier exposes no resource-level ARN for this read action.
            # This is an account-plan preflight, not permission to upgrade it.
            allow('freetier:GetAccountPlanState', '*'),
            allow(['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:Query'], arn('OwnershipTable'), scoped_keys),
            allow(['s3:GetObject', 's3:GetObjectVersion', 's3:PutObject', 's3:AbortMultipartUpload', 's3:DeleteObject'], prefix),
            allow('s3:ListBucket', arn('ArtifactBucket'), {'StringLike': {'s3:prefix': [sub('${CampaignId}/*')]}}),
            allow('cloudformation:DescribeStacks', ref('AWS::StackId')),
            # Deployment binding reads only this stack's original template and
            # the deployed watchdog package's CodeSha256; it cannot update code.
            allow('cloudformation:GetTemplate', ref('AWS::StackId'),
                  {'StringEquals': {'aws:RequestedRegion': ref('AWS::Region')}}),
            allow('lambda:GetFunctionConfiguration', arn('DeadlineFunction'),
                  {'StringEquals': {'aws:RequestedRegion': ref('AWS::Region')}}),
            allow('scheduler:GetSchedule', schedule_arn),
            # The exact-instance SSM readiness read has no resource-level ARN;
            # keep its account-wide visibility inside this workload region.
            allow('ssm:DescribeInstanceInformation', '*',
                  {'StringEquals': {'aws:RequestedRegion': ref('AWS::Region')}}),
            allow('ssm:SendCommand', sub('arn:${AWS::Partition}:ssm:${AWS::Region}::document/AWS-RunShellScript')),
            allow('ssm:SendCommand', instance_arn, {'StringEquals': {
                'ssm:resourceTag/RoveCampaign': ref('CampaignId'), 'ssm:resourceTag/RoveOwner': ref('OwnerNonce')}}),
            allow(['ssm:GetCommandInvocation', 'ssm:ListCommandInvocations', 'ssm:CancelCommand'], '*')])}],
        'Tags': campaign_tags}}
    value = {'AWSTemplateFormatVersion': '2010-09-09',
        'Description': 'Rove4k single-instance Spot campaign safety and 30-day evidence; no EC2 instance is created by this stack',
        'Metadata': {'AWSToolsMetrics': {'AWSAgentToolkit': 'aws-cloudformation@3'},
            'Rove4k::DeploymentPrerequisites': {
            'AccountPlan': {
                'Operation': 'freetier:GetAccountPlanState',
                'Before': ['CreateStack', 'UpdateStack', 'RunInstances'],
                'RequiredResponse': {'accountId': 'must equal verified STS account', 'accountPlanType': 'PAID'},
                'RecordResponseFields': ['accountId', 'accountPlanType', 'accountPlanStatus',
                    'accountPlanExpirationDate', 'accountPlanRemainingCredits'],
                'KnownStatusValues': ['NOT_STARTED', 'ACTIVE', 'EXPIRED'],
                'ReadOnlyGlobalEndpointException': 'freetier.us-east-1.api.aws; account-plan observation only, never workload region fallback.',
                'StatusMeaning': 'Record status separately; credit or plan expiration is not evidence of paid-account deactivation.',
                'OnMissingOrUnverifiedEvidence': 'Refuse before resource creation.',
                'Enforcement': 'External deployment preflight; CloudFormation does not query account-plan state.'},
            'Region': {
                'Binding': 'ProjectRegion must equal AWS::Region when explicitly selected.',
                'RegionalResources': 'All campaign resources remain in the stack workload region; never retry another region.',
                'ToolkitConfiguration': 'A Toolkit global configuration-service endpoint is separate from the project workload region.'}}},
        'Parameters': {
            'ProjectRegion': region_parameter,
            'CampaignId': {'Type': 'String', 'AllowedPattern': '[a-z0-9][a-z0-9-]{2,39}'},
            'OwnerNonce': {'Type': 'String', 'AllowedPattern': '[a-f0-9]{32,64}'},
            'HardDeadlineUtc': {'Type': 'String', 'AllowedPattern': r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'},
            'GitHubOidcProviderArn': {'Type': 'String', 'AllowedPattern': r'arn:aws:iam::[0-9]{12}:oidc-provider/token\.actions\.githubusercontent\.com'},
            'AmiId': {'Type': 'AWS::EC2::Image::Id'}, 'SubnetId': {'Type': 'AWS::EC2::Subnet::Id'},
            'VpcId': {'Type': 'AWS::EC2::VPC::Id'}},
        'Rules': {'ProjectRegionMatchesStack': {'Assertions': [{
            'Assert': {'Fn::Or': [{'Fn::Equals': [ref('ProjectRegion'), '']},
                                 {'Fn::Equals': [ref('ProjectRegion'), ref('AWS::Region')]}]},
            'AssertDescription': 'Deploy campaign resources only in the explicitly selected project region; no fallback region.'}]}},
        'Resources': resources,
        'Outputs': {'OwnershipTable': {'Value': ref('OwnershipTable')},
            'ScheduleName': {'Value': ref('DeadlineSchedule')}, 'WatchdogArn': {'Value': arn('DeadlineFunction')},
            'InstanceProfileArn': {'Value': arn('InstanceProfile')}, 'SecurityGroupId': {'Value': ref('SecurityGroup')},
            'ArtifactBucket': {'Value': ref('ArtifactBucket')}, 'ControllerRoleArn': {'Value': arn('ControllerRole')}}}
    if readiness is not None:
        account = readiness['project_account_id']
        organization = readiness['organization_id']
        management = readiness['management_account_id']
        condition = {'StringEquals': {'aws:PrincipalAccount': account,
                                      'aws:PrincipalOrgID': organization}}
        statements = resources['ControllerRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        index = statements.index(allow('freetier:GetAccountPlanState', '*'))
        statements[index:index + 1] = [
            allow('account:GetAccountInformation',
                  f'arn:aws:account::{management}:account/{organization}/{account}', condition),
            allow('organizations:DescribeOrganization', '*', condition)]
        prerequisites = value['Metadata']['Rove4k::DeploymentPrerequisites']
        del prerequisites['AccountPlan']
        prerequisites['AccountReadiness'] = {
            'Kind': readiness['kind'],
            'ReviewedConfiguration': readiness,
            'Before': ['CreateStack', 'UpdateStack', 'RunInstances'],
            'Operations': ['sts:GetCallerIdentity', 'account:GetAccountInformation',
                           'organizations:DescribeOrganization'],
            'RequiredFreshObservations': {
                'Identity': {'Account': account},
                'OwnAccount': {'Request': {}, 'AccountId': account, 'AccountState': 'ACTIVE'},
                'Organization': {'Id': organization, 'MasterAccountId': management, 'FeatureSet': 'ALL'}},
            'TrustSource': 'Explicit reviewed user-confirmed Advanced transition; not inferred from an API error or organization membership.',
            'ReadOnlyGlobalEndpointException': 'Account and organization metadata only; never workload region fallback.',
            'OnMissingOrUnverifiedEvidence': 'Refuse before resource creation; do not switch readiness classes.',
            'Enforcement': 'External deployment preflight; CloudFormation does not perform these observations.',
            'EvidenceMeaning': 'This configured class does not claim a Free Tier PAID API response or a current credit balance.'}
    return value


def output_path(value):
    """Validate an explicit new external JSON destination without creating it."""
    destination = Path(value)
    if not destination.is_absolute() or destination.suffix.lower() != '.json':
        raise ValueError('out must be an absolute new external JSON path')
    if any(part.lower() in ('.aws', '.ssh', 'credentials', 'credential')
           or part.lower() == '.env' or part.lower().startswith('.env.') for part in destination.parts):
        raise ValueError('protected output path')
    for ancestor in (destination, *destination.parents):
        if ancestor.is_symlink():
            raise ValueError('linked output path')
        if ancestor.exists() and getattr(ancestor.stat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('linked output path')
    destination = destination.resolve()
    if destination.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('out must stay outside the source workspace')
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError('out must be new and its external parent must already exist')
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description='Render source-only campaign CloudFormation; never contact AWS.')
    parser.add_argument('--project-region')
    parser.add_argument('--account-readiness', required=True,
                        choices=('freetier-paid', 'configured-advanced-member-project'))
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        destination = output_path(args.out)
        readiness = (readiness_type()().as_dict()
                     if args.account_readiness == 'configured-advanced-member-project' else None)
        value = template(args.project_region, readiness)
        raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
        with os.fdopen(os.open(destination, flags, 0o600), 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({'path': str(destination), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest(),
                      'account_readiness': args.account_readiness, 'source_only': True}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
