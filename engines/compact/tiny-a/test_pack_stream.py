"""Reproduction, byte preservation and process lifecycle for stream launchers."""
import ast
import bz2
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import selectors
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from pack_stream import CODECS, make_stream, write_stream
from functools import partial
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from compiler_group import transform_bootstrap
make_stream=partial(make_stream, compiler_group=transform_bootstrap)
write_stream=partial(write_stream, compiler_group=transform_bootstrap)


COMMAND = ["cc", "-O2", "-xc", "-", "-o", "x"]
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(tempfile.gettempdir()).resolve()
if BASE == ROOT or ROOT in BASE.parents:
    BASE = Path.home().resolve()
if BASE == ROOT or ROOT in BASE.parents:
    raise RuntimeError("an external fixture directory is required")
LINUX = sys.platform == "linux" and all(shutil.which(program) for program in ("sh", "tail", "xz", "gzip", "bzip2", "python3"))


def temporary():
    return tempfile.TemporaryDirectory(prefix="r4-stream-test-", dir=BASE)


def emit(directory, source, command, codec):
    data, record = make_stream(source, command, codec)
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
            process.wait(timeout=18)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()


class StreamLauncherTests(unittest.TestCase):
    def test_complete_file_reproduction_offset_and_actual_sizes(self):
        source = b"int main(void){return 7;}\n"
        decoders = {"xz": lzma.decompress, "gzip": gzip.decompress, "bzip2": bz2.decompress}
        with temporary() as directory:
            directory = Path(directory)
            first = write_stream(source, directory / "first", COMMAND)
            second = write_stream(source, directory / "second", COMMAND)
            self.assertEqual([item["codec"] for item in first], list(CODECS))
            for codec, record, repeated in zip(CODECS, first, second):
                with self.subTest(codec=codec):
                    data, generated = make_stream(source, COMMAND, codec)
                    self.assertEqual(data, make_stream(source, COMMAND, codec)[0])
                    self.assertEqual(data, Path(record["path"]).read_bytes())
                    self.assertEqual(data, Path(repeated["path"]).read_bytes())
                    self.assertEqual(len(data), generated["bytes"])
                    self.assertEqual(hashlib.sha256(data).hexdigest(), generated["sha256"])
                    offset = int(re.match(rb"#!/bin/sh\np=\$\(tail -c\+(\d+) ", data).group(1))
                    self.assertEqual(offset, generated["payload_offset_1based"])
                    self.assertEqual(offset - 1, generated["stub_bytes"])
                    self.assertEqual(generated["launcher_bytes"], generated["stub_bytes"])
                    self.assertEqual(len(data) - offset + 1, generated["payload_bytes"])
                    payload = decoders[codec](data[offset - 1:])
                    self.assertEqual(len(payload), generated["python_bytes"])
                    ast.parse(payload)
                    self.assertNotIn(b"zipfile", payload)
                    self.assertIn(b"sys.argv[1:]", payload)
                    self.assertEqual(generated["source_bytes"], len(source))
                    self.assertEqual(generated["external_programs"], ["sh", "tail", codec, "python3", "cc"])
                    self.assertTrue(generated["allowlisted_programs_only"])
                    self.assertEqual(generated["under_4096_bytes"], len(data) <= 4096)
                    self.assertEqual(generated["rules_eligibility"], "unproven_requires_runtime_and_full_rules_review")
                    if os.name == "posix":
                        self.assertEqual(Path(record["path"]).stat().st_mode & 0o777, 0o755)
        with self.assertRaises(ValueError):
            make_stream(source, COMMAND, "unknown")
        with self.assertRaises(ValueError):
            make_stream(source, [])
        with self.assertRaises(ValueError):
            make_stream(source, "cc")
        with self.assertRaises(TypeError):
            make_stream("not bytes", COMMAND)
        with self.assertRaises(ValueError):
            write_stream(source, "relative-output", COMMAND)

    @unittest.skipUnless(LINUX, "Linux shell and decoders required")
    def test_literal_encodings_preserve_exact_compiler_stdin_bytes(self):
        fixtures = (
            (b"int main(void){return 0;}\n", "raw-single"),
            (b"/* ''' */\n", "raw-double"),
            (b'/* \'\'\' """ */\n', "bytes-repr"),
            (b"line\r\n", "bytes-repr"),
            (b"zero\0byte", "bytes-repr"),
            (b"invalid\xffutf8", "bytes-repr"),
            (b"ends\\", "bytes-repr"),
            (b"ends\\\\", "raw-single"),
            (b"quote'", "raw-double"),
            ("/* 한글 é */\n".encode("utf-8"), "raw-single"),
            (b'const char*s="$(printf injected)";\n', "raw-single"),
        )
        with temporary() as directory:
            directory = Path(directory)
            captured = directory / "compiler-stdin"
            compiler = directory / "capture.py"
            compiler.write_text("import sys\nfrom pathlib import Path\nPath(" + repr(str(captured)) +
                                ").write_bytes(sys.stdin.buffer.read())\nraise SystemExit(23)\n", encoding="utf-8")
            for codec in CODECS:
                for source, kind in fixtures:
                    with self.subTest(codec=codec, source=repr(source)):
                        path, scratch, environment, record = emit(directory, source, [sys.executable, str(compiler)], codec)
                        process = subprocess.run([str(path)], env=environment, stdin=subprocess.DEVNULL,
                                                 capture_output=True, timeout=5)
                        self.assertEqual(process.returncode, 23, process.stderr)
                        self.assertEqual(process.stderr, b"")
                        self.assertEqual(captured.read_bytes(), source)
                        self.assertEqual(record["source_literal"], kind)
                        self.assertFalse(record["allowlisted_programs_only"])
                        self.assertEqual(list(scratch.iterdir()), [])

    @unittest.skipUnless(LINUX and shutil.which("cc"), "Linux C compiler required")
    def test_native_fd_exec_arguments_environment_io_status_and_cleanup(self):
        source = b'''#include <stdio.h>
#include <stdlib.h>
int main(int n,char **v){char s[80];
 if(n!=3||!fgets(s,sizeof s,stdin))return 31;
 printf("%s|%s|%s|%s",v[1],v[2],getenv("R4_STREAM_TEST"),s);fflush(stdout);
 if(!fgets(s,sizeof s,stdin))return 32;
 return 17;}
'''
        with temporary() as directory:
            directory = Path(directory)
            for codec in CODECS:
                with self.subTest(codec=codec):
                    path, scratch, environment, record = emit(directory, source, COMMAND, codec)
                    environment["R4_STREAM_TEST"] = "environment"
                    process = subprocess.Popen([str(path), "argument", "two words"], cwd=directory,
                                               env=environment, stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        process.stdin.write(b"standard input\n")
                        process.stdin.flush()
                        with selectors.DefaultSelector() as selector:
                            selector.register(process.stdout, selectors.EVENT_READ)
                            self.assertTrue(selector.select(10), "native program did not produce output")
                        self.assertEqual(process.stdout.readline(), b"argument|two words|environment|standard input\n")
                        self.assertIsNone(process.poll())
                        self.assertEqual(list(scratch.iterdir()), [])
                        proc = Path("/proc") / str(process.pid)
                        with (proc / "exe").open("rb") as executable:
                            self.assertEqual(executable.read(4), b"\x7fELF")
                        self.assertTrue(os.readlink(proc / "exe").endswith("/x (deleted)"))
                        status = dict(line.split(":", 1) for line in (proc / "status").read_text().splitlines())
                        self.assertEqual(int(status["PPid"]), os.getpid(), "an intermediate wrapper parent remains")
                        self.assertEqual((proc / "task" / str(process.pid) / "children").read_text().strip(), "")
                        self.assertEqual(path.stat().st_size, record["bytes"])
                        process.stdin.write(b"finish\n")
                        process.stdin.close()
                        self.assertEqual(process.wait(timeout=5), 17)
                        self.assertEqual(process.stderr.read(), b"")
                    finally:
                        cleanup(process)

    @unittest.skipUnless(LINUX, "Linux launcher required")
    def test_missing_compiler_primary_error_and_cleanup(self):
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
                    self.assertEqual(list(scratch.iterdir()), [])

    @unittest.skipUnless(LINUX, "Linux process groups required")
    def test_sigterm_forwards_to_compiler_group_and_waits_before_cleanup(self):
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
                        "import json,os,signal,subprocess,sys,time\nfrom pathlib import Path\nchild=None\n"
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
                    identities = None; retained=[]
                    try:
                        deadline = time.monotonic() + 5
                        while not parent_ready.exists() and time.monotonic() < deadline and process.poll() is None:
                            time.sleep(.01)
                        self.assertTrue(parent_ready.exists(), "compiler and grandchild did not become ready")
                        identities = json.loads(parent_ready.read_text())
                        for name in ("pid","child"):
                            retained.append(os.pidfd_open(identities[name]))
                        self.assertEqual(identities["group"], identities["pid"])
                        self.assertEqual(os.getpgid(identities["child"]), identities["group"])
                        self.assertEqual(Path(identities["tmpdir"]).parent, scratch)
                        self.assertEqual(identities["cwd"], identities["tmpdir"])
                        process.send_signal(signal.SIGTERM)
                        self.assertEqual(process.wait(timeout=8), 143)
                        self.assertEqual(parent_signal.read_text(), str(signal.SIGTERM))
                        self.assertEqual(child_signal.read_text(), str(signal.SIGTERM))
                        self.assertEqual(waited.read_text(), "0")
                        self.assertEqual(list(scratch.iterdir()), [])
                        self.assertFalse(Path(identities["tmpdir"]).exists())
                        self.assertEqual(process.stderr.read(), b"")
                        for fd in retained:
                            self.assertTrue(select.select([fd], [], [], 0)[0], "owned compiler identity still live")
                    finally:
                        for fd in retained:
                            try:
                                if not select.select([fd], [], [], 0)[0]:
                                    signal.pidfd_send_signal(fd, signal.SIGKILL)
                            finally:
                                os.close(fd)
                        cleanup(process)


if __name__ == "__main__":
    unittest.main()
