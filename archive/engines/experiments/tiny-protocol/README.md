# Tiny A / D span and move-admission experiment

This is an independent MIT implementation of a protocol architecture experiment.
It changes only a frozen readable source snapshot in a new external directory.
No external engine code is copied. The canonical Tiny A / Tiny D folders, their
selected artifacts, and shared builders are untouched. This experiment is not
automatically selected by either engine's production builder.

The result is mixed: the actual complete Tiny A source launcher grows **240 B**,
while Tiny D's scalar and HQ native ELFs each shrink **64 B**. The source launcher
candidate is an unselected failed size hypothesis. The D result is an optional
handoff candidate, subject to its owner's integration and a new identity check.
None of these files meets 4096 B. No fair NPS, playing-strength, many-core, or
other-platform comparison was run.

## Implementation and observation contract

`span.c.in` scans immutable pointer/length spans, checks exact command/key
spelling, and accumulates unsigned decimal values with a `LLONG_MAX` admission
bound before multiplication. An invalid or missing number means zero. A
nonnumeric following token is left visible to the next key iteration, so a
missing value cannot swallow `btime`, `winc`, or `infinite`.

The move decoder accepts exactly four coordinates and an optional lowercase
`n`, `b`, `r`, or `q`. It checks length before reading, checks all coordinates,
packs the engine's real `Move`, and requires exact membership in the actual
production `gen` output. Only then does it call the real `make` **once**, into a
separate child board. It returns that child to replay. Generated membership
remains necessary: `make` alone is not a geometry/rights/promotion validator.
This removes the previous stringification/compare and successful double-make
admission path without replacing the board or its legal-move authority.

`position.c.in` prepares its board and every accepted history key locally. It
commits the board, history length, and key prefix only after the complete command
is admitted. Late invalid moves and history overflow preserve the previous root
and history. DEV FEN admission remains available separately. `go-loop.c.in`
shares the span scanner; the existing deadline formula below that loop remains.

`transform.py` keeps DEV's original full-line command dispatcher. The shipping
dispatcher uses exact span commands and accepts leading/trailing ASCII bytes
1..32 as whitespace. No-argument commands with another token are ignored:
`quitx`, `quit extra`, `stopwatch`, and `stop extra` do not act as control
commands. Unknown go tokens are skipped; known fields may occur in any order,
with later duplicate fields replacing earlier values. `infinite` wins when
encountered. Empty `moves` is accepted. Broader ASCII whitespace admission and
missing-number recovery are explicit parser-policy changes, not a claim of
byte-for-byte behavioral equivalence for all malformed old inputs.
An argument-free shipping `position` now crosses `wait` before replay is
rejected; the old dispatcher ignored that malformed command. This is another
explicit malformed-command policy change, not a search or state mutation.

In D, generic string helpers become DEV-only. Output counts its literal text
locally, and packed bestmove output length is `4 + !!PROMO(best)`, covering
ordinary/null and promotion output. Partial-write/EINTR handling is retained.
The physical line reader, whole-line NUL/overflow drain, startup worker pool,
wait/result epochs, physical join path, board, search, full-key TT, PVS/QS,
history, continuation, correction, and HQ/scalar algorithms are unchanged.

## Frozen controls and measured cost

The tested domain is WSL Ubuntu 24.04, x86-64 Linux, GCC
`13.3.0-6ubuntu2~24.04.1`, Python 3.12.3, with two search workers and one command
thread and `TT_BITS=18`. Exactly the two selected engine compiler recipes were
used: A `cc -Os -x c - -o x -s`, and D's frozen freestanding static `-Oz -flto`
recipe. Unit sanitization is separate validation instrumentation. No compiler
or identifier sweep was run. The existing fixed identifier mapping is applied
unchanged to both A forms, rather than retuned to the new parser.

| Actual form | Frozen control | Span candidate | Difference |
| --- | ---: | ---: | ---: |
| A compact C input | 11351 B | 12212 B | +861 B |
| A stripped native ELF | 22664 B | 22664 B | 0 B in length; different program bytes |
| A complete source launcher, shared XZ lc2/lp0/pb0 CRC64 | 5283 B | 5523 B | **+240 B** |
| D scalar DEV ELF | 12796 B | 12860 B | +64 B |
| D HQ DEV ELF | 13184 B | 13248 B | +64 B |
| D scalar shipping native ELF | 8540 B | 8476 B | **-64 B** |
| D HQ shipping native ELF | 8928 B | 8864 B | **-64 B** |
| D scalar complete own ELF, BCJ | 8806 B | 8763 B | -43 B |
| D HQ complete own ELF, BCJ | 9142 B | 9081 B | -61 B |

A control compact input SHA-256 is
`49aa4d484458d0e4f6d14850fb2260a7007ea40f588003131d43a516d06a592e`;
the complete 5283 B control is
`798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645`.
The readable precursor is the frozen tiny-search source
`109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`.
The A candidate compact input is
`65c243ccad2dc78fe95c76d25267be7b254bc97dc77fa3402e14ff82b348f59c`;
its 5523 B complete launcher is
`5fc02e4f1a27a96cb775d436059692e35cf2b03e5d5dfcc5e27fdc5d8ad48c8d`.
The candidate remains 1427 B over the target.

D scalar/HQ candidate native SHA-256 values are respectively
`ba2d42473ca25a944b85da18f74f32eae18e68112010948a0e7c2dc0c69a7c5c` and
`09917666d5862c4f17ed77e33453000f608a7d83aa47f16f8726a063ec5f31ce`.
Complete own-ELF hashes are respectively
`8f020c3be7b3510ab27256fc8120d2c7c6839067f54ddfd8d212b0a4aefd97e2` and
`7c2f225dfb48e8929cf4c684f76088996bb1805e3c8a232c014c8556d4245f79`.
Native scalar/HQ candidates are still 4380/4768 B over the target. All headers,
loader, payload and runtime restoration costs are included in complete-file
figures. D's own loader is larger than its native file in these measurements.

`campaign.py` first reproduced the frozen A compact source, native program and
complete launcher exactly, and reproduced both frozen D native programs. It
compiled every native form twice and packed every complete form twice, requiring
exact bytes each time. This is reproduction within each recipe, **not native
identity between the changed algorithm and its control**. `results.json`
contains commands, input hashes, per-form native hashes and full loader costs.

The immutable campaign root is
`/home/stemxstudio/rove4k-tiny-protocol-20261020`.
The independent selected A input is under
`/home/stemxstudio/rove4k-tiny-encoding-combined-20261020/05-combined-fixed-stripped/`;
its wrapper is under `rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/`.
The D control is `/home/stemxstudio/rove4k-tiny-d-final-20261020/`.
Later producer metadata/new experiments must not be relabeled as these inputs.

## Actual qualification and limits

All **49 common groups** passed across eight actual forms: A DEV and complete
source launcher; D scalar/HQ DEV, native shipping and complete own ELF. DEV
forms ran protocol/rules/state/search/lifecycle/selfplay/EOF/quit; shipping
forms ran the five applicable groups. The shared rules validator uses an
independent chess oracle, published perft positions and special-move fixtures.
DEV results alone do not qualify the new shipping-only dispatcher.

The independent `edges.py` raw-byte campaign passed all eight forms: 144
automatic clock epochs, 56 explicit-control epochs, 40 final-line EOF cases,
24 DEV special-move replays and 66 invalid replay rollbacks. It covers leading
whitespace/tabs on shipping, exact negative commands, numeric overflow and
missing-value recovery, white/black field order, NUL drain, 32767/32768-byte
physical lines, fragmented 4095/4096/4097-byte boundaries, and duplicate-result
barriers. All three DEV forms also passed 4095-admitted/4096-rejected replay.
Actual command files were SHA-pinned, runtime executable identities recorded,
and the same three startup TIDs persisted. Each owned runtime exited zero,
became absent and had its output reader joined. There were 112/112 pre-control
worker CPU-progress observations; `stop_causal_link` remains **unproven**.
Work observed before a control and a result received after it is not causal
proof of cancellation.

`unit.py` passed seven actual-code configurations: A shipping, DEV and ASan/UBSan;
D scalar/HQ shipping and DEV. The only instrumentation renames the actual `make`
definition and inserts a counting wrapper. Checks include short-span no-read,
coordinate/suffix admission, actual EP/castling/all promotions, one make per
accepted move, zero make for nonmembers, one failing make for a generated pinned
move, full meaningful board and all 4096 history-key slots on rollback, and exact
clock arithmetic including `LLONG_MAX`. These headless units start no helper
threads and manually settle the parser's pending job between clock cases; they
make **no physical-completion claim**. Runtime tests supply that separate proof.

A retained-feature check and both D retained-feature checks passed actual
PVS/QS/TT/history/continuation/correction counters, halfmove-sensitive TT context,
EP correction exclusion, insufficient-material cases and PLY=4 incomplete-depth
boundary. Five one-worker fixed-depth scalar/HQ comparisons matched score,
bestmove and node count exactly, including a promotion bestmove. D's actual
runtime with a stub board/search separately passed all 11 runtime-fault cases,
including partial clone failure, EAGAIN, fragmented input, rapid epochs and
physical joins. A stub runtime result is not a chess result; actual forms also
passed the shared/edge chess and lifecycle checks above.

Two harness setup failures are preserved and are not engine failures:
the first qualification copied the validator at a directory depth that made
its outside-checkout guard reject output; r2 fixes only that directory layout.
The first units passed A's three forms, then D did not compile because the
cross-translation-unit counting variable lacked an `extern` declaration. The
fixture declaration was added, and all seven r2 configurations passed without
changing product code or expectations. The first successful edge campaign is
also retained; r2 strengthens duplicate-publication barriers and wrapper child
enumeration. No board/search source changed between these runs.

Final Linux reports are in
`/home/stemxstudio/rove4k-tiny-protocol-qualification-r2-20261020/`,
`/home/stemxstudio/rove4k-tiny-protocol-units-r2-20261020/`, and
`/home/stemxstudio/rove4k-tiny-protocol-edges-r2-20261020/`.
Windows review copies, frozen inputs and final artifacts are outside Git at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-protocol-20261020-evidence/`.

## Reproduce

Run under the domain above. Every `--out` must be a new absolute directory
outside the repository. The commands below identify the actual immutable input
set; choose fresh output names instead of overwriting the recorded evidence.

```sh
experiment=/mnt/c/Users/강민수/Documents/Codex/rove4k-engines-af-20261020/engines/experiments/tiny-protocol
python3 "$experiment/campaign.py" \
  --a-readable /home/stemxstudio/rove4k-tiny-search-clean-20261020/winner-state/combined.c \
  --a-reference /home/stemxstudio/rove4k-tiny-search-clean-20261020/measure.json \
  --a-search-rename /home/stemxstudio/rove4k-tiny-search-rename-20261020/results.json \
  --a-encoding /home/stemxstudio/rove4k-tiny-encoding-combined-20261020/results.json \
  --a-wrapper /home/stemxstudio/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --d-build /home/stemxstudio/rove4k-tiny-d-final-20261020/build.json \
  --out /home/stemxstudio/new-protocol-build
python3 "$experiment/qualify.py" \
  --build /home/stemxstudio/new-protocol-build/results.json \
  --out /home/stemxstudio/new-protocol-qualification
python3 "$experiment/unit.py" \
  --build /home/stemxstudio/new-protocol-build/results.json \
  --out /home/stemxstudio/new-protocol-units
python3 "$experiment/edges.py" \
  --manifest /home/stemxstudio/new-protocol-qualification/manifest.json \
  --out /home/stemxstudio/new-protocol-edges --timeout 10
```

`campaign.py --no-own-elf` omits D loader packaging, so that mode cannot reproduce
the complete-file comparison or qualify the own-ELF forms. `transform.py` is the
fail-closed readable-source API used by the campaign; the three `.c.in` files
are its implementation inputs. `qualify.py` snapshots shared validators and
uses the existing Tiny A/D retained checks and D runtime injector. `unit.py`
uses `unit.c.in` for counted direct parser units. `edges.py` is independently
authored raw process/byte validation; `--skip-eof` reduces its scope and was
not used in the final campaign. `review.md` separates read-only review from
executed evidence.
