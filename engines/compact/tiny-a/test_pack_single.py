"""Whole-file reproduction and Linux lifecycle checks for the single-C launcher.

Every fixture and compiled product lives in an external TemporaryDirectory.
No engine code is imported and no speed or tournament eligibility is inferred.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

from pack_single import make_single, write_single


CODECS = ("zlib", "bz2", "lzma")
COMMAND = ["cc", "-O2", "-xc", "-", "-o", "x"]
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(tempfile.gettempdir()).resolve()
if BASE == ROOT or ROOT in BASE.parents:
    BASE = Path.home().resolve()
if BASE == ROOT or ROOT in BASE.parents:
    raise RuntimeError("an external fixture directory is required")


def temporary():
    return tempfile.TemporaryDirectory(prefix="r4-single-test-", dir=BASE)


def emit(directory, source, command, codec):
    data, record = make_single(source, command, codec)
    path = directory / "launcher"
    path.write_bytes(data)
    path.chmod(0o755)
    scratch = directory / "scratch"
    scratch.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment["TMPDIR"] = str(scratch)
    return path, scratch, environment, record


def cleanup(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()


class SingleSourceLauncherTests(unittest.TestCase):
    def test_all_codecs_reproduce_complete_files_and_report_actual_sizes(self):
        source = b"int main(void){return 7;}\n" * 4
        with temporary() as directory:
            directory = Path(directory)
            written = write_single(source, directory / "first", COMMAND)
            repeated = write_single(source, directory / "second", COMMAND)
            self.assertEqual([entry["codec"] for entry in written], list(CODECS))
            for codec, entry, again in zip(CODECS, written, repeated):
                with self.subTest(codec=codec):
                    data, record = make_single(source, COMMAND, codec)
                    self.assertEqual(data, make_single(source, COMMAND, codec)[0])
                    self.assertEqual(data, Path(entry["path"]).read_bytes())
                    self.assertEqual(data, Path(again["path"]).read_bytes())
                    self.assertEqual(len(data), record["bytes"])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
                    self.assertEqual(record["under_4096_bytes"], len(data) <= 4096)
                    self.assertEqual(record["external_programs"], ["python3", "cc"])
                    self.assertEqual(record["rules_eligibility"], "unproven_requires_runtime_and_full_rules_review")
                    self.assertTrue(data.startswith(b"#!/usr/bin/python3\n"))
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        self.assertEqual(archive.namelist(), ["__main__.py", "c"])
                        self.assertEqual(archive.read("c"), source)
                        self.assertEqual(archive.getinfo("c").compress_size, record["payload_bytes"])
                        self.assertEqual(record["launcher_bytes"], len(data) - archive.getinfo("c").compress_size)
                        for info in archive.infolist():
                            self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    if os.name == "posix":
                        self.assertEqual(Path(entry["path"]).stat().st_mode & 0o777, 0o755)
        with self.assertRaises(ValueError):
            make_single(source, COMMAND, "unknown")
        with self.assertRaises(ValueError):
            write_single(source, Path("relative-output"), COMMAND)

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("cc"), "Linux C compiler required")
    def test_all_codecs_compile_stdin_and_fd_exec_preserves_process_and_io(self):
        source = b'''#include <stdio.h>
#include <stdlib.h>
int main(int n,char **v){char s[80];
 if(n!=3||!fgets(s,sizeof s,stdin))return 31;
 printf("%s|%s|%s|%s",v[1],v[2],getenv("R4_SINGLE_TEST"),s);fflush(stdout);
 if(!fgets(s,sizeof s,stdin))return 32;
 return 17;}
'''
        with temporary() as directory:
            directory = Path(directory)
            for codec in CODECS:
                with self.subTest(codec=codec):
                    path, scratch, environment, record = emit(directory, source, COMMAND, codec)
                    environment["R4_SINGLE_TEST"] = "environment"
                    process = subprocess.Popen([str(path), "argument", "two words"], cwd=directory,
                                               env=environment, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        process.stdin.write(b"standard input\n")
                        process.stdin.flush()
                        with selectors.DefaultSelector() as selector:
                            selector.register(process.stdout, selectors.EVENT_READ)
                            self.assertTrue(selector.select(10), "compiled program did not produce output")
                        self.assertEqual(process.stdout.readline(), b"argument|two words|environment|standard input\n")
                        self.assertIsNone(process.poll(), "native program exited before process inspection")
                        self.assertEqual(list(scratch.iterdir()), [], "owned temporary directory survived fd-exec")
                        process_root = Path("/proc") / str(process.pid)
                        with (process_root / "exe").open("rb") as executable:
                            self.assertEqual(executable.read(4), b"\x7fELF")
                        self.assertTrue(os.readlink(process_root / "exe").endswith("/x (deleted)"))
                        status = dict(line.split(":", 1) for line in (process_root / "status").read_text().splitlines())
                        self.assertEqual(int(status["PPid"]), os.getpid(), "an intermediate wrapper parent remains")
                        children = process_root / "task" / str(process.pid) / "children"
                        self.assertEqual(children.read_text().strip(), "", "a compiler child remains after native exec")
                        self.assertEqual(path.stat().st_size, record["bytes"])
                        process.stdin.write(b"finish\n")
                        process.stdin.close()
                        self.assertEqual(process.wait(timeout=5), 17)
                        self.assertEqual(process.stderr.read(), b"")
                    finally:
                        cleanup(process)

    @unittest.skipUnless(sys.platform == "linux", "Linux launcher required")
    def test_missing_compiler_preserves_primary_error_and_cleans_owned_directory(self):
        with temporary() as directory:
            directory = Path(directory)
            for codec in CODECS:
                with self.subTest(codec=codec):
                    path, scratch, environment, _ = emit(directory, b"int main(void){return 0;}",
                                                          ["/r4-test-missing-compiler/cc", "-xc", "-", "-o", "x"], codec)
                    process = subprocess.run([str(path)], env=environment, capture_output=True, timeout=5)
                    self.assertNotEqual(process.returncode, 0)
                    self.assertIn(b"FileNotFoundError", process.stderr)
                    self.assertIn(b"/r4-test-missing-compiler/cc", process.stderr)
                    self.assertNotIn(b"During handling of the above exception", process.stderr)
                    self.assertNotIn(b"AttributeError", process.stderr)
                    self.assertNotIn(b"UnboundLocalError", process.stderr)
                    self.assertEqual(list(scratch.iterdir()), [])

    @unittest.skipUnless(sys.platform == "linux", "Linux process groups required")
    def test_sigterm_reaches_compiler_and_grandchild_and_waits_before_cleanup(self):
        with temporary() as directory:
            directory = Path(directory)
            for codec in CODECS:
                with self.subTest(codec=codec):
                    run = directory / codec
                    run.mkdir()
                    child_ready, child_signal = run / "child-ready", run / "child-signal"
                    parent_ready, parent_signal, waited = run / "parent-ready", run / "parent-signal", run / "waited"
                    grandchild = run / "grandchild.py"
                    grandchild.write_text(
                        "import os,signal,time\nfrom pathlib import Path\n"
                        "def stop(s,f):\n Path(" + repr(str(child_signal)) + ").write_text(str(s))\n raise SystemExit(0)\n"
                        "signal.signal(signal.SIGTERM,stop)\n"
                        "Path(" + repr(str(child_ready)) + ").write_text(str(os.getpid()))\n"
                        "while True:time.sleep(30)\n", encoding="utf-8")
                    compiler = run / "compiler.py"
                    compiler.write_text(
                        "import json,os,signal,subprocess,sys,time\nfrom pathlib import Path\n"
                        "child=None\n"
                        "def stop(s,f):\n Path(" + repr(str(parent_signal)) + ").write_text(str(s))\n"
                        " code=child.wait(timeout=3)\n Path(" + repr(str(waited)) + ").write_text(str(code))\n raise SystemExit(0)\n"
                        "signal.signal(signal.SIGTERM,stop)\n"
                        "child=subprocess.Popen([sys.executable," + repr(str(grandchild)) + "])\n"
                        "while not Path(" + repr(str(child_ready)) + ").exists():time.sleep(.005)\n"
                        "Path(" + repr(str(parent_ready)) + ").write_text(json.dumps({'pid':os.getpid(),'child':child.pid,'group':os.getpgrp(),'tmpdir':os.environ['TMPDIR'],'cwd':os.getcwd()}))\n"
                        "while True:time.sleep(30)\n", encoding="utf-8")
                    path, scratch, environment, _ = emit(run, b"int main(void){return 0;}",
                                                          [sys.executable, str(compiler)], codec)
                    process = subprocess.Popen([str(path)], env=environment, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    identities = None
                    try:
                        deadline = time.monotonic() + 5
                        while not parent_ready.exists() and time.monotonic() < deadline and process.poll() is None:
                            time.sleep(.01)
                        self.assertTrue(parent_ready.exists(), "compiler or grandchild did not become ready")
                        identities = json.loads(parent_ready.read_text())
                        self.assertEqual(identities["group"], identities["pid"], "compiler lacks its own process group")
                        self.assertEqual(os.getpgid(identities["child"]), identities["group"])
                        self.assertEqual(Path(identities["tmpdir"]).parent, scratch)
                        self.assertEqual(identities["cwd"], identities["tmpdir"])
                        process.send_signal(signal.SIGTERM)
                        self.assertEqual(process.wait(timeout=8), 143)
                        self.assertEqual(parent_signal.read_text(), str(signal.SIGTERM))
                        self.assertEqual(child_signal.read_text(), str(signal.SIGTERM))
                        self.assertEqual(waited.read_text(), "0", "compiler did not wait for its grandchild")
                        self.assertEqual(list(scratch.iterdir()), [])
                        self.assertFalse(Path(identities["tmpdir"]).exists())
                        self.assertEqual(process.stderr.read(), b"")
                        for pid in (identities["pid"], identities["child"]):
                            with self.assertRaises(ProcessLookupError):
                                os.kill(pid, 0)
                    finally:
                        if identities is not None:
                            try:
                                os.killpg(identities["group"], signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        cleanup(process)


if __name__ == "__main__":
    unittest.main()
