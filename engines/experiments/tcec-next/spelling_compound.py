"""One finite original-coordinate union of three named spelling experiments.

Every component is derived independently from the same admitted selected full
source. This module performs no reads, builds, compression or engine execution.
The caller authenticates the exact individual helper before supplying it.
"""
from hashlib import sha256

SCHEMA = "rove4k.selected-spelling-compound.v1"
VARIANT = "clock-atomic-launcher"
HELPER = "engines/experiments/tcec-next/profile_spelling.py"
HELPER_PIN = dict(bytes=9921, sha256="7ec393bc9c805ee8e1e6d715f40cb9883f829e3c6b01e2f71f31701e35136ea8")
COMPONENTS = ("clock-type", "atomic-assignment", "launcher-short")
PROFILES = ("test-p4", "test-p28", "tcec-provisional")


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


def transform_source(source, *, family, profile_id, spelling):
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


def restore_source(candidate, proof, *, spelling):
    require(type(candidate) is bytes and proof.get("schema") == SCHEMA
            and proof.get("variant") == VARIANT and pin(candidate) == proof.get("output"),
            "exact compound output required")
    restored = candidate
    for row in reversed(proof["edits"]):
        at, after = row["output_begin"], row["after"].encode("ascii")
        require(type(at) is int and at >= 0 and restored[at:at + len(after)] == after,
                "compound inverse span differs")
        restored = restored[:at] + row["before"].encode("ascii") + restored[at + len(after):]
    require(pin(restored) == proof.get("input"), "compound inverse input differs")
    repeated, expected = transform_source(restored, family=proof["family"],
        profile_id=proof["profile_id"], spelling=spelling)
    require(repeated == candidate and expected == proof,
            "compound inverse, individual proofs or protected gaps differ")
    return restored
