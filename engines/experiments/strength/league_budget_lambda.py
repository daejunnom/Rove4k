"""Diagnostic-only serialized budget writer for an isolated DDB namespace.

The history uses the same DynamoRepository conditional transaction as the
existing writer, but an inaccessible-to-v2 partition suffix and its own
durable gate.  Caller-supplied observations and the local clock are not
authenticated, the history has no independent anchor, and remote ownership
and physical settlement are not proven.  This code grants no GO, launch or
termination authority and must not be deployed as an authorization service.
Every attempted transaction keeps the gate busy across Lambda restarts until
an explicit matching read-only reconciliation. There is no automatic retry.
Reconciliation checks only this store's self-consistency; its caller and
history are not authenticated or independently anchored.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time

try:
    from . import league_budget_writer_trial as history
    from .league_budget_writer_bridge_trial import TrialTransactionBridge
    from .league_writer_lambda import DynamoRepository
except ImportError:
    import league_budget_writer_trial as history
    from league_budget_writer_bridge_trial import TrialTransactionBridge
    from league_writer_lambda import DynamoRepository


_TABLE_ARN = re.compile(r'arn:aws(?:-us-gov|-cn)?:dynamodb:([a-z0-9-]+):[0-9]{12}:table/[A-Za-z0-9_.-]{3,255}\Z')
_REQUEST_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')
_SUFFIX = '#budget-v3'
_GUARD = 'gate'


class Quarantined(RuntimeError):
    """An operation may have happened; do not retry without reconciliation."""


def _copy(value):
    return json.loads(history._canonical(value))


class IsolatedRepository:
    """Map the restricted campaign to a distinct physical DDB partition.

    The '#' suffix cannot occur in a valid campaign ID accepted by either
    writer. No v2 campaign can therefore address this history partition.
    Existing writers and tables remain unchanged. This is key isolation, not
    IAM isolation or proof against a privileged DDB client.
    """

    def __init__(self, repository, root):
        if not isinstance(repository, DynamoRepository):
            raise TypeError('actual DynamoRepository required')
        root = _copy(root)
        history._root(root)
        self.repo, self.campaign = repository, root['campaign']
        self.physical = self.campaign + _SUFFIX
        self.guard_partition = self.physical + '#gate'

    def _check(self, campaign):
        if campaign != self.campaign:
            raise ValueError('campaign differs from pinned root')

    def bootstrap_v2(self, campaign, head):
        self._check(campaign)
        return self.repo.bootstrap_v2(self.physical, head)

    def read_v2_snapshot(self, campaign):
        self._check(campaign)
        before, rows, after = self.repo.read_v2_snapshot(self.physical)
        mapped = []
        for row in rows:
            if row.get('campaign_id') != self.physical:
                raise ValueError('physical partition differs')
            mapped.append({**row, 'campaign_id': self.campaign})
        return before, mapped, after

    def append_v2(self, campaign, old, new, event, indexes):
        self._check(campaign)
        return self.repo.append_v2(self.physical, old, new, event, indexes)

    def _key(self):
        return self.repo._wire({'campaign_id': self.guard_partition, 'record_id': _GUARD})

    def initialize_gate(self):
        return self.repo.client.put_item(TableName=self.repo.table,
            Item=self.repo._wire({'campaign_id': self.guard_partition, 'record_id': _GUARD,
                                  'state': 'busy', 'owner': 'bootstrap'}),
            ConditionExpression='attribute_not_exists(#pk) AND attribute_not_exists(#sk)',
            ExpressionAttributeNames={'#pk': 'campaign_id', '#sk': 'record_id'})

    def acquire(self, owner):
        return self.repo.client.update_item(TableName=self.repo.table, Key=self._key(),
            UpdateExpression='SET #state = :busy, #owner = :owner',
            ConditionExpression='#state = :idle',
            ExpressionAttributeNames={'#state': 'state', '#owner': 'owner'},
            ExpressionAttributeValues=self.repo._wire({':busy': 'busy', ':idle': 'idle', ':owner': owner}))

    def release(self, owner):
        return self.repo.client.update_item(TableName=self.repo.table, Key=self._key(),
            UpdateExpression='SET #state = :idle',
            ConditionExpression='#state = :busy AND #owner = :owner',
            ExpressionAttributeNames={'#state': 'state', '#owner': 'owner'},
            ExpressionAttributeValues=self.repo._wire({':busy': 'busy', ':idle': 'idle', ':owner': owner}))


def _scope(state, **extra):
    return {'state': state, 'authorizes_go': False, 'authorizes_launch': False,
            'authorizes_termination': False, 'authenticated_budget': False,
            'authenticated_clock': False, 'independent_anchor': False, **extra}


def execute(request, root, repository, *, now):
    """Execute one diagnostic event; ambiguous writes retain the durable gate.

    ``now`` is a server-supplied integral UTC second, not an authenticated
    clock.  No request field selects a root, table, partition or timestamp.
    This service accepts untrusted diagnostic observations only; production
    callers must not treat the result as physical or financial evidence.
    """
    root, request = _copy(root), _copy(request)
    initial, _ = history._root(root)
    if (not isinstance(request, dict) or set(request) != {'kind', 'payload', 'expected_head', 'request_id'}
            or not isinstance(request['request_id'], str) or not _REQUEST_ID.fullmatch(request['request_id'])):
        raise ValueError('exact request fields and bounded request identity required')
    now = history._seconds(now)
    isolated = IsolatedRepository(repository, root)
    kind = request['kind']
    if kind == 'bootstrap':
        if request['payload'] != {} or request['expected_head'] is not None:
            raise ValueError('bootstrap cannot choose a root or head')
        try:
            isolated.initialize_gate()
            isolated.bootstrap_v2(root['campaign'], initial)
        except Exception as error:
            raise Quarantined('bootstrap outcome is unresolved; do not retry automatically') from error
        return _scope('diagnostic-bootstrap-pending-reconciliation', head=initial)
    if kind == 'reconcile_bootstrap':
        if request['payload'] != {} or history._canonical(request['expected_head']) != history._canonical(initial):
            raise ValueError('bootstrap reconciliation requires the pinned initial head')
        bridge = TrialTransactionBridge(isolated, root)
        _, events, head = bridge.read()
        if events or history._canonical(head) != history._canonical(initial):
            raise ValueError('bootstrap history differs from the pinned root')
        try:
            isolated.release('bootstrap')
        except Exception as error:
            raise Quarantined('bootstrap reconciliation release outcome unknown') from error
        return _scope('diagnostic-bootstrap-reconciled', head=head)
    if kind == 'reconcile':
        # This operation grants no authority: its caller, root and replayed
        # history are not authenticated or independently anchored.
        payload = request['payload']
        if not isinstance(payload, dict) or set(payload) != {'original', 'event_sha256'}:
            raise ValueError('reconciliation requires original request and event digest')
        original = payload['original']
        if (not isinstance(original, dict) or set(original) != {'kind', 'payload', 'expected_head', 'request_id'}
                or original['kind'] not in ('budget', 'intent') or not isinstance(original['payload'], dict)
                or not isinstance(original['request_id'], str) or not _REQUEST_ID.fullmatch(original['request_id'])
                or not isinstance(original['expected_head'], dict)
                or set(original['expected_head']) != {'revision', 'sha256'}):
            raise ValueError('exact original request required')
        history._sha(payload['event_sha256'])
        bridge = TrialTransactionBridge(isolated, root)
        _, events, head = bridge.read()
        if not events or history._canonical(head) != history._canonical(request['expected_head']):
            raise ValueError('current head differs from reconciliation')
        last = events[-1]
        expected = original['expected_head']
        if (type(expected['revision']) is not int or last['revision'] != expected['revision'] + 1
                or last['previous_sha256'] != expected['sha256'] or last['kind'] != original['kind']
                or history._canonical(last['payload']) != history._canonical(original['payload'])
                or last['sha256'] != payload['event_sha256'] or head['sha256'] != payload['event_sha256']):
            raise ValueError('committed event does not match the original request')
        owner = hashlib.sha256(history._canonical({'root': root, 'request': original})).hexdigest()
        try:
            isolated.release(owner)
        except Exception as error:
            raise Quarantined('reconciliation release outcome unknown') from error
        return _scope('diagnostic-reconciled', head=head, event_sha256=last['sha256'])
    if kind not in ('budget', 'intent') or not isinstance(request['payload'], dict):
        raise ValueError('only diagnostic budget and intent records are supported')
    head = request['expected_head']
    if not isinstance(head, dict) or set(head) != {'revision', 'sha256'}:
        raise ValueError('exact expected head required')
    owner = hashlib.sha256(history._canonical({'root': root, 'request': request})).hexdigest()
    try:
        isolated.acquire(owner)
    except Exception as error:
        raise Quarantined('gate unavailable or acquisition outcome unknown; do not retry') from error
    bridge = TrialTransactionBridge(isolated, root)
    wrote = False
    try:
        observed_root, events, before = bridge.read()
        if history._canonical(observed_root) != history._canonical(root) or history._canonical(before) != history._canonical(head):
            raise ValueError('expected history head differs')
        state, attempts = history.replay(root, events, before)
        payload = _copy(request['payload'])
        history._apply(state, kind, payload, now, attempts)
        core = {'revision': before['revision'] + 1, 'previous_sha256': before['sha256'],
                'at': now, 'kind': kind, 'payload': payload}
        event = {**core, 'sha256': history._hash(b'rove4k-budget-event\0', core)}
        after = {'revision': event['revision'], 'sha256': event['sha256']}
        history.replay(root, events + [event], after)
        # Mark before issuing I/O: even a timeout after a commit is unknown.
        wrote = True
        bridge.compare_append(before, event, after)
    except Exception as error:
        if wrote:
            raise Quarantined('transaction outcome unknown; gate remains busy') from error
        # A read or validation failure has not issued a transaction; release
        # only this exact owner. Unknown release leaves reconciliation needed.
        try:
            isolated.release(owner)
        except Exception as release_error:
            raise Quarantined('gate release outcome unknown') from release_error
        raise
    # Even the Lambda response can be lost after the DDB transaction returns.
    # Retain the gate until an explicit replay confirms this exact event.
    return _scope('diagnostic-committed-pending-reconciliation', head=after,
                  event_sha256=event['sha256'])


_runtime = None


def handler(event, context):
    """AWS Lambda entrypoint with environment-pinned root and table ARN."""
    global _runtime
    if _runtime is None:
        import boto3
        from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
        from botocore.config import Config
        root = _copy(json.loads(os.environ['ROVE_BUDGET_DIAGNOSTIC_ROOT_JSON']))
        history._root(root)
        table = os.environ['ROVE_BUDGET_DIAGNOSTIC_TABLE_ARN']
        match = _TABLE_ARN.fullmatch(table)
        if match is None or match.group(1) != os.environ['AWS_REGION']:
            raise ValueError('full same-region DynamoDB table ARN required')
        client = boto3.client('dynamodb', config=Config(retries={'total_max_attempts': 1},
                                                       connect_timeout=5, read_timeout=10))
        _runtime = (root, DynamoRepository(client, table, TypeSerializer(), TypeDeserializer()))
    return execute(event, _runtime[0], _runtime[1], now=int(time.time()))
