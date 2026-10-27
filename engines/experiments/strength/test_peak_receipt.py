"""Receipt boundary tests; no cgroups, engines, cloud or large allocations."""
import copy
import hashlib
import json
import unittest

try:
    from . import peak_receipt
except ImportError:
    import peak_receipt


def sign_digest(report):
    core = {key: value for key, value in report.items() if key != "observation_sha256"}
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    report["observation_sha256"] = hashlib.sha256(raw).hexdigest()


def sample():
    expected = {
        "profile": "test-p192", "plan": [{"slot": "slot-0", "cgroup_path": "/sys/fs/cgroup/league/slot-0",
                                             "cpus": list(range(192)), "nodes": [0, 1],
                                             "artifacts": [{"id": "A"}, {"id": "B"}]}],
        "boot_id": "expected-boot", "cgroup_root": "/sys/fs/cgroup/league",
        "controller_cgroup_path": "/sys/fs/cgroup/league/controller",
        "runner_sha256": "1" * 64, "controller_sha256": "2" * 64,
        "observer_source_sha256": "3" * 64,
        "now_monotonic_ns": 300, "max_age_ns": 200,
    }
    report = {name: copy.deepcopy(value) for name, value in expected.items()
              if name not in ("now_monotonic_ns", "max_age_ns")}
    report.update({"format": "rove4k-cohort-peak-observation-v2", "started_ns": 100,
                   "finished_ns": 200, "test_inputs": False,
                   "game_groups_empty_observed": True, "controller_cleanup_observed": False,
                   "samples": [{"games": [{"slot": "slot-0"}]}],
                   "finished_game_groups": [{"slot": "slot-0"}]})
    report.update({name: False for name in peak_receipt._UNPROVEN})
    sign_digest(report)
    return report, expected


class PeakReceiptTests(unittest.TestCase):
    def test_matching_fabrication_is_only_diagnostic_and_not_admission(self):
        # This entire input is fabricated: its self-hash cannot authenticate it.
        report, expected = sample()
        entries = []
        result = peak_receipt.record_diagnostic(lambda name, data: entries.append((name, data)),
                                                report, expected=expected)
        self.assertEqual(entries, [("campaign.memory_peak_diagnostic", result)])
        self.assertFalse(result["authenticated"])
        self.assertFalse(result["actual_owner_verified"])
        self.assertFalse(result["all_tt_resident_verified"])
        self.assertFalse(result["runtime_admission"])
        self.assertFalse(result["scored_qualification"])
        self.assertNotIn("per_game_overhead_bytes", result)
        self.assertNotIn("controller_reserve_bytes", result)

    def test_tampering_and_context_mismatch_are_rejected(self):
        report, expected = sample()
        report["boot_id"] = "other"
        with self.assertRaisesRegex(ValueError, "digest differs"):
            peak_receipt.inspect_diagnostic(report, expected=expected)
        sign_digest(report)
        with self.assertRaisesRegex(ValueError, "context differs"):
            peak_receipt.inspect_diagnostic(report, expected=expected)

    def test_stale_and_missing_independent_context_are_rejected(self):
        report, expected = sample()
        expected["now_monotonic_ns"] = 401
        with self.assertRaisesRegex(ValueError, "freshness"):
            peak_receipt.inspect_diagnostic(report, expected=expected)
        del expected["plan"]
        with self.assertRaisesRegex(ValueError, "independent expected"):
            peak_receipt.inspect_diagnostic(report, expected=expected)

    def test_synthetic_inputs_and_claimed_proofs_are_rejected_even_if_rehashed(self):
        report, expected = sample()
        report["test_inputs"] = True
        sign_digest(report)
        with self.assertRaisesRegex(ValueError, "synthetic observation"):
            peak_receipt.inspect_diagnostic(report, expected=expected)
        report["test_inputs"] = False
        report["all_tt_resident_verified"] = True
        sign_digest(report)
        with self.assertRaisesRegex(ValueError, "unsupported qualification"):
            peak_receipt.inspect_diagnostic(report, expected=expected)

    def test_failed_inspection_never_appends(self):
        report, expected = sample()
        report["controller_cleanup_observed"] = True
        sign_digest(report)
        entries = []
        with self.assertRaisesRegex(ValueError, "lifecycle"):
            peak_receipt.record_diagnostic(lambda *args: entries.append(args), report, expected=expected)
        self.assertEqual(entries, [])

    def test_incomplete_fabricated_cohort_is_rejected(self):
        report, expected = sample()
        report["samples"] = []
        sign_digest(report)
        with self.assertRaisesRegex(ValueError, "complete cohort"):
            peak_receipt.inspect_diagnostic(report, expected=expected)


if __name__ == "__main__":
    unittest.main()
