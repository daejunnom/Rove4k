"""A matching self-digest does not make a partial schedule complete."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import ledger
import registry
import run
import test_run


class FrozenSchedule(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        fixture = test_run.PlanAndControllerTests()
        registry_path, bank, bank_sha, binary, build, snapshot = fixture.inputs(root)
        content = json.loads(registry_path.read_bytes())
        identity, family = "fixture-C", "C"
        data = b"synthetic contract fixture, no executable engine: fixture-C"
        source = root / identity
        source.write_bytes(data)
        profile = registry.production.resource_profile("test-p4")
        artifact = registry.Artifact(identity, family, source, "test", "test-p4", 4,
            profile.layout(24).bytes, 24, "source-jit", True, test_run.sha(data), len(data), test_run.sha(b"native-fixture" + data))
        receipt = {"format": "rove4k-qualification-v1", "complete": True, "failures": [],
            "division": "general4k", "artifact": artifact.identity(),
            "checks": {name: True for name in registry.CHECKS},
            "observations": {"startup_ms": 1, "workers": 4, "positive_cpu_workers": 4,
                "tt_bytes": artifact.tt_bytes, "runtime_native_sha256": artifact.native_sha256,
                "physical_cores": 4, "logical_cpus": 4, "temporary_cleanup_while_live": True,
                "nbrq_replay": True, "nbrq_generation": True}}
        proof = root / (identity + ".json")
        proof.write_bytes(ledger.canonical(receipt))
        content["players"].append({"artifact": {**artifact.identity(), "path": str(source)},
                                   "receipt": str(proof), "receipt_sha256": test_run.sha(proof.read_bytes())})
        registry_path.write_bytes(ledger.canonical(content))
        self.plan = run.freeze_plan("fixture", "test-p4", registry_path, bank, bank_sha,
                                    binary, build, root / "bundle", snapshot=snapshot)
        self.path = root / "bundle/plan.json"

    def write_and_load(self, plan):
        plan["sha256"] = ledger.digest(plan["content"])
        self.path.write_bytes(ledger.canonical(plan))
        return run.load_plan(self.path)

    def test_complete_deterministic_schedule_loads(self):
        plan, _ = self.write_and_load(copy.deepcopy(self.plan))
        self.assertEqual(len(plan["content"]["pairs"]), 3)

    def test_rehashed_partial_duplicate_repeat_and_order_are_rejected(self):
        def remove(pairs):
            pairs.pop()
        def duplicate(pairs):
            pairs[1] = {**pairs[0], "id": "unique-but-not-scheduled"}
        def change_repeat(pairs):
            pairs[0]["repeat"] = 1
        def reorder(pairs):
            pairs[0], pairs[1] = pairs[1], pairs[0]
        def change_id(pairs):
            pairs[0]["id"] = "unique-but-not-derived"
        def bool_repeat(pairs):
            pairs[0]["repeat"] = False
        def bool_opening_index(pairs):
            pairs[0]["opening_index"] = True
        for change in (remove, duplicate, change_repeat, reorder, change_id, bool_repeat, bool_opening_index):
            with self.subTest(change=change):
                plan = copy.deepcopy(self.plan)
                change(plan["content"]["pairs"])
                with self.assertRaisesRegex(ValueError, "schedule differs"):
                    self.write_and_load(plan)

    def test_update_allows_one_or_two_opening_pairs_of_one_family(self):
        root = Path(self.temp.name) / "update"
        root.mkdir()
        fixture = test_run.PlanAndControllerTests()
        registry_path, bank, _, binary, build, snapshot = fixture.inputs(root)
        reg = json.loads(registry_path.read_bytes())
        second = reg["players"][1]
        second["artifact"]["family"] = "A"
        proof_path = Path(second["receipt"])
        proof = json.loads(proof_path.read_bytes())
        proof["artifact"]["family"] = "A"
        proof_path.write_bytes(ledger.canonical(proof))
        second["receipt_sha256"] = test_run.sha(proof_path.read_bytes())
        registry_path.write_bytes(ledger.canonical(reg))
        bank_data = json.loads(bank.read_bytes())
        bank_data["stages"]["update1"] = bank_data["stages"]["broad"]
        bank_data["files"]["update1"] = bank_data["files"]["broad"]
        bank.write_bytes(ledger.canonical(bank_data))
        for repeats in (1, 2):
            with self.subTest(repeats=repeats):
                out = root / f"bundle-{repeats}"
                plan = run.freeze_plan("fixture", "test-p4", registry_path, bank,
                    test_run.sha(bank.read_bytes()), binary, build, out, stage="update1",
                    snapshot=snapshot, selected_ids=["fixture-A", "fixture-B"], repeats=repeats)
                loaded, _ = run.load_plan(out / "plan.json")
                self.assertEqual(ledger.canonical(loaded), ledger.canonical(plan))
                self.assertEqual([p["repeat"] for p in loaded["content"]["pairs"]], list(range(repeats)))


if __name__ == "__main__":
    unittest.main()
