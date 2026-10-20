# Maintained minimal C entry

The selected complete shipping file is **5,245 bytes**, down 99 from 5,344 and
**1,149 bytes above 4,096**. Ordinary pinned source inputs regenerate its C,
native ELF, bootstrap and wrapper. Historical reports and artifacts are
qualification metadata, never normal generation inputs.

`engine.c` remains the readable canonical program with the previous PSQT/gather
reference and DEV diagnostics. The shipping-only source stages produce the
qualified color-residual SIMD representation described below. DEV source and
full native retain their previous literal identities; DEV gather equality is
not used as proof that the new shipping kernel executed.

On the recorded Linux x86-64 Ubuntu 24.04.4/GCC 13.3/binutils 2.42/glibc 2.39/
Python 3.12.3/xz-lzma 5.4.5 AVX2 environment:

```sh
python3 -B engines/compact/tiny-entry-c/build.py --out /absolute/new/C-build --dev
python3 -B engines/compact/tiny-entry-c/verify.py --build /absolute/C-build --out /absolute/new/C-runtime
```

Output directories must be new, absolute and outside Git. A builder call
regenerates shipping twice and optional DEV twice. The unchanged verifier runs
one quit and one EOF wrapper, each performing its ordinary source restoration
and compilation. The unchanged `fresh.py` can separately archive the 21-file
closure and execute two extractions. No fresh/archive-execution check is implied
by a direct builder call, and fresh is not run for this promotion.

The fixed local profile remains two search workers plus one controller, TT 18
and PLY 128. Compiler arguments, bootstrap template and 77-byte launcher remain:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -mavx2 -DDEV=0 -x c - -o x
```

Existing specialize/minify/diagnostic stripping, alpha, static/local scope and
`shipping_core.py` stay unchanged. The core stage still requires and produces
its exact pre-SIMD source; its nonzero TT sentinel, consumed sort-prefix
omission, inactive outer clamp removal and zero-order removal remain intact.
New `shipping_simd.py` runs immediately **after core**, only in shipping mode.
It owns exact canonical15999279... and post-core68ad43de... input domains,
paired readable/shipping fragments, position inverse, complete untouched byte
complement and final90a566c5... source identity. Three known DEV-only literal
witness spans explain the active readable correspondence; this is not a generic
preprocessor or AST/name allocator. The explanatory readable block preserves
the original DEV body. Canonical/alpha/scope/core guards are not broadened.

The new leaf has a local 16xi16 vector: per color, six piece counts, one own-side
positional residual and one zero. Residual is
`sign(piece)*value(piece,square)-material[kind]`. White coefficients are
`[100,320,330,500,900,0,1,0]`, black coefficients their negatives. Actual AVX2
signed16 madd and i32 reduction return exactly the scalar white HCE, then the
unchanged caller multiplies by side. The king center coefficient-3, pawn/rook
advance and all other original terms remain. Each color's feature prefix is
bounded by 1008 and counts by 16; the analytic total HCE bound 29120 remains.

The shipping table and constructor are removed, while `value()` remains for
capture ordering and the scalar reference. Board, put, make, EP, castle,
promotion, hash/context, TT, search and lifecycle lie in the preserved byte
complement. There is no new Board cache or shared mutable evaluator state.
Normal generation needs no experiment source, receipt, generated artifact,
Clang, external model or network. DEV bypasses every shipping-only stage and
requires its SIMD metadata to remain None.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C | 11,086 | `90a566c5e814cf87dd38f92f40ce8fe7115c4d4d07f75d9ff0981ffaae1fbc28` |
| Native ELF | 26,376 | `c32772b3d1bb9ce985bfdecbd31dc4cc5fd06721f03aa6259a4021a4fbb0c788` |
| Complete file | 5,245 | `de57a0a21e8ecb2f958207c3e71bcc7d791448340acc103faaea5f1010433933` |
| Bootstrap | 12,161 | `275e40359feee02e321f4619f313a6a31f0a9b8f4d3362bfe705472b89055cda` |

The native is a new full identity, 32 bytes smaller than the immediate control.
No old-full-native equality or metadata exception is claimed. Actual codegen
places YMM `vpmaddwd`, i32 reduction and side multiplication in search `P` before
evaluation/QS use. This is a static returned-score dependency check, not a speed
or functional-execution measurement.

Packaging remains one fixed LZMA1 ALONE 9-extreme/lc2/lp0/pb0/BT4/64MiB/nice64
stream with the 77-byte prefix. ALONE has no checksum; the complete cost includes
header, launcher, bootstrap and source literal. Strict recovery checked the
exact source/bootstrap/compiler argv. No name, codec, flag or resource sweep
is part of the producer.

Focused qualification first stopped at a harness compile error: canonical
`half` was used on shipping `za`, whose field is `zL`. That v1 failure is preserved
as result `a8db8af5857f66e59e5ea36f30e4dff4b29c6849c4e32fefe13037b09c0f1688`.
V2 corrects only those three fixture field tokens; all other fixture bytes and
the candidate remain unchanged. V2 passed 832 component
cases (not legal full boards), 39 admission-shape boards plus 10 actual special
children, 98 side and98 deliberately nonadmitted padding probes, promotion 8,
castle 4 and EP 2. Actual kernel/value sum/independent scalar formula and made-child
hash/context checks pass. No TT/sort suite or broad core matrix was repeated.

Two separately qualified whole wrappers passed eight legal GO results, exact
restored new native, startup three persistent TIDs, stdio-only descriptors,
private-path cleanup and physical quit/EOF settlement. The focused proof index
is `c23d10677dfea9ea2d0578d9b746724fa3282c78867dd7c4b4a3abff5d2a8962`.
Direct normal generation reproduced shipping twice and DEV twice from the
ordinary 21-file closure. Both DEV source and full native matched the previous
literal pins. The unchanged verifier then passed one quit and one EOF session,
with eight legal GO results. These normal receipts are separate from the focused
fixture and experimental wrapper receipts. The exact producing recipe is
preserved outside Git; only qualification metadata was added after execution. Older qualifications remain ancestry, not a new full-core result.

Per-node `value()`/feature construction may change speed. No benchmark, playing
strength, target scaling or 4KiB eligibility is claimed. Cancellation causality
remains unproven. Generated artifacts, fixtures, failure logs and receipts stay
outside Git.