# Independent Rust D: one fixed self-restoring file first cost

This experiment owns exact snapshots of the already qualified no_std Rust D
native inputs and the project-owned C D packaging helpers. Its ordinary builder
reads only these source files, its literal recipe and system build tools. It
does not read mutable maintained engine directories, old generated binaries,
historical reports, npm packages or a new Rust ASCII experiment.

It is a distinct `tiny-rust-d-sectionless-load-v1` class. The original C D
admission, source, recipe and layout are not changed or extended. The C packer's
snapshot is exact, including its original C admission function; this producer
never calls that admission. It performs a separate literal Rust admission.
The C code supplies only the owned decoder/entry wrapper and build-time tools.
The board, HCE, search, TT, protocol and raw clone/futex OS remain the unchanged
independent Rust core. There is no C engine backend or runtime external decoder.

The two original controlled native ELFs are each 16,824 bytes:

| Profile | Complete original native SHA-256 |
|---|---|
| HQ | `2c84c684d840ad7e7f0567b2b76d9c28693a00f6f95779675fb45ff84c06d3b3` |
| Scalar | `0c364208165b79d95f146650ec8ae144f1e4cb6427197b80f37f0e97a90a4eb3` |

Native source, Rust compiler flags, linker, 2-search-worker/TT18/PLY128 resources
and HQ/scalar implementations are unchanged. Each native is rebuilt twice with
the original builder and must match the complete original hash. The original
builder also retains its separate same-load-image unstripped static audit.
The producer never executes a native or self-restoring ELF.

The existing section stripping removes section metadata outside the PT_LOAD
file contents and zeroes only ELF section-header metadata fields. Both retained
load spans are 16,400 bytes. Program headers, entry and every byte from `_start`
through text/rodata/data remain identical; header metadata in the RX segment
differs deliberately. Original complete native, sectionless load span, payload
and self-restoring whole file are distinct identities. Decoding all 16,824 bytes
would incorrectly copy section metadata over `.bss`, so it is rejected.

The new class has fixed entry `0x4000f0`, final RX4 pages at `0x400000`, final
RW1 page at `0x404000`, and guards at `0x3ff000` and `0x405000`. The initialized
RW first 16 bytes are the exact memcpy/memcmp pointer slots
`46014000000000008801400000000000`; the next four BSS bytes are OUTPUT=0.
The decoded stream ends immediately before that BSS. The remaining RW page
tail must stay zero at entry.

The unchanged loader uses IMAGE_PAGES=0x5000 for its temporary decode/protect
span and BSS_BASE=0x404000/BSS_PAGES=0x1000 for the final data-and-BSS page.
These macro names do not describe the final RX span or an all-zero RW page in
this class. Five pages are RW during decode, then RX, then the last page is
changed to RW before entry. No native code runs between those permission
changes and no mapping is RWX. The original READ_IMPLIES_EXEC rejection,
MAP_FIXED_NOREPLACE reservation, bounds-checked fixed decoder, inverse BCJ,
original stack handoff and loader link address `0x10000000` are unchanged.

Only the existing E8/E9 BCJ and one-final-fixed-Huffman Deflate recipe is used.
No codec/preset/compiler/linker search or new Rust unsafe code is introduced.
Both profiles are independently encoded/loader-compiled twice. The actual
complete bytes and payload must reproduce. Loader/header contribution is
measured rather than assumed equal to the C class's previous 1,115 bytes.

On Linux x86-64, including the qualified WSL Ubuntu toolchain:

```sh
python3 -I -B engines/experiments/tiny-rust-d-packed/build.py \
  --out /absolute/new/external-first-cost \
  --rustc /home/stemxstudio/.cargo/bin/rustc
```

The output must be new and outside the repository. The native builder runs
from a closed source snapshot with its original repository-relative placement.
Source pins are raw LF bytes; no implicit text normalization is admitted.
Compiler commands have per-command and aggregate bounds and owned process
groups. Incomplete or interrupted work retains `complete:false` and diagnostics.
Reports, builds, binaries and full source archives belong outside Git.

The independent source review closed before the first compiler invocation.
It found a failed-tool cleanup gap when a compiler descendant outlived its
Python leader; this was fixed before compilation. The first fixed recipe then
completed with both original natives and both whole files reproduced twice:

| Profile | Sectionless span | Fixed payload | Loader + headers | Complete own-ELF | Complete SHA-256 |
|---|---:|---:|---:|---:|---|
| HQ | 16,400 B | 11,439 B | 1,115 B | **12,554 B** | `ec6d1b5dae6915a44affcfe319d72171a4115389185b83fe50f7bfb93dce1318` |
| Scalar | 16,400 B | 11,079 B | 1,115 B | **12,194 B** | `78137e6ea89a38ac1cb3e83edaec65d420a05fe3e9d1f3a340d23d76046489b7` |

These are 4,270 and 4,630 bytes smaller than their complete direct-native
controls, but exceed 4,096 bytes by 8,458 and 8,098 bytes. These comparisons are
to the independent Rust native control, not to a different C engine.

At the original first-cost checkpoint, actual candidate ELF executions were
**zero**, and no CHECKPOINT had been built or executed. Static/source admission
and a build-time codec roundtrip did not prove actual restoration memory or
runtime behavior. The builder's `executed_ELFs:0` and `runtime_qualified:false`
describe that cost-only producer, which never executes an engine. Its executed
source and pre-result README are frozen in the external first-cost receipt.
The separately authorized actual-runtime follow-up and its incomplete negative
gate are recorded below; they do not change the original cost-only receipt.

Runtime qualification, under4k eligibility, playing strength, target resource
or scaling evidence, CI and release remain unproven. Old board/search and
raw-native runtime evidence stays separate from any future restored-file
runtime observation. Training and AWS are excluded.

## Bounded actual restoration observations and incomplete negative gate

The first actual restoration campaign used independently reviewed verifier
`1a2d24e0f3d386bbebf3370f66f23ac3d4b3002109e46c1436d64846ab507858`.
Its six positive sessions passed without forced cleanup:

- Two distinct CHECKPOINT loader files (HQ 12,577 B, scalar 12,217 B) stopped
  before original entry. Each had one TID, only stdio, actual anonymous RX4/RW1,
  the exact sectionless bytes including data16, zero OUTPUT/BSS4 and RW padding,
  both image guards and a non-executable process stack. SIGCONT then reached
  the original Rust entry, produced uciok/readyok and exited normally.
- Four exact shipping-file sessions covered both profiles with active quit and
  EOF. Each retained three startup TIDs and two guarded raw 1 MiB worker stacks,
  only stdio and no observed helper children. White/black clocked play, active
  GO replacement, active position replacement and final active shutdown gave
  six independent-oracle-legal results for six dispatched GOs per session.
  Queue/observed/consumed totals, whole `/proc/exe` identity, restored memory,
  stdout/stderr EOF, reader join and physical TID/group disappearance passed.

These are actual packed-file observations, distinct from earlier direct-native
board/search, raw-kernel trace, deep-stack and fault results. Cancellation
causality remains unproven. Final W^X maps were observed; the transient decode
sequence is also tied to unchanged loader source, not inferred from final maps
alone. No new large fault matrix, codec, engine source or compiler recipe was
introduced.

The overall campaign remains **`complete:false`**. Its subsequent HQ
READ_IMPLIES_EXEC rejection fixture exceeded its strict pre-entry syscall cap,
was force-cleaned and did not prove rejection. The first failed harness did
not preserve its partial syscall list; that lost evidence is not reconstructed.
The scalar rejection fixture was not executed.

A separately approved ONE HQ diagnostic used the identical shipping bytes and
logging-only corrected verifier
`33e37d4e1d5cf04361583dc5dd8e0f782105cada61d3636720231bfb9394acc8`.
It preserved every syscall event before the unchanged cap. The child confirmed
READ_IMPLIES_EXEC before exec, but the loader's first actual personality query
returned **0 after exec**. It then entered the restore mmap and RW-to-RX
protection sequence; the diagnostic stopped at the existing cap and was
force-cleaned. Thus the pre/post-exec flag differs in this environment, and
**the rejection negative remains unproven**. No criterion was relaxed and no
positive session was rerun. The source guard remains unchanged; this is not
an actual guard-rejection success claim.

`helpers/` contains immutable snapshots: the previous C verifier `045550...`
supplies process/reader/mapping observation functions, Rust strict verifier
`d43b9d...` supplies exact GO/result accounting and guarded-stack recognition,
and independent oracle `aea285...` supplies legal witnesses. Their historical
top-level image expectations or native qualification claims are not reused.
The new verifier never calls the old C image inspector or constructs a second
old Rust Session process. Its own literal whole guards and Rust mapping rules
are separate. Later mutable maintained C/Rust files are not runtime inputs.

The reviewed/executed first verifier and all failed reports, raw streams,
CHECKPOINT files, corrected diagnostic source/events and source inventories are
preserved outside Git. The current corrected verifier has not rerun the full
campaign. Further negative-gate work requires a deliberate follow-up; these
partial positive results do not establish complete runtime admission, 4 KiB
eligibility, final resource/scaling performance, strength, CI or release.
