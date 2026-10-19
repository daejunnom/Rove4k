# NVCompact

**N-versions compaction with verified builds, packing, and reproducible results.**

NV means **N-Versions**. NVCompact compares source spellings, interchangeable
implementations, compiler/linker combinations and packed deployment files. It
records the smallest measured file separately from a candidate that passes its
declared execution checks. Results are limited to the searched portfolio and
the stated equivalence contract.

NVCompact **0.3.0** adds plain compile/link builds, explicitly started resource
tests, and typed C rewrite portfolios. A Node CLI launches the current Python
implementation. The historical 11-engine campaign remains previous evidence;
this release does not relabel it as a newly repeated campaign.

See the [Korean 0.3 work record](docs/RELEASE-0.3.ko.md),
[changelog](CHANGELOG.md), [native build guide](docs/NATIVE-BUILD.md),
[C rewrite guide](docs/C-REWRITES.md), [resource testing](docs/RESOURCE-TESTING.md)
and [Rust migration direction](docs/RUST-ROADMAP.md).

## Workspace map

| Path | Role |
|---|---|
| `packages/nvcompact` | Locally installable npm CLI candidate, Python core, original small examples, linkers and profiles |
| `packages/tcec4k-lab` | Private experiment workspace with 11 pinned engine inputs, manifests, corresponding sources and licenses |
| `scripts` and `tests` | Package preparation, installation and behavior checks |
| `docs` | Tool contracts, naming proposal and packaging decisions |
| `evidence` | Migration, prior campaign and new package-validation records |

Detailed design history remains in the sibling `nvcompact-monorepo-handoff`
directory. Workspace boundaries are current design choices, not permanent
constraints on future algorithms, languages or package structure.

## Runtime

- Linux; Node.js 22 or later; CPython 3.11 or later.
- Packing requires the selected standard compression APIs; `doctor` checks
  `lzma`, `bz2` and `gzip`. Plain `build` does not probe or invoke codecs.
- No runtime npm dependencies and no install-time downloads or compilation.
- Compiler, linker and unpacker requirements depend on the selected manifest.
- Typed C rewrites require a local Clang frontend. `rewrite-c --clang PATH`
  selects it; the optional frontend is not bundled or downloaded by npm.
- Optional UCI legality oracle: `chess==1.11.2`, installed in the development
  environment. It is not included in a chess engine or its 4096-byte budget.

`NVCOMPACT_PYTHON` is one executable name or path, including paths with spaces.
It is not a shell command string. The CLI preserves the caller's working
directory and passes arguments without a shell.

## Develop and pack

```sh
npm ci --ignore-scripts --offline --no-audit --no-fund
npm exec -- nvcompact --help
npm exec -- nvcompact doctor
npm test
npm run check
npm run pack:cli
npm run verify:package
```

The CLI tarball is written to `dist/nvcompact-0.3.0.tgz`. `dist/pack.json` records
its actual entries, size and hash. The integration verifier installs that
tarball into a separate temporary consumer project using the offline npm path.

Run all lifecycle checks and the Python tests with the optional UCI
oracle. Without this development dependency, `npm test` reports three UCI
cancellation checks as skipped:

```sh
python3 -m pip install --target .deps chess==1.11.2
NVUCI_ORACLE_PATH="$PWD/.deps" npm test
NVUCI_ORACLE_PATH="$PWD/.deps" NVCOMPACT_CLANG=clang npm run test:core
```

The tests use small programs. Neither these commands nor package installation
starts the original high-memory engines. CI checks the package on Node 22 and 24.

## Install the local package in a consumer project

Copy the supplied tarball into your project, then run:

```sh
npm install --save-dev ./nvcompact-0.3.0.tgz --ignore-scripts --no-audit --no-fund
npm exec -- nvcompact --version
npm exec -- nvcompact doctor
npm exec -- nvcompact notation engine.cpp \
  --language cpp --target cpp17-lp64 \
  --token-contract no-token-observation --compact \
  --portfolio runs/spellings-01
```

The package README documents each command. The npm name has not been published
by this work; registry-only installation is not a demonstrated command yet.

## Plain compile/link builds

From the monorepo root:

```sh
npm exec -- nvcompact build packages/nvcompact/examples/native-build/manifest.json \
  --out runs/native-01 --jobs 2

npm exec -- nvcompact reproduce runs/native-01/winner.recipe.json \
  --out runs/native-replay-01
```

These commands compile/link and compare fresh build bytes. They do not execute
the produced program, transform ELF metadata or call NVCompact compression.
Declared build commands, compiler flags and linker scripts still run as written.
Add `--verify` to a particular `build` or native `reproduce` invocation to start
the manifest's execution checker. See [the native contract](docs/NATIVE-BUILD.md).

## Typed C rewrite portfolios

```sh
npm exec -- nvcompact rewrite-c engine.c --clang clang --standard c11 \
  --token-contract no-token-observation --portfolio runs/c-variants-01
```

The default token contract preserves the input. An explicit compatible contract
enables supported AST-based transformations: conditional returns/assignments,
short-circuit guards, boolean forms, compound updates and other shorter C forms.
Rules check their type, scope and evaluation conditions and reparse each result.
They do not change engine search algorithms or establish universal equivalence.

`--run-manifest` can generate a runnable native portfolio with an explicit
application verifier, target and contract. The original source remains a
candidate. Compare actual native and complete packed bytes instead of assuming
that the shortest source is the smallest executable. A complete command and
the broader rule comparison are in [C-REWRITES.md](docs/C-REWRITES.md).

## Native implementation and link portfolio

The installed package contains the complete C/Rust mixed example and its linker
scripts. With the compiler toolchain installed, run from your consumer project:

```sh
npm exec -- nvcompact run \
  node_modules/nvcompact/examples/mixed/manifest-notation.json \
  --out runs/mixed-01 --jobs 2
```

This is a small integer-kernel example. The Rove4k chess engine is a
separate project and a proposed consumer of NVCompact.

## TCEC experiment workspace

From the monorepo root, choose a new output directory:

```sh
npm exec -- nvcompact envelope packages/tcec4k-lab/engines/sunfish.json \
  --output runs/sunfish-01 --jobs 2 --uci --oracle-path .deps \
  --uci-config packages/nvcompact/profiles/protocol-15s.json

npm exec -- nvcompact replay runs/sunfish-01/summary.json \
  --output runs/sunfish-01-replay --selection accepted \
  --uci --oracle-path .deps \
  --uci-config packages/nvcompact/profiles/protocol-15s.json

npm exec -- nvcompact engines --manifests packages/tcec4k-lab/engines \
  --only sunfish --output runs/campaign-01 --jobs 2 \
  --oracle-path .deps \
  --uci-config packages/nvcompact/profiles/protocol-15s.json
```

`--jobs` controls compressor workers, not engine search threads. Resource-blocked
manifests retain their prior diagnostics; their TT and thread settings have not
been reduced. The generic npm package does not silently download these inputs.

### Plan high-memory testing separately

```sh
npm exec -- nvcompact resource plan \
  packages/tcec4k-lab/resource-profiles/ice4-v6.1-original.json \
  --output runs/ice4-resource-plan.json
```

Planning reads input fingerprints and current resource information without
starting the engine, allocating its TT or running compiler version probes.
Actual execution is a separate, explicitly started command:

```sh
npm exec -- nvcompact resource run runs/ice4-resource-plan.json \
  --start --output runs/ice4-resource-execution-01
```

The run rechecks the plan and resource availability before starting. Original
profiles preserve engine options, including Hash and Threads. Their successful
planning is not a UCI pass. Per-process limits and current memory observations
are not a reservation or a hard cap for an entire process tree; see
[RESOURCE-TESTING.md](docs/RESOURCE-TESTING.md).

## Implementation direction

Python remains the backend in this version. A future Rust migration should
preserve recipes, observable behavior, explicit execution and owned subprocess
cleanup, then use measured bottlenecks to guide bounded parallel work. The
[roadmap](docs/RUST-ROADMAP.md) records the migration boundaries without freezing
engine algorithms, thread counts or a permanent crate layout.

## Repositories, license and release status

The engine repository is [Rove4k](https://github.com/daejunnom/Rove4k).
The owner supplied the MIT license for this NVCompact repository; its own
package metadata and distributed license follow that choice. External lab
engines retain their original licenses and sources.

The CLI is a private, locally installable npm candidate. Registry publication
is a separate action. The historical naming and packaging reports describe
the earlier preparation stage.

See [release preparation](docs/RELEASING.md),
[packaging decisions](docs/PACKAGING-DECISIONS.ko.md),
[license status](LICENSE-STATUS.md), and [AGENTS.md](AGENTS.md).
