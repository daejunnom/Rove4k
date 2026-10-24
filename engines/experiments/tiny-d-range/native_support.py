#!/usr/bin/env python3
"""Project-owned TinyD direct-loader v3 helper, reused with RANGE_PROFILE macro.
Frozen source hashes and exact local provenance are documented in README.md.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
INPUTS = {
    "scalar-shipping": (8540, "ef14e2839af96d111fa9ce1a2928749ceec518e3be652cc6d36ee8975cae47d0", 8806, 0x401fa6),
    "hq-shipping": (8928, "387a00209ffcc14446f662a56cc2ff778ae7873c2dfebebbee9906fd19e5cd0c", 9142, 0x4020e3),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def elf(data):
    if len(data) < 64 or data[:9] != b"\x7fELF\x02\x01\x01\0\0":
        raise ValueError("expected ELF64 little-endian System V ABI")
    kind, machine, version = struct.unpack_from("<HHI", data, 16)
    entry, phoff, shoff = struct.unpack_from("<QQQ", data, 24)
    flags, ehsize, phsize, phnum, shsize, shnum, shstr = struct.unpack_from("<IHHHHHH", data, 48)
    if (kind, machine, version, flags, ehsize, phoff, phsize) != (2, 62, 1, 0, 64, 64, 56):
        raise ValueError("unsupported ELF header")
    if not 1 <= phnum <= 3 or phoff + phnum*phsize > len(data):
        raise ValueError("invalid program header extent")
    segments = [dict(zip(("type", "flags", "offset", "vaddr", "paddr", "filesz", "memsz", "align"),
                         struct.unpack_from("<IIQQQQQQ", data, phoff+i*phsize))) for i in range(phnum)]
    return {"entry": entry, "section_offset": shoff, "section_size": shsize, "section_count": shnum,
            "section_names": shstr, "segments": segments}


def admit(data, form):
    size, expected, _, entry = INPUTS[form]
    if len(data) != size or sha(data) != expected:
        raise ValueError("unknown TinyD image bytes: " + form)
    parsed = elf(data)
    expected_segments = [
        {"type": 1, "flags": 5, "offset": 0, "vaddr": 0x400000, "paddr": 0x400000, "filesz": size, "memsz": size, "align": 4096},
        {"type": 1, "flags": 6, "offset": 0, "vaddr": 0x403000, "paddr": 0x403000, "filesz": 0, "memsz": 175092, "align": 4096},
        {"type": 0x6474e551, "flags": 6, "offset": 0, "vaddr": 0, "paddr": 0, "filesz": 0, "memsz": 0, "align": 8},
    ]
    if parsed["entry"] != entry or parsed["segments"] != expected_segments or any(parsed[key] for key in ("section_offset", "section_size", "section_count", "section_names")):
        raise ValueError("unadmitted layout/interpreter/TLS/dynamic/data/entry")
    image_pages = (size+4095)&-4096
    bss_pages = (175092+4095)&-4096
    if 0x400000+image_pages != 0x403000:
        raise ValueError("RX/RW pages overlap or layout changed")
    return {**parsed, "image_base": 0x400000, "image_size": size, "image_pages": image_pages,
            "bss_base": 0x403000, "bss_size": 175092, "bss_pages": bss_pages,
            "guard_base": 0x3ff000, "reserve_size": 4096+image_pages+bss_pages+4096,
            "upper_guard": 0x403000+bss_pages}


def run(command, *, timeout=120):
    started = time.monotonic()
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        stdout, stderr = p.communicate()
        raise RuntimeError("compiler/process timeout: " + json.dumps(list(map(str, command))))
    record = {"command": list(map(str, command)), "returncode": p.returncode, "wall_seconds": time.monotonic()-started,
              "stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace")}
    if p.returncode:
        raise RuntimeError(json.dumps(record))
    return record


def stripped_loader(data):
    parsed = elf(data)
    loads = [s for s in parsed["segments"] if s["type"] == 1]
    if len(loads) != 1 or len(parsed["segments"]) != 2 or loads[0]["flags"] != 5 or loads[0]["vaddr"] != 0x10000000:
        raise ValueError("loader must contain exactly one fixed RX image and nonexec stack")
    stack = next(s for s in parsed["segments"] if s["type"] == 0x6474e551)
    if stack["flags"] != 6 or any(s["flags"] & 3 == 3 for s in parsed["segments"]):
        raise ValueError("loader has executable writable mapping/stack")
    segment = loads[0]
    if segment["filesz"] != segment["memsz"] or segment["offset"]:
        raise ValueError("loader unexpectedly needs writable state")
    out = bytearray(data[:segment["filesz"]])
    struct.pack_into("<Q", out, 40, 0)
    struct.pack_into("<HHH", out, 58, 0, 0, 0)
    return bytes(out)


def compile_loader(directory, recipe, payload, layout, codec, compiler, checkpoint=False):
    directory.mkdir(parents=True)
    payload_path = directory / "payload.bin"
    payload_path.write_bytes(payload)
    quoted = str(payload_path).replace("\\", "\\\\").replace('"', '\\"')
    assembly = directory / "payload.S"
    assembly.write_text('.section .payload,"a",@progbits\n.global payload,payload_end\npayload:\n'
                        '.incbin "' + quoted + '"\npayload_end:\n.section .note.GNU-stack,"",@progbits\n')
    definitions = {"IMAGE_BASE": layout["image_base"], "IMAGE_SIZE": layout["image_size"], "IMAGE_PAGES": layout["image_pages"],
                   "IMAGE_ENTRY": layout["entry"], "BSS_BASE": layout["bss_base"], "BSS_PAGES": layout["bss_pages"],
                   "GUARD_BASE": layout["guard_base"], "RESERVE_SIZE": layout["reserve_size"],
                   "RANGE_PROFILE": int(codec == "mix2"), "CHECKPOINT": int(checkpoint)}
    flags = ["-Oz", "-flto", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic", "-fno-builtin",
             "-fno-stack-protector", "-fno-asynchronous-unwind-tables", "-fno-unwind-tables", "-fno-ident",
             "-fcf-protection=none", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections,--build-id=none,-s,-z,noexecstack"]
    command = [compiler, *flags, *[f"-D{name}={value}UL" for name,value in definitions.items()], str(recipe/"loader.c"), str(assembly),
               "-Wl,-T," + str(recipe/"image.ld"), "-o", str(directory/"linked")]
    record = run(command)
    (directory / "compile.json").write_text(json.dumps(record, indent=2)+"\n")
    data = stripped_loader((directory/"linked").read_bytes())
    target = directory / "x"
    target.write_bytes(data)
    target.chmod(0o755)
    return {"path": str(target), "bytes": len(data), "sha256": sha(data), "compile": record, "definitions": definitions,
            "payload_bytes": len(payload), "loader_and_headers_bytes": len(data)-len(payload)}
