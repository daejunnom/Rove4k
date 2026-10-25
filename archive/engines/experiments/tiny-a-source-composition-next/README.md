# One A child-search retry composition: rejected at first cost

The sole fixed source candidate replaces A's four recursive child-search call
sites with one retry-state loop. Its shipping C is 28 bytes smaller, but its
complete file is **5,000 bytes**, 20 bytes larger than the reproduced maintained
**4,980-byte** control. Both physical candidate attempts agree exactly. This
experiment stops at that loss; no second source variant or runtime qualification
was attempted. Maintained A remains the baseline.

## Source decision and limits

The exact old retry region is 592 bytes and `retry.c.in` is 523 bytes. The new
`narrow` local chooses the null or full child window, while `reduce` first
selects the reduced depth and then clears on an alpha raise. A reduced result
above beta still retries at the unreduced null window before accepting a cutoff.
Only an unreduced null-window result strictly between alpha and beta proceeds
to the full window. The first legal move and quiescence use the full window
immediately. A's continuation index, reduction eligibility and correction
threshold remain those of the exact baseline.

The 24,228-byte source complement outside this region is byte-identical:
`d5cd28d9b09caa33c15844c32feca710cd34275a5cd2dd435cd2311a94a5ff97`.
That complement includes board/evaluation, full-key coherent TT, history,
continuation/correction updates, the single path push/pop and cancellation fence,
SMP, UCI, clocks, rules and bounds. Independent source review found no blocker in
the retry transition cases. This is source reasoning, not runtime equivalence
or a performance claim; the changed native image was never executed.

## Closed recipe and actual cost

The folder contains 26 ordinary source files: 18 exact copied control inputs,
six candidate producer inputs, this README and the LF attribute. The copied
tests/verifiers are source closure only and were not run. `closure.json` pins
the control bytes and original profile. `transform.py` requires the exact old
readable source/region and emits the candidate from ordinary inputs.

Original public shipping alpha/storage policies remain unchanged and continue
to reject the candidate. `candidate-domain.json` is a separate literal domain,
and `candidate_domain.py` reuses the same fixed 31-name and 18-name maps through
their unchanged writers. It preserves protected boundaries, the old readable
reservation union plus the new unmapped `narrow` local, alias freshness, eight
`PLY` uses, and all 53 opaque regions. There was one count-domain preparation
for this fixed source, without a name, flag, threshold or codec sweep.

The copied original builder first reproduced both physical shipping controls.
Then `build.py` admitted those exact artifacts and the independent precompile
review, froze all 24 producer/control inputs, generated the candidate twice and
compiled both complete new native images before packaging either attempt. Both
native images agree; old-native equality is deliberately not required for a
source-logic change. The original `cc -Os -x c - -o x -s` invocation, workers=2,
TT_BITS=18, PLY=128, 77-byte launcher, bootstrap template and LZMA-alone
settings are fixed. Both packages passed strict Python and command-line LZMA
decoding back to their exact bootstrap text. This did not execute the bootstrap
or the engine.

| Artifact | Exact baseline, both attempts | Fixed candidate, both attempts | Delta |
| --- | ---: | ---: | ---: |
| Readable C | 24,820 | 24,751 | -69 |
| Shipping C | 10,184 | 10,156 | -28 |
| Full native ELF64 | 22,672 | 22,672 | 0 |
| Complete file | 4,980 | 5,000 | +20 |
| Bytes above 4,096 | 884 | 904 | +20 |

SHA-256 identities:

| Artifact | Baseline | Candidate |
| --- | --- | --- |
| Readable C | `71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734` | `b1855017138a77c6f36050d5903abb1379180e62272b4412ccd43e9b4809d1fd` |
| Shipping C | `9e764bbbea91f198a4cb5aff62aae9f3007df5f715d4d8b8142e4795b5109d5a` | `6227b58d60680970eb7ee98c15fe9f73181a22e513fabb301d9030c3b66bd20d` |
| Full native ELF64 | `84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a` | `ce3896916d07094d15c8b91c8ceacca179c147a32fba13f541caea3fa7bb1b38` |
| Complete file | `4f339d08d99e51cd5935f20cc10d0665ed19f515e227cb5fa6be1623e7b21a8d` | `fb49c66f0aba9b67b8d344acfb13632643dbb05c4e8c455c7ae8902497af0888` |

## Retained evidence and reproducibility

Original reports, generated C, preprocessor output, both physical native images,
bootstrap text and packages are retained outside Git under
`/home/stemxstudio/rove4k-tiny-a-source-composition-next-20261020/`:

- `baseline/build.json`: two original shipping attempts, SHA-256
  `0ac940ad6205afadd8a1e34a60c9139cd8804b7b7bd63222ff4167f703e8411f`.
- `literal-domain-preparation/preparation.json`: one fixed source-domain
  preparation; original public-policy rejection was retained.
- `candidate-first/results.json`: two candidate native/whole attempts, SHA-256
  `429597181a78b6ac825078cf5394a3e01076d1f593bfc7ab3b5eacfaae6e0378`.

Independent precompile review is
`/home/stemxstudio/rove4k-tiny-a-source-composition-next-precompile-20261020.json`,
SHA-256 `5f8dba9652c77168a41d0a74bf2822482ae848ad2e8454d20bec738f414aea73`.
It binds all six current producer files and the exact 18-file ordinary control
closure. The current producer inputs did not change after that review.

On the same Linux x86-64 compiler/runtime, first use the copied control builder
with a fresh external absolute directory:

```sh
python3 -I -B control/engines/compact/tiny-entry-a/build.py --out /absolute/external/baseline
```

Then retain a review receipt binding the six producer files and invoke the fixed
candidate driver, also with a fresh external absolute output directory:

```sh
python3 -I -B build.py --baseline /absolute/external/baseline --review /absolute/external/review.json --out /absolute/external/candidate-first
```

For this run both commands terminated with exit 0. Baseline native compilations:
2; candidate native compilations: 2; package attempts: 2 + 2. Candidate engine
runs, runtime qualification, games, benchmarks, training and AWS operations:
**0**. No managed command remains live. Loss is retained as loss; no promotion,
4 KiB completion or semantic/runtime acceptance is claimed.
