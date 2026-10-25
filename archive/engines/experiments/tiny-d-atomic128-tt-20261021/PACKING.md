# Fixed21 CRC cost stage for the exact atomic16 candidate

Native producing source13 remains immutable. The six current maintained loader/
encoder/model sources are copied without changes. candidate-packer.py is a
separate literal class: only two native hashes/sizes/entry literals change in
its native admission and native/model mappings; its W^X, BSS, guard geometry,
ELF stripping, loader compile flags/macro order and class conditions stay exact.
The unchanged reference/packer.py remains a separate snapshot, never broadened.

Two candidate packets use the original ordered21 models/WMASKs and fixed21 CRC
format. Each exact native is admitted before packing. Existing control whole
6108/6288 files are only read and hashed; no control recompile/reencode/relink.
The actual new whole contains headers+CRC loader+packet. Existing exact positive
data decoder binaries are pinned with historical source/compile receipts and
reused once each with128MiB AS/10CPU-second/30wall-second limits. They treat the
new native as bytes, compare packet→BCJ bytes, inverse native bytes, canaries and
table munmap, and never call the native entry or execute its TT assembly.

This stage is cost plus data-codec diagnostics only. No engine/TT/ASM fixture,
startup race, target negative, RIE/personality/ptrace/register, game, benchmark,
normal promotion or playing-strength claim. Future target admission must require
CX16 in addition to the existing SSE4.2 loader requirement. No variants/retries.
