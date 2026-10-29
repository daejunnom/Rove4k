# Maintained minimal C entry

`engine.c` is the readable canonical program for the selected **5,947-byte** C
source entry. It includes both development and shipping branches. Maintain this
file when changing the program; compact C, ELF and the compressed executable
are generated outputs. This entry preserves the existing selected algorithm,
resources, minimum UCI policy, compiler arguments, bootstrap and compression
bytes. It performs no selection sweep and does not depend on historical output
directories, executables, reports or network access.

The current source incorporates the already qualified shipping HCE-cache removal
from its 5,955-byte predecessor: only `Board.v` and its two maintenance updates
are DEV-only. The existing builder, verifier, compiler, spelling and transport
contracts remain unchanged. The predecessor source and its exact archive and
5,955-byte source/native/bootstrap/whole controls were preserved outside Git
before this update.

The selected entry remains **1,851 bytes above 4,096**. This source promotion
does not establish 4KiB eligibility, playing strength or many-core scalability.
The exact-byte domain is Linux x86-64, Ubuntu 24.04.4, GCC 13.3.0, binutils 2.42,
glibc 2.39, Python 3.12.3 and xz 5.4.5. A different compiler/encoder result fails
the identity gates instead of being silently accepted as the qualified entry.

## Fixed production recipe

From an ordinary repository checkout on the recorded Linux toolchain, including
WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-c/build.py --out /absolute/new/C-build --dev
```

The destination must not exist and must stay outside any Git checkout. The
single shipping profile fixes two search workers, one command thread, TT bits
18 and PLY 128. `--dev` adds the unchanged diagnostic control; it does not choose
a different shipping configuration. The exact shipping compiler argv is:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -mavx2 -DDEV=0 -x c - -o x
```

The DEV command changes only `-DDEV=0` to `-DDEV=1`. The fixed AVX2 target is
intentional. Unlike A's selected encoding recipe, this selected C entry has no
token renames, function spellings, fixed-resource token substitutions, stripped
ELF class or shorter compiler argv. Those A decisions are not applied here.

The build graph contains four ordinary tracked helpers:
`engines/scripts/specialize.py`, `engines/scripts/minify.py`,
`engines/compact/tiny-a/stitch.py` and `engines/compact/tiny-a/pack_stream.py`.
It consumes only `specialize_c`, lexical `compact_source`, the fixed eight
shipping no-op `strip_dev_counters` sites and exact `source_literal` spelling.
The recipe pins the helpers' LF-normalized hashes, copies and checks their
bytes before importing them outside Git, and rejects lone CR. This folder's
`.gitattributes` fixes its own tracked text to LF.

`bootstrap.py.in` is the exact selected Python bootstrap, with only its C source
literal replaced by one explicit marker. Its original compiler argv list stays
verbatim. `launcher.sh` is the exact 75-byte prefix. Packaging inserts the source
literal and applies one fixed XZ/LZMA2 preset 9 extreme configuration,
`lc=3/lp=0/pb=2`, CRC64. The full shell/bootstrap/source/compiler bytes count
toward the 5,947 bytes. Signal blocking, child process groups, forwarding,
wait/kill fallback, private `TMPDIR`, cleanup and fd execution are preserved.

Each build preprocesses, compacts, compiles and packages independently twice.
Every stage must match the selected expected hash, and the two complete output
sets must match each other. It repeats the optional DEV form too. Inputs,
intermediate C, stderr, bootstrap, ELF, executable and `build.json` stay outside
Git; failures retain an incomplete report.

| Exact output | Bytes | SHA-256 |
| --- | ---: | --- |
| Readable canonical engine | 27,003 | `1f0f18ffee91ecddea3cb31e7553e1d1415e25b3f759cdec4e0f375fcd0b2298` |
| Compact shipping C | 14,206 | `dcbfb3e92b52e2ee902055aa7331c068b6b95226f00b1edfc4b63b789405105c` |
| Restored stdin native ELF | 26,464 | `c948e31aea9f413614881b8e8e6060e5aa70314dd84b2d9b544e3f20edb99df2` |
| Complete selected source executable | 5,947 | `76ed08f657398ac4b8cfbd0ff2230257ab18547f082b4c29af62428d802f33d3` |

The diagnostic source and native ELF must respectively equal
`31415fddd3cf1ebd378e58ccc41cdb2b9382df646e41f002653734a5e4d746bf`
and `5e9b05e55cba56c63b180c2dce1d9330d2f3a69d7563360e35484684ebb730ba`.

## Closed source archive and selected runtime

```sh
python3 -B engines/compact/tiny-entry-c/fresh.py --out /absolute/new/C-source-proof
python3 -B /absolute/new/C-source-proof/checkout-1/engines/compact/tiny-entry-c/verify.py \
  --build /absolute/new/C-source-proof/build-1 --out /absolute/new/C-runtime-proof
```

`fresh.py` explicitly names the complete source closure: this folder's nine
files, the four build helpers and two independent black-box helpers. It preserves
the raw and normalized input hashes, creates an isolated local Git repository
with no commits/remotes, writes a tree and archives exactly those named files.
It never changes the calling project's index. It rejects unexpected archive
paths/types and extracts twice into independent source directories. Both
extracted builders execute their two attempts and must produce the same source,
native image, complete executable, bootstrap and diagnostic outputs. The source
tree/archive hash, complete path list and raw/LF hashes bind the source proof.
This isolated source archive is explicitly separate from project-HEAD CI.

`verify.py` freezes two pinned tracked black-box helpers and launches only the
new selected complete file in two fresh sessions. It verifies exact restored
native bytes through `/proc`, deleted restoration directory, no compiler
children, three persistent startup TIDs, legal own-side white/black zero clocks
and finite bare go. It observes active-search quit/EOF, exactly one final legal
move, waited exit, absent process and finished output readers. This is selected
lifecycle evidence, not a fair performance study or proof that cancellation
caused the observed completion. Exact prior rule/core/SIMD coverage is reused
separately through identity rather than rerunning a broad campaign.

## Preserved engine and evidence boundary

C's shared 832-entry startup PSQT is built once from the exact HCE formula
before main and worker creation. The search leaf performs eight AVX2 gathers
over all 64 visible squares and consumes their horizontal vector sum. It ignores
cached HCE and mailbox padding; there is no runtime ISA selector. The 3,328-byte
table is shared across workers. Actual PVS/QS, coherent full-key locked TT,
history, continuation, correction, repetition/halfmove context, legal move
admission and completed-root publication boundaries remain unchanged.

The current shipping Board is 168 bytes on the qualified LP64 target; DEV keeps
the predecessor's 176-byte layout, incremental HCE updates and independent
invariant oracle. The raw SIMD leaf and `best-evaluation` residual were already
used before cache removal. That residual, its sign/clamp, startup PSQT and
capture-priority `value()` calls are unchanged. The original readable comment
describing incremental `v` now applies to the retained DEV field.

Shipping `uci` returns only `uciok`; `isready` returns `readyok`.
`position startpos [moves ...]` remains transactional. An own-side clock uses
the original formula/caps and minimum 1 ms, while clockless bare go uses the
fixed 1,000 ms default. Optional `stop`, `ucinewgame`, `infinite` and unknown
words are consumed without adding public controls. Next-go, position, quit and
EOF still settle the old search before state reuse or resource release. DEV
retains its stronger commands, identification, FEN and diagnostics.

The exact current 5,947-byte selection is bound by the cache qualification index
`67d7dce0b1852f7227f62f87c9b9568c9ebbc365274d182a4515e707200f2d11`, producer
`ab45382eaae131897e9cb113f11d984cd7205d2040696941fb019d29f3dcac68`, focused
actual-DEV0 state/core proof
`ec77e71a259b9017ef8bd893e5b77e26388ebc396cea55e98144db7546573765`, and
selected-file runtime
`9885005c404b06b5403b6f7ea71839446687d99f5458b2fbc425c99246c80cf6`.
Its optimized/sanitized proof compares 160,432 normalized positions, 150,419
legal children, 832 PSQT terms, 14 special fixtures and 5,000 deterministic
plies per run. Ten direct shipping core checks per form include actual TT
context misses, draw/mate precedence, positive production learning and EP
correction exclusion. The direct ply-abort fixture preserves fields installed
from a completed depth-four search; it is not a new `think()` publication or
concurrent-cancellation observation. Exact cross-form search score/node/table
equality was not claimed.

The separately retained 5,955-byte predecessor has source
`f0bc01d4ebde79578248e1d210723bff6be0639e829c166d6204de02466c3e82`, source tree
`720ce86c92d8ffe48689ce5064ad0a8eee21b7c2`, archive
`ec6a6b09c96f25035255fdebc890b0ab0127035686f5e4e7287282d0b94e1345` and maintained
source receipt
`6bf1a0b9a8c967618409a763f0531bdbe69f5a225c9d380c805245cba1f9a44c`.
Its original portfolio index, producer and C core/SIMD/context receipts remain
separate predecessor metadata in the recipe. The unchanged PSQT/math and exact
DEV identities support reuse of the prior 369,255-board/738,510-SIMD-call
optimized/sanitized coverage; that is not relabeled as a new execution of the
changed shipping layout.

Only hashes and scope metadata are stored here. No historical report, build,
archive, executable or cache-experiment output is opened by the maintained
build/fresh/verifier commands. The cache experiment itself has an independent
owned control source/recipe/bootstrap and does not consume this mutable entry.
Fresh source archives and selected-file sessions establish regeneration and
physical runtime for this promotion separately from the reused focused proofs
and from project-HEAD CI acceptance.
