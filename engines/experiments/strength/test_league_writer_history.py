"""Mutation, replay and uniqueness contracts for diagnostic writer history."""
import copy
import unittest

try:
    from . import league_writer_history as history
except ImportError:
    import league_writer_history as history


def intent(attempt="attempt-1", subject="game-1", kind="go"):
    return {"attempt_id": attempt, "subject_id": subject, "intent_kind": kind,
            "job_sha256": "1" * 64, "host_sha256": "2" * 64,
            "request_sha256": "3" * 64, "not_before_utc_ms": 1_000, "expires_utc_ms": 2_000}


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.root = history.genesis("league-test", "a" * 64, "b" * 64, "c" * 64, 12_000_000)

    def events(self):
        head, first = history.append(self.root, [], self.root, "diagnostic", intent())
        head, second = history.append(self.root, [first], head, "diagnostic", intent("attempt-2", "game-2"))
        head, third = history.append(self.root, [first, second], head, "drain", {"reason": "manual"})
        return head, [first, second, third]

    def test_full_history_round_trip_and_authority_is_not_granted(self):
        head, rows = self.events()
        self.assertEqual(history.replay(self.root, rows, head), head)
        self.assertEqual(head["revision"], 3)
        self.assertEqual(head["mode"], "draining")
        self.assertNotIn("authorizes_go", head)
        self.assertNotIn("authorizes_launch", head)

    def test_removed_inserted_reordered_or_changed_history_is_rejected(self):
        head, rows = self.events()
        changed = copy.deepcopy(rows)
        changed[1]["payload"]["job_sha256"] = "4" * 64
        for candidate in (rows[:-1], rows[1:], rows + [rows[-1]], [rows[1], rows[0], rows[2]], changed):
            with self.subTest(candidate=len(candidate)), self.assertRaises(ValueError):
                history.replay(self.root, candidate, head)

    def test_rehashing_a_gap_or_changed_owner_does_not_hide_order(self):
        head, rows = self.events()
        for field, value in (("revision", 8), ("epoch_before", 8), ("owner_before", "d" * 64)):
            altered = copy.deepcopy(rows)
            altered[0][field] = value
            core = {k: v for k, v in altered[0].items() if k != "sha256"}
            altered[0]["sha256"] = history._hash(b"rove4k-league-event-v2\0", core)
            with self.subTest(field=field), self.assertRaises(ValueError):
                history.replay(self.root, altered, head)

    def test_attempt_and_subject_are_unique_in_complete_history(self):
        head, first = history.append(self.root, [], self.root, "diagnostic", intent())
        for second in (intent("attempt-1", "other"), intent("other", "game-1")):
            with self.subTest(second=second), self.assertRaises(ValueError):
                history.append(self.root, [first], head, "diagnostic", second)
        other_kind = intent("attempt-3", "game-1", "launch")
        next_head, event = history.append(self.root, [first], head, "diagnostic", other_kind)
        self.assertEqual(history.replay(self.root, [first, event], next_head), next_head)

    def test_untrusted_budget_observation_is_monotonic_and_cannot_reopen(self):
        payload = {"budget_head": "d" * 64, "budget_upper_micros": 120_000_000, "evidence_sha256": "e" * 64}
        head, row = history.append(self.root, [], self.root, "budget_observed", payload)
        self.assertEqual(head["mode"], "draining")
        with self.assertRaisesRegex(ValueError, "cannot decrease"):
            history.append(self.root, [row], head, "budget_observed", {**payload, "budget_upper_micros": 119_999_999})
        with self.assertRaises(ValueError):
            history.append(self.root, [row], head, "diagnostic", intent())
        advanced, event = history.append(self.root, [row], head, "handoff", {"new_owner": "f" * 64})
        self.assertEqual(advanced["mode"], "draining")
        self.assertEqual(advanced["epoch"], 1)
        self.assertEqual(history.replay(self.root, [row, event], advanced), advanced)

    def test_type_and_namespace_validation_rejects_bool_numeric_aliases(self):
        with self.assertRaises(ValueError):
            history.genesis("legacy", "a" * 64, "b" * 64, "c" * 64, 0)
        with self.assertRaises(ValueError):
            history.genesis("league-test", "a" * 64, "b" * 64, "c" * 64, True)
        head, row = history.append(self.root, [], self.root, "diagnostic", intent())
        altered = copy.deepcopy(row)
        altered["revision"] = True
        with self.assertRaises(ValueError):
            history.replay(self.root, [altered], head)
        altered_head = {**head, "revision": True}
        with self.assertRaises(ValueError):
            history.replay(self.root, [row], altered_head)
        with self.assertRaises(ValueError):
            history.append(self.root, [], self.root, "diagnostic", {**intent(), "expires_utc_ms": True})

    def test_expected_and_genesis_are_required_and_not_mutated(self):
        before = copy.deepcopy(self.root)
        payload = intent()
        head, row = history.append(self.root, [], self.root, "diagnostic", payload)
        payload["attempt_id"] = "changed"
        self.assertEqual(row["payload"]["attempt_id"], "attempt-1")
        self.assertEqual(self.root, before)
        with self.assertRaises(ValueError):
            history.append(self.root, [row], self.root, "drain", {"reason": "manual"})
        with self.assertRaises(ValueError):
            history.replay({**self.root, "revision": False}, [row], head)
        with self.assertRaises(ValueError):
            history.replay({**self.root, "history_sha256": "f" * 64}, [row], head)

    def test_unknown_fields_actions_and_windows_fail_closed(self):
        for bad in ({**intent(), "extra": 1}, {**intent(), "intent_kind": "terminate"},
                    {**intent(), "expires_utc_ms": 61_001}, {**intent(), "subject_id": "has space"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                history.append(self.root, [], self.root, "diagnostic", bad)
        with self.assertRaises(ValueError):
            history.append(self.root, [], self.root, "approve_go", {})
        with self.assertRaises(ValueError):
            history.append(self.root, [], self.root, "handoff", {"new_owner": "d" * 64})


if __name__ == "__main__":
    unittest.main()
