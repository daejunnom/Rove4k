# TinyD fixed-image restoration study

This experiment specializes deployment to one frozen, project-owned TinyD
image. It does not replace the generic ELF packer or modify TinyD source/search.
The generic memfd/execveat wrapper remains a control. Training and AWS are outside
this work. Actual native loader size and execution must be measured separately
from the build-time payload measurements below.

## Frozen input and observed layout

The input root is `/absolute/external/rove4k-tiny-d-final-20261020`. Its copied
`sources/image.ld` and `sources/start.S` define the deployment contract; changing
those files or the final ELF requires a new admission check and recipe identity.

| Image | Exact input SHA-256 | File/RX bytes | Entry |
| --- | --- | ---: | --- |
| scalar-shipping/x | ef14e2839af96d111fa9ce1a2928749ceec518e3be652cc6d36ee8975cae47d0 | 8,540 | 0x401fa6 |
| hq-shipping/x | 387a00209ffcc14446f662a56cc2ff778ae7873c2dfebebbee9906fd19e5cd0c | 8,928 | 0x4020e3 |

Both actual ELF program-header tables contain exactly:

- RX `PT_LOAD`: file offset 0, virtual address `0x400000`, `filesz == memsz`
  equal to the full input file size, page alignment 4096.
- RW `PT_LOAD`: virtual address `0x403000`, `filesz == 0`, `memsz == 175092`
  (`0x2abf4`), page alignment 4096. The page-rounded end is `0x42e000`.
- `PT_GNU_STACK` with RW flags and no execute flag.

ELF/program headers occupy the first `0xe8` bytes and are themselves inside the
RX load. Keep those bytes in the restored image. They compress cheaply and allow
the stronger claim that every original RX load byte is restored at its original
address. Discarding them would introduce an unnecessary memory-identity
exception. The RW segment is currently entirely zero-initialized; the linker
script still permits `.data`, so a future nonzero RW `filesz` must be rejected
rather than silently treated as BSS.

## Chosen mapping architecture

Link the complete loader and compressed payload at a separate small-code-model
address such as `0x10000000`. Its actual program headers must prove that it does
not overlap the restoration span or guard pages. The generic loader's existing
`0x400000` base cannot be reused for direct restoration.

Reserve `[0x3ff000, 0x42f000)` as private anonymous `PROT_NONE` memory with
`MAP_FIXED_NOREPLACE`. This is `0x30000` bytes including one guard page on each
side. Reject a syscall error or any returned address different from the request;
an older kernel may ignore the flag. Never fall back to destructive
`MAP_FIXED`, and do not create an unmap/remap gap. This follows the documented
[Linux mmap behavior](https://man7.org/linux/man-pages/man2/mmap.2.html).

Change `[0x400000, 0x403000)` to RW while decoding the full RX image. After
decompression, inverse BCJ in place and change those same pages to RX. Make
`[0x403000, 0x42e000)` RW for BSS; anonymous mappings supply its initial zero
bytes. Keep the outer pages inaccessible. Check every `mprotect` result and
never request writable+executable memory. The loader ELF must also declare a
non-executable stack. Linux documents personality-dependent implicit execution
permissions, so actual mapping checks or explicit rejection of
`READ_IMPLIES_EXEC` are needed for a strict permission claim.
[Linux mprotect semantics](https://man7.org/linux/man-pages/man2/mprotect.2.html)

Preserve the original kernel-entry RSP before calling a C decoder. A noreturn
assembly trampoline restores that RSP, clears DF/EBP, supplies the no-dynamic
loader EDX state, and jumps to the exact frozen entry. Do not call the engine
entry as an ordinary C function or rely on a C epilogue after rewriting RSP.
TinyD's entry aligns the stack and calls `main(void)` itself.

This handoff keeps the original stdin/out/err and process/thread identity but
does not create a new kernel ELF execution. Auxv still describes the loader,
and its mappings and initial brk state remain present. Current TinyD uses raw
syscalls/mmap, has no TLS/interpreter, and does not read auxv or use libc startup.
These are explicit admission requirements. Restoring original header bytes does
not make `AT_PHDR`, `AT_ENTRY` or `/proc/self/exe` describe the restored engine.
Do not extend this format to arbitrary C/Rust executables under that claim.

## Exactly two codec alternatives

Both alternatives use the same fixed mapping and reversible BCJ transform of
the complete RX byte sequence, starting at byte offset zero. The native inverse
runs only after the entire decompression completes, so LZ history remains in the
transformed domain. Build-time roundtrip must reproduce the original full RX
bytes exactly.

1. Internal LZ runs, copied from this repository's handwritten generic packer.
   Literal runs have 1..128 bytes; three-byte matches encode length 3..130 and
   16-bit nonzero distance. This is the simple decoder/control alternative.
2. One final fixed-Huffman raw Deflate block, produced at build time with
   Python zlib `Z_FIXED`, decoded at runtime by project-owned code. The dedicated
   subset rejects every stored, dynamic or non-final block, reserved symbol,
   out-of-bounds reference, size mismatch, trailing byte and nonzero padding.
   Producer strategy alone does not prove admission because zlib can choose
   stored blocks. Parse the complete stream before accepting it.

Fixed Huffman coding can be decoded bit-serially from its 7/8/9-bit canonical
intervals. Length and distance bases can be computed without large decode tables.
Huffman code bits and ordinary extra fields have different bit order; all reads
and forward-overlapping copies need bounds. This deliberately constrained format
is based on [RFC 1951](https://www.rfc-editor.org/rfc/rfc1951.html), rather than a
claim to support every Deflate stream. The pure Python decoder is checked against
zlib's independent decoder and manually written streams.

## Measured payload floors

These are actual codec payload measurements from the frozen full RX bytes, not
native loader output sizes. The header floor uses a conventional 64-byte ELF
header plus one 56-byte load header and one 56-byte GNU-stack header (176 bytes).
It assumes a zero-byte decoder and therefore is a lower bound only for this
specified layout/codec, not a universal compression lower bound.

| Input | BCJ + internal LZ | BCJ + fixed Deflate | Fixed payload + 176 B header floor |
| --- | ---: | ---: | ---: |
| scalar | 7,931 | 6,550 | 6,726 |
| HQ | 8,267 | 6,803 | 6,979 |

Thus neither codec can reach 4096 bytes on these frozen inputs even with a
zero-byte decoder. Still measure both complete native artifacts: the simpler
decoder may offset some payload loss, and a useful size reduction against the
generic wrapper remains possible. Reaching 4K requires a substantially smaller
source/machine image or a different codec outside these two alternatives.

The actual fixed streams each contain one final fixed block. Payload hashes:

| Input | Internal LZ SHA-256 | Fixed Deflate SHA-256 |
| --- | --- | --- |
| scalar | 7c6054ab88ed9902ea5ad7cbbd28bc4de9ed8e9b0f093cdd871ca32efd91c6bf | 2b8a5e3b0b921a016cf4459bc55c1cd12c8613d08fa22a25b29698877298fb1d |
| HQ | 6f711684ac6178b8eff5bd6c4fc1872af1399d990dcee15b48ae864008eebcc7 | accf77f742e93cdea6d1bc013d7034689faf299db2e13db18a9e5f022e12e02a |

## Native acceptance contract

The final loader must demonstrate the original RX bytes at the fixed mapping,
the entire logical BSS initially zero, the correct entry, guards, RX/RW page
permissions and non-executable stack. Do this before engine initialization
changes BSS. A separate instrumented observation build can test the handoff;
the actual shipping loader must then pass TinyD's existing UCI/runtime/chess
checks and reproduce byte-identically from the frozen recipe. Keep the generic
wrapper and raw native image as unchanged controls. Reject unsupported images
and mapping collisions without executing a partially restored image.

Pure checks are available without compilation:

```sh
TINY_D_FROZEN_ROOT=/absolute/external/rove4k-tiny-d-final-20261020 \
python3 engines/experiments/tiny-d-loader/test_codecs.py
```
