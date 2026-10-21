# NVCompact

NVCompact means **N-version compaction**: preserve the original, construct
explicit alternatives, verify their applicable contracts, and compare the
complete deliverable. It is an internal Rust tool in the Rove4k monorepo.

The current version is 0.4.1. Node supplies the `nvcompact` npm command boundary;
Rust performs the active compilation orchestration, spelling transformations,
packing, reproduction, resource checks and UCI probes. The archived Python 0.3
implementation is reference material for past results.

## Build and package

The current execution environment is Linux. Use Node 22 or later, Rust/Cargo,
and the build dependencies for liblzma, zlib and libbz2. C/C++ comparison builds
need their declared compiler; typed C transformations also need Clang.

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
`npm install --offline --ignore-scripts /absolute/path/nvcompact-0.4.1.tgz`.
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
The [whole-file source portfolio guide](docs/SOURCE-PORTFOLIO.md) documents the
contracts, configuration, bounds and unsupported cases. Engine-specific work
is separated in the [PR #12 handoff](docs/PR12-HANDOFF.ko.md).

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
