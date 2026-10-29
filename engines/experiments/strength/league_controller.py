"""League-specific plan and shared-budget observation, without GO authority.

This module never invokes the legacy AWS plan, deadline watchdog or cleanup.
The identity checks below catch declared collisions only: they do not verify
deployed IAM, boot user-data, external owners, source provenance, clocks or
physical processes.  The shared journal's S3 writes remain synchronous and
must run away from WaveExecutor's selector thread.  A successful observation
is not permission to launch, send GO or terminate an instance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import re
import threading

try:
    from .budget import SharedCampaignBudget, decimal, timestamp
    from .diagnostic_ledger_bridge import DiagnosticHost, DiagnosticLedgerMailbox
    from .global_budget import S3SharedBudget
    from .ledger import digest
    from .shared_coordinator import SharedBudgetJournal
except ImportError:
    from budget import SharedCampaignBudget, decimal, timestamp
    from diagnostic_ledger_bridge import DiagnosticHost, DiagnosticLedgerMailbox
    from global_budget import S3SharedBudget
    from ledger import digest
    from shared_coordinator import SharedBudgetJournal


_REGION = re.compile(r'[a-z]{2}(?:-gov)?-[a-z]+-\d+')
_CAMPAIGN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')
_BUCKET = re.compile(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]')
_TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{7,63}')


def _arn(value, account, kind):
    """Accept only canonical resource ARNs, not table-name/ARN aliases."""
    region = r'[a-z]{2}(?:-gov)?-[a-z]+-\d+'
    name = r'[A-Za-z0-9_+=,.@/-]+'
    patterns = {
        'table': rf'arn:aws:dynamodb:{region}:{account}:table/[A-Za-z0-9_.-]+',
        'role': rf'arn:aws:iam::{account}:role/{name}',
        'profile': rf'arn:aws:iam::{account}:instance-profile/{name}',
        'watchdog': rf'arn:aws:lambda:{region}:{account}:function:[A-Za-z0-9_-]+',
    }
    if not isinstance(value, str) or not re.fullmatch(patterns[kind], value):
        raise ValueError('canonical ' + kind + ' ARN in plan account required')
    return value


@dataclass(frozen=True)
class LegacyResources:
    campaign: str
    bucket: str
    table: str
    role_arn: str
    profile_arn: str
    watchdog_arn: str


@dataclass(frozen=True)
class HostPlan:
    region: str
    profile: str
    slots: int
    launch_token: str
    later_profiles: tuple[str, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.region, str) or not _REGION.fullmatch(self.region)
                or self.profile not in ('test-p16', 'test-p192')
                or type(self.slots) is not int
                or self.slots != {'test-p16': 11, 'test-p192': 1}[self.profile]
                or not isinstance(self.launch_token, str) or not _TOKEN.fullmatch(self.launch_token)
                or not isinstance(self.later_profiles, tuple)
                or any(value not in ('test-p16', 'test-p192') for value in self.later_profiles)
                or len(set((self.profile, *self.later_profiles))) != 1 + len(self.later_profiles)):
            raise ValueError('P16/P192 host region, slots or token differs')


@dataclass(frozen=True)
class LeaguePlan:
    campaign: str
    account: str
    home_region: str
    bucket: str
    table: str
    role_arn: str
    profile_arn: str
    watchdog_arn: str
    legacy: LegacyResources
    hosts: tuple[HostPlan, ...]

    def __post_init__(self):
        if (not isinstance(self.campaign, str) or not _CAMPAIGN.fullmatch(self.campaign)
                or not self.campaign.startswith('league-')
                or not isinstance(self.account, str) or not re.fullmatch(r'\d{12}', self.account)
                or not isinstance(self.home_region, str) or not _REGION.fullmatch(self.home_region)
                or not isinstance(self.bucket, str) or not _BUCKET.fullmatch(self.bucket)
                or not isinstance(self.legacy, LegacyResources)
                or not isinstance(self.hosts, tuple) or not 1 <= len(self.hosts) <= 2
                or any(not isinstance(host, HostPlan) for host in self.hosts)
                or len({host.launch_token for host in self.hosts}) != len(self.hosts)):
            raise ValueError('invalid league identity or host cohort')
        old = self.legacy
        if (not isinstance(old.campaign, str) or not _CAMPAIGN.fullmatch(old.campaign)
                or not isinstance(old.bucket, str) or not _BUCKET.fullmatch(old.bucket)):
            raise ValueError('canonical legacy identity required')
        for kind, new, previous in (
            ('table', self.table, old.table), ('role', self.role_arn, old.role_arn),
            ('profile', self.profile_arn, old.profile_arn), ('watchdog', self.watchdog_arn, old.watchdog_arn),
        ):
            if _arn(new, self.account, kind) == _arn(previous, self.account, kind):
                raise ValueError('league and legacy ' + kind + ' collide')
        if self.campaign == old.campaign or self.bucket == old.bucket:
            raise ValueError('league and legacy campaign or bucket collide')

    @property
    def sha256(self):
        return digest({'format': 'rove4k-league-plan-v2', **asdict(self)})


def _snapshot_state(campaign, snapshot):
    """Replay a validated S3 snapshot including the trusted opening balance.

    The S3 parser has validated the opening and event chain.  Replaying only
    snapshot.rows would omit carried-in costs and past ownership identities.
    Keep this arithmetic in sync with S3SharedBudget._parse; fixtures cover
    opening events, balances, confirmed drain and subsequent ledger events.
    """
    opening = snapshot.opening
    state = SharedCampaignBudget(campaign)
    for row in opening['events']:
        state = state.apply(row['event'], row['data'], row['time_utc'])
    state = replace(state, last_at=timestamp(opening['as_of']),
                    prior_compute_usd=decimal(opening['prior_compute_usd']),
                    prior_ancillary_usd=decimal(opening['prior_ancillary_usd']),
                    confirmed_limit=state.confirmed_limit or opening['prior_limit_confirmed'],
                    prior_game_ids=frozenset(opening['prior_game_ids']),
                    prior_pair_ids=frozenset(opening['prior_pair_ids']),
                    prior_launch_tokens=frozenset(opening['prior_launch_tokens']),
                    prior_instance_ids=frozenset(opening['prior_instance_ids']),
                    prior_receipts=tuple(tuple(row) for row in opening['prior_receipts']))
    for row in snapshot.rows:
        state = state.apply(row['event'], row['data'], row['time_utc'])
    return state


def _budget_report(state, at, compute, upper):
    """Describe the current ledger arithmetic without claiming a bill.

    The prior balances and receipts are recorded assertions, and the instance
    charge is calculated at the recorded upper rate from the request time.
    Neither those values nor a recorded limit event authenticate actual AWS
    charges. The reserve and its buffer expose the existing policy unchanged.
    """
    recorded_ancillary = state.prior_ancillary_usd + sum(
        (amount for _, amount in state.ancillary_receipts), decimal('0'))
    reserve_floor = decimal('20')
    reserve_buffer = max(decimal('0'), reserve_floor - recorded_ancillary)
    # This is the maximum policy window, not an actual authorized game or
    # proof of a future charge. A shorter window can yield a different result.
    _, projected_upper = state.totals(at + 60)
    maximum_window_fits = state.release_window_fits(at, at + 60)
    reasons = []
    if state.confirmed_limit:
        reasons.append('ledger_limit_reported')
    if upper >= decimal('120'):
        reasons.append('estimated_upper_reached')
    return {
        # Keep the original keys for consumers of previous reports.
        'compute_usd': str(compute), 'upper_usd': str(upper),
        'compute_upper_usd': str(compute),
        'prior_compute_recorded_usd': str(state.prior_compute_usd),
        'ancillary_recorded_usd': str(recorded_ancillary),
        'ancillary_reserve_floor_usd': str(reserve_floor),
        'ancillary_reserve_buffer_usd': str(reserve_buffer),
        'budget_limit_usd': '120',
        'maximum_release_window_seconds': 60,
        'maximum_release_window_upper_usd': str(projected_upper),
        'maximum_release_window_budget_fits': maximum_window_fits,
        'projection_scope': 'ledger_arithmetic_only_not_game_admission',
        'instance_charge_basis': 'request_time_upper_rate_and_minimum_60_seconds',
        'billing_authenticated': False,
        'confirmed_billed_usd': None,
        'draining_reasons': reasons,
    }


class LeagueController:
    """Serialize actual budget observations and produce a denial-only mailbox.

    This is not the scored controller.  S3 and the journal do not prove a
    distributed owner, authentic physical settlement, or exclusive IAM. A
    denied or uncertain action never sends GO and cannot terminate a host.
    Existing games are only reported; this code does not control their life.
    """
    provides_go_authority = False
    provides_termination_authority = False

    def __init__(self, plan, store, owner):
        if not isinstance(plan, LeaguePlan) or not isinstance(store, S3SharedBudget) or not isinstance(owner, SharedBudgetJournal):
            raise TypeError('league plan, actual S3 budget and journal owner required')
        if (owner._store is not store or store.campaign != plan.campaign or store.account != plan.account
                or store.bucket != plan.bucket or store.region != plan.home_region
                or store.key != plan.campaign + '/shared/budget.json'):
            raise ValueError('league plan and owned shared ledger identities differ')
        self.plan, self.store, self.owner = plan, store, owner
        self._lock = threading.Lock()
        self._mailboxes = []
        # A restarted owner must observe its validated opening and live ledger
        # before accepting even denial-only diagnostic requests.
        self._draining = True
        self._observed = None
        self._observed_anchor = None
        self._faulted = False

    def observe(self, *, request_id, at):
        """Journal a budget observation; preserve unconfirmed game ownership."""
        with self._lock:
            if self._faulted:
                raise RuntimeError('league observation requires independent reconciliation')
            at = timestamp(at)
            try:
                snapshot = self.owner.record(request_id=request_id, event='budget.v2.observe',
                    data={'scope': 'league-controller-v2', 'plan_sha256': self.plan.sha256}, at=at)
                state = _snapshot_state(self.plan.campaign, snapshot)
                compute, upper = state.totals(at)
                hosts = {row.launch_token: row for row in self.plan.hosts}
                for instance in state.active_instances:
                    planned = hosts.get(instance.charge.launch_token)
                    if planned is None or planned.region != instance.region:
                        raise ValueError('active ledger owner is outside the declared host cohort')
            except BaseException:
                # Unknown write or untrusted reconstruction cannot permit
                # further local requests. Already-owned children are untouched.
                self._draining = True
                self._observed = None
                self._observed_anchor = None
                self._faulted = True
                for mailbox in self._mailboxes:
                    mailbox.on_drain('shared_budget_unknown', None, {})
                raise
            self._draining = state.draining
            self._observed = state
            self._observed_anchor = snapshot.anchor
            if self._draining:
                # Purely local notifications prevent new diagnostic requests;
                # they do not prove that another host has been fenced.
                for mailbox in self._mailboxes:
                    mailbox.on_drain('shared_budget_reached', None, {})
            games = [{'game_id': row.game_id, 'launch_token': row.launch_token,
                      'release_authorized': row.release_authorized,
                      'release_observed': row.release_observed, 'settled': row.settled}
                     for row in state.games]
            return {'state': 'draining' if state.draining else 'diagnostic',
                    'budget': _budget_report(state, at, compute, upper),
                    'draining': state.draining, 'games': games,
                    'scored_go_allowed': False, 'termination_allowed': False,
                    'scored_go_block_reason': 'score_authority_not_implemented',
                    'declared_resource_ids_disjoint': True, 'iam_isolation_verified': False,
                    'legacy_nonce_tokens_tags_schedules_verified': False,
                    'physical_settlement_verified': False, 'anchor': asdict(snapshot.anchor)}

    def diagnostic_mailbox(self, host, **kwargs):
        """Bind the existing Wave mailbox; it always denies all GO requests."""
        if not isinstance(host, DiagnosticHost) or host.launch_token not in {row.launch_token for row in self.plan.hosts}:
            raise ValueError('diagnostic host is outside this plan')
        with self._lock:
            # This is a point-in-time local comparison, not an atomic fence:
            # other writers and remote EC2 identity remain unverified.
            if (self._draining or self.owner.blocked or self._observed is None
                    or self.owner.anchor != self._observed_anchor):
                raise ValueError('league budget owner is draining or blocked')
            bindings = [row for row in self._observed.active_instances
                        if row.charge.launch_token == host.launch_token and not row.closing]
            if len(bindings) != 1 or bindings[0].charge.instance_id != host.instance_id:
                raise ValueError('diagnostic host differs from the observed ledger binding')
            mailbox = DiagnosticLedgerMailbox(self.owner, host, **kwargs)
            self._mailboxes.append(mailbox)
            return mailbox
