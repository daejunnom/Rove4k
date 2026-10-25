"""Pure boundary regressions; no fabricated positive SearchAdmission token."""
from copy import deepcopy
import json
import lzma
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


ADMIT = load("D_alpha_admission_properties", HERE / "proper_alpha_admission.py")
LEXICAL = load("D_alpha_admission_lexical", ROOT / "engines/scripts/rename_c.py")
CLEANUP = load("D_alpha_admission_cleanup", HERE / "closed_tu_cleanup.py")
PARENT = load("D_alpha_admission_parent", HERE / "search_admission.py")
SHARED = load("D_alpha_admission_rules", ROOT / ADMIT.RULES)
ALPHA = load("D_alpha_admission_alpha", HERE / "proper_alpha.py")


def ordinary_bundle(files=None, flags=None, units=None):
    files = {"main.c": b"int main(void){return 0;}"} if files is None else files
    flags = ["-std=c11"] if flags is None else flags
    units = ["main.c"] if units is None else units
    bundle = {"files": {n: b.decode() for n, b in sorted(files.items())}, "flags": flags, "units": units}
    return files, flags, units, bundle


def synthetic_package(*, compressed=False):
    files, flags, units, bundle = ordinary_bundle()
    decoded = ("import os\nbundle=" + repr(bundle) + "\n").encode() if compressed else json.dumps(bundle).encode()
    header = b"#!/bin/sh\nexec python3 -c 'synthetic-unit-boundary'\n"
    whole = header + lzma.compress(decoded, format=lzma.FORMAT_ALONE)
    detail = {"header_bytes": len(header), "cleanup": "all filesystem inputs and native removed before fdexec"}
    if compressed:
        detail.update(kind="D-compressed-source-bootstrap-v1", cleanup="original all-paths-removed-before-fdexec suffix unchanged")
    return whole, detail, files, flags, units


class AlphaAdmissionBoundaries(unittest.TestCase):
    def test_JSON_and_foreign_parent_cannot_reach_any_compile(self):
        calls = []
        for parent in ({"kind": ADMIT.PARENT_KIND}, object(), None):
            with self.assertRaises(ValueError):
                ADMIT.admit_alpha(parent, parent_module=PARENT, parent_source={}, admission_source={},
                    helper_sources={}, frozen_inputs={}, current_inputs={}, modules={},
                    compile_identity=lambda *args: calls.append(args), reserved_paths=["/archive"])
        self.assertEqual(calls, [])
        with self.assertRaises(ValueError):
            ADMIT.AlphaAdmission(object(), {}, object(), PARENT, {}, {}, {}, CLEANUP)

    def test_runtime_and_rules_reject_serialized_generation_flags(self):
        fake = {"kind": ADMIT.KIND, "source_admitted": True, "native_admitted": True}
        with self.assertRaises(ValueError):
            ADMIT.carrier(fake, "source-jit", runtime=object(), frozen_inputs={})
        with self.assertRaises(ValueError):
            ADMIT.render_rules(fake, [], parent_module=PARENT, search_runtime=object(),
                preprocess_board=lambda *args: self.fail("must not preprocess"), shared=SHARED,
                minifier=object(), lexical=LEXICAL)

    def test_current_frozen_pair_and_executing_module_identity(self):
        raw = (HERE / "proper_alpha_admission.py").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(ADMIT.source_pair({"current": raw, "frozen": raw}, ADMIT, executing=True), raw)
        with self.assertRaises(ValueError):
            ADMIT.source_pair({"current": raw + b"\n", "frozen": raw}, ADMIT, executing=True)
        with self.assertRaises(ValueError):
            ADMIT.source_pair({"current": b"KIND='foreign'", "frozen": b"KIND='foreign'"}, ADMIT, executing=True)
        with self.assertRaises(ValueError):
            ADMIT.source_pair({"current": raw, "frozen": raw, "ignored": True}, ADMIT, executing=True)

    def test_helper_function_and_exact_source_authentication(self):
        raw = (HERE / "proper_alpha.py").read_bytes().replace(b"\r\n", b"\n")
        pair = {"current": raw, "frozen": raw}
        self.assertEqual(ADMIT.source_pair(pair, ALPHA, expected=ADMIT.HELPER_PINS[ADMIT.ALPHA],
            verifier=PARENT._function_inputs), raw)
        with patch.object(ALPHA, "transform", lambda *args: {}):
            with self.assertRaises(ValueError):
                ADMIT.source_pair(pair, ALPHA, expected=ADMIT.HELPER_PINS[ADMIT.ALPHA], verifier=PARENT._function_inputs)
        with self.assertRaises(ValueError):
            ADMIT.source_pair(pair, ALPHA, expected=ADMIT.HELPER_PINS[ADMIT.CLEANUP], verifier=PARENT._function_inputs)

    def test_relative_sources_refuse_secrets_heavy_names_and_escapes(self):
        self.assertEqual(ADMIT.relative("engines/scripts/build.py"), "engines/scripts/build.py")
        for name in ("/engine.c", "../engine.c", "engines/../engine.c", "engines//engine.c",
            "engines/./engine.c", "engines\\engine.c", "C:/engine.c", "engines/a\0.c",
            "inventory.json", "engines/.env", "engines/.env.release", "engines/node_modules/a.py",
            "engines/build/a.py", "engines/.aws/credentials", "package-lock.json"):
            with self.subTest(name=name), self.assertRaises(ValueError): ADMIT.relative(name)

    def test_absolute_evidence_path_is_canonical(self):
        self.assertEqual(ADMIT.absolute("/new/proof.c"), "/new/proof.c")
        for value in ("/", "relative", "/a/../b", "/a//b", "/a/./b", "/a\\b", "/a:b", None, True):
            with self.subTest(value=value), self.assertRaises(ValueError): ADMIT.absolute(value)

    def test_full_source_closure_is_parent_union_explicit_consumers(self):
        base = {"selection/build.json": b"{}", "engines/control.py": b"control"}
        parent = types.SimpleNamespace(input_pins=ADMIT.inventory(base))
        frozen = {**base, **{n: n.encode() for n in ADMIT.REQUIRED_EXTRA}}
        current = {n: b for n, b in frozen.items() if n.startswith("engines/")}
        self.assertEqual(ADMIT.full_source_closure(parent, frozen, current), ADMIT.inventory(frozen))
        for damaged in ({**frozen, "engines/unlisted.py": b"extra"}, {n: b for n, b in frozen.items() if n != ADMIT.SELF},
                        {**frozen, "engines/control.py": b"changed"}):
            with self.assertRaises(ValueError): ADMIT.full_source_closure(parent, damaged, current)
        with self.assertRaises(ValueError):
            ADMIT.full_source_closure(parent, frozen, {**current, "engines/unlisted.py": b"extra"})

    def test_archived_and_parent_fresh_paths_are_both_reserved(self):
        record = {"fresh_commands": [{"command": {"cwd": "/parent/fresh-1",
            "command": ["cc", "/parent/fresh-1/main.c", "-Wl,-T,/parent/fresh-1/image.ld"],
            "stdout": {"path": "/parent/tool.stdout"}, "stderr": {"path": "/parent/tool.stderr"}},
            "linked_path": "/parent/fresh-1/linked"}]}
        reserved = ADMIT.reservations(record, ["/archive", "/old-storage/result.json"])
        self.assertIn("/parent/fresh-1/image.ld", reserved)
        for path in ("/archive/new.c", "/parent/fresh-1/main.c", "/parent/tool.stdout", "/old-storage/result.json"):
            with self.subTest(path=path), self.assertRaises(ValueError): ADMIT.claim_paths([path], set(reserved))
        with self.assertRaises(ValueError): ADMIT.reservations(record, [])

    def test_fresh_callback_paths_are_distinct_and_not_reused(self):
        seen = {"/old"}
        paths = ["/fresh/compile", "/fresh/compile/main.c", "/fresh/compile/linked", "/fresh/stdout", "/fresh/stderr"]
        ADMIT.claim_paths(paths, seen)
        self.assertTrue(set(paths) <= seen)
        with self.assertRaises(ValueError): ADMIT.claim_paths(["/fresh/compile/again.c"], seen)
        with self.assertRaises(ValueError): ADMIT.claim_paths(["/fresh"], seen)
        with self.assertRaises(ValueError): ADMIT.claim_paths(["/brandnew/out", "/brandnew/out"], set())

    def test_ordinary_and_compressed_source_payloads_have_complete_inverses(self):
        for compressed, route in ((False, "source-jit"), (True, "source-jit-compressed")):
            with self.subTest(route=route):
                whole, detail, files, flags, units = synthetic_package(compressed=compressed)
                inverse = ADMIT.package_inverse(whole, detail, files, flags, units, route)
                self.assertEqual(inverse["header"], ADMIT.pin(whole[:detail["header_bytes"]]))
                with self.assertRaises(ValueError): ADMIT.package_inverse(whole + b"tail", detail, files, flags, units, route)
                with self.assertRaises((ValueError, lzma.LZMAError)):
                    ADMIT.package_inverse(whole[:-5], detail, files, flags, units, route)
                with self.assertRaises(ValueError): ADMIT.package_inverse(whole, detail, {"main.c": b"foreign"}, flags, units, route)
                with self.assertRaises(ValueError): ADMIT.package_inverse(whole, detail, files, flags + ["-DOTHER"], units, route)
                with self.assertRaises(ValueError): ADMIT.package_inverse(whole, detail, files, flags, ["different.c"], route)

    def test_foreign_route_or_bootstrap_cleanup_cannot_be_relabelled(self):
        whole, detail, files, flags, units = synthetic_package()
        for route in ("packed-xz-bcj", "source", "test-p28", None):
            with self.assertRaises(ValueError): ADMIT.package_inverse(whole, detail, files, flags, units, route)
        for replacement in (True, 0, len(whole)):
            with self.assertRaises(ValueError):
                ADMIT.package_inverse(whole, {**detail, "header_bytes": replacement}, files, flags, units, "source-jit")
        with self.assertRaises(ValueError):
            ADMIT.package_inverse(whole, {**detail, "cleanup": "leave-temp"}, files, flags, units, "source-jit")

    def test_source_runtime_expected_image_is_linked_and_not_stripped(self):
        linked, stripped, whole = b"full-linked-image", b"stripped", b"header-payload"
        expected = ADMIT.runtime_expected(linked, whole, 6)
        self.assertEqual(expected["native_bytes"], len(linked))
        self.assertEqual(expected["native_sha256"], ADMIT.pin(linked)["sha256"])
        self.assertNotEqual(expected["native_sha256"], ADMIT.pin(stripped)["sha256"])
        self.assertEqual(expected["payload_bytes"], len(whole) - 6)
        with self.assertRaises(ValueError): ADMIT.runtime_expected(linked, whole, True)

    def test_composition_uses_the_admitted_full_map_without_a_second_rename(self):
        first = {"Board": "y", "Move": "H", "start": "start", "make": "make"}
        second = {"start": "bx", "make": "aR", "count": "I"}
        result = ADMIT.compose_identifiers(first, second)
        self.assertEqual(result["Board"], "y")
        self.assertEqual(result["Move"], "H")
        self.assertEqual(result["start"], "bx")
        self.assertEqual(result["make"], "aR")
        self.assertEqual(result["count"], "I")

    def test_actual_board_prefix_cleanup_then_full_alpha_map(self):
        original = b"DEAD;typedef int y;void start(void){}"
        cleanup = types.SimpleNamespace(SPANS=((0, 5, "dead declaration"),), _project=CLEANUP._project, _restore=CLEANUP._restore)
        expected = b"typedef int y;void bx(void){}"
        shipping = {"main.c": expected + b"int main(void){return 0;}"}
        actual, proof = ADMIT.project_board_prefix(original, shipping, cleanup, {"start": "bx", "unusedName": "zz"}, LEXICAL)
        self.assertEqual(actual, expected)
        self.assertEqual(proof["alpha_map"], {"start": "bx", "unusedName": "zz"})
        self.assertEqual(CLEANUP._restore(b"typedef int y;void start(void){}", proof["cleanup"]), original)
        with self.assertRaises(ValueError): ADMIT.project_board_prefix(original, {"main.c": b"foreign"}, cleanup, {"start": "bx"}, LEXICAL)
        crossing = types.SimpleNamespace(SPANS=((0, len(original) + 1, "crossing"),), _project=CLEANUP._project)
        with self.assertRaises(ValueError): ADMIT.project_board_prefix(original, shipping, crossing, {"start": "bx"}, LEXICAL)

    def test_fixture_namespace_preserves_member_fields_and_quoted_bytes(self):
        binding = {"board": "y", "start": "bx", "generate": "bV", "make": "aR", "four_args": False}
        driver = b'static int rv_rule_legal(const y *p,unsigned *out){unsigned m=0;char *s=0;return p->s+m+!!s+!!out;}\n'
        rendered, mapping = ADMIT.namespace_fixture(driver, b"typedef struct{int s;}y;", binding, LEXICAL)
        self.assertIn(b"p->s".replace(b"p", b"rv_alpha_rule_var_p"), rendered)
        self.assertIn(b"rv_alpha_rule_var_s", rendered)
        self.assertIn(b"rv_alpha_rule_legal", rendered)
        self.assertEqual(mapping["m"], "rv_alpha_rule_var_m")
        quoted = b'char *text="m s p rv_rule_legal";'
        result, _ = ADMIT.namespace_fixture(quoted, b"", binding, LEXICAL)
        self.assertIn(b'"m s p rv_rule_legal"', result)

    def test_real_shared_fixture_template_can_be_namespaced_without_new_tokens(self):
        binding = {"board": "y", "start": "bx", "generate": "bV", "make": "aR", "four_args": False}
        board = b"typedef struct{int s;}y;"
        cases = [{"moves": ["e2e4", "e7e5"]}, {"moves": []}]
        raw = SHARED.render_bound_fixture(board, binding, cases)
        prefix = b"#define main rv_rule_original_main\n"
        driver = raw[len(prefix) + len(board):]
        result, mapping = ADMIT.namespace_fixture(driver, board, binding, LEXICAL)
        self.assertIn(b"rv_alpha_rule_play", result)
        self.assertIn(b"rv_alpha_rule_var_row", result)
        self.assertIn(b'"e2e4 e7e5"', result)
        self.assertEqual(mapping["paths"], "rv_alpha_rule_var_paths")

    def test_fixture_capture_and_unreviewed_names_are_rejected_before_compile(self):
        binding = {"board": "y", "start": "bx", "generate": "bV", "make": "aR", "four_args": False}
        driver = b"unsigned m=0;"
        with self.assertRaises(ValueError):
            ADMIT.namespace_fixture(driver, b"int rv_alpha_rule_var_m;", binding, LEXICAL)
        with self.assertRaises(ValueError):
            ADMIT.namespace_fixture(driver, b"", {**binding, "make": "moves"}, LEXICAL)
        with self.assertRaises(ValueError):
            ADMIT.namespace_fixture(b"int unknownIdentifier;", b"", binding, LEXICAL)

    def test_policy_and_boolean_types_are_not_normalized_into_acceptance(self):
        self.assertFalse(ADMIT.equal({"selected": False}, {"selected": 0}))
        self.assertFalse(ADMIT.equal({"workers": 4}, {"workers": 4.0}))
        self.assertTrue(set(ADMIT.ROUTES) == {"source-jit", "source-jit-compressed"})
        self.assertNotIn("packed-xz-bcj", ADMIT.ROUTES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
