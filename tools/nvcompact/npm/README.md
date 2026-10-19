# @rove4k/nvcompact

Private npm entry point for the Rust NVCompact tool in
[Rove4k](https://github.com/daejunnom/Rove4k/tree/main/tools/nvcompact).
The executable command is `nvcompact`. No npm registry publication is configured.

## Prepare a usable local package

From the Rove4k repository, with Node 22 or later and a Linux Rust toolchain:

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
npm install --offline --ignore-scripts /absolute/path/rove4k-nvcompact-0.4.0.tgz
npm exec -- nvcompact --version
npm exec -- nvcompact doctor --json
```

This is a package for the Linux architecture and runtime ABI on which it was
built. Rebuild locally for another environment. C/C++ compilers, Clang for typed
C rewrites, and declared deployment decoders remain explicit external tools.

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
