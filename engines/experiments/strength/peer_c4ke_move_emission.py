"""Unmeasured reversible c4ke move-emission sharing experiment.

The caller supplies the five pinned upstream files as bytes. The four pawn
offsets are nonzero, so zero selects fixed-origin, non-promotion emission.
This changes neither TT allocation nor engine resource policy. It does not
produce a submission or establish whole-engine behavioral equivalence.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "move-emission-v1"
SOURCE_FILES = ("src/board.cpp", "src/chess.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
NAME = b"rove_emit_from"
PAWN_CALLS = (
    b"add_pawn_moves(list, pawns_push, stm ? -8 : 8);",
    b"add_pawn_moves(list, (stm ? south(pawns_push & 0xff0000000000) : north(pawns_push & 0xff0000)) & ~occupied, stm ? -16 : 16);",
    b"add_pawn_moves(list, (stm ? se(pawns) : nw(pawns)) & pawns_targets, stm ? -7 : 7);",
    b"add_pawn_moves(list, (stm ? sw(pawns) : ne(pawns)) & pawns_targets, stm ? -9 : 9);",
)
PAWN_BEFORE = (
    b"null add_pawn_moves(i16*& list, u64 targets, i32 offset) {\r\n"
    b"        for (; targets;) {\r\n"
    b"            i32 to = LSB(targets);\r\n"
    b"            targets &= targets - 1;\r\n\r\n"
    b"            *list++ = move_make(to - offset, to, (to < 8 || to > 55) * QUEEN);\r\n"
    b"        }\r\n"
    b"    }"
)
PAWN_AFTER = (
    b"null add_pawn_moves(i16*& list, u64 targets, i32 offset, i32 rove_emit_from = 0) {\r\n"
    b"        for (; targets;) {\r\n"
    b"            i32 to = LSB(targets);\r\n"
    b"            targets &= targets - 1;\r\n\r\n"
    b"            *list++ = move_make(offset ? to - offset : rove_emit_from, to, "
    b"offset && (to < 8 || to > 55) ? QUEEN : PAWN);\r\n"
    b"        }\r\n"
    b"    }"
)
PIECE_BEFORE = (
    b"for (; attacks;) {\r\n"
    b"                i32 to = LSB(attacks);\r\n"
    b"                attacks &= attacks - 1;\r\n\r\n"
    b"                *list++ = move_make(from, to);\r\n"
    b"            }"
)
PIECE_AFTER = b"add_pawn_moves(list, attacks, 0, from);"
CONSTANTS = (b"#define PAWN 0", b"#define QUEEN 4",
             b"i16 move_make(i32 from, i32 to, i32 promo = PAWN)")


def transform(sources):
    if type(sources) is not dict or set(sources) != set(SOURCE_FILES):
        raise ValueError("c4ke source closure differs")
    if any(type(data) is not bytes for data in sources.values()):
        raise ValueError("source must be immutable bytes")
    for path, data in sources.items():
        peers.verify_blob("c4ke", path, data)
        if NAME in data:
            raise ValueError("candidate name already exists")
    board, chess = sources["src/board.cpp"], sources["src/chess.cpp"]
    if (board.count(b"add_pawn_moves(") != 5
            or any(board.count(call) != 1 for call in PAWN_CALLS)
            or any(chess.count(constant) != 1 for constant in CONSTANTS)):
        raise ValueError("pawn offsets or move encoding preconditions differ")
    outputs, proofs = {}, {}
    for path in SOURCE_FILES:
        edits = [("pawn-emitter", PAWN_BEFORE, PAWN_AFTER),
                 ("piece-emitter", PIECE_BEFORE, PIECE_AFTER)] if path == "src/board.cpp" else []
        outputs[path], proofs[path] = peers.exact_edits(sources[path], edits)
    return outputs, {"format": "c4ke-move-emission-v1", "variant": VARIANT,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-move-emission-v1"
            or receipt.get("variant") != VARIANT
            or receipt.get("revision") != peers.peer_spec("c4ke").revision
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(SOURCE_FILES)
            or type(outputs) is not dict or set(outputs) != set(SOURCE_FILES)):
        raise ValueError("c4ke move-emission receipt identity or closure differs")
    try:
        original = {path: peers.restore_resources(outputs[path], receipt["files"][path])
                    for path in SOURCE_FILES}
        rebuilt, proof = transform(original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke move-emission receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke move-emission receipt does not reproduce candidate")
    return original
