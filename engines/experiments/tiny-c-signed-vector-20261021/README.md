# ONE C signed-net vector experiment

## Historical first-cost scope

The exact actual current control is10803/8fd32643, complete5152/6584d2d9.
This sole candidate folds private color-separated16lanes into8 signed-net
lanes. Lane0 is zero padding; lanes1..6 are white-minus-black PNBRQK counts;
lane7 is sum(value(piece,square)-sign(piece)*material[k]). Coefficients are
[0,100,320,330,500,900,0,1], unchanged material values. King material lane6
is zero, but its positional value remains in residual lane7. Natural piece
indices preserve value(0,square)==0 for capture/EP priority without extra logic.

A guarded nonzero H delta adds n*sign to count[k], and adds n*value-signed_n*
material[k] to residual. Thus madd plus horizontal reduction computes exactly
the old full HCE white score by algebra; execution equivalence remains pending.
Count magnitude<=16, individual positional residual<=63 and total signed
residual magnitude<=2016 over<=32 pieces; all signed16 state and signed32
madd/reduction intermediates are safe. Coefficients/model/evaluation policy
are unchanged. Source outside five literal regions is byte-identical. Hash,
ordering, search, corrections, TT and pool are untouched by the transform.

The actual leaf is now128-bit _mm_madd_epi16 plus two horizontal adds. Its
intrinsic minimum is SSE2+SSSE3; compiler flags remain the fixed -mavx2 profile
and emitted instructions may be VEX XMM. This is a width/ISA-use change from
the prior256-bit AVX2 leaf, with no inherited claim of AVX2-specific256-bit
execution. The candidate must retain actual production SIMD consumption.

```sh
python3 -B engines/experiments/tiny-c-signed-vector-20261021/cost.py --control-dir /home/stemxstudio/rove4k-c-incremental-vector-normal-20261021 --out /absolute/new/first-cost
```

One fixed candidate compile, one unchanged ALONE9e/lc2lp0pb0/BT4/64MiB/nice64
package and two strict bootstrap/compiler/source decodes are authorized. Exact
control source/native/whole are read only, without control compile/package.
Ordinary input snapshots and all artifacts stay outside Git. Loss/tie stops;
gain is reported before separately authorized functional/layout/SIMD or normal
qualification. Canonical/DEV16lane/gather and normal C are unchanged. No
coefficient, codec, flag, name, target or native-variant sweep; no engine/game/
performance execution. A focused tracked-source search found no prior rejected
signed-net8lane/_mm_madd_epi16 cost experiment to repeat.

The sole first cost gained60B: source10803->10656 (-147), bootstrap11878->
11731 (-147), native26376->26376 (different full SHA), complete5152->5092.
The current gap to4096 is996B. Whole SHA is
175b73a5a720e2197c3842a8e61ed0a335b927491e43d00e60e42cc8509836b4;
native SHA is4ffb9c371eb7c0949f34ed637350ff3be9c7164890d1784c12e3cd3d93912691.
One native compile, one fixed ALONE and strict decode2 completed; control
compile/package and engine runs were0. Owned compiler group was absent after
reap, and the dispatch exited0. Actual receipt is
/home/stemxstudio/rove4k-c-signed-vector-first-cost-20261021/cost.json.

Existing independent child source review was CLEAR for algebraic score equality,
empty-piece and king handling, put deltas, signed16/int32 bounds and meaningful
SIMD return use. This was a source-only review with0 execution. No focused
state/layout/SIMD execution, actual instruction observation or normal promotion
has run for this candidate; these require separate root GO after this gain.
Normal C5152 and all earlier ordinary inputs remain unchanged. Producing cost,
transform/config and snapshots remain fixed; this paragraph closes outcome
metadata only. No retry, alternative vector layout or compiler/codec sweep ran.

## Focused and normal outcome

After gain and separate GO, one candidate ASan+UBSan fixture compile/run passed
actual H/K/U state, independent mailbox/hash/scalarHCE/old16-to-signed8 algebra,
all8lanes including king/padding zero coefficients,154 legalchildren,10816
capture-order checks,4 poison EP cases and all specialmoves in both colors.
Exact case rows and both actual searches (score0,best4742/10998,nodes150/104)
match the frozen prior actual DEV receipt2b52cd2d; that DEV reference was reused,
not rerun. New fixture receipt bfebab79e5f1658097f0938ea4099cc9ab907dbff2b725813840ad934202fa21
is /home/stemxstudio/rove4k-c-signed-vector-focused-20261021/focused.json.
New layout is184B versus200B; existing firstcost native P disassembly shows
actual128-bit XMM load/madd/twohadds and fixed allocation4392 versus4416B,
6 versus8 pushes and no old32byte alignment mask. This does not claim speed.

The pure ordinary shipping_signed_vector.py now closes normal generation after
incremental, with all prior guards and canonical/DEV sources unchanged. One
normal builder passed2shipping+2DEV; unchanged selected verifier passed2sessions/
8legalGO, exact new native image,3startupTIDs and physical quit/EOF settlement.
Build receipt12c85436 and runtime d18ee2e0 are separate from focused source QA.
Current shipping is exact10656/58e71a9c, native26376/4ffb9c37, bootstrap11731/
9b664514, whole5092/175b73a5. Normal25-source closure uses only ordinary inputs.
No fresh/archive execution, game, training, benchmark, codec/flag/name sweep or
new target variant ran. Source/evidence aggregate is external
rove4k-c-signed-vector-final-20261021/final.json; active terminal handles0.
