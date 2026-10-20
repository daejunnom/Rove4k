"""Byte-exact C source literal alternatives for a frozen Python bootstrap.

This module changes representation only. It neither rewrites C identifiers nor
executes a bootstrap or compiler. Every returned expression evaluates to bytes.
"""
import ast
import re


def _source(source):
    if not isinstance(source, bytes):
        raise TypeError("source must be bytes")


def _raw(source, quote):
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return None
    trailing = len(text) - len(text.rstrip("\\"))
    if "\r" in text or "\0" in text or trailing % 2 or quote in text or text.endswith(quote[0]):
        return None
    return "r" + quote + text + quote + ".encode()"


def canonical_literal(source):
    """The producer's default raw-single/raw-double/bytes-repr selection."""
    _source(source)
    for quote in ("'''", '"""'):
        expression = _raw(source, quote)
        if expression is not None:
            return expression
    return repr(source)


def _ascii_triple(source, quote):
    body = []
    for byte in source:
        if byte == 92:
            body.append("\\\\")
        elif byte == ord(quote[0]):
            body.append("\\" + chr(byte))
        elif byte in (9, 10):
            body.append(chr(byte))
        elif byte == 13:
            body.append("\\r")
        elif 32 <= byte <= 126:
            body.append(chr(byte))
        else:
            body.append("\\x%02x" % byte)
    return "b" + quote + "".join(body) + quote


def _value(expression):
    if not isinstance(expression, str):
        raise TypeError("literal expression must be a string")
    try:
        node = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as error:
        raise ValueError("invalid literal expression") from error
    body = node.body
    constant = isinstance(body, ast.Constant) and isinstance(body.value, bytes)
    encoded = (isinstance(body, ast.Call) and not body.args and not body.keywords
               and isinstance(body.func, ast.Attribute) and body.func.attr == "encode"
               and isinstance(body.func.value, ast.Constant) and isinstance(body.func.value.value, str))
    if not (constant or encoded):
        raise ValueError("only a bytes literal or string literal .encode() is permitted")
    try:
        value = eval(compile(node, "<tiny-encoding-literal>", "eval"), {"__builtins__": {}})
    except (UnicodeError, ValueError) as error:
        raise ValueError("literal does not encode as UTF-8 bytes") from error
    if not isinstance(value, bytes):
        raise ValueError("literal must evaluate to bytes")
    return value


def variants(source):
    """Return name -> expression, omitting raw/UTF-8 forms that cannot be exact."""
    _source(source)
    result = {"canonical": canonical_literal(source)}
    for name, quote in (("raw-single", "'''"), ("raw-double", '"""')):
        expression = _raw(source, quote)
        if expression is not None:
            result[name] = expression
    result["bytes-repr"] = repr(source)
    result["bytes-triple-single"] = _ascii_triple(source, "'''")
    result["bytes-triple-double"] = _ascii_triple(source, '"""')
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        result["str-repr-utf8"] = repr(text) + ".encode()"
    for name, expression in result.items():
        if _value(expression) != source:
            raise ValueError("non-exact generated literal: " + name)
    return result


def replace_literal(script, source, expression):
    """Replace exactly one canonical p.communicate argument using AST spans.

    Matching strings or comments are ignored. Coordinates are UTF-8 byte
    offsets, preserving every byte outside the selected argument expression.
    """
    _source(source)
    if not isinstance(script, bytes):
        raise TypeError("script must be bytes")
    if _value(expression) != source:
        raise ValueError("replacement expression changes source bytes")
    try:
        text = script.decode("utf-8")
        tree = ast.parse(text)
    except (UnicodeError, SyntaxError, ValueError) as error:
        raise ValueError("bootstrap must be valid UTF-8 Python") from error
    canonical = canonical_literal(source)
    matches = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and len(node.args) == 1 and not node.keywords
                and isinstance(node.func, ast.Attribute) and node.func.attr == "communicate"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "p"
                and ast.get_source_segment(text, node.args[0]) == canonical):
            matches.append(node.args[0])
    if len(matches) != 1:
        raise ValueError("expected one canonical p.communicate literal, found %d" % len(matches))
    argument = matches[0]
    starts = [0] + [match.end() for match in re.finditer(rb"\r\n|\r|\n", script)]
    begin = starts[argument.lineno - 1] + argument.col_offset
    end = starts[argument.end_lineno - 1] + argument.end_col_offset
    result = script[:begin] + expression.encode("utf-8") + script[end:]
    try:
        ast.parse(result)
    except (SyntaxError, ValueError) as error:
        raise ValueError("replacement produced invalid Python") from error
    return result
