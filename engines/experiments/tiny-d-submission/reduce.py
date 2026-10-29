"""Preprocessed-C size candidates behind a complete native-byte identity gate.

Only unused scalar typedef declarations are pruned. No static assertion,
runtime check, function body or atomic operation is removed. A batch lexical
alpha-renaming is admitted only if the complete compiled native is identical.
Assembly, literals and compiler-reserved identifiers remain opaque.
"""
from collections import Counter
import hashlib
import re


def pin(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


SCALAR_TYPEDEF = re.compile(r"typedef\s+(?:[A-Za-z_][A-Za-z_0-9]*\s+)+([A-Za-z_][A-Za-z_0-9]*)\s*;\Z")


def prune_typedefs(files, lexical):
    """Iterate unused scalar aliases; keep every nontrivial declarator."""
    result, rounds = dict(files), []
    while True:
        counts = Counter(token for data in result.values()
                         for _, _, token in lexical._identifier_spans(data.decode()))
        edits = {}
        for name, data in result.items():
            text = data.decode()
            candidates = []
            for begin, _, token in lexical._identifier_spans(text):
                if token != "typedef":
                    continue
                end = text.find(";", begin)
                if end < 0:
                    continue
                fragment = text[begin:end + 1]
                match = SCALAR_TYPEDEF.fullmatch(fragment)
                if (match and not {"struct", "union", "enum"}.intersection(fragment.split())
                        and counts[match.group(1)] == 1):
                    candidates.append((begin, end + 1, fragment, match.group(1)))
            if candidates:
                parts, at = [], 0
                for begin, end, fragment, alias in candidates:
                    if begin < at:
                        raise ValueError("overlapping scalar typedef candidates")
                    parts.append(text[at:begin])
                    at = end
                parts.append(text[at:])
                output = "".join(parts).encode()
                edits[name] = dict(input=pin(data), output=pin(output),
                                   removed=[dict(begin=a, end=b, declaration=s, alias=n)
                                            for a, b, s, n in candidates])
                result[name] = output
        if not edits:
            return result, rounds
        rounds.append(edits)


def reduce_sources(files, compile_digest, lexical, *, reserve=()):
    """Return actual accepted input plus independent gate observations."""
    original = dict(files)
    baseline = compile_digest(dict(original), "baseline")
    report = dict(method="unused-scalar-typedef-and-batch-alpha-native-identity-v1",
                  baseline_native_sha256=baseline,
                  before={n: pin(d) for n, d in original.items()}, stages=[])
    accepted = dict(original)
    pruned, rounds = prune_typedefs(original, lexical)
    if rounds:
        digest = compile_digest(pruned, "typedefs")
        status = "accepted" if digest == baseline else "rejected-native-differs"
        report["stages"].append(dict(kind="unused-scalar-typedefs", status=status,
                                     native_sha256=digest, rounds=rounds))
        if status == "accepted":
            accepted = pruned
    counts = Counter()
    protected = set(reserve) | {"main", "spawn", "memcpy", "memset", "memcmp", "abort"}
    used = set(lexical._KEYWORDS) | protected
    for data in accepted.values():
        text = data.decode()
        counts.update(token for _, _, token in lexical._identifier_spans(text))
        used.update(lexical._ANY_WORD.findall(text))
    candidates = sorted((n for n in counts if len(n) > 1 and n not in lexical._KEYWORDS
                         and n not in protected
                         and lexical._ASCII_IDENTIFIER.fullmatch(n)),
                        key=lambda n: (-(len(n) - 1) * counts[n], n))
    names, renames = lexical._short_names(), {}
    for old in candidates:
        new = next(name for name in names if name not in used)
        used.add(new)
        if len(new) < len(old):
            renames[old] = new
    batch = {}
    for name, data in accepted.items():
        text, parts, at = data.decode(), [], 0
        for begin, end, token in lexical._identifier_spans(text):
            if token in renames:
                parts.extend((text[at:begin], renames[token]))
                at = end
        parts.append(text[at:])
        batch[name] = "".join(parts).encode()
    # Compiler, timeout, ownership and I/O failures abort the producer. They
    # are not evidence that a source candidate merely differs in native bytes.
    digest = compile_digest(batch, "batch-alpha")
    status = "accepted" if digest == baseline else "rejected-native-differs"
    report["stages"].append(dict(kind="batch-alpha", status=status,
                                 native_sha256=digest, renames=renames,
                                 protected_original_identifiers=sorted(protected),
                                 protected_assembly_and_literals=True))
    if status == "accepted":
        accepted = batch
    report["after"] = {n: pin(d) for n, d in accepted.items()}
    report["final_native_sha256"] = baseline
    return accepted, report
