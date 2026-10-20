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

**No family has a verified complete file at or below 4,096 bytes.** All twelve
cores have functional evidence, but portfolio completion still requires source
reduction, D's eligible own-ELF artifact, final candidate comparisons and games,
and selected profile/resource and target-hardware evidence. The first matched
C/Rust structural comparison and the twelve original target512 short searches
now have their own bounded evidence; these do not accept future smaller cores.
Startup-only evidence and small-profile games have the narrower scopes below.

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

WSL2 Ubuntu 24.04.4, x86-64, glibc 2.39 is available locally. Initial tools:
GCC 13.3.0, Python 3.12.3 and Rust 1.97.0. AVX2 is exposed; AVX-512 is not.
WSL execution explicitly selects the existing `stemxstudio` account.
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
