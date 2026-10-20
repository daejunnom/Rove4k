# Private semaphore pool: independent source review

Reviewed source: `main.c`, SHA-256
`020696ecdfb4a2cca262667ce7daf6657cb2fd3eec8d2091dd9bc059802c1e2a`.
Date: 2026-10-20. This document records source reasoning. Fault injection,
runtime thread counts, and bounded shutdown require separate execution evidence.

No source defect requiring a change was found in the reviewed pool phases.
The protocol assumes that a scheduled `think` observes cancellation and returns,
stdio output can progress, and successful POSIX calls provide their documented
synchronization. This review does not establish a latency or scaling bound.

`board.c`, `search.c`, and `tiny.h` are byte-identical to the existing baseline:

| Module | SHA-256 | Compared baseline |
| --- | --- | --- |
| `board.c` | `d96f3981b46c13ae152da97ecf884c0a35d81081cd3b242c659ffe39b2d74235` | `engines/compact/tiny-a/board-generated.c.in` |
| `search.c` | `87bec413c4dcbccafd1b9c48e2a4ae878caae11747caf942f36a1036e88c7fb8` | `engines/compact/tiny-a/search.c` |
| `tiny.h` | `e209d37be5c1a8b320c45de87944ed3dc55b8c006713834ad4fd1cfb5eeae19d` | `engines/compact/tiny-a/tiny.h` |

Semaphores are a separate `signals[WORKERS+2]` array; the shared `Worker` layout
and search/board code are unchanged. No chess-core retest is inferred from this
comparison, and no such retest is needed to isolate this pool experiment.

## Phase ledger

| Phase | Source path | Reasoned invariant |
| --- | --- | --- |
| Allocate | `main`: TT allocation and initialization | Allocation failure returns 2 before any semaphore or thread exists. |
| Initialize | `sem_init` prefix loop | Jobs `[0,N)` start at 0, completion `[N]` at 1, startup `[N+1]` at 0. All are initialized before the first thread. |
| Create | `pthread_create` prefix loop | Worker IDs are assigned before creation. `created` counts only successful creates. |
| Startup | `work`: startup post; `main`: N startup takes | Successful startup receives an acknowledgement from every created worker before reading stdin. A worker may not yet have entered its private wait, but the job semaphore preserves a later post. |
| Idle wait | `wait` | Set atomic stop, take completion, repost completion. Only main consumes this idle token, so repeated waits are idempotent and completion remains available. |
| Begin job | `go` | Wait for previous completion, consume its token, publish immutable job fields and reset worker result records, set `pending=N`, then post each private semaphore once. Posting work is O(N). |
| Execute | `work` | Each worker consumes only its own token and calls `think` once. A fast worker cannot consume another worker's work. No per-job thread or polling loop is created. |
| Finish | last `pending` decrement | The last worker gathers all worker results, emits and flushes output, then posts completion. |
| Stop/reset | `wait` before position, clear, DEV state/verification | Main changes shared board/history/table/configuration only after physical stdio flush and completion acquisition. |
| Quit/EOF | final `wait`, then shutdown | Finish current output, publish quit, post only created workers, join only created workers, destroy only initialized semaphore entries, then free TT. |

## Publication and race reasoning

Successful semaphore and thread synchronization calls establish memory ordering
under [POSIX memory synchronization](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap04.html#tag_04_15_02).
The job's non-atomic board/history/deadline/fallback fields are written before
each worker's private post and read after that worker's successful wait.

Every worker writes only its own result record, then performs an acquire-release
RMW decrement on the same `pending` atomic. Each RMW reads the preceding atomic
modification; the acquire/release chain carries prior worker writes to the last
worker. Consequently the last worker may read all result records in `result`.
Its completion post occurs after `printf`, `fflush`, and `funlockfile` return.
Main acquires completion before rewriting any next-job data or result record.

The non-atomic `quitting` is safe under this phase ordering. Its reads for the
previous job happen before those workers' RMW completions, the completion post,
main's completion acquisition, and main's write of `quitting=1`. Each future
read follows acquisition of that worker's shutdown post, which is sequenced
after the write. On partial startup no job is published; the initial quit write
is likewise followed by a private shutdown post before any worker reads it.

Private job and completion tokens never exceed one in an admitted phase. Startup
may collect N acknowledgement tokens, all consumed only after every create
succeeds. A completed job may post completion before main starts waiting; the
token persists, so that late wait has no lost-wakeup window. Worker idle behavior
is a blocking wait. `take` retries only `EINTR`, as allowed by
[Linux sem_wait documentation](https://man7.org/linux/man-pages/man3/sem_wait.3.html).

## Failure and teardown audit

| Failure | Source behavior | Remaining proof obligation |
| --- | --- | --- |
| TT allocation | Return 2, no initialized synchronization object | Inject allocation failure and observe no semaphore/thread calls. |
| `sem_init` at index k | Skip creation, destroy successful prefix `[0,k)`, return 2 | Inject every index; failed/uninitialized entries must never be destroyed. |
| `pthread_create` at index k | Bypass N-worker startup barrier; quit/post/join only successful prefix `[0,k)` | Inject k=0 and k=1; do not wait for a nonexistent startup acknowledgement. |
| Wait interrupted | Retry the same semaphore; no job or completion token is invented | Inject finite `EINTR` before success at all semaphore roles. |
| Non-`EINTR` wait or post failure | `_Exit(2)` | This deliberately terminates immediately and bypasses explicit joins/destroys. It must not be described as graceful cleanup. |
| Join failure | `_Exit(2)` | Do not free shared storage while a thread's lifetime is uncertain. |
| Destroy failure | Record status 2 and attempt the remaining initialized entries | All joins already succeeded before any destroy is attempted. |

Destroying a semaphore with a blocked waiter is invalid, so the join-before-
destroy ordering is material; see
[Linux sem_destroy documentation](https://man7.org/linux/man-pages/man3/sem_destroy.3.html).
No semaphore is copied or moved, consistent with
[POSIX sem_init requirements](https://pubs.opengroup.org/onlinepubs/9699919799.2008edition/functions/sem_init.html).
Fatal synchronization exits are separate from normal and partial-startup
teardown: the source does not attempt to continue or reuse its shared memory
after such a failure, and the review does not claim individual object cleanup.

## Execution checklist recorded at initial review

Use an interposer confined to a test translation unit and delegate ordinary
calls to the actual syscalls. Keep the real pool bodies unchanged. Required
cases are rapid generations; stable startup and lifetime TIDs; a stored job
token posted before the delayed worker enters its real private wait; delayed
worker completion; output held before completion posting; quit and EOF during
clocked/infinite work; all initialization and partial-create failures; finite
EINTR retries; and bounded fatal wait/post exits. Trace successful initialization,
creation, joining, and destruction to prove prefix accounting. The candidate's
first size comparison is separate from these correctness proofs.

## Execution addendum: 2026-10-20

The checklist above was completed by the bounded O2 fault campaign:
`/home/stemxstudio/rove4k-tiny-semaphore-pool-contract-o2-third-20261020/results.json`.
The Windows copy is
`C:/Users/강민수/Documents/Codex/rove4k-tiny-semaphore-pool-contract-evidence-20261020/o2-third/results.json`.
Every case retains its stdout, JSON event trace, exact command, PID, status and
cleanup observations outside Git. All 26 cases passed; all owned processes
terminated with the expected 0 or 2. No timeout cleanup terminate/kill was used.

The nine phase/lifetime groups cover fixed pre-input three-thread startup,
96 GO/stop/position/new-game cycles plus one clocked search, active quit/EOF,
token-before-wait, a held worker, held completion before position/quit, held
physical stdout flush before position publication, and EINTR at every role.
The 17 injected-fault groups cover all four initialization indices, both
thread-creation indices, all four wait/post roles, both join indices and TT
allocation failure. Successful initialization and creation prefixes are
matched to exact destroy and join prefixes. Fatal done-post failure retains
its already emitted info/bestmove together with exit 2, without promotion to
success or a claim of explicit per-object cleanup.

Trace accounting proves 97 publications numbered 1 through 97, exactly two
jobs per generation (worker indices 0 and 1), and 194 jobs in total. Each
worker receives 98 private posts: 97 job posts plus one shutdown post. The
held-worker case explicitly establishes its peer's initial actual wait, one
job, and a second actual idle wait before release. The stored-token case
records a successful real private post before entry into the real wait.
Output-hold cases observe the next input owner's completion wait while both
position commit and GO publication remain absent; after release, real stdout
flush precedes the position commit, and the next publication carries that
committed position's hash. Raw stdin receipt is not forbidden by this contract.

Reviewed runtime SHA-256 remains the value at the top of this document.
Fixture SHA-256 is
`d213474eacb5dcadb0b649f637609e6a91b0e3e4e0728e332fddb1861512d8a4`;
final harness SHA-256 is
`cd474550dda804aba5c416df255bad61674cd7a1ca4727563bf3cc3b43e14a66`.
No product source was changed by fault injection. The fixture includes the
frozen board/search modules, then macro-interposes only runtime calls; ordinary
calls delegate to real syscalls and no fixture thread is created.

An earlier harness run stopped after seven passing cases because stdout and
stderr were drained independently and a trace was inspected before it arrived.
It is retained as partial evidence. The fix explicitly waits for each required
trace event, and the final run also strengthens initial-idle and per-generation
accounting assertions. The first failure was not a product-runtime defect.

The campaign used WORKERS=2, TT_BITS=18 and DEV=1, with no sanitizer or race
detector. It makes no 256/509/512-thread scaling, performance, or engine-strength
claim. Compilation reports one inherited signedness warning in frozen
`search.c:35`; no product change was made to suppress it. Generic historical
trace `value` fields are not all pending counts: only role-specific job/idle
events and their sequence/count assertions support the phase proofs.
