# Optional Rust shipping source specialization

`generate.py` provides explicit A / shipping source candidates. It keeps
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

The existing loose configuration is `ROVE_VARIANT=A`, `ROVE_DEV=0`,
`ROVE_PARALLEL=0`, `ROVE_MODEL=0`, `ROVE_HQ=0`, workers 1 through 512, and TT bits
8 through 26. Optional F flags must be zero. The public recipe environment may
also contain `SOURCE_DATE_EPOCH=0`, `LC_ALL=C`, and `TZ=UTC`. Unknown profiles,
source bindings, files and environment keys fail explicitly. Other families,
policies and model representations remain canonical candidates.

The separate fixed-root source form uses `ROVE_PARALLEL=1` with exactly two
search workers and TT bits 18; the other fixed values above remain unchanged.
Its metadata producer is `rust-A-fixed-root-structural-v1` and
`guards.parallel` is `root`. It derives `parallel.rs` from the bound canonical
production file through 28 exact token edits and checks the full inverse before
returning. It does not use the loose `parallel.in` backend or copy a scheduler.
The existing loose output and metadata are byte-for-byte unchanged at the same
configuration. `main.in`, `parallel.in`, `syntax.py` and the six canonical input
bindings remain unchanged.

Fixed root retains the canonical `Depth::work` queue, Acquire/Release alpha
publication, mutex-protected incumbent and all-required-complete aggregation.
The leader first searches one legal root move with the full window. That exact
NORMAL result seeds the incumbent and `finished=1`; `cache=None` makes
`first_job=1`, so the already completed first task is skipped. The typed
depth-local cache consumer remains, but mode 1 has no `Some(proposal)` producer.
PALS and its feedback-approved unrestricted Repair producers are excluded,
along with group, hybrid and whole-root loose scheduling. This is the existing
Rust mode 1 seed-and-skip behavior, not the C completed-slot dispatcher.

`MoveList::extend`, `search_move`, `search_move_hint` and `Helpers::task` remain
because root splitting uses them. Partial searches call the real
`Board::play(first)` at ply 1 with the negated window, preserving child history,
mate distance, halfmove/repetition rules, requested depth and root move witness.
Root draw/terminal handling runs before first-child work. An incomplete depth
does not replace the previous completed result; the unchanged runtime checks
the chosen move against the immutable root's legal moves and uses its legal
fallback (or `0000` for a terminal root).

The original GO `Control` and deadline are shared by every root task. Frozen
correction/epoch publication, root owner lifetime, helper drain, pool reuse and
helper/coordinator joins stay on the canonical paths. Resource values are
source constants; this form adds no public UCI resource options. The production
qualification below observed the expected three persistent startup TIDs for two
workers. Rust's correction contributes to the frozen leaf
evaluation and its epoch/history contribute to TT keys; these semantics differ
from C and are not a language-only matched comparison.

The first fixed-root source generation contains 38,452 bytes across six
files (including the 5,583-byte derived scheduler), versus 34,402 bytes for the
existing loose source at workers 2 / TT bits 18. These are source sizes, not
native or packed sizes. Source binding, exact inverse, protected production
paths, deterministic generation and loose-output preservation were checked.

The subsequent ordinary Linux x86-64 Rust 1.97 build used the fixed shipping
2-worker / TT18 root profile, size optimization and fat LTO. Its canonical
native is 374,952 bytes; the root-specialized native is 373,672 bytes, a
1,280-byte reduction. The root-specialized and then lexical forms have identical
native bytes. The canonical and root-specialized natives are distinct.
The subsequent generic source-archive comparison used the same frozen
`pack.py` LZMA/XZ preset-9/base85 context: canonical lexical Rust source was
64,853 bytes and its whole package 24,961 bytes; fixed-root structural then
lexical source was 38,458 bytes and its whole package 16,151 bytes, an
8,810-byte whole-file reduction. All four C/Rust source packages passed strict
restoration with no compiler call; the corresponding C whole packages were
21,175 and 15,140 bytes. This generic context differs from the maintained tiny
entries and does not replace their measurements. Packaged UCI/startup was not
executed. See the repository's engine plan and results documentation for the
separate generic-cost evidence and its final index.

Two separately compiled non-test consumers appended external observation
adapters to exact canonical or generated module prefixes. Both used DEV0 / A /
root1 / 2 workers / TT18 and called the real Engine, Searcher and Board methods.
They passed first-child ply-1/window/history comparisons, actual TT
EXACT/LOWER/UPPER entries, root move/depth witnesses, mate distance, draw before
an irreversible first move, completed-depth preservation under a 21-node
budget, unchanged deadline and helper drain/join. The initial `finished=1`
publication was checked in source; runtime observed `cache=None`, `first_job=1`,
20 completed moves and 40 actual jobs across two completed depths. A direct
Engine fixture has its caller and one helper, so its two observed threads are
separate from the production Runtime's three-thread contract.

The canonical and selected production natives each passed quit and EOF sessions:
28 legal results across four sessions, using the existing Engine client and
independent rules oracle. The checks covered shipping bare/own-clock GO,
stop, GO-position readiness fencing, active quit/EOF, three persistent startup
TIDs, a sleeping stdin thread with both search workers consuming CPU, and
physical process/TID/group exit with joined readers. Shipping DEV-only
depth/nodes/movetime fields were consumed with a supported clock; they were not
used as limit witnesses. All owned groups ended without forced cleanup.
These are focused production and direct-search checks, not strength, scaling,
time-limited trace equality, 4K package eligibility or final hardware acceptance.
The historical measurements and runtime checks below apply only to the loose
form.

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
