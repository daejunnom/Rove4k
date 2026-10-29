"""Reversible, unmeasured c4ke castling expression experiment.

Inputs are pinned upstream bytes supplied by the caller and stay outside Git.
The TT allocation, probe, store and prefetch are outside this edit. This
module alone does not produce an exact-P192 candidate or qualify an engine.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANTS = ("castle-or-v1",)

_CASTLE_BEFORE = (
    b"if (from == H1 || to == H1) castled |= CASTLED_WK;\r\n"
    b"        if (from == A1 || to == A1) castled |= CASTLED_WQ;\r\n"
    b"        if (from == H8 || to == H8) castled |= CASTLED_BK;\r\n"
    b"        if (from == A8 || to == A8) castled |= CASTLED_BQ;"
)
_CASTLE_AFTER = (
    b"castled |= (from==H1||to==H1)*CASTLED_WK"
    b"|(from==A1||to==A1)*CASTLED_WQ"
    b"|(from==H8||to==H8)*CASTLED_BK"
    b"|(from==A8||to==A8)*CASTLED_BQ;"
)


def edit_specs(variant):
    """Return exact edits and pin the constants' untouched defining source."""
    if variant not in VARIANTS:
        raise ValueError("unknown c4ke structural variant")
    return {"src/board.cpp": (("castle-or", _CASTLE_BEFORE, _CASTLE_AFTER, 1),),
            "src/chess.cpp": ()}


def transform(variant, sources):
    specs = edit_specs(variant)
    if type(sources) is not dict or set(sources) != set(specs):
        raise ValueError("c4ke structural input closure differs")
    outputs, proofs = {}, {}
    for path, edits in specs.items():
        if type(sources[path]) is not bytes:
            raise ValueError("source must be immutable bytes")
        peers.verify_blob("c4ke", path, sources[path])
        outputs[path], proofs[path] = peers.exact_edits(
            sources[path], [(role, before, after) for role, before, after, _ in edits])
    return outputs, {"format": "c4ke-structural-v1", "variant": variant,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-structural-v1"
            or receipt.get("revision") != peers.peer_spec("c4ke").revision):
        raise ValueError("c4ke structural receipt identity differs")
    specs = edit_specs(receipt.get("variant"))
    if (type(outputs) is not dict or set(outputs) != set(specs)
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(specs)):
        raise ValueError("c4ke structural output closure differs")
    try:
        original = {path: peers.restore_resources(value, receipt["files"][path])
                    for path, value in outputs.items()}
        rebuilt, proof = transform(receipt["variant"], original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke structural receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke structural receipt does not reproduce candidate")
    return original
