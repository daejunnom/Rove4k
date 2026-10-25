# One bounded context decoder and complete own-ELF first cost

This experiment independently implements one H24/base10 arithmetic-context
decoder. No upstream implementation or executable is included or invoked by
these sources. The format was studied from fixed external reference sources;
the preserved original compressor was used only for the separate reference
codec campaign. This folder is not a maintained closed native/encoder recipe.

`decoder.h` is project-owned C with software CRC32C, full-width context-table
addresses, a u32 output-bitlength field, and four physical zero tail bytes.
Header/mask/bit reads are bounded by the actual supplied end. Models are
limited to 21 and weights to 9; the arithmetic product is 64 bits. Counters
have byte-wrap updates, a boost for a zero counter, and one update per model
even when multiple contexts collide. All model probabilities are collected
before any update. The interval state is a relative code and range.

Local history and prefix state consume the first coded 1 sentinel separately
and write exactly N real bytes. Neither the preceding guard nor out[N] is
used as history or prefix storage. The table supplied by the caller must be
zero and exactly 33,554,432 B. The decoder does not allocate, call libc, use
SSE4.2, or require another runtime program.

`diagnostic.c` includes that same decoder header and checks two exact frozen
u32/zero4 streams against the actual BCJ native bytes. Input, output and table
buffers have PROT_NONE guard pages; input/output buffers are aligned to their
right guard and output's preceding page padding is checked. This is a decoder
diagnostic, not an engine execution or proof over arbitrary inputs.

The parent dispatches the complete-ELF cost producer only after both actual
decoder diagnostics pass. That prerequisite is recorded externally; build.py
does not claim to enforce a historical diagnostic receipt itself.

```sh
python3 -I -B engines/experiments/tiny-d-context/build.py \
  --inputs /absolute/frozen-reference-data \
  --out /absolute/new/context-whole-first-cost
```

The input directory contains only the pinned `scalar-shipping` and
`hq-shipping` native/original.paq data files. Both native images are unchanged
qualified maintained D controls, not the unselected TT payload-lock candidate.
The producer checks the complete native identities and exact PHDR/entry
layouts, checks the original stream identities, and prepares u32 framing plus
four actual zero bytes. It never runs a compressor, compiles an engine,
updates expected identities, or executes either completed ELF. The prepared
payloads are 5,034 B scalar and 5,247 B HQ, including length/model headers and
the physical tail. Existing 1,115 B decoder overhead is not added as an estimate.

The two fixed loader compilations retain the existing -Oz/LTO loader flags
and exact project-owned linker bytes. `loader.c` retains the guarded restore's
READ_IMPLIES_EXEC rejection, MAP_FIXED_NOREPLACE reservation, RW-only native
decode, inverse BCJ, checked RW-to-RX transition, separately writable zero BSS,
non-executable stack and original entry/stack handoff. It adds one anonymous
RW H24 context mapping and a checked munmap before native entry. It has no
writable globals and makes no RWX mapping. No CHECKPOINT or engine run is part
of the first-cost campaign, so these are source/ELF contracts rather than new
observed process mappings or lifecycle qualification.

Every complete output counts its real ELF header/PHDRs, compiled decoder and
restoration text, metadata, zero tail, arithmetic body, constants and padding.
The static ELF shape and component arithmetic are checked against the actual
linked and stripped file. A smaller payload alone is not a complete-ELF result
or 4 KiB qualification. Native source, full-key TT, legal board/search/HQ,
clocks, two persistent workers, TT_BITS=18 and the original BSS geometry remain
unchanged. Source, tool and input provenance, any preparation/runtime failure,
commands and outputs are recorded externally. No source-profile, flags, model,
table-size or code-layout sweep is performed.

External frozen stream data are explicit experimental diagnostic inputs, not
a new normal build dependency on upstream code or executables. A maintained
closed producer still requires a project-owned build-time encoder and its own
source/reproduction qualification. No broad safety, performance, strength or
submission-size claim is made by this experiment.

## Observed first cost and limited decoder proof

The single libc diagnostic compilation and its two guarded valid-stream runs
passed without a source correction or retry. Scalar decoded 5,034 B to the
exact 8,092 B BCJ image; HQ decoded 5,247 B to the exact 8,480 B BCJ image.
Both returned zero, matched all output bytes, retained the prefix canary and
read-only input, and released all three guarded allocations without errors.
The diagnostic source includes the same frozen decoder header. This is not a
run of the completed -Oz/LTO own-ELFs or a malformed-stream corpus result.

The subsequent two loader compilations each ran once. Actual complete files:

| Component | Scalar | HQ |
| --- | ---: | ---: |
| ELF header and two PHDRs | 176 B | 176 B |
| Decoder and guarded restoration .text | 1,191 B | 1,191 B |
| U32 length, weightmask and 21 model masks | 29 B | 29 B |
| Arithmetic body | 5,001 B | 5,214 B |
| Physical zero tail | 4 B | 4 B |
| Other rodata / alignment | 0 / 0 B | 0 / 0 B |
| **Complete own-ELF file** | **6,401 B** | **6,614 B** |
| Previous qualified complete file | 7,457 B | 7,707 B |
| Actual whole byte change | **-1,056 B** | **-1,093 B** |

The measured nonpayload cost is 1,367 B. This replaces the old decoder rather
than adding an estimated old 1,115 B overhead to the new stream. Both outputs
remain above 4,096 B: 2,305 B and 2,518 B over the limit.

Scalar whole SHA-256:
`7e8f405c40ae5a64f3420f23d77a179d4154e5b9bd9e9c67aea1c83a18d238da`.
HQ whole SHA-256:
`be6a45a21895b204550cc0ae7a9a73928d6f4df1313757bad68db4dd97c4f358`.
Each actual outer ELF has entry 0x100000b0, one RX PT_LOAD at 0x10000000 with
filesz=memsz equal to its complete file length, and a non-executable stack
PHDR. It has no interpreter, writable globals, file-backed data, section table
or W+X segment. Native target geometry and exact native identities remain the
original per-form literals. These are static observations; neither completed
ELF has been executed or repeated for byte reproduction in this campaign.

The external guarded diagnostic receipt is SHA-256
`121677440a2b1beb9e775a84bf52bbbefff308ac4966bca3fe71772a30f4442f`.
The original complete-file cost receipt is SHA-256
`432ec934af089db4d23edf4c3b269ee5e86941634aeb77e88f037c96f232f7a9`.
All commands exited zero and required no forced cleanup. Producing source8,
both actual linked/stripped files, payloads and command records were preserved
externally before this README-only annotation. An execution-preflight review
also corrected failure-state reporting before any command was run. There were
no actual diagnostic/build failures or retries and no new flags or variants.

Runtime restoration by the actual own-ELFs, pre-entry maps/BSS observations,
engine startup/GO/quit/EOF qualification, strength, startup speed, hardware
scaling and maintained closed-source reproduction remain outside this result.
