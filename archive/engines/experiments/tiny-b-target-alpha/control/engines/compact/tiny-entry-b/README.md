# Maintained minimal B entry

`engine.c` is the readable canonical B program, including DEV and shipping
forms. It is the exact qualified minimal-UCI portfolio B source, not generated
compact C maintained by hand. This folder promotes the existing program and
fixed recipe; it changes no algorithm, protocol, resource, compiler or codec
policy. It is the repository's MIT implementation; no external engine source
is copied.

The selected complete file is **6,219 bytes**, 2,123 bytes above 4,096. This is
not a 4 KiB, strength, scaling or general portability claim. The qualified
domain is Linux x86-64 on Ubuntu 24.04.4, GCC 13.3.0, binutils 2.42, glibc 2.39,
Python 3.12.3 and xz 5.4.5. Python's linked LZMA encoder also affects exact
compressed bytes. Other environments must pass the same exact identity gates;
the builder does not silently accept a different output.

## Fixed build and identities

From a normal checkout on that Linux environment, including WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-b/build.py --out /absolute/new/external-build --dev
```

Outputs must be new absolute paths outside any Git checkout. Workers are fixed
at 2, TT_BITS at 18, and PLY at 128. `--dev` additionally builds the unchanged
diagnostic form; it does not select another shipping configuration. The actual
compiler-stdin command is exactly:

```sh
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

This is B's selected unstripped command, not A's shorter stripped command. The
restored-native ELF is an explicit identity class; historical file-compiled
ELFs must not be substituted for it. DEV uses the same argument list with
`-DDEV=1`. The complete entry uses the selected 75-byte shell launcher and XZ
LZMA2 preset 9 extreme, lc=3/lp=0/pb=2, CRC64. These are B's selected parameters,
not A/F's lc=2/lp=0/pb=0. No compiler, spelling or compression search is run.

Four tracked build helpers are needed: `engines/scripts/specialize.py`,
`minify.py`, `engines/compact/tiny-b/generate.py`, and
`engines/compact/tiny-a/pack_stream.py`. Their complete LF-normalized hashes are
pinned in `recipe.json`. Only `strip_counters()` and its local replacement helper
are consumed from the B generator module. Its historical overlay/base-source
graph is not executed or read: the maintained canonical combined program is
already in `engine.c`. After preprocessing and lexical compaction, the exact
declared 12 no-op shipping counter sites are removed. There are no identifier,
resource-token or function-name substitutions in B's selected pipeline.

The builder copies and checks its local inputs and four helpers before importing
the external copies. It reads no historical experiment folder, report, executable,
dependency tree or network resource. `bootstrap.py.in` is the exact selected
bootstrap with only the compiler-source literal replaced by an explicit marker;
`launcher.sh` is its exact shell prefix. Runtime signal/process-group handling,
unlinked-file execution and cleanup remain unchanged.

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| Readable engine.c | 28,953 | `1f879828346dfbc6023f6abfbbf1e1d2062e8e2dc0e9919aade254ba7a0a97f6` |
| Compact shipping C | 15,566 | `eea1fe5f60c56aa90d2d51f3fa5a1aa56a63318527943500aa02d0105668f910` |
| Restored native ELF | 26,592 | `221a865e2712cb3e704128e0ae8353edd358343f564fe53093040f6515d522ec` |
| Complete launcher | 6,219 | `01261167253dd89a0e2d88aded2ee493fc0ffaec34cd2322459ddbc515f8aefd` |
| Bootstrap | — | `a4b430323614856d68fd59742c25d772459cc8de6cac601848f709dc67ce7c37` |

The selected portfolio DEV compact C and restored ELF must remain exactly
`31ef1cb522371a0094effb098c8ea9c0a78ff800c01da9eef5087c5b43e18ec2`
and `9e5ac53ca94cf36e6ac43632d2e507598deb516e40405bafa6bd874e56069c30`.
These are the matched portfolio DEV controls; no historical file-compiled DEV
image is relabeled as this compiler-stdin image.

Every build independently preprocesses, compacts, compiles and packages twice,
then requires all expected hashes and direct complete-byte equality. Optional
DEV generation/compilation also repeats twice. Raw used inputs, compiler stderr,
preprocessed/compact C, bootstrap, native ELF, launcher and `build.json` stay in
the external output. Reports remain incomplete on failure. CRLF checkouts are
explicitly normalized to LF; lone CR fails. Local `.gitattributes` keeps all nine
entry sources LF in Git.

## Fresh Git-source and actual runtime binding

```sh
python3 -B engines/compact/tiny-entry-b/fresh.py --out /absolute/new/archive-proof
python3 -B /absolute/new/archive-proof/checkout-1/engines/compact/tiny-entry-b/verify.py \
  --build /absolute/new/archive-proof/build-1 --out /absolute/new/runtime-proof
```

`fresh.py` names a closed set of **15 files**: this folder's nine source files,
the four pinned build helpers and `engines/tests/{verify.py,chess_oracle.py}`.
It preserves raw inputs and hashes, copies LF-normalized inputs into a new local
Git repository with no remote or commits, writes a tree and archives it. The
project checkout's index is never used. It admits only the named regular files
and directory entries with safe archive paths. Two separate fresh extractions
each invoke their own extracted builder with `--dev`, each doing two independent
attempts; shipping C/native/whole/bootstrap and DEV C/native are compared across
both extractions. `fresh.json`, raw inputs, source.tar and tree hash preserve the
proof. An uncommitted isolated tree is source evidence, not project HEAD or CI
success; after integration the same named ordinary files work from a checkout.

`verify.py` SHA-pins and copies the two tracked independent black-box helpers.
It checks the selected source/native/whole identities, launches only the actual
whole file twice, and verifies the fixed three TIDs before UCI input, the exact
restored image through `/proc`, the removed private directory and no live helper
child. It checks legal white/black zero-clock moves, finite bare `go`, and an
observably active clocked search followed by quit and EOF in separate sessions.
Each final epoch must emit one legal bestmove, reach process wait and reader EOF,
and leave no `/proc` entry. CPU activity is process-level evidence, not proof of
cancellation causality or a performance measurement.

## Preserved engine and reused qualification

B keeps mailbox plus occupied/piece bitboards, shared attack logic, legal SEE
with pin/king/EP/promotion handling and cancellation, qualified single singular
extension with excluded-search learning/TT boundaries, PVS, check-aware QS,
incremental HCE, history, continuation and learned correction. All four
promotions, castling, canonical EP, FIDE third repetition, halfmove/dead-position
handling, reversible-context full-key coherent locked TT and PLY abort with a
retained legal witness remain in the actual source. Search workers are created
at startup; completion and storage-reuse fences remain unchanged.

The selected minimal shipping protocol returns `uciok` and `readyok`, accepts
transactional `position startpos [moves ...]`, finite `go` with the qualified
own-side clock policy, and quit/EOF. `stop` and `ucinewgame` are consumed without
cancellation, wait or TT clearing; `infinite` is an ignored shipping token, so
clockless go has the finite 1,000 ms default. Subsequent go/position and quit/EOF
still cancel and physically settle old epochs before reuse. DEV retains the
stronger identification/parser/diagnostics. No old optional-stop result is
reused as proof of this deliberately narrower shipping policy.

`recipe.json` records metadata hashes of the original family producer
`b94f663777d1219cad9827bd7322cd3a0872f5fcac2a82efb8d4df81335fef90`,
portfolio freeze receipt
`71d1a8f86d09364fbe9f1f0a2138b5c87a8361a86b46e6756a182f754c9b9f9d`,
actual portfolio runtime receipt
`6f26a3c46bff4d9b3dfe531eaac9a43b9a02eff52d5bda1c1bc2ca9624a84b09`
and separate B core receipt
`a2965d8f57d36187cb33a7201467271f66f2dae42c8c42b55c518272eea5e951`.
These are provenance, not builder inputs or executable prerequisites.

The historical qualification binds actual SEE/singular optimized/sanitized
positive controls, exact unchanged core bodies and matched DEV, 15 modeled
shipping-policy cases and actual selected whole-file sessions. Separate direct
minimal-source checks bound TT halfmove/path separation, scores `[0,916]`, EP
selection/correction exclusion and PLY4 retained-witness interruption. Exact
source/artifact identity permits that coverage to be reused; this builder does
not claim to rerun it. The new archive and selected-image lifecycle receipts are
separate fresh evidence. No broad engine matrix, game-strength test, fair NPS,
many-core campaign or training is implied by canonical promotion.
