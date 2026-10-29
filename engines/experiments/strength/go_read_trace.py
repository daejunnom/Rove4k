"""Linux x86-64 diagnostic: sample one traced thread's stdin read buffers.

The tracer executes an unmodified engine under ptrace. A matching candidate is
assembled from user-memory samples at successful read(0) return stops. Other
threads can modify that memory or share and read fd 0; neither exclusive buffer
ownership nor a complete byte stream is established. It does not prove UCI
receipt, parsing, search, host identity or authority. Instrumentation affects
performance and this run must never be scored.
"""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import struct
import sys
import time

_libc = ctypes.CDLL(None, use_errno=True)
_libc.ptrace.restype = ctypes.c_long
_PEEKDATA, _SYSCALL, _DETACH, _SETOPTIONS = 2, 24, 17, 0x4200
_GET_SYSCALL_INFO = 0x420E
_TRACESYSGOOD, _TRACEEXEC, _EVENT_EXEC = 1, 16, 4
_MAX_READ = 65536


def _syscall_info(pid):
    """Use kernel ENTRY/EXIT labels, never infer phase by toggling stops."""
    raw = ctypes.create_string_buffer(128)
    try:
        size = _ptrace(_GET_SYSCALL_INFO, pid, ctypes.sizeof(raw), ctypes.addressof(raw))
    except OSError as error:
        if error.errno in (errno.EPERM, errno.EACCES, errno.EINVAL, errno.EIO, errno.ENOSYS):
            os.write(2, ('diagnostic-capability-unavailable: GET_SYSCALL_INFO errno=%d\n' % error.errno).encode())
        raise
    if size < 24:
        raise RuntimeError('kernel syscall information unavailable or truncated')
    op, arch = struct.unpack_from('<B3xI', raw.raw)
    if arch != 0xc000003e:
        raise RuntimeError('non-x86-64 syscall ABI is not observable')
    if op == 1 and size >= 80:
        nr, fd, address, count = struct.unpack_from('<QQQQ', raw.raw, 24)
        return ('entry', nr, fd, address, count)
    if op == 2 and size >= 33:
        return ('exit', struct.unpack_from('<q', raw.raw, 24)[0])
    raise RuntimeError('unrecognized or truncated syscall information')


def _ptrace(request, pid=0, address=0, data=0):
    ctypes.set_errno(0)
    result = _libc.ptrace(ctypes.c_uint(request), ctypes.c_int(pid),
                          ctypes.c_void_p(address), ctypes.c_void_p(data))
    err = ctypes.get_errno()
    if result == -1 and err:
        raise OSError(err, os.strerror(err))
    return result


def _bytes_at(pid, address, count):
    result = bytearray()
    width = ctypes.sizeof(ctypes.c_long)
    # Read aligned machine words so the final short chunk cannot make ptrace
    # access an unmapped following page outside the successful read's buffer.
    start = address - address % width
    offset_in_word = address - start
    for offset in range(0, offset_in_word + count, width):
        value = _ptrace(_PEEKDATA, pid, start + offset)
        result.extend(int(value & ((1 << (width * 8)) - 1)).to_bytes(width, 'little'))
    return bytes(result[offset_in_word:offset_in_word + count])


def _emit(fd, event):
    # These fixed claim fields are diagnostic state, never authorization and
    # never a statement that an unobserved event definitely did not happen.
    event = {**event, 'engine_go_confirmed': False, 'search_started_confirmed': False,
             'performance_eligible': False, 'score_eligible': False,
             'operational_go_authorized': False}
    data = (json.dumps(event, sort_keys=True, separators=(',', ':')) + '\n').encode()
    while data:
        n = os.write(fd, data)
        if n <= 0:
            raise OSError('short evidence write')
        data = data[n:]


def run(engine, evidence_fd):
    """Trace one engine; stdin/stdout/stderr are inherited from the caller.

    Only this direct child's native x86-64 SYS_read on descriptor 0 is observed.
    readv, mmap, descendants, subsequent execs and syscall interception failures
    may be missing; absence of an event cannot establish that GO did not arrive.
    The evidence FD must be supplied by an owning caller and is closed on exec.
    """
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('Linux x86-64 ptrace diagnostic only')
    if not isinstance(engine, (list, tuple)) or not engine or not Path(engine[0]).is_absolute():
        raise ValueError('absolute engine executable required')
    if type(evidence_fd) is not int or evidence_fd < 3:
        raise ValueError('distinct evidence FD required')
    os.set_inheritable(evidence_fd, False)
    child = os.fork()
    if child == 0:
        try:
            try:
                _ptrace(0)  # PTRACE_TRACEME; owned by this tracer.
            except OSError as error:
                if error.errno in (errno.EPERM, errno.EACCES, errno.ENOSYS):
                    os.write(2, ('diagnostic-capability-unavailable: TRACEME errno=%d\n' % error.errno).encode())
                raise
            os.execv(engine[0], list(engine))
        except BaseException:
            os._exit(127)
    pending, entry, aligned = bytearray(), None, True
    complete = False
    try:
        pid, status = os.waitpid(child, 0)
        if pid != child or not os.WIFSTOPPED(status) or os.WSTOPSIG(status) != signal.SIGTRAP:
            raise RuntimeError('engine did not enter the expected exec trace stop')
        _ptrace(_SETOPTIONS, child, 0, _TRACESYSGOOD | _TRACEEXEC)
        _emit(evidence_fd, {'event': 'trace_started', 'pid': child,
                            'performance_eligible': False,
                            'scope': 'direct child; x86-64 read fd 0 only'})
        signal_to_deliver = 0
        while True:
            _ptrace(_SYSCALL, child, 0, signal_to_deliver)
            signal_to_deliver = 0
            _, status = os.waitpid(child, 0)
            if os.WIFEXITED(status):
                code = os.WEXITSTATUS(status)
                complete = True
                _emit(evidence_fd, {'event': 'trace_exited', 'pid': child, 'exit_code': code,
                                    'observation_complete': False})
                return code
            if os.WIFSIGNALED(status):
                code = 128 + os.WTERMSIG(status)
                complete = True
                _emit(evidence_fd, {'event': 'trace_signaled', 'pid': child,
                                    'signal': os.WTERMSIG(status), 'observation_complete': False})
                return code
            if not os.WIFSTOPPED(status):
                raise RuntimeError('unexpected ptrace wait state')
            stop = os.WSTOPSIG(status)
            if stop == signal.SIGTRAP and status >> 16 == _EVENT_EXEC:
                # This ptrace event is not an actual SIGTRAP delivered to the
                # engine. The process image and its input framing may change.
                pending.clear()
                aligned = False
                _emit(evidence_fd, {'event': 'trace_exec_changed', 'pid': child,
                                    'observation_complete': False})
                continue
            if stop != (signal.SIGTRAP | 0x80):
                # Actual signal-delivery stops are forwarded unchanged; no
                # debugger-generated EXEC trap is injected into the engine.
                signal_to_deliver = stop
                continue
            info = _syscall_info(child)
            if info[0] == 'entry':
                if entry is not None:
                    pending.clear()
                    aligned = False
                    _emit(evidence_fd, {'event': 'trace_incomplete', 'pid': child,
                                        'reason': 'missing_syscall_exit'})
                entry = info[1:]
            elif entry is None:
                pending.clear()
                aligned = False
                _emit(evidence_fd, {'event': 'trace_incomplete', 'pid': child,
                                    'reason': 'missing_syscall_entry'})
            else:
                syscall, fd, address, requested = entry
                entry = None
                n = info[1]
                if syscall == 19 and fd == 0 and n > 0:  # readv is not captured.
                    pending.clear()
                    aligned = False
                    _emit(evidence_fd, {'event': 'trace_incomplete', 'pid': child,
                                        'reason': 'readv_not_observed'})
                if syscall != 0 or fd != 0 or n <= 0:
                    continue
                if n > requested or n > _MAX_READ or len(pending) + n > _MAX_READ:
                    pending.clear()
                    aligned = False
                    _emit(evidence_fd, {'event': 'trace_incomplete', 'pid': child,
                                        'reason': 'read_or_line_limit'})
                    continue
                pending.extend(_bytes_at(child, address, n))
                while b'\n' in pending:
                    line, _, rest = pending.partition(b'\n')
                    pending[:] = rest
                    if not aligned:
                        aligned = True
                        continue
                    # Commands are ASCII protocol bytes; record a digest, not
                    # an untrusted stream or any engine-generated output.
                    words = line.rstrip(b'\r').split()
                    if words and words[0] == b'go':
                        _emit(evidence_fd, {'event': 'stdin_read_buffer_go_candidate', 'pid': child,
                            'monotonic_ns': time.monotonic_ns(), 'line_sha256': hashlib.sha256(line).hexdigest(),
                            'line_bytes': len(line), 'performance_eligible': False,
                            'thread_and_buffer_exclusive': False, 'engine_received_line': None,
                            'engine_parsed': None, 'search_started': None})
    finally:
        if not complete:
            # Never kill a possibly started engine because tracing failed.
            # Detach resumes an existing ptrace stop; retain the child until
            # natural exit. If detaching fails, physical settlement may block.
            while True:
                try:
                    _ptrace(_DETACH, child)
                except OSError:
                    pass
                try:
                    _, final_status = os.waitpid(child, 0)
                except ChildProcessError:
                    break
                if os.WIFEXITED(final_status) or os.WIFSIGNALED(final_status):
                    break


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit('usage: go_read_trace.py EVIDENCE_FD /absolute/engine [args...]')
    raise SystemExit(run(sys.argv[2:], int(sys.argv[1])))
