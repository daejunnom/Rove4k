# nvcompact

**N-version compaction:** compare native implementations, source representations
and compression portfolios, then retain the smallest complete artifact that
satisfies the selected contract. The Rust implementation is maintained inside
[Rove4k](https://github.com/daejunnom/Rove4k/tree/main/tools/nvcompact).
The npm package and executable are both named `nvcompact`.

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
npm install --offline --ignore-scripts /absolute/path/nvcompact-0.4.1.tgz
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

See the [maintainer publishing guide](https://github.com/daejunnom/Rove4k/blob/main/tools/nvcompact/docs/PUBLISHING.md)
for the personal-account bootstrap, OIDC configuration and release workflow.
