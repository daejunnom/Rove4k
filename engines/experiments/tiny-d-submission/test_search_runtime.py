"""Search carrier consumer tests; synthetic admission is no native authority."""
from copy import deepcopy
import importlib.util
import json
import lzma
from pathlib import Path
import sys
import types
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BRIDGE = load("search_runtime_tests_target", HERE / "search_runtime.py")
RUNTIME = load("search_runtime_tests_generic", ROOT / "engines/experiments/tcec-next/profile_verify.py")
LEXICAL = load("search_runtime_tests_lexical", ROOT / "engines/scripts/rename_c.py")
MINIFIER = load("search_runtime_tests_minifier", ROOT / "engines/scripts/minify.py")
AUTHORITY_SOURCE = b"pass\n"
AUTHORITY_PATH = "/fixture/search_admission.py"


class Packaging:
    """A real bounded inverse with inert synthetic bootstrap, never executed."""
    def package_native(self, native, codec):
        payload = lzma.compress(native, format=lzma.FORMAT_XZ,
            filters=[{"id": lzma.FILTER_X86}, {"id": lzma.FILTER_LZMA2, "preset": 1}])
        prefix = b"#!/bin/sh\nexec python3 -c "
        header = prefix + b"x" * (5261 - len(payload) - len(prefix) - 1) + b"\n"
        return header + payload, {"codec": codec, "cleanup": "memfd-CLOEXEC",
            "header_bytes": len(header), "payload_bytes": len(payload),
            "restoration": "complete kernel-executable ELF"}


class Token:
    """Trusted dependency stand-in to isolate this consumer's own checks."""
    def __init__(self):
        self.valid = True
        self._readable = {name: (name + "\n").encode() for name in BRIDGE.READABLE}
        self._shipping = {"main.c": b"void board(void){}void search(void){}", "start.S": b"entry", "image.ld": b"layout"}
        self._native, self._linked = b"N" * 7136, b"L" * 7488
        self._inputs = {"selection/build.json": b"{}", "engines/c/board.c": b"board"}
        self._composition = {"legacy": {}, "accepted_alpha": {}, "scalar_typedef_rounds": [], "composed": {}}
        self._fresh = []
        whole, detail = Packaging().package_native(self._native, "xz-bcj")
        self._whole = whole
        self._packages = [{"route": BRIDGE.ROUTE, "whole": BRIDGE.pin(whole), "detail": detail, "reproduced": True}]
        self.record = {"kind": BRIDGE.SOURCE_KIND, "selector": BRIDGE.SELECTOR, "options": list(BRIDGE.OPTIONS),
            "ownership_policy": BRIDGE.POLICY, "last_search_output_required": False,
            "input_contract": BRIDGE.INPUT_CONTRACT, "source_admitted": True, "native_admitted": True,
            "package_generation_admitted": True, "fresh_full_artifact_runtime": False,
            "rules_qualified": False, "physical_placement_qualified": False, "size_qualified": False,
            "selected": False, "profile": RUNTIME.contracts().resource_profile("test-p4").to_record(16),
            "flags": ["-Os"], "units": ["main.c", "start.S"],
            "identity": {"linked": BRIDGE.pin(self._linked), "stripped": BRIDGE.pin(self._native)},
            "admission_source": BRIDGE.pin(AUTHORITY_SOURCE)}

    def assert_valid(self):
        BRIDGE.require(self.valid, "typed source admission was invalidated")

    def to_record(self):
        return deepcopy(self.record)

    @property
    def readable(self): return deepcopy(self._readable)
    @property
    def shipping(self): return deepcopy(self._shipping)
    @property
    def native(self): return self._native
    @property
    def linked(self): return self._linked
    @property
    def input_pins(self): return BRIDGE.inventory(self._inputs)
    @property
    def packages(self): return deepcopy(self._packages)
    @property
    def identifier_composition(self): return deepcopy(self._composition)
    @property
    def fresh_commands(self): return deepcopy(self._fresh)
    def package_bytes(self, route):
        assert route == BRIDGE.ROUTE
        return self._whole


MODULE = types.SimpleNamespace(KIND=BRIDGE.SOURCE_KIND, SearchAdmission=Token,
    __file__=AUTHORITY_PATH, _EXECUTING_CODE=compile(AUTHORITY_SOURCE, AUTHORITY_PATH, "exec", dont_inherit=True))


def carrier(token, **changes):
    source = Path(BRIDGE.__file__).read_bytes().replace(b"\r\n", b"\n")
    arguments = dict(admission_module=MODULE, admission_source={"current": AUTHORITY_SOURCE, "frozen": AUTHORITY_SOURCE},
        bridge_source={"current": source, "frozen": source}, runtime=RUNTIME,
        packaging=Packaging(), frozen_inputs=deepcopy(token._inputs))
    arguments.update(changes)
    return BRIDGE.prepare_carrier(token, **arguments)


def board_token():
    token = Token()
    raw = (b"typedef int unused;typedef unsigned long size_t;extern size_t strlen(const char*);"
           b"extern int strcmp(const char*,const char*);extern char*strtok_r(char*,const char*,char**);"
           b"typedef struct{int x;}Board;void start(Board*p){p->x=0;}"
           b"void gen(Board*p){p->x++;}void make(Board*p){p->x--;}\n")
    compact = MINIFIER.compact_source(raw, "c").rstrip(b"\n")
    legacy = {"Board": "Y", "size_t": "F"}
    before = compact
    for old, new in legacy.items():
        before = LEXICAL._replace({"main.c": before}, old, new)["main.c"]
    declaration = b"typedef int unused;"
    assert before.startswith(declaration)
    after = before[len(declaration):]
    after = LEXICAL._replace({"main.c": after}, "start", "a")["main.c"]
    token._composition = {"legacy": legacy,
        "scalar_typedef_rounds": [[{"main.c": {"removed": [{"begin": 0, "end": len(declaration), "declaration": declaration.decode()}]}}]],
        "accepted_alpha": {"start": "a"}, "composed": {"Board": "Y", "size_t": "F", "start": "a"}}
    token._shipping["main.c"] = after + b"int search(void){return 0;}"
    return token, raw, after


def board_receipt(token, raw):
    directory = "/fresh/board"
    row = {"started": True, "terminal": True, "reaped": True, "owned_group_absent": True,
        "original_identity_retained_until_other_members_absent": True, "forced_cleanup": False,
        "other_group_members_before_reap": [], "returncode": 0, "pid": 17, "pgid": 17,
        "cwd": directory, "command": ["cc", "-E", "-P", *token.record["flags"], directory + "/board.c"],
        "stdout": {"path": "/fresh/tool.stdout", **BRIDGE.pin(raw)},
        "stderr": {"path": "/fresh/tool.stderr", **BRIDGE.pin(b"")}}
    return {"kind": "D-search-board-preprocess-v1", "label": "search-actual-board",
        "input_pins": BRIDGE.inventory(token.readable), "flags": list(token.record["flags"]),
        "readable_dir": directory, "output": raw, "command": row}


class SearchRuntimeBoundaries(unittest.TestCase):
    def test_carrier_preserves_immediate_exit_domain_and_size_block(self):
        token = Token()
        files, admitted = carrier(token)
        record = json.loads(files["build.json"])
        self.assertEqual((len(files["program"]), admitted.expected["native_bytes"]), (5261, 7136))
        self.assertFalse(record["size_qualified"])
        self.assertFalse(record["selected"])
        self.assertFalse(record["event_target_confirmed"])
        self.assertEqual(record["shutdown_scope"], BRIDGE.SCOPE)
        self.assertEqual(admitted.source_contract["kind"], BRIDGE.KIND)
        self.assertEqual(admitted.source_contract["ownership_policy"], BRIDGE.POLICY)
        self.assertFalse(admitted.source_contract["last_search_output_required"])
        self.assertFalse(admitted.source_contract["event_target_confirmed"])
        self.assertEqual(admitted.resources["tt_bytes"], 128 << 20)
        self.assertEqual(admitted.runtime_policy["startup_threads"], 5)
        self.assertEqual(admitted.wrapper_contract["entry_cleanup"], "loader-owned-fd")
        self.assertEqual(files["inputs/" + BRIDGE.ADMISSION], AUTHORITY_SOURCE)
        self.assertEqual(files["native/image"], token.native)
        token.record["options"].clear()
        token._shipping["main.c"] = b"changed"
        self.assertEqual(admitted.source_contract["options"], BRIDGE.OPTIONS)
        self.assertEqual(files["shipping-inputs/main.c"], b"void board(void){}void search(void){}")

    def test_native_map_owner_and_invalidated_source_are_rejected(self):
        token = Token()
        for value in ({"native": token.native}, types.SimpleNamespace(**token.__dict__)):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                BRIDGE.prepare_carrier(value, admission_module=MODULE, admission_source={}, bridge_source={},
                    runtime=RUNTIME, packaging=Packaging(), frozen_inputs={})
        for key, value in (("kind", "rove4k.D-process-owner-source.v1"),
                ("ownership_policy", "final-wait-equivalent-output"), ("last_search_output_required", True),
                ("input_contract", "malformed-lines"), ("options", ["previous-piece"]), ("selected", True)):
            altered = Token(); altered.record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                carrier(altered)
        token.valid = False
        with self.assertRaisesRegex(ValueError, "invalidated"):
            carrier(token)

    def test_frozen_helper_closure_and_native_changes_are_rejected(self):
        token = Token()
        for inputs in ({}, {**token._inputs, "extra.c": b"extra"}, {**token._inputs, "engines/c/board.c": b"changed"}):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                carrier(token, frozen_inputs=inputs)
        with self.assertRaisesRegex(ValueError, "current and frozen"):
            carrier(token, admission_source={"current": b"different", "frozen": AUTHORITY_SOURCE})
        with self.assertRaisesRegex(ValueError, "executing module"):
            carrier(token, admission_source={"current": b"x=1\n", "frozen": b"x=1\n"})
        token._native = b"X" * 7136
        with self.assertRaisesRegex(ValueError, "linked/native"):
            carrier(token)

    def test_full_packed_inverse_rejects_trailing_or_changed_payload(self):
        class BadPackaging(Packaging):
            def package_native(self, native, codec):
                whole, detail = super().package_native(native, codec)
                return whole[:-1] + b"x", detail
        with self.assertRaises(ValueError):
            carrier(Token(), packaging=BadPackaging())
        token = Token(); token._packages[0]["detail"]["cleanup"] = "unlink-original"
        with self.assertRaises(ValueError):
            carrier(token)

    def test_actual_board_prefix_applies_full_TU_deletions_before_alpha(self):
        token, raw, expected = board_token()
        self.assertEqual(BRIDGE.shipping_board(token, raw, admission_module=MODULE, minifier=MINIFIER,
            lexical=LEXICAL), expected)
        token._composition["scalar_typedef_rounds"][0][0]["main.c"]["removed"][0]["end"] += 1
        with self.assertRaisesRegex(ValueError, "deletion"):
            BRIDGE.shipping_board(token, raw, admission_module=MODULE, minifier=MINIFIER, lexical=LEXICAL)

    def test_actual_board_must_be_a_complete_shipping_prefix(self):
        token, raw, _ = board_token()
        token._shipping["main.c"] = b"unrelated"
        with self.assertRaisesRegex(ValueError, "shipping prefix"):
            BRIDGE.shipping_board(token, raw, admission_module=MODULE, minifier=MINIFIER, lexical=LEXICAL)

    def test_fresh_rules_uses_new_command_kind_and_original_libc_declarations(self):
        token, raw, expected = board_token()
        captured = []
        def render(board, names, cases, declarations):
            captured.append((board, names, cases, declarations)); return b"fixture"
        receipt = board_receipt(token, raw)
        fixture, report = BRIDGE.render_rules(token, ["case"], admission_module=MODULE,
            preprocess_board=lambda *args: receipt, shared=types.SimpleNamespace(render_bound_fixture=render),
            minifier=MINIFIER, lexical=LEXICAL)
        self.assertEqual(fixture, b"fixture")
        self.assertEqual(captured[0][:3], (expected, {"board": "Y", "start": "a", "generate": "gen", "make": "make", "four_args": False}, ["case"]))
        self.assertIn(b"typedef F size_t;", captured[0][3])
        self.assertFalse(report["TT_allocated"])
        self.assertFalse(report["native_entry_called"])
        self.assertFalse(report["last_search_output_required"])
        self.assertFalse(report["event_target_confirmed"])
        self.assertEqual(report["shutdown_scope"], BRIDGE.SCOPE)

    def test_reused_or_forged_board_preprocess_is_rejected(self):
        token, raw, _ = board_token()
        shared = types.SimpleNamespace(render_bound_fixture=lambda *args: b"fixture")
        for kind in ("owner-kind", "argv", "stdout", "forced", "reused", "input"):
            receipt = board_receipt(token, raw)
            token._fresh = []
            if kind == "owner-kind": receipt["kind"] = "D-owner-board-preprocess-v1"
            elif kind == "argv": receipt["command"]["command"][-1] = "/another/board.c"
            elif kind == "stdout": receipt["command"]["stdout"]["sha256"] = "0" * 64
            elif kind == "forced": receipt["command"]["forced_cleanup"] = True
            elif kind == "input": receipt["input_pins"].pop("tiny.h")
            else: token._fresh = [{"commands": [{"cwd": "/fresh/board"}]}]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                BRIDGE.render_rules(token, [], admission_module=MODULE, preprocess_board=lambda *args: receipt,
                    shared=shared, minifier=MINIFIER, lexical=LEXICAL)

    def test_prior_preprocess_and_semantic_files_cannot_be_new_pipe_paths(self):
        token, raw, _ = board_token()
        shared = types.SimpleNamespace(render_bound_fixture=lambda *args: b"fixture")
        token._fresh = [{"input_pins": {"driver.c": BRIDGE.pin(b"driver"), "tiny.h": BRIDGE.pin(b"header")},
            "commands": [{"cwd": "/old/semantic", "command": ["cc", "/old/semantic/driver.c", "-o", "/old/semantic/x"]},
                         {"cwd": "/old/semantic", "command": ["/old/semantic/x"]}]}]
        for name in ("driver.c", "tiny.h", "x"):
            receipt = board_receipt(token, raw)
            receipt["command"]["stdout"]["path"] = "/old/semantic/" + name
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "reused"):
                BRIDGE.render_rules(token, [], admission_module=MODULE, preprocess_board=lambda *args: receipt,
                    shared=shared, minifier=MINIFIER, lexical=LEXICAL)


if __name__ == "__main__":
    unittest.main()
