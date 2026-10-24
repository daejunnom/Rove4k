# One LZMA-alone transport for the maintained A5207 entry

The complete candidate is **5,163 bytes**, a **44-byte reduction** from the exact
5,207-byte maintained A control. It remains **1,067 bytes above 4,096** and is
not size-eligible. This optional experiment changes only the compressed entry
transport. It does not change the maintained A source/recipe/verifier, earlier
experiments, compiler argv, resources, runtime, bootstrap or C source. There is
one declared alternative, with no codec, preset, spelling, flag or resource
sweep. No third-party engine source or decoder code is copied.

## Exact whole-file cost

Both entries carry the same **12,138-byte Python bootstrap**, including the
same **11,148-byte C compiler input**, fixed
`cc -Os -x c - -o x -s` command, signal handoff, compiler process-group cleanup
and fd-exec path. The candidate changes `xz -dc` to the allowed `lzma -dc` in
the original shell launcher and updates its one-based `tail` address. Its
77-byte prefix addresses byte 78; the original 75-byte prefix addresses byte
76. The final exec/exit boundary and newline stay intact. No newline or padding
is appended to the compressed stream.

| Actual bytes, all included in the whole file | XZ control | LZMA-alone | Difference |
| --- | ---: | ---: | ---: |
| Complete shell prefix | 75 | 77 | +2 |
| Container/check/padding/index overhead | 58 | 13 | -45 |
| Coded data including coding termination | 5,074 | 5,073 | -1 |
| Complete compressed payload | 5,132 | 5,086 | -46 |
| **Complete executable entry** | **5,207** | **5,163** | **-44** |

The control's 58 bytes consist of a 12-byte stream header, 12-byte block
header, 8-byte CRC64, 2-byte block padding, 12-byte index and 12-byte stream
footer. The candidate's complete 13-byte header contains one properties byte,
four dictionary bytes and eight uncompressed-size bytes. Its actual header is
`0200000004ffffffffffffffff`: `lc=2`, `lp=0`, `pb=0`, a 64MiB dictionary and
unknown uncompressed size. The encoded end marker/range termination remains
inside the counted coded data. LZMA1 replaces LZMA2, so the saving is **not
described as purely container overhead**. LZMA-alone has no XZ CRC64 field;
no equivalent corruption-detection claim is made.

The single candidate uses Python `FORMAT_ALONE`, one `FILTER_LZMA1`, filter
preset `9 | PRESET_EXTREME`, explicit `lc=2/lp=0/pb=0` and `CHECK_NONE`. The
control uses its recorded LZMA2/XZ 9-extreme, `lc=2/lp=0/pb=0`, CRC64 profile.
[Python's documented format/filter contract](https://docs.python.org/3.12/library/lzma.html)
and the [upstream LZMA format](https://github.com/tukaani-project/xz/blob/v5.4.5/doc/lzma-file-format.txt)
support this bounded comparison. Both the Python-linked library and actual
decoder are liblzma/XZ 5.4.5. The receipt records the mapped library path and
version; `/usr/bin/lzma` resolves to `/usr/bin/xz` and is invoked by the allowed
`lzma` name. No installation or system configuration is performed.

## Literal identity and reproducibility

The admitted maintained control is
`/home/stemxstudio/rove4k-tiny-entry-a-5207-final-20261020-v2/build-1`.
Its raw `build.json` is pinned, as are the exact wrapper, source, bootstrap and
native. All ten declared maintained source/helper inputs are also copied and
checked against the pinned manifest. The bootstrap AST must contain the exact
C input and fixed compiler argv. Neither transport production nor decoding
executes the restored Python bootstrap or invokes its compiler.

| Object | SHA-256 |
| --- | --- |
| Original 5207 entry | `085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36` |
| **LZMA-alone 5163 entry** | **`4f1562199786596c4addb36c1b47ecdcee143ca0338e8c986d350fe5639d1f8c`** |
| Unchanged bootstrap | `11679fb20e24e7cb777cb49e4bee5a7ee7ea999278651fbba6d622320e751d44` |
| Unchanged C input | `5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7` |
| Unchanged native ELF | `d39167146236aafde21b59439b853bd10561f04e9186c18b839c2f84f2e16e12` |

`build.py` first reproduces the complete 5207-byte control exactly twice. It
independently compresses the one ALONE alternative twice, writes two complete
files and requires identical bytes. Strict Python decompression requires exact
bootstrap bytes, true EOF and empty unused data. Actual `lzma -dc` is separately
given only the extracted payload and must return those same bootstrap bytes
with exit zero. CLI XZ decoding separately checks the control. The decoder
output is never sent to Python execution at the cost stage.

The immutable first cost is
`/home/stemxstudio/rove4k-tiny-lzma-entry-first-20261020-r2/results.json`, SHA
`d4b05dd0daae3e345e18f40d24eceb523d64b087bee811eb0f7c54b52d0c62b7`.
Its candidate already had two strict Python and two CLI decode checks. Its
shared control repeat flag overstated the Python count: the control had one
strict Python admission decode, two CLI decodes and two exact re-encodes.
That original receipt remains unchanged. The final repeat adds two explicit
strict Python control decodes as well, retaining the same candidate bytes:
`/home/stemxstudio/rove4k-tiny-lzma-entry-first-20261020-r3/results.json`, SHA
`2cdc6859837ba17752bb8a30531bbee7cae8e647cdc183f438f4ab69cdbcd5df`.
Both cost-stage receipts retain `runtime_qualified: false`; later runtime
evidence does not rewrite those original stages.

The initial output directory without an `r2/r3` suffix is a preserved failed
input-collection attempt, before compression or engine execution. The
maintained builder records logical repository helper names but stores their
snapshots by basename. Reading that exact hash-pinned builder established the
fixed storage mapping; the retry still requires the original literal names,
hashes and lengths. No admission hash was replaced with an observed value.

## Root-authorized two-session runtime evidence

After the actual 44-byte gain was reported, root explicitly authorized only
two selected-wrapper sessions: quit and EOF. `verify.py` hard-pins the literal
5163 entry hash above, both cost receipts and the unchanged native/source/
bootstrap identities. It keeps the maintained A recipe and verifier read-only
and freezes their exact bytes. It creates a **separate, explicitly named
candidate recipe** with literal candidate expectations. Expectations are not
learned from the file under test, and the original 5207 recipe is not rebound.

The canonical A verifier itself is copied unchanged, SHA
`cc63a511446c35db54676356a9d885b95db7da994133147cda3e3ff1c4464b0c`.
Its original shared verifier/oracle helpers are pinned and frozen. The same
actual restoration, stable startup, legal white/black zero-clock result,
finite bare-go, active-close, reader completion and process-absence gates run
against only the literal candidate adapter.

**Both sessions pass, exit zero.** The actual full restored ELF matches
`d3916714...e16e12`; its private file and directory are absent before search,
no compiler/helper child remains, and three startup TIDs are stable. Each
session completes the required legal clocked and bare-go results, observes
unfinished work before quit/EOF, receives exactly one legal closing bestmove,
joins output readers and confirms process disappearance. Cancellation
causality remains `unproven`; work/result receipt ordering is not promoted to
a causal cancellation proof. The observed bare-go wall bounds include the
verifier's quiet interval and are not a performance comparison.

The candidate adapter receipt is
`/home/stemxstudio/rove4k-tiny-lzma-entry-runtime-20261020/results.json`, SHA
`22b8ab4879b13debf56792fe7b9bd859bc69ffd34f48a21ce61417d831708927`.
The unchanged canonical verifier's actual receipt is
`actual-two-sessions/runtime.json` under that root, SHA
`34e0900a4ce0e0a26c2c563b6bbc93cac62d06258cc0c968f152b45f7464514d`.
There are no extra game, feature, preset, benchmark or target-thread campaigns.
Old core/rule evidence is reused only through exact unchanged bootstrap/C/native
identity. These two sessions do not establish playing strength, scaling,
other-platform support or 4KiB eligibility. All managed commands are terminal.

Reproduce into new absolute directories outside Git:

```sh
python3 -B engines/experiments/tiny-lzma-entry/build.py \
  --control /home/stemxstudio/rove4k-tiny-entry-a-5207-final-20261020-v2/build-1 \
  --out /home/stemxstudio/new-lzma-entry
```

The runtime adapter deliberately admits the exact recorded first/final cost
receipts, rather than silently updating its literal expected report hashes for
a new output path. To replay the already frozen qualification:

```sh
python3 -B engines/experiments/tiny-lzma-entry/verify.py \
  --cost /home/stemxstudio/rove4k-tiny-lzma-entry-first-20261020-r3/results.json \
  --first-cost /home/stemxstudio/rove4k-tiny-lzma-entry-first-20261020-r2/results.json \
  --out /home/stemxstudio/new-lzma-entry-runtime
```

All generated files, old failures, frozen recipes and raw receipts remain
outside Git. The maintained A owner/root must separately decide and verify any
canonical transport adoption; this experiment does not perform that promotion.

## Historical-input path independence

Before later canonical A promotion, the two historical source inputs used by
this experiment were saved as ordinary owned files:

- `control/verify.py` is the exact previously executed canonical verifier,
  SHA `cc63a511446c35db54676356a9d885b95db7da994133147cda3e3ff1c4464b0c`.
- `control/recipe.json` is the original A5207 recipe, SHA
  `749b6e102a581efe419de14e40bd7346afff18b5bc8b46c145084b11bb89456a`.

The candidate adapter now reads those two exact relative input names from its
own `control/` directory. Shared `engines/tests/verify.py` and the oracle keep
their existing tracked, hash-pinned lookup. The historical snapshots are data
inputs, not standalone entry points: the adapter still copies verifier bytes
into the same external mirrored layout and writes the same separate explicit
candidate recipe. It does not edit the historical verifier or rebound recipe.
The owned folder's local `.gitattributes` keeps these raw-hash-pinned historical
inputs and other source text LF on Windows checkouts; canonical A's own LF
attributes do not extend to this separate experiment folder.

The original three source files and original freeze receipt were preserved
outside Git before the lookup edit. Static comparison removes only the new
lookup helper and restores the one old lookup expression, then requires the
entire adapter AST to equal the adapter that actually ran. The lookup helper's
own exact AST distinguishes the two canonical inputs from the shared verifier
with the same basename. Input bytes and the actual candidate-recipe JSON are
also checked against the prior qualified execution, along with the complete
candidate/bootstrap/C/native bytes. External mirrored paths, subprocess argv,
hash admission and all engine/checker behavior are unchanged.

This revision **reuses** the existing two-session receipt; it launches no new
adapter runtime, codec, compiler or engine process. The historical runtime
`adapter_sha256=b5450962...` remains untouched and identifies the code that
actually ran. The new adapter source hash is recorded separately by
`input-path-revision-20261020/receipt.json` in the external evidence directory.
The revised adapter's runtime path has not been executed. Its independence
from the live canonical A verifier/recipe is established by the path-only AST
and exact copied-input proof, not by relabeling the old runtime as a new run.
