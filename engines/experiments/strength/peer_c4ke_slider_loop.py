"""Reversible c4ke slider-call sharing candidate, without engine sources in Git.

The caller supplies the complete pinned source closure in memory.  This is a
source experiment only; no size, legality, runtime or strength is established.
"""
try:
    from . import peers
except ImportError:
    import peers

VARIANT = "slider-loop-v1"
SOURCE_FILES = ("src/board.cpp", "src/chess.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
LOOP_NAME = b"rove_slider_type"
BEFORE = (
    b"        add_moves(list, targets, occupied, (pieces[BISHOP] | pieces[QUEEN]) & colors[stm], BISHOP);\r\n"
    b"        add_moves(list, targets, occupied, (pieces[ROOK] | pieces[QUEEN]) & colors[stm], ROOK);"
)
AFTER = (
    b"        for(i32 rove_slider_type=BISHOP;rove_slider_type<=ROOK;rove_slider_type++) {\r\n"
    b"            add_moves(list,targets,occupied,(pieces[rove_slider_type]|pieces[QUEEN])&colors[stm],rove_slider_type);\r\n"
    b"        }"
)


def transform(sources):
    if type(sources) is not dict or set(sources) != set(SOURCE_FILES):
        raise ValueError("c4ke source closure differs")
    if any(type(data) is not bytes for data in sources.values()):
        raise ValueError("source must be immutable bytes")
    for path, data in sources.items():
        peers.verify_blob("c4ke", path, data)
        if LOOP_NAME in data:
            raise ValueError("candidate loop name already exists")
    chess = sources["src/chess.cpp"]
    if (chess.count(b"#define BISHOP 2") != 1 or chess.count(b"#define ROOK 3") != 1
            or chess.count(b"#define QUEEN 4") != 1):
        raise ValueError("slider and queen constants differ")
    outputs, proofs = {}, {}
    for path in SOURCE_FILES:
        edits = [("slider-loop", BEFORE, AFTER)] if path == "src/board.cpp" else []
        outputs[path], proofs[path] = peers.exact_edits(sources[path], edits)
    return outputs, {"format": "c4ke-slider-loop-v1", "variant": VARIANT,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-slider-loop-v1"
            or receipt.get("variant") != VARIANT
            or receipt.get("revision") != peers.peer_spec("c4ke").revision
            or type(receipt.get("files")) is not dict
            or set(receipt["files"]) != set(SOURCE_FILES)
            or type(outputs) is not dict or set(outputs) != set(SOURCE_FILES)):
        raise ValueError("c4ke slider receipt identity or closure differs")
    try:
        original = {path: peers.restore_resources(outputs[path], receipt["files"][path])
                    for path in SOURCE_FILES}
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid c4ke slider receipt") from error
    candidate, regenerated = transform(original)
    if candidate != outputs or regenerated != receipt:
        raise ValueError("c4ke slider receipt does not reproduce candidate")
    return original
