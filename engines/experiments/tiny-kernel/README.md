# Tiny A direct kernel: failed size experiment

The single direct generation/transition/search kernel is **5,543 bytes**, versus
the exactly reproduced **5,283-byte frozen A control**: a loss of **260 bytes**.
No candidate is promoted. The experiment ends at this one architecture, with
bounded targeted proof rather than another variant or a flag/identifier/codec
search. The candidate remains 1,447 bytes above 4,096.

| Measured bytes | Frozen A control | Direct kernel | Delta |
|---|---:|---:|---:|
| Compact shipping C before fixed spelling | 13,366 | 13,654 | +288 |
| Fixed encoded C sent to compiler | 11,351 | 11,876 | +525 |
| Actual stripped ELF | 22,664 | 26,760 | +4,096 |
| Complete executable shell/XZ/Python/C file | 5,283 | 5,543 | +260 |

The cost is for the complete runnable source package, including the 75-byte
shell launcher, compressed bootstrap, compiler argv and C literal. Source alone
and the restored ELF are separate quantities. An existing shared walk already
unified attacks and generation in the control; that is not a new saving here.
Removing the callback framework used by the separate `tiny-fused` experiment
did not make this direct kernel smaller than the frozen control.

## Architecture and policy

`control.c.in` is this repository's own qualified readable structural winner,
SHA-256 `109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504`.
`transform.py` admits only those exact bytes. It replaces the shipping move
list/generator/make/search path with one recursive function, explicit typed
modes and one direct macro body. Generation holds its facts in locals, applies
a copied child and searches directly; there are no visitor/fact/node callback
objects, function pointers, iterator context or executable-stack trampoline.
Input text is validated and decoded once, then matched and applied once in
the same kernel. DEV-only list/make adapters retain the independent oracle's
entry points; collection is legal-only, whereas the frozen control's collection
is pseudo-legal.

The board remains signed absolute 0x88, with the same incremental HCE, canonical
legal-EP FIDE hash, ordered reversible TT digest, full-key locked TT, mate scale,
all four promotions, castling/EP/king safety, dead-material minimum, halfmove and
third-repetition contracts. Search keeps PVS, QS, private history/continuation,
learned correction in selective reduction, key-stack ownership and unfinished
PLY-cap abort. The original fixed startup pool, parser transaction, clock and
stop/quit/EOF publication paths remain in the control source.

The explicit search policy is different. Before any descendant, one complete
generation sweep snapshots ordinal ranks from history, continuation and the
existing worker jitter. Four subsequent generation sweeps select TT, remaining
tactical moves, quiet rank at least 32, and remaining quiet moves. No per-move
rescan or seen bitmap is used, and no packed move array is passed to a separate
shipping make routine. The threshold is fixed at 32; jitter is only 0..16, so
learning is needed to cross it. Within stages, source files are visited in
`file xor (worker_id & 7)` order. This gives at most eight fresh source patterns,
not 512 distinct orders or a scalability claim. These are at most five
**generation** sweeps; attack/check/EP validation also walks board geometry.
It is not the control's total-score order, and no equal-node/strength claim is
made. `design.md` records the ownership, exclusive-stage and rule contracts.

## Frozen production and identity gates

`campaign.py` freezes all inputs and helpers in an external output directory
before importing or compiling. `spelling.json` carries the already selected 45
identifier substitutions and fixed function/resource spellings. No new spelling
was searched. The historical lexer skips directives, so only owned `K_*` macro
bodies are explicitly exposed to the same quote/comment-aware token replacement
and collision checks; the baseline path remains unchanged.

For each form the producer compares full stripped native bytes across readable
shipping, conditional specialization/lexical compaction, removal of known no-op
diagnostics, and fixed spellings/resource/compiler rendering. Eight COUNT calls
and the exact empty K_OBSERVE/K_COLLECTED definitions/calls are removed only with
that native identity gate. Every native and complete-file generation is repeated
independently. The frozen control additionally must reproduce its declared C,
native, bootstrap and actual 5,283-byte package hashes before the kernel row is
accepted. The measured run supplied the actual prior wrapper and compared bytes.

The one profile is two startup workers, TT bits 18, PLY 128. The encoded compiler
argv is `cc -Os -x c - -o x -s`; resource constants are in the C source. The argv
uses the fixed string-split rendering, and XZ uses CRC64/LZMA2 preset 9 extreme,
lc=2/lp=0/pb=0. This was measured on WSL Ubuntu 24.04.4 LTS x86_64, GCC
13.3.0-6ubuntu2~24.04.1 and glibc 2.39. It does not establish portability to an
unspecified compiler/libc or an event organizer's acceptance of runtime tools.
The source still uses pthreads; omitting the separate `-pthread` link flag is
part of this locally tested modern-glibc domain, not removal of that dependency.

| Identity | SHA-256 |
|---|---|
| Frozen control whole file | `798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645` |
| Kernel whole file | `9c766f856060f7a46494d8a88666cb23ac64fc109658e12fc36f5b19f4b51f52` |
| Kernel stripped native | `d2049419376fb686cc939b0a1b801fa8644b32d25625cc247c875a0df32b8f89` |

## Reproduction and retained evidence

Run from the repository in the measured Linux environment, choosing a new
absolute external output directory:

```sh
python3 -B engines/experiments/tiny-kernel/campaign.py \
  --out /absolute/external/rove4k-tiny-kernel-replay-new
```

The optional `--reference-wrapper /absolute/external/prior-5283-wrapper` adds
actual byte comparison with the pinned prior package; the digest/source/native/
bootstrap gates remain mandatory without it. Every helper is hash-pinned.
The first cost run is retained outside Git at:

```text
/home/stemxstudio/rove4k-tiny-kernel-first-20261020/results.json
/home/stemxstudio/rove4k-tiny-kernel-first-20261020/provenance.json
/home/stemxstudio/rove4k-tiny-kernel-first-20261020/validation-manifest.json
/home/stemxstudio/rove4k-tiny-kernel-rebuild-20261020/reproduction.json
```

The cost run, session 62640, ended with code 0. An unchanged producer replay in a
fresh directory, session 10943, also ended with code 0. All 13 input/helper/
reference bindings matched before replay. All 104 generated paths matched:
90 non-JSON files were byte-identical, including all source, native, bootstrap,
complete files, DEV binaries and frozen inputs; 14 JSON reports matched after
normalizing only the build-output-root string. Both whole hashes remained the
values above. This is one repeated fixed recipe, not another candidate or tuning
campaign. Source/native/whole repetition results are distinct from the targeted
proofs below. No source outside this experiment is changed.

## Targeted actual package execution

`identity.py` freezes the exact producer inputs, whole wrapper, encoded C,
bootstrap, reference native, verifier and independent oracle before launch. One
actual 5,543-byte wrapper execution passed at
`/home/stemxstudio/rove4k-tiny-kernel-identity-20261020/identity.json`:

- Restored C, compiler argv and unchanged bootstrap skeleton matched; the actual
  26,760-byte `/proc/PID/exe` image equalled the declared stripped native bytes.
- The same PID ran the deleted ELF. Three thread IDs observed before the first
  command remained stable through stop. There were no compiler children after
  UCI-ready, and the dedicated temporary directory was absent at that point.
  Cleanup before fd-exec has unchanged source-ordering evidence; there is no
  independent pre-input filesystem sample.
- One startpos `go wtime 300000 btime 300000 winc 0 binc 0` showed work before
  `stop`, then emitted exactly one independently legal `bestmove b1c3`. Ready,
  quiet time and quit produced no duplicate result. Cancellation causality is
  explicitly `unproven`; observing work and a later result is not that proof.
- Quit returned 0 with empty stderr. All observed owned descendants settled,
  the native PID exited, and no forced timeout cleanup was used.

This is one targeted image/startup/clock-stop/quit execution, not the complete
five-group shipping suite, all-position correctness, performance, strength or
4K qualification. Reproduce it independently with:

```sh
python3 -B engines/experiments/tiny-kernel/identity.py \
  --results /absolute/external/rove4k-tiny-kernel-replay-new/results.json \
  --out /absolute/external/rove4k-tiny-kernel-identity-replay-new
```

## Bounded independent contracts after the loss

The frozen candidate then passed one bounded campaign in three profiles:
baseline O2, kernel O2 and kernel ASAN/UBSAN. Each checked 47 normalized position
reports, 999 legal child transitions, 6,016 pointwise attacks, 24 replay plies,
six invalid-promotion transaction rejects and three perfts: startpos depth 3
8,902, kiwipete depth 2 2,039 and rook/EP depth 3 2,812. Both kernel profiles'
47 board/hash/HCE/path/child/attack reports equalled the baseline. The independent
oracle and fixture inputs were frozen before compilation.

Both kernel profiles passed the same 11 white-box contracts, covering utility
mode isolation with stopped set and output aliasing, exclusive legal-stage
coverage, cached ranks, actual learned order, fresh worker order, stop key-stack
pop, draw/mate precedence, unfinished PLY abort, positive search algorithms,
EP correction exclusion and halfmove TT context. Ten root runs produced 98
legal observer records, including all 20 fresh startpos moves and 13 tactical
fixture moves. These are post-legality selected visits before the QS skip;
they do not claim a trace of every raw pseudo attempt or every searched child.

Real descendants made 719 history/continuation updates and changed two live
root ranks, while the root still used its earlier cached ranks. A real quiet
depth-6 cutoff learned history 36 and continuation 36. The history-only witness
uses an untrained continuation row; another same-piece quiet naturally has zero
history and uses continuation rank 36. Both cross the declared threshold and
actually move the quiet to the earlier stage. Fresh workers 0 and 1 also produced
different source orders without training. This is a witness for two workers,
not a diversity or scaling measurement at larger worker counts.

The same bounded run exercised PVS 2,137, QS 2,708, TT hits 495, correction
updates 12 and correction uses 17. The fresh KR position scored 520 while the
halfmove-99 context scored 0; an EP best move was excluded from quiet correction
learning. These establish positive feature execution within this fixture, not
the control's exact node order or a broad algorithm/strength qualification.

The first campaign retained a test-helper compilation failure: fixture function
`ready()` collided with the included engine's `ready` variable. Its baseline
profile passed, while both kernel profiles failed compilation. The corrected
fixture uses `contract_ready`; no engine source was changed. Initial reports,
frozen helpers and compiler logs remain separate from the successful second
campaign. Successful runtime stderr is empty and no timeout cleanup was used;
compiler diagnostics are retained, including inherited/source-format warnings.

```sh
python3 -B engines/experiments/tiny-kernel/kernel-check.py \
  --baseline /absolute/external/rove4k-tiny-kernel-replay-new/baseline/combined.c \
  --kernel /absolute/external/rove4k-tiny-kernel-replay-new/kernel/combined.c \
  --out /absolute/external/rove4k-tiny-kernel-contract-replay-new --asan
```

The authoritative report is
`/home/stemxstudio/rove4k-tiny-kernel-contract-second-20261020/results.json`.
Both first and second campaigns' frozen inputs, logs and transcripts are retained
at `C:/Users/강민수/Documents/Codex/rove4k-tiny-kernel-contract-evidence-20261020/`.
These bounded checks preserve a useful failed architecture result; they do not
promote the candidate into the canonical engine or complete the A-F size goal.

The consolidated Windows evidence is retained at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-kernel-20261020-evidence/`.
Its `summary.json` binds all eleven source files, first-cost/provenance/manifest,
independent reproduction, actual-image proof, both contract reports and their
logs/transcripts by SHA-256. Actual baseline/kernel wrappers, encoded C,
readable combined C and decoded bootstraps are included outside Git. All owned
compiler, wrapper and contract processes are terminal; no further variant,
benchmark or full QA campaign follows this loss.
