"""Conservative lexical whitespace/comment compaction, without identifier rewriting.

Preprocessor directives retain their spelling and line boundaries. Rust raw string
delimiters, nested comments and lifetimes are preserved. This is an input recipe,
not a claim of compiler or behavior equivalence; build both forms and validate the
generated engines before choosing a candidate.
"""

import re


_word = re.compile(r"[A-Za-z_$][A-Za-z_0-9$]*")
_number = re.compile(r"(?:[0-9]|\.[0-9])(?:[A-Za-z_0-9.]|[eEpP][+-])*")
_punct = sorted(("<<=", ">>=", "...", "..=", "->", "++", "--", "<<", ">>",
                 "<=", ">=", "==", "!=", "&&", "||", "*=", "/=", "%=", "+=",
                 "-=", "&=", "^=", "|=", "##", "::", "=>", ".."), key=len, reverse=True)


def _quoted(text, start, quote):
    end = start + 1
    while end < len(text):
        if text[end] == "\\":
            end += 2
        elif text[end] == quote:
            return end + 1
        else:
            end += 1
    raise ValueError("unterminated quoted literal")


def _tokens(text, language):
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        if text.startswith("//", pos):
            end = text.find("\n", pos + 2)
            pos = len(text) if end < 0 else end + 1
            continue
        if text.startswith("/*", pos):
            depth, end = 1, pos + 2
            while end < len(text) and depth:
                if language == "rust" and text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
            if depth:
                raise ValueError("unterminated block comment")
            pos = end
            continue
        raw = re.match(r'(?:br|cr|r)(\#{0,255})"', text[pos:]) if language == "rust" else None
        if raw:
            delimiter = '"' + raw.group(1)
            end = text.find(delimiter, pos + raw.end())
            if end < 0:
                raise ValueError("unterminated raw string")
            end += len(delimiter)
        else:
            prefix = re.match(r'(?:u8|[uULbc])?(["\'])', text[pos:])
            if prefix:
                literal_start = pos + prefix.end() - 1
                # Rust 'name and 'static are lifetimes, rather than character literals.
                lifetime = re.match(r"'[A-Za-z_][A-Za-z_0-9]*", text[pos:]) if language == "rust" else None
                if lifetime and not text.startswith("'", pos + lifetime.end()):
                    end = pos + lifetime.end()
                else:
                    end = _quoted(text, literal_start, prefix.group(1))
            else:
                match = _word.match(text, pos) or _number.match(text, pos)
                if match:
                    end = match.end()
                else:
                    punct = next((item for item in _punct if text.startswith(item, pos)), None)
                    end = pos + len(punct) if punct else pos + 1
        yield text[pos:end]
        pos = end


def _compact_chunk(text, language):
    tokens = list(_tokens(text, language))
    result = []
    previous = ""
    for token in tokens:
        try:
            joined = list(_tokens(previous + token, language)) if previous else []
        except ValueError:
            joined = []
        literal_suffix = (previous.endswith(('"', "'")) or
                          re.match(r'^(?:br|cr|r)#+"', previous)) and re.match(r"[A-Za-z_]", token)
        # Rust rejects '<-' as a legacy token even though its characters have
        # separate meanings in comparisons with a negative operand.
        reserved_joint = previous == "<" and token == "-"
        if previous and (joined != [previous, token] or literal_suffix or reserved_joint):
            result.append(" ")
        result.append(token)
        previous = token
    return "".join(result)


def compact_source(data, language):
    text = data.decode("utf-8")
    if language not in ("c", "rust"):
        raise ValueError("only C and Rust source compaction is supported")
    if language == "rust":
        # Attributes contain '#', but unlike C are ordinary language tokens.
        return (_compact_chunk(text, language) + "\n").encode()
    # C translation phase 2 splices escaped newlines before comment recognition.
    # Strip comments first so a line beginning '#' inside a block comment cannot
    # accidentally become a retained preprocessor directive.
    text = text.replace("\\\r\n", "").replace("\\\n", "")
    clean, pos = [], 0
    while pos < len(text):
        if text[pos] in "\"'":
            end = _quoted(text, pos, text[pos])
            clean.append(text[pos:end])
            pos = end
        elif text.startswith("//", pos):
            end = text.find("\n", pos + 2)
            pos = len(text) if end < 0 else end
            clean.append(" ")
        elif text.startswith("/*", pos):
            end = text.find("*/", pos + 2)
            if end < 0:
                raise ValueError("unterminated block comment")
            clean.append(" " + "\n" * text[pos:end + 2].count("\n"))
            pos = end + 2
        else:
            clean.append(text[pos])
            pos += 1
    text = "".join(clean)
    output, chunk = [], []
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("#"):
            if chunk:
                output.append(_compact_chunk("".join(chunk), language) + "\n")
                chunk.clear()
            directive = line.lstrip()
            while directive.rstrip("\r\n").endswith("\\"):
                index += 1
                if index >= len(lines):
                    raise ValueError("unterminated preprocessor continuation")
                directive += lines[index]
            output.append(directive.rstrip("\r\n") + "\n")
        else:
            chunk.append(line)
        index += 1
    if chunk:
        output.append(_compact_chunk("".join(chunk), language) + "\n")
    return "".join(output).encode()
