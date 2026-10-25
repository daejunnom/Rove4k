"""Canonical/model objective checks; real corpus qualification is separate."""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from engines.model.e19 import Model, PositionFeatures, TRAINABLE, features, mailbox_from_fen, round_away, trunc0
from engines.training.e19.trainer import TrainingConfig, TrainingState, Sample, loss_gradient, prepare, train

FENS = (
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "4k3/3q4/8/2n5/3B4/4P3/2Q1N3/4K3 w - - 0 1",
    "r3k3/8/3p4/8/6R1/8/P5K1/8 b - - 0 1",
    "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "1r5k/P7/8/8/8/8/8/7K w - - 0 1",
    "7k/8/8/8/8/8/p7/1R5K b - - 0 1",
)


def tokens(source: bytes) -> bytes:
    return re.sub(rb"\s+", b"", re.sub(rb"/\*.*?\*/", b"", source, flags=re.S))


class CanonicalModelTests(unittest.TestCase):
    def setUp(self):
        self.model = Model.load()

    def test_readable_production_tokens_and_mapping(self):
        old = (ROOT / "engines/compact/tiny-entry-e/model19.h").read_bytes()
        self.assertEqual(tokens(self.model.render_model_fragment()), tokens(old))
        self.assertEqual(self.model.coefficient_sha256(), "a5bb11099b62489aca43a011619e15076b0637b2f2e460d89772162965cd5424")
        physical = self.model.physical_coefficients()
        self.assertEqual((physical[0], physical[6]), (0, 0))
        self.assertEqual(physical[1:6] + physical[7:21], self.model.coefficients)
        source = ("static const int16_t qi[21]={" + ",".join(map(str, physical)) + "};").encode()
        self.assertFalse(self.model.validate_physical_table(source)["consumer_semantics_checked"])
        with self.assertRaisesRegex(ValueError, "differs"):
            self.model.validate_physical_table(source.replace(b"0,100", b"1,100"))
        aliased = source.replace(b"int16_t", b"X")
        aliased = b"typedef int16_t X;" + aliased
        recovered = Model.from_physical_source(aliased, model_id="admitted-source-baseline")
        self.assertEqual(recovered.coefficients, self.model.coefficients)
        with self.assertRaisesRegex(ValueError, "zero slots"):
            Model.from_physical_source(aliased.replace(b"0,100", b"1,100"), model_id="reject-zero-slot")
        coefficients = list(self.model.coefficients)
        coefficients[5] += 1
        revised = Model("canonical-binding-candidate", tuple(coefficients))
        bound, proof = revised.bind_physical_table(aliased, source_model=self.model)
        self.assertTrue(proof["full_inverse"])
        self.assertEqual(proof["change_kind"], "model-parameters")
        self.assertEqual(revised.validate_physical_table(bound)["coefficient_sha256"], revised.coefficient_sha256())

    def test_bounds_precede_clamp_and_new_weights_recompute(self):
        bounds = self.model.bounds()
        self.assertEqual(tuple(bounds[k] for k in ("material_abs_upper", "activity_abs_upper", "quadratic_product_abs_upper", "raw_abs_upper")), (14400, 1728, 2985984, 39466))
        changed = list(self.model.coefficients)
        changed[13] = 32767
        with self.assertRaisesRegex(ValueError, "before clamp"):
            Model("overflow-must-reject", tuple(changed))
        changed[13] = 2
        candidate = Model("recomputed-model", tuple(changed))
        self.assertEqual(candidate.bounds()["quadratic_product_abs_upper"], 2 * bounds["quadratic_product_abs_upper"])
        # R itself is below INT_MAX here; the actual h priority addition is not.
        near_limit = list(self.model.coefficients)
        near_limit[4] = near_limit[14] = near_limit[15] = 32767
        near_limit[16] = near_limit[17] = near_limit[18] = 0
        with self.assertRaisesRegex(ValueError, "preordering_abs_upper"):
            Model("reject-caller-overflow", tuple(near_limit))

    def test_exact_truncation_rounding_and_color_symmetry(self):
        self.assertEqual([trunc0(v) for v in (-129, -128, -127, 127, 128, 129)], [-1, -1, 0, 0, 1, 1])
        self.assertEqual([round_away(v) for v in (-2.5, -0.5, -0.49, 0.49, 0.5, 2.5)], [-3, -1, 0, 0, 1, 3])
        for fen in FENS:
            cells, side, _ = mailbox_from_fen(fen)
            value = features(cells, side)
            opposite = PositionFeatures(tuple(-v for v in value.material), tuple(-v for v in value.centers), -value.pawn_advance, -value.side)
            self.assertEqual(self.model.integer_score(value), -self.model.integer_score(opposite))

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("cc"), "Linux C compiler required")
    def test_actual_readable_c_inference_and_ordering(self):
        expected, blocks = [], []
        moves = ((68, 83, 0), (4, 6, 0), (96, 113, 2), (96, 113, 3), (96, 113, 4), (96, 113, 5), (16, 1, 2), (16, 1, 3), (16, 1, 4), (16, 1, 5))
        for fen in FENS:
            cells, side, ep = mailbox_from_fen(fen)
            value = features(cells, side)
            values = ",".join(map(str, cells))
            blocks.append("{za p={.b={" + values + "},.s=" + str(side) + ",.e=" + str(ep) + "};for(int q=0;q<128;q++)if(!(q&0x88)&&p.b[q])piece(&p,p.b[q],q,1);printf(\"%d\\n\",S(&p));")
            expected.append(self.model.integer_score(value))
            for origin, target, promotion in moves:
                if not cells[origin]:
                    continue
                blocks.append(f"printf(\"%d\\n\",R(&p,MOVE({origin},{target},{promotion})));" )
                expected.append(self.model.ordering(cells, ep, origin, target, promotion))
            blocks.append("}")
        for activity in range(-1728, 1729):
            for side in (-1, 1):
                raw = 14400 + activity + trunc0(activity * abs(activity)) + side * 10
                expected.append(max(-20000, min(20000, raw)))
        blocks.append("for(int a=-1728;a<=1728;a++)for(int side=-1;side<=1;side+=2){za p={.v=14400,.a=a,.s=side};printf(\"%d\\n\",S(&p));}")
        preamble = b"#include<stdint.h>\n#include<stdio.h>\n#include<stdlib.h>\ntypedef unsigned Move;typedef struct{int8_t b[128];int s,e,v,a;}za;\n#define FROM(m) ((m)&119)\n#define TO(m) (((m)>>7)&127)\n#define PROMO(m) (((m)>>14)&7)\n#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))\nstatic uint64_t mix(uint64_t x){return x;}\n"
        source = preamble + self.model.render_model_fragment() + ("\nint main(void){" + "".join(blocks) + "return 0;}\n").encode()
        with tempfile.TemporaryDirectory(prefix="rove4k-e19-c-oracle-") as temporary:
            directory = Path(temporary)
            self.assertFalse(ROOT == directory or ROOT in directory.parents)
            compile_result = subprocess.run(["cc", "-std=c11", "-O2", "-fsanitize=undefined", "-fno-sanitize-recover=all", "-x", "c", "-", "-o", str(directory / "oracle")], input=source, capture_output=True, timeout=30)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr.decode())
            result = subprocess.run([str(directory / "oracle")], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(map(int, result.stdout.split())), expected)


class TrainerContractTests(unittest.TestCase):
    def setUp(self):
        self.model = Model.load()
        self.config = TrainingConfig()
        self.samples = []
        for index, fen in enumerate(FENS[:3]):
            cells, side, _ = mailbox_from_fen(fen)
            self.samples.append(Sample(features(cells, side), (0.5, 0.2, 0.8)[index], 1.0 / (index + 1), f"fixture-{index}"))

    def test_actual_analytic_gradient_matches_finite_difference(self):
        state = TrainingState(self.model)
        loss, gradient = loss_gradient(state, self.samples, self.config)
        self.assertTrue(math.isfinite(loss))
        for index in TRAINABLE:
            epsilon = 1e-5
            above, below = list(state.values), list(state.values)
            above[index] += epsilon
            below[index] -= epsilon
            numerical = (loss_gradient(TrainingState(self.model, above), self.samples, self.config)[0] - loss_gradient(TrainingState(self.model, below), self.samples, self.config)[0]) / (2 * epsilon)
            self.assertAlmostEqual(gradient[index], numerical, delta=max(1e-8, abs(numerical) * 1e-5))
        self.assertEqual([gradient[i] for i in range(19) if i not in TRAINABLE], [0] * 10)

    def test_production_prepare_does_not_enter_optimizer(self):
        state = TrainingState(self.model)
        before = state.parameter_bytes()
        result = prepare(state, self.samples, self.config)
        self.assertEqual(state.parameter_bytes(), before)
        self.assertEqual(state.optimizer_steps, 0)
        self.assertEqual(result["parameter_sha256_before"], result["parameter_sha256_after"])
        self.assertEqual(result["export_coefficient_sha256"], self.model.coefficient_sha256())
        self.assertFalse(result["trained_model"])

    def test_toy_training_loop_is_real_and_fixed_coefficients_do_not_move(self):
        production = TrainingState(self.model)
        toy = TrainingState(self.model)
        initial_sha = production.parameter_sha256()
        result = train(toy, lambda: iter(self.samples), replace(self.config, batch_size=2, shuffle_buffer=4), max_steps=3)
        self.assertEqual(toy.optimizer_steps, 3)
        self.assertEqual(len(result["updates"]), 3)
        self.assertNotEqual(toy.parameter_sha256(), initial_sha)
        self.assertEqual(production.parameter_sha256(), initial_sha)
        self.assertEqual(production.optimizer_steps, 0)
        for index in range(19):
            if index not in TRAINABLE:
                self.assertEqual(toy.values[index], self.model.coefficients[index])
        again = TrainingState(self.model)
        train(again, lambda: iter(self.samples), replace(self.config, batch_size=2, shuffle_buffer=4), max_steps=3)
        self.assertEqual(toy.parameter_bytes(), again.parameter_bytes())

    def test_export_rejects_overflow_and_revision_reuse(self):
        state = TrainingState(self.model)
        state.values[13] = 32767.0
        with self.assertRaisesRegex(ValueError, "before clamp"):
            state.export(model_id="reject-overflow")
        state.values[13] = 2.0
        with self.assertRaisesRegex(ValueError, "new model ID"):
            state.export()
        self.assertEqual(state.export(model_id="changed-model-2").coefficients[13], 2)


if __name__ == "__main__":
    unittest.main()
