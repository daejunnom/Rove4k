"""Linux sealed opening binding; no scored league or AWS execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import sealed_opening_exec as helper
except ImportError:
    import sealed_opening_exec as helper


@unittest.skipUnless(sys.platform == "linux" and hasattr(os, "memfd_create"), "Linux memfd required")
class SealedOpeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / "opening.pgn"
        self.raw = b'[Event "fixture"]\n\n1. e4 e5 *\n'
        self.source.write_bytes(self.raw)
        self.pin = {"bytes": len(self.raw), "sha256": hashlib.sha256(self.raw).hexdigest()}

    def test_snapshot_remains_immutable_after_path_replace(self):
        fd = helper.sealed_snapshot(self.source, self.pin)
        self.addCleanup(os.close, fd)
        self.source.unlink()
        self.source.write_bytes(b"different")
        with open(f"/proc/self/fd/{fd}", "rb") as file:
            self.assertEqual(file.read(), self.raw)
        with self.assertRaises(OSError):
            os.pwrite(fd, b"x", 0)
        with self.assertRaises(OSError):
            os.ftruncate(fd, 1)

    def test_bad_pin_or_replaced_input_fails_closed(self):
        self.source.write_bytes(b"replaced")
        with self.assertRaises(ValueError):
            helper.sealed_snapshot(self.source, self.pin)
        self.source.write_bytes(b"x" * len(self.raw))
        with self.assertRaisesRegex(ValueError, "differs"):
            helper.sealed_snapshot(self.source, self.pin)
        self.source.unlink()
        self.source.symlink_to(self.root / "other")
        (self.root / "other").write_bytes(self.raw)
        with self.assertRaises(OSError):
            helper.sealed_snapshot(self.source, self.pin)

    def test_missing_kernel_seal_capability_fails_closed(self):
        with patch.object(helper, "_HAS_SEALS", False), self.assertRaisesRegex(RuntimeError, "memfd"):
            helper.sealed_snapshot(self.source, self.pin)

    def test_only_openings_file_placeholder_is_replaced(self):
        command = ["/tmp/runner", "-openings", "file=" + helper.PLACEHOLDER,
                   "-log", "file=/tmp/game.log"]
        replaced = helper.command_with_fd(command, 9)
        self.assertEqual(replaced[2], "file=/proc/self/fd/9")
        self.assertEqual(replaced[-1], "file=/tmp/game.log")
        for invalid in (command + ["file=" + helper.PLACEHOLDER],
                        ["/tmp/runner", "-log", "file=" + helper.PLACEHOLDER],
                        ["/tmp/runner", "-openings", "x", "file=" + helper.PLACEHOLDER],
                        ["/tmp/runner", "-openings", "file=" + helper.PLACEHOLDER, "file=/tmp/other"]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                helper.command_with_fd(invalid, 9)

    def test_isolated_exec_passes_sealed_fd_after_source_replacement(self):
        script = self.root / "runner.py"
        script.write_text('import json, os, sys\n'
                          'source = sys.argv[1]\n'
                          'path = sys.argv[sys.argv.index("-openings") + 1][5:]\n'
                          'os.unlink(source)\n'
                          'open(source, "wb").write(b"new bytes")\n'
                          'data = open(path, "rb").read()\n'
                          'try:\n'
                          '    fd = os.open(path, os.O_WRONLY); os.write(fd, b"x")\n'
                          '    writable = True\n'
                          'except OSError:\n'
                          '    writable = False\n'
                          'print(json.dumps({"data": data.decode(), "writable": writable}))\n')
        argv = [sys.executable, "-I", str(Path(helper.__file__).resolve()),
                "--source", str(self.source), "--sha256", self.pin["sha256"],
                "--bytes", str(self.pin["bytes"]), "--", sys.executable, str(script),
                str(self.source), "-openings", "file=" + helper.PLACEHOLDER]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"data": self.raw.decode(), "writable": False})


if __name__ == "__main__":
    unittest.main()
