# Maintained minimal F entry

`engine.c` is the readable canonical source of the selected **5,051-byte** F
entry. It contains shipping and diagnostic forms together. This version adopts
one qualified query/reset/startup composition after F5083. The whole file is
32 bytes smaller and remains **955 bytes above 4,096**. It does not establish
4 KiB eligibility, strength, fair NPS or general target portability.

The production core keeps full-depth MTD(f), integer unit windows, stable
leaves, exact-horizon/context-compatible coherent full-key single-bound TT
entries, retained lower/upper intervals, attaining root witnesses, completed
iteration retention and learning. The search prefix and MTD driver after the
entry reset are byte-identical to the old source. The new native is a different
image; it is not qualified through old full-native equality.

The fixed exact-byte target is Linux x86-64, Ubuntu 24.04.4, GCC 13.3.0,
binutils 2.42, glibc 2.39, Python 3.12.3 and xz 5.4.5, including WSL Ubuntu.
Other compiler/encoder outputs fail reviewed literal expectations. A build
never discovers or refreshes its own expected hashes.

## Fixed source recipe

```sh
python3 -B engines/compact/tiny-entry-f/build.py --out /absolute/new/external-output --dev
```

The output must be new and outside Git. The fixed profile has two search
workers plus the input thread, TT_BITS=18 and PLY=128. Shipping has no resource
options. `--dev` adds the separately admitted new candidate diagnostic C/ELF;
it does not choose another shipping profile or execute a DEV engine.

The builder performs no structural source transform. Its canonical input
already contains the seven fixed changes of the qualified composition. Each
of two independent attempts follows this sequence:

1. Specialize with the original `-std=c11 -Os -pthread -DWORKERS=2
   -DTT_BITS=18 -DPLY=128` and explicit DEV value, then lexically compact.
2. DEV stops source processing here. Shipping uses the unchanged strict
   beta-only counter-removal schema: one no-op definition, three fixed
   conditional calls and nine fixed unconditional calls, with no PVS calls.
3. Require resource identifier counts WORKERS=6, TT_BITS=3, PLY=8, then apply
   the original literal values 2/18/128 and the same 34 function spellings.
4. The local `shipping_alpha.py` applies the same 73-name map to exactly
   12,395 bytes (`ae4b81bf9a29e43efea3fe63c3ed733d2482546de3704e932ad61328fe68cc7b`).
   Its 509 occurrences save 1,486 bytes, giving 10,909 bytes with SHA-256
   `69ee88c2353ae8579e6da02ac06ec2b408812c29bb4a40684d59b9f02bed14ad`.
5. The local `shipping_storage.py` applies the same 18-name storage map.
   Seventeen names have 89 occurrences; the fixed `ready` alias has zero use.
   It saves 432 bytes and produces the exact 10,477-byte selected source.
6. Compile through stdin with the unchanged command
   `cc -Os -pthread -x c - -o x -s`, then package the selected source literal.

Both local spelling helpers bind the exact new readable, stage input/output,
counts, opaque/directive partitions and arithmetic. They embed the new domain
JSON SHA-256 `749133a23382dbaaf74fdd46e80d3b3c963688430502e14e84d0d63832870a04`.
The original 73-name policy is
`4bf1b189e9073aa994c29c07f64bcf05b1b3e749a0a172150cac68c1971d7d92`;
the original 18-name policy is
`e89afbf078f902a4cfc3c0ee8c1fba525966be76e4df14b18f50746c2d40cff3`.
No pair, resource value, function spelling, flag or codec is searched.

The local storage helper copies the original generic lexer/opaque/rewrite
function AST and the literal 592-word readable reservation union. It admits
only the new F domain and checks new canonical freshness without reading
another engine. The shared `fixed_shipping_storage.py` remains unchanged and
is no longer a normal F build input. DEV bypasses both local spelling stages.

The six pinned build helpers are `engines/scripts/specialize.py`, `minify.py`,
`rename_c.py`, `engines/compact/tiny-a/pack_stream.py`, and this folder's
`shipping_alpha.py` and `shipping_storage.py`. Their relative paths and
LF-normalized hashes are literal recipe inputs. The builder copies and checks
them before importing from its external output. They use only Python standard
libraries and read no experiment, report, generated source, old executable or
other family as a normal generation input. CRLF normalization is explicit;
lone CR fails. The local `.gitattributes` keeps this source folder LF.

The beta-only counter schema is unchanged: conditional `hits`, `qs`,
`corr_uses`, then unconditional `ply_aborts`, `hist_updates`, `cont_updates`,
`corr_updates`, `f_probes`, `f_lower`, `f_upper`, `f_converged`, `f_conflicts`.
Exactly 12 calls and the no-op definition are removed. Any residual `COUNT(`
or unexpected schema fails. The old shared F overlay is not consumed.

## Fixed compiler and transport

The shipping command remains `cc -Os -pthread -x c - -o x -s`. The DEV command
is unchanged: `cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DPLY=128
-DDEV=1 -x c - -o x`. The canonical bootstrap contains the same shipping argv.
The original template, 75-byte shell prefix and XZ/LZMA2 stream remain fixed:
preset 9 extreme, lc=2/lp=0/pb=0, CRC64. `bootstrap.py.in` substitutes only its
source-literal marker; `launcher.sh` uses `tail -c+76` and `xz -dc`.

Compiler signal-mask publication, private TMPDIR/cwd, process-group cleanup,
file opening, private-directory removal and fd execution are unchanged. Engine
argv and original environment remain the old values. Successful startup and
selected image checks are not a general compiler-descendant lifetime proof;
the separately recorded bootstrap static audit is not changed by this source
promotion.

| Exact output | Bytes | SHA-256 |
| --- | ---: | --- |
| Readable engine.c | 25,755 | `ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd` |
| Compact shipping C | 10,477 | `c63a450245ff4ca703a5abe2dc75d840c7c7e936bb2a30a726c30014e3a92e90` |
| Restored stdin native ELF | 22,672 | `757b9a14cd5174dad55754196cce098fd89018a8b0d7adcf08bcddb2e1fc092b` |
| Complete launcher | 5,051 | `ad4030ad32af47469ca067e4f10c4b60103eddcc6afdfefd22dedea1269052ce` |
| Decoded bootstrap | 11,476 | `3a6dc4c7c77c77b48f4b020cda1a4397af22eb2cdea97447bf97d7bae8a29162` |
| New candidate DEV C | 19,513 | `84fbc9b3651494ce0ebabdc25b9a1fa7b3a334fa7394eee2631581682a804b58` |
| New candidate DEV ELF | 26,984 | `6eb28892842bef969edff9295aae74b7edd71d61eb39ac01236f2adcd4785340` |

The candidate DEV was not built by the first-cost/proof experiments. Before
these literals were written, the exact new readable was independently
specialized, compacted and compiled twice with the original DEV command.
Both full outputs matched; the binding receipt is
`c05ff227901dbb01baa7c7527bd02ab123a4fc312539bc644a9c3da4c7dea04d`.
No counter strip or shipping spelling stage was applied. These are new DEV
identities, deliberately different from F5083; no old DEV identity or new DEV
engine execution is claimed. The builder's `diagnostic_exact_control` field
means equality to these explicit candidate diagnostic pins.

## Source ownership and private differences

A single nullable-text query now serves fallback and position replay. It
returns its already-made legal child to the caller, removing replay's second
`make`. Distinct input/output boards are required and failure scratch is
unusable. Replay commits only after the whole move history succeeds. Fallback
also performs the existing bounded text conversion; equal CPU work is not
claimed.

Per-job reset belongs to `think` entry: it clears best with nodes/depth/score.
GO no longer duplicates worker resets. Startup uses `pending=WORKERS`, worker
entry decrements it under the old mutex and the original wait supplies the
arrival barrier. Partial creation still skips the wait and joins only created
workers. Startup does not call result.

The two qualified private differences are pre-first-GO stopped=1 and direct
think clearing a caller-preseeded best. GO clears stopped before publication.
Existing shutdown/join error behavior is not strengthened. Board rules, TT,
MTD(f), last-completed publication and minimum shipping UCI remain unchanged.
This structural candidate is not equated with F5083's old complete native.

## Closed source and selected physical verification

```sh
python3 -B engines/compact/tiny-entry-f/fresh.py --out /absolute/new/source-proof
python3 -B /absolute/new/source-proof/checkout-1/engines/compact/tiny-entry-f/verify.py \
  --build /absolute/new/source-proof/build-1 --out /absolute/new/runtime-proof-1
python3 -B /absolute/new/source-proof/checkout-2/engines/compact/tiny-entry-f/verify.py \
  --build /absolute/new/source-proof/build-2 --out /absolute/new/runtime-proof-2
```

The unchanged `fresh.py` names LOCAL9, six recipe helpers and two independent
test helpers: **17** ordinary files. Local storage replaces one shared helper
path; no artificial extra file is added. The source archive checks regular
members, raw/LF hashes and two independent extractions. Each archived builder
makes two shipping/DEV attempts and compares full source/native/whole/bootstrap
and diagnostic tuples. All reports, source archives, compiler outputs and
intermediates stay outside Git. An isolated archive is not a project commit.

The unchanged selected verifier reads explicit new recipe pins and runs only
quit and EOF sessions. From each of the two extracted source trees it checks
the actual restored `/proc` image, removed private path, no current compiler
children, three stable startup TIDs, legal white/black zero clocks and finite
bare go, then active-search physical quit/EOF and output-reader termination.
Four new wrapper sessions are sufficient for this promotion. Cancellation
causality remains unproven. No generic infinite/stop contract, new game,
benchmark or broad old engine matrix is added.

## Qualification and predecessor boundary

The qualified F composition proof61 summary is
`eed7014b750abfdd19381be83091ecf7ede32e60973228dc6b548ed87153a4f0`.
Its fresh F query, startup, epoch, MTD and selected-wrapper executions are used
through exact candidate/source/native/whole identities. Original A/C fixture
sources are historical design inputs, not reused executions. The historical
malformed-query-fixture failure remains recorded rather than converted to a
candidate failure or silently removed.

First cost: `c9b2cbb83662610965b9ccd1ebc3935f73db605ec5853775836d5abd3c219313`.
Query: `5667f5ff42288da513bdf27b6cfc7a35846ccc1b8871a5d62af886bf23c67d16`.
Startup: `7cfdd6489ea3771502cef8ffab72acae5b857494cfd1e647548681c06690a719`.
Epoch: `026a8dc2cff7dea559df06e8e5e43b656c6d49d52468430d665011073bad421c`.
MTD: `89b904412a091b7c26d793a460e3a7f3e4c52e66b69800b33e181bbf0a237302`.
Original selected-verifier receipt:
`e595137d5aaa03394dd1f1618eb36896fb40167e4cd9b6bd2ec48843e8b4dc49`.
These are historical metadata, not regeneration inputs or new executions.
The exact candidate's PP inverse and final raw-macro multiplicity evidence are
also reused by exact stage identities; no new header-expansion campaign is
claimed by the normal builder.

The previous F5083 normal17 raw source, exact source archive, shipping/DEV
outputs and selected runtime receipts were preserved before mutation. Their
native was `ef10962ff16e5158e0cb18cbf96b944404bd1c4db301bfbb47a0faed33466c22`
and their DEV source/native were `9528b0e97f71d2d07d60a63956fc19a9156f778b30088b34f62e4eb445260ece`
and `bd71ff07625fa9891a4b4ef79c50b5215fa4169f18d83f15d9378fe833872a2d`.
All earlier beta-only, alpha73 and storage18 qualified receipts remain in the
recipe's predecessor metadata and external preserved source. The new normal
build never reads those reports, old executables or experimental folders.
