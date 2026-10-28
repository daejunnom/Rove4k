"""Small contract fixtures; actual encoding and engine builds belong to CI."""
import json
import lzma
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import rove_lzma1ext_compare as subject


class CompareTests(unittest.TestCase):
    def make_build(self, root, family, profile):
        source = b"int main(void){return 0;}\n"
        header = b"#!/bin/sh\ntail -n+3 \"$0\"|xz -d\n"
        payload = lzma.compress(source, format=lzma.FORMAT_ALONE)
        pieces = {"main.c": source, "header.sh": header, "payload.lzma": payload, "x": header + payload}
        for directory in (root, root / "first", root / "repeat"):
            directory.mkdir(exist_ok=True)
            for name, data in pieces.items():
                (directory / name).write_bytes(data)
        recipe = {"format": "lzma-alone", "filter": "LZMA1", "check": "NONE",
                  "preset": 6, "extreme": False, "lc": 2, "lp": 0, "pb": 0,
                  "mf": "BT2", "nice_len": 24, "dictionary_bytes": 16384}
        manifest = {"complete": True, "reproducible": True, "family": family,
                    "resources": {"id": profile}, "compression": recipe}
        if family == "B":
            manifest.update(post_profile={"variant": "tcec-final-lf"},
                            post_spelling={"selection": "league-atomic"})
        else:
            manifest["post_league"] = {"variant": subject.VARIANTS[family]}
        (root / "build.json").write_text(json.dumps(manifest), encoding="utf-8")
        return payload

    def run_case(self, root, family, profile, payload):
        admitted = SimpleNamespace(family=family, profile_id=profile, representation="source-jit")
        proof = {"liblzma_header": "5.4.5", "liblzma_runtime": "5.4.5",
                 "xz_version": "xz (XZ Utils) 5.4.5", "runtime_qualified": False,
                 "league_qualified": False}
        with patch.object(subject, "admit", return_value=admitted), patch.object(
                subject.trial, "encode_verified", return_value=(payload, proof)) as encode:
            result = subject.compare(root, family, profile, subject.VARIANTS[family], "h1", "h2", "xz")
        return result, encode

    def test_all_families_and_profiles_keep_baseline_settings_and_scope(self):
        for family in subject.VARIANTS:
            for profile in subject.PROFILES:
                with self.subTest(family=family, profile=profile), tempfile.TemporaryDirectory() as path:
                    root = Path(path)
                    payload = self.make_build(root, family, profile)
                    result, encode = self.run_case(root, family, profile, payload)
                    self.assertEqual(encode.call_count, 2)
                    self.assertEqual(encode.call_args.kwargs["dict_size"], 16384)
                    self.assertEqual(encode.call_args.kwargs["mf"], lzma.MF_BT2)
                    self.assertEqual(result["delta_bytes"], 0)
                    self.assertFalse(result["runtime_qualified"] or result["league_qualified"])
                    self.assertFalse(result["baseline_codec_internals_identical"])

    def test_changed_retained_attempt_is_rejected(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            payload = self.make_build(root, "A", "test-p16")
            (root / "repeat" / "header.sh").write_bytes(b"modified")
            with self.assertRaises(ValueError):
                self.run_case(root, "A", "test-p16", payload)

    def test_wrong_family_variant_and_mismatched_producer_are_rejected(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            payload = self.make_build(root, "A", "test-p16")
            with self.assertRaises(ValueError):
                subject.compare(root, "D", "test-p16", "control", "h1", "h2", "xz")
            with self.assertRaises(ValueError):
                self.run_case(root, "C", "test-p16", payload)


if __name__ == "__main__":
    unittest.main()
