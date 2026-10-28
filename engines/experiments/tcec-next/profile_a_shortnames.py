"""Finite A source-name compaction after the maintained dependency stage.

Only complete pinned A sources are admitted.  Replacing C identifier tokens
does not touch string or character literals, comments, or unrelated tokens.
The full inverse and named native-image checks remain separate obligations.
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
    "test-p4": (7540, "79074cfacf8225df8285bcdca08931a42d8270a48e560b3a8c48937f225fab36"),
    "tcec-provisional": (7542, "8144c429c67b8c41611996cb50e8fda2e85359d7389df0836321836d5f7195ef"),
}
NAMES = ((b"HISTORY", b"BB", 3), (b"MOVES", b"PL", 4),
         (b"MATE", b"LL", 10), (b"PLY", b"JJ", 8))
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


def transform_source(source, *, family, profile_id):
    require(family == "A" and profile_id in INPUTS and type(source) is bytes
            and (len(source), sha256(source).hexdigest()) == INPUTS[profile_id],
            "exact full A source and supported profile required")
    result, edits = _project(source, NAMES)
    require((len(result), sha256(result).hexdigest()) == OUTPUTS[profile_id]
            and _inverse(result, edits) == source, "named output or complete inverse differs")
    proof = {"schema": SCHEMA, "family": family, "profile_id": profile_id,
             "variant": DECLARATION["variant"], "input": pin(source), "output": pin(result),
             "edits": edits, "full_inverse": True, "raw_source_delta": len(result) - len(source),
             "scope": "identifier tokens only; literals, comments and other bytes preserved",
             "features_removed": False, "engine_executed": False, "runtime_qualified": False}
    return result, proof


def restore_source(candidate, proof):
    require(type(proof) is dict and proof.get("schema") == SCHEMA and proof.get("family") == "A"
            and proof.get("profile_id") in OUTPUTS and pin(candidate) == proof.get("output"),
            "named A inverse proof required")
    original = _inverse(candidate, proof.get("edits"))
    rebuilt, expected = transform_source(original, family="A", profile_id=proof["profile_id"])
    require(rebuilt == candidate and json.dumps(proof, sort_keys=True, separators=(",", ":")) ==
            json.dumps(expected, sort_keys=True, separators=(",", ":")), "canonical projection proof differs")
    return original
