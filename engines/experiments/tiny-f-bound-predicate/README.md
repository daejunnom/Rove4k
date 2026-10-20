# One exact F TT bound predicate first cost

The only candidate replaces the exact 9,954-byte shipping-F predicate
`(I==1||(I==2&&H>=d)||(I==3&&H<d))` with
`(I==1||((H>=d)==(I==2)))`. The retained outer gate is
`if(f&&I&&J==(a>0?a:0)&&`. Here `I=(F>>41)&3` is bound, H the integer
restored score, d the integer beta parameter, f ply, a depth and J TT depth.
The source is pinned to `00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916`.

All four decoded bounds and both score/beta relations are checked as eight pure
truth rows including the nonzero-bound guard. The two inner expressions differ
for bound 0 below beta; the unchanged outer guard makes that case false in
both. No unconditional inner-expression equivalence is claimed. Exact source
and bootstrap literal reverse replacements are required. No feature, policy,
normal source domain, name, resource, model, compiler or codec change is added.

The actual normal F source/native/whole/bootstrap/build report and frozen
compile_c/source_literal helpers are hash-pinned and reused read-only from
`/home/stemxstudio/rove4k-f-member-normal-20261020`. No control is copied or
compiled. There is one candidate stdin native compile at the original argv and
private cwd, and one fixed ALONE/77-byte-prefix complete package. Full native
equality is observed, never repaired with a metadata exception. Strict decoding
reuses the pinned `tiny-source-codec/decode.py` verifier and CLI LZMA. Its limited
Python AST inspection binds bootstrap compiler argv and stdin literals; it
does not analyze the engine or execute the bootstrap.

The one measured candidate reduced source from 9,954 to 9,945 bytes (-9) and
the complete file from 4,814 to 4,811 bytes (-3). The full native remains
22,672 bytes, but its identity changed from
`757b9a14cd5174dad55754196cce098fd89018a8b0d7adcf08bcddb2e1fc092b` to
`a886eab2d630a8afb2cbdbaa0da2d512bf4d4f8b6febd56fa2e3863db76f9501`.
No metadata exception or native equivalence claim is applied. The candidate
whole SHA-256 is `e5397bbdbde82c17ac88747353a41994a57c6ac1c8daa9c4e1e066e02dcfcc56`.

The eight guarded truth rows, exact source/bootstrap reverse replacements,
unchanged compiler and codec, both existing-verifier strict decode checks,
and independent CLI restoration passed. This is one first-cost observation,
without a repeat-reproduction claim. No new engine/Clang AST campaign, CPP,
engine execution, matrix/game/benchmark, variant, retry, flag/model/alias/codec
sweep or Git/global documentation change is included. Restricted bootstrap
AST literal checks ran twice; bootstrap execution ran zero times. The changed
native has no runtime qualification, performance or promotion claim. Root owns
any downstream decision. All commands have physically ended with exit 0.

Run once in WSL Ubuntu as `stemxstudio`:

```sh
python3 -I -B /mnt/c/Users/강민수/Documents/Codex/rove4k-engines-af-20261020/engines/experiments/tiny-f-bound-predicate/build.py --out /home/stemxstudio/rove4k-tiny-f-bound-predicate-20261020/first-cost
```

The original `cost.json`, candidate source/native/whole/bootstrap, and CLI
restore output remain in that external output directory. Its complete copy,
source3 freeze and final intake receipt are stored outside Git at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-f-bound-predicate-20261020-evidence/`.
The exact existing source/native/whole/bootstrap/build report is reused in
place; no control is copied into this experiment's closure or evidence.
