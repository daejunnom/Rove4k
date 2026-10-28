"""P16/P192 real runner command preparation with synthetic kernel evidence.

No engine, Fastchess process, AWS call, large TT, or scored game is started.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from . import league_executor, placement, run, topology, wave
except ImportError:
    import league_executor
    import placement
    import run
    import topology
    import wave


def kernel_fixture():
    """Use the actual 192-vCPU, sparse, two-node SMT topology contract."""
    cpus = tuple(topology.Cpu(core * 4 + smt, core // 48, core, core // 48,
                              (core * 4, core * 4 + 1))
                 for core in range(96) for smt in (0, 1))
    return topology.Topology(cpus, tuple(cpu.id for cpu in cpus), (0, 1), {},
                             'synthetic-kernel-fixture')


class PreparedLeagueWaveTests(unittest.TestCase):
    def fixture(self, profile, root):
        root = Path(root).resolve()
        snapshot = kernel_fixture()
        slots, controller = run.league_placement(snapshot, profile)
        target_path = root / 'delegated'
        target = {'path': str(target_path), 'device': 7, 'inode': 8}
        groups = {slot.id: {'path': str(target_path / slot.id), 'device': 7,
                            'inode': 100 + i, 'cpus': list(slot.cpus),
                            'memory_nodes': list(slot.memory_nodes),
                            'memory_max': (26 if profile == 'test-p16' else 386) << 30}
                  for i, slot in enumerate(slots)}
        pairs = [{'id': f'pair-{i}', 'players': ['white', 'black'],
                  'opening_index': i + 1,
                  'opening': {'id': f'opening-{i}', 'moves': ['e2e4', 'e7e5']}}
                 for i in range(len(slots))]
        body = {'campaign': 'fixture', 'profile': profile, 'topology': snapshot.to_record(),
                'slots': json.loads(json.dumps([slot.to_record() for slot in slots])),
                'controller_cpus': controller, 'pairs': pairs, 'bank_id': 'bank-fixture',
                'runner': {'path': 'runner', 'sha256': 'c' * 64}, 'opening_pgn': 'openings.pgn'}
        tt = (12 if profile == 'test-p16' else 192) << 30
        players = [{'artifact': SimpleNamespace(id=name, path=root / name, tt_bytes=tt, sha256=char * 64)}
                   for name, char in (('white', 'a'), ('black', 'b'))]
        envelope = {'content': body, 'sha256': 'd' * 64}
        selections = [{'pair': pair['id'], 'leg': i % 2, 'attempt': 0, 'slot': slot.id}
                      for i, (pair, slot) in enumerate(zip(pairs, slots))]
        return snapshot, slots, target, groups, envelope, players, selections

    def invoke(self, root, profile, *, mutate=None):
        snapshot, slots, target, groups, envelope, players, selections = self.fixture(profile, root)
        if mutate:
            snapshot, target, groups, envelope, players, selections = mutate(
                snapshot, target, groups, envelope, players, selections)
        out = Path(root) / 'prepared'
        with patch.object(run, 'load_plan', return_value=(envelope, players)), \
             patch.object(topology.Topology, 'snapshot_target', return_value=snapshot), \
             patch.object(placement, 'verify_cgroup_live') as verify:
            jobs, specs = league_executor.prepare_wave(Path(root) / 'plan.json', selections, groups,
                                                      target, out, launch_id='fixture-launch')
        return jobs, specs, slots, groups, envelope, out, verify

    def test_p16_uses_eleven_node_local_slots_for_both_players(self):
        with tempfile.TemporaryDirectory(prefix='rove-p16-wave-') as tmp:
            jobs, specs, slots, groups, envelope, out, verify = self.invoke(tmp, 'test-p16')
            self.assertEqual(len(jobs), 11)
            self.assertEqual(verify.call_count, 11)
            self.assertEqual(len({cpu for slot in slots for cpu in slot.cpus}), 176)
            for index, (job, slot) in enumerate(zip(jobs, slots)):
                self.assertIsInstance(job, wave.WaveJob)
                self.assertEqual(specs[job.identity]['slot'], slot.to_record())
                record = json.loads((out / f'placement-{slot.id}.json').read_text())
                self.assertEqual(record['slot']['cpus'], list(slot.cpus))
                self.assertEqual(record['slot']['memory_nodes'], list(slot.memory_nodes))
                self.assertEqual(record['saved_ancestor_nodes'], [0, 1])
                self.assertEqual(record['cgroup'], groups[slot.id])
                self.assertEqual(len(slot.memory_nodes), 1)
                self.assertEqual(job.start_job['slot'], slot.id)
                argv = list(job.argv)
                self.assertEqual(argv[argv.index('--slot') + 1], str(out / f'placement-{slot.id}.json'))
                command = argv[argv.index('--') + 1:]
                self.assertIn('tc=30:00+3', command)
                self.assertIn('option.Ponder=false', command)
                self.assertEqual(command[command.index('-concurrency') + 1], '1')
                self.assertEqual(command[command.index('-games') + 1], '1')
                names = [command[pos + 1] for pos, value in enumerate(command) if value == '-engine']
                expected = ['name=white', 'name=black'] if index % 2 == 0 else ['name=black', 'name=white']
                self.assertEqual(names, expected)
                self.assertEqual(specs[job.identity]['identity']['slot'], slot.id)
            self.assertEqual(json.loads((out / 'prepared-wave.json').read_text())['profile'], 'test-p16')

    def test_p192_shares_the_full_cpu_and_memory_node_envelope(self):
        with tempfile.TemporaryDirectory(prefix='rove-p192-wave-') as tmp:
            jobs, specs, slots, groups, envelope, out, verify = self.invoke(tmp, 'test-p192')
            self.assertEqual(len(jobs), 1)
            self.assertEqual(len(slots[0].cpus), 192)
            self.assertEqual(slots[0].memory_nodes, (0, 1))
            self.assertEqual(envelope['content']['controller_cpus'], list(slots[0].cpus))
            slot = json.loads((out / f'placement-{slots[0].id}.json').read_text())
            self.assertEqual(slot['saved_ancestor_nodes'], [0, 1])
            self.assertEqual(slot['cgroup']['memory_max'], 386 << 30)
            self.assertIn('tc=30:00+3', jobs[0].argv)
            self.assertIn('option.Ponder=false', jobs[0].argv)
            self.assertEqual(verify.call_count, 1)

    def test_duplicate_game_or_slot_is_rejected_before_output(self):
        for kind in ('slot', 'game'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix='rove-wave-duplicate-') as tmp:
                def mutate(snapshot, target, groups, envelope, players, selections):
                    if kind == 'slot':
                        selections[1]['slot'] = selections[0]['slot']
                    else:
                        selections[1]['pair'] = selections[0]['pair']
                        selections[1]['leg'] = selections[0]['leg']
                    return snapshot, target, groups, envelope, players, selections
                with self.assertRaises(ValueError):
                    self.invoke(tmp, 'test-p16', mutate=mutate)
                self.assertFalse((Path(tmp) / 'prepared').exists())

    def test_profile_capacity_never_accepts_an_extra_game(self):
        for profile in ('test-p16', 'test-p192'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory(prefix='rove-wave-capacity-') as tmp:
                def mutate(snapshot, target, groups, envelope, players, selections):
                    selections.append(copy.deepcopy(selections[0]))
                    return snapshot, target, groups, envelope, players, selections
                with self.assertRaisesRegex(ValueError, 'profile slot count'):
                    self.invoke(tmp, profile, mutate=mutate)
                self.assertFalse((Path(tmp) / 'prepared').exists())

    def test_memory_and_cgroup_masks_reject_tampering(self):
        for kind in ('memory', 'nodes', 'cpus', 'duplicate-inode', 'escape'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix='rove-wave-group-') as tmp:
                def mutate(snapshot, target, groups, envelope, players, selections):
                    first, second = list(groups)[:2]
                    if kind == 'memory': groups[first]['memory_max'] = (24 << 30) - 1
                    elif kind == 'nodes': groups[first]['memory_nodes'] = [99]
                    elif kind == 'cpus': groups[first]['cpus'] = groups[first]['cpus'][:-1]
                    elif kind == 'duplicate-inode': groups[second]['inode'] = groups[first]['inode']
                    else: groups[first]['path'] = str(Path(tmp) / 'outside')
                    return snapshot, target, groups, envelope, players, selections
                with self.assertRaises(ValueError):
                    self.invoke(tmp, 'test-p16', mutate=mutate)
                self.assertFalse((Path(tmp) / 'prepared').exists())

    def test_changed_topology_and_frozen_slot_are_rejected(self):
        for kind in ('live-nodes', 'frozen-slot', 'controller'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix='rove-wave-topology-') as tmp:
                def mutate(snapshot, target, groups, envelope, players, selections):
                    if kind == 'live-nodes':
                        snapshot = topology.Topology(snapshot.cpus, snapshot.allowed_cpus, (0,), {}, snapshot.kernel)
                    elif kind == 'frozen-slot': envelope['content']['slots'][0]['cpus'].pop()
                    else: envelope['content']['controller_cpus'].pop()
                    return snapshot, target, groups, envelope, players, selections
                with self.assertRaises(ValueError):
                    self.invoke(tmp, 'test-p16', mutate=mutate)
                self.assertFalse((Path(tmp) / 'prepared').exists())

    def test_scored_execution_is_denied_before_process_creation(self):
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('process started')) as popen, \
             patch.object(wave.WaveExecutor, 'run_wave', side_effect=AssertionError('wave started')) as spawn:
            with self.assertRaisesRegex(RuntimeError, 'authenticated global budget and host fencing'):
                league_executor.run_scored()
        popen.assert_not_called()
        spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
