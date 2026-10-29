# Tiny Rust A compiler-stdin stream experiment

> **Retired by user request on2026-10-25.** The Rust A stream/prepared/TCEC
> producers and their test/runtime CLIs are disabled before output creation.
> The7502-byte selection below is historical and is no longer produced by CI.
> Sources remain recoverable; shared compiler/packaging helpers and independent
> Rust D consumers are retained. The rest of this document is historical.

## Explicit Rust prepared-input and fixed-source environment candidates

The build-time `--prepared-input` candidate preserves the Rust envelope while
sharing W1/W2 and seek producers. It retains `r4s-`, the fixed Rust command,
positive compiler status and conventional128+signal mapping, SIGCHLD handling,
parent UCI stdin and engine `sys.argv[1:]`. The shared C default admission and
emitted bytes are unchanged; Rust uses the explicit `rust-stream-v1` contract.
Compiler FD0 becomes a private seekable regular file prepared under the existing
blocked INT/TERM interval. Pending cancellation can reach the parent after spawn
publication; preparation cancellation does not promise compiler0. A pending
buffered write failure can now arise at seek rather than explicit flush.

`--omit-resource-environment` requires `--embody-resources` and the exact
22981-byte/516aab3e source at workers2/TT18. It omits only the two resource
overrides, retaining SOURCE_DATE_EPOCH0/LC_ALLC/TZUTC and caller environment.
General/unembodied source still receives all five overrides. The native image
must independently compare equal before this candidate can be qualified.

The old9074-byte ZIP control and old9009-byte selected XZ stream remain distinct.
The existing Python stdlib self-decoder is preserved, not counted as a new gain.
New fixed-codec costs, independent native comparison and current runtime
qualification are pending. Prior qualification below retains its original scope.

The test host also removes unconditional post-reap signals to saved compiler
PGIDs. New group-bearing fixtures retain their own wrapper leader with the
existing Rust shipping host owner until settlement, then reap. On exceptional
closure they first ask that still-owned wrapper to drain its own compiler group.
No new fault campaign has run at this source checkpoint.

This experiment measures a different source layout and complete-file launcher for
the fixed Tiny Rust A production checkpoint. The stable four-file engine and its
9,074-byte ZIP/LZMA artifact remain unchanged. The engine uses Rust's standard
library, with no external crates or C backend. This directory adds no algorithm
or feature deletion to obtain its source-size comparison.

`merge.py` accepts the exact four DEV-free production inputs and emits one Rust
source unit with inline modules. The compiler reads that unit from stdin with
fixed crate name `rove4k`. `stream_pack.py` stores the source and Python bootstrap
in one compressed stream and adds the complete restoration stub. All bytes in
the resulting file count toward its measured size.

The final qualified selection is the fixed-resource XZ stream, **9,009 bytes**,
SHA-256 `d996efd72a4fed56daba9a9e9a560846e4e0b49a4aad76ad9a7702d3c5a821fc`.
It saves 65 bytes against the unchanged 9,074-byte ZIP baseline and remains above
4,096 bytes. The earlier 9,009-byte stream has different bytes and a different
hash; it is retained as a historical checkpoint below.

## Reproduce an immutable cost checkpoint

On Linux x86-64, including WSL Ubuntu:

```sh
python3 -I -B engines/experiments/tiny-rust-stream/build.py \
  --out /absolute/new/tiny-rust-stream --workers 2 --tt-bits 18 \
  --reproduce --embody-resources
```

`--out` must be new, absolute and outside the checkout. `--rustc` selects the host
compiler. The runtime source recipe contains literal `rustc`, resolved through
the target caller's `PATH`; host paths are metadata. Workers 1–512 and TT bits
8–26 are accepted compile-time inputs. The exact 9,074-byte reference applies to
the initial two-worker, TT-bits-18 configuration. Other configurations are
identified separately and do not inherit that measured reference.

`--embody-resources` is the final selection's explicit source transformation and
accepts only workers 2 and TT bits 18. It removes the now-unused compile-time
`number` helper and replaces only the two root constant initializers with those
fixed values. Its producer verifies the original environment interpretation,
module/main token identity and restoration of every other token. The board,
search and worker-runtime bodies remain unchanged. Omitting the flag retains
the general compile-time resource parser and produces a separate source class.

Before importing any producer, the builder normalizes CRLF to LF in the closed
source/helper text input list, rejects lone CR, and checks one exact Git-LF
identity per bound input. `CANONICAL_SOURCE_BINDINGS` identifies those source
bytes. `input-canonicalization.json` records each checkout input's original
size/hash, canonical size/hash, CRLF count and whether its EOL bytes changed.
The old local checkpoint's `search.rs` ended with one CRLF in a test declaration;
its historical raw hash is distinct from the current Git-LF input identity.

The builder then freezes the four canonical LF production
files, the stable source-pruning builder, Rust lexical helper, original general
ZIP packer, Tiny A stream helper and this directory's builder/merge/stream
producers under `out/recipe`. Every later producer import uses that frozen tree.
The optional `resources.py` producer is frozen and imported only when its flag is
requested. The report retains the pre-resource merge hash and saves
`pre-resource.stdin.rs`; `merged.stdin.rs` and `merged_source_sha256` identify the
actual final source sent to the compiler and packed into the selected artifact.
DEV and unit files are absent from the explicit runtime input list. Unknown canonical
source, pruned source or stable helper bindings fail rather than being silently
assigned the old checkpoint's identity.

The stable pruner removes inactive DEV and unit items, fields and blocks. The
bound merge producer then inlines those four resulting files. The build keeps
the complete compiler flags from the stable size recipe: edition 2024, `z`, fat
LTO, one codegen unit, aborting panics, stripped symbols, no debug information,
no build ID and the same cfg checking. The input changes to `-` and receives the
fixed `--crate-name rove4k`. There is no flag search. `ROVE_WORKERS`,
`ROVE_TT_BITS`, `SOURCE_DATE_EPOCH`, `LC_ALL` and `TZ` remain explicit fixed
compiler environment inputs and count in the source launcher.

The four-file ZIP/LZMA baseline is regenerated with its original compiler command
and environment. For two workers and TT bits 18, both its complete 9,074-byte
length and SHA-256
`35bc0d0f930da90ac4826659c60db5c3dcf805edba7047d85855d86d13cc8a72`
must match the existing qualified artifact. The builder does not rerun a
Cartesian matrix of baseline codecs or optimization flags.

The baseline packer is the explicit project-owned historical control
`engines/experiments/packaging-control/pack.py`, copied byte-for-byte from
`1d2e3b7:engines/scripts/pack.py` (`f95a9166...`). This ZIP retains that old
compiler owner's known boundary; it is comparison data, not qualification of
the new common compiler owner. The current stable Rust helper is consumed only
through unchanged specialization/recipe/run/smoke definitions, and the current
Tiny A helper's raw `source_literal`/`bootstrap` definitions remain byte-exact.
The qualified `stream_pack.py` runtime body and the 9,074-byte reference are
unchanged. Current generic Rust source packages use the stable Tiny Rust builder.

With `--reproduce`, the builder separately repeats pruning, merging and the
requested resource embodiment, compiles
the stdin source in a second directory with identical path remapping, compares
the full native bytes, and regenerates each complete XZ/gzip/bzip2 stream for
full byte comparison. The regenerated baseline is also compared byte for byte.
The stdin/inline-module native class is distinct from the four-file native
class: source file and line locations in panic metadata can change. Its native
hash is reported independently, without requiring cross-class binary identity.

The report records canonical pre-pruning and pruned input hashes, every recipe hash, compiler
version, exact commands/environment, merge metadata and full artifact sizes and
hashes. `validation-manifest.json` identifies the stdin native, original four-file
ZIP baseline and smallest complete stream for subsequent external verification.

The default build measures files without executing an engine or
wrapper. Runtime decoding, signal cleanup, ELF restoration and shipping protocol
qualification are separate checks of the selected artifact. `--smoke-selected`
optionally executes only the selected stream's UCI startup/quit smoke under the
controlled compiler `PATH` recorded in the report.

## Launcher boundary

The experiment freezes the Tiny A stream helper as provenance and records its
explicit adaptations. Its new shell stub immediately replaces itself with a
Python standard-library decoder, avoiding a separate `tail` or codec process
during restoration. The revised producer writes the compiler's unbuffered stdin
pipe directly and uses `waitid` with `WNOWAIT` to observe exit without reaping the
compiler leader. It drains the remaining compiler group before the final wait,
retaining the leader's identity during cleanup. Before compiler spawn it saves
and normalizes the `SIGCHLD` disposition observed at Python decoder entry, then
restores it before executing the engine. The shebang shell can normalize an
inherited disposition before Python entry; that earlier boundary is measured
separately. Cleanup covers signalable children remaining in the compiler's
process group on Linux `/proc`. An undrainable live group returns status 125 and
retains its private directory. The observed qualifications below apply to this
scope.

## Final fixed-resource result and qualification

The final selection uses Rust 1.97.0 on Linux x86-64, two workers and TT bits 18.
The original four-file ZIP regenerates to the exact 9,074-byte baseline. Resource
embodiment reduces the merged source from 23,334 to **22,981 bytes**, SHA-256
`516aab3e2f9085dd4a95503cc4ebc1a02670034a0a2daee8350081957f056e0b`.

| Complete artifact | Actual bytes |
| --- | ---: |
| Exact four-file ZIP/LZMA baseline | 9,074 |
| Final XZ stream | 9,009 |
| Final gzip stream | 9,263 |
| Final bzip2 stream | 9,141 |

The final XZ file includes its 113-byte stub and 8,896-byte compressed shared
bootstrap/source payload. Its hash is the `d996efd7...` value given above, not the
first stream's `92860a1a...` value. The final stdin native is **339,880 bytes**,
SHA-256 `c477f362dde2d347cc295cd74a5de49dd24746f221dc181a2da4a62f507e6309`.
Both independent native builds and all three complete stream codecs reproduce
their full bytes. The baseline also reproduces exactly.

| Final producer | SHA-256 |
| --- | --- |
| `build.py` | `f0536ac9cca6ed393b66e6102923cd56842d4cf593e07b12c35485976d70c879` |
| `merge.py` | `268d9ddf451fb6f81b288f38eb586ba081871a275fccd3f6b14f00e910bd5cf1` |
| `resources.py` | `01710645a6b0efebcb08892c849024eed869762beeadbbc8407fa69419460724` |
| `stream_pack.py` | `763e958d466c8f119712aa898fee9f2cbff001b62fa567299c576365b95e2638` |

Independent checks of this exact source and producer include:

- Merge fixtures compile two positive original/merged program pairs and one
  private-access failure pair, six actual Rust compiler invocations in total.
  Fifteen negative source guards reject unsupported inputs.
- Resource checks reject eleven invalid profiles/types/source shapes and verify
  the three allowed root edits, all other token identities, deterministic output
  and no I/O during the pure transformation.
- Stream checks reproduce all three codecs, preserve bytes in 33 stdin fixtures
  and reject five invalid API configurations. A real Rust fixture is compiled
  independently twice. Four compiler failure/status cases, TERM and INT process
  group cases, the WNOWAIT source contract and two `SIGCHLD` entry fixtures pass.
- Actual selected-artifact verification captures the exact 22,981 compiler stdin
  bytes, fixed arguments and five compiler environment values, and a private
  mode-0700 compiler directory. The restored live ELF hash is exactly `c477f362...`.
  The wrapper becomes the engine in its original process, with three fixed
  startup thread IDs, and accepts queued UCI input and legal/malformed move input.
- The selected source artifact and its stdin native each pass five full shipping
  groups, ten in total. Each also passes ten white/black malformed, negative,
  overflow, missing and zero clock cases, twenty in total. Stdin stays open and
  no `stop` or EOF is sent before the legal `bestmove`. Scratch directories are
  empty after these completed checks.

The initial `SIGCHLD` fixture expected a pre-shell ignored disposition to survive
`/bin/sh`; that harness expectation failed and is preserved. The corrected
whole-artifact and direct-Python-entry fixtures test their respective observed
entry states with the final producer unchanged. Earlier first-stream, waitid and
intermediate fixed-resource artifacts remain separate snapshots; their results
are not reassigned to this final hash.

The production assembly auxiliary build is byte-identical to the **entire**
selected stdin native ELF, not only its text section. It reports CFA offsets of
4,640 bytes for recursive search, 73,344 bytes for the worker body and 2,240 bytes
for pseudo-move generation. The representative sum is
`128 * 4640 + 73344 + 2240 = 669504` bytes. A separate append-only fixture using
unchanged production modules executes 128 search nodes through the ply-127 cap
on an actual 1 MiB worker stack, propagates `Abort/None`, and observes zero
recursive search allocations. Observed storage sizes are Board 160, Moves 2,056,
Worker 71,032 and TT slot 24 bytes. The fixture is absent from the shipping source.
These observations are not a complete all-path, asynchronous-signal or
standard-library stack bound.

This is local A qualification at the fixed two-worker/TT-bits-18 configuration.
It establishes no Elo, NPS, larger-machine scaling, B–F implementation acceptance
or 4 KiB eligibility. The source artifact remains 9,009 bytes.

## Preserved historical checkpoints

These are distinct immutable artifacts. Equal file lengths do not identify equal
bytes. Every checkpoint regenerated the same exact 9,074-byte ZIP baseline and
reproduced its own two stdin native builds and three complete stream codecs.
The final qualification above belongs to the last row.

| Checkpoint | Source bytes | XZ / gzip / bzip2 bytes | Selected XZ SHA-256 |
| --- | ---: | --- | --- |
| First inline modules, before WNOWAIT | 23,334 | 9,009 / 9,260 / 9,138 | `92860a1a76bb01c79ddd7d5a7669bcbf78722d65a3a8c617ffd6d5ab2db653a9` |
| WNOWAIT, general resource parser | 23,334 | 9,121 / 9,382 / 9,240 | `4a967cf5b21720c93c8d437021a68c9c6460916c75f9b6b54a5cb6aefc5de1d9` |
| Fixed 2/18, before SIGCHLD entry fix | 22,981 | 8,989 / 9,239 / 9,122 | `593d564f0e605763b485c44eb42aac57fc2bdc35a6dae2e504188be138e0836d` |
| Final fixed 2/18 and SIGCHLD handling | 22,981 | 9,009 / 9,263 / 9,141 | `d996efd72a4fed56daba9a9e9a560846e4e0b49a4aad76ad9a7702d3c5a821fc` |

Before resource embodiment, the source hash was
`06cae21874330adaf436f91d16450a53b8dbb836072531e73700f89e27de5cd3`
and its 339,880-byte native hash was
`ebb63209ed6649ade8fe909968b1c5ccfddaf1e4c3bd20f2670e8ee57c8c6d9e`.
The two fixed-resource rows use source `516aab3e...` and native `c477f362...`,
identified in full above. All raw engine inputs remain the same checkpoint.

The first stream producer was `f03198f9...`; the WNOWAIT and intermediate fixed
rows used `4354c582...`; the final producer is `763e958d...`, identified in full
above. Their complete producers, input hashes and reports remain in their
separate frozen `recipe` trees. The Tiny A helper origin remains
`b4addefbb1233881e85707aa525ca4af7f8210d9d27f56fbb52e4440a966b99e`.
No earlier result or smaller intermediate artifact is relabeled as the final
qualified selection.
