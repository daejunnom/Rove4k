"""Actual compiler checks for the reviewed final include projection."""
import importlib.util
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("dependency_projection_tests",
                                            Path(__file__).with_name("profile_dependencies.py"))
DEPENDENCIES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPENDENCIES)


@unittest.skipUnless(shutil.which("cc"), "C compiler required")
class DependencyProjectionTests(unittest.TestCase):
    def run_compiler(self, command, *, cwd, kind, data):
        result = subprocess.run(command, cwd=cwd, input=data, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result.stdout

    def test_unused_header_has_identical_expansion_and_native(self):
        before = b"#include<stdlib.h>\n#include<limits.h>\nint main(void){return 0;}\n"
        after, proof = DEPENDENCIES.transform_source(before)
        self.assertEqual(DEPENDENCIES.restore_source(after, proof), before)
        with tempfile.TemporaryDirectory(prefix="rove4k-dependency-test-") as temp:
            root = Path(temp)
            command = ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"]
            gate = DEPENDENCIES.compile_gate(before, after, compiler=command,
                directory=root / "gate", run=self.run_compiler, prefix="test")
            self.run_compiler(command, cwd=root, kind="shipping", data=after)
            self.assertEqual((root / "gate/x").read_bytes(), (root / "x").read_bytes())
            self.assertEqual(gate["native"], DEPENDENCIES.pin((root / "x").read_bytes()))

    def test_required_macro_conditional_and_line_identity_are_rejected(self):
        for body in (b"int main(void){return INT_MAX;}\n",
                     b"#if INT_MAX>10\nint main(void){return 0;}\n#else\nint main(void){return 1;}\n#endif\n",
                     b"int main(void){return __LINE__;}\n"):
            with self.subTest(body=body), tempfile.TemporaryDirectory(prefix="rove4k-dependency-reject-") as temp:
                before = b"#include<limits.h>\n" + body
                after, _ = DEPENDENCIES.transform_source(before)
                with self.assertRaisesRegex(ValueError, "changed expanded compiler input"):
                    DEPENDENCIES.compile_gate(before, after,
                        compiler=["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"],
                        directory=Path(temp) / "gate", run=self.run_compiler, prefix="test")
                self.assertFalse((Path(temp) / "gate/x").exists())

    def test_target_flags_are_preserved_and_other_modes_rejected(self):
        command = ["cc", "-Os", "-mavx2", "-DVALUE=1", "-x", "c", "-", "-o", "x", "-s"]
        self.assertEqual(DEPENDENCIES.preprocess_command(command),
            ["cc", "-Os", "-mavx2", "-DVALUE=1", "-x", "c", "-", "-E", "-P"])
        with self.assertRaises(ValueError):
            DEPENDENCIES.preprocess_command(command + ["-c"])

    def test_inverse_rejects_tampering_and_absent_include_is_identity(self):
        before = b"#include<limits.h>\nint main(void){return 0;}\n"
        after, proof = DEPENDENCIES.transform_source(before)
        with self.assertRaisesRegex(ValueError, "output identity"):
            DEPENDENCIES.restore_source(after + b" ", proof)
        same, empty = DEPENDENCIES.transform_source(after)
        self.assertEqual(same, after)
        self.assertEqual(empty["spans"], [])
        with self.assertRaisesRegex(ValueError, "at most one"):
            DEPENDENCIES.transform_source(DEPENDENCIES.DIRECTIVE + before)

    def test_receipt_binds_shipping_compiler_and_actual_stdin(self):
        # Synthetic receipt isolates the admission boundary; the tests above
        # exercise real compiler behavior. No synthetic image is executed.
        before = b"#include<limits.h>\nint main(void){return 0;}\n"
        after, proof = DEPENDENCIES.transform_source(before)
        compiler = ["cc", "-Os", "-x", "c", "-", "-o", "x", "-s"]
        native, expanded = b"fixture native", b"fixture expanded input"
        files = {"first/dependency-gate/before.c": before,
                 "first/dependency-gate/after.c": after,
                 "first/dependency-gate/before.i": expanded,
                 "first/dependency-gate/after.i": expanded,
                 "first/dependency-gate/x": native, "first/native/x": native}
        commands = []
        for index, label in enumerate(("before", "after", "native", "shipping")):
            stem = "tool-" + str(index)
            stdout = expanded if label in ("before", "after") else b""
            files[stem + ".stdout"], files[stem + ".stderr"] = stdout, b""
            files[stem + ".stdin"] = after if label in ("after", "shipping") else before
            commands.append(dict(kind="first-compile" if label == "shipping" else "first-dependencies-" + label,
                command=DEPENDENCIES.preprocess_command(compiler) if label in ("before", "after") else compiler.copy(),
                returncode=0, terminal=True, reaped=True, owned_group_absent=True, forced_cleanup=False,
                stdout={"path": stem + ".stdout", **DEPENDENCIES.pin(stdout)},
                stderr={"path": stem + ".stderr", **DEPENDENCIES.pin(b"")}))
        receipt = dict(compiler=compiler, source_dependencies=DEPENDENCIES.DECLARATION, commands=commands,
            attempts=[dict(directory="first", native_bytes=len(native),
                native_sha256=DEPENDENCIES.pin(native)["sha256"], whole_bytes=40,
                dependency_gate=dict(input=DEPENDENCIES.pin(before), output=DEPENDENCIES.pin(after),
                    expanded=DEPENDENCIES.pin(expanded), native=DEPENDENCIES.pin(native),
                    whole_cost=dict(before=41, after=40)))])
        def checked(root, name, expected):
            data = files[name]
            if DEPENDENCIES.pin(data) != expected:
                raise ValueError("evidence pin differs")
            return data
        self.assertEqual(DEPENDENCIES.validate_receipt(Path("unused"), receipt, proof, after,
                                                      checked=checked), before)
        # The same owned native evidence must also bind the pre-compaction
        # compile when the later stage is explicitly selected. It is not
        # acceptable to silently fall back to the final shipping command.
        compact = copy.deepcopy(receipt)
        compact["post_compact"] = {"path": "reviewed-helper.py", "variant": "named"}
        compact["commands"][-1]["kind"] = "first-final-compact-control"
        compact["attempts"][0]["final_compact_gate"] = {
            "directory": "final-compact-control", "source": DEPENDENCIES.pin(after),
            "native": DEPENDENCIES.pin(native), "image_identical": True}
        # The dependency reduction ends at 40 bytes; the later compact stage
        # then independently reduces the shipping artifact from 40 to 39.
        compact["attempts"][0]["final_compact_cost"] = {"before": 40, "after": 39}
        compact["attempts"][0]["whole_bytes"] = 39
        files["first/final-compact-control/x"] = native
        self.assertEqual(DEPENDENCIES.validate_receipt(Path("unused"), compact, proof, after,
                                                      checked=checked, final_compact=True), before)
        with self.assertRaisesRegex(ValueError, "explicit control compile"):
            DEPENDENCIES.validate_receipt(Path("unused"), compact, proof, after, checked=checked)
        with self.assertRaisesRegex(ValueError, "explicit final compaction mode"):
            DEPENDENCIES.validate_receipt(Path("unused"), compact, proof, after,
                                          checked=checked, final_compact=1)
        for field, bad, message in (("image_identical", 1, "control gate"),
                                    ("source", DEPENDENCIES.pin(before), "control gate")):
            changed = copy.deepcopy(compact)
            changed["attempts"][0]["final_compact_gate"][field] = bad
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                DEPENDENCIES.validate_receipt(Path("unused"), changed, proof, after,
                                              checked=checked, final_compact=True)
        changed = copy.deepcopy(compact)
        changed["commands"][-1]["kind"] = "first-compile"
        with self.assertRaisesRegex(ValueError, "control compiler command"):
            DEPENDENCIES.validate_receipt(Path("unused"), changed, proof, after,
                                          checked=checked, final_compact=True)
        for cost, error in (({"before": 39, "after": 39}, "dependency whole cost"),
                            ({"before": 40, "after": 38}, "final compaction whole cost"),
                            ({"before": 40, "after": True}, "final compaction whole cost"),
                            ({"before": 38, "after": 39}, "final compaction whole cost"),
                            (None, "final compaction whole cost")):
            changed = copy.deepcopy(compact)
            changed["attempts"][0]["final_compact_cost"] = cost
            with self.subTest(cost=cost), self.assertRaisesRegex(ValueError, error):
                DEPENDENCIES.validate_receipt(Path("unused"), changed, proof, after,
                                              checked=checked, final_compact=True)
        files["first/final-compact-control/x"] = b"different native"
        with self.assertRaisesRegex(ValueError, "evidence pin differs"):
            DEPENDENCIES.validate_receipt(Path("unused"), compact, proof, after,
                                          checked=checked, final_compact=True)
        files["first/final-compact-control/x"] = native
        changed = copy.deepcopy(receipt)
        changed["commands"][-1]["command"].append("-DOTHER_CONTEXT=1")
        with self.assertRaisesRegex(ValueError, "shipping dependency compiler command differs"):
            DEPENDENCIES.validate_receipt(Path("unused"), changed, proof, after, checked=checked)
        files["tool-3.stdin"] = before
        with self.assertRaisesRegex(ValueError, "evidence pin differs"):
            DEPENDENCIES.validate_receipt(Path("unused"), receipt, proof, after, checked=checked)

    def test_identity_cleanup_still_requires_compaction_control(self):
        source = b"int main(void){return 0;}\n"
        unchanged, proof = DEPENDENCIES.transform_source(source)
        self.assertEqual(unchanged, source)
        native = b"native"
        receipt = {"compiler": ["cc"], "source_dependencies": DEPENDENCIES.DECLARATION,
                   "post_compact": {"path": "reviewed-helper.py", "variant": "named"},
                   "commands": [], "attempts": [{"directory": "first", "dependency_gate": None,
                   "native_bytes": len(native), "native_sha256": DEPENDENCIES.pin(native)["sha256"]}]}
        with self.assertRaisesRegex(ValueError, "control gate"):
            DEPENDENCIES.validate_receipt(Path("unused"), receipt, proof, source,
                                          checked=lambda *args: b"", final_compact=True)
        receipt["attempts"][0].update(whole_bytes=39, final_compact_gate={
            "directory": "final-compact-control", "source": DEPENDENCIES.pin(source),
            "native": DEPENDENCIES.pin(native), "image_identical": True})
        receipt["commands"] = [{"kind": "first-final-compact-control", "command": ["cc"],
            "returncode": 0, "terminal": True, "reaped": True, "owned_group_absent": True,
            "forced_cleanup": False, "stdout": {"path": "tool-1.stdout"},
            "stderr": {"path": "tool-1.stderr", **DEPENDENCIES.pin(b"")}}]
        files = {"tool-1.stdin": source, "tool-1.stderr": b"",
                 "first/final-compact-control/x": native, "first/native/x": native}
        def checked(root, name, expected):
            data = files[name]
            if DEPENDENCIES.pin(data) != expected:
                raise ValueError("evidence pin differs")
            return data
        with self.assertRaisesRegex(ValueError, "final compaction whole cost"):
            DEPENDENCIES.validate_receipt(Path("unused"), receipt, proof, source,
                                          checked=checked, final_compact=True)
        receipt["attempts"][0]["final_compact_cost"] = {"before": 40, "after": 39}
        self.assertEqual(DEPENDENCIES.validate_receipt(Path("unused"), receipt, proof, source,
                                                      checked=checked, final_compact=True), source)


if __name__ == "__main__":
    unittest.main()
