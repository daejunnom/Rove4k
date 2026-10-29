"""Reversible c4ke start-position edit-loop candidate.

The original loop's edit calls are reordered.  Equivalence requires the
unchanged startpos reset and empty-square initialization, distinct squares,
and the original edit's XOR updates.  No engine qualification is implied.
Pinned external inputs are supplied as bytes and are not stored in Git.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "startpos-loop-v1"
SOURCE_FILES = ("src/board.cpp", "src/chess.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
LOOP_NAME = b"rove_start_i"
PRECONDITION = (b"        *this = {};\r\n\r\n"
                b"        for (i32 i = 0; i < 64; i++)\r\n"
                b"            board[i] = PIECE_NONE;\r\n\r\n")
BEFORE = (
    b"        for (i32 i = 0; i < 8; i++)\r\n"
    b"            edit(i + A1, LAYOUT[i] * 2 + WHITE),\r\n"
    b"            edit(i + A8, LAYOUT[i] * 2 + BLACK),\r\n"
    b"            edit(i + A2, WHITE_PAWN),\r\n"
    b"            edit(i + A7, BLACK_PAWN);"
)
AFTER = (
    b"        for(i32 rove_start_i=0;rove_start_i<32;rove_start_i++) {\r\n"
    b"            edit(rove_start_i+rove_start_i/16*32,"
    b"LAYOUT[rove_start_i%8]*2*!(rove_start_i/8%3)+rove_start_i/16);\r\n"
    b"        }"
)
CONSTANTS = (b"#define A1 0", b"#define A2 8", b"#define A7 48", b"#define A8 56",
             b"#define WHITE 0", b"#define BLACK 1", b"#define WHITE_PAWN 0", b"#define BLACK_PAWN 1")
LAYOUT = b"LAYOUT[] { ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK }"


def transform(sources):
    if type(sources) is not dict or set(sources) != set(SOURCE_FILES):
        raise ValueError("c4ke source closure differs")
    if any(type(data) is not bytes for data in sources.values()):
        raise ValueError("source must be immutable bytes")
    for path, data in sources.items():
        peers.verify_blob("c4ke", path, data)
        if LOOP_NAME in data:
            raise ValueError("candidate loop name already exists")
    if (sources["src/board.cpp"].count(PRECONDITION + BEFORE) != 1
            or any(sources["src/chess.cpp"].count(constant) != 1 for constant in CONSTANTS)
            or sources["src/eval.cpp"].count(LAYOUT) != 1):
        raise ValueError("startpos precondition, constants or layout differ")
    outputs, proofs = {}, {}
    for path in SOURCE_FILES:
        edits = [("startpos-loop", BEFORE, AFTER)] if path == "src/board.cpp" else []
        outputs[path], proofs[path] = peers.exact_edits(sources[path], edits)
    return outputs, {"format": "c4ke-startpos-loop-v1", "variant": VARIANT,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-startpos-loop-v1"
            or receipt.get("variant") != VARIANT
            or receipt.get("revision") != peers.peer_spec("c4ke").revision
            or type(receipt.get("files")) is not dict
            or set(receipt["files"]) != set(SOURCE_FILES)
            or type(outputs) is not dict or set(outputs) != set(SOURCE_FILES)):
        raise ValueError("c4ke startpos receipt identity or closure differs")
    try:
        original = {path: peers.restore_resources(outputs[path], receipt["files"][path])
                    for path in SOURCE_FILES}
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid c4ke startpos receipt") from error
    candidate, regenerated = transform(original)
    if candidate != outputs or regenerated != receipt:
        raise ValueError("c4ke startpos receipt does not reproduce candidate")
    return original
