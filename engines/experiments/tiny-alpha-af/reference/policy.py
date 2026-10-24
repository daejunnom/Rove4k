"""One pinned lexical shipping policy, with no compilation or size search.

The sibling JSON is an immutable transcription of the approved read-only audit.
Only its three exact shipping inputs are admitted. The caller supplies its own
frozen rename_c module; this module neither resolves live engine paths nor
imports a compiler, preprocessor, codec, or engine. Lexical checks do not prove
C semantics: the caller must still require the original full native SHA-256
and measure the complete package before accepting a family.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re


_POLICY_SHA256 = "b3f08ba26b38dbce1e4b63d3eb98ab37f438295cfacff6037b1cfacbf7d5e5a0"
_POLICY_BYTES = Path(__file__).with_name("policy.json").read_bytes()
if hashlib.sha256(_POLICY_BYTES).hexdigest() != _POLICY_SHA256:
    raise ValueError("fixed alpha policy.json SHA-256 mismatch")

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
_WORD = re.compile(r"[A-Za-z_$][A-Za-z_0-9$]*")
_TRIGRAPH = re.compile(r"\?\?[=/'()!<>-]")
_LITERAL = re.compile(r"(?:u8|[LuU])?([\"'])")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _binding(data, expected, label):
    if len(data) != expected["bytes"] or _sha(data) != expected["sha256"]:
        raise ValueError(label + " bytes/SHA-256 mismatch")


def _logical(text):
    """Independent physical-offset map for opaque-region preservation checks."""
    chars, offsets, pos = [], [], 0
    while pos < len(text):
        if text.startswith("\\\r\n", pos):
            pos += 3
        elif text.startswith("\\\n", pos):
            pos += 2
        else:
            chars.append(text[pos])
            offsets.append(pos)
            pos += 1
    return "".join(chars), offsets


def _opaque_parts(text):
    """Inventory exact directive, comment, and quoted-literal physical bytes.

    This deliberately uses a scanner separate from the supplied identifier
    lexer. It checks preservation, not header expansion or C name resolution.
    Phase-two splicing is considered before recognizing opaque regions.
    """
    if _TRIGRAPH.search(text):
        raise ValueError("trigraph spellings are outside the fixed policy")
    logical, offsets = _logical(text)
    parts, pos, prefix = [], 0, True
    while pos < len(logical):
        char, start = logical[pos], pos
        if char.isspace():
            if char in "\r\n":
                prefix = True
            pos += 1
            continue
        kind = None
        if prefix and (char == "#" or logical.startswith("%:", pos)):
            kind = "directive"
            end = logical.find("\n", pos)
            pos = len(logical) if end < 0 else end + 1
            prefix = True
        elif logical.startswith("//", pos):
            kind = "comment"
            end = logical.find("\n", pos)
            pos = len(logical) if end < 0 else end + 1
            prefix = True
        elif logical.startswith("/*", pos):
            kind = "comment"
            end = logical.find("*/", pos + 2)
            if end < 0:
                raise ValueError("unterminated C block comment")
            pos = end + 2
            if "\n" in logical[start:pos] or "\r" in logical[start:pos]:
                prefix = True
        else:
            prefix = False
            literal = _LITERAL.match(logical, pos)
            if literal:
                kind = "literal"
                quote, pos = literal.group(1), literal.end()
                while pos < len(logical):
                    if logical[pos] == "\\":
                        pos += 2
                    elif logical[pos] == quote:
                        pos += 1
                        break
                    elif logical[pos] in "\r\n":
                        raise ValueError("unescaped newline in C quoted literal")
                    else:
                        pos += 1
                else:
                    raise ValueError("unterminated C quoted literal")
            else:
                pos += 1
        if kind:
            parts.append((kind, text[offsets[start]:offsets[pos - 1] + 1]))
    return tuple(parts)


def _rewrite(data, substitutions, *, lexer):
    """Apply a supplied fixed mapping; exposed privately for pure fixtures."""
    if not isinstance(data, bytes):
        raise ValueError("source must be immutable bytes")
    text = data.decode("utf-8")
    if not all(_IDENTIFIER.fullmatch(old) and isinstance(new, str)
               and (_IDENTIFIER.fullmatch(new) or new.isdecimal())
               for old, new in substitutions.items()):
        raise ValueError("invalid fixed substitution")
    aliases = [new for new in substitutions.values() if not new.isdecimal()]
    if len(aliases) != len(set(aliases)):
        raise ValueError("fixed aliases must be injective")
    reserved = set(_WORD.findall(text)) | set(_WORD.findall(_logical(text)[0]))
    reserved |= set(lexer._KEYWORDS) | set(substitutions) | {"main"}
    if reserved.intersection(aliases):
        raise ValueError("fixed alias is not fresh")
    opaque = _opaque_parts(text)
    output, previous, span_end, counts = [], 0, 0, Counter()
    for start, end, token in lexer._identifier_spans(text):
        if not (isinstance(start, int) and isinstance(end, int)
                and span_end <= start < end <= len(text)
                and text[start:end] == token and _IDENTIFIER.fullmatch(token)):
            raise ValueError("invalid or overlapping lexer span")
        span_end = end
        if token in substitutions:
            output.extend((text[previous:start], substitutions[token]))
            previous = end
            counts[token] += 1
    output.append(text[previous:])
    candidate = "".join(output).encode("utf-8")
    repeated = {"source.c": data}
    for old, new in substitutions.items():
        repeated = lexer._replace(repeated, old, new)
    if repeated != {"source.c": candidate}:
        raise ValueError("single-pass and repeated _replace disagree")
    if _opaque_parts(candidate.decode("utf-8")) != opaque:
        raise ValueError("directive/literal/comment bytes changed")
    return candidate, counts, opaque


def transform_source(data: bytes, *, family: str, lexer):
    """Return the sole approved candidate and source-only audit metadata.

    Unknown families, modified source, policy drift, count drift, alias
    collisions, or any unexpected result fail closed. No option changes the
    mapping, resources, accepted input identities, or expected candidate bytes.
    """
    policy = json.loads(_POLICY_BYTES)
    if not isinstance(family, str) or family not in policy["families"]:
        raise ValueError("unknown fixed alpha family")
    if not isinstance(data, bytes):
        raise ValueError("source must be immutable bytes")
    expected = policy["families"][family]
    _binding(data, expected["source"], family + " shipping input")
    mapping, resources = policy["mapping"], policy["resource_literals"]
    if len(mapping) != 89 or resources != {"WORKERS": "2", "TT_BITS": "18"}:
        raise ValueError("fixed policy shape mismatch")
    if set(mapping) != set(expected["alpha_counts"]) or set(mapping) & set(resources):
        raise ValueError("fixed policy count keys mismatch")
    if set(mapping).intersection(policy["symbol_bearing_spellings_retained"]):
        raise ValueError("symbol-bearing spelling included in fixed mapping")
    before_sha = _sha(data)
    substitutions = dict(mapping)
    substitutions.update(resources)
    candidate, counts, opaque = _rewrite(data, substitutions, lexer=lexer)
    actual_alpha = {old: counts[old] for old in mapping}
    actual_resources = {old: counts[old] for old in resources}
    if actual_alpha != expected["alpha_counts"]:
        raise ValueError("fixed alpha occurrence counts mismatch")
    if actual_resources != expected["resource_counts"]:
        raise ValueError("fixed resource occurrence counts mismatch")
    source_counts = Counter(token for _, _, token in lexer._identifier_spans(data.decode("utf-8")))
    if source_counts["PLY"] != expected["retained_PLY_count"]:
        raise ValueError("retained PLY count mismatch")
    alpha_saved = sum((len(old) - len(new)) * counts[old] for old, new in mapping.items())
    resource_saved = sum((len(old) - len(new)) * counts[old] for old, new in resources.items())
    mapping_used = sum(counts[old] > 0 for old in mapping)
    directive_bytes = sum(len(raw.encode("utf-8")) for kind, raw in opaque if kind == "directive")
    if (alpha_saved != expected["alpha_saved_bytes"]
            or resource_saved != expected["resource_saved_bytes"]
            or alpha_saved + resource_saved != expected["total_saved_bytes"]
            or len(data) - len(candidate) != expected["total_saved_bytes"]
            or mapping_used != expected["mapping_used"]
            or sum(counts.values()) != expected["source_edits_count"]
            or directive_bytes != expected["retained_directive_bytes"]):
        raise ValueError("fixed policy arithmetic/count preservation mismatch")
    _binding(candidate, expected["candidate"], family + " fixed candidate")
    if _sha(data) != before_sha:
        raise ValueError("input bytes changed")
    meta = {"family": family, "policy": policy["policy"], "policy_sha256": _POLICY_SHA256,
            "source_report_sha256": policy["source_report_sha256"],
            "expected_lexer_sha256": policy["lexer_sha256"],
            "before": dict(expected["source"]), "after": dict(expected["candidate"]),
            "mapping": mapping, "mapping_used": mapping_used, "alpha_counts": actual_alpha,
            "resource_literals": resources, "resource_counts": actual_resources,
            "alpha_saved_bytes": alpha_saved, "resource_saved_bytes": resource_saved,
            "source_saved_bytes": len(data) - len(candidate), "source_edits_count": sum(counts.values()),
            "retained_PLY_count": source_counts["PLY"], "retained_directive_bytes": directive_bytes,
            "opaque_regions_preserved": len(opaque), "replacement_methods_agree": True,
            "input_immutable": True,
            "expected_old_native": expected["expected_old_native"],
            "expected_old_whole": expected["expected_old_whole"],
            "compiler_header_native_whole_gates_executed": False,
            "scope": "lexical source identity only; no C semantic/native/package acceptance"}
    return candidate, meta
