# Maintained minimal A entry

`engine.c` is the readable canonical program for the selected minimal A entry.
It contains the development and shipping forms together. Edit this source when
changing the program; do not maintain the compact C or compressed launcher by
hand. It incorporates qualified query/job ownership, the measured LZMA-alone
transport and startup-counter ownership source, followed by one fixed
shipping-only A31 spelling policy that preserves PLY uses, then the qualified
18-name storage spelling policy and declaration-bound automatic-name replay.
Search policy, compiler argv,
worker resources and the Python bootstrap's process/signal/cleanup logic remain unchanged.

The complete selected launcher is **4,846 bytes**, a 134-byte reduction from
4,980 and still 750 bytes above 4,096. This
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
startup-source diagnostic form; it does not select another shipping profile. Workers
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
order. Shipping then applies the owned ordinary `shipping_alpha.py` fixed
31-name map with all 95 token occurrences checked. PLY is protected and retains
all eight code uses; the final WORKERS/TT_BITS spelling stage has zero resource
occurrences. The subsequent `fixed_shipping_storage.py` stage applies the fixed
18-name storage map to this exact A31 output: 17 names have 87 occurrences,
`ready` is unused, and PLY retains all eight code uses. The final local
`shipping_scope.py` replays 70 AST-bound declarations at 274 exact physical
locations. Input/output SHA, each original occurrence and a byte inverse are
checked. It shortens source by 274 bytes to 9,910 bytes; aliases are unique
within functions and reused between functions. The normal build needs no
libclang, reference engine or experiment input. No identifier, compiler,
flag, compression or runtime search is run.
`bootstrap.py.in` preserves the selected bootstrap with only its source literal
replaced by one explicit marker; `launcher.sh` is its exact launcher prefix.

Eight repository helpers are needed: `engines/scripts/specialize.py`,
`minify.py`, `rename_c.py`, and `engines/compact/tiny-a/stitch.py` plus
`pack_stream.py`, the local `shipping_alpha.py`, and the ordinary shared
`engines/scripts/fixed_shipping_storage.py`, followed by the local
`shipping_scope.py`. Their relative paths and
LF-normalized SHA-256 values are
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
| Readable engine.c | 24,820 | `71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734` |
| Compact shipping C | 9,910 | `a3414baa5034a62067f74f7f8fff9a1578827f37e6ca59b0db8e5bc1968df312` |
| Stripped native ELF | 22,672 | `84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a` |
| Complete launcher | 4,846 | `1227e4ba99a986d52a33f6b901f3be117d1b522001f2f86f6da07e4c27a74c9d` |
| Decoded bootstrap | 10,900 | `d73d24f699811253492ad8bab152907835763a68d7a35962e83d14156840cb47` |

The diagnostic C and ELF must equal the explicitly admitted startup-source DEV:
`41ab9f0f5d28183b76833d038c40e0bb6a2ee6ef9303766c293dd577680a4c9c`
and `8733dbf0814a2c2545251f6e0e17d243ecfd41fce7853fb325ca9720fedd1102`.
The qualified startup experiment built shipping DEV=0 only. Before these new
literal expectations were written, its exact readable candidate was separately
generated and compiled twice with the existing DEV command. Both C (18,743 B)
and ELF (31,080 B) were byte-identical. The binding receipt
`af6889fb9009fe9cbd7c59361a005cf2a89f21274088eabb90c49570ec52d342`
pins the candidate equal to the startup diagnostic's frozen source and the raw
cost/body/phase/runtime receipts. This proves DEV generation/compilation, not a
new DEV startup diagnostic or engine execution. It deliberately differs from
the older 5,140-byte and earlier DEV identities; no expectation is learned or
automatically updated by the canonical builder.

## Fresh source archive and physical run

```sh
python3 -B engines/compact/tiny-entry-a/fresh.py --out /absolute/new/archive-proof
python3 -B /absolute/new/archive-proof/checkout-1/engines/compact/tiny-entry-a/verify.py \
  --build /absolute/new/archive-proof/build-1 --out /absolute/new/runtime-proof-1
python3 -B /absolute/new/archive-proof/checkout-2/engines/compact/tiny-entry-a/verify.py \
  --build /absolute/new/archive-proof/build-2 --out /absolute/new/runtime-proof-2
```

`fresh.py` names the complete source closure explicitly: this folder's original
nine files, the eight pinned build helpers (including local alpha, shared
storage and local scope policies) and the two pinned independent test helpers, totaling 19
ordinary files. The local
policy enters through `recipe.helper_sha256`; `fresh.py` is unchanged.
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

## Fixed A31 spelling policy

The local standalone helper embeds the qualified A-only policy JSON exactly,
SHA-256 `e1d5daf3636851711d08309b772edf7a3546bfffeb402d745d33eaaf80560244`.
Only the old 10,855-byte A shipping input and exact 24,820-byte canonical A
readable are admitted. The helper owns its fixed map, regexes, independent
opaque scanner and rewrite functions as ordinary source. The caller supplies
only its pinned lexer and canonical readable bytes; no experiment directory,
report, generated source, old executable, AF policy file or other engine is
read by the maintained build.

All 31 role-audited aliases retain the original fixed alias gaps. They must be
injective and fresh in raw and phase-two words of both the readable and actual
shipping source. Functions, global/static storage, API identifiers, macros,
directives and all names outside the exact allowlist remain protected. Both
the single-pass lexer edit and repeated replacement path must agree. An
independent scanner preserves exact directives, comments and quoted literals,
including literal prefixes and backslash-newline splicing. It rejects trigraph
spellings. Exact count/arithmetic gates require 31 used aliases, 95 edits,
249 source bytes saved, 432 directive bytes and 53 opaque regions. PLY is absent
from substitutions and remains eight code uses before and after the rewrite.
The sole 10,606-byte candidate SHA is literal; no expected value is refreshed.

The separate qualified A-only candidate keeps actual macro uses, unlike the
earlier joint AF A candidate that failed its strict raw full-PP inverse gate.
That older failure remains preserved; it is neither relabeled nor promoted.
The new A-only raw compiler-expanded source passes an alias-only inverse with
no whitespace normalization or numeric replacement, and the complete final
macro dumps are byte-identical. Its final resource dump retains PLY=128; the
configured readable WORKERS=2/TT_BITS=18/PLY=128 probe is separate. Those PP
checks are reused through exact source/candidate/full-native identity here,
rather than claimed as a fresh header-expansion campaign by the normal builder.
The qualified cost receipt is
`64c7908e6b560fa1f2c798c2f33de36a51af52a210d7f9f7db21a01cc2b1fe15`.
The new candidate's original actual quit/EOF two-session receipts are
`c7e8a9ef92184e6a30f5e8d7a7d5ebe067eeaade38ab6651539a5b77e0a549c7`
and `03fb9fb7211bf186b8eb58b03bb87762b4a30b5aa378056c30f12ca4b606ef39`.
The A31 FINAL index is
`5d0878cab7b9f7758bb12a11ea490c6e3fdc01f208aebdbdcb5536adcdf55f7b`.
These identities are metadata only, never regeneration inputs.

Each independent archive extraction makes two shipping and DEV generations,
with complete native ELF (including build ID and nonallocated sections) and
DEV bytes equal to the previous controls. The earlier A31 complete file was 57 bytes
smaller; its source was 249 bytes smaller. The final storage stage saves a
further 422 source bytes and 92 complete-file bytes. Readable source, search, startup, clock,
parser, resource profile, native compiler and LZMA-alone packaging are unchanged.
Broad core/rule/search/startup proofs are reused by those exact identities;
only the needed new selected-file image, clocks, quit and EOF checks are run.
Before editing, the old nine files, exact source archive and shipping/DEV
controls were verified and preserved outside Git. Promotion evidence and all
generated files also remain outside Git.

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

The readable program is the exact final qualified startup source,
SHA `71f9ff6c…a734`, derived from query/job-ownership `79284c72…b48ed`,
preconditions source `321ab861…12c6d`,
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

The earlier ownership source added the previously qualified query/job changes.
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
fixed recipe/template/prefix and then-five tracked helpers. The earlier A31
promotion added its local ordinary policy as a sixth helper; storage18 adds
the seventh, and fixed scope replay adds the eighth. There is no runtime
dependency on the composition folder or those historical artifacts.

The old 5,207-byte nine-file canonical, archive tree
`a6cb91a7c6441977c6525ebf279b6639d0163689` and receipts remain preserved outside
Git, as do the older 5,223-byte canonical/archive and all three composition
controls. Metadata retains the preconditions/earlier receipts and the transport
input-closure final receipt
`2a07487768738bb9cd87f24f27a0e41b084cce7dd12322d90435a2e5c4975219`.
The preserved old native images are not relabeled as the new ownership image.

The selected startup source makes exactly three further checked changes:
remove the separate `ready` counter and initialize `pending=WORKERS` before
thread creation; let each worker decrement pending once under the existing
mutex and broadcast `finished` on entry; and reuse existing `wait()` after all
creates succeed instead of a separate startup predicate/wait sequence. Startup
arrivals settle before input and before any job publishes its pending count.
An arrival is not a search completion and never calls `result()`. Creation
failure still bypasses startup wait and shuts down only the created threads;
the count for uncreated workers is not awaited. Shutdown and join-error policy
are unchanged; no cleanup guarantee after an injected join error is added.

There is an explicit private inactive-state difference: main's startup `wait()`
stores **`stopped=1` before the first GO**, instead of leaving its original zero.
Public GO already clears it before publishing work. A direct search consumer
that follows main-style startup but bypasses GO must clear it explicitly.
This is not claimed as identical arbitrary private-call behavior.

The final startup summary
`f09a0b388e6417f5e80964b39eac1b2341fb2809314a5e24ef8c82f918fb0f60`
binds the exact 24-file experiment, first-cost/reproduction receipts, source
segments, five controlled phase modes and actual two-wrapper/eighteen-epoch
receipt. Its 16,374-byte board/TT/search/think prefix is unchanged at
`9c0aba3b85cb8d36905c81d1bef5135722fcf71e4f7983374c7f1c7ae7a17f95`;
query/result, normal wait/GO/parser and main input/shutdown tails are also exact.
These boundaries support narrow old proof reuse rather than a fresh full
board/search/SAN campaign. The five modes are DEV=0 diagnostic interposition:
two successful early/late schedules observe pending zero and stopped one at
first input, while fail-0 and early/late fail-1 avoid waiting for uncreated
workers and observe created-thread joins before TT free. They are not shipping
native join interception, TSAN/SAN evidence or a scheduler/race proof.

The actual qualified startup whole-file receipt separately covers two sessions
and eighteen legal-root epochs, startup/image identity, next-GO/position fences
and physical quit/EOF. This canonical promotion reuses that exact shipping
source/artifact receipt and independently repeats only its own selected two
image/clock/quit/EOF sessions. The old 5,140-byte nine-file canonical, archive
tree `644e6f04289f9edc51ff0432e322f50a3dedaa07`, both shipping/DEV builds and all
older composition controls remain preserved outside Git before promotion.
Compared with 5,140, the actual startup complete file is 11 bytes smaller while
its restored native image is 8 bytes larger. Builder, fresh-archive driver,
selected verifier, helper versions, compiler, spellings and codec are unchanged.

The current tracked stitch helper adds LF-aware assembly/metadata relative to
the historical snapshot; only its byte-identical `strip_dev_counters` function
is consumed here, and all final identity gates still apply. Fresh archive and
physical-run receipts distinguish new checks from that reused coverage. No
general rules suite, strength match, fair NPS study or many-core target campaign
is implied by this promotion.

## Fixed storage stage and qualification reuse

The shared ordinary `fixed_shipping_storage.py` embeds the exact storage18
policy JSON with SHA-256
`e89afbf078f902a4cfc3c0ee8c1fba525966be76e4df14b18f50746c2d40cff3`.
It binds the current family, post-alpha shipping source and canonical readable
bytes before applying the same fixed name-to-alias decisions. It contains its
own pure lexical and independent opaque/rewrite logic. It reads no experiment,
report, other engine source or generated artifact. Reserved aliases from the
reviewed pair remain literal policy evidence; this build checks its own exact
canonical source, rather than claiming a fresh cross-engine scan.

The 18 decisions rename only the audited same-TU external objects, file-static
objects and block-static objects. Functions, types, Move, directive bytes,
strings, external ABI and all previous local alpha decisions remain unchanged.
All three shipping spelling stages are bypassed for DEV. Full source/candidate/native pins
are reviewed constants; a different input, occurrence inventory, opaque region,
resource use or complete ELF fails rather than learning a new expectation.

The qualified storage experiment FINAL44 index is
`2824e102ceb29316a522982fb8c249c0f8fd8588a2cfa0e4b6b4d5fb9649074c`;
its cost receipt is
`505932407b3b306c8a9122cf7da11f1200a75a4f39cb821101afffbca095106d`
and actual selected runtime receipt is
`304b37c55065752cb1c723ad73e9d713f6681c32fc8ad91616a2ac340afc7ea1`.
These are historical metadata, never normal regeneration inputs. Their strict
compiler-expanded inverse, final macro definitions and actual-header alias
freshness checks are reused by exact before/after source identity. Broad core
proofs are reused by the unchanged complete native ELF; DEV pins also remain
unchanged. The present fresh-source promotion checks regeneration separately
from each selected wrapper's actual image, stable startup TIDs, legal clocks,
finite bare go, physical quit/EOF and cleanup. It does not run new games,
benchmarks, compiler variants or a second policy.

Before promotion the original ten local source files and full named build/test
closure, old source archive, shipping and DEV controls were preserved outside
Git. Each fresh extraction contains the new shared helper and its own fixed
recipe, so historical reports or generated bytes cannot become its only input.

## Fixed scope replay and current selected verification

The exact AST-bound A map is
`c7c84366437df666fd353213242a3ae9e2e6e71c0914992b563a9012619241cf`.
The local ordinary helper embeds only its 70 declaration groups and 274
physical occurrences. It admits the qualified 10,184-byte post-storage input
`9e764bbbea91f198a4cb5aff62aae9f3007df5f715d4d8b8142e4795b5109d5a`
and requires the sole 9,910-byte output. It verifies exact inverse bytes.
Globals, static storage, functions, types, fields, header/macro identifiers,
string bytes and external ABI are unchanged. Its normal generation imports
only standard-library hashing and does not read the experimental analyzer,
map JSON, reports, external toolchain or generated old files.

This is the separately measured locals-only A policy with the original ALONE
codec and unchanged 77-byte launcher. It does not include private-function
names or another codec composition. Full native ELF including all metadata
remains exactly `84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a`;
canonical castling/rules/search/startup bodies and both DEV pins are unchanged.
Core and original binding proofs are reused through these exact identities.
The first A row's source/native/whole receipt is
`7f38a9bca532519fd68efbdb8580999c1ad4fa201baf7564d8d7b76aad816157`.
Its overall report retains a B AST rejection; only its completed A row is
reused here. That historical failure is not relabeled as a successful campaign.

Before mutation, the original normal18 ordinary source closure and old pins
were preserved outside Git. This promotion ran one normal build, with two
independent shipping/DEV generations and complete native/whole comparisons,
then only the unchanged A selected verifier's quit and EOF sessions: eight
legal GO epochs, exact restored image, three stable startup TIDs, private-path
removal, process absence and output-reader completion. It did not run a fresh
archive extraction, new AST analysis, DEV engine, broad core matrix, game or
benchmark. The unchanged `fresh.py` can close the new ordinary19 source set;
that capability is separate from this promotion's actually executed checks.

Production build receipt: `2ff77ccd43d3df223a2926a46cef5ca82319b97beb2dc82de4214bf769f69d34`.
Selected runtime receipt: `399ca285479bc1e02b026656b8b274d1f1c8b148c0033a7d25e742b6fec23ef5`.
The production recipe is preserved externally before adding only the later
qualification metadata. Existing wrapper/core receipts remain historical;
they are not relabeled as executions of the 4,846-byte whole. Cancellation
causality and standard-descriptor observation remain unproven/unobserved as
recorded. Compiler signal/group/tempfile/fd-exec behavior is unchanged; selected
successful startup and leader reaping do not prove a general descendant-group
lifetime contract. The previously recorded bootstrap limitation remains.
