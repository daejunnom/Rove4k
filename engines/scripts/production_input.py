"""Bounded POSIX reads for production evidence, not path discovery or writes.

Every ancestor is opened without following links.  The leaf is opened
nonblocking, then checked against the same regular inode before and after a
bounded read.  Installed compiler inputs may explicitly permit hardlinks.
This module fails closed on platforms without the required POSIX operations.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
_EXECUTING_CODE = sys._getframe().f_code
MODULE_NAME = "rove4k_production_input"
SOURCE_LIMIT = 1 << 20
_POSIX_FDS = (os.name == "posix" and all(hasattr(os, name) for name in
              ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"))
              and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd)


def require(value, detail):
    if not value:
        raise ValueError(detail)


def file_stamp(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def open_directory(path):
    """Return an owned directory fd reached from the absolute filesystem root."""
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "absolute directory path required")
    require(_POSIX_FDS,
            "POSIX no-follow file handles required for production evidence")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def same_directory(path, descriptor):
    """Reject a namespace replacement after a read through an anchored fd."""
    current = open_directory(path)
    try:
        before, after = os.fstat(descriptor), os.fstat(current)
        require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
                "production evidence parent directory changed during read")
    finally:
        os.close(current)


def read_regular_at(parent, name, *, limit, allow_hardlinks=False, expected=None):
    """Read one name below a caller-owned anchored directory fd.

    The caller retains ownership of ``parent`` and its enclosing namespace.
    ``expected`` optionally binds a stat result from an anchored directory scan.
    """
    require(isinstance(name, str) and name not in ("", ".", "..")
            and "/" not in name and "\\" not in name and "\0" not in name,
            "one ordinary evidence filename required")
    require(type(limit) is int and limit >= 0, "finite nonnegative evidence byte bound required")
    require(type(allow_hardlinks) is bool, "explicit evidence hardlink policy required")
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    require(expected is None or file_stamp(before) == file_stamp(expected),
            "production evidence changed since its directory scan")
    require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= limit
            and (before.st_nlink >= 1 if allow_hardlinks else before.st_nlink == 1),
            "bounded ordinary evidence file required")
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                         getattr(os, "O_CLOEXEC", 0), dir_fd=parent)
    try:
        require(file_stamp(os.fstat(descriptor)) == file_stamp(before),
                "production evidence changed before read")
        chunks, count = [], 0
        while count <= before.st_size:
            value = os.read(descriptor, min(1 << 16, before.st_size + 1 - count))
            if not value:
                break
            chunks.append(value)
            count += len(value)
        require(count == before.st_size
                and file_stamp(os.fstat(descriptor)) == file_stamp(before)
                and file_stamp(os.stat(name, dir_fd=parent, follow_symlinks=False)) == file_stamp(before),
                "production evidence changed during read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_regular(path, *, limit, allow_hardlinks=False):
    """Read a bounded stable regular file; never follow leaf or ancestor links."""
    path = Path(path)
    require(path.is_absolute() and path.name not in ("", ".", "..") and ".." not in path.parts,
            "absolute ordinary evidence file required")
    parent = open_directory(path.parent)
    try:
        data = read_regular_at(parent, path.name, limit=limit, allow_hardlinks=allow_hardlinks)
        same_directory(path.parent, parent)
        return data
    finally:
        os.close(parent)


def source_identity():
    """Return normalized source bytes matching this actually executing module."""
    data = read_regular(Path(__file__).absolute(), limit=SOURCE_LIMIT).replace(b"\r\n", b"\n")
    require(b"\r" not in data and compile(data, __file__, "exec", dont_inherit=True) == _EXECUTING_CODE,
            "production input reader source differs from its executing code")
    return data


def cached_module():
    """Return the canonical module identity used by all production consumers."""
    this = sys.modules[__name__]
    current = sys.modules.setdefault(MODULE_NAME, this)
    require(Path(current.__file__).absolute() == Path(__file__).absolute()
            and current._EXECUTING_CODE == _EXECUTING_CODE,
            "another production input reader occupies the canonical module name")
    return current
