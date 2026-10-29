"""Pure consumer boundaries for the explicit no-TID qualification class.

No admitted token, native image or successful runtime receipt is fabricated.
Positive component checks are not generation or engine authority; the full
positive path belongs to the explicit frozen qualification CLI.
"""
import ast
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = "engines/experiments/tiny-d-submission/"
READER = "engines/scripts/production_input.py"
COMPOSER = "engines/scripts/source_composition.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_bytes(module):
    data = Path(module.__file__).read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in a named test input")
    return data


def authority_source(module):
    data = source_bytes(module)
    return {"current": data, "frozen": data}


def selected_readable():
    """Rebuild only actual source text; no PP, compiler, binary or allocation."""
    logical = {"source": "source", "storage": "storage", "startup": "test_startup",
               "publication": "publication", "owner": "process_owner", "arity": "syscall_arity",
               "valid": "valid_input", "search": "search_compact"}
    modules = {role: load("D_no_tid_test_source_" + role, HERE / (name + ".py"))
               for role, name in logical.items()}
    source, startup = modules["source"], modules["startup"]
    profile = source.production().resource_profile("test-p4")
    files, _ = startup.prepared(source, profile, True, modules["storage"], "prefix")
    files, owner_proof = modules["owner"].transform(files, modules["publication"])
    files, arity_proof = modules["arity"].transform(files, modules["owner"], modules["publication"],
        owner_proof, noinline_wake=True, immediate_exit=True)
    files, valid_proof = modules["valid"].transform(files, modules["arity"], modules["owner"],
        modules["publication"], arity_proof, mode="one-byte-valid")
    files, _ = modules["search"].transform(files, modules["valid"], modules["arity"], modules["owner"],
        modules["publication"], valid_proof, options=("previous-piece", "unsigned-history"))
    return files


class NoTidAuthorityComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admission = load("D_no_tid_authority_component_tests", HERE / "no_tid_admission.py")
        cls.parent_module = load("D_no_tid_real_parent_component_tests", HERE / "search_admission.py")

    @staticmethod
    def profile():
        # The qualification requirement is independent of dataclass equality:
        # Python bools compare equal to 0/1 but are not accepted resource counts.
        return {"id": "test-p4", "purpose": "test", "workers": 4, "control_threads": 1,
                "os_threads": 5, "tt_bits": 23, "tt_entry_bytes": 16,
                "tt_entries": 1 << 23, "tt_mask": (1 << 23) - 1, "tt_bytes": 128 << 20,
                "tt_cap_bytes": 128 << 20, "parallel_init": True,
                "init_partition_requires_page_aligned_base": True,
                "initialization_in_startup": True, "event_allocation_confirmed": None}

    def test_profile_is_the_typed_fixed_resource_contract_and_returns_a_copy(self):
        a = self.admission
        original = self.profile()
        observed = a.validate_profile(original)
        self.assertEqual(observed, original)
        observed["workers"] = 256
        self.assertEqual(original["workers"], 4)
        for field in ("workers", "control_threads", "os_threads", "tt_bits", "tt_entry_bytes",
                      "tt_entries", "tt_mask", "tt_bytes", "tt_cap_bytes"):
            for replacement in (True, False, float(original[field]), str(original[field])):
                bad = self.profile(); bad[field] = replacement
                with self.subTest(field=field, value=replacement), self.assertRaises(ValueError):
                    a.validate_profile(bad)
        for field in ("parallel_init", "init_partition_requires_page_aligned_base", "initialization_in_startup"):
            for replacement in (False, 1, None):
                bad = self.profile(); bad[field] = replacement
                with self.subTest(field=field, value=replacement), self.assertRaises(ValueError):
                    a.validate_profile(bad)
        for replacement in (False, True, 0):
            bad = self.profile(); bad["event_allocation_confirmed"] = replacement
            with self.subTest(event=replacement), self.assertRaises(ValueError):
                a.validate_profile(bad)

    def test_executing_source_requires_both_current_and_frozen_actual_code(self):
        a = self.admission
        actual = authority_source(a)
        self.assertEqual(a._source(a, actual, a.SELF), actual["frozen"])
        self.assertEqual(a._source(self.parent_module, authority_source(self.parent_module), a.PARENT_ADMISSION),
                         source_bytes(self.parent_module))
        changed = actual["frozen"] + b"\nFOREIGN_AUTHORITY_BINDING = 1\n"
        for sources in ({"current": changed, "frozen": actual["frozen"]},
                        {"current": changed, "frozen": changed}):
            with self.subTest(same_bytes=sources["current"] == sources["frozen"]), self.assertRaises(ValueError):
                a._source(a, sources, a.SELF)
        with self.assertRaises(ValueError):
            a._source(a, actual, a.PARENT_ADMISSION)

    def test_same_code_function_with_foreign_globals_is_not_executing_authority(self):
        a = self.admission
        raw = authority_source(a)
        original = a.validate_profile
        foreign_globals = dict(a.__dict__)
        foreign_globals["require"] = lambda *args: None
        counterfeit = types.FunctionType(original.__code__, foreign_globals, original.__name__)
        self.assertEqual(counterfeit.__code__, original.__code__)
        self.assertIsNot(counterfeit.__globals__, a.__dict__)
        with patch.object(a, "validate_profile", counterfeit):
            with self.assertRaises(ValueError):
                a._source(a, raw, a.SELF)

    def test_same_code_method_with_foreign_globals_is_not_typed_authority(self):
        a = self.admission
        raw = authority_source(a)
        original = a.NoTidAdmission.to_record
        counterfeit = types.FunctionType(original.__code__, dict(a.__dict__), original.__name__)
        with patch.object(a.NoTidAdmission, "to_record", counterfeit):
            with self.assertRaises(ValueError):
                a._source(a, raw, a.SELF)

    def test_namespace_proxy_cannot_claim_the_registered_executing_frame(self):
        a = self.admission
        proxy = types.SimpleNamespace(**a.__dict__)
        with patch.dict(sys.modules, {a.__name__: proxy}):
            with self.assertRaises(ValueError):
                a._source(proxy, authority_source(a), a.SELF)

    def test_private_constructor_does_not_accept_old_or_foreign_nonces(self):
        a = self.admission
        for nonce in (None, object(), self.parent_module._TOKEN):
            with self.subTest(nonce=type(nonce).__name__), self.assertRaises(ValueError):
                a.NoTidAdmission(nonce, {}, None, self.parent_module, {}, {}, {}, b"", b"")

    def test_real_parent_class_is_required_before_any_parent_record_is_consumed(self):
        a, parent = self.admission, self.parent_module
        class Lookalike:
            def assert_valid(self):
                raise AssertionError("untrusted parent method was invoked")
            def to_record(self):
                raise AssertionError("untrusted parent record was consumed")
        class ParentSubclass(parent.SearchAdmission):
            pass
        for value in ({"kind": parent.KIND}, Lookalike(), object.__new__(ParentSubclass)):
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                a.validate_parent(value, parent, authority_source(parent))

    def test_rebinding_canonical_authority_to_an_inheriting_class_is_rejected(self):
        a = self.admission
        for module, name, logical in ((a, "NoTidAdmission", a.SELF),
                                     (self.parent_module, "SearchAdmission", a.PARENT_ADMISSION)):
            original = getattr(module, name)
            raw = authority_source(module)
            class Replacement(original):
                def __getattribute__(self, attribute):
                    raise AssertionError("inherited counterfeit authority was invoked")
            Replacement.__module__ = module.__name__
            Replacement.__name__ = name
            Replacement.__qualname__ = name
            with self.subTest(authority=name), patch.object(module, name, Replacement):
                with self.assertRaises(ValueError):
                    a._source(module, raw, logical)
                if module is self.parent_module:
                    with self.assertRaises(ValueError):
                        a.validate_parent(object.__new__(Replacement), module, raw)

    def test_unminted_parent_instance_cannot_shadow_the_authoritative_validator(self):
        a, parent = self.admission, self.parent_module
        unminted = object.__new__(parent.SearchAdmission)
        object.__setattr__(unminted, "_valid", object())
        def tripwire():
            raise AssertionError("instance shadow ran before the authenticated class validator")
        object.__setattr__(unminted, "assert_valid", tripwire)
        with self.assertRaises(ValueError):
            a.validate_parent(unminted, parent, authority_source(parent))

    def test_recipe_closure_keeps_reader_composer_and_new_startup_transform(self):
        a, parent = self.admission, self.parent_module
        producer = ("engines/compact/tiny-entry-d/native/runtime.c", COMPOSER)
        base = set(producer) | set(parent.EXTRA) | {"selection/build.json"}
        record = {"inputs": {name: a.pin(b"component source") for name in base},
                  "tools": {name: a.pin(b"component tool") for name in (a.CHANGE, a.COST_DRIVER, READER)}}
        self.assertEqual(set(a.input_names(record, producer)), base | set(record["tools"]))
        for missing in (READER, a.CHANGE):
            bad = deepcopy(record); del bad["tools"][missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                a.input_names(bad, producer)
        # Even a self-consistent recipe/input omission cannot erase the
        # independently required composer dependency.
        bad = deepcopy(record); del bad["inputs"][COMPOSER]
        with self.assertRaises(ValueError):
            a.input_names(bad, tuple(n for n in producer if n != COMPOSER))
        bad = deepcopy(record); bad["inputs"]["engines/unconsumed.c"] = a.pin(b"extra")
        with self.assertRaises(ValueError):
            a.input_names(bad, producer)

    def test_new_unminted_class_cannot_enter_the_old_search_carrier(self):
        a = self.admission
        old_bridge = load("D_no_tid_wrong_old_carrier_test", HERE / "search_runtime.py")
        unminted = object.__new__(a.NoTidAdmission)
        # The exact-class rejection precedes properties, packaging or runtime;
        # no synthetic successful admission is constructed for this test.
        with self.assertRaises(ValueError):
            old_bridge.prepare_carrier(unminted, admission_module=self.parent_module,
                admission_source={}, bridge_source={}, runtime=None, packaging=None, frozen_inputs={})

    def test_fresh_paths_reserve_parent_preprocess_semantic_archive_and_linker_names(self):
        a = self.admission
        earlier = {"fresh_commands": [
            {"commands": [{"cwd": "/parent/cpp", "command": ["cc", "/parent/cpp/main.c"],
                            "stdout": {"path": "/parent/cpp.stdout"}, "stderr": {"path": "/parent/cpp.stderr"}}]},
            {"source_paths": {"driver.c": "/parent/semantic/driver.c"},
             "binary_path": "/parent/semantic/x"},
            {"command": {"command": ["cc", "-Wl,-T,/parent/shipping/image.ld", "-o", "/parent/linked"]}},
        ]}
        archived = ["/archive/no-tid/gate-0/main.c", "/archive/no-tid/native-0/linked"]
        reserved = a.used_paths(earlier, archived)
        expected = {"/parent/cpp", "/parent/cpp/main.c", "/parent/cpp.stdout", "/parent/cpp.stderr",
                    "/parent/semantic/driver.c", "/parent/semantic/x", "/parent/shipping/image.ld",
                    "/parent/linked", *archived}
        self.assertEqual(reserved, expected)
        self.assertNotIn("-Wl,-T,/parent/shipping/image.ld", reserved)
        self.assertFalse(reserved.intersection({"/fresh/main.c", "/fresh/image.ld", "/fresh/stdout"}))


class NoTidStartupConsumer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = load("D_no_tid_three_argument_consumer_tests", HERE / "no_tid_runtime.py")
        cls.change = load("D_no_tid_source_change_component_tests", HERE / "no_tid_startup.py")
        cls.control = selected_readable()
        cls.candidate, cls.proof = cls.change.transform(cls.control, nonreturning=False)
        cls.tail, _ = cls.change.transform(cls.control, nonreturning=True)

    def test_source_rebuild_and_consumer_projection_keep_a_complete_inverse(self):
        self.assertEqual(self.change.pins(self.control), self.change.INPUTS)
        self.assertEqual(self.change.restore(self.candidate, deepcopy(self.proof)), self.control)
        generated, proof = self.bridge.render_startup_fixture(dict(self.candidate))
        self.assertEqual(set(generated), set(self.candidate))
        self.assertIsInstance(proof, dict)
        self.assertEqual(generated["board.c"], self.candidate["board.c"])
        self.assertEqual(generated["search.c"], self.candidate["search.c"])

    def test_old_four_argument_and_tail_sources_are_not_the_new_startup_mechanism(self):
        for label, files in (("old-four-argument", self.control), ("nonreturning-tail", self.tail)):
            with self.subTest(source=label), self.assertRaises(ValueError):
                self.bridge.render_startup_fixture(dict(files))

    def test_callback_contract_cannot_be_selected_by_integer_truthiness(self):
        for nonreturning in (0, 1, None, "False"):
            with self.subTest(nonreturning=nonreturning), self.assertRaises(ValueError):
                self.change.transform(self.control, nonreturning=nonreturning)

    def test_stale_tid_consumers_cannot_be_hidden_by_preserving_other_sources(self):
        c = self.change
        mutations = {
            "four-argument-prototype": ("runtime.c", c.PROTOTYPE3, c.PROTOTYPE),
            "four-argument-call": ("runtime.c", c.SPAWN_CALL3, c.SPAWN_CALL),
            "old-clone-flags": ("start.S", b"mov $0x50f00,%edi", b"mov $0x350f00,%edi"),
        }
        for label, (name, before, after) in mutations.items():
            self.assertEqual(self.candidate[name].count(before), 1)
            wrong = dict(self.candidate); wrong[name] = wrong[name].replace(before, after)
            with self.subTest(source=label), self.assertRaises(ValueError):
                self.bridge.render_startup_fixture(wrong)
        wrong = dict(self.candidate)
        wrong["runtime.c"] += b"\nstatic atomic_int ids[WORKERS];\n"
        with self.assertRaises(ValueError):
            self.bridge.render_startup_fixture(wrong)


class NoTidCarrierAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = load("D_no_tid_carrier_authority_tests", HERE / "no_tid_runtime.py")
        cls.admission = load("D_no_tid_carrier_real_authority_tests", HERE / "no_tid_admission.py")
        cls.parent_module = load("D_no_tid_carrier_real_parent_tests", HERE / "search_admission.py")

    def test_old_parent_and_json_maps_cannot_enter_the_new_carrier(self):
        b, a = self.bridge, self.admission
        for token in ({"kind": a.KIND}, object.__new__(self.parent_module.SearchAdmission)):
            with self.subTest(token=type(token).__name__), self.assertRaises(ValueError):
                b.prepare_carrier(token, admission_module=a, admission_source=authority_source(a),
                    bridge_source=authority_source(b), runtime=None, packaging=None, frozen_inputs={})

    def test_foreign_authority_is_rejected_before_calling_its_token_methods(self):
        b, a = self.bridge, self.admission
        class UntrustedToken:
            def assert_valid(self):
                raise AssertionError("foreign token code ran before module authentication")
            def to_record(self):
                raise AssertionError("foreign token record ran before module authentication")
        counterfeit = types.ModuleType("D_no_tid_counterfeit_authority_test")
        counterfeit.__file__ = a.__file__
        counterfeit._EXECUTING_CODE = a._EXECUTING_CODE
        counterfeit.KIND = a.KIND
        counterfeit.NoTidAdmission = UntrustedToken
        with patch.dict(sys.modules, {counterfeit.__name__: counterfeit}):
            consumers = {
                "carrier": lambda: b.prepare_carrier(UntrustedToken(), admission_module=counterfeit,
                    admission_source=authority_source(a), bridge_source=authority_source(b),
                    runtime=None, packaging=None, frozen_inputs={}),
                "shipping-board": lambda: b.shipping_board(UntrustedToken(), b"untrusted board",
                    admission_module=counterfeit, admission_source=authority_source(a), minifier=None, lexical=None),
                "rules": lambda: b.render_rules(UntrustedToken(), [], admission_module=counterfeit,
                    admission_source=authority_source(a), preprocess_board=None, shared=None, minifier=None, lexical=None),
            }
            for name, consume in consumers.items():
                with self.subTest(consumer=name), self.assertRaises(ValueError):
                    consume()

    def test_unminted_no_tid_instance_cannot_shadow_the_carrier_validator(self):
        b, a = self.bridge, self.admission
        unminted = object.__new__(a.NoTidAdmission)
        object.__setattr__(unminted, "_valid", object())
        def tripwire():
            raise AssertionError("unminted instance shadow executed")
        object.__setattr__(unminted, "assert_valid", tripwire)
        with self.assertRaises(ValueError):
            b.prepare_carrier(unminted, admission_module=a, admission_source=authority_source(a),
                bridge_source=authority_source(b), runtime=None, packaging=None, frozen_inputs={})

    def test_carrier_source_requires_actual_function_globals(self):
        b = self.bridge
        actual = authority_source(b)
        self.assertEqual(b._source(actual, b), actual["frozen"])
        original = b._relative
        counterfeit = types.FunctionType(original.__code__, dict(b.__dict__), original.__name__)
        with patch.object(b, "_relative", counterfeit):
            with self.assertRaises(ValueError):
                b._source(actual, b)


class QualifierSourceAndSupport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qualifier = load("D_no_tid_qualifier_component_tests", HERE / "qualify_no_tid.py")
        cls.runtime = load("D_no_tid_generic_runtime_component_tests",
                           ROOT / "engines/experiments/tcec-next/profile_verify.py")

    def test_frozen_loader_consumes_captured_bytes_even_if_live_path_changes(self):
        q = self.qualifier
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "component.py"
            path.write_bytes(b"raise AssertionError('live source executed')\n")
            frozen = b"value=17\ndef compute(): return value+1\n"
            module = q.load_bytes("D_no_tid_captured_component_test", path, frozen)
            self.assertEqual(module.compute(), 18)
            self.assertEqual(module.__file__, str(path))

    def test_reader_and_composer_are_individually_required_closure_members(self):
        q = self.qualifier
        support = {name: (ROOT / name).read_bytes().replace(b"\r\n", b"\n") for name in q.SUPPORT}
        self.assertIn(READER, support)
        self.assertIn(COMPOSER, support)
        q.require_support(self.runtime, support)
        for missing in (READER, COMPOSER):
            without = {name: data for name, data in support.items() if name != missing}
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                q.require_support(self.runtime, without)
        with self.assertRaises(ValueError):
            q.require_support(self.runtime, {**support, "engines/unconsumed-helper.py": b"pass\n"})

    def test_explicit_qualification_tools_do_not_replace_old_search_consumers(self):
        q = self.qualifier
        required = {D + "no_tid_admission.py", D + "no_tid_runtime.py", D + "qualify_no_tid.py"}
        self.assertTrue(required <= set(q.TOOLS))
        self.assertNotIn(D + "search_runtime.py", q.TOOLS)
        self.assertNotIn(D + "qualify_search.py", q.TOOLS)

    def test_unified_snapshot_rejects_conflicting_support_provenance(self):
        q = self.qualifier
        captured = {READER: b"captured reader", COMPOSER: b"captured composer"}
        self.assertEqual(q.unified_sources(captured, dict(captured)), captured)
        for name in (READER, COMPOSER):
            with self.subTest(conflict=name), self.assertRaises(ValueError):
                q.unified_sources(captured, {name: b"different authority for same role"})

    def test_nested_owner_keeps_cumulative_positive_cpu_limits(self):
        q = self.qualifier
        self.assertEqual(q.bounded_limits(300, 330, (150, 180)), (150, 180))
        self.assertEqual(q.bounded_limits(300, 330, (-1, -1)), (300, 330))
        self.assertEqual(q.bounded_limits(300, 330, (150, -1)), (150, 330))
        for current in ((0, 0), (True, 180), (150.0, 180)):
            with self.subTest(current=current), self.assertRaises(ValueError):
                q.bounded_limits(300, 330, current)

    def test_bounded_reader_rejects_traversal_and_oversize_evidence(self):
        q = self.qualifier
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source.c").write_bytes(b"abcd")
            self.assertEqual(q.safe(root, "source.c", maximum=4), b"abcd")
            with self.assertRaises(ValueError):
                q.safe(root, "source.c", maximum=3)
            for name in ("../outside.c", str(root / "source.c")):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    q.safe(root, name)

    @unittest.skipUnless(os.name == "posix", "actual POSIX link semantics")
    def test_evidence_reader_rejects_symlinks_and_shared_hardlinks(self):
        q = self.qualifier
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "source.c"
            original.write_bytes(b"component source")
            os.symlink(original, root / "symbolic.c")
            with self.assertRaises(ValueError):
                q.safe(root, "symbolic.c")
            os.link(original, root / "hard.c")
            for name in ("source.c", "hard.c"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    q.safe(root, name)

    def test_evidence_write_never_overwrites_the_first_result(self):
        q = self.qualifier
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            q.write(root, "fresh/source.c", b"original evidence")
            with self.assertRaises(ValueError):
                q.write(root, "fresh/source.c", b"replacement")
            self.assertEqual((root / "fresh/source.c").read_bytes(), b"original evidence")

    def test_python310_syntax_for_new_qualification_modules(self):
        for name in ("no_tid_admission.py", "no_tid_runtime.py", "qualify_no_tid.py"):
            with self.subTest(module=name):
                ast.parse((HERE / name).read_bytes(), feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
