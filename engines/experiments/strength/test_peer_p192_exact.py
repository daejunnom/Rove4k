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


def share_sources():
    """Synthetic shape exercising the reviewed TCEC sharing assumptions."""
    value = sources("c4ke")
    value["src/chess.cpp"] = b"TTEntry* TTABLE = (TTEntry*)calloc(1ull << TT_BITS, 8);\n"
    value["src/board.cpp"] = b"__builtin_prefetch(&TTABLE[hash >> TT_SHIFT]);\n"
    value["src/search.cpp"] = (
        b"TTEntry tt = TTABLE[board.hash >> TT_SHIFT];\n"
        b"Board child = board;\nBoard child = board;\n"
        b"score = search(board,1);\nscore = search(board,2);\n" +
        b"// board.hash\n" * 11 +
        b"TTABLE[board.hash >> TT_SHIFT] = {0};\n")
    value["src/main.cpp"] = (b"#ifdef OB\n        // Uci ucinewgame\n"
        b"free(TTABLE);\nTTABLE = (TTEntry*)calloc(1ull << TT_BITS, sizeof(TTEntry));\n"
        b"#endif\n        // Uci position\njthread threads[THREADS];\nfree(TTABLE);\n")
    value["src/eval.cpp"] = b"synthetic eval dependency\n"
    return value


def slot_ray_sources():
    """Short synthetic inputs with the pinned transform marker shape."""
    value = share_sources()
    value["src/chess.cpp"] += exact._RAY_BEFORE
    return value


def ice_structural_sources():
    value = sources("ice4")
    structural = exact.peer_ice_structural.edit_specs("castle-zobrist-v1")
    for path, edits in structural.items():
        value[path] = value.get(path, b"synthetic context\n") + b"\n".join(edit[1] for edit in edits)
    return value


def c4ke_structural_sources():
    value = slot_ray_sources()
    value["src/board.cpp"] += exact.peer_c4ke_structural._CASTLE_BEFORE
    return value


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
    def test_c4ke_castle_variants_compose_with_exact_tt(self):
        all_sources = c4ke_structural_sources()
        variants = ("castle-or-v1", "ray-castle-or-v1")
        for variant in variants:
            original = {path: all_sources[path] for path in exact.source_closure("c4ke", variant=variant)}
            with self.subTest(variant=variant), pin_synthetic("c4ke", original):
                changed, receipt = exact.transform("c4ke", original, variant=variant)
                self.assertEqual(exact.restore("c4ke", changed, receipt, variant=variant), original)
                self.assertIn(b"calloc(3ull << 33, 8)", changed["src/chess.cpp"])
                self.assertIn(exact.peer_c4ke_structural._CASTLE_AFTER, changed["src/board.cpp"])
                with self.assertRaises(ValueError):
                    exact.restore("c4ke", changed, receipt, variant="baseline")
                with self.assertRaises(ValueError):
                    exact.source_closure("ice4", variant=variant)

    def test_ice_structural_variants_compose_with_exact_tt_and_reject_cross_variant(self):
        all_sources = ice_structural_sources()
        variants = exact.peer_ice_structural.VARIANTS
        for variant in variants:
            original = {path: all_sources[path] for path in exact.source_closure("ice4", variant=variant)}
            with self.subTest(variant=variant), pin_synthetic("ice4", original):
                changed, receipt = exact.transform("ice4", original, variant=variant)
                self.assertEqual(receipt["variant"], variant)
                self.assertEqual(exact.restore("ice4", changed, receipt, variant=variant), original)
                self.assertIn(b"calloc(3ull << 33, 8)", changed["src/board.cpp"])
                self.assertIn(b"TT[((zobrist >> 16) * 3) >> 15]", changed["src/board.cpp"])
                self.assertIn(b"TT[((board.zobrist >> 16) * 3) >> 15]", changed["src/search.cpp"])
                for other in ("baseline", *variants):
                    if other != variant:
                        with self.assertRaises(ValueError):
                            exact.restore("ice4", changed, receipt, variant=other)
                with self.assertRaises(ValueError):
                    exact.source_closure("c4ke", variant=variant)

    def test_baseline_receipt_and_closure_are_unchanged(self):
        for name in ("ice4", "c4ke"):
            original = sources(name)
            with self.subTest(peer=name), pin_synthetic(name, original):
                default = exact.transform(name, original)
                self.assertEqual(default, exact.transform(name, original, variant="baseline"))
                self.assertNotIn("variant", default[1])
                self.assertEqual(exact.source_closure(name), set(original))

    def test_share_variant_pins_context_and_roundtrips(self):
        original = share_sources()
        with pin_synthetic("c4ke", original):
            self.assertEqual(exact.source_closure("c4ke", variant=exact.SHARE_VARIANT), set(original))
            changed, receipt = exact.transform("c4ke", original, variant=exact.SHARE_VARIANT)
            self.assertEqual(exact.restore("c4ke", changed, receipt, variant=exact.SHARE_VARIANT), original)
            self.assertEqual(receipt["variant"], "share-v1")
            self.assertIn(b"TTEntry &rove_entry=TTABLE[3*(board.hash>>16)>>15],tt=rove_entry;",
                          changed["src/search.cpp"])
            self.assertIn(b"rove_entry = {", changed["src/search.cpp"])
            self.assertIn(b"TTABLE[3*(hash >> 16)>>15]", changed["src/board.cpp"])
            self.assertEqual(changed["src/main.cpp"], original["src/main.cpp"])
            self.assertEqual(changed["src/eval.cpp"], original["src/eval.cpp"])
            with self.assertRaises(ValueError):
                exact.restore("c4ke", changed, receipt)
            altered = copy.deepcopy(receipt)
            altered["variant"] = "baseline"
            with self.assertRaises(ValueError):
                exact.restore("c4ke", changed, altered, variant=exact.SHARE_VARIANT)
        with self.assertRaises(ValueError):
            exact.source_closure("ice4", variant=exact.SHARE_VARIANT)

    def test_share_variant_rejects_mutated_guard_context(self):
        original = share_sources()
        cases = [
            {**original, "src/search.cpp": original["src/search.cpp"].replace(
                b"// board.hash\n", b"board.hash += 1;\n", 1)},
            {**original, "src/search.cpp": original["src/search.cpp"].replace(
                b"// board.hash\n", b"++board.hash;\n", 1)},
            {**original, "src/main.cpp": original["src/main.cpp"].replace(
                b"#ifdef OB\n", b"#ifdef OTHER\n", 1)},
            {**original, "src/eval.cpp": b"rove_entry collision"},
        ]
        for changed in cases:
            with self.subTest(case=changed), pin_synthetic("c4ke", changed), self.assertRaises(ValueError):
                exact.transform("c4ke", changed, variant=exact.SHARE_VARIANT)

    def test_slot_and_ray_variants_are_distinct_and_fully_invertible(self):
        original = slot_ray_sources()
        variants = (exact.SLOT_VARIANT, exact.RAY_VARIANT, exact.SLOT_RAY_VARIANT)
        with pin_synthetic("c4ke", original):
            for variant in variants:
                with self.subTest(variant=variant):
                    changed, receipt = exact.transform("c4ke", original, variant=variant)
                    self.assertEqual(exact.restore("c4ke", changed, receipt, variant=variant), original)
                    self.assertEqual(receipt["variant"], variant)
                    if variant in (exact.SLOT_VARIANT, exact.SLOT_RAY_VARIANT):
                        self.assertEqual(changed["src/board.cpp"].count(b"rove_slot(hash)"), 1)
                        self.assertEqual(changed["src/search.cpp"].count(b"rove_slot(board.hash)"), 2)
                        self.assertIn(b"return TTABLE[3*(h>>16)>>15];", changed["src/chess.cpp"])
                    if variant in (exact.RAY_VARIANT, exact.SLOT_RAY_VARIANT):
                        self.assertNotIn(exact._RAY_BEFORE, changed["src/chess.cpp"])
                        self.assertIn(b"for(i32 rove_ray=6;rove_ray--;)", changed["src/chess.cpp"])
                    for other in variants:
                        if other != variant:
                            with self.assertRaises(ValueError):
                                exact.restore("c4ke", changed, receipt, variant=other)
            for variant in variants:
                with self.assertRaises(ValueError):
                    exact.source_closure("ice4", variant=variant)

    def test_slot_and_ray_variants_reject_unexpected_markers_and_collisions(self):
        original = slot_ray_sources()
        for field, replacement, variant in (
                ("src/chess.cpp", b"rove_slot collision", exact.SLOT_VARIANT),
                ("src/eval.cpp", b"rove_ray collision", exact.RAY_VARIANT),
                ("src/chess.cpp", original["src/chess.cpp"].replace(exact._RAY_BEFORE, b"changed"), exact.RAY_VARIANT)):
            altered = dict(original)
            altered[field] = replacement
            with self.subTest(field=field, variant=variant), pin_synthetic("c4ke", altered):
                with self.assertRaises(ValueError):
                    exact.transform("c4ke", altered, variant=variant)

    @unittest.skipUnless(shutil.which("c++"), "a local C++ compiler is required")
    def test_slot_and_ray_toy_differential(self):
        # This independently exercises lvalue/prefetch and six ordered ray
        # updates. The bounded array is a toy and never allocates the large TT.
        program = r'''#include <cstdint>
#include <climits>
using u64=uint64_t;
struct Entry { u64 key, value; };
Entry first[64],second[64],*table=first;
u64 index(u64 h){return 3*(h>>16)>>15;}
Entry& slot(u64 h){return table[index(h)%64];}
u64 east(u64 x){return x<<1&~0x0101010101010101ULL;}
u64 west(u64 x){return x>>1&~0x8080808080808080ULL;}
using Move=u64(*)(u64);
u64 original_ray(u64 mask,u64 occupied,Move move){
 mask=move(mask);
 mask|=move(mask&~occupied);mask|=move(mask&~occupied);
 mask|=move(mask&~occupied);mask|=move(mask&~occupied);
 mask|=move(mask&~occupied);mask|=move(mask&~occupied);
 return mask;
}
u64 loop_ray(u64 mask,u64 occupied,Move move){
 mask=move(mask);for(int n=6;n--;)mask|=move(mask&~occupied);return mask;
}
int main(){
 u64 h=0,occ=0;Move moves[]={east,west};
 for(unsigned bit=0;bit<64;++bit){
  u64 mask=1ULL<<bit, occupied[]={0,~0ULL,mask,~mask};
  for(Move move:moves)for(u64 blockers:occupied)
   if(original_ray(mask,blockers,move)!=loop_ray(mask,blockers,move))return 6;
 }
 for(unsigned k=0;k<50000;++k){
  h=h*6364136223846793005ULL+1442695040888963407ULL;
  occ=occ*2862933555777941757ULL+3037000493ULL;
  u64 i=((h>>16)*3)>>15;
  if(index(h)!=i||i>=3ULL<<33||index(h&~65535ULL)!=i)return 1;
  table=(k&1)?first:second;
  if(&slot(h)!=&table[i%64])return 2;
  __builtin_prefetch(&slot(h));
  Entry before=table[i%64],copy=slot(h);
  if(before.key!=copy.key||before.value!=copy.value)return 3;
  slot(h)={h,k};
  if(table[i%64].key!=h||table[i%64].value!=k)return 4;
  for(Move move:moves){u64 mask=1ULL<<(k%64);
   if(original_ray(mask,occ,move)!=loop_ray(mask,occ,move))return 5;
  }
 }
 return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="rove4k-slot-ray-") as tmp:
            source, binary = Path(tmp) / "slot.cpp", Path(tmp) / "slot-check"
            source.write_text(program, encoding="ascii")
            built = subprocess.run([shutil.which("c++"), "-std=c++17", "-O2", str(source), "-o", str(binary)],
                                   capture_output=True, check=False, timeout=20)
            self.assertEqual(built.returncode, 0, built.stderr.decode(errors="replace"))
            tested = subprocess.run([str(binary)], capture_output=True, check=False, timeout=10)
            self.assertEqual(tested.returncode, 0)

    @unittest.skipUnless(shutil.which("c++"), "a local C++ compiler is required")
    def test_shared_entry_preserves_value_copy_and_store_location(self):
        program = r'''#include <stdint.h>
struct Entry { uint64_t key, move; };
static Entry original[64], shared[64];
int main() {
  uint64_t h = 0;
  for (unsigned k = 0; k != 50000; ++k) {
    h = h * 6364136223846793005ULL + 1442695040888963407ULL;
    uint64_t a = ((h >> 16) * 3) >> 15;
    uint64_t b = 3 * (h >> 16) >> 15;
    if (a != b) return 1;
    unsigned slot = a % 64;
    Entry before = original[slot];
    Entry &entry = shared[slot], copy = entry;
    if (before.key != copy.key || before.move != copy.move) return 2;
    before.move ^= k; copy.move ^= k;
    original[slot] = {h, before.move};
    entry = {h, copy.move};
    if (original[slot].key != shared[slot].key || original[slot].move != shared[slot].move) return 3;
  }
  return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="rove4k-shared-index-") as tmp:
            source, binary = Path(tmp) / "check.cpp", Path(tmp) / "check"
            source.write_text(program, encoding="ascii")
            built = subprocess.run([shutil.which("c++"), "-std=c++20", "-O0", str(source), "-o", str(binary)],
                                   capture_output=True, check=False, timeout=20)
            self.assertEqual(built.returncode, 0, built.stderr.decode(errors="replace"))
            tested = subprocess.run([str(binary)], capture_output=True, check=False, timeout=5)
            self.assertEqual(tested.returncode, 0)

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
