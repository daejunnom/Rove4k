# Independent source-first Rust A candidate

This directory is an optional Rust A implementation designed around small source
structures. It uses Rust's standard library, has no external crates or C backend,
and leaves the canonical `engines/rust` implementations unchanged. It is an A-only
candidate; B–F and their specialized search/evaluation policies are separate work.

The four production files are `main.rs`, `board.rs`, `search.rs` and `runtime.rs`.
`dev.rs`, `tests.py` and `tests/` are development inputs, not shipping source.
Source size, executable size, complete launcher size, runtime validation and
competition eligibility are separate results. A completed build alone establishes
neither algorithm acceptance nor 4 KiB eligibility.

## Search design and canonical differences

This is an independent engine architecture. Its source generation only removes
inactive source from this candidate; it does not transform or preserve the
canonical Rust A search's full behavior.

The correction snapshot is frozen once per `go` and used by every worker and all
depth iterations in that job. The canonical implementation's freezing boundary
is per depth. Each worker keeps private history, continuation and learned
correction state. Only worker 0's learned correction coefficients become the
snapshot for the next `go`, including when a helper supplies the selected final
move. Updates from completed subtrees remain in that learned state even if the
enclosing root iteration is later aborted; final move publication still retains
the last completed root result or its legal startup fallback.

The shared TT publishes one coherent full-key entry with an exact, lower or upper
bound while holding its slot lock. This differs from the canonical paired TT's
interval representation. The key includes the game/search history context,
halfmove clock and frozen correction epoch. These are explicit design choices
whose semantic tests and size results belong to this candidate.

## Fixed build and packaging contract

Run on Linux x86-64, including WSL Ubuntu, with Python 3 and a Rust compiler:

```sh
python3 -I -B engines/compact/tiny-rust/build.py \
  --out /absolute/new/tiny-rust-A --workers 2 --tt-bits 18 --reproduce
python3 engines/tests/verify.py \
  --manifest /absolute/new/tiny-rust-A/validation-manifest.json \
  --out /absolute/new/tiny-rust-A-verification --startup-threads 3
```

`--out` must be new, absolute and outside the checkout. `--workers` accepts 1–512
search workers; `--tt-bits` accepts 8–26. The fixed compiler environment contains
`ROVE_WORKERS` and `ROVE_TT_BITS`; these are compile-time inputs. Workers and the
shared table are created at startup. Main owns stdin, giving `workers + 1` engine
threads. Resource sizing is not an interactive shipping option.

Matching-side `wtime`/`btime` presence is preserved even when its decimal value is
missing, invalid or overflows `u64`; these inputs receive a bounded 1 ms budget.
An explicit `go infinite` retains its separate unbounded-search meaning.

The default compiler recipe is Rust edition 2024, size optimization (`z`), fat
LTO, one codegen unit, aborting panics, no debug information, stripped symbols and
no ELF build ID. `--rustc` selects the host build compiler. Source launchers use
the literal command `rustc`, resolved through the target caller's `PATH`; host
compiler paths are report metadata. Their actual startup smoke uses a controlled
`PATH` containing the selected host compiler directory and standard Linux tool
directories. A usable Rust compiler and linker must be present there. `--dev`
enables the explicit `tiny_dev`
configuration and includes `dev.rs`. `--no-pack` omits complete launchers, and
`--no-smoke` records runtime startup as unverified. These flags do not imply
validation beyond the actions recorded in the build report.

Before compiling, the builder copies every production input, its own producer,
the shared Rust lexical helper and the general launcher producer into
`out/recipe`. Subsequent imports and generation use those frozen bytes. The
report records exact input and recipe hashes, compiler version, fixed compiler
arguments/environment and each source/native/complete-file size and hash.

The `original` and `lexical` forms compile the same selected source inputs.
Shipping additionally builds a `shipping` form whose inactive development and
test source is physically removed. Only this pruned form enters shipping source
launchers. In particular, a false `#[cfg(tiny_dev)] mod dev` declaration, DEV
counter fields, initializers and statement blocks, and conditional test modules
are absent from the archived source, rather than relying on native dead-code
elimination. Development builds identify the pruned form as `dev-specialized`;
they are never relabeled as shipping.

The producer evaluates the explicit `tiny_dev` and `test` cfg atoms and their
`not`/`all`/`any` combinations. It rejects unknown configurations, `cfg!` and
`cfg_attr`, and accepts only the four named production paths plus optional
`dev.rs`. Strings, character literals, lifetimes, raw strings and nested comments
are handled by the shared Rust tokenizer. It groups consecutive attributes so
removing a false cfg target cannot leave a preceding derive attribute attached
to the next item. Runtime DEV statements use attributed blocks; this is a
bounded source contract, not a general Rust preprocessor.

For the pruned form, all six combinations of zlib/bz2/lzma and base85/ZIP are
measured for complete source launchers and for complete native launchers. Source
launchers contain all four source files, fixed configuration, restoration logic
and compiler command. Native launchers contain the full ELF. No model, source,
crate or executable is downloaded. The smallest complete source launcher is
identified separately from every native launcher.

`--reproduce` independently generates source and metadata a second time, compiles
in a second directory with the same path remapping, compares complete native
bytes and recreates every launcher for full byte comparison. The manifest pins
the actual executable hashes and adds the selected complete source launcher for
external verification. The build's UCI smoke observes `uciok` and `readyok` and
successful quit for each native form and the smallest complete source and native
launchers; broader runtime and chess checks belong to the independent validation
runner.

## Clock-corrected whole-file checkpoint

The current portable immutable checkpoint uses Rust 1.97.0 on Linux x86-64,
two search workers, TT bits 18 and the compiler recipe above. All sizes below
are actual bytes from completed builds, rather than compressed-source estimates:

| Form | Source bytes | Native ELF bytes |
| --- | ---: | ---: |
| Original | 33,693 | 339,912 |
| Lexical | 25,698 | 339,912 |
| Physically pruned shipping | 23,334 | 339,912 |

The smallest complete source package is **9,074 bytes**, using ZIP/LZMA. Its
compressed payload is 7,987 bytes and the remaining complete launcher overhead is
1,087 bytes. Its compiler command is `rustc` on the target's `PATH`; the complete
bootstrap contains no host compiler path. This exact package has SHA-256
`35bc0d0f930da90ac4826659c60db5c3dcf805edba7047d85855d86d13cc8a72`.
The smallest complete native package is 145,081 bytes. Neither artifact meets
4,096 bytes. The earlier 9,067-byte portable package predates the production clock
correction and is retained separately. The earlier 9,087-byte host-bound source
recipe is also retained. Each changed recipe or source was regenerated,
independently rebuilt and executed; earlier results are not assigned to changed
bytes.

Each form's independent second native build reproduced its own complete bytes.
The three forms have different native hashes despite equal executable sizes;
size equality is not a claim of semantic equivalence. All twelve complete source
and native launchers reproduced their full bytes. The chosen source and native
packages both executed the UCI startup/quit smoke successfully. The shipping
source producer removed 26 conditional targets and archived exactly the four
production files, with no DEV or unit sources. The source package smoke used the
controlled target `PATH` recorded in its report; host-specific compiler locations
are metadata, not artifact inputs.

The checkpoint is identified by these actual raw source hashes:

| Input | SHA-256 |
| --- | --- |
| `board.rs` | `47e6289e06eff93484c50ef4218729b444eea7b4a8868362dd1d0d37eaaf06d9` |
| `main.rs` | `c1d659cf38473d838505e3912effac0798841eb160d7033a21ab2dc5443ed56d` |
| `runtime.rs` | `2bf60847bf40c882ac16e0840f51fd24d9cf6dad5bb463e9dda0a83623ac6dec` |
| `search.rs` | `4573947933c348cff4fa371f656dc5cdc21560ea09ca95d98dfaf0667ce6b981` |

An earlier frozen attempt failed at the actual shipping compilation because a
development attribute had been placed directly on an `if` statement, outside the
producer's attributed-block contract. That source snapshot is retained. The
runtime now encloses it in an attributed block, and the producer explicitly
rejects such unsupported targets. The successful checkpoint above is a separate
snapshot; the earlier failure is not relabeled as passing.

The same four production source hashes also pass the independent validation
runner at two workers and TT bits 12: 14 actual Rust unit tests, original versus
pruned cfg fixtures with four real compiler invocations, five shipping process
groups and eight DEV process groups. Ten additional shipping cases cover both
sides with malformed, negative, overflowing, missing and zero clocks. Each
produces a legal `bestmove` without a preceding `stop` or EOF. These checks use
their own configuration and report; they do not substitute their executable
hashes for the TT-bits-18 complete artifacts measured above.

The exact selected source and native launchers above have also passed the full
shipping process suite at two workers and TT bits 18: five groups per actual
launcher, ten groups in total. Both retained three stable startup thread IDs.
Twenty additional malformed-clock cases, ten per launcher, all produced a legal
`bestmove` while stdin remained open and before any `stop` or EOF. The source
launcher ran with the controlled target `PATH` recorded in the verification
report. A follow-up harness initially referenced a nonexistent helper; that
harness failure is preserved separately. The corrected clock-only follow-up
executed all twenty cases without changing either engine artifact.

The four pruned source hashes in the final package also match the separately
measured production stack snapshot. With size optimization, fat LTO, one codegen
unit and aborting panics, the actual DEV-free search plus an appended fixture
visited 128 nodes through the ply-127 abort on an actual 1 MiB thread, with zero
recursive allocator calls. The fixture does not enter the shipping archive.
Emitted production CFA offsets were 4,640 bytes for recursive search, 73,344 bytes
for the worker body including its private worker state, and 2,240 bytes for
pseudo-move generation. The representative sum
`128 * 4640 + 73344 + 2240 = 669504` bytes describes those selected frames. It is
not a complete bound for asynchronous signals, standard-library internals or
every call path; the actual 1 MiB fixture result is separate observed evidence.

The candidate is being integrated and validated. Follow the immutable build
reports and independent validation transcripts for exact accepted snapshots.
These local checks do not establish full algorithm acceptance, playing strength,
performance, machine-scale behavior, a universal stack bound or full competition
eligibility.
