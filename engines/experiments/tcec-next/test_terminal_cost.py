"""Pure controller boundary regressions; no factory, compiler or codec calls."""
import copy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("terminal_cost_pure_tests", HERE / "terminal_cost.py")
cost = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cost
spec.loader.exec_module(cost)


def receipt(kind):
    return dict(format=1, **{"class": kind}, family="A", entry="A", complete=True, reproducible=True,
                host_cleanup={"unsettled_commands": 0, "errors": []},
                commands=[dict(started=True, terminal=True, reaped=True, returncode=0,
                               owned_group_absent=True, forced_cleanup=False)])


class TerminalCostBoundaries(unittest.TestCase):
    def test_inactive_measure_and_cli_never_capture_or_create_output(self):
        with patch.object(cost, "capture", side_effect=AssertionError("source capture forbidden")) as capture:
            with self.assertRaises(ValueError):
                cost.measure("A", Path("unused"))
            with patch.object(cost, "measure", side_effect=AssertionError("measure forbidden")) as measure:
                with self.assertRaises(SystemExit) as error:
                    cost.main(["--entry", "A", "--out", "unused"])
                self.assertEqual(error.exception.code, 2)
                measure.assert_not_called()
            capture.assert_not_called()

    def test_finite_plan_factory_flags_and_separate_outer_count(self):
        for family in ("A", "E"):
            plan = cost.plan(family)
            self.assertEqual(plan["outer_commands"], 14)
            self.assertEqual(plan["profile"], "test-p4")
            self.assertEqual(plan["cases"], ["control", "terminal-owner-late-queries"])
            command = cost.factory_argv(family, Path("/external/new"))
            self.assertEqual(command.count("--scan-variant"), int(family == "A"))
            self.assertNotIn("--measure", command)
            self.assertNotIn("--compile-executor", command)
            self.assertEqual(command[command.index("--profile") + 1], "test-p4")
        for family in ("B", "C", "D", "F", "F8", True):
            with self.assertRaises(ValueError):
                cost.plan(family)

    def test_factory_native_per_call_limits_restore_on_success_and_failure(self):
        for factory in (False, True):
            for fail in (False, True):
                owner = SimpleNamespace(LIMITS=dict(child_AS=7, child_CPU=8, nested_producer_AS=9, other=10))
                original = dict(owner.LIMITS)
                seen = []

                class Host:
                    report = {"commands": []}

                    def save(self):
                        pass

                    def run(self, command, **kwargs):
                        limits = dict(AS=owner.LIMITS["child_AS"], CPU=owner.LIMITS["child_CPU"])
                        seen.append(limits)
                        self.report["commands"].append(dict(kind=kwargs["kind"], child_limits=limits))
                        if fail:
                            raise RuntimeError("retained original failure")
                        return b"pure mock result"

                host = Host()
                if fail:
                    with self.assertRaisesRegex(RuntimeError, "retained original failure"):
                        cost.run_command(host, owner, ["never-executed"], cwd=Path("unused"),
                                         kind="fresh-profile" if factory else "native", factory=factory)
                else:
                    self.assertEqual(cost.run_command(host, owner, ["never-executed"], cwd=Path("unused"),
                        kind="fresh-profile" if factory else "native", factory=factory), b"pure mock result")
                self.assertEqual(seen, [dict(AS=4 << 30, CPU=480) if factory else dict(AS=2 << 30, CPU=120)])
                self.assertEqual(owner.LIMITS, original)

    def test_new_factory_receipt_contract_rejects_legacy_and_unsettled_records(self):
        profile = receipt("rove4k-production-profile-v1")
        control = receipt("tcec-full-C-v1")
        cost.validate_factory_receipts(profile, control, "A")
        legacy = dict(complete=True, source_reproduced=True, native_reproduced=True,
                      whole_reproduced=True, shell_header_reproduced=True, owned_tool_handles=0)
        with self.assertRaises(ValueError):
            cost.validate_factory_receipts(legacy, control, "A")
        for key, value in (("format", True), ("complete", 1), ("family", "F")):
            changed = copy.deepcopy(profile)
            changed[key] = value
            with self.assertRaises(ValueError):
                cost.validate_factory_receipts(changed, control, "A")
        for key, value in (("returncode", False), ("reaped", False), ("forced_cleanup", True)):
            changed = copy.deepcopy(control)
            changed["commands"][0][key] = value
            with self.assertRaises(ValueError):
                cost.validate_factory_receipts(profile, changed, "A")

    def test_lower_inherited_caps_are_never_raised(self):
        limits = cost.limit_plan((100, 500), (4 << 30, 4 << 30), (1024, 2048))
        self.assertEqual(limits["parent_CPU"], (100, 500))
        self.assertEqual(limits["FSIZE"], (1024, 1024))
        for cpu, address in (((100, 479), (-1, -1)), ((-1, -1), (2 << 30, 4 << 30))):
            with self.assertRaises(ValueError):
                cost.limit_plan(cpu, address, (-1, -1))


if __name__ == "__main__":
    unittest.main()
