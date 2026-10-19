# Rove4k

A UCI chess engine project targeting TCEC 4K.

Rove4k is an early engine project in the RoveZero/Rovent family. The engine
implementation is being designed. This monorepo contains the engine's common
engineering contracts and **[NVCompact](tools/nvcompact/README.md)**, its internal
Rust tool for native linking, compression portfolios and submission verification.

NVCompact means **N-version compaction**: compare independently declared
implementations and representation/packing variants, then retain the smallest
complete artifact that meets the selected contract. It is a development tool;
its own executable and development dependencies are not the 4 KiB engine entry.

## Internal tool

The Cargo workspace member is `tools/nvcompact`; its npm package and executable
are named `nvcompact`. The operational backend is Rust. The previous Python
implementation is a filtered historical reference, never an implicit backend.

The [npm publishing guide](tools/nvcompact/docs/PUBLISHING.md) separates local
package preparation, the personal-account first upload and GitHub OIDC releases.

```sh
# Choose an output directory outside the checkout.
CARGO_TARGET_DIR=/tmp/rove4k-target cargo build --locked --release -p nvcompact
/tmp/rove4k-target/release/nvcompact --help

# A plain compile/link build; compression and target execution are opt-in.
/tmp/rove4k-target/release/nvcompact build \
  tools/nvcompact/examples/native-build/manifest.json \
  --out /tmp/rove4k-native-build
```

See the [tool guide](tools/nvcompact/README.md),
[Rust migration](tools/nvcompact/docs/MIGRATION-0.4.ko.md),
[external TCEC examples](tools/nvcompact/docs/TCEC-EXAMPLES.md) and
[measured comparison](tools/nvcompact/docs/TCEC-RESULTS-0.4.ko.md).
External engine source, compressed source and engine executables are not vendored.
The comparison manifests contain provenance and hashes; input files and campaign
outputs live outside the checkout. General 4K scripts and self-contained 4K ELF
entries are separate categories.

## Development

Start with [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md) and the
[engineering contract](docs/ENGINEERING-CONTRACT.md). Algorithms, implementation
languages and parallel search designs remain implementation decisions.
The target's many-core performance and total resource use are part of those
decisions.

Internal tool work also follows its separate
[NVCompact contract](tools/nvcompact/AGENTS.md). The engine's runtime size and
per-node costs do not forbid parsers, diagnostics or appropriate dependencies in
the development tool. Neither contract fixes an engine architecture or a
compression algorithm.

Earlier detailed designs remain in the separately delivered external handoff.
They are reference material, not mandatory engine architecture.

## License

MIT; see [LICENSE](LICENSE).
