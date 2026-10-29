"""Opt-in A/C P16/P192 square scanning on actual league control sources.

Pins identify the complete ``resource-projection.c`` files produced by
GitHub Actions run 40530103670.  This is a pure reversible source experiment:
it does not select a producer or attest to size, rules, native or runtime.
"""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path


SCHEMA = "rove4k.league-square-scan.v1"
VARIANT = "square-successor"
INPUTS = {
    ("A", "test-p16"): (7868, "dfea3d86ab55b725ebc09e37b00a4053be1039b5bcd50b0c73d82aaaaf5c4ead"),
    ("A", "test-p192"): (7869, "c02da48b86de955f13f7d0442d5a1804e3eb91253d15160186a72dd116c0d910"),
    ("C", "test-p16"): (8502, "d85638b93ceefd6ad937d2f157d9d6e0af3f03d5cfab7fec42a5c150bd6ea4d8"),
    ("C", "test-p192"): (8503, "9a41fa67f547f0074bfb7a2fdd0ca124b6da68027455741b558d06461d6e5e2d"),
}
OUTPUTS = {
    ("A", "test-p16"): (7839, "2050992258ac3e074b5f8791159b2fed55a3a30ead872ef264091d103756ba72"),
    ("A", "test-p192"): (7840, "db04a7827768fef98c8947828dd61cce9a2fdd1354fd271a086238838d33fecf"),
    ("C", "test-p16"): (8473, "9341ba716a5cae4a3caa2b8de5fee73d4924db21c05b55b8a329d2e93b92f8f4"),
    ("C", "test-p192"): (8474, "440ccf24cf6e7305c6fccbbb71650157000a4a55e09eda0da18c540934ebbdeb"),
}


def _load_scan():
    spec = importlib.util.spec_from_file_location("rove_league_square_scan", Path(__file__).with_name("profile_scan.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pin(source):
    if type(source) is not bytes:
        raise ValueError("immutable source bytes required")
    return {"bytes": len(source), "sha256": sha256(source).hexdigest()}


def transform_source(source, *, family, profile_id):
    key = (family, profile_id)
    identity = _pin(source)
    if key not in INPUTS or tuple(identity.values()) != INPUTS[key] or b"\r" in source:
        raise ValueError("exact observed A/C league control source required")
    scan = _load_scan()
    candidate, edits, gaps = scan._project(source, scan.SPANS[family])
    output = _pin(candidate)
    if tuple(output.values()) != OUTPUTS[key] or scan._inverse(candidate, edits) != source:
        raise ValueError("finite league output or inverse differs")
    for gap in gaps:
        old = source[gap["input_begin"]:gap["input_begin"] + gap["bytes"]]
        new = candidate[gap["output_begin"]:gap["output_begin"] + gap["bytes"]]
        if old != new or _pin(old) != {k: gap[k] for k in ("bytes", "sha256")}:
            raise ValueError("protected region changed")
    return candidate, {
        "schema": SCHEMA, "family": family, "profile_id": profile_id,
        "variant": VARIANT, "input": identity, "output": output,
        "edits": edits, "protected_gaps": gaps, "iteration": scan.iteration_witness(),
        "full_inverse": True, "raw_source_delta": len(candidate) - len(source),
        "scope": "two valid-square scan openings; all other bytes preserved",
        "resources_changed": False, "features_removed": False,
        "production_selected": False, "rules_qualified": False, "runtime_qualified": False,
    }


def restore_source(candidate, proof):
    if type(proof) is not dict or proof.get("schema") != SCHEMA or _pin(candidate) != proof.get("output"):
        raise ValueError("exact candidate and proof required")
    scan = _load_scan()
    source = scan._inverse(candidate, proof.get("edits"))
    rebuilt, expected = transform_source(source, family=proof.get("family"), profile_id=proof.get("profile_id"))
    if rebuilt != candidate or json.dumps(proof, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ValueError("canonical league inverse or proof differs")
    return source
