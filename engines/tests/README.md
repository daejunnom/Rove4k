# Engine process checks

`verify.py` drives actual engine processes. It uses Python's standard library
and an independent, deliberately simple 64-square rules oracle. It imports no
engine source and never treats source text, feature names, or another engine's
agreement as a correctness oracle.

Run Linux programs with Linux Python, including WSL Ubuntu. Build and result
directories belong outside the checkout:

```sh
python3 engines/tests/verify.py \
  --manifest /tmp/rove4k/build/build.json \
  --out /tmp/rove4k/verification

python3 engines/tests/verify.py \
  --engine A-c=/tmp/rove4k/A-c/native \
  --out /tmp/rove4k/A-c-checks
```

The manifest is either a JSON array or an object containing `engines`:

```json
{
  "engines": [
    {
      "id": "A-c",
      "command": ["/tmp/rove4k/A-c/native"],
      "cwd": "/tmp/rove4k/A-c",
      "profile": "dev",
      "workers": 2,
      "max_threads": 2
    }
  ]
}
```

Build manifests may also provide `artifacts`. Successful `native-elf` entries
with `source_form: "original"` or `"compact"` are checked against their actual
on-disk SHA-256. Every distinct executable is run; a compact form with different
bytes gets an additional `ID-compact` engine entry. Only exactly identical
executable bytes reuse an execution, with the reason and hash recorded in
`identical_artifact_reuse`. Equal size, matching source semantics, package hashes
or successful handshake alone do not justify execution reuse.

`command` is an argument array, never shell text. `cwd`, `workers`, and
`max_threads` are optional. `max_threads` is the actual total process-thread
budget, including control threads. Linux `/proc` sampling observes peak threads
but cannot prove an unobserved transient did not occur. Configured worker count
and observed peak count are reported separately.

For build manifests with `configuration.ROVE_WORKERS`, the checker requires the
configured search workers plus one stdin thread to exist **before the first UCI
input**. Their `/proc` task IDs must remain unchanged after searches and during
the active stop/quit/EOF checks. Direct entries can request the same check with
`--startup-threads N`, or a manifest entry can provide `startup_threads`.
This checks a real persistent pool at the declared local size; it is separate
from peak sampling and does not establish scaling or memory use on target 512.
`--startup-timeout 60` allows source-wrapper compilation and fixed pool creation
within a separate startup budget, while retaining the normal response and
search timeouts. A manifest's `expected_program_sha256` pins selected packaging
artifacts before execution.

[target_startup.py](target_startup.py) separately checks larger fixed worker
profiles with explicit available-memory admission and process resource limits.
It verifies startup task counts/identity and physical termination for quit and
EOF without searching. Those startup-only results do not replace the chess
behavior checks here or establish target-hardware scalability.

The default checks cover:

- Minimal UCI handshake, unsupported-command consumption, clocked search
  including an exhausted zero clock, and a
  legal bestmove after a startpos move list.
- Frozen reference perft totals: startpos depths 1–4, Kiwipete, rook/en-passant,
  promotion/castling, underpromotion, and pins. Targeted edge cases compare
  exact legal sets and perft against the independent oracle.
- Position replay versus canonical FEN reconstruction, position hash and eval
  identity, hash discrimination for side/castling/legal EP/placement, simple
  material score ordering, halfmove reset, twofold versus threefold repetition,
  halfmove 99 versus 100, and 50-move root draw scores.
- Fixed depth, node limit, movetime, legal principal variations, mate distance,
  checkmate and stalemate.
- Repeated infinite/stop cycles, queued stop/position/new-go epoch boundaries,
  direct active position and new-game resets, exactly one bestmove, EOF and quit
  during a search, actual process termination, and cleanup of child processes
  observed during that test. Development tests first verify no bestmove was
  published before cancellation. Each cancelled epoch must publish its own one
  legal bestmove before a subsequent root's result is accepted.
- A bounded legal-move selfplay smoke. It supports no Elo or strength claim.

`--profile shipping` applies to direct `--engine` entries. Manifest entries with
`profile: "shipping"`, or `--suite shipping`, run only the public protocol,
lifecycle, selfplay, EOF and quit checks. They do not require FEN, perft, state,
depth/nodes options, resource options or detailed search output. The lifecycle
smoke sends `go infinite` and `stop`; a shipping engine may safely interpret an
unsupported go mode as its default bounded clock policy.

`--suite dev` runs only development diagnostics. `--select ID` filters manifest
entries and may be repeated. `--quick` limits reference perft to depth 3 and
replay checks to 24 plies. `--plies` bounds selfplay (default 12; maximum 128).
`--match A-c,A-rust` adds two games between separate owned processes with colours
exchanged. Both identifiers must be present in the selected manifest. The same
independent oracle validates every played move; this is an opponent smoke, not
a strength comparison or rating estimate.
Every response has a finite timeout; stdout/stderr have a combined 8 MiB bound.
Failures preserve transcripts and terminate the owned process group.

The development interface is:

```text
position fen <six-field FEN> [moves <UCI move> ...]
perft N              -> perft N COUNT
legal                -> legal <UCI move> ...
state                -> JSON {hash, halfmove, eval, draw, ...}
go depth N           -> info depth ... score cp|mate ... pv ...; bestmove ...
go nodes N depth N   -> same, bounded by nodes
go movetime MS       -> same, bounded by time
stats                -> JSON {nodes, workers|search_workers, ...}
```

`state` may start with `state ` before the JSON object. If present, `invariant`
must be true; `fen` and `pawn_hash` are independently checked. The required
`draw` field means a current repetition or 50-move draw, not merely a heuristic
evaluation close to zero. Replaying the same board from FEN resets repetition
history. Completed nonterminal development search output must include a legal
PV; rule-drawn roots may report the exact zero score without a continuation. Terminal
positions return `bestmove 0000`.
Final node counters include aborted work. C's per-node atomic increment permits
at most `workers - 1` nodes of concurrent cancellation overshoot; Rust's node
reservation uses a stricter bound. The node-budget check records both the final
counter and this explicit ceiling, rather than inferring a budget from wall time.

Validate the oracle independently before engine runs with:

```sh
python3 engines/tests/verify.py --oracle-only --oracle-deep \
  --out /tmp/rove4k/oracle
```

The standard perft FEN fixtures also appear in
[Stockfish's official perft tests](https://github.com/official-stockfish/Stockfish/blob/master/tests/perft.sh).
The low-depth totals are frozen fixtures and are recomputed by this oracle;
they are never learned from the candidate engines.

`results.json` records individual pass/fail evidence, binary hashes when a
direct program file is supplied, elapsed times, and transcript paths. A failed
or missing response fails its check; the runner continues with a fresh process
for the next independent check. A process transcript is JSONL with monotonic
times, sent commands, actual stdout/stderr and terminal exit status.

These checks do not by themselves prove SEE/singular state isolation, scalar
versus SIMD equivalence, MTD bounds or PALS compatibility. Those require the
implementations' additional semantic diagnostics. Nor do small local worker
profiles prove 512-hardware-thread scaling, 4 KiB eligibility, artifact
reproducibility, learning quality or competition strength.

## C search semantic contracts

The separate `search_contract.c` exercises the real C search implementation,
compiled without its UCI main. Run its bounded build/test recipe on Linux:

```sh
python3 engines/tests/run_search_contract.py \
  --out /tmp/rove4k/search-contract --variants BCF --workers 1
```

The runner records exact source hashes, compiler arguments, executable hashes,
exit statuses and stdout/stderr. It fails a frozen-source claim if inputs change
during the run. Every compile has a 60-second bound; every test has a 45-second
bound. `--workers` permits 1–8 for local checks.

- **B:** exact legal-exchange values for pins, legal versus protected king
  recaptures, EP, promotions, underpromotions and optional recapture; rejection
  of initially illegal pin/EP moves; incomplete cancellation. A real completed
  depth-3 search produces the TT entry qualifying a depth-6 singular search.
  Excluded low/full-window searches with frozen learning must preserve the
  ordinary root TT entry, history, continuation, correction, killers, board and
  path depth. Ordinary learning positive controls first prove that the selected
  positions/windows actually qualify for each relevant update. A second
  unique-capture position proves the singular extension is taken: excluded
  alternatives fail below its threshold and the real depth-6 search completes
  the selected child at depth 6 instead of the ordinary depth 5.
- **C:** 400 actual AVX2 evaluations equal a scalar score recomputed from board
  contents during deterministic legal walks. The production SIMD counter must
  advance. Execution requires an AVX2-capable CPU.
- **F:** actual MTD root iterations on three separated king/pawn positions agree
  with a plain independent full minimax oracle, and the returned legal move
  attains that value. The oracle has no TT, ordering, PVS or pruning; it checks
  its quiet-frontier precondition explicitly. Actual convergence counters and
  conflict counters are checked, repeated searches retain TT data across
  horizon changes, explicitly requested shallow depths 1 and 2 still equal
  their own minimax values after a deeper search, and a 100-node cancellation preserves the last completed
  score and attaining move.

These semantic fixtures add evidence for those specific contracts. They do not
replace the subprocess protocol/rules checks or prove the other algorithm and
parallel-policy requirements.
