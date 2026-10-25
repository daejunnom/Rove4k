# One startup-counter ownership experiment

This folder preserves one fixed source change against the maintained A5140
entry. It does not select or promote a canonical engine. Its complete candidate
is **5,129 bytes**, 1,033 bytes above 4,096; the target remains unmet.

| Form | Readable C | Compact C | Stripped ELF | Complete file |
| --- | ---: | ---: | ---: | ---: |
| Frozen maintained control | 24,921 | 10,958 | 22,664 | 5,140 |
| Startup-counter candidate | 24,820 | 10,855 | 22,672 | 5,129 |
| Difference | -101 | -103 | +8 | **-11** |

These are actual complete-file costs with the same compiler, fixed spelling
map, resource literals, Python bootstrap and LZMA-alone transport. They are not
additive estimates. Both forms reproduced independently twice in the first
producer run. A second standalone source closure, copied from the first frozen
inputs with no maintained-entry or shared-helper lookup, again reproduced both
forms twice and matched all ten readable/compact/native/bootstrap/whole files.
No flag, identifier, compression or architecture sweep was performed.

## Exact change and phase ownership

`transform.py` admits only readable control SHA-256
`79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed`.
It makes exactly three checked replacements:

1. Remove `ready` and initialize `pending=WORKERS` before creating threads.
2. Each worker decrements `pending` once on entry under the existing mutex and
   broadcasts the existing `finished` condition. This remains outside the
   search-completion/result branch.
3. After every `pthread_create` succeeds, main calls the existing `wait()` in
   place of its separate startup lock/predicate/wait/unlock sequence.

Startup arrivals finish before input processing and therefore before the first
job can publish a new pending count. Early arrivals leave a persistent zero;
late arrivals and spurious condition wakes are handled by the same predicate
under the same mutex. No startup arrival calls `result()`. Job epochs, search,
last-worker output, cancellation and shutdown retain their existing ownership.

Partial creation failure still jumps directly to shutdown, bypassing startup
`wait()`. The residual count for uncreated workers is never awaited. Only the
successfully created workers are woken and joined. A worker arriving after the
shutdown broadcast observes persistent `quitting=1` and does not depend on the
earlier broadcast. Successful joins precede TT free. The existing join-error
path is unchanged: it records status 2 and still frees the table; injected join
failure is outside this experiment's proof.

There is one private state difference: startup `wait()` stores `stopped=1`
instead of leaving the original initial zero. Public `go` already clears it
before publishing work. A direct search caller that follows main-style startup
and bypasses `go` must explicitly clear it. This is declared rather than treated
as identical inactive-state behavior.

## Frozen inputs and reproduction

`control/` contains the nine exact historical entry files. Their old
`build.py`, `fresh.py` and `verify.py` are preserved provenance, not invoked by
this producer. `helpers/` contains the five exact SHA-pinned producer helpers;
`tests/` contains the two exact existing black-box helpers. `control-inputs.json`
binds their raw and LF-normalized bytes and original source paths. No future
canonical file is a build input. This folder's `.gitattributes` preserves LF.

```sh
python3 -I -B engines/experiments/tiny-a-startup/build.py \
  --out /absolute/new/external-output
```

The producer requires a new directory outside Git. It checks all historical
control identities, copies its full required closure before importing helpers,
specializes and compiles each form twice, preserves compiler diagnostics, and
counts the complete 77-byte shell prefix plus LZMA-alone stream. Strict Python
decode and independent `lzma -dc` restoration both require exact bootstrap
bytes. It never starts an engine.

The fixed target is Ubuntu 24.04.4 x86-64, GCC 13.3.0, binutils 2.42, glibc 2.39,
Python 3.12.3 and xz/lzma 5.4.5. Native argv remains
`cc -Os -x c - -o x -s`; the existing glibc domain is retained. Resources remain
2 search workers, TT_BITS=18 and PLY=128. There is no new dependency or public
option. The transport remains LZMA1 preset 9 extreme, lc=2/lp=0/pb=0, no check,
64 MiB dictionary and the same unknown-size/end-marked ALONE header.

| Candidate member | SHA-256 |
| --- | --- |
| Readable C | `71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734` |
| Compact C | `f69044dc9ad2869bd3583308ef446a67f3afa6b31b36e7daade6a6b8cd9a3e6a` |
| Stripped ELF | `84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a` |
| Complete file | `5da238b8f2cc622e5f71a2da07a4f3a787c6679fa29f78b27546800174578527` |
| Restored Python bootstrap | `53cd5d2cf78c8f779744d48f597a797b08c6df12d11cb1967d52dbf37fef9e96` |

## Evidence boundary

The first producer receipt is outside Git at
`/home/stemxstudio/rove4k-tiny-a-startup-first-20261020/build.json`; the
standalone repetition is under
`/home/stemxstudio/rove4k-tiny-a-startup-reproduce-20261020/`.
`body-bindings.json` and `readable.diff` preserve the exact three-site change.
The 16,374-byte board/TT/search/think prefix is byte-identical at SHA-256
`9c0aba3b85cb8d36905c81d1bef5135722fcf71e4f7983374c7f1c7ae7a17f95`.
The text/query/result, normal wait/GO/parser, and main input/shutdown tails are
also exact. Historical algorithm/rule/query receipts are reused only through
these unchanged source boundaries; they are not newly executed tests of this
candidate. Fresh startup and actual wrapper receipts are separate. No strength,
games, NPS, scale or whole-plan completion claim is made.

`verify.py` binds the first-cost receipt and selected readable/compact/ELF/whole
hashes before launch, then starts exactly two actual selected wrappers:

```sh
python3 -I -B engines/experiments/tiny-a-startup/verify.py \
  --build /absolute/first-cost-output --out /absolute/new/runtime-output
```

The fresh receipt at
`/home/stemxstudio/rove4k-tiny-a-startup-runtime-20261020/runtime.json` passed
18 individually attributed epochs across quit and EOF sessions. It observes
three stable preinput TIDs, the exact deleted `/proc` executable, absent private
restoration paths/helpers, white/black zero-clock results, two long GO
replacements and two active position/reset fences per session. Queued `isready`
responses separate each previous legal result from the replacement/new root.
The final active epoch in each session closes through one legal result,
successful process wait, joined readers/sampler, direct pipe EOF, and absent
owned PID/TID/observed-descendant identities. Cleanup is empty. CPU observations
establish active work only; cancellation causality remains unproven. The
black-box observations do not claim to intercept native `pthread_join`; actual
join-call observation belongs to the separate startup diagnostic scope.

`phase-check.py` separately compiles `phase-contract.c` once and runs exactly
five controlled startup schedules. The diagnostic includes the unchanged
candidate source and interposes pthread/input/free calls with separate
condition gates; none of these hooks is part of the shipping source or size.
It checks that the included text equals the exact frozen control transformed by
`transform.py`, and pins both inputs before compilation.

```sh
python3 -I -B engines/experiments/tiny-a-startup/phase-check.py \
  --candidate /absolute/first-cost-output/candidate/engine.c \
  --out /absolute/new/startup-phase-output
```

The fresh receipt at
`/home/stemxstudio/rove4k-tiny-a-startup-phase-20261020/results.json` passed its
one compile and five modes without retries or source edits:

| Diagnostic mode | Witness | Status |
| --- | --- | ---: |
| success-early | Both arrivals precede main wait; persistent pending zero admits input | 0 |
| success-late | Main sees positive pending and enters real wait before worker 1 arrives | 0 |
| fail-0 | No created worker; no startup wait or protocol input | 2 |
| fail-1-early | Worker 0 has arrived/idle-waited before second create fails | 2 |
| fail-1-late | Worker 0 enters after real shutdown broadcast, observes quitting, and skips idle wait | 2 |

Every created pthread identity has exactly one observed entry, exit and
successful actual join, with TT free once afterwards. Failed creation never
waits for an uncreated worker. Both successful cases observe pending zero and
stopped one at first input. Startup bestmove output, contract violations,
observed children, survivors and forced cleanup are absent. Independent
read-only C review found no concrete lock-order or lifetime blocker in these
gates. This is bounded diagnostic interposition, not the shipping native image,
TSAN/SAN evidence, a scheduler/race proof, or a join-error guarantee.

Raw receipt SHA-256 values are kept distinct:

| Receipt | SHA-256 |
| --- | --- |
| First-cost `build.json` | `e24de8edf5f33558193d8f0e57b68de4a2eb9bf5f9887be24426f1d072578240` |
| Standalone `reproduction.json` | `d132d82be9ac252cd6bb96b29301e1e180700d1b0dc294e6d70d7f8931285911` |
| Selected-wrapper `runtime.json` | `f13080626ea2e169651c379321de1a69fcfe2061fa458a8c527ba4b031ccb960` |
| Startup-phase `results.json` | `a56a73586870531ce6547917fa62564fd14978564da72679b74de139519f0dff` |

The wrapper runtime receipt's `build_receipt_sha256` points to the first row;
it is not its own file hash. The final external evidence index binds the actual
raw files and every source path. The producer, actual-wrapper verifier and
startup diagnostic are terminal with no owned execution handles remaining.
