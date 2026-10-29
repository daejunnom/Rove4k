#!/usr/bin/env python3
"""Focused source-shape checks for the one fixed ordering-policy overlay."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class Overlay(unittest.TestCase):
    def test_fixed_policy_and_rejections(self):
        g=load('order_generate',HERE/'generate.py')
        sample=(g.OLD+'\n'+g.VALUE+'\nscores[i]+=tiny_order(p,m);\n'
                'int evaluation=p->s*tiny_raw(p);\nint error=best-evaluation;').encode()
        self.assertEqual(g.overlay(sample,'control')[0],sample)
        changed,record=g.overlay(sample,'model')
        self.assertTrue(record['policy_change']);self.assertNotIn(g.OLD.encode(),changed)
        self.assertIn(b'#if DEV\nint value(',changed)
        self.assertIn(b'scores[i]+=tiny_order(p,m);',changed)
        for bad in (sample+g.OLD.encode(),sample.replace(b'tiny_order',b'other_order')):
            with self.assertRaises(ValueError):g.overlay(bad,'model')
        with self.assertRaises(ValueError):g.overlay(sample,'other')

if __name__=='__main__':unittest.main()
