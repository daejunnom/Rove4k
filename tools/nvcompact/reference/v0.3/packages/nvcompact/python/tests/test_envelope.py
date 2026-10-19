"""Real suffix/decoder tests and separately mocked selection-control tests.

The UCI mock deliberately stands only for an acceptance predicate. It is not
evidence that these arbitrary byte fixtures implement UCI or chess semantics.
"""
from __future__ import annotations

from collections import Counter
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nvenvelope as envelope
import nvpack
import nvuci


CODECS = [{"format": "gzip", "level": 9}, {"format": "bzip2", "level": 9}]
HAS_DECODERS = all(shutil.which(name) for name in ("sh", "tail", "xz", "gzip", "bzip2"))


def fixture(root: Path, *, decoder="gzip -d", payload=None) -> tuple[Path, bytes, bytes]:
    payload = payload if payload is not None else b"abc" * 10000
    header = ("#!/bin/sh\ntail -n +4 \"$0\"|" + decoder + "\nexit\n").encode()
    original = header + gzip.compress(payload, compresslevel=1, mtime=0)
    path = root / "upstream"
    path.write_bytes(original)
    manifest = {"name": "independent codec fixture", "artifact": str(path), "category": "4k",
                "sha256": envelope.sha(original),
                "envelope": {"header": header.decode(), "decoder": decoder,
                             "payload_codec": {"format": "gzip"}}}
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path, original, payload


def protocol_result(verdict: str) -> dict:
    return {"verdict": verdict, "cases": [{"id": "selection_fixture", "status": verdict}],
            "observations": []}


@unittest.skipUnless(HAS_DECODERS, "Linux shell and xz/gzip/bzip2 are required")
class RealEnvelopeTests(unittest.TestCase):
    def test_tail_fixed_point_extracts_the_exact_binary_suffix(self):
        payload = bytes(range(256)) * 5 + b"\x00\n#!/bin/sh\ninvalid shell text\xff"
        recipe = {"format": "gzip", "level": 9}
        blob = envelope.compress(payload, recipe)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for padding in (0, 60, 960):
                # Four complete header lines mean the original tail starts at
                # line five, independently of the implementation's calculation.
                original = b'#!/bin/sh\n#' + b'x' * padding + b'\ntail -n +5 "$0"|xz -d\nexit\n'
                for style in ("original", "lines", "bytes"):
                    with self.subTest(padding=padding, style=style):
                        header = envelope.make_header(original, "xz -d", "gzip -d", style)
                        spec = {"header": header.decode(), "decoder": "gzip -d", "payload_codec": recipe}
                        self.assertEqual(envelope.extract(header + blob, spec)[1], payload)
                        path = root / "actual-wrapper"
                        path.write_bytes(header + blob)
                        run = subprocess.run([shutil.which("sh"), str(path)], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, timeout=3, check=False)
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertEqual(run.stdout, payload)

    def test_hash_header_and_offset_mismatches_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, original, _ = fixture(root)
            manifest = json.loads(path.read_text())
            spec = manifest["envelope"]
            with self.assertRaises(ValueError):
                envelope.extract(original, {**spec, "header": spec["header"].replace("exit", "exit ")})
            wrong_header = spec["header"].replace("+4", "+3")
            wrong_artifact = wrong_header.encode() + original[len(spec["header"].encode()):]
            with self.assertRaises(ValueError):
                envelope.extract(wrong_artifact, {**spec, "header": wrong_header})
            manifest["sha256"] = "0" * 64
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                envelope.run(path, root / "bad-hash", notation=False)

    def test_real_decoders_restore_all_supported_envelope_formats(self):
        payload = b"calls\xe8\x08\x00\x00\x00and\xe9\xff\xff\xff\xffdata\x00\n" * 90
        recipes = [dict(format=fmt, x86=x86, preset=6, dict_size=4096, lc=0, lp=0, pb=0)
                   for fmt, x86 in (("alone", False), ("xz", False), ("raw", False), ("raw", True))]
        recipes += CODECS
        for recipe in recipes:
            with self.subTest(recipe=recipe):
                blob = envelope.compress(payload, recipe)
                self.assertEqual(envelope.decode(blob, recipe), payload)
                self.assertEqual(envelope._actual_decoder(blob, envelope.decoder_for(recipe), payload)["status"], "pass")

    def test_bad_original_decoder_without_payload_pin_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # The declared gzip payload is valid, but bzip2 cannot execute the
            # original header's decoder contract. No engine-specific exception.
            path, _, _ = fixture(root, decoder="bzip2 -d")
            with self.assertRaises(ValueError), mock.patch.object(envelope, "codec_recipes", return_value=CODECS):
                envelope.run(path, root / "rejected", notation=False)

    def test_pinned_payload_can_record_original_decoder_failure_without_claiming_equivalence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, _, payload = fixture(root, decoder="bzip2 -d")
            manifest = json.loads(path.read_text())
            manifest["payload_sha256"] = envelope.sha(payload)
            path.write_text(json.dumps(manifest))
            with mock.patch.object(envelope, "codec_recipes", return_value=CODECS):
                result = envelope.run(path, root / "repaired-deployment", notation=False)
            self.assertEqual(result["original_decoder_check"]["status"], "fail")
            self.assertFalse(result["original_deployment_equivalent"])
            self.assertEqual(result["smallest_payload_check"]["decoder"]["status"], "pass")
            self.assertEqual((root / "repaired-deployment" / "original-payload").read_bytes(), payload)
            manifest["payload_sha256"] = "0" * 64
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError), mock.patch.object(envelope, "codec_recipes", return_value=CODECS):
                envelope.run(path, root / "wrong-pin", notation=False)

    def test_successful_decoder_with_wrong_output_is_never_a_payload_pin_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # A zero-exit no-output command contradicts the declared nonempty
            # payload. Pinning a payload cannot excuse that successful mismatch.
            path, _, payload = fixture(root, decoder="true")
            manifest = json.loads(path.read_text())
            manifest["payload_sha256"] = envelope.sha(payload)
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError), mock.patch.object(envelope, "codec_recipes", return_value=CODECS):
                envelope.run(path, root / "rejected", notation=False)

    def test_submitted_compressed_bytes_remain_available_after_header_shortening(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, original, payload = fixture(root)
            original_header = json.loads(path.read_text())["envelope"]["header"].encode()
            with mock.patch.object(envelope, "codec_recipes", return_value=[]):
                result = envelope.run(path, root / "result", notation=False)
            winner = (root / "result" / "smallest").read_bytes()
            self.assertLess(len(winner), len(original))
            self.assertTrue(winner.endswith(original[len(original_header):]))
            spec = {"header": result["winner"]["header"], "decoder": "gzip -d", "payload_codec": {"format": "gzip"}}
            self.assertEqual(envelope.extract(winner, spec)[1], payload)


@unittest.skipUnless(HAS_DECODERS, "Linux shell and xz/gzip/bzip2 are required")
class SelectionControlTests(unittest.TestCase):
    def test_failed_smallest_selects_the_next_passing_distinct_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, original, _ = fixture(root)
            def checker(command, config):
                data = Path(command[0]).read_bytes()
                return protocol_result("fail" if b"bzip2 -d" in data else "pass")
            with mock.patch.object(envelope, "codec_recipes", return_value=CODECS), \
                    mock.patch.object(nvuci, "verify_engine", side_effect=checker):
                result = envelope.run(path, root / "result", notation=False, uci=True)
            self.assertIsNotNone(result["accepted"])
            self.assertLess(result["winner"]["bytes"], result["accepted"]["bytes"])
            self.assertLess(result["accepted"]["bytes"], len(original))
            self.assertEqual(result["protocol_attempts"][0]["verdict"], "fail")
            self.assertEqual(envelope.sha((root / "result" / "accepted").read_bytes()),
                             result["accepted"]["sha256"])

    def test_inherited_failure_never_promotes_identity_and_duplicate_sha_is_screened_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, _, _ = fixture(root)
            observed = []
            def checker(command, config):
                observed.append(envelope.sha(Path(command[0]).read_bytes()))
                return protocol_result("fail")
            with mock.patch.object(envelope, "codec_recipes", return_value=CODECS + CODECS), \
                    mock.patch.object(nvuci, "verify_engine", side_effect=checker):
                result = envelope.run(path, root / "result", notation=False, uci=True)
            self.assertIsNone(result["accepted"])
            self.assertFalse((root / "result" / "accepted").exists())
            attempts = result["protocol_attempts"]
            self.assertEqual(len({item["sha256"] for item in attempts}), len(attempts))
            self.assertTrue(all(item["verdict"] == "fail" for item in attempts))

    def test_passing_identity_remains_fallback_when_protocol_budget_is_exhausted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, original, _ = fixture(root)
            def checker(command, config):
                return protocol_result("pass" if Path(command[0]).read_bytes() == original else "fail")
            with mock.patch.object(envelope, "codec_recipes", return_value=CODECS), \
                    mock.patch.object(nvuci, "verify_engine", side_effect=checker):
                result = envelope.run(path, root / "result", notation=False, uci=True, max_protocol_candidates=1)
            self.assertIsNotNone(result["accepted"])
            self.assertEqual((root / "result" / "accepted").read_bytes(), original)

    def test_final_replay_failure_aborts_without_publishing_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, _, _ = fixture(root)
            seen = Counter()
            def checker(command, config):
                key = envelope.sha(Path(command[0]).read_bytes())
                seen[key] += 1
                return protocol_result("fail" if seen[key] > 1 else "pass")
            with mock.patch.object(envelope, "codec_recipes", return_value=CODECS), \
                    mock.patch.object(nvuci, "verify_engine", side_effect=checker), self.assertRaises(ValueError):
                envelope.run(path, root / "result", notation=False, uci=True)
            self.assertFalse((root / "result" / "accepted").exists())

    def test_nonreproducing_compressor_is_a_hard_error_not_identity_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, _, payload = fixture(root)
            calls = 0
            def unstable(data, recipe):
                nonlocal calls
                calls += 1
                return gzip.compress(data, compresslevel=9, mtime=calls)
            with mock.patch.object(envelope, "codec_recipes", return_value=[CODECS[0]]), \
                    mock.patch.object(envelope, "compress", side_effect=unstable), self.assertRaises(ValueError):
                envelope.run(path, root / "result", notation=False)
            self.assertFalse((root / "result" / "accepted").exists())


@unittest.skipUnless(shutil.which("cc") and sys.platform == "linux", "native Linux C compiler required")
class NativeEnvelopeTests(unittest.TestCase):
    def test_native_portfolio_restores_the_entire_original_elf(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "original-elf"
            subprocess.run([shutil.which("cc"), "-Os", "-s", "-x", "c", "-o", str(binary), "-"],
                           input=b"int main(void){return 17;}\n", stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=30, check=True)
            original = binary.read_bytes()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"name": "native fixture", "artifact": str(binary),
                                             "category": "4k", "sha256": envelope.sha(original)}))
            actual_pack = nvpack.pack_by_id
            def checked_pack(data, **kwargs):
                self.assertEqual(data, original, "whole-ELF restoration contract must retain every original header byte")
                return actual_pack(data, **kwargs)
            with mock.patch.object(nvpack, "pack_by_id", side_effect=checked_pack):
                result = envelope.run(manifest, root / "result", notation=False)
            self.assertEqual(binary.read_bytes(), original)
            self.assertLessEqual(result["winner"]["bytes"], len(original))
            run = subprocess.run([str(root / "result" / "smallest")], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, timeout=3, check=False)
            self.assertEqual(run.returncode, 17, run.stderr)


if __name__ == "__main__":
    unittest.main()
