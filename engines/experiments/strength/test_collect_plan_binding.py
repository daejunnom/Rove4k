"""Frozen plan consistency checks do not establish game authority."""
import copy
import tempfile
import unittest
from pathlib import Path

import collect
import ledger
from test_run import add_leg


class FrozenPlanBinding(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        with ledger.Journal(Path(self.directory.name) / "journal.jsonl", "fixture") as journal:
            add_leg(journal, 0)
            add_leg(journal, 1, result="0-1")
            self.rows = copy.deepcopy(journal.rows)
        for row in self.rows:
            if row["event"] == "game.started":
                row["data"]["runner_sha256"] = "d" * 64
        self.plan = {"campaign": "fixture", "profile": "test-p4", "bank_id": "b" * 64,
                     "runner": {"sha256": "d" * 64},
                     "registry": {"players": [
                         {"artifact": {"id": "fixture-A", "sha256": "a" * 64}},
                         {"artifact": {"id": "fixture-B", "sha256": "c" * 64}}]},
                     "pairs": [{"id": "fixture-pair", "players": ["fixture-A", "fixture-B"],
                                "opening": {"id": "fixture-opening", "moves": ["f2f3", "e7e5"]}}]}

    def collect(self, rows=None, plan=None):
        return collect.collect(self.rows if rows is None else rows, "fixture", profile="test-p4",
                               expected_pairs=["fixture-pair"], plan=self.plan if plan is None else plan)

    def test_complete_pair_binds_but_is_not_an_authority_claim(self):
        result = self.collect()
        self.assertTrue(result["plan_game_binding_checked"])
        self.assertTrue(result["campaign_stage_complete"])
        self.assertEqual(result["standings"][0]["points"], 2)
        self.assertIn("no host attestation", result["scope"])

    def test_partial_pair_stays_incomplete(self):
        rows = [row for row in self.rows if row.get("game") != "fixture-pair-leg1"]
        self.assertFalse(self.collect(rows)["selection_ready"])

    def test_p16_and_p192_bind_same_recorded_game_contract(self):
        for profile in ("test-p16", "test-p192"):
            with self.subTest(profile=profile):
                rows, plan = copy.deepcopy(self.rows), copy.deepcopy(self.plan)
                plan["profile"] = profile
                for row in rows:
                    if row["event"] in ("game.started", "game.result"):
                        row["data"]["profile"] = profile
                # A changed result has a different digest, so regenerate only
                # the fixture acknowledgements and GC closing references.
                results = {row["game"]: ledger.digest(row["data"]) for row in rows
                           if row["event"] == "game.result"}
                for row in rows:
                    if row["event"] == "game.cooperative_gc_close":
                        row["data"]["result_sha256"] = results[row["game"]]
                    elif row["event"] == "game.remote_confirmed":
                        row["data"]["sha256"] = results[row["game"]]
                summary = collect.collect(rows, "fixture", profile=profile,
                                          expected_pairs=["fixture-pair"], plan=plan)
                self.assertTrue(summary["plan_game_binding_checked"])
                self.assertTrue(summary["selection_ready"])

    def test_wrong_players_opening_resources_and_runner_are_rejected(self):
        cases = [
            lambda p: p["pairs"][0]["players"].reverse(),
            lambda p: p["pairs"][0]["opening"].update(id="other-opening"),
            lambda p: p["pairs"][0]["opening"].update(moves=["e2e4"]),
            lambda p: p.update(bank_id="e" * 64),
            lambda p: p["runner"].update(sha256="e" * 64),
            lambda p: p["registry"]["players"][0]["artifact"].update(sha256="e" * 64),
        ]
        for change in cases:
            with self.subTest(change=change):
                plan = copy.deepcopy(self.plan)
                change(plan)
                with self.assertRaisesRegex(ValueError, "differs from its frozen plan"):
                    self.collect(plan=plan)

    def test_missing_runner_or_wrong_game_identity_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        del next(row for row in rows if row["event"] == "game.started")["data"]["runner_sha256"]
        with self.assertRaisesRegex(ValueError, "differs from its frozen plan"):
            self.collect(rows)
        rows = copy.deepcopy(self.rows)
        for row in rows:
            if row.get("game") == "fixture-pair-leg0":
                row["game"] = "impostor-game"
        with self.assertRaisesRegex(ValueError, "differs from its frozen plan"):
            self.collect(rows)

    def test_plan_scope_and_duplicate_player_fail_closed(self):
        for change in (lambda p: p.update(campaign="other"),
                       lambda p: p["pairs"][0].update(id="other-pair"),
                       lambda p: p["registry"]["players"].append(p["registry"]["players"][0])):
            plan = copy.deepcopy(self.plan)
            change(plan)
            with self.assertRaises(ValueError):
                self.collect(plan=plan)


if __name__ == "__main__":
    unittest.main()
