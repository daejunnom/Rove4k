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
    def test_bcj_scan_boundaries_and_random_roundtrips(self):
        for original, encoded in [(bytes.fromhex("e8fbffffff"), bytes.fromhex("e800000000")),
                                  (bytes.fromhex("e9ffffffff"), bytes.fromhex("e904000000")),
                                  (bytes.fromhex("90e8faffffff"), bytes.fromhex("90e800000000")),
                                  (bytes.fromhex("e8000000"), bytes.fromhex("e8000000")),
                                  (bytes.fromhex("e8e8e9e8e9"), bytes.fromhex("e8ede9e8e9"))]:
            self.assertEqual(loader._bcj(original), encoded)
            self.assertEqual(loader._bcj(encoded, inverse=True), original)
        rng = random.Random(20261020)
        cases = [b"", b"\xe8", b"\xe9"*131,
                 b"\xe8\xe9\xe8\xe9\xe8\xe9\0\0\0\0",
                 b"\x90"*65533+b"\xe8\xfb\xff\xff\xff",
                 bytes(range(256))*300]
        cases.extend(rng.randbytes(length) for length in range(520))
        for original in cases:
            self.assertEqual(loader._bcj(loader._bcj(original), inverse=True), original)

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
FILE*s=fopen("/proc/self/exe","rb");if(!s)return 6;
while((x=fread(b,1,sizeof b,s))>0)if(fwrite(b,1,x,stdout)!=(size_t)x)return 7;
if(ferror(s)||fclose(s))return 8;
fputs("stderr-preserved\\n",stderr);return 17;}
''', encoding="utf-8")
            subprocess.run(["cc", "-Os", "-s", "-pthread", str(c), "-o", str(work / "c")], check=True)
            programs = [work / "c"]
            rustc = os.environ.get("RUSTC") or shutil.which("rustc")
            if not rustc:
                self.fail("Rust compiler required: set RUSTC to its Linux path")
            rust = work / "driver.rs"
            rust.write_text('''use std::{io::{self,BufRead,Write},thread,env,fs::File};
fn main(){let mut b=String::new();io::stdin().lock().read_line(&mut b).unwrap();
let a:Vec<String>=env::args().collect();let n=thread::spawn(||73).join().unwrap();
print!("{}:{}:{}:{}:{}",a.len(),a[1],env::var("ROVE_TEST").unwrap(),n,b);
io::stdout().flush().unwrap();io::copy(&mut File::open("/proc/self/exe").unwrap(),&mut io::stdout()).unwrap();
eprintln!("stderr-preserved");std::process::exit(17);}
''', encoding="utf-8")
            subprocess.run([rustc, "-C", "opt-level=z", "-C", "strip=symbols", str(rust),
                            "-o", str(work / "rust")], check=True, timeout=120)
            programs.append(work / "rust")
            records = []
            for source in programs:
                env = {"ROVE_TEST": "env-value", "PATH": ""}
                expected = subprocess.run([str(source), "argv-value"], input=b"stdin-value\n",
                                          capture_output=True, env=env, timeout=5)
                for filter_mode in ("none", "bcj", "auto"):
                    target = source.with_suffix("."+filter_mode)
                    record = loader.pack_elf(source, target, filter=filter_mode)
                    actual = subprocess.run([str(target), "argv-value"], input=b"stdin-value\n",
                                            capture_output=True, env=env, timeout=5)
                    self.assertEqual(actual.returncode, 17)
                    self.assertEqual(actual.stdout, b"2:argv-value:env-value:73:stdin-value\n"+source.read_bytes())
                    self.assertEqual(actual.stderr, b"stderr-preserved\n")
                    self.assertEqual((actual.stdout, actual.stderr, actual.returncode),
                                     (expected.stdout, expected.stderr, expected.returncode))
                    self.assertIsNone(loader._elf(target.read_bytes())["interpreter"])
                    sizes = {candidate["filter"]: candidate["output_bytes"] for candidate in record["filter_candidates"]}
                    if filter_mode == "auto":
                        self.assertEqual(record["output_bytes"], min(sizes.values()))
                    else:
                        self.assertEqual(record["filter"], filter_mode)
                        self.assertEqual(record["output_bytes"], sizes[filter_mode])
                    self.assertEqual(record["within_size_limit"], record["output_bytes"] <= 4096)
                    record["runtime_validation"] = "exact_self_bytes_argv_env_stdio_threads_exit_pass"
                    records.append(record)
                # The auto-selected image must reproduce across temp build dirs.
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
            print(json.dumps({"native_checks": [
                {key: record[key] for key in ("input_bytes", "input_sha256", "output_bytes", "output_sha256",
                                              "payload_bytes", "loader_and_headers_bytes", "filter", "requested_filter",
                                              "within_size_limit", "runtime_validation", "filter_candidates")}
                for record in records]}, indent=2))


if __name__ == "__main__":
    unittest.main()
