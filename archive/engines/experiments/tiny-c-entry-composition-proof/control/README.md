# One C query/reset/startup composition

This is one fixed source candidate based on the maintained C5723 ordinary
source. It combines nullable-text/made-child query sharing, worker-entry job
reset ownership and a pending-owned startup arrival barrier. It uses exactly
seven literal replacement sites. There is no engine-family, representation,
compiler, resource, codec or packing variant selection.

`control/` owns the 17 ordinary files needed for the old C maintained recipe,
including its readable source, recipe, unchanged helpers and verifier sources.
No normal input comes from a live maintained folder, historical result, old
executable, generated source or network service. `candidate.c` is the readable
new C program. `transform.py` independently admits the old readable SHA, applies
the seven literal sites, checks the exact candidate and restores the old bytes
with an inverse. Every byte before `void think` is unchanged: Board layout,
shipping DEV-v guards, king-capture/list guards, rules, PSQT constructor, actual
AVX2 gather/reduction, TT and search remain C's original implementation.

The candidate removes the separate `first` walk and returns parse's already
made child to replay. A null text asks for the same first legal generated move;
callers provide separate child scratch and discard it on failure. Think clears
best with its existing nodes/depth/score reset; GO no longer loops over worker
reset fields. Startup borrows pending, initialized to WORKERS, and worker entry
decrements it under the existing mutex. Startup never calls result. Successful
creation uses the old wait; partial creation still jumps past that wait into
shutdown and joins only created workers.

Two private differences require future C-specific qualification: direct think
now clears a preseeded best, and startup wait leaves stopped=1 before first GO.
GO clears stopped before publishing its epoch. A's proof is design background;
none of its hashes, phase diagnostics or executions qualify this new C source.
Existing shutdown/join-error behavior is not strengthened.

The old 89-name spelling map is unchanged. The owned `policy.json` admits only
the new candidate's separately fixed source/count domain. All aliases remain
the old spellings, with no new name discovery. Exact counts, opaque regions,
PLY uses, arithmetic, independent opaque scanner and lexer/repeated-rewrite
agreement are required. The old guarded public alpha function remains unchanged
for the old control; candidate policy calls only its generic pure rewrite.

The fixed profile is two search workers plus input, TT_BITS=18 and PLY=128.
The fixed C compiler, -pthread/-mavx2, bootstrap and 75-byte XZ/LZMA2 launcher
recipe are unchanged. Before codec use, actual full-compiler-expanded source
must pass an alias-only inverse without whitespace or numeric repair. Full
final macro definitions/resources must match as raw lines with multiplicity;
GCC's symbol-table-dependent dump order is reported separately and is not
claimed byte-identical when only line order differs. No definition content or
whitespace is normalized. Candidate full-native ELF before and
after the spelling transform must be identical. This identity proves only the
spelling boundary; the structural candidate is not equated with old C native.

On the qualified Ubuntu environment:

```sh
python3 -B engines/experiments/tiny-c-entry-composition/build.py \
  --out /absolute/new/external-output
```

The output must be new and outside Git. The producer first runs its old control
builder for two shipping and two DEV reproductions, then makes two independent
candidate source/native/whole attempts. Each candidate attempt compiles both
before-alpha and after-alpha sources; codec starts only after both attempts'
full-native alpha identity gates. It never executes an engine, semantic test,
game or benchmark. Compiler/PP/decoder tool stdout, stderr, process-group
ownership, reports and all generated artifacts remain in the external output.
The tool runner owns whole process groups, including after a leader exits.

First cost does not qualify query semantics, publication/reset, startup phases,
partial creation, active next-GO/position or physical quit/EOF. Those checks need
separate authorization after the measured result. This folder does not claim
4KiB completion, strength, NPS, scaling, DEV candidate qualification or runtime
acceptance.
