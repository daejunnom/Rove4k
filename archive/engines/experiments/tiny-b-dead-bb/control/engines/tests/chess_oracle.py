"""Small independent rules oracle for subprocess tests, never imported by engines.

The intentionally plain 64-square representation recomputes attacks and copies
the board for every legal-move check. It is a correctness oracle, not a searcher.
Standard-chess positions only; FEN input must contain one king of each colour.
"""

from dataclasses import dataclass


START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FILES = "abcdefgh"
KNIGHT = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
KING = tuple((x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if x or y)
DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
STRAIGHT = ((1, 0), (-1, 0), (0, 1), (0, -1))


def square(name):
    return FILES.index(name[0]) + 8 * (int(name[1]) - 1)


def coord(index):
    return FILES[index % 8] + str(index // 8 + 1)


def white(piece):
    return piece.isupper()


@dataclass(frozen=True)
class Move:
    src: int
    dst: int
    promotion: str = ""

    def __str__(self):
        return coord(self.src) + coord(self.dst) + self.promotion


@dataclass
class Board:
    cells: list
    turn: bool
    castling: str
    ep: int
    halfmove: int
    fullmove: int

    @classmethod
    def from_fen(cls, fen=START):
        fields = fen.split()
        if len(fields) != 6:
            raise ValueError("FEN requires six fields")
        cells = ["."] * 64
        rows = fields[0].split("/")
        if len(rows) != 8:
            raise ValueError("FEN requires eight ranks")
        for row, data in enumerate(rows):
            file = 0
            for char in data:
                if char.isdigit():
                    file += int(char)
                elif char in "pnbrqkPNBRQK" and file < 8:
                    cells[(7 - row) * 8 + file] = char
                    file += 1
                else:
                    raise ValueError("Invalid FEN placement")
            if file != 8:
                raise ValueError("Invalid FEN rank width")
        if cells.count("K") != 1 or cells.count("k") != 1:
            raise ValueError("FEN requires exactly one king per colour")
        return cls(cells, fields[1] == "w", fields[2].replace("-", ""),
                   -1 if fields[3] == "-" else square(fields[3]), int(fields[4]), int(fields[5]))

    def fen(self):
        rows = []
        for rank in range(7, -1, -1):
            row, empty = "", 0
            for piece in self.cells[rank * 8:rank * 8 + 8]:
                if piece == ".":
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += piece
            rows.append(row + (str(empty) if empty else ""))
        return ("/".join(rows) + (" w " if self.turn else " b ")
                + (self.castling or "-") + " " + (coord(self.ep) if self.ep >= 0 else "-")
                + f" {self.halfmove} {self.fullmove}")

    def attacked(self, target, by_white):
        tx, ty = target % 8, target // 8
        pawn = "P" if by_white else "p"
        source_y = ty - (1 if by_white else -1)
        if 0 <= source_y < 8:
            for x in (tx - 1, tx + 1):
                if 0 <= x < 8 and self.cells[source_y * 8 + x] == pawn:
                    return True
        for deltas, kind in ((KNIGHT, "n"), (KING, "k")):
            for dx, dy in deltas:
                x, y = tx + dx, ty + dy
                if 0 <= x < 8 and 0 <= y < 8:
                    piece = self.cells[y * 8 + x]
                    if piece.lower() == kind and white(piece) == by_white:
                        return True
        for deltas, kinds in ((DIAGONAL, "bq"), (STRAIGHT, "rq")):
            for dx, dy in deltas:
                x, y = tx + dx, ty + dy
                while 0 <= x < 8 and 0 <= y < 8:
                    piece = self.cells[y * 8 + x]
                    if piece != ".":
                        if piece.lower() in kinds and white(piece) == by_white:
                            return True
                        break
                    x, y = x + dx, y + dy
        return False

    def in_check(self, colour=None):
        colour = self.turn if colour is None else colour
        return self.attacked(self.cells.index("K" if colour else "k"), not colour)

    def pseudo_moves(self):
        for src, piece in enumerate(self.cells):
            if piece == "." or white(piece) != self.turn:
                continue
            x, y, kind = src % 8, src // 8, piece.lower()
            if kind == "p":
                direction = 1 if self.turn else -1
                ny = y + direction
                if not 0 <= ny < 8:
                    continue
                if self.cells[ny * 8 + x] == ".":
                    for promotion in ("qrbn" if ny in (0, 7) else ("",)):
                        yield Move(src, ny * 8 + x, promotion)
                    nny = y + 2 * direction
                    if y == (1 if self.turn else 6) and self.cells[nny * 8 + x] == ".":
                        yield Move(src, nny * 8 + x)
                for nx in (x - 1, x + 1):
                    if not 0 <= nx < 8:
                        continue
                    dst = ny * 8 + nx
                    capture = self.cells[dst]
                    ep_pawn = self.cells[dst - 8 * direction]
                    if (capture != "." and white(capture) != self.turn and capture.lower() != "k") or (
                            dst == self.ep and capture == "." and ep_pawn == ("p" if self.turn else "P")):
                        for promotion in ("qrbn" if ny in (0, 7) else ("",)):
                            yield Move(src, dst, promotion)
                continue
            sliding = kind in "brq"
            deltas = (KNIGHT if kind == "n" else KING if kind == "k" else
                      DIAGONAL if kind == "b" else STRAIGHT if kind == "r" else DIAGONAL + STRAIGHT)
            for dx, dy in deltas:
                nx, ny = x + dx, y + dy
                while 0 <= nx < 8 and 0 <= ny < 8:
                    dst, capture = ny * 8 + nx, self.cells[ny * 8 + nx]
                    if capture == "." or (white(capture) != self.turn and capture.lower() != "k"):
                        yield Move(src, dst)
                    if capture != "." or not sliding:
                        break
                    nx, ny = nx + dx, ny + dy
            if kind == "k" and src == (4 if self.turn else 60) and not self.in_check():
                base = 0 if self.turn else 56
                for right, rook, free, through, target in (
                        ("K" if self.turn else "k", 7, (5, 6), (5, 6), 6),
                        ("Q" if self.turn else "q", 0, (1, 2, 3), (3, 2), 2)):
                    if (right in self.castling and self.cells[base + rook] == ("R" if self.turn else "r")
                            and all(self.cells[base + f] == "." for f in free)
                            and all(not self.attacked(base + f, not self.turn) for f in through)):
                        yield Move(src, base + target)

    def apply(self, move):
        """Apply an already validated move; legal_moves performs validation."""
        cells = self.cells.copy()
        piece, captured = cells[move.src], cells[move.dst]
        old_ep, rights = self.ep, self.castling
        ep = -1
        if piece.lower() == "p":
            if move.dst == old_ep and captured == "." and move.src % 8 != move.dst % 8:
                cells[move.dst - (8 if self.turn else -8)] = "."
                captured = "p" if self.turn else "P"
            if abs(move.dst - move.src) == 16:
                ep = (move.src + move.dst) // 2
        cells[move.src], cells[move.dst] = ".", piece
        if move.promotion:
            cells[move.dst] = move.promotion.upper() if self.turn else move.promotion
        if piece.lower() == "k":
            rights = "".join(c for c in rights if c not in ("KQ" if self.turn else "kq"))
            if abs(move.dst - move.src) == 2:
                rook_src = move.src + (3 if move.dst > move.src else -4)
                rook_dst = (move.src + move.dst) // 2
                cells[rook_dst], cells[rook_src] = cells[rook_src], "."
        for sq, right in ((0, "Q"), (7, "K"), (56, "q"), (63, "k")):
            if move.src == sq or move.dst == sq:
                rights = rights.replace(right, "")
        return Board(cells, not self.turn, rights, ep,
                     0 if captured != "." or piece.lower() == "p" else self.halfmove + 1,
                     self.fullmove + (not self.turn))

    def legal_moves(self):
        for move in self.pseudo_moves():
            result = self.apply(move)
            if not result.in_check(self.turn):
                yield move

    def play(self, uci):
        for move in self.legal_moves():
            if str(move) == uci:
                return self.apply(move)
        raise ValueError(f"Illegal move {uci} in {self.fen()}")

    def repetition_key(self):
        # FIDE identity includes EP only if a legal EP capture is available.
        ep = self.ep if any(m.dst == self.ep and self.cells[m.src].lower() == "p"
                            and m.src % 8 != m.dst % 8 for m in self.legal_moves()) else -1
        return tuple(self.cells), self.turn, self.castling, ep

    def perft(self, depth):
        if depth == 0:
            return 1
        moves = list(self.legal_moves())
        if depth == 1:
            return len(moves)
        return sum(self.apply(move).perft(depth - 1) for move in moves)


# FENs are the standard positions in official-stockfish/Stockfish/tests/perft.sh.
# Low-depth expected totals are frozen reference values, not engine output.
PERFT = (
    ("startpos", START, (20, 400, 8902, 197281)),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", (48, 2039, 97862)),
    ("rook-ep", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", (14, 191, 2812, 43238)),
    ("promotion-castle", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", (6, 264, 9467)),
    ("underpromotion", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", (44, 1486, 62379)),
    ("pins", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", (46, 2079, 89890)),
)


def self_check(deep=False):
    checked = []
    for label, fen, totals in PERFT:
        maximum = len(totals) if deep else 2
        board = Board.from_fen(fen)
        assert board.fen() == fen
        for depth, expected in enumerate(totals[:maximum], 1):
            actual = board.perft(depth)
            assert actual == expected, (label, depth, actual, expected)
            checked.append((label, depth, actual))
    return checked
