# Separate compact C and E candidates

These are independently executable C and E source candidates over an owned
snapshot of the audited TinyA architecture. The canonical C/Rust portfolio and
TinyA source remain separate. The snapshot comes from commit
`a681ff840c60c7a5f9477782c7fdb126555db3a5`; `core/provenance.json` binds each
actual input byte sequence. Assembly explicitly normalizes CRLF to LF.

Both candidates preserve the 0x88 legal move generator, incremental HCE and
repetition hash, 512-entry proven move-list bound, coherent full-key TT,
PVS/quiescence, history, continuation, correction and fixed persistent startup
workers. Each completed root iteration publishes a legal witness; cancellation
and ply exhaustion preserve the last completed result. Development-only
diagnostics and input modes are removed through the actual C preprocessor.

C evaluates eight mailbox cells at a time using AVX2 gather, integer
material/rank/center arithmetic, sign application and horizontal reduction. The
actual search leaf consumes that returned SIMD score. Its independent scalar
reference calls the original HCE `value(piece, square)` and ignores cached HCE.
The submission recipe fixes `-mavx2`; there is no runtime ISA selector. C keeps
the common history/continuation/tactical move ordering.

E consumes the exact 21 hand-authored **untrained** coefficients from the frozen
model: 16 evaluation and five ordering weights, stored as 42 signed-16 bytes.
It evaluates material, center, pawn advance, doubled/isolated pawns, bishop pair
and tempo, and adds the separate capture/attacker/promotion/center/pawn-advance
model prediction to actual move priority. En passant counts its captured pawn.
Raw evaluation remains signed-32 and is clamped to the existing model's
`[-20000,20000]` search scale. Correction residuals and LMR eligibility use that
same evaluation scale; worker-local correction never changes TT leaf meaning.
The original incremental HCE and hash remain maintained through every move.

The model identity is
`4ff88c9f4dde9d51f69e32e8c9f57ce555361ea9d22086b41e8873bc06c72164` for canonical
JSON and `eff32c8c6fe02961cb2adfd923897393bfc3448f3650116ece358cc68c79ddc6`
for the exact 21 little-endian signed-16 values. Conservative bounds remain
56,224 for raw evaluation and 24,940 for ordering. The generator rejects model,
feature, provenance and fixed overlay-shape drift. No training or quantization
is performed.

The first complete-file checkpoint is:

| Candidate | Complete source stream | Complete native ZIP | Compact C source | Shipping native ELF |
| --- | ---: | ---: | ---: | ---: |
| C, actual AVX2 HCE | 6,059 B | 9,915 B | 14,710 B | 26,464 B |
| E, exact model evaluation and ordering | 6,107 B | 10,164 B | 14,934 B | 26,504 B |

The source streams include the 75-byte shell prefix plus a shared XZ-compressed
Python bootstrap, C source and complete fixed compiler command. The native
ZIP includes its decoder and executable. All bytes count. These candidates
**exceed 4,096 bytes** and have no tournament eligibility claim. They make the
candidate-specific source costs concrete; they do not complete the size gate.

Run on Linux with Python 3 and GCC, using new absolute output directories
outside the checkout:

```sh
python3 -I -B engines/compact/tiny-ce/test_generate.py
python3 -I -B engines/compact/tiny-ce/build.py --variant C --out /absolute/new/C
python3 -I -B engines/compact/tiny-ce/build.py --variant E --out /absolute/new/E
python3 -I -B engines/compact/tiny-ce/check.py --build /absolute/new/C/build.json --out /absolute/new/C-consumer
python3 -I -B engines/compact/tiny-ce/check.py --build /absolute/new/E/build.json --out /absolute/new/E-consumer
python3 -I -B engines/compact/tiny-ce/restoration.py --build /absolute/new/C/build.json --out /absolute/new/C-restoration
python3 -I -B engines/compact/tiny-ce/restoration.py --build /absolute/new/E/build.json --out /absolute/new/E-restoration
python3 -I -B engines/compact/tiny-ce/blackbox.py --build /absolute/new/C/build.json --build /absolute/new/E/build.json --out /absolute/new/blackbox
```

Each producer freezes the core, model, overlay, compiler flags and shared helper
bytes into its external `recipe/` tree before importing them. It compiles each
DEV/original/compact form twice, requires original and compact native byte
identity, compiles and reproduces the separate stdin restoration recipe, and
reproduces every complete source/native wrapper. `build.json` records hashes,
full file sizes, expected restored native bytes and the selected artifacts.
The saved `recipe/engines/compact/tiny-ce/build.py` can replay the build without
reading the mutable checkout.

The current C kernel's optimized and ASAN/UBSAN scalar-parity contracts pass
369,255 board positions and 738,510 SIMD evaluations per build, including every
piece/square, poisoned padding and cached HCE, reversed side to move, special
moves and random reachable positions. Compile `c_contract.c` with `-DDEV=1
-mavx2 -I engines/compact/tiny-ce/core -I engines/compact/tiny-ce` to reproduce.
`check.py` additionally verifies that the actual completed C search consumes
SIMD leaves and that its production executable contains the AVX2 arithmetic.

E's production-source consumer passes the existing hand-computed evaluation,
capture, promotion and en-passant fixtures. A harness includes the actual
producer's combined DEV source and checks 2,007 arbitrary and dense promoted
positions against the independent frozen scalar oracle in optimized and
ASAN/UBSAN builds. It covers raw/clamped evaluation, ordering and poisoned cached
HCE. A real completed depth-four search reports positive leaf, model ordering,
PVS/QS, history, continuation and correction activity.

The shared frozen black-box validator passes 56 groups across both candidates'
DEV, original, compact, selected source and selected native artifacts. The quick
suite exercises rules/state/search plus shipping protocol, legal short play,
stop/restart and active quit/EOF. The deeper unchanged-board oracle proof is
inherited only through identical frozen board/header bytes. Separate restoration
checks compare complete `/proc/<pid>/exe` bytes, require three stable startup
threads for the default two-worker profile, verify cleanup before exec and
normal shutdown. These are local WSL functional checks, with no Elo or target
512-hardware-thread performance claim.

Remaining work includes further source/representation co-design to reach the
size gate, larger resource profiles for these optional candidates if selected,
and any desired C+E composition. No combined C+E candidate is silently selected.
