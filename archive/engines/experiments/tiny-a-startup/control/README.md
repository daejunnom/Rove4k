# Maintained minimal A entry

`engine.c` is the readable canonical program for the selected minimal A entry.
It contains the development and shipping forms together. Edit this source when
changing the program; do not maintain the compact C or compressed launcher by
hand. It incorporates the qualified query/job-ownership source and one measured
LZMA-alone transport composition. Search policy, compiler argv, worker resources
and the Python bootstrap's process/signal/cleanup logic remain unchanged.

The complete selected launcher is **5,140 bytes**, 1,044 bytes above 4,096. This
folder does not claim the 4 KiB target, a strength result or general target
portability. Its qualified environment is Ubuntu 24.04.4 x86-64, GCC 13.3.0,
binutils 2.42, glibc 2.39, Python 3.12.3 and xz/lzma 5.4.5. Python's linked LZMA encoder is
also an input to exact compressed bytes. Other environments fail the expected
hash checks rather than silently qualify a different entry.

## Fixed recipe

From the repository root on that Linux environment, or through WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-a/build.py --out /absolute/new/external-output --dev
```

The output must be outside any Git checkout and must not exist. `--dev` adds the
qualified ownership-source diagnostic form; it does not select another shipping profile. Workers
are fixed at 2, TT_BITS at 18, and PLY at 128. Both search workers and the input
thread exist at startup. Shipping has no resource options. The native command
is exactly `cc -Os -x c - -o x -s`. The complete file is a 77-byte shell launcher
plus LZMA-alone: LZMA1 preset 9 extreme, lc=2, lp=0, pb=0, CHECK_NONE, 64MiB
dictionary and an end-marked unknown-size stream. Its Python
bootstrap restores the source, compiles it, removes its private directory and
executes the unlinked native image. Signal/child cleanup and file descriptor
execution are retained byte for byte.

The launcher uses `lzma -dc` and addresses byte 78. The complete 13-byte ALONE
header is `0200000004ffffffffffffffff`; all header and coded termination bytes
count. LZMA-alone has no XZ CRC64 field; no equivalent corruption-detection
claim is made. The fixed builder checks the header, strict Python decode with
true EOF/no trailing bytes, and independent `lzma -dc` output before packaging.

`recipe.json` stores the actual selected decisions: 45 accepted token mappings,
the fixed resource substitutions, and 31 function spellings, all in application
order. No identifier, compiler, flag, compression or runtime search is run.
`bootstrap.py.in` preserves the selected bootstrap with only its source literal
replaced by one explicit marker; `launcher.sh` is its exact launcher prefix.

Five repository helpers are needed: `engines/scripts/specialize.py`,
`minify.py`, `rename_c.py`, and `engines/compact/tiny-a/stitch.py` plus
`pack_stream.py`. Their relative paths and LF-normalized SHA-256 values are
pinned in the recipe. The builder copies and checks these files before importing
them from its external output, and uses only Python standard libraries. It does
not read an old experiment directory, report, build.json, executable, dependency
tree or network resource. CRLF checkouts normalize to LF; lone CR is rejected.
This folder's `.gitattributes` keeps its canonical source and recipe LF in Git.

Each build independently preprocesses, compacts, compiles and packages twice,
checks every expected identity and compares the complete outputs. All inputs,
compiler stderr, intermediate C, bootstrap, ELF, launcher and `build.json` remain
in the external output. An incomplete report remains incomplete on failure.

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| Readable engine.c | 24,921 | `79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed` |
| Compact shipping C | 10,958 | `5ed00fd936cf6228ec7f73d6c1fddd0f18bfe899aff82b5aa695732240079b59` |
| Stripped native ELF | 22,664 | `6d9a3c192078f22914e17a0332ef2f0dbd134050833c1fceb0ccb221ecba34e2` |
| Complete launcher | 5,140 | `75dc3d610d39bbc0702c6eda219fa0acb4d167c40d3c78e241cf867a33e5a4e7` |

The diagnostic C and ELF must equal the qualified ownership candidate:
`60e40bfa24ae06afdafbdfffacda2576b7056d22dffb12e70a22d0d8c3142942`
and `ff29baa1648f68812424f6e1f718f5e44b9037813e74dc2492a3e4425c88cb0f`.
These deliberately differ from the older 5,207-byte entry's DEV identities;
the new helper/job boundary is not disguised as an unchanged general DEV image.

## Fresh source archive and physical run

```sh
python3 -B engines/compact/tiny-entry-a/fresh.py --out /absolute/new/archive-proof
python3 -B /absolute/new/archive-proof/checkout-1/engines/compact/tiny-entry-a/verify.py \
  --build /absolute/new/archive-proof/build-1 --out /absolute/new/runtime-proof
```

`fresh.py` names the complete source closure explicitly: this folder's nine
files, the five pinned build helpers and the two pinned independent test helpers.
It preserves raw input bytes, copies their explicit LF-normalized forms into a separate local Git repository with no
remote or commits, writes a tree and archives that tree. It never changes the
project checkout's index. It validates archive paths/types, extracts into two
separate source directories, invokes each extracted builder and requires the
same shipping C, ELF, complete file, bootstrap and diagnostic outputs. Each
builder in turn performs two independent attempts. `fresh.json`, `source.tar`,
the source tree hash and raw/LF input hashes bind this proof. Before integration
this is explicitly an uncommitted Git source tree, not a claim about project
HEAD; the same named sources become ordinary checkout inputs after integration.

`verify.py` uses copies of two SHA-pinned tracked black-box helpers. It checks
the selected whole-file/native/source identity before launching the actual
whole file twice. It observes three stable startup TIDs before UCI input, the
restored native image through `/proc`, absence of the private restoration
directory and live compiler helpers, legal white/black zero-clock results, bare
finite `go`, and active-search quit/EOF. Each closing epoch must emit one legal
bestmove and reach process wait, absent `/proc` entry and reader EOF. This is
bounded lifecycle evidence, not a performance benchmark; CPU activity does not
establish that cancellation caused completion.

## Program and proof boundary

The core retains all four promotions, castling, canonical en passant, legal move
filtering, FIDE third repetition, halfmove/dead-position handling, incremental
evaluation, coherent full-key locked TT, PVS with quiescence, learned history,
continuation and correction, startup loose SMP, and completed-result fences.
The shipping minimum is intentional: `uci` returns `uciok`, `isready` returns
`readyok`, `position startpos [moves ...]` replays transactionally, `go` is finite
with the selected own-clock budgeting, and `quit`/EOF physically join workers.
`stop`, `ucinewgame`, `infinite` and unsupported words are consumed without adding
public controls. A subsequent `go` or `position` still cancels and waits for the
old epoch before shared state reuse. DEV keeps the richer parser and diagnostics.

The readable program is the exact final qualified query/job-ownership source,
SHA `79284c72…b48ed`, derived from preconditions source `321ab861…12c6d`,
minimal-UCI v4 `38d6c829…0a7b`, maintained Tiny A and the selected tiny-search structural source
(`109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`)
followed by the already qualified minimal shipping UCI policy. It is an MIT
project implementation, with no external engine source copied. Historical
selection inputs are now fixed recipe data, not regeneration dependencies.

The earlier 5,223-to-5,207 source specialization wrapped two
guards in `#if DEV`: rejecting a captured king in `make`, and checking move-list
overflow in `add`. Shipping calls `make` only for a move emitted by the production
generator, and admits only legal histories from startpos. A legal predecessor
leaves its own king unattacked by the next side, so the next generated move
cannot capture that king. Each side retains at most 16 pieces, including one
king; one king emits at most 10 pseudo moves and each other piece at most 27,
including promotion expansion: `10 + 15*27 = 415 < MOVES (512)`. No shipping FEN,
raw TT move or direct arbitrary move reaches `make`. Own-king safety, castle
gates, EP normalization, transactional replay and all TT/pool/clock fences
remain unchanged. These are explicit ingress and generated-move preconditions,
not a safety claim for arbitrary raw boards or moves. Both guards remain in DEV. The inherited
nearby source comment about retaining the king-capture prohibition describes
that general/DEV admission; shipping instead relies on the stated legal-history
precondition. It remains verbatim to preserve the qualified readable source.

The selected source adds exactly the previously qualified ownership changes.
A null text pointer asks the existing generated-move/text/strcmp query for the
first legal move. A successful query returns its already-made child in separate
caller-owned Board scratch; replay reuses it and commits globals only after the
whole move history succeeds. Failed-query scratch is discarded; input/output
aliasing is outside the private helper contract. Per-job best/nodes/depth/score
reset belongs to each `think` entry before any iteration, including a stopped
or zero-iteration job, rather than a redundant GO loop. Learned heuristics and
worker identity persist. Direct calls with a preseeded best now clear it; this
is an explicit private contract change, while production GO already cleared it.

The board/search body is unchanged at SHA
`557f9e15c072410fc16c7f3aad8320e904e02574b99b1c625a9047c620b85b57`.
The qualified ownership summary
`671717f28b8efdf6417c2d660aac1a2a9bde0dff3661cb22caff3b4b78090407`
binds control O2, candidate O2 and candidate ASan/UBSan query/reset checks,
122 legal coordinate queries, 192 invalid tokens, 14 replay transactions,
history capacity and explicit production/direct-think differences. Its separate
actual original-XZ two-session/eight-epoch receipt proves repeated white/black
job fences and physical exit. Those source-boundary proofs are reused; they
are not relabeled as newly executed algorithm tests or the new ALONE process.

One fixed composition was then measured, without adding independent savings:

| Complete control or candidate | Bytes | Actual identity |
| --- | ---: | --- |
| Original source + XZ | 5,207 | `085fcf6b…33e36` |
| Original source + ALONE | 5,163 | `4f156219…d1f8c` |
| Ownership source + XZ | 5,183 | `9a4911a0…cfa7b` |
| Ownership source + ALONE | **5,140** | `75dc3d61…e5a4e7` |

The actual composition is 23 bytes below 5,163 and 43 below 5,183. It is not the
5,139-byte sum of the separate savings. Its first-cost receipt is
`e64bb57448049fe95d63859ebb4a04cdac2fd4ab1783f2154a12bcace6686fe3`.
`engines/experiments/tiny-a-compose/build.py` preserves and hash-admits all three
raw controls, reproduces and strictly decodes each twice, then independently
encodes/decodes the one combined whole file twice. It runs no engine/compiler.
That cost-only producer deliberately uses immutable external control artifacts;
the canonical builder here instead reads only the maintained ordinary source,
fixed recipe/template/prefix and five tracked helpers. There is no runtime
dependency on the composition folder or those historical artifacts.

The old 5,207-byte nine-file canonical, archive tree
`a6cb91a7c6441977c6525ebf279b6639d0163689` and receipts remain preserved outside
Git, as do the older 5,223-byte canonical/archive and all three composition
controls. Metadata retains the preconditions/earlier receipts and the transport
input-closure final receipt
`2a07487768738bb9cd87f24f27a0e41b084cce7dd12322d90435a2e5c4975219`.
The preserved old native images are not relabeled as the new ownership image.
The current tracked stitch helper adds LF-aware assembly/metadata relative to
the historical snapshot; only its byte-identical `strip_dev_counters` function
is consumed here, and all final identity gates still apply. Fresh archive and
physical-run receipts distinguish new checks from that reused coverage. No
general rules suite, strength match, fair NPS study or many-core target campaign
is implied by this promotion.
