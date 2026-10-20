# Maintained minimal E entry

`engine.c` remains the readable canonical program. The selected complete
shipping file is **5,400 bytes**, **1,304 bytes above 4,096**, down from
5,679 bytes. Source, native ELF and the wrapper are generated from ordinary
inputs; no generated artifact is an input to the normal build.

On the qualified Linux x86-64 Ubuntu 24.04.4/GCC 13.3.0/binutils 2.42/glibc 2.39/
Python 3.12.3/xz-lzma 5.4.5 toolchain:

```sh
python3 -B engines/compact/tiny-entry-e/build.py --out /absolute/new/E-build --dev
python3 -B engines/compact/tiny-entry-e/verify.py --build /absolute/E-build --out /absolute/new/E-runtime
```

Outputs must be new absolute directories outside Git checkouts. One builder
invocation independently regenerates shipping twice and optional DEV twice.
The unchanged verifier opens exactly two selected wrappers for quit and EOF;
each wrapper performs its normal fixed source compilation/restoration.
`fresh.py` can separately archive the 18-file ordinary closure and rebuild
two extracted copies. That separate fresh-archive check is not implied by a
direct build invocation.

The profile retains two search workers, one controller, TT bits 18 and PLY 128.
These are provisional fixed resources, not final competition scaling choices.
Compiler flags and bootstrap body remain unchanged:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

Existing conditional specialization, compaction, diagnostic stripping and fixed
shipping spelling guards remain unchanged. `shipping_scope.py` then replays the
qualified 25 private static-function maps and 79 automatic-name
declaration maps in that order. It changes only literal physical occurrences,
requires exact input/output hashes at both stages and restores each input by
inverse edits. It imports only `hashlib`; normal CI needs no Clang, experiment,
external report, generated C, other engine source or network input. Shared
guards are not broadened. Canonical DEV bypasses all shipping spelling stages;
its previous source and complete native hashes remain required.

Packaging uses a 77-byte shell launcher and one fixed LZMA1 ALONE preset 9
extreme/lc2/lp0/pb0/BT4/64 MiB dictionary/nice 32 stream. The ALONE container
has no checksum. Complete file cost includes the launcher, bootstrap and source
literal; no flag, name or codec sweep runs in the builder. Qualification checked
strict source/compiler-argv recovery and two byte-identical encodes.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C | 11,803 | `acd417f903ada227092b0ba371d6ad960ab80b4925ab64633b9b8a2774a9b3aa` |
| Native ELF | 26,360 | `500ccb26bc366c129c77720d9229caac99ae9777d0148a1cc25da4a0fd6552d0` |
| Complete file | 5,400 | `7a04e3d2fac68c4fdca62b6c1fd6e3e71b58da0add25a2b452ab08870d496ec2` |
| Bootstrap | — | `dc65f22b293a451ca1d333f8782d206bd0555b2b1b2c58af5f53c978ad64990c` |

The complete native differs from the previous maintained image. All program
headers, code/data and dynamic symbols/strings/relocations are equal. The exact
allocated-section exception is the GNU build-ID descriptor; the other changed
loaded byte is the ELF header's `e_shoff` low byte at offset 40. Nonallocated
symbol/string/section metadata and offsets also change. Symbol fields other
than the selected private names retain their values, sizes, sections and
attributes. The subsequent automatic-name stage produces the complete same
native bytes as the static-only stage. These are specific observed boundaries,
not general ELF/ABI equivalence or equality to the old complete native.

Historical source/AST, native-byte and strict codec receipts are recorded in
`recipe.json` as provenance, never read by the producer. The frozen experiment
summary is `f2282baf0f54f7c98c517fd9b7c67e3643ceb2ba1a006448e8fd89de30dbf730`.
The normal builder requires the literal new identities above, preserves old
expectations as ancestry, and never updates an expectation from an execution.

Existing core evidence is reused through unchanged canonical/DEV and the
observed code/data/relocation boundary. Selected restoration, legal clocked and
bare GO, fixed startup threads, private path cleanup, exactly one closing
bestmove and physical quit/EOF settlement are checked separately by the
unchanged verifier. Cancellation causality, final playing strength, target
scaling and 4 KiB eligibility remain unproven. Generated binaries, receipts and
archives stay outside Git.
