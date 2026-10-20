# Maintained minimal A entry

`engine.c` is the readable canonical program for the selected minimal A entry.
It contains the development and shipping forms together. Edit this source when
changing the program; do not maintain the compact C or compressed launcher by
hand. This promotion changes source ownership and regeneration inputs, not the
search policy, runtime or compiler settings. The final promotion also incorporates
the already qualified two-guard shipping specialization described below.

The complete selected launcher is **5,207 bytes**, 1,111 bytes above 4,096. This
folder does not claim the 4 KiB target, a strength result or general target
portability. Its qualified environment is Ubuntu 24.04.4 x86-64, GCC 13.3.0,
binutils 2.42, glibc 2.39, Python 3.12.3 and xz 5.4.5. Python's LZMA encoder is
also an input to exact compressed bytes. Other environments fail the expected
hash checks rather than silently qualify a different entry.

## Fixed recipe

From the repository root on that Linux environment, or through WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-a/build.py --out /absolute/new/external-output --dev
```

The output must be outside any Git checkout and must not exist. `--dev` adds the
unchanged diagnostic form; it does not select another shipping profile. Workers
are fixed at 2, TT_BITS at 18, and PLY at 128. Both search workers and the input
thread exist at startup. Shipping has no resource options. The native command
is exactly `cc -Os -x c - -o x -s`. The complete file is a 75-byte shell launcher
plus an XZ stream: LZMA2 preset 9 extreme, lc=2, lp=0, pb=0, CRC64. Its Python
bootstrap restores the source, compiles it, removes its private directory and
executes the unlinked native image. Signal/child cleanup and file descriptor
execution are retained byte for byte.

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
| Readable engine.c | 25,131 | `321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d` |
| Compact shipping C | 11,148 | `5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7` |
| Stripped native ELF | 22,664 | `d39167146236aafde21b59439b853bd10561f04e9186c18b839c2f84f2e16e12` |
| Complete launcher | 5,207 | `085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36` |

The diagnostic C and ELF must also equal the previously qualified control:
`8a0985aad0b1514aa78a6aafc59c0fc1cc511d1b06a441bab91a404cdd98a477`
and `dad84ccaa35f6c9d7860b1bd39d283f8bdb7d5a1c74ec6c25615e443376974ce`.

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

The readable program is the exact final qualified preconditions source,
SHA `321ab861…12c6d`, derived from minimal-UCI v4 SHA `38d6c829…0a7b`.
That predecessor derives from maintained Tiny A and the selected tiny-search structural source
(`109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`)
followed by the already qualified minimal shipping UCI policy. It is an MIT
project implementation, with no external engine source copied. Historical
selection inputs are now fixed recipe data, not regeneration dependencies.

The only readable-code change from that 5,223-byte predecessor is wrapping two
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
not a safety claim for arbitrary raw boards or moves. Both guards remain in DEV,
whose compact source and native output are exactly unchanged. The inherited
nearby source comment about retaining the king-capture prohibition describes
that general/DEV admission; shipping instead relies on the stated legal-history
precondition. It remains verbatim to preserve the qualified readable source.

The source and selected shipping outputs are byte-identical to the final frozen
5,207-byte candidate. The recipe records its producer receipt hash
`59f2b8b30ca17d8e084474f1dff8b7effb1e177ebaa2fb3f9f69e09b6c27a9d1`
and final evidence index hash
`be24c6f166da35230f7ebbdff979979744c7cc49339927055894fe08b4ff9c8f`.
That qualification covered the generated legal graph and capacity argument,
actual DEV=0 O2/sanitizer/PLY forms, state/search/context contracts, and selected
native/whole-file runtime/image/protocol fences. Identity permits their reuse,
not a claim they were rerun by this builder. The recipe also retains the 5,223-byte
predecessor's producer/runtime receipt hashes, and that predecessor's complete
nine-file canonical source, Git archive/tree `d69a48ce01d96b7f6165f14078929a71d2384d66`,
builds and runtime receipts remain preserved outside Git. The old qualification
is not silently relabeled as a run of the new native image.
The current tracked stitch helper adds LF-aware assembly/metadata relative to
the historical snapshot; only its byte-identical `strip_dev_counters` function
is consumed here, and all final identity gates still apply. Fresh archive and
physical-run receipts distinguish new checks from that reused coverage. No
general rules suite, strength match, fair NPS study or many-core target campaign
is implied by this promotion.
