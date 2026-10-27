import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


path = Path(__file__).with_name("league_compound_compare.py")
spec = importlib.util.spec_from_file_location("league_compound_compare_tested", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())


class CompoundCompareContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = b"same original source"
        self.single_proofs = {}
        self.roots = {}
        self._artifact("control", self.base)
        for name in module.SINGLES.values():
            source = (name + " output").encode()
            proof = {"input": module.single.pin(self.base), "output": module.single.pin(source),
                     "variant": name, "full_inverse": True, "test_flag": True}
            self.single_proofs[name] = proof
            self._artifact(name, source, proof)
        for name, components in module.VARIANTS.items():
            source = (name + " output").encode()
            proof = {"schema": module.COMPOUND_SCHEMA, "family": "C", "profile_id": "test-p16",
                     "variant": name, "input": module.single.pin(self.base),
                     "output": module.single.pin(source), "full_inverse": True,
                     "components": [{"component": part, "proof": self.single_proofs[module.SINGLES[part]]}
                                    for part in components]}
            self._artifact(name, source, proof)

    def _artifact(self, name, source, proof=None):
        root = self.root / name
        self.roots[name] = root
        whole = ("wrapper-" + name).encode()
        manifest = {"family": "C", "resources": {"id": "test-p16"}, "complete": True,
                    "reproducible": True, "compiler": ["cc"], "compile_executor": ["cc"],
                    "compile_executor_version": "test", "compression": {"format": "test"}}
        if proof is not None:
            helper = (module.COMPOUND_PATH if name in module.VARIANTS else module.single.HELPERS[name])
            manifest["post_league"] = {"path": helper, "variant": name}
            manifest["source_proofs"] = [proof]
        put(root / "build/build.json", manifest)
        put(root / "build/main.c", source)
        put(root / "build/x", whole)
        put(root / "build/header.sh", b"same header")
        put(root / "build/control/main.c", b"same original producer input")
        put(root / "resource-projection.c", self.base)
        put(root / "compiler-sha256.txt", b"same compiler")
        put(root / "linker-sha256.txt", b"same linker")
        put(root / "artifact-audit.json", {"family": "C", "profile": "test-p16", "variant": name,
            "parts": {"x": module.single.pin(whole)}, "actual_whole_bytes": len(whole)})
        put(root / "admission.json", {"strict_source_admission": True, "family": "C", "profile": "test-p16", "variant": name})
        put(root / "rules/probe/rules.json", {"complete": True, "family": "C", "profile": {"id": "test-p16"},
                                              "source": module.single.pin(source)})
        rows = [{"kind": kind, "returncode": 0, "terminal": True, "reaped": True,
                 "owned_group_absent": True, "forced_cleanup": False} for kind in (
                     "rules-compile-plain", "rules-execute-plain", "rules-compile-ubsan", "rules-execute-ubsan")]
        put(root / "rules/commands.json", {"complete": True, "commands": rows,
             "host_cleanup": {"unsettled_commands": 0, "errors": []}})

    def arguments(self, variant):
        singles = [(module.SINGLES[name], self.roots[module.SINGLES[name]]) for name in module.VARIANTS[variant]]
        pairs = [(name, self.roots[name]) for name in module.PAIRS] if variant == "square-ep-atomic" else []
        return {"family": "C", "profile": "test-p16", "variant": variant, "singles": singles, "pairs": pairs}

    def check(self, variant):
        return module.checked_comparison(self.roots["control"], self.roots[variant], **self.arguments(variant))

    def test_all_pairs_and_triple_bind_actual_constituents(self):
        for variant in module.VARIANTS:
            with self.subTest(variant=variant):
                roots, _, _ = self.check(variant)
                expected = 8 if variant == "square-ep-atomic" else 4
                self.assertEqual(len(roots), expected)

    def test_missing_or_duplicate_single_and_missing_triple_pair_fail(self):
        args = self.arguments("square-ep-atomic")
        args["singles"] = args["singles"][:-1]
        with self.assertRaisesRegex(ValueError, "single candidates"):
            module.checked_comparison(self.roots["control"], self.roots[args["variant"]], **args)
        args = self.arguments("square-ep-atomic")
        args["pairs"] = args["pairs"][:-1]
        with self.assertRaisesRegex(ValueError, "pair candidates"):
            module.checked_comparison(self.roots["control"], self.roots[args["variant"]], **args)
        args = self.arguments("square-atomic")
        args["singles"].append(args["singles"][0])
        with self.assertRaisesRegex(ValueError, "single candidates"):
            module.checked_comparison(self.roots["control"], self.roots[args["variant"]], **args)

    def test_component_proof_must_match_actual_single_with_json_types(self):
        path = self.roots["square-atomic"] / "build/build.json"
        manifest = json.loads(path.read_bytes())
        manifest["source_proofs"][-1]["components"][0]["proof"]["test_flag"] = 1
        put(path, manifest)
        with self.assertRaisesRegex(ValueError, "constituent proof"):
            self.check("square-atomic")

    def test_pair_proof_and_producer_rule_failure_are_rejected(self):
        path = self.roots["square-ep"] / "build/build.json"
        manifest = json.loads(path.read_bytes())
        manifest["source_proofs"][-1]["components"].reverse()
        put(path, manifest)
        with self.assertRaisesRegex(ValueError, "component order"):
            self.check("square-ep-atomic")
        put(self.roots["atomic-assignment"] / "rules/probe/rules.json", {"complete": False})
        with self.assertRaisesRegex(ValueError, "rules"):
            self.check("square-atomic")

    def test_same_host_compares_control_singles_and_all_pairs(self):
        class Wrapper:
            @staticmethod
            def package(package, unlink, source, compression, compiler):
                return b"same-header" + source
        with patch.object(module.single, "load_shared", side_effect=[object(), Wrapper, object()]):
            result = module.compare(self.roots["control"], self.roots["square-ep-atomic"],
                                    **self.arguments("square-ep-atomic"))
        self.assertEqual(set(result["versus"]), set(self.roots) - {"square-ep-atomic"})
        self.assertFalse(result["production_selected"])
        self.assertFalse(result["runtime_qualified"])
        self.assertTrue(result["constituent_proofs_match"])


if __name__ == "__main__":
    unittest.main()
