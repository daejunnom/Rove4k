"""Focused compiler, lexical, cleanup and fd-exec checks with owned tiny fixtures."""

from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from elf_loader import _elf
from minify import compact_source
import pack as packing
from pack import make_launcher
from compiler_group import transform_bootstrap
from functools import partial
make_launcher=partial(make_launcher, compiler_group=transform_bootstrap)


class PackagingTests(unittest.TestCase):
    def test_c_tokens_preprocessor_and_comment_boundaries(self):
        source = b'''/* comment\n#define NOT_CODE 1\n*/
#include <stdio.h>
#define F(x) ((x) + 1)
#define G (3)
int main(void) { int a = 7; int b = a + + 1; // ignored
  printf("%d %s\\n", F(b) + G, "/* literal */"); return 0; }
'''
        compact = compact_source(source, "c")
        self.assertIn(b"#define F(x)", compact)
        self.assertIn(b"#define G (3)", compact)
        self.assertIn(b"a+ +1", compact)
        self.assertNotIn(b"NOT_CODE", compact)
        if shutil.which("cc"):
            with tempfile.TemporaryDirectory(prefix="r4-lex-") as temporary:
                directory = Path(temporary)
                outputs = []
                for index, data in enumerate((source, compact)):
                    path = directory / (str(index) + ".c")
                    path.write_bytes(data)
                    subprocess.run(["cc", str(path), "-o", str(directory / str(index))], check=True)
                    outputs.append(subprocess.check_output([str(directory / str(index))]))
                self.assertEqual(outputs[0], outputs[1])

    def test_rust_nested_comment_raw_string_and_lifetime(self):
        source = b'''/* outer /* nested */ ignored */
fn use_ref<'a>(s: &'a str) -> &'a str { s }
fn r#type() -> usize { '0' as usize }
fn main() { let n = r#type(); let p = if n < -1i32 as usize { 1 } else { 0 };
  match "depth" { "depth" if p == 0 => (), _ => () }
  println!("{} {}", use_ref(r##"a/*b*/c"##), b'x'); }
'''
        compact = compact_source(source, "rust")
        self.assertIn(b"r##\"a/*b*/c\"##", compact)
        self.assertIn(b"&'a str", compact)
        compiler = os.environ.get("RUSTC", "rustc")
        if shutil.which(compiler):
            with tempfile.TemporaryDirectory(prefix="r4-rust-lex-") as temporary:
                directory = Path(temporary)
                outputs = []
                for index, data in enumerate((source, compact)):
                    path = directory / ("s" + str(index) + ".rs")
                    path.write_bytes(data)
                    subprocess.run([compiler, str(path), "-o", str(directory / str(index))], check=True)
                    outputs.append(subprocess.check_output([str(directory / str(index))]))
                self.assertEqual(outputs[0], outputs[1])

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("cc"), "Linux compiler required")
    def test_fd_exec_preserves_io_arguments_environment_and_cleans_before_exec(self):
        source = b'''#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int n,char**v){char s[80];fgets(s,sizeof s,stdin);printf("%s:%s:%s",v[1],getenv("R4_TEST"),s);fflush(stdout);sleep(1);return 17;}
'''
        with tempfile.TemporaryDirectory(prefix="r4-pack-test-") as temporary:
            directory = Path(temporary)
            source_path, native = directory / "a.c", directory / "a"
            source_path.write_bytes(source)
            subprocess.run(["cc", str(source_path), "-o", str(native)], check=True)
            for command, files in ((None, {"x": native.read_bytes()}),
                                   (["cc", "c/a.c", "-o", "x"], {"c/a.c": source})):
                for codec, transport in ((codec, transport) for codec in ("zlib", "bz2", "lzma")
                                          for transport in ("base85", "zip")):
                    script, record = make_launcher(files, command=command, codec=codec, transport=transport)
                    self.assertEqual(len(script), record["bytes"])
                    path = directory / "x"
                    path.write_bytes(script)
                    path.chmod(0o755)
                    scratch = directory / "scratch"
                    scratch.mkdir(exist_ok=True)
                    environment = os.environ.copy()
                    environment.update({"TMPDIR": str(scratch), "R4_TEST": "env"})
                    process = subprocess.Popen([str(path), "arg"], stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
                    try:
                        process.stdin.write(b"input\n")
                        process.stdin.close()
                        self.assertEqual(process.stdout.readline(), b"arg:env:input\n")
                        # The engine is still sleeping; every restored source and
                        # executable file must already be gone before it runs.
                        self.assertIsNone(process.poll())
                        self.assertEqual(list(scratch.iterdir()), [])
                        self.assertEqual(process.wait(timeout=5), 17)
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                        process.stdout.close()
                        process.stderr.close()

    @unittest.skipUnless(sys.platform == "linux", "Linux signal lifecycle required")
    def test_compiler_sigterm_is_forwarded_waited_and_temp_files_removed(self):
        with tempfile.TemporaryDirectory(prefix="r4-stop-test-") as temporary:
            directory = Path(temporary)
            ready = directory / "ready"
            compiler = directory / "compiler.py"
            compiler.write_text("import os,time\nopen(" + repr(str(ready)) + ",'w').write(str(os.getpid()))\ntime.sleep(30)\n")
            data, _ = make_launcher({"unused": b"x"},
                                    command=[sys.executable, str(compiler)])
            path = directory / "x"
            path.write_bytes(data)
            path.chmod(0o755)
            scratch = directory / "scratch"
            scratch.mkdir()
            environment = os.environ.copy()
            environment["TMPDIR"] = str(scratch)
            process = subprocess.Popen([str(path)], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(ready.exists(), "compiler did not start")
                child = int(ready.read_text())
                process.send_signal(signal.SIGTERM)
                self.assertEqual(process.wait(timeout=5), 143)
                self.assertEqual(list(scratch.iterdir()), [])
                with self.assertRaises(ProcessLookupError):
                    os.kill(child, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
                process.stderr.close()

    @unittest.skipUnless(sys.platform == "linux", "Linux launcher required")
    def test_missing_compiler_retains_primary_error_and_cleans_sources(self):
        with tempfile.TemporaryDirectory(prefix="r4-missing-test-") as temporary:
            directory = Path(temporary)
            data, _ = make_launcher({"c/a.c": b"int main(void){return 0;}"},
                                    command=["/unavailable-compiler/cc", "c/a.c", "-o", "x"])
            path = directory / "x"
            path.write_bytes(data)
            path.chmod(0o755)
            scratch = directory / "scratch"
            scratch.mkdir()
            environment = os.environ.copy()
            environment["TMPDIR"] = str(scratch)
            process = subprocess.run([str(path)], env=environment, capture_output=True, timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b"FileNotFoundError", process.stderr)
            self.assertNotIn(b"AttributeError", process.stderr)
            self.assertEqual(list(scratch.iterdir()), [])


@unittest.skipUnless(sys.platform == "linux" and shutil.which("cc"), "Linux ELF compiler required")
class SingleNativeTests(unittest.TestCase):
    """Actual ELF transport, short write, signal and pre-exec failure boundaries."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="r4-single-native-test-")
        cls.directory = Path(cls.temporary.name)
        source = cls.directory / "fixture.c"
        source.write_text('''#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
int main(int n,char**v){char b[4096];
for(int f=3;f<32;f++)if(fcntl(f,F_GETFD)!=-1)return 8;
if(n!=2||!fgets(b,sizeof b,stdin))return 9;
printf("%d|%s|%s|%s|%s",n,v[0],v[1],getenv("R4_NATIVE"),b);
ssize_t k=readlink("/proc/self/exe",b,sizeof b-1);if(k<0)return 10;
b[k]=0;printf("exe:%s\\nELF\\n",b);
FILE*f=fopen("/proc/self/exe","rb");if(!f)return 11;
while((k=fread(b,1,sizeof b,f)))if(fwrite(b,1,k,stdout)!=(size_t)k)return 12;
if(ferror(f)||fclose(f))return 13;
fputs("native-stderr\\n",stderr);return 17;}
''')
        subprocess.run(["cc", "-Os", "-s", str(source), "-o", str(cls.directory / "native")],
                       capture_output=True, check=True, timeout=60)
        cls.native = (cls.directory / "native").read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def launcher(self, backend, transport="base85"):
        return packing.make_launcher({"x": self.native}, command=None, codec="zlib", transport=transport,
                                     native_backend=backend, elf_admission=_elf)

    def backends(self):
        result = ["file"]
        try:
            packing.memfd_support()
        except ValueError:
            pass  # File remains applicable; no weaker memfd backend is run.
        else:
            result.append("memfd")
        return result

    def execute_source(self, script):
        # Run the emitted pre-exec code with scoped syscall injection, restoring
        # the actual signal handlers/mask even after a real signal boundary.
        handlers = {number: signal.getsignal(number) for number in (2, 15)}
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        try:
            exec(compile(script, "<single-native-test>", "exec"), {})
        finally:
            for number, handler in handlers.items():
                signal.signal(number, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)

    def test_explicit_elf_admission_and_memfd_policy_rejection(self):
        for arguments in ({"command": ["cc"]}, {"files": {"x": self.native, "y": b"extra"}},
                          {"files": {"x": b"#!/bin/sh\nexit 0\n"}}, {"elf_admission": None},
                          {"binary": "../x", "files": {"../x": self.native}}):
            values = {"files": {"x": self.native}, "command": None,
                      "native_backend": "file", "elf_admission": _elf}
            values.update(arguments)
            with self.subTest(arguments=tuple(arguments)), self.assertRaises(ValueError):
                packing.make_launcher(**values)
        with mock.patch.object(packing.Path, "read_text", return_value="2"), \
                mock.patch.object(os, "memfd_create", side_effect=AssertionError("no policy bypass")):
            with self.assertRaisesRegex(ValueError, "memfd_noexec=2"):
                self.launcher("memfd")

    def test_file_actual_native_argv_environment_stdio_and_preexec_cleanup(self):
        self.actual_contract("file")

    def test_memfd_actual_native_argv_environment_stdio_and_cloexec(self):
        try:
            packing.memfd_support()
        except ValueError as error:
            self.skipTest(str(error))
        self.actual_contract("memfd")

    def actual_contract(self, backend):
        for transport in ("base85", "zip"):
            with self.subTest(backend=backend, transport=transport), tempfile.TemporaryDirectory(prefix="r4-native-run-") as directory:
                root = Path(directory)
                path, scratch = root / "wrapper", root / "scratch"
                scratch.mkdir()
                data, record = self.launcher(backend, transport)
                path.write_bytes(data)
                path.chmod(0o755)
                environment = {**os.environ, "TMPDIR": str(scratch), "R4_NATIVE": "env-value"}
                actual = subprocess.run([str(path), "arg-value"], input=b"input-value\n", capture_output=True,
                                        env=environment, timeout=10)
                self.assertEqual(actual.returncode, 17, actual.stderr)
                self.assertEqual(actual.stderr, b"native-stderr\n")
                heading, native = actual.stdout.split(b"ELF\n", 1)
                prefix = ("2|" + str(path) + "|arg-value|env-value|input-value\nexe:").encode()
                self.assertTrue(heading.startswith(prefix), heading)
                self.assertIn(b"memfd:r4" if backend == "memfd" else b"r4-", heading[len(prefix):])
                self.assertTrue(heading.endswith(b" (deleted)\n"), heading)
                self.assertEqual(native, self.native)
                self.assertEqual(list(scratch.iterdir()), [])
                self.assertEqual(record["native_sha256"], packing.sha256(self.native))
                self.assertEqual(record["bytes"], len(data))

    def test_short_writes_reach_exact_elf_and_exec_failure_closes_fd(self):
        real_write = os.write
        for backend in self.backends():
            data, _ = self.launcher(backend)
            seen, writes = [], []
            primary = OSError(13, "injected native exec failure")

            def short_write(fd, value):
                writes.append(len(value))
                return real_write(fd, value[:7])

            def failed_exec(fd, argv, environment):
                self.assertEqual(os.pread(fd, len(self.native)+1, 0), self.native)
                self.assertFalse(os.get_inheritable(fd))
                seen.append(fd)
                raise primary

            with self.subTest(backend=backend), tempfile.TemporaryDirectory(prefix="r4-short-") as directory:
                with mock.patch.object(tempfile, "tempdir", directory), \
                        mock.patch.object(os, "write", side_effect=short_write), \
                        mock.patch.object(os, "execve", side_effect=failed_exec):
                    with self.assertRaises(OSError) as raised:
                        self.execute_source(data)
                self.assertIs(raised.exception, primary)
                self.assertEqual(len(seen), 1)
                self.assertGreater(len(writes), 1)
                with self.assertRaises(OSError):
                    os.fstat(seen[0])
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_write_error_zero_progress_and_secondary_close_preserve_primary(self):
        for backend in self.backends():
            for zero in (False, True):
                data, _ = self.launcher(backend)
                primary = OSError(28, "injected native write failure")
                write = mock.Mock(return_value=0) if zero else mock.Mock(side_effect=primary)
                with self.subTest(backend=backend, zero=zero), tempfile.TemporaryDirectory(prefix="r4-write-fail-") as directory:
                    with mock.patch.object(tempfile, "tempdir", directory), mock.patch.object(os, "write", write), \
                            mock.patch.object(os, "execve", side_effect=AssertionError("exec after failed write")):
                        with self.assertRaises(OSError) as raised:
                            self.execute_source(data)
                    if zero:
                        self.assertIn("no progress", str(raised.exception))
                    else:
                        self.assertIs(raised.exception, primary)
                    self.assertEqual(list(Path(directory).iterdir()), [])
            data, _ = self.launcher(backend)
            primary = OSError(13, "injected native exec failure")
            real_close = os.close
            executable_fd = []

            def failed_exec(fd, argv, environment):
                executable_fd.append(fd)
                raise primary

            def failed_close(fd):
                real_close(fd)
                if executable_fd and fd == executable_fd[0]:
                    raise OSError(5, "injected secondary close failure")

            output = io.StringIO()
            with self.subTest(backend=backend, secondary_close=True), \
                    mock.patch.object(os, "execve", side_effect=failed_exec), \
                    mock.patch.object(os, "close", side_effect=failed_close), redirect_stderr(output):
                with self.assertRaises(OSError) as raised:
                    self.execute_source(data)
            self.assertIs(raised.exception, primary)
            self.assertIn("secondary close failure", output.getvalue())
            executable_fd.clear()
            unavailable = io.StringIO()
            unavailable.close()
            with self.subTest(backend=backend, unavailable_stderr=True), \
                    mock.patch.object(os, "execve", side_effect=failed_exec), \
                    mock.patch.object(os, "close", side_effect=failed_close), redirect_stderr(unavailable):
                with self.assertRaises(OSError) as raised:
                    self.execute_source(data)
            self.assertIs(raised.exception, primary)

    def test_actual_int_term_during_write_keep_exit_mapping_and_cleanup(self):
        for backend in self.backends():
            for number in (signal.SIGINT, signal.SIGTERM):
                data, _ = self.launcher(backend)

                def interrupted(fd, value):
                    os.kill(os.getpid(), number)
                    raise AssertionError("handler did not interrupt write")

                with self.subTest(backend=backend, signal=number), tempfile.TemporaryDirectory(prefix="r4-native-signal-") as directory:
                    with mock.patch.object(tempfile, "tempdir", directory), \
                            mock.patch.object(os, "write", side_effect=interrupted), \
                            mock.patch.object(os, "execve", side_effect=AssertionError("exec after signal")):
                        with self.assertRaises(SystemExit) as raised:
                            self.execute_source(data)
                    self.assertEqual(raised.exception.code, 128+number)
                    self.assertEqual(list(Path(directory).iterdir()), [])

    def test_child_int_term_write_boundary_has_physical_130_143_exit(self):
        for backend in self.backends():
            for number in (signal.SIGINT, signal.SIGTERM):
                data, _ = self.launcher(backend)
                with self.subTest(backend=backend, signal=number), tempfile.TemporaryDirectory(prefix="r4-native-child-signal-") as directory:
                    root = Path(directory)
                    script, ready, scratch = root / "wrapper.py", root / "ready", root / "scratch"
                    script.write_bytes(data)
                    scratch.mkdir()
                    entry = ("import os,pathlib\n"
                             "def interrupted(fd,value):\n"
                             " pathlib.Path(" + repr(str(ready)) + ").write_text(str(os.getpid()))\n"
                             " os.kill(os.getpid()," + str(int(number)) + ")\n"
                             " raise AssertionError('handler did not interrupt write')\n"
                             "def unexpected_exec(*args):raise AssertionError('exec after signal')\n"
                             "os.write=interrupted;os.execve=unexpected_exec\n"
                             "exec(compile(pathlib.Path(" + repr(str(script)) + ").read_bytes(),'<native-signal-child>','exec'),{})\n")
                    result = subprocess.run([sys.executable, "-B", "-c", entry], capture_output=True,
                                            env={**os.environ, "TMPDIR": str(scratch)}, timeout=10)
                    self.assertTrue(ready.exists(), "fixture did not reach actual emitted put/write boundary")
                    self.assertEqual(result.returncode, 128+number, result.stderr)
                    self.assertEqual((result.stdout, result.stderr), (b"", b""))
                    self.assertEqual(list(scratch.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
