# One shipping E feature/dead classification fusion

This experiment preserves the maintained E5,679 ordinary control in `control/`.
Its 17 raw files close the original readable program, recipe, build helpers and
ancestry archive/verifier sources. The original builder is invoked only for its
two exact shipping source/native/whole repetitions; no verifier or engine is run.
Root MIT licensing applies. No external engine code is copied.

The sole structural candidate fuses material classification into the existing
shipping `tiny_white` evaluation pass. It keeps the two per-side bishop counts,
adds the total knight count, bishop-square-color bits and a pawn/rook/queen flag,
and computes exactly the old dead predicate:

```text
!heavy && (knights + bishops[0] + bishops[1] < 2 ||
           !knights && colors != 3)
```

The original separate shipping `dead` scan can then be omitted. No packed-pawn
representation, move parser, model, ordering, search retry, board layout, resource,
compiler, codec or flag alternative is combined with this candidate.

The transform accepts one original readable SHA and changes four guarded source
regions. It retains original DEV dead/evaluation/search text verbatim in DEV
branches. Shipping evaluation returns its material-dead flag through one nonnull
local output pointer, then search ORs it after the existing evaluation and both
score clamps, before the existing terminal/PLY and TT branches. Halfmove and
repetition decisions, mate precedence, legal-witness/PLY abort, fixed TT scale,
PVS/QS, learning, correction, startup SMP and command/completion barriers remain
outside the changed complement. All 21 signed-16 coefficients, sixteen leaf
terms, five ordering terms and the raw clamp retain their exact source meaning.

This is a static source proposal until separately qualified. In particular,
mixed/opposite bishop colors, multiple promoted minors, heavy pieces, legal
EP/castles/promotions, draw/mate precedence, checked PLY boundaries and actual
pool/publication behavior need appropriate later semantic/runtime evidence.
Verbatim DEV branches are source ancestry, not a newly executed DEV/native proof.

## Fixed first-cost reproduction

```sh
python3 -B engines/experiments/tiny-e-feature-dead/build.py --out /absolute/new/external-output
```

The qualified target/toolchain and original compiler command are unchanged:

```sh
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

The builder first requires the original maintained whole 5,679-byte literal and
full source/native hashes through its own unchanged builder. The only candidate
is generated twice from the same readable control and fixed transform. Actual
conditional generation and lexical compaction precede the existing eight no-op
counter removals. The fixed 89 name-to-alias pairs and WORKERS/TT_BITS literals
are reused without searching names. The existing shared helper and its original
input admission are never changed or bypassed; only its generic lexical rewrite
is used through a new experiment-owned literal source/count/unused/opaque
admission. New unmapped local names stay unchanged. Functions, global/static
symbols, external names and opaque regions are protected by the same policy.

The new admission is deliberately seeded once before the first measurement and
saved as ordinary `candidate-alias-admission.json`. Reproduction only checks it;
it never updates expected source/counts from generated output. Actual header
expansion must match exactly after identifier-only inverse, final macros and
resources must agree, and aliases must be absent from real header/macro names.
Candidate pre/post-alias whole native ELF must be byte-identical, including
notes/symbols; no allocated-segment or build-ID exception is admitted. That
comparison concerns the candidate's lexical alias stage, not structural equality
with old E.

The exact original Python/bootstrap and 75-byte shell prefix are retained. Only
the source literal is filled; fixed XZ/LZMA2 preset9 extreme lc3/lp0/pb2 CRC64
is unchanged. Two complete candidate source/native/bootstrap/whole results must
match. Inputs, PP data, diagnostics, original controls, native and whole outputs
and incomplete failure receipts remain outside Git. The copied utility supplies
only the pinned header/package logic; an owned bounded signal-cleaning runner
executes commands. No historical experiment report or generated binary is an
execution input.

First cost alone establishes neither semantic equivalence, playing strength,
runtime restoration, eligibility nor selection. Engine/semantic/game/benchmark
execution is outside this stage. A zero or negative whole gain is retained and
reported without a second variant, sweep or silent repair.

## Actual first cost: whole regression, candidate stopped

| Output | Original control | Sole candidate | Difference |
| --- | ---: | ---: | ---: |
| Pre-alias shipping C | 14,352 B | 14,335 B | -17 B |
| Fixed89 shipping C | 12,641 B | 12,626 B | -15 B |
| Entire native ELF | 26,408 B | 26,376 B | -32 B |
| Complete source wrapper | 5,679 B | 5,683 B | **+4 B** |

The exact original control reproduced twice before candidate measurement. Two
candidate generations produced identical source, complete native, bootstrap and
whole bytes. Each attempt's actual full header expansion/inverse, complete final
macros and fresh-alias checks passed. Candidate pre/post-alias entire ELF bytes
also matched in both attempts. This is lexical identity within the candidate;
the changed structural candidate is not equated to the old native image.

Candidate whole SHA-256 is
`fe62d5807e3f56c30e7360e8dfb01ab52f27559867d6a8bf530c7cc235e58133`.
The producing result receipt SHA-256 is
`2c2417db620d65f12d31807529dc13a055bcd3b037c6a69c328b7382e0149b0b`.
The source/count admission was seeded once before native measurement, SHA-256
`9f9f5899e62f01fdda23d331f598c2f68d8a8f8666d5df347d94f6caeeee8a46`.
These external receipt hashes are provenance only, not inputs to the producer.

The sole candidate has no actual whole gain and is stopped. No second feature
formula, alias selection, codec/flag variant, semantic fixture, production
session, game or benchmark was executed after observing this result. Smaller
source/native bytes did not establish a smaller complete submission. This
experiment remains a preserved negative cost result, not a maintained selection,
semantic acceptance or 4,096-byte eligibility claim.
