"""Focused compiler, lexical, cleanup and fd-exec checks with owned tiny fixtures."""

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from minify import compact_source
from pack import make_launcher


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
fn main() { let n = '0' as usize; let p = if n < -1i32 as usize { 1 } else { 0 };
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
                for codec in ("zlib", "bz2", "lzma"):
                    script, record = make_launcher(files, command=command, codec=codec)
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


if __name__ == "__main__":
    unittest.main()
