"""Original peer candidate pin bridge; synthetic bytes, no engine is run."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import diagnostic_candidates as candidate, original_peer_build as original, registry
except ImportError:
    import diagnostic_candidates as candidate
    import original_peer_build as original
    import registry


def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class OriginalBridgeTests(unittest.TestCase):
    def fixture(self, root, peer, profile):
        base = root / (peer + "-" + profile)
        (base / "src").mkdir(parents=True)
        files = {name: ("synthetic " + name).encode() for name in original.source_names(peer)}
        for name, data in files.items():
            (base / name).write_bytes(data)
        # Only tests mock the upstream Git pin authority; production checks actual pins.
        with patch.object(original.peers, "verify_blob"):
            snapshot = original.source_record(peer, profile, files)
        for index in (1, 2):
            (base / ("peer-native-" + str(index))).write_bytes(b"synthetic peer binary")
        native = pin(base / "peer-native-1")
        report = {"format": "rove4k-original-peer-build-v1", "purpose": "test-only", "peer": peer,
                  "profile": profile, "revision": snapshot["revision"], "source": snapshot["source"],
                  "source_closure_sha256": snapshot["source_closure_sha256"],
                  "source_modified_by_builder": False, "requested_uci": snapshot["requested_uci"],
                  "uci_setup_performed": False, "complete": True, "same_host_native_reproduced": True,
                  "compiler": {"flags": list(original._FLAGS[peer])},
                  "engines_executed": 0,
                  "attempts": [{"name": "peer-native-" + str(i), "bytes": native["bytes"],
                                "sha256": native["sha256"]} for i in (1, 2)]}
        build = base / "original-peer-build.json"
        build.write_text(json.dumps(report), encoding="utf-8")
        config = snapshot["requested_uci"]
        artifact = {"id": peer + "-" + profile, "family": peer, "path": native["path"], "purpose": "test",
                    "profile": profile, "workers": config["workers"],
                    "tt_bytes": config["expected_tt_bytes_if_entry8"], "entry_bytes": 8,
                    "representation": "configurable-native", "full": True, "sha256": native["sha256"],
                    "native_sha256": native["sha256"], "whole_bytes": native["bytes"],
                    "layout_id": registry.PEER_ORIGINAL_UCI_LAYOUT}
        row = {"artifact": artifact, "source": pin(base / "src/main.cpp"), "native": native,
               "evidence": {"kind": "original-peer-build-v1", "build": pin(build)}}
        path = root / "candidates.json"
        def save():
            path.write_text(json.dumps({"format": "rove4k-diagnostic-candidate-set-v1", "profile": profile,
                                       "candidates": [row]}), encoding="utf-8")
            return pin(path)["sha256"]
        return base, row, path, save

    def test_original_profiles_replay_pins_without_league_admission(self):
        for peer in ("ice4", "c4ke"):
            for profile, hash_mib in (("test-p16", 16384), ("test-p192", 262144)):
                with self.subTest(peer=peer, profile=profile), tempfile.TemporaryDirectory() as tmp:
                    base, row, path, save = self.fixture(Path(tmp).resolve(), peer, profile)
                    with patch.object(original.peers, "verify_blob"):
                        rows, _ = candidate.read_candidates(path, save(), profile, allow_single=True)
                    evidence = rows[0]["evidence"]
                    self.assertEqual(evidence["requested_uci"]["hash_mib"], hash_mib)
                    self.assertTrue(evidence["native_reference_files_replay_verified"])
                    self.assertFalse(evidence["source_to_native_proven"])
                    self.assertFalse(evidence["allocation_observed"])
                    self.assertFalse(evidence["scored_game_admitted"])
                    with self.assertRaisesRegex(ValueError, "separate original-source qualification"):
                        registry.admit_to_test_league(rows[0]["artifact"], base / "nothing", "0" * 64)
                    (base / "peer-native-2").write_bytes(b"changed")
                    with patch.object(original.peers, "verify_blob"), self.assertRaisesRegex(ValueError, "native attempts"):
                        candidate.read_candidates(path, save(), profile, allow_single=True)

    def test_original_rejects_generic_evidence_and_wrong_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, row, path, save = self.fixture(Path(tmp).resolve(), "ice4", "test-p192")
            row["evidence"] = {"kind": "file-pins-only"}
            with self.assertRaisesRegex(ValueError, "original build evidence"):
                candidate.read_candidates(path, save(), "test-p192", allow_single=True)
            row["artifact"]["tt_bytes"] = 192 << 30
            with self.assertRaisesRegex(ValueError, "original peer UCI request"):
                candidate.read_candidates(path, save(), "test-p192", allow_single=True)

    def test_receipt_and_source_tampering_are_rejected(self):
        for target in ("uci", "flags", "source"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                base, row, path, save = self.fixture(Path(tmp).resolve(), "c4ke", "test-p192")
                build = base / "original-peer-build.json"
                report = json.loads(build.read_text(encoding="utf-8"))
                if target == "uci":
                    report["requested_uci"]["hash_mib"] = 196608
                elif target == "flags":
                    report["compiler"]["flags"] = []
                else:
                    (base / "src/main.cpp").write_bytes(b"changed source")
                    row["source"] = pin(base / "src/main.cpp")
                build.write_text(json.dumps(report), encoding="utf-8")
                row["evidence"]["build"] = pin(build)
                with patch.object(original.peers, "verify_blob"), self.assertRaisesRegex(ValueError, "build identity"):
                    candidate.read_candidates(path, save(), "test-p192", allow_single=True)

    def test_controller_refuses_originals_without_option_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _, row, path, save = self.fixture(root, "ice4", "test-p16")
            with patch.object(candidate, "read_candidates", return_value=([{"artifact": registry.Artifact.from_record(row["artifact"])}], "1" * 64)):
                with self.assertRaisesRegex(ValueError, "does not yet bind original peer UCI options"):
                    candidate.build_inputs(candidate_path=path, candidate_sha256=save(), profile="test-p16",
                        bank_path=root / "bank", bank_sha256="2" * 64, runner_binary=root / "runner",
                        runner_receipt=root / "receipt", output_root=root / "out")


if __name__ == "__main__":
    unittest.main()
