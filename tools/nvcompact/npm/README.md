# nvcompact

**N-version compaction:** compare native implementations, source representations
and compression portfolios, then retain the smallest complete artifact that
satisfies the selected contract. The Rust implementation is maintained inside
[Rove4k](https://github.com/daejunnom/Rove4k/tree/main/tools/nvcompact).
The npm package and executable are both named `nvcompact`.

Version 0.5.0 adds bounded complete-file source search, retained source-search
attempts and the read-only `compare-attempts` command. Typed C Boolean rewrites
require a proved 0-or-1 value domain. The [0.5.0 release notes](https://github.com/daejunnom/Rove4k/blob/main/tools/nvcompact/docs/RELEASE-0.5.ko.md)
describe the source contracts, measured results and supported platforms.

## Install and use

```sh
npm install --global nvcompact
nvcompact --version
nvcompact doctor --json
nvcompact --help
```

The published native target is **Linux x64 with glibc**. Release CI uses Ubuntu
24.04; glibc 2.39 or newer, zlib and the GCC runtime must be available. Node 22
or newer launches the bundled Rust executable. Windows, macOS, ARM and musl
packages are not currently provided. C/C++ builds require their declared
compiler, typed C rewrites require Clang, and decoder/interpreter requirements
belong to each explicitly selected deployment or verifier.

## Build a package from source

From Rove4k with a Linux x64 Rust toolchain and native codec development libraries:

```sh
npm ci --ignore-scripts
npm run build:nvcompact
npm run pack:nvcompact -- --no-build
npm run verify:package
```

The pack command reports the complete tarball path. It stages the Rust binary,
Node launcher, license and metadata outside the repository. The binary and all
build outputs stay outside the repository. The package contains no external
chess engine files or archived Python implementation.

Install that tarball into another project:

```sh
npm install --offline --ignore-scripts /absolute/path/nvcompact-0.5.0.tgz
npm exec -- nvcompact --version
npm exec -- nvcompact doctor --json
```

The native binary is specific to its target and runtime ABI; an npm tarball is
not a TCEC submission. Other targets require an explicit build and packaging contract.

## Executable selection

`NVCOMPACT_BIN=/absolute/path/to/nvcompact` selects an explicit Rust build.
Otherwise, an installed package uses its bundled native executable. The source
workspace uses the external build metadata written by `npm run build:nvcompact`.
The launcher preserves argument boundaries, working directory, stdio and exit
status, and forwards cancellation to the owned Rust child.

The active builder runs in Rust. A submitted general 4k loader or a user-declared
verifier can explicitly require an interpreter; those are separate deployment
and verification dependencies. ELF-only submission candidates do not use script
loaders. `nvcompact --help` lists the current command surface.

`spell-c` generates local-binding and typed literal alternatives. An inspected
submission manifest can opt into `source_search` to compare their complete
compressed file cost, preserving the previous portfolio and requiring native
and compiler-diagnostic identity. `replay` reconstructs the selected derivation
without repeating its search. See the [source portfolio guide](https://github.com/daejunnom/Rove4k/blob/main/tools/nvcompact/docs/SOURCE-PORTFOLIO.md)
for the explicit C/Python observation contracts and bounded search settings.

Source builds from the follow-up development PR also provide `advise-c` for
typed constants, unused declarations and integer ranges at individual reads,
plus `inspect-binary` for exact repeated-byte inventories. Advice does not enter
the compressor or edit inputs. Optional `advise-c --instrument` exports a
separate diagnostic copy without starting it; `--profile` attaches finite
observations without promoting them to static facts. These additions are not a
claim that the already-published 0.5.0 tarball includes the new commands.
See the [advisor guide](https://github.com/daejunnom/Rove4k/blob/feature/nvcompact-search-architecture/tools/nvcompact/docs/SHORTCODE-ADVISOR.ko.md).

See the [maintainer publishing guide](https://github.com/daejunnom/Rove4k/blob/main/tools/nvcompact/docs/PUBLISHING.md)
for the personal-account bootstrap, OIDC configuration and release workflow.
