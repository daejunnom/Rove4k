"""Controller boundary/fault tests. Synthetic receipts never qualify real engines."""
from __future__ import annotations

import hashlib
import base64
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import budget
import collect
import durability
import fastchess
import ledger
import registry
import run
import topology


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


def game_spec(leg=0, opening=None):
    moves = ["f2f3", "e7e5"] if opening is None else opening
    return {"leg": leg, "white": "fixture-A" if leg == 0 else "fixture-B",
            "black": "fixture-B" if leg == 0 else "fixture-A", "profile": "test-p4",
            "opening_id": "fixture-opening", "opening_moves": moves,
            "opening_sha256": ledger.digest(moves), "bank_id": "b" * 64,
            "artifact_sha256": {"fixture-A": "a" * 64, "fixture-B": "c" * 64}}


def add_leg(journal, leg, *, acknowledged=True, pair="fixture-pair", result="1-0"):
    spec = game_spec(leg)
    keys = {"pair": pair, "game": pair + f"-leg{leg}", "attempt": 0}
    journal.append("game.started", spec, **keys)
    data = {**{name: spec[name] for name in ("white", "black", "profile", "opening_id", "opening_sha256", "bank_id", "artifact_sha256")},
            "result": result, "reason": "completed_chess_result", "pgn_sha256": sha(b"unit-pgn"),
            "raw_sha256": sha(b"unit-raw"), "pgn_object_key": "fixture/games/pgn", "raw_object_key": "fixture/games/raw"}
    journal.append("game.result", data, **keys)
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
            result = run.parse_result(pgn, raw, spec)
            self.assertEqual((result["result"], result["plies"]), ("0-1", 4))
            self.assertEqual(result["raw_sha256"], sha(raw.read_bytes()))
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
                   "standings": [{"player": name} for name in ("A4", "B4", "C4")]}
        high = [{"id": name + "28", "family": name} for name in ("B", "C", "ice4", "c4ke")]
        selected = collect.select_high(summary, {"A4": "A", "B4": "B", "C4": "C"}, high)
        self.assertEqual(selected["players"], ["B28", "C28", "c4ke28", "ice428"])
        with self.assertRaises(ValueError):
            collect.select_high({**summary, "selection_ready": False}, {}, high)
        with self.assertRaises(ValueError):
            collect.select_high(summary, {}, high + [high[0]])

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
        observed = run.proc_identity(os.getpid())
        rows = [{"event": "game.process", "game": "fixture-game", "attempt": 0,
                 "data": {**observed, "instance_id": "i-fixture",
                          "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}}]
        with self.assertRaises(RuntimeError):
            run.require_settled_prior_jobs(rows, "i-fixture", budget.CampaignBudget("fixture"))

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
