# Self-restoring Linux ELF

`../elf_loader.py` packs a Linux x86-64 ELF into another ELF containing a small
static native loader and a compressed copy of the entire input. The original
ELF is not stripped or rewritten. The handwritten codec stores literal runs and
backreferences; it does not incorporate an external decoder implementation.

The loader uses Linux syscalls to allocate a decode buffer, restore the input to
an anonymous `memfd`, and replace itself with that ELF using `execveat`. It does
not invoke a shell, compiler, unpacker or other runtime tool, and creates no
filesystem pathname. The restored program uses its own declared interpreter and
libraries. A kernel allowing executable `memfd` and `execveat` is required;
unsupported or denied operations terminate with exit code 126 and a diagnostic.
The loader has an RX load segment and a non-executable stack; its decode buffer
is RW. The kernel loads the restored program with its original segment rights.

The supported observation contract includes ordinary argument strings,
environment, inherited descriptors, stdin/stdout/stderr, normal ELF/TLS/thread
initialization, signals and exit status. Self-file paths, `/proc/self/exe`
identity, `AT_EXECFN`, and privileged-file semantics differ. Setuid/setgid inputs
are rejected; callers must not use capabilities or other privileged-file
semantics. Engines that use these excluded observations need a different
deployment method or an explicit source change.

Build on Linux x86-64, including WSL Ubuntu, using Python 3.10+ and a compatible
C compiler/linker. The output path must be absolute and outside the repository.
Existing output files are never overwritten. For example:

```sh
python3 engines/scripts/elf_loader.py \
  /tmp/rove4k-build/engine /tmp/rove4k-build/engine-packed --filter auto > /tmp/rove4k-build/pack.json
```

Build scripts can import
`pack_elf(input_path, output_path, *, cc='cc', timeout=120, filter='auto')`.
It returns input/output hashes, complete artifact and compressed payload sizes,
source hashes, compiler/linker versions and the original ELF interpreter. The
timeout covers compression and compiler invocation. It verifies a build-time
byte roundtrip; callers must also run the resulting engine's actual protocol and
chess checks. `runtime_validation: caller_required` makes that distinction
explicit. Changing temporary build directories does not change artifact bytes
with the same inputs, sources and toolchain.

The optional branch-offset filter scans the entire original file. At each
complete `E8` or `E9` five-byte sequence it adds the following file offset to the
little-endian 32-bit operand modulo 2^32, then skips all four operand bytes. The
native inverse subtracts the same offset after LZ decompression and before
writing the memfd. Opcode-looking bytes inside operands are skipped by both
passes. This is a reversible byte transform, including non-code ELF contents;
it does not identify instruction boundaries or change the restored program.

Every call builds and measures both `none` and `bcj` complete ELF candidates.
`--filter auto` chooses the smaller complete artifact, including the actual
inverse code, and prefers `none` on a tie. `--filter none` and `--filter bcj`
explicitly choose that candidate while retaining both measured sizes/hashes in
`filter_candidates`. The metadata records the selected `filter` and algorithm
version separately from the LZ codec. This avoids choosing a smaller compressed
payload when its added decoder would make the submitted file larger. For
example, one C fixture's payload shrank by 26 bytes but its complete ELF grew by
102 bytes; auto retained the unfiltered candidate.

The complete ELF size, including all headers and the loader, determines the
4096-byte size gate. A successful packed program can remain too large. Standard
Rust runtime removal, a stronger codec or smaller source logic are separate
optimizations; this packer does not claim to solve those costs. The field
`within_size_limit` is only a byte-count result, not competition eligibility or
protocol acceptance. In particular, the permissibility of executing one's own
restored ELF must be checked against the actual event's deployment rules.

Run the focused checks on Linux with both C and Rust available:

```sh
RUSTC="$HOME/.cargo/bin/rustc" python3 engines/scripts/elf-loader/test_loader.py
```

The checks cover hand-authored codec/filter boundaries, malformed streams,
operand opcodes, wraparound, random binary buffers, long-window and
incompressible data, then compile C and standard Rust programs with threads.
They execute all three filter modes with an empty executable search path and
compare the original and final ELF's argument/environment/stdio/exit behavior.
The programs also stream their own executable bytes, verifying that the native
inverse restores every original byte. The checks verify byte-identical rebuilds
and execute a deliberately corrupted payload to check native rejection. These
fixtures establish loader behavior and do not replace engine validation.
