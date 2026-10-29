"""Two opt-in TT mate-distance forms on exact full A/B/C/E profile sources.

The folded form ports the already used F idiom. The shared form gives the two
opposite adjustments one static function. This module does no I/O, imports of
project code, source-factory execution, compilation, packaging or engine execution.
The caller authenticates the existing projection owner before supplying it.

The arithmetic domain is promoted signed16 TT scores and signed32 search
scores bounded by +/-30000, with ply 0..127 on the current int32 target. It is
not a transformation for arbitrary int values: abs(INT_MIN) is undefined.
The threshold is strictly 29872; both endpoints remain unchanged. One old
adjustment cannot enter the opposite mate band. TT bits, guards, recursive
calls, learners, move ordering, workers and resource constants are protected.
Code/whole size and runtime equivalence remain separate observations.
"""
from hashlib import sha256
import json
import re


SCHEMA = "rove4k.compact-mate-source.v1"
VARIANTS = ("folded", "shared")
HELPER_NAME = "rv_mate"
PROJECTION = {
    "path": "engines/experiments/tcec-next/spelling_compound.py",
    "bytes": 9472,
    "sha256": "4e2a1599ab5b6f294b1cb59a10a1ec6667b5a2e0c993c1ce48895cddb7e55fce",
}
INPUTS = {
    ("A", "test-p4"): (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6"),
    ("A", "test-p28"): (7628, "f1d5465716752b23c31d63035bbcb94b12818a984c9afbc4ce20c0c843f82006"),
    ("B", "test-p4"): (7934, "09546a75f5e417125ec033994fec52b1e23da4d504e5146a54cead53966136ce"),
    ("B", "test-p28"): (7962, "326e18b0b480a42c16ab0c4ec06ff90770842aec2bd8c9e1ea91f70be9427eb6"),
    ("C", "test-p4"): (8199, "86b7dd0e5f206d10086d098ce82083d4d12910df91a7f1215915727327f1d42a"),
    ("C", "test-p28"): (8232, "b3a968d2287a8418ce32b7b2f9f019c4695b55a32fd4f332eab89e16d012d2d0"),
    ("E", "test-p4"): (7815, "198bccf29d1441f63e3fd07b5da9ab4164fe3c31393af7ad35ab72d4d3fe08ff"),
    ("E", "test-p28"): (7848, "de83f406f1c7916277f71e75c4b6ac2a5aa77663ab9f7e3ec2af11e8480668b8"),
}
# These bindings are in the pinned payloads, not names inferred from another
# engine. F is already folded and D compression is deliberately outside scope.
CONTEXT = {
    "A": dict(integer="L", returned="J", static="static", conditional="if", score="l", best="H", ply="d",
              positive="MATE-PLY", negative="-MATE+PLY", search="static L h(M*w,"),
    "B": dict(integer="I", returned="l", static="J", conditional="W", score="yl", best="zi", ply="n",
              positive="29872", negative="-29872", search="J I P(zd*w,"),
    "C": dict(integer="int", returned="return", static="static", conditional="if", score="l", best="H", ply="d",
              positive="30000-128", negative="-30000+128", search="static int h(ai*w,"),
    "E": dict(integer="L", returned="J", static="static", conditional="if", score="l", best="H", ply="d",
              positive="30000-128", negative="-30000+128", search="static L h(ai*w,"),
}
DOMAIN = dict(TT_score_min=-32768, TT_score_max=32767, search_score_min=-30000,
              search_score_max=30000, ply_min=0, ply_max=127, target_int_bits_min=32,
              strict_mate_threshold=29872, arbitrary_int_equivalence_claimed=False)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(value, message):
    if not value:
        raise ValueError(message)


def _admit(source, family, profile_id, variant):
    require(type(family) is str and type(profile_id) is str and (family, profile_id) in INPUTS
            and type(variant) is str and variant in VARIANTS, "finite A/B/C/E P4/P28 variant required")
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[family, profile_id],
            "exact selected full profile payload required")


def _edits(source, family, variant):
    c = CONTEXT[family]
    score, ply, cond = c["score"], c["ply"], c["conditional"]
    load = f"{cond}({score}>{c['positive']}){score}-={ply};{cond}({score}< {c['negative']}){score}+={ply};"
    store = f"{cond}({score}>{c['positive']}){score}+={ply};{cond}({score}< {c['negative']}){score}-={ply};"
    if variant == "folded":
        rows = (
            ("mate-load-folded", load, f"{cond}(abs({score})>29872){score}+={score}>0?-{ply}:{ply};"),
            ("mate-store-folded", store, f"{cond}(abs({score})>29872){score}+={score}>0?{ply}:-{ply};"),
        )
    else:
        require(not re.search(rb"\b" + HELPER_NAME.encode() + rb"\b", source), "private mate helper collides")
        helper = (f"{c['static']} {c['integer']} {HELPER_NAME}({c['integer']} x,{c['integer']} d){{"
                  f"{cond}(abs(x)>29872)x+=x>0?d:-d;{c['returned']} x;}}")
        rows = (
            ("mate-shared-owner", c["search"], helper + c["search"]),
            ("mate-load-shared", load, f"{score}={HELPER_NAME}({score},-{ply});"),
            ("mate-store-shared", f"{score}={c['best']};" + store,
             f"{score}={HELPER_NAME}({c['best']},{ply});"),
        )
    edits = []
    for role, before, after in rows:
        literal = before.encode("ascii")
        require(source.count(literal) == 1, "one exact mate consumer required: " + role)
        edits.append(dict(input_begin=source.index(literal), before=before, after=after,
                          role=role, component="mate-" + variant))
    return edits


def transform_source(source, *, family, profile_id, variant, projection):
    """Return one finite source hypothesis with a complete protected inverse."""
    _admit(source, family, profile_id, variant)
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "authenticated existing compound projection owner required")
    candidate, edits, gaps = projection._splice(source, _edits(source, family, variant))
    count = 2 if variant == "folded" else 3
    require(len(edits) == count and len(gaps) == count + 1
            and projection._inverse_edits(candidate, edits) == source, "mate edits or full inverse differ")
    proof = dict(schema=SCHEMA, family=family, profile_id=profile_id, variant=variant,
                 input=pin(source), output=pin(candidate), projection=dict(PROJECTION), domain=dict(DOMAIN),
                 edits=edits, protected_gaps=gaps, full_inverse=True, source_only=True,
                 resources_changed=False, features_removed=False, production_selected=False,
                 native_identity_claimed=False, runtime_equivalence_claimed=False)
    return candidate, proof


def restore_source(candidate, proof, *, projection):
    """Restore and replay all typed metadata, edits and protected source gaps."""
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA
            and type(proof.get("edits")) is list and pin(candidate) == proof.get("output"),
            "mate source candidate and complete proof required")
    require(projection.SCHEMA == "rove4k.selected-spelling-compound.v1",
            "authenticated existing compound projection owner required")
    source = projection._inverse_edits(candidate, proof["edits"])
    _admit(source, proof.get("family"), proof.get("profile_id"), proof.get("variant"))
    require(pin(source) == proof.get("input"), "mate source inverse input differs")
    replay, expected = transform_source(source, family=proof["family"], profile_id=proof["profile_id"],
                                        variant=proof["variant"], projection=projection)
    require(replay == candidate and
            json.dumps(expected, sort_keys=True, allow_nan=False) ==
            json.dumps(proof, sort_keys=True, allow_nan=False), "mate proof, typed metadata or inverse differs")
    return source
