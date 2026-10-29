#!/usr/bin/env python3
"""Fault-inject the selected Fastchess runner's engine-input writes.

Only the first fixture GO or isready is affected. LD_PRELOAD supplies synthetic
short writes and errors; separate owned fixtures exercise a real closed pipe
and an actual thread-directed SIGINT interrupting a full pipe write. None proves
remote GO receipt, physical ownership, or league/strength qualification. Run
only with a verified local build receipt; mock engines stay outside Git.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rove_write_runtime', HERE / 'test_fastchess.py')
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)
fastchess = runtime.fastchess
ALL_MODES = ('short', 'eintr', 'short_eintr', 'signal_eintr', 'zero', 'error', 'ready_error',
             'short_zero', 'short_error', 'real_epipe', 'short_error_wait')

SHIM = r'''#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

static atomic_int fired = 0;
static atomic_int failed_after_partial = 0;
static int pending_fd = -1;
static long signal_result = -2;
static long signal_tid = -1;
static void *interrupt_writer(void *arg) {
    usleep(100000);
    signal_tid = (long)(intptr_t)arg;
    signal_result = syscall(SYS_tgkill, getpid(), (pid_t)signal_tid, SIGINT);
    return NULL;
}
ssize_t write(int fd, const void *buf, size_t len) {
    const char *mode = getenv("ROVE_TEST_WRITE_MODE");
    const char *target = getenv("ROVE_TEST_WRITE_TARGET");
    const char *log = getenv("ROVE_TEST_WRITE_LOG");
    char exe[4096];
    ssize_t exe_len = readlink("/proc/self/exe", exe, sizeof(exe)-1);
    if (exe_len >= 0) exe[exe_len] = '\0';
    int stage = atomic_load_explicit(&fired, memory_order_relaxed);
    if (mode && target && log && exe_len >= 0 && strcmp(exe, target) == 0 &&
        atomic_load_explicit(&failed_after_partial, memory_order_relaxed) && fd == pending_fd) {
        char row[256];
        int count = snprintf(row, sizeof(row), "POST %zu %.*s\n", len,
                             (int)(len < 40 ? len : 40), (const char*)buf);
        int logfd = open(log, O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC, 0600);
        if (logfd >= 0) {
            if (count > 0) syscall(SYS_write, logfd, row, (size_t)count);
            close(logfd);
        }
    }
    if (mode && target && log && exe_len >= 0 && strcmp(exe, target) == 0 &&
        ((stage == 0 && ((strcmp(mode, "ready_error") && len >= 4 && memcmp(buf, "go ", 3) == 0) ||
                         (!strcmp(mode, "ready_error") && len >= 8 && memcmp(buf, "isready", 7) == 0))) ||
         (stage == 1 && fd == pending_fd))) {
        atomic_store_explicit(&fired, 2, memory_order_relaxed);
        ssize_t result;
        int err = 0;
        if (!strcmp(mode, "short") || (!stage &&
                (!strcmp(mode, "short_error") || !strcmp(mode, "short_zero") ||
                 !strcmp(mode, "short_eintr") || !strcmp(mode, "short_error_wait")))) {
            result = syscall(SYS_write, fd, buf, len / 2);
            if (result > 0 && strcmp(mode, "short")) {
                pending_fd = fd;
                atomic_store_explicit(&fired, 1, memory_order_relaxed);
            }
        } else if (!strcmp(mode, "eintr") || !strcmp(mode, "short_eintr")) {
            result = -1; err = EINTR;
        } else if (!strcmp(mode, "zero") || !strcmp(mode, "short_zero")) {
            result = 0;
        } else if (!strcmp(mode, "error") || !strcmp(mode, "ready_error") || !strcmp(mode, "short_error") ||
                   !strcmp(mode, "short_error_wait")) {
            result = -1; err = EIO;
        } else if (!strcmp(mode, "real_epipe")) {
            result = syscall(SYS_write, fd, buf, len);
            if (result < 0) err = errno;
        } else if (!strcmp(mode, "signal_eintr")) {
            int flags = fcntl(fd, F_GETFL);
            char filler[4096];
            memset(filler, 'x', sizeof(filler));
            ssize_t fill_result;
            if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
                result = -1; err = EINVAL;
            } else {
                do { fill_result = syscall(SYS_write, fd, filler, sizeof(filler)); }
                while (fill_result > 0);
                if (fill_result != -1 || errno != EAGAIN || fcntl(fd, F_SETFL, flags) < 0) {
                    result = -1; err = EINVAL;
                } else {
                    pthread_t thread;
                    pending_fd = fd;
                    if (pthread_create(&thread, NULL, interrupt_writer,
                                       (void*)(intptr_t)syscall(SYS_gettid)) != 0) {
                        result = -1; err = EINVAL;
                    } else {
                        result = syscall(SYS_write, fd, buf, len);
                        if (result < 0) err = errno;
                        pthread_join(thread, NULL);
                        atomic_store_explicit(&failed_after_partial, 1, memory_order_relaxed);
                    }
                }
            }
        } else {
            result = -1; err = EINVAL;
        }
        if (stage == 1 && strcmp(mode, "short_eintr"))
            atomic_store_explicit(&failed_after_partial, 1, memory_order_relaxed);
        char row[256];
        int count = snprintf(row, sizeof(row), "%s %zu %zd %d\n", mode, len, result, err);
        int logfd = open(log, O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC, 0600);
        if (logfd >= 0) {
            if (count > 0) syscall(SYS_write, logfd, row, (size_t)count);
            if (!strcmp(mode, "signal_eintr")) {
                count = snprintf(row, sizeof(row), "SIGNAL %ld %ld\n", signal_tid, signal_result);
                if (count > 0) syscall(SYS_write, logfd, row, (size_t)count);
            }
            close(logfd);
        }
        if (err) errno = err;
        return result;
    }
    return syscall(SYS_write, fd, buf, len);
}
'''

LIFECYCLE_CPP = r'''#include <engine/process/process_posix.hpp>
#include <chrono>
#include <iostream>
#include <string>
#include <vector>
namespace fastchess { const char* version = "fixture"; }
using fastchess::engine::process::Process;
using fastchess::engine::process::Line;
int main(int argc, char** argv) {
    if (argc != 2) return 90;
    Process process;
    auto run = [&](const char* phase) {
        auto opened = process.init("/tmp", "/usr/bin/python3", std::string("-u ") + argv[1], phase);
        if (!opened) { std::cerr << "init " << opened.message << "\n"; return false; }
        auto sent = process.writeInput("hello\n");
        if (!sent) { std::cerr << "write " << sent.message << "\n"; return false; }
        std::vector<Line> lines;
        auto received = process.readOutput(lines, "ACK:", std::chrono::seconds(5));
        if (!received || lines.empty() || lines.back().line != "ACK:hello") return false;
        if (!process.writeInput("quit\n")) return false;
        process.terminate();
        return true;
    };
    if (!run("first")) return 1;
    auto failed = process.init("/tmp", "/definitely-not-a-real-rove-engine", "", "missing");
    if (failed) return 2;
    auto denied = process.writeInput("must-not-be-sent\n");
    if (denied || denied.message != "engine input unusable; delivery uncertain") return 3;
    process.terminate();
    if (!run("second")) return 4;
    std::cout << "lifecycle-ok\n";
}
'''

LIFECYCLE_ENGINE = """import sys
for line in sys.stdin:
    text = line.strip()
    if text == 'quit':
        break
    print('ACK:' + text, flush=True)
"""


def _rows(path: Path) -> list[dict]:
    return runtime._rows(path)


def _validate_build(receipt: Path) -> tuple[Path, dict]:
    built = json.loads(receipt.read_text(encoding='utf-8'))
    if built.get('complete') is not True or built.get('upstream_commit') != fastchess.PIN:
        raise ValueError('complete pinned build receipt required')
    if built.get('patch_sha256') != fastchess.sha(fastchess.PATCH.read_bytes()):
        raise ValueError('build receipt does not match reviewed patch')
    binary = Path(built['binary']).resolve(strict=True)
    if fastchess.sha(binary.read_bytes()) != built['binary_sha256']:
        raise ValueError('runner binary differs from build receipt')
    return binary, built


def _lifecycle(source: Path, build_receipt: Path, built: dict, out: Path) -> dict:
    source = source.resolve(strict=True)
    prepared = fastchess.verify_checkout(source)
    if prepared['patch_sha256'] != built['patch_sha256']:
        raise ValueError('lifecycle source does not match runner patch')
    object_root = build_receipt.resolve().parent / 'objects'
    command = built['command']['argv']
    if ('BUILDDIR=' + str(object_root) not in command or
            'BINARY_PATH=' + str(build_receipt.resolve().parent) not in command):
        raise ValueError('lifecycle object directory differs from runner build')
    objects = sorted(path for path in object_root.rglob('*.o')
                     if path.relative_to(object_root).as_posix() != 'src/main.o')
    if not 1 <= len(objects) <= 200 or any(path.is_symlink() or not path.is_file() for path in objects):
        raise ValueError('bounded runner objects required')
    harness = out / 'process-lifecycle.cc'
    harness.write_text(LIFECYCLE_CPP, encoding='utf-8')
    binary = out / 'process-lifecycle'
    app = source / 'app'
    subprocess.run(['g++', '-std=c++17', '-O2', '-DNDEBUG', '-I' + str(app / 'src'),
                    '-I' + str(app / 'third_party'), '-I' + str(app / 'third_party/fmt/include'),
                    str(harness), *(str(path) for path in objects), '-pthread', '-lstdc++fs',
                    '-o', str(binary)], check=True, timeout=90)
    with tempfile.TemporaryDirectory(prefix='rove-lifecycle-', dir='/tmp') as temporary:
        mock = Path(temporary) / 'engine.py'
        mock.write_text(LIFECYCLE_ENGINE, encoding='utf-8')
        process = subprocess.Popen([str(binary), str(mock)], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            stdout, _ = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            fastchess.signal_owned_group(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
            raise RuntimeError('lifecycle fixture timed out')
        if process.returncode != 0 or stdout != b'lifecycle-ok\n':
            raise AssertionError('actual Process lifecycle fixture failed: ' + repr(stdout[-2048:]))
    return {'complete': True, 'source_patch_sha256': prepared['patch_sha256'],
            'harness_sha256': hashlib.sha256(harness.read_bytes()).hexdigest(),
            'scope': 'actual patched Process class with runner build objects; fixture only'}


def actual_check(build_receipt: Path, out: Path, *, source: Path | None = None,
                 modes=ALL_MODES) -> dict:
    if sys.platform != 'linux':
        raise RuntimeError('Linux dynamic loader required for write fault injection')
    binary, built = _validate_build(build_receipt)
    out = fastchess._external_new(out)
    out.mkdir(parents=True)
    shim_source = out / 'write_fault.c'
    shim_binary = out / 'write_fault.so'
    shim_source.write_text(SHIM, encoding='utf-8')
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC', '-pthread',
                    str(shim_source), '-o', str(shim_binary)], check=True, timeout=60)
    mock = out / 'mock_engine.py'
    import_anchor = 'import json, os, stat, sys, time'
    uci_anchor = "        print('uciok', flush=True)"
    ready_anchor = "    elif line == 'isready':\n        print('readyok', flush=True)"
    if any(runtime.MOCK.count(anchor) != 1 for anchor in (import_anchor, uci_anchor, ready_anchor)):
        raise ValueError('fixture modification anchor differs')
    mock_source = runtime.MOCK.replace(import_anchor,
                                       'import json, os, signal, stat, sys, threading, time').replace(
        uci_anchor,
        uci_anchor + "\n"
        "        if mode == 'stale_ready':\n"
        "            def emit_stale():\n"
        "                time.sleep(.2)\n"
        "                note(event='stale_readyok_sent')\n"
        "                try:\n"
        "                    print('readyok', flush=True)\n"
        "                except BrokenPipeError:\n"
        "                    pass\n"
        "                time.sleep(3)\n"
        "                os._exit(0)\n"
        "            threading.Thread(target=emit_stale, daemon=True).start()"
    ).replace(
        ready_anchor,
        "    elif line == 'isready':\n"
        "        if mode == 'broken' and moves:\n"
        "            os.close(0)\n"
        "            note(event='stdin_closed')\n"
        "            print('readyok', flush=True)\n"
        "            time.sleep(5)\n"
        "            break\n"
        "        if mode == 'signal' and moves:\n"
        "            note(event='signal_wait')\n"
        "            print('readyok', flush=True)\n"
        "            time.sleep(3)\n"
        "            os._exit(0)\n"
        "        if mode == 'failure' and moves:\n"
        "            signal.signal(signal.SIGALRM, lambda *_: sys.exit(0))\n"
        "            signal.alarm(2)\n"
        "        print('readyok', flush=True)")
    mock.write_text(mock_source, encoding='utf-8')
    mock.chmod(0o700)
    book = out / 'book.pgn'
    book.write_text('[Event "Fixture only"]\n[Result "*"]\n\n1. f3 e5 *\n', encoding='utf-8')
    report = {'complete': False, 'upstream_commit': fastchess.PIN,
              'patch_sha256': built['patch_sha256'], 'binary_sha256': built['binary_sha256'],
              'injector_sha256': hashlib.sha256(shim_source.read_bytes()).hexdigest(),
              'scope': 'local controlled write faults, SIGINT and closed-pipe fixtures; not GO authority or league qualification',
              'engine_go_receipt_confirmed': False, 'scored_game_authorized': False,
              'cases': []}
    report_path = out / 'write-fault.json'
    try:
        if source is not None:
            report['lifecycle'] = _lifecycle(source, build_receipt, built, out)
        else:
            report['lifecycle'] = {'complete': False, 'scope': 'not requested in exploratory replay'}
    except Exception as error:
        report['lifecycle'] = {'complete': False, 'error': type(error).__name__ + ': ' + str(error)}
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        raise
    for mode in modes:
        directory = out / mode
        directory.mkdir()
        trace_a, trace_b = directory / 'a.jsonl', directory / 'b.jsonl'
        mock_mode = ('broken' if mode == 'real_epipe' else 'stale_ready' if mode == 'ready_error' else
                     'signal' if mode == 'signal_eintr' else
                     'failure' if mode in ('zero', 'error', 'short_zero', 'short_error') else 'normal')
        a = fastchess.EngineCommand('mock-a', (sys.executable, str(mock), str(trace_a), mock_mode))
        b = fastchess.EngineCommand('mock-b', (sys.executable, str(mock), str(trace_b), 'normal'))
        argv = fastchess.single_game_argv(binary, a, b, opening_pgn=book, opening_start=1, out=directory)
        argv[argv.index('tc=30:00+3')] = 'tc=0:01+0'
        fault_log = directory / 'fault.txt'
        env = dict(os.environ, LD_PRELOAD=str(shim_binary), ROVE_TEST_WRITE_MODE=mode,
                   ROVE_TEST_WRITE_TARGET=str(binary), ROVE_TEST_WRITE_LOG=str(fault_log))
        for key in ('ROVE_START_FD', 'ROVE_START_JOB', 'ROVE_START_PROTOCOL', 'ROVE_OPENING_FD'):
            env.pop(key, None)
        started = time.monotonic()
        forced = False
        with (directory / 'runner.log').open('wb') as stream:
            process = subprocess.Popen(argv, cwd=directory, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=90 if mode == 'short_error_wait' else 20)
            except subprocess.TimeoutExpired:
                forced = True
                fastchess.signal_owned_group(process.pid, signal.SIGTERM)
                try:
                    code = process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    fastchess.signal_owned_group(process.pid, signal.SIGKILL)
                    code = process.wait(timeout=5)
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            group_absent = True
        else:
            group_absent = False
            fastchess.signal_owned_group(process.pid, signal.SIGKILL)
        lines = fault_log.read_text(encoding='ascii').splitlines() if fault_log.exists() else []
        inputs = {name: [row.get('line') for row in _rows(path) if row.get('event') == 'input']
                  for name, path in (('a', trace_a), ('b', trace_b))}
        goes = {name: [line for line in rows if isinstance(line, str) and line.startswith('go')]
                for name, rows in inputs.items()}
        pgn_file = directory / 'game.pgn'
        pgn = pgn_file.read_text(encoding='utf-8') if pgn_file.exists() else ''
        log_text = (directory / 'runner.log').read_text(encoding='utf-8', errors='replace')
        raw_file = directory / 'raw.log'
        raw_text = raw_file.read_text(encoding='utf-8', errors='replace') if raw_file.exists() else ''
        stale_accepted = mode == 'ready_error' and 'Engine mock-a is responsive' in raw_text
        report['cases'].append({'mode': mode, 'fault_records': lines, 'go': goes, 'returncode': code,
                                'elapsed_seconds': round(time.monotonic()-started, 3),
                                'forced_cleanup': forced, 'group_absent': group_absent,
                                'stale_readyok_accepted': stale_accepted,
                                'pgn': pgn, 'runner_log_tail': log_text[-2048:]})
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        expected_records = 2 if mode in ('short_zero', 'short_error', 'short_eintr',
                                          'short_error_wait', 'signal_eintr') else 1
        if len(lines) != expected_records:
            raise AssertionError(f'{mode}: unexpected injection count: {lines!r}')
        if mode == 'signal_eintr':
            signal_row = lines[1].split()
            if (len(signal_row) != 3 or signal_row[0] != 'SIGNAL' or
                    not signal_row[1].isdigit() or int(signal_row[1]) <= 0 or signal_row[2] != '0'):
                raise AssertionError('thread-directed SIGINT was not sent successfully')
        records = [line.split() for line in (lines[:1] if mode == 'signal_eintr' else lines)]
        if any(len(row) != 4 or row[0] != mode for row in records):
            raise AssertionError(f'{mode}: malformed injection record')
        requested, written, error = map(int, records[0][1:])
        if mode == 'short' and not (0 < written < requested and error == 0):
            raise AssertionError('short injection did not produce a positive partial write')
        if mode == 'eintr' and (written != -1 or error != 4):
            raise AssertionError('EINTR injection did not occur')
        if mode == 'signal_eintr' and (written != -1 or error != 4 or
                not any(row.get('event') == 'signal_wait' for row in _rows(trace_a))):
            raise AssertionError('blocked write did not receive thread-directed SIGINT/EINTR')
        if mode == 'zero' and (written != 0 or error != 0):
            raise AssertionError('zero injection did not occur')
        if mode == 'error' and (written != -1 or error != 5):
            raise AssertionError('EIO injection did not occur')
        if mode == 'ready_error' and (written != -1 or error != 5 or
                not any(row.get('event') == 'stale_readyok_sent' for row in _rows(trace_a))):
            raise AssertionError('failed isready or stale readyok fixture did not occur')
        if stale_accepted:
            raise AssertionError('failed isready was accepted after a stale readyok')
        if mode == 'real_epipe' and (written != -1 or error != 32 or
                not any(row.get('event') == 'stdin_closed' for row in _rows(trace_a))):
            raise AssertionError('actual closed pipe did not produce EPIPE')
        if mode in ('short_zero', 'short_error', 'short_eintr', 'short_error_wait'):
            second_requested, second_written, second_error = map(int, records[1][1:])
            if not (0 < written < requested and second_requested == requested - written and error == 0):
                raise AssertionError(f'{mode}: first short write or retried suffix differs')
            expected = {'short_zero': (0, 0), 'short_error': (-1, 5),
                        'short_error_wait': (-1, 5), 'short_eintr': (-1, 4)}[mode]
            if (second_written, second_error) != expected:
                raise AssertionError(f'{mode}: second injected result differs')
        if mode == 'short_error_wait' and not 55 <= time.monotonic() - started < 90:
            raise AssertionError('owned waiting fixture did not traverse Fastchess cleanup timeout')
        if forced or not group_absent:
            raise AssertionError(f'{mode}: fixture process group did not settle')
        if mode in ('short', 'eintr', 'short_eintr'):
            if (code != 0 or len(goes['a']) != 1 or len(goes['b']) != 1 or
                    not all(line.startswith('go wtime ') and ' btime ' in line for xs in goes.values() for line in xs) or
                    '[Result "0-1"]' not in pgn or 'd8h4' not in pgn):
                raise AssertionError(f'{mode}: complete fixture GO/game was not preserved')
        else:
            if goes['a'] or goes['b']:
                raise AssertionError(f'{mode}: fixture observed a GO-like line after failed write; delivery is ambiguous')
            if code == 0 or pgn.strip():
                raise AssertionError(f'{mode}: failed write was accepted as a scored fixture game')
    report['complete'] = (source is not None and report['lifecycle'].get('complete') is True and
                          tuple(modes) == ALL_MODES and len(report['cases']) == len(ALL_MODES))
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = actual_check(args.build, args.out, source=args.source)
    print(json.dumps({'complete': result['complete'], 'cases': len(result['cases'])}))
