# TinyE capture-prior and minimal-UCI composition

This candidate actually composes the qualified 5,959-byte E capture-material
prior with the qualified 6,031-byte E minimal shipping UCI policy. Their common
root is the exact 6,095-byte shipping-cache-removal candidate. Neither component
folder is modified. This is a composition of two declared policy changes, not
lossless compaction or an arithmetic sum of earlier size savings.

The actual complete source file is **5,899 bytes**, including its shell prefix,
decompressor/bootstrap, source and complete compiler argv. It is 60 bytes smaller
than the order-only control and 132 bytes smaller than the minimal-UCI-only
control. Adding the isolated 136-byte and 64-byte savings would have predicted
5,895 bytes; that prediction is not the measured result.

| Candidate | Compact C | Restored stdin ELF | Complete source file |
| --- | ---: | ---: | ---: |
| Qualified E state root | 14,896 B | 26,504 B | 6,095 B |
| Exact order-only control | 14,547 B | 26,440 B | 5,959 B |
| Exact minimal-UCI-only control | 14,701 B | 26,472 B | 6,031 B |
| Actual composition | **14,352 B** | **26,408 B** | **5,899 B** |

The whole-file SHA-256 is
`ccf1a0b4c2163b46c445d4ec1add03bcc75ba75d66cd1647ab9dc2ca556687f3`.
The restored native SHA-256 is
`5429f2d80521f775bac6802ec4940e8e0ff1b344464ed8e9a0629ba6650eb675`.
These are the stdin compiler identity class. Historical file-compiled native
images are kept separate. This candidate remains **1,803 B above 4,096 B**;
there is no final eligibility, playing-strength or high-worker-scaling claim.

## Canonical composition and protected source

`build.py` admits literal raw component-report hashes and five exact upstream
helper files before importing code. It freezes them, its own producer/checker
sources and the complete qualified E-state recipe. It regenerates the readable
root through the original core/stitch/model/cache-overlay graph, with the
original input provenance and narrowly admitted provenance-JSON LF/CRLF forms.
There are 53 frozen inputs in the complete build manifest. Unknown source,
report, input bytes, resource counts, compiler recipes or source shapes fail.

The local `generate.py` proves composition in two independent orders:

1. Replay the existing UCI transform on the literal state source and require
   exact equality with the qualified minimal-UCI readable source.
2. Replay the exact order overlay on the state source and require exact equality
   with the qualified order-only readable source.
3. Apply the same order overlay to the minimal-UCI source.
4. Separately prove the order-only `go()` and `main()` equal the state versions,
   transplant only the complete minimal functions into the order-only source,
   and require full-byte equality with step 3.
5. Require all bytes outside `go()` and `main()` to equal the order-only source.

The protected complement is 23,218 bytes with SHA-256
`631e2f93b998efd918dbc89df56785e8831a31751e43962a1f034599ee29daab`.
This includes the actual 21 exact hand-authored untrained coefficients, model
evaluation/clamp, model ordering, legal transitions, hashes and TT context,
coherent full-key TT, PVS/QS, history/continuation/correction, worker body and
completion helpers. The qualified UCI transform also preserves the explicit
startup/publication/reuse/join boundaries in the changed functions.

The ordering policy retains the exact model capture-material prior while
removing the duplicated legacy HCE/PST prior. It keeps the TT/capture-class/
promotion bases and all five model-order terms. Search order, later LMR and
learning can differ from the original state root. DEV also uses that new
ordering, with its independent legacy HCE transition oracle retained.

DEV's protocol remains the strong diagnostic protocol of the order-only form.
The actual preprocessed DEV source and independently stdin-compiled native
image are byte-identical between the order-only control and composition. They
are not asserted equal to historical file-compiled DEV images.

## Fixed recipe and fresh selected-file behavior

The build preserves the admitted control's actual bootstrap and compiler argv;
only its exactly restored C source argument changes. It uses Ubuntu 24.04.4,
GCC 13.3.0, Python 3.12.3, two search workers, TT bits 18, `-std=c11 -Os -pthread`,
and the selected XZ 9 extreme `lc=3/lp=0/pb=2` recipe. There are no flags, codecs,
names, representations, resource profiles or model sweeps. Both component
source/native/whole controls reproduce their qualified hashes exactly.
Source generation, shipping native compilation and whole packaging each run
twice. An additional saved-recipe invocation reproduces every generated source,
native/DEV image, bootstrap and complete wrapper independently.

Shipping `uci` returns only `uciok`. `stop` and `ucinewgame` are consumed without
cancellation or TT clearing. Bare `go` has the existing qualified 1,000 ms
default; the unknown shipping `infinite` token uses that same finite default
when no clock is present. Own-side clock/increment arithmetic and its caps are
unchanged. The 256-node polling interval means this is not a strict real-time
completion bound. Subsequent `go`, `position`, `quit` and EOF retain actual old
epoch completion before state/storage reuse.

`verify.py` freezes the already qualified policy checker and independent
oracle unchanged. The selected composed wrapper passes two fresh actual
shipping sessions, policy and active EOF, plus one strict ordered-DEV session.
They cover minimum handshake, own-side clocks/increments and field order,
finite bare/infinite-token go, tolerated stop/newgame with continued CPU
progress, next-go and position barriers, active quit and EOF. Actual bestmoves
are checked by the independent oracle, whose twelve perft self-checks pass.

Both wrapper sessions verify the complete running `/proc/PID/exe` image,
wrapper-to-native PID identity, exactly three stable startup TIDs, only fd
0/1/2, no compiler child or temporary file after exec, joined readers and
native process absence on completion. `stop_causal_link` remains explicitly
unproven; consuming ignored controls is not claimed as cancellation.

The complete `go()` body also matches the previously qualified A function
exactly. This binds reuse of its default-budget/clock-arithmetic observations
only. It does not claim a new E whole-TT snapshot proof.

## Bounded core evidence reuse

`proof.py` rechecks the actual composition and ordered-source complement. It
freezes its own executing bytes, hard-pins the E-order freeze receipt and its
actual positive-search receipt, and verifies the old checker/oracle, all source
and compiled consumer-image links. The six historical optimized/sanitized
DEV/original/compact runs remain historical executions: each checks 20,000
raw/clamped evaluations, 160,000 model-order predictions, 206,389 legal child
transitions and 59,555 actual production priority assignments, including EP,
promotions and TT priority. The old actual completed search has positive model
leaf/order, PVS/QS, history/continuation/correction update/use activity.

These results are reused only after full complement equality, exact component
source reproduction and actual DEV source/stdin-image equality. The old TT
context fixture proves halfmove/path key separation and coherent collision
miss; it is not relabeled as a newly forced production cutoff/miss. The
fresh wrapper policy evidence above is separate. No full candidate matrix,
model training, games/Elo, AWS work or high-worker performance test was run.

Two focused tests cover source drift/independent composition, unterminated
function rejection and output/recipe boundaries including relative paths,
existing directories, Git ancestors and resolved symlinks. An independent
read-only review found no engine/composition blocker and independently checked
all 53 frozen inputs, actual source/native/wrapper hashes, DEV identity and a
separate complete-function transplant. It identified a missing literal hash
for the historical positive-search JSON; that evidence binding was fixed and
the proof rerun. Earlier proof snapshots remain preserved.

Reproduce on Linux with new absolute output directories outside Git:

```sh
python3 -I -B engines/experiments/tiny-e-compose/test_generate.py
python3 -I -B engines/experiments/tiny-e-compose/build.py --out /absolute/new/compose
python3 -I -B /absolute/new/compose/recipe/engines/experiments/tiny-e-compose/verify.py --build /absolute/new/compose/build.json --out /absolute/new/runtime
python3 -I -B /absolute/new/compose/recipe/engines/experiments/tiny-e-compose/proof.py --build /absolute/new/compose/build.json --out /absolute/new/core-proof
```

Saved source recipes avoid the mutable checkout, but still require the exact
retained historical component trees and policy/core receipt archives. The
`--state-build`, `--order-build` and `--uci-build` overrides change locations,
not raw hash admission. This is not a standalone binary-only historical replay.

Evidence is outside Git under
`/home/stemxstudio/rove4k-tiny-e-compose-20261020/`. `first` and `replay` preserve
the first actual cost build and independent saved-recipe replay. `final2`
includes the evidence-checker fixes; its complete generated source/native/
bootstrap/wrapper bytes are identical to the tested first artifacts. The two
fresh shipping sessions and DEV session are in `runtime/results.json`; the
final strict historical binding is in `core-proof-final2/results.json`.
`freeze-receipt.json` records those identities and the narrow exact-image
runtime reuse across checker-only changes, without reporting another physical
wrapper execution.
