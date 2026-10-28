"""Build-only LZMA1EXT trial; no submission or runtime qualification.

The caller compiles peer_lzma1ext_trial.c against liblzma and supplies the
resulting executable and xz.  This module does not download tools or execute
an engine. Two calls to the same identified helper are compared, and the
output is checked with Python's .lzma decoder and the external xz executable.
These decoders may use the same liblzma implementation.
The limits below apply to the directly executed Linux helper and xz processes;
they are not a sandbox for arbitrary helpers or their descendants. The caller
must also ensure that sufficient physical RAM is available before starting.
"""

from __future__ import annotations

import hashlib
import lzma
import re
import subprocess
import sys
import tempfile
from pathlib import Path

INPUT_LIMIT = 1 << 20
DECODER_LIMIT = 128 << 20
OUTPUT_LIMIT = 2 * INPUT_LIMIT + 4096
PROCESS_MEMORY_LIMIT = 1536 << 20
_VERSION = re.compile(
    rb"header=([^\s]+) runtime=([^\s]+) header_number=([0-9]+) "
    rb"runtime_number=([0-9]+) ext=([01])\n"
)
_FINDERS = (lzma.MF_HC3, lzma.MF_HC4, lzma.MF_BT2, lzma.MF_BT3, lzma.MF_BT4)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(argv, *, data=b"", timeout=60):
    if sys.platform != "linux":
        raise ValueError("bounded LZMA1EXT trials require Linux")
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ValueError("invalid trial timeout")
    import resource

    def lower_limit(which, wanted):
        soft, hard = resource.getrlimit(which)
        if soft != resource.RLIM_INFINITY:
            wanted = min(wanted, soft)
        if hard != resource.RLIM_INFINITY:
            wanted = min(wanted, hard)
        resource.setrlimit(which, (wanted, hard))

    def limits():
        lower_limit(resource.RLIMIT_AS, PROCESS_MEMORY_LIMIT)
        lower_limit(resource.RLIMIT_FSIZE, OUTPUT_LIMIT)
        lower_limit(resource.RLIMIT_CPU, timeout + 1)

    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            result = subprocess.run(argv, input=data, stdout=stdout, stderr=stderr,
                                    timeout=timeout, check=False, preexec_fn=limits)
            if result.returncode:
                raise ValueError("trial tool failed with exit code " + str(result.returncode))
            stdout.seek(0)
            output = stdout.read(OUTPUT_LIMIT + 1)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("trial tool could not complete") from error
    if len(output) > OUTPUT_LIMIT:
        raise ValueError("trial tool exceeded output limit")
    return output


def _parameters(lc, lp, pb, mf, nice, dict_size, depth):
    values = (lc, lp, pb, mf, nice, dict_size, depth)
    if any(type(value) is not int for value in values):
        raise ValueError("trial parameters must be integers")
    is_power_of_two = lambda value: value > 0 and not value & (value - 1)
    standard_dict = is_power_of_two(dict_size) or (
        dict_size % 3 == 0 and is_power_of_two(dict_size // 3))
    if not (0 <= lc <= 4 and 0 <= lp <= 4 and lc + lp <= 4 and 0 <= pb <= 4
            and mf in _FINDERS and 8 <= nice <= 273
            and 4096 <= dict_size <= (64 << 20) and standard_dict
            and 0 <= depth <= 100000):
        raise ValueError("invalid LZMA1EXT trial parameters")
    return values


def encode_verified(data: bytes, *, helper: str | Path, xz: str | Path,
                    lc=2, lp=0, pb=0, mf=lzma.MF_BT4, nice=128,
                    dict_size=64 << 20, depth=0, timeout=60):
    """Return verified stream and diagnostic receipt, without executing an engine."""
    if type(data) is not bytes or len(data) > INPUT_LIMIT:
        raise ValueError("trial source must be bounded bytes")
    values = _parameters(lc, lp, pb, mf, nice, dict_size, depth)
    helper = Path(helper).resolve(strict=True)
    if not helper.is_file():
        raise ValueError("helper must be an existing executable")
    helper_sha = _sha(helper.read_bytes())
    helper_source = Path(__file__).with_suffix(".c")
    helper_source_sha = _sha(helper_source.read_bytes())
    xz = str(xz)
    version = _run([str(helper), "--version"], timeout=timeout)
    match = _VERSION.fullmatch(version)
    if not match or match.group(5) != b"1":
        raise ValueError("LZMA1EXT unavailable or invalid version response")
    command = [str(helper), *(str(value) for value in values)]
    payload = _run(command, data=data, timeout=timeout)
    if payload != _run(command, data=data, timeout=timeout):
        raise ValueError("LZMA1EXT encoding was not reproducible")
    if _sha(helper.read_bytes()) != helper_sha:
        raise ValueError("LZMA1EXT helper changed during trial")
    if _sha(helper_source.read_bytes()) != helper_source_sha:
        raise ValueError("LZMA1EXT helper source changed during trial")
    if len(payload) < 13 or len(payload) > 2 * len(data) + 4096:
        raise ValueError("LZMA1EXT stream size is outside the trial bound")
    if (payload[0] != (pb * 5 + lp) * 9 + lc
            or int.from_bytes(payload[1:5], "little") != dict_size
            or int.from_bytes(payload[5:13], "little") != len(data)):
        raise ValueError("LZMA1EXT stream header differs from requested settings")
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=DECODER_LIMIT)
        restored = decoder.decompress(payload, max_length=len(data) + 1)
    except lzma.LZMAError as error:
        raise ValueError("Python .lzma decoder rejected trial stream") from error
    if restored != data or not decoder.eof or decoder.unused_data:
        raise ValueError("Python .lzma restore differs or has trailing data")
    xz_version = _run([xz, "--version"], timeout=timeout)
    if _run([xz, "-d"],
            data=payload, timeout=timeout) != data:
        raise ValueError("xz .lzma restore differs")
    receipt = {
        "format": "peer-lzma1ext-trial-v1",
        "scope": "build-only diagnostic; no engine or league qualification",
        "input": {"bytes": len(data), "sha256": _sha(data)},
        "payload": {"bytes": len(payload), "sha256": _sha(payload)},
        "settings": dict(zip(("lc", "lp", "pb", "mf", "nice", "dict_size", "depth"), values)),
        "helper_sha256": helper_sha,
        "helper_source_sha256": helper_source_sha,
        "helper_build_provenance_verified": False,
        "liblzma_header": match.group(1).decode("ascii"),
        "liblzma_runtime": match.group(2).decode("ascii"),
        "liblzma_header_number": int(match.group(3)),
        "liblzma_runtime_number": int(match.group(4)),
        "xz_version": xz_version.decode("utf-8", "strict").strip(),
        "repeatable_same_helper": True,
        "independent_build_reproducible": False,
        "python_and_xz_restore_verified": True,
        "runtime_qualified": False,
        "league_qualified": False,
    }
    return payload, receipt
