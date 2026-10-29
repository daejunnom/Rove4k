"""Verify the small GNU-tail-only peer launcher transform with toy input."""
import copy
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import peer_launcher_trim as trim, peer_exact_runner as owned_runner
except ImportError:
    import peer_launcher_trim as trim
    import peer_exact_runner as owned_runner


# Synthetic toy contract: no external engine source or launcher is stored here.
TOY = (b'#!/bin/sh\nQ=`mktemp -p "$HOME"`;echo shell=$$\n'
       b'tail -n +5 "$0"|xz -d|g++ -O3 -std=c++23 -pthread -march=native -xc++ -o"$Q" -\n'
       b'(sleep 1;rm "$Q")&exec "$Q"\n')
TOY_ICE = (b'#!/bin/sh\nQ=`mktemp -p "$HOME"`;echo shell=$$\n'
           b'tail -n +5 "$0"|xz -d|c++ -O3 -pthread -xc++ -o"$Q" -\n'
           b'(sleep 1;rm "$Q")&exec "$Q"\n')


class LauncherTrimTests(unittest.TestCase):
    def setUp(self):
        self.source_pin = patch.object(trim.peers, "verify_blob", return_value=None)
        self.source_pin.start()
        self.addCleanup(self.source_pin.stop)

    def test_only_line_selector_changes_and_full_inverse_is_exact(self):
        for name in ("ice4", "c4ke"):
            with self.subTest(peer=name):
                candidate, proof = trim.transform_launcher(name, TOY)
                self.assertEqual(len(candidate), len(TOY) - 3)
                self.assertEqual(candidate, TOY.replace(trim._BEFORE, trim._AFTER, 1))
                self.assertEqual(trim.restore_launcher(name, candidate, proof), TOY)
                self.assertEqual(proof["peer"], name)
                self.assertFalse(proof["runtime_qualified"])
                self.assertFalse(proof["engine_executed"])

    def test_changed_or_missing_pinned_marker_is_rejected(self):
        for malformed in (TOY.replace(trim._BEFORE, b"other"), TOY + trim._BEFORE):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                trim.transform_launcher("c4ke", malformed)
        with self.assertRaises(ValueError):
            trim.transform_launcher("c4ke", bytearray(TOY))
        with self.assertRaises(ValueError):
            trim.transform_launcher("unrecognized", TOY)

    def test_exact_peer_blob_pin_is_required_before_transform(self):
        for name in ("ice4", "c4ke"):
            with self.subTest(peer=name), patch.object(trim.peers, "verify_blob") as verify:
                trim.transform_launcher(name, TOY)
                verify.assert_called_once_with(name, "launcher.sh", TOY)
            with self.subTest(rejected_peer=name), patch.object(trim.peers, "verify_blob", side_effect=ValueError("bad blob")):
                with self.assertRaisesRegex(ValueError, "bad blob"):
                    trim.transform_launcher(name, TOY)

    def test_modified_candidate_or_proof_is_rejected(self):
        candidate, proof = trim.transform_launcher("c4ke", TOY)
        altered = copy.deepcopy(proof)
        altered["runtime_qualified"] = True
        with self.assertRaises(ValueError):
            trim.restore_launcher("c4ke", candidate, altered)
        with self.assertRaises(ValueError):
            trim.restore_launcher("c4ke", candidate + b"x", proof)
        with self.assertRaises(ValueError):
            trim.restore_launcher("ice4", candidate, proof)

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("tail"), "GNU tail is required")
    def test_tail_binary_line_selection_with_and_without_posix_environment(self):
        payload = b"header1\nheader2\nheader3\nheader4\n\x00\xff\nZ"
        for value in (None, "1"):
            env = {"PATH": "/usr/bin:/bin"}
            if value is not None:
                env["POSIXLY_CORRECT"] = value
            expected = subprocess.run(["tail", "-n", "+5"], input=payload, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, env=env, timeout=5, check=True)
            actual = subprocess.run(["tail", "+5"], input=payload, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=env, timeout=5, check=True)
            self.assertEqual(expected.stdout, b"\x00\xff\nZ")
            self.assertEqual(actual.stdout, expected.stdout)
            self.assertEqual(actual.stderr, b"")

    @unittest.skipUnless(sys.platform == "linux" and all(shutil.which(x) for x in ("g++", "c++", "xz", "tail", "mktemp")),
                         "Linux GNU tail, xz, mktemp and g++ are required")
    def test_real_shell_decompress_compile_exec_and_cleanup_with_toy_payload(self):
        # No real engine is built or executed: the tiny toy only prints its PID.
        with tempfile.TemporaryDirectory(prefix="rove4k-peer-tail-") as root:
            root = Path(root)
            temp_dir = root / "tmp"
            temp_dir.mkdir(mode=0o700)
            scripts = root / "path with spaces"
            scripts.mkdir()
            for peer, original in (("c4ke", TOY), ("ice4", TOY_ICE)):
                candidate, _ = trim.transform_launcher(peer, original)
                for status in (0, 7):
                    cpp = ('#include <cstdio>\n#include <unistd.h>\n'
                           'int main(){std::printf("native=%%ld\\n",(long)getpid());return %d;}\n' % status).encode()
                    payload = lzma.compress(cpp, format=lzma.FORMAT_ALONE)
                    for label, header in (("original", original), ("candidate", candidate)):
                        with self.subTest(peer=peer, label=label, status=status):
                            target = scripts / (peer + "-" + label + "-" + str(status))
                            target.write_bytes(header + payload)
                            target.chmod(0o700)
                            if status:
                                with self.assertRaises(owned_runner.BuildCommandFailure) as failure:
                                    owned_runner.run([str(target)], scripts, sandbox_home=temp_dir,
                                                     cpu=min(os.sched_getaffinity(0)), timeout=15)
                                record = failure.exception.record
                            else:
                                stdout, stderr, record = owned_runner.run([str(target)], scripts, sandbox_home=temp_dir,
                                                                          cpu=min(os.sched_getaffinity(0)), timeout=15)
                                lines = stdout.decode("ascii").splitlines()
                                self.assertEqual(len(lines), 2)
                                self.assertTrue(lines[0].startswith("shell="))
                                self.assertEqual(lines[0].removeprefix("shell="), lines[1].removeprefix("native="))
                                self.assertTrue(lines[1].startswith("native="))
                                self.assertEqual(stderr, b"")
                            self.assertEqual(record["exit_code"], status)
                            self.assertFalse(record["forced_cleanup"])
                            self.assertTrue(record["group_absent"])
                            self.assertEqual(list(temp_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
