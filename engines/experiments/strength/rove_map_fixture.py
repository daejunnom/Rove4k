"""Synthetic-only experiment for a GNU ld map from a stripped PIE link.

This does not accept engine source or a pre-existing map. It binds the map to
the native output from the *same* compiler invocation and checks byte identity
with a second link without -Map. It never runs either executable.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct
import subprocess
import tempfile

SOURCE = b"""#include <stdint.h>
typedef struct { uint64_t a, b, c; } Entry;
_Static_assert(sizeof(Entry)==24, "fixture entry");
Entry *qq;
_Static_assert(sizeof(qq)==8, "fixture pointer");
int main(void) { return qq != 0; }
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def elf_candidate(data, address):
    """Check a fixture address in writable mapped memory, not symbol meaning."""
    if len(data) < 64 or data[:16] != b'\x7fELF\x02\x01\x01' + b'\x00' * 9:
        raise ValueError("expected ELF64 little-endian System V")
    e_type, machine = struct.unpack_from('<HH', data, 16)
    phoff, shoff = struct.unpack_from('<QQ', data, 32)
    phentsize, phnum, shentsize, shnum = struct.unpack_from('<HHHH', data, 54)
    if e_type not in (2, 3) or machine != 62 or phentsize != 56 or shentsize != 64:
        raise ValueError("unsupported executable format")
    if not phnum or phoff + phnum * phentsize > len(data) or not shnum or shoff + shnum * shentsize > len(data):
        raise ValueError("truncated ELF tables")
    writable = []
    for i in range(phnum):
        typ, flags, offset, vaddr, _, filesz, memsz, _ = struct.unpack_from('<IIQQQQQQ', data, phoff + 56*i)
        if typ == 1 and flags & 2 and filesz <= memsz and address >= vaddr + filesz and address + 8 <= vaddr + memsz:
            writable.append((vaddr, offset, filesz, memsz))
    if address % 8 or len(writable) != 1:
        raise ValueError("candidate is not aligned in one writable PT_LOAD")
    # Relocations that write any byte of the pointer prevent interpreting it as
    # the zero-initialized fixture object. REL/RELA offsets are virtual addresses.
    for i in range(shnum):
        values = struct.unpack_from('<IIQQQQIIQQ', data, shoff + 64*i)
        typ, off, size, entsize = values[1], values[4], values[5], values[9]
        if typ == 2:
            raise ValueError("fixture output is not stripped")
        if typ == 19:
            raise ValueError("RELR relocations are unsupported")
        if typ == 6:
            if entsize != 16 or size % entsize or off + size > len(data):
                raise ValueError("invalid dynamic table")
            for pos in range(off, off + size, entsize):
                tag = struct.unpack_from('<q', data, pos)[0]
                if tag in (35, 36, 37):
                    raise ValueError("dynamic RELR relocations are unsupported")
        if typ not in (4, 9):
            continue
        minimum = 24 if typ == 4 else 16
        if entsize < minimum or size % entsize or off + size > len(data):
            raise ValueError("invalid relocation table")
        for pos in range(off, off + size, entsize):
            target, info = struct.unpack_from('<QQ', data, pos)
            if (info & 0xffffffff) not in (0, 6, 7, 8):
                raise ValueError("unsupported x86-64 relocation")
            if target < address + 8 and target + 8 > address:
                raise ValueError("candidate has a dynamic relocation")
    return 'PIE' if e_type == 3 else 'EXEC'


def map_candidate(raw):
    """Restrict parsing to one GNU map .bss object and one qq line."""
    text = raw.decode('utf-8', errors='strict')
    matches = list(re.finditer(r'(?m)^[ \t]*(0x[0-9a-fA-F]+)[ \t]+qq[ \t]*$', text))
    if len(matches) != 1:
        raise ValueError("map lacks exactly one fixture symbol")
    match = matches[0]
    preceding = text[:match.start()].splitlines()
    if not preceding:
        raise ValueError("map section missing")
    section = re.fullmatch(r'\s*\.bss\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+\S+\.o\s*', preceding[-1])
    if not section:
        raise ValueError("fixture symbol is not directly attached to .bss object")
    start, size, address = int(section[1], 16), int(section[2], 16), int(match[1], 16)
    if size != 8 or address != start:
        raise ValueError("fixture .bss object layout differs")
    return address


def inspect(*, pie=True):
    """Compile the fixed synthetic source twice; never execute a fixture."""
    with tempfile.TemporaryDirectory(prefix='rove-map-fixture-') as td:
        mode = ['-fPIE', '-pie'] if pie else ['-fno-pie', '-no-pie']
        common = ['cc', '-std=c11', '-Os', *mode, '-x', 'c', '-', '-s', '-o', 'x']
        def link(extra):
            result = subprocess.run(common + extra, input=SOURCE, cwd=td,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=60, check=False)
            if result.returncode:
                raise ValueError('fixture link failed: ' + result.stderr[-4096:].decode(errors='replace'))
            return Path(td, 'x').read_bytes()
        baseline = link([])
        native = link(['-Wl,-Map=fixture.map'])
        map_bytes = Path(td, 'fixture.map').read_bytes()
        if native != baseline:
            raise ValueError("map link changed executable bytes")
        address = map_candidate(map_bytes)
        kind = elf_candidate(native, address)
        if kind != ('PIE' if pie else 'EXEC'):
            raise ValueError('link mode differs')
        return {'source_sha256': digest(SOURCE), 'native_sha256': digest(native),
                'map_sha256': digest(map_bytes), 'symbol': 'qq', 'elf_value': address,
                'type': kind, 'same_link_native_map': True,
                'identical_to_no_map_link': True, 'executed': False,
                'tt_semantics_proven': False, 'runtime_address_observed': False}
