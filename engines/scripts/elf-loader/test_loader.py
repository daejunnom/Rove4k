#!/usr/bin/env python3
"""Run on Linux x86-64: python3 engines/scripts/elf-loader/test_loader.py.

RUSTC can name the Linux Rust compiler if it is not on PATH. Generated source,
executables and metadata live only in an owned temporary artifact directory.
"""
import importlib.util
from functools import lru_cache
from itertools import product
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

_spec = importlib.util.spec_from_file_location("elf_loader", Path(__file__).resolve().parent.parent / "elf_loader.py")
loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(loader)


class Compression(unittest.TestCase):
    def test_optimal_exact_cost_against_small_independent_token_oracle(self):
        cases = [bytes(values) for size in range(9) for values in product(b"ab", repeat=size)]
        cases.extend((b"abcXabcY", b"abcdXabcdYabcdZ", bytes(range(16))))
        for data in cases:
            @lru_cache(None)
            def cost(at):
                if at == len(data):
                    return 0
                best = min(length+1+cost(at+length)
                           for length in range(1, min(128, len(data)-at)+1))
                # These small cases have fewer than 64 prior candidates and no
                # window expiry. Enumerate every valid token, independently of
                # the production match table, ring tree and literal queue.
                for previous in range(at):
                    length = 0
                    while length < min(130, len(data)-at) and data[previous+length] == data[at+length]:
                        length += 1
                    for count in range(3, length+1):
                        best = min(best, 3+cost(at+count))
                return best
            with self.subTest(data=data):
                packed = loader.compress_payload(data, encoder="optimal64-v1")
                self.assertEqual(len(packed), cost(0))
                self.assertEqual(loader._decompress(packed, len(data)), data)
                self.assertEqual(loader.compress_payload(data, encoder="optimal64-v1"), packed)
                self.assertLessEqual(len(packed), len(loader._compress(data)))
        self.assertEqual(len(loader._compress(b"abcXabcY")), 10)
        self.assertEqual(loader.compress_payload(b"abcXabcY", encoder="optimal64-v1"), b"\7abcXabcY")

    def test_optimal_selector_global_ties_and_finite_domain(self):
        for data in (b"", b"x", bytes(range(128)), b"a"*131):
            greedy = loader._compress(data)
            self.assertEqual(loader.compress_payload(data), greedy)
            self.assertEqual(loader.compress_payload(data, encoder="greedy64-v1"), greedy)
            self.assertEqual(loader.compress_payload(data, encoder="optimal64-v1"), greedy)
        with self.assertRaises(ValueError):
            loader.compress_payload(b"abc", encoder="unknown")
        with patch.object(loader, "_compress", side_effect=AssertionError("oversize input reached codec")):
            with self.assertRaisesRegex(ValueError, "256 KiB"):
                loader.compress_payload(b"x"*(loader.MAX_OPTIMAL_INPUT+1), encoder="optimal64-v1")
        with patch.object(loader.time, "monotonic", return_value=2):
            with self.assertRaises(TimeoutError):
                loader.compress_payload(b"abc", encoder="optimal64-v1", deadline=1)

    def test_optimal_overlap_window_and_length_boundaries(self):
        rng = random.Random(20261027)
        block = rng.randbytes(65535)
        cases = (b"a"*131073, b"abc"*2000, block+block[:130], bytes(range(256))*300)
        for data in cases:
            with self.subTest(size=len(data)):
                greedy = loader._compress(data)
                packed = loader.compress_payload(data, encoder="optimal64-v1")
                self.assertEqual(loader._decompress(packed, len(data)), data)
                self.assertLessEqual(len(packed), len(greedy))
                self.assertEqual(loader.compress_payload(data, encoder="optimal64-v1"), packed)
        packed = loader.compress_payload(block+block[:130], encoder="optimal64-v1")
        at, distances = 0, []
        while at < len(packed):
            control = packed[at]
            at += 1
            if control < 128:
                at += control+1
            else:
                distances.append(int.from_bytes(packed[at:at+2], "little"))
                at += 2
        self.assertIn(65535, distances)

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
                    self.assertNotIn("encoder", record)
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
                if source.name == "c":
                    # The bounded new encoder uses the unchanged native decoder
                    # and must still expose every original compiler ELF byte.
                    optimal_target = source.with_suffix(".optimal")
                    optimal_record = loader.pack_elf(source, optimal_target, encoder="optimal64-v1")
                    optimal_actual = subprocess.run([str(optimal_target), "argv-value"], input=b"stdin-value\n",
                                                    capture_output=True, env=env, timeout=5)
                    self.assertEqual((optimal_actual.stdout, optimal_actual.stderr, optimal_actual.returncode),
                                     (expected.stdout, expected.stderr, expected.returncode))
                    self.assertEqual(optimal_record["encoder"], "optimal64-v1")
                    self.assertEqual(optimal_record["codec"], "rove4k-lz-runs-v1")
                    self.assertLessEqual(optimal_record["output_bytes"], record["output_bytes"])
                    self.assertEqual(optimal_record["output_bytes"],
                                     min(row["output_bytes"] for row in optimal_record["filter_candidates"]))
                    optimal_record["runtime_validation"] = "exact_self_bytes_argv_env_stdio_threads_exit_pass"
                    records.append(optimal_record)
            print(json.dumps({"native_checks": [
                {"encoder": record.get("encoder", "greedy64-v1"),
                 **{key: record[key] for key in ("input_bytes", "input_sha256", "output_bytes", "output_sha256",
                                              "payload_bytes", "loader_and_headers_bytes", "filter", "requested_filter",
                                               "within_size_limit", "runtime_validation", "filter_candidates")}}
                for record in records]}, indent=2))


if __name__ == "__main__":
    unittest.main()
