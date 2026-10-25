# One D TT payload-lock native cost experiment

This isolated folder closes the maintained C D's 18 ordinary sources from
`a3546f1f409337bc0cf176cdfefc14bbdd1a3693`. The exact source18 set is
`81ca7f18839efd52484add4dacce2fedccb15dd8a121e834ee02bf0ba531563c`.
`inputs/entry/` is an ordinary frozen source snapshot, independent of future
maintained edits. The original source archive and all six selected native,
whole and audit controls are preserved externally before this experiment.
Historical receipt identities are metadata; no historical report or image is
an input to normal native generation.

There is one project-owned source transform and no spelling, compiler flag,
profile, resource setting, codec or search-feature variant. It changes exactly
three source fragments:

- `tiny.h`: replace the separate atomic_flag with an exact-width atomic data
  field and add a compile-time aligned/always-lock-free 64-bit admission.
- `search.c`: keep the probe signature and write-flag behavior, using a single
  acquire exchange to reserve data bit 63 and a release payload store to unlock.
- `runtime.c`: initialize key and atomic data only in the existing quiescent
  clear. Startup-before-clone and DEV wait-before-clear callers are unchanged.

The other five native files, full 64-bit key comparison, TT context, board,
search logic outside probe, HQ, finite clocks, completion latch, raw OS/pool,
loader, codec and compiler/linker flags retain their exact source bytes.
TT_BITS remains 18, WORKERS 2, PLY 128 and DEV 0.

## Ownership and payload contract

The current payload producer occupies bits 0--42: Move 0--16, score 17--32,
depth decoder 33--40 and bound 41--42. Actual positive depth is at most 126.
Bits 43--63 are unused; bit 63 is the temporary marker. No key bit is reserved.

Exchange returns the old payload and writes only the marker. A caller that
receives a marked old value returns a miss without key access or a later store.
A successful reader uses the returned old payload, not the current marked data.
Read hit, mismatch and zero-payload cases all release-restore the old payload;
the returned mismatch zero is never stored into another key's slot. A writer
sets the full key before release-publishing the new payload. Every successful
owner releases, including readers. There is no retry/spin loop.

The contending marker exchange is an indivisible RMW. It cannot read a marker
and separately overwrite a later owner publication; if it follows release, it
receives the published payload and becomes the next owner. Reader release is
retained to order plain key accesses and carry publication to the next acquire.
The original quiescent clear fences remain necessary because atomic_init does
not protect a concurrent clear. No new concurrency qualification is claimed.

The new admission requires atomic data size 8, Entry alignment at least 8,
data offset divisible by 8, mmap-page compatibility with Entry alignment, and
GCC's compile-time always-lock-free 8-byte property. It rejects a helper-based
fallback. It does not force sizeof(Entry), native length, RX pages or BSS extent
to match an assumed result.

## Native-first boundary

```sh
python3 -I -B engines/experiments/tiny-d-tt-payload-lock/build.py \
  --out /absolute/new/external-native-cost
```

The source closure is the frozen18 plus this folder's five ordinary files.
It is validated and copied before importing the frozen transform and original
packer. Native inputs are generated from those sources, never generated C or
an old image. The original fixed five-unit order and flags are used without
diagnostic compiler flags. First reproduce the scalar 8,092 B and HQ 8,480 B
controls twice each, then build the sole candidate's scalar and HQ forms twice
each: exactly eight native compilations. Each native and linked pair must be
byte-identical; the one transform also regenerates identical candidate source
bytes into two separate source roots. There is no runtime claim.

Actual linked bytes, headers/PHDRs, sections and stripped full native files are
saved before shape checks. The candidate's entry, RX pages, zero file-backed
data and BSS are observed rather than forced to the old class. The original
strict selected-image guard must still reject a changed candidate. There is
no new generic or cost-only image admission in this stage.

Entry size is tied to the actual native table mmap length dataflow and
the unchanged allocation expression `(1 << TT_BITS) * sizeof(Entry)`, using
read-only disassembly. An arbitrary occurrence of 0x400000 is insufficient,
since that is also the native RX base. This is compiled layout/allocation
evidence, not an observed runtime mapping. No auxiliary compiler mode, layout
runner or diagnostic flag is needed.

Actual compiled control/candidate Entry widths are 24 and 16 B. In both forms,
the table allocation syscall receives lengths 0x600000 and 0x400000 in RSI,
respectively, and stores its result into the same global reloaded by clear.
Clear's compiled strides are 24 and 16 B and its bounds are the corresponding
table lengths. The source allocation expression and TT_BITS remain unchanged.
This establishes a requested allocation change from 6 to 4 MiB for the same
262,144 slots, a 2,097,152 B reduction. It does not observe an allocation's
success, runtime mapping, residency or RSS. No old raw Entry24 snapshot is a
new Entry-layout proof.

The readable generated native source grows by 197 B, mainly from the explicit
compile-time atomic admission. This is not a readable-source saving. Separate
flag handling and the wider stride are removed, while the marker RMW and
old-payload preservation add work. Actual native results below are ties;
no whole-file result follows
from those results or the static allocation reduction.

## Fixed first-cost result

All eight native compilations completed with rc=0: both controls first/repeat
before both candidate forms first/repeat. Each full native and linked ELF is
byte-identical across its two attempts. Both independent candidate source
generations and canonical source proofs also match. No candidate variant or
additional compiler flag was introduced.

| Actual cost | Scalar control -> candidate | HQ control -> candidate |
| --- | ---: | ---: |
| Complete stripped native file | 8,092 -> 8,092 B | 8,480 -> 8,480 B |
| .text | 7,570 -> 7,575 B | 7,876 -> 7,881 B |
| .rodata | 284 -> 284 B | 352 -> 352 B |
| File-backed .data | 0 -> 0 B | 0 -> 0 B |
| BSS memsz | 175,092 -> 175,096 B | 175,092 -> 175,096 B |
| RX / BSS pages | 2 / 43 -> 2 / 43 | 3 / 43 -> 3 / 43 |

The 5 B text increase consumes alignment padding before unchanged rodata,
leaving the full native file size unchanged. Scalar text-to-rodata padding
falls from 6 to 1 B; HQ padding falls from 20 to 15 B. BSS grows by 4 B even
though its rounded 43-page extent stays unchanged. Neither form has a native
file saving, and the readable generated source grows by 197 B. The separate
static TT allocation benefit is not a code-size or performance claim.

Candidate scalar native SHA-256 is
`3df7daa7dab12645483db434e96f5bd20b98006cf6999d04443ee75a7761fb6d`,
entry 0x401e2d, RX base 0x400000 / 2 pages, BSS base 0x402000,
upper guard declaration 0x42d000 and reserve declaration 0x2f000.
Candidate HQ native SHA-256 is
`e65eeda016e6d38d4d469cec2075ab932b3eb37bfd32246d5bc9e5a19147c7ab`,
entry 0x401f5f, RX base 0x400000 / 3 pages, BSS base 0x403000,
upper guard declaration 0x42e000 and reserve declaration 0x30000.
Both have exactly RX, zero-file-backed RW BSS, and a non-executable stack PHDR;
there is no interpreter, W+X segment or file-backed writable data. These are
static ELF observations and declared geometry, not observed process mappings.
The unchanged production admission rejects both candidate identities.

The external original native receipt is SHA-256
`aaf06fafe74645a9a0ee06de8215b18d10add2ed140c16ac1226d96e7c366922`.
Its producing recipe, generated sources, all eight native and eight linked
images, and command outputs are preserved before this README-only annotation.
The separate static layout proof is SHA-256
`a2357cb72daa7d20c220228ed53f09938f82775b01ce95c4eb342c97154ad9bc`;
it checks actual native instruction bytes and four read-only disassemblies.
An independent review checked the source fragments, actual artifacts, command
order, repeat equality and geometry. None of these checks executes this new
TT protocol or qualifies its concurrent behavior.

This stage builds no loader or whole file, invokes no codec, starts no engine
or CHECKPOINT, and runs no DEV, fault, game, strength, scaling or benchmark
qualification. All generated C, binaries, disassembly, commands and receipts
remain outside Git. Maintained18, prior frozen experiments and shared files
remain unchanged; root owns any following stage and commits.
