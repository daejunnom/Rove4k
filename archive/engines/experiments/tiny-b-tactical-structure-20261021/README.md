# B generated-Move tactical classification — ONE first cost

Current production B5371 (source11532/3fca96, shared forward walker and legal-LVA
ordering) is the read-only control. The old full-minimax DEV is not this model.
One generated Move uses otherwise-zero 0x88 FROM bit3 as capture-or-promotion
metadata. FROM mask119 removes it. TO/PROMO and the existing17-bit TT payload
positions remain. All coordinate inputs are valid0x88 squares; the metadata
is private, never part of decoded/text coordinates. TT/exclusion comparisons
use consistently tagged generated moves. No old raw-Move identity is claimed.

The existing emitter receives tag2 for a pawn push, tag3 for pawn captures/EP,
and0/1 for other quiet/capture geometry. It expands all4 promotions and sets
bit3 for captures OR promotions. Actual ordering/SEE eligibility, QS tactical
eligibility and correction quiet guards consume that one classification.
The repeated Board/Move classifier is removed. Only initial nonpromotion EP
adds100 to SEE gain when the target is empty. Quiet promotions do not add100.
Q's recursive directly constructed recaptures have occupied targets and do
not consume that initial empty-target classification. Top production Q uses
tagged gen moves. Old fixtures must construct actual generated moves or
explicitly normalize encoding; expected scores must never be auto-updated.

The declared legal-LVA score algorithm, all4promotion continuations, legal
make/attackers, cancel/deadline UNKNOWN propagation and absence of QS SEE
negative pruning remain. Quiet promotions now receive the capture tactical
base ordering tier: this is an explicit private ordering policy change,
separate from unchanged intended SEE gains. No strength/equal search-tree
or old DEV equivalence is claimed. Raw source/native identities change.

Full inverse/disjoint literals/readable emitter role relation and unchanged
source complement are checked by transform.py. Hybrid Board/BB/HCE/hash/path,
coherent fullkey TT slots, qualified single singular/excludedTT-learning
fences and persistent SMP/input/pool source remain in that complement.

cost.py reuses the previously pinned producer structure and exactly the same
B compiler argv/stdin/private cwd/profile/77-byte bootstrap prefix/fixed
ALONE9e lc2lp0pb0 BT4 64MiB nice32. Baseline4 is read-only; no control build,
copy or compression. Candidate compile1/ALONE1 plus pure strict decode2 only.
Loss or tie stops. A gain requires targeted new-ABI/tactical/TT/exclusion and
wrapper proof before normal promotion. No upstream code, source/alias/flag/
codec sweep, games, benchmark, training or new agent. Outputs stay outside Git.

Source preparation: 11,532 -> 11,430 bytes (-102). The sole first cost produced
26,360-byte native (-24) and 5,357-byte whole (-14 vs B5371), gap1,261 to4KiB.
No functional/stack/performance qualification is inherited from old images.

## Observed result and qualification boundary

The sole native/ALONE cost passed strict baseline/candidate decode2. Native
SHA483a2b6c1f420a30d2f04f1acab9101f6b7dc44c06e1485117a2e8117f1365dd;
whole SHA8b8c3b565974813aa2ea54383bcc19240c1dcf506157d2aa0b44c8b24fa3d5be.
Compiler PID/PGID52620 exited0 and its group was absent after reap.

ONE O2 diagnostic fixture compile/run passed99 boards,294 independent tactical
tags and1,281 independent legal child full states. Actual gen full order equals
the frozen prior production output only after explicitly clearing bit3 in the
external comparison. Production retains tagged identity in TT and exclusions.
The unchanged frozen85 legal-LVA score rows,2 illegal rows,2 normalized-away EP
exclusions and6 clock/cancel guards passed. Expected scores/call counts were
not regenerated. All4 promotions remain real generated/made/SEE continuations.

Two admitted observation-only counters in a separate diagnostic source view
observed qualified singular1 and taken extension1; exact inverse recovers the
actual candidate source. Ordinary history/continuation positive controls and
correction64->63 passed. Excluded low/wide/expired probes preserved root TT,
learning, Board, active path and original deadline. The tagged capture12441
survived actual TT17-bit extraction/exclusion: prime910, alternatives14 below
threshold898, best remained the same tagged move. Actual TT18 child fullkey
read returned0; this is recorded, not replaced by the old fixture's20-bit slot
assumption or counted as proof of child-depth storage.

The external clock is fixture-only. No selected whole-program/normal wrapper,
SMP lifecycle, strength/performance or stack equivalence was newly observed.
Both owned diagnostic process groups settled, and no retry/variant occurred.
Normal/canonical/shared files remain unchanged. Producing source5/cost and
postproof README/recipe metadata are preserved separately outside Git. Root
owns any later normal promotion and actual selected runtime qualification.
