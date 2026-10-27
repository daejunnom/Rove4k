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
import re

try:
    from .league_controller import LeaguePlan, _snapshot_state
    from .global_budget import S3SharedBudget
    from .shared_coordinator import SharedBudgetJournal
except ImportError:
    from league_controller import LeaguePlan, _snapshot_state
    from global_budget import S3SharedBudget
    from shared_coordinator import SharedBudgetJournal


_SHA = re.compile(r'[0-9a-f]{64}')
_ID = {
    'image': re.compile(r'ami-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'subnet': re.compile(r'subnet-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'vpc': re.compile(r'vpc-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'group': re.compile(r'sg-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
    'instance': re.compile(r'i-(?:[0-9a-f]{8}|[0-9a-f]{17})'),
}
_OWNER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{7,63}')
_STATES = frozenset(('pending', 'running', 'stopping', 'stopped', 'shutting-down', 'terminated'))


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
            or state not in _STATES or (bound is not None and row['InstanceId'] != bound)):
        raise ValueError('EC2 instance differs from declared league launch identity')
    return {'instance_id': row['InstanceId'], 'state': state}


def inspect_launch(plan, store, owner, intent, client):
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
    request = {'Filters': [{'Name': 'client-token', 'Values': [intent.launch_token]}], 'MaxResults': 100}
    token, seen, matches = None, set(), []
    for _ in range(100):
        args = dict(request)
        if token is not None:
            args['NextToken'] = token
        result = client.call('ec2', 'describe-instances', args)
        if not isinstance(result, dict) or not isinstance(result.get('Reservations'), list):
            raise ValueError('EC2 discovery response is incomplete')
        for reservation in result['Reservations']:
            if not isinstance(reservation, dict) or not isinstance(reservation.get('Instances'), list):
                raise ValueError('EC2 reservation lacks instance list')
            for instance in reservation['Instances']:
                matches.append(_instance(plan, intent, reservation, instance, bound))
                if len(matches) > 1:
                    raise ValueError('launch token resolved to multiple instances')
        token = result.get('NextToken')
        if token is None:
            break
        if not isinstance(token, str) or not token or token in seen:
            raise ValueError('invalid or repeated EC2 pagination token')
        seen.add(token)
    else:
        raise ValueError('EC2 discovery pagination limit exceeded')
    games = [{'game_id': game.game_id, 'ledger_release_authorized': game.release_authorized,
              'ledger_release_observed': game.release_observed, 'ledger_settled': game.settled}
             for game in ledger_state.games if game.launch_token == intent.launch_token]
    with owner._lock:
        # A local writer can advance while EC2 is being queried. This flag is
        # diagnostic only: equal local anchors cannot exclude another host's
        # write, S3 ABA, or an instance change immediately after this read.
        final_anchor, final_blocked = owner.anchor, owner.blocked
        journal_changed = final_anchor != local_anchor or final_blocked != pending
    return {'format': 'rove4k-league-launch-observation-v1', 'plan_sha256': plan.sha256,
            'region': intent.region, 'launch_token': intent.launch_token,
            'ec2_state': matches[0]['state'] if matches else 'unresolved',
            'instance_id': matches[0]['instance_id'] if matches else bound,
            'ledger_anchor': asdict(snapshot.anchor), 'journal_anchor': asdict(local_anchor),
            'ledger_ahead_of_journal': snapshot.anchor != local_anchor,
            'journal_blocked_at_snapshot': pending,
            'journal_anchor_after_ec2': asdict(final_anchor), 'journal_blocked_after_ec2': final_blocked,
            'local_journal_changed_during_observation': journal_changed, 'ledger_games': games,
            'absence_proven': False, 'intent_authenticated': False,
            'remote_owner_authenticated': False, 'physical_game_settlement_verified': False,
            'launch_authorized': False, 'scored_go_authorized': False,
            'termination_authorized': False, 'aws_mutation_performed': False}
