# Focused qualification of the frozen A castle candidate

This folder tests the exact already frozen 4,959-byte candidate. It does not
change or rebuild the immutable 27-file first-cost source, maintained A, shared
helpers or repository documentation. Shipping king move order and possible
tied search order, and repeated pure origin attacks, are admitted changed
private policies. Child sets and full states are compared without ordering.
Strength/performance, whole-engine stack safety and promotion remain separate.

`inputs/engine.c`, `transform.py` and `castle.c.in` are exact ordinary copies
from the frozen cost closure. The fixture regenerates and binds the exact old
and new readables. Both are compiled with DEV=0, workers=2 and TT_BITS=18.
The only target fixture port is renaming its unused `main`; no generator,
make, attack, evaluation, hash, search or learning code is patched. A FEN
loader is generated from the unchanged canonical DEV FEN body under the name
`fixture_fen`, outside the target. It supplies fixture states only and adds no
shipping command. Fixture output prints actual Board fields, legal children,
replay states and all 64 attack queries for each side. Two sparse castle
positions also call actual search at depth 2 with a finite safety deadline.

The fixture data targets KQkq, occupied paths including the queenside b-file,
origin/transit/destination attacks, right subsets, absent/moved/captured rooks,
king and rook return, all four castle transitions, legal/pinned/uncapturable EP,
both colours' four promotions and rook-home captures. It is a selected risk
set, not an inherited full matrix or a count gate. The unchanged independent
64-square rules oracle supplies legal child sets and board transitions.
Python separately recomputes HCE/hash and ordered reversible-path updates from
each oracle board. O2 and ASan/UBSan run the same fixed fixture data against
both exact readables, with raw compiler/runtime outputs retained outside Git.

The original selected A verifier and its two helpers are copied byte-for-byte.
Only its local recipe binds the new source/native/whole identities; the legacy
`qualified_receipt` field is null, so no old DEV/runtime receipt is inherited.
QA artifacts are raw copies of the actual cost output, including the unchanged
cost report under `build.json`. Strict decode and AST-only bootstrap source
extraction bind the wrapper to shipping C before the unchanged verifier runs
its quit and EOF sessions. It checks live restored new-native image identity,
startup TIDs, legal clocked moves, active closing epochs and physical exits;
cancellation causality retains the verifier's unproven classification.

Run only after root source review, using a fresh external output:

```sh
python3 -I -B proof.py --cost /home/stemxstudio/rove4k-tiny-a-castle-composition-20261020/candidate-first --out /absolute/external/proof
```

Root read the actual driver, C fixture and data before authorizing this exact
execution scope. The preexecution ordinary 12-file source set was frozen at
`787649120808084efad22b2148c1dfb46141944ff8a178e1722358a03248da8d`.
After execution only this README was updated; every executable producer/input
remains the reviewed and executed bytes.

The sole actual run completed with exit 0 under
`/home/stemxstudio/rove4k-tiny-a-castle-proof-20261020/run-1/`.
`proof.json` SHA-256 is
`c09db2ccb05b587df69a79fbdbb04ec9c8723865375b1e850deb9be4a50cdb43`.
Raw compiler/runtime stdout, stderr, command records, generated fixture inputs,
exact old/new sources and all reports remain there outside Git.

| Scope | Actual result |
| --- | --- |
| O2 old/new and ASan+UBSan old/new | Four fixed fixture processes passed |
| Each fixture process | 32 selected root positions; 749 legal child full states; 4,096 attack values; 14 replay states |
| Old/new comparison | Child sets/full states, initial/replay/root fields, attacks and pseudo counts agree |
| Sanitizers | Both sanitizer fixture stderr streams empty |
| Actual depth 2 searches | Two castle boards per fixture process; completed without stop, equal old/new score 1028, legal best moves |
| Generated legal order | Changes actually observed in 24 selected positions; explicitly admitted private policy |
| Exact 4,959-byte wrapper | Two fresh sessions, quit and EOF, passed unchanged selected verifier |

The wrapper was a raw copy of the measured complete file
`990fca211734b174c7b9eceaeb2fe35f4a997c81344de99093d49cf52a201e61`.
Strict restoration and AST-only extraction matched its exact shipping C. Both
live restored images matched new native
`ff8c4c99d1410a57ff92701d71ddf953d66c03ca7a6d616fd3cce37c1dc7f1b8`.
Both sessions had three startup TIDs, no surviving restoration helpers/private
path, legal white/black zero-clock and bare-go completions, stable thread sets,
and an observed active closing epoch yielding exactly one legal bestmove.
Both exited 0, were absent from `/proc`, and completed their output readers.
The verifier retains `cancellation_causality: unproven`: active-work/physical
exit observations are not upgraded to a causal cancellation proof.

The legacy historical receipt field is null. No old DEV/runtime receipt is
inherited. No outer verifier timeout occurred; the unchanged selected verifier's
per-engine finally/terminate cleanup remains in place. The four fixture
processes, four compiler commands and selected verifier reached terminal exit 0;
no managed command remains live. The wrapper internally restored its native in
each fresh session as usual; this did not change the measured artifact.

This closes the approved focused qualification. Whole-engine stack safety,
strength/performance, 4 KiB completion and promotion remain unclaimed. No
variant, game, benchmark, training, AWS, maintained/shared/Git change or
automatic promotion occurred.
