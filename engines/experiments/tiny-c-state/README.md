# One shipping C HCE-cache removal

This is one fixed source/state simplification of the qualified C5955 entry.
The actual complete source file measures **5,947 bytes**, saving **8 bytes**.
It remains **1,851 bytes above 4,096**. No algorithm, parameter, spelling,
compiler, compression or resource sweep is performed, and the maintained C/E
entries remain unchanged.

| Fixed form | Compact shipping C | Restored stdin ELF | Complete source file |
| --- | ---: | ---: | ---: |
| Qualified control | 14,244 B | 26,464 B | 5,955 B |
| DEV-only HCE cache | **14,206 B** | 26,464 B | **5,947 B** |

`control.c` is an owned exact readable snapshot, SHA-256
`f0bc01d4ebde79578248e1d210723bff6be0639e829c166d6204de02466c3e82`.
`inputs.json`, `bootstrap.py.in` and `launcher.sh` preserve its actual fixed
compiler/preprocessor/profile, expected control identities, selected Python
bootstrap and 75-byte launcher. They are ordinary tracked inputs in this folder.
The producer has no dependency on a future mutable `tiny-entry-c`, old build,
report, executable or historical output directory. Historical receipt hashes
remain metadata only. Four ordinary source helpers are LF-hash pinned and
copied before import. `.gitattributes` fixes all new source text to LF.

## The only change

The current C search already computes `evaluation=side*tiny_raw(board)` and
uses the same clamped SIMD evaluation for QS, LMR and `best-evaluation`
correction learning. Nothing in the shipping search reads `Board.v`. The only
shipping accesses are cache maintenance itself, in the two branches of `put`.
The invariant comparison is DEV only.

`generate.py` admits exactly the readable control above and adds DEV guards at
three literal sites: the `v` field declarator, old-piece HCE subtraction and
new-piece HCE addition. It reverses those three replacements to prove every
other input byte unchanged. There is **no residual rewrite and no brace change**.
The resulting shipping source removes exactly 38 lexical bytes. DEV specialized
source and native ELF are exactly the old control bytes, preserving the cached
HCE transition oracle and FEN/invariant diagnostics.

Actual shipping `sizeof(Board)` changes **176 to 168 bytes** in both optimized
and ASAN/UBSAN fixture builds. The cached int and its following alignment padding
disappear. Source-level move application drops two HCE computations/updates for
an ordinary quiet move, three for a capture/EP, and four for castling; startpos
construction drops its 32 cache updates. No machine-instruction, stack-frame,
NPS or strength gain is inferred from those counts.

`value()` remains in shipping. It still constructs all 832 shared PSQT terms
before main/worker startup and supplies capture move priority. The actual AVX2
gather/reduction leaf, score sign/clamp, correction/search, hash/context, full-key
TT, fixed pool and completed-root fences retain their source bodies. The fixed
profile remains two search workers plus stdin, TT bits 18 and PLY 128. The
compiler argv and XZ9-extreme `lc=3/lp=0/pb=2` bootstrap/encoding are unchanged.

## Reproduce the first cost, then qualify the single gain

Run on the recorded Linux x86-64 Ubuntu/GCC13.3 AVX2 environment, using new
absolute output directories outside Git:

```sh
python3 -B engines/experiments/tiny-c-state/build.py \
  --out /absolute/new/C-cache-cost
python3 -B engines/experiments/tiny-c-state/qualify.py \
  --build /absolute/new/C-cache-cost/build.json --out /absolute/new/C-cache-proof
python3 -B engines/experiments/tiny-c-state/verify.py \
  --build /absolute/new/C-cache-cost --out /absolute/new/C-cache-runtime
```

The first command independently regenerates/compiles/packages both control and
candidate twice. It must reproduce C5955 exactly before reporting the candidate
cost and must retain the exact old DEV source/native identities for both forms.
Qualification requires the measured single strict gain. No additional candidate
is chosen on failure. All copied inputs, intermediate source, stderr, ELF,
bootstrap, complete files and reports stay outside Git. The original cost report
keeps `runtime_qualified: false`; subsequent qualification/runtime reports remain
separate evidence stages.

| Exact candidate identity | SHA-256 |
| --- | --- |
| Readable guarded candidate | `1f0f18ffee91ecddea3cb31e7553e1d1415e25b3f759cdec4e0f375fcd0b2298` |
| Compact shipping C | `dcbfb3e92b52e2ee902055aa7331c068b6b95226f00b1edfc4b63b789405105c` |
| Restored stdin ELF | `c948e31aea9f413614881b8e8e6060e5aa70314dd84b2d9b544e3f20edb99df2` |
| Complete 5,947-byte file | `76ed08f657398ac4b8cfbd0ff2230257ab18547f082b4c29af62428d802f33d3` |

DEV remains source
`31415fddd3cf1ebd378e58ccc41cdb2b9382df646e41f002653734a5e4d746bf`
and native
`5e9b05e55cba56c63b180c2dce1d9330d2f3a69d7563360e35484684ebb730ba`.

## Focused actual DEV0 evidence

The qualifier freezes the actual first-cost readable/specialized inputs and
artifacts. It includes each **actual specialized DEV=0 shipping source** in a
separate translation unit. Only public names are namespaced after system
headers load; static SIMD, constructor, board and search remain local to their
original units. A fixture-only ABI copies semantic fields explicitly, excluding
padding/cache, and a fixture-only copy of the original DEV FEN parser constructs
special positions through each unit's actual `put`, `ep` and state functions.
That parser is not added to the shipping entry.

Optimized and ASAN/UBSAN runs each pass:

- 832 actual PSQT terms and independent scalar-HCE equality.
- 14 fixed special-position fixtures, 5,000 deterministic plies, **160,432
  normalized position comparisons**, 150,419 legal children and 164,667 pseudo
  moves; ordered pseudo moves, sorted legal sets and every legal child agree.
- Cells, side, castling, kings, EP, halfmove, hash, reversible context, raw SIMD
  leaf and unchanged parent bytes agree. Scalar/SIMD and side invariance hold.
- Actual knight cycles and halfmove/path distinctions agree; this state fixture
  labels its reconstructed-key result separately from a production TT cutoff.
- Ten direct actual-shipping core checks per form: full-key collision miss,
  seeded genuine TT cutoff followed by halfmove/path search misses, third visit
  versus second visit, halfmove draw/mate precedence, positive completed
  depth-four search and history/continuation/correction activity, actual ply-cap
  abort, and EP-best correction exclusion.

The ply-cap fixture performs a real direct depth-four `search`, installs its
result into the worker's completed fields, then calls the real abort branch at
`PLY-1`. It proves those supplied fields survive that branch. It does **not**
newly observe `think()` iteration publication or a concurrent cancellation
fence; unchanged-source/DEV evidence for that path is reused separately.
Likewise the core fixture requires both forms to satisfy the contracts; it
does not compare their exact depth-four score, node count or learned tables.

Disassembly of the actual control and new shipping images places AVX2 gather
and horizontal reduction directly inside `search` after compiler inlining.
The actual production search therefore continues to consume SIMD evaluation.
The old full scalar/SIMD/math proof is reused by unchanged source and exact DEV
identity rather than being rerun as a broad matrix or mislabeled as execution
of the new shipping native image.

`verify.py` runs only the new selected whole file, in two fresh sessions. It
checks exact restored native bytes, wrapper/native PID continuity, deleted
private path, no compiler children, fd0/1/2, three persistent startup TIDs,
legal own-side white/black zero clocks and finite bare go. Active quit and EOF
each produce one legal closing bestmove and reach exit0, reader EOF and absent
process. Cancellation causality remains unproven. No games, fair benchmark,
profile sweep, CI dispatch, maintained-entry promotion or 4KiB acceptance is
claimed by this experiment.
