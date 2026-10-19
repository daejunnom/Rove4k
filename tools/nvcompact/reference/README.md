# Historical comparison implementation

`v0.3/` is a filtered snapshot of NVCompact commit
`4f238d1e56faca3a8c926098c6d5be2c98728cb8`. External engine inputs and source
archives were deliberately excluded. It is preserved so the Python compression
algorithm, past failures, recipes, tests and design decisions remain reviewable
after the standalone repository is removed.

The migration record identifies every excluded asset. Thirty embedded upstream
shell headers in twelve historical JSON metadata files were also replaced by
their byte length and SHA-256. They can be recovered from the separately obtained,
hash-checked external artifacts; no upstream shell source is bundled here.
These metadata redactions are recorded with before/after file hashes. Historical
Python reproduction needs a separately hydrated metadata copy because that old
implementation expects literal headers.

These files are historical references, not the active CLI, CI, packaging or
engineering policy. Paths into the excluded old `inputs/` and `vendor/` trees
are historical references and must be materialized outside the repository when
reproducing an old experiment. `AGENTS.archived.md` is not an active instruction
file. Current source is in `../src/`; current rules are `../AGENTS.md`.

Original Markdown links were not rewritten as though the old experiments ran
in the new layout. In particular, historical links to `AGENTS.md` refer to
[the archived contract](v0.3/AGENTS.archived.md); some old research links to
build logs, environment records and excluded inputs no longer resolve from
their preserved locations. Use the recorded original commit and migration
manifest to identify those references, not an automatic new success claim.

The Rust implementation does not launch these Python modules as a backend.
Explicit Python reference comparisons and independent example oracles are
development tests, separately identified in the current evidence.
