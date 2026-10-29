#!/usr/bin/env python3
"""Prepare legal, game/family-separated E19 WDL data without training.

Official complete monthly archives and a verified league holdout are required
for data_ready. Plain PGN fixtures exercise this pipeline but never qualify as
real corpus. A local SQLite stage bounds memory and preserves the selection.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

import chess
import chess.pgn

try:
    from .fetch_data import CORPUS, external_output, sha256_file
except ImportError:
    from fetch_data import CORPUS, external_output, sha256_file

SEED = 20261025
OPENING_REVISION = "a6189a30dc273ccb21fc2536a9a2fefd5592a67a"
RESULTS = {"1-0": 1.0, "1/2-1/2": 0.5, "0-1": 0.0}
PRIORITY = {"test": 0, "validation": 1, "train": 2}
FILTERS = {"minimum_rating_both": 1600, "minimum_base_plus_40_increment_seconds": 180,
           "minimum_sample_ply": 24, "maximum_sample_ply": 160, "maximum_positions_per_game": 16}
MAX_ZSTD_WINDOW_BYTES = 256 * 1024 * 1024


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def family_id(moves) -> str:
    if len(moves) < 8:
        raise ValueError("opening family requires eight actual legal UCI plies")
    return " ".join(moves[:8])


def split_for_family(family: str, seed: int = SEED) -> str:
    bucket = int(_digest(f"{seed}:family:{family}")[:16], 16) % 100
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def header_rejection(headers) -> str | None:
    variant = headers.get("Variant", "Standard")
    if variant not in ("Standard", "Chess") or headers.get("SetUp", "0") != "0" or "FEN" in headers:
        return "nonstandard_start"
    if headers.get("Result") not in RESULTS:
        return "unfinished_or_invalid_result"
    white = headers.get("White", "").strip().casefold()
    black = headers.get("Black", "").strip().casefold()
    if not white or not black or white == "?" or black == "?":
        return "missing_player_identity"
    if white == black:
        return "same_player"
    try:
        if min(int(headers.get("WhiteElo", "")), int(headers.get("BlackElo", ""))) < FILTERS["minimum_rating_both"]:
            return "rating"
    except ValueError:
        return "missing_rating"
    timing = re.fullmatch(r"([0-9]+)\+([0-9]+)", headers.get("TimeControl", ""))
    if not timing:
        return "unsupported_time_control"
    base, increment = map(int, timing.groups())
    if base + 40 * increment < FILTERS["minimum_base_plus_40_increment_seconds"]:
        return "time_control"
    return None


class _CorpusBuilder(chess.pgn.GameBuilder):
    def begin_game(self):
        self._result_seen = False
        return super().begin_game()

    def end_headers(self):
        return chess.pgn.SKIP if header_rejection(self.game.headers) else None

    def handle_error(self, error):
        self.game.errors.append(error)

    def visit_result(self, result):
        expected = self.game.headers.get("Result")
        if expected in RESULTS and result != expected:
            self.handle_error(ValueError("PGN header and movetext results disagree"))
        self._result_seen = True
        return super().visit_result(result)

    def visit_move(self, board, move):
        if self._result_seen:
            self.handle_error(ValueError("PGN contains a move after its result token"))
        return super().visit_move(board, move)

    def end_game(self):
        if not self._result_seen and header_rejection(self.game.headers) is None:
            self.handle_error(ValueError("PGN is missing its movetext result token"))
        return super().end_game()


class _BoundedReader(io.RawIOBase):
    def __init__(self, source, limit: int):
        self.source, self.limit, self.total = source, limit, 0

    def readable(self):
        return True

    def readinto(self, buffer):
        data = self.source.read(len(buffer))
        self.total += len(data)
        if self.total > self.limit:
            raise ValueError("decompressed PGN exceeds the declared byte bound")
        buffer[:len(data)] = data
        return len(data)


@contextmanager
def open_pgn(path: Path):
    if str(path).endswith(".zst"):
        import zstandard
        with Path(path).open("rb") as raw:
            # The pinned 0.25 C backend passes this byte-valued bound to
            # libzstd. Concatenated frames include a real multi-MiB window.
            with zstandard.ZstdDecompressor(max_window_size=MAX_ZSTD_WINDOW_BYTES).stream_reader(raw, read_across_frames=True) as stream:
                with io.TextIOWrapper(io.BufferedReader(_BoundedReader(stream, 1024 * 1024 * 1024)), encoding="utf-8-sig", errors="strict") as text:
                    yield text
    else:
        with Path(path).open("r", encoding="utf-8-sig", errors="strict") as text:
            yield text


def load_holdout(path: Path | None, *, expected_sha256: str | None = None) -> tuple[set[str], dict]:
    if path is None:
        return set(), {"verified": False, "reason": "real league holdout not supplied", "family_count": 0}
    path = Path(path).resolve()
    raw = path.read_bytes()
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        if re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None or actual_sha256 != expected_sha256:
            raise ValueError("holdout differs from the independently supplied bank digest")
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError("holdout must be a bank manifest")
    rows = list(document.get("openings", []))
    stages = document.get("stages", {})
    if not isinstance(stages, dict):
        raise ValueError("holdout stages must map stage names to opening rows")
    for stage in stages.values():
        if not isinstance(stage, list):
            raise ValueError("each holdout stage must contain opening rows")
        rows.extend(stage)
    if not rows:
        raise ValueError("holdout contains no actual openings")
    families = set()
    for row in rows:
        moves = row.get("moves")
        if isinstance(moves, str):
            moves = moves.split()
        if not isinstance(moves, list) or len(moves) < 8:
            raise ValueError("holdout opening requires actual startpos moves")
        board = chess.Board()
        for value in moves:
            move = chess.Move.from_uci(value)
            if move not in board.legal_moves:
                raise ValueError("holdout contains an illegal startpos prefix")
            board.push(move)
        family = family_id(moves)
        declared = row.get("family", row.get("family_id", family))
        if declared != family:
            raise ValueError("holdout family differs from its actual first eight plies")
        families.add(family)
    source = document.get("source", {})
    repository = "https://github.com/lichess-org/chess-openings"
    source_url = str(source.get("url", ""))
    source_verified = (source.get("revision") == OPENING_REVISION and
                (source_url == repository or source_url.startswith(repository + "/")) and
                re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", ""))) is not None and
                source.get("license") == "CC0-1.0" and source.get("verified") is True)
    return families, {"path": str(path), "sha256": actual_sha256, "expected_sha256": expected_sha256,
                      "family_count": len(families), "source": source, "source_verified": source_verified,
                      "verified": source_verified and expected_sha256 is not None}


def corpus_source(path: Path) -> dict:
    path = Path(path).resolve()
    actual = sha256_file(path)
    frozen = next((row for row in CORPUS.values() if row["filename"] == path.name), None)
    real = frozen is not None and actual == frozen["sha256"]
    if frozen is not None and not real:
        raise ValueError("named official corpus file differs from its frozen complete archive")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual,
            "kind": "lichess-standard-rated-cc0" if real else "fixture",
            "url": frozen["url"] if real else None, "license": "CC0-1.0" if real else None}


def game_record(game, source_id: str, ordinal: int, seed: int, holdout: set[str]) -> tuple[dict | None, str | None]:
    reason = header_rejection(game.headers)
    if reason:
        return None, reason
    if game.errors:
        return None, "pgn_parse_error"
    board = chess.Board()
    moves, candidates = [], []
    for ply, move in enumerate(game.mainline_moves(), 1):
        if board.is_game_over(claim_draw=False):
            return None, "move_after_automatic_terminal"
        if move not in board.legal_moves:
            return None, "illegal_move"
        board.push(move)
        moves.append(move.uci())
        if not board.is_valid():
            return None, "invalid_board"
        if any(chess.popcount(board.occupied_co[color]) > 16 for color in chess.COLORS):
            return None, "model_population_domain"
        if FILTERS["minimum_sample_ply"] <= ply <= FILTERS["maximum_sample_ply"]:
            fen = board.fen(en_passant="legal")
            key = _digest(" ".join(fen.split()[:4]))
            candidates.append({"ply": ply, "fen": fen, "position_key": key})
    if len(moves) < 8 or not candidates:
        return None, "no_sample_positions"
    family = family_id(moves)
    if family in holdout:
        return None, "league_holdout_family"
    label = RESULTS[game.headers["Result"]]
    outcome = board.outcome(claim_draw=False)
    if outcome is not None and outcome.result() != game.headers["Result"]:
        return None, "contradictory_terminal_result"
    identity = _json([game.headers["White"].strip().casefold(), game.headers["Black"].strip().casefold(), label, moves])
    identity = _digest(identity)
    for candidate in candidates:
        candidate["sample_rank"] = _digest(f"{seed}:position:{identity}:{candidate['ply']}")
    candidates.sort(key=lambda row: row["sample_rank"])
    candidates = candidates[:FILTERS["maximum_positions_per_game"]]
    return {"game_id": identity, "family_id": family, "split": split_for_family(family, seed),
            "rank": _digest(f"{seed}:game:{identity}"), "white_label": label, "moves": moves,
            "source_id": source_id, "source_game_ordinal": ordinal,
            "source_game_url": game.headers.get("Site"), "positions": candidates,
            "ratings": [int(game.headers["WhiteElo"]), int(game.headers["BlackElo"])],
            "time_control": game.headers["TimeControl"]}, None


def prepare_dataset(pgnpaths, holdout_path, out: Path, *, seed: int = SEED, max_games: int = 50000,
                    holdout_sha256: str | None = None) -> dict:
    started = time.monotonic()
    started_cpu = time.process_time()
    if type(seed) is not int or type(max_games) is not int or not 1 <= max_games <= 50000:
        raise ValueError("seed must be an integer and max_games must be in 1..50000")
    if chess.__version__ != "1.11.2":
        raise ValueError("the pinned development parser chess==1.11.2 is required")
    paths = [Path(path).resolve() for path in pgnpaths]
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("distinct PGN input files are required")
    sources = [corpus_source(path) for path in paths]
    holdout, holdout_receipt = load_holdout(holdout_path, expected_sha256=holdout_sha256)
    out = external_output(out)
    out.mkdir(parents=True)
    producer = {}
    (out / "producer").mkdir()
    for name in ("data.py", "fetch_data.py", "requirements.txt"):
        body = Path(__file__).with_name(name).read_bytes()
        snapshot = out / "producer" / name
        snapshot.write_bytes(body)
        producer[name] = {"path": str(snapshot), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    zstandard_version = None
    zstandard_backend = None
    if any(str(path).endswith(".zst") for path in paths):
        import zstandard
        if zstandard.__version__ != "0.25.0":
            raise ValueError("the pinned archive parser zstandard==0.25.0 is required")
        zstandard_version = zstandard.__version__
        zstandard_backend = getattr(zstandard, "backend", None)
    counts = Counter()
    runtime = {"pid": os.getpid(), "cpu_affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None}
    try:
        import resource
        runtime["limits"] = {name: list(resource.getrlimit(getattr(resource, name)))
                             for name in ("RLIMIT_CPU", "RLIMIT_AS", "RLIMIT_FSIZE")}
    except ImportError:
        runtime["limits"] = None
    manifest = {"format": 1, "kind": "e19-wdl-dataset", "complete": False, "data_ready": False,
                "pipeline_ready": False, "seed": seed, "max_games": max_games, "filters": FILTERS,
                "split_policy": "sha256(seed:first8-uci-family),80/10/10; no symmetry transform",
                "position_key": "board/side/castling/legal-EP; excludes move counters",
                "dedup_priority": ["test", "validation", "train"], "sources": sources,
                "holdout": holdout_receipt, "producer": producer,
                "parser": {"chess": chess.__version__, "zstandard": zstandard_version,
                           "zstandard_backend": zstandard_backend, "maximum_zstd_window_bytes": MAX_ZSTD_WINDOW_BYTES,
                           "maximum_decompressed_bytes_per_input": 1024 * 1024 * 1024, "python": sys.version.split()[0]},
                "runtime": runtime, "training_updates": 0, "shards": {}}

    def save():
        manifest["counts"] = dict(sorted(counts.items()))
        runtime["elapsed_seconds"] = time.monotonic() - started
        runtime["cpu_seconds"] = time.process_time() - started_cpu
        (out / "dataset.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    save()
    connection = sqlite3.connect(out / "selection.sqlite")
    try:
        connection.execute("PRAGMA cache_size=-20000")
        connection.execute("CREATE TABLE games(id TEXT PRIMARY KEY, rank TEXT NOT NULL, body TEXT NOT NULL)")
        for path, source in zip(paths, sources):
            with open_pgn(path) as stream:
                ordinal = 0
                while True:
                    game = chess.pgn.read_game(stream, Visitor=_CorpusBuilder)
                    if game is None:
                        break
                    ordinal += 1
                    counts["parsed_games"] += 1
                    row, reason = game_record(game, source["sha256"], ordinal, seed, holdout)
                    if reason:
                        counts["rejected_" + reason] += 1
                    else:
                        counts["eligible_games_before_dedup"] += 1
                        cursor = connection.execute("INSERT OR IGNORE INTO games VALUES(?,?,?)", (row["game_id"], row["rank"], _json(row)))
                        if cursor.rowcount == 0:
                            counts["duplicate_games"] += 1
                    if ordinal % 10000 == 0:
                        connection.commit()
                        save()
                        print(_json({"kind": "data-progress", "parsed": counts["parsed_games"], "eligible": counts["eligible_games_before_dedup"]}), flush=True)
            connection.commit()
        connection.execute("CREATE TABLE winners(key TEXT PRIMARY KEY, priority INTEGER, rank TEXT, game_id TEXT, body TEXT)")
        selected = connection.execute("SELECT body FROM games ORDER BY rank,id LIMIT ?", (max_games,))
        for (encoded,) in selected:
            row = json.loads(encoded)
            counts["selected_games_before_position_dedup"] += 1
            for candidate in row["positions"]:
                priority = PRIORITY[row["split"]]
                ranking = row["rank"] + ":" + candidate["sample_rank"]
                existing = connection.execute("SELECT priority,rank FROM winners WHERE key=?", (candidate["position_key"],)).fetchone()
                if existing is not None and existing <= (priority, ranking):
                    counts["duplicate_positions"] += 1
                    continue
                if existing is not None:
                    counts["duplicate_positions"] += 1
                sample = {"game_id": row["game_id"], "family_id": row["family_id"], "split": row["split"],
                          "white_label": row["white_label"], "ply": candidate["ply"], "fen": candidate["fen"],
                          "position_key": candidate["position_key"], "moves": row["moves"][:candidate["ply"]],
                          "source_id": row["source_id"], "source_game_ordinal": row["source_game_ordinal"],
                          "source_game_url": row["source_game_url"]}
                connection.execute("INSERT OR REPLACE INTO winners VALUES(?,?,?,?,?)", (candidate["position_key"], priority, ranking, row["game_id"], _json(sample)))
        connection.commit()
        for split, priority in PRIORITY.items():
            path = out / (split + ".jsonl")
            labels, families, games = Counter(), set(), set()
            rows = 0
            # The window count uses all retained positions of this game; every
            # surviving game contributes exactly one total sample weight.
            query = "SELECT body,COUNT(*) OVER (PARTITION BY game_id) FROM winners WHERE priority=? ORDER BY game_id,key"
            with path.open("x", encoding="utf-8", newline="\n") as target:
                for encoded, per_game in connection.execute(query, (priority,)):
                    sample = json.loads(encoded)
                    sample["weight"] = 1.0 / per_game
                    target.write(_json(sample) + "\n")
                    rows += 1
                    labels[str(sample["white_label"])] += 1
                    families.add(sample["family_id"])
                    games.add(sample["game_id"])
            manifest["shards"][split] = {"path": str(path), "bytes": path.stat().st_size,
                                          "sha256": sha256_file(path), "rows": rows, "games": len(games),
                                          "families": len(families), "labels": dict(labels)}
        expected = {row["sha256"] for row in CORPUS.values()}
        complete_real_corpus = len(sources) == len(expected) and {row["sha256"] for row in sources} == expected and all(row["kind"] == "lichess-standard-rated-cc0" for row in sources)
        manifest["complete"] = True
        manifest["pipeline_ready"] = all(row["rows"] > 0 for row in manifest["shards"].values())
        manifest["data_ready"] = bool(complete_real_corpus and holdout_receipt["verified"] and manifest["pipeline_ready"])
        manifest["readiness_reasons"] = [reason for reason, passed in (
            ("complete frozen monthly CC0 archives are required", complete_real_corpus),
            ("verified real league holdout is required", holdout_receipt["verified"]),
            ("train, validation and test must each contain retained positions", manifest["pipeline_ready"])) if not passed]
        save()
        return manifest
    except Exception as error:
        manifest["error"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pgn", type=Path, action="append", required=True)
    parser.add_argument("--holdout", type=Path)
    parser.add_argument("--holdout-sha256", help="bank digest supplied by its independent verified producer")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--max-games", type=int, default=50000)
    args = parser.parse_args()
    result = prepare_dataset(args.pgn, args.holdout, args.out, seed=args.seed, max_games=args.max_games,
                             holdout_sha256=args.holdout_sha256)
    print(_json({"complete": result["complete"], "data_ready": result["data_ready"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
