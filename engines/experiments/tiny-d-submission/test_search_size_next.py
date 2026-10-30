"""Bounded pure checks for D search representations, never a native test.

Hosted tests must still execute the generated actual search and compare its
node/order/TT/learner/cancellation observations in plain and UBSan modes.
"""
import importlib.util
import itertools
import lzma
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location("D_search_size_test_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


search = load("search_size_next")


class RepresentationProofs(unittest.TestCase):
    def test_ranked_cells_preserve_unread_moves_in_reverse_expansion(self):
        # Model actual overlapping bytes, including every admitted list length.
        # Reverse expansion must retain the complete still-unread plain prefix.
        # The arithmetic packing itself is independent of object byte order.
        scores = (-(1 << 31), -1000000, -1, 0, 1, 1405000, (1 << 31) - 1)
        for count in range(414):
            moves = [(index * 2654435761 ^ 0xDEADBEEF) & 0xffffffff for index in range(count)]
            expected = [(move, scores[index % len(scores)]) for index, move in enumerate(moves)]
            for endian in ("<", ">"):
                storage = bytearray(8 * count + 16)
                storage[8 * count:] = b"unchanged-guard!"
                for index, move in enumerate(moves):
                    struct.pack_into(endian + "I", storage, 4 * index, move)
                for index in reversed(range(count)):
                    move = struct.unpack_from(endian + "I", storage, 4 * index)[0]
                    self.assertEqual(move, moves[index])
                    unread = bytes(storage[:4 * index])
                    cell = ((expected[index][1] & 0xffffffff) << 32) | move
                    struct.pack_into(endian + "Q", storage, 8 * index, cell)
                    self.assertEqual(storage[:4 * index], unread)
                restored = []
                for index in range(count):
                    cell = struct.unpack_from(endian + "Q", storage, 8 * index)[0]
                    score = (cell >> 32) - ((1 << 32) if cell >> 63 else 0)
                    restored.append((cell & 0xffffffff, score))
                self.assertEqual(restored, expected)
                self.assertEqual(storage[8 * count:], b"unchanged-guard!")

    def test_ranked_selection_preserves_signed_scores_and_original_tie_order(self):
        def original(moves, scores):
            moves, scores, result = list(moves), list(scores), []
            for index in range(len(moves)):
                best = index
                for other in range(index + 1, len(moves)):
                    if scores[other] > scores[best]:
                        best = other
                result.append((moves[best], scores[best]))
                moves[best], scores[best] = moves[index], scores[index]
            return result

        def packed(moves, scores):
            cells = [((score & 0xffffffff) << 32) | move for move, score in zip(moves, scores)]
            result = []
            def signed(cell):
                value = cell >> 32
                return value - (1 << 32) if value & (1 << 31) else value
            for index in range(len(cells)):
                best = index
                for other in range(index + 1, len(cells)):
                    if signed(cells[other]) > signed(cells[best]):
                        best = other
                result.append((cells[best] & 0xffffffff, signed(cells[best])))
                cells[best] = cells[index]
            return result

        for count in range(6):
            # Descending move values expose an accidental composite tie-break.
            moves = [0xffffffff - index * 43 for index in range(count)]
            for scores in itertools.product((-2, -1, 0, 1, 2), repeat=count):
                self.assertEqual(packed(moves, scores), original(moves, scores))
        extremes = (-(1 << 31), (1 << 31) - 1, -1, 0, 1, -1000000, 1405000)
        for count in (7, 31, 128, 413):
            moves = [((index * 65537) ^ 0x80000001) & 0xffffffff for index in range(count)]
            scores = [extremes[(index * 3) % len(extremes)] for index in range(count)]
            self.assertEqual(packed(moves, scores), original(moves, scores))

    def test_ordered_retry_states_preserve_every_window_and_reduction(self):
        # Compare the original two independent flags to the proposed ordered
        # states, including null-window fail-high and cancellation's zero score.
        for alpha in (-3, 0, 3):
            for beta in (alpha + 1, alpha + 4):
                values = sorted(set((alpha - 1, alpha, beta - 1, beta, beta + 1, 0)))
                for initial in ((0, 0), (1, 0), (1, 1)):
                    for results in itertools.product(values, repeat=3):
                        narrow, reduce = initial
                        old = []
                        for score in results:
                            old.append((reduce, alpha + 1 if narrow else beta))
                            if not narrow or score <= alpha or (not reduce and score >= beta):
                                break
                            if reduce: reduce = 0
                            else: narrow = 0
                        stage = initial[0] + initial[1]
                        new = []
                        for score in results:
                            new.append((int(stage == 2), alpha + 1 if stage else beta))
                            if stage == 0 or score <= alpha or (stage == 1 and score >= beta):
                                break
                            stage -= 1
                        self.assertEqual(new, old)

    def test_prefix_keeps_every_relevant_history_index_and_parity(self):
        # Distinct integer labels represent distinct history positions, making
        # any missing/duplicated/out-of-order read visible without a chess model.
        for root_length in (1, 2, 3, 98, 99, 100, 101, 102, 4095, 4096):
            prefix = min(100, root_length)
            removed = root_length - prefix
            for ply in (0, 1, 2, 3, 63, 126, 127):
                for half in range(100):
                    length = root_length + ply
                    old = list(range(length - 3, max(0, length - 1 - half) - 1, -2))
                    local = prefix + ply
                    new = [index + removed for index in
                           range(local - 3, max(0, local - 1 - half) - 1, -2)]
                    self.assertEqual(new, old)
                    self.assertTrue(all(0 <= index - removed < 100 + 128 for index in new))

    def test_byte_aligned_tt_fields_are_bijective_without_hidden_bits(self):
        # Exercise every encoded signed16 bit pattern and every move bit pattern
        # independently, plus all depth/bound pairs. Other fields are maximal.
        def check(move, score_bits, depth, bound):
            old = move | (score_bits << 17) | (depth << 33) | (bound << 41)
            new = move | (score_bits << 32) | (depth << 48) | (bound << 56)
            restored = ((new & 0xffffffff) | (((new >> 32) & 65535) << 17) |
                        (((new >> 48) & 255) << 33) | ((new >> 56) << 41))
            self.assertEqual(restored, old)
            self.assertEqual((new & 0xffffffff) & ~131071, 0)
        for value in range(65536):
            check(131071, value, 255, 3)
        for value in range(131072):
            check(value, 65535, 255, 3)
        for depth in range(256):
            for bound in range(4):
                check(131071, 65535, depth, bound)

    def test_board_owned_hashes_preserve_root_suffix_indices_and_zero_values(self):
        # boards[0] is root, while the separate keys[0] used to be its child.
        # Repeated values include hash zero, so truthiness cannot replace equality.
        for root_length in (1, 2, 3, 99, 100, 101, 4096):
            game = [index % 4 for index in range(root_length)]
            for ply in (0, 1, 2, 3, 4, 63, 126, 127):
                suffix = [(root_length + index) % 4 for index in range(ply)]
                boards = [game[-1], *suffix]
                for half in (0, 1, 2, 3, 98, 99, 100, 101, 4095):
                    length = root_length + ply
                    indices = range(length - 3, max(0, length - 1 - half) - 1, -2)
                    old = [game[index] if index < root_length else suffix[index - root_length]
                           for index in indices]
                    owned = [game[index] if index < root_length else boards[index - root_length + 1]
                             for index in indices]
                    self.assertEqual(owned, old)
                    if half == 0:
                        self.assertEqual(owned, [])
                    for current_hash in (boards[ply], 0):
                        old_repetitions = sum(value == current_hash for value in old)
                        new_repetitions = sum(value == current_hash for value in owned)
                        self.assertEqual(new_repetitions, old_repetitions)
                        self.assertEqual(half >= 100 or new_repetitions >= 2,
                                         half >= 100 or old_repetitions >= 2)


class ActualSourceRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cost = load("structural_bss_cost")
        inputs = cls.cost.capture_inputs()
        core = cls.cost._core(cls.cost.ROOT)
        baseline = cls.cost.validate_inputs(inputs, core)
        modules = core.load_modules(cls.cost.ROOT, baseline)
        cls.modules = modules
        files, _ = core.prepare_sources(modules, baseline)
        helper = cls.cost._bss(cls.cost.ROOT, inputs[cls.cost.BSS])
        cls.files, _ = cls.cost._apply_bss(helper, files, modules["source"], 23)
        cls.source = modules["source"]
        cls.storage = load("check_storage")
        cls.probe = load("probe_search_compact")
        cls.reference = load("structural_size").load_baseline()["board.c"]

    def test_ranked_type_assertion_preserves_reserved_legacy_spellings(self):
        # Captured hosted GCC13 CPP, round3 tool-170-preprocess-single-TU.stdout
        # SHA256 bc745c443f00a2353c785d448ef209c7a51e50e7fe5e1fd33a37d95dd1973d54.
        # Keep the real failing expansion; do not change/whitelist its lexer.
        captured = b'''_Static_assert(8==8&&sizeof(Move)==4&&(0x7fffffff * 2U + 1U)==(4294967295U)&&
                   sizeof(int)==4&&(-0x7fffffff - 1)==(-2147483647-1)&&0x7fffffff==(2147483647),"ranked32 fields");'''
        lexical = self.modules["lexical"]
        minifier = self.modules["minifier"]
        reserved = set(self.modules["legacy"].LEGACY.values())
        def collisions(data):
            return reserved.intersection(lexical._ANY_WORD.findall(minifier.compact_source(data, "c").decode()))
        self.assertEqual(collisions(captured), {"U"})
        self.assertEqual(lexical._ANY_WORD.findall(captured.decode()).count("U"), 3)
        source = search.apply(self.files, ("ranked64",))["search.c"]
        start = source.index(b"_Static_assert(CHAR_BIT")
        assertion = source[start:source.index(b";", start) + 1]
        # Reuse only these observed scalar expansions, not a mock C compiler.
        # The subsequent hosted run must still preprocess the full real TU.
        observed = {"CHAR_BIT": "8", "UINT_MAX": "(0x7fffffff * 2U + 1U)",
                    "UINT32_MAX": "(4294967295U)", "INT_MIN": "(-0x7fffffff - 1)",
                    "INT32_MIN": "(-2147483647-1)", "INT_MAX": "0x7fffffff", "INT32_MAX": "(2147483647)"}
        expanded = lexical._ANY_WORD.sub(lambda match: observed.get(match.group(), match.group()), assertion.decode())
        self.assertFalse(collisions(expanded.encode()))
        # Equality alone accepts signed -1 after conversion to uint32_t.
        self.assertIn(b"(Move)-1>0&&(Move)-1==(uint32_t)-1", assertion)

    def test_all_selector_compositions_and_actual_observers_render_purely(self):
        original = dict(self.files)
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("compiler/process forbidden")), \
             mock.patch.object(lzma, "compress", side_effect=AssertionError("codec forbidden")), \
             mock.patch.object(lzma, "decompress", side_effect=AssertionError("codec forbidden")):
            for length in range(len(search.OPTIONS) + 1):
                for names in itertools.combinations(search.OPTIONS, length):
                    if "board_keys" in names and ("board_path" not in names or "repetition_prefix" in names):
                        with self.assertRaisesRegex(ValueError, "requires board_path"):
                            search.apply(self.files, names)
                        continue
                    for ordered in (names, names[::-1]):
                        files = search.apply(self.files, ordered)
                        generated, driver, proof = search.render_probe(
                            files, self.source, self.storage, self.probe,
                            reference_board=self.reference, names=ordered)
                        self.assertEqual(proof["source"], self.probe.inventory(files))
                        self.assertEqual(proof["output"], self.probe.inventory(generated))
                        self.assertEqual(proof["driver"], self.probe.pin(driver))
                        self.assertFalse(proof["actual_runtime"])
        self.assertEqual(self.files, original)

    def test_selector_and_source_drift_fail_before_partial_application(self):
        for names in ("tt_bytes", ("unknown",), ("tt_bytes", "tt_bytes")):
            with self.assertRaises(ValueError):
                search.apply(self.files, names)
        for name in search.OPTIONS:
            names = ("board_path", name) if name == "board_keys" else (name,)
            changed = search.apply(self.files, names)
            with self.assertRaises(ValueError):
                search.apply(changed, names)
        files = search.apply(self.files, ("tt_bytes",))
        with self.assertRaisesRegex(ValueError, "selector contract"):
            search.render_probe(files, self.source, self.storage, self.probe,
                                reference_board=self.reference, names=())


if __name__ == "__main__":
    unittest.main()
