"""Fixed-shape admission tests for the three-site state-only transform."""
import importlib.util
import copy
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

state=load("tiny_e_state_test_overlay",HERE/"generate.py")
producer=load("tiny_e_state_test_producer",HERE/"build.py")
ce=HERE.parents[1]/"compact/tiny-ce"
generate=load("tiny_e_state_test_base",ce/"generate.py")
stitch=load("tiny_e_state_test_stitch",ce.parent/"tiny-a/stitch.py")

class StateContract(unittest.TestCase):
    def source(self):
        names=("tiny.h","board.c","search.c","main.c")
        combined=stitch.stitch({n:(ce/"core"/n).read_bytes() for n in names},names,True)[0]
        return generate.overlay(combined,"E",(ce/"e-eval.c.in").read_bytes(),(ce/"frozen.json").read_bytes())[0]

    def test_three_sites_and_baseline_identity(self):
        base=self.source();self.assertEqual(state.overlay(base,"baseline")[0],base)
        result,record=state.overlay(base,"state");self.assertEqual(record["exact_overlay_sites"],3)
        for before,after in state.SITES:
            self.assertNotIn(before.encode(),result);self.assertEqual(result.count(after.encode()),1)
        self.assertIn(b"500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):",result)

    def test_missing_duplicate_or_new_consumers_rejected(self):
        base=self.source()
        wrong=[base.replace(state.SITES[0][0].encode(),b"typedef int Board;"),
               base+state.SITES[1][0].encode(),base+b"\nint new_reader(const Board *p){return p->v;}\n",
               base.replace(b"int error=best-evaluation;",b"int error=best;")]
        for source in wrong:
            with self.subTest(source=source[-80:]),self.assertRaises(ValueError):state.overlay(source,"state")
        with self.assertRaises(ValueError):state.overlay(base,"other")

    def test_verified_provenance_lf_and_crlf_preserve_raw_identity(self):
        name=producer.EOL_EQUIVALENT_INPUT
        expected=json.loads((HERE/"inputs.json").read_bytes())[name]
        lf=(ce/"core/provenance.json").read_bytes().replace(b"\r\n",b"\n")
        records=[producer.admit_input(name,data,expected) for data in (lf,lf.replace(b"\n",b"\r\n"))]
        self.assertEqual(records[0]["identity"],records[1]["identity"])
        self.assertEqual(records[0]["raw"]["bytes"],1462)
        self.assertEqual(records[1]["raw"]["bytes"],1503)
        self.assertEqual(records[0]["raw"]["crlf_count"],0)
        self.assertEqual(records[1]["raw"]["crlf_count"],41)
        self.assertNotEqual(records[0]["raw"]["sha256"],records[1]["raw"]["sha256"])

    def test_provenance_content_lone_cr_and_mixed_eol_rejected(self):
        name=producer.EOL_EQUIVALENT_INPUT
        expected=json.loads((HERE/"inputs.json").read_bytes())[name]
        lf=(ce/"core/provenance.json").read_bytes().replace(b"\r\n",b"\n")
        wrong=(lf.replace(b"TinyA",b"TinyZ",1),lf+b" ",lf.replace(b"\n",b"\r",1),lf.replace(b"\n",b"\r\n",1))
        for data in wrong:
            self.assertNotEqual(data,lf)
            with self.subTest(data=data[-50:]),self.assertRaises(ValueError):producer.admit_input(name,data,expected)
        with self.assertRaises(ValueError):producer.admit_input("other.json",lf,expected)
        literal=copy.deepcopy(expected);literal.pop("eol_equivalence")
        with self.assertRaises(ValueError):producer.admit_input(name,lf,literal)

    def test_other_bound_inputs_remain_literal(self):
        bindings=json.loads((HERE/"inputs.json").read_bytes())
        for name,expected in bindings.items():
            if name==producer.EOL_EQUIVALENT_INPUT:continue
            data=(HERE.parents[2]/producer.HISTORICAL_INPUTS.get(name,name)).read_bytes()
            self.assertEqual(producer.admit_input(name,data,expected)["admission"],"literal")
            with self.subTest(name=name),self.assertRaises(ValueError):producer.admit_input(name,data.replace(b"\n",b"\r\n"),expected)

if __name__=="__main__":unittest.main()
