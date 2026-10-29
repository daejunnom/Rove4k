import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("table_generate_test", HERE / "generate.py")
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)


class ExactTable(unittest.TestCase):
    def test_complete_signed_piece_square_domain(self):
        values = generate.table_values()
        self.assertEqual(len(values), 832)
        self.assertEqual(values[6 * 64:7 * 64], [0] * 64)
        for piece in range(1, 7):
            for q in range(64):
                rotated = 63 - q
                self.assertEqual(values[(piece + 6)*64 + q], -values[(6-piece)*64 + rotated])
        self.assertLess(max(map(abs, values)), 2**31)

    def test_both_bounded_representations_preserve_identity(self):
        template = (b"@TABLE_DECL@\nstatic void __attribute__((constructor)) tiny_eval_init(void){\n@TABLE_INIT@\n}\nstatic int tiny_raw(const Board *p){return 0;}")
        startup, left = generate.produce(template, "startup")
        readonly, right = generate.produce(template, "readonly")
        self.assertEqual(left["table_i32le_sha256"], right["table_i32le_sha256"])
        self.assertIn(b"value(v,", startup)
        self.assertNotIn(b"value(v,", readonly)
        self.assertIn(b"const int32_t", readonly)
        self.assertEqual(left["table_bytes"], 3328)
        self.assertFalse(left["cached_hce_used"])

    def test_unknown_or_ambiguous_templates_fail(self):
        for template in (b"@TABLE_DECL@", b"@TABLE_DECL@@TABLE_DECL@@TABLE_INIT@"):
            with self.assertRaisesRegex(ValueError, "template shape"):
                generate.produce(template, "startup")
        with self.assertRaisesRegex(ValueError, "only startup or readonly"):
            generate.produce(b"", "packed")


if __name__ == "__main__":
    unittest.main()
