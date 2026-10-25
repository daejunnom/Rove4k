# TinyD original online range-code experiment

This is a retained unsuccessful size experiment. The smallest complete file is
**7,998 bytes scalar / 8,299 bytes HQ**. Every measured form exceeds 4,096 bytes
and the sibling dedicated fixed-Huffman files (7,665 / 7,918 bytes). It does not
replace the original native TinyD images or establish an eligible 4 KiB entry.

The new architecture is an original binary range encoder and two independently
implemented decoders: Python reference and freestanding C. The encoder uses a
32-bit interval, 64-bit carry accumulator, byte normalization and five-byte
termination. A 20-byte frame carries magic, fixed profile, exact raw/encoded
lengths and Adler-32. Both decoders bound reads/writes, require the initial zero
byte, exact compressed consumption and final code zero, then check Adler-32.
The checksum detects accidental corruption; it is not authentication.

Exactly two algorithm profiles were fixed before measuring the real images:

- `order1`: previous byte plus current byte's binary-tree prefix selects one
  of 65,536 unsigned 16-bit probability states.
- `mix2`: an equal integer-floor mixture of prefix, order1 and a bounded
  two-previous-byte hash selects three disjoint tables, 131,328 states total.

States start at 32,768 and intrinsically adapt by 1/32 after each decoded bit.
There are no offline trained tables, engine/model training, data fitting,
parameter sweeps, external code downloads or remote compute. A reversible x86
call/jump displacement transform precedes coding; decoded RX bytes match the
admitted source images exactly after inversion.

| Frozen image | Profile | Framed stream | Decoder + ELF headers | Complete ELF | Temporary probability RAM |
|---|---|---:|---:|---:|---:|
| Scalar | order1 | 6,882 | 1,116 | **7,998** | 131,072 |
| Scalar | mix2 | 6,889 | 1,240 | **8,129** | 262,656 |
| HQ | order1 | 7,183 | 1,116 | **8,299** | 131,072 |
| HQ | mix2 | 7,182 | 1,240 | **8,422** | 262,656 |

The mix2 anonymous allocation rounds to 266,240 mapped bytes. Model memory is
RW, initialized at startup and unmapped before engine entry. These RAM costs
are separate from the complete file sizes. No profile is selected using a
payload-only size claim.

## Native contract and provenance

Only the exact known TinyD Linux x86-64 LP64 static scalar/HQ shipping files
are admitted. `native_support.admit` validates both SHA-256 and the complete
known ELF geometry, including entry, zero BSS, separate RX/RW pages, no
interpreter/TLS/dynamic/data segments and stripped section metadata.

- Scalar, 8,540 bytes: `ef14e2839af96d111fa9ce1a2928749ceec518e3be652cc6d36ee8975cae47d0`
- HQ, 8,928 bytes: `387a00209ffcc14446f662a56cc2ff778ae7873c2dfebebbee9906fd19e5cd0c`

The repository-owned bootstrap, mapping policy, entry assembly, BCJ inverse,
ELF validation/build helpers, linker script and runtime inspector were locally
reused from the frozen direct-loader v3 recipe. The original range algorithm
and Python/C coding implementations were written for this experiment. The
repository root MIT license applies; no external codec implementation was
copied. Frozen internal provenance:

| Original v3 recipe | SHA-256 |
|---|---|
| `loader.c` | `8a6a9cb93ae484400056852c5bc406be1cc15dc7b8df6b0a57e6d6330a2e4094` |
| `image.ld` | `93934099212b944b20c2f7840ee87e4817311c4f87fddbb2b3f91db28776cf99` |
| `build.py` | `fe43b4c59a571b125812bc805dc90cf1d9f37289519b8d4ecfa959dbad2a5241` |
| `test_runtime.py` | `43c02d5b89afa3cf56d39dbab1e1e8f429c1b24d64b48ebb1d45ab51a577403d` |

The frozen external source is catalogued as
`rove4k-tiny-d-direct-loader-20261020-v3/recipe`.
`native_support.py` retains the relevant helper prefix, changes only the
profile macro from fixed-Huffman selection to `RANGE_PROFILE`, and updates the
module description. The inspector changes profile names for quit/EOF coverage.

The bootstrap lives at `0x10000000`. It rejects inherited READ_IMPLIES_EXEC,
reserves `0x3ff000..0x42f000` using MAP_FIXED_NOREPLACE, checks the exact return
address, and keeps its first/last pages inaccessible. Image pages become RW
for checked decoding and then RX. Untouched anonymous BSS pages separately
become RW; no page is RWX. The loader uses raw syscalls without libc, TLS,
interpreter, external programs, file creation or runtime compilation. It
restores the initial RSP, clears DF/EBP/EDX and jumps to the admitted entry.

The inherited auxv, executable identity, initial brk and surviving loader map
still describe the bootstrap. The supported contract is the exact admitted
static images and their observed runtime behavior; this is not a general ELF
loader or full process-image equivalence claim. Linker-symbol pointer arithmetic
uses GNU freestanding ELF conventions.

## Reproduce

On Linux x86-64 with GCC and Python 3.12, keep all outputs in new absolute
directories outside Git. The input root is the frozen direct-loader build
containing the two `native-control` files:

```sh
python3 -B engines/experiments/tiny-d-range/test_codec.py --out /external/range-codec
python3 -B engines/experiments/tiny-d-range/build.py \
  --input-root /external/tiny-d-direct-loader --out /external/range-build
python3 -B engines/experiments/tiny-d-range/test_native.py \
  --build /external/range-build/build.json --out /external/range-native
python3 -B engines/experiments/tiny-d-range/test_runtime.py \
  --build /external/range-build/build.json --out /external/range-runtime
python3 -B engines/experiments/tiny-d-range/startup.py \
  --build /external/range-build/build.json --out /external/range-startup
```

`build.py` freezes all executable source/validator recipes, encodes twice and
compiles twice per scalar/HQ/profile form. It counts the entire stripped ELF,
including headers, decoder, model initialization, framing and stream, and also
builds stopped pre-entry audits and eight malformed native diagnostic controls.

## Observed evidence and limits

WSL Ubuntu, GCC 13.3, Python 3.12 local observations on 2026-10-20:

- Codec/reference: **1,062** deterministic round trips/repeated encodes,
  **563** malformed/truncated frames and **4,040/4,040** sampled body bit
  mutations rejected. Fixtures include every byte value, lengths 0..255,
  random data, long equal runs, byte boundaries and x86 patterns.
- Native arbitrary-data parity: **18** diagnostic images exactly restored
  before entry; **54** small-frame truncation prefixes rejected. Diagnostic
  bytes were inspected while stopped, then killed/reaped without execution.
- Four actual engine forms reproduced byte-for-byte, with exact original RX,
  zero BSS/padding, inaccessible guards, correct protections, nonexec stack and
  no writable executable mapping. Resuming each audit reached original UCI
  entry. Actual production clocked search retained three startup TIDs,
  immutable RX and only stdio descriptors. Order1 quit and mix2 EOF succeeded.
  Eight malformed native controls exited 126 without output.
- A separate read-only agent reviewed both Python algorithms and the native
  arithmetic/bounds/ABI/mapping path without finding a blocking defect.
- Three exec-to-ready samples per native control/profile (18 launches total)
  measured 3.93..8.23 ms locally; range forms 4.93..8.23 ms. These include
  process launch, scheduling, engine startup and concurrent local work, and do
  not isolate decoder CPU time or establish target latency. All had three TIDs.
  Ready RSS was about 6 MiB; the temporary probability allocation was already
  unmapped. Exact observations, not subtracted overhead claims, are retained.

Final binaries/audits in v2 match v1 byte-for-byte; the v2 changes only freeze
the final validation recipes and tighten host/output-path checks. Native parity
and codec evidence are reused on identical codec/decoder bytes; actual engine
runtime was rerun for v2. Evidence is outside Git:

- `/home/stemxstudio/rove4k-tiny-d-range-20261020-v2/build.json`
- `/home/stemxstudio/rove4k-tiny-d-range-20261020-codec/codec.json`
- `/home/stemxstudio/rove4k-tiny-d-range-20261020-native/native.json`
- `/home/stemxstudio/rove4k-tiny-d-range-20261020-v2-runtime/results.json`
- `/home/stemxstudio/rove4k-tiny-d-range-20261020-v2-startup/startup.json`

All owned test/compiler processes were physically reaped, and a final
`/proc/*/exe` check found no surviving executable under this experiment's output
prefix. The unsuccessful artifacts and failure evidence are preserved.

No full legal-move/two-colour shared-shipping campaign was run for these size
failures. The unchanged original TinyD images retain their separate prior
engine evidence; this experiment establishes exact restoration plus the bounded
runtime observations above. Tournament loader eligibility, 4 KiB acceptance,
Elo, target performance, full engine acceptance and release remain unproven.
