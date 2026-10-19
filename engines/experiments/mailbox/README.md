# C A mailbox and update comparison

This is a controlled, optional source experiment. It does not change the
canonical engine or the independent compact A architecture. It implements the
plan's two A structure axes as four actual runtime engines:

| Layout | Recursive update |
|---|---|
| 0x88, 128 stored squares | Copy and make |
| 0x88, 128 stored squares | Make and unmake |
| 10×12, 120 stored squares | Copy and make |
| 10×12, 120 stored squares | Make and unmake |

`generate.py` consumes one frozen canonical C source set. Every cell retains A's
incremental HCE and keys, PVS, quiescence, TT, history, continuation, correction,
selective reductions and fixed loose worker pool. It is strictly an A recipe;
the variant-specific B–F branches are not geometry-converted or supported.
Compiler, TT size, worker count and parallel policy are identical across a
comparison. Source bytes are captured once before generating the four cells.

The 10×12 path changes stored square indices, pawn/ray/knight strides, king and
castling locations, board traversal, FEN and UCI conversion, and the history
table dimensions. Its validity test uses rank/file arithmetic over the 120-cell
mailbox. This is one explicit 10×12 implementation, not a claim about the best
possible sentinel, square-table or assembly implementation. Physical squares
are normalized only in the random-key and worker tie-breaking domains, keeping
hash/TT collisions and ordering controlled. The engine does not convert each
recursive position through a 0x88 adapter.

The unmake path changes the actual `search()` and `qsearch()` recursive updates.
Its 64-byte `Undo` records at most four changed squares and reversible metadata.
Reversing `put()` restores bitboards, occupancy, pawn hash, material and HCE;
saved metadata restores clocks, rights, EP, king squares and position key.
Illegal moves after king-safety checks are rolled back. Search restores the
board and active history length before processing a cancellation return.
Each loose worker receives a private mutable root. Full-board copy remains at
the public immutable `make_move()` boundary and in nonrecursive witnesses;
it is absent from the changed recursive move application.

## Reproduce on Linux

Outputs must use new absolute directories outside the checkout. Run from the
repository root with Python 3 and a C11 GCC-compatible compiler:

```sh
python3 engines/experiments/mailbox/build.py \
  --out /absolute/external/mailbox-build --no-pack
python3 engines/experiments/mailbox/check.py \
  --build /absolute/external/mailbox-build/build.json \
  --out /absolute/external/mailbox-check
python3 engines/experiments/mailbox/measure.py \
  --build /absolute/external/mailbox-build/build.json \
  --out /absolute/external/mailbox-packages
python3 engines/experiments/mailbox/study.py \
  --build /absolute/external/mailbox-build/build.json \
  --out /absolute/external/mailbox-resources
python3 engines/experiments/mailbox/study.py \
  --build /absolute/external/mailbox-build/build.json \
  --out /absolute/external/mailbox-smp --workers 2 --oracle
```

`--source-root` selects an earlier frozen directory containing the six canonical
inputs. The build emits a copy in `canonical-input/`, source and executable
hashes, exact commands and compiler identity. Original and compact native forms
are compiled twice and compared as actual bytes. The package measurement
checks source hashes before generating all six source/native codec/transport
forms, generates every complete wrapper twice, and executes the actual minimum
source and minimum native wrapper for every cell. Its size counts include the
launcher, decoder, archive metadata and payload.

## Recorded local checkpoint

WSL Ubuntu 24.04, GCC 13.3, one search worker, TT bits 16, canonical inputs whose
hashes are in the external build record. This checkpoint has **no 4,096-byte
eligible artifact**.

| Layout / update | Complete source minimum | Complete native minimum | Stripped ELF | Board | Worker |
|---|---:|---:|---:|---:|---:|
| 0x88 / copy | 13,035 B | 16,000 B | 43,144 B | 696 B | 211,936 B |
| 0x88 / unmake | 13,378 B | 16,406 B | 43,144 B | 696 B | 211,936 B |
| 10×12 / copy | 13,053 B | 16,416 B | 43,144 B | 664 B | 196,064 B |
| 10×12 / unmake | 13,396 B | 16,792 B | 43,144 B | 664 B | 196,064 B |

All selected complete minima use ZIP-LZMA. The 10×12 mailbox reduces the
declared board by 32 bytes and the per-worker history/state structure by 15,872
bytes, while adding 18 bytes to this complete source package. Unmake replaces
the 696/664-byte recursive child board with a 64-byte undo record but adds 343
bytes to the complete source package. ELF file alignment produces equal
stripped file sizes; the compressed native costs and actual hashes differ.
These are measured costs of this recipe, not conclusions about all possible
mailbox implementations.

Verification completed:

- Eight optimized/ASAN+UBSAN restoration runs: each visits 137,749 positions,
  137,742 legal edges and 4,139 special moves, with the same normalized
  key/HCE checksum `eccc8bcc517354e3`. The undo cells compare every legal child
  against the retained independent canonical copy-make update and compare the
  exact parent bytes after legal and illegal attempts.
- Ten real recursive node-budget cancellations per run restore the board,
  active history length and root key. Castling, EP, pinned EP, promotion,
  captures, rights, half/fullmove clocks and incremental board invariants are
  exercised by the fixtures.
- Independent UCI oracle on four development and eight shipping/compact
  binaries: **72/72 groups pass**, covering known perft totals, legal replay,
  hash/state/evaluation, mates, clocks, lifecycle, bounded selfplay and quit/EOF.
- Six completed depth-4 searches in every single-worker cell agree exactly on
  state, score/PV, legal bestmove, completed depth and node count. A separate
  24-search resource run reproduces that comparison.
- Eight selected complete wrappers: **40/40 shipping groups pass**, including
  actual source restoration/compilation and native restoration/execution.
- Two-worker builds use the same frozen source and only change the explicit
  worker definition. Their 24 completed searches and **32/32 independent UCI
  groups pass**. Startup has three threads and preserves the same task IDs
  through the lifecycle checks.

Observed single-worker resident high-water marks in the separate local
resource run were 2,560–2,688 KiB; two-worker marks were 2,688–2,816 KiB.
Page granularity and process/runtime overhead exceed the structural differences
in these small profiles, so this is not evidence of an RSS or speed advantage.
Elapsed search samples are preserved, but the host was shared with other work;
no fair NPS, strength, rating or many-core scalability claim is made.

External records on the WSL host:

- `/home/stemxstudio/rove4k-mailbox-20261020-v1/build.json`
- `/home/stemxstudio/rove4k-mailbox-20261020-check-v2/results.json`
- `/home/stemxstudio/rove4k-mailbox-20261020-pack-v1/measurements.json`
- `/home/stemxstudio/rove4k-mailbox-20261020-study-v1/results.json`
- `/home/stemxstudio/rove4k-mailbox-20261020-study-smp-v1/results.json`

Generated readable source copies, frozen inputs, binaries, package candidates
and transcripts remain outside Git. Training, external engines and AWS were
not used.
