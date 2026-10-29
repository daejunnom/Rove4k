"""Reversible, unmeasured c4ke quiet-history sharing experiment.

Upstream source bytes are supplied by the caller and remain outside Git.
This transform does not change TT sizing and does not qualify a peer.
"""
import re

try:
    from . import peers
except ImportError:
    import peers

VARIANT = "quiet-history-v1"
PATHS = ("src/chess.cpp", "src/board.cpp", "src/eval.cpp", "src/search.cpp", "src/main.cpp")
IDENTIFIER = b"rove_quiet_history"
IDENTIFIERS = (IDENTIFIER, b"rove_b", b"rove_m", b"rove_p", b"rove_v")

_SEARCH = b"    i32 search(Board& board, i32 alpha"
_HELPER = (
    b"    null rove_quiet_history(Board& rove_b, i32 rove_m, i32 rove_p, i32 rove_v) {\r\n"
    b"        update_history(qhist[rove_b.stm][rove_m & 4095], rove_v);\r\n"
    b"        update_history(stack_conthist[rove_p][0][rove_b.board[move_from(rove_m)]][move_to(rove_m)], rove_v);\r\n"
    b"        update_history(stack_conthist[rove_p + 1][0][rove_b.board[move_from(rove_m)]][move_to(rove_m)], rove_v);\r\n"
    b"    }\r\n"
)
_BONUS_BEFORE = (
    b"update_history(qhist[board.stm][move & 4095], bonus);\r\n"
    b"                    update_history(stack_conthist[ply][0][board.board[move_from(move)]][move_to(move)], bonus);\r\n"
    b"                    update_history(stack_conthist[ply + 1][0][board.board[move_from(move)]][move_to(move)], bonus);"
)
_BONUS_AFTER = b"rove_quiet_history(board, move, ply, bonus);"
_PENALTY_BEFORE = (
    b"update_history(qhist[board.stm][quiet_list[k] & 4095], -bonus),\r\n"
    b"                        update_history(stack_conthist[ply][0][board.board[move_from(quiet_list[k])]][move_to(quiet_list[k])], -bonus),\r\n"
    b"                        update_history(stack_conthist[ply + 1][0][board.board[move_from(quiet_list[k])]][move_to(quiet_list[k])], -bonus);"
)
_PENALTY_AFTER = b"rove_quiet_history(board, quiet_list[k], ply, -bonus);"


def edit_specs(variant):
    if variant != VARIANT:
        raise ValueError("unknown c4ke quiet-history variant")
    return {path: (("helper", _SEARCH, _HELPER + _SEARCH, 1),
                   ("bonus", _BONUS_BEFORE, _BONUS_AFTER, 1),
                   ("penalty", _PENALTY_BEFORE, _PENALTY_AFTER, 1))
            if path == "src/search.cpp" else () for path in PATHS}


def transform(variant, sources):
    specs = edit_specs(variant)
    if type(sources) is not dict or set(sources) != set(PATHS):
        raise ValueError("c4ke quiet-history input closure differs")
    names = [re.compile(rb"(?<![A-Za-z0-9_])" + value + rb"(?![A-Za-z0-9_])")
             for value in IDENTIFIERS]
    outputs, proofs = {}, {}
    for path, edits in specs.items():
        data = sources[path]
        if type(data) is not bytes:
            raise ValueError("source must be immutable bytes")
        peers.verify_blob("c4ke", path, data)
        if any(name.search(data) for name in names):
            raise ValueError("quiet-history helper or parameter identifier collides")
        outputs[path], proofs[path] = peers.exact_edits(
            data, [(role, before, after) for role, before, after, _ in edits])
    return outputs, {"format": "c4ke-quiet-history-v1", "variant": variant,
                     "revision": peers.peer_spec("c4ke").revision, "files": proofs}


def restore(outputs, receipt):
    if (type(receipt) is not dict or receipt.get("format") != "c4ke-quiet-history-v1"
            or receipt.get("revision") != peers.peer_spec("c4ke").revision):
        raise ValueError("c4ke quiet-history receipt identity differs")
    specs = edit_specs(receipt.get("variant"))
    if (type(outputs) is not dict or set(outputs) != set(specs)
            or type(receipt.get("files")) is not dict or set(receipt["files"]) != set(specs)):
        raise ValueError("c4ke quiet-history output closure differs")
    try:
        original = {path: peers.restore_resources(value, receipt["files"][path])
                    for path, value in outputs.items()}
        rebuilt, proof = transform(receipt["variant"], original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid c4ke quiet-history receipt") from error
    if rebuilt != outputs or peers.canonical(proof) != peers.canonical(receipt):
        raise ValueError("c4ke quiet-history receipt does not reproduce candidate")
    return original
