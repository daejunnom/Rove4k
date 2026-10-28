"""E-only fixed-model source stage, selected explicitly; no GO authority.

The selected E model has exact coefficients 1, 2 and 4 in the three guarded
integer expressions below.  Substitution preserves their C integer promotions
and grouping.  This applies only to the exact generated fixed-model spelling;
it does not accept other models, user-supplied coefficients or DEV sources.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

SCHEMA = "rove4k.e-fixed-coeff-macros.v1"
DECLARATION = {"path": "engines/compact/tiny-entry-e/profile_eval_unit.py",
               "variant": "e-fixed-coeff-macros"}
TABLE = b"static const X qi[21]={0,100,320,330,500,900,0,3,8,5,2,1,-3,6,10,1,16,-1,12,2,4};"
# Generated E source from this branch's explicit control/legal-maker P4 and
# W256 profiles; a changed producer requires a new independently reviewed pin.
INPUT_SHA256 = frozenset({
    "d3069c36dec5becdca14b69e49016b9a3a6b4c762da91471e7ba8c73debad4f3",
    "198bccf29d1441f63e3fd07b5da9ab4164fe3c31393af7ad35ab72d4d3fe08ff",
    "d9da4822b16da457786b6517675015c7a91c110a6685ffb9444eea945bbcff58",
    "fc08a94db7593439322910bdc6bc3be307a1a8c3e65f948842a15f1cf7b95335",
})
PROFILE_BY_SOURCE_SHA = {
    "d3069c36dec5becdca14b69e49016b9a3a6b4c762da91471e7ba8c73debad4f3": ("tcec-provisional", "control"),
    "198bccf29d1441f63e3fd07b5da9ab4164fe3c31393af7ad35ab72d4d3fe08ff": ("test-p4", "control"),
    "d9da4822b16da457786b6517675015c7a91c110a6685ffb9444eea945bbcff58": ("tcec-provisional", "legal-maker"),
    "fc08a94db7593439322910bdc6bc3be307a1a8c3e65f948842a15f1cf7b95335": ("test-p4", "legal-maker"),
}
EDITS = (
    (b"qi[15]*p->a*abs(p->a)", b"p->a*abs(p->a)"),
    (b"qi[19]*(Q(P)-Q(o))", b"2*(Q(P)-Q(o))"),
    (b"qi[20]*((P>>4)-(o>>4))*p->s", b"4*((P>>4)-(o>>4))*p->s"),
)
COEFFICIENT_RESULT_SHA256 = frozenset({
    "ddda40981838bf1eed6dd64b0a1f5a44bc317466d4cc14d0480a9bbe3db85d99",
    "c5394389bd6ec749158b62250c8c0e02b9d2f318025ea59cf3965bcb5ec71596",
    "02d4f436c032e374cff599e0334796a5b71ee11b6f828534a28b93aebd5667a6",
    "85b145b40964f6330133436bf34b9d7f987939952a65e838eda5ea695231cca7",
})
MACRO_EDITS = ((b"FROM", b"TT"), (b"MOVE", b"YX"), (b"PROMO", b"XX"))
# Exact-context substitutions after the model/macro stage.  The outer input
# digest pins the whole producer source; these anchors make inversion unique.
FINAL_EDITS = (
    (b'nt(void){J strtok(NULL,', b'nt(void){J strtok(0,'),
    (b'(d==128-1)*2', b'(d==127)*2'),
    (b'C<=128-2;C++', b'C<=126;C++'),
    (b'for(L f=0;f<8;f++){b(&t,f,qa[f]);',
     b'for(L f=0;f!=8;f++){b(&t,f,qa[f]);'),
)


def transform_final(source: bytes) -> tuple[bytes, dict]:
    result = source
    for before, after in FINAL_EDITS:
        if result.count(before) != 1 or result.count(after):
            raise ValueError("the guarded E final expression layout differs")
        result = result.replace(before, after, 1)
    restored = result
    for before, after in reversed(FINAL_EDITS):
        if restored.count(after) != 1 or restored.count(before):
            raise ValueError("the E final expression inverse is ambiguous")
        restored = restored.replace(after, before, 1)
    if restored != source:
        raise ValueError("the E final expression inverse differs")
    return result, {
        "source_bytes": len(source), "source_sha256": sha256(source).hexdigest(),
        "result_bytes": len(result), "result_sha256": sha256(result).hexdigest(),
        "inverse_exact": True, "source_only": True, "runtime_qualified": False,
    }



def transform(source: bytes) -> tuple[bytes, dict]:
    """Apply three exact fixed-coefficient rewrites with a byte-exact inverse."""
    if type(source) is not bytes or sha256(source).hexdigest() not in INPUT_SHA256:
        raise ValueError("an independently pinned E source is required")
    if source.count(TABLE) != 1:
        raise ValueError("one exact E fixed-model table is required")
    if any(source.count(before) != 1 or source.count(after) != int(after in before)
           for before, after in EDITS):
        raise ValueError("the guarded E expression layout differs")
    result = source
    for before, after in EDITS:
        result = result.replace(before, after, 1)
    restored = result
    for before, after in reversed(EDITS):
        if restored.count(after) != 1:
            raise ValueError("the E expression inverse is ambiguous")
        restored = restored.replace(after, before, 1)
    if restored != source:
        raise ValueError("the E expression inverse differs")
    return result, {
        "source_bytes": len(source), "source_sha256": sha256(source).hexdigest(),
        "result_bytes": len(result), "result_sha256": sha256(result).hexdigest(),
        "inverse_exact": True, "model": "fixed E 21 coefficient table",
        "source_only": True, "runtime_qualified": False,
    }


def transform_macros(source: bytes) -> tuple[bytes, dict]:
    """Rename E's three macro identifiers after the coefficient projection.

    The input is pinned in full: this byte-level projection is not a general C
    lexer, and makes no claims for arbitrary sources, strings or directives.
    """
    if type(source) is not bytes or sha256(source).hexdigest() not in COEFFICIENT_RESULT_SHA256:
        raise ValueError("the independently pinned E coefficient result is required")
    result = source
    for before, after in MACRO_EDITS:
        if result.count(b"#define " + before + b"(") != 1 or re.search(rb"\b" + after + rb"\b", result):
            raise ValueError("the guarded E macro identifiers differ")
        result = re.sub(rb"\b" + before + rb"\b", after, result)
    restored = result
    for before, after in reversed(MACRO_EDITS):
        restored = re.sub(rb"\b" + after + rb"\b", before, restored)
    if restored != source:
        raise ValueError("the E macro inverse differs")
    return result, {
        "source_bytes": len(source), "source_sha256": sha256(source).hexdigest(),
        "result_bytes": len(result), "result_sha256": sha256(result).hexdigest(),
        "inverse_exact": True, "source_only": True, "runtime_qualified": False,
    }


def transform_source(source: bytes, *, family: str, profile_id: str) -> tuple[bytes, dict]:
    """Apply the selected E stages; an explicit source digest fixes EP variant."""
    if type(source) is not bytes or family != "E" or type(profile_id) is not str:
        raise ValueError("the E family and a supported profile are required")
    selected = PROFILE_BY_SOURCE_SHA.get(sha256(source).hexdigest())
    if selected is None or selected[0] != profile_id:
        raise ValueError("the pinned E source and profile differ")
    coefficient, first = transform(source)
    macros, second = transform_macros(coefficient)
    result, third = transform_final(macros)
    proof = {"schema": SCHEMA, "family": family, "profile_id": profile_id,
             "variant": DECLARATION["variant"], "ep_variant": selected[1],
             "input": {"bytes": len(source), "sha256": sha256(source).hexdigest()},
             "output": {"bytes": len(result), "sha256": sha256(result).hexdigest()},
             "components": [first, second, third], "full_inverse": True,
             "source_only": True, "runtime_qualified": False}
    return result, proof


def restore_source(candidate: bytes, proof: dict) -> bytes:
    """Replay an exact proof and recover the complete original source."""
    if (type(candidate) is not bytes or type(proof) is not dict or proof.get("schema") != SCHEMA or
            proof.get("output") != {"bytes": len(candidate), "sha256": sha256(candidate).hexdigest()}):
        raise ValueError("the exact E candidate and proof are required")
    source = candidate
    for before, after in reversed(FINAL_EDITS):
        if source.count(after) != 1 or source.count(before):
            raise ValueError("the E final expression inverse is ambiguous")
        source = source.replace(after, before, 1)
    for before, after in reversed(MACRO_EDITS):
        source = re.sub(rb"\b" + after + rb"\b", before, source)
    for before, after in reversed(EDITS):
        if source.count(after) != 1:
            raise ValueError("the E coefficient inverse is ambiguous")
        source = source.replace(after, before, 1)
    rebuilt, expected = transform_source(source, family=proof.get("family"), profile_id=proof.get("profile_id"))
    if (rebuilt != candidate or json.dumps(proof, sort_keys=True, allow_nan=False) !=
            json.dumps(expected, sort_keys=True, allow_nan=False)):
        raise ValueError("the canonical E source proof differs")
    return source
