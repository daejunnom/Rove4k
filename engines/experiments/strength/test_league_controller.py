"""League plan and shared-ledger integration, using fixtures only.

These tests do not assert AWS ownership, GO authority, or real game exits.
"""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from . import global_budget as g
    from .league_controller import HostPlan, LegacyResources, LeaguePlan, LeagueController
    from .diagnostic_ledger_bridge import DiagnosticHost
    from .ledger import Journal
    from .shared_coordinator import CoordinatorBlocked, SharedBudgetJournal
    from .test_global_budget import FakeS3
    from .wave import WaveJob
except ImportError:
    import global_budget as g
    from league_controller import HostPlan, LegacyResources, LeaguePlan, LeagueController
    from diagnostic_ledger_bridge import DiagnosticHost
    from ledger import Journal
    from shared_coordinator import CoordinatorBlocked, SharedBudgetJournal
    from test_global_budget import FakeS3
    from wave import WaveJob


ACCOUNT = '123456789012'
REGION = 'ap-southeast-2'
LEGACY = LegacyResources(
    campaign='old-campaign', bucket='legacy-campaign-bucket',
    table=f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/legacy-owner-table',
    role_arn=f'arn:aws:iam::{ACCOUNT}:role/legacy-controller',
    profile_arn=f'arn:aws:iam::{ACCOUNT}:instance-profile/legacy-host',
    watchdog_arn=f'arn:aws:lambda:{REGION}:{ACCOUNT}:function:legacy-deadline')
HOSTS = (
    HostPlan(region=REGION, profile='test-p16', slots=11, launch_token='first-token'),
    HostPlan(region=REGION, profile='test-p192', slots=1, launch_token='other-token'),
)


def make_plan(**overrides):
    value = dict(campaign='league-test', account=ACCOUNT, home_region=REGION,
        bucket='league-campaign-bucket', table=f'arn:aws:dynamodb:{REGION}:{ACCOUNT}:table/league-owner-table',
        role_arn=f'arn:aws:iam::{ACCOUNT}:role/league-controller',
        profile_arn=f'arn:aws:iam::{ACCOUNT}:instance-profile/league-host',
        watchdog_arn=f'arn:aws:lambda:{REGION}:{ACCOUNT}:function:league-watchdog',
        legacy=LEGACY, hosts=HOSTS)
    value.update(overrides)
    return LeaguePlan(**value)


class PlanTests(unittest.TestCase):
    def test_requested_profile_geometry_and_unique_host_ownership(self):
        plan = make_plan()
        self.assertEqual(tuple((h.profile, h.slots) for h in plan.hosts),
                         (('test-p16', 11), ('test-p192', 1)))
        for hosts in (
            lambda: (replace(HOSTS[0], slots=10),),
            lambda: (replace(HOSTS[1], slots=11),),
            lambda: (replace(HOSTS[0], profile='test-p28'),),
            lambda: (HOSTS[0], replace(HOSTS[1], launch_token=HOSTS[0].launch_token)),
            lambda: (HOSTS[0], HOSTS[1], replace(HOSTS[0], launch_token='third-token')),
        ):
            with self.subTest(hosts=hosts), self.assertRaises((ValueError, TypeError)):
                make_plan(hosts=hosts())

    def test_every_declared_legacy_namespace_collision_is_rejected(self):
        for name in ('campaign', 'bucket', 'table', 'role_arn', 'profile_arn', 'watchdog_arn'):
            with self.subTest(name=name), self.assertRaises((ValueError, TypeError)):
                make_plan(**{name: getattr(LEGACY, name)})

    def test_deadline_is_not_a_league_plan_field(self):
        with self.assertRaises(TypeError):
            make_plan(hard_deadline_utc=1234)

    def test_later_p192_phase_is_explicit_and_cannot_duplicate_or_be_unknown(self):
        host = replace(HOSTS[0], later_profiles=('test-p192',))
        self.assertEqual(host.slots, 11)
        self.assertEqual(host.later_profiles, ('test-p192',))
        self.assertEqual(make_plan(hosts=(host,)).hosts, (host,))
        for later in (('test-p192', 'test-p192'), ('test-p16',), ('test-p28',)):
            with self.subTest(later=later), self.assertRaises((ValueError, TypeError)):
                replace(HOSTS[0], later_profiles=later)


@unittest.skipUnless(sys.platform == 'linux', 'requires the real POSIX journal implementation')
class LeagueControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rove4k-league-test-')
        self.client = FakeS3()
        self.client.doc['campaign'] = 'league-test'
        # Carry-in costs are part of the trusted opening and must not be lost
        # when replaying the later event rows.
        self.client.doc['opening']['prior_compute_usd'] = '99'
        self.client._publish(g.canonical(self.client.doc))
        self.plan = make_plan()
        self.store = g.S3SharedBudget(self.client, bucket=self.plan.bucket,
            key='league-test/shared/budget.json', account=ACCOUNT,
            region=REGION, campaign=self.plan.campaign)
        self.root = g.Anchor(-1, g.ZERO, self.store.authority,
                             g.digest(self.client.doc['opening']))
        self.journal = Journal(Path(self.temp.name) / 'journal.jsonl', self.plan.campaign)
        self.owner = SharedBudgetJournal(self.store, self.journal, self.root)
        self.controller = LeagueController(self.plan, self.store, self.owner)

    def tearDown(self):
        self.journal.close()
        self.temp.cleanup()

    def event(self, n, event, data, at=1000):
        return self.owner.record(request_id=f'league-test-request-{n:03}',
                                 event=event, data=data, at=at)

    def launch_and_start(self):
        for number, token, instance in ((1, 'first-token', 'i-123'), (3, 'other-token', 'i-456')):
            self.event(number, 'budget.v2.launch_requested', {'launch_token': token,
                'region': REGION, 'max_hourly_usd': '8'})
            self.event(number + 1, 'budget.v2.instance_bound', {
                'launch_token': token, 'instance_id': instance})
        for number, game, token in ((5, 'game-a', 'first-token'), (7, 'game-b', 'other-token')):
            self.event(number, 'budget.v2.game_admitted', {'game_id': game, 'pair_id': 'pair-a',
                'launch_token': token})
            self.event(number + 1, 'budget.v2.game_release_authorized', {'game_id': game,
                'valid_until_utc': 1005})

    def test_observation_replays_opening_cost_and_blocks_at_limit_without_settling_games(self):
        self.launch_and_start()
        before = self.controller.observe(request_id='league-observation-001', at=1001)
        self.assertEqual(before['state'], 'diagnostic')
        self.assertFalse(before['draining'])
        self.assertGreater(float(before['budget']['upper_usd']), 119)
        self.assertEqual({row['game_id'] for row in before['games']}, {'game-a', 'game-b'})
        self.assertTrue(all(row['release_authorized'] and not row['settled'] for row in before['games']))
        boot = '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb'
        host = DiagnosticHost('i-123', boot, 'first-token')
        mailbox = self.controller.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1001)
        try:
            after = self.controller.observe(request_id='league-observation-002', at=1226)
            self.assertEqual(after['state'], 'draining')
            self.assertTrue(after['draining'])
            self.assertGreaterEqual(float(after['budget']['upper_usd']), 120)
            self.assertEqual({row['game_id'] for row in after['games']}, {'game-a', 'game-b'})
            self.assertTrue(all(not row['settled'] for row in after['games']))
            self.assertFalse(after['scored_go_allowed'])
            self.assertFalse(after['termination_allowed'])
            meta = {'attempt_id': 'attempt-00000001', 'probe_fence_id': 'diagnostic-1',
                    'boot_id': boot, 'instance_id': 'i-123', 'launch_token': 'first-token'}
            job = WaveJob('game-new', (sys.executable,), {}, meta,
                          Path(self.temp.name).resolve() / 'attempt')
            with self.assertRaises(ValueError):
                mailbox.request(job, {'ready_monotonic': 1, 'ready': {'event': 'READY', 'job': meta}})
            with self.assertRaises(ValueError):
                self.controller.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1001)
        finally:
            self.assertTrue(mailbox.close(2))
        snapshot = self.store.load(self.root)
        self.assertEqual(snapshot.rows[-1]['event'], 'budget.v2.observe')
        self.assertEqual(snapshot.anchor, self.owner.anchor)

    def test_prior_confirmed_limit_survives_even_when_current_upper_is_below_cap(self):
        self.event(1, 'budget.v2.limit_confirmed', {'actual_usd': '120',
            'evidence': {'source': 'fixture', 'observation_id': 'charge-1'}})
        report = self.controller.observe(request_id='league-observation-003', at=1001)
        self.assertTrue(report['draining'])
        self.assertLess(float(report['budget']['upper_usd']), 120)
        self.assertFalse(report['scored_go_allowed'])
        self.assertFalse(report['termination_allowed'])

    def test_mailbox_requires_an_observation_and_stays_closed_when_limit_confirmed(self):
        boot = '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb'
        host = DiagnosticHost('i-123', boot, 'first-token')
        with self.assertRaises(ValueError):
            self.controller.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1001)
        self.event(1, 'budget.v2.limit_confirmed', {'actual_usd': '120',
            'evidence': {'source': 'fixture', 'observation_id': 'charge-2'}})
        restarted = LeagueController(self.plan, self.store, self.owner)
        with self.assertRaises(ValueError):
            restarted.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1001)
        report = restarted.observe(request_id='league-observation-006', at=1001)
        self.assertTrue(report['draining'])
        with self.assertRaises(ValueError):
            restarted.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1001)

    def test_mailbox_identity_must_match_observed_ledger_owner(self):
        self.launch_and_start()
        self.controller.observe(request_id='league-observation-007', at=1001)
        boot = '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb'
        wrong = DiagnosticHost('i-456', boot, 'first-token')
        with self.assertRaises(ValueError):
            self.controller.diagnostic_mailbox(wrong, read_boot=lambda: boot, now_utc=lambda: 1001)
        right = DiagnosticHost('i-123', boot, 'first-token')
        mailbox = self.controller.diagnostic_mailbox(right, read_boot=lambda: boot, now_utc=lambda: 1001)
        self.assertTrue(mailbox.close(2))

    def test_mailbox_requires_reobservation_after_owner_anchor_advances(self):
        self.launch_and_start()
        self.controller.observe(request_id='league-observation-011', at=1001)
        boot = '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb'
        host = DiagnosticHost('i-123', boot, 'first-token')
        self.event(9, 'budget.v2.observe', {'scope': 'separate-local-writer'}, at=1002)
        with self.assertRaises(ValueError):
            self.controller.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1002)
        report = self.controller.observe(request_id='league-observation-012', at=1003)
        self.assertFalse(report['draining'])
        mailbox = self.controller.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1003)
        self.assertTrue(mailbox.close(2))

    def test_opening_checkpoint_replays_active_game_and_confirmed_limit(self):
        client = FakeS3()
        client.doc['campaign'] = self.plan.campaign
        opening = client.doc['opening']
        opening['prior_compute_usd'] = '5'
        opening['prior_limit_confirmed'] = True
        opening['as_of'] = 1000
        opening['events'] = [
            {'campaign': self.plan.campaign, 'event': 'budget.v2.launch_requested',
             'data': {'launch_token': 'first-token', 'region': REGION, 'max_hourly_usd': '8'}, 'time_utc': 950},
            {'campaign': self.plan.campaign, 'event': 'budget.v2.instance_bound',
             'data': {'launch_token': 'first-token', 'instance_id': 'i-123'}, 'time_utc': 951},
            {'campaign': self.plan.campaign, 'event': 'budget.v2.game_admitted',
             'data': {'game_id': 'opening-game', 'pair_id': 'opening-pair', 'launch_token': 'first-token'}, 'time_utc': 952},
            {'campaign': self.plan.campaign, 'event': 'budget.v2.game_release_authorized',
             'data': {'game_id': 'opening-game', 'valid_until_utc': 954}, 'time_utc': 953},
        ]
        client._publish(g.canonical(client.doc))
        store = g.S3SharedBudget(client, bucket=self.plan.bucket, key='league-test/shared/budget.json',
                                 account=ACCOUNT, region=REGION, campaign=self.plan.campaign)
        anchor = g.Anchor(-1, g.ZERO, store.authority, g.digest(opening))
        with Journal(Path(self.temp.name) / 'opening.jsonl', self.plan.campaign) as journal:
            owner = SharedBudgetJournal(store, journal, anchor)
            controller = LeagueController(self.plan, store, owner)
            report = controller.observe(request_id='league-opening-observation-001', at=1001)
            self.assertTrue(report['draining'])
            self.assertGreater(float(report['budget']['compute_usd']), 5)
            self.assertLess(float(report['budget']['upper_usd']), 120)
            self.assertEqual([row['game_id'] for row in report['games']], ['opening-game'])
            self.assertTrue(report['games'][0]['release_authorized'])
            self.assertFalse(report['games'][0]['settled'])
            self.assertFalse(report['scored_go_allowed'])
            self.assertFalse(report['termination_allowed'])

    def test_ledger_conflict_is_not_retried_and_blocks_subsequent_observations(self):
        self.launch_and_start()
        self.controller.observe(request_id='league-observation-008', at=1001)
        boot = '9c87985b-49cb-4c8e-9de5-3ea3d9c7fabb'
        host = DiagnosticHost('i-123', boot, 'first-token')
        mailbox = self.controller.diagnostic_mailbox(host, read_boot=lambda: boot, now_utc=lambda: 1001)
        self.client.conflict = True
        try:
            with self.assertRaises(g.LedgerConflict):
                self.controller.observe(request_id='league-observation-004', at=1002)
            self.assertTrue(self.owner.blocked)
            sequence = self.client.seq
            self.client.conflict = False
            with self.assertRaises((CoordinatorBlocked, ValueError, RuntimeError)):
                self.controller.observe(request_id='league-observation-005', at=1003)
            self.assertEqual(self.client.seq, sequence)
            meta = {'attempt_id': 'attempt-00000001', 'probe_fence_id': 'diagnostic-1',
                    'boot_id': boot, 'instance_id': 'i-123', 'launch_token': 'first-token'}
            job = WaveJob('game-new', (sys.executable,), {}, meta, Path(self.temp.name).resolve() / 'attempt')
            with self.assertRaises(ValueError):
                mailbox.request(job, {'ready_monotonic': 1, 'ready': {'event': 'READY', 'job': meta}})
        finally:
            self.assertTrue(mailbox.close(2))

    def test_unrelated_store_and_owner_are_rejected(self):
        other = g.S3SharedBudget(self.client, bucket='other-campaign-bucket',
            key='league-test/shared/budget.json', account=ACCOUNT,
            region=REGION, campaign=self.plan.campaign)
        with self.assertRaises((ValueError, TypeError)):
            LeagueController(self.plan, other, self.owner)

    def test_changed_opening_snapshot_is_rejected_without_remote_write(self):
        self.client.doc['opening']['prior_compute_usd'] = '0'
        self.client._publish(g.canonical(self.client.doc))
        sequence = self.client.seq
        with self.assertRaises(ValueError):
            self.controller.observe(request_id='league-observation-009', at=1001)
        self.assertTrue(self.owner.blocked)
        self.assertEqual(self.client.seq, sequence)
        with self.assertRaises(RuntimeError):
            self.controller.observe(request_id='league-observation-010', at=1002)
        self.assertEqual(self.client.seq, sequence)


if __name__ == '__main__':
    unittest.main()
