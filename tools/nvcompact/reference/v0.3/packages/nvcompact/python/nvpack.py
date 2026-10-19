"""Reproducible native-ELF packing candidates, with no filesystem extraction.

This is an artifact builder, not a proof of program equivalence.  Each packed
candidate is a general TCEC 4k *script* profile, NOT the separate ELF-only
profile.  Its only external programs are /bin/sh and python3.  It requires
Linux, /proc/self/status, Python >= 3.8 with the selected standard-library
codec, os.memfd_create, fd-based os.execve, and policy permitting memfd exec.

The loader preserves argv[1:], binary stdin/stdout/stderr, exit status, the
process ID after exec, inherited SIGPIPE/SIGXFSZ ignore dispositions, and the
pre-Python LC_CTYPE environment setting.  Its argv[0] is the script invocation
path.  Custom execve argv[0], self-file inspection, /proc/self/exe identity,
$ORIGIN-relative shared libraries, privileged executables, exact startup
timing, and arbitrary shell/interpreter process observations are outside this
profile.  Use the raw candidate when those observations matter.  A deployment
verifier must test the complete final artifact against its actual contract.

No temporary pathname is created, no background deletion timer is used, and
no rm command is assumed.  A close-on-exec anonymous descriptor is written in
full before exec.  Failures remain nonzero, with the underlying diagnostic;
there is no fallback to executing partially decoded bytes.

Reproduction is with pinned Python/codec implementations and this builder.
The codec roundtrip flag proves byte restoration only.  It does not claim
that an upstream source/link transformation preserved program semantics.
"""

from __future__ import annotations

import bz2
import gzip
import io
import lzma
import struct
import zlib
from typing import Any


CODEC_GROUPS: dict[str, tuple[str, ...]] = {
    "raw": ("raw",),
    "gzip": ("gzip-1", "gzip-9"),
    "zlib": ("zlib-1", "zlib-9"),
    "bzip2": ("bzip2-1", "bzip2-9"),
    "xz": ("xz-0", "xz-6", "xz-9"),
    "xz-bcj": ("xz-bcj-0", "xz-bcj-6", "xz-bcj-9"),
    "lzma": ("lzma-0", "lzma-6", "lzma-9"),
}

_DEFAULT_GROUPS = ("gzip", "zlib", "bzip2", "xz", "lzma")
_EXACT_IDS = frozenset(item for group in CODEC_GROUPS.values() for item in group)
_PROFILE = "linux-script-python-memfd"


def _x86_64(target: str) -> bool:
    normalized = target.lower().replace("amd64", "x86_64")
    return "linux" in normalized and "x86_64" in normalized


def _check_elf(raw_bytes: bytes, target: str) -> None:
    if not isinstance(raw_bytes, bytes):
        raise TypeError("raw_bytes must be bytes")
    if not isinstance(target, str) or "linux" not in target.lower():
        raise ValueError("this packer supports declared Linux ELF targets only")
    if len(raw_bytes) < 52 or raw_bytes[:4] != b"\x7fELF":
        raise ValueError("native packing requires an ELF executable, not a script")
    elf_class, byte_order, version = raw_bytes[4:7]
    if elf_class not in (1, 2) or byte_order not in (1, 2) or version != 1:
        raise ValueError("invalid or unsupported ELF identification")
    if elf_class == 2 and len(raw_bytes) < 64:
        raise ValueError("truncated ELF64 header")
    elf_type, machine = struct.unpack_from("<HH" if byte_order == 1 else ">HH", raw_bytes, 16)
    if elf_type not in (2, 3):
        raise ValueError("ELF input must be ET_EXEC or ET_DYN, not a relocatable object")
    # This is a target sanity check, not a replacement for the linker's ELF
    # audit or the deployment verifier.  BCJ is never inferred from bytes alone.
    if _x86_64(target) and (elf_class != 2 or byte_order != 1 or machine != 62):
        raise ValueError("declared x86_64 Linux target disagrees with the ELF header")


def candidate_ids(target: str, codecs: list[str] | None = None) -> list[str]:
    """Expand families or exact IDs in a stable order; raw is always first.

    An empty list selects only raw.  An explicit xz-bcj request for another
    architecture is an error, rather than a silent reduction of the search.
    """
    if not isinstance(target, str) or "linux" not in target.lower():
        raise ValueError("this packer supports declared Linux ELF targets only")
    if codecs is not None and not isinstance(codecs, list):
        raise TypeError("codecs must be a list of families/exact IDs, or None")
    requests = list(_DEFAULT_GROUPS) if codecs is None else codecs
    if codecs is None and _x86_64(target):
        requests.append("xz-bcj")
    result = ["raw"]
    for request in requests:
        if not isinstance(request, str):
            raise TypeError("codec requests must be strings")
        if request in CODEC_GROUPS:
            expanded = CODEC_GROUPS[request]
        elif request in _EXACT_IDS:
            expanded = (request,)
        else:
            raise ValueError(f"unknown packing codec or exact ID: {request!r}")
        for pack_id in expanded:
            if pack_id.startswith("xz-bcj-") and not _x86_64(target):
                raise ValueError("x86 BCJ requires an explicitly declared x86_64 Linux target")
            if pack_id not in result:
                result.append(pack_id)
    return result


def _dictionary_size(input_length: int, level: int) -> int:
    # A dictionary cannot match history preceding the beginning of the input.
    # Keep the preset's maximum, but avoid declaring 64 MiB for a tiny ELF.
    preset_limit = {0: 1 << 18, 6: 1 << 23, 9: 1 << 26}[level]
    covering_power_of_two = 1 << max(12, (input_length - 1).bit_length())
    return min(preset_limit, covering_power_of_two)


def _compress(raw_bytes: bytes, pack_id: str) -> tuple[bytes, str, dict[str, Any]]:
    level = int(pack_id.rsplit("-", 1)[1])
    if pack_id.startswith("gzip-"):
        # GzipFile fixes OS=255 as well as the empty filename and mtime=0.
        # gzip.compress(mtime=0) has had version-dependent OS header behavior.
        buffer = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, compresslevel=level, mtime=0) as stream:
            stream.write(raw_bytes)
        payload = buffer.getvalue()
        restored = gzip.decompress(payload)
        module = "gzip"
        recipe: dict[str, Any] = {"format": "gzip", "level": level, "mtime": 0, "filename": ""}
    elif pack_id.startswith("bzip2-"):
        payload = bz2.compress(raw_bytes, compresslevel=level)
        restored = bz2.decompress(payload)
        module = "bz2"
        recipe = {"format": "bzip2", "level": level}
    elif pack_id.startswith("zlib-"):
        # Same DEFLATE codec family as gzip, with smaller deterministic framing
        # and an Adler-32 integrity check.  Compare the full runnable wrapper.
        payload = zlib.compress(raw_bytes, level=level)
        restored = zlib.decompress(payload)
        module = "zlib"
        recipe = {"format": "zlib", "level": level, "check": "adler32"}
    else:
        alone = pack_id.startswith("lzma-")
        bcj = pack_id.startswith("xz-bcj-")
        dictionary = _dictionary_size(len(raw_bytes), level)
        filters: list[dict[str, int]] = []
        if bcj:
            filters.append({"id": lzma.FILTER_X86})
        filters.append({"id": lzma.FILTER_LZMA1 if alone else lzma.FILTER_LZMA2,
                        "preset": level, "dict_size": dictionary})
        if alone:
            payload = lzma.compress(raw_bytes, format=lzma.FORMAT_ALONE, filters=filters)
        else:
            payload = lzma.compress(raw_bytes, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC32, filters=filters)
        restored = lzma.decompress(payload, format=lzma.FORMAT_ALONE if alone else lzma.FORMAT_XZ)
        module = "lzma"
        recipe = {"format": "lzma-alone" if alone else "xz", "level": level,
                  "dict_size": dictionary, "bcj": "x86" if bcj else None,
                  "check": "none" if alone else "crc32"}
    if restored != raw_bytes:
        raise RuntimeError(f"codec roundtrip failed for {pack_id}; artifact not generated")
    return payload, module, recipe


def _loader(module: str, offset: int) -> bytes:
    # Capture inherited ignore dispositions *before* Python changes SIGPIPE
    # and SIGXFSZ.  /proc/self avoids relying on a virtualized shell PID.
    # Preserve LC_CTYPE because Python may coerce a C locale at startup.
    python = (
        f"import os,sys,signal,{module}\n"
        "a=sys.argv;m=int(a[1],16);e=os.environ;k=\"LC_CTYPE\"\n"
        "if a[2]:e[k]=a[3]\n"
        "else:e.pop(k,None)\n"
        "a=a[4:]\n"
        f"with open(a[0],\"rb\") as p:p.seek({offset});d={module}.decompress(p.read())\n"
        "f=os.memfd_create(\"\",os.MFD_CLOEXEC)\n"
        # BufferedWriter completes short writes (or raises); the with block
        # flushes before exec while closefd=False keeps the CLOEXEC fd usable.
        "with os.fdopen(f,\"wb\",closefd=False) as w:w.write(d)\n"
        "os.fchmod(f,0o500)\n"
        "for s in (signal.SIGPIPE,signal.SIGXFSZ):signal.signal(s,signal.SIG_IGN if m>>(s-1)&1 else signal.SIG_DFL)\n"
        "os.execve(f,a,e)"
    )
    # All Python string literals use double quotes.  No untrusted source text,
    # path, or argument is interpolated into this single-quoted shell program.
    if "'" in python:
        raise AssertionError("internal loader quoting error")
    shell = (
        "#!/bin/sh\n"
        # read's k/v bindings are confined to a subshell.  Otherwise caller-
        # exported variables with those names would leak modified values into
        # the ELF environment, even though they are only loader temporaries.
        f"exec python3 -I -S -c '{python}' "
        "\"$(while read k v;do [ \"$k\" = SigIgn: ]&&{ printf %s \"$v\";break;};done</proc/self/status)\" "
        "\"${LC_CTYPE+x}\" \"${LC_CTYPE-}\" \"$0\" \"$@\"\n"
        "exit 127\n"
    )
    return shell.encode("ascii")


def _wrap(payload: bytes, module: str) -> tuple[bytes, int]:
    # The offset's decimal digits contribute to the header length.  Compute
    # the fixed point instead of embedding a hand-counted tail/seek constant.
    offset = 0
    while True:
        header = _loader(module, offset)
        actual = len(header)
        if actual == offset:
            return header + payload, actual
        if actual < offset:
            raise RuntimeError("non-monotone internal loader layout")
        offset = actual


def pack_variants(raw_bytes: bytes, *, target: str,
                  codecs: list[str] | None = None) -> list[dict[str, Any]]:
    """Generate and byte-roundtrip-check complete runnable artifact candidates.

    Selection is deliberately left to the caller, which must also check the
    complete artifact's executable behavior and deployment requirements.
    ``payload_bytes`` and ``loader_bytes`` are descriptive; compare ``data``'s
    full length.  Errors are raised instead of being relabeled as an ordinary
    larger candidate.  Exact selected IDs can be regenerated with pack_by_id.
    """
    _check_elf(raw_bytes, target)
    ids = candidate_ids(target, codecs)
    result: list[dict[str, Any]] = []
    for pack_id in ids:
        if pack_id == "raw":
            result.append({"id": "raw", "data": raw_bytes,
                           "payload_bytes": len(raw_bytes), "loader_bytes": 0,
                           "payload_offset": 0, "requirements": ["declared Linux ELF ABI"],
                           "runtime_profile": "native-elf", "roundtrip_verified": True,
                           "codec": {"format": "identity"}})
            continue
        payload, module, recipe = _compress(raw_bytes, pack_id)
        artifact, offset = _wrap(payload, module)
        # Verify the actual slicing used by the generated loader, not merely
        # the codec's in-memory input before it was embedded in the wrapper.
        decoder = {"gzip": gzip.decompress, "zlib": zlib.decompress,
                   "bz2": bz2.decompress, "lzma": lzma.decompress}[module]
        if decoder(artifact[offset:]) != raw_bytes:
            raise RuntimeError(f"embedded payload roundtrip failed for {pack_id}")
        result.append({"id": pack_id, "data": artifact,
                       "payload_bytes": len(payload), "loader_bytes": offset,
                       "payload_offset": offset,
                       "requirements": ["/bin/sh with POSIX builtins", "python3 >= 3.8",
                                        f"Python standard library {module}", "/proc/self/status",
                                        "Linux memfd_create and fd exec permitted",
                                        "declared Linux ELF ABI"],
                       "runtime_profile": _PROFILE, "roundtrip_verified": True,
                       "codec": recipe})
    return result


def pack_by_id(raw_bytes: bytes, *, target: str, pack_id: str) -> dict[str, Any]:
    """Reproduce one exact selected packing recipe; family aliases are rejected."""
    if pack_id not in _EXACT_IDS:
        raise ValueError(f"pack_by_id requires an exact candidate ID, got {pack_id!r}")
    return next(candidate for candidate in pack_variants(raw_bytes, target=target, codecs=[pack_id])
                if candidate["id"] == pack_id)
