"""Independent byte checks for literal representation changes; no C compiler."""
import ast
import random
from types import SimpleNamespace
import unittest

from literal import canonical_literal, replace_literal, variants


FIXTURES = (
    ("empty", b""),
    ("ordinary-c", b"int main(void){return 0;}\n"),
    ("single-quote-end", b"x'"),
    ("double-quote-end", b'x"'),
    ("single-triple", b"/* ''' */\n"),
    ("double-triple", b'/* """ */\n'),
    ("both-triples", b'/* \'\'\' """ */\n'),
    ("lf", b"a\nb\n"),
    ("cr", b"a\rb\r"),
    ("crlf", b"a\r\nb\r\n"),
    ("nul", b"a\0b"),
    ("form-feed", b"a\fb"),
    ("vertical-tab", b"a\vb"),
    ("tab", b"a\tb"),
    ("del", b"a\x7fb"),
    ("invalid-utf8", b"\xff\xfe\x80"),
    ("truncated-utf8", b"\xed\x95"),
    ("utf8", "/* 한글 é */\n".encode("utf-8")),
    ("utf8-bom", b"\xef\xbb\xbfint x;\n"),
    ("slash-one", b"end\\"),
    ("slash-two", b"end\\\\"),
    ("slash-three", b"end\\\\\\"),
    ("slash-four", b"end\\\\\\\\"),
    ("c-escapes", b'const char*s="\\n\\r\\t\\x41\\u1234";\n'),
    ("c-continuation", b"#define F(x) \\\n+(x)\n"),
    ("shell-spelling", b'char*s="$(printf injected)";\n'),
    ("python-looking", b"# p.communicate(b'not a call')\n"),
    ("unicode-separators", "a\u2028b\u2029c".encode("utf-8")),
    ("two-single-quotes-end", b"x''"),
    ("two-double-quotes-end", b'x""'),
    ("long", b"int source_long_name;\n" * 256),
    ("every-byte", bytes(range(256))),
    ("mixed-boundaries", b"\r\n\0'''\\\n\xff\"\"\"\t"),
)


def independent_value(expression):
    node = ast.parse(expression, mode="eval")
    if isinstance(node.body, ast.Constant):
        return ast.literal_eval(node)
    return eval(compile(node, "<literal-test>", "eval"), {"__builtins__": {}})


class LiteralTests(unittest.TestCase):
    def test_all_33_boundary_fixtures_compile_to_exact_input_bytes(self):
        self.assertEqual(len(FIXTURES), 33)
        for label, source in FIXTURES:
            choices = variants(source)
            self.assertEqual(choices["canonical"], canonical_literal(source))
            self.assertIn("bytes-repr", choices)
            self.assertIn("bytes-triple-single", choices)
            self.assertIn("bytes-triple-double", choices)
            for name, expression in choices.items():
                with self.subTest(fixture=label, representation=name):
                    result = independent_value(expression)
                    self.assertIs(type(result), bytes)
                    self.assertEqual(result, source)
                    if name.startswith("bytes-triple"):
                        self.assertTrue(expression.isascii())
            if b"\r" in source or b"\0" in source:
                self.assertNotIn("raw-single", choices)
                self.assertNotIn("raw-double", choices)
            try:
                source.decode("utf-8")
            except UnicodeDecodeError:
                self.assertNotIn("str-repr-utf8", choices)
                self.assertNotIn("raw-single", choices)
                self.assertNotIn("raw-double", choices)
            else:
                self.assertIn("str-repr-utf8", choices)

    def test_seeded_arbitrary_bytes_are_exact_for_every_available_variant(self):
        rng = random.Random(20261020)
        for case in range(128):
            source = bytes(rng.randrange(256) for _ in range(rng.randrange(385)))
            for name, expression in variants(source).items():
                with self.subTest(case=case, representation=name):
                    self.assertEqual(independent_value(expression), source)

    def test_canonical_selection_matches_defined_producer_contract(self):
        self.assertEqual(canonical_literal(b"x\n"), "r'''x\n'''.encode()")
        self.assertTrue(canonical_literal(b"/* ''' */").startswith('r"""'))
        for source in (b'/* \'\'\' """ */', b"x\r\n", b"x\0", b"x\\", b"\xff"):
            self.assertEqual(canonical_literal(source), repr(source))

    def test_replacement_changes_only_argument_and_preserves_compiler_input(self):
        for label, source in FIXTURES:
            canonical = canonical_literal(source)
            # Same-line Unicode forces correct UTF-8 byte offsets. The quoted
            # preview and comment contain calls that must never be replaced.
            preview = repr("p.communicate(" + canonical + ")")
            prefix = ("preview=" + preview + "\n# p.communicate(b'comment')\nlabel='한글é'; ").encode("utf-8")
            suffix = b")\ntrailer='unchanged'\n"
            script = prefix + b"p.communicate(" + canonical.encode("utf-8") + suffix
            for name, expression in variants(source).items():
                with self.subTest(fixture=label, representation=name):
                    transformed = replace_literal(script, source, expression)
                    self.assertEqual(transformed, prefix + b"p.communicate(" + expression.encode("utf-8") + suffix)
                    received = []
                    namespace = {"p": SimpleNamespace(communicate=received.append), "__builtins__": {}}
                    exec(compile(transformed, "<literal-bootstrap-test>", "exec"), namespace)
                    self.assertEqual(received, [source])
                    self.assertEqual(namespace["trailer"], "unchanged")
            self.assertEqual(replace_literal(script, source, canonical), script)

    def test_replacement_handles_physical_crlf_and_cr_bootstrap_lines(self):
        source = "한글\n".encode("utf-8")
        canonical = canonical_literal(source).encode("utf-8")
        replacement = variants(source)["bytes-triple-double"]
        for newline in (b"\r\n", b"\r"):
            prefix = b"# header" + newline + "label='é'; ".encode("utf-8")
            script = prefix + b"p.communicate(" + canonical + b")" + newline
            expected = prefix + b"p.communicate(" + replacement.encode("utf-8") + b")" + newline
            self.assertEqual(replace_literal(script, source, replacement), expected)

    def test_replacement_fails_closed_on_missing_ambiguous_or_modified_calls(self):
        source = b"int x;\n"
        canonical = canonical_literal(source).encode("utf-8")
        call = b"p.communicate(" + canonical + b")\n"
        replacement = variants(source)["bytes-repr"]
        scripts = (
            b"# no active call\n",
            call + call,
            b"q.communicate(" + canonical + b")\n",
            b"p.communicate(" + canonical + b",timeout=1)\n",
            b"p.communicate(" + replacement.encode() + b")\n",
            b"broken (\n",
            b"\xff",
        )
        for script in scripts:
            with self.subTest(script=repr(script)):
                with self.assertRaises(ValueError):
                    replace_literal(script, source, replacement)
        with self.assertRaises(ValueError):
            replace_literal(call, source, "b'different source'")

    def test_replacement_rejects_executable_nonliteral_expressions(self):
        source = b"x"
        script = b"p.communicate(" + canonical_literal(source).encode() + b")\n"
        expressions = (
            "__import__('builtins').print('must not run')",
            "(lambda:b'x')()",
            "b'x'.decode().encode()",
            "'x'.encode('utf-8')",
            "'x'.__class__.encode('x')",
            "b'x'+b''",
            "'\\ud800'.encode()",
            "not valid Python!",
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    replace_literal(script, source, expression)
        with self.assertRaises(TypeError):
            variants(bytearray(b"x"))
        with self.assertRaises(TypeError):
            replace_literal("not bytes", source, "b'x'")
        with self.assertRaises(TypeError):
            replace_literal(script, source, b"b'x'")


if __name__ == "__main__":
    unittest.main()
