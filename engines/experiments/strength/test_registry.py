import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from registry import (Artifact, CHECKS, PEER_EXACT_P192_LAYOUT, _read_smt_evidence, admit_to_test_league,
                      inspect_league_test_receipt, smt_runtime_evidence)
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

    def test_explicit_league_test_receipt_tracks_size_without_enforcing_4k(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            original, legacy = self.fixture(directory)
            legacy_receipt, legacy_pin = self.write_receipt(directory, legacy)
            with self.assertRaisesRegex(ValueError, "league-test v2"):
                inspect_league_test_receipt(original, legacy_receipt, legacy_pin)
            original.path.write_bytes(b"x" * 4097)
            artifact = Artifact(**{**original.__dict__, "whole_bytes": 4097,
                                   "sha256": hashlib.sha256(original.path.read_bytes()).hexdigest()})
            legacy = {**legacy, "artifact": artifact.identity()}
            receipt, digest = self.write_receipt(directory, legacy)
            with self.assertRaisesRegex(ValueError, "4KiB"):
                admit_to_test_league(artifact, receipt, digest)

            report = {**legacy, "format": "rove4k-qualification-v2", "division": "league-test",
                      "qualification_scope": "league-test", "functional_runtime_complete": True,
                      "test_qualified": True, "release_qualified": False, "event_target_confirmed": False,
                      "score_authorized": False, "submission_size_within_4096": False,
                      "checks": {**legacy["checks"], "size": False}}
            receipt, digest = self.write_receipt(directory, report)
            admitted = inspect_league_test_receipt(artifact, receipt, digest)
            self.assertTrue(admitted["diagnostic_eligible"])
            self.assertIs(admitted["score_authorized"], False)
            self.assertNotIn("qualified", admitted)
            self.assertIn("league-test", admitted["scope"])
            with self.assertRaisesRegex(ValueError, "4KiB"):
                admit_to_test_league(artifact, receipt, digest)
            with self.assertRaisesRegex(ValueError, "4KiB"):
                admit_to_test_league(artifact, directory / "missing-receipt.json", digest)
            with self.assertRaises(ValueError):
                Artifact(**{**artifact.__dict__, "workers": 4.0})
            with self.assertRaises(ValueError):
                Artifact(**{**artifact.__dict__, "tt_bytes": float(artifact.tt_bytes)})
            for key, replacement in (("full", 1), ("workers", 4.0)):
                altered_identity = {**report["artifact"], key: replacement}
                path, pin = self.write_receipt(directory, {**report, "artifact": altered_identity})
                with self.subTest(identity_type=key), self.assertRaisesRegex(ValueError, "exact TEST"):
                    inspect_league_test_receipt(artifact, path, pin)
            for before, after in ((b'"format": ', b'"format": "rove4k-qualification-v2", "format": '),
                                  (b'"full": true', b'"full": true, "full": true')):
                raw = json.dumps(report).encode()
                self.assertEqual(raw.count(before), 1)
                raw = raw.replace(before, after, 1)
                receipt.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, "duplicate league-test"):
                    inspect_league_test_receipt(artifact, receipt, hashlib.sha256(raw).hexdigest())
            nonfinite = {**report, "observations": {**report["observations"], "startup_ms": float("nan")}}
            path, pin = self.write_receipt(directory, nonfinite)
            with self.assertRaisesRegex(ValueError, "non-finite"):
                inspect_league_test_receipt(artifact, path, pin)
            raw = json.dumps(report).encode()
            raw = raw[:-1] + b', "unused_number": 1e999}'
            receipt.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "non-finite"):
                inspect_league_test_receipt(artifact, receipt, hashlib.sha256(raw).hexdigest())
            for mutation in (
                    {"qualification_scope": "general4k"}, {"division": "general4k"},
                    {"functional_runtime_complete": False}, {"test_qualified": False},
                    {"release_qualified": True}, {"event_target_confirmed": True}, {"score_authorized": True},
                    {"submission_size_within_4096": True}, {"submission_size_within_4096": 0},
                    {"checks": {**report["checks"], "size": True}},
                    {"checks": {**report["checks"], "size": 0}},
                    {"checks": {**report["checks"], "protocol": False}},
                    {"observations": []}, {"failures": ["protocol"]}, {"format": "unknown"}):
                with self.subTest(mutation=mutation):
                    path, pin = self.write_receipt(directory, {**report, **mutation})
                    with self.assertRaises(ValueError):
                        inspect_league_test_receipt(artifact, path, pin)

            # A small file must still record the actual submission-size fact.
            small, baseline = self.fixture(directory)
            small_report = {**report, "artifact": small.identity(), "checks": baseline["checks"],
                            "submission_size_within_4096": True}
            path, pin = self.write_receipt(directory, small_report)
            self.assertTrue(inspect_league_test_receipt(small, path, pin)["diagnostic_eligible"])
            with self.assertRaisesRegex(ValueError, "does not authorize scored"):
                admit_to_test_league(small, path, pin)
            path, pin = self.write_receipt(directory, {**small_report, "submission_size_within_4096": False})
            with self.assertRaisesRegex(ValueError, "submission size"):
                inspect_league_test_receipt(small, path, pin)

    def test_league_test_receipt_does_not_admit_unproven_peer_or_smt(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            original, baseline = self.fixture(directory)
            report = {**baseline, "format": "rove4k-qualification-v2", "division": "league-test",
                      "qualification_scope": "league-test", "functional_runtime_complete": True,
                      "test_qualified": True, "release_qualified": False, "event_target_confirmed": False,
                      "score_authorized": False, "submission_size_within_4096": True}
            smt = Artifact(**{**original.__dict__, "id": "a-p16", "profile": "test-p16",
                              "workers": 16, "tt_bytes": 12 << 30})
            smt_report = {**report, "artifact": smt.identity(),
                          "observations": {**report["observations"], "workers": 16,
                                           "positive_cpu_workers": 16, "tt_bytes": 12 << 30,
                                           "physical_cores": 8, "logical_cpus": 16}}
            path, pin = self.write_receipt(directory, smt_report)
            with self.assertRaisesRegex(ValueError, "independent SMT"):
                inspect_league_test_receipt(smt, path, pin)
            peer = Artifact(**{**original.__dict__, "id": "ice-p4", "family": "ice4", "entry_bytes": 8,
                               "tt_bytes": 128 << 20, "representation": "configurable-native"})
            path, pin = self.write_receipt(directory, {**report, "artifact": peer.identity()})
            with self.assertRaisesRegex(ValueError, "separate original-source"):
                inspect_league_test_receipt(peer, path, pin)

    def test_explicit_smt_diagnostic_binds_owned_observation_without_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            original, baseline = self.fixture(directory)
            original.path.write_bytes(b"x" * 4097)
            artifact = Artifact(**{**original.__dict__, "id": "a-p16", "profile": "test-p16",
                                   "workers": 16, "tt_bytes": 12 << 30, "whole_bytes": 4097,
                                   "sha256": hashlib.sha256(original.path.read_bytes()).hexdigest()})
            runtime_sha, source_sha = "e" * 64, "f" * 64
            binding = {"runtime_sha256": runtime_sha, "source_sha256": source_sha,
                       "boot_id": "01234567-89ab-cdef-0123-456789abcdef", "cgroup_path": "/rove4k/slot",
                       "tt_symbol": "qq", "tt_symbol_evidence_sha256": "7" * 64}
            report = {**baseline, "artifact": artifact.identity(), "format": "rove4k-qualification-v2",
                      "division": "league-test", "qualification_scope": "league-test",
                      "functional_runtime_complete": True, "test_qualified": True, "release_qualified": False,
                      "event_target_confirmed": False, "score_authorized": False,
                      "submission_size_within_4096": False, "source_sha256": source_sha,
                      "smt_binding": binding, "evidence": {"runtime": {"sha256": runtime_sha}},
                      "checks": {**baseline["checks"], "size": False},
                      "observations": {**baseline["observations"], "workers": 16, "positive_cpu_workers": 16,
                                       "tt_bytes": artifact.tt_bytes, "physical_cores": 8, "logical_cpus": 16}}
            receipt, receipt_sha = self.write_receipt(directory, report)
            smt, _ = self.smt_fixture()
            smt.update(format="rove4k-owned-smt-observation-v1", qualification_sha256=receipt_sha,
                       artifact=artifact.identity(), binding=deepcopy(binding))
            other = 768 << 20
            for session in smt["sessions"]:
                session["owner"].update(whole_sha256=artifact.sha256, runtime_native_sha256=artifact.native_sha256,
                                        boot_id=binding["boot_id"], cgroup_path=binding["cgroup_path"])
                session["image"]["native_sha256"] = artifact.native_sha256
                session["image"]["tt"].update(tt_bytes=artifact.tt_bytes, symbol=binding["tt_symbol"],
                                               symbol_evidence_sha256=binding["tt_symbol_evidence_sha256"])
                session["image"]["tt"]["mappings"][0]["end"] = 0x110 + artifact.tt_bytes
                session["runtime_budget"].update(tt_bytes=artifact.tt_bytes,
                    address_space_bytes=artifact.tt_bytes + other, required_available_bytes=0)
                session["preexec_placement"]["runtime_limits"]["address_space"] = [artifact.tt_bytes + other] * 2
                session["finish"].update(leader_exited_with_other_members=False, other_members_observed=[])
            numa = smt["sessions"][0]["post_go_tt_numa"]
            numa["tt_bytes"] = artifact.tt_bytes
            numa["tt_mappings"][0]["end"] = 0x110 + artifact.tt_bytes
            self.assertFalse(smt_runtime_evidence(smt, artifact)["host_runtime_evidence_complete"])
            self.assertTrue(smt_runtime_evidence(
                smt, artifact, require_delayed_group_observation=False)["host_runtime_evidence_complete"])
            peer = SimpleNamespace(**{**artifact.__dict__, "family": "ice4"})
            self.assertFalse(smt_runtime_evidence(
                smt, peer, require_delayed_group_observation=False)["host_runtime_evidence_complete"])
            evidence = directory / "smt-observation.json"
            def write_record(value):
                raw = json.dumps(value, sort_keys=True).encode()
                evidence.write_bytes(raw)
                return hashlib.sha256(raw).hexdigest()
            digest = write_record(smt)
            def inspect(pin=digest, **overrides):
                options = {"smt_evidence_path": evidence, "smt_evidence_sha256": pin,
                           "expected_runtime_sha256": runtime_sha, "expected_source_sha256": source_sha}
                return inspect_league_test_receipt(artifact, receipt, receipt_sha, **{**options, **overrides})
            result = inspect()
            self.assertTrue(result["diagnostic_eligible"])
            self.assertTrue(result["smt_observations_consistent"])
            self.assertFalse(result["score_authorized"])
            self.assertFalse(result["host_origin_authenticated"])
            self.assertFalse(result["source_origin_authenticated"])
            self.assertFalse(result["tt_symbol_origin_authenticated"])
            self.assertNotIn("qualified", result)
            with self.assertRaisesRegex(ValueError, "parent identity"):
                _read_smt_evidence(receipt, evidence, digest, (-1, -1))
            with self.assertRaises(ValueError):
                inspect(pin="0" * 64)
            with self.assertRaises(ValueError):
                inspect(expected_runtime_sha256="0" * 64)
            with self.assertRaises(ValueError):
                inspect(expected_source_sha256="0" * 64)
            with self.assertRaises(ValueError):
                inspect(smt_evidence_path=directory / "other.json")
            for mutation in ("qualification", "artifact", "boot", "cgroup", "symbol", "symbol_pin",
                             "pid", "duplicate_owner", "worker", "invalid_tid", "float_tid", "float_workers",
                             "float_tt", "float_other", "float_address", "float_cpu", "float_limits",
                             "mapping", "cleanup", "hard_limit", "policy", "policy_type", "policy_float"):
                altered = deepcopy(smt)
                if mutation == "qualification":
                    altered["qualification_sha256"] = "0" * 64
                elif mutation == "artifact":
                    altered["artifact"]["full"] = 1
                elif mutation in ("boot", "cgroup"):
                    altered["sessions"][0]["owner"]["boot_id" if mutation == "boot" else "cgroup_path"] = "wrong"
                elif mutation in ("symbol", "symbol_pin"):
                    altered["sessions"][0]["image"]["tt"]["symbol" if mutation == "symbol" else "symbol_evidence_sha256"] = "wrong"
                elif mutation == "pid":
                    owner = altered["sessions"][0]["owner"]
                    owner.update(pid=0, pgid=0, session=0)
                    altered["sessions"][0]["preexec_placement"]["pid"] = 0
                elif mutation == "duplicate_owner":
                    first, second = altered["sessions"][:2]
                    for key in ("pid", "pgid", "session", "start_ticks"):
                        second["owner"][key] = first["owner"][key]
                    second["preexec_placement"]["pid"] = first["owner"]["pid"]
                elif mutation == "worker":
                    altered["sessions"][0]["searches"][0]["worker_affinity_evidence"][0]["cpu_ticks_last"] = 1
                elif mutation == "invalid_tid":
                    search = altered["sessions"][0]["searches"][0]
                    search["worker_affinity_evidence"][0]["tid"] = -1
                    search["worker_ids"][0] = search["positive_cpu_worker_ids"][0] = -1
                elif mutation == "float_tid":
                    search = altered["sessions"][0]["searches"][0]
                    search["worker_affinity_evidence"][0]["tid"] = float(search["worker_ids"][0])
                    search["worker_ids"][0] = search["positive_cpu_worker_ids"][0] = 200.0
                elif mutation in ("float_workers", "float_tt", "float_other", "float_address", "float_cpu"):
                    field = {"float_workers": "workers", "float_tt": "tt_bytes", "float_other": "other_peak_bytes",
                             "float_address": "address_space_bytes", "float_cpu": "effective_cpus"}[mutation]
                    budget = altered["sessions"][0]["runtime_budget"]
                    budget[field] = float(budget[field])
                elif mutation == "float_limits":
                    limits = altered["sessions"][0]["preexec_placement"]["runtime_limits"]["cpu"]
                    limits[0] = float(limits[0])
                elif mutation == "mapping":
                    altered["sessions"][0]["image"]["tt"]["mappings"][0]["end"] -= 4096
                elif mutation == "cleanup":
                    altered["sessions"][0]["cleanup"]["owned_group_absent"] = False
                elif mutation == "hard_limit":
                    altered["sessions"][0]["preexec_placement"]["runtime_limits"]["address_space"] = [1, 1]
                elif mutation == "policy_type":
                    altered["sessions"][0]["preexec_placement"]["observed_policy"] = []
                elif mutation == "policy_float":
                    altered["sessions"][0]["preexec_placement"]["observed_policy"]["mode"] = 3.0
                else:
                    altered["sessions"][0]["preexec_placement"]["observed_policy"]["nodes"] = [1]
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    inspect(pin=write_record(altered))
            # Independently supplied pins cannot authorize a linked or escaped
            # receipt/observation path, even when bytes and hashes match.
            digest = write_record(smt)
            bad = directory / "child" / ".." / "smt-observation.json"
            with self.assertRaises(ValueError):
                inspect(pin=digest, smt_evidence_path=bad)
            protected_artifact = Artifact(**{**artifact.__dict__, "path": directory / ".env" / "qualified-file"})
            with self.assertRaisesRegex(ValueError, "allowed absolute path"):
                inspect_league_test_receipt(protected_artifact, receipt, receipt_sha)
            with self.assertRaises(ValueError):
                inspect_league_test_receipt(artifact, directory / "child" / ".." / "qualification.json", receipt_sha)
            other = directory / "linked"
            other.mkdir()
            alias = directory / "alias"
            try:
                os.symlink(directory, alias, target_is_directory=True)
            except (OSError, NotImplementedError):
                pass
            else:
                try:
                    linked_artifact = Artifact(**{**artifact.__dict__, "path": alias / artifact.path.name})
                    with self.assertRaises(ValueError):
                        inspect_league_test_receipt(linked_artifact, receipt, receipt_sha)
                    with self.assertRaises(ValueError):
                        inspect_league_test_receipt(artifact, alias / "qualification.json", receipt_sha)
                finally:
                    alias.unlink()
            try:
                os.link(evidence, other / "smt-observation.json")
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ValueError):
                    inspect(pin=digest)
                (other / "smt-observation.json").unlink()
            for source in (artifact.path, receipt):
                target = other / source.name
                try:
                    os.link(source, target)
                except (OSError, NotImplementedError):
                    continue
                try:
                    with self.assertRaises(ValueError):
                        inspect(pin=digest)
                finally:
                    target.unlink()

    def test_named_resources_and_submission_scope_do_not_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact, report = self.fixture(Path(tmp).resolve())
            row = {**artifact.__dict__, "workers": 256}
            with self.assertRaisesRegex(ValueError, "worker count"):
                Artifact(**row)
            row = {**artifact.__dict__, "tt_bytes": 128 << 20}
            with self.assertRaisesRegex(ValueError, "TT extent"):
                Artifact(**row)

    def test_explicit_exact_peer_layout_binds_identity_without_granting_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            original, baseline = self.fixture(directory)
            legacy_identity = {
                "id": "A-test-p4", "family": "A", "purpose": "test", "profile": "test-p4",
                "workers": 4, "tt_bytes": 96 << 20, "entry_bytes": 24,
                "representation": "source-jit", "full": True,
                "sha256": original.sha256, "whole_bytes": original.whole_bytes,
                "native_sha256": "b" * 64,
            }
            self.assertEqual(original.identity(), legacy_identity)
            self.assertEqual(json.dumps(original.identity(), separators=(",", ":")),
                             json.dumps(legacy_identity, separators=(",", ":")))
            restored_legacy = Artifact.from_record({**legacy_identity, "path": str(original.path)})
            self.assertEqual(restored_legacy.identity(), legacy_identity)
            with self.assertRaisesRegex(ValueError, "omit layout_id"):
                Artifact.from_record({**legacy_identity, "path": str(original.path), "layout_id": None})

            for family in ("ice4", "c4ke"):
                with self.subTest(family=family):
                    row = {**original.__dict__, "id": family + "-exact-p192", "family": family,
                           "profile": "test-p192", "workers": 192, "entry_bytes": 8,
                           "tt_bytes": 192 << 30, "layout_id": PEER_EXACT_P192_LAYOUT}
                    exact = Artifact(**row)
                    self.assertEqual(exact.identity()["layout_id"], PEER_EXACT_P192_LAYOUT)
                    identity_bytes = json.dumps(exact.identity(), sort_keys=True, separators=(",", ":")).encode()
                    identity_sha256 = hashlib.sha256(identity_bytes).hexdigest()
                    serialized = json.dumps({**exact.identity(), "path": str(exact.path)}, separators=(",", ":"))
                    restored = Artifact.from_record(json.loads(serialized))
                    self.assertEqual(restored.identity(), exact.identity())
                    self.assertEqual(restored.path, exact.path)
                    self.assertEqual(hashlib.sha256(json.dumps(
                        restored.identity(), sort_keys=True, separators=(",", ":")).encode()).hexdigest(), identity_sha256)
                    report = {**baseline, "artifact": exact.identity(),
                              "observations": {**baseline["observations"], "workers": 192,
                                               "positive_cpu_workers": 192, "tt_bytes": 192 << 30,
                                               "physical_cores": 96, "logical_cpus": 192}}
                    receipt, digest = self.write_receipt(directory, report)
                    with self.assertRaisesRegex(ValueError, "SMT TEST runtime and placement"):
                        admit_to_test_league(exact, receipt, digest)

                    mutations = (
                        {"layout_id": "unknown"}, {"layout_id": True}, {"layout_id": 7},
                        {"layout_id": None}, {"family": "A"}, {"profile": "test-p16", "workers": 16},
                        {"workers": 191}, {"purpose": "submission"}, {"entry_bytes": 24},
                        {"tt_bytes": 128 << 30}, {"tt_bytes": float(192 << 30)},
                        {"representation": "packed-native"}, {"representation": "self-contained-elf"},
                        {"representation": "configurable-native"}, {"full": False}, {"full": 1},
                    )
                    for mutation in mutations:
                        with self.subTest(mutation=mutation):
                            with self.assertRaises(ValueError):
                                Artifact(**{**row, **mutation})
                    with self.assertRaises(ValueError):
                        Artifact.from_record({**exact.identity(), "layout_id": "wrong", "path": str(exact.path)})
                    missing_layout = {**exact.identity(), "path": str(exact.path)}
                    del missing_layout["layout_id"]
                    with self.assertRaisesRegex(ValueError, "TT extent"):
                        Artifact.from_record(missing_layout)

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

    def smt_fixture(self):
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
        return report, artifact

    def test_smt_runtime_evidence_does_not_promote_tt_or_score(self):
        report, artifact = self.smt_fixture()
        observed = smt_runtime_evidence(report, artifact)
        self.assertTrue(observed["host_runtime_evidence_complete"])
        self.assertTrue(observed["tt_overlapping_vma_pages_observed"])
        self.assertFalse(observed["tt_only_pages_proven"])
        self.assertFalse(observed["scored_game_placement_confirmed"])
        for mode in ("low", "negative", "missing", "unavailable", "estimate"):
            changed = deepcopy(report)
            budget = changed["sessions"][0]["runtime_budget"]
            if mode == "low":
                budget["availability"] = {"host_available_bytes": 0, "cgroup_remaining_bytes": [0],
                                          "effective_available_bytes": 0}
            elif mode == "negative":
                budget["availability"] = {"host_available_bytes": -1, "cgroup_remaining_bytes": [-2],
                                          "effective_available_bytes": -2}
            elif mode == "missing":
                budget.pop("availability")
                budget.pop("required_available_bytes")
            elif mode == "unavailable":
                budget["availability"] = {"error": "unavailable"}
            else:
                budget["required_available_bytes"] = 10**30
            with self.subTest(availability=mode):
                evidence = smt_runtime_evidence(changed, artifact)
                self.assertTrue(evidence["host_runtime_evidence_complete"])
                self.assertTrue(evidence["tt_overlapping_vma_pages_observed"])
                self.assertFalse(evidence["scored_game_placement_confirmed"])
                self.assertEqual(evidence["availability_observations"][0]["availability"],
                                 budget.get("availability"))
                self.assertEqual(evidence["availability_observations"][0]["estimated_required_available_bytes"],
                                 budget.get("required_available_bytes"))
        for invalid in ({"host_available_bytes": "1"}, {"effective_available_bytes": True},
                        {"cgroup_remaining_bytes": [1, "2"]}, [0]):
            changed = deepcopy(report)
            changed["sessions"][0]["runtime_budget"]["availability"] = invalid
            with self.subTest(invalid_availability=invalid):
                self.assertFalse(smt_runtime_evidence(changed, artifact)["host_runtime_evidence_complete"])
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
        for mutate in ("worker", "node", "parent_limit", "hard_limit", "identity", "policy", "unrelated_vma", "mapping_gap", "finish"):
            changed = deepcopy(report)
            if mutate == "worker":
                changed["sessions"][0]["searches"][0]["worker_affinity_evidence"][0]["cpus"] = [0]
            elif mutate == "node":
                changed["sessions"][0]["post_go_tt_numa"]["tt_overlapping_vmas"][0]["node_pages"] = {1: 2}
            elif mutate == "parent_limit":
                changed["sessions"][0]["preexec_placement"]["child_inherited_limits"]["cpu"] = [10, 10]
            elif mutate == "hard_limit":
                changed["sessions"][0]["preexec_placement"]["runtime_limits"]["address_space"] = [1, 1]
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
