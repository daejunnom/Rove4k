"""Combine reviewed, disjoint league source edits on the same pinned input.

Each component first runs and inverts on its original exact control source.
This adapter merges only their non-overlapping original-coordinate edits and
proves the combined full inverse. Callers must authenticate the injected
helper and support bytes; this module does not grant runtime qualification.
"""
from hashlib import sha256
import json


SCHEMA = "rove4k.league-combined-source.v1"
VARIANTS = {
    "square-atomic": ("square", "atomic"),
    "square-ep": ("square", "ep"),
    "ep-atomic": ("ep", "atomic"),
    "square-ep-atomic": ("square", "ep", "atomic"),
}
FAMILIES = {"square-atomic": "AC", "square-ep": "C", "ep-atomic": "CE", "square-ep-atomic": "C"}
SCHEMAS = {"square": "rove4k.league-square-scan.v1",
           "ep": "rove4k.league-ep-source.v1",
           "atomic": "rove4k.league-acef-atomic.v1"}
COMPONENT_VARIANTS = {"square": "square-successor", "ep": "legal-maker", "atomic": "atomic-assignment"}
EP_SCHEMA = "rove4k.compact-ep-source.v1"
PROJECTION_SCHEMA = "rove4k.selected-spelling-compound.v1"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def pin(data):
    require(type(data) is bytes, "immutable source bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _validate_helpers(helpers, components):
    expected = set(components) | ({"ep_owner", "projection"} if "ep" in components else set())
    require(type(helpers) is dict and set(helpers) == expected, "exact component/support roles required")
    for name in components:
        module = helpers[name]
        require(getattr(module, "SCHEMA", None) == SCHEMAS[name]
                and getattr(module, "VARIANT", None) == COMPONENT_VARIANTS[name]
                and callable(getattr(module, "transform_source", None))
                and callable(getattr(module, "restore_source", None)), "component role differs: " + name)
    if "ep" in components:
        require(getattr(helpers["ep_owner"], "SCHEMA", None) == EP_SCHEMA
                and getattr(helpers["projection"], "SCHEMA", None) == PROJECTION_SCHEMA,
                "EP support roles differ")


def _component(source, *, family, profile_id, name, helpers):
    module = helpers[name]
    identity = pin(source)
    require(getattr(module, "INPUTS", {}).get((family, profile_id)) ==
            (identity["bytes"], identity["sha256"]), "component control-source pin differs: " + name)
    options = {"family": family, "profile_id": profile_id}
    inverse_options = {}
    if name == "atomic":
        options["variant"] = COMPONENT_VARIANTS[name]
    elif name == "ep":
        inverse_options = {"ep": helpers["ep_owner"], "projection": helpers["projection"]}
        options.update(inverse_options)
    candidate, proof = module.transform_source(source, **options)
    require(type(proof) is dict and proof.get("schema") == SCHEMAS[name]
            and proof.get("family") == family and proof.get("profile_id") == profile_id
            and proof.get("variant") == COMPONENT_VARIANTS[name] and proof.get("input") == identity
            and proof.get("output") == pin(candidate) and proof.get("full_inverse") is True
            and module.restore_source(candidate, proof, **inverse_options) == source,
            "component proof or full inverse differs: " + name)
    rows = proof.get("edits")
    require(type(rows) is list and len(rows) > 0, "nonempty component edit proof required")
    spans = []
    for row in rows:
        require(type(row) is dict and type(row.get("input_begin")) is int
                and row["input_begin"] >= 0 and type(row.get("before")) is str
                and type(row.get("after")) is str, "typed component edit required")
        try:
            before, after = row["before"].encode("ascii"), row["after"].encode("ascii")
        except UnicodeError as error:
            raise ValueError("ASCII component edit required") from error
        at = row["input_begin"]
        require(before and before != after and source[at:at + len(before)] == before,
                "component edit does not match original input")
        spans.append((at, before, after))
    spans.sort(key=lambda item: item[0])
    replay, old_at = bytearray(), 0
    for at, before, after in spans:
        require(at >= old_at, "component edits overlap")
        replay.extend(source[old_at:at])
        replay.extend(after)
        old_at = at + len(before)
    replay.extend(source[old_at:])
    require(bytes(replay) == candidate, "component edits do not replay its exact candidate")
    return candidate, proof, rows


def transform_source(source, *, family, profile_id, variant, helpers):
    require(type(family) is str and len(family) == 1 and type(profile_id) is str and type(variant) is str
            and variant in VARIANTS and family in FAMILIES[variant]
            and profile_id in ("test-p16", "test-p192"), "finite combined league selection required")
    pin(source)
    components = VARIANTS[variant]
    _validate_helpers(helpers, components)
    component_rows, edits = [], []
    for name in components:
        _, proof, rows = _component(source, family=family, profile_id=profile_id,
                                    name=name, helpers=helpers)
        component_rows.append({"component": name, "proof": proof})
        for row in rows:
            require(type(row) is dict and type(row.get("input_begin")) is int
                    and row["input_begin"] >= 0 and type(row.get("before")) is str
                    and type(row.get("after")) is str, "typed component edit required")
            try:
                before, after = row["before"].encode("ascii"), row["after"].encode("ascii")
            except UnicodeError as error:
                raise ValueError("ASCII component edit required") from error
            at = row["input_begin"]
            require(before and before != after and source[at:at + len(before)] == before,
                    "component edit does not match original input")
            edits.append({"component": name, "input_begin": at, "before": row["before"], "after": row["after"]})
    edits.sort(key=lambda row: row["input_begin"])
    protected_maker = None
    if "ep" in components:
        _, _, maker = helpers["ep_owner"]._regions(source, family)
        require(type(maker) is bytes and maker and source.count(maker) == 1,
                "unique original EP maker required")
        maker_at = source.index(maker)
        for row in edits:
            begin = row["input_begin"]
            end = begin + len(row["before"].encode("ascii"))
            require(end <= maker_at or begin >= maker_at + len(maker),
                    "combined edit intersects protected EP maker")
        protected_maker = {"input_begin": maker_at, **pin(maker)}
    output = bytearray()
    gaps, old_at = [], 0
    for row in edits:
        at = row["input_begin"]
        require(at >= old_at, "component source edits overlap")
        gap = source[old_at:at]
        gaps.append({"input_begin": old_at, "output_begin": len(output), **pin(gap)})
        output.extend(gap)
        row["output_begin"] = len(output)
        output.extend(row["after"].encode("ascii"))
        old_at = at + len(row["before"].encode("ascii"))
    tail = source[old_at:]
    gaps.append({"input_begin": old_at, "output_begin": len(output), **pin(tail)})
    output.extend(tail)
    candidate = bytes(output)
    require(candidate != source, "combined candidate must change source")
    if protected_maker is not None:
        require(candidate.count(maker) == 1, "combined output changed protected EP maker")
    proof = {"schema": SCHEMA, "family": family, "profile_id": profile_id, "variant": variant,
             "input": pin(source), "output": pin(candidate), "components": component_rows,
             "edits": edits, "protected_gaps": gaps, "full_inverse": True,
             "protected_ep_maker": protected_maker,
             "resources_changed": False, "features_removed": False,
             "production_selected": False, "rules_qualified": False, "runtime_qualified": False}
    return candidate, proof


def restore_source(candidate, proof, *, helpers):
    require(type(proof) is dict and proof.get("schema") == SCHEMA and pin(candidate) == proof.get("output")
            and type(proof.get("edits")) is list, "exact combined candidate and proof required")
    source = candidate
    try:
        for row in reversed(proof["edits"]):
            at = row["output_begin"]
            require(type(at) is int and at >= 0 and type(row["before"]) is str
                    and type(row["after"]) is str, "typed combined inverse required")
            before, after = row["before"].encode("ascii"), row["after"].encode("ascii")
            require(source[at:at + len(after)] == after, "combined inverse span differs")
            source = source[:at] + before + source[at + len(after):]
        rebuilt, expected = transform_source(source, family=proof["family"], profile_id=proof["profile_id"],
                                              variant=proof["variant"], helpers=helpers)
        require(rebuilt == candidate and json.dumps(proof, sort_keys=True, allow_nan=False) ==
                json.dumps(expected, sort_keys=True, allow_nan=False), "canonical combined proof differs")
    except (KeyError, TypeError, IndexError, UnicodeError) as error:
        raise ValueError("malformed combined proof") from error
    return source
