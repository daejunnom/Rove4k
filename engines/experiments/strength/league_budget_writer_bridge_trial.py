"""Trial adapter to the existing DDB-shaped conditional transaction API.

Test this only with a fake Dynamo client and a dedicated isolated table.  This
uses the diagnostic writer's v2 physical namespace but different root and
event schemas, so it MUST NOT share a table/campaign with the diagnostic v2
writer. The pinned root here is caller-supplied and not authenticated. This
module does not configure AWS, grant GO or launch authority, or reconcile
unknown responses. It is not wired into Lambda, CI release or a live host.
"""
from __future__ import annotations

import copy
import json

try:
    from . import league_budget_writer_trial as trial
    from . import league_writer_lambda as diagnostic
except ImportError:
    import league_budget_writer_trial as trial
    import league_writer_lambda as diagnostic


def _indexes(event):
    if event['kind'] != 'intent':
        return {}
    payload = event['payload']
    record = {'event_sha256': event['sha256'], 'revision': event['revision']}
    return {diagnostic.PREFIX + 'attempt#' + payload['attempt_id']: record,
            diagnostic.PREFIX + 'subject#go#' + payload['game_id']: record}


class TrialTransactionBridge:
    """Use DynamoRepository's exact snapshot and transaction interfaces.

    The caller must ensure a dedicated isolated trial table; no IAM, table
    identity or exclusivity can be proven by this object. No exceptions are
    downgraded to Conflict: any transport or transaction error is uncertain
    to TrialWriter and must not be automatically retried.
    """
    provides_go_authority = False

    def __init__(self, repository, root):
        root = json.loads(trial._canonical(root))
        trial._root(root)
        if not callable(getattr(repository, 'read_v2_snapshot', None)) or not callable(getattr(repository, 'append_v2', None)):
            raise ValueError('diagnostic transaction repository required')
        self.repository, self.root = repository, root

    def read(self):
        campaign = self.root['campaign']
        before, rows, after = self.repository.read_v2_snapshot(campaign)
        if trial._canonical(before) != trial._canonical(after) or not isinstance(rows, list):
            raise ValueError('snapshot changed while reading')
        bodies = {}
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {'campaign_id', 'record_id', 'body'}
                    or row['campaign_id'] != campaign or not isinstance(row['record_id'], str)
                    or not row['record_id'].startswith(diagnostic.PREFIX) or row['record_id'] in bodies):
                raise ValueError('invalid snapshot row')
            bodies[row['record_id']] = diagnostic._decode(row['body'])
        if diagnostic.HEAD not in bodies or trial._canonical(bodies[diagnostic.HEAD]) != trial._canonical(before):
            raise ValueError('queried and consistent HEAD differ')
        revision = before.get('revision') if isinstance(before, dict) else None
        if type(revision) is not int or not 0 <= revision <= 100_000:
            raise ValueError('invalid trial revision')
        try:
            events = [bodies[diagnostic._event_key(i)] for i in range(1, revision + 1)]
        except KeyError as error:
            raise ValueError('trial history is incomplete') from error
        trial.replay(self.root, events, before)
        expected = {diagnostic.HEAD: before}
        for event in events:
            expected[diagnostic._event_key(event['revision'])] = event
            for key, value in _indexes(event).items():
                if key in expected:
                    raise ValueError('duplicate trial index')
                expected[key] = value
        if trial._canonical(bodies) != trial._canonical(expected):
            raise ValueError('trial indexes or complete row set differ')
        return copy.deepcopy((self.root, events, before))

    def compare_append(self, old, event, new):
        # The existing repository conditions the exact old HEAD, makes the
        # event and both indexes unique, and writes all in one transaction.
        response = self.repository.append_v2(self.root['campaign'], old, new, event, _indexes(event))
        if not isinstance(response, dict):
            raise ValueError('transaction acknowledgement is malformed')
        return copy.deepcopy(new)
