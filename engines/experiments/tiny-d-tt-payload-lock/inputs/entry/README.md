# Maintained selected C D own-ELF entry

The readable native program lives in `native/`; its project-owned restoring
loader, linker and build-time codec live in `loader/`. `recipe.json` fixes
source hashes, compiler/linker order, resources, the finite shipping policy,
admitted layouts and exact native/whole/audit identities. Edit readable source
deliberately; generated native images and payloads do not belong in this folder.

This selection promotes the qualified completion latch over the previous
7,478/7,718 B layout-plus-phase selection. Seven exact runtime fragments replace
separate ready/pending/completed counters with one pending latch. The complete
Board/search/HQ sources, seven other native files, raw clone/futex ABI, loader,
codec, flags and resources retain their exact bytes. Scalar retains its two-page
RX class and HQ its three-page class. Each full native identity has its own
literal entry and mapping class. There is no optimizer, flag/codec/preset sweep,
generic ELF admission or external engine source. The root MIT license applies.

| Fixed profile | Native ELF | Complete own-ELF | Complete SHA-256 |
| --- | ---: | ---: | --- |
| Scalar | 8,092 B | **7,457 B** | `08c40aa381953df98aa6d6f893487ff90d9a43854acd552158795ce795afcc70` |
| HQ | 8,480 B | **7,707 B** | `1178c3e22ac3a2e9db549ddb5246f9b197b7136fa0fc89008577c52468217963` |

Both exceed 4,096 bytes by 3,361/3,611 bytes. The actual native files save
32 B each and complete files save 21/11 B against the preserved layout-phase
control; native and complete-file savings are measured separately. This folder makes no event
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
- Next `go`, `position`, `quit` and EOF still request cancellation and wait
  for an acquire observation of `pending==0` after result output. Pending 1
  reserves result publication and never permits main to reuse job storage.
  Shutdown retains the kernel-CLEARTID joins and startup pool ownership.

The 1,000 ms value is a search budget, **not a hard wall-time cap**. Deadline
checks occur every 256 claimed nodes, and fallback preparation, scheduling and
output add time. Ignoring external stop or retaining TT between games can
change choices under time limits; unchanged search source does not imply
identical game results.

DEV retains its identification, stop/newgame and infinite/depth/nodes/movetime
source paths, but the shared private completion protocol has changed. Previous
DEV preprocessed/native identities and prior W1 DEV core contracts are ancestry
for their exact source scope. They are not current WORKERS=2 DEV binaries,
new DEV equality or general race qualification. This shipping closure compiles
only DEV=0; unchanged Board/search proofs remain separately scoped below.

## Completion latch and lifecycle evidence

Before clone, main runtime-stores WORKERS into zero-initialized pending storage.
Each arrival release-decrements it, and successful startup waits for zero.
This startup wait privately sets stopped to 1; epoch remains zero until GO.
GO stores WORKERS+1 before epoch release. Each finished worker acq_rel-decrements
once, and old value 2 selects the final worker. Pending 1 reserves the unchanged
`result()` body; only its completed output is followed by release-store zero.
Main's acquire-zero wait gates position replacement, re-GO and normal shutdown.
Late wakes trigger condition rechecks after all prior decrements have finished.

The exact source complement keeps clone failure before startup wait, created-only
kernel-cleared TID joins, quitting and epoch publication unchanged. Failure after
zero or one successful clone bypasses the incomplete arrival barrier. There is
no explicit stack munmap or TT free: main joins created TIDs, returns, and
`start.S` calls exit_group to release process mappings. Static complement receipt
SHA is `f44e70893fda1cd16a10d3e6bfa5123a3125cc043329ab535dbbcfc72de54173`.
Prior raw-runtime fault evidence is ancestry for those exact unchanged premises,
not newly executed startup-failure or CLEARTID branch coverage.

The exact scalar/HQ shipping images have a separate actual publication proof,
receipt `99320b49fefaa20644a1261bbe82fd29984e6d9d674367b2a6a3643a0c5b28bc`.
Two sessions and four GO epochs use real stdout backpressure: a worker blocks
in result write while main is in private futex wait and the current pending
word is 1. Its syscall expected argument may still be 3 and is kept separate
from the current word. Ordered independently legal results, the same word zero,
persistent startup TIDs and natural quit with output EOF settlement are observed. Target
code, memory, registers and kernel personality are unmodified. This is not
general race freedom, a new startup fault suite, strength or performance proof.
The ordinary source archives and newly bound pre-entry audits below qualify
reproduction and routine physical checks separately.

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
scalar 59829299f667cdb6682c5ed4a955fb50b76a5584209caf9e4bddf1c0ee2cd160
HQ     f1d6558ec5a13e400c2d6df182b01b3236bf1ee1e99f686e47f144a32d222c5c
```

The loader retains E8/E9 BCJ plus one-final-fixed-Huffman Deflate. Payloads are
6,342/6,592 B; headers/decoder/inverse filter/ABI configuration add exactly
1,115 B. The full sizes above include everything. `loader/codec.py` is the
unchanged original build-time codec, selecting only `fixed_compress`; its
unused alternatives are not searched. Zlib is build-time only. Running the
full file requires no libc, external decoder, compiler, interpreter or helper.

The admitted classes are exact per form and native hash, not a general range:

| Form | Entry | RX at `0x400000` | BSS | Upper guard | Reservation |
| --- | --- | --- | --- | --- | --- |
| Scalar | `0x401e28` | 2 pages | `0x402000` | `0x42d000` | `0x2f000` |
| HQ | `0x401f5a` | 3 pages | `0x403000` | `0x42e000` | `0x30000` |

Both have BSS 175,092 B within 43 pages, lower guard `0x3ff000`, non-executable
stacks and loader at `0x10000000`. The packer requires the full literal ELF
header/segments plus identity, form, entry and class; the verifier independently
requires each full literal layout. Historical production guards in frozen
experiment inputs remain unchanged and reject these identities; the separate
cost-only exact adapter is not a general admission. READ_IMPLIES_EXEC rejection,
MAP_FIXED_NOREPLACE reservation, checked decode and RW-to-RX restoration bodies
remain unchanged. There is no old-image fallback or generic page-count admission.

Every build compiles each native twice, independently encodes/compiles each
whole twice, and builds a separate CHECKPOINT audit once per form. Exact
native, whole, payload, overhead and audit identities must match the recipe;
roundtrip alone is not acceptance. Audits are 7,480/7,730 B, never production
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
The Board/search contract receipts are reused by exact unchanged core inputs;
that previous physical/audit pair is old-image ancestry, not current latch
image evidence. New publication and maintained routine physical observations
are separate. No broad game/fault/benchmark rerun is hidden in this promotion.

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
