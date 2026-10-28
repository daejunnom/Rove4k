"""Run one bounded build tool while retaining its original process-group owner.

This is for local build/minifier commands, not engine or score execution.
It does not create file logs, pass the caller's environment, establish a
sandbox, or prove the absence of descendants that escape the original process
group.  Linux /proc enumeration is not an atomic snapshot and can be hidden by
namespaces. A caller must not install SIGCHLD=SIG_IGN or concurrently reap our
children.  Unsettled handles are retained rather than signalled by a stale ID.
"""
from __future__ import annotations

import ctypes
import hashlib
import math
import os
import platform
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time

try:
    import resource
except ImportError:  # Import remains possible on Windows; execution is Linux-only.
    resource = None


_UNSETTLED = {}
_BLOCKED = frozenset((".ssh", ".aws", ".npmrc", "node_modules", "dist", "dist-server", "build",
                      "coverage", "models", "checkpoints", ".cache", "package-lock.json", "inventory.json",
                      "id_rsa", "id_ed25519", "id_dsa", "id_ecdsa"))


class OwnershipLost(RuntimeError):
    """The original child can no longer be safely identified or reaped."""


class GroupUnsettled(RuntimeError):
    """The original group could not be shown to have settled safely."""


class BuildCommandFailure(RuntimeError):
    def __init__(self, message, record):
        super().__init__(message)
        self.record = record


def _safe_path(path):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("an absolute non-protected directory is required")
    for part in path.parts:
        value = part.lower()
        if (value in _BLOCKED or value.startswith(".env") or value == "token" or
                value.startswith("token.") or value.endswith(("-token", "_token")) or
                any(key in value for key in ("credential", "service-account", "service_account",
                                              "api-key", "api_key", "ssh-key", "ssh_key",
                                              "private-key", "private_key", "password"))):
            raise ValueError("protected directory is not a build input")
    return path


def _open_directory(path, *, private=False):
    path = _safe_path(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        details = os.fstat(fd)
        if private and (details.st_uid != os.geteuid() or stat.S_IMODE(details.st_mode) != 0o700):
            raise ValueError("sandbox home must be a private directory owned by the caller")
        result, fd = fd, None
        return result
    finally:
        if fd is not None:
            os.close(fd)


def _path_env():
    # PATH is not a credential; omit unsafe or relative search directories.
    selected = []
    for value in os.environ.get("PATH", os.defpath).split(os.pathsep):
        if not value:
            continue
        try:
            _safe_path(value)
        except ValueError:
            continue
        if value not in selected:
            selected.append(value)
    if not selected:
        raise ValueError("no allowed executable search path")
    return os.pathsep.join(selected)


def _require_reap_contract():
    """Reject auto-reaping or a competing Python/OS thread before launch."""
    if (threading.current_thread() is not threading.main_thread() or threading.active_count() != 1 or
            len(os.listdir("/proc/self/task")) != 1 or signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL):
        raise ValueError("exclusive child reaping and default SIGCHLD handling are required")
    if platform.machine().lower() not in ("x86_64", "amd64") or platform.libc_ver()[0] != "glibc":
        raise ValueError("known Linux x86-64 glibc signal ABI is required")
    # glibc Linux x86-64 sigaction: handler, 1024-bit sigset, flags, restorer.
    # A SA_NOCLDWAIT setup can auto-reap even with the default handler.
    class SigAction(ctypes.Structure):
        _fields_ = [("handler", ctypes.c_void_p), ("mask", ctypes.c_ulong * 16),
                    ("flags", ctypes.c_int), ("restorer", ctypes.c_void_p)]
    libc = ctypes.CDLL(None, use_errno=True)
    action = SigAction()
    if libc.sigaction(int(signal.SIGCHLD), None, ctypes.byref(action)) != 0:
        raise ValueError("SIGCHLD action is unavailable")
    if action.handler not in (None, 0) or action.flags & 2:  # SA_NOCLDWAIT
        raise ValueError("SIGCHLD can reap the original leader automatically")


def _require_inherited_limits(timeout, memory_bytes):
    seconds = max(1, math.ceil(timeout))
    wanted = ((resource.RLIMIT_AS, memory_bytes), (resource.RLIMIT_CPU, seconds + 5),
              (resource.RLIMIT_FSIZE, 64 << 20))
    for kind, needed in wanted:
        soft, hard = resource.getrlimit(kind)
        if any(value != resource.RLIM_INFINITY and value < needed for value in (soft, hard)):
            raise ValueError("build child cannot increase an inherited resource limit")


def _identity(pid):
    try:
        raw = Path("/proc") .joinpath(str(pid), "stat").read_text(encoding="ascii")
        fields = raw.rsplit(")", 1)[1].split()
        pgrp, session, ticks = int(fields[2]), int(fields[3]), int(fields[19])
    except (OSError, ValueError, IndexError) as error:
        raise OwnershipLost("original process identity is unavailable") from error
    if pgrp != pid or session != pid or ticks <= 0:
        raise OwnershipLost("original process group or session identity differs")
    return {"pid": pid, "pgid": pgrp, "session": session, "start_ticks": ticks}


def _observe(proc, expected):
    try:
        status = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError as error:
        raise OwnershipLost("original leader was reaped elsewhere") from error
    if _identity(proc.pid) != expected:
        raise OwnershipLost("original leader identity changed")
    return status is not None


def _members(expected):
    result = []
    try:
        entries = list(os.scandir("/proc"))
    except OSError as error:
        raise GroupUnsettled("process group visibility is unavailable") from error
    for entry in entries:
        if not entry.name.isdecimal() or int(entry.name) == expected["pid"]:
            continue
        try:
            raw = Path("/proc") .joinpath(entry.name, "stat").read_text(encoding="ascii")
            fields = raw.rsplit(")", 1)[1].split()
            if int(fields[2]) == expected["pgid"]:
                result.append({"pid": int(entry.name), "state": fields[0]})
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (OSError, ValueError, IndexError) as error:
            raise GroupUnsettled("process group membership is not fully visible") from error
    return result


def _signal_owned(proc, identity, sig):
    # No signalling is allowed once another waiter reaps the original leader.
    _observe(proc, identity)
    try:
        os.killpg(identity["pgid"], sig)
    except ProcessLookupError:
        # A verified unreaped leader normally keeps this group present.
        raise OwnershipLost("original process group vanished before settlement") from None


def _settle(proc, identity, *, stop, seconds=5):
    """Do not reap the leader until all observed original group members exit."""
    deadline = time.monotonic() + seconds
    if stop:
        _signal_owned(proc, identity, signal.SIGKILL)
    while True:
        exited = _observe(proc, identity)
        others = _members(identity)
        if exited and not others:
            # WNOWAIT observation and zero other members precede this only reap.
            return proc.wait(timeout=1)
        if time.monotonic() >= deadline:
            raise GroupUnsettled("original process group did not fully settle")
        time.sleep(.02)


def run(command, cwd, *, sandbox_home, rustup_home=None, timeout=600, cpu=5,
        memory_bytes=2 << 30, output_bytes=2 << 20):
    """Run argv once with bounded streams and no logs or inherited secrets."""
    if (sys.platform != "linux" or resource is None or
            not all(hasattr(os, key) for key in ("waitid", "WNOWAIT", "sched_setaffinity"))):
        raise ValueError("Linux waitid and CPU affinity support are required")
    if (type(command) not in (list, tuple) or not command or
            any(type(value) is not str or not value or "\x00" in value for value in command)):
        raise ValueError("structured non-empty argv required")
    if (type(cpu) is not int or cpu < 0 or cpu not in os.sched_getaffinity(0) or
            type(timeout) not in (int, float) or isinstance(timeout, bool) or not math.isfinite(timeout) or
            not 0 < timeout <= 3600 or type(memory_bytes) is not int or not 0 < memory_bytes <= 8 << 30 or
            type(output_bytes) is not int or not 0 < output_bytes <= 16 << 20):
        raise ValueError("invalid CPU, duration, memory or output limit")
    if _UNSETTLED:
        raise GroupUnsettled("an earlier original process group is still unresolved")
    _require_reap_contract()
    _require_inherited_limits(timeout, memory_bytes)
    cwd_fd = home_fd = rust_fd = None
    proc = identity = None
    stdout, stderr, reason, code = bytearray(), bytearray(), None, None
    started = time.monotonic()
    handled = (signal.SIGTERM, signal.SIGINT)
    original_handlers = {item: signal.getsignal(item) for item in handled}
    def interrupt(signum, frame):
        raise KeyboardInterrupt("build command interrupted")
    for item in handled:
        signal.signal(item, interrupt)
    try:
        cwd_fd = _open_directory(cwd)
        home_fd = _open_directory(sandbox_home, private=True)
        if rustup_home is not None:
            rust_fd = _open_directory(rustup_home)
        # The supervisor keeps these FDs alive for the entire group lifetime.
        # A child may close inherited FDs before spawning grandchildren; an
        # anchored parent-FD path still names the original private directory.
        owner_pid = os.getpid()
        home_path = f"/proc/{owner_pid}/fd/{home_fd}"
        env = {"PATH": _path_env(), "LANG": "C", "LC_ALL": "C",
               "HOME": home_path, "CARGO_HOME": home_path + "/cargo"}
        if rust_fd is not None:
            env["RUSTUP_HOME"] = f"/proc/{owner_pid}/fd/{rust_fd}"
        inherited = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            def child_setup():
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                seconds = max(1, math.ceil(timeout))
                resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 5))
                resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))
                os.sched_setaffinity(0, {cpu})
                signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
            proc = subprocess.Popen(list(command), cwd=f"/proc/{owner_pid}/fd/{cwd_fd}", env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True, preexec_fn=child_setup)
            _UNSETTLED[proc.pid] = proc
            identity = _identity(proc.pid)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, inherited)
        deadline = started + timeout
        with selectors.DefaultSelector() as selector:
            for stream in (proc.stdout, proc.stderr):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                _observe(proc, identity)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("build command exceeded its wall deadline")
                for key, _ in selector.select(min(.1, remaining)):
                    target = stdout if key.fileobj is proc.stdout else stderr
                    try:
                        chunk = os.read(key.fileobj.fileno(), min(65536, output_bytes + 1 - len(target)))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        target.extend(chunk)
                        if len(target) > output_bytes or len(stdout) + len(stderr) > output_bytes:
                            raise ValueError("build command exceeded its output byte limit")
        while not _observe(proc, identity):
            if time.monotonic() >= deadline:
                raise TimeoutError("build command exceeded its wall deadline")
            time.sleep(.01)
        others = _members(identity)
        if others:
            raise GroupUnsettled("leader exited while original group members remained")
        # A signal between the one allowed reap and owner removal must not
        # re-enter cleanup with a stale PID. Deliver it only after both finish.
        prior = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            code = _settle(proc, identity, stop=False)
            _UNSETTLED.pop(proc.pid, None)
            proc.stdout.close()
            proc.stderr.close()
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, prior)
        record = {"argv": list(command), "cwd": str(cwd), "exit_code": code,
                  "elapsed_seconds": time.monotonic() - started, "leader_reaped": True,
                  "forced_cleanup": False, "group_absent": True,
                  "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                  "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                  "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
                  "original_group_empty_observed_before_reap": True,
                  "physical_group_settlement_proven": False,
                  "scope": "non-atomic original-group observation; escaped descendants and hidden namespaces unproved"}
        if code != 0:
            raise BuildCommandFailure("build command returned nonzero", record)
        return bytes(stdout), bytes(stderr), record
    except BaseException as error:
        reason = error
        if proc is None and isinstance(reason, (ValueError, OSError)):
            raise ValueError("unsafe or unavailable build directory or environment") from reason
        if proc is not None and proc.pid in _UNSETTLED:
            prior = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
            try:
                if identity is None:
                    raise OwnershipLost("created child identity was not established")
                code = _settle(proc, identity, stop=True)
                _UNSETTLED.pop(proc.pid, None)
                proc.stdout.close()
                proc.stderr.close()
            except (OwnershipLost, GroupUnsettled, OSError, subprocess.TimeoutExpired) as cleanup:
                failure = GroupUnsettled("build command ownership or cleanup remains uncertain")
                failure.process, failure.identity = proc, identity
                # A live child or grandchild may still dereference our
                # supervisor-FD cwd/HOME/toolchain paths. Preserve the exact
                # descriptors with the original process until an explicit
                # owner can resolve it; closing them here would change its
                # environment while it is still alive.
                retained = {"process": proc, "identity": identity,
                            "directory_fds": tuple(fd for fd in (cwd_fd, home_fd, rust_fd) if fd is not None)}
                _UNSETTLED[proc.pid] = retained
                failure.directory_fds = retained["directory_fds"]
                cwd_fd = home_fd = rust_fd = None
                raise failure from cleanup
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, prior)
        if isinstance(reason, (KeyboardInterrupt, SystemExit, BuildCommandFailure)):
            raise
        record = {"argv": list(command), "cwd": str(cwd), "exit_code": code,
                  "elapsed_seconds": time.monotonic() - started, "leader_reaped": proc is not None,
                  "forced_cleanup": proc is not None, "group_absent": proc is not None,
                  "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                  "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                  "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
                  "original_group_empty_observed_before_reap": proc is not None,
                  "physical_group_settlement_proven": False,
                  "scope": "non-atomic original-group observation; escaped descendants and hidden namespaces unproved"}
        raise BuildCommandFailure(str(reason), record) from reason
    finally:
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set(handled))
        try:
            for fd in (cwd_fd, home_fd, rust_fd):
                if fd is not None:
                    os.close(fd)
            for item, handler in original_handlers.items():
                signal.signal(item, handler)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
