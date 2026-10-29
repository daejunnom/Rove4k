"""Reversible c4ke en-passant hash cancellation experiment.

Pinned upstream sources are supplied by the caller and stay outside Git.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "ep-hash-v1"
PATHS = ("src/chess.cpp", "src/board.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
_BEFORE = (
    b"hash ^= KEYS[PIECE_NONE][enpassant];\r\n\r\n"
    b"        if (piece < WHITE_KNIGHT && to == enpassant)\r\n"
    b"            edit(to ^ 8, PIECE_NONE),\r\n"
    b"            hash ^= KEYS[PIECE_NONE][enpassant];"
)
_AFTER = (
    b"if (piece < WHITE_KNIGHT && to == enpassant)\r\n"
    b"            edit(to ^ 8, PIECE_NONE);\r\n"
    b"        else\r\n"
    b"            hash ^= KEYS[PIECE_NONE][enpassant];"
)
_EDIT_START = b"    null edit(i32 square, i32 piece) {"
_EDIT_END = b"    u64 attackers(u64 mask) {"
_MAKE_START = b"    u64 make(i32 move) {"
_MAKE_END = b"        // Castling"
_EDIT_SHA = "07c3038a9bbb6b1105ccf05953affce7173cf0846981c554f828b58cecede186"
_MAKE_SHA = "85917cbebfe3c8ae0533a509042a8dde95ce7412f113499dd32d6a1233c9e068"


def edit_specs(variant):
    if variant != VARIANT:
        raise ValueError("unknown c4ke ep hash variant")
    return {path: (("ep-hash", _BEFORE, _AFTER, 1),) if path == "src/board.cpp" else ()
            for path in PATHS}


def _context(board, start, end, expected):
    if board.count(start) != 1:
        raise ValueError("c4ke ep hash context start differs")
    first = board.index(start)
    last = board.find(end, first + len(start))
    if last < 0 or peers.sha(board[first:last]) != expected:
        raise ValueError("c4ke ep hash context differs")


def transform(variant, sources):
    specs = edit_specs(variant)
    if type(sources) is not dict or set(sources) != set(PATHS):
        raise ValueError("c4ke ep hash input closure differs")
    for path in PATHS:
        if type(sources[path]) is not bytes:
            raise ValueError("source must be immutable bytes")
        peers.verify_blob("c4ke", path, sources[path])
    board = sources["src/board.cpp"]
    _context(board, _EDIT_START, _EDIT_END, _EDIT_SHA)
    _context(board, _MAKE_START, _MAKE_END, _MAKE_SHA)
    outputs, proofs = {}, {}
    for path, edits in specs.items():
        outputs[path], proofs[path] = peers.exact_edits(
            sources[path], [(role, before, after) for role, before, after, _ in edits])
    return outputs, {"format": "c4ke-ep-hash-v1", "variant": variant,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-ep-hash-v1"
            or receipt.get("revision") != peers.peer_spec("c4ke").revision):
        raise ValueError("c4ke ep hash receipt identity differs")
    specs = edit_specs(receipt.get("variant"))
    if (type(outputs) is not dict or set(outputs) != set(specs)
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(specs)):
        raise ValueError("c4ke ep hash output closure differs")
    try:
        original = {path: peers.restore_resources(value, receipt["files"][path])
                    for path, value in outputs.items()}
        rebuilt, proof = transform(receipt["variant"], original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke ep hash receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke ep hash receipt does not reproduce candidate")
    return original
