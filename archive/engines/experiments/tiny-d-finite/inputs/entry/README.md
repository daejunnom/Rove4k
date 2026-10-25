# Maintained selected C D own-ELF entry

The readable native program lives in `native/`; the selected project-owned
self-restoring loader, linker and build-time codec live in `loader/`.
`recipe.json` records fixed compiler/linker order, resource constants, source
hashes, admitted layouts and expected complete-file identities. Edit maintained
source deliberately; do not edit generated native images or compressed payloads.

This promotes source ownership and reproduction only. The native algorithms,
scalar/HQ backends, protocol parser, raw Linux runtime, persistent startup pool,
TT, resources, loader, codec and layouts are exactly the already qualified
`tiny-d-compose` selection. There is no optimizer, codec/preset/flag search or
new image admission. No external engine or decoder source is copied; the root
MIT license applies.

| Fixed profile | Native ELF | Complete own-ELF | Complete SHA-256 |
| --- | ---: | ---: | --- |
| Scalar | 8,476 B | **7,640 B** | `2147bd4e56915196ade254c05b587cffd2cbc5c5355ad1f9f1daeda3df4d575f` |
| HQ | 8,864 B | **7,881 B** | `051ec52baaac55fd1fd8f80af6bea0d74a1e852f8672ef52237bb06a7d994c0a` |

Both exceed 4,096 bytes: by 3,544 and 3,785 bytes. This folder makes no event
eligibility, playing-strength, throughput, scaling or cross-toolchain claim.

## Source-only fixed build

On the qualified Linux x86-64 environment, including WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-d/build.py --out /absolute/new/external-build
```

The only option is the new absolute external output directory. The builder
reads this folder's ordinary maintained source and recipe, plus the installed
compiler/Python standard libraries. It does not read an old experiment directory,
report, generated image, dependency tree or network resource. Historical receipt
hashes are metadata only. No executable or compressed payload is stored here.

Workers are fixed at 2, TT_BITS at 18, PLY at 128 and DEV at 0. Both search
workers and the input thread exist at startup. The native source retains the
already selected protocol, including its existing stop/newgame/infinite behavior;
the later minimal A consume-only policy is not applied. Board legality, legal EP,
all promotions/castles, repetition/halfmove state, incremental HCE, PVS/QS,
learning, ordered TT context and full-key coherent TT are unchanged. HQ remains
an actual search backend rather than an unused demonstration.

Native compilation retains GCC `-Oz -flto`, the exact previous static/raw
syscall flags and five-unit order, `native/image.ld` and existing section-header
stripping. Source paths and output paths are the only substituted command
arguments. Both native images must equal their selected SHA-256:

```text
scalar ba2d42473ca25a944b85da18f74f32eae18e68112010948a0e7c2dc0c69a7c5c
HQ     09917666d5862c4f17ed77e33453000f608a7d83aa47f16f8726a063ec5f31ce
```

The fixed loader uses the unchanged E8/E9 BCJ plus one-final-fixed-Huffman
Deflate recipe. Payloads are 6,525 and 6,766 bytes. All ELF headers, decoder,
inverse filter, ABI guards and configuration add **1,115 bytes**; the complete
sizes above count all of them. `loader/codec.py` is the exact original codec
source, including its build-only unused alternative helpers, and selects only
the already admitted `fixed_compress` path. Zlib is a build-time input, never a
runtime dependency. The full files require no libc, external decoder, compiler,
interpreter or helper process to run.

The admitted native mappings remain RX at `0x400000` over three pages, BSS at
`0x403000` with 175,092 bytes in 43 pages, inaccessible guards at `0x3ff000` and
`0x42e000`, a non-executable stack and the same original-entry ABI. Scalar entry
is `0x401f89`, HQ entry `0x4020c6`; the loader itself stays at `0x10000000`.
READ_IMPLIES_EXEC rejection, MAP_FIXED_NOREPLACE reservation, bounds-checked
decode and RW-to-RX restoration remain unchanged.

Every build compiles native twice and independently encodes/compiles each whole
file twice. Exact native, whole, payload and fixed-overhead identities must
match the recipe; decode roundtrip alone is not acceptance. The same prior
CHECKPOINT audit images are built separately to observe pre-entry state and
must also match their selected hashes. They are never counted as production
sizes. Failure leaves an incomplete report and owned command cleanup.

The qualified byte-producing environment is GCC 13.3.0, GNU binutils 2.42,
Python 3.12.3, zlib 1.3 and x86-64 WSL Ubuntu. The builder records actual tool
versions and zlib build/runtime versions. Different versions must reproduce
the expected bytes to pass; this is not an assertion of cross-version identity.
CRLF text is explicitly normalized to LF before hashing/copying/compilation;
lone CR is rejected. This folder's `.gitattributes` keeps maintained input LF.

## Closed archive and narrow physical proof

```sh
python3 -B engines/compact/tiny-entry-d/fresh.py --out /absolute/new/source-proof
python3 -B engines/compact/tiny-entry-d/verify.py \
  --build /absolute/new/external-build/build.json \
  --out /absolute/new/physical-proof
```

`fresh.py` explicitly enumerates 20 ordinary source members: this folder's 18
files, the root LICENSE and tracked independent `engines/tests/chess_oracle.py`.
It hashes and validates the exact archive member set, rejects links and unsafe
paths, and creates two separate closed extractions without Git or generated
files. Each extraction starts a fresh isolated Python interpreter and executes
its own local builder, then its own local narrow verifier. Repeated native,
whole and unchanged audit bytes must match across both extractions. The builder
itself is fully folder-contained; the oracle is needed only by verification.

`verify.py` uses the same admitted-image observation method as the prior
dedicated-loader proof, with explicit production image identities. This
loader restores into anonymous fixed mappings; `/proc/PID/exe` identifies the
**whole own-ELF**, not the restored native ELF. The native SHA is checked from
actual restored RX memory. The audit checkpoint separately checks initial zero
BSS/padding and entry handoff. Production checks cover immutable restored RX,
guards/W^X/non-executable stack, three persistent startup TIDs, only stdio,
no children, actual oracle-legal clocked play and physical quit/EOF settlement.
Command/result ordering is not a claim of cancellation causality.

Fresh source regeneration and these narrow physical observations are separate
from prior broad algorithm, codec fault, layout-admission, raw runtime fault and
shipping game evidence. Those prior results are reused only because exact
compiled source, native, loader and full images are unchanged; they are not
relabeled as new runs. The metadata binds the prior compose summary
`d98218c08f05a9e39af40016e731aba1d1b02846524a2fb412e45e02868aa0fc`,
build `86ab399d8a2732a4527db0290e01101c9b783c4f87f608c3c8db8ff23ed7540c`,
image proof `3dd9ef4cdee98201d39d3eb51675a31574e84b849cdc32cbbe9c7b838d6167f8`
and 10 shipping groups/two oracle games
`d224fb32e158bad3fcf997810ad96f6225c9b099c0e80a3bb01627fef0e9687a`.
The existing canonical TinyD and historical experiments remain untouched.

All build products, source archives, extractions, compiler diagnostics, runtime
transcripts and reports belong in new external output directories. This folder
contains only readable maintained inputs and their fixed regeneration/proof
tools. The final external index ties completed source/archive and physical
receipts to the current maintained-file hashes.
