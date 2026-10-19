#!/usr/bin/env python3
"""Build an ELF64 x86-64 self-restoring image using only Python stdlib + cc.

The built loader has no runtime compiler, decoder, shell or temporary pathname.
It restores the exact original ELF to an anonymous memfd and executes that ELF.
This preserves ordinary argv/env/stdio and kernel ELF initialization. Self-file
paths, /proc/self/exe identity, auxv AT_EXECFN and privileged-file semantics are
outside this deployment contract. Full output size determines size eligibility.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import time

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
_SOURCES = _HERE / "elf-loader"
_MAX_INPUT = 256 * 1024 * 1024


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bcj(data: bytes, *, inverse: bool = False, deadline: float | None = None) -> bytes:
    """Reversible whole-file E8/E9 operand transform, not an x86 disassembler.

    Add the file position following each complete five-byte E8/E9 sequence to
    its unsigned LE32 operand (subtract for inverse), modulo 2^32. Both scans
    leave the opcode unchanged and skip all four operands, so opcode-looking
    bytes in an operand cannot change the later scan's position.
    """
    transformed = bytearray(data)
    at = 0
    while at+4 < len(transformed):
        if deadline is not None and at % 4096 < 5 and time.monotonic() >= deadline:
            raise TimeoutError("ELF branch filtering exceeded time bound")
        if transformed[at] in (0xE8, 0xE9):
            value = int.from_bytes(transformed[at+1:at+5], "little")
            value = (value-(at+5) if inverse else value+(at+5)) & 0xFFFFFFFF
            transformed[at+1:at+5] = value.to_bytes(4, "little")
            at += 5
        else:
            at += 1
    return bytes(transformed)


def _elf(data: bytes) -> dict:
    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("input must be ELF64 little-endian")
    if data[7] not in (0, 3) or data[8] != 0:
        raise ValueError("unsupported ELF operating-system ABI")
    kind, machine, version = struct.unpack_from("<HHI", data, 16)
    entry, phoff = struct.unpack_from("<QQ", data, 24)
    ehsize, phsize, phnum = struct.unpack_from("<HHH", data, 52)
    if kind not in (2, 3) or machine != 62 or version != 1 or ehsize != 64:
        raise ValueError("input must be Linux x86-64 ET_EXEC or ET_DYN")
    if phsize != 56 or not phnum or phnum == 65535 or phoff+phsize*phnum > len(data):
        raise ValueError("invalid or unsupported ELF program headers")
    maximum = 0
    has_entry = False
    interpreter = None
    for i in range(phnum):
        typ, flags, offset, virtual, _, filesz, memsz, align = struct.unpack_from(
            "<IIQQQQQQ", data, phoff+i*phsize)
        if offset+filesz > len(data) or virtual+memsz > (1 << 64):
            raise ValueError("ELF program segment exceeds file or address space")
        if typ == 1:
            if filesz > memsz or (align > 1 and (align & (align-1) or offset % align != virtual % align)):
                raise ValueError("invalid ELF load segment")
            maximum = max(maximum, offset+filesz)
            has_entry |= bool(flags & 1 and virtual <= entry < virtual+memsz)
        if typ == 3:
            raw = data[offset:offset+filesz]
            if not raw.startswith(b"/") or not raw.endswith(b"\0") or b"\0" in raw[:-1]:
                raise ValueError("invalid ELF interpreter")
            interpreter = os.fsdecode(raw[:-1])
    if not has_entry:
        raise ValueError("ELF entry is outside executable load segments")
    return {"type": "ET_EXEC" if kind == 2 else "ET_DYN",
            "interpreter": interpreter, "load_file_end": maximum}


def _compress(data: bytes, *, deadline: float | None = None) -> bytes:
    """Literal runs 1..128; matches length 3..130 with 16-bit distance.

    All candidates in the most recent 64 equal-three-byte hash entries are
    considered. Greedy ties choose the nearest prior match deterministically.
    Overlapping matches are legal and copied forward by the decoder.
    """
    chains: dict[bytes, deque[int]] = {}
    encoded = bytearray()
    literals = bytearray()
    n = len(data)

    def flush() -> None:
        if literals:
            encoded.append(len(literals)-1)
            encoded.extend(literals)
            literals.clear()

    def remember(at: int) -> None:
        expired = at-65535
        if expired >= 0:
            old_key = data[expired:expired+3]
            old_positions = chains.get(old_key)
            if old_positions and old_positions[0] == expired:
                old_positions.popleft()
                if not old_positions:
                    del chains[old_key]
        if at+2 < n:
            key = data[at:at+3]
            positions = chains.setdefault(key, deque(maxlen=64))
            positions.append(at)

    at = 0
    while at < n:
        if deadline is not None and at % 4096 < 130 and time.monotonic() >= deadline:
            raise TimeoutError("ELF compression exceeded time bound")
        best, distance = 0, 0
        if at+2 < n:
            positions = chains.get(data[at:at+3], ())
            maximum = min(130, n-at)
            for previous in reversed(positions):
                delta = at-previous
                if delta > 65535:
                    break
                length = 3
                while length < maximum and data[previous+length] == data[at+length]:
                    length += 1
                if length > best:
                    best, distance = length, delta
                    if best == maximum:
                        break
        # A three-byte match uses three bytes and a literal costs ~one byte;
        # accepting it can still save run overhead and enables later matches.
        if best >= 3:
            flush()
            encoded.append(128+best-3)
            encoded.extend(struct.pack("<H", distance))
            for position in range(at, at+best):
                remember(position)
            at += best
        else:
            literals.append(data[at])
            remember(at)
            at += 1
            if len(literals) == 128:
                flush()
    flush()
    return bytes(encoded)


def _decompress(data: bytes, expected: int) -> bytes:
    """Build-time inverse; exact native behavior is verified by execution too."""
    result = bytearray()
    at = 0
    while at < len(data):
        control = data[at]
        at += 1
        if control < 128:
            count = control+1
            if at+count > len(data):
                raise ValueError("truncated literal run")
            result.extend(data[at:at+count])
            at += count
        else:
            if at+2 > len(data):
                raise ValueError("truncated match")
            distance = int.from_bytes(data[at:at+2], "little")
            at += 2
            if not 0 < distance <= len(result):
                raise ValueError("invalid match distance")
            for _ in range((control & 127)+3):
                result.append(result[-distance])
        if len(result) > expected:
            raise ValueError("decoded payload exceeds declared size")
    if len(result) != expected:
        raise ValueError("decoded payload has wrong size")
    return bytes(result)


def pack_elf(input_path, output_path, *, cc="cc", timeout=120, filter="auto") -> dict:
    """Pack an ELF to an absolute path outside the repository; return metadata.

    Run on Linux x86-64 with a GCC/Clang compatible cc and GNU-compatible linker.
    The caller owns source runtime/protocol verification. Output is never silently
    replaced; use a new artifact directory for each build. Both unfiltered and
    BCJ candidates are built and measured including their actual native inverse
    code. Auto chooses the smaller complete ELF, preferring none on a tie.
    """
    started = time.monotonic()
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise ValueError("ELF loader builds require Linux x86-64 (WSL Ubuntu is supported)")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if filter not in ("none", "bcj", "auto"):
        raise ValueError("filter must be none, bcj or auto")
    source = Path(input_path).resolve(strict=True)
    target = Path(output_path)
    if not target.is_absolute():
        raise ValueError("ELF output must be an absolute external artifact path")
    target = target.resolve()
    if target.is_relative_to(_ROOT):
        raise ValueError("ELF output must be outside the repository")
    if target.exists():
        raise FileExistsError(f"output already exists: {target}")
    if source.stat().st_mode & 0o6000:
        raise ValueError("privileged setuid/setgid ELF semantics are unsupported")
    if source.stat().st_size > _MAX_INPUT:
        raise ValueError("ELF input exceeds 256 MiB build bound")
    data = source.read_bytes()
    input_elf = _elf(data)
    source_files = [_SOURCES / "loader.c", _SOURCES / "loader.ld", Path(__file__).resolve()]
    source_hashes = {str(path.relative_to(_HERE)): _sha(path.read_bytes()) for path in source_files}

    def run(arguments):
        remaining = timeout-(time.monotonic()-started)
        if remaining <= 0:
            raise TimeoutError("ELF packing exceeded time bound")
        return subprocess.run(arguments, check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=remaining)

    compiler_path = shutil.which(str(cc))
    if not compiler_path:
        raise FileNotFoundError(f"C compiler not found: {cc}")
    compiler = run([compiler_path, "--version"]).stdout.decode("utf-8", "replace").splitlines()[0]
    linker_path = run([compiler_path, "-print-prog-name=ld"]).stdout.decode("utf-8", "strict").strip()
    linker = run([linker_path, "--version"]).stdout.decode("utf-8", "replace").splitlines()[0]
    options = ["-Os", "-nostdlib", "-static", "-no-pie", "-fno-pie", "-fno-pic",
               "-fno-stack-protector", "-fno-builtin", "-fno-asynchronous-unwind-tables",
               "-fno-unwind-tables", "-fno-ident", "-fcf-protection=none",
               "-Wl,--build-id=none", "-Wl,-z,noexecstack", "-Wl,-s",
               f"-DOUTPUT_SIZE={len(data)}"]
    candidates = []
    artifacts = {}
    with tempfile.TemporaryDirectory(prefix="rove4k-elf-loader-") as directory:
        work = Path(directory)
        payload = work / "payload.bin"
        assembly = work / "payload.S"
        quoted = str(payload).replace("\\", "\\\\").replace('"', '\\"')
        assembly.write_text('.section .payload,"a",@progbits\n.balign 1\n'
                            '.global packed_payload,packed_payload_end\npacked_payload:\n'
                            f'.incbin "{quoted}"\npacked_payload_end:\n'
                            '.section .note.GNU-stack,"",@progbits\n', encoding="utf-8")
        for candidate_filter in ("none", "bcj"):
            filtered = data if candidate_filter == "none" else _bcj(data, deadline=started+timeout)
            packed = _compress(filtered, deadline=started+timeout)
            decoded = _decompress(packed, len(data))
            restored = decoded if candidate_filter == "none" else _bcj(decoded, inverse=True, deadline=started+timeout)
            if restored != data:
                raise RuntimeError("internal filter/compression roundtrip mismatch")
            payload.write_bytes(packed)
            linked = work / "loader"
            candidate_options = [*options, f"-DBRANCH_FILTER={int(candidate_filter == 'bcj')}"]
            run([compiler_path, *candidate_options, str(_SOURCES / "loader.c"), str(assembly),
                 "-Wl,-T,"+str(_SOURCES / "loader.ld"), "-o", str(linked)])
            built = bytearray(linked.read_bytes())
            load_end = _elf(built)["load_file_end"]
            # Only this freshly linked loader is section-stripped. The payload
            # restores the exact original ELF, including section metadata.
            built = built[:load_end]
            struct.pack_into("<Q", built, 40, 0)
            struct.pack_into("<HHH", built, 58, 0, 0, 0)
            output_elf = _elf(built)
            if output_elf["interpreter"] is not None:
                raise RuntimeError("self-restoring loader unexpectedly needs an interpreter")
            artifacts[candidate_filter] = built
            candidates.append({"filter": candidate_filter, "output_bytes": len(built),
                               "output_sha256": _sha(built), "payload_bytes": len(packed),
                               "loader_and_headers_bytes": len(built)-len(packed),
                               "within_size_limit": len(built) <= 4096,
                               "compiler_options": candidate_options})
        selected = (min(candidates, key=lambda candidate: candidate["output_bytes"])
                    if filter == "auto" else next(candidate for candidate in candidates if candidate["filter"] == filter))
        built = artifacts[selected["filter"]]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(built)
        target.chmod(0o755)
    return {"format": "elf64-x86_64-self-restoring", "codec": "rove4k-lz-runs-v1",
            "input": str(source), "input_bytes": len(data), "input_sha256": _sha(data),
            "output": str(target), "output_bytes": len(built), "output_sha256": _sha(built),
            "payload_bytes": selected["payload_bytes"],
            "loader_and_headers_bytes": selected["loader_and_headers_bytes"],
            "filter": selected["filter"], "requested_filter": filter,
            "filter_algorithm": "e8-e9-whole-file-add-next-offset-le32-v1" if selected["filter"] == "bcj" else None,
            "filter_candidates": candidates,
            "size_limit_bytes": 4096, "within_size_limit": len(built) <= 4096,
            "compiler": compiler, "compiler_path": compiler_path, "linker": linker,
            "python": platform.python_version(), "compiler_options": selected["compiler_options"],
            "source_sha256": source_hashes, "input_elf": input_elf,
            "runtime": "Linux x86-64; memfd_create + execveat; original interpreter/libraries if any",
            "runtime_external_tools": [], "runtime_validation": "caller_required",
            "observation_contract_excludes": ["self-file path and /proc/self/exe identity",
                                               "AT_EXECFN", "privileged-file semantics"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--filter", choices=("none", "bcj", "auto"), default="auto")
    options = parser.parse_args()
    print(json.dumps(pack_elf(options.input, options.output, cc=options.cc,
                              timeout=options.timeout, filter=options.filter), indent=2))


if __name__ == "__main__":
    main()
