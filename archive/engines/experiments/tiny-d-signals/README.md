# Blocked private-signal D runtime experiment

This is one independent runtime-source architecture on the frozen **0x88
TinyD** scalar/HQ controls. It does not incorporate the unselected pure
bitboard experiment or the separate protocol/loader tracks. Production
compilation remains GCC 13.3 `-Oz -flto`, with the same worker count, TT size,
64-bit ABI, board, HCE/hash, search, coherent full-key TT and ELF layout.

**The candidate is unselected because it increases complete-file size.** The
first native cost was measured before the runtime proof campaign. No compiler
sweep or alternate notification architecture was added after that result.

| Complete artifact | Frozen TinyD | Private signals | Delta |
|---|---:|---:|---:|
| Scalar native ELF | 8,540 B | 8,796 B | +256 B |
| HQ native ELF | 8,928 B | 9,184 B | +256 B |
| Scalar own-restoring ELF | 8,806 B | 9,008 B | +202 B |
| HQ own-restoring ELF | 9,142 B | 9,363 B | +221 B |

The standalone files still need no libc, pthread, TLS, interpreter or runtime
external program. Both complete native forms and own-restoring files reproduce
byte identically. `.text` increases by 247 bytes in each backend, read-only
data is unchanged, and alignment accounts for the remaining nine bytes.
`Board`, `Worker` and TT entry layouts are unchanged. No file is within 4,096 B.

## Notification contract

Before cloning, main blocks USR1 and USR2, preserving other inherited blocked
signals, then resets the two private dispositions to DFL. This handles an
inherited IGN without allowing a default action during setup. All threads keep
both signals blocked. No asynchronous C handler or restorer trampoline runs.

Workers synchronously consume USR1 with `rt_sigtimedwait`. Main consumes USR2
for readiness and completion. Every internal send uses
`tgkill(tgid, specific_tid, signal)`; there is no process-directed broadcast.
Standard signal coalescing is safe because **atomic state is the authority**:
workers execute only for a new epoch, readiness waits check the counter, and
main waits for the exact completed epoch. Signals only wake a condition loop.
An early pending work signal, stale completion or merged readiness notification
does not create an extra job or replace a missing completion.

The job epoch is release-published after all shared job state. The last worker
retains the pending decrement's acquire/release ordering, emits bestmove, then
release-publishes completion before notifying main. The next command cannot
reset the board or workers while that output is in progress. Quit/EOF cancel
active work, publish quitting, notify each created live worker and retain the
shared futex join on kernel-cleared TIDs. A sampled worker may exit before its
shutdown notification; ESRCH is accepted only after quitting. Other notification
errors fail closed. Wait/send EINTR is retried; setup and unexpected wait errors
terminate the process group through the existing raw exit-group path.

Without interruption, one `go` requires **W thread-targeted work sends plus one
final completion send**. At 511 search workers this is 512 notification syscalls per job, rather
than a constant-size futex wake broadcast. Startup readiness and shutdown also
send per worker. These dispatch costs are recorded without an NPS, strength or
hardware-scaling claim. Idle workers sleep in the kernel; there is no spin-idle
or asynchronous handler computation. EINTR retries can add syscall attempts.

The Linux x86-64 raw ABI uses an eight-byte kernel signal set and a 32-byte
action with handler, flags, restorer and mask fields. The syscall numbers are
13/14/128/234 for action/mask/synchronous wait/tgkill. This uses kernel layouts
rather than libc's larger signal-set structure. The ABI and behavior were
checked against [Linux's x86 kernel signal definitions](https://raw.githubusercontent.com/torvalds/linux/v6.6/arch/x86/include/asm/signal.h),
[native action layout](https://raw.githubusercontent.com/torvalds/linux/v6.6/arch/x86/include/uapi/asm/signal.h),
[the Linux implementation](https://raw.githubusercontent.com/torvalds/linux/v6.6/kernel/signal.c),
[synchronous waiting](https://man7.org/linux/man-pages/man2/sigwaitinfo.2.html)
and [thread-directed delivery](https://man7.org/linux/man-pages/man2/tgkill.2.html).

## Reproduce

All outputs must be new absolute paths outside Git:

```sh
python3 engines/experiments/tiny-d-signals/build.py \
  --out /absolute/external/signal-D
python3 engines/experiments/tiny-d-signals/check.py \
  --build /absolute/external/signal-D/build.json \
  --out /absolute/external/signal-D-check
python3 engines/experiments/tiny-d-signals/algorithms.py \
  --build /absolute/external/signal-D/build.json \
  --out /absolute/external/signal-D-search --timeout 60
python3 engines/experiments/tiny-d-signals/cost.py \
  --build /absolute/external/signal-D/build.json \
  --out /absolute/external/signal-D-cost
python3 engines/experiments/tiny-d-signals/compare_controls.py \
  --build /absolute/external/signal-D/build.json \
  --control /absolute/external/frozen-TinyD/build.json \
  --out /absolute/external/signal-D-comparison
python3 engines/experiments/tiny-d-signals/test_signals.py \
  --source-root /absolute/external/signal-D/sources \
  --out /absolute/external/signal-D-runtime
```

The common executable gate passed **36/36 groups across six distinct native /
own-restoring files plus two color-exchanged bounded games**. It verifies fixed
startup TIDs, UCI/rules/state, actual search, active cancellation, quit/EOF and
short legal play. Separate production checks observed retained PVS/QS/TT/
history/continuation/correction, halfmove-sensitive TT context `[0,916]`, EP
correction exclusion and PLY-cap cancellation retaining the completed witness.
The two deterministic one-worker backends matched exact depth-four replies in
five positions. Independent read-only concurrency/ABI review found no concrete
blocker in the frozen runtime.

Signal-specific probes are a separate runtime-only qualification. Their
external reports bind the exact source, controlled fixture transformations and
whole fixture binaries; they are not substitutes for the real chess executable
tests. All **13/13 probes passed**: 256 immediate generations; gated workers
with private signals pending before their first wait; stale and wrong-target
USR1/USR2; inherited IGN plus USR1/USR2/ALRM masks; zero idle CPU ticks; clone
failure after zero/one successes; mask/action/wait/notification failures ending
with status 2; EINTR retry; and a genuine kernel-observed late-shutdown ESRCH.
Owned process groups were gone at the end. The source stayed unchanged during
the bounded 60-second-budget campaign, which completed in under five seconds.

The signal architecture remains unselected even when functional checks pass.
The frozen controls and first-cost report remain preserved outside Git. No
additional profiles, 512-thread startup campaign or performance measurement is
part of this experiment.
