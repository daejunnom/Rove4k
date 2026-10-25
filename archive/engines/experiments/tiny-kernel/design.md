# Direct kernel experiment: frozen architecture hypothesis

This folder owns one independent source architecture. It does not alter the
optional canonical TinyA, earlier experiments, shared scripts, CI or release
policy. The source control is this repository's own previously qualified A
readable structural winner, copied as `control.c.in` with SHA-256
`109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`.
Its fixed historical spelling/compiler/bootstrap/XZ recipe must reproduce the
actual 5,283-byte control before any candidate measurement is accepted. No
external engine implementation is copied and no new rename/flag/codec sweep is
part of this experiment.

## One direct body and typed modes

`kernel.c.in` contains one recursive function with explicit `KernelMode`.
`emit.c.in` supplies its one C macro body. Generation holds `from`, `to`, the
original mover/type, promotion and target as locals. The macro constructs and
validates the copied child and directly searches it. There is no callback,
function pointer, visitor/fact/node framework, iterator context, runtime
trampoline, shipping move array or separate packed-move decode/make handoff.

The modes have deliberately separate meanings:

| Mode | Meaning and ownership |
|---|---|
| `K_ATTACK` | Geometric protection by the requested absolute side. Test the queried square before friendly occupancy blocks a ray. Include pinned attackers and friendly protection, exclude pawn pushes/castles. Never copy/apply a child, claim nodes, touch TT/learners or consult cancellation. |
| `K_FIRST` | Return one legal packed witness, ignoring search cancellation. The parent remains unchanged. |
| `K_MATCH` | Match one validated packed input against generated candidates, then return its fully formed legal child. No output is written on failure, so transactional replay owns its commit. Aliasing is safe because the child is local until the final assignment. |
| `K_COLLECT` | DEV-only collection of all legal moves, with an explicit capacity check. Compatibility `gen`/`make` are absent from shipping. |
| `K_SEARCH` | Claim one node, preserve mate/draw/PLY precedence, probe/publish the coherent full-key TT and recurse with private learning and key-path push/pop. |

Existing geometric walking already unified generation and attacks in the
control. That existing unification is not a claimed new saving here.

## Rules and state ownership

The board representation, absolute signed pieces, incremental white HCE,
canonical FIDE position key, reversible ordered TT digest, halfmove clock,
king coordinates, rights mask and admitted piece inventory are unchanged.
For each selected candidate, the direct body copies the immutable parent,
removes the old state key, applies EP capture/promotion/rook displacement and
rights updates, rejects king captures and resulting own-king attacks, normalizes
the new EP square through a scratch geometric attack test, adds the new state
key and computes its path digest. Four promotion pieces are emitted separately;
the original pawn local is never mutated between them.

Ordinary pins, EP discoveries and castle destination attacks are checked after
applying the child. Castle generation retains origin/transit safety and empty
path checks. Admission and rights updates preserve the required rook witness.
EP normalization calls only attack mode, which never normalizes EP recursively.
Each successful transition is a complete child before output or recursion.

FIDE third repetition scans the same same-side history window bounded by the
halfmove clock. Dead material retains the same exact minimum rules. A draw or
PLY-cap node first seeks a legal witness: absence preserves mate/stalemate
precedence; a legal cap witness aborts the unfinished iteration instead of
publishing a static leaf. Only search owns a key-stack push, and every such push
has its pop before cancellation can return. The existing startup pool, clock,
protocol, reset/stop/quit/EOF and physical result publication remain unchanged.

## Explicit search-policy change

The fixed policy is frozen before the first size measurement:

1. Sweep 0 snapshots `history[from][to] + continuation[prior][mover+6] + jitter`
   for every pseudo-move ordinal. No descendant or learner update runs here.
2. Sweep 1 selects the TT move.
3. Sweep 2 selects every other capture, EP capture or promotion.
4. Sweep 3 selects remaining quiet moves whose snapshot rank is at least 32.
5. Sweep 4 selects every remaining quiet move.

The jitter formula and worker identity are retained; jitter alone is 0..16 and
cannot cross 32. Positive cutoff learning can move a quiet from stage 4 to stage
3 through history or continuation, which requires an actual reachable-learning
and ordering-effect proof. Within a stage, geometry order is fixed. This is not
the control's total-score selection order and does not claim equal nodes or
strength. Search visits source files in `file xor (worker_id & 7)` order;
non-search modes keep absolute file order. This makes the startup workers'
fresh, untrained search orders differ as well as retaining the jitter formula.
There are at most eight fresh source-enumeration patterns; this does not claim
512 distinct orders or a scaling result.
The declared cost is at most five whole-board generation sweeps per
searched node, rather than a full rescan per selected move. Snapshot ranks are
one bounded integer table, not a move list or seen bitmap.

Every pseudo emission increments the same ordinal in every sweep, including
illegal candidates and king-capture candidates. Assignment
`TT ? 1 : tactical ? 2 : rank >= 32 ? 3 : 4` is exclusive. `legal` increments only
after the selected stage's complete own-king test, so stage 0 never changes PVS
first-child state and no candidate is counted twice. A quiet TT witness in QS
does not skip later capture stages; stand-pat reaching beta may finish after a
legal witness. Mate-score conversion, raw HCE TT scale, locked full key/payload,
PVS retries, selective LMR, private history/continuation and learned correction
remain present. Mutable correction changes only selective reduction eligibility.

## Cost-first stop rule and evidence limits

After independent source review, compile one fixed profile, reproduce the
control, and independently repeat source/native/whole-file production. Report
the first complete-file result before a large proof campaign. A size loss ends
architecture exploration and receives only bounded targeted correctness proof;
no second pool/kernel variant or tuning sweep follows it. Runtime/ELF execution
of a package, algorithm feature activation and full rule acceptance are separate
evidence classes. No size alone establishes those classes or 4K eligibility.
