# Maintained minimal B entry

`engine.c` is the unchanged readable canonical B program. The selected complete
shipping file is **5,851 bytes**, still **1,755 bytes above 4,096**. The program
retains hybrid bitboards, shared attackers, legal SEE, qualified singular
exclusion, PVS/QS, coherent full-key TT and its existing fixed-resource UCI pool.
Compact C, native ELF and complete wrapper are generated artifacts.

## Ordinary build

On Linux x86-64 with the recorded Ubuntu 24.04.4/GCC 13.3.0/binutils 2.42/
glibc 2.39/Python 3.12.3/xz 5.4.5 toolchain:

```sh
python3 -B engines/compact/tiny-entry-b/build.py --out /absolute/new/B-build --dev
python3 -B engines/compact/tiny-entry-b/fresh.py --out /absolute/new/B-fresh
```

Output paths must be new absolute directories outside any Git checkout. The
single local profile fixes two search workers, one controller, TT bits 18 and
PLY 128. These are not final target-resource selections. Shipping compiler:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

DEV changes only DEV to one. The compiler remains unstripped. Bootstrap,
75-byte launcher and fixed XZ/LZMA2 preset 9 extreme, lc3/lp0/pb2, CRC64 remain
unchanged. All bootstrap, source, restoration and launcher bytes count toward
the complete file. The builder performs no policy, flag or codec sweep.

The old shared89 source-name/resource stage runs unchanged. A new local
`shipping_storage.py` then applies the fixed eighteen remaining object names
to the single exact B shipping source. Its embedded policy SHA is
`ed24184ebe07a23e09983a219eb2f20370c783e7b308aee2515df8ecfe713c87`.
It calls only the caller's pinned shared generic rewrite/scanner and lexer,
with its own canonical readable bytes. The shared helper and C/E admission
domains remain unchanged. DEV bypasses both shipping spelling stages.

The normal source closure has eighteen files. Helpers and local inputs are
authenticated and copied before import. It reads no experiment, historical
report, old generated file, other-family canonical source or network input.
Each builder invocation reproduces shipping twice and optional DEV twice.
`fresh.py` uses a separate temporary Git tree/archive and two independent source
extractions without changing the calling checkout's index.

## Source and image boundary

Canonical B and DEV source/native remain exact to the old B5955 control.
Shipping C falls **13,606 to 13,071 bytes** through 112 fixed token edits, with
directives, literals, APIs, resources and PLY uses preserved. Actual complete
preprocessor alias-only inversion, fresh header names and macro-definition
multiplicity pass for this source pair.

The new shipping ELF is a distinct image. The original experiment's whole-ELF
identity assertion failed and remains failed. The separate new-image
qualification pins both full hashes and accounts for all file bytes. Program
headers, allocated-section geometry, code/data, dynamic symbols/strings and
relocations remain exact. Explicit differences are limited to the literal GNU
build-ID descriptor, ELF section-table pointer and fixed nonallocated
symbol/string/section metadata associated with nineteen named object symbols.
Local symbol order, raw attributes, values, sizes, sections and multiplicity
remain fixed; only the permitted global ordering/string offsets differ.

The qualifier does not normalize or strip an image, and does not claim general
ABI equivalence. The sole stdin translation unit has no exported engine-object
consumer in its unchanged dynamic symbol/relocation domain. Existing rule and
search evidence is reused within this source and machine-code boundary, with
actual selected restoration and process checks kept separate.

The new normal builder requires the new full native identity. It never treats
that image as the old native, and no failed old expectation is automatically
updated. The metadata pure-byte suite passes 44 cases; first-cost controls and
both independent candidate packages reproduce. The original failure index is
`0bf7fa1b7fc6d74b40a0d59c30bf91c5bca7c6f729a90330d5129851c6193e66`;
new cost receipt is
`d5d4729a808e031f5f76d63e946be00a2e321c16ae47a8bb919d8d723debf9d4`.
These hashes are provenance metadata, never generation inputs.

## Selected identities

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C | 13,071 | `96e6e330e5289d1c404dac0402e8b672a89c52e193a9d4f9aebb02e0c9042ffa` |
| Native ELF | 26,496 | `5a315a66f86ff81f9b0feb679b25f919c5aaf63bb9db2d157040a5b7ce6bbb4b` |
| Complete file | 5,851 | `25b2c6a1198d5e600be252ae57da84ca9f9e40c3167021ce33f3f9eff29f425c` |
| Bootstrap | — | `7159e4bad6b9bfd37f69dbcc8ebe6fec5ff497c425323ec2e71050f43dc46673` |

The unchanged verifier binds a freshly generated wrapper to its new native:

```sh
python3 -B engines/compact/tiny-entry-b/verify.py --build /absolute/B-build --out /absolute/new/B-runtime
```

It checks legal clocked/bare GO output, the restored full native identity,
three stable startup TIDs, no remaining compiler child/private path,
one active-close result and physical quit/EOF settlement. It does not require
ordinary-TCEC optional commands from the minimum 4K interface. Cancellation
causality, final playing strength, target scaling and 4KiB eligibility remain
unproven. Generated binaries, reports and archives stay outside Git.
