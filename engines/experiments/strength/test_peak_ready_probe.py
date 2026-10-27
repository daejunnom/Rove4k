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
                        "engines": [{"id": "white", "path": files[1], "whole_sha256": sha(files[1]), "native_sha256": "a" * 64, "tt_bytes": 12 << 30},
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
                    self_outer.assertEqual(json.loads((entries[0]["out"] / "slot.json").read_text())["cgroup"], group)
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

    def test_unknown_go_preserves_owner_observations(self):
        observations = [{"identity": "p192", "gate_transport": "uncertain"}]
        with self.assertRaises(probe.ProbeFailure) as error:
            probe._require_unreleased(observations, ["p192"])
        self.assertIs(error.exception.observations, observations)


if __name__ == "__main__":
    unittest.main()
