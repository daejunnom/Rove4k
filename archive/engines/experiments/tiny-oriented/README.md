# Tiny A moving-side-oriented architecture experiment

This architecture is **rejected for the current complete-file size objective**.
Under the same frozen source/encoding recipe, the absolute-board baseline is
**5,527 bytes** and the oriented board is **5,559 bytes: +32 bytes**. The oriented
file remains **1,463 bytes above 4,096**. The implementation and evidence are
preserved as an adverse architecture result; there is no canonical adoption or
4K eligibility claim.

The previously qualified 5,283-byte file is a pinned historical control from a
different search/source-renaming co-design seed. It is not this experiment's
matched baseline, and its earlier savings cannot be added to this result.
This experiment was authored from the owned Tiny A implementation and local
independent contracts. No external engine source was read or copied.

## One relative board, one canonical actual-colour hash

The board retains a signed `int8_t[128]` 0x88 mailbox. Its interpretation changes
after each legal move: the mover is positive and advances +16, while opposing
pieces are negative. `Board.s` still means the actual colour, white +1 or black
-1. An absolute square is `relative_q ^ (s<0 ? 112 : 0)`. Files stay unchanged;
the three rank bits are reversed for an actual black mover.

`flip` negates the vertically mirrored pieces, exchanges/mirrors the two king
locations, exchanges the two pairs of castling flags, mirrors an existing EP
target, negates cached HCE and changes `s`. `k[0]` is always the own king and
`k[1]` the opponent; low castling bits are always own rights. Own move generation
uses positive pieces and forward pawn movement. The attack query scans opposing
negative pieces. After applying a generated move, own-king safety is checked
before flipping the child to the next mover.

There is **one `h` field**, not a pair of orientation hashes. Each piece update
maps its local piece and square back to the original actual-colour key domain:

```text
actual_piece = relative_piece * Board.s
actual_square = relative_square ^ (Board.s < 0 ? 112 : 0)
piece_key = mix(actual_square + (actual_piece + 6)*128)
```

The flip changes representation while preserving actual piece placement, so
piece keys need not be recomputed or stored twice. At both flip call sites only
piece keys are attached. The state contribution is attached afterward using the
actual turn, absolute castling flags and legally capturable EP file. A black FEN
is first admitted in absolute form, then oriented, EP-normalized and completed
with its state hash. Reversible-path context still uses the canonical actual
hash after every move; pawn moves/captures reset that context.

Cached `v` is now mover-view HCE. The exact integer identity
`value(-piece, square^112) == -value(piece, square)` permits `v=-v` during a flip.
The independent contract checks all **768 piece/square identities** and actual
incremental values. DEV `eval` and `state.eval` therefore return `position.v`
directly. They retain the same public side-to-move interpretation as baseline.

Public coordinates always use the board being interpreted. `text` accepts a
`const Board *`; `parse` passes its local scratch board during nested position
replay, while final results and DEV legal moves pass the immutable root
`&position`. This prevents a prior global root's colour from misinterpreting a
later replay ply. `0000` and promotion suffixes retain their previous spelling.

The fixed worker pool, shared TT, generated-list membership precondition,
transactional position commit, bounded input/clock handling and output barriers
remain. The measured entry creates two workers plus main before accepting UCI
input, and emits one final bestmove per accepted search. Shipping exposes no
runtime resource options or DEV commands.

## Search policy is deliberately different

TT keys remain canonical actual-colour hashes with halfmove/path context, but
stored moves are local to the keyed position's orientation. Their 17-bit layout
is unchanged. History uses relative from/to squares, and deterministic move ties
use the relative packed move. Previous/current continuation is now a **7-by-7
piece-kind table**, including empty/root kind zero. After a child flip, the prior
mover is negative at the mirrored destination; its positive kind is passed to
the next search call, including promotions.

Pooling history and continuation across actual colours and changing black move
ordering changes search policy. No exact baseline node count, search digest or
strength equivalence is asserted. The board contract instead compares complete
absolute state and child state after sorting legal moves by public UCI spelling.
All 146 normal reports match baseline in that normalized form; generation order
is intentionally not part of that equality.

The continuation backing array saves `(13*13-7*7)*2 = 240` bytes per worker by
declaration. There is no measured whole-struct ABI-size or speed claim. The
extra representation work did not produce a smaller complete source entry.

## Matched costs and independent reproduction

The default is the existing **argv string-split** representation. Both forms use
the same preprocessing, lexical compaction, fixed-resource literals,
predetermined function spellings, compiler command and shared-stream packaging.
XZ is fixed to preset `9e`, CRC64, `lc=2`, `lp=0`, `pb=0`. This experiment adds no
flag, identifier or compression-parameter search.

| Matched source form | Shipping C | Encoded C | Shipping native | Complete selected file |
| --- | ---: | ---: | ---: | ---: |
| Absolute signed 0x88 baseline | 13,541 | 13,110 | 26,432 | **5,527** |
| Moving-side-oriented 0x88 | 13,579 | 13,184 | 26,432 | **5,559 (+32)** |

The selected oriented file has SHA-256
`af3918e83dcc81ce9f043c283b10ab83bef42b99fcb73daff76cca03f6b85d3f`.
Its 75-byte shell prefix and 5,484 bytes of shared XZ data both count. Python,
C source and compiler argv are inside that compressed stream; the shell prefix
is not the complete restoration overhead.

`build.py` freezes the inputs and helper sources before use, repeats each DEV/
original/compact native compile, requires original and compact shipping native
bytes to match within each form, and repeats every whole wrapper. The encoded
source also has to reproduce its own stripped compiler-stdin native reference.
An independent build in a second output tree reproduced the source, native and
complete artifact bytes for both forms. Equal native **sizes** between the
architectures do not mean equal native **images**.

The native build retains explicit C11 and `-pthread`. The fixed encoded command
is the previously selected measured recipe, represented with `.split()`:

```text
cc -Os -x c - -o x -s
```

Its omitted flags are qualified only in the measured **WSL Ubuntu 24.04.4 LTS,
x86-64, GCC 13.3.0 (`13.3.0-6ubuntu2~24.04.1`), glibc 2.39** environment, with
two workers and TT bits 18. New compilers, libc versions, or target resource
profiles require their own identity and runtime checks. No 255/508/511-worker
scalability or TCEC-machine compatibility claim follows from this local study.

## Actual wrapper and functional evidence

`qualify.py` verifies the selected full-file hash, decodes exactly one shared
compressed stream, and requires restricted literal ASTs to restore the recorded
C bytes and compiler argv. It compares the bootstrap skeleton with the frozen
producer after replacing only those two expressions with sentinels. Before
importing test code it freezes/hashes its own source, verifier, oracle, producer,
expression helper, report, source, bootstrap and selected wrapper.

The hash-identical frozen wrapper copy actually executed and restored a
22,664-byte stripped image with SHA-256
`0d0a4eae8da82b33800e88335de1b45f9c799161a090bf7c605aa9da22e567ef`.
It retained the launch PID, replaced the wrapper with a deleted ELF, left no
compiler child, and retained all three startup thread IDs through UCI-ready.
The actual image imports `pthread_create@GLIBC_2.34` and
`pthread_join@GLIBC_2.34`; `readelf` reports `libc.so.6` as its needed library.
Filesystem absence was sampled **after UCI-ready**. Cleanup before fd-exec is
established by the unchanged source ordering; no separate pre-input filesystem
sample is claimed.

The common verifier passed **13 groups**: all eight DEV groups and the five
shipping groups on the exact 5,559-byte selected file. These cover protocol,
rules, state, search, lifecycle, bounded self-play, EOF and quit as applicable.
Shipping lifecycle records retain `cancellation_causality: unproven`; observed
work and a later legal result do not independently attribute internal
cancellation. Thread identity and duplicate/stale output checks remain separate
assertions. No NPS, Elo or strength result is inferred.

The actual algorithm check observes positive PVS/QS/TT, history, continuation,
correction-update and correction-use counters. Halfmove contexts score `[0,916]`
without clearing the TT between them. EP does not produce quiet-only correction
updates, and ten positive/negative dead-material fixtures pass. A distinct
one-worker `PLY=4` build observes a ply abort, retains depth one's legal witness,
and does not mislabel the unfinished depth-two search as completed.

## Independent board contracts

All three actual profiles passed:

| Profile | Audited positions | Legal children | Pointwise attack queries |
| --- | ---: | ---: | ---: |
| Absolute baseline | 146 | 3,780 | 18,688 |
| Oriented | 146 | 3,780 | 18,688 |
| Oriented ASAN/UBSAN | 74 | 1,591 | 9,472 |

Each profile additionally checks 131,072 randomized attack queries, 768 value
flip identities and six perft fixtures covering **518,474 visited states** with
board/HCE invariants. The six final perft totals are 197,281 / 97,862 / 43,238 /
9,467 / 62,379 / 89,890. The independent Python oracle checks public legal sets,
attacks, absolute state, hashes/context and complete legal child states across
special cases and seeded replays. All 146 normalized normal reports equal
baseline, with legal children compared by move spelling rather than generation
order.

The contract also checks flip involution, inventory and offboard invariants,
transactional rejection of a seventeenth piece, invalid promotion spellings,
king-capture rejection, and an intentional move-list overflow ending in SIGABRT.
Castling and EP cases cover both actual colours after orientation changes.
These are finite board-contract checks, not an all-position proof or an exact
search-policy comparison.

## Reproduce outside the checkout

Run from the repository root in the measured Linux environment. All output
directories/files must be new, absolute and outside the checkout. These are
developer checks; the entry runtime itself uses only its recorded shell,
decoder, Python and compiler dependencies.

```sh
python3 -B engines/experiments/tiny-oriented/build.py \
  --out /absolute/external/rove4k-tiny-oriented-replay-new --argv-form split \
  --selected-control /absolute/external/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --selected-control-sha256 798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645
python3 -B engines/experiments/tiny-oriented/board-check.py \
  --frozen /absolute/external/rove4k-tiny-oriented-replay-new/frozen \
  --out /absolute/external/rove4k-tiny-oriented-contract-replay-new
python3 -B engines/tests/verify.py \
  --manifest /absolute/external/rove4k-tiny-oriented-replay-new/validation-manifest.json \
  --select oriented-dev --select oriented-selected --suite all \
  --out /absolute/external/rove4k-tiny-oriented-verification-replay-new
mkdir /absolute/external/rove4k-tiny-oriented-caps-replay-new
cc -std=c11 -Os -pthread -DDEV=1 -DWORKERS=1 -DTT_BITS=18 -DPLY=4 \
  /absolute/external/rove4k-tiny-oriented-replay-new/oriented/assembled.c \
  -o /absolute/external/rove4k-tiny-oriented-caps-replay-new/oriented
python3 -B engines/compact/tiny-a/check.py \
  --engine /absolute/external/rove4k-tiny-oriented-replay-new/oriented/dev/x \
  --cap-engine /absolute/external/rove4k-tiny-oriented-caps-replay-new/oriented \
  --out /absolute/external/rove4k-tiny-oriented-algorithms-replay-new.json
python3 -B engines/experiments/tiny-oriented/qualify.py \
  --build /absolute/external/rove4k-tiny-oriented-replay-new/build.json --form oriented \
  --out /absolute/external/rove4k-tiny-oriented-native-qualification-replay-new
python3 -B engines/experiments/tiny-oriented/build.py \
  --out /absolute/external/rove4k-tiny-oriented-rebuild-replay-new --argv-form split \
  --selected-control /absolute/external/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --selected-control-sha256 798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645
```

Compare actual source/native/whole-file bytes between the two fresh build
trees, rather than trusting equal size fields or path-dependent report JSON:

```sh
python3 - <<'PY'
from pathlib import Path
first = Path('/absolute/external/rove4k-tiny-oriented-replay-new')
second = Path('/absolute/external/rove4k-tiny-oriented-rebuild-replay-new')
files = ('assembled.c', 'dev/main.c', 'dev/x', 'original/main.c', 'original/x',
         'compact/main.c', 'compact/x', 'encoded/main.c', 'encoded/bootstrap.py',
         'encoded/xz/x', 'encoded/gzip/x', 'encoded/bzip2/x', 'encoded/xz-selected/x')
for form in ('baseline', 'oriented'):
    for relative in files:
        if (first/form/relative).read_bytes() != (second/form/relative).read_bytes():
            raise SystemExit('rebuild differs: ' + form + '/' + relative)
print('all declared source, native and complete-file bytes match')
PY
```

Measured evidence is retained outside Git:

```text
/absolute/external/rove4k-tiny-oriented-first-20261020/build.json
/absolute/external/rove4k-tiny-oriented-contract-20261020/results.json
/absolute/external/rove4k-tiny-oriented-verification-20261020/results.json
/absolute/external/rove4k-tiny-oriented-algorithms-20261020.json
/absolute/external/rove4k-tiny-oriented-native-qualification-20261020/identity.json
/absolute/external/rove4k-tiny-oriented-rebuild-20261020/reproduction.json
```

Final Windows evidence is retained at
`external-evidence/rove4k-tiny-oriented-20261020-evidence/`:
summary, build/manifest, verification, algorithms, board contract, actual native
identity, independent rebuild/reproduction, cap profile and verifier hashes,
plus the actual baseline/oriented wrappers and shipping C files.

The frozen result preserves a tested but larger architecture. Training, AWS,
canonical promotion, tournament acceptance and A–F completion remain outside
this experiment.
