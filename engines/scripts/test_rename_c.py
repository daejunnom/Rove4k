"""Lexical/candidate checks, plus an explicitly enabled real compiler fixture.

Run pure checks with ``python -m unittest discover -s engines/scripts -p
test_rename_c.py``. On an otherwise free Linux compiler slot, set
``ROVE4K_IDENTIFIER_COMPACTION_COMPILE=1`` for the full native hash gate fixture.
Mock digests in the unit tests exercise decisions, not C equivalence claims.
"""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from rename_c import _FIRST, _identifier_spans, _replace, compact_identifiers


class IdentifierTests(unittest.TestCase):
    def test_replacement_preserves_directives_comments_literals_and_numbers(self):
        source = b'''#include <long_identifier.h>
#define long_identifier(x) #x \\
+ long_identifier
/* long_identifier */ int long_identifier=0xabcdef+12UL+1e+6;
char *s=u8"long_identifier";int n=L'X';// long_identifier \\
long_identifier
long_identifier++;
'''
        changed = _replace({"a.c": source}, "long_identifier", "q")["a.c"]
        expected = source.replace(b"int long_identifier=", b"int q=")
        expected = expected.replace(b"long_identifier++;", b"q++;")
        self.assertEqual(changed, expected)
        tokens = [token for _, _, token in _identifier_spans(source.decode())]
        self.assertNotIn("xabcdef", tokens)
        self.assertNotIn("UL", tokens)
        self.assertNotIn("u8", tokens)
        self.assertNotIn("L", tokens)

    def test_phase_two_comments_spliced_names_and_alternative_directives(self):
        source = (b"/\\\n/ long_identifier\n"
                  b"/\\\r\n* long_identifier *\\\r\n/\n"
                  b"%:define long_identifier 1\n"
                  b"char*s=\"ab\\\r\nlong_identifier\";\n"
                  b"int long_\\\nidentifier;int long_identifier;\n")
        result = _replace({"a.c": source}, "long_identifier", "q")["a.c"]
        self.assertEqual(result, source.replace(b";int long_identifier;", b";int q;"))

    def test_recipe_dependent_trigraph_files_are_preserved_and_recorded(self):
        for source in (b"??=define long_identifier 2\nint long_identifier;\n",
                       b"// long_identifier ??/\nlong_identifier\n",
                       b"/??/\n/ long_identifier\n"):
            self.assertEqual(_replace({"a.c": source}, "long_identifier", "q")["a.c"], source)
            result, record = compact_identifiers({"a.c": source}, lambda *_: "0" * 64)
            self.assertEqual(result, {"a.c": source})
            self.assertIn("a.c", record["lexically_excluded_files"])
            self.assertEqual(record["trials_completed"], 0)

    def test_fresh_names_reserve_all_existing_tokens_and_global_spelling(self):
        files = {"a.c": b'int shared_function(void);int main(void){return shared_function();}\n',
                 "b.c": b'#define b c\n/* d */const char*s="a";int shared_function(void){return 7;}\n'}
        observed = []

        def gate(candidate, number):
            observed.append((candidate, number))
            return "ab" * 32

        result, record = compact_identifiers(files, gate, max_trials=1)
        self.assertEqual(record["accepted_renames"], {"shared_function": "e"})
        self.assertIn(b"int e(void);", result["a.c"])
        self.assertIn(b"return e();", result["a.c"])
        self.assertIn(b"int e(void)", result["b.c"])
        self.assertEqual([number for _, number in observed], [0, 1])
        self.assertIn(b"shared_function", files["a.c"])
        self.assertEqual(record["before"]["a.c"]["sha256"], hashlib.sha256(files["a.c"]).hexdigest())
        self.assertEqual(record["after"]["a.c"]["sha256"], hashlib.sha256(result["a.c"]).hexdigest())

    def test_unused_names_reserve_logical_spliced_and_trigraph_spellings(self):
        source = ("/* " + " ".join(_FIRST) + " */int a\\\na;int lengthy_name;\n").encode()
        _, record = compact_identifiers({"a.c": source}, lambda *_: "0" * 64, max_trials=1)
        self.assertEqual(record["accepted_renames"], {"lengthy_name": "ab"})
        _, record = compact_identifiers({"a.c": source.replace(b"a\\\na;int lengthy_name;", b"a??/\na;"),
                                         "b.c": b"int lengthy_name;\n"},
                                        lambda *_: "0" * 64, max_trials=1)
        self.assertEqual(record["accepted_renames"], {"lengthy_name": "ab"})

    def test_gate_rejects_changed_native_bytes_and_compilation_failure(self):
        files = {"a.c": b"int longest_identifier,other_identifier;\n"}
        observed = []

        def gate(candidate, number):
            observed.append(dict(candidate))
            if number == 1:
                return "1" * 64
            if number == 2:
                raise RuntimeError("intentional fixture compiler failure")
            return "0" * 64

        result, record = compact_identifiers(files, gate, max_trials=2)
        self.assertEqual(result, files)
        self.assertEqual(record["accepted_renames"], {})
        self.assertEqual([trial["reason"] for trial in record["trials"]],
                         ["native_digest_mismatch", "compile_error"])
        self.assertIn(b"longest_identifier", observed[2]["a.c"])
        self.assertIn("other_identifier", record["rejected_renames"])

    def test_keywords_reserved_names_unicode_and_prefixed_literals_are_not_candidates(self):
        source = 'static _Atomic int _reserved;char*unicode_name=U"unicode_name";int café;int cafe\u0301;int \\u00E9name;\n'
        result, record = compact_identifiers({"a.c": source.encode()}, lambda *_: "0" * 64)
        self.assertEqual(set(record["accepted_renames"]), {"unicode_name"})
        self.assertIn(b"_reserved", result["a.c"])
        self.assertIn('café'.encode(), result["a.c"])
        self.assertIn('cafe\u0301'.encode(), result["a.c"])
        self.assertIn(b"\\u00E9name", result["a.c"])
        self.assertIn(b'U"unicode_name"', result["a.c"])

    def test_baseline_is_mandatory_bounds_are_explicit_and_digest_is_validated(self):
        calls = []
        source = {"a.c": b"int lengthy_name;\n"}
        result, record = compact_identifiers(source, lambda files, number: calls.append(number) or "0" * 64,
                                             max_trials=0)
        self.assertEqual(calls, [0])
        self.assertEqual(result, source)
        self.assertEqual(record["trials_completed"], 0)
        self.assertEqual(record["unattempted_identifiers"], {"lengthy_name": "trial_limit"})
        with self.assertRaisesRegex(RuntimeError, "baseline failed"):
            compact_identifiers(source, lambda *_: (_ for _ in ()).throw(RuntimeError("baseline failed")))
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            compact_identifiers(source, lambda *_: "short")
        with self.assertRaises(ValueError):
            compact_identifiers(source, lambda *_: "0" * 64, max_trials=-1)

    def test_deterministic_order_and_baseline_cannot_mutate_accepted_input(self):
        files = {"b.c": b"int second_long_name;\n", "a.c": b"int first_long_name;\n"}

        def gate(candidate, number):
            candidate.clear()
            return "a" * 64

        first = compact_identifiers(files, gate, max_trials=1)
        second = compact_identifiers(dict(reversed(list(files.items()))), gate, max_trials=1)
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 2)
        self.assertEqual(first[1]["trials_completed"], 1)


@unittest.skipUnless(os.environ.get("ROVE4K_IDENTIFIER_COMPACTION_COMPILE") == "1" and
                     sys.platform == "linux" and shutil.which("cc"),
                     "explicit Linux compiler slot required")
class NativeGateTests(unittest.TestCase):
    def test_actual_full_executable_hash_and_cross_translation_unit_rename(self):
        files = {"a.c": b'''#include <stdio.h>
#define SPELL(value) #value
int shared_long_function(int);
int main(void){printf("%d %s\\n",shared_long_function(5),SPELL(stringified_long_name));return 0;}
''', "b.c": b'''static int long_private_counter=7;
int shared_long_function(int long_argument_value){return long_argument_value+long_private_counter;}
'''}
        with tempfile.TemporaryDirectory(prefix="r4-rename-c-") as temporary:
            directory, outputs = Path(temporary), {}

            def compile_digest(candidate, number):
                for name, data in candidate.items():
                    (directory / name).write_bytes(data)
                subprocess.run(["cc", "-std=c11", "-Os", "-fno-ident", "-s", "a.c", "b.c", "-o", "native"],
                               cwd=directory, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=20)
                native = directory / "native"
                data = native.read_bytes()
                outputs[number] = subprocess.check_output([str(native)], timeout=5)
                return hashlib.sha256(data).hexdigest()

            result, record = compact_identifiers(files, compile_digest)
            self.assertIn("shared_long_function", record["accepted_renames"])
            self.assertEqual(record["rejected_renames"]["stringified_long_name"]["reason"],
                             "native_digest_mismatch")
            self.assertEqual(record["rejected_renames"]["printf"]["reason"], "compile_error")
            self.assertLess(record["after_bytes"], record["before_bytes"])
            self.assertEqual(compile_digest(result, 1000), record["baseline_native_sha256"])
            self.assertEqual(outputs[1000], b"12 stringified_long_name\n")
            self.assertEqual(outputs[0], outputs[1000])


if __name__ == "__main__":
    unittest.main()
