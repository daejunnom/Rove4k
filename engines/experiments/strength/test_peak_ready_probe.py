"""Synthetic protocol tests: no live engines, cgroups, TT or cloud."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import peak_ready_probe as probe, topology
except ImportError:
    import peak_ready_probe as probe
    import topology


class PeakReadyTests(unittest.TestCase):
    def test_controller_manifest_is_pinned_and_decodes_frozen_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "controller.json"
            slot = topology.Slot("slot-000", tuple(range(192)), tuple((0, i) for i in range(96)),
                                 (0, 1), 192, True, "default")
            manifest = {"format": "rove4k-pre-go-controller-v2", "profile": "test-p192",
                        "entries": [{"slot": slot.to_record(), "engines": [], "opening_start": 1,
                                     "out": str(Path(tmp) / "output")}],
                        "runner": str(Path(tmp) / "fastchess"), "runner_sha256": "a" * 64,
                        "opening": str(Path(tmp) / "opening.pgn"), "opening_sha256": "b" * 64,
                        "topology": {"synthetic": True},
                        "saved_ancestor_cpus": list(slot.cpus),
                        "wall_seconds": 120}
            raw = json.dumps(manifest).encode()
            path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            self.assertEqual(probe.load_controller_manifest(path, digest)["entries"][0]["slot"], slot)
            path.write_bytes(raw + b" ")
            with self.assertRaisesRegex(ValueError, "pinned digest"):
                probe.load_controller_manifest(path, digest)
            manifest["format"] = "rove4k-pre-go-controller-v1"
            old = json.dumps(manifest).encode()
            path.write_bytes(old)
            with self.assertRaisesRegex(ValueError, "invalid controller manifest"):
                probe.load_controller_manifest(path, hashlib.sha256(old).hexdigest())

    def test_controller_cli_uses_private_channel_and_pre_go_path(self):
        manifest = {"profile": "test-p192", "entries": [], "runner": "/fastchess",
                    "runner_sha256": "a" * 64, "opening": "/openings", "opening_sha256": "b" * 64,
                    "saved_ancestor_cpus": [1],
                    "wall_seconds": 120}
        channel = object()
        with patch.object(probe, "load_controller_manifest", return_value=manifest) as load, \
             patch.object(probe.peak_supervisor, "ControllerChannel", return_value=channel), \
             patch.object(probe, "ready_probe", return_value={"runtime_admission": False}) as ready, \
             patch("builtins.print"):
            self.assertEqual(probe.main(["--manifest", "/input.json", "--manifest-sha256", "a" * 64]), 0)
        load.assert_called_once_with("/input.json", "a" * 64)
        self.assertIs(ready.call_args.kwargs["channel"], channel)
        self.assertEqual(ready.call_args.kwargs["profile"], "test-p192")

    def test_actual_path_remains_pre_go_and_uses_handed_off_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = []
            for name in ("fastchess", "white", "black", "openings"):
                path = root / name
                path.write_bytes(name.encode())
                files.append(path)
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            slot = topology.Slot("p192", tuple(range(192)), tuple((0, i) for i in range(96)),
                                 (0, 1), 192, True, "default")
            group = {"path": str(root / "group"), "device": 1, "inode": 2,
                     "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes), "memory_max": 1024}
            controller = dict(group, path=str(root / "controller"))
            (root / "controller").mkdir()
            (root / "controller" / "cgroup.procs").write_text(str(os.getpid()))
            entries = [{"slot": slot, "out": root / "attempt", "opening_start": 1,
                        "engines": [{"id": "white", "path": files[1], "whole_sha256": sha(files[1]), "native_sha256": "a" * 64, "tt_bytes": 256 << 30,
                                     "uci": {"kind": "original-peer-uci-v1", "family": "ice4", "hash_mib": 262144, "threads": 192}},
                                    {"id": "black", "path": files[2], "whole_sha256": sha(files[2]), "native_sha256": "b" * 64, "tt_bytes": 12 << 30}]}]
            class Channel:
                def handoff(self):
                    return {"games": {"p192": group}, "controller": controller, "runtime_admission": False}
                def active(self, members):
                    # Reversed /proc enumeration must still map to frozen colour order.
                    self.members = members
                    return True
                def settled(self):
                    return True
            channel = Channel()
            class Executor:
                def run_wave(self, jobs, wall_seconds, release_callback, on_event, *, authorize_go, observe_transport):
                    self_outer.assertEqual(jobs[0].argv[1], str(Path(probe.placement.__file__).resolve()))
                    arguments = list(jobs[0].argv)
                    white = arguments.index("name=white")
                    black = arguments.index("name=black")
                    self_outer.assertIn("option.Hash=262144", arguments[white:black])
                    self_outer.assertIn("option.Threads=192", arguments[white:black])
                    self_outer.assertFalse(any(value.startswith(("option.Hash=", "option.Threads="))
                                               for value in arguments[black:]))
                    recorded = json.loads((entries[0]["out"] / "slot.json").read_text())
                    self_outer.assertEqual(recorded["cgroup"], group)
                    self_outer.assertEqual(recorded["saved_ancestor_nodes"], [0, 1])
                    self_outer.assertEqual(recorded["saved_ancestor_cpus"], list(slot.cpus))
                    (entries[0]["out"] / "placement.json").write_text("{}")
                    on_event("ready", jobs[0], {"pid": 1, "start_ticks": 2})
                    self_outer.assertTrue(release_callback())
                    self_outer.assertIs(authorize_go(jobs[0], {}), False)
                    return [{"identity": "p192", "pid": 1, "returncode": 0, "remaining_processes": [], "readers_done": True,
                             "gate_released": False, "gate_cancelled": True, "gate_authorized": False,
                             "gate_authorization_unknown": False, "gate_transport": "not_attempted"}]
            self_outer = self
            live = {"cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes)}
            observed = {"engines": [{"pid": 22, "native_sha256": "b" * 64},
                                    {"pid": 11, "native_sha256": "a" * 64}]}
            with patch.object(probe.placement, "verify_cgroup_live", return_value=live), \
                 patch.object(probe.os, "sched_getaffinity", return_value=set(slot.cpus), create=True), \
                 patch.object(probe, "_read_receipt", return_value={}), \
                 patch.object(probe.run, "verify_preexec_placement"), \
                 patch.object(probe.placement, "observe_game_engines", return_value=observed), \
                 patch.object(probe.wave, "WaveExecutor", return_value=Executor()):
                result = probe.ready_probe(profile="test-p192", entries=entries, runner=files[0],
                        runner_sha256=sha(files[0]), opening=files[3], opening_sha256=sha(files[3]), saved_ancestor_cpus=slot.cpus,
                        channel=channel)
            self.assertEqual(channel.members["p192"]["engines"], [11, 22])
            self.assertEqual(result["games_started"], 0)
            self.assertIs(result["runtime_admission"], False)
            self.assertIs(result["representative_search_workload_verified"], False)

            # Source-JIT wrapper identity is not the identity of the native
            # image observed after the wrapper compiles and execs it.
            entries[0]["out"] = root / "attempt2"
            files[1].write_bytes(b"modified wrapper")
            with patch.object(probe.placement, "verify_cgroup_live", return_value=live), \
                 patch.object(probe.os, "sched_getaffinity", return_value=set(slot.cpus), create=True):
                with self.assertRaisesRegex(ValueError, "engine image differs"):
                    probe.ready_probe(profile="test-p192", entries=entries, runner=files[0],
                            runner_sha256=sha(files[0]), opening=files[3], opening_sha256=sha(files[3]), saved_ancestor_cpus=slot.cpus,
                            channel=channel)
            self.assertFalse(entries[0]["out"].exists())

            files[1].write_bytes(b"white")
            original_opening = sha(files[3])
            files[3].write_bytes(b"modified opening")
            with self.assertRaisesRegex(ValueError, "opening PGN differs"):
                probe.ready_probe(profile="test-p192", entries=entries, runner=files[0],
                        runner_sha256=sha(files[0]), opening=files[3], opening_sha256=original_opening,
                        saved_ancestor_cpus=slot.cpus, channel=channel)
            self.assertFalse(entries[0]["out"].exists())

            files[3].write_bytes(b"openings")
            wrong_image = {"engines": [{"pid": 22, "native_sha256": "b" * 64},
                                       {"pid": 11, "native_sha256": "c" * 64}]}
            with patch.object(probe.placement, "verify_cgroup_live", return_value=live), \
                 patch.object(probe.os, "sched_getaffinity", return_value=set(slot.cpus), create=True), \
                 patch.object(probe, "_read_receipt", return_value={}), \
                 patch.object(probe.run, "verify_preexec_placement"), \
                 patch.object(probe.placement, "observe_game_engines", return_value=wrong_image), \
                 patch.object(probe.wave, "WaveExecutor", return_value=Executor()):
                with self.assertRaisesRegex(ValueError, "observed engine identity"):
                    probe.ready_probe(profile="test-p192", entries=entries, runner=files[0],
                            runner_sha256=sha(files[0]), opening=files[3], opening_sha256=original_opening,
                            saved_ancestor_cpus=slot.cpus, channel=channel)

    def test_narrow_controller_or_unrelated_parent_refuses_before_spawn(self):
        """The READY path only inherits a checked controller node envelope."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slot = topology.Slot("p192", tuple(range(192)), tuple((0, i) for i in range(96)),
                                 (0, 1), 192, True, "default")
            controller_path = root / "cohort" / "controller"
            controller_path.mkdir(parents=True)
            (controller_path / "cgroup.procs").write_text(str(os.getpid()))
            controller = {"path": str(controller_path), "device": 1, "inode": 2,
                          "cpus": [190, 191], "memory_nodes": [0, 1], "memory_max": 1024}
            group = {"path": str(root / "cohort" / "slot-000"), "device": 1, "inode": 3,
                     "cpus": list(slot.cpus), "memory_nodes": [0, 1], "memory_max": 1024}
            output = root / "not-created"
            entries = [{"slot": slot, "out": output, "opening_start": 1, "engines": []}]
            class Channel:
                def handoff(self):
                    return {"games": {"p192": group}, "controller": controller,
                            "runtime_admission": False}
            for kind in ("narrow", "forged-controller", "outside-parent"):
                with self.subTest(kind=kind):
                    group["path"] = str(root / ("outside" if kind == "outside-parent" else "cohort") / "slot-000")
                    actual_controller = {**controller, "memory_nodes": [0] if kind == "narrow" else [0, 1]}
                    def observe(record):
                        if kind == "forged-controller" and record is controller:
                            raise ValueError("owned cgroup effective masks differ from their original receipt")
                        return actual_controller if record is controller else group
                    with patch.object(probe, "_file_sha", return_value="a" * 64), \
                         patch.object(probe.placement, "verify_cgroup_live", side_effect=observe), \
                         patch.object(probe.os, "sched_getaffinity", return_value={190, 191}, create=True), \
                         patch.object(probe.wave, "WaveExecutor") as spawn:
                        with self.assertRaisesRegex(ValueError, "controller memory nodes|supervisor parent|effective masks"):
                            probe.ready_probe(profile="test-p192", entries=entries,
                                              runner=root / "runner", runner_sha256="a" * 64,
                                              opening=root / "openings", opening_sha256="a" * 64,
                                              saved_ancestor_cpus=slot.cpus, channel=Channel())
                    spawn.assert_not_called()
                    self.assertFalse(output.exists())

    def test_p16_full_cohort_uses_live_controller_node_envelope(self):
        """A CPU-reserved controller still encompasses both live NUMA nodes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = []
            for name in ("runner", "white", "black", "openings"):
                path = root / name
                path.write_bytes(name.encode())
                files.append(path)
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            cohort = root / "cohort"
            controller_path = cohort / "controller"
            controller_path.mkdir(parents=True)
            (controller_path / "cgroup.procs").write_text(str(os.getpid()))
            controller = {"path": str(controller_path), "device": 1, "inode": 2,
                          "cpus": list(range(176, 192)), "memory_nodes": [0, 1], "memory_max": 1024}
            entries, groups = [], {}
            for index in range(11):
                slot_id = f"slot-{index:03d}"
                cpus = tuple(range(16 * index, 16 * (index + 1)))
                node = 0 if index < 6 else 1
                slot = topology.Slot(slot_id, cpus, tuple((node, index * 8 + j) for j in range(8)),
                                     (node,), 16, True, "default")
                groups[slot_id] = {"path": str(cohort / slot_id), "device": 1, "inode": 10 + index,
                                   "cpus": list(cpus), "memory_nodes": [node], "memory_max": 1024}
                entries.append({"slot": slot, "out": root / "jobs" / slot_id, "opening_start": index + 1,
                    "engines": [{"id": "white", "path": files[1], "whole_sha256": sha(files[1]),
                                 "native_sha256": "a" * 64, "tt_bytes": 12 << 30},
                                {"id": "black", "path": files[2], "whole_sha256": sha(files[2]),
                                 "native_sha256": "b" * 64, "tt_bytes": 12 << 30}]})
            class Channel:
                def handoff(self):
                    return {"games": groups, "controller": controller, "runtime_admission": False}
                def active(self, members):
                    self.members = members
                    return True
                def settled(self):
                    return True
            channel = Channel()
            self_outer = self
            class Executor:
                def run_wave(self, jobs, wall_seconds, release_callback, on_event, *, authorize_go, observe_transport):
                    self_outer.assertEqual(len(jobs), 11)
                    for job, entry in zip(jobs, entries):
                        config = json.loads((entry["out"] / "slot.json").read_text())
                        self_outer.assertEqual(config["slot"]["cpus"], list(entry["slot"].cpus))
                        self_outer.assertEqual(config["slot"]["memory_nodes"], list(entry["slot"].memory_nodes))
                        self_outer.assertEqual(config["saved_ancestor_nodes"], [0, 1])
                        self_outer.assertEqual(config["saved_ancestor_cpus"], list(range(192)))
                        self_outer.assertEqual(config["cgroup"], groups[entry["slot"].id])
                        self_outer.assertTrue(set(controller["cpus"]).isdisjoint(entry["slot"].cpus))
                        self_outer.assertIn("tc=30:00+3", job.argv)
                        self_outer.assertIn("option.Ponder=false", job.argv)
                        on_event("ready", job, {"pid": 1, "start_ticks": 2})
                        self_outer.assertIs(authorize_go(job, {}), False)
                    self_outer.assertTrue(release_callback())
                    return [{"identity": job.identity, "pid": 1, "returncode": 0,
                             "remaining_processes": [], "readers_done": True,
                             "gate_released": False, "gate_cancelled": True,
                             "gate_authorized": False, "gate_authorization_unknown": False,
                             "gate_transport": "not_attempted"} for job in jobs]
            observed = {"engines": [{"pid": 11, "native_sha256": "a" * 64},
                                    {"pid": 22, "native_sha256": "b" * 64}]}
            with patch.object(probe.placement, "verify_cgroup_live", side_effect=lambda record: record), \
                 patch.object(probe.os, "sched_getaffinity", return_value=set(controller["cpus"]), create=True), \
                 patch.object(probe, "_read_receipt", return_value={}), \
                 patch.object(probe.run, "verify_preexec_placement"), \
                 patch.object(probe.placement, "observe_game_engines", return_value=observed), \
                 patch.object(probe.wave, "WaveExecutor", return_value=Executor()):
                result = probe.ready_probe(profile="test-p16", entries=entries, runner=files[0],
                    runner_sha256=sha(files[0]), opening=files[3], opening_sha256=sha(files[3]),
                    saved_ancestor_cpus=tuple(range(192)), channel=channel)
            self.assertEqual(len(channel.members), 11)
            self.assertEqual(result["games_started"], 0)
            self.assertIs(result["runtime_admission"], False)

    def test_context_and_receipt_are_recorded_without_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "receipt.json"
            report, process = {"sample": "example"}, object()
            recorded = []
            with patch.object(probe.peak_supervisor, "observe", return_value=(report, process)), \
                 patch.object(probe.peak_receipt, "inspect_diagnostic"), \
                 patch.object(probe.peak_receipt, "record_diagnostic", side_effect=lambda append, report, expected:
                              (append("campaign.memory_peak_diagnostic", {"runtime_admission": False}), {"ok": True})[1]):
                result, owner = probe.observe_and_record(observe_args={}, expected_context=lambda: {"fresh": True},
                                 report_path=report_path, append=lambda kind, data: recorded.append((kind, data)))
            self.assertIs(owner, process)
            self.assertEqual(result, {"ok": True})
            self.assertEqual(recorded[0][1]["report_bytes_sha256"], hashlib.sha256(report_path.read_bytes()).hexdigest())
            self.assertIs(recorded[0][1]["runtime_admission"], False)

    def test_failed_receipt_keeps_owner_and_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            report, process = {"observation": "retained"}, object()
            with patch.object(probe.peak_supervisor, "observe", return_value=(report, process)), \
                 patch.object(probe.peak_receipt, "inspect_diagnostic", side_effect=ValueError("bad context")):
                with self.assertRaises(probe.peak_supervisor.SupervisorFailure) as error:
                    probe.observe_and_record(observe_args={}, expected_context=lambda: {},
                        report_path=Path(tmp) / "receipt.json", append=lambda *_: None)
            self.assertIs(error.exception.process, process)
            self.assertIs(error.exception.report, report)

    def test_pre_ready_oom_is_recorded_without_losing_child_handle(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "failure.json"
            process = object()
            evidence = {"format": "rove4k-pre-go-probe-failure-v1", "cause": "pre-READY EOF",
                        "oom_observed": True, "all_groups_read": True,
                        "physical_settlement_proven": False, "runtime_admission": False,
                        "scored_qualification": False,
                        "groups": [{"group": "slot-000", "observed_events": {"oom_kill": 1}}]}
            failure = probe.peak_supervisor.SupervisorFailure("pre-READY EOF", process, evidence)
            recorded = []
            with patch.object(probe.peak_supervisor, "observe", side_effect=failure):
                with self.assertRaises(probe.peak_supervisor.SupervisorFailure) as caught:
                    probe.observe_and_record(observe_args={}, expected_context=lambda: {}, report_path=report_path,
                        append=lambda kind, data: recorded.append((kind, data)))
            self.assertIs(caught.exception, failure)
            self.assertIs(failure.process, process)
            self.assertEqual(json.loads(report_path.read_text(encoding="ascii")), evidence)
            self.assertEqual(recorded[0][0], "campaign.memory_peak_diagnostic_failed")
            self.assertTrue(recorded[0][1]["oom_observed"])
            self.assertEqual(recorded[0][1]["report_bytes_sha256"], hashlib.sha256(report_path.read_bytes()).hexdigest())
            self.assertFalse(recorded[0][1]["runtime_admission"])

    def test_failure_report_write_or_journal_error_preserves_original_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = object()
            evidence = {"oom_observed": False, "all_groups_read": False}
            for fail_at in ("write", "journal"):
                failure = probe.peak_supervisor.SupervisorFailure("timeout", process, evidence)
                report_path = Path(tmp) / (fail_at + ".json")
                def append(*_):
                    if fail_at == "journal":
                        raise OSError("journal unavailable")
                original = probe._persist_report
                def persist(*args):
                    if fail_at == "write":
                        raise OSError("storage unavailable")
                    return original(*args)
                with patch.object(probe.peak_supervisor, "observe", side_effect=failure), \
                     patch.object(probe, "_persist_report", side_effect=persist):
                    with self.assertRaises(probe.peak_supervisor.SupervisorFailure) as caught:
                        probe.observe_and_record(observe_args={}, expected_context=lambda: {},
                                                 report_path=report_path, append=append)
                self.assertIs(caught.exception, failure)
                self.assertIs(failure.process, process)
                self.assertIn("unavailable", failure.evidence_persistence_error)

    def test_unknown_go_preserves_owner_observations(self):
        observations = [{"identity": "p192", "gate_transport": "uncertain"}]
        with self.assertRaises(probe.ProbeFailure) as error:
            probe._require_unreleased(observations, ["p192"])
        self.assertIs(error.exception.observations, observations)


if __name__ == "__main__":
    unittest.main()
