"""Reachability safety boundaries for the optional structural source recipe."""
import unittest
from generate import functions, prune_sources, replace_function


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


if __name__ == '__main__':
    unittest.main()
