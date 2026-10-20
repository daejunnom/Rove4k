# Maintained C D atomic128 TT own-ELF entry

The selected source uses aligned 16-byte full-key/payload TT entries. Concurrent
slot access uses the reviewed two-instruction CMPXCHG16B path: one coherent read,
then one conditional publication CAS for a write, with a changed slot allowed
to drop the write. There is no lock flag or retry loop. A write attempt is not
an acknowledgement. Entry size falls from24 to16 bytes; TT_BITS18 remains fixed,
so the anonymous TT mapping falls from6MiB to4MiB. Fresh mmap zero state replaces
only shipping startup clear; DEV wait-then-clear remains quiescent.

The execution profile is linux-x86_64-sse4.2-cx16-crc32b-v1. The verifier requires
sse4_2 and cx16 on every CPU in the inherited affinity before any target launch.
This local exposed-feature admission does not establish generic x86-64 or
current tournament-server compatibility. The earlier official4K wiki request
returned429 and remains an unsuccessful rules/CPU check.

Measured first-cost identities, including complete headers/loader/packet:

| Form | Native | Packet | Complete own ELF | Change from prior normal | Nonpacket |
|---|---:|---:|---:|---:|---:|
| scalar-shipping |7932|4927|6064|−44|1137|
| hq-shipping |8288|5116|6253|−35|1137|

Scalar native SHA890cf9a47918f3525ae8340999d5f1d0a9a34f51f9f4ed21b01fd6472fe2f96b;
whole SHAef992be19acbf77b8942c19bf98cd81f92a310be03e5d4ee290595ae3886ef88.
HQ native SHA84261c1153d1e0d71b3241375423cf8a6ffc386a6058380a1b14abfc6d757efe;
whole SHAa03667db1839b238c217968a35883bf99d2b32fb82f9f475c2e8c8dd8814222c.
Both text sections shrink39B; complete native changes32/64B include alignment.
The first-cost complete files are6064/6253B, not4KiB entries.

The packet codec remains rove4k-context-h24-base10-fixed21-replay-zero4-v2.
CRC32 byte instruction, fixed21 WMASK replay, models/range arithmetic,
BCJ, zero4 sentinel, full decoded bounds, loader sources and both linkers are
unchanged. Two existing positive DATA helpers decoded the new packets to exact
native images with canaries and owned32MiB table munmap. They did not enter the
native images. Compiler flags, scalar/HQ algorithms, HCE, full64key/payload
packing, mate/bound/context handling, learning, WORKERS2 and PLY128 remain fixed.

Scalar restores RX2 at400000/BSS402000 and entry401d70; HQ RX3/BSS403000
and entry401ead. Both BSS175092B round to43pages. Exact reserve/guard contracts,
NX stack, initial zero BSS, private decoder-table lifetime and RW→RX stay fixed.
Both worker stacks retain private1MiB plus guards. The verifier lifecycle and
mapping observer bodies are unchanged; only literal candidate identities and
all-affinity CX16 admission are updated.

Finite-minimum UCI policy is unchanged: uci/isready/position startpos moves/go
clock/quit/EOF, without optional id/options. Shipping consumes stop/ucinewgame/
infinite without DEV semantics. Missing own clock gives1000ms budget, not a
hard wall-time cap. Next go, position, quit and EOF wait for pending0 after
complete output. Persistent clone/futex ownership, partial-create shutdown
bypass and kernel clearTID joins remain unchanged.

The ordinary positive TT unit includes the actual unchanged probe function.
One C compile and one bounded run passed full-key/payload vectors, mate/bound
packing and a finite two-writer/one-reader coherent-pair check. Joined writers
and an uncontended final publication were checked. Contention-drop causality,
general race freedom, SMP scaling, playing strength and performance were not
established. The first Python driver failed to parse before any C compile/run;
its source/error is preserved separately. The corrected driver performed the
sole actual C compile/run, not a retry of a failed TT unit.

Before this normal edit, current source23 and both complete authoritative prior
normal build directories were copied and checked outside Git. Prior normal
native7964/8352, whole6108/6288 and audit6131/6311 observations remain predecessor
evidence. The earlier CRC audit-discovery driver terminal1 failure, despite two
compiler0 outputs and an inaccurate raw complete:true, is preserved unchanged;
the separately successful closed normal fresh does not repair that failure.

Root independently read the actual native/packet/shipping/audit files, ELF
headers, source diff and discovery receipt before admitting the two exact audit
identities: scalar6087B SHA9e8831581ee618d9ecb99373ee8eb39c312d7a7e696ea569e1b3a56e694cc07c;
HQ6276B SHAdb6cdcfa09b94f0d9441384f5646678258d5e7cbeeaa9537ca149127f663985e.
The original strict admission gates remain in place. Root intake SHA is
c5d89d6a28d612c7f7b4d02ec5af8907c88d2b8a1c3d27d560c5420f883b07d2.

One existing normal builder invocation completed terminal0: native4,
shipping-loader4, audit-loader2 and encoder4 reproduced the exact selected
files. One selected positive verifier invocation completed terminal0: shipping
quit/EOF4sessions with12GO and positive pre-entry2 passed. Every available local
CPU0..7 exposed CX16 and SSE4.2. Restored native/RX padding and initial BSS/
paddingzero, guards/NX and original entry resume were observed. Shipping
retained three startup TIDs, private guarded1MiB worker stacks, onlystdio,
no helpers observed, legal white/black/active results and natural reader/
process/group settlement. All recorded target TIDs were absent on readback;
forced cleanup0. No fresh invocation or negative campaign was run.

Normal build SHA12c7096e312e4ed3d6761da81569eb222b54f8c99556eef3bef566c203bcf1a8;
positive verifier SHA f4536e49cf9276a123a8954c91a12a4bfe9060cb3cd4387b597006dda017059a;
readback SHA ff696c24deebd1758401ace9439f4897f93d2548b88e440d54496c23316105c3.
Producing source23 index SHA7cd4680e1e5a259b4864a85eed02a9fbd3c421e6740230ee9c28151ce6dd2880,
recipe SHAc80654a02beae7e16cdb5a6311251a267409e1fc19150cdfc7eae23495ef402d,
verifier SHA215ababe7abba67f29687b2a1da6e0e204a777f20c0712b95e6d86f91c7081df.
After that execution only this README and recipe qualification metadata were
overlaid; all19 other local files and producing recipe fields stay exact.
The unmodified builder does not separately observe compiler descendants/groups.
These checks do not establish ignored-control/default-budget timing, exact
decoder-table unmap causality, general TT/SMP race freedom, strength or performance.

The closed normal source stays21 local files plus oracle/LICENSE=23. Unchanged
loader, codec and physical-helper source is reused; old runtime receipts are
not relabelled as new runs. No negative/fault/RIE/ptrace/register/personality,
game, benchmark, training or paid-resource campaign is part of this work.
