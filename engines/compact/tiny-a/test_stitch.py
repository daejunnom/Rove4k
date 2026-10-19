"""Pure source-layout boundary checks; no compiler or engine process required."""
from pathlib import Path
import unittest

from stitch import stitch

HERE = Path(__file__).resolve().parent


class StitchTests(unittest.TestCase):
    def inputs(self, board="board-generated.c.in", runtime="main.c"):
        selected = ("tiny.h", board, "search.c", runtime)
        return {name: (HERE / name).read_bytes().replace(b"\r\n", b"\n") for name in selected}, selected

    def test_lf_and_crlf_assembled_bytes_equal(self):
        for board in ("board.c", "board-rays.c.in", "board-forward.c.in", "board-generated.c.in"):
            for runtime in ("main.c", "main-futex.c.in"):
                sources, selected = self.inputs(board, runtime)
                windows = {name: data.replace(b"\n", b"\r\n") for name, data in sources.items()}
                for lean in (False, True):
                    with self.subTest(board=board, runtime=runtime, lean=lean):
                        lf, lf_record = stitch(sources, selected, lean)
                        crlf, crlf_record = stitch(windows, selected, lean)
                        self.assertEqual(lf, crlf)
                        self.assertNotIn(b"\r", crlf)
                        self.assertEqual(lf_record["normalized_inputs"], [])
                        self.assertEqual(set(crlf_record["normalized_inputs"]), set(selected))
                        self.assertEqual(crlf_record["newline_normalization"], "CRLF_to_LF")
                        if lean:
                            self.assertEqual(crlf_record["removed_externs"], 10)
                            self.assertEqual(crlf_record["removed_prototypes"], 11)

    def test_declaration_count_fails_closed(self):
        sources, selected = self.inputs()
        for before, after in ((b"extern uint64_t deadline;\n", b""),
                              (b"int dead(const Board *);\n", b"int dead(const Board *);\nint extra(void);\n")):
            changed = {**sources, "tiny.h": sources["tiny.h"].replace(before, after)}
            self.assertNotEqual(changed["tiny.h"], sources["tiny.h"])
            for windows in (False, True):
                with self.subTest(declaration=before, windows=windows):
                    data = {name: value.replace(b"\n", b"\r\n") for name, value in changed.items()} if windows else changed
                    with self.assertRaisesRegex(ValueError, "fixed API declaration count changed"):
                        stitch(data, selected, True)

    def test_clock_shape_fails_closed(self):
        sources, selected = self.inputs()
        changed = {**sources, "main.c": sources["main.c"].replace(b"uint64_t now(void)", b"uint64_t changed_clock(void)")}
        with self.assertRaisesRegex(ValueError, "exactly one declared monotonic clock definition"):
            stitch(changed, selected, True)


if __name__ == "__main__":
    unittest.main()
