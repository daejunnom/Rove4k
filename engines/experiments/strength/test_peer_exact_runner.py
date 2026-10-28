"""Small owned-process tests for peer build runner; no chess engine runs."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

try:
    from . import peer_exact_runner as runner
except ImportError:
    import peer_exact_runner as runner


@unittest.skipUnless(sys.platform == "linux" and hasattr(os, "sched_getaffinity"), "Linux process ownership required")
class OwnedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="rove4k-owned-runner-test-")
        self.addCleanup(self.directory.cleanup)
        self.cwd = Path(self.directory.name).resolve()
        self.home = self.cwd / "sandbox-home"
        self.home.mkdir(mode=0o700)
        self.cpu = min(os.sched_getaffinity(0))

    def run_code(self, code, *, timeout=5, output_bytes=4096, rustup_home=None):
        return runner.run([sys.executable, "-I", "-B", "-c", code], self.cwd,
                          cpu=self.cpu, timeout=timeout, memory_bytes=512 << 20,
                          output_bytes=output_bytes, sandbox_home=self.home, rustup_home=rustup_home)

    def assert_no_logs(self):
        self.assertEqual(list(self.cwd.iterdir()), [self.home])
        self.assertEqual(list(self.home.iterdir()), [])

    def test_normal_output_and_no_command_logs(self):
        stdout, stderr, record = self.run_code("import os;os.write(1,b'normal');os.write(2,b'warning')")
        self.assertEqual(stdout, b"normal")
        self.assertEqual(stderr, b"warning")
        self.assertEqual(record["exit_code"], 0)
        self.assertTrue(record["leader_reaped"])
        self.assertTrue(record["group_absent"])
        self.assertFalse(record["forced_cleanup"])
        self.assert_no_logs()

    def test_arbitrary_parent_environment_is_not_inherited(self):
        marker = "R4K_SYNTHETIC_DO_NOT_INHERIT"
        code = ("import os;"
                "print(int('R4K_SYNTHETIC_DO_NOT_INHERIT' in os.environ));"
                "print(int(os.path.samefile(os.environ['HOME'], " + repr(str(self.home)) + ")))")
        with patch.dict(os.environ, {marker: "synthetic-fixture"}):
            stdout, _, _ = self.run_code(code)
        self.assertEqual(stdout.splitlines(), [b"0", b"1"])
        self.assert_no_logs()

    def test_grandchild_keeps_home_and_toolchain_directory_identity(self):
        rustup = self.cwd / "toolchain"
        rustup.mkdir(mode=0o700)
        grandchild = ("import os,sys;"
                      "print(int(os.path.samefile(os.environ['HOME'],sys.argv[1])));"
                      "print(int(os.path.samefile(os.environ['RUSTUP_HOME'],sys.argv[2])))")
        code = ("import subprocess,sys;"
                "r=subprocess.run([sys.executable,'-I','-B','-c'," + repr(grandchild) + "," +
                repr(str(self.home)) + "," + repr(str(rustup)) + "],capture_output=True,check=True);"
                "sys.stdout.buffer.write(r.stdout)")
        stdout, _, _ = self.run_code(code, rustup_home=rustup)
        self.assertEqual(stdout.splitlines(), [b"1", b"1"])
        self.assertEqual(set(self.cwd.iterdir()), {self.home, rustup})
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(list(rustup.iterdir()), [])

    def test_output_limit_is_enforced_for_stdout_and_stderr(self):
        for fd in (1, 2):
            with self.subTest(fd=fd):
                code = f"import os;os.write({fd},b'x'*200000)"
                with self.assertRaises(RuntimeError):
                    self.run_code(code, output_bytes=4096)
                self.assert_no_logs()

    def test_timeout_and_abnormal_exit_do_not_create_logs(self):
        start = time.monotonic()
        with self.assertRaises(runner.BuildCommandFailure) as timed:
            self.run_code("import time;time.sleep(20)", timeout=1)
        self.assertLess(time.monotonic() - start, 10)
        self.assertTrue(timed.exception.record["forced_cleanup"])
        self.assertTrue(timed.exception.record["leader_reaped"])
        self.assertTrue(timed.exception.record["group_absent"])
        with self.assertRaises(runner.BuildCommandFailure) as failed:
            self.run_code("raise SystemExit(7)")
        self.assertEqual(failed.exception.record["exit_code"], 7)
        self.assertTrue(failed.exception.record["leader_reaped"])
        self.assertTrue(failed.exception.record["group_absent"])
        self.assert_no_logs()

    def test_timeout_does_not_signal_a_separate_owned_test_process(self):
        other = subprocess.Popen([sys.executable, "-I", "-B", "-c", "import time;time.sleep(20)"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            with self.assertRaises(RuntimeError):
                self.run_code("import time;time.sleep(20)", timeout=1)
            self.assertIsNone(other.poll(), "a separately created test process must remain running")
        finally:
            if other.poll() is None:
                other.terminate()
            other.wait(timeout=5)
        self.assert_no_logs()

    def test_live_child_after_leader_exit_is_cleaned_before_reap(self):
        real_killpg = os.killpg
        ownership_checks = []

        def observe_kill(group, sig):
            if sig in (signal.SIGTERM, signal.SIGKILL):
                self.assertNotEqual(group, os.getpgrp())
                # The leader must still own its numeric PID and process group
                # when a group signal is sent, including if it has exited.
                raw = Path(f"/proc/{group}/stat").read_text(encoding="ascii")
                fields = raw[raw.rfind(")") + 2:].split()
                self.assertEqual(int(fields[2]), group)
                ownership_checks.append((group, sig, fields[0]))
            return real_killpg(group, sig)

        code = ("import os,subprocess,sys;"
                "subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(20)']);"
                "os._exit(0)")
        start = time.monotonic()
        with patch.object(runner.os, "killpg", side_effect=observe_kill):
            with self.assertRaises(RuntimeError) as failed:
                self.run_code(code, timeout=3)
        self.assertLess(time.monotonic() - start, 10)
        self.assertTrue(ownership_checks, "the still-owned group must be checked when cleaning its child")
        if isinstance(failed.exception, runner.BuildCommandFailure):
            self.assertTrue(failed.exception.record["forced_cleanup"])
            self.assertTrue(failed.exception.record["leader_reaped"])
            self.assertTrue(failed.exception.record["group_absent"])
        else:
            self.assertIsInstance(failed.exception, runner.GroupUnsettled)
            self.assertIsNotNone(failed.exception.process)
            self.assertIsNotNone(failed.exception.identity)
        self.assert_no_logs()

    def test_invalid_resources_are_rejected_before_spawn(self):
        allowed = set(os.sched_getaffinity(0))
        bad_cpu = max(allowed) + 1
        with self.assertRaises(ValueError):
            runner.run([sys.executable, "-c", "raise SystemExit(0)"], self.cwd, cpu=bad_cpu,
                       timeout=2, memory_bytes=512 << 20, output_bytes=4096, sandbox_home=self.home)
        for timeout, output in ((0, 4096), (2, 0), (-1, 4096)):
            with self.subTest(timeout=timeout, output=output), self.assertRaises(ValueError):
                runner.run([sys.executable, "-c", "raise SystemExit(0)"], self.cwd, cpu=self.cpu,
                           timeout=timeout, memory_bytes=512 << 20, output_bytes=output, sandbox_home=self.home)
        self.assert_no_logs()

    def test_nonprivate_or_symlinked_home_rejected(self):
        nonprivate = self.cwd / "nonprivate"
        nonprivate.mkdir()
        nonprivate.chmod(0o755)
        alias = self.cwd / "linked-home"
        alias.symlink_to(self.home, target_is_directory=True)
        command = [sys.executable, "-I", "-B", "-c", "raise SystemExit(0)"]
        for home in (nonprivate, alias):
            with self.subTest(home=home), self.assertRaises(ValueError):
                runner.run(command, self.cwd, cpu=self.cpu, timeout=2,
                           memory_bytes=512 << 20, output_bytes=4096, sandbox_home=home)

    def test_custom_sigchld_and_worker_thread_rejected_before_spawn(self):
        before = signal.getsignal(signal.SIGCHLD)
        try:
            signal.signal(signal.SIGCHLD, lambda *_: None)
            with self.assertRaises(ValueError):
                self.run_code("raise SystemExit(0)")
        finally:
            signal.signal(signal.SIGCHLD, before)
        errors = []
        def invoke():
            try:
                self.run_code("raise SystemExit(0)")
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=invoke)
        thread.start()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], (RuntimeError, ValueError))
        self.assert_no_logs()

    def test_lower_inherited_soft_limit_is_not_raised(self):
        script = r'''import resource,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import peer_exact_runner as runner
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
ceiling = 256 << 20
if hard != resource.RLIM_INFINITY and hard < ceiling:
    ceiling = hard
resource.setrlimit(resource.RLIMIT_AS, (ceiling, hard))
try:
    runner.run([sys.executable, '-I', '-B', '-c', 'raise SystemExit(0)'], Path(sys.argv[2]),
               cpu=int(sys.argv[4]), timeout=2, memory_bytes=512 << 20, output_bytes=4096,
               sandbox_home=Path(sys.argv[3]))
except ValueError:
    print('rejected')
else:
    raise SystemExit('inherited soft address-space limit was exceeded')
'''
        checked = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                                  str(Path(runner.__file__).parent), str(self.cwd), str(self.home), str(self.cpu)],
                                 capture_output=True, timeout=10, check=False)
        self.assertEqual(checked.returncode, 0, checked.stderr.decode(errors="replace"))
        self.assertEqual(checked.stdout.strip(), b"rejected")
        self.assert_no_logs()

    def test_term_settles_child_then_restores_previous_handler(self):
        marker = self.cwd / "owned-child.pid"
        toy = ("import os,time;from pathlib import Path;"
               "Path(" + repr(str(marker)) + ").write_text(str(os.getpid()));time.sleep(20)")
        script = r'''import signal,sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import peer_exact_runner as runner
def prior(signum, frame):
    pass
signal.signal(signal.SIGTERM, prior)
try:
    runner.run([sys.executable, '-I', '-B', '-c', sys.argv[5]], Path(sys.argv[2]),
               cpu=int(sys.argv[4]), timeout=15, memory_bytes=512 << 20, output_bytes=4096,
               sandbox_home=Path(sys.argv[3]))
except KeyboardInterrupt:
    print('interrupted')
    print('restored' if signal.getsignal(signal.SIGTERM) is prior else 'changed')
else:
    raise SystemExit('expected interrupted run')
'''
        supervisor = subprocess.Popen([sys.executable, "-I", "-B", "-c", script,
                                       str(Path(runner.__file__).parent), str(self.cwd), str(self.home),
                                       str(self.cpu), toy], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      start_new_session=True)
        try:
            deadline = time.monotonic() + 8
            while not marker.exists():
                if supervisor.poll() is not None or time.monotonic() >= deadline:
                    self.fail("the test child did not report startup")
                time.sleep(.02)
            child_pid = int(marker.read_text(encoding="ascii"))
            supervisor.send_signal(signal.SIGTERM)
            stdout, stderr = supervisor.communicate(timeout=10)
            self.assertEqual(supervisor.returncode, 0, stderr.decode(errors="replace"))
            self.assertEqual(stdout.splitlines(), [b"interrupted", b"restored"])
            self.assertFalse(Path(f"/proc/{child_pid}").exists(), "the owned child must be reaped")
        finally:
            if supervisor.poll() is None:
                supervisor.kill()
                supervisor.wait(timeout=5)
            marker.unlink(missing_ok=True)
        self.assert_no_logs()

    def test_pending_term_during_reap_never_signals_reused_process_group(self):
        script = r'''import os,signal,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import peer_exact_runner as runner
def prior(signum, frame):
    raise AssertionError('previous handler must not be invoked while ownership is changing')
signal.signal(signal.SIGTERM, prior)
settle = runner._settle
def interrupt_at_reap(proc, identity, *, stop, seconds=5):
    result = settle(proc, identity, stop=stop, seconds=seconds)
    if not stop:
        os.kill(os.getpid(), signal.SIGTERM)
        if signal.SIGTERM not in signal.sigpending():
            raise AssertionError('TERM was not held across the critical section')
    return result
try:
    with patch.object(runner, '_settle', side_effect=interrupt_at_reap), \
         patch.object(runner.os, 'killpg', side_effect=AssertionError('must not signal reaped group')):
        runner.run([sys.executable, '-I', '-B', '-c', 'raise SystemExit(0)'], Path(sys.argv[2]),
                   cpu=int(sys.argv[4]), timeout=5, memory_bytes=512 << 20, output_bytes=4096,
                   sandbox_home=Path(sys.argv[3]))
except KeyboardInterrupt:
    if runner._UNSETTLED or signal.getsignal(signal.SIGTERM) is not prior:
        raise AssertionError('ownership or handler not restored after pending TERM')
    print('passed')
else:
    raise SystemExit('expected interrupted run')
'''
        checked = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                                  str(Path(runner.__file__).parent), str(self.cwd), str(self.home), str(self.cpu)],
                                 capture_output=True, timeout=10, check=False)
        self.assertEqual(checked.returncode, 0, checked.stderr.decode(errors="replace"))
        self.assertEqual(checked.stdout.strip(), b"passed")
        self.assert_no_logs()

    def test_unsettled_group_retains_original_directory_descriptors(self):
        rustup = self.cwd / "toolchain"
        rustup.mkdir(mode=0o700)
        already_owned = set(runner._UNSETTLED)
        settle = runner._settle
        try:
            with patch.object(runner, "_settle", side_effect=runner.GroupUnsettled("synthetic unavailable observation")):
                with self.assertRaises(runner.GroupUnsettled) as failed:
                    self.run_code("import time;time.sleep(20)", timeout=1, rustup_home=rustup)
            error = failed.exception
            self.assertIsNotNone(error.process)
            self.assertIsNotNone(error.identity)
            retained = runner._UNSETTLED[error.process.pid]
            self.assertIs(retained["process"], error.process)
            self.assertEqual(retained["identity"], error.identity)
            self.assertEqual(retained["directory_fds"], error.directory_fds)
            self.assertEqual(len(error.directory_fds), 3)
            pending = set(runner._UNSETTLED)
            with self.assertRaises(runner.GroupUnsettled):
                self.run_code("raise SystemExit(0)")
            self.assertEqual(set(runner._UNSETTLED), pending, "an unresolved owner must block another spawn")
            for fd, expected in zip(error.directory_fds, (self.cwd, self.home, rustup)):
                os.fstat(fd)
                self.assertTrue(os.path.samefile(f"/proc/self/fd/{fd}", expected))
        finally:
            # Resolve only a process created by this test, through the original
            # retained identity while its numeric leader is still unreaped.
            for pid in set(runner._UNSETTLED) - already_owned:
                retained = runner._UNSETTLED[pid]
                self.assertIsInstance(retained, dict)
                process, identity = retained["process"], retained["identity"]
                settle(process, identity, stop=True)
                runner._UNSETTLED.pop(pid)
                process.stdout.close()
                process.stderr.close()
                for fd in retained["directory_fds"]:
                    os.close(fd)
        self.assertEqual(set(self.cwd.iterdir()), {self.home, rustup})


if __name__ == "__main__":
    unittest.main()
