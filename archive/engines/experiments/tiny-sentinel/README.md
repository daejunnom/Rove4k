# Tiny A sentinel architecture experiment

This architecture is **rejected for the current source-size objective**. With
matched readable modules and the same encoding recipe, the signed 0x88 baseline
produces a 5,531-byte complete file. The controlled sentinel form produces
5,743 bytes (**+212**), and its native hash/order form produces 5,719 bytes
(**+188**). Both sentinel forms pass the checks below, but neither improves the
matched complete file or meets 4,096 bytes. Neither form replaces canonical Tiny A.

The separately qualified **5,283-byte** encoding artifact is retained as a pinned
historical control. It came from a different search/source-renaming co-design
seed. It is not the matched architecture baseline, and its earlier savings
cannot be added to this experiment's source or wrapper costs.

All changes in this directory were authored from the owned Tiny A implementation
and local independent contracts. No GPL engine source was read, copied or
vendored for this experiment. The canonical Tiny A and shared encoding helpers
remain unchanged.

## Representation and preserved contracts

The board uses `uint8_t b[120]` with a 10-by-12 sentinel border. A real square is
`21 + file + rank*10`, so a1 is 21 and h8 is 98. Empty is zero. P/N/B/R/Q/K use
low three-bit values 1..6; white adds bit 8 and black adds bit 16. Every offboard
cell is `EDGE=24`, containing both colour bits and type zero. Thus
`target & moving_side` rejects both friendly pieces and the border in one test.

The largest first knight hop is 21, so probes from real squares stay in indices
0..119. Sliding rays stop at their first EDGE cell. Attack queries test their
requested target before friendly occupancy, retaining protection of a square
occupied by a friendly piece. Pawn, king, EP and castle logic use sentinel
coordinates, not the old 0x88 bit masks.

All affected domains are converted together:

- `Board.s` is 8/16. `SIDE(s)=s>>4` maps white/black to king-array indices 0/1;
  `OTHER(s)=s^24` changes colour. Pawn direction is +10/-10.
- Piece-square HCE uses `FILE_OF(q)=q%10-1` and `RANK_OF(q)=q/10-2`. It retains
  the same integer material/advance/centre terms and incremental white-view sum.
  Public DEV evaluation changes sign by colour, rather than multiplying by 8/16.
- `Move` retains seven from bits, seven to bits and three promotion bits: 17 bits
  total. TT score/depth/bound fields keep their existing positions above them.
- History becomes `int16_t[120][120]`. Continuation still has 13 indices, now
  `TYPE(piece)+6*SIDE(piece)`: empty 0, white P..K 1..6, black P..K 7..12. This
  is a bijection of the old signed-piece-plus-six indices, not lost state.
- Piece hashes, state hashes, reversible-path context and move tie ordering
  have explicit controlled/native modes described below.
- Start/FEN admission, castling-right normalization, legal-only EP identity,
  copy-make updates, dead-material handling and king safety are preserved.
  Public FEN and UCI coordinates retain normal chess notation.

The mailbox backing array saves eight bytes, and the declared history backing
array saves `(128*128-120*120)*2 = 3,968` bytes per worker. These are arithmetic
array sizes; no whole-`Board`/`Worker` ABI size measurement was performed, and
these storage savings did not improve the submitted source-file cost.

The runtime retains the fixed startup pool, stdin on main, shared TT and
independent worker heuristics. In the measured profile, two search workers plus
main are created before the first UCI input. Every epoch finishes and emits its
single result before a later position can commit. The existing 32,767-byte
whole-line limit, NUL/overflow draining, transactional position replay, bounded
clock parsing, zero-clock budget, stop, ready, quit and EOF contracts remain.
Shipping adds no resource options or DEV commands.

## Controlled equality and native policy

`CONTROLLED=1` maps each sentinel square/piece back to the original signed 0x88
piece-hash domain and maps move tie keys to old square coordinates. The state
hash uses the same side/castling/legal-EP domains. This form is intended to retain
the exact original search policy while changing board storage and operations.

`CONTROLLED=0` hashes native tagged pieces and sentinel coordinates directly,
and uses native packed moves for deterministic tie ordering. Its piece-key
domains remain disjoint from state-key inputs. Changing TT hashes and move ties
can change search work and learned state. This is an independently checked
policy variant; no exact search equivalence to the original is claimed for it.

`compare.py` compiles each complete readable translation unit with its original
main renamed, then calls the actual `think` implementation. Both runs have one
worker, TT bits 18 and DEV enabled. The same 12 search fixtures preserve TT and
learning between cases, including a repeated final start position.

For controlled comparison only, the harness projects history into a zero-filled
canonical 128-by-128 0x88 grid and asserts unused source cells are zero. It maps
old continuation indices 0..5 to new 12..7, old empty 6 to new 0, and old 7..12
to new 1..6. It normalizes only the TT's low 17 move bits; full keys, upper data
bits, slots and table order are preserved. Correction and full path-key arrays
are compared directly under equal controlled hashes.

All 12 records matched exactly between baseline and `CONTROLLED=1` at `-O2` and
again under ASAN/UBSAN. Both instrumented results also matched the normal
baseline. Compared fields include actual UCI bestmove, score, completed depth,
local/global nodes, full normalized learning/path digests, every TT key/data
slot, PVS/QS/TT hits and history/continuation/correction/abort counters. Positive
PVS, QS, TT and every learning branch were observed. Abort was zero in these
12 fixtures; separate PLY=4 tests exercise that branch. These comparisons are
bounded deterministic evidence, not an all-position or SMP determinism proof.

## Matched complete-file costs

The primary comparison uses `--argv-form list`, the default. Every form uses the
same preprocessing, lexical compaction, fixed-resource literals, predetermined
function spellings, compiler argv and shared-stream producer. The selected XZ
recipe is fixed `9e`, CRC64, `lc=2`, `lp=0`, `pb=0`; this experiment introduces
no additional compressor search. The 75-byte prefix, compressed Python
bootstrap, C source and compiler command all count toward complete file size.

| Matched source form | Shipping C | Encoded C | Shipping native | Complete selected file | Delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Signed 0x88 baseline | 13,541 | 13,110 | 26,432 | **5,531** | 0 |
| Sentinel, `CONTROLLED=1` | 14,261 | 13,830 | 26,456 | **5,743** | **+212** |
| Sentinel, `CONTROLLED=0` | 14,171 | 13,740 | 26,432 | **5,719** | **+188** |

The primary sentinel selected file hashes are
`f9e36b2dc00ce60866bfac9bab678693fc042b7739d333e5c00b443c25c91e1f`
and `4dc9e8c9f55cdabf58e88869e8ddff5b9ef3bf90ab6544cf498cd56c9160784c`.
Both exact files passed the five shipping groups below. Smaller mailbox/history
storage and equal native file size do not imply smaller compressed source.

A secondary `--argv-form split` rendering, with unchanged C and compiler argv,
measures baseline 5,527, controlled 5,751 (**+224**) and native 5,723 (**+196**)
bytes. Those exact secondary wrappers have byte/source/native identity evidence,
but have not independently acquired shipping runtime qualification here. They
also fail the matched size objective. A pure regeneration check reproduced all
six primary/secondary complete-file hashes against the existing reports; no
further architecture or compressor trials were added.

The ordinary native build command retains C11 and `-pthread`. The encoded
source compiler command is the existing measured recipe:

```text
cc -Os -x c - -o x -s
```

For each form, that command's transformed C is compiled twice and must equal its
own stripped compiler-stdin reference built with the explicit flags. This
comparison is restricted to **WSL Ubuntu 24.04.4 LTS, x86-64, GCC 13.3.0
(`13.3.0-6ubuntu2~24.04.1`), glibc 2.39**, two workers and TT bits 18. Omitting
`-pthread`/`-std=c11` is not a portability claim or deletion of pthread workers.
The previously qualified encoding image imports pthread functions at
`GLIBC_2.34` from libc; these sentinel forms additionally pass their own native
byte gate and actual fixed-thread protocol checks on this host. Other target
resources, libc versions and compilers require new qualification.

## Validation coverage

`build.py` freezes baseline/sentinel input modules and all producer helpers into
the new external output before using them. It independently compiles DEV,
original shipping and compact shipping twice, requires whole native equality
between original/compact shipping, and repeats every complete wrapper. Native
identity is required within each form; different architectures are not required
to produce identical ELF bytes.

The common external verifier passed **26 groups** across the two sentinel modes:

| Actual artifact class | Groups per mode | Both modes |
| --- | --- | ---: |
| DEV | Rules, state, search | 6 |
| DEV public interface | Protocol, lifecycle, bounded self-play, EOF, quit | 10 |
| Primary selected complete shipping file | Protocol, lifecycle, bounded self-play, EOF, quit | 10 |

Shipping lifecycle evidence retains `cancellation_causality: unproven`; observed
work before a signal and a legal result afterward are not internal attribution.
The tests assert fixed startup thread IDs and no stale/duplicate results. No
timing, NPS, Elo or large-machine scalability conclusion is taken from them.

Both modes separately passed the actual algorithm check: positive PVS/QS/TT/
history/continuation/correction counters; TT halfmove-context scores `[0,916]`
without clearing between contexts; no correction learning from the EP capture;
and ten positive/negative material-draw cases. Separate one-worker `PLY=4` builds
observed one ply abort while retaining depth one's legal bestmove when depth
two was interrupted. These are distinct fixture profiles, not the measured
two-worker package profile.

The independent board contract passed all five profiles:

| Board contract profile | Audited positions | Legal children | Pointwise attack queries |
| --- | ---: | ---: | ---: |
| Baseline | 134 | 3,467 | 17,152 |
| Controlled | 134 | 3,467 | 17,152 |
| Native | 134 | 3,467 | 17,152 |
| Controlled ASAN/UBSAN | 62 | 1,278 | 7,936 |
| Native ASAN/UBSAN | 62 | 1,278 | 7,936 |

Every profile additionally passed 131,072 randomized attack queries and the six
frozen final perft totals: 197,281 / 97,862 / 43,238 / 9,467 / 62,379 / 89,890.
Every visited perft state checks the board invariant and an independently
written HCE expression. The Python oracle independently checks legal sets,
attacks, normalized state, incremental hash/context and child states across
special cases and seeded legal replays. All 134 complete controlled reports
equal baseline, including generation order. FEN admitting a seventeenth piece
is rejected transactionally, inventory/border corruption is detected, and an
intentional move-list overflow aborts with SIGABRT instead of writing past it.
These finite checks do not prove every possible chess position.

## Reproduce outside the checkout

Run from the repository root in the measured Linux environment. Use new absolute
output locations outside the checkout. The following are developer validation
commands; only the producer's recorded dependencies belong to the entry runtime.

```sh
python3 -B engines/experiments/tiny-sentinel/build.py \
  --out /absolute/external/rove4k-tiny-sentinel-replay-new --argv-form list \
  --selected-control /absolute/external/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --selected-control-sha256 798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645
python3 -B engines/experiments/tiny-sentinel/compare.py \
  --baseline-source /absolute/external/rove4k-tiny-sentinel-replay-new/baseline/assembled.c \
  --sentinel-source /absolute/external/rove4k-tiny-sentinel-replay-new/sentinel-controlled/assembled.c \
  --out /absolute/external/rove4k-tiny-sentinel-compare-replay-new --sanitize
python3 -B engines/experiments/tiny-sentinel/board-check.py \
  --frozen /absolute/external/rove4k-tiny-sentinel-replay-new/frozen \
  --out /absolute/external/rove4k-tiny-sentinel-contract-replay-new
python3 -B engines/tests/verify.py \
  --manifest /absolute/external/rove4k-tiny-sentinel-replay-new/validation-manifest.json \
  --select sentinel-controlled-dev --select sentinel-native-dev --suite dev \
  --out /absolute/external/rove4k-tiny-sentinel-dev-replay-new
python3 -B engines/tests/verify.py \
  --manifest /absolute/external/rove4k-tiny-sentinel-replay-new/validation-manifest.json \
  --select sentinel-controlled-dev --select sentinel-native-dev --suite shipping \
  --out /absolute/external/rove4k-tiny-sentinel-public-replay-new
python3 -B engines/tests/verify.py \
  --manifest /absolute/external/rove4k-tiny-sentinel-replay-new/validation-manifest.json \
  --select sentinel-controlled-selected --select sentinel-native-selected --suite shipping \
  --out /absolute/external/rove4k-tiny-sentinel-shipping-replay-new
mkdir /absolute/external/rove4k-tiny-sentinel-caps-replay-new
cc -std=c11 -Os -pthread -DDEV=1 -DWORKERS=1 -DTT_BITS=18 -DPLY=4 -DCONTROLLED=1 \
  /absolute/external/rove4k-tiny-sentinel-replay-new/sentinel-controlled/assembled.c \
  -o /absolute/external/rove4k-tiny-sentinel-caps-replay-new/controlled
cc -std=c11 -Os -pthread -DDEV=1 -DWORKERS=1 -DTT_BITS=18 -DPLY=4 -DCONTROLLED=0 \
  /absolute/external/rove4k-tiny-sentinel-replay-new/sentinel-native/assembled.c \
  -o /absolute/external/rove4k-tiny-sentinel-caps-replay-new/native
python3 -B engines/compact/tiny-a/check.py \
  --engine /absolute/external/rove4k-tiny-sentinel-replay-new/sentinel-controlled/dev/x \
  --cap-engine /absolute/external/rove4k-tiny-sentinel-caps-replay-new/controlled \
  --out /absolute/external/rove4k-tiny-sentinel-controlled-algorithms-replay-new.json
python3 -B engines/compact/tiny-a/check.py \
  --engine /absolute/external/rove4k-tiny-sentinel-replay-new/sentinel-native/dev/x \
  --cap-engine /absolute/external/rove4k-tiny-sentinel-caps-replay-new/native \
  --out /absolute/external/rove4k-tiny-sentinel-native-algorithms-replay-new.json
```

Logical measured-evidence records are listed below; their actual locations are
kept in the external run catalog:

```text
/absolute/external/rove4k-tiny-sentinel-first-20261020/build.json
/absolute/external/rove4k-tiny-sentinel-first-20261020/argv-recipe-reproduction.json
/absolute/external/rove4k-tiny-sentinel-final-20261020/build.json
/absolute/external/rove4k-tiny-sentinel-compare-20261020/results.json
/absolute/external/rove4k-tiny-sentinel-dev-20261020/results.json
/absolute/external/rove4k-tiny-sentinel-dev-public-20261020/results.json
/absolute/external/rove4k-tiny-sentinel-shipping-20261020/results.json
/absolute/external/rove4k-tiny-sentinel-controlled-algorithms-20261020.json
/absolute/external/rove4k-tiny-sentinel-native-algorithms-20261020.json
/absolute/external/rove4k-tiny-sentinel-contract-20261020/results.json
```

Final Windows copies, the manifest/hashes and both actual primary sentinel
`.sh` files are retained in
`external-evidence/rove4k-tiny-sentinel-20261020-evidence/`.
Its `summary.json` separates `initial-build.json`, `split-build.json`,
`compare.json`, `board-contract.json`, `dev.json`, `dev-public.json`,
`shipping.json`, both algorithm reports, `cap-build.json` and
`argv-recipe-reproduction.json`.

The experiment is frozen as a measured adverse architecture result. Training,
AWS, canonical promotion, tournament acceptance and A–F completion are excluded.
