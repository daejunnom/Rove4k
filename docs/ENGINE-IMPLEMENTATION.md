# A–F engine implementation checkpoints

The full implementation scope is recorded in [the accepted plan](ENGINE-PLAN.ko.md).
The current user request excludes training and AWS connections. Frozen model
inference and lossless model storage remain in scope; trained strength is not claimed.

## Current acceptance state

The latest fully verified core is `de5676dcbc498d77477c66064aca926633c851ff`.
Its [Linux CI](https://github.com/daejunnom/Rove4k/actions/runs/39339036826)
passed both C and Rust jobs. The immutable local rebuild passed 144/144 behavior
groups, independent byte reproduction of all 24 native forms, and four bounded
A/F C-versus-Rust games. The sections below preserve earlier checkpoint results
as history; they do not override this newer evidence.
The later source/tooling checkpoints `5e24f2a` and `a681ff8` also pass both
language jobs in their respective exact-head CI runs
([5e24f2a](https://github.com/daejunnom/Rove4k/actions/runs/39340690254),
[a681ff8](https://github.com/daejunnom/Rove4k/actions/runs/39342301394)).
The compact-portfolio checkpoint `830eaa0` also passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39345975382),
including the new standalone D checks and Rust structural unit/reproduction path.
The process-lifetime follow-up `df5c1d1` also passes both language jobs and
repository lifecycle checks in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39346330566).
The consumer/layout checkpoint `d7a38d7` also passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39348805876),
including the independent tiny Rust builder, rule, process and clock contracts.
Its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39348805878)
also succeeds. Later local experiments below retain their own exact artifact
proof; this CI result is not relabeled as a run of a future head.
The D-composition/priority/signal checkpoint `147d9e2` also passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39349918237)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39349918247).
The Rust-stream/semaphore checkpoint `b2bf5ce` also passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39351271963),
including the new actual Rust stream, resource-binding and controlled semaphore
steps. Its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39351272214)
also succeeds.
The minimum-UCI/visitor-cost checkpoint `fce70d1` also passes both language jobs
in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39352032977)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39352032876).
The newer locally qualified candidates below retain their exact source and
artifact receipts; that completed CI is not a result for a later head.
The maintained-A/no_std-Rust-D checkpoint `ca3aae5` passes both language jobs
in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39354935832)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39354935728).
That run actually regenerates the 5,207-byte A file and admits both exact
16,824-byte Rust D images before runtime and controlled production tracing.
The maintained-portfolio/A-composition checkpoint `4e3af24` passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39358129123)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39358129198).
It regenerates the 5,140-byte A, the maintained B/C/E/F wrappers and both
maintained C D own-ELFs, then runs their selected files and restored images.
Both no_std Rust D paths also retain their actual runtime/trace checks.
The B/C experiment-source checkpoint `7d86a07` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39359052804)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39359052729).
Its ordinary maintained entries are exercised; the separately recorded B6155
and C5947 experimental qualification is local evidence, not an additional CI step.
The maintained-C-cache checkpoint `829f27d` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39360106393)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39360106274).
This run regenerates the promoted C5947 and executes that exact selected file.
The maintained-A-startup checkpoint `39cab5e` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39362161257)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39362161296).
It regenerates the 5,129-byte A and exercises the maintained entries.
The later finite-D/F/Rust-ingress checkpoint `b2ba5ae` passes both language jobs
in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39364246525)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39364246190).
It actually regenerates and exercises F5407, D7540/7800 and both Rust D16816
production paths. The separately qualified source-spelling experiment retains
its own cost/runtime evidence; it is not an additional CI step.
The maintained-B/C/E-spelling checkpoint `7910a33` passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39365629437)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39365629402).
The C job actually regenerates and runs the promoted B5955/C5723/E5679 entries.
The independent packed-Rust checkpoint is source-only in this CI claim.
The source-composition checkpoint `418435c` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39367412574)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39367412571).
Its B target/alpha, D metadata layout and Rust constructor experiments retain
their separate local proof scopes; these are not additional CI executions.
The maintained-F/qualified-composition checkpoint `8fc4267` passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39368674853)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39368674790).
The C job actually regenerates and executes F5179. The A/F, D phase/composition
and Rust data8 experiments below retain their separate local evidence scopes.
The maintained-A/D checkpoint `1f35a6e` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39370590464)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39370590452).
It actually regenerates and executes maintained A5072 and D7478/7718. The
separately recorded E fusion loss is source/cost evidence, not a CI engine run.
The maintained-A/F-storage checkpoint `23e6482` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39372260910)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39372260921).
It regenerates and exercises A4980 and F5083 with their exact existing native
images. The B dead-bb neutral cost and C composition first cost retain their
separate local evidence scopes; their candidate engines are not CI steps.
The C-proof/D-latch-cost checkpoint `9cf8cdf` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39390557965)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39390557983).
Its new experiments retain their local qualification/cost/failure boundaries;
they are not additional engine CI executions.
The maintained-C-composition checkpoint `034e9d8` passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39391598903)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39391598852).
The C job actually regenerates and exercises the maintained 5,687-byte entry.
The fixed-macro-loss checkpoint `c7be9ea` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39392239296)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39392239338).
The A/F macro experiment remains a local cost-only loss, not a new CI engine run.
The maintained-B-storage checkpoint `2a0d99a` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39393850340)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39393850575).
The C job actually regenerates and exercises the 5,851-byte maintained B entry.
The D-publication checkpoint `1c8be9d` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39395877875)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39395877918).
The new D output-reservation observation remains a separate local runtime
result; the CI does not execute that new experiment or promote its candidates.
The maintained-D/source-cost checkpoint `a3546f1` passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39399550146)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39399550128).
The C job regenerates and executes the new 7,457/7,707-byte maintained D pair;
the separately frozen A/F costs and failed C/E observation remain local results.
The maintained-F/source-composition checkpoint `71a0791` passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39404347515)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39404347797).
The C job regenerates and executes the maintained 5,051-byte F file. Other
source-cost experiments retain their local execution scopes.
The fixed-codec/source-comparison checkpoint `647f04a` also passes both jobs in
its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39405755104)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39405755067).
Its source-only codec experiment is not an additional runtime CI execution.
The maintained-F-scope checkpoint `195b541` passes both language jobs in its
[exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39408227153)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39408227165).
It regenerates and exercises the maintained 4,839-byte F file.
The maintained-A/B/C/E-scope checkpoint `ffb2799` passes both language jobs in
its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39410522104)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39410522081).
It regenerates and exercises A4846/B5558/C5395/E5400/F4839. The separately
qualified context-D experiment and encoder remain local evidence; this CI
still regenerates and exercises the maintained old-codec D7457/7707 pair.
The maintained-context-D/F-member checkpoint `e266ea5` passes both language
jobs in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39413637855)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39413637981).
It regenerates and exercises the new maintained D6401/6614 own-ELFs and F4814,
alongside A4846/B5558/C5395/E5400. Later cost-only candidates remain separate.
The subsequent source-cost checkpoint `03018dd` also passes both language jobs
in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39417816887)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39417816891).
It exercises the same maintained entries; the newly recorded experiments are
local cost evidence and are not extra CI runtime steps.
The following cost-source checkpoint `6cf2ff1` also passes both language jobs
in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39419480599),
[repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39419480600)
and the [NVCompact checks](https://github.com/daejunnom/Rove4k/actions/runs/39419480680).
Those jobs still regenerate the preceding maintained entries, not the later
EP-only F or reset/BCJ D candidates under local qualification below.
The BCJ-cost/ownership checkpoint `b8bb037` also passes both language jobs
in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39420784684)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39420784662).
It still exercises D6401/6614 and F4814; the subsequent normal-source promotion
requires its own exact-head result.

**No family has a verified complete file at or below 4,096 bytes.** All twelve
cores have functional evidence, but portfolio completion still requires source
reduction, D's eligible own-ELF artifact, final candidate comparisons and games,
and selected profile/resource and target-hardware evidence. The first matched
C/Rust structural comparison and the twelve original target512 short searches
now have their own bounded evidence; these do not accept future smaller cores.
Startup-only evidence and small-profile games have the narrower scopes below.

The current maintained local entries are listed here; older tables below record
their historical checkpoints. The fixed local profile has two search workers
plus the controller and TT_BITS=18. These are not final target profiles.

| Family | Complete file | Remaining above 4,096 B | Current source decision |
| --- | ---: | ---: | --- |
| A | 4,766 B | 670 B | Order-independent text profile, shared startup/query, bound names and original ALONE |
| B | 5,546 B | 1,450 B | Incoming-move legal SEE, hybrid attackers/singular, bound names and ALONE |
| C | 5,245 B | 1,149 B | Real AVX2 residual-feature dot, fixed TT/sort/clamp specialization, bound names and ALONE |
| D scalar / HQ | 6,272 / 6,452 B | 2,176 / 2,356 B | Own context ELF, single-step residual leapers, worker reset and guarded BCJ restoration |
| E | 5,366 B | 1,270 B | All 21 untrained coefficients, fixed TT/sort/clamp specialization, bound names and ALONE |
| F | 4,735 B | 639 B | Full-depth MTD(f), shared EP legality, order-independent text profile and fixed ALONE |

The separate Rust D native images are 16,816 bytes each. Their independent
packed experiment retains its own qualification state and does not silently
replace this maintained table.

## Starting checkpoint: 2026-10-20

Base: develop `56bfb5f45bff59a570d3f04f8eba06332d53c052`.
The base contains NVCompact and repository contracts, but no chess engine.
The implementation uses a separate owned feature worktree. Existing checkouts
and completed package release worktrees are preserved.

| Workstream | Implemented evidence at start | Work still required |
| --- | --- | --- |
| A, C and Rust | None | Legal state, incremental bookkeeping, HCE, PVS/QS, TT, histories, correction, SMP |
| B, C and Rust | None | Bitboards, shared attacker calculations, SEE, qualified singular exclusion |
| C, C and Rust | None | Real AVX2 operations, scalar comparison, native build and restoration |
| D, C and Rust | None | Small OS/start path, scalar/HQ, internal ELF restoration and integrated SMP |
| E, C and Rust | None | Frozen integer evaluation and ordering, exact encoding/decoding, inference bounds |
| F, C and Rust | None | MTD(f), lower/upper convergence, stable evaluation and interrupted iteration handling |
| Parallel policies | None | Shared search, explicit tasks, groups, all three PALS stages, hybrid selection |
| Submission artifacts | None | Source/native wrappers, standalone ELF, complete size accounting and reproduction |
| Acceptance | None | Independent move oracle, special moves, search/lifecycle, candidate features, size and bounded games |

Implementation ownership is divided between C, independent Rust, frozen model
data, parallel scheduling, build/packing, and behavioral verification. Shared
interfaces are coordinated before another owner edits a source file. Generated
executables, test logs and archives stay outside the repository.

## Runtime contracts

Shipping builds expose the 4K command subset: `uci`, `isready`, `position startpos
[moves ...]`, clocked `go`, one final `bestmove` per search, `quit` and EOF.
`stop`, `ucinewgame` and unsupported commands are consumed safely. Development
builds may additionally expose FEN, perft, legal moves, state/hash/evaluation,
depth/nodes/movetime and diagnostics. Resource option parsing is outside the
shipping executable.

The search worker count and TT allocation are build inputs. The stdin/control
thread counts toward the process total; a profile with 512 total threads may
therefore contain 511 search workers. Local verification uses small fixed
profiles on the available eight logical CPUs. Profile generation is not evidence
that a 256/509/512-thread target has been run or scales well.

All jobs in one search share its cancellation and original wall-clock deadline.
An interrupted iteration is not a completed bound. Position replacement, reset,
quit and EOF wait for owned workers before their state is reused. Hints,
completed compatible bounds and rule conclusions remain distinct.

## Verification environment

WSL2 Ubuntu 24.04.4, x86-64, glibc 2.39 is available locally. Current tools:
GCC 13.3.0, Python 3.12.3 and Rust 1.97.0. AVX2 is exposed; AVX-512 is not.
WSL execution explicitly selects the existing `stemxstudio` account.
The 2026-10-20 read-only refresh confirms kernel
`6.6.87.2-microsoft-standard-WSL2`, eight visible/affinity CPUs, and Rust through
`/home/stemxstudio/.cargo/bin/rustc` rather than the noninteractive default PATH.
Subsequent Linux build, ELF/syscall, pthread, `/proc`, restoration and process
lifetime checks may use this environment, with their actual artifact bindings.
This is consistent with Microsoft's documented
[WSL2 Linux kernel and syscall support](https://learn.microsoft.com/en-us/windows/wsl/compare-versions).
AVX-512, final server timing, resource behavior and target-hardware scaling
still need their corresponding target environment; eight virtual CPUs cannot
establish 512-core performance.

The Windows managed-worktree `.git` pointer contains a Windows drive path that
Linux Git cannot interpret. Git operations therefore use Windows Git; Linux
builds use a fixed input snapshot and external output directory. Build-intensive
work uses the Linux filesystem, following Microsoft's
[filesystem guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems).
Exact source bytes and LF policies remain explicit when crossing filesystems.
New source builds and execution evidence must identify their actual inputs;
earlier NVCompact package checks do not establish engine correctness.

## Completion accounting

For each family and language, retain separate facts for functional behavior,
final counted file bytes, reproduction, fixed-resource runtime and performance.
Every family needs at least one complete artifact no larger than 4096 bytes;
D specifically needs a self-restoring ELF with no external decoder. Two wrappers
around the same engine do not establish independent C and Rust cores.

Small games are smoke evidence, not Elo or TCEC acceptance. Missing hardware,
unverified scaling or an oversized file remains an explicit outstanding item.
The goal stays active until the full in-scope plan has corresponding evidence.

## First functional checkpoint: 2026-10-20

The local `c-second` build snapshot compiled A–F in C, both original and lexically
compacted sources. The corresponding executable bytes matched for each family.
All six original executables passed the independent process harness: 48 grouped
checks covering known perft counts, special moves, legal move replay and state,
hash/repetition/halfmove bookkeeping, search output, clocks, stop/replacement,
bounded self-play and active-search quit/EOF. This snapshot used one search
worker plus stdin control. It is evidence for that snapshot, not future changes.

The independent review found and prompted fixes to rule-context TT keys,
exhausted clocks and model initialization. The initial failed builds and runtime
observations remain separate from subsequent passing evidence. Rust original A
compiled, but its compacted source exposed lexical token joining defects in the
new compactor; full Rust candidate validation was still pending at this checkpoint.

The frozen E model uses 21 signed coefficients in 26 encoded bytes. Its generator,
signed-16 exhaustive round trip, malformed stream rejection, feature references
and accumulator bounds passed nine model tests. Actual C/Rust consumers initialize
the same parameters; this is an untrained hand-authored integer model.

Outstanding work remains substantial: finish the independent Rust matrix and
algorithm-specific checks; connect and verify all parallel policies in real
engines; move allocation/workers into the startup lifetime; validate shipping
and restored execution; specialize and reduce source; measure complete artifacts;
meet each family's 4096-byte requirement; reproduce selected outputs; compare
features, cross-candidates and bounded performance. Development C binaries at
this checkpoint were 30,768 bytes, and no size eligibility was established.

Completed model work was reassigned to the planned SIMD plus E cross-candidate.
Parallel scheduler protocol tests are supporting evidence; they do not establish
that the full engine uses the scheduler correctly.

## Fixed-pool and semantic checkpoint: 2026-10-20

Both languages now contain their own A–F search cores. A uses incremental HCE
at the actual leaf; B uses legal SEE and a qualified same-ply excluded singular
search; C consumes AVX2; D consumes HQ sliding attacks; E consumes the frozen
evaluation and ordering model; F runs MTD(f) with matching-depth TT intervals
and preserves the lower-bound move witness. These are implementation facts,
with the focused evidence below, rather than final portfolio acceptance.

The startup lifetime includes every search thread, TT, worker history, correction,
PV and scheduler workspace. In both languages the coordinator is worker zero;
the input thread makes the total `search workers + 1`. Repeated searches retain
the same Linux task IDs. The five policies have actual engine integration and
small-profile runtime evidence. Rust still allocates `Vec` objects in board move
generation and play, so startup preparation does not establish allocation-free
search or a fixed total RSS. Target256/509/512 profiles remain compile-only.

The frozen `pool-matrix` snapshot built all 12 candidates from original and
lexically compacted sources. Every form was independently compiled again with
identical resulting bytes for that form. C original/compact files also matched
one another; Rust original/compact files differed and require separate runtime
checks. The external process matrix passed 83 of 96 groups. Its 13 failures were
terminal score/stale root result handling and F's repeated-search horizon
contract. Newer sources fix those causes; that older run remains a failed
snapshot. The first exact-head CI also failed on a model fixture admitted as a
second C main and the terminal Rust cases. Production model input admission and
the fixture suffix have been corrected. Fresh matrix and CI evidence is required
for the new combined source.

Focused current-source evidence includes:

- C A/D: 4,158 legal states per family, 532,224 independent attack queries per
  run, incremental state/evaluation parity and 45 special moves; optimized and
  ASan/UBSan signatures match.
- C B: ten SEE fixtures, cancellation, a real depth-3 TT qualification followed
  by depth-6 singular execution, and excluded-search preservation of TT, board,
  path and learning. Positive controls demonstrate normal continuation, killer
  and correction updates before checking their absence under exclusion.
- C C: 400 actual SIMD evaluations match an independent scalar recomputation.
- C F: three low-branch positions match independent full minimax, including an
  attaining move, TT-retained repeats and cancellation preserving the last
  completed result. Five repeated `go infinite` searches no longer terminate
  early from contradictory mixed-horizon bounds.
- C actual A/PALS, B/loose and F/loose: four-worker lifecycle runs pass ASan/UBSan
  with stable startup task IDs and bounded node consumption.
- Rust: 28 optimized integrated unit tests pass in WSL. D HQ matches independent
  scalar rays over 786,432 occupancy cases; B SEE observes original cancellation
  inside recursion. Terminal reuse and F bound/move witnesses have regressions.

Source work is independent of NVCompact. Conditional specialization, source
reachability pruning, a fixed-policy scheduler and a smaller shipping UCI path
reduced an A complete source ZIP from 12,734 to 9,513 bytes in the first structural
snapshot. Later representations and native forms need their own records. This
remains above 4,096 bytes. The own-ELF decoder executes real restored C/Rust
payloads without an external unpacker, but no complete A–F ELF is size eligible.

The C+E comparison uses identical frozen sources and profile, changing only the
explicit model flag. Runtime-verified minimum complete files are C baseline
12,931 / C+E 13,873 bytes and Rust baseline 20,586 / C+E 20,588 bytes. These
minima can select different packaging forms; matched-form deltas are retained
in the external comparison. Thirty-six shipping searches establish bounded
responses, one final move and clean exit; they do not establish NPS or strength.

Remaining work is the fresh final-source matrix/CI, shipping/restored chess
validation, further candidate-specific source and runtime reduction, at least
one actual complete file at or below 4,096 bytes for every family, D's eligible
own-ELF path, and bounded comparable games/performance. Full target resource
execution and scaling have no evidence on this eight-logical-CPU WSL host.
Training and AWS remain excluded. The full A–F goal stays active.

## Whole-matrix checkpoint: `d31056a`

An immutable Git archive of `d31056a459942369f219bf98e91111af8b6154dd` was built
in a separate Linux directory. All 24 original/compact native forms compiled;
each form's independent second compilation produced identical bytes. The six C
compact files match their original executable hashes and reuse only that exact
runtime evidence. The twelve Rust executable hashes are checked independently.

The final process matrix passed **144/144 groups across 18 distinct executables**:
six C and twelve Rust original/compact forms. Every group checks its actual fixed
startup total of two tasks before UCI input, with stable task IDs through search
and cancellation. Two C/Rust pairs (A and F), each with colors exchanged, also
passed four bounded games. These remain short legality/lifecycle games, not a
playing-strength comparison. The final reports and transcripts are retained
outside Git under `final-d31056a` and `final-d31056a-verification`.

The corresponding [CI run](https://github.com/daejunnom/Rove4k/actions/runs/39335785952)
passed the full Rust job. C stopped before engine compilation because the newly
added standalone scheduler fixture relied on an include-directory flag absent
from CI. The fixture now includes its header relative to its own source, and
the exact CI compile/run command passes locally. Commit `491415d` contains only
that fixture correction. Its [fresh CI run](https://github.com/daejunnom/Rove4k/actions/runs/39336276080)
completed successfully for both C and Rust. The repository lifecycle workflow
also passed for that SHA. This does not cover subsequent uncommitted source work.

Further source reduction is assigned by actual cost: the optional A shipping
board removes unconsumed bitboard/fullmove/material fields while retaining
incremental HCE/hash and exact legal replay; compact search work preserves the
family-specific algorithms; Rust work replaces per-node heap collections with
bounded storage; E compares lossless coefficient representations including their
decoder and consumer cost. None changes the full portfolio completion criteria.

## Coherent TT and bounded Rust storage: `de5676d`

A deterministic mixed-publication example exposed a false hit in the old C
XOR key/payload protocol. A–E now use a full 64-bit key and seven payload bytes
under one exclusive atomic-byte CAS, retaining a 16-byte slot. F's paired
32-byte slot protects both directions under the same lock; key replacement
invalidates both payloads. A busy reader misses and a busy writer skips the
slot. No concurrent plain payload access occurs outside the lock. Optimized
and sanitizer fixtures exercise actual engine publication and replacement,
including eight-thread collision runs. This is a correctness change, not a
notation-only optimization.

Rust now uses a checked 512-entry move list with an initialized prefix and a
101-key reversible history. Admitted positions contain at most sixteen pieces
and eight pawns per side; the conservative pseudo-move bound fits the list.
History older than the retained suffix cannot change the halfmove-100 result;
checkmate still takes precedence. Actual A–F depth-three searches perform zero
allocations after startup. The larger fixed Board is 1,080 bytes, versus the
previous 288-byte heap-backed value, so this is not reported as a Board-size
reduction. A normal B search reaches ply 96 on a 1 MiB worker stack in both
optimized compiler profiles and returns an unfinished result at its limit.

Direct start-position construction removes the shipping FEN dependency. Rust
test bodies now live under `engines/tests/rust`, with unchanged `rustc --test`
entry points, and are absent from production source archives. In a matched A
shipping recipe the complete minimum source file decreases from 21,732 to
18,427 bytes. Frozen input, compiler and actual file hashes accompany each
phase; this remains oversized.

The new immutable native matrix again passes **144/144 groups across eighteen
distinct executable byte streams**, plus four bounded A/F games. Every process
has two startup tasks with stable task IDs. All twenty-four native forms match
their own independent second compilation. The actual archive inputs use CRLF;
their LF-normalized contents match the named Git commit. Reports hash the
actual input bytes and do not assert raw Git-blob byte identity. External
records are `final-de5676d/build.json` and
`final-de5676d-verification/results.json`.

## Controlled structures and complete-file costs

The optional [A mailbox experiment](../engines/experiments/mailbox/README.md)
implements all four real engine combinations, with one frozen source basis,
evaluation, search features and fixed resources:

| A representation | Minimum complete source | Minimum complete native wrapper | Board | Worker |
| --- | ---: | ---: | ---: | ---: |
| 0x88 / copy-make | 13,035 B | 16,000 B | 696 B | 211,936 B |
| 0x88 / make-unmake | 13,378 B | 16,406 B | 696 B | 211,936 B |
| 10x12 / copy-make | 13,053 B | 16,416 B | 664 B | 196,064 B |
| 10x12 / make-unmake | 13,396 B | 16,792 B | 664 B | 196,064 B |

All four agree on the score, PV, completed depth and node count of six
single-worker searches. Eight optimized/sanitizer oracle runs, 72 native
behavior groups, 40 selected whole-wrapper groups and 32 two-worker groups pass.
This records the declared frozen experiment, not automatic acceptance of those
older artifacts as the latest coherent-TT submission.

The [F experiment](../engines/experiments/f/README.md) compares actual C/Rust
paired/single TT storage and previous-depth/same-parity first guesses. The
default remains paired/previous. All four configurations retain full keys,
matching-depth intervals, the attaining lower-bound move, completion-only guess
updates and cancellation. Selected complete files reproduce and pass actual
shipping checks. At 262,144 slots the paired/single TT allocations are C 8/4 MiB
and Rust 6/4 MiB. The measured source files are C 13,167–13,207 bytes and Rust
18,980–18,996 bytes: a smaller TT does not automatically make a smaller file.
Observed C coordinated root rounds and Rust summed worker probes are distinct
metrics and are not compared across languages.

The D scalar/HQ comparison uses exactly the same frozen producer, source,
toolchain, profile and flags except for the attack implementation. All 140
complete artifacts pass startup and independent reproduction. The selected
whole-file costs are:

| D language | Scalar source / HQ source | Scalar native wrapper / HQ wrapper | Scalar own ELF / HQ ELF |
| --- | ---: | ---: | ---: |
| C | 12,995 / 13,152 B | 13,528 / 13,726 B | 20,205 / 20,476 B |
| Rust | 18,960 / 18,962 B | 155,757 / 156,082 B | 248,162 / 248,948 B |

All twelve selected D files now also pass sixty full shipping behavior groups
using clocked go: actual source/native/self-ELF execution, legal results,
replacement, stop, quit and EOF. A separate strengthened rerun pins every actual
file SHA and requires exactly three startup tasks, stable identities and a
three-task peak; all sixty groups pass. The earlier observation-only report is
preserved, not rewritten. Concurrent producer startup observations are not used
to rank performance. All forms exceed the size limit. The validators record
output/signal ordering without proving cancellation causality.

Additional optional C source work shares PVS/QS control, specializes fixed
Loose SMP, removes unreachable production code and narrows proved worker state.
The qualified coherent-TT source minima for A–F are respectively 9,356, 9,953,
9,659, 9,668, 10,176 and 9,546 bytes. Corresponding source/native launchers pass
sixty shipping groups; their final lexical forms execute the same hashed ELF
bytes. This source work does not depend on NVCompact. The new central
`--shipping-operations` integration passes its separate full generation pipeline:
all thirty-six native forms start and reproduce, including independent source
regeneration. The six new operations natives also pass thirty shipping groups
with exact three-task startup and stable task IDs. This integration run does
not create complete wrappers. Its deadline sampling is explicitly per-worker
rather than aggregate.

E storage work retains every coefficient of the untrained model. Six exact
representations have complete-file cost evidence; a 42-byte immutable table
outperforms the 17-byte encoded payload in that frozen recipe once decoder and
consumer costs are counted. The central `--model-format varint|static16` path
freezes its pure source transform and canonical model. Fresh `de5676d` varint
and static16 producers now pass 140/140 artifact startups and reproductions.
Actual C consumers pass coefficient/evaluation/ordering/clamp checks under
ASan/UBSan; both Rust consumers pass sixteen tests using separately hashed
validation fixtures. Selected complete-file costs change as follows:

| E language | Varint / static16 source | Varint / static16 native wrapper | Varint / static16 own ELF |
| --- | ---: | ---: | ---: |
| C | 13,771 / 13,689 B | 14,049 / 13,929 B | 20,928 / 20,764 B |
| Rust | 18,960 / 18,801 B | 156,879 / 156,605 B | 249,903 / 249,367 B |

The twelve selected complete files also pass sixty shipping behavior groups,
with actual hash admission and exact stable startup task sets. Default varint
is retained; static16 is explicit. No coefficient or inference-scale change
occurs. Output/signal ordering is recorded without claiming cancellation
causality.

## Fixed-resource runtime and bounded policy study

An opt-in [target startup harness](../engines/tests/target_startup.py) admits
memory and PID headroom before launching a single process. On the eight-CPU
WSL host, A/F in both languages pass **24/24 startup cases**: totals 256, 509
and 512, each with quit and EOF. Exact task sets remain unchanged before input,
after UCI and after two readiness barriers. All processes exit normally without
forced cleanup. Startup readiness is 0.531–2.179 seconds including the stability
sampling period; maximum sampled RSS is 2,153,512,960 bytes and maximum virtual
memory is 6,547,410,944 bytes. Resource limits, admission facts and actual native
hashes are retained. No search is sent in this campaign. It proves software
startup/lifecycle under oversubscription, not target-profile search memory or
512-hardware-thread scalability. All A–F C/Rust now also compile under all three
target profiles: thirty-six configurations, seventy-two original/compact native
files and seventy-two independently rebuilt files have matching reproduction
hashes. Their central manifests explicitly retain unexecuted runtime fields;
the separate startup evidence applies only to the A/F originals just described.

A separate opt-in `target_search.py` campaign now executes all twelve A–F
C/Rust **originals at target512**, one process at a time. Each completes a short
clocked start-position search and a second search after e2e4 with work observed
before stop or quit. The independent oracle accepts exactly one legal result
per epoch. All 512 startup task IDs remain stable; every process exits normally
with no surviving owned group or forced cleanup. Maximum sampled RSS is
2,179,072,000 bytes; maximum virtual memory is 6,547,410,944 bytes. Admission and
8 GiB AS/DATA, 3 GiB sampled RSS, 60 CPU-second and 45 wall-second limits are
recorded. The initial A/F four cases and later B–E eight cases keep separate
reports, hashes and an explicit combined index. AVX2/AVX/XSAVE were verified
before C's execution. This proves those exact short searches, not arbitrary
depth memory, lower-profile search execution, distinct Rust compact forms or
hardware scalability. A byte-identical C compact may reuse its original's
execution evidence.

The five-policy A study uses four search workers plus stdin, TT bits 18, CPU
affinity 0–4 and one immutable `de5676d` source basis. **180/180 fresh-process
workloads and 26/26 bounded games pass**. Node-budget workloads finish at exactly
12,000 nodes. Every process has the same five startup tasks throughout. Games
contain 1,973 timed plies; six end in checkmate and twenty reach the declared
80-ply limit with result `*`, not a draw. Independent legal replay, clock
accounting, SAN and PGN checks agree. The study does not show that the additional
policy costs repay themselves on these small workloads. Four workers provide
only one TT group, so this is not a cross-group scaling test.

C/Rust policy runs use their actual implementations. Their HCE coefficients,
search heuristics and TT bytes per slot differ; these results therefore do not
isolate a language effect. A separately generated E experiment now aligns the
actual evaluation, ordering, heuristics, TT key/layout and resource policy for a
bounded structural comparison, described below.
No Elo, strength ranking or many-core recommendation follows from these games.

The next work is candidate-specific source reduction, fresh acceptance of
selected new cores, final candidate comparisons, further selected profile
workloads and eligible complete files for every family. Each smaller architecture
retains its own source and whole-file validation. Training and AWS remain excluded.

## Smaller A architecture and shipping command boundary

The optional [smaller A core](../engines/compact/tiny-a/README.md) is now recorded
as readable source plus a separate producer. It shares a forward piece walker
for attacks and generation, relies on the explicitly proved generated-move
precondition inside make, orders definitions before callers and removes only
known no-op shipping diagnostics under complete native-byte identity. The
512-move capacity has a conservative admitted-position proof and checked
overflow; it never silently truncates moves.

PVS/QS, incremental HCE/hash, coherent full-key TT, history, continuation,
correction-controlled reduction and startup SMP remain actual search paths.
Correction does not alter the shared TT's fixed leaf scale. Dead material,
legal EP context, repetition, mate precedence and unfinished ply-limit handling
have dedicated tests. This architecture is A only; it does not claim B–F's
distinct algorithms.

Its measured complete stream is **5,671 bytes**, still 1,575 bytes over budget.
The 75-byte shell prefix and 5,596-byte compressed stream are both counted.
Python bootstrap and C share that stream, so 75 bytes is not the complete
restoration cost. All twenty-seven native/wrapper artifacts reproduce. The
three native forms plus actual selected whole wrapper pass twenty-three
black-box groups; nine packer groups separately exercise byte preservation,
real compiler/argv/environment/I/O/status, compiler-child signal forwarding,
physical exit and cleanup. The producer now emits a hash-pinned
`validation-manifest.json` for those same four executable entries.
The single-translation-unit producer explicitly normalizes CRLF to LF while
retaining original input hashes. Twelve producer tests include LF/CRLF byte
equivalence and guarded declaration failures; the normalization leaves the
already qualified assembled C and complete artifact unchanged.

The separate [tiny-search experiment](../engines/experiments/tiny-search/README.md)
reduces this complete file from 5,671 to **5,419 bytes**, still 1,323 bytes over
budget. It removes a proved unreachable HCE clamp, unconsumed selection-prefix
stores and constant/private argument work, then accepts spelling transformations
only when actual compiled native bytes match. Its guard pins the value and
piece-admission contracts; all 768 piece-square values have absolute value at
most 910, and 32 admitted pieces cannot reach the mate-score band. An unsupported
ply limit fails preprocessing. Six structures across twelve deterministic
positions match score, best move, nodes, complete TT state and learning/path
state; baseline/winner sanitizer runs and the actual selected whole-file
shipping checks pass. Both native and whole-file independent reproduction pass.
These optional tools preserve the unmodified readable smaller A baseline.

Shipping lifecycle tests now send long **clocked go**, matching the approved
minimum interface. DEV retains infinite-search and strict node checks. Reports
distinguish work observed before a signal, output observed after it and searches
already completed before it; immediate legal completion does not establish
active cancellation. These harness changes have clock-only and immediate-result
fixtures plus a current A DEV regression. Broader D/E/operations shipping runs
use their own preserved validator inputs and remain separately tracked.

## Smaller portfolio and structural Rust checkpoint

The new compact cores make every family's specific implementation cost visible.
They are optional, separately generated candidates; the twelve canonical cores
remain available. These local measurements include the entire selected file.

| Family | Smaller selected complete file | Format and actual distinct logic | Remaining over 4,096 B |
| --- | ---: | --- | ---: |
| A | 5,283 B | Source stream; mailbox HCE/PVS, retained learning and SMP | 1,187 B |
| B | 6,283 B | Source stream; incremental bitboards, shared attackers, legal SEE and singular exclusion | 2,187 B |
| C | 6,059 B | Source stream; AVX2 gather/arithmetic HCE used by search | 1,963 B |
| D scalar / HQ | 8,540 / 8,928 B | Standalone syscall native ELF; persistent clone/futex pool and actual scalar/HQ | 4,444 / 4,832 B |
| E | 6,107 B | Source stream; all 21 untrained coefficients in evaluation and ordering | 2,011 B |
| F | 5,551 B | Source stream; exact-horizon full-depth MTD(f) with attaining bound witness | 1,455 B |

A's [encoding experiment](../engines/experiments/tiny-encoding/README.md)
reproduces the 5,419 → 5,303 → 5,283-byte chain. Fixed-resource spelling and
compiler-argument changes preserve exact native bytes within their declared
stripped/unstripped identity classes. Seven bounded XZ settings add a further
20-byte saving. The final whole file passes five shipping groups and actual
restored-image identity, startup-thread and cleanup checks. Its compiler command
`cc -Os -x c - -o x -s` is qualified only on Ubuntu 24.04.4 / GCC 13.3 / glibc
2.39; omitting `-pthread` leaves the real pthread functions and their glibc 2.34
symbol requirements present. This is not a broad compiler/host portability claim.
The 75-byte shell prefix is counted together with the compressed Python/C/argv
payload; it is not the whole bootstrap cost.

[TinyB](../engines/compact/tiny-b/README.md) passes 23 process groups, its
optimized and ASan/UBSan SEE/singular contracts, producer guards and actual
feature/context/EP/dead-material/ply-cap checks. Singular tests verify both real
qualification and a genuinely extended child, and fence excluded-node TT and
learning effects. The selected whole file also restores the exact independently
compiled stdin image, keeps three startup TIDs and leaves no compiler children
or owned temporary files. All 24 complete forms reproduce.

[TinyC and TinyE](../engines/compact/tiny-ce/README.md) pass 56 process groups
across their DEV, original, lexical, selected source and selected native files.
The AVX2 kernel's optimized and sanitizer runs compare 369,255 board positions
and 738,510 evaluations each. Actual completed C search consumes SIMD leaves.
E's production consumer checks 2,007 arbitrary/dense positions against the
independent frozen oracle, including raw/clamped evaluation, ordering and special
moves; actual search consumes both model outputs. Source and native launchers
restore their exact expected images with fixed three-task startup and cleanup.
Their board-oracle reuse is limited to byte-identical frozen board/header code.

[TinyF](../engines/compact/tiny-f/README.md) is an explicit full-depth policy
candidate: MTD(f) probes retain a stable HCE leaf scale, use only exact-horizon TT
cutoffs and publish a lower-bound attaining witness. Selective LMR is absent;
correction learns and affects actual quiet ordering rather than leaf values or
depth. This differs from the selective A/canonical policy and is not presented
as a pure spelling transform. The 5,763 → 5,703-byte structural change preserves
36 single-worker result/state observations and a 3,785-node total. Fixed-profile
spelling/argv plus two bounded XZ settings yield the selected 5,551-byte file.
Its stripped native identity is separate from the unstripped control.

The final proof passes 28 process groups, twelve independent minimax/witness
fixtures, real horizon/QS/root/mate/correction-ordering controls, node-32 and
`PLY=4` last-completed-result retention, and optimized/sanitizer full-key TT
contention contracts. Ten Linux admission/ownership cases reject cross-build,
source/native/input drift and outside paths and reap an actual orphan. The
selected whole file restores its exact expected image, keeps three stable TIDs
and leaves no compiler children or owned temporary files. Earlier audit failures
and the fixes for proof-input freezing and exception cleanup are retained.

[TinyD](../engines/compact/tiny-d/README.md) supplies `_start`, raw syscalls,
guarded worker stacks and a persistent clone/futex pool without libc, TLS,
interpreter or per-search worker creation. The selected `-Oz -flto` six-form
campaign passes 36 process groups and two bounded games. Five positions have
exact scalar/HQ depth-four score, nodes, PV and best move. Actual search and
context/abort contracts, 4,932,096 HQ kernel comparisons per mode/build and
eleven raw-runtime fault probes pass. Scalar/HQ startup-only profiles with 511
search workers pass four quit/EOF cases with 512 stable TIDs; TT bits 18 and no
search make this separate from the canonical large-TT target512 campaign.
Own-loader alternatives are larger at 8,806/9,142 bytes. The scalar ELF contains
7,952 bytes of text, 348 read-only bytes and 240 header/padding bytes. All bytes
count; neither the raw ELF nor its wrapper meets the size gate.

The D algorithm driver now applies a shared aggregate wall deadline and fixed
per-command deadlines, cleans its owned process group and writes failure/partial
transcripts in `finally`. A follow-up also runs compiler/retained-check wrappers
in owned process groups and cleans descendants on every exit path. Seven focused
fake-process cases cover normal replies, continuous info without bestmove,
exit 17, compile-stage failure and actual parent/child timeout/exit boundaries;
all terminate and preserve the intended reports. The original four-case report
and checker remain immutable. This control-flow evidence changes no engine bytes
and does not replace the earlier executable campaigns.

The separate [streaming picker experiment](../engines/experiments/tiny-stream/README.md)
is a retained failure: a shared walker/visited-ordinal design increases the whole
A file from 5,419 to 5,579 bytes. Its real legality, feature, context and shipping
checks pass, but its new plumbing costs more than the removed sorting. It also
changes tie/re-evaluation policy; no speed or strength improvement is claimed.

Rust's [guarded structural generator](../engines/compact/rust/README.md) is
integrated through the explicit `--rust-structural-compact` option. It currently
accepts only A/shipping/loose with the pinned canonical source. The pure transform
removes inactive families, diagnostics and scheduling while preserving effectful
TT writes, frozen evaluation epochs, paired bounds/witnesses and startup/physical
completion barriers. Actual raw hashes and CRLF counts are retained; only the
verified CRLF-to-LF Rust normalization is accepted, and content drift is rejected.

The central producer changes source totals from 88,157 original / 61,773 lexical
to 34,335 structural / 34,341 structural-lexical bytes. Its best complete source
file is **11,645 bytes**; native wrapper and own ELF are 155,028 and 247,102 bytes.
All 56 central artifacts pass startup and independent source/native/package
reproduction. Four selected complete files pass twenty shipping groups with
exact stable three-task startup. Sixteen transform tests include nine compiled
behavior pairs; an additional 44-position driver compares board/evaluation/search
and independent perft. The original LF/CRLF admission failure is preserved.
Earlier owner-recipe 11,675-byte results use a different packaging recipe and
are not silently substituted for these central values. Other Rust families are
not supported by this optional specialization yet.

The manifest loader also fixes compact variants to their own actual SHA rather
than inheriting the original file pin and rejects expanded-ID collisions in both
input orders before starting any process. Twelve metadata-only cases, including
two old-validator defect controls, pass. This does not rerun or replace earlier
engine runtime evidence.

Further structural work is assigned in separate experimental paths: one span
scanner/direct coordinate input path, a tagged 120-square sentinel mailbox, and
a pure bitboard D representation that removes mailbox/HQ adapters. A separate
genuinely Rust tiny core is also being implemented. Each must earn new whole-file
and runtime evidence; no size saving or final acceptance is assumed. All full-key
TT, rule, completed-result and fixed-startup contracts remain part of the work.

## Matched C/Rust implementation and submission costs

The separate [matched E experiment](../engines/experiments/matched/README.md)
uses the same actual 21-coefficient model, PVS/QS, learning/update equations,
LMR policy, total move-order tie, full-key 16-byte TT, identical Zobrist/pawn and
ordered reversible keys, four-MiB allocation and one-MiB search stacks. Both
clear and touch the whole TT before input admission. One or four search workers
run fixed loose sharing; language-specific board/rule implementations remain.
Neither common policy nor identical nodes isolates a causal language effect.

Five hash-overlay tests cover all 1,561 keys and 146 special-move/history states.
Six one-worker cold fixtures agree on every completed score/node count and final
move, while four-worker fixtures require semantic equality and stable five-task
startup without pretending shared-TT schedules are identical. Both profiles pass
sixteen independent black-box groups each.

The bounded timing campaign contains **18 valid pairs / 36 paired fresh-process
runs** across three positions, two profiles and three samples. Its first quiet
window expired after sixteen pairs because dispatch/forwarding consumed most of
the reserved interval. That report remains failed/partial, with its extra C
singleton and incomplete Rust attempt excluded from paired summaries and retained
separately. A second reserved window ran only the missing four-worker Kiwipete
sample indices 1 and 2; it passed and physically exited. Nine measurement functions
and all runtime inputs/native/tool identities are invariant across the helper
selector change. The combined index links the immutable reports instead of
rewriting the failed campaign as success.

At one worker, median parent-observed search wall times for C/Rust are
142.48/185.67 ms at startpos, 224.18/266.20 ms in the opening and 325.00/326.83 ms
at Kiwipete; exact corresponding node totals are 84,834, 92,847 and 88,002. At four
workers medians are 70.52/88.27, 114.71/130.70 and 181.44/162.50 ms, with different
actual work. These are three short local samples of exact DEV speed artifacts,
not a general language, strength or scaling ranking. Process CPU is `utime+stime`
without double-counting threads; its conservative endpoint quantization bound is
20 ms. The supervisor lacks a separate physical core, and RSS is approximate
kernel accounting. Full raw endpoints, affinity, startup, memory and order remain.

A separate size recipe reproduces and executes all sixteen selected role files:

| Search workers | Language | Whole source | Whole native wrapper | Raw native ELF | Own restoring ELF |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | C | 13,942 B | 13,918 B | 34,864 B | 20,811 B |
| 1 | Rust | 18,717 B | 164,362 B | 367,568 B | 253,793 B |
| 4 | C | 13,944 B | 14,043 B | 34,864 B | 20,980 B |
| 4 | Rust | 18,719 B | 165,799 B | 371,720 B | 256,580 B |

The [cost report](../engines/experiments/matched/COST.md) counts every decoder,
header, model and fixed compiler argument. Selected payloads and actual running
images are compared; each role passes clocked play, zero clocks, active stop/quit,
stable startup identities and physical cleanup. Larger measured encodings are
not all runtime-qualified. DEV timing binaries and shipping size binaries remain
distinct; no speed is attributed to these compressed files. Every row is oversize.

## Consumer, source-layout and dedicated-loader experiments

These separately frozen experiments extend the preceding portfolio. They do not
change the canonical C/Rust cores or silently combine separately measured gains.
The smallest new qualified C/E source files are 6,015/6,095 bytes; the dedicated
D own-restoring ELF is 7,665/7,918 bytes for scalar/HQ. All are still oversize.

| Actual experiment | Frozen control | Result | Scope |
| --- | ---: | ---: | --- |
| C startup PSQT gather | 6,059 B | 6,015 B | Same HCE, actual AVX2 leaf |
| C readonly PSQT | 6,059 B | 6,455 B | Retained adverse storage result |
| E unused shipping HCE cache | 6,107 B | 6,095 B | Cache maintenance only; tactical value() remains |
| D direct fixed-Deflate restore, scalar/HQ | 8,806 / 9,142 B | 7,665 / 7,918 B | Complete own ELF, exact admitted native images |
| D direct LZ restore, scalar/HQ | 8,806 / 9,142 B | 8,721 / 9,057 B | Larger than raw native; retained |
| D span input, scalar/HQ native | 8,540 / 8,928 B | 8,476 / 8,864 B | Parser policy changes declared |
| A span input | 5,283 B | 5,523 B | Unselected size regression |
| A tagged sentinel, controlled/new domain | 5,531 B | 5,743 / 5,719 B | Matched readable control, not the 5,283-byte control |
| A moving-side orientation | 5,527 B | 5,559 B | Relative history/tie policy differs |
| D pure bitboard, scalar/HQ native | 8,540 / 8,928 B | 8,800 / 9,088 B | Smaller RAM state, larger file |

The [C table experiment](../engines/experiments/tiny-c-table/README.md) retains
all 832 exact signed-piece/square values. The startup representation adds 3,328
shared table bytes, including 3,352 BSS section bytes after alignment, and 832 HCE
calls before workers. The readonly representation stores the same values in
source. Optimized and sanitizer production-consumer tests, real SIMD search,
all 56 black-box groups, restored-image identity and fixed startup/cleanup pass.
Its small file saving is not an NPS claim.

The [E state experiment](../engines/experiments/tiny-e-state/README.md) removes
only cached HCE from shipping Board and its two unused incremental arithmetic
updates. The capture priority still reads `value()`, so that function stays.
DEV cache/state diagnostics are unchanged. Shipping Board changes 176 →168
bytes, native ZIP 10,164 →10,113 bytes; equal raw ELF lengths do not imply equal
images. Six consumer forms per representation pass 20,000 raw/clamped model
positions, 160,000 ordering cases and 206,389 legal transitions per run, with
matching state/search/learning observations. Both forms pass 28 black-box groups
and actual source/native wrapper image/startup/cleanup checks.

Its source catalog was also replayed against all 23 actual Git blobs. One
provenance JSON has verified 1,503-byte CRLF and 1,462-byte LF encodings; all other
22 inputs match literally. Only those two exact encodings at that one path are
admitted, with actual raw hashes/counts and a separate normalized identity.
Mixed endings, lone CR and content drift fail. The original failure/catalog stay
preserved. Fresh LF baseline/state, archived LF recipe and CRLF production each
reproduce all generated sources, ten native files and 36 wrappers. Prior runtime
evidence is reused only through exact bytes; fresh LF image/startup/cleanup also
passes. Five admission/transform unit groups cover this boundary.

The [span parser](../engines/experiments/tiny-protocol/README.md) decodes external
coordinates, requires production-generator membership and applies each move once.
Replay commits only after all moves succeed. Forty-nine common groups across
eight actual forms, raw-input boundaries, seven production parser configurations,
retained search/context/ply-cap checks and eleven D runtime faults pass. New
ASCII-whitespace, malformed-number recovery and no-argument command handling
are explicit policy changes. D benefits modestly; A does not.

The [sentinel](../engines/experiments/tiny-sentinel/README.md),
[moving-side orientation](../engines/experiments/tiny-oriented/README.md) and
[pure bitboard D](../engines/experiments/tiny-d-bitboard/README.md) experiments
are retained size regressions. Their independent special-move/perft/transition,
hash/HCE/context, actual search, whole-file lifecycle and reproducibility checks
pass within their recorded scopes. Sentinel controlled search matches complete
normalized TT/heuristic/path state; orientation and pure-BB change ordering and
do not claim identical nodes. Pure BB reduces Board 176 →104 bytes and Worker
68,976 →44,400 bytes, while native/own files grow. Its checker now shares the
stable D driver's absolute deadlines, owned-group cleanup and finally-written
failure reports; a separate narrow replay preserves the old proof and matches
the actual algorithm binaries. The reduced RAM does not make it a size winner.

The [dedicated D loader](../engines/experiments/tiny-d-loader/README.md) admits
exact native hashes and geometry, restores original RX bytes at the original
entry and uses zero anonymous BSS. It rejects READ_IMPLIES_EXEC, reserves guarded
address space without replacement, decodes RW then changes it to RX, and never
uses RWX. Four files reproduce and pass pre-entry audits, production image/search/
startup/stdio/quit/EOF checks, twenty shared shipping groups and two bounded
colour-exchanged games. Four malformed decoder controls and fourteen input/layout
admission cases pass. Pre-entry audit executables remain distinct from shipping
files. Auxv, initial brk and executable identity still describe the loader; this
scope accepts only the known static images, not general ELF process equivalence.

Fixed-Deflate payloads are 6,550/6,803 bytes plus 1,115 decoder/header bytes.
Generic LZ controls contain 7,931/8,267 payload bytes plus 875 overhead bytes.
Further progress needs a smaller engine image or a better total representation.
The separate [range-code experiment](../engines/experiments/tiny-d-range/README.md)
tests exactly two intrinsically adaptive lossless profiles without training or
parameter fitting. Its best files are 7,998/8,299 bytes and remain unselected.
Codec/reference/native restore, malformed-frame, guard/ABI and bounded production
startup/search checks pass; no full shared game matrix was run for this loss.

The new [independent tiny Rust A](../engines/compact/tiny-rust/README.md) has a
160-byte mailbox, unified PVS/QS, coherent single-bound TT, private heuristics,
fixed startup pool and one frozen correction epoch per GO. It is a new policy,
not a behavior-preserving rewrite of canonical Rust. Source totals are 33,693
readable / 25,698 lexical / 23,334 DEV-pruned bytes; the selected complete source
file is **9,074 bytes** and native wrapper 145,081 bytes. Every native form and
twelve complete artifacts independently reproduce. Fourteen contracts, actual
shipping/DEV interfaces, both final wrappers' ten shipping groups and twenty
natural malformed-clock completions pass. The clock-presence bug and older
9,067-byte artifact remain preserved before the final fix.

An actual DEV-free production search reaches ply 127 on a one-MiB thread with
zero recursive allocations and aborts without publishing a partial bound. Its
measured CFA components give a representative 669,504-byte deep path, not a
universal async/standard-library stack theorem. Only A has this tiny Rust port;
all canonical Rust B–F cores remain available. CI adds its actual unit/builder/
process/clock checks at a separately named small profile.

The next isolated work covers packed move/priority state, smaller synchronous
startup-pool protocols and a single-stream Rust module layout. Selected D parser
and restoration gains must be combined and measured rather than added on paper.
No family has earned a complete 4,096-byte artifact; final candidate games,
selected-profile resources and target hardware scaling remain outstanding.

## Composed D restoration and worker/priority representations

The [D composition](../engines/experiments/tiny-d-compose/README.md) actually
combines the qualified span-input natives with the unchanged dedicated v3
fixed-Deflate decoder. The two complete files are **7,640 / 7,881 bytes**,
compared with separate v3's 7,665 / 7,918. The 64-byte native reduction thus
saves 25 / 37 bytes in the complete representation. Payloads are 6,525 / 6,766
bytes with the same 1,115-byte header/decoder overhead. Both remain 3,544 /
3,785 bytes above the limit.

Both natives are rebuilt twice from frozen protocol sources and flags. The
original v3 admission really rejects them; a separate known-image admission
pins the new hashes, sizes and entry addresses, with identical BSS, mappings
and guards. Independent layout review, whole-file reproduction, pre-entry RX/
zero-BSS audits and production post-search RX, permissions, fixed three TIDs,
stdio and EOF checks pass. The two new files separately pass ten common
shipping groups and two colour-exchanged twelve-ply games. No old result is
reclassified as proof for the composition. Evidence is preserved outside Git
under `rove4k-tiny-d-composed-20261020`; the external summary hash is
`d98218c08f05a9e39af40016e731aba1d1b02846524a2fb412e45e02868aa0fc`.

The [packed-priority experiment](../engines/experiments/tiny-ranked/README.md)
replaces two local arrays with one widened move/priority representation. The
two complete source files are **5,299 / 5,303 bytes**, both larger than their
exact 5,283-byte control. Priorities are snapped before descendants, compared
without raw-move tie breaking and stripped before every public/TT consumer.
The actual ordered search streams and full normalized TT/learning/path states
match in the bounded optimized and sanitizer comparisons. Negative signed
learning, all promotion bits, two worker IDs and destructive equal-priority
ties are exercised. Twenty-six common groups, retained/context/PLY contracts,
actual restored images, startup, cleanup and independent reproduction pass.
This widens public move lists and some frames; removing an array is not a RAM
or complete-file saving. The two layouts remain unselected.

The [private-signal D pool](../engines/experiments/tiny-d-signals/README.md)
preserves the frozen board/search inputs and uses blocked, thread-targeted
synchronous notifications around authoritative atomic epochs. Its native
files grow 256 bytes each to **8,796 / 9,184**, and generic own-restoring files
grow to **9,008 / 9,363**. It remains unselected. Six actual files pass 36
common groups and two bounded colour-exchanged games, plus retained features,
context/PLY and scalar/HQ search comparisons. Thirteen separate runtime probes
cover rapid generations, pending/stale/wrong-target notifications, inherited
signal state, idle sleep, partial clone failure, interrupted waits, fatal
syscall errors and late shutdown ESRCH. All owned groups terminate. These
runtime-only probes are separate from the real chess executable evidence.
An uninterrupted job requires W+1 targeted sends, so 511 search workers imply
512 such calls; no dispatch-speed or target-hardware scaling claim is made.
The external final index hash is
`d458f2fe14282d9a2dff751ebcec864238fa44314b3224d91474e79041b0d8b0`.

The exact LF working bytes of all 24 new source/recipe files in these three
experiments match their staged Git objects. Their output files, large raw
traces, logs, failure reports and immutable manifests remain outside Git.
Semaphore coordination and the independent Rust single-stream source layout
are still separately owned work until their final qualification handoffs.
Larger source-kernel redesigns are being evaluated because these measured
representation changes have not closed any family's complete 4 KiB gap.

## Qualified Rust stdin source and semaphore completion

The [Rust stream experiment](../engines/experiments/tiny-rust-stream/README.md)
merges the four exact DEV-pruned modules into inline modules, then embodies
the fixed two-worker/TT18 profile and removes only its unused compile-time
number parser. Board, search, runtime and main token contracts are retained;
source locations change and native hashes belong to a new class. Source shrinks
23,334 →22,981 bytes, and the complete file shrinks **9,074 →9,009 bytes**.
The final whole hash is
`d996efd72a4fed56daba9a9e9a560846e4e0b49a4aad76ad9a7702d3c5a821fc`;
an earlier same-size artifact has different bytes and remains separate.
The unchanged four-file ZIP baseline is independently reproduced byte for byte.

The final stream stores source and Python bootstrap in one 8,896-byte payload
plus a 113-byte stub; that stub is not the entire restoration cost. Runtime
uses literal `rustc` from the caller's PATH and no external crate or C backend.
The helper observes compiler exit with `waitid(WNOWAIT)`, retaining leader
identity while draining its process group before the final reap. It saves and
normalizes SIGCHLD for that waitable compiler, then restores the Python-entry
disposition before the engine exec. Decoder-entry signal handling, compiler
status/signals, a leader exiting before its child, inherited SIGCHLD, queued
stdin/argv/environment, temporary cleanup and actual fd-exec are separately
exercised. The shebang shell's earlier signal normalization stays an observed
boundary rather than an assumed Python guarantee.

Two stdin native compiles and all three whole codec forms reproduce. The
selected source is `516aab3e…56e0b`, actual live ELF is `c477f362…e6309`, and
three persistent startup TIDs match the exact selected artifact. The native and
wrapper pass ten shipping groups and twenty natural malformed/missing/zero
clock completions. A diagnostic assembly build is entirely byte-identical to
that selected native. Production CFA components are 4,640 /73,344 /2,240 bytes;
an actual one-MiB worker reaches ply 127 with 128 nodes, no search allocation
and a propagated incomplete result. These are bounded observations, not a
universal asynchronous-stack or hardware-scaling proof. All old failed and
intermediate 9,009/9,121/8,989-byte streams remain preserved. The final external
aggregate is `rove4k-tiny-rust-stream-qualified-20261020-evidence/phase-summary.json`,
SHA-256 `e7ce47d6ce6ac81c24e9028a1cf68802ece90e088f383961191612dc3b7781a5`.

The [semaphore experiment](../engines/experiments/tiny-semaphore/README.md)
changes the condition-variable runtime only, with exact board/header/search
bytes. Its matched readable control is 5,527 bytes and the candidate **5,515**;
the previously qualified 5,283-byte candidate remains a distinct, smaller
control. Its 137-byte shipping-source reduction is not added to that earlier
file. Shared completion starts with one token; GO consumes it, posts one private
token per worker, and the last worker posts completion only after output flush.
Stored tokens and the release/acquire chain retain jobs posted before waits.
Initialization/creation prefixes are destroyed/joined only after ownership
ends, and fatal wait/post paths terminate with status 2.

Thirteen actual DEV/whole-file groups, retained PVS/QS/TT/history/continuation/
correction and context/PLY contracts, actual restored-image identity, fixed
three TIDs, normal physical cleanup and independent source/native/whole
reproduction pass. A separate final 26-case runtime fixture proves generations
1..97, workers [0,1] for each, 194 jobs and 98 private posts per worker including
quit. It explicitly observes initial and second real waits, tokens before a
wait, delayed workers, and physical output before position publication. Partial
init/create, allocation, wait/post/join and EINTR cases terminate as expected;
no timeout cleanup signal was used. Its earlier cross-pipe observation failure
and unavailable unsaved trace are retained as partial evidence; the production
runtime stays unchanged. The final external summary hash is
`48dc518a018a4c7d9cc8570e0167f991b7064f9e1e40bf35edf8cb80fd603a6e`.

CI now invokes the exact production Rust merge/resource bindings, real Rust
bootstrap fixtures and controlled semaphore runtime phases on a Linux Git
checkout. Registration alone does not prove a new-head CI success; the local
selected whole-artifact proof and old `147d9e2` CI keep their own identities.
The qualified Rust stream driver originally has 391 CRLF endings and no lone
CR. Before Git integration it is canonicalized to LF with exact Python AST and
compiled-bytecode identity. Its original raw receipt stays preserved and the
new source encoding has a separate receipt. Runtime inputs and all producer
bytes remain unchanged; new-head CI executes the canonical driver itself.
The next source work is a minimal shipping UCI policy, one fused generation/
search kernel and an independent no_std scalar/HQ Rust D. Training and AWS stay
excluded. Every family still needs a complete <=4,096-byte submission, final
selected-profile/resource/strength comparison and target-hardware evidence.

## Minimal shipping policy and failed visitor fusion

The [minimal UCI candidate](../engines/experiments/tiny-uci-min/README.md) is a
qualified **5,223-byte** whole source launcher, 60 bytes smaller than its exact
5,283-byte control and still 1,127 bytes above the size limit. Compact source
is 11,351 →11,192 bytes; the 22,664-byte native length stays equal while its
bytes change. Source/native/whole generation is independently repeated twice.
The final whole SHA-256 is
`fbb416160e98beb8f10cc5fec6b3792f4591055626344dcbe31cb50ffce41ee9`.

This is a declared protocol policy change. Shipping emits `uciok` without id,
consumes stop/newgame without cancellation or TT reset, and gives bare go a
1,000-ms budget. An unsupported infinite token leaves that same finite default.
The own-side clock calculation stays unchanged. Go/position/quit/EOF retain
internal cancellation and physical completion fences; startup still initializes
all TT locks. DEV preprocessing and native bytes remain exactly unchanged.
This distinction follows TCEC4k 7.9-7.11 and the accepted plan's consume-only
minimum, not the full general UCI behavior. A finite default does not imply a
strict wall-time upper bound because deadline sampling is every 256 nodes.

All eight actual native/wrapper process runs pass with exact image hashes,
three stable pre-input TIDs, only stdio descriptors, no compiler children or
temporary files, next-job/position fences and quit/EOF physical exit plus
reader join. The final driver also passes twelve independent oracle perfts
and one strict unchanged DEV session. Thirty separately modeled dispatcher/
budget/TT-sentinel cases have no physical worker threads; their state/TT claims
are not expanded to the actual threaded observations. Ignored-control CPU
progress and result ordering are not reported as cancellation causality.
The old stronger common checker stays unchanged. Original failed producer
directories and their corrected exact DEV comparison are preserved. The
external freeze receipt is
`b99b6f9aa911df3d3e0a3d17e4364fabcf36dd367f0ff957352f623822f4203b`.

The [visitor fusion](../engines/experiments/tiny-fused/README.md) removes real
gen/make/first/match consumer boundaries and the move/score lists, but its Fact,
Visit and mode glue makes compact source grow **11,351 →12,655 bytes** and the
whole file **5,283 →5,739 bytes**. It is an unselected negative result, with no
post-result sweep or full test-count campaign. Its fixed TT/best-tactical/
tactical/best-quiet/quiet staging is an explicit move-order/LMR policy change.
Independent precompile review corrected material-draw/PLY precedence and a
quiet TT hint prematurely ending QS captures. Bounded optimized and sanitizer
production fixtures cover those boundaries, all four promotions, legal EP,
castle/hash/context transitions, third repetition, invalid-input rollback,
actual positive learners and raw prefix uniqueness. One actual whole wrapper
passes four clocked/cancelled epochs with exact restored image, startup TIDs,
cleanup and physical join. This evidence is intentionally narrower than the
canonical full suite. The external index hash is
`5e0c9a82414453af695d9fec3a6c3c3409d3acef70c5d1ad5a1e970730c4383e`.

Source work continues with a direct kernel that avoids that context layer,
minimal-UCI B/C/E/F candidates, a fresh-checkout canonical A source/recipe, and
an independent no_std Rust D scalar/HQ runtime. Each remains separately owned
until its actual final artifact and relevant runtime proof are handed off.
No family yet has a complete 4,096-byte file; source reduction, selected
profiles/resources, final strength comparison and target hardware remain open.

## Maintained minimal source and portfolio policy checkpoint

The smallest locally qualified complete files now have the following costs.
These are measured complete launchers, including their decoder/bootstrap, not
the lengths of a C source fragment or a restored native executable.

| Family | Qualified whole file | Remaining above 4,096 B | Selected local change |
| --- | ---: | ---: | --- |
| A | 5,207 B | 1,111 B | Minimal UCI and generated-move preconditions |
| B | 6,219 B | 2,123 B | Minimal shipping UCI |
| C | 5,955 B | 1,859 B | Startup PSQT gather plus minimal shipping UCI |
| D scalar / HQ | 7,640 / 7,881 B | 3,544 / 3,785 B | Previously qualified own-ELF composition |
| E | 5,899 B | 1,803 B | Capture-prior removal plus minimal shipping UCI |
| F | 5,479 B | 1,383 B | Minimal shipping UCI |

The [maintained A entry](../engines/compact/tiny-entry-a/README.md) is now a
readable canonical program and a fixed recipe. Its ordinary checkout inputs
are nine owned files and five SHA-pinned build helpers; two pinned test helpers
complete its verification closure. It reads no historical build/report or
generated engine directory. A fresh sixteen-file Git tree was archived and
extracted twice, and both extracted builders independently repeated generation,
compilation and packing. Compact C is 11,148 bytes, native ELF 22,664 bytes and
the whole launcher 5,207 bytes, with whole SHA-256
`085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36`.
The fresh source tree is `a6cb91a7c6441977c6525ebf279b6639d0163689`;
its external final index SHA is
`8c4ad6f919f5737005acf289c42c53c083410a0989eded752e00c49a35590470`.
Two actual selected-wrapper sessions bind the regenerated native image,
three stable pre-input TIDs, legal white/black/bare-go results, removed
restoration directory/helpers and active quit/EOF physical exit with one final
legal result. Historical broader proof is reused by exact identity. The
previous 5,223-byte canonical source/archive and evidence remain preserved.

The final A change keeps the king-capture and move-list-capacity guards in DEV
and omits them only in shipping. The [precondition proof](../engines/experiments/tiny-preconditions/README.md)
traces every shipping make/add consumer: only generated moves from startpos
histories enter make, and TT hints only reorder or cut search. The preceding
legal transition preserves the king-safety invariant; the actual pseudo-move
bound is `10 + 15*27 = 415 < 512`, including all promotions. Own-king safety,
EP/castle checks and transactional replay remain. This removes 44 compact C
bytes and 16 whole-file bytes; DEV source and native bytes are identical.
Eight O2/sanitizer/PLY forms, eight actual native/whole runtime sessions and
fifteen separate modeled clock cases pass. The final runtime driver also
corrects its owned-process cleanup on aggregate alarm; the deliberate timeout
fixture observes leader and grandchild disappearance. Neither that fixture
nor active-search exit establishes arbitrary nested cancellation causality.

The [B/C/E/F minimum-UCI experiment](../engines/experiments/tiny-uci-portfolio/README.md)
reproduces each old control before applying the same qualified command policy.
Whole-file changes are B 6,283→6,219, C 6,015→5,955, E 6,095→6,031 and
F 5,551→5,479 bytes. Everything outside go/main is byte-identical to each
readable control, and DEV preprocessing/native pairs remain exact. Eight actual
whole-file sessions and four strict DEV sessions pass. New focused B/C core
checks and thirty modeled B/F dispatch cases have separate scopes; unchanged
SEE, singular, SIMD, model and MTD(f) coverage is reused only through exact
source/harness/image bindings. The final external receipt SHA is
`71d1a8f86d09364fbe9f1f0a2138b5c87a8361a86b46e6756a182f754c9b9f9d`.

The [E ordering change](../engines/experiments/tiny-e-order/README.md) removes
the old HCE/PST capture prior because the unchanged frozen model already has
its material-order term. It keeps the 500,000 capture class, promotion/TT
priorities, all 21 untrained coefficients, model leaf/clamp and full model
ordering sum. This explicitly changes move order, later reductions and
learning, so no unchanged-search or stronger-play claim is made. It reduces
compact C 14,896→14,547, native 26,504→26,440 and whole file 6,095→5,959 bytes.
Six actual production forms per policy pass O2/sanitizer model, legal-transition
and priority-consumer checks, and both policies pass their 28-group bounded
process suite. Selected source/native restorations have exact image/startup/
cleanup proof. The final metadata-only clarification preserves every tested
engine byte, bound by external receipt SHA
`ee0d1015fb2090a5fd52349dfa5a09518fa5d5adb99a69a96b4743459f286332`.
The separate [actual composition](../engines/experiments/tiny-e-compose/README.md)
reproduces the 5,959-byte order control and 6,031-byte UCI control, then measures
5,899 bytes, not the 5,895-byte arithmetic prediction. Compact C is 14,352 bytes
and restored stdin ELF 26,408 bytes. Both transform orders and a separate
whole-function transplant produce the same source; all 23,218 readable bytes
outside go/main equal the qualified order-only core. Two actual whole-file
sessions and one strict ordered-DEV session pass, with exact native/image/TID/
cleanup and physical completion gates. Six earlier model-consumer forms and
positive search/learning proof are reused through literal source/report pins.
The final proof-tool-only fixes keep every tested engine byte identical and
preserve the first runtime record. Final external receipt SHA is
`cbb9f44160caac83d1e52a4dd224513d819c493b519faffb65ff7c9f49d08590`.
Git preserves the exact CRLF bytes of the fixed E-order and E-composition
input-map JSON files through path-specific attributes; other source inputs
are unchanged. This metadata preservation is separate from the frozen
eight-file experiment receipts.

The [direct kernel](../engines/experiments/tiny-kernel/README.md) avoids the
visitor/context layer but still loses: compact C before fixed spelling grows
13,366→13,654, encoded C 11,351→11,876, native 22,664→26,760 and whole file
5,283→5,543 bytes. The five generation stages, frozen rank threshold and worker
file order are explicit search-policy changes. Independent byte reproduction,
bounded legal/attack/transaction contracts, optimized/sanitized positive search
fixtures and one actual whole-file lifecycle pass; no full-suite, strength or
scaling claim follows. This losing architecture is retained as evidence and
does not replace the selected A source.

A single original [source PPM experiment](../engines/experiments/tiny-source-ppm/build.py)
also stops on first cost. Its order-four exclusion model compresses the exact
11,148-byte C to a 4,675-byte frame, but its complete standard-library decoder,
bootstrap reconstruction and launcher produce 7,483 bytes, 2,276 bytes larger
than the reproduced 5,207-byte control. Independent reference decoding twice
and intercepted final exec restore the exact C and original bootstrap. There
are zero compiler invocations or engine executions in that first-cost proof;
it supplies no new runtime, strength or eligibility evidence.

## Independent no_std Rust D runtime checkpoint

The [separate Rust D implementation](../engines/compact/tiny-rust-d/README.md)
has its own Linux x86-64 entry, raw syscall/clone trampoline, futex coordination,
guarded worker stacks and assembly memory primitives. It uses Rust core without
external crates, libc, pthread, TLS, interpreter or a C backend. Both actual
scalar and HQ paths independently reproduce **16,824-byte complete ELFs**.
HQ SHA is `2c84c684d840ad7e7f0567b2b76d9c28693a00f6f95779675fb45ff84c06d3b3`;
scalar SHA is `0c364208165b79d95f146650ec8ae144f1e4cb6427197b80f37f0e97a90a4eb3`.
Static gates inspect an auxiliary unstripped link and require its allocated
sections/addresses/BSS to equal the stripped image, with no unresolved symbols,
dynamic dependency, interpreter, TLS or executable stack.

Fresh ordinary sessions of both actual shipping images pass three-TID startup,
clock/search/stop/position/reset/quit/EOF, cumulative per-GO result totals and
full output EOF. Separate owned-child ptrace runs of the same images hold actual
output and exit syscalls: finished stays old before bestmove output while OUTPUT
is held, and the new generation is published only after the full write with
OUTPUT released. The kernel clear-TID contract is observed before successful
stack unmap. Waitpid notification ordering is a separate observation and is
not used as a substitute for this join. No GO-time clone/mmap/mprotect occurs.
The single main controller owns start/reset/shutdown; this is not a general
pool API safe for concurrent external controllers.

Exact-body std board drivers pass twenty published perft totals per lane,
128 independent positions, 3,590 child transitions, 16,384 attack queries and
148,480 raw HQ/ray cases; full scalar/HQ responses match. Eleven search contracts
per lane retain positive search/learning, coherent full-key/context TT and
completed/interrupted witness evidence. Separate no_std deep diagnostic images
reach the 128-ply abort on the actual guarded 1 MiB stack path and join before
unmap. Fourteen fault images cover failed second clone after one physical
worker exists, worker clock failure after startup and GO, short I/O, retries
and actual lower/upper guard faults. These diagnostic images and the std
allocator probes remain separate from unchanged shipping-image proof.

The actual HQ shipping ELF also equals an auxiliary frame-audit image: search
CFA 4,880 bytes, worker entry 73,200, pseudo generation 2,224 and main 431,952.
The observed deep path and these frames are not a universal stack bound.
Production Rust/assembly/linker bytes did not change during qualification;
first harness failures and final strict runtime/trace verifier fixes are
preserved with the versions that produced each receipt. Final seventeen-file
source/evidence aggregate SHA is
`a79b90ec7deed06cff221b9cfbb94edc722eb101f71a08484d2605a65823c0a9`.
Git integration removes one extra final LF from only the search test fixture;
the old seventeen-file receipt remains historical, with a separate exact
normalization/hook/unit-image receipt. Production sources and runtime evidence
retain their original identities.
No compressed-loader, 4 KiB, strength, NPS or 512-worker scaling claim follows.

CI now builds the maintained A source with its fixed expected bytes and runs
that exact selected launcher from a clean checkout. It also builds/reproduces
both Rust D lanes and invokes actual runtime, production tracing, board and
search-unit checks after explicit expected native-hash admission.
Adding these steps is not a
claim that the new head has passed it. Training and AWS remain excluded;
eligible complete files, final selected-profile resource/strength comparisons
and target-hardware scaling are still required for portfolio completion.

## Maintained portfolio sources and actual A composition

All six selected C implementations now have ordinary maintained source and a
fixed checkout-only recipe under `engines/compact/tiny-entry-{a,b,c,d,e,f}`.
The maintained selected complete-file costs are:

| Family | Complete selected file | Above 4,096 B | Maintained submission form |
| --- | ---: | ---: | --- |
| A | 5,129 B | 1,033 B | Ownership/query source, shared startup phase counter, LZMA-alone |
| B | 6,219 B | 2,123 B | Minimum-UCI source entry |
| C | 5,947 B | 1,851 B | SIMD/PSQT entry with DEV-only HCE cache |
| D scalar / HQ | 7,640 / 7,881 B | 3,544 / 3,785 B | Own self-restoring ELF |
| E | 5,899 B | 1,803 B | Untrained model/order composition source entry |
| F | 5,479 B | 1,383 B | Full-depth MTD(f) source entry |

These are the measured local two-search-worker/TT18 profiles. They are not
final target-profile costs, strength recommendations or 4 KiB acceptance.
The independent C/Rust cores and earlier structural comparisons remain
available; this source promotion does not substitute one language for the other.

B/C/E/F each retain their exact readable program and qualified shipping C,
native, bootstrap, complete file and DEV bytes. Their source closures contain
15/15/15/16 files respectively: nine local files plus only the actual required
build/test helpers. B has no name-replacement stage; C/E retain their own
SIMD/model pipeline and compiler argv; F retains its 34 fixed spellings.
A's spelling, stripped compiler or encoder choices are not imposed on them.
Each closure was archived as an isolated Git tree and extracted twice. Each
extracted builder repeated generation/compilation/packing, followed by two
actual selected-wrapper sessions per family. Image, startup-TID, legal-clock,
restoration cleanup and physical quit/EOF gates pass. Existing broader SEE,
singular, SIMD, model or MTD(f) proof is reused by exact identity rather than
reported as new execution. Final external source receipts are B/F
`13b33f6da3fe434ae17957048f762f89026dfc27b6a14f379267b0e015770a4c`, C
`6bf1a0b9a8c967618409a763f0531bdbe69f5a225c9d380c805245cba1f9a44c`, E
`6a7e5e3c3de7ea3a8d383f8c1d6a4f849a0f86cfda0744eb9881a38086b7e452`.

D retains eight native sources and three loader/codec/linker inputs in its
18-file maintained entry. Its explicit twenty-file archive also includes
LICENSE and the independent oracle. Two isolated extractions independently
reproduce both native images, both complete own-ELFs and the same CHECKPOINT
audits. Eight production cases and four pre-entry audits distinguish the whole
`/proc/exe` identity from anonymous restored RX bytes, then check zero BSS,
guards/W^X, original entry handoff, startup TIDs, stdio/child state, legal clocked
responses and physical exit. The ordinary single-TERM compiler-stall fixture
also verifies owned-process cleanup and retained incomplete reports/output.
Its final source/evidence index is
`7c6b2dd18d72c003c839f228df96639d4cef90d9f9c5c69c880cef7866fe311a`.
Existing kernel/protocol/loader fault proof stays attached to its original
images and verifier versions. There is no new layout or image-class admission.

The [A ownership change](../engines/experiments/tiny-a-ownership/README.md)
unifies first-legal and exact-text move queries and returns the already-made
child. Replay commits that child, and each worker resets its per-job result at
think entry before any claim or pending decrement. Readable C shrinks
25,131→24,921 bytes and compact shipping C 11,148→10,958. Query output must be
non-aliasing caller-owned scratch, discarded on failure. Published GO jobs
preserve their old fallback/results; a direct internal think call with a
preseeded best now clears it. That broader private API difference is explicit.
Three optimized/sanitized query forms check complete child state, exact token
admission, special moves, transactional HISTORY boundaries and both direct
reset cases. Two actual wrapper sessions cover eight repeated/replaced jobs,
position reuse, zero clocks and active quit/EOF. Board and search bodies stay
exact, while the changed boundary has its own proof.

The [LZMA-alone transport](../engines/experiments/tiny-lzma-entry/README.md)
keeps the exact old source/bootstrap/native but reduces 5,207→5,163 bytes.
Its prefix grows 75→77, format/check/padding/index cost falls 58→13 and actual
coded data falls by one byte. LZMA1 replaces LZMA2; this is not just a container
claim, and ALONE has no equivalent XZ CRC64 protection. Strict Python and real
CLI decodes bind the full bootstrap. Two actual selected sessions passed with
the original adapter. Its later input-path-only revision archives the old
verifier/recipe so canonical promotion cannot break the experiment. The new
adapter is statically bound and unexecuted, explicitly reusing the earlier
runtime rather than relabeling it. The PPM losing experiment likewise derives
its old template/prefix only from admitted controls, and repeats the same
7,483-byte result after removing its live-canonical dependency.

The [actual A composition](../engines/experiments/tiny-a-compose/README.md)
preserves and reencodes all three 5,207/5,183/5,163-byte controls, then measures
one fixed combination at **5,140 bytes**, not the additive prediction of 5,139.
The maintained A now contains the qualified ownership program and fixed
77-byte/LZMA1-alone 9-extreme lc2/lp0/pb0/CHECK_NONE recipe. Its native stays the
ownership image, and the new ownership DEV source/native pins replace the old
5,207-byte program's DEV pins. Two fresh sixteen-file source extractions each
repeat every output, then the actual new selected file passes two fresh
quit/EOF sessions. The whole SHA is
`75dc3d610d39bbc0702c6eda219fa0acb4d167c40d3c78e241cf867a33e5a4e7`;
final eleven-source/receipt aggregate is
`85da3ed9dec657baa9e27e0c5ca98394cf66c5753b507b8f1c1ae4506cb38657`.
All prior canonical inputs, archives and controls remain preserved. Active
search exit is observed; cancellation causality is still unproven.

The [Rust affine-HCE first-cost experiment](../engines/experiments/tiny-rust-affine/README.md)
preserves safe indexing and proves all 832 admitted piece/square pairs before
compilation. Function size falls 216→150 bytes, and allocated text/rodata shrink
106 bytes. The unchanged linker absorbs them as padding before data at offset
0x4000, so both complete scalar/HQ ELFs remain 16,824 bytes; readable source
grows seven bytes. It stops at cost without executing an engine or claiming
runtime qualification. This losing whole-file result is not promoted.

CI now regenerates A/B/C/E/F and runs each selected source wrapper, plus
rebuilds both maintained D own-ELFs and checks their distinct restored images.
Those steps pass in the exact `4e3af24` C job; its Rust job and repository
lifecycle also finish successfully at the linked runs above. Later experiments
retain separate local evidence and are not included in that CI claim. No family
yet has a qualified <=4,096-byte file. Further source reduction, actual final
target profiles/resources, candidate-specific games and hardware scaling
remain required; training and AWS remain excluded.

## Focused B target emitter and C cache experiments

The fixed [B target-emitter candidate](../engines/experiments/tiny-b-target/README.md)
reuses the existing `attackers()` path for ordinary generation and SEE capture
enumeration. The exact 6,219-byte control is reproduced; compact source falls
15,566 to 15,456 bytes, native grows 26,592 to 26,624, and the actual complete
file falls to **6,155 bytes**, a 64-byte saving and still 2,059 bytes oversized.
Independent generation/compile/package repeats match. Optimized and sanitized
special-move/SEE/singular/excluded-learning checks, the independent oracle's
15 roots and 207 legal children, and two actual selected-file quit/EOF sessions
pass. Move generation order changes and up to 64 reverse attack queries per
ordinary generation may slow nodes; no performance or strength claim is made.
One byte-identical diagnostic compile accounts for 692,520 worker-stack bytes,
including the new SEE move arrays and same-ply singular frames. Library,
pthread/signal/entry and deepest-path runtime use remain unmeasured:
`whole_runtime_stack_qualified` is false. The original eight-source aggregate
is preserved; adding only the ninth LF policy file changes the final aggregate
to `d3ddcb059e9f5f0739cbf982f07164e928fb88250ff6cb1e981a391def14cdf3`
without rerunning or relabeling earlier execution.

The fixed [C shipping-cache candidate](../engines/experiments/tiny-c-state/README.md)
guards only the unused shipping HCE cache field and its two `put` maintenance
sites as DEV. Shipping source falls 14,244 to 14,206 bytes and actual Board size
176 to 168; native length remains 26,464 while the complete file falls from the
exact reproduced 5,955-byte control to **5,947 bytes**, still 1,851 oversized.
The actual SIMD/search consumers stay unchanged, `value()` remains for PSQT
construction and move priority, and both DEV source/native identities stay exact.
Optimized and sanitized shipping-layout comparisons each cover 160,432 positions,
150,419 legal children and actual TT/draw/mate/learning/PLY contracts. The PLY
fixture installs a real direct-search result into completed fields before the
abort call; it is not a new observation of think publication. Cross-form exact
search scores, nodes and learned tables are not compared. Two actual selected
wrapper sessions bind the new native image, persistent three-TID startup,
legal clocks/bare go and physical quit/EOF. The fourteen-source final receipt is
`67d7dce0b1852f7227f62f87c9b9568c9ebbc365274d182a4515e707200f2d11`.

Both experiments keep their original cost reports separate from later focused
qualification. At their experimental checkpoint the maintained B/C entries
remained unchanged. Neither is accepted as the final profile or for 4 KiB. Actual active exits retain
cancellation causality as unproven. These later local results are outside the
`4e3af24` CI claim. Final resource/stack/profile comparisons, games and target
hardware work remain outstanding.

The exact C5947 candidate is subsequently promoted to the maintained C entry.
Only readable `engine.c`, the explicitly pinned recipe and README change; the
builder, verifier, fresh driver, compiler/profile, codec, prefix and bootstrap
remain identical to the preserved C5955 predecessor. The historical experiment
has its own control source and does not consume the mutable maintained entry.
Two independent extractions of the new fifteen-file source archive each repeat
shipping/DEV generation and run two actual selected-file sessions, for four
new physical sessions total. Shipping/native/whole and unchanged DEV pins all
match the qualified candidate. The promotion receipt is
`69cf45d8c105e2c5c8622a5319d09cb0248c8a2a122d6ce2e63fe77206b104d4`;
source tree `13f03c96bb8daa802dd56a48ba831f63b1f548ab` and archive
`089f36326e7ec3a441b0f11766ee1ed1ed3dd74b57c2a139cbdf239b1e065a73`.
Broad state/search proof is reused by exact candidate identity; it is not rerun
or replaced by source regeneration. This source promotion still requires its
own later-head CI result and does not select the final target profile.

## A startup phase ownership

The fixed [startup-counter source change](../engines/experiments/tiny-a-startup/README.md)
uses `pending` during the disjoint startup and search phases. It starts at the
fixed worker count; worker entry decrements it separately from the existing
job-completion/result branch. After every create succeeds, main uses the existing
`wait()` instead of a separate arrival counter and loop. Partial-create failure
still goes directly to shutdown and joins only actually created workers.
Board, TT, search, think, queries, parser, epoch and shutdown bodies remain exact.

The exact 5,140-byte maintained control is independently reproduced. Readable
source falls 24,921 to 24,820 bytes and compact C 10,958 to 10,855; native grows
22,664 to 22,672 while the actual complete file falls to **5,129 bytes**, an
11-byte saving and still 1,033 bytes oversized. A second isolated copy of the
owned source closure independently repeats both forms twice, matching every
readable/compact/native/bootstrap/whole output without mutable canonical inputs.

One separate instrumented compile passes five forced startup schedules: both
arrivals before main waits, a late arrival after the real wait predicate, no
successful create, one early worker before second-create failure, and a worker
entering after the real shutdown broadcast. Actual entry/exit/join identities
and TT free after successful joins agree. These are diagnostic pthread wrappers,
not the shipping native image or a general scheduler/join-error proof. Successful
startup now leaves internal `stopped=1` instead of zero; first GO already clears
it. A private consumer bypassing GO must clear it explicitly.

Two actual selected-wrapper processes pass eighteen individually fenced GO
epochs, including white/black zero clocks, active GO replacement and position
reuse, final quit/EOF, exact native bytes, stable three-TID startup, restoration
cleanup, reader EOF and absent owned PID/TID/observed-descendant identities.
The black-box sessions do not intercept pthread joins or prove cancellation
causality; those limitations remain explicit. No SAN/TSAN, broad board/search,
games or performance campaign is rerun. The final twenty-four-source index is
`f09a0b388e6417f5e80964b39eac1b2341fb2809314a5e24ef8c82f918fb0f60`;
the selected complete file is
`5da238b8f2cc622e5f71a2da07a4f3a787c6679fa29f78b27546800174578527`.
First cost, isolated reproduction, actual-wrapper and diagnostic receipt hashes
remain separate, including the actual runtime receipt
`f13080626ea2e169651c379321de1a69fcfe2061fa458a8c527ba4b031ccb960`.

The exact startup candidate is promoted to the maintained A source. The prior
nine files, source archive and shipping/DEV controls are preserved before editing.
Only `engine.c`, recipe and README change; builder, fresh/verifier code, template,
prefix, compiler, spelling/resource decisions and codec remain exact. New DEV
source/native are independently compiled twice from the qualified candidate
before literal admission; their identities deliberately differ from A5140 DEV.
Two isolated sixteen-file source extractions each reproduce shipping/DEV twice.
Two new actual selected-wrapper quit/EOF sessions pass, reusing the separate
five-schedule startup and eighteen-epoch proof through exact input bindings.
The promotion receipt is
`1b585bf749a7bde6cef3d3006b8856ff9624e286366afbd7fe537ff61abdc6b9`;
source tree `162cef5a32f3b58308b1623a237d985f5448fbc4` and archive
`8ffdde2d02fcdc8fa18bd6da08b5f8349c04ef487f97382a999282cd030ad7fb`.
Earlier experiments use preserved controls and do not acquire a dependency on
this new mutable canonical source. This remains a local source promotion until
the later exact-head CI runs; eligible size and final target acceptance are open.

## F integer-unit-window source specialization

The [F beta-only candidate](../engines/experiments/tiny-f-zero/README.md)
specializes the private recursive search API to the integer unit windows that
the production full-depth MTD driver actually supplies. Children receive
`1-beta`; a completed score stores a lower bound iff it reaches beta, otherwise
an upper bound. This removes first/later PVS dispatch and an unreachable interior
re-search. The coherent full-key single-bound TT and the driver's lower/upper
interval remain distinct. It is not a general wide-window search API.

Readable C falls 26,360 to 26,100 bytes, compact shipping C becomes 12,722 bytes,
and the actual complete wrapper falls **5,479 to 5,407 bytes**. Native remains
22,664 bytes with new exact contents. The focused proof compares the real old
unit-window search and new beta API in optimized and sanitizer forms, including
compact DEV=0 source, 51 finite thresholds/special states, retained MTD minimax
and attaining witnesses, interruption and PLY/context/learning controls. The
former seven wide-window fixtures are not reused for this changed API.
The proof receipt is
`96678ed411e4fea4fcd0b176fe5cd707f073d49166e541dd9112b3d1bfa49e12`.

The [maintained F entry](../engines/compact/tiny-entry-f/README.md) now contains
that exact readable program. Its builder removes counters using an owned strict
beta-only schema rather than the former shared overlay's PVS assumption.
Compiler, profile, codec and launcher stay fixed. Two fresh source extractions
each reproduce shipping/DEV outputs and run the selected wrapper for quit/EOF,
four new physical sessions in total. The selected whole-file SHA is
`e562a49a06257d46bbbb9e0481023f3716926e4cf2a8086dcd5307b3e8a96078`;
promotion receipt is
`a60b7d60b40d45863a1de2b3e0b378bd0764f1d980f9a67faab4eca109e1e23f`.
No broad campaign, strength or target stack/profile acceptance is inferred.

## D finite minimum shipping protocol

The [finite-D candidate](../engines/experiments/tiny-d-finite/README.md)
omits optional identification and consumes unsupported `stop`, `ucinewgame`
and `infinite` without adding controls. Clock allocation for the moving side
stays unchanged; absent that clock, a GO receives a finite 1,000 ms budget.
This is a search budget, not a hard wall-time cap. Next GO, position, quit and
EOF still wait for result publication and physical completion before reuse.
DEV retains the previous stronger controls.

The exact scalar/HQ natives shrink 8,476/8,864 to 8,348/8,736 bytes. Complete
own ELFs shrink **7,640/7,881 to 7,540/7,800 bytes**. Core, clone/futex pool,
fixed codec and loader stay unchanged; the admitted image class retains three
RX pages, 43 BSS pages and its guards. The original focused command/clock/TT
sentinel proof and broader physical sessions retain their original receipts.
The common strong-stop lifecycle harness is unchanged and is not claimed as
proof for the new consume-only shipping policy.

The [maintained D entry](../engines/compact/tiny-entry-d/README.md) promotes this
exact runtime and literal native/whole/checkpoint pins. Two independent source
extractions each reproduce both forms, their repeats and pre-entry audits.
Eight new production sessions and four pre-entry checkpoints pass image/RX/BSS,
permissions, legal results, persistent startup TIDs and quit/EOF settlement,
with no forced cleanup. The promotion index SHA is
`bbfdaa3f012f400b2ca575dae8ce91dbf0687379065f746a96e689bf5facf1d6`;
the fresh results SHA is
`80860d7be1d1b0ed5ba7e7d16a82653ae85a4ab3abd3b4347a1893daabac39ad`.

## Rust D borrowed ASCII ingress

The [ASCII ingress candidate](../engines/experiments/tiny-rust-d-ascii/README.md)
replaces the stored 16,384-token array with a borrowed byte stream. It rejects
a complete NUL/non-ASCII line before command dispatch and accepts ASCII space
and bytes 9 through 13 as whitespace. Unsigned parsing, successful-only numeric
lookahead consumption, transactional replay and the safe `parse(&str)` wrapper
remain explicit. Unicode whitespace admission is intentionally removed.

This change increases readable Rust by 836 bytes. Actual text plus rodata falls
1,403 bytes, absorbed by the unchanged linker alignment. Removing the unused
comparison GOT slot reduces data from 16 to 8 bytes, so both complete native
images fall only **16,824 to 16,816 bytes**. Main's measured prologue allocation
falls 431,952 to 169,824 bytes; this is not a universal stack bound or a source
minification result. No new unsafe indexing, search, OS, runtime, compiler or
linker policy is introduced.

The [maintained Rust D](../engines/compact/tiny-rust-d/README.md) promotes the
exact main/board sources and an owned strict verifier with ASCII negative and
whitespace/numeric/replay checks. Two fresh source extractions each reproduce
both native profiles twice. Actual new production ELFs pass 126/126 admitted
GOs across sixteen sessions. Both new production ptraces observe output before
completion publication and shared clear-TID join before stack unmap; the tracer
source is unchanged. Older deep/fault/board/search runs retain their original
scope and are not relabeled as new executions. The promotion receipt SHA is
`ff7bc32bbb4d00139848cb349180441b3c2cdc064cab9258ffc068244e173a80`.
CI pins the two new 16,816-byte identities literally. The root LF rule for this
subtree is repository metadata added separately from the qualified seventeen
source inputs; it does not change their bytes or their source archive.

These promotions are still oversized. All six eligible artifacts, selected
final resources, candidate-specific strength comparisons and target-hardware
scaling remain outstanding. Training and AWS connections remain excluded.

## Fixed B/C/E source spelling portfolio

The [alpha portfolio](../engines/experiments/tiny-alpha-portfolio/README.md)
shortens admitted automatic locals/parameters, private members and owned type
names, plus the already fixed WORKERS/TT_BITS literals. Protected functions,
global/static storage, directive consumers, external APIs, strings and compiler
arguments remain unchanged. Alias freshness/injectivity and exact occurrence
counts are explicit. Reversing aliases in the full preprocessed translation
unit reproduces the original bytes, and each full native ELF remains exact.

| Family | Compact C before / after | Whole file before / after | Whole saving |
| --- | ---: | ---: | ---: |
| B | 15,566 / 13,606 B | 6,219 / 5,955 B | 264 B |
| C | 14,206 / 12,526 B | 5,947 / 5,723 B | 224 B |
| E | 14,352 / 12,641 B | 5,899 / 5,679 B | 220 B |

Two independent candidate generations/builds per family reproduce those exact
source/native/bootstrap/whole identities. Six new selected-wrapper sessions,
quit and EOF for each family, pass exact restored native bytes, persistent
three-TID startup, legal white/black zero-clock and bare-GO output, active closing
output, reader EOF, process absence and temporary restoration cleanup. Compiler,
profile, codec and DEV are unchanged; historical core proof is reused by exact
native identity. There is no new game, benchmark or cancellation-causality proof.

The first-cost receipt SHA is
`e0527b2c9c566150791f6095346694961b81dc007fb9f89e1c135755ab81a1d8`;
actual new wrapper results SHA is
`5fbd18434187219b571dfb962058298616d560c671485c32d320a368607df427`;
the frozen forty-four-source aggregate is
`436d7cbdc6ad7fa52b73d5b1e9075971b9249f64d8225b775585a4dbd5b0ad80`.
This experimental closure has its own immutable historical control inputs.
At that experiment checkpoint, maintained B/C/E promotion was still a separate
next step. The following promotion now supplies those exact selected bytes.

The maintained B/C/E entries use a standalone ordinary-source helper containing
the identical readable policy bytes. Its transformation function bodies remain
identical; it reads no experiment files, side policy file or historical report.
Only each builder/recipe/README and the new helper change. Readable engines,
DEV, compiler, resource profile, codec, launcher and existing helpers stay exact.
The new helper has an explicit repository LF rule, separate metadata from the
qualified source closure.

Each seventeen-file source archive is extracted twice; each builder repeats
shipping and DEV generation/compilation. All twelve shipping and twelve DEV
builds match their literal pins. Six new selected-wrapper quit/EOF sessions
pass exact old native bytes and the new complete files, startup TID stability,
legal results and physical settlement. Earlier preprocessor/core proof is reused
by exact identity rather than rerun. The final promotion index SHA is
`6bbfcd6ffbf2b1dc029fa62295fb8cefe5687a430004a896de292c6d63aca712`;
the ten-source/union-thirty-six-input raw freeze is
`d2d9eb5182876708a95e4755693941b54e335f54b68021ee7d777398b61d7b83`;
fresh actual results SHA is
`ebacff60e489f3cb230313b4474b0cce57e206730745d5e077c2a052a6b89f53`.
This is a local source promotion until its later exact-head CI succeeds, and
none of the new whole files fits 4,096 bytes.

## Independent Rust D self-restoring ELF checkpoint

The [Rust packed experiment](../engines/experiments/tiny-rust-d-packed/README.md)
connects the independent no_std Rust core to the project's owned fixed decoder
and entry wrapper. It owns seven historical Rust production inputs and the
packaging sources; it does not call a C chess engine or an external decoder.
This uses the qualified pre-ASCII 16,824-byte native controls, not the newer
16,816-byte maintained inputs. The original C image admission remains unchanged.

The explicit Rust class removes only ELF section metadata outside PT_LOAD and
normalizes the section-header fields. Its 16,400-byte decoded span preserves
entry, program headers and all allocated text/rodata/data. The final mappings
are four RX pages and one RW page containing sixteen initialized pointer bytes,
four zero OUTPUT bytes and zero padding. Original-native, sectionless, payload
and whole-file identities are separate. Copying section metadata over BSS is
rejected rather than treated as a valid loaded image.

Two independent builds per profile reproduce complete self-restoring files of
**12,554 B HQ / 12,194 B scalar**, including the 1,115-byte header/loader cost.
These save 4,270/4,630 B over the direct Rust native controls and remain far
above 4,096 bytes. First-cost execution was zero; later runtime is a separate
campaign. The original first-cost index SHA is
`b9e9325c4a5cbcf04515012afd733a25dd5caec92f0e3e929bad3d19bd5eff3d`.

Actual new packed-file observations pass two distinct pre-entry CHECKPOINTs
and four shipping sessions, both profiles with quit and EOF. The checkpoints
bind the anonymous decoded bytes, initial data/BSS, guards, permissions and
original entry. Shipping covers 24 legal results for 24 GOs, persistent three
startup TIDs and guarded stacks, active replacement/position/shutdown, complete
output/readers and physical process/TID/group disappearance. None of these six
positive sessions needed forced cleanup. Older raw-native kernel/deep/fault
proof is not relabeled as a new packed execution.

The full campaign stays **incomplete**. Its READ_IMPLIES_EXEC rejection fixture
did not reach the intended boundary: a confirmed pre-exec flag was zero in the
loader's actual post-exec personality query. That diagnostic reached restoration
and was stopped at its event cap, with forced cleanup explicitly recorded.
It is not a guard-rejection success; the scalar negative was unexecuted.
A logging-only revision preserves events immediately but has not rerun the full
campaign. A later register-modifying debugger fixture was not executed and is
kept outside Git. The admitted nineteen-source checkpoint therefore preserves
the original positive results, failed report and unproven negative separately.
Its external index SHA is
`95c581b682b3cec6398a6d29864b810aa99b5fd01457fa0abb9c74685c2d63c4`.
This checkpoint establishes implemented and observed Rust restoration paths,
not complete runtime admission, eligible size, strength or target scaling.

## Rust D constructor reuse first cost

The [runtime-start candidate](../engines/experiments/tiny-rust-d-start/README.md)
changes only `Board::start()`: initialize the fixed 32 occupied squares through
the already-shipping `put`, then finish state hash/context. Arbitrary-input
rebuild, canonical EP, move/search/TT/learning, OS/SMP, ABI, compiler and linker
remain unchanged. No const factory, dispatch change or unsafe shortcut is added.

Both exact ASCII controls reproduce before candidate compilation. Each candidate
reproduces independently and passes the existing ELF gates. Allocated `.text`
falls **272 B** in both profiles; `.rodata` stays 304 B and `.data` 8 B. The
unchanged data alignment absorbs that gain, so both complete natives remain
**16,816 B**. Readable and identically merged measurement source each grow 16 B.
Existing `put` stays 314 B and `start` shrinks 545 to 322 B; changed inlining of
the unchanged canonical-EP body explains the remaining allocation effect.

Separate ordinary-runtime std units compare all ten Board fields and 151
elements between original/candidate and check Copy/fresh-start independence.
Both HQ and scalar pass two tests each. These diagnostics do not compile the
raw runtime or search. At this constructor-only checkpoint the new production
ELFs have not been executed; the later packed cost and observation are recorded
separately below. Twenty-four ordinary LF sources
retain the control and constructor producer without a live-maintained dependency.
Final aggregate SHA is
`689a3d5b662bd6d8163fbce5ec882a31dfb6a980d596aa44212e5b5b98b53db5`;
source manifest SHA is
`15778ac39d3b529926881c0486df98d7be512e0efca938785e741fd33c26d655`.
This is an allocated-code saving with narrow constructor proof, not a smaller
whole file, a source-minification result or a qualified new shipping runtime.

## B target emitter with fixed source spelling

The [target/alpha composition](../engines/experiments/tiny-b-target-alpha/README.md)
reproduces the maintained 5,955-byte B and combines the earlier target emitter
with its own literal adaptation of the same 89-name alpha policy. The actual
whole file is **5,899 B**, a 56 B saving, rather than the additive prediction
from the separate target-only and spelling results. Compact source falls
13,606 to 13,559 B; native grows 26,592 to 26,624 B and remains byte-identical
to the previously qualified target image. No additional core policy changes.

The target uses eighty of the mapping names. Its exact 607 token occurrences,
unchanged opaque regions, fresh aliases and candidate identities are admitted
separately; the original alpha helper and its three admitted domains stay
unchanged. Actual resource/header/full-preprocessor inverse checks and two
independent source/native/whole generations pass. Two actual selected-wrapper
quit/EOF sessions pass the unchanged original verifier with literal new source,
bootstrap and whole-file pins and the already qualified target native pin.

The target's changed generation order and up to 64 reverse attacker queries per
ordinary generation retain their unmeasured speed tradeoff. No new core/game/
NPS campaign or universal stack claim follows from the source composition;
whole-runtime stack qualification stays false and cancellation causality
unproven. This remains an experimental candidate, 1,803 B oversized, rather
than an automatic replacement for the maintained B profile.

Thirty-one ordinary LF source files close the experiment without live maintained
or generated-engine inputs. One later repository-only ignore override admits
its three ordinary `control/target` sources while keeping other target outputs
ignored; the original thirty-one bytes/hashes and executions stay unchanged.
The final summary SHA is
`f63ff76aff763489621ec6c1115e0a7541334050a86016eae4ad7d4584538c2e`;
cost receipt is
`c6b104022c8b1580febcc81f8826c2b2f34c25fa87323540f5c8c4ce8b8da4b7`;
actual selected runtime is
`141ccb1f841b6d3687a09d7fa914b13c4b270a673635a96fa47d3f940214e0eb`.

## D metadata-first Board cost

The [D layout experiment](../engines/experiments/tiny-d-layout/README.md)
moves the Board's existing metadata before its 128-byte mailbox. Field types,
board/search/runtime statements, compiler/profile and loader/codec stay fixed.
Both layouts measure size 176, alignment 8 and four padding bytes. Metadata
offsets become small while mailbox indexing gains an offset; no size advantage
is assumed before compilation. Read-only consumers show no exposed Board ABI,
raw serialization or assembly field offsets, but semantic/physical candidate
qualification is not inferred from that audit.

Original scalar/HQ natives 8,348/8,736 B reproduce first. The one fixed layout
then reproduces at **8,220/8,576 B**, saving 128/160 B. With the unchanged fixed
codec and loader, actual whole files reproduce at **7,513/7,748 B**, saving
27/52 B from the original 7,540/7,800. Header/loader remains 1,115 B. These
are measured first costs, not qualified new runtime files. The experiment has
no engine or restoration-checkpoint executions; original image admission still
rejects the new native identities.

Twenty-five ordinary sources preserve the original native producer and the
separate whole-cost producer. Final handoff SHA is
`4f154f5869fb23a91165658a52ac875f319dbfd49c30ccd2ef83e34acf4a7cbe`;
final raw-source freeze is
`d807aa5889e2d43fb5da95160143dd2a2e8d46652d1779da54c137c30675e0d3`;
whole-cost receipt is
`255cb5028429d6a0aa5ddaba90673d7fe3964c278e4b381ed7666c21d337e1b5`.
The separately measured retry-phase/layout combination changes the scalar RX
page class and remains under its own explicit admission and qualification work.
Its gains are not added to these individual measurements.

## Fixed A/F private spelling and maintained F promotion

The [A/F spelling experiment](../engines/experiments/tiny-alpha-af/README.md)
applies one fixed role-audited map of 73 private type/member/local names.
Functions, global/static objects, external APIs, macros and opaque bytes stay
protected. No name, compiler or codec sweep is performed. For F, compact source
falls 12,722 to 11,216 B and the actual whole file falls **5,407 to 5,179 B**.
Both independent builds reproduce the exact original 22,664-byte native ELF,
including build ID and nonallocated bytes. Full raw preprocessor alias-only
inverse and final macro-dump equality pass. Two actual selected-file quit/EOF
sessions pass exact restored image, fixed startup TIDs, legal clock/bare results,
active closing output and physical settlement.

The original A attempt has a different outcome: replacing PLY with its equal
128 literal changes whitespace in the raw expanded expression. Its strict full
preprocessor inverse fails before candidate compilation, codec or engine
execution. That failure remains recorded; F's success does not admit A. An
initial diagnostic incorrectly expected configured resources in the compiler's
final macro dump. The corrected gate compares actual final dumps exactly and
keeps the original configured 2/18/128 probe separate; it does not normalize
whitespace or numbers to admit the failed A candidate.

Forty-two ordinary sources freeze both outcomes. Final experiment index SHA is
`6a955eae59e558c67ca4902ef1e75f18ee3d13a8372ef039105ff9887688e837`.
The two F engine sessions used the preserved original outer adapter. Its later
ownership repair was checked with stub children only, so those sessions are
not attributed to the revised adapter.

The maintained F builder now owns an ordinary `shipping_alpha.py`, embedding
the original policy bytes and the identical generic scanner/rewrite function
bodies. It admits only its exact canonical F and compact input; the experiment
folder, historical receipts and another engine's source are not build inputs.
DEV bypasses the new stage. Engine, native and DEV bytes, profile, compiler,
codec, launcher and existing helper bodies remain unchanged. The four-file
promotion expands fresh closure to sixteen ordinary sources.

Two independent source extractions each reproduce shipping and DEV twice.
Four new actual wrapper sessions cover sixteen GO epochs, exact native image,
persistent startup TIDs, legal results, active quit/EOF and reader/process/path
settlement. No forced cleanup is needed; cancellation causality stays unproven.
Whole-file SHA is
`41a730c266082b1c8285fef7972eb158704cd7411a475d4eecc9dd058ef587aa`;
promotion receipt is
`121713961ca1987f7fe299fc645f4572e80b4013206b698c1df77d19a6647a80`;
raw ten-local/sixteen-closure freeze is
`165855fcac4de546f3ae3b2de7bc16fc7ee741cdca39f5a007851b51c6204560`.
The 228-byte saving leaves F 1,083 B above 4 KiB. Core evidence is reused only
through exact native identity; no new strength or target-profile claim follows.

The later [A-only macro-preserving candidate](../engines/experiments/tiny-alpha-a/README.md)
retains the exact 31 A-present alias pairs and their gaps, while protecting all
eight PLY code uses instead of replacing that equal-length macro. This is a new
fixed candidate; the joint A failure above remains unchanged. It saves 249 B of
source and 57 B of actual whole file, **5,129 to 5,072 B**. Raw full-PP inverse
uses aliases alone, with no whitespace/number normalization; final dumps and
the separate configured 2/18/128 probe pass. Both complete native files equal
the original 22,672-byte literal before codec; DEV and all runtime/compiler/
profile/ALONE choices remain unchanged.

Two actual selected-wrapper quit/EOF sessions pass eight GO epochs, exact
restored native, persistent three TIDs, legal results and physical settlement.
The corrected outer ownership adapter is the executed version for these new A
sessions. This does not rerun broad core, sanitizer, game or performance proof;
core reuse is through exact native identity and cancellation causality stays
unproven. Thirty-three ordinary LF sources close the producer and verifier.
Final index SHA is
`5d0878cab7b9f7758bb12a11ea490c6e3fdc01f208aebdbdcb5536adcdf55f7b`;
actual runtime receipt is
`c7e8a9ef92184e6a30f5e8d7a7d5ebe067eeaade38ab6651539a5b77e0a549c7`;
whole-file SHA is
`47370ce2d27e84349eade3f7b3ff698f5e76f1cb382531e409420b6dbbbb8f2d`.
This separate local candidate remains 976 B oversized; its maintained-source
promotion has its own subsequent reproduction/runtime step.

The maintained A now promotes that exact candidate through four files: builder,
recipe, README and an owned ordinary `shipping_alpha.py`. Original forty-five
renames, fixed resources and thirty-one function spellings keep their order;
the new fixed map is the final shipping stage. DEV bypasses it. Canonical engine,
full native/DEV bytes, compiler, profile, launcher, template, existing helpers
and ALONE settings remain exact. The helper reads no experimental/historical
or generated-engine input. Original nine sources/archive and shipping/DEV
controls are preserved before replacement.

Two independent seventeen-file source extractions each reproduce shipping and
DEV twice. Four actual selected-wrapper sessions pass sixteen GO epochs,
restored image identity, persistent three-TID startup, legal zero-clock/bare
results and active quit/EOF reader/process/path settlement. Historical raw PP
and core proofs remain reused by exact identity; no broad campaign is rerun.
Promotion receipt SHA is
`41516d5993b1be2473c33dc7b3f42864a22d67963a63453f665eaef9e4122fb5`;
ten-local/seventeen-closure source freeze is
`54d773e921f115a4c6c801a485773621b4f81b94f348c1c55d3e2fecdc0da9b4`.
The original A/F failure and all frozen experiments remain unchanged. This is
a local source promotion pending a subsequent exact-head CI, still oversized.

## D retry-phase qualification and metadata composition

The [D retry-phase experiment](../engines/experiments/tiny-d-search-phase/README.md)
reuses the previously investigated finite retry-loop expression for D's real
eight-argument PVS calls. It keeps reduced null-window, full-depth null-window
retry and full-window retry decisions explicit. This is not a new search
algorithm, and the earlier A whole-file loss remains historical evidence.
Compact source falls 6,269 to 6,209 B; native scalar/HQ falls 8,348/8,736 to
8,284/8,672 B. Actual whole files reproduce at **7,501/7,753 B**, saving 39/47 B.

Four actual optimized one-worker DEV subjects pass twenty fixed cases against
the old source, comparing result rows, search trace, Worker, TT and game state.
Reduced-null, full-null retry and full-window retry branches are observed.
Beta-high has no dynamic hit in this finite campaign and retains source-path
reasoning only. Four actual selected-file sessions and two new pre-entry audits
pass image, three RX pages, 43 BSS pages, guards, permissions, fixed startup
TIDs, twelve legal results, reader/process settlement and no forced cleanup.
There is no new broad fault, game or performance campaign. Twenty-nine sources
and the final proof index are frozen at
`0649c0f6978a601b7e9297abd156c0c22b95a4d2e10b7f3cfa2170adbc4e0313`.

The separate [layout/phase composition](../engines/experiments/tiny-d-layout-phase/README.md)
combines exactly the metadata-first Board declaration and this search fragment.
Two independent builds reproduce scalar/HQ natives **8,124/8,512 B** and actual
whole files **7,478/7,718 B**. These measured whole savings are 62/82 B from the
original 7,540/7,800 B; they are not sums of the separate experiments. The same
fixed payload codec and 1,115-byte header/loader are used.

The actual scalar native now has two RX pages and BSS at 0x402000; HQ retains
three RX pages and BSS at 0x403000. Both retain 43 BSS pages. Root independently
read the exact repeat natives' ELF headers/program headers; the loader's new
per-form guard/reserve constants are still declarations, not physical proof.
Old production image admission remains unchanged and rejects the new natives.
The cost producer has no CHECKPOINT or engine executions. Named-field Board,
special-move/search and the new two-/three-page physical qualification are a
separate subsequent proof below; neither cost nor phase-only proof promotes
the combined image automatically. Twenty-eight ordinary sources are frozen;
handoff index SHA is
`2bda9d37186d0d171a5a7f3928929082085595b25399ed63382bd271209b639e`.

The separate [combined-image qualification](../engines/experiments/tiny-d-layout-phase-proof/README.md)
now closes forty ordinary source inputs without editing the frozen cost or
phase-only producers. Four optimized one-worker DEV subjects pass the same
twenty actual search cases, comparing normalized named Board fields/mailbox,
full Worker, TT and game state. A separate independent-oracle Board campaign
passes twenty-four fixed cases per subject, 3,051 nodes each, including perft
400/2,039/191, initialization, special moves/rights, all-square attacks, full
HCE, hash and reversible-path state. Layout normalization is limited to Board;
raw within-object snapshots and the other unchanged representations stay exact.
Reduced-null/full-null/full-window retries retain their observed coverage;
beta-high remains dynamically unproven in this finite set.

Four actual shipping quit/EOF sessions and two separate pre-entry CHECKPOINTs
pass exact native/restored bytes, RX/BSS padding, permissions, image and worker
guards, FD012/no children, three persistent startup TIDs, twelve legal results,
exit 0, reader join and owned group/TID absence. Scalar's two-page RX, BSS at
0x402000, upper guard 0x42d000 and reserve 0x2f000 are now physically observed;
HQ retains its separately observed three-page class. Both have 43 BSS pages.
No forced cleanup is required. Loader/codec/runtime/pool are unchanged source
inputs, not new broad fault or game executions. Original production admission
remains unchanged during this experimental proof. Final index SHA is
`b05e3e344983c0bc340c28570b0229c8c5ab3cb1e579ca0e3bf290ac8a51cc83`;
actual physical receipt is
`dfcebada0c43fee2dba85893385f261bc398b4c4808a90a6d90055ef1c922add`.
The qualified experiment remains 3,382/3,622 B oversized. Its separate
maintained-source promotion has not been included in these experimental runs.

The maintained D entry now promotes that exact header/search pair and the
qualified native/whole/audit literals through seven files. Six other native
sources, runtime/pool, loader/codec, compiler/flags/profile, fresh-source tool
and LF policy remain exact. Packer admission binds each full native SHA/size
to its own HQ flag, entry and complete mapping class. The independent verifier
requires the full per-form literal layout. This is not a generic two-/three-page
permission, and historical experiment guards remain unchanged. Earlier DEV
identities are explicitly ancestry only; the changed Board/search does not
claim byte-identical DEV binaries.

Before editing, the old eighteen sources, archives and native/whole/audit
controls are preserved externally. Two independent twenty-member source
extractions reproduce eight natives, eight whole files and four separate
audits. Eight new actual shipping sessions and four pre-entry checkpoints
pass exact restored images, the two mappings, twenty-four legal results,
startup/guard/permission checks and physical settlement, with no forced cleanup.
The new maintained source closure reuses the separate Board/search proof by
exact fragments; it does not rerun broad fault, game or benchmark campaigns.
Final promotion index SHA is
`b8f7c95d3606caae4ce251258e9ed1a60522690f805a64ce1683166f61c49421`;
fresh actual results SHA is
`87b78afdc9438aaf34d43f5b118ce89e1fa5558030d437ccc4ba3730c741e8fc`;
closed source archive SHA is
`49a1fd6266dfe3a374a250d962eb82473e6f38e5ab9367647e339cee9fa2f184`.
This local source promotion awaits its subsequent exact-head CI and remains
oversized; reduced beta-high dynamic coverage, strength and target scaling
are not enlarged by the promotion.

## Rust D ASCII data8 packed cost and positive observation

The [new data8 experiment](../engines/experiments/tiny-rust-d-packed-ascii/README.md)
combines the preserved borrowed-ASCII inputs with the constructor candidate in
an explicit class separate from the old data16 packed image. All four matched
forms reproduce full native and whole bytes twice before observations.

| Form | Payload | Whole file | Saving from matched ASCII control |
| --- | ---: | ---: | ---: |
| ASCII control HQ | 10,647 B | 11,762 B | Baseline |
| ASCII control scalar | 10,288 B | 11,403 B | Baseline |
| Put-start HQ | 10,450 B | 11,565 B | 197 B |
| Put-start scalar | 10,091 B | 11,206 B | 197 B |

Each whole includes 1,115 B of loader/headers. Constructor `.text` reduction of
272 B therefore becomes an actual packed saving of 197 B. The older data16 to
ASCII-control saving, 792/791 B, is a different comparison. Original full native,
sectionless span, payload and whole identities remain distinct. The sectionless
span is 16,392 B; data8 stores only memcpy at 0x400146. OUTPUT is four bytes at
0x404008, followed by padding at 0x40400c. RX4/RW1 and five decoded pages remain.

Two actual pre-entry CHECKPOINTs bind a single stopped TID, FD012/no children,
all five restored pages, initial zero OUTPUT/padding, data8, guards and observed
permissions. SIGCONT is followed by protocol/exit; no new instruction-pointer
trace is claimed. Four shipping quit/EOF sessions bind three persistent startup
TIDs and two guarded 1 MiB worker stacks. Each session observes CPU tick growth
and active workers at GO replacement, position replacement and shutdown. All
twenty-four admitted GOs have exactly twenty-four consumed legal bestmoves,
with complete output/readers, exit 0 and no forced cleanup. An independent
postrun check verifies sixty-nine preserved files and ten five-page snapshots.

The positive observation is complete for this fixed profile. Runtime admission
and all loader conditions remain incomplete; READ_IMPLIES_EXEC rejection and
cancellation causality remain unproven. No negative/personality/register/ptrace,
new kernel join trace, deep/fault, benchmark, game, training or AWS campaign is
attributed to this class. The old failed fixture and controls remain preserved.
Twenty-two ordinary sources are frozen. Final index SHA is
`eaae61309580f5dfa0758f3b38df98a41c58eef296749836fc9c226ca25601d3`;
actual positive runtime receipt is
`a5221549c16adb9af08c0d46a90e023481f269773fa61916703353131f98aeb4`.
Both whole files remain oversized, and this experiment does not replace the
maintained Rust D profile or establish final target strength/scaling.

## E feature/material-pass composition: measured loss

The [E fusion experiment](../engines/experiments/tiny-e-feature-dead/README.md)
collects the existing insufficient-material classification during the existing
twenty-one-coefficient leaf feature pass. DEV retains the prior source path;
the candidate's normal shipping source uses one fixed structural composition
and the same fixed eighty-nine-name policy with its own literal input counts.
No existing helper or historical guard is broadened.

The exact maintained E5679 control reproduces twice first. Candidate shipping
source falls **12,641 to 12,626 B** and native falls **26,408 to 26,376 B**, but
the actual complete file grows **5,679 to 5,683 B**. Both independent candidates
reproduce source/native/bootstrap/whole bytes. Candidate alias-only full-header
inverse, final macros and pre-/post-alias full native equality pass; the
structurally changed image is not equal to the old E native. The measured
whole-file loss ends this candidate. There is no candidate engine/semantic,
DEV-native, game, benchmark or promotion campaign; maintained E stays 5,679 B.

Twenty-five ordinary LF source inputs preserve the candidate and the control.
Final index SHA is
`cb99a23f854792459be534a06bbb5836d138cb68850852bf078e20a5d8ee1ff9`;
actual first-cost receipt is
`2c2417db620d65f12d31807529dc13a055bcd3b037c6a69c328b7382e0149b0b`.
This records a rejected size result, not new functional acceptance for E.

## A/F private object spelling

The [storage18 experiment](../engines/experiments/tiny-alpha-storage-af/README.md)
adds one fixed `qa` through `qr` mapping for eighteen private shipping objects
after the earlier type/member/local policies. The original conservative object
protection was audited against actual consumers: pthread/atomic calls use their
addresses and values, and these single-translation-unit entry builds have no
consumer of the remaining object spellings. Public/API functions, directive
consumers, types, members and strings remain protected. In particular Move is
still consumed by the MOVE directive and remains unchanged. Aliases are not
searched or retried; actual source and expanded-header freshness are checked.

| Family | Compact source before / after | Whole before / after | Actual whole saving |
| --- | ---: | ---: | ---: |
| A | 10,606 / 10,184 B | 5,072 / 4,980 B | 92 B |
| F | 11,216 / 10,745 B | 5,179 / 5,083 B | 96 B |

A uses seventeen names at 87 occurrences and F uses eighteen at 99. Actual
source savings are 422/471 B; the earlier manual estimate missed one mutex
occurrence per family and remains preserved separately. Both independent
candidate natives match the original complete ELF bytes before codec. Raw
full-PP alias-only inverse, complete final macro dumps and separate configured
profile probes pass. DEV, native code, compiler, profile, codec and launchers
remain unchanged. These equivalences are scoped to the admitted A/F entries,
not an assertion about unstripped entries in other families.

Four actual selected-wrapper sessions pass sixteen GO epochs, exact restored
native image, three persistent startup TIDs, legal results and physical
reader/process/path settlement. Cancellation causality remains unproven.
Forty-four ordinary sources freeze the producer and the executed adapter.
Final index SHA is
`2824e102ceb29316a522982fb8c249c0f8fd8588a2cfa0e4b6b4d5fb9649074c`;
actual runtime receipt is
`304b37c55065752cb1c723ad73e9d713f6681c32fc8ad91616a2ac340afc7ea1`.
The candidates remain 884/987 B oversized. Their subsequent maintained-source
promotion and fresh-archive execution are separate steps.

The maintained A/F entries now promote those exact selected bytes through six
builder/recipe/README files and one shared ordinary
`engines/scripts/fixed_shipping_storage.py`. The helper embeds the identical
fixed policy and lexical/opaque checks; its readable reservation union is
embedded from the exact audited canonical inputs. A caller supplies only its
own family's canonical/source bytes. There is no runtime experiment/report,
other-family file or generated-source dependency. The stage follows the local
alpha map, and DEV bypasses both shipping stages. Existing engine/local alpha,
fresh/verifier tools, compiler/profile/template/launcher/codec remain exact.
The root helper LF attribute is separate repository metadata.

Old A10/F10 sources, closures, archives and shipping/DEV outputs are preserved
before editing. New normal source closures contain eighteen A files and
seventeen F files, twenty-eight unique files. Each family archive has two
independent extractions, each repeating shipping and DEV generation/compilation.
The full native ELF and both DEV identities remain unchanged, without build-ID
or nonallocated-section exceptions. Eight new actual wrapper sessions pass
thirty-two GO epochs, exact native image, persistent three-TID startup, legal
clock/bare output and active quit/EOF physical settlement. No new broad core,
PP, game, benchmark or DEV-engine run is inferred; earlier source/PP/core proof
is reused by exact source/native identity.

Final maintained promotion index SHA is
`71b68e367a2505b3bf21b6f36ad527f5da52b317b4549da27a75a1186661dcb5`;
raw-source/output freeze is
`fa731d627a422c08ad94311fea50b14ac29667db726fb7c3b0fb3ccd6764b047`;
normal-source union archive is
`ab663f9f8aae0ce2ca40634566256917c4c639be52a9af03a52ec1ad9e2bb7ae`.
This local source promotion awaits its exact-head CI. Both families remain
oversized and cancellation causality remains unproven.

## B bitboard material predicate: unchanged whole cost

The [B dead-bb experiment](../engines/experiments/tiny-b-dead-bb/README.md)
replaces only the insufficient-material mailbox scan with existing coherent
piece/occupancy bitboards. It introduces no new Board state or table. Its
unsigned minor-population and bishop-color expression is statically equivalent
under the canonical bb/mailbox consistency contract; no repair of stale or
arbitrary manual objects is implied.

Readable source falls 77 B, pre-alpha shipping falls 47 B, but after the same
fixed policy compact source falls only **13,606 to 13,602 B**. Native text grows
7 B while the full ELF remains 26,592 B with different contents. The actual
complete file stays **5,955 B**, a zero-byte saving. Both original controls and
independent candidates reproduce. Candidate alias-only full PP inverse, macro
definitions and full native equality before/after alias pass; the old and new
structural natives are different identities.

Twenty-four ordinary sources freeze this neutral first cost. Final index SHA
is `f77eab167403f98d570adfe7063f831d259470f6e0fb05f23a0f8fbc012b6148`;
actual cost receipt is
`a0abaebf810de912c9a997a5ac9000aed6b203574c3f88a2e694550f05824bb3`.
There is no candidate engine/material fixture/board/search/runtime/game or
benchmark execution, no promotion and no speed claim. The target5899 source
remains a separate candidate and is not combined with this measured result.

## C query/reset/startup composition first cost

The [C entry composition](../engines/experiments/tiny-c-entry-composition/README.md)
transfers three source decisions into the actual C program: nullable-text query
and made-child replay share one legal walk; think owns best reset instead of a
GO-wide worker loop; startup arrivals share pending and the existing wait.
The entire prefix before think, including Board/shipping-v handling, rules,
PSQT constructor, actual AVX2 leaf, TT and search, remains byte-identical.
King-capture/list guards and compiler/profile/codec remain unchanged. Initial
stopped becomes one before first GO and direct think resets best; these private
differences require their own C tests rather than inherited A acceptance.

Readable source falls **27,003 to 26,692 B**, compact source **12,526 to
12,224 B**, native **26,464 to 26,424 B** and actual whole **5,723 to 5,687 B**.
Original shipping/DEV controls reproduce twice, and both independent candidate
source/native/bootstrap/whole files match. Candidate full native bytes before
and after fixed89 alias are equal; they differ from the old C native.

The first attempt stopped before candidate compilation because a new owned guard
incorrectly requires raw macro-dump order equality. Complete raw definitions
and duplicate counts are equal, with order only different. The failed run and
its source snapshot remain preserved. The corrected owned gate uses
Counter(raw.splitlines(keepends=True)): every definition byte/ending and count
must match, while raw-order equality is recorded separately as false. No
whitespace or numeric normalization is introduced, full raw PP alias inverse
remains strict, and existing frozen helper/guard domains stay unchanged.
Independent review also repairs a nonunique inverse site and establishes owned
process-group lifetime for candidate preprocessing before successful compilation.

Twenty-eight ordinary sources close this cost-only candidate. Final index SHA
is `f98cfee22ee4c2895719d4a6286873c12d49ca4cdce11c9ee4a16eea40b65244`;
successful actual cost is
`88e1dc9273c7231e33ff2783323b55353937c9a6c795b6727fc3fb31ba208932`;
preserved first failure is
`9e67f4282cb8ad710e51a996d1229bea2cff66c3453b5fea9a68ff9bccdc49db`.
At this first-cost checkpoint candidate DEV/engine/semantic execution is zero.
Selected executable candidate-1/2 files are mode 0755; the selected/x copy is
0644 and has not been executed. C-specific query/ownership/startup/SIMD and
selected-wrapper proof is a separate in-progress step. This candidate remains
1,591 B oversized and does not replace the maintained C entry automatically.

## C composition: bounded functional qualification

The [C composition proof](../engines/experiments/tiny-c-entry-composition-proof/README.md)
now qualifies the same 5,687-byte candidate through its changed query, startup
and GO ownership paths. Four actual old/new O2 and ASAN+UBSAN forms pass the
independent Board/query checks, including legal children, invalid text,
transactional replay, repetition hash, reversible-path digest and raw SIMD
HCE/scalar parity. Five controlled pthread startup schedules cover early/late
arrivals and creation failure after zero or one successful creation. The real
epoch fixture observes four GO epochs and pending completion before root reuse.
The unchanged actual SIMD evaluator and standalone native disassembly are
checked separately from those ownership fixtures.

Exactly two selected whole wrappers, one quit and one EOF, produce eight legal
GO results. The unchanged C verifier observes the new native identity,
three startup TIDs, FDs 0/1/2, one closing result per session and physical
reader/process/private-path cleanup. These are actual restored candidate
executions, not inherited A results. Candidate DEV has not been built or
admitted in this proof, and old C full-native equality is not claimed. The
epoch fixture covers early claim abort and depth-zero fallback; it does not
establish deep iteration publication or general race freedom. Cancellation
causality remains unproven.

The first query fixture incorrectly labels a move legal in its pinned-rook
root as invalid. Its abort and source are preserved; only that text token is
corrected, independently rejected on all roots, before the four passing forms.
The final record accounts for all five attempted query executions. Fifty
ordinary sources are frozen with final index
`f3278861a28f37adfb2aead6f7ce2f8558caf261ff77f8f68c70380d996e0641`,
source freeze `a22ecac4bcd283128793b2fb7256504dbc3bcc669dca64eee25d4274fb7547b0`
and source archive `7262ca5ac6c734698d7ba80aa1101e5d7829a7724dc476b77cf36857a139186a`.
The recorded 48 owned PIDs/TIDs and both restoration paths are absent at final
settlement. Maintained C promotion is a subsequent, separate step.

## B/C/E storage spellings: original native-identity failure

The [B/C/E storage experiment](../engines/experiments/tiny-alpha-storage-bce/README.md)
applies the same fixed eighteen object spellings to ordinary B5955/C5723/E5679
controls. Source falls by 535/461/449 bytes respectively, but the original
full-native-identity contract fails on the first B candidate. Baselines for
all three families reproduce twice before that compile. Candidate native
compilation then stops: B has one attempt, C/E have none, and candidate codec,
whole-file measurement and engine execution remain zero.

The observed B file changes from 26,592 to 26,496 bytes. Direct ELF inspection
finds unchanged program headers, allocated-section geometry, code/data,
dynamic symbols and relocations. The GNU build-ID descriptor and nonallocated
symbol/string/section metadata differ after source object renaming. These
observations do not satisfy the original full-file identity assertion and do
not prove semantic or ABI qualification. The failed original producer and its
52 ordinary sources remain frozen; a new, separately named metadata boundary
can be evaluated without relabeling this failure as success. Original final
index is `0bf7fa1b7fc6d74b40a0d59c30bf91c5bca7c6f729a90330d5129851c6193e66`.

## D completion latch: measured cost before lifecycle qualification

The [D completion-latch experiment](../engines/experiments/tiny-d-completion-latch/README.md)
reuses pending for startup arrival and search/result completion while retaining
epoch and quitting. A GO publishes WORKERS+1; the last search result owns the
remaining value one until output finishes, then releases zero for main-thread
reuse. Startup creation failures bypass the arrival barrier and retain
kernel clear-TID joins before stack/TT reclamation. Board, search, HQ logic,
compiler profile, loader and codec stay unchanged.

Both ordinary controls reproduce twice before the candidate whole builds.
Scalar native falls 8,124 to 8,092 bytes, HQ 8,512 to 8,480; actual whole files
fall 7,478 to **7,457 bytes** and 7,718 to **7,707 bytes**. Both independent
candidate builds match. The unchanged loader/header cost is 1,115 bytes;
payloads are 6,342/6,592. BSS remains 175,092 bytes despite the removed source
objects. The original admission rejects the new native identities; only the
separate exact cost adapter admits them for this measurement.

Independent actual-file review confirms whole/linked byte relationships and
bounded Deflate plus BCJ restoration to the fresh native bytes. This is data
restoration and cost evidence; candidate engine, checkpoint and runtime mapping
execution are zero at this frozen stage. Lifecycle qualification is separate.
Twenty-four ordinary sources freeze the final cost index
`05b027c5ec0e21da9ab6fdc91c8120984e2cea2e11b993edd5ceed1076748e0e`;
actual whole receipt is
`628ea7e3eccae0c20ade39997836a838b03e60ed128dc1eadc8a0119fd556bca`.
Neither measured file meets 4KiB, and no performance or strength gain is claimed.

## Maintained C composition source promotion

The [maintained C entry](../engines/compact/tiny-entry-c/README.md) now owns the
qualified 5,687-byte composition as its ordinary readable engine source.
Five local files change: engine, builder, recipe, README and one new local
shipping-alpha helper. The helper embeds the exact original C composition
policy and calls the existing pinned shared generic scanner/rewrite with its
own canonical bytes. It neither calls nor widens the old shared admission;
B/E and all existing shared helper bytes remain unchanged. The compiler,
profile, codec, bootstrap, launcher, fresh/verifier and core prefix are exact.

The old seventeen-file C5723 closure and shipping/DEV files are preserved and
reproduced from two independent archive extractions first. New DEV source and
native are generated twice from the qualified readable and explicitly pinned;
old C5723 DEV/native equality is not claimed. New normal generation consumes
eighteen ordinary sources, including the local helper, and reads no historical
report, experimental folder or old generated artifact.

Two independent new source archive extractions each regenerate shipping and
DEV twice. All source/native/bootstrap/whole and new DEV bytes reproduce.
The unchanged verifier then executes both selected builds: four actual
quit/EOF wrapper sessions, sixteen legal GO results, exact restored native,
three stable startup TIDs, FDs 0/1/2 and physical reader/process/path cleanup
pass. No new DEV engine or game/benchmark is executed. The earlier C-specific
query/startup/epoch/SIMD proof is reused through exact readable, shipping and
native identities; cancellation causality remains unproven.

The final promotion receipt is
`a3d54a16e4df0f18a3da3ea2361fd8138ec91903140f19fe06256922bef970be`;
normal source archive is
`a613040357d46f33bf5c59c72a2fc7a8d1830fce9a14fc6d0420d3a46835a75c`.
New whole is 5,687 bytes, saving 36 and still exceeding 4KiB by 1,591.
Its own `034e9d8` exact-head C/Rust and repository lifecycle CI passes, as linked
above. The C job regenerates and runs this maintained entry. This does not
replace other experimental scopes with additional CI engine executions.

## A/F stop-load macro: smaller source, larger whole files

The [fixed qA experiment](../engines/experiments/tiny-af-stop-macro/README.md)
replaces the three A and four F identical relaxed stop-load expressions with
one fixed macro after the final include. The macro still expands at each
original site and retains F's short circuit. All original controls reproduce
twice before the candidate work. Actual full expanded bytes are identical,
and raw macro-line Counters differ only by the one exact new definition.
Both complete candidate natives equal their original full ELF bytes before
either fixed codec call; two independent packages per family reproduce.

The define-inclusive source falls A10,184 to 10,110 and F10,745 to 10,627
bytes. Actual whole files grow A4,980 to **4,983** and F5,083 to **5,087**.
Both candidates are rejected for promotion. Maintained A/F remain unchanged,
and candidate wrapper, DEV, semantic fixture, game and benchmark counts are
zero. No alternative spelling, placement, compiler flag, codec or retry is
attempted. This measured loss is retained instead of inferring whole savings
from source length or starting runtime tests for an unselected candidate.

Thirty-seven ordinary sources close the producer. The raw thirty-tool receipt
is `c3d67f5d81de3f67fa50e9032696406ed66931e191b88a95a55cc336cb944d2d`;
final source/cost index is
`6a78e50f2819950dde3ade2bf55c4bbb5a9ca4230a122e33017b4f6e4f04b0fe`.
All tools terminate without forced cleanup. The producing source snapshot is
preserved; the final README result is the only post-cost source change.

## B storage spellings: distinct metadata class and maintained promotion

The separate [B metadata stage](../engines/experiments/tiny-alpha-storage-bce/METADATA.md)
now measures the same fixed storage18 source under an explicitly different
native-image contract. The original full-native assertion stays failed. The new
qualifier pins both entire files and accounts for the header, section payloads,
symbol/string records and intervening bytes. All program headers and allocated
section geometry remain exact; code/data, dynamic symbols/strings and
relocations are exact. Only the literal build-ID descriptor, section-table
pointer and the specified nonallocated metadata of nineteen object symbols may
change. Local symbol ordering and raw attributes remain fixed; permitted global
symbol order is compared with exact mapped record multiplicity. No stripping,
normalized executable or general ABI equivalence is claimed.

Forty-four pure byte fixtures pass, including repinned structural mutations.
The fixed normal producer first reproduces B5955 twice, then independently
compiles and packages the new candidate twice. Candidate C/E compiles and all
target executions remain zero in that cost stage. Actual whole cost is
**5,851 bytes**, saving 104; shipping source is 13,071, saving 535. Independent
actual-file readback confirms the two full natives/wholes, 26 allocated-section
geometries, unchanged remaining payloads, strict XZ restoration and the exact
compiler-stdin source. Cost receipt is
`d5d4729a808e031f5f76d63e946be00a2e321c16ae47a8bb919d8d723debf9d4`;
readback is `84030a2193e74b2804dbba3d294aae1bd41247583ec1a08a8b9c03b7217fae13`.
The pure fixture loader uses an explicit local import for its documented
isolated Python invocation; the qualifier and its literal policy are unchanged.
The producing 57-source snapshot remains preserved, with only the final result
documentation added afterward.

The [maintained B entry](../engines/compact/tiny-entry-b/README.md) now applies
this fixed mapping through one local embedded-policy helper after unchanged
shared89 alpha. Canonical B, DEV, compiler/profile/codec/bootstrap/launcher and
the existing shared C/E helpers remain unchanged. The three generic scanner/
rewrite function ASTs match the experimental reference. Normal builds consume
eighteen ordinary sources, without experiments, other canonical families,
historical reports or old generated files as inputs. Admission requires the new
full native SHA; it never presents this image as the old B native.

The old seventeen-source normal closure and shipping/DEV files are preserved
and reproduced first. Two independent new source extractions regenerate
shipping and DEV twice each. Both fresh wrappers then pass the unchanged B
verifier: four actual quit/EOF sessions, sixteen legal GO results, new native
identity, stable three-TID startup, no live compiler child/private path and
physical reader/process settlement. New DEV bytes equal the old full files;
there is no new DEV runtime, game or benchmark. Existing rule/search evidence
is reused within the exact canonical/source and machine-code boundary, not
through an assertion of old full-native equality. Cancellation causality remains
unproven.

The final promotion receipt is
`7837cec084aa65e2a7541765fa2a7a60a8050445d14f2fe297e6d0fc7fdacbf6`.
The executed normal-source archive is
`eb6d28e0a58dc8d96035fff51359d1b82c26a8c116635f4690139cf9bc58069b`.
After those runs, README alone removes an unsupported FD-observation claim;
the receipt pins both documentation versions and all unchanged executable
inputs. The first collector's mistaken C-only field lookup is preserved as a
collector failure, not an engine failure; it causes no engine rerun. FDs are
not claimed as observed by the unchanged B verifier. This maintained promotion
subsequently passes exact-head `2a0d99a` CI, recorded above, and remains
1,755 bytes above 4KiB.

## D completion latch: actual output reservation observed

The [D publication observation](../engines/experiments/tiny-d-completion-latch-proof/README.md)
executes the exact unmodified 7,457/7,707-byte scalar/HQ first-cost shipping files.
Its parent fills an empty blocking stdout pipe, then queues GO, a replacement
position and the next GO. Read-only /proc inspection observes a worker blocked
in its actual bestmove write and main blocked in the private futex wait, while
the BSS word addressed by that futex is **pending=1**. Both forms retain the
original futex expected argument three from the earlier wait; that argument is
recorded separately from the current word one. The old result therefore still
owns the output reservation while main is waiting to reuse engine state.

After draining only the parent's filler, both ordered old/new-root results are
independently legal and pending subsequently becomes zero. Two actual wrappers
execute four GO epochs with stable three-TID startup, natural quit and output
EOF settlement, no forced cleanup. Actual own-loader/native identities, RX padding,
mapping permissions and guards, nonexecutable main stack and descriptors 0/1/2
are observed. There is no target code/memory/register patch, personality change,
compiler invocation, game or benchmark in this check.

The exact runtime receipt is
`99320b49fefaa20644a1261bbe82fd29984e6d9d674367b2a6a3643a0c5b28bc`;
source/runtime intake is
`901012de7ebd790e8aea3e87ecae0a88c8bff96276fa3761822880df595b1857`.
Both validator source files are frozen, the existing oracle is raw-hash pinned,
and all six recorded TIDs are absent at final intake. This is bounded output
publication evidence, not general race freedom, new startup/partial-clone fault
coverage, initial zero-BSS observation, cancellation causality or maintained D
promotion. The earlier cost receipt retains its original zero engine-execution
count; these new sessions remain separate. Normal-source promotion and newly
bound pre-entry audits were open at that observation checkpoint; the following
promotion supplies their separate evidence.

## Maintained D completion latch and fixed A/F source costs

The [maintained D entry](../engines/compact/tiny-entry-d/README.md) now regenerates
the exact 7,457/7,707-byte scalar/HQ completion-latch files from eighteen ordinary
sources. Six files change: runtime, build metadata, recipe, exact packer/verifier
admission and README. The twelve other files, including seven native inputs,
loader/codec and fresh driver, retain their raw bytes. Board/search/HQ, compiler,
resources and finite public policy stay within their existing source contracts.
New full native identities and entry points are explicit; no generic page-range
admission or old-image fallback is introduced.

New CHECKPOINT audit images measure 7,480/7,730 bytes. Two independently created
closed source archives and the archive used by the unchanged fresh driver have
identical bytes. Two source extractions independently reproduce eight native,
eight whole and four audit files. Eight actual shipping sessions (four quit,
four EOF) produce 24 independently legal results, and four pre-entry sessions
observe zero BSS/padding and exact restored RX/guard permissions. All twelve
sessions settle naturally with reader EOF/join and absent owned groups. The
routine verifier does not resample the pending latch; the separate actual
output-reservation observation above supplies that narrower fact.

The final source/promotion index is
`8ace0b06b07dcf4d44a12d5210a068ed357f0bf1149c6322f3d8bc77d02f5dd1`;
fresh execution is
`d656183b4a41fbc35fdfb2eb6ca8b786e3e3666ce2c7d970251050703711cc04`.
The actual source archive is
`965f0e33150a02cdbea35efdfe4349ee0486d06e7a37ad3eb49b966d436669f5`.
Partial-clone failure bypass and created-TID joins are source-complement reuse,
not new fault executions. The actual reclamation order is created-TID join,
main return and exit_group; there is no explicit stack munmap or TT free.
New DEV identity, general race freedom, cancellation causality, strength,
scaling and 4KiB acceptance remain unclaimed.

The [fixed A retry experiment](../engines/experiments/tiny-a-source-composition-next/README.md)
consolidates four child-search call sites into one retry-state loop. Its
protected 24,228-byte source complement remains exact. Original A4980 is
reproduced twice first; the sole candidate then reproduces twice. Readable
source falls 69 bytes and shipping source 28, but the complete file grows
**20 bytes to 5,000**. Its new native has the same length and a different full
identity. This is a measured loss, so maintained A4980 remains selected. No
candidate engine, DEV, game or runtime qualification runs. The final 26-source
receipt is `d5c8b61991877935c2645f43ce70197bc5b06878c2290c12e9146c66609e1baa`;
cost is `429597181a78b6ac825078cf5394a3e01076d1f593bfc7ab3b5eacfaae6e0378`.

The [fixed F composition experiment](../engines/experiments/tiny-f-source-composition-next/README.md)
shares nullable legal query/made-child replay, think-owned reset and startup
pending. The complete 15,340-byte search prefix and 1,354-byte MTD driver remain
exact. Its original 73 alpha and eighteen storage maps retain their decisions;
the new source/count domain is separate and literal. Original F5083 reproduces
twice first. The sole candidate independently reproduces source, native and
whole twice: shipping source falls 268 bytes to 10,477; the new native grows
eight bytes to 22,672; the whole file falls **32 bytes to 5,051**. Actual raw
preprocessing alias inversion, macro-definition bytes/multiplicity and header
freshness pass. This is cost evidence only; maintained F5083 remains selected
while new F-specific query/startup/result qualification proceeds separately.
Engine/DEV/runtime executions remain zero in the immutable first-cost receipt
`c9b2cbb83662610965b9ccd1ebc3935f73db605ec5853775836d5abd3c219313`.
The 28-source final summary is
`4c5a0779fbd5aa2c16fbc0a43aa8bbfc5d70d10247c35a26df8b4885603f409d`.
Root independently reads both cost files' actual representations, strict LZMA
restoration and compiler-stdin source; source/archive/frozen bytes match.

## Current C/E storage observation: original string-packing failure

The [current C/E storage study](../engines/experiments/tiny-storage-ce-current/README.md)
uses current C5687 rather than the older C5723 domain. Both original builders
reproduce their shipping files twice before the first candidate native. Its
fixed eighteen-name map reduces C source by 422 bytes and E source by 449.
Only the first C candidate native is compiled. Full native equality is not
asserted: old C is 26,424 bytes and this new identity is 26,344.

The observer passes program headers, allocated section geometry, other payloads
and the seventeen mapped object records, then rejects its complete stored
string-entry Counter. That failure is preserved. C's second and E's candidate
compiles, all candidate codecs/whole files/engines and the later file-gap loop
are zero/unreached. The observer is not edited to turn this result into success.

Independent physical parsing identifies the precise representation assumption:
old global object table references byte 130, a suffix five bytes into stored
tiny_table at 125. New tiny_table remains a local BSS object with the same value
and size, while qq has a separate stored entry at 818. The only extra complete
stored entry beyond the literal mapped Counter is qq. ELF string indices can
reference substrings; this is permitted by the
[ELF gABI string-table contract](https://gabi.xinuos.com/elf/04-strtab.html).
A separately named exact suffix-packing class requires its own source/actual
byte review; no metadata, runtime or maintained promotion is yet claimed.

The immutable original 38-source final summary is
`83ca8460a6d06ddf5def9e6cbd470b3d8f182d6a25e630d1792a07c3034497ed`;
the failed producer is
`dfa01b450ab9fefc1fe795ae8bf8b8f8d0211c364ab92779a1be7250683841e7`.
Root verifies all current raw inputs and the actual suffix/object attributes.
Old B's independent nineteen-pair qualifier and its earlier failure stay exact.

A separate read-only A/F bootstrap audit finds no safe substantive size
simplification. It also narrows prior cleanup claims: existing poll/leader-wait
logic does not establish absence of same-group compiler descendants after an
early leader exit. This is a static control-flow limitation, not an observed
failure of the successful startup sessions or a new executed fault campaign.
The external audit is
`55567a59592a9db13b5027ed57c073087e854441f3fab436df2d3575a50efd38`.

## F5051 functional qualification and separate E5647 first cost

The [F-specific proof](../engines/experiments/tiny-f-source-composition-proof/README.md)
qualifies the exact F5051 source composition without changing its frozen cost
inputs. Old/new optimized and sanitizer query forms compare shipping Board176's
incremental v/h/r, legal children, special positions and atomic replay/history
transactions against an independent 64-square oracle and scalar evaluation.
Five actual pthread startup schedules cover two successful arrival orders and
three expected partial-create failures. A four-GO actual runtime diagnostic
observes positive-pending replacement/position waits, natural own-clock expiry,
result ownership, two joins and subsequent TT free.

Focused old/new DEV1 diagnostics execute six actual think calls. Independent
minimax checks the completed quiet depth-three value and attaining witness.
A new startpos job completes depth one at 31 nodes, then a limit of 32 interrupts
the next iteration while retaining that same job's completed best/score. Old/new
observed states match. This is a narrowly bound diagnostic, not a packaged DEV
identity, search-strength comparison or inherited C proof.

The unchanged F verifier then runs exactly two actual F5051 wrappers, quit and
EOF, producing eight independently legal GO results. New restored-native SHA,
three startup TIDs, compiler-child/private-path cleanup, reader settlement and
physical exit pass. The genuine cost receipt is copied verbatim for explicit
QA artifact admission; the executable link targets the actual mode-0755 first
cost file. FD012 is not claimed because the unchanged F verifier does not record
FDs. Cancellation causality remains unproven. The private stopped/best-reset/
failed-child and bounded nullable-text-work differences remain explicit.

All 61 proof sources, actual snapshots and archive bytes are frozen; the 28
cost sources retain their original bytes. Final proof summary is
`eed7014b750abfdd19381be83091ecf7ede32e60973228dc6b548ed87153a4f0`.
Actual wrapper outer/original-verifier receipts are
`e88aa70a80b473801e5fe2e62e4b73d1fdf83afa0b2a0fa72fd29b4b267b16b3`
and `e595137d5aaa03394dd1f1618eb36896fb40167e4cd9b6bd2ec48843e8b4dc49`.
All 31 recorded PIDs/TIDs are absent at final intake. Normal F promotion remains
separate and must discover and pin its new DEV bytes from ordinary source.

The [separate E composition](../engines/experiments/tiny-e-source-composition-next/README.md)
applies the analogous nullable query, made-child replay, think reset and startup
pending changes to E5679. Its E-only DEV order call keeps tiny_order on the
original position rather than the made child. All 21 coefficients and the
18,042-byte Board/model/search prefix retain their exact source. New local
literal admission keeps the same 89-name map without widening shared domains.

The one candidate measures source 12,339, native 26,376 and whole **5,647 bytes**,
saving 302/32/32 respectively against E5679. Both final representations reproduce
twice; actual full-PP alias inversion, raw macro multiplicity and freshness pass.
Engine/DEV/runtime executions remain zero at this immutable cost checkpoint.
Its 23 ordinary sources are unchanged after execution; cost summary is
`37976679f0b99e2fc4877ea20ff6367cf70d7f253bc169b34ce9a7ab4bff5012`
and cost receipt is
`6857c539c7d881a7e6a897b27f694ac0d2e76634ae64fdda888209b326b35a28`.
The current maintained table is not replaced by this first-cost result.

Actual work includes four control compiles/packages: an outer pipeline pair,
then an unchanged ordinary-builder pair. Two additional pre-alpha candidate
compiles completed before scope correction arrived; their outputs/counts are
preserved and are not presented as required validation. Two earlier preparation
errors stopped before preprocessing/compiler/codec work and remain separate
incomplete receipts. Candidate wrappers are preserved as mode0644; future
execution uses an explicitly bound separate executable copy. Cost tools returned
terminally, but no new group-absence/reader proof is asserted for that stage.
Root independently verifies current sources, both actual representation pairs,
strict XZ restoration and AST compiler-stdin source for E as well as F.

## Maintained F5051 and new size-analysis intake

The ordinary F producer now includes the qualified query/reset/startup change.
Its six changed files use the same fixed alpha73/storage18 decisions in local
helpers; shared domains, compiler, profile, bootstrap and codec stay fixed.
The normal source closure has 17 files. Two independent source extractions,
each with two shipping/DEV builds, reproduce the complete new tuples. Four
actual wrapper sessions produce 16 legal GO results and settle naturally.
DEV source/native identities are newly generated and pinned; DEV engines are
not executed. No previous DEV identity is inherited. Final promotion index is
`af79c02bfca0450c23bd6ef5b4645e81b21614ffb208072045b2aa37ed05b375`.
The maintained file is **5,051 B**, source 10,477 B and native 22,672 B, with
whole SHA `ad4030ad32af47469ca067e4f10c4b60103eddcc6afdfefd22dedea1269052ce`.
Local reproduction and runtime qualification do not claim future-head CI success.

E5647 separately passes old/new optimized and sanitizer query/model checks,
five startup schedules, four actual GO epochs and two unchanged-verifier
wrapper sessions. Its exact model/search prefix remains source reuse; features
12/14 are not observed nonzero and the clamp is not exercised. The 59-file
proof summary is `e5141d5d714061101767d8c6f4b043990282a94011407c845f784e4ffa8228af`.
E remains 5,679 B in the maintained table pending a normal-producer change.

The C/E storage experiment preserves its original failed C string-Counter
comparison. A separate observer admits the exact suffix-sharing class and
checks allocated contents, headers, relocations and remaining byte gaps. Both
final native forms repeat. Two packages each measure **C5603/E5595**, saving
84 B each with the original codec. Strict decoding and AST source/argv binding
pass; candidate engines and normal-producer promotion remain unexecuted.
Its final 46-file cost summary is
`19940b30277a38afedd522eedc78480ec6b85c9448bd96a84e83a357609117ef`.

The user-supplied PR12 size analysis is reference evidence from another
environment. Its reported hashes, codec minima and full-native equality are
not treated as current reproduction. Work now tests independently implemented
function-local name reuse, fixed LZMA1 settings, Rust D's shipping node-accounting
path and D's internal context decoder. Fixed upstream ice4, 4ku, 4kc and STRO4K
sources and licenses are compared outside this repository. No upstream engine
source is vendored or used as a Rove4k build input. Policy differences such as
queen-only generation, twofold repetition and per-GO thread creation cannot
silently become equivalent source compression.

Two other fixed candidates keep distinct dispositions. A's merged castle
emission costs 4,959 B, down 21 B, with a new native and changed private move
order; its focused functional proof is a separate follow-up. B's first-ray
attacker merge shrinks shipping source 11 B but grows the complete file
12 B to 5,863 B. B is rejected before engine/runtime qualification. Existing
maintained A/B images stay selected. The B final summary is
`2dd665666a308b9586560af615815a362612d9442d99bd693d9f13023d5b8c2d`.
Two copied proof control files retain a pre-existing extra blank EOF line to
preserve their exact producing bytes; diff-check reports those whitespace
warnings. They are not functional test failures or silently normalized inputs.

## Fixed-codec reproduction and upstream source comparison

The [fixed-codec producer](../engines/experiments/tiny-source-codec/README.md)
first reproduces the original source/bootstrap/whole pins from `a3546f1` and a
separate ordinary F5051 source snapshot. It then measures one specified LZMA1
9-extreme configuration: lc2/lp0/pb0, BT4, 64-MiB dictionary, and nice lengths
A273/B32/C64/E32/F32. Complete costs include the 77-byte launcher, 13-byte ALONE
header and end bytes. They are observed costs, not sums of prior reductions.

| Fixed source | Original whole | Candidate whole | Saved |
| --- | ---: | ---: | ---: |
| a354 A | 4,980 | 4,980 | 0 |
| a354 B | 5,851 | 5,796 | 55 |
| a354 C | 5,687 | 5,624 | 63 |
| a354 E | 5,679 | 5,613 | 66 |
| a354 F | 5,083 | 5,032 | 51 |
| Separate F5051 | 5,051 | 5,003 | 48 |

Each original/candidate package repeats independently. Six real preprocessing
commands and 24 compression/strict-decode checks run; native/bootstrap/engine
executions are zero. Root separately reads all 54 ordinary source pins and the
six selected physical packages, then decodes each and checks exact bootstrap,
compiler argv and compiler-stdin bytes. This does not qualify future runtime.
XZ-to-ALONE removes CRC64 container checking; exact normal-byte recovery does
not preserve corruption detection. A was already ALONE and is byte-identical.
The other environment's codec-only minima are not relabeled as reproduced.
Final summary: `9856ce3abaeb3d30c9e5258d6600e03f04c952d3d9720d8a4d5e294cc0deb642`.

Comparison uses pinned original sources outside Git. The
[ice4 semantic analyzer](https://github.com/MinusKelvin/ice4/blob/2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19/minifier/semantic_analysis.rs)
and [renamer](https://github.com/MinusKelvin/ice4/blob/2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19/minifier/renamer.rs)
bind declarations/references and group nonconflicting names. Rove4k's new
independent experiment starts with AST-bound automatic locals and parameters,
unique names within each function and reuse between functions. Static/global,
member/type, macro and ABI spellings remain outside that initial policy.

The actual [4ku search](https://github.com/kz04px/4ku/blob/203ddd4bf9b331851c796d8b5d57eac08f6e6c18/src/main.cpp)
shares main/quiescence search and consumes only the remaining selection-sort
suffix. Its side-relative board and packed tapered evaluation differ from the
current A/F scalar model. A/B/F already share their recursive main/QS bodies;
that source does not reveal a duplicate full search body to delete here.
The [ice4 UCI path](https://github.com/MinusKelvin/ice4/blob/2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19/src/uci.cpp)
uses fixed-position clock parsing and joins per-GO workers before continuing
the input loop in its TCEC branch. These are different runtime policies.
Pinned ice4 actually uses an atomic eight-byte TT with a 16-bit tag and Lazy
SMP; it is not classified as a plain single-thread TT implementation. Its
search generates queen promotions and accepts one prior repetition match,
while replay underpromotions are a separate path. Pinned 4ku generates all
four promotions and uses a full-key plain 16-byte TT, default one thread and
per-GO jthreads. Its shared plain stop/TT does not establish Rove4k's coherent
publication contract. The comparison preserves Rove4k's full-key context,
third-occurrence rule, all promotions, B SEE/singular fences and F MTD witness.
The external comparison summary is
`ea5672341e0b73952e49b96ebeb3d3c9311dad46a1497554f6830ec163ad8056`.

The [4kc loader](https://github.com/GediminasMasaitis/4k-dot-c/blob/26e936860c8da80de73ea3041ccade96ba8112a3/loader.asm)
reads a 16-bit output bit count and overlaps executable code with an RWX ELF
header. A 32-bit context stream and guarded RW-to-RX restoration require a
separate Rove4k decoder/layout; a smaller payload alone is no complete own-ELF.
[STRO4K's build documentation](https://github.com/ONE-RANDOM-HUMAN/STRO4K/blob/51ea73a3d86141d96ad428402dc387722fc0f9b1/README.md)
separates its NASM 4K build from the Rust STRO development program. Its reported
4,092 bytes are not a reproduced Rust D result. External source/license bytes
remain outside the repository and are not linked or copied into these engines.

The separate [A castle proof](../engines/experiments/tiny-a-castle-proof/README.md)
runs old/new O2 and ASan/UBSan forms. Each checks 32 selected positions, 749
legal child states, 4,096 attack values and 14 replay states against an
independent oracle. Child sets/full states match; move order changes in 24
positions. Two depth-two castle searches retain score 1,028 and legal witnesses.
The actual 4,959-byte file passes two unchanged-verifier quit/EOF sessions with
its new native identity and no inherited DEV/runtime receipt. This is separate
qualification, not maintained promotion, strength or stack proof. Final proof:
`4396c9af4b5c0b7ea7ee9f68c1333e48925cd6974ce9ecd1035ae68ca6214d0a`.

The [D TT payload-lock experiment](../engines/experiments/tiny-d-tt-payload-lock/README.md)
uses payload bit 63 for slot ownership and preserves full keys. All eight
control/candidate native builds complete. Candidate scalar/HQ native lengths
tie at 8,092/8,480 B, with text +5 B, BSS +4 B and source +197 B. Static
disassembly/ABI dataflow shows Entry24-to-16 and TT request 6-to-4 MiB for the
same slot count; this is not runtime RAM measurement. The original exact-image
packer rejects the new identities. No candidate whole, loader/codec, engine or
DEV qualification runs, and the candidate stays unselected. Final index:
`2c65f9c96e35a767156f7547fa0f3cce25fe25a64469476099cc594ddca079a3`.

## Declaration-bound names and maintained F4839

The [independent AST experiment](../engines/experiments/tiny-scope-names/README.md)
implements function-wide automatic-local/parameter names, restarting the alias
pool between functions. Physical declaration/reference offsets, main-file
declaration and macro ordinals, exact macro-body token signatures, opaque/macro
exclusions, inverse source recovery and reparse binding graphs form its source
checks. It uses external libclang and real resource headers, not copied ice4
implementation. Ten focused fixtures cover capture, initializer shadowing,
macro targets/body changes, static/member/string preservation and asm exclusion.

| Original-codec source | New source | Actual whole | Saved whole | Complete old native |
| --- | ---: | ---: | ---: | --- |
| A4980 | 9,910 | 4,846 | 134 | exact |
| B5851 | 12,485 | 5,659 | 192 | exact |
| C5687 | 11,704 | 5,507 | 180 | exact |
| E5679 | 12,093 | 5,515 | 164 | exact |
| F5051 | 10,011 | 4,891 | 160 | exact, twice |

Two B preparations stop before native compilation: moved macro source offsets
first break external-USR identity; the ordinal retry exposes undefined libclang
declaration attributes queried on a preprocessing cursor. The final producer
uses stable macro ordinal/body/use identities and preserves every edge. It does
not ignore the mismatches. F/A/C/E executed snapshots and both B failures remain
outside Git. The final ordinary experiment has seven source files; final summary
is `f185a2c2fcff2dab9c8607a7b2776bf0d75e8f66137c6e292b6bbe127b976785`.
This v2 index corrects one historical fixture path; source and artifact bytes
are unchanged and the original inventory remains preserved.
There are six actual native compiles and no engine executions in this experiment.

F's actual name-plus-codec composition is **4,839 B**, down 212 from F5051.
It is 77 B launcher plus 4,762 B ALONE stream. Two independent whole files and
strict source/argv recovery match. The 160-B name saving plus standalone 48-B
codec saving is not added; actual combined saving is 212 B. Composition receipt:
`83a25431528e48b503afa4f146b90d1fde9f3fb36c9d2d1dd790926fb0784694`.

The normal F source producer now replays that exact declaration-bound map in
`shipping_scope.py`, admitted only for the complete post-storage input hash and
each physical occurrence, with exact inverse/output checks. No libclang or
external reference source is needed by the maintained 18-file closure. Canonical
engine, compiler, DEV and full native bytes stay fixed; transport changes from
XZ/CRC64 to fixed ALONE/no checksum. Normal shipping and DEV tuples reproduce
twice, and the unchanged verifier runs the new file in two quit/EOF sessions,
producing eight legal results with exact restored native, three startup TIDs,
private-path cleanup, reader EOF and physical exit. Normal build/runtime receipts:
`3802290d2aa8beb3ce464b98ccedea93efeda9afbe430528f4792ff8b3e72ea6` /
`bd4803e0d6c16cf52086d65ac38b0e72fcf26dfca52ead045832b9bd0a407080`.
Producing recipe is preserved before a qualification-metadata-only update.
FD012 is not newly observed by F's verifier; cancellation causality is unproven.

The [C/E core composition](../engines/experiments/tiny-ce-core-size/README.md)
removes C's zero ordering function, consumed selection-prefix writes and the
separate TT write argument. All production writes have bound 1..3 in bits41..42,
so payload is nonzero even for zero move/score/depth. E's real ordering remains.
Twenty-nine selection cases and 189 payload boundaries pass. One control and
one candidate per family cost **C5643/E5655**, down 44/24. Candidate native code
differs and grows 32 B; runtime/repeat/normal qualification has not run. Clamps,
model/AVX2 and other source complements stay fixed. The failed raw `-dM` order
check is preserved; complete definition multiset comparison corrects that
unordered-output assumption. Final receipt:
`e466ab69e833bd5410e6a845f26474babedf0e6d9622898d8a5a2d815f22aadb`.

The fixed external 4kc codec is also actually reproduced: scalar/HQ streams
5,028/5,243 B restore the exact current native through decode and inverse BCJ.
The reference C reader is not bounded at input end, so separate decode inputs
include four actual zero bytes while original payloads are preserved. A new
independent bounded u32/software-CRC decoder and guarded complete ELF first-cost
are in progress. No new complete D result or decoder cost is inferred from the
payload. External reproduction index:
`5af5628f200c3eafe772f320ed751d3f3b7455f9f272aea8712a09d4bcc51ed0`.

The new independent bounded decoder then passes one diagnostic build and two
guarded valid-stream calls, recovering exact BCJ output bytes. A separate
first-cost builds two actual own-ELFs: **scalar6401/HQ6614**, saving 1,056/1,093
from maintained D7457/7707. Actual total is 176-B ELF/PHDR + 1,191-B text + 29-B
u32/model header + 5,001/5,214-B arithmetic body + four real tail bytes; no extra
rodata/padding is omitted. The 1,367-B nonpayload cost is measured rather than
reusing the old 1,115 B. New complete D files are not executed or runtime
qualified, and the encoder is an explicit external-data first-cost producer,
not a closed maintained source encoder. Cost receipt:
`432ec934af089db4d23edf4c3b269ee5e86941634aeb77e88f037c96f232f7a9`.

## Normal A/B/C/E names and separate runtime follow-ups

Normal A now replays its 70-declaration/274-occurrence map, retaining original
ALONE, compiler, canonical engine, complete native and DEV bytes. The maintained
file is **4,846 B**, down 134 B. Shipping and DEV each reproduce twice, and two
unchanged-verifier quit/EOF sessions produce eight legal results. All four owned
files and the 19-file ordinary source closure are frozen; no libclang or
experimental input is required by normal generation. Final promotion summary:
`39310589b4e16d23b82a32fd19839a941ed1f0f7a0b1779d7330a905bc9f032c`.

The static-function experiment first admits only real owned static function
declarations/direct references, excluding address-taken workers, constructors,
macros, external ABI and name observers. Each actual candidate retains all
PHDR/allocated code/data/dynamic/relocation bytes except the exact GNU build-ID
descriptor; e_shoff and nonallocated symbol/string/section metadata also change.
Full-native equality to the maintained predecessor is false. Automatic names
on top reproduce those new static-only natives exactly. Actual combined codec
cost is measured on the resulting source, not added from separate savings:

| Family | Final C | Combined original XZ | Fixed ALONE | Saved from maintained predecessor |
| --- | ---: | ---: | ---: | ---: |
| B | 12,220 | 5,619 | 5,558 | 293 |
| C | 11,455 | 5,459 | 5,395 | 292 |
| E | 11,803 | 5,455 | 5,400 | 279 |

Normal B/C/E now use two exact position-bound replay stages and fixed ALONE.
Each shipping/DEV tuple reproduces twice; each unchanged verifier runs two new
quit/EOF wrapper sessions. The combined 15-file change preserves all canonical,
DEV, bootstrap, shared policy and verifier inputs. Normal closures have 19/19/18
files. There is no Clang, report, upstream engine or experimental source normal
dependency. A stale early C XZ-format check stops one CLI before output/compiler;
it is corrected consistently for C/E and the failed preparation is preserved.
Final promotion summary:
`8280977aa06c274444984dacc1dfab077515eacf1e4a9d1efa687b27418f5bf6`.
An independent read-only source review is clear. These are local normal results;
CI is reported only for the actual later committed head.

The separate B source-sharing candidate costs 5,843 B, saving only eight despite
161 B less shipping C. It shares old/new put updates and exact clock-token
consumption, and forwards continuation piece context. New native code differs;
engine/runtime/repeat qualification is zero. It is not combined with names or
selected over B5558. Summary:
`6faacbe5e5bb85f75287c7e1a7cd651b0cc05c5ab141fa49938e7127580ac6a7`.

The Rust D explicit shipping-node-budget specialization preserves parser,
stop/newgame/infinite/bare-GO policy, local deadline/result counts and correction
epochs. Focused default/DEV/node/deadline fixtures pass, but complete scalar/HQ
costs **11,404/11,770 B**, up 1/8 B. Native length ties at 16,816 B while RX
grows 16 B. The sole candidate is size-rejected without production ELF execution
or more variants. Final handoff:
`69c7d84fe16bda6b8380123fc81acc2fbaa0c10a181ca020f93a8bd44040672b`.

The D context whole then passes four actual scalar/HQ quit/EOF sessions, with
12 independently legal results, exact restored native RX and padding, guards,
three persistent TIDs, stdio-only FDs, absent children, reader EOF and physical
group settlement. The adapter admits only the two new whole hashes and exact
old native/layout/helper inputs, leaving the old verifier main/EXPECTED intact.
At eight map observations no RW interval of at least 32 MiB appears in this
local profile; context-address/munmap causality and CHECKPOINT initial BSS are
not inferred. New RIE/ptrace negative tests are zero. Actual runtime receipt:
`dad61bc39bc3ee777fcbef79081a78a786f7fdeb8e27990c3cd510ccd1d3bc82`.

An independent standard-library Python fixed-model encoder also restores three
small fixtures and both exact native inputs through the existing guarded C
diagnostic. Its two isolated CLI encodes happen to reproduce the complete
5034/5247-byte payloads, without an upstream program or model search. Exact old
payload matching is a comparison rather than a forced termination-bit rule.
Encoder receipt:
`705e720ea01d5eb1f4254c6a8cda646e323d67bf9ffcc4653cb27841bae33b66`.
Closing the maintained D source encoder/audit consumers remains separate work.

## Exact F member names and an incomplete lexical experiment

The exact-F owned-member map renames 13 fields at 57 physical declaration/use
positions, reducing post-scope source from 10,011 to 9,954 B. Independent Clang
reparse preserves the complete 2,463-edge reference graph, all other physical
tokens and all 22 fields' order, types, qualifiers, offsets, sizes and alignments.
The atomic-macro field zb.zN and all external/header members remain protected.
The source-only proof and a separate read-only review are frozen; source saving
alone is not treated as packed saving.

One exact candidate native is then byte-identical to the maintained 22,672 B
native, with no metadata exception. One fixed ALONE package costs **4,814 B**,
down 25 B from F4839. Normal F now replays that map as a second stage in the
existing helper; the original 98-declaration/451-position automatic map stays
byte-identical. Canonical, DEV, bootstrap, compiler, launcher and resources stay
fixed. No Clang, experimental source or receipt is needed for normal generation.

Normal shipping and DEV each reproduce twice. The unchanged verifier passes
two actual quit/EOF sessions and eight legal results against the new wrapper.
Whole SHA is `30240a27c0682519b1d2539c58d153ebaf7dcf4b9d9dde631f985f3c27261285`;
source SHA is `00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916`.
Normal build/runtime receipts are
`522f9c565914bf1fda1cd74cbb7e5133c6e74bdf90198fa4f26d1dbff222e26f` /
`acbde1bf6f0438cb0f16502d1b4a9cc28951d9309333e4e28845841c4eea1e12`.
The independent first-cost receipt is
`2b2eb28b291d10f913e00d78d9eff398608f80fa66785ae6ee3eec08ce43873a`.

The separate lexical alias prototype remains **incomplete and unselected**.
Its first run aborts on an unclassified parameter-redefinition diagnostic;
the second aborts on an unclassified tentative-shadowing int-to-Move-pointer
diagnostic. Both failures and their original incomplete checkpoints remain
preserved. The last checkpoint processes only 20/98 declarations and 56 greedy
trials. A separate final two-parse validation admits its exact forward/inverse,
protected declaration shapes and observed reference projection, without changing
those failed runs into success. Its 10,011 B source changes only two aliases at
four tokens and saves zero raw bytes; native, codec and engine execution remain
zero. Final handoff: `1f57db2fcdb5ef340763889bd9b6d7d41eb81a5153e58a049dc7f6b2c74345b9`.

## Maintained D context producer and fresh pre-entry qualification

Normal D now generates its own fixed H24/base10/u32 context packets from the
eight unchanged native sources. The exact independently authored encoder,
range module, fixed models and decoder are ordinary local source inputs. All
native/loader pins are checked, and the 17 producer inputs are copied before
importing the encoder.
There is no upstream compressor, historical packet, external artifact or
experimental-source dependency in normal generation. The original two native
images, compiler/link flags, resources, native admission and physical verifier
helper bodies remain unchanged.

The maintained complete own-ELFs are **6,401 / 6,614 B**, saving 1,056/1,093 B
from D7457/7707. Their exact shipping hashes remain those of the separately
qualified context experiment. All 1,367 B of headers/loader plus packet framing
and real zero tail are counted. Initial discovery compiles shipping twice and
the two new CHECKPOINT variants once each, without executing them. The actual
audit files are 6,424/6,637 B, with hashes
`07f0a624c85bec6a716cf40a738d6a455c555d6ea230528a4c531ae9d084b59f` /
`854595138f823be31da5d189161ed7e7e802ee8f5dc836c7c534949f9dea3a6f`.
They are explicitly admitted only after source and physical ELF review; no old
decoder audit identity is reused. CHECKPOINT stops after checked context unmap,
inverse BCJ and final RX/BSS protection, immediately before native entry.

The unchanged fresh contract then passes on two independent extractions of
exactly 23 ordinary archive members: local21 plus oracle/LICENSE. Actual native,
whole and audit bytes match across extractions and repeated generation. This
runs eight native, eight shipping-loader and four audit-loader compilations,
then eight actual shipping quit/EOF sessions and four positive pre-entry audits.
Each audit observes the exact restored RX, zero RX padding and rounded initial
BSS, guards and permissions, then resumes the original entry and exits cleanly.
No forced cleanup, errors, retries, RIE/ptrace mutations, games or benchmarks
are introduced. This qualifies the new context path separately from old fault
receipts and from the earlier production-only adapter.

The producing source21 set is
`f32b345cdc1f5b031130dcfe8ca52a5778f310a132af772e7d2208e6390be5e0`.
The source archive is
`4a05643884df255f56e16e50da70c10cb9536b3af1ff7b316a7bf30be924e09f`.
Fresh result/readback receipts are
`3e8ab7c220c5ed26da56dde77fa5b086d4f5f8165518181a10b7676f7611e35b` /
`26ced4a9aa2bdec75f1f16c7018401eec289d0b44b33eda95d59b86c2a098776`.
Post-run qualification metadata is distinguished from these producing inputs.
Current-head CI and 4 KiB eligibility are still separate acceptance conditions.

## Further source sharing: first costs, not maintained entries

The next bounded experiments keep the maintained `e266ea5` sources and exact
admission guards unchanged. Each row below is one physically generated complete
file, including its original launcher or ELF header/loader. Independent gains
are not added together.

| Exact candidate | Maintained whole | Candidate whole | Change |
| --- | ---: | ---: | ---: |
| A local own-side piece expressions | 4,846 | 4,853 | +7; rejected |
| F guarded TT-bound predicate | 4,814 | 4,811 | -3 |
| F EP legality through existing make | 4,814 | 4,808 | -6 |
| F EP plus bound predicate | 4,814 | 4,808 | -6; ties EP alone |
| F shared GO field parsing | 4,814 | 4,812 | -2; separate unqualified candidate |
| F full-key 16-byte CMPXCHG16B TT | 4,814 | 4,862 | +48; rejected |
| D worker-owned reset, scalar | 6,401 | 6,387 | -14 |
| D worker-owned reset, HQ | 6,614 | 6,580 | -34 |
| D reset plus fixed-width inverse BCJ, scalar | 6,401 | 6,313 | -88 |
| D reset plus fixed-width inverse BCJ, HQ | 6,614 | 6,506 | -108 |

F's predicate retains the outer nonzero-bound gate. Its eight decoded-bound /
score-relation truth rows agree even though the isolated inner expression
differs for bound zero. Only nine shipping-source bytes change. The EP candidate
shares the three-square board edit and own-king legality check through `make`.
Its trial child is discarded; a temporarily noncanonical scratch hash cannot
escape to TT, history or results. Its inner EP immediately returns because the
trial capture cannot create a double-push target. Both candidates produce new
native identities and retain separate functional qualification requirements.
The guarded-predicate cost receipt is
`187fd808c759720d23f4777d164d659f05c0a141955612674ff7f21de2777f04`;
the EP cost receipt is
`c59a93ae67cce82b0accac9d743099d663b264d4c1af49402f01afc7a5d816cb`.
One actual combination of those two transformations costs the same 4,808 bytes
as EP alone, despite its 9,916-byte source being nine bytes shorter. It is not
selected over the simpler EP-only candidate. Its separate new native and whole
identities are retained in external receipt
`a1eea975549fb09481cd72ba500f41d2163faf99960b972a0836f6f786c8389c`.

The CAS16 experiment preserves all 64 key bits and all payload bits in a single
coherent operation. It changes contention policy: reads obtain a coherent
snapshot and a failed single store attempt drops its update. Inline codegen and
the added `-mcx16` bootstrap are included in the cost. The first checker wrongly
expected two static CAS instruction sites; the original failure is preserved.
An explicit read-only admission identifies three legitimate sites (read
snapshot, write snapshot, conditional write), reuses the unchanged native, and
allows the sole package measurement. The larger complete file rejects this
candidate without runtime or additional flag/codec variants. The 24-to-16-byte
entry reduction is allocation arithmetic, not a measured RSS or file saving.

D removes the controller's duplicated all-worker result-reset loop. Each worker
clears its own best move immediately before the unchanged `think` reset of
nodes, depth and score. Epoch publication, completion/output reservation and
storage-reuse ownership remain explicit. Scalar/HQ natives shrink by 32 bytes
each to 8,060/8,448; their distinct compressed savings are measured, not inferred
from native lengths. The fixed context packets cost 5,020/5,213 bytes, with the
same 1,367 bytes of ELF header and loader. The first whole-cost receipt is
`c89c7ec1a595ded61c11844352e80f244149eb29088eaa62b3ec6499ce9d2063`.
New-code runtime and pre-entry qualification are not inherited from the former
native identities.

The separate adjacent-declaration inventory finds only two conservative plain
`int ` joins in the exact F source: eight raw duplicate-prefix bytes. No changed
C, native or package is generated for that lane. Its independent policy review
is clear for those two positions, without a general GNU-extension or typedef
chain claim. The inventory is closed without treating its arithmetic target as
a realized saving. Scope coloring remains the earlier incomplete experiment.

A separate source review traces pinned 4ku's side-relative bitboards and
recomputed hash/evaluation, and ice4's absolute board plus direction/sign
parameters. They do not establish a large drop from physically flipping the
current A/F board. The earlier complete flip already grows by 32 bytes. One
smaller six-expression A candidate keeps absolute board/key/move domains and
normalizes only local mover values. Its shipping source shrinks 19 bytes, but
one actual package grows by seven bytes to 4,853. It is size-rejected without
runtime or F variants. The new native differs despite tying in file length.
Its actual first-cost receipt is
`0674ab007661efee495abb350bbac896697cf4691f809b9a32f67671252d9131`.

All compiler outputs, complete files, source snapshots, receipts and external
engine comparisons stay outside Git. Only independently authored experiment
sources are committed. No third-party engine implementation is vendored; no
games, training, AWS or target many-core benchmark is part of these costs.

The EP-only candidate subsequently passes one diagnostic fixture with 16 EP
roots, 106 full real-child states and three replays against the independent
board oracle, then both actual 4,808-byte shipping quit/EOF sessions with eight
legal results. The diagnostic uses the same readable EP change, without a
substituted search or function-instrumentation observer. Existing-image
disassembly shows the local EP attack chain growing by 256 stack bytes from
432 to 688; search's own 4,432-byte frame stays unchanged. Bounded recursion is
source-proven, while final-target stack and speed claims remain unmeasured.
Actual selected-wrapper runtime receipt is
`53f620c73bec830835374c5662373b4492dabb695497782ad80aeaff0695b745`.

The reset-only D images subsequently pass four actual production sessions
(12 GO epochs) and two existing output-publication cases (four GO epochs).
The latter observe pending=1 while the old result write is blocked and the
controller waits, then legal ordered old/new-root results and pending=0. Both
forms preserve the restored native identity, RX/BSS permissions, guards,
persistent TIDs, stdio-only descriptors and natural exit/readers. This is
post-entry ownership evidence, not initial-BSS or pre-entry audit evidence;
cancellation causality stays unproven. No substituted search, target writes,
fault campaign, compiler or codec is added. Actual receipt is
`bb01f2daf8960b73a2cb81b51776249d0ac25b5aca98c1d1f2754953d4894476`.

The further D BCJ candidate replaces only byte gather/scatter with two
four-byte `__builtin_memcpy` expressions on the fixed AMD64 little-endian
target. Actual codegen is one unaligned 32-bit memory add, with the same
opcode test, bounds, modulo subtraction and five-byte skip; no copy helper
or new dependency appears. Two loader compilations reuse the exact reset
native/packet pair, without native compilation, encoding or target execution.
Loader text falls from 1,191 to 1,117 bytes; all 176 ELF/PHDR bytes are counted,
so total nonpacket cost is 1,293 and complete costs are 6,313/6,506. The source
literal inverse and independent codegen review pass. This is an actual reset
plus BCJ composition; new-loader restoration qualification remains separate.
Cost receipt:
`86679cee87d5ac07b574b5da82c0edc65756e6fbbeddf53c1cd7ef90fc6dbb3c`.

One standalone F GO-parser candidate also shares time/increment token parsing
while retaining both assignments inside the own-side condition. Exact token
consumption, number parsing and last-value policies are source-reviewed. Its
source shrinks 58 bytes but whole only two, to 4,812; native identity changes.
It is not combined with EP and receives no parser-runtime or normal-promotion
claim. Cost receipt:
`cc40b3ba82fe6961328c52e2a01750954a99acc550ae753735bc8117dad907f5`.

## Maintained EP-only F and worker-reset/BCJ D

The selected normal F pipeline now applies EP source sharing from ordinary
`shipping_semantics.py`. Its readable body is the semantic source for both
DEV-before-specialization and shipping-after-members. The old engine base and
all alpha/storage/scope/member guards stay byte-identical. The fixed helper
checks each exact source identity, readable/shipping role relation, literal
occurrence, protected complement and inverse. Normal generation imports no
experiment or historical artifact. Its fresh archive closure includes the
helper through the existing recipe helper list.

Normal shipping source/native/whole/bootstrap reproduce twice at
9,925/22,672/4,808/10,924 bytes. The newly identified DEV source/native also
reproduce twice at 19,488/26,984 bytes; they are not labeled equal to old DEV.
The unchanged selected-wrapper verifier passes two actual quit/EOF sessions
and eight legal results on the normal 4,808-byte file. Source/native/whole
hashes are
`3549063cbdca22c83536e0879b5e7baff8c7cbef3b5911f4152850732c86300c` /
`9b4ca00fd54b67c33c01e92389c4f9130751233633faa828b6eb46e3b20890db` /
`93377e104d934d5bde1e8c7a491b54b72d0a7a6e9d40b845f94f86bc0c2f6956`.
The actual normal build/runtime receipts are
`0fc04401edd284fe072f2ff43d1c2489713944b1b44a06345f3e91d77e676777` /
`49e6a6ed062667ca94fdc338ab6a73a2f3fb71a14cd71cb46328eda6c5c2a18d`.
This selects EP alone: the bound-expression combination ties in whole cost,
and the GO-field experiment is not silently composed with it.

Normal D now owns both the worker-reset runtime and the fixed-width BCJ loader.
Only those two runtime bodies change. Exact native admission is updated to the
new 8,060/8,448-byte pair, with its literal entry and private mapping geometry.
Encoder, range math, fixed models, decoder, linker, flags, profile and other
seven native sources remain unchanged. Packets and shipping whole identities
match the actual independently measured reset/BCJ composition. No external
program or experiment is required by normal generation or runtime restoration.

The new audit files are discovered without target execution, then statically
reviewed and explicitly admitted: scalar 6,336 bytes with SHA
`93df62352f49aee0d01e4022c6a7acc773593255dfa252c28a200d3e521df905`;
HQ 6,529 bytes with SHA
`9bf7165d3840488c9cdd674caa2e7cb2379c6d6eed917005cd8ce2d48129a8fd`.
The source CHECKPOINT still follows checked context unmap, inverse BCJ and
RX/BSS protection, immediately before native entry. Old audit identities are
not reused and the physical verifier helper bodies stay unchanged.

The existing fresh contract passes once on two independent extractions of the
same 23-member ordinary archive. It actually runs eight native, eight shipping
loader and four audit loader compilations; eight shipping sessions with 24 GO
epochs and four positive pre-entry audits pass. Exact native RX, zero mapping
padding and rounded initial BSS, guards, NX permissions, original entry resume,
readers and natural group exit are observed. No forced cleanup, target writes,
new fault campaign or retry occurs. A readback-only tool-schema mistake is
preserved separately; correcting that observer does not rerun or relabel the
completed fresh execution.

The producing source archive is
`f8a86aca8e0632d34f10d9a99d53b9ad6382e76420264853158b1b899ae010c6`;
the actual fresh receipt is
`e4838c7aeed82688983244a1fb91f85c570e35a51433570015f20d4d2aa20c0c`.
The complete shipping files are 6,313/6,506 bytes with SHA
`66f70074da2270f1d6aa33beb50c1f34038b4bc36e4272d748c1720935fb4a9a` /
`7ba4858dcf40c837d107f865e14b82d19ede40570059dcff1ca4bd3012ff7234`.
Post-run README/qualification metadata is distinguished from producing inputs.
These normal local results are separate from the next exact-head CI, final
resource/profile, strength and 4 KiB acceptance conditions. No family is yet
size-eligible, and all twelve independent cores remain in scope.

## Further source compression after the EP/BCJ promotion

The next isolated candidates start from committed `9e2a152`, rather than the
attachment's older `a3546f1` baseline. Their measured savings are not added to
earlier standalone experiments. First-cost recipes were kept separate until
source generation and focused functional validation completed; the later
normal-promotion section records the resulting maintained entries.

| Candidate | Maintained whole | Actual candidate whole | Difference | Current evidence |
| --- | ---: | ---: | ---: | --- |
| A shipping text profile | 4,846 | 4,766 | -80 | Focused input, normal reproduction and actual wrapper pass |
| B incoming-move SEE | 5,558 | 5,546 | -12 | Focused SEE, normal reproduction and actual wrapper pass |
| C structural composition | 5,395 | 5,344 | -51 | Focused TT/sort/eval, normal reproduction and actual wrapper pass |
| D scalar residual leapers | 6,313 | 6,272 | -41 | Focused board/oracle and normal fresh/runtime/pre-entry pass |
| D HQ residual leapers | 6,506 | 6,452 | -54 | Same focused and normal fresh scope |
| E structural composition | 5,400 | 5,366 | -34 | Focused TT/sort/eval, normal reproduction and actual wrapper pass |
| F shipping text profile | 4,808 | 4,735 | -73 | Focused input, normal reproduction and actual wrapper pass |

The F candidate shares the own-side clock classifier, uses bounded `strtoull`
admission and replaces the byte reader with a bounded text-line loop. Clock
fields remain order independent; absence and an explicit zero retain different
budget meanings. It explicitly selects NUL-free text and exact first command
tokens, so malformed extras and leading whitespace are a changed input policy,
not universal parser equivalence. Search, TT, MTD bounds, worker publication
and physical output ownership are outside the changed source regions. The
compiled 9,728-byte shipping source and 18,576-byte native have new identities.
The initial readable DEV wrapper has a missing directive newline; that separate
uncompiled representation is preserved as a failed preparation and cannot be
used as normal-generation evidence. A boundary-only producer correction now
creates readable `fe1309f3...` and exactly the same compiled shipping source;
it adds no compiler or codec run and does not yet establish DEV generation.

The D candidate preserves slider handling and specializes only its residual
pawn/knight/king path. The old inner ray always stopped after its first square
on this admitted piece domain. Attack-before-friendly filtering, direction and
promotion order, EP and castle paths remain explicit proof obligations. Native
size falls 96 bytes in each form; BSS, guards, NX and the existing two/three-page
RX layout classes pass static checks. The actual first-cost receipt is
`96e7eda66d500b312e93f47b42fe55896f8f0f10bbf14ebfd8da6b84b14bc443`.

C/E sentinel, consumed-prefix, inactive-clamp and C zero-order changes have
now been measured with the current names and codec. The actual 5,344/5,366-byte
files save 51/34 bytes, rather than the sum of old standalone measurements.
Native images each grow 24 bytes and have new code identities; no metadata
exception is used. C still contains actual AVX2 gather and horizontal-add
instructions, and E retains all 21 coefficients and its inner clamp. The cost
receipt is `69b2553811f983744e9a0a33e5e9590076a983c472ffa5c4db4358844879d689`.
Focused fixtures and selected wrapper checks remain separate from this cost.
A separate B proposal shares initial and recursive SEE move/gain
ownership while preserving full legal minimax and incomplete-result fences;
its initial 84-byte code projection was not a shipping or whole-size result.
The sole actual candidate now saves 72 bytes of final C, 32 bytes of native and
12 bytes of whole, yielding 5,546 bytes with SHA
`70e5ea64a97efaa84385a429bca84bad2924a5256c478973cc2798a4b070ad2f`.
It changes the recursive helper's internal return meaning to incoming move net
gain; the full legal recapture tree, all promotion choices, incomplete fence,
singular policy and excluded-root learning/TT rules remain explicit obligations.
No LVA approximation or playing-strength claim is substituted for them.

The same fixed text policy is independently ported to A's actual source/name
domain. Its 9,713-byte source and 4,766-byte whole are measured with A's own
original ALONE preset; F's nice32 setting and 73-byte saving are not reused.
The new 22,672-byte native has SHA
`28260858a130711bb5fa70816e950b7666440168e8835bb4802b98675b972422`;
the actual whole is
`8a783ff2d0f5d3546e54dba3d8c4c5931ba9b72c95270deca69eeabd33136226`.
This first-cost uses one compiler and one compression, with no control rebuild
or runtime qualification. A's focused validation follows separately.

The next focused checks pass on the actual changed source, with original
failures and first-cost producers preserved. B's single fixture covers 38
score/visit rows plus seeded visit-limit, cancellation and expired-deadline
cases; these are not million-node searches. Its search/TT/singular/learning
caller bytes remain exact, and its actual wrapper passes two quit/EOF sessions
with eight GO epochs. New recursion stack capacity is not qualified. Proof:
`fbdca8c590e7dabaf6d21d0e1b49cb075f5abfc9f86e291ad76da8cda1230421`.

C/E each pass 26 TT, 29 sort-suffix and 39 admitted-board cases in one compiled
fixture. C additionally checks 768 piece-square pairs against scalar/AVX2;
E checks all coefficients and 938 ordering values. Two nonadmitted E clipping
examples are labeled separately. Four actual wrapper sessions produce 16 GO
epochs with exact new process images and natural quit/EOF settlement. D's two
compiled fixtures each pass 12 roots, 177 full board records and 22,656 attack
queries against an independent oracle; scalar/HQ raw states and move order
match. Its shipping execution and new pre-entry audit are still pending.

F's one compiled fixture passes 25 numeric, 26 GO, 25 transaction, six special
root and 96 full-child checks. Its workerless manual publication setup does
not prove physical SMP. That evidence comes separately from the unchanged
verifier's two actual sessions/eight GO and one actual text-only session.
The latter observes LF-before-length 32,767 admission, 32,768 draining, CR's
contribution to the CRLF boundary, final EOF and exact command-token policy.
The functional/runtime/text receipts are
`5311a603eef2910af95582d4e8db155ac02f4bb41a49bee5c023fd07a1442113` /
`cb93679523bc078b7554a5f99bcf2ff47cf40e5588618d86540cb5bddbad53fd` /
`f55ce1a122c83fab585461910d4f7ce3cc67be8d78fd82ddb4409ac046760491`.
Natural physical settlement does not establish cancellation causality.

## Maintained text, SEE, C/E core and D leaper specializations

All six measured source changes above now pass their normal local generation
and selected-file checks. The maintained table near the beginning reflects
4,766 / 5,546 / 5,344 / 6,272–6,452 / 5,366 / 4,735 bytes. Each cost is the
actual complete file at its unchanged family codec settings; independent
standalone savings are not summed. No family is yet within 4,096 bytes.

A/B/C/E/F each run their ordinary builder once, reproducing shipping and DEV
twice. All five DEV tuples are compared with their prior full source/native
identities and match. Each unchanged normal verifier then runs its actual new
whole file for quit/EOF sessions and eight legal GO epochs: ten sessions and
40 GO in total. The newly added ordinary helpers are recipe-pinned and need no
experiment, historical artifact, upstream engine or Clang installation. Their
ordinary closures are A20/B20/C20/E19/F20; fresh extraction is not run for these
five in this checkpoint.

B/C/E apply exact production-domain source transformations only after their
unchanged spelling/scope guards. Original readable and diagnostic APIs remain
available for their broader domains. A/F additionally feed corrected dual
readable input into DEV specialization, where the original diagnostic branches
are selected; their original canonical bytes still reach every old shipping
guard. A/F text policy counts CR among the 32,767 bytes before LF, preserves
order-independent clocks and explicitly selects its documented malformed-input
behavior. This is source-level specialization, not a native-byte rewrite.

The normal A build/runtime receipts are
`b53178618951654aa0ab9bd1d5413162eff6a0de8178b9fc083af2d3b12e09a9` /
`822bf19b4c150ca784bed9272399f9d0ef03de4a58f2da428798e1e98c9309d0`.
Its focused fixture and three actual wrapper sessions pass the same explicitly
bound input policy on A's own code and new native. The normal B receipts are
`f43079a91203007704789a62bdaa5e73403af9153870427c4e3d56588e35a069` /
`3554ba9a0a05d6d34453f5c7ae75cbe580101bd6820ba7c64bbbf12b08bc642d`.
C/E's combined normal receipt is
`f20d8f40bdb099af8a359f24a4b3f5c387f0550c16bd7438a0dd84ee8239a05a`;
their final summary is
`eeb670a30cd6d429a4f0788df232d803adebb1b91c4e72af0d9ca470c1323e81`.
The normal F build/runtime receipts are
`dd8d4d81057cb5352b51831eca446b6d43716027873442e785a419e8bddc79af` /
`b837a43829868645ac82e6f158c41247380f2d761df2eb5687858fc7bfbf2eeb`.
The new shipping native identities are explicit; old metadata-only or stack
observations are not extended to the changed code. Final recipe qualification
metadata and README results are kept separate from the exact producing files.

D changes its readable board walker itself. Seven other native inputs and all
encoder, model, decoder, loader, linker, flags, resources and observer bodies
remain unchanged. Two new CHECKPOINT files are discovered without execution,
then their exact bytes and layout are independently read before admission:
scalar 6,295 bytes / `ce72966846e52a7f72d49c577ad9eb799fd81b195308b5e02def39cf84526b8f`;
HQ 6,475 bytes / `3660dc07190104f062fabe57e2f0603df21d94d47aa9c41cb487204f2a4f4547`.
The unchanged fresh contract passes on two independent 23-member ordinary
source extractions. Eight native, eight shipping-loader and four audit-loader
compilations reproduce the new identities; eight shipping sessions/24 GO and
four positive pre-entry audits pass. Exact restored RX, RX padding, rounded
initial BSS zero, guards/NX, original entry resume, stable workers, readers and
natural exit are observed. There is no target mutation or negative campaign.
Actual fresh receipt:
`3a32b4420c299c2f826cf90d7c8760578e275abb7da16179dc5c00936a2c82c5`.

The shared experimental-source head `72d5e70` passes both C/Rust jobs in
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39426741555) and
[repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39426741244).
That run exercises the preceding selected recipes. CI of the later normal
promotion is reported separately for its committed SHA in the draft PR. Final resources,
target hardware/scaling, remaining size gaps and strength validation remain
open across the complete independent C/Rust portfolio.

## Maintained C residual-vector evaluator

The following C-only checkpoint changes the maintained complete file from
5,344 to **5,245 bytes**, a measured 99-byte reduction at the same compiler,
profile, bootstrap and ALONE settings. Shipping C falls from 11,284 to 11,086
bytes and native ELF from 26,408 to 26,376 bytes. The other five maintained
families remain at the preceding table values. C is still 1,149 bytes over
4,096; all six family size gates remain open.

The shipping evaluator replaces the 13x64 table, its constructor and gather
leaf with sixteen local signed-16 features. Each color contributes six piece
counts, its own-perspective positional residual and one zero lane. Weights
are the original material values plus residual weight one, with opposite
signs for black. Residual is sign(piece)*value(piece,square)-material(kind),
including the negative king-center coefficient. It is not abs(value).
Within the admitted sixteen-pieces-per-color domain, residual prefixes are
bounded by 1,008, counts by 16, and the signed dot/reduction uses 32-bit sums.
The conservative raw HCE bound remains 29,120.

An actual YMM `vpmaddwd`, extraction and horizontal reduction feed the side
multiply, search evaluation and QS comparison in the new native. Both vector
halves carry evaluation data. This is a new full native identity, not a dummy
SIMD operation or a metadata-only exception. Board/put/make/hash/context,
capture ordering, TT and search remain outside the changed source fragment.
Speed, strength and target-stack effects are not measured by this checkpoint.

The fixed new ordinary `shipping_simd.py` runs after the unchanged core stage.
It owns its readable/shipping literals, exact canonical and post-core inputs,
paired token roles, positional inverse, untouched complement and final source
identity. It imports only hashlib/re and consumes no experiment, external
report, executable or Clang installation. DEV bypasses all shipping stages;
the original readable source and existing guards remain unchanged.

Focused diagnostic v1 failed compilation because its fixture used canonical
field `half` on shipping struct `za`. That failure is preserved. Explicit v2
changes only those three fixture field tokens to the actual `zL`, with exact
inverse/complement, leaving the candidate and v1 records unchanged. One v2
compile/run passes 3,399 assertions: 832 piece/square components (not legal
full-board claims), 39 admitted-shape boards, ten special children and 98
side/padding probes each. Actual raw SIMD scores match an independent scalar
formula. Its result is
`47567e88e61d660b4f015778c54d47093271e784ba66534a3c85b0ed422a69a9`.
The actual candidate wrapper passes two quit/EOF sessions and eight legal GO;
receipt `ad108b597a8263a3f860c6054f2764dc5daa47ba5e6b8b63ec06da1bc5dd05d0`.

The normal builder then independently reproduces shipping twice and DEV
twice. Source/native/whole/bootstrap match the measured candidate, while both
DEV source/native tuples actually match their preceding full identities.
The unchanged normal verifier passes two additional actual quit/EOF sessions
and eight legal GO, observing the new process image, stable startup TIDs,
unlinked private paths, readers and natural physical exit. No fresh archive
extraction, extra candidate, game or benchmark is run. Cancellation causality
remains unproven. The ordinary C closure is now 21 files.

Normal build/runtime receipts are
`c07ff5af9bceeed62ecaaf3f2fb36d20ca6ec76f4ce5f76ad511ccdfc82124ad` /
`11d28534dda26349dadeff13a2d606cdd1f7127aada4e5e9bdb3a43d5e187361`;
combined normal receipt is
`d36cf1eea2697d24af6bcd33c3c24bd08faf9171028e8f0ee23863dfe1bc8436`.
New source is
`90a566c5e814cf87dd38f92f40ce8fe7115c4d4d07f75d9ff0981ffaae1fbc28`,
native `c32772b3d1bb9ce985bfdecbd31dc4cc5fd06721f03aa6259a4021a4fbb0c788`,
whole `de57a0a21e8ecb2f958207c3e71bcc7d791448340acc103faaea5f1010433933`.
Producing sources/recipe and later completion metadata remain separately
preserved. The frozen experiment records its first-cost stage only.

The preceding normal head `d982717` passes both jobs in
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39431496618)
and [repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39431496637).
CI for the later C promotion is reported separately against its actual head
in the draft PR. Those earlier successes do not accept a future source.

A separate source-only A/F review finds that nullable parse can share the
terminal branch's first-legal-move scan. Its estimated 20-35 compact C bytes
per family are unmeasured, with no candidate or whole-size saving included.
The next structural work is prioritized against the complete family gaps;
the twelve independent cores, final resource profiles, parallel comparisons,
target hardware/scaling and strength validation remain open.

## A/F terminal witness: source shrink with complete-file regressions

The previously unmeasured nullable-parse/terminal-witness proposal is now
measured as one fixed candidate per family. Unchanged text/query definitions
move before search; the terminal branch reuses the query, and ordinary move
generation moves after that branch. Exact span inverses and every untouched
gap are checked. Each compact C file loses 23 bytes, but A's complete file
grows 4,766 to 4,775 bytes and F's 4,735 to 4,738 bytes. Both candidates are
rejected for size; the maintained A/F selections remain unchanged.

Each family runs one stdin native compile and one fixed ALONE encoding,
sequential A then F. Strict bootstrap/source/argv recovery and independent
CLI decode pass. Native byte counts stay 22,672/18,576, but full identities
differ; equal sizes do not establish native or runtime equivalence. No
functional fixture, native/whole execution, DEV build, normal promotion,
control compile, retry, game or benchmark follows these losses. Owned groups
are absent and handles terminal. The exact compressed-size cause is not
isolated, so function relocation is not counted as a general size benefit.

Actual A/F cost receipts are
`c3ad15651a1475be95ddea0cc31088ebd75291614666b6291776386f89e72a55` /
`a70c80138f64689c6d9d8b479f30642ad099f3dbd6466429829f26dcb3dd7a28`.
Final experiment handoff is
`5a4cbe7bd69cd09e4b251114e196c3abbf941c2e5bb231b2cc613d9bc79e815b`;
five ordinary experiment files are frozen separately from generated artifacts
and producing snapshots. The measured 92dfc34 normal selections pass both jobs
in [C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39437607789)
and [repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39437607775).
Later WIP experiment heads report their own CI separately in the draft PR.
