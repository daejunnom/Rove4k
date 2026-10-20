# TinyE shipping HCE cache removal

This independent candidate removes an unconsumed incremental HCE cache from
TinyE's shipping representation. The exact 21 untrained model coefficients,
evaluation features, `[-20000,20000]` clamp, model ordering and existing tactical
ordering remain unchanged. The canonical `engines/compact/tiny-ce` inputs are
read-only dependencies whose source identities are bound by `inputs.json`.

The consumer trace matters: TinyE's existing overlay replaces the search leaf
with `p->s*tiny_raw(p)` and the correction residual with `best-evaluation`.
Its DEV `eval` and `state` commands also use the model. The remaining cache
reader is `verify_board()`, which is already DEV-only. However, shipping
capture ordering still calls `value()` for victim and attacker values before
adding `tiny_order()`. Therefore **`value()` remains in shipping**.

There are exactly two structural forms, `baseline` and `state`. The state
overlay changes exactly three fixed sites: it puts `Board.v` and the subtract
and add HCE expressions in `put()` under `#if DEV`. Mailbox, piece hash and
king-location updates remain unconditional. DEV retains the original cache,
its maintenance and its independent transition invariant. The DEV native
binary is byte-identical between baseline and state. Both forms preserve
PVS/QS, full-key locked TT, history, continuation, correction, legal EP,
third-visit repetition, reversible-path/halfmove TT context, dead material,
ply abort, fixed persistent startup workers and the shipping protocol.

The builder rejects drift in 23 upstream inputs before importing any helper.
Twenty-two retain literal byte bindings. The single exception is
`engines/compact/tiny-ce/core/provenance.json`: its audited Windows copy has
1,503 bytes, 41 CRLF pairs and SHA-256
`e751477788f471f0ec9650deb40a66f3c2423acd95a6a46b8c17f504de7d8520`, while the
Git blob has 1,462 LF bytes and SHA-256
`a996e15e0babc0181215b63e74a55ba675705dbc8df0cbecbb14209de135659a`.
Only those two verified encodings are admitted; CRLF-to-LF replacement proves
their exact shared content identity. The original raw catalog remains in
`inputs.json`. Lone CR, mixed line endings, whitespace or content changes,
equivalence declarations on other paths and CRLF changes to other inputs are
rejected. This does not normalize arbitrary JSON values or rewrite source.

The recipe freezes the actual admitted raw bytes and its own producer/checker
sources into the external `recipe/` tree. `input_sha256` continues to bind the
actual snapshots, while `input_admission` separately records raw byte count,
hash, CRLF/lone-CR counts, admission mode and normalized content identity.
The saved producer replays without reading the checkout.
The overlay additionally rejects missing/duplicate update sites, new cache
readers and changed leaf/residual/ordering consumer shapes. This is a fixed
TinyE transformation, not a general C dead-state optimizer.
The producer/checker resolve output paths and reject Git ancestors; explicit
relative, `..` and symlink output-boundary rejection cases pass without writes.
The focused generator suite has five groups, including LF/CRLF admission,
content-drift/lone-CR/mixed-EOL rejection and the other 22 literal bindings.

The actual complete-file comparison on WSL Ubuntu, GCC 13.3.0, Python 3.12.3,
`-std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0` is:

| Measured object | Frozen TinyE baseline | Cache removal | Change |
| --- | ---: | ---: | ---: |
| Complete selected source stream | 6,107 B | 6,095 B | -12 B |
| Complete selected native ZIP | 10,164 B | 10,113 B | -51 B |
| Compact source | 14,934 B | 14,896 B | -38 B |
| Shipping native ELF | 26,504 B | 26,504 B | 0 B |
| Shipping `sizeof(Board)` | 176 B | 168 B | -8 B |
| DEV native ELF | 31,376 B | 31,376 B | identical bytes |

Source stream sizes include the shell prefix, decompressor, complete compiler
command and C payload. Native ZIP sizes include their decoder. Every native
and complete-wrapper production is repeated and required byte-identical. A
separate producer invocation also reproduced all three native forms and both
selected wrappers. The state source wrapper SHA-256 is
`283f639687c80ddfc5859178ed1a3ce19d4b42b4a9ed5e488d96420811759167`.
This candidate remains **1,999 B above 4,096 B**, with `eligible_4k: false`.

Reproduce using new absolute output directories outside Git:

```sh
python3 -I -B engines/experiments/tiny-e-state/test_generate.py
python3 -I -B engines/experiments/tiny-e-state/build.py --form baseline --out /absolute/new/baseline
python3 -I -B engines/experiments/tiny-e-state/build.py --form state --out /absolute/new/state
python3 -I -B /absolute/new/state/recipe/engines/experiments/tiny-e-state/check.py --build /absolute/new/state/build.json --out /absolute/new/state-check
python3 -B /absolute/new/state/recipe/engines/tests/verify.py --manifest /absolute/new/state/build.json --out /absolute/new/state-blackbox --quick
python3 -I -B /absolute/new/state/recipe/engines/compact/tiny-ce/restoration.py --build /absolute/new/state/build.json --out /absolute/new/state-restoration
```

Run the same three checks against baseline. `check.py` verifies the hashes of
the frozen recipe before executing its saved checker and independent model
reference. It covers the existing hand-computed fixtures and 2,007 dense,
promoted and arbitrary boards in optimized and ASAN/UBSAN DEV harnesses. The
actual completed two-worker depth-four search has positive model leaf,
model ordering, PVS/QS, history, continuation, correction update/use activity.

The additional `contract.c` includes the actual producer DEV, original and
compact translation units, compiling each in optimized and ASAN/UBSAN forms.
Each of these six runs per structural form compares 20,000 raw/clamped
evaluations and 160,000 ordering predictions with independent scalar formulas,
including both clamp extremes. It checks 206,389 legal child transitions
against a recomputed hash and, in DEV, an independent full HCE sum. All runs
have transition digest `27256fa4c94f319e` and identical fixed depth-four score,
move, history, continuation and correction results. Intentional fixtures cover
legal/pinned EP, every quiet/capture promotion, both castlings and colors,
dead material, second/third repetition, halfmove draw, mate precedence,
full-key collision miss, TT halfmove/path context and live-position ply abort.

The frozen quick black-box suite passes 28 groups per structural form across
DEV, original, compact, selected source and selected native artifacts. Its
shipping checks exercise legal short play, malformed protocol, stop/restart,
active quit and EOF. Restoration independently reads the complete
`/proc/<pid>/exe` image of both selected wrappers, checks the expected native
hash, requires three stable startup threads before search, and verifies no
temporary files survive exec. The checked processes have exited; managed
build/check sessions reached terminal success. These checks provide local
functional and byte-reproduction evidence, with no strength, elapsed-time
search equivalence or target high-thread-count performance claim.

The EOL fix was independently replayed on Linux from an external controlled
tree containing all 23 actual Git HEAD blobs plus the current candidate
producer. A complete LF baseline, LF state, saved-LF-recipe replay and Linux
state production using the Windows CRLF provenance snapshot reproduced the original generated DEV/original/compact
sources, all native images and every complete wrapper byte-for-byte. This
supports reuse of the exact-image consumer and black-box evidence above;
the 56-group matrix was not rerun for a producer admission change. The LF
state wrappers separately passed fresh native-image/startup/cleanup checks.
The previous LF rejection was reproduced and preserved along with its original
source, catalog and reports. No old result was overwritten.

Original functional evidence is outside Git under
`/home/stemxstudio/rove4k-tiny-e-state-20261020-evidence/final2/`, including both
`build.json` files, recipe trees, consumer/black-box/restoration reports and
`comparison.json`. The source-encoding audit, original LF failure, fresh
productions and exact-image reuse proof are preserved under the same evidence
root's `eol/` directory. No training or AWS work is involved.
