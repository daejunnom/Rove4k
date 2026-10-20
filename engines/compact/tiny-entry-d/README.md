# Maintained selected C D context own-ELF entry

`native/` contains the readable raw-syscall chess engine. `loader/` contains
the project-owned guarded restorer, independent integer context decoder and
standard-library Python encoder. `recipe.json` pins ordinary source bytes,
compiler/linker order, resources, finite public policy and exact
native/payload/whole/audit identities. Generated files belong outside Git.

The selected integration moves each job's best reset into its worker and
replaces inverse-BCJ four-byte gather/scatter with fixed-size builtin copies.
All seven other native sources, the encoder/decoder/model, both linker scripts,
resources and compiler/linker flags are unchanged. The normal producer reads
only maintained ordinary source, the installed compiler and Python standard
library; experiments, reports, historical native files and packets are not
normal build dependencies. The root MIT license applies.

| Fixed form | Native ELF | Complete own-ELF | Complete SHA-256 |
| --- | ---: | ---: | --- |
| Scalar | 8,060 B | **6,313 B** | `66f70074da2270f1d6aa33beb50c1f34038b4bc36e4272d748c1720935fb4a9a` |
| HQ | 8,448 B | **6,506 B** | `7ba4858dcf40c837d107f865e14b82d19ede40570059dcff1ca4bd3012ff7234` |

Both exceed 4,096 bytes by 2,217/2,410 bytes. The complete files save88/108B
against the preserved6,401/6,614B context controls. This is an actual combined
whole-file comparison, not a sum of predicted source or text savings. No
event eligibility, playing-strength, throughput or scaling result is claimed.

## Two bounded source changes

Runtime source15027B SHA
`51902e800066562f7dbc5d240db57a6635b20c74ed8fede3a4cd71329fc62a38`
differs in exactly two fragments: remove go's all-worker reset loop, then set
`w->best=0` after accepted epoch/seen checks immediately before unchanged
think. Think already resets nodes/depth/score. Direct think callers retain
their seeded-best API because think itself is unchanged.

Each worker initializes before its completion decrement. The last worker's
acq_rel pending transition2→1 acquires the earlier worker's field publication;
pending1 reserves output. Only output completion then release0/main acquire0
allows another position or GO to reuse storage. Shutdown/quitting, partial
startup failure bypass, guarded stacks and kernel-CLEARTID joins are unchanged.
The runtime is new code, not an object-identical spelling substitution.

Loader source2997B SHA
`ea574f09aefc0f910a64c683c7052482d3b2e0c52a10f09450233b155674a85c`
changes only little-endian u32 gather/scatter to `__builtin_memcpy` of
`sizeof value`. Fixed x86-64 codegen review observed exact four-byte inline
memory access, no helper, the same modulo32 correction/opcode/skip/bounds,
and unchanged surrounding syscall/error boundaries. Compiler output and
full-file SHA gates retain that fixed-target contract.

The worker-reset actual receipt
`bb01f2daf8960b73a2cb81b51776249d0ac25b5aca98c1d1f2754953d4894476`
and independent readback
`3c41877ef872e84fa03c30ccfd05866f5904ac190ce2058eeef6a7733a8e79b8`
cover six shipping sessions/16 GO of this native with the previous loader.
Four production sessions covered repeated roots and active quit/EOF. Two
publication sessions observed actual pending1/main futex/blocked worker write,
then ordered legal results and pending0/natural exit. Three zero-clock GO and
one bare GO were used; bare GO was followed by a position fence. These do not
observe private zero-iteration state, first-node deadline causality, natural
default-budget expiry or general race freedom. They qualify new-native
post-entry ownership, not this new BCJ loader's restoration.

## Closed reproduction and current qualification stage

Old ordinary21/archive and20 actual native/whole/audit outputs were preserved
before integration. New CHECKPOINT1 images were built externally for literal
identity discovery only, with no audit/engine execution. Their fixed identities
are scalar6336B/93df62352f49aee0d01e4022c6a7acc773593255dfa252c28a200d3e521df905 and
HQ6529B/9bf7165d3840488c9cdd674caa2e7cb2379c6d6eed917005cd8ce2d48129a8fd. They are separate from shipping images and
from all historical old-decoder/context audit identities.

One unchanged normal fresh invocation completed with two independent closed
source extractions. Local21 plus oracle/LICENSE make23 ordinary archive members.
Both extractions reproduced actual native/payload/whole/audit bytes exactly:
8 native,8 shipping-loader and4 audit-loader compiler commands plus4 metadata
commands succeeded. The unchanged verifier passed8 shipping sessions/24GO and
4 positive pre-entry sessions, including exact restored native RX/padding,
initial BSS/padding zero, guards, NX, resume and natural reader/process cleanup.
There was no target forced cleanup or retry. Compiler commands returned zero;
compiler descendant/group absence was not separately observed by the unchanged
builder. Exact input native and restored RX identities remain distinct from
`/proc/PID/exe`, which names the own-loader ELF.

The actual producing source21 set is
`222aaaf8a893e6c0fbec63039d0958357c780fc8b6d567337aed3eecedf31b11`,
recipe SHA`74d179d61c96b33777054f5928384c4e30dfbbdf638fef17358aa11fe6450d54`,
and closed source23 archive
`f8a86aca8e0632d34f10d9a99d53b9ad6382e76420264853158b1b899ae010c6`.
Fresh receipt is
`e4838c7aeed82688983244a1fb91f85c570e35a51433570015f20d4d2aa20c0c`,
actual readback
`af3dc55b006c4bc1ad7bd3a09a63b2aeaf6c0f53a58d01edfcb6c2603607194a`,
and independent frozen source/literal/audit review
`e602fc2760fb38385db008142e647e6cfd35ad41fa9c012a28ae7a57e097ca52`.
Only README and recipe qualification metadata changed afterward. The actual
producing closure remains frozen separately; this final explanatory overlay
was not run as a second fresh. All producing code, expected image identities,
flags, profile and source pins remain exact.

```sh
python3 -I -B engines/compact/tiny-entry-d/build.py --out /absolute/new/build
python3 -I -B engines/compact/tiny-entry-d/fresh.py --out /absolute/new/fresh
```

Build expects literal source/native/packet/whole/audit hashes and fails on a
mismatch. It never discovers or accepts a new expected hash automatically.
Normal admission binds each of two exact native identities to its own exact
per-form entry/PHDR/RX/BSS/guard/reserve geometry. Historical experiment guards
remain unchanged; this is not permission for arbitrary two/three-page images.

## Fixed policy, resources and restoration boundary

Shipping implements uci/isready, startpos legal move histories, clocked GO,
quit and EOF. uci emits only uciok; no optional ID/options are shipped. stop and
ucinewgame are consumed without cancellation/TT clear, and infinite is an
unsupported consumed token. GO is finite: absent own clock uses1000ms; present
zero/invalid own clock uses at least1ms under the fixed formula. This is a
search budget, not a hard wall-time cap. Position/nextGO/quit/EOF request stop
and wait for pending0 after output before storage reuse. Input replay remains
transactional. This is the project's minimum TCEC4k policy, not general TCEC UCI.

WORKERS2/TT_BITS18/PLY128/DEV0 remain fixed. Two persistent startup workers,
coherent nonwaiting full-key TT, legal all-four promotions, HCE/PVS/QS,
history/continuation/correction, draw/halfmove/legal-EP context and PLY abort
remain in the unchanged board/search/HQ complement. No new DEV equality,
fault matrix or broad core/game/strength result is claimed for this integration.

Scalar native is8060B/SHA381fd1f478b090372365371d39337920c11fee4ab04ed59ab8616d0286b125d1,
entry401dfe/RX2/BSS402000/upper42d000/reserve2f000. HQ is8448B/SHA
215ee72678b41032e7f3283bf40fda752f385833df46d2b430bfc2d5c5f89008,
entry401f30/RX3/BSS403000/upper42e000/reserve30000. Both retain175092B
zero-file-byte BSS rounded43pages, lower guard3ff000 and NX stacks.

The context stream is fixed H24/base10 with21 models, u32 coded length,
software CRC/local history/seed update and a real four-byte zero tail.
Packets5020/5213B SHA4aecde84c170d0be88d3110d9854494d453c9773235f18cb008b54eb40dfd919 /
2a47024e48caec8065c593f42b3026731faf0131c85cea664c402fe04d55f019
include29B header and4B tail. Encoder applies BCJ once over the native file.
Actual ELF/header+loader overhead is1293B. Loader allocates a private32MiB
kernel-zero RW context table, checks decode and munmap, then reverses BCJ,
applies native RW→RX and separate BSS RW protections, and enters native code.
CHECKPOINT stops after these steps and before native BSS initialization or
worker creation. The fixed guarded policy never requests RWX and rejects the
existing READ_IMPLIES_EXEC condition. No RIE/ptrace/register/personality
negative or new fault campaign is part of this promotion.

Recipe qualification hashes are metadata only. Old core, raw-kernel and
old-decoder receipts remain explicitly scoped ancestry. Final README/recipe
qualification metadata is a separate explanatory overlay after the one
successful fresh run; the actual producing recipe/source/archive remains
frozen and that overlay is not a second fresh execution.
