"""Exact 192-GiB experimental peer source transform; no engine execution.

The original pinned upstream bytes remain external to Git.  This transform
changes TT allocation and indexing for a TCEC minifier input, not merely a
resource constant; its receipt must not be called an upstream algorithm or
runtime qualification.  It is not wired into the existing peer producer or
registry until their independent source/runtime contracts support it.
"""
from __future__ import annotations

import re

try:
    from . import peers
except ImportError:
    import peers

PROFILE = "test-p192-exact-v1"
ENTRIES = 3 << 33
TT_BYTES = ENTRIES * 8
WORKERS = 192
SHARE_VARIANT = "share-v1"
SLOT_VARIANT = "slot-v1"
RAY_VARIANT = "ray-v1"
SLOT_RAY_VARIANT = "slot-ray-v1"

# The first tuple names the role, the exact pinned input, replacement and the
# required number of occurrences.  Both hot access and prefetch use exactly
# the same mapping.  These inputs are a private TCEC producer snapshot; they
# are not a substitute for upstream's general OPENBENCH source.
_EDITS = {
    "ice4": {
        "src/board.cpp": (
            ("allocation", b"calloc(1ull << DEFAULT_TT_BITS, 8)", b"calloc(3ull << 33, 8)", 1),
            ("prefetch", b"TT[zobrist >> (64 - TT_BITS)]", b"TT[((zobrist >> 16) * 3) >> 15]", 1),
        ),
        "src/search.cpp": (
            ("probe-store", b"TT[board.zobrist >> (64 - TT_BITS)]", b"TT[((board.zobrist >> 16) * 3) >> 15]", 1),
        ),
    },
    "c4ke": {
        "src/chess.cpp": (
            ("allocation", b"calloc(1ull << TT_BITS, 8)", b"calloc(3ull << 33, 8)", 1),
        ),
        "src/board.cpp": (
            ("prefetch", b"TTABLE[hash >> TT_SHIFT]", b"TTABLE[((hash >> 16) * 3) >> 15]", 1),
        ),
        "src/search.cpp": (
            ("probe-store", b"TTABLE[board.hash >> TT_SHIFT]", b"TTABLE[((board.hash >> 16) * 3) >> 15]", 2),
        ),
    },
}

# This distinct c4ke experiment caches the same TT lvalue across search.
# The referenced entry is stable only for the pinned TCEC build: search does
# not change its own board hash, and the OB-only hash-resize branch is removed.
# The additional untouched source blobs pin the reviewed dependency context;
# this is not proof of a minifier output or of concurrent runtime behavior.
_SHARE_EDITS = {
    "src/chess.cpp": _EDITS["c4ke"]["src/chess.cpp"],
    "src/board.cpp": (
        ("prefetch", b"TTABLE[hash >> TT_SHIFT]", b"TTABLE[3*(hash >> 16)>>15]", 1),
    ),
    "src/search.cpp": (
        ("probe-and-slot", b"TTEntry tt = TTABLE[board.hash >> TT_SHIFT];",
         b"TTEntry &rove_entry=TTABLE[3*(board.hash>>16)>>15],tt=rove_entry;", 1),
        ("store-to-slot", b"TTABLE[board.hash >> TT_SHIFT] = {", b"rove_entry = {", 1),
    ),
    "src/main.cpp": (),
    "src/eval.cpp": (),
}

# These are independent experiments, not replacements for the measured
# baseline or share-v1.  The reference helper computes the same slot on each
# access; unlike share-v1 it does not cache a pointer across search.  The ray
# candidate performs the original six updates in the same order.
_SLOT_ALLOC = (
    "allocation-and-slot-helper",
    b"TTEntry* TTABLE = (TTEntry*)calloc(1ull << TT_BITS, 8);",
    b"TTEntry* TTABLE=(TTEntry*)calloc(3ull<<33,8);"
    b"TTEntry& rove_slot(u64 h){return TTABLE[3*(h>>16)>>15];}",
    1,
)
_RAY_BEFORE = b"    mask |= func(mask & ~occupied);\r\n" * 6
_RAY_EDIT = ("six-ray-updates", _RAY_BEFORE,
             b"    for(i32 rove_ray=6;rove_ray--;)mask |= func(mask & ~occupied);\r\n", 1)
_SLOT_EDITS = {
    "src/chess.cpp": (_SLOT_ALLOC,),
    "src/board.cpp": (("prefetch", b"TTABLE[hash >> TT_SHIFT]", b"rove_slot(hash)", 1),),
    "src/search.cpp": (("probe-store", b"TTABLE[board.hash >> TT_SHIFT]", b"rove_slot(board.hash)", 2),),
    "src/main.cpp": (),
    "src/eval.cpp": (),
}
_RAY_EDITS = {
    "src/chess.cpp": (*_EDITS["c4ke"]["src/chess.cpp"], _RAY_EDIT),
    "src/board.cpp": _EDITS["c4ke"]["src/board.cpp"],
    "src/search.cpp": _EDITS["c4ke"]["src/search.cpp"],
    "src/main.cpp": (),
    "src/eval.cpp": (),
}
_SLOT_RAY_EDITS = {**_SLOT_EDITS, "src/chess.cpp": (_SLOT_ALLOC, _RAY_EDIT)}


def _variant_edits(name, variant):
    if variant == "baseline":
        return _EDITS.get(name)
    if variant == SHARE_VARIANT and name == "c4ke":
        return _SHARE_EDITS
    if name == "c4ke" and variant in (SLOT_VARIANT, RAY_VARIANT, SLOT_RAY_VARIANT):
        return {SLOT_VARIANT: _SLOT_EDITS, RAY_VARIANT: _RAY_EDITS,
                SLOT_RAY_VARIANT: _SLOT_RAY_EDITS}[variant]
    raise ValueError("unsupported peer transform variant")


def source_closure(name, *, variant="baseline"):
    edits = _variant_edits(name, variant)
    if edits is None:
        raise ValueError("pinned ice4 or c4ke sources are required")
    return frozenset(edits) | {peers.peer_spec(name).resource_path}


def _check_share_context(source_files):
    # Known-pinned sources are additionally checked for the precise structural
    # assumptions reviewed for this experiment. Reproduction of those bytes is
    # still not an independent proof of compiler or engine behavior.
    search = source_files["src/search.cpp"]
    board = source_files["src/board.cpp"]
    main = source_files["src/main.cpp"].replace(b"\r\n", b"\n")
    chess = source_files["src/chess.cpp"]
    if any(b"rove_entry" in data for data in source_files.values()):
        raise ValueError("cached TT reference name already exists")
    required = (
        (search, b"TTEntry tt = TTABLE[board.hash >> TT_SHIFT];", 1),
        (search, b"TTABLE[board.hash >> TT_SHIFT] = {", 1),
        (search, b"Board child = board;", 2),
        (search, b"score = search(board,", 2),
        (board, b"__builtin_prefetch(&TTABLE[hash >> TT_SHIFT]);", 1),
        (chess, b"TTEntry* TTABLE = (TTEntry*)calloc(1ull << TT_BITS, 8);", 1),
        (main, b"#ifdef OB\n        // Uci ucinewgame", 1),
        (main, b"TTABLE = (TTEntry*)calloc(1ull << TT_BITS, sizeof(TTEntry));", 1),
        (main, b"jthread threads[THREADS];", 1),
        (main, b"free(TTABLE);", 2),
    )
    if any(data.count(marker) != count for data, marker, count in required):
        raise ValueError("pinned c4ke TCEC reference assumptions differ")
    if (search.count(b"board.hash") != 13 or search.count(b"board.make(") or
            search.count(b"TTABLE[") != 2 or board.count(b"TTABLE[") != 1):
        raise ValueError("pinned c4ke hash/TT access shape differs")
    if (re.search(rb"\bboard\.hash\b\s*(?:\+\+|--|[+*/%&|^\-]=|=(?!=))", search) or
            re.search(rb"(?:\+\+|--)\s*board\.hash\b", search)):
        raise ValueError("search writes the source board hash")
    begin = main.index(b"#ifdef OB\n        // Uci ucinewgame")
    end = main.index(b"#endif\n        // Uci position", begin)
    reallocation = main.index(b"TTABLE = (TTEntry*)calloc(1ull << TT_BITS, sizeof(TTEntry));")
    if not begin < reallocation < end:
        raise ValueError("TT reallocation is not inside the removed OB block")


def index(hash_value):
    """Map the upper 48 bits to the full table, preserving the low 16-bit tag."""
    if type(hash_value) is not int or not 0 <= hash_value < 1 << 64:
        raise ValueError("an unsigned 64-bit hash is required")
    return ((hash_value >> 16) * 3) >> 15


def _edit(source, specifications):
    rows = []
    for role, before, after, expected in specifications:
        if source.count(before) != expected:
            raise ValueError("pinned transform marker differs: " + role)
        offset = 0
        for occurrence in range(expected):
            start = source.index(before, offset)
            rows.append({"role": role + ":" + str(occurrence), "start": start,
                         "before": before.decode("ascii"), "after": after.decode("ascii")})
            offset = start + len(before)
    rows.sort(key=lambda row: row["start"])
    parts, cursor = [], 0
    for row in rows:
        before, after = row["before"].encode("ascii"), row["after"].encode("ascii")
        start = row["start"]
        if start < cursor or source[start:start + len(before)] != before:
            raise ValueError("overlapping transform markers")
        parts.extend((source[cursor:start], after))
        cursor = start + len(before)
    parts.append(source[cursor:])
    result = b"".join(parts)
    proof = {"before_sha256": peers.sha(source), "after_sha256": peers.sha(result), "edits": rows}
    if peers.restore_resources(result, proof) != source:
        raise ValueError("complete source inverse failed")
    return result, proof


def transform(name, source_files, *, variant="baseline"):
    """Transform exactly the needed verified upstream blobs in memory.

    Return changed bytes and a complete inverse receipt.  The minifier's
    existing 192-worker numeric substitutions are retained, but its TT_BITS
    value is no longer the emitted TT extent for this distinct profile.
    """
    edits = _variant_edits(name, variant)
    if edits is None or type(source_files) is not dict:
        raise ValueError("pinned ice4 or c4ke sources are required")
    peer = peers.peer_spec(name)
    expected = source_closure(name, variant=variant)
    if set(source_files) != expected:
        raise ValueError("exact source transform closure required")
    for path in sorted(expected):
        data = source_files[path]
        if type(data) is not bytes:
            raise ValueError("source must be immutable bytes")
        peers.verify_blob(name, path, data)
    if variant == SHARE_VARIANT:
        _check_share_context(source_files)
    if variant in (SLOT_VARIANT, SLOT_RAY_VARIANT) and any(b"rove_slot" in data for data in source_files.values()):
        raise ValueError("TT slot helper name already exists")
    if variant in (RAY_VARIANT, SLOT_RAY_VARIANT) and any(b"rove_ray" in data for data in source_files.values()):
        raise ValueError("ray loop variable name already exists")
    output, proofs = {}, {}
    for path in sorted(edits):
        output[path], proofs[path] = _edit(source_files[path], edits[path])
    output[peer.resource_path], numeric_proof = peers.resource_patch(
        name, source_files[peer.resource_path], "test-p192")
    # The upstream minifier still substitutes TT_BITS=34, but the transformed
    # TCEC allocation and every indexing site no longer use that constant.
    # Do not embed the legacy 128-GiB layout as if it described this profile.
    proofs[peer.resource_path] = {key: numeric_proof[key]
                                  for key in ("before_sha256", "after_sha256", "edits")}
    receipt = {"format": "rove4k-peer-p192-exact-transform-v1", "profile": PROFILE,
               "peer": name, "repository": peer.repository, "revision": peer.revision,
               "workers": WORKERS, "entry_bytes": 8, "tt_entries": ENTRIES, "tt_bytes": TT_BYTES,
               "index": "upper48-times3-shift15", "algorithm_changed": True,
               "minifier_numeric_substitutions": {"workers": WORKERS, "tt_bits": 34,
                                                  "tt_bits_describes_runtime_extent": False},
               "scope": "TCEC minifier input only; not runtime qualification or score admission",
               "files": proofs}
    if variant == SHARE_VARIANT:
        receipt["variant"] = variant
        receipt["shared_slot_scope"] = "pinned TCEC source review; runtime and minifier behavior unverified"
    elif variant in (SLOT_VARIANT, RAY_VARIANT, SLOT_RAY_VARIANT):
        receipt["variant"] = variant
        receipt["variant_scope"] = "pinned source transform; minifier, native runtime and playing strength unverified"
    return output, receipt


def restore(name, changed, receipt, *, variant="baseline"):
    """Verify the frozen transform, reconstruct every original and replay it."""
    edits = _variant_edits(name, variant)
    if edits is None or type(changed) is not dict or type(receipt) is not dict:
        raise ValueError("invalid transform receipt")
    peer = peers.peer_spec(name)
    expected = source_closure(name, variant=variant)
    if set(changed) != expected or type(receipt.get("files")) is not dict or set(receipt["files"]) != expected:
        raise ValueError("transform receipt closure differs")
    original = {}
    try:
        for path in sorted(expected):
            if type(changed[path]) is not bytes:
                raise ValueError("transformed source must be bytes")
            original[path] = peers.restore_resources(changed[path], receipt["files"][path])
            peers.verify_blob(name, path, original[path])
        replay, expected_receipt = transform(name, original, variant=variant)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid transform receipt") from error
    if replay != changed or peers.canonical(receipt) != peers.canonical(expected_receipt):
        raise ValueError("transform replay or receipt differs")
    return original
