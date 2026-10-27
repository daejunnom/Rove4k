"""Cumulative campaign admission, independent of the game controller and AWS.

Amounts are conservative upper bounds, not reconciled AWS invoices. A launch
request counts until authoritative absence or observed termination; sending a
terminate request never frees time, money, or the one-instance slot.
"""
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
import math
import re


def decimal(value):
    if isinstance(value, bool):
        raise ValueError('boolean is not a monetary amount')
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError('amount must be finite and nonnegative')
    return result


def timestamp(value):
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('ledger timestamp must specify its UTC offset')
        value = parsed.timestamp()
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('timestamp must be a nonnegative finite epoch')
    return float(value)


@dataclass(frozen=True)
class BudgetPolicy:
    instance_seconds: int = 12 * 3600
    compute_usd: Decimal = Decimal('100')
    total_usd: Decimal = Decimal('120')
    ancillary_reserve_usd: Decimal = Decimal('20')
    max_hourly_usd: Decimal = Decimal('8')
    max_pairs: int = 128
    termination_slack_seconds: int = 300

    def __post_init__(self):
        for name in ('compute_usd', 'total_usd', 'ancillary_reserve_usd', 'max_hourly_usd'):
            object.__setattr__(self, name, decimal(getattr(self, name)))
        if (type(self.instance_seconds) is not int or type(self.max_pairs) is not int
                or not 0 < self.instance_seconds <= 43200 or not 0 < self.max_pairs <= 128):
            raise ValueError('campaign time/pair caps cannot exceed the accepted policy')
        if self.compute_usd > 100 or self.total_usd > 120 or self.max_hourly_usd > 8:
            raise ValueError('campaign monetary caps cannot exceed the accepted policy')
        if self.ancillary_reserve_usd < 20 or self.compute_usd + self.ancillary_reserve_usd > self.total_usd:
            raise ValueError('preserve the ancillary reserve within the total cap')
        if self.max_hourly_usd == 0 or type(self.termination_slack_seconds) is not int or not 0 < self.termination_slack_seconds < self.instance_seconds:
            raise ValueError('a positive termination reserve is required')


@dataclass(frozen=True)
class InstanceCharge:
    launch_token: str
    requested_at: float
    hourly_usd: Decimal
    instance_id: str | None = None
    terminated_at: float | None = None
    authoritative_absence: bool = False

    def __post_init__(self):
        if not isinstance(self.launch_token, str) or not 8 <= len(self.launch_token) <= 64:
            raise ValueError('launch token required')
        object.__setattr__(self, 'requested_at', timestamp(self.requested_at))
        object.__setattr__(self, 'hourly_usd', decimal(self.hourly_usd))
        if self.hourly_usd <= 0 or self.hourly_usd > 8:
            raise ValueError('charge rate must preserve the Spot ceiling')
        if self.terminated_at is not None:
            object.__setattr__(self, 'terminated_at', timestamp(self.terminated_at))
            if self.terminated_at < self.requested_at:
                raise ValueError('termination predates launch')
        if self.authoritative_absence and self.instance_id is not None:
            raise ValueError('a bound instance cannot be declared never launched')

    @property
    def active(self):
        return self.terminated_at is None and not self.authoritative_absence

    def seconds(self, now):
        if self.authoritative_absence:
            return 0.0
        end = self.terminated_at if self.terminated_at is not None else timestamp(now)
        if end < self.requested_at:
            raise ValueError('observation precedes the launch request')
        return end - self.requested_at

    def cost(self, now):
        if self.authoritative_absence:
            return Decimal(0)
        # Linux EC2 has a minimum billing interval; reservation is conservative
        # even before an uncertain launch outcome has been reconciled.
        return decimal(max(60.0, self.seconds(now))) * self.hourly_usd / Decimal(3600)


@dataclass(frozen=True)
class Admission:
    allowed: bool
    reasons: tuple[str, ...]
    instance_seconds_used: float
    compute_upper_usd: Decimal
    total_upper_usd: Decimal
    remaining_seconds: float

    def as_dict(self):
        return {'allowed': self.allowed, 'reasons': list(self.reasons),
                'instance_seconds_used': self.instance_seconds_used,
                'compute_upper_usd': str(self.compute_upper_usd),
                'total_upper_usd': str(self.total_upper_usd),
                'remaining_seconds': self.remaining_seconds}


@dataclass(frozen=True)
class CampaignBudget:
    campaign: str
    policy: BudgetPolicy = BudgetPolicy()
    instances: tuple[InstanceCharge, ...] = ()
    started_pairs: frozenset[str] = frozenset()
    completed_pairs: frozenset[str] = frozenset()
    ancillary_receipts: tuple[tuple[str, Decimal], ...] = ()
    last_at: float = 0.0

    @property
    def active_instances(self):
        return tuple(item for item in self.instances if item.active)

    def _find(self, token):
        matches = [i for i, item in enumerate(self.instances) if item.launch_token == token]
        if len(matches) != 1:
            raise ValueError('unknown or ambiguous launch token')
        return matches[0]

    def apply(self, event, data, at):
        """Reduce one immutable ledger event; unrelated events may be skipped.

        Supported names have a ``budget.`` prefix. The parent ledger owns
        fsync/hash-chain persistence and must record launch_requested before
        invoking EC2. Idempotent retries retain their original request time.
        """
        at = timestamp(at)
        if at < self.last_at:
            raise ValueError('ledger time regressed; do not lower accrued cost')
        if not event.startswith('budget.'):
            return self
        state = replace(self, last_at=at)
        if event == 'budget.launch_requested':
            token, rate = data['launch_token'], decimal(data['max_hourly_usd'])
            if not isinstance(token, str) or not 8 <= len(token) <= 64 or rate <= 0 or rate > self.policy.max_hourly_usd:
                raise ValueError('invalid launch token or price ceiling')
            existing = [item for item in self.instances if item.launch_token == token]
            if existing:
                if existing[0].hourly_usd != rate:
                    raise ValueError('idempotent launch changed its price ceiling')
                return state
            if self.active_instances:
                raise ValueError('an active or unresolved instance already owns the slot')
            if not self.admit(at, 0).allowed:
                raise ValueError('campaign budget cannot admit another instance')
            return replace(state, instances=self.instances + (InstanceCharge(token, at, rate),))
        if event in ('budget.instance_bound', 'budget.launch_absent', 'budget.instance_observed'):
            index = self._find(data['launch_token'])
            item = self.instances[index]
            if event == 'budget.instance_bound':
                instance_id = data['instance_id']
                if not isinstance(instance_id, str) or not instance_id.startswith('i-') or item.authoritative_absence:
                    raise ValueError('invalid instance binding')
                if item.instance_id not in (None, instance_id):
                    raise ValueError('idempotent launch changed its instance identity')
                item = replace(item, instance_id=instance_id)
            elif event == 'budget.launch_absent':
                if item.instance_id or not data.get('authoritative_absence') or not data.get('evidence'):
                    raise ValueError('absence requires unbound authoritative EC2 evidence')
                item = replace(item, authoritative_absence=True)
            else:
                if item.instance_id != data['instance_id'] or item.authoritative_absence:
                    raise ValueError('observation does not belong to the bound instance')
                if data['state'] not in ('pending', 'running', 'stopping', 'stopped', 'shutting-down', 'terminated'):
                    raise ValueError('unknown EC2 state')
                if data['state'] == 'terminated' and item.terminated_at is None:
                    if not data.get('evidence'):
                        raise ValueError('termination requires an authoritative observation')
                    item = replace(item, terminated_at=at)
                elif item.terminated_at is not None and data['state'] != 'terminated':
                    raise ValueError('terminated instance cannot become active again')
            rows = list(self.instances)
            rows[index] = item
            return replace(state, instances=tuple(rows))
        if event == 'budget.terminate_requested':
            item = self.instances[self._find(data['launch_token'])]
            if item.instance_id is None or item.instance_id != data['instance_id']:
                raise ValueError('terminate request identity mismatch')
            return state  # Request success is deliberately not physical termination.
        if event == 'budget.pair_started':
            pair = data['pair_id']
            if not isinstance(pair, str) or not pair:
                raise ValueError('pair identity required')
            if pair not in self.started_pairs and len(self.started_pairs) >= self.policy.max_pairs:
                raise ValueError('cumulative pair cap exhausted')
            if pair not in self.started_pairs and not self.admit(
                    at, data.get('reserved_wall_seconds', 0), pair_id=pair).allowed:
                raise ValueError('campaign is draining; no new pair may start')
            return replace(state, started_pairs=self.started_pairs | {pair})
        if event == 'budget.pair_completed':
            pair = data['pair_id']
            if pair not in self.started_pairs:
                raise ValueError('cannot complete an unregistered pair')
            return replace(state, completed_pairs=self.completed_pairs | {pair})
        if event == 'budget.ancillary_charge':
            receipt, amount = data['receipt_id'], decimal(data['usd'])
            previous = dict(self.ancillary_receipts)
            if receipt in previous and previous[receipt] != amount:
                raise ValueError('receipt identity changed its charge')
            if receipt not in previous:
                return replace(state, ancillary_receipts=self.ancillary_receipts + ((receipt, amount),))
            return state
        raise ValueError('unknown budget event: ' + event)

    @classmethod
    def replay(cls, campaign, events, policy=None):
        result = cls(campaign, policy or BudgetPolicy())
        for row in events:
            if row.get('campaign') != campaign:
                raise ValueError('ledger contains a different campaign')
            result = result.apply(row['event'], row['data'], row['time_utc'])
        return result

    def admit(self, now, expected_wall_seconds, *, pair_id=None):
        """Reserve a future wall interval plus termination time, never games.

        The estimate is not a promise that 30+3 games will finish. An admitted
        pair may still be drained/unscored at the hard campaign boundary.
        """
        now = timestamp(now)
        future = timestamp(expected_wall_seconds)
        if now < self.last_at:
            raise ValueError('budget observation precedes ledger time')
        used = sum(item.seconds(now) for item in self.instances)
        compute = sum((item.cost(now) for item in self.instances), Decimal(0))
        ancillary = sum((amount for _, amount in self.ancillary_receipts), Decimal(0))
        reserve = max(self.policy.ancillary_reserve_usd, ancillary)
        window = decimal(future + self.policy.termination_slack_seconds)
        future_rate = max((item.hourly_usd for item in self.active_instances), default=self.policy.max_hourly_usd)
        future_rate = max(future_rate, self.policy.max_hourly_usd)
        projected = compute + window * future_rate / Decimal(3600)
        reasons = []
        if len(self.active_instances) > 1:
            reasons.append('multiple-active-instances')
        if used + float(window) > self.policy.instance_seconds:
            reasons.append('cumulative-instance-time')
        if projected > self.policy.compute_usd:
            reasons.append('compute-budget')
        if projected + reserve > self.policy.total_usd:
            reasons.append('total-budget')
        if pair_id is not None and pair_id not in self.started_pairs and len(self.started_pairs) >= self.policy.max_pairs:
            reasons.append('cumulative-pair-cap')
        seconds_left = max(0.0, self.policy.instance_seconds - used)
        money_left = min(self.policy.compute_usd - compute, self.policy.total_usd - reserve - compute)
        money_seconds = max(Decimal(0), money_left * Decimal(3600) / future_rate)
        remaining = max(0.0, min(seconds_left, float(money_seconds)) - self.policy.termination_slack_seconds)
        if remaining <= 0 and not reasons:
            reasons.append('budget-drain')
        return Admission(not reasons, tuple(reasons), used, compute, compute + reserve, remaining)

    def deadline(self, now):
        """Latest conservative terminate-trigger epoch, before the hard cap."""
        return timestamp(now) + self.admit(now, 0).remaining_seconds

    def as_dict(self, now):
        admission = self.admit(now, 0)
        return {'campaign': self.campaign, 'instances': [
                    {'launch_token': item.launch_token, 'requested_at': item.requested_at,
                     'max_hourly_usd': str(item.hourly_usd), 'instance_id': item.instance_id,
                     'terminated_at': item.terminated_at,
                     'authoritative_absence': item.authoritative_absence}
                    for item in self.instances],
                'started_pairs': sorted(self.started_pairs),
                'completed_pairs': sorted(self.completed_pairs),
                'ancillary_receipts': [[key, str(amount)] for key, amount in self.ancillary_receipts],
                'last_at': self.last_at, 'admission': admission.as_dict(),
                'terminate_trigger_epoch': self.deadline(now)}


@dataclass(frozen=True)
class SharedInstance:
    """An independently billed instance and its immutable regional identity."""
    region: str
    charge: InstanceCharge
    closing: bool = False


@dataclass(frozen=True)
class SharedGame:
    """A game attempt with separate pre-GO reservation and release facts."""
    game_id: str
    pair_id: str
    launch_token: str
    release_authorized: bool = False
    release_valid_until: float | None = None
    release_observed: bool = False
    settled: bool = False


@dataclass(frozen=True)
class SharedCampaignBudget:
    """V2 game-level budget reducer for a future shared, serialized ledger.

    This object does not launch or stop anything. Its caller must serialize and
    durably append the pre-GO release decision across all regions, and reconcile
    an uncertain GO or child process before marking it settled. The
    legacy CampaignBudget/controller/watchdog are deliberately not consumers
    of this policy and must not be used to claim V2 campaign readiness.

    The $20 ancillary reserve and $8 per-instance price ceiling remain from the
    existing campaign. An upper bound at $120 temporarily blocks new starts;
    an independently confirmed actual charge at $120 closes admission until
    additional funding is explicitly authorized. In-flight games remain
    accounted until physical settlement. There is no instance-hour deadline.
    """
    campaign: str
    prior_compute_usd: Decimal = Decimal(0)
    prior_ancillary_usd: Decimal = Decimal(0)
    prior_game_ids: frozenset[str] = frozenset()
    prior_pair_ids: frozenset[str] = frozenset()
    prior_launch_tokens: frozenset[str] = frozenset()
    prior_instance_ids: frozenset[str] = frozenset()
    prior_receipts: tuple[tuple[str, Decimal], ...] = ()
    instances: tuple[SharedInstance, ...] = ()
    games: tuple[SharedGame, ...] = ()
    ancillary_receipts: tuple[tuple[str, Decimal], ...] = ()
    confirmed_limit: bool = False
    last_at: float = 0.0

    def __post_init__(self):
        if type(self.confirmed_limit) is not bool:
            raise ValueError('confirmed limit must be a boolean')
        object.__setattr__(self, 'prior_compute_usd', decimal(self.prior_compute_usd))
        object.__setattr__(self, 'prior_ancillary_usd', decimal(self.prior_ancillary_usd))
        if (not isinstance(self.prior_game_ids, frozenset) or not isinstance(self.prior_pair_ids, frozenset)
                or not isinstance(self.prior_launch_tokens, frozenset) or not isinstance(self.prior_instance_ids, frozenset)
                or not isinstance(self.prior_receipts, tuple)
                or len(self.prior_pair_ids) > 128
                or any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', value)
                       for value in self.prior_game_ids | self.prior_pair_ids)):
            raise ValueError('invalid previously observed game or pair identities')
        if (any(not isinstance(value, str) or not 8 <= len(value) <= 64 for value in self.prior_launch_tokens)
                or any(not isinstance(value, str) or not value.startswith('i-') for value in self.prior_instance_ids)):
            raise ValueError('invalid previously observed instance ownership')
        receipt_ids = set()
        normalized_receipts = []
        for receipt in self.prior_receipts:
            if (not isinstance(receipt, tuple) or len(receipt) != 2 or not isinstance(receipt[0], str)
                    or not receipt[0] or receipt[0] in receipt_ids):
                raise ValueError('invalid previously observed ancillary receipt')
            receipt_ids.add(receipt[0])
            normalized_receipts.append((receipt[0], decimal(receipt[1])))
        if sum((amount for _, amount in normalized_receipts), Decimal(0)) > self.prior_ancillary_usd:
            raise ValueError('prior receipts exceed the trusted ancillary balance')
        object.__setattr__(self, 'prior_receipts', tuple(normalized_receipts))

    @property
    def active_instances(self):
        return tuple(row for row in self.instances if row.charge.active)

    @property
    def unsettled_games(self):
        return tuple(row for row in self.games if not row.settled)

    @property
    def draining(self):
        """Whether admission is blocked as of the last ledger event.

        The conservative estimate may later fall after a launch is proved
        absent. Only a separately confirmed limit event is permanent. This
        predicate is not evidence that an AWS invoice reached the limit.
        """
        return self.confirmed_limit or self.totals(self.last_at)[1] >= Decimal('120')

    def _find(self, token):
        matches = [i for i, row in enumerate(self.instances) if row.charge.launch_token == token]
        if len(matches) != 1:
            raise ValueError('unknown or ambiguous shared launch token')
        return matches[0]

    def totals(self, now):
        now = timestamp(now)
        if now < self.last_at:
            raise ValueError('budget observation precedes ledger time')
        compute = self.prior_compute_usd + sum((row.charge.cost(now) for row in self.instances), Decimal(0))
        ancillary = self.prior_ancillary_usd + sum((amount for _, amount in self.ancillary_receipts), Decimal(0))
        return compute, compute + max(Decimal('20'), ancillary)

    def can_admit_game(self, now, *, game_id, pair_id, launch_token):
        """Read-only predicate, not an atomic reservation or a GO authority."""
        _, total = self.totals(now)
        if not all(isinstance(value, str) and value for value in (game_id, pair_id, launch_token)):
            return False
        if self.draining or total >= Decimal('120') or game_id in self.prior_game_ids or any(row.game_id == game_id for row in self.games):
            return False
        pairs = {row.pair_id for row in self.games} | self.prior_pair_ids
        if pair_id not in pairs and len(pairs) >= 128:
            return False
        matching = [row.charge for row in self.active_instances if row.charge.launch_token == launch_token and not row.closing]
        return len(matching) == 1 and matching[0].instance_id is not None

    def release_window_fits(self, now, valid_until):
        """Conservatively project the shared upper bound through a GO window.

        This is arithmetic only, not a lease, trusted clock, or GO authority.
        A serialized owner must separately validate the clock, expiry, any
        concurrent charges, the gate transport and recovery before using it.
        """
        now, valid_until = timestamp(now), timestamp(valid_until)
        if now < self.last_at or valid_until < now or valid_until - now > 60:
            raise ValueError('invalid bounded release window')
        return not self.confirmed_limit and self.totals(valid_until)[1] < Decimal('120')

    def may_terminate(self, token):
        """Do not free an owner while any admitted game may still be running."""
        self._find(token)
        return not any(row.launch_token == token and not row.settled for row in self.games)

    def apply(self, event, data, at):
        at = timestamp(at)
        if at < self.last_at:
            raise ValueError('ledger time regressed; do not lower accrued cost')
        if not event.startswith('budget.'):
            return self
        if not event.startswith('budget.v2.'):
            raise ValueError('legacy budget events need explicit migration and reconciliation')
        _, total = self.totals(at)
        state = replace(self, last_at=at)
        if event == 'budget.v2.launch_requested':
            token, region = data['launch_token'], data['region']
            rate = decimal(data['max_hourly_usd'])
            if not isinstance(token, str) or not 8 <= len(token) <= 64 or not isinstance(region, str) or not re.fullmatch(r'[a-z]{2}(?:-gov)?-[a-z]+-\d+', region) or not 0 < rate <= 8:
                raise ValueError('invalid scoped launch or price ceiling')
            if state.draining:
                raise ValueError('campaign is draining; no launch may be retried')
            if token in self.prior_launch_tokens:
                raise ValueError('previously closed launch token cannot be reused')
            matches = [row for row in self.instances if row.charge.launch_token == token]
            if matches:
                if matches[0].region != region or matches[0].charge.hourly_usd != rate:
                    raise ValueError('idempotent launch changed region or price')
                if not matches[0].charge.active or matches[0].closing:
                    raise ValueError('closed launch token cannot be reused')
                return state
            if state.draining or len(self.active_instances) >= 2:
                raise ValueError('campaign is draining or both instance slots are occupied')
            if total + rate / Decimal(60) >= Decimal('120'):
                raise ValueError('campaign cannot admit minimum launch charge')
            return replace(state, instances=self.instances + (SharedInstance(region, InstanceCharge(token, at, rate)),))
        if event in ('budget.v2.instance_bound', 'budget.v2.launch_absent', 'budget.v2.instance_observed'):
            index = self._find(data['launch_token'])
            row, charge = self.instances[index], self.instances[index].charge
            if event == 'budget.v2.instance_bound':
                identity = data['instance_id']
                if not isinstance(identity, str) or not identity.startswith('i-') or not charge.active or row.closing:
                    raise ValueError('invalid instance binding')
                if identity in self.prior_instance_ids or charge.instance_id not in (None, identity) or any(other.charge.instance_id == identity and other.charge.launch_token != charge.launch_token for other in self.instances):
                    raise ValueError('instance identity is already bound or changed')
                charge = replace(charge, instance_id=identity)
            elif event == 'budget.v2.launch_absent':
                evidence = data.get('evidence')
                if (charge.instance_id or data.get('authoritative_absence') is not True
                        or not isinstance(evidence, dict) or evidence.get('launch_token') != charge.launch_token
                        or evidence.get('region') != row.region or evidence.get('state') != 'absent'
                        or not isinstance(evidence.get('observation_id'), str) or not evidence['observation_id']):
                    raise ValueError('absence requires unbound authoritative EC2 evidence')
                charge = replace(charge, authoritative_absence=True)
            else:
                if charge.instance_id is None or charge.instance_id != data['instance_id'] or charge.authoritative_absence:
                    raise ValueError('observation does not belong to the bound instance')
                status = data['state']
                if status not in ('pending', 'running', 'stopping', 'stopped', 'shutting-down', 'terminated'):
                    raise ValueError('unknown EC2 state')
                if status == 'terminated' and charge.terminated_at is None:
                    evidence = data.get('evidence')
                    if (not isinstance(evidence, dict) or evidence.get('launch_token') != charge.launch_token
                            or evidence.get('region') != row.region or evidence.get('instance_id') != charge.instance_id
                            or evidence.get('state') != 'terminated' or not isinstance(evidence.get('observation_id'), str)
                            or not evidence['observation_id']):
                        raise ValueError('termination requires an authoritative observation')
                    charge = replace(charge, terminated_at=at)
                elif charge.terminated_at is not None and status != 'terminated':
                    raise ValueError('terminated instance cannot become active again')
                if status in ('stopping', 'stopped', 'shutting-down', 'terminated'):
                    row = replace(row, closing=True)
            rows = list(self.instances)
            rows[index] = replace(row, charge=charge)
            return replace(state, instances=tuple(rows))
        if event == 'budget.v2.game_admitted':
            game_id, pair_id, token = data['game_id'], data['pair_id'], data['launch_token']
            if not state.can_admit_game(at, game_id=game_id, pair_id=pair_id, launch_token=token):
                raise ValueError('game admission denied: draining, duplicate, pair cap, or unbound instance')
            return replace(state, games=self.games + (SharedGame(game_id, pair_id, token),))
        if event in ('budget.v2.game_release_authorized', 'budget.v2.game_release_observed'):
            matches = [i for i, row in enumerate(self.games) if row.game_id == data['game_id']]
            if len(matches) != 1:
                raise ValueError('unknown game release identity')
            index, game = matches[0], self.games[matches[0]]
            if game.settled:
                raise ValueError('settled game cannot be released')
            if event == 'budget.v2.game_release_authorized':
                owner = self.instances[self._find(game.launch_token)]
                if state.draining or owner.closing or not owner.charge.active or owner.charge.instance_id is None or game.release_authorized:
                    raise ValueError('game release denied: draining, inactive owner, or duplicate authorization')
                valid_until = None
                if 'valid_until_utc' in data:
                    valid_until = timestamp(data['valid_until_utc'])
                    if not state.release_window_fits(at, valid_until):
                        raise ValueError('game release denied: upper bound crosses limit within release window')
                # Old, unbounded prototype events remain readable, but must
                # never be accepted as an actual transport authorization.
                game = replace(game, release_authorized=True, release_valid_until=valid_until)
            else:
                owner = self.instances[self._find(game.launch_token)].charge
                evidence = data.get('evidence')
                if (not game.release_authorized or data.get('launch_token') != game.launch_token
                        or not isinstance(evidence, dict) or evidence.get('game_id') != game.game_id
                        or evidence.get('instance_id') != owner.instance_id or owner.instance_id is None
                        or not isinstance(evidence.get('observation_id'), str) or not evidence['observation_id']):
                    raise ValueError('release observation requires prior authorization and GO evidence')
                game = replace(game, release_observed=True)
            rows = list(self.games)
            rows[index] = game
            return replace(state, games=tuple(rows))
        if event == 'budget.v2.game_settled':
            matches = [i for i, row in enumerate(self.games) if row.game_id == data['game_id']]
            if len(matches) != 1:
                raise ValueError('game settlement requires identity and physical completion evidence')
            game = self.games[matches[0]]
            owner = self.instances[self._find(game.launch_token)].charge
            receipt = data.get('evidence')
            if (data.get('launch_token') != game.launch_token or data.get('physically_settled') is not True
                    or not isinstance(receipt, dict) or receipt.get('game_id') != game.game_id
                    or receipt.get('instance_id') != owner.instance_id or owner.instance_id is None
                    or receipt.get('state') not in ('exited', 'cancelled_before_go')
                    or (receipt.get('state') == 'cancelled_before_go' and game.release_authorized)
                    or not isinstance(receipt.get('observation_id'), str) or not receipt['observation_id']):
                raise ValueError('game settlement requires identity and physical completion evidence')
            rows = list(self.games)
            rows[matches[0]] = replace(rows[matches[0]], settled=True)
            return replace(state, games=tuple(rows))
        if event == 'budget.v2.terminate_requested':
            token = data['launch_token']
            index = self._find(token)
            row = self.instances[index]
            if row.charge.instance_id is None or row.charge.instance_id != data['instance_id'] or not self.may_terminate(token):
                raise ValueError('termination requires the exact owner and settled games')
            rows = list(self.instances)
            rows[index] = replace(row, closing=True)
            return replace(state, instances=tuple(rows))
        if event == 'budget.v2.ancillary_charge':
            receipt, amount = data['receipt_id'], decimal(data['usd'])
            if not isinstance(receipt, str) or not receipt:
                raise ValueError('receipt identity required')
            previous = dict(self.prior_receipts + self.ancillary_receipts)
            if receipt in previous and previous[receipt] != amount:
                raise ValueError('receipt identity changed its charge')
            if receipt not in previous:
                state = replace(state, ancillary_receipts=self.ancillary_receipts + ((receipt, amount),))
            return state
        if event == 'budget.v2.limit_confirmed':
            evidence = data.get('evidence')
            try:
                actual = decimal(data.get('actual_usd'))
            except (ArithmeticError, TypeError, ValueError) as error:
                raise ValueError('confirmed limit requires actual charge and source evidence') from error
            if (actual < Decimal('120') or not isinstance(evidence, dict)
                    or not isinstance(evidence.get('observation_id'), str) or not evidence['observation_id']
                    or not isinstance(evidence.get('source'), str) or not evidence['source']):
                raise ValueError('confirmed limit requires actual charge and source evidence')
            # Authenticity of the evidence and any budget increase are the
            # responsibility of the independently fenced campaign owner.
            return replace(state, confirmed_limit=True)
        if event == 'budget.v2.observe':
            return state
        raise ValueError('unknown shared budget event: ' + event)

    @classmethod
    def replay(cls, campaign, events):
        state = cls(campaign)
        for row in events:
            if row.get('campaign') != campaign:
                raise ValueError('ledger contains a different campaign')
            state = state.apply(row['event'], row['data'], row['time_utc'])
        return state
