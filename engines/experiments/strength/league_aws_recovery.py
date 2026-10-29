"""Read-only reconciliation of a league launch after a controller restart.

The legacy campaign launch/cleanup functions use an incompatible 12-hour
deadline and are intentionally not imported. This observer uses the original
launch token rather than issuing another RunInstances request. Its results are
point-in-time diagnostics: declared identity, S3/EC2 observations and a local
journal lock do not establish remote host ownership, a fenced writer, or game
completion. This module never starts, resumes, stops or terminates an instance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

try:
    from .league_controller import LeaguePlan, _snapshot_state
    from .global_budget import S3SharedBudget, digest
    from .ledger import canonical
    from .shared_coordinator import SharedBudgetJournal
except ImportError:
    from league_controller import LeaguePlan, _snapshot_state
    from global_budget import S3SharedBudget, digest
    from ledger import canonical
    from shared_coordinator import SharedBudgetJournal


_SHA = re.compile(r'[0-9a-f]{64}')
_ID = {
    'image': re.compile(r'ami-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'subnet': re.compile(r'subnet-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'vpc': re.compile(r'vpc-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'group': re.compile(r'sg-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'instance': re.compile(r'i-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'spot_request': re.compile(r'sir-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
}
_OWNER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{7,63}')
_STATES = frozenset(('pending', 'running', 'stopping', 'stopped', 'shutting-down', 'terminated'))
_SPOT_STATES = frozenset(('open', 'active', 'closed', 'cancelled', 'failed'))
_SSM_STATES = frozenset(('Online', 'ConnectionLost', 'Inactive'))


def _launch_digest(token):
    return 'sha256:' + hashlib.sha256(token.encode('utf-8')).hexdigest()


def _v1_request(plan, intent, row, decoded):
    """Validate the frozen v1 request shape without using today's builder.

    This is deliberately versioned and independent of request_preview: future
    producer changes must introduce a new format instead of changing this one.
    The only variable fields come from the bound plan/identity and the bounded
    root, network and price fields below. UserData and unknown fields are not
    accepted. This is shape validation, not proof of AWS authority.
    """
    root = decoded['BlockDeviceMappings'][0]
    name = root['DeviceName']
    volume = root['Ebs']['VolumeSize']
    public = decoded['NetworkInterfaces'][0]['AssociatePublicIpAddress']
    price_text = row['max_hourly_usd']
    if (not isinstance(name, str) or not re.fullmatch(r'/dev/[A-Za-z0-9_.-]{1,32}', name)
            or type(volume) is not int or not 8 <= volume <= 64 or type(public) is not bool
            or not isinstance(price_text, str)):
        raise ValueError('invalid v1 root, network or price')
    try:
        price = Decimal(price_text)
        if not price.is_finite() or not Decimal('0.001') < price <= Decimal(8) or format(price, 'f') != price_text:
            raise ValueError('invalid v1 Spot price')
    except InvalidOperation as error:
        raise ValueError('invalid v1 Spot price') from error
    tags = [{'Key': 'RoveLeagueCampaign', 'Value': plan.campaign},
            {'Key': 'RoveLeagueOwner', 'Value': intent.owner_tag},
            {'Key': 'RoveLeagueLaunchDigest', 'Value': _launch_digest(intent.launch_token)}]
    return {'ImageId': intent.image_id, 'InstanceType': 'm6a.48xlarge',
            'MinCount': 1, 'MaxCount': 1, 'ClientToken': intent.launch_token,
            'IamInstanceProfile': {'Arn': plan.profile_arn},
            'NetworkInterfaces': [{'DeviceIndex': 0, 'SubnetId': intent.subnet_id,
                'Groups': list(intent.security_group_ids), 'AssociatePublicIpAddress': public,
                'DeleteOnTermination': True}],
            'MetadataOptions': {'HttpTokens': 'required', 'HttpEndpoint': 'enabled'},
            'BlockDeviceMappings': [{'DeviceName': name, 'Ebs': {'VolumeSize': volume,
                'VolumeType': 'gp3', 'Encrypted': True, 'DeleteOnTermination': True}}],
            'InstanceMarketOptions': {'MarketType': 'spot', 'SpotOptions': {
                'MaxPrice': price_text, 'SpotInstanceType': 'one-time',
                'InstanceInterruptionBehavior': 'terminate'}},
            'TagSpecifications': [{'ResourceType': kind, 'Tags': [dict(tag) for tag in tags]}
                                  for kind in ('instance', 'volume', 'network-interface', 'spot-instances-request')]}


@dataclass(frozen=True)
class RecoveryIntent:
    """Declared launch identity; integrity/authenticity must be provided externally.

    A digest of this object does not establish its origin. The observer compares
    this declaration to EC2 but never treats that match as launch/GO authority.
    """
    plan_sha256: str
    launch_token: str
    region: str
    image_id: str
    subnet_id: str
    vpc_id: str
    security_group_ids: tuple[str, ...]
    owner_tag: str

    def __post_init__(self):
        if not isinstance(self.plan_sha256, str) or not _SHA.fullmatch(self.plan_sha256):
            raise ValueError('declared league plan digest required')
        if not isinstance(self.launch_token, str) or not _OWNER.fullmatch(self.launch_token):
            raise ValueError('original launch token required')
        if not isinstance(self.region, str) or not re.fullmatch(r'[a-z]{2}(?:-gov)?-[a-z]+-\d+', self.region):
            raise ValueError('explicit launch region required')
        for name, value in (('image', self.image_id), ('subnet', self.subnet_id), ('vpc', self.vpc_id)):
            if not isinstance(value, str) or not _ID[name].fullmatch(value):
                raise ValueError('invalid declared ' + name)
        if (not isinstance(self.security_group_ids, tuple) or not self.security_group_ids
                or tuple(sorted(set(self.security_group_ids))) != self.security_group_ids
                or any(not isinstance(group, str) or not _ID['group'].fullmatch(group)
                       for group in self.security_group_ids)):
            raise ValueError('canonical distinct security group IDs required')
        if not isinstance(self.owner_tag, str) or not _OWNER.fullmatch(self.owner_tag):
            raise ValueError('declared league owner tag required')


def _instance(plan, intent, reservation, row, bound):
    if (not isinstance(reservation, dict) or reservation.get('OwnerId') != plan.account
            or not isinstance(row, dict) or not isinstance(row.get('InstanceId'), str)
            or not _ID['instance'].fullmatch(row['InstanceId'])):
        raise ValueError('EC2 reservation account or instance identity differs')
    groups = row.get('SecurityGroups')
    if (not isinstance(groups, list) or not groups or any(not isinstance(group, dict)
            or not isinstance(group.get('GroupId'), str) for group in groups)):
        raise ValueError('EC2 security groups unavailable')
    observed_groups = tuple(sorted(group['GroupId'] for group in groups))
    tags = row.get('Tags')
    if not isinstance(tags, list) or any(not isinstance(tag, dict)
            or not isinstance(tag.get('Key'), str) or not isinstance(tag.get('Value'), str) for tag in tags):
        raise ValueError('EC2 tags unavailable')
    tag_map = {tag['Key']: tag['Value'] for tag in tags}
    if len(tag_map) != len(tags):
        raise ValueError('duplicate EC2 tag keys')
    tag_digest = tag_map.get('RoveLeagueLaunchDigest')
    if tag_digest is not None and tag_digest != _launch_digest(intent.launch_token):
        raise ValueError('EC2 launch digest tag differs from declared token')
    state = row.get('State')
    state = state.get('Name') if isinstance(state, dict) else None
    profile = row.get('IamInstanceProfile')
    profile = profile.get('Arn') if isinstance(profile, dict) else None
    if (row.get('ClientToken') != intent.launch_token or row.get('InstanceType') != 'm6a.48xlarge'
            or row.get('ImageId') != intent.image_id or row.get('SubnetId') != intent.subnet_id
            or row.get('VpcId') != intent.vpc_id or observed_groups != intent.security_group_ids
            or row.get('InstanceLifecycle') != 'spot' or profile != plan.profile_arn
            or tag_map.get('RoveLeagueCampaign') != plan.campaign
            or tag_map.get('RoveLeagueOwner') != intent.owner_tag
            or 'RoveCampaign' in tag_map or 'RoveOwner' in tag_map
            or not isinstance(state, str) or state not in _STATES
            or (bound is not None and row['InstanceId'] != bound)):
        raise ValueError('EC2 instance differs from declared league launch identity')
    request_id = row.get('SpotInstanceRequestId')
    if request_id is not None and (not isinstance(request_id, str)
                                   or not _ID['spot_request'].fullmatch(request_id)):
        raise ValueError('EC2 Spot request identity is malformed')
    return {'instance_id': row['InstanceId'], 'state': state,
            'spot_request_id': request_id,
            'launch_digest_tag': 'matches' if tag_digest is not None else 'missing'}


def _launch_record(snapshot, plan, intent, current_request_sha256):
    """Compare any original request identity fields without authenticating them.

    Older budget.v2 events need not carry these fields. A caller-supplied
    RecoveryIntent alone cannot reproduce RunInstances without its launch spec.
    A comparison to a caller-supplied spec is diagnostic, not authentication.
    """
    rows = list(snapshot.opening['events']) + list(snapshot.rows)
    matches = [row['data'] for row in rows
               if row.get('event') == 'budget.v2.launch_requested'
               and row['data'].get('launch_token') == intent.launch_token]
    result = {'observation': 'unresolved', 'matching_events': len(matches),
              'identity_digest_matches': False, 'request_digest_present': False,
              'request_digest_comparison': 'not_checked',
              'request_digest_verified': False, 'intent_authenticated': False,
              'stored_request_state': 'unresolved', 'stored_request_canonical_json': None}
    if len(matches) != 1:
        return result
    row = matches[0]
    request = row.get('request_sha256')
    if (row.get('plan_sha256') == plan.sha256
            and row.get('identity_sha256') == digest(asdict(intent))
            and isinstance(request, str) and _SHA.fullmatch(request)):
        result.update(observation='identity_digest_match', identity_digest_matches=True,
                      request_digest_present=True)
        if current_request_sha256 is not None:
            result['request_digest_comparison'] = ('matches_current_preview' if request == current_request_sha256
                                                   else 'differs_current_preview')
        # The previous format kept only a digest. It cannot reconstruct a
        # RunInstances request and must never be upgraded by inference.
        raw = row.get('request_canonical_json')
        if row.get('request_format') == 'rove4k-league-run-instances-v1' and isinstance(raw, str):
            try:
                if len(raw.encode('utf-8')) > 16384:
                    raise ValueError('request exceeds bounded size')
                decoded = json.loads(raw)
                if canonical(decoded).decode('utf-8') != raw or digest(decoded) != request:
                    raise ValueError('request encoding or digest differs')
                expected = _v1_request(plan, intent, row, decoded)
                if (row.get('region') != intent.region or decoded != expected
                        or canonical(expected).decode('utf-8') != raw):
                    raise ValueError('request differs from reviewed v1 shape or identity')
            except (KeyError, IndexError, TypeError, ValueError, UnicodeError, RecursionError):
                result['stored_request_state'] = 'invalid'
            else:
                result['stored_request_state'] = 'canonical_v1_matches_declared_identity'
                result['stored_request_canonical_json'] = raw
    return result


def _spot_observation(client, plan, intent, instance):
    """Observe tagged requests; AWS exposes no client-token filter on this API.

    Tag-only results, including a launch digest, are mutable observations. An
    instance/request ID cross-check is not an authenticated ownership claim.
    The source may return an empty page with a continuation token. Empty or
    unavailable results never demonstrate absence or permission to retry.
    """
    filters = [{'Name': 'tag:RoveLeagueCampaign', 'Values': [plan.campaign]},
               {'Name': 'tag:RoveLeagueOwner', 'Values': [intent.owner_tag]}]
    expected_digest = _launch_digest(intent.launch_token)
    found, seen_ids, seen_tokens, token = [], set(), set(), None
    def unresolved(reason):
        return {'status': 'unresolved', 'reason': reason, 'candidates': [],
                'potential_open_request': None, 'request_launch_token_verified': False}
    try:
        for _ in range(100):
            args = {'Filters': filters, 'MaxResults': 100}
            if token is not None:
                args['NextToken'] = token
            try:
                response = client.call('ec2', 'describe-spot-instance-requests', args)
            except Exception:
                return unresolved('read_unavailable')
            if not isinstance(response, dict) or not isinstance(response.get('SpotInstanceRequests'), list):
                raise ValueError('incomplete Spot response')
            for row in response['SpotInstanceRequests']:
                if not isinstance(row, dict):
                    raise ValueError('malformed Spot request')
                request_id, state, kind = row.get('SpotInstanceRequestId'), row.get('State'), row.get('Type')
                if (not isinstance(request_id, str) or not _ID['spot_request'].fullmatch(request_id)
                        or request_id in seen_ids or not isinstance(state, str) or state not in _SPOT_STATES
                        or not isinstance(kind, str) or kind not in ('one-time', 'persistent')):
                    raise ValueError('Spot request identity or lifecycle unavailable')
                tags = row.get('Tags')
                if (not isinstance(tags, list) or any(not isinstance(tag, dict)
                        or not isinstance(tag.get('Key'), str) or not isinstance(tag.get('Value'), str)
                        for tag in tags)):
                    raise ValueError('Spot request tags unavailable')
                tag_map = {tag['Key']: tag['Value'] for tag in tags}
                if (len(tag_map) != len(tags) or tag_map.get('RoveLeagueCampaign') != plan.campaign
                        or tag_map.get('RoveLeagueOwner') != intent.owner_tag
                        or 'RoveCampaign' in tag_map or 'RoveOwner' in tag_map):
                    raise ValueError('Spot request tags do not match the query')
                actual_instance = row.get('InstanceId')
                if actual_instance is not None and (not isinstance(actual_instance, str)
                        or not _ID['instance'].fullmatch(actual_instance)):
                    raise ValueError('Spot request instance identity is malformed')
                status = row.get('Status')
                if status is not None and not isinstance(status, dict):
                    raise ValueError('Spot request status is malformed')
                status_code = status.get('Code') if isinstance(status, dict) else None
                if status_code is not None and (not isinstance(status_code, str)
                        or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,127}', status_code)):
                    raise ValueError('Spot request status is malformed')
                tag_digest = tag_map.get('RoveLeagueLaunchDigest')
                if tag_digest is None:
                    digest_status = 'missing'
                elif isinstance(tag_digest, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', tag_digest):
                    digest_status = 'matches' if tag_digest == expected_digest else 'different'
                else:
                    raise ValueError('Spot request launch digest tag is malformed')
                bidirectional = bool(instance and instance['spot_request_id'] == request_id
                                     and instance['instance_id'] == actual_instance)
                found.append({'request_id': request_id, 'state': state, 'type': kind,
                              'status_code': status_code, 'instance_id': actual_instance,
                              'launch_digest_tag': digest_status,
                              'instance_request_crosscheck': bidirectional})
                seen_ids.add(request_id)
            token = response.get('NextToken')
            if token is None or token == '':
                break
            if not isinstance(token, str) or token in seen_tokens:
                raise ValueError('invalid or repeated Spot pagination token')
            seen_tokens.add(token)
        else:
            raise ValueError('Spot pagination limit exceeded')
    except ValueError:
        # Incomplete, denied or malformed AWS reads cannot provide a complete
        # candidate inventory. Do not expose unverified partial observations.
        return unresolved('read_incomplete')
    saw_open = any(row['state'] in ('open', 'active') for row in found)
    return {'status': 'observed' if found else 'unresolved',
            'reason': 'tagged_candidates' if found else 'empty_not_absence',
            'candidates': found,
            # A closed-only snapshot cannot exclude another hidden, untagged,
            # deleted, or not-yet-visible request. Never return False here.
            'potential_open_request': True if saw_open else None,
            'request_launch_token_verified': False}


def _ssm_observation(client, instance):
    """Read SSM agent connectivity; this cannot establish child ownership."""
    base = {'status': 'unresolved', 'reason': 'instance_unobserved', 'agent_ping': None,
            'remote_child_ownership': 'unresolved', 'physical_game_settlement_verified': False}
    if instance is None:
        return base
    seen_tokens, token, rows = set(), None, []
    try:
        for _ in range(100):
            args = {'Filters': [{'Key': 'InstanceIds', 'Values': [instance['instance_id']]}], 'MaxResults': 50}
            if token is not None:
                args['NextToken'] = token
            try:
                response = client.call('ssm', 'describe-instance-information', args)
            except Exception:
                return {**base, 'reason': 'read_unavailable'}
            if not isinstance(response, dict) or not isinstance(response.get('InstanceInformationList'), list):
                raise ValueError('incomplete SSM response')
            for row in response['InstanceInformationList']:
                if (not isinstance(row, dict) or row.get('InstanceId') != instance['instance_id']
                        or not isinstance(row.get('PingStatus'), str)
                        or row['PingStatus'] not in _SSM_STATES or rows):
                    raise ValueError('SSM instance or ping status differs')
                rows.append(row)
            token = response.get('NextToken')
            if token is None or token == '':
                break
            if not isinstance(token, str) or token in seen_tokens:
                raise ValueError('invalid or repeated SSM pagination token')
            seen_tokens.add(token)
        else:
            raise ValueError('SSM pagination limit exceeded')
    except ValueError:
        return {**base, 'reason': 'read_incomplete'}
    if rows:
        base.update(status='observed_agent_only', reason='agent_connectivity_only',
                    agent_ping=rows[0]['PingStatus'])
    else:
        base['reason'] = 'empty_not_absence'
    return base


def inspect_launch(plan, store, owner, intent, client, *, launch_spec=None):
    """Inspect one launch token using an exact journal anchor and AWS reads.

    No AWS mutations or ledger writes occur. A missing EC2 result is unresolved:
    it is not evidence that RunInstances never took effect, nor permission to
    submit a new token. An S3 head ahead of the local journal is reported, never
    adopted. Already-started games and the host are never signalled here.
    """
    if not isinstance(plan, LeaguePlan) or not isinstance(store, S3SharedBudget) or not isinstance(owner, SharedBudgetJournal):
        raise TypeError('league plan and actual shared ledger owner required')
    if not isinstance(intent, RecoveryIntent) or intent.plan_sha256 != plan.sha256:
        raise ValueError('declared intent differs from the league plan')
    current_request_sha256 = None
    if launch_spec is not None:
        # Lazy import: league_aws_launch imports RecoveryIntent from this module.
        try:
            from .league_aws_launch import LeagueLaunchSpec, request_preview
        except ImportError:
            from league_aws_launch import LeagueLaunchSpec, request_preview
        if not isinstance(launch_spec, LeagueLaunchSpec) or launch_spec.identity != intent:
            raise ValueError('launch specification differs from the observed identity')
        current_request_sha256 = digest(request_preview(plan, launch_spec))
    hosts = [host for host in plan.hosts if host.launch_token == intent.launch_token]
    if (len(hosts) != 1 or hosts[0].region != intent.region
            or getattr(client, 'region', None) != intent.region
            or owner._store is not store or store.campaign != plan.campaign
            or store.account != plan.account or store.bucket != plan.bucket
            or store.region != plan.home_region or store.key != plan.campaign + '/shared/budget.json'):
        raise ValueError('intent, region, plan or shared ledger differs')
    # The ledger and EC2 clients can use different regions and credential
    # sessions. Check both callers before making either project read; a profile
    # label or the region alone does not establish the workload account.
    for transport in (store.client, client):
        identity = transport.call('sts', 'get-caller-identity', {})
        if not isinstance(identity, dict) or identity.get('Account') != plan.account:
            raise ValueError('AWS caller is not in the league project account')
    with owner._lock:
        local_anchor = owner.anchor
        snapshot = store.load(local_anchor)
        ledger_state = _snapshot_state(plan.campaign, snapshot)
        rows = [row for row in ledger_state.instances
                if row.charge.launch_token == intent.launch_token]
        if len(rows) != 1 or rows[0].region != intent.region:
            raise ValueError('original launch request is not present in the observed ledger')
        bound = rows[0].charge.instance_id
        pending = owner.blocked
        launch_record = _launch_record(snapshot, plan, intent, current_request_sha256)
    request = {'Filters': [{'Name': 'client-token', 'Values': [intent.launch_token]}], 'MaxResults': 100}
    token, seen, matches, ec2_problem = None, set(), [], None
    for _ in range(100):
        args = dict(request)
        if token is not None:
            args['NextToken'] = token
        try:
            result = client.call('ec2', 'describe-instances', args)
        except Exception:
            ec2_problem = 'read_unavailable'
            break
        if not isinstance(result, dict) or not isinstance(result.get('Reservations'), list):
            ec2_problem = 'read_incomplete'
            break
        for reservation in result['Reservations']:
            if not isinstance(reservation, dict) or not isinstance(reservation.get('Instances'), list):
                ec2_problem = 'read_incomplete'
                break
            for instance in reservation['Instances']:
                matches.append(_instance(plan, intent, reservation, instance, bound))
                if len(matches) > 1:
                    raise ValueError('launch token resolved to multiple instances')
        if ec2_problem:
            break
        token = result.get('NextToken')
        if token is None or token == '':
            break
        if not isinstance(token, str) or not token or token in seen:
            ec2_problem = 'read_incomplete'
            break
        seen.add(token)
    else:
        ec2_problem = 'read_incomplete'
    if ec2_problem:
        # Discard partial rows: a missing page can hide a competing instance.
        matches = []
    observed_instance = matches[0] if matches else None
    spot_observation = _spot_observation(client, plan, intent, observed_instance)
    ssm_observation = _ssm_observation(client, observed_instance)
    games = [{'game_id': game.game_id, 'ledger_release_authorized': game.release_authorized,
              'ledger_release_observed': game.release_observed, 'ledger_settled': game.settled}
             for game in ledger_state.games if game.launch_token == intent.launch_token]
    with owner._lock:
        # A local writer can advance while EC2 is being queried. This flag is
        # diagnostic only: equal local anchors cannot exclude another host's
        # write, S3 ABA, or an instance change immediately after this read.
        final_anchor, final_blocked = owner.anchor, owner.blocked
        journal_changed = final_anchor != local_anchor or final_blocked != pending
    if pending or final_blocked or journal_changed or snapshot.anchor != local_anchor:
        # An observed newer or locally uncertain journal is not the anchored
        # intent the caller asked to recover. Keep it quarantined even if its
        # JSON happens to match the declared request.
        launch_record['stored_request_canonical_json'] = None
        launch_record['stored_request_state'] = 'journal_unresolved'
    return {'format': 'rove4k-league-launch-observation-v1', 'plan_sha256': plan.sha256,
            'region': intent.region, 'launch_token': intent.launch_token,
            'ec2_state': matches[0]['state'] if matches else 'unresolved',
            'ec2_observation_reason': ec2_problem or ('observed' if matches else 'empty_not_absence'),
            'instance_id': matches[0]['instance_id'] if matches else bound,
            'instance_launch_digest_tag': matches[0]['launch_digest_tag'] if matches else 'unresolved',
            'ledger_anchor': asdict(snapshot.anchor), 'journal_anchor': asdict(local_anchor),
            'ledger_ahead_of_journal': snapshot.anchor != local_anchor,
            'journal_blocked_at_snapshot': pending,
            'journal_anchor_after_ec2': asdict(final_anchor), 'journal_blocked_after_ec2': final_blocked,
            'local_journal_changed_during_observation': journal_changed, 'ledger_games': games,
            'ledger_launch_record': launch_record, 'spot_request_observation': spot_observation,
            'ssm_agent_observation': ssm_observation,
            'absence_proven': False, 'intent_authenticated': False,
            'remote_owner_authenticated': False, 'physical_game_settlement_verified': False,
            'launch_authorized': False, 'scored_go_authorized': False,
            'termination_authorized': False, 'aws_mutation_performed': False}
