# The same minimal shipping UCI policy on Tiny B, C, E and F

This bounded experiment applies the one qualified `tiny-uci-min` shipping
policy to four exact, previously qualified controls. It changes only this new
experiment; canonical engines, earlier experiments and the shared checker are
unchanged. D's native/own-ELF composition is outside this experiment. This is a
declared protocol policy change, not semantic-preserving compaction. All code
is derived from the repository's own MIT sources; no foreign engine source is
copied.

The whole-file reductions are **64 B for B, 60 B for C, 64 B for E and 72 B for
F**. These are actual independent measurements, not A's 60-byte result added to
other receipts. None reaches the 4,096-byte gate.

| Family and fixed qualified architecture | Control compact source | New compact source | Control restored native | New restored native | Control whole file | New whole file | Whole change | Above 4096 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B, SEE/singular | 15,761 | 15,566 | 26,624 | 26,592 | 6,283 | **6,219** | -64 | 2,123 |
| C, AVX2 startup PSQT | 14,439 | 14,244 | 26,488 | 26,464 | 6,015 | **5,955** | -60 | 1,859 |
| E, 21 coefficients/order, shipping HCE-cache removal | 14,896 | 14,701 | 26,504 | 26,472 | 6,095 | **6,031** | -64 | 1,935 |
| F, full-depth MTD(f), fixed encoding | 13,185 | 12,982 | 22,664 | 22,664 | 5,551 | **5,479** | -72 | 1,383 |

Every whole-file figure includes the shell prefix, decoder/bootstrap, source
literal and complete compiler command. The restored-native column is the
actual compiler-stdin identity class. In particular, B/C/E's historical
file-compiled ELF hashes differ from their restored stdin images; these are
not interchanged. No resource, compiler flag, codec, parser or spelling sweep
was performed.

## One policy and preserved boundaries

As in the separately qualified A experiment, shipping `uci` emits only
`uciok`. `stop` and `ucinewgame` are consumed without cancellation, waiting or
TT clearing. Bare `go` has a 1,000 ms default budget. The optional shipping
`infinite` extension is removed: it is an unknown token, so clockless
`go infinite` has the same finite default. An own-side clock retains the
existing `clock/30 + min(increment,86400000)*3/4` formula, the `clock/5` cap,
minimum 1 ms and final 86,400,000 ms cap. Timing is polled per 256 claimed
nodes; the budget is not a strict real-time completion guarantee.

The [official TCEC 4k sections 7.9–7.11](https://wiki.chessdom.org/Rules#TCEC_4k_rules)
distinguish the minimum commands, including bare `go`, from error-free
consumption of other commands and optional identification/information/options.
This policy preserves the project's additional next-go, position, quit and EOF
completion/resource boundaries. Every affected input still settles an old
epoch before worker/root fields are reused or storage is freed. Startup TT
atomic initialization and persistent worker creation remain in place. This
does not claim that optional `stop` has the previous stronger semantics.

The transform admits four literal readable-source hashes and fixed source
shapes. F's original identification is specifically `Rove4k F full-depth MTD`,
not a wildcard name. An initial pure shape check rejected the shorter assumed
name; the exact pinned F source justified that one explicit spelling. No
candidate was compiled or measured from the rejected shape. Unknown content,
source layouts, fixed resource counts or recipe/report identities fail closed.

All bytes outside the complete `go` and `main` functions are identical between
each control and candidate, verified from the actual readable inputs. This
includes board transitions, hash/reversible-path/halfmove context, TT,
PVS/QS/history/continuation/correction, B SEE/singular, C constructor/table/SIMD,
E coefficients/evaluation/order and F full-depth MTD(f). DEV source after the
same preprocessing/minification and its native image are byte-identical
within each comparison. Those new DEV images need not equal historical
readable-file-compiled DEV images: source preprocessing and stdin compilation
are separately identified, so old positive evidence is reused through actual
unchanged readable bodies rather than a false native-image identity claim.

## Exact producer and selected-file runtime evidence

`family_bf.py` and `family_ce.py` hard-pin their qualified raw reports and
selected controls, freeze the upstream recipe before importing it, regenerate
the readable source from its original core/overlay/stitch graph and require
exact equality with the recorded readable input. B uses its qualified source
stream; C uses the qualified constructor PSQT; E uses the qualified cache
overlay; F reapplies its already fixed structural and spelling/encoding
decisions. No earlier builder's multi-format launcher search is rerun.

`build.py` reproduces each control's compact source, restored native image and
whole file exactly, then independently repeats source generation, native
compilation and whole-file generation for both forms. The selected bootstrap
is decoded from the actual admitted wrapper. Only its source argument changes;
the exact literal is restored and compared. B/C/E retain their selected XZ 9
extreme `lc=3/lp=0/pb=2` profile; F retains its selected `lc=2/lp=0/pb=0` profile.
All use the same two search workers, one command thread, TT bits 18 and original
compiler argv. C remains fixed AVX2. No AWS, training, many-core run, fair NPS or
playing-strength measurement is part of this work.

The producer root is
`/home/stemxstudio/rove4k-tiny-uci-portfolio-20261020`.
Its `results.json` has SHA-256
`f4833f5922dcdddad9abcdbd82f588d1d1e51a5a0e6c63f46b7693fdcbae6455`.
Its four original cost-stage `runtime_qualified: false` fields are retained;
later evidence is separate and does not rewrite that stage.

`verify.py` freezes the already qualified A process/policy checker unchanged.
It runs only the four selected whole-file winners, each in a policy session
and active EOF session, plus one strict DEV control session per family:
**8/8 shipping sessions and 4/4 DEV sessions pass**. It also requires the exact
complete new `go` body to match the qualified A body, binding reuse of A's
independent clock-arithmetic/default-budget instrumentation. That narrow reuse
does not claim a fresh whole-TT memory snapshot for C or E.

Each winner passes actual minimum handshake, own-side clocks/increments and
field order, finite bare/infinite-token go, tolerated stop/newgame, live CPU
progress before/after ignored controls, next-go/position fences, active quit
and EOF. The full `/proc/PID/exe` hash matches the newly built native image,
the wrapper PID becomes the native PID, exactly three startup TIDs persist,
only fd 0/1/2 remain, and no compiler child or temporary file survives startup
or shutdown. Actual bestmoves are checked by the frozen independent oracle;
its 12 fixed perft self-checks pass. Reader join and process absence are
required. Receipt ordering still has `stop_causal_link=unproven`; no stronger
cancellation claim is made.

This runtime receipt is
`/home/stemxstudio/rove4k-tiny-uci-portfolio-runtime-20261020/results.json`, SHA
`6f26a3c46bff4d9b3dfe531eaac9a43b9a02eff52d5bda1c1bc2ca9624a84b09`.
Family feature/context/PLY qualification also passed, through separate
`proof_bf.py` and `proof_ce.py` receipts. They read the actual archived control
and minimal source files, independently verify the declared transformation and
unchanged whole complement outside go/main, rebind actual artifacts and freeze
the old receipts and their source/harness/image identities. No old stronger
shipping protocol result is reused as proof of the changed shipping policy.

The proof scopes are deliberately different:

- **B:** the optimized/ASan SEE and singular receipt is bound through its actual
  compiled unit. Fifteen new modeled shipping-dispatch/budget/state cases pass.
  A fresh actual-minimal-source optimized core bundle closes the missing B
  context/PLY receipt: retained-TT halfmove scores `[0,916]`, equal board keys
  with different TT context keys, selected EP `e5d6`, correction updates `7→7`,
  and PLY4 completed depth 1 with a legal retained witness and one ply abort.
- **C:** the startup PSQT/SIMD positive receipt is reused through actual exact
  unchanged source bodies and its old DEV/harness/image bindings. It includes
  369,255 board comparisons and 738,510 SIMD calls per optimized/sanitized
  build, plus positive completed-search counters. One new optimized direct
  actual-minimal-source DEV harness passes nine context/PLY checks: full-key
  collision miss, forced actual search misses after halfmove/path changes,
  third visit, halfmove draw, mate precedence, live ply abort, genuine depth-two
  completion-field preservation and EP-best correction exclusion. It creates
  no workers and does not observe concurrent result publication.
- **E:** the exact 21 coefficients, model evaluation/order positive receipt and
  six actual-source optimized/sanitized context/PLY runs are reused through the
  unchanged readable bodies. The old E context fixture proves context-key
  separation; it is not relabeled as a forced production cutoff/miss test.
  No model training or new model-consumer matrix was run.
- **F:** fifteen new modeled policy cases pass. Its exact-source optimized,
  sanitized and PLY4 final receipt is frozen and reused for full-depth MTD(f),
  exact-horizon/coherent TT, retained-depth interruption and real legal witness
  behavior. Its fixed source spelling and encoding decisions remain unchanged.

The 30 B/F modeled cases run real shipping dispatcher/go/wait/clear code with
fixed clock and synthetic worker completion. Each observation explicitly has
`physical_completion_claim=false`; the eight selected whole-file sessions are
the separate actual process/fence/cleanup evidence. New B/C direct core calls
also do not supply a new concurrent publication or scaling proof. All bounded
proof commands are terminal; neither proof helper repeated whole-wrapper
sessions or a canonical portfolio matrix. Independent read-only final reviews
found no concrete blockers in the family adapters/proof helpers.

| Final separate core receipt | SHA-256 |
| --- | --- |
| `/home/stemxstudio/rove4k-tiny-uci-bf-proof-20261020/B/results.json` | `a2965d8f57d36187cb33a7201467271f66f2dae42c8c42b55c518272eea5e951` |
| `/home/stemxstudio/rove4k-tiny-uci-portfolio-ce-proof-20261020/C/results.json` | `2d1efcd44b98062f09d564d8ebbac828d25b9250a441cbfe25c67f053c9bebd3` |
| `/home/stemxstudio/rove4k-tiny-uci-portfolio-ce-proof-20261020/E/results.json` | `f545a25084652d99bfd01a461bb720ecaf75c1b1199c7b4c103dfa9d6868e5d5` |
| `/home/stemxstudio/rove4k-tiny-uci-bf-proof-20261020/F/results.json` | `6fe9500aa943baab38c119926c696e911d590f952f4d4b8deb694f808e51592f` |

| Minimal whole-file identity | SHA-256 |
| --- | --- |
| B 6219 | `01261167253dd89a0e2d88aded2ee493fc0ffaec34cd2322459ddbc515f8aefd` |
| C 5955 | `ec4037167559bf2aeda349af6330d0ef83712305d6c3c6e30f09d7cf70c1af46` |
| E 6031 | `83434699e8ac4746fd99efa4b824c80ecbd5e52f91d0301398a24593eb143124` |
| F 5479 | `485a5aab79761541d8f1ad2a08ad49a7fd4c6d787883992c2fa0cd21cb12adce` |

Reproduce in new absolute directories outside Git on the recorded Linux/GCC
13.3 AVX2 toolchain:

```sh
python3 -B engines/experiments/tiny-uci-portfolio/build.py \
  --out /home/stemxstudio/new-tiny-uci-portfolio
python3 -B engines/experiments/tiny-uci-portfolio/verify.py \
  --portfolio /home/stemxstudio/new-tiny-uci-portfolio/results.json \
  --out /home/stemxstudio/new-tiny-uci-portfolio-runtime
python3 -B engines/experiments/tiny-uci-portfolio/proof_ce.py \
  --family C --build /home/stemxstudio/new-tiny-uci-portfolio/C/build.json \
  --out /home/stemxstudio/new-tiny-uci-portfolio-C-proof
```

`proof_bf.py` exposes the verified Python API rather than a standalone CLI:

```sh
python3 -B - <<'PY'
from pathlib import Path
import importlib.util
path = Path('engines/experiments/tiny-uci-portfolio/proof_bf.py')
spec = importlib.util.spec_from_file_location('portfolio_bf_proof', path)
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)
proof.verify('B', Path('/home/stemxstudio/new-tiny-uci-portfolio/B/build.json'),
             Path('/home/stemxstudio/new-tiny-uci-portfolio-B-proof'))
PY
```

Repeat that API call with F, and the C proof command with E, using fresh output
directories. The original frozen historical controls/receipts remain
required inputs; the helper hard-pins them rather than replacing missing
evidence with a newly chosen candidate.

The default paths identify the exact historical controls. Relocated identical
reports may be supplied with `--controls`; this changes paths, not the literal
hash admission. Executables, frozen recipes, source snapshots and reports
remain outside Git. Earlier stronger protocol evidence stays attached to its
original policy and is not relabeled as this minimal-policy runtime result.
