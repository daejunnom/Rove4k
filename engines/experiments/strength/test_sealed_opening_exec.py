"""Linux sealed opening binding; no scored league or AWS execution."""
import hashlib
import json
import os
from pathlib import Path
import shutil
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
        runner = self.root / "python-runner"
        shutil.copyfile(Path(sys.executable).resolve(), runner)
        runner.chmod(0o700)
        runner_sha = hashlib.sha256(runner.read_bytes()).hexdigest()
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
                "--bytes", str(self.pin["bytes"]), "--runner-sha256", runner_sha,
                "--", str(runner), str(script),
                str(self.source), "-openings", "file=" + helper.PLACEHOLDER]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"data": self.raw.decode(), "writable": False})

    def test_runner_snapshot_rejects_wrong_or_replaced_elf(self):
        runner = self.root / "runner"
        shutil.copyfile(Path(sys.executable).resolve(), runner)
        runner.chmod(0o700)
        raw = runner.read_bytes()
        pin = hashlib.sha256(raw).hexdigest()
        fd = helper.sealed_runner_snapshot(runner, pin)
        self.addCleanup(os.close, fd)
        self.assertFalse(os.get_inheritable(fd))
        runner.unlink()
        runner.write_bytes(b"replaced")
        runner.chmod(0o700)
        with open(f"/proc/self/fd/{fd}", "rb") as stream:
            self.assertEqual(stream.read(), raw)
        with self.assertRaises(OSError):
            os.pwrite(fd, b"x", 0)
        with self.assertRaises(ValueError):
            helper.sealed_runner_snapshot(runner, pin)
        runner.unlink()
        runner.symlink_to(Path(sys.executable).resolve())
        with self.assertRaises((ValueError, OSError)):
            helper.sealed_runner_snapshot(runner, pin)

    def test_runner_snapshot_rejects_parent_traversal(self):
        runner = self.root / "runner"
        shutil.copyfile(Path(sys.executable).resolve(), runner)
        runner.chmod(0o700)
        sub = self.root / "sub"
        sub.mkdir()
        pin = hashlib.sha256(runner.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "parent traversal"):
            helper.sealed_runner_snapshot(sub / ".." / "runner", pin)

    def test_runner_snapshot_respects_original_execute_permission(self):
        runner = self.root / "runner"
        shutil.copyfile(Path(sys.executable).resolve(), runner)
        runner.chmod(0o600)
        pin = hashlib.sha256(runner.read_bytes()).hexdigest()
        with self.assertRaises(PermissionError):
            subprocess.run([str(runner), "--version"], check=True, capture_output=True)
        with self.assertRaises(PermissionError):
            helper.sealed_runner_snapshot(runner, pin)

    def test_runner_snapshot_rejects_setid_or_file_capability(self):
        runner = self.root / "runner"
        shutil.copyfile(Path(sys.executable).resolve(), runner)
        pin = hashlib.sha256(runner.read_bytes()).hexdigest()
        runner.chmod(0o4700)
        if runner.stat().st_mode & 0o4000:
            with self.assertRaisesRegex(PermissionError, "privilege-bearing"):
                helper.sealed_runner_snapshot(runner, pin)
        runner.chmod(0o700)
        with patch.object(helper.os, "getxattr", return_value=b"capability"), \
             self.assertRaisesRegex(PermissionError, "file capabilities"):
            helper.sealed_runner_snapshot(runner, pin)

    def test_runner_snapshot_rejects_actual_noexec_mount(self):
        noexec_dir = Path("/run/lock")
        if not noexec_dir.is_dir() or not os.access(noexec_dir, os.W_OK):
            self.skipTest("no writable noexec test directory")
        if not os.statvfs(noexec_dir).f_flag & os.ST_NOEXEC:
            self.skipTest("test directory is executable")
        with tempfile.TemporaryDirectory(prefix="rove-noexec-", dir=noexec_dir) as tmp:
            runner = Path(tmp) / "runner"
            shutil.copyfile(Path(sys.executable).resolve(), runner)
            runner.chmod(0o700)
            pin = hashlib.sha256(runner.read_bytes()).hexdigest()
            with self.assertRaises(PermissionError):
                subprocess.run([str(runner), "--version"], check=True, capture_output=True)
            with self.assertRaises(PermissionError):
                helper.sealed_runner_snapshot(runner, pin)

    def test_runner_fd_exec_is_bound_after_path_replacement(self):
        runner = self.root / "runner"
        source = self.root / "runner.c"
        source.write_text('#include <stdio.h>\nint main(void){puts("original-runner");return 0;}\n')
        subprocess.run(["cc", str(source), "-o", str(runner)], check=True, timeout=30)
        fd = helper.sealed_runner_snapshot(runner, hashlib.sha256(runner.read_bytes()).hexdigest())
        self.addCleanup(os.close, fd)
        runner.unlink()
        runner.write_bytes(b"replaced")
        launch = ('import os,sys; fd=int(sys.argv[1]); os.set_inheritable(fd,False); '
                  'os.execve(fd,[sys.argv[2]],os.environ)')
        result = subprocess.run([sys.executable, "-I", "-c", launch, str(fd), str(runner)],
                                pass_fds=(fd,), capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "original-runner\n")

    def test_helper_preserves_closed_standard_fds_for_real_elf_runner(self):
        runner = self.root / "runner"
        source = self.root / "stdio.c"
        source.write_text(
            '#include <errno.h>\n#include <fcntl.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <unistd.h>\n'
            'int main(int n,char **v){int mask=0;for(int i=0;i<3;i++){errno=0;'
            'if(fcntl(i,F_GETFD)<0&&errno==EBADF)mask|=1<<i;}'
            'int pg=atoi(getenv("ROVE_OPENING_FD"));char b[128];int len=read(pg,b,sizeof b);'
            'int leak=0;for(int i=3;i<256;i++){char p[64],q[256];snprintf(p,sizeof p,"/proc/self/fd/%d",i);'
            'int z=readlink(p,q,sizeof q-1);if(z>0){q[z]=0;if(strstr(q,"memfd:rove4k-runner"))leak=1;}}'
            'dprintf(atoi(v[1]),"%d %d %d %d\\n",mask,pg,len,leak);return pg<3||len<=0||leak;}\n')
        subprocess.run(["cc", str(source), "-o", str(runner)], check=True, timeout=30)
        pin = hashlib.sha256(runner.read_bytes()).hexdigest()
        for mask in range(1, 8):
            with self.subTest(closed_mask=mask):
                report = self.root / ("report-" + str(mask))
                report_fd = os.open(report, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    def close_selected():
                        for number in range(3):
                            if mask & (1 << number):
                                os.close(number)
                    argv = [sys.executable, "-I", str(Path(helper.__file__).resolve()),
                            "--source", str(self.source), "--sha256", self.pin["sha256"],
                            "--bytes", str(self.pin["bytes"]), "--runner-sha256", pin,
                            "--", str(runner), str(report_fd), "-openings", "file=" + helper.PLACEHOLDER]
                    result = subprocess.run(argv, pass_fds=(report_fd,), preexec_fn=close_selected, timeout=20)
                    self.assertEqual(result.returncode, 0)
                    os.lseek(report_fd, 0, os.SEEK_SET)
                    observed, opening_fd, length, runner_leaked = map(int, os.read(report_fd, 128).split())
                    self.assertEqual(observed, mask)
                    self.assertGreaterEqual(opening_fd, 3)
                    self.assertEqual(length, len(self.raw))
                    self.assertEqual(runner_leaked, 0)
                finally:
                    os.close(report_fd)


if __name__ == "__main__":
    unittest.main()
