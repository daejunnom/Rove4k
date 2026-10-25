# Rust D fixed castling bounded-index native cost

This owns the exact seven ordinary maintained ASCII Rust D inputs and one fixed
three-index mask transform. The candidate board is 14,346 bytes, SHA-256
3f73e15f0d59ab90b54899a3c322b78cd4d33b9a0d844d348149f8e4c9715c71;
readable Rust grows by18 bytes. Each original index in the fixed castling tuples
is already0..119, so the mask is identity without a side±1 assumption. No unsafe,
new coordinate wrap, Board/layout, parser, search, runtime or feature change.

`cost.py --out /absolute/new/external/path` freezes this ordinary closure before
one candidate scalar and one candidate HQ link with the unchanged fixed compiler,
flags/linker and workers2/TT18 profile. Existing exact control native files are
read and reused; no control, extra unstripped or repeat link is performed.
The helper parses ELF metadata and records static readelf/objdump outputs. It
never runs a generated ELF and has no packing phase. Whole size remains unmeasured.
Generated source/native/dumps/logs/receipts belong outside Git. Failed tool events
and cleanup state remain in the external incomplete receipt. No automatic retry.

The external source-only proposal and raw diff are preserved at
`C:/Users/강민수/Documents/Codex/rove4k-rust-d-bounded-index-proposal-20261021/`.
Its original scalar checks plus dedicated tails occupy66 existing bytes; this is
not a predicted saving. Actual full native, sections and any later whole cost
must remain separate. Packaging or runtime needs a later explicit root decision.
