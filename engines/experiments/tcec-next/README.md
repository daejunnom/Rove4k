# Next full TCEC submissions

The literal W2/TT18 and F8 selections below remain qualified small-resource
controls. The resumed [execution plan](../../../docs/ENGINE-PLAN.ko.md) separates
TEST P4/P28 from submission W256/256GiB-TT-cap. New production profile builders
and their independent qualification are being implemented; these control bytes
do not establish new-profile size, startup or runtime acceptance.

These selected profiles regenerate the exact maintained7f TCEC controls from
frozen canonical source, then independently compose and compile the next
projections twice. Historical generated source and native files are not build
inputs. Full N/B/R/Q, evaluation/search/learners, repetition and fifty-move
handling are retained. This is a size/runtime checkpoint, not full A–F or
tournament-strength acceptance.

## Current production source ownership

Readable A–F sources use the shared bodies in `engines/common`; the build-time
assembler runs before the existing transformations and checks the original
assembled canonical digest. Shared C bodies are engine inputs, independently
frozen from the assembler tool. This layout introduces no runtime dispatch or
submitted bytes. Different board, parser, TT and worker contracts retain their
own implementations; see [the common-source boundary](../../common/README.md).

`profile_build.py` now defaults to `--source-dependencies unused-includes`.
The last source stage removes the reviewed literal `limits.h` include after
its numeric-parser consumer has disappeared. The canonical development parser
still needs that header. This stage does not infer liveness from a text search:
it requires identical complete preprocessor output, identical native bytes and
diagnostics, the same recorded compiler and stdin, a full inverse, and no
increase in the complete packaged artifact. Both attempts independently repeat
these checks. `--source-dependencies control` reproduces the prior source stage
without cleanup. Generic dependency/function candidate discovery belongs to
NVCompact; this engine stage binds its reviewed candidate to production.

With the existing `phase-init` projection and source-JIT wrapper, C changes from
3,962 to 3,957 B (P4), 3,975 to 3,969 B (P28), and 3,963 to 3,957 B (provisional target).
These figures are complete-file source/packaging comparisons with equal native
images on the same GCC13 host. They do not override the maintained recipe's
compiler-specific native hash, qualify the startup/runtime gates, or establish
TCEC/AWS acceptance. A/B/E/F and D are byte-identical after the shared-source
layout change. The older W2/F8 selections below remain unchanged.

## Preserved small-resource selections

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

The user retired all engine Rust paths on2026-10-25 and subsequently resumed
the complete C implementation plan.
Rust proposals are no longer active work or size blockers. B exchange-only metadata and new
TT/evaluation/resource policies retain their separate implementation or
strength-evaluation scope. Bounded AWS evaluation and E19 preparation to production
optimizer step0 are now implementation scope. Existing historical receipts do
not imply a new account connection, paid execution or production training. See
the [implementation record](../../../docs/WRAPPER-IMPLEMENTATION.ko.md) for
scope, failures, AWS-plan corrections and evidence boundaries.
