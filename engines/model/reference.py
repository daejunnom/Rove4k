"""Scalar E inference oracle. Board indices are a1=0, h8=63.

No training or learned-strength claim is attached to this hand-authored model.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from codec import load_model

PIECES = "PNBRQK"


@dataclass(frozen=True)
class Position:
    board: tuple[str, ...]
    side: int

    @staticmethod
    def fen(text):
        fields = text.split()
        if len(fields) < 2 or fields[1] not in ("w", "b"):
            raise ValueError("FEN board and side are required")
        ranks = fields[0].split("/")
        if len(ranks) != 8:
            raise ValueError("FEN must have eight ranks")
        board = []
        for rank in reversed(ranks):
            row = []
            for token in rank:
                if token in "12345678":
                    row.extend("." * int(token))
                elif token.upper() in PIECES:
                    row.append(token)
                else:
                    raise ValueError("invalid FEN piece")
            if len(row) != 8:
                raise ValueError("FEN rank must have eight files")
            board.extend(row)
        if board.count("K") != 1 or board.count("k") != 1:
            raise ValueError("reference requires exactly one king per side")
        return Position(tuple(board), 1 if fields[1] == "w" else -1)


def center(square):
    return 7 - (abs(2 * (square % 8) - 7) + abs(2 * (square // 8) - 7)) // 2


def feature_vector(position):
    features = [0] * 16
    pawns = [[0] * 8 for _ in range(2)]
    bishops = [0, 0]
    for square, piece in enumerate(position.board):
        if piece == ".":
            continue
        color = 0 if piece.isupper() else 1
        sign = 1 if color == 0 else -1
        kind = PIECES.index(piece.upper())
        if kind < 5:
            features[kind] += sign
        features[5 + kind] += sign * center(square)
        if kind == 0:
            rank = square // 8 if color == 0 else 7 - square // 8
            features[11] += sign * (rank - 1)
            pawns[color][square % 8] += 1
        if kind == 2:
            bishops[color] += 1
    for color in range(2):
        sign = 1 if color == 0 else -1
        for file in range(8):
            n = pawns[color][file]
            features[12] += sign * max(0, n - 1)
            if (file == 0 or pawns[color][file - 1] == 0) and (
                file == 7 or pawns[color][file + 1] == 0
            ):
                features[13] += sign * n
        features[14] += sign * (bishops[color] >= 2)
    features[15] = position.side
    return features


def evaluate(position, weights=None):
    """Independent scalar polynomial, White perspective; does not clamp raw output."""
    w = weights if weights is not None else load_model()["evaluation"]["weights"]
    result = position.side * w[15]
    for color, sign in ((True, 1), (False, -1)):
        pieces = [(s, p.upper()) for s, p in enumerate(position.board)
                  if p != "." and p.isupper() == color]
        pawn_files = [sum(p == "P" and s % 8 == f for s, p in pieces) for f in range(8)]
        for square, piece in pieces:
            kind = PIECES.index(piece)
            result += sign * ((w[kind] if kind < 5 else 0) + w[kind + 5] * center(square))
            if piece == "P":
                relative_rank = square // 8 if color else 7 - square // 8
                result += sign * w[11] * (relative_rank - 1)
                file = square % 8
                if not any(pawn_files[f] for f in (file - 1, file + 1) if 0 <= f < 8):
                    result += sign * w[13]
        result += sign * w[12] * sum(n - 1 for n in pawn_files if n)
        result += sign * w[14] * (sum(p == "B" for _, p in pieces) >= 2)
    return result


def ordering_features(position, source, target, promotion=".", en_passant=False, weights=None):
    if not (0 <= source < 64 and 0 <= target < 64):
        raise ValueError("move square outside board")
    piece = position.board[source]
    if piece == "." or (piece.isupper() != (position.side == 1)):
        raise ValueError("source must contain a side-to-move piece")
    if promotion != "." and (piece.upper() != "P" or promotion.upper() not in "NBRQ"):
        raise ValueError("promotion requires pawn and N/B/R/Q piece")
    if en_passant and piece.upper() != "P":
        raise ValueError("en passant requires pawn")
    w = weights if weights is not None else load_model()["evaluation"]["weights"]

    def value(p):
        return 0 if p in ".Kk" else w[PIECES.index(p.upper())]

    victim = "p" if en_passant else position.board[target]
    if not en_passant and victim != "." and victim.isupper() == piece.isupper():
        raise ValueError("cannot capture own piece")
    return [value(victim), value(piece) if victim != "." else 0,
            value(promotion) - w[0] if promotion != "." else 0,
            center(target) - center(source),
            position.side * (target // 8 - source // 8) if piece.upper() == "P" else 0]


def ordering_score(position, source, target, promotion=".", en_passant=False, model=None):
    model = model if model is not None else load_model()
    features = ordering_features(position, source, target, promotion, en_passant,
                                 model["evaluation"]["weights"])
    return sum(a * b for a, b in zip(features, model["ordering"]["weights"]))


def accumulator_bound(model=None):
    """Conservative bound for <=64 pieces including exactly two kings.

    This includes arbitrary promoted material and pawns on end ranks. Search must
    clamp to its normal-evaluation band separately to avoid mate-score overlap.
    """
    model = model if model is not None else load_model()
    w, order = model["evaluation"]["weights"], model["ordering"]["weights"]
    piece_bounds = [abs(w[k]) + 6 * abs(w[5 + k]) for k in range(5)]
    piece_bounds[0] += 6 * abs(w[11]) + abs(w[12]) + abs(w[13])
    evaluation = 62 * max(piece_bounds) + 6 * abs(w[10]) + abs(w[14]) + abs(w[15])
    material = max(abs(v) for v in w[:5])
    promotion = max(abs(v - w[0]) for v in w[1:5])
    ordering = (material * (abs(order[0]) + abs(order[1])) + promotion * abs(order[2])
                + 6 * abs(order[3]) + 7 * abs(order[4]))
    return {"raw_evaluation_abs_max": evaluation, "ordering_abs_max": ordering,
            "accumulator": "signed-32", "safe": max(evaluation, ordering) < 2**31}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fen")
    parser.add_argument("--move", help="UCI coordinate move, optionally with promotion")
    parser.add_argument("--en-passant", action="store_true")
    args = parser.parse_args()
    position = Position.fen(args.fen)
    output = {"model": load_model()["id"], "raw_white_evaluation": evaluate(position),
              "features": feature_vector(position), "bounds": accumulator_bound()}
    if args.move:
        move = args.move
        if len(move) not in (4, 5) or any(move[i] not in "abcdefgh" for i in (0, 2)) or any(
            move[i] not in "12345678" for i in (1, 3)
        ):
            raise SystemExit("invalid coordinate move")
        source = ord(move[0]) - 97 + 8 * (int(move[1]) - 1)
        target = ord(move[2]) - 97 + 8 * (int(move[3]) - 1)
        promotion = move[4] if len(move) == 5 else "."
        output["ordering"] = ordering_score(position, source, target, promotion, args.en_passant)
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
