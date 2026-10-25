# D reset plus one inverse-BCJ word-access expression

This is one cost-only loader candidate over the exact worker-reset native and
packet pair. Maintained D, its original loader/decoder, native core, resources,
flags and exact-image admission remain unchanged. There is no new codec,
encoder invocation, native compilation, target execution or runtime proof.

The literal transformation in `recipe.json` replaces only the four-byte
inverse-BCJ gather/scatter with constant-size `__builtin_memcpy` into and from
the existing local unsigned `u32`. The original source is exactly recovered by
the inverse replacement. Opcode testing, `i+4 < IMAGE_SIZE`, unsigned modulo
subtraction and skip-five semantics remain unchanged. No unaligned typed
pointer cast, library, header, model, prefix or second transformation is added.

The original loader is 3,093 B, SHA-256
`fba857458166293381a5e403e1ee8ebeeb6171e682f395b0f21524a60670fef4`.
The sole candidate is 2,997 B, SHA-256
`ea574f09aefc0f910a64c683c7052482d3b2e0c52a10f09450233b155674a85c`.

| Form | Maintained whole | Exact reset control | Reset + BCJ candidate | vs reset | vs maintained |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scalar | 6,401 B | 6,387 B | **6,313 B** | −74 B | −88 B |
| HQ | 6,614 B | 6,580 B | **6,506 B** | −74 B | −108 B |

These are actual complete-file costs for the composition, not summed source
or earlier experiment deltas. The unchanged packets are 5,020/5,213 B. Other
whole bytes decreased from 1,367 to **1,293 = 176 ELF/PHDR + 1,117 text**.
Both candidates remain above 4,096 B and have no event-eligibility claim.

The scalar whole SHA-256 is
`66f70074da2270f1d6aa33beb50c1f34038b4bc36e4272d748c1720935fb4a9a`.
The HQ whole SHA-256 is
`7ba4858dcf40c837d107f865e14b82d19ede40570059dcff1ca4bd3012ff7234`.

Actual GCC codegen in both forms uses one inline 32-bit memory ADD at
`0x100004a2`, to `[RAX+0x400001]`, with the unsigned displacement represented
as `-(i+5)`. The four-byte operand does not extend beyond the existing bound.
No `memcpy`, external copy helper or undefined dependency was generated.
Independent static readback bound the exact linked files and build receipt,
checked the opcode mask, scan indices, modulo arithmetic, packet and geometry.
It does not substitute for restored-image or runtime observation.

The H24/base10 decoder, packet header, physical zero4 tail and checked 32 MiB
unmap retain their exact bytes and order. Personality rejection, no-replace
reservation, lower/upper guards, initially zero BSS, RW-to-RX transitions, NX
stack, original-stack entry bridge and syscall failure paths are unchanged
source. The outer ELF remains one RX image plus a nonexecutable-stack header,
with no writable loader globals or dynamic dependency. The scalar native is
8,060 B and HQ 8,448 B; their exact identities and separate mapping/entry
constants are literal recipe inputs, not broader permission for other images.

The producer validates source, native, packet, control linked/whole and layout
pins before either compiler starts. It freezes ordinary inputs outside Git,
performs exactly one CHECKPOINT=0 loader compilation per form, and records
disassembly and ELF geometry. `finish` requires an independent exact codegen
receipt, rehashes frozen ordinary inputs, and reserves a once-only cost receipt
before publishing the stripped wholes. Current output is
`/home/stemxstudio/rove4k-tiny-d-bcj-loads-20261020-v1/`.

```sh
python3 -B engines/experiments/tiny-d-bcj-loads/build.py build \
  --out /absolute/new/external-output
python3 -B engines/experiments/tiny-d-bcj-loads/build.py finish \
  --build /absolute/external-output --review /absolute/independent-codegen.json
```

This experiment intentionally reuses the explicitly pinned external reset
packets and native inputs. It is not a new standalone maintained producer or
an unattended codegen-approval mechanism. Unknown source, image, packet,
geometry or helper behavior is rejected rather than admitted dynamically.

Actual counts: loader compilations **2**, packet copies **2**, native copies
and compilations **0**, encoder/codec execution **0**, C/Clang AST **0**,
CHECKPOINT/audit/fresh/negative/target/runtime/game/benchmark runs **0**.
There was one candidate and no retry, source spelling, flag, layout or model
sweep. No independent repeat or new physical qualification is claimed. Work
stops at cost pending a separate root decision.
