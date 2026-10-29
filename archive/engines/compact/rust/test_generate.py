"""Behavioral boundaries for the guarded Rust shipping-source transformation.

Compiler fixtures use tiny independent programs, with expected output derived
from Rust evaluation order. They do not claim proc-macro span/stringify!
preservation or general name resolution for the canonical-only specializer.
Temporary sources and executables are always outside the checkout.
"""

if __name__ == "__main__":
    raise SystemExit("Rove4k Rust engine paths are retired; use C A-F")

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent.parent
CONFIGURATION = {
    "ROVE_VARIANT": "A", "ROVE_DEV": "0", "ROVE_PARALLEL": "0",
    "ROVE_MODEL": "0", "ROVE_HQ": "0", "ROVE_WORKERS": "1",
    "ROVE_TT_BITS": "8", "ROVE_F_SINGLE": "0", "ROVE_F_PARITY": "0",
}
RUSTC = shutil.which(os.environ.get("RUSTC", "rustc"))


def module(name):
    """Avoid the sibling C generator's identical basename during discovery."""
    key = "rove_compact_rust_" + name
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, HERE / (name + ".py"))
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[key] = loaded
        sys.path.insert(0, str(HERE))
        try:
            spec.loader.exec_module(loaded)
        finally:
            sys.path.pop(0)
    return sys.modules[key]


def canonical_sources():
    names = ("rust/main.rs", "rust/board.rs", "rust/eval.rs",
             "rust/search.rs", "rust/parallel.rs", "rust/pool.rs",
             "model/frozen.rs")
    return {name: (ENGINE_ROOT / name).read_bytes() for name in names}


LEXICAL = r'''#![allow(dead_code)]
/// A doc comment must not consume the next function after rendering.
fn echo<'a>(s: &'a str) -> &'a str { s }
fn main() {
    /* outer { /* nested " } */ } */
    let raw = r###"if DEV { panic!("bad") } /* raw */ 'x' "##"###;
    let bytes = br##"/* bytes */ } "#"##;
    let value = 8 / * &2;
    let mut range = 0;
    'outer: for n in 0..=4 {
        if n == 3 { break 'outer; }
        range += n;
    }
    let r#type = 7u8;
    println!("{}:{}:{}:{}:{}:{}:{}:{}:{}",
             echo("ok"), '\'' as u32, b'/' as u32, 'λ' as u32,
             raw.contains("/* raw */"), value, range, r#type, bytes[0]);
}
'''

NAMESPACES = r'''#![allow(dead_code, non_snake_case)]
const DEV: bool = false;
mod other { pub const DEV: bool = true; }
struct Gate { DEV: bool }
impl Gate { fn DEV(&self) -> bool { self.DEV } }
fn choose() -> u8 { 99 }
struct Probe;
impl Probe { fn choose(&self) -> u8 { 7 } }
fn main() {
    const DEV: bool = true;
    let gate = Gate { DEV: true };
    if gate.DEV() { print!("m"); }
    if gate.DEV { print!("f"); }
    if DEV { print!("L"); }
    if crate::DEV { print!("bad"); }
    if other::DEV { print!("M"); }
    println!(":{}", Probe.choose());
}
'''

KNOWN_BRANCHES = r'''const DEV: bool = false;
const VARIANT: u8 = b'A';
fn main() {
    let value = if crate::DEV { panic!("dead-development-branch") }
                else if crate::VARIANT == b'A' {
                    if !crate::DEV { 7 } else { panic!("dead-nested-branch") }
                } else { panic!("dead-variant-branch") };
    let mut scoped = 3;
    if !crate::DEV { let scoped = 9; print!("{scoped}:"); }
    scoped += value;
    println!("{scoped}");
}
'''

IF_LET = r'''const DEV: bool = false;
fn main() {
    let value = if crate::DEV { 0 }
                else if let Some(n) = Some(7) { n + 1 } else { 9 };
    let mut pending = Some(3);
    let mut total = 0;
    while let Some(n) = pending { total += n; pending = None; }
    println!("{value}:{total}");
}
'''

EFFECTS = r'''const DEV: bool = false;
fn hit(n: &mut u8) -> bool { *n += 1; true }
fn main() {
    let mut n = 0;
    if hit(&mut n) && crate::DEV { panic!("false"); }
    if crate::DEV && hit(&mut n) { panic!("false"); }
    if hit(&mut n) || !crate::DEV { print!("a"); }
    if !crate::DEV || hit(&mut n) { print!("b"); }
    println!("{n}");
}
'''

BLOCK_CONDITIONS = r'''const DEV: bool = false;
fn main() {
    let mut n = 0;
    if crate::DEV && { n += 1; true } { panic!("dead body"); }
    if !crate::DEV || { n += 1; false } { print!("yes:"); }
    if crate::DEV && unsafe { n += 1; true } { panic!("dead unsafe body"); }
    println!("{n}");
}
'''

DEREF_EFFECTS = r'''use std::ops::Deref;
use std::sync::atomic::{AtomicUsize, Ordering};
const DEV: bool = false;
static HITS: AtomicUsize = AtomicUsize::new(0);
struct Flag { flag: bool }
struct Wrapped(Flag);
impl Deref for Wrapped {
    type Target = Flag;
    fn deref(&self) -> &Flag {
        HITS.fetch_add(1, Ordering::SeqCst);
        &self.0
    }
}
fn main() {
    let wrapped = Wrapped(Flag { flag: true });
    if wrapped.flag && crate::DEV { panic!("false"); }
    if crate::DEV && wrapped.flag { panic!("false"); }
    if wrapped.flag || !crate::DEV { print!("a"); }
    if !crate::DEV || wrapped.flag { print!("b"); }
    println!("{}", HITS.load(Ordering::SeqCst));
}
'''

RETURN_CONDITION = r'''const DEV: bool = false;
fn choose() -> bool {
    if (return true) && crate::DEV { panic!("dead"); }
    false
}
fn main() { println!("{}", choose()); }
'''

MATCH_GUARDS = r'''const DEV: bool = false;
const VARIANT: u8 = b'A';
fn hit(n: &mut u8) -> bool { *n += 1; true }
fn main() {
    let mut n = 0;
    let a = match crate::VARIANT {
        b'B' => panic!("unreachable B"),
        b'A' if hit(&mut n) && crate::DEV => 1,
        b'A' => 2,
        _ => 3,
    };
    let b = match crate::VARIANT {
        b'A' if hit(&mut n) => 4,
        _ => 5,
    };
    println!("{a}:{b}:{n}");
}
'''


class CompilerFixture(unittest.TestCase):
    def compare_program(self, original, transformed, expected):
        if not RUSTC:
            self.skipTest("rustc is required for independent execution fixtures")
        environment = os.environ.copy()
        environment.update(CONFIGURATION)
        with tempfile.TemporaryDirectory(prefix="rove-rust-transform-") as temp:
            root = Path(temp)
            for name, source in (("original", original), ("transformed", transformed)):
                with self.subTest(program=name):
                    path = root / (name + ".rs")
                    path.write_text(source, encoding="utf-8", newline="\n")
                    executable = root / (name + (".exe" if os.name == "nt" else ""))
                    compiled = subprocess.run(
                        [RUSTC, "--edition=2024", "-Awarnings", str(path), "-o", str(executable)],
                        capture_output=True, text=True, env=environment, timeout=30)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr + "\n" + source)
                    ran = subprocess.run([str(executable)], capture_output=True,
                                         text=True, timeout=5)
                    self.assertEqual(ran.returncode, 0, ran.stderr)
                    self.assertEqual(ran.stdout, expected)


class LexicalBoundaries(CompilerFixture):
    def test_chars_lifetimes_literals_comments_and_punctuation_execute(self):
        syntax = module("syntax")
        tokens = syntax.tokenize(LEXICAL)
        rendered = syntax.render(tokens)
        self.assertEqual(syntax.tokenize(rendered), tokens)
        self.compare_program(LEXICAL, rendered, "ok:39:47:955:true:4:3:7:47\n")

    def test_namespaces_fields_methods_and_shadowing_roundtrip(self):
        syntax = module("syntax")
        rendered = syntax.render(syntax.tokenize(NAMESPACES))
        self.compare_program(NAMESPACES, rendered, "mfLM:7\n")

    def test_balanced_delimiters_ignore_literal_and_comment_contents(self):
        syntax = module("syntax")
        tokens = syntax.tokenize('#[allow(unused)] fn f(){let s=r#"}])"#;/* [ */(1,[2])}')
        for index, token in enumerate(tokens):
            if token in ("(", "[", "{", ")", "]", "}"):
                other = syntax.matching(tokens, index)
                self.assertEqual(syntax.matching(tokens, other), index)

    def test_malformed_lexical_inputs_are_rejected(self):
        syntax = module("syntax")
        for source in ('/* outer /* inner */', 'r##"missing"#', '"missing'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "unterminated"):
                syntax.tokenize(source)
        for tokens in (("(", "[", ")", "]"), ("{", "x")):
            with self.subTest(tokens=tokens), self.assertRaises(ValueError):
                syntax.matching(list(tokens), 0)


class ConditionalSemantics(CompilerFixture):
    def specialize(self, source):
        # The fixture constants are explicitly unshadowed. Namespace/shadowing
        # preservation above is a lexical contract, not a scope resolver claim.
        return module("generate").specialize_text(
            source, constants={"DEV": False, "crate::DEV": False,
                               "VARIANT": ord("A"), "crate::VARIANT": ord("A")})

    def test_known_conditions_remove_dead_code_but_keep_expression_and_scope(self):
        result = self.specialize(KNOWN_BRANCHES)
        self.assertNotIn("dead-development-branch", result)
        self.assertNotIn("dead-nested-branch", result)
        self.assertNotIn("dead-variant-branch", result)
        self.compare_program(KNOWN_BRANCHES, result, "9:10\n")

    def test_if_let_and_while_let_remain_valid(self):
        self.compare_program(IF_LET, self.specialize(IF_LET), "8:3\n")

    def test_short_circuit_folding_preserves_left_to_right_effects(self):
        self.compare_program(EFFECTS, self.specialize(EFFECTS), "ab2\n")

    def test_condition_blocks_are_not_mistaken_for_the_if_body(self):
        self.compare_program(BLOCK_CONDITIONS, self.specialize(BLOCK_CONDITIONS), "yes:0\n")

    def test_field_autoderef_effects_are_not_erased_by_known_rhs(self):
        self.compare_program(DEREF_EFFECTS, self.specialize(DEREF_EFFECTS), "ab2\n")

    def test_return_inside_condition_is_not_a_pure_unknown_value(self):
        self.compare_program(RETURN_CONDITION, self.specialize(RETURN_CONDITION), "true\n")

    def test_match_arm_and_guard_evaluation_is_preserved(self):
        self.compare_program(MATCH_GUARDS, self.specialize(MATCH_GUARDS), "2:4:2\n")


class ProducerGuards(unittest.TestCase):
    def test_configuration_outside_bound_shipping_domain_is_rejected(self):
        generate = module("generate")
        files = canonical_sources()
        cases = [("ROVE_VARIANT", variant) for variant in "BCDEF"]
        cases += [(name, "1") for name in ("ROVE_DEV", "ROVE_PARALLEL",
                  "ROVE_MODEL", "ROVE_HQ", "ROVE_F_SINGLE", "ROVE_F_PARITY")]
        cases += [("ROVE_WORKERS", value) for value in ("0", "513", "2x")]
        cases += [("ROVE_TT_BITS", value) for value in ("7", "27", "bad")]
        before = dict(files)
        for key, value in cases:
            with self.subTest(key=key, value=value):
                configuration = dict(CONFIGURATION, **{key: value})
                with self.assertRaises(ValueError):
                    generate.specialize_rust(files, configuration=configuration)
                self.assertEqual(files, before)

    def test_resource_boundaries_are_admitted_without_allocating_resources(self):
        generate = module("generate")
        files = canonical_sources()
        ordinary_recipe = {key: value for key, value in CONFIGURATION.items()
                           if key not in ("ROVE_F_SINGLE", "ROVE_F_PARITY")}
        profiles = (dict(CONFIGURATION),
                    dict(CONFIGURATION, ROVE_WORKERS="512", ROVE_TT_BITS="26"),
                    ordinary_recipe)
        for configuration in profiles:
            with self.subTest(configuration=configuration):
                output, metadata = generate.specialize_rust(files, configuration=configuration)
                self.assertIn("rust/main.rs", output)
                self.assertTrue(all(isinstance(data, bytes) for data in output.values()))
                self.assertIsInstance(metadata, dict)

    def test_source_drift_does_not_silently_receive_canonical_rewrites(self):
        files = {name: data.replace(b"\r\n", b"\n")
                 for name, data in canonical_sources().items()}
        # A real Rust semantic edit, not an invalid source or missing file, must
        # reach the canonical binding guard before any transformation applies.
        original = files["rust/main.rs"]
        changed = original.replace(
            b'const VARIANT:u8=letter(option_env!("ROVE_VARIANT"),b\'A\');',
            b'const VARIANT:u8=letter(option_env!("ROVE_VARIANT"),b\'B\');', 1)
        self.assertNotEqual(changed, original)
        files["rust/main.rs"] = changed
        for eol in (b"\n", b"\r\n"):
            with self.subTest(eol=eol):
                styled = {name: data.replace(b"\n", eol) for name, data in files.items()}
                before = dict(styled)
                with self.assertRaisesRegex(ValueError, "source binding mismatch: rust/main.rs"):
                    module("generate").specialize_rust(styled, configuration=CONFIGURATION)
                self.assertEqual(styled, before)

    def test_CRLF_and_LF_produce_identical_output_but_retain_raw_provenance(self):
        generate = module("generate")
        lf = {name: data.replace(b"\r\n", b"\n")
              for name, data in canonical_sources().items()}
        crlf = {name: data.replace(b"\n", b"\r\n") for name, data in lf.items()}
        self.assertNotEqual(lf["rust/main.rs"], crlf["rust/main.rs"])
        plain, plain_metadata = generate.specialize_rust(lf, configuration=CONFIGURATION)
        windows, windows_metadata = generate.specialize_rust(crlf, configuration=CONFIGURATION)
        self.assertEqual(plain, windows)
        for files, metadata in ((lf, plain_metadata), (crlf, windows_metadata)):
            with self.subTest(crlf=files is crlf):
                self.assertEqual(metadata["input_sha256"], {
                    name: hashlib.sha256(data).hexdigest() for name, data in files.items()})
                self.assertEqual(metadata["input_bytes"], sum(map(len, files.values())))
                self.assertEqual(metadata["input_crlf_counts"], {
                    name: data.count(b"\r\n") for name, data in files.items()})
                self.assertEqual(metadata["binding_normalized_sha256"], {
                    name: hashlib.sha256(data).hexdigest()
                    for name, data in lf.items() if name.startswith("rust/")})
        self.assertNotEqual(plain_metadata["input_sha256"]["rust/main.rs"],
                            windows_metadata["input_sha256"]["rust/main.rs"])
        self.assertGreater(windows_metadata["input_bytes"], plain_metadata["input_bytes"])

    def test_transformation_is_pure_and_repeatable(self):
        generate = module("generate")
        files = canonical_sources()
        before = dict(files)
        configuration = dict(CONFIGURATION)
        first, first_metadata = generate.specialize_rust(files, configuration=configuration)
        second, second_metadata = generate.specialize_rust(files, configuration=configuration)
        self.assertEqual(files, before)
        self.assertEqual(configuration, CONFIGURATION)
        self.assertEqual(first, second)
        self.assertEqual(first_metadata, second_metadata)
        self.assertNotEqual(first["rust/main.rs"], files["rust/main.rs"])


if __name__ == "__main__":
    unittest.main()
