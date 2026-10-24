# Rove4k engine portfolio

The readable engine sources are in `c/` and `rust/`. Each language compiles A–F
independently. A build selects one family, one parallel policy, one resource
profile and any explicit cross feature. The executable has no runtime family,
worker-count or hash-size selector. Development protocol commands are selected
at compilation.

The A–F implementation plan remains the scope. Building a variant does not prove
that its named algorithm, complete chess behavior, parallel semantics, playing
strength or final 4,096-byte submission requirement has passed acceptance. The
build report records measured files and individual runtime checks without
turning missing evidence into completion. Frozen E inference is included; model
training and AWS execution are outside the current implementation task.

## Maintained compact submissions

The reviewed `d8bdd0e1` checkpoint separates the default compiler-owner
contract from explicit smaller packaging choices. The table reports complete
files, including header and payload; it is not a tournament eligibility or
strength ranking. These compact entries are separate from the generic build
examples below.

| Engine / policy | Default grace | Explicit Bash shell | Evidence scope |
|---|---:|---:|---|
| A / full | 4,785 B | 4,232 B | Grace reproduced/executed; shell cost measurement only |
| B / full | 5,259 B | 4,712 B | Grace reproduced/executed; shell cost measurement only |
| C / full | 4,924 B | 4,375 B | Grace reproduced/executed; shell cost measurement only |
| E / full | 4,878 B | 4,323 B | Grace reproduced/executed; shell cost measurement only |
| [F2 / full](compact/tiny-entry-f/README.md) | 4,576 B | 4,026 B | Each reproduced and passed its own selected runtime contract |
| [F8 / full](compact/tiny-entry-f-resource8/README.md) | 4,588 B | 4,028 B | Separate eight-worker reproduction and selected runtime |
| F2 / material-noise | 4,616 B | Unsupported | Reduced evaluation/learners; separate feature policy |
| F2 / material-move-tt | 4,342 B | Unsupported | Reduced evaluation/learners/TT; separate feature policy |

Full F remains the default feature policy. Its Bash selections preserve full
features but change compiler cancellation and delayed cleanup. The measured
4,011-byte sh/inherit candidate was rejected for its cleanup-child condition.
F2/F8's 70/68-byte margins therefore establish file size only. Current `legacy`
choices preserve immediate predecessors, rather than restoring historical
old-owner minima. C D's 5,527/6,037-byte scalar/HQ own-ELF files and Rust paths
have separate packaging contracts and are not grace/shell rows in this table.

For complete source/native/whole identities, wrapper differences and execution
receipt scopes, read [the wrapper implementation record](../docs/WRAPPER-IMPLEMENTATION.ko.md).
Source-freeze PENDING notes in entry histories are not overwritten by later
results; current summaries link the later evidence explicitly.

## Build on Linux, including WSL Ubuntu

The build tool uses Python 3 standard library, a C11 compiler and Rust 2024
compiler. C SIMD candidates require AVX2. Linux x86-64, glibc and pthreads are the
current target. On WSL, use Linux `cc` and Linux `rustc`, rather than Windows
executables found through the inherited PATH. A normal Linux checkout gives Git
revision metadata; a Windows managed worktree can still build through `/mnt/c`,
but Git's Windows absolute worktree pointer may be unavailable to Linux Git.
That lookup is recorded as unavailable and actual source hashes remain present.

Every output directory must be absolute, outside the checkout and new or empty.
Existing artifacts and failure records are preserved. For example:

```sh
python3 engines/scripts/build.py \
  --out /tmp/rove4k-dev-build \
  --profile local-dev --languages c,rust --variants ABCDEF \
  --no-pack --reproduce

python3 engines/tests/verify.py \
  --manifest /tmp/rove4k-dev-build/build.json \
  --out /tmp/rove4k-dev-verification --quick

python3 engines/scripts/build.py \
  --out /tmp/rove4k-shipping-build \
  --profile local-ship --languages c,rust --variants ABCDEF \
  --self-elf --reproduce

python3 engines/tests/verify.py \
  --manifest /tmp/rove4k-shipping-build/build.json \
  --out /tmp/rove4k-shipping-verification --suite shipping
```

`--language` and `--variant` are aliases for their plural forms. `--cc` and
`--rustc` select build compilers, including an explicit Linux Rust installation
path. Source launchers resolve `cc` or `rustc` from the target's PATH. The exact
flags, fixed environment, source byte hashes, compaction hashes, compiler
versions, Python/glibc/OS, profile and tooling hashes are written to `build.json`.
`--optimize size` uses C `-Os` / Rust `z`; `--optimize speed` uses `-O2` / Rust `2`.
Neither choice is reported as the strongest playing engine.

`--source-root /absolute/snapshot` reuses a tree containing `c/`, `rust/` and
`model/`. Each campaign copies its exact admitted inputs to `sources/`; another
campaign can use that directory to compare feature flags on identical source
bytes. Source snapshots are taken before the first compilation. Development
model scripts, JSON, documentation and standalone model C fixtures are excluded
from production source archives.
The exact scripts, loader sources, profiles and structural templates are also
preserved in `recipe/`. Transformations execute those preserved bytes, so a later
agent edit cannot change an ongoing campaign. To repeat the complete recipe,
invoke `recipe/engines/scripts/build.py` with `--source-root` pointing at the old
`sources/`, a new external output directory and the same flags. Each engine has
its explicit `generation_config` and SHA-256, in addition to source hashes.
The manifest's original executable entry also carries its expected program
SHA-256, fixed startup/maximum thread total and 60-second startup bound. These
are validation requirements: declaring them does not prove successful startup
or persistent thread identity. When selecting another artifact for verification,
pin that artifact's actual SHA-256 and carry the same fixed thread requirements.

`--c-lto on` adds C cross-translation-unit optimization as an explicit compiler
experiment. The default is `off`; Rust's independently declared LTO recipe is
unchanged. Compare final complete files and runtime behavior before choosing a
compiler experiment.

`--parallel loose|root|groups|pals|hybrid` sets `ROVE_PARALLEL=0..4`; the default
is `loose`. `--model` sets `ROVE_MODEL=1` for explicit SIMD/frozen-model cross
candidates, which receive separate `-model` report identities. The baseline does
not silently acquire that feature. Verify each combined implementation before
treating a cross candidate as functional.
F currently requires `loose` to preserve complete-root MTD(f) semantics; an
unsupported F/policy combination is rejected explicitly. `--hq auto` selects HQ
sliding attacks only for D. For an explicit D scalar/HQ comparison, select
`--variant D --hq scalar` or `--variant D --hq hq`; the effective compile-time
`ROVE_HQ` value is recorded for both languages.
F also exposes compile-time `--f-tt paired|single` and
`--f-guess previous|parity` experiments. Defaults retain paired bounds and the
previous-depth guess. Nondefault choices require `--variant F`; structural
overlays are rejected until those combinations are qualified. C receives
`ROVE_F_SINGLE`/`ROVE_F_PARITY` macros; Rust receives the corresponding fixed
environment and `--cfg rove_f_single` for single-bound storage. The manifest
records these as search/storage experiments rather than lossless notation
changes.
The cross flag requires `--variant C` explicitly. `--structural-compact` adds a
separately named C form generated from `compact/c/generate.py`, followed by the
real preprocessor, reachability pruning and lexical compaction. Structural
changes receive their own source/recipe hashes and final-file comparisons;
ordinary byte identity is measured and never assumed for that form.
`--structural-search` appends an additional generated search layout while keeping
the previous structural form. `--small-worker` appends another worker-storage
form and requires structural search, a shipping profile and the loose policy.
These are separately measured candidates; a source or native saving is not
automatically an improvement to every complete-file format.

`--rust-structural-compact` adds two separate Rust source forms: the guarded
structural producer output and that output followed by lexical compaction.
Both remain in the comparison because an extra lexical pass can increase the
complete compressed file. This optional producer requires `--variant A`, a
shipping profile and the loose policy. It binds the exact six canonical Rust
production files from checkpoint `de5676d` and rejects changed source or
unsupported configurations explicitly. The binding admits audited LF/CRLF
equivalence, with actual raw input hashes/bytes, normalized binding hashes and
CRLF counts recorded separately; other content changes and lone CR fail.
The model input is omitted only within
the admitted A/MODEL0 configuration. Original and lexical baselines remain in
the build, and the manifest records all producer/helper/template hashes and
input/output source hashes. `--reproduce` independently reruns the producer
before the native and complete-file reproduction checks. The producer's
[documented scope](compact/rust/README.md) and its original differential proof
do not establish other-family support, large-machine scaling or 4K eligibility.

`--shipping-operations` adds another separate C form and requires the loose
shipping profile, structural search and small-worker storage. It specializes
the shipping stop/diagnostic paths, with the non-B arity transformation applied
only after the real compiler has selected conditional branches, before pruning
and lexical compaction. B retains its learning-related argument behavior. The
manifest records both preparation and post-specialization operations; all
earlier source forms remain available for cost and behavior comparisons.

`--model-format varint|static16` selects the frozen model's production
representation. The default `varint` preserves admitted source bytes exactly.
`static16` requires E, or the explicit C `--model` cross candidate, and receives
a separate `-static16` identity. Its pure producer changes only the selected
language's frozen coefficient header and inference consumer; canonical input
sources remain in `sources/`, while the engine's `sources` and
`generated_sources.original` hashes identify the actual transformed compilation
inputs. `model_representation` records the coefficient hash and changed source
hashes, and `--reproduce` repeats the transformation independently. The model
producer and its canonical JSON are frozen under `recipe/`; development fixtures
and producer scripts remain outside the final runtime archive. Compare complete
files and validate both inference and search before selecting a representation:
a smaller coefficient payload alone does not establish a smaller engine.

`--identifier-compact --identifier-trials 64` adds bounded identifier-spelling
trials to the latest requested C form. Every accepted transformation must compile
to the exact same full native SHA-256 as its baseline with the same toolchain and
configuration. Compile failures and byte mismatches reject the candidate and
retain trial sources and diagnostics. The lexical candidate heuristic is not a
proof of C scope or ABI equivalence. The actual native byte gate is required,
and the separately measured compressed result may still be larger. With
`--reproduce`, the search runs independently again and accepted source bytes must
also match before native and complete-file reproduction checks.

## Fixed resource profiles

The profiles in `profiles/fixed.json` count the engine's input/control thread
alongside its search workers. Search worker 0 coordinates the other workers.
TT bits state the compile-time entry count exponent, rather than a claimed byte
budget: actual TT entry layout and additional worker/history/model memory also
count. Allocation and thread startup belong to engine startup.

| Profile | Search workers | Expected total engine threads | TT bits | Development |
| --- | ---: | ---: | ---: | --- |
| local-dev | 1 | 2 | 16 | yes |
| local-smp | 2 | 3 | 18 | yes |
| local-study | 4 | 5 | 18 | yes |
| local-ship | 2 | 3 | 18 | no |
| target256 | 255 | 256 | 26 | no |
| target509 | 508 | 509 | 26 | no |
| target512 | 511 | 512 | 26 | no |

The build tool executes only small local profiles, bounded by eight available
logical CPUs. The target profiles are compile-only in this tool even on a large
host. Their successful compilation does not prove resource availability,
thread-start success, memory consumption or many-core scaling. No training,
cloud connection or paid instance is started by these recipes.

## Source compaction and complete-file packaging

The script preserves readable originals. It compiles original and lexically
compacted forms. The lexical pass removes comments and redundant whitespace,
retains C preprocessor line boundaries, and handles Rust raw strings, nested
comments, lifetimes and reserved token adjacency. It does not rename arbitrary
identifiers or claim AST equivalence. Compilation and actual native hashes expose
differences; protocol and engine checks cover behavior beyond successful parsing.

For C packaging there is an additional compiler-context specialization. The
selected compiler processes the actual headers and conditional directives using
`-E -fdirectives-only`. The tool retains engine-origin source, flattens local
headers, restores system include directives, and removes inactive family and
development branches. It does not expand every libc header into the submission
or guess the values of conditional expressions. Each translation unit remains
independent. `byte_identical_to_original_native` reports whether the generated
native file actually matches the original build, including all executable bytes.

General 4K candidates use Python 3 with three standard codecs: DEFLATE/zlib,
bzip2 and LZMA. Both plain Python/base85 and executable ZIP transports are
measured. ZIP transport stores compressed binary directly, with deterministic
archive metadata and the compressed bootstrap included in the measured size.
Source candidates contain all required own source/model bytes and fixed compiler
arguments; native candidates contain the complete native ELF. Nothing is fetched
at runtime.

The Python bootstrap restores to an owned temporary directory. Source candidates
compile in a private process group; SIGINT/SIGTERM forward to that group and wait
before cleanup. The finished ELF is opened as a file descriptor, every restored
file is removed, and descriptor execution replaces Python. The searching engine
has no extra Python parent process and leaves no restored executable behind.
SIGKILL cannot run Python cleanup if it interrupts the restoration/compile phase;
ordinary engine execution begins only after that cleanup has finished. Actual
startup must still meet the event's 60-second limit. Compiler version differences
on the final target remain a deployment consideration.
The compiler's `TMPDIR` also points inside the owned directory, including its
assembler/linker intermediates. A missing compiler retains its original error
and still removes the restored source tree.

The own-ELF path is implemented by
[`scripts/elf_loader.py`](scripts/elf_loader.py) and its
[`elf-loader` sources](scripts/elf-loader/README.md). It embeds a handwritten
decoder, restores the exact complete ELF to an anonymous memfd, and invokes
`execveat`. It has no interpreter or external compiler/decoder program at runtime.
The original payload may retain the allowed system dynamic linker/libraries.
Linux policy must permit executable memfd use. Self-file identity, privileged
file semantics and `AT_EXECFN` identity are outside this packaging contract.
The loader measures both an unfiltered payload and a reversible E8/E9 operand
filter. Its automatic choice compares the two complete ELF files, including
the filter's inverse code, and prefers the unfiltered file on a tie. Both
candidate sizes, hashes and exact compiler arguments remain in the report;
a smaller compressed payload cannot hide a larger decoder.

Each final candidate is named `x` within its own report directory. Reported bytes
include its executable header, restoration/bootstrap, payload, encoding, archive
metadata and fixed configuration. `under_4096_bytes` is a measurement, not
tournament approval. `rules_eligibility` stays unproven until the final file,
startup, allowed dependencies and complete engine requirements have been checked
against the [specific TCEC 4K rules](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853).
Own-ELF candidates never receive an external-decoder exemption.

`--reproduce` actually compiles second original/compacted/specialized copies in
different directories and compares SHA-256. It does not infer reproducibility
from a cache hit. `build.json` remains `complete: false` if generation fails, and
all earlier measured candidates remain available. Its minimum-size field means
the smallest measured complete file in that campaign, with each runtime result
shown separately; it is not an adopted or fully accepted tournament file.

Focused packaging checks are reproducible without large engines:

```sh
RUSTC=rustc python3 -m unittest discover -s engines/scripts -p 'test*.py'
RUSTC=rustc python3 engines/scripts/elf-loader/test_loader.py
```

The first suite compiles small C/Rust lexical fixtures and exercises both
transports/codecs, descriptor execution, argv/environment/stdio/status,
pre-execution cleanup and interrupted compiler lifetime. The own-ELF suite also
checks corruption rejection, threaded C/Rust payloads and byte reproduction.
These narrow fixtures do not replace final A–F chess and concurrency validation.
