"""Pure controller boundary regressions; no factory, compiler or codec calls."""
import copy
import importlib.util
import json
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

    def test_mate_is_explicit_and_uses_each_actual_compiler_and_factory_route(self):
        for family in "ABCE":
            for variant in ("folded", "shared"):
                policy = cost.plan(family, experiment="mate", variant=variant)
                self.assertEqual(policy["outer_commands"], 16)
                self.assertEqual(policy["cases"], ["control", variant])
                self.assertFalse(policy["diagnostic_engine"])
                command = cost.factory_argv(family, Path("/external/new"), experiment="mate", variant=variant)
                self.assertEqual(command.count("--scan-variant"), int(family in "AC"))
                self.assertEqual(command[command.index("--b-variant") + 1],
                                 "tcec-final-lf" if family == "B" else "control")
                self.assertEqual(command[command.index("--phase-variant") + 1],
                                 "control" if family == "B" else "phase-init")
                self.assertEqual(command[command.index("--spelling-variant") + 1],
                                 "best" if family == "B" else "compound")
                self.assertEqual("-mavx2" in policy["compiler"], family == "C")
                self.assertEqual("-pthread" in policy["compiler"], family == "B")
                self.assertEqual("-s" in policy["compiler"], family != "B")
                self.assertIn("-fsanitize=undefined", policy["diagnostic_compiler"])
                self.assertIn("-fno-sanitize-recover=undefined", policy["diagnostic_compiler"])
        for kwargs in (dict(experiment="mate"), dict(experiment="mate", variant="control"),
                       dict(experiment="terminal", variant="folded"), dict(experiment=True)):
            with self.assertRaises(ValueError):
                cost.plan("A", **kwargs)

    def test_lifted_mate_edit_commutes_with_the_real_dependency_owner(self):
        projection = cost.load_bytes("cost_pure_lift_projection", cost.PROJECTION,
                                     (HERE / "spelling_compound.py").read_bytes())
        dependencies = cost.load_bytes("cost_pure_lift_dependencies", cost.DEPENDENCIES,
                                       (HERE / "profile_dependencies.py").read_bytes())
        for has_include in (False, True):
            before = b"HEAD" + (dependencies.DIRECTIVE if has_include else b"") + b"TAIL"
            final, old_dependency = dependencies.transform_source(before)
            candidate, rows, _ = projection._splice(final, [dict(input_begin=4, before="TAIL", after="BODY",
                role="pure-coordinate-transport", component="test")])
            lifted, new_dependency, proof = cost.lift_mate_source(before, final, candidate, {"edits": rows},
                old_dependency, projection=projection, dependencies=dependencies)
            self.assertEqual(lifted, b"HEAD" + (dependencies.DIRECTIVE if has_include else b"") + b"BODY")
            self.assertEqual(dependencies.transform_source(lifted)[0], candidate)
            self.assertEqual(dependencies.restore_source(candidate, new_dependency), lifted)
            self.assertEqual(projection._inverse_edits(lifted, proof["lifted_edits"]), before)
            self.assertTrue(proof["exact_commuting_output"])
            self.assertEqual(cost.lift_source_edits(before, final, candidate, {"edits": rows}, old_dependency,
                projection=projection, dependencies=dependencies), (lifted, new_dependency, proof))
            if has_include:
                crossing, crossing_rows, _ = projection._splice(final, [dict(input_begin=3, before="DTA", after="DTB",
                    role="deliberate-overlap", component="test")])
                with self.assertRaisesRegex(ValueError, "crosses the removed include"):
                    cost.lift_mate_source(before, final, crossing, {"edits": crossing_rows}, old_dependency,
                                         projection=projection, dependencies=dependencies)

    def test_ep_is_explicit_CE_only_and_reuses_the_actual_five_control_pins(self):
        for family in ("C", "E"):
            policy = cost.plan(family, experiment="ep")
            mate = cost.plan(family, experiment="mate", variant="folded")
            self.assertEqual(policy["cases"], ["control", "legal-maker"])
            self.assertEqual(policy["outer_commands"], 16)
            self.assertEqual(policy["control"], mate["control"])
            self.assertEqual(policy["compiler"], mate["compiler"])
            self.assertEqual(policy["compression"], mate["compression"])
            self.assertFalse(policy["diagnostic_engine"])
            self.assertNotIn("variant", policy)
            self.assertEqual(cost.factory_argv(family, Path("/external/new"), experiment="ep"),
                cost.factory_argv(family, Path("/external/new"), experiment="mate", variant="folded"))
            command = policy["diagnostic_compiler"]
            self.assertIn("-fsanitize=undefined", command)
            self.assertIn("-fno-sanitize-recover=undefined", command)
            self.assertEqual("-mavx2" in command, family == "C")
        for family in ("A", "B", "D", "F", "F8", True):
            with self.assertRaises(ValueError):
                cost.plan(family, experiment="ep")
        for variant in ("folded", "shared", "legal-maker", False):
            with self.assertRaises(ValueError):
                cost.plan("C", experiment="ep", variant=variant)

    def test_semantic_receipt_requires_the_actual_exhaustive_domain_and_types(self):
        valid = dict(complete=True, family="C", profile="test-p4", variant="shared", decode_cases=8388608,
                     store_cases=8388608, TT_values=65536, plies=128, checksum=0)
        self.assertEqual(cost.semantic_observation(json.dumps(valid).encode(), family="C", variant="shared"), valid)
        for key, value in (("complete", 1), ("family", "A"), ("variant", "folded"),
                           ("decode_cases", 8388607), ("plies", True), ("checksum", -1)):
            changed = dict(valid)
            changed[key] = value
            with self.assertRaises(ValueError):
                cost.semantic_observation(json.dumps(changed).encode(), family="C", variant="shared")

    def test_mate_preserves_the_complete_factory_closure_and_checks_every_support_overlap(self):
        support = {name: name.encode() for name in cost.SUPPORT if name != cost.HELPER}
        support.update({name: name.encode() for name in (cost.MATE_HELPER, cost.MATE_SEMANTICS)})
        # B's selected best stage has no spelling_compound production input.
        parent = {name: data for name, data in support.items()
                  if name not in (cost.SELF, cost.PROJECTION, cost.MATE_HELPER, cost.MATE_SEMANTICS)}
        parent["parent-only.c"] = b"complete admitted parent input"
        original_parent, original_support = dict(parent), dict(support)
        closure = cost.merge_source_closure(parent, support, experiment="mate")
        self.assertEqual(closure, {**parent, **support})
        self.assertEqual(set(closure), set(parent) | set(support))
        self.assertEqual(parent, original_parent)
        self.assertEqual(support, original_support)
        for name in (cost.PROJECTION, cost.BUILDER):
            conflicting = {**parent, name: b"different frozen input"}
            with self.assertRaisesRegex(ValueError, "factory/captured support differs"):
                cost.merge_source_closure(conflicting, support, experiment="mate")
        with self.assertRaisesRegex(ValueError, "mandatory factory/captured owner missing"):
            cost.merge_source_closure({name: data for name, data in parent.items() if name != cost.BUILDER},
                                      support, experiment="mate")
        with self.assertRaisesRegex(ValueError, "mandatory factory/captured owner missing"):
            cost.merge_source_closure(parent, support)
        self.assertEqual(cost.merge_source_closure({**parent, cost.PROJECTION: support[cost.PROJECTION]}, support),
                         closure)

    def test_outer_limit_cannot_be_raised_outside_the_two_finite_experiments(self):
        for limit in (17, 100, True, 16.0):
            host = SimpleNamespace(report=dict(commands=[], outer_command_limit=limit))
            owner = SimpleNamespace(LIMITS={})
            with self.assertRaisesRegex(ValueError, "outer command limit"):
                cost.run_command(host, owner, ["never-executed"], cwd=Path("unused"), kind="unused")


if __name__ == "__main__":
    unittest.main()
