"""Synthetic source-pinned candidates; no engine, cgroup or scored game runs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

try:
    from . import diagnostic_candidates as candidate, peak_ready_probe, peer_runtime, registry, topology
except ImportError:
    import diagnostic_candidates as candidate
    import peak_ready_probe
    import peer_runtime
    import registry
    import topology


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


class DiagnosticCandidatesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.profile = "test-p16"
        self.rows = []
        for name, family in (("A", "A"), ("B", "B")):
            paths = {}
            for kind in ("whole", "source", "native"):
                path = self.root / (name + "-" + kind)
                path.write_bytes((name + " " + kind).encode("ascii"))
                paths[kind] = pin(path)
            self.rows.append({"artifact": {"id": name, "family": family, "path": paths["whole"]["path"],
                     "purpose": "test", "profile": self.profile, "workers": 16,
                     "tt_bytes": registry.resource_profile(self.profile).layout(24).bytes,
                     "entry_bytes": 24, "representation": "source-jit", "full": True,
                     "sha256": paths["whole"]["sha256"], "whole_bytes": paths["whole"]["bytes"],
                     "native_sha256": paths["native"]["sha256"]},
                     "source": paths["source"], "native": paths["native"],
                     "evidence": {"kind": "file-pins-only"}})
        self.candidate_path = self.root / "candidates.json"
        (self.root / "fastchess").write_bytes(b"runner")
        (self.root / "runner.json").write_text("{}", encoding="utf-8")
        (self.root / "opening.pgn").write_text("fixture", encoding="utf-8")
        self.bank_path = self.root / "bank.json"
        self.bank_path.write_text(json.dumps({"files": {stage: {"path": str(self.root / "opening.pgn")}
                                                          for stage in ("broad", "high")}}), encoding="utf-8")
        self.bank_sha = pin(self.bank_path)["sha256"]
        self.write_candidates()

    def write_candidates(self):
        raw = json.dumps({"format": "rove4k-diagnostic-candidate-set-v1", "profile": self.profile,
                          "candidates": self.rows}, sort_keys=True).encode("utf-8")
        self.candidate_path.write_bytes(raw)
        self.candidate_sha = hashlib.sha256(raw).hexdigest()

    def args(self):
        return {"candidate_path": self.candidate_path, "candidate_sha256": self.candidate_sha,
                "profile": self.profile, "bank_path": self.bank_path, "bank_sha256": self.bank_sha,
                "runner_binary": self.root / "fastchess", "runner_receipt": self.root / "runner.json",
                "output_root": self.root / "out", "snapshot": self.snapshot()}

    def snapshot(self):
        return SimpleNamespace(allowed_cpus=tuple(range(192)), to_record=lambda: {"fixture": True})

    def slots(self):
        count = 11 if self.profile == "test-p16" else 1
        workers = 16 if self.profile == "test-p16" else 192
        return [topology.Slot(f"slot-{i:03d}", tuple(range(i * workers, (i + 1) * workers)),
                              tuple((0, i * (workers // 2) + k) for k in range(workers // 2)),
                              (0,), workers, True, "default") for i in range(count)]

    def build(self, *, write=False, overrides=None):
        stage = "broad" if self.profile == "test-p16" else "high"
        bank = {"files": {stage: {"sha256": "2" * 64}}}
        with patch.object(candidate.run, "runner_identity", return_value={"sha256": "3" * 64}), \
             patch.object(candidate.run, "validate_bank", return_value=(bank, self.bank_sha, [{"id": "one"}], self.root / "opening.pgn")), \
             patch.object(candidate.run, "league_placement", return_value=(self.slots(), list(range(176, 192)))), \
             patch.object(candidate.run, "load_plan", side_effect=AssertionError("scored plan used")), \
             patch.object(registry, "admit_to_test_league", side_effect=AssertionError("scored admission used")):
            return (candidate.write_inputs if write else candidate.build_inputs)(**{**self.args(), **(overrides or {})})

    def test_p16_pinned_manifest_round_trip_remains_diagnostic_only(self):
        result = self.build(write=True)
        self.assertFalse(result["runtime_admission"])
        self.assertFalse(result["scored_qualification"])
        manifest = peak_ready_probe.load_controller_manifest(result["manifest_path"], result["manifest_sha256"])
        self.assertEqual(len(manifest["entries"]), 11)
        self.assertEqual(manifest["entries"][0]["engines"][0]["whole_sha256"], self.rows[0]["artifact"]["sha256"])
        self.assertEqual(manifest["entries"][0]["engines"][0]["native_sha256"], self.rows[0]["artifact"]["native_sha256"])
        self.assertEqual(manifest["entries"][0]["engines"][0]["tt_bytes"], self.rows[0]["artifact"]["tt_bytes"])
        lock = json.loads(Path(result["lock_path"]).read_bytes())
        for kind in ("manifest", "artifacts"):
            actual = hashlib.sha256(Path(result[kind + "_path"]).read_bytes()).hexdigest()
            self.assertEqual(lock[kind + "_sha256"], actual)
            self.assertEqual(result[kind + "_sha256"], actual)
        self.assertEqual(lock["candidate_set_sha256"], self.candidate_sha)
        self.assertEqual(lock["candidates"][0]["source"]["sha256"], self.rows[0]["source"]["sha256"])
        self.assertFalse(lock["source_to_native_provenance_verified"])
        self.assertFalse(lock["runtime_native_observed"])
        self.assertFalse(lock["scored_qualification"])
        self.assertFalse((self.root / "out" / "jobs").exists())

    def test_missing_or_invalid_bank_digest_is_rejected_before_input_reads(self):
        for bad in (None, "", "0" * 63, "g" * 64):
            with self.subTest(bad=bad), \
                 patch.object(candidate, "read_candidates", side_effect=AssertionError("unexpected candidate read")):
                with self.assertRaisesRegex(ValueError, "opening bank digest"):
                    candidate.build_inputs(**{**self.args(), "bank_sha256": bad})

    def test_protected_and_generated_paths_are_rejected_without_access(self):
        blocked = [".ENV.PROD", ".env.test", "package-lock.json", "NODE_MODULES/file", "dist/file",
                   "dist-server/file", "build/file", "coverage/file", "models/file", "checkpoints/file",
                   ".cache/file", ".aws/credentials", ".ssh/id_ed25519", "inventory.json", "TOKEN", "api_token"]
        for name in blocked:
            with self.subTest(name=name), \
                 patch.object(Path, "stat", side_effect=AssertionError("blocked path touched")), \
                 patch.object(Path, "read_bytes", side_effect=AssertionError("blocked path read")):
                with self.assertRaises(ValueError):
                    candidate._safe_input_path(self.root / name)

    def test_protected_output_paths_are_rejected_before_any_filesystem_inspection(self):
        for name in (".ENV.PROD/out", "NODE_MODULES/out", "build/out", "package-lock.json", ".aws/credentials"):
            with self.subTest(name=name), \
                 patch.object(Path, "stat", side_effect=AssertionError("blocked output stat")), \
                 patch.object(Path, "exists", side_effect=AssertionError("blocked output exists check")), \
                 patch.object(candidate.run, "external_new", side_effect=AssertionError("blocked output inspected")):
                with self.assertRaises(ValueError):
                    candidate._safe_output_path(self.root / name)

    def test_tokenize_source_filename_is_not_a_secret_token_path(self):
        source = self.root / "tokenize.rs"
        source.write_bytes(b"synthetic source")
        self.assertEqual(candidate._safe_input_path(source), source)

    def test_p192_uses_single_slot_and_profile_specific_resources(self):
        self.profile = "test-p192"
        for row in self.rows:
            row["artifact"].update(profile=self.profile, workers=192,
                                   tt_bytes=registry.resource_profile(self.profile).layout(24).bytes)
        self.write_candidates()
        data = self.build()
        self.assertEqual(len(data["manifest"]["entries"]), 1)
        self.assertEqual(data["manifest"]["entries"][0]["slot"]["workers"], 192)
        self.assertFalse(data["scored_qualification"])

    def test_target_cgroup_topology_is_independent_of_observer_affinity(self):
        path = self.root / "target-cgroup"
        path.mkdir()
        info = path.stat()
        target = {"path": str(path), "device": info.st_dev, "inode": info.st_ino}
        target_snapshot = SimpleNamespace(allowed_cpus=tuple(range(192)),
                                          to_record=lambda: {"target_topology": True})
        with patch.object(candidate.topology.Topology, "snapshot_target", return_value=target_snapshot) as observe, \
             patch.object(candidate.topology.Topology, "snapshot", side_effect=AssertionError("observer topology used")):
            data = self.build(overrides={"snapshot": None, "target_cgroup": target})
        observe.assert_called_once_with(path, device=info.st_dev, inode=info.st_ino)
        self.assertEqual(data["manifest"]["topology"], {"target_topology": True})
        self.assertEqual(data["lock"]["target_topology_cgroup"], target)
        self.assertFalse(data["runtime_admission"])
        self.assertFalse(data["scored_qualification"])

    def test_invalid_target_cgroup_or_multiple_topology_sources_are_rejected(self):
        path = self.root / "target-cgroup"
        path.mkdir()
        info = path.stat()
        valid = {"path": str(path), "device": info.st_dev, "inode": info.st_ino}
        invalid = ({"path": str(path)}, {"path": str(path), "device": info.st_dev},
                   {**valid, "inode": 0}, {**valid, "device": -1}, {**valid, "inode": True},
                   {**valid, "extra": "field"})
        with patch.object(candidate.topology.Topology, "snapshot_target") as observe:
            with self.assertRaisesRegex(ValueError, "one explicit topology source"):
                self.build(overrides={"target_cgroup": valid})
            for target in invalid:
                with self.subTest(target=target), self.assertRaises(ValueError):
                    self.build(overrides={"snapshot": None, "target_cgroup": target})
            observe.assert_not_called()
        with patch.object(candidate.topology.Topology, "snapshot_target", side_effect=ValueError("target identity changed")):
            with self.assertRaisesRegex(ValueError, "target identity changed"):
                self.build(overrides={"snapshot": None, "target_cgroup": valid})

    def test_source_native_and_whole_tampering_each_rejected(self):
        row = self.rows[0]
        for kind, path in (("source", row["source"]["path"]), ("native", row["native"]["path"]),
                           ("whole", row["artifact"]["path"])):
            with self.subTest(kind=kind):
                path = Path(path)
                original = path.read_bytes()
                path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                with self.assertRaisesRegex(ValueError, "pinned identity"):
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                path.write_bytes(original)

    def test_registry_digest_and_profile_or_resource_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity differs"):
            candidate.read_candidates(self.candidate_path, "0" * 64, self.profile)
        with self.assertRaises(ValueError):
            candidate.read_candidates(self.candidate_path, self.candidate_sha, "test-p192")
        self.rows[0]["artifact"]["tt_bytes"] += 1
        self.write_candidates()
        with self.assertRaises(ValueError):
            candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)

    def test_D_elf_duplicate_and_unpinned_candidates_rejected(self):
        for changes in ({"family": "D"}, {"representation": "self-contained-elf"}, {"id": "B"},
                        {"full": False}):
            with self.subTest(changes=changes):
                before = dict(self.rows[0]["artifact"])
                self.rows[0]["artifact"].update(changes)
                self.write_candidates()
                with self.assertRaises(ValueError):
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                self.rows[0]["artifact"] = before
        self.rows[0]["source"]["sha256"] = "0" * 64
        self.write_candidates()
        with self.assertRaises(ValueError):
            candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)

    def test_rove_generation_evidence_replays_verifier_and_checks_each_pin(self):
        build = self.root / "build-output"
        (build / "native").mkdir(parents=True)
        row = self.rows[0]
        for source, target in ((row["artifact"]["path"], build / "x"),
                               (row["source"]["path"], build / "main.c"),
                               (row["native"]["path"], build / "native" / "x")):
            shutil.copyfile(source, target)
        row["artifact"]["path"] = str(build / "x")
        row["source"], row["native"] = pin(build / "main.c"), pin(build / "native" / "x")
        report = build / "build.json"
        report.write_text("{}", encoding="utf-8")
        row["evidence"] = {"kind": "rove-profile-build-v1", "build": pin(report)}
        self.write_candidates()
        artifact = row["artifact"]
        admitted = SimpleNamespace(family="A", profile_id=self.profile, representation="source-jit", full=True,
                    program="x", source="main.c", native="native/x",
                    resources={"workers": 16, "tt_bytes": artifact["tt_bytes"], "tt_entry_bytes": 24},
                    expected={"source_sha256": row["source"]["sha256"], "native_sha256": row["native"]["sha256"],
                              "whole_sha256": artifact["sha256"]})
        verifier = SimpleNamespace(admit_c_build=Mock(return_value=admitted))
        with patch.object(candidate, "_profile_verifier", return_value=verifier):
            rows, _ = candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
            verifier.admit_c_build.assert_called_once_with({}, build)
            self.assertTrue(rows[0]["evidence"]["source_contract_verified"])
            self.assertTrue(rows[0]["evidence"]["native_reference_files_replay_verified"])
            self.assertFalse(rows[1]["evidence"]["source_contract_verified"])
            for attribute, bad in (("profile_id", "test-p192"), ("family", "B"),
                                   ("representation", "packed-native"), ("source", "other.c")):
                with self.subTest(attribute=attribute):
                    original = getattr(admitted, attribute)
                    setattr(admitted, attribute, bad)
                    with self.assertRaisesRegex(ValueError, "source admission differs"):
                        candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                    setattr(admitted, attribute, original)
            for field in ("source_sha256", "native_sha256", "whole_sha256"):
                original = admitted.expected[field]
                admitted.expected[field] = "f" * 64
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "source admission differs"):
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                admitted.expected[field] = original
            admitted.resources["tt_bytes"] += 1
            with self.assertRaisesRegex(ValueError, "source admission differs"):
                candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)

    def test_peer_generation_and_three_native_references_are_independently_bound(self):
        row = self.rows[0]
        artifact = row["artifact"]
        artifact.update(family="ice4", entry_bytes=8,
                        tt_bytes=registry.resource_profile(self.profile).layout(8).bytes)
        peer_build = self.root / "peer-build.json"
        peer_build.write_text("{}", encoding="utf-8")
        reference_dir = self.root / "reference"
        reference_dir.mkdir()
        reference_source = reference_dir / "main.cpp"
        reference_source.write_bytes(Path(row["source"]["path"]).read_bytes())
        peers = peer_runtime.sibling("peers")
        fixed = [self.root / "peer-producer.py"]
        fixed.extend(reference_dir / "source-closure" / relative for relative in
                     peer_runtime.SOURCE_FILES + peer_runtime.LEAGUE_SOURCE_FILES)
        for index in (1, 2):
            attempt = self.root / ("attempt-" + str(index))
            fixed.extend(attempt / item for item in ("main.cpp", "resource-proof.json", peers.peer_spec("ice4").tiny_name))
            fixed.extend(attempt / "source" / relative for relative in peers.SOURCE_BLOBS["ice4"])
        for path in fixed:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic fixture")
        reference_native = Path(row["native"]["path"]).read_bytes()
        for index in (1, 2, 3):
            (reference_dir / ("reference-" + str(index))).write_bytes(reference_native)
        row["native"] = pin(reference_dir / "reference-1")
        resources = {"id": self.profile, "workers": 16, "tt_bytes": artifact["tt_bytes"]}
        reference = {"format": "rove4k-peer-reference-v1", "complete": True, "engines_executed": 0,
                     "entry_size_compile_assertion": True,
                     "build": {"path": str(peer_build), "sha256": pin(peer_build)["sha256"]},
                     "resources": resources, "source": pin(reference_source),
                     "native": row["native"], "native_attempts": [pin(reference_dir / ("reference-" + str(i))) for i in (1, 2, 3)],
                     "source_inputs": {}, "tt_symbol": "tt", "tt_symbol_value": 42, "dependencies": ["libc.so.6"]}
        reference_path = reference_dir / "reference.json"
        reference_path.write_text(json.dumps(reference), encoding="utf-8")
        row["evidence"] = {"kind": "peer-reference-v1", "build": pin(peer_build), "reference": pin(reference_path)}
        self.write_candidates()
        admitted = {"peer": "ice4", "layout": resources, "tt_symbol": "tt",
                    "whole": Path(artifact["path"]).read_bytes(), "source": Path(row["source"]["path"]).read_bytes()}
        elf = SimpleNamespace(dependencies=lambda: ["libc.so.6"], pointer_symbol=lambda name: 42)
        with patch.object(peer_runtime, "_verify_frozen") as closure, \
             patch.object(peer_runtime, "validate_build", return_value=admitted) as validate, \
             patch.object(peer_runtime, "Elf64", return_value=elf):
            rows, _ = candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
            closure.assert_called_once()
            validate.assert_called_once_with(peer_build, pin(peer_build)["sha256"])
            self.assertTrue(rows[0]["evidence"]["source_contract_verified"])
            self.assertTrue(rows[0]["evidence"]["native_reference_files_replay_verified"])
            (reference_dir / "reference-2").write_bytes(b"different")
            with self.assertRaises(ValueError):
                candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)


if __name__ == "__main__":
    unittest.main()
