# Maintained minimal B entry

The selected shipping source uses legal least-valuable-attacker exchange for
ordering after the fixed text input profile. Its complete file is **5,371
bytes**,55 below LVA-only B5426 and **1,275 above4,096**. It is not a4KiB
entry. The readable canonical engine.c remains28,953 bytes. Canonical and DEV
retain the old full legal minimax model and API as a distinct reference;
DEV-model equivalence to production legal-LVA is explicitly false.

The fixed Linux x86-64 target remains Ubuntu24.04.4/GCC13.3/binutils2.42/
glibc2.39/Python3.12.3/xz-lzma5.4.5. Resources remain2 workers,1 controller,
TT bits18 and PLY128. Those are provisional competition resources. The minimal
shipping UCI and public interface are unchanged; this stage adds no option.

```sh
python3 -B engines/compact/tiny-entry-b/build.py --out /absolute/new/B-build --dev
python3 -B engines/compact/tiny-entry-b/verify.py --build /absolute/B-build --out /absolute/new/B-runtime
```

One builder invocation generates shipping twice and, with --dev, the old
diagnostic reference twice. The unchanged selected verifier runs actual quit
and EOF sessions. Each wrapper restores its exact C stdin with the original
compiler argv before exec:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

## Ordinary source decisions

Canonical preprocessing, minification, diagnostic stripping, shared89 spelling,
B storage/static/scope maps and their old exact guards remain unchanged. The
existing shipping_core.py first transforms12220 to12148 using its unchanged
incoming-Move full-minimax composition. The fixed input helper then produces
11829/11a32cc6c48ad16856e7968c5ba91456257c1b249590f0aa71a371d2fd276a93.
Only then does B-only shipping_order.py produce11702 bytes. The final
shipping_walk.py consumes those exact bytes and produces11532. No previous
map or guard is generalized to accept a new source domain.

shipping_order.py embeds paired readable/physical literals, fixed role and
identifier-count domains, full input/output pins, three disjoint inverse
regions and an exact11083-byte all-gap complement. It removes the Exchange
type, replaces the incoming-net/wrapper region with one recursive Q, and
removes the entire QS negative-SEE clause. The actual ordering Q call and its
SEE_INCOMPLETE guard remain exact. The pure helper reads no experiment,
report, generated source/artifact, compiler/Clang/AST result or network data.
Receipt hashes are metadata only and are never regeneration inputs.

After successful make, the declared model chooses the first legal recapture
source by pre-capture P,N,B,R,Q,K kind, then ctz square order. All four N/B/R/Q
promotions of that selected source are tried and maximized. If all choices
from a source are illegal, it continues to the next source. A selected legal
negative continuation is declined with max(0,value); it does not search a more
expensive source for a better exchange. Initial EP and promotion gain remain
inside the incoming move. Incremental mailbox/bitboard attackers are reused;
unchanged make filters pins, king safety and special-move legality.

This is a declared model and search-policy change from full legal minimax.
Ordering, QS tree, node use, scores and learned values can change. The
approximate negative value is never a pruning certificate: the QS SEE-negative
test is wholly removed. Incomplete values never adjust ordering. Shared
stopped/deadline is checked after successful make and UNKNOWN propagates before
arithmetic. Illegal -MATE and SEE_INCOMPLETE(-32001) remain distinct from legal
completed values. The old private million-visit state is removed with the
Exchange model. Old minimax, DEV, visit-counter or stack evidence is not inherited.

All bytes outside the three fixed regions remain identical to the accepted
input-profile source. Qualified single-singular, production excluded-root TT
and learning fences, full-key coherent TT, generator/make/attackers/material,
board/hash/HCE, rules/repetition, resources and pool/lifecycle are preserved by
that source complement. Source preservation does not imply identical search
results after changing the ordering and QS policy.

## Current identities and evidence

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C |11532|3fca96ff1a913ed74edaed69d74794a433a9013e4a6cd88dc0e3dfe5e35d0b6f|
| Native |26384|7b9503f99d7e71eb26522501eaa89caaefbd3000d38ef0637688378aa62b9423|
| Complete file |5371|0b6642824ca291faceb774fe8c7a15af97fbce844f1b889903ddfa353e9c13b1|

Bootstrap SHA-256 is88af0a7d1ba13e4de0bf1f1ddfeff487f76bc9e0361e234e6cc4f1dd38c94789.
The old DEV source/full-native gates remain31ef1cb522371a0094effb098c8ea9c0a78ff800c01da9eef5087c5b43e18ec2
and9e5ac53ca94cf36e6ac43632d2e507598deb516e40405bafa6bd874e56069c30.
Their equality must be observed in the normal run; they qualify the distinct
reference tuple, not the production LVA model.

Packaging remains prefix77 and fixed LZMA1 ALONE9e/lc2lp0pb0/BT4/dict64MiB/
nice32. The earlier LVA-only first cost used native1/package1 and strict pure decode2. Native
grew8 bytes and whole shrank35 versus the accepted input profile; neither
independent source savings nor prior reductions were added as predictions.
No native metadata exception applies. ALONE has no checksum; exact source,
bootstrap and argv recovery is separate evidence.

Focused production-model evidence used the exact11702 candidate in one O2
include fixture. Independent legal rules computed46 roots plus43 selected
subcalls:85 legal score/state/source/promotion rows,2 illegal initial rows,
2 normalized-away EP exclusions and6 cancel/deadline guards. Both colours,
kind-before-square priority, ctz tie order, pinned-source fallback, king
recapture legality, EP occupancy/removal, all initial and recapture promotions,
negative continuation decline and incomplete propagation passed. A fixture-only
external clock port made child cancellation deterministic; it is not evidence
about production wall-clock timing.

The counterexample k7/8/2p1B3/3n4/1rP1P1K1/1b6/8/8 w - - 0 1, e6d5
gave+90 in independent Python full legal minimax and-10 in actual production Q.
No old binary was compiled for that reference. This observed difference is
why approximate negative values are not used by QS pruning. The mirrored
case gives+90 under the changed ctz order; colour symmetry is not claimed.

Cost receipt SHA-256:01daf1ba45610f8121cc18ec5f781dea3eff46ddf250ff32c7aab59d48ed168e.
Focused proof receipt:5bb133e2d840c61c4d1f8fcee8042080ad1ebcfafdb0acfbafb18c37c08a9aa1.
Focused final receipt:08793fb0790909aa6057f6f42c3cf4630b23624a240c1fbf4e1caf52803dc462.
These are external evidence metadata; no evidence file is a normal input.

The inherited input profile accepts NUL-free text, max32767 bytes before LF or
final EOF including CR, and space/tab/CR/LF delimiters with exact first command
tokens. Overlong lines drain/drop; VT/FF are not delimiters and embedded NUL is
outside contract. Numbers are whole ASCII decimal0..LLONG_MAX. Four exact clock
keys consume one value; last own-side values win. Absent own clock defaults
1000ms and invalid/zero/missing time has at least1ms. Existing budget caps,
nullable legal query with made child and transactional replay remain unchanged.
Input-profile normal B5461 receipts c196fc146544681c216d7542a5ffc90fdb03361f2e769ba86acea2b61d73e424
and a20b0f0d1687d1786c63df32d58e8b93cb4211105b87c2292d53a442ff4b2078
remain ancestry for that prior image, not current-image execution.

The previous LVA-only normal builder completed shipping2 and DEV-reference2.
Its shipping tuple was B5426, not the current shared-walk pins above;
each DEV source/full native retained the old reference tuple. The unchanged
selected verifier completed quit/EOF2 sessions and8 legal GO. It observed the
exact new native image,3 persistent startup TIDs, absent compiler/helper
children and restoration paths, one closing result, finished readers, process
absence and physical exit0. Cancellation causality remains unproven. Its
unchanged compiler helper does not separately observe compiler descendant/group
absence. No old metadata exception was applied.

Normal build receipt SHA-256:f9c1c3b969cae739885dd3cccf2c5f6d88768504ae7ca67d46dbbd4e697a91c2.
Normal runtime receipt:a2d12a0fe8cafca23a9a4a4b862e655dc6364fc4d0c5ceeda9904668919b608c.
Producing closure22 was frozen before execution; only recipe validation metadata
and this README change afterward. The original producing recipe/README and full
ordinary source snapshot remain external. Unchanged fresh.py finds
the additional ordinary helper through recipe helper_sha256; fresh extraction
and archived rebuild are0 at this checkpoint. No additional fixture, DEV engine,
game, benchmark, strength, stack or scaling qualification is claimed.


## Shared forward geometry

The final pure shipping_walk helper replaces reverse attackers395 and gen727
with one forward walker/prototype/attackers wrapper900 and gen wrapper52,
source-170. It enumerates the actual incremental occupiedBB in ascendingctz.
Query mode returns every attacking source bit, tests target before friendly
occupancy rejection, counts empty pawn diagonals, and emits no push/castle.
Generation retains source/direction/push/all4promotion/castle order. Square0
is valid because mode is the move-buffer pointer. Castle query mode cannot
recurse into generation. LVA keeps its piece-BB kind intersections and all
other source bytes remain exact via10580-byte protected complement. Existing
BB/mailbox coherence, make legality, normalized EP, full-key TT, singular and
excluded-learning fences are retained. All previous source guards run first.
DEV bypasses the stage and remains the distinct old full-minimax reference.

The actual first cost is source11532/native26384/whole5371, reducing170/16/55
bytes respectively from the prior normal. Fixed compiler/profile/bootstrap77/
ALONE9e/nice32 remain unchanged. Cost receipt SHA-256 is
14a7cba0f1aa3a190f71d81276282ab3151d49bb7d5456eee8cf99879e56cf1d.

Focused actual old/new production-source fixtures passed99 complete pseudo-list
orders per source,12672 full geometric attacker masks per source against an
independent64-coordinate oracle, and1281 complete legal child states per source
against the existing independent rules oracle. They retain85 legal/2illegal
LVA rows,2 normalizedEP exclusions and6 clock/cancel guards per source. Open,
blocked, origin/transit/destination-attacked and missing-rights castles are
included. The clock port is fixture-only. Proof SHA-256 is
57367b67b1dd783c3c5c1740d01afa3ab5410d64ab0848698972b9edcf320579.

Queries may be slower: up to16friendly sources and their forward rays replace
target-centered rays. No performance, strength, exact timed-search result or
whole-stack equivalence is claimed. The single authorized normal builder
completed shipping2 and old DEV-reference2 with the exact pins above. The
unchanged verifier completed actual new-image quit/EOF2sessions and8 legal GO,
observing3 persistent startup TIDs, absent helpers/private restoration paths,
one legal closing result, finished readers, absent process and physical exit0.
Cancellation causality remains unproven. The unchanged normal compile helper
does not separately observe compiler descendant/group absence. Native metadata
exceptions remain0. Normal build receipt SHA-256:b17212d6914e3d0e02a4b0488a6aab27e34b55bf471bdce1274a04444ba8305d.
Normal runtime receipt:0de3dd1ac8d0b4b57808f0d116bbfdb69ee16ce1336f69aef62aa9b5307d4fcc.
Producing closure23 is frozen separately from completion recipe/README metadata.
Fresh0, extra fixture/oracle/wrapper session0, DEV engine0, game/benchmark/retry0.
