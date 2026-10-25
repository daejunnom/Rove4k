#!/usr/bin/env python3
"""Black-box pure-bitboard board contracts against our independent rules oracle.

Consumes a frozen build.json plus its sources/ directory and selects one DEV
binary by its complete-file hash. Hash/HCE/context are recomputed in Python
from the oracle's 64 cells, not from the engine's incremental fields. This is
board correctness evidence, not strength, shipping-size, or hardware scaling.
All inputs, transcripts, partial failures and results go to a new external --out.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
MASK = (1 << 64) - 1
RIGHTS = ("K", "Q", "k", "q")
MATERIAL = (100, 320, 330, 500, 900, 0)
SPECIAL = {
    "ep-legal": "7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "ep-file-pin": "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "ep-rank-discovery": "k7/8/8/4KPpr/8/8/8/8 w - g6 0 1",
    "ep-one-of-two-legal": "k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1",
    "ep-no-capturer": "7k/8/8/8/4P3/8/8/K7 b - e3 0 1",
    "castle-clear": "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "castle-through-check": "r3k2r/8/8/8/8/5r2/8/R3K2R w KQkq - 0 1",
    "castle-destination-check": "r3k2r/8/8/8/8/6r1/8/R3K2R w KQkq - 0 1",
    "castle-queenside-blocker": "r3k2r/8/8/8/8/8/8/RN2K2R w KQkq - 0 1",
    "castle-current-check": "r3k2r/8/8/8/8/4r3/8/R3K2R w KQkq - 0 1",
    "castle-stale-rights": "4k3/8/8/8/8/8/8/4K3 w KQkq - 0 1",
    "promotion-quiet": "7k/P7/8/8/8/8/8/4K3 w - - 0 1",
    "promotion-both-captures": "r1r4k/1P6/8/8/8/8/8/4K3 w - - 0 1",
    "rook-absolute-pin": "4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1",
    "knight-absolute-pin": "4r2k/8/8/8/8/8/4N3/4K3 w - - 0 1",
    "double-check": "4r2k/8/8/8/1b6/8/8/4K3 w - - 0 1",
    "halfmove-99": "7k/8/8/8/8/8/8/R3K3 w - - 99 80",
    "halfmove-100": "7k/8/8/8/8/8/8/R3K3 w - - 100 80",
    "dead-bishops": "7k/8/5b2/8/8/8/1B6/K7 w - - 0 1",
    "live-opposite-bishops": "7k/8/8/5b2/8/8/1B6/K7 w - - 0 1",
    "live-two-knights": "7k/8/8/8/8/8/1NN5/K7 w - - 0 1",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def mix(x):
    x = (x + 0x9E3779B97F4A7C15) & MASK
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


def castle(board):
    # FEN admission canonicalizes stale rights against king/rook placement.
    homes = ((4, "K", 7, "R"), (4, "K", 0, "R"), (60, "k", 63, "r"), (60, "k", 56, "r"))
    return sum(1 << i for i, (k, king, r, rook) in enumerate(homes)
               if RIGHTS[i] in board.castling and board.cells[k] == king and board.cells[r] == rook)


def legal_ep(board):
    if board.ep >= 0:
        for move in board.legal_moves():
            if move.dst == board.ep and board.cells[move.src].lower() == "p" and move.src % 8 != move.dst % 8:
                return board.ep
    return -1


def full_hash(board):
    h = mix(2048 + castle(board)) ^ (0 if board.turn else mix(2064))
    ep = legal_ep(board)
    if ep >= 0:
        h ^= mix(2065 + ep % 8)
    for square, piece in enumerate(board.cells):
        if piece != ".":
            kind, color = "pnbrqk".index(piece.lower()), int(piece.islower())
            h ^= mix(square + (kind + 6 * color) * 64)
    return h


def full_eval(board):
    total = 0
    for square, piece in enumerate(board.cells):
        if piece == ".":
            continue
        kind, white = "pnbrqk".index(piece.lower()), piece.isupper()
        rank, file = divmod(square, 8)
        advance = rank if white else 7 - rank
        center = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
        score = MATERIAL[kind] + advance * (7 if kind == 0 else 2 if kind == 3 else 0)
        score += center * (9 if kind == 1 else 5 if kind == 2 else -3 if kind == 5 else 2 if kind in (0, 4) else 0)
        total += score if white else -score
    return total if board.turn else -total


def dead(board):
    pieces = [(i, p.lower()) for i, p in enumerate(board.cells) if p != "." and p.lower() != "k"]
    if any(p not in "bn" for _, p in pieces):
        return False
    return len(pieces) < 2 or (all(p == "b" for _, p in pieces)
                              and len({(s // 8 + s % 8) % 2 for s, _ in pieces}) == 1)


def reference(boards):
    context = full_hash(boards[0])
    hashes = [context]
    for board in boards[1:]:
        h = full_hash(board)
        context = ((((context << 1) | (context >> 63)) & MASK) ^ h) if board.halfmove else h
        hashes.append(h)
    board = boards[-1]
    return {"hash": hashes[-1], "context": context, "halfmove": board.halfmove,
            "eval": full_eval(board), "ep": legal_ep(board), "castle": castle(board),
            "side": 1 if board.turn else -1,
            "draw": board.halfmove >= 100 or hashes.count(hashes[-1]) >= 3 or dead(board)}


def reflected(board, cls, mirror=False):
    cells = ["."] * 64
    for square, piece in enumerate(board.cells):
        rank, file = divmod(square, 8)
        target = rank * 8 + 7 - file if mirror else (7 - rank) * 8 + file
        cells[target] = piece if mirror else piece.swapcase()
    ep = -1 if board.ep < 0 else ((board.ep // 8) * 8 + 7 - board.ep % 8 if mirror
                                 else (7 - board.ep // 8) * 8 + board.ep % 8)
    rights = board.castling if mirror else "".join(c for c in RIGHTS if c.swapcase() in board.castling)
    return cls(cells, board.turn if mirror else not board.turn, rights, ep, board.halfmove, board.fullmove)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True, help="frozen build.json with source/native hashes")
    parser.add_argument("--engine", type=Path, required=True, help="one DEV executable recorded in --build")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, help="override build.json's sibling sources directory")
    parser.add_argument("--oracle-root", type=Path, default=HERE.parents[1] / "tests")
    parser.add_argument("--random-games", type=int, default=4)
    parser.add_argument("--plies", type=int, default=96)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.out.is_absolute() or out.exists() or any((p / ".git").exists() for p in (out, *out.parents)):
        parser.error("--out must be a new absolute directory outside Git checkouts")
    if not 0 <= args.random_games <= 32 or not 1 <= args.plies <= 256:
        parser.error("random-games must be 0..32 and plies 1..256")
    build_path, binary = args.build.resolve(), args.engine.resolve()
    build = json.loads(build_path.read_text())
    selected = [r for r in build["engines"] if Path(r["command"][0]).resolve() == binary]
    require(len(selected) == 1 and selected[0]["profile"] == "dev", "select exactly one recorded DEV executable")
    spec = selected[0]
    require(sha(binary.read_bytes()) == spec["native_sha256"], "complete executable SHA-256 differs from build")
    source = args.source_root.resolve() if args.source_root else build_path.parent / "sources"
    source_bytes = {}
    for name, expected in build["source_sha256"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "unsafe source manifest path")
        data = (source / name).read_bytes()
        require(sha(data) == expected, f"frozen source hash mismatch: {name}")
        source_bytes[name] = data
    out.mkdir(parents=True)
    recipe = out / "recipe"
    recipe.mkdir()
    (recipe / "build.json").write_bytes(build_path.read_bytes())
    (recipe / "tests_board.py").write_bytes(Path(__file__).read_bytes())
    for name, data in source_bytes.items():
        target = recipe / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    oracle_bytes = {}
    for name in ("chess_oracle.py", "verify.py"):
        data = (args.oracle_root / name).read_bytes()
        (recipe / name).write_bytes(data)
        oracle_bytes[name] = sha(data)
    oracle = load_module("chess_oracle", recipe / "chess_oracle.py")
    probe = load_module("tiny_d_board_probe", recipe / "verify.py")
    report = {"scope": "Independent legal/perft/transitions and full hash/HCE/context recomputation; no strength or size claim.",
              "binary": str(binary), "binary_sha256": spec["native_sha256"],
              "build_sha256": sha(build_path.read_bytes()), "source_sha256": build["source_sha256"],
              "oracle_sha256": oracle_bytes, "harness_sha256": sha(Path(__file__).read_bytes()),
              "perft": [], "matrices": [], "random": [], "cycles": [], "snapshots": 0,
              "transitions": 0, "passed": False}
    engine = None
    stage = "oracle self-check"
    try:
        report["oracle_self_check"] = oracle.self_check()
        engine = probe.Engine(spec, out, "engine", 10)
        engine.initialize()

        def snapshot(boards, label, moves=True):
            actual, expected = engine.state(), reference(boards)
            for key, value in expected.items():
                require(key in actual, f"{label}: missing DEV field {key}")
                observed = int(actual[key], 16) if key in ("hash", "context") else actual[key]
                require(observed == value, f"{label}: {key}: actual={observed!r} expected={value!r}; fen={boards[-1].fen()}")
            require(actual.get("invariant") is True, f"{label}: internal full recomputation failed")
            report["snapshots"] += 1
            if moves:
                wanted = {str(m) for m in boards[-1].legal_moves()}
                found = engine.dev("legal", "legal").split()[1:]
                require(len(found) == len(set(found)) and set(found) == wanted,
                        f"{label}: legal moves missing={wanted-set(found)} extra={set(found)-wanted}")
            return expected

        stage = "frozen perft positions"
        for label, fen, totals in oracle.PERFT:
            board = oracle.Board.from_fen(fen)
            engine.position(fen)
            snapshot([board], label)
            require(engine.dev("verify", "verify ").startswith("verify pass positions "), f"{label}: verify failed")
            for depth, wanted in enumerate(totals, 1):
                fields = engine.dev(f"perft {depth}", "perft ").split()
                require(fields == ["perft", str(depth), str(wanted)], f"{label}: perft {depth}: {fields} != {wanted}")
                report["perft"].append({"case": label, "depth": depth, "nodes": wanted})

        stage = "special transitions"
        matrices = []
        for label, fen in SPECIAL.items():
            board = oracle.Board.from_fen(fen)
            matrices += [(label, board), (label + "/color", reflected(board, oracle.Board))]
            if not board.castling:
                matrices += [(label + "/file", reflected(board, oracle.Board, True)),
                             (label + "/color-file", reflected(reflected(board, oracle.Board), oracle.Board, True))]
        for label, board in matrices:
            stage = "special " + label
            engine.position(board.fen())
            snapshot([board], label)
            wanted = board.perft(2)
            require(engine.dev("perft 2", "perft ").split() == ["perft", "2", str(wanted)], f"{label}: perft 2 mismatch")
            require(engine.dev("verify", "verify ").startswith("verify pass positions "), f"{label}: verify failed")
            count = 0
            for move in board.legal_moves():
                child = board.apply(move)
                engine.position(board.fen(), [str(move)])
                replay = snapshot([board, child], label + "/" + str(move))
                engine.position(child.fen())
                rebuilt = snapshot([child], label + "/rebuild/" + str(move), moves=False)
                require(all(replay[k] == rebuilt[k] for k in replay if k not in ("context", "draw")),
                        f"{label}: replay/FEN mismatch after {move}")
                count += 1
            report["transitions"] += count
            report["matrices"].append({"case": label, "fen": board.fen(), "perft2": wanted, "transitions": count})

        stage = "random replay and reconstruction"
        for game in range(args.random_games):
            rng, boards, moves = random.Random(20261020 + game), [oracle.Board.from_fen()], []
            for ply in range(args.plies):
                legal = list(boards[-1].legal_moves())
                if not legal:
                    break
                move = rng.choice(legal)
                moves.append(str(move)); boards.append(boards[-1].apply(move))
                engine.position(moves=moves)
                snapshot(boards, f"random/{game}/{ply+1}")
                engine.position(boards[-1].fen())
                snapshot([boards[-1]], f"random/{game}/{ply+1}/rebuild", moves=False)
                report["transitions"] += 1
            report["random"].append({"seed": 20261020 + game, "plies": len(moves), "moves": moves})

        stage = "repetition and irreversible resets"
        knight_cycle = ["g1f3", "g8f6", "f3g1", "f6g8"]
        castle_fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        castle_cycle = ["e1f1", "e8f8", "f1e1", "f8e8"]
        cycles = [("twofold", None, knight_cycle), ("third-repeat", None, knight_cycle * 2),
                  ("pawn-reset", None, knight_cycle * 2 + ["e2e4"]),
                  ("capture-reset", None, ["e2e4", "d7d5", "e4d5"]),
                  ("ep-cycle-twofold", None, ["e2e4", "g8f6", "g1f3", "f6g8", "f3g1"]),
                  ("ep-cycle-threefold", None, ["e2e4"] + ["g8f6", "g1f3", "f6g8", "f3g1"] * 2),
                  ("castle-loss-twofold", castle_fen, castle_cycle * 2),
                  ("castle-loss-threefold", castle_fen, castle_cycle * 3)]
        for label, fen, moves in cycles:
            boards = [oracle.Board.from_fen(fen or oracle.START)]
            for move in moves:
                boards.append(boards[-1].play(move))
            engine.position(fen, moves)
            expected = snapshot(boards, label)
            report["cycles"].append({"case": label, "moves": moves, "expected_draw": expected["draw"],
                                     "halfmove": expected["halfmove"]})
        report["stats"] = engine.stats()
        engine.assert_threads_stable()
        engine.close()
        engine = None
        require(sha(binary.read_bytes()) == spec["native_sha256"], "complete binary changed during verification")
        require(all((source / name).read_bytes() == data for name, data in source_bytes.items()),
                "frozen source bytes changed during verification")
        report["passed"] = True
    except Exception as error:
        report["error"] = {"stage": stage, "type": type(error).__name__, "message": str(error)}
    finally:
        if engine is not None:
            engine.terminate()
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "snapshots": report["snapshots"],
                      "transitions": report["transitions"], "report": str(out / "results.json")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
