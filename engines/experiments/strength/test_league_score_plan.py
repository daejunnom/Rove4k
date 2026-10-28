"""Draft-plan input tests using file pins; no engines or scored games run."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import league_score_plan as plan, original_peer_build as original, registry, fastchess
    from . import test_original_candidate_bridge as bridge
except ImportError:
    import league_score_plan as plan
    import original_peer_build as original
    import registry
    import fastchess
    import test_original_candidate_bridge as bridge

pin = bridge.pin


class DraftPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def fixture(self, profile="test-p16", peer="ice4"):
        root = self.root
        workers = 16 if profile == "test-p16" else 192
        _, peer_row, path, _ = bridge.OriginalBridgeTests().fixture(root, peer, profile)
        whole = root / "rove-whole"
        whole.write_bytes(b"large Rove full source " * 300)
        source, native = root / "rove-source", root / "rove-native"
        source.write_bytes(b"synthetic source")
        native.write_bytes(b"synthetic native")
        wp, sp, np = pin(whole), pin(source), pin(native)
        rove = {"artifact": {"id": "Rove-A", "family": "A", "path": wp["path"],
            "purpose": "test", "profile": profile, "workers": workers,
            "tt_bytes": registry.resource_profile(profile).layout(24).bytes,
            "entry_bytes": 24, "representation": "source-jit", "full": True,
            "sha256": wp["sha256"], "whole_bytes": wp["bytes"], "native_sha256": np["sha256"]},
            "source": sp, "native": np, "evidence": {"kind": "file-pins-only"}}
        def write_candidates():
            path.write_text(json.dumps({"format": "rove4k-diagnostic-candidate-set-v1",
                "profile": profile, "candidates": [rove, peer_row]}), encoding="utf-8")
            return pin(path)["sha256"]
        candidates_sha = write_candidates()
        runner, receipt = root / "runner", root / "runner.json"
        runner.write_bytes(b"synthetic runner")
        receipt.write_text(json.dumps({"complete": True, "upstream_commit": fastchess.PIN,
            "patch_sha256": fastchess.sha(fastchess.PATCH.read_bytes()),
            "binary_sha256": pin(runner)["sha256"], "command": {"returncode": 0,
            "forced_cleanup": False, "leader_reaped": True, "group_absent": True}}), encoding="utf-8")
        opening = root / "opening.pgn"
        opening.write_bytes(b'[Event "Rove4k opening-1"]\n[ECO "C60"]\n[Result "*"]\n\n'
                            b'1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 *\n')
        moves = "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6".split()
        opening_info = pin(opening)
        bank = root / "bank.json"
        stage = "broad" if profile == "test-p16" else "high"
        bank.write_text(json.dumps({"bank_id": "fixture-bank", "source": {
            "revision": "a6189a30dc273ccb21fc2536a9a2fefd5592a67a", "verified": True, "license": "CC0-1.0"},
            "stages": {stage: [{"id": "opening-1", "eco": "C60", "moves": moves, "family": " ".join(moves)}]},
            "files": {stage: opening_info}}), encoding="utf-8")
        args = {"campaign": "draft-test", "profile": profile, "candidate_path": path,
            "candidate_sha256": candidates_sha, "bank_path": bank, "bank_sha256": pin(bank)["sha256"],
            "runner_binary": runner, "runner_receipt": receipt}
        return args, rove, peer_row, write_candidates, opening

    def prepare(self, args):
        # Synthetic fixture does not claim the mocked upstream blob authority.
        with patch.object(original.peers, "verify_blob"):
            return plan.prepare(**args)

    def verify(self, value):
        with patch.object(original.peers, "verify_blob"):
            return plan.verify(value, value["sha256"])

    def test_full_oversize_rove_and_original_resources_are_drafts_only(self):
        args, rove, peer, _, _ = self.fixture()
        draft = self.prepare(args)
        self.assertEqual(draft["format"], "rove4k-score-plan-draft-v1")
        self.assertGreater(rove["artifact"]["whole_bytes"], 4096)
        self.assertIsNotNone(self.verify(draft))
        players = {row["identity"]["family"]: row for row in draft["content"]["players"]}
        self.assertEqual(set(players), {"A", "ice4"})
        self.assertEqual(players["A"]["identity"]["whole_bytes"], rove["artifact"]["whole_bytes"])
        self.assertEqual(players["ice4"]["identity"]["tt_bytes"], 16 << 30)
        self.assertEqual(players["ice4"]["uci"]["hash_mib"], 16384)
        self.assertEqual(players["ice4"]["uci"]["threads"], 16)
        self.assertFalse(players["A"]["evidence"]["source_contract_verified"])
        self.assertFalse(players["ice4"]["evidence"]["source_to_native_proven"])
        self.assertFalse(players["ice4"]["evidence"]["allocation_observed"])
        claims = draft["content"]["claims"]
        self.assertIs(claims["local_pins_replayed"], True)
        self.assertIs(claims["opening_pgn_mapping_verified"], True)
        self.assertTrue(all(value is False for key, value in claims.items()
                            if key not in ("local_pins_replayed", "opening_pgn_mapping_verified")))
        self.assertEqual(draft["content"]["clock"], {"initial_seconds": 1800, "increment_seconds": 3,
            "ponder_requested": False, "unsupported_ponder": "record-and-proceed"})
        pair, = draft["content"]["pairs"]
        self.assertEqual(pair["opening_index"], 1)
        a, b = pair["games"]
        self.assertEqual((a["white"], a["black"]), (b["black"], b["white"]))

    def test_p192_uses_approved_256_gib_peer_request(self):
        args, _, _, _, _ = self.fixture("test-p192", "c4ke")
        draft = self.prepare(args)
        peer = next(row for row in draft["content"]["players"] if row["identity"]["family"] == "c4ke")
        self.assertEqual(peer["uci"]["hash_mib"], 262144)
        self.assertEqual(peer["uci"]["threads"], 192)
        self.assertEqual(peer["identity"]["tt_bytes"], 256 << 30)
        self.assertIsNotNone(self.verify(draft))

    def test_rehashed_pgn_with_different_moves_is_rejected(self):
        args, _, _, _, opening = self.fixture()
        opening.write_bytes(opening.read_bytes().replace(b"Nf6 *", b"Nge7 *"))
        bank = Path(args["bank_path"])
        record = json.loads(bank.read_text(encoding="utf-8"))
        record["files"]["broad"] = pin(opening)
        bank.write_text(json.dumps(record), encoding="utf-8")
        args["bank_sha256"] = pin(bank)["sha256"]
        with self.assertRaisesRegex(ValueError, "opening PGN differs"):
            self.prepare(args)

    def test_bank_validation_uses_same_pgn_snapshot_without_reopening(self):
        args, _, _, _, opening = self.fixture()
        file_sha = registry.file_sha
        json_input = plan.run.json_input
        def guarded(path):
            if Path(path) == opening:
                raise AssertionError("bank validator reopened the PGN pathname")
            return file_sha(path)
        def guarded_json(path, *args, **kwargs):
            if Path(path) == Path(args_for_test["bank_path"]):
                raise AssertionError("bank validator reopened the bank pathname")
            return json_input(path, *args, **kwargs)
        args_for_test = args
        with patch.object(registry, "file_sha", side_effect=guarded), \
             patch.object(plan.run, "json_input", side_effect=guarded_json):
            draft = self.prepare(args)
        self.assertTrue(draft["content"]["claims"]["opening_pgn_mapping_verified"])

    @unittest.skipUnless(os.name == "posix", "Linux no-follow input contract")
    def test_bank_snapshot_rejects_hardlink_before_input_use(self):
        args, _, _, _, _ = self.fixture()
        bank = Path(args["bank_path"])
        alias = self.root / "bank-copy.json"
        os.link(bank, alias)
        with self.assertRaisesRegex(ValueError, "single-link"):
            self.prepare(args)

    def test_candidate_profile_full_and_original_pins_are_revalidated(self):
        args, rove, peer, save, _ = self.fixture("test-p192")
        mutations = ((rove["artifact"], "full", False), (rove["artifact"], "family", "D"),
                     (peer["artifact"], "tt_bytes", 192 << 30),
                     (peer, "evidence", {"kind": "file-pins-only"}))
        for obj, key, replacement in mutations:
            with self.subTest(key=key, value=replacement):
                previous = obj[key]
                obj[key] = replacement
                args["candidate_sha256"] = save()
                with self.assertRaises((ValueError, TypeError)):
                    self.prepare(args)
                obj[key] = previous
        args["candidate_sha256"] = save()
        peer_source = Path(peer["source"]["path"])
        peer_source.write_bytes(b"changed upstream source")
        with self.assertRaises((ValueError, OSError)):
            self.prepare(args)

    def test_frozen_plan_and_live_inputs_detect_mutation(self):
        args, rove, _, _, opening = self.fixture()
        draft = self.prepare(args)
        tampered = copy.deepcopy(draft)
        tampered["content"]["profile"] = "test-p192"
        with self.assertRaises((ValueError, TypeError)):
            self.verify(tampered)
        tampered = copy.deepcopy(draft)
        tampered["content"]["claims"]["go_authorized"] = True
        # A self-consistent hash is not enough; replay must reject a forged claim.
        tampered["sha256"] = plan.ledger.digest(tampered["content"])
        with self.assertRaises((ValueError, TypeError)):
            self.verify(tampered)
        tampered = copy.deepcopy(draft)
        tampered["content"]["pairs"][0]["games"][1]["white"] = "Rove-A"
        tampered["sha256"] = plan.ledger.digest(tampered["content"])
        with self.assertRaises((ValueError, TypeError)):
            self.verify(tampered)
        with patch.object(original.peers, "verify_blob"), self.assertRaises((ValueError, TypeError)):
            plan.verify(draft, "0" * 64)
        whole = Path(rove["artifact"]["path"])
        old_whole = whole.read_bytes()
        whole.write_bytes(b"different")
        with self.assertRaises((ValueError, OSError)):
            self.verify(draft)
        whole.write_bytes(old_whole)
        with self.assertRaises((ValueError, TypeError)):
            bad = dict(args)
            bad["candidate_sha256"] = "0" * 64
            self.prepare(bad)
        old_runner = args["runner_binary"].read_bytes()
        args["runner_binary"].write_bytes(b"different runner")
        with self.assertRaises((ValueError, OSError)):
            self.verify(draft)
        args["runner_binary"].write_bytes(old_runner)
        old_bank = args["bank_path"].read_bytes()
        args["bank_path"].write_bytes(b"{}")
        with self.assertRaises((ValueError, OSError)):
            self.verify(draft)
        args["bank_path"].write_bytes(old_bank)
        opening.write_bytes(b"tampered PGN")
        with self.assertRaises((ValueError, OSError)):
            self.verify(draft)

    def test_canonical_wire_and_duplicate_keys_are_checked(self):
        args, _, _, _, _ = self.fixture()
        draft = self.prepare(args)
        with patch.object(original.peers, "verify_blob"):
            raw = plan.ledger.canonical(draft)
            self.assertEqual(plan.verify_bytes(raw, draft["sha256"]), draft)
            self.assertEqual(plan.verify_bytes(raw + b"\n", draft["sha256"]), draft)
            with self.assertRaises((ValueError, TypeError)):
                plan.verify_bytes(b'{"format":"x","format":"y"}', draft["sha256"])
            with self.assertRaises((ValueError, TypeError)):
                plan.verify_bytes(json.dumps(draft, indent=2).encode(), draft["sha256"])


if __name__ == "__main__":
    unittest.main()
