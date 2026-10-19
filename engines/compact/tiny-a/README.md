# Optional source-first A candidate

This is a separate architecture experiment. The canonical C and Rust A engines
remain authoritative portfolio implementations. This candidate keeps A's mailbox,
incremental HCE/hash, PVS, quiescence, shared TT, history, continuation, correction
and fixed startup SMP in a smaller source design. It does not implement B–F or
replace the portfolio's other parallel policies.

The latest audited complete source launcher measures **5,671 bytes**, including
its shell prefix and the shared compressed Python bootstrap, C source and fixed
compiler command. This is
**not a 4KiB eligible artifact**. Use each build's source hashes and full
artifact bytes for comparisons. The selected stream contains 5,596 bytes of
shared XZ data and a 75-byte shell prefix. The Python bootstrap is inside those
5,596 bytes; the prefix is not the complete restoration overhead. The earlier
6,054-byte ZIP artifact remains a separate verified snapshot.
It preserves every A feature listed above; it is not selected by deleting a
candidate's required algorithm.

## Contracts

- A 176-byte copy-make state uses signed `int8_t[128]` and 0x88 squares, with a1
  at zero. Positive P/N/B/R/Q/K codes are 1 through 6. White moves with `s=1`.
- `gen` emits pseudo-legal moves. Internal `make` requires membership in that
  generated list and then checks king safety. Public text is matched against the
  generated list before applying it.
- Start and DEV FEN admission preserve at most 16 pieces per colour. A piece
  has at most 27 pseudo moves (pawn promotions at most 12; king plus castling at
  most 10), so `16*27=432<512` bounds the fixed list. An unexpected overflow
  aborts rather than dropping moves. DEV FEN rejects a 17th piece transactionally.
- Every square update changes HCE and deterministic piece-square keys together.
  The repetition key includes side, castling rights and only legally capturable
  en passant. It excludes the halfmove clock and move history.
- The TT key additionally contains the halfmove clock and an ordered reversible
  path digest. Threefold adjudication compares actual repetition keys in game
  and search history. Checkmate takes precedence at the 50-move boundary.
- Dead-material detection recognizes bare kings, one minor in total, and bishops
  confined to one square colour. KNN/K, KN/KN and opposite-colour bishops do not
  cause automatic draw. Reaching the nonterminal ply cap aborts the unfinished
  iteration, retaining the last completed legal root witness.
- TT readers and writers try to acquire each slot's atomic flag. Contention is a
  miss; key and payload are accessed only while holding the slot. Workers keep
  independent mutable heuristics and deterministic different move tie orders.
- PVS iterations publish only after completion. On cancellation, the last
  completed legal root witness survives; before any completed iteration, the
  runtime returns a legal move generated before dispatch.
- Leaves use fixed integer incremental HCE. Correction learns the discrepancy
  against raw HCE from exact quiet best moves, excluding en passant. Correction
  affects actual late-move reduction eligibility; reduced fail-high probes are
  researched at full depth. It never changes the shared TT's leaf-score scale.
- Exactly `WORKERS` search threads are created before accepting UCI input. Main
  owns stdin, so the total is `WORKERS+1`. Startup failure exits explicitly.
  All workers complete before main can mutate position/history or publish the
  next job. The last worker prints exactly one final result per accepted `go`.
- The POSIX mutex/condition-variable pool is the baseline. `main-futex.c.in`
  compares a Linux private-futex implementation with acquire/release publication,
  completion only after final output, and persistent thread lifetimes.
- Input is limited to 32,767 payload bytes. Oversized or NUL-containing lines are
  drained completely. Position replay commits only after all moves are legal.
  Invalid decimal clocks become an immediate bounded budget; zero time gets 1ms.
- Shipping includes no FEN, perft, diagnostics, resource options or node/depth
  controls. Their development implementations and counters are removed by the
  actual C preprocessor before lexical source compaction.

## Reproduce outside the checkout

On Linux, with Python 3 and a C11 compiler:

```sh
python3 -I -B engines/compact/tiny-a/build.py --out /absolute/new/tiny-a \
  --board generated --single-unit --strip-dev-counters
python3 engines/tests/verify.py --manifest /absolute/new/tiny-a/validation-manifest.json \
  --out /absolute/new/tiny-a-verification --startup-threads 3
python3 engines/compact/tiny-a/check.py --engine /absolute/new/tiny-a/dev/x \
  --out /absolute/new/tiny-a-algorithms.json
```

`--runtime futex` and `--board rays|forward` compare optional source structures. The
default preserves the independently checked original mailbox algorithms. `rays`
shares one direction kernel between generation and reverse attack queries; its
HCE expression is algebraically identical to the baseline. `forward` shares one
forward walker across pieces. `generated` additionally uses the existing
generated-move precondition to remove duplicate endpoint/promotion/EP/castle
checks; it retains king-capture prohibition and post-move own-king safety. Its
proof is next to `make`, and DEV verifies castle rights imply their home pieces.
`--single-unit` moves global and clock definitions before callers, removing ten
extern declarations and eleven redundant prototypes from the packaged C source.
`--strip-dev-counters` removes eight known no-op shipping diagnostics and accepts
the result only if original and compact complete native bytes are identical.
DEV counters remain active. Local producer modules load by explicit owned paths,
so isolated `python3 -I` invocation does not require external helper modules.

The build records exact input hashes, compiler version/arguments, original and
specialized source bytes, complete native and wrapper bytes, and independent
second-generation byte equality. No output goes inside the checkout. The common
black-box verifier imports an independent Python chess oracle, not this engine.
Each native manifest entry pins its actual executable hash. With packaging,
`validation-manifest.json` adds the smallest complete wrapper to the three native
entries, including its hash, fixed threads, working directory and 60s startup
limit. A `--no-pack` build emits only its three actual native entries.
`check.py` additionally requires observed PVS/QS/TT/history/continuation/correction
branches and tests different halfmove contexts without clearing the shared TT.
It also checks ten positive/negative insufficient-material positions and an EP
capture's correction eligibility. `--cap-engine` accepts a separate DEV build
compiled with `-DPLY=4`, and requires an observed ply abort while depth one's
completed legal witness survives the interrupted depth-two search.

The audited selected snapshot passes 23 common external verifier groups: eight
development groups, five each for original/compact shipping natives, and five for
the actual selected 5,671-byte complete wrapper. The byte-identity recipe also
repeats every native compile and every full wrapper generation independently.
The specialized wrapper's separate three-codec tests verify actual compiler
stdin, argv/environment/I/O/status preservation, no residual wrapper process or
temporary files, missing-compiler cleanup, and SIGTERM forwarding/wait/cleanup
for a compiler with a child process.

The stream producer separately verifies all three `xz`/`gzip`/`bzip2` codecs,
33 byte-preservation cases and the same process/cleanup contracts. It places
Python and C in one compressed stream, avoiding separate ZIP member headers and
allowing shared compression. Its external programs are explicitly recorded.

The following matched local profiles use two workers, TT bits 18, the capacity
admission above and the same compiler/packaging recipe. Sizes are complete files:

| Source structure | Shipping C | Best ZIP | Best stream |
| --- | ---: | ---: | ---: |
| Original walker, declared modules | 14,794 | 6,058 | 5,919 |
| Shared forward walker | 14,393 | 6,031 | 5,883 |
| Generated-move preconditions | 14,150 | 5,969 | 5,823 |
| Definitions before callers | 13,735 | 5,888 | 5,743 |
| Remove known no-op shipping diagnostics | 13,541 | 5,816 | **5,671** |

These are source-structure/cost comparisons. The independent correctness gates
pass; the table does not establish playing strength or parallel speedup.

Earlier controlled structure comparisons found the shared direction walker
increased the whole file from 5,877 to 5,904 bytes; combining it with futex pool
control increased it to 6,026 bytes. These measurements predate the dead-material,
ply-cap and correction audit fixes. Neither optional structure is the selected
default; smaller raw source alone was insufficient to justify selection.

The local two-worker profile checks behavior on an eight-logical-CPU WSL host.
Compile `--workers 255`, `508`, or `511` for fixed total thread profiles of 256,
509, or 512; local smokes do not prove those profiles' scalability or tournament
eligibility. No rating or strength claim follows from bounded legal games.
