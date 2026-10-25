# F atomic64 partial-tag TT: one cache-policy candidate

This is an explicit probabilistic TT identity policy change. It is not lossless
compression or full64-key equivalence. The normal full-key F4728 source/native,
wrapper and source22 closure remain preserved and unchanged. The engineering
contract permits a separately declared search/cache-policy change.

The exact current shipping source 9690/e0aa8dd9 becomes 9626/dd999295 (-64 B).
Only three literal spans change: Entry type, probe and startup clear. Exact
forward/inverse and the entire protected complement are checked. All board,
ordered-history and halfmove context-key formation remains full64 and unchanged.
The truncation is solely TT identity. Full-depth MTD driver, retained horizon,
score/mate conversion, bound consumption, root witness, stable HCE, learning,
cancellation and lifecycle code are not rewritten. Their behavior under false
TT identity hits requires new qualification; older full-key results are not
relabelled as this candidate's proof.

Readable equivalent policy:

```c
typedef _Atomic uint64_t Entry;
Entry *slot=table+(key&((1u<<18)-1));
/* tag = key>>43; data is the bounded actual 43-bit payload. */
if (data) atomic_store_explicit(slot, (key>>43<<43)|data, memory_order_relaxed);
else {
    uint64_t word=atomic_load_explicit(slot,memory_order_relaxed);
    data=(word>>43)==(key>>43)?word&((1ULL<<43)-1):0;
}
```

The actual caller always builds a 43-bit payload: move17, signed16 score,
depth8 (0..126), bound2 (currently 2/3). This valid caller domain is preserved
byte-for-byte, so a store's data cannot overlap the tag. Arbitrary 64-bit data is
not a new supported API. Queries extract tag and payload from the same single
loaded local word. Each write atomically replaces the entire word. There are no
plain shared key/data fields, try-locks or busy-slot misses. Relaxed operations
allow stale complete entries; they never claim freshness or a correct-position
bound for an aliased tag. Empty0 returns payload0 even for key tag0. All entries
receive atomic_init after allocation and before any worker is created. There is
no concurrent clear or early free; existing join/publication ownership is intact.

Index low18 plus tag high21 retains 39 effective key bits; bits18..42 are ignored.
Keys differing only in bit18 are a constructed collision. Under a uniform,
independent random-key model, conditional tag alias on an occupied indexed slot
is 2^-21, and a pair's index+tag match is 2^-39. These are not adversarial or
whole-search error probability guarantees. TT score/bound fields remain used,
so aliasing may change bounds, search, convergence or selected move. It must not
be recorded as exact collision rejection.

On the fixed Linux64 GCC LP64 profile the entry is one 8-byte atomic uint64_t,
versus the old 24-byte lock/key/data struct. At 262144 slots this changes the
table from 6291456 to 2097152 bytes (6 to 2 MiB); no memory/performance benchmark
is claimed. Cost preflight observes the same compiler's uint64_t/LP64 and
always-lock-free64 macros; the actual native is checked as ELF64 x86-64. No
redundant profile assertions are added to shipping. The earlier +6 B arithmetic
proposal with both shipping checks was never generated/compiled/packed/executed;
root selected this one core candidate before compilation. Runtime lock-free
assertion and sizeof observation may belong to a later isolated focused fixture.

One candidate native compile, fixed F ALONE package and strict pure decode are
allowed. The existing normal compiler argv/stdin/private cwd, inherited env,
77-byte prefix/template/source literal and ALONE9-extreme/lc2/lp0/pb0/BT4/64MiB/
nice32 remain. The baseline is read without copying/rebuilding/repacking; its
decode is pure. All artifacts/reports stay outside Git. No normal/shared edits,
source/flag/codec variants, engine/DEV/game/benchmark/training/AWS run occurs.
A gain permits a later root decision for focused TT coherence, constructed
collision policy, MTD/horizon and cancellation qualification before promotion.

The single first-cost run completed: source 9626/dd999295, native
18576/2a854b53, bootstrap 10625/9ba82649, and whole 4711/90a2f0ce,
17 bytes below the preserved full-key F4728 baseline. The native length is
unchanged but its full identity is new. Fixed ABI macro preflight, one native
compile and one fixed package passed; compiler stderr is empty and both pure
baseline/candidate decodes passed. No functional/engine/DEV execution occurred.
This is a cost-positive policy experiment, not a qualified or promoted engine.

The exact four producing ordinary source files are preserved outside Git under
rove4k-f-atomic-tag-tt-first-20261021-evidence/producing-source. This README's
readable pointer clarification and completed results are metadata after that
execution. Full-key baseline source22 remains in the prior packed-HCE final
source snapshot and its actual normal artifact root, unchanged. No trial was
compiled with the discarded shipping profile checks.
