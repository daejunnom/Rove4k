# One metadata-first D Board layout experiment

This is a native-cost experiment over the maintained finite-minimum C D source
at `7910a33b444a37f43bf9d37e900611b525cc9ea9`. The complete 18 ordinary source
files are retained byte-for-byte under `control/` and pinned in `recipe.json`.
No mutable maintained entry, historical report or generated image is a build
input. Root MIT licensing applies; no external implementation is copied.

Only one declaration is changed in the candidate copy:

```c
/* Control */
typedef struct { int8_t b[128]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;
/* Candidate */
typedef struct { int s,c,e,k[2],half,v; uint64_t h,r; int8_t b[128]; } Board;
```

No type, field meaning, function body, initializer, board algorithm, move order,
HQ implementation, HCE/hash/TT rule, pool, clone ownership, finite protocol,
compiler flag, link unit order or resource setting is changed. Shorter x86-64
metadata displacements are a hypothesis; array accesses can gain a displacement
and compiler layout/inlining can offset or reverse any benefit. Native cost
alone cannot establish the cause, final compressed size or semantic acceptance.

The first actual native-only comparison completed on the qualified compiler:

| Form | Exact original | Metadata-first | Native reduction |
| --- | ---: | ---: | ---: |
| Scalar | 8,348 B | 8,220 B | 128 B |
| HQ | 8,736 B | 8,576 B | 160 B |

Each native was independently compiled twice and was byte-identical within its
form/order. Control full hashes equal the maintained literals. Candidate scalar
is `97199bc4f763478dc939b290ff45372381a27d1f12552884ebae841f5fd9264d`;
candidate HQ is `32c7ba4f7724665685178dff1831699885e2989a52f6176d961edae171ed253b`.
Both candidates remain above 8,192 bytes; scalar exceeds it by 28 bytes. RX is
still three pages and the complete RW BSS segment remains at `0x403000` with
175,092 bytes. Scalar/HQ entry points change to `0x401e9b`/`0x401fcd`.
The original admission rejects both with `unknown selected TinyD native image`.
No new expectation is installed, and these native reductions are not inferred
whole-file or runtime gains.

The two actual compiler-emitted data objects record the following offsets:

| Property/field | Original | Metadata-first |
| --- | ---: | ---: |
| `sizeof(Board)` | 176 | 176 |
| `_Alignof(Board)` | 8 | 8 |
| Total padding bytes | 4 | 4 |
| `b` | 0 | 48 |
| `s` | 128 | 0 |
| `c` | 132 | 4 |
| `e` | 136 | 8 |
| `k` | 140 | 12 |
| `half` | 148 | 20 |
| `v` | 152 | 24 |
| `h` | 160 | 32 |
| `r` | 168 | 40 |

Every field size is unchanged. Padding moves from bytes 156..159 to 28..31.
The native-only producing receipt SHA-256 is
`fba00019af03d210ef74a5ab69f1cfd958e24b71f238f468e4a44f9711db85d2`.
It records eight native compilations and two compile-only layout probes,
zero codec/package/engine executions, exact commands and preserved original
admission errors. Reports and all executable/object outputs are external.

## Closed native-only reproduction

On Linux x86-64 with the qualified GCC 13.3/binutils 2.42 environment, including
WSL Ubuntu:

```sh
python3 -B engines/experiments/tiny-d-layout/build.py --out /absolute/new/external-output
```

The driver verifies and copies raw18 inputs, normalizes CRLF explicitly for the
compiler, and applies exactly one literal declaration replacement to a separate
candidate source copy. All eight native source hashes and the complete source
complement are recorded. It compiles scalar and HQ controls twice first and
requires their original full native identities, 8,348/8,736 bytes, plus the
original exact layout admission. Only after both controls pass does it compile
the one candidate twice per form. Native flags, five-unit order, strip operation
and original linker script come from the pinned control recipe. Paths are the
only substituted command arguments. There is no compiler, order, name, codec
or resource sweep.

Two small compile-only objects emit `sizeof`, alignment, each field offset and
field size into a data section. The driver reads those constants without
executing either a probe or an engine. They use the same target compiler ABI;
their auxiliary object command is recorded separately from production flags.
ELF RX page extent, entry, BSS addresses/sizes and section metadata are observed
without updating any accepted layout. The unmodified original admission guard
must reject the candidate's unknown full image. A changed page class or BSS is
reported rather than normalized into the previous loader contract.

No codec function, restoration loader compilation, packaging, audit loader,
engine process, UCI session, chess game or benchmark is executed. The copied
`control/fresh.py` is ancestry source only and is not standalone at this nested
path; the experiment never invokes it or the original whole-file builder.
Generated outputs, diagnostics and receipts stay outside Git. Incomplete
reports and command failures remain incomplete and are preserved.

## Layout and acceptance boundaries

Read-only review of all native units found typed Board copies/assignments,
zero aggregate initialization and named field access. HQ consumes the explicit
mailbox array pointer. Its only Board-related `memcmp` compares the two king
integers, not the object representation. Assembly handles entry/syscall/clone
registers and stack alignment, not Board offsets. DEV output serializes named
logical fields rather than raw Board storage. There is no position-dependent
nonzero aggregate initializer, raw-Board serialization, whole-object comparison,
Board-prefix cast or fixed `offsetof` dependency in the closed production source.

On the conventional target ABI the anticipated size is 176 bytes in both
orders with alignment 8 and four padding bytes; compiler-emitted measurements
are authoritative. Padding location changes and must not be compared as chess
state. The declaration is outside the DEV conditional, so the candidate also
changes the private DEV layout. Old exact DEV image claims do not transfer.

If native cost is promising, a separate authorized qualification should compare
every logical Board field and all 128 mailbox elements across independent
control/candidate transition sequences, then cover published/special perft,
HQ/scalar parity, repetition/halfmove/HCE/hash/TT-context and PLY cases with
normalized state rather than `memcmp(Board)`. It should also exercise the actual
candidate production pool, clocked/bare go and active position/next-go/quit/EOF
completion. Restoration requires an explicitly reviewed new exact image/layout
contract and actual RX/BSS/guard/stdio/TID/cleanup proof. Neither that packaging
nor runtime acceptance follows from this bounded first-cost step.
