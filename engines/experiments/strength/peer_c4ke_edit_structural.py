"""Independent, unmeasured c4ke Board::edit loop experiment.

Caller supplies pinned upstream bytes in memory. This does not create a P192
artifact, run an engine, or establish size, strength or runtime qualification.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "edit-loop-v1"
_EDIT_BEFORE = (
    b"        // Remove any pieces that exist in this square\r\n"
    b"        if (board[square] < PIECE_NONE)\r\n"
    b"            pieces[board[square] / 2] ^= 1ull << square,\r\n"
    b"            colors[board[square] % 2] ^= 1ull << square,\r\n\r\n"
    b"            hash ^= KEYS[board[square]][square],\r\n"
    b"            (board[square] < WHITE_KNIGHT ? hash_pawn : hash_non_pawn[board[square] % 2]) ^= KEYS[board[square]][square];\r\n\r\n"
    b"        // Place new piece\r\n"
    b"        if (piece < PIECE_NONE)\r\n"
    b"            pieces[piece / 2] ^= 1ull << square,\r\n"
    b"            colors[piece % 2] ^= 1ull << square,\r\n\r\n"
    b"            hash ^= KEYS[piece][square],\r\n"
    b"            (piece < WHITE_KNIGHT ? hash_pawn : hash_non_pawn[piece % 2]) ^= KEYS[piece][square];\r\n\r\n"
)
_EDIT_AFTER = (
    b"        for(i32 rove_p=board[square],rove_i=0;rove_i<2;rove_p=piece,rove_i++)\r\n"
    b"            if(rove_p<PIECE_NONE)\r\n"
    b"                pieces[rove_p/2]^=1ull<<square,colors[rove_p%2]^=1ull<<square,\r\n"
    b"                hash^=KEYS[rove_p][square],\r\n"
    b"                (rove_p<WHITE_KNIGHT?hash_pawn:hash_non_pawn[rove_p%2])^=KEYS[rove_p][square];\r\n\r\n"
)


def edit_specs(variant):
    if variant != VARIANT:
        raise ValueError("unknown c4ke edit structural variant")
    return {"src/board.cpp": (("edit-loop", _EDIT_BEFORE, _EDIT_AFTER, 1),),
            "src/chess.cpp": (), "src/search.cpp": (), "src/eval.cpp": (),
            "src/main.cpp": ()}


def transform(variant, sources):
    specs = edit_specs(variant)
    if type(sources) is not dict or set(sources) != set(specs):
        raise ValueError("c4ke edit structural input closure differs")
    if any(type(source) is not bytes for source in sources.values()):
        raise ValueError("source must be immutable bytes")
    if any(b"rove_p" in data or b"rove_i" in data for data in sources.values()):
        raise ValueError("candidate loop names already exist")
    outputs, proofs = {}, {}
    for path, edits in specs.items():
        peers.verify_blob("c4ke", path, sources[path])
        outputs[path], proofs[path] = peers.exact_edits(
            sources[path], [(role, before, after) for role, before, after, _ in edits])
    return outputs, {"format": "c4ke-edit-structural-v1", "variant": variant,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-edit-structural-v1"
            or receipt.get("revision") != peers.peer_spec("c4ke").revision):
        raise ValueError("c4ke edit structural receipt identity differs")
    specs = edit_specs(receipt.get("variant"))
    if (type(outputs) is not dict or set(outputs) != set(specs)
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(specs)):
        raise ValueError("c4ke edit structural output closure differs")
    try:
        original = {path: peers.restore_resources(value, receipt["files"][path])
                    for path, value in outputs.items()}
        rebuilt, proof = transform(receipt["variant"], original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke edit structural receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke edit structural receipt does not reproduce candidate")
    return original
