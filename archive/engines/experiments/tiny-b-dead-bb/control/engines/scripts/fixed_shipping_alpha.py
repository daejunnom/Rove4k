"""Fixed shipping alpha/resource policy for the maintained B/C/E recipes.

This standalone ordinary helper embeds one readable JSON policy verbatim and
checks its SHA-256 before use. There are no runtime side files or engine-source
path dependencies. Only three exact shipping inputs are admitted; the fixed 89
private identifier aliases and WORKERS=2/TT_BITS=18 have no search or variants.
The caller supplies its pinned lexer and owns the actual header, complete native
SHA-256, and complete-package checks. Lexical checks are not a C semantic proof.
"""

from collections import Counter
import hashlib
import json
import re


_POLICY_SHA256 = "b3f08ba26b38dbce1e4b63d3eb98ab37f438295cfacff6037b1cfacbf7d5e5a0"
_POLICY_BYTES = r'''{
  "format": 1,
  "policy": "fixed89-alpha-resource-20261020",
  "source_checkpoint": "829f27d1338be6fd9f3f2a270239bdc6e3d89a27",
  "source_report_sha256": "7a49e468018e026e2ea95676bf09eeef7ab2e3c7b07c5c8cb0e20170288cfb9d",
  "lexer_sha256": "9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5",
  "scope": "Exact maintained shipping sources B6219/C5947/E5899 only. Lexical source transformation; actual header/native/whole gates belong to the caller.",
  "mapping": {
    "Board": "za",
    "Entry": "zb",
    "Exchange": "zc",
    "Worker": "zd",
    "advance": "ze",
    "alpha": "zf",
    "bad": "zg",
    "base": "zh",
    "best": "zi",
    "bestmove": "zj",
    "beta": "zk",
    "bishops": "zl",
    "black": "zm",
    "bonus": "zn",
    "bound": "zo",
    "budget": "zp",
    "candidates": "zq",
    "cell": "zr",
    "center": "zs",
    "check": "zt",
    "colors": "zu",
    "complete": "zv",
    "continuation": "zw",
    "correction": "zx",
    "count": "zy",
    "created": "zz",
    "data": "zA",
    "depth": "zB",
    "draw": "zC",
    "end": "zD",
    "error": "zE",
    "evaluation": "zF",
    "excluded": "zG",
    "extension": "zH",
    "file": "zI",
    "from": "zJ",
    "gain": "zK",
    "half": "zL",
    "history": "zM",
    "home": "zN",
    "inc": "zO",
    "key": "zP",
    "keys": "zQ",
    "knights": "zR",
    "last": "zS",
    "learning": "zT",
    "legal": "zU",
    "length": "zV",
    "line": "zW",
    "list": "zX",
    "lock": "zY",
    "minors": "zZ",
    "move": "z0",
    "moves": "z1",
    "name": "z2",
    "next": "z3",
    "nodes": "z4",
    "occupied": "z5",
    "old": "z6",
    "pawns": "z7",
    "pieces": "z8",
    "ply": "z9",
    "present": "ya",
    "prior": "yb",
    "prom": "yc",
    "promotion": "yd",
    "quiet": "ye",
    "rank": "yf",
    "reduce": "yg",
    "repetitions": "yh",
    "rook": "yi",
    "root": "yj",
    "save": "yk",
    "score": "yl",
    "scores": "ym",
    "seen": "yn",
    "shift": "yo",
    "side": "yp",
    "sign": "yq",
    "singular": "yr",
    "status": "ys",
    "sum": "yt",
    "tactical": "yu",
    "target": "yv",
    "threads": "yw",
    "threshold": "yx",
    "transit": "yy",
    "ttdepth": "yz",
    "visits": "yA"
  },
  "resource_literals": {
    "TT_BITS": "18",
    "WORKERS": "2"
  },
  "symbol_bearing_spellings_retained": [
    "table",
    "workers",
    "stopped",
    "deadline",
    "game_keys",
    "game_length",
    "position",
    "steps",
    "material",
    "back",
    "tiny_weights",
    "tiny_table",
    "mutex",
    "command",
    "finished",
    "epoch",
    "pending",
    "ready",
    "quitting",
    "fallback",
    "tiny_eval_init"
  ],
  "families": {
    "B": {
      "source": {
        "bytes": 15566,
        "sha256": "eea1fe5f60c56aa90d2d51f3fa5a1aa56a63318527943500aa02d0105668f910"
      },
      "candidate": {
        "bytes": 13606,
        "sha256": "abc1e1c734d10211e8b9f0a5fc2b97c20f931f08a33c639cd7739f349b4106d7"
      },
      "readable_sha256": "1f879828346dfbc6023f6abfbbf1e1d2062e8e2dc0e9919aade254ba7a0a97f6",
      "recipe_sha256": "be4a9a2dda5136ac7a89431fb93cbf9674a0bdac403a9e252e0835b82a0de681",
      "alpha_counts": {
        "Board": 28,
        "Entry": 3,
        "Exchange": 3,
        "Worker": 8,
        "advance": 2,
        "alpha": 18,
        "bad": 3,
        "base": 0,
        "best": 27,
        "bestmove": 6,
        "beta": 8,
        "bishops": 0,
        "black": 0,
        "bonus": 6,
        "bound": 10,
        "budget": 9,
        "candidates": 5,
        "cell": 3,
        "center": 2,
        "check": 6,
        "colors": 3,
        "complete": 4,
        "continuation": 3,
        "correction": 4,
        "count": 5,
        "created": 8,
        "data": 16,
        "depth": 28,
        "draw": 4,
        "end": 4,
        "error": 6,
        "evaluation": 3,
        "excluded": 7,
        "extension": 3,
        "file": 2,
        "from": 42,
        "gain": 7,
        "half": 8,
        "history": 3,
        "home": 12,
        "inc": 4,
        "key": 11,
        "keys": 9,
        "knights": 3,
        "last": 2,
        "learning": 7,
        "legal": 5,
        "length": 6,
        "line": 16,
        "list": 9,
        "lock": 4,
        "minors": 4,
        "move": 3,
        "moves": 21,
        "name": 3,
        "next": 5,
        "nodes": 5,
        "occupied": 2,
        "old": 10,
        "pawns": 0,
        "pieces": 0,
        "ply": 15,
        "present": 3,
        "prior": 3,
        "prom": 3,
        "promotion": 6,
        "quiet": 4,
        "rank": 4,
        "reduce": 5,
        "repetitions": 3,
        "rook": 2,
        "root": 3,
        "save": 8,
        "score": 36,
        "scores": 8,
        "seen": 3,
        "shift": 3,
        "side": 9,
        "sign": 0,
        "singular": 3,
        "status": 7,
        "sum": 0,
        "tactical": 4,
        "target": 15,
        "threads": 3,
        "threshold": 4,
        "transit": 2,
        "ttdepth": 3,
        "visits": 2
      },
      "resource_counts": {
        "TT_BITS": 3,
        "WORKERS": 7
      },
      "mapping_used": 82,
      "source_edits_count": 619,
      "alpha_saved_bytes": 1903,
      "resource_saved_bytes": 57,
      "total_saved_bytes": 1960,
      "retained_directive_bytes": 464,
      "retained_PLY_count": 9,
      "expected_old_native": {
        "bytes": 26592,
        "sha256": "221a865e2712cb3e704128e0ae8353edd358343f564fe53093040f6515d522ec"
      },
      "expected_old_whole": {
        "bytes": 6219,
        "sha256": "01261167253dd89a0e2d88aded2ee493fc0ffaec34cd2322459ddbc515f8aefd"
      }
    },
    "C": {
      "source": {
        "bytes": 14206,
        "sha256": "dcbfb3e92b52e2ee902055aa7331c068b6b95226f00b1edfc4b63b789405105c"
      },
      "candidate": {
        "bytes": 12526,
        "sha256": "5b0bebf394c7774bcd6d0b677d11537a44e7dc0850cb6d38331bd4d97eb99bb3"
      },
      "readable_sha256": "1f0f18ffee91ecddea3cb31e7553e1d1415e25b3f759cdec4e0f375fcd0b2298",
      "recipe_sha256": "b0ccd6366416b1edc1eccaf8718c6c348e2445e2e67b72cfa0333f36b29ff062",
      "alpha_counts": {
        "Board": 27,
        "Entry": 3,
        "Exchange": 0,
        "Worker": 7,
        "advance": 2,
        "alpha": 18,
        "bad": 3,
        "base": 4,
        "best": 23,
        "bestmove": 6,
        "beta": 8,
        "bishops": 0,
        "black": 0,
        "bonus": 6,
        "bound": 8,
        "budget": 9,
        "candidates": 0,
        "cell": 3,
        "center": 2,
        "check": 6,
        "colors": 3,
        "complete": 0,
        "continuation": 3,
        "correction": 4,
        "count": 5,
        "created": 8,
        "data": 15,
        "depth": 27,
        "draw": 4,
        "end": 4,
        "error": 6,
        "evaluation": 8,
        "excluded": 0,
        "extension": 0,
        "file": 2,
        "from": 39,
        "gain": 0,
        "half": 14,
        "history": 3,
        "home": 12,
        "inc": 4,
        "key": 11,
        "keys": 9,
        "knights": 3,
        "last": 2,
        "learning": 0,
        "legal": 5,
        "length": 6,
        "line": 16,
        "list": 9,
        "lock": 4,
        "minors": 4,
        "move": 3,
        "moves": 29,
        "name": 3,
        "next": 0,
        "nodes": 5,
        "occupied": 0,
        "old": 5,
        "pawns": 0,
        "pieces": 2,
        "ply": 13,
        "present": 3,
        "prior": 3,
        "prom": 3,
        "promotion": 3,
        "quiet": 3,
        "rank": 4,
        "reduce": 5,
        "repetitions": 3,
        "rook": 2,
        "root": 3,
        "save": 8,
        "score": 34,
        "scores": 10,
        "seen": 3,
        "shift": 3,
        "side": 6,
        "sign": 0,
        "singular": 0,
        "status": 7,
        "sum": 5,
        "tactical": 4,
        "target": 8,
        "threads": 3,
        "threshold": 0,
        "transit": 2,
        "ttdepth": 2,
        "visits": 0
      },
      "resource_counts": {
        "TT_BITS": 3,
        "WORKERS": 7
      },
      "mapping_used": 73,
      "source_edits_count": 562,
      "alpha_saved_bytes": 1623,
      "resource_saved_bytes": 57,
      "total_saved_bytes": 1680,
      "retained_directive_bytes": 455,
      "retained_PLY_count": 12,
      "expected_old_native": {
        "bytes": 26464,
        "sha256": "c948e31aea9f413614881b8e8e6060e5aa70314dd84b2d9b544e3f20edb99df2"
      },
      "expected_old_whole": {
        "bytes": 5947,
        "sha256": "76ed08f657398ac4b8cfbd0ff2230257ab18547f082b4c29af62428d802f33d3"
      }
    },
    "E": {
      "source": {
        "bytes": 14352,
        "sha256": "392aba92dff47317243a7966f9aa1f725357c08b48b9b8072a1d753d6514ed46"
      },
      "candidate": {
        "bytes": 12641,
        "sha256": "af0ab88d9f4ce25154b3fda909fc00b9eca0cda8d8784b4b07e4926015a2c330"
      },
      "readable_sha256": "0a7fe69022051e1893ffbd52ade7a2fbb3f342fe20b581bb786d6997b46fb712",
      "recipe_sha256": "3d5f3753f012a044ecb100729ef96a41450ba486419cf1db493d8ed93f3461ff",
      "alpha_counts": {
        "Board": 28,
        "Entry": 3,
        "Exchange": 0,
        "Worker": 7,
        "advance": 0,
        "alpha": 18,
        "bad": 3,
        "base": 0,
        "best": 23,
        "bestmove": 6,
        "beta": 8,
        "bishops": 3,
        "black": 13,
        "bonus": 6,
        "bound": 8,
        "budget": 9,
        "candidates": 0,
        "cell": 3,
        "center": 0,
        "check": 6,
        "colors": 3,
        "complete": 0,
        "continuation": 3,
        "correction": 4,
        "count": 5,
        "created": 8,
        "data": 15,
        "depth": 27,
        "draw": 4,
        "end": 4,
        "error": 6,
        "evaluation": 8,
        "excluded": 0,
        "extension": 0,
        "file": 0,
        "from": 41,
        "gain": 0,
        "half": 8,
        "history": 3,
        "home": 12,
        "inc": 4,
        "key": 11,
        "keys": 9,
        "knights": 3,
        "last": 2,
        "learning": 0,
        "legal": 5,
        "length": 6,
        "line": 16,
        "list": 9,
        "lock": 4,
        "minors": 4,
        "move": 3,
        "moves": 29,
        "name": 3,
        "next": 0,
        "nodes": 5,
        "occupied": 0,
        "old": 5,
        "pawns": 5,
        "pieces": 0,
        "ply": 13,
        "present": 3,
        "prior": 3,
        "prom": 6,
        "promotion": 3,
        "quiet": 3,
        "rank": 0,
        "reduce": 5,
        "repetitions": 3,
        "rook": 2,
        "root": 3,
        "save": 8,
        "score": 36,
        "scores": 10,
        "seen": 3,
        "shift": 3,
        "side": 6,
        "sign": 3,
        "singular": 0,
        "status": 7,
        "sum": 0,
        "tactical": 4,
        "target": 8,
        "threads": 3,
        "threshold": 0,
        "transit": 2,
        "ttdepth": 2,
        "visits": 0
      },
      "resource_counts": {
        "TT_BITS": 3,
        "WORKERS": 7
      },
      "mapping_used": 70,
      "source_edits_count": 567,
      "alpha_saved_bytes": 1654,
      "resource_saved_bytes": 57,
      "total_saved_bytes": 1711,
      "retained_directive_bytes": 432,
      "retained_PLY_count": 12,
      "expected_old_native": {
        "bytes": 26408,
        "sha256": "5429f2d80521f775bac6802ec4940e8e0ff1b344464ed8e9a0629ba6650eb675"
      },
      "expected_old_whole": {
        "bytes": 5899,
        "sha256": "ccf1a0b4c2163b46c445d4ec1add03bcc75ba75d66cd1647ab9dc2ca556687f3"
      }
    }
  }
}
'''.encode("ascii")
if hashlib.sha256(_POLICY_BYTES).hexdigest() != _POLICY_SHA256:
    raise ValueError("embedded fixed alpha policy SHA-256 mismatch")

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
