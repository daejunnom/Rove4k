"""Pure lexical helpers for the Rust 2021/2024 source specializer.

Literals and documentation comments are opaque strings. Ordinary comments and
whitespace are discarded. ``render`` keeps the resulting Rust token spellings,
not source locations or formatting observed by ``stringify!``/procedural macros.
In particular, the list[str] interface does not model proc_macro Punct spacing.
This is a lexer, not a Rust grammar or literal-validity checker. Identifier
recognition uses the host Python Unicode XID tables; shipping inputs are ASCII.
"""

from functools import lru_cache


_OPERATORS = (
    "...", "..=", "<<=", ">>=", "!=", "%=", "&&", "&=", "*=", "+=",
    "-=", "->", "..", "/=", "::", "<-", "<<", "<=", "==", "=>", ">=",
    ">>", "^=", "|=", "||",
)
_OPEN = {"(": ")", "[": "]", "{": "}"}
_CLOSE = {value: key for key, value in _OPEN.items()}
_WHITESPACE = "\t\n\v\f\r \u0085\u200e\u200f\u2028\u2029"


def _ident_start(char):
    return bool(char) and (char == "_" or char.isidentifier())


def _ident_continue(char):
    return bool(char) and ("a" + char).isidentifier()


def _identifier_end(source, pos):
    if pos >= len(source) or not _ident_start(source[pos]):
        return pos
    pos += 1
    while pos < len(source) and _ident_continue(source[pos]):
        pos += 1
    return pos


def _quoted_end(source, start, quote):
    pos = start + 1
    while pos < len(source):
        if source[pos] == "\\":
            pos += 2
        elif source[pos] == quote:
            return pos + 1
        else:
            pos += 1
    raise ValueError(f"unterminated {quote} literal at offset {start}")


def _raw_end(source, start):
    """Return a raw string's end, or None if this is not a raw prefix."""
    prefix = next((p for p in ("br", "cr", "r") if source.startswith(p, start)), None)
    if prefix is None:
        return None
    pos = start + len(prefix)
    while pos < len(source) and source[pos] == "#":
        pos += 1
    if pos == len(source) or source[pos] != '"':
        return None
    hashes = pos - start - len(prefix)
    if hashes > 255:
        raise ValueError(f"raw string has more than 255 hashes at offset {start}")
    delimiter = '"' + "#" * hashes
    end = source.find(delimiter, pos + 1)
    if end < 0:
        raise ValueError(f"unterminated raw string at offset {start}")
    return end + len(delimiter)


def _number_end(source, start):
    """Consume a numeric token without swallowing range/field punctuation."""
    pos, length = start, len(source)
    radix = source[start:start + 2]
    if radix in ("0b", "0o", "0x"):
        pos += 2
        digits = "0123456789abcdefABCDEF_" if radix == "0x" else "0123456789_"
        while pos < length and source[pos] in digits:
            pos += 1
        return _identifier_end(source, pos)
    while pos < length and source[pos] in "0123456789_":
        pos += 1
    if pos < length and source[pos] == ".":
        following = source[pos + 1:pos + 2]
        # 1..=2 and 1.method() start with an integer, unlike 1. or 1.25.
        if following != "." and not _ident_start(following):
            pos += 1
            if pos == length or source[pos] not in "0123456789":
                return pos  # A float ending with '.' cannot take a suffix.
            while pos < length and source[pos] in "0123456789_":
                pos += 1
    if pos < length and source[pos] in "eE":
        pos += 1
        if pos < length and source[pos] in "+-":
            pos += 1
        while pos < length and source[pos] in "0123456789_":
            pos += 1
    return _identifier_end(source, pos)


def _doc_comment(source, start):
    return source.startswith(("//!", "/*!"), start) or (
        source.startswith("///", start) and not source.startswith("////", start)
    ) or (
        source.startswith("/**", start)
        and not source.startswith(("/***", "/**/"), start)
    )


def _block_end(source, start):
    end, depth = start + 2, 1
    while end < len(source) and depth:
        if source.startswith("/*", end):
            depth += 1
            end += 2
        elif source.startswith("*/", end):
            depth -= 1
            end += 2
        else:
            end += 1
    if depth:
        raise ValueError(f"unterminated block comment at offset {start}")
    return end


def _inner_attribute(source, start):
    # rustc distinguishes a shebang from #! /* ordinary trivia */ [attribute]
    # by looking for the next non-trivia token, including across newlines.
    pos = start + 2
    while pos < len(source):
        if source[pos] in _WHITESPACE:
            pos += 1
        elif _doc_comment(source, pos):
            return False
        elif source.startswith("//", pos):
            end = source.find("\n", pos + 2)
            pos = len(source) if end < 0 else end
        elif source.startswith("/*", pos):
            try:
                pos = _block_end(source, pos)
            except ValueError:
                return False
        else:
            return source[pos] == "["
    return False


def tokenize(source: str) -> list[str]:
    """Split source into Rust token spellings, retaining doc comments/shebang.

    Ordinary comments may nest. Delimiters inside literals/comments are opaque.
    Unclosed comments and quoted/raw literals raise ValueError. As with a lexer,
    semantic errors such as invalid numeric suffixes are left to rustc.
    """
    # Match rustc's one-pass input normalization, including inside literals.
    source = source.replace("\r\n", "\n")
    result, pos, length = [], 0, len(source)
    if source.startswith("\ufeff"):
        pos = 1  # Rust ignores an initial UTF-8 BOM.
    if source.startswith("#!", pos) and not _inner_attribute(source, pos):
        end = source.find("\n", pos)
        end = length if end < 0 else end
        result.append(source[pos:end])
        pos = end
    while pos < length:
        char = source[pos]
        if char in _WHITESPACE:
            pos += 1
            continue
        if source.startswith("//", pos):
            end = source.find("\n", pos + 2)
            end = length if end < 0 else end
            if _doc_comment(source, pos):
                result.append(source[pos:end])
            pos = end
            continue
        if source.startswith("/*", pos):
            end = _block_end(source, pos)
            if _doc_comment(source, pos):
                result.append(source[pos:end])
            pos = end
            continue

        end = _raw_end(source, pos)
        if end is not None:
            end = _identifier_end(source, end)
        elif char == '"':
            end = _identifier_end(source, _quoted_end(source, pos, '"'))
        elif source.startswith(('b"', 'c"', "b'"), pos):
            end = _identifier_end(source, _quoted_end(source, pos + 1, source[pos + 1]))
        elif char == "'":
            name = pos + 3 if source.startswith("'r#", pos) else pos + 1
            lifetime_end = _identifier_end(source, name)
            if lifetime_end > name and (lifetime_end == length or source[lifetime_end] != "'"):
                end = lifetime_end
            else:
                end = _identifier_end(source, _quoted_end(source, pos, "'"))
        elif source.startswith("r#", pos) and pos + 2 < length and _ident_start(source[pos + 2]):
            end = _identifier_end(source, pos + 2)
        elif _ident_start(char):
            end = _identifier_end(source, pos)
        elif char in "0123456789":
            end = _number_end(source, pos)
        else:
            operator = next((item for item in _OPERATORS if source.startswith(item, pos)), char)
            end = pos + len(operator)
        result.append(source[pos:end])
        pos = end
    return result


def _line_token(token):
    return token.startswith(("//", "#!")) and not token.startswith("#![")


def _identifier(token):
    return bool(token) and _ident_start(token[0]) and _identifier_end(token, 0) == len(token)


@lru_cache(maxsize=8192)
def _space_between(left, right):
    # These are lexer errors in current editions, even where naive independent
    # token recognition would still return the same two spellings.
    if left == "#" and (right == "#" or right.startswith('"')):
        return True
    if (_identifier(left) or (left.startswith("'") and not left.endswith("'"))) and right.startswith(("#", "'", '"')):
        return True
    if left in ("r", "br", "cr", "'r") and right == "#":
        return True
    try:
        return tokenize(left + right) != [left, right]
    except ValueError:
        # For example, '/' + '*' would open a comment, or a literal would be
        # interpreted as a different raw-prefix/character construction.
        return True


def render(tokens: list[str]) -> str:
    """Join tokens with only separators needed for their Rust token spellings.

    Input is the output of tokenize or complete replacement tokens. Empty
    replacements are ignored. A line documentation comment or shebang retains
    its newline so it cannot consume the following item.
    """
    result, previous = [], ""
    for token in tokens:
        if not token:
            continue
        if previous:
            if _line_token(previous):
                result.append("\n")
            elif _space_between(previous, token):
                result.append(" ")
        result.append(token)
        previous = token
    if previous and _line_token(previous):
        result.append("\n")
    return "".join(result)


def matching(tokens: list[str], index: int) -> int:
    """Return the matching (), [] or {} delimiter index in either direction.

    A mismatched/unclosed group or non-delimiter input raises ValueError; an
    index outside the token list raises IndexError. This intentionally does not
    match '<': Rust generics and comparisons require syntactic context.
    """
    if index < 0 or index >= len(tokens):
        raise IndexError(index)
    token = tokens[index]
    if token in _OPEN:
        step, opening, closing = 1, _OPEN, _CLOSE
    elif token in _CLOSE:
        step, opening, closing = -1, _CLOSE, _OPEN
    else:
        raise ValueError(f"token at index {index} is not a delimiter: {token!r}")
    stack = [token]
    pos = index + step
    while 0 <= pos < len(tokens):
        token = tokens[pos]
        if token in opening:
            stack.append(token)
        elif token in closing:
            if not stack or opening[stack[-1]] != token:
                raise ValueError(f"mismatched delimiter at index {pos}: {token!r}")
            stack.pop()
            if not stack:
                return pos
        pos += step
    raise ValueError(f"unclosed delimiter at index {index}: {tokens[index]!r}")
