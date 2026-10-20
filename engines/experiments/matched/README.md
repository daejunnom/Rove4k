# Optional matched C-policy E experiment

This is a source experiment over the real independent C and Rust E engines. It
generates guarded overlays from Git commit
`de5676dcbc498d77477c66064aca926633c851ff`; it does not edit canonical sources,
call a C backend from Rust, or replace chess/search with a small timing kernel.
The normal candidates and their language-specific features remain unchanged.
The local comparison below has bounded, explicit coverage. General performance,
language attribution and candidate selection remain unproven.

Both engines consume the existing frozen 21-coefficient E evaluation and
ordering model. Both execute actual iterative PVS, quiescence, single-bound TT,
history, continuation, killers, correction, LMR, game rules and persistent loose
sharing pools. The selected policy is C's policy; Rust's other policy choices
remain available in its canonical candidate.

| Contract | Selected behavior |
| --- | --- |
| Evaluation | Same raw frozen E integer model; correction never changes a leaf score |
| Correction | Live worker-local `i32[2][1024]`, pawn-key index, `/64` in LMR guard; quiet exact noncheck nonmate update `clamp(best-raw,-256,256)-cell/64` |
| History | `i32[2][128][128]`, quiet beta cutoffs only, bonus `depth*depth`, C bounded update equation |
| Continuation | `i32[13][13]`, C signed-piece index and same update equation |
| Killers | Two moves per ply, 96 plies |
| LMR | One ply at depth >=4 and searched >=4, quiet, parent/child noncheck, `raw+correction < alpha+100`; full-depth and full-window retries preserved |
| Ordering | C TT/reply priorities and MVV-LVA, history/continuation/killers plus E order; total tie `(score DESC, packed move ASC)` in QS and PVS |
| Diversity | Same C additive `(move*(worker*17+13))&31` for nonzero workers |
| Generation | Both order all legal moves; C study uses real `generate+make_move` before ordering |
| QS | Terminal/draw/stand-pat precede ordering; both compute raw evaluation even in check, matching C |
| TT | Full 64-bit keys, 16-byte exclusive-CAS slots, always replace one bound, no QS TT, cutoff only below root, depth >= request |
| Bounds | `INF=32000`, `MATE=30000`, mate normalization at `MATE-96`, abort at ply >=95; root mate-distance clamp |
| Placement | Identical 1,561 Zobrist keys and reversible-history context fold; incremental identical pawn keys; no evaluation-epoch mix |
| Resources | One or four search workers plus input thread, 262,144 slots / 4 MiB TT, 1 MiB search stacks, logical learning array counts/types matched |
| Startup TT initialization | Both clear and touch every real TT slot before worker/input admission; Rust's lazy zero allocation is not silently timed as search work |
| Recipe | GCC `-O2` plus explicit LTO; Rust opt-level 2 and fat LTO; exact tools/helpers/flags/hashes recorded |

C's shared raw-model diagnostic increment is omitted in the study so it does
not add a shared cacheline hotspot absent in Rust. Neither study core adds a
shared TT-hit diagnostic increment. These changes remove instrumentation,
not evaluation or TT functionality. Node accounting remains real shared atomic
accounting. Canonical diagnostic behavior is untouched.

Rust hashes use a compile-time 12,488-byte read-only table. C initializes the
same values into BSS at startup. Both perform table lookup per piece; their
source/native/data/startup differences remain explicit measured properties.
Rust still uses its own legal generation and move application, while C uses its
own board and legality checks. Matching semantic work does not assert identical
board-internal instruction counts or turn all remaining differences into a
causal language effect.

Use a fresh process per fixture. In particular, canonical C `ucinewgame` clears
TT and Rust also resets learning; that lifecycle difference is not silently
used to build a matched benchmark sequence. Fixed-depth nonmate fixtures avoid
clock/deadline and early mate-termination differences. Mate, cancellation,
stop/reset/quit/EOF remain separate correctness checks.

```sh
python3 engines/experiments/matched/generate.py --out /absolute/new-one-worker \
  --workers 1 --compile --rustc /absolute/path/to/rustc
python3 engines/experiments/matched/verify.py \
  --manifest /absolute/new-one-worker/generation.json \
  --out /absolute/new-one-worker/semantic-verification
```

The generator obtains exact Git object bytes rather than the working copy,
checks the pinned commit and strict replacement anchors, and records every
before/after runtime-source SHA, template/helper SHA, compiler identity and
actual native command. On a Windows-managed worktree accessed from WSL it uses
the Windows Git client to read those same objects. `hash_overlay` must run
before other board transforms and rejects a drifted/reapplied board source.
Use `--workers 4` only after the one-worker semantic gate passes. Four-worker
shared-TT races do not require identical node counts.

The comparator launches fresh processes, checks full position/pawn hashes, raw
model output, the legal set against the independent Python rules oracle, every
completed depth score and fixed startup thread identities. With one worker it
also requires exactly equal nodes at every depth and the same attaining move.
It reads the kernel's memory fields as resource evidence; it records no timing
ranking. The ordinary black-box harness can check protocol/rules/search and
active lifecycle on the generated native manifest:

```sh
python3 engines/tests/verify.py --manifest /absolute/new-one-worker/generation.json \
  --out /absolute/new-one-worker/full-quick-verification --suite all --quick
```

## Verified first implementation checkpoint, 2026-10-20

The hash overlay passed 5 tests: all 1,561 actual C/Rust/reference key values and
146 states across 12 replay cases, including incremental pawn/rebuild checks,
legal/pinned/irrelevant EP, castling, capture promotions and history rollover.

Six cold one-worker fixtures passed raw evaluation, full position/pawn hashes,
independent legal sets, **every completed depth's exact node count and score**,
and final best move: start position, an opening, Kiwipete, quiet pawns, legal EP
and pinned EP. The corresponding four-worker fixtures passed semantic values
and fixed five-thread startup checks; node equality was not required. Both
resource profiles also passed all 16 black-box protocol/rules/state/search/
lifecycle/selfplay/EOF/quit groups. These are correctness and source-contract
gates, not throughput or playing-strength results.

Generated native files were 43,056 / 408,176 bytes for C/Rust with one worker and
47,152 / 412,816 bytes with four workers, using the explicit speed recipe. These
are native file measurements, not a whole submission size comparison.

## Completed cost and bounded timing checkpoint, 2026-10-20

The source-preserving shipping producer in [COST.md](COST.md) measured complete
source launchers, complete native launchers, raw native ELF files and the
project's own restoring ELF files. All 16 selected role files reproduced,
decoded to their expected payloads and passed actual whole-file runtime checks.
Shipping size recipes and developer speed-native measurements remain separate.
Every selected complete file remains above 4,096 bytes.

The separately coordinated quiet-window campaign in
[MEASUREMENT.md](MEASUREMENT.md) completed 18 valid cold pairs / 36 paired runs:
three nonmate fixtures, three samples, and one or four search workers. The
one-worker runs matched every depth's exact nodes, score and attaining move.
Four-worker scores matched; scheduling and shared-TT races changed completed
aggregate work, so the report retains actual nodes alongside wall time and NPS.

Q1 remains a failed partial campaign with 16 completed pairs, one successful
unpaired C run and one interrupted Rust attempt. Q2 executed only missing
four-worker Kiwipete sample indices 1 and 2. The metadata-only
`index_measurements.py` verifies immutable source reports and matching source,
native, resource and nine measurement-core hashes, rejects duplicate sample
indices, and indexes only completed pairs. Its `coverage_complete` field never
rewrites an original campaign's `passed` status.

```sh
python3 engines/experiments/matched/index_measurements.py \
  --campaign /absolute/measurement-q1/results.json \
  --campaign /absolute/measurement-q2/results.json \
  --invariance /absolute/measurement-invariance/q1-q2-invariance.json \
  --out /absolute/new-measurement-combined/index.json
```

Exact manifests, source/native/producer hashes, frozen recipes, selected files,
reproduction outputs and transcripts remain outside Git under these logical
evidence names. Absolute host locations belong to the run catalog, rather than
this portable source document:

| Logical evidence | Content |
| --- | --- |
| `matched-prefault-one` / `matched-prefault-four` | Generation manifests, exact generated sources, developer natives, six-case semantic gates and 16-group black-box gates per profile |
| `matched-hash` | Five hash-overlay tests, all 1,561 keys and incremental board/replay comparisons |
| `matched-shipping-cost` | `cost.json`, frozen build/packaging recipes, independently reproduced files and 16 selected-file runtime transcripts |
| `measurement-q1` | Immutable failed partial campaign, completed pairs and excluded singleton/interrupted attempt |
| `measurement-q2` | Two missing global sample indices with a separate successful campaign ID |
| `measurement-invariance` | Exact helper diff, both helper snapshots and nine unchanged measurement-core hashes |
| `measurement-combined` | `index.json`, complete pair coverage, separate excluded attempts and per-fixture descriptive summaries |

These results establish costs and bounded behavior of the declared independent
C/Rust engine representations, exact compilers and host. They establish no
causal language effect, general NPS advantage, Elo, tournament approval, 4 KiB
eligibility or target-machine scalability. Broader traces and workloads are
future work if broader attribution or candidate selection is requested.
