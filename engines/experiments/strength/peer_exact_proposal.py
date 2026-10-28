"""Recheck an experimental exact-P192 peer producer without admitting it.

This consumes the retained producer files, not the JSON flags alone. It
verifies two source snapshots against pinned upstream blobs, the inverse
transform, and the emitted source and source-JIT whole bytes. The minifier
output's TT semantics and any native reference are not established here.
No returned identity can be used as a diagnostic or scored Artifact.
"""
from __future__ import annotations

import hashlib
import json
import lzma
from pathlib import Path
import re

try:
    from . import peer_p192_exact as exact, peer_p192_exact_build as build, peers
except ImportError:
    import peer_p192_exact as exact
    import peer_p192_exact_build as build
    import peers

LAYOUT = "peer-p192-exact-3x2p33-v1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate producer JSON member")
            out[key] = value
        return out
    def bad(_):
        raise ValueError("non-finite producer JSON number")
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    if type(value) is not dict:
        raise ValueError("producer JSON object required")
    return value


def _pinned(path, descriptor):
    if (type(descriptor) is not dict or type(descriptor.get("bytes")) is not int or
            descriptor["bytes"] < 0 or type(descriptor.get("sha256")) is not str or
            _SHA.fullmatch(descriptor["sha256"]) is None):
        raise ValueError("bounded producer descriptor required")
    raw = build._read_proof(path)
    if len(raw) != descriptor["bytes"] or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
        raise ValueError("retained producer bytes changed")
    return raw


def inspect(producer_record, producer_sha256):
    """Return only a reproducible source-transport proposal, never admission."""
    record_path = Path(producer_record)
    if (not record_path.is_absolute() or record_path.name != "peer-exact.json" or
            type(producer_sha256) is not str or _SHA.fullmatch(producer_sha256) is None):
        raise ValueError("absolute exact producer receipt and supplied SHA-256 required")
    raw = build._read_proof(record_path)
    if hashlib.sha256(raw).hexdigest() != producer_sha256:
        raise ValueError("producer receipt identity changed")
    record = _json(raw)
    peer = record.get("peer")
    if peer not in ("ice4", "c4ke"):
        raise ValueError("supported pinned peer required")
    spec = peers.peer_spec(peer)
    if (record.get("format") != "rove4k-peer-p192-exact-producer-v1" or
            record.get("artifact_kind") != "experimental-p192-exact" or
            record.get("profile") != exact.PROFILE or record.get("family") != peer or
            record.get("version") != spec.version or record.get("repository") != spec.repository or
            record.get("revision") != spec.revision or record.get("source_url") != spec.source_url or
            record.get("algorithm_changed") is not True or record.get("complete") is not True or
            record.get("reproducible") is not True or record.get("executing_code_identity_verified") is not False):
        raise ValueError("experimental producer identity or completion differs")
    resources = {"workers": 192, "entry_bytes": 8, "tt_entries": 3 << 33,
                 "tt_bytes": 192 << 30, "index": "upper48-times3-shift15"}
    found_resources = record.get("resources")
    if (found_resources != resources or type(found_resources) is not dict or
            any(type(found_resources.get(k)) is not int for k in
                ("workers", "entry_bytes", "tt_entries", "tt_bytes"))):
        raise ValueError("exact P192 peer layout differs")
    qualified = record.get("qualification")
    if (type(qualified) is not dict or qualified.get("input_transform_inverse_verified") is not True or
            any(qualified.get(k) is not False for k in
                ("emitted_tt_semantics_verified", "runtime_qualified", "league_qualified"))):
        raise ValueError("producer must remain an unqualified experiment")
    expected_manifest = peers.sha(peers.canonical(peers.SOURCE_BLOBS[peer]))
    if record.get("upstream_blob_manifest_sha256") != expected_manifest:
        raise ValueError("pinned upstream manifest differs")
    variant = record.get("source_variant", "baseline")
    launcher_variant = record.get("launcher_variant", "upstream")
    if type(variant) is not str or launcher_variant not in ("upstream", "gnu-tail-v1"):
        raise ValueError("exact producer variants differ")
    closure = exact.source_closure(peer, variant=variant)
    modules = {"producer": build, "transform": exact, "peer_base": peers,
               "command_runner": build.runner}
    if variant in ("castle-v1", "zobrist-v1", "castle-zobrist-v1"):
        modules["ice_structural_transform"] = exact.peer_ice_structural
    if variant in ("castle-or-v1", "ray-castle-or-v1", "edit-castle-or-v1", "edit-castle-alloc24-v1",
                   "edit-castle-slider-v1", "edit-castle-startpos-v1", "edit-castle-quiet-v1",
                   "edit-castle-emission-v1", "edit-castle-phalanx-v1"):
        modules["c4ke_structural_transform"] = exact.peer_c4ke_structural
    if variant in ("edit-loop-v1", "edit-castle-or-v1", "edit-castle-alloc24-v1",
                   "edit-castle-slider-v1", "edit-castle-startpos-v1", "edit-castle-quiet-v1",
                   "edit-castle-emission-v1", "edit-castle-phalanx-v1"):
        modules["c4ke_edit_structural_transform"] = exact.peer_c4ke_edit_structural
    if variant in ("edit-castle-slider-v1", "edit-castle-startpos-v1"):
        modules["c4ke_loop_transform"] = (exact.peer_c4ke_slider_loop if variant == "edit-castle-slider-v1"
                                           else exact.peer_c4ke_startpos_loop)
    if variant == "edit-castle-quiet-v1":
        modules["c4ke_quiet_transform"] = exact.peer_c4ke_quiet_history
    if variant in ("edit-castle-emission-v1", "edit-castle-phalanx-v1"):
        modules["c4ke_candidate_transform"] = (exact.peer_c4ke_move_emission
                                               if variant == "edit-castle-emission-v1"
                                               else exact.peer_c4ke_phalanx)
    if launcher_variant == "gnu-tail-v1":
        try:
            from . import peer_launcher_trim as trim
        except ImportError:
            import peer_launcher_trim as trim
        modules["launcher_transform"] = trim
    tools = record.get("producer_inputs")
    if type(tools) is not dict or set(tools) != set(modules):
        raise ValueError("producer tool set differs")
    for name, module in modules.items():
        retained = _pinned(record_path.parent / (name + ".py"), tools[name])
        if build._read_proof(Path(module.__file__).resolve(strict=True)) != retained:
            raise ValueError("producer snapshot differs from verifier source")
    attempts = record.get("attempts")
    if type(attempts) is not list or len(attempts) != 2:
        raise ValueError("two exact producer attempts required")
    root = record_path.parent
    observed = []
    upstream = None
    for number, row in enumerate(attempts, 1):
        if type(row) is not dict or row.get("source_inverse_verified") is not True:
            raise ValueError("attempt inverse claim missing")
        attempt = root / ("attempt-" + str(number))
        snapshot = build._source_snapshot(peer, attempt / "source", pinned=False)
        proof_raw = build._read_proof(attempt / "transform-proof.json")
        if hashlib.sha256(proof_raw).hexdigest() != row.get("transform_proof_sha256"):
            raise ValueError("retained transform proof changed")
        proof = _json(proof_raw)
        original_closure = exact.restore(peer, {p: snapshot[p] for p in closure}, proof, variant=variant)
        original = {**snapshot, **original_closure}
        for relative, data in original.items():
            peers.verify_blob(peer, relative, data)
        if upstream is not None and original != upstream:
            raise ValueError("two upstream source snapshots differ")
        upstream = original
        source = _pinned(attempt / "main.cpp", row.get("source"))
        if not source.startswith(b"#include"):
            raise ValueError("emitted source header differs")
        whole_descriptor = row.get("whole")
        target = attempt / spec.tiny_name
        if type(whole_descriptor) is not dict or whole_descriptor.get("path") != str(target):
            raise ValueError("attempt whole path differs")
        whole = _pinned(target, whole_descriptor)
        if launcher_variant == "gnu-tail-v1":
            header, _ = trim.transform_launcher(peer, original["launcher.sh"])
        else:
            header = original["launcher.sh"]
        if row.get("header") != {"bytes": len(header), "sha256": peers.sha(header)} or not whole.startswith(header):
            raise ValueError("actual launcher bytes differ")
        # The producer's preset 9 uses a 64 MiB dictionary. Bound decoder
        # allocation independently of the output-size limit below.
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=128 << 20)
        try:
            expanded = decoder.decompress(whole[len(header):], max_length=peers.MiB + 1)
        except lzma.LZMAError as error:
            raise ValueError("invalid retained source stream") from error
        if not decoder.eof or decoder.unused_data or expanded != source:
            raise ValueError("whole stream does not restore emitted source")
        observed.append((source, whole, proof_raw, row.get("compiler_version_sha256")))
    if observed[0] != observed[1]:
        raise ValueError("independent exact producer attempts differ")
    first = attempts[0]["whole"]
    if record.get("whole") != first or qualified.get("size_within_4096") is not (len(observed[0][1]) <= 4096):
        raise ValueError("producer whole or size conclusion differs")
    return {"format": "rove4k-peer-exact-proposal-v1", "layout": LAYOUT,
            "peer": peer, "test_profile": "test-p192", "resources": resources,
            "source_sha256": peers.sha(observed[0][0]), "whole_sha256": peers.sha(observed[0][1]),
            "whole_bytes": len(observed[0][1]), "producer_receipt_sha256": producer_sha256,
            "source_snapshot_inverse_verified": True, "retained_source_whole_consistent": True,
            "minifier_execution_replayed": False,
            "emitted_tt_semantics_verified": False, "native_reference_verified": False,
            "eligible_for_diagnostic": False, "eligible_for_scored_league": False,
            "scope": "experimental source transport only; no Artifact, TT semantic or runtime admission"}
