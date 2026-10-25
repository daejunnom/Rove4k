"""One fixed F shipping spelling policy, stored as ordinary source.

The original AF policy JSON is embedded byte-for-byte. Only the qualified F
shipping source is admitted here. The caller supplies the pinned identifier
lexer and the canonical readable F bytes. There are no live AF, report, old
executable, compiler, header, or codec dependencies in this pure lexical stage.
The independent opaque scanner and rewrite functions are copied unchanged from
the qualified AF reference. Actual complete-native and package gates remain the
builder's responsibility; lexical checks alone do not prove C semantics.
"""
from collections import Counter
import hashlib
import json
import re

POLICY_SHA256='4bf1b189e9073aa994c29c07f64bcf05b1b3e749a0a172150cac68c1971d7d92'
POLICY_BYTES=r'''{
  "format": 1,
  "policy": "one-fixed-AF-private73-resource3-20261020",
  "source_checkpoint": "b2ba5ae70a0ee7cfb009393b6db408b41780dfcb",
  "scope": "one automatic fixed ASCII alias assignment from independently audited old shipping roles; no compile-guided search",
  "allowed_shipping_names": [
    "Board",
    "Entry",
    "Worker",
    "advance",
    "bad",
    "best",
    "bestmove",
    "beta",
    "bonus",
    "bound",
    "budget",
    "cell",
    "center",
    "check",
    "colors",
    "continuation",
    "correction",
    "count",
    "created",
    "data",
    "depth",
    "draw",
    "end",
    "error",
    "evaluation",
    "file",
    "from",
    "half",
    "history",
    "home",
    "inc",
    "key",
    "keys",
    "knights",
    "last",
    "legal",
    "length",
    "line",
    "list",
    "lock",
    "lower",
    "minors",
    "move",
    "moves",
    "name",
    "next",
    "nodes",
    "old",
    "pawn",
    "ply",
    "present",
    "prior",
    "prom",
    "promotion",
    "quiet",
    "rank",
    "repetitions",
    "rook",
    "root",
    "save",
    "score",
    "scores",
    "seen",
    "shift",
    "side",
    "status",
    "tactical",
    "target",
    "threads",
    "transit",
    "ttdepth",
    "upper",
    "witness"
  ],
  "mapping": {
    "Board": "za",
    "Entry": "zb",
    "Worker": "zc",
    "advance": "zd",
    "bad": "ze",
    "best": "zf",
    "bestmove": "zg",
    "beta": "zh",
    "bonus": "zi",
    "bound": "zj",
    "budget": "zk",
    "cell": "zl",
    "center": "zm",
    "check": "zn",
    "colors": "zo",
    "continuation": "zp",
    "correction": "zq",
    "count": "zr",
    "created": "zs",
    "data": "zt",
    "depth": "zu",
    "draw": "zv",
    "end": "zw",
    "error": "zx",
    "evaluation": "zy",
    "file": "zz",
    "from": "zA",
    "half": "zB",
    "history": "zC",
    "home": "zD",
    "inc": "zE",
    "key": "zF",
    "keys": "zG",
    "knights": "zH",
    "last": "zI",
    "legal": "zJ",
    "length": "zK",
    "line": "zL",
    "list": "zM",
    "lock": "zN",
    "lower": "zO",
    "minors": "zP",
    "move": "zQ",
    "moves": "zR",
    "name": "zS",
    "next": "zT",
    "nodes": "zU",
    "old": "zV",
    "pawn": "zW",
    "ply": "zX",
    "present": "zY",
    "prior": "zZ",
    "prom": "z0",
    "promotion": "z1",
    "quiet": "z2",
    "rank": "z3",
    "repetitions": "z4",
    "rook": "z5",
    "root": "z6",
    "save": "z7",
    "score": "z8",
    "scores": "z9",
    "seen": "ya",
    "shift": "yb",
    "side": "yc",
    "status": "yd",
    "tactical": "ye",
    "target": "yf",
    "threads": "yg",
    "transit": "yh",
    "ttdepth": "yi",
    "upper": "yj",
    "witness": "yk"
  },
  "resource_literals": {
    "WORKERS": "2",
    "TT_BITS": "18",
    "PLY": "128"
  },
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
    },
    "engines/compact/tiny-entry-f/engine.c": {
      "bytes": 26100,
      "sha256": "dc065b98d99a147f862bd2d4cb0a1349ff79a2da7c1be873d906dff71cc9cd89"
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
        "sha256": "33c988b2428ca2fbd6c97668ccb3cd9d3b6ff35617cbd3be53a91137f0f5786f"
      },
      "alpha_counts": {
        "Board": 0,
        "Entry": 3,
        "Worker": 0,
        "advance": 2,
        "bad": 3,
        "best": 0,
        "bestmove": 0,
        "beta": 0,
        "bonus": 0,
        "bound": 0,
        "budget": 0,
        "cell": 3,
        "center": 2,
        "check": 0,
        "colors": 3,
        "continuation": 0,
        "correction": 0,
        "count": 0,
        "created": 0,
        "data": 0,
        "depth": 0,
        "draw": 4,
        "end": 4,
        "error": 0,
        "evaluation": 0,
        "file": 2,
        "from": 0,
        "half": 0,
        "history": 3,
        "home": 0,
        "inc": 4,
        "key": 0,
        "keys": 0,
        "knights": 3,
        "last": 2,
        "legal": 0,
        "length": 0,
        "line": 0,
        "list": 0,
        "lock": 4,
        "lower": 0,
        "minors": 0,
        "move": 3,
        "moves": 0,
        "name": 3,
        "next": 5,
        "nodes": 0,
        "old": 6,
        "pawn": 2,
        "ply": 0,
        "present": 3,
        "prior": 3,
        "prom": 3,
        "promotion": 0,
        "quiet": 3,
        "rank": 4,
        "repetitions": 0,
        "rook": 2,
        "root": 3,
        "save": 0,
        "score": 0,
        "scores": 0,
        "seen": 3,
        "shift": 3,
        "side": 0,
        "status": 0,
        "tactical": 0,
        "target": 0,
        "threads": 3,
        "transit": 2,
        "ttdepth": 2,
        "upper": 0,
        "witness": 0
      },
      "resource_counts": {
        "WORKERS": 0,
        "TT_BITS": 0,
        "PLY": 8
      },
      "mapping_used": 31,
      "alpha_saved_bytes": 249,
      "resource_saved_bytes": 0,
      "source_saved_bytes": 249,
      "source_edits_count": 103,
      "retained_directive_bytes": 432,
      "opaque_regions_preserved": 53
    },
    "F": {
      "source": {
        "bytes": 12722,
        "sha256": "69885c0fd3096c8782a96c4f11b8d3a3b322858fe513b7420330d8e07e16baf8"
      },
      "candidate": {
        "bytes": 11216,
        "sha256": "5c4008afe4a0708558eb829c815a7a095c436df92a3a7685e8553e24efedb991"
      },
      "alpha_counts": {
        "Board": 26,
        "Entry": 3,
        "Worker": 8,
        "advance": 2,
        "bad": 3,
        "best": 16,
        "bestmove": 3,
        "beta": 10,
        "bonus": 6,
        "bound": 7,
        "budget": 9,
        "cell": 6,
        "center": 2,
        "check": 4,
        "colors": 3,
        "continuation": 3,
        "correction": 5,
        "count": 5,
        "created": 8,
        "data": 16,
        "depth": 21,
        "draw": 4,
        "end": 4,
        "error": 6,
        "evaluation": 2,
        "file": 2,
        "from": 40,
        "half": 8,
        "history": 3,
        "home": 12,
        "inc": 4,
        "key": 11,
        "keys": 9,
        "knights": 3,
        "last": 2,
        "legal": 3,
        "length": 6,
        "line": 16,
        "list": 9,
        "lock": 4,
        "lower": 6,
        "minors": 4,
        "move": 7,
        "moves": 28,
        "name": 3,
        "next": 2,
        "nodes": 5,
        "old": 4,
        "pawn": 2,
        "ply": 10,
        "present": 3,
        "prior": 5,
        "prom": 3,
        "promotion": 3,
        "quiet": 3,
        "rank": 4,
        "repetitions": 3,
        "rook": 2,
        "root": 3,
        "save": 8,
        "score": 39,
        "scores": 7,
        "seen": 3,
        "shift": 3,
        "side": 6,
        "status": 7,
        "tactical": 3,
        "target": 8,
        "threads": 3,
        "transit": 2,
        "ttdepth": 2,
        "upper": 5,
        "witness": 7
      },
      "resource_counts": {
        "WORKERS": 0,
        "TT_BITS": 0,
        "PLY": 0
      },
      "mapping_used": 73,
      "alpha_saved_bytes": 1506,
      "resource_saved_bytes": 0,
      "source_saved_bytes": 1506,
      "source_edits_count": 517,
      "retained_directive_bytes": 416,
      "opaque_regions_preserved": 52
    }
  },
  "alias_rule": "old spelling ASCII-sort, len>2; first fresh z*/y*/x* two-character alias not in any readable/shipping raw or phase-two token, keyword, main or key; no native/size feedback",
  "protection_rule": "default deny every shipping identifier outside the exact73 role-audited automatic/parameter/private member/owned typedef names and three fixedresources; Move/directives and all functions/globals/statics/API remain protected",
  "native_identity_policy": "exact complete old SHA including build-ID; no section exception",
  "numeric_inverse_replacements": 0
}
'''.encode('ascii')
if hashlib.sha256(POLICY_BYTES).hexdigest()!=POLICY_SHA256:
    raise ValueError('embedded original AF literal policy changed')

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



def transform_source(data,*,family,lexer,readable):
    """Admit F only, with the original mapping/count/freshness boundaries."""
    fixed=json.loads(POLICY_BYTES)
    if family!='F':raise ValueError('only the qualified maintained F input is admitted')
    row=fixed['families']['F'];_binding(data,row['source'],'F shipping input')
    mapping=fixed['mapping'];resources=fixed['resource_literals']
    if resources!={'WORKERS':'2','TT_BITS':'18','PLY':'128'}:
        raise ValueError('fixed resources changed')
    if len(mapping)!=73 or sorted(mapping)!=fixed['allowed_shipping_names'] or set(mapping)&set(fixed['protected_shipping_names']):
        raise ValueError('protected or unaudited old spelling admitted')
    if any(len(old)<=2 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*',new) or len(new)!=2 for old,new in mapping.items()):
        raise ValueError('unexpected alias rule')
    aliases=set(mapping.values())
    if len(aliases)!=len(mapping):raise ValueError('noninjective F aliases')
    _binding(readable,fixed['readable_inputs']['engines/compact/tiny-entry-f/engine.c'],'F canonical readable input')
    reserved=set(_WORD.findall(readable.decode()))|set(_WORD.findall(_logical(readable.decode())[0]))
    if aliases&reserved:raise ValueError('alias occurs in the canonical readable F source')
    before=_sha(data)
    candidate,counts,opaque=_rewrite(data,{**mapping,**resources},lexer=lexer)
    alpha_counts={old:counts[old] for old in mapping}
    resource_counts={old:counts[old] for old in resources}
    if alpha_counts!=row['alpha_counts'] or resource_counts!=row['resource_counts']:
        raise ValueError('literal F token occurrence counts changed')
    alpha_saved=sum((len(old)-len(new))*counts[old] for old,new in mapping.items())
    resource_saved=sum((len(old)-len(new))*counts[old] for old,new in resources.items())
    directive_bytes=sum(len(raw.encode()) for kind,raw in opaque if kind=='directive')
    used=sum(counts[old]>0 for old in mapping)
    if (alpha_saved!=row['alpha_saved_bytes'] or resource_saved!=row['resource_saved_bytes']
            or len(data)-len(candidate)!=row['source_saved_bytes'] or used!=row['mapping_used']
            or sum(counts.values())!=row['source_edits_count'] or directive_bytes!=row['retained_directive_bytes']
            or len(opaque)!=row['opaque_regions_preserved']):
        raise ValueError('literal F arithmetic or opaque count changed')
    _binding(candidate,row['candidate'],'F sole candidate')
    if _sha(data)!=before:raise ValueError('source mutated')
    return candidate,{'family':'F','original_AF_policy_sha256':POLICY_SHA256,'mapping':mapping,'mapping_used':used,
        'alpha_counts':alpha_counts,'resource_literals':resources,'resource_counts':resource_counts,
        'alpha_saved_bytes':alpha_saved,'resource_saved_bytes':resource_saved,'source_saved_bytes':len(data)-len(candidate),
        'source_edits_count':sum(counts.values()),'retained_directive_bytes':directive_bytes,'opaque_regions_preserved':len(opaque),
        'canonical_F_freshness_checked':True,'independent_opaque_and_rewrite_checks':True,
        'source_only_proof':True,'native_or_package_gate_executed':False}
