# Maintained minimal C entry

`engine.c` is the readable canonical program for the selected **5,955-byte** C
source entry. It includes both development and shipping branches. Maintain this
file when changing the program; compact C, ELF and the compressed executable
are generated outputs. This entry preserves the existing selected algorithm,
resources, minimum UCI policy, compiler arguments, bootstrap and compression
bytes. It performs no selection sweep and does not depend on historical output
directories, executables, reports or network access.

The selected entry remains **1,859 bytes above 4,096**. This source promotion
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
toward the 5,955 bytes. Signal blocking, child process groups, forwarding,
wait/kill fallback, private `TMPDIR`, cleanup and fd execution are preserved.

Each build preprocesses, compacts, compiles and packages independently twice.
Every stage must match the selected expected hash, and the two complete output
sets must match each other. It repeats the optional DEV form too. Inputs,
intermediate C, stderr, bootstrap, ELF, executable and `build.json` stay outside
Git; failures retain an incomplete report.

| Exact output | Bytes | SHA-256 |
| --- | ---: | --- |
| Readable canonical engine | 26,952 | `f0bc01d4ebde79578248e1d210723bff6be0639e829c166d6204de02466c3e82` |
| Compact shipping C | 14,244 | `6fc93fc02e63749ae8864c1a32bbbd3ef327540753189dbd6d871b1d7c23e779` |
| Restored stdin native ELF | 26,464 | `3ecbded7c3df09fdbf2e85b6769595f023eaed4f2add807020f66270593afe5b` |
| Complete selected source executable | 5,955 | `ec4037167559bf2aeda349af6330d0ef83712305d6c3c6e30f09d7cf70c1af46` |

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

Shipping `uci` returns only `uciok`; `isready` returns `readyok`.
`position startpos [moves ...]` remains transactional. An own-side clock uses
the original formula/caps and minimum 1 ms, while clockless bare go uses the
fixed 1,000 ms default. Optional `stop`, `ucinewgame`, `infinite` and unknown
words are consumed without adding public controls. Next-go, position, quit and
EOF still settle the old search before state reuse or resource release. DEV
retains its stronger commands, identification, FEN and diagnostics.

The exact original selection is bound by final evidence index SHA-256
`71d1a8f86d09364fbe9f1f0a2138b5c87a8361a86b46e6756a182f754c9b9f9d`, producer
build `552db533349aa3f33fadeb7bfb3fe41ce6a02f91549788ceef1095ab038e63a1` and
separate C core/SIMD/context receipt
`2d1efcd44b98062f09d564d8ebbac828d25b9250a441cbfe25c67f053c9bebd3`.
Only hashes and scope metadata are stored here; none of those historical files
is opened by the maintained build or source proof. That prior qualification
includes exact source-bound optimized/sanitized PSQT parity over 369,255 boards
and 738,510 SIMD calls per build, positive production search consumption, and
nine direct actual-minimal-source context/PLY checks. Fresh generation/runtime
reports remain separate from that inherited coverage and from CI acceptance.
