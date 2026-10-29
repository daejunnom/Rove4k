"""Resource arithmetic and admission for league-only fixed profiles."""
from contextlib import redirect_stderr
import importlib.util
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import league_resource_profiles as league
import production


class LeagueResourceProfiles(unittest.TestCase):
    def test_actual_compact_geometry_and_threads(self):
        for profile_id, workers, cap, bits, total in (
            ("test-p16", 16, 16 << 30, 29, 12 << 30),
            ("test-p192", 192, 192 << 30, 33, 192 << 30),
        ):
            with self.subTest(profile=profile_id):
                profile = league.resource_profile(production, profile_id)
                layout = profile.layout(24)
                self.assertEqual((profile.id, profile.purpose, profile.workers,
                                  profile.tt_cap_bytes, profile.os_threads),
                                 (profile_id, "test", workers, cap, workers + 1))
                self.assertEqual((layout.bits, layout.entries, layout.bytes, layout.mask),
                                 (bits, 1 << bits, total, (1 << bits) - 1))
                self.assertFalse(profile.to_record(24)["event_allocation_confirmed"] is True)

    def test_p192_page_ranges_cover_exactly_once_when_not_evenly_divisible(self):
        profile = league.resource_profile(production, "test-p192")
        layout = profile.layout(24)
        rows = profile.init_ranges(layout, base_address=0x100000)
        self.assertEqual(len(rows), 192)
        self.assertEqual(rows[0].begin, 0)
        self.assertEqual(rows[-1].end, 1 << 33)
        self.assertEqual(sum(row.entries for row in rows), 1 << 33)
        self.assertEqual({row.entries // 512 for row in rows}, {87381, 87382})
        self.assertTrue(all(row.begin % 512 == row.end % 512 == 0 for row in rows))
        self.assertTrue(all(left.end == right.begin for left, right in zip(rows, rows[1:])))
        self.assertNotEqual(rows[0].end, (1 << 33) // 192)

    def test_p16_ranges_and_historical_profile_are_separate(self):
        profile = league.resource_profile(production, "test-p16")
        rows = profile.init_ranges(profile.layout(24), base_address=0x100000)
        self.assertEqual(len(rows), 16)
        self.assertEqual({row.entries for row in rows}, {1 << 25})
        self.assertTrue(all(left.end == right.begin for left, right in zip(rows, rows[1:])))
        self.assertNotIn("test-p16", production.PROFILES)
        self.assertNotIn("test-p192", production.PROFILES)
        self.assertEqual(league.resource_profile(production, "test-p4"),
                         production.resource_profile("test-p4"))
        with self.assertRaises(ValueError):
            league.resource_profile(production, "unregistered")
        with self.assertRaises(ValueError):
            league.resource_profile(production, True)
        with self.assertRaises(TypeError):
            league.LEAGUE_PROFILES["test-p16"] = (1, 1)

    def test_new_profiles_fail_closed_before_unreviewed_builder_paths(self):
        source = Path(__file__).resolve().parents[1] / "experiments/tcec-next/profile_build.py"
        spec = importlib.util.spec_from_file_location("league_profile_build_test", source)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        for profile in league.LEAGUE_PROFILES:
            base = ["profile_build.py", "--entry", "A", "--profile", profile, "--out", "/unused"]
            self.assertEqual(builder.argument_parser().parse_args(base[1:]).profile, profile)
            for options in (("--representation", "self-contained-elf"),
                            ("--phase-variant", "phase-init"),
                            ("--ep-variant", "legal-maker")):
                with self.subTest(profile=profile, options=options), patch.object(sys, "argv", [*base, *options]):
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as caught:
                        builder.main()
                    self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
