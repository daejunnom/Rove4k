"""Small synthetic cgroup/proc fixtures; no real engine, TT or cloud calls."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    from . import overhead
except ImportError:
    import overhead


RUNNER = b"fastchess test image"
ENGINE1 = b"first engine test image"
ENGINE2 = b"second engine test image"
CONTROLLER = b"controller test image"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Fixture:
    def __init__(self, base, profile="test-p16"):
        self.base = Path(base).resolve()
        self.root = self.base / "cgroup"
        self.root.mkdir()
        self.proc = self.base / "proc"
        (self.proc / "sys/kernel/random").mkdir(parents=True)
        (self.proc / "sys/kernel/random/boot_id").write_text("e4b848ab-9f21-4130-b8ae-c8c5b02e4299\n")
        self.profile = profile
        self.workers = 16 if profile == "test-p16" else 192
        self.count = 11 if self.workers == 16 else 1
        self.cpu_masks = {}
        self.games = []
        self.members = {}
        for number in range(self.count):
            cpus = tuple(range(number * self.workers, (number + 1) * self.workers))
            nodes = (number // 3,) if self.workers == 16 else (0, 1)
            directory = self.root / ("slot-%03d" % number)
            self.group(directory, cpus, nodes)
            self.games.append({"slot": directory.name, "path": directory, "cpus": cpus, "nodes": nodes,
                               "artifacts": [{"id": "A", "whole_sha256": "a" * 64,
                                              "native_sha256": sha(ENGINE1), "tt_bytes": 12 << 30},
                                             {"id": "B", "whole_sha256": "b" * 64,
                                              "native_sha256": sha(ENGINE2), "tt_bytes": 16 << 30}]})
        self.control = self.root / "controller"
        control_cpus = tuple(range(176, 192)) if self.workers == 16 else tuple(range(192))
        self.group(self.control, control_cpus, (0, 1, 2, 3) if self.workers == 16 else (0, 1))
        self.observer = overhead.CohortPeakObserver(profile=profile, root=self.root, games=self.games,
                                                     controller=self.control, runner_sha256=sha(RUNNER),
                                                     proc_root=self.proc, affinity=lambda pid: self.cpu_masks[pid])

    @staticmethod
    def group(path, cpus, nodes):
        path.mkdir()
        for name, value in {"memory.current": "0\n", "memory.peak": "0\n",
                            "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n",
                            "cgroup.events": "populated 0\nfrozen 0\n", "cgroup.procs": "",
                            "cpuset.cpus.effective": ",".join(map(str, cpus)) + "\n",
                            "cpuset.mems.effective": ",".join(map(str, nodes)) + "\n"}.items():
            (path / name).write_text(value, encoding="ascii")

    def process(self, pid, image, cpus, *, threads=0, ticks=100):
        path = self.proc / str(pid)
        path.mkdir()
        fields = ["S"] + ["1"] * 19
        fields[19] = str(ticks)
        (path / "stat").write_text(str(pid) + " (test engine) " + " ".join(fields) + "\n", encoding="ascii")
        (path / "exe").write_bytes(image)
        (path / "task").mkdir()
        self.cpu_masks[pid] = set(cpus)
        for i in range(threads):
            tid = pid if i == 0 else pid * 1000 + i
            (path / "task" / str(tid)).mkdir()
            self.cpu_masks[tid] = set(cpus)

    def active(self, *, engine_threads=None):
        if engine_threads is None:
            engine_threads = self.workers
        controller_pid = 42
        control_cpus = tuple(range(176, 192)) if self.workers == 16 else tuple(range(192))
        self.process(controller_pid, CONTROLLER, control_cpus)
        (self.control / "cgroup.procs").write_text(f"{controller_pid}\n")
        (self.control / "cgroup.events").write_text("populated 1\nfrozen 0\n")
        (self.control / "memory.current").write_text("200\n")
        (self.control / "memory.peak").write_text("300\n")
        for i, game in enumerate(self.games):
            runner, engine1, engine2 = 1000 + i * 10, 1001 + i * 10, 1002 + i * 10
            self.process(runner, RUNNER, game["cpus"])
            self.process(engine1, ENGINE1, game["cpus"], threads=engine_threads)
            self.process(engine2, ENGINE2, game["cpus"], threads=engine_threads)
            group = game["path"]
            (group / "cgroup.procs").write_text(f"{runner}\n{engine1}\n{engine2}\n")
            (group / "cgroup.events").write_text("populated 1\nfrozen 0\n")
            (group / "memory.current").write_text(str(1000 + i) + "\n")
            (group / "memory.peak").write_text(str(1200 + i) + "\n")
            self.members[game["slot"]] = {"runner": runner, "engines": [engine1, engine2]}
        return self.observer.sample_active(members=self.members, controller_pid=controller_pid,
                                           controller_sha256=sha(CONTROLLER))

    def end_games(self):
        for game in self.games:
            row = self.members[game["slot"]]
            for pid in [row["runner"], *row["engines"]]:
                shutil.rmtree(self.proc / str(pid))
            (game["path"] / "cgroup.procs").write_text("")
            (game["path"] / "cgroup.events").write_text("populated 0\nfrozen 0\n")
            (game["path"] / "memory.current").write_text("0\n")


class CohortPeakObservationTests(unittest.TestCase):
    def test_p16_full_cohort_records_whole_peaks_and_keeps_admission_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            begin = fixture.observer.begin()
            self.assertEqual(begin["fresh_empty_groups"], 12)
            sample = fixture.active()
            self.assertEqual(len(sample["games"]), 11)
            fixture.end_games()
            result = fixture.observer.finish(per_game_headroom_bytes=100, controller_headroom_bytes=50)
            self.assertEqual(result["arithmetic"]["observed_max_game_peak_bytes"], 1210)
            self.assertEqual(result["arithmetic"]["legacy_per_game_overhead_bytes"], 1310)
            self.assertEqual(result["arithmetic"]["all_in_per_game_envelope_bytes"], 1310)
            self.assertEqual(result["arithmetic"]["all_in_cohort_envelope_bytes"], 1310 * 11 + 350)
            self.assertTrue(result["arithmetic"]["legacy_double_counts_tt"])
            self.assertTrue(result["test_inputs"])
            self.assertFalse(result["runtime_admission"])
            self.assertFalse(result["scored_qualification"])
            self.assertFalse(result["future_peak_bound_verified"])
            self.assertFalse(result["all_tt_resident_verified"])
            self.assertFalse(result["artifact_source_provenance_verified"])
            self.assertFalse(result["observer_loaded_source_verified"])
            self.assertFalse(result["process_charges_complete"])
            self.assertFalse(result["simultaneous_cohort_presence_verified"])
            self.assertEqual(len(result["observation_sha256"]), 64)
            self.assertEqual(result["cgroup_root"], str(fixture.root))
            self.assertEqual(result["plan"][0]["cgroup_path"], str(fixture.games[0]["path"]))
            inspect = {"profile": fixture.profile, "plan": result["plan"], "boot_id": result["boot_id"],
                       "cgroup_root": str(fixture.root), "controller_cgroup_path": str(fixture.control),
                       "runner_sha256": sha(RUNNER), "controller_sha256": sha(CONTROLLER),
                       "observer_source_sha256": result["observer_source_sha256"],
                       "now_monotonic_ns": result["finished_ns"] + 100, "max_age_ns": 1000}
            self.assertFalse(overhead.inspect_report(result, **inspect)["authenticated"])
            self.assertFalse(overhead.inspect_report(result, **inspect)["runtime_admission"])
            self.assertEqual(result["format"], "rove4k-cohort-peak-observation-v2")
            old = dict(result, format="rove4k-cohort-peak-observation-v1")
            del old["observation_sha256"]
            raw = json.dumps(old, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
            old["observation_sha256"] = hashlib.sha256(raw).hexdigest()
            with self.assertRaisesRegex(ValueError, "context differs"):
                overhead.inspect_report(old, **inspect)
            tampered = dict(result, cgroup_root="/other")
            with self.assertRaisesRegex(ValueError, "digest differs"):
                overhead.inspect_report(tampered, **inspect)
            forged = dict(tampered)
            del forged["observation_sha256"]
            raw = json.dumps(forged, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
            forged["observation_sha256"] = hashlib.sha256(raw).hexdigest()
            with self.assertRaisesRegex(ValueError, "context differs"):
                overhead.inspect_report(forged, **inspect)
            with self.assertRaisesRegex(ValueError, "freshness"):
                overhead.inspect_report(result, **dict(inspect, now_monotonic_ns=result["finished_ns"] + 1001))
            with self.assertRaisesRegex(ValueError, "active-cohort"):
                fixture.observer.finish(per_game_headroom_bytes=100, controller_headroom_bytes=50)

    def test_p192_uses_a_separate_all_in_envelope_without_subtracting_tt(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp, "test-p192")
            fixture.observer.begin()
            fixture.active()
            fixture.end_games()
            result = fixture.observer.finish(per_game_headroom_bytes=50, controller_headroom_bytes=20)
            self.assertEqual(result["arithmetic"]["all_in_per_game_envelope_bytes"], 1250)
            self.assertEqual(result["arithmetic"]["all_in_cohort_envelope_bytes"], 1570)
            self.assertFalse(result["physical_topology_verified"])

    def test_ready_records_lazy_workers_without_claiming_search_or_activity(self):
        for profile, requested_workers in (("test-p16", 16), ("test-p192", 192)):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                fixture = Fixture(tmp, profile)
                fixture.observer.begin()
                sample = fixture.active(engine_threads=1)
                for game in sample["games"]:
                    for engine in game["engines"]:
                        self.assertEqual(engine["observed_thread_count"], 1)
                        self.assertEqual(engine["requested_worker_count"], requested_workers)
                        self.assertEqual(engine["thread_ids"], [engine["pid"]])
                        self.assertEqual(engine["thread_affinities"], [
                            {"tid": engine["pid"], "cpu_mask": game["cpus"]}])
                        self.assertFalse(engine["worker_set_complete_verified"])
                        self.assertFalse(engine["worker_cpu_activity_verified"])
                fixture.end_games()
                result = fixture.observer.finish(per_game_headroom_bytes=50, controller_headroom_bytes=20)
                self.assertFalse(result["worker_completeness_verified"])
                self.assertFalse(result["worker_cpu_activity_verified"])
                self.assertFalse(result["representative_search_workload_verified"])
                self.assertFalse(result["runtime_admission"])
                self.assertFalse(result["scored_qualification"])

    def test_ready_requires_actual_engine_leader_thread(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp, "test-p192")
            fixture.observer.begin()
            with self.assertRaisesRegex(ValueError, "leader thread"):
                fixture.active(engine_threads=0)

    def test_reused_group_and_wrong_cohort_geometry_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            (fixture.games[0]["path"] / "memory.peak").write_text("1\n")
            with self.assertRaisesRegex(ValueError, "fresh empty"):
                fixture.observer.begin()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            (fixture.games[0]["path"] / "memory.events").write_text("oom 1\noom_kill 0\n")
            with self.assertRaisesRegex(ValueError, "fresh empty"):
                fixture.observer.begin()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            with self.assertRaisesRegex(ValueError, "exactly eleven"):
                overhead.CohortPeakObserver(profile="test-p16", root=fixture.root, games=fixture.games[:-1],
                                             controller=fixture.control, runner_sha256=sha(RUNNER),
                                             proc_root=fixture.proc, affinity=lambda _: {0})

    def test_wrong_controller_reserve_and_oversize_tt_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            (fixture.control / "cpuset.cpus.effective").write_text("0-15\n")
            with self.assertRaisesRegex(ValueError, "reserved CPUs"):
                fixture.observer.begin()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            fixture.games[0]["artifacts"][0]["tt_bytes"] = (16 << 30) + 1
            with self.assertRaisesRegex(ValueError, "TT extent exceeds"):
                overhead.CohortPeakObserver(profile="test-p16", root=fixture.root, games=fixture.games,
                                             controller=fixture.control, runner_sha256=sha(RUNNER),
                                             proc_root=fixture.proc, affinity=lambda _: {0})

    def test_wrong_native_and_wrong_worker_affinity_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            fixture.observer.begin()
            fixture.active()
            pid = fixture.members["slot-000"]["engines"][0]
            (fixture.proc / str(pid) / "exe").write_bytes(b"not the selected image")
            with self.assertRaisesRegex(ValueError, "executable"):
                fixture.observer.sample_active(members=fixture.members, controller_pid=42, controller_sha256=sha(CONTROLLER))
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp)
            fixture.observer.begin()
            fixture.active()
            pid = fixture.members["slot-000"]["engines"][0]
            fixture.cpu_masks[pid * 1000 + 1] = {16}
            with self.assertRaisesRegex(ValueError, "thread affinity"):
                fixture.observer.sample_active(members=fixture.members, controller_pid=42, controller_sha256=sha(CONTROLLER))

    def test_controller_image_identity_and_sample_count_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp, "test-p192")
            fixture.observer.begin()
            fixture.active()
            (fixture.proc / "42" / "exe").write_bytes(b"different controller")
            with self.assertRaisesRegex(ValueError, "controller executable identity"):
                fixture.observer.sample_active(members=fixture.members, controller_pid=42,
                                               controller_sha256=sha(b"different controller"))
            fixture.end_games()
            with self.assertRaisesRegex(ValueError, "controller cgroup"):
                fixture.observer.finish(per_game_headroom_bytes=50, controller_headroom_bytes=20)
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp, "test-p192")
            fixture.observer.begin()
            fixture.observer.samples = [None] * 64
            with self.assertRaisesRegex(ValueError, "sample count"):
                fixture.observer.sample_active(members={"slot-000": {}}, controller_pid=42,
                                               controller_sha256=sha(CONTROLLER))

    def test_observer_source_change_is_not_reported_as_the_original_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp, "test-p192")
            fixture.observer.begin()
            fixture.active()
            fixture.end_games()
            real = overhead._sha_file
            def replaced(path):
                return "f" * 64 if Path(path) == Path(overhead.__file__) else real(path)
            with patch.object(overhead, "_sha_file", side_effect=replaced):
                with self.assertRaisesRegex(ValueError, "observer source file changed"):
                    fixture.observer.finish(per_game_headroom_bytes=50, controller_headroom_bytes=20)
    def test_oom_and_live_migrated_engine_cannot_be_reported_as_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp, "test-p192")
            fixture.observer.begin()
            fixture.active()
            fixture.end_games()
            (fixture.games[0]["path"] / "memory.events").write_text("oom 1\noom_kill 0\n")
            with self.assertRaisesRegex(overhead.ObservationFailure, "OOM") as caught:
                fixture.observer.finish(per_game_headroom_bytes=50, controller_headroom_bytes=20)
            self.assertEqual(caught.exception.evidence["group"], "slot-000")
            self.assertEqual(caught.exception.evidence["initial_events"]["oom"], 0)
            self.assertEqual(caught.exception.evidence["final_events"]["oom"], 1)
            self.assertFalse(caught.exception.evidence["runtime_admission"])
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(tmp, "test-p192")
            fixture.observer.begin()
            fixture.active()
            game = fixture.games[0]
            (game["path"] / "cgroup.procs").write_text("")
            (game["path"] / "cgroup.events").write_text("populated 0\nfrozen 0\n")
            (game["path"] / "memory.current").write_text("0\n")
            with self.assertRaisesRegex(ValueError, "remains alive"):
                fixture.observer.finish(per_game_headroom_bytes=50, controller_headroom_bytes=20)


if __name__ == "__main__":
    unittest.main()
