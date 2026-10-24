# Full TCEC submission profiles

This is the current full-feature source-submission path for the TCEC 4k size
work. It regenerates each maintained canonical producer before applying the
declared tournament specialization. The standalone grace/kill/shell contracts
remain available in their original entry directories; their stronger compiler
ownership is not a prerequisite for a small tournament submission.

Full means the selected family's chess/search/evaluation/learner features,
including N/B/R/Q promotions, repetition and the fifty-move rule. It does not
require optional development UCI, arbitrary malformed-input rollback or every
standalone compiler recovery guarantee. The external protocol is specialized
for TCEC 4k rather than the general TCEC tournament. Resource choices are fixed
in the generated program, with no worker-count or hash-size UCI option.

| Full profile | Workers / TT bits | Previous Bash | TCEC complete file |
|---|---|---:|---:|
| C A | 2 / 18 | 4,232 B | 3,894 B |
| C B | 2 / 18 | 4,712 B | 4,265 B |
| C C | 2 / 18 | 4,375 B | 4,031 B |
| C E | 2 / 18 | 4,323 B | 3,980 B |
| C F2 | 2 / 18 | 4,018 B | 3,576 B |
| C F8 | 8 / 18 | 4,028 B | 3,591 B |
| Rust A | 2 / 18 | 8,945 B source stream | 7,502 B |

Every size includes header and compressed payload. B remains 169 B above
4,096 B, and Rust A remains 3,406 B above. Size qualification, local runtime,
exact-revision CI, playing strength and tournament eligibility are separate
claims. The implementation record identifies current receipts and preserved
failed or unselected experiments.

## Reproduce the selected C profiles

Run on Linux x86-64 with Python 3, a C11 compiler and pthreads. WSL Ubuntu is a
supported local verification environment. Output paths must be new absolute
paths outside every Git checkout.

```sh
python3 -I -B engines/experiments/tcec-scope/build.py \
  --entry F --out /tmp/rove4k-tcec-F
python3 -I -B engines/experiments/tcec-scope/verify.py \
  --build /tmp/rove4k-tcec-F --out /tmp/rove4k-tcec-F-runtime
```

Entries are `A B C E F F8`. Default builds consume literal selections in
`recipe.json`; they fail on drift rather than updating expected output.
Explicit runtime/input/line/operator flags are developer comparisons and are
reported as experimental measurements. They are not runtime UCI options.

A/B/C/E remove process-final shutdown bookkeeping and retain their persistent
worker synchronization. F2/F8 use asynchronous per-GO workers: learner storage
persists, main continues reading UCI, the last atomic completion publishes the
existing result, and the next GO/position joins old handles before reusing
memory. Startup/between-GO TIDs are one for F and W+1 for the persistent
families; active GO has W+1. The verifier follows these declared lifetimes
instead of requiring persistent worker IDs for every implementation.

The common valid-input projection preserves parsing of legal moves and clock
sentinels. `getline` replaces the fixed line array and overflow drain with one
reused buffer; allocation/read failure exits the loop without inspecting the
failed buffer. This buffer grows to the longest logical line. The `word`
declaration used where smaller requires an actual C11 compatible-pointer type
assertion with `size_t`; F8 uses `size_t` directly at equal complete-file cost.
B additionally removes dead shipping score stores, applies audited finite
expression/macro edits and aliases struct members without changing their
layout, the learner or search policy. The field-alias stage produces an exact
native match to its declared predecessor.

## Rust A

```sh
RUSTUP_TOOLCHAIN=1.97.0 python3 -I -B \
  engines/experiments/tiny-rust-stream/tcec_build.py \
  --out /tmp/rove4k-tcec-rust-A
RUSTUP_TOOLCHAIN=1.97.0 python3 -I -B \
  engines/experiments/tcec-scope/verify.py \
  --build /tmp/rove4k-tcec-rust-A --out /tmp/rove4k-tcec-rust-A-runtime
```

The separate Rust class retains two persistent workers. Its local node counter
and 256-node clock cadence, stop atomic, TT locks and job/result barrier remain;
unused shared observer/quota, diagnostic result copies and optional shipping
UCI are omitted. `tiny_dev` retains those diagnostics and its own process
suite. The old fixed three-resource-environment bootstrap admission is not
extended to the new source: the new TCEC producer has its own exact input,
compiler argv and complete-file identities.

## Small wrapper contract

The wrapper streams decompressed source directly to the compiler, uses one
temporary executable and schedules normal unlink after one second. Bash
`errexit` and `pipefail` prevent execution after decompression or compiler
failure, including a compiler that writes an executable before failing. UCI
stdin and cwd are retained.

Failure before the cleanup child is scheduled can leave the temporary file.
Arbitrary compiler descendants, parent-only cancellation, cleanup-child reap
and argv forwarding are outside this wrapper's contract. Final quit/EOF may
terminate an active search without a final bestmove. Live GO/position memory
reuse and responsive `isready` remain required. Development tools separately
bound and settle their own processes; those tools are not embedded in the
submission.

Sources, helpers, compilation and complete packaging are reproduced twice.
`build.json`, `source-proof.json` and runtime receipts preserve actual input
closures, inverse/protected-source checks, native image identities, worker
activity, normal unlink and physical shutdown. Generated files, logs, failed
candidates and external peer-engine sources stay outside Git. Read the
[implementation record](../../../docs/WRAPPER-IMPLEMENTATION.ko.md) for evidence
scope and remaining full A–F work.
