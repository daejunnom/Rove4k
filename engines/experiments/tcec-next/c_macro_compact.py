"""C-only pinned macro and source compaction; no runtime authority.

The immintrin header is moved before the three compact macro definitions;
their names are then replaced in declarations and uses. Comments, quoted
literals and preprocessing numbers are preserved, and the complete
predecessor must be reconstructed before any result is accepted.
"""
from collections import Counter
from hashlib import sha256
import json
import re

SELF = "engines/experiments/tcec-next/c_macro_compact.py"
SCHEMA = "rove4k.c-macro-compact-experiment.v1"
DECLARATION = {"path": SELF, "variant": "unused-macro-names"}
_BODY_SHA256 = "e0fb0a62a5ee072982697574d16ed10e70960b4f4c6bdf7718a5aca2d735f888"
_PREFIX = {
    "test-p4": b"#define RVW 4\n#define RVN ((size_t)1<<22)\n",
    "tcec-provisional": b"#define RVW 256\n#define RVN ((size_t)1<<33)\n",
}
_NAMES = {b"PROMO": b"AO", b"FROM": b"TQ", b"MOVE": b"YO"}
_COUNTS = {b"PROMO": 8, b"FROM": 6, b"MOVE": 3}
_EARLY = b"#include <time.h>\n"
_HEADER = b"#include<immintrin.h>\n"
_LATE = _HEADER + b"static int U("
_REWRITES = (
    (b"strtok(NULL,", b"strtok(0,"),
    (b"d==128-1", b"d==127"),
    (b"C<=128-2", b"C<=126"),
    (b"static void O(X*a,int d){*a+=(d-*a*d/16384);}static int s(int p){return p+6;}static int h(",
     b"static void O(X*a,int d){*a+=(d-*a*d/16384);}static int h("),
    (b"R=s(p->b[o])", b"R=p->b[o]+6"),
    (b"R=s(q.b[P])", b"R=q.b[P]+6"),
    (b"for(int f=0;f<8;f++){b(&t,f,qa[f]);b(&t,16+f,1);b(&t,96+f,-1);b(&t,112+f,-qa[f]);}",
     b"for(int f=0;f<8;f++)b(&t,f,qa[f]),b(&t,16+f,1),b(&t,96+f,-1),b(&t,112+f,-qa[f]);"),
    (b"if(U)e->aT=a,e->U=U;else U=e->aT==a?e->U:0;",
     b"U=U?(e->aT=a,e->U=U):e->aT==a?e->U:0;"),
)
_IDENT = re.compile(rb"[A-Za-z_][A-Za-z_0-9]*")
_NUMBER = re.compile(rb"(?:[0-9]|\.[0-9])(?:[eEpP][+-]|[A-Za-z_0-9.])*")
_LITERAL = re.compile(rb'(?:u8|[LuU])?["\']')
_TRIGRAPH = re.compile(rb"\?\?[=/'()!<>-]")


def _parts(source):
    """Split enough C preprocessing tokens to preserve non-identifiers."""
    if type(source) is not bytes or b"\r" in source or b"\\\n" in source or _TRIGRAPH.search(source):
        raise ValueError("canonical unspliced C source required")
    result, i = [], 0
    while i < len(source):
        if source.startswith(b"//", i):
            j = source.find(b"\n", i + 2)
            j = len(source) if j < 0 else j
            result.append((False, source[i:j])); i = j; continue
        if source.startswith(b"/*", i):
            j = source.find(b"*/", i + 2)
            if j < 0:
                raise ValueError("unterminated C comment")
            j += 2
            result.append((False, source[i:j])); i = j; continue
        literal = _LITERAL.match(source, i)
        if literal:
            quote = source[i + len(literal.group()) - 1]
            j = i + len(literal.group())
            while j < len(source) and source[j] != quote:
                if source[j] == 92:
                    j += 2
                elif source[j] == 10:
                    raise ValueError("unterminated C literal")
                else:
                    j += 1
            if j >= len(source):
                raise ValueError("unterminated C literal")
            j += 1
            result.append((False, source[i:j])); i = j; continue
        match = _NUMBER.match(source, i)
        if match:
            result.append((False, match.group())); i = match.end(); continue
        match = _IDENT.match(source, i)
        if match:
            result.append((True, match.group())); i = match.end(); continue
        result.append((False, source[i:i+1])); i += 1
    return result


def _replace(source, mapping, counts):
    parts = _parts(source)
    present = Counter(value for identifier, value in parts if identifier)
    if any(present[before] != number for before, number in counts.items()):
        raise ValueError("C macro identifier count differs")
    if any(present[after] for after in mapping.values()):
        raise ValueError("C macro target identifier already exists")
    return b"".join(mapping.get(value, value) if identifier else value for identifier, value in parts)


def _move_header(source):
    if source.count(_EARLY) != 1 or source.count(_HEADER) != 1 or source.count(_LATE) != 1:
        raise ValueError("C SIMD header relocation anchors differ")
    return source.replace(_LATE, b"static int U(", 1).replace(_EARLY, _EARLY + _HEADER, 1)


def _restore_header(source):
    if (source.count(_EARLY + _HEADER) != 1 or source.count(_HEADER) != 1 or
            source.count(b"static int U(") != 1):
        raise ValueError("C SIMD header inverse anchors differ")
    return source.replace(_EARLY + _HEADER, _EARLY, 1).replace(b"static int U(", _LATE, 1)


def _rewrite(source, *, reverse=False):
    pairs = reversed(_REWRITES) if reverse else _REWRITES
    for original, compact in pairs:
        before, after = (compact, original) if reverse else (original, compact)
        if source.count(before) != 1 or source.count(after) != 0:
            raise ValueError("C compact rewrite anchors differ")
        source = source.replace(before, after, 1)
    return source


def transform_source(source, *, family, profile_id):
    if family != "C" or type(profile_id) is not str or profile_id not in _PREFIX or type(source) is not bytes:
        raise ValueError("only the pinned C P4 and W256 source forms are supported")
    prefix = _PREFIX[profile_id]
    if not source.startswith(prefix) or sha256(source[len(prefix):]).hexdigest() != _BODY_SHA256:
        raise ValueError("C macro source differs from its pinned body")
    result = _rewrite(_replace(_move_header(source), _NAMES, _COUNTS))
    inverse = {value: key for key, value in _NAMES.items()}
    if _restore_header(_replace(_rewrite(result, reverse=True), inverse, {_NAMES[key]: count for key, count in _COUNTS.items()})) != source:
        raise ValueError("C macro complete inverse differs")
    return result, {"schema": SCHEMA, "variant": DECLARATION["variant"],
                    "family": family, "profile_id": profile_id,
                    "input": {"bytes": len(source), "sha256": sha256(source).hexdigest()},
                    "output": {"bytes": len(result), "sha256": sha256(result).hexdigest()},
                    "inverse_exact": True, "header_before_compact_macros": True, "native_identical": False,
                    "runtime_qualified": False, "submission_qualified": False}


def restore_source(candidate, proof):
    if type(candidate) is not bytes or type(proof) is not dict:
        raise ValueError("C macro candidate and proof required")
    inverse = {value: key for key, value in _NAMES.items()}
    source = _restore_header(_replace(_rewrite(candidate, reverse=True), inverse, {_NAMES[key]: count for key, count in _COUNTS.items()}))
    regenerated, expected = transform_source(source, family=proof.get("family"), profile_id=proof.get("profile_id"))
    try:
        proof_matches = (json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False)
                         == json.dumps(proof, sort_keys=True, separators=(",", ":"), allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ValueError("C macro source proof is not canonical JSON") from error
    if regenerated != candidate or not proof_matches:
        raise ValueError("C macro source proof differs")
    return source
