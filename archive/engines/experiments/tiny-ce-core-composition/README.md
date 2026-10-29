# Current-name C/E core composition: bounded first cost

This is one combined structural candidate per family over current C5395/E5400
at source HEAD `9e2a15235fdc5d79fbe9a43be97eeabdb4833f89`. It changes no
maintained/shared source, compiler, profile, naming policy, codec or launcher.
The current private/static and automatic-local spellings are retained directly.

The four decisions are: use nonzero TT data as the private write sentinel;
remove writeback into the consumed selection-sort prefix; remove the inactive
outer evaluation clamp; and, only in C, remove the side-effect-free zero
`tiny_order` function and call. C has eight literal source sites, E six.
There is one fixed composition, not a feature or spelling sweep.

The exact domain is WORKERS=2, TT_BITS=18, PLY=128, MATE=30000 and admitted
Board state. C's fixed value/table evaluator has conservative absolute bound
32*910=29120; E's unchanged `tiny_raw` inner clamp is +/-20000. Both lie within
the old outer threshold +/-29871. This is not permission to delete arbitrary
model, correction, mate, QS or depth clamps. E's 21 coefficients and actual
ordering, C's constructor/actual AVX2 gather and reductions, and all score/mate
packing and PLY-abort ordering remain unchanged.

Every production TT store contains bound 1, 2 or 3 in bits41..42, disjoint from
the other fields. Even zero move/score/depth therefore gives nonzero payload.
Reads still use zero and contention is still a try-lock miss. Full key/context,
acquire/release publication, the existing depth-at-least comparison and
replacement semantics stay unchanged. Zero-data private fixture writes are
outside this narrowed production-call contract.

Selection still keeps the chosen move locally and writes old index-i values
into index-j. Only writes back to the already consumed index-i prefix and its
score temporary are removed. Strict-greater ties, j==i, rejected moves, QS
skips and the unconsumed suffix retain their original meaning.

`recipe.json` separately pins canonical and actual current final shipping
inputs and their paired edit fragments. The existing lexical token scanner
checks punctuation/literals/keywords and retained identifier correspondences;
member roles distinguish probe's `e->data` from its data parameter. Position
inverse and the complete protected complement match in each view. This is a
narrow exact-input lexical/manual source relation, **not a new AST binding or
normal-producer regeneration proof**. No current alpha/replay guard is relaxed
or called on a new domain. No new short names are allocated.

Previously qualified C query/startup/reset remains untouched. E's separate
query composition is not in the current E5400 source and is not added here.
The old `tiny-ce-core-size` first cost used older names/codec and did not remove
the clamp; its savings are not summed. Its preserved PP macro-dump-order
failure and the earlier C query invalid-fixture failure were read as separate
history, not rerun or converted into this candidate's qualification.

| Family | Shipping C old/new | Native old/new | Whole old/new | Actual whole delta |
| --- | ---: | ---: | ---: | ---: |
| C | 11,455 / 11,284 | 26,384 / 26,408 | 5,395 / **5,344** | **-51 B** |
| E | 11,803 / 11,703 | 26,360 / 26,384 | 5,400 / **5,366** | **-34 B** |

Both native files grow by 24 bytes and have new full identities. No metadata
exception or full old/native equality is claimed. C's new native is SHA-256
`05e1ffa928e488ed1cbfef7679634e465415326c1ba60e739d3842bb4fc0f766`;
E's is `851c4c9fc1a3f0696de66ff54e4659de375507ad455c86204e0600912f51b137`.
The whole SHA-256 values are respectively
`fd8dd108aceddf70e7adfa5ea02fc1b0ddc713e75bd3d6bb8efed8c6d41ba100`
and `d043584483ab1e0bded0f8e04ad61931f063976d8aec1d2897c69f09595a4621`.
Both remain above 4096 bytes; this is not event eligibility or performance proof.

Actual source/native/bootstrap/whole controls are checked read-only against
current maintained recipe hashes. None is copied or recompiled. Exact source
literal plus the unchanged template reproduces each old bootstrap before any
compiler starts. One new native and one fixed whole are then made per family.
The unchanged 77-byte prefix and ALONE/LZMA1 9e lc2/lp0/pb0 BT4/64MiB settings
use C nice64 and E nice32. Strict decode recovers each exact new bootstrap,
source and compiler argv. C disassembly retains vpgatherdd and two vphaddd.

```sh
python3 -B engines/experiments/tiny-ce-core-composition/build.py \
  --out /absolute/new/external-output
```

The actual first-cost root is
`/home/stemxstudio/rove4k-tiny-ce-core-composition-20261020-v1/`. It contains the
new readable and shipping sources, exact edit/binding/complement receipts,
native files, complete packages and strict decode evidence. This experimental
producer intentionally reuses explicitly pinned current artifacts; it does
not introduce such dependencies into a normal build.

This FINAL5 records native compilations2, compressions2, baseline compiles and
artifact copies0, separate PP/C-AST0 and engine/game/benchmark0. Each family
was measured once; no independent-repeat or functional/runtime acceptance is
claimed by first cost. Any focused qualification is a separately authorized
external receipt. The maintained C/E sources and this frozen cost candidate
remain unchanged during that work.
