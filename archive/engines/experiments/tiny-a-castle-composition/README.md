# One A castle emission composition: first cost gain, unqualified

The sole fixed source candidate produces a **4,959-byte** complete file, 21 bytes
smaller than the reproduced **4,980-byte** control. Both physical candidate
attempts agree in shipping C, full new native, bootstrap and complete file.
This is a first cost result only. No candidate engine or bootstrap was executed,
and maintained A has not been changed or promoted by this experiment. The
candidate remains 863 bytes above 4,096 bytes.

## Source decision and changed private policy

The candidate shares castle emission with ordinary king horizontal geometry.
At king direction indices 8 and 9, the existing `to=from+d` is the transit square
and `to+d` is the castle destination. The rights bit index
`i-8+2*(s<0)` selects K/Q/k/q. The new emission is inside the actual `moves`
guard, after the ordinary move is emitted and before the existing king break.
It retains empty transit/destination, queenside b-file emptiness, origin/transit
attack tests and the unchanged `make()` destination safety test after rook
placement. No new readable identifier was introduced.

Generated king move order changes: ordinary king moves formerly preceded both
castles; now each horizontal king move is followed by its eligible castle.
Consequently DEV `legal` output order and possible tied search order change.
The origin attack query can also repeat for the two eligible paths. These are
explicit changed private policies; full behavior or performance preservation
is not claimed. Exact legal child sets and rules still require runtime
qualification, despite independent source review finding no edge blocker.

`transform.py` requires the exact baseline and replaces only its 525-byte
region with the sole 427-byte `castle.c.in`. The other 24,295 readable bytes
are byte-identical, SHA-256
`b10fc139d8af7f1def0e42d0e710fb79488003d44046e05e4db844b8d42d1517`.
That complement contains Board/put/make, EP normalization, rights updates,
incremental HCE/hash/reversible path, repetition, PVS/QS, full-key coherent TT,
history/continuation/correction, SMP, minimum UCI, clocks and resource bounds.
Their source is retained; runtime and new-native acceptance are separate.

## Closed recipe and actual cost

There are 27 ordinary source files: 18 exact copied controls, seven candidate
producer inputs, this README and the LF attribute. The control closure was
copied from the frozen A4980 ordinary archive, not from generated outputs.
Copied tests/verifiers are closure only; they were not run. This folder's
copied original builder reproduced two physical shipping controls before the
candidate was measured.

The original public alpha/storage policies are unchanged and reject the new
candidate. `candidate-domain.json` is a separate literal source/count domain;
`candidate_domain.py` uses their exact original 31-name and 18-name maps and
unchanged writers. The alpha stage uses 30 names and 92 edits; storage uses 17
names and 87 edits. Unused `shift`, all other unused mappings and all 49 aliases
remain reserved. Alias freshness, the old readable reservation union, eight
`PLY` uses, 53 opaque regions and 432 directive bytes are retained at each stage.
There was one fixed count-domain preparation, with no name/flag/codec sweep.

Actual raw source inverse and actual full raw PP inverse match byte-for-byte.
Actual macro dumps are identical. All 49 aliases are absent from the before
source's actual full PP/header and macro environment. These checks passed in
the domain preparation and again independently for both candidate attempts,
with all command outputs retained. No native was compiled from pre-alpha C.

After independent precompile review, `build.py` freezes all 25 control/producer
inputs, generates both candidate sources and performs both PP gates. It then
compiles and compares both final full new native images before packaging either
attempt. Old-native equality is not required for this source change. The
original `cc -Os -x c - -o x -s` compiler invocation, workers=2, TT_BITS=18,
PLY=128, 77-byte launcher, bootstrap template and LZMA-alone settings remain
fixed. Both packages passed strict Python and command-line LZMA decoding back
to their exact bootstrap text; neither decoder executes that text.

| Artifact | Exact control, both attempts | Fixed candidate, both attempts | Delta |
| --- | ---: | ---: | ---: |
| Readable C | 24,820 | 24,722 | -98 |
| Shipping C | 10,184 | 10,093 | -91 |
| Full native ELF64 | 22,672 | 22,672 | 0 |
| Complete file | 4,980 | 4,959 | -21 |
| Bytes above 4,096 | 884 | 863 | -21 |

SHA-256 identities:

| Artifact | Control | Candidate |
| --- | --- | --- |
| Readable C | `71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734` | `554d0700bffeda11850f1168b90dc25228382453683b7a962d522d29044dc2ff` |
| Shipping C | `9e764bbbea91f198a4cb5aff62aae9f3007df5f715d4d8b8142e4795b5109d5a` | `069691392089b072ce5b389ab0a3320002c2412a9838d7d09ec564295d764e2f` |
| Full native ELF64 | `84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a` | `ff8c4c99d1410a57ff92701d71ddf953d66c03ca7a6d616fd3cce37c1dc7f1b8` |
| Complete file | `4f339d08d99e51cd5935f20cc10d0665ed19f515e227cb5fa6be1623e7b21a8d` | `990fca211734b174c7b9eceaeb2fe35f4a997c81344de99093d49cf52a201e61` |

## Retained evidence and pending decision

All original generated C, PP outputs, native images, bootstrap text, packages,
recipes and reports remain outside Git under
`/home/stemxstudio/rove4k-tiny-a-castle-composition-20261020/`:

- `baseline/build.json`: two physical controls, SHA-256
  `a61af79c48a75a477d550900a6c1072798fde41b514a242985e4da90917de75e`.
- `literal-domain-preparation/preparation.json`: sole fixed count preparation,
  SHA-256 `2acea2b7633e95526f24c7c7650f07c4789816f4f473de79524905e1680318f4`.
- `candidate-first/results.json`: two candidate native/whole attempts, SHA-256
  `41e357d650527dcb4a8b64c027b721095bb63565f5869cb2ed3a2d19fd825ac3`.

Independent precompile review is
`/home/stemxstudio/rove4k-tiny-a-castle-composition-precompile-20261020.json`,
SHA-256 `06e9a231fbf611fc9bb0715d593c5e380fd3abd04f55c73df66b66fb2b245443`.
It binds all seven current producer files and the exact 18-file control closure.
Those inputs did not change after review.

For reproduction on the same Linux x86-64 compiler/runtime, run the copied
control builder in a fresh external absolute directory:

```sh
python3 -I -B control/engines/compact/tiny-entry-a/build.py --out /absolute/external/baseline
```

Then retain a source-review receipt binding the seven producer files and run
the fixed candidate driver with another fresh external absolute directory:

```sh
python3 -I -B build.py --baseline /absolute/external/baseline --review /absolute/external/review.json --out /absolute/external/candidate-first
```

Both actual commands terminated with exit 0. Baseline native compilations: 2;
final candidate native compilations: 2; pre-alpha native compilations: 0;
package attempts: 2 + 2. Engine/DEV/runtime qualification, games, benchmarks,
training and AWS operations: **0**. No managed command remains live.

Root owns the qualification and promotion decision. Outstanding evidence
includes actual legal-child/rule equivalence around all four castles and their
blocked/attacked paths, interaction with the unchanged special-move/state
contracts, changed-order search behavior, and actual selected wrapper/native
lifecycle. No old native stack or runtime claim is carried over to this changed
native. No qualification, performance, 4 KiB completion or promotion is claimed.
