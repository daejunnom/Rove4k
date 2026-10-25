#!/usr/bin/env python3
"""Freeze and execute a TEST-only colour-pair league using the pinned runner.

This controller does not create EC2 instances. The AWS lifecycle consumer owns
launch/termination and supplies an already verified live lease and publisher.
Every score-producing CLI path validates the exact artifact qualifications.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import uuid

try:
    from . import budget, collect, durability, fastchess, ledger, placement, registry, topology
except ImportError:
    import budget, collect, durability, fastchess, ledger, placement, registry, topology

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ID = ledger.valid_id
SHA = re.compile(r"^[a-f0-9]{64}$")


def protected_input(path):
    path = Path(path)
    if not path.is_absolute() or path.name == "inventory.json":
        raise ValueError("explicit absolute non-protected campaign input required")
    if any(part.startswith(".env") or part in (".ssh", ".aws", ".npmrc", "id_rsa", "id_ed25519") or
            any(word in part.lower() for word in ("credential", "service-account", "service_account", "api_key", "api-key", "ssh_key"))
            for part in path.parts):
        raise ValueError("protected file is not a campaign input")
    return path


def json_input(path, expected_sha=None):
    path = protected_input(path)
    if path.suffix != ".json":
        raise ValueError("explicit absolute JSON input required")
    if path.is_symlink() or path.stat().st_size > 32 << 20:
        raise ValueError("campaign input must be an ordinary bounded file")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and (not SHA.fullmatch(expected_sha) or actual != expected_sha):
        raise ValueError("input identity differs: " + path.name)
    return json.loads(raw), actual


def external_new(path):
    path = protected_input(path)
    if not path.is_absolute() or path.exists() or any((p / ".git").exists() for p in (path, *path.parents)):
        raise ValueError("new absolute output outside Git required")
    if any(p.is_symlink() for p in path.parents):
        raise ValueError("output must not follow links")
    return path


def bundle_path(root, logical):
    path = Path(logical)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("bundle members must be relative owned paths")
    result = root / path
    if result.is_symlink() or not result.resolve().is_relative_to(root.resolve()):
        raise ValueError("bundle member escaped its owner")
    return result


def runner_identity(binary, receipt):
    binary = protected_input(binary)
    record, receipt_sha = json_input(receipt)
    expected_patch = fastchess.sha(fastchess.PATCH.read_bytes())
    if (record.get("complete") is not True or record.get("upstream_commit") != fastchess.PIN or
            record.get("patch_sha256") != expected_patch or not binary.is_absolute() or binary.is_symlink()):
        raise ValueError("runner is not the reviewed pinned Fastchess build")
    command = record.get("command", {})
    if (command.get("returncode") != 0 or command.get("forced_cleanup") is not False or
            command.get("leader_reaped") is not True or command.get("group_absent") is not True):
        raise ValueError("runner build has no successful physical completion")
    binary_sha = registry.file_sha(binary)
    if record.get("binary_sha256") != binary_sha:
        raise ValueError("runner bytes differ from its actual build receipt")
    return {"sha256": binary_sha, "receipt_sha256": receipt_sha, "patch_sha256": expected_patch,
            "upstream_commit": fastchess.PIN}


def qualified_players(value, profile, *, base=None):
    if value.get("format") != "rove4k-league-registry-v1":
        raise ValueError("explicit qualification registry required")
    accepted, rejected, seen = [], [], set()
    for index, row in enumerate(value.get("players", [])):
        identity = row.get("artifact", {}).get("id", f"registry-row-{index}")
        try:
            raw = dict(row["artifact"])
            proof = Path(row["receipt"])
            if base is not None:
                raw["path"] = bundle_path(base, raw["path"])
                proof = bundle_path(base, row["receipt"])
            raw["path"] = protected_input(raw["path"])
            proof = protected_input(proof)
            artifact = registry.Artifact.from_record(raw)
            if artifact.profile != profile:
                continue
            if artifact.id in seen:
                raise ValueError("duplicate player identity")
            admitted = registry.admit_to_test_league(artifact, proof, row["receipt_sha256"])
            seen.add(artifact.id)
            accepted.append({"artifact": artifact, "receipt": proof, "receipt_sha256": row["receipt_sha256"],
                             "admission": admitted})
        except (KeyError, OSError, ValueError, TypeError) as error:
            rejected.append({"id": identity, "reason": str(error)})
    return accepted, rejected


def validate_bank(path, expected_sha, stage):
    bank, actual_sha = json_input(path, expected_sha)
    source = bank.get("source", {})
    if (source.get("revision") != "a6189a30dc273ccb21fc2536a9a2fefd5592a67a" or
            source.get("verified") is not True or source.get("license") != "CC0-1.0"):
        raise ValueError("league bank must be the verified pinned CC0 source")
    openings = bank.get("stages", {}).get(stage)
    if not openings:
        raise ValueError("the requested stage has no actual legal openings")
    families = []
    for row in openings:
        ID(row["id"])
        moves = row["moves"]
        if len(moves) < 8 or row["family"] != " ".join(moves[:8]):
            raise ValueError("opening family differs from its actual legal prefix")
        # Replaying again at plan time binds actual bank moves, not just a label.
        board = rules_module().Board.from_fen()
        for move in moves:
            board = board.play(move)
        families.append(row["family"])
    if len(families) != len(set(families)):
        raise ValueError("stage reuses an opening family")
    pgndata = bank["files"][stage]
    pgnpath = protected_input(pgndata["path"])
    if registry.file_sha(pgnpath) != pgndata["sha256"] or pgnpath.stat().st_size != pgndata["bytes"]:
        raise ValueError("opening PGN bytes differ from the bank")
    return bank, actual_sha, openings, pgnpath


def freeze_plan(campaign, profile, registry_path, bank_path, bank_sha256, runner_binary,
                runner_receipt, out, *, stage="broad", snapshot=None, selected_ids=None, repeats=1,
                broad_plan=None, broad_journal=None):
    ID(campaign)
    if profile not in ("test-p4", "test-p28") or stage not in ("broad", "high", "update1", "update2"):
        raise ValueError("score plans accept only named TEST profiles/stages")
    if type(repeats) is not int or repeats not in (1, 2):
        raise ValueError("one DRR, or explicitly two update opening pairs, required")
    if stage in ("broad", "high") and repeats != 1:
        raise ValueError("broad/high schedule is one DRR")
    source, source_sha = json_input(registry_path)
    players, rejected = qualified_players(source, profile)
    selection = None
    if stage == "broad" and profile != "test-p4" or stage == "high" and profile != "test-p28":
        raise ValueError("broad/high stages use P4/P28 respectively")
    if stage == "high":
        if broad_plan is None or broad_journal is None or selected_ids is not None:
            raise ValueError("high selection derives from the completed frozen broad stage")
        broad, broad_players = load_plan(broad_plan)
        if broad["content"]["campaign"] != campaign or broad["content"]["stage"] != "broad":
            raise ValueError("broad selection belongs to another campaign/stage")
        broad_rows = ledger.read_journal(broad_journal, campaign)
        summary = collect.collect(broad_rows, campaign,
            expected_pairs=[row["id"] for row in broad["content"]["pairs"]], profile="test-p4")
        selection = collect.select_high(summary,
            {row["artifact"].id: row["artifact"].family for row in broad_players},
            [{"id": row["artifact"].id, "family": row["artifact"].family} for row in players])
        selection.update(broad_plan_sha256=broad["sha256"],
                         broad_journal_last_sha256=broad_rows[-1]["sha256"],
                         summary_sha256=ledger.digest(summary))
        selected_ids = selection["players"]
    if selected_ids is not None:
        if len(selected_ids) != len(set(selected_ids)):
            raise ValueError("duplicate selected player")
        available = {row["artifact"].id for row in players}
        if not set(selected_ids) <= available:
            raise ValueError("a selected player is not qualified at this TEST profile")
        players = [row for row in players if row["artifact"].id in selected_ids]
    players.sort(key=lambda row: row["artifact"].id)
    if len(players) < 2:
        raise ValueError("at least two qualified players are needed; no native fallback")
    if stage in ("broad", "high") and len({row["artifact"].family for row in players}) != len(players):
        raise ValueError("one qualified artifact per family in broad/high")
    if stage.startswith("update") and (selected_ids is None or len(players) != 2):
        raise ValueError("updates require an explicitly selected baseline/candidate pair")
    if stage.startswith("update") and (players[0]["artifact"].family != players[1]["artifact"].family or
            players[0]["artifact"].sha256 == players[1]["artifact"].sha256):
        raise ValueError("an update compares a distinct qualified candidate against its own family baseline")
    runner = runner_identity(runner_binary, runner_receipt)
    bank, bank_sha, openings, pgnpath = validate_bank(bank_path, bank_sha256, stage)
    snapshot = snapshot or topology.Topology.snapshot()
    physical, workers = (4, 4) if profile == "test-p4" else (28, 28)
    slots = topology.plan_slots(snapshot, physical, workers, reserve_physical=8)
    used = {key for slot in slots for key in slot.physical_cores}
    unused = sorted({cpu.physical for cpu in snapshot.cpus} - used)
    controller_cores = set(unused[:8])
    if len(controller_cores) != 8:
        raise ValueError("eight whole physical controller cores were not reserved")
    controller_cpus = sorted(cpu.id for cpu in snapshot.cpus if cpu.physical in controller_cores)
    pairs = []
    for repeat in range(repeats):
        for a, b in itertools.combinations(players, 2):
            index = len(pairs)
            opening_index = index % len(openings)
            opening = openings[opening_index]
            ids = a["artifact"].id, b["artifact"].id
            pair_hash = ledger.digest({"campaign": campaign, "stage": stage, "profile": profile,
                                       "players": ids, "repeat": repeat, "opening": opening["id"]})[:12]
            pair_id = f"{stage}-{profile}-{index:03d}-{pair_hash}"
            pairs.append({"id": pair_id, "players": list(ids), "opening": opening,
                          "opening_index": opening_index + 1, "repeat": repeat})
    if len(pairs) > 128:
        raise ValueError("plan alone exceeds the cumulative campaign pair cap")
    out = external_new(out)
    out.mkdir(parents=True)
    (out / "players").mkdir()
    (out / "proofs").mkdir()
    (out / "runner").mkdir()
    published = []
    for row in players:
        artifact = row["artifact"]
        target = out / "players" / artifact.id
        shutil.copyfile(artifact.path, target)
        target.chmod(0o700)
        artifact.verify_bytes()
        if registry.file_sha(target) != artifact.sha256:
            raise ValueError("copied whole artifact changed")
        receipt_name = f"proofs/{artifact.id}.json"
        shutil.copyfile(row["receipt"], out / receipt_name)
        published.append({"artifact": {**artifact.identity(), "path": "players/" + artifact.id},
                          "receipt": receipt_name, "receipt_sha256": row["receipt_sha256"]})
    shutil.copyfile(runner_binary, out / "runner/fastchess")
    (out / "runner/fastchess").chmod(0o700)
    shutil.copyfile(runner_receipt, out / "runner/build.json")
    shutil.copyfile(pgnpath, out / "openings.pgn")
    shutil.copyfile(bank_path, out / "bank.json")
    body = {"campaign": campaign, "profile": profile, "stage": stage, "pairs": pairs,
            "registry": {"format": "rove4k-league-registry-v1", "players": published},
            "registry_input_sha256": source_sha, "excluded": rejected,
            "bank_id": bank["bank_id"], "bank_sha256": bank_sha, "bank_path": "bank.json", "selection": selection,
            "opening_pgn": "openings.pgn", "opening_pgn_sha256": registry.file_sha(out / "openings.pgn"),
            "runner": {**runner, "path": "runner/fastchess", "receipt": "runner/build.json"},
            "topology": snapshot.to_record(), "slots": [slot.to_record() for slot in slots],
            "controller_cpus": controller_cpus,
            "clock": {"tc": "30:00+3", "initial_ms": 1803000, "increment_ms": 3000, "ponder": False},
            "scope": "qualified TEST artifact cohort; not TCEC W256 strength", "partial_player_set": len(players) < 8}
    plan = {"format": "rove4k-campaign-plan-v1", "sha256": ledger.digest(body), "content": body}
    (out / "plan.json").write_bytes(ledger.canonical(plan) + b"\n")
    return plan


def load_plan(path):
    value, _ = json_input(path)
    if value.get("format") != "rove4k-campaign-plan-v1" or ledger.digest(value.get("content")) != value.get("sha256"):
        raise ValueError("frozen plan content identity changed")
    body = value["content"]
    if body["profile"] not in ("test-p4", "test-p28") or not body["pairs"]:
        raise ValueError("nonempty TEST pair plan required")
    ID(body["campaign"])
    players, rejected = qualified_players(body["registry"], body["profile"], base=Path(path).parent)
    if rejected or len(players) != len(body["registry"]["players"]):
        raise ValueError("frozen player qualifications no longer match")
    runner = body["runner"]
    observed = runner_identity(bundle_path(Path(path).parent, runner["path"]), bundle_path(Path(path).parent, runner["receipt"]))
    if observed != {key: runner[key] for key in observed}:
        raise ValueError("frozen runner provenance changed")
    if registry.file_sha(bundle_path(Path(path).parent, body["opening_pgn"])) != body["opening_pgn_sha256"]:
        raise ValueError("frozen opening bank changed")
    bank, _ = json_input(bundle_path(Path(path).parent, body["bank_path"]), body["bank_sha256"])
    if bank["bank_id"] != body["bank_id"] or bank["files"][body["stage"]]["sha256"] != body["opening_pgn_sha256"]:
        raise ValueError("frozen bank/PGN binding changed")
    cohort = {row["artifact"].id for row in players}
    pair_ids = set()
    for pair in body["pairs"]:
        ID(pair["id"])
        if pair["id"] in pair_ids or len(pair["players"]) != 2 or len(set(pair["players"])) != 2 or not set(pair["players"]) <= cohort:
            raise ValueError("pair identity/cohort changed")
        pair_ids.add(pair["id"])
        index = pair["opening_index"]
        if type(index) is not int or index < 1 or pair["opening"] != bank["stages"][body["stage"]][index - 1]:
            raise ValueError("pair does not use its frozen source-bank opening")
    saved = topology.Topology.from_record(body["topology"])
    physical = 4 if body["profile"] == "test-p4" else 28
    expected_slots = [json.loads(json.dumps(slot.to_record())) for slot in topology.plan_slots(saved, physical, physical, reserve_physical=8)]
    if body["slots"] != expected_slots or body["clock"] != {"tc": "30:00+3", "initial_ms": 1803000, "increment_ms": 3000, "ponder": False}:
        raise ValueError("frozen placement/clock differs from the reviewed TEST contract")
    used = {tuple(key) for slot in expected_slots for key in slot["physical_cores"]}
    controller_cores = set(sorted({cpu.physical for cpu in saved.cpus} - used)[:8])
    if len(controller_cores) != 8 or body["controller_cpus"] != sorted(cpu.id for cpu in saved.cpus if cpu.physical in controller_cores):
        raise ValueError("whole-core controller reserve changed")
    return value, players


def rules_module():
    name = "rove_league_chess_oracle"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "engines/tests/chess_oracle.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


TRACE = re.compile(r"^\[Engine\] \[(?P<time>[^\]]+)\] <[^>]+>\s+(?P<player>[A-Za-z0-9_.-]+) (?P<direction><---|--->) (?P<command>.*)$")


class TraceState:
    """Bind sent position/clock traffic to independently legal full history."""
    def __init__(self, opening, white, black):
        self.opening, self.white, self.black = tuple(opening), white, black
        self.moves = []
        self.board = rules_module().Board.from_fen()
        self.first_go = True
        self.clock = None
        self.candidate = None
        self.position_seen = False
        self.searching_player = None

    def consume(self, line):
        match = TRACE.fullmatch(line)
        if match is None or match["player"] not in (self.white, self.black):
            return None
        command, sent = match["command"], match["direction"] == "<---"
        if sent and command.startswith("position startpos"):
            tokens = command.split()
            if tokens[:2] != ["position", "startpos"] or len(tokens) > 2 and tokens[2] != "moves":
                raise ValueError("runner did not use full standard-start history")
            moves = tokens[3:] if len(tokens) > 2 else []
            if moves[:len(self.opening)] != list(self.opening) or moves[:len(self.moves)] != self.moves:
                raise ValueError("runner opening/history changed or retracted")
            added = moves[len(self.moves):]
            if not self.position_seen:
                if moves != list(self.opening):
                    raise ValueError("first position differs from the whole frozen opening")
            elif added and (len(added) != 1 or self.candidate is None or not self.candidate["legal"] or
                            added[0] != self.candidate["move"]):
                raise ValueError("confirmed history is not the accepted bestmove candidate")
            for move in moves[len(self.moves):]:
                self.board = self.board.play(move)
                self.moves.append(move)
            expected_player = self.white if self.board.turn else self.black
            if match["player"] != expected_player:
                raise ValueError("position was sent to the wrong side")
            self.position_seen = True
            self.candidate = None
            return {"kind": "confirmed_position", "moves": list(self.moves), "raw_time": match["time"],
                    "player": match["player"]}
        if sent and command.startswith("go "):
            if not self.position_seen:
                raise ValueError("GO preceded its full position history")
            tokens = command.split()
            if len(tokens) != 9 or tokens[:1] != ["go"] or tokens[1::2] != ["wtime", "btime", "winc", "binc"]:
                raise ValueError("runner clock syntax changed")
            try:
                values = {tokens[index]: int(tokens[index + 1]) for index in range(1, len(tokens), 2)}
            except (ValueError, IndexError) as error:
                raise ValueError("invalid runner clock") from error
            if (set(values) != {"wtime", "btime", "winc", "binc"} or any(value < 0 for value in values.values()) or
                    values["winc"] != 3000 or values["binc"] != 3000):
                raise ValueError("clock/increment differs from the frozen control")
            if self.first_go and (values["wtime"] != 1803000 or values["btime"] != 1803000):
                raise ValueError("initial clock includes gate waiting or differs from the pinned convention")
            if match["player"] != (self.white if self.board.turn else self.black):
                raise ValueError("GO was sent to the wrong side")
            if self.clock is not None:
                mover = "wtime" if match["player"] == self.black else "btime"
                other = "btime" if mover == "wtime" else "wtime"
                if values[other] != self.clock[other] or values[mover] > self.clock[mover] + 3000:
                    raise ValueError("runner clock changed the waiting side or added excess time")
            self.first_go, self.clock = False, values
            self.searching_player = match["player"]
            return {"kind": "go_clock", "moves": list(self.moves), "clock": values,
                    "raw_time": match["time"], "player": match["player"]}
        if not sent and command.startswith("bestmove "):
            tokens = command.split()
            move = tokens[1] if len(tokens) > 1 else ""
            legal = False
            try:
                self.board.play(move)
                legal = match["player"] == self.searching_player
            except (ValueError, IndexError):
                pass
            self.candidate = {"kind": "bestmove_candidate", "move": move, "legal": legal,
                              "player": match["player"], "raw_time": match["time"]}
            return self.candidate
        return None


def parse_result(path, raw_path, spec):
    text = path.read_text(encoding="utf-8")
    headers = dict(re.findall(r'^\[(\w+) "([^"\r\n]*)"\]$', text, re.MULTILINE))
    if (len(re.findall(r'^\[Event ', text, re.MULTILINE)) != 1 or headers.get("White") != spec["white"] or
            headers.get("Black") != spec["black"] or headers.get("Result") not in ("1-0", "0-1", "1/2-1/2") or
            "FEN" in headers or "SetUp" in headers):
        raise ValueError("completed PGN does not bind this standard-start game")
    body = re.sub(r'^\[.*\]\s*$', '', text, flags=re.MULTILINE)
    body = re.sub(r'\{[^}]*\}', ' ', body, flags=re.DOTALL)
    moves = re.findall(r'(?<![A-Za-z0-9])([a-h][1-8][a-h][1-8][nbrq]?)(?![A-Za-z0-9])', body)
    if moves[:len(spec["opening_moves"])] != spec["opening_moves"]:
        raise ValueError("PGN does not preserve the entire frozen opening prefix")
    board = rules_module().Board.from_fen()
    seen = Counter({board.repetition_key(): 1})
    for move in moves:
        board = board.play(move)
        seen[board.repetition_key()] += 1
    legal = list(board.legal_moves())
    terminal = None
    if not legal:
        terminal = ("0-1" if board.turn else "1-0") if board.in_check() else "1/2-1/2"
    pieces = [(index, piece.lower()) for index, piece in enumerate(board.cells) if piece not in ".Kk"]
    dead = (not any(piece in "pqr" for _, piece in pieces) and
            (len(pieces) <= 1 or all(piece == "b" for _, piece in pieces) and
             len({(index // 8 + index % 8) % 2 for index, _ in pieces}) == 1))
    if terminal is None and (dead or seen[board.repetition_key()] >= 3 or board.halfmove >= 100):
        terminal = "1/2-1/2"
    result, reason = headers["Result"], "completed_chess_result"
    if terminal is not None and result != terminal:
        raise ValueError("PGN result contradicts the independent chess oracle")
    if terminal is None:
        explanation = (headers.get("Termination", "") + " " + text[-1024:]).lower()
        if "illegal" in explanation:
            reason = "engine_illegal"
        elif any(word in explanation for word in ("time forfeit", "loses on time", "time loss", "timeout")):
            reason = "engine_time_loss"
        elif any(word in explanation for word in ("disconnect", "crash", "stalled")):
            reason = "engine_crash"
        elif "resign" not in explanation:
            raise ValueError("nonterminal PGN has no recognized actual engine outcome")
        if result == "1/2-1/2":
            raise ValueError("nonterminal draw is not a supported score adjudication")
    trace = TraceState(spec["opening_moves"], spec["white"], spec["black"])
    if raw_path.is_symlink() or raw_path.stat().st_size > 128 << 20:
        raise ValueError("raw game evidence exceeds its owned finite extent")
    with raw_path.open(encoding="utf-8", errors="replace") as source:
        for line in source:
            if len(line) > 64 << 10 or not line.endswith("\n"):
                raise ValueError("raw game has an excessive or incomplete protocol line")
            trace.consume(line.rstrip("\r\n"))
    if trace.first_go:
        raise ValueError("completed game has no actual fixed-clock GO evidence")
    final = trace.moves + ([trace.candidate["move"]] if trace.candidate and trace.candidate["legal"] else [])
    if moves != trace.moves and moves != final:
        raise ValueError("PGN history differs from actual runner-confirmed UCI history")
    return {"result": result, "reason": reason, "moves": moves, "plies": len(moves),
            "pgn_sha256": registry.file_sha(path), "raw_sha256": registry.file_sha(raw_path),
            "white": spec["white"], "black": spec["black"], "opening_id": spec["opening_id"],
            "opening_sha256": spec["opening_sha256"], "bank_id": spec["bank_id"],
            "profile": spec["profile"], "artifact_sha256": spec["artifact_sha256"]}


def proc_identity(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    parts = raw[raw.rfind(")") + 2:].split()
    return {"pid": pid, "pgid": int(parts[2]), "session": int(parts[3]), "start_ticks": int(parts[19])}


def require_settled_prior_jobs(rows, instance_id, campaign_budget):
    """An elapsed wait or a different controller host is not process death."""
    starts, settled, unsettled = {}, set(), {}
    for row in rows:
        key = row.get("game"), row.get("attempt")
        if row["event"] == "game.process":
            starts[key] = row["data"]
        elif row["event"] == "game.process_completed":
            data = row["data"]
            if data.get("readers_done") is True and data.get("remaining_processes") == [] and type(data.get("returncode")) is int:
                settled.add(key)
        elif row["event"] == "campaign.unsettled_owner":
            unsettled[row["data"]["launch_id"]] = row["data"]
    current_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    for launch, data in unsettled.items():
        owned = data["observation"]
        if data.get("instance_id") != instance_id:
            prior = [item for item in campaign_budget.instances if item.instance_id == data.get("instance_id")]
            if len(prior) != 1 or prior[0].active:
                raise RuntimeError("unsettled launch's prior host lacks authoritative termination")
            continue
        if not isinstance(data.get("boot_id"), str) or not re.fullmatch(r"[a-f0-9-]{36}", data["boot_id"]):
            raise ValueError("unsettled launch lacks its original boot identity")
        if data.get("boot_id") != current_boot:
            continue
        if (any(type(owned.get(name)) is not int or owned[name] <= 0 for name in
                ("pid", "pgid", "session", "start_ticks")) or owned.get("readers_done") is not True):
            raise RuntimeError("unverified launch/output owner remains unsettled on this boot; no new wave or resume")
        starts["launch:" + launch, None] = {**owned, "instance_id": instance_id, "boot_id": current_boot}
    for key, owned in starts.items():
        if key in settled:
            continue
        if owned.get("instance_id") != instance_id:
            prior = [item for item in campaign_budget.instances if item.instance_id == owned.get("instance_id")]
            if len(prior) != 1 or prior[0].active:
                raise RuntimeError("prior host has no authoritative termination observation")
            continue
        if not isinstance(owned.get("boot_id"), str) or not re.fullmatch(r"[a-f0-9-]{36}", owned["boot_id"]):
            raise ValueError("prior runner lacks its original boot identity")
        if owned.get("boot_id") != current_boot:
            continue  # Same verified EC2 lease, new kernel boot: old tasks cannot survive.
        leader = proc_identity(owned["pid"])
        if (owned["pid"], owned["pgid"], owned["session"]) != (owned["pid"],) * 3:
            raise ValueError("prior runner was not the recorded dedicated process-group/session leader")
        if leader is not None:
            if leader["start_ticks"] == owned["start_ticks"]:
                raise RuntimeError("original runner identity exists; settle its owner before resume")
            # Linux retains the dedicated leader's PID allocation while a
            # process-group/session still references it. A reused leader PID
            # has a new allocation; its groups belong to another owner.
            continue
        for path in Path("/proc").iterdir():
            if path.name.isdigit():
                observed = proc_identity(int(path.name))
                if observed and (observed["pgid"] == owned["pgid"] or observed["session"] == owned["session"]):
                    reallocated = proc_identity(owned["pid"])
                    if reallocated is not None and reallocated["start_ticks"] != owned["start_ticks"]:
                        break
                    raise RuntimeError("prior runner process group/session is still present")


class StageController:
    """One frozen stage; AWS lifecycle remains a separate verified owner."""
    def __init__(self, plan_path, out, journal, publisher, campaign_budget, *, wave_executor=None, lease_verifier=None):
        self.plan_path = Path(plan_path)
        self.envelope, players = load_plan(self.plan_path)
        self.plan = self.envelope["content"]
        assert_stage_binding(self.envelope, journal.rows)
        self.bundle = self.plan_path.parent
        self.players = {row["artifact"].id: row["artifact"] for row in players}
        self.out = Path(out)
        self.journal = journal
        self.publisher = publisher
        self.budget = campaign_budget
        self.results = ledger.CampaignResults.replay(self.plan["campaign"], journal.rows)
        if self.budget.campaign != self.plan["campaign"] or len(self.budget.active_instances) != 1 or not self.budget.active_instances[0].instance_id:
            raise ValueError("one verified, bound live campaign lease is required")
        self.instance_id = self.budget.active_instances[0].instance_id
        if wave_executor is None:
            try:
                from .wave import WaveExecutor
            except ImportError:
                from wave import WaveExecutor
            wave_executor = WaveExecutor()
        self.executor = wave_executor
        self.lease_verifier = lease_verifier
        self.pending_results = {}
        self.tail = {}
        self.job_specs = {}
        self.enqueued = len(journal.rows)
        self.last_replication = 0.0
        self.replication_tickets = []
        self.outbox = None
        self.slots = {}
        self.ready = {}
        self.unsettled = {}

    def record_unsettled(self, job, observation):
        if job.identity in self.unsettled:
            return
        spec = self.job_specs[job.identity]
        data = {"launch_id": job.identity, "game": spec["game"], "attempt": spec["attempt"],
                "instance_id": self.instance_id, "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "observation": observation}
        self.append("campaign.unsettled_owner", data)
        self.unsettled[job.identity] = data

    def append(self, event, data=None, *, pair=None, game=None, attempt=None):
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        preview = {"event": event, "data": {} if data is None else data,
                   "campaign": self.plan["campaign"], "pair": pair, "game": game, "attempt": attempt}
        results = self.results
        if event in ("game.started", "game.result", "game.remote_confirmed", "game.interrupted"):
            results = ledger.CampaignResults(results.campaign, dict(results.games))
            if (game, attempt) in results.games:
                results.games[game, attempt] = copy.copy(results.games[game, attempt])
        results.apply(preview)
        next_budget = self.budget.apply(event, preview["data"], timestamp)
        row = self.journal.append(event, data, pair=pair, game=game, attempt=attempt, time_utc=timestamp)
        self.results, self.budget = results, next_budget
        return row

    def replicate(self, *, force=False):
        self.outbox.check()
        now = time.monotonic()
        if not force and now - self.last_replication < 1:
            return
        rows = self.journal.rows[self.enqueued:]
        while rows:
            block, size = [], 0
            for row in rows:
                encoded = ledger.canonical(row) + b"\n"
                if block and size + len(encoded) > 4 << 20:
                    break
                block.append((row, encoded))
                size += len(encoded)
            data = b"".join(encoded for _, encoded in block)
            sha = hashlib.sha256(data).hexdigest()
            key = f"{self.plan['campaign']}/journal/{block[0][0]['seq']:09d}-{block[-1][0]['seq']:09d}-{sha}.jsonl"
            self.replication_tickets.append(self.outbox.submit(key, data))
            self.enqueued += len(block)
            rows = rows[len(block):]
        self.last_replication = now

    def queue_result(self, game, attempt, data):
        # FIFO publication makes the immutable start/READY/result journal
        # prefix durable before a result object can become visible remotely.
        self.replicate(force=True)
        required = []
        for kind, filename in (("pgn", "game.pgn"), ("raw", "raw.log")):
            key_name = kind + "_object_key"
            key = data[key_name]
            path = bundle_path(self.out, data["evidence_directory"]) / filename
            if path.is_file():
                body = path.read_bytes()
            elif hasattr(self.publisher, "read_verified"):
                body = self.publisher.read_verified(key, expected_sha=data[kind + "_sha256"], max_bytes=128 << 20)
            else:
                raise RuntimeError("completed evidence is missing; do not replay or fabricate its game")
            if hashlib.sha256(body).hexdigest() != data[kind + "_sha256"]:
                raise ValueError("completed evidence bytes changed")
            required.append(self.outbox.submit(key, body))
        raw = ledger.canonical(data)
        sha = hashlib.sha256(raw).hexdigest()
        key = f"{self.plan['campaign']}/results/{game}/attempt-{attempt:03d}/{sha}.json"
        self.pending_results[game, attempt] = {"result": self.outbox.submit(key, raw), "required": required}

    def acknowledge_results(self, *, wait=False):
        for key, tickets in list(self.pending_results.items()):
            ticket = tickets["result"]
            if not wait and not all(item.done.is_set() for item in (*tickets["required"], ticket)):
                continue
            evidence = [item.result(timeout=125 if wait else 0) for item in tickets["required"]]
            acknowledgement = ticket.result(timeout=125 if wait else 0)
            acknowledgement["evidence"] = evidence
            state = self.results.games[key]
            self.append("game.remote_confirmed", acknowledgement, pair=state.pair, game=state.game, attempt=state.attempt)
            del self.pending_results[key]
        for pair in self.results.pairs():
            if pair["pair"] not in self.budget.completed_pairs:
                self.append("budget.pair_completed", {"pair_id": pair["pair"]})

    def observe_raw(self, job):
        state = self.tail[job.identity]
        path = job.out / "raw.log"
        if not path.exists():
            return
        if path.is_symlink() or path.stat().st_size < state["offset"]:
            raise ValueError("owned raw trace was replaced or truncated")
        with path.open("rb") as stream:
            stream.seek(state["offset"])
            data = stream.read(128 << 10)
        if not data:
            return
        spec = self.job_specs[job.identity]
        import base64
        started = (spec["game"], spec["attempt"]) in self.results.games
        self.append("game.raw_chunk" if started else "campaign.launch_raw_chunk", {"launch_id": job.identity,
                    "offset": state["offset"], "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "base64": base64.b64encode(data).decode()},
                    pair=spec["pair"], game=spec["game"], attempt=spec["attempt"])
        state["offset"] += len(data)
        if not started:
            return
        text = state["partial"] + data.decode("utf-8", "replace")
        lines = text.split("\n")
        state["partial"] = lines.pop()
        if len(state["partial"]) > 64 << 10:
            raise ValueError("raw protocol line exceeds the admitted input extent")
        for line in lines:
            observed = state["trace"].consume(line.rstrip("\r"))
            if observed is not None:
                self.append("game." + observed["kind"], observed, pair=spec["pair"], game=spec["game"], attempt=spec["attempt"])

    def event(self, event, job, observation):
        spec = self.job_specs[job.identity]
        keys = {name: spec[name] for name in ("pair", "game", "attempt")}
        if event == "spawned":
            self.append("game.started", spec["identity"], **keys)
            self.append("game.process", {**observation, "instance_id": self.instance_id,
                        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}, **keys)
        elif event in ("ready", "released"):
            if event == "ready":
                slot = self.slots[spec["identity"]["slot"]]
                observation = {**observation, "engines": placement.observe_game_engines(
                    observation["pid"], [self.players[name].native_sha256 for name in
                    (spec["identity"]["white"], spec["identity"]["black"])], slot.cpus,
                    expected_start_ticks=observation["start_ticks"])}
                self.ready[job.identity] = observation
            self.append("game." + event, observation, **keys)
        elif event == "tick":
            self.observe_raw(job)
        elif event in ("completed", "aborted"):
            # The WaveExecutor only reports completed after group and readers
            # are physically settled. Earlier completed colours survive a later abort.
            state = self.results.games.get((spec["game"], spec["attempt"]))
            if state is None:
                self.append("campaign.game_not_started", {"runner_observation": observation}, **keys)
                if not physically_settled(observation):
                    self.record_unsettled(job, observation)
                return
            self.append("game.process_completed", observation, **keys)
            self.observe_raw(job)
            if (event == "completed" and observation.get("gate_released") is True and
                    observation.get("returncode") == 0 and observation.get("cleanup_forced") is False and
                    observation.get("remaining_processes") == [] and observation.get("readers_done") is True):
                try:
                    data = parse_result(job.out / "game.pgn", job.out / "raw.log", spec["identity"])
                except (OSError, ValueError) as error:
                    self.append("game.interrupted", {"reason": "protocol_harness_error", "error": str(error)}, **keys)
                else:
                    prefix = f"{self.plan['campaign']}/games/{spec['game']}/attempt-{spec['attempt']:03d}"
                    data["pgn_object_key"] = f"{prefix}/pgn-{data['pgn_sha256']}.pgn"
                    data["raw_object_key"] = f"{prefix}/raw-{data['raw_sha256']}.log"
                    data["evidence_directory"] = str(job.out.relative_to(self.out))
                    self.append("game.result", data, **keys)
                    self.queue_result(spec["game"], spec["attempt"], data)
            elif state.result is None and state.interrupted is None:
                reason = "budget_termination" if time.time() >= self.budget.deadline(time.time()) else "protocol_harness_error"
                self.append("game.interrupted", {"reason": reason, "runner_observation": observation}, **keys)
        self.acknowledge_results()
        self.replicate()

    def pending(self):
        jobs = []
        for pair in self.plan["pairs"]:
            for leg in (0, 1):
                game = pair["id"] + f"-leg{leg}"
                states = [state for (name, _), state in self.results.games.items() if name == game]
                if any(state.accepted or state.result is not None for state in states):
                    continue
                if states and any(state.interrupted is None for state in states):
                    raise ValueError("an earlier game attempt is not settled/interrupted")
                attempt = max((state.attempt for state in states), default=-1) + 1
                jobs.append({"pair": pair, "leg": leg, "game": game, "attempt": attempt})
        jobs.sort(key=lambda row: (row["pair"]["id"] not in self.budget.started_pairs,
                                  self.plan["pairs"].index(row["pair"]), row["leg"]))
        return jobs

    def execute(self, cgroup_root, *, resume=False):
        assert_stage_binding(self.envelope, self.journal.rows)
        current = topology.Topology.snapshot()
        saved = topology.Topology.from_record(self.plan["topology"])
        if current.to_record() != saved.to_record():
            raise ValueError("host topology/effective masks changed; freeze a new plan")
        if not self.out.is_absolute() or any((p / ".git").exists() for p in (self.out, *self.out.parents)):
            raise ValueError("external stage execution directory required")
        marker = self.out / "execution.json"
        if self.out.exists():
            if not resume or not marker.is_file() or json.loads(marker.read_text()) != {
                    "campaign": self.plan["campaign"], "plan_sha256": self.envelope["sha256"]}:
                raise ValueError("existing stage output is not this resumable execution")
        else:
            self.out.mkdir(parents=True)
            marker.write_bytes(ledger.canonical({"campaign": self.plan["campaign"], "plan_sha256": self.envelope["sha256"]}))
        require_settled_prior_jobs(self.journal.rows, self.instance_id, self.budget)
        prior_groups = []
        current_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        for row in self.journal.rows:
            if (row["event"] == "campaign.cgroups" and row["data"].get("root") == str(cgroup_root)
                    and row["data"].get("instance_id") == self.instance_id and row["data"].get("boot_id") == current_boot):
                prior_groups.extend(row["data"].get("groups", {}).values())
                if row["data"].get("parent"):
                    prior_groups.append(row["data"]["parent"])
        if prior_groups:
            prior_cleanup = placement.cleanup_owned_groups(prior_groups, root=cgroup_root)
            self.append("campaign.prior_cgroup_cleanup", {"outcomes": prior_cleanup})
            if any(row.get("error") for row in prior_cleanup):
                raise RuntimeError("original owned cgroups are not safely settled; preserve them for audit")
        for state in self.results.games.values():
            if state.result is None and state.interrupted is None:
                self.append("game.interrupted", {"reason": "controller_failure", "evidence": "original group/session settled before resume"},
                            pair=state.pair, game=state.game, attempt=state.attempt)
        execution = sum(row["event"] == "campaign.stage_started" and row["data"].get("plan_sha256") == self.envelope["sha256"]
                        for row in self.journal.rows)
        launch = uuid.uuid4().hex[:16]
        self.append("campaign.stage_started", {"plan_sha256": self.envelope["sha256"], "stage": self.plan["stage"], "execution": execution,
                                              "launch_id": launch})
        original = set(os.sched_getaffinity(0))
        manager = None
        cleanup = []
        failure = None
        try:
            remote_audit = audit_remote_results(self.publisher, self.plan["campaign"], self.results)
            (self.out / f"remote-audit-{launch}.json").write_bytes(ledger.canonical(remote_audit))
            self.append("campaign.remote_result_audit", remote_audit)
            if remote_audit["uncertain"]:
                raise ValueError("uncertain remote completed result; preserve its evidence and do not replay its colour")
            namespace = self.plan["campaign"][:40] + "-" + self.plan["stage"] + "-" + ledger.digest({"plan": self.envelope["sha256"], "execution": execution, "launch": launch})[:12]
            self.append("campaign.cgroup_intent", {"root": str(cgroup_root), "namespace": namespace})
            manager = placement.CgroupSlots(cgroup_root, namespace)
            slots, groups = [], {}
            for row in self.plan["slots"]:
                slot = topology.Slot(**{**row, "cpus": tuple(row["cpus"]),
                                       "physical_cores": tuple(tuple(key) for key in row["physical_cores"]),
                                       "memory_nodes": tuple(row["memory_nodes"])})
                groups[slot.id] = manager.create(slot)
                slots.append(slot)
            self.slots = {slot.id: slot for slot in slots}
            self.append("campaign.cgroups", {"root": str(cgroup_root), "namespace": namespace, "groups": groups,
                                             "parent": manager.parent_record(), "instance_id": self.instance_id,
                                             "boot_id": current_boot})
            os.sched_setaffinity(0, set(self.plan["controller_cpus"]))
            if set(os.sched_getaffinity(0)) != set(self.plan["controller_cpus"]):
                raise ValueError("controller reserve affinity was not applied")
            # Publisher and reader threads start after this one-time pin so
            # they inherit reserved cores, not scored engine cores.
            self.outbox = durability.DurableOutbox(self.out / f"outbox-{execution:03d}-{launch}", self.publisher)
            plan_ticket = self.outbox.submit(f"{self.plan['campaign']}/plans/{self.envelope['sha256']}.json",
                                              ledger.canonical(self.envelope))
            plan_ticket.result(timeout=125)
            self.enqueued = 0  # Republish complete hash-chain history on first stage/resume.
            self.replicate(force=True)
            for state in list(self.results.games.values()):
                if state.result is not None and state.remote is None and state.interrupted is None:
                    self.queue_result(state.game, state.attempt, state.result)
            self.acknowledge_results(wait=True)
            wave_number = 0
            while self.pending():
                if self.lease_verifier is None:
                    raise ValueError("scored execution requires a fresh actual AWS owned-lease verification port")
                lease = self.lease_verifier(self.budget)
                if not isinstance(lease, dict) or lease.get("verified") is not True or lease.get("instance_id") != self.instance_id:
                    raise ValueError("actual live instance ownership was not verified")
                self.append("campaign.lease_verified", lease)
                remaining = self.budget.admit(time.time(), 0).remaining_seconds
                if remaining <= 0:
                    self.append("campaign.budget_drain", {"reason": "no safe runtime remains"})
                    break
                candidates = self.pending()
                admitted = []
                proposed_pairs = set(self.budget.started_pairs)
                for row in candidates:
                    if row["pair"]["id"] not in proposed_pairs and len(proposed_pairs) >= self.budget.policy.max_pairs:
                        continue
                    horizon = 0 if row["pair"]["id"] in self.budget.started_pairs else (10800 if len(slots) % 2 else 5400)
                    if self.budget.admit(time.time(), horizon, pair_id=row["pair"]["id"]).allowed:
                        admitted.append(row)
                        proposed_pairs.add(row["pair"]["id"])
                    if len(admitted) == len(slots):
                        break
                if not admitted:
                    self.append("campaign.budget_drain", {"reason": "new pairs cannot reserve both colour legs"})
                    break
                try:
                    from .wave import WaveJob
                except ImportError:
                    from wave import WaveJob
                jobs, metadata = [], []
                for index, row in enumerate(admitted):
                    slot = slots[(index + wave_number) % len(slots)]
                    pair, leg, attempt = row["pair"], row["leg"], row["attempt"]
                    white, black = pair["players"] if leg == 0 else tuple(reversed(pair["players"]))
                    game = row["game"]
                    identity = {"leg": leg, "white": white, "black": black, "opening_id": pair["opening"]["id"],
                                "opening_moves": pair["opening"]["moves"], "opening_sha256": ledger.digest(pair["opening"]["moves"]),
                                "bank_id": self.plan["bank_id"], "profile": self.plan["profile"],
                                "artifact_sha256": {name: self.players[name].sha256 for name in (white, black)},
                                "runner_sha256": self.plan["runner"]["sha256"], "slot": slot.id, "wave": wave_number}
                    job_id = game + f".a{attempt:03d}.x{launch}"
                    job_out = self.out / "jobs" / game / f"attempt-{attempt:03d}-launch-{launch}"
                    slot_file = self.out / f"placement-{launch}-{wave_number:03d}-{slot.id}.json"
                    slot_file.write_bytes(ledger.canonical({"slot": slot.to_record(), "cgroup": groups[slot.id],
                                                           "saved_ancestor_cpus": list(saved.allowed_cpus)}))
                    runner_argv = fastchess.single_game_argv(bundle_path(self.bundle, self.plan["runner"]["path"]),
                        fastchess.EngineCommand(white, (str(self.players[white].path),)),
                        fastchess.EngineCommand(black, (str(self.players[black].path),)),
                        opening_pgn=bundle_path(self.bundle, self.plan["opening_pgn"]), opening_start=pair["opening_index"], out=job_out)
                    argv = (sys.executable, str(HERE / "placement.py"), "--slot", str(slot_file),
                            "--record", str(self.out / f"placement-observed-{job_id}.json"), "--", *runner_argv)
                    start_job = {"campaign": self.plan["campaign"], "pair": pair["id"], "game": game,
                                 "attempt": attempt, "slot": slot.id, "wave": wave_number,
                                 "artifacts": [white, black], "opening": pair["opening"]["id"], "launch_id": launch}
                    job = WaveJob(job_id, tuple(argv), {"TZ": "UTC", "LANG": "C.UTF-8"}, start_job, job_out)
                    jobs.append(job)
                    self.job_specs[job_id] = {"pair": pair["id"], "game": game, "attempt": attempt, "identity": identity}
                    self.tail[job_id] = {"offset": 0, "partial": "", "trace": TraceState(pair["opening"]["moves"], white, black)}
                    self.append("campaign.launch_allocated", {"game": game, "attempt": attempt, "launch_id": job_id,
                                "directory": str(job_out.relative_to(self.out)), "plan_sha256": self.envelope["sha256"],
                                "identity": identity})
                    metadata.append(row)

                def release():
                    self.outbox.check()
                    for job in jobs:
                        observed = self.ready[job.identity]
                        spec = self.job_specs[job.identity]["identity"]
                        fresh = placement.observe_game_engines(observed["pid"],
                            [self.players[name].native_sha256 for name in (spec["white"], spec["black"])],
                            self.slots[spec["slot"]].cpus, expected_start_ticks=observed["start_ticks"])
                        owners = lambda proof: sorted((row["pid"], row["start_ticks"], row["native_sha256"]) for row in proof["engines"])
                        if owners(fresh) != owners(observed["engines"]):
                            raise ValueError("a READY engine owner changed before the global GO admission")
                        self.append("game.release_observation", fresh, pair=self.job_specs[job.identity]["pair"],
                                    game=self.job_specs[job.identity]["game"], attempt=self.job_specs[job.identity]["attempt"])
                    for pair_id in dict.fromkeys(row["pair"]["id"] for row in metadata):
                        if pair_id not in self.budget.started_pairs:
                            horizon = 10800 if len(slots) % 2 else 5400
                            if not self.budget.admit(time.time(), horizon, pair_id=pair_id).allowed:
                                return False
                            self.append("budget.pair_started", {"pair_id": pair_id, "reserved_wall_seconds": horizon})
                    if self.budget.admit(time.time(), 0).remaining_seconds <= 0:
                        return False
                    self.replicate(force=True)
                    return True

                remaining = min(remaining, self.budget.admit(time.time(), 0).remaining_seconds)
                observations = self.executor.run_wave(jobs, wall_seconds=remaining, release_callback=release, on_event=self.event)
                # Event callbacks may have failed and been disabled. Preserve
                # returned live/unknown ownership before any fallible trace
                # parsing can prevent this final admission check.
                for observation in observations:
                    if not physically_settled(observation):
                        job = next(job for job in jobs if job.identity == observation.get("identity", observation.get("id")))
                        self.record_unsettled(job, observation)
                if self.unsettled:
                    self.replicate(force=True)
                    raise RuntimeError("a launch owner is not physically settled; no subsequent wave may initialize")
                for job in jobs:
                    while (job.out / "raw.log").exists() and (job.out / "raw.log").stat().st_size > self.tail[job.identity]["offset"]:
                        self.observe_raw(job)
                for observation in observations:
                    spec = self.job_specs[observation.get("identity", observation.get("id"))]
                    state = self.results.games.get((spec["game"], spec["attempt"]))
                    if state is not None and state.result is None and state.interrupted is None:
                        settled = physically_settled(observation)
                        if settled:
                            keys = {name: spec[name] for name in ("pair", "game", "attempt")}
                            self.append("game.process_completed", observation, **keys)
                            self.append("game.interrupted", {"reason": "protocol_harness_error", "runner_observation": observation}, **keys)
                self.acknowledge_results(wait=True)
                self.replicate(force=True)
                (self.out / f"wave-{execution:03d}-{launch}-{wave_number:03d}.json").write_bytes(ledger.canonical(observations))
                if any(row.get("wave_aborted") for row in observations):
                    break
                wave_number += 1
            self.acknowledge_results(wait=True)
            self.replicate(force=True)
            for ticket in self.replication_tickets:
                ticket.result(timeout=125)
        except BaseException as error:
            failure = {"type": type(error).__name__, "error": str(error)}
            self.append("campaign.controller_error", failure)
        finally:
            if self.outbox is not None:
                try:
                    self.outbox.close(timeout=125)
                except BaseException as error:
                    cleanup.append({"component": "publisher", "error": str(error)})
            if manager is not None:
                cleanup.extend(manager.close())
            if self.unsettled:
                cleanup.append({"component": "runner", "unsettled_launches": sorted(self.unsettled)})
            os.sched_setaffinity(0, original)
        summary = collect.collect(self.journal.rows, self.plan["campaign"],
                                  expected_pairs=[row["id"] for row in self.plan["pairs"]], profile=self.plan["profile"])
        report = {"format": "rove4k-stage-run-v1", "plan_sha256": self.envelope["sha256"],
                  "complete": summary["campaign_stage_complete"] and failure is None and not cleanup,
                  "summary": summary, "failure": failure, "cleanup_errors": cleanup,
                  "budget": self.budget.as_dict(time.time()), "scope": self.plan["scope"]}
        (self.out / f"run-{execution:03d}-{launch}.json").write_bytes(ledger.canonical(report) + b"\n")
        return report


def physically_settled(observation):
    if observation.get("readers_done") is not True or observation.get("remaining_processes") != []:
        return False
    if observation.get("pid") is None:
        return observation.get("pgid") is None and observation.get("session") is None and observation.get("returncode") is None
    return type(observation.get("returncode")) is int


def assert_stage_binding(envelope, rows):
    body = envelope["content"]
    if any(row["event"] == "campaign.stage_started" and row["data"].get("stage") == body["stage"]
           and row["data"].get("plan_sha256") != envelope["sha256"] for row in rows):
        raise ValueError("campaign stage is already bound to another full artifact/native cohort; use a fresh campaign or distinct authorized stage")


def audit_remote_results(publisher, campaign, results):
    """Reject a remote completed colour absent from the verified journal.

    This also protects imports from an older/non-FIFO publisher. Recovery does
    not manufacture the missing original start, READY, placement or result.
    """
    pattern = re.compile(re.escape(campaign) + r"/results/([A-Za-z0-9_.-]+)/attempt-(\d{3,})/([a-f0-9]{64})\.json")
    known, uncertain = [], []
    keys = publisher.list_keys(campaign + "/results")
    if len(keys) > 4096:
        raise ValueError("remote result namespace exceeds the bounded campaign")
    for key in keys:
        match = pattern.fullmatch(key)
        if match is None:
            raise ValueError("unrecognized object in the owned result namespace")
        raw = publisher.read_verified(key, expected_sha=match[3])
        data = json.loads(raw)
        if ledger.canonical(data) != raw:
            raise ValueError("remote result bytes are not the canonical published contract")
        state = results.games.get((match[1], int(match[2])))
        if state is not None and state.result is not None and state.result == data and state.result_sha256 == match[3]:
            known.append(key)
            continue
        preserved = []
        for kind in ("pgn", "raw"):
            body_key, expected = data.get(kind + "_object_key"), data.get(kind + "_sha256")
            if (not isinstance(body_key, str) or not body_key.startswith(campaign + "/games/") or
                    not isinstance(expected, str) or not SHA.fullmatch(expected)):
                raise ValueError("uncertain remote result lacks bounded owned evidence identities")
            body = publisher.read_verified(body_key, expected_sha=expected, max_bytes=128 << 20)
            preserved.append({"kind": kind, "object_key": body_key, "sha256": expected, "bytes": len(body)})
        uncertain.append({"game": match[1], "attempt": int(match[2]), "object_key": key,
                          "sha256": match[3], "evidence": preserved,
                          "reason": "original completed result/start/READY journal prefix is unavailable or differs"})
    return {"known": known, "uncertain": uncertain,
            "scope": "verified remote object audit; uncertain colours must not be replayed or fabricated"}


def restore_remote_journal(publisher, campaign, out):
    """Recover a complete verified prefix, deduplicating overlapping snapshots.

    A missing last cloud chunk stays missing. Recovery neither invents an event
    nor promotes a queued/unacknowledged result into an accepted game.
    """
    ID(campaign)
    out = external_new(out)
    out.mkdir(parents=True)
    key_pattern = re.compile(re.escape(campaign) + r"/journal/(\d{9})-(\d{9})-([0-9a-f]{64})\.jsonl")
    keys = publisher.list_keys(campaign + "/journal")
    if not keys or len(keys) > 100000:
        raise ValueError("a bounded nonempty remote journal prefix is required")
    rows, total = {}, 0
    for key in keys:
        match = key_pattern.fullmatch(key)
        if match is None:
            raise ValueError("unexpected object in the owned journal namespace")
        raw = publisher.read_verified(key, expected_sha=match[3], max_bytes=4 << 20)
        total += len(raw)
        if total > 16 << 30:
            raise ValueError("recovery exceeded the finite campaign journal bound")
        block = raw.splitlines(keepends=True)
        if not block or any(not row.endswith(b"\n") or len(row) > 1 << 20 for row in block):
            raise ValueError("remote journal contains an incomplete or excessive event")
        parsed = [json.loads(row) for row in block]
        if [row["seq"] for row in parsed] != list(range(int(match[1]), int(match[2]) + 1)):
            raise ValueError("remote journal range differs from its immutable key")
        for row in parsed:
            sequence = row["seq"]
            if sequence in rows and rows[sequence] != row:
                raise ValueError("remote journal snapshots conflict at one sequence")
            rows[sequence] = row
    if sorted(rows) != list(range(len(rows))):
        raise ValueError("remote journal has a missing prefix or gap; preserve it for audit")
    destination = out / "campaign.jsonl"
    with destination.open("xb") as output:
        for sequence in range(len(rows)):
            output.write(ledger.canonical(rows[sequence]) + b"\n")
        output.flush()
        os.fsync(output.fileno())
    checked = ledger.read_journal(destination, campaign)
    results = ledger.CampaignResults.replay(campaign, checked)
    budget.CampaignBudget.replay(campaign, checked)
    audit = audit_remote_results(publisher, campaign, results)
    (out / "remote-result-audit.json").write_bytes(ledger.canonical(audit))
    if audit["uncertain"]:
        raise ValueError("uncertain remote completed colour; verified objects preserved and automatic replay blocked")
    return {"journal": str(destination), "events": len(checked), "last_sha256": checked[-1]["sha256"],
            "objects": len(keys), "verified_download_bytes": total, "sha256": registry.file_sha(destination),
            "scope": "verified cloud prefix only; live-owner and lease checks still required before resume"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    freeze = actions.add_parser("plan", help="freeze an actual qualified partial or complete TEST cohort")
    freeze.add_argument("--campaign", required=True)
    freeze.add_argument("--profile", choices=("test-p4", "test-p28"), required=True)
    freeze.add_argument("--stage", choices=("broad", "high", "update1", "update2"), default="broad")
    freeze.add_argument("--registry", type=Path, required=True)
    freeze.add_argument("--bank", type=Path, required=True)
    freeze.add_argument("--bank-sha256", required=True)
    freeze.add_argument("--runner", type=Path, required=True)
    freeze.add_argument("--runner-receipt", type=Path, required=True)
    freeze.add_argument("--out", type=Path, required=True)
    freeze.add_argument("--selected-id", action="append")
    freeze.add_argument("--repeats", type=int, default=1, choices=(1, 2))
    freeze.add_argument("--broad-plan", type=Path)
    freeze.add_argument("--broad-journal", type=Path)
    inspect = actions.add_parser("dry-run", help="verify a frozen bundle without executing engines or AWS calls")
    inspect.add_argument("--plan", type=Path, required=True)
    execute = actions.add_parser("run", help="run on the already allocated, verified owned instance")
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--aws-plan", type=Path, required=True)
    execute.add_argument("--journal", type=Path, required=True)
    execute.add_argument("--out", type=Path, required=True)
    execute.add_argument("--cgroup-root", type=Path, required=True)
    execute.add_argument("--resume", action="store_true")
    recover = actions.add_parser("restore", help="read checksum-verified owned cloud journal objects")
    recover.add_argument("--aws-plan", type=Path, required=True)
    recover.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "plan":
        envelope = freeze_plan(args.campaign, args.profile, args.registry, args.bank, args.bank_sha256,
            args.runner, args.runner_receipt, args.out, stage=args.stage, selected_ids=args.selected_id,
            repeats=args.repeats, broad_plan=args.broad_plan, broad_journal=args.broad_journal)
        result = {"plan": str(args.out / "plan.json"), "sha256": envelope["sha256"],
                  "pairs": len(envelope["content"]["pairs"]), "players": len(envelope["content"]["registry"]["players"]),
                  "paid_launch_performed": False}
    elif args.action == "dry-run":
        envelope, players = load_plan(args.plan)
        content = envelope["content"]
        result = {"plan_sha256": envelope["sha256"], "campaign": content["campaign"],
                  "profile": content["profile"], "stage": content["stage"], "pairs": len(content["pairs"]),
                  "games": len(content["pairs"]) * 2, "slots": len(content["slots"]),
                  "cohort": [row["artifact"].identity() for row in players], "scope": content["scope"],
                  "engine_execution_performed": False, "aws_calls_performed": False}
    else:
        try:
            from . import aws
        except ImportError:
            import aws
        config, _ = json_input(args.aws_plan)
        aws_plan = aws.AWSPlan.from_dict(config)
        client = aws.AWSCLI(aws_plan.region)
        publisher = aws.S3Evidence(client, aws_plan, args.out)
        if args.action == "restore":
            result = restore_remote_journal(publisher, aws_plan.campaign_id, args.out)
        else:
            envelope, _ = load_plan(args.plan)
            if envelope["content"]["campaign"] != aws_plan.campaign_id:
                raise ValueError("execution plan and AWS ownership campaign differ")
            with ledger.Journal(args.journal, aws_plan.campaign_id) as journal:
                assert_stage_binding(envelope, journal.rows)
                state = budget.CampaignBudget.replay(aws_plan.campaign_id, journal.rows)
                aws.verify_owned_lease(client, aws_plan, state, time.time(), caller_kind="instance")
                controller = StageController(args.plan, args.out, journal, publisher, state,
                    lease_verifier=lambda current: aws.verify_owned_lease(client, aws_plan, current, time.time(), caller_kind="instance"))
                result = controller.execute(args.cgroup_root, resume=args.resume)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 2 if args.action == "run" and not result["complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
