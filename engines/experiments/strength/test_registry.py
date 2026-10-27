import hashlib
import json
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from registry import Artifact, CHECKS, admit_to_test_league, smt_runtime_evidence
from topology import Cpu, Topology


class RegistryTests(unittest.TestCase):
    def fixture(self, directory):
        path = directory / "qualified-file"
        path.write_bytes(b"contract-fixture-only")
        item = Artifact("A-test-p4", "A", path, "test", "test-p4", 4, 96 << 20, 24,
                        "source-jit", True, hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, "b" * 64)
        report = {"format": "rove4k-qualification-v1", "complete": True, "failures": [],
                  "division": "general4k", "artifact": item.identity(), "checks": dict.fromkeys(CHECKS, True),
                  "observations": {"startup_ms": 100, "workers": 4, "positive_cpu_workers": 4,
                                   "tt_bytes": 96 << 20, "runtime_native_sha256": "b" * 64,
                                   "physical_cores": 4, "logical_cpus": 4,
                                   "temporary_cleanup_while_live": True, "nbrq_replay": True, "nbrq_generation": True}}
        return item, report

    def write_receipt(self, directory, report):
        path = directory / "qualification.json"
        data = json.dumps(report, allow_nan=True).encode()
        path.write_bytes(data)
        return path, hashlib.sha256(data).hexdigest()

    def test_receipt_binding_and_physical_placement_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            artifact, report = self.fixture(directory)
            path, digest = self.write_receipt(directory, report)
            self.assertTrue(admit_to_test_league(artifact, path, digest)["qualified"])
            for name, value in (("physical_cores", 1), ("runtime_native_sha256", "c" * 64),
                                ("startup_ms", float("nan")), ("positive_cpu_workers", 3), ("nbrq_generation", False)):
                with self.subTest(name=name):
                    changed = {**report, "observations": {**report["observations"], name: value}}
                    path, digest = self.write_receipt(directory, changed)
                    with self.assertRaises(ValueError):
                        admit_to_test_league(artifact, path, digest)
            changed = {**report, "artifact": {**report["artifact"], "purpose": "submission"}}
            path, digest = self.write_receipt(directory, changed)
            with self.assertRaisesRegex(ValueError, "exact TEST"):
                admit_to_test_league(artifact, path, digest)

    def test_original_bytes_and_receipt_hash_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            artifact, report = self.fixture(directory)
            path, digest = self.write_receipt(directory, report)
            with self.assertRaisesRegex(ValueError, "receipt identity"):
                admit_to_test_league(artifact, path, "0" * 64)
            artifact.path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "artifact bytes"):
                admit_to_test_league(artifact, path, digest)

    def test_named_resources_and_submission_scope_do_not_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact, report = self.fixture(Path(tmp).resolve())
            row = {**artifact.__dict__, "workers": 256}
            with self.assertRaisesRegex(ValueError, "worker count"):
                Artifact(**row)
            row = {**artifact.__dict__, "tt_bytes": 128 << 20}
            with self.assertRaisesRegex(ValueError, "TT extent"):
                Artifact(**row)

    def test_new_smt_profiles_remain_blocked_without_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            original, baseline = self.fixture(directory)
            for profile_id, workers, physical, rove_tt, peer_tt in (
                    ("test-p16", 16, 8, 12 << 30, 16 << 30),
                    ("test-p192", 192, 96, 192 << 30, 128 << 30)):
                for family, entry, tt in (("A", 24, rove_tt), ("ice4", 8, peer_tt)):
                    with self.subTest(profile=profile_id, family=family):
                        artifact = Artifact(**{**original.__dict__, "id": profile_id + "-" + family,
                                               "profile": profile_id, "family": family, "workers": workers,
                                               "entry_bytes": entry, "tt_bytes": tt})
                        artifact.verify_bytes()
                        report = {**baseline, "artifact": artifact.identity(),
                                  "observations": {**baseline["observations"], "workers": workers,
                                                   "positive_cpu_workers": workers, "tt_bytes": tt,
                                                   "physical_cores": physical, "logical_cpus": workers}}
                        path, digest = self.write_receipt(directory, report)
                        with self.assertRaisesRegex(ValueError, "SMT TEST runtime and placement"):
                            admit_to_test_league(artifact, path, digest)

    def test_smt_runtime_evidence_does_not_promote_tt_or_score(self):
        cpus = [value for core in range(8) for value in (core, core + 8)]
        topology = Topology(tuple(Cpu(cpu, 0, cpu % 8, 0, (cpu % 8, cpu % 8 + 8)) for cpu in cpus),
                            tuple(cpus), (0,), {"0": [10]}, "fixture").to_record()
        artifact = SimpleNamespace(profile="test-p16", workers=16, tt_bytes=16 << 30, entry_bytes=8,
                                   sha256="a" * 64, native_sha256="b" * 64)
        sessions = []
        for index, label in enumerate(("cold", "warm", "active-quit", "active-eof")):
            pid = 100 + index
            owner = {"pid": pid, "pgid": pid, "session": pid, "start_ticks": 500 + index,
                     "whole_sha256": artifact.sha256, "runtime_native_sha256": artifact.native_sha256}
            as_limit, cpu_limits = (16 << 30) + (768 << 20), [2240, 2272]
            preexec = {"pid": pid, "requested_cpus": sorted(cpus), "effective_cpus": sorted(cpus),
                       "requested_nodes": [0], "effective_allowed_nodes": [0, 1], "fallback": None,
                       "requested_policy": "interleave",
                       "observed_policy": {"available": True, "mode": 3, "nodes": [0]},
                       "runtime_limits": {"address_space": [as_limit] * 2, "cpu": cpu_limits},
                       "child_inherited_limits": {"address_space": [-1, -1], "cpu": [-1, -1]}}
            budget = {"profile": artifact.profile, "workers": 16, "tt_bytes": artifact.tt_bytes,
                      "required_available_bytes": 17 << 30, "address_space_bytes": as_limit,
                      "other_peak_bytes": 768 << 20, "effective_cpus": 16, "wall_seconds": 180,
                      "cpu_seconds": cpu_limits, "parent_limits": {"address_space": [-1, -1], "cpu": [-1, -1]},
                      "availability": {"host_available_bytes": 20 << 30, "cgroup_remaining_bytes": [],
                                       "effective_available_bytes": 20 << 30}}
            session = {"label": label, "owner": owner, "preexec_placement": preexec, "runtime_budget": budget,
                       "image": {"native_sha256": artifact.native_sha256,
                                 "tt": {"pointer": 0x110, "tt_bytes": artifact.tt_bytes,
                                        "mappings": [{"start": 0x100, "end": 0x110 + artifact.tt_bytes,
                                                      "permissions": "rw-p"}],
                                        "mapping_extent_verified": True}},
                       "finish": {"returncode": 0, "readers_joined": True, "reaped": True,
                                  "forced_cleanup": False, "original_identity_retained_until_other_members_absent": True,
                                  "leader_exited_with_other_members": label == "active-quit",
                                  "other_members_observed": [999] if label == "active-quit" else []},
                       "cleanup": {"owned_group_absent": True, "readers_joined": True, "errors": [],
                                   "forced_cleanup": False, "settled_before_cleanup": True, "reaped": True}}
            sessions.append(session)
        worker_rows = [{"tid": 200 + index, "start_ticks": 1000 + index, "cpus": sorted(cpus),
                        "cpu_ticks_first": 1, "cpu_ticks_last": 2} for index in range(16)]
        sessions[0]["searches"] = [{"worker_affinity_evidence": worker_rows,
                                    "worker_affinity_evidence_complete": True,
                                    "worker_ids": [row["tid"] for row in worker_rows],
                                    "positive_cpu_worker_ids": [row["tid"] for row in worker_rows]}]
        sessions[0]["post_go_tt_numa"] = {
            "owner": {key: sessions[0]["owner"][key] for key in ("pid", "pgid", "session", "start_ticks")},
            "tt_bytes": artifact.tt_bytes, "tt_pointer": 0x110, "all_mapping_starts_observed": True,
            "tt_mappings": [{"start": 0x100, "end": 0x110 + artifact.tt_bytes, "permissions": "rw-p"}],
            "tt_overlapping_vmas": [{"mapping_start": 0x100, "node_pages": {0: 2},
                                      "raw": "100 default anon=2 N0=2"}],
            "matching_vma_starts": [0x100], "observed_page_nodes": [0]}
        report = {"topology": topology, "placement": {"cpu_ids": sorted(cpus), "memory_nodes": [0]},
                  "sessions": sessions}
        observed = smt_runtime_evidence(report, artifact)
        self.assertTrue(observed["host_runtime_evidence_complete"])
        self.assertTrue(observed["tt_overlapping_vma_pages_observed"])
        self.assertFalse(observed["tt_only_pages_proven"])
        self.assertFalse(observed["scored_game_placement_confirmed"])
        # Synthetic peer-schema observations exercise the Rove resource layout
        # separately; the current Rove runtime driver does not emit this schema.
        rove = SimpleNamespace(profile="test-p16", workers=16, tt_bytes=12 << 30,
                               entry_bytes=24, sha256="c" * 64, native_sha256="d" * 64)
        rove_report = deepcopy(report)
        other = 768 << 20
        for session in rove_report["sessions"]:
            session["owner"].update(whole_sha256=rove.sha256, runtime_native_sha256=rove.native_sha256)
            session["image"]["native_sha256"] = rove.native_sha256
            session["image"]["tt"].update(tt_bytes=rove.tt_bytes)
            session["image"]["tt"]["mappings"][0]["end"] = 0x110 + rove.tt_bytes
            budget = session["runtime_budget"]
            budget.update(tt_bytes=rove.tt_bytes, address_space_bytes=rove.tt_bytes + other,
                          required_available_bytes=rove.tt_bytes + other + (256 << 20))
            session["preexec_placement"]["runtime_limits"]["address_space"] = [rove.tt_bytes + other] * 2
        numa = rove_report["sessions"][0]["post_go_tt_numa"]
        numa["tt_bytes"] = rove.tt_bytes
        numa["tt_mappings"][0]["end"] = 0x110 + rove.tt_bytes
        self.assertTrue(smt_runtime_evidence(rove_report, rove)["host_runtime_evidence_complete"])
        self.assertFalse(smt_runtime_evidence(rove_report, rove)["scored_game_placement_confirmed"])
        rove_report["sessions"][0]["owner"]["runtime_native_sha256"] = artifact.native_sha256
        self.assertFalse(smt_runtime_evidence(rove_report, rove)["host_runtime_evidence_complete"])
        saved = json.loads(json.dumps(report))
        self.assertEqual(smt_runtime_evidence(saved, artifact), observed)
        local = deepcopy(report)
        for session in local["sessions"]:
            session["preexec_placement"]["requested_policy"] = "inherit"
            session["preexec_placement"]["observed_policy"] = {"available": True, "mode": 4, "nodes": []}
            session["preexec_placement"]["effective_allowed_nodes"] = [0]
        self.assertTrue(smt_runtime_evidence(local, artifact)["host_runtime_evidence_complete"])
        local["sessions"][0]["preexec_placement"]["effective_allowed_nodes"] = [0, 1]
        self.assertFalse(smt_runtime_evidence(local, artifact)["host_runtime_evidence_complete"])
        for mutate in ("worker", "node", "parent_limit", "identity", "policy", "unrelated_vma", "mapping_gap", "finish"):
            changed = deepcopy(report)
            if mutate == "worker":
                changed["sessions"][0]["searches"][0]["worker_affinity_evidence"][0]["cpus"] = [0]
            elif mutate == "node":
                changed["sessions"][0]["post_go_tt_numa"]["tt_overlapping_vmas"][0]["node_pages"] = {1: 2}
            elif mutate == "parent_limit":
                changed["sessions"][0]["preexec_placement"]["child_inherited_limits"]["cpu"] = [10, 10]
            elif mutate == "identity":
                changed["sessions"][0]["post_go_tt_numa"]["owner"]["start_ticks"] = 1
            elif mutate == "policy":
                changed["sessions"][0]["preexec_placement"]["observed_policy"]["nodes"] = [1]
            elif mutate == "unrelated_vma":
                row = changed["sessions"][0]["post_go_tt_numa"]["tt_overlapping_vmas"][0]
                row.update(mapping_start=0x900, raw="900 default anon=2 N0=2")
            elif mutate == "mapping_gap":
                changed["sessions"][0]["post_go_tt_numa"]["tt_mappings"][0]["end"] -= 4096
            else:
                changed["sessions"][0]["finish"]["forced_cleanup"] = True
            with self.subTest(mutate=mutate):
                self.assertFalse(smt_runtime_evidence(changed, artifact)["host_runtime_evidence_complete"])


if __name__ == "__main__":
    unittest.main()
