"""One conservative AST-bound private static-function spelling proposal.

Only declaration and direct-call reference byte offsets supplied by the real
Clang AST are edited. Lexical tokens are used to reject unaccounted consumers,
never to perform a name-wide substitution. Native equivalence is not asserted.
"""

from collections import Counter
import hashlib
import json
import re
import string


_WORD = re.compile(r"[A-Za-z_$][A-Za-z_0-9$]*")
_SELF = {"__func__", "__FUNCTION__", "__PRETTY_FUNCTION__"}
_INSPECTION = {"dlsym", "dladdr", "backtrace", "backtrace_symbols", "asm", "__asm", "__asm__"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _main(cursor, filename):
    return cursor.location.file is not None and cursor.location.file.name == filename


def _usr(cursor):
    return cursor.canonical.get_usr() if cursor is not None else ""


def parse(cindex, source, filename, arguments):
    unit = cindex.Index.create().parse(filename, args=arguments,
        unsaved_files=[(filename, source.decode("utf-8"))],
        options=cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
    diagnostics = [{"severity": item.severity, "text": str(item)} for item in unit.diagnostics]
    if any(item["severity"] >= cindex.Diagnostic.Error for item in diagnostics):
        raise ValueError("real-header AST diagnostics: " + json.dumps(diagnostics))
    nodes = []
    def visit(cursor, parents):
        children = list(cursor.get_children())
        nodes.append((cursor, parents))
        for index, child in enumerate(children):
            visit(child, parents + [(cursor, index)])
    visit(unit.cursor, [])
    return unit, nodes, diagnostics


def _signature(nodes, filename, renamed):
    """Compare main-source AST structure and referenced declaration identities.

    Main-file canonical declarations receive stable preorder ordinals so their
    USRs may change spelling while reference binding must stay the same.
    """
    declarations = {}
    for cursor, _ in nodes:
        if _main(cursor, filename) and (cursor.kind.is_declaration()
                                       or cursor.kind.name == "MACRO_DEFINITION"):
            key = _usr(cursor)
            if key and key not in declarations:
                declarations[key] = len(declarations)
    result = []
    for cursor, _ in nodes:
        if not _main(cursor, filename):
            continue
        target = cursor.referenced
        target_key = _usr(target)
        binding = ("main", declarations[target_key]) if target_key in declarations else ("external", target_key)
        spelling = cursor.spelling
        if cursor.kind.name == "FUNCTION_DECL" or target is not None and target.kind.name == "FUNCTION_DECL":
            spelling = renamed.get(spelling, spelling)
        # Clang's storage API is defined for function/variable declarations;
        # querying macro or expression cursors can return unrelated values.
        storage = (cursor.storage_class.name if cursor.kind.name in
                   {"FUNCTION_DECL", "VAR_DECL", "PARM_DECL"} else None)
        result.append((cursor.kind.name, spelling, cursor.type.spelling,
                       storage, binding, len(list(cursor.get_children()))))
    return result


def _direct_call(cursor, parents, target_key):
    for ancestor, branch in reversed(parents):
        kind = ancestor.kind.name
        if kind == "CALL_EXPR":
            return branch == 0 and _usr(ancestor.referenced) == target_key
        if kind != "UNEXPOSED_EXPR":
            return False
    return False


def _aliases():
    alphabet = string.ascii_lowercase + string.ascii_uppercase
    yield from alphabet
    for first in alphabet:
        for second in alphabet + string.digits:
            yield first + second


def propose(source, *, cindex, arguments, lexer, opaque, filename="private.c"):
    if not isinstance(source, bytes):
        raise ValueError("immutable source bytes required")
    if not source.isascii():
        raise ValueError("fixed byte-offset policy admits ASCII shipping sources only")
    text = source.decode("utf-8")
    words = set(_WORD.findall(text)) | set(_WORD.findall(opaque._logical(text)[0]))
    if words.intersection(_INSPECTION) or "/proc/self/exe" in text:
        raise ValueError("source has an excluded symbol/image/assembly observer")
    unit, nodes, diagnostics = parse(cindex, source, filename, arguments)
    kind = cindex.CursorKind
    definitions = {}
    for cursor, _ in nodes:
        if (_main(cursor, filename) and cursor.kind == kind.FUNCTION_DECL and cursor.is_definition()
                and cursor.storage_class == cindex.StorageClass.STATIC):
            definitions[_usr(cursor)] = cursor
    rows = {key: {"name": cursor.spelling, "declarations": [], "references": [], "excluded": []}
            for key, cursor in definitions.items()}
    lexical = {}
    for start, end, token in lexer._identifier_spans(text):
        lexical.setdefault(token, []).append((start, end))
    directive_words = set()
    for part_kind, part in opaque._opaque_parts(text):
        if part_kind == "directive":
            directive_words.update(_WORD.findall(part))
    for key, cursor in definitions.items():
        row = rows[key]
        tokens = {token.spelling for token in cursor.get_tokens()}
        if tokens.intersection(_SELF):
            row["excluded"].append("function observes its own spelling")
        if any(child.kind.is_attribute() for child in cursor.get_children()):
            row["excluded"].append("function has an attribute/implicit consumer")
        if cursor.linkage != cindex.LinkageKind.INTERNAL:
            row["excluded"].append("function is not internal linkage")
        if cursor.spelling in directive_words:
            row["excluded"].append("spelling occurs in an opaque directive")
        if cursor.spelling in {"main", "work", "tiny_eval_init"}:
            row["excluded"].append("explicit conservative callback/startup/main protection")
    for cursor, parents in nodes:
        if not _main(cursor, filename):
            continue
        if cursor.kind == kind.FUNCTION_DECL and _usr(cursor) in rows:
            key = _usr(cursor)
            row = rows[key]
            if cursor.storage_class != cindex.StorageClass.STATIC:
                row["excluded"].append("declaration storage differs")
            row["declarations"].append(cursor.location.offset)
        elif cursor.kind == kind.DECL_REF_EXPR and cursor.referenced is not None:
            key = _usr(cursor.referenced)
            if key in rows:
                row = rows[key]
                row["references"].append(cursor.location.offset)
                if not _direct_call(cursor, parents, key):
                    row["excluded"].append("address/argument/indirect or non-direct-call reference")
    reserved = words | set(lexer._KEYWORDS)
    reserved.update(cursor.spelling for cursor, _ in nodes if cursor.spelling)
    candidates = []
    for key, row in rows.items():
        old = row["name"]
        offsets = sorted(set(row["declarations"] + row["references"]))
        if len(offsets) != len(row["declarations"]) + len(row["references"]):
            row["excluded"].append("duplicate AST name locations")
        expected = [(offset, offset + len(old)) for offset in offsets]
        if expected != lexical.get(old, []):
            row["excluded"].append("same-spelled code token is outside bound function declarations/references")
        if any(source[start:end] != old.encode("ascii") for start, end in expected):
            row["excluded"].append("macro expansion/nonphysical source location")
        row["excluded"] = sorted(set(row["excluded"]))
        row["occurrences"] = len(offsets)
        if not row["excluded"]:
            candidates.append((old, key, offsets))
    mapping, edits, generated = {}, [], _aliases()
    for old, key, offsets in sorted(candidates):
        new = next(name for name in generated if name not in reserved)
        if len(new) >= len(old):
            rows[key]["excluded"].append("no shorter fresh alias in fixed order")
            continue
        reserved.add(new)
        mapping[old] = new
        rows[key]["alias"] = new
        for offset in offsets:
            edits.append((offset, offset + len(old), old, new))
    edits.sort()
    if any(edits[index - 1][1] > edits[index][0] for index in range(1, len(edits))):
        raise ValueError("overlapping AST edits")
    parts, previous = [], 0
    for start, end, old, new in edits:
        if source[start:end] != old.encode("ascii"):
            raise ValueError("AST source token mismatch")
        parts.extend((source[previous:start], new.encode("ascii")))
        previous = end
    parts.append(source[previous:])
    candidate = b"".join(parts)
    if opaque._opaque_parts(candidate.decode()) != opaque._opaque_parts(text):
        raise ValueError("directive/string/comment bytes changed")
    rewritten_unit, rewritten_nodes, new_diagnostics = parse(cindex, candidate, filename, arguments)
    before_signature = _signature(nodes, filename, {})
    after_signature = _signature(rewritten_nodes, filename, {new: old for old, new in mapping.items()})
    if before_signature != after_signature:
        for index, pair in enumerate(zip(before_signature, after_signature)):
            if pair[0] != pair[1]:
                raise ValueError("AST binding/shape changed at " + str(index) + ": " + repr(pair))
        raise ValueError("AST binding/shape length changed")
    metadata = {"before": {"bytes": len(source), "sha256": sha(source)},
        "after": {"bytes": len(candidate), "sha256": sha(candidate)},
        "mapping": mapping, "functions": [rows[key] for key in sorted(rows, key=lambda k: rows[k]["name"])],
        "edits": [{"start": a, "end": b, "old": old, "new": new} for a, b, old, new in edits],
        "AST_signature_sha256": sha(json.dumps(before_signature, separators=(",", ":")).encode()),
        "AST_signature_nodes": len(before_signature), "reparsed_binding_and_shape_equal": True,
        "diagnostics": diagnostics, "candidate_diagnostics": new_diagnostics,
        "opaque_regions_unchanged": True, "native_or_package_executed": False,
        "native_equality_claimed": False,
        "policy": "STATIC internal functions; every declaration/direct call bound by AST; all other uses excluded; fixed global-fresh alias order"}
    del unit, rewritten_unit
    return candidate, metadata
