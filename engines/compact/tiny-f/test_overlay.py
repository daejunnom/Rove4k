"""Producer schema/admission tests; actual engine contracts are separate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("tiny_f_overlay_test",HERE/"overlay.py")
overlay=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay)
spec=importlib.util.spec_from_file_location("tiny_f_qualification_test",HERE/"qualify.py")
qualify=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualify)


class OverlayTests(unittest.TestCase):
    def inputs(self):
        return {name:(HERE.parent/"tiny-a"/name).read_bytes() for name in overlay.EXPECTED}

    def test_admitted_frozen_inputs_and_explicit_f_name(self):
        result=overlay.transform(self.inputs(),(HERE/"search.c").read_bytes())
        self.assertIn(b"Rove4k F full-depth MTD",result["main.c"])
        self.assertIn(b"f_conflicts",result["tiny.h"])
        self.assertIn(b"f_upper_other",result["main.c"])

    def test_changed_input_fails_closed(self):
        for name in overlay.EXPECTED:
            inputs=self.inputs();inputs[name]+=b"\n"
            with self.assertRaises(ValueError):overlay.transform(inputs,b"")

    def test_lf_and_crlf_have_same_overlay(self):
        inputs={name:data.replace(b"\r\n",b"\n") for name,data in self.inputs().items()}
        crlf={name:data.replace(b"\n",b"\r\n") for name,data in inputs.items()}
        self.assertEqual(overlay.transform(inputs,b"x\n"),overlay.transform(crlf,b"x\r\n"))


class EncodingBindingTests(unittest.TestCase):
    def fixture(self,directory):
        sha=qualify.sha;directory=Path(directory)
        source=b"f source";build=json.dumps({"engines":[{"id":"tiny-F-compact","source_sha256":sha(source)}]}).encode()
        frozen=directory/"frozen";frozen.mkdir();native=directory/"native";native.mkdir()
        files={"input-build.json":build,"main.c":source,"encode.py":b"encode helper",
               "rename_c.py":b"rename helper","pack_stream.py":b"stream helper",
               "compiler_group.py":b"compiler owner helper"}
        for name,data in files.items():(frozen/name).write_bytes(data)
        (frozen/"fixed-main.c").write_bytes(b"fixed source")
        for name in ("reference","fixed"):(native/(name+".elf")).write_bytes(b"native image")
        record={"input_hashes":{name:sha(data) for name,data in files.items()},"input_source_sha256":sha(source),
                "transformed_source_sha256":sha(b"fixed source"),"reference_native":{"sha256":sha(b"native image")},
                "actual_native":{"sha256":sha(b"native image")},"selected":{"path":str(directory/"packed/xz/x")}}
        path=directory/"results.json";path.write_text(json.dumps(record))
        return build,path,record

    def test_same_build_and_encoding_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            build,path,_=self.fixture(directory)
            self.assertTrue(qualify.admit_encoding(build,path)["frozen_inputs_verified"])

    def test_other_build_rejected_before_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            build,path,_=self.fixture(directory)
            with self.assertRaises(ValueError):qualify.admit_encoding(build+b" ",path)

    def test_other_source_rejected_before_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            build,path,record=self.fixture(directory);record["input_source_sha256"]=qualify.sha(b"other source")
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):qualify.admit_encoding(build,path)

    def test_frozen_input_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            build,path,_=self.fixture(directory);(path.parent/"frozen/main.c").write_bytes(b"drift")
            with self.assertRaises(ValueError):qualify.admit_encoding(build,path)

    def test_native_identity_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            build,path,_=self.fixture(directory);(path.parent/"native/fixed.elf").write_bytes(b"other image")
            with self.assertRaises(ValueError):qualify.admit_encoding(build,path)

    def test_unknown_input_and_outside_program_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            build,path,record=self.fixture(directory)
            record["input_hashes"]["unknown-input"]=qualify.sha(b"ignored")
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):qualify.admit_encoding(build,path)
            del record["input_hashes"]["unknown-input"]
            record["selected"]["path"]=str(path.parent.parent/"outside-program")
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):qualify.admit_encoding(build,path)


@unittest.skipUnless(sys.platform=="linux","Linux compiler ownership fixture")
class OwnedChildrenTests(unittest.TestCase):
    def test_separately_sessioned_orphan_is_terminated_and_reaped(self):
        with qualify.owned_children():
            script="import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True);print(p.pid,flush=True)"
            parent=subprocess.Popen([sys.executable,"-c",script],stdout=subprocess.PIPE,text=True)
            child=int(parent.stdout.readline());parent.stdout.close();parent.wait(timeout=3)
            self.assertTrue(Path("/proc",str(child)).exists())
        self.assertFalse(Path("/proc",str(child)).exists())
        self.assertEqual(qualify.descendants(os.getpid()),set())


if __name__=="__main__":unittest.main()
