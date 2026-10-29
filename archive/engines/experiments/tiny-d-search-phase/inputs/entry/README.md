# Maintained selected C D own-ELF entry

The readable native program lives in `native/`; its project-owned restoring
loader, linker and build-time codec live in `loader/`. `recipe.json` fixes
source hashes, compiler/linker order, resources, the finite shipping policy,
admitted layouts and exact native/whole/audit identities. Edit readable source
deliberately; generated native images and payloads do not belong in this folder.

This selection promotes the already qualified finite-minimum D source and
images. Only runtime `go` and shipping dispatch differ from the previous
7,640/7,881 B strong-policy selection. Board/search/HQ, the remaining runtime
source bodies, raw OS/pool ownership, loader/codec, flags, resources and mapping
class remain unchanged. There is no optimizer, flag/codec/preset sweep, new
loader capability or external engine/decoder source. The root MIT license
applies.

| Fixed profile | Native ELF | Complete own-ELF | Complete SHA-256 |
| --- | ---: | ---: | --- |
| Scalar | 8,348 B | **7,540 B** | `26eaedc2560776a226a8e17886e209501346524e97fc2b47483f13335fbde013` |
| HQ | 8,736 B | **7,800 B** | `3c863ceba32bf9173bf53d72f575c9e28e2ce2eb1cc43fde38bf03d6c9eff3ca` |

Both exceed 4,096 bytes by 3,444/3,704 bytes. This folder makes no event
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

DEV retains the original identification, actual stop/newgame and
infinite/depth/nodes/movetime behavior. The finite qualification established
exact old/new DEV runtime `cc -E -P` equality and native equality. Its runtime
preprocessed SHA is `4205a736ef55e70f87128e45a207d8695a1451945265fb6a124682a8ae294d18`;
scalar DEV is 12,860 B / `0b013e8a55f1708b92af1aa4d08b44520c1ed345934db1ccf767c710b5c582ad`,
HQ DEV is 13,248 B / `1bcf5bb9ef4d1bc6f8d0d5e5d947f418db21419f38268207bdacd90bf300832e`.
Those proofs are reused by exact source identity rather than rerun here.

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
scalar 0e21d39f5f294f496f2224595462661864b4a274f4c2238a38f47024f0c93bbf
HQ     6b987cc4f616ce9d835679c61d9aff8c0c16b59ec9a74db055c8ce826e14581f
```

The loader retains E8/E9 BCJ plus one-final-fixed-Huffman Deflate. Payloads are
6,425/6,685 B; headers/decoder/inverse filter/ABI configuration add exactly
1,115 B. The full sizes above include everything. `loader/codec.py` is the
unchanged original build-time codec, selecting only `fixed_compress`; its
unused alternatives are not searched. Zlib is build-time only. Running the
full file requires no libc, external decoder, compiler, interpreter or helper.

The admitted mappings remain RX at `0x400000` over three pages, BSS at
`0x403000` with 175,092 bytes in 43 pages, inaccessible guards at `0x3ff000` and
`0x42e000`, and non-executable stacks. Scalar entry is `0x401f27`, HQ entry
`0x402064`; the loader stays at `0x10000000`. READ_IMPLIES_EXEC rejection,
MAP_FIXED_NOREPLACE reservation, checked decode and RW-to-RX restoration are
unchanged. Exact new image identities are admitted without old-image fallback
or mapping/segment guard relaxation.

Every build compiles each native twice, independently encodes/compiles each
whole twice, and builds a separate CHECKPOINT audit once per form. Exact
native, whole, payload, overhead and audit identities must match the recipe;
roundtrip alone is not acceptance. Audits are 7,563/7,823 B, never production
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

The completed finite qualification remains separate provenance: its native
checkpoint SHA is `1055c89f0f7bc042d33ad53ccad82fb9ca6a39368e6ed84dfd9e2a82fef24767`,
whole cost `53cb8a1fc1e9857d87e11c09bfc1ad0d61255784f427368f5940e0f4ab83a390`,
actual-dispatch TT/arithmetic `9d164b571a24181b1c93151e82a0ffe2472d77bb0635849409da7a65caf36756`,
and physical own-ELF/native `69eafcbbdb6493eeccd903c903154402922441516d584e786cf378c3b4b12ea7`.
The first proof exercises 60 commands, 38 exact clock cases and 14 ignored-state
comparisons per form with explicitly synthetic completion. The second is
actual worker/image/completion evidence. They are not relabeled as fresh runs.

Broader board/search/HQ, kernel/runtime-fault and decoder-fault evidence is
reused only for unchanged source bodies and fixed loader/mapping contract.
Old compose images are ancestry controls, not current image identities. The
previous strong stop/newgame/infinite lifecycle is excluded: the shared
`engines/tests/verify.py` strong stop group expects prompt external stop and
does not qualify this consume-only shipping profile. That shared test has not
been weakened or claimed as passed here. All provenance hashes are retained
as metadata without opening old evidence at build/runtime.

All generated files, archives, extractions, logs, transcripts, failure history
and final receipts remain outside Git. The final external index binds the 18
current raw source hashes and actual changed files to the closed archive and
terminal proof receipts. Historical experiments and other families are untouched.
