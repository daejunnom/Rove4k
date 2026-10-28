"""Shorten seven names in the exact selected full B source projections.

This is a bounded token-only spelling experiment. It does not build an
executable, choose an entry or establish runtime or competition qualification.
The constrained C lexer excludes literals, comments and directives; the complete
named input pin and reversible edit list bound its use further.
"""
from hashlib import sha256
import json
import re
from types import SimpleNamespace

SCHEMA = "rove4k.profile-b-short-names.v1"
DECLARATION = {"path": "engines/experiments/tcec-next/profile_b_w256_names.py", "variant": "b-search-names"}
INPUTS = {
    "tcec-provisional": (7936, "5f64922b49923ef9637dc41328761a4c3f4eb0063e39bd9f04c46e3d19c9b62d"),
    "test-p4": (7934, "09546a75f5e417125ec033994fec52b1e23da4d504e5146a54cead53966136ce"),
}
RENAMES = {"zU": "v", "zi": "e", "qX": "qY", "yz": "zk", "yl": "zx", "yu": "zz", "z6": "qU"}
COUNTS = {"zU": 5, "zi": 12, "qX": 7, "yz": 3, "yl": 27, "yu": 4, "z6": 3}
SCOPE = "pinned P search-function identifier tokens only; no directives, literals or comments"


def pin(data):
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _identifier_spans(text):
    """Scan the pinned ASCII input; reject C translations this scanner omits."""
    require(type(text) is str and text.isascii(), "ASCII C source required")
    require("\\\n" not in text and "\\\r\n" not in text and
            not re.search(r"\?\?[=/'()!<>-]", text), "line splices and trigraphs are unsupported")
    pos, prefix = 0, True
    while pos < len(text):
        char = text[pos]
        if char.isspace():
            if char in "\r\n":
                prefix = True
            pos += 1
            continue
        if text.startswith("//", pos) or (prefix and (char == "#" or text.startswith("%:", pos))):
            end = text.find("\n", pos)
            pos = len(text) if end < 0 else end + 1
            prefix = True
            continue
        if text.startswith("/*", pos):
            end = text.find("*/", pos + 2)
            require(end >= 0, "unterminated C comment")
            if "\n" in text[pos:end + 2]:
                prefix = True
            pos = end + 2
            continue
        prefix = False
        literal = re.match(r'(?:u8|[LuU])?(["\'])', text[pos:])
        if literal:
            quote = literal.group(1)
            pos += literal.end()
            closed = False
            while pos < len(text):
                if text[pos] == "\\":
                    pos += 2
                elif text[pos] == quote:
                    pos += 1
                    closed = True
                    break
                else:
                    require(text[pos] not in "\r\n", "unescaped newline in C literal")
                    pos += 1
            require(closed, "unterminated C literal")
            continue
        if char.isdigit() or (char == "." and pos + 1 < len(text) and text[pos + 1].isdigit()):
            end = pos + 1
            while end < len(text):
                item = text[end]
                if item.isalnum() or item in "_.'":
                    end += 1
                elif item in "+-" and text[end - 1] in "eEpP":
                    end += 1
                else:
                    break
            pos = end
            continue
        if char.isalpha() or char == "_":
            end = pos + 1
            while end < len(text) and (text[end].isalnum() or text[end] == "_"):
                end += 1
            yield pos, end, text[pos:end]
            pos = end
            continue
        require(char != "$" and not text.startswith(("\\u", "\\U"), pos),
                "nonstandard C identifier is unsupported")
        pos += 1


_LEXER = SimpleNamespace(_identifier_spans=_identifier_spans)


def _rewrite(source, lexer):
    """Apply the pinned search-scope edits and retain every untouched gap."""
    require(type(source) is bytes and hasattr(lexer, "_identifier_spans"), "bytes and the C lexer are required")
    text = source.decode("ascii")
    require(text.count("J I P(") == 1 and text.count("}void i(") == 1,
            "exact search function boundaries required")
    lo = text.index("J I P(")
    hi = text.index("}void i(", lo) + 1
    spans = list(lexer._identifier_spans(text))
    require(spans, "lexical token inventory is unavailable")
    by_name = {name: [(start, end) for start, end, token in spans if token == name]
               for name in RENAMES}
    for old, rows in by_name.items():
        require(len(rows) == COUNTS[old] and all(lo <= start < end <= hi for start, end in rows),
                "source name or its search scope differs: " + old)
        matches = [(match.start(), match.end()) for match in re.finditer(r"\b" + re.escape(old) + r"\b", text)]
        require(matches == rows,
                "source name appears outside ordinary identifier tokens: " + old)
    for target in ("qY", "zk", "zx", "zz", "qU"):
        require(not re.search(r"\b" + target + r"\b", text), "target name already exists: " + target)
    for target in ("v", "e"):
        occurrences = [(start, end) for start, end, token in spans if token == target and lo <= start < hi]
        require((target == "e" and not occurrences) or
                (target == "v" and len(occurrences) == 1 and text[occurrences[0][0]-2:occurrences[0][0]] == "->"),
                "target collides with a search local: " + target)
        require(not re.search(r"(?m)^\s*#\s*define\s+" + target + r"\b", text),
                "target collides with a preprocessor macro: " + target)
    edits = sorted((start, end, old, RENAMES[old]) for old, rows in by_name.items() for start, end in rows)
    pieces, proof, gaps = [], [], []
    old_at = new_at = 0
    for start, end, before, after in edits:
        gap = source[old_at:start]
        pieces.append(gap)
        gaps.append({"input_begin": old_at, "output_begin": new_at, **pin(gap)})
        new_at += len(gap)
        require(text[start:end] == before, "identifier span differs")
        proof.append({"input_begin": start, "output_begin": new_at, "before": before, "after": after})
        pieces.append(after.encode("ascii"))
        new_at += len(after)
        old_at = end
    gap = source[old_at:]
    pieces.append(gap)
    gaps.append({"input_begin": old_at, "output_begin": new_at, **pin(gap)})
    return b"".join(pieces), proof, gaps


def transform_source(source, *, family, profile_id, lexer=None):
    require(family == "B", "full B family required")
    require(type(profile_id) is str and profile_id in INPUTS, "named full B W256 or P4 profile required")
    require(type(source) is bytes and (len(source), sha256(source).hexdigest()) == INPUTS[profile_id],
            "exact selected full B profile source required")
    candidate, edits, gaps = _rewrite(source, _LEXER if lexer is None else lexer)
    proof = {"schema": SCHEMA, "family": "B", "profile_id": profile_id, "variant": DECLARATION["variant"],
             "input": pin(source), "output": pin(candidate), "edits": edits,
             "protected_gaps": gaps, "full_inverse": True, "scope": SCOPE,
             "resources_changed": False, "features_removed": False,
             "runtime_qualified": False, "selection_made_by_helper": False}
    return candidate, proof


def restore_source(candidate, proof, *, lexer=None):
    require(type(candidate) is bytes and type(proof) is dict and proof.get("schema") == SCHEMA
            and pin(candidate) == proof.get("output"), "exact candidate and proof required")
    restored = candidate
    for row in reversed(proof["edits"]):
        at, before, after = row["output_begin"], row["before"].encode("ascii"), row["after"].encode("ascii")
        require(type(at) is int and at >= 0 and restored[at:at + len(after)] == after,
                "inverse identifier span differs")
        restored = restored[:at] + before + restored[at + len(after):]
    repeated, expected = transform_source(restored, family=proof["family"],
                                           profile_id=proof["profile_id"], lexer=lexer)
    require(repeated == candidate and json.dumps(proof, sort_keys=True, allow_nan=False) ==
            json.dumps(expected, sort_keys=True, allow_nan=False), "inverse or protected gaps differ")
    return restored
