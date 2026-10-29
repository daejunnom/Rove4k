import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


path = Path(__file__).with_name("league_candidate_compare.py")
spec = importlib.util.spec_from_file_location("league_candidate_compare_tested", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())


class CompareContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.roots = [Path(self.temp.name) / "control", Path(self.temp.name) / "candidate"]
        parent, candidate = b"exact parent source", b"exact candidate source"
        rows = [{"kind": name, "returncode": 0, "terminal": True, "reaped": True,
                 "owned_group_absent": True, "forced_cleanup": False} for name in (
                     "rules-compile-plain", "rules-execute-plain", "rules-compile-ubsan", "rules-execute-ubsan")]
        for index, root in enumerate(self.roots):
            whole = (b"control" if index == 0 else b"candidate")
            manifest = {"family": "A", "resources": {"id": "test-p16"}, "complete": True,
                        "reproducible": True, "compiler": ["cc"], "compile_executor": ["cc"],
                        "compile_executor_version": "test", "compression": {"format": "test"}}
            if index:
                manifest["post_league"] = {"path": module.HELPERS["square-successor"],
                                           "variant": "square-successor"}
                manifest["source_proofs"] = [{"input": module.pin(parent), "output": module.pin(candidate),
                                              "variant": "square-successor", "full_inverse": True}]
            put(root / "build/build.json", manifest)
            put(root / "build/main.c", parent if index == 0 else candidate)
            put(root / "build/x", whole)
            put(root / "build/header.sh", b"same header")
            put(root / "build/control/main.c", b"same producer parent")
            put(root / "resource-projection.c", parent)
            put(root / "compiler-sha256.txt", b"same compiler")
            put(root / "linker-sha256.txt", b"same linker")
            put(root / "artifact-audit.json", {"family": "A", "profile": "test-p16",
                "variant": "control" if not index else "square-successor", "parts": {"x": module.pin(whole)},
                "actual_whole_bytes": len(whole)})
            put(root / "admission.json", {"strict_source_admission": True, "family": "A", "profile": "test-p16",
                                         "variant": "control" if not index else "square-successor"})
            put(root / "rules/probe/rules.json", {"complete": True, "family": "A", "profile": {"id": "test-p16"},
                                                   "source": module.pin(parent if index == 0 else candidate)})
            put(root / "rules/commands.json", {"complete": True, "commands": rows,
                "host_cleanup": {"unsettled_commands": 0, "errors": []}})

    def check(self):
        return module.checked_pair(*self.roots, family="A", profile="test-p16", variant="square-successor")

    def test_actual_pair_and_source_identity(self):
        self.assertEqual(self.check()[2], [b"exact parent source", b"exact candidate source"])
        (self.roots[1] / "build/main.c").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "rules"):
            self.check()

    def test_partial_rules_and_tool_mismatch_are_rejected(self):
        put(self.roots[1] / "rules/probe/rules.json", {"complete": False})
        with self.assertRaisesRegex(ValueError, "rules"):
            self.check()
        put(self.roots[1] / "rules/probe/rules.json", {"complete": True, "family": "A", "profile": {"id": "test-p16"},
            "source": module.pin(b"exact candidate source")})
        put(self.roots[1] / "linker-sha256.txt", b"different linker")
        with self.assertRaisesRegex(ValueError, "identity"):
            self.check()

    def test_admission_and_rules_are_bound_to_actual_identity(self):
        target = self.roots[1] / "admission.json"
        put(target, {"strict_source_admission": True, "family": "C", "profile": "test-p16", "variant": "square-successor"})
        with self.assertRaisesRegex(ValueError, "admission"):
            self.check()
        put(target, {"strict_source_admission": True, "family": "A", "profile": "test-p16", "variant": "square-successor"})
        target = self.roots[1] / "rules/probe/rules.json"
        put(target, {"complete": True, "family": "A", "profile": {"id": "test-p192"}, "source": module.pin(b"exact candidate source")})
        with self.assertRaisesRegex(ValueError, "rules"):
            self.check()


if __name__ == "__main__":
    unittest.main()
