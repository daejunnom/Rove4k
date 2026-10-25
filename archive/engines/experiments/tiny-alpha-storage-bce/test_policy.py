#!/usr/bin/env python3
"""Bounded pure fixed18 storage policy fixtures; no compiler or engine."""
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


policy=module('bce_pure_policy',HERE/'policy.py')
lexer=module('bce_pure_lexer',HERE/'control/engines/scripts/rename_c.py')
support=module('bce_pure_support',HERE/'support.py')
SOURCES=None


class PolicyTests(unittest.TestCase):
    def test_exact_storage_candidates_and_counts(self):
        fixed=json.loads(policy.POLICY_BYTES)
        for family in ('B','C','E'):
            before=(SOURCES/(family+'.c')).read_bytes()
            first,meta=policy.transform_source(before,family=family,lexer=lexer)
            second,again=policy.transform_source(before,family=family,lexer=lexer)
            self.assertEqual((first,meta),(second,again))
            self.assertEqual(policy.sha(first),fixed['families'][family]['candidate']['sha256'])
            self.assertEqual(meta['source_saved_bytes'],{'B':535,'C':461,'E':449}[family])
            self.assertEqual(meta['resource_saved_bytes'],0)
            self.assertEqual(meta['mapping_used'],17 if family=='E' else 18)
            self.assertEqual(meta['preserved_PLY_code_uses'],9 if family=='B' else 12)
            self.assertEqual(before,(SOURCES/(family+'.c')).read_bytes())

    def test_modified_input_and_unknown_family_fail_closed(self):
        source=(SOURCES/'B.c').read_bytes()
        for candidate,family in ((source+b' ','B'),(source,'A')):
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
        roles=audit['external_linkage_same_TU_objects']+audit['file_static_objects']+audit['block_static_objects']
        self.assertEqual(len(roles),18);self.assertEqual(set(roles),set(fixed['mapping']))
        self.assertFalse(set(roles)&set(fixed['protected_shipping_names']))
        self.assertFalse(set(roles)&{'Move','clock','tv_sec','tv_nsec','main','Board','Worker','history','continuation','correction'})
        self.assertEqual(fixed['resource_literals'],{})
        self.assertEqual(fixed['numeric_inverse_replacements'],0)
        self.assertEqual(fixed['families']['E']['alpha_counts']['material'],0)
        self.assertIn('not merged',audit['B_material_distinct_scopes'])

    def test_full_logical_macro_definitions_with_duplicates(self):
        raw=(b' #define F(x) ((x)+\\\n1)\n#define Q "#define FAKE 4"\n'
             b'#define DUP one\n#define DUP two\n#define DUP one\n')
        definitions,counts,names=support.macro_records(raw,policy.reference)
        self.assertEqual(definitions[0],b' #define F(x) ((x)+1)')
        self.assertEqual(definitions[1],b'#define Q "#define FAKE 4"')
        self.assertEqual(len(definitions),5)
        self.assertEqual(counts[b'#define DUP one'],2)
        self.assertEqual(names['DUP'],[b'#define DUP one',b'#define DUP two',b'#define DUP one'])
        changed=raw.replace(b'#define DUP one\n#define DUP two',b'#define DUP two\n#define DUP one',1)
        other,other_counts,other_names=support.macro_records(changed,policy.reference)
        self.assertEqual(counts,other_counts)
        self.assertNotEqual(definitions,other)
        self.assertNotEqual(names,other_names)
        with self.assertRaises(ValueError):support.macro_records(b'int fake;\n'+raw,policy.reference)

    def test_resource_macro_multiplicity_is_not_collapsed(self):
        raw=b'#define WORKERS 2\n#define TT_BITS 18\n#define PLY 128\n#define DEV 0\n'
        definitions,_,_=support.macro_records(raw,policy.reference)
        self.assertEqual(support.resources(definitions)['WORKERS'],['2'])
        with self.assertRaises(ValueError):support.resources(definitions+[b'#define WORKERS 2'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sources',type=Path,required=True)
    args=parser.parse_args();SOURCES=args.sources
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
