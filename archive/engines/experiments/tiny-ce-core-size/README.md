# One combined C/E core-size candidate

This experiment considers three current-source decisions from the attached size
analysis, independently checked against maintained C/E. It deletes C's actual
always-zero `tiny_order` function/call, removes dead consumed-prefix selection
writebacks in both families, and uses the nonzero TT payload as the private
write sentinel in both. Model/AVX2, Board/rules/state, evaluation clamps,
ordering policy, full-key coherent TT locking, search/learning, UCI/SMP and
resources stay in scope. No name, compiler, codec, bootstrap or launcher change
is included. No clamp change is attempted.

The selection loop reads only its unconsumed suffix and local selected move;
the retained `j <- old i` assignments preserve that suffix and strict-greater
tie behavior even when j==i or make rejects the selected move. C's zero-order
body has no side effects, including no DEV counter update. E's real ordering
function remains intact. Every production TT write is the sole search-tail
call: bound is 1, 2 or 3 and occupies bits41..42 disjoint from all other fields,
so even zero-score/zero-move/depth-zero records have nonzero payload. Zero
continues to mean a read; zero-payload writes are not production callers.

Ordinary tracked inputs are listed with exact hashes rather than copied into
nested source archives here. The producer freezes those inputs outside Git,
keeps original public alpha policies unchanged, and uses the same original89
mapping/resource decision through a separate literal new source/count domain.
Unused aliases remain reserved. Actual control C/E source/native/whole bytes
are checked against current maintained pins. The one old/new cost pair per
family is four native compiles and four original-codec complete packages total;
it makes no independent-repeat claim and compiles no pre-alpha native.

## Actual bounded first cost

Root read both exact diffs and the transform/call sites before source GO.
The actual current controls match all maintained source/native/bootstrap/whole
pins. The sole combined candidate has a complete-file gain in both families:

| Family | Readable C old/new | Shipping C old/new | Full native old/new | Whole old/new | Whole delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| C | 26,692 / 26,521 | 12,224 / 12,089 | 26,424 / 26,456 | 5,687 / 5,643 | -44 |
| E | 28,001 / 27,938 | 12,641 / 12,596 | 26,408 / 26,440 | 5,679 / 5,655 | -24 |

C remains 1,547 bytes above 4,096; E remains 1,559 bytes above. Both new full
native images differ from their controls and grow by 32 bytes. No metadata-only
explanation or old-native equality is claimed. These are new native identities:

| Artifact | C candidate SHA-256 | E candidate SHA-256 |
| --- | --- | --- |
| Readable C | `cd30bcab302327f140571dfb8a3222f5c4743a8bf81e35c0bace95f2b136cdcf` | `58ed7733cc9375ea6a60e28b09cb28e11d67d6e38b3f58cda377370f0e39a7db` |
| Shipping C | `fea9a67caac62593b8c71d5ac40a0cd8f4d5c1b5b22c9ae8c3627fa054541998` | `9cd96fd79a70b6d1d8fa06c687e665f925a60084a0032c979cb8ec260cd0b48d` |
| Full native | `ca0321ededbb68a5761c2b58129c5465c4ca385587276239069fdc6620098b6e` | `f446d4a2497ce56ff5a041a75a835914ce8652ff34d812f184b44ac2089191ee` |
| Complete package | `d67cdec49c6bc83461395cb1a6fc21f537c6f0924c38eb7c33633fe707bf3091` | `ae334d941f39cfb2f72c1d0d46f7b104e44d76970e3671d6fd36ebe6f6e3c1a1` |

The protected complement SHA-256, after excluding only the explicit transform
fragments, is `21cdcb2734f2871d70cb3763574910acd066e631c73fa26dbd43d242bc373281`
for C and `98d39c1259f677a0210bd0187cf66132579d48a485c0744b64b6cd4f5e048a16`
for E. No evaluation clamp or E model/ordering body changed. The scope is these
exact readable inputs, WORKERS=2, TT_BITS=18 and PLY=128; no generalized model
or arbitrary-PLY deletion claim is made.

The original XZ/LZMA2 9e, lc3/lp0/pb2, CRC64 codec, 75-byte prefix, bootstrap
and original compiler argv were used for every old/new package. Strict Python
restoration checks EOF, trailing bytes and CRC64; independent `xz -dc` also
restored the exact bootstrap text. No bootstrap or engine was executed.

## Source guards, preserved failure and receipts

The 17 existing tracked inputs have manifest SHA-256
`8204096c59a1e7367aa5ef683402aafd5f065181716e5eccf485bf09ced7a7a3`.
They are normalized exactly as the maintained producers do, then frozen only
outside Git. No nested control/source copy is stored in this experiment.
`candidate-domain.json` is literal SHA-256
`f9a6414be782a8ed7393bea18039dd462f087f327dd2e456b8e3bd98d42e2d15`.
Both original public policy domains still reject the candidate; neither their
admissions nor the shared original89 maps/resources were changed. Unused
`write` and every other unused alias remain reserved. New count domains check
all alias/resource occurrences, exact source/output bytes, PLY uses, opaque
regions and directive bytes. Actual full raw PP inverse matches in both
families, and all 89 aliases are absent from before-source full PP/header and
macro environments. Numeric inverse replacements remain zero.

The first source-only preparation stopped at an overstrict raw `-dM` dump-order
check on C. Its 1,479 complete macro-definition lines are an exact permutation;
raw PP inverse was already exact and no alias conflicted. The failure and all
raw outputs remain unmodified. The producer's guard now compares sorted full
definition lines including multiplicity, recording raw byte equality separately
(false for C, true for E). Macro bodies/definitions are unchanged. This repairs
the added observation guard; no original policy or expected artifact pin was
relaxed. The same fixed core candidate then completed source preparation in a
fresh directory. There was no native compile in either preparation attempt.

The pure checks cover 29 selected sequence/suffix cases, including permutations,
duplicates, ties and j==i, and 189 payload boundary combinations, including zero
move/score/depth with all three bound bits. Both source preparations used those
same checks. They are algebra checks, not new-engine runtime qualification.

All original receipts and outputs remain under
`/home/stemxstudio/rove4k-tiny-ce-core-size-20261020/`:

- `prepared/prepare.json`: preserved source-only dump-order failure, SHA-256
  `aa9c8f91ca5d67bfcc65567010532136a04f10c21113f0ae2cc62cfb510201f8`.
- `prepared-2/prepare.json`: completed exact source/domain and PP preparation,
  SHA-256 `5dee62f05d9b688c143b49a781e478e39496db832c92e1e5d8f4d6fb84fd6bc6`.
- `first-cost/cost.json`: sole old/new first cost pair, SHA-256
  `0d0261647cedb8e5fab9f0c244b3effc64fcc72f35a96a3a1bdcabf444056748`.

Production regeneration uses `build.py prepare --out /absolute/external/new`
and the reviewed literal candidate domain, followed by
`build.py cost --prepared /absolute/external/new --out /absolute/external/cost`.
The preparation command emits only an external proposed domain, never updates
the owned literal file. Cost mode refuses any different domain, map, input pin,
prepared bytes or original control identity.

The completed cost has exactly four native compiles and four whole packages:
one current control and one candidate per family. Pre-alpha native compiles,
engine/DEV/selected-wrapper runtime, games, benchmarks, training and AWS: **0**.
It makes no independent-repeat, runtime, strength, stack, 4 KiB or promotion
claim. No managed command remains live. Root owns any risk-based follow-up and
normal promotion decision. Maintained/shared/Git/docs remain unchanged.
