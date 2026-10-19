# Structural C source candidate

This optional source recipe is selected by `engines/scripts/build.py
--structural-compact`. It transforms the current canonical `engines/c` source,
then uses the selected C compiler's conditional specialization and the ordinary
lexical compactor. It does not supply a separate weakened chess core.

The recipe currently applies to fixed Loose SMP only. Root splitting, groups,
PALS and hybrid retain the canonical implementation. Every Loose worker searches
the complete root; helpers and the coordinator start before the first UCI input.
The lowest-index complete result with a compatible bound wins, and the completion
barrier precedes callback-state reuse. Startup failure exits instead of silently
reducing workers. The helper pool is joined before its synchronization is freed.

`fixed_loose.h` specializes the generic scheduler to that policy. `uci.c.in` is a
shipping-only main: Session owns the position and history, commands update them
after cancellation completes, and the constant `@VARIANT@` identity is generated
from the selected A-F input. Whole-line input admission, transactional moves,
clock-presence handling and asynchronous stop/readiness are retained. Static
POSIX initializers and a persistent coordinator avoid per-search allocation.

Shipping startpos initialization directly places the canonical pieces and derives
the same position key. It does not require a general FEN interpreter. A/D/F without
the optional model use explicit signed eight-bit mailbox cells; all produced and
admitted pieces are in -6..6 and consumers retain C integer promotion. E/model's
`int[128]` interface and C's SIMD packing retain their canonical representation.

The shipping Loose iteration controller omits split-root move arrays, diagnostic
PV copying and counters that no shipping command observes. It retains the same
PVS or MTD root calls, completed-depth acceptance, last completed best move,
history/correction behavior and shared TT. The canonical board, move application,
attack logic, evaluator, ordering, QS, TT and selective search remain the source
of those operations. A family's selected SEE/singular, HQ, SIMD, model and MTD
paths are not removed when reachable from its search.

After actual compiler specialization, conservative function-name reachability
removes definitions unreachable from `main` or owned global initializers/macros.
Address-taking and function-pointer arguments count as references. Ambiguous names
retain every definition with that name. This is a recipe for these owned sources,
not a general C optimizer. Unsupported declarators fail rather than being guessed.
The generated source must compile, reproduce and pass runtime validation.

`test_generate.py` checks reachability safety boundaries. `test_loose.c` executes
four simultaneous workers, complete-result precedence, rejection of an invalid
bound, cancellation, startup/restart and shutdown. They supplement the repository's
actual engine and shipping tests. These source reductions and tests do not establish
a 4,096-byte final submission, playing strength, or target many-core performance.
Complete launcher/ELF size and executable behavior must be measured separately.
