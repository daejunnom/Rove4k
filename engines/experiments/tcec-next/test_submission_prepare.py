"""Pure selected-submission policy checks; no producer, compiler or engine run."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


prepare = module("submission_prepare_tests_owner", HERE / "submission_prepare.py")
builder = module("submission_prepare_tests_builder", HERE / "profile_build.py")
contracts = module("submission_prepare_tests_contracts", ROOT / "engines/scripts/production.py")


def fixture(family, *, ep_variant="control"):
    chosen = prepare.selection(family, ep_variant=ep_variant)
    spelling = builder.spelling_selection(family, prepare.REPRESENTATION, chosen["b_variant"],
                                          chosen["phase_variant"], chosen["spelling_variant"])
    scan = builder.scan_selection(family, prepare.REPRESENTATION, chosen["phase_variant"], spelling,
                                  chosen["source_dependencies"], chosen["scan_variant"])
    post = dict(path=builder.B_PROFILE, variant="tcec-final-lf") if family == "B" else dict(
        path=builder.PHASE, variant="phase-init")
    record = dict(family=family, entry=family, resources=dict(id=prepare.PROFILE, workers=256),
                plan=dict(representation="source-jit", entry_cleanup="private-path", full=True),
                post_profile=post, post_spelling=spelling, post_scan=scan,
                source_dependencies=dict(path=builder.DEPENDENCIES, variant="unused-includes"),
                compiler=["cc", "-Os"], compile_executor=["cc", "-Os"])
    if ep_variant == "legal-maker":
        record["post_ep"] = dict(path=builder.EP, variant="legal-maker")
    if chosen.get("final_compact") == "selected":
        compact = builder.FINAL_COMPACTS[family]
        record["post_compact"] = {"path": compact["path"], "variant": compact["variant"]}
    return record


class SubmissionPreparation(unittest.TestCase):
    def test_opt_in_precedes_source_admission_and_output(self):
        with patch.object(prepare, "load") as load, patch.object(prepare, "external_path") as path:
            with self.assertRaisesRegex(ValueError, "without --execute"):
                prepare.prepare_submission("unread", "uncreated", family="A")
            with self.assertRaises(SystemExit) as error:
                prepare.main(["--entry", "A", "--build", "unread", "--out", "uncreated"])
            self.assertEqual(error.exception.code, 2)
            load.assert_not_called()
            path.assert_not_called()

    def test_existing_producer_arguments_are_explicit_full_submission_choices(self):
        for family in "ABCEF":
            arguments = prepare.selected_arguments(family)
            self.assertEqual(arguments[arguments.index("--profile") + 1], "tcec-provisional")
            self.assertEqual(arguments[arguments.index("--representation") + 1], "source-jit")
            self.assertEqual(arguments[arguments.index("--source-dependencies") + 1], "unused-includes")
            self.assertNotIn("--out", arguments)
            self.assertNotIn("--runtime", arguments)
            self.assertNotIn("--ep-variant", arguments)
            self.assertEqual(arguments[arguments.index("--b-variant") + 1], "tcec-final-lf" if family == "B" else "control")
            self.assertEqual(arguments[arguments.index("--spelling-variant") + 1],
                             "best" if family == "B" else "compound-v2" if family == "F" else "compound")
            self.assertEqual(arguments[arguments.index("--scan-variant") + 1],
                             "square-successor" if family in "AC" else "control")
        for family in ("D", "F8", "G", True, None):
            with self.assertRaises(ValueError):
                prepare.selected_arguments(family)

    def test_selected_full_entries_require_the_reviewed_final_compact_stage(self):
        for family in "ABCEF":
            ep = "legal-maker" if family in "CE" else "control"
            chosen = prepare.selected_arguments(family, ep_variant=ep)
            at = chosen.index("--final-compact")
            self.assertEqual(chosen[at:at + 2], ["--final-compact", "selected"])
            record = fixture(family, ep_variant=ep)
            prepare.validate_selection(record, family, builder, ep_variant=ep)
            for changed in (None, {"path": "foreign.py", "variant": "selected"},
                            {"path": builder.FINAL_COMPACTS[family]["path"], "variant": "control"}):
                bad = copy.deepcopy(record)
                bad["post_compact"] = changed
                with self.subTest(family=family, changed=changed), self.assertRaises(ValueError):
                    prepare.validate_selection(bad, family, builder, ep_variant=ep)

    def test_CE_EP_selection_is_explicit_and_preserves_the_maintained_pipeline(self):
        for family in "CE":
            control = prepare.selection(family)
            selected = prepare.selection(family, ep_variant="legal-maker")
            self.assertNotIn("ep_variant", control)
            self.assertEqual(selected, {**control, "ep_variant":"legal-maker", "final_compact":"selected"})
            arguments = prepare.selected_arguments(family, ep_variant="legal-maker")
            at = arguments.index("--ep-variant")
            self.assertEqual(arguments[at:at + 2], ["--ep-variant", "legal-maker"])
            del arguments[at:at + 2]
            at = arguments.index("--final-compact")
            self.assertEqual(arguments[at:at + 2], ["--final-compact", "selected"])
            del arguments[at:at + 2]
            self.assertEqual(arguments, prepare.selected_arguments(family))
        for family in "ABF":
            with self.subTest(family=family), self.assertRaises(ValueError):
                prepare.selection(family, ep_variant="legal-maker")
            with self.assertRaises(ValueError):
                prepare.selected_arguments(family, ep_variant="legal-maker")
        for variant in (None, True, "", "other"):
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                prepare.selected_arguments("C", ep_variant=variant)

    def test_EP_metadata_must_match_the_explicit_submission_request(self):
        # These are recipe-grammar fixtures; genuine native policy belongs to R.
        for family in "CE":
            selected = fixture(family, ep_variant="legal-maker")
            prepare.validate_selection(selected, family, builder, ep_variant="legal-maker")
            with self.assertRaises(ValueError):
                prepare.validate_selection(selected, family, builder)
            for declaration in (None, {}, {"path":"foreign.py", "variant":"legal-maker"},
                                {"path":builder.EP, "variant":"control"},
                                {"path":builder.EP, "variant":"legal-maker", "extra":True}):
                changed = copy.deepcopy(selected)
                changed["post_ep"] = declaration
                with self.subTest(family=family, declaration=declaration), self.assertRaises(ValueError):
                    prepare.validate_selection(changed, family, builder, ep_variant="legal-maker")
            for value in ({}, None):
                changed = fixture(family)
                changed["ep_native_policy"] = value
                with self.assertRaises(ValueError):
                    prepare.validate_selection(changed, family, builder)
            compatible = fixture(family)
            compatible["post_ep"] = None
            prepare.validate_selection(compatible, family, builder)
        with self.assertRaises(ValueError):
            prepare.validate_selection(fixture("A"), "A", builder, ep_variant="legal-maker")

    def test_EP_CLI_requires_opt_in_and_forwards_choice_without_runtime_qualification(self):
        with patch.object(prepare, "load") as load, patch.object(prepare, "external_path") as path:
            with self.assertRaisesRegex(ValueError, "without --execute"):
                prepare.prepare_submission("unread", "uncreated", family="C", ep_variant="legal-maker")
            with self.assertRaises(SystemExit) as error:
                prepare.main(["--entry", "C", "--build", "unread", "--out", "uncreated",
                              "--ep-variant", "legal-maker"])
            self.assertEqual(error.exception.code, 2)
            load.assert_not_called()
            path.assert_not_called()
        for family in "CE":
            result = dict(prepared=True, size={"general4k":{"status":"within_limit"}})
            with patch.object(prepare, "prepare_submission", return_value=result) as consume, \
                    patch.object(sys, "stdout", new_callable=io.StringIO) as output:
                self.assertEqual(prepare.main(["--entry", family, "--build", "unread", "--out", "uncreated",
                                               "--ep-variant", "legal-maker", "--execute"]), 0)
                consume.assert_called_once_with(Path("unread"), Path("uncreated"), family=family,
                                                ep_variant="legal-maker", execute=True)
                observed = json.loads(output.getvalue())
            self.assertEqual(observed["profile"], "tcec-provisional")
            self.assertFalse(observed["runtime_qualified"])
            self.assertFalse(observed["event_target_confirmed"])

    def test_selection_uses_current_producer_grammar_and_rejects_stale_or_test_inputs(self):
        for family in "ABCEF":
            original = fixture(family)
            prepare.validate_selection(original, family, builder)
            changes = (
                lambda row: row["resources"].update(id="test-p28"),
                lambda row: row["resources"].update(workers=28),
                lambda row: row["plan"].update(full=False),
                lambda row: row["plan"].update(representation="packed-native"),
                lambda row: row.update(post_profile=None),
                lambda row: row.update(post_spelling=None),
                lambda row: row.update(source_dependencies=None),
                lambda row: row.update(compile_executor=["other-cc", "-Os"]),
            )
            for change in changes:
                altered = copy.deepcopy(original)
                change(altered)
                with self.assertRaises(ValueError):
                    prepare.validate_selection(altered, family, builder)
        alias = fixture("B")
        alias["spelling_request"] = dict(requested="compound", effective="best")
        with self.assertRaises(ValueError):
            prepare.validate_selection(alias, "B", builder)
        stale_f = fixture("F")
        stale_f["post_spelling"] = dict(builder.COMPOUND_DECLARATION)
        with self.assertRaises(ValueError):
            prepare.validate_selection(stale_f, "F", builder)

    def test_size_decisions_never_qualify_source_jit_as_elf(self):
        for family in "ABCEF":
            limit = prepare.size_decisions(family, 4096, contracts)
            self.assertEqual(limit["general4k"]["status"], "within_limit")
            self.assertEqual(limit["elf4k"]["status"], "not_applicable")
            self.assertFalse(limit["general4k"]["qualified"])
            above = prepare.size_decisions(family, 4097, contracts)
            self.assertEqual(above["general4k"]["status"], "blocked_size")
            self.assertEqual(above["elf4k"]["status"], "not_applicable")
        elf = contracts.ArtifactPlan(contracts.engine_spec("A"), contracts.resource_profile(prepare.PROFILE),
                                     "self-contained-elf", "none", full=True)
        self.assertEqual(elf.size_decision(4097, "elf4k")["status"], "deferred_size")

    def test_output_paths_are_external_new_and_protected_names_are_not_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(prepare.external_path(root, existing=True), root)
            self.assertEqual(prepare.external_path(root / "new", existing=False), root / "new")
            with self.assertRaises(ValueError):
                prepare.external_path(root, existing=False)
            for leaf in (".env", ".aws", "inventory.json", "service-account"):
                with self.assertRaisesRegex(ValueError, "protected"):
                    prepare.external_path(root / leaf, existing=False)
        with self.assertRaises(ValueError):
            prepare.external_path(Path("relative"), existing=False)


if __name__ == "__main__":
    unittest.main()
