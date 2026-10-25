import unittest

from openings import family, select_openings


class OpeningSelectionTests(unittest.TestCase):
    def rows(self):
        values = []
        for bucket in "ABCDE":
            for index in range(10):
                # Pure selector fixtures only. Legal SAN/UCI replay is the real
                # corpus preparation's separate chess-parser boundary.
                moves = tuple(f"{bucket}{index}-{ply}" for ply in range(8))
                values.append({"family": family(moves), "moves": moves, "eco": bucket + "00",
                               "name": f"{bucket}-{index}", "source_row_sha256": "a" * 64})
        return values

    def test_stage_holdouts_are_disjoint_reproducible_and_balanced(self):
        first = select_openings(self.rows())
        second = select_openings(list(reversed(self.rows())))
        self.assertEqual(first, second)
        all_families = [row.family for values in first.values() for row in values]
        self.assertEqual(len(all_families), 32)
        self.assertEqual(len(set(all_families)), 32)
        self.assertEqual({name: len(values) for name, values in first.items()},
                         {"broad": 12, "high": 12, "update1": 4, "update2": 4})
        for stage in ("broad", "high"):
            self.assertEqual({row.eco[0] for row in first[stage]}, set("ABCDE"))

    def test_missing_actual_family_or_duplicate_family_rejects(self):
        with self.assertRaisesRegex(ValueError, "eight"):
            family(["e2e4"])
        rows = self.rows()
        with self.assertRaisesRegex(ValueError, "more than once"):
            select_openings(rows + [rows[0]])
        rows[0] = {**rows[0], "family": "pretend"}
        with self.assertRaisesRegex(ValueError, "actual moves"):
            select_openings(rows)


if __name__ == "__main__":
    unittest.main()
