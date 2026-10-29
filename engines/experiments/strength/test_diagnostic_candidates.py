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
        (self.root / "opening.pgn").write_bytes(
            b'[Event "Rove4k one"]\n[ECO "C60"]\n[Result "*"]\n\n'
            b'1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 *\n')
        self.bank_path = self.root / "bank.json"
        self.bank_path.write_text(json.dumps({"files": {stage: pin(self.root / "opening.pgn")
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
        bank = {"files": {stage: pin(self.root / "opening.pgn")}}
        opening = {"id": "one", "eco": "C60", "moves": "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6".split()}
        with patch.object(candidate.run, "runner_identity", return_value={"sha256": "3" * 64}), \
             patch.object(candidate.run, "validate_bank", return_value=(bank, self.bank_sha, [opening], self.root / "opening.pgn")), \
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

    def test_rehashed_opening_with_mismatched_moves_is_not_a_probe_input(self):
        opening = self.root / "opening.pgn"
        opening.write_bytes(opening.read_bytes().replace(b"Nf6 *", b"Nge7 *"))
        self.bank_path.write_text(json.dumps({"files": {stage: pin(opening) for stage in ("broad", "high")}}), encoding="utf-8")
        self.bank_sha = pin(self.bank_path)["sha256"]
        with self.assertRaisesRegex(ValueError, "opening PGN differs"):
            self.build()

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

    def test_original_peer_options_are_frozen_in_diagnostic_manifest(self):
        for profile, hash_mib, threads in (("test-p16", 16384, 16), ("test-p192", 262144, 192)):
            with self.subTest(profile=profile):
                self.profile = profile
                for row in self.rows:
                    row["artifact"].update(profile=profile, workers=threads,
                        tt_bytes=registry.resource_profile(profile).layout(24).bytes)
                peer = self.rows[0]
                peer["artifact"].update(family="ice4", representation="configurable-native", entry_bytes=8,
                    tt_bytes=hash_mib << 20, layout_id=registry.PEER_ORIGINAL_UCI_LAYOUT)
                peer["evidence"] = {"kind": "original-peer-build-v1"}
                self.write_candidates()
                def replay(evidence, artifact, *args):
                    if artifact.family == "ice4":
                        return {"kind": "original-peer-build-v1",
                                "requested_uci": {"hash_mib": hash_mib, "threads": threads}}
                    return {"kind": "file-pins-only"}
                with patch.object(candidate, "_source_evidence", side_effect=replay):
                    data = self.build()
                engine = data["manifest"]["entries"][0]["engines"][0]
                self.assertEqual(engine["uci"], {"kind": "original-peer-uci-v1", "family": "ice4",
                                                  "hash_mib": hash_mib, "threads": threads})
                self.assertNotIn("uci", data["manifest"]["entries"][0]["engines"][1])
                self.assertEqual(data["lock"]["manifest_sha256"], hashlib.sha256(
                    candidate.ledger.canonical(data["manifest"])).hexdigest())
                command = peak_ready_probe.engine_command(engine, profile)
                self.assertEqual((command.hash_mib, command.threads), (hash_mib, threads))
                self.assertFalse(data["runtime_admission"])
                self.assertFalse(data["scored_qualification"])
                engine["uci"]["hash_mib"] -= 1
                with self.assertRaisesRegex(ValueError, "differs"):
                    peak_ready_probe.engine_command(engine, profile)
                engine["uci"]["hash_mib"] += 1
                engine["uci"]["family"] = "A"
                with self.assertRaisesRegex(ValueError, "original-peer"):
                    peak_ready_probe.engine_command(engine, profile)
                if profile == "test-p192":
                    del engine["uci"]
                    with self.assertRaisesRegex(ValueError, "256 GiB"):
                        peak_ready_probe.engine_command(engine, profile)

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

    def test_one_candidate_is_explicitly_allowed_only_for_single_diagnostics(self):
        self.rows = self.rows[:1]
        self.write_candidates()
        for allow in (None, False):
            with self.subTest(allow=allow), self.assertRaisesRegex(ValueError, "candidate set"):
                if allow is None:
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                else:
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile,
                                              allow_single=allow)
        rows, digest = candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile,
                                                 allow_single=True)
        self.assertEqual(digest, self.candidate_sha)
        self.assertEqual([row["artifact"].id for row in rows], ["A"])
        self.assertEqual(rows[0]["whole"], Path(self.rows[0]["artifact"]["path"]))
        self.assertFalse(rows[0]["evidence"]["source_contract_verified"])
        self.assertFalse(rows[0]["evidence"]["native_reference_files_replay_verified"])
        with self.assertRaisesRegex(ValueError, "candidate set"):
            self.build()
        self.assertFalse((self.root / "out").exists())

    def test_single_candidate_allow_flag_is_boolean_and_bounds_stay_enforced(self):
        for flag in (None, 0, 1, "true", [], {}):
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, "explicit boolean"):
                candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile,
                                          allow_single=flag)
        self.rows = []
        self.write_candidates()
        with self.assertRaisesRegex(ValueError, "candidate set"):
            candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile, allow_single=True)
        row = {"invalid": "length is checked before rows"}
        self.rows = [row] * 33
        self.write_candidates()
        with self.assertRaisesRegex(ValueError, "candidate set"):
            candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile, allow_single=True)

    def test_single_candidate_still_rejects_each_tamper_and_forbidden_engine(self):
        self.rows = self.rows[:1]
        self.write_candidates()
        row = self.rows[0]
        for kind, filename in (("source", row["source"]["path"]), ("native", row["native"]["path"]),
                               ("whole", row["artifact"]["path"])):
            with self.subTest(kind=kind):
                path = Path(filename)
                raw = path.read_bytes()
                path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                try:
                    with self.assertRaisesRegex(ValueError, "pinned identity"):
                        candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile,
                                                  allow_single=True)
                finally:
                    path.write_bytes(raw)
        for changes in ({"family": "D"}, {"representation": "self-contained-elf"},
                        {"full": False}, {"profile": "test-p192"}, {"tt_bytes": 1}):
            with self.subTest(changes=changes):
                original = dict(row["artifact"])
                row["artifact"].update(changes)
                self.write_candidates()
                with self.assertRaises(ValueError):
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile,
                                              allow_single=True)
                row["artifact"] = original
        self.write_candidates()
        with self.assertRaisesRegex(ValueError, "identity differs"):
            candidate.read_candidates(self.candidate_path, "0" * 64, self.profile, allow_single=True)

    def test_one_p192_candidate_keeps_profile_specific_resource_checks(self):
        self.profile = "test-p192"
        self.rows = self.rows[:1]
        self.rows[0]["artifact"].update(profile=self.profile, workers=192,
            tt_bytes=registry.resource_profile(self.profile).layout(24).bytes)
        self.write_candidates()
        rows, _ = candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile,
                                            allow_single=True)
        self.assertEqual(rows[0]["artifact"].workers, 192)
        self.assertEqual(rows[0]["artifact"].tt_bytes, 192 << 30)
        self.rows[0]["artifact"]["workers"] = 16
        self.write_candidates()
        with self.assertRaises(ValueError):
            candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile, allow_single=True)

    def test_p192_rejects_legacy_128g_peer_before_inspecting_candidate_files(self):
        self.profile = "test-p192"
        self.rows = self.rows[:1]
        artifact = self.rows[0]["artifact"]
        artifact.update(family="ice4", profile=self.profile, workers=192, entry_bytes=8,
                        tt_bytes=registry.resource_profile(self.profile).layout(8).bytes)
        self.assertEqual(artifact["tt_bytes"], 128 << 30)
        self.write_candidates()
        with patch.object(candidate, "_pinned_file", side_effect=AssertionError("unexpected candidate read")):
            with self.assertRaisesRegex(ValueError, "P192 diagnostics require 192 GiB"):
                candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile, allow_single=True)

    def test_exact_p192_peer_cannot_bypass_unverified_source_with_file_pins(self):
        self.profile = "test-p192"
        self.rows = self.rows[:1]
        artifact = self.rows[0]["artifact"]
        artifact.update(profile=self.profile, workers=192, entry_bytes=8,
                        tt_bytes=192 << 30, layout_id="peer-p192-exact-3x2p33-v1")
        for family in ("ice4", "c4ke"):
            artifact["family"] = family
            for evidence in ({"kind": "file-pins-only"}, {"kind": "peer-reference-v1"},
                             {"kind": "peer-exact-reference-v1"}):
                with self.subTest(family=family, evidence=evidence):
                    self.rows[0]["evidence"] = evidence
                    self.write_candidates()
                    with patch.object(candidate, "_pinned_file", side_effect=AssertionError("unexpected candidate read")):
                        with self.assertRaisesRegex(ValueError, "P192 peer diagnostic awaits source and native"):
                            candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile, allow_single=True)

    def test_p192_peer_cannot_forge_a_24_byte_legacy_layout(self):
        self.profile = "test-p192"
        self.rows = self.rows[:1]
        self.rows[0]["artifact"].update(profile=self.profile, workers=192,
                                        entry_bytes=24, tt_bytes=192 << 30)
        self.rows[0]["evidence"] = {"kind": "file-pins-only"}
        for family in ("ice4", "c4ke"):
            with self.subTest(family=family):
                self.rows[0]["artifact"]["family"] = family
                self.write_candidates()
                with patch.object(candidate, "_pinned_file", side_effect=AssertionError("unexpected candidate read")):
                    with self.assertRaisesRegex(ValueError, "P192 peer diagnostic awaits source and native"):
                        candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile, allow_single=True)

    def test_p16_legacy_peer_16g_still_obeys_the_approved_cap(self):
        self.rows = self.rows[:1]
        artifact = self.rows[0]["artifact"]
        artifact.update(family="ice4", entry_bytes=8,
                        tt_bytes=registry.resource_profile(self.profile).layout(8).bytes)
        self.assertEqual(artifact["tt_bytes"], 16 << 30)
        self.write_candidates()
        rows, _ = candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile,
                                            allow_single=True)
        self.assertEqual(rows[0]["artifact"].tt_bytes, 16 << 30)

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

    def test_b_evidence_requires_pinned_mode_and_rejects_replaced_static_files(self):
        try:
            from . import rove_b_static_tt
        except ImportError:
            import rove_b_static_tt
        directory = self.root / "b-output"
        (directory / "native").mkdir(parents=True)
        row = self.rows[1]
        for source, target in ((row["artifact"]["path"], directory / "x"),
                               (row["source"]["path"], directory / "main.c"),
                               (row["native"]["path"], directory / "native" / "x")):
            shutil.copyfile(source, target)
        row["artifact"]["path"] = str(directory / "x")
        row["source"], row["native"] = pin(directory / "main.c"), pin(directory / "native" / "x")
        build_report = directory / "build.json"
        build_report.write_text("{}", encoding="utf-8")
        artifact = row["artifact"]
        admitted = SimpleNamespace(family="B", profile_id=self.profile, representation="source-jit", full=True,
            program="x", source="main.c", native="native/x",
            resources={"workers": 16, "tt_bytes": artifact["tt_bytes"], "tt_entry_bytes": 24},
            expected={"source_sha256": row["source"]["sha256"], "native_sha256": row["native"]["sha256"],
                      "whole_sha256": artifact["sha256"]})
        verifier = SimpleNamespace(admit_c_build=Mock(return_value=admitted))
        basic = {"kind": "rove-profile-build-v1", "build": pin(build_report)}
        row["evidence"] = dict(basic)
        self.write_candidates()
        with patch.object(candidate, "_profile_verifier", return_value=verifier):
            with self.assertRaisesRegex(ValueError, "explicit B static evidence mode"):
                candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
            row["evidence"] = dict(basic, b_static_mode="legacy-no-static", b_static_files={}, b_producer_report=None)
            self.write_candidates()
            rows, _ = candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
            self.assertEqual(rows[1]["evidence"]["b_static_mode"], "legacy-no-static")
            for name, value in (("b_static_files", {"b-static-tt.json": {}}),
                                ("b_producer_report", {"path": "fake"})):
                row["evidence"][name] = value
                self.write_candidates()
                with self.subTest(field=name), self.assertRaisesRegex(ValueError, "legacy B candidate"):
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                row["evidence"][name] = {} if name == "b_static_files" else None
            row["evidence"]["b_static_mode"] = "sealed-static-correlated"
            self.write_candidates()
            with self.assertRaisesRegex(ValueError, "incomplete B static"):
                candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
            row["evidence"]["b_static_mode"] = "legacy-no-static"
            self.write_candidates()
            for name, data in (("b-static-tt.json", b"{}"), ("compiler-sha256.txt", b"a" * 64),
                               ("linker-sha256.txt", b"b" * 64)):
                (directory / name).write_bytes(data)
            with self.assertRaisesRegex(ValueError, "legacy B candidate"):
                candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
            static = {"symbol": "qq", "elf_symbol_offset": 128, "tt_bytes": 12 << 30,
                      "source_sha256": row["source"]["sha256"], "native_sha256": row["native"]["sha256"],
                      "compiler_replay_independently_verified": False, "producer_authenticated": False,
                      "tt_semantics_proven": False}
            static["report_sha256"] = hashlib.sha256(b"{}").hexdigest()
            producer = {"format": "rove4k.github-source-observation-v1", "family": "B", "profile": self.profile,
                        "variant": "league-atomic", "candidate_pins_match": True, "candidate_files_observed": False,
                        "runtime_qualified": False, "authorizes_go": False,
                        "b_static_correlation": dict(static, producer_artifact_observed=True)}
            producer_path = directory / "observation.json"
            producer_path.write_text(json.dumps(producer), encoding="utf-8")
            file_pins = {name: candidate._b_pin((directory / name).read_bytes()) for name in candidate._B_STATIC_NAMES}
            row["evidence"] = dict(basic, b_static_mode="sealed-static-correlated", b_static_files=file_pins,
                                   b_producer_report=pin(producer_path))
            self.write_candidates()
            with patch.object(rove_b_static_tt, "validate_report_bytes", return_value=dict(static)):
                rows, _ = candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                self.assertEqual(rows[1]["evidence"]["b_static_mode"], "sealed-static-correlated")
                self.assertFalse(rows[1]["evidence"]["b_static_correlation"]["producer_authenticated"])
                producer_bytes = producer_path.read_bytes()
                producer_path.write_bytes(producer_bytes + b" ")
                with self.assertRaises(ValueError):
                    candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                producer_path.write_bytes(producer_bytes)
                for name in candidate._B_STATIC_NAMES:
                    path = directory / name
                    original = path.read_bytes()
                    path.write_bytes(original + b"changed")
                    with self.subTest(name=name), self.assertRaisesRegex(ValueError, "static candidate file pins differ"):
                        candidate.read_candidates(self.candidate_path, self.candidate_sha, self.profile)
                    path.write_bytes(original)
                # Replacing every adjacent file while keeping the candidate pin is also rejected.
                originals = {name: (directory / name).read_bytes() for name in candidate._B_STATIC_NAMES}
                for name in candidate._B_STATIC_NAMES:
                    (directory / name).write_bytes(originals[name] + b"changed")
                with self.assertRaisesRegex(ValueError, "static candidate file pins differ"):
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
