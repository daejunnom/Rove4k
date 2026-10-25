import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from registry import Artifact, CHECKS, admit_to_test_league


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


if __name__ == "__main__":
    unittest.main()
