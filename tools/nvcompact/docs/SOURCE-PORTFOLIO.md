# Whole-file C source portfolios

This change develops NVCompact's source transformations on a separate feature
branch based on develop `56bfb5f45bff59a570d3f04f8eba06332d53c052`. Engine PR #12
remains independent. Its comparison input is pinned to
`0e716e0b366272c66749f6e7194f64cb715e2d00`; a later engine update is a different input.

## Scope and acceptance

The objective is the complete submitted file, including its loader and compressed
payload. Source length is an observation, not a pruning rule. Equal-length local
name assignments and longer, type-preserving literal spellings can be useful.
The original file, original compressed stream and previous candidate portfolio
remain available. New candidates must not displace a smaller previous result.

The implementation adds bounded, deterministic candidates for automatic local
bindings, typed integer and narrow character literals, and proven C condition
forms. A declaration's binding, C type and value, evaluation count, side effects,
and ownership remain part of the contract. Engine-specific board invariants,
search policies, TT layouts and memory orders are not inferred from examples.

An opt-in source search will compare the actual envelope cost, then validate
binding/type structure and complete native bytes under the declared compiler
recipe. Embedded C requires an explicitly inspected Python bytes-literal span;
the rest of the bootstrap must retain its typed AST and exact surrounding bytes.
Replay applies the selected derivation and rechecks it without rerunning a search.
These are source/byte-equivalence checks, not a claim of new UCI or tournament
qualification. Heavy engine execution retains its separate plan/start boundary.

## Work in progress

- Implement and review the Rust source candidate, embedding and selection paths.
- Check condition operators against independent value/effect counterexamples.
- Rebuild and compare owned examples, pinned A–F inputs, and all available
  external General/ELF comparison manifests with the previous implementation.
- Preserve failures, unavailable runtime/resource checks and untested targets.
- Keep external engine source, generated engines and raw campaign output outside
  Git and npm. Publish reviewed metadata and commands only.

The separate [PR #12 handoff](PR12-HANDOFF.ko.md) distinguishes engine changes
from common compression work. Final measurements and current CLI details will
replace this work-in-progress section before the PR is ready for review.
