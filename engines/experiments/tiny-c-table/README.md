# Tiny C exact PSQT gather experiment

This bounded experiment compares two exact lookup representations against the
qualified **6,059-byte TinyC** and **5,671-byte TinyA** controls. It changes only
the separate C candidate's evaluation source in an external producer copy. The
canonical portfolio, TinyCE, TinyA and shared scripts remain unchanged.

The startup-table candidate measures **6,015 complete bytes**, saving 44 bytes
against TinyC. The readonly-table candidate measures **6,455 complete bytes**,
adding 396 bytes. Both results are retained. Neither reaches the 4,096-byte gate;
the smaller candidate is still 1,919 bytes over.

| Fixed AVX2 candidate | Complete source wrapper | Complete native wrapper | Compact C source | Shipping ELF |
| --- | ---: | ---: | ---: | ---: |
| Qualified TinyC control | 6,059 B | 9,915 B | 14,710 B | 26,464 B |
| Construct table before main | **6,015 B** | **9,892 B** | 14,439 B | 26,488 B |
| Exact readonly source table | 6,455 B | 10,223 B | 17,637 B | 30,552 B |

Every source wrapper includes the shell prefix, shared compressed Python
bootstrap, C input, table declaration/encoding/initialization and fixed compiler
command. Every native wrapper includes its decoder and executable. No external
table, model, download or NVCompact call supplies omitted bytes.

The table has 13 signed-piece rows (`-6..6`) and 64 squares (`a1..h8`): 832 signed
32-bit values, 3,328 bytes total. Its exact little-endian bytes have SHA-256
`172c6eac2478f596fef4d0cc78a1ba644ae8bce06b4e5fd4258310713f49ae1c`.
The startup representation calls the original HCE `value(piece, square88)` for
every entry in one constructor before main and before worker creation. The
readonly representation inserts the same exact values into C and has no
shipping initialization function. DEV alone retains a constructor counter for
the initialization-boundary fixture.

The real leaf loads eight signed board cells, forms `(piece+6)*64+square64`,
gathers their HCE values and adds them to SIMD lanes. Eight gathers cover all 64
visible squares. Horizontal SIMD reduction supplies the returned search score.
The leaf reads neither cached `Board.v` nor mailbox padding, and adds no runtime
ISA selector. Both candidates retain fixed `-mavx2`, the incremental HCE/hash,
full-key coherent TT, legal move admission, PVS/QS, history, continuation,
correction, startup pool and completed-root publication boundaries.

The storage tradeoff is separate from complete file size:

| Shipping ELF section | TinyC control | Startup table | Readonly table |
| --- | ---: | ---: | ---: |
| `.text` | 8,738 B | 8,656 B | 8,592 B |
| `.rodata` | 384 B | 352 B | 3,680 B |
| `.bss` | 171,176 B | 174,528 B | 171,176 B |
| `.init_array` | 8 B | 16 B | 8 B |

Startup therefore adds 3,352 section bytes to BSS, including layout/alignment,
for a 3,328-byte shared table. It performs 832 HCE calls before main. The table
is shared by all workers and is read only after construction. The readonly
choice adds 3,296 `.rodata` bytes against the control after removing the old
32-byte packed coefficient table. Startup observations under concurrent host
load separately record native process startup, `VmRSS`, `VmSize`, `VmData` and
stable thread IDs. They do not establish an isolated startup or NPS improvement.
The measured source-wrapper startups were about 0.87 seconds; both restored the
expected complete ELF, removed temporary files before exec and exited normally.

`campaign.py` consumes the original TinyC build's saved `recipe/`, validates
every recorded input hash and freezes it before producing either alternative.
It verifies that the TinyA control has the same four core source hashes and the
same compiler identity. The complete control artifacts and build manifests are
copied into the external campaign. Both candidates therefore use the original
compiler flags and packager bytes; later mutable helper changes do not enter
this comparison. Generation/validation scripts and their exact input hashes
are also saved. Build outputs, tables, binaries and reports stay outside Git.

Reproduce on the recorded WSL Ubuntu/GCC 13.3 AVX2 environment with the two
qualified control manifests and the TinyA artifact:

```sh
python3 -I -B engines/experiments/tiny-c-table/test_generate.py
python3 -I -B engines/experiments/tiny-c-table/campaign.py \
  --control-c-build /external/TinyC6059/build.json \
  --control-a-build /external/TinyA5671/build.json \
  --control-a-artifact /external/selected-A-5671.sh \
  --out /external/new-table-campaign
python3 -I -B /external/new-table-campaign/frozen/engines/experiments/tiny-c-table/qualify.py \
  --campaign /external/new-table-campaign/results.json \
  --out /external/new-table-qualification
python3 -I -B /external/new-table-campaign/frozen/engines/compact/tiny-ce/blackbox.py \
  --build /external/new-table-campaign/startup/build/build.json \
  --out /external/new-table-blackbox/startup
python3 -I -B /external/new-table-campaign/frozen/engines/compact/tiny-ce/blackbox.py \
  --build /external/new-table-campaign/readonly/build/build.json \
  --out /external/new-table-blackbox/readonly
```

The measured builds independently reproduce every native form, the compiler
stdin restoration image and every complete wrapper. Original and compact forms
produce identical native bytes. Both table candidates pass production-source
O2 and ASAN/UBSAN contracts: all 832 table terms, exactly one DEV startup
initialization, **369,255 board comparisons and 738,510 actual SIMD calls per
build**. Cases include every piece/square, poisoned cached HCE and padding,
reversed side, board preservation, special-move children and reachable boards.
The fixture includes the actual combined producer DEV source rather than a
separately reconstructed evaluator. The emitted DEV and shipping native images
contain `vpgatherdd` and `vphaddd` instructions. Real completed depth-four searches
show positive SIMD leaf, PVS/QS, history, continuation and correction activity.

Both candidates pass **56/56 shared black-box groups** in total, covering their
DEV, original, compact, selected source and selected native artifacts. Selected
source/native restoration checks compare complete `/proc/<pid>/exe` bytes and
require three stable startup task IDs for the fixed two-worker profile, clean
temporary storage and normal shutdown. Runtime qualification is recorded
separately from the initial source-cost report, whose candidates remain marked
`runtime_qualified: false` to preserve that report's original evidence stage.
These are local functional and source-cost results, with no strength estimate,
512-hardware-thread scaling claim, canonical adoption or 4KiB acceptance.
