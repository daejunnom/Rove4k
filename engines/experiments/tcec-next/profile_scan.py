"""Finite A/C valid-square projection after compound, before final cleanup.

The six literal inputs are complete reviewed sources, not learned from a run.
Only two outer loop openings change.  Bodies, resources, phase startup, SIMD,
search and protocol remain in protected byte gaps.  This pure source stage
does not admit a native image or select a production/default recipe.
"""
from hashlib import sha256
import json


SELF = "engines/experiments/tcec-next/profile_scan.py"
SCHEMA = "rove4k.selected-square-scan.v1"
VARIANT = "square-successor"
DECLARATION = {"path": SELF, "variant": VARIANT}
FAMILIES = ("A", "C")
PROFILES = ("test-p4", "test-p28", "tcec-provisional")
STAGE_ORDER = ("resource", "phase-init", "compound", VARIANT, "dependency-cleanup")
# Each row is input/output before cleanup, then input/output after cleanup.
# P4 is bridged to the separate first cost experiment. P28 comes from exact
# sealed TEST sources; W256 comes from the explicitly reviewed 15-profile
# index, with every declared current producer input independently checked.
IMAGES = {
    ("A", "test-p4"): (
        (7624, "e3dde9e31bc95be91bdf49ffc9c4f7b72f3fc816402c00855410a82c9d1e5ec3"),
        (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6"),
        (7624, "e3dde9e31bc95be91bdf49ffc9c4f7b72f3fc816402c00855410a82c9d1e5ec3"),
        (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6")),
    ("C", "test-p4"): (
        (8247, "13318ea6cd28c7b41433ad4b669bede34270143e53b9f1c4e8bd21761e170188"),
        (8218, "9a3ccb2330218ddfbf485cbf5e691197c80f34c81fee8efb36a54423c13666e8"),
        (8228, "43f4d27643a29484c4fa8f0e29072ccea460ca931a4e5855824bca4dcd70722f"),
        (8199, "86b7dd0e5f206d10086d098ce82083d4d12910df91a7f1215915727327f1d42a")),
    ("A", "test-p28"): (
        (7657, "d58e5bba1b91fe4dff59f0f4002532055e91e7afd08af7d2ee325f87f0e2a431"),
        (7628, "f1d5465716752b23c31d63035bbcb94b12818a984c9afbc4ce20c0c843f82006"),
        (7657, "d58e5bba1b91fe4dff59f0f4002532055e91e7afd08af7d2ee325f87f0e2a431"),
        (7628, "f1d5465716752b23c31d63035bbcb94b12818a984c9afbc4ce20c0c843f82006")),
    ("C", "test-p28"): (
        (8280, "edb5523685c4432747d6d13f18262756e122d559ff3b054b8df67de6b7f35cb6"),
        (8251, "192a0913e748f763a22f5a8579ee95930e5b6e368c46a5ba625b3ea87ac7edd3"),
        (8261, "75ebff57a478e285a62ee815375d89ebd45274cc6324373c682c268c1c1891b4"),
        (8232, "b3a968d2287a8418ce32b7b2f9f019c4695b55a32fd4f332eab89e16d012d2d0")),
    ("A", "tcec-provisional"): (
        (7626, "a218e141fd989501622248fad0b99231630a6ef2ea5478c28814469fef2759a8"),
        (7597, "f85fa3716aed39fe9b2ca973ac3d87650dbac95dfa9cedbaf800ada4f6375a23"),
        (7626, "a218e141fd989501622248fad0b99231630a6ef2ea5478c28814469fef2759a8"),
        (7597, "f85fa3716aed39fe9b2ca973ac3d87650dbac95dfa9cedbaf800ada4f6375a23")),
    ("C", "tcec-provisional"): (
        (8249, "2476b096224908d1306a59d74696bacfa3cc17283e4e84a46f9d88144b0cf495"),
        (8220, "31b4c0f78e211679fc8d5f502174873d2e8a3738d478a5e4d1dc32e8139fb92e"),
        (8230, "2edeae827dd092577f5cd8e5ba143271a71df09aa95e4f47780b2340f95f2efb"),
        (8201, "ae131e49609b34eefaa54499f79f2aa738d103cbc800c1d7a70cde359106b807")),
}
INPUTS = {key: value[0] for key, value in IMAGES.items()}
OUTPUTS = {key: value[1] for key, value in IMAGES.items()}
POST_DEPENDENCY_INPUTS = {key: value[2] for key, value in IMAGES.items()}
POST_DEPENDENCY_OUTPUTS = {key: value[3] for key, value in IMAGES.items()}
SPANS = {
    "A": (
        ("dead-valid-squares", "for(L q=0;q<128;q++)if(!(q&0x88)){", "for(L q=0;q<128;q=q+9&~8){"),
        ("walker-valid-squares", "for(L o=0;o<128;o++){if(o&0x88){o+=7;continue;}", "for(L o=0;o<128;o=o+9&~8){")),
    "C": (
        ("dead-valid-squares", "for(int q=0;q<128;q++)if(!(q&0x88)){", "for(int q=0;q<128;q=q+9&~8){"),
        ("walker-valid-squares", "for(int o=0;o<128;o++){if(o&0x88){o+=7;continue;}", "for(int o=0;o<128;o=o+9&~8){")),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "actual immutable source bytes required")
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("finite JSON source proof required") from error


def iteration_witness():
    """Pure order witness only; complete body bytes are protected separately."""
    expected = [16 * rank + file for rank in range(8) for file in range(8)]
    guarded = [q for q in range(128) if not q & 0x88]
    skipped, q = [], 0
    while q < 128:
        if q & 0x88:
            q += 7
        else:
            skipped.append(q)
        q += 1
    skipped_exit = q
    successor, q, maximum_sum = [], 0, 0
    while q < 128:
        successor.append(q)
        maximum_sum = max(maximum_sum, q + 9)
        q = (q + 9) & ~8
    require(guarded == skipped == successor == expected and len(expected) == 64
            and expected[-1] == 119 and q == skipped_exit == maximum_sum == 128,
            "bounded ordered valid-square witness differs")
    return dict(kind="pure-ordered-integer-enumeration", values=expected,
        count=64, first=0, last=119, exit=128, maximum_addition=128,
        guarded_body_visits_equal=True, hole_skip_body_visits_equal=True,
        source_bodies_preserved_separately=True, compiled_C_executed=False)


def _project(source, specifications):
    """Splice the two unique literal openings; no token or body rewriting."""
    require(type(source) is bytes and type(specifications) is tuple and len(specifications) == 2,
            "immutable source and exactly two literal spans required")
    rows = []
    for role, before, after in specifications:
        require(type(role) is str and type(before) is str and type(after) is str
                and before and after, "literal source span required")
        old, new = before.encode("ascii"), after.encode("ascii")
        require(source.count(old) == 1, "one exact outer scan required: " + role)
        rows.append((source.index(old), old, new, role))
    rows.sort()
    parts, edits, gaps, old_at, new_at = [], [], [], 0, 0
    for at, before, after, role in rows:
        require(at >= old_at, "outer-scan edits overlap")
        gap = source[old_at:at]
        parts.append(gap)
        gaps.append(dict(input_begin=old_at, output_begin=new_at, **pin(gap)))
        new_at += len(gap)
        edits.append(dict(role=role, input_begin=at, output_begin=new_at,
                          before=before.decode("ascii"), after=after.decode("ascii")))
        parts.append(after)
        old_at, new_at = at + len(before), new_at + len(after)
    tail = source[old_at:]
    parts.append(tail)
    gaps.append(dict(input_begin=old_at, output_begin=new_at, **pin(tail)))
    return b"".join(parts), edits, gaps


def _inverse(candidate, edits):
    require(type(candidate) is bytes and type(edits) is list and len(edits) == 2,
            "immutable candidate and exactly two inverse spans required")
    restored = candidate
    for row in reversed(edits):
        require(type(row) is dict and set(row) ==
                {"role", "input_begin", "output_begin", "before", "after"}
                and type(row["input_begin"]) is int and row["input_begin"] >= 0
                and type(row["output_begin"]) is int
                and type(row["role"]) is str and type(row["before"]) is str
                and type(row["after"]) is str and 0 < len(row["before"]) <= 128
                and 0 < len(row["after"]) <= 128,
                "exact typed source inverse span required")
        at = row["output_begin"]
        old, new = row["before"].encode("ascii"), row["after"].encode("ascii")
        require(0 <= at <= len(restored) and restored[at:at + len(new)] == new,
                "outer-scan inverse span differs")
        restored = restored[:at] + old + restored[at + len(new):]
    return restored


def transform_source(source, *, family, profile_id):
    key = family, profile_id
    require(type(family) is str and type(profile_id) is str and key in INPUTS,
            "explicit finite A/C profile required")
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[key]
            and b"\r" not in source, "exact full pre-cleanup source pin required")
    result, edits, gaps = _project(source, SPANS[family])
    require((len(result), sha256(result).hexdigest()) == OUTPUTS[key]
            and _inverse(result, edits) == source, "finite scan output or full inverse differs")
    for gap in gaps:
        before = source[gap["input_begin"]:gap["input_begin"] + gap["bytes"]]
        after = result[gap["output_begin"]:gap["output_begin"] + gap["bytes"]]
        require(before == after and pin(after) == {name: gap[name] for name in ("bytes", "sha256")},
                "outer-scan protected body/complement differs")
    return result, dict(schema=SCHEMA, family=family, profile_id=profile_id, variant=VARIANT,
        input=pin(source), output=pin(result), edits=edits, protected_gaps=gaps,
        iteration=iteration_witness(), full_inverse=True, source_regions=2,
        raw_source_delta=len(result) - len(source), stage_order=list(STAGE_ORDER),
        input_stage="after-compound-before-dependency-cleanup",
        output_stage="after-square-scan-before-dependency-cleanup",
        scope="two outer openings only; every ordered body and all other bytes protected",
        resources_changed=False, features_removed=False, engine_executed=False,
        runtime_qualified=False, rules_qualified=False, production_selected=False)


def restore_source(candidate, proof):
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA
            and type(proof.get("family")) is str and type(proof.get("profile_id")) is str,
            "exact pre-cleanup square scan proof required")
    key = proof["family"], proof["profile_id"]
    require(key in OUTPUTS and (len(candidate), sha256(candidate).hexdigest()) == OUTPUTS[key]
            and pin(candidate) == proof.get("output"), "finite scan output identity differs")
    restored = _inverse(candidate, proof.get("edits"))
    repeated, canonical = transform_source(restored, family=key[0], profile_id=key[1])
    require(repeated == candidate and _json(canonical) == _json(proof),
            "square scan proof differs from its complete canonical projection")
    return restored
