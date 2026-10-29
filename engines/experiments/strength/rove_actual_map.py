"""Diagnostic same-link map replay for strictly admitted C TEST artifacts.

Never executes an engine or observes a process. A map address is a candidate,
not proof of runtime TT semantics, placement, SMT, playing strength or GO.
Only narrowly named compiler recipes and source shapes are accepted.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile

try:
    from . import peer_runtime, rove_b_static_tt
except ImportError:
    import peer_runtime
    import rove_b_static_tt

BITS = {"test-p16": 29, "test-p192": 33}
NAMES = {"A": ("Z", "N"), "B": ("zb", "qq"), "C": ("Z", "qq"),
         "E": ("Z", "qq"), "F": ("ql", "B")}
COMMON = ("cc", "-Os", "-x", "c", "-", "-o", "x", "-s")
COMMANDS = {
    "A": {COMMON}, "C": {("cc", "-Os", "-mavx2", "-x", "c", "-", "-o", "x", "-s")},
    "E": {COMMON}, "F": {("cc", "-Os", "-pthread", "-x", "c", "-", "-o", "x", "-s")},
    "B": {tuple(rove_b_static_tt.COMMAND),
          ("cc", "-std=c11", "-Os", "-pthread", "-DWORKERS=2", "-DTT_BITS=18", "-DDEV=0", "-x", "c", "-", "-o", "x")},
}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _verify_module():
    path = Path(__file__).resolve().parent.parent / "tcec-next" / "profile_verify.py"
    name = "rove_map_profile_verify"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_contract(source, family, profile):
    """Check exact projected consumers after independent strict admission."""
    if family not in NAMES or profile not in BITS or type(source) is not bytes:
        raise ValueError("unsupported C TEST source")
    typ, symbol = NAMES[family]
    candidates = ["RVN"] + (["qN"] if family == "B" else [])
    valid = []
    for count in candidates:
        terms = (f"#define {count} ((size_t)1<<{BITS[profile]})\n",
                 f"{typ}*{symbol};", f"{symbol}=aligned_alloc(4096,{count}*sizeof*{symbol});",
                 f"{symbol}+(a&({count}-1))")
        if all(source.count(term.encode()) == 1 for term in terms):
            valid.append(count)
    if len(valid) != 1:
        raise ValueError("final source candidate contract unavailable")
    return typ, symbol, valid[0]


def map_candidate(raw, symbol):
    """Require a unique global map symbol inside one input .bss section."""
    if not isinstance(raw, bytes) or len(raw) > 16 * 1024 * 1024 or symbol not in {v[1] for v in NAMES.values()}:
        raise ValueError("unsupported map or candidate")
    lines = raw.decode("utf-8", errors="strict").splitlines()
    sym = re.compile(r"^\s*(0x[0-9a-fA-F]+)\s+" + re.escape(symbol) + r"\s*$")
    section = re.compile(r"^\s*\.bss\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+\S+\.o\s*$")
    rows = [i for i, line in enumerate(lines) if sym.fullmatch(line)]
    if len(rows) != 1:
        raise ValueError("map candidate missing or ambiguous")
    pos = rows[0]
    # A new input section between the object and symbol invalidates association.
    for line in reversed(lines[:pos]):
        item = section.fullmatch(line)
        if item:
            start, size = int(item[1], 16), int(item[2], 16)
            address = int(sym.fullmatch(lines[pos])[1], 16)
            if start <= address and address + 8 <= start + size:
                return address
            break
        if re.match(r"^\s*\.[A-Za-z_][\w.]*\s+0x", line):
            break
    raise ValueError("map candidate is outside its input .bss")


def elf_candidate(native, address):
    """Bound candidate to writable zero-fill PT_LOAD; reject unknown relocations."""
    elf = peer_runtime.Elf64(native)
    segments = [p for p in elf.programs if p[0] == 1 and p[1] & 2 and p[5] <= p[6]
                and p[3] + p[5] <= address and address + 8 <= p[3] + p[6]]
    if address % 8 or len(segments) != 1:
        raise ValueError("candidate is not inside one writable zero-fill PT_LOAD")
    for s in elf.sections:
        typ, off, size, entsize = s[1], s[4], s[5], s[9]
        if typ == 19:
            raise ValueError("RELR unsupported")
        if typ == 6:
            if entsize != 16 or size % 16:
                raise ValueError("invalid dynamic table")
            elf.segment(off, size)
            for i in range(off, off + size, 16):
                if elf.unpack("qQ", i)[0] in (35, 36, 37):
                    raise ValueError("dynamic RELR unsupported")
        if typ not in (4, 9):
            continue
        width = 24 if typ == 4 else 16
        if entsize != width or size % width:
            raise ValueError("unsupported relocation table")
        elf.segment(off, size)
        for i in range(off, off + size, width):
            target, info = elf.unpack("QQ", i)
            relocation = info & 0xffffffff
            if relocation not in (0, 5, 6, 7, 8):
                raise ValueError("unsupported relocation type")
            write_width = 0 if relocation == 0 else 8
            if relocation == 5:  # R_X86_64_COPY writes the dynamic symbol's size.
                link, index = s[6], info >> 32
                if link >= len(elf.sections):
                    raise ValueError("copy relocation symbol table unavailable")
                table = elf.sections[link]
                if table[1] != 11 or table[9] != 24 or table[5] % 24 or index >= table[5] // 24:
                    raise ValueError("invalid copy relocation symbol table")
                elf.segment(table[4], table[5])
                symbol = elf.unpack("IBBHQQ", table[4] + index * 24)
                if symbol[3] == 0 or symbol[4] != target or symbol[5] == 0:
                    raise ValueError("invalid copy relocation symbol")
                write_width = symbol[5]
            if target + write_width > 1 << 64:
                raise ValueError("relocation range overflow")
            if write_width and target < address + 8 and target + write_width > address:
                raise ValueError("candidate intersects relocation")
    return "PIE" if elf.kind == 3 else "EXEC"


def inspect(manifest, build, compiler_sha, linker_sha):
    """Replay only a strict-admitted final source/native, without execution."""
    admitted = _verify_module().admit_c_build(manifest, Path(build))
    family, profile = admitted.family, admitted.profile_id
    command = manifest.get("compile_executor")
    if family not in COMMANDS or type(command) is not list or tuple(command) not in COMMANDS[family]:
        raise ValueError("actual compiler recipe not admitted for family")
    source = (Path(build) / admitted.source).read_bytes()
    native = (Path(build) / admitted.native).read_bytes()
    for name, data in (("source", source), ("native", native)):
        if (len(data), _digest(data)) != (admitted.expected[name + "_bytes"], admitted.expected[name + "_sha256"]):
            raise ValueError("admitted " + name + " differs")
    typ, symbol, count = source_contract(source, family, profile)
    bits = BITS[profile]
    res = admitted.resources
    if (res["tt_bits"], res["tt_entries"], res["tt_entry_bytes"], res["tt_bytes"], res["tt_mask"]) != (bits, 1 << bits, 24, 24 << bits, (1 << bits) - 1):
        raise ValueError("admitted resource contract differs")
    compiler = rove_b_static_tt._tool("cc", compiler_sha)
    proc = subprocess.run([compiler, "-print-prog-name=ld"], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=10, check=True)
    linker_name = proc.stdout.decode("utf-8", "strict").strip()
    if not linker_name or "\n" in linker_name:
        raise ValueError("invalid linker name")
    rove_b_static_tt._tool(linker_name, linker_sha)
    assertions = (f'\n_Static_assert(sizeof({typ})==24,"TT entry");\n'
                  f'_Static_assert(sizeof(*{symbol})==24,"TT pointee");\n'
                  f'_Static_assert(sizeof({symbol})==8,"TT pointer");\n').encode()
    with tempfile.TemporaryDirectory(prefix="rove-actual-map-") as directory:
        def link(input_source, extra):
            cmd = [compiler, *command[1:], *extra]
            result = subprocess.run(cmd, input=input_source, cwd=directory,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
            if result.returncode:
                raise ValueError("link replay failed: " + result.stderr[-4096:].decode(errors="replace"))
            return (Path(directory) / "x").read_bytes()
        with_map = link(source, ["-Wl,-Map=fixture.map"])
        map_bytes = (Path(directory) / "fixture.map").read_bytes()
        if with_map != native:
            raise ValueError("same-link map native differs from admitted native")
        if link(source + assertions, []) != native:
            raise ValueError("source type assertions change native bytes")
        offset = map_candidate(map_bytes, symbol)
        kind = elf_candidate(native, offset)
    return {"schema": "rove4k.actual-map-candidate.v1", "family": family, "profile": profile,
            "source_sha256": _digest(source), "native_sha256": _digest(native),
            "map_sha256": _digest(map_bytes), "compiler_sha256": compiler_sha,
            "linker_sha256": linker_sha, "compiler_command": command, "source_counter": count,
            "symbol_candidate": symbol, "elf_value": offset, "elf_kind": kind,
            "same_link_map": True, "native_bytes_match": True,
            "target_pointer_and_entry_assertions": True, "engine_executed": False,
            "tt_semantics_proven": False, "runtime_address_observed": False,
            "physical_placement_qualified": False, "smt_qualified": False, "go": False}
