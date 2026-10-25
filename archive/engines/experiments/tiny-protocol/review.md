# Independent parser contract review

This is a read-only source review and proposed fixture set for the Tiny A / Tiny
D protocol experiment. No fixture in this document has been executed by this
reviewer. It does not establish parser equivalence, binary size, performance, or
runtime correctness. The reviewed baseline files were
`engines/compact/tiny-a/main.c`, `engines/compact/tiny-a/tiny.h`,
`engines/compact/tiny-d/runtime.c`, `engines/compact/tiny-d/tiny.h`, and the Tiny D
`board.c` move-generation / move-application contract.

The experiment owns its span scanner and packed UCI-coordinate decoding. It
must retain generated-move membership before applying a decoded move. Tiny D's
`make` intentionally relies on generation for geometry, side, occupancy,
promotion geometry, and castling origin/transit checks. Passing a syntactically
valid packed move directly to `make` would break that proof.

## Token and number fixtures

The baseline accepts decimal digits only, bounded by `LLONG_MAX`. Invalid or
missing numeric values become zero; a relevant zero clock is still present and
therefore produces a minimum bounded deadline. Duplicate known keys use the
last occurrence. `infinite`, when observed as a key, overrides the clock. Keep
these decisions explicit in the new scanner rather than infer equivalence from
valid-input smoke tests.

Recommended observable fixtures, at a white-to-move start position:

| Input after `go` | Required observation / decision |
| --- | --- |
| `wtime 100 btime 900 winc 2 binc 90` and reordered `binc 90 winc 2 btime 900 wtime 100` | Identical parsed white clock and increment; black fields do not replace them. Repeat at a black root with the sides reversed. |
| `unknown 7 wtime 0 another-token btime 1` | Unknown tokens do not hide the subsequent known zero clock. |
| `wtimeX 500 btimee 500 wtime 0` | Exact key lengths; prefixes cannot match. |
| `wtime 30 wtime 0` | Last known white clock wins and remains present. |
| `wtime 0 winc 9223372036854775807` | Increment clamp precedes multiplication; bounded deadline, no overflow. |
| `wtime 9223372036854775807 winc 9223372036854775807` | Valid maximum values, safe arithmetic, final budget clamp. Inspect parsed arithmetic in a direct harness; do not wait a day in a runtime test. |
| `wtime 9223372036854775808`, `wtime 18446744073709551615`, `wtime 18446744073709551616`, `wtime -1`, `wtime +1`, `wtime 1x`, `wtime 0x10`, `wtime --1` | Invalid numeric token is zero under the baseline policy; it cannot become an unbounded huge clock through wraparound or partial parsing. |
| `wtime`, `wtime btime 40 winc 2`, `winc infinite wtime 0` | Missing numeric-token policy must be recorded. Recommended recovery leaves a following recognized key visible, treating the missing value as zero. The old `strtok_r` loop consumes that key as an invalid value, so recovery is a deliberate parser behavior change. |
| `infinite wtime 0`, `wtime 0 infinite`, `unknown infinite wtime 0` | An observed `infinite` is order-independent and remains stoppable. Missing-value recovery must not accidentally swallow it. |
| no fields / only unknown fields | Baseline has no deadline; an explicit later `stop` must still finish. Do not misclassify this as a clock-bound failure. |

Check arithmetic before any signed conversion. For each digit `d`, rejecting
when `n > (LLONG_MAX-d)/10` admits the maximum without unsigned wraparound. A
span parser must consume or reject an entire numeric token, not a decimal
prefix. If a peeked token is kept for missing-value recovery, every outer-loop
iteration must still advance or exit; recovery cannot create an infinite scan.

No-argument commands also require exact token matching: `quitx`, `stopwatch`,
`isreadyx`, and `ucinewgamex` must have no effect. The old dispatcher ignores
`quit extra` and `stop extra`. Accepting the first token alone would widen that
behavior; record that choice explicitly. Whitespace-only lines and an optional
trailing CR must not produce a command. A scanner may intentionally accept
multiple spaces, tabs, or leading whitespace, but that is broader than the old
top-level dispatcher and should be described as such.

## Move decoding and transactional replay

Decode only tokens of exactly four or five bytes. Check length before reading
four coordinates or a suffix; check each file in `a..h` and rank in `1..8`
before packing. A fifth byte may map only lowercase `n,b,r,q` to promotion
values `2,3,4,5`. Uppercase, king/pawn suffixes, extra trailing bytes, and embedded
control bytes are rejected. Syntactic validity alone never admits a move.

For a candidate packed move, obtain the real generated list, find an exact
full-`Move` match, and call `make` once into a separate child. Return the child
only after `make` succeeds. The replay caller must use that child instead of
calling `make` a second time. A failed `make` may have partially written its
child argument; it must not alias the accepted parent board or global position.

Concrete start-position replay fixtures:

| Replay / alteration | Expected result |
| --- | --- |
| `position startpos moves e2e4 e7e5 g1f3 b8c6` | Commit all four plies and five history keys. |
| `position startpos moves e2e4 e7e5 e1e3` | Reject the whole command; preserve the board, history length, and accepted key prefix that existed before this command, including any earlier non-start root. |
| `position startpos moves e2e4 a7a6 e4e5 d7d5 e5d6` | Accept legal EP through generated membership and resulting king check. |
| Replace that final EP with `e5d6q` or use `e2e5` from the start | Reject the whole command. |
| `position startpos moves e2e4 e7e5 g1f3 b8c6 f1e2 g8f6 e1g1` | Accept legal kingside castling and move the rook. |
| `position startpos moves e1g1`, or append `q` to the valid castle | Reject; a packed coordinate pair cannot bypass rights, occupancy, or promotion checks. |
| `position startpos moves a2a4 h7h5 a4a5 h5h4 a5a6 h4h3 a6b7 h3g2 b7a8X`, separately for each `X` in `n,b,r,q` | Accept every generated underpromotion / queen promotion and capture the rook. |
| Replace that final promotion with `b7a8`, `b7a8p`, `b7a8k`, `b7a8Q`, `b7a8qq` | Reject the whole command, including rollback of all earlier replayed moves. |
| Empty `moves` suffix | Baseline accepts the base position with its one history key; preserve or explicitly change that decision. |
| `position startposition`, `position startpos junk`, duplicated `moves`, non-move trailing tokens | Reject without committing a partial root. |

For a direct parser harness, compare complete meaningful board fields and the
entire accepted `game_keys[0:game_length]`, not only the hash. A bad late move
must not reset `game_length`, install temporary keys, change the reversible TT
context, or leave a partially replayed board. The `HISTORY` boundary is also
transactional: 4095 admitted plies fit with the initial key; the next must reject
the entire new command. Use a repeated legal knight cycle for this fixture.

DEV-only FEN fixtures can supplement production replay for pinned EP, castling
through check, destination check, and king capture. DEV support is a separate
surface; removing a generic helper from shipping D must not silently remove a
helper still used inside its DEV FEN / verification code.

## Line framing and EOF

The baseline buffer holds 32767 input bytes plus its terminator. Any NUL byte or
an additional byte makes the whole physical line invalid, and input continues
to the next LF or EOF. Bad-line tails must never be interpreted as new commands.
Tiny D's 4096-byte syscall buffer must retain unread bytes for later lines.

Use raw-byte fixtures, where escapes below describe bytes rather than literal
backslash characters:

| Bytes written | Expected result |
| --- | --- |
| `b"quit\x00\nisready\n"` | Discard the first line; produce exactly one `readyok` and remain alive. |
| `b"isready\x00quit\nisready\n"` | Discard the entire first line, not merely truncate it at NUL. |
| `b"x"*32768 + b"quit\nisready\n"` | Drain the oversized first line including `quit`; the second line is processed. |
| `b"isready" + b" "*32760 + b"\n"` | Exactly 32767 bytes is a valid physical line; trailing whitespace still permits readiness. |
| Same line with one extra space | Reject as oversized; process a following normal `isready` exactly once. |
| Multiple valid lines in one write; split tokens / CRLF / LF at byte 4095, 4096, 4097 | Byte-chunk boundaries do not change command boundaries or lose a line. |
| Valid final `uci` or `isready` without LF, then close stdin | Execute the final command once and shut down cleanly. |
| NUL-containing or oversized final line without LF, then close stdin | Discard it and shut down; never dispatch a valid-looking prefix. |
| `go wtime 0 btime 0` without LF, then close stdin | Process the final search command, then wait for its completed result and join the fixed workers. |

Retain Tiny D's EINTR retry for read and write. If output now accepts an explicit
span length to eliminate `strlen`, the length must include precisely the
intended payload (no terminator, no stale bytes); partial writes advance both
pointer and remaining length. Promotion output is five coordinate bytes and
ordinary / null output is four.

## Search lifetime and publication

Parsing may be compacted, but search control remains the existing owner path:

1. The old epoch is stopped and fully completed before root / TT reset, replay,
   worker reset, or a new search launch.
2. Root, history, deadline, fallback, and worker initial values are published
   before the new epoch release operation / mutex broadcast.
3. Every worker decrements pending once. The last worker publishes `bestmove`
   before D's completion-epoch release store. The command owner waits with an
   acquire load of that completion epoch. A zero pending count alone does not
   cover result publication.
4. EOF / quit perform completion waiting, then signal shutdown and physically
   join every worker before state reuse or process return.

Proposed lifecycle fixtures should establish active work first, then queue
`stop`, `position startpos moves e2e4`, and a new zero-clock `go`. Require exactly
one completed result per launched epoch, with the new result legal for the black
root and no old result after the owner has crossed a stop / reset barrier.
Repeat with direct `position` and `ucinewgame`, and with active quit / EOF. An idle
`stop` emits no result. `isready` during active work may reply immediately; it is
not a search-completion barrier.

Check the same worker TIDs from startup through the queued epochs, EOF, and
quit. Input parsing must not add a thread, respawn the pool, or weaken D's child
TID / futex physical-join path. None of these runtime claims can be established
by this read-only review alone.

## Review disposition

The main hazards are direct `make` without generation provenance, early global
position / history writes, numeric recovery swallowing a key or failing to
advance, prefix command dispatch, and conflating pending with completed output.
The proposed fixtures target those paths rather than duplicate ordinary valid
UCI smoke tests. The scanner's malformed-input recovery and whitespace behavior
must be reported separately if they intentionally differ from the old parser.

## Final candidate source review

The implemented `transform.py`, `span.c.in`, `position.c.in`, `go-loop.c.in`, and
`unit.c.in` were subsequently reviewed. This pass found no concrete production
correctness defect in those files. It was read-only and started no compiler or
runtime, so the parent's reported validation results remain separate evidence.

The implementation checks token length before coordinate access, checks all
four endpoint components before packing, admits exactly promotion values 2..5,
finds an exact production-generated move, and returns the child of one `make`.
Replay commits the board, history length, and key prefix only after every move
succeeds. Numeric recovery rewinds a nonnumeric value for the outer scanner;
the outer iteration still consumes a token and therefore progresses. Full-token
overflow checks and the original clock-budget expression are retained.

Shipping alone receives the new top-level span dispatcher. DEV retains the old
full-line dispatcher and its optional command tail, while sharing the new go
and replay helpers. D's generic string operations remain available under DEV
for FEN / diagnostic consumers; shipping output computes its required length
without that generic helper layer. Search launch, completion, fixed pool,
shutdown, and bad-line draining are not rewritten by these transformations.

The counted unit explicitly simulates settled epochs without launching workers;
it supports parser, admission-count, rollback, boundary, and budget assertions,
not physical-completion or join claims. Those require the separate full-runtime
evidence. The raw edge harness also correctly distinguishes DEV dispatch from
the shipping scanner and labels cancellation causality as unproven.

One additional malformed-input difference is visible: bare shipping `position`
now enters `wait` and then rejects the empty replay, while the old top-level
dispatcher ignored that line. Invalid `position <arguments>` already waited in
the baseline. Together with the documented whitespace and missing-value
recovery choices, this is a parser behavior change to report if equivalence is
discussed; it is not an identified chess-state or memory-safety defect.
