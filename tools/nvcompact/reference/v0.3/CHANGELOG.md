# Changelog

## 0.3.0 — 2026-10-19

- Add `build` for manifest-driven native compile/link portfolios without
  NVCompact notation, ELF changes, codecs or wrappers. Default builds and
  native recipe replays compare bytes without executing the resulting program.
  Each execution check requires an explicit `--verify`.
- Add `resource plan` and `resource run --start`. Plans fingerprint reviewed
  inputs and read available resources. Runs recheck those assumptions, preserve
  original UCI options when requested, apply finite child limits and retain
  owned cleanup. Four high-memory original-engine profiles are plan-only in
  this release's validation.
- Add `rewrite-c` with typed Clang AST checks, per-rule and combined shorter C
  candidates, and an original-preserving manifest export for application
  verification and actual native/complete-file size comparison.
- Update the Node/Python CLI boundary so ordinary commands do not run the
  diagnostic codec probes. `doctor` explicitly exercises those APIs.
- Validate the local npm installation across the native and packed paths.
  Load the public `node:test` API directly to support both Node 22 and Node 24
  without the unsupported Node 22 `--test-isolation=none` flag.
- Record the future Rust backend direction: bounded parallel work, explicit
  subprocess ownership, compatible contracts and measured migration decisions.

This is a locally installable, private npm candidate. Registry publication and
actual high-memory engine execution have not been performed by this release.
See `evidence/` for the scope, runtime and source hashes of actual checks.

Native recipes retain strict generating-runtime fingerprints. Historical 0.2
recipes use their recorded 0.2 runtime; this update does not silently migrate
them to different core hashes.

The owner selected the `Rove4k` and `NVCompact` GitHub repositories and supplied
their MIT licenses. Earlier naming and private licensing proposals remain
historical records, superseded by those repository decisions.

## 0.2.0 npm packaging preparation

This section preserves the preparation-stage record. Its naming proposal and
remote-repository status describe that stage, before the owner's repository choice.

- Define the name NVCompact as N-Versions + Compact.
- Create a native npm workspaces monorepo with a CLI candidate and a private
  TCEC 4K experiment workspace.
- Preserve the eight Python core modules and the original mixed examples and
  linker profiles byte-for-byte.
- Add a Node command entry, runtime diagnostics, an explicit Python selector,
  and a Python launch boundary for controlled cancellation.
- Validate actual npm tarball contents and installation in a separate consumer
  directory, including meaningful backend execution and reproduction.
- Keep the 0.2 engine campaign as historical evidence and retain source/archive
  license provenance in the private lab.
- Propose Rook4k for the future engine repository, with Rove4k as the lineage
  alternative. No engine implementation, registry publication or remote
  repository creation is part of this packaging change.
