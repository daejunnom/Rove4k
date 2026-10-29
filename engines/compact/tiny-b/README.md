# Optional source-first B candidate

This independent C architecture candidate combines B's required algorithms with
Tiny A's compact runtime. It does not replace the canonical C/Rust portfolio or
modify Tiny A. The smallest complete source launcher measured here is **6,283
bytes**, **2,187 bytes above 4,096**. B therefore still has no eligible artifact
from this candidate. No training, external model, cloud connection or NVCompact
dependency is involved.

The shipping engine has real incremental mailbox and bitboard state, shared
attackers, exact legal SEE, one qualified singular extension, incremental HCE and
hash, PVS, quiescence, locked full-key TT, history, continuation, correction and
a persistent startup worker pool. Its shipping interface retains Tiny A's small
UCI surface. FEN, perft, state, algorithm counters and bounded depth/node controls
exist only in development specialization. Worker count and memory are fixed at
compile/startup, with no public resource options.

## Frozen source and representation

`base/` is an unmodified frozen copy of Tiny A's generated-board source and its
three local source-layout/packaging helpers. `generate.py` pins every file's
SHA-256 before applying exact, counted replacements. It then loads this
directory's own readable `search.c` and `attackers.c.in`. A modified baseline or
changed replacement shape fails closed; a future Tiny A edit does not silently
change Tiny B. The build freezes every executed producer and source into the
external output's `recipe/engines/` tree before importing it. That recipe can
build again independently of the current checkout.

The bitboards use `bb[colour][1..6]` for pieces and `bb[colour][0]` for occupied
squares. `put()` updates mailbox, both bitboards, HCE, hash and king location
together. EP canonicalization must also use `put()`: updating only its temporary
mailbox would make a pinned EP capture look legal to bitboard king safety.
Development invariant checking reconstructs and compares every bitboard.

`attackers()` reads these actual incremental masks. King safety and SEE call
the same function. Geometric masks may include pinned pieces; every exchange
candidate passes through the real legal `make()`. SEE considers all legal
recaptures and all four promotions, with an optional zero-gain refusal to
recapture. Material-only gains exclude piece-square terms. Each recapture
reduces piece count, bounding recursion under the admitted 32-piece maximum.
The million-visit guard declines an estimate with a distinct incomplete value.
Stop or expiry shares the original search deadline, marks the estimate
incomplete and never turns it into a losing-capture pruning decision.

`make()` and SEE's initial move are internal generated-move APIs. Public text
is matched against `gen()` before application. An EP target removed during
canonicalization is absent from that list; feeding a fabricated diagonal pawn
move to this API violates its precondition. SEE recaptures construct the exact
generated target-capture geometry from shared attackers and promotion choices;
the target contains the opponent's preceding capturer, so no EP or castle is
possible at that stage. `make()` retains king-capture and own-king safety checks.

Singular verification requires a non-root depth of at least six, a real TT move,
an adequately deep exact/lower bound and a non-mate score. Its threshold is
`tt_score - 2*depth`. The verification excludes that move, shares cancellation
and the original deadline, suppresses the constrained node's TT read/write and
propagates learning suppression through its descendants. Those descendants
remain normal legal search positions and may publish their own valid TT bounds.
Only a completed verification below threshold extends the candidate by one
ply. No remaining alternative returns the caller's alpha, not checkmate.

Additional source changes retain these algorithms:

- The unread selected prefix of selection sort is discarded without changing
  the remaining equal-score order.
- Nonzero TT payloads mark writes. Every actual store has bound 1–3 at bit 41;
  zero is reserved for reads. The acquire/release try-lock and full 64-bit key
  comparison remain unchanged.
- Both history/continuation callers pass positive `depth*depth`, removing an
  unnecessary `abs` in the learner.
- All 768 signed-piece/square values have magnitude at most 910; admission
  permits at most 16 pieces per side. Thus `abs(HCE)<=32*910=29120`, below the
  mate score band. The redundant static clamp is removed and `PLY>879` is
  rejected at preprocessing. The correction residual's 256 clamp stays active.

The fixed local recipe is GCC 13.3, C11 `-Os -pthread`, `WORKERS=2`,
`TT_BITS=18`, `PLY=128` on WSL Ubuntu x86-64. Before those additional source
changes the compact C measured 15,917 bytes and its smallest complete wrapper
6,327 bytes. The current C measures **15,761 bytes** and its wrapper **6,283**.
These are whole-file measurements, including the shell prefix, compressed
Python compiler bootstrap, C input and compiler argv. They do not establish
playing strength, fair NPS, target-machine scaling or tournament acceptance.

## Verification

The first and current source snapshots passed the common independent verifier.
The current snapshot passed all **23 groups**: eight development groups and
five each for original shipping native, compact shipping native and the actual
selected complete wrapper. The pool had exactly three startup threads with
stable identities. Original and specialized shipping native bytes match exactly
for this recipe; every native and complete wrapper has an independent
byte-identical second generation.

`check.py` includes the actual generated DEV translation unit. Optimized and
ASan/UBSan builds both pass:

- 12,279 legal child states with reconstructed bitboards and 51,200 independent
  geometric attack queries.
- Ten exact SEE fixtures covering pins, king recaptures, EP, queen and knight
  promotions and optional recaptures. Illegal public EP and pinned-bishop
  controls, explicit stop and original-deadline expiry also pass.
- A real completed depth-three exact TT candidate qualifies a depth-six
  singular probe. Ordinary low-window learning changes history/continuation;
  an ordinary wide-window search changes correction from 64 to 63.
- Excluded low/wide/expired probes preserve heuristic arrays, board, active path
  and the original node's TT record. The deadline is never replaced.
- In the queen-capture fixture, prime score 910 and alternatives 14 lie around
  threshold 898. The actual candidate child's completed TT depth is six,
  compared with five without the extension.

The focused contract uses `TT_BITS=20` because a legitimate later descendant in
this deterministic fixture overwrites the watched child's slot with 18 bits.
The production algorithm is unchanged. The failed 18-bit observation and its
actual conflicting key remain in external reports; a singular counter alone
was not accepted as proof of an extension. Runtime wrappers still use 18 bits.

Tiny A's existing real-feature fixture also passes on Tiny B: PVS, QS, TT hits,
history, continuation, correction learning and correction-dependent reductions
are observed; retained-TT halfmove contexts score `[0,916]`, and EP does not
enter quiet-only correction learning. These are branch/functional observations,
not performance or rating evidence.

## Reproduce outside the checkout

```sh
python3 -I -B engines/compact/tiny-b/build.py --out /external/new/tiny-b
python3 engines/tests/verify.py \
  --manifest /external/new/tiny-b/validation-manifest.json \
  --out /external/new/tiny-b-verification --startup-threads 3
python3 -I -B engines/compact/tiny-b/check.py \
  --build /external/new/tiny-b --out /external/new/tiny-b-contract
python3 -I -B engines/compact/tiny-b/qualify.py \
  --build /external/new/tiny-b --out /external/new/tiny-b-restored-image
```

`qualify.py` additionally compares the live fd-executed wrapper image with an
independently reproduced compiler-stdin ELF, inspects its fixed thread IDs and
checks compiler-child/temporary-directory cleanup. Its result is separate from
the general verifier. All reports, generated sources, binaries and launchers
stay outside Git. Existing failure directories are retained.
