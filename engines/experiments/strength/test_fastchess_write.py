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
             'short_zero', 'short_error', 'real_epipe', 'short_error_wait',
             'full_signal_other', 'short_full_signal_other', 'full_then_drain')

SHIM = r'''#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <poll.h>
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
static atomic_int poll_started = 0;
static atomic_int cancel_sent = 0;
static long writer_tid = -1;
static void log_line(const char *line) {
    const char *path = getenv("ROVE_TEST_WRITE_LOG");
    if (!path) return;
    int logfd = open(path, O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC, 0600);
    if (logfd >= 0) { syscall(SYS_write, logfd, line, strlen(line)); close(logfd); }
}
static void *interrupt_other(void *unused) {
    (void)unused;
    for (int i = 0; i < 10000 && !atomic_load(&poll_started); ++i) usleep(1000);
    long target = syscall(SYS_gettid);
    long result = atomic_load(&poll_started) ? syscall(SYS_tgkill, getpid(), (pid_t)target, SIGINT) : -2;
    if (!result) atomic_store(&cancel_sent, 1);
    char row[128];
    snprintf(row, sizeof(row), "OTHER_SIGNAL %ld %ld %ld\n", writer_tid, target, result);
    log_line(row);
    return NULL;
}
int rove_test_poll(struct pollfd *fds, nfds_t count, int timeout) __asm__("poll");
int rove_test_poll(struct pollfd *fds, nfds_t count, int timeout) {
    const char *mode = getenv("ROVE_TEST_WRITE_MODE");
    const char *target = getenv("ROVE_TEST_WRITE_TARGET");
    char exe[4096];
    ssize_t exe_len = readlink("/proc/self/exe", exe, sizeof(exe)-1);
    if (exe_len >= 0) exe[exe_len] = '\0';
    int relevant = 0;
    if (mode && target && exe_len >= 0 && strcmp(exe, target) == 0 &&
        (!strcmp(mode, "full_signal_other") || !strcmp(mode, "short_full_signal_other") ||
         !strcmp(mode, "full_then_drain"))) {
        for (nfds_t i = 0; i < count; ++i) {
            if (fds[i].fd == pending_fd && (fds[i].events & POLLOUT)) relevant = 1;
        }
    }
    if (relevant) { atomic_store(&poll_started, 1); log_line("POLL_ENTER\n"); }
    return (int)syscall(SYS_poll, fds, count, timeout);
}
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
    if (mode && target && exe_len >= 0 && strcmp(exe, target) == 0 &&
        (!strcmp(mode, "full_signal_other") || !strcmp(mode, "short_full_signal_other")) &&
        atomic_load(&cancel_sent) && fd == pending_fd) log_line("POST_CANCEL\n");
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
                 !strcmp(mode, "short_eintr") || !strcmp(mode, "short_error_wait") ||
                 !strcmp(mode, "short_full_signal_other")))) {
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
        } else if (!strcmp(mode, "full_signal_other") || !strcmp(mode, "short_full_signal_other") ||
                   !strcmp(mode, "full_then_drain")) {
            int flags = fcntl(fd, F_GETFL);
            char filler[4096];
            memset(filler, ' ', sizeof(filler));
            if (strcmp(mode, "short_full_signal_other")) filler[sizeof(filler)-1] = '\n';
            ssize_t fill_result = -1;
            if (flags < 0 || !(flags & O_NONBLOCK)) {
                result = -1; err = EINVAL;
            } else {
                if (fcntl(fd, F_SETPIPE_SZ, 4096) != 4096) {
                    result = -1; err = EINVAL;
                    goto record_result;
                }
                size_t fill_size = !strcmp(mode, "short_full_signal_other") ? 1 : sizeof(filler);
                do { fill_result = syscall(SYS_write, fd, filler, fill_size); }
                while (fill_result > 0);
                if (fill_result != -1 || errno != EAGAIN) {
                    result = -1; err = EINVAL;
                } else {
                    pending_fd = fd;
                    writer_tid = syscall(SYS_gettid);
                    if (strcmp(mode, "full_then_drain")) {
                        pthread_t thread;
                        if (pthread_create(&thread, NULL, interrupt_other, NULL) != 0) {
                            result = -1; err = EINVAL;
                        } else {
                            pthread_detach(thread);
                            result = -1; err = EAGAIN;
                        }
                    } else {
                        result = -1; err = EAGAIN;
                    }
                }
            }
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
                /* Force a blocking syscall just for this EINTR injection;
                 * production writeInput keeps its write end nonblocking. */
                if (fill_result != -1 || errno != EAGAIN || fcntl(fd, F_SETFL, flags & ~O_NONBLOCK) < 0) {
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
                        if (fcntl(fd, F_SETFL, flags) < 0) { result = -1; err = EINVAL; }
                        pthread_join(thread, NULL);
                        atomic_store_explicit(&failed_after_partial, 1, memory_order_relaxed);
                    }
                }
            }
        } else {
            result = -1; err = EINVAL;
        }
record_result:
        if (stage == 1 && strcmp(mode, "short_eintr") && strcmp(mode, "short_full_signal_other"))
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

LATE_REGISTER_CPP = r'''
#include <core/config/config.hpp>
#include <core/globals/globals.hpp>
#include <engine/process/process_posix.hpp>
#include <matchmaking/tournament/base/tournament.hpp>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <iostream>
#include <memory>
#include <spawn.h>
#include <thread>

namespace fastchess { const char* version = "fixture"; }
using namespace std::chrono_literals;
using fastchess::engine::process::Process;
using fastchess::engine::process::Line;
static std::atomic_bool spawned{false}, snapshot{false}, resume_spawn{false}, finished{false};
static std::atomic_bool write_failed{false}, init_ok{false};

extern "C" int __real_posix_spawnp(pid_t*, const char*, const posix_spawn_file_actions_t*,
                                    const posix_spawnattr_t*, char* const[], char* const[]);
extern "C" int __wrap_posix_spawnp(pid_t* p, const char* path, const posix_spawn_file_actions_t* f,
                                    const posix_spawnattr_t* a, char* const args[], char* const env[]) {
    const int rc = __real_posix_spawnp(p, path, f, a, args, env);
    if (!rc) {
        spawned.store(true);
        const auto deadline = std::chrono::steady_clock::now() + 10s;
        while (!resume_spawn.load() && std::chrono::steady_clock::now() < deadline)
            std::this_thread::sleep_for(1ms);
    }
    return rc;
}
extern "C" void __real__ZN9fastchess16writeToOpenPipesEv();
extern "C" void __wrap__ZN9fastchess16writeToOpenPipesEv() {
    __real__ZN9fastchess16writeToOpenPipesEv();
    snapshot.store(true);
}

class TestTournament : public fastchess::BaseTournament {
  public:
    TestTournament() : BaseTournament({}) {}
    void startNext() override {}
    void enqueue(std::function<void()> f) { pool_.enqueue(std::move(f)); }
};

int main(int argc, char** argv) {
    if (argc != 4) return 1;
    // If the fixture regresses, the harness bounds itself; the owned engine
    // exits independently after five seconds and no unrelated process is touched.
    std::thread([] { std::this_thread::sleep_for(15s); std::_Exit(124); }).detach();
    auto conf = std::make_unique<fastchess::config::Tournament>();
    conf->config_name = argv[3];
    conf->concurrency = 1;
    fastchess::config::TournamentConfig = std::move(conf);
    fastchess::config::EngineConfigs = std::make_unique<std::vector<fastchess::EngineConfiguration>>(1);
    fastchess::config::EngineConfigs->at(0).name = "fixture";
    auto* tournament = new TestTournament;
    tournament->enqueue([&] {
        Process p;
        auto result = p.init("", "/usr/bin/python3", std::string(argv[1]) + " " + argv[2], "fixture");
        init_ok.store(bool(result));
        if (result) write_failed.store(!bool(p.writeInput("go wtime 100 btime 100\n")));
        finished.store(true);
    });
    auto until = std::chrono::steady_clock::now() + 10s;
    while (!spawned.load() && std::chrono::steady_clock::now() < until) std::this_thread::sleep_for(1ms);
    if (!spawned.load()) { delete tournament; return 2; }
    std::thread destroy([&] { delete tournament; });
    while (!snapshot.load() && std::chrono::steady_clock::now() < until) std::this_thread::sleep_for(1ms);
    if (!snapshot.load()) { resume_spawn.store(true); destroy.join(); return 3; }
    if (fastchess::atomic::stop.load()) { resume_spawn.store(true); destroy.join(); return 4; }
#ifdef CHECK_IO_SHUTDOWN
    if (!fastchess::atomic::io_shutdown.load()) { resume_spawn.store(true); destroy.join(); return 6; }
#endif
    resume_spawn.store(true);
    destroy.join();
    if (!finished.load() || !init_ok.load() || !write_failed.load()) return 5;
    std::cout << "late-register-rejected\n";
    return 0;
}
'''

LATE_REGISTER_ENGINE = r'''
#!/usr/bin/env python3
import os
import selectors
import sys
import time

trace = sys.argv[1]
with open(trace, "a", encoding="utf-8") as out:
    out.write("START\n")
    out.flush()
    sel = selectors.DefaultSelector()
    sel.register(sys.stdin, selectors.EVENT_READ)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not sel.select(min(0.05, max(0, deadline - time.monotonic()))):
            continue
        line = sys.stdin.readline()
        if not line:
            break
        out.write("INPUT " + line)
        out.flush()
        if line == "quit\n":
            break
    sel.close()
    out.write("EXIT\n")
'''

# Hold the writer at poll until readOutput consumes the shared interrupt.
CANCEL_POLL_SHIM = r'''#define _GNU_SOURCE
#include <poll.h>
#include <stdatomic.h>
#include <dlfcn.h>
#include <spawn.h>
#include <sys/syscall.h>
#include <unistd.h>
static atomic_int held = 0, reader_armed = 0, released = 0;
static atomic_int spawn_calls = 0;
int rove_poll_held(void) { return atomic_load(&held); }
int rove_reader_armed(void) { return atomic_load(&reader_armed); }
int rove_spawn_calls(void) { return atomic_load(&spawn_calls); }
void rove_reset_reader(void) { atomic_store(&reader_armed, 0); }
void rove_release_poll(void) { atomic_store(&released, 1); }
int posix_spawnp(pid_t *pid, const char *path, const posix_spawn_file_actions_t *acts,
                 const posix_spawnattr_t *attr, char *const argv[], char *const envp[]) {
    atomic_fetch_add(&spawn_calls, 1);
    typedef int (*fn)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                      const posix_spawnattr_t *, char *const[], char *const[]);
    fn real = (fn)dlsym(RTLD_NEXT, "posix_spawnp");
    return real ? real(pid, path, acts, attr, argv, envp) : -1;
}
int posix_spawn(pid_t *pid, const char *path, const posix_spawn_file_actions_t *acts,
                const posix_spawnattr_t *attr, char *const argv[], char *const envp[]) {
    atomic_fetch_add(&spawn_calls, 1);
    typedef int (*fn)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                      const posix_spawnattr_t *, char *const[], char *const[]);
    fn real = (fn)dlsym(RTLD_NEXT, "posix_spawn");
    return real ? real(pid, path, acts, attr, argv, envp) : -1;
}
int rove_test_poll(struct pollfd *fds, nfds_t count, int timeout) __asm__("poll");
int rove_test_poll(struct pollfd *fds, nfds_t count, int timeout) {
    if (count && (fds[0].events & POLLOUT) && !atomic_load(&released)) {
        atomic_store(&held, 1);
        while (!atomic_load(&released)) usleep(1000);
    } else if (count > 1 && (fds[0].events & POLLIN)) {
        atomic_store(&reader_armed, 1);
    }
    return (int)syscall(SYS_poll, fds, count, timeout);
}
'''

INIT_FAIL_SHIM = r'''#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <spawn.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>
static atomic_int armed = 0, failures = 0, spawn_calls = 0;
void rove_arm_fault(void) { atomic_store(&armed, 1); }
int rove_fault_count(void) { return atomic_load(&failures); }
int rove_spawn_calls(void) { return atomic_load(&spawn_calls); }
int pipe2(int fds[2], int flags) {
    const char *mode = getenv("ROVE_INIT_FAULT");
    if (atomic_load(&armed) && mode && strstr(mode, "pipe2-") == mode &&
        atomic_exchange(&failures, 1) == 0) {
        errno = strstr(mode, "enosys") ? ENOSYS : EIO;
        return -1;
    }
    return (int)syscall(SYS_pipe2, fds, flags);
}
int fcntl(int fd, int cmd, ...) {
    int arg = 0;
    if (cmd == F_SETFD || cmd == F_SETFL) {
        va_list ap;
        va_start(ap, cmd);
        arg = va_arg(ap, int);
        va_end(ap);
    } else if (cmd != F_GETFD && cmd != F_GETFL) {
        errno = ENOTSUP;
        return -1;
    }
    const char *mode = getenv("ROVE_INIT_FAULT");
    if (atomic_load(&armed) && mode &&
        ((!strcmp(mode, "fcntl-getfd") && cmd == F_GETFD) ||
         (!strcmp(mode, "fcntl-getfl") && cmd == F_GETFL) ||
         (!strcmp(mode, "fcntl-setfl") && cmd == F_SETFL)) &&
        atomic_exchange(&failures, 1) == 0) {
        errno = EIO;
        return -1;
    }
    return (int)syscall(SYS_fcntl, fd, cmd, arg);
}
int posix_spawnp(pid_t *pid, const char *path, const posix_spawn_file_actions_t *acts,
                 const posix_spawnattr_t *attr, char *const argv[], char *const envp[]) {
    atomic_fetch_add(&spawn_calls, 1);
    typedef int (*fn)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                      const posix_spawnattr_t *, char *const[], char *const[]);
    fn real = (fn)dlsym(RTLD_NEXT, "posix_spawnp");
    return real ? real(pid, path, acts, attr, argv, envp) : -1;
}
int posix_spawn(pid_t *pid, const char *path, const posix_spawn_file_actions_t *acts,
                const posix_spawnattr_t *attr, char *const argv[], char *const envp[]) {
    atomic_fetch_add(&spawn_calls, 1);
    typedef int (*fn)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                      const posix_spawnattr_t *, char *const[], char *const[]);
    fn real = (fn)dlsym(RTLD_NEXT, "posix_spawn");
    return real ? real(pid, path, acts, attr, argv, envp) : -1;
}
'''

CANCEL_PROCESS_CPP = r'''#include <core/globals/globals.hpp>
#include <engine/process/process_posix.hpp>
#include <atomic>
#include <chrono>
#include <dlfcn.h>
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>
namespace fastchess { const char* version = "fixture"; }
using fastchess::engine::process::Process;
using fastchess::engine::process::Line;
using namespace std::chrono_literals;
static bool wait_flag(const std::function<bool()>& check, std::chrono::milliseconds timeout) {
    auto until = std::chrono::steady_clock::now() + timeout;
    while (std::chrono::steady_clock::now() < until) {
        if (check()) return true;
        std::this_thread::sleep_for(2ms);
    }
    return false;
}
int main(int argc, char** argv) {
    if (argc != 4) return 90;
    std::string args = std::string("-u ") + argv[1] + " " + argv[2] + " " + argv[3];
    const std::string mode = argv[3];
    const bool pre_shutdown = mode == "pre-shutdown";
    const bool init_fault = mode.rfind("pipe2-", 0) == 0 || mode.rfind("fcntl-", 0) == 0;
    const bool constructor_fault = mode.rfind("pipe2-ctor-", 0) == 0;
    auto arm = reinterpret_cast<void(*)()>(dlsym(RTLD_DEFAULT, "rove_arm_fault"));
    auto faults = reinterpret_cast<int(*)()>(dlsym(RTLD_DEFAULT, "rove_fault_count"));
    auto calls = reinterpret_cast<int(*)()>(dlsym(RTLD_DEFAULT, "rove_spawn_calls"));
    if (init_fault && (!arm || !faults || !calls)) return 15;
    if (constructor_fault) arm();
    std::unique_ptr<Process> holder;
    try { holder = std::make_unique<Process>(); }
    catch (const std::exception&) {
        if (!constructor_fault || faults() != 1 || calls() != 0) return 16;
        std::cout << "init-failure-ok\n";
        return 0;
    }
    if (constructor_fault) return 17;
    Process& process = *holder;
    if (init_fault) arm();
    if (pre_shutdown) fastchess::atomic::io_shutdown = true;
    auto initialized = process.init("/tmp", "/usr/bin/python3", args, "cancellation");
    if (init_fault) {
        if (initialized || faults() != 1 || calls() != 0) return 18;
        process.terminate();
        std::cout << "init-failure-ok\n";
        return 0;
    }
    if (pre_shutdown) {
        if (initialized || !calls || calls() != 0) return 14;
        process.terminate();
        fastchess::atomic::io_shutdown = false;
        std::cout << "pre-shutdown-ok\n";
        return 0;
    }
    if (!initialized) return 1;
    if (std::string(argv[3]) == "graceful") {
        if (!process.writeInput("hello\n")) return 2;
        std::vector<Line> lines;
        if (!process.readOutput(lines, "ACK:hello", 5s)) return 3;
        fastchess::atomic::stop = true;
        if (!process.writeInput("stop\n") || !process.writeInput("quit\n")) return 4;
        process.terminate();
        fastchess::atomic::stop = false;
        std::cout << "graceful-ok\n";
        return 0;
    }
    auto held = reinterpret_cast<int(*)()>(dlsym(RTLD_DEFAULT, "rove_poll_held"));
    auto armed = reinterpret_cast<int(*)()>(dlsym(RTLD_DEFAULT, "rove_reader_armed"));
    auto reset = reinterpret_cast<void(*)()>(dlsym(RTLD_DEFAULT, "rove_reset_reader"));
    auto release = reinterpret_cast<void(*)()>(dlsym(RTLD_DEFAULT, "rove_release_poll"));
    if (!held || !armed || !reset || !release) return 5;
    int interrupt_fd = -1, owned = 0;
    fastchess::process_list.lock();
    for (const auto& item : fastchess::process_list) { interrupt_fd = item.fd_write; ++owned; }
    fastchess::process_list.unlock();
    char target[256];
    std::string fdpath = "/proc/self/fd/" + std::to_string(interrupt_fd);
    auto n = readlink(fdpath.c_str(), target, sizeof(target)-1);
    if (owned != 1 || n < 0) return 12;
    target[n] = 0;
    const std::string expected = std::string(argv[3]) == "sink-pipe" ? "pipe:[" : "anon_inode:[eventfd]";
    if (std::string(target).rfind(expected, 0) != 0) return 13;
    std::vector<Line> ready;
    if (!process.readOutput(ready, "READY", 5s)) return 6;
    reset();
    std::atomic<bool> writer_done{false}, writer_rejected{false}, reader_done{false}, reader_interrupted{false};
    std::thread writer([&] {
        auto result = process.writeInput(std::string(1024*1024, 'x'));
        writer_rejected = !result;
        writer_done = true;
    });
    if (!wait_flag([&] { return held(); }, 4s)) std::_Exit(7);
    std::thread reader([&] {
        std::vector<Line> lines;
        auto result = process.readOutput(lines, "NEVER", 0ms);
        reader_interrupted = !result && result.message == "Interrupted by control pipe";
        reader_done = true;
    });
    if (!wait_flag([&] { return armed(); }, 4s)) std::_Exit(8);
    // No global stop: the reader must consume the single interrupt first.
    fastchess::writeToOpenPipes();
    if (!wait_flag([&] { return reader_done.load(); }, 4s) || !reader_interrupted) std::_Exit(9);
    reader.join();
    release();
    if (!wait_flag([&] { return writer_done.load(); }, 2s) || !writer_rejected) std::_Exit(10);
    writer.join();
    if (process.writeInput("quit\n")) return 11;
    process.terminate();
    std::cout << "consumed-interrupt-ok\n";
}
'''

CANCEL_ENGINE = """import sys, time
trace, mode = sys.argv[1:]
if mode.startswith('sink-'):
    print('READY', flush=True)
    time.sleep(3)
else:
    for line in sys.stdin:
        with open(trace, 'a', encoding='utf-8') as out:
            out.write(line)
        if line.strip() == 'quit':
            break
        print('ACK:' + line.strip(), flush=True)
"""

CROSS_SPAWN_CPP = r'''#include <core/globals/globals.hpp>
#include <engine/process/process_posix.hpp>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <iostream>
#include <spawn.h>
#include <string>
#include <thread>
#include <vector>
namespace fastchess { const char* version = "fixture"; }
using fastchess::engine::process::Process;
using fastchess::engine::process::Line;
using namespace std::chrono_literals;
static std::atomic<bool> first_stalled{false}, release_first{false};
extern "C" int __real_posix_spawnp(pid_t*, const char*, const posix_spawn_file_actions_t*,
                                    const posix_spawnattr_t*, char* const[], char* const[]);
extern "C" int __wrap_posix_spawnp(pid_t* pid, const char* path, const posix_spawn_file_actions_t* acts,
                                    const posix_spawnattr_t* attr, char* const argv[], char* const envp[]) {
    bool first = false;
    for (size_t i = 0; argv[i]; ++i) if (!std::strcmp(argv[i], "first")) first = true;
    if (first) {
        first_stalled = true;
        auto deadline = std::chrono::steady_clock::now() + 10s;
        while (!release_first && std::chrono::steady_clock::now() < deadline)
            std::this_thread::sleep_for(1ms);
        if (!release_first) return EAGAIN;
    }
    return __real_posix_spawnp(pid, path, acts, attr, argv, envp);
}
int main(int argc, char** argv) {
    if (argc != 4) return 90;
    Process first, second;
    std::atomic<bool> first_ok{false};
    std::thread one([&] {
        first_ok = bool(first.init("/tmp", "/usr/bin/python3",
            std::string("-u ") + argv[1] + " " + argv[2] + " first", "first"));
    });
    auto deadline = std::chrono::steady_clock::now() + 10s;
    while (!first_stalled && std::chrono::steady_clock::now() < deadline) std::this_thread::sleep_for(1ms);
    if (!first_stalled) std::_Exit(2);
    // A is paused before spawn with its prepared FDs open while B starts.
    auto second_ok = second.init("/tmp", "/usr/bin/python3",
        std::string("-u ") + argv[1] + " " + argv[3] + " second", "second");
    release_first = true;
    one.join();
    if (!first_ok || !second_ok) return 3;
    int interrupts = 0;
    const char* forced = std::getenv("FASTCHESS_FORCE_PIPE_INTERRUPT");
    const std::string expected = forced && *forced && *forced != '0' ? "pipe:[" : "anon_inode:[eventfd]";
    fastchess::process_list.lock();
    for (const auto& item : fastchess::process_list) {
        char target[256];
        std::string fdpath = "/proc/self/fd/" + std::to_string(item.fd_write);
        auto n = readlink(fdpath.c_str(), target, sizeof(target)-1);
        if (n < 0) { fastchess::process_list.unlock(); return 7; }
        target[n] = 0;
        if (std::string(target).rfind(expected, 0) != 0) { fastchess::process_list.unlock(); return 8; }
        ++interrupts;
    }
    fastchess::process_list.unlock();
    if (interrupts != 2) return 9;
    std::vector<Line> first_lines, second_lines;
    if (!first.readOutput(first_lines, "READY:first", 5s) ||
        !second.readOutput(second_lines, "READY:second", 5s)) return 5;
    if (!first.writeInput("quit\n") || !second.writeInput("quit\n")) return 4;
    if (!first.readOutput(first_lines, "ACK:first", 5s) ||
        !second.readOutput(second_lines, "ACK:second", 5s)) return 6;
    first.terminate();
    second.terminate();
    std::cout << "cross-spawn-ok\n";
}
'''

CROSS_SPAWN_ENGINE = """import json, os, sys, time
trace, tag = sys.argv[1:]
leaks = []
for name in os.listdir('/proc/self/fd'):
    try:
        fd = int(name)
        if fd < 3:
            continue
        target = os.readlink('/proc/self/fd/' + name)
        if target.startswith('pipe:[') or target.startswith('anon_inode:[eventfd]'):
            leaks.append([fd, target])
    except (FileNotFoundError, ValueError):
        pass
with open(trace, 'w', encoding='utf-8') as out:
    json.dump({'tag': tag, 'leaks': leaks}, out)
print('READY:' + tag, flush=True)
for line in sys.stdin:
    if line.strip() == 'quit':
        print('ACK:' + tag, flush=True)
        time.sleep(.2)
        break
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


def _cancel_process(source: Path, build_receipt: Path, built: dict, out: Path) -> dict:
    prepared = fastchess.verify_checkout(source.resolve(strict=True))
    if prepared['patch_sha256'] != built['patch_sha256']:
        raise ValueError('cancellation source does not match runner patch')
    object_root = build_receipt.resolve().parent / 'objects'
    command = built['command']['argv']
    if ('BUILDDIR=' + str(object_root) not in command or
            'BINARY_PATH=' + str(build_receipt.resolve().parent) not in command):
        raise ValueError('cancellation objects differ from runner build')
    objects = sorted(path for path in object_root.rglob('*.o')
                     if path.relative_to(object_root).as_posix() != 'src/main.o')
    if not 1 <= len(objects) <= 200 or any(path.is_symlink() or not path.is_file() for path in objects):
        raise ValueError('bounded runner objects required')
    harness = out / 'process-cancel.cc'
    harness.write_text(CANCEL_PROCESS_CPP, encoding='utf-8')
    hook_source = out / 'cancel-poll.c'
    hook_source.write_text(CANCEL_POLL_SHIM, encoding='utf-8')
    hook = out / 'cancel-poll.so'
    subprocess.run(['cc', '-std=c11', '-O0', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                    str(hook_source), '-ldl', '-o', str(hook)], check=True, timeout=60)
    init_source = out / 'init-fail.c'
    init_source.write_text(INIT_FAIL_SHIM, encoding='utf-8')
    init_hook = out / 'init-fail.so'
    subprocess.run(['cc', '-std=c11', '-O0', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                    str(init_source), '-ldl', '-o', str(init_hook)], check=True, timeout=60)
    binary = out / 'process-cancel'
    app = source / 'app'
    subprocess.run(['g++', '-std=c++17', '-O2', '-DNDEBUG', '-I' + str(app / 'src'),
                    '-I' + str(app / 'third_party'), '-I' + str(app / 'third_party/fmt/include'),
                    str(harness), *(str(path) for path in objects), '-pthread', '-ldl', '-lstdc++fs',
                    '-o', str(binary)], check=True, timeout=90)
    results = []
    with tempfile.TemporaryDirectory(prefix='rove-cancel-process-', dir='/tmp') as temporary:
        temporary = Path(temporary)
        mock = temporary / 'engine.py'
        mock.write_text(CANCEL_ENGINE, encoding='utf-8')
        modes = ('graceful', 'pre-shutdown', 'sink-eventfd', 'sink-pipe',
                 'pipe2-ctor-enosys', 'pipe2-ctor-eio', 'pipe2-interrupt-enosys',
                 'pipe2-interrupt-eio', 'fcntl-getfd', 'fcntl-getfl', 'fcntl-setfl')
        for mode in modes:
            trace = temporary / (mode + '.txt')
            env = dict(os.environ)
            env.pop('FASTCHESS_FORCE_PIPE_INTERRUPT', None)
            init_fault = mode.startswith(('pipe2-', 'fcntl-'))
            if init_fault:
                env['LD_PRELOAD'] = str(init_hook)
                env['ROVE_INIT_FAULT'] = mode
            elif mode != 'graceful':
                env['LD_PRELOAD'] = str(hook)
            if mode == 'sink-pipe' or mode.startswith('pipe2-interrupt-'):
                env['FASTCHESS_FORCE_PIPE_INTERRUPT'] = '1'
            process = subprocess.Popen([str(binary), str(mock), str(trace), mode], env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                stdout, _ = process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                fastchess.signal_owned_group(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
                raise RuntimeError(f'{mode}: cancellation fixture timed out')
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                group_absent = True
            else:
                group_absent = False
                fastchess.signal_owned_group(process.pid, signal.SIGKILL)
            expected = (b'init-failure-ok\n' if init_fault else b'graceful-ok\n' if mode == 'graceful' else b'pre-shutdown-ok\n'
                        if mode == 'pre-shutdown' else b'consumed-interrupt-ok\n')
            if process.returncode != 0 or stdout != expected or not group_absent:
                raise AssertionError(f'{mode}: actual Process cancellation failed: {stdout[-2048:]!r}')
            if mode == 'graceful' and trace.read_text(encoding='utf-8') != 'hello\nstop\nquit\n':
                raise AssertionError('graceful stop and quit were not both delivered')
            results.append({'mode': mode, 'complete': True, 'group_absent': group_absent})
    return {'complete': True, 'source_patch_sha256': prepared['patch_sha256'], 'cases': results,
            'harness_sha256': hashlib.sha256(harness.read_bytes()).hexdigest(),
            'scope': 'actual Process class; forced consumer/writer interrupt race; local fixtures only'}


def _late_registration(source: Path, build_receipt: Path, built: dict, out: Path) -> dict:
    prepared = fastchess.verify_checkout(source.resolve(strict=True))
    if prepared['patch_sha256'] != built['patch_sha256']:
        raise ValueError('late registration source does not match runner patch')
    object_root = build_receipt.resolve().parent / 'objects'
    command = built['command']['argv']
    if ('BUILDDIR=' + str(object_root) not in command or
            'BINARY_PATH=' + str(build_receipt.resolve().parent) not in command):
        raise ValueError('late registration objects differ from runner build')
    objects = sorted(path for path in object_root.rglob('*.o')
                     if path.relative_to(object_root).as_posix() != 'src/main.o')
    if not 1 <= len(objects) <= 200 or any(path.is_symlink() or not path.is_file() for path in objects):
        raise ValueError('bounded runner objects required')
    harness = out / 'late-registration.cc'
    harness.write_text(LATE_REGISTER_CPP, encoding='utf-8')
    binary = out / 'late-registration'
    app = source / 'app'
    subprocess.run(['g++', '-std=c++17', '-O2', '-DNDEBUG', '-DCHECK_IO_SHUTDOWN',
                    '-I' + str(app / 'src'), '-I' + str(app / 'third_party'),
                    '-I' + str(app / 'third_party/fmt/include'), str(harness),
                    *(str(path) for path in objects), '-pthread', '-lstdc++fs',
                    '-Wl,--wrap=posix_spawnp', '-Wl,--wrap=_ZN9fastchess16writeToOpenPipesEv',
                    '-o', str(binary)], check=True, timeout=120)
    with tempfile.TemporaryDirectory(prefix='rove-late-register-', dir='/tmp') as temporary:
        temporary = Path(temporary)
        engine = temporary / 'engine.py'
        engine.write_text(LATE_REGISTER_ENGINE, encoding='utf-8')
        trace = temporary / 'trace.txt'
        config = temporary / 'output.json'
        process = subprocess.Popen([str(binary), str(engine), str(trace), str(config)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=22)
        except subprocess.TimeoutExpired:
            fastchess.signal_owned_group(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
            raise RuntimeError('late registration fixture timed out')
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            group_absent = True
        else:
            group_absent = False
            fastchess.signal_owned_group(process.pid, signal.SIGKILL)
        rows = trace.read_text(encoding='utf-8').splitlines() if trace.is_file() else []
        if process.returncode != 0 or stdout != b'late-register-rejected\n' or rows != ['START', 'EXIT'] or not group_absent:
            raise AssertionError(f'late registration fixture failed: {stdout[-512:]!r}, {stderr[-512:]!r}, {rows!r}')
    return {'complete': True, 'source_patch_sha256': prepared['patch_sha256'],
            'harness_sha256': hashlib.sha256(harness.read_bytes()).hexdigest(),
            'group_absent': group_absent,
            'scope': 'actual BaseTournament destructor, worker and Process; owned local fixture only'}


def _cross_spawn(source: Path, build_receipt: Path, built: dict, out: Path) -> dict:
    prepared = fastchess.verify_checkout(source.resolve(strict=True))
    if prepared['patch_sha256'] != built['patch_sha256']:
        raise ValueError('cross-spawn source does not match runner patch')
    object_root = build_receipt.resolve().parent / 'objects'
    command = built['command']['argv']
    if ('BUILDDIR=' + str(object_root) not in command or
            'BINARY_PATH=' + str(build_receipt.resolve().parent) not in command):
        raise ValueError('cross-spawn objects differ from runner build')
    objects = sorted(path for path in object_root.rglob('*.o')
                     if path.relative_to(object_root).as_posix() != 'src/main.o')
    if not 1 <= len(objects) <= 200 or any(path.is_symlink() or not path.is_file() for path in objects):
        raise ValueError('bounded runner objects required')
    harness = out / 'cross-spawn.cc'
    harness.write_text(CROSS_SPAWN_CPP, encoding='utf-8')
    binary = out / 'cross-spawn'
    app = source / 'app'
    subprocess.run(['g++', '-std=c++17', '-O2', '-DNDEBUG', '-I' + str(app / 'src'),
                    '-I' + str(app / 'third_party'), '-I' + str(app / 'third_party/fmt/include'),
                    str(harness), *(str(path) for path in objects), '-pthread', '-lstdc++fs',
                    '-Wl,--wrap=posix_spawnp', '-o', str(binary)], check=True, timeout=120)
    results = []
    with tempfile.TemporaryDirectory(prefix='rove-cross-spawn-', dir='/tmp') as temporary:
        temporary = Path(temporary)
        mock = temporary / 'engine.py'
        mock.write_text(CROSS_SPAWN_ENGINE, encoding='utf-8')
        for mode in ('eventfd', 'pipe'):
            first, second = temporary / (mode + '-a.json'), temporary / (mode + '-b.json')
            env = dict(os.environ)
            env.pop('FASTCHESS_FORCE_PIPE_INTERRUPT', None)
            if mode == 'pipe':
                env['FASTCHESS_FORCE_PIPE_INTERRUPT'] = '1'
            process = subprocess.Popen([str(binary), str(mock), str(first), str(second)], env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                stdout, _ = process.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                fastchess.signal_owned_group(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
                raise RuntimeError(f'{mode}: cross-spawn fixture timed out')
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                group_absent = True
            else:
                group_absent = False
                fastchess.signal_owned_group(process.pid, signal.SIGKILL)
            if process.returncode != 0 or stdout != b'cross-spawn-ok\n' or not group_absent:
                raise AssertionError(f'{mode}: cross-spawn process failed: {stdout[-2048:]!r}')
            rows = [json.loads(path.read_text(encoding='utf-8')) for path in (first, second)]
            if rows != [{'tag': 'first', 'leaks': []}, {'tag': 'second', 'leaks': []}]:
                raise AssertionError(f'{mode}: child inherited unexpected engine or control FD: {rows!r}')
            results.append({'mode': mode, 'complete': True, 'group_absent': group_absent})
    return {'complete': True, 'source_patch_sha256': prepared['patch_sha256'], 'cases': results,
            'harness_sha256': hashlib.sha256(harness.read_bytes()).hexdigest(),
            'scope': 'two actual Process instances, overlapping spawn; local fixtures only'}


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
        'import fcntl, json, os, select, signal, stat, sys, threading, time').replace(
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
        "        if mode == 'signal_drain' and moves:\n"
        "            note(event='signal_wait')\n"
        "            print('readyok', flush=True)\n"
        "            time.sleep(.5)\n"
        "            fcntl.fcntl(0, fcntl.F_SETFL, fcntl.fcntl(0, fcntl.F_GETFL) | os.O_NONBLOCK)\n"
        "            seen = 0\n"
        "            while True:\n"
        "                try:\n"
        "                    chunk = os.read(0, 8192)\n"
        "                except BlockingIOError:\n"
        "                    break\n"
        "                if not chunk:\n"
        "                    note(event='premature_eof')\n"
        "                    os._exit(0)\n"
        "                seen += len(chunk)\n"
        "            ready, _, _ = select.select([0], [], [], .2)\n"
        "            if ready and not os.read(0, 8192):\n"
        "                note(event='premature_eof')\n"
        "                os._exit(0)\n"
        "            note(event='no_early_eof', bytes=seen)\n"
        "            os._exit(0)\n"
        "        if mode == 'delayed_drain' and moves:\n"
        "            print('readyok', flush=True)\n"
        "            note(event='delay_before_drain')\n"
        "            time.sleep(1)\n"
        "            continue\n"
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
            report['cancellation'] = _cancel_process(source, build_receipt, built, out)
            report['late_registration'] = _late_registration(source, build_receipt, built, out)
            report['cross_spawn'] = _cross_spawn(source, build_receipt, built, out)
        else:
            report['lifecycle'] = {'complete': False, 'scope': 'not requested in exploratory replay'}
            report['cancellation'] = {'complete': False, 'scope': 'not requested in exploratory replay'}
            report['late_registration'] = {'complete': False, 'scope': 'not requested in exploratory replay'}
            report['cross_spawn'] = {'complete': False, 'scope': 'not requested in exploratory replay'}
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
                     'signal_drain' if mode in ('full_signal_other', 'short_full_signal_other') else
                     'delayed_drain' if mode == 'full_then_drain' else
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
        injections = [line for line in lines if line.startswith(mode + ' ')]
        expected_records = 2 if mode in ('short_zero', 'short_error', 'short_eintr',
                                          'short_error_wait', 'short_full_signal_other') else 1
        if len(injections) != expected_records:
            raise AssertionError(f'{mode}: unexpected injection count: {lines!r}')
        if mode == 'signal_eintr':
            signals = [line for line in lines if line.startswith('SIGNAL ')]
            signal_row = signals[0].split() if len(signals) == 1 else []
            if (len(signal_row) != 3 or signal_row[0] != 'SIGNAL' or
                    not signal_row[1].isdigit() or int(signal_row[1]) <= 0 or signal_row[2] != '0'):
                raise AssertionError('thread-directed SIGINT was not sent successfully')
        records = [line.split() for line in injections]
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
        if mode in ('full_signal_other', 'short_full_signal_other', 'full_then_drain'):
            test_written, test_error = (map(int, records[1][2:]) if mode == 'short_full_signal_other' else
                                        (written, error))
            if (test_written != -1 or test_error != 11 or 'POLL_ENTER' not in lines or
                    not any(row.get('event') == ('delay_before_drain' if mode == 'full_then_drain' else
                                                 'signal_wait') for row in _rows(trace_a))):
                raise AssertionError(f'{mode}: full nonblocking pipe and poll were not exercised')
            if mode == 'short_full_signal_other':
                if not (0 < written < requested and error == 0 and int(records[1][1]) == requested-written):
                    raise AssertionError('partial GO prefix or remaining byte count differs')
            if mode != 'full_then_drain':
                notes = _rows(trace_a)
                if not any(row.get('event') == 'no_early_eof' and row.get('bytes', 0) > 0 for row in notes):
                    raise AssertionError('engine did not observe open input after cancellation')
                if any(row.get('event') == 'premature_eof' for row in notes) or 'POST_CANCEL' in lines:
                    raise AssertionError('cancelled writer closed or reused the uncertain input')
                signals = [line.split() for line in lines if line.startswith('OTHER_SIGNAL ')]
                if (len(signals) != 1 or len(signals[0]) != 4 or
                        not signals[0][1].isdigit() or not signals[0][2].isdigit() or
                        int(signals[0][1]) == int(signals[0][2]) or signals[0][3] != '0'):
                    raise AssertionError('SIGINT was not delivered to a distinct live thread')
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
        if mode in ('short', 'eintr', 'short_eintr', 'full_then_drain'):
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
                          report['cancellation'].get('complete') is True and
                          report['late_registration'].get('complete') is True and
                          report['cross_spawn'].get('complete') is True and
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
