# Preserved engine work

This directory holds retired Rove4k engine implementations and inactive
experiments. Their source, receipts, rejected candidates and incomplete results
are preserved byte for byte. Moving them does not change a past failure into a
success or qualify a past measurement for the current engine.

The active implementation is C A–F. NVCompact is an active Rust tool under
`tools/nvcompact`; it is outside this engine retirement. Generic Rust lexical,
model-representation and ELF-loader fixtures also remain active where they test
shared tooling rather than a retired Rove4k engine.

| Preserved path | Responsibility |
| --- | --- |
| `engines/rust`, `engines/tests/rust` | Retired reference Rust engines and their engine tests |
| `engines/compact/rust`, `tiny-rust`, `tiny-rust-d`, `tiny-rust-d-shipping` | Retired Rust structural, compact and shipping producers |
| `engines/experiments` | Inactive source, packaging, search and representation experiments, including failed attempts |
| `engines/tests/compare_parallel.py`, `target_search.py`, `engines/model/compare_c.py` | Historical comparison harnesses that require retired C/Rust portfolio combinations |

[The snapshot manifest](engines/snapshot.json) lists original repository roots.
Each listed root is preserved here under the same path prefixed by `archive/`.
Its source revision is
`b5e3987c925cc82fcd210c2205262d92692bf961`, the PR #12 source tree before this
layout change. The archive contains tracked source and evidence, not a generated
build/cache directory.

## Inspect here; replay at the original paths

Historical producers use repository-relative imports, companion source files
and literal source hashes. Their contents have deliberately not been rewritten
for the archive location. Running a moved producer directly under `archive/`
would give it the wrong repository root or mix old and current dependencies.

Export the complete declared source revision to a new directory outside every
Git checkout:

```sh
python3 -B archive/replay.py --out /var/tmp/rove4k-preserved-b5e3987
```

The exporter reads local Git objects and restores original paths, exact blob
bytes and executable modes. It ignores today's worktree and Git export
attributes, writes an `archive-replay.json` receipt and executes no engine or
build. An existing destination is rejected so previous evidence cannot be
overwritten. The source commit must be available in local history; a shallow
checkout without it gets an explicit failure, with no automatic network fetch.

The exported tree provides the **pre-move source state**, not a promise that
every historical campaign can be rerun successfully. Some receipts name an
earlier source snapshot, a different toolchain or an unmet runtime condition;
those requirements remain authoritative. Preserve and inspect any rejection.
Use the recipe's original commands and separate output paths only after checking
its inputs and resource requirements. The Rust retirement remains the current
production policy even though the source is available for inspection.

To reconsider an experiment for today's engines, port its transformation to the
current canonical input owner and compare full generated source, native output
and final file under the current validation contract. Historical hashes and
byte savings must not be copied into a new acceptance record.

The maintained production, evaluation, E19 and CI dependencies remain under
[`engines/`](../engines/README.md). The smaller live experiment set and its
dependencies are listed in
[`engines/experiments/README.md`](../engines/experiments/README.md).
