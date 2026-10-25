"""Pure, bound module inlining for the independent Tiny Rust A candidate.

Production input is the four exact DEV/test-pruned files named below. The only
structural edit replaces each root ``mod name;`` by ``mod name { body }``. This
keeps module paths, privacy, imports and the main function. No identifiers,
algorithms, flags or resource policies are changed. ``merge_unbound`` exposes
the same bounded syntax contract for independent fixtures, without claiming a
production source binding.

The frozen Rust lexer is loaded and hash checked once at import. Calls perform
no I/O. Token identity does not preserve source file/line locations in compiler
diagnostics or panic locations. Span-observing source macros and attributes are
outside this producer's contract; the fixed standard macros are audited below.
"""

import hashlib
import json
from pathlib import Path
import types


FILES = ("main.rs", "board.rs", "search.rs", "runtime.rs")
MODULES = ("board", "search", "runtime")
EXPECTED = {
    "main.rs": "8c6a6b9f9789f7245df10c620723dde6d2f4287afc166d083c768c6e5bfacd0e",
    "board.rs": "62d99b2aa5f628750152c4e0e627e2ecd681e54abd2db3c76c889c8ad3d7e57f",
    "search.rs": "d24fd229bbddebc91146334ed66f39567ac9ec1deaee2c055e3eac4bd43c4cb8",
    "runtime.rs": "aedb9ef9503bde3f5db392cd73cd6dbeecf30c82f006b836f09a8b3ad4a90344",
}
EXPECTED_SYNTAX = "54ff9e05cbcb099c6ee96e09014be3d2a80c21fb8bf21e508b0a03bda5114100"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


_syntax_path = Path(__file__).resolve().parents[2] / "compact" / "rust" / "syntax.py"
_syntax_bytes = _syntax_path.read_bytes()
if _sha(_syntax_bytes) != EXPECTED_SYNTAX:
    raise ValueError("Rust lexer source changed; audit and rebind the module merger")
SYNTAX = types.ModuleType("tiny_rust_stream_syntax")
SYNTAX.__file__ = str(_syntax_path)
exec(compile(_syntax_bytes, str(_syntax_path), "exec"), SYNTAX.__dict__)

# Standard macros used by the bound files. They consume normal Rust expression
# tokens or literal environment keys; none includes external source. Macro
# definitions/imported procedural derives are not part of these source inputs.
MACROS = frozenset(("assert", "option_env", "println", "vec", "writeln"))
DERIVES = frozenset(("Clone", "Copy", "Default", "Debug"))
_KEYWORDS = frozenset((
    "as", "async", "await", "break", "const", "continue", "crate", "dyn",
    "else", "enum", "extern", "false", "fn", "for", "if", "impl", "in",
    "let", "loop", "match", "mod", "move", "mut", "pub", "ref", "return",
    "self", "Self", "static", "struct", "super", "trait", "true", "type",
    "unsafe", "use", "where", "while",
))
_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {v: k for k, v in _OPEN.items()}


def _identifier(token):
    return (token[2:] if token.startswith("r#") else token).isidentifier()


def _pairs(tokens):
    """Validate all ordinary delimiters; literals and docs remain opaque."""
    stack, pairs = [], {}
    for pos, token in enumerate(tokens):
        if token in _OPEN:
            stack.append(pos)
        elif token in _CLOSE:
            if not stack or tokens[stack[-1]] != _CLOSE[token]:
                raise ValueError(f"mismatched Rust delimiter at token {pos}")
            begin = stack.pop()
            pairs[begin] = pos
            pairs[pos] = begin
    if stack:
        raise ValueError(f"unclosed Rust delimiter at token {stack[-1]}")
    return pairs


def _roots(tokens, pairs):
    pos = 0
    while pos < len(tokens):
        yield pos
        pos = pairs[pos] + 1 if tokens[pos] in _OPEN else pos + 1


def _token_sha(tokens):
    return _sha(json.dumps(tokens, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _guard(name, tokens):
    pairs = _pairs(tokens)
    roots = set(_roots(tokens, pairs))
    declarations, macros, derives = {}, {}, []
    for pos, token in enumerate(tokens):
        if token.startswith("#!"):
            raise ValueError(f"shebang is outside the inlining contract: {name}")
        if token in ("extern", "macro", "macro_rules"):
            raise ValueError(f"external declarations or macro definitions are unsupported: {name}: {token}")
        if token == "#":
            if tokens[pos + 1:pos + 2] != ["["]:
                raise ValueError(f"unsupported Rust attribute shape: {name}")
            end = pairs[pos + 1]
            attr = tokens[pos + 2:end]
            if len(attr) < 4 or attr[:2] != ["derive", "("] or attr[-1] != ")":
                raise ValueError(f"only audited builtin derive attributes are allowed: {name}")
            if pairs[pos + 3] != end - 1:
                raise ValueError(f"unexpected derive attribute shape: {name}")
            parts = attr[2:-1]
            values, expect_name = [], True
            for part in parts:
                if expect_name and part in DERIVES:
                    values.append(part)
                elif not expect_name and part == ",":
                    pass
                else:
                    raise ValueError(f"unsupported derive trait or syntax: {name}")
                expect_name = not expect_name
            if not values:
                raise ValueError(f"empty derive attribute: {name}")
            derives.append(values)
        if token == "!" and tokens[pos + 1:pos + 2] and tokens[pos + 1] in _OPEN and pos:
            previous = tokens[pos - 1]
            # `if !(...)`, `return !{...}` and `while ![...]` are unary NOT,
            # unlike an identifier/path immediately followed by a macro bang.
            if _identifier(previous) and (previous not in _KEYWORDS or previous.startswith("r#")):
                if previous not in MACROS:
                    raise ValueError(f"unsupported or span/source-observing macro: {name}: {previous}!")
                macros[previous] = macros.get(previous, 0) + 1
        if token == "mod":
            if pos + 2 >= len(tokens) or not _identifier(tokens[pos + 1]):
                raise ValueError(f"unexpected module declaration shape: {name}")
            module, kind = tokens[pos + 1:pos + 3]
            if kind == ";":
                if name != "main.rs" or pos not in roots or module not in MODULES:
                    raise ValueError(f"external modules outside the three root declarations are forbidden: {name}")
                previous = tokens[pos - 1] if pos else ";"
                if previous not in (";", "}") and not previous.startswith(("//!", "/*!")):
                    raise ValueError(f"root module declaration must be naked: {module}")
                if module in declarations:
                    raise ValueError(f"duplicate root module declaration: {module}")
                declarations[module] = pos
            elif kind == "{":
                if name == "main.rs" and pos in roots and module in MODULES:
                    raise ValueError(f"expected an external root module declaration: {module}")
            else:
                raise ValueError(f"unexpected module declaration shape: {name}")
    if name == "main.rs":
        if set(declarations) != set(MODULES):
            raise ValueError("main.rs needs exactly one naked root declaration for board/search/runtime")
        mains = [p for p in roots if tokens[p:p + 2] == ["fn", "main"]]
        if len(mains) != 1:
            raise ValueError("main.rs needs exactly one root fn main")
    elif declarations:
        raise ValueError(f"unexpected external module declaration: {name}")
    return pairs, declarations, {"macro_invocations": macros, "builtin_derives": derives}


def _merge(files, bound):
    if not isinstance(files, dict) or set(files) != set(FILES):
        raise ValueError("expected exactly main.rs, board.rs, search.rs and runtime.rs")
    if any(not isinstance(value, bytes) for value in files.values()):
        raise ValueError("Rust source values must be immutable bytes")
    hashes = {name: _sha(files[name]) for name in FILES}
    if bound:
        drift = [name for name in FILES if hashes[name] != EXPECTED[name]]
        if drift:
            raise ValueError("DEV-pruned source SHA-256 binding mismatch: " + ", ".join(drift))
    token_sets, guards = {}, {}
    for name in FILES:
        try:
            tokens = SYNTAX.tokenize(files[name].decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError(f"invalid Rust lexical input: {name}: {error}") from error
        _, declarations, guards[name] = _guard(name, tokens)
        token_sets[name] = tokens
        if name == "main.rs":
            root_declarations = declarations
    main = token_sets["main.rs"]
    replacements = {pos: module for module, pos in root_declarations.items()}
    output, cursor = [], 0
    for pos, module in sorted(replacements.items()):
        output.extend(main[cursor:pos])
        output.extend(["mod", module, "{", *token_sets[module + ".rs"], "}"])
        cursor = pos + 3
    output.extend(main[cursor:])
    data = (SYNTAX.render(output) + "\n").encode("utf-8")
    recovered = SYNTAX.tokenize(data.decode("utf-8"))
    if recovered != output:
        raise ValueError("rendering changed the merged Rust token sequence")
    pairs = _pairs(recovered)
    locations, modules, restored = {}, {}, []
    cursor = 0
    for pos in _roots(recovered, pairs):
        if recovered[pos] != "mod":
            continue
        module = recovered[pos + 1]
        if module not in MODULES:
            continue
        if recovered[pos + 2:pos + 3] != ["{"] or module in locations:
            raise ValueError("unexpected module structure after inlining")
        close = pairs[pos + 2]
        body = recovered[pos + 3:close]
        original = token_sets[module + ".rs"]
        if body != original:
            raise ValueError(f"inlined module tokens changed: {module}")
        restored.extend(recovered[cursor:pos])
        restored.extend(["mod", module, ";"])
        cursor = close + 1
        locations[module] = [pos + 3, close]
        modules[module] = {
            "input": module + ".rs", "input_tokens": len(original),
            "input_token_sha256": _token_sha(original),
            "output_body_token_sha256": _token_sha(body),
            "output_body_token_span": [pos + 3, close],
            "body_token_identity": True,
        }
    restored.extend(recovered[cursor:])
    if set(locations) != set(MODULES) or restored != main:
        raise ValueError("main tokens outside the three declarations changed")
    metadata = {
        "producer": "tiny-rust-inline-modules-v1",
        "production_binding_verified": bound,
        "input_sha256": hashes,
        "input_bytes": sum(map(len, files.values())),
        "input_token_sha256": {name: _token_sha(token_sets[name]) for name in FILES},
        "output_sha256": _sha(data), "output_bytes": len(data),
        "output_tokens": len(recovered), "output_token_sha256": _token_sha(recovered),
        "syntax_sha256": EXPECTED_SYNTAX,
        "modules": modules,
        "main_token_identity_outside_declarations": True,
        "guards": guards,
        "changes": {"external_root_modules_inlined": 3, "renamed_identifiers": 0,
                    "policy_changes": 0, "compiler_flag_changes": 0},
        "external_source_inputs": False,
        "source_locations_preserved": False,
    }
    return data, metadata


def merge(files: dict[str, bytes]) -> tuple[bytes, dict]:
    """Inline only the three modules in the exact bound DEV-pruned source."""
    return _merge(files, True)


def merge_unbound(files: dict[str, bytes]) -> tuple[bytes, dict]:
    """Independent fixture API; identical guards but no production hash claim."""
    return _merge(files, False)
