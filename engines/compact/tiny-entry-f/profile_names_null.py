"""F-only final C spellings with exact source pins and reversible edits.

The selected variant changes pointer null constants, three macro names, and
two equivalent expressions. Native identity and runtime qualification are not
implied by the source transformation itself.
"""
from __future__ import annotations

import hashlib
import re

SCHEMA = "rove4k-f-final-spelling-v1"
DECLARATION = {"path": "engines/compact/tiny-entry-f/profile_names_null.py", "variant": "names-null"}

INPUTS = {
    "test-p4": (7030, "0aa062ec8440911d094a1b4eea48eceb96facfaa4ce94d654f46bfa19c83c7f0"),
    "test-p28": (7063, "5a016f252e8efb4faf356de92397964d19e6c5e95863e063a5179864988dcdc5"),
    "tcec-provisional": (7032, "7701b38ad0957066d427bb085575f26b511691a6ea60e67f44835ce9359db9df"),
}
OUTPUTS = {
    "names-null": {
        "test-p4": (6989, "6d849252d5994d531399b5eb57f915c1ff3ff3ca79a4674591ac074c30a97730"),
        "test-p28": (7022, "5e36e83138e24172ac0ba66fd654f0a396c2882e5ef56cda3e1eff27111f50e7"),
        "tcec-provisional": (6991, "5e46fd242e777c79c45ceda782be430476a6b650a35d24eb2e2636f7f4a461a2"),
    },
}
TOKENS = ((b"NULL", b"0", 4), (b"PROMO", b"qO", 8),
          (b"MOVE", b"qe", 3), (b"aa", b"qt", 28))
EXPRESSIONS = ((b"!(w->e&255)", b"w->e%256==0"),
               (b"t->s=-s;", b"t->s*=-1;"))


def pin(data):
    return (len(data), hashlib.sha256(data).hexdigest())


def _edits(source, variant):
    rows = []
    for before, after, count in TOKENS:
        pattern = rb"\b" + before + rb"\b"
        matches = list(re.finditer(pattern, source))
        if len(matches) != count:
            raise ValueError("F token role differs")
        if after != b"0" and re.search(rb"\b" + after + rb"\b", source):
            raise ValueError("F replacement identifier is already used")
        rows.extend((match.start(), before, after) for match in matches)
    for before, after in EXPRESSIONS:
        if source.count(before) != 1:
            raise ValueError("F expression role differs")
        rows.append((source.index(before), before, after))
    return sorted(rows)


def transform_source(source, *, family, profile_id, variant="names-null"):
    if (type(source) is not bytes or family != "F" or variant not in OUTPUTS or
            profile_id not in INPUTS or pin(source) != INPUTS[profile_id]):
        raise ValueError("unknown full F selected source")
    cursor = 0
    result = bytearray()
    edits = []
    for offset, before, after in _edits(source, variant):
        if offset < cursor or source[offset:offset + len(before)] != before:
            raise ValueError("overlapping F source edits")
        result.extend(source[cursor:offset])
        edits.append({"offset": len(result), "before": before.decode("ascii"),
                      "after": after.decode("ascii")})
        result.extend(after)
        cursor = offset + len(before)
    result.extend(source[cursor:])
    candidate = bytes(result)
    if pin(candidate) != OUTPUTS[variant][profile_id]:
        raise ValueError("F selected output differs")
    return candidate, {"format": SCHEMA, "schema": SCHEMA, "family": family,
                       "profile_id": profile_id, "variant": variant,
                       "input": list(pin(source)), "output": list(pin(candidate)), "edits": edits}


def restore_source(candidate, proof):
    if (type(candidate) is not bytes or type(proof) is not dict or
            set(proof) != {"format", "schema", "family", "profile_id", "variant", "input", "output", "edits"} or
            proof["format"] != SCHEMA or proof["schema"] != SCHEMA or proof["family"] != "F" or
            proof["variant"] not in OUTPUTS or proof["profile_id"] not in INPUTS or
            list(pin(candidate)) != proof["output"] or type(proof["edits"]) is not list):
        raise ValueError("invalid F spelling inverse proof")
    cursor = 0
    result = bytearray()
    for row in proof["edits"]:
        if type(row) is not dict or set(row) != {"offset", "before", "after"}:
            raise ValueError("invalid F spelling edit")
        offset = row["offset"]
        if type(offset) is not int or offset < cursor or type(row["before"]) is not str or type(row["after"]) is not str:
            raise ValueError("invalid F spelling offset")
        try:
            before, after = row["before"].encode("ascii"), row["after"].encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError("non-ASCII F spelling edit") from error
        if not before or not after or candidate[offset:offset + len(after)] != after:
            raise ValueError("F spelling output span differs")
        result.extend(candidate[cursor:offset])
        result.extend(before)
        cursor = offset + len(after)
    result.extend(candidate[cursor:])
    original = bytes(result)
    replay, replay_proof = transform_source(original, family="F", profile_id=proof["profile_id"], variant=proof["variant"])
    if replay != candidate or replay_proof != proof:
        raise ValueError("F spelling inverse does not replay")
    return original
