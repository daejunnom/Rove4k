# F CAS16 first-cost experiment

This is a stopped, single-candidate shipping experiment. It changes the exact
9,954-byte maintained F source with four literal, reversible rules in
`recipe.json`. It does not change maintained F or claim runtime qualification.

The candidate replaces the lock/key/data entry with an aligned unsigned
128-bit scalar. A GCC `__sync_val_compare_and_swap` snapshot reads the full
64-bit key and full 64-bit payload together. Store attempts one CAS against
that snapshot and drops the write on failure, with no retry. All meaningful
43 payload bits, full context key, exact horizon, mate normalization, MTD
interval and root witness code remain outside the changed source fragments.
Contention behavior changes: a coherent read replaces a possible busy miss,
and a racing writer can drop a store. No trace, game or performance equality
is claimed.

The one allowed related cleanup removes startup's redundant clear immediately
after successful `calloc`, before workers start. The scalar clear function is
retained and is safe only under a quiescent call contract. The input is already
shipping-only; this experiment does not generate or qualify a DEV candidate.

The candidate adds `-mcx16` to both the native compiler argv and the embedded
bootstrap argv. The same compilation includes size/alignment/CAS-target
assertions. The admitted target is GNU C on Linux AMD64 with advertised CX16,
16-byte scalar alignment and the AMD64 `calloc` alignment contract. This is not
a portable C or CPU-execution claim. There is no `libatomic` dependency.

| Artifact | Maintained control | CAS16 candidate |
| --- | ---: | ---: |
| Shipping C bytes | 9,954 | 9,933 |
| Native file bytes | 22,672 | 22,672 |
| Python bootstrap bytes | 10,953 | 10,939 |
| Complete file bytes | 4,814 | 4,862 |

The whole file **grew by 48 bytes**. Its SHA-256 is
`513f50e0bc21051c53d6d930af450715e6723f0bb1d5be786571eabc3bc1fe96`.
The candidate native differs from the control and has SHA-256
`78cfb7232c3bd90facc21c1e87ff5b953fe2a221b3877b77897107c6223570c6`.
No flags, codec, model or source alternatives were tried after this loss.

The codec was one unchanged ALONE/LZMA1 preset 9 extreme, lc2/lp0/pb0, BT4,
64 MiB dictionary, nice32 operation, with the existing 77-byte prefix. Strict
decode recovered the exact candidate source, bootstrap and compiler argv.
Complete size includes the source assertion and compiler-flag spelling.

The one native compilation succeeded, but its first checker assumed exactly
two static CAS sites and failed. That false `build.json` and its executed
producer are preserved unchanged outside Git. GCC separately inlined the read
and write calls, yielding three actual sites: read snapshot `0x26a5`, write
snapshot `0x2ae3`, and store CAS `0x2b1a`. Independent readback verified the
same table base plus `(key & 0x3ffff) << 4`, `calloc` element size 16, full
snapshot registers, one store with no retry edge, and no external 128-bit
helper. ELF instruction bytes were rebound to executable load ranges.

`build.py readback` is deliberately a receipt adapter for this exact historical
native and independent review, not a broad exception to the failed checker.
It leaves the failed build receipt untouched and writes a separate admission.
The revised cost producer is separately frozen from the initially executed
native producer. `build.py cost` rehashes the frozen ordinary helpers and
requires that admission before its one compression. The current native checker
records the observed three-site shape; no second compilation was performed.

The actual output root is
`/home/stemxstudio/rove4k-tiny-f-tt-cas16-20261020/`. The external final index
records the initial failure, both executed producer snapshots, independent
readback, source/native/bootstrap/whole identities, and all local source pins.
The experiment executed one native compile, one compression and one strict
decode. Control compilation/copy, native/engine execution, Clang AST, games,
benchmarks and concurrency stress were all zero. Static alignment and CPU
advertisement were checked; actual allocation addresses and CX16 execution
were not observed. The result remains above 4,096 bytes and is not an eligible
4K artifact.
