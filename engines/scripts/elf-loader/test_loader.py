#!/usr/bin/env python3
"""Run on Linux x86-64: python3 engines/scripts/elf-loader/test_loader.py.

RUSTC can name the Linux Rust compiler if it is not on PATH. Generated source,
executables and metadata live only in an owned temporary artifact directory.
"""
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

_spec = importlib.util.spec_from_file_location("elf_loader", Path(__file__).resolve().parent.parent / "elf_loader.py")
loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loader)


class Compression(unittest.TestCase):
    def test_boundary_streams(self):
        # Hand-written expected streams exercise forward overlap and both
        # literal/match length bounds independently of compressor choices.
        for stream, expected in [(b"\0x\x80\1\0", b"xxxx"),
                                 (b"\0x\xff\1\0", b"x"*131),
                                 (bytes([127])+bytes(range(128)), bytes(range(128)))]:
            self.assertEqual(loader._decompress(stream, len(expected)), expected)
        for stream, size in [(b"\x80\0\0", 3), (b"\x80\1\0", 3),
                             (b"\x7fabc", 128), (b"\x80\1", 3), (b"\0x", 2)]:
            with self.assertRaises(ValueError):
                loader._decompress(stream, size)

    def test_long_window_and_incompressible_bytes(self):
        rng = random.Random(20261020)
        block = rng.randbytes(70000)
        for data in [b"", b"a"*131073, block, block+block[:2048], bytes(range(256))*300]:
            packed = loader._compress(data)
            self.assertEqual(loader._decompress(packed, len(data)), data)
            self.assertEqual(loader._compress(data), packed)


class Native(unittest.TestCase):
    def test_dynamic_c_and_standard_rust(self):
        with tempfile.TemporaryDirectory(prefix="rove4k-elf-contract-") as directory:
            work = Path(directory)
            c = work / "driver.c"
            c.write_text('''#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static void *worker(void *p){*(int*)p=73;return 0;}
int main(int n,char**a){char b[128];int x=0;pthread_t t;
if(!fgets(b,sizeof b,stdin))return 4;
if(pthread_create(&t,0,worker,&x)||pthread_join(t,0))return 5;
printf("%d:%s:%s:%d:%s",n,a[1],getenv("ROVE_TEST"),x,b);
fputs("stderr-preserved\\n",stderr);return 17;}
''', encoding="utf-8")
            subprocess.run(["cc", "-Os", "-s", "-pthread", str(c), "-o", str(work / "c")], check=True)
            programs = [work / "c"]
            rustc = os.environ.get("RUSTC") or shutil.which("rustc")
            if not rustc:
                self.fail("Rust compiler required: set RUSTC to its Linux path")
            rust = work / "driver.rs"
            rust.write_text('''use std::{io::{self,BufRead},thread,env};
fn main(){let mut b=String::new();io::stdin().lock().read_line(&mut b).unwrap();
let a:Vec<String>=env::args().collect();let n=thread::spawn(||73).join().unwrap();
print!("{}:{}:{}:{}:{}",a.len(),a[1],env::var("ROVE_TEST").unwrap(),n,b);
eprintln!("stderr-preserved");std::process::exit(17);}
''', encoding="utf-8")
            subprocess.run([rustc, "-C", "opt-level=z", "-C", "strip=symbols", str(rust),
                            "-o", str(work / "rust")], check=True, timeout=120)
            programs.append(work / "rust")
            records = []
            for source in programs:
                target = source.with_suffix(".packed")
                record = loader.pack_elf(source, target)
                env = {"ROVE_TEST": "env-value", "PATH": ""}
                expected = subprocess.run([str(source), "argv-value"], input=b"stdin-value\n",
                                          capture_output=True, env=env, timeout=5)
                actual = subprocess.run([str(target), "argv-value"], input=b"stdin-value\n",
                                        capture_output=True, env=env, timeout=5)
                self.assertEqual(actual.returncode, 17)
                self.assertEqual(actual.stdout, b"2:argv-value:env-value:73:stdin-value\n")
                self.assertEqual(actual.stderr, b"stderr-preserved\n")
                self.assertEqual((actual.stdout, actual.stderr, actual.returncode),
                                 (expected.stdout, expected.stderr, expected.returncode))
                self.assertIsNone(loader._elf(target.read_bytes())["interpreter"])
                repeat = source.with_suffix(".repeat")
                repeat_record = loader.pack_elf(source, repeat)
                self.assertEqual(target.read_bytes(), repeat.read_bytes())
                self.assertEqual(record["output_sha256"], repeat_record["output_sha256"])
                # Corrupt the first embedded token into an illegal backreference.
                broken = bytearray(target.read_bytes())
                start = len(broken)-record["payload_bytes"]
                broken[start:start+3] = b"\x80\0\0"
                invalid = source.with_suffix(".invalid")
                invalid.write_bytes(broken)
                invalid.chmod(0o755)
                rejected = subprocess.run([str(invalid)], capture_output=True, env=env, timeout=5)
                self.assertEqual(rejected.returncode, 126)
                self.assertEqual(rejected.stderr, b"Rove4k ELF restore failed\n")
                record["runtime_validation"] = "argv_env_stdio_threads_exit_and_repeat_pass"
                records.append(record)
            print(json.dumps({"native_checks": records}, indent=2))


if __name__ == "__main__":
    unittest.main()
