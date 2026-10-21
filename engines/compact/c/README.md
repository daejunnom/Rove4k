# Structural C source candidate

This optional source recipe is selected by `engines/scripts/build.py
--structural-compact`. It transforms the current canonical `engines/c` source,
then uses the selected C compiler's conditional specialization and the ordinary
lexical compactor. It does not supply a separate weakened chess core.

The existing Loose recipe applies to fixed Loose SMP. Every Loose worker searches
the complete root; helpers and the coordinator start before the first UCI input.
The lowest-index complete result with a compatible bound wins, and the completion
barrier precedes callback-state reuse. Startup failure exits instead of silently
reducing workers. The helper pool is joined before its synchronization is freed.

An additional fixed A root recipe is selected with `--variant A --profile
local-ship --parallel root --structural-compact`. `fixed_root.py` derives it from
the bound canonical scheduler and search callback. It removes unreachable Loose,
group, PALS and hybrid branches while preserving the normal proposal, compatible
completed-result reuse, atomic root queue and completed-iteration aggregation.
The first child still uses the canonical make, history and ply-1 search. The
canonical main, board, evaluator, search algorithm, deadline, callback drain and
helper joins remain in use. This path does not use `fixed_loose.h` or `uci.c.in`.
Its source/build guard requires A, shipping, model off, two search workers and
TT bits 18. Other root profiles are rejected; group/PALS/hybrid source requests
continue to use the canonical implementation. These are source-generation
contracts. Native size, whole-file size and runtime qualification are recorded
separately from the raw-source reduction.

The first local A/root build reduces the actual lexical compile inputs from
60,283 to 44,098 bytes. Both natives are 30,768 bytes with different hashes.
Real canonical/selected search and scheduler adapters pass under UBSan, and
four production quit/EOF sessions pass twelve legal GO results with three
persistent TIDs and physical process/thread exit. A separate generic
LZMA/XZ-preset9/base85 source envelope measures 21,175 to 15,140 whole bytes;
the packaged source is restored exactly but is not executed in that cost check.
These are bounded local results, separate from the maintained tiny entries,
4096-byte eligibility, strength and many-core scaling. See the fixed-root
checkpoint in `docs/ENGINE-IMPLEMENTATION.md` for the observation limits.

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

Shipping A further uses a mailbox-only state. Attack detection reads that mailbox,
so its unused bitboard/occupancy mirrors and material-only accumulator are omitted.
The fullmove counter has no shipping observer. Side, castling, en passant and king
squares have explicit signed-byte ranges. The halfmove clock uses `uint16_t` only
when the declared maximum root replay plus search path fits; changing that bound
outside the supported range fails generation. Incremental HCE and position/pawn
keys remain, and the insufficient-material scan checks pawns/majors together with
its existing minor-piece scan. The generated Board is 160 bytes on the checked
Linux x86-64 ABI, compared with the canonical 696 bytes. Actual move application,
all legal moves, keys, HCE and perft were compared with canonical C and the
independent rules oracle, including castling, EP and all promotion choices.

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

`compact_search=True` selects `search.c.in` as an additional source candidate;
the baseline remains independently buildable. PVS and QS share node entry,
selection, cancellation and result operations. Their TT, terminal, pruning,
singular, learning and F convergence policies remain distinct where required.
Full PV diagnostics remain in development; Loose shipping needs the root first
move. Source and native sizes must be compared independently: a shared operation
can shrink native code while increasing the compressed source by a few bytes.

`small_worker=True` additionally requires shipping mode 0 and that unified search.
`worker_state.py` maps valid 0x88 history coordinates to 64-square indices, stores
history/continuation in `uint16_t`, correction in `int16_t`, and one PV move per
ply. The source guard checks `MAXPLY<=130`, the actual wide-integer update helper,
all three history accesses and the unused callback reply removal. From zero, the
history recurrence stays in 0..16384 and correction in -16384..16384; arithmetic
continues in `int` before storage. Changing those assumptions fails generation.
The checked x86-64 Worker storage is 56336 bytes, versus 211936 bytes before this
transformation. This is allocated storage size, not an RSS or speed measurement.

`shipping_operations=True` is a separate opt-in candidate requiring unified search,
small worker state and fixed Loose shipping. Its raw-source stage installs
`search_stop.c.in`: every search entry still observes shared cancellation, while
private worker node accounting replaces an unobserved central atomic increment.
This deliberately changes deadline sampling from one aggregate 256-node quantum
to a 256-node quantum per worker. Root/controller deadline checks remain. The
development aggregate node limit and statistics path is preserved.

After actual compiler specialization, call `specialize_shipping_operations()`
before pruning and final lexical compaction. It removes only seven allowlisted,
unread shipping diagnostic counters using `search_observe.py`. It then applies
`search_args.py` to non-B candidates: the actual chess-search prototype, definition
and eight-argument calls lose constant exclusion/learning arguments, while the
three-argument scheduler callback remains unchanged. B keeps exclusion and frozen
learning for singular searches. Unresolved conditional input, other policies,
development readers and unfamiliar counter/argument uses are rejected. The default
baseline is independent; compare complete source and native files for each form.

F's shipping controller always stops on a score outside the current lower/upper
interval before updating either bound. Optional diagnostic removal preserves this
control operation and the last completed best move. TT representation and its
coherent publication/read helpers always come from the current canonical source;
an older result using a different TT is not acceptance evidence for a new build.

`test_generate.py` checks reachability safety boundaries. `test_loose.c` executes
four simultaneous workers, complete-result precedence, rejection of an invalid
bound, cancellation, startup/restart and shutdown. They supplement the repository's
actual engine and shipping tests. These source reductions and tests do not establish
a 4,096-byte final submission, playing strength, or target many-core performance.
Complete launcher/ELF size and executable behavior must be measured separately.
