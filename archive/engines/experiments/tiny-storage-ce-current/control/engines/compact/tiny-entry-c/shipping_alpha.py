"""One exact C composition shipping domain with the unchanged shared89 map.

The new source/count policy is embedded as literal bytes. Callers supply their
raw-hash-pinned ordinary shared reference and lexer plus canonical readable
bytes. Only shared generic binding/logical/rewrite helpers are used. The old
shared transform_source admission is neither called nor changed, including its
unchanged B/E domains. There are no path, side-file, experiment/report or other
engine dependencies in this module's normal execution.

This is exact lexical source reproduction, not a general C AST/name-binding
proof or a native/package/runtime gate. DEV bypass belongs to the caller.
"""

import hashlib
import json


_POLICY_SHA256 = "9ac6fdd907a114d6748268c5777e5ee3fa54a53ce56ae07bd1d7fae37d1202c5"
_POLICY_BYTES = b'''{
  "format": 1,
  "family": "C",
  "scope": "one fixed C three-site composition candidate; original89 map unchanged, new literal source/count domain; no search/variants",
  "original_policy_sha256": "b3f08ba26b38dbce1e4b63d3eb98ab37f438295cfacff6037b1cfacbf7d5e5a0",
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
  "source": {
    "bytes": 13878,
    "sha256": "df44d4246f2ab4145b525a79b9207f4ebe279c450a2cce723bfedbe4b2c5d1a9"
  },
  "candidate": {
    "bytes": 12224,
    "sha256": "20f06b6ed9ada03db6f8719f05ecdf9cb52802ab0a1acc8999627999db899046"
  },
  "alpha_counts": {
    "Board": 26,
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
    "depth": 26,
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
    "list": 5,
    "lock": 4,
    "minors": 4,
    "move": 3,
    "moves": 29,
    "name": 3,
    "next": 0,
    "nodes": 4,
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
    "score": 33,
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
    "WORKERS": 6
  },
  "mapping_used": 73,
  "alpha_saved_bytes": 1603,
  "resource_saved_bytes": 51,
  "source_edits_count": 553,
  "source_saved_bytes": 1654,
  "retained_directive_bytes": 455,
  "opaque_regions_preserved": 54,
  "retained_PLY_code_uses": 12
}
'''
if hashlib.sha256(_POLICY_BYTES).hexdigest() != _POLICY_SHA256:
    raise ValueError("embedded C composition policy SHA-256 mismatch")

_ORIGINAL_POLICY_SHA256 = "b3f08ba26b38dbce1e4b63d3eb98ab37f438295cfacff6037b1cfacbf7d5e5a0"
_READABLE = {
    "bytes": 26692,
    "sha256": "15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b",
}
_EXPECTED_CALLER_PINS = {
    "engines/scripts/fixed_shipping_alpha.py": "92b351d537c1da0f346f072df2ca4b0be713d0e286e039b30efa9f758519c806",
    "engines/scripts/rename_c.py": "9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5",
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source: bytes, *, family: str, lexer, reference, readable: bytes):
    """Return the sole admitted C composition source and source-only metadata.

    Shared module and lexer raw source authentication belongs to the caller.
    Unknown/old/DEV/modified inputs fail closed; no admission is discovered or
    updated from input. Previously qualified shared source domains stay intact.
    """
    if not isinstance(family, str) or family != "C":
        raise ValueError("unknown local C composition family")
    if not isinstance(source, bytes) or not isinstance(readable, bytes):
        raise ValueError("immutable shipping and canonical readable bytes required")
    if _sha(_POLICY_BYTES) != _POLICY_SHA256:
        raise ValueError("embedded C composition policy SHA-256 mismatch")
    old_raw = getattr(reference, "_POLICY_BYTES", None)
    if (not isinstance(old_raw, bytes) or _sha(old_raw) != _ORIGINAL_POLICY_SHA256
            or getattr(reference, "_POLICY_SHA256", None) != _ORIGINAL_POLICY_SHA256):
        raise ValueError("original shared policy identity changed")
    fixed, original = json.loads(_POLICY_BYTES), json.loads(old_raw)
    if (fixed["family"] != "C" or fixed["original_policy_sha256"] != _ORIGINAL_POLICY_SHA256
            or fixed["mapping"] != original["mapping"]):
        raise ValueError("original89 alias map changed")
    mapping, resources = fixed["mapping"], fixed["resource_literals"]
    protected = fixed["symbol_bearing_spellings_retained"]
    if (len(mapping) != 89 or len(set(mapping.values())) != 89
            or resources != {"TT_BITS": "18", "WORKERS": "2"}
            or resources != original["resource_literals"]
            or protected != original["symbol_bearing_spellings_retained"]
            or set(mapping).intersection(protected)):
        raise ValueError("original default-deny resource/symbol boundary changed")
    if any(not callable(getattr(reference, name, None))
           for name in ("_binding", "_logical", "_rewrite")):
        raise ValueError("ordinary shared generic helpers are missing")
    reference._binding(readable, _READABLE, "sole C composition canonical readable")
    own_text = readable.decode("utf-8")
    reserved = (set(reference._WORD.findall(own_text))
                | set(reference._WORD.findall(reference._logical(own_text)[0])))
    if set(mapping.values()).intersection(reserved):
        raise ValueError("fixed alias occurs in candidate readable")
    reference._binding(source, fixed["source"], "new composition shipping before alpha")
    before_sha, readable_sha = _sha(source), _sha(readable)
    candidate, counts, opaque = reference._rewrite(source, {**mapping, **resources}, lexer=lexer)
    if not isinstance(candidate, bytes):
        raise ValueError("shared rewrite returned a non-byte candidate")
    alpha_counts = {name: counts[name] for name in mapping}
    resource_counts = {name: counts[name] for name in resources}
    alpha_saved = sum((len(name) - len(mapping[name])) * count
                      for name, count in alpha_counts.items())
    resource_saved = sum((len(name) - len(resources[name])) * count
                         for name, count in resource_counts.items())
    ply = sum(token == "PLY" for _, _, token in lexer._identifier_spans(source.decode("utf-8")))
    used = sum(value > 0 for value in alpha_counts.values())
    directive_bytes = sum(len(text.encode("utf-8")) for kind, text in opaque if kind == "directive")
    if (alpha_counts != fixed["alpha_counts"] or resource_counts != fixed["resource_counts"]
            or alpha_saved != fixed["alpha_saved_bytes"]
            or resource_saved != fixed["resource_saved_bytes"]
            or len(source) - len(candidate) != fixed["source_saved_bytes"]
            or sum(counts.values()) != fixed["source_edits_count"]
            or used != fixed["mapping_used"] or ply != fixed["retained_PLY_code_uses"]
            or len(opaque) != fixed["opaque_regions_preserved"]
            or directive_bytes != fixed["retained_directive_bytes"]):
        raise ValueError("new literal candidate count/domain mismatch")
    if sum(token == "PLY" for _, _, token in lexer._identifier_spans(candidate.decode("utf-8"))) != ply:
        raise ValueError("PLY code uses changed")
    reference._binding(candidate, fixed["candidate"], "sole C composition alpha result")
    if _sha(source) != before_sha or _sha(readable) != readable_sha:
        raise ValueError("input bytes changed")
    return candidate, {
        "family": family, "policy_sha256": _POLICY_SHA256,
        "original_policy_sha256": _ORIGINAL_POLICY_SHA256,
        "expected_caller_pinned_modules": dict(_EXPECTED_CALLER_PINS),
        "before": dict(fixed["source"]), "after": dict(fixed["candidate"]),
        "readable": dict(_READABLE), "mapping": mapping, "mapping_used": used,
        "resource_literals": resources, "symbol_bearing_spellings_retained": protected,
        "original89_mapping_unchanged": True, "alpha_counts": alpha_counts,
        "resource_counts": resource_counts, "alpha_saved_bytes": alpha_saved,
        "resource_saved_bytes": resource_saved, "source_saved_bytes": len(source) - len(candidate),
        "source_edits_count": sum(counts.values()), "retained_PLY_code_uses": ply,
        "retained_directive_bytes": directive_bytes, "opaque_regions_preserved": len(opaque),
        "independent_rewrite_opaque_checks": True, "input_immutable": True,
        "caller_must_pin_module_source_bytes": True,
        "source_only_proof": True, "preprocessor_native_package_runtime_gate_executed": False,
    }
