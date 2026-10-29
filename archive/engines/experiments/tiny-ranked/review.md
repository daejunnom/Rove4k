# Independent packed-priority review

This is a source review and a set of independent fixture expectations. It does
not report a compiler, runtime, package-size, NPS, or chess-strength result. The
reviewer did not modify the engine, transform, builder, or any older experiment.

The admitted readable input is
`/home/stemxstudio/rove4k-tiny-search-clean-20261020/winner-state/combined.c`,
SHA-256 `109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`.
Its search differs from the tracked Tiny A precursor, so proofs below use the
frozen input, especially lines 307–309 and 322–394. The initial review also read
`engines/compact/tiny-a/tiny.h`, `search.c`, and the existing tiny-search
equivalence fixture. The current `transform.py` was then inspected directly.

## Representation and score proof

The raw `MOVE` representation uses bits 0–6 for `from`, 7–13 for `to`, and
14–16 for promotion. `gen` emits only those bits. A widened `Move` does not
authorize priority bits in generator output, board APIs, the TT, fallback,
root results, or `Worker.best`. Only the current search frame's local list may
temporarily contain them.

The old priority expression has the following conservative bounds. These
bounds admit every `int16_t` history/continuation value, including negative
values that normal zero-initialized positive learning may not produce.

| Component | Bound |
| --- | --- |
| Ordinary quiet history + continuation + worker jitter | −65,536 … 65,550 |
| Capture base, using admitted `abs(value) <= 910` | 499,090 … 514,560 |
| TT match before promotion | 1,000,000 |
| Any promotion addition, N/B/R/Q | 402,000 … 405,000 |
| Universal final priority | **−65,536 … 1,405,000** |

Thus `priority + 65536` is nonnegative and at most 1,470,536, which fits in
21 bits. `((uint64_t)(priority + 65536) << 17)` uses at most 38 bits. The
addition is safe in the existing 32-bit signed `int` domain, and the cast
must precede the shift. Shifting a negative signed priority, shifting a
32-bit operand by 17 before widening, or truncating the result back to
32 bits would break the proof.

The transform's explicit `(int)PROMO(m)` in the promotion addition is
appropriate: after widening `Move`, the macro otherwise has unsigned
64-bit type. Keeping the priority calculation in the documented signed
domain makes the bias proof direct.

The old tie jitter was unsigned 32-bit arithmetic. Widening `m` changes
usual arithmetic conversions. For this frozen recipe, raw `m <= 131071`
and worker IDs are exactly 0 and 1, so `m*37 + id*19` cannot wrap 32 bits
and the modulo-17 value is unchanged. A broader worker-ID contract would
need an explicit original-width expression or a new proof. The frozen
two-worker scope must not silently become a proof for arbitrary IDs.

## Ordering and lifetime requirements

The existing picker compares with strict `>` and scans indices in increasing
order. It then replaces the selected suffix slot with the unselected entry
at the current index; it does not maintain a globally stable sort. For
example, `[A:1, B:1, C:2]` yields **C, B, A**. Equal-priority comparisons
must inspect only `packed >> 17`, not the complete packed word: raw move
bits must never become an extra tie breaker.

All priorities are computed once before searching the children. Descendant
learning must not cause the remaining moves to be rescored. Copying the
complete packed suffix entry preserves the old priority snapshot. The
current transform retains that lifetime and the old destructive suffix
replacement.

Selection must immediately restore `m = packed & 131071` before `make`,
capture/promotion metadata, root/best assignment, or TT publication. This
is a correctness boundary even though `FROM`/`TO`/`PROMO` individually mask
their fields. The frozen TT writer at line 393 ORs `bestmove` directly into
bits 0–16 of a payload whose score starts at bit 17, depth at bit 33, and
bound at bit 41. Leaking priority bits would corrupt those fields.
Likewise a packed word compared to the raw TT move would never provide the
old ordering relation. The current transform masks the selected move before
all these consumers; its initial priority loop sees fresh raw `gen` output.

The draw/PLY-limit branch precedes packing and still receives raw generated
moves. Recursive frames generate fresh lists. No pointer to a ranked list
escapes the current search call in the reviewed frozen source.

## Width and fixture hazards

- All declarations, definitions, and callers of `Move` must agree on its
  widened type. The combined translation unit provides this agreement;
  mixing separately compiled old and new headers would not.
- Generator lists outside search also widen. The search list changes from
  512 four-byte moves plus 512 four-byte scores to 512 eight-byte entries,
  so its nominal list storage stays 4,096 bytes. Other lists, including
  perft/fallback/parser lists, double. `Worker.best` can change structure
  layout/alignment. Actual stack/RSS measurements, if made, should describe
  the resulting binary rather than claim universal memory equivalence.
- Do not compare or serialize whole `Worker` bytes across representations.
  Compare named public fields and the history/continuation/correction/key
  arrays, which preserve their types.
- `engines/experiments/tiny-search/equivalence.c.in` prints `w->best` with
  `%u`. Reusing it unchanged with `uint64_t Move` is a variadic-format
  mismatch even when the numeric value fits 17 bits. An explicit raw
  `unsigned` cast plus a separate high-bit assertion, or a matching
  `PRIu64` format, is required. Do not rely on an ABI accident in a parity
  fixture.
- Existing TT packing casts its signed score to `uint16_t` before widening
  and shifting. This separate 16-bit score contract must remain unchanged.
  Packed move priority is not a new TT score representation.

## Independent fixture expectations

These expectations were proposed before executing the candidate; they are
not a pass report.

1. Compare the actual old and new picker on full 512-entry lists with
   ascending/descending/interleaved raw moves; equal priorities; repeated
   equal groups; and priorities at −65,536, −65,535, −1, 0, 1, 65,550,
   499,090, 514,560, 1,000,000, and 1,405,000. Preserve every selected raw
   move and exact old tie order. Include `[A:1,B:1,C:2] -> C,B,A` and two
   equal-priority entries with increasing raw values so a whole-word
   comparator fails visibly.
2. Drive the real production priority expression on generated moves after
   seeding both history and continuation with negative, positive, and
   counterbalanced `int16_t` extremes. Include a quiet minimum of −65,536
   with zero jitter, N/B/R/Q promotions, capture promotions, EP, and a TT
   promotion. Standalone positive-only pack/unpack samples are insufficient.
3. Run deterministic one-worker old/new searches with the same board,
   worker ID, deadline/limit, initial tables, and seeded learning. Compare
   raw best, score, completed depth, nodes, every retained feature counter,
   TT key/payload digest, and named learning/path arrays. Include the
   existing 12-position set, negative-learning cases, and repeated searches
   with retained learning/TT state. Correct raw-best formatting first.
4. Assert `best & ~131071 == 0` for every published root/worker/fallback
   result, and confirm generated lists have no high bits before ranking.
   Inspect actual TT writes or compare exact old/new TT payloads; merely
   reading their low 17 bits cannot detect corruption of score/depth/bound.
5. Retain the actual wrapper's protocol, rule/oracle, startup thread and
   physical completion checks. Source-level one-worker parity does not
   establish the packaged binary's SMP/public interface behavior. Retain
   draw-context/EP-correction and PLY-limit incompletion probes as well.
6. Use sanitizers on a development form for shifts, arithmetic, and
   indexing; compile reused development fixtures with format diagnostics.
   No candidate result may be relabeled as passing from an older binary
   just because the raw chess representation is unchanged.

The reviewed transform currently satisfies the static packing, extraction,
comparison, snapshot, and frozen two-worker arithmetic conditions above.
Runtime parity, whole-file cost, reproducibility, and final adoption remain
separate evidence owned by the parent experiment.

## Final bounded review: priority starting at bit 32

The final `transform(source, shift=32)` was inspected read-only after the
second layout was added. The transform admits only shifts 17 and 32 and
still requires the exact frozen readable SHA-256 above. Both layouts use
the same original priority expression, signed bias, immutable per-frame
priority snapshot, strict priority-only comparison, and destructive suffix
replacement. No runtime or compiler was invoked for this follow-up review.

For shift 32, the existing bound gives
`0 <= priority + 65536 <= 1470536 < 2^21`. The cast to unsigned `uint64_t`
`Move` occurs before the shift, so shifting by 32 is defined and the packed
priority occupies at most bits 32–52. It cannot overflow 64 bits. Because
fresh `gen` output uses only bits 0–16, bits 17–31 of every packed entry
remain zero. Copying complete entries preserves that gap. Consequently
`packed >> 32` recovers exactly the biased priority, independent of raw
move bits, and preserves the same strict comparison and tie order.

The selected expression `(unsigned)moves[j]` is correct for the frozen
Ubuntu x86-64 GCC target, where `unsigned` is 32 bits. Conversion from
`uint64_t` to `unsigned` is defined reduction modulo `2^32`, which removes
all priority bits. Widening that unsigned result back to `Move` preserves
its nonnegative value without sign extension. The proven zero gap then
makes this value exactly the original raw 17-bit move, not merely an
arbitrary low-32-bit value. Thus the existing `make`, root/best publication,
and TT writer still receive only the original raw move. The draw/PLY-limit
branch still runs before ranking and receives unmodified raw output.

This extraction is a deliberate target qualification. ISO C does not
require `unsigned` to be exactly 32 bits: on a target with 64-bit unsigned
it would retain priority bits, while a 16-bit unsigned would lose raw move
bit 16. The fixed compiler/platform recipe supplies the width premise;
this review does not claim that the cast is a portable substitute for the
explicit 17-bit mask on arbitrary C implementations.

The promotion contribution remains explicitly cast to `int` before adding
to signed `priority`; the bias fits signed `int` on the same target. The
previous raw-jitter proof still depends on the frozen two-worker IDs. No
new signed shift, invalid shift count, implementation-defined signed
narrowing, or sign extension is introduced by the inspected 32-bit layout.

The parent reports whole submission sizes of 5,299 and 5,303 bytes for the
two candidates versus the reproduced 5,283-byte baseline, with both
candidates retained as unselected regressions. The parent also reports
26 common groups, retained/context/PLY-limit checks, and actual-wrapper
native identity, startup and cleanup checks passing. Those statements are
parent-owned execution evidence; this reviewer did not independently run
or reclassify those checks. Exact trace/negative-learning proof remains
owned by the parent's separate trace reviewer. The static qualification
above is complete for both declared layouts under the frozen target.
