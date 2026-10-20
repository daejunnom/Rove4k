# One finite minimal shipping policy for selected C D

This optional experiment applies exactly one explicit shipping protocol policy
to the qualified maintained C D selection. It changes only runtime `go` and
the shipping main dispatcher. It preserves DEV behavior and preprocessing,
all board/search/HQ code, raw OS/pool ownership, codec/loader source, compiler
and linker flags, fixed resources and the already admitted layout class.
No engine feature core is removed and no compiler/encoding/codec search runs.
The repository's MIT license applies; all implementation source is project-owned.

| Actual form | Qualified strong control | Finite policy | Difference |
| --- | ---: | ---: | ---: |
| Scalar native | 8,476 B | 8,348 B | -128 B |
| HQ native | 8,864 B | 8,736 B | -128 B |
| Scalar complete own-ELF | 7,640 B | **7,540 B** | **-100 B** |
| HQ complete own-ELF | 7,881 B | **7,800 B** | **-81 B** |

Neither is a 4KiB entry: the whole files remain 3,444/3,704 bytes over 4,096.
The gains are actual complete files, not sums of earlier protocol, bitboard,
signals or codec measurements. There is no performance/strength/scaling claim.

## Declared policy

The [TCEC 4k rules, section 7.9–7.11](https://wiki.chessdom.org/Rules#TCEC_4k_rules)
distinguish the required minimal subset from tolerating unsupported commands
and optional identification. The one shipping policy is:

- `uci` prints `uciok` only, omitting the optional identification line.
- `stop` and `ucinewgame` are consumed like other unsupported commands. They
  do not cancel/wait/clear the TT. Extra-token admission remains unchanged.
- Every `go` has a finite budget. Without an own-side clock, the default is
  1,000 ms; this number is a project policy choice, not a rule-prescribed value.
- `infinite` is an unsupported shipping token. Without own clock it therefore
  uses the same 1,000 ms default; with own clock the existing clock formula wins.
- Own-side clock calculation is unchanged: clock/30 + capped increment*3/4,
  capped to clock/5, at least 1 ms and at most 86,400,000 ms. Present zero or
  invalid own clock still uses 1 ms; opposite-clock-only uses the default.
- The existing span parser, checked number/overflow handling and missing-value
  key reprocessing are retained. No parse or legal-move admission is removed.

DEV keeps its old identification, real stop/newgame and infinite/depth/nodes/
movetime behavior. The actual DEV `cc -E -P` source and stripped native are
byte-identical in each old/new pair. Scalar DEV remains 12,860 B with SHA-256
`0b013e8a55f1708b92af1aa4d08b44520c1ed345934db1ccf767c710b5c582ad`;
HQ DEV remains 13,248 B with SHA-256
`1bcf5bb9ef4d1bc6f8d0d5e5d947f418db21419f38268207bdacd90bf300832e`.
Both runtime DEV preprocessed files have SHA-256
`4205a736ef55e70f87128e45a207d8695a1451945265fb6a124682a8ae294d18`.

This is a semantic policy change. Retaining TT entries between games or
ignoring an external stop can change time-limited choices. No search-result
equivalence is inferred from unchanged search code. The 1,000 ms value is a
budget, not a strict completion-time guarantee: deadlines are sampled every
256 claimed nodes; fallback preparation, scheduling and output can add delay.

Internal cancellation/completion fences remain exact: next go, position,
quit and EOF cancel and wait for `completed==epoch` after result output.
`pending` is still distinct from completion. Startup TT lock initialization,
ready/partial-clone behavior, result publication, epoch ordering and actual
kernel-CLEARTID joins are unchanged. Ignoring two external commands does not
remove `stopped`, `wait`, `completed`, futexes or those ownership boundaries.

## Immutable control inputs and fixed generation

Before source changes, all 18 maintained entry inputs and the two old native
plus two old whole files were copied outside Git. The prechange freeze is
`/home/stemxstudio/rove4k-tiny-d-finite-inputs-20261020/freeze.json`, SHA-256
`fd0644307bf090dde7b93ac98ee3fce8d3b16328a5245a26c52cf4b725f89549`.

`inputs/entry/` contains those 18 ordinary maintained-source snapshots.
`pins.json` pins every LF input and the old expected images. New builds do
not read the mutable maintained folder, a historical experiment directory or
an old generated image. The first native phase independently rebuilds the old
control through the frozen source-only builder, requiring exact old native,
whole and audit hashes before generating a candidate. Old expectations are
never replaced by observed output. CRLF is explicitly normalized to LF, lone
CR rejected; `.gitattributes` preserves the owned text inputs as LF.

`transform.py` requires the exact old runtime SHA-256
`ec9ba6fce84fac501a25a3317a326bc62c9e420002a81303475230702ae1c773`,
requires each exact fragment once, and checks the byte complement outside
`go` and main. Its generated runtime has SHA-256
`82c62b57e500918827721553d67d9e23073c6cb5ca79dc22cdb8e38ab15f8e63`.
The other seven native source files must be identical to the control. Two
independent pure source generations, native builds and fixed-codec whole
builds require exact equality. There is no variant or preset selection.

Readable dual-mode runtime grows 184 B (15,065→15,249) to retain the exact DEV
branches. This does not count as shipping source reduction. A separate static
DEV=0 branch selection, removing comments/whitespace but not expanding macros,
measures active C spelling 7,379→7,177 characters, a 202-character reduction.
This is a static source metric, not compiler-preprocessed/package size; the
actual native and whole sizes are the measured values above.

## Native checkpoint before restoration cost

`build.py` never packs or runs a candidate. It first records both repeated
native files, DEV equality, new entry/header/segments and exact page-class
comparison. A changed class is a stop requiring root confirmation. The actual
checkpoint preserved RX three pages at 0x400000, BSS at 0x403000 with 175,092 B
in 43 pages, both guards, three program headers and non-executable stack.
Only RX byte lengths and entry changed:

| Mode | New entry | Native SHA-256 |
| --- | --- | --- |
| Scalar | 0x401f27 | `0e21d39f5f294f496f2224595462661864b4a274f4c2238a38f47024f0c93bbf` |
| HQ | 0x402064 | `6b987cc4f616ce9d835679c61d9aff8c0c16b59ec9a74db055c8ce826e14581f` |

`cost.py` requires the completed native-v2 checkpoint and exact current frozen
producer, 18 pins, two forms, two native repeats and eight candidate sources.
It reapplies the strict transform and reparses the actual native layout before
restoration. The old exact-image `admit()` stays unchanged and reproduces the
old controls; it does not claim to accept the new hashes. Candidate cost uses
the separately reviewed, source-bound same-class checkpoint with every old
mapping/segment guard retained. Its measured hash is first-cost metadata,
not an update of the old recipe or a claim of prior production admission.

Only the same BCJ + one-final-fixed-Huffman Deflate path and loader compile
recipe is used, twice. New payloads are 6,425/6,685 B; unchanged headers/loader
overhead is 1,115 B. The two exact whole identities are:

```text
scalar 26eaedc2560776a226a8e17886e209501346524e97fc2b47483f13335fbde013
HQ     3c863ceba32bf9173bf53d72f575c9e28e2ce2eb1cc43fde38bf03d6c9eff3ca
```

The same CHECKPOINT branch is compiled separately only because both whole
files won and the class was unchanged; audit sizes 7,563/7,823 B are not entry
sizes. A tie/loss would stop without candidate runtime. No image class or
loader capability is added. The toolchain remains the previously qualified
GCC13.3/binutils2.42/Python3.12.3/zlib1.3 environment.

## Reproduction and evidence scope

```sh
python3 -B engines/experiments/tiny-d-finite/build.py \
  --out /absolute/new/native-checkpoint
# Read the class checkpoint before proceeding. A changed class requires root.
python3 -B engines/experiments/tiny-d-finite/cost.py \
  --native /absolute/new/native-checkpoint/build.json \
  --out /absolute/new/whole-cost
```

The successful native-v2 receipt is
`/home/stemxstudio/rove4k-tiny-d-finite-native-20261020-v2/build.json`, SHA-256
`1055c89f0f7bc042d33ad53ccad82fb9ca6a39368e6ed84dfd9e2a82fef24767`.
The initial v1 native checkpoint is immutable; v2 adds explicit independent
source-generation equality and reproduces the same native bytes.
The whole cost receipt is
`/home/stemxstudio/rove4k-tiny-d-finite-cost-20261020-v1/build.json`, SHA-256
`53cb8a1fc1e9857d87e11c09bfc1ad0d61255784f427368f5940e0f4ab83a390`.
These first-cost receipts deliberately retain `candidate_qualified=false`;
the separately pinned policy/physical receipt is required for qualification.

## Fresh policy and physical qualification

The admitted candidate passed both separately scoped proofs. `units.py`
includes the actual candidate runtime with exact `go` and main source-body
hashes. Only its declared clock/input/completion/spawn boundaries are
interposed. Per scalar/HQ form, two shutdown cases exercise 60 commands,
38 exact fixed-clock calculations, 14 ignored-command state comparisons and
38 synthetic result publications. The comparisons include every actual TT
byte, all worker records, position/history, deadline, epoch and completion
state. `go infinite wtime 3000` uses the unchanged 100 ms own-clock formula;
bare/infinite-without-own-clock use 1,000 ms. These fixtures create no physical
worker and claim no actual clone, worker completion or kernel join.

`verify.py` separately pins the new native, whole, CHECKPOINT and first-cost
receipt identities. Both scalar/HQ forms pass actual quit and EOF sessions,
with eight independently legal results per session (32 total), plus two
pre-entry restoration checkpoints. The physical observations cover persistent
three startup TIDs, active worker CPU progress before and after ignored
controls, next-go and position output/completion fences, and active quit/EOF.
Own executable and anonymous native RX hashes are checked separately. RX
padding, initial BSS/padding, guards, stack permissions, stdio-only descriptors
and absence of child processes are checked by the frozen narrow image helper.
Every process exits 0; output readers join and owned groups disappear without
forced cleanup. Physical TT preservation is not inferred from these results;
the exact-byte TT assertion belongs to the interposed proof above.

The unit receipt is
`/home/stemxstudio/rove4k-tiny-d-finite-units-20261020-v1/results.json`, SHA-256
`9d164b571a24181b1c93151e82a0ffe2472d77bb0635849409da7a65caf36756`.
The physical receipt is
`/home/stemxstudio/rove4k-tiny-d-finite-physical-20261020-v1/results.json`, SHA-256
`69eafcbbdb6493eeccd903c903154402922441516d584e786cf378c3b4b12ea7`.
Both commands terminated 0 and preserve their exact proof sources, inputs,
compiler logs and transcripts externally. No failed candidate execution or
unsettled handle remains. Prelaunch review corrections affected proof cleanup
reporting and coverage only; native/whole/engine bytes remained frozen.

These validators deliberately admit these exact completed first-cost
receipts. A fresh build can reproduce the engine files from the source-only
recipe, but a changed receipt/path is not automatically accepted or used to
rewrite expected hashes. This qualification is a bounded experiment result;
it does not promote the maintained entry, qualify a 4KiB file, or establish
performance, strength or scaling.

Broad board/search/HQ/kernel and raw runtime/loader faults are not rerun.
Their unchanged source bodies, fixed decoder and mapping contract are bound
by exact source identity, with prior receipt metadata kept separately in the
frozen old recipe. The previous strong stop/newgame/infinite lifecycle proof
does not qualify this different shipping policy. A's minimum-policy evidence
supplies rule rationale/test design only, not D raw-clone completion or image
identity. Candidate verification must distinguish modeled TT/arithmetic checks
from actual worker completion, and own-ELF `/proc/exe` from anonymous native RX.

All generated sources, native/whole/audit files, receipts, transcripts and
failure history remain outside Git. Maintained entry inputs, shared docs,
workflow and common validators are untouched. The final external index binds
current owned source hashes to terminal receipts and records their exact scope.
