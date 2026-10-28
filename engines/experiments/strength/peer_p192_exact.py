"""Exact 192-GiB experimental peer source transform; no engine execution.

The original pinned upstream bytes remain external to Git.  This transform
changes TT allocation and indexing for a TCEC minifier input, not merely a
resource constant; its receipt must not be called an upstream algorithm or
runtime qualification.  It is not wired into the existing peer producer or
registry until their independent source/runtime contracts support it.
"""
from __future__ import annotations

try:
    from . import peers
except ImportError:
    import peers

PROFILE = "test-p192-exact-v1"
ENTRIES = 3 << 33
TT_BYTES = ENTRIES * 8
WORKERS = 192

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


def transform(name, source_files):
    """Transform exactly the needed verified upstream blobs in memory.

    Return changed bytes and a complete inverse receipt.  The minifier's
    existing 192-worker numeric substitutions are retained, but its TT_BITS
    value is no longer the emitted TT extent for this distinct profile.
    """
    if name not in _EDITS or type(source_files) is not dict:
        raise ValueError("pinned ice4 or c4ke sources are required")
    peer = peers.peer_spec(name)
    expected = set(_EDITS[name]) | {peer.resource_path}
    if set(source_files) != expected:
        raise ValueError("exact source transform closure required")
    for path in sorted(expected):
        data = source_files[path]
        if type(data) is not bytes:
            raise ValueError("source must be immutable bytes")
        peers.verify_blob(name, path, data)
    output, proofs = {}, {}
    for path in sorted(_EDITS[name]):
        output[path], proofs[path] = _edit(source_files[path], _EDITS[name][path])
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
    return output, receipt


def restore(name, changed, receipt):
    """Verify the frozen transform, reconstruct every original and replay it."""
    if name not in _EDITS or type(changed) is not dict or type(receipt) is not dict:
        raise ValueError("invalid transform receipt")
    peer = peers.peer_spec(name)
    expected = set(_EDITS[name]) | {peer.resource_path}
    if set(changed) != expected or type(receipt.get("files")) is not dict or set(receipt["files"]) != expected:
        raise ValueError("transform receipt closure differs")
    original = {}
    try:
        for path in sorted(expected):
            if type(changed[path]) is not bytes:
                raise ValueError("transformed source must be bytes")
            original[path] = peers.restore_resources(changed[path], receipt["files"][path])
            peers.verify_blob(name, path, original[path])
        replay, expected_receipt = transform(name, original)
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid transform receipt") from error
    if replay != changed or peers.canonical(receipt) != peers.canonical(expected_receipt):
        raise ValueError("transform replay or receipt differs")
    return original
