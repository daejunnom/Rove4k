"""One finite original-coordinate union of three named spelling experiments.

Every component is derived independently from the same admitted selected full
source. This module performs no reads, builds, compression or engine execution.
The caller authenticates the exact individual helper before supplying it.
"""
from hashlib import sha256
import json

SCHEMA = "rove4k.selected-spelling-compound.v1"
VARIANT = "clock-atomic-launcher"
HELPER = "engines/experiments/tcec-next/profile_spelling.py"
HELPER_PIN = dict(bytes=9921, sha256="7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8")
COMPONENTS = ("clock-type", "atomic-assignment", "launcher-short")
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
F_SCHEMA = "rove4k.selected-spelling-compound.v2"
F_VARIANT = "clock-atomic-launcher-parentheses"
F_BASES = {
    "test-p4": (7034, "c89769c80c70722f2a610dbe9371edce9f4063abc15ed2fff6cdc637fec4bc6e"),
    "test-p28": (7067, "ad730fee827851f5833e753eb55b60453ed009987211a65d4a7bc4426ca8b5f8"),
    "tcec-provisional": (7036, "752720efdcc97c32eb79ff4796e4a0bc4cdfe4f24790863a52b585c667c1497b"),
}
F_OUTPUTS = {
    "test-p4": (7030, "0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0"),
    "test-p28": (7063, "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5"),
    "tcec-provisional": (7032, "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df"),
}
F_PARENS = (
    ("for(S q=0;q<128;q=(q+9)&~8){", "for(S q=0;q<128;q=q+9&~8){", "dead-parentheses"),
    ("for(S j=0;j<128;j=(j+9)&~8){", "for(S j=0;j<128;j=j+9&~8){", "walk-parentheses"),
)


def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def require(value, message):
    if not value:
        raise ValueError(message)


def components(family):
    require(family in ("A", "B", "C", "E", "F"), "explicit full C family required")
    return ("atomic-assignment",) if family == "B" else COMPONENTS


def _splice(source, edits):
    """Apply nonempty ASCII replacements only in original input coordinates."""
    require(type(source) is bytes, "byte source required")
    source.decode("ascii")
    old_at = new_at = 0
    pieces, rows, gaps = [], [], []
    ordered = sorted(edits, key=lambda row: row["input_begin"])
    require(ordered, "one finite compound must contain edits")
    for row in ordered:
        at, before, after = row["input_begin"], row["before"], row["after"]
        require(type(at) is int and at >= old_at and isinstance(before, str)
                and isinstance(after, str) and before and after and before != after,
                "compound edits overlap or are not nonempty replacements")
        before_bytes, after_bytes = before.encode("ascii"), after.encode("ascii")
        require(source[at:at + len(before_bytes)] == before_bytes, "original compound span differs")
        gap = source[old_at:at]
        pieces.append(gap)
        gaps.append(dict(input_begin=old_at, output_begin=new_at, **pin(gap)))
        new_at += len(gap)
        rows.append(dict(input_begin=at, output_begin=new_at, before=before,
                         after=after, role=row["role"], component=row["component"]))
        pieces.append(after_bytes)
        new_at += len(after_bytes)
        old_at = at + len(before_bytes)
    gap = source[old_at:]
    pieces.append(gap)
    gaps.append(dict(input_begin=old_at, output_begin=new_at, **pin(gap)))
    return b"".join(pieces), rows, gaps


def transform_source(source, *, family, profile_id, spelling, variant=VARIANT):
    if variant == F_VARIANT:
        return _transform_f(source, family=family, profile_id=profile_id, spelling=spelling)
    require(variant == VARIANT, "named compound variant required")
    selected = components(family)
    require(profile_id in PROFILES and type(source) is bytes
            and spelling.INPUTS.get((family, profile_id)) == (len(source), sha256(source).hexdigest())
            and spelling.SCHEMA == "rove4k.selected-spelling-experiment.v1",
            "exact selected parent and individual helper schema required")
    edits, individual = [], []
    for variant in selected:
        require(variant in spelling.available(family), "named component is unavailable")
        candidate, proof = spelling.transform_source(source, family=family,
            profile_id=profile_id, variant=variant)
        require(spelling.restore_source(candidate, proof) == source
                and proof["variant"] == variant and proof["input"] == pin(source),
                "individual component inverse or original parent differs")
        individual.append(dict(variant=variant, proof=proof))
        for row in proof["edits"]:
            edits.append(dict(input_begin=row["input_begin"], before=row["before"],
                              after=row["after"], role=row["role"], component=variant))
    candidate, rows, gaps = _splice(source, edits)
    proof = dict(schema=SCHEMA, variant=VARIANT, family=family, profile_id=profile_id,
        input=pin(source), output=pin(candidate), helper=dict(path=HELPER, **HELPER_PIN),
        components=list(selected), individual=individual, edits=rows, protected_gaps=gaps,
        full_inverse=True, original_coordinate_union=True, duplicate_best=family == "B",
        new_candidate_count=0 if family == "B" else 1, production_selected=False,
        resources_changed=False, features_removed=False,
        scope="named component union on exact selected parent; valid TCEC clocks, C11 atomics and private launcher name")
    require(candidate != source, "compound must contain a real spelling change")
    return candidate, proof


def _inverse_edits(candidate, edits):
    restored = candidate
    for row in reversed(edits):
        at, after = row["output_begin"], row["after"].encode("ascii")
        require(type(at) is int and at >= 0 and restored[at:at + len(after)] == after,
                "compound inverse span differs")
        restored = restored[:at] + row["before"].encode("ascii") + restored[at + len(after):]
    return restored


def _transform_f(source, *, family, profile_id, spelling):
    require(family == "F" and profile_id in PROFILES, "F-only compound v2 profile required")
    base, base_proof = transform_source(source, family=family, profile_id=profile_id, spelling=spelling)
    require((len(base), sha256(base).hexdigest()) == F_BASES.get(profile_id),
            "exact finite F v1 compound output required")
    edits = []
    for before, after, role in F_PARENS:
        before_bytes = before.encode("ascii")
        require(base.count(before_bytes) == 1, "one exact F scan opening required")
        edits.append(dict(input_begin=base.index(before_bytes), before=before, after=after,
                          role=role, component="scan-parentheses"))
    candidate, rows, gaps = _splice(base, edits)
    require((len(candidate), sha256(candidate).hexdigest()) == F_OUTPUTS.get(profile_id),
            "exact finite F v2 compound output required")
    proof = dict(schema=F_SCHEMA, variant=F_VARIANT, family=family, profile_id=profile_id,
        input=pin(source), output=pin(candidate), base=base_proof, edits=rows,
        protected_gaps=gaps, full_inverse=True, production_selected=False,
        resources_changed=False, features_removed=False,
        scope="F v1 compound followed by two scan successor parentheses; dependency cleanup remains later")
    return candidate, proof


def _restore_f(candidate, proof, *, spelling):
    base_proof = proof.get("base")
    require(type(candidate) is bytes and proof.get("variant") == F_VARIANT
            and proof.get("family") == "F" and proof.get("profile_id") in PROFILES
            and pin(candidate) == proof.get("output") and isinstance(base_proof, dict)
            and base_proof.get("schema") == SCHEMA and base_proof.get("variant") == VARIANT
            and base_proof.get("family") == "F"
            and base_proof.get("profile_id") == proof.get("profile_id"),
            "exact F compound v2 output and v1 base required")
    base = _inverse_edits(candidate, proof["edits"])
    require(pin(base) == base_proof.get("output"), "F compound v1 intermediate differs")
    restored = restore_source(base, base_proof, spelling=spelling)
    repeated, expected = transform_source(restored, family="F", profile_id=proof["profile_id"],
                                           spelling=spelling, variant=F_VARIANT)
    require(repeated == candidate
            and json.dumps(expected, sort_keys=True, allow_nan=False) ==
                json.dumps(proof, sort_keys=True, allow_nan=False),
            "F compound v2 inverse, base proof or protected gaps differ")
    return restored


def restore_source(candidate, proof, *, spelling):
    if proof.get("schema") == F_SCHEMA:
        return _restore_f(candidate, proof, spelling=spelling)
    require(type(candidate) is bytes and proof.get("schema") == SCHEMA
            and proof.get("variant") == VARIANT and pin(candidate) == proof.get("output"),
            "exact compound output required")
    restored = _inverse_edits(candidate, proof["edits"])
    require(pin(restored) == proof.get("input"), "compound inverse input differs")
    repeated, expected = transform_source(restored, family=proof["family"],
        profile_id=proof["profile_id"], spelling=spelling)
    require(repeated == candidate and expected == proof,
            "compound inverse, individual proofs or protected gaps differ")
    return restored
