"""Exec a runner with one revalidated PGN supplied by a sealed Linux memfd.

This is a non-authorizing input-binding helper. It does not authenticate the
host, launcher, runner, producer, other inputs, GO, or eventual game outcome.
Its inherited read-only contents may also be inherited by the runner's engine
children unless the reviewed Fastchess startup applies close-on-exec to it. A
later caller must own the process and verify these other boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    from . import diagnostic_candidates, opening_pgn
except ImportError:
    # This helper is also executed with Python -I; explicitly load only its
    # sibling source tree, rather than relying on cwd or PYTHONPATH.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import diagnostic_candidates
    import opening_pgn


PLACEHOLDER = "/__rove4k_sealed_opening_snapshot_v1__"
_SEAL_NAMES = ("F_SEAL_SEAL", "F_SEAL_SHRINK", "F_SEAL_GROW", "F_SEAL_WRITE", "F_ADD_SEALS", "F_GET_SEALS")
_HAS_SEALS = sys.platform == "linux" and fcntl is not None and all(hasattr(fcntl, name) for name in _SEAL_NAMES)
_REQUIRED_SEALS = (fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
                   if _HAS_SEALS else 0)


def sealed_snapshot(source, pin):
    """Return an owned, sealed FD for a fresh snapshot matching the plan pin.

    Revalidating the SHA and length binds the contents to the earlier plan's
    canonical snapshot; it does not freeze the original pathname. Failures
    close only the FD created by this function. Linux and procfs are required.
    """
    if not _HAS_SEALS or not all(hasattr(os, name) for name in ("memfd_create", "MFD_CLOEXEC", "MFD_ALLOW_SEALING")):
        raise RuntimeError("Linux sealed memfd support is required")
    source = diagnostic_candidates._check_path_components(source)
    raw = opening_pgn.read_snapshot(source, pin)
    fd = os.memfd_create("rove4k-opening", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise OSError("opening memfd write made no progress")
            offset += written
        if os.fstat(fd).st_size != len(raw):
            raise ValueError("opening memfd length differs")
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, _REQUIRED_SEALS)
        if fcntl.fcntl(fd, fcntl.F_GET_SEALS) & _REQUIRED_SEALS != _REQUIRED_SEALS:
            raise RuntimeError("opening memfd seals are incomplete")
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), "rb") as stream:
            frozen = stream.read(len(raw) + 1)
        if frozen != raw or hashlib.sha256(frozen).hexdigest() != pin["sha256"]:
            raise ValueError("sealed opening memfd differs from the plan pin")
        # procfs opens an independent read handle; verify it resolves before
        # exec, rather than silently falling back to the original path.
        with open(f"/proc/self/fd/{fd}", "rb") as stream:
            if stream.read(len(raw) + 1) != raw:
                raise ValueError("procfs opening handle differs")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def command_with_fd(command, fd):
    """Replace exactly the reserved Fastchess opening argument with this FD."""
    if (type(command) not in (tuple, list) or not command or
            any(type(item) is not str or "\x00" in item for item in command) or
            not Path(command[0]).is_absolute() or type(fd) is not int or fd < 0):
        raise ValueError("absolute runner command and valid FD required")
    placeholder = "file=" + PLACEHOLDER
    if (command.count(placeholder) != 1 or command.count("-openings") != 1 or
            command.index(placeholder) != command.index("-openings") + 1):
        raise ValueError("one reserved Fastchess opening argument is required")
    start = command.index("-openings") + 1
    end = next((i for i in range(start, len(command)) if command[i].startswith("-")), len(command))
    if [item for item in command[start:end] if item.startswith("file=")] != [placeholder]:
        raise ValueError("duplicate Fastchess opening files are not permitted")
    return ["file=/proc/self/fd/" + str(fd) if item == placeholder else item for item in command]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--bytes", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    fd = sealed_snapshot(args.source, {"sha256": args.sha256, "bytes": args.bytes})
    try:
        command = command_with_fd(command, fd)
        # PEP 446 makes new FDs close-on-exec. The runner must keep this one
        # alive until it opens its /proc/self/fd path.
        os.set_inheritable(fd, True)
        os.environ["ROVE_OPENING_FD"] = str(fd)
        os.execv(command[0], command)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
