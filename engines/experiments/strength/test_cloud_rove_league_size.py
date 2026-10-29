"""Focused TEST-versus-submission boundary tests, without engines or AWS."""
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock, patch
import tempfile

try:
    from . import cloud_runtime as cloud
except ImportError:
    import cloud_runtime as cloud


def admitted(size=4097, *, full=True):
    whole_sha = hashlib.sha256(b"x" * size).hexdigest() if type(size) is int and 0 < size <= 131072 else "a" * 64
    return SimpleNamespace(family="A", full=full, expected={"whole_bytes": size, "whole_sha256": whole_sha}, profile_id="test-p4",
                           input_pins={}, program="x")


def verifier(purpose="test"):
    def qualification_record(*args, qualification_scope="general4k", **kwargs):
        return None
    return SimpleNamespace(profile_resource=lambda *a, **k: SimpleNamespace(purpose=purpose),
                           qualification_record=qualification_record)


def receipt(size):
    within = size <= 4096
    return {"format": "rove4k-qualification-v2", "division": "league-test",
            "qualification_scope": "league-test", "checks": {"size": within},
            "submission_size_within_4096": within, "artifact": {"whole_bytes": size},
            "score_authorized": False, "release_qualified": False, "event_target_confirmed": False}


class LeagueTestBoundary(TestCase):
    def test_full_test_build_keeps_real_size_without_a_4k_limit(self):
        for size in (4095, 4096, 4097, 131072):
            with self.subTest(size=size):
                cloud.require_rove_league_test(verifier(), admitted(size))
                cloud.validate_rove_league_test_record(receipt(size), admitted(size))

    def test_release_incomplete_bad_size_and_legacy_verifier_fail_closed(self):
        legacy = SimpleNamespace(profile_resource=lambda *a, **k: SimpleNamespace(purpose="test"),
                                 qualification_record=lambda *a, **k: None)
        with self.assertRaisesRegex(ValueError, "legacy v1 seed exceeds 4KiB"):
            cloud.require_rove_league_test(legacy, admitted())
        self.assertIs(cloud.require_rove_league_test(legacy, admitted(4096)), False)
        with self.assertRaisesRegex(ValueError, "TEST profile"):
            cloud.require_rove_league_test(verifier("submission"), admitted())
        with self.assertRaisesRegex(ValueError, "blocked_full"):
            cloud.require_rove_league_test(verifier(), admitted(full=False))
        for bad in (0, -1, True, "4097"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "positive complete-file"):
                cloud.require_rove_league_test(verifier(), admitted(bad))

    def test_receipt_cannot_conflate_submission_or_forge_size_and_authority(self):
        for field, value in (("format", "rove4k-qualification-v1"), ("division", "general4k"),
                             ("qualification_scope", "general4k"), ("submission_size_within_4096", True),
                             ("score_authorized", True), ("release_qualified", True),
                             ("event_target_confirmed", True)):
            proof = receipt(4097)
            proof[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                cloud.validate_rove_league_test_record(proof, admitted())
        for bad in (True, 4096, "4097"):
            proof = receipt(4097)
            proof["artifact"]["whole_bytes"] = bad
            with self.subTest(artifact_size=bad), self.assertRaises(ValueError):
                cloud.validate_rove_league_test_record(proof, admitted())
        proof = receipt(4097)
        proof["checks"]["size"] = 0
        with self.assertRaises(ValueError):
            cloud.validate_rove_league_test_record(proof, admitted())

    def test_legacy_registry_does_not_open_p16_or_p192_score_path(self):
        class Consumer:
            pass
        with patch.object(cloud, "CloudConsumer", Consumer):
            for profile in ("test-p16", "test-p192"):
                with self.subTest(profile=profile), self.assertRaisesRegex(ValueError, "named TEST profile"):
                    cloud.prepare_registry({}, Path("."), Path("unused"), Consumer(), profile,
                                           execute_command=Mock(), restored_layout=object())

    def test_oversized_legacy_seed_stops_before_compiler_or_engine(self):
        class Layout:
            def revalidate(self):
                pass
            def execution_path(self, name):
                return Path("/fixture") / name
        legacy = SimpleNamespace(profile_resource=lambda *a, **k: SimpleNamespace(purpose="test"),
                                 qualification_record=lambda *a, **k: None,
                                 admit_c_build=Mock(return_value=admitted(4097)))
        compiler = Mock()
        with patch.object(cloud, "load_module", return_value=legacy), \
             patch.object(cloud, "require_rove_bridge"), \
             patch.object(cloud, "OriginalLayout", Layout), \
             patch.object(cloud, "checked_json", return_value={}):
            with self.assertRaisesRegex(ValueError, "regenerate with a league-test verifier"):
                cloud.prepare_rove({"family": "A", "build": "stage"}, seed={"source_tree": "source"},
                    root=Path("/fixture"), out=Path("/unused"), consumer=object(), slot=object(),
                    execute_command=compiler, restored_layout=Layout())
        compiler.assert_not_called()

    def test_real_registry_inspects_prepared_test_receipt_without_score_promotion(self):
        class Layout:
            def __init__(self, root):
                self.root = root
            def revalidate(self):
                pass
            def execution_path(self, name):
                return self.root / name
        class Consumer:
            def revalidate(self):
                pass
            def to_record(self):
                return {"compiler_context": {"driver": {"path": "/cc"}}, "topology": {}}
        reference = SimpleNamespace(source_evidence={}, to_record=lambda: {})
        consumer = Consumer()
        slot = SimpleNamespace(cpus=[0])
        row = {"family": "A", "profile": "test-p4", "build": "stage", "rules": "rules.json"}
        for size, legacy_seed in ((4096, False), (4097, False), (4096, True)):
            with self.subTest(size=size, legacy_seed=legacy_seed), tempfile.TemporaryDirectory(prefix="rove-test-scope-") as tmp:
                root = Path(tmp).resolve()
                stage = root / "stage"
                stage.mkdir()
                program = stage / "x"
                program.write_bytes(b"x" * size)
                artifact = cloud.registry.Artifact("A-test-p4", "A", program, "test", "test-p4", 4,
                    96 << 20, 24, "source-jit", True, hashlib.sha256(program.read_bytes()).hexdigest(),
                    size, "b" * 64)
                mock_verify = verifier()
                mock_verify.admit_c_build = Mock(return_value=admitted(size))
                mock_verify.cloud_rules_receipt = Mock(return_value=Path(tmp) / "rules.json")
                mock_verify.effective_available_bytes = Mock(return_value=1)
                mock_verify.execution_limits = Mock(return_value={})
                mock_verify.run_runtime = Mock()
                calls = []
                def make_proof(qualification_scope):
                    within = size <= 4096
                    proof = {**receipt(size), "artifact": artifact.identity(), "complete": True,
                            "failures": [], "functional_runtime_complete": True, "test_qualified": True,
                            "checks": {**dict.fromkeys(cloud.registry.CHECKS, True), "size": within},
                            "observations": {"startup_ms": 100, "workers": 4, "positive_cpu_workers": 4,
                                "tt_bytes": 96 << 20, "runtime_native_sha256": "b" * 64,
                                "physical_cores": 4, "logical_cpus": 4, "temporary_cleanup_while_live": True,
                                "nbrq_replay": True, "nbrq_generation": True}}
                    if qualification_scope == "general4k":
                        proof["format"] = "rove4k-qualification-v1"
                        proof["division"] = "general4k"
                        proof.pop("qualification_scope")
                        proof.pop("submission_size_within_4096")
                        proof.pop("score_authorized")
                    return proof
                def qualification_record(*args, qualification_scope="general4k", **kwargs):
                    calls.append(qualification_scope)
                    return make_proof(qualification_scope)
                def legacy_record(*args, rules_path=None, target_reference=None):
                    calls.append("legacy-v1")
                    return make_proof("general4k")
                mock_verify.qualification_record = legacy_record if legacy_seed else qualification_record
                command = Mock()
                with patch.object(cloud, "load_module", return_value=mock_verify), \
                     patch.object(cloud, "require_rove_bridge"), \
                     patch.object(cloud, "OriginalLayout", Layout), \
                     patch.object(cloud, "checked_json", return_value={}), \
                     patch.object(cloud, "new_external", side_effect=lambda path: Path(path)), \
                     patch.object(cloud, "validate_cloud_runtime", return_value=reference), \
                     patch.object(cloud, "qualification_slot", return_value=nullcontext()):
                    result = cloud.prepare_rove(row, seed={"source_tree": "source"}, root=tmp,
                                       out=Path(tmp) / "out", consumer=consumer, slot=slot,
                                       execute_command=command, restored_layout=Layout(root))
                expected_calls = ["legacy-v1"] if legacy_seed else (
                    ["league-test", "general4k"] if size == 4096 else ["league-test"])
                self.assertEqual(calls, expected_calls)
                command.assert_called_once()
                mock_verify.run_runtime.assert_called_once()
                self.assertIs(result["diagnostic_eligible"], not legacy_seed)
                self.assertIs(result["score_authorized"], False)
                if legacy_seed:
                    self.assertEqual(result["qualification_scope"], "legacy-general4k")
                    self.assertTrue(cloud.registry.admit_to_test_league(artifact, Path(result["receipt"]),
                                                                       result["receipt_sha256"])["qualified"])
                else:
                    with self.assertRaises(ValueError):
                        cloud.registry.admit_to_test_league(artifact, Path(result["receipt"]), result["receipt_sha256"])
                if size == 4096:
                    legacy = result["legacy_scored_receipt"]
                    self.assertTrue(cloud.registry.admit_to_test_league(artifact, Path(legacy["receipt"]),
                                                                      legacy["receipt_sha256"])["qualified"])
                else:
                    self.assertIsNone(result["legacy_scored_receipt"])

                seed = {"rove": [row], "peers": [], "source_origin": {"fixture": True}}
                fake_topology = SimpleNamespace(from_record=lambda value: object())
                with patch.object(cloud, "CloudConsumer", Consumer), \
                     patch.object(cloud, "revalidate_seed"), \
                     patch.object(cloud.topology, "Topology", fake_topology), \
                     patch.object(cloud.topology, "plan_slots", return_value=[slot]), \
                     patch.object(cloud, "new_external", side_effect=lambda path: Path(path)):
                    registry_path = cloud.prepare_registry(seed, root, root / "registry-out", consumer,
                        "test-p4", execute_command=command, restored_layout=Layout(root),
                        rove_driver=lambda *a, **k: result)
                stored = json.loads(registry_path.read_text(encoding="utf-8"))
                self.assertEqual(len(stored["players"]), 1 if size == 4096 else 0)
                self.assertEqual(len(stored["diagnostic_players"]), 0 if legacy_seed else 1)
                self.assertIs(stored["diagnostic_score_authorized"], False)
                if not legacy_seed:
                    self.assertIs(stored["diagnostic_players"][0]["score_authorized"], False)
                accepted, rejected = cloud.run.qualified_players(stored, "test-p4")
                self.assertEqual(len(accepted), 1 if size == 4096 else 0)
                self.assertEqual(rejected, [])
                if not legacy_seed:
                    forced = {**stored, "players": stored["diagnostic_players"]}
                    accepted, rejected = cloud.run.qualified_players(forced, "test-p4")
                    self.assertEqual(accepted, [])
                    self.assertEqual(len(rejected), 1)
                for payload in (b"tampered", b"z" * size):
                    with self.subTest(tampered_size=len(payload)):
                        program.write_bytes(payload)
                        with self.assertRaisesRegex(ValueError, "artifact bytes"):
                            inspect = (cloud.registry.admit_to_test_league if legacy_seed else
                                       cloud.registry.inspect_league_test_receipt)
                            inspect(artifact, Path(result["receipt"]), result["receipt_sha256"])


if __name__ == "__main__":
    main()
