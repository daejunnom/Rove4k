"""Reversible, unmeasured ice4 source experiments for a separate CI batch.

Upstream source remains external. These edits do not change TT allocation or
indexing and do not establish runtime, compression, or tournament eligibility.
The consumer must compose them with the exact-P192 edits before minification.
"""
try:
    from . import peers
except ImportError:
    import peers

_CASTLE_BEFORE = (
    b'if (mv.from == A1 || mv.to == A1) {\n'
    b'            castle_rights |= WHITE_LONG_CASTLE;\n'
    b'        }\n'
    b'        if (mv.from == H1 || mv.to == H1) {\n'
    b'            castle_rights |= WHITE_SHORT_CASTLE;\n'
    b'        }\n'
    b'        if (mv.from == A8 || mv.to == A8) {\n'
    b'            castle_rights |= BLACK_LONG_CASTLE;\n'
    b'        }\n'
    b'        if (mv.from == H8 || mv.to == H8) {\n'
    b'            castle_rights |= BLACK_SHORT_CASTLE;\n'
    b'        }'
)
_CASTLE_AFTER = (b'for(int i=0;i<4;i++){int s=A1+7*(i&1)+70*(i>>1);'
                 b'if(mv.from==s||mv.to==s){castle_rights|=(2>>(i&1))<<(2*(i>>1));}}')
_ZOBRIST_BEFORE = b'fread(&ZOBRIST, sizeof(ZOBRIST), 1, fopen("/dev/urandom", "r"));'
_ZOBRIST_AFTER = b'fread(ZOBRIST, sizeof ZOBRIST, 1, fopen("/dev/urandom", "r"));'

VARIANTS = ("castle-v1", "zobrist-v1", "castle-zobrist-v1")


def edit_specs(variant):
    """Return exact non-overlapping edits; empty entries pin reviewed context."""
    if variant not in VARIANTS:
        raise ValueError("unknown ice4 structural variant")
    edits = {}
    if variant in ("castle-v1", "castle-zobrist-v1"):
        edits["src/board.cpp"] = (("castle-loop", _CASTLE_BEFORE, _CASTLE_AFTER, 1),)
        edits["src/consts.cpp"] = ()
    if variant in ("zobrist-v1", "castle-zobrist-v1"):
        edits["src/tables.cpp"] = (("zobrist-array-address", _ZOBRIST_BEFORE, _ZOBRIST_AFTER, 1),)
    return edits


def transform(variant, sources):
    """Transform pinned upstream inputs and produce a fully reversible receipt."""
    specs = edit_specs(variant)
    if set(sources) != set(specs):
        raise ValueError("ice4 structural input closure differs")
    outputs, proofs = {}, {}
    for path, edits in specs.items():
        peers.verify_blob("ice4", path, sources[path])
        outputs[path], proofs[path] = peers.exact_edits(
            sources[path], [(role, before, after) for role, before, after, _ in edits])
    return outputs, {"format": "ice4-structural-v1", "variant": variant,
                     "revision": peers.peer_spec("ice4").revision, "files": proofs}


def restore(outputs, receipt):
    if (receipt.get("format") != "ice4-structural-v1" or
            receipt.get("revision") != peers.peer_spec("ice4").revision):
        raise ValueError("ice4 structural receipt identity differs")
    variant = receipt.get("variant")
    if set(outputs) != set(edit_specs(variant)) or set(receipt.get("files", {})) != set(outputs):
        raise ValueError("ice4 structural output closure differs")
    original = {path: peers.restore_resources(value, receipt["files"][path])
                for path, value in outputs.items()}
    rebuilt, proof = transform(variant, original)
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("ice4 structural receipt does not reproduce candidate")
    return original
