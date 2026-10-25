# One F production zero-window source specialization

This separate candidate reduces the maintained F entry's complete source file
from **5,479 to 5,407 bytes**: **72 bytes smaller**, still **1,311 bytes above
4,096**. It does not modify or promote the maintained entry. It makes no 4K
eligibility, strength, NPS, broad portfolio or many-core scaling claim.

Only one source policy was measured. Compiler arguments, function spellings,
fixed resources, Python bootstrap skeleton, shell prefix and XZ settings stay
fixed. The two candidate generations reproduce the same source, native,
bootstrap and complete file bytes. These results apply to Linux x86-64,
GCC 13.3.0, Python 3.12.3 and the recorded liblzma encoder, with two search
workers, three total startup threads, TT bits 18 and PLY 128.

| Actual artifact | Frozen control | Beta-only candidate |
| --- | ---: | ---: |
| Readable C | 26,318 B | 26,100 B |
| Compact shipping C | 12,982 B | 12,722 B |
| Restored stripped ELF | 22,664 B | 22,664 B |
| Complete source launcher | 5,479 B | **5,407 B** |

The native files have different hashes despite equal sizes. Candidate native
SHA-256 is `ef10962ff16e5158e0cb18cbf96b944404bd1c4db301bfbb47a0faed33466c22`.
The complete candidate's SHA-256 is
`e562a49a06257d46bbbb9e0481023f3716926e4cf2a8086dcd5307b3e8a96078`.

## Why a beta-only search is sufficient here

The frozen production F has exactly one caller outside recursive search:
`think` supplies the integer window `[beta-1,beta]` for every MTD probe.
Every actually searched descendant preserves that width:

1. Entry alpha equals `beta-1`.
2. An integer quiet standpat either leaves alpha unchanged or reaches beta.
   When it reaches beta, the QS filter searches no child. It still applies
   generated moves through `make` to prove that a legal move exists.
3. Otherwise a child's first-move window `[-beta,-alpha]` and later PVS window
   `[-alpha-1,-alpha]` are both `[-beta,1-beta]`.
4. A child that raises alpha also reaches beta and immediately cuts off. No
   subsequent child sees an alpha strictly between the entry alpha and beta.
5. Therefore strict `alpha < score < beta` re-search is unreachable in this
   production call graph, and the child's beta-only threshold is `1-beta`.

The candidate removes the alpha argument and `old` local, the first/later PVS
branch and unreachable re-search, and the alpha updates. TT upper admission is
`score < beta`; lower admission remains `score >= beta`. A stored result is
lower bound 2 when `best >= beta`, upper bound 3 otherwise. An exact reader
record is still supported, although a completed integer unit-window search
does not itself write exact bound 1.

Crucially, `make` and the legal counter remain **before** the QS skip:

```c
++legal;
if(quiet&&(!tactical||best>=beta))continue;
```

Stalemate therefore cannot escape as a standpat score. The post-child stop
check remains before root-result updates and learning, path length is restored,
and the driver still publishes only converged completed iterations using its
lower-bound attaining move. Upper-only moves cannot replace that witness.

The board, coherent full-key TT primitive, context/leaf helpers and everything
after `think` remain byte-identical. The MTD driver differs only in the root
API argument list. The actual frozen control uses a single-bound TT record;
its driver retains both interval directions. No TT layout or canonical paired-
TT implementation is changed. History, continuation, ordering correction,
exact horizons, mate normalization, terminal/draw rules, abort handling, fixed
startup pool and minimal UCI policy remain in place.

DEV retains the original nonfirst-normal-probe counter behind an explicit DEV
guard. That conditional is absent from shipping. The new private search API
does not accept a general wide window. Original TinyF wide-window fixtures
remain reference evidence and are not reused as proof of this candidate.

## Fixed source closure and reproduction

`control/` is an owned LF snapshot of the exact old readable F, recipe,
bootstrap, shell prefix and five helper versions. `upstream-build.py` is
preserved for provenance only and is never executed. `cost.py` reads only this
folder's pinned inputs, copies them outside Git before importing helpers, then
requires the control's compact C/native/bootstrap/whole hashes to reproduce
the exact qualified **5,479-byte** control. It never reads a mutable maintained
entry, an old executable or a network resource.

The current candidate is `transform.py`'s one guarded source change. The
shipping diagnostic removal schema explicitly removes the obsolete shipping
PVS call; shared helper code is untouched. Fixed compiler argv remains:

```text
cc -Os -pthread -x c - -o x -s
```

Resources, 34 function spellings and XZ `9e/lc2/lp0/pb0/CRC64` are copied from
the control's declared recipe. No identifier or codec search is performed.

From the repository root, using new absolute paths outside Git:

```sh
python3 -I -B engines/experiments/tiny-f-zero/cost.py \
  --out /absolute/external/f-zero-cost
python3 -I -B engines/experiments/tiny-f-zero/proof.py \
  --cost /absolute/external/f-zero-cost/cost.json \
  --out /absolute/external/f-zero-proof
```

There is one control generation and two independent candidate generations.
Native execution begins only after an actual complete-file reduction. A zero
or negative benefit ends the cost phase without runtime qualification.

## Focused dynamic evidence

The proof includes the **actual compact DEV0 shipping source**, with its fixed
production function spellings, into private O2 and ASan/UBSan fixtures. The
control receives only `alpha=beta-1`; the candidate uses its actual beta-only
signature. There are 51 finite threshold/position cases covering independent
quiet minimax values and adjacent integer thresholds, extreme thresholds,
checkmate at halfmove 100, stalemate with standpat above the threshold, dead
material, fifty-move draw, legal QS check evasions and quiet standpat.

Matching/incompatible normal and QS TT horizons, exact/directional injection
controls, root cutoff rejection, mate-ply normalization, halfmove and ordered
repetition context, and a real correction-ordering positive control add five
state observations. Shipping O2 and SAN therefore compare **56 rows each**.
Scores, moves, node counts and complete TT/learner/active-path digests match.
Independent minimax additionally checks that every directional bound contains
the exact value, adjacent thresholds return that value, and fail-high root
moves attain their lower bounds.

Separate readable DEV O2 and SAN fixtures each compare **70 rows**, including
12 actual MTD iterations at retained depths 3/3/1/2 with independently checked
scores and attaining witnesses. They exercise actual history, continuation,
correction learning/use, both interval directions and completed-depth node
interruption. A separate PLY4 comparison retains depth one's legal result
after the interrupted deeper iteration. The five control/candidate configuration
pairs all match. The overlapping DEV and actual shipping observations also
match; the DEV-only iteration/feature/abort rows are explicitly excluded from
that bridge.

Two fresh sessions execute the **actual 5,407-byte file**. They hash the restored
`/proc/PID/exe` against the candidate native, observe three stable startup TIDs,
verify deleted restoration paths and no compiler helpers, require one legal
white and black zero-clock result, then observe an active clocked search before
quit or EOF. Each closing epoch emits exactly one legal result and physically
exits with all output readers finished. Cancellation causality remains
`unproven`; these are physical lifetime observations rather than a specific
internal-path attribution or a performance benchmark.

The board/TT primitive/pool/parser identity receipts are separate from these
new search proofs. No broad board matrix, games or NPS campaign was repeated.

The external evidence set retains `cost.json`, `proof.json`, the frozen source
and helper closure, control/candidate artifacts and both initial harness failures.
The first source guard stopped before compilation because a DEV comment used
the word `old`; only that comment was corrected. The first runtime proof's five
engine comparison pairs passed, but its DEV-to-shipping bridge mistakenly
included a DEV-only feature row. The final v2 proof corrects that inventory and
passes the complete sequence. Neither failure involved another source policy.

Final cost report SHA-256:
`b951f2e1e1696967a767a3dcee9fd7ae12e1d56cfb6af18f2bff655a456c572a`.
Final proof report SHA-256:
`96678ed411e4fea4fcd0b176fe5cd707f073d49166e541dd9112b3d1bfa49e12`.
The external evidence copy,
`rove4k-tiny-f-zero-20261020-evidence/receipt.json`, binds these observations to
the fixed source and artifact hashes. This generated summary stays outside Git
and is separate from the source inputs. It does not claim maintained-entry
promotion, CI success or 4K acceptance.
