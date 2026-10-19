"""Behavioral checks for guarded C rewrites; no engine or high-memory runs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nvcflow

CLANG = os.environ.get("NVCOMPACT_CLANG") or shutil.which("clang") or shutil.which("clang-20")
GCC = shutil.which("gcc")

SEMANTICS = br'''
#include <stdio.h>
static int trace;
static int event(int n) { trace = trace * 10 + n; return n; }
static int choose(int c) { if(event(c)) { return event(2); } else { return event(3); } }
static int assign(int c) { int x; if(event(c)) x=event(4); else x=event(5); return x; }
static void effect(int c) { if(event(c)) event(6); else event(7); }
static void guard(int c) { if(event(c)) { event(8); } }
static unsigned long mixed(int c) { if(c) return -1; else return 1U; }
static unsigned long naive(int c) { return c ? -1 : 1U; }
static int arithmetic(int n) { int x=3; x=x+n; x*=2; x+=1; x-=1; return x; }
static int tail(int c, int n) { if(c) return n+2; return n-2; }
static int boolean(int x) { return x?1:0; }
static unsigned int ub(boolean_unused) ;
static unsigned int typed(int x) { return (x?1U:0U)+0xffffffffU; }
static int negated(int a, int b) { return !(a<b)+!(a==b); }
static int demorgan(int c) { int a=!(event(c) && event(2)); int b=!(event(c) || event(3)); return a+b; }
static int normalized(int a, int b) { return !!(a<b) + ((a==b)?1:0); }
static int loops(int x) {
 int sum=0;
 while(1) { if(x==0) { break; } if(x%2) { sum=sum+x; } x-=1; }
 do { sum+=1; } while(0);
 for(int i=0;!!i<0;i+=1) { sum+=1; }
 return sum;
}
static int nested(int a,int b) { int x=0; if(a) { if(b) {x=1;} else {x=2;} } else {x=3;} return x; }
static int punctuation(int c,int x) { if(c) {x+=1;} else {x-=1;} return x; }
static const int *ptr(int c, const int *a, const int *b) {if(c)return a;else return b;}
static double nan_input(void) { return __builtin_nan(""); }
static int nan_case(double x) { return !(x<0); }
static volatile int watched;
static int volatile_case(int c) { if(c) { watched=watched+1; } return watched; }
static _Atomic int atomic_counter;
static int atomic_case(int c) { if(c) {atomic_counter=atomic_counter+1;} return atomic_counter; }
static int twice(int x) __attribute__((returns_twice));
static int twice(int x) { return x; }
static int context(int c) { if(twice(c)) return 1; else return 2; }
static int indirect(int (*fn)(int), int c) { if(fn(c)) return 1; else return 2; }
static int generic(int x) { if(x) return _Generic(x,int:3,default:4); else return 5; }
static int size_context(int x) { if(x) return sizeof(x?1U:0U); else return sizeof(x); }
#define SPELL(x) #x
#define ADD(x) ((x)+1)
static const char *spelling(void) { return SPELL(100000); }
static int macro_case(int c) { if(c) return ADD(4); else return 2; }
struct item { int value; };
static int lifetime(int c) { if(c) { return ((struct item){5}).value; } else { return 2; } }
int main(void) {
 int a=41,b=43;
 for(int c=0;c<2;++c) {
  trace=0; int r=choose(c); printf("choose %d %d\n",r,trace);
  trace=0; r=assign(c); printf("assign %d %d\n",r,trace);
  trace=0; effect(c); printf("effect %d\n",trace);
  trace=0; guard(c); printf("guard %d\n",trace);
  trace=0; r=demorgan(c); printf("demorgan %d %d\n",r,trace);
  printf("mixed %lu naive %lu\n",mixed(c),naive(c));
  printf("ptr %d nested %d %d\n",*ptr(c,&a,&b),nested(c,0),nested(c,1));
  printf("protected %d %d %d %d %d %s\n",volatile_case(c),atomic_case(c),context(c),macro_case(c),lifetime(c),spelling());
  printf("contexts %d %d %d\n",indirect(twice,c),generic(c),size_context(c));
 }
 for(int n=0;n<8;++n) printf("n %d %d %d %u %d %d %d %d\n",arithmetic(n),tail(n%2,n),boolean(n),typed(n),negated(n,3),loops(n),punctuation(n%2,n),normalized(n,3));
 printf("nan %d %d\n",nan_case(nan_input()),nan_input()>=0);
 return 0;
}
'''.replace(b'static unsigned int ub(boolean_unused) ;\n', b'')


def execute_c(source, compiler, optimization, directory, identifier):
    path = directory / (identifier + ".c")
    binary = directory / identifier
    path.write_bytes(source)
    built = subprocess.run([compiler, "-std=c11", optimization, str(path), "-o", str(binary)],
                           capture_output=True, timeout=20)
    if built.returncode:
        raise AssertionError(built.stderr.decode("utf-8", "replace"))
    result = subprocess.run([str(binary)], capture_output=True, timeout=5)
    return result.returncode, result.stdout, result.stderr


class ContractTests(unittest.TestCase):
    def test_opaque_identity_never_requires_frontend(self):
        source = b"not even parsed C\n"
        result = nvcflow.generate_variants(source, clang="/missing/clang")
        self.assertEqual([x["data"] for x in result], [source])
        self.assertIn("identity", result[0]["notes"][0])

    def test_invalid_frontend_contract_fails_explicitly(self):
        with self.assertRaises(nvcflow.FlowError):
            nvcflow.generate_variants(b"int x;", compiler_args=["-Xclang", "-load"])
        with self.assertRaises(nvcflow.FlowError):
            nvcflow.generate_variants(b"int x;", token_contract="no-token-observation", clang="/missing/clang")
        with self.assertRaises(nvcflow.FlowError):
            nvcflow.generate_variants(b"int x;", max_passes=0)

    def test_default_output_preserves_opaque_source_without_clang(self):
        with tempfile.TemporaryDirectory(prefix="nvcflow-opaque-") as temp:
            directory = Path(temp)
            source, output = directory / "input.c", directory / "output.c"
            source.write_bytes(b"int f(int c){if(c)return 2;else return 3;}\n")
            self.assertEqual(nvcflow.main([str(source), "--output", str(output), "--clang", "/missing/clang"]), 0)
            self.assertEqual(output.read_bytes(), source.read_bytes())
            self.assertEqual(nvcflow.main([str(source), "--output", str(directory / "explicit.c"),
                "--variant", "c-all", "--clang", "/missing/clang"]), 2)

    def test_unsupported_identifier_spelling_is_identity_not_a_splice(self):
        for name in (br"\u03b1", b"$name", "π".encode()):
            source = b"int " + name + b",else" + name + b";void f(int c){if(c){" + name + b"=2;}else{" + name + b"=3;}}int main(void){f(0);return " + name + b";}"
            variants = nvcflow.generate_variants(source, clang="/missing/clang", token_contract="no-token-observation")
            self.assertEqual([v["data"] for v in variants], [source])
            self.assertIn("unsupported preprocessing token", variants[0]["notes"][0])


@unittest.skipUnless(CLANG, "optional Clang unavailable; set NVCOMPACT_CLANG to enable semantic C tests")
class SemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.variants = nvcflow.generate_variants(SEMANTICS, clang=CLANG, token_contract="no-token-observation")

    def test_all_unique_candidates_preserve_outputs_and_effect_order(self):
        unique = {v["sha256"]: v for v in self.variants}.values()
        with tempfile.TemporaryDirectory(prefix="nvcflow-semantic-") as temp:
            directory = Path(temp)
            for compiler in dict.fromkeys(c for c in (GCC, CLANG) if c):
                baseline = execute_c(SEMANTICS, compiler, "-Os", directory, "baseline")
                self.assertEqual((baseline[0], baseline[2]), (0, b""))
                self.assertIn(b"nan 1 0\n", baseline[1])
                self.assertIn(b"choose 3 3\n", baseline[1])
                self.assertIn(b"choose 2 12\n", baseline[1])
                self.assertIn(b"effect 16\n", baseline[1])
                self.assertIn(b"guard 18\n", baseline[1])
                for candidate in unique:
                    with self.subTest(compiler=compiler, recipe=candidate["id"]):
                        actual = execute_c(candidate["data"], compiler, "-Os", directory, candidate["id"])
                        self.assertEqual(actual, baseline)
                combined = next(v for v in self.variants if v["id"] == "c-all")
                self.assertEqual(execute_c(combined["data"], compiler, "-O0", directory, "combined-o0"),
                                 execute_c(SEMANTICS, compiler, "-O0", directory, "baseline-o0"))
        self.assertLess(min(v["bytes"] for v in self.variants), len(SEMANTICS))

    def test_sensitive_functions_and_source_types_are_protected(self):
        protected = {"mixed", "volatile_case", "atomic_case", "context", "indirect", "generic", "size_context", "macro_case", "spelling", "lifetime"}
        # Mixed signed/unsigned returns may still have lexical brace edits; the
        # forbidden event is merging their contextual conversions into ?:.
        for variant in self.variants:
            for record in variant["audit"]:
                if record["function"] == "mixed":
                    self.assertNotIn(record["rule"], ("if-return", "return-tail"))
                elif record["function"] in protected:
                    self.fail(f"context-sensitive function rewritten: {record}")
        direct = b"int setjmp(void*);int f(void*p){if(setjmp(p))return 1;else return 0;}"
        result = nvcflow.generate_variants(direct, clang=CLANG, token_contract="no-token-observation")
        self.assertTrue(all(v["data"] == direct for v in result))

    def test_macro_introduced_by_loop_keyword_is_not_accepted(self):
        source = b"#define for(...) if(0)\nint f(void){int x=0;while(1){x=3;break;}return x;}\n#undef for\n"
        variants = nvcflow.generate_variants(source, clang=CLANG, token_contract="no-token-observation")
        with tempfile.TemporaryDirectory(prefix="nvcflow-macro-") as temp:
            root = Path(temp)
            baseline = execute_c(source + b"int main(void){return f()!=3;}\n", CLANG, "-O0", root, "raw")
            for variant in variants:
                self.assertEqual(execute_c(variant["data"] + b"int main(void){return f()!=3;}\n", CLANG, "-O0", root, variant["id"]), baseline)

    def test_preprocessor_effects_missing_from_ast_remain_in_source(self):
        with tempfile.TemporaryDirectory(prefix="nvcflow-pragma-") as temp:
            root = Path(temp)
            header = root / "effect.h"
            header.write_text('#define EFFECT _Pragma("pack(1)")\n#define ALIAS EFFECT\n')
            for prefix, effect in ((b"", b'_Pragma("pack(1)")'),
                                   (b'#include "effect.h"\n', b"ALIAS"),
                                   ('#define π _Pragma("pack(1)")\n'.encode(), "π".encode())):
                source = prefix + b"int x;void f(int c){if(c){" + effect + b" x=2;}}struct S{char a;int b;};int main(void){return sizeof(struct S);}"
                path = root / "original.c"
                path.write_bytes(source)
                variants = nvcflow.generate_variants(source, clang=CLANG, source_path=path,
                    token_contract="no-token-observation")
                baseline = execute_c(source, CLANG, "-O0", root, "original")
                self.assertEqual(baseline[0], 5)
                for variant in variants:
                    self.assertFalse(any(record["function"] == "f" for record in variant["audit"]))
                    self.assertEqual(execute_c(variant["data"], CLANG, "-O0", root, variant["id"]), baseline)

    def test_ucn_and_ordinary_string_escapes_keep_their_runtime_behavior(self):
        ucn = br'int \u03b1,else\u03b1;void f(int c){if(c){\u03b1=2;}else{\u03b1=3;}}int main(void){f(0);return \u03b1;}'
        quoted = br'int f(int c){if(c){return "\u03b1"[0];}else{return "\u03b1"[0];}}int main(void){return f(0)!=f(1);}'
        with tempfile.TemporaryDirectory(prefix="nvcflow-tokens-") as temp:
            root = Path(temp)
            for source in (ucn, quoted):
                variants = nvcflow.generate_variants(source, clang=CLANG, token_contract="no-token-observation")
                baseline = execute_c(source, CLANG, "-O0", root, "baseline")
                for variant in variants:
                    self.assertEqual(execute_c(variant["data"], CLANG, "-O0", root, variant["id"]), baseline)
                if source == quoted:
                    self.assertLess(min(v["bytes"] for v in variants), len(source))

    def test_manifest_retains_raw_and_real_program_verifier(self):
        example = Path(__file__).resolve().parents[2] / "examples" / "c-rewrites"
        variants = nvcflow.generate_variants((example / "program.c").read_bytes(), clang=CLANG,
            source_path=example / "program.c", token_contract="no-token-observation", max_variants=3)
        with tempfile.TemporaryDirectory(prefix="nvcflow-manifest-") as temp:
            output = Path(temp) / "portfolio"
            nvcflow.write_portfolio(output, variants)
            path = nvcflow.write_run_manifest(output, variants, verifier=example / "verify.py",
                target="x86_64-unknown-linux-gnu", contract="16 documented integer rows; no self-file/path observation", codecs=["gzip-9"])
            manifest = json.loads(path.read_text())
            self.assertEqual(manifest["baseline"]["variants"]["program"], "raw")
            self.assertEqual(manifest["components"][0]["variants"][0]["sources"], ["raw.c"])
            self.assertEqual((output / "verify.py").read_bytes(), (example / "verify.py").read_bytes())
            self.assertTrue(all((output / p).is_file() for p in manifest["inputs"]))
            with self.assertRaises(FileExistsError):
                nvcflow.write_portfolio(output, variants)


if __name__ == "__main__":
    unittest.main()
