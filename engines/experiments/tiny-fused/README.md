# One fixed-stage fused producer experiment

This is one independent project implementation, with no external engine code
copied. It changes only a frozen Tiny A snapshot under a new external output
root. Canonical engines, existing experiments, selected artifacts and shared
builders remain unchanged. The hypothesis **failed its primary whole-source
cost gate**: the complete launcher is **5739 B versus the frozen 5283 B**.
The candidate is unselected. No flag, name, preset or representation sweep was
run after the result, and no full verification or performance campaign was
started to enlarge the failed candidate's test count.

## Shared producer and deliberate search policy

The geometry walk now emits a raw 17-bit `Move` and one `Fact`: origin,
destination, moving piece, actual victim piece/cell, and optional castling rook
cells. The shared `apply` consumes these facts into a copied child. It retains
incremental HCE/hash, rights, halfmove clock, legal normalized EP, own-king
filtering and reversible path `r`. Parents remain immutable; EP attack scratch
does not invoke normalization or another transition recursively.

One `offer` emitter serves first-legal/witness queries, exact input-move
matching, DEV raw collection, priority survey and actual searched moves.
Shipping no longer contains the old public `gen`/`make` adapters or the separate
first/matching loops. DEV adapters remain so existing development tools can
collect raw pseudo moves and apply generated moves. Matching returns the actual
child, so transactional replay does not call make again. Existing line framing,
numeric policy, command matching and fixed pool/completion code remain.

The search removes `Move[512]` and `scores[512]`. A survey freezes two preferred
facts and verifies TT membership in the actual producer. The order is:

1. The TT move, only if it matched actual generated geometry.
2. Best tactical move from the survey, excluding TT.
3. One geometry-order pass of remaining tactical moves.
4. Best quiet from the survey, excluding TT.
5. One geometry-order pass of remaining quiets.

Thus there are at most **three complete enumeration passes**: survey, remaining
tacticals and remaining quiets. Fixed prefix visits do not re-enumerate. Attack
and EP legality probes are separate geometry queries. There is no seen bitmap,
no repeated whole walk per selected move, no priority bits in public moves and
no full-array selection sort. Each later pass skips the TT and its class's
preferred raw identity, even when that prefix failed the own-king filter.
Every N/B/R/Q promotion remains a distinct raw move.

The preferred quiet uses actual history, continuation and worker jitter; the
preferred tactical uses material/PST ordering and promotion bonus. Both are
snapshots taken **before any descendant search**. Later learning does not
rerank either prefix or the remaining geometry-order moves. The EP tactical
priority uses its actual captured pawn/PST instead of the empty destination.

This is an explicit **move-order and LMR placement policy change**, not an
identical-node representation refactor. PVS/QS, genuine history/continuation
learning and learned correction remain. The remaining moves no longer receive
the baseline's full score ordering. Different ordering can change reductions,
node counts, selected lines and playing strength; none of those is claimed to
match or improve. Copy children were retained because standalone undo did not
offer a justified source saving and would complicate completion cleanup.

## Design review before compilation

The readable source was frozen and independently reviewed before the first C
compile. One review found that material draw had to be incorporated before the
PLY limit: a legal K/K or K+B/K at the cap must return draw without setting the
abort flag. The decision now follows the survey's material tally. Draw/cap
handling still obtains a legal witness so mate/stalemate takes precedence.

Self-review also corrected the quiet TT move in noncheck QS: a legal quiet TT
move supplies a witness but cannot stop later capture search unless stand-pat
already reaches beta. The quiet pass may stop once only a legal witness remains
necessary. These fixes happened before the measured candidate was compiled.
The resulting readable SHA-256 is
`60ae3c097b2337f6b7a260824c61c819a95f90c38a7512c52f8eb9bd5d76f5be`.

The copied child lives through the complete reduced/null/full PVS retry bundle.
Path keys are pushed once and popped before stop checking, learning or result
updates. Current-node TT data is published only after a legal witness and a
complete search. Query modes do not publish TT data. Full key and the existing
acquire/release slot lock, halfmove/reversible-path context and mate distance
packing remain. The survey version reads a coherent TT slot before its material
draw decision, but consumes no bound or hit counter on that draw path.

## Exact frozen cost comparison

The historical control is the 11351 B selected Tiny A input, SHA-256
`49aa4d484458d0e4f6d14850fb2260a7007ea40f588003131d43a516d06a592e`.
Its readable precursor is SHA
`109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`.
Both use the exact fixed two-worker, `TT_BITS=18`, `PLY=128`, GCC 13.3.0
Ubuntu x86-64 recipe `cc -Os -x c - -o x -s`, unchanged fixed identifier
mapping, resource literals, compiler bootstrap and XZ `9e/lc2/lp0/pb0/CRC64`.
New identifiers were not retuned by a spelling sweep.

| Actual artifact | Frozen control | Fused | Change |
| --- | ---: | ---: | ---: |
| Compact C compiler input | 11351 B | 12655 B | +1304 B |
| Stripped native ELF | 22664 B | 22664 B | same length, different bytes |
| Complete source launcher | **5283 B** | **5739 B** | **+456 B** |
| Excess over 4096 B | 1187 B | 1643 B | +456 B |

The control's exact compact source, native and complete wrapper were reproduced.
Each native form was compiled twice and each complete package produced twice;
the repeated bytes had to match. The fused native is
`9a9683f900a6b146791b5aabd5bd4662694bf290886fdfebdf13a792778fed2b`;
its compact source is
`47979a944610053cacc865e13b0cf170a21bc208361be0e0e19714064dea40d7`;
its complete launcher is
`51c1da31d86077f14df0bdbf77cc29fc80e721a486efdef992dba6060ab9035b`.
Every bootstrap/header/payload/restoration byte is included in the whole-file
figure. Equal native lengths do not establish identical programs. Native
identity gates apply to repeat generation within each recipe, not between
changed search policies.

The actual old consumer loops were removed, but the fact/context structures,
field access and mode glue cost more source than they replaced. This is useful
negative evidence against adding a generic visitor around this already compact
core. A future monolithic kernel without this context layer is a different
experiment, not an unmeasured improvement of this result.

Immutable measurement root:
`/home/stemxstudio/rove4k-tiny-fused-20261020/`.
The pure precompile design snapshot is separately preserved under
`/home/stemxstudio/rove4k-tiny-fused-design-20261020/`.

## Bounded qualification

After the loss was reported, scope stayed limited to targeted correctness
fixtures and one actual-wrapper smoke. The wrapper smoke passed exact restored
native identity, three fixed startup TIDs, temporary directory removal before
engine input and no compiler children. White/black zero clocks returned legal
moves. Active stop and active quit each yielded one legal completed result;
runtime absence and output-reader joins were checked. CPU progress was observed
before control, but cancellation causality remains explicitly `unproven`.
The report is `/home/stemxstudio/rove4k-tiny-fused-smoke-20261020/results.json`.
This single process is not a full shipping-protocol, all-rule, large-resource or
strength qualification.

The focused actual-code fixture in `check.py` and `unit.c.in` passed at `-Os`
and the same `-Os` with ASan/UBSan, under one second of combined execution. It
checks dead K/K and K+B/K at the PLY cap without abort; a nondead cap with an
actual abort; and mate precedence at halfmove 100. A quiet TT hint followed by
a hanging-queen capture returns score 900, so a quiet witness cannot suppress
QS captures. An impossible TT move never reaches application.

One observation hook immediately before the real `offer` application records
only the test root; it changes no outcome or algorithm counter. Eight depth-1
full-window roots visit every generated raw move **exactly once**, with counts
20/48/5/26/7/11/10/23. They include illegal tactical and quiet prefixes and a
king-capture candidate. Small perft references (start 20/400/8902 and Kiwipete
48/2039), all four promotion queries, EP/castle child parity, third repetition
and late-invalid transactional rollback passed. A natural retained depth-4
search reports nodes 3210, PVS 1904, QS 1998, TT hits 684, history/continuation
updates 704 each, correction updates 10 and correction uses 17, with the key
path unwound. These counters are actual observed execution, not injected proof
markers. In the DEV unit, Fact is 32 B and Visit is 240 B; Board remains 176 B.

This fixture is deliberately separate from exact-node parity, which would be
the wrong requirement for the declared policy change. It is a bounded targeted
check, not the full rules/protocol suite. The report is
`/home/stemxstudio/rove4k-tiny-fused-targeted-20261020/results.json`.
Windows frozen sources, artifacts and reports are outside Git at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-fused-20261020-evidence/`.

## Reproduce

Use a new absolute external output directory for every command. The scripts
retain the immutable source/encoding controls; do not silently substitute a
later Tiny A winner. No NVCompact dependency is used.

```sh
experiment=/mnt/c/Users/강민수/Documents/Codex/rove4k-engines-af-20261020/engines/experiments/tiny-fused
python3 "$experiment/campaign.py" \
  --readable /home/stemxstudio/rove4k-tiny-search-clean-20261020/winner-state/combined.c \
  --reference /home/stemxstudio/rove4k-tiny-search-clean-20261020/measure.json \
  --search-rename /home/stemxstudio/rove4k-tiny-search-rename-20261020/results.json \
  --encoding /home/stemxstudio/rove4k-tiny-encoding-combined-20261020/results.json \
  --wrapper /home/stemxstudio/rove4k-tiny-encoding-xz-20261020/03-lc2-pb0/x \
  --out /home/stemxstudio/new-fused-cost
python3 "$experiment/smoke.py" \
  --build /home/stemxstudio/new-fused-cost/results.json \
  --out /home/stemxstudio/new-fused-smoke
python3 "$experiment/check.py" \
  --source /home/stemxstudio/new-fused-cost/fused/combined.c \
  --out /home/stemxstudio/new-fused-targeted
```

`transform.py` owns the only source architecture. The five `.c.in` files define
the shared types, transition, walk, search/emitter and public query wrappers.
`campaign.py` snapshots them and the selected producer helpers, reproduces the
historical control, then measures exactly one candidate. `smoke.py` snapshots
the existing shared process/oracle helpers and runs the actual whole wrapper.
`check.py` supplies the separate bounded target fixture. No full suite, fair
NPS campaign, playing-strength or 4096 B conformance claim follows.
