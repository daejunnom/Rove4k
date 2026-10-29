"""Finite independent league producer selections; never run engines."""
from copy import copy
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("league_producer_selection_test", HERE / "profile_build.py")
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


class LeagueSelection(unittest.TestCase):
    def args(self, family, profile, variant):
        return builder.argument_parser().parse_args([
            "--entry", family, "--profile", profile, "--out", "unrun",
            "--league-variant", variant, "--source-dependencies", "control"])

    def test_reviewed_families_profiles_and_exact_declarations(self):
        for variant, families in (("atomic-assignment", "ACEF"),
                                  ("square-successor", "AC"), ("legal-maker", "CE"),
                                  ("square-atomic", "AC"), ("square-ep", "C"),
                                  ("ep-atomic", "CE"), ("square-ep-atomic", "C")):
            for family in families:
                for profile in ("test-p16", "test-p192"):
                    with self.subTest(variant=variant, family=family, profile=profile):
                        self.assertEqual(builder.league_selection(self.args(family, profile, variant)),
                            {"path": builder.LEAGUE_EXPERIMENTS[variant]["path"], "variant": variant})
        self.assertIsNone(builder.league_selection(self.args("A", "test-p16", "control")))

    def test_other_families_profiles_and_combinations_are_rejected(self):
        cases = (("square-successor", "EF"), ("legal-maker", "AF"), ("atomic-assignment", "B"),
                 ("square-atomic", "EF"), ("square-ep", "AEF"), ("ep-atomic", "AF"),
                 ("square-ep-atomic", "AEF"))
        for variant, families in cases:
            for family in families:
                with self.subTest(variant=variant, family=family), self.assertRaises(ValueError):
                    builder.league_selection(self.args(family, "test-p16", variant))
        for profile in ("test-p4", "test-p28", "tcec-provisional"):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                builder.league_selection(self.args("A", profile, "atomic-assignment"))
        base = self.args("A", "test-p16", "atomic-assignment")
        for field, changed in (("representation", "packed-native"), ("b_variant", "tcec-final-lf"),
                               ("phase_variant", "phase-init"), ("spelling_variant", "compound"),
                               ("scan_variant", "square-successor"), ("ep_variant", "legal-maker"),
                               ("source_dependencies", "unused-includes")):
            args = copy(base)
            setattr(args, field, changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                builder.league_selection(args)


if __name__ == "__main__":
    unittest.main()
