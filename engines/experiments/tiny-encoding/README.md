# Tiny A encoding experiments

The smallest complete file measured here is **5,283 bytes**, which is **1,187
bytes above 4,096**. It contains the shell launcher and one shared compressed
Python bootstrap/C source stream. These are optional representation experiments;
the canonical Tiny A source and its required algorithms stay unchanged. This
directory does not establish a 4K entry, engine strength or portfolio completion.

The measured domain is **WSL Ubuntu 24.04.4 LTS, x86-64, GCC 13.3.0
(`13.3.0-6ubuntu2~24.04.1`), glibc 2.39, Python 3.12.3**, with **two fixed
search workers, three total startup threads and TT bits 18**. Every native byte
identity statement below is restricted to its frozen input and this toolchain.
The smaller compiler argument lists have no established portability outside
that domain. The 255/508/511-worker target profiles need separate builds,
measurements and runtime qualification.

## Representation changes and gates

`literal.py` supplies raw single/double triple-quoted strings followed by
`.encode()`, bytes `repr`, escaped ASCII bytes triple literals and UTF-8 string
`repr` followed by `.encode()`. Forms that cannot preserve the input bytes are
omitted. CRLF, NUL, invalid UTF-8, quote collisions and trailing backslashes are
handled without normalizing C input. Its AST replacement helper accepts one
canonical `p.communicate(...)` argument, rejects ambiguous calls, validates the
replacement bytes and preserves everything outside that argument. Seven unit
test groups cover 33 boundary fixtures, 128 seeded arbitrary byte inputs,
Unicode byte offsets, CR/CRLF script lines and nonliteral rejection.

`campaign.py` additionally compares these fixed cases:

- Compiler argv represented as a Python list, tuple or fixed string `.split()`.
  The evaluated argument vector must still equal the recorded compiler argv.
- Removal of `-DDEV=0`, `-std=c11` and/or `-pthread`, individually and together.
  Compilation must produce the full native image of the declared identity class.
- Token-aware replacement of `WORKERS` with `2` and `TT_BITS` with `18`, removing
  their corresponding command-line definitions. The combined frozen input has
  seven `WORKERS` occurrences and three `TT_BITS` occurrences.
- A fixed list of public/private function spellings replaced through the owned
  C token helper. Fresh two-character spellings avoid existing identifiers.
  This is a deterministic representation case, not a new identifier search.
- `-s` output compared against a separate stripped baseline, with function
  spelling and fixed-resource combinations admitted only in that class.
- Reversible 8/16/32-word dictionaries in the Python source literal. These restore
  the same complete C bytes; they do not change compiler-visible C identifiers.

Every admitted case restores the recorded transformed C bytes exactly and uses
the recorded compiler argv. It then generates each complete XZ/gzip/bzip2 file
twice and requires byte equality. `accepted` means that native identity passed
and the best complete file did not exceed that campaign's baseline. It does not
mean tournament acceptance or runtime qualification. The campaign reports keep
`runtime_qualified: false`; later runtime evidence lives in separate reports.

The bootstrap's signal-blocked `Popen` handshake, separate compiler process
group, signal forwarding, wait/kill fallback, private `TMPDIR`, cleanup and
fd-exec remain present. `qualify.py` replaces only the source and compiler argv
expressions with sentinels, then requires the remainder of the selected Python
bootstrap to equal the frozen producer's baseline skeleton.

## Two native identity classes

Each input source has its own two reference classes. The unstripped class uses:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

The stripped class adds `-s`. Compiler stdin avoids a changing source filename.
The **entire ELF image**, including any remaining metadata, must match the
reference hash in its declared class. Stripped and unstripped images are never
compared as though they were one identical artifact.

The combined and explicit-pthread campaigns use frozen input source
`56c9984b2e6fbda08be1bd5d30df813c52ef4a3265da8044d35b786c15df4d8c`:

| Class | Native bytes | Native SHA-256 |
| --- | ---: | --- |
| Unstripped | 26,456 | `c31c93a930485b325a8b9279c59374375516d0592e7cea1208f4126307b5222c` |
| Stripped | 22,664 | `0454dfde844f29a962dc2b79b0ff6485dc461cb836d8103a57e811030e8578d4` |

The earlier `baseline` campaign used a different 13,541-byte C input and its own
references (`5a5585a7...` unstripped, `045c1b04...` stripped). Its 5,671-byte
baseline and 5,587-byte selected file are historical measurements of that input.
They must not be substituted for the combined input's identity classes. The
combined input arrived from the separate frozen source-renaming experiment and
starts at 5,419 complete bytes; savings across those different inputs are not
independent additive measurements.

## Compiler flags and observed pthread runtime

The combined case fixes the profile in C, changes the predetermined function
spellings, strips native symbol metadata and renders this exact compiler argv
with `.split()`:

```text
cc -Os -x c - -o x -s
```

The resulting complete file is **5,303 bytes**: 75 bytes of shell prefix and
5,228 bytes of shared XZ data. This is 1,207 bytes over the limit. Its transformed
C input is 11,351 bytes with SHA-256
`49aa4d484458d0e4f6d14850fb2260a7007ea40f588003131d43a516d06a592e`.
The source and compiler argv are inside the compressed Python payload; the
75-byte prefix is not the complete restoration overhead.

Although this argv omits both `-pthread` and `-std=c11`, the actual restored
native image has the stripped reference hash above. `qualify.py` inspected that
running process and observed three startup threads, a deleted ELF replacing the
wrapper, no compiler child, and a removed owned temporary directory. `readelf`
on that actual image reported only `libc.so.6` as `NEEDED` and unresolved dynamic
symbols `pthread_create@GLIBC_2.34` and `pthread_join@GLIBC_2.34`. The two pthread
workers remain active components of the program. Removing these flags is a
measured local identity result; it is not an assertion that arbitrary GCC,
glibc, headers or operating systems admit the same command.

| Combined representation | Exact additional flag policy | Complete XZ bytes | Evidence |
| --- | --- | ---: | --- |
| `combined-fixed-stripped` | Neither `-pthread` nor `-std=c11` | 5,303 | Native compiler gate and actual restored-image/startup qualification |
| `combined-fixed-stripped-pthread` | `cc -Os -x c - -o x -pthread -s` | 5,307 | Compiler-stdin native identity and repeatable complete files |
| `combined-fixed-stripped-c11-pthread` | `cc -std=c11 -Os -pthread -x c - -o x -s` | 5,315 | Compiler-stdin native identity and repeatable complete files |

The 5,307/5,315-byte wrappers have not acquired independent wrapper runtime
qualification from these reports. Their compiled native bytes match the same
stripped class on this host. Retain that distinction until those exact wrapper
hashes are executed and checked.

## Rejected literal and dictionary costs

In the historical 5,671-byte baseline input, the canonical/raw-single/raw-double
forms all measured 5,671 complete bytes. Bytes `repr` and both ASCII bytes triple
forms measured 5,675; UTF-8 string `repr` plus `.encode()` measured 5,679. Their
source restoration and native identity passed, but the complete files grew.
List, tuple and string-split command rendering alone all measured 5,671 bytes.

The 8/16/32-word dictionaries measured 5,711/5,719/5,763 complete bytes. Their
decoder text and dictionary cost exceeded any shared-compression benefit. These
cases were rejected for file growth, not silently discarded as semantic errors.
Adding `-s` alone also increased the historical wrapper to 5,675 bytes despite
shrinking its restored native image. Selection uses the complete submitted file,
not the raw C, ELF or isolated compressed-payload size.

## Seven bounded XZ parameter trials

`recompress.py` performs exactly seven fixed trials against the selected
5,303-byte file. It first reproduces the original default XZ stream exactly,
keeps the 75-byte shell prefix byte-identical, keeps CRC64, preset `9e` and
`lp=0`, and changes only `lc`/`pb`. Each trial is independently compressed twice
and decoded with both Python and external `xz -dc`.

| `lc` | `pb` | Complete bytes | Delta from 5,303 |
| ---: | ---: | ---: | ---: |
| 3 | 2 | 5,303 | 0 |
| 0 | 0 | 5,287 | -16 |
| 1 | 0 | 5,287 | -16 |
| **2** | **0** | **5,283** | **-20** |
| 3 | 0 | 5,291 | -12 |
| 4 | 0 | 5,335 | +32 |
| 3 | 1 | 5,295 | -8 |

All seven decode to the same 12,341-byte Python+C+compiler-argv program, SHA-256
`cbf2c1f024929aedb38da64b4c8f9b5d962a9bd2d2b36f8fff2b22f0034ab633`.
The selected 5,283-byte file has SHA-256
`798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645`.
It passed five actual shipping verifier groups: protocol, lifecycle, bounded
16-ply self-play, EOF and quit. Three startup thread IDs were observed and
preserved within each process.

The recompression report initially records native evidence reuse through
unchanged decoded Python/C/argv. A subsequent qualification of the exact
5,283-byte wrapper independently captured its running `/proc/exe` image and
matched the same `0454dfde...` stripped native hash. It also confirmed three
startup threads, unchanged bootstrap skeleton, the deleted ELF replacing the
wrapper, no compiler child, removed temporary files and the same pthread symbols.
An independent clean campaign and all seven clean XZ trials reproduced the
complete file bytes, including the selected hash.

The actual wrapper's five shipping tests are separate positive runtime evidence.
Those tests retain `cancellation_causality: unproven`: they observe
process work before a reset/stop/termination and receive the legal result after
it, without attributing the result to one internal cancellation path. They
establish neither Elo nor high-thread-count scalability.

## Frozen recipes and external evidence

Campaigns copy their producer, C token helper, literal helper, input C and
reference wrapper into an external `frozen/` directory. Current `campaign.py`
also freezes itself and records its hash. Helpers are loaded by those explicit
frozen paths. The historical baseline and combined directories predate copying
`campaign.py` itself; combined records its recipe hash, but its exact old recipe
file is not in that directory. The explicit-pthread campaign contains the
frozen recipe as well as all three shared helper snapshots.

The shared frozen helper hashes are:

| Helper | SHA-256 |
| --- | --- |
| `pack_stream.py` | `b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e` |
| `rename_c.py` | `9d7d09e2787cfda21701384be94ed00d588165574da5d8aacdf731fcb317cbe5` |
| `literal.py` | `e95e3c81eb0037e5c4c0ad7924fa55ae2ca14f481dae5ca427928f5c48c7f4da` |

`qualify.py` is a separate verifier that imports the checkout's `campaign.py`
and the report's frozen stream producer. Its `--wrapper` option additionally
requires an exact expected wrapper hash, an identical complete shell prefix,
and decoded bytes equal to the selected campaign bootstrap before inspecting
the actual recompressed native process. Its report proves the observed image
and skeleton checks; it does not make the historical campaign self-contained.
Source order establishes cleanup before fd-exec, and runtime inspection confirms
absence of files at UCI-ready. The inspection occurs after the handshake, so the
report field named `temp_removed_before_engine_input` should be read with that
source-order evidence, not as an independent pre-input filesystem sample.

The measured reports are outside Git:

```text
/home/stemxstudio/rove4k-tiny-encoding-baseline-20261020/results.json
/home/stemxstudio/rove4k-tiny-encoding-combined-20261020/results.json
/home/stemxstudio/rove4k-tiny-encoding-explicit-pthread-20261020/results.json
/home/stemxstudio/rove4k-tiny-encoding-native-qualification-20261020/identity.json
/home/stemxstudio/rove4k-tiny-encoding-xz-20261020/results.json
/home/stemxstudio/rove4k-tiny-encoding-xz-shipping-20261020/results.json
```

Final Windows evidence is retained at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-encoding-20261020-evidence/`.
It includes `summary.json`, `combined.json`, `clean-repro.json`, `xz.json`,
`xz-clean-repro.json`, `shipping.json`, `identity.json` and the actual
`rove4k-A-encoding-5283.sh` file. This final `identity.json` refers to the
5,283-byte recompressed wrapper; the older Linux native-qualification directory
above refers to the 5,303-byte wrapper.

## Reproduce outside the checkout

Run from the repository root in the measured Linux toolchain. Every output path
must be new, absolute and outside the checkout. The current helper snapshots
must reproduce the declared baseline before a campaign can proceed; if they
drift, stop and recover the recorded recipe/helpers instead of weakening that
check. These commands replay the fixed cases without introducing another search.

```sh
python3 -B -m unittest discover -s engines/experiments/tiny-encoding -p test_literal.py -v
python3 -B engines/experiments/tiny-encoding/campaign.py \
  --source /home/stemxstudio/rove4k-tiny-encoding-explicit-pthread-20261020/frozen/main.c \
  --baseline-wrapper /home/stemxstudio/rove4k-tiny-encoding-explicit-pthread-20261020/frozen/reference-wrapper \
  --cases literal-canonical,combined-fixed-stripped,combined-fixed-stripped-pthread,combined-fixed-stripped-c11-pthread \
  --out /home/stemxstudio/rove4k-tiny-encoding-replay-new
python3 -B engines/experiments/tiny-encoding/qualify.py \
  --report /home/stemxstudio/rove4k-tiny-encoding-replay-new/results.json \
  --out /home/stemxstudio/rove4k-tiny-encoding-native-replay-new
python3 -B engines/experiments/tiny-encoding/recompress.py \
  --baseline-wrapper /home/stemxstudio/rove4k-tiny-encoding-replay-new/01-combined-fixed-stripped/packed/xz/x \
  --expected-sha256 283a38e77dd69f66b397feb95d1313b42e66c1f1cd4c3287755d2dc222e2ad96 \
  --expected-native-sha256 0454dfde844f29a962dc2b79b0ff6485dc461cb836d8103a57e811030e8578d4 \
  --out /home/stemxstudio/rove4k-tiny-encoding-xz-replay-new
python3 -B engines/experiments/tiny-encoding/qualify.py \
  --report /home/stemxstudio/rove4k-tiny-encoding-replay-new/results.json \
  --wrapper /home/stemxstudio/rove4k-tiny-encoding-xz-replay-new/03-lc2-pb0/x \
  --expected-wrapper-sha256 798c1492fcfc5734c9794704b5575a19755618e19d51aa12950302044065b645 \
  --out /home/stemxstudio/rove4k-tiny-encoding-xz-native-replay-new
python3 -B engines/tests/verify.py \
  --manifest /home/stemxstudio/rove4k-tiny-encoding-xz-replay-new/validation-manifest.json \
  --suite shipping --startup-threads 3 --plies 16 \
  --out /home/stemxstudio/rove4k-tiny-encoding-xz-shipping-replay-new
```

Runtime dependencies remain the recorded `sh`, `tail`, `xz` (or the selected
`gzip`/`bzip2` decoder), `python3` and `cc`. Their names are checked against the
pinned TCEC 4K program list by the producer; full rules eligibility remains
unproven. Training, AWS, strength testing and target-machine acceptance are
outside this experiment.
