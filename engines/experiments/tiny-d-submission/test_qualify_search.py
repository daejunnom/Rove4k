"""Focused orchestration checks; these do not execute an engine or compiler."""
import ast
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PATH = Path(__file__).with_name("qualify_search.py")
SPEC = importlib.util.spec_from_file_location("D_search_qualifier_tests", PATH)
Q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(Q)


class QualifierTests(unittest.TestCase):
    def test_frozen_bytes_execute_even_if_original_path_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "helper.py"
            source.write_bytes(b"raise AssertionError('live source consumed')\n")
            frozen = b"value=17\ndef actual(): return value+1\n"
            module = Q.load_bytes("D_search_frozen_byte_test", source, frozen)
            self.assertEqual(module.actual(), 18)
            self.assertEqual(module.__file__, str(source))

    def test_runtime_reader_is_mandatory_exact_support(self):
        reader = "engines/scripts/production_input.py"
        runtime = SimpleNamespace(SUPPORT={Q.SUPPORT[2]: "literal", Q.SUPPORT[3]: "literal", Q.SUPPORT[4]: "literal"},
                                  INPUT_READER=reader)
        support = dict.fromkeys(Q.SUPPORT, b"frozen")
        Q.require_support(runtime, support)
        with self.assertRaisesRegex(ValueError, "complete frozen"):
            Q.require_support(runtime, {name: data for name, data in support.items() if name != reader})
        with self.assertRaisesRegex(ValueError, "complete frozen"):
            Q.require_support(runtime, {**support, "unknown.py": b"unconsumed"})

    def test_safe_bounds_and_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source.c").write_bytes(b"abcd")
            self.assertEqual(Q.safe(root, "source.c", maximum=4), b"abcd")
            with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                Q.safe(root, "source.c", maximum=3)
            for name in ("../outside.c", str(root / "source.c")):
                with self.assertRaisesRegex(ValueError, "explicit relative"):
                    Q.safe(root, name)

    @unittest.skipUnless(os.name == "posix", "real POSIX link policy")
    def test_safe_rejects_links_and_hardlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source.c").write_bytes(b"actual")
            os.symlink(root / "source.c", root / "link.c")
            with self.assertRaisesRegex(ValueError, "cannot follow links"):
                Q.safe(root, "link.c")
            os.link(root / "source.c", root / "hard.c")
            for name in ("source.c", "hard.c"):
                with self.assertRaisesRegex(ValueError, "bounded ordinary"):
                    Q.safe(root, name)

    def test_write_never_replaces_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            Q.write(root, "exact/source.c", b"first")
            with self.assertRaisesRegex(ValueError, "will not overwrite"):
                Q.write(root, "exact/source.c", b"second")
            self.assertEqual((root / "exact/source.c").read_bytes(), b"first")

    def test_selector_required_before_source_reads(self):
        with patch.object(sys, "argv", [str(PATH), "--experiment", "/known", "--storage-evidence", "/known2", "--out", "/new"]), \
             patch.object(Q, "normalized", side_effect=AssertionError("source read")) as read:
            with self.assertRaises(SystemExit) as failure:
                Q.main()
            self.assertEqual(failure.exception.code, 2)
            read.assert_not_called()

    def test_output_inside_git_rejected_before_source_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            argv = [str(PATH), "--experiment", str(root / "evidence"), "--storage-evidence", str(root / "storage"),
                    "--selector", "proved-win-combination", "--out", str(root / "new")]
            with patch.object(sys, "argv", argv), patch.object(Q.sys, "platform", "linux"), \
                 patch.object(Q.platform, "machine", return_value="x86_64"), \
                 patch.object(Q, "normalized", side_effect=AssertionError("source read")) as read:
                with self.assertRaisesRegex(ValueError, "new external"):
                    Q.main()
                read.assert_not_called()

    def test_python310_syntax(self):
        ast.parse(PATH.read_bytes(), feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
