# One affine-HCE Rust D cost candidate

FIRST-COST completed with no whole-native saving. HQ and scalar controls and
candidates each independently reproduced complete **16,824 B** ELFs. The shared
`value` function fell from 216 B to 150 B; each image's text fell 64 B and read-only
data fell 42 B. The unchanged linker's 4 KiB data alignment absorbed the 106 B
section reduction as padding, so the complete artifact did not shrink. Readable
Rust source rose from 38,625 B to 38,632 B; the identical measurement-only merged
layout rose from 38,641 B to 38,648 B. The candidate is stopped at cost, with no
candidate native execution or further numerical/runtime campaign.

This experiment leaves maintained Tiny Rust D unchanged. It transforms only its
shared `value(p, square)` function and adds one static seven-entry packed
coefficient table. The original safe API, signed piece indexing and rejection of
invalid piece kinds remain. It adds no unsafe access, external dependency, flag,
linker change or identifier/preset sweep.

All valid board consumers use signed pieces `-6..=6` and valid 0x88 board squares.
Their HCE is exactly `sign(p) * (base + C * center + A * advance)`. The independent
precompile proof covers every one of these 832 input pairs, the coefficient
packing, and the actual incremental/capture consumer admission paths. Arbitrary
invalid `usize` square values are not admitted production boards; no larger
domain equivalence is inferred. Safe array checks are retained.

Run on Linux x86-64 with a controlled Rust 1.97 compiler:

```sh
python3 -I -B engines/experiments/tiny-rust-affine/run_cost.py \
  --source-dir "$PWD/engines/compact/tiny-rust-d" \
  --out /absolute/new/external/tiny-rust-affine --rustc rustc
```

The runner freezes original inputs, experiment sources and the exact source
diff. It requires the independent proof before compiling. It then invokes the
unchanged original builder for control/candidate × HQ/scalar, each with an
independent repeat. The original complete ELF pins must reproduce exactly.
Only fixed two workers and TT bits 18 are compared. No engine is executed.

Readable source totals and one identical inline-module serialization are counted
for each representation. Merged serializations are only byte-count measurements;
the native comparison retains the original module layout and exact recipe.
The output reports complete ELF costs, not compressed payloads. A positive size
result alone is not runtime qualification, loader admission or 4KiB eligibility.
