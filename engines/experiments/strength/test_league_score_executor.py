"""Draft-driven wave preparation; no engine, GO or AWS calls."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import league_executor, league_score_plan, original_peer_build, placement, run, topology, wave
    from . import test_league_executor as kernel, test_league_score_plan as fixtures
except ImportError:
    import league_executor
    import league_score_plan
    import original_peer_build
    import placement
    import run
    import topology
    import wave
    import test_league_executor as kernel
    import test_league_score_plan as fixtures


class DraftWaveTests(unittest.TestCase):
    def fixture(self, root, profile):
        sample = fixtures.DraftPlanTests()
        sample.root = root
        args, _, _, _, _ = sample.fixture(profile)
        with patch.object(original_peer_build.peers, "verify_blob"):
            draft = league_score_plan.prepare(**args)
        plan_path = root / "draft.json"
        plan_path.write_bytes(league_score_plan.ledger.canonical(draft))
        snapshot = kernel.kernel_fixture()
        slots, _ = run.league_placement(snapshot, profile)
        target_path = root / "delegated"
        target = {"path": str(target_path), "device": 7, "inode": 8}
        memory = (34 if profile == "test-p16" else 460) << 30
        groups = {slot.id: {"path": str(target_path / slot.id), "device": 7,
                  "inode": 100 + i, "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes),
                  "memory_max": memory} for i, slot in enumerate(slots)}
        return draft, plan_path, snapshot, slots, target, groups

    def prepare(self, root, profile, leg, *, mutate=None):
        draft, path, snapshot, slots, target, groups = self.fixture(root, profile)
        pair, = draft["content"]["pairs"]
        selections = [{"pair": pair["id"], "leg": leg, "attempt": 0, "slot": slots[0].id}]
        if mutate:
            mutate(draft, path, slots, target, groups, selections)
        out = root / "prepared"
        with patch.object(original_peer_build.peers, "verify_blob"), \
             patch.object(topology.Topology, "snapshot_target", return_value=snapshot), \
             patch.object(placement, "verify_cgroup_live"), \
             patch.object(subprocess, "Popen", side_effect=AssertionError("unexpected process")), \
             patch.object(wave.WaveExecutor, "run_wave", side_effect=AssertionError("unexpected GO")):
            jobs, specs = league_executor.prepare_draft_wave(path, draft["sha256"], selections,
                groups, target, out, launch_id="fixture-launch")
        return jobs, specs, slots, groups, draft, out

    def test_peer_resources_follow_both_colour_orders(self):
        for profile, mib, threads in (("test-p16", 16384, 16), ("test-p192", 262144, 192)):
            for leg in (0, 1):
                with self.subTest(profile=profile, leg=leg), tempfile.TemporaryDirectory() as tmp:
                    jobs, specs, slots, groups, draft, out = self.prepare(Path(tmp).resolve(), profile, leg)
                    job, = jobs
                    self.assertIsInstance(job, wave.WaveJob)
                    cmd = list(job.argv)
                    segments = {}
                    for index, value in enumerate(cmd):
                        if value == "-engine":
                            stop = next(i for i in range(index + 1, len(cmd)) if cmd[i] in ("-engine", "-each"))
                            segments[cmd[index + 1]] = cmd[index + 2:stop]
                    ice = next(name for name in segments if name.startswith("name=ice4"))
                    self.assertIn(f"option.Hash={mib}", segments[ice])
                    self.assertIn(f"option.Threads={threads}", segments[ice])
                    self.assertFalse(any(arg.startswith(("option.Hash=", "option.Threads="))
                                         for arg in segments["name=Rove-A"]))
                    self.assertEqual(list(segments)[leg == 0], ice)
                    self.assertIn("tc=30:00+3", cmd)
                    self.assertIn("option.Ponder=false", cmd)
                    self.assertEqual(specs[job.identity]["slot"], slots[0].to_record())
                    group_record = json.loads((out / f"placement-{slots[0].id}.json").read_text())
                    self.assertEqual(group_record["cgroup"], groups[slots[0].id])
                    receipt = json.loads((out / "prepared-wave.json").read_text())
                    self.assertEqual(receipt["format"], "rove4k-league-draft-prepared-wave-v1")
                    self.assertTrue(receipt["draft_only"])
                    self.assertFalse(receipt["score_authorized"])
                    self.assertFalse(receipt["go_authorized"])
                    self.assertTrue(receipt["live_topology_snapshot_not_attestation"])

    def test_distinct_colour_legs_share_no_slot_and_keep_same_opening(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            draft, path, snapshot, slots, target, groups = self.fixture(root, "test-p16")
            pair, = draft["content"]["pairs"]
            selections = [{"pair": pair["id"], "leg": leg, "attempt": 0, "slot": slots[leg].id}
                          for leg in (0, 1)]
            with patch.object(original_peer_build.peers, "verify_blob"), \
                 patch.object(topology.Topology, "snapshot_target", return_value=snapshot), \
                 patch.object(placement, "verify_cgroup_live"), \
                 patch.object(subprocess, "Popen", side_effect=AssertionError("unexpected process")):
                jobs, specs = league_executor.prepare_draft_wave(path, draft["sha256"], selections,
                    groups, target, root / "prepared", launch_id="fixture-launch")
            self.assertEqual(len(jobs), 2)
            a, b = [specs[job.identity]["identity"] for job in jobs]
            self.assertEqual((a["white"], a["black"]), (b["black"], b["white"]))
            self.assertEqual(a["opening_sha256"], b["opening_sha256"])
            self.assertNotEqual(a["slot"], b["slot"])

    def test_forged_plan_and_wrong_slot_memory_are_rejected_before_output(self):
        for kind in ("body", "digest", "memory", "slot"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                def mutate(draft, path, slots, target, groups, selections):
                    if kind == "body":
                        forged = copy.deepcopy(draft)
                        forged["content"]["claims"]["go_authorized"] = True
                        path.write_bytes(league_score_plan.ledger.canonical(forged))
                    elif kind == "digest":
                        draft["sha256"] = "0" * 64
                    elif kind == "memory":
                        groups[slots[0].id]["memory_max"] = 1
                    else:
                        selections[0]["slot"] = "not-a-slot"
                with self.assertRaises((ValueError, OSError)):
                    self.prepare(root, "test-p16", 0, mutate=mutate)
                self.assertFalse((root / "prepared").exists())

    def test_global_go_remains_denied(self):
        with patch.object(subprocess, "Popen", side_effect=AssertionError("unexpected process")), \
             patch.object(wave.WaveExecutor, "run_wave", side_effect=AssertionError("unexpected GO")):
            with self.assertRaises(RuntimeError):
                league_executor.run_scored()

    def test_draft_output_rejects_protected_directories(self):
        for name in ('.cache', 'build', 'node_modules', 'TOKEN'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                draft, path, snapshot, slots, target, groups = self.fixture(root, 'test-p16')
                selection = [{'pair': draft['content']['pairs'][0]['id'], 'leg': 0,
                              'attempt': 0, 'slot': slots[0].id}]
                with patch.object(original_peer_build.peers, 'verify_blob'), \
                     patch.object(topology.Topology, 'snapshot_target', return_value=snapshot), \
                     patch.object(placement, 'verify_cgroup_live'), self.assertRaises(ValueError):
                    league_executor.prepare_draft_wave(path, draft['sha256'], selection, groups,
                                                       target, root / name / 'out', launch_id='fixture-launch')


if __name__ == "__main__":
    unittest.main()
