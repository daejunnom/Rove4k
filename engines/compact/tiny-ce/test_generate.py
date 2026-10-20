import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generate = load("tiny_ce_test_generate", HERE / "generate.py")
stitch = load("tiny_ce_test_stitch", HERE.parent / "tiny-a/stitch.py")


class OverlayContract(unittest.TestCase):
    def source(self):
        names = ("tiny.h", "board.c", "search.c", "main.c")
        sources = {name: (HERE / "core" / name).read_bytes() for name in names}
        return stitch.stitch(sources, names, True)[0]

    def test_model_identity_and_int32_bounds(self):
        record = generate.model_record((HERE / "frozen.json").read_bytes())
        self.assertEqual(record["weights"], list(generate.WEIGHTS))
        self.assertEqual(record["coefficient_count"], 21)
        self.assertEqual(record["coefficient_bytes"], 42)
        self.assertEqual(record["raw_evaluation_abs_max"], 56224)
        self.assertEqual(record["ordering_abs_max"], 24940)
        self.assertLess(max(record["raw_evaluation_abs_max"], record["ordering_abs_max"]), 2**31)
        self.assertFalse(record["training"])
        self.assertFalse(record["quantization"])

    def test_model_feature_or_coefficient_drift_rejected(self):
        base = json.loads((HERE / "frozen.json").read_bytes())
        for field in ("weight", "feature", "provenance"):
            wrong = copy.deepcopy(base)
            if field == "weight":
                wrong["ordering"]["weights"][0] += 1
            elif field == "feature":
                wrong["evaluation"]["features"][0] = "changed"
            else:
                wrong["provenance"] = "trained"
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "identity changed"):
                generate.model_record(json.dumps(wrong))

    def test_actual_leaf_and_ordering_replace_fixed_sites(self):
        source, record = generate.overlay(self.source(), "E", (HERE / "e-eval.c.in").read_bytes(), (HERE / "frozen.json").read_bytes())
        text = source.decode()
        self.assertIn("int evaluation=p->s*tiny_raw(p);", text)
        self.assertIn("int error=best-evaluation;", text)
        self.assertIn("scores[i]+=tiny_order(p,m);", text)
        self.assertNotIn("@WEIGHTS@", text)
        self.assertEqual(record["model"]["weights"], list(generate.WEIGHTS))
        for contract in ("atomic_flag_test_and_set_explicit", "memory_order_acquire", "probe(key,1,data)",
                         "w->history[from][to]", "w->continuation[prior]", "w->correction[p->h&1023]",
                         "pthread_create", "w->best=best;w->score=score;w->depth=depth;"):
            self.assertIn(contract, text)

    def test_c_has_real_simd_leaf_and_no_model(self):
        source, record = generate.overlay(self.source(), "C", (HERE / "c-eval.c.in").read_bytes(), (HERE / "frozen.json").read_bytes())
        self.assertIn(b"_mm256_", source)
        self.assertIn(b"int evaluation=p->s*tiny_raw(p);", source)
        self.assertIsNone(record["model"])
        self.assertNotIn(b"tiny_weights", source)

    def test_unexpected_source_or_variant_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlay shape"):
            generate.overlay(self.source().replace(b"int error=best-p->s*p->v;", b"int error=0;"), "E",
                             (HERE / "e-eval.c.in").read_bytes(), (HERE / "frozen.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "separate C or E"):
            generate.overlay(self.source(), "CE", b"", b"")


if __name__ == "__main__":
    unittest.main()
