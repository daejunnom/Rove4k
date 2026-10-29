"""One fixed A31 shipping spelling policy, stored as ordinary source.

The original PLY-preserving A-only policy JSON is embedded byte-for-byte. Only
the exact qualified shipping A and canonical readable A are admitted. The
caller supplies its pinned identifier lexer and readable bytes. No experiment,
historical report, generated source, executable or other engine is consumed.
The generic independent opaque scanner/rewrite is copied unchanged from the
qualified reference. Complete-native/package gates remain the builder's job.
"""
from collections import Counter
import hashlib
import json
import re

POLICY_SHA256='e1d5daf3636851711d08309b772edf7a3546bfffeb402d745d33eaaf80560244'
POLICY_BYTES=r'''{
  "format": 1,
  "policy": "one-fixed-A-private31-preserve-PLY-20261020",
  "source_checkpoint": "418435c75ea68e21b2a0fde3723cf8c4fb42c524",
  "scope": "one approved A-only subset of the original fixed73 aliases, same alias gaps, retaining PLY macro uses; no search/feedback",
  "allowed_shipping_names": [
    "Entry",
    "advance",
    "bad",
    "cell",
    "center",
    "colors",
    "draw",
    "end",
    "file",
    "history",
    "inc",
    "knights",
    "last",
    "lock",
    "move",
    "name",
    "next",
    "old",
    "pawn",
    "present",
    "prior",
    "prom",
    "quiet",
    "rank",
    "rook",
    "root",
    "seen",
    "shift",
    "threads",
    "transit",
    "ttdepth"
  ],
  "mapping": {
    "Entry": "zb",
    "advance": "zd",
    "bad": "ze",
    "cell": "zl",
    "center": "zm",
    "colors": "zo",
    "draw": "zv",
    "end": "zw",
    "file": "zz",
    "history": "zC",
    "inc": "zE",
    "knights": "zH",
    "last": "zI",
    "lock": "zN",
    "move": "zQ",
    "name": "zS",
    "next": "zT",
    "old": "zV",
    "pawn": "zW",
    "present": "zY",
    "prior": "zZ",
    "prom": "z0",
    "quiet": "z2",
    "rank": "z3",
    "rook": "z5",
    "root": "z6",
    "seen": "ya",
    "shift": "yb",
    "threads": "yg",
    "transit": "yh",
    "ttdepth": "yi"
  },
  "resource_literals": {
    "WORKERS": "2",
    "TT_BITS": "18"
  },
  "preserved_resource_macro": "PLY",
  "protected_shipping_names": [
    "B",
    "C",
    "CLOCK_MONOTONIC",
    "E",
    "EOF",
    "FROM",
    "G",
    "H",
    "HISTORY",
    "LLONG_MAX",
    "MATE",
    "MOVE",
    "MOVES",
    "Move",
    "NULL",
    "PLY",
    "PROMO",
    "PTHREAD_COND_INITIALIZER",
    "PTHREAD_MUTEX_INITIALIZER",
    "R",
    "S",
    "TO",
    "U",
    "UINT64_C",
    "V",
    "a",
    "a1",
    "a2",
    "a4",
    "a5",
    "a7",
    "aA",
    "aB",
    "aC",
    "aD",
    "aE",
    "aF",
    "aG",
    "aH",
    "aI",
    "aJ",
    "aK",
    "aL",
    "aM",
    "aN",
    "aO",
    "aP",
    "aQ",
    "aR",
    "aS",
    "aT",
    "aU",
    "aV",
    "aW",
    "aX",
    "aZ",
    "aa",
    "ab",
    "abort",
    "abs",
    "ac",
    "ad",
    "ae",
    "af",
    "ag",
    "ah",
    "ai",
    "aj",
    "ak",
    "al",
    "am",
    "an",
    "ao",
    "ap",
    "aq",
    "ar",
    "as",
    "at",
    "atomic_flag",
    "atomic_flag_clear",
    "atomic_flag_clear_explicit",
    "atomic_flag_test_and_set_explicit",
    "atomic_int",
    "atomic_load_explicit",
    "atomic_store",
    "au",
    "av",
    "aw",
    "ax",
    "ay",
    "az",
    "b",
    "ba",
    "back",
    "bb",
    "bc",
    "bd",
    "be",
    "bf",
    "bg",
    "bh",
    "break",
    "c",
    "calloc",
    "char",
    "clock",
    "clock_gettime",
    "command",
    "const",
    "continue",
    "d",
    "deadline",
    "e",
    "else",
    "epoch",
    "f",
    "fallback",
    "fflush",
    "finished",
    "flockfile",
    "for",
    "free",
    "funlockfile",
    "game_keys",
    "game_length",
    "getchar",
    "goto",
    "h",
    "i",
    "id",
    "if",
    "int",
    "int16_t",
    "int8_t",
    "j",
    "k",
    "l",
    "m",
    "main",
    "material",
    "memcpy",
    "memory_order_acquire",
    "memory_order_relaxed",
    "memory_order_release",
    "mutex",
    "n",
    "o",
    "p",
    "pending",
    "pi",
    "position",
    "printf",
    "pthread_cond_broadcast",
    "pthread_cond_t",
    "pthread_cond_wait",
    "pthread_create",
    "pthread_join",
    "pthread_mutex_lock",
    "pthread_mutex_t",
    "pthread_mutex_unlock",
    "pthread_t",
    "puts",
    "q",
    "quitting",
    "r",
    "ready",
    "return",
    "s",
    "shutdown",
    "size_t",
    "sizeof",
    "sq",
    "static",
    "stdout",
    "steps",
    "stopped",
    "strcmp",
    "strcpy",
    "strlen",
    "strncmp",
    "strstr",
    "strtok_r",
    "struct",
    "t",
    "table",
    "timespec",
    "to",
    "tt",
    "tv_nsec",
    "tv_sec",
    "typedef",
    "uint16_t",
    "uint64_t",
    "unsigned",
    "v",
    "void",
    "w",
    "while",
    "workers",
    "x",
    "z"
  ],
  "readable_inputs": {
    "engines/compact/tiny-entry-a/engine.c": {
      "bytes": 24820,
      "sha256": "71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734"
    }
  },
  "families": {
    "A": {
      "source": {
        "bytes": 10855,
        "sha256": "f69044dc9ad2869bd3583308ef446a67f3afa6b31b36e7daade6a6b8cd9a3e6a"
      },
      "candidate": {
        "bytes": 10606,
        "sha256": "252d87ed58df8c86b2d7898fafcedc0bed1c3bab447846b484e5afbdd5b27ac3"
      },
      "alpha_counts": {
        "Entry": 3,
        "advance": 2,
        "bad": 3,
        "cell": 3,
        "center": 2,
        "colors": 3,
        "draw": 4,
        "end": 4,
        "file": 2,
        "history": 3,
        "inc": 4,
        "knights": 3,
        "last": 2,
        "lock": 4,
        "move": 3,
        "name": 3,
        "next": 5,
        "old": 6,
        "pawn": 2,
        "present": 3,
        "prior": 3,
        "prom": 3,
        "quiet": 3,
        "rank": 4,
        "rook": 2,
        "root": 3,
        "seen": 3,
        "shift": 3,
        "threads": 3,
        "transit": 2,
        "ttdepth": 2
      },
      "resource_counts": {
        "WORKERS": 0,
        "TT_BITS": 0
      },
      "alpha_saved_bytes": 249,
      "resource_saved_bytes": 0,
      "source_saved_bytes": 249,
      "mapping_used": 31,
      "source_edits_count": 95,
      "retained_directive_bytes": 432,
      "opaque_regions_preserved": 53,
      "preserved_PLY_code_uses": 8
    }
  },
  "alias_rule": "exact A-present31 subset of original fixed73 literalmap; same aliases including gaps; never regenerate",
  "protection_rule": "default deny every shipping identifier outside exact31 audited locals/parameters/private members/owned typedef and two resource spellings; PLY/all directives/functions/globals/statics/external APIs preserved",
  "native_identity_policy": "exact complete original SHA including build-ID and nonallocated sections; no exception",
  "numeric_inverse_replacements": 0,
  "provenance": {
    "original_joint_policy_sha256": "4bf1b189e9073aa994c29c07f64bcf05b1b3e749a0a172150cac68c1971d7d92",
    "normal_build_dependency": false
  }
}
'''.encode('ascii')
if hashlib.sha256(POLICY_BYTES).hexdigest()!=POLICY_SHA256:
    raise ValueError('embedded reviewed A31 literal policy changed')

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


def sha(data):return hashlib.sha256(data).hexdigest()


def binding(data,pin,label):
    if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError(label+' exact bytes changed')


def transform_source(data,*,family,lexer,readable):
    fixed=json.loads(POLICY_BYTES)
    if family!='A':raise ValueError('only the reviewed A family is admitted')
    row=fixed['families'][family];binding(data,row['source'],family+' shipping source')
    mapping=fixed['mapping'];resources=fixed['resource_literals']
    if resources!={'WORKERS':'2','TT_BITS':'18'} or fixed['preserved_resource_macro']!='PLY':raise ValueError('fixed resource/PLY boundary changed')
    if sorted(mapping)!=fixed['allowed_shipping_names'] or set(mapping)&set(fixed['protected_shipping_names']):
        raise ValueError('protected or unaudited old spelling admitted')
    if any(len(old)<=2 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*',new) or len(new)!=2 for old,new in mapping.items()):
        raise ValueError('unexpected alias rule')
    aliases=set(mapping.values())
    if len(aliases)!=len(mapping) or len(mapping)!=31:raise ValueError('noninjective or changed A aliases')
    for name,pin in fixed['readable_inputs'].items():
        if name!='engines/compact/tiny-entry-a/engine.c':raise ValueError('unexpected canonical readable input')
        raw=readable;binding(raw,pin,'canonical readable A input')
        reserved=set(_WORD.findall(raw.decode()))|set(_WORD.findall(_logical(raw.decode())[0]))
        if aliases&reserved:raise ValueError('alias occurs in frozen readable source')
    substitutions={**mapping,**resources}
    if 'PLY' in substitutions:raise ValueError('PLY macro must stay unchanged')
    before=sha(data);candidate,counts,opaque=_rewrite(data,substitutions,lexer=lexer)
    alpha_counts={old:counts[old] for old in mapping};resource_counts={old:counts[old] for old in resources}
    if alpha_counts!=row['alpha_counts'] or resource_counts!=row['resource_counts']:
        raise ValueError('literal AF token occurrence counts changed')
    alpha_saved=sum((len(old)-len(new))*counts[old] for old,new in mapping.items())
    resource_saved=sum((len(old)-len(new))*counts[old] for old,new in resources.items())
    directive_bytes=sum(len(raw.encode()) for kind,raw in opaque if kind=='directive')
    used=sum(counts[old]>0 for old in mapping)
    if (alpha_saved!=row['alpha_saved_bytes'] or resource_saved!=row['resource_saved_bytes']
            or len(data)-len(candidate)!=row['source_saved_bytes'] or used!=row['mapping_used']
            or sum(counts.values())!=row['source_edits_count'] or directive_bytes!=row['retained_directive_bytes']
            or len(opaque)!=row['opaque_regions_preserved']):
        raise ValueError('literal A arithmetic or opaque count changed')
    ply_before=sum(token=='PLY' for _,_,token in lexer._identifier_spans(data.decode()))
    ply_after=sum(token=='PLY' for _,_,token in lexer._identifier_spans(candidate.decode()))
    if ply_before!=8 or ply_after!=8 or row['preserved_PLY_code_uses']!=8:raise ValueError('PLY code uses changed')
    binding(candidate,row['candidate'],family+' sole candidate')
    if sha(data)!=before:raise ValueError('source mutated')
    return candidate,{'family':family,'policy_sha256':POLICY_SHA256,'mapping':mapping,'mapping_used':used,
        'alpha_counts':alpha_counts,'resource_literals':resources,'resource_counts':resource_counts,
        'alpha_saved_bytes':alpha_saved,'resource_saved_bytes':resource_saved,'source_saved_bytes':len(data)-len(candidate),
        'source_edits_count':sum(counts.values()),'retained_directive_bytes':directive_bytes,'opaque_regions_preserved':len(opaque),
        'preserved_PLY_code_uses':ply_after,
        'independent_opaque_and_rewrite_checks':True,'source_only_proof':True,'native_or_package_gate_executed':False}
