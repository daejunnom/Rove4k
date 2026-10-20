#!/usr/bin/env python3
"""Reject drift/invalid output boundaries before producing a candidate."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Composition(unittest.TestCase):
    def test_output_and_recipe_boundaries(self):
        b=load('compose_build',HERE/'build.py')
        for name in ('/absolute','../parent','a/../b','a\\b'):
            with self.assertRaises(ValueError):b.safe_relative(name)
        with tempfile.TemporaryDirectory(prefix='tiny-e-compose-boundary-') as d:
            checkout=Path(d)/'owned-checkout';checkout.mkdir();(checkout/'.git').write_text('fixture')
            link=Path(d)/'checkout-link';link.symlink_to(checkout,target_is_directory=True)
            forbidden=(Path('relative-output'),checkout/'never-created-output',Path(d),link/'never-created-output')
            for target in forbidden:
                with patch('sys.argv',['build.py','--out',str(target)]):
                    with self.assertRaises(ValueError):b.main()
            self.assertFalse((checkout/'never-created-output').exists())
    def test_independent_source_composition(self):
        root=HERE.parents[2];g=load('compose_generate',HERE/'generate.py')
        uci=load('compose_uci',root/'engines/experiments/tiny-uci-portfolio/transform.py')
        order=load('compose_order',root/'engines/experiments/tiny-e-order/generate.py')
        state=Path('/home/stemxstudio/rove4k-tiny-e-state-20261020-evidence/final2/state/original/main.c').read_bytes()
        minimal,_=uci.transform(state,'E');ordered,_=order.overlay(state,'model')
        final,proof=g.compose(state,ordered,minimal,order,uci)
        self.assertTrue(proof['independent_function_transplant_equal']);self.assertNotEqual(final,ordered)
        for a,b,c in ((state+b' ',ordered,minimal),(state,ordered+b' ',minimal),(state,ordered,minimal+b' ')):
            with self.assertRaises(ValueError):g.compose(a,b,c,order,uci)
        with self.assertRaises(ValueError):uci.region('int main(void){','int main(void){')

if __name__=='__main__':unittest.main()
