#!/usr/bin/env python3
"""Execute a fully linked/wrapped example against an independent integer oracle.

This is finite evidence for the documented scalar contract, not a proof for all
2**64 bitboards or an automatic cross-language equivalence checker. Linux/POSIX
execution is intentional. No shell command string or candidate vote is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import tempfile
import time


MASK = (1 << 64) - 1
RECORD = struct.Struct("<QII")
ANSWER = struct.Struct("<Ii")


def expected(bits: int, square: int) -> bytes:
    file, rank = square % 8, square // 8
    # Independent from the implementations' edge-distance/table/abs(2*x-7).
    distance = min(abs(file - f) + abs(rank - r)
                   for f, r in ((3, 3), (3, 4), (4, 3), (4, 4)))
    return ANSWER.pack(bits.bit_count(), 6 - 2 * distance)


def corpus(quick: bool) -> tuple[bytes, bytes, int]:
    data, answers = bytearray(), bytearray()

    def add(bits: int, square: int) -> None:
        data.extend(RECORD.pack(bits, square, 0))
        answers.extend(expected(bits, square))

    edges = [0, MASK, 1, 1 << 63, 0xAAAAAAAAAAAAAAAA,
             0x5555555555555555, 0x8000000000000001,
             0xFFFFFFFF, 0xFFFFFFFF00000000]
    for square in range(64):
        for bits in edges:
            add(bits, square)
        add(1 << square, square)
        add(MASK ^ (1 << square), square)

    if not quick:
        for high in (0, 0x8000000000000000, 0xFFFFFFFFFFFF0000):
            for low in range(1 << 16):
                add(high | low, low % 64)

    # Explicit fixed integer PRNG, independent of Python's random version.
    state = 0xA32F9071D81BC405
    for index in range(512 if quick else 2048):
        state ^= state << 13 & MASK
        state ^= state >> 7
        state ^= state << 17 & MASK
        state &= MASK
        add(state, index % 64)
    return bytes(data), bytes(answers), len(data) // RECORD.size


def run_case(binary: Path, data: bytes, output: bytes, code: int,
             deadline: float, label: str) -> None:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError("verifier time budget exhausted before " + label)
    # RLIMIT_FSIZE bounds both captured files even if a candidate writes forever.
    # This limit is for this small example contract, not arbitrary engine outputs.
    cap = max(len(output) + 1024, 65536)

    def child_limits() -> None:
        resource.setrlimit(resource.RLIMIT_FSIZE, (cap, cap))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU,
                           (max(1, math.ceil(remaining)),
                            max(2, math.ceil(remaining) + 1)))
        resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))

    with tempfile.TemporaryFile() as inp, tempfile.TemporaryFile() as out, \
            tempfile.TemporaryFile() as err:
        inp.write(data)
        inp.seek(0)
        process = subprocess.Popen([str(binary)], stdin=inp, stdout=out,
                                   stderr=err, start_new_session=True,
                                   preexec_fn=child_limits)
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            raise RuntimeError("candidate timed out: " + label) from None
        finally:
            # Signal this execution's own group, then reap its direct leader.
            # This is not a sandbox or a proof that detached descendants exited;
            # the example and accepted wrappers must not daemonize/detach.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        out.seek(0)
        actual = out.read(len(output) + 1)
        out_size = os.fstat(out.fileno()).st_size
        if returncode != code or out_size != len(output) or actual != output:
            err.seek(0)
            detail = err.read(400).decode("utf-8", "backslashreplace")
            first = next((i for i, (a, b) in enumerate(zip(actual, output))
                          if a != b), min(len(actual), len(output)))
            raise RuntimeError(
                f"{label}: exit={returncode}, expected_exit={code}, "
                f"stdout_bytes={out_size}, expected_bytes={len(output)}, "
                f"first_difference={first}, stderr={detail!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--timeout", type=float, default=20.0,
                        help="total seconds for corpus construction and all cases")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be positive and finite")
    started = time.monotonic()
    deadline = started + args.timeout
    cases = 0
    try:
        binary = args.binary.resolve(strict=True)
        data, answers, records = corpus(args.quick)
        run_case(binary, data, answers, 0, deadline, "integer corpus")
        cases += 1
        run_case(binary, b"", b"", 0, deadline, "empty stream")
        cases += 1
        good = RECORD.pack(0x8000000000000001, 27, 0)
        for length in ([1, 15] if args.quick else range(1, 16)):
            run_case(binary, good[:length], b"", 2, deadline,
                     f"truncated record ({length} bytes)")
            cases += 1
        run_case(binary, good + b"\0", expected(0x8000000000000001, 27),
                 2, deadline, "valid prefix then truncated record")
        cases += 1
        for square, flags in ((64, 0), (0xFFFFFFFF, 0), (0, 1), (63, 0xFFFFFFFF)):
            run_case(binary, RECORD.pack(MASK, square, flags), b"", 2,
                     deadline, f"invalid square/flags ({square}, {flags})")
            cases += 1
        print(json.dumps({"ok": True, "mode": "quick" if args.quick else "full",
                          "cases": cases, "valid_records": records,
                          "corpus_sha256": hashlib.sha256(data).hexdigest(),
                          "oracle_sha256": hashlib.sha256(answers).hexdigest(),
                          "elapsed_seconds": round(time.monotonic() - started, 6)},
                         sort_keys=True))
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "completed_cases": cases,
                          "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
