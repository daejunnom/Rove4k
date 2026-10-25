"""Pure negative boundaries for the explicit D structural-search admission."""
import importlib.util
from copy import deepcopy
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PATH = Path(__file__).with_name("search_admission.py")
SPEC = importlib.util.spec_from_file_location("D_search_admission_tests", PATH)
ADMIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ADMIT
SPEC.loader.exec_module(ADMIT)


def command(kind, index=1):
    return {"kind": kind, "command": ["cc"], "cwd": "/owned", "pid": index, "pgid": index,
        "started": True, "terminal": True, "reaped": True, "owned_group_absent": True,
        "original_identity_retained_until_other_members_absent": True, "forced_cleanup": False,
        "other_group_members_before_reap": [], "returncode": 0}


def record():
    value = {"kind": ADMIT.EXPERIMENT_KIND, "complete": True, "frozen_execution": True,
        "inputs": {name: {} for name in {"selection/build.json", *ADMIT.EXTRA, "engines/recipe-source.c"}},
        "host_cleanup": {"unsettled_commands": 0, "errors": []}}
    for name in ("selected", "old_admission_changed", "runtime_qualified", "rules_qualified",
                 "real_target_allocation", "locality_proof", "strength_claim"):
        value[name] = False
    kinds = ["compiler-version"]
    for label in ADMIT.PLANS:
        kinds += [label + "-semantic-" + action + "-" + mode
                  for mode in ("plain", "ubsan") for action in ("compile", "run")]
        kinds += [label + "-preprocess", label + "-entry"]
        kinds += [label + "-source-gate-" + trial for trial in ("baseline", "typedefs", "batch-alpha")]
        kinds += [label + "-native-" + str(index) for index in range(2)]
        kinds += [label + "-fixture-" + action + "-" + mode
                  for mode in ("valid", "quit", "eof") for action in ("compile", "run")]
    value["commands"] = [command(kind, index + 1) for index, kind in enumerate(kinds)]
    return value


class SearchAdmissionBoundaries(unittest.TestCase):
    def test_owner_and_runtime_maps_are_not_search_tokens(self):
        with self.assertRaisesRegex(ValueError, "fresh explicit search"):
            ADMIT.SearchAdmission(None, {}, {}, {}, {}, b"", b"")
        with self.assertRaisesRegex(ValueError, "explicit completed structural"):
            ADMIT.input_names({"kind": "rove4k.D-process-owner-source.v1"}, ())

    def test_recipe_derived_inputs_reject_unknown_and_missing_sources(self):
        value = record(); producer = ("engines/recipe-source.c",)
        self.assertEqual(set(ADMIT.input_names(value, producer)), set(value["inputs"]))
        for name in (".env", "inventory.json", "engines/extra-tool.py"):
            bad = record(); bad["inputs"][name] = {}
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "recipe-derived"):
                ADMIT.input_names(bad, producer)
        del value["inputs"][ADMIT.EXTRA[0]]
        with self.assertRaisesRegex(ValueError, "recipe-derived"):
            ADMIT.input_names(value, producer)

    def test_selected_or_target_qualified_reports_never_become_generation_authority(self):
        for key in ("selected", "runtime_qualified", "real_target_allocation", "strength_claim"):
            value = record(); value[key] = True
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "unqualified and unselected"):
                ADMIT.input_names(value, ("engines/recipe-source.c",))

    def test_original_command_roles_order_and_lifetimes_are_exact(self):
        value = record(); producer = ("engines/recipe-source.c",)
        self.assertEqual(len(ADMIT.command_scopes(value, producer)), 1 + len(ADMIT.PLANS) * 17)
        for change in ("missing", "duplicate", "order", "nonzero", "forced", "remaining", "pid"):
            bad = record()
            if change == "missing": bad["commands"].pop()
            elif change == "duplicate": bad["commands"][-1] = dict(bad["commands"][-2])
            elif change == "order": bad["commands"][1:3] = reversed(bad["commands"][1:3])
            elif change == "nonzero": bad["commands"][0]["returncode"] = 7
            elif change == "forced": bad["commands"][0]["forced_cleanup"] = True
            elif change == "remaining": bad["commands"][0]["other_group_members_before_reap"] = [2]
            else: bad["commands"][0]["pgid"] += 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                ADMIT.command_scopes(bad, producer)

    def test_finite_product_names_cannot_request_external_paths(self):
        names = ADMIT.evidence_names(record(), ("engines/recipe-source.c",))
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in names))
        self.assertIn(ADMIT.SELECTOR + "/gate-2/linked", names)
        self.assertIn(ADMIT.SELECTOR + "/fixture-eof/dialogue.json", names)

    def test_fresh_callbacks_are_mandatory_and_receipt_class_cannot_be_changed(self):
        with self.assertRaisesRegex(ValueError, "callbacks are required"):
            ADMIT.admit_search({}, {}, {}, {}, current_inputs={}, admission_source={}, evidence_root="/owned",
                preprocess=None, compile_identity=None, storage_evidence=None)
        with self.assertRaisesRegex(ValueError, "receipt identity differs"):
            ADMIT.admit_search({}, {}, {}, {}, current_inputs={}, admission_source={}, evidence_root="/owned",
                preprocess=lambda *a: None, compile_identity=lambda *a: None,
                semantic_callback=lambda *a: None, storage_evidence=None)

    def test_fresh_source_and_output_paths_cannot_be_reused(self):
        row = command("fresh"); row.update(stdout={"path": "/owned/stdout"}, stderr={"path": "/owned/stderr"})
        used = set(); ADMIT._fresh_paths(row, ["/owned/main.c", "/owned/linked"], used)
        with self.assertRaisesRegex(ValueError, "reused"):
            ADMIT._fresh_paths(row, ["/owned/new.c", "/owned/new-linked"], used)

    def test_fresh_preprocess_receipt_records_json_pins_after_exact_byte_checks(self):
        files = {name: ("source " + name).encode() for name in ADMIT.NATIVE}
        flags, directory, label = ["-Os"], "/owned/new-preprocess", "control"
        driver = b"".join(('#include "' + name + '"\n').encode() for name in ADMIT.MEMBERS)
        outputs = {"main.c": b"actual preprocessed main", "start.S": b"actual preprocessed entry"}
        rows = [command("main", 1), command("entry", 2)]
        for index, (name, row) in enumerate(zip(outputs, rows)):
            row.update(cwd=directory, stdout={"path": "/owned/stdout-" + str(index), **ADMIT.pin(outputs[name])},
                stderr={"path": "/owned/stderr-" + str(index), **ADMIT.pin(b"")})
        rows[0]["command"] = ["cc", "-E", "-P", *flags, "-I", directory, "-x", "c", "-"]
        rows[1]["command"] = ["cc", "-E", "-P", "-x", "assembler-with-cpp", directory + "/start.S"]
        actual = {"kind": "D-search-preprocess-v1", "label": label, "input_pins": ADMIT.inventory(files),
            "flags": flags, "members": list(ADMIT.MEMBERS), "driver": driver, "readable_dir": directory,
            "commands": rows, "outputs": outputs}
        observed, receipt = ADMIT.fresh_preprocess(actual, files, flags, label, set())
        self.assertEqual(observed, outputs)
        self.assertEqual(receipt["driver"], ADMIT.pin(driver))
        self.assertEqual(receipt["outputs"], ADMIT.inventory(outputs))
        self.assertEqual(json.loads(json.dumps(receipt)), receipt)
        for changed in ("driver", "output"):
            wrong = deepcopy(actual)
            if changed == "driver": wrong["driver"] += b"different"
            else: wrong["outputs"]["main.c"] += b"different"
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                ADMIT.fresh_preprocess(wrong, files, flags, label, set())

    def test_approved_storage_raw_receipt_is_required(self):
        with self.assertRaisesRegex(ValueError, "approved actual storage receipt"):
            ADMIT._storage({"raw": b"{}", "root": "/owned", "products": {}}, {}, {})
        with self.assertRaisesRegex(ValueError, "before evidence name discovery"):
            ADMIT.storage_evidence_names({"cases": [{"name": "../../foreign"}]})

    def test_path_sensitive_semantic_images_are_independently_pinned(self):
        archived_binary = b"ELF fixture includes /archive/driver.c"
        fresh_binary = b"ELF fixture includes /new-owned/driver.c"
        output, normalized, summary = b"actual observations\n", b"same normalized\n", {"runs": 1486}
        old = {"binary": ADMIT.pin(archived_binary), "output": ADMIT.pin(output),
               "normalized": ADMIT.pin(normalized), "summary": summary}
        fresh = {"binary": fresh_binary, "output": output, "execute": {"stdout": ADMIT.pin(output)}}
        evidence = ADMIT.semantic_observation(fresh, old, archived_binary, normalized, summary)
        self.assertEqual(evidence["binary"], ADMIT.pin(fresh_binary))
        self.assertEqual(evidence["archived_binary"], ADMIT.pin(archived_binary))
        self.assertFalse(evidence["binary_matches_archived"])
        for change in ("archived", "raw_output", "normalized", "summary", "pipe_pin"):
            altered = deepcopy(fresh); actual_archive, actual_normalized, actual_summary = archived_binary, normalized, summary
            if change == "archived": actual_archive += b"changed"
            elif change == "raw_output": altered["output"] += b"changed"
            elif change == "normalized": actual_normalized += b"changed"
            elif change == "summary": actual_summary = {"runs": 1}
            else: altered["execute"]["stdout"] = ADMIT.pin(b"other output")
            with self.subTest(change=change), self.assertRaises(ValueError):
                ADMIT.semantic_observation(altered, old, actual_archive, actual_normalized, actual_summary)

    def test_executing_admission_source_is_bound(self):
        source = PATH.read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(ADMIT.executing_source(source), source)
        with self.assertRaisesRegex(ValueError, "executing module"):
            ADMIT.executing_source(source.replace(b'KIND = "rove4k.D-search-source.v1"', b'KIND = "foreign"'))

    def test_frozen_module_functions_cannot_disappear_or_be_replaced(self):
        source = b"def transform(value):\n    return value + 1\nclass Box:\n    pass\nvalues = [i for i in range(2)]\n"
        path = "/owned/engines/frozen.py"
        class Callable:
            def __call__(self, value): return value + 1
        for replacement in ("missing", "callable", "counterfeit_code", "foreign_function"):
            module = types.ModuleType("frozen_test")
            exec(compile(source, path, "exec", dont_inherit=True), module.__dict__)
            ADMIT._function_inputs(module, source, path)
            original = module.transform
            if replacement == "missing": del module.transform
            elif replacement == "callable": module.transform = Callable()
            elif replacement == "counterfeit_code": module.transform = types.SimpleNamespace(__code__=original.__code__)
            else: module.transform = lambda value: value + 1
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, "compiled frozen module"):
                ADMIT._function_inputs(module, source, path)

    def test_token_accessors_are_copies_and_do_not_grant_runtime_or_size(self):
        linked, native = b"fixture linked", b"fixture native"
        identity = {"linked": ADMIT.pin(linked), "stripped": ADMIT.pin(native)}
        metadata = {"kind": ADMIT.KIND, "selector": ADMIT.SELECTOR, "input_pins": {"x": ADMIT.pin(b"x")},
            "packages": [], "identifier_composition": {}, "fresh_commands": [], "runtime_qualified": False, "size_qualified": False}
        with patch.object(ADMIT, "IDENTITY", identity):
            token = ADMIT.SearchAdmission(ADMIT._TOKEN, metadata, {"board.c": b"board"}, {"main.c": b"main"},
                {"packed-xz-bcj": b"whole"}, native, linked)
            token.assert_valid(); token.to_record()["size_qualified"] = True
            token.readable["board.c"] = b"changed"; token.input_pins.clear()
            self.assertEqual(token.readable, {"board.c": b"board"})
            self.assertFalse(token.to_record()["size_qualified"])
            self.assertEqual(token.package_bytes("packed-xz-bcj"), b"whole")
            self.assertTrue(token.input_pins)


if __name__ == "__main__":
    unittest.main()
