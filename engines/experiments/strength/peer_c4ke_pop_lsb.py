"""Unmeasured reversible sharing of four pinned c4ke bitboard pop loops.

Caller supplies original source bytes; no upstream source is stored here. This
is an isolated experiment, not a producer, CI, or submission integration.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "pop-lsb-v1"
PATHS = ("src/chess.cpp", "src/board.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
NAMES = (b"rove_pop", b"rove_pop_bits", b"rove_pop_sq")
HELPER = (b"i32 rove_pop(u64& rove_pop_bits){i32 rove_pop_sq=LSB(rove_pop_bits);"
          b"rove_pop_bits&=rove_pop_bits-1;return rove_pop_sq;}")
ANCHOR = b'#include "eval.cpp"\r\n\r\nstruct Board {'
ANCHOR_NEW = b'#include "eval.cpp"\r\n\r\n' + HELPER + b'\r\n\r\nstruct Board {'
DEFINITIONS = (b"using u64 = uint64_t;\r\n", b"using i32 = int;\r\n", b"#define LSB countr_zero\r\n")

# Each match includes its nonzero loop guard and is checked exactly once. Both
# assignments in each replacement remain sequenced before the loop body.
SITES = (
    ("pawn-targets", b"for (; targets;) {\r\n            i32 to = LSB(targets);\r\n            targets &= targets - 1;",
     b"for (; targets;) {\r\n            i32 to = rove_pop(targets);"),
    ("piece-mask", b"for (; mask;) {\r\n            i32 from = LSB(mask);\r\n            mask &= mask - 1;",
     b"for (; mask;) {\r\n            i32 from = rove_pop(mask);"),
    ("piece-attacks", b"for (; attacks;) {\r\n                i32 to = LSB(attacks);\r\n                attacks &= attacks - 1;",
     b"for (; attacks;) {\r\n                i32 to = rove_pop(attacks);"),
    ("eval-mask", b"for (; mask;) {\r\n                    i32 square = LSB(mask);\r\n                    mask &= mask - 1;",
     b"for (; mask;) {\r\n                    i32 square = rove_pop(mask);"),
)


def transform(sources):
    if type(sources) is not dict or set(sources) != set(PATHS):
        raise ValueError("c4ke pop input closure differs")
    for path in PATHS:
        data = sources[path]
        if type(data) is not bytes:
            raise ValueError("source must be immutable bytes")
        peers.verify_blob("c4ke", path, data)
        if any(name in data for name in NAMES):
            raise ValueError("c4ke pop helper name already exists")
    if any(sources["src/chess.cpp"].count(item) != 1 for item in DEFINITIONS):
        raise ValueError("c4ke pop definitions differ")
    edits = [("helper", ANCHOR, ANCHOR_NEW), *SITES]
    if any(sources["src/board.cpp"].count(before) != 1 for _, before, _ in edits):
        raise ValueError("c4ke pop loop context differs")
    outputs, proofs = {}, {}
    for path in PATHS:
        outputs[path], proofs[path] = peers.exact_edits(
            sources[path], edits if path == "src/board.cpp" else [])
    return outputs, {"format": "c4ke-pop-lsb-v1", "variant": VARIANT,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-pop-lsb-v1"
            or receipt.get("variant") != VARIANT
            or receipt.get("revision") != peers.peer_spec("c4ke").revision
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(PATHS)
            or type(outputs) is not dict or set(outputs) != set(PATHS)):
        raise ValueError("c4ke pop receipt identity or closure differs")
    try:
        original = {path: peers.restore_resources(outputs[path], receipt["files"][path]) for path in PATHS}
        rebuilt, proof = transform(original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke pop receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke pop receipt does not reproduce candidate")
    return original
