# One F unit-window bound predicate first cost

This is one fixed source-expression candidate on the maintained full-key
F9464 source/4720-byte whole control. It is separate from the in-progress
three-word futex pool and the unselected partial-tag TT policy. No algorithm,
flag encoding, horizon admission, mate adjustment or witness changes.

The exact readable guard is:

```c
if(ply&&bound&&ttdepth==(depth>0?depth:0)&&
   (bound==1||(bound==2&&score>=beta)||(bound==3&&score<beta)))return score;
```

Replace only its predicate with `bound!=2+(score>=beta)`. With the bound0
gate retained, exact1 accepts both score classes, lower2 only score>=beta,
upper3 only score<beta. The physical source projection is fixed in
`transform.py`, with input SHA, one span, exact inverse, protected complement
and all eight truth-table entries. This applies to F's integer unit window;
it is not an admission rule for A's arbitrary PV windows.

The actual pinned 4ku source outside Git uses an analogous flag inequality at
main.cpp673. Its depth>= rule, board/evaluation data, TT publication and other
upstream code/coefficients are not imported. The independent review also
confirmed ice4's renamer is occurrence-weighted lexical-scope conflict grouping,
not liveness coloring, and its packed MG/EG evaluation is not Rove's scalar HCE.

`cost.py --out /absolute/new/outside-git` reads only the exact four qualified
normal artifacts plus their literal build receipt, snapshots this producer and
the pinned ordinary literal helper/template/prefix, and compiles this candidate
once with the unchanged argv in an owned bounded process group. It compares
the complete native bytes with the old native, packages once with the unchanged
ALONE9e/lc2/lp0/pb0/BT4/64MiB/nice32 and 77-byte prefix, and strictly restores
old/new bootstraps with Python and the independent CLI decoder. It verifies the
source literal and compiler argv without executing a bootstrap or engine.

No baseline compile/compression/copy, C AST/PP, engine, DEV, game, benchmark,
normal-source edit, promotion, Git operation, alternative or sweep is authorized
in this stage. Native identity is a measurement, not an assumption. A loss ends
the candidate; a gain is handed off for a separately authorized promotion.

## One measured result

| Form | Shipping source | Entire native | Complete file |
|---|---:|---:|---:|
| Fixed control | 9464 B | 18576 B | 4720 B |
| Sole candidate | 9442 B | 18576 B, new identity | 4709 B (-11) |

Candidate source SHA-256 is
`245dae234e80c514d64da9109326dbf50077d703f6f353011f97aac682bdfd20`;
native is
`a25b88d5f97279b6b4cbee33d5af879e543d9796b0864f6b3331869e69415f9c`;
whole is
`2b9e91889a6c963db9bf752ad6b4ace95bc6036f342e4f0e411fb46b0488d04b`.
Full native equality failed; identical length is not identity, and no
metadata-only difference is assumed. The source truth-table proof is separate
from any future observation of this new engine image.

One unchanged-argv candidate compilation and one fixed ALONE compression
completed. Strict Python EOF/no-trailing restoration and independent CLI decode
match both original and candidate bootstraps. The owned compiler/decoder groups
are reaped and absent. Original producing four files and actual outputs remain
under `/home/stemxstudio/rove4k-f-unit-bound-first-20261021`; this result-only
README change occurs after that immutable snapshot. No engine, DEV, normal
promotion, alternative, sweep, game or performance run followed the first cost.
The candidate is a measured gain awaiting a separate promotion decision.
