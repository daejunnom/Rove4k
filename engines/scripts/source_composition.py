"""Assemble readable C from explicit, shared source fragments before transforms.

The template is canonical source, not a generated duplicate. Its deliberately
unresolvable ``rove-common`` includes require this assembly step before the C
preprocessor. Fragments supply text only: no runtime dispatch, declarations,
feature flags or whitespace are inserted by the assembler.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
from typing import Mapping


_INCLUDE = re.compile(rb'^#include "rove-common/([a-z][a-z0-9_]*)/([a-z][a-z0-9_]*)"$', re.M)
_SECTION = re.compile(rb'^/\* rove:begin ([a-z][a-z0-9_]*) \*/\n(.*?)\n/\* rove:end \1 \*/$', re.M | re.S)
_PATH = re.compile(r"engines/common/[a-z][a-z0-9_]*\.c\Z")


def _normalized(data: bytes) -> bytes:
    data = data.replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ValueError("lone CR in composition source")
    return data


def _includes(source: bytes):
    if b"\r" in source:
        raise ValueError("composition requires LF-normalized source")
    matches = tuple(_INCLUDE.finditer(source))
    if source.count(b"rove-common/") != len(matches):
        raise ValueError("malformed shared source include")
    return matches


def dependencies(source: bytes) -> tuple[str, ...]:
    """Return the exact repository-relative C input set named by a template."""
    return tuple(sorted({"engines/common/" + m[1].decode() + ".c" for m in _includes(source)}))


def fragments(data: bytes) -> dict[str, bytes]:
    """Read framed bodies without including their framing newlines/comments."""
    if b"\r" in data:
        raise ValueError("composition requires LF-normalized fragments")
    matches = tuple(_SECTION.finditer(data))
    if (data.count(b"/* rove:begin ") != len(matches)
            or data.count(b"/* rove:end ") != len(matches)):
        raise ValueError("malformed or nested shared source fragment")
    result = {}
    for match in matches:
        name, body = match[1].decode(), match[2]
        if name in result:
            raise ValueError("duplicate shared source fragment: " + name)
        if not body or b"rove-common/" in body:
            raise ValueError("empty or recursive shared source fragment: " + name)
        result[name] = body
    return result


def assemble(source: bytes, shared: Mapping[str, bytes], *, expected_sha256: str | None = None) -> bytes:
    """Expand only the supplied closure; never read additional files implicitly."""
    required = dependencies(source)
    if set(shared) != set(required):
        raise ValueError("shared source inputs must exactly cover the template dependencies")
    units = {path: fragments(shared[path]) for path in required}

    def replace(match):
        path = "engines/common/" + match[1].decode() + ".c"
        name = match[2].decode()
        try:
            return units[path][name]
        except KeyError:
            raise ValueError("missing shared source fragment: " + path + ":" + name) from None

    result = _INCLUDE.sub(replace, source)
    if expected_sha256 is not None and sha256(result).hexdigest() != expected_sha256:
        raise ValueError("assembled canonical source differs from recipe")
    return result


def read_shared(root: Path, expected: Mapping[str, str]) -> tuple[dict[str, bytes], dict]:
    """Read and admit explicit shared C inputs; they remain engine source roles."""
    contents, records = {}, {}
    for logical, digest in expected.items():
        if not _PATH.fullmatch(logical):
            raise ValueError("invalid shared source path: " + logical)
        path = root / logical
        if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
            raise ValueError("shared source must be a regular file without symlink parents: " + logical)
        raw = path.read_bytes()
        data = _normalized(raw)
        actual = sha256(data).hexdigest()
        if actual != digest:
            raise ValueError("shared source input differs from recipe: " + logical)
        contents[logical] = data
        records[logical] = {"bytes": len(data), "sha256": actual,
                            "working_bytes_sha256": sha256(raw).hexdigest(), "LF_normalization": raw != data}
    return contents, records


def freeze_shared(root: Path, destination: Path, expected: Mapping[str, str]) -> tuple[dict[str, bytes], dict]:
    """Freeze admitted shared inputs and assemble from that frozen snapshot."""
    contents, records = read_shared(root, expected)
    frozen = {}
    for logical, data in contents.items():
        path = destination / logical
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        frozen[logical] = path.read_bytes()
    return frozen, records


def read_source(root: Path, logical: str) -> bytes:
    """Compose a readable source for development consumers, without recipe admission.

    Production builders use ``read_shared``/``freeze_shared`` and the recipe's
    assembled digest. This convenience entry point makes direct source readers
    explicit about composition instead of relying on a generated monolith.
    """
    source = _normalized((root / logical).read_bytes())
    shared = {name: _normalized((root / name).read_bytes()) for name in dependencies(source)}
    return assemble(source, shared)
