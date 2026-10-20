import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("tiny_b_generate_test", HERE / "generate.py")
OVERLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OVERLAY)


class OverlayTests(unittest.TestCase):
    def test_frozen_inputs_are_repeatable(self):
        before = {name: (HERE / "base" / name).read_bytes() for name in OVERLAY.BASE}
        files = OVERLAY.sources()
        self.assertEqual(set(files), {"tiny.h", "board-generated.c.in", "search.c", "main.c"})
        self.assertEqual(files, OVERLAY.sources())
        self.assertEqual(before, {name: (HERE / "base" / name).read_bytes() for name in OVERLAY.BASE})

    def test_replacements_fail_closed(self):
        for text in ("absent", "needle needle"):
            with self.assertRaises(ValueError):
                OVERLAY.replace(text, "needle", "new")

    def test_changed_frozen_base_is_rejected(self):
        original = OVERLAY.HERE
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base").mkdir()
            (root / "base" / "tiny.h").write_bytes((HERE / "base" / "tiny.h").read_bytes() + b"\n")
            try:
                OVERLAY.HERE = root
                with self.assertRaisesRegex(ValueError, "frozen base bytes changed: tiny.h"):
                    OVERLAY.sources()
            finally:
                OVERLAY.HERE = original

    def test_counter_guard(self):
        with self.assertRaises(ValueError):
            OVERLAY.strip_counters(b"int main(void){return 0;}")


if __name__ == "__main__":
    unittest.main()
