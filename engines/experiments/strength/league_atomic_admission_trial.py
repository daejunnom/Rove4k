"""Pure model of a combined two-host budget/epoch admission transaction.

This module creates data only: it does not contact DynamoDB, authenticate any
input, own a clock or journal, fence a recipient, or authorize a game.  Its
schema is intentionally separate from the existing diagnostic table schemas.
The caller must persist and reconcile write outcomes before using any model in
a real service. This model does not replay epoch/owner/mode history from an
independent root; a diagnostic drain record alone does not supply that proof.
A DynamoDB commit cannot atomically send a socket command.
"""
from __future__ import annotations

import json
import re

try:
    from . import league_budget_writer_trial as budget
except ImportError:
    import league_budget_writer_trial as budget


_HEAD_FIELDS = frozenset({'campaign', 'generation', 'epoch', 'revision', 'owner',
                          'mode', 'budget_revision', 'budget_sha256',
                          'budget_upper_micros', 'observed_at'})
_HEAD_KEY = 'atomic-trial#head'
_PREFIX = 'atomic-trial#'
_MAX_REVISION = 2**63 - 1
_CAP = 120_000_000
_MAX_EVENT_BYTES = 64 * 1024
_TABLE = re.compile(r'[A-Za-z0-9_.-]{3,255}\Z')
_OBSERVATION_EVENTS = frozenset({'budget.v2.observe', 'budget.v2.ancillary_charge',
                                  'budget.v2.limit_confirmed'})
_LIFECYCLE_EVENTS = frozenset({'budget.v2.launch_requested', 'budget.v2.instance_bound',
                                'budget.v2.launch_absent', 'budget.v2.instance_observed',
                                'budget.v2.game_release_observed', 'budget.v2.game_settled',
                                'budget.v2.terminate_requested'})


def _detached(value):
    return json.loads(budget._canonical(value))


def _nonnegative(value, name):
    if type(value) is not int or not 0 <= value <= _MAX_REVISION:
        raise ValueError(name + ' must be a bounded nonnegative integer')
    return value


def _head(root, events, head, *, at, write_state, owner_context):
    """Replay the supplied complete history and validate the exact head.

    ``write_state`` is an explicit local model state, not proof that another
    writer or a previous transport is settled.  Quarantine cannot be cleared
    by this module.
    """
    if write_state != 'clean':
        raise ValueError('uncertain or in-flight write blocks new transactions')
    root, events, head, owner_context = _detached([root, events, head, owner_context])
    if not isinstance(head, dict) or set(head) != _HEAD_FIELDS:
        raise ValueError('exact atomic admission head required')
    budget._root(root)
    if head['campaign'] != root['campaign']:
        raise ValueError('campaign and budget root differ')
    for name in ('generation', 'owner', 'budget_sha256'):
        budget._sha(head[name])
    for name in ('epoch', 'revision', 'budget_revision', 'budget_upper_micros'):
        _nonnegative(head[name], name)
    if head['mode'] not in ('active', 'draining'):
        raise ValueError('unknown head mode')
    if not isinstance(owner_context, dict) or set(owner_context) != {'generation', 'epoch', 'owner'}:
        raise ValueError('explicit model owner context required')
    _nonnegative(owner_context['epoch'], 'owner epoch')
    for name in ('generation', 'owner'):
        budget._sha(owner_context[name])
    if owner_context != {name: head[name] for name in ('generation', 'epoch', 'owner')}:
        raise ValueError('head differs from the explicit model owner context')
    at = budget._seconds(at)
    if type(head['observed_at']) is not int or head['observed_at'] != at:
        raise ValueError('budget observation must match the proposed event second')
    budget_head = {'revision': head['budget_revision'], 'sha256': head['budget_sha256']}
    state, attempts = budget.replay(root, events, budget_head)
    if budget.projected_upper_micros(state, at) != head['budget_upper_micros']:
        raise ValueError('budget upper bound differs from complete replay')
    return root, events, head, state, attempts, at


def _s(value):
    return {'S': value}


def _n(value):
    return {'N': str(value)}


def _key(campaign, record):
    return {'campaign_id': _s(campaign), 'record_id': _s(record)}


def _condition(head):
    names = {'#gen': 'generation', '#epoch': 'epoch', '#rev': 'revision',
             '#owner': 'owner', '#mode': 'mode', '#br': 'budget_revision',
             '#bh': 'budget_sha256', '#upper': 'budget_upper_micros',
             '#at': 'observed_at'}
    values = {':gen': _s(head['generation']), ':epoch': _n(head['epoch']),
              ':rev': _n(head['revision']), ':owner': _s(head['owner']),
              ':mode': _s(head['mode']), ':br': _n(head['budget_revision']),
              ':bh': _s(head['budget_sha256']), ':upper': _n(head['budget_upper_micros']),
              ':at': _n(head['observed_at'])}
    expression = ('#gen = :gen AND #epoch = :epoch AND #rev = :rev AND '
                  '#owner = :owner AND #mode = :mode AND #br = :br AND '
                  '#bh = :bh AND #upper = :upper AND #at = :at')
    return names, values, expression


def _scope(**fields):
    return {'authorizes_go': False, 'authorizes_launch': False,
            'authorizes_termination': False, 'inputs_authenticated': False,
            'write_performed': False, 'recipient_fenced': False,
            'global_history_replayable': False, 'ddb_item_size_verified': False, **fields}


def propose_admission(table, root, events, head, payload, *, at, write_state, owner_context):
    """Return one proposed DDB transaction for a diagnostic admission model.

    The cost calculation, including both active hosts and the release window,
    reuses the existing exact rational budget replay.  Unique attempt and game
    rows and the head compare/update are in the same requested transaction.
    ``table`` and all identity/time/price fields are untrusted model inputs.
    """
    if not isinstance(table, str) or _TABLE.fullmatch(table) is None:
        raise ValueError('explicit bounded model table name required')
    root, events, head, state, attempts, at = _head(
        root, events, head, at=at, write_state=write_state, owner_context=owner_context)
    if head['mode'] != 'active' or state.draining or head['budget_upper_micros'] >= _CAP:
        raise ValueError('draining or exhausted campaign cannot admit a game')
    if head['revision'] >= _MAX_REVISION - 1 or head['budget_revision'] >= _MAX_REVISION - 1:
        raise ValueError('revision must leave room to close starts')
    payload = _detached(payload)
    budget._apply(state, 'intent', payload, at, attempts)
    core = {'revision': head['budget_revision'] + 1, 'previous_sha256': head['budget_sha256'],
            'at': at, 'kind': 'intent', 'payload': payload}
    event = {**core, 'sha256': budget._hash(b'rove4k-budget-event\0', core)}
    if len(budget._canonical(event)) > _MAX_EVENT_BYTES:
        raise ValueError('model event exceeds the bounded body limit')
    next_budget = {'revision': event['revision'], 'sha256': event['sha256']}
    # Replay again to check exactly the event that will be written, rather
    # than trusting the detached proposal or a caller-provided projection.
    after, _ = budget.replay(root, events + [event], next_budget)
    projected = budget.projected_upper_micros(after, payload['expires_utc'])
    if projected >= _CAP:
        raise ValueError('two-host upper bound reaches the cap in the start window')
    names, values, condition = _condition(head)
    values.update({':next': _n(head['revision'] + 1), ':br_next': _n(event['revision']),
                   ':bh_next': _s(event['sha256'])})
    unique = 'attribute_not_exists(campaign_id) AND attribute_not_exists(record_id)'
    campaign = head['campaign']
    body = budget._canonical(event).decode('ascii')
    item = {**_key(campaign, _PREFIX + 'event#' + str(event['revision']).zfill(20)),
            'body': _s(body)}
    index = {'event_sha256': _s(event['sha256']), 'generation': _s(head['generation']),
             'epoch': _n(head['epoch']), 'revision': _n(head['revision'] + 1)}
    attempt = {**_key(campaign, _PREFIX + 'attempt#' + payload['attempt_id']), **index}
    game = {**_key(campaign, _PREFIX + 'game#' + payload['game_id']), **index}
    transaction = {'TransactItems': [
        {'Update': {'TableName': table, 'Key': _key(campaign, _HEAD_KEY),
                    'UpdateExpression': 'SET #rev = :next, #br = :br_next, #bh = :bh_next',
                    'ConditionExpression': condition, 'ExpressionAttributeNames': names,
                    'ExpressionAttributeValues': values}},
        *[{'Put': {'TableName': table, 'Item': row, 'ConditionExpression': unique}}
          for row in (item, attempt, game)],
    ]}
    next_head = {**head, 'revision': head['revision'] + 1,
                 'budget_revision': event['revision'], 'budget_sha256': event['sha256']}
    return _scope(transaction=transaction, event=event, next_head=next_head,
                  projected_upper_micros=projected, write_state='in_flight')


def propose_drain(table, root, events, head, *, at, write_state, owner_context):
    """Propose closing starts without changing or settling existing games.

    A stale budget observation can still be used to close starts.  The prior
    head is replayed at its recorded time and compared in the transaction;
    the drain timestamp may advance but cannot precede that observation.
    Neither this closure nor its supplied time authenticates a remote owner.
    """
    if not isinstance(table, str) or _TABLE.fullmatch(table) is None:
        raise ValueError('explicit bounded model table name required')
    if not isinstance(head, dict) or type(head.get('observed_at')) is not int:
        raise ValueError('prior observation timestamp required')
    _, _, head, _, _, _ = _head(
        root, events, head, at=head['observed_at'], write_state=write_state, owner_context=owner_context)
    at = budget._seconds(at)
    if at < head['observed_at']:
        raise ValueError('drain time precedes the prior budget observation')
    if head['mode'] != 'active':
        raise ValueError('only an active head can be drained')
    if head['revision'] >= _MAX_REVISION:
        raise ValueError('drain revision is exhausted')
    names, values, condition = _condition(head)
    values.update({':next': _n(head['revision'] + 1), ':drain': _s('draining')})
    record = {'kind': 'drain', 'previous_head': head, 'at': at,
              'next_revision': head['revision'] + 1}
    record_hash = budget._hash(b'rove4k-atomic-drain\0', record)
    record_item = {**_key(head['campaign'], _PREFIX + 'drain#' + str(head['revision'] + 1).zfill(20)),
                   'body': _s(budget._canonical(record).decode('ascii')),
                   'sha256': _s(record_hash)}
    transaction = {'TransactItems': [{'Update': {'TableName': table,
        'Key': _key(head['campaign'], _HEAD_KEY),
        'UpdateExpression': 'SET #rev = :next, #mode = :drain',
        'ConditionExpression': condition, 'ExpressionAttributeNames': names,
        'ExpressionAttributeValues': values}},
        {'Put': {'TableName': table, 'Item': record_item,
                 'ConditionExpression': 'attribute_not_exists(campaign_id) AND attribute_not_exists(record_id)'}}]}
    return _scope(transaction=transaction, drain_record_sha256=record_hash,
                  next_head={**head, 'revision': head['revision'] + 1, 'mode': 'draining'},
                  write_state='in_flight')


def propose_budget_observation(table, root, events, head, event_name, data, *, at,
                               write_state, owner_context):
    """Propose one replayed budget observation or lifecycle record.

    This model requires an exact prior head and monotonically increasing
    observation seconds; distinct lifecycle records can share a second.
    Reaching the cap changes mode to draining in the *same* transaction as the
    budget event. Lifecycle evidence remains untrusted and does not authorize
    launch, GO, termination, or resolve an uncertain prior write.
    """
    if not isinstance(table, str) or _TABLE.fullmatch(table) is None:
        raise ValueError('explicit bounded model table name required')
    if not isinstance(head, dict) or type(head.get('observed_at')) is not int:
        raise ValueError('prior observation timestamp required')
    root, events, head, state, attempts, old_at = _head(
        root, events, head, at=head['observed_at'], write_state=write_state,
        owner_context=owner_context)
    at = budget._seconds(at)
    if event_name not in _OBSERVATION_EVENTS | _LIFECYCLE_EVENTS:
        raise ValueError('unsupported model observation event')
    if at < old_at or (event_name in _OBSERVATION_EVENTS and at == old_at):
        raise ValueError('new observation time must advance')
    if event_name == 'budget.v2.launch_requested' and head['mode'] != 'active':
        raise ValueError('draining campaign cannot request a new launch')
    if head['revision'] >= _MAX_REVISION or head['budget_revision'] >= _MAX_REVISION:
        raise ValueError('revision is exhausted')
    payload = _detached({'event': event_name, 'data': data})
    if not isinstance(payload['data'], dict):
        raise ValueError('lifecycle data must be an object')
    if event_name == 'budget.v2.launch_requested' and any(
            row.charge.launch_token == payload['data'].get('launch_token') for row in state.instances):
        raise ValueError('launch token already recorded; reconcile before retry')
    if event_name in ('budget.v2.game_release_observed', 'budget.v2.game_settled'):
        matches = [game for game in state.games if game.game_id == payload['data'].get('game_id')]
        if len(matches) == 1 and (matches[0].settled or
                (event_name == 'budget.v2.game_release_observed' and matches[0].release_observed)):
            raise ValueError('game lifecycle record already applied')
    if event_name == 'budget.v2.terminate_requested' and any(
            entry['kind'] == 'budget' and entry['payload']['event'] == event_name and
            entry['payload']['data'].get('launch_token') == payload['data'].get('launch_token')
            for entry in events):
        raise ValueError('termination request already recorded')
    evidence = payload['data'].get('evidence')
    observation_id = evidence.get('observation_id') if isinstance(evidence, dict) else None
    if observation_id is not None:
        if not isinstance(observation_id, str) or not 1 <= len(observation_id) <= 256:
            raise ValueError('bounded observation identity required')
        for entry in events:
            prior_data = entry['payload'].get('data') if entry['kind'] == 'budget' else None
            prior_evidence = prior_data.get('evidence') if isinstance(prior_data, dict) else None
            if isinstance(prior_evidence, dict) and prior_evidence.get('observation_id') == observation_id:
                raise ValueError('observation identity already recorded')
    budget._apply(state, 'budget', payload, at, attempts)
    core = {'revision': head['budget_revision'] + 1, 'previous_sha256': head['budget_sha256'],
            'at': at, 'kind': 'budget', 'payload': payload}
    event = {**core, 'sha256': budget._hash(b'rove4k-budget-event\0', core)}
    if len(budget._canonical(event)) > _MAX_EVENT_BYTES:
        raise ValueError('model event exceeds the bounded body limit')
    after, _ = budget.replay(root, events + [event],
                             {'revision': event['revision'], 'sha256': event['sha256']})
    upper = budget.projected_upper_micros(after, at)
    mode = 'draining' if head['mode'] == 'draining' or after.draining or upper >= _CAP else 'active'
    if mode == 'active' and (head['revision'] >= _MAX_REVISION - 1
                             or head['budget_revision'] >= _MAX_REVISION - 1):
        raise ValueError('revision must leave room to close starts')
    names, values, condition = _condition(head)
    values.update({':next': _n(head['revision'] + 1), ':br_next': _n(event['revision']),
                   ':bh_next': _s(event['sha256']), ':new_at': _n(at),
                   ':new_upper': _n(upper), ':new_mode': _s(mode)})
    item = {**_key(head['campaign'], _PREFIX + 'event#' + str(event['revision']).zfill(20)),
            'body': _s(budget._canonical(event).decode('ascii'))}
    unique = 'attribute_not_exists(campaign_id) AND attribute_not_exists(record_id)'
    transaction = {'TransactItems': [
        {'Update': {'TableName': table, 'Key': _key(head['campaign'], _HEAD_KEY),
                    'UpdateExpression': ('SET #rev = :next, #br = :br_next, #bh = :bh_next, '
                                         '#at = :new_at, #upper = :new_upper, #mode = :new_mode'),
                    'ConditionExpression': condition, 'ExpressionAttributeNames': names,
                    'ExpressionAttributeValues': values}},
        {'Put': {'TableName': table, 'Item': item, 'ConditionExpression': unique}},
    ]}
    if observation_id is not None:
        observation_hash = budget._hash(b'rove4k-atomic-observation\0', {'id': observation_id})
        index = {**_key(head['campaign'], _PREFIX + 'observation#' + observation_hash),
                 'event_sha256': _s(event['sha256'])}
        transaction['TransactItems'].append({'Put': {'TableName': table, 'Item': index,
                                                       'ConditionExpression': unique}})
    next_head = {**head, 'revision': head['revision'] + 1, 'budget_revision': event['revision'],
                 'budget_sha256': event['sha256'], 'observed_at': at,
                 'budget_upper_micros': upper, 'mode': mode}
    return _scope(transaction=transaction, event=event, next_head=next_head,
                  write_state='in_flight')


def resolve_model_write(write_state, outcome):
    """Model a write outcome; uncertainty cannot be cleared here.

    The caller's report is not verified and no durable quarantine is created.
    Explicit no-write and exact commit evidence must be established elsewhere.
    """
    if write_state != 'in_flight':
        raise ValueError('an in-flight model transaction is required')
    if outcome in ('verified_commit', 'verified_no_write'):
        return _scope(write_state='clean', outcome=outcome)
    return _scope(write_state='quarantined', outcome='unknown')
