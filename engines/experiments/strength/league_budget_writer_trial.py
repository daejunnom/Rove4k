"""Local model of a single serialized budget and start-intent history.

The store is injected and this module has no AWS adapter.  It does not grant
GO, launch, settlement or termination authority.  In particular the input
prices, timestamps, identities, evidence and store are not authenticated;
the in-memory quarantine is not durable across a process restart.  A real
implementation needs a trusted writer, clock, independently anchored history,
recipient fencing and recovery of all uncertain writes and live processes.
"""
from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import json
import re
import threading

try:
    from .budget import SharedCampaignBudget, decimal, valid_game_pair_id
except ImportError:
    from budget import SharedCampaignBudget, decimal, valid_game_pair_id


FORMAT = 'rove4k-budget-intent-trial-v1'
_SHA = re.compile(r'[0-9a-f]{64}')
_MAX_TIME = 2**40  # Whole seconds remain exactly representable by float.
_EVENTS = frozenset({'budget.v2.launch_requested', 'budget.v2.instance_bound',
    'budget.v2.launch_absent', 'budget.v2.instance_observed',
    'budget.v2.ancillary_charge', 'budget.v2.limit_confirmed',
    'budget.v2.observe', 'budget.v2.game_release_observed',
    'budget.v2.game_settled', 'budget.v2.terminate_requested'})
_INTENT = frozenset({'attempt_id', 'game_id', 'pair_id', 'launch_token',
    'instance_id', 'host_sha256', 'job_sha256', 'request_sha256',
    'not_before_utc', 'expires_utc'})


class Conflict(RuntimeError):
    """A trusted store explicitly reported that no conditional write occurred."""


class Uncertain(RuntimeError):
    """A write might have taken effect and must not be automatically retried."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False,
                      sort_keys=True, separators=(',', ':')).encode('ascii')


def _hash(domain, value):
    return hashlib.sha256(domain + _canonical(value)).hexdigest()


def _seconds(value):
    if type(value) is not int or not 0 <= value <= _MAX_TIME:
        raise ValueError('whole nonnegative bounded UTC seconds are required')
    return value


def _sha(value):
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ValueError('lowercase SHA-256 required')
    return value


def genesis(campaign, *, prior_compute_usd='0', prior_ancillary_usd='0'):
    if not valid_game_pair_id(campaign) or not campaign.startswith('league-'):
        raise ValueError('league campaign identity required')
    compute, ancillary = decimal(prior_compute_usd), decimal(prior_ancillary_usd)
    root = {'format': FORMAT, 'campaign': campaign, 'prior_compute_usd': str(compute),
            'prior_ancillary_usd': str(ancillary)}
    return root, {'revision': 0, 'sha256': _hash(b'rove4k-budget-root\0', root)}


def _root(root):
    if not isinstance(root, dict) or set(root) != {'format', 'campaign', 'prior_compute_usd', 'prior_ancillary_usd'}:
        raise ValueError('invalid root')
    expected, head = genesis(root['campaign'], prior_compute_usd=root['prior_compute_usd'],
                             prior_ancillary_usd=root['prior_ancillary_usd'])
    if _canonical(expected) != _canonical(root):
        raise ValueError('noncanonical root')
    state = SharedCampaignBudget(root['campaign'], prior_compute_usd=decimal(root['prior_compute_usd']),
                                 prior_ancillary_usd=decimal(root['prior_ancillary_usd']))
    return head, state


def projected_upper_micros(state, end):
    """Exact rational projection, rounded upward only after all costs are summed."""
    end = _seconds(end)
    if end < state.last_at:
        raise ValueError('projection precedes last event')
    compute = Fraction(state.prior_compute_usd)
    for row in state.instances:
        charge = row.charge
        if charge.authoritative_absence:
            continue
        start = int(charge.requested_at)
        finish = int(charge.terminated_at) if charge.terminated_at is not None else end
        if finish < start or charge.requested_at != start or (charge.terminated_at is not None and charge.terminated_at != finish):
            raise ValueError('charge timestamps are not whole seconds')
        compute += Fraction(max(60, finish - start)) * Fraction(charge.hourly_usd) / 3600
    ancillary = Fraction(state.prior_ancillary_usd) + sum((Fraction(amount) for _, amount in state.ancillary_receipts), Fraction(0))
    total = (compute + max(Fraction(20), ancillary)) * 1_000_000
    return (total.numerator + total.denominator - 1) // total.denominator


def _apply(state, kind, payload, at, attempts):
    if not isinstance(payload, dict):
        raise ValueError('payload must be an object')
    if kind == 'budget':
        if set(payload) != {'event', 'data'} or payload['event'] not in _EVENTS or not isinstance(payload['data'], dict):
            raise ValueError('unsupported budget event')
        return state.apply(payload['event'], payload['data'], at)
    if kind != 'intent' or set(payload) != _INTENT:
        raise ValueError('invalid intent payload')
    if not valid_game_pair_id(payload['attempt_id']) or payload['attempt_id'] in attempts:
        raise ValueError('attempt identity is invalid or already recorded')
    for key in ('host_sha256', 'job_sha256', 'request_sha256'):
        _sha(payload[key])
    start, end = _seconds(payload['not_before_utc']), _seconds(payload['expires_utc'])
    if not start <= at < end or not 0 < end - start <= 60:
        raise ValueError('bounded, currently valid intent window required')
    token, instance = payload['launch_token'], payload['instance_id']
    matches = [row for row in state.active_instances if row.charge.launch_token == token]
    if len(matches) != 1 or matches[0].charge.instance_id != instance or instance is None:
        raise ValueError('intent is not bound to the exact active instance')
    # Both changes are computed before the single intent record is committed.
    candidate = state.apply('budget.v2.game_admitted', {'game_id': payload['game_id'],
        'pair_id': payload['pair_id'], 'launch_token': token}, at)
    candidate = candidate.apply('budget.v2.game_release_authorized',
        {'game_id': payload['game_id'], 'valid_until_utc': end}, at)
    # Defensive exact check: whole-second timestamps avoid float rounding of
    # the elapsed interval. Costs remain Decimal, including minimum charges.
    if projected_upper_micros(candidate, end) >= 120_000_000:
        raise ValueError('shared upper estimate reaches the limit in the intent window')
    attempts.add(payload['attempt_id'])
    return candidate


def replay(root, events, expected_head):
    """Validate a complete supplied history; hashes do not authenticate it."""
    head, state = _root(root)
    if not isinstance(events, list) or len(events) > 100_000:
        raise ValueError('bounded complete event list required')
    attempts = set()
    for event in events:
        if not isinstance(event, dict) or set(event) != {'revision', 'previous_sha256', 'at', 'kind', 'payload', 'sha256'}:
            raise ValueError('invalid event fields')
        if type(event['revision']) is not int or event['revision'] != head['revision'] + 1 or event['previous_sha256'] != head['sha256']:
            raise ValueError('event history is not contiguous')
        at = _seconds(event['at'])
        core = {key: event[key] for key in ('revision', 'previous_sha256', 'at', 'kind', 'payload')}
        if event['sha256'] != _hash(b'rove4k-budget-event\0', core):
            raise ValueError('event digest differs')
        state = _apply(state, event['kind'], event['payload'], at, attempts)
        head = {'revision': event['revision'], 'sha256': event['sha256']}
    if _canonical(head) != _canonical(expected_head):
        raise ValueError('complete history and expected head differ')
    return state, attempts


class TrialWriter:
    """One client of an injected compare-and-append store; never GO authority.

    Store.read() returns root, complete events, head. Store.compare_append()
    must atomically append only if the exact head still matches and return the
    exact new head as an acknowledgement. Only an
    explicit Conflict denotes a known no-write; all other exceptions quarantine
    this writer. Neither the injected store nor this guarantee is audited here.
    """
    provides_go_authority = False

    def __init__(self, store, trusted_root):
        trusted_root = json.loads(_canonical(trusted_root))
        _root(trusted_root)
        self.store = store
        self.root = trusted_root
        self.uncertain = False
        self._lock = threading.Lock()

    def append(self, kind, payload, *, at):
        at = _seconds(at)
        with self._lock:
            if self.uncertain:
                raise Uncertain('prior write outcome is unresolved')
            # Validate and store the same detached, plain-JSON snapshot. In
            # particular, an overridable __deepcopy__ must not replace a
            # previously validated intent when constructing the event.
            payload = json.loads(_canonical(payload))
            root, events, head = self.store.read()
            root, events, head = json.loads(_canonical([root, events, head]))
            if _canonical(root) != _canonical(self.root):
                raise ValueError('store root differs')
            state, attempts = replay(root, events, head)
            _apply(state, kind, payload, at, attempts)
            core = {'revision': head['revision'] + 1, 'previous_sha256': head['sha256'],
                    'at': at, 'kind': kind, 'payload': payload}
            event = {**core, 'sha256': _hash(b'rove4k-budget-event\0', core)}
            new_head = {'revision': event['revision'], 'sha256': event['sha256']}
            replay(root, events + [event], new_head)
            try:
                acknowledgement = self.store.compare_append(copy.deepcopy(head), copy.deepcopy(event), copy.deepcopy(new_head))
                if _canonical(acknowledgement) != _canonical(new_head):
                    raise ValueError('append acknowledgement differs')
            except Conflict:
                raise
            except Exception as error:
                self.uncertain = True
                raise Uncertain('conditional write may have committed; do not retry') from error
            return {'head': new_head, 'authorizes_go': False, 'authorizes_launch': False,
                    'authorizes_termination': False}
