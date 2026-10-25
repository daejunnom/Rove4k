# Next full TCEC submissions

These selected profiles regenerate the exact maintained7f TCEC controls from
frozen canonical source, then independently compose and compile the next
projections twice. Historical generated source and native files are not build
inputs. Full N/B/R/Q, evaluation/search/learners, repetition and fifty-move
handling are retained. This is a size/runtime checkpoint, not full A–F or
tournament-strength acceptance.

| Entry | Previous7f whole | Selected whole | Header + payload | Margin below4096 |
|---|---:|---:|---:|---:|
| A2 | 3894 B | **3731 B** | 94 +3637 B | 365 B |
| B2 | 4265 B | **4092 B** | 109 +3983 B | **4 B** |
| C2 | 4031 B | **3873 B** | 101 +3772 B | 223 B |
| E2 | 3980 B | **3817 B** | 94 +3723 B | 279 B |
| F2 | 3576 B | **3530 B** | 103 +3427 B | 566 B |
| F8 | 3591 B | **3548 B** | 103 +3445 B | 548 B |

Workers are fixed2, or8 for F8, with TT18/PLY128. All C entries now use
asynchronous per-GO threads. Worker/learner storage persists; atomic completion
publishes the existing selector, main answers active `isready`, and the next
GO/position joins the old handles before state reuse. Startup/between-GO has
one TID and active GO has W+1. Final quit/EOF may discard an active result.

A/B/C/E share the immutable game-key prefix instead of copying32KiB into each
worker. Their private recursive paths remain128 entries. B additionally replaces
piece-type bitboards with side occupancy and classifies the mailbox while
visiting the same kind1..6/ascending-origin legal-LVA order. Measured Board size
is288→192 B. This is not a SEE policy or pruning change.

The engine removes only its wrapper-owned private absolute argv0 before
starting. An unlink failure exits2. The wrapper has no delayed cleanup child,
retains the same five-line pipefail/decode/compile structure, and joins GCC
option arguments `-xc`/`-oPATH` to save two header bytes. Actual JIT native hash
checks verify the spelling equivalence. Compile/decode failure may leave a temp
file for the development owner. The preserved source/script/native artifact is
never the deletion target. **Direct native use requires a disposable copy with
its own absolute argv0**; do not execute the stored `native/x` baseline itself.

```sh
python3 -I -B engines/experiments/tcec-next/build.py \
  --entry B --out /tmp/rove4k-next-B
python3 -I -B engines/experiments/tcec-scope/verify.py \
  --build /tmp/rove4k-next-B --out /tmp/rove4k-next-B-runtime
```

Use a new absolute output outside every Git checkout. Entries are A/B/C/E/F/F8.
Defaults consume manually reviewed literal source/native/header/payload/whole
identities in `recipe.json`. `--measure` is an explicit comparison; it never
updates the selected expectations. All stages admit exact known source inputs
and disjoint original-coordinate edits, with whole inverse and protected gaps.

The shared verifier is unchanged. It checks the declared per-GO topology,
active readiness, actual source-JIT image, clocks, queued jobs, full promotion
replays, long valid input, immediate normal unlink, and physical quit/EOF.
Each final local profile has four sessions/24 GO requests/22 normal legal
results; two active terminal requests may omit their bestmove. F8 was run alone
on local CPU0–7. The VM reports8 logical CPUs/4 cores with2-way SMT; this is not
eight physical cores or TCEC many-core scaling evidence.

Separate experiments remain available without changing the selected source:

- `search_queries.py`: TT generation/evaluation deferral and first-legal QS
  cutoff. Thirty-five actual shipping-core comparisons preserve the tested
  score/move/work/learner/TT/SEE/clock observations and reduce unused queries.
- `history_layout.py`: prefix sharing and a64×64 bijective history candidate.
  Actual UBSan search/learner/path/TT fixtures cover all six families. Dense
  history saves24KiB/worker but can add indexing cost and submitted bytes; it is
  not enabled here.
- `compiler_options.py` and its checker: Os/O2/O3 complete-file/native
  comparison and fixed-depth single-worker shipping-core timing. O3 improved
  the local F/B fixture, but unmodified shipping-native throughput, target
  hardware and SMP remain separate. Selected profiles retain Os.

The next-optimization attachment also discusses Rust prefix/fallback/zeroing,
B exchange-only metadata and new TT/evaluation/resource policies. These remain
separate implementation or strength-evaluation work. Rust A stays7502 B in its
existing producer. AWS/Spot is planning-only: no account connection, resources,
paid execution, workflow, training or scheduled task is introduced here. See
the [implementation record](../../../docs/WRAPPER-IMPLEMENTATION.ko.md) for
scope, failures, AWS-plan corrections and evidence boundaries.
