"""Exec a revalidated runner with a PGN supplied by sealed Linux memfds.

This is a non-authorizing input-binding helper. It does not authenticate the
host, launcher, producer, engine inputs, dynamic libraries, GO, or outcome.
The source-fd access and mount checks do not establish equivalence to the
original pathname's LSM, integrity appraisal, or dynamic-linker policies.
Its inherited read-only contents may also be inherited by the runner's engine
children unless the reviewed Fastchess startup applies close-on-exec to it. A
later caller must own the process and verify these other boundaries.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import os
from pathlib import Path
import re
import stat
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
_MAX_RUNNER_BYTES = 64 << 20


def _private_memfd(name):
    """Create a close-on-exec memfd without occupying a standard stream."""
    fd = os.memfd_create(name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    if fd >= 3:
        return fd
    try:
        return fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 3)
    finally:
        os.close(fd)


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
    fd = _private_memfd("rove4k-opening")
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


def sealed_runner_snapshot(source, expected_sha256):
    """Freeze the exact plan-pinned ELF runner before executing its bytes.

    This binds the image to the plan's digest; it does not authenticate the
    plan, Python launcher, LSM/integrity policy, dynamic linker, host, or
    engine processes. The source execute-access check is not a claim that
    memfd execution preserves all pathname-based security policy.
    """
    if not _HAS_SEALS or os.execve not in getattr(os, "supports_fd", set()):
        raise RuntimeError("Linux sealed executable FD support is required")
    if type(expected_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValueError("runner SHA-256 pin required")
    source = diagnostic_candidates._check_path_components(source)
    if not source.is_absolute() or ".." in source.parts:
        raise ValueError("absolute runner path without parent traversal required")
    if not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "ST_NOEXEC", "fstatvfs")):
        raise RuntimeError("Linux executable path policy checks are required")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    directory, original = os.open(source.anchor, flags | os.O_DIRECTORY), None
    try:
        for component in source.parts[1:-1]:
            child = os.open(component, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        original = os.open(source.name, flags, dir_fd=directory)
        before = os.fstat(original)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                not 0 < before.st_size <= _MAX_RUNNER_BYTES):
            raise ValueError("bounded ordinary single-link runner required")
        # Copying a privilege-bearing ELF to memfd cannot preserve the
        # pathname's set-ID or file-capability exec semantics. Refuse it.
        if before.st_mode & (stat.S_ISUID | stat.S_ISGID):
            raise PermissionError("privilege-bearing runner is not supported")
        try:
            os.getxattr(original, "security.capability")
        except OSError as error:
            if error.errno not in {errno.ENODATA, errno.EOPNOTSUPP}:
                raise
        else:
            raise PermissionError("runner file capabilities are not supported")
        # Do not bypass the original mount's noexec or effective-user execute
        # permissions by copying bytes to an executable memfd. The procfs path
        # refers to the opened inode, not a subsequently replaced pathname.
        if (os.fstatvfs(original).f_flag & os.ST_NOEXEC or
                not os.access(f"/proc/self/fd/{original}", os.X_OK, effective_ids=True)):
            raise PermissionError("original runner is not executable in this context")
        with os.fdopen(original, "rb") as stream:
            original = None
            raw = stream.read(before.st_size + 1)
            after = os.fstat(stream.fileno())
        current = os.stat(source.name, dir_fd=directory, follow_symlinks=False)
        stamp = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
                               value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if stamp(before) != stamp(after) or stamp(before) != stamp(current) or len(raw) != before.st_size:
            raise ValueError("runner input identity changed during snapshot")
    finally:
        if original is not None:
            os.close(original)
        os.close(directory)
    if raw[:4] != b"\x7fELF" or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("runner ELF snapshot differs from its plan pin")
    fd = _private_memfd("rove4k-runner")
    try:
        os.fchmod(fd, 0o500)
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise OSError("runner memfd write made no progress")
            offset += written
        if os.fstat(fd).st_size != len(raw):
            raise ValueError("runner memfd length differs")
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, _REQUIRED_SEALS)
        if fcntl.fcntl(fd, fcntl.F_GET_SEALS) & _REQUIRED_SEALS != _REQUIRED_SEALS:
            raise RuntimeError("runner memfd seals are incomplete")
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), "rb") as stream:
            frozen = stream.read(len(raw) + 1)
        if frozen != raw or hashlib.sha256(frozen).hexdigest() != expected_sha256:
            raise ValueError("sealed runner memfd differs from its plan pin")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--bytes", type=int, required=True)
    parser.add_argument("--runner-sha256", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    fd = sealed_snapshot(args.source, {"sha256": args.sha256, "bytes": args.bytes})
    runner_fd = None
    try:
        command = command_with_fd(command, fd)
        runner_fd = sealed_runner_snapshot(command[0], args.runner_sha256)
        # PEP 446 makes new FDs close-on-exec. The runner must keep this one
        # alive until it opens its /proc/self/fd path.
        os.set_inheritable(fd, True)
        os.environ["ROVE_OPENING_FD"] = str(fd)
        os.execve(runner_fd, command, os.environ)
    finally:
        os.close(fd)
        if runner_fd is not None:
            os.close(runner_fd)


if __name__ == "__main__":
    main()
