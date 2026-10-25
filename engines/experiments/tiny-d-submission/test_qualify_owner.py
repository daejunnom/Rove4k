"""Frozen owner runtime support/import closure; no compiler or engine jobs."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
READER="engines/scripts/production_input.py"


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


QUALIFY=load("owner_support_qualifier",HERE/"qualify_owner.py")


def write_snapshot(root,contents):
    for name,data in contents.items():
        path=root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)


@unittest.skipUnless(sys.platform=="linux","actual POSIX bounded reader path")
class OwnerRuntimeSupport(unittest.TestCase):
    def test_actual_frozen_runtime_and_rules_imports_are_complete(self):
        contents=QUALIFY.support_inputs(ROOT)
        self.assertIn(READER,contents)
        with tempfile.TemporaryDirectory(prefix="D-owner-frozen-support-") as temporary,patch.dict(sys.modules):
            sys.modules.pop("rove4k_production_input",None)
            root=Path(temporary)
            write_snapshot(root,contents)
            runtime=load("owner_support_frozen_runtime",root/QUALIFY.SUPPORT[0])
            QUALIFY.require_support_closure(runtime,contents)
            actual_load=runtime.load;observed=[]
            def confined_load(name,path):
                resolved=path.resolve()
                self.assertTrue(resolved.is_relative_to(root.resolve()),str(path))
                observed.append(resolved.relative_to(root.resolve()).as_posix())
                return actual_load(name,path)
            with patch.object(runtime,"load",confined_load):
                scope,owner,oracle=runtime.support_modules()
                reader=runtime.input_reader()
                self.assertEqual(reader.source_identity(),contents[READER])
                self.assertEqual(Path(reader.__file__).resolve(),root/READER)
                self.assertEqual(runtime.contracts().engine_spec("D").family,"D")
            self.assertTrue({READER,"engines/scripts/production.py",*runtime.SUPPORT}<=set(observed))
            self.assertTrue(all(Path(module.__file__).resolve().is_relative_to(root.resolve())
                                for module in (scope,owner,oracle)))
            rules=load("owner_support_frozen_rules",root/QUALIFY.SUPPORT[1])
            actual_rules_load=rules.load
            def confined_rules_load(name,path):
                self.assertTrue(path.resolve().is_relative_to(root.resolve()),str(path))
                return actual_rules_load(name,path)
            with patch.object(rules,"load",confined_rules_load):
                cases,coverage=rules.fixture_cases()
            self.assertEqual(len(cases),105)
            self.assertTrue(coverage)

    def test_missing_frozen_reader_fails_without_original_root_fallback(self):
        contents=QUALIFY.support_inputs(ROOT)
        del contents[READER]
        with tempfile.TemporaryDirectory(prefix="D-owner-missing-reader-") as temporary,patch.dict(sys.modules):
            sys.modules.pop("rove4k_production_input",None)
            root=Path(temporary)
            write_snapshot(root,contents)
            runtime=load("owner_support_missing_runtime",root/QUALIFY.SUPPORT[0])
            with self.assertRaisesRegex(ValueError,"support closure differs"):
                QUALIFY.require_support_closure(runtime,contents)
            with self.assertRaises(FileNotFoundError) as missing:
                runtime.support_modules()
            self.assertEqual(Path(missing.exception.filename),root/READER)

    def test_canonical_reader_from_another_root_is_rejected(self):
        contents=QUALIFY.support_inputs(ROOT)
        with tempfile.TemporaryDirectory(prefix="D-owner-wrong-reader-") as temporary,patch.dict(sys.modules):
            sys.modules.pop("rove4k_production_input",None)
            root=Path(temporary)
            write_snapshot(root,contents)
            load("rove4k_production_input",ROOT/READER)
            runtime=load("owner_support_wrong_runtime",root/QUALIFY.SUPPORT[0])
            with self.assertRaisesRegex(ValueError,"shared input reader came from another source path"):
                runtime.support_modules()

    def test_unused_composer_is_not_silently_added_to_runtime_support(self):
        # source_composition is already in the separately admitted producer
        # closure. Generic local runtime/contracts do not import that tool.
        contents=QUALIFY.support_inputs(ROOT)
        with tempfile.TemporaryDirectory(prefix="D-owner-extra-support-") as temporary:
            root=Path(temporary)
            write_snapshot(root,contents)
            runtime=load("owner_support_extra_runtime",root/QUALIFY.SUPPORT[0])
            extra={**contents,"engines/scripts/source_composition.py":b"unused"}
            with self.assertRaisesRegex(ValueError,"support closure differs"):
                QUALIFY.require_support_closure(runtime,extra)


if __name__=="__main__":unittest.main()
