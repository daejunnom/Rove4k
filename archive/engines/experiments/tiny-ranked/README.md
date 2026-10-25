# Packed move-priority representation experiment

This experiment preserves an immutable Tiny A input and implements two defined
priority layouts in a new external snapshot. Canonical engines, older
experiments, selected artifacts, and shared builders are untouched. Neither
layout is selected: complete source launchers are **5299 B and 5303 B**, compared
with the frozen **5283 B** control. Removing a separate score array is a source
representation hypothesis, not an automatic reduction in compressed cost.

The frozen readable input is
`/home/stemxstudio/rove4k-tiny-search-clean-20261020/winner-state/combined.c`,
SHA-256 `109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`.
The selected compact control is
`49aa4d484458d0e4f6d14850fb2260a7007ea40f588003131d43a516d06a592e`;
its complete 5283 B wrapper is
`798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645`.
These are task-specific immutable controls, not a claim about later Tiny A
work. No future producer metadata is substituted for them.

## Actual transformation

`transform.py` admits only the exact readable hash above. It widens the common
`Move` typedef from `unsigned` to `uint64_t`, removes search's separate
`int scores[512]`, and uses the search frame's `Move moves[512]` to hold raw moves
and priority bits. Generator output and all public move objects remain raw.
The old integer priority is computed once per generated move before searching
children, preserving the existing learning snapshot. No child-driven rescore
policy is introduced.

The original signed priority domain, including **all** `int16_t` history and
continuation values, is bounded by `-65536..1405000`: quiets use two signed cells
plus jitter `0..16`; captures use the existing material/PST term; TT priority is
1000000; promotion adds 402000..405000. Bias 65536 gives `0..1470536`, safely
within signed `int`. Cast to `Move` occurs before the unsigned shift.

- `ranked`: priority begins at bit 17. Its packed word uses at most 38 bits.
  Selection compares only `moves[k] >> 17`, with strict `>`. The selected move
  is restored with `&131071` before any board, search metadata, root, worker, or
  TT consumer.
- `ranked32`: priority begins at bit 32, using at most 53 bits. Bits 17..31
  remain zero because the generator emits raw 17-bit moves. A defined
  `(unsigned)` conversion removes the priority. This version explicitly assumes
  the tested target's **32-bit unsigned** and is not a portable replacement for
  mask17 on arbitrary C implementations.

Both keep the existing destructive suffix replacement `moves[j]=moves[i]`.
Comparing the complete packed word would introduce an unintended raw-move tie
breaker; these layouts compare only priority bits. The old selection is not
globally stable: `[A:1,B:1,C:2]` yields `C,B,A`, which must also be preserved.
Selection immediately recovers a raw move before `make`, capture/promotion,
previous-piece metadata, best/root publication and TT data OR-packing. The
draw/PLY-limit branch occurs before packing, when its whole list is still raw.

Widening `Move` changes the type of the jitter arithmetic, but fixed runtime
worker IDs are 0 and 1 and raw moves are at most 131071, so neither the old
32-bit expression nor the new expression overflows and their modulo-17 jitter
is equal. This is a frozen two-worker proof, not support for arbitrary IDs.
Promotion's score contribution is explicitly cast to signed `int`. No
unchecked aliasing, shared union storage, negative signed shift, or uninitialized
high bytes are used.

There is no intended search/order/selectivity change. Board state, move
generation/make, PVS/QS, TT full-key coherence and draw context, history,
continuation, correction, learning lifetime, startup pool and completion/abort
paths remain in the actual source. The internal `Move` ABI and non-search list
storage do change; separately compiled old/new headers must never be mixed.

## Whole-file measurement and reproduction

The fixed target is WSL Ubuntu 24.04 x86-64 Linux, GCC
`13.3.0-6ubuntu2~24.04.1`, Python 3.12.3. Resources are `WORKERS=2`, `TT_BITS=18`,
`PLY=128`. Exactly the selected `cc -Os -x c - -o x -s` recipe, existing fixed
identifier map, and existing shared stream bootstrap/XZ settings
`lc=2,lp=0,pb=0,9e,CRC64` are used. There is no flag or rename sweep and no third
representation. Sanitizers are validation instrumentation at the same `-Os`.

| Actual artifact | Frozen control | ranked17 | ranked32 |
| --- | ---: | ---: | ---: |
| Compact C input | 11351 B | 11397 B (+46) | 11400 B (+49) |
| Stripped native ELF | 22664 B | 22664 B | 22664 B |
| Complete source launcher | **5283 B** | **5299 B (+16)** | **5303 B (+20)** |
| Excess over 4096 B | 1187 B | 1203 B | 1207 B |

Equal native file length is not native identity. Candidate native hashes are
`d54c8adc2dca6df14edcf91568fd7d535b320731f82bbd82885136e166d1d9ee`
and `9d281e461f393e240047ad128be3ae50ef4a46d885c79d8feece82338517adfb`.
Complete wrapper hashes are respectively
`b8eb380c3ce5b13ea0f4660ec0a86326fb73f43e83f0bf67d8306cc96ec03e0f`
and `2cf9da731e3845e391afd329791657650fddd17b8c3fa4024225dd5e50fa6b14`.
All restoration, header, payload and startup/bootstrap code is included in the
complete-file cost. Native identity is required **within** each fixed recipe;
the changed representation produces its own distinct native program.

`campaign.py` reproduced the control's exact compact source, native and whole
wrapper. It compiled every native form twice and packed every whole form twice,
requiring byte equality. All recipe inputs are copied under the new evidence
root. The first 17-bit-only run is retained separately; the bounded two-layout
run reproduces that same candidate and adds the second layout.

Final campaign root:
`/home/stemxstudio/rove4k-tiny-ranked-two-layouts-20261020/`.
The first cost-only run is `/home/stemxstudio/rove4k-tiny-ranked-20261020/`.
Neither candidate is adopted on the basis of its slightly shorter C mechanism.

## Runtime qualification

Both actual complete source launchers and their two-worker development forms
passed **26 common groups**: eight groups per DEV form and five per shipping
form. Coverage includes shared independent perft/legal/state oracles,
promotions/EP/castling, forced mate/stalemate and draw boundaries, clocked and
zero-clock search, active resets, selfplay, EOF and quit. Both retained-feature
checks passed actual PVS/QS/TT/history/continuation/correction counters,
halfmove-dependent TT context, EP correction exclusion and PLY=4 incomplete
iteration boundaries. SMP checks establish the packaged fixed-pool contracts;
they do not require deterministic cross-run SMP node counts.

Both wrappers were separately launched and their actual restored `/proc/.../exe`
hashes matched their new native images. Their source-expression bytes and
unchanged bootstrap skeleton were checked against the frozen recipe. The
restoration temporary directory was removed before engine input, no compiler
child remained, and the same three startup TIDs persisted. NUL and oversized
physical lines were fully drained. Quit reaped the runtime and joined output
readers. Stop causality in shared lifecycle observations remains `unproven`,
as in the validator's contract.

The first qualifier completed all common groups, then its identity harness
used a nonexistent `Engine.startup_thread_ids` attribute. The correct existing
attribute is `startup_task_ids`; only the harness name was corrected. The
second run reused the first **completed** common report after checking exact
engine manifests, artifact hashes, validator bytes and all expected passing
groups; it reran identity and retained checks. Product code was unchanged and
the initial harness failure is preserved.

Final qualification is
`/home/stemxstudio/rove4k-tiny-ranked-qualification-r2-20261020/results.json`;
the original common results remain under
`/home/stemxstudio/rove4k-tiny-ranked-qualification-20261020/common/`.
Independent static review and proof hazards are in `review.md`. Exact
deterministic search/learning/TT and memory-layout proof are recorded separately
by `prove.py`; they are not inferred from the UCI checks.

## Exact internal proof and resource cost

The first independent `prove.py` campaign passed baseline and both candidates at
`-Os` and `-Os` with ASan/UBSan. Fifteen actual fixed-depth search cases exercise
worker IDs 0/1, fourteen depth-4 searches and one depth-3 Kiwipete search,
retained TT, injected signed learning matrices, promotions, EP, mate/stalemate,
repetition and halfmove context. Actual PVS/QS/TT/history/continuation/correction
and correction-controlled reduction paths were exercised. Every canonical
Board/Worker scalar, all path keys, all history/continuation/correction cells,
all feature counters and every TT key/payload were serialized numerically.
The complete **64,475,310-byte** state stream was compared byte for byte and
matched for both candidates and settings, SHA-256
`c9e029e2f075d88539640fa6d30b2b7bcda8eb30172f26d97f4e1d603456e835`.
Structure padding and intentionally different Move/Worker ABI bytes are not
misrepresented as equal logical state.

The exact production priority and destructive-selection blocks are also used
by a separate fixture. Each of the 65,536 `int16_t` values is supplied as a
history cell and separately as a continuation cell, including 32,768 negative
values per kind, with other cells held at fixture extremes. This is not an
exhaustive cross-product of every possible pair of cells. Independent
expectations cover negative/equal priority ties, both worker IDs, reachable
minimum -65536, TT promotions including the 1405000 maximum, all promotion raw
high bits, and a whole-word-comparison failure trap. Each complete form performs
5,864,543 raw-boundary checks on gen/make/capture/root/Worker/TT consumers.

The original ordered event comparison used two 64-bit rolling hashes and event
counts. A separate `-Os` supplemental campaign then captured **all real-search
events for the same 15 cases** and directly compared the entire
**158,529,984-byte** event stream. Both layouts were byte-identical to the
baseline, SHA-256
`00bab87dbe413cb7ac16bbaa6cbfb7956766d5775f2551dc919cbc91959cb1ba`.
This includes actual search entry/return, priority/pick order, gen output,
make/capture arguments and outcomes, child h/r, and TT requests/results. Only
the exhaustive synthetic rank fixture is excluded from this supplemental byte
capture; its full-value hash/count comparison and sanitizer run remain separate
evidence. Raw event/state streams were compressed after direct comparison for
preservation. No matching output was substituted for the actual search.

Actual selected shipping C was additionally compiled via the same stdin argv
with `-fstack-usage`. Each resulting native binary was required to be exactly
equal to its original selected artifact before its production stack metadata
was used. Instrumented proof-frame sizes are kept separately in the report.

| Actual shipping resource | Control | ranked17 | ranked32 |
| --- | ---: | ---: | ---: |
| `sizeof(Move)` | 4 B | 8 B | 8 B |
| `sizeof(Board)` / `sizeof(Entry)` | 176 / 24 B | 176 / 24 B | 176 / 24 B |
| `sizeof(Worker)`, DEV=0 | 68976 B | 68984 B | 68984 B |
| Two-worker array | 137952 B | 137968 B | 137968 B |
| Nominal search list(s), 512 entries | 4096 B | 4096 B | 4096 B |
| Other public 512-entry move list | 2048 B | 4096 B | 4096 B |
| Actual `.text` | 8152 B | 8251 B | 8288 B |
| Actual `.bss` | 171176 B | 171208 B | 171208 B |
| Production recursive search frame | 4480 B | 4480 B | 4496 B |
| Production fallback frame | 2304 B | 4352 B | 4352 B |
| Production main frame | 68272 B | 70320 B | 70320 B |

These are GCC static stack-usage estimates for this exact binary and ABI, not
measured peak RSS or a generic recursion bound. TT allocation remains
`2^18 * 24 = 6291456` bytes, and no worker is added. The widened representation
is not a memory saving; its compiler text grows even where file padding keeps
the full native length unchanged.

The original proof is
`/home/stemxstudio/rove4k-tiny-ranked-equivalence-20261020/results.json`;
the exact-event supplement and production metadata are
`/home/stemxstudio/rove4k-tiny-ranked-equivalence-bytes-20261020/results.json`.
The proof source is frozen at fixture SHA-256
`b5518872047235489ce3181a31bc7a39e6707d1b84cf8312df651963f13574fa`
and driver `e582ae057a1277700c7ec7b2696220398be3561b1e1719130c4b5368b39208cd`.

## Reproduce

Every output path must be a new absolute directory outside the repository.
Use the immutable input set below; do not silently substitute a later best
engine. The scripts fail closed when the readable input or control identity
differs.

```sh
experiment=/mnt/c/Users/강민수/Documents/Codex/rove4k-engines-af-20261020/engines/experiments/tiny-ranked
python3 "$experiment/campaign.py" \
  --readable /home/stemxstudio/rove4k-tiny-search-clean-20261020/winner-state/combined.c \
  --reference /home/stemxstudio/rove4k-tiny-search-clean-20261020/measure.json \
  --search-rename /home/stemxstudio/rove4k-tiny-search-rename-20261020/results.json \
  --encoding /home/stemxstudio/rove4k-tiny-encoding-combined-20261020/results.json \
  --wrapper /home/stemxstudio/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --out /home/stemxstudio/new-ranked-build
python3 "$experiment/qualify.py" \
  --build /home/stemxstudio/new-ranked-build/results.json \
  --out /home/stemxstudio/new-ranked-qualification
python3 "$experiment/prove.py" \
  --sources /home/stemxstudio/new-ranked-build \
  --out /home/stemxstudio/new-ranked-proof
python3 "$experiment/prove.py" \
  --sources /home/stemxstudio/new-ranked-build \
  --trace-bytes --Os-only \
  --out /home/stemxstudio/new-ranked-proof-bytes
```

`transform.py` provides `transform(source,shift=17|32)`. `campaign.py` builds
both declared representations and an exact frozen control with no alternative
compiler setting. `qualify.py` snapshots shared validators, runs packaged UCI
contracts, pins actual restored images and invokes the existing retained check.
Its optional `--reuse-common <completed-common-directory>` requires identical
manifest/validator bytes and complete passing group coverage; that option
records reuse rather than pretending a fresh run. `prove.py` and
`equivalence.c.in` provide the separate deterministic internal comparison. Its
default runs both `-Os` and `-Os` sanitizer settings; `--trace-bytes --Os-only`
records the bounded supplemental exact event stream with the original sanitizer
proof retained separately. Actual production native/stack/ABI metadata is
queried without a new optimization setting or behavioral sweep.

No fair NPS or playing-strength campaign was run. Removing one array has not
closed the 4KiB gap, and no target-conformance or project-completion claim follows
from these bounded representation checks.
