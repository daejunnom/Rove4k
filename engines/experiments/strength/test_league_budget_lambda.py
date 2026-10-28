"""Dedicated writer handler contract exercised only with a fake DDB client."""
import copy
import json
import os
import sys
import threading
import types
import unittest
from unittest.mock import patch

try:
    from . import league_budget_lambda as handler
    from . import league_budget_writer_trial as trial
    from . import league_budget_writer_bridge_trial as bridge
    from . import league_writer_lambda as diagnostic
    from .test_league_writer_lambda import Dynamo
except ImportError:
    import league_budget_lambda as handler
    import league_budget_writer_trial as trial
    import league_budget_writer_bridge_trial as bridge
    import league_writer_lambda as diagnostic
    from test_league_writer_lambda import Dynamo


class PartitionedDynamo(Dynamo):
    """Small partition-aware DDB double with conditional gate updates."""
    def __init__(self, root):
        super().__init__(root)
        self.rows = {}
        self.fail_gate_release = False
        self.fail_bootstrap_head = False
        self.fail_bootstrap_after_head = False

    def get_item(self, **request):
        assert request['ConsistentRead'] is True
        key = (request['Key']['campaign_id']['S'], request['Key']['record_id']['S'])
        return {'Item': copy.deepcopy(self.rows[key])} if key in self.rows else {}

    def get_paginator(self, name):
        assert name == 'query'
        client = self
        class Pager:
            def paginate(self, **request):
                assert request['ConsistentRead'] is True
                partition = request['ExpressionAttributeValues'][':pk']['S']
                prefix = request['ExpressionAttributeValues'][':prefix']['S']
                yield {'Items': [copy.deepcopy(row) for (pk, sk), row in sorted(client.rows.items())
                                 if pk == partition and sk.startswith(prefix)]}
        return Pager()

    def put_item(self, **request):
        row = request['Item']
        key = (row['campaign_id']['S'], row['record_id']['S'])
        if key in self.rows:
            raise ValueError('conditional duplicate')
        if key[1] == diagnostic.HEAD and self.fail_bootstrap_head:
            raise TimeoutError('head write outcome unknown')
        self.rows[key] = copy.deepcopy(row)
        if key[1] == diagnostic.HEAD and self.fail_bootstrap_after_head:
            raise TimeoutError('head acknowledgement lost')
        return {}

    def update_item(self, **request):
        key = (request['Key']['campaign_id']['S'], request['Key']['record_id']['S'])
        row = self.rows[key]
        values = request['ExpressionAttributeValues']
        condition = request['ConditionExpression']
        if condition == '#state = :idle':
            if row['state'] != values[':idle']:
                raise ValueError('gate busy')
            row['state'], row['owner'] = values[':busy'], values[':owner']
        elif condition == '#state = :busy AND #owner = :owner':
            if row['state'] != values[':busy'] or row['owner'] != values[':owner']:
                raise ValueError('gate owner mismatch')
            if self.fail_gate_release:
                raise TimeoutError('unknown gate release')
            row['state'] = values[':idle']
        else:
            raise AssertionError('unexpected update condition')
        return {}

    def transact_write_items(self, **request):
        self.transactions.append(copy.deepcopy(request))
        entries = request['TransactItems']
        update = entries[0]['Update']
        key = (update['Key']['campaign_id']['S'], update['Key']['record_id']['S'])
        if self.rows[key]['body'] != update['ExpressionAttributeValues'][':old']:
            raise ValueError('conditional head failure')
        staged = copy.deepcopy(self.rows)
        for entry in entries[1:]:
            row = entry['Put']['Item']
            put_key = (row['campaign_id']['S'], row['record_id']['S'])
            if put_key in staged:
                raise ValueError('conditional duplicate')
            staged[put_key] = copy.deepcopy(row)
        staged[key]['body'] = update['ExpressionAttributeValues'][':new']
        self.rows = staged
        if self.fail_after_commit:
            raise TimeoutError('response lost after transaction')
        return {}


class BudgetLambdaTests(unittest.TestCase):
    def setUp(self):
        self.root, _ = trial.genesis('league-test')
        self.client = PartitionedDynamo(self.root)
        self.repo = diagnostic.DynamoRepository(self.client, 'unit-only', self.client.codec, self.client.codec)
        self.isolated = handler.IsolatedRepository(self.repo, self.root)
        self.store = bridge.TrialTransactionBridge(self.isolated, self.root)
        self.sequence = 0
        result = handler.execute({'kind': 'bootstrap', 'payload': {}, 'expected_head': None,
                         'request_id': 'request-bootstrap'}, self.root, self.repo, now=1000)
        handler.execute({'kind': 'reconcile_bootstrap', 'payload': {}, 'expected_head': result['head'],
                         'request_id': 'request-bootstrap-reconcile'}, self.root, self.repo, now=1000)

    def request(self, kind, payload):
        _, _, head = self.store.read()
        self.sequence += 1
        return {'kind': kind, 'payload': payload, 'expected_head': head,
                'request_id': 'request-' + str(self.sequence)}

    def execute(self, kind, payload, now=1000):
        request = self.request(kind, payload)
        result = handler.execute(request, self.root, self.repo, now=now)
        self.reconcile(request, result, now=now)
        return result

    def reconcile(self, request, result, now=1000):
        self.sequence += 1
        return handler.execute({'kind': 'reconcile',
            'payload': {'original': request, 'event_sha256': result['event_sha256']},
            'expected_head': result['head'], 'request_id': 'reconcile-' + str(self.sequence)},
            self.root, self.repo, now=now)

    def budget(self, event, data, now=1000):
        return self.execute('budget', {'event': 'budget.v2.' + event, 'data': data}, now)

    def hosts(self):
        for token, instance in (('first-token', 'i-first'), ('other-token', 'i-other')):
            self.budget('launch_requested', {'launch_token': token, 'region': 'ap-southeast-2', 'max_hourly_usd': '8'})
            self.budget('instance_bound', {'launch_token': token, 'instance_id': instance})

    def intent(self, game='game-1', token='first-token', instance='i-first'):
        return {'attempt_id': 'attempt-' + game, 'game_id': game, 'pair_id': 'pair-' + game,
                'launch_token': token, 'instance_id': instance, 'host_sha256': 'a' * 64,
                'job_sha256': 'b' * 64, 'request_sha256': 'c' * 64,
                'not_before_utc': 1000, 'expires_utc': 1060}

    def test_intent_uses_one_conditional_transaction_and_grants_no_authority(self):
        self.hosts()
        result = self.execute('intent', self.intent())
        self.assertFalse(result['authorizes_go'])
        self.assertFalse(result['authorizes_launch'])
        self.assertFalse(result['authorizes_termination'])
        writes = self.client.transactions[-1]['TransactItems']
        self.assertEqual(len(writes), 4)
        self.assertEqual(writes[0]['Update']['ConditionExpression'], '#body = :old')
        self.assertTrue(all('attribute_not_exists' in item['Put']['ConditionExpression'] for item in writes[1:]))

    def test_bootstrap_response_loss_requires_explicit_reconcile(self):
        client = PartitionedDynamo(self.root)
        repo = diagnostic.DynamoRepository(client, 'unit-only', client.codec, client.codec)
        result = handler.execute({'kind': 'bootstrap', 'payload': {}, 'expected_head': None,
            'request_id': 'boot-first'}, self.root, repo, now=1000)
        self.assertEqual(result['state'], 'diagnostic-bootstrap-pending-reconciliation')
        pending = {'kind': 'budget', 'payload': {'event': 'budget.v2.observe', 'data': {}},
                   'expected_head': result['head'], 'request_id': 'req-other'}
        with self.assertRaises(handler.Quarantined):
            handler.execute(pending, self.root, repo, now=1000)
        with self.assertRaises(Exception):
            handler.execute({'kind': 'reconcile_bootstrap', 'payload': {},
                'expected_head': {'revision': 0, 'sha256': 'f' * 64},
                'request_id': 'wrong-head'}, self.root, repo, now=1000)
        receipt = handler.execute({'kind': 'reconcile_bootstrap', 'payload': {},
            'expected_head': result['head'], 'request_id': 'boot-reconcile'}, self.root, repo, now=1000)
        self.assertEqual(receipt['state'], 'diagnostic-bootstrap-reconciled')
        self.assertFalse(receipt['authorizes_go'])

    def test_incomplete_bootstrap_cannot_be_reconciled_or_retried(self):
        client = PartitionedDynamo(self.root)
        client.fail_bootstrap_head = True
        repo = diagnostic.DynamoRepository(client, 'unit-only', client.codec, client.codec)
        bootstrap = {'kind': 'bootstrap', 'payload': {}, 'expected_head': None, 'request_id': 'boot-first'}
        with self.assertRaises(handler.Quarantined):
            handler.execute(bootstrap, self.root, repo, now=1000)
        client.fail_bootstrap_head = False
        _, initial = trial.genesis('league-test')
        with self.assertRaises(Exception):
            handler.execute({'kind': 'reconcile_bootstrap', 'payload': {}, 'expected_head': initial,
                             'request_id': 'boot-reconcile'}, self.root, repo, now=1000)
        with self.assertRaises(handler.Quarantined):
            handler.execute(bootstrap, self.root, repo, now=1000)
        with self.assertRaises(handler.Quarantined):
            handler.execute({'kind': 'budget', 'payload': {'event': 'budget.v2.observe', 'data': {}},
                'expected_head': initial, 'request_id': 'req-other'}, self.root, repo, now=1000)

    def test_bootstrap_head_ack_loss_can_reconcile_only_after_complete_readback(self):
        client = PartitionedDynamo(self.root)
        client.fail_bootstrap_after_head = True
        repo = diagnostic.DynamoRepository(client, 'unit-only', client.codec, client.codec)
        with self.assertRaises(handler.Quarantined):
            handler.execute({'kind': 'bootstrap', 'payload': {}, 'expected_head': None,
                             'request_id': 'boot-first'}, self.root, repo, now=1000)
        client.fail_bootstrap_after_head = False
        isolated = handler.IsolatedRepository(repo, self.root)
        _, events, head = bridge.TrialTransactionBridge(isolated, self.root).read()
        self.assertEqual(events, [])
        receipt = handler.execute({'kind': 'reconcile_bootstrap', 'payload': {}, 'expected_head': head,
                                   'request_id': 'boot-reconcile'}, self.root, repo, now=1000)
        self.assertEqual(receipt['state'], 'diagnostic-bootstrap-reconciled')
        self.assertFalse(receipt['authorizes_go'])

    def test_stale_head_rejects_without_writing(self):
        self.hosts()
        stale = self.request('intent', self.intent())
        self.budget('observe', {})
        count = len(self.client.transactions)
        with self.assertRaises(ValueError):
            handler.execute(stale, self.root, self.repo, now=1000)
        self.assertEqual(len(self.client.transactions), count)

    def test_request_cannot_choose_clock_or_extra_fields(self):
        self.hosts()
        request = self.request('intent', self.intent())
        request['now'] = 1000
        with self.assertRaises(ValueError):
            handler.execute(request, self.root, self.repo, now=2000)
        del request['now']
        with self.assertRaises(ValueError):
            handler.execute(request, self.root, self.repo, now=2000)

    def test_two_hosts_cannot_use_same_stale_head(self):
        self.hosts()
        first = self.request('intent', self.intent())
        second = copy.deepcopy(first)
        second['payload'] = self.intent('game-2', 'other-token', 'i-other')
        committed = handler.execute(first, self.root, self.repo, now=1000)
        self.reconcile(first, committed)
        with self.assertRaises(ValueError):
            handler.execute(second, self.root, self.repo, now=1000)
        root, events, head = self.store.read()
        self.assertEqual([g.game_id for g in trial.replay(root, events, head)[0].games], ['game-1'])

    def test_concurrent_other_host_cannot_pass_busy_gate(self):
        self.hosts()
        first = self.request('intent', self.intent())
        second = self.request('intent', self.intent('game-2', 'other-token', 'i-other'))
        entered, release = threading.Event(), threading.Event()
        original = self.client.transact_write_items
        def delayed(**kwargs):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('test controller failed to release transaction')
            return original(**kwargs)
        outcomes = []
        self.client.transact_write_items = delayed
        def invoke():
            try:
                outcomes.append(handler.execute(first, self.root, self.repo, now=1000))
            except Exception as error:
                outcomes.append(error)
        worker = threading.Thread(target=invoke)
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaises(handler.Quarantined):
                handler.execute(second, self.root, self.repo, now=1000)
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(outcomes), 1)
        self.assertIsInstance(outcomes[0], dict)
        root, events, head = self.store.read()
        self.assertEqual([g.game_id for g in trial.replay(root, events, head)[0].games], ['game-1'])

    def test_limit_rejects_new_game_but_keeps_started_game(self):
        self.hosts()
        self.execute('intent', self.intent())
        self.budget('limit_confirmed', {'actual_usd': '120',
            'evidence': {'observation_id': 'test-observation', 'source': 'test'}})
        with self.assertRaises(ValueError):
            self.execute('intent', self.intent('game-2', 'other-token', 'i-other'))
        root, events, head = self.store.read()
        state = trial.replay(root, events, head)[0]
        self.assertEqual(len(state.unsettled_games), 1)
        self.assertFalse(state.may_terminate('first-token'))

    def test_lost_reply_does_not_resubmit_and_old_head_cannot_replay(self):
        self.hosts()
        request = self.request('intent', self.intent())
        self.client.fail_after_commit = True
        with self.assertRaises(Exception):
            handler.execute(request, self.root, self.repo, now=1000)
        count = len(self.client.transactions)
        self.client.fail_after_commit = False
        with self.assertRaises(handler.Quarantined):
            handler.execute(request, self.root, self.repo, now=1000)
        self.assertEqual(len(self.client.transactions), count)
        root, events, head = self.store.read()
        self.assertEqual(len(trial.replay(root, events, head)[0].games), 1)

    def test_unknown_reply_quarantines_other_request_and_recreated_runtime(self):
        self.hosts()
        self.client.fail_after_commit = True
        with self.assertRaises(handler.Quarantined):
            self.execute('intent', self.intent())
        self.client.fail_after_commit = False
        pending = self.request('intent', self.intent('game-2', 'other-token', 'i-other'))
        count = len(self.client.transactions)
        new_repo = diagnostic.DynamoRepository(self.client, 'unit-only', self.client.codec, self.client.codec)
        with self.assertRaises(handler.Quarantined):
            handler.execute(pending, self.root, new_repo, now=1000)
        self.assertEqual(len(self.client.transactions), count)

    def test_response_lost_after_commit_can_be_reconciled_only_from_exact_history(self):
        self.hosts()
        original = self.request('intent', self.intent())
        self.client.fail_after_commit = True
        with self.assertRaises(handler.Quarantined):
            handler.execute(original, self.root, self.repo, now=1000)
        self.client.fail_after_commit = False
        _, events, head = self.store.read()
        recovered = {'head': head, 'event_sha256': events[-1]['sha256']}
        self.assertEqual(self.reconcile(original, recovered)['state'], 'diagnostic-reconciled')
        result = self.execute('intent', self.intent('game-2', 'other-token', 'i-other'))
        self.assertFalse(result['authorizes_go'])

    def test_namespace_is_separate_from_existing_diagnostic_history(self):
        self.hosts()
        self.execute('intent', self.intent())
        partitions = {key[0] for key in self.client.rows}
        self.assertEqual(partitions, {'league-test#budget-v3', 'league-test#budget-v3#gate'})
        self.assertNotIn(('league-test', diagnostic.HEAD), self.client.rows)
        self.assertTrue(all(item[next(iter(item))]['TableName'] == 'unit-only'
                            for item in self.client.transactions[-1]['TransactItems']))

    def test_handler_rejects_non_arn_and_cross_region_tables_before_client(self):
        calls = []
        boto = types.ModuleType('boto3')
        boto.client = lambda *args, **kwargs: calls.append((args, kwargs))
        dynamodb = types.ModuleType('boto3.dynamodb')
        dtypes = types.ModuleType('boto3.dynamodb.types')
        dtypes.TypeSerializer = dtypes.TypeDeserializer = type(self.client.codec)
        botocore = types.ModuleType('botocore')
        config = types.ModuleType('botocore.config')
        config.Config = lambda **kwargs: kwargs
        modules = {'boto3': boto, 'boto3.dynamodb': dynamodb, 'boto3.dynamodb.types': dtypes,
                   'botocore': botocore, 'botocore.config': config}
        for table in ('unit-only', 'arn:aws:dynamodb:ap-northeast-1:123456789012:table/unit-only'):
            env = {'ROVE_BUDGET_DIAGNOSTIC_ROOT_JSON': json.dumps(self.root),
                   'ROVE_BUDGET_DIAGNOSTIC_TABLE_ARN': table, 'AWS_REGION': 'ap-southeast-2'}
            with self.subTest(table=table), patch.dict(sys.modules, modules), patch.dict(os.environ, env), \
                    patch.object(handler, '_runtime', None), self.assertRaises(ValueError):
                handler.handler({}, None)
        self.assertEqual(calls, [])

    def test_lambda_handler_uses_pinned_runtime_and_server_clock(self):
        client = PartitionedDynamo(self.root)
        repo = diagnostic.DynamoRepository(client, 'unit-only', client.codec, client.codec)
        store = bridge.TrialTransactionBridge(handler.IsolatedRepository(repo, self.root), self.root)
        with patch.object(handler, '_runtime', (self.root, repo)), patch.object(handler.time, 'time', return_value=1000):
            boot = handler.handler({'kind': 'bootstrap', 'payload': {}, 'expected_head': None,
                                    'request_id': 'handler-boot'}, None)
            reconciled = handler.handler({'kind': 'reconcile_bootstrap', 'payload': {},
                                          'expected_head': boot['head'],
                                          'request_id': 'handler-boot-reconcile'}, None)
            self.assertEqual(reconciled['state'], 'diagnostic-bootstrap-reconciled')
            request = {'kind': 'budget', 'payload': {'event': 'budget.v2.launch_requested',
                'data': {'launch_token': 'first-token', 'region': 'ap-southeast-2', 'max_hourly_usd': '8'}},
                'expected_head': boot['head'], 'request_id': 'handler-budget'}
            recorded = handler.handler(request, None)
            result = handler.handler({'kind': 'reconcile',
                'payload': {'original': request, 'event_sha256': recorded['event_sha256']},
                'expected_head': recorded['head'], 'request_id': 'handler-budget-reconcile'}, None)
            self.assertEqual(result['state'], 'diagnostic-reconciled')
            self.assertFalse(result['authorizes_go'])
        root, events, head = store.read()
        self.assertEqual(events[0]['at'], 1000)
        self.assertEqual(trial.replay(root, events, head)[0].active_instances[0].charge.launch_token, 'first-token')

    def test_failed_release_leaves_gate_busy_and_rejects_new_invocation(self):
        self.hosts()
        request = self.request('intent', self.intent())
        result = handler.execute(request, self.root, self.repo, now=1000)
        self.client.fail_gate_release = True
        with self.assertRaises(handler.Quarantined):
            self.reconcile(request, result)
        self.client.fail_gate_release = False
        with self.assertRaises(handler.Quarantined):
            self.execute('intent', self.intent('game-2', 'other-token', 'i-other'))

    def test_success_reply_does_not_unlock_until_exact_reconciliation(self):
        self.hosts()
        request = self.request('intent', self.intent())
        result = handler.execute(request, self.root, self.repo, now=1000)
        self.assertEqual(result['state'], 'diagnostic-committed-pending-reconciliation')
        with self.assertRaises(handler.Quarantined):
            self.execute('intent', self.intent('game-2', 'other-token', 'i-other'))
        self.assertEqual(self.reconcile(request, result)['state'], 'diagnostic-reconciled')
        next_result = self.execute('intent', self.intent('game-2', 'other-token', 'i-other'))
        self.assertFalse(next_result['authorizes_go'])

    def test_wrong_original_or_digest_cannot_unlock(self):
        self.hosts()
        request = self.request('intent', self.intent())
        result = handler.execute(request, self.root, self.repo, now=1000)
        invalid = copy.deepcopy(request)
        invalid['payload']['game_id'] = 'different-game'
        with self.assertRaises(Exception):
            self.reconcile(invalid, result)
        invalid_result = copy.deepcopy(result)
        invalid_result['event_sha256'] = 'f' * 64
        with self.assertRaises(Exception):
            self.reconcile(request, invalid_result)
        with self.assertRaises(handler.Quarantined):
            self.execute('intent', self.intent('game-2', 'other-token', 'i-other'))
        self.reconcile(request, result)

    def test_invalid_expected_head_never_commits(self):
        self.hosts()
        for head in (None, {}, {'revision': True, 'sha256': '0' * 64}):
            request = self.request('intent', self.intent())
            request['expected_head'] = head
            count = len(self.client.transactions)
            with self.subTest(head=head), self.assertRaises(ValueError):
                handler.execute(request, self.root, self.repo, now=1000)
            self.assertEqual(len(self.client.transactions), count)


if __name__ == '__main__':
    unittest.main()
