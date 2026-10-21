# NVCompact

NVCompact means **N-version compaction**: preserve the original, construct
explicit alternatives, verify their applicable contracts, and compare the
complete deliverable. It is an internal Rust tool in the Rove4k monorepo.

The source version is 0.6.0. Node supplies the `nvcompact` npm command boundary;
Rust performs the active compilation orchestration, spelling transformations,
packing, reproduction, resource checks and UCI probes. The archived Python 0.3
implementation is reference material for past results.

Version 0.6.0 adds advisory-only C/C++/Rust scalar-domain analysis, bounded
typed n-version suggestions, constant and unused-declaration diagnostics, and
final-file repeated-byte inspection. It also reduces repeated search planning,
cache lookup and decode-verification work. See the [0.6.0 release notes](docs/RELEASE-0.6.ko.md)
for the supported subsets, measured gains and limits. The source-search and
retained-attempt features from [0.5.0](docs/RELEASE-0.5.ko.md) remain available.
Historical measurements below retain their recorded inputs and tool versions.

## Build and package

The current execution environment is Linux. Use Node 22 or later, Rust/Cargo,
and the build dependencies for liblzma, zlib and libbz2. C/C++ comparison builds
need their declared compiler; typed C transformations and C/C++ advice also need Clang.

```sh
npm ci --ignore-scripts
npm run build:nvcompact
npm exec -- nvcompact --version
npm exec -- nvcompact doctor --json
npm test
npm run test:core
```

`npm run build:nvcompact` uses Cargo with `--locked --release`. By default, native
outputs and build metadata live in an external OS temporary directory keyed by
the repository path. Set `NVCOMPACT_ARTIFACT_DIR` to choose a durable external
directory. An external `CARGO_TARGET_DIR` is honored. Output directories inside
Rove4k are rejected by these npm build scripts, including symlink aliases.

```sh
export NVCOMPACT_ARTIFACT_DIR=/absolute/external/nvcompact-artifacts
export CARGO_TARGET_DIR=/absolute/external/rove4k-target
npm run build:nvcompact
npm run pack:nvcompact -- --no-build
npm run verify:package
```

The public package name and executable are both `nvcompact`. The monorepo stays
private to npm, while its package metadata allows public publication.
`pack:nvcompact` prints the actual tarball location and
hash, includes the matching Rust executable, and stages its files outside the
repository. Omitting `--no-build` first builds current source. The explicit
`--no-build` path checks recorded source, host and executable fingerprints.

Install the resulting tarball with
`npm install --offline --ignore-scripts /absolute/path/nvcompact-0.6.0.tgz`.
The npm target is Linux x64/glibc, with release CI on Ubuntu 24.04. It does not
claim universal binary compatibility. `NVCOMPACT_BIN` selects another
explicit Rust executable without triggering a build or another backend.

The [publishing guide](docs/PUBLISHING.md) documents a verified tarball's manual
first upload from the configured personal npm account and the separate OIDC
workflow. `npm run release:prepare` builds, packs and actually installs the
tarball. `npm run publish:nvcompact` only prints its local plan; adding `-- --start`
requests the registry write. Preparation does not publish or configure npm accounts.

The installed-package test uses a separate consumer directory with spaces and
Korean characters. It installs the actual tarball offline, exercises command
selection and typed notation, builds and reproduces an owned C fixture, verifies
256 integer inputs and two invalid inputs, checks fresh explicit execution
authorization, and confirms that installed package bytes remain unchanged.
It also checks the installed C++/Rust advisory utilities, explicit unsupported
language/profile boundaries, and repeated-byte inspection on owned fixtures.

The recorded 0.4.0 local run passed 41 Rust tests, five launcher tests, and all
nine installed-package validation groups. The actual installed package was
tested with Node 24.19.0; the CI workflow also defines a Node 22 job. See the
[package validation evidence](evidence/0.4/package-validation.json) for artifact
hashes, exact test scope and the distinction between local results and a future
remote CI run.

## Compile and link without compression

```sh
npm exec -- nvcompact build \
  tools/nvcompact/examples/native-build/manifest.json \
  --out /absolute/external/native-build --jobs 2

npm exec -- nvcompact reproduce \
  /absolute/external/native-build/winner.recipe.json \
  --out /absolute/external/native-replay
```

`build` compares the raw linked files. It does not apply NVCompact codecs,
section removal or script loaders. Its default mode does not execute targets or
verifiers. Add `--verify` to request the declared checks. A later native
`reproduce` needs `--verify` again to execute those checks. Manifest compiler
commands, link scripts and declared `post_link` commands still run as requested.

`run` enables the manifest's packing portfolio and requires its baseline,
candidate and final verifiers. Reproduction of a packed recipe retains that
verification requirement. All measured sizes include their loader and payload.

## Actual TCEC submission comparisons

Comparison manifests identify external upstream files by URL, release or commit,
size and hash. Original engine source, compressed source, executable files and
archives are kept outside this repository. Fetch the named original file into
your own external input directory and verify its recorded digest.

```sh
npm exec -- nvcompact envelope \
  tools/nvcompact/comparisons/general/4ku.json \
  --artifact /absolute/external/inputs/4ku \
  --output /absolute/external/4ku-search --jobs 2

npm exec -- nvcompact replay \
  /absolute/external/4ku-search/summary.json \
  --output /absolute/external/4ku-replay
```

The general `4k` category compares permitted complete script/ELF artifacts. An
inspected envelope can be described by `header_bytes` and `header_sha256`; the
header itself is read from the external file. The original complete file and
original compressed payload remain candidates. Context models, dictionaries,
match finders, codec framing and tail spelling are compared together.

The separate `4k-elf` category keeps every candidate as a native ELF. External
script interpreters and decoder wrappers are excluded. Section-header removal
requires a declared deployment contract; engines that execute header bytes are
preserved without that edit. Equality is an honest result for an already tightly
packed upstream submission. Identity selection is not a new compression gain.

An opt-in `allow_load_zero_tail` profile additionally represents trailing zero
bytes in the final writable segment using ELF zero-fill. Its limited deployment
contract, owned C/Rust example, GNU/LLD comparisons and unchanged external-engine
results are recorded in [ELF/Rust compaction](docs/ELF-RUST-COMPACTION.md).
[Further Rust size options](docs/RUST-SIZE-OPTIONS.md) separates implemented
transformations from research candidates and their observable behavior.

`envelope` reports a measured minimum and decoder reproduction. Add `--uci` for
the finite actual protocol and legal-move probes, with resource settings suitable
for that exact engine. Protocol verification, upstream source correspondence,
competition-rule review and performance on the actual TCEC server are separate
claims. A short probe does not establish tournament strength or whole-program
semantic equivalence.

## Resource-heavy engines

```sh
npm exec -- nvcompact resource plan \
  /absolute/external/ice4-resource-specification.json \
  --output /absolute/external/ice4-plan.json

npm exec -- nvcompact resource run \
  /absolute/external/ice4-plan.json \
  --start --output /absolute/external/ice4-resource-run
```

Planning reads inputs, executable fingerprints and current resource data. It
does not start an engine or allocation probe. The explicit run checks those
inputs and resources again before executing. Source memory and thread constants
are not silently reduced. An ELF virtual memory extent is recorded separately
from physical RAM requirements. Child process limits do not claim a hard cgroup
budget over an arbitrary complete process tree.

## Source alternatives and meaning

`notation` generates typed literal and trivia alternatives under an explicit
token-observation contract. `rewrite-c` additionally uses Clang's typed AST to
compare supported expression and control-flow forms. An integer-to-floating
spelling such as `100000` to `1e5` is not accepted merely because the mathematical
values match; type and context still matter.

`spell-c` exposes bounded, unranked candidates for automatic local names and
type-preserving integer/character spellings. The opt-in envelope `source_search`
compares their **complete compressed submission cost**, including an explicitly
inspected Python bytes embedding when present. Equal-length or longer source
spellings can win. Accepted changes require binding/type checks and identical
complete native output and compiler diagnostics under the declared recipe.
`replay` reconstructs the accepted derivation without repeating the search.
The caller must establish the declared source/wrapper observation contract;
masked AST and native identity do not establish traceback/location non-observation.

The submitted-codec strategy keeps the existing improving-incumbent rounds
before deferred spelling subsets. The full-codec strategy instead interleaves
singletons and subsets, checks a measured improvement immediately, and gives
initial round/family phases bounded shares before resuming their saved queues.
It does not wait for every singleton and payload style to be scored before
admission. A started candidate may finish bounded proof of its measured
improvement after the scheduling deadline; cancellation and retention/frontend
stops remain binding, and new candidates cannot start after the deadline.

Losing or tied singles remain eligible for a combined gain. `max_combinations`
defaults to 16384 per strategy, with a supported maximum of 1048576; generation,
time, measurement and retention bounds remain separate. Reports distinguish
declared generated-space completion from budget stops and unfinished work.
Condition recipes and codec refinements retain their bounded heuristic scope;
the search does not enumerate every equivalent program or rewrite sequence.
Preserving earlier priority and candidates is not a guarantee of the same
minimum under every wall-clock limit or execution environment.

When `source_search` is enabled, the envelope defaults to two source strategies:
the submitted codec first, then the complete current codec policy as an
objective. Both winners enter the final comparison, together with a distinct
legacy priority seed when deferred work changes that winner. The seed shares
its strategy's budget and crosses the same fresh final checks; it is not a new
strategy. Set the manifest's top-level
`"source_search_portfolio": false` to exclude the second strategy explicitly.
Each strategy owns its budget and attempt archive; `source_search_budget` reports
the aggregate limits and retained seed count separately. With defaults, two
strategies permit up to 4096 complete payload evaluations, 32768 combination
attempts and 600 scheduling seconds.
One evaluation may run many codecs, and in-flight work, final acceptance and the
final codec comparison are separate from those scheduling deadlines.

Both strategies and final selection share the whole-file evaluator's bounded
codec/header caches. Keys preserve payload identity and the complete recipe;
same native ELF bytes do not merge distinct source costs. Workers are reused
within a codec batch, while fresh final checks bypass measurement caches.
The default codec policy includes adaptive legacy refinements. The Rust API's
explicit fixed-recipe policy can exhaust its declared list; neither policy
claims the global compression optimum. The [search architecture](docs/SEARCH-ARCHITECTURE.ko.md)
describes ownership, reuse, exact coverage and fresh verification boundaries.

To measure repeated whole-file cost reuse on owned inert data, run from the
repository root:

```sh
cargo run --release --locked -p nvcompact --example cost_reuse
```

The [bounded example](examples/cost_reuse.rs) evaluates eight payloads 16 times
against the same fixed gzip levels 1, 6 and 9 with `jobs=1`. It compares retained
codec/header caches with disabled caches in four trials each, alternating the
execution order. JSON output records each duration, actual work and reuse
statistics, complete winning artifact hashes, and fresh evaluations of every
unique payload. Repeated, cache-policy and fresh artifact identities must agree.
Each policy runs first twice. The measurement timer includes objective setup,
header/codec work, restoration, artifact construction and identity checks; fresh
checks have a separate timer. There is no untimed warmup before measurement.
The shell header is data in this example. These measurements isolate identical
repeated work; they do not establish the overall speedup of an engine campaign
or a search that now explores more candidates. The source-search
`frontend_work` statistic likewise covers only tracked prepared analyses, not
all Clang work or the full command's running time.

Source search also retains original/candidate source snapshots, derivations and
failed or unselected observations in a bounded external attempt archive. It
automatically compares the recorded complete-file costs when sealing the run;
`compare-attempts ARCHIVE... --output NEW_JSON` compares saved runs under matching
input, tool, observation and codec contexts. It checks archive integrity without
executing saved commands or promoting size-only measurements to verified results.

The guarded Boolean-domain rule includes actual C `_Bool`/`stdbool.h` types and
aliases: `a != 1` and `1 != a` can become `!a` when the evaluated value is proven
to be 0 or 1. A name such as `typedef int bool` does not establish that domain.
Evaluation count, result type, macro boundaries and volatile/atomic protections
remain part of the rule's applicability checks.
The [whole-file source portfolio guide](docs/SOURCE-PORTFOLIO.md) documents the
contracts, configuration, bounds and unsupported cases. Engine-specific work
is tracked separately in [PR #12](https://github.com/daejunnom/Rove4k/pull/12).

### Short-coding advice

`advise-source SOURCE --language c|cpp|rust` selects an explicit source-language
contract. C++17/20 uses Clang's real C++ AST and preserves built-in scalar type
and value category. Rust's bounded primitive subset uses separate Rust typing,
checked arithmetic and rendering; it does not build a crate or expand macros.
Python and other languages return an explicit unsupported-language error. These
language restrictions apply to advisory analysis, not byte compression.

```sh
nvcompact advise-source final.cpp --language cpp --standard c++17
nvcompact advise-source final.rs --language rust --standard rust2021
```

C++ and Rust currently support static advice only; `--profile` and `--instrument`
are explicitly rejected. Shared findings/ranges and `language_details` identify
actual language semantics separately from the internal candidate generator.
See the [language contracts](docs/LANGUAGE-ADVISOR.ko.md),
[native audit and retained-engine limitations](docs/LANGUAGE-RESULTS.ko.md), and owned
[C++](examples/advice/domains.cpp) / [Rust](examples/advice/domains.rs) examples.

These commands are included in the 0.6.0 source and package. The earlier
published npm 0.5.0 tarball does not include them. See the release workflow and
registry for publication status; a local source build alone is not publication.

`nvcompact advise-c final.c --report advice.json` reports typed repeated
constants, declarations with no translation-unit references, and integer ranges
at evaluated read sites, with conditional shortening suggestions. It never feeds
findings into compression or rewrites the input. `--instrument diagnostic`
exports a separate, bounded C11 diagnostic copy; `--profile observations.log`
imports its samples as observations, without turning them into static facts.

The domain pass now combines intervals, known bits and bounded finite sets.
Pure single-variable expressions also receive typed n-version comparison:
generic arithmetic/shift/mask/Boolean alternatives are checked over every value
in the supplied containing domain. For example, the rank predicate can yield
`!(to+16&96)` when the site admits only `0..127`; a `0x88` mask guard alone does
not establish that bound. Long and long-long ranks, signedness, short-circuiting
and undefined operations remain part of the comparison.

Profile comparison uses a guaranteed expression-entry read and checks the full
observed minimum-to-maximum interval, including unsampled values. These results
remain conditional hypotheses and include separately bounded outside-domain
counterexamples. Shared DAG/typed-vector memoization avoids repeated work while
retaining algorithm-family alternatives. The [domain and n-version design](docs/DOMAIN-NVERSION.ko.md)
describes proof scopes, actual grammar, budgets, omissions and command options.

`nvcompact inspect-binary submission --word-bytes 8` inventories exact repeated
bytes in the final artifact. Matching bytes are not automatically semantic
constants or measured savings. The [advisor design and usage](docs/SHORTCODE-ADVISOR.ko.md)
explains type, side-effect, control-flow, profiling and resource boundaries.
The small owned [example](examples/advice/program.c) exercises all three source
diagnostics. Neither command starts the submitted program.
The [domain example](examples/advice/domains.c) contrasts explicit bounds, a
sparse board domain, an insufficient mask guard, and conditional observations.

The [performance and advisory follow-up](docs/PERFORMANCE-ADVICE-RESULTS.ko.md)
records the streaming verifier, indexed FIFO cache, bounded worker scheduling,
48 baseline/final measurements, complete test run and independent advisory audit.
The [domain and performance extension results](docs/DOMAIN-PERFORMANCE-RESULTS.ko.md)
record the subsequent typed-domain audit, retained TCEC comparisons, planning
algorithm improvement and rejected scratch-buffer experiments.

The [external byte-saving commit review](docs/EXTERNAL-SIZE-COMMITS.ko.md) records
upstream techniques, losses and semantic/deployment tradeoffs independently of
whether Rove4k already uses them; historical upstream sizes are not new local
measurements.
The [PR #16 measurements](docs/PR16-RESULTS.ko.md) record the ownership/search
refactor against the same pinned inputs, a separate bootstrap-byte-preserving
matrix, and the bounded cost-reuse experiment. Source-search measurements under
declared non-observation assumptions are distinguished from wrapper semantics,
UCI and submission acceptance. Its A–F input commit differs from the older
PR #13 campaign, so engine changes are not attributed to the compressor.
The [PR #13 measurements](docs/PR13-RESULTS.ko.md) compare 26 pinned
input/profile rows: seven smaller complete files and 19 byte-identical winners,
with explicit replay, compiler-proof and unexecuted runtime boundaries.
The [attempt-retention and Boolean follow-up](docs/PR13-ATTEMPTS-FOLLOWUP.ko.md)
records the new comparison command and a fresh check against those PR #13
winners: all 26 matching-condition rows remain byte-identical, with 22 fresh
engine/profile replays and four independently verified owned examples.

`npm run test:comparison` checks the read-only regression reporter. Its
`scripts/compare-results.mjs` command compares actual complete files against a
separately pinned manifest roster and the previous NVCompact winner, preserving
missing, failed and unexecuted cases rather than treating them as equivalent.

Several different source expressions can produce identical ELF bytes because
the compiler recognizes equivalent computations and optimizes them to the same
machine code. The linker then combines the compiled inputs. Identical linked
bytes are evidence about that exact toolchain and recipe, and do not imply that
linking ignores source meaning. Source length can improve while linked or packed
file length stays unchanged.

Current command syntax is available through `nvcompact --help` and each
subcommand's `--help`. The applicable working rules are in [AGENTS.md](AGENTS.md).
They preserve implementation freedom while requiring truthful size, semantics,
resource, lifetime and verification results.
