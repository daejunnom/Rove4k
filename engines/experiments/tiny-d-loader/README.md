# Dedicated TinyD image restoration

This is a bounded deployment experiment for the two exact project-owned TinyD
`-Oz -flto` shipping images. It changes no board, evaluation, search, TT, pool,
worker count or command behavior. The central packer and TinyD source stay
unchanged. It is **not a 4 KiB entry**.

The builder admits the exact scalar 8,540-byte and HQ 8,928-byte SHA-256 values
listed in [ARCHITECTURE.md](ARCHITECTURE.md). It additionally checks every ELF
header, all three program segments, fixed entry, zero initialized-data size,
exact zero-BSS extent and separate RX/RW pages. Unknown content, layout,
interpreter, TLS or dynamic dependencies fail before loader construction.

The loader is linked at `0x10000000`. It reserves `[0x3ff000,0x42f000)` with
`PROT_NONE|MAP_FIXED_NOREPLACE`, verifies the returned address, and retains one
guard page at each end. The original full RX image, including its original ELF
headers, is restored at `0x400000` in RW pages and changed to RX. The original
BSS at `0x403000` is anonymous zero memory changed to RW. It never requests RWX,
rejects inherited `READ_IMPLIES_EXEC`, and declares a non-executable stack. A
small assembly handoff restores the initial RSP, clears DF/EBP/EDX and jumps to
the exact native entry.

There is no runtime ELF parser, memfd, exec, pathname, temporary file, external
decoder, interpreter or library. Auxv, initial brk, the extra loader mapping and
`/proc/self/exe` still describe the loader process. This is admitted only because
the frozen TinyD uses raw syscalls and mmap, with no libc/TLS/auxv/brk dependency.
It does not preserve those observations for arbitrary programs.

## Two alternatives and complete-file cost

Both alternatives first apply the same reversible E8/E9 BCJ transform to the
whole RX image. One uses the repository's existing LZ run format; the other uses
exactly one final fixed-Huffman raw Deflate block. The build-time producer uses
Python's zlib `Z_FIXED`, then independently parses the entire stream and compares
all decoded bytes. Stored, dynamic and non-final blocks, reserved symbols,
invalid distances/sizes, extra bytes and nonzero padding are rejected.

The runtime fixed-Huffman decoder is handwritten from
[RFC 1951](https://www.rfc-editor.org/rfc/rfc1951.html); no external decoder code
was copied. The internal LZ/BCJ format derives from this repository's handwritten
`engines/scripts/elf_loader.py` under the root [MIT license](../../../LICENSE).
Python zlib is a build dependency only. There is no runtime zlib linkage.

Final version 3 measured these full executable files on Linux x86-64/GCC 13.3:

| Mode | Raw native control | Generic own-ELF control | Dedicated LZ | Dedicated fixed Deflate |
| --- | ---: | ---: | ---: | ---: |
| Scalar | 8,540 | 8,806 | 8,721 | **7,665** |
| HQ | 8,928 | 9,142 | 9,057 | **7,918** |

LZ is 181/129 bytes larger than raw native and remains a measured loss. Fixed
Deflate saves 875/1,010 bytes against raw native and 1,141/1,224 against the
generic own-ELF controls. Its payloads are 6,550/6,803 bytes and the entire
decoder plus ELF headers adds 1,115 bytes. The LZ payloads are 7,931/8,267 bytes,
with 790 bytes of decoder and headers. All configuration, headers and inverse
BCJ code count. Filenames are `x`; no behavior is selected through the filename.

The selected generic controls use the same 7,931/8,267-byte LZ+BCJ payloads with
875 bytes of overhead: 176 ELF/program-header bytes and 699 restoration/filter/
alignment bytes. Without BCJ their payloads were 8,223/8,558 and overhead was
747 (176 headers plus 571 decoder/alignment). Thus the filter adds 128 overhead
bytes, saves 292/291 payload bytes and saves 164/163 complete-file bytes. These
figures were read from the frozen controls; no extra compression run was used.

These are exactly two codec/layout alternatives, with no compression-preset
sweep. Even a zero-byte decoder plus this format's 176-byte ELF/program headers
would leave fixed Deflate at 6,726/6,979 bytes on these frozen inputs. This is a
codec/layout-specific floor, not a universal compression lower bound.

## Reproduction and observed state

Use a new absolute external output path:

```sh
python3 -B engines/experiments/tiny-d-loader/build.py \
  --input-root /absolute/external/rove4k-tiny-d-final-20261020 \
  --out /absolute/external/direct-loader
python3 -B /absolute/external/direct-loader/recipe/test_runtime.py \
  --build /absolute/external/direct-loader/build.json \
  --out /absolute/external/direct-loader/image-check
python3 -B engines/experiments/tiny-d-loader/test_layout.py \
  --input-root /absolute/external/rove4k-tiny-d-final-20261020 \
  --out /absolute/external/admission-check
```

The builder freezes exact source/recipe/native/generic-control bytes and ELF
segments outside Git, constructs two independent copies of every final file,
and requires whole-file SHA-256 equality. Instrumented pre-entry observation
builds and deliberately malformed decoder controls are separate files and never
count as candidate sizes. Replay the archived `recipe/build.py` against the
unchanged admitted control root into another external path to repeat the recipe.

The actual final four loaders were independently rebuilt and later reproduced
again by executing the archived recipe. A separate parent `/proc` inspection
stopped each observation build before entering TinyD and verified every restored
RX byte against the original full native SHA-256, all 175,092 BSS bytes plus page
padding zero, both guard mappings, RX/RW permissions and a non-executable stack.
The production files then performed a clocked search with three persistent
startup TIDs, unchanged full RX memory and only descriptors 0/1/2. Quit and EOF
exited successfully. Four invalid native decoder fixtures exited 126 without
producing engine output. Fourteen exact-input/header/content admission cases
passed. Pure codec tests cover fixed-code classes, distance 32768, overlap,
truncation, reserved codes, bounds, padding and trailing data.

The final four production files separately passed all 20 common shipping groups
(protocol, lifecycle, legal selfplay, EOF and quit), with expected program hashes,
exact three startup TIDs, persistent IDs and maximum three threads enforced.
The selected fixed-Deflate scalar and HQ files also passed two colour-exchanged
12-ply games under the independent oracle. Receipt ordering in the clocked
lifecycle checks does not prove cancellation causality.

The observed environment is GCC 13.3, GNU ld 2.42, Python 3.12.3, zlib 1.3 at
build and runtime, and WSL Linux 6.6.87.2. An explicit toolchain supplement binds
these versions to the unchanged final files; new builder reports record them
directly. Archived replay proves reproduction in this observed environment,
without a cross-version portability claim. No NPS, strength, large-machine
scaling or event eligibility was established. Further size reduction requires
changes beyond this bounded loader comparison. Generated evidence remains outside Git under
`/absolute/external/rove4k-tiny-d-direct-loader-20261020-v3`; previous measurements
are preserved separately, including the first 7,626/7,879-byte decoder before
the final explicit personality/entry-state guards.
