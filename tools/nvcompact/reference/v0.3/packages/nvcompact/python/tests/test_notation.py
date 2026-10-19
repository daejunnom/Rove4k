"""Behavioral regressions for source spelling, types, token boundaries and compilers."""
import ast
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nvnotation as n


def variant(source, language="c", identifier="shortest", **kwargs):
    return next(v for v in n.generate_variants(source, language=language,
                token_contract="no-token-observation", **kwargs) if v["id"] == identifier)


class LiteralTests(unittest.TestCase):
    def test_integer_never_becomes_float_and_correct_exponent(self):
        for language in ("c", "cpp", "rust", "python"):
            integers = n.literal_candidates("100000", language=language)
            self.assertTrue(integers)
            self.assertNotIn("1e5", {c["spelling"] for c in integers})
            floats = n.literal_candidates("100000.0", language=language)
            self.assertEqual(floats[0]["spelling"], "1e5")
            self.assertNotIn("1e6", {c["spelling"] for c in floats})

    def test_lp64_base_and_suffix_preserve_distinct_types(self):
        self.assertNotIn("0x80000000", {x["spelling"] for x in n.literal_candidates("2147483648", language="c")})
        self.assertIn("0x80000000l", {x["spelling"] for x in n.literal_candidates("2147483648", language="c")})
        self.assertNotIn("2147483648", {x["spelling"] for x in n.literal_candidates("0x80000000", language="c")})
        self.assertEqual({x["proof"]["type"] for x in n.literal_candidates("1ll", language="c")}, {"long long"})
        self.assertEqual(n.literal_candidates("0b100", language="c"), [])
        self.assertTrue(n.literal_candidates("0b100", language="c", target="c23-lp64"))

    def test_rust_hex_digits_suffixes_and_tuple_indices(self):
        hex_digits = n.literal_candidates("0x01_f32", language="rust")
        self.assertEqual(hex_digits[0]["proof"]["value"], "7986")
        self.assertEqual(hex_digits[0]["proof"]["type"], "inferred integer")
        self.assertEqual(n.literal_candidates("100_000f32", language="rust")[0]["spelling"], "1e5f32")
        source = b"fn main(){let x=(1,2);let y=x.1;let z=0x00000001u32;}"
        out = variant(source, "rust")["data"]
        self.assertIn(b"x.1", out)
        self.assertIn(b"z=1u32", out)

    def test_macro_strings_and_unknown_suffixes_stay_opaque(self):
        source = b'#include <stdint.h>\n#define S(x) #x\nint n=000017; const char*s=S(000017);const char*t="000017";\n'
        output = variant(source)["data"]
        self.assertIn(b"n=15", output)
        self.assertIn(b"#define S(x) #x", output)
        self.assertIn(b"S(000017)", output)
        self.assertIn(b'"000017"', output)
        cpp = b'auto a=1000_tag;auto b=R"tag(100000.0 // text)tag";auto c=1\'000\'000;'
        output = variant(cpp, "cpp")["data"]
        self.assertIn(b"1000_tag", output)
        self.assertIn(b'R"tag(100000.0 // text)tag"', output)
        self.assertIn(b"c=0xf4240", output)
        rust = b'fn f(){ let s=stringify!(100_000); let x=100_000; }'
        self.assertIn(b"stringify!(100_000)", variant(rust, "rust")["data"])

    def test_token_joining_does_not_form_pp_numbers_or_comments(self):
        source = b"int f(int *p){int x=000016+2;return x/ *p + +x;}\n"
        output = variant(source, identifier="hex-compact", compact=True)["data"]
        self.assertNotIn(b"0xe+", output)
        self.assertNotIn(b"/*", output)
        self.assertNotIn(b"++", output)
        # Comments cannot concatenate identifiers; directives retain line boundaries.
        source = b"#define F 1\nint/**/value = 0x000f;\n"
        output = variant(source, compact=True, identifier="shortest-compact")["data"]
        self.assertIn(b"#define F 1\nint value=15;", output)

    def test_identity_contract_and_bounded_portfolio(self):
        source = b"int n=0x00000001;"
        self.assertEqual(n.generate_variants(source, language="c")[0]["data"], source)
        self.assertEqual(len(n.generate_variants(source, language="c")), 1)
        out = n.generate_variants(source * 50, language="c", token_contract="no-token-observation", compact=True, max_variants=3)
        self.assertEqual([v["id"] for v in out], ["raw", "shortest", "shortest-compact"])
        self.assertEqual(out[0]["data"], source * 50)
        with self.assertRaises(n.NotationError):
            n.generate_variants(source, language="c", compact="false")

    def test_python_ast_types_strings_and_execution(self):
        source = b'''# an ordinary comment\nx = 1_000_000\ny = 100000.0\ns = "\\x61\\x62\\x63"\nz = -0.0\nc = 100_000j\nresult = (x, y, s, z, c)\n'''
        result = variant(source, "python", compact=True, identifier="shortest-compact")
        output = result["data"]
        self.assertEqual(ast.dump(ast.parse(source), include_attributes=False), ast.dump(ast.parse(output), include_attributes=False))
        self.assertIn(b"1e5", output)
        self.assertIn(b"100_000j", output)
        self.assertLess(len(output), len(source))
        before, after = {}, {}
        exec(compile(source, "fixture", "exec"), before)
        exec(compile(output, "fixture", "exec"), after)
        self.assertEqual(before["result"], after["result"])

    def test_python_already_minified_layout_is_not_expanded(self):
        source = b"a=1;b=2\nx=[0 for _ in range(2)]\nresult=1 if x else(a+b,[i for i in range(3)])\n"
        output = variant(source, "python", compact=True, identifier="shortest-compact")["data"]
        self.assertEqual(output, source)
        # Minification is idempotent and cannot grow another spelling recipe's
        # source merely by restoring spaces around punctuation.
        variants = n.generate_variants(source, language="python", compact=True,
                                       token_contract="no-token-observation")
        by_id = {item["id"]: item["data"] for item in variants}
        for policy in n.POLICIES:
            self.assertLessEqual(len(by_id[policy + "-compact"]), len(by_id[policy]))
        # Python's tokenizer accepts number/keyword adjacency which its
        # compiler warns about. Do not create it under a -Werror launch.
        subprocess.run([sys.executable, "-Werror", "-c", output.decode()],
                       check=True, capture_output=True, timeout=5)

    def test_python_compaction_preserves_encoding_tabs_and_crlf(self):
        source = ("#!/usr/bin/env python3\r\n# coding: latin-1\r\n"
                  "def f(a, b):\r\n"
                  "\t# ordinary comment\r\n"
                  "\tif a is not None and b not in [1, 2]:\r\n"
                  "\t\treturn (a + b, '\u00e9#text') # inline comment\r\n"
                  "\treturn (0, '')\r\n"
                  "result = f(4, 3)\r\n").encode("latin-1")
        item = variant(source, "python", compact=True, identifier="shortest-compact")
        output = item["data"]
        self.assertTrue(output.startswith(source[:source.index(b"def ")]))
        self.assertNotIn(b"ordinary comment", output)
        self.assertNotIn(b"inline comment", output)
        self.assertIn(b"\t\treturn", output)
        self.assertIn(b"a is not None and b not in", output)
        self.assertEqual(output.count(b"\r\n"), source.count(b"\r\n"))
        self.assertEqual(ast.dump(ast.parse(source), include_attributes=False),
                         ast.dump(ast.parse(output), include_attributes=False))
        before, after = {}, {}
        exec(compile(source, "fixture", "exec"), before)
        exec(compile(output, "fixture", "exec"), after)
        self.assertEqual(before["result"], after["result"])
        self.assertLess(len(output), len(source))
        self.assertEqual(item["notes"], [])

    def test_python_token_boundaries_continuations_and_multiline_strings(self):
        source = (b"value = 1 \\\n    + 2\n"
                  b"body = '''one\ntwo\nthree\nfour\nfive\nsix\nseven\n'''\n"
                  b"empty = \"\"  \"\"\nattr = 1  .real\n"
                  b"result = (value, body, empty, attr, [x for x in [1, 2] if x not in []])\n")
        item = variant(source, "python", compact=True, identifier="shortest-compact")
        output = item["data"]
        self.assertIn(b"\\\n    +", output)
        self.assertIn(b'"" ""', output)  # not an unterminated triple quote
        self.assertIn(b"1 .real", output)  # not the different number token 1.
        self.assertEqual(output.count(b"\n"), source.count(b"\n"))
        self.assertEqual(ast.dump(ast.parse(source), include_attributes=False),
                         ast.dump(ast.parse(output), include_attributes=False))
        before, after = {}, {}
        exec(compile(source, "fixture", "exec"), before)
        exec(compile(output, "fixture", "exec"), after)
        self.assertEqual(before["result"], after["result"])
        self.assertEqual(item["notes"], [])

    def test_python_bom_and_formfeed_have_real_token_offsets(self):
        source = (b"\xef\xbb\xbf# coding: utf-8\r\n"
                  b"if True:\r\n\f    s='a\f\xe2\x98\x83';x=1_000_000 # remove\r\n"
                  b"result=(s,x)\r\n")
        item = variant(source, "python", compact=True, identifier="shortest-compact")
        output = item["data"]
        self.assertTrue(output.startswith(b"\xef\xbb\xbf# coding: utf-8\r\n"))
        self.assertIn(b"\r\n\f    s=", output)
        self.assertNotIn(b"1_000_000", output)
        self.assertNotIn(b"# remove", output)
        self.assertEqual(output.count(b"\r\n"), source.count(b"\r\n"))
        before, after = {}, {}
        exec(compile(source, "fixture", "exec"), before)
        exec(compile(output, "fixture", "exec"), after)
        self.assertEqual(before["result"], after["result"])
        self.assertEqual(item["notes"], [])


class CompilerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_all_c_integer_spelling_candidates_match_compiler_types(self):
        literals = ["0", "2147483648", "0x80000000", "0xffffffff", "0xffffffffffffffff",
                    "9223372036854775807ll", "0x000000ffUL", "123u", "000017"]
        assertions = []
        for literal in literals:
            for candidate in n.literal_candidates(literal, language="c"):
                other = candidate["spelling"]
                assertions.append(f'_Static_assert(__builtin_types_compatible_p(__typeof__({literal}),__typeof__({other})),"type");')
                assertions.append(f'_Static_assert(({literal})==({other}),"value");')
        with tempfile.TemporaryDirectory(prefix="nvnotation-c-types-") as tmp:
            src = Path(tmp) / "test.c"
            src.write_text("\n".join(assertions) + "\nint main(void){return 0;}\n")
            subprocess.run(["cc", "-std=c11", "-Werror", str(src), "-o", str(Path(tmp) / "test")], check=True, capture_output=True)
            subprocess.run([str(Path(tmp) / "test")], check=True, timeout=5)

    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_c_float_candidates_match_type_and_machine_bits(self):
        literals = ["100000.0", "0.000001", "0x1p-20", "1.00000011920928955078125f", "1e-45f", "1e-300"]
        checks = []
        for original in literals:
            for candidate in n.literal_candidates(original, language="c"):
                other = candidate["spelling"]
                checks.append(f'{{__typeof__({original}) a=({original}),b=({other});_Static_assert(__builtin_types_compatible_p(__typeof__({original}),__typeof__({other})),"type");if(memcmp(&a,&b,sizeof a))return 1;}}')
        with tempfile.TemporaryDirectory(prefix="nvnotation-c-float-") as tmp:
            src = Path(tmp) / "test.c"
            src.write_text("#include <string.h>\nint main(void){" + "".join(checks) + "return 0;}\n")
            subprocess.run(["cc", "-std=c11", "-Werror", str(src), "-o", str(Path(tmp) / "test")], check=True, capture_output=True)
            subprocess.run([str(Path(tmp) / "test")], check=True, timeout=5)

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler unavailable")
    def test_cpp_macro_raw_string_operator_and_literal_portfolio(self):
        source = b'''#include <cstring>\n#define S(x) #x\nconstexpr unsigned long long operator "" _tag(unsigned long long x){return x;}\nint main(){const char *a=S(1'000); const char*b=R"tag(100000.0 // text)tag";auto x=1'000'000;auto y=1000_tag;return not(x==1000000 and y==1000) || std::strcmp(a,"1'000") || std::strcmp(b,"100000.0 // text");}\n'''
        with tempfile.TemporaryDirectory(prefix="nvnotation-cpp-") as tmp:
            for item in n.generate_variants(source, language="cpp", token_contract="no-token-observation", compact=True):
                src = Path(tmp) / (item["id"] + ".cpp")
                exe = Path(tmp) / item["id"]
                src.write_bytes(item["data"])
                subprocess.run(["c++", "-std=c++17", "-Werror", str(src), "-o", str(exe)], check=True, capture_output=True)
                subprocess.run([str(exe)], check=True, timeout=5)

    def test_rust_portfolio_preserves_macro_tokens_and_float_inference(self):
        rustc = shutil.which("rustc") or "/tmp/nvcompact-rust-1.99.1/toolchain/bin/rustc"
        if not Path(rustc).exists():
            self.skipTest("Rust compiler unavailable")
        source = b'''#![allow(unused_variables)]\nmacro_rules! s {($x:tt) => {stringify!($x)}}\npub extern "C" fn answer()->u32{0x0000002a}\nfn main(){let a:u64=100_000;let b=100_000.0_f64;let c=0x01_f32;let t=(1,2);let x=t.1;assert_eq!(s!(100_000),"100_000");if a!=100000 || b.to_bits()!=100000.0f64.to_bits() || c!=7986 || x!=2 || answer()!=42{std::process::exit(1);}}\n'''
        with tempfile.TemporaryDirectory(prefix="nvnotation-rust-") as tmp:
            for item in n.generate_variants(source, language="rust", token_contract="no-token-observation", compact=True):
                src = Path(tmp) / (item["id"] + ".rs")
                exe = Path(tmp) / item["id"]
                src.write_bytes(item["data"])
                subprocess.run([rustc, "--edition=2021", "--crate-name", "fixture", str(src), "-o", str(exe)], check=True, capture_output=True)
                subprocess.run([str(exe)], check=True, timeout=5)


if __name__ == "__main__":
    unittest.main()
