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
