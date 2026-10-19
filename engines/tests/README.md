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

`command` is an argument array, never shell text. `cwd`, `workers`, and
`max_threads` are optional. `max_threads` is the actual total process-thread
budget, including control threads. Linux `/proc` sampling observes peak threads
but cannot prove an unobserved transient did not occur. Configured worker count
and observed peak count are reported separately.

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
  exactly one bestmove, EOF and quit during a search, actual process termination,
  and cleanup of child processes observed during that test.
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
