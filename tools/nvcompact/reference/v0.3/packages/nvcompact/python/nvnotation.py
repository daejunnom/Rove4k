#!/usr/bin/env python3
"""Bounded, audited source-spelling candidates; no C/Rust AST rewriting.

Identity is always available. Rewrites require an explicit source/token
non-observation contract and still belong in the normal build/verify portfolio.
The integer model is LP64; floating candidates preserve an exact rational and
the literal's type/inference class. This is not a general equivalence prover.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import sys
import tokenize

VERSION = "0.2.0"
TARGETS = {"c": {"c11-lp64", "c23-lp64"},
           "cpp": {"cpp17-lp64"}, "rust": {"rust2021"},
           "python": {"python3"}}
DEFAULT_TARGET = {k: sorted(v)[0] for k, v in TARGETS.items()}
POLICIES = ("shortest", "hex", "decimal", "scientific", "octal", "binary")
MAX_LITERAL = 512
MAX_SOURCE = 8 << 20


class NotationError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int
    end: int


def _ident_start(c: str) -> bool:
    return bool(c) and (c.isalpha() or c == "_" or ord(c) >= 128)


def _ident(c: str) -> bool:
    return _ident_start(c) or bool(c) and c.isdigit()


_PUNCT = sorted({"%:%:", ">>=", "<<=", "...", "->*", "<=>", "..=", "::",
                 "->", "++", "--", "<<", ">>", "<=", ">=", "==", "!=", "&&",
                 "||", "*=", "/=", "%=", "+=", "-=", "&=", "^=", "|=", "##",
                 "<:", ":>", "<%", "%>", "%:", ".*", "..", "=>"}, key=lambda x: (-len(x), x))
_C_RAW = re.compile(r'(?:u8|u|U|L)?R"([^ ()\\\t\r\n]{0,16})\(')
_RUST_RAW = re.compile(r'(?:br|cr|r)(#*)"')
_C_QUOTE = re.compile(r'(?:u8|u|U|L)?["\']')
_RUST_QUOTE = re.compile(r'(?:b|c)?["\']')
_RUST_LIFETIME = re.compile(r"'(?:r#)?[A-Za-z_][A-Za-z_0-9]*")


def _quoted_end(s: str, pos: int, quote: str) -> int:
    i = pos + 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
        elif s[i] == quote:
            return i + 1
        else:
            i += 1
    raise NotationError("unterminated quoted token")


def _lex(s: str, language: str) -> list[Token]:
    """Small lossless lexer, not a parser. Unknown tokens remain opaque."""
    result: list[Token] = []
    i = 0
    line_code = False
    while i < len(s):
        start = i
        c = s[i]
        kind = "punct"
        if c.isspace():
            i += 1
            while i < len(s) and s[i].isspace():
                i += 1
            kind = "space"
        elif s.startswith("//", i):
            i += 2
            while i < len(s):
                if language != "rust" and s[i] == "\\" and s[i + 1:i + 2] == "\n":
                    i += 2
                elif s[i] == "\n":
                    break
                else:
                    i += 1
            kind = "doc" if language == "rust" and (s.startswith("//!", start) or
                    s.startswith("///", start) and not s.startswith("////", start)) else "comment"
        elif s.startswith("/*", i):
            depth = 1
            i += 2
            while i < len(s) and depth:
                if language == "rust" and s.startswith("/*", i):
                    depth += 1
                    i += 2
                elif s.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                raise NotationError("unterminated block comment")
            kind = "doc" if language == "rust" and (s.startswith("/*!", start) or
                    s.startswith("/**", start) and not s.startswith("/***", start)) else "comment"
        elif language != "rust" and not line_code and (c == "#" or s.startswith("%:", i)):
            while i < len(s):
                if s[i] == "\\" and s[i + 1:i + 2] == "\n":
                    i += 2
                elif s[i] == "\\" and s[i + 1:i + 3] == "\r\n":
                    i += 3
                elif s[i] == "\n":
                    i += 1
                    break
                else:
                    i += 1
            kind = "directive"
        else:
            raw = _C_RAW.match(s, i) if language == "cpp" else None
            rust_raw = _RUST_RAW.match(s, i) if language == "rust" else None
            prefix = (_C_QUOTE if language != "rust" else _RUST_QUOTE).match(s, i)
            if raw:
                end = s.find(")" + raw.group(1) + '"', raw.end())
                if end < 0:
                    raise NotationError("unterminated C++ raw string")
                i = end + len(raw.group(1)) + 2
                kind = "quoted"
            elif rust_raw:
                marker = '"' + rust_raw.group(1)
                end = s.find(marker, rust_raw.end())
                if end < 0:
                    raise NotationError("unterminated Rust raw string")
                i = end + len(marker)
                kind = "quoted"
            elif language == "rust" and c == "'" and (life := _RUST_LIFETIME.match(s, i)) and s[life.end():life.end() + 1] != "'":
                i = life.end()
                kind = "lifetime"
            elif prefix:
                pos = prefix.end() - 1
                i = _quoted_end(s, pos, s[pos])
                kind = "quoted"
            elif c.isdigit() or language != "rust" and c == "." and s[i + 1:i + 2].isdigit():
                i += 1
                if language == "rust":
                    if s[start:start + 2] in ("0x", "0o", "0b"):
                        i = start + 2
                        while i < len(s) and _ident(s[i]):
                            i += 1
                    else:
                        while i < len(s) and (s[i].isdigit() or s[i] == "_"):
                            i += 1
                        if s[i:i + 1] == "." and s[i + 1:i + 2] != "." and not _ident_start(s[i + 1:i + 2]):
                            i += 1
                            while i < len(s) and (s[i].isdigit() or s[i] == "_"):
                                i += 1
                        if s[i:i + 1] in ("e", "E"):
                            i += 1
                            if s[i:i + 1] in ("+", "-"):
                                i += 1
                        while i < len(s) and _ident(s[i]):
                            i += 1
                else:
                    while i < len(s):
                        if _ident(s[i]) or s[i] in ".'":
                            i += 1
                        elif s[i] in "+-" and s[i - 1] in "eEpP":
                            i += 1
                        else:
                            break
                kind = "number"
            elif _ident_start(c):
                i += 1
                while i < len(s) and _ident(s[i]):
                    i += 1
                # A Rust raw identifier is one token, not an opportunity to remove '#'.
                if language == "rust" and s[start:i] == "r" and s[i:i + 1] == "#" and _ident_start(s[i + 1:i + 2]):
                    i += 2
                    while i < len(s) and _ident(s[i]):
                        i += 1
                kind = "identifier"
            else:
                p = next((p for p in _PUNCT if s.startswith(p, i)), None)
                i += len(p) if p else 1
            if kind == "quoted" and language in ("cpp", "rust"):
                while i < len(s) and _ident(s[i]):
                    i += 1  # literal suffix stays attached, even when invalid in an expression
        text = s[start:i]
        result.append(Token(kind, text, start, i))
        if "\n" in text:
            line_code = bool(text.rsplit("\n", 1)[1].strip()) and kind not in ("space", "comment", "doc", "directive")
        elif kind not in ("space", "comment", "doc"):
            line_code = True
    return result


def _protected_tokens(tokens: list[Token], language: str) -> set[int]:
    sig = [i for i, t in enumerate(tokens) if t.kind not in ("space", "comment", "doc")]
    protected: set[int] = set()
    opens = {"(": ")", "[": "]", "{": "}"}
    closes = {}
    stack: list[tuple[int, str]] = []
    intervals = []
    for pos, idx in enumerate(sig):
        text = tokens[idx].text
        if text in opens:
            stack.append((pos, opens[text]))
        elif text in opens.values():
            if stack and stack[-1][1] == text:
                begin, _ = stack.pop()
                closes[begin] = pos
            else:
                stack.clear()
    keywords = {"if", "while", "for", "switch", "sizeof", "_Alignof", "_Generic",
                "alignof", "decltype", "noexcept", "static_assert"}
    for n, i in enumerate(sig):
        t = tokens[i]
        start = None
        if language == "rust":
            if t.text == "!" and n and tokens[sig[n - 1]].kind == "identifier":
                j = n + 1
                if j < len(sig) and tokens[sig[j]].kind == "identifier":
                    j += 1  # macro_rules! name { ... }
                if j < len(sig) and tokens[sig[j]].text in opens:
                    start = j
            elif t.text == "#":
                j = n + 1
                if j < len(sig) and tokens[sig[j]].text == "!":
                    j += 1
                if j < len(sig) and tokens[sig[j]].text == "[":
                    start = j
            elif t.kind == "number" and n and tokens[sig[n - 1]].text == ".":
                protected.add(i)  # tuple fields are spelled decimal indices, not values
        elif t.text == "(" and n and tokens[sig[n - 1]].kind == "identifier" and tokens[sig[n - 1]].text not in keywords:
            start = n  # unknown header-defined function-like macros may stringify
        if start is not None and start in closes:
            intervals.append((sig[start], sig[closes[start]]))
    last = -1
    for begin, end in sorted(intervals):
        if end > last:
            protected.update(range(max(begin, last + 1), end + 1))
            last = end
    return protected


def _c_type(value: int, base: int, suffix: str) -> str | None:
    suffix = suffix.lower()
    decimal = base == 10
    choices = {"": ("int", "long", "long long") if decimal else ("int", "unsigned int", "long", "unsigned long", "long long", "unsigned long long"),
               "u": ("unsigned int", "unsigned long", "unsigned long long"),
               "l": ("long", "long long") if decimal else ("long", "unsigned long", "long long", "unsigned long long"),
               "ul": ("unsigned long", "unsigned long long"),
               "lu": ("unsigned long", "unsigned long long"),
               "ll": ("long long",) if decimal else ("long long", "unsigned long long"),
               "ull": ("unsigned long long",), "llu": ("unsigned long long",)}.get(suffix, ())
    for typ in choices:
        bits = 32 if typ in ("int", "unsigned int") else 64
        if value < 1 << (bits if typ.startswith("unsigned") else bits - 1):
            return typ
    return None


def _integer(text: str, language: str, target: str) -> tuple[int, str, list[tuple[str, str]]] | None:
    if language in ("c", "cpp"):
        if "'" in text:
            if target == "c11-lp64" or re.search(r"(^|[^0-9a-fA-F])'|'([^0-9a-fA-F]|$)", text):
                return None
            text = text.replace("'", "")
        m = re.fullmatch(r"(0[xX][0-9a-fA-F]+|0[bB][01]+|0[0-7]*|[1-9][0-9]*)([uUlL]*)", text)
        if not m or re.search(r"lL|Ll", m[2]):
            return None
        body, suffix = m.groups()
        base = 16 if body.lower().startswith("0x") else 2 if body.lower().startswith("0b") else 8 if body.startswith("0") else 10
        if base == 2 and target == "c11-lp64":
            return None
        value = int(body, base)
        typ = _c_type(value, base, suffix)
        if typ is None:
            return None
        bases = [(10, "decimal", str(value)), (16, "hex", hex(value)),
                 (8, "octal", "0" + format(value, "o") if value else "0")]
        if target != "c11-lp64":
            bases.append((2, "binary", bin(value)))
        forms = [(body + suffix, family) for base, family, body in bases
                 for suffix in ("", "u", "l", "ul", "ll", "ull")
                 if _c_type(value, base, suffix) == typ]
        return value, typ, forms
    if language == "rust":
        compact = text.replace("_", "")
        m = re.fullmatch(r"(0x[0-9a-fA-F]+|0o[0-7]+|0b[01]+|[0-9]+)(u8|i8|u16|i16|u32|i32|u64|i64|u128|i128|usize|isize)?", compact)
        if not m:
            return None
        body, suffix = m[1], m[2] or ""
        value = int(body, 0) if body.startswith(("0x", "0o", "0b")) else int(body, 10)
        if value >= 1 << 128:
            return None
        forms = [(str(value) + suffix, "decimal"), (hex(value) + suffix, "hex"),
                 (oct(value) + suffix, "octal"), (bin(value) + suffix, "binary")]
        return value, suffix or "inferred integer", forms
    return None


def _fraction(text: str) -> Fraction:
    if text.lower().startswith("0x"):
        significand, exp_text = re.split("[pP]", text[2:])
        exponent = int(exp_text)
        before, _, after = significand.partition(".")
        if abs(exponent) > 2048:
            raise ValueError("exponent outside notation budget")
        value = Fraction(int((before or "0") + after, 16), 16 ** len(after))
        return value * 2 ** exponent if exponent >= 0 else value / 2 ** -exponent
    decimal = Decimal(text)
    if not decimal.is_finite() or abs(decimal.as_tuple().exponent) > 2048:
        raise ValueError("exponent outside notation budget")
    return Fraction(decimal)


def _ieee_bits(value: Fraction, fraction_bits: int, exponent_bits: int) -> int | None:
    """Exact rational -> round-to-nearest, ties-to-even IEEE positive value."""
    if not value:
        return 0
    n, d = value.numerator, value.denominator
    e = n.bit_length() - d.bit_length()
    if (n < d << e) if e >= 0 else (n << -e < d):
        e -= 1
    bias = (1 << (exponent_bits - 1)) - 1
    minimum = 1 - bias
    unit = max(e, minimum) - fraction_bits
    numerator, denominator = (n, d << unit) if unit >= 0 else (n << -unit, d)
    mantissa, rem = divmod(numerator, denominator)
    if rem * 2 > denominator or rem * 2 == denominator and mantissa & 1:
        mantissa += 1
    if e < minimum:
        return mantissa  # includes rounding to the smallest normal value
    if mantissa == 1 << (fraction_bits + 1):
        mantissa >>= 1
        e += 1
    if e > bias:
        return None
    return ((e + bias) << fraction_bits) | (mantissa - (1 << fraction_bits))


def _decimal_forms(value: Fraction, language: str, suffix: str) -> set[tuple[str, str]]:
    n, d = value.numerator, value.denominator
    twos = fives = 0
    while d % 2 == 0:
        d //= 2
        twos += 1
    while d % 5 == 0:
        d //= 5
        fives += 1
    if d != 1:
        return set()
    places = max(twos, fives)
    digits = str(n * 2 ** (places - twos) * 5 ** (places - fives))
    exponent = -places
    if n == 0:
        digits, exponent = "0", 0
    else:
        while digits.endswith("0"):
            digits = digits[:-1]
            exponent += 1
    if len(digits) > MAX_LITERAL:
        return set()
    forms: set[tuple[str, str]] = set()
    for k in range(1, len(digits) + 1):
        mantissa = digits[:k] + ("." + digits[k:] if k < len(digits) else "")
        exp = exponent + len(digits) - k
        forms.add((mantissa + "e" + str(exp) + suffix, "scientific"))
    point = len(digits) + exponent
    if abs(point) <= MAX_LITERAL:
        fixed = ("0." + "0" * -point + digits if point <= 0 else
                 digits[:point] + "." + digits[point:] if point < len(digits) else
                 digits + "0" * (point - len(digits)) + ".")
        if language == "rust":
            if suffix and fixed.endswith("."):
                fixed = fixed[:-1]  # 12f32 is float; 12.f32 is member syntax
            forms.add((fixed + suffix, "decimal"))
        else:
            forms.add((fixed + suffix, "decimal"))
            if fixed.startswith("0."):
                forms.add((fixed[1:] + suffix, "decimal"))
    return forms


def _float(text: str, language: str, target: str) -> tuple[str, Fraction, list[tuple[str, str]], dict] | None:
    compact = text.replace("_", "") if language == "rust" else text.replace("'", "") if target != "c11-lp64" else text
    decimal_pattern = r"(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+"
    if language == "rust":
        m = re.fullmatch(r"(" + decimal_pattern + r"|[0-9]+)(f32|f64)?", compact)
        if not m or not m[2] and "." not in m[1] and "e" not in m[1].lower():
            return None
        if m[1].startswith(".") or m[2] and m[1].endswith("."):
            return None
        body, suffix = m[1], m[2] or ""
        typ = suffix or "inferred float"
    else:
        m = re.fullmatch(r"(" + decimal_pattern + r"|0[xX](?:[0-9a-fA-F]+\.?[0-9a-fA-F]*|\.[0-9a-fA-F]+)[pP][+-]?[0-9]+)([fFlL]?)", compact)
        if not m or m[2].lower() == "l":
            return None  # long double ABI/rounding is not covered by this model
        body, suffix = m[1], m[2].lower()
        typ = "float" if suffix else "double"
    try:
        value = _fraction(body)
    except (ValueError, InvalidOperation, OverflowError):
        return None
    widths = ((23, 8),) if typ in ("float", "f32") else ((52, 11),) if typ in ("double", "f64") else ((23, 8), (52, 11))
    bits = {f"binary{32 if f == 23 else 64}": _ieee_bits(value, f, e) for f, e in widths}
    if all(v is None for v in bits.values()):
        return None
    forms = _decimal_forms(value, language, suffix)
    if language in ("c", "cpp") and value.denominator & (value.denominator - 1) == 0:
        n = value.numerator
        exponent = -(value.denominator.bit_length() - 1)
        if n:
            while n % 2 == 0:
                n //= 2
                exponent += 1
        digits = format(n, "x")
        if len(digits) <= MAX_LITERAL:
            for k in range(1, len(digits) + 1):
                mantissa = digits[:k] + ("." + digits[k:] if k < len(digits) else "")
                forms.add(("0x" + mantissa + "p" + str(exponent + 4 * (len(digits) - k)) + suffix, "hex"))
    # Equality of exact rational values is stronger than host Python float equality.
    return typ, value, sorted(forms), bits


def literal_candidates(text: str, *, language: str, target: str | None = None) -> list[dict]:
    """Candidate spellings for ONE literal in an ordinary expression context."""
    language = {"c++": "cpp", "py": "python"}.get(language, language)
    target = target or DEFAULT_TARGET.get(language)
    if language not in TARGETS or target not in TARGETS[language]:
        raise NotationError("unsupported language/target pair")
    if len(text) > MAX_LITERAL:
        return []
    if language == "python":
        return _python_literal(text)
    integer = _integer(text, language, target)
    if integer:
        value, typ, forms = integer
        proof = {"model": target, "kind": "integer", "value": str(value), "type": typ}
    else:
        floating = _float(text, language, target)
        if not floating:
            return []
        typ, value, forms, bits = floating
        proof = {"model": target, "kind": "float", "exact_value": f"{value.numerator}/{value.denominator}",
                 "type": typ, "round_nearest_even_bits": bits,
                 "compiler_condition": "IEEE binary32/binary64 conversion; verify target build"}
    seen = set()
    result = []
    for spelling, family in sorted(forms, key=lambda x: (len(x[0]), x[0], x[1])):
        if spelling in seen or len(spelling) > MAX_LITERAL:
            continue
        seen.add(spelling)
        result.append({"spelling": spelling, "family": family, "proof": proof})
    return result


def _python_literal(text: str) -> list[dict]:
    try:
        value = ast.literal_eval(text)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return []
    forms: set[tuple[str, str]] = set()
    if type(value) is int and value >= 0:
        forms.update(((str(value), "decimal"), (hex(value), "hex"), (oct(value), "octal"), (bin(value), "binary")))
    elif type(value) is float and math.isfinite(value) and value >= 0:
        forms.add((repr(value), "decimal"))
        for precision in range(1, 18):
            for spec in ("g", "e"):
                candidate = format(value, f".{precision}{spec}")
                candidate = re.sub(r"e\+?(-?)0*([0-9]+)$", r"e\1\2", candidate)
                if "e" in candidate:
                    mantissa, exponent = candidate.split("e")
                    candidate = mantissa.rstrip("0").rstrip(".") + "e" + exponent if "." in mantissa else candidate
                if "." not in candidate and "e" not in candidate:
                    candidate += "."
                if candidate.startswith("0."):
                    candidate = candidate[1:]
                forms.add((candidate, "scientific" if "e" in candidate else "decimal"))
    elif type(value) in (str, bytes):
        forms.add((repr(value), "string"))
        if isinstance(value, str):
            forms.add((json.dumps(value, ensure_ascii=False), "string"))
    else:
        return []  # bool, None, complex, containers and f-strings are not rewritten
    original = ast.dump(ast.parse(text, mode="eval"), include_attributes=False)
    result = []
    for spelling, family in sorted(forms, key=lambda x: (len(x[0].encode("utf-8")), x[0])):
        try:
            other = ast.literal_eval(spelling)
            same = ast.dump(ast.parse(spelling, mode="eval"), include_attributes=False) == original
            if isinstance(value, float):
                same = same and struct.pack("!d", value) == struct.pack("!d", other)
            if same:
                result.append({"spelling": spelling, "family": family,
                               "proof": {"model": "python3", "kind": type(value).__name__, "ast_equal": True}})
        except (SyntaxError, ValueError, TypeError):
            pass
    return result


def _choose(candidates: list[dict], original: str, policy: str) -> dict | None:
    if not candidates:
        return None
    ordered = sorted(candidates, key=lambda c: (len(c["spelling"].encode("utf-8")), c["spelling"]))
    if policy != "shortest":
        preferred = [c for c in ordered if c["family"] == policy]
        if preferred:
            return preferred[0]
    candidate = ordered[0]
    return candidate if len(candidate["spelling"]) < len(original) else None


_ALT = {"<:": "[", ":>": "]", "<%": "{", "%>": "}"}
_CPP_ALT = {"and": "&&", "or": "||", "not": "!", "bitand": "&", "bitor": "|",
            "xor": "^", "compl": "~", "and_eq": "&=", "or_eq": "|=", "xor_eq": "^=", "not_eq": "!="}


def _significant(tokens: list[Token]) -> list[tuple[str, str]]:
    return [(t.kind, t.text) for t in tokens if t.kind not in ("space", "comment")]


def _compact_c_like(source: str, language: str) -> tuple[str, str | None]:
    tokens = _lex(source, language)
    protected = _protected_tokens(tokens, language)
    out = []
    prev: list[Token] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if i in protected:
            start = i
            while i + 1 < len(tokens) and i + 1 in protected:
                i += 1
            text = source[tokens[start].start:tokens[i].end]
            out.append(text)
            prev = [tokens[i]]
        elif t.kind not in ("space", "comment"):
            if t.kind in ("directive", "doc"):
                if out and not out[-1].endswith("\n"):
                    out.append("\n")
                out.append(t.text)
                if not t.text.endswith("\n"):
                    out.append("\n")
                prev = []
            else:
                if prev:
                    left = "".join(p.text for p in prev[-2:])
                    expected = [(p.kind, p.text) for p in prev[-2:]] + [(t.kind, t.text)]
                    # Prevent phase-1 trigraph creation even when the lexer is C++17.
                    try:
                        joined = _significant(_lex(left + t.text, language))
                    except NotationError:
                        joined = []
                    rust_prefix = language == "rust" and prev[-1].kind == "identifier" and (
                        t.kind == "quoted" or t.text.startswith(("#", "'")))
                    if joined != expected or rust_prefix or left.endswith("?") and t.text.startswith("?"):
                        out.append(" ")
                        prev = []
                out.append(t.text)
                prev = (prev + [t])[-2:]
        i += 1
    candidate = "".join(out)
    try:
        if _significant(_lex(candidate, language)) == _significant(tokens):
            return candidate, None
    except NotationError:
        pass
    return source, "compaction omitted: complete token sequence did not match"


def _rewrite_c_like(source: str, language: str, target: str, policy: str, compact: bool) -> tuple[str, list[dict], list[str]]:
    tokens = _lex(source, language)
    protected = _protected_tokens(tokens, language)
    if any(t.kind not in ("directive", "comment", "quoted") and ("\\\n" in t.text or "\\\r\n" in t.text) for t in tokens) or re.search(r"\?\?[=/\('\)!<>-]", source):
        return source, [], ["line splicing/trigraph input requires compiler preprocessing first"]
    # A standalone backslash outside quoted/directive/comment tokens may be a
    # splice or universal-character escape; the small lexer does not normalize it.
    if any(t.kind == "punct" and t.text == "\\" for t in tokens):
        return source, [], ["unprocessed backslash token: identity retained"]
    out = []
    audit = []
    literal_cache = {}
    for i, token in enumerate(tokens):
        replacement = token.text
        record = None
        if i not in protected:
            if token.kind == "number":
                if token.text not in literal_cache:
                    literal_cache[token.text] = literal_candidates(token.text, language=language, target=target)
                record = _choose(literal_cache[token.text], token.text, policy)
                if record:
                    replacement = record["spelling"]
            elif token.kind == "punct" and language in ("c", "cpp") and token.text in _ALT:
                replacement = _ALT[token.text]
                record = {"proof": {"kind": "alternative punctuator"}}
            elif token.kind == "identifier" and language == "cpp" and token.text in _CPP_ALT:
                replacement = _CPP_ALT[token.text]
                record = {"proof": {"kind": "C++ alternative operator token"}}
        if replacement != token.text:
            # Same token type must survive its ORIGINAL neighbors too. In
            # particular, 0xe immediately followed by '+' is one pp-number.
            neighbors = tokens[max(0, i - 1):i] + [Token(token.kind, replacement, 0, 0)] + tokens[i + 1:i + 2]
            candidate_text = "".join(t.text for t in neighbors)
            try:
                check = _lex(candidate_text, language)
                expected = [(t.kind, t.text) for t in neighbors if t.kind not in ("space", "comment")]
                if record and record["proof"].get("kind", "").startswith(("alternative", "C++")):
                    expected = [("punct" if text == replacement else kind, text) for kind, text in expected]
                if _significant(check) != expected:
                    replacement, record = token.text, None
            except NotationError:
                replacement, record = token.text, None
        out.append(replacement)
        if replacement != token.text and record:
            audit.append({"start_byte": token.start, "end_byte": token.end,
                          "before": token.text, "after": replacement, "proof": record["proof"]})
    output = "".join(out)
    notes = []
    if compact:
        output, note = _compact_c_like(output, language)
        if note:
            notes.append(note)
        elif output != "".join(out):
            audit.append({"operation": "comments and whitespace", "proof": {"same_token_sequence": True,
                          "contract": "source/token spelling and locations unobserved"}})
    return output, audit, notes


def _python_offsets(text: str) -> list[int]:
    # tokenize's readline counts physical LF lines. str.splitlines() also
    # splits form-feed and Unicode separators, including inside string tokens.
    return [0] + [match.end() for match in re.finditer("\n", text)]


def _python_comment_is_protected(token: tokenize.TokenInfo) -> bool:
    return token.type == tokenize.COMMENT and (
        token.start == (1, 0) and token.string.startswith("#!")
        or token.start[0] <= 2 and re.search(r"coding[=:]\s*[-\w.]+", token.string) is not None)


def _python_token_signature(tokens) -> list[tuple[int, str]]:
    return [(token.type, token.string) for token in tokens
            if token.type not in (tokenize.ENCODING, tokenize.ENDMARKER)
            and (token.type != tokenize.COMMENT or _python_comment_is_protected(token))
            # The tokenizer inserts an empty virtual newline at some EOFs.
            # Real NL/NEWLINE spellings and all indentation remain exact.
            and (token.type not in (tokenize.NL, tokenize.NEWLINE) or token.string)]


def _python_tokens_join(left: tokenize.TokenInfo, right: tokenize.TokenInfo) -> bool:
    """Check the lexical boundary, including number attributes/string prefixes.

    An isolated delimiter such as '(' can cause EOF-in-multiline-statement
    after yielding every token. The complete program is checked again below;
    a missing or changed string/number token never matches this local check.
    """
    # tokenize can split `1if` into NUMBER+NAME even though the parser emits
    # "invalid decimal literal" SyntaxWarning (and -Werror rejects it).
    # Keep the boundary for every number/name pair, not individual keywords.
    if left.type == tokenize.NUMBER and right.type == tokenize.NAME:
        return False
    observed = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(left.string + right.string).readline):
            if token.type not in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL,
                                  tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                observed.append((token.type, token.string))
    except (SyntaxError, tokenize.TokenError):
        pass
    return observed == [(left.type, left.string), (right.type, right.string)]


def _compact_python(text: str) -> tuple[str, dict | None, str | None]:
    """Delete only source trivia; never reserialize the token stream.

    Keep every physical newline, indentation prefix, explicit line splice and
    retained token spelling. Only ordinary comments and inline horizontal
    gaps can shrink. A full token/AST comparison is the final acceptance gate.
    """
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    offsets = _python_offsets(text)

    def position(pair):
        row, column = pair
        # Virtual NEWLINE/ENDMARKER positions may be just past the source.
        return min(len(text), offsets[row - 1] + column) if 0 < row <= len(offsets) else len(text)

    pieces = []
    cursor = 0
    previous = None
    joins = {}
    removed_comments = 0
    shortened_gaps = 0
    for token in tokens:
        start, end = position(token.start), position(token.end)
        gap = text[cursor:start]
        leading = previous is None or previous.end[0] < token.start[0] or previous.type == tokenize.INDENT
        if gap and not leading and all(char in " \t\f" for char in gap):
            if token.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER):
                replacement = ""
            else:
                key = (previous.type, previous.string, token.type, token.string)
                if key not in joins:
                    joins[key] = _python_tokens_join(previous, token)
                replacement = "" if joins[key] else " "
            if len(replacement) < len(gap):
                gap = replacement
                shortened_gaps += 1
        pieces.append(gap)
        if token.type == tokenize.COMMENT and not _python_comment_is_protected(token):
            removed_comments += 1
        else:
            pieces.append(text[start:end])
        cursor = end
        previous = token
    pieces.append(text[cursor:])
    candidate = "".join(pieces)
    if candidate == text:
        return text, None, None
    try:
        other = list(tokenize.generate_tokens(io.StringIO(candidate).readline))
        same_tokens = _python_token_signature(tokens) == _python_token_signature(other)
        same_tree = ast.dump(ast.parse(text), include_attributes=False) == ast.dump(
            ast.parse(candidate), include_attributes=False)
    except (SyntaxError, tokenize.TokenError):
        same_tokens = same_tree = False
    if not same_tokens or not same_tree:
        return text, None, "Python compaction omitted: complete token sequence or AST did not match"
    return candidate, {"operation": "source-position comments/whitespace",
                       "removed_comments": removed_comments,
                       "shortened_horizontal_gaps": shortened_gaps,
                       "proof": {"same_token_sequence": True, "whole_program_ast_equal": True,
                                 "preserved": ["shebang", "encoding cookie", "indentation", "line endings"],
                                 "contract": "source/token spelling and locations unobserved"}}, None


def _rewrite_python(source: bytes, policy: str, compact: bool) -> tuple[bytes, list[dict], list[str]]:
    try:
        # detect_encoding retains utf-8-sig for BOM round-tripping; the emitted
        # ENCODING token normalizes that spelling to utf-8 and loses the BOM.
        encoding = tokenize.detect_encoding(io.BytesIO(source).readline)[0]
        text = source.decode(encoding)
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        tree = ast.dump(ast.parse(text), include_attributes=False)
    except (SyntaxError, UnicodeError, tokenize.TokenError) as e:
        raise NotationError(f"Python parse failed: {e}") from e
    offsets = _python_offsets(text)
    changes = []
    audit = []
    notes = []
    literal_cache = {}
    for t in tokens:
        spelling = t.string
        if t.type in (tokenize.NUMBER, tokenize.STRING):
            if spelling not in literal_cache:
                candidates = literal_candidates(spelling, language="python")
                encodable = []
                for candidate in candidates:
                    try:
                        candidate["spelling"].encode(encoding)
                        encodable.append(candidate)
                    except UnicodeError:
                        pass
                literal_cache[spelling] = encodable
            record = _choose(literal_cache[spelling], spelling, policy)
            if record and spelling != record["spelling"]:
                spelling = record["spelling"]
                start = offsets[t.start[0] - 1] + t.start[1]
                end = offsets[t.end[0] - 1] + t.end[1]
                changes.append((start, end, spelling))
                audit.append({"start": list(t.start), "end": list(t.end), "before": t.string,
                              "after": spelling, "proof": record["proof"]})
    for start, end, spelling in reversed(changes):
        text = text[:start] + spelling + text[end:]
    if compact:
        before = len(text.encode(encoding))
        text, record, note = _compact_python(text)
        if record:
            record["source_bytes_saved"] = before - len(text.encode(encoding))
            audit.append(record)
        if note:
            notes.append(note)
    output = text.encode(encoding)
    try:
        same = ast.dump(ast.parse(output.decode(encoding)), include_attributes=False) == tree
    except (SyntaxError, UnicodeError):
        same = False
    if not same:
        raise NotationError("Python transformed whole-program AST did not match")
    return output, audit, notes


def generate_variants(source: bytes, *, language: str, target: str | None = None,
                      compact: bool = False, token_contract: str = "opaque",
                      max_variants: int = 16) -> list[dict]:
    """Return bounded deterministic recipe variants. No exponential token product.

    Same-byte variants deliberately retain recipe IDs. Callers may deduplicate
    by bytes/hash, but must retain provenance. `opaque` returns identity only.
    """
    language = {"c++": "cpp", "py": "python"}.get(language, language)
    target = target or DEFAULT_TARGET.get(language)
    if language not in TARGETS or target not in TARGETS[language]:
        raise NotationError("unsupported language/target pair")
    if not isinstance(source, bytes) or len(source) > MAX_SOURCE:
        raise NotationError(f"source must be bytes of at most {MAX_SOURCE} bytes")
    if token_contract not in ("opaque", "no-token-observation", "preprocessed"):
        raise NotationError("unknown token contract")
    if token_contract == "preprocessed" and language not in ("c", "cpp"):
        raise NotationError("preprocessed contract is C/C++ only")
    if type(compact) is not bool or type(max_variants) is not int or not 1 <= max_variants <= 32:
        raise NotationError("compact must be bool; max_variants must be 1..32")
    contract = {"language": language, "target": target, "token_contract": token_contract,
                "compact": compact, "source_sha256": hashlib.sha256(source).hexdigest(),
                "required_acceptance": "compile plus program verification; prefer identical native bytes for spelling-only changes"}
    def make(identifier: str, data: bytes, audit: list[dict], notes: list[str]) -> dict:
        return {"id": identifier, "data": data, "source_bytes": len(source), "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(), "audit": audit, "notes": notes,
                "contract": contract, "size_claim": "source bytes only, not final compressed-file optimum"}
    result = [make("raw", source, [], [])]
    if token_contract == "opaque":
        result[0]["notes"].append("no rewriting without an explicit source/token non-observation contract")
        return result
    recipes = [("shortest", "shortest", False)]
    if compact:
        recipes += [("shortest-compact", "shortest", True)]
    recipes += [(policy, policy, False) for policy in POLICIES[1:]]
    if compact:
        recipes += [(policy + "-compact", policy, True) for policy in POLICIES[1:]]
    for identifier, policy, compact_this in recipes[:max_variants - 1]:
        if language == "python":
            data, audit, notes = _rewrite_python(source, policy, compact_this)
        else:
            text, audit, notes = _rewrite_c_like(source.decode("latin-1"), language, target, policy, compact_this)
            data = text.encode("latin-1")
        result.append(make(identifier, data, audit, notes))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--language", required=True, choices=("c", "cpp", "c++", "rust", "python", "py"))
    parser.add_argument("--target")
    parser.add_argument("--token-contract", choices=("opaque", "no-token-observation", "preprocessed"), default="opaque")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--max-variants", type=int, default=16)
    parser.add_argument("--variant", default="shortest")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--portfolio", type=Path)
    parser.add_argument("--list-variants", action="store_true")
    args = parser.parse_args(argv)
    try:
        variants = generate_variants(args.input.read_bytes(), language=args.language, target=args.target,
                                     compact=args.compact, token_contract=args.token_contract,
                                     max_variants=args.max_variants)
        metadata = [{k: v for k, v in item.items() if k != "data"} for item in variants]
        if args.list_variants:
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
        if args.portfolio:
            args.portfolio.mkdir(parents=True, exist_ok=False)
            for item in variants:
                (args.portfolio / (item["id"] + args.input.suffix)).write_bytes(item["data"])
            (args.portfolio / "audit.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.output:
            if args.output.resolve() == args.input.resolve():
                raise NotationError("output must not overwrite source")
            selected = next((v for v in variants if v["id"] == args.variant), None)
            if selected is None:
                raise NotationError(f"variant {args.variant!r} unavailable; available: {[v['id'] for v in variants]}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("xb") as f:
                f.write(selected["data"])
            if args.audit:
                with args.audit.open("x", encoding="utf-8") as f:
                    json.dump({k: v for k, v in selected.items() if k != "data"}, f, ensure_ascii=False, indent=2)
                    f.write("\n")
        if not (args.output or args.portfolio or args.list_variants):
            parser.error("choose --output, --portfolio or --list-variants")
    except (NotationError, OSError) as e:
        print(f"nvnotation: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
