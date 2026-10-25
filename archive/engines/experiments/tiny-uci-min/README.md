# One minimal shipping UCI policy for Tiny A

This optional experiment changes the shipping protocol policy on the exact
5,283-byte Tiny A control. It does not change the canonical engine, shared
validator, board, search, TT representation, workers, compiler settings, fixed
identifier mapping, bootstrap or compression settings. It is an explicit
protocol policy change, not semantic-preserving source compression. No external
engine source is copied; the repository's MIT license applies.

The complete file is **5,223 bytes**, a **60-byte reduction**. It remains
**1,127 bytes above 4,096** and is not a size-eligible submission. No playing
strength, fair throughput, many-core or other-platform claim follows from this
measurement.

## Declared policy

The primary [TCEC 4k rules, sections 7.9–7.11](https://wiki.chessdom.org/Rules#TCEC_4k_rules)
require `uci`/`uciok`, `isready`/`readyok`, `position startpos moves`, `go`
(bare or clocks/increments), `bestmove` and `quit`. They distinguish accepting
other commands without error from implementing their general UCI behavior;
`id`, `info`, options and new-game behavior are optional. This experiment uses
that distinction only for the following one shipping policy:

- `uci` prints only `uciok`; the optional identification line is omitted.
- `stop` and `ucinewgame` are consumed by the input loop like unknown commands.
  They do not cancel, wait, clear the TT or reset a live search.
- Bare `go` has a default **1,000 ms** search budget. Shipping has no explicit
  `infinite` extension: the unknown token is ignored, so `go infinite` has the
  same finite default when no own-side clock is present.
- An own-side clock keeps the existing calculation:
  `clock/30 + min(increment,86400000)*3/4`, capped to `clock/5`, then at least
  1 ms and at most 86,400,000 ms. Zero or invalid own-side numbers retain the
  existing minimum-budget behavior. Opposite-side clocks alone leave the
  default budget. Existing token admission is otherwise unchanged.
- A following `go` or `position`, `quit`, and EOF still publish internal
  cancellation and wait for every worker to finish before state reuse or
  release. The last worker publishes the result while holding the existing
  mutex before waking the waiter. Startup still initializes every TT atomic
  lock and creates the same persistent two-worker pool plus command thread.

The 1,000 ms budget is not a strict wall-clock completion guarantee. Workers
check deadlines every 256 claimed nodes, with ordinary scheduling delay, and
the legal fallback is prepared before publishing the new search. This finite
policy supplies the required bare `go`; simply deleting the `infinite` token
while leaving `UINT64_MAX` would not have done so.

DEV retains its original identification, explicit stop, TT-clearing new game,
infinite, depth, nodes, movetime and diagnostics. The actual preprocessed,
minified DEV source and its native ELF are byte-identical between control and
candidate. Retaining the TT across new games can affect time-limited choices;
no search-result or playing-strength equivalence is claimed.

## Fixed inputs and actual cost

`build.py` admits exact hashes for the earlier external A recipe at
`/home/stemxstudio/rove4k-tiny-protocol-20261020/recipe`. That recipe contains the
readable source, already selected spelling decisions, the selected encoding
case and the exact 5,283-byte wrapper. The transform operates on the readable
source; generated C is not edited directly. Both forms use the same accepted
identifier decisions and `cc -Os -x c - -o x -s`. Packaging keeps the same
75-byte shell prefix and Python compiler/signal/cleanup/fd-exec bootstrap,
replacing only its C source argument. XZ uses the already selected LZMA2
preset 9 extreme, `lc=2`, `lp=0`, `pb=0`, CRC64. There is no setting or name
sweep here.

| Actual form | Exact control | Minimal policy | Difference |
| --- | ---: | ---: | ---: |
| Compact C source | 11,351 B | 11,192 B | -159 B |
| Stripped native ELF | 22,664 B | 22,664 B | 0 B; program bytes differ |
| Complete source launcher | 5,283 B | 5,223 B | **-60 B** |
| Compressed bootstrap and source, included above | 5,208 B | 5,148 B | -60 B |

Actual independent generation, native compilation and whole-file packaging
were each performed twice per form, requiring identical bytes. The control
also had to reproduce the earlier qualified source, native and wrapper
hashes exactly before a policy result was accepted. Source restoration was
decoded from the actual executable bootstrap expression and matched exactly.
The environment is WSL Ubuntu, x86-64 Linux, GCC 13.3.0, binutils 2.42, Python
3.12.3 and xz 5.4.5; the report records the actual full tool version lines.

| Identity | Control SHA-256 | Minimal policy SHA-256 |
| --- | --- | --- |
| Readable source | `109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504` | `38d6c829a4d98a172b01c945a20e091bd529a5998174896dbf0ad2dbc01a0a7b` |
| Compact source | `49aa4d484458d0e4f6d14850fb2260a7007ea40f588003131d43a516d06a592e` | `b70dce2bd28834f6218b72e255ee5689028ab187be91bf2df661c6c48af55092` |
| Native ELF | `0454dfde844f29a962dc2b79b0ff6485dc461cb836d8103a57e811030e8578d4` | `60797c218437055bdc56a46e9ff37d9007ba39e547bccccfa36d8f5acb9cb430` |
| Complete launcher | `798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645` | `fbb416160e98beb8f10cc5fec6b3792f4591055626344dcbe31cb50ffce41ee9` |

The final producer root is
`/home/stemxstudio/rove4k-tiny-uci-min-20261020-v4`.
Its `recipe/` freezes all actual source/tool input bytes; `build.json` records
commands, hashes, declared resources, reproduction and source restoration.
The first two failed output directories remain separate. The first DEV
verification compile omitted fixed resource macros; the second detected a
changed DEV declaration order. Restoring the original declaration and adding
the compile macros fixed these harness/transform issues. Neither failed report
is relabeled as success, and neither is the final tested artifact. The successful
v3 measurement is also preserved; v4 adds an explicit DEV native-byte equality
assertion after independent review and reproduces all the same artifact hashes.

## Qualification boundary

`verify.py` supplies direct checks for this declared shipping policy. It does
not loosen the common strong stop/newgame/infinite validator. Earlier stronger
control results remain evidence for the earlier behavior, not automatically
for this policy. A result received after a control is not by itself causal
proof that the control cancelled the search.

The direct runtime gate is complete, with **8/8 shipping process runs** across
control/candidate, native/complete launcher, and active quit/EOF. Each actual
executable was SHA-pinned. At startup, the launcher PID was the restored native
PID, `/proc/PID/exe` had the expected full native SHA, exactly three startup
TIDs existed, only descriptors 0/1/2 remained, no compiler/helper child remained
and the private working/temporary directories were empty. Policy sessions
repeated the identity/resource checks after the transaction fences and required
the same persistent TIDs. Active quit/EOF settled exactly one outstanding epoch;
the process became absent and output readers joined. No residual files or
stderr were observed. The frozen independent oracle checked actual bestmoves.
Its 12 independent fixed perft self-checks also passed.

Required white/black clock and increment cases, field order, zero-clock
fallbacks, `isready`, consume-only commands and next-go/position fences passed.
The four minimal-policy bare/`infinite` observations returned in approximately
1.0003–1.0018 seconds on this machine. These are bounded completion observations,
not a fair timing comparison or strict real-time guarantee. Worker CPU progress
was observed before and after shipping's ignored controls. Receipt ordering
alone still has `stop_causal_link=unproven`; the separate instrumented dispatch
check establishes what those input branches actually do.

**30/30 modeled cases** compiled the actual readable shipping translation units
with fixed-clock and no-thread environmental stubs. They exercised the real
main dispatcher, wait, clear, go and replay. TT sentinel bytes, complete history,
root, workers, epoch, deadline and stop/pending state remained unchanged across
shipping stop/newgame; the control kept its original stronger behavior. Exact
bare-go and clock arithmetic, huge admitted numbers, the day cap, both colors,
next-go/position settlement and quit/EOF joins passed. Those environmental
stubs prove dispatch/arithmetic/state order, **not physical worker completion**;
the eight real process runs provide that distinct evidence. The unchanged DEV
ELF separately passed identification, live infinite search, explicit stop,
newgame, depth and physical shutdown controls.

The immutable runtime receipt is
`/home/stemxstudio/rove4k-tiny-uci-min-verify-20261020/results.json`, SHA-256
`5d298cc4e7ad787a5503c46a2d33a8e338689f678d64fc8bc0a086ef6ed077d3`.
It binds the producer `build.json` SHA
`fa4587ce3af610e04edff071e5976b2fdb638f2c163701d21dbe61de34c907f2`
and freezes the unchanged process helper and chess oracle. The new verifier
source was read independently after implementation; no extra blockers were
found. The producer/transform also received an independent read-only review;
that review did not claim to execute the measured files.

Reproduce into a **new absolute external directory**:

```sh
python3 -B engines/experiments/tiny-uci-min/build.py \
  --control-recipe /home/stemxstudio/rove4k-tiny-protocol-20261020/recipe \
  --out /home/stemxstudio/rove4k-tiny-uci-min-new
python3 -B engines/experiments/tiny-uci-min/verify.py \
  --build /home/stemxstudio/rove4k-tiny-uci-min-new/build.json \
  --out /home/stemxstudio/rove4k-tiny-uci-min-new-verification
```

Generated executables, recipes, JSON evidence and compiler output belong
outside Git. Only this readable transform, producer, policy-specific verifier
and documentation are source contributions.
