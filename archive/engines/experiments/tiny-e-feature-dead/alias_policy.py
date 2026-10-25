"""One fixed alpha policy with an explicit new E source admission.

The caller supplies its raw-hash-pinned ordinary policy and lexer modules.
Only the policy module's generic lexical rewrite is reused; its original exact
transform_source admission is neither called nor changed. analyze() proposes
data for one deliberate recipe seed before compilation. Reproduction calls
apply() with that literal data; it never updates an admission automatically.
No source path, side file, preprocessor, compiler, codec, or engine is used.

The shared whitelist originated in a role audit. These lexical checks do not
establish a new C AST/name-binding proof: the candidate producer must preserve
function/global/static/extern declaration roles and review any new consumers.
Actual header expansion and native/cost qualification belong to the caller.
"""

from collections import Counter
import hashlib
import json


POLICY_SHA256 = "b3f08ba26b38dbce1e4b63d3eb98ab37f438295cfacff6037b1cfacbf7d5e5a0"
EXPECTED_MODULE_PINS = {
    "engines/scripts/fixed_shipping_alpha.py": "92b351d537c1da0f346f072df2ca4b0be713d0e286e039b30efa9f758519c806",
    "engines/scripts/rename_c.py": "9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5",
}
_METHOD = "E_fixed89_resource2_literal_admission_v1"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as error:
        raise ValueError("admission must be ordinary finite JSON data") from error


def _context(policy_module):
    raw = getattr(policy_module, "_POLICY_BYTES", None)
    if not isinstance(raw, bytes) or _sha(raw) != POLICY_SHA256:
        raise ValueError("embedded fixed policy bytes differ")
    if getattr(policy_module, "_POLICY_SHA256", None) != POLICY_SHA256:
        raise ValueError("embedded fixed policy identity differs")
    policy = json.loads(raw)
    mapping, resources = policy["mapping"], policy["resource_literals"]
    if len(mapping) != 89 or len(set(mapping.values())) != 89:
        raise ValueError("fixed89 mapping shape differs")
    if resources != {"WORKERS": "2", "TT_BITS": "18"}:
        raise ValueError("fixed resource literals differ")
    protected = policy["symbol_bearing_spellings_retained"]
    if set(mapping) & (set(resources) | set(protected)):
        raise ValueError("fixed policy captures a retained symbol")
    if any(not callable(getattr(policy_module, name, None))
           for name in ("_rewrite", "_opaque_parts")):
        raise ValueError("ordinary generic lexical helper is missing")
    return policy, mapping, resources, protected


def _inventory(data):
    return {"bytes": len(data), "sha256": _sha(data)}


def _counts(source, lexer):
    return Counter(token for _, _, token in lexer._identifier_spans(source))


def _opaque_inventory(parts):
    kinds = {name: {"regions": 0, "bytes": 0}
             for name in ("directive", "literal", "comment")}
    for kind, text in parts:
        if kind not in kinds:
            raise ValueError("unknown opaque region kind")
        kinds[kind]["regions"] += 1
        kinds[kind]["bytes"] += len(text.encode("utf-8"))
    return {"sha256": _sha(_canonical(parts)), "regions": len(parts), "kinds": kinds}


def _next_code_char(text, end):
    tail = text[end:].replace("\\\r\n", "").replace("\\\n", "")
    while True:
        tail = tail.lstrip()
        if tail.startswith("/*"):
            close = tail.find("*/", 2)
            if close < 0:
                raise ValueError("unterminated consumer comment")
            tail = tail[close + 2:]
        elif tail.startswith("//"):
            close = tail.find("\n")
            tail = "" if close < 0 else tail[close + 1:]
        else:
            return tail[:1]


def _propose(source, lexer, policy_module):
    if not isinstance(source, bytes):
        raise ValueError("source must be immutable bytes")
    policy, mapping, resources, protected = _context(policy_module)
    text = source.decode("utf-8")
    # A shared whitelist must not silently acquire a new function/macro role.
    # This is a conservative consumer guard, not general C declaration parsing.
    for _, end, token in lexer._identifier_spans(text):
        if token in mapping and _next_code_char(text, end) == "(":
            raise ValueError("mapped spelling has a function-like consumer: " + token)
    before_counts = _counts(text, lexer)
    substitutions = dict(mapping)
    substitutions.update(resources)
    opaque_before = policy_module._opaque_parts(text)
    candidate, helper_counts, helper_opaque = policy_module._rewrite(
        source, substitutions, lexer=lexer)
    if not isinstance(candidate, bytes):
        raise ValueError("ordinary helper returned a non-byte candidate")
    after_text = candidate.decode("utf-8")
    opaque_after = policy_module._opaque_parts(after_text)
    if opaque_before != opaque_after or helper_opaque != opaque_before:
        raise ValueError("directive/literal/comment bytes changed")
    expected_counts = Counter({old: before_counts[old] for old in substitutions
                               if before_counts[old]})
    if helper_counts != expected_counts:
        raise ValueError("ordinary helper occurrence counts differ")
    after_counts = _counts(after_text, lexer)
    expected_after = Counter(before_counts)
    for old, new in mapping.items():
        count = expected_after.pop(old, 0)
        if count:
            expected_after[new] += count
    for old in resources:
        expected_after.pop(old, None)
    if after_counts != expected_after:
        raise ValueError("unexpected code identifier change")
    retained = {name: before_counts[name] for name in protected}
    if any(after_counts[name] != count for name, count in retained.items()):
        raise ValueError("known symbol-bearing spelling changed")
    alpha_counts = {old: before_counts[old] for old in mapping}
    resource_counts = {old: before_counts[old] for old in resources}
    unused = [old for old in mapping if not before_counts[old]]
    unused_aliases = [mapping[old] for old in unused]
    if any(after_counts[name] for name in unused_aliases):
        raise ValueError("unused fixed alias was captured")
    alpha_saved = sum((len(old) - len(new)) * before_counts[old]
                      for old, new in mapping.items())
    resource_saved = sum((len(old) - len(new)) * before_counts[old]
                         for old, new in resources.items())
    if len(source) - len(candidate) != alpha_saved + resource_saved:
        raise ValueError("fixed substitution byte arithmetic differs")
    unmapped = {name: count for name, count in before_counts.items()
                if name not in substitutions}
    proposal = {
        "format": 1, "family": "E", "method": _METHOD,
        "policy_sha256": POLICY_SHA256,
        "expected_caller_pinned_modules": dict(EXPECTED_MODULE_PINS),
        "mapping_sha256": _sha(_canonical(mapping)),
        "resource_literals": resources,
        "before": _inventory(source), "after": _inventory(candidate),
        "alpha_counts": alpha_counts, "resource_counts": resource_counts,
        "mapping_used": len(mapping) - len(unused),
        "unused_mappings": unused, "unused_aliases": unused_aliases,
        "source_edits_count": sum(alpha_counts.values()) + sum(resource_counts.values()),
        "alpha_saved_bytes": alpha_saved, "resource_saved_bytes": resource_saved,
        "source_saved_bytes": len(source) - len(candidate),
        "opaque_preserved": _opaque_inventory(opaque_before),
        "retained_symbol_counts": retained,
        "unmapped_code_identifier_counts_sha256": _sha(_canonical(unmapped)),
        "unmapped_code_identifiers_preserved": True,
        "single_pass_and_repeated_replace_agree": True,
        "input_immutable": True,
        "scope": "fixed lexical source admission only; new C declaration roles, headers, native identity and cost are not qualified",
    }
    if _inventory(source) != proposal["before"]:
        raise ValueError("input bytes changed")
    return candidate, proposal


def analyze(source, lexer, policy_module):
    """Propose the sole fixed-policy candidate and one literal source admission.

    The caller may deliberately save this proposal once in its ordinary recipe
    before the first candidate compile. A reproducible builder must only call
    apply with that saved literal; this function is not a native approval gate.
    Expected raw module pins are caller-owned requirements, not a claim that
    Python module objects have been authenticated by this pure function.
    """
    return _propose(source, lexer, policy_module)


def apply(source, *, admission, lexer, policy_module):
    """Apply a saved exact admission; fail closed rather than update its pins."""
    if type(admission) is not dict or not isinstance(source, bytes):
        raise ValueError("literal admission dictionary and immutable source bytes required")
    _context(policy_module)
    if (admission.get("format") != 1 or admission.get("family") != "E"
            or admission.get("method") != _METHOD
            or admission.get("policy_sha256") != POLICY_SHA256):
        raise ValueError("unknown fixed E admission")
    before = admission.get("before")
    if type(before) is not dict or set(before) != {"bytes", "sha256"}:
        raise ValueError("literal input identity is missing")
    if _canonical(before) != _canonical(_inventory(source)):
        raise ValueError("literal source input bytes/SHA-256 mismatch")
    literal = _canonical(admission)
    candidate, reproduced = _propose(source, lexer, policy_module)
    if literal != _canonical(reproduced):
        raise ValueError("literal admission/counts/candidate/opaque identity mismatch")
    metadata = dict(reproduced)
    metadata.update(literal_admission_sha256=_sha(literal),
                    admission_reproduced_exactly=True,
                    caller_must_pin_module_source_bytes=True,
                    preprocessor_compiler_native_or_engine_gates_executed=False)
    return candidate, metadata
