"""Embody one fixed resource profile in the exact merged Tiny Rust A source.

Only the audited 2-worker / TT-bits-18 profile is supported. The root decimal
parser is unused after replacing the two constant initializers by their fixed
values, so its definition is removed. Every other source token is preserved.
The fixed recipe still supplies the same compiler environment; no compiler flag,
identifier, search, board, runtime or main-function change is made.

The hash-checked Rust lexer is loaded once at import. ``embody`` performs no I/O
and does not consult the process environment. Compiler diagnostic/panic source
locations, already outside the module merger's contract, remain unpreserved.
"""

import hashlib
import json
from pathlib import Path
import types


EXPECTED_SOURCE = "06cae21874330adaf436f91d16450a53b8dbb836072531e73700f89e27de5cd3"
EXPECTED_BYTES = 23334
EXPECTED_SYNTAX = "54ff9e05cbcb099c6ee96e09014be3d2a80c21fb8bf21e508b0a03bda5114100"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


_syntax_path = Path(__file__).resolve().parents[2] / "compact" / "rust" / "syntax.py"
_syntax_bytes = _syntax_path.read_bytes()
if _sha(_syntax_bytes) != EXPECTED_SYNTAX:
    raise ValueError("Rust lexer source changed; audit and rebind fixed resources")
SYNTAX = types.ModuleType("tiny_rust_stream_resources_syntax")
SYNTAX.__file__ = str(_syntax_path)
exec(compile(_syntax_bytes, str(_syntax_path), "exec"), SYNTAX.__dict__)


def _token_sha(tokens):
    return _sha(json.dumps(tokens, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _roots(tokens):
    pos = 0
    while pos < len(tokens):
        yield pos
        pos = SYNTAX.matching(tokens, pos) + 1 if tokens[pos] in ("(", "[", "{") else pos + 1


def _number_definition(tokens, roots):
    starts = [p for p in roots if tokens[p:p + 3] == ["const", "fn", "number"]]
    if len(starts) != 1:
        raise ValueError("expected exactly one root const fn number")
    start = starts[0]
    if tokens[start + 3] != "(":
        raise ValueError("unexpected number parameter shape")
    end_params = SYNTAX.matching(tokens, start + 3)
    params = ["value", ":", "Option", "<", "&", "str", ">", ",", "default", ":", "usize"]
    if tokens[start + 4:end_params] != params or tokens[end_params + 1:end_params + 4] != ["->", "usize", "{"]:
        raise ValueError("unexpected root number signature")
    end = SYNTAX.matching(tokens, end_params + 3) + 1
    return start, end


def _constant(tokens, roots, name, environment, default):
    starts = [p for p in roots if tokens[p:p + 2] == ["const", name]]
    if len(starts) != 1:
        raise ValueError("expected exactly one root constant: " + name)
    start = starts[0]
    if tokens[start:start + 5] != ["const", name, ":", "usize", "="]:
        raise ValueError("resource constant name/type changed: " + name)
    begin = start + 5
    expected = ["number", "(", "option_env", "!", "(", json.dumps(environment), ")", ",", str(default), ")"]
    end = begin + len(expected)
    if tokens[begin:end] != expected or tokens[end:end + 1] != [";"]:
        raise ValueError("unexpected fixed resource initializer: " + name)
    return begin, end


def _module_bodies(tokens):
    result = {}
    for pos in _roots(tokens):
        if tokens[pos:pos + 1] != ["mod"]:
            continue
        name = tokens[pos + 1]
        if name not in ("board", "search", "runtime") or tokens[pos + 2] != "{" or name in result:
            raise ValueError("unexpected merged root module shape")
        end = SYNTAX.matching(tokens, pos + 2)
        result[name] = tokens[pos + 3:end]
    if set(result) != {"board", "search", "runtime"}:
        raise ValueError("expected three inline production modules")
    return result


def _main_function(tokens):
    starts = [p for p in _roots(tokens) if tokens[p:p + 2] == ["fn", "main"]]
    if len(starts) != 1:
        raise ValueError("expected exactly one root main function")
    start = starts[0]
    if tokens[start:start + 5] != ["fn", "main", "(", ")", "{"]:
        raise ValueError("unexpected main function signature")
    return tokens[start:SYNTAX.matching(tokens, start + 4) + 1]


def _original_number(text, default):
    # The bound Rust const fn returns default only for None. The fixed recipe
    # supplies these two nonempty ASCII strings, so no environment is read here.
    if text is None:
        return default
    n = 0
    for c in text:
        if not "0" <= c <= "9":
            return 0
        n = min((1 << 64) - 1, n * 10 + ord(c) - ord("0"))
    return n if text else 0


def embody(source: bytes, *, workers: int = 2, tt_bits: int = 18) -> tuple[bytes, dict]:
    """Return the bound merged source with only fixed 2/18 resources embodied."""
    if type(workers) is not int or type(tt_bits) is not int or workers != 2 or tt_bits != 18:
        raise ValueError("fixed-resource producer supports only workers=2 and tt_bits=18")
    if not isinstance(source, bytes):
        raise ValueError("merged Rust source must be immutable bytes")
    if len(source) != EXPECTED_BYTES or _sha(source) != EXPECTED_SOURCE:
        raise ValueError("exact merged source SHA-256/size binding mismatch")
    tokens = SYNTAX.tokenize(source.decode("utf-8"))
    roots = list(_roots(tokens))
    number_start, number_end = _number_definition(tokens, roots)
    constants = {
        "WORKERS": ("ROVE_WORKERS", 2, workers),
        "TT_BITS": ("ROVE_TT_BITS", 16, tt_bits),
    }
    edits = [(number_start, number_end, [], "remove-unused-number")]
    initializers, references = {}, [number_start + 2]
    for name, (environment, default, literal) in constants.items():
        begin, end = _constant(tokens, roots, name, environment, default)
        parsed = _original_number(str(literal), default)
        if parsed != literal:
            raise ValueError("original initializer does not equal the fixed resource: " + name)
        edits.append((begin, end, [str(literal)], "embody-" + name))
        references.append(begin)
        initializers[name] = {
            "type": "usize", "environment": environment, "fixed_environment_value": str(literal),
            "original_fallback": default, "original_parsed_value": parsed, "literal": literal,
            "input_initializer_token_sha256": _token_sha(tokens[begin:end]),
        }
    if [p for p, token in enumerate(tokens) if token == "number"] != sorted(references):
        raise ValueError("number has references outside its definition and the two resource constants")
    output, spans, cursor = [], [], 0
    for begin, end, replacement, label in sorted(edits):
        if begin < cursor:
            raise ValueError("overlapping fixed resource edits")
        output.extend(tokens[cursor:begin])
        out_begin = len(output)
        output.extend(replacement)
        spans.append((out_begin, len(output), tokens[begin:end], label))
        cursor = end
    output.extend(tokens[cursor:])
    data = (SYNTAX.render(output) + "\n").encode("utf-8")
    recovered = SYNTAX.tokenize(data.decode("utf-8"))
    if recovered != output:
        raise ValueError("rendering changed embodied Rust token spellings")
    restored, cursor = [], 0
    for begin, end, old, _ in spans:
        restored.extend(recovered[cursor:begin])
        restored.extend(old)
        cursor = end
    restored.extend(recovered[cursor:])
    if restored != tokens:
        raise ValueError("tokens outside the fixed resource edits changed")
    before_modules, after_modules = _module_bodies(tokens), _module_bodies(recovered)
    modules = {}
    for name in before_modules:
        if before_modules[name] != after_modules[name]:
            raise ValueError("fixed resources changed a module body: " + name)
        modules[name] = {
            "tokens": len(before_modules[name]), "body_token_identity": True,
            "input_token_sha256": _token_sha(before_modules[name]),
            "output_token_sha256": _token_sha(after_modules[name]),
        }
    before_main, after_main = _main_function(tokens), _main_function(recovered)
    if before_main != after_main:
        raise ValueError("fixed resources changed main function tokens")
    metadata = {
        "producer": "tiny-rust-fixed-resources-v1", "production_binding_verified": True,
        "input_sha256": EXPECTED_SOURCE, "input_bytes": len(source),
        "output_sha256": _sha(data), "output_bytes": len(data), "saved_bytes": len(source) - len(data),
        "input_token_sha256": _token_sha(tokens), "output_token_sha256": _token_sha(recovered),
        "syntax_sha256": EXPECTED_SYNTAX, "profile": {"workers": workers, "tt_bits": tt_bits},
        "initializers": initializers, "number_reference_count_before": len(references),
        "number_reference_count_after": recovered.count("number"),
        "removed_number_definition_token_sha256": _token_sha(tokens[number_start:number_end]),
        "modules": modules, "remaining_tokens_restoration_identity": True,
        "main_function_token_identity": True, "main_function_token_sha256": _token_sha(before_main),
        "changes": [label for _, _, _, label in spans],
        "renamed_identifiers": 0, "compiler_flag_changes": 0, "source_locations_preserved": False,
    }
    return data, metadata
