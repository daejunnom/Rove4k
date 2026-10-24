# Independent no_std Tiny Rust D

This is a separate Linux x86-64 Rust D implementation. It uses `core`, its own
entry point, assembly memory primitives and raw Linux system calls. It has no
external crate, libc, pthread, TLS, interpreter or C engine backend. Existing
Tiny Rust A, its source-stream experiment and the canonical engines are kept
unchanged.

The maintained input path is the qualified ASCII streaming implementation.
Both fixed 2/18 production profiles produce a **16,816 byte complete ELF**:

| Actual production path | Complete ELF SHA-256 |
| --- | --- |
| HQ | `f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8` |
| Scalar | `bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878` |

These files exceed 4,096 bytes. Neither was compressed or admitted to an existing
image loader. The original static-only milestone and subsequent execution
receipts are separate records; a successful link was not used as runtime proof.

## Source and ownership

- `board.rs` ports the bounded mailbox/copy-make board and adds maintained piece
  bitboards plus actual scalar and Hyperbola Quintessence slider attack paths.
  `ROVE_HQ=0/1` selects the path; the initial profile uses HQ. Promotion,
  castling, legal EP identity, incremental HCE/hash, halfmove/dead material and
  reversible history context are covered by the board/state qualification below.
- `search.rs` ports the coherent full-key TT and fixed per-worker state to
  `core` atomics and startup mmap. `learn`, the Worker implementation and TT
  get/put have source-token identity with Tiny Rust A. The monotonic clock is a
  raw `clock_gettime` call. Raw-stack and mapping-trace evidence below covers the
  recursive path, separately from std-adapter allocator instrumentation.
- `os.rs` owns `_start`, the separate raw-clone assembly trampoline, syscall
  wrappers, private/shared futex contracts, guarded stack mappings and assembly
  `memcpy`, `memmove`, `memset`, `memcmp` and `bcmp`.
- `runtime.rs` starts all fixed workers before reading input. Private Worker
  learning belongs to each child. The main thread modifies Job only after an
  acquire of the coordinator's finished generation. Each worker publishes its
  copied result with release; worker zero acquires all results, emits one full
  output message under the output gate, then publishes finished. Shutdown
  changes the wake generation, waits kernel clear-TID and only then unmaps each
  stack.
- `main.rs` owns bounded ASCII input, transactional startpos replay and the
  minimal shipping UCI interface. It supports fixed compile-time resources,
  not runtime resource options. The initial profile is two search workers plus
  the main thread, TT bits 18 and two guarded 1 MiB worker stacks.

The generation, result and job storage is process-lifetime mmap memory.
`UnsafeCell` separates phase-owned ordinary data from atomics. No mutable
reference to the whole shared runtime survives worker publication. Failed
syscalls and panic use `exit_group`; only a normally returning worker uses
thread exit. Main does not wait for a result while holding the output gate.
The control methods belong exclusively to this binary's single main controller.
The shared reference used by workers does not make concurrent `start`, `reset`
or shutdown calls safe; this is not a general-purpose concurrent pool API.

The kernel owns TID publication and clearing. The parent never writes a positive
clone return over a TID that a fast child may have cleared. Own job futexes use
PRIVATE WAIT/WAKE; clear-TID joining uses shared WAIT to match the kernel wake.

## Build without execution

```sh
python3 -I -B engines/compact/tiny-rust-d/build.py \
  --out /absolute/new/tiny-rust-d --rustc rustc \
  --workers 2 --tt-bits 18 --hq hq --reproduce
```

The output must be new and outside the checkout. The readable source, linker
script and builder are frozen before compilation. Supported compile-time input
domains are workers 1–512 and TT bits 8–26; only 2/18 is the initial measured
profile. Support for 512 workers has not been executed or claimed scalable.

The fixed recipe uses Rust 2024, size optimization, fat LTO, one codegen unit,
aborting panic, static relocation, no default linker libraries, `-nostdlib`, a
local linker script and stripped symbols. The complete ELF counts toward the
native size; no compressed payload is presented as the whole file.

The builder never runs an ELF. It records static program/section inspection,
no interpreter/dynamic dependency/TLS/unwind section/FS-or-GS memory access,
and non-executable GNU stack. An auxiliary unstripped link has no undefined
symbols; all of its allocatable sections, addresses and BSS sizes must match
the selected stripped native image. Its symbol list also exposes the own
assembly runtime primitives. The linker script is a selected layout, not a
claim that all possible link recipes have been minimized.

## Bounded qualification and evidence classes

ASCII promotion changes `main.rs` and adds a safe byte parser behind the existing
`Board::parse(&str)` compatibility wrapper. Board geometry, move generation,
play, evaluation and history bodies are identical to the preserved control;
search, runtime, OS, linker script, compiler flags and resource profile are
unchanged. The old control ELFs are 16,824 B: HQ `2c84c684…c06d3b3` and scalar
`0c364208…a90a4eb3`. Their sources, complete files and original build/runtime/
production-trace receipts are retained outside Git before promotion.

The input policy deliberately rejects an entire line containing NUL or any
non-ASCII byte before dispatch. Previously accepted Unicode whitespace or
arguments are now rejected. Accepted token whitespace is exactly bytes
9 through 13 and 32; LF still terminates a line. The 32,768 byte line buffer,
overlong-line drain, EOF behavior and transactional startpos replay are retained.
Borrowed byte tokens replace the materialized 16,384-element string-slice array.
A line of at most 32,768 bytes can have at most 16,384 nonempty tokens because
`2*T-1 <= N`. Numeric input retains a single optional leading `+`, checked `u64`
overflow rejection and the original successful-lookahead consumption rule.
Failed numeric lookahead leaves the next token available; invalid replay keeps
the prior position. No unchecked UTF-8 conversion or new unsafe access is used.

The ASCII candidate already passed 126 actual admitted GO/result pairs across
both exact production images, plus separate exact-source helper diagnostics.
Maintained-source reproduction, actual runtime and production ptrace reruns are
separate promotion receipts. `verify_runtime.py` embeds the ASCII rejection,
six-whitespace, numeric/clock, replay, stop/reset and quit/EOF fixtures and admits
only the exact fixed-profile source and ELF pins before starting either lane.
It needs no experiment folder or mutable historical helper.

Relative to the old input path, the five readable Rust files and the same inline
module measurement both **grow by 836 B**. `.text` shrinks by 848 B and `.rodata`
by 555 B, a combined **1,403 B** reduction. Alignment absorbs this reduction;
`.data` and the complete file each shrink by only **8 B**, while the data segment
still begins at file offset `0x4000`. These are separate size measurements.
The observed main prologue frame estimate falls from 431,952 B to 169,824 B
(262,128 B), principally from removal of the 262,144 B token array. This is a
compiler frame estimate for that function, excluding callees and asynchronous
paths; it is not a universal stack bound or a recursive-search measurement.

The following board/search/deep/fault results describe the preserved control
qualification. Exact unchanged core bodies permit narrowly scoped proof reuse;
old diagnostic executions are not relabeled as executions of the new ELF.

Independent source review covered actual clone register order and stack
alignment, parent callee-saved registers, TID handling, atomic publication,
phase ownership, completion after output, shutdown wake races and join-before-
unmap. Actual execution then established the following local fixed-profile
results. None of the test tools or std adapters is included in the native ELF.

- Both unchanged production ELFs start with three fixed TIDs, produce clocked
  bestmoves while main is blocked reading input, preserve TIDs and fixed mappings
  through repeated GO/stop/replace/reset operations, and terminate on quit/EOF.
  The strict verifier checks queued replies, cumulative per-GO totals, full pipe
  EOF and unterminated output tails. Lifecycle has 14 dispatched GOs per lane;
  malformed/negative/overflow/missing/zero clocks have ten cases per lane.
- Owned-child ptrace of both unchanged production images observes exactly two
  startup clones and no GO-time clone/mmap/mprotect. The tracer explicitly
  influences scheduling: it holds a bestmove write and worker exit stops. It
  checks the finished atomic is old while OUTPUT is held before the write, full
  write return, then the new finished value with OUTPUT released at its matching
  wake. Shared clear-TID futex wait, zero TID and successful stack munmap are
  observed in order. Waitpid notification order is recorded separately and is
  not substituted for the kernel clear-TID join contract.
- Exact-body std board drivers pass 20 published perft totals, 128 independent
  positions, 3,590 legal child transitions, 16,384 attack queries and 148,480 raw
  HQ-versus-coordinate-ray cases per lane. Complete scalar/HQ responses match.
  This covers legal EP, all promotions/castling, HCE/hash/bitboards, halfmove,
  dead material and reversible context; it is not a custom-OS runtime test.
- Exact-prefix search unit images pass 11 contracts per lane, including actual
  PVS/QS/history/continuation/correction paths, full-key context and publication,
  mate/terminal precedence, repetition and completed/aborted result witnesses.
  Separate non-DEV std probes report zero recursive allocator calls and reach
  ply 127/128 claims in a real 1 MiB std worker. Their image and CFA are distinct
  from the raw shipping image.
- Separate no_std deep diagnostic ELFs contain exact production board/OS bytes
  and the exact search prefix plus one external std-free hook. Both execute the
  actual search to ply 127/128 claims on `os::stack()` with its 1 MiB writable
  span and two 4 KiB guards, assert `None`/stop and unchanged partial TT hints,
  then clear-TID join before unmap. Mapping traces show no mmap/brk/clone between
  deep-begin return and the completed 128-node marker. No std allocator count is
  reassigned to these images.
- Fourteen separate fault images retain full source snapshots/diffs and exact
  ELF pins. They cover syscall errors/retries/short writes, a second-clone
  failure after one physical worker exists, worker clock error after three-TID
  startup and GO, and lower/upper hardware guard faults at the mapped addresses.
  Expected exit/signal and disappearance checks precede emergency cleanup.
  These are explicit fault diagnostic classes, not unchanged production ELFs.

The old raw HQ shipping frame audit uses auxiliary unwind assembly but discards its
unwind sections at link. Its entire resulting ELF matches the selected native
bytes: search CFA 4,880 B, worker entry 73,200 B, pseudo move generation 2,224 B
and main 431,952 B. Board is 272 B and Worker is 71,032 B. The observed deep path
and these frames are not a theorem about every asynchronous/system call path.

First-attempt harness failures and subsequent strict verifier fixes are retained
outside Git; they are not engine-source fixes. Production Rust/assembly/linker
bytes remained unchanged through those control qualifications. Final strict runtime and
production-trace reruns retain the earlier fault/deep verifier versions with the
receipts those versions actually produced.

There is no strength/NPS/512-worker scalability, universal stack bound, compressed
loader, deployment or 4 KiB eligibility claim. Test scripts use bounded owned
process groups, time/output/event limits and external output directories.
