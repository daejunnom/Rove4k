# ASCII streaming ingress: one Tiny Rust D first-cost candidate

The single candidate completed fixed 2/18 first-cost and focused qualification.
Both complete candidate ELFs are **16,816 B**, an **8 B** saving from independently
reproduced 16,824 B controls. There was no compiler, linker or layout change.

| Profile | Candidate complete ELF SHA-256 |
| --- | --- |
| HQ | `f8581a68f09d4d9cdc3e1413aa45ffb385bafd8240f1432403629ec2a0e544f8` |
| Scalar | `bd0e3bd1567ae906d4ab9704603204d22302895df1f05679f6221d6445aef878` |

For either lane, text fell 848 B and read-only data fell 555 B, but the unchanged
4 KiB alignment absorbed those changes. The actual whole-file saving came from
data falling from 16 B to 8 B: byte comparisons no longer need the old bcmp GOT
entry. The own bcmp implementation remains in the original assembly section.
`engine_main` fell from 4,379 B to 3,414 B. Its actual push/probe/sub prologue gives
a frame estimate of 431,952 B versus 169,824 B; this excludes callees and is not
a universal asynchronous stack bound. The removed token array accounts for
262,144 B of source-level stack storage. Readable Rust source **increased** from
38,625 B to 39,461 B; the same measurement-only merged layout increased from
38,641 B to 39,477 B. No compressed/source archive or 4 KiB result is claimed.

The maintained 17-file Rust D implementation and its qualified 16,824-byte HQ and
scalar controls remain unchanged. This new candidate explicitly rejects a whole
line containing NUL or any non-ASCII byte before command dispatch. Accepting
Unicode whitespace is intentionally removed from this shipping input policy.

`main.rs` is the readable candidate. It keeps the original 32,768-byte bounded
line/EOF reader but streams borrowed byte tokens. ASCII whitespace includes all
bytes 9 through 13, including vertical tab, plus space, preserving original ASCII
whitespace behavior. Nonempty token count needs no stored array or pre-count:
`2*T - 1 <= N <= 32768` implies `T <= 16384`.

The unsigned decimal parser retains leading `+`, leading zeros, exact `u64`
overflow rejection and invalid/missing-token behavior. Lookahead is consumed
only after successful numeric parsing, including after an unrecognized key.
Position replay remains transactional with the same 4,096-key history bound.
The UCI name, minimal commands, `stop`, `ucinewgame`, `infinite`, clock allocation,
resource profile, worker lifetime and output are unchanged.

`parse-bytes.rs.in` shares the original board move parser with a byte entry point.
The old `parse(&str)` API is a safe wrapper. Every original parser statement
after `as_bytes()` is unchanged, and all other board, play, search, TT, runtime,
OS, compiler and linker logic stays exact. There is no unchecked UTF-8 or new
unsafe access. `producer.py` fails closed on original input or adapter drift.

Independent source review must bind the exact candidate source hashes before
the first compiler invocation. The cost recipe compares original/candidate HQ
and scalar complete ELFs with the unchanged builder, twice each. Merged source
counts use an identical inline-module layout for measurement only. No native is
executed during first-cost; an equal or larger whole artifact stops the axis
without runtime tests or another representation variant.

`control/` contains all 17 original source files as an ordinary byte-exact
snapshot taken before implementing this candidate. It includes the original
main, board, core, build recipe, linker and strict helper. It is a historical
source input, never an alias or symlink to the future mutable canonical engine.
The default cost input and runtime helper/source checks use this owned snapshot.
An explicitly relocated snapshot can be supplied with `--control-source` for
cost, or `--stable`/`--helper` for runtime; original hash guards still apply.
Use these experiment runners to reconstruct the frozen build layout rather
than invoking historical control verification tools in isolation.

Two independent source reviews preceded the first compiler invocation; their
exact main, adapter, producer and generated seven-input hashes are checked by
`run_cost.py`. Its review receipt and original source/control preservation live
in external evidence, not in the source tree. Reproduce the same fixed cost with:

```sh
python3 -I -B engines/experiments/tiny-rust-d-ascii/run_cost.py \
  --out /absolute/new/ascii-cost --rustc rustc \
  --review /absolute/external/precompile-review.json
```

The initial comparison reproduced all four original/candidate HQ/scalar native
forms twice and passed the original static ELF gates. It did not execute them.
The positive whole-file result was followed by these separate bounded checks:

- `verify_helpers.py` extracts the exact candidate token/numeric/position/clock
  helpers and actual candidate board, and retains the exact old functions/board
  as differential references in distinct std test images. Both lanes pass seven
  groups: 16,512 short ASCII numeric cases plus 26 boundaries, 16,512 token cases,
  the maximum 32,768-byte/16,384-token line, 2,172 clock comparisons, 19 position
  comparisons plus 4,095/4,096-move boundaries, and focused byte move parsing
  (nine boards, 128 pseudo strings, 9,706 byte mutations and 19 special moves).
  Search, the raw OS and shipping main are not executed in these diagnostics.
- `verify_runtime.py` checks the exact two candidate ELF and source pins before
  any Popen. It freezes the prior strict helper byte-exact and changes only its
  input accounting to the declared ASCII policy. Both actual no_std profiles
  pass strict lifecycle/clock/history/EOF/closed-output tests and supplemental
  full-line rejection, all six ASCII whitespace roles, transactional replay,
  numeric boundaries and infinite cases. Each has 63 admitted GO commands and
  63 bestmoves. All 16 owned sessions terminate without emergency cleanup:
  14 normally and two with expected SIGPIPE. Three TIDs and two guarded 1 MiB
  worker-stack mappings are observed per process.

Independent read-only reviews cover both test sources and their actual reports.
Unknown numeric consumption is supported by the source/differential test, not
inferred solely from a move. A side-to-move witness does not prove complete board
identity by itself. Existing broad board/search/raw-OS proofs retain their exact
original bodies and image classes; there was no new broad matrix, deep, ptrace,
fault or performance campaign. The maintained 17 files remain unchanged. This
experiment has not been promoted, admitted to a loader or registered as CI.

The executed first-cost and runtime verifier versions remain frozen in external
evidence. A later input-path-only revision selects `control/` by default; its
four reproduced native forms equal those exact original outputs, with two
identical builds per form. The runtime CLI revision was checked by exact source
diff and `--help`, not a second engine execution. That revision does not turn the
prior runtime report into a new verifier execution.

For a new external output directory, the focused verification commands are:

```sh
python3 -I -B engines/experiments/tiny-rust-d-ascii/verify_helpers.py \
  --cost-dir /absolute/ascii-cost --out /absolute/new/ascii-helpers --rustc rustc
python3 -I -B engines/experiments/tiny-rust-d-ascii/verify_runtime.py \
  --hq /absolute/ascii-cost/candidate-hq/first/x \
  --scalar /absolute/ascii-cost/candidate-scalar/first/x \
  --out /absolute/new/ascii-runtime
```
