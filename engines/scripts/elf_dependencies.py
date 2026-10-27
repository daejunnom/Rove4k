"""Bounded ELF64 dependency DATA and the documented TCEC 4K ELF allowlist.

This does not load an ELF, run ldd, resolve a library, inspect the environment,
or qualify size/startup/UCI. Callers bind the returned input identity to their
actual artifact. Dynamic tag constants follow glibc-2.39 elf/elf.h.
"""
from __future__ import annotations

from fnmatch import fnmatchcase
from hashlib import sha256
import struct


FORMAT = "rove4k-elf-dependencies-v1"
RULE_URL = "https://wiki.chessdom.org/TCEC_4k_Rules#8._4K_ELF_specific_rules"
CONSTANTS_URL = "https://github.com/bminor/glibc/blob/glibc-2.39/elf/elf.h"
MAX_INPUT = 16 << 20
MAX_PHDRS = 1024
MAX_DYNAMIC = 4096
MAX_STRTAB = 1 << 20
MAX_NAME = 4096
LOAD_PAGE_BYTES = 4096
ADDRESS_END = 1 << 64
PT_LOAD, PT_DYNAMIC, PT_INTERP, PT_TLS = 1, 2, 3, 7
DT_NULL, DT_NEEDED, DT_STRTAB, DT_STRSZ = 0, 1, 5, 10
DT_SONAME, DT_RPATH, DT_RUNPATH = 14, 15, 29
LOADER_FEATURES = {
    0x6FFFFEF9: "DT_GNU_LIBLIST",
    0x6FFFFEFA: "DT_CONFIG",
    0x6FFFFEFB: "DT_DEPAUDIT",
    0x6FFFFEFC: "DT_AUDIT",
    0x7FFFFFFD: "DT_AUXILIARY",
    0x7FFFFFFF: "DT_FILTER",
}
# Standard/known GNU relocation, symbol, version and state tags. Unknown tags
# are reported, not interpreted as proof that no other DSO can be loaded.
KNOWN_DYNAMIC_TAGS = frozenset(range(31)) | frozenset(range(32, 38)) | frozenset(LOADER_FEATURES) | frozenset((
    0x6FFFFDF5, 0x6FFFFDF6, 0x6FFFFDF7, 0x6FFFFDF8, 0x6FFFFDF9,
    0x6FFFFDFA, 0x6FFFFDFB, 0x6FFFFDFC, 0x6FFFFDFD, 0x6FFFFDFE,
    0x6FFFFDFF, 0x6FFFFEF5, 0x6FFFFEF6, 0x6FFFFEF7, 0x6FFFFEF8,
    0x6FFFFEFD, 0x6FFFFEFE, 0x6FFFFEFF, 0x6FFFFFF0,
    0x6FFFFFF9, 0x6FFFFFFA, 0x6FFFFFFB, 0x6FFFFFFC,
    0x6FFFFFFD, 0x6FFFFFFE, 0x6FFFFFFF,
))
LIBRARY_PATHS = {
    "/lib/x86_64-linux-gnu": ("ld-*.so", "libc-*.so", "libc.so*", "libdl-*.so",
        "libdl.so*", "libgcc_s.so*", "libm-*.so", "libm.so*",
        "libpthread-*.so", "libpthread.so*"),
    "/lib64": ("ld-linux-x86-64.so*",),
    "/usr/lib/x86_64-linux-gnu": ("libstdc++.so*",),
}
INTERPRETER_PATHS = {
    "/lib/x86_64-linux-gnu": ("ld-*.so",),
    "/lib64": ("ld-linux-x86-64.so*",),
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_dependencies(data):
    """Inspect one immutable bounded Linux x86-64 ELF; return only DATA.

    Section headers are not needed. This is the current Linux x86-64 4KiB load
    profile; the consumer checks the actual host page size before execution.
    Overlap between page-rounded LOAD memory extents is unsupported, including
    partial/file/BSS aliases. Anonymous extents are never materialized.
    Nonstandard loader features are exposed without following their pointers.
    """
    _require(type(data) is bytes and 64 <= len(data) <= MAX_INPUT,
             "bounded immutable ELF bytes required")
    _require(data[:7] == b"\x7fELF\x02\x01\x01" and data[7] in (0, 3) and data[8] == 0,
             "ELF64 little-endian System V/Linux ABI required")
    kind, machine, version = struct.unpack_from("<HHI", data, 16)
    entry, phoff = struct.unpack_from("<QQ", data, 24)
    ehsize, phsize, phnum = struct.unpack_from("<HHH", data, 52)
    _require(kind in (2, 3) and machine == 62 and version == 1 and ehsize == 64,
             "Linux x86-64 ET_EXEC/ET_DYN required")
    _require(phsize == 56 and 1 <= phnum <= MAX_PHDRS and phoff >= ehsize
             and phoff + phnum * phsize <= len(data), "bounded program headers required")
    headers = [struct.unpack_from("<IIQQQQQQ", data, phoff + index * phsize)
               for index in range(phnum)]
    loads, dynamics, interpreters, tls = [], [], [], []
    for row in headers:
        tag, flags, offset, address, _, filesz, memsz, align = row
        _require(offset + filesz <= len(data) and address + memsz <= ADDRESS_END,
                 "program segment exceeds file/address extent")
        if tag == PT_LOAD:
            _require(filesz <= memsz and (align <= 1 or
                not (align & (align - 1)) and offset % align == address % align),
                "invalid load segment geometry")
            _require(offset % LOAD_PAGE_BYTES == address % LOAD_PAGE_BYTES,
                     "LOAD offset/address disagree at the target page size")
            loads.append(row)
        elif tag == PT_DYNAMIC:
            dynamics.append(row)
        elif tag == PT_INTERP:
            interpreters.append(row)
        elif tag == PT_TLS:
            _require(filesz <= memsz, "TLS file extent exceeds memory extent")
            tls.append(row)
    _require(loads and any(flags & 1 and address <= entry < address + memsz
        for _, flags, _, address, _, _, memsz, _ in loads), "ELF entry outside executable load")
    rounded = sorted((address // LOAD_PAGE_BYTES * LOAD_PAGE_BYTES,
                      (address + memsz + LOAD_PAGE_BYTES - 1) // LOAD_PAGE_BYTES * LOAD_PAGE_BYTES)
                     for _, _, _, address, _, _, memsz, _ in loads if memsz)
    _require(all(left[1] <= right[0] for left, right in zip(rounded, rounded[1:])),
             "overlapping page-rounded LOAD memory extents are unsupported")
    _require(len(dynamics) <= 1 and len(interpreters) <= 1 and len(tls) <= 1,
             "multiple dynamic/interpreter/TLS segments are unsupported")

    def file_mapping(address, size):
        _require(address + size <= ADDRESS_END, "virtual data extent overflows")
        offsets = {offset + address - base for _, _, offset, base, _, filesz, _, _ in loads
                   if base <= address and address + size <= base + filesz}
        _require(len(offsets) == 1, "virtual data lacks one unambiguous file-backed load mapping")
        offset = offsets.pop()
        _require(offset + size <= len(data), "mapped data outside file")
        return offset

    interpreter = None
    if interpreters:
        _, _, offset, _, _, size, _, _ = interpreters[0]
        _require(2 <= size <= MAX_NAME, "bounded absolute interpreter required")
        raw = data[offset:offset + size]
        _require(raw[:1] == b"/" and raw[-1:] == b"\0" and b"\0" not in raw[:-1],
                 "one absolute NUL-terminated interpreter required")
        try:
            interpreter = raw[:-1].decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError("ASCII interpreter required by bounded dependency profile") from error

    rows = []
    if dynamics:
        _, _, offset, address, _, size, memsz, _ = dynamics[0]
        _require(16 <= size <= MAX_DYNAMIC * 16 and size % 16 == 0 and size <= memsz
                 and file_mapping(address, size) == offset, "bounded mapped dynamic segment required")
        terminated = False
        for at in range(offset, offset + size, 16):
            tag, value = struct.unpack_from("<qQ", data, at)
            if tag == DT_NULL:
                terminated = True
                break
            rows.append((tag, value))
        _require(terminated, "dynamic segment has no bounded DT_NULL")
    singles = {}
    for tag, value in rows:
        if tag in (DT_STRTAB, DT_STRSZ, DT_SONAME, DT_RPATH, DT_RUNPATH):
            _require(tag not in singles, "ambiguous repeated dynamic string metadata")
            singles[tag] = value
    string_tags = {DT_NEEDED, DT_SONAME, DT_RPATH, DT_RUNPATH}
    strings = b""
    if DT_STRTAB in singles or DT_STRSZ in singles or any(tag in string_tags for tag, _ in rows):
        _require(DT_STRTAB in singles and DT_STRSZ in singles
                 and 1 <= singles[DT_STRSZ] <= MAX_STRTAB, "bounded complete dynamic string table required")
        offset = file_mapping(singles[DT_STRTAB], singles[DT_STRSZ])
        strings = data[offset:offset + singles[DT_STRSZ]]
        _require(strings[:1] == b"\0", "dynamic string table must begin with NUL")
    cache = {}
    emitted = 0

    def text(offset, *, empty=False):
        nonlocal emitted
        _require(offset < len(strings), "dynamic string offset outside table")
        if offset not in cache:
            end = strings.find(b"\0", offset, min(len(strings), offset + MAX_NAME))
            _require(end >= offset, "dynamic string lacks bounded NUL terminator")
            try:
                value = strings[offset:end].decode("ascii")
            except UnicodeDecodeError as error:
                raise ValueError("ASCII dynamic strings required by bounded dependency profile") from error
            emitted += len(value)
            _require(emitted <= MAX_STRTAB, "aggregate decoded dynamic strings exceed bound")
            cache[offset] = value
        value = cache[offset]
        _require(empty or bool(value), "empty needed library/SONAME is unsupported")
        return value

    needed = [text(value) for tag, value in rows if tag == DT_NEEDED]
    result = {
        "format": FORMAT, "input": {"bytes": len(data), "sha256": sha256(data).hexdigest()},
        "elf_type": "ET_EXEC" if kind == 2 else "ET_DYN", "interpreter": interpreter,
        "load_page_bytes": LOAD_PAGE_BYTES,
        "has_dynamic": bool(dynamics), "has_tls": bool(tls), "needed": needed,
        "soname": text(singles[DT_SONAME]) if DT_SONAME in singles else None,
        "rpath": text(singles[DT_RPATH], empty=True) if DT_RPATH in singles else None,
        "runpath": text(singles[DT_RUNPATH], empty=True) if DT_RUNPATH in singles else None,
        "loader_features": [{"tag": LOADER_FEATURES[tag], "value": value}
                            for tag, value in rows if tag in LOADER_FEATURES],
        "unrecognized_dynamic_tags": sorted({tag for tag, _ in rows if tag not in KNOWN_DYNAMIC_TAGS}),
        "dynamic_entries": len(rows), "constants_source": CONSTANTS_URL,
        "scope": "dependency metadata only; no loading, resolution, environment or runtime qualification",
    }
    return result


def _allowed_name(name, paths, *, absolute=False):
    if (type(name) is not str or not name or any(ord(char) <= 32 or ord(char) >= 127 for char in name)
            or "$" in name or "\\" in name):
        return False
    if "/" not in name:
        return not absolute and any(fnmatchcase(name, pattern) for patterns in paths.values() for pattern in patterns)
    if not name.startswith("/") or any(part in ("", ".", "..") for part in name.split("/")[1:]):
        return False
    directory, _, basename = name.rpartition("/")
    return any(fnmatchcase(basename, pattern) for pattern in paths.get(directory, ()))


def check_tcec_policy(metadata):
    """Check the documented dependency names, never grant ELF qualification.

    SONAMEs are allowed names, not proof of which on-disk library a loader will
    select. Actual resolution/LD_PRELOAD, external-program use, startup, UCI and
    the complete submitted size remain the producer/runtime consumer's work.
    Search-path tags and loader extensions require a separate reviewed policy.
    """
    _require(type(metadata) is dict and metadata.get("format") == FORMAT,
             "actual inspector metadata required")
    required = {"input", "elf_type", "interpreter", "load_page_bytes", "has_dynamic", "has_tls", "needed",
                "soname", "rpath", "runpath", "loader_features", "unrecognized_dynamic_tags"}
    _require(required <= metadata.keys(), "complete ELF dependency metadata keys required")
    identity = metadata["input"]
    _require(type(identity) is dict and type(identity.get("bytes")) is int
             and 64 <= identity["bytes"] <= MAX_INPUT and type(identity.get("sha256")) is str
             and len(identity["sha256"]) == 64
             and all(char in "0123456789abcdef" for char in identity["sha256"]),
             "complete inspected input identity required")
    page = metadata["load_page_bytes"]
    _require(type(page) is int and page == LOAD_PAGE_BYTES, "current 4KiB load-page metadata required")
    _require(metadata.get("elf_type") in ("ET_EXEC", "ET_DYN")
             and type(metadata.get("has_dynamic")) is bool and type(metadata.get("has_tls")) is bool,
             "complete ELF dependency metadata required")
    _require(type(metadata.get("needed")) is list and all(type(name) is str for name in metadata["needed"])
             and len(metadata["needed"]) <= MAX_DYNAMIC, "bounded needed-library metadata required")
    _require(metadata.get("interpreter") is None or type(metadata["interpreter"]) is str,
             "typed interpreter metadata required")
    _require(all(metadata.get(key) is None or type(metadata[key]) is str for key in ("rpath", "runpath", "soname"))
             and type(metadata.get("loader_features")) is list
             and type(metadata.get("unrecognized_dynamic_tags")) is list,
             "complete typed dynamic-feature metadata required")
    reasons = []
    interpreter = metadata["interpreter"]
    if interpreter is not None and not _allowed_name(interpreter, INTERPRETER_PATHS, absolute=True):
        reasons.append("interpreter is outside the documented loader paths")
    for name in metadata["needed"]:
        if not _allowed_name(name, LIBRARY_PATHS):
            reasons.append("needed library is outside the documented names/paths: " + name)
    if metadata["rpath"] is not None or metadata["runpath"] is not None:
        reasons.append("DT_RPATH/DT_RUNPATH resolution is outside this bounded profile policy")
    if metadata["loader_features"]:
        reasons.append("additional loader configuration/audit/filter features require separate review")
    if metadata["unrecognized_dynamic_tags"]:
        reasons.append("unrecognized dynamic tags require separate review")
    return {"allowed": not reasons, "reasons": reasons, "rule_url": RULE_URL,
            "scope": "ELF dependency-name policy only", "runtime_resolution_checked": False,
            "environment_checked": False, "external_programs_checked": False,
            "size_checked": False, "runtime_qualified": False}
