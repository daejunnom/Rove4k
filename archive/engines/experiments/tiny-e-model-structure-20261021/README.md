# One declared E model-structure experiment

This is a model architecture/feature change, not a lossless encoding of frozen
E21. The unchanged normal E remains 5281B. The only candidate is shipping
11105/b043eae2 from exact normal11378/761e301c, a raw reduction of273B including
the new private Board state and every delta update. No normal/shared file changes.

The hand-authored, UNTRAINED e-hand-quadratic-19-1 model retains material5,
piece-center6, pawn advancement and tempo coefficients; removes doubled/isolated
pawn and bishop-pair features; and adds residual gain1. Its white-perspective
inference is clamp(M+A+gain*A*abs(A)/128+side*tempo, -20000,20000), with C division
toward zero. M and A are exact put-maintained material/activity projections.
The quadratic residual creates cross-piece/color interactions, so this is not
the old HCE or an assertion of E21 equivalence. All19 signed16 coefficients are
exact static storage, with no quantization, training or data. The separate actual
five-feature ordering model retains its exact old coefficients and formula;
only indices move. Its score remains ordering-only, never a TT bound. Search
continues to use the new raw score for QS, correction residual and LMR guard.

Board gains two int fields (8B before measured layout); no recursive92B scratch
is introduced. Zero start and all make copies/deltas carry the state. EP attack
scratch changes raw b but is consumed only by attacked, never inference/search.
Changed layout, actual transition and production inference are not qualified by
the old canonical DEV reference. No old model, state, native, stack, strength or
4K eligibility proof is inherited.

```sh
python3 -I -B engines/experiments/tiny-e-model-structure-20261021/cost.py --out /absolute/new/first-cost
```

First cost reads exact pinned normal control source/native/whole/bootstrap,
compiles candidate stdin once, packages once with the unchanged77B launcher and
fixed ALONE9e/lc2lp0pb0/BT4/64MiB/nice32, then strict-decodes old/new once each.
Compiler/profile/resources/codec/names do not vary. Five fixed literal regions,
full inverse and complete untouched complement guard the source. All generated
files stay outside Git. A tie/loss stops; a gain is reported before focused
integer inference, ordering, state/transition and range qualification. No engine,
DEV, benchmark, game, AWS or training runs in first cost.

The sole first cost gained105B: complete5176/a3a36bdc (gap1080), source11105/
b043eae2, native26416/5ddcd703 (+32), bootstrap12170/97912c33. Cost receipt
/home/stemxstudio/rove4k-e-model-structure-first-cost-20261021/cost.json has
SHA235659d80b5ebc08f5829c1ce36b7e992b188bcbfcb4a57e42d9419d23d9865f.
Producing first-cost inputs are frozen externally before this outcome paragraph.

The initial focused preflight stopped before any fixture compile/run because
the observer assumed one stack-allocation instruction. The actual GCC stack
clash prologue uses split0x1000+remainder. Failed preflight receipt6d486a35 is
preserved; it is not a model/core failure. After the authorized observer-only
fix, one ASan+UBSan fixture compile/run passed under focused-20261021-v2.
Receipt3b1531a9 binds exact actualS/R bodies, independent board/hash/model/order
oracles,534 legalchildren including all specialmoves in both colors, complete
activity-interval int64 inference/clamp checks, and nonadditive legal-shape
model interaction. Actual depth2 search in both colors consumed these wrappers
and returned legal results (119/115 nodes); no full engine session or game ran.
Private Board is actually168->176B; current -Os M frame4392->4408B (+16), with
split allocations matched to teardown. These are layout/frame facts, not speed
or whole-stack performance claims. Canonical DEV21 is not a reference oracle
for E19. Readable model19.h has the exact actual model token bodies, with the
parameter mapping, changed-feature definition and conservative int32 bounds.
Normal integration/restoration completed after root model intake and existing
independent source/fixture CLEAR. The ordinary local shipping_model.py and
readable model19.h reproduce exact b043eae2/5ddcd703/a3a36bdc/97912c33 without
experiment/report/generated-source inputs. One unchanged normal builder passed
2shipping+2DEV21; the unchanged verifier passed2selected quit/EOF sessions and
8legal GO, new native image,3startupTIDs and physical exit/reader/private-path
fences. Current complete5176 remains1080B over4KiB; model strength/performance
are untested. No more target execution or compression followed.

The executed focused driver e833fdaf (6046B) is preserved externally. A subsequent
source-only interrupt-cleanup fix catches BaseException, kills and drains its
owned group; current driver21a9bc64 was not rerun. The model, fixture and
instrumented S/R bodies are unchanged. EP dynamic poisoning proves cache
independence and field preservation; scratch non-escape/parent immutability is
separately grounded in the frozen A source review. Old normal20/archive/control
are at rove4k-e-model-structure-normal-preserve-20261021; final source/receipt
aggregate is rove4k-e-model-structure-final-20261021/final.json.
