"""Finite A source compaction after the maintained dependency stage.

Only complete pinned A sources are admitted.  Replacing C identifier tokens
does not touch string or character literals, comments, or unrelated tokens.
The pinned expression substitutions have an exact inverse as well; native-image
checks remain a separate obligation.
"""
from hashlib import sha256
import json
import re

SELF = "engines/experiments/tcec-next/profile_a_shortnames.py"
SCHEMA = "rove4k.a-shortnames.v1"
DECLARATION = {"path": SELF, "variant": "shortnames-v1"}
INPUTS = {
    "test-p4": (7595, "02faeb563c435c02321fc6d497f54a31de01d9093be33bff5e44206a93dfbdc6"),
    "tcec-provisional": (7597, "f85fa3716aed39fe9b2ca973ac3d87650dbac95dfa9cedbaf800ada4f6375a23"),
}
OUTPUTS = {
    "test-p4": (7527, "f6afa9e4872dbe0a3a94ec5edd9934835bae7680bc9041a92e8d3aca8dc5f886"),
    "tcec-provisional": (7529, "e27c7609c42b9d39629a79b8b92a01b2b70cb369c6ca3e719ce22b99aef0de37"),
}
NAMES = ((b"HISTORY", b"BB", 3), (b"MOVES", b"PL", 4),
         (b"MATE", b"LL", 10), (b"PLY", b"JJ", 8))
EXPRESSIONS = ((b"strtok(NULL,", b"strtok(0,"),
               (b"(unsigned)p->aI", b"(Y)p->aI"),
               (b"if(x<0)x=0;", b"x=x<0?0:x;"),
               (b"JJ-1", b"127"), (b"JJ-2", b"126"))
_TOKEN = re.compile(rb'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*.*?\*/|//[^\n]*|[A-Za-z_][A-Za-z_0-9]*', re.S)
_IDENT = re.compile(rb"[A-Za-z_][A-Za-z_0-9]*\Z")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(data):
    require(type(data) is bytes, "immutable source bytes required")
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _project(source, names):
    """Rename exact identifier tokens with all complementary bytes preserved."""
    require(type(source) is bytes and type(names) is tuple, "immutable named projection required")
    mapping = {before: after for before, after, _ in names}
    require(len(mapping) == len(names) and len(set(mapping.values())) == len(names),
            "distinct identifier mapping required")
    matches = list(_TOKEN.finditer(source))
    identifiers = [match.group() for match in matches if _IDENT.fullmatch(match.group())]
    require(all(after not in identifiers for _, after, _ in names), "replacement identifier already exists")
    require(all(identifiers.count(before) == count for before, _, count in names),
            "identifier occurrence counts differ")
    parts, edits, position, output = [], [], 0, 0
    for match in matches:
        before = match.group()
        if before not in mapping or not _IDENT.fullmatch(before):
            continue
        gap = source[position:match.start()]
        parts.append(gap)
        output += len(gap)
        after = mapping[before]
        parts.append(after)
        edits.append({"input_begin": match.start(), "output_begin": output,
                      "before": before.decode(), "after": after.decode()})
        position, output = match.end(), output + len(after)
    parts.append(source[position:])
    return b"".join(parts), edits


def _inverse(candidate, edits):
    require(type(candidate) is bytes and type(edits) is list, "immutable inverse inputs required")
    result = candidate
    for row in reversed(edits):
        require(type(row) is dict and set(row) == {"input_begin", "output_begin", "before", "after"}
                and type(row["input_begin"]) is int and type(row["output_begin"]) is int
                and type(row["before"]) is str and type(row["after"]) is str,
                "typed inverse edit required")
        at = row["output_begin"]
        old, new = row["before"].encode("ascii"), row["after"].encode("ascii")
        require(at >= 0 and result[at:at + len(new)] == new, "inverse token differs")
        result = result[:at] + old + result[at + len(new):]
    return result


def _expressions(source):
    """Apply only single, exact pinned source spans and retain inverse offsets."""
    result, stages = source, []
    for before, after in EXPRESSIONS:
        require(result.count(before) == 1, "expression occurrence count differs")
        at = result.index(before)
        result = result[:at] + after + result[at + len(before):]
        stages.append([{ "input_begin": at, "output_begin": at,
                         "before": before.decode(), "after": after.decode() }])
    return result, stages


def _inverse_expressions(candidate, stages):
    require(type(stages) is list and len(stages) == len(EXPRESSIONS),
            "expression stages differ")
    for edits in reversed(stages):
        candidate = _inverse(candidate, edits)
    return candidate


def transform_source(source, *, family, profile_id):
    require(family == "A" and profile_id in INPUTS and type(source) is bytes
            and (len(source), sha256(source).hexdigest()) == INPUTS[profile_id],
            "exact full A source and supported profile required")
    renamed, edits = _project(source, NAMES)
    result, expression_edits = _expressions(renamed)
    require((len(result), sha256(result).hexdigest()) == OUTPUTS[profile_id]
            and _inverse(_inverse_expressions(result, expression_edits), edits) == source,
            "named output or complete inverse differs")
    proof = {"schema": SCHEMA, "family": family, "profile_id": profile_id,
             "variant": DECLARATION["variant"], "input": pin(source), "output": pin(result),
             "edits": edits, "expression_edits": expression_edits,
             "full_inverse": True, "raw_source_delta": len(result) - len(source),
             "scope": "identifier tokens and pinned expression spans; other bytes preserved",
             "features_removed": False, "engine_executed": False, "runtime_qualified": False}
    return result, proof


def restore_source(candidate, proof):
    require(type(proof) is dict and proof.get("schema") == SCHEMA and proof.get("family") == "A"
            and proof.get("profile_id") in OUTPUTS and pin(candidate) == proof.get("output"),
            "named A inverse proof required")
    original = _inverse(_inverse_expressions(candidate, proof.get("expression_edits")), proof.get("edits"))
    rebuilt, expected = transform_source(original, family="A", profile_id=proof["profile_id"])
    require(rebuilt == candidate and json.dumps(proof, sort_keys=True, separators=(",", ":")) ==
            json.dumps(expected, sort_keys=True, separators=(",", ":")), "canonical projection proof differs")
    return original
