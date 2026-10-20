# Tiny A private semaphore pool experiment

The matched complete source entry shrinks from **5,527 to 5,515 bytes**, a
**12-byte reduction**. The shipping C source itself shrinks by 137 bytes before
the unchanged encoding recipe is applied. The result is still **1,419 bytes
above 4,096**; this experiment does not establish 4K eligibility or canonical
adoption. No further pool variants were tried in this campaign.

The previously qualified 5,283-byte artifact is a separate historical control
from a different search/source-renaming co-design seed. It is not this matched
baseline, the 12-byte saving cannot be added to it, and the new 5,515-byte file
is not a new overall smallest entry.

This experiment was authored from the owned Tiny A implementation and local
independent contracts. No external engine source was read or copied. Only the
pool in `main.c` changes: `tiny.h`, `board.c` and `search.c` are byte-identical
to the corresponding owned baseline inputs. Their exact bindings are recorded
in both build reports, the native qualification report and `review.md`.

## Fixed pool and phase ordering

The measured profile creates **two search workers plus main**, once at startup.
The shared TT is also allocated before protocol input. `Worker` is unchanged;
synchronization objects live in a separate `sem_t signals[WORKERS+2]` array:

| Index | Purpose | Initial tokens |
| --- | --- | ---: |
| `[0,N)` | One private job semaphore per worker | 0 each |
| `N` | Previous job and physical output completed | 1 |
| `N+1` | Startup acknowledgement | 0 |

All `N+2` semaphores are initialized before the first `pthread_create`. Each
worker posts one startup acknowledgement before entering its private job wait.
Only after all creates succeed does main consume all N acknowledgements and
begin reading protocol input. A worker need not already be inside `sem_wait`
when a job is posted: its private semaphore retains that token.

`wait()` sets atomic cancellation, takes the completion token and reposts it.
Repeated idle waits therefore leave exactly one completion token. A new `go`
first performs that wait, then **consumes completion to zero before changing any
job field**. Main retains the immutable root board/history, prepares the
deadline/fallback state, resets worker result records, clears cancellation and stores `pending=N` before
posting each worker's private semaphore once. Publication costs O(N) posts;
there is no broadcast, polling loop or per-search thread creation. A fast worker
can consume only its own job, so it cannot steal another worker's execution.

Each worker calls the unchanged `think` once per acquired job. After writing its
own result record, it performs an acquire-release RMW decrement of `pending`.
The RMW chain carries the other workers' writes to the last worker. That last
worker selects the deepest completed result, emits the existing single
`bestmove` frame, flushes stdout, releases its stdio lock, and only then posts
completion. Main acquires that completion before resetting any next-job state.
The generated legal fallback and deterministic lower-worker-ID depth tie remain
unchanged.

Raw stdin can be received while a search is active, and `isready` can be
answered then. Position mutation, TT clearing, a replacement `go`, and DEV
state-reading commands wait for **physical result-output completion**. Whole
input lines retain the existing 32,767-byte payload limit and NUL/overflow drain;
position replay still commits only after every move is legal. Fixed resource
settings, clock parsing, shipping command surface and DEV public fields are
unchanged.

Quit and EOF first wait for the active job and its physical output. Main then
writes `quitting=1`, posts only successfully created workers, joins only those
workers, destroys only successfully initialized semaphores, and frees the TT.
The plain quit flag is published through the private shutdown posts. Source
reasoning for the semaphore and atomic happens-before paths is in `review.md`;
the reasoning assumes `think` returns after cancellation and stdio can progress.

## Failure behavior

| Failure | Required runtime behavior |
| --- | --- |
| TT allocation | Return status 2 before semaphore initialization or thread creation. |
| `sem_init` at index k | Create no threads; destroy the successful prefix `[0,k)` and return 2. |
| `pthread_create` at index k | Skip the N-worker startup barrier; quit, wake and join only the successful prefix `[0,k)`, then destroy initialized semaphores and return 2. |
| `sem_wait` interrupted with `EINTR` | Retry that same semaphore without inventing a token. |
| Other wait error or any post error | `_Exit(2)` immediately. |
| Join error | `_Exit(2)` before destroying or freeing storage that might still be in use. |
| Destroy error | Retain status 2 and continue attempting the remaining initialized entries after all joins succeed. |

Successful creates are counted independently of semaphore initialization. This
also handles a worker that starts after a partial-create failure: its already
posted private shutdown token survives until the worker reaches its wait. There
is no wait for a nonexistent worker's startup acknowledgement.

Fatal synchronization and join errors deliberately bypass explicit individual
joins/destroys. They terminate the process without further shared-resource use;
they are not graceful cleanup paths. Normal and partial-startup teardown have
separate prefix-accounting checks. No continued-operation or recovery claim is
made after a fatal synchronization error.

## Matched costs and independent generation

Both forms use the same source assembly, DEV specialization, no-op counter
removal, lexical compaction, fixed resource literal representation, existing
function spellings, argv string-split expression and selected XZ recipe. There
was no flag, renaming or compression-parameter search in this experiment.

| Measured layer | Mutex/condition baseline | Private semaphores | Delta |
| --- | ---: | ---: | ---: |
| Shipping compact C | 13,541 | 13,404 | -137 |
| Encoded C passed to compiler stdin | 13,110 | 12,913 | -197 |
| Unstripped shipping native image | 26,432 | 26,416 | -16 |
| Complete selected entry | 5,527 | 5,515 | -12 |

The complete entry includes its **75-byte shell prefix** and shared compressed
Python bootstrap/C payload. The selected encoding is XZ/LZMA2 preset 9 extreme,
`lc=2, lp=0, pb=0`, CRC64. The exact selected semaphore file SHA-256 is
`0074f4a0def353e91146a12de1f73392d9c530beea70a81e873c78b289665c00`.

The fixed runtime compiler command is:

```text
cc -Os -x c - -o x -s
```

This command omits `-pthread` and `-std=c11`. In the measured environment, the
encoding gate compares its **entire stripped native bytes** against the compact
source built with the original explicit C11/pthread flags. That equality is a
local measured compiler/libc fact, not a portable compiler assumption. The
actual restored executable imports `pthread_create`, `pthread_join`, `sem_init`,
`sem_wait`, `sem_post` and `sem_destroy` at `GLIBC_2.34`; its recorded needed
shared library is `libc.so.6`.

The first build independently regenerates natives and complete files. A second
fresh build directory then reproduces actual assembled, specialized, encoded,
native and whole-file bytes for both forms. `reproduction.json` records that
comparison and the unchanged header/board/search source bindings. Equal sizes
alone are not used as reproduction evidence.

## Executed evidence and limits

The common external verifier passed **13 groups**: eight DEV groups
(`protocol`, `rules`, `state`, `search`, `lifecycle`, `selfplay`, `eof`, `quit`)
and five groups against the **actual complete selected wrapper** (`protocol`,
`lifecycle`, `selfplay`, `eof`, `quit`). Startup checks observe and retain the
three task IDs. These are finite black-box checks, not an all-position proof.
The common active EOF/quit evidence records work before the signal and a result
afterward; it explicitly leaves cancellation causality unproven.

The actual DEV algorithm check records positive PVS, quiescence, TT-hit, history,
continuation and correction counters. It distinguishes the same placement at
halfmove 99 and 0 with scores `[0,916]`, checks ten dead-material cases, and
observes no correction update for the en-passant-only witness (`42` before and
after). A separate one-worker **PLY=4** build records one ply abort and reports
only completed depth one for the requested depth-two search. These checks are
separate from the pool's lifecycle evidence and do not claim strength equality
between multithreaded schedules.

`qualify.py` freezes its own bytes, the verifier and oracle, the build report,
encoded source, bootstrap, selected wrapper and producer helpers before import
or execution. It validates the full wrapper hash, restricted-literal source and
compiler argv, and unchanged signal/wait/cleanup/fd-exec bootstrap skeleton.
The actual restored **22,664-byte** native image has SHA-256
`de011ee07fb765be47140c755995f01e361ca3dfae8fcb4b1e2e8dbac181a472`,
exactly matching the recorded stripped image class.

That qualification observes three pre-input task IDs preserved through UCI
ready, the same PID executing `/x (deleted)`, no compiler children, normal
`quit` status 0 and empty stderr. Its filesystem observation is specifically
**after UCI-ready**. Cleanup before fd-exec is supported separately by the
unchanged frozen bootstrap source ordering; no independent pre-input filesystem
sample is claimed.

The final independent controlled pool/fault run passed **26 of 26 cases**, built with
`-O2`, DEV enabled, two workers and TT18. `pool-check.py` freezes the four core
inputs and its own C/Python fixture before compiling an interposed translation
unit. The real board/search/runtime bodies remain unchanged; ordinary calls
delegate to the actual POSIX functions while selected calls are gated or fail.

| Controlled evidence | Cases |
| --- | ---: |
| 96 rapid go/stop/position/newgame cycles plus a naturally completed clocked search, with stable startup/lifetime TIDs and exactly 97 results | 1 |
| Quit and EOF after both search workers enter the active job | 2 |
| A real private post before the delayed worker's real wait; a held worker preventing early result; a held done post preventing position or quit; a held real stdout flush preventing position until physical output completes | 5 |
| One injected `EINTR` at each of the four semaphore indices, followed by successful retry | 1 |
| Initialization failure at every semaphore index and creation failure at either worker index, with exact successful-prefix cleanup | 6 |
| Fatal non-`EINTR` wait or post failure at each semaphore index; join failure at either index | 10 |
| TT allocation failure before synchronization/thread initialization | 1 |

The final traces account for **97 generations, exactly one job on each worker
per generation, and 194 jobs total**. Each worker receives 98 private posts:
97 jobs and one shutdown. The held-worker witness explicitly observes the peer's
initial actual wait and later idle wait; it does not infer idleness from sleep.
All owned processes settled with the expected status 0 or 2, without timeout
cleanup terminate/kill. The held-output
case orders the actual flush trace before position commit, then observes a
subsequent job using the newly committed hash. The completion gates show that
receiving result text alone does not release main before the done token. These
are finite, controlled schedule witnesses, not a proof that every race is
absent. Fatal done-post failure retains already emitted output together with
status 2, without treating that partial effect as successful completion.
No ASAN/UBSAN or thread-sanitizer campaign was run for this pool. Destroy failure
handling remains source-reviewed; a destroy error was not injected. Compilation
records one inherited signedness warning in frozen `search.c:35`; no product
source was changed to suppress it.

The initial bounded campaign is preserved as a failed partial report. Its first
seven cases passed; the physical-output case encountered an observer race
between stdout and the separate stderr trace pipe. The harness consumed
`readyok` before the corresponding trace record had been collected. The Python
driver was corrected to wait, with a bound, for its required trace events. No
production source or C fixture changed. The corrected second campaign passed
all 26 cases. The final third campaign repeated those same cases with stronger
initial-idle and per-generation accounting assertions and also passed 26/26;
it is the authoritative report cited here. These records do not erase or
reinterpret the first partial run. The final Python harness SHA-256 is
`cd474550dda804aba5c416df255bad61674cd7a1ca4727563bf3cc3b43e14a66`.

The supported measured domain is **WSL Ubuntu 24.04.4 LTS x86_64**,
`cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`, glibc **2.39**, fixed **two
workers and TT_BITS=18**. The explicit one-worker PLY=4 build is a diagnostic
exception. No 255/508/511-worker run, large-machine scaling, NPS/Elo, training,
AWS, tournament acceptance or A–F completion is established here.

## Reproduce outside the checkout

Run from the repository root in the measured Linux environment. All output
paths must be fresh, absolute and outside the checkout. `sh`, `tail`, `xz`,
`python3` and `cc` are the selected entry's external programs. `readelf`,
`getconf`, the verifier and interposer are developer inspection tools rather
than additional entry-runtime dependencies.

```sh
python3 -B engines/experiments/tiny-semaphore/build.py \
  --out /absolute/external/rove4k-tiny-semaphore-replay-new --argv-form split \
  --selected-control /absolute/external/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --selected-control-sha256 798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645
python3 -B engines/tests/verify.py \
  --manifest /absolute/external/rove4k-tiny-semaphore-replay-new/validation-manifest.json \
  --select semaphore-dev --select semaphore-selected --suite all \
  --out /absolute/external/rove4k-tiny-semaphore-verification-replay-new
mkdir /absolute/external/rove4k-tiny-semaphore-caps-replay-new
cc -std=c11 -Os -pthread -DDEV=1 -DWORKERS=1 -DTT_BITS=18 -DPLY=4 \
  /absolute/external/rove4k-tiny-semaphore-replay-new/semaphore/assembled.c \
  -o /absolute/external/rove4k-tiny-semaphore-caps-replay-new/semaphore
python3 -B engines/compact/tiny-a/check.py \
  --engine /absolute/external/rove4k-tiny-semaphore-replay-new/semaphore/dev/x \
  --cap-engine /absolute/external/rove4k-tiny-semaphore-caps-replay-new/semaphore \
  --out /absolute/external/rove4k-tiny-semaphore-algorithms-replay-new.json
python3 -B engines/experiments/tiny-semaphore/qualify.py \
  --build /absolute/external/rove4k-tiny-semaphore-replay-new/build.json --form semaphore \
  --out /absolute/external/rove4k-tiny-semaphore-native-qualification-replay-new
python3 -B engines/experiments/tiny-semaphore/pool-check.py \
  --frozen /absolute/external/rove4k-tiny-semaphore-replay-new/frozen/semaphore \
  --out /absolute/external/rove4k-tiny-semaphore-pool-replay-new
python3 -B engines/experiments/tiny-semaphore/build.py \
  --out /absolute/external/rove4k-tiny-semaphore-rebuild-replay-new --argv-form split \
  --selected-control /absolute/external/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --selected-control-sha256 798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645
```

Compare the two builds' actual bytes, excluding their path-dependent JSON:

```sh
python3 - <<'PY'
from pathlib import Path
first = Path('/absolute/external/rove4k-tiny-semaphore-replay-new')
second = Path('/absolute/external/rove4k-tiny-semaphore-rebuild-replay-new')
files = ('assembled.c', 'dev/main.c', 'dev/x', 'original/main.c', 'original/x',
         'compact/main.c', 'compact/x', 'encoded/main.c', 'encoded/bootstrap.py',
         'encoded/xz/x', 'encoded/gzip/x', 'encoded/bzip2/x', 'encoded/xz-selected/x')
for form in ('baseline', 'semaphore'):
    for relative in files:
        if (first/form/relative).read_bytes() != (second/form/relative).read_bytes():
            raise SystemExit('rebuild differs: ' + form + '/' + relative)
print('all declared source, native and complete-file bytes match')
PY
```

Measured reports remain outside Git:

```text
/home/stemxstudio/rove4k-tiny-semaphore-first-20261020/build.json
/home/stemxstudio/rove4k-tiny-semaphore-verification-20261020/results.json
/home/stemxstudio/rove4k-tiny-semaphore-algorithms-20261020.json
/home/stemxstudio/rove4k-tiny-semaphore-native-qualification-20261020/identity.json
/home/stemxstudio/rove4k-tiny-semaphore-rebuild-20261020/reproduction.json
/home/stemxstudio/rove4k-tiny-semaphore-pool-contract-o2-third-20261020/results.json
```

The final Windows evidence destination is
`C:/Users/강민수/Documents/Codex/rove4k-tiny-semaphore-20261020-evidence/`.
The retained export contains `summary.json`, the build and validation manifest,
common verification, algorithm and cap profiles, actual native identity,
independent rebuild/reproduction, the corrected second and strengthened third
pool reports, all 26 final case traces, the initial seven-case partial report,
the harness-observation note and source review. It also contains the actual
5,527/5,515-byte baseline/semaphore wrappers and their shipping C, encoded C and
decoded bootstrap files. The first hold-output trace was never written; the
observation note records that evidence limit, and no replacement trace is
presented as the original. `summary.json` binds these reports and the ten source
files by SHA-256. The source and reports preserve this small matched size
improvement without promoting it into the canonical entry.

The finalized pool-specific Windows evidence is already retained at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-semaphore-pool-contract-evidence-20261020/`:
`o2-third/results.json`, the strengthened proof summary, all 26 case traces,
the earlier partial evidence and harness-observation note. `review.md` includes
the dated source review and final execution addendum.
