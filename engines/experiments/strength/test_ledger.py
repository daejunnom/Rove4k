import json
import os
from pathlib import Path
import tempfile
import unittest

from ledger import CampaignResults, Journal, digest, read_journal


class LedgerTests(unittest.TestCase):
    class ShortFile:
        def __init__(self, actual, stop=None):
            self.actual, self.stop, self.calls = actual, stop, 0

        def __getattr__(self, name):
            return getattr(self.actual, name)

        def write(self, body):
            self.calls += 1
            if self.stop is not None and self.calls > 1:
                return self.stop
            return self.actual.write(body[:7])

    def spec(self, leg):
        return {"leg": leg, "white": "A" if leg == 0 else "B", "black": "B" if leg == 0 else "A",
                "opening_id": "broad-000", "profile": "test-p4", "opening_sha256": "c" * 64,
                "bank_id": "d" * 64, "artifact_sha256": {"A": "a" * 64, "B": "b" * 64},
                "slot": "slot-000", "wave": 0}

    def event(self, name, data, leg=0, attempt=0):
        return {"campaign": "fixture", "pair": "p", "game": "g" + str(leg),
                "attempt": attempt, "event": name, "data": data}

    def complete(self, result, leg, value="1-0"):
        body = {name: self.spec(leg)[name] for name in
                ("white", "black", "opening_id", "opening_sha256", "bank_id", "profile", "artifact_sha256")}
        body.update({"result": value, "reason": "completed_chess_result", "pgn_sha256": "e" * 64,
                     "raw_sha256": "f" * 64, "pgn_object_key": f"fixture/g{leg}.pgn",
                     "raw_object_key": f"fixture/g{leg}.log"})
        result.apply(self.event("game.result", body, leg))
        ack = {"sha256": digest(body), "verified": True, "object_key": f"fixture/g{leg}.json",
               "evidence": [{"sha256": body[kind + "_sha256"], "verified": True,
                             "object_key": body[kind + "_object_key"], "reused_existing": False}
                            for kind in ("pgn", "raw")], "reused_existing": False}
        result.apply(self.event("game.remote_confirmed", ack, leg))
        return body, ack

    def test_half_pair_and_duplicate_upload_are_not_extra_games(self):
        result = CampaignResults("fixture")
        for leg in (0, 1):
            result.apply(self.event("game.started", self.spec(leg), leg))
        body, ack = self.complete(result, 0)
        self.assertEqual(result.pairs(), [])
        result.apply(self.event("game.result", body))
        result.apply(self.event("game.remote_confirmed", ack))
        self.complete(result, 1)
        self.assertEqual(len(result.pairs()), 1)
        self.assertEqual(result.pairs()[0]["score"], 1.0)
        with self.assertRaisesRegex(ValueError, "duplicate result"):
            result.apply(self.event("game.result", {**body, "result": "0-1"}))

    def test_infrastructure_is_unscored_and_retry_keeps_original_identity(self):
        result = CampaignResults("fixture")
        result.apply(self.event("game.started", self.spec(0)))
        result.apply(self.event("game.interrupted", {"reason": "host_interruption"}))
        with self.assertRaisesRegex(ValueError, "infrastructure"):
            result.apply(self.event("game.result", {"result": "1/2-1/2", "reason": "budget_termination"}))
        with self.assertRaisesRegex(ValueError, "retry changed"):
            result.apply(self.event("game.started", {**self.spec(0), "opening_id": "different"}, attempt=1))
        result.apply(self.event("game.started", {**self.spec(0), "slot": "slot-001", "wave": 1}, attempt=1))
        self.assertEqual(len(result.games), 2)
        self.assertEqual(result.pairs(), [])

    def test_pair_cannot_mix_different_opening_bytes(self):
        result = CampaignResults("fixture")
        result.apply(self.event("game.started", self.spec(0), 0))
        result.apply(self.event("game.started", {**self.spec(1), "opening_sha256": "f" * 64}, 1))
        self.complete(result, 0)
        body = {name: result.games["g1", 0].spec[name] for name in
                ("white", "black", "opening_id", "opening_sha256", "bank_id", "profile", "artifact_sha256")}
        body.update({"result": "1-0", "reason": "completed_chess_result", "pgn_sha256": "e" * 64,
                     "raw_sha256": "f" * 64, "pgn_object_key": "fixture/g1.pgn", "raw_object_key": "fixture/g1.log"})
        result.apply(self.event("game.result", body, 1))
        result.apply(self.event("game.remote_confirmed", {
            "sha256": digest(body), "verified": True, "object_key": "fixture/g1.json",
            "evidence": [{"sha256": body[kind + "_sha256"], "verified": True,
                          "object_key": body[kind + "_object_key"]} for kind in ("pgn", "raw")]}, 1))
        with self.assertRaisesRegex(ValueError, "pair legs differ"):
            result.pairs()

    def test_duplicate_verified_upload_ignores_retry_telemetry(self):
        result = CampaignResults("fixture")
        result.apply(self.event("game.started", self.spec(0)))
        body, original = self.complete(result, 0)
        retry = json.loads(json.dumps(original))
        retry["reused_existing"] = True
        for item in retry["evidence"]:
            item["reused_existing"] = True
        result.apply(self.event("game.remote_confirmed", retry))
        self.assertEqual(result.games["g0", 0].remote, original)
        retry["object_key"] = "fixture/different.json"
        with self.assertRaisesRegex(ValueError, "acknowledgement changed"):
            result.apply(self.event("game.remote_confirmed", retry))
        with self.assertRaisesRegex(ValueError, "completed chess result"):
            result.apply(self.event("game.interrupted", {"reason": "host_interruption"}))

    def test_result_remains_unaccepted_without_verified_raw_and_pgn(self):
        result = CampaignResults("fixture")
        result.apply(self.event("game.started", self.spec(0)))
        body, ack = self.complete(result, 0)
        result.games["g0", 0].remote = None  # Isolate the first-ack intake boundary.
        for changed in ({**ack, "evidence": ack["evidence"][:1]},
                        {**ack, "evidence": [ack["evidence"][0], {**ack["evidence"][1], "verified": False}]}):
            with self.assertRaisesRegex(ValueError, "evidence|objects"):
                result.apply(self.event("game.remote_confirmed", changed))
            self.assertFalse(result.games["g0", 0].accepted)

    def test_physically_written_chain_reopens_and_tamper_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "events.jsonl"
            with Journal(path, "fixture") as writer:
                first = writer.append("campaign.created", {"profile": "test-p4"})
                second = writer.append("budget.pair_started", {"pair_id": "p"})
            rows = read_journal(path, "fixture")
            self.assertEqual(rows, [first, second])
            original = path.read_bytes()
            path.write_bytes(original.replace(b"test-p4", b"test-p8"))
            damaged = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "hash chain"):
                Journal(path, "fixture")
            self.assertEqual(path.read_bytes(), damaged)

    def test_incomplete_tail_and_file_replacement_are_not_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "events.jsonl"
            with Journal(path, "fixture") as writer:
                writer.append("campaign.created")
                replacement = path.with_name("replacement.jsonl")
                replacement.write_bytes(path.read_bytes())
                os.replace(replacement, path)
                with self.assertRaisesRegex(ValueError, "identity changed"):
                    writer.append("campaign.next")
            body = path.read_bytes()
            path.write_bytes(body[:-1])
            with self.assertRaisesRegex(ValueError, "incomplete event"):
                read_journal(path, "fixture")
            self.assertEqual(path.read_bytes(), body[:-1])

    def test_short_writes_complete_before_publishing_the_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "events.jsonl"
            with Journal(path, "fixture") as writer:
                writer.file = self.ShortFile(writer.file)
                data = {"nested": {"value": 1}}
                returned = writer.append("campaign.created", data)
                self.assertGreater(writer.file.calls, 1)
                data["nested"]["value"] = 2
                returned["data"]["nested"]["value"] = 3
                self.assertEqual(writer.rows[0]["data"]["nested"]["value"], 1)
            self.assertEqual(read_journal(path, "fixture")[0]["data"]["nested"]["value"], 1)

    def test_failed_short_write_preserves_partial_tail_without_accepting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "events.jsonl"
            with Journal(path, "fixture") as writer:
                writer.file = self.ShortFile(writer.file, stop=0)
                with self.assertRaisesRegex(OSError, "partial tail"):
                    writer.append("budget.launch_requested", {"token": "fixture"})
                self.assertEqual(writer.rows, [])
                self.assertEqual(writer.offset, 0)
                self.assertEqual(writer.last, "0" * 64)
                self.assertEqual(path.stat().st_size, 7)
                with self.assertRaisesRegex(ValueError, "identity changed"):
                    writer.append("campaign.next")
            partial = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "incomplete event"):
                Journal(path, "fixture")
            self.assertEqual(path.read_bytes(), partial)


if __name__ == "__main__":
    unittest.main()
