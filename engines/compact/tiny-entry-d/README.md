# Maintained selected C D context own-ELF entry

The readable native program is in `native/`. The project-owned restoring
loader, independent integer decoder and build-time encoder are in `loader/`.
`recipe.json` pins their source, compiler/linker order, resources, finite public
policy, exact native mapping classes and full native/whole/audit identities.
Generated images, packets and reports belong outside this source folder.

This integration replaces the previous fixed-Huffman codec with one fixed
H24/base10 context format. All eight native files, both linker scripts,
resources and compiler/linker flags retain their exact bytes. The normal
producer reads only maintained ordinary source and the installed compiler and
Python standard library. Upstream source/programs, historical packets, images,
experiments and report paths are not normal inputs. The root MIT license applies.

| Fixed form | Native ELF | Complete own-ELF | Complete SHA-256 |
| --- | ---: | ---: | --- |
| Scalar | 8,092 B | **6,401 B** | `7e8f405c40ae5a64f3420f23d77a179d4154e5b9bd9e9c67aea1c83a18d238da` |
| HQ | 8,480 B | **6,614 B** | `be6a45a21895b204550cc0ae7a9a73928d6f4df1313757bad68db4dd97c4f358` |

Both exceed 4,096 bytes by 2,305/2,518 bytes. Native identities and costs remain
unchanged. The complete files save 1,056/1,093 B against the preserved
7,457/7,707 B controls; these are measured whole-file differences. This folder
makes no event eligibility, playing-strength, throughput or scaling claim.
The old maintained18, archive and all six native/whole/audit controls were
verified against their external preservation before integration.

## Qualified source reproduction

The initial normal-source discovery reproduced both full shipping SHA values
and measured the two new CHECKPOINT identities without target execution. After
independent frozen-source review and explicit literal admission, **one unchanged
fresh invocation completed with two independent closed source extractions**.
Actual source/archive, repeated native/whole/audit files, eight shipping sessions
and four positive pre-entry audits passed. All compiler commands and target
sessions returned zero; no forced cleanup or retry was needed.

The producing source21 set is
`f32b345cdc1f5b031130dcfe8ca52a5778f310a132af772e7d2208e6390be5e0`,
recipe SHA `76af9740e012235c48d4abd6880ef91c2a49c101a6300d9df5611bcae5dbb341`,
and ordinary source23 archive SHA
`4a05643884df255f56e16e50da70c10cb9536b3af1ff7b316a7bf30be924e09f`.
The actual fresh receipt is
`3e8ab7c220c5ed26da56dde77fa5b086d4f5f8165518181a10b7676f7611e35b`,
readback `26ced4a9aa2bdec75f1f16c7018401eec289d0b44b33eda95d59b86c2a098776`,
and independent source/literal review
`a8acbd25821eb5552671b4f02a3d4dc2be0720601446b4b5c4e9ee6ce7d8e19d`.

Only this README and recipe qualification metadata were updated after that
producing closure. The actual producing recipe/source/archive remain separately
frozen; these final explanatory bytes were not the inputs of a second fresh run.
Native, loader, encoder/model, scripts, flags and expected identities are exact
between the producing closure and final metadata snapshot. The normal producer
has no dependency on frozen experiments or receipts. Old decoder audits remain
historical ancestry; the new context path has its own actual pre-entry results.

## Fixed finite shipping policy and native core

Shipping implements `uci`, `isready`, startpos move histories, clocked `go`,
`quit` and EOF. `uci` emits `uciok` without optional identification or options.
`stop` and `ucinewgame` are consumed without cancellation or TT clear.
`infinite` is consumed as an unsupported token; every GO is finite. Without an
own-side clock, its search budget is 1,000 ms. A present zero/invalid own clock
uses at least 1 ms under the unchanged formula. Opposite clock alone uses the
default. Checked numbers, overflow and missing-value reprocessing are unchanged.
These choices follow the project's minimum TCEC 4k policy, not general TCEC UCI.

The default is a search budget, **not a hard wall-time cap**. Periodic deadline
checks, fallback preparation, scheduling and output add time. Next `go`,
`position`, `quit` and EOF still request cancellation and acquire `pending==0`
after result output before reusing job storage. Pending 1 reserves publication.
Ignoring stop and retaining TT can affect choices under time limits even when
search source is unchanged.

Resources are fixed at WORKERS=2, TT_BITS=18, PLY=128 and DEV=0. Two search
workers and the input thread persist from startup. Board legality, legal EP,
all promotions and castles, repetition/halfmove context, incremental HCE,
PVS/QS, history/continuation/correction and full-key coherent TT remain exact.
HQ is an actual search backend. No core feature or legality boundary is removed.
DEV source paths remain present but this closure builds DEV=0 only; it does
not establish a new DEV identity, equality or general race qualification.

Before clone, main runtime-stores WORKERS into zero-initialized pending. Worker
arrivals release-decrement it; successful startup waits for zero. GO stores
WORKERS+1 before epoch release. Each finished worker acq_rel-decrements once;
old==2 selects the final worker. It writes the result while pending is 1, then
release-stores zero. Main's acquire-zero condition gates replacement and normal
shutdown. The exact runtime complement retains epoch/quitting, partial-clone
failure bypass before the startup wait and created-only kernel CLEARTID joins.
Main returns after joins and start.S calls exit_group; there is no explicit
stack/TT munmap claim. These unchanged source contracts retain their separately
scoped ancestry, not a new startup-fault or universal concurrency proof.

## Fixed context format and restore boundary

`loader/codec.py` is the independent encoder, with its exact sibling
`range_bits.py` and `models.json`. The builder validates and copies every
loader source/model hash before importing the codec and its helper. Each
fixed scalar/HQ model has 21 ordered masks/weights. There is no model search,
training, alternative codec or external build dependency. The encoder applies
whole-file E8/E9 BCJ internally, including the ELF header, using file offset+5
and modulo-2^32 operands; callers do not apply a second BCJ.

The packet contains a little-endian u32 coded length `8*N+1`, a u32 weightmask,
21 mask bytes, integer arithmetic-coded body and **four actual zero tail
bytes**. H24 selects a 32 MiB pair-counter table; base probability is 10.
Software reflected CRC32C uses raw state without initial/final XOR. Local byte
history, prefix, ordered alias updates and unsigned-byte wrap match the decoder.
The fixed u32 length supports both native inputs; it does not inherit the
reference loader's 16-bit HQ length limitation.

| Form | Packet | Header | Arithmetic body | Real zero tail | Other whole bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scalar | 5,034 B | 29 B | 5,001 B | 4 B | 1,367 B |
| HQ | 5,247 B | 29 B | 5,214 B | 4 B | 1,367 B |

The complete file includes actual ELF/PHDR headers, entry, decoder, inverse
BCJ and packet. Its 1,367 nonpacket bytes are measured, not an old-loader
estimate. There is no libc, external decoder, compiler, interpreter or helper
at engine runtime. Encoder build-time RAM is distinct from engine TT resources.

The loader first rejects READ_IMPLIES_EXEC and reserves the exact guard range
with MAP_FIXED_NOREPLACE. Native output pages become RW for bounded decode.
A separate kernel-zero anonymous 32 MiB RW context table lives only through
decode; checked munmap precedes inverse BCJ and native entry. The native pages
then become RX and separate untouched BSS pages RW. No RWX mapping is requested.
`decoder.h` is independently written project source; upstream code is not vendored.

| Form | Native entry | RX at `0x400000` | BSS | Upper guard | Reservation |
| --- | --- | --- | --- | --- | --- |
| Scalar | `0x401e28` | 2 pages | `0x402000` | `0x42d000` | `0x2f000` |
| HQ | `0x401f5a` | 3 pages | `0x403000` | `0x42e000` | `0x30000` |

Both have 175,092 B BSS within 43 pages, lower guard `0x3ff000`, NX stack and
outer loader at `0x10000000`. `packer.admit` retains the exact per-form native
SHA, header/PHDR, entry and geometry literals. This is no general two/three-page
or unknown-image permission. Historical experiment guards remain unchanged.

The audit's only conditional branch is immediately before `enter`, after
successful context-table unmap, inverse BCJ and final RX/BSS protection. It
sends self SIGSTOP before native initialization or worker creation. CHECKPOINT=0
removes the branch entirely and must reproduce both selected full shipping SHAs.
CHECKPOINT=1 is a separately pinned image, not a production entry size. The fresh
positive observer read restored RX/padding and initial zero BSS, then resumed
original entry. The separate earlier production receipt does not prove that
initial state; the four new positive audits do.

| New audit form | Complete bytes | Full SHA-256 |
| --- | ---: | --- |
| Scalar CHECKPOINT=1 | 6,424 B | `07f0a624c85bec6a716cf40a738d6a455c555d6ea230528a4c531ae9d084b59f` |
| HQ CHECKPOINT=1 | 6,637 B | `854595138f823be31da5d189161ed7e7e802ee8f5dc836c7c534949f9dea3a6f` |

Discovery performed two independent own encodes and four loader compiler
commands: two shipping images plus two audits, each once. Both shipping full
SHA values remained unchanged. Audits contain 176 B ELF/PHDR headers, 1,214 B
text and the same exact 5,034/5,247 B packets, without other allocated data or
padding. Each has one RX segment at `0x10000000`, entry `0x100000b0`, matching
file/memory size and a separate NX-stack header. The discovery stage itself had
zero target executions; the subsequent fresh invocation and four positive
audits are separately bound above. The discovery receipt is `393353335e870d9ef6580e82f1231cf71da0fe4d6c7f1c21586fa8b6d8b2a4b0`.

## Normal source producer and closed verification

On qualified Linux x86-64, including WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-d/build.py --out /absolute/new/external-build
python3 -B engines/compact/tiny-entry-d/fresh.py --out /absolute/new/source-proof
python3 -B engines/compact/tiny-entry-d/verify.py \
  --build /absolute/new/external-build/build.json --out /absolute/new/physical-proof
```

Only the new external output directory is configurable for the build. Native
GCC -Oz/-flto flags, five-unit order, linkers and section-metadata stripping
are fixed. Qualified tools are GCC 13.3.0, binutils 2.42 and Python 3.12.3;
actual versions are recorded and any environment must reproduce the literal
bytes. CRLF input is explicitly normalized to LF and lone CR rejected.
`.gitattributes` retains LF. No zlib or third-party Python package is required.

Each build compiles each native twice, encodes and compiles each shipping whole
twice, and compiles one separate audit per form. Full native, packet, whole,
nonpacket and audit identities must match literal recipe values. Fresh enumerates
**21 local sources plus oracle/LICENSE: 23 ordinary archive members**. It checks
raw/normalized hashes, member set and safe regular paths, then uses two closed
extractions with separate isolated Python processes. Actual native/whole/audit
bytes matched across extractions. Actual full fresh cost was eight native
builds, eight shipping loader builds, four audit loader builds, four compiler
metadata commands, eight production sessions and four pre-entry audits.
Failures preserve incomplete reports and clean only owned process groups.

The unchanged physical observer distinguishes `/proc/PID/exe` as complete own
ELF from the restored anonymous native RX. It checks full RX/hash/padding,
guards/NX/W^X, exact native/layout, startup TIDs, stdio/no children, independently
legal clocked results and output/reader/process settlement. Its separate
CHECKPOINT consumer requires initial BSS/padding zero. The metadata policy check
does not rerun ignored-control/default-budget arithmetic, games or performance.
No RIE/ptrace mutations or negative decoder fixtures are part of this integration.

## Evidence boundaries

The context first-cost index SHA is
`199e5df9b91cce82ae81f19ab0fa4726bfe92bb5c8525e2c11177974cb44aa49`.
Its separate production runtime index is
`d2e7d4802ffbbca2d9f3f49bdcd8da3732732bce4b733c6492b3f9393d38b269`,
actual report `dad61bc39bc3ee777fcbef79081a78a786f7fdeb8e27990c3cd510ccd1d3bc82`.
Four exact whole sessions (scalar/HQ x quit/EOF), twelve legal results, native
RX/permissions/guard observations, persistent three TIDs and natural cleanup
passed. At eight local snapshots no extra writable interval of at least 32 MiB
was observed; that is not a causal context-address/unmap observation. No initial
BSS, CHECKPOINT, new startup fault or RIE/ptrace result is claimed by that report.

Independent encoder summary SHA is
`22b968d719c56e7cb92da79a178263f627c0fed866567d276631dc27b666d4b8`.
It produced both exact packets from the native inputs and the independent C
diagnostic restored exact BCJ bytes with canary/protection/lifetime checks.
That bounded decoder diagnostic is separate from full own-ELF runtime proof.

The unchanged Board/search pair remains
`e19749eb3315253e04171b89b8188df7e0db6b39ec4eb495187a6e158836823f` /
`48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c`.
Their normalized search and independent board receipts remain
`e06e27d4c8c42e4db819afe3b8ab702a4fe61f0d9636e102efd05a4ea5ab2539` /
`c123692a26644738f31e0d3710161b44a37aaefb40517b5ec6843a88606110bb`.
They are exact-source ancestry, not newly executed here. Prior completion-latch
publication, finite arithmetic and runtime complements are likewise separately
scoped under recipe metadata. **Old fixed-Huffman audit/decoder-fault receipts
remain old-decoder ancestry and do not qualify this context decoder.** No broad
fault, game, strength, scaling or universal race claim is added.

All generated files, archives, packets, transcripts and receipts stay outside
Git. Only the 21 maintained source/data files form this local source closure.
