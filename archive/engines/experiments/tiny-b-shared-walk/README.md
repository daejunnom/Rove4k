# One B shared forward geometry first cost

This one candidate shares actual forward piece/ray traversal between pseudo
generation and full attacker-bitset queries. It uses B's incremental occupied
bitboard in ctz source order; existing piece-kind bitboards still serve LVA.
Null move buffer means query, with target matching before friendly rejection,
empty pawn diagonals counted as attacks, and no pawn push/castle emission.
Generation retains the original per-source direction/push/promotion/castle
order. The existing g capacity bound and all four promotions remain.

Exact shipping input11702/d0b914 becomes11532/3fca96, raw-170. Only old l395
and gen727 change to walker/prototype/l900 and gen52. Embedded readable/physical
literals, fixed roles, full inverse and10580-byte protected complement close
the decision. All current LVA/input/Board/make/EP/hash/HCE/path/TT/singular/
excluded-learning/resources/lifecycle bytes outside those regions stay exact.
This is not the old64-target emitter or adjacency/first-ray experiment.

Queries now walk up to16friendly sources instead of target-centered8rays and
can be slower. Full geometric masks and pseudo list order are intended equal
under the existing coherent BB/mailbox admission; runtime, strength and stack
claims require separate evidence. Raw source savings predict no whole saving.

```sh
python3 -I -B engines/experiments/tiny-b-shared-walk/cost.py --out /absolute/new/first-cost
```

The cost command reuses only four exact actual normal artifacts read-only,
then compiles one candidate stdin in a private cwd/owned90-second process group
and packages one fixed ALONE9e/lc2lp0pb0/BT4/64MiB/nice32 with prefix77.
Strict pure decode checks baseline and candidate source/bootstrap/compiler
argv. Normal/shared/otherexperiment/Git inputs are not modified. No engine,
AST, standalone PP, DEV, game, benchmark, sweep or retry runs at first cost.
Outputs stay outside Git. Tie/loss stops; gain is reported before focused QA.

The sole first cost completed: source11532(-170), native26384(-16), whole5371
(-55 from5426), leaving1275 bytes above4096. New native SHA-256 is
7b9503f99d7e71eb26522501eaa89caaefbd3000d38ef0637688378aa62b9423;
whole SHA-256 is0b6642824ca291faceb774fe8c7a15af97fbce844f1b889903ddfa353e9c13b1.
Native equality is false and no metadata exception applies. One compile and
one package completed, strict pure decode2 passed, the compiler group was
absent after reap and the dispatch exited0. Engine/runtime checks were0 at
cost. Original producing5 and generated outputs are external under
rove4k-tiny-b-shared-walk-cost-20261021-evidence. Only recipe result metadata
and this paragraph change after cost. Root owns Git/global docs and any normal
promotion; focused qualification is a separate conditional step.
