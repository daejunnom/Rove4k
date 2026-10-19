"""Reachability safety boundaries for the optional structural source recipe."""
import unittest
from pathlib import Path
from generate import (functions,prune_sources,replace_function,prepare_sources,
                      specialize_shipping_operations)


class Reachability(unittest.TestCase):
    def retained(self, text):
        sources, removed = prune_sources({'c/x.c': text.encode()})
        return {row[0] for row in functions(sources['c/x.c'].decode())}, removed

    def test_calls_and_address_taken_callbacks(self):
        names, _ = self.retained('''
        int leaf(void){return 3;} int dead(void){return 4;}
        int callback(void){return leaf();}
        int invoke(int (*f)(void)){return f();}
        int main(void){return invoke(callback);}
        ''')
        self.assertEqual(names, {'leaf', 'callback', 'invoke', 'main'})

    def test_macro_and_global_function_addresses(self):
        names, _ = self.retained('''
        int through_macro(void); int through_global(void);
        #define CALL through_macro
        int (*saved)(void)=through_global;
        int through_macro(void){return 1;}
        int through_global(void){return 2;}
        int main(void){return CALL()+saved();}
        ''')
        self.assertEqual(names, {'through_macro', 'through_global', 'main'})

    def test_prototypes_and_literal_names_do_not_retain_dead_code(self):
        names, _ = self.retained('''
        int dead(void); int dead(void){return 2;}
        /* int fake(void) { return dead(); } */
        int main(void){const char *s="dead() } {";return s[0];}
        ''')
        self.assertEqual(names, {'main'})

    def test_pre_attribute_and_exact_replacement(self):
        text = '__attribute__((target("avx2"))) static int f(void){return 1;}\nint main(void){return f();}'
        result = replace_function(text, 'f', 'static int f(void){return 9;}')
        self.assertIn('return 9;', result)
        self.assertNotIn('__attribute__', result)
        self.assertIn('int main(void){return f();}', result)
        with self.assertRaises(ValueError):
            replace_function(text, 'missing', '')

    def test_unknown_post_attribute_is_rejected(self):
        with self.assertRaises(ValueError):
            functions('int f(void) __attribute__((noinline)) {return 1;}')


class Domains(unittest.TestCase):
    def setUp(self):
        directory=Path(__file__).resolve().parents[2]/'c'
        self.sources={'c/'+name:(directory/name).read_bytes()
                      for name in ('rove.h','board.c','search.c','main.c')}

    def test_shipping_mailbox_layout_only_A_without_model(self):
        for variant,model in (('A',True),('B',False),('C',False),('D',False),('E',False),('F',False)):
            sources,changes=prepare_sources(self.sources,variant=variant,model=model)
            self.assertIn('bb[2][7]',sources['c/rove.h'].decode())
            self.assertFalse(any(c.get('operation')=='A-mailbox-only-board-state' for c in changes))
        sources,changes=prepare_sources(self.sources,variant='A')
        self.assertIn('uint16_t half;',sources['c/rove.h'].decode())
        self.assertNotIn('bb[2][7]',sources['c/rove.h'].decode())
        self.assertTrue(any(c.get('operation')=='A-mailbox-only-board-state' for c in changes))

    def test_development_preserves_FEN_and_full_invariant_state(self):
        sources,changes=prepare_sources(self.sources,variant='A',development=True)
        self.assertIn('bb[2][7]',sources['c/rove.h'].decode())
        self.assertIn('board_fen',sources['c/board.c'].decode())
        self.assertNotIn('uint16_t half;',sources['c/rove.h'].decode())
        self.assertEqual(sources['c/main.c'],self.sources['c/main.c'])

    def test_other_scheduler_remains_canonical(self):
        sources,changes=prepare_sources(self.sources,variant='A',parallel=3)
        self.assertEqual(sources,self.sources)
        self.assertEqual(changes[0]['applied'],False)

    def test_halfmove_bound_admission(self):
        sources=dict(self.sources)
        sources['c/rove.h']=sources['c/rove.h'].replace(b'#define MAXHISTORY 4096',b'#define MAXHISTORY 65536')
        with self.assertRaisesRegex(ValueError,'halfmove'):
            prepare_sources(sources,variant='A')

    def test_CRLF_checkout_produces_same_C_source(self):
        lf={name:data.replace(b'\r\n',b'\n') for name,data in self.sources.items()}
        crlf={name:data.replace(b'\n',b'\r\n') for name,data in lf.items()}
        plain,_=prepare_sources(lf,variant='A')
        windows,changes=prepare_sources(crlf,variant='A')
        self.assertEqual(plain,windows)
        self.assertTrue(any(c.get('operation')=='physical-C-newline-normalization' for c in changes))

    def test_small_worker_rejects_unsupported_domains(self):
        for options in ({'small_worker':True},
                        {'compact_search':True,'small_worker':True,'development':True},
                        {'compact_search':True,'small_worker':True,'parallel':1}):
            with self.assertRaisesRegex(ValueError,'small worker'):
                prepare_sources(self.sources,variant='A',**options)

    def test_shipping_operations_require_qualified_shipping_layout(self):
        for options in ({'shipping_operations':True},
                        {'shipping_operations':True,'compact_search':True},
                        {'shipping_operations':True,'compact_search':True,'small_worker':True,'development':True},
                        {'shipping_operations':True,'compact_search':True,'small_worker':True,'parallel':1}):
            with self.assertRaises(ValueError):
                prepare_sources(self.sources,variant='A',**options)

    def test_post_operations_reject_development_and_unspecialized_C(self):
        for variant,development,parallel in (('A',True,0),('A',False,1),('Z',False,0)):
            with self.assertRaises(ValueError):
                specialize_shipping_operations({'c/main.c':b'int main(void){return 0;}'},
                    variant=variant,development=development,parallel=parallel)
        with self.assertRaisesRegex(ValueError,'translation units'):
            specialize_shipping_operations(self.sources,variant='A',development=False)
        with self.assertRaisesRegex(ValueError,'compiler-resolved'):
            specialize_shipping_operations({'c/main.c':b'#if ENABLED\nint main(void){return 0;}\n#endif\n'},
                                           variant='A',development=False)


if __name__ == '__main__':
    unittest.main()
