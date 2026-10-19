# NVCompact

**N-versions compaction with verified builds, packing, and reproducible results.**

NV stands for **N-Versions**: alternative source spellings, implementations,
builds, link layouts and packed files compete under explicit contracts.
NVCompact selects a small complete deployment file and records its verification
and reproduction evidence. A finite portfolio is not a proof of global minimum
size or universal semantic equivalence.

## Install this candidate

This is the local npm packaging candidate for version **0.3.0**. From a project
containing the supplied tarball:

```sh
npm install --save-dev ./nvcompact-0.3.0.tgz --ignore-scripts --no-audit --no-fund
npm exec -- nvcompact --version
npm exec -- nvcompact doctor
```

The candidate is private and has not been published by this preparation. The owner
supplied the MIT license; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

## Requirements

Linux, Node.js 22+, and CPython 3.11+. Packing uses the selected standard
compression modules; plain builds do not invoke or probe codecs. Typed C
rewrites additionally use a local Clang executable selected with `--clang`.
Compiler/linker/unpacker requirements are determined by your manifest.
`NVCOMPACT_PYTHON` can select one Python executable path. There are no runtime
npm dependencies and no automatic interpreter, compiler or package downloads.

The optional UCI oracle is a development dependency:

```sh
python3 -m pip install --target .deps chess==1.11.2
```

The installed tool does not add Node or this oracle to the produced engine.

## Commands

| Command | Backend and purpose |
|---|---|
| `nvcompact --help` / `--version` | CLI usage and package version |
| `nvcompact doctor` | Check the local Python runtime and required compression APIs |
| `nvcompact build ...` | Compile/link without NVCompact compression; execution checks require `--verify` |
| `nvcompact run ...` | Native implementation/compiler/linker/packing portfolio |
| `nvcompact reproduce ...` | Reproduce a recipe; native recipes execute checkers only with a new `--verify` |
| `nvcompact notation ...` | Generate safe literal/token spelling candidates |
| `nvcompact rewrite-c ...` | Generate typed C structural alternatives and optionally a run manifest |
| `nvcompact envelope ...` | Repack a reviewed source or native self-extracting envelope |
| `nvcompact replay ...` | Reproduce an envelope selection and optionally run UCI |
| `nvcompact uci ...` | Execute and inspect the actual final engine file |
| `nvcompact engines --manifests ...` | Run an explicit, nonempty local manifest collection |
| `nvcompact resource plan ...` / `resource run ... --start` | Read-only resource planning followed by separately requested UCI execution |

Run a command with `--help` for its arguments. Paths are resolved using the
caller's working directory or the manifest's own documented base. Output paths
must satisfy the backend's new-output policy.

## Source notation

```sh
npm exec -- nvcompact notation engine.cpp \
  --language cpp --target cpp17-lp64 \
  --token-contract no-token-observation --compact \
  --portfolio runs/spellings-01
```

The default opaque token contract preserves the source. Explicitly declaring
`no-token-observation` permits supported transformations; it does not authorize
changing integer types, macro meaning or observable source behavior.

## Plain build and native reproduction

```sh
npm exec -- nvcompact build \
  node_modules/nvcompact/examples/native-build/manifest.json \
  --out runs/native-01 --jobs 2

npm exec -- nvcompact reproduce runs/native-01/winner.recipe.json \
  --out runs/native-replayed-01
```

These commands build and reproduce native bytes without executing the produced
program. They skip NVCompact source notation, ELF surgery, codecs and wrappers.
Manifest compile/link/post-link commands run as declared. Add `--verify` to
each invocation that should execute its checker, even when replaying an
originally verified native recipe. Compressed `run` recipes retain their
existing execution-check behavior on reproduction.

The default plain result is `built` with verification `not_run`; explicit
successful checks produce `accepted`. Native reproduction reports
`byte_identical` independently from its execution-check result.

## Typed C structural shortening

```sh
npm exec -- nvcompact rewrite-c engine.c --clang clang --standard c11 \
  --token-contract no-token-observation --portfolio runs/c-variants-01
```

Supported rules use Clang's types and syntax, protect incompatible macro/scope
and evaluation contexts, and reparse resulting candidates. The original remains
available. Conditional expressions, short-circuit guards and compound updates
are only applied when their implemented preconditions hold. `--run-manifest`
with an application verifier, explicit target and contract connects these
alternatives to the native/packing portfolio; source length alone does not
choose the final executable.

For complete examples and the rule comparison, see the repository's
[C rewrite guide](https://github.com/daejunnom/NVCompact/blob/main/docs/C-REWRITES.md).

## Complete native example

This package includes the C/Rust kernels, oracle and linker scripts. With `cc`,
`ld`, `rustc` and `python3` installed:

```sh
npm exec -- nvcompact run \
  node_modules/nvcompact/examples/mixed/manifest-notation.json \
  --out runs/mixed-01 --jobs 2
```

Follow the produced recipe with `nvcompact reproduce --help`. The example is an
integer kernel, not a chess engine strength benchmark.

## Envelopes and UCI

```sh
npm exec -- nvcompact envelope ./engines/example.json \
  --output runs/engine-01 --uci --oracle-path .deps

npm exec -- nvcompact replay runs/engine-01/summary.json \
  --output runs/engine-01-replay --selection accepted \
  --uci --oracle-path .deps
```

`./engines/example.json` is your reviewed manifest and must refer to actual
local input bytes and the required source/provenance files. The 11 historical
TCEC inputs are in the separate monorepo lab, not bundled into this npm package.

`smallest` is a measured size result. `accepted` also passes the requested
execution checks. Reproducing bytes alone does not certify TCEC admission,
many-core scalability or engine strength.

## Memory-heavy execution is opt-in

```sh
npm exec -- nvcompact resource plan ./resource-spec.json \
  --output runs/resource-plan.json

npm exec -- nvcompact resource run runs/resource-plan.json \
  --start --output runs/resource-execution-01
```

Use an actual reviewed resource specification. Planning fingerprints files and
reads the host's current resource information; it starts neither the engine nor
compiler version probes. Running requires `--start`, an unchanged plan and
adequate observed resources. The lab's original profiles preserve engine UCI
options and are supplied separately from this generic npm package. Memory
estimates are not reservations; per-process limits are not a process-tree cap.
See the repository's
[resource guide](https://github.com/daejunnom/NVCompact/blob/main/docs/RESOURCE-TESTING.md).

## Cancellation and reproducibility

The launch adapter handles SIGINT and SIGTERM, stops the subprocess groups it
created, lets known nested Python helpers clean their own groups, cancels queued
worker tasks, and waits for running workers to finish. Cancellation exits with
130 or 143. Cleanup failures are reported as incomplete; they are not labeled
successful cleanup.

The ownership boundary is the original groups and bundled helpers. Arbitrary
external helpers that daemonize or create independent sessions must manage those
lifetimes themselves. SIGKILL and host failure cannot provide normal cleanup.
A running native compression call may finish before cancellation can complete.

Core recipe fingerprints cover the modules actually used by the selected path.
Keep the installed npm version/tarball hash and a launch diagnostic with a run:

```sh
npm exec -- nvcompact doctor --json > nvcompact-runtime.json
```

The diagnostic contains the core version and launch adapter SHA256. It checks
the local runtime; it does not install compilers or prove engine eligibility.
This release provides a CLI interface; JavaScript library internals are not a
stable in-process compression API.

The backend remains Python. The repository's
[Rust migration direction](https://github.com/daejunnom/NVCompact/blob/main/docs/RUST-ROADMAP.md)
records how a future replacement should preserve behavior, reproducibility and
resource ownership before claiming a performance improvement.
