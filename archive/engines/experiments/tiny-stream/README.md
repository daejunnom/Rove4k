# Shared move walk / streaming picker experiment

This is a separate, **unselected failed size candidate**. It owns no canonical
tiny-A, tiny-search, builder, CI, or encoding/runtime files. The frozen reference
is the readable 5,615-byte tiny-search composition, projected through the exact
already qualified identifier substitutions to reproduce the actual **5,419-byte
complete source artifact**. No new identifier campaign is performed.

## Actual result

| Whole-program measurement | Frozen reference | Streaming prototype | Change |
| --- | ---: | ---: | ---: |
| Specialized/compacted C with the fixed spelling map | 11,726 B | 12,198 B | +472 B |
| Smallest of 27 complete source wrappers | **5,419 B** | **5,579 B** | **+160 B** |
| Native ELF, compiler-stdin recipe | 26,456 B | 26,456 B | 0 B |

The complete wrappers include the loader/bootstrap, source, compiler command,
compression/transport metadata and prefix. The minimum is the same combined XZ
source-stream form in both cases. The 5,419-byte reference's source, complete
artifact and actual native SHA-256 reproduce exactly. The unchanged native file
length does not imply identical code between the two engines; their program
hashes differ. Each candidate separately passes the full native SHA identity
gate before/after applying the fixed spelling map.

This transformation did not close the 1,323-byte gap from the qualified 5,419-byte
reference to 4 KiB. Its larger result is retained as a failed hypothesis, with
the complete inputs, artifacts and qualification records outside Git.

## What actually changed

`transform.py` takes only the pinned readable translation unit SHA-256
`109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`.
The ordinary generator, attack query and search picker share the existing
geometric `walk` and promotion/castling emitter. A `Pick` request either fills
the unchanged public move list or selects the highest-scoring unvisited pseudo
move directly while walking the board. Search no longer materializes its
`moves[MOVES]`, `scores[MOVES]`, score pass or selection-sort prefix.

The original TT-first, tactical value/promotion, quiet history, continuation and
worker-salt score terms remain active. PVS, QS, TT payload/key/lock meaning,
history/continuation updates, correction learning and correction-dependent LMR,
fixed startup SMP and completed-iteration publication remain real paths.

This is **a search policy change**, not exact search-equivalent compaction:

- Equal-score moves use stable generation order instead of the original
  selection sort's tie permutation.
- Remaining moves read live learner values after each descendant search instead
  of a once-per-node frozen score array. This can change ordering, which moves
  receive LMR, nodes and scores from selective depths.
- Deadline checks occur before every picker request; cancellation is also
  checked during piece scans. The original deadline is retained. Timing/poll
  behavior is not called unchanged.

A rank-ceiling cursor alone would be unsound: descendant history/continuation
updates could move an unvisited candidate above the ceiling and omit it. Every
pseudo move therefore has a stable generation ordinal and one bit in a private
512-bit per-node visited set. Live score changes cannot omit or duplicate a move.
The ordinal includes illegal pseudo moves and all four promotions. Public
generation works while search is stopped because it has no worker context.

The draw/MAXPLY legal-witness branch shares the picker loop. Such nodes suppress
TT reads, and their first legal child returns the draw or signals incomplete ply
exhaustion. With no legal move they still return checkmate/stalemate, preserving
mate precedence. QS stand-pat still needs a legal witness and check evasions are
not capture-only. Cancellation after an interrupted walk returns incomplete
before any partial bound or iteration can be published.

## Runtime tradeoff and next structural question

The search's former approximately 4 KiB move/score buffers become a 64-byte seen
bitmap plus a small picker context. This is a layout fact, not a measured memory
or speed result. The picker may regenerate and rescore the entire pseudo-move
set for every selected move, making geometric traversal and value computation
quadratic in move count. A substantial runtime regression is plausible. The
bounded tests below are functional checks and **do not establish fair NPS,
strength or scalability**.

The old score/selection prefix has only 447 whitespace-free bytes, plus 93 bytes
of adjacent declarations, some of which remain needed. A shared picker cannot
by itself save about 1 KiB of compressed source from that block. Its callback,
frame, visited-state and witness plumbing consumed more than the removed code.
A substantially smaller design would need to share a larger part of node
control/legality/state handling. [review.md](review.md) records a distinct safe
staged proposal: one pure planning walk freezes a high/low quiet bitmap from
history+continuation+salt, then TT/tactical/high/low passes emit moves. That
proposal is **not implemented or measured**; it retains actual coarse learned
ordering and avoids the live-stage-membership omission trap.

## Verification that actually ran

- Independent common black-box verifier: all **eight development groups** and
  **five actual whole-wrapper shipping groups** passed. These cover independent
  legal/perft/rule and board-state checks, bounded search/mate/PV, fixed startup
  threads, active stop/reset epochs, 16-ply legal selfplay, EOF and quit.
- The real development feature fixture observed PVS 3,737, QS 3,219, TT hits
  1,872, history and continuation updates 1,065 each, correction updates 28 and
  correction uses 68. These are one run's branch observations, not performance
  results or exact node equality with the reference.
- Retained-TT halfmove contexts scored `[0,916]`; EP remained excluded from quiet
  correction learning. Dead-material and `PLY=4` incomplete-iteration tests
  passed, retaining the last completed legal witness.
- `picker_contract.c.in` tests the actual picker, not a duplicate chess engine.
  Across five positions it selected all 89 pseudo moves exactly once while
  changing remaining ranks in both directions. Separate positive controls prove
  actual TT-first, capture-first, history and continuation ordering; cancellation
  empties the search picker while public generation remains usable. Optimized
  and ASan/UBSan builds both passed.

These checks qualify the declared changed policy on the recorded local profile;
they do not turn a larger file into an adopted candidate. Board/TT algorithms
not changed by the prototype retain their original source; no old broad proof
is relabelled as a new concurrency or tournament result.

## Reproduce with immutable inputs

The profile is GCC 13.3, C11 `-Os -pthread`, `WORKERS=2`, `TT_BITS=18`, `DEV=0`,
default `PLY=128`, the generated tiny-A board and POSIX startup pool. Development
checks use `DEV=1`, and the explicit cap fixture uses `PLY=4`. `campaign.py`
copies the exact named frozen helper sources from the earlier tiny-search
measurement, takes its already accepted fixed spelling map through trial 93,
and validates that the whole 5,419-byte reference reproduces before comparing.
It does not depend on current canonical producer metadata or silently inherit
later LF/CRLF/encoding changes.

```sh
python3 engines/experiments/tiny-stream/campaign.py \
  --baseline /external/tiny-search/winner-state/combined.c \
  --reference /external/tiny-search/measure.json \
  --rename /external/tiny-search-rename/results.json \
  --out /external/new-tiny-stream
python3 engines/experiments/tiny-stream/qualify.py \
  --measure /external/new-tiny-stream/measure.json \
  --out /external/new-tiny-stream-qualification
```

Every output directory must be new, absolute and outside the checkout. The
initial metadata-only driver failed when it enumerated its generated
`__pycache__` as a file; that was fixed before either candidate was built. The
failed first output directory is retained. Actual successful measurements are
in `/home/stemxstudio/rove4k-tiny-stream-r2-20261020/`; qualification is in
`/home/stemxstudio/rove4k-tiny-stream-qualification-20261020/`. No canonical
source, final CI builder, or existing comparison artifact was overwritten.
