# D syscall / scalar–HQ prototype

This is an independent optional D architecture. It does not replace the twelve
canonical C/Rust engines or the TinyA source-package experiment. It is **not yet
a 4 KiB entry**: the smallest verified complete native file in the initial
bounded GCC 13.3 comparison is 8,540 bytes (scalar); HQ is 8,928 bytes.

The readable board and search began from TinyA's admitted 0x88/incremental HCE
core. D changes actual slider attack/generation, startup, thread creation,
command loop, output and deployment. Both D slider modes execute through the
same production `walk()` used by generation and king-safety attack detection.
Search therefore exercises scalar rays or genuine hyperbola subtraction; HQ
is not an isolated demonstration or an unused helper. A bitboard occupancy is
derived from the authoritative mailbox at each walk.

`runtime.c` and `start.S` supply Linux x86-64 syscalls directly. The linked ELF
has no interpreter, dynamic section, libc, pthread, TLS, external unpacker or
runtime compiler. It uses `mmap` for TT/storage, `clone` for a fixed startup
worker pool, futexes for epochs/completion/join, `clock_gettime` for deadlines,
and `read`/`write` for the shipping UCI interface. Each worker has a private
1 MiB stack preceded by an inaccessible guard page. The command owner is the
additional thread; `WORKERS=2` therefore means three total startup threads.

Search retains PVS, quiescence, incremental HCE/hash, full-key coherent shared
TT, history, continuation, correction-guided late-move reduction, repeated
position/rule-50/dead-material handling and a legal completed root witness.
The TT's try-lock makes contention a miss. Each worker owns its heuristics and
path. The last worker publishes `bestmove` before releasing a distinct
completion epoch; the command owner waits for that epoch before changing a
position, resetting workers, starting another search or joining on shutdown.
Quit and EOF cancel active work, wake idle workers and wait for kernel-cleared
TIDs with shared futex operations. No new workers are created per `go`.

The shipping command set includes `uci`, `isready`, `position startpos moves`,
clocked `go`, `stop`, `ucinewgame`, `quit` and EOF. Worker count and TT size are
compile-time resources; no shipping resource options are exposed. DEV adds
FEN, perft/legal/state/eval/verify/stats and bounded depth/node/movetime search.
The admitted board has at most 16 pieces per side; the conservative 432-move
bound fits the checked 512-entry move lists.

## Reproduce and validate

Run on Linux x86-64 with GCC and Python 3.12. Outputs must be new absolute
directories outside the checkout:

```sh
python3 engines/compact/tiny-d/build.py \
  --out /absolute/external/tiny-d --optimize z --lto
python3 engines/compact/tiny-d/check.py \
  --build /absolute/external/tiny-d/build.json \
  --out /absolute/external/tiny-d-check
python3 engines/compact/tiny-d/algorithms.py \
  --build /absolute/external/tiny-d/build.json \
  --out /absolute/external/tiny-d-algorithms
python3 engines/compact/tiny-d/cost.py \
  --build /absolute/external/tiny-d/build.json \
  --out /absolute/external/tiny-d-cost
python3 engines/compact/tiny-d/optimize.py \
  --build /absolute/external/tiny-d/build.json \
  --out /absolute/external/tiny-d-codegen
python3 engines/compact/tiny-d/startup.py \
  --build /absolute/external/tiny-d/build.json \
  --out /absolute/external/tiny-d-startup
```

The builder freezes production source and packer recipes, compiles DEV and
shipping scalar/HQ files twice, then accepts a native file only after complete
byte reproduction. Section removal preserves every PT_LOAD file byte and
clears only section metadata. RX code/read-only data, RW state and a
non-executable stack remain separate program segments. An optional own
self-restoring ELF is also built and reproduced; the native candidate remains
available even when that wrapper is larger. Complete native and wrapped file
sizes both include ELF headers. The own loader's tournament acceptability is
separate from local functional evidence.

The check driver freezes the common independent oracle/harness, hash-pins each
of six distinct native/wrapped executables, checks exact startup TIDs and runs
two colour-exchanged bounded games. The algorithms driver builds deterministic
one-worker controls, checks actual PVS/QS/TT/history/continuation/correction
branches, halfmove-sensitive TT context, EP correction exclusion, dead-material
classification, ply-cap cancellation and completed-witness retention. It then
compares exact production scalar/HQ search replies over five ordinary/special
positions. `tests_hq.c` independently compares all ray occupancies and random
full-board occupancies with coordinate rays; it is not the actual-search gate.

The symbol cost driver keeps its map only when the symbol-bearing relink,
after the declared metadata removal, matches every byte of the selected ELF.
The code-generation study tests eight bounded `-Os`/`-Oz`, LTO, no-inline,
whole-program and code-alignment combinations, with two independent compiles
and an actual clocked search for every scalar/HQ candidate. It changes no
algorithm, 64-bit ABI, resource count or UCI command. These measurements do not
establish NPS, Elo or target-machine scaling.

Initial WSL Ubuntu/GCC 13.3 evidence lives outside Git. Both `-Os -flto` and
selected `-Oz -flto` six-form campaigns passed 36/36 common checks plus two
bounded games. The separate kernel campaign passed 4,932,096 comparisons for
each mode under optimized and ASAN/UBSAN builds. Eleven raw-runtime stub probes
covered rapid generations, fragmented/malformed input, active cancellation,
fixed startup identity and partial clone failures. Stub probes qualify runtime
lifecycle only; actual search correctness comes from the executable campaigns.
The separate `WORKERS=511, TT_BITS=18` startup-only build passed four admission
runs (scalar/HQ, quit/EOF) with 512 stable TIDs on the eight-CPU WSL host. These
checks submit no search and do not qualify the final large-TT target profile,
search RSS or hardware scaling.

The `-Oz -flto` native files (8,540/8,928 bytes) remain substantially above
4,096. The own-loader alternatives are larger (8,806/9,142 bytes), so they are
retained controls. This prototype establishes a small independent syscall
runtime and measured D cost baseline; further source/machine-code co-design is
required before D is an eligible final entry.
