# A–F engine implementation checkpoints

The full implementation scope is recorded in [the accepted plan](ENGINE-PLAN.ko.md).
The current user request excludes training and AWS connections. Frozen model
inference and lossless model storage remain in scope; trained strength is not claimed.

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
