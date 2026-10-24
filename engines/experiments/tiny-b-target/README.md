# One Tiny B target-centered generation experiment

This is one fixed source-architecture hypothesis against the exact qualified
6,219-byte minimal-UCI B control. It does not edit Tiny B, the portfolio, active
entry experiments, or shared producers/checkers. No compiler/flag/identifier/
codec sweep, training, cloud connection, performance or strength study is used.

The candidate routes ordinary pseudo generation and exact SEE recaptures through
one target emitter backed by B's existing incremental bitboards and `attackers()`.
It removes the separate forward knight/slider/king geometry loop and SEE's own
bit-pop/promotion emitter. `add()` supplies all four promotions. Negative target
means all targets; square zero remains a valid single target. Ordinary pawn
pushes and castles remain explicit; single-target mode admits only captures of
enemy occupants. Empty pawn diagonals require the normalized EP square.

The two replacement regions are the complete old `gen()` body and only the
enumeration part of `exchange()`. Exact retained source bytes include mailbox/
bitboard state, `put/make`, king safety, hash/ordered reversible path/halfmove,
full-key coherent TT, PVS/QS/history/continuation/correction, qualified singular
and excluded-learning fences, SEE's original stop/deadline/visit/incomplete
guard, the startup pool and minimal UCI policy. Move generation order changes;
node/score parity with the control is not claimed.

The fixed profile is two search workers/three total startup threads, TT bits 18,
PLY 128, GCC 13.3/glibc 2.39 on WSL Ubuntu x86-64. The exact compiler argv is:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

The actual control wrapper's bootstrap and compiler command remain fixed. Only
the C literal changes, using the same XZ CRC64 preset 9 extreme lc3/lp0/pb2 and
75-byte shell prefix. Complete file size includes all restoration/compiler code.

Independent source review must precede the first compile. `build.py` requires a
source-review receipt matching the exact transform and both C templates. It
freezes the pinned control manifest/readable/compact/native/wrapper and every
executed helper before importing it. Both source generations, native compiles
and full wrappers repeat independently; the control must reproduce its actual
recorded C/native/6,219-byte file exactly. Historical receipts and source/native
identity classes are not replaced by a source-size estimate.

Ordinary generation can ask up to 64 reverse attack queries instead of walking
once from each piece. This may substantially slow nodes. There is no performance
claim. The SEE generator now needs a local `Move[512]`: at most 31 simultaneous
exchange frames contribute 63,488 array bytes under the 32-piece admission bound.
Whole-frame accounting for this actual image is recorded below; the previous
image's stack qualification is not reused.

The first-cost result is recorded outside Git. A loss/equality ends this one
experiment without runtime QA or a second variant. A gain permits only the
focused legal-child/SEE/special-move, real-TT singular/excluded-learning and
actual selected-wrapper/image/thread/active-exit checks described by the root
task. No fair NPS, games or broad canonical matrix follows this cost driver.

Example with the exact historical control tree available:

```sh
python3 -I -B engines/experiments/tiny-b-target/build.py \
  --review /external/source-review.json --out /external/new/tiny-b-target
```

`--control` relocates identical frozen historical inputs; every literal hash
admission remains mandatory. Generated files and reports remain outside Git.

## Recorded first cost

The one fixed candidate produced a 6,155-byte complete file, a 64-byte saving
against the exact reproduced 6,219-byte control. It remains 2,059 bytes above
4,096 and is not a 4KiB submission. No second variant or flag sweep was measured.

| Actual form | Control | Target emitter | Change |
| --- | ---: | ---: | ---: |
| Compact C source | 15,566 B | 15,456 B | -110 B |
| Compiled stdin native image | 26,592 B | 26,624 B | +32 B |
| Complete bootstrap file | 6,219 B | 6,155 B | -64 B |

Source generation, native compilation and complete packaging each repeated
independently twice for each form and were byte-identical within their form.
The control also reproduced all historical source/native/whole identities.
The cost receipt retains its original `candidate_runtime_qualified: false`;
later focused runtime evidence is a separate receipt, not a rewritten cost claim.

The exact external receipts are:

```text
/home/stemxstudio/rove4k-tiny-b-target-first-20261020/results.json
  sha256 9794de8564b31404254fb14864827d40f4fb00323a40868abca6c26b9f9d3976
/home/stemxstudio/rove4k-tiny-b-target-focused-20261020/results.json
/home/stemxstudio/rove4k-tiny-b-target-stack-20261020/results.json
  sha256 b76adb3705209ae26d227ba8ea0c427a9398ef49cf9d4bbaf488157e76909ce1
```

The candidate readable C SHA-256 is
`caadf2ed45ecde9fb760b2697f9f38b9023a6729870ea6eb8ff8472e0100d2ce`;
compact C is `81cfb3099857a95a91f7e8f97caa080f938a6a73435277b75ea6201bc3b1b251`;
native is `50e41afb800f86aff1022511d67d1bbba14c86c3a6e52a48233e1d5ce9174983`;
the actual selected complete file is
`8da1090b68f9e5977938cd0fd2cb33e097335b6c3793707c1e3f20cb6bfa15e4`.

## Focused qualification

`check.py --cost /external/first-cost/results.json --out /external/new/focused`
freezes its checker, target fixture and exact historical oracle/raw-process/
B-contract sources before running. Optimized and AddressSanitizer/UBSan builds
both passed with empty stderr. Each checked 18 special-move positions, 1,152
single-target modes, 309 pseudo/257 legal children and 24 promotion moves. The
1,093 attack-query count is source-derived, not runtime performance measurement.
The ten exact legal SEE cases, two illegal controls and original stop/expired
deadline controls passed. The original broad board/attacker campaign was not run.

The actual depth-3 exact TT candidate qualified a depth-6 singular probe. A taken
extension used prime 910, alternatives 16 and threshold 898; its actual child TT
depth was 6 instead of the ordinary 5. The changed alternative value follows the
declared generation order change. Ordinary history/continuation and correction
(64 to 63) positive learning controls changed, while excluded low/wide/expired
probes preserved TT, learning arrays, Board, ordered path and original deadline.
These internal contracts use TT bits 20 to avoid the watched-child slot collision;
the shipping profile and complete file retain TT bits 18.

The frozen independent 64-square oracle matched all legal sets, invariants and
halfmoves for 15 special roots and all 207 of their legal child positions. Two
actual selected-wrapper sessions exercised active `quit` and active EOF. Both
loaded the exact selected native bytes by same-PID fd exec, kept exactly three
startup TIDs, had only file descriptors 0/1/2 after readiness, and left no compiler
children or temporary files. Worker CPU progression was observed before control;
each session then returned one legal `bestmove g1f3`, exit 0, joined readers and
an absent native PID. The receipt explicitly retains
`stop_causal_link: unproven`: this observation does not establish cancellation
causality. No games, fair NPS or broad canonical matrix were run.

## New-image stack accounting

`stack.py --cost /external/first-cost/results.json --out /external/new/stack`
adds only `-fstack-usage` to one diagnostic compile. Its entire native file was
byte-identical to the selected shipping native. GCC reported search 4,608 B
(dynamic, bounded), exchange 2,448 B (static, including the 2,048-byte move array),
see 352 B, make 80 B, EP normalization 368 B, generate 96 B and attackers 56 B.

The derivation allows 133 simultaneous search frames: 128 ordinary ply frames
plus five same-ply singular verification frames. Verification depth follows
126 -> 62 -> 30 -> 14 -> 6 -> 2; an excluded root cannot verify itself, and normal
descendant depth cannot increase when the extension is at most one. The 31 SEE
frames follow the admission limit of 32 pieces minus two uncapturable kings:
each recapture removes one remaining capturable piece, plus the initial frame.

The conservative compiler-accounted worker path is 692,520 B: 689,784 B of GCC
frames plus a 2,736-byte reserve of 16 bytes per internal call/tail edge. This
includes search, SEE and reachable helper frames. It is 356,056 B below 1 MiB,
but `whole_runtime_stack_qualified` remains false: libc, pthread/loader/signal/
thread-entry frames and deepest-path runtime behavior have not been measured.
The diagnostic executed no engine. An initial report parser stopped at GCC's
`see.isra` versus ELF's `see.isra.0` clone spelling; exact binding was corrected
and analysis resumed on the existing single compile. Both driver revisions and
the original compile receipt remain outside Git; no second compile was used.

The Windows evidence export is
`C:/Users/강민수/Documents/Codex/rove4k-tiny-b-target-20261020-evidence/`.
Its final `summary.json` binds these eight source files, all separate receipts
and the selected candidate/control complete files. This is a focused source
checkpoint, without an adoption, strength, whole-runtime-stack or 4KiB claim.
