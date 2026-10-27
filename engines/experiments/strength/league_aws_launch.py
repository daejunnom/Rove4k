"""Build and inspect a league Spot request without issuing RunInstances.

This is intentionally independent of the legacy AWSPlan, its 12-hour shutdown,
deadline Lambda and unconditional cleanup. It constructs an exact request and
checks its durable budget intent and point-in-time AWS metadata. It provides no
permission to create, retry, stop, or terminate an instance. In particular,
S3 CAS, a local journal and a caller-supplied Advisor record do not establish a
globally fenced owner, trusted clock, source authenticity, boot ownership, or
live Spot capacity. Those remain mandatory before a real launch can be wired.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import re

try:
    from .aws import (ADVISOR_MAX_SOURCE_AGE_SECONDS, ADVISOR_URL, INSTANCE_TYPE,
                      STANDARD_SPOT_QUOTA, iso, pages, standard_spot_used)
    from .budget import decimal, timestamp
    from .global_budget import S3SharedBudget
    from .league_aws_recovery import RecoveryIntent
    from .league_controller import LeaguePlan, _snapshot_state
    from .ledger import digest
    from .shared_coordinator import SharedBudgetJournal
except ImportError:
    from aws import (ADVISOR_MAX_SOURCE_AGE_SECONDS, ADVISOR_URL, INSTANCE_TYPE,
                     STANDARD_SPOT_QUOTA, iso, pages, standard_spot_used)
    from budget import decimal, timestamp
    from global_budget import S3SharedBudget
    from league_aws_recovery import RecoveryIntent
    from league_controller import LeaguePlan, _snapshot_state
    from ledger import digest
    from shared_coordinator import SharedBudgetJournal


@dataclass(frozen=True)
class LeagueLaunchSpec:
    """One explicit request; its declaration is not an authenticated intent."""
    identity: RecoveryIntent
    root_device_name: str
    root_volume_gib: int
    max_hourly_usd: str
    associate_public_ipv4: bool

    def __post_init__(self):
        if not isinstance(self.identity, RecoveryIntent):
            raise TypeError('explicit recoverable instance identity required')
        if (not isinstance(self.root_device_name, str)
                or not re.fullmatch(r'/dev/[A-Za-z0-9_.-]{1,32}', self.root_device_name)
                or type(self.root_volume_gib) is not int or not 8 <= self.root_volume_gib <= 64
                or type(self.associate_public_ipv4) is not bool
                or not isinstance(self.max_hourly_usd, str)):
            raise ValueError('explicit root volume, price and network settings required')
        price = decimal(self.max_hourly_usd)
        if not Decimal('0.001') < price <= Decimal(8) or self.max_hourly_usd != format(price, 'f'):
            raise ValueError('canonical Spot price ceiling must be within the reviewed limit')


def _bind(plan, spec):
    if not isinstance(plan, LeaguePlan) or not isinstance(spec, LeagueLaunchSpec):
        raise TypeError('league plan and explicit launch specification required')
    identity = spec.identity
    hosts = [host for host in plan.hosts if host.launch_token == identity.launch_token]
    if identity.plan_sha256 != plan.sha256 or len(hosts) != 1 or hosts[0].region != identity.region:
        raise ValueError('launch specification does not belong to the selected league host')


def request_preview(plan, spec):
    """Return exact EC2 RunInstances arguments; this is not launch authority.

    The AMI must eventually supply an independently reviewed host owner; no
    credentials, legacy shutdown script, timeout, or hidden schedule is added.
    Spot interruption can still kill a game and is a separate infrastructure
    failure, not a normal budget drain. The launch-token digest is a correlation
    label only: it neither authenticates the request nor hides a guessable token.
    Adding this label changes the canonical request hash; an earlier recorded
    intent cannot authorize or be reinterpreted as this request.
    """
    _bind(plan, spec)
    identity = spec.identity
    tags = [{'Key': 'RoveLeagueCampaign', 'Value': plan.campaign},
            {'Key': 'RoveLeagueOwner', 'Value': identity.owner_tag},
            {'Key': 'RoveLeagueLaunchDigest',
             'Value': 'sha256:' + hashlib.sha256(identity.launch_token.encode('utf-8')).hexdigest()}]
    return {'ImageId': identity.image_id, 'InstanceType': INSTANCE_TYPE,
            'MinCount': 1, 'MaxCount': 1, 'ClientToken': identity.launch_token,
            'IamInstanceProfile': {'Arn': plan.profile_arn},
            'NetworkInterfaces': [{'DeviceIndex': 0, 'SubnetId': identity.subnet_id,
                'Groups': list(identity.security_group_ids),
                'AssociatePublicIpAddress': spec.associate_public_ipv4, 'DeleteOnTermination': True}],
            'MetadataOptions': {'HttpTokens': 'required', 'HttpEndpoint': 'enabled'},
            'BlockDeviceMappings': [{'DeviceName': spec.root_device_name, 'Ebs': {
                'VolumeSize': spec.root_volume_gib, 'VolumeType': 'gp3', 'Encrypted': True,
                'DeleteOnTermination': True}}],
            'InstanceMarketOptions': {'MarketType': 'spot', 'SpotOptions': {
                'MaxPrice': spec.max_hourly_usd, 'SpotInstanceType': 'one-time',
                'InstanceInterruptionBehavior': 'terminate'}},
            'TagSpecifications': [{'ResourceType': kind, 'Tags': [dict(tag) for tag in tags]}
                                  for kind in ('instance', 'volume', 'network-interface', 'spot-instances-request')]}


def _advisor(advisor, region, now):
    now = timestamp(now)
    if (not isinstance(advisor, dict) or advisor.get('source_url') != ADVISOR_URL
            or advisor.get('region') != region or advisor.get('instance_type') != INSTANCE_TYPE
            or advisor.get('os') != 'Linux' or not isinstance(advisor.get('sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', advisor['sha256'])
            or not isinstance(advisor.get('band'), str) or advisor['band'].replace(' ', '') != '<5%'):
        raise ValueError('exact AWS Linux Spot Advisor <5% record required')
    maximum = decimal(advisor.get('maximum_percent', 101))
    fetched_at = timestamp(advisor.get('fetched_at'))
    source_at = timestamp(advisor.get('source_modified_at'))
    if (maximum > 5 or not source_at <= fetched_at <= now
            or not 0 <= now - fetched_at <= 86400
            or not 0 <= now - source_at <= ADVISOR_MAX_SOURCE_AGE_SECONDS):
        raise ValueError('Spot Advisor record is stale or outside the reviewed range')
    return {'advisor_source_sha256': advisor['sha256'],
            'advisor_source_modified_at': source_at}


def intent_data(plan, spec, advisor, now):
    """Canonical event data for a *single* budget.v2.launch_requested event.

    Persist this through the shared journal before any future EC2 side effect.
    The current reducer tolerates duplicate token events; review below rejects
    them. Creation of this dictionary is neither durable nor an approval.
    """
    request = request_preview(plan, spec)
    return {'launch_token': spec.identity.launch_token, 'region': spec.identity.region,
            'max_hourly_usd': spec.max_hourly_usd, 'plan_sha256': plan.sha256,
            'request_sha256': digest(request), 'identity_sha256': digest(asdict(spec.identity)),
            **_advisor(advisor, spec.identity.region, now)}


def advisor_recheck_data(plan, spec, advisor, now):
    """Bind a newer Advisor source to the same immutable request digest.

    Persist this as budget.v2.observe before reviewing a changed source. It
    is not a launch attempt, a trusted source attestation, or a fresh token.
    """
    return {'scope': 'league-launch-advisor-v1', 'launch_token': spec.identity.launch_token,
            'plan_sha256': plan.sha256, 'request_sha256': digest(request_preview(plan, spec)),
            'identity_sha256': digest(asdict(spec.identity)), **_advisor(advisor, spec.identity.region, now)}


def _caller(client, plan, region):
    if getattr(client, 'region', None) != region:
        raise ValueError('AWS client region differs from the selected host')
    identity = client.call('sts', 'get-caller-identity', {})
    role = plan.role_arn.rsplit('/', 1)[-1]
    expected = f'arn:aws:sts::{plan.account}:assumed-role/{role}/'
    if (not isinstance(identity, dict) or identity.get('Account') != plan.account
            or not isinstance(identity.get('Arn'), str) or not identity['Arn'].startswith(expected)):
        raise ValueError('AWS caller differs from the declared league account or role')
    return {'account': identity['Account'], 'arn': identity['Arn']}


def inspect_environment(plan, spec, client, now):
    """Read the exact region's metadata, quota and price; never call DryRun.

    These observations do not establish IAM policy isolation, Spot capacity,
    a safe host supervisor, or independent ownership of the launch token.
    """
    _bind(plan, spec)
    now = timestamp(now)
    identity = _caller(client, plan, spec.identity.region)
    profile_name = plan.profile_arn.rsplit('/', 1)[-1]
    profile = client.call('iam', 'get-instance-profile', {'InstanceProfileName': profile_name}).get('InstanceProfile', {})
    roles = profile.get('Roles', []) if isinstance(profile, dict) else []
    if (not isinstance(profile, dict) or profile.get('Arn') != plan.profile_arn
            or not isinstance(roles, list) or len(roles) != 1
            or not isinstance(roles[0], dict) or not isinstance(roles[0].get('Arn'), str)
            or not roles[0]['Arn'].startswith(f'arn:aws:iam::{plan.account}:role/')
            or roles[0]['Arn'] in (plan.legacy.role_arn, plan.role_arn)):
        raise ValueError('league instance profile and host role differ from the declared isolation')
    spot_role = client.call('iam', 'get-role', {'RoleName': 'AWSServiceRoleForEC2Spot'}).get('Role', {})
    if spot_role.get('Arn') != f'arn:aws:iam::{plan.account}:role/aws-service-role/spot.amazonaws.com/AWSServiceRoleForEC2Spot':
        raise ValueError('Spot service-linked role is unavailable in the league account')
    types = client.call('ec2', 'describe-instance-types', {'InstanceTypes': [INSTANCE_TYPE]}).get('InstanceTypes', [])
    if (len(types) != 1 or types[0].get('InstanceType') != INSTANCE_TYPE
            or types[0].get('VCpuInfo', {}).get('DefaultVCpus') != 192
            or types[0].get('MemoryInfo', {}).get('SizeInMiB') != 786432
            or 'spot' not in types[0].get('SupportedUsageClasses', [])
            or 'x86_64' not in types[0].get('ProcessorInfo', {}).get('SupportedArchitectures', [])):
        raise ValueError('instance type metadata differs from the league profile')
    images = client.call('ec2', 'describe-images', {'ImageIds': [spec.identity.image_id]}).get('Images', [])
    if (len(images) != 1 or images[0].get('ImageId') != spec.identity.image_id
            or images[0].get('State') != 'available' or images[0].get('Architecture') != 'x86_64'
            or images[0].get('PlatformDetails') != 'Linux/UNIX'
            or images[0].get('RootDeviceName') != spec.root_device_name
            or images[0].get('RootDeviceType') != 'ebs'):
        raise ValueError('selected AMI is not the declared available Linux image')
    mappings = images[0].get('BlockDeviceMappings')
    if not isinstance(mappings, list) or any(not isinstance(row, dict) for row in mappings):
        raise ValueError('AMI block-device mappings unavailable')
    if any(row.get('DeviceName') != spec.root_device_name and 'Ebs' in row for row in mappings):
        raise ValueError('additional AMI EBS volumes require explicit cost and encryption review')
    roots = [row for row in mappings if row.get('DeviceName') == spec.root_device_name]
    root = roots[0].get('Ebs') if len(roots) == 1 else None
    if (not isinstance(root, dict) or not isinstance(root.get('SnapshotId'), str)
            or not re.fullmatch(r'snap-(?:[0-9a-f]{8}|[0-9a-f]{17})', root['SnapshotId'])
            or type(root.get('VolumeSize')) is not int or not 0 < root['VolumeSize'] <= spec.root_volume_gib):
        raise ValueError('AMI root EBS mapping differs or exceeds the requested volume')
    snapshots = client.call('ec2', 'describe-snapshots', {'SnapshotIds': [root['SnapshotId']]}).get('Snapshots', [])
    if (len(snapshots) != 1 or snapshots[0].get('SnapshotId') != root['SnapshotId']
            or snapshots[0].get('State') != 'completed' or type(snapshots[0].get('VolumeSize')) is not int
            or not 0 < snapshots[0]['VolumeSize'] <= spec.root_volume_gib):
        raise ValueError('root snapshot is unavailable or exceeds the requested volume')
    subnets = client.call('ec2', 'describe-subnets', {'SubnetIds': [spec.identity.subnet_id]}).get('Subnets', [])
    if (len(subnets) != 1 or subnets[0].get('SubnetId') != spec.identity.subnet_id
            or subnets[0].get('VpcId') != spec.identity.vpc_id or subnets[0].get('State') != 'available'
            or type(subnets[0].get('AvailableIpAddressCount')) is not int
            or subnets[0]['AvailableIpAddressCount'] < 1
            or not isinstance(subnets[0].get('AvailabilityZone'), str)):
        raise ValueError('selected subnet is unavailable or belongs to another VPC')
    zone = subnets[0]['AvailabilityZone']
    if not zone.startswith(spec.identity.region):
        raise ValueError('subnet availability zone differs from the selected region')
    groups = client.call('ec2', 'describe-security-groups', {'GroupIds': list(spec.identity.security_group_ids)}).get('SecurityGroups', [])
    if (len(groups) != len(spec.identity.security_group_ids)
            or {group.get('GroupId') for group in groups} != set(spec.identity.security_group_ids)
            or any(group.get('VpcId') != spec.identity.vpc_id for group in groups)):
        raise ValueError('selected security groups differ from the declared VPC')
    offers = pages(client, 'ec2', 'describe-instance-type-offerings', {'LocationType': 'availability-zone',
        'Filters': [{'Name': 'location', 'Values': [zone]},
                    {'Name': 'instance-type', 'Values': [INSTANCE_TYPE]}]}, 'InstanceTypeOfferings')
    if not any(row.get('InstanceType') == INSTANCE_TYPE and row.get('Location') == zone for row in offers):
        raise ValueError('instance type is not offered in the selected zone')
    limit = decimal(client.call('service-quotas', 'get-service-quota', {
        'ServiceCode': 'ec2', 'QuotaCode': STANDARD_SPOT_QUOTA}).get('Quota', {}).get('Value'))
    used = standard_spot_used(client)
    if limit - used < 192:
        raise ValueError('fewer than 192 Standard Spot vCPUs remain')
    prices = list(pages(client, 'ec2', 'describe-spot-price-history', {
        'InstanceTypes': [INSTANCE_TYPE], 'ProductDescriptions': ['Linux/UNIX'],
        'AvailabilityZone': zone, 'StartTime': iso(max(0, now - 3600)), 'EndTime': iso(now)}, 'SpotPriceHistory'))
    # DescribeSpotPriceHistory also returns the last price change before the
    # requested start time; that price can still be the currently valid one.
    # The change timestamp is not the observation time or a capacity promise.
    prices = [row for row in prices if row.get('AvailabilityZone') == zone
              and row.get('InstanceType') == INSTANCE_TYPE and timestamp(row.get('Timestamp')) <= now]
    if not prices:
        raise ValueError('no recent Spot price for the selected zone')
    current = max(prices, key=lambda row: timestamp(row['Timestamp']))
    if decimal(current['SpotPrice']) > decimal(spec.max_hourly_usd):
        raise ValueError('Spot price exceeds the declared ceiling')
    return {'plan_sha256': plan.sha256, 'request_sha256': digest(request_preview(plan, spec)),
            'identity_sha256': digest(asdict(spec.identity)), 'identity': identity,
            'root_snapshot_id': root['SnapshotId'], 'zone': zone, 'quota_limit': str(limit), 'quota_used': used,
            'spot_price': str(decimal(current['SpotPrice'])),
            'price_changed_at': timestamp(current['Timestamp']), 'observed_at': now,
            'capacity_available': None, 'iam_isolation_verified': False,
            'host_boot_owner_verified': False, 'launch_authorized': False, 'aws_mutation_performed': False}


def review_recorded_intent(plan, spec, store, owner, advisor, now):
    """Review one exact persisted budget intent; never invoke EC2.

    A single original event must match the exact request and Advisor source;
    a duplicate token, locally uncertain write, prior closed token or existing
    instance binding cannot be treated as a fresh request. The caller-supplied
    Advisor record and clock are still untrusted and cannot unlock launch.
    """
    expected = intent_data(plan, spec, advisor, now)
    if not isinstance(store, S3SharedBudget) or not isinstance(owner, SharedBudgetJournal):
        raise TypeError('actual shared budget store and journal owner required')
    if (owner._store is not store or store.campaign != plan.campaign or store.account != plan.account
            or store.bucket != plan.bucket or store.region != plan.home_region
            or store.key != plan.campaign + '/shared/budget.json'):
        raise ValueError('shared budget ownership differs from the league plan')
    _caller(store.client, plan, plan.home_region)
    with owner._lock:
        if owner.blocked:
            raise ValueError('uncertain journal cannot approve another request')
        anchor = owner.anchor
        snapshot = store.load(anchor)
        if snapshot.anchor != anchor:
            raise ValueError('shared budget is ahead of the local journal')
        state = _snapshot_state(plan.campaign, snapshot)
        events = list(snapshot.opening['events']) + list(snapshot.rows)
        matches = [row for row in events if row.get('event') == 'budget.v2.launch_requested'
                   and isinstance(row.get('data'), dict)
                   and row['data'].get('launch_token') == spec.identity.launch_token]
        if len(matches) != 1:
            raise ValueError('exact unique durable launch request intent required')
        original = matches[0]['data']
        source_keys = {'advisor_source_sha256', 'advisor_source_modified_at'}
        if ({key: value for key, value in original.items() if key not in source_keys}
                != {key: value for key, value in expected.items() if key not in source_keys}
                or not isinstance(original.get('advisor_source_sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', original['advisor_source_sha256'])):
            raise ValueError('exact unique durable launch request intent required')
        timestamp(original.get('advisor_source_modified_at'))
        position = events.index(matches[0])
        rechecks = [row['data'] for row in events[position + 1:]
                    if row.get('event') == 'budget.v2.observe' and isinstance(row.get('data'), dict)
                    and row['data'].get('scope') == 'league-launch-advisor-v1'
                    and row['data'].get('launch_token') == spec.identity.launch_token]
        if rechecks:
            if rechecks[-1] != advisor_recheck_data(plan, spec, advisor, now):
                raise ValueError('latest durable Advisor recheck differs from the supplied source or request')
        elif any(original.get(key) != expected[key] for key in source_keys):
            raise ValueError('new Advisor source requires a durable request-bound recheck')
        instances = [row for row in state.instances if row.charge.launch_token == spec.identity.launch_token]
        if (len(instances) != 1 or not instances[0].charge.active or instances[0].closing
                or instances[0].charge.instance_id is not None or state.draining):
            raise ValueError('launch token is closed, bound, draining or otherwise uncertain')
        compute, upper = state.totals(timestamp(now))
        if upper >= Decimal('120'):
            raise ValueError('aggregate budget ceiling reached')
    return {'plan_sha256': plan.sha256, 'request_sha256': expected['request_sha256'],
            'ledger_anchor_sha256': anchor.sha256, 'compute_upper_usd': str(compute),
            'total_upper_usd': str(upper), 'exact_intent_recorded': True,
            'advisor_source_recorded': True,
            'advisor_input_authenticated': False, 'trusted_clock_verified': False,
            'global_fence_verified': False, 'prior_dispatch_absence_verified': False,
            'launch_authorized': False, 'retry_authorized': False, 'aws_mutation_performed': False}
