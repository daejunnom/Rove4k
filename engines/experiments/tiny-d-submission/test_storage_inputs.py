"""Actual frozen-only storage/D7 recipe replay; no compiler or engine jobs."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


NAMES=load("storage_regression_names",HERE/"source_inputs.py")
SOURCE=load("storage_regression_source",HERE/"source.py")
STORAGE=load("storage_regression_fixture",HERE/"check_storage.py")
CONSUMERS=("test_search_compact","test_attack_compact","test_frontend_compact")


def write_snapshot(root,contents):
    for name,data in contents.items():
        path=root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)


def frozen_replay(root,expected):
    """Every actual source byte read must resolve inside the isolated snapshot."""
    frozen_source=load("storage_regression_frozen_source",root/(NAMES.D+"source.py"))
    original=Path.read_bytes
    observed=[]
    def read_bytes(path):
        resolved=path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise AssertionError("source replay escaped frozen snapshot: "+str(resolved))
        observed.append(resolved.relative_to(root.resolve()).as_posix())
        return original(path)
    with patch.object(Path,"read_bytes",read_bytes):
        profile=frozen_source.production().resource_profile("test-p4")
        prepared,proof=frozen_source.prepare(profile)
    if (prepared,proof)!=expected:
        raise AssertionError("actual frozen-only source/proof differs")
    return observed


class StorageRecipeInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected=SOURCE.prepare(SOURCE.production().resource_profile("test-p4"))
        cls.recipe=json.loads(SOURCE.normalized(ROOT/NAMES.RECIPE))

    def test_storage_snapshot_is_exact_recipe_and_executable_tool_closure(self):
        contents=STORAGE.snapshot_inputs()
        expected={*NAMES.source_names(self.recipe),NAMES.SELF,SOURCE.HOST,
                  NAMES.D+"storage.py",NAMES.D+"check_storage.py"}
        self.assertEqual(set(contents),expected)
        self.assertIn(NAMES.COMPOSER,contents)
        self.assertTrue(set(self.recipe["shared_source_sha256"])<=contents.keys())
        with tempfile.TemporaryDirectory(prefix="D-storage-frozen-only-") as temporary:
            root=Path(temporary)
            write_snapshot(root,contents)
            observed=frozen_replay(root,self.expected)
            self.assertIn(NAMES.COMPOSER,observed)
            self.assertTrue(set(self.recipe["shared_source_sha256"])<=set(observed))
            frozen_fixture=load("storage_regression_frozen_fixture",root/(NAMES.D+"check_storage.py"))
            self.assertEqual(frozen_fixture.snapshot_inputs(),contents)

    def test_missing_frozen_assembler_fails_without_workspace_fallback(self):
        contents=STORAGE.snapshot_inputs()
        del contents[NAMES.COMPOSER]
        with tempfile.TemporaryDirectory(prefix="D-storage-missing-assembler-") as temporary:
            root=Path(temporary)
            write_snapshot(root,contents)
            source=load("storage_regression_missing_composer",root/(NAMES.D+"source.py"))
            with self.assertRaises(FileNotFoundError) as missing:
                source.prepare(source.production().resource_profile("test-p4"))
            self.assertEqual(Path(missing.exception.filename),root/NAMES.COMPOSER)

    @unittest.skipUnless(sys.platform=="linux","actual Linux consumer snapshot entry")
    def test_each_actual_D7_entry_freezes_recipe_and_replays_from_its_own_inputs(self):
        producer=NAMES.producer_names(self.recipe)
        producer_bytes={name:SOURCE.normalized(ROOT/name) for name in producer}
        control=dict(storage="prefix",source_reduced=False,family="D",equivalent_edits=True,
            complete=True,frozen_execution=True,native_reproduced=True,units=["main.c","start.S"],
            inputs={name:SOURCE.pin(data) for name,data in producer_bytes.items()})
        for consumer in CONSUMERS:
            with self.subTest(consumer=consumer),tempfile.TemporaryDirectory(prefix="D7-source-closure-") as temporary:
                root=Path(temporary);selected=root/"selected";selected.mkdir();out=root/"out"
                write_snapshot(selected/"inputs",producer_bytes)
                (selected/"build.json").write_text(json.dumps(control))
                reader=load("storage_regression_"+consumer,HERE/(consumer+".py"))
                actual_load=reader.load;captured=[]
                def execute_snapshot(actual_out,contents,origin):
                    self.assertEqual(actual_out,out)
                    self.assertEqual(origin,ROOT)
                    self.assertTrue(set(producer)<=contents.keys())
                    self.assertIn(NAMES.SELF,contents)
                    self.assertIn(NAMES.COMPOSER,contents)
                    self.assertEqual(contents[NAMES.SELF],SOURCE.normalized(ROOT/NAMES.SELF))
                    captured.append(frozen_replay(out/"inputs",self.expected))
                def load_consumer(name,path):
                    if path==out/"inputs"/(NAMES.D+consumer+".py"):
                        return SimpleNamespace(run_snapshot=execute_snapshot)
                    return actual_load(name,path)
                # Only later compilation/runtime consumption is replaced. The
                # actual entry's recipe membership, pins, reads and writes run.
                with patch.object(reader,"load",load_consumer),patch.object(sys,"argv",
                        [str(HERE/(consumer+".py")),"--build",str(selected),"--out",str(out)]):
                    reader.main()
                self.assertEqual(len(captured),1)
                self.assertIn(NAMES.COMPOSER,captured[0])

    @unittest.skipUnless(sys.platform=="linux","actual Linux consumer rejection entry")
    def test_D7_old_or_extra_producer_closure_still_fails_before_snapshot(self):
        producer=NAMES.producer_names(self.recipe)
        producer_bytes={name:SOURCE.normalized(ROOT/name) for name in producer}
        good=dict(storage="prefix",source_reduced=False,family="D",equivalent_edits=True,
            complete=True,frozen_execution=True,native_reproduced=True,units=["main.c","start.S"],
            inputs={name:SOURCE.pin(data) for name,data in producer_bytes.items()})
        for consumer in CONSUMERS:
            for mutation in ("missing-assembler","extra-source"):
                with self.subTest(consumer=consumer,mutation=mutation),tempfile.TemporaryDirectory(prefix="D7-reject-") as temporary:
                    root=Path(temporary);selected=root/"selected";selected.mkdir();out=root/"out"
                    record=deepcopy(good)
                    if mutation=="missing-assembler":del record["inputs"][NAMES.COMPOSER]
                    else:record["inputs"]["engines/common/protocol.c"]={"bytes":0,"sha256":"0"*64}
                    (selected/"build.json").write_text(json.dumps(record))
                    reader=load("storage_regression_reject_"+consumer,HERE/(consumer+".py"))
                    with patch.object(sys,"argv",[str(HERE/(consumer+".py")),"--build",str(selected),"--out",str(out)]):
                        with self.assertRaisesRegex(ValueError,"unreduced prefix control required"):
                            reader.main()
                    self.assertFalse(out.exists())


if __name__=="__main__":unittest.main()
