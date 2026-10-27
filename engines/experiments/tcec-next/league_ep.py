"""Source-only C/E league EP maker experiment on four observed projections.

The existing compact_ep owner checks the private normalizer and maker domain;
this adapter binds that operation to actual P16/P192 control projections.
It does not select a producer, qualify native binaries, or assert runtime or
complete-file cost. Input hashes are from CI-produced resource projections.
"""
from copy import deepcopy
from hashlib import sha256
import json

SCHEMA = "rove4k.league-ep-source.v1"
VARIANT = "legal-maker"
INPUTS = {
    ("C", "test-p16"): (8502, "d85638b93ceefd6ad937d2f157d9d6e0af3f03d5cfab7fec42a5c150bd6ea4d8"),
    ("C", "test-p192"): (8503, "9a41fa67f547f0074bfb7a2fdd0ca124b6da68027455741b558d06461d6e5e2d"),
    ("E", "test-p16"): (8061, "996ae7e3ea1becb7c8d6a37a89385ab1297fc219ccf8c387978747941aa27006"),
    ("E", "test-p192"): (8062, "ddc4412e5b033cda3372e070676f8686180231ff85adfc0200518bde59a8af2f"),
}
SUPPORT = {
    "ep": {"path": "engines/experiments/tcec-next/compact_ep.py", "bytes": 7267,
           "sha256": "42963c889070f29da4dc05d08d5fc4749afb7aec36b0d00735ccc9d271215c6c"},
    "projection": {"path": "engines/experiments/tcec-next/spelling_compound.py", "bytes": 9472,
                   "sha256": "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce"},
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def transform_source(source, *, family, profile_id, ep, projection):
    require(type(family) is str and type(profile_id) is str and (family, profile_id) in INPUTS,
            "finite C/E P16/P192 league EP candidate required")
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[family, profile_id],
            "exact observed league resource projection required")
    require(ep.SCHEMA == "rove4k.compact-ep-source.v1" and
            projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "explicit EP and projection owners required")
    before, after, maker = ep._regions(source, family)
    row = {"input_begin": source.index(before), "before": before.decode("ascii"),
           "after": after.decode("ascii"), "role": "private-EP-trial-to-maker",
           "component": "ep-maker-shared"}
    candidate, edits, gaps = projection._splice(source, [row])
    require(len(edits) == 1 and len(gaps) == 2 and candidate.count(maker) == 1
            and projection._inverse_edits(candidate, edits) == source,
            "one exact EP region, protected maker and complete inverse required")
    proof = {"schema": SCHEMA, "family": family, "profile_id": profile_id,
             "variant": VARIANT, "input": pin(source), "output": pin(candidate),
             "support": deepcopy(SUPPORT), "domain": deepcopy(ep.DOMAIN), "edits": edits,
             "protected_gaps": gaps, "protected_maker": pin(maker),
             "full_inverse": True, "source_only": True, "resources_changed": False,
             "models_changed": False, "features_removed": False,
             "move_encoding_changed": False, "ordering_or_ties_changed": False,
             "TT_or_atomic_publication_changed": False, "production_selected": False,
             "extra_private_state_work": True, "timing_equivalence_claimed": False,
             "native_identity_claimed": False, "runtime_qualified": False}
    return candidate, proof


def restore_source(candidate, proof, *, ep, projection):
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA
            and type(proof.get("edits")) is list and pin(candidate) == proof.get("output"),
            "league EP candidate and complete proof required")
    try:
        source = projection._inverse_edits(candidate, proof["edits"])
    except (KeyError, TypeError, IndexError, UnicodeError) as error:
        raise ValueError("malformed league EP inverse edits") from error
    require(pin(source) == proof.get("input"), "league EP inverse input differs")
    replay, expected = transform_source(source, family=proof.get("family"),
        profile_id=proof.get("profile_id"), ep=ep, projection=projection)
    require(replay == candidate and json.dumps(expected, sort_keys=True, allow_nan=False) ==
            json.dumps(proof, sort_keys=True, allow_nan=False),
            "league EP metadata, protected gaps or complete inverse differs")
    return source
