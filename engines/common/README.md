# Shared readable engine source

The active C engines own their layouts, evaluation/search policy and runtime
lifecycle in `engines/compact/tiny-entry-{a,b,c,d,e,f}`. Identical source bodies
have one owner here: `board.c` owns mailbox state/FEN operations, `move.c` owns
the shared move/walk bodies, `search.c` owns shared budget/TT/history helpers,
and `protocol.c` owns reusable protocol bodies. These are build-time fragments,
not separately linked translation units.

An engine template includes a named body using, for example,
`#include "rove-common/board/mix"`. The named include deliberately cannot be
compiled directly. `engines/scripts/source_composition.py` expands it before
the existing readable transformations and before C preprocessing. Fragment
framing comments and their newlines are excluded; all surrounding template
bytes are retained. Assembly introduces no calls, dispatch table, data layout,
features or conditional compilation.

Production recipes pin three distinct things: the raw family template, the
explicit shared C inputs, and the assembled readable source. The initial
extraction retains the previous assembled source digest and every downstream
source/native/package expectation. Shared C files are engine inputs in
`production.py`, while the assembler is a tool input. Fresh archives and frozen
build snapshots include both roles. Development tools that read a canonical C
file directly must use `read_source(root, logical_path)`; production builders
also admit the recipe pins before assembly.

## Contracts kept separate

| Fragments | Consumers | Reason for the boundary |
| --- | --- | --- |
| `board/put_scalar` | A, D, F | Maintains scalar evaluation in every build. |
| `board/put_dev_evaluation` | C, E | Scalar evaluation maintenance is diagnostic-only. |
| `move/make` | B, C, D, E, F | These exact bodies retain their own king-capture check; A has a different shipping/DEV boundary. |
| `search/probe`, `probe_explicit_write` | A/F and C/E respectively | A/F use nonzero data to request a write; C/E pass the write operation separately. |
| `search/learn_signed` | C, E | The decay uses the absolute bonus, preserving signed history updates. |
| `protocol/parse_with_board` | A, C | Accepts a nullable move string and returns the successor board. |
| `protocol/parse_move_only`, `first_legal` | B, E | Move parsing returns only the move; fallback is separate and the caller constructs the successor. |
| `protocol/work_pending_start` | A, C, F | Startup readiness consumes the initial pending count. |
| `protocol/work_ready_start` | B, E | Startup readiness has a separate ready counter. |
| `protocol/set_position_*`, `go_*` | Matching parse/lifecycle groups | Preserve each group's caller and worker-reset contracts. |

F's parser still belongs to its template. It has A/C's interface but formats
each candidate even for the null-string fallback. This is a representation/work
alternative to compare with the final whole-file codec; extraction does not
claim that one spelling is smaller for every family. D's raw-syscall runtime
also remains separate from the pthread/stdio protocol.

Shared ownership does not itself reduce submission bytes. The assembly check
establishes unchanged source; compiler/whole-file reproduction and runtime
qualification keep their existing separate gates. Semantically different
implementations must not be merged just because their function names match.
