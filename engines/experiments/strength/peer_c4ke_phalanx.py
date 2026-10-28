"""Reversible, unmeasured c4ke pawn-phalanx simplification.

The caller supplies pinned upstream source bytes; no peer source is stored here.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "phalanx-v1"
PATHS = ("src/chess.cpp", "src/board.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
_START = b"        for (i32 color = WHITE; color < 2; color++) {"
_BEFORE = b"if (west(pawns_us) & pawns_us & 1ull << square)"
_AFTER = b"if (west(pawns_us) & 1ull << square)"
# Pins the complete loop context through the expression, including initialization,
# iteration, square selection, mask updates, and the pawn-only branch.
_CONTEXT_SHA256 = "70b13a6e76dfb0fc8eaf65b8e6d23bcd27726242f00055c7616e42516cee7986"
_DEFINITIONS = (b"#define PAWN 0\r\n", b"#define LSB countr_zero\r\n")


def edit_specs(variant):
    if variant != VARIANT:
        raise ValueError("unknown c4ke phalanx variant")
    return {path: (("phalanx", _BEFORE, _AFTER, 1),) if path == "src/board.cpp" else ()
            for path in PATHS}


def transform(variant, sources):
    specs = edit_specs(variant)
    if type(sources) is not dict or set(sources) != set(PATHS):
        raise ValueError("c4ke phalanx input closure differs")
    for path in PATHS:
        if type(sources[path]) is not bytes:
            raise ValueError("source must be immutable bytes")
        peers.verify_blob("c4ke", path, sources[path])
    chess, board = sources["src/chess.cpp"], sources["src/board.cpp"]
    if any(chess.count(definition) != 1 for definition in _DEFINITIONS):
        raise ValueError("c4ke phalanx definitions differ")
    if board.count(_START) != 1 or board.count(_BEFORE) != 1:
        raise ValueError("c4ke phalanx loop markers differ")
    start, end = board.index(_START), board.index(_BEFORE) + len(_BEFORE)
    if end <= start or peers.sha(board[start:end]) != _CONTEXT_SHA256:
        raise ValueError("c4ke phalanx loop context differs")
    outputs, proofs = {}, {}
    for path, edits in specs.items():
        outputs[path], proofs[path] = peers.exact_edits(
            sources[path], [(role, before, after) for role, before, after, _ in edits])
    return outputs, {"format": "c4ke-phalanx-v1", "variant": variant,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-phalanx-v1"
            or receipt.get("revision") != peers.peer_spec("c4ke").revision):
        raise ValueError("c4ke phalanx receipt identity differs")
    specs = edit_specs(receipt.get("variant"))
    if (type(outputs) is not dict or set(outputs) != set(specs)
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(specs)):
        raise ValueError("c4ke phalanx output closure differs")
    try:
        original = {path: peers.restore_resources(value, receipt["files"][path])
                    for path, value in outputs.items()}
        rebuilt, proof = transform(receipt["variant"], original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke phalanx receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke phalanx receipt does not reproduce candidate")
    return original
