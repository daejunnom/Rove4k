"""Pure fixed currentCE storage policy and full macro-record fixtures."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
policy=module('ce_test_policy',HERE/'policy.py')
lexer=module('ce_test_lexer',HERE/'control/engines/scripts/rename_c.py')
support=module('ce_test_support',HERE/'support.py')
SOURCES=None
class Tests(unittest.TestCase):
    def test_fixed_candidates_counts_and_reproduction(self):
        fixed=json.loads(policy.POLICY_BYTES)
        for family in ('C','E'):
            source=(SOURCES/(family+'.c')).read_bytes();first,meta=policy.transform_source(source,family=family,lexer=lexer)
            self.assertEqual((first,meta),policy.transform_source(source,family=family,lexer=lexer))
            self.assertEqual(policy.sha(first),fixed['families'][family]['candidate']['sha256'])
            self.assertEqual(meta['source_saved_bytes'],422 if family=='C' else 449)
            self.assertEqual(meta['mapping_used'],17);self.assertEqual(meta['resource_saved_bytes'],0)
            self.assertEqual(meta['preserved_PLY_code_uses'],12)
            self.assertEqual(source,(SOURCES/(family+'.c')).read_bytes())
    def test_modified_source_or_old_family_rejected(self):
        source=(SOURCES/'C.c').read_bytes()
        for data,family in ((source+b' ','C'),(source,'B')):
            with self.assertRaises(ValueError):policy.transform_source(data,family=family,lexer=lexer)
    def test_opaque_regions_and_splicing(self):
        source=b'#define KEEP score \\\n+score\n// score \\\n+score\n/* score */int score;const char*s=u8"score\\\"";score=1;\n'
        after,counts,opaque=policy.reference._rewrite(source,{'score':'za'},lexer=lexer)
        self.assertEqual(counts['score'],2)
        self.assertEqual(after,source.replace(b'int score;',b'int za;').replace(b';score=1;',b';za=1;'))
        self.assertEqual(policy.reference._opaque_parts(after.decode()),opaque)
    def test_alias_freshness_in_physical_and_logical_opaque(self):
        for part in (b'/* za */',b'puts("za");',b'#define KEEP za\n',b'puts("z\\\na");'):
            with self.assertRaisesRegex(ValueError,'not fresh'):policy.reference._rewrite(part+b'int score;',{'score':'za'},lexer=lexer)
    def test_mapping_injectivity_keywords_and_overlap(self):
        for mapping in ({'score':'za','depth':'za'},{'score':'for'},{'score':'depth','depth':'za'}):
            with self.assertRaises(ValueError):policy.reference._rewrite(b'int score,depth;',mapping,lexer=lexer)
    def test_roles_and_unused_slots(self):
        fixed=json.loads(policy.POLICY_BYTES);audit=json.loads((HERE/'ownership.json').read_text())
        roles=audit['external_linkage_same_TU_objects']+audit['file_static_objects']+audit['block_static_objects']
        self.assertEqual(len(roles),18);self.assertEqual(set(roles),set(fixed['mapping']))
        self.assertFalse(set(roles)&set(fixed['protected_shipping_names']))
        self.assertEqual(fixed['families']['C']['alpha_counts']['ready'],0)
        self.assertEqual(fixed['families']['E']['alpha_counts']['material'],0)
        self.assertEqual(fixed['resource_literals'],{});self.assertEqual(fixed['numeric_inverse_replacements'],0)
    def test_complete_macro_definitions_and_duplicate_order(self):
        raw=b' #define F(x) ((x)+\\\n1)\n#define Q "#define FAKE 4"\n#define DUP one\n#define DUP two\n#define DUP one\n'
        defs,counts,names=support.macro_records(raw,policy.reference)
        self.assertEqual(defs[0],b' #define F(x) ((x)+1)');self.assertEqual(len(defs),5)
        self.assertEqual(defs[1],b'#define Q "#define FAKE 4"');self.assertEqual(counts[b'#define DUP one'],2)
        changed=raw.replace(b'#define DUP one\n#define DUP two',b'#define DUP two\n#define DUP one',1)
        other,counter,byname=support.macro_records(changed,policy.reference)
        self.assertEqual(counter,counts);self.assertNotEqual(other,defs);self.assertNotEqual(byname,names)
        with self.assertRaises(ValueError):support.macro_records(b'int fake;\n'+raw,policy.reference)
    def test_resource_definition_multiplicity(self):
        raw=b'#define WORKERS 2\n#define TT_BITS 18\n#define PLY 128\n#define DEV 0\n'
        defs,_,_=support.macro_records(raw,policy.reference)
        self.assertEqual(support.resources(defs)['PLY'],['128'])
        with self.assertRaises(ValueError):support.resources(defs+[b'#define WORKERS 2'])
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sources',type=Path,required=True)
    args=parser.parse_args();SOURCES=args.sources
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
