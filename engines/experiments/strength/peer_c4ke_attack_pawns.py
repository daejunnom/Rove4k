"""Unmeasured reversible c4ke pawn-attacker term sharing experiment.

Five pinned upstream source files are provided as bytes by the caller. The
direction implementations are pinned because this rewrite composes their
horizontal operations before north/south shifts. TT and resources are untouched.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "attack-pawns-v1"
SOURCE_FILES = ("src/board.cpp", "src/chess.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
NAME = b"rove_pawn_lateral"
DIRECTIONS = (
    b"u64 north(u64 bitboard) {\r\n    return bitboard << 8;\r\n}",
    b"u64 south(u64 bitboard) {\r\n    return bitboard >> 8;\r\n}",
    b"u64 west(u64 bitboard) {\r\n    return bitboard >> 1 & ~0x8080808080808080;\r\n}",
    b"u64 east(u64 bitboard) {\r\n    return bitboard << 1 & ~0x101010101010101;\r\n}",
    b"u64 nw(u64 bitboard) {\r\n    return north(west(bitboard));\r\n}",
    b"u64 ne(u64 bitboard) {\r\n    return north(east(bitboard));\r\n}",
    b"u64 sw(u64 bitboard) {\r\n    return south(west(bitboard));\r\n}",
    b"u64 se(u64 bitboard) {\r\n    return south(east(bitboard));\r\n}",
)
CONSTANTS = (b"using u64 = uint64_t;", b"#define PAWN 0", b"#define WHITE 0", b"#define BLACK 1")
BEFORE = (
    b"return\r\n"
    b"            (nw(mask) | ne(mask)) & pieces[PAWN] & colors[BLACK] |\r\n"
    b"            (sw(mask) | se(mask)) & pieces[PAWN] & colors[WHITE]"
)
AFTER = (
    b"u64 rove_pawn_lateral = west(mask) | east(mask);\r\n"
    b"        return\r\n"
    b"            ((rove_pawn_lateral << 8 & colors[BLACK]) | "
    b"(rove_pawn_lateral >> 8 & colors[WHITE])) & pieces[PAWN]"
)


def transform(sources):
    if type(sources) is not dict or set(sources) != set(SOURCE_FILES):
        raise ValueError("c4ke source closure differs")
    if any(type(data) is not bytes for data in sources.values()):
        raise ValueError("source must be immutable bytes")
    for path, data in sources.items():
        peers.verify_blob("c4ke", path, data)
        if NAME in data:
            raise ValueError("candidate name already exists")
    if any(sources["src/chess.cpp"].count(fragment) != 1 for fragment in DIRECTIONS + CONSTANTS):
        raise ValueError("pawn direction or type preconditions differ")
    outputs, proofs = {}, {}
    for path in SOURCE_FILES:
        edits = [("pawn-attackers", BEFORE, AFTER)] if path == "src/board.cpp" else []
        outputs[path], proofs[path] = peers.exact_edits(sources[path], edits)
    return outputs, {"format": "c4ke-attack-pawns-v1", "variant": VARIANT,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-attack-pawns-v1"
            or receipt.get("variant") != VARIANT
            or receipt.get("revision") != peers.peer_spec("c4ke").revision
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(SOURCE_FILES)
            or type(outputs) is not dict or set(outputs) != set(SOURCE_FILES)):
        raise ValueError("c4ke pawn-attacker receipt identity or closure differs")
    try:
        original = {path: peers.restore_resources(outputs[path], receipt["files"][path])
                    for path in SOURCE_FILES}
        rebuilt, proof = transform(original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke pawn-attacker receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke pawn-attacker receipt does not reproduce candidate")
    return original
