# One C local color-residual SIMD dot

This experiment owns one fixed shipping-only expression change over the qualified
maintained C5344 control. Its 11,284-byte shipping source is read at its literal
SHA from an explicitly named actual output; control source/native/bootstrap/whole
are hash-checked in memory and never copied or compiled. Normal C20, canonical,
DEV, shared helpers and prior experiments remain unchanged.

The candidate replaces only the shared13x64 table, constructor and shipping raw
leaf with a local16xi16 feature vector. Each color contributes six piece counts,
one own-perspective positional residual and one zero lane. Residual is
`sign(v)*value(v,q)-material[abs(v)]`; white coefficients are
`[100,320,330,500,900,0,1,0]` and black coefficients their negatives. Both halves
carry actual evaluation information. Signed256-bit madd and i32 reduction return
the white HCE; the caller still applies side. Material, pawn/rook advance, center
including king coefficient-3, capture ordering and score scale are exact.

A color has at most16 pieces. Each residual contribution has conservative
absolute bound63, so every prefix is within1008 and counts0..16 fit i16. Pair
products/reduction are i32. This preserves the analytic whole-HCE bound29120.
Board, put, copy, EP, castle, promotion, TT/search and the existing core stage
are outside the edit complement. The explanatory readable view retains the exact
old evaluator block under DEV and puts the new leaf only in the shipping branch;
no DEV source is generated or executed here.

`recipe.json` owns the exact old/new fragments, full input/output hashes, three
literal DEV-only witness spans and resource/compiler/transport decisions.
`transform.py` checks paired readable/shipping token roles, operators/literals,
position inverse and the entire untouched byte complement. This is a pinned
literal domain, not generic AST binding or a generalized conditional processor.
Existing keyword/token/source-literal/strict-decode helpers are hash-pinned
ordinary sources, frozen before import. No preprocessor or C AST is run.

On the recorded WSL Ubuntu/GCC13.3 AVX2 environment, using a new absolute output
outside Git:

```sh
python3 -B engines/experiments/tiny-c-feature-dot/build.py --out /external/new/C-dot
```

That step compiles exactly one native from stdin with the unchanged C argv and
private output cwd. It records disassembly and stops if no actual YMM signed
madd exists. An independent read must bind exact native/disassembly hashes and
confirm its actual leaf-return path in `codegen-admission.json` before:

```sh
python3 -B engines/experiments/tiny-c-feature-dot/build.py --out /external/new/C-dot --pack
```

The second step performs no native compile. It encodes once using the unchanged
77-byte prefix and LZMA1 ALONE9-extreme/lc2/lp0/pb0/BT4/64MiB/nice64 and verifies
strict bootstrap/source/compiler-argv recovery. Native is a new full identity;
no metadata exception or equality to the old image is expected. Whole cost
includes all transport/header/bootstrap/source bytes. No flag/name/codec sweep,
volatile workaround or dummy SIMD is admitted.

Physical source preparation is11284->11086 bytes (-198); the715-byte old shipping
fragment becomes517 bytes. The first cost is now terminal: native26,376 bytes (-32) and complete5,245
bytes (-99) against current native26,408/whole5,344. The selected complete file
remains1,149 bytes above4,096. Exactly one native and one compression were run;
there is no independent native/whole reproduction or functional acceptance. The source candidate SHA is
`90a566c5e814cf87dd38f92f40ce8fe7115c4d4d07f75d9ff0981ffaae1fbc28`.
On scalar/128bit-only codegen or whole tie/loss the single candidate stops and
retains failure. Functional qualification and normal promotion require separate
root GO after a strict gain. Engine, games and benchmarks remain0.

Historical startup PSQT saved44 whole bytes and readonly PSQT lost396 against
their then control; cache removal saved8. None is this residual-dot experiment.
No savings or coverage from those runs is added to this candidate. Full source
proposal SHA31691e8be2c1bbdff0bd4ffd92af0558289cf0655207b2684ddd4dc61fbc00ea
records the source-only algebra and alternatives; only this one candidate is run.
Generated C/ELF, assembly, bootstrap, packet, logs and receipts stay outside Git.
## Frozen first-cost result

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C | 11086 | `90a566c5e814cf87dd38f92f40ce8fe7115c4d4d07f75d9ff0981ffaae1fbc28` |
| Native ELF | 26376 | `c32772b3d1bb9ce985bfdecbd31dc4cc5fd06721f03aa6259a4021a4fbb0c788` |
| Complete file | 5245 | `de57a0a21e8ecb2f958207c3e71bcc7d791448340acc103faaea5f1010433933` |

Cost receipt SHA `e7feb08bd534149794d594b28b6f93d783afa2432a16930d3e25f8251e58baeb`.
The actual kernel is inlined in search `P`: feature/value scan and WORD residual
updates feed the YMM load; address0x2839 `vpmaddwd ymm0,ymm0,ymm1`, extract/add/hadd
reduction and0x2855 side multiply feed0x2881 evaluation and0x2890 QS comparison.
Independent read-only source and disassembly reviews are CLEAR. This static
return-path proof is not execution/functional parity or performance evidence.
Strict ALONE bootstrap/source/compiler-argv recovery passed. All cost commands
returned0; no owned compiler or engine remains. Runtime qualification, normal
promotion and any further variant require separate root GO. Normal C5344 and
its frozen20-file closure are unchanged.
