# TinyE model-only capture ordering

This is one explicit search-ordering policy experiment over the qualified
`tiny-e-state` cache-removal candidate. The historical qualified control reproduced
that candidate's actual source, native images and selected complete files. The new policy removes
the duplicated legacy HCE/PST contribution from capture priority:

```c
scores[i]=m==tt?1000000:capture(p,m)?500000:
    w->history[from][to]+w->continuation[prior][pi]+(int)((m*37u+w->id*19u)%17);
if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;
scores[i]+=tiny_order(p,m);
```

The frozen model already contributes its exact `16*victimMaterial-attackerMaterial`
prediction through `tiny_order()`. The old capture base additionally used
`16*abs(value(victim,to))-abs(value(attacker,from))`, including the legacy PST.
Removing that second contribution changes capture order and can change visited
nodes, LMR decisions, learning and the eventual search result. This is **not a
lossless source transformation** and has no strength-improvement claim.

All 21 hand-authored, untrained coefficients remain exact and consumed: sixteen
evaluation weights and five move-order weights. The model evaluation, clamp,
capture/attacker/promotion/center/pawn-advance prediction and unconditional
addition to move scores are unchanged. EP continues to supply a pawn victim
inside the model even though its destination is empty. King/empty material is
still zero. The TT move base, promotion base, legal move generation, QS tactical
predicate and quiet-move history/LMR eligibility remain unchanged.

After cache removal, the old capture expression was the only shipping reader
of `value()`. Its definition is now DEV-only. The single-translation-unit
stitcher already removes its API prototype before this overlay. DEV still
maintains the independent HCE cache and verifies it after transitions. The
shipping `Board` has no HCE cache. No C/Rust canonical source is modified.

An independent agent reviewed the consumers and policy before implementation,
and reviewed the implementation separately. The authoritative generator retains
24 upstream input identities: the existing 23-input TinyE catalog and the exact
state overlay. Four historical build/packaging identities are admitted from the
explicit `engines/experiments/packaging-control/` copies of `tiny-ce-build.py`,
`pack.py`, `pack_single.py` and `pack_stream.py`. Their original logical catalog
keys and expected hashes are unchanged; `input_admission` records each actual
control source path. The original catalog's narrowly admitted LF/CRLF
provenance JSON encodings are retained; other input bytes remain literal.
Missing/duplicate overlay sites and altered model/leaf/ordering consumers are
rejected. The actual admitted raw bytes and producer/checker sources are copied
into the external recipe before use. Current `engines/scripts/pack.py`,
`engines/compact/tiny-a/pack_single.py`, `engines/compact/tiny-a/pack_stream.py`
and `engines/scripts/compiler_group.py` are frozen separately at their canonical
recipe paths. These current producers create the new wrappers; historical
catalog admission does not select an old wrapper producer. Saved recipes retain
both explicit path sets and replay without consulting the mutable checkout.

The historical measured fixed build used Ubuntu 24.04.4, GCC 13.3.0 and Python 3.12.3, with
`-std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0`. There is one existing XZ
source-stream recipe and one existing LZMA native-ZIP recipe, with no new flags,
codec presets, models, names or representation search.

The following sizes, wrapper hashes and v3 qualification results describe the
preserved historical wrappers. The current compiler-group owning wrappers have
not been produced or qualified under this adapter update, so those results do
not establish their byte identity, size or runtime behavior. New reports record
`packaging.historical_wrapper_identity_claimed=false` and
`packaging.current_wrapper_qualification="not_yet_executed"`, alongside the
historical control paths and the actual frozen current-producer byte/hash pairs.

| Object | Cache-removal control | Model-only capture prior | Change |
| --- | ---: | ---: | ---: |
| Complete source stream | 6,095 B | 5,959 B | -136 B |
| Complete native ZIP | 10,113 B | 9,877 B | -236 B |
| Compact C source | 14,896 B | 14,547 B | -349 B |
| Shipping native ELF | 26,504 B | 26,440 B | -64 B |
| Shipping Board | 168 B | 168 B | 0 B |

The new source stream has a 75-byte shell prefix and a 5,884-byte XZ payload
containing the Python bootstrap, complete C source and fixed compiler command.
Its SHA-256 is
`e4641519f463b2e7fd676831abf6e6d2dc49c061a1189d36670ecdb880b1b69d`.
The native ZIP SHA-256 is
`241ef27ecb531c95f8453ebfb938212f4b260464aee911843b64f68408b5e87a`.
This is **1,863 B above 4,096 B**. No tournament eligibility or final acceptance
is claimed. The separately qualified minimal-UCI E candidate is a different
experiment; its saving is not added to this result.

Each DEV/original/compact native and each stdin-restoration native is compiled
twice and compared byte-for-byte. Original and compact native files are also
byte-identical within each policy. Both complete wrappers are reproduced.
An independent subsequent full producer invocation reproduced all three source
forms, all native images and the selected wrappers for each policy. The control
also matches the historical qualified cache-removal candidate by actual hashes.

Use the current producer CLI on Linux with new absolute directories outside Git.
It freezes and uses the current compiler-group owner while keeping the historical
catalog identities separate; it does not claim to reproduce the old wrapper
hashes. The commands below are the current production and qualification path,
not a record of new executions:

```sh
python3 -I -B engines/experiments/tiny-e-order/test_generate.py
python3 -I -B engines/experiments/tiny-e-order/build.py --form control --out /absolute/new/control
python3 -I -B engines/experiments/tiny-e-order/build.py --form model --out /absolute/new/model
python3 -I -B /absolute/new/model/recipe/engines/experiments/tiny-e-order/check.py --build /absolute/new/model/build.json --out /absolute/new/model-consumers
python3 -B /absolute/new/model/recipe/engines/tests/verify.py --manifest /absolute/new/model/build.json --out /absolute/new/model-blackbox --quick
python3 -I -B /absolute/new/model/recipe/engines/compact/tiny-ce/restoration.py --build /absolute/new/model/build.json --out /absolute/new/model-restoration
```

The remaining result paragraphs summarize preserved historical v3 evidence;
they are not new qualification of the current owning wrappers.

The model consumer runs hand-computed evaluation, capture, promotion and EP
fixtures and 2,007 dense/random positions against the independent frozen scalar
oracle in optimized and ASAN/UBSAN builds. Actual completed two-worker search
reports positive model leaf, model order, PVS, QS, history, continuation and
correction update/use activity. These DEV search observations use the changed
policy, rather than relabeling an older DEV executable.

`contract.c` additionally includes each actual generated DEV/original/compact
translation unit in optimized and ASAN/UBSAN forms. Each of the six executions
per policy checks 20,000 raw/clamped evaluations, 160,000 model-order predictions
and 206,389 legal child transitions, with transition digest
`27256fa4c94f319e`. It verifies independent hash and model sums, DEV HCE,
legal/pinned EP, all quiet/capture promotions, both castles/colors, dead
material, third-visit repetition, halfmove draw, mate precedence, coherent
full-key collision miss, halfmove/path TT context and live-position ply abort.
Both clamp extremes are exercised. Actual search updates nonzero history,
continuation and correction cells.

The checker inserts one test-only forward declaration and a post-assignment
observer into a saved copy of each production translation unit. It does not
replace the score expression or the model. An independent scalar oracle checks
59,555 actual score assignments per execution, including 1,401 captures, six
EP cases, 28 promotions and 37 TT-priority cases. There are 1,398 non-TT captures
where the removed legacy prior is nonzero. This proves the new shipping
consumer uses the changed priority, including special cases, rather than merely
checking the unchanged model in isolation. The original production source and
instrumented-copy hashes are separately recorded.

The frozen quick suite passes 28 groups for each policy across DEV, original,
compact, selected source and selected native forms. It covers minimal UCI
handshakes, clocked search, legal short play, malformed/unsupported commands,
stop/restart and active quit/EOF. Selected source/native wrappers separately
restore their expected complete `/proc/<pid>/exe` bytes, have three stable
startup threads before search, leave no temporary files after exec and exit
normally. These local checks establish the described functional scope, with no
Elo, arbitrary-depth, 512-hardware-thread scaling or elapsed-time speed claim.

Evidence is outside Git under
`/home/stemxstudio/rove4k-tiny-e-order-20261020/`, including `control-final`,
`model-final`, both `*-check-v3` and `*-blackbox-v3` reports,
`model-restoration-v3`, and `comparison-v3.json`. The initial producer failure
incorrectly expected an API prototype already removed by the lean stitcher;
that failed recipe is preserved in `control/`. Correcting this source-shape
assumption changed no engine behavior or acceptance expectation. Earlier v2
productions are preserved and match v3 engine/output bytes.

The final metadata labels `state_overlay` as an intermediate stage and records
the final shipping `value()` consumer explicitly; this avoids mistaking the
state overlay's historical capture-order reader for a final-model reader. The
original v3 reports are preserved. `freeze-receipt.json` verifies that this is
the only producer-text change, all other frozen checker/oracle inputs match,
and every generated source, native and complete wrapper is byte-identical to
the tested v3 form. It reuses the exact-image v3 functional evidence under that
binding, rather than reporting unperformed additional tests.
