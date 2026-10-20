# Optional Rust shipping source specialization

`generate.py` is an explicit A / shipping / loose-SMP source candidate. It keeps
the canonical independent Rust implementation in `engines/rust` intact. The
generator removes inactive source before source archiving, where rustc's native
dead-code elimination cannot reduce the archived input.

```python
output_files, metadata = specialize_rust(files, configuration=fixed_env)
```

The function performs no I/O and does not mutate its input dictionaries. Its
module loads the two checked-in templates and lexical helper once on import.
Inputs use relative POSIX paths such as `rust/main.rs`. It accepts the exact six
Rust production files from checkpoint `de5676d`, plus optional
`model/frozen.rs`. SHA-256 source binding uses Rust's CRLF-to-LF input
normalization, allowing the verified LF Git files and CRLF Linux snapshot.
Metadata retains every actual raw input SHA-256 and CRLF count, the total input
byte count, and the normalized binding hashes. Content drift and lone CR are rejected.
This prevents applying these specific rewrites to a changed program. The inactive model file is omitted only for the
accepted A / MODEL0 configuration.

The supported configuration is `ROVE_VARIANT=A`, `ROVE_DEV=0`,
`ROVE_PARALLEL=0`, `ROVE_MODEL=0`, `ROVE_HQ=0`, workers 1 through 512, and TT bits
8 through 26. Optional F flags must be zero. The public recipe environment may
also contain `SOURCE_DATE_EPOCH=0`, `LC_ALL=C`, and `TZ=UTC`. Unknown profiles,
source bindings, files and environment keys fail explicitly. Other families,
policies and model representations remain canonical candidates.

The source form preserves A's incremental HCE, quiet/continuation/capture
history, correction learning, frozen evaluation epochs, reversible-history TT
keys, paired TT publication and move-witness semantics. Its selected runtime
still allocates the configured shared table and private searchers at startup,
waits for helpers at each depth, and chooses `leader.or(first_helper)` in fixed
worker priority. Stop, reset, invalid-position replacement, EOF, quit, startup
readiness and panic-to-abort retain their physical completion barriers.

The generator removes test code and DEV UCI arms, unselected evaluation and
board operations, F-only probes and B-only singular/SEE work, and split/PALS/
hybrid scheduling. `main.in` and `parallel.in` express the selected shipping and
loose-SMP paths without the inactive data fields. It deliberately retains the
eager `Table::put` call from `if !put(...) && variant == F`: the F condition is
false for A, but Rust evaluates that write first.

`syntax.py` preserves literal spellings and Rust parser tokenization rather than
source spans or arbitrary procedural-macro punctuation-spacing observations.
Canonical production code is bound and audited for this scope. The public
`specialize_text` fixture helper requires explicitly unshadowed constant names;
it is not a general Rust name resolver. Unknown calls, overloaded field reads,
match guards and ambiguous condition blocks retain their evaluation effects.

The first fixed local proof used Linux x86-64, Rust 1.97, two search workers,
TT bits 18, size optimization and fat LTO. Actual complete-file measurements
include source restoration, the compiler recipe and launcher:

| Source form | Source bytes | Native ELF bytes | Smallest whole source file |
| --- | ---: | ---: | ---: |
| Canonical | 86,509 | 372,264 | 23,719 |
| Lexical | 61,773 | 372,264 | 18,990 |
| Structural | 34,335 | 370,544 | 11,675 |
| Structural, then lexical | 34,341 | 370,544 | 11,681 |

Each of the four native forms was independently rebuilt with identical bytes
to its own first build. The structural and structural-then-lexical native
images also match each other; canonical and lexical native images are distinct.
All 48
complete source/native codec and transport artifacts were reproduced. The
baseline binary, selected binary and smallest selected source/native files
passed the shipping protocol, lifecycle, legal selfplay, EOF and quit checks,
including fixed startup thread identity. A separate fixture driver compared
the original and selected board/evaluation/search on 44 positions: legal move
sets, perft counts, and completed depths 1 through 3 had identical results,
scores, best moves and node counts. Independent oracle checks covered every
position's legal moves and perft 1/2, six published perft-3 totals and startpos
perft 4. These fixture drivers and reports are outside the runtime archive.

These sizes remain above 4,096 bytes. This proof does not establish a 4K entry,
other-family correctness, large-machine scaling, search strength, performance,
or equality of time-limited multi-worker traces. The remaining source is chiefly
board rules, search, fixed startup coordination and standard I/O; further size
work must change their representation while preserving the selected contracts.

The focused suite has 16 tests, including nine original/transformed fixture
pairs that are actually compiled and executed. Run it with an explicit compiler:

```sh
RUSTC=/home/stemxstudio/.cargo/bin/rustc PYTHONDONTWRITEBYTECODE=1 \
  python3 engines/compact/rust/test_generate.py -v
```

`cost.py` is a read-only source inventory. Its omission-based compression
marginals identify priorities; they are not compilable candidate measurements.
