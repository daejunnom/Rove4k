"""Pin and shorten a peer TCEC launcher's line-selection syntax.

This build-only transform does not copy the upstream launcher into Git or
change compiler options, process cleanup, payload bytes, or exec behavior.
The alternate ``tail +5`` syntax requires GNU coreutils; this is an explicit
target-environment assumption, not a portable POSIX shell claim.  A header
reduction alone does not qualify an engine or establish a 4 KiB submission.
"""
from __future__ import annotations

try:
    from . import peers
except ImportError:
    import peers

_BEFORE = b'tail -n +5 "$0"'
_AFTER = b'tail +5 "$0"'


def transform_launcher(name, data):
    """Return a pinned GNU-tail candidate and a complete inverse proof."""
    if name not in ("ice4", "c4ke") or type(data) is not bytes:
        raise ValueError("pinned peer and immutable launcher bytes required")
    peers.verify_blob(name, "launcher.sh", data)
    candidate, proof = peers.exact_edits(data, [("gnu-tail-line-selection", _BEFORE, _AFTER)])
    proof.update(format="rove4k-peer-gnu-tail-launcher-v1", peer=name,
                 runtime_requirement="GNU tail +N line-number syntax",
                 source_blob_verified=True, engine_executed=False, runtime_qualified=False)
    return candidate, proof


def restore_launcher(name, candidate, proof):
    """Reconstruct the original and reject any noncanonical proof or bytes."""
    try:
        original = peers.restore_resources(candidate, proof)
        rebuilt, expected = transform_launcher(name, original)
        if rebuilt != candidate or peers.canonical(proof) != peers.canonical(expected):
            raise ValueError("launcher proof is not canonical")
        return original
    except (KeyError, TypeError, UnicodeError, IndexError) as error:
        raise ValueError("invalid launcher transform proof") from error
