"""Verify this project's canonical standard-start opening PGN against UCI moves.

This is intentionally not a general PGN parser.  It independently renders the
format produced by openings.py using the in-repository legal-move oracle and
requires exact bytes in the same order.  A successful comparison binds the
one-based sequential game index to the bank; it does not authenticate the
file's producer, freeze its future contents or authorize a scored game.
"""
from __future__ import annotations

import re
import hashlib
import os
from pathlib import Path
import stat

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
_ECO = re.compile(r"[A-E][0-9]{2}\Z")
_MAX_PGN_BYTES = 1 << 20
_MAX_OPENINGS = 1000
# openings.py selects at most 16 plies from standard start.  In that bound
# neither the 100-halfmove rule nor insufficient material can be reached.
_MAX_PLIES = 16


def _san(board, text, rules):
    legal = list(board.legal_moves())
    matching = [move for move in legal if str(move) == text]
    if len(matching) != 1:
        raise ValueError("opening move is not an unambiguous legal UCI move")
    move = matching[0]
    piece = board.cells[move.src]
    kind = piece.lower()
    capture = board.cells[move.dst] != "." or (kind == "p" and move.src % 8 != move.dst % 8)
    if kind == "k" and abs(move.dst - move.src) == 2:
        san = "O-O" if move.dst > move.src else "O-O-O"
    else:
        san = "" if kind == "p" else piece.upper()
        if kind == "p":
            if capture:
                san += rules.coord(move.src)[0]
        else:
            rivals = [other for other in legal if other.src != move.src and other.dst == move.dst
                      and board.cells[other.src] == piece]
            if rivals:
                same_file = any(other.src % 8 == move.src % 8 for other in rivals)
                same_rank = any(other.src // 8 == move.src // 8 for other in rivals)
                source = rules.coord(move.src)
                san += source if same_file and same_rank else source[1] if same_file else source[0]
        san += ("x" if capture else "") + rules.coord(move.dst)
        if move.promotion:
            san += "=" + move.promotion.upper()
    after = board.apply(move)
    if after.in_check():
        san += "+" if any(after.legal_moves()) else "#"
    return san, after


def canonical(openings, rules):
    """Render canonical bank games from validated UCI moves, preserving order."""
    if type(openings) is not list or not 0 < len(openings) <= _MAX_OPENINGS:
        raise ValueError("bounded nonempty opening list required")
    games, names = [], set()
    for opening in openings:
        if type(opening) is not dict:
            raise ValueError("opening row must be an object")
        name, eco, moves = opening.get("id"), opening.get("eco"), opening.get("moves")
        if (type(name) is not str or _ID.fullmatch(name) is None or type(eco) is not str or
                _ECO.fullmatch(eco) is None or type(moves) not in (list, tuple) or
                not 0 < len(moves) <= _MAX_PLIES or any(type(move) is not str for move in moves)):
            raise ValueError("opening identifier, ECO or moves differ from canonical bank format")
        if name in names:
            raise ValueError("opening identifiers must be unique")
        names.add(name)
        board, tokens = rules.Board.from_fen(), []
        seen = {board.repetition_key(): 1}
        for index, move in enumerate(moves):
            if index % 2 == 0:
                tokens.append(str(index // 2 + 1) + ".")
            san, board = _san(board, move, rules)
            # Fastchess checks game-over *before* retaining each parsed move.
            # Reject any terminal prefix rather than claiming the full bank
            # is loaded when its last parsed move would in fact be dropped.
            key = board.repetition_key()
            seen[key] = seen.get(key, 0) + 1
            if seen[key] >= 3 or not any(board.legal_moves()):
                raise ValueError("Fastchess would stop before this terminal opening prefix")
            tokens.append(san)
        games.append(f'[Event "Rove4k {name}"]\n[ECO "{eco}"]\n[Result "*"]\n\n' +
                     " ".join(tokens) + " *\n")
    result = "\n".join(games).encode("ascii")
    if len(result) > _MAX_PGN_BYTES:
        raise ValueError("canonical opening PGN exceeds bounded size")
    return result


def validate(raw, openings, rules):
    """Require exact, unambiguous bytes for each one-based sequential entry."""
    if type(raw) is not bytes or not 0 < len(raw) <= _MAX_PGN_BYTES:
        raise ValueError("bounded canonical opening PGN bytes required")
    if raw != canonical(openings, rules):
        raise ValueError("opening PGN differs from the bank's ordered legal moves")


def _read_owned(path, maximum, expected_size=None):
    """Read a single-link regular file by no-follow dirfd on Linux only.

    The caller must first reject protected path names. No later pathname
    identity is implied; future consumers must separately freeze the file.
    """
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute opening input path required")
    if os.name == "posix" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"):
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
        directory, fd = os.open(path.anchor, flags | os.O_DIRECTORY), None
        try:
            for component in path.parts[1:-1]:
                child = os.open(component, flags | os.O_DIRECTORY, dir_fd=directory)
                os.close(directory)
                directory = child
            fd = os.open(path.name, flags, dir_fd=directory)
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                    not 0 < before.st_size <= maximum or
                    expected_size is not None and before.st_size != expected_size):
                raise ValueError("opening input must be a bounded ordinary single-link file")
            with os.fdopen(fd, "rb") as stream:
                fd = None
                raw = stream.read(maximum + 1)
                after = os.fstat(stream.fileno())
            current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            stamp = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
                                   value.st_size, value.st_mtime_ns, value.st_ctime_ns)
            if stamp(before) != stamp(after) or stamp(before) != stamp(current):
                raise ValueError("opening input identity changed during snapshot")
        finally:
            if fd is not None:
                os.close(fd)
            os.close(directory)
    else:
        raise RuntimeError("Linux no-follow opening input support is required")
    if len(raw) != before.st_size:
        raise ValueError("opening input snapshot length differs")
    return raw


def read_snapshot(path, pin):
    """Read a PGN snapshot and verify its bank length and SHA-256."""
    if (type(pin) is not dict or type(pin.get("bytes")) is not int or
            not 0 < pin["bytes"] <= _MAX_PGN_BYTES or type(pin.get("sha256")) is not str or
            re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]) is None):
        raise ValueError("bounded opening PGN pin required")
    raw = _read_owned(path, _MAX_PGN_BYTES, pin["bytes"])
    if len(raw) != pin["bytes"] or hashlib.sha256(raw).hexdigest() != pin["sha256"]:
        raise ValueError("opening PGN snapshot differs from its bank pin")
    return raw


def read_bank(path, expected_sha256):
    """Read a bank JSON snapshot against an independently supplied digest."""
    if type(expected_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValueError("independent opening bank SHA-256 required")
    raw = _read_owned(path, 32 << 20)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("opening bank snapshot differs from the supplied digest")
    return raw
