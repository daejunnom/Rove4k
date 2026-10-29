# Selected A query and job ownership experiment

One fixed candidate reduces the complete selected A package from **5,207 to
5,183 bytes**, a saving of **24 bytes**. It remains 1,087 bytes above 4,096.
This folder does not promote the canonical entry, change search policy or run a
compiler/identifier/compression sweep. Root owns integration and qualification.

| Bytes | Historical selected control | Candidate | Delta |
|---|---:|---:|---:|
| Readable C | 25,131 | 24,921 | -210 |
| Encoded shipping C | 11,148 | 10,958 | -190 |
| Stripped native ELF | 22,664 | 22,664 | 0 |
| Complete executable launcher | 5,207 | 5,183 | -24 |

The native size is equal; the actual native images differ. Complete size includes
the unchanged 75-byte shell prefix, compressed Python bootstrap, compiler argv
and restored C literal. Size is separate from the narrow boundary proofs below.

## Exactly two ownership changes

`transform.py` accepts only the readable control SHA-256
`321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d`.
The candidate readable SHA-256 is
`79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed`.

The existing generated-move text query also serves first-legal lookup when its
text pointer is null. It keeps the same `text`, exact `strcmp`, generator order
and `make` legality filter. Its successful already-made child is returned in a
caller-owned scratch Board and reused by replay, avoiding a second identical
make. A failed query may change scratch, which callers discard; input/output
aliasing is outside this helper's contract. Empty text remains distinct from a
null pointer. Global position/history are committed only after the full history
has been admitted. No decoder or move annotation is introduced.

Per-job nodes/depth/score/best reset belongs to `think` entry instead of a GO
loop followed by another partial reset in `think`. Every dispatched worker
enters `think` before decrementing pending, including a job already stopped or
with no search iterations. The final pending transition therefore publishes
only freshly reset/completed outputs, retaining the same legal fallback if no
iteration completes. Worker identity and learned heuristics persist. Partial
startup failure happens before dispatch and is unchanged. Best still survives
between completed iterations inside one job.

A broader private interface intentionally changes: directly calling `think`
with a preseeded best now clears it even for stopped/zero-iteration calls.
Production GO already cleared that field. This is a declared job-ownership
boundary, not a claim that arbitrary direct consumers are bit-identical.

The board/hash/search body is byte-identical to the qualified control, SHA-256
`557f9e15c072410fc16c7f3aad8320e904e02574b99b1c625a9047c620b85b57`.
Its existing rule/core coverage can be reused at that boundary. Changed query,
`think` entry and physical job publication paths need separate proof; equal body
bytes alone do not qualify them. `design.md` records the ownership assumptions.

## Fixed production

The selected recipe is unchanged: two workers, TT bits 18, PLY 128,
`cc -Os -x c - -o x -s`, the existing 45 fixed token substitutions and 31 function
spellings, and XZ CRC64/LZMA2 preset 9 extreme with lc=2/lp=0/pb=0. The measured
target is WSL Ubuntu 24.04.4 x86-64, GCC 13.3.0, glibc 2.39 and Python 3.12.3.
This does not establish generic compiler/libc or event-tool eligibility.

The builder snapshots raw and explicit LF source/recipe/template/prefix/helper
bytes before importing helpers. Each control/candidate is independently generated
twice, including DEV when requested. Control compact C/native/bootstrap/whole
and DEV hashes must match the selected recipe. Each form's readable shipping
image and fixed compact image must match as full stripped native bytes.

The first cost receipt is preserved outside Git at
`/home/stemxstudio/rove4k-tiny-a-ownership-first-20261020/`:
`build.json`, `provenance.json`, `validation-manifest.json` and `readable.diff`.
It was reported before runtime checks. Its builder hash is
`b20c920860a50bb33091e04dfb616370fd0396f443bdb93aa0f5270e4da83ca8`.
That receipt remains bound to its actual original input paths and producer;
later source-closure maintenance is recorded separately.

The historical control closure is stored in this folder as
`control/{engine.c,recipe.json,bootstrap.py.in,launcher.sh,build.py}`. All five
files are exact LF copies of the first receipt's frozen inputs, with explicit
hashes. `control/build.py` is historical provenance, not the runnable experiment
producer. The current `build.py` reads only that owned control closure and pinned
shared helpers; it has no input dependency on a future mutable `tiny-entry-a`.
Its source-closure version hash is
`65dee690ccf2ceac809cb580e8667abaf6da8a45d1dd7f93c1bf9e40168e3af6`.
This path-only maintenance preserves the original cost receipt and receives a
separate same-recipe replay; it is not a second candidate.

The closure replay completed at
`/home/stemxstudio/rove4k-tiny-a-ownership-closure-rebuild-20261020/`.
Its `reproduction.json` compares 106 generated form files: 94 non-JSON files are
byte-identical, and 12 compile JSON files differ only in the normalized output
root. Control/candidate shipping C, native, bootstrap, whole file and DEV outputs
remain exact. All five archived control inputs, helpers and transform match the
original frozen inputs; only the producer's explicit input-path maintenance is
different and recorded. Existing runtime proof is reused only because its actual
candidate source/bootstrap/wrapper/native identities are unchanged.

```sh
python3 -B engines/experiments/tiny-a-ownership/build.py \
  --out /absolute/new/external-ownership-build --dev
```

| Candidate identity | SHA-256 |
|---|---|
| Encoded C | `5ed00fd936cf6228ec7f73d6c1fddd0f18bfe899aff82b5aa695732240079b59` |
| Stripped native | `6d9a3c192078f22914e17a0332ef2f0dbd134050833c1fceb0ccb221ecba34e2` |
| Complete file | `9a4911a0364c881e88764dbf41832c051eead2961160cae97136668405cbfa7b` |
| Decoded bootstrap | `833d83371cd7ddb11a4a940801fe99c4e2ffc11fc2da32482ee264f20883b095` |

## Scope of verification

Independent source review found no concrete defect under the documented
nonalias scratch, transactional replay and published-job contracts. First cost
and both independent attempts passed. The following separate narrow proofs also
passed; unchanged board/search body coverage is reused rather than relabeled as
a fresh general rule run. No general rule matrix, strength games, NPS or
many-core campaign is part of this experiment.

### Query and worker-entry boundary

`query-contract.c` and `query-check.py` freeze the original readable control,
candidate and fixture before compiling control O2, candidate O2 and candidate
ASAN/UBSAN for exactly the same cases. Each profile passes eight positions,
122 matched coordinate queries with all declared child fields, 192 invalid
tokens, fourteen transactional replay cases, two production-equivalent think
cases and two broader direct-think cases. Special positions include four
promotion pieces, EP and castling. The history boundary accepts 4,095 replay
moves (4,096 stored keys) and rejects the next move without changing globals.
No input/output aliasing or read of failed-query scratch is tested or promised.

The complete shared JSON reports agree. The only expected differences are
preseeded direct-think best 6676 in the old control versus 0 in the candidate,
once prestopped and once zero-iteration. Other metadata is equal. These explicit
differences document the private contract instead of calling arbitrary direct
think calls equivalent. Runtime stderr and sanitizer stderr are empty; all
profile returns are 0, with no forced cleanup. Compiler logs are retained.

```sh
python3 -B engines/experiments/tiny-a-ownership/query-check.py \
  --control /absolute/new/external-ownership-build/control/engine.c \
  --candidate /absolute/new/external-ownership-build/candidate/engine.c \
  --out /absolute/new/external-ownership-query --asan
```

Authoritative report:
`/home/stemxstudio/rove4k-tiny-a-ownership-query-contract-first-20261020/results.json`.
The complete frozen inputs, compiler logs, declared child fields and transcripts
are retained at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-a-ownership-query-evidence-20261020/`.

### Actual package, repeated job fences and physical exit

`verify.py` freezes the first-cost producer/program/proof/shared-helper bytes
before launching the actual 5,183-byte file in two sessions, one quit and one EOF.
Each has four clocked epochs: active white GO replaced by another GO, active GO
followed by position replay to black, zero-clock black GO immediately replaced,
then active black termination. The observed legal-root/result sequence is white
g1f3, white g1f3, black a7a6 and black g8f6 in each session, exactly once per epoch.
The black roots prevent a previous white result from passing as a fresh output.
No unsupported shipping stop/infinite command is used.

The actual deleted ELF image equals candidate native SHA-256 above. Three TIDs
observed before the first command remain stable, no compiler child remains
after UCI-ready, and the private restoration directory is absent then. Cleanup
before fd-exec has unchanged source-ordering evidence; no independent pre-input
filesystem sample is claimed. Both sessions return 0, readers observe physical
EOF, the native PID is absent, observed owned descendants settle, stderr is empty
and forced cleanup is empty. CPU activity and later output do not prove
cancellation causality or forced per-worker scheduling; both limits remain
explicit in the receipt.

```sh
python3 -B engines/experiments/tiny-a-ownership/verify.py \
  --build /absolute/new/external-ownership-build/build.json \
  --out /absolute/new/external-ownership-runtime
```

Authoritative report:
`/home/stemxstudio/rove4k-tiny-a-ownership-runtime-20261020/results.json`.
The consolidated Windows evidence is
`C:/Users/강민수/Documents/Codex/rove4k-tiny-a-ownership-20261020-evidence/`.
Its `summary.json` binds the twelve source inputs and the original cost,
source-closure replay, query and physical-run receipts. Every owned compiler,
wrapper and test process is terminal. Canonical promotion, combined transport
measurement and CI are separate root-owned work.
