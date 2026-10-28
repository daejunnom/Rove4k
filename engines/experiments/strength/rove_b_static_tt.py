"""Static source-to-native evidence for B's candidate pointer; never runs B.

The caller must first strictly admit the build.  This verifies that the exact
admitted source recompiles to the exact native bytes with the recorded local
toolchain, and checks a limited source/symbol contract.  It does not establish
the runtime meaning of the symbol, physical placement, or playing strength.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import peer_runtime
import rove_b_tt_observe

COMMAND = ["cc", "-std=c11", "-Os", "-pthread", "-x", "c", "-", "-o", "x"]
BITS = {"test-p16": 29, "test-p192": 33}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _tool(name, expected):
    path = shutil.which(name)
    if path is None or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("compiler or linker pin unavailable")
    raw = Path(path).read_bytes()
    if _digest(raw) != expected:
        raise ValueError("compiler or linker bytes differ from recorded pin")
    return str(Path(path).resolve())


def _run(command, source, cwd):
    result = subprocess.run(command, input=source, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=60, check=False)
    if result.returncode:
        raise ValueError("source compile failed: " + result.stderr[-4096:].decode(errors="replace"))


def inspect(admitted, manifest, build, compiler_sha, linker_sha):
    """Inspect an already strictly admitted B profile on its producer host."""
    if admitted.family != "B" or admitted.profile_id not in BITS:
        raise ValueError("only admitted B P16/P192 profiles are supported")
    if manifest.get("compiler") != COMMAND:
        raise ValueError("unexpected B compiler command")
    compiler = _tool("cc", compiler_sha)
    result = subprocess.run([compiler, "-print-prog-name=ld"], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=10, check=True)
    linker_name = result.stdout.decode().strip()
    if not linker_name or "\n" in linker_name:
        raise ValueError("unexpected linker path")
    _tool(linker_name, linker_sha)
    source = (Path(build) / admitted.source).read_bytes()
    native = (Path(build) / admitted.native).read_bytes()
    expected = admitted.expected
    for label, raw in (("source", source), ("native", native)):
        if (len(raw), _digest(raw)) != (expected[label + "_bytes"], expected[label + "_sha256"]):
            raise ValueError(label + " differs from admitted pin")
    bits = BITS[admitted.profile_id]
    resources = admitted.resources
    if (resources["tt_bits"], resources["tt_entries"], resources["tt_entry_bytes"],
        resources["tt_bytes"], resources["tt_mask"]) != (bits, 1 << bits, 24, 24 << bits, (1 << bits) - 1):
        raise ValueError("admitted TT resources differ")
    expected_macro = f"#define qN ((size_t)1<<{bits})\n".encode()
    required = (expected_macro, b"zb*qq;", b"qq=aligned_alloc(4096,qN*sizeof*qq);",
                b"qq+(a&(qN-1))")
    if any(source.count(term) != 1 for term in required):
        raise ValueError("B candidate source contract differs")
    with tempfile.TemporaryDirectory(prefix="rove-b-static-") as directory:
        _run([compiler, *COMMAND[1:]], source, directory)
        rebuilt = (Path(directory) / "x").read_bytes()
        if rebuilt != native:
            raise ValueError("compiler output differs from admitted native bytes")
        _run([compiler, "-std=c11", "-pthread", "-x", "c", "-", "-fsyntax-only"],
             source + b'\n_Static_assert(sizeof(zb)==24,"B entry width");\n', directory)
    symbol = rove_b_tt_observe._symbol_value(peer_runtime.Elf64(native), "qq")
    return {"schema": "rove4k.b-static-candidate.v1", "family": "B", "profile": admitted.profile_id,
            "source": {"bytes": len(source), "sha256": _digest(source)},
            "native": {"bytes": len(native), "sha256": _digest(native)},
            "compiler_sha256": compiler_sha, "linker_sha256": linker_sha, "compiler_command": COMMAND,
            "source_recompiled_native_identical": True, "entry_bytes_compile_assertion": 24,
            "candidate_symbol": "qq", "candidate_symbol_value": symbol,
            "candidate_tt_bytes": 24 << bits, "source_allocation_alignment": 4096,
            "engine_executed": False, "live_pointer_observed": False,
            "tt_semantics_proven": False, "physical_placement_qualified": False,
            "runtime_qualified": False, "playing_strength_qualified": False}
