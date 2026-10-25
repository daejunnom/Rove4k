# Data8 Rust D: one matched four-form own-ELF first cost

This separate `tiny-rust-d-data8-sectionless-v1` class compares the frozen ASCII
native control with one runtime Board::start implementation that reuses put.
Each constructor has HQ/scalar backends. It does not modify or extend the older
data16 packed class, the maintained engine, the start experiment, the loader,
the codec or any prior qualification receipt.

All four original complete natives are 16,816 bytes and have literal identities:

| Form | Original complete native SHA-256 | RX file bytes |
|---|---|---:|
| control-hq | `f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8` | 14,688 |
| control-scalar | `bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878` | 14,240 |
| put-hq | `9b72472b1b73ee12a6ab2755e8b9c14f5544efc6766cf67eb8bbee031bbbabcf` | 14,416 |
| put-scalar | `ef9b112aa489268bffa1c8cf96dbde945e811a93f2a95357cbd74ff6779e7461` | 13,968 |

The constructor candidate reduces each native's .text by 272 bytes but leaves
the complete ELF size unchanged because data still starts at file offset 0x4000.
Its readable Rust source grows by 16 bytes. The prior distinct std test images
compare all ten named fields/151 elements and Copy/fresh-start independence,
two tests in each lane. Those proofs belong to the frozen constructor receipt,
not to a production ELF or this packed file's actual execution.

Every form has entry 0x4000f0, RX beginning at 0x400000 and RW LOAD at file offset
0x4000/address 0x404000 with filesz8/memsz12. Data8 is exactly
`4601400000000000`, a memcpy pointer to 0x400146 inside RX. OUTPUT is the four-byte
BSS at **0x404008**. The .shstrtab starts at file offset 0x4008, so both a complete
16,816-byte decode and the old class's 16,400-byte decode would overwrite BSS.
This class's sectionless span is exactly **16,392 bytes**. PHDR/entry and all
text/rodata/gap/data bytes stay identical; only ELF section-header metadata
fields are zeroed before non-load section metadata is truncated. Each form's
native/span/payload/whole identity is separate.

The fixed reservation remains 0x3ff000..0x406000: lower guard, five decode pages,
upper guard. Existing loader macros IMAGE_PAGES=0x5000 and BSS_BASE=0x404000 /
BSS_PAGES=0x1000 create final RX4 plus RW1 through the unchanged source sequence.
The real initial BSS and zero tail start at 0x404008; live OUTPUT inspection
uses offset0x4008 and immutable padding from offset0x400c.
This is a separate literal class, not broad automatic ELF-layout admission.

The ordinary source closure is fully owned here:

- native/ contains the seven byte-exact frozen ASCII control build inputs.
- start/ contains the exact frozen producer and readable replacement template;
  only Board::start is transformed, with board SHA 4f476e...50c checked explicitly.
- packaging/ contains exact unchanged project-owned loader, linker, codec and
  packer snapshots. Only existing E8/E9 BCJ and fixed-Huffman Deflate are used.
- guard16.py is the exact old data16 producer snapshot. Its admission function
  is used only to confirm rejection of every new data8 native. Its main/build
  path is never run, and its old input sources are not loaded.
- recipe.json pins all inputs, four complete natives, four sectionless spans,
  the literal new layout, original flags and fixed2worker/TT18/PLY128 profile.

No normal build reads mutable maintained folders, a mutable experiment folder,
historical reports, generated candidates, old payloads or network inputs. The
constructor's final phase/manifest/archive hashes are metadata only. The builder
materializes two source trees inside a new external directory at the original
engines/compact/tiny-rust-d placement, preserving the unchanged native builder's
output fence. Native flags, Rust1.97 recipe and loader flags are fixed.

Each native is compiled twice and must equal its literal complete hash. The
original builder's distinct unstripped static audit remains. Each full packed
file is encoded/loader-compiled twice and must reproduce complete bytes. Actual
payload and loader/header contributions are measured rather than borrowed from
the old class. Commands are bounded and own their process groups; incomplete
or interrupted work preserves complete:false and diagnostics.

```sh
python3 -I -B engines/experiments/tiny-rust-d-packed-ascii/build.py \
  --out /absolute/new/external-data8-cost \
  --rustc /home/stemxstudio/.cargo/bin/rustc
```

The first-cost gate is compilation/static inspection and build-time codec
roundtrip only. **No production native or packed ELF, CHECKPOINT, ptrace, RIE
fixture or benchmark is executed by this producer.** An independent source
review must precede its first compiler invocation. Old positive or failed
runtime reports are preserved separately and do not qualify these new files.

The previous data16 file costs (HQ12,554/scalar12,194) are historical metadata.
The new control-to-put packed difference is a matched constructor comparison;
old-data16-to-new-ASCII-control and new-control-to-put differences are recorded
separately. A 272-byte .text change does not predict the compressed whole delta.
Runtime admission, 4 KiB eligibility, strength, target scaling, CI and release
are not established here. Training and AWS remain excluded.

The first fixed cost completed with all four native and complete packed files
independently reproduced twice:

| Form | Payload | Loader + headers | Complete own-ELF | Complete SHA-256 |
|---|---:|---:|---:|---|
| control-hq | 10,647 B | 1,115 B | **11,762 B** | `da6f203d2304311856509d5d8d803cb647e4bb7f3444caa3a2fb1710304607e5` |
| control-scalar | 10,288 B | 1,115 B | **11,403 B** | `c485ddc7cca0bbfa31605d6488113075879164802c89ccda48d29d49c7756bc6` |
| put-hq | 10,450 B | 1,115 B | **11,565 B** | `48dfbe38442f6f39dbbd7559ade48ed3a134ccb558d23ad26416c128192bcaa7` |
| put-scalar | 10,091 B | 1,115 B | **11,206 B** | `cd25152381cb3c42a906edff2dae4da0a053fdc421db4b72e645f6f0c200d0da` |

The actual matched constructor saving is **197 bytes in each backend**. The
historical data16-to-ASCII-control differences are separately HQ792/scalar791
bytes; this measures a different input revision and class transition. None is
an inferred additive prediction. All four files still exceed 4,096 bytes.

At this first-cost checkpoint, candidate ELF/CHECKPOINT/ptrace/RIE/benchmark
executions were zero. The independent precompiler review binds producer
`f47e2a2d0547d3d981c8a3493a5afa24b3e9440dc0fe3303b0b688d72ddf0733`.
Its executed source and pre-result README are frozen externally. This result
table was added afterward without another native compiler or codec invocation.


The later positive-observation campaign used a separate `verify.py` and three
owned immutable helper snapshots. The unchanged producer, recipe, native seven,
constructor producer/template, loader/codec/packer and data16 guard were frozen
before these four observer sources were added. The accounting helper is the
ASCII revision SHA-256
`5e93b4df6d6edf8393c4d57e87da3923569733f77e10e8925ed3daf6f8d5a2e6`,
with `rejected_lines=[]` initialized in the stream adapter. It reuses exact
input admission and cumulative dispatch/observed/consumed-result methods; it
does not call that helper's control-image pin or qualification entry points.
The C helper contributes owned process/readers, maps, task/stdio and physical
activity observation. Its C-layout inspector is not used. The independent
chess oracle supplies legal moves. No mutable maintained validator is read.

```sh
python3 -I -B engines/experiments/tiny-rust-d-packed-ascii/verify.py \
  --first-cost /absolute/existing/fixed-data8-cost \
  --out /absolute/new/external-data8-positive-observation
```

The fixed positive campaign completed once, with separate identities:

| Profile | Shipping sessions | Separate CHECKPOINT bytes | CHECKPOINT SHA-256 |
|---|---|---:|---|
| put-hq | quit + EOF, both passed | 11,588 B | `a9a7002907bd405de1e30c5ce169fd73dd836627488c452bd672605b1b8d2e87` |
| put-scalar | quit + EOF, both passed | 11,229 B | `7ee84f328f44fd14a34518d5131dfa84875fe4752759e2ef8c4c6facbe85ecb6` |

Each CHECKPOINT image stopped before the original native entry with one TID,
stdio only and no child/native worker. A complete five-page `/proc` read matched
the exact 16,392-byte sectionless span, initialized memcpy pointer 0x400146,
OUTPUT/BSS4 zero at 0x404008 and zero padding from 0x40400c. Final mappings were
anonymous RX4/RW1 with both image guards, no observed WX and a non-executable
process stack. SIGCONT passed the unchanged literal 0x4000f0 entry handoff and
produced the original uci/isready acknowledgments before normal quit/EOF. This
is source-bound handoff plus protocol evidence, not an instruction-pointer trace.

Each of the four shipping sessions had three persistent startup TIDs, two raw
guarded non-executable 1 MiB worker stacks, stdio only and no task children.
Startup and active five-page reads, raw maps, stdio pipe links and task states
were preserved. `/proc/PID/exe` matched the shipping whole-file SHA separately
from the normalized anonymous restored header/RX/data identity. Both clock
colors, physically active GO replacement, active position replacement and
active quit/EOF each produced the expected legal result. Six GO commands per
session matched six observed and consumed legal bestmoves, **24 total**, with
no rejected input lines, partial tails or extra results. The main was observed
sleeping while both workers ran with increasing aggregate CPU ticks before
those active boundaries.

All six candidate/audit processes exited zero, their readers reached EOF and
joined, and every session settled without forced cleanup. Post-run inspection
found all eight owned process groups (including two audit compiler groups) and
all sixteen observed TIDs absent; the handle registry was empty. The original
runtime report SHA-256 is
`a5221549c16adb9af08c0d46a90e023481f269773fa61916703353131f98aeb4`.
Raw sources, audit files, memory reads, maps, commands, input/output and cleanup
receipts remain in external evidence directories. No native or shipping file
was recompiled or re-encoded during observation; only the two separately
identified CHECKPOINT loaders were compiled.

`complete` and `positive_observation_complete` describe only this positive
campaign. `runtime_admission_complete` and `all_loader_conditions_verified`
remain **false**. RIE rejection, negative fixtures, arbitrary repeated-signal
behavior and cancellation causality remain unproven. This observer contains
no personality setting, register-change or ptrace execution path, and none was
run. Existing data16 positive/failed reports and the stopped unexecuted RIE
adapter are preserved separately; old trace/deep/fault evidence is only prior
source/body proof and is never relabelled as a data8 run. This campaign makes
no 4 KiB, strength/scaling, benchmark, CI, release, training or AWS claim.
