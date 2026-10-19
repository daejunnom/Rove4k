"""Explicit, restricted ELF deployment variants; no external dependencies.

Removing section headers is NOT byte-lossless compression and not a general
program-equivalence transformation. The caller must declare that deployment
does not observe its own file/ELF section headers or require section-based tools.
The edited ELF metadata must not be repurposed as executable code or data.
Program-header file extents, the ELF header and the program-header table remain.
Linux-compatible ELF64 little-endian x86-64 ET_EXEC/ET_DYN only; no extended
numbering. This deliberately rejects rather than guesses unsupported layouts.
"""

from __future__ import annotations

import struct


class ElfPreconditionError(ValueError):
    """The requested deployment transform's input contract is not satisfied."""


ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
PROGRAM_HEADER = struct.Struct("<IIQQQQQQ")
SECTION_HEADER = struct.Struct("<IIQQQQIIQQ")
UINT64_LIMIT = 1 << 64


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ElfPreconditionError(message)


def _checked_end(offset: int, size: int, total: int, label: str) -> int:
    end = offset + size
    _require(end < UINT64_LIMIT and end <= total,
             f"{label} file extent is outside the input")
    return end


def _sectionless(data: bytes) -> bytes:
    _require(len(data) >= ELF_HEADER.size, "truncated ELF header")
    (ident, kind, machine, version, entry, phoff, shoff, flags, ehsize,
     phentsize, phnum, shentsize, shnum, shstrndx) = ELF_HEADER.unpack_from(data)
    _require(ident[:4] == b"\x7fELF", "input is not ELF")
    _require(ident[4:7] == b"\x02\x01\x01",
             "requires ELF64, little endian, ELF version 1")
    _require(ident[7] in (0, 3) and ident[8] == 0,
             "requires System V/Linux OS ABI with ABI version 0")
    _require(kind in (2, 3), "requires ET_EXEC or ET_DYN")
    _require(machine == 62 and version == 1 and flags == 0,
             "requires ordinary x86-64 ELF version 1")
    _require(ehsize == ELF_HEADER.size, "unexpected ELF header size")
    _require(phentsize == PROGRAM_HEADER.size,
             "unexpected program-header entry size")
    _require(0 < phnum < 0xFFFF, "requires nonextended program-header count")
    _require(phoff >= ehsize, "program-header table overlaps ELF header")
    phend = _checked_end(phoff, phnum * phentsize, len(data), "program headers")

    # Validate the supplied normal section-table description before removing it.
    # Sectionless ELF inputs are allowed and make this operation idempotent.
    if shoff == 0:
        _require(shnum == 0 and shstrndx == 0 and shentsize in (0, 64),
                 "inconsistent absent section-header table")
    else:
        _require(shoff >= ehsize and shentsize == SECTION_HEADER.size,
                 "unexpected section-header layout")
        _require(0 < shnum < 0xFF00 and shstrndx < shnum,
                 "extended or invalid section-header numbering is unsupported")
        _checked_end(shoff, shnum * shentsize, len(data), "section headers")
        for index in range(shnum):
            (name, stype, sflags, address, offset, size, link, info,
             alignment, entsize) = SECTION_HEADER.unpack_from(
                 data, shoff + index * shentsize)
            if index == 0:
                _require(stype == 0 and size == 0 and link == 0 and info == 0,
                         "nonordinary section zero or extended numbering")
            elif stype not in (0, 8):  # NULL and NOBITS have no file payload.
                _checked_end(offset, size, len(data), f"section {index}")

    end = max(ehsize, phend)
    loads = 0
    for index in range(phnum):
        (ptype, pflags, offset, vaddr, paddr, filesz, memsz, align) = \
            PROGRAM_HEADER.unpack_from(data, phoff + index * phentsize)
        segment_end = _checked_end(offset, filesz, len(data),
                                   f"program header {index}")
        end = max(end, segment_end)
        _require(vaddr + memsz < UINT64_LIMIT,
                 f"program header {index} memory extent overflows")
        if ptype == 1:  # PT_LOAD
            loads += 1
            _require(filesz <= memsz,
                     f"load segment {index} filesz exceeds memsz")
            _require(align in (0, 1) or align & (align - 1) == 0,
                     f"load segment {index} alignment is not a power of two")
            if align > 1:
                _require(offset % align == vaddr % align,
                         f"load segment {index} file/virtual alignment differs")
    _require(loads > 0, "requires at least one loadable segment")

    result = bytearray(data[:end])
    struct.pack_into("<Q", result, 40, 0)  # e_shoff
    struct.pack_into("<HHH", result, 58, 0, 0, 0)  # shentsize/shnum/shstrndx
    return bytes(result)


def deployment_variants(raw_bytes: bytes, *,
                        allow_section_header_removal: bool) -> list[dict]:
    """Return identity and an explicitly authorized deployment transform.

    True means the caller declares section headers/self-file bytes unobserved
    and the edited metadata unused as code/data by its runtime/deployment
    contract. This function cannot establish that
    semantic precondition from arbitrary machine code. Final candidates must
    still pass their actual execution tests. Unsupported enabled inputs raise
    ElfPreconditionError; they are not reported as successfully transformed.
    """
    _require(isinstance(raw_bytes, bytes), "raw_bytes must be bytes")
    _require(isinstance(allow_section_header_removal, bool),
             "allow_section_header_removal must be boolean")
    variants = [{"id": "original", "data": raw_bytes,
                 "preconditions": ["identity bytes"]}]
    if allow_section_header_removal:
        variants.append({
            "id": "no-section-headers",
            "data": _sectionless(raw_bytes),
            "preconditions": [
                "declared Linux-compatible ELF64LE x86-64 ET_EXEC/ET_DYN deployment",
                "no runtime/deployment observation of self-file or section headers",
                "edited ELF metadata is not repurposed as executable code or data",
                "ordinary nonextended ELF and program-header numbering",
                "all ELF/program-header and segment file extents retained",
                "actual final artifact execution must be verified",
            ],
        })
    return variants
