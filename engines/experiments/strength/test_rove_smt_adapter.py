"""Synthetic records test the adapter contract, never actual host evidence."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import registry
import rove_smt_adapter as adapter
import test_registry


def put(path, value):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


class AdapterTests(unittest.TestCase):
    def fixture(self, directory):
        helper = test_registry.RegistryTests()
        original, base = helper.fixture(directory)
        artifact = registry.Artifact(**{**original.__dict__, "id": "a-p16", "profile": "test-p16",
                                        "workers": 16, "tt_bytes": 12 << 30})
        runtime, source = directory / "runtime.json", directory / "engine.c"
        runtime_sha = put(runtime, b'{"synthetic":true}')
        source_sha = put(source, b'/* synthetic source only */')
        binding = {"runtime_sha256": runtime_sha, "source_sha256": source_sha,
                   "boot_id": "01234567-89ab-cdef-0123-456789abcdef", "cgroup_path": "/rove4k/slot",
                   "tt_symbol": "qq", "tt_symbol_evidence_sha256": "7" * 64}
        report = {**base, "artifact": artifact.identity(), "format": "rove4k-qualification-v2",
                  "division": "league-test", "qualification_scope": "league-test",
                  "functional_runtime_complete": True, "test_qualified": True, "release_qualified": False,
                  "event_target_confirmed": False, "score_authorized": False,
                  "submission_size_within_4096": True, "source_sha256": source_sha,
                  "smt_binding": binding, "evidence": {"runtime": {"sha256": runtime_sha}},
                  "observations": {**base["observations"], "workers": 16, "positive_cpu_workers": 16,
                                   "tt_bytes": artifact.tt_bytes, "physical_cores": 8, "logical_cpus": 16}}
        receipt, receipt_sha = helper.write_receipt(directory, report)
        smt, _ = helper.smt_fixture()
        smt.update(format="rove4k-owned-smt-observation-v1", qualification_sha256=receipt_sha,
                   artifact=artifact.identity(), binding=deepcopy(binding))
        overhead = 768 << 20
        for session in smt["sessions"]:
            session["owner"].update(whole_sha256=artifact.sha256, runtime_native_sha256=artifact.native_sha256,
                                    boot_id=binding["boot_id"], cgroup_path=binding["cgroup_path"])
            session["image"]["native_sha256"] = artifact.native_sha256
            session["image"]["tt"].update(tt_bytes=artifact.tt_bytes, symbol=binding["tt_symbol"],
                                          symbol_evidence_sha256=binding["tt_symbol_evidence_sha256"])
            session["image"]["tt"]["mappings"][0]["end"] = 0x110 + artifact.tt_bytes
            session["runtime_budget"].update(tt_bytes=artifact.tt_bytes,
                address_space_bytes=artifact.tt_bytes + overhead, required_available_bytes=0)
            session["preexec_placement"]["runtime_limits"]["address_space"] = [artifact.tt_bytes + overhead] * 2
            session["finish"].update(leader_exited_with_other_members=False, other_members_observed=[])
        numa = smt["sessions"][0]["post_go_tt_numa"]
        numa["tt_bytes"] = artifact.tt_bytes
        numa["tt_mappings"][0]["end"] = 0x110 + artifact.tt_bytes
        observation = directory / "smt-observation.json"
        pin = put(observation, smt)
        args = dict(qualification_path=receipt, qualification_sha256=receipt_sha, runtime_path=runtime,
                    runtime_sha256=runtime_sha, source_path=source, source_sha256=source_sha)
        return artifact, observation, pin, args, smt

    def test_incomplete_lifecycle_is_never_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            artifact, observation, _, _, _ = self.fixture(directory)
            lifecycle = {"format": "rove4k-owned-lifecycle-v1", "artifact": artifact.identity(),
                         "profile": artifact.profile, "complete": False, "sessions": [], "claims": {}}
            pin = put(observation, lifecycle)
            result = adapter.inspect_owned_observation(artifact, observation, pin)
            self.assertEqual(result["status"], "incomplete")
            self.assertGreaterEqual(len(result["reasons"]), 6)
            self.assertFalse(result["diagnostic_eligible"] or result["score_authorized"] or result["release_authorized"])

    def test_synthetic_complete_record_uses_real_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact, observation, pin, args, smt = self.fixture(Path(tmp).resolve())
            result = adapter.inspect_owned_observation(artifact, observation, pin, **args)
            self.assertEqual(result["status"], "consistent")
            self.assertFalse(result["digest_authenticates_origin"] or result["host_origin_authenticated"] or
                             result["source_origin_authenticated"] or result["score_authorized"] or
                             result["release_authorized"] or result["performance_authorized"])
            smt["sessions"][0]["owner"]["boot_id"] = "wrong"
            pin = put(observation, smt)
            with self.assertRaises(ValueError):
                adapter.inspect_owned_observation(artifact, observation, pin, **args)

    def test_independent_pins_and_files_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact, observation, pin, args, _ = self.fixture(Path(tmp).resolve())
            incomplete = adapter.inspect_owned_observation(artifact, observation, pin)
            self.assertEqual(incomplete["status"], "incomplete")
            for field in ("qualification_sha256", "runtime_sha256", "source_sha256"):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    adapter.inspect_owned_observation(artifact, observation, pin, **{**args, field: "0" * 64})
            with self.assertRaises(ValueError):
                adapter.inspect_owned_observation(artifact, observation, "0" * 64, **args)


if __name__ == "__main__":
    unittest.main()
