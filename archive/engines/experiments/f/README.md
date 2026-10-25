# F: bound storage and initial-estimate experiments

These are selectable production implementations of two comparisons required by
the F plan. Both keep the whole-root MTD(f) loop, fixed evaluation meaning for
one depth, exact-horizon TT admission, local monotone interval and the move that
witnessed a completed lower bound. The default remains paired bounds with the
previous completed depth's score as the next estimate.

| Choice | C | Rust |
| --- | --- | --- |
| Paired TT | 32 bytes per slot, full key and two directional payloads | 24 bytes per slot, full key and a merged lower/upper interval |
| Single TT | 16 bytes per slot, full key, one bound, move, score and depth | 16 bytes per slot, full key, one bound, move, score and depth |
| Previous estimate | completed depth `d-1`, zero for depth 1 | same |
| Same-parity estimate | completed depth `d-2`; previous estimate for depths 1 and 2 | same |

The smaller TT deliberately replaces an opposite-direction record. It does not
claim that a single record preserves a paired interval. The MTD(f) controller
still retains its local lower/upper interval and lower-bound move witness, so an
upper-only record cannot change the published attaining move. Every compact TT
record access holds an exclusive byte CAS lock; a busy read misses and a busy
write skips replacement. The C paired record uses the same coherent protocol.
No full key is truncated, and a reader never observes payload before acquiring
the lock. Rust's default paired table retains its existing sequence protocol.

The parity cache is local to a `go`, indexed by depth parity, and updates only
after a whole iteration completes. Cancellation cannot train its next seed.
Shipping UCI gains no runtime options. The development-only `info string f seed`
line makes the estimate actually used by each production root iteration visible.

Build a configuration using the ordinary build tool:

```sh
python3 engines/scripts/build.py --out /absolute/new-directory \
  --profile local-smp --languages c,rust --variants F --parallel loose \
  --f-tt single --f-guess parity --no-pack --reproduce
```

At compiler level, C uses `ROVE_F_SINGLE=0|1` and `ROVE_F_PARITY=0|1`. Rust uses
`--cfg rove_f_single` for the compact record and the compile-time environment
`ROVE_F_PARITY=0|1`. The build manifest records both choices. Structural overlays
are a separate experiment and reject these nondefault configurations until
their combined behavior is explicitly implemented and verified.

Run all four matched configurations from one frozen set of runtime source bytes:

```sh
python3 engines/experiments/f/campaign.py --out /absolute/new-campaign \
  --rustc /absolute/path/to/rustc
```

The default uses two search workers plus the input thread. `--profile local-dev`
uses one search worker. `--pack` also builds, reproduces and startup-checks
complete source/native launchers. All reports and binaries stay outside Git.
Each distinct native SHA receives actual production UCI verification; identical
forms may share that exact executable evidence.

`compare.py` requires all four manifests and rejects changed source bytes or
nonexperimental configuration differences. It checks three quiet positions
against a separate 64-square minimax and independent arithmetic for each
language's fixed HCE. It verifies that the reported legal move attains the
completed value, retained deeper TT entries cannot contaminate restarted shallow
searches, the observed initial estimates follow the selected policy, fixed
startup thread IDs persist, node-budget cancellation preserves completed work,
and no bound conflict occurred. Probe counts, nodes, actual complete file bytes
and TT bytes are recorded. Shared-host elapsed times are diagnostics and cannot
establish throughput, playing strength, or target-machine scaling.

The memory comparison holds the number of slots fixed; it measures the RAM
saved by each representation. It is not an equal-RAM capacity comparison. C's
probe counter counts coordinated whole-root rounds, whereas Rust's counter sums
its independent workers' probes. Compare modes within one language; those two
counters do not measure identical work across languages. SMP node/probe counts
also vary with interleaving, so a single local observation cannot select a
universally better policy.

After the correctness campaign, measure the complete shipping files with its
same frozen runtime inputs:

```sh
python3 engines/experiments/f/cost.py --source-root /absolute/campaign/source \
  --out /absolute/new-cost-campaign --rustc /absolute/path/to/rustc
```

This uses the fixed `local-ship` profile, freezes packaging tools after the first
build, reproduces every generated file, and executes each selected smallest
complete file. Its actual UCI checks cover clocked play, zero clocks, active
stop, active quit, active input EOF and the startup thread identities. Only the
selected files receive those runtime claims; other measured encodings remain
unverified candidates. The size result does not establish tournament approval.

`tt_contract.c` includes the real C search implementation. Its full-key,
directional replacement, mate normalization, retained-horizon, held-lock and
contended-publication cases complement the existing independent minimax and
cancellation contract in `engines/tests/search_contract.c`. Rust's corresponding
actual-table unit tests live in `engines/tests/rust/f_tt.rs`.

## Verified local checkpoint, 2026-10-20

All four configurations passed the actual C contract, including independent
minimax, an attaining move, retained-TT horizon restarts and cancellation. The
TT-specific contract passed four optimized configurations and two ASAN/UBSAN
configurations. It exercised eight threads contending for one slot, with 480,000
write attempts and 960,000 reads in each TT run. All successful reads had one
complete record belonging to the requested full key. The existing optimistic C
XOR publication had a deterministic mixed-record alias; the new exclusive
protocol rejects probes during that partial publication. A-E now use the same
coherent 16-byte single record without increasing their TT slot size.

The Rust unit configurations passed 38, 38, 39 and 39 tests respectively. The
frozen two-worker production campaign then built and byte-reproduced every
original/compact form and executed all 12 distinct native SHAs. Each received
14 checks of independent minimax, the attaining witness, retained table,
observed estimate policy and cancellation. C's identical compact/native bytes
reuse the exact same executable evidence; Rust's distinct forms each ran.

The following shipping comparison holds 262,144 TT slots and two search
workers fixed. The selected files are complete Python source ZIP applications;
each was reproduced byte-for-byte and executed through clocked/zero-clock play,
active stop, active quit and active input EOF, preserving its three startup
thread identities.

| Mode | C complete file | C TT bytes | Rust complete file | Rust TT bytes |
| --- | ---: | ---: | ---: | ---: |
| paired / previous | 13,167 | 8,388,608 | 18,980 | 6,291,456 |
| paired / parity | 13,200 | 8,388,608 | 18,982 | 6,291,456 |
| single / previous | 13,174 | 4,194,304 | 18,996 | 4,194,304 |
| single / parity | 13,207 | 4,194,304 | 18,996 | 4,194,304 |

The compact representation saves actual TT RAM; its decoder/configuration cost
does not automatically save bytes in the complete compressed source file.
Same-parity estimates reduced observed start-position depth-4 work in this
campaign, but those SMP counts do not establish a general performance winner.
The default has not changed. None of these files meets the 4,096-byte limit.

The full exact-input evidence remains outside Git at
`/home/stemxstudio/rove4k-f-experiments-20261020/production-four-modes-v2`
and `/home/stemxstudio/rove4k-f-experiments-20261020/shipping-four-costs-v1`.
The Windows copy of the reports and transcripts is
`C:/Users/강민수/Documents/Codex/rove4k-f-experiments-20261020-evidence`.
