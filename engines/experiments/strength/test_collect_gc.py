import copy
import unittest

import collect
import ledger


class CooperativeGcCollectionTests(unittest.TestCase):
    campaign = "fixture"
    pair = "pair-0"

    def row(self, event, game, data, attempt=0):
        return {"campaign": self.campaign, "pair": self.pair, "game": game,
                "attempt": attempt, "event": event, "data": data}

    def make_leg(self, leg, *, request_delta=0, performed_delta=0):
        game = f"game-{leg}"
        white, black = ("A", "B") if leg == 0 else ("B", "A")
        spec = {"leg": leg, "white": white, "black": black, "opening_id": "opening-0",
                "profile": "test-p16", "opening_sha256": "c" * 64, "bank_id": "d" * 64,
                "artifact_sha256": {"A": "a" * 64, "B": "b" * 64}}
        process = {"instance_id": "i-fixture", "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
                   "pid": 100 + leg, "pgid": 100 + leg, "session": 100 + leg,
                   "start_ticks": 200 + leg, "identity": game, "spawn_monotonic": 0.0000015}
        identity = {"instance_id": process["instance_id"], "boot_id": process["boot_id"],
                    "launch_pid": process["pid"], "launch_start_ticks": process["start_ticks"],
                    "observer_pid": 42, "observer_start_ticks": 10, "scope_start_ns": 1000 + leg}
        scope = {**identity, "format": "rove4k-cooperative-gc-v1",
                 "coverage_scope": "owned-controller-explicit-gc",
                 "scope_id": ledger.cooperative_gc_scope_id(self.campaign, self.pair, game, 0, identity),
                 "request_count": 9, "performed_count": 8, "active_count": 0, "coverage_complete": True}
        body = {name: spec[name] for name in ("white", "black", "opening_id", "opening_sha256",
                                              "bank_id", "profile", "artifact_sha256")}
        body.update({"result": "1-0" if leg == 0 else "0-1", "reason": "completed_chess_result",
                     "pgn_sha256": "e" * 64, "raw_sha256": "f" * 64,
                     "pgn_object_key": f"fixture/{game}.pgn", "raw_object_key": f"fixture/{game}.log"})
        close = {**scope, "scope_end_ns": 2000 + leg, "request_count": 9 + request_delta,
                 "performed_count": 8 + performed_delta, "result_sha256": ledger.digest(body)}
        acknowledgement = {"sha256": ledger.digest(body), "verified": True,
                           "object_key": f"fixture/{game}.json", "backend": "s3", "bucket": "bucket",
                           "evidence": [{"sha256": body[kind + "_sha256"], "verified": True,
                                         "object_key": body[kind + "_object_key"],
                                         "backend": "s3", "bucket": "bucket"}
                                        for kind in ("pgn", "raw")]}
        completion = {**process, "gate_released": True, "cleanup_forced": False, "returncode": 0,
                      "readers_done": True, "remaining_processes": [], "completed_monotonic": 0.0000018}
        return [self.row("game.started", game, spec), self.row("game.process", game, process),
                self.row("game.cooperative_gc_open", game, scope),
                self.row("game.process_completed", game, completion), self.row("game.result", game, body),
                self.row("game.cooperative_gc_close", game, close),
                self.row("game.remote_confirmed", game, acknowledgement)]

    def summary(self, rows):
        return collect.collect(rows, self.campaign, expected_pairs=[self.pair], profile="test-p16")

    def test_complete_clean_explicit_gc_scope_can_be_scored(self):
        rows = self.make_leg(0) + self.make_leg(1)
        summary = self.summary(rows)
        self.assertTrue(summary["campaign_stage_complete"])
        self.assertTrue(summary["selection_ready"])
        self.assertEqual(summary["performance_excluded_pairs"], [])
        self.assertEqual((summary["standings"][0]["player"], summary["standings"][0]["points"]), ("A", 2))
        self.assertTrue(all(row["performance_included"] for row in summary["raw_completed_games"]))

    def test_requested_or_performed_gc_excludes_pair_but_preserves_results(self):
        for name in ("request_delta", "performed_delta"):
            with self.subTest(name=name):
                rows = self.make_leg(0, **{name: 1}) + self.make_leg(1, **{name: 1})
                summary = self.summary(rows)
                self.assertTrue(summary["campaign_stage_complete"])
                self.assertFalse(summary["selection_ready"])
                self.assertEqual(summary["standings"], [])
                self.assertEqual(len(summary["raw_completed_games"]), 2)
                self.assertEqual(summary["performance_excluded_pairs"][0]["games"][0]["cooperative_gc"], "intervened")

    def test_gc_already_active_at_start_or_still_active_at_end_is_excluded(self):
        for event in ("game.cooperative_gc_open", "game.cooperative_gc_close"):
            rows = self.make_leg(0) + self.make_leg(1)
            target = next(row for row in rows if row["game"] == "game-0" and row["event"] == event)
            target["data"]["active_count"] = 1
            summary = self.summary(rows)
            self.assertFalse(summary["selection_ready"])
            self.assertEqual(summary["performance_excluded_pairs"][0]["games"][0]["cooperative_gc"], "intervened")

    def test_missing_incomplete_or_forged_interval_is_not_clean(self):
        original = self.make_leg(0) + self.make_leg(1)
        variants = []
        variants.append([row for row in original if not (row["game"] == "game-0" and
                                                          row["event"] == "game.cooperative_gc_close")])
        for field, value in (("coverage_complete", False), ("result_sha256", "0" * 64),
                             ("launch_pid", True), ("scope_end_ns", -1), ("request_count", True),
                             ("scope_end_ns", 10 ** 400), ("request_count", 10 ** 400)):
            changed = copy.deepcopy(original)
            close = next(row for row in changed if row["game"] == "game-0" and
                         row["event"] == "game.cooperative_gc_close")
            close["data"][field] = value
            variants.append(changed)
        changed = copy.deepcopy(original)
        opened = next(row for row in changed if row["game"] == "game-0" and
                      row["event"] == "game.cooperative_gc_open")
        changed.insert(changed.index(opened) + 1, copy.deepcopy(opened))
        variants.append(changed)
        for field, value in (("pid", True), ("returncode", False), ("readers_done", False),
                             ("cleanup_forced", True), ("remaining_processes", [101]),
                             ("completed_monotonic", 10 ** 400)):
            changed = copy.deepcopy(original)
            completion = next(row for row in changed if row["game"] == "game-0" and
                              row["event"] == "game.process_completed")
            completion["data"][field] = value
            variants.append(changed)
        changed = copy.deepcopy(original)
        opened = next(row for row in changed if row["game"] == "game-0" and
                      row["event"] == "game.cooperative_gc_open")
        opened["attempt"] = False
        variants.append(changed)
        for rows in variants:
            with self.subTest(rows=rows):
                summary = self.summary(rows)
                self.assertTrue(summary["campaign_stage_complete"])
                self.assertFalse(summary["selection_ready"])
                self.assertEqual(summary["standings"], [])
                self.assertEqual(len(summary["raw_completed_games"]), 2)

    def test_normal_automatic_gc_is_not_an_explicit_intervention(self):
        rows = self.make_leg(0) + self.make_leg(1)
        rows.insert(3, self.row("game.python_automatic_gc", "game-0", {"count": 1}))
        self.assertTrue(self.summary(rows)["selection_ready"])

    def test_overlapping_scopes_reject_inconsistent_global_counters(self):
        rows = self.make_leg(0, request_delta=1) + self.make_leg(1)
        summary = self.summary(rows)
        self.assertFalse(summary["selection_ready"])
        statuses = [item["cooperative_gc"] for item in summary["performance_excluded_pairs"][0]["games"]]
        self.assertEqual(statuses, ["unverified", "unverified"])

    def test_overlapping_scopes_on_one_host_with_different_observers_are_unverified(self):
        rows = self.make_leg(0) + self.make_leg(1)
        relevant = [row for row in rows if row["game"] == "game-1" and
                    row["event"] in ("game.cooperative_gc_open", "game.cooperative_gc_close")]
        for row in relevant:
            row["data"]["observer_pid"] = 43
            identity = {name: row["data"][name] for name in
                        ("instance_id", "boot_id", "launch_pid", "launch_start_ticks",
                         "observer_pid", "observer_start_ticks", "scope_start_ns")}
            row["data"]["scope_id"] = ledger.cooperative_gc_scope_id(self.campaign, self.pair, "game-1", 0, identity)
        summary = self.summary(rows)
        self.assertFalse(summary["selection_ready"])
        statuses = [item["cooperative_gc"] for item in summary["performance_excluded_pairs"][0]["games"]]
        self.assertEqual(statuses, ["unverified", "unverified"])

    def test_scope_must_cover_spawn_and_completion(self):
        rows = self.make_leg(0) + self.make_leg(1)
        relevant = [row for row in rows if row["game"] == "game-0" and
                    row["event"] in ("game.cooperative_gc_open", "game.cooperative_gc_close")]
        for row in relevant:
            row["data"]["scope_start_ns"] = 5_000_000
            if row["event"] == "game.cooperative_gc_close":
                row["data"]["scope_end_ns"] = 6_000_000
            identity = {name: row["data"][name] for name in
                        ("instance_id", "boot_id", "launch_pid", "launch_start_ticks",
                         "observer_pid", "observer_start_ticks", "scope_start_ns")}
            row["data"]["scope_id"] = ledger.cooperative_gc_scope_id(self.campaign, self.pair, "game-0", 0, identity)
        self.assertFalse(self.summary(rows)["selection_ready"])

    def test_large_monotonic_float_uses_outward_integer_bounds(self):
        seconds = 9_000_000_000.0
        exact = 9_000_000_000_000_000_000
        lower = collect.conservative_monotonic_ns(seconds, lower=True)
        upper = collect.conservative_monotonic_ns(seconds, lower=False)
        self.assertLess(lower, exact - 1000)
        self.assertGreater(upper, exact + 1000)

    def test_submicrosecond_scope_gaps_and_impossible_counters_are_not_clean(self):
        for mode in ("start-gap", "end-gap", "performed-exceeds-request", "impossible-active"):
            rows = self.make_leg(0) + self.make_leg(1)
            records = [row for row in rows if row["game"] == "game-0" and
                       row["event"] in ("game.cooperative_gc_open", "game.cooperative_gc_close")]
            if mode == "start-gap":
                for row in records:
                    row["data"]["scope_start_ns"] = 1900  # spawn at 1500 ns; gap was formerly accepted
                    identity = {name: row["data"][name] for name in
                                ("instance_id", "boot_id", "launch_pid", "launch_start_ticks",
                                 "observer_pid", "observer_start_ticks", "scope_start_ns")}
                    row["data"]["scope_id"] = ledger.cooperative_gc_scope_id(
                        self.campaign, self.pair, "game-0", 0, identity)
            elif mode == "end-gap":
                records[1]["data"]["scope_end_ns"] = 1500  # finish at 1800 ns
            else:
                for row in records:
                    if mode == "performed-exceeds-request":
                        row["data"]["performed_count"] = 10
                    else:
                        row["data"]["active_count"] = 2
            with self.subTest(mode=mode):
                self.assertFalse(self.summary(rows)["selection_ready"])

    def extra_leg(self):
        rows = self.make_leg(0)
        for row in rows:
            row["pair"], row["game"] = "pair-extra", "game-extra"
            if row["event"] in ("game.cooperative_gc_open", "game.cooperative_gc_close"):
                identity = {name: row["data"][name] for name in
                            ("instance_id", "boot_id", "launch_pid", "launch_start_ticks",
                             "observer_pid", "observer_start_ticks", "scope_start_ns")}
                row["data"]["scope_id"] = ledger.cooperative_gc_scope_id(
                    self.campaign, "pair-extra", "game-extra", 0, identity)
        return rows

    def test_unfinished_other_scope_on_same_host_blocks_performance_not_raw_results(self):
        rows = self.make_leg(0) + self.make_leg(1)
        extra = self.extra_leg()[:3]  # started, process and open, but no completion/close
        extra.append({"campaign": self.campaign, "pair": "pair-extra", "game": "game-extra",
                      "attempt": 0, "event": "game.interrupted", "data": {"reason": "host_interruption"}})
        summary = self.summary(extra + rows)
        self.assertTrue(summary["campaign_stage_complete"])
        self.assertFalse(summary["selection_ready"])
        self.assertEqual(len(summary["raw_completed_games"]), 2)
        self.assertEqual(summary["standings"], [])

    def test_unbound_started_attempt_cannot_be_assumed_to_be_on_another_host(self):
        rows = self.make_leg(0) + self.make_leg(1)
        summary = self.summary(self.extra_leg()[:1] + rows)
        self.assertFalse(summary["selection_ready"])
        self.assertEqual(summary["standings"], [])

    def test_unfinished_attempt_from_another_boot_is_not_the_same_host_scope(self):
        rows = self.make_leg(0) + self.make_leg(1)
        extra = self.extra_leg()[:3]
        extra[1]["data"]["boot_id"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        summary = self.summary(extra + rows)
        self.assertTrue(summary["selection_ready"])

    def test_unfinished_attempt_with_invalid_boot_cannot_be_assumed_nonoverlapping(self):
        rows = self.make_leg(0) + self.make_leg(1)
        extra = self.extra_leg()[:3]
        extra[1]["data"]["boot_id"] = "-" * 36
        summary = self.summary(extra + rows)
        self.assertFalse(summary["selection_ready"])

    def test_unacknowledged_completed_scope_still_participates_in_counter_checks(self):
        rows = self.make_leg(0) + self.make_leg(1)
        extra = self.extra_leg()[:-1]  # result and close, no remote acknowledgement
        close = next(row for row in extra if row["event"] == "game.cooperative_gc_close")
        close["data"]["request_count"] += 1
        summary = self.summary(extra + rows)
        self.assertFalse(summary["selection_ready"])
        self.assertEqual(summary["standings"], [])


if __name__ == "__main__":
    unittest.main()
