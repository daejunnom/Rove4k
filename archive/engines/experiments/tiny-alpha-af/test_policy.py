#!/usr/bin/env python3
"""Bounded pure AF binding/opaque/freshness fixtures; no compiler or engine."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


policy=module('af_pure_policy',HERE/'policy.py')
lexer=module('af_pure_lexer',HERE/'control/engines/scripts/rename_c.py')
SOURCES=None


class PolicyTests(unittest.TestCase):
    def test_exact_AF_candidates_and_counts(self):
        fixed=json.loads(policy.POLICY_BYTES)
        for family in ('A','F'):
            before=(SOURCES/(family+'.c')).read_bytes()
            first,meta=policy.transform_source(before,family=family,lexer=lexer)
            second,again=policy.transform_source(before,family=family,lexer=lexer)
            self.assertEqual((first,meta),(second,again))
            self.assertEqual(policy.sha(first),fixed['families'][family]['candidate']['sha256'])
            self.assertEqual(meta['source_saved_bytes'],249 if family=='A' else 1506)
            self.assertEqual(meta['resource_saved_bytes'],0)
            self.assertEqual(before,(SOURCES/(family+'.c')).read_bytes())

    def test_modified_input_and_unknown_family_fail_closed(self):
        source=(SOURCES/'A.c').read_bytes()
        for candidate,family in ((source+b' ','A'),(source,'B')):
            with self.assertRaises(ValueError):policy.transform_source(candidate,family=family,lexer=lexer)

    def test_directive_literal_comment_and_splice_opaque(self):
        source=(b'#define KEEP score \\\n+score\n// score \\\n+score\n/* score */int score;'
                b'const char*s=u8"score\\\"";score=1;\n')
        after,counts,opaque=policy.reference._rewrite(source,{'score':'za'},lexer=lexer)
        self.assertEqual(counts['score'],2)
        self.assertEqual(after,source.replace(b'int score;',b'int za;').replace(b';score=1;',b';za=1;'))
        self.assertEqual(policy.reference._opaque_parts(after.decode()),opaque)

    def test_freshness_in_all_opaque_and_logical_regions(self):
        for part in (b'/* za */',b'puts("za");',b'#define KEEP za\n',b'puts("z\\\na");'):
            with self.assertRaisesRegex(ValueError,'not fresh'):
                policy.reference._rewrite(part+b'int score;',{'score':'za'},lexer=lexer)

    def test_injectivity_keyword_and_overlap(self):
        for mapping in ({'score':'za','depth':'za'},{'score':'for'},{'score':'depth','depth':'za'}):
            with self.assertRaises(ValueError):
                policy.reference._rewrite(b'int score,depth;',mapping,lexer=lexer)

    def test_role_and_resource_literal_boundaries(self):
        fixed=json.loads(policy.POLICY_BYTES);audit=json.loads((HERE/'ownership.json').read_text())
        roles=sum(audit['roles'].values(),[])
        self.assertEqual(len(roles),73);self.assertEqual(set(roles),set(fixed['mapping']))
        self.assertFalse(set(roles)&set(fixed['protected_shipping_names']))
        self.assertFalse(set(roles)&{'Move','clock','material','back','tv_sec','tv_nsec','main'})
        self.assertEqual(fixed['resource_literals'],{'WORKERS':'2','TT_BITS':'18','PLY':'128'})
        self.assertEqual(fixed['numeric_inverse_replacements'],0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sources',type=Path,required=True)
    args=parser.parse_args();SOURCES=args.sources
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
