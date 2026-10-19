"""Tests of final executable behavior, not just codec roundtrips."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nvpack import candidate_ids, pack_by_id, pack_variants


_PROGRAM = r'''
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void term(int sig){(void)sig;write(2,"handled-term\n",13);_exit(23);}
int main(int argc,char **argv){
 if(argc>1&&!strcmp(argv[1],"--pipe")){raise(SIGPIPE);return 0;}
 if(argc>1&&!strcmp(argv[1],"--term")){signal(SIGTERM,term);raise(SIGTERM);return 99;}
 if(argc>1&&!strcmp(argv[1],"--locale")){
  const char *p=getenv("LC_CTYPE");printf("%s:%s\n",p?"set":"unset",p?p:"");return 0;
 }
 if(argc>1&&!strcmp(argv[1],"--loader-env")){
  const char *k=getenv("k"),*v=getenv("v");printf("%s\n%s\n",k?k:"unset",v?v:"unset");return 0;
 }
 for(int i=1;i<argc;i++){printf("%zu:",strlen(argv[i]));fwrite(argv[i],1,strlen(argv[i]),stdout);putchar('\n');}
 for(int fd=3;fd<64;fd++)if(fcntl(fd,F_GETFD)>=0){fprintf(stderr,"leaked-fd:%d\n",fd);return 88;}
 fflush(stdout);
 unsigned char b[137];ssize_t n;
 while((n=read(0,b,sizeof b))>0){ssize_t i=0;while(i<n){ssize_t w=write(1,b+i,n-i);if(w<=0)return 89;i+=w;}}
 if(n<0)return 90;
 write(2,"native-stderr\n",14);
 return 7;
}
'''


@unittest.skipUnless(sys.platform.startswith("linux") and hasattr(os, "memfd_create")
                     and os.execve in os.supports_fd, "Linux memfd/fd-exec runtime required")
class NativePackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("cc")
        if compiler is None:
            raise unittest.SkipTest("a C compiler is needed for the native fixture")
        cls.owner = tempfile.TemporaryDirectory(prefix="nvpack test '")
        cls.root = Path(cls.owner.name)
        source = cls.root / "fixture.c"
        source.write_text(_PROGRAM)
        cls.native = cls.root / "native"
        subprocess.run([compiler, "-O2", str(source), "-o", str(cls.native)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        cls.raw = cls.native.read_bytes()
        # The test host is x86_64 in the supplied example environment; another
        # Linux host can still exercise non-BCJ codec families.
        cls.target = "x86_64-linux-gnu" if os.uname().machine in ("x86_64", "amd64") else "linux-native"
        cls.variants = pack_variants(cls.raw, target=cls.target)

    @classmethod
    def tearDownClass(cls):
        cls.owner.cleanup()

    def artifact(self, variant):
        path = self.root / ("packed $; ' " + variant["id"])
        path.write_bytes(variant["data"])
        path.chmod(0o700)
        return path

    def run_file(self, path, args=(), data=b"", **kwargs):
        return subprocess.run([str(path), *args], input=data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=15, **kwargs)

    def test_final_artifacts_preserve_binary_streams_argv_status_and_close_fds(self):
        args = ["", "space ; $ ( ) ' \" *", "line\nnext", "--literal-option"]
        data = bytes(range(256)) * 3 + b"\nlast line\x00"
        expected = self.run_file(self.native, args, data)
        self.assertEqual(expected.returncode, 7)
        for variant in self.variants:
            with self.subTest(pack=variant["id"]):
                actual = self.run_file(self.artifact(variant), args, data)
                self.assertEqual((actual.returncode, actual.stdout, actual.stderr),
                                 (expected.returncode, expected.stdout, expected.stderr))

    def test_selected_recipes_reproduce_full_bytes_and_embedded_offsets(self):
        for variant in self.variants:
            with self.subTest(pack=variant["id"]):
                again = pack_by_id(self.raw, target=self.target, pack_id=variant["id"])
                self.assertEqual(again["data"], variant["data"])
                self.assertTrue(again["roundtrip_verified"])
                self.assertEqual(len(variant["data"]),
                                 variant["payload_bytes"] + variant["loader_bytes"])
                self.assertEqual(variant["payload_offset"], variant["loader_bytes"])

    def test_python_signal_ignore_changes_do_not_leak_into_engine(self):
        packed = self.artifact(pack_by_id(self.raw, target=self.target, pack_id="gzip-9"))
        for ignored in (False, True):
            def setup():
                signal.signal(signal.SIGPIPE, signal.SIG_IGN if ignored else signal.SIG_DFL)
            with self.subTest(ignored=ignored):
                expected = self.run_file(self.native, ["--pipe"], preexec_fn=setup)
                actual = self.run_file(packed, ["--pipe"], preexec_fn=setup)
                self.assertEqual(expected.returncode, 0 if ignored else -signal.SIGPIPE)
                self.assertEqual(actual.returncode, expected.returncode)
                self.assertEqual(actual.stderr, expected.stderr)

    def test_engine_signal_handler_and_exit_status_remain_direct(self):
        expected = self.run_file(self.native, ["--term"])
        packed = self.artifact(pack_by_id(self.raw, target=self.target, pack_id="xz-6"))
        actual = self.run_file(packed, ["--term"])
        self.assertEqual(expected.returncode, 23)
        self.assertEqual((actual.returncode, actual.stdout, actual.stderr),
                         (expected.returncode, expected.stdout, expected.stderr))

    def test_python_locale_coercion_does_not_change_engine_environment(self):
        packed = self.artifact(pack_by_id(self.raw, target=self.target, pack_id="bzip2-9"))
        for locale in (None, "", "C", "C.UTF-8"):
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C"}
            if locale is not None:
                env["LC_CTYPE"] = locale
            with self.subTest(locale=locale):
                expected = self.run_file(self.native, ["--locale"], env=env)
                actual = self.run_file(packed, ["--locale"], env=env)
                self.assertEqual((actual.returncode, actual.stdout, actual.stderr),
                                 (expected.returncode, expected.stdout, expected.stderr))

    def test_shell_read_temporaries_do_not_replace_exported_environment(self):
        packed = self.artifact(pack_by_id(self.raw, target=self.target, pack_id="zlib-9"))
        env = dict(os.environ, k="original k ; ' $\n", v="original v")
        expected = self.run_file(self.native, ["--loader-env"], env=env)
        actual = self.run_file(packed, ["--loader-env"], env=env)
        self.assertEqual((actual.returncode, actual.stdout, actual.stderr),
                         (expected.returncode, expected.stdout, expected.stderr))

    def test_truncated_payload_fails_without_executing_partial_native_bytes(self):
        for codec in ("gzip-9", "zlib-9", "bzip2-9", "xz-6", "lzma-6"):
            with self.subTest(pack=codec):
                candidate = pack_by_id(self.raw, target=self.target, pack_id=codec)
                candidate["data"] = candidate["data"][:-5]
                actual = self.run_file(self.artifact(candidate), ["should-not-run"])
                self.assertNotEqual(actual.returncode, 0)
                self.assertEqual(actual.stdout, b"")
                self.assertNotIn(b"native-stderr", actual.stderr)
                self.assertTrue(actual.stderr)

    def test_no_extraction_files_in_declared_temporary_directory(self):
        temp_path = self.root / "owned tmp"
        temp_path.mkdir(exist_ok=True)
        env = dict(os.environ, TMPDIR=str(temp_path))
        packed = self.artifact(pack_by_id(self.raw, target=self.target, pack_id="xz-9"))
        before = list(temp_path.iterdir())
        result = self.run_file(packed, data=b"binary\0input", env=env)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(list(temp_path.iterdir()), before)

    def test_raw_identity_and_explicit_profile_errors(self):
        result = pack_variants(self.raw, target=self.target, codecs=[])
        self.assertEqual([item["id"] for item in result], ["raw"])
        self.assertIs(result[0]["data"], self.raw)
        with self.assertRaises(ValueError):
            pack_by_id(self.raw, target=self.target, pack_id="gzip")
        with self.assertRaises(ValueError):
            pack_variants(b"#!/bin/sh\nexit 0\n", target=self.target)
        with self.assertRaises(ValueError):
            candidate_ids("aarch64-linux-gnu", ["xz-bcj"])
        with self.assertRaises(ValueError):
            candidate_ids(self.target, ["unknown"])


if __name__ == "__main__":
    unittest.main()
