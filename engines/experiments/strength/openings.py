#!/usr/bin/env python3
"""Freeze a legal standard-start opening bank from the pinned CC0 input.

Inputs and generated banks live outside Git. This module is a development
consumer; none of its parser, source data or Python dependencies is submitted.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path
import random

REVISION = "a6189a30dc273ccb21fc2536a9a2fefd5592a67a"
SOURCE_URL = "https://github.com/lichess-org/chess-openings/tree/" + REVISION
SEED = 20261025
STAGE_COUNTS = {"broad": 12, "high": 12, "update1": 4, "update2": 4}
INPUT_BLOBS = {
    "a.tsv": "561099854a15dfb523759aa87993a1fe480a6abc",
    "b.tsv": "41c3727d28fc0b5915f30f3b634c07bd296f4bdb",
    "c.tsv": "4b3d9c90c67864db6eb728d82b225b44d91fccbd",
    "d.tsv": "a829bac9d2f288b033d605e842f3b802379e3455",
    "e.tsv": "93a82e1f505e06256530736b45460738bd50e897",
    "COPYING.txt": "0e259d42c996742e9e3cba14c677129b2c1b6311",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def family(moves):
    if len(moves) < 8:
        raise ValueError("opening family requires at least eight actual UCI plies")
    return " ".join(moves[:8])


def chess_modules():
    try:
        import chess
        import chess.pgn
    except ImportError as error:
        raise RuntimeError("development preparation requires pinned chess==1.11.2") from error
    if chess.__version__ != "1.11.2":
        raise ValueError("opening parser must use chess==1.11.2")
    return chess


@dataclass(frozen=True)
class Opening:
    id: str
    stage: str
    family: str
    moves: tuple[str, ...]
    eco: str
    name: str
    source_row_sha256: str


def verified_inputs(directory):
    """Verify original Git blob bytes, including the actual CC0 license."""
    records = []
    for name, expected in INPUT_BLOBS.items():
        path = directory / name
        if any(candidate.is_symlink() for candidate in (path, *path.parents)) or path.stat().st_nlink != 1:
            raise ValueError("source inputs must be ordinary owned files, not links")
        data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != expected:
            raise ValueError("pinned opening source differs: " + name)
        records.append({"name": name, "bytes": len(data), "sha256": sha(data), "git_blob": blob,
                        "url": "https://raw.githubusercontent.com/lichess-org/chess-openings/" + REVISION + "/" + name})
    return records


def candidates(directory):
    chess = chess_modules()
    groups = {}
    rejected = 0
    for name in ("a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"):
        with (directory / name).open(encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source, delimiter="\t"):
                game = chess.pgn.read_game(io.StringIO(row["pgn"] + " *"))
                if game is None or game.errors or game.headers.get("SetUp") or game.headers.get("FEN"):
                    rejected += 1
                    continue
                board = chess.Board()
                moves = []
                for move in game.mainline_moves():
                    if move not in board.legal_moves:
                        raise ValueError("source opening has an illegal move")
                    board.push(move)
                    moves.append(move.uci())
                    if len(moves) == 16:
                        break
                if len(moves) < 8 or board.is_game_over(claim_draw=True):
                    rejected += 1
                    continue
                key = family(moves)
                item = {"family": key, "moves": tuple(moves), "eco": row["eco"], "name": row["name"],
                        "source_row_sha256": sha(canonical(row))}
                # This fixed content ordering selects a representative without engine results.
                rank = (sha(canonical(item)), item["eco"], item["name"])
                if key not in groups or rank < groups[key][0]:
                    groups[key] = (rank, item)
    return [value[1] for _, value in sorted(groups.items())], rejected


def select_openings(rows, counts=STAGE_COUNTS, seed=SEED):
    """Balance ECO A-E buckets, never reuse a first-eight-ply family."""
    buckets = {letter: [] for letter in "ABCDE"}
    seen = set()
    for row in rows:
        if family(row["moves"]) != row["family"]:
            raise ValueError("declared family differs from actual moves")
        if row["family"] in seen:
            raise ValueError("opening family occurs more than once")
        seen.add(row["family"])
        buckets[row["eco"][0]].append(row)
    rng = random.Random(seed)
    for letter in buckets:
        buckets[letter].sort(key=lambda row: row["family"])
        rng.shuffle(buckets[letter])
    total = sum(counts.values())
    selected = []
    while len(selected) < total:
        before = len(selected)
        for letter in "ABCDE":
            if buckets[letter] and len(selected) < total:
                selected.append(buckets[letter].pop())
        if before == len(selected):
            raise ValueError("insufficient distinct legal opening families")
    result, offset = {}, 0
    for stage, count in counts.items():
        result[stage] = []
        for index, row in enumerate(selected[offset:offset + count]):
            result[stage].append(Opening(id=f"{stage}-{index:03d}", stage=stage, **row))
        offset += count
    return result


def pgn(openings):
    chess = chess_modules()
    games = []
    for opening in openings:
        board, tokens = chess.Board(), []
        for index, text in enumerate(opening.moves):
            if index % 2 == 0:
                tokens.append(str(index // 2 + 1) + ".")
            move = chess.Move.from_uci(text)
            if move not in board.legal_moves:
                raise ValueError("bank move failed legal replay")
            tokens.append(board.san(move))
            board.push(move)
        games.append(f'[Event "Rove4k {opening.id}"]\n[ECO "{opening.eco}"]\n[Result "*"]\n\n' +
                     " ".join(tokens) + " *\n")
    return "\n".join(games).encode()


def prepare_bank(inputs, out, *, seed=SEED):
    if not inputs.is_absolute() or not out.is_absolute() or out.exists():
        raise ValueError("absolute input and new absolute external output required")
    if any((parent / ".git").exists() for parent in (out, *out.parents)):
        raise ValueError("generated opening bank must remain outside Git")
    input_records = verified_inputs(inputs)
    rows, rejected = candidates(inputs)
    stages = select_openings(rows, seed=seed)
    encoded = {stage: [asdict(item) for item in values] for stage, values in stages.items()}
    bank_id = sha(canonical({"revision": REVISION, "seed": seed, "stages": encoded}))
    record = {"format": 1, "bank_id": bank_id, "seed": seed,
              "source": {"url": SOURCE_URL, "revision": REVISION, "license": "CC0-1.0", "inputs": input_records,
                         "sha256": sha(canonical(input_records)), "sha256_scope": "canonical input records", "verified": True},
              "family_definition": "space-joined first eight UCI plies from standard startpos",
              "stages": encoded, "holdout_families": sorted(item.family for values in stages.values() for item in values),
              "candidate_families": len(rows), "rejected_source_rows": rejected,
              "runtime": {"python_chess": "1.11.2"}, "files": {}}
    out.mkdir(parents=True)
    for stage, values in stages.items():
        data = pgn(values)
        (out / (stage + ".pgn")).write_bytes(data)
        record["files"][stage] = {"path": str(out / (stage + ".pgn")), "bytes": len(data), "sha256": sha(data)}
    body = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    (out / "openings.json").write_bytes(body)
    return {"path": str(out / "openings.json"), "sha256": sha(body), "bank_id": bank_id,
            "families": len(record["holdout_families"]), "stages": {key: len(value) for key, value in stages.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    print(json.dumps(prepare_bank(args.inputs, args.out, seed=args.seed), sort_keys=True))


if __name__ == "__main__":
    main()
