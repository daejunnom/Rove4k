# D hardware CRC32 byte experiment

One independently written cx_crc replacement uses SSE4.2 CRC32 r32,r/m8.
It receives the original arbitrary32-bit seed and byte without a pre-XOR.
The generic selected normal decoder remains unchanged. This profile requires
SSE4.2; it is not a generic x86-64 binary or a runtime-dispatched fallback.

Only decoder.h's cx_crc body differs. Fixed21 replay, count/readend/zero4,
all-probabilities-before-ordered-alias-updates, wrap, original native/packets,
loader/flags/model/RW→RX/guards/BSS/NX/entry remain fixed.

build.py accepts one new absolute external --out directory. It freezes pinned
ordinary inputs before module loading. It executes exactly one CRC-only C
diagnostic first: zero,32 seed basis bits,8 byte basis bits, all256 bytes with
six fixed seeds,4096 deterministic random pairs,5673 comparisons in total.
The documented GF(2) reasoning complements those positive comparisons.

After that passes, each form gets one fixed shipping-loader compilation and
one isolated actual-packet decoder diagnostic compilation/run. Native and
packet inputs are full-hash checked existing closed artifacts; no native or
encoder rebuild/control compile/sweep occurs. Static objdump only decodes the
new loader's executable section. Actual C diagnostic output must equal the
entire BCJ image and inverse native, with bounded owned buffers/canaries and
one32MiB table released. Generated shipping ELF files are not executed.

One fixed execution passed. Scalar whole6165→6108B and HQ6345→6288B each save57B.
Packets remain4971/5151B and exact native outputs remain7964/8352B. Actual
overhead1194→1137B consists of the same176B ELF/PHDR and961B text, previously
1018B. Both .text sections contain two CRC32 byte-input/32-bit-output sites.

CRC-only5673 comparisons passed. Both actual packet diagnostics compared the
entire BCJ image and inverse native exactly, with output canaries and32MiB
table munmap succeeding. All10 commands (5 compiler,3 isolated diagnostic,
2 static objdump) returned0, owned groups were absent and forced cleanup0.
No candidate shipping ELF was executed. These diagnostic allocation/unmap
observations are not production mapping/restore/entry observations.

Shipping scalar SHA cce0f6e6c23c80721bfe514a433d7e65d76cf41f67f6aeb61bab354c65463f92;
HQ SHA f9f9297f8363b1863707df0e7eb7912e56d18788c64aa86998623b3f12ef3da0.
Actual results SHA b645ec13306c0f40ea7cd19be045fe140354482fa37f13434d0a2f6a7cd4b2c1.
Producing source6 was frozen before execution; this README result metadata
is the only post-execution source change. Recipe/producer/decoder/fixture
remain producing-exact. No repeat build or timing/strength claim is made.

This folder does not promote normal D or register a new normal admission/audit
identity. An explicit SSE4.2 profile decision and new positive shipping
qualification remain required. No shipping/audit engine, CHECKPOINT, fresh,
negative/fault/RIE/ptrace/register/personality, game, benchmark or training
campaign is part of this first-cost scope. Reports and all generated files
remain outside Git. Root owns Git and global documentation.
