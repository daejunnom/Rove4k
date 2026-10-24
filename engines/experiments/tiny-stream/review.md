# Bounded staged-stream alternative

Design review only. No engine code was changed, compiled, or executed for this review. The input was the frozen readable winner at `/home/stemxstudio/rove4k-tiny-search-clean-20261020/winner-state/combined.c`, particularly the shared `walk`/`add` generator and `search`.

## Proposed structure

First make one pure planning walk over the shared move emitter, before any child search. Give each emitted pseudo move the walker's stable ordinal in `[0, MOVES)`. For each quiet move, freeze a high/low ordering decision in a 512-bit ordinal bitmap, using the actual history, continuation, and worker-salt score. Then search immediately from four bounded passes over the same immutable parent board:

1. The node's snapshotted TT move, only if the actual generator emits it.
2. Every capture or promotion, excluding the TT move.
3. Quiet moves whose frozen bitmap bit is set.
4. Quiet moves whose frozen bitmap bit is clear.

For example, the planning decision and later stage classification can be expressed as:

```c
/* Planning only: there is no recursion or learning in this walk. */
high[ordinal >> 6] |= (uint64_t)
    (history[from][to] + continuation[prior][piece_index(p->b[from])]
     + (m * 37u + w->id * 19u) % 17 >= 8) << (ordinal & 63);

/* Search walks use the frozen bit and do not rescore membership. */
stage = m == tt ? 0 : capture(p, m) || PROMO(m) ? 1
      : 2 + !(high[ordinal >> 6] >> (ordinal & 63) & 1);
```

Initialize the bitmap to zero before planning. The example threshold is a candidate ordering policy, not an established strength setting. Actual history and continuation change whether a quiet is searched before or after the low bucket; the salt retains a first-iteration difference between workers. Both quiet buckets must be visited exactly once. If there is no TT move, skip pass zero. A found TT move can end its pass after its one search even without a beta cutoff. Attack queries continue to use the walker's existing geometric-attack mode; the board agent owns that implementation.

Use one stack-local search frame containing the existing node variables, the bitmap, the pseudo-move ordinal, and a current pass. Reset the ordinal at every planning or search walk; increment it for every generated pseudo move before any stage filter or legality rejection. The emitter ignores moves belonging to another pass, calls `make`, and runs the existing recursive PVS/QS child-search and learning body for an accepted legal move. Its return value requests that the walker stop on a completed TT pass, beta cutoff, or cancellation. Keep the reason in the frame so a normal end of a TT pass cannot be confused with a node cutoff or an interrupted search. Do not put node frames or their mutable state in a shared global; recursion and SMP require independent frames.

## Explicit policy change

The alternative replaces exact integer sorting by TT/tactical/frozen-high-quiet/frozen-low-quiet stage order. It does not sort captures by MVV/LVA or promotions by promotion value. History and continuation retain an actual coarse ordering contribution, but exact rank within either quiet bucket becomes generator order.

Keep actual history and continuation updates and the current correction term in LMR eligibility. Do not move history and continuation exclusively into LMR: the required scope retains their ordering contribution. Bucket threshold and changed tactical/quiet rank precision need their own strength measurement; this candidate cannot inherit the old ordering policy's strength claims.

Do not use live history or continuation to choose search passes. Descendant searches update those cells while the parent is traversing later stages, which can move an unvisited quiet into a stage already completed. Freezing only a scalar threshold does not fix that. Membership is snapshotted before any child changes learned state; all search passes read only the bitmap, immutable parent board, and saved TT move. The parent's separate max-rank candidate instead avoids the same trap with a 512-bit ordinal seen set while allowing later scores to change.

## Required invariants

- Preserve `add`'s four promotion choices and all existing castling and en-passant paths. A promotion capture belongs to exactly one tactical stage. Planning and search must enumerate the same pseudo ordinals, including illegal pseudo moves, and must retain the existing 512-move bound.
- The TT move is admitted through generator membership and `make`; passing an unverified TT move directly to `make` would violate the frozen board contract.
- Obtain an existential legal witness before returning draw, maximum-ply, or a quiescence stand-pat cutoff. A quiet-only legal position must not become a false stalemate when tactical stages emit nothing. The planning callback can record a witness, calling `make` until the first successful one and then continuing pure bucket planning. A terminal-only witness mode can exit on the first successful `make` when no later ordering plan is needed.
- In check, visit quiet evasions as well as tacticals. At ordinary QS nodes, the witness proves nonterminal status and only tactical moves need recursive search.
- Count accepted legal children across stages for first-child PVS and LMR eligibility. Do not reset that count when advancing a pass.
- Preserve key-stack push/pop, mate-distance conversion, reversible-history TT context, full-key locked TT access, bound classification, and correction learning conditions.
- A cancelled callback must unwind its key-stack entry and propagate cancellation before changing the node's bound, TT slot, or completed root result.

## Cost and risk assessment

The frozen score-calculation loop and selection prefix occupy **527 raw bytes, or 447 bytes with whitespace removed**. The adjacent move/score declarations occupy another **93 bytes with whitespace removed**, and some scalar declarations remain necessary. These are static text counts, not minifier or compression measurements. The classifier, bitmap planning, frame declaration, member access, pass loop, and callback stop protocol consume part of that saving. A roughly 1 KiB compressed-source gain is therefore not supported by removal of the picker alone; a larger gain would require the callback to replace additional existing generator/search plumbing. Whole final file measurements must decide whether it is useful.

Memory per search frame falls substantially because the two 512-entry arrays disappear. The frozen-membership method uses a 64-byte bitmap, the same bitmap budget as the parent's ordinal-seen candidate. Normal full search performs one planning walk and at most four search walks, and the planning walk can also supply its legal witness. This avoids the max-rank candidate's potentially quadratic regeneration, although it weakens ordering and can consequently expand many more search nodes. Planning at a node that immediately TT-cuts or stand-pat-cuts can waste work; do not claim a speed improvement without measurement.

Check the stop flag at each emitted candidate, including the planning pass, rejected stages, and witness mode, and check the deadline at a bounded emission or outer-walk interval without charging rejected pseudo moves as searched nodes. Otherwise repeated generation can delay a stop while `claim` is only reached at recursive children. A bounded stop check in the shared emitter is sufficient for prompt external cancellation; its deadline check must not depend on a node count that never changes during that pass.

This is a useful second experiment if the seen-bitmap max-rank version saves source but loses too much time to rescanning. It is not a preferred implementation until complete package size, legal-special/witness coverage, cancellation, and independent depth-limited search behavior have been checked. No such runtime or performance result is claimed by this review.
