"""Controller boundary/fault tests. Synthetic receipts never qualify real engines."""
from __future__ import annotations

import hashlib
import base64
from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import budget
import collect
import durability
import fastchess
import ledger
import registry
import run
import topology
import wave


def sha(data):
    return hashlib.sha256(data).hexdigest()


def protocol(player, direction, command):
    return f"[Engine] [19:24:15.663230] <     126244989433536>  {player} {direction} {command}\n"


class MemoryS3Port:
    """An injected unit-test transport, never used by the production CLI."""
    def __init__(self):
        self.objects = {}
        self.gate = None
        self.entered = threading.Event()
        self.failure = False
        self.max_publish_seconds = .2
        self.published = []

    def publish(self, path, key):
        self.entered.set()
        if self.gate is not None and not self.gate.wait(3):
            raise TimeoutError("test transport gate")
        data = path.read_bytes()
        if key in self.objects and self.objects[key] != data:
            raise ValueError("immutable object changed")
        self.objects[key] = data
        self.published.append(key)
        if self.failure:
            raise TimeoutError("lost remote acknowledgement fixture")
        return {"verified": True, "acknowledged": True, "backend": "s3", "bucket": "unit-test-bucket", "object_key": key,
                "sha256": sha(data), "bytes": len(data), "checksum_sha256": base64.b64encode(hashlib.sha256(data).digest()).decode()}

    def list_keys(self, prefix):
        return sorted(key for key in self.objects if key.startswith(prefix.rstrip("/") + "/"))

    def read_verified(self, key, *, expected_sha=None, max_bytes=4 << 20):
        data = self.objects[key]
        if len(data) > max_bytes or expected_sha is not None and sha(data) != expected_sha:
            raise ValueError("unit transport checksum/size mismatch")
        return data


def game_spec(leg=0, opening=None, players=None):
    moves = ["f2f3", "e7e5"] if opening is None else opening
    first, second = ("fixture-A", "fixture-B") if players is None else players
    identities = ({first: "a" * 64, second: "c" * 64} if players is None else
                  {name: sha(name.encode()) for name in players})
    return {"leg": leg, "white": first if leg == 0 else second,
            "black": second if leg == 0 else first, "profile": "test-p4",
            "opening_id": "fixture-opening", "opening_moves": moves,
            "opening_sha256": ledger.digest(moves), "bank_id": "b" * 64,
            "artifact_sha256": identities}


def add_leg(journal, leg, *, acknowledged=True, pair="fixture-pair", result="1-0", players=None):
    spec = game_spec(leg, players=players)
    keys = {"pair": pair, "game": pair + f"-leg{leg}", "attempt": 0}
    journal.append("game.started", spec, **keys)
    # A test-only owned-controller GC scope; real coverage requires the runner hook.
    process = {"instance_id": "i-fixture", "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
               "pid": 100 + leg, "pgid": 100 + leg, "session": 100 + leg,
               "start_ticks": 200 + leg, "identity": keys["game"], "spawn_monotonic": 0.0000015}
    identity = {"instance_id": process["instance_id"], "boot_id": process["boot_id"],
                "launch_pid": process["pid"], "launch_start_ticks": process["start_ticks"],
                "observer_pid": 42, "observer_start_ticks": 10, "scope_start_ns": 1000 + leg}
    scope = {**identity, "format": "rove4k-cooperative-gc-v1",
             "coverage_scope": "owned-controller-explicit-gc", "coverage_complete": True,
             "scope_id": ledger.cooperative_gc_scope_id("fixture", pair, keys["game"], 0, identity),
             "request_count": 0, "performed_count": 0, "active_count": 0}
    journal.append("game.process", process, **keys)
    journal.append("game.cooperative_gc_open", scope, **keys)
    data = {**{name: spec[name] for name in ("white", "black", "profile", "opening_id", "opening_sha256", "bank_id", "artifact_sha256")},
            "result": result, "reason": "completed_chess_result", "pgn_sha256": sha(b"unit-pgn"),
            "raw_sha256": sha(b"unit-raw"), "pgn_object_key": "fixture/games/pgn", "raw_object_key": "fixture/games/raw"}
    journal.append("game.process_completed", {**process, "gate_released": True, "cleanup_forced": False,
                   "returncode": 0, "readers_done": True, "remaining_processes": [],
                   "completed_monotonic": 0.0000018}, **keys)
    journal.append("game.result", data, **keys)
    journal.append("game.cooperative_gc_close", {**scope, "scope_end_ns": 2000 + leg,
                   "result_sha256": ledger.digest(data)}, **keys)
    if acknowledged:
        journal.append("game.remote_confirmed", {"sha256": ledger.digest(data), "verified": True,
            "object_key": "unit-test/result", "backend": "s3", "bucket": "unit-test-bucket",
            "evidence": [{"sha256": data[kind + "_sha256"], "verified": True, "backend": "s3",
                          "bucket": "unit-test-bucket", "object_key": data[kind + "_object_key"]} for kind in ("pgn", "raw")]}, **keys)
    return keys, data


class ProtocolTests(unittest.TestCase):
    def test_confirmed_history_and_fixed_clock(self):
        trace = run.TraceState(["f2f3", "e7e5"], "fixture-A", "fixture-B")
        position = trace.consume(protocol("fixture-A", "<---", "position startpos moves f2f3 e7e5").strip())
        self.assertEqual(position["moves"], ["f2f3", "e7e5"])
        clock = trace.consume(protocol("fixture-A", "<---", "go wtime 1803000 btime 1803000 winc 3000 binc 3000").strip())
        self.assertEqual(clock["clock"]["wtime"], 1803000)
        candidate = trace.consume(protocol("fixture-A", "--->", "bestmove g2g4").strip())
        self.assertTrue(candidate["legal"])
        self.assertEqual(trace.moves, ["f2f3", "e7e5"])
        trace.consume(protocol("fixture-B", "<---", "position startpos moves f2f3 e7e5 g2g4").strip())
        self.assertEqual(trace.moves[-1], "g2g4")
        trace.consume(protocol("fixture-B", "<---", "go wtime 1805000 btime 1803000 winc 3000 binc 3000").strip())

    def test_spoofed_info_and_stderr_do_not_become_commands(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        fake = protocol("fixture-A", "--->", "info string go wtime 0 btime 0 winc 0 binc 0").strip()
        self.assertIsNone(trace.consume(fake))
        self.assertIsNone(trace.consume("garbage " + protocol("fixture-A", "<---", "position startpos")))
        self.assertIsNone(trace.consume("[Engine] [x] < 1> <stderr> fixture-A <--- position startpos"))
        self.assertTrue(trace.first_go)

    def test_optional_ponder_traffic_is_recorded_without_claiming_it_was_disabled(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        observed = trace.consume(protocol("fixture-B", "<---", "go ponder wtime 100 btime 100").strip())
        self.assertEqual(observed["kind"], "ponder_go_sent")
        self.assertIsNone(observed["actual_off_turn_search"])
        self.assertEqual(fastchess.ponder_uci_evidence(trace.ponder_sent["fixture-B"])["go_ponder_received"], 1)
        self.assertTrue(trace.first_go)

    def test_ponder_speculation_never_overwrites_confirmed_candidate(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        trace.consume(protocol("fixture-A", "<---", "position startpos").strip())
        trace.consume(protocol("fixture-A", "<---", "go wtime 1803000 btime 1803000 winc 3000 binc 3000").strip())
        trace.consume(protocol("fixture-A", "--->", "bestmove e2e4 ponder e7e5").strip())
        speculative = trace.consume(protocol("fixture-A", "<---", "position startpos moves e2e4 e7e5").strip())
        self.assertFalse(speculative["confirmed"])
        self.assertEqual(trace.moves, [])
        trace.consume(protocol("fixture-A", "<---", "go ponder wtime 1803000 btime 1803000").strip())
        trace.consume(protocol("fixture-B", "<---", "position startpos moves e2e4").strip())
        trace.consume(protocol("fixture-B", "<---", "go wtime 1805000 btime 1803000 winc 3000 binc 3000").strip())
        diagnostic = trace.consume(protocol("fixture-A", "--->", "bestmove g1f3").strip())
        self.assertEqual(diagnostic["kind"], "ponder_bestmove_observed")
        self.assertFalse(diagnostic["confirmed"])
        trace.consume(protocol("fixture-B", "--->", "bestmove e7e5").strip())
        confirmed = trace.consume(protocol("fixture-A", "<---", "position startpos moves e2e4 e7e5").strip())
        self.assertEqual(confirmed["moves"], ["e2e4", "e7e5"])

    def test_ponder_position_after_opponent_go_preserves_actual_history(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        trace.consume(protocol("fixture-A", "<---", "position startpos").strip())
        trace.consume(protocol("fixture-A", "<---", "go wtime 1803000 btime 1803000 winc 3000 binc 3000").strip())
        trace.consume(protocol("fixture-A", "--->", "bestmove e2e4 ponder e7e5").strip())
        trace.consume(protocol("fixture-B", "<---", "position startpos moves e2e4").strip())
        trace.consume(protocol("fixture-B", "<---", "go wtime 1805000 btime 1803000 winc 3000 binc 3000").strip())
        diagnostic = trace.consume(protocol("fixture-A", "<---", "position startpos moves e2e4 e7e5").strip())
        self.assertEqual(diagnostic["kind"], "ponder_position_sent")
        self.assertEqual(trace.moves, ["e2e4"])
        trace.consume(protocol("fixture-A", "<---", "go ponder wtime 1805000 btime 1803000").strip())
        trace.consume(protocol("fixture-A", "--->", "bestmove g1f3").strip())
        trace.consume(protocol("fixture-B", "--->", "bestmove e7e5").strip())
        confirmed = trace.consume(protocol("fixture-A", "<---", "position startpos moves e2e4 e7e5").strip())
        self.assertEqual(confirmed["moves"], ["e2e4", "e7e5"])

    def test_ponderhit_binds_actual_reply_and_marks_clock_gap(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        trace.consume(protocol("fixture-A", "<---", "position startpos").strip())
        trace.consume(protocol("fixture-A", "<---", "go wtime 1803000 btime 1803000 winc 3000 binc 3000").strip())
        trace.consume(protocol("fixture-A", "--->", "bestmove e2e4 ponder e7e5").strip())
        trace.consume(protocol("fixture-B", "<---", "position startpos moves e2e4").strip())
        trace.consume(protocol("fixture-B", "<---", "go wtime 1805000 btime 1803000 winc 3000 binc 3000").strip())
        trace.consume(protocol("fixture-A", "<---", "position startpos moves e2e4 e7e5").strip())
        trace.consume(protocol("fixture-A", "<---", "go ponder wtime 1805000 btime 1803000").strip())
        trace.consume(protocol("fixture-B", "--->", "bestmove e7e5").strip())
        hit = trace.consume(protocol("fixture-A", "<---", "ponderhit").strip())
        self.assertEqual(hit["moves"], ["e2e4", "e7e5"])
        self.assertFalse(trace.clock_tracking_complete)
        trace.consume(protocol("fixture-A", "--->", "bestmove g1f3").strip())
        confirmed = trace.consume(protocol("fixture-B", "<---", "position startpos moves e2e4 e7e5 g1f3").strip())
        self.assertEqual(confirmed["moves"], ["e2e4", "e7e5", "g1f3"])

    def test_ponderhit_different_actual_reply_is_rejected(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        trace.consume(protocol("fixture-A", "<---", "position startpos").strip())
        trace.consume(protocol("fixture-A", "<---", "go wtime 1803000 btime 1803000 winc 3000 binc 3000").strip())
        trace.consume(protocol("fixture-A", "--->", "bestmove e2e4 ponder e7e5").strip())
        trace.consume(protocol("fixture-B", "<---", "position startpos moves e2e4").strip())
        trace.consume(protocol("fixture-B", "<---", "go wtime 1805000 btime 1803000 winc 3000 binc 3000").strip())
        trace.consume(protocol("fixture-A", "<---", "position startpos moves e2e4 e7e5").strip())
        trace.consume(protocol("fixture-A", "<---", "go ponder wtime 1805000 btime 1803000").strip())
        trace.consume(protocol("fixture-B", "--->", "bestmove c7c5").strip())
        with self.assertRaisesRegex(ValueError, "confirmed predicted reply"):
            trace.consume(protocol("fixture-A", "<---", "ponderhit").strip())

    def test_clock_before_position_and_wrong_initial_clock_rejected(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        with self.assertRaises(ValueError):
            trace.consume(protocol("fixture-A", "<---", "go wtime 1803000 btime 1803000 winc 3000 binc 3000").strip())
        trace.consume(protocol("fixture-A", "<---", "position startpos").strip())
        with self.assertRaises(ValueError):
            trace.consume(protocol("fixture-A", "<---", "go wtime 1800000 btime 1803000 winc 3000 binc 3000").strip())

    def test_wrong_side_and_unaccepted_history_rejected(self):
        trace = run.TraceState([], "fixture-A", "fixture-B")
        with self.assertRaises(ValueError):
            trace.consume(protocol("fixture-B", "<---", "position startpos").strip())
        trace = run.TraceState([], "fixture-A", "fixture-B")
        trace.consume(protocol("fixture-A", "<---", "position startpos").strip())
        with self.assertRaises(ValueError):
            trace.consume(protocol("fixture-B", "<---", "position startpos moves e2e4").strip())

    def make_mate(self, root, *, wrong_result=False, bad_clock=False):
        spec = game_spec()
        pgn = root / "game.pgn"
        pgn.write_text('[Event "Unit fixture"]\n[White "fixture-A"]\n[Black "fixture-B"]\n'
                       f'[Result "{"1-0" if wrong_result else "0-1"}"]\n\n'
                       '1. f2f3 e7e5 2. g2g4 d8h4 0-1\n')
        lines = [protocol("fixture-A", "<---", "position startpos moves f2f3 e7e5"),
                 protocol("fixture-A", "<---", f"go wtime {1800000 if bad_clock else 1803000} btime 1803000 winc 3000 binc 3000"),
                 protocol("fixture-A", "--->", "bestmove g2g4"),
                 protocol("fixture-B", "<---", "position startpos moves f2f3 e7e5 g2g4"),
                 protocol("fixture-B", "<---", "go wtime 1805000 btime 1803000 winc 3000 binc 3000"),
                 protocol("fixture-B", "--->", "bestmove d8h4")]
        raw = root / "raw.log"
        raw.write_text("".join(lines))
        return pgn, raw, spec

    def test_pgn_and_actual_trace_must_agree_with_independent_oracle(self):
        with tempfile.TemporaryDirectory() as folder:
            pgn, raw, spec = self.make_mate(Path(folder))
            raw.write_text(protocol("fixture-A", "--->", "option name Ponder type check default true") +
                           protocol("fixture-A", "<---", "setoption name Ponder value false") + raw.read_text())
            result = run.parse_result(pgn, raw, spec)
            self.assertEqual((result["result"], result["plies"]), ("0-1", 4))
            self.assertEqual(result["raw_sha256"], sha(raw.read_bytes()))
            self.assertEqual(result["ponder_uci"]["fixture-A"]["setoption_ponder_false_received"], 1)
            self.assertTrue(result["ponder_uci"]["fixture-A"]["option_advertised_in_trace"])
            self.assertFalse(result["ponder_uci"]["fixture-B"]["option_advertised_in_trace"])
            self.assertIsNone(result["ponder_uci"]["fixture-B"]["actual_off_turn_search"])
            raw.write_text(raw.read_text().replace("bestmove d8h4", "bestmove d8e7"))
            with self.assertRaises(ValueError):
                run.parse_result(pgn, raw, spec)

    def test_late_trace_clock_defect_cannot_be_hidden_by_valid_mate_pgn(self):
        with tempfile.TemporaryDirectory() as folder:
            pgn, raw, spec = self.make_mate(Path(folder), bad_clock=True)
            with self.assertRaises(ValueError):
                run.parse_result(pgn, raw, spec)

    def test_nonterminal_draw_or_wrong_result_cannot_be_scored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pgn, raw, spec = self.make_mate(root, wrong_result=True)
            with self.assertRaises(ValueError):
                run.parse_result(pgn, raw, spec)
            pgn.write_text('[Event "Unit fixture"]\n[White "fixture-A"]\n[Black "fixture-B"]\n'
                           '[Result "1/2-1/2"]\n\n1. f2f3 e7e5 1/2-1/2\n')
            with self.assertRaises(ValueError):
                run.parse_result(pgn, raw, spec)


class DurabilityTests(unittest.TestCase):
    def test_queued_local_bytes_are_not_remote_acknowledgement(self):
        with tempfile.TemporaryDirectory() as folder:
            publisher = MemoryS3Port()
            publisher.gate = threading.Event()
            box = durability.DurableOutbox(Path(folder) / "outbox", publisher)
            ticket = box.submit("fixture/object", b"immutable\n")
            self.assertTrue(publisher.entered.wait(1))
            self.assertFalse(ticket.done.is_set())
            with self.assertRaises(TimeoutError):
                ticket.result(.01)
            publisher.gate.set()
            self.assertEqual(ticket.result(1)["sha256"], sha(b"immutable\n"))
            box.close(1)
            self.assertFalse(box.thread.is_alive())

    def test_lost_ack_preserves_data_and_same_key_can_be_recovered(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            publisher = MemoryS3Port()
            publisher.failure = True
            box = durability.DurableOutbox(root / "first", publisher)
            ticket = box.submit("fixture/object", b"actual bytes")
            with self.assertRaises(RuntimeError):
                ticket.result(1)
            with self.assertRaises(RuntimeError):
                box.close(1)
            self.assertEqual(ticket.path.read_bytes(), b"actual bytes")
            publisher.failure = False
            with durability.DurableOutbox(root / "retry", publisher) as retry:
                self.assertTrue(retry.submit("fixture/object", b"actual bytes").result(1)["verified"])
            self.assertEqual(len(publisher.objects), 1)

    def test_wrong_remote_hash_is_rejected(self):
        class Wrong(MemoryS3Port):
            def publish(self, path, key):
                return {**super().publish(path, key), "sha256": "f" * 64}
        with tempfile.TemporaryDirectory() as folder:
            box = durability.DurableOutbox(Path(folder) / "outbox", Wrong())
            ticket = box.submit("fixture/object", b"data")
            with self.assertRaises(RuntimeError):
                ticket.result(1)
            with self.assertRaises(RuntimeError):
                box.close(1)

    def test_bounded_backlog_blocks_new_work_without_dropping_local_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            publisher = MemoryS3Port()
            publisher.gate = threading.Event()
            box = durability.DurableOutbox(Path(folder) / "outbox", publisher, pending_limit=1)
            box.submit("fixture/1", b"first")
            self.assertTrue(publisher.entered.wait(1))
            box.submit("fixture/2", b"second")
            with self.assertRaises(RuntimeError):
                box.submit("fixture/3", b"third")
            self.assertTrue((box.root / (sha(b"third") + ".chunk")).is_file())
            publisher.gate.set()
            box.close(1)

    def test_timed_shutdown_stops_new_requests_and_settles_inflight_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            publisher = MemoryS3Port()
            publisher.gate = threading.Event()
            publisher.max_publish_seconds = .08
            box = durability.DurableOutbox(Path(folder) / "outbox", publisher)
            first = box.submit("fixture/1", b"inflight")
            self.assertTrue(publisher.entered.wait(1))
            second = box.submit("fixture/2", b"must not publish after timeout")
            release = threading.Timer(.06, publisher.gate.set)
            release.start()
            with self.assertRaises(RuntimeError):
                box.close(.1)
            release.join()
            self.assertFalse(box.thread.is_alive())
            self.assertTrue(first.done.is_set())
            self.assertTrue(second.done.is_set())
            self.assertEqual(publisher.published, ["fixture/1"])


class CollectionTests(unittest.TestCase):
    def test_half_pair_is_preserved_but_not_scored(self):
        with tempfile.TemporaryDirectory() as folder:
            with ledger.Journal(Path(folder) / "campaign.jsonl", "fixture") as journal:
                add_leg(journal, 0)
                partial = collect.collect(journal.rows, "fixture", expected_pairs=["fixture-pair"], profile="test-p4")
                self.assertFalse(partial["selection_ready"])
                self.assertEqual((partial["completed_pair_count"], len(partial["raw_completed_games"])), (0, 1))
                add_leg(journal, 1, result="0-1")
                summary = collect.collect(journal.rows, "fixture", expected_pairs=["fixture-pair"], profile="test-p4")
                self.assertTrue(summary["selection_ready"])
                self.assertEqual((summary["standings"][0]["player"], summary["standings"][0]["points"]), ("fixture-A", 2))

    def test_empty_schedule_and_pending_remote_ack_are_incomplete(self):
        self.assertFalse(collect.collect([], "fixture", expected_pairs=[])["campaign_stage_complete"])
        with tempfile.TemporaryDirectory() as folder:
            with ledger.Journal(Path(folder) / "campaign.jsonl", "fixture") as journal:
                add_leg(journal, 0)
                add_leg(journal, 1, acknowledged=False)
                summary = collect.collect(journal.rows, "fixture", expected_pairs=["fixture-pair"])
                self.assertEqual(summary["completed_pair_count"], 0)
                self.assertEqual(len(summary["incomplete_attempts"]), 1)

    def test_high_selection_uses_only_eligible_families_and_completed_p4(self):
        summary = {"profile": "test-p4", "selection_ready": True,
                   "standings": [{"player": name, "points": 3 - index,
                                  "tied_head_to_head": 0, "sonneborn_berger": 0}
                                 for index, name in enumerate(("A4", "B4", "C4"))]}
        high = [{"id": name + "28", "family": name} for name in ("B", "C", "ice4", "c4ke")]
        selected = collect.select_high(summary, {"A4": "A", "B4": "B", "C4": "C"}, high)
        self.assertEqual(selected["players"], ["B28", "C28", "c4ke28", "ice428"])
        with self.assertRaises(ValueError):
            collect.select_high({**summary, "selection_ready": False}, {}, high)
        with self.assertRaises(ValueError):
            collect.select_high(summary, {}, high + [high[0]])

    def test_p16_broad_selection_keeps_profile_specific_selection_label(self):
        summary = {"profile": "test-p16", "selection_ready": True,
                   "standings": [{"player": "A16", "points": 2, "tied_head_to_head": 0, "sonneborn_berger": 0},
                                 {"player": "B16", "points": 1, "tied_head_to_head": 0, "sonneborn_berger": 0}]}
        selected = collect.select_high(summary, {"A16": "A", "B16": "B"},
                                       [{"id": "A192", "family": "A"}, {"id": "B192", "family": "B"}])
        self.assertEqual(selected["players"], ["A192", "B192"])
        self.assertIn("P16", selected["selection"])
        self.assertIn("P192", selected["selection"])
        with self.assertRaises(ValueError):
            collect.select_high({**summary, "profile": "test-p192"}, {"A16": "A", "B16": "B"}, [])
        with self.assertRaisesRegex(ValueError, "D is outside"):
            collect.select_high(summary, {"A16": "D", "B16": "B"}, [])
        with self.assertRaisesRegex(ValueError, "D is outside"):
            collect.select_high(summary, {"A16": "A", "B16": "B"}, [{"id": "D192", "family": "D"}])

    def test_drawn_broad_uses_family_ids_even_when_artifact_ids_sort_backwards(self):
        families = {"z-A": "A", "m-B": "B", "a-C": "C"}
        pairs = (("z-A", "m-B"), ("z-A", "a-C"), ("m-B", "a-C"))
        with tempfile.TemporaryDirectory() as folder:
            with ledger.Journal(Path(folder) / "campaign.jsonl", "fixture") as journal:
                for index, players in enumerate(pairs):
                    for leg in (0, 1):
                        add_leg(journal, leg, pair=f"tie-{index}", result="1/2-1/2", players=players)
                arguments = dict(expected_pairs=[f"tie-{index}" for index in range(3)], profile="test-p4")
                unbound = collect.collect(journal.rows, "fixture", **arguments)
                bound = collect.collect(journal.rows, "fixture", **arguments, player_families=families)
        self.assertTrue(bound["selection_ready"])
        self.assertEqual({(row["points"], row["tied_head_to_head"], row["sonneborn_berger"])
                          for row in bound["standings"]}, {(2, 2, 4)})
        self.assertEqual([row["player"] for row in unbound["standings"]], ["a-C", "m-B", "z-A"])
        self.assertEqual([row["player"] for row in bound["standings"]], ["z-A", "m-B", "a-C"])
        high = [{"id": family + "28", "family": family} for family in ("C", "B", "A")]
        high += [{"id": "a-ice4", "family": "ice4"}, {"id": "z-c4ke", "family": "c4ke"}]
        selected = collect.select_high(unbound, families, high)
        self.assertEqual(selected["players"], ["A28", "B28", "a-ice4", "z-c4ke"])

    def test_high_selection_requires_unambiguous_family_binding_and_score_precedence(self):
        rows = [{"player": name, "points": 1, "tied_head_to_head": 1, "sonneborn_berger": 1}
                for name in ("z-A", "a-B")]
        summary = {"profile": "test-p4", "selection_ready": True, "standings": rows}
        high = [{"id": family + "28", "family": family} for family in ("A", "B")]
        for families in (None, {}, {"z-A": "A"}, {"z-A": "A", "a-B": "A"},
                         {"z-A": "A", "a-B": "unknown"}):
            with self.assertRaises(ValueError):
                collect.select_high(summary, families, high)
        families = {"z-A": "A", "a-B": "B"}
        for name in ("points", "tied_head_to_head", "sonneborn_berger"):
            ranked = [dict(row) for row in rows]
            ranked[1][name] = 2
            selected = collect.select_high({**summary, "standings": ranked}, families, high)
            self.assertEqual(selected["players"], ["B28", "A28"])

    def test_collection_cli_binds_plan_families_and_preserves_unbound_reporting(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            journal_path = root / "campaign.jsonl"
            with ledger.Journal(journal_path, "fixture") as journal:
                for leg in (0, 1):
                    add_leg(journal, leg, result="1/2-1/2")
            content = {"campaign": "fixture", "profile": "test-p4", "pairs": [{"id": "fixture-pair"}],
                       "registry": {"players": [{"artifact": {"id": "fixture-A", "family": "B"}},
                                                 {"artifact": {"id": "fixture-B", "family": "A"}}]}}
            plan = root / "plan.json"
            plan.write_bytes(ledger.canonical({"format": "rove4k-campaign-plan-v1",
                "content": content, "sha256": ledger.digest(content)}))
            for bound in (False, True):
                out = root / ("bound" if bound else "unbound")
                argv = ["collect", "--journal", str(journal_path), "--campaign", "fixture", "--out", str(out)]
                if bound:
                    argv += ["--plan", str(plan)]
                with patch.object(sys, "argv", argv), patch("sys.stdout"):
                    collect.main()
                summary = json.loads((out / "summary.json").read_bytes())
                self.assertEqual(summary["standings"][0]["player"], "fixture-B" if bound else "fixture-A")
                self.assertEqual(summary["selection_ready"], bound)

    def test_completed_result_waiting_for_ack_is_never_replayed(self):
        with tempfile.TemporaryDirectory() as folder:
            with ledger.Journal(Path(folder) / "campaign.jsonl", "fixture") as journal:
                add_leg(journal, 0, acknowledged=False)
                controller = object.__new__(run.StageController)
                controller.plan = {"pairs": [{"id": "fixture-pair"}]}
                controller.results = ledger.CampaignResults.replay("fixture", journal.rows)
                controller.budget = budget.CampaignBudget("fixture")
                pending = controller.pending()
                self.assertEqual([(row["leg"], row["attempt"]) for row in pending], [(1, 0)])


class RecoveryTests(unittest.TestCase):
    @unittest.skipUnless(Path("/proc/self/stat").is_file(), "Linux original-process identity")
    def test_unstarted_unknown_owner_blocks_resume_without_assigning_numeric_ownership(self):
        row = {"event": "campaign.unsettled_owner", "data": {"launch_id": "fixture-launch", "instance_id": "i-fixture",
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "observation": {"pid": 77777, "pgid": 77777, "session": 77777, "start_ticks": None,
                            "readers_done": False, "remaining_processes": [{"state": "ownership_unverified"}]}}}
        with patch.object(run, "proc_identity", side_effect=AssertionError("unknown identity must not be assigned")):
            with self.assertRaisesRegex(RuntimeError, "unverified launch/output owner"):
                run.require_settled_prior_jobs([row], "i-fixture", budget.CampaignBudget("fixture"))

    @unittest.skipUnless(Path("/proc/self/stat").is_file(), "Linux original-process identity")
    def test_unstarted_known_owner_is_rechecked_and_pid_reuse_is_preserved(self):
        observed = {"pid": 77777, "pgid": 77777, "session": 77777, "start_ticks": 100, "readers_done": True,
                    "remaining_processes": [{"pid": 77777}]}
        row = {"event": "campaign.unsettled_owner", "data": {"launch_id": "fixture-launch", "instance_id": "i-fixture",
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "observation": observed}}
        with patch.object(run, "proc_identity", return_value=observed):
            with self.assertRaises(RuntimeError):
                run.require_settled_prior_jobs([row], "i-fixture", budget.CampaignBudget("fixture"))
        with patch.object(run, "proc_identity", return_value={**observed, "start_ticks": 200}):
            run.require_settled_prior_jobs([row], "i-fixture", budget.CampaignBudget("fixture"))

    def test_verified_orphan_result_blocks_replay_and_preserves_both_evidence_objects(self):
        publisher = MemoryS3Port()
        pgn_key, raw_key = "fixture/games/orphan/pgn", "fixture/games/orphan/raw"
        publisher.objects.update({pgn_key: b"real unit pgn bytes", raw_key: b"real unit raw bytes"})
        result = {"pgn_object_key": pgn_key, "pgn_sha256": sha(publisher.objects[pgn_key]),
                  "raw_object_key": raw_key, "raw_sha256": sha(publisher.objects[raw_key])}
        result_key = f"fixture/results/orphan/attempt-000/{ledger.digest(result)}.json"
        publisher.objects[result_key] = ledger.canonical(result)
        audit = run.audit_remote_results(publisher, "fixture", ledger.CampaignResults("fixture"))
        self.assertEqual(audit["uncertain"][0]["game"], "orphan")
        self.assertEqual(len(audit["uncertain"][0]["evidence"]), 2)
        self.assertEqual(len(publisher.objects), 3)
    def test_overlapping_verified_snapshots_recover_one_exact_hash_chain(self):
        with tempfile.TemporaryDirectory() as folder:
            root, publisher = Path(folder), MemoryS3Port()
            with ledger.Journal(root / "source.jsonl", "fixture") as journal:
                journal.append("campaign.prepared", {"fixture": True})
                journal.append("campaign.observed", {"fixture": True})
                for first, last in ((0, 0), (0, 1), (1, 1)):
                    data = b"".join(ledger.canonical(row) + b"\n" for row in journal.rows[first:last + 1])
                    publisher.objects[f"fixture/journal/{first:09d}-{last:09d}-{sha(data)}.jsonl"] = data
                result = run.restore_remote_journal(publisher, "fixture", root / "recovered")
                self.assertEqual((result["events"], result["last_sha256"]), (2, journal.last))
                self.assertEqual(Path(result["journal"]).read_bytes(), journal.path.read_bytes())

    def test_missing_cloud_prefix_or_conflicting_event_does_not_recover(self):
        with tempfile.TemporaryDirectory() as folder:
            root, publisher = Path(folder), MemoryS3Port()
            with ledger.Journal(root / "source.jsonl", "fixture") as journal:
                journal.append("campaign.prepared")
                second = journal.append("campaign.observed")
                data = ledger.canonical(second) + b"\n"
                publisher.objects[f"fixture/journal/000000001-000000001-{sha(data)}.jsonl"] = data
                with self.assertRaises(ValueError):
                    run.restore_remote_journal(publisher, "fixture", root / "missing")
                changed = {**second, "data": {"changed": True}}
                duplicate = ledger.canonical(changed) + b"\n"
                publisher.objects[f"fixture/journal/000000001-000000001-{sha(duplicate)}.jsonl"] = duplicate
                with self.assertRaises(ValueError):
                    run.restore_remote_journal(publisher, "fixture", root / "conflict")

    @unittest.skipUnless(Path("/proc/self/stat").is_file(), "Linux original-process identity")
    def test_live_original_owner_cannot_be_restarted(self):
        child = subprocess.Popen([sys.executable, "-B", "-c", "import sys; sys.stdin.buffer.read(1)"],
                                 stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        observed = None
        try:
            observed = run.proc_identity(child.pid)
            self.assertIsNotNone(observed)
            self.assertEqual((observed["pid"], observed["pgid"], observed["session"]), (child.pid,) * 3)
            self.assertNotEqual(child.pid, os.getpgrp())
            self.assertIsNone(child.poll())
            rows = [{"event": "game.process", "game": "fixture-game", "attempt": 0,
                     "data": {**observed, "instance_id": "i-fixture",
                              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}}]
            with self.assertRaisesRegex(RuntimeError, "original runner identity exists"):
                run.require_settled_prior_jobs(rows, "i-fixture", budget.CampaignBudget("fixture"))
        finally:
            child.stdin.close()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if observed is None or run.proc_identity(child.pid) != observed:
                    raise RuntimeError("owned fixture child identity changed; refuse an unbound signal")
                child.kill()  # Only this unreaped, identity-checked child; never the test process group.
                child.wait(timeout=5)
        self.assertEqual(child.returncode, 0)

    @unittest.skipUnless(Path("/proc/self/stat").is_file(), "Linux original-process identity")
    def test_reused_numeric_pid_and_groups_are_not_assigned_to_old_owner(self):
        original = {"pid": 77777, "pgid": 77777, "session": 77777, "start_ticks": 100,
                    "instance_id": "i-fixture", "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
        unrelated = {"pid": 77777, "pgid": 77777, "session": 77777, "start_ticks": 200}
        rows = [{"event": "game.process", "game": "fixture-game", "attempt": 0, "data": original}]
        with patch.object(run, "proc_identity", return_value=unrelated):
            run.require_settled_prior_jobs(rows, "i-fixture", budget.CampaignBudget("fixture"))


class PlanAndControllerTests(unittest.TestCase):
    """Actual controller/filesystem path, with explicitly simulated OS/AWS ports."""
    OPENING = "g1f3 g8f6 f3g1 f6g8 f2f3 e7e5 g2g4 b8c6".split()

    def inputs(self, root):
        players = []
        for family in ("A", "B"):
            identity = "fixture-" + family
            data = ("synthetic contract fixture, no executable engine: " + identity).encode()
            path = root / identity
            path.write_bytes(data)
            profile = registry.production.resource_profile("test-p4")
            artifact = registry.Artifact(identity, family, path, "test", "test-p4", 4,
                profile.layout(24).bytes, 24, "source-jit", True, sha(data), len(data), sha(b"native-fixture" + data))
            receipt = {"format": "rove4k-qualification-v1", "complete": True, "failures": [],
                "division": "general4k", "artifact": artifact.identity(),
                "checks": {name: True for name in registry.CHECKS},
                "observations": {"startup_ms": 1, "workers": 4, "positive_cpu_workers": 4,
                    "tt_bytes": artifact.tt_bytes, "runtime_native_sha256": artifact.native_sha256,
                    "physical_cores": 4, "logical_cpus": 4, "temporary_cleanup_while_live": True,
                    "nbrq_replay": True, "nbrq_generation": True}}
            proof = root / (identity + ".json")
            proof.write_bytes(ledger.canonical(receipt))
            players.append({"artifact": {**artifact.identity(), "path": str(path)},
                            "receipt": str(proof), "receipt_sha256": sha(proof.read_bytes())})
        registry_path = root / "registry.json"
        registry_path.write_bytes(ledger.canonical({"format": "rove4k-league-registry-v1", "players": players}))
        binary = root / "runner-fixture"
        binary.write_bytes(b"synthetic build receipt fixture, no actual Fastchess binary")
        build = root / "build-receipt.json"
        build.write_bytes(ledger.canonical({"complete": True, "upstream_commit": fastchess.PIN,
            "patch_sha256": fastchess.sha(fastchess.PATCH.read_bytes()), "binary_sha256": sha(binary.read_bytes()),
            "compiler": "synthetic fixture; no compilation performed",
            "command": {"returncode": 0, "forced_cleanup": False, "leader_reaped": True, "group_absent": True}}))
        opening = {"id": "fixture-opening", "family": " ".join(self.OPENING), "moves": self.OPENING}
        pgn = root / "openings.pgn"
        pgn.write_text('[Event "Synthetic opening fixture"]\n\n' + " ".join(self.OPENING) + " *\n")
        bank = root / "bank.json"
        bank.write_bytes(ledger.canonical({"source": {"revision": "a6189a30dc273ccb21fc2536a9a2fefd5592a67a",
            "verified": True, "license": "CC0-1.0"}, "bank_id": "b" * 64,
            "stages": {"broad": [opening]},
            "files": {"broad": {"path": str(pgn), "bytes": pgn.stat().st_size, "sha256": sha(pgn.read_bytes())}}}))
        cpus = tuple(topology.Cpu(core * 4 + smt, core // 48, core, core // 48, (core * 4, core * 4 + 1))
                     for core in range(96) for smt in (0, 1))
        snapshot = topology.Topology(cpus, tuple(cpu.id for cpu in cpus), (0, 1), {}, "synthetic-kernel-fixture")
        return registry_path, bank, sha(bank.read_bytes()), binary, build, snapshot

    def freeze(self, root):
        reg, bank, bank_sha, binary, build, snapshot = self.inputs(root)
        plan = run.freeze_plan("fixture", "test-p4", reg, bank, bank_sha, binary, build,
                               root / "bundle", snapshot=snapshot)
        return plan, snapshot

    def test_p16_p192_frozen_placement_has_the_requested_controller_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            *_, snapshot = self.inputs(Path(folder))
            p16, reserved = run.league_placement(snapshot, "test-p16")
            p192, shared = run.league_placement(snapshot, "test-p192")
        self.assertEqual(len(p16), 11)
        self.assertTrue(all(slot.workers == 16 and slot.smt and slot.policy == "default" and len(slot.memory_nodes) == 1 for slot in p16))
        self.assertEqual(len({cpu for slot in p16 for cpu in slot.cpus}), 176)
        self.assertTrue(set(reserved).isdisjoint(cpu for slot in p16 for cpu in slot.cpus))
        self.assertEqual(len(reserved), 16)
        self.assertEqual(len(p192), 1)
        self.assertEqual(p192[0].workers, 192)
        self.assertEqual(p192[0].policy, "default")
        self.assertEqual(set(shared), set(snapshot.allowed_cpus))
        self.assertEqual(set(shared), set(p192[0].cpus))

    def test_p16_p192_cgroup_creation_uses_aligned_pair_and_aggregate_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            *_, snapshot = self.inputs(Path(folder))
        class Artifact:
            def __init__(self, identity, tt):
                self.name, self.tt = identity, tt
            def identity(self):
                return {"id": self.name, "sha256": ("a" if self.name == "A" else "b") * 64,
                        "tt_bytes": self.tt}
        class Manager:
            def __init__(self):
                self.calls = []
            def create(self, slot, memory_bytes):
                self.calls.append((slot.id, memory_bytes))
                return {"id": slot.id, "memory_max": memory_bytes}
        evidence = {"host_available_bytes": 600 << 30, "node_available_bytes": {0: 256 << 30, 1: 256 << 30},
                    "per_game_overhead_bytes": (2 << 30) + 1, "overhead_evidence_sha256": "c" * 64,
                    "controller_reserve_bytes": 2 << 30, "page_bytes": 4096}
        for profile, sizes, expected_count in (("test-p16", (12 << 30, 16 << 30), 11),
                                               ("test-p192", (192 << 30, 256 << 30), 1)):
            with self.subTest(profile=profile):
                slots, _ = run.league_placement(snapshot, profile)
                players = [Artifact("A", sizes[0]), Artifact("B", sizes[1])]
                manager = Manager()
                groups, proof = run.create_league_cgroups(manager, slots, players, profile, memory_preflight=evidence)
                expected = sum(sizes) + (2 << 30) + 4096
                self.assertEqual(len(groups), expected_count)
                self.assertEqual(manager.calls, [(slot.id, expected) for slot in slots])
                self.assertFalse(proof["runtime_admission_complete"])
                # Current free memory is telemetry, not an allocation promise
                # or a reason to refuse the requested profile.
                for observations in ({"host_available_bytes": 1 << 30},
                                     {"host_available_bytes": 0, "node_available_bytes": {0: 0, 1: None}},
                                     {"host_available_bytes": None, "node_available_bytes": None}):
                    manager = Manager()
                    measured = {**evidence, **observations}
                    groups, proof = run.create_league_cgroups(manager, slots, players, profile,
                                                              memory_preflight=measured)
                    self.assertEqual(manager.calls, [(slot.id, expected) for slot in slots])
                    self.assertEqual(proof["supplied_host_available_bytes"], measured["host_available_bytes"])
                    self.assertFalse(proof["availability_used_for_admission"])
                    self.assertFalse(proof["physical_capacity_verified"])
                    self.assertFalse(proof["runtime_admission_complete"])
                manager = Manager()
                no_telemetry = {name: value for name, value in evidence.items()
                                if name not in ("host_available_bytes", "node_available_bytes")}
                groups, proof = run.create_league_cgroups(manager, slots, players, profile,
                                                          memory_preflight=no_telemetry)
                self.assertEqual(manager.calls, [(slot.id, expected) for slot in slots])
                self.assertIsNone(proof["supplied_host_available_bytes"])
                self.assertEqual(proof["supplied_node_available_bytes"], {})
                self.assertFalse(proof["physical_capacity_verified"])
                manager = Manager()
                with self.assertRaisesRegex(ValueError, "explicit observed memory"):
                    run.create_league_cgroups(manager, slots, players, profile)
                self.assertEqual(manager.calls, [])
        manager = Manager()
        with self.assertRaisesRegex(ValueError, "unknown TEST profile"):
            run.create_league_cgroups(manager, slots, players, "tcec-provisional")
        self.assertEqual(manager.calls, [])

    def test_capacity_snapshot_is_bound_before_cgroup_calculation(self):
        with tempfile.TemporaryDirectory() as folder:
            *_, snapshot = self.inputs(Path(folder))
        slots, _ = run.league_placement(snapshot, "test-p16")
        overhead = {"per_game_overhead_bytes": 2 << 30, "overhead_evidence_sha256": "c" * 64,
                    "controller_reserve_bytes": 2 << 30}
        records = [slot.to_record() for slot in slots]
        # Synthetic source fixture; False here tests validation, not a claim
        # about actual operating-system observation or score admission.
        capacity = {"format": "rove4k-memory-capacity-observation-v1", "slot_sha256": ledger.digest(records),
                    "test_inputs": False, "runtime_admission_complete": False, "host_available_bytes": 600 << 30,
                    "node_available_bytes": {0: 256 << 30, 1: 256 << 30}, "page_bytes": 4096}
        observe = Mock(return_value=capacity)
        actual, preflight = run.capture_league_preflight(slots, Path("/fixture/cgroup"), overhead, observe)
        self.assertEqual(actual, capacity)
        self.assertEqual(preflight["node_available_bytes"], capacity["node_available_bytes"])
        observe.assert_called_once_with(records, Path("/fixture/cgroup"))
        missing_telemetry = {name: value for name, value in capacity.items()
                             if name not in ("host_available_bytes", "node_available_bytes")}
        _, preflight = run.capture_league_preflight(slots, Path("/fixture/cgroup"), overhead,
                                                   Mock(return_value=missing_telemetry))
        self.assertIsNone(preflight["host_available_bytes"])
        self.assertIsNone(preflight["node_available_bytes"])
        class Artifact:
            def __init__(self, name):
                self.name = name
            def identity(self):
                return {"id": self.name, "sha256": ("a" if self.name == "A" else "b") * 64,
                        "tt_bytes": 12 << 30}
        class Manager:
            def __init__(self):
                self.calls = []
            def create(self, slot, memory_bytes):
                self.calls.append((slot.id, memory_bytes))
                return {"id": slot.id, "memory_max": memory_bytes}
        manager = Manager()
        groups, proof = run.create_league_cgroups(manager, slots, [Artifact("A"), Artifact("B")],
                                                  "test-p16", memory_preflight=preflight)
        self.assertEqual(len(groups), 11)
        self.assertEqual(manager.calls, [(slot.id, 26 << 30) for slot in slots])
        self.assertFalse(proof["runtime_admission_complete"])
        for mutation in ({"slot_sha256": "a" * 64}, {"test_inputs": True}, {"runtime_admission_complete": True}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                run.capture_league_preflight(slots, Path("/fixture/cgroup"), overhead,
                                             Mock(return_value={**capacity, **mutation}))
        def mutate_slots(rows, path):
            rows[0]["memory_nodes"] = (999,)
            return {**capacity, "slot_sha256": ledger.digest(rows)}
        with self.assertRaisesRegex(ValueError, "frozen-slot preflight"):
            run.capture_league_preflight(slots, Path("/fixture/cgroup"), overhead, mutate_slots)
        with self.assertRaisesRegex(ValueError, "overhead evidence"):
            run.capture_league_preflight(slots, Path("/fixture/cgroup"), None, observe)

    def test_broad_and_high_profiles_cannot_be_crossed(self):
        for profile in ("test-p4", "test-p16"):
            self.assertTrue(run.stage_profile_allowed("broad", profile))
            self.assertFalse(run.stage_profile_allowed("high", profile))
        for profile in ("test-p28", "test-p192"):
            self.assertTrue(run.stage_profile_allowed("high", profile))
            self.assertFalse(run.stage_profile_allowed("broad", profile))
        self.assertEqual(run.BROAD_FOR_HIGH["test-p28"], "test-p4")
        self.assertEqual(run.BROAD_FOR_HIGH["test-p192"], "test-p16")
        self.assertFalse(run.stage_profile_allowed("other", "test-p16"))
        self.assertFalse(run.stage_profile_allowed("broad", "tcec-provisional"))

    def test_p16_never_silently_reduces_eleven_game_capacity(self):
        with tempfile.TemporaryDirectory() as folder:
            *_, snapshot = self.inputs(Path(folder))
        missing = snapshot.cpus[0].siblings[1]
        restricted = topology.Topology(snapshot.cpus, tuple(cpu for cpu in snapshot.allowed_cpus if cpu != missing),
                                       snapshot.allowed_nodes, snapshot.distances, snapshot.kernel)
        with self.assertRaisesRegex(ValueError, "eleven complete node-local slots"):
            run.league_placement(restricted, "test-p16")
        with self.assertRaises(ValueError):
            run.league_placement(restricted, "test-p192")

    def test_p16_rejects_bad_smt_observations_before_freezing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            reg, bank, bank_sha, binary, build, snapshot = self.inputs(root)
            # Corrupt one CPU in a scored slot while preserving self-membership.
            chosen = run.league_placement(snapshot, "test-p16")[0][0].cpus[0]
            qualified = run.qualified_players
            for siblings in ((chosen,), (chosen, chosen)):
                with self.subTest(siblings=siblings):
                    changed = list(snapshot.cpus)
                    row = next(cpu for cpu in changed if cpu.id == chosen)
                    changed[changed.index(row)] = topology.Cpu(row.id, row.socket, row.core, row.node, siblings)
                    broken = topology.Topology(tuple(changed), snapshot.allowed_cpus, snapshot.allowed_nodes,
                                               snapshot.distances, snapshot.kernel)
                    out = root / ("broken-" + str(len(siblings)))
                    # The small synthetic players are P4-only; bypass only that
                    # profile selection to exercise the real P16 freeze path.
                    with patch.object(run, "qualified_players", side_effect=lambda source, profile:
                                      qualified(source, "test-p4")):
                        with self.assertRaisesRegex(ValueError, "SMT slots require two mutually observed siblings per core"):
                            run.freeze_plan("fixture", "test-p16", reg, bank, bank_sha, binary, build,
                                            out, snapshot=broken)
                    self.assertFalse(out.exists())

    def test_p16_p192_scored_execution_is_held_before_host_or_cloud_access(self):
        for profile in ("test-p16", "test-p192"):
            controller = object.__new__(run.StageController)
            controller.plan = {"profile": profile}
            with self.subTest(profile=profile), patch.object(topology.Topology, "snapshot", side_effect=AssertionError("host access")):
                with self.assertRaisesRegex(ValueError, "awaits shared-budget"):
                    controller.execute(Path("/not-used"))

    def test_cli_p16_p192_rejects_before_aws_or_journal_access(self):
        for profile in ("test-p16", "test-p192"):
            argv = ["run.py", "run", "--plan", "/fixture/plan.json", "--aws-plan", "/fixture/aws.json",
                    "--journal", "/fixture/journal.jsonl", "--out", "/fixture/out", "--cgroup-root", "/fixture/cg"]
            with self.subTest(profile=profile), patch.object(sys, "argv", argv), \
                    patch.object(run, "load_plan", return_value=({"content": {"profile": profile}}, [])), \
                    patch.object(run, "json_input", side_effect=AssertionError("AWS config read")), \
                    patch.object(ledger, "Journal", side_effect=AssertionError("journal opened")):
                with self.assertRaisesRegex(ValueError, "awaits shared-budget"):
                    run.main()

    def test_preexec_placement_requires_actual_masks_policy_and_original_group(self):
        with tempfile.TemporaryDirectory() as folder:
            *_, snapshot = self.inputs(Path(folder))
        slot = run.league_placement(snapshot, "test-p16")[0][0]
        group = {"path": "/fixture/slot-000", "device": 1, "inode": 2,
                 "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes), "memory_max": 30 << 30}
        receipt = {"pid": 123, "stage": "pre-exec runner; final engine observation is separate",
                   "requested_cpus": list(slot.cpus), "effective_cpus": list(slot.cpus),
                   "requested_nodes": list(slot.memory_nodes), "effective_allowed_nodes": list(slot.memory_nodes),
                   "cgroup": group, "requested_policy": "default", "fallback": None,
                   "observed_policy": {"available": True, "request_applied": True, "mode": 0, "nodes": []}}
        result = run.verify_preexec_placement(receipt, pid=123, slot=slot, cgroup=group)
        self.assertEqual(result["tt_page_placement"], "pending")
        mutations = [{"pid": 124}, {"effective_cpus": []}, {"effective_allowed_nodes": []},
                     {"cgroup": {**group, "inode": 3}}, {"fallback": "retained inherited policy"},
                     {"observed_policy": {"available": False, "request_applied": True}},
                     {"observed_policy": {"available": True, "request_applied": False, "mode": 0}}]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                run.verify_preexec_placement({**receipt, **mutation}, pid=123, slot=slot, cgroup=group)
        with self.assertRaisesRegex(ValueError, "cgroup identity"):
            run.verify_preexec_placement({**receipt, "cgroup": None}, pid=123, slot=slot, cgroup=None)

    def test_ready_event_consumes_actual_preexec_receipt_before_engine_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            *_, snapshot = self.inputs(Path(folder))
        slot = run.league_placement(snapshot, "test-p16")[0][0]
        group = {"path": "/fixture/slot-000", "device": 1, "inode": 2,
                 "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes), "memory_max": 30 << 30}
        receipt = {"pid": 123, "stage": "pre-exec runner; final engine observation is separate",
                   "requested_cpus": list(slot.cpus), "effective_cpus": list(slot.cpus),
                   "requested_nodes": list(slot.memory_nodes), "effective_allowed_nodes": list(slot.memory_nodes),
                   "cgroup": group, "requested_policy": "default", "fallback": None,
                   "observed_policy": {"available": True, "request_applied": True, "mode": 0, "nodes": []}}
        controller = object.__new__(run.StageController)
        controller.plan = {"profile": "test-p16"}
        controller.slots = {slot.id: slot}
        controller.players = {name: type("Player", (), {"native_sha256": "a" * 64})() for name in ("A", "B")}
        controller.job_specs = {"job": {"pair": "pair", "game": "game", "attempt": 0,
            "identity": {"slot": slot.id, "white": "A", "black": "B"},
            "placement_record": Path("/fixture/preexec.json"), "placement_cgroup": group}}
        controller.ready = {}
        controller.append = Mock()
        controller.acknowledge_results = Mock()
        controller.replicate = Mock()
        job = type("Job", (), {"identity": "job"})()
        observed = {"pid": 123, "start_ticks": 10}
        with patch.object(run, "json_input", return_value=(receipt, "b" * 64)), \
                patch.object(run.placement, "observe_game_engines", return_value={"engines": []}) as engines:
            controller.event("ready", job, observed)
        self.assertEqual([call.args[0] for call in controller.append.call_args_list],
                         ["game.placement_preexec", "game.ready"])
        self.assertEqual(controller.ready["job"]["preexec_placement"]["receipt_sha256"], "b" * 64)
        engines.assert_called_once()
        controller.append.reset_mock()
        with patch.object(run, "json_input", return_value=({**receipt, "fallback": "failed"}, "c" * 64)), \
                patch.object(run.placement, "observe_game_engines") as engines:
            with self.assertRaisesRegex(ValueError, "policy was not applied"):
                controller.event("ready", job, observed)
        controller.append.assert_not_called()
        engines.assert_not_called()

    def test_cancelled_gate_records_physical_settlement_without_inventing_authorization(self):
        controller = object.__new__(run.StageController)
        state = type("State", (), {"result": None, "interrupted": None})()
        controller.results = type("Results", (), {"games": {("game", 0): state}})()
        controller.job_specs = {"job": {"pair": "pair", "game": "game", "attempt": 0}}
        controller.instance_id = "i-fixture"
        controller.uncertain_releases = {}
        controller.unsettled = {}
        controller.append = Mock()
        controller.acknowledge_results = Mock()
        controller.replicate = Mock()
        job = type("Job", (), {"identity": "job"})()
        settled = {"pid": 123, "returncode": 1, "readers_done": True, "remaining_processes": [],
                   "gate_cancelled": True, "gate_transport": "not_attempted", "gate_authorized": False,
                   "gate_authorization_unknown": False, "status": "cancelled_before_go"}
        controller.event("cancelled", job, settled)
        self.assertEqual([call.args[0] for call in controller.append.call_args_list],
                         ["game.process_completed", "game.interrupted"])
        self.assertEqual(controller.append.call_args_list[-1].args[1]["reason"], "budget_drain")
        controller.append.reset_mock()
        unresolved = {**settled, "gate_authorization_unknown": True, "status": "cancelled_unreconciled"}
        controller.event("cancelled", job, unresolved)
        self.assertEqual([call.args[0] for call in controller.append.call_args_list],
                         ["game.process_completed", "campaign.release_unreconciled"])
        self.assertIn("job", controller.uncertain_releases)
        with self.assertRaisesRegex(ValueError, "durable owner recovery"):
            run.assert_no_unreconciled_releases([{"event": "campaign.release_unreconciled"}])

        # A planned GO2 receipt may be pending even if no write was attempted;
        # it remains quarantined rather than being treated as a confirmed GO.
        controller.append.reset_mock()
        unresolved_intent = {**settled, "status": "cancelled_unreconciled",
                             "gate_authorized": True, "gate_intent_requested": True,
                             "gate_receipt": "pending", "gate_released": False,
                             "released_monotonic": None}
        controller.event("cancelled", job, unresolved_intent)
        self.assertEqual([call.args[0] for call in controller.append.call_args_list],
                         ["game.process_completed", "campaign.release_unreconciled"])

        # Contradictory no-send and send/receipt evidence must be rejected
        # before journaling anything or changing another owned game's state.
        other_game = type("State", (), {"result": "untouched", "interrupted": None})()
        controller.results.games[("other-game", 0)] = other_game
        for contradiction in ({"gate_released": True}, {"gate_released": 0},
                              {"gate_send_started_monotonic": 1.0}, {"released_monotonic": 1.0},
                              {"gate_receipt": "matched"}, {"gate_receipt_monotonic": 1.0},
                              {"gate_fence_send_time_uncertain": True},
                              {"gate_transport_observation_error": "lost"},
                              {"gate_release_event_error": "lost"},
                              {"gate_receipt_event_error": "lost"}):
            with self.subTest(contradiction=contradiction):
                controller.append.reset_mock()
                controller.uncertain_releases = {"other-job": {"sentinel": True}}
                with self.assertRaisesRegex(ValueError, "bounded gate outcome"):
                    controller.event("cancelled", job, {**settled, **contradiction})
                controller.append.assert_not_called()
                self.assertEqual(controller.uncertain_releases, {"other-job": {"sentinel": True}})
                self.assertEqual(other_game.result, "untouched")

        for contradiction in ({"gate_authorization_requested": True, "gate_authorization_resolved": False},
                              {"gate_authorization_requested": False, "gate_authorization_resolved": True},
                              {"gate_intent_requested": True}, {"gate_authorization_requested": 0},
                              {"gate_authorized": 0}, {"gate_authorization_unknown": 0}):
            with self.subTest(authorization=contradiction):
                controller.append.reset_mock()
                with self.assertRaisesRegex(ValueError, "authorization state differs"):
                    controller.event("cancelled", job, {**settled, **contradiction})
                controller.append.assert_not_called()
        for contradiction in ({"gate_authorized": "yes"}, {"gate_authorization_unknown": 0}):
            with self.subTest(unreconciled_authorization=contradiction):
                controller.append.reset_mock()
                with self.assertRaisesRegex(ValueError, "authorization state differs"):
                    controller.event("cancelled", job, {**unresolved_intent, **contradiction})
                controller.append.assert_not_called()

        for unresolved_transport in ({"gate_transport": "uncertain"},
                                     {"gate_transport": "sent", "gate_transport_observation_error": "lost"},
                                     {"gate_transport": "sent", "gate_authorized": True,
                                      "gate_receipt_required": True, "gate_receipt": "unresolved"},
                                     {"gate_transport": "sent", "gate_authorized": True,
                                      "gate_receipt_required": True, "gate_receipt": "matched",
                                      "gate_receipt_event_error": "lost"},
                                     {"gate_transport": "not_attempted", "gate_authorized": True}):
            controller.append.reset_mock()
            controller.uncertain_releases = {}
            observed = {**settled, **unresolved_transport, "status": "completed", "gate_cancelled": False}
            controller.event("delivery_uncertain", job, observed)
            self.assertEqual([call.args[0] for call in controller.append.call_args_list],
                             ["game.process_completed", "campaign.release_unreconciled"])
            self.assertIn("job", controller.uncertain_releases)

    def test_completed_game_with_ponderhit_clock_gap_is_preserved_unscored(self):
        controller = object.__new__(run.StageController)
        controller.plan = {"campaign": "fixture", "profile": "test-p16"}
        controller.out = Path("/fixture/out")
        state = type("State", (), {"result": None, "interrupted": None})()
        controller.results = type("Results", (), {"games": {("game", 0): state}})()
        controller.job_specs = {"job": {"pair": "pair", "game": "game", "attempt": 0, "identity": {}}}
        controller.instance_id = "i-fixture"
        controller.uncertain_releases = {}
        controller.append = Mock()
        controller.observe_raw = Mock()
        controller.queue_result = Mock()
        controller.acknowledge_results = Mock()
        controller.replicate = Mock()
        job = type("Job", (), {"identity": "job", "out": Path("/fixture/out/game")})()
        observed = {"pid": 123, "returncode": 0, "readers_done": True, "remaining_processes": [],
                    "gate_released": True, "cleanup_forced": False}
        parsed = {"pgn_sha256": "a" * 64, "raw_sha256": "b" * 64,
                  "result": "1-0", "clock_tracking_complete": False}
        with patch.object(run, "parse_result", return_value=parsed):
            controller.event("completed", job, observed)
        events = [call.args[0] for call in controller.append.call_args_list]
        self.assertEqual(events, ["game.process_completed", "campaign.game_evidence_unresolved"])
        self.assertEqual(controller.uncertain_releases["job"]["result"]["result"], "1-0")
        controller.queue_result.assert_not_called()
        with self.assertRaisesRegex(ValueError, "durable owner recovery"):
            run.assert_no_unreconciled_releases([{"event": "campaign.game_evidence_unresolved"}])

    def test_final_wave_observation_detects_uncertainty_even_without_event_callback(self):
        for row in ({"gate_transport": "uncertain"}, {"gate_authorization_unknown": True},
                    {"gate_transport": "sent", "gate_transport_observation_error": "lost"},
                    {"gate_transport": "sent", "gate_release_event_error": "lost"},
                    {"gate_transport": "sent", "gate_receipt_required": True},
                    {"gate_transport": "sent", "gate_receipt_required": True, "gate_receipt": "pending"},
                    {"gate_transport": "sent", "gate_receipt_required": True, "gate_receipt": "unresolved"},
                    {"gate_transport": "sent", "gate_receipt_required": True, "gate_receipt": "matched",
                     "gate_receipt_event_error": "journal failed"},
                    {"gate_transport": "sent", "gate_receipt_required": "invalid", "gate_receipt": "matched"},
                    {"gate_transport": "not_attempted", "gate_authorized": True}):
            with self.subTest(row=row):
                self.assertTrue(run.release_unresolved(row))
        self.assertFalse(run.release_unresolved({"gate_transport": "sent", "gate_authorized": True}))
        self.assertFalse(run.release_unresolved({"gate_transport": "sent", "gate_authorized": True,
                                                 "gate_receipt_required": True, "gate_receipt": "matched"}))
        self.assertFalse(run.release_unresolved({"gate_transport": "not_attempted", "gate_authorized": False}))

    def test_go2_receipt_is_bound_and_replayed_before_resume(self):
        start_job = {"attempt_id": "attempt-00000001", "pair": "pair", "game": "game", "attempt": 0}
        job = type("Job", (), {"identity": "launch-1", "start_job": start_job})()
        encoded = json.dumps({"identity": job.identity, "start_job": start_job},
                             sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
        job_sha = hashlib.sha256(encoded).hexdigest()
        expected = {"event": "GO2_ACCEPTED", "attempt_id": start_job["attempt_id"],
                    "fence_id": "fence-1", "job_sha256": job_sha, "nonce": "a" * 64}
        observation = {"identity": job.identity, "pid": 123, "start_ticks": 7,
                       "ready": {"event": "READY", "job": start_job,
                                 "white_clock_ms": 1803000, "black_clock_ms": 1803000},
                       "gate_authorized": True, "gate_transport": "sent",
                       "gate_receipt_required": True, "gate_receipt": "pending",
                       "gate_send_started_monotonic": 10.0, "released_monotonic": 10.1,
                       "gate_receipt_deadline": 15.0,
                       "gate_receipt_expected": expected, "gate_fence_binding_sha256": job_sha,
                       "gate_fence": {"game_id": job.identity, "fence_id": "fence-1", "job_sha256": job_sha,
                                      "not_before_monotonic": 9.0, "expires_monotonic": 20.0}}
        identity = {"leg": 0, "white": "A", "black": "B", "opening_id": "open",
                    "profile": "test-p16", "artifact_sha256": {"A": "a" * 64, "B": "b" * 64},
                    "opening_sha256": "c" * 64, "bank_id": "d" * 64}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder).resolve() / "events.jsonl"
            with ledger.Journal(path, "fixture") as journal:
                controller = object.__new__(run.StageController)
                controller.plan = {"campaign": "fixture"}
                controller.instance_id = "i-fixture"
                controller.journal = journal
                controller.results = ledger.CampaignResults("fixture")
                controller.budget = budget.CampaignBudget("fixture")
                controller.job_specs = {job.identity: {"pair": "pair", "game": "game", "attempt": 0}}
                controller.ready = {job.identity: {"pid": 123, "start_ticks": 7}}
                controller.acknowledge_results = Mock()
                controller.replicate = Mock()
                controller.append("game.started", identity, pair="pair", game="game", attempt=0)
                with patch.object(run.Path, "read_text", return_value="boot-1"):
                    controller.event("released", job, observation)
                    with self.assertRaisesRegex(ValueError, "unconfirmed GO2 receipt"):
                        run.assert_no_unreconciled_releases(journal.rows)
                    controller.event("gate_received", job, {**observation, "gate_receipt": "matched",
                                                            "gate_receipt_monotonic": 10.2})
                run.assert_no_unreconciled_releases(journal.rows)
                self.assertIn(("game", 0), ledger.CampaignResults.replay("fixture", journal.rows).games)
                receipt = journal.rows[-1]
                self.assertEqual(receipt["event"], "game.gate_received")
                self.assertEqual((receipt["data"]["launch_id"], receipt["data"]["instance_id"],
                                  receipt["data"]["boot_id"]), ("launch-1", "i-fixture", "boot-1"))
                self.assertIn("not coordinator authentication", receipt["data"]["scope"])

                for change in (lambda row: row.update(attempt=1),
                               lambda row: row.update(pair="other"),
                               lambda row: row["data"].update(boot_id="other"),
                               lambda row: row["data"]["observation"]["gate_receipt_expected"].update(nonce="b" * 64),
                               lambda row: row["data"]["observation"]["ready"].update(white_clock_ms=1800000),
                               lambda row: row["data"]["observation"]["gate_fence"].update(expires_monotonic=21.0),
                               lambda row: row["data"]["observation"].update(gate_receipt_monotonic=15.0),
                               lambda row: row["data"]["observation"].update(gate_receipt="unresolved")):
                    mutated = json.loads(json.dumps(journal.rows))
                    change(mutated[-1])
                    with self.subTest(change=change), self.assertRaises(ValueError):
                        run.assert_no_unreconciled_releases(mutated)
                with self.assertRaisesRegex(ValueError, "unmatched GO2 receipt"):
                    run.assert_no_unreconciled_releases([receipt])

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_wave_go2_receipt_journal_with_real_toy_runner(self):
        # This runner exercises the actual local Wave callback path, not an
        # engine search, authenticated coordinator or score qualification.
        toy = r'''import json, os, socket, sys, time
s = socket.socket(fileno=int(os.environ['ROVE_START_FD']))
j = json.loads(os.environ['ROVE_START_JOB'])
s.sendall((json.dumps({'event':'READY','job':j,'white_clock_ms':1803000,'black_clock_ms':1803000})+'\n').encode())
data = b''
while b'\n' not in data:
    part = s.recv(1024)
    if not part: sys.exit(3)
    data += part
kind, attempt, fence, digest, nonce = data.decode().strip().split(' ')
assert kind == 'GO2' and attempt == j['attempt_id']
if sys.argv[1] == 'wrong': nonce = '0' * 64
s.sendall((json.dumps({'event':'GO2_ACCEPTED','attempt_id':attempt,'fence_id':fence,'job_sha256':digest,'nonce':nonce})+'\n').encode())
time.sleep(.1)
'''
        for mode in ("ok", "wrong"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="rove-go2-ledger-") as folder:
                root = Path(folder).resolve()
                script = root / "toy.py"
                script.write_text(toy)
                start_job = {"campaign": "fixture", "pair": "pair", "game": "game", "attempt": 0,
                             "attempt_id": "attempt-00000001"}
                job = wave.WaveJob("launch-1", (sys.executable, str(script), mode), {}, start_job, root / "out")
                identity = {"leg": 0, "white": "A", "black": "B", "opening_id": "open", "slot": "slot-0",
                            "profile": "test-p4", "artifact_sha256": {"A": "a" * 64, "B": "b" * 64},
                            "opening_sha256": "c" * 64, "bank_id": "d" * 64}

                class Mailbox:
                    def can_release(self, job, observation, fence): return True
                    def release_guard(self, job, observation, fence): return nullcontext(True)
                    def request(self, job, observation):
                        binding = json.dumps({"identity": job.identity, "start_job": job.start_job},
                                             sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
                        now = time.monotonic()
                        self.value = wave.AsyncGateDecision(job.identity, True, wave.ReleaseFence(
                            job.identity, "fence-1", hashlib.sha256(binding).hexdigest(), now, now + 3))
                    def poll(self):
                        value, self.value = self.value, None
                        return [value] if value else []

                with ledger.Journal(root / "events.jsonl", "fixture") as journal:
                    controller = object.__new__(run.StageController)
                    controller.plan = {"campaign": "fixture", "profile": "test-p4"}
                    controller.out, controller.instance_id, controller.journal = root, "i-fixture", journal
                    controller.results = ledger.CampaignResults("fixture")
                    controller.budget = budget.CampaignBudget("fixture")
                    controller.job_specs = {job.identity: {"pair": "pair", "game": "game", "attempt": 0,
                                                           "identity": identity}}
                    controller.slots = {"slot-0": type("Slot", (), {"cpus": [0]})()}
                    controller.players = {name: type("Player", (), {"native_sha256": "a" * 64})()
                                          for name in ("A", "B")}
                    controller.ready, controller.unsettled, controller.uncertain_releases = {}, {}, {}
                    controller.observe_raw = Mock()
                    controller.acknowledge_results = Mock()
                    controller.replicate = Mock()
                    controller.queue_result = Mock()
                    owner = controller.prepare_intent_owner()
                    try:
                        with patch.object(run.placement, "observe_game_engines", return_value={"engines": []}):
                            result = wave.WaveExecutor().run_wave([job], 5, async_authorizer=Mailbox(), intent_owner=owner,
                                observe_transport=lambda job, obs: None, on_event=controller.event)[0]
                        if mode == "ok":
                            with self.assertRaisesRegex(ValueError, "durable process settlement"):
                                controller.close_intent_owner(owner, [{**result, "pid": result["pid"] + 1}])
                            process = next(row for row in journal.rows if row["event"] == "game.process")
                            duplicate = json.loads(json.dumps(process))
                            duplicate["data"]["identity"] = "different-launch"
                            journal.rows.append(duplicate)
                            try:
                                with self.assertRaisesRegex(ValueError, "durable process settlement"):
                                    controller.close_intent_owner(owner, [result])
                            finally:
                                journal.rows.pop()
                            controller.close_intent_owner(owner, [result])
                        else:
                            with self.assertRaisesRegex(ValueError, "locally settled"):
                                controller.close_intent_owner(owner, [result])
                    finally:
                        if not owner._closed:
                            owner.close()
                    intents = run.registered_intent_rows(journal.rows, root, "fixture", allow_open=mode != "ok")
                    self.assertEqual(len(intents), 1)
                    self.assertEqual(intents[0]["event"], "game.release_intent")
                    events = [row["event"] for row in journal.rows]
                    self.assertEqual(result["returncode"], 0)
                    self.assertFalse(result["cleanup_forced"])
                    self.assertIn("game.released", events)
                    if mode == "ok":
                        self.assertEqual(result["gate_receipt"], "matched")
                        self.assertIn("game.gate_received", events)
                        self.assertLess(events.index("game.released"), events.index("game.gate_received"))
                        run.assert_no_unreconciled_releases(journal.rows, intents)
                    else:
                        self.assertEqual(result["gate_receipt"], "unresolved")
                        self.assertNotIn("game.gate_received", events)
                        self.assertIn("campaign.release_unreconciled", events)
                        with self.assertRaisesRegex(ValueError, "durable owner recovery"):
                            run.assert_no_unreconciled_releases(journal.rows, intents)

                # Reopen both files, as a restarted process would. A durable
                # intent remains uncertain even if the send/release row was
                # never written; an ACK-less release is also quarantined.
                main_rows = ledger.read_journal(root / "events.jsonl", "fixture")
                intent_rows = run.registered_intent_rows(main_rows, root, "fixture", allow_open=mode != "ok")
                if mode == "ok":
                    release_index = next(i for i, row in enumerate(main_rows) if row["event"] == "game.released")
                    receipt_index = next(i for i, row in enumerate(main_rows) if row["event"] == "game.gate_received")
                    for prefix in (main_rows[:release_index], main_rows[:receipt_index]):
                        with self.assertRaisesRegex(ValueError, "open intent journal"):
                            run.registered_intent_rows(prefix, root, "fixture")
                        with self.assertRaisesRegex(ValueError, "durable owner recovery"):
                            run.assert_no_unreconciled_releases(prefix, intent_rows)
                    closed_index = next(i for i, row in enumerate(main_rows) if row["event"] == "campaign.intent_journal_closed")
                    with self.assertRaisesRegex(ValueError, "open intent journal"):
                        run.registered_intent_rows(main_rows[:closed_index], root, "fixture")
                    late = json.loads(json.dumps(main_rows[receipt_index]))
                    late["seq"] = main_rows[closed_index]["seq"] + 1
                    with self.assertRaisesRegex(ValueError, "evidence after intent journal closure"):
                        run.registered_intent_rows(main_rows + [late], root, "fixture")
                    run.assert_no_unreconciled_releases(main_rows, intent_rows)
                    with self.assertRaisesRegex(ValueError, "durable pre-send intent"):
                        run.assert_no_unreconciled_releases(main_rows, ())
                    forged = json.loads(json.dumps(intent_rows))
                    forged[0]["data"]["intent"]["receipt"]["nonce"] = "b" * 64
                    forged[0]["sha256"] = ledger.digest({key: value for key, value in forged[0].items() if key != "sha256"})
                    corrupted_main = json.loads(json.dumps(main_rows))
                    corrupted_main[release_index]["data"]["gate_intent_sha256"] = forged[0]["sha256"]
                    with self.assertRaisesRegex(ValueError, "durable pre-send intent"):
                        run.assert_no_unreconciled_releases(corrupted_main, forged)

    def test_attempt_identity_is_bounded_and_changes_with_launch(self):
        one = run.attempt_identity("fixture", "pair", "g" * 96, 100000, "launch-1")
        two = run.attempt_identity("fixture", "pair", "g" * 96, 100000, "launch-2")
        self.assertRegex(one, r"^[a-f0-9]{64}$")
        self.assertNotEqual(one, two)

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_script_entrypoint_uses_same_intent_owner_type_as_wave(self):
        # Exercise __main__ loading, not only package imports. A duplicate
        # local `run` module would cause Wave's exact owner check to reject it.
        script = r'''import os, runpy, sys
from pathlib import Path
source, root, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(source.parent if mode == 'script' else source.parents[3]))
sys.argv = [str(source), '--help']
try:
    if mode == 'script': runpy.run_path(str(source), run_name='__main__')
    else: runpy.run_module('engines.experiments.strength.run', run_name='__main__', alter_sys=True)
except SystemExit as error:
    assert error.code == 0
if mode == 'script': import ledger, run, wave
else: from engines.experiments.strength import ledger, run, wave
with ledger.Journal(root/'main.jsonl', 'fixture') as main:
    owner = run.IntentJournalOwner(root/'intent.jsonl', 'fixture', 'i-fixture')
    row = main.append('campaign.intent_journal', {'path':str(owner.path), 'instance_id':owner.instance_id,
        'boot_id':owner.boot_id, 'device':owner.journal.identity[0], 'inode':owner.journal.identity[1]})
    owner.bind_registration(main, row)
    try:
        job = wave.WaveJob('launch-1', ('/bin/false',), {},
            {'campaign':'fixture','pair':'pair','game':'game','attempt':0,'attempt_id':'attempt-00000001'}, root/'out')
        class Mailbox:
            def request(self, job, observation): pass
            def poll(self): return []
        wave.WaveExecutor().run_wave([job], 2, async_authorizer=Mailbox(), intent_owner=owner,
                                     observe_transport=lambda job, obs: None)
    finally:
        owner.close()
'''
        for mode in ("script", "module"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="rove-cli-owner-") as folder:
                result = subprocess.run([sys.executable, "-B", "-c", script, str(Path(run.__file__).resolve()), folder, mode],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(sys.platform == "linux", "Linux process and socket ownership")
    def test_intent_fsync_failure_never_sends_go(self):
        toy = r'''import json, os, socket, sys
s=socket.socket(fileno=int(os.environ['ROVE_START_FD']))
j=json.loads(os.environ['ROVE_START_JOB'])
s.sendall((json.dumps({'event':'READY','job':j,'white_clock_ms':1803000,'black_clock_ms':1803000})+'\n').encode())
data=b''
while b'\n' not in data:
    part=s.recv(1024)
    if not part: sys.exit(2)
    data+=part
if data.startswith(b'GO2 '): open(sys.argv[1], 'w').write('GO')
'''
        with tempfile.TemporaryDirectory(prefix="rove-intent-fsync-") as folder:
            root = Path(folder).resolve()
            script = root / "toy.py"
            script.write_text(toy)
            marker = root / "go-observed"
            start_job = {"campaign": "fixture", "pair": "pair", "game": "game", "attempt": 0,
                         "attempt_id": "attempt-00000001"}
            job = wave.WaveJob("launch-1", (sys.executable, str(script), str(marker)), {}, start_job, root / "out")

            class Mailbox:
                def can_release(self, job, observation, fence): return True
                def release_guard(self, job, observation, fence): return nullcontext(True)
                def request(self, item, observation):
                    binding = json.dumps({"identity": item.identity, "start_job": item.start_job},
                                         sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
                    now = time.monotonic()
                    self.value = wave.AsyncGateDecision(item.identity, True, wave.ReleaseFence(
                        item.identity, "fence-1", hashlib.sha256(binding).hexdigest(), now, now + 3))
                def poll(self):
                    value, self.value = self.value, None
                    return [value] if value else []

            with ledger.Journal(root / "main.jsonl", "fixture") as main:
                owner = run.IntentJournalOwner(root / "intent.jsonl", "fixture", "i-fixture")
                row = main.append("campaign.intent_journal", {"path": str(owner.path), "instance_id": owner.instance_id,
                    "boot_id": owner.boot_id, "device": owner.journal.identity[0], "inode": owner.journal.identity[1]})
                owner.bind_registration(main, row)
                try:
                    with patch.object(owner.journal, "append", side_effect=OSError("fixture fsync failure")):
                        result = wave.WaveExecutor().run_wave([job], 5, async_authorizer=Mailbox(), intent_owner=owner,
                                                              observe_transport=lambda job, obs: None)[0]
                finally:
                    owner.close()
            self.assertFalse(marker.exists())
            self.assertEqual(result["gate_transport"], "not_attempted")
            self.assertEqual(result["status"], "cancelled_unreconciled")
            self.assertTrue(run.release_unresolved(result))

    def test_registered_intent_journal_missing_or_unregistered_is_never_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            path = root / "release-intents.jsonl"
            marker = {"event": "campaign.intent_journal", "data": {"path": str(path)}}
            with self.assertRaisesRegex(ValueError, "registered intent journal missing"):
                run.registered_intent_rows([marker], root, "fixture")
            with ledger.Journal(path, "fixture") as sidecar:
                marker["data"].update(device=sidecar.identity[0], inode=sidecar.identity[1])
            with self.assertRaisesRegex(ValueError, "unregistered intent journal"):
                run.registered_intent_rows([], root, "fixture")
            with self.assertRaisesRegex(ValueError, "open intent journal"):
                run.registered_intent_rows([marker], root, "fixture")
            self.assertEqual(run.registered_intent_rows([marker], root, "fixture", allow_open=True), [])
            replacement = root / "replacement.jsonl"
            replacement.write_bytes(b"")
            os.replace(replacement, path)
            with self.assertRaisesRegex(ValueError, "intent journal identity changed"):
                run.registered_intent_rows([marker], root, "fixture")

    @unittest.skipUnless(sys.platform == "linux", "POSIX journal ownership")
    def test_restart_before_first_intent_record_remains_quarantined(self):
        with tempfile.TemporaryDirectory(prefix="rove-intent-open-") as folder:
            root = Path(folder).resolve()
            with ledger.Journal(root / "events.jsonl", "fixture") as journal:
                controller = object.__new__(run.StageController)
                controller.plan, controller.out, controller.instance_id = {"campaign": "fixture"}, root, "i-fixture"
                controller.journal = journal
                controller.results = ledger.CampaignResults("fixture")
                controller.budget = budget.CampaignBudget("fixture")
                owner = controller.prepare_intent_owner()
                owner.close()  # Simulate losing the controller before it can write a close record.
            rows = ledger.read_journal(root / "events.jsonl", "fixture")
            self.assertEqual([row["event"] for row in rows], ["campaign.intent_journal"])
            with self.assertRaisesRegex(ValueError, "open intent journal"):
                run.registered_intent_rows(rows, root, "fixture")

    def test_unavailable_ponder_setting_does_not_block_local_league_score(self):
        data = {"white": "A", "black": "B", "clock_tracking_complete": True, "ponder_uci": {
            "A": {"tcec_ponder_compliance": None}, "B": {"tcec_ponder_compliance": None}}}
        self.assertIsNone(run.score_evidence_unresolved(data, "test-p4"))
        for profile in ("test-p16", "test-p192"):
            self.assertIsNone(run.score_evidence_unresolved(data, profile))
            self.assertEqual(run.score_evidence_unresolved({**data, "clock_tracking_complete": False}, profile),
                             "clock_continuity_unverified")
            proved = {**data, "ponder_uci": {name: {"tcec_ponder_compliance": True} for name in ("A", "B")}}
            self.assertIsNone(run.score_evidence_unresolved(proved, profile))

    def test_frozen_bundle_is_portable_and_exact_bytes_are_rechecked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, snapshot = self.freeze(root)
            value, players = run.load_plan(root / "bundle/plan.json")
            self.assertEqual(value["sha256"], plan["sha256"])
            self.assertEqual((len(players), len(plan["content"]["slots"])), (2, 22))
            used = {cpu for slot in plan["content"]["slots"] for cpu in slot["cpus"]}
            self.assertFalse(used & set(plan["content"]["controller_cpus"]))
            self.assertEqual(len(plan["content"]["controller_cpus"]), 16)
            (root / "bundle/players/fixture-A").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                run.load_plan(root / "bundle/plan.json")

    def test_rehashed_wrong_clock_or_submission_profile_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, _ = self.freeze(root)
            plan["content"]["clock"]["initial_ms"] = 1800000
            plan["sha256"] = ledger.digest(plan["content"])
            (root / "bundle/plan.json").write_bytes(ledger.canonical(plan))
            with self.assertRaises(ValueError):
                run.load_plan(root / "bundle/plan.json")
            reg, bank, bank_sha, binary, build, snapshot = self.inputs(root)
            with self.assertRaises(ValueError):
                run.freeze_plan("fixture", "tcec-provisional", reg, bank, bank_sha, binary, build,
                                root / "submission", snapshot=snapshot)

    def test_same_whole_source_id_cannot_change_native_cohort_inside_one_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original, _ = self.freeze(root)
            changed = json.loads(ledger.canonical(original))
            row = changed["content"]["registry"]["players"][0]
            old_whole, old_id = row["artifact"]["sha256"], row["artifact"]["id"]
            row["artifact"]["native_sha256"] = "e" * 64
            proof_path = root / "bundle" / row["receipt"]
            proof = json.loads(proof_path.read_bytes())
            proof["artifact"]["native_sha256"] = "e" * 64
            proof["observations"]["runtime_native_sha256"] = "e" * 64
            proof_path.write_bytes(ledger.canonical(proof))
            row["receipt_sha256"] = sha(proof_path.read_bytes())
            changed["sha256"] = ledger.digest(changed["content"])
            plan_path = root / "bundle/plan.json"
            plan_path.write_bytes(ledger.canonical(changed))
            self.assertEqual((row["artifact"]["sha256"], row["artifact"]["id"]), (old_whole, old_id))
            publisher = MemoryS3Port()
            with ledger.Journal(root / "campaign.jsonl", "fixture") as journal:
                journal.append("campaign.stage_started", {"stage": "broad", "plan_sha256": original["sha256"]})
                count, last = len(journal.rows), journal.last
                with self.assertRaisesRegex(ValueError, "stage is already bound"):
                    run.StageController(plan_path, root / "execution", journal, publisher, budget.CampaignBudget("fixture"))
                self.assertEqual((len(journal.rows), journal.last), (count, last))
                self.assertEqual(publisher.published, [])
                self.assertFalse((root / "execution").exists())

    def test_no_qualifications_or_native_fallback_never_create_a_score_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            reg, bank, bank_sha, binary, build, snapshot = self.inputs(root)
            value = json.loads(reg.read_text())
            value["players"][0]["artifact"]["representation"] = "configurable-native"
            reg.write_bytes(ledger.canonical(value))
            with self.assertRaises(ValueError):
                run.freeze_plan("fixture", "test-p4", reg, bank, bank_sha, binary, build,
                                root / "fallback", snapshot=snapshot)
            self.assertFalse((root / "fallback").exists())

    def test_protected_inputs_rejected_before_filesystem_read(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("must not read protected data")):
            for name in (".env", "inventory.json", "credentials.json", "service-account.json"):
                with self.assertRaises(ValueError):
                    run.json_input(Path(tempfile.gettempdir()) / name)

    def test_controller_path_waits_for_both_full_evidence_objects(self):
        self.controller_path(fault=False)

    def test_one_completed_colour_survives_an_interrupted_sibling(self):
        self.controller_path(fault=True)

    def test_failed_spawn_retries_in_a_fresh_durable_launch_directory(self):
        self.controller_path(fault=False, spawn_fault=True)

    def test_ready_engine_death_before_global_go_aborts_every_colour_unscored(self):
        self.controller_path(fault=False, pre_go_exit=True)

    def test_completed_stage_resume_reaudits_actual_result_keys_without_replaying_games(self):
        self.controller_path(fault=False, completed_resume=True)

    def test_initial_identity_failure_retains_unknown_owner_and_blocks_next_wave_and_resume(self):
        self.controller_path(fault=False, unsettled_spawn=True)

    def test_returned_unknown_owner_is_persisted_before_a_failed_raw_callback_can_run(self):
        self.controller_path(fault=False, unsettled_spawn=True, disabled_callbacks=True)

    def controller_path(self, *, fault, spawn_fault=False, pre_go_exit=False, completed_resume=False, unsettled_spawn=False,
                        disabled_callbacks=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, snapshot = self.freeze(root)
            publisher = MemoryS3Port()
            testcase = self
            affinities = [set(snapshot.allowed_cpus)]

            class Groups:
                def __init__(self, group_root, namespace):
                    self.path = group_root / namespace
                def create(self, slot):
                    return {"path": str(self.path / slot.id), "device": 1, "inode": 2,
                            "cpus": list(slot.cpus), "memory_nodes": list(slot.memory_nodes), "memory_max": 4 << 30}
                def parent_record(self):
                    return {"path": str(self.path), "device": 1, "inode": 1}
                def close(self):
                    return []

            class Executor:
                calls = 0
                def run_wave(self, jobs, *, wall_seconds, release_callback, on_event):
                    self.calls += 1
                    attempts = [job.start_job["attempt_id"] for job in jobs]
                    testcase.assertEqual(len(attempts), len(set(attempts)))
                    for job in jobs:
                        data = job.start_job
                        testcase.assertEqual(data["attempt_id"], run.attempt_identity(
                            data["campaign"], data["pair"], data["game"], data["attempt"], job.identity))
                    if (spawn_fault or unsettled_spawn) and self.calls == 1:
                        result = []
                        for job in jobs:
                            job.out.mkdir(parents=True)
                            (job.out / "raw.log").write_bytes(b"failed launch evidence, must be preserved\n")
                            obs = {"identity": job.identity, "gate_released": False, "returncode": None,
                                   "readers_done": True, "remaining_processes": [], "cleanup_forced": False,
                                   "wave_aborted": True, "gate_error": "synthetic Popen failure"}
                            if unsettled_spawn:
                                obs.update(pid=77777, pgid=77777, session=77777, start_ticks=None, readers_done=False,
                                           remaining_processes=[{"pid": 77777, "state": "ownership_unverified"}])
                            if not disabled_callbacks:
                                on_event("aborted", job, obs)
                            result.append(obs)
                        return result
                    observations = []
                    for index, job in enumerate(jobs):
                        job.out.mkdir(parents=True)
                        obs = {"identity": job.identity, "pid": 77777 + index, "pgid": 77777 + index,
                               "session": 77777 + index, "start_ticks": 100, "gate_released": False}
                        on_event("spawned", job, obs)
                        on_event("ready", job, obs)
                        observations.append(obs)
                    try:
                        admission = release_callback()
                    except (ValueError, RuntimeError):
                        for job, obs in zip(jobs, observations):
                            obs.update(returncode=-15, readers_done=True, remaining_processes=[],
                                       cleanup_forced=False, wave_aborted=True)
                            on_event("aborted", job, obs)
                        return observations
                    testcase.assertTrue(admission)
                    for index, (job, obs) in enumerate(zip(jobs, observations)):
                        obs.update(gate_released=True, returncode=0, readers_done=True,
                                   remaining_processes=[], cleanup_forced=False, wave_aborted=False)
                        on_event("released", job, obs)
                        if fault and index == 1:
                            obs.update(returncode=-15, wave_aborted=True)
                            on_event("aborted", job, obs)
                            continue
                        spec = controller.job_specs[job.identity]["identity"]
                        white, black = spec["white"], spec["black"]
                        opening = " ".join(testcase.OPENING)
                        (job.out / "game.pgn").write_text('[Event "Synthetic controller fixture"]\n'
                            f'[White "{white}"]\n[Black "{black}"]\n[Result "0-1"]\n\n'
                            + opening + " a2a3 d8h4 0-1\n")
                        (job.out / "raw.log").write_text("".join([
                            protocol(white, "<---", "position startpos moves " + opening),
                            protocol(white, "<---", "go wtime 1803000 btime 1803000 winc 3000 binc 3000"),
                            protocol(white, "--->", "bestmove a2a3"),
                            protocol(black, "<---", "position startpos moves " + opening + " a2a3"),
                            protocol(black, "<---", "go wtime 1805000 btime 1803000 winc 3000 binc 3000"),
                            protocol(black, "--->", "bestmove d8h4")]))
                        on_event("completed", job, obs)
                    return observations

            with ledger.Journal(root / "campaign.jsonl", "fixture") as journal:
                journal.append("budget.launch_requested", {"launch_token": "fixture-launch-token", "max_hourly_usd": "8"})
                journal.append("budget.instance_bound", {"launch_token": "fixture-launch-token", "instance_id": "i-fixture"})
                state = budget.CampaignBudget.replay("fixture", journal.rows)
                executor = Executor()
                controller = run.StageController(root / "bundle/plan.json", root / "execution", journal, publisher,
                    state, wave_executor=executor, lease_verifier=lambda _: {"verified": True, "instance_id": "i-fixture"})
                probes = []
                def native_probe(pid, hashes, cpus, **kwargs):
                    probes.append(pid)
                    if pre_go_exit and len(probes) > 2:
                        raise ValueError("synthetic original READY engine exited before global admission")
                    return {"engines": [{"pid": pid * 2 + index, "start_ticks": 100, "native_sha256": fingerprint}
                                        for index, fingerprint in enumerate(hashes)]}
                with patch.object(run.topology.Topology, "snapshot", return_value=snapshot), \
                     patch.object(run.placement, "CgroupSlots", Groups), \
                     patch.object(run.placement, "cleanup_owned_groups", side_effect=lambda records, **_: [
                         {"path": row["path"], "already_absent": True} for row in records]), \
                     patch.object(run.placement, "observe_game_engines", side_effect=native_probe), \
                     patch.object(os, "sched_getaffinity", side_effect=lambda _: affinities[0]), \
                     patch.object(os, "sched_setaffinity", side_effect=lambda _, cpus: affinities.__setitem__(0, set(cpus))):
                    if disabled_callbacks:
                        controller.observe_raw = lambda _: self.fail("raw parsing must not precede returned ownership persistence")
                    report = controller.execute(root / "cgroups")
                    if unsettled_spawn:
                        self.assertFalse(report["complete"])
                        self.assertEqual(report["failure"]["type"], "RuntimeError")
                        self.assertTrue(report["cleanup_errors"])
                        self.assertFalse(controller.outbox.thread.is_alive())
                        self.assertTrue(any(row["event"] == "campaign.unsettled_owner" for row in journal.rows))
                        self.assertFalse(any(row["event"] == "game.started" for row in journal.rows))
                        next_controller = run.StageController(root / "bundle/plan.json", root / "execution", journal, publisher,
                            controller.budget, wave_executor=executor,
                            lease_verifier=lambda _: {"verified": True, "instance_id": "i-fixture"})
                        with self.assertRaisesRegex(RuntimeError, "unverified launch/output owner"):
                            next_controller.execute(root / "cgroups", resume=True)
                        self.assertEqual(executor.calls, 1)
                        self.assertEqual(affinities[0], set(snapshot.allowed_cpus))
                        return
                    if spawn_fault:
                        self.assertFalse(report["complete"])
                        failed = list((root / "execution/jobs").glob("*/attempt-000-launch-*/raw.log"))
                        self.assertEqual(len(failed), 2)
                        original = {path: path.read_bytes() for path in failed}
                        controller = run.StageController(root / "bundle/plan.json", root / "execution", journal, publisher,
                            controller.budget, wave_executor=executor,
                            lease_verifier=lambda _: {"verified": True, "instance_id": "i-fixture"})
                        report = controller.execute(root / "cgroups", resume=True)
                        self.assertTrue(all(path.read_bytes() == data for path, data in original.items()))
                        self.assertEqual(len(list((root / "execution/jobs").glob("*/attempt-000-launch-*"))), 4)
                        self.assertTrue(all(row.attempt == 0 for row in controller.results.games.values()))
                    if completed_resume:
                        self.assertTrue(report["complete"], report)
                        controller = run.StageController(root / "bundle/plan.json", root / "execution", journal, publisher,
                            controller.budget, wave_executor=executor,
                            lease_verifier=lambda _: {"verified": True, "instance_id": "i-fixture"})
                        report = controller.execute(root / "cgroups", resume=True)
                        self.assertEqual(executor.calls, 1)
                        self.assertEqual(sum(row["event"] == "game.started" for row in journal.rows), 2)
                self.assertEqual(report["complete"], not fault and not pre_go_exit, report)
                self.assertIsNone(report["failure"], report)
                self.assertFalse(report["cleanup_errors"], report)
                self.assertFalse(controller.outbox.thread.is_alive())
                self.assertEqual(affinities[0], set(snapshot.allowed_cpus))
                states = list(controller.results.games.values())
                self.assertEqual(sum(row.accepted for row in states), 0 if pre_go_exit else (1 if fault else 2))
                actual_audit = run.audit_remote_results(publisher, "fixture", controller.results)
                self.assertEqual(actual_audit["uncertain"], [])
                self.assertEqual(len(actual_audit["known"]), sum(row.accepted for row in states))
                cloud_copy = run.restore_remote_journal(publisher, "fixture", root / "verified-cloud-copy")
                recovered = ledger.CampaignResults.replay("fixture", ledger.read_journal(Path(cloud_copy["journal"]), "fixture"))
                self.assertEqual(sum(row.accepted for row in recovered.games.values()), sum(row.accepted for row in states))
                for row in states:
                    if row.accepted:
                        self.assertEqual(len(row.remote["evidence"]), 2)
                        for kind in ("pgn", "raw"):
                            self.assertEqual(sha(publisher.objects[row.result[kind + "_object_key"]]), row.result[kind + "_sha256"])
                if pre_go_exit:
                    self.assertFalse(any(row["event"] in ("game.result", "budget.pair_started") for row in journal.rows))
                    self.assertEqual(len(probes), 3)
                else:
                    first_result = next(index for index, key in enumerate(publisher.published) if "/results/" in key)
                    previous_journals = [key for key in publisher.published[:first_result] if "/journal/" in key]
                    self.assertTrue(previous_journals)
                    self.assertTrue(any(b'"event":"game.result"' in publisher.objects[key] for key in previous_journals))


if __name__ == "__main__":
    unittest.main()
