"""Model representation and independent scalar inference checks; no training."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest

from codec import (HERE, coefficient_bounds, decode_signed, encode_signed,
                   generated_sources, load_model)
from reference import (Position, accumulator_bound, center, evaluate, feature_vector,
                       ordering_score)

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"


class CodecTests(unittest.TestCase):
    def test_all_signed_16_bit_values_round_trip(self):
        values = list(range(-32768, 32768))
        self.assertEqual(decode_signed(encode_signed(values), len(values)), values)
        self.assertEqual(encode_signed([0, -1, 1, -64, 63, -65, 64]),
                         bytes([0, 1, 2, 127, 126, 129, 1, 128, 1]))

    def test_invalid_encodings_and_coefficients_fail(self):
        for bad in (b"\x80", b"\x80\0", b"\xff\xff\x04", b"\x80\x80\x80\0"):
            with self.subTest(encoded=bad), self.assertRaises(ValueError):
                decode_signed(bad)
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            decode_signed(b"\0", 2)
        for bad in (-32769, 32768, 1.0, True):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                encode_signed([bad])

    def test_checked_in_sources_are_exact_generation(self):
        model = load_model()
        self.assertEqual(len(encode_signed(model["evaluation"]["weights"] +
                                           model["ordering"]["weights"])), 26)
        for name, source in generated_sources(model).items():
            self.assertEqual((HERE / name).read_text(encoding="utf-8"), source)

    def test_integer_model_loader_rejects_feature_drift_and_accumulator_overflow(self):
        model = load_model()
        with tempfile.TemporaryDirectory(prefix="rove4k-model-test-") as directory:
            path = Path(directory) / "model.json"
            wrong = copy.deepcopy(model)
            wrong["evaluation"]["features"][0] = "other_feature"
            path.write_text(json.dumps(wrong), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "feature order"):
                load_model(path)
            wrong = copy.deepcopy(model)
            wrong["evaluation"]["weights"][:5] = [-32768, 32767, 32767, 32767, 32767]
            wrong["ordering"]["weights"] = [-32768] * 5
            path.write_text(json.dumps(wrong), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overflow"):
                load_model(path)
            with self.assertRaisesRegex(ValueError, "overflow"):
                generated_sources(wrong)
            wrong = copy.deepcopy(model)
            wrong["evaluation"]["weights"][0] = 100.0
            path.write_text(json.dumps(wrong), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "floating point"):
                load_model(path)


class InferenceTests(unittest.TestCase):
    def test_hand_computed_evaluations_and_structured_features(self):
        cases = [(START + " w", 10), (START + " b", -10),
                 ("4k3/8/8/8/4P3/8/8/4K3 w", 132),
                 ("4k3/8/8/4P3/4P3/8/8/4K3 w", 248),
                 ("4k3/8/8/8/3PP3/8/8/4K3 w", 270),
                 ("4k3/8/8/8/8/8/8/B3K2B w", 694)]
        for fen, expected in cases:
            with self.subTest(fen=fen):
                self.assertEqual(evaluate(Position.fen(fen)), expected)
        self.assertEqual(feature_vector(Position.fen(cases[3][0]))[12:15], [1, 2, 0])
        self.assertEqual(feature_vector(Position.fen(cases[5][0]))[14], 1)

    def test_ordering_is_separate_and_has_exact_capture_promotion_ep_semantics(self):
        self.assertEqual(ordering_score(Position.fen(START + " w"), 12, 28), 12)
        self.assertEqual(ordering_score(Position.fen("4k3/8/8/3q4/4P3/8/8/4K3 w"),
                                        28, 35), 14304)
        self.assertEqual(ordering_score(Position.fen("4k3/P7/8/8/8/8/8/4K3 w"),
                                        48, 56, "Q"), 9602)
        self.assertEqual(ordering_score(Position.fen("1r2k3/P7/8/8/8/8/8/4K3 w"),
                                        48, 57, "Q"), 17504)
        self.assertEqual(ordering_score(Position.fen("4k3/8/8/3pP3/8/8/8/4K3 w"),
                                        36, 43, en_passant=True), 1502)

    def test_center_and_color_rotation_symmetry(self):
        self.assertEqual([center(s) for s in (0, 7, 56, 63, 27, 28)], [0, 0, 0, 0, 6, 6])
        position = Position.fen("r3k2r/pp1q1ppp/2n1b3/3pP3/2B2N2/8/PPP2PPP/R2Q1RK1 w")
        rotated = Position(tuple(p.swapcase() for p in reversed(position.board)), -position.side)
        self.assertEqual(feature_vector(rotated), [-f for f in feature_vector(position)])
        self.assertEqual(evaluate(rotated), -evaluate(position))

    def test_dense_promoted_material_uses_32_bit_range_and_separate_mate_clamp(self):
        dense = Position.fen("QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQkQQQQ/QQQQQQQQ/QQQQQQQQ/KQQQQQQQ w")
        self.assertEqual(evaluate(dense), 56014)
        self.assertEqual(coefficient_bounds(load_model()), (56224, 24940))
        self.assertEqual(accumulator_bound()["raw_evaluation_abs_max"], 56224)
        self.assertTrue(accumulator_bound()["safe"])
        self.assertGreater(evaluate(dense), 32767)

    def test_scalar_polynomial_matches_independent_feature_dot_product(self):
        rng = random.Random(20261020)
        frozen = load_model()["evaluation"]["weights"]
        weights = [frozen, [rng.randint(-32768, 32767) for _ in range(16)]]
        for _ in range(1000):
            squares = list(range(64))
            rng.shuffle(squares)
            board = ["."] * 64
            board[squares.pop()] = "K"
            board[squares.pop()] = "k"
            for square in squares[:rng.randrange(63)]:
                board[square] = rng.choice("PNBRQpnbrq")
            position = Position(tuple(board), rng.choice((-1, 1)))
            features = feature_vector(position)
            for w in weights:
                self.assertEqual(evaluate(position, w), sum(a * b for a, b in zip(features, w)))
            self.assertLessEqual(abs(evaluate(position, frozen)), 56224)


if __name__ == "__main__":
    unittest.main()
