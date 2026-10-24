# Tiny Rust D runtime start constructor experiment

This is one source-owned candidate over the frozen maintained ASCII Tiny Rust D.
Only `Board::start()` changes: `empty()`, four existing `put` calls per file and
the final state hash/context replace the separate full-board rebuild. This is a
runtime constructor, not the separately reviewed const-factory idea. Generic
`rebuild`, `canonical_ep`, public value and parsing APIs, move/search/TT/learning,
OS/SMP, compiler flags, linker script, resource profile and ABI are unchanged.
The equality-dispatch idea is not included.

`control/` preserves all 17 maintained ASCII source files as ordinary LF files.
The producer reads this owned snapshot, never a future mutable maintained tree.
`start.rs.in` is the readable candidate constructor; `producer.py` binds exactly
seven control production inputs and proves the outside-constructor bytes exact.
The unchanged original `build.py` is copied into both generated source trees.
Test helpers are not part of those seven production inputs or either native.

At fixed Rust 1.97.0, workers 2 and TT bits 18, both control literals reproduce
and both candidate profiles independently reproduce complete ELF bytes:

| Form | Complete ELF B | `.text` B | `.rodata` B | `.data` B | SHA-256 |
| --- | ---: | ---: | ---: | ---: | --- |
| ASCII control HQ | 16,816 | 14,137 | 304 | 8 | `f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8` |
| Runtime put HQ | 16,816 | 13,865 | 304 | 8 | `9b72472b1b73ee12a6ab2755e8b9c14f5544efc6766cf67eb8bbee031bbbabcf` |
| ASCII control scalar | 16,816 | 13,689 | 304 | 8 | `bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878` |
| Runtime put scalar | 16,816 | 13,417 | 304 | 8 | `ef9b112aa489268bffa1c8cf96dbde945e811a93f2a95357cbd74ff6779e7461` |

Readable five-module Rust source grows from 39,461 B to 39,477 B. The identical
inline-module measurement grows from 39,477 B to 39,493 B; that measurement file
was not compiled. Each profile reduces allocated `.text` by 272 B, leaves
`.rodata`/`.data` unchanged, and retains `.data` at file offset `0x4000`. Alignment
absorbs the saving, so the complete native file does not shrink.

The existing `put` symbol is 314 B in all forms. `start` changes 545 to 322 B.
The old 307 B separate `canonical_ep` symbol disappears; its unchanged source
body is inlined into `play`, whose symbol grows from 958 to 1,217 B. Those
function changes explain 271 B and text placement accounts for the remaining
byte. The total `.text` measurement, not a sum of duplicated aliases, is the
272 B result.

```sh
python3 -I -B engines/experiments/tiny-rust-d-start/run_cost.py \
  --out /absolute/new/tiny-rust-d-start-cost --rustc rustc
```

The command builds each control/candidate profile twice, checks exact control
ELF literals, freezes source/recipe inputs, checks the unchanged builder's ELF
gates and keeps an unstripped allocatable-image audit. It never executes a
production ELF or creates a packed artifact. Its first attempted orchestration
failed before compiler invocation because Python isolated mode excludes bare
sibling imports. The failed runner and receipt are retained externally; the
executed revision loads only its owned producer explicitly.

The 32 constructor destinations are distinct valid squares and initially empty.
The existing `put` therefore accumulates the same piece hash, score, bitboards
and king positions. Side, castle, halfmove and EP are unchanged; `canonical_ep`
on this fixed `ep=-1` would be a no-op. Final state XOR and `context=hash` retain
the old values. This proof does not remove any arbitrary-input check from the
generic board API. The separate std field diagnostic compares all named fields
and copy ownership against the frozen original ordinary runtime constructor.

Both HQ and scalar std diagnostics passed two unit tests each. They compare all
151 elements of the ten named Board fields and exercise mutation of a copied
value and fresh-constructor independence for both original and candidate. The
two exact board source files are separate modules; opaque function pointers and
opt-level zero retain ordinary runtime constructor calls. Those std executables
do not include the production main, raw OS, search or worker runtime.

```sh
python3 -I -B engines/experiments/tiny-rust-d-start/verify_fields.py \
  --control-dir /absolute/checkout/engines/experiments/tiny-rust-d-start/control \
  --candidate-dir /absolute/cost-output/candidate-source/engines/compact/tiny-rust-d \
  --candidate-sha256 4f476e713d3dfc10350c33035efa99038e8f0afe8014ac7c4064216c64ea750c \
  --out /absolute/new/tiny-rust-d-start-fields --rustc rustc
```

Complete-file reproduction, std field equivalence, source-body proof and actual
production runtime are distinct evidence classes. The candidate production ELFs
have **not been executed**. No packed size, decoder admission, main promotion,
4 KiB eligibility, speed, strength, broad board/search/deep/fault qualification
or CI success is claimed. A future packed-payload cost can be considered because
actual code shrank, but it has not been produced or measured here.
