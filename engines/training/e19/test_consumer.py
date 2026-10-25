"""Admission tests for the actual final E19 model consumer checker."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from engines.model.e19 import Model
from engines.training.e19.check_consumer import fixture_source, inspect_consumer, Q_REGION, S_REGION, SETTER_REGION, H_PREFIX


class ConsumerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.model = Model.load()

    def source(self):
        import ast
        raw = (ROOT / "engines/compact/tiny-entry-e/shipping_order_inline.py").read_text()
        module = ast.parse(raw)
        edits = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "EDITS" for target in node.targets))
        physical = ",".join(map(str, self.model.physical_coefficients())).encode()
        return (b"#define J return\n#define L int\ntypedef int16_t X;static const X qi[21]={" + physical + b"};" +
                Q_REGION + S_REGION + SETTER_REGION + H_PREFIX + edits[1][3] + b"}")

    def test_semantic_change_rejected_before_compilation(self):
        source = self.source()
        loop, proof = inspect_consumer(source, self.model)
        self.assertEqual(proof["physical_table"]["physical_count"], 21)
        self.assertIn(b"qi[20]", loop)
        with self.assertRaisesRegex(ValueError, "semantic region"):
            inspect_consumer(source.replace(b"qi[15]*", b"qi[14]*", 1), self.model)
        with self.assertRaisesRegex(ValueError, "h no longer"):
            inspect_consumer(source.replace(loop, loop.replace(b"400000", b"400001")), self.model)

    def test_numeric_binding_must_match_the_model(self):
        source = self.source()
        with self.assertRaisesRegex(ValueError, "table differs"):
            inspect_consumer(source.replace(b"0,100,320", b"1,100,320"), self.model)

    def test_real_data_fixture_bound_and_scope_are_explicit(self):
        source = self.source()
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        fixture, report = fixture_source(source, self.model, additional_fens=[fen])
        self.assertEqual(report["additional_data_fens"], 1)
        self.assertFalse(report["actual_engine_main_executed"])
        self.assertFalse(report["actual_search_executed"])
        self.assertFalse(report["full_engine_or_resource_qualification"])
        self.assertIn(b"e19_check_loop", fixture)
        with self.assertRaisesRegex(ValueError, "at most 256"):
            fixture_source(source, self.model, additional_fens=[fen] * 257)


if __name__ == "__main__":
    unittest.main()
