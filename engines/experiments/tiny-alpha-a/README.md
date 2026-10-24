# One fixed A spelling candidate with PLY preserved

This independent experiment freezes maintained A5129 at
`418435c75ea68e21b2a0fde3723cf8c4fb42c524`. It retains the exact 31 aliases
already used by A in the reviewed 73-name A/F policy, including gaps between
aliases. It preserves all eight PLY code uses as macro identifiers. It makes no
engine, profile, compiler, bootstrap, launcher or codec policy change, and does
not promote the maintained entry.

| Representation | Original | Candidate | Saving |
| --- | ---: | ---: | ---: |
| Readable engine C | 24,820 | 24,820 | 0 |
| Specialized shipping C | 10,855 | 10,606 | **249** |
| Complete native ELF | 22,672 | 22,672 | 0; full bytes equal |
| Complete executable launcher | 5,129 | **5,072** | **57** |

All sizes are bytes. The complete file still exceeds 4,096 by 976 bytes.
Lexical source savings and complete-file savings are separate measurements.
There is no 4KiB, strength, NPS, SMP scaling or whole-plan acceptance claim.

## Fixed ownership and literal policy

`policy.json` fixes the 31 old/new pairs, the source/candidate SHA values, every
token count and the expected arithmetic. `ownership.json` records one owned
typedef (`Entry`), two private member spellings (`lock`, `history`) and 28
automatic-local/parameter spellings. The aliases are copied literally from the
original reviewed policy; no new alias pool, permutation or candidate search is
run. All 31 appear in shipping C: 95 substitutions save 249 bytes.

Functions, globals, static-storage objects, external APIs, atomic/pthread names,
all directives and string/comment regions remain protected. Default admission
rejects every identifier outside the exact role-audited list and two resource
spellings. Freshness includes the frozen A readable input and shipping raw and
phase-two words, including opaque regions. Actual expanded headers and final
macro names are checked independently before native compilation. This is an
A-only consumer boundary; it does not claim to rerun joint A/F freshness.

Only WORKERS=2 and TT_BITS=18 remain in `resource_literals`, each with zero code
uses in the already specialized source. PLY is explicitly protected and must
have eight code uses before and after transformation. Resource substitution
saves zero bytes. The directives occupy 432 bytes and all 53 opaque regions
are preserved in order and byte for byte.

Six bounded pure source fixtures passed. Independent precompile reviews checked
the literal aliases/roles/protected names, new recipe and shipping-source pins,
own-input closure and the actual PP/native/codec gate path. A separate read-only
token comparison of the prepared original and candidate confirmed the 95 edits,
all literal counts, PLY 8-to-8 and opaque preservation. These reviews did not
import the producer, compile, run tests again or execute engines.

## Closed ordinary-source producer

`control/` owns the historical nine-file A entry, five producer helpers and two
existing runtime helpers: 16 files. `reference/` owns five frozen prior-policy
ordinary files. The generic opaque scanner and rewrite logic are reused from
that reference; its old B/C/E public transform is never called. `recipe.json`
binds normalized input bytes, original raw working bytes, historical expected
outputs and all four executed policy inputs. `.gitattributes` requires LF.

```sh
python3 -I -B engines/experiments/tiny-alpha-a/build.py \
  --out /absolute/new/alpha-a-cost
```

The normal build reads only its own ordinary sources. It does not read an AF
generated source, report, artifact or mutable canonical helper. The old joint
policy SHA is provenance metadata, not a build dependency. An input-only
`prepare.py` reproduces the pinned historical shipping C using the owned
ordinary closure; it performs no native compilation or engine execution.

The qualified target remains Ubuntu 24.04.4 x86-64, GCC 13.3.0, glibc 2.39,
Python 3.12.3 and xz 5.4.5. The original native argv remains
`cc -Os -x c - -o x -s`. Its existing lack of a separate `-pthread` link flag
uses the qualified merged-pthread glibc environment; this experiment does not
expand the supported compiler/libc domain. The configured readable preprocessor
retains `-std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18` exactly as before.

## Exact PP, native and whole-file comparison

The original producer independently reproduced the original source, native,
complete file and unchanged DEV source/native twice. For actual final `-E -P`
and `-E -dM`, only the sole `-o x` output pair is removed from the native argv;
`-Os` and `-s` remain and no extra resource defines are added. The complete
candidate expanded output is reversed using identifier aliases alone. Raw
whitespace and numeric spellings are preserved, with zero numeric inverse
replacements and no token normalization.

The full 88,808-byte expanded original and inverse are identical at SHA
`44f815ff1a83db4e878fc30527b787921e745cb21d8e8213ed8b6dd699240c39`.
Both complete final macro dumps are 44,984 bytes at SHA
`3f26d31a8c0949cfe0d062bc723f29611b0190c366fab4d909e960cd760a7fb9`,
with final resource state `{PLY:128}`. A separate unchanged-readable probe uses
the exact configured profile and confirms WORKERS=2, TT_BITS=18, PLY=128; that
probe is distinct from the actual final compiler context.

Both candidate native builds must equal the original FULL native SHA before
either candidate codec is called. The complete 22,672-byte ELF, including
build-ID and nonallocated sections, equals
`84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a`
in both attempts. DEV remains untransformed and reproduced twice at original
source SHA `41ab9f0f5d28183b76833d038c40e0bb6a2ee6ef9303766c293dd577680a4c9c`
and native SHA `8733dbf0814a2c2545251f6e0e17d243ecfd41fce7853fb325ca9720fedd1102`.

Packaging retains the original 77-byte launcher and Python source-literal
logic, ALONE LZMA1 preset 9 extreme, lc2/lp0/pb0, 64MiB dictionary, no check and
header `0200000004ffffffffffffffff`. Strict Python decompression checks EOF and
trailing bytes; independent CLI `lzma -dc` must restore identical bootstrap
bytes. Both independent complete-file generations matched.

| Candidate item | SHA-256 |
| --- | --- |
| Shipping C, 10,606 bytes | `252d87ed58df8c86b2d7898fafcedc0bed1c3bab447846b484e5afbdd5b27ac3` |
| Complete 5,072-byte file | `47370ce2d27e84349eade3f7b3ff698f5e76f1cb382531e409420b6dbbbb8f2d` |
| Restored bootstrap | `7278a0af96c7217cbdec383692a4b7996d6c73b096cd32ea2dc2c4060caf558c` |
| Literal A policy | `e1d5daf3636851711d08309b772edf7a3546bfffeb402d745d33eaaf80560244` |

The cost receipt is
`/home/stemxstudio/rove4k-tiny-alpha-a-first-20261020/results.json`, SHA
`64c7908e6b560fa1f2c798c2f33de36a51af52a210d7f9f7db21a01cc2b1fe15`.
The bounded command exited 0. No engine executes in this cost producer.

## Separate candidate and retained original failure

The prior `tiny-alpha-af/` experiment remains unchanged. Its A candidate also
had 10,606 bytes but replaced PLY with equal-length 128 literals, producing a
different source SHA and failing the strict raw full-PP inverse at byte 81960.
No A native, package or engine was produced there. This experiment is the
explicitly approved new macro-preserving candidate, with its own ordinary
inputs, literal recipe and independent proof. It does not repair or relabel
the old failure. F's separately qualified result and promotion are outside this
folder.

Historical A board/search/rules/SMP qualification is reused only through exact
complete native-image identity. A broad board/search suite, games, sanitizer
campaign, performance benchmark and new engine policy are not rerun here.
Fresh selected-wrapper evidence is recorded separately after the two approved
quit/EOF restoration sessions.

## Two actual selected-wrapper sessions

The runtime adapter binds the literal new A cost receipt, all 27 producer inputs
(16 controls, five references, six producer inputs), the selected files and both
independent candidate attempts: 12 artifact pins. It copies its own frozen A
verifier and runtime helpers unchanged into a separate execution mirror. Only
five recipe expected fields change there: source bytes/SHA, whole bytes/SHA and
bootstrap SHA. Native, DEV, readable and historical qualification metadata stay
unchanged. The real raw cost receipt is copied byte for byte as `build.json`;
no substitute build-success report is manufactured.

`run_owned_verifier` is byte-identical to the separately reviewed and stub-tested
corrected ownership function: 2,583 bytes at SHA
`b9d830bfbe3fae4dec71826063f8e273641e807e75e0a21c5ded33f4838bc644`.
The A adapter checks that embedded source identity without reading any AF
runtime source or report. All post-Popen saves and wait operations are protected
by BaseException cleanup, bounded SIGINT/kill/reap and best-effort failure
recording; forced cleanup cannot be called success. The new A adapter required
no further stub/process variant. Independent read review preceded execution.

```sh
python3 -I -B engines/experiments/tiny-alpha-a/verify.py \
  --out /absolute/new/alpha-a-runtime
```

The original A verifier ran once and created exactly two actual wrappers, one
closed by `quit` and one by EOF. Each returned a legal result for white-zero,
black-zero and bare finite GO, then one closing bestmove during a separately
observed active clocked GO. All eight GO epochs settled with return code 0 and
empty stderr. Both restored `/proc/<pid>/exe` images had the original full
native SHA, exactly three stable startup TIDs and empty observed child lists at
the startup boundary. The private executable paths were already deleted. Both
main processes were absent and all output readers finished after exit. Every
original input, pinned artifact and execution-mirror file was rechecked after
the sessions.

Observed activity and physical completion do not prove that cancellation caused
search completion; `cancellation_causality` remains `unproven`. These are fresh
restoration/lifecycle observations for the exact selected file. They do not
extend historical core, strength or scaling qualification. No other engine or
additional fixture campaign ran.

The executed adapter is 15,206 bytes at SHA
`00dd19229b64d849be4c376bbbfebdd6fc61edcadbcd875e0267ee8cde5f4f22`;
the literal runtime pins SHA is
`3bd1fae9d8fcdcd9fb74b2a911b2268612786d5641ee8ba938f07397c8028fb2`.
The adapter receipt is
`/home/stemxstudio/rove4k-tiny-alpha-a-runtime-20261020/runtime.json`, SHA
`c7e8a9ef92184e6a30f5e8d7a7d5ebe067eeaade38ab6651539a5b77e0a549c7`.
The unchanged original verifier's fresh receipt is `fresh/runtime.json`, SHA
`03fb9fb7211bf186b8eb58b03bb87762b4a30b5aa378056c30f12ca4b606ef39`.
The bounded adapter command and its owned verifier both exited 0. All owned
commands and descendant agents are terminal with no live execution handles.

The runtime command deliberately binds this historical external cost receipt
and artifacts. The normal producer remains independent of generated evidence.
The final ordinary-source inventory and raw evidence index is
`C:/Users/강민수/Documents/Codex/rove4k-tiny-alpha-a-20261020-evidence/summary.json`.
This folder is frozen for a separately assigned maintained-entry promotion;
it performs no promotion itself.
