# Maintained selected C D own-ELF entry

The readable native program lives in `native/`; its project-owned restoring
loader, linker and build-time codec live in `loader/`. `recipe.json` fixes
source hashes, compiler/linker order, resources, the finite shipping policy,
admitted layouts and exact native/whole/audit identities. Edit readable source
deliberately; generated native images and payloads do not belong in this folder.

This selection promotes the qualified layout-plus-phase D source and images
over the previous 7,540/7,800 B finite selection. Exactly one Board declaration
moves unchanged metadata before the mailbox, and one eight-argument search
fragment shares its existing PVS retries through one phase loop. Board fields
and logical representation are unchanged. Six other native files, raw OS/pool
ownership, finite runtime, loader/codec, flags and resources remain unchanged.
Scalar now has an explicitly qualified two-page RX class; HQ retains three RX
pages. Each exact native identity has its own literal class. There is no
optimizer, flag/codec/preset sweep, generic ELF admission or external engine
source. The root MIT license applies.

| Fixed profile | Native ELF | Complete own-ELF | Complete SHA-256 |
| --- | ---: | ---: | --- |
| Scalar | 8,124 B | **7,478 B** | `d4f2ba718c5e9391708c86468416338f78b6134d1f017267c6c34add187381f2` |
| HQ | 8,512 B | **7,718 B** | `3bb8a6a97a27a77508848ab9bd388a4802e07f8d8ff0e37b536176423aa7028f` |

Both exceed 4,096 bytes by 3,382/3,622 bytes. The actual combined native files
save 224 B each and complete files save 62/82 B against that finite control;
separate experiment savings are not added as estimates. This folder makes no event
eligibility, playing-strength, throughput, scaling or cross-toolchain claim.
The previous 18 sources, source archives and both old native/whole/audit
controls were preserved externally before this explicit expectation update.

## Fixed finite shipping policy

The [TCEC 4k minimum UCI rules](https://wiki.chessdom.org/Rules#TCEC_4k_rules)
distinguish the required subset, tolerating unsupported controls, and optional
identification. Shipping implements `uci`, `isready`, startpos move histories,
clocked `go`, `quit` and EOF with these explicit choices:

- `uci` emits `uciok` without optional id/options.
- `stop` and `ucinewgame` are consumed without cancellation, waiting or TT clear.
- `infinite` is consumed as an unsupported token. Every `go` is finite.
- Without an own-side clock, the budget is 1,000 ms. This is project policy,
  not a rule-prescribed number. With an own clock, the unchanged clock formula
  applies; a present zero/invalid own clock uses at least 1 ms. Opposite clock
  alone uses the default. Checked numbers, overflow, span parsing and
  missing-value key reprocessing are unchanged.
- Next `go`, `position`, `quit` and EOF still cancel and wait for
  `completed==epoch` after result output. `pending==0` is not that completion
  fence. Shutdown retains the kernel-CLEARTID joins and startup pool ownership.

The 1,000 ms value is a search budget, **not a hard wall-time cap**. Deadline
checks occur every 256 claimed nodes, and fallback preparation, scheduling and
output add time. Ignoring external stop or retaining TT between games can
change choices under time limits; unchanged search source does not imply
identical game results.

DEV retains the original protocol identification, actual stop/newgame and
infinite/depth/nodes/movetime source paths. The Board declaration and search
have changed, so the previous finite selection's DEV preprocessed/native
identities are **ancestry only**, not current DEV binaries or reused equality.
They remain explicitly scoped as old metadata in the recipe. The qualified
new pair instead has actual fixed O2/WORKERS=1/DEV=1 search and independent Board
contracts described below. This shipping source closure does not compile or
claim a new raw WORKERS=2 DEV executable.

## Source-only fixed build

On the qualified Linux x86-64 environment, including WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-d/build.py --out /absolute/new/external-build
```

The only option is a new absolute external output directory. The builder
reads this folder's ordinary source and recipe plus the installed compiler
and Python standard libraries. It never opens historical reports, experiments,
generated images, dependency trees or network resources. Receipt hashes in
the recipe are provenance metadata only. No executable/payload is tracked here.

Workers are fixed at 2, TT_BITS at 18, PLY at 128 and DEV at 0. Both search
workers and the input thread exist at startup. Board legality, legal EP, all
promotions/castles, repetition/halfmove state, incremental HCE, PVS/QS, learning,
ordered TT context and full-key coherent TT are preserved. HQ remains an
actual search backend. The build and verifier independently require the exact
`shipping_protocol` declaration; that metadata check is not a new runtime test
of default-budget or ignored-command behavior.

GCC `-Oz -flto`, static/raw syscall flags, five-unit order, native linker script
and section-header stripping remain fixed. Source/output paths are the only
substituted command arguments. Native identities are explicit literals:

```text
scalar 199da6e1e1a94c97fe853e0ff3d89b52e2057a55592052e7fbe5500147e4aeec
HQ     3f4269dc5c0d72c0b43bc73c6a11afdab5844836e12e7c31d60dde08c8ae2806
```

The loader retains E8/E9 BCJ plus one-final-fixed-Huffman Deflate. Payloads are
6,363/6,603 B; headers/decoder/inverse filter/ABI configuration add exactly
1,115 B. The full sizes above include everything. `loader/codec.py` is the
unchanged original build-time codec, selecting only `fixed_compress`; its
unused alternatives are not searched. Zlib is build-time only. Running the
full file requires no libc, external decoder, compiler, interpreter or helper.

The admitted classes are exact per form and native hash, not a general range:

| Form | Entry | RX at `0x400000` | BSS | Upper guard | Reservation |
| --- | --- | --- | --- | --- | --- |
| Scalar | `0x401e4d` | 2 pages | `0x402000` | `0x42d000` | `0x2f000` |
| HQ | `0x401f7f` | 3 pages | `0x403000` | `0x42e000` | `0x30000` |

Both have BSS 175,092 B within 43 pages, lower guard `0x3ff000`, non-executable
stacks and loader at `0x10000000`. The packer requires the full literal ELF
header/segments plus identity, form, entry and class; the verifier independently
requires each full literal layout. Previous experiment guards remain unchanged
and reject these new identities. READ_IMPLIES_EXEC rejection,
MAP_FIXED_NOREPLACE reservation, checked decode and RW-to-RX restoration bodies
remain unchanged. There is no old-image fallback or generic page-count admission.

Every build compiles each native twice, independently encodes/compiles each
whole twice, and builds a separate CHECKPOINT audit once per form. Exact
native, whole, payload, overhead and audit identities must match the recipe;
roundtrip alone is not acceptance. Audits are 7,501/7,741 B, never production
entry sizes. Failures save an incomplete report and clean owned commands.

The qualified producing environment remains GCC 13.3.0, GNU binutils 2.42,
Python 3.12.3, zlib 1.3 and x86-64 WSL Ubuntu. Actual versions are recorded;
other versions must reproduce the fixed bytes to pass. CRLF inputs are
explicitly normalized to LF and lone CR is rejected. `.gitattributes` keeps
these maintained sources LF.

## Closed archive and narrow physical proof

```sh
python3 -B engines/compact/tiny-entry-d/fresh.py --out /absolute/new/source-proof
python3 -B engines/compact/tiny-entry-d/verify.py \
  --build /absolute/new/external-build/build.json \
  --out /absolute/new/physical-proof
```

`fresh.py` enumerates exactly 20 ordinary source members: this folder's 18,
root LICENSE and tracked `engines/tests/chess_oracle.py`. It hashes and checks
the archive member set, rejects links/unsafe paths, and creates two separate
closed extractions without Git/generated files. Each starts its own isolated
Python interpreter, local builder and local verifier. Actual repeated native,
whole and audit bytes must match across extractions. The total is eight native
builds, eight whole builds, four audits, eight production sessions and four
pre-entry checkpoints. No immutable finite experiment or frozen helper is an
execution dependency. The oracle is needed only by verification.

The maintained verifier preserves the established narrow case scale: three
clocked searches per session with actual active quit or EOF for both forms.
It pins native/whole/audit/entry independently and checks `/proc/PID/exe` as
the **whole own-ELF**, restored anonymous RX as the **native**, pre-entry zero
BSS/padding, guards/W^X/non-executable stacks, persistent three startup TIDs,
stdio-only/no children, oracle legality and complete output/reader/process
settlement. It also rejects optional shipping id/options. This new source
closure run does not repeat the finite dispatch/TT-sentinel/arithmetic cases.

The selected header/search are exactly the qualified combined pair:
`e19749eb3315253e04171b89b8188df7e0db6b39ec4eb495187a6e158836823f` and
`48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c`.
The immutable proof40 index SHA is
`b05e3e344983c0bc340c28570b0229c8c5ab3cb1e579ca0e3bf290ac8a51cc83`.
Its four single-worker DEV search subjects retain the exact 20-case body and
compare normalized named Board/mailbox fields, full Worker/TT/game storage and
actual eight-argument call/counter traces. All 80 trace/state pairs match;
observed reduced/full-null/wide retries are 128/20/47 per subject. The reduced
score-at-or-above-beta path has actual count 0 and stays dynamically unproven;
exact expression reasoning remains separate. Search receipt SHA is
`e06e27d4c8c42e4db819afe3b8ab702a4fe61f0d9636e102efd05a4ea5ab2539`.

The independent Board contract checks four subjects, 24 cases and 3,051 nodes
each. Named fields, all 128 mailbox cells, legal sets, all-square attacks and
full HCE/hash/context match the independent oracle; special transitions and
poison initialization/reinitialization pass. Generator order matches across
the four actual subjects. Fixed perft depth-2 leaves are 400/2,039/191.
Its receipt SHA is `c123692a26644738f31e0d3710161b44a37aaefb40517b5ec6843a88606110bb`.
Neither contract compares raw Board padding across layouts. The separate exact
selected whole proof observes both per-form mappings, four shipping sessions
and two pre-entry checkpoints, receipt
`dfcebada0c43fee2dba85893385f261bc398b4c4808a90a6d90055ef1c922add`.
These receipts are reused by exact inputs; no broad game/fault/benchmark rerun
is hidden in this source-promotion check.

The completed finite qualification remains separate provenance: its native
checkpoint SHA is `1055c89f0f7bc042d33ad53ccad82fb9ca6a39368e6ed84dfd9e2a82fef24767`,
whole cost `53cb8a1fc1e9857d87e11c09bfc1ad0d61255784f427368f5940e0f4ab83a390`,
actual-dispatch TT/arithmetic `9d164b571a24181b1c93151e82a0ffe2472d77bb0635849409da7a65caf36756`,
and physical own-ELF/native `69eafcbbdb6493eeccd903c903154402922441516d584e786cf378c3b4b12ea7`.
The first proof exercises 60 commands, 38 exact clock cases and 14 ignored-state
comparisons per form with explicitly synthetic completion. The second is
actual worker/image/completion evidence. They are not relabeled as fresh runs.

Broader kernel/runtime-fault and decoder-fault evidence is reused only for
unchanged bodies; old three-page fault fixtures do not establish a new general
two-page admission claim. Exact new scalar/HQ positive mapping observations
are separately bound above. Old compose/finite images and old DEV hashes are
ancestry controls, not current image identities. The
previous strong stop/newgame/infinite lifecycle is excluded: the shared
`engines/tests/verify.py` strong stop group expects prompt external stop and
does not qualify this consume-only shipping profile. That shared test has not
been weakened or claimed as passed here. All provenance hashes are retained
as metadata without opening old evidence at build/runtime.

All generated files, archives, extractions, logs, transcripts, failure history
and final receipts remain outside Git. The final external index binds the 18
current raw source hashes and actual changed files to the closed archive and
terminal proof receipts. Historical experiments and other families are untouched.
