"""Synthetic metadata tests for the build-only LZMA1EXT comparison."""
import json
import lzma
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import peer_lzma1ext_compare as compare
except ImportError:
    import peer_lzma1ext_compare as compare


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "result"
        self.root.mkdir()
        self.source = b"synthetic-source-do-not-export\n"
        self.header = b"synthetic-launcher\n"
        self.payload = lzma.compress(self.source, format=lzma.FORMAT_ALONE,
            filters=[{"id": lzma.FILTER_LZMA1, "dict_size": 65536, "lc": 2,
                      "lp": 0, "pb": 0, "mf": lzma.MF_BT4, "nice_len": 128}])
        self.attempts = []
        for index in (1, 2):
            attempt = self.root / ("attempt-" + str(index))
            attempt.mkdir()
            (attempt / "main.cpp").write_bytes(self.source)
            whole = self.header + self.payload
            whole_path = attempt / "c4ke-tcec"
            whole_path.write_bytes(whole)
            self.attempts.append({
                "source": {"bytes": len(self.source), "sha256": compare._sha(self.source)},
                "whole": {"path": str(whole_path), "bytes": len(whole), "sha256": compare._sha(whole)},
                "header": {"bytes": len(self.header), "sha256": compare._sha(self.header)},
                "selected_codec": {"mf": lzma.MF_BT4, "nice_len": 128},
            })
        self.receipt = {
            "complete": True, "reproducible": True, "peer": "c4ke",
            "revision": compare.EXPECTED_REVISION, "source_variant": "edit-castle-phalanx-v1",
            "launcher_variant": "gnu-tail-v1", "codec_search": {"name": "extended"},
            "resources": {"workers": 192, "tt_bytes": compare.TT_BYTES}, "attempts": self.attempts,
        }
        self.write_receipt()
        self.registry = patch.object(compare.registry, "inspect_exact_peer_proposal", return_value={
            "source_snapshot_inverse_verified": True, "retained_source_whole_consistent": True,
            "eligible_for_diagnostic": False, "eligible_for_scored_league": False,
        })
        self.registry.start()
        self.addCleanup(self.registry.stop)
        self.evidence = {"liblzma_header": "5.4.5", "liblzma_runtime": "5.4.5",
                         "xz_version": "xz (XZ Utils) 5.4.5",
                         "runtime_qualified": False, "league_qualified": False}

    def write_receipt(self):
        (self.root / "peer-exact.json").write_text(json.dumps(self.receipt), encoding="utf-8")

    def test_receipt_contains_sizes_and_hashes_but_no_source_or_engine_bytes(self):
        with patch.object(compare.trial, "encode_verified", return_value=(b"trial-payload", self.evidence)) as encode:
            result = compare.compare(self.root, "helper1", "helper2", "xz")
        self.assertEqual(encode.call_count, 2)
        self.assertEqual(result["trial_whole"]["bytes"], len(self.header) + len(b"trial-payload"))
        self.assertEqual(result["delta_bytes"], len(b"trial-payload") - len(self.payload))
        self.assertFalse(result["runtime_qualified"])
        self.assertFalse(result["league_qualified"])
        serialized = json.dumps(result).encode()
        self.assertNotIn(self.source, serialized)
        self.assertNotIn(self.header, serialized)
        self.assertNotIn(b"trial-payload", serialized)

    def test_unpinned_profile_or_changed_source_rejected(self):
        self.receipt["resources"]["tt_bytes"] = 128 << 30
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, "pinned P192"):
            compare.compare(self.root, "helper1", "helper2", "xz")
        self.receipt["resources"]["tt_bytes"] = compare.TT_BYTES
        self.write_receipt()
        (self.root / "attempt-2" / "main.cpp").write_bytes(b"tampered")
        with patch.object(compare.trial, "encode_verified", return_value=(b"trial", self.evidence)):
            with self.assertRaisesRegex(ValueError, "pin differs"):
                compare.compare(self.root, "helper1", "helper2", "xz")

    def test_two_helpers_must_emit_identical_payload_and_version(self):
        with patch.object(compare.trial, "encode_verified", side_effect=[
                (b"first", self.evidence), (b"second", self.evidence)]):
            with self.assertRaisesRegex(ValueError, "attempts or trial payloads differ"):
                compare.compare(self.root, "helper1", "helper2", "xz")
        bad_version = dict(self.evidence, liblzma_runtime="5.6.1")
        with patch.object(compare.trial, "encode_verified", return_value=(b"trial", bad_version)):
            with self.assertRaisesRegex(ValueError, "pinned version"):
                compare.compare(self.root, "helper1", "helper2", "xz")


if __name__ == "__main__":
    unittest.main()
