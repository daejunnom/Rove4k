# Tiny A search representation study

These are independent source experiments. They do not modify
`engines/compact/tiny-a` or replace the A–F portfolio. Generated source, binaries,
packages and reports belong in a new directory outside the checkout. The frozen
reference is the generated-board, definitions-before-callers, disabled-counter
cleaned tiny A build. Its complete selected source launcher is 5,671 bytes.
The canonical readable modules and current producer remain in
[`../../compact/tiny-a/`](../../compact/tiny-a/); use that producer to create a
new immutable reference, then pass its `build.json` into this independent study.
The recorded profile is GCC 13.3, C11 `-Os -pthread`, `WORKERS=2`, `TT_BITS=18`,
`DEV=0`, default `PLY=128`, generated board and the POSIX startup pool. Development
validation uses `DEV=1`; the explicit cap fixture uses `PLY=4`.

The best measured and qualified composition is **5,419 bytes**, including the
shell prefix, compressed Python compiler bootstrap and complete C source. It is
still **1,323 bytes above 4 KiB**. It uses the same Python/compiler/runtime
requirements as its reference. No NPS, rating, scaling or tournament eligibility
claim follows from this study.

## Expressions and measured whole-file cost

All values below use the same frozen reference, compiler and 27 complete wrapper
forms. The minimum for each expression is the combined XZ source stream.

| Expression | Complete bytes | Difference from 5,671 |
| --- | ---: | ---: |
| Reference | 5,671 | 0 |
| Discard the unused selected prefix of selection sort | 5,659 | -12 |
| Pass the previous piece index instead of the previous move | 5,659 | -12 |
| One recursive PVS call site with a retry loop | 5,687 | +16 |
| Remove unreachable static evaluation clamp under proven admission | 5,651 | -20 |
| Discard prefix and pass piece index | 5,647 | -24 |
| Both above plus bounded evaluation | 5,627 | -44 |
| Above plus nonzero TT write marker and positive learning bonus | 5,615 | -56 |
| Then native-identity-gated identifier spelling, best trial 93 of 96 | **5,419** | **-252** |

`represent.py` owns these guarded readable-source transformations. Its `apply`
returns a new mapping and never writes the canonical input. The selected
structural composition uses `discard`, `prior`, `bounded-eval` followed by
`state.py`'s `probe-marker` and `positive-bonus`.

- Selection sort never reads its selected prefix again. Discarding its two dead
  stores leaves the remaining list order, including equal scores, unchanged.
- A child's previous piece index is the piece on the legal move's destination
  after make, including promotion. Root still uses the neutral index 6. The
  continuation read/update and all search calls retain their original meaning.
- Every TT store has a nonzero bound 1–3 at bit 41. Reads pass zero. A nonzero
  payload therefore replaces the write flag without changing the full 64-bit
  key comparison or the try-lock acquire/release publication boundary.
- Both history/continuation learner callers pass `depth*depth` inside
  `depth>0`. Their positive bonus does not need `abs`.
- The real evaluator was enumerated over all 768 signed-piece/square pairs:
  `abs(value)<=910`. Admission permits at most 16 pieces per colour; captures
  decrease and promotions preserve that count. Thus `abs(HCE)<=32*910=29120`,
  below `MATE-PLY-1=29871`. The static clamp is unreachable in the admitted
  profile. The transform pins the evaluator body and piece admission, rejects
  changed coefficients/admission/mate scale, and adds a preprocessor rejection
  for an incompatible ply profile. The correction error's 256 clamp remains.

The identifier study uses the existing `engines/scripts/rename_c.py`, without an
NVCompact dependency. Each proposed spelling compiles the *complete program*
with the actual compiler-stdin recipe. Only exact full native SHA-256 equality
can enter the whole-file comparison. This is qualified for the recorded
compiler/profile; a new recipe must run its own gate. Future identifier/encoding
work belongs to the separate tiny-encoding owner.

## Preserved experiments that were not selected

The retry-loop template has exactly the original reduced probe, mandatory full
depth retry, and in-window full-window retry sequence. It passed deterministic
search-state parity but increased the compressed file. Root trial storage and
packed move/ordering records also failed to improve the earlier 5,743-byte
reference. Shared mate/clamp helpers were measured against that older exact
reference and regressed despite shorter readable expressions in some subsets.
The reports preserve both baselines rather than mix their deltas.

`state.py` additionally offers `hole-learners`: it places continuation and
correction in unreachable 0x88 history rows. The static index sets are disjoint
and its complete wrapper measures 5,659 bytes, but it is **not engine qualified
or adopted**. Logical learner normalization and explicit layout checks are
needed before considering that representation. Its worker memory reduction is
not a substitute for the required whole-file comparison.

## Qualification and reproduction

`campaign.py` requires the immutable reference `build.json`, verifies named
readable input/used recipe hashes, reproduces the reference compact source and
measures transformed full packages. It uses the exact reference translation unit
rather than depend on a concurrently evolving producer. `build.py` provenance
is retained by the reference but is not an executed dependency of this driver.
The later tiny-A LF/CRLF producer normalization changed `stitch.py`/`build.py`
metadata hashes while leaving this reference's assembled C unchanged. Its
existing source/native/package byte proofs therefore remain scoped to the
recorded immutable inputs; the campaign must not silently relabel the old
recipe hash as current. A future producer run records its own new metadata.

`qualify.py` includes the *actual* readable engine into `equivalence.c.in`.
Six representations each matched 12 deterministic positions in best move,
score, nodes, complete TT key/payload state, learning tables, path keys and
actual algorithm counters, with TT retained across positions. The reference and
selected structural composition also passed ASan/UBSan on those cases.
Single-worker equality is separate from the actual two-worker wrapper tests.

`verify_selected.py` runs the shared shipping verifier on the actual selected
complete wrapper: protocol, active stop/reset lifecycle, 16-ply legal selfplay,
EOF and quit. All five groups passed. It runs the real development algorithm
check, halfmove-sensitive retained-TT fixture, EP correction exclusion,
dead-material cases and `PLY=4` incomplete-iteration witness fixture. PVS, QS,
TT, history, continuation, correction learning and correction use counters were
all positive. Once UCI readiness proves compilation complete, `/proc/PID/exe`
must match the identifier gate's program hash and have exactly three startup
threads. `proof.py` checks HCE bounds/admission rejections and independently
reproduces both the selected complete artifact and native program bytes.

Example Linux invocation (use new absolute external output paths):

```sh
python3 engines/experiments/tiny-search/campaign.py \
  --baseline /external/frozen-tiny-a/build.json --out /external/search-measure \
  --select baseline --select winner-state
python3 engines/experiments/tiny-search/rename.py \
  --measure /external/search-measure/measure.json --form winner-state \
  --out /external/search-rename --trials 96
python3 engines/experiments/tiny-search/qualify.py \
  --candidate /external/search-measure/baseline/combined.c \
  --candidate /external/search-measure/winner-state/combined.c \
  --out /external/search-equivalence
python3 engines/experiments/tiny-search/verify_selected.py \
  --measure /external/search-measure/measure.json \
  --rename /external/search-rename/results.json --out /external/search-selected
python3 engines/experiments/tiny-search/proof.py \
  --measure /external/search-measure/measure.json \
  --rename /external/search-rename/results.json --out /external/search-proof
```

The 2026-10-20 local evidence copy is outside Git in the
`rove4k-tiny-search-20261020-evidence` directory.
Selected complete artifact SHA-256:
`8aa0b9b4722b230d71284346ff745960f86f0b9b960a2e530594cf1b9ebe8646`.
Its actual compiler-stdin native SHA-256:
`c31c93a930485b325a8b9279c59374375516d0592e7cea1208f4126307b5222c`.
