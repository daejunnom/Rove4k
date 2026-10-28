"""Create a reproducible league score-plan *draft*, never a GO authority.

Inputs are the existing independently pinned diagnostic candidates, reviewed
runner receipt and opening bank. Replaying these local files does not prove
compiler or host identity, allocated TT, placement, budget or game eligibility.
The format deliberately differs from the legacy executable campaign plan.
"""
from __future__ import annotations

import itertools
from pathlib import Path

try:
    from . import diagnostic_candidates, ledger, original_peer_uci, registry, run
except ImportError:
    import diagnostic_candidates
    import ledger
    import original_peer_uci
    import registry
    import run


FORMAT = "rove4k-score-plan-draft-v1"


def _player(row, profile):
    artifact, evidence = row["artifact"], row["evidence"]
    if artifact.family not in ("A", "B", "C", "E", "F", "ice4", "c4ke"):
        raise ValueError("unsupported league candidate")
    if artifact.representation == "configurable-native":
        options = original_peer_uci.fastchess_resources(profile)
        if (artifact.family not in ("ice4", "c4ke") or
                artifact.layout_id != registry.PEER_ORIGINAL_UCI_LAYOUT or
                evidence.get("kind") != "original-peer-build-v1" or
                evidence.get("requested_uci") != options or
                artifact.workers != options["threads"] or
                artifact.tt_bytes != options["hash_mib"] << 20):
            raise ValueError("original peer profile, evidence and UCI request differ")
        uci = {"kind": "original-peer-uci-v1", "family": artifact.family, **options}
    else:
        if artifact.family not in "ABCEF":
            raise ValueError("league comparison peers must use original configurable builds")
        if profile == "test-p16" and artifact.tt_bytes > 16 << 30:
            raise ValueError("Rove P16 TT exceeds the profile cap")
        if profile == "test-p192" and artifact.tt_bytes != 192 << 30:
            raise ValueError("Rove P192 TT request differs")
        uci = None
    return {"identity": artifact.identity(), "whole_path": str(row["whole"]),
            "source": row["source"], "native": row["native"],
            "evidence": evidence, "uci": uci,
            "test_file_within_4096": artifact.whole_bytes <= 4096,
            "runtime_qualified": False, "score_qualified": False}


def prepare(campaign, profile, candidate_path, candidate_sha256, bank_path,
            bank_sha256, runner_binary, runner_receipt):
    """Build a deterministic draft from pinned local inputs without execution."""
    run.ID(campaign)
    if profile not in ("test-p16", "test-p192"):
        raise ValueError("P16 or P192 TEST profile required")
    if not isinstance(bank_sha256, str) or not run.SHA.fullmatch(bank_sha256):
        raise ValueError("an independently supplied opening bank digest is required")
    candidate_path = diagnostic_candidates._safe_input_path(candidate_path)
    bank_path = diagnostic_candidates._safe_input_path(bank_path)
    runner_binary = diagnostic_candidates._safe_input_path(runner_binary)
    runner_receipt = diagnostic_candidates._safe_input_path(runner_receipt)
    rows, candidate_digest = diagnostic_candidates.read_candidates(candidate_path, candidate_sha256, profile)
    players = [_player(row, profile) for row in rows]
    if len({row["identity"]["family"] for row in players}) != len(players):
        raise ValueError("a league stage requires one candidate per family")
    stage = "broad" if profile == "test-p16" else "high"
    bank_preview, _ = run.json_input(bank_path, bank_sha256)
    diagnostic_candidates._safe_input_path(bank_preview["files"][stage]["path"])
    bank, bank_digest, openings, pgn_path = run.validate_bank(bank_path, bank_sha256, stage)
    pgn_path = diagnostic_candidates._safe_input_path(pgn_path)
    runner = run.runner_identity(runner_binary, runner_receipt)
    pairs = []
    for index, (white, black) in enumerate(itertools.combinations(players, 2)):
        players_by_id = [white["identity"]["id"], black["identity"]["id"]]
        opening_index = index % len(openings)
        opening = openings[opening_index]
        pair_id = "pair-" + ledger.digest({"campaign": campaign, "profile": profile,
                         "players": players_by_id, "opening": opening["id"]})[:20]
        pairs.append({"id": pair_id, "players": players_by_id,
                      "opening_id": opening["id"], "opening_index": opening_index + 1,
                      "opening_moves": opening["moves"],
                      "games": [{"leg": 0, "white": players_by_id[0], "black": players_by_id[1]},
                                {"leg": 1, "white": players_by_id[1], "black": players_by_id[0]}]})
    content = {
        "campaign": campaign, "profile": profile, "stage": stage, "bank_id": bank["bank_id"],
        "inputs": {"candidate_path": str(candidate_path), "candidate_sha256": candidate_digest,
                   "bank_path": str(bank_path), "bank_sha256": bank_digest,
                   "runner_binary": str(runner_binary), "runner_receipt": str(runner_receipt)},
        "opening_pgn": {"path": str(pgn_path), "sha256": bank["files"][stage]["sha256"],
                        "bytes": bank["files"][stage]["bytes"]},
        "runner": runner, "players": players, "pairs": pairs,
        "clock": {"initial_seconds": 1800, "increment_seconds": 3,
                  "ponder_requested": False, "unsupported_ponder": "record-and-proceed"},
        "claims": {"local_pins_replayed": True, "producer_authenticated": False,
                   "runner_producer_authenticated": False, "actual_abi_verified": False,
                   "opening_pgn_mapping_verified": False, "high_selection_verified": False,
                   "tt_allocation_observed": False, "worker_or_numa_observed": False,
                   "host_authenticated": False, "budget_authorized": False,
                   "score_qualified": False, "go_authorized": False, "score_final": False},
    }
    return {"format": FORMAT, "content": content, "sha256": ledger.digest(content)}


def verify(envelope, expected_sha256):
    """Replay every input against an independently supplied draft digest.

    This accepts a parsed object only; consumers of JSON bytes must themselves
    reject duplicate keys before passing a document here.
    """
    if (type(envelope) is not dict or set(envelope) != {"format", "content", "sha256"} or
            envelope["format"] != FORMAT or not isinstance(expected_sha256, str) or
            not run.SHA.fullmatch(expected_sha256) or envelope["sha256"] != expected_sha256 or
            ledger.digest(envelope["content"]) != expected_sha256):
        raise ValueError("draft identity or independently supplied digest differs")
    body = envelope["content"]
    if type(body) is not dict or type(body.get("inputs")) is not dict:
        raise ValueError("draft input record is invalid")
    inputs = body["inputs"]
    if set(inputs) != {"candidate_path", "candidate_sha256", "bank_path", "bank_sha256",
                       "runner_binary", "runner_receipt"}:
        raise ValueError("draft input fields differ")
    replay = prepare(body.get("campaign"), body.get("profile"), **inputs)
    if ledger.canonical(replay) != ledger.canonical(envelope):
        raise ValueError("draft differs from replayed pinned inputs")
    return replay


def verify_bytes(raw, expected_sha256):
    """Decode bounded canonical JSON and replay, rejecting duplicate fields."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 16 << 20:
        raise ValueError("bounded draft JSON bytes required")
    envelope = diagnostic_candidates._strict_json(raw)
    canonical = ledger.canonical(envelope)
    if raw not in (canonical, canonical + b"\n"):
        raise ValueError("draft JSON is not canonical")
    return verify(envelope, expected_sha256)
