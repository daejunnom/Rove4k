"""Prepare an unchanged upstream OpenBench peer for TEST diagnostics.

Only upstream source files whose Git blobs are pinned in ``peers`` are used.
Snapshots and binaries must stay outside Git checkouts.  These records identify
bytes and compile attempts; they do not authenticate a host or toolchain, prove
the actual TT layout, authorize a UCI process, or admit a scored game.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import sys

sys.dont_write_bytecode = True
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import peers, peer_exact_runner
except ImportError:
    import peers
    import peer_exact_runner

MAX_SOURCE_BYTES = 1 << 20
MAX_NATIVE_BYTES = 64 << 20
MAX_COMPILER_BYTES = 64 << 20
_ORIGINAL_QUARANTINE = []
_PROFILES = {
    "test-p16": {"workers": 16, "hash_mib": 16384, "expected_tt_bytes_if_entry8": 16 << 30},
    "test-p192": {"workers": 192, "hash_mib": 262144, "expected_tt_bytes_if_entry8": 256 << 30},
}
_FLAGS = {
    "ice4": ("-DOPENBENCH", "-g", "-O3", "-pthread"),
    "c4ke": ("-DNDEBUG", "-std=c++23", "-O3", "-march=native", "-pthread"),
}


def source_names(peer):
    """The original source closure; no minifier, resource patch or generated input."""
    peers.peer_spec(peer)
    names = tuple(sorted(name for name in peers.SOURCE_BLOBS[peer] if name.startswith("src/")))
    if (len(names) != {"ice4": 8, "c4ke": 5}[peer] or "src/main.cpp" not in names or
            any(name.count("/") != 1 or not name.endswith(".cpp") for name in names)):
        raise ValueError("pinned upstream source closure differs")
    return names


def source_record(peer, profile, files):
    """Check exact pinned blobs and return a non-authorizing source/build plan."""
    spec = peers.peer_spec(peer)
    if profile not in _PROFILES or type(files) is not dict or set(files) != set(source_names(peer)):
        raise ValueError("a complete original peer source and P16/P192 profile are required")
    entries = {}
    for name in source_names(peer):
        data = files[name]
        if type(data) is not bytes or not 0 < len(data) <= MAX_SOURCE_BYTES:
            raise ValueError("invalid bounded upstream source input")
        peers.verify_blob(peer, name, data)
        entries[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                         "git_blob": peers.git_blob(data)}
    return {
        "format": "rove4k-original-peer-source-v1", "purpose": "test-only",
        "peer": peer, "revision": spec.revision, "profile": profile,
        "source": entries, "source_closure_sha256": peers.sha(peers.canonical(entries)),
        "build": {"compiler": "g++", "flags": list(_FLAGS[peer]), "input": "src/main.cpp",
                  "upstream_source_modified": False, "planning_only": True,
                  "execution_available": False,
                  "scope": "this source snapshot is a plan; a separate diagnostic build can be attempted",
                  "blockers": ["this source-only plan does not establish compiler output FD ownership",
                               "this source-only plan does not establish child settlement",
                               "supervisor death, escaped descendants and same-UID mutation are unproved"]},
        "requested_uci": dict(_PROFILES[profile]),
        "qualification": {"source_blob_identity_checked": True, "compiler_authenticated": False,
                          "source_to_native_proven": False, "tt_abi_verified": False,
                          "allocation_observed": False, "runtime_qualified": False,
                          "league_qualified": False, "scored_game_admitted": False},
        "limitations": ["8-byte TT entry is an unverified target ABI assumption",
                        "same-UID concurrent modifications and compiler provenance are not excluded",
                        "original process-group observation does not prove escaped descendants settled",
                        "readyok cannot establish allocation or actual worker placement"],
    }


def compile_argv(peer, output):
    """Return a non-executable plan for flags and a reserved output basename.

    This path-based command is unsafe to execute: a future compiler supervisor
    must pin and retain the output FD rather than trust its pathname.
    """
    peers.peer_spec(peer)
    if output not in ("peer-native-1", "peer-native-2"):
        raise ValueError("invalid private output name")
    return ["g++", *_FLAGS[peer], "src/main.cpp", "-o", output]


def _linux():
    if sys.platform != "linux" or not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY")):
        raise ValueError("Linux no-follow directory access is required")


def _read_regular(directory_fd, name, limit):
    if "/" in name or name in ("", ".", ".."):
        raise ValueError("invalid direct file name")
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= limit:
            raise ValueError("bounded regular input with one link required")
        chunks, remaining = [], before.st_size
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                raise ValueError("short input")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        linked = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
                                  value.st_ctime_ns, value.st_nlink)
        if identity(before) != identity(after) or (after.st_dev, after.st_ino) != (linked.st_dev, linked.st_ino):
            raise ValueError("file changed during bounded read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_sources(peer, root):
    fd = peer_exact_runner._open_directory(Path(root) / "src")
    try:
        return {name: _read_regular(fd, name.split("/", 1)[1], MAX_SOURCE_BYTES)
                for name in source_names(peer)}
    finally:
        os.close(fd)


def _outside_checkout(path):
    path = _protected_path(path)
    if not path.name or path.name in (".", ".."):
        raise ValueError("new absolute external output required")
    for ancestor in (path, *path.parents):
        try:
            os.lstat(ancestor / ".git")
        except FileNotFoundError:
            continue
        raise ValueError("foreign source and native must stay outside Git checkouts")
    return path


def _protected_path(path):
    """Reject protected components before inspecting any filesystem path."""
    path = peer_exact_runner._safe_path(path)
    for part in path.parts:
        lower = part.casefold()
        if any(word in lower for word in ("secret", "access_key", "access-key", "serviceaccount")):
            raise ValueError("protected source or output path")
    if path.suffix.casefold() in (".pem", ".key", ".p12", ".pfx"):
        raise ValueError("protected source or output path")
    return path


def _write_exclusive(directory_fd, name, data, mode=0o600):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=directory_fd)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short output write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _stat_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_owned_fd(fd, maximum, *, allow_empty=False):
    """Read an existing regular descriptor without advancing its file offset."""
    before = os.fstat(fd)
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            not (0 if allow_empty else 1) <= before.st_size <= maximum):
        raise ValueError("bounded owned regular file required")
    chunks, offset = [], 0
    while offset < before.st_size:
        chunk = os.pread(fd, min(65536, before.st_size - offset), offset)
        if not chunk:
            raise ValueError("owned file became shorter")
        chunks.append(chunk)
        offset += len(chunk)
    if _stat_identity(before) != _stat_identity(os.fstat(fd)):
        raise ValueError("owned file changed while reading")
    return b"".join(chunks)


def _open_compiler():
    """Open a bounded, no-follow compiler executable and pin its bytes."""
    found = shutil.which("g++", path=peer_exact_runner._path_env())
    if found is None:
        raise ValueError("upstream g++ compiler unavailable")
    _protected_path(found)
    path = _protected_path(Path(found).resolve(strict=True))
    parent = peer_exact_runner._open_directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        data = _read_owned_fd(fd, MAX_COMPILER_BYTES)
        info = os.fstat(fd)
        if not info.st_mode & 0o111:
            raise ValueError("upstream compiler is not executable")
        result = (str(path), hashlib.sha256(data).hexdigest(), len(data), fd)
        fd = None
        return result
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _guard_output_path(out, parent_fd, out_fd):
    """Check held and named directory identities without following a link."""
    reopened = peer_exact_runner._open_directory(out.parent)
    try:
        parent, current_parent = os.fstat(parent_fd), os.fstat(reopened)
        if (parent.st_dev, parent.st_ino) != (current_parent.st_dev, current_parent.st_ino):
            raise ValueError("output parent path changed")
    finally:
        os.close(reopened)
    held = os.fstat(out_fd)
    linked = os.stat(out.name, dir_fd=parent_fd, follow_symlinks=False)
    if (not stat.S_ISDIR(held.st_mode) or not stat.S_ISDIR(linked.st_mode) or
            (held.st_dev, held.st_ino) != (linked.st_dev, linked.st_ino) or
            held.st_uid != os.geteuid() or stat.S_IMODE(held.st_mode) != 0o700):
        raise ValueError("owned output path changed")


def _snapshot_pins(peer, out_fd, expected):
    """Compare pinned original source bytes and named inode identities."""
    source_fd = os.open("src", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=out_fd)
    try:
        directory = os.fstat(source_fd)
        named = os.stat("src", dir_fd=out_fd, follow_symlinks=False)
        if (not stat.S_ISDIR(named.st_mode) or
                (directory.st_dev, directory.st_ino) != (named.st_dev, named.st_ino) or
                directory.st_uid != os.geteuid() or stat.S_IMODE(directory.st_mode) != 0o700):
            raise ValueError("snapshot changed: source directory differs")
        basenames = {name.split("/", 1)[1] for name in source_names(peer)}
        if set(os.listdir(source_fd)) != basenames:
            raise ValueError("snapshot changed: source closure differs")
        result = {"directory": (directory.st_dev, directory.st_ino), "files": {}}
        for name in source_names(peer):
            basename = name.split("/", 1)[1]
            data = _read_regular(source_fd, basename, MAX_SOURCE_BYTES)
            info = os.stat(basename, dir_fd=source_fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or data != expected[name]:
                raise ValueError("snapshot changed: source bytes or file identity differ")
            peers.verify_blob(peer, name, data)
            result["files"][name] = (_stat_identity(info), hashlib.sha256(data).hexdigest())
        again = os.stat("src", dir_fd=out_fd, follow_symlinks=False)
        if ((again.st_dev, again.st_ino) != result["directory"] or not stat.S_ISDIR(again.st_mode) or
                set(os.listdir(source_fd)) != basenames):
            raise ValueError("snapshot changed: source directory was replaced")
        return result
    finally:
        os.close(source_fd)


def _validate_native(data):
    """Check bounded ELF geometry only; this does not certify executable code."""
    try:
        from . import peer_runtime
    except ImportError:
        import peer_runtime
    peer_runtime.Elf64(data)


# The wrapper is fixed code, not source text supplied by an engine.  The
# pinned compiler is executed through the child's inherited descriptor and
# receives the original upstream source name and flags, without a shell.
_ORIGINAL_EXEC = r'''import hashlib,os,stat,sys
fd,expected,size,*argv=sys.argv[1:]
if not fd.isdecimal() or int(fd)<3 or not size.isdecimal(): raise RuntimeError("invalid compiler descriptor")
fd=int(fd); st=os.fstat(fd)
if not stat.S_ISREG(st.st_mode) or st.st_size!=int(size): raise RuntimeError("compiler identity differs")
h=hashlib.sha256(); offset=0
while offset<st.st_size:
 b=os.pread(fd,min(65536,st.st_size-offset),offset)
 if not b: raise RuntimeError("compiler became shorter")
 h.update(b); offset+=len(b)
if os.fstat(fd).st_size!=st.st_size or h.hexdigest()!=expected: raise RuntimeError("compiler digest differs")
os.execv("/proc/self/fd/"+str(fd),["g++",*argv])
'''


def _prepare_at(peer, profile, source, out, parent_fd):
    """Create a verified snapshot under the caller's held parent descriptor."""
    files = _read_sources(peer, source)
    record = source_record(peer, profile, files)
    out_fd = source_fd = None
    try:
        reopened = peer_exact_runner._open_directory(out.parent)
        try:
            parent, current = os.fstat(parent_fd), os.fstat(reopened)
            if (parent.st_dev, parent.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError("output parent path changed before snapshot")
        finally:
            os.close(reopened)
        os.mkdir(out.name, mode=0o700, dir_fd=parent_fd)
        out_fd = os.open(out.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        details = os.fstat(out_fd)
        if details.st_uid != os.geteuid() or stat.S_IMODE(details.st_mode) != 0o700:
            raise ValueError("private source snapshot ownership differs")
        _guard_output_path(out, parent_fd, out_fd)
        os.mkdir("src", mode=0o700, dir_fd=out_fd)
        source_fd = os.open("src", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=out_fd)
        for name in source_names(peer):
            _write_exclusive(source_fd, name.split("/", 1)[1], files[name])
        _write_exclusive(out_fd, "source-snapshot.json", peers.canonical(record) + b"\n")
        _guard_output_path(out, parent_fd, out_fd)
        _snapshot_pins(peer, out_fd, files)
        result_fd, out_fd = out_fd, None
        return record, result_fd, files
    finally:
        for fd in (source_fd, out_fd):
            if fd is not None:
                os.close(fd)


def prepare(peer, profile, source, out):
    """Copy verified original source to a new private external directory.

    A failure may leave a partial output. Never recursively delete or overwrite
    it: an owner can inspect it and retry with a different fresh output path.
    """
    _linux()
    source, out = _outside_checkout(Path(source)), _outside_checkout(Path(out))
    if out == source or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError("source and new output must not overlap")
    parent_fd = peer_exact_runner._open_directory(out.parent)
    out_fd = None
    try:
        record, out_fd, _ = _prepare_at(peer, profile, source, out, parent_fd)
        return record
    finally:
        if out_fd is not None:
            os.close(out_fd)
        os.close(parent_fd)


def build(peer, profile, source, out, *, cpu, timeout=600):
    """Compile unmodified pinned source twice for *unqualified* diagnostics.

    The snapshot and native files stay in a new external private directory.
    The compiler and output are inherited descriptor anchors, not user-supplied
    pathnames.  No binary is executed, no TT is allocated and no score or
    runtime authority is granted.  In-process quarantine preserves original
    FDs on uncertain ownership; it is not a durable supervisor.
    """
    _linux()
    if _ORIGINAL_QUARANTINE or peer_exact_runner._UNSETTLED:
        raise peer_exact_runner.GroupUnsettled("an earlier owned build remains unresolved")
    peers.peer_spec(peer)
    if profile not in _PROFILES:
        raise ValueError("a supported original peer TEST profile is required")
    if (not hasattr(os, "sched_getaffinity") or type(cpu) is not int or cpu < 0 or
            cpu not in os.sched_getaffinity(0) or isinstance(timeout, bool) or
            type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 3600):
        raise ValueError("an allowed CPU and bounded build timeout are required")
    source, out = _outside_checkout(Path(source)), _outside_checkout(Path(out))
    if out == source or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError("source and new output must not overlap")
    held = []
    uncertain = False
    try:
        parent_fd = peer_exact_runner._open_directory(out.parent)
        held.append(parent_fd)
        snapshot, out_fd, expected = _prepare_at(peer, profile, source, out, parent_fd)
        held.append(out_fd)
        _guard_output_path(out, parent_fd, out_fd)
        if source_record(peer, profile, expected) != snapshot:
            raise ValueError("snapshot changed after original source copy")
        pins = _snapshot_pins(peer, out_fd, expected)
        os.mkdir("home", 0o700, dir_fd=out_fd)
        compiler_path, compiler_sha, compiler_size, compiler_fd = _open_compiler()
        held.append(compiler_fd)
        attempts = []
        output_fds = []
        native_bytes = []

        def verify_snapshot():
            _guard_output_path(out, parent_fd, out_fd)
            if _snapshot_pins(peer, out_fd, expected) != pins:
                raise ValueError("snapshot changed during original peer build")

        def verify_native(name, fd):
            current = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=out_fd)
            try:
                owned, named = os.fstat(fd), os.fstat(current)
                if (owned.st_dev, owned.st_ino) != (named.st_dev, named.st_ino):
                    raise ValueError("owned native output identity changed")
                data = _read_owned_fd(fd, MAX_NATIVE_BYTES)
                if _read_owned_fd(current, MAX_NATIVE_BYTES) != data:
                    raise ValueError("owned native output bytes changed")
                return data
            finally:
                os.close(current)

        for index in (1, 2):
            verify_snapshot()
            name = f"peer-native-{index}"
            output_fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                0o600, dir_fd=out_fd)
            held.append(output_fd)
            output_fds.append((name, output_fd))
            command = ["python3", "-I", "-B", "-c", _ORIGINAL_EXEC,
                       "{fd:compiler}", compiler_sha, str(compiler_size),
                       *_FLAGS[peer], "src/main.cpp", "-o", "/proc/self/fd/{fd:output}"]
            _, _, observed = peer_exact_runner.run(
                command, out, sandbox_home=out / "home", cpu=cpu, timeout=timeout,
                fd_anchors={"work": (out_fd, out), "compiler": (compiler_fd, compiler_path),
                            "output": (output_fd, out / name)}, cwd_anchor="work")
            if (type(observed) is not dict or observed.get("exit_code") != 0 or
                    observed.get("leader_reaped") is not True or observed.get("group_absent") is not True or
                    observed.get("physical_group_settlement_proven") is not False):
                raise ValueError("bounded build observation differs")
            verify_snapshot()
            native = verify_native(name, output_fd)
            native_bytes.append(native)
            attempts.append({"name": name, "bytes": len(native),
                             "sha256": hashlib.sha256(native).hexdigest(), "command": observed})

        if native_bytes[0] != native_bytes[1]:
            raise ValueError("native attempts differ")
        _validate_native(native_bytes[0])
        verify_snapshot()
        for (name, fd), expected_native in zip(output_fds, native_bytes):
            if verify_native(name, fd) != expected_native:
                raise ValueError("owned native output changed before receipt")
        if peer_exact_runner._UNSETTLED:
            raise peer_exact_runner.GroupUnsettled("owned compiler settlement remains uncertain")
        record = {
            "format": "rove4k-original-peer-build-v1", "purpose": "test-only",
            "peer": peer, "profile": profile, "revision": snapshot["revision"],
            "source": snapshot["source"], "source_closure_sha256": snapshot["source_closure_sha256"],
            "source_modified_by_builder": False, "concurrent_source_mutation_excluded": False,
            "requested_uci": dict(snapshot["requested_uci"]), "uci_setup_performed": False,
            "complete": True, "same_host_native_reproduced": True,
            "compiler": {"path": compiler_path, "sha256": compiler_sha, "bytes": compiler_size,
                         "flags": list(_FLAGS[peer]), "home_policy": "/dev/null"},
            "attempts": attempts, "engines_executed": 0,
            "qualification": {"source_blob_identity_checked": True, "compiler_authenticated": False,
                              "source_to_native_proven": False, "tt_abi_verified": False,
                              "allocation_observed": False, "runtime_qualified": False,
                              "league_qualified": False, "scored_game_admitted": False},
            "limitations": ["source pre/post pins do not exclude transient same-UID modifications",
                            "same-UID directory replacement between mkdir and open is not excluded",
                            "compiler path and hash do not authenticate the compiler or its dependencies",
                            "original process-group observation does not prove escaped descendants settled",
                            "process quarantine is in-memory and not durable across supervisor death"],
        }
        raw = peers.canonical(record) + b"\n"
        _write_exclusive(out_fd, "original-peer-build.json", raw)
        os.fsync(out_fd)
        return {"path": str(out / "original-peer-build.json"),
                "sha256": hashlib.sha256(raw).hexdigest(), "record": record}
    except (peer_exact_runner.GroupUnsettled, peer_exact_runner.OwnershipLost):
        uncertain = True
        raise
    finally:
        if uncertain or peer_exact_runner._UNSETTLED:
            # Do not publish or clean up anything while an original build
            # owner may still reference our descriptors.  Retention ends with
            # this process and does not establish crash-safe ownership.
            _ORIGINAL_QUARANTINE.append({"fds": tuple(held), "output": str(out),
                                         "reason": "ownership-unsettled"})
            held.clear()
        while held:
            os.close(held.pop())
