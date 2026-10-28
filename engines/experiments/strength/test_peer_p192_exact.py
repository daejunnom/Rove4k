"""Synthetic source transforms and index properties; no peer engines run."""
from __future__ import annotations

import copy
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import peer_p192_exact as exact
except ImportError:
    import peer_p192_exact as exact


def sources(name):
    """Small synthetic fragments; these are not copies of upstream files."""
    if name == "ice4":
        return {
            "minifier/preprocess.rs": (b'"DEFAULT_TT_BITS" if tcec => "35"\n'
                                        b'"THREADS" if tcec => "256"\n'),
            "src/board.cpp": (b"prefix\ncalloc(1ull << DEFAULT_TT_BITS, 8);\n"
                              b"TT[zobrist >> (64 - TT_BITS)];\nsuffix\n"),
            "src/search.cpp": b"prefix\nTT[board.zobrist >> (64 - TT_BITS)];\nsuffix\n",
        }
    if name == "c4ke":
        return {
            "minifier/mini.h": (b'if (is_tcec && name == "THREADS") {\n            value = "256";\n        }\n'
                                 b'if (is_tcec && name == "TT_BITS") {\n            value = "35";\n        }\n'
                                 b'if (is_tcec && name == "TT_SHIFT") {\n            value = "29";\n        }\n'),
            "src/chess.cpp": b"prefix\ncalloc(1ull << TT_BITS, 8);\nsuffix\n",
            "src/board.cpp": b"prefix\nTTABLE[hash >> TT_SHIFT];\nsuffix\n",
            "src/search.cpp": (b"prefix\nTTABLE[board.hash >> TT_SHIFT];\n"
                               b"TTABLE[board.hash >> TT_SHIFT];\nsuffix\n"),
        }
    raise ValueError(name)


def pin_synthetic(name, values):
    """Replace only that peer's upstream hashes with the synthetic fixture."""
    return patch.dict(exact.peers.SOURCE_BLOBS,
                      {name: {path: exact.peers.git_blob(data) for path, data in values.items()}})


class IndexProperties(unittest.TestCase):
    def test_exact_192gib_boundaries_and_no_64bit_overflow(self):
        count = 3 * (1 << 33)
        self.assertEqual(exact.ENTRIES, 25_769_803_776)
        self.assertEqual(exact.ENTRIES, count)
        self.assertEqual(exact.TT_BYTES, 192 * (1 << 30))
        self.assertEqual(exact.index(0), 0)
        self.assertEqual(exact.index((1 << 64) - 1), count - 1)
        self.assertLess(((1 << 48) - 1) * 3, 1 << 50)
        for value in (False, True, -1, 1 << 64, 0.0, "1", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                exact.index(value)

    def test_low_tag_independence_and_index_bounds(self):
        rand = random.Random(71191)
        for _ in range(10_000):
            high = rand.getrandbits(48)
            expected = high * 3 // (1 << 15)
            for low in (0, 1, 0xffff):
                observed = exact.index((high << 16) | low)
                self.assertEqual(observed, expected)
                self.assertLess(observed, exact.ENTRIES)

    def test_each_sampled_slot_has_near_uniform_complete_preimages(self):
        rand = random.Random(1911)
        indices = [0, 1, 2, 3, exact.ENTRIES - 2, exact.ENTRIES - 1]
        indices += [rand.randrange(exact.ENTRIES) for _ in range(1000)]
        counts = set()
        for slot in indices:
            # First upper-48 input for this slot is ceil(slot * 2^15 / 3).
            lower = (slot * (1 << 15) + 2) // 3
            upper = ((slot + 1) * (1 << 15) + 2) // 3
            counts.add(upper - lower)
            self.assertEqual(exact.index(lower << 16), slot)
            self.assertEqual(exact.index(((upper - 1) << 16) | 0xffff), slot)
            if slot + 1 < exact.ENTRIES:
                self.assertEqual(exact.index(upper << 16), slot + 1)
        self.assertEqual(counts, {10922, 10923})

    @unittest.skipUnless(shutil.which("cc"), "a local C compiler is required")
    def test_unsigned_c_arithmetic_matches_128bit_reference(self):
        # The multiply happens in uint64_t in the emitted engine. Check C
        # integer promotion and overflow against an independent wide reference.
        program = r'''#include <stdint.h>
int main(void) {
  uint64_t h = 0, n = 3ULL << 33;
  for (unsigned k = 0; k < 50000; ++k) {
    h = h * 6364136223846793005ULL + 1442695040888963407ULL;
    uint64_t a = ((h >> 16) * 3) >> 15;
    uint64_t b = (uint64_t)(((__uint128_t)(h >> 16) * n) >> 48);
    if (a != b || a >= n) return 1;
  }
  h = UINT64_MAX;
  return (((h >> 16) * 3) >> 15) != n - 1;
}
'''
        with tempfile.TemporaryDirectory(prefix="rove4k-index-check-") as tmp:
            source, binary = Path(tmp) / "index.c", Path(tmp) / "index-test"
            source.write_text(program, encoding="ascii")
            built = subprocess.run([shutil.which("cc"), "-std=c11", "-O2", str(source), "-o", str(binary)],
                                   capture_output=True, check=False, timeout=20)
            self.assertEqual(built.returncode, 0, built.stderr.decode(errors="replace"))
            tested = subprocess.run([str(binary)], capture_output=True, check=False, timeout=5)
            self.assertEqual(tested.returncode, 0)


class TransformProperties(unittest.TestCase):
    def test_both_peers_roundtrip_complete_and_all_sites_use_mapping(self):
        for name in ("ice4", "c4ke"):
            original = sources(name)
            with self.subTest(peer=name), pin_synthetic(name, original):
                changed, proof = exact.transform(name, original)
                self.assertEqual(exact.restore(name, changed, proof), original)
                self.assertEqual(proof["tt_bytes"], 192 << 30)
                self.assertEqual(proof["tt_entries"], 3 << 33)
                self.assertEqual(proof["workers"], 192)
                self.assertTrue(proof["algorithm_changed"])
                self.assertEqual(set(proof["files"]), set(original))
                if name == "ice4":
                    self.assertIn(b"calloc(3ull << 33, 8)", changed["src/board.cpp"])
                    self.assertIn(b"TT[((zobrist >> 16) * 3) >> 15]", changed["src/board.cpp"])
                    self.assertIn(b"TT[((board.zobrist >> 16) * 3) >> 15]", changed["src/search.cpp"])
                else:
                    self.assertIn(b"calloc(3ull << 33, 8)", changed["src/chess.cpp"])
                    self.assertIn(b"TTABLE[((hash >> 16) * 3) >> 15]", changed["src/board.cpp"])
                    self.assertEqual(changed["src/search.cpp"].count(
                        b"TTABLE[((board.hash >> 16) * 3) >> 15]"), 2)
                self.assertEqual(exact.peers.resource_layout("test-p192")["tt_bytes"], 128 << 30)

    def test_missing_extra_and_unpinned_source_rejected(self):
        for name in ("ice4", "c4ke"):
            original = sources(name)
            with self.subTest(peer=name), pin_synthetic(name, original):
                missing = dict(original)
                del missing["src/board.cpp"]
                with self.assertRaises(ValueError):
                    exact.transform(name, missing)
                with self.assertRaises(ValueError):
                    exact.transform(name, {**original, "unexpected.cpp": b"x"})
                changed = dict(original)
                changed["src/board.cpp"] += b"tamper"
                with self.assertRaises(ValueError):
                    exact.transform(name, changed)

    def test_duplicate_or_missing_hot_site_rejected_even_with_matching_pin(self):
        for name in ("ice4", "c4ke"):
            original = sources(name)
            search = original["src/search.cpp"]
            marker = (b"TT[board.zobrist >> (64 - TT_BITS)]" if name == "ice4"
                      else b"TTABLE[board.hash >> TT_SHIFT]")
            for changed_search in (search.replace(marker, b"removed", 1), search + marker):
                bad = {**original, "src/search.cpp": changed_search}
                with self.subTest(peer=name), pin_synthetic(name, bad), self.assertRaises(ValueError):
                    exact.transform(name, bad)

    def test_tampered_changed_source_or_inverse_receipt_rejected(self):
        for name in ("ice4", "c4ke"):
            original = sources(name)
            with self.subTest(peer=name), pin_synthetic(name, original):
                changed, proof = exact.transform(name, original)
                forged = dict(changed)
                forged["src/search.cpp"] += b"unexpected"
                with self.assertRaises(ValueError):
                    exact.restore(name, forged, proof)
                for field, value in (("tt_bytes", 128 << 30), ("workers", 16),
                                     ("algorithm_changed", False), ("revision", "wrong")):
                    bad_proof = copy.deepcopy(proof)
                    bad_proof[field] = value
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        exact.restore(name, changed, bad_proof)
                bad_proof = copy.deepcopy(proof)
                bad_proof["files"]["src/search.cpp"]["edits"][0]["before"] = "forged"
                with self.assertRaises(ValueError):
                    exact.restore(name, changed, bad_proof)


if __name__ == "__main__":
    unittest.main()
