"""Small binding/capture fixtures for the one independent AST policy."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest

import rename

CONFIG = {}


class BindingTests(unittest.TestCase):
    def run_source(self, text, arguments=()):
        source = text.encode()
        candidate, meta = rename.rewrite(source, **CONFIG, arguments=['-std=c11', *arguments])
        self.assertEqual(rename.inverse(candidate, meta['edits']), source)
        self.assertTrue(meta['reparse_binding_graph_equal'])
        return candidate, meta

    def test_initializer_and_nested_shadow_identity(self):
        candidate, meta = self.run_source(
            'int shadow;int f(int argument){long shadow=sizeof shadow;'
            '{int argument=2;shadow+=argument;}return shadow+argument;}')
        self.assertIn(b'int shadow;', candidate)
        rows = meta['functions'][0]['declarations']
        self.assertEqual([r['old'] for r in rows].count('argument'), 2)
        self.assertEqual(len({r['new'] for r in rows}), len(rows))
        self.assertTrue(any(r['old'] == 'shadow' and r['occurrences'] == 4 for r in rows))

    def test_allocator_restarts_between_functions(self):
        _, meta = self.run_source('int f(int input_value){return input_value;}'
                                  'int g(int other_value){return other_value;}')
        a, b = [r['declarations'][0]['new'] for r in meta['functions']]
        self.assertEqual(a, b)

    def test_macro_expansion_keeps_affected_declaration(self):
        candidate, meta = self.run_source(
            '#define ID(x) (x)\nint f(int macro_value){int ordinary_value=1;'
            'return ID(macro_value)+ordinary_value;}')
        self.assertIn(b'ID(macro_value)', candidate)
        self.assertIn(b'int macro_value', candidate)
        self.assertTrue(meta['functions'][0]['skipped_declarations'])
        self.assertTrue(any(r['old'] == 'ordinary_value' for r in
                            meta['functions'][0]['declarations']))

    def test_static_type_member_and_string_are_unchanged(self):
        candidate, meta = self.run_source(
            'struct Cell{int member_value;};int global_value;'
            'int f(int argument){static int persistent_value;'
            'struct Cell local_cell={argument};const char *text_value="argument";'
            'return local_cell.member_value+persistent_value+global_value+text_value[0];}')
        for text in (b'member_value', b'persistent_value', b'global_value', b'"argument"'):
            self.assertIn(text, candidate)
        self.assertNotIn('persistent_value', [r['old'] for r in
                                           meta['functions'][0]['declarations']])

    def test_macro_name_even_after_undef_is_reserved(self):
        _, meta = self.run_source('#define a 1\n#undef a\nint f(int long_value){return long_value;}')
        self.assertIn('a', meta['macro_names'])
        self.assertNotEqual(meta['functions'][0]['declarations'][0]['new'], 'a')

    def test_macro_definition_after_shortened_function_has_stable_identity(self):
        candidate, meta = self.run_source(
            'int f(int long_value){return long_value;}\n'
            '#define LATE_LIMIT 7\n'
            'int g(int other_value){return other_value+LATE_LIMIT;}')
        self.assertIn(b'#define LATE_LIMIT 7\n', candidate)
        self.assertIn(b'+LATE_LIMIT;', candidate)
        self.assertEqual(meta['renamed_declarations'], 2)
        self.assertTrue(meta['reparse_binding_graph_equal'])

    def test_header_and_main_macro_with_same_name_keep_distinct_targets(self):
        with tempfile.TemporaryDirectory(prefix='rove-scope-fixture-') as directory:
            header = Path(directory) / 'outside.h'
            header.write_bytes(b'#define SAME_LIMIT 3\n')
            text = ('int f(int long_value){return long_value+SAME_LIMIT;}\n'
                    '#undef SAME_LIMIT\n#define SAME_LIMIT 7\n'
                    'int g(int other_value){return other_value+SAME_LIMIT;}')
            arguments = ['-include', str(header)]
            candidate, _ = self.run_source(text, arguments)
            self.assertIn(b'#undef SAME_LIMIT\n#define SAME_LIMIT 7\n', candidate)
            ci = rename.clang_api(CONFIG['clang_site'])
            tu, _, _ = rename.parse(ci, candidate, CONFIG['resource_dir'], ['-std=c11', *arguments])
            references = rename.snapshot(ci, tu)[3]
            macro_targets = [target[0] for kind, target in references
                             if kind == 'MACRO_INSTANTIATION']
            self.assertEqual(macro_targets, ['external', 'main'])

    def test_macro_shape_binds_exact_body_tokens(self):
        ci = rename.clang_api(CONFIG['clang_site'])
        shapes = []
        for value in (b'7', b'8'):
            source = b'#define LOCAL_TAG ' + value + b'\nint f(void){return LOCAL_TAG;}'
            tu, _, _ = rename.parse(ci, source, CONFIG['resource_dir'], ['-std=c11'])
            macro = next(shape for shape in rename.snapshot(ci, tu)[2]
                         if shape[0] == 'MACRO_DEFINITION')
            shapes.append(macro)
            self.assertIn(('LITERAL', value.decode()), macro[2])
        self.assertNotEqual(shapes[0], shapes[1])

    def test_asm_function_is_not_transformed(self):
        source = 'int f(int long_value){__asm__ volatile("" : : "r"(long_value));return long_value;}'
        candidate, meta = self.run_source(source)
        self.assertEqual(candidate, source.encode())
        self.assertEqual(meta['renamed_declarations'], 0)

    def test_bad_ast_and_phase_two_input_reject(self):
        for source in (b'int f( {', b'int f(int lo\\\nng){return long;}'):
            with self.assertRaises(rename.Rejected):
                rename.rewrite(source, **CONFIG, arguments=['-std=c11'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--clang-site', required=True)
    parser.add_argument('--resource-dir', required=True)
    args, rest = parser.parse_known_args()
    CONFIG.update(clang_site=args.clang_site, resource_dir=args.resource_dir)
    unittest.main(argv=['test_rename.py', *rest])
