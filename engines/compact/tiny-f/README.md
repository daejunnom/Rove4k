# Optional full-depth MTD(f) F core

This independent F candidate reuses TinyA's admitted generated mailbox board and
persistent startup pool through a strict frozen overlay. It owns its search and
does not modify the canonical A–F implementations, TinyA or shared producers.
The smallest qualified complete source launcher is **5,551 bytes**, including its shell
prefix, compressed Python compiler bootstrap, complete C source and fixed
compiler argv. It remains **1,455 bytes above 4,096**. No 4K entry, playing
strength, target-hardware scaling or portfolio completion follows from this.

The measured toolchain is WSL Ubuntu 24.04.4, x86-64 GCC 13.3.0, glibc 2.39 and
Python 3.12.3. The qualified local profile has two fixed search workers, three
total startup threads and TT bits 18. Training and AWS are outside this work.

## F's actual search contract

- Each iterative depth runs MTD(f) zero-window probes until its local lower and
  upper bounds meet. The starting estimate is the last completed depth's score.
- A completed probe outside the known interval stops the session. An interrupted
  probe or unconverged depth cannot replace the last completed score or move.
- Only a fail-high lower-bound probe may update the root witness. A later
  fail-low probe's move may be legal without attaining the converged value and
  therefore cannot replace that witness. A legal startup fallback exists before
  worker dispatch; terminal/drawn roots can return without a search root move.
- One TT record stores a full 64-bit context key and one bound under the existing
  exclusive acquire/release try-lock. Busy slots are misses or skipped writes.
  The driver's local interval retains both directions independently of the TT.
- A TT cutoff requires the **exact requested horizon**. Positive normal depths
  are distinct; zero is the quiescence domain. Different normal depths and
  normal/QS records cannot cut each other off. Root TT cutoffs remain disabled
  so a nonterminal fail-high produces an actually searched move.
- Incremental integer HCE is the fixed leaf score. Full-depth PVS and QS retain
  history and continuation learning. PVS uses its null-window path during MTD
  probes. Selective LMR is deliberately absent to keep one depth's bound meaning
  unchanged across probes and workers; this differs from TinyA's selective core.
- Correction learns a quiet converged root's residual against raw HCE and
  contributes to actual quiet-move ordering. It changes neither leaf values nor
  searched depth. Captures, promotions and en passant do not train that update.
- Independent workers may change traversal order while sharing the TT and one
  deadline/cancellation flag. Every published converged value has the same
  full-depth score contract. All workers finish before position/history mutation.

TinyA's board contracts remain in force: admitted 16 pieces per colour, bounded
512-move storage with explicit overflow failure, legal EP repetition keys,
halfmove and reversible-history TT context, actual repetition adjudication,
mate precedence, dead material and unfinished ply-cap abortion. The shared
black-box verifier uses its independent Python chess oracle.

## Source structure and measured file cost

The first complete F source launcher measured 5,763 bytes. The optional
`--structure compact` representation measures 5,703 bytes. Its five guarded
operations preserve the same ordered search and mutable state:

1. Discard the already-selected prefix of selection sort instead of restoring
   two cells that will never be read again.
2. Pass the actual moved piece's continuation index directly to the child.
3. Use the nonzero TT payload as the write marker: every stored payload has a
   bound 1–3 at bit 41, while reads pass zero.
4. Use the positive squared-depth learner bonus without a redundant absolute
   value operation.
5. Remove unreachable static HCE clamps under the pinned evaluator/admission
   proof: every piece/square term is at most 910 in absolute value and admission
   preserves at most 32 pieces, hence `abs(HCE)<=29120<MATE-PLY-1`. An incompatible
   ply/mate scale is rejected by the emitted preprocessor guard.

Across 12 positions with retained TT and depths 3/1/2, both representations
produced the same 36 best-move/score/node/TT/learner observations, 3,785 nodes and
state digest `14571315fabad9d2`. These are deterministic single-worker state
comparisons, separate from actual two-worker runtime qualification.

`encode.py` is a further optional representation gate. It fixes the recorded
resource profile in C, tries one predetermined function spelling map, strips
symbol metadata and compacts compiler argv. It accepts these changes only when
the **entire stripped native image** matches its compiler-stdin reference.
Two fixed XZ settings preserve the same decoded bootstrap/C/argv. This gate does
not delete algorithms or alter the signal/wait/cleanup/fd-exec bootstrap.
The compact representation retains `-pthread` and uses the measured compiler
argv `cc -Os -pthread -x c - -o x -s`. Omitting `-std=c11` is qualified only by
the complete native identity gate on the toolchain above. It does not establish
portability to another compiler/header/libc environment.

| Frozen F representation | Complete file |
| --- | ---: |
| First full-depth MTD source | 5,763 B |
| Five guarded source structure changes | 5,703 B |
| Fixed resources/function spellings/argv, default XZ | 5,563 B |
| Same decoded program, XZ `lc2/lp0/pb0`, `9e`, CRC64 | **5,551 B** |

The selected complete file's SHA-256 is
`5b61c8cc14a21de3c8ac446439d4d90ebb8ea909e9e3d3d0161c692fb2ab6082`.
Its actual restored native image is 22,664 bytes, SHA-256
`71b9b39ceb59024fce3fdc87b1a4c22d38af5ef88e89a5f841e96e4ca8ecdb4b`.
This identity is against the separately compiled **stripped** reference; the
unstripped structural native is 26,456 bytes and belongs to another identity
class. Every accepted wrapper and both fixed XZ settings were regenerated
independently with byte-identical results. Source/native sizes from different
identity classes are never substituted for one another.

## Reproduction and qualification

Use a new absolute directory outside the checkout for each command:

```sh
python3 -I -B engines/compact/tiny-f/build.py --structure compact \
  --out /external/tiny-f-build
python3 -I -B engines/compact/tiny-f/encode.py \
  --build /external/tiny-f-build/build.json --out /external/tiny-f-encoding
python3 -I -B engines/compact/tiny-f/qualify.py \
  --build /external/tiny-f-build/build.json \
  --encoding /external/tiny-f-encoding/results.json --out /external/tiny-f-proof
```

`build.py` first freezes all 12 source/producer inputs in `out/recipe`, records
raw-byte and LF-normalized hashes, then reexecutes the frozen producer with
isolated Python imports. The overlay admits only its pinned board/header/runtime
and uses explicit single-unit stitching. Each DEV/original/compact native is
independently compiled twice. Original and compact shipping native bytes must
match after known no-op diagnostic removal. Every complete launcher is generated
twice, including the prefix and compressed compiler recipe.

The actual native and selected structural wrapper pass 23 external verifier
groups: DEV eight, original five, compact five and selected wrapper five. Fixed
startup thread IDs survive every protocol/lifecycle check. `check.py` verifies
12 independent exact minimax scores and attaining witnesses at depths 3/3/1/2
with TT retained, plus feature use, node cancellation and halfmove-sensitive
context. Actual probes include upper-only moves different from the lower
witness; the published witness still attains the independently computed score.

`contract.c` includes the actual frozen DEV translation unit. Matching horizon
and QS records are positive cutoff controls; incompatible horizons and root
records are negative controls. It checks mate-ply normalization, correction's
real ordering effect, held-slot misses/skipped writes, and eight contending
threads performing 160,000 stores plus 160,000 reads. It also interrupts depth
two at node 32 and requires depth one's exact score and witness to survive.
The optimized and ASan/UBSan builds exercise the same contracts; a `PLY=4`
fixture independently requires ply abortion to retain a completed legal witness.

`qualify.py` freezes its test sources, checks the actual selected encoding's
`/proc/PID/exe` hash against the stripped identity class, observes all fixed
startup workers, verifies no compiler child or owned temporary files remain at
UCI-ready, then runs the exact wrapper's shipping checks. Bounded legal games
are correctness evidence and do not establish strength. Software thread startup
on the eight-CPU WSL host does not establish 512-CPU scaling.

The final qualification binds the encoding to the exact build-manifest hash and
compact source hash, rechecks its five frozen encoding inputs and native
identity files, freezes the admitted DEV translation unit, and derives its own
hash-pinned runtime manifests. It does not trust a mutable sibling validation
file. Exceptional startup first sends TERM and waits for the bootstrap's own
forwarding/cleanup path. A temporary Linux subreaper additionally terminates and
reaps owned compiler descendants that outlive their wrapper.

Ten Linux admission/ownership tests pass without skips. They cover cross-build
and cross-source rejection, frozen-input/native drift, unknown inputs/outside
program paths, LF/CRLF admission, and an actual separately-sessioned orphan's
termination and reaping. Optimized and ASan/UBSan contracts both reproduce the
36-case state digest above; the `PLY=4` fixture retains depth one with one
observed ply abort. The final structural run passes 23 verifier groups and 12
independent minimax/witness cases; the exact 5,551-byte encoding separately
passes all five shipping groups with 16-ply bounded selfplay.

Reports and generated files stay outside Git. The final external evidence set
contains `build.json`, `build-recipe/inputs.json`, `encoding.json`,
`qualification.json`, `independent.json`, `blackbox.json`,
`encoded-blackbox.json`, `identity.json`, the frozen producer/test inputs and
the actual `rove4k-F-5551.sh` file. The build recipe input index has SHA-256
`a4ebff26b26d655f4892c67b03c2b800387c0d995737a74b31fd8623169bb331`;
the final qualification report has SHA-256
`62b04e0c5eddaf6d1adcf25b18315dfad43437d20efb6fd0d06b37cde600e173`.
