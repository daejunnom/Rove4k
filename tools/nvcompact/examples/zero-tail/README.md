# Initialized-data / ELF zero-tail example

This is an owned C/Rust comparison fixture, not a chess engine or vendored TCEC
submission. Run commands from the repository root with Rust, GNU cc/ld and Node
available. Keep all output directories outside the checkout.

```sh
npm exec -- nvcompact run tools/nvcompact/examples/zero-tail/manifest.json \
  --out /absolute/external/zero-tail --jobs 2
npm exec -- nvcompact reproduce /absolute/external/zero-tail/winner.recipe.json \
  --out /absolute/external/zero-tail-replay --verify
```

The profile compares C and Rust kernels, `-Oz`/`-Os`/`-O2`/`-O3` against Rust
`z`/`s`/`2`/`3`, and Rust `off`/`thin`/`fat` LTO. These are explicit candidates,
not a recommendation that one setting always produces the smallest program.
C uses the declared optimization level without cross-language LTO. Rust emits
one native object, so this fixture does not claim a multi-crate LTO benchmark.
The single-codegen-unit setting is deliberate for a single output object.

The kernel holds 8192 writable bytes initialized with byte 17 followed by zeros.
Each 8-byte little-endian request is `(u32 index, u32 value)`. For index 0..8191,
it returns the previous byte as a 4-byte little-endian integer, then stores the
low eight bits of `value`. State persists within one process. EOF is clean only
between records; a partial or out-of-range record exits with code 2. There is no
concurrency, dynamic loader, TLS, heap, constructor, unwinding or signal API.
The driver handles partial reads/writes and EINTR. The independent Node oracle
checks all bytes, memory page boundaries, persistent writes, narrowing, EOF and
rejected inputs; it does not derive expected outputs from ELF metadata.

The link script places RX and RW mappings on separate virtual pages while using
matching file/virtual page residues. The declaration `allow_load_zero_tail: true`
also requires `allow_section_header_removal: true`. It permits omitting only a
zero suffix of the final RW, non-executable segment while retaining its virtual
address, memory size and permissions. The original and ordinary sectionless
files remain candidates. The process and deployment must not observe its own
file, ELF headers, program-header values through `AT_PHDR`, or other changed
metadata. File mappings, path-sensitive behavior and introspection therefore
need their own contract and cannot silently use this profile.

The emitted file needs actual execution verification. This fixture supports
Linux x86-64 with 4096-byte pages. Unknown segments, overlapping virtual pages,
truncated extents, an interpreter, dynamic linking, TLS and metadata reused as
code are rejected by this profile. It is not a universal ELF transformer.

For an ELF-only submission comparison, copy this own manifest outside the
checkout, set `project_root` to the absolute tool directory, set `category` to
`4k-elf`, and restrict `codecs` to `["raw"]`. General packaging keeps the declared
wrappers and counts their decoder header as part of the final file. This example
has no UCI protocol and must not be presented as a TCEC engine.
