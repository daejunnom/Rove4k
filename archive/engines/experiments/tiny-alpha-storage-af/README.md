# One fixed A/F private storage spelling stage

This independent experiment adds exactly 18 literal private-object aliases
after the frozen maintained A5072/F5179 shipping stages. Prior A31/F73 and the
earlier A renames, resources and function spellings stay unchanged. Readable
engine code, DEV, types, members, functions, external APIs, directives, strings,
runtime/search policy, compiler flags, profile, launcher and codecs are controls.
No maintained entry is modified or promoted by this folder.

| Family | Control C | Candidate C | Source saving | Control whole | Candidate whole | Whole saving |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 10,606 | **10,184** | **422** | 5,072 | **4,980** | **92** |
| F | 11,216 | **10,745** | **471** | 5,179 | **5,083** | **96** |

All values are bytes. A and F still exceed 4,096 by 884 and 987 bytes. Source
savings and complete-file savings are different measurements. No 4KiB,
strength, NPS, SMP scaling or whole-plan acceptance is claimed.

## Exact single policy and ownership

The literal map was fixed before source preparation, without an alias pool,
permutation, retry, compiler-feedback choice or compression sweep.

| Old object | Alias | Old object | Alias |
| --- | --- | --- | --- |
| back | qa | command | qb |
| deadline | qc | epoch | qd |
| fallback | qe | finished | qf |
| game_keys | qg | game_length | qh |
| material | qi | mutex | qj |
| pending | qk | position | ql |
| quitting | qm | ready | qn |
| steps | qo | stopped | qp |
| table | qq | workers | qr |

The ownership inventory has seven file-scope objects with C external linkage,
nine explicit file-static objects including F's ready, and two function-static
arrays. Their inspected standalone shipping build compiles one C translation
unit from stdin without a companion engine object or export script. The
external-linkage objects remain external-linkage objects; their type, storage
duration, initialization, address consumers and synchronization stay unchanged.
pthread receives object addresses rather than object-identifier strings.

The old policy conservatively excluded globals/statics by role. That exclusion
did not establish a spelling-required external ABI. This review does not infer
native equality from `-s`; the complete native gates below independently decide
it for the qualified compiler/libc target. main, actual external types/APIs,
all functions and the Move typedef remain protected. MOVE directly consumes
Move in its opaque directive body, so it is outside this object-only stage.
Already shortened types/members and DEV-only letters/castles are not recounted.

A uses 17 object names in 87 code substitutions; ready has zero uses. F uses
all 18 in 99 substitutions, including three ready uses. There are no new
resource substitutions. PLY code uses remain A 8/F 0. All 53/52 opaque regions
and 432/416 directive bytes remain in order and byte-identical.

The read-only source audit and fixed proposal are preserved outside Git at
`C:/Users/강민수/Documents/Codex/rove4k-af-private-name-audit-20261020/`.
The proposal SHA is
`a0e047f1e11ea22956962a13107db2a28c457009137b5d04d671e55e63b9d488`.
Its human source-line estimates were 419/468 bytes. Actual prepared-source
counting found one additional mutex use in each work-loop condition wait:
13/16 instead of 12/15, adding three bytes per family. The original audit and
proposal remain unchanged; `estimate-versus-actual.json` preserves the exact
discrepancy. Aliases and candidates were not changed in response to a cost.

## Closed controls and decisive gates

The owned control tree contains 27 ordinary files: both ten-file maintained
entries, five shared producer helpers and two existing runtime helpers.
The A source was admitted against its qualified source-freeze SHA
`54d773e921f115a4c6c801a485773621b4f81b94f348c1c55d3e2fecdc0da9b4`
before copying. That old report is provenance metadata, not a normal build
input. Five frozen prior-policy reference files supply the reviewed generic
opaque/rewrite logic. The normal producer reads its own ordinary sources only;
it does not read current maintained files, an old executable or generated
source/report. LF normalization and raw working-input hashes are explicit.

```sh
python3 -I -B engines/experiments/tiny-alpha-storage-af/build.py \
  --out /absolute/new/storage-af-cost
```

Each unchanged baseline builder reproduces shipping C/native/whole and DEV
C/native twice. The new final stage requires literal source/candidate pins,
all per-name counts and arithmetic, injectivity, raw/logical readable and
shipping freshness, and independent opaque/lexer agreement. Six bounded pure
source fixtures passed. Independent policy/ownership/gate reviews preceded
candidate compilation. A separate read-only prepared-byte comparison confirmed
that the entire candidate contains only the exact 18-name code rewrite.

Actual final compiler preprocessing removes only `-o x`; it retains all other
flags, including `-s` and F's `-pthread`, and adds no resource defines. Candidate
full `-E -P` output is reversed using identifier aliases alone and must equal
the original raw bytes. Whitespace/token normalization and numeric inverse
replacement are zero. Full final macro dumps agree, with A `{PLY:128}` and F
`{}`. A separate unchanged-readable probe under the original configured profile
confirms WORKERS=2, TT_BITS=18, PLY=128. Header-expanded identifiers and final
macro names must be free of every new alias before this inverse comparison.

Both candidate ELF builds for a family must equal its original COMPLETE native
SHA before either candidate codec runs. Build-ID and nonallocated sections are
included; no exception is allowed. A remains 22,672 bytes at
`84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a`;
F remains 22,664 bytes at
`ef10962ff16e5158e0cb18cbf96b944404bd1c4db301bfbb47a0faed33466c22`.
Both attempts passed for both families. A hard gate failure would preserve the
receipt and stop the whole family loop without retry or an alternative alias.
That path did not occur in the successful first cost.

A retains cc -Os with its stripped native argv, 77-byte launcher and ALONE
LZMA1 preset 9 extreme/lc2/lp0/pb0/no-check/64MiB dictionary. F retains its
-pthread argv, 75-byte launcher and XZ LZMA2 preset 9 extreme/lc2/lp0/pb0/CRC64.
Source-literal selection and bootstrap templates are unchanged. Strict Python
EOF/trailing checks and independent CLI decoding restore exact bootstrap bytes.
Two independent source/native/whole generations agreed for each family.
The qualified domain remains Ubuntu 24.04.4 x86-64, GCC 13.3.0 and glibc 2.39;
A's existing merged-pthread libc dependency is unchanged.

| Item | A SHA-256 | F SHA-256 |
| --- | --- | --- |
| Candidate C | `9e764bbbea91f198a4cb5aff62aae9f3007df5f715d4d8b8142e4795b5109d5a` | `fa03bfe65508b5fd72097940cea869c79744a8d3d2fa3bd09f8cd60b90173dc2` |
| Complete file | `4f339d08d99e51cd5935f20cc10d0665ed19f515e227cb5fa6be1623e7b21a8d` | `c4308bd1173d93a5ae83055ae0dd535264d4fec0c938dc4a78ccc2536e25ff02` |
| Bootstrap | `1397aa310d1ae1e65b528f3f12977494cde173356313b687436ec3b15b37a391` | `27140179b5d628d1458cc79936f5c541512ecf6a191b1754a5ce760d3245484d` |

The raw first-cost receipt is
`/home/stemxstudio/rove4k-tiny-alpha-storage-af-first-20261020/results.json`,
SHA `505932407b3b306c8a9122cf7da11f1200a75a4f39cb821101afffbca095106d`.
The command is terminal exit 0; engine executions in that producer are zero.
Historical core/rules/search/SMP evidence is reused only through exact complete
native identity. No broad engine, game, sanitizer, performance or scaling
campaign is rerun. The separately authorized four selected-wrapper sessions
and final ordinary-source inventory are recorded after physical completion.

## Four actual selected-wrapper sessions

After both gains, root authorized only the selected A4980 and F5083 wrappers,
each with one quit and one EOF session. The runtime adapter admits the exact
own cost receipt, all 38 producer inputs (27 controls, five references, six
producer inputs), 24 selected/independent-attempt artifacts and both original
control receipts before launching either verifier. It never rereads maintained
files or current Git state.

Each original verifier and its helpers are copied unchanged from the own
ordinary controls into an execution mirror. Only five representation expected
fields change per recipe: source bytes/SHA, whole bytes/SHA and bootstrap SHA.
Old native, DEV, readable and historical qualification metadata stay unchanged.
The actual raw two-family cost receipt is copied byte for byte as both selected
`build.json` files; no replacement success report is manufactured.

The adapter owns the exact corrected 2,583-byte `run_owned_verifier` function,
SHA `b9d830bfbe3fae4dec71826063f8e273641e807e75e0a21c5ded33f4838bc644`,
and checks that embedded source identity without an old-runtime dependency.
Post-Popen saves/waits remain under BaseException cleanup, bounded
SIGINT/kill/reap and best-effort error recording. A and F use distinct ownership
rows/logs, and the next family starts only after the previous verifier is
waited, validated and absent. Forced cleanup cannot be reported as success.
Independent source review preceded execution; no new stub campaign ran.

```sh
python3 -I -B engines/experiments/tiny-alpha-storage-af/verify.py \
  --out /absolute/new/storage-af-runtime
```

Exactly two original verifier invocations created four actual wrappers and
16 GO epochs. All four wrappers returned legal results for white-zero,
black-zero and bare finite GO, followed by one closing bestmove during an
observed active clocked GO. Each restored `/proc/<pid>/exe` had its original
complete native SHA, exactly three stable startup TIDs, an already deleted
private executable path and empty observed compiler-child lists. All four
exited 0 with empty stderr; main processes were absent and output readers had
finished. Both verifier PIDs were absent after wait. All 38 inputs, 24 artifacts,
two control receipts, the raw cost receipt and mirror files were rechecked.

Observed work and physical completion do not establish that cancellation caused
search completion; causality remains explicitly `unproven`. These are fresh
selected-file restoration/lifecycle observations and do not extend historical
core, strength or scaling evidence. No further engine, core fixture, variant,
compiler/codec search, game or benchmark ran. The normal startup compilation
inside the four selected wrappers is part of their ordinary restoration.

The executed adapter is 16,377 bytes at SHA
`5adc608293166ad23fc66f54e38646cb55e6b012b3299380d8353bd64cf981da`;
the 15,018-byte runtime pins SHA is
`0243096344ddaad506ca72c4d7e5590cd4e70bb41d9c0207112daef5c2f08192`.
The successful raw runtime receipt is
`/home/stemxstudio/rove4k-tiny-alpha-storage-af-runtime-20261020/runtime.json`,
SHA `304b37c55065752cb1c723ad73e9d713f6681c32fc8ad91616a2ac340afc7ea1`.
The unchanged verifiers' fresh receipts are `A/fresh/runtime.json`, SHA
`0b3073520f8f9e17d9a114e0c6732df4d2b2d11086f03a689adcde41633ffaba`,
and `F/fresh/runtime.json`, SHA
`9e13940ecbe5a89c6978e535ea69f95aa633c2005ffd42a3f897397bd528510d`.

The adapter and both owned verifier commands are terminal exit 0. All child
reviewers are terminal with no live execution handles. After the sessions,
only this README result was updated; executed helper/source/policy/recipe pins
remain unchanged. The first-cost raw receipt and its source snapshot are
preserved, including zero producer engine executions and the original pending
runtime status. Runtime success is a separate receipt.

The final 44-file ordinary-source inventory and raw evidence index is
`C:/Users/강민수/Documents/Codex/rove4k-tiny-alpha-storage-af-20261020-evidence/summary.json`.
The selected runtime command binds this historical external cost; the normal
producer remains independent of generated evidence. This candidate is frozen
for separately assigned maintained A/F promotion and does not perform it.
