# C D full-key atomic16 TT fixed cost

One aligned16-byte Entry stores the full64-bit key and full64-bit packed payload.
Two single-instruction GNU asm volatile templates use lock cmpxchg16b with +m
for the entire Entry, +a/+d expected/observed pair, b/c desired pair and cc/memory
clobbers. The first compares/writes zero to obtain a coherent pair. A write makes
one CAS against that pair and drops a conflicting publication without retry.
All concurrent TT cell accesses remain inside these asm blocks. The read's
write-cycle requires the existing RW mmap. Layout/offset static assertions bind
key0/data8, size16/alignment16. Linux x86-64 SSE4.2+CX16 is mandatory; no runtime
CPU admission, TT execution, race/functional qualification or generic ABI claim.

The anonymous mmap is kernel-zero before clone. Plain uint64_t fields need no
C11 atomic_flag object initialization, so shipping startup clear is removed.
DEV ucinewgame still executes wait();clear() and clear memsets the new full table
only at quiescence. Slots remain2^18 and workers2/PLY128; table bytes change from
6MiB to4MiB. Full key/context, mate/bound/depth payload, search/learning and finite
protocol stay source-exact outside the private probe and initialization changes.
Read hits/contended write outcomes can differ from the old try-lock TT; no byte-
equal semantics claim is made. ABA is harmless for this replacement cache: every
accepted publication still has one coherent full key/payload pair.

Existing scalar native7964/HQ8352 and whole6108/6288 are immutable read-only cost
controls from the authoritative normal fresh. Old scalar startup clear has a
37-byte loop at40179f..4017c4 plus setup, but added register pressure/atomic16 code
can absorb that saving; no guaranteed reduction. Only one native and one fixed21
CRC loader cost per form are authorized, with generated files outside Git. The
positive decoder helper treats candidate native solely as data. It never enters
the TT/engine. No target/ASM fixture, negative, RIE/personality/ptrace/register,
normal promotion, games, benchmark, training, AWS or paid resource is authorized.

Primary contracts: GCC Extended Asm and x86 constraints; Intel SDM CMPXCHG16B.
These are GNU implementation/ISA contracts, not portable C11 atomic operations.
https://gcc.gnu.org/onlinedocs/gcc/Extended-Asm.html
https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2a-manual.pdf
