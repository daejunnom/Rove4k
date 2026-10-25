# Shipping preconditions on the qualified minimal Tiny A

This optional experiment narrows one internal API to the engine's actual
shipping ingress: legal startpos histories whose moves belong to `gen(p)`.
It changes only two conditional guards in the exact qualified 5,223-byte
minimal-UCI control. It does not provide a general unchecked Board API.
DEV retains both original guards, FEN admission and its original behavior.
The generated DEV source and native executable are byte-identical to the
qualified control. No external engine source is used; the repository MIT
license applies.

The complete file is **5,207 bytes**, **16 bytes smaller** than its exact
control, and **1,111 bytes above 4,096**. It is not a size-eligible submission.
There is no playing-strength, throughput, scaling or other-platform claim.

## Exact change and retained boundaries

`transform.py` accepts only readable control SHA-256
`38d6c829a4d98a172b01c945a20e091bd529a5998174896dbf0ad2dbc01a0a7b`.
It wraps exactly these existing lines in `#if DEV` / `#endif`:

```c
if(abs(target)==6)return 0;
if(*n>=MOVES)abort();
```

The first belongs to `make`; the second belongs to `add`. There are no other
engine changes. Own-king postmove safety, legal EP normalization, castling
origin/current/transit/rights/empty-path tests, all four promotions, FIDE
repetition and halfmove state, HCE, ordered reversible TT context, full-key
coherent TT, all search learning, deadline checks and the persistent pool are
unchanged. Parser `!m`, history-capacity and transactional commit checks,
input-length/NUL guards, numeric checks, result publication and all physical
wait/join fences remain unchanged.

The exact control already omitted duplicate endpoint, own-piece,
friendly-target, promotion-geometry, EP-victim and castle-rook checks from
`make` under its generated-move contract. Those absent checks are not part
of this experiment's savings. The public parser remains checked.

## Whole shipping call graph

Line numbers below refer to the exact frozen readable control, not generated
compact C. An independent read-only reviewer challenged this whole call graph
and its preconditions before compilation.

| Producer or consumer | Control lines | Authority |
| --- | --- | --- |
| Search generation | 323 | Local `moves` comes from `gen(p)` |
| Search draw/PLY terminal scan | 329 | Applies local list members only |
| Search ordered child transition | 355 | Applies a permutation of that list |
| TT payload and ordering | 335–349 | A TT move can affect ordering/cutoff; it is never passed directly to `make` |
| Legal fallback | 430 | Generates a list and makes its members |
| Text parser | 432–433 | Compares complete text with generated members, then calls `make` |
| Position replay | 469 | Requires nonzero parser result and history capacity, then remakes it on the same unchanged board |
| Public ingress/commit | 462–471 | Shipping admits only startpos; commits root and history after the entire private replay succeeds |
| `add` callers | 179, 180, 191, 198, 199 | Pawn push/double push, geometric move, two castles; attack mode never calls `add` |

`perft`, FEN, legal-list and board-verification commands are DEV-only. Worker
search roots are immutable between publication and completion because the
next `go`/`position`, quit and EOF wait for pending workers before reuse.
No raw TT, arbitrary coordinate or FEN path bypasses generation in shipping.
Adding such a path would require reviewing this specialization again.

## Why a king target cannot occur

Every reachable shipping parent satisfies:

```text
the side to move does not attack the opponent king
```

It holds at startpos. After a successful move, the retained own-king test
ensures that the previous mover's king is not attacked by the next side;
after the side flip, that is the same invariant at the next parent.

For an ordinary generated move, including a promotion capture, targeting an
occupied enemy king would be an attack detected by the same shared walker.
This contradicts the parent invariant. Pawn pushes and castles require an
empty destination. The normalized EP target is empty. Thus no reachable
generated move can remove the opponent king, so both kings survive the
transition and the induction remains closed. The final own-king test is
essential to this argument and remains present.

DEV FEN admission has a broader contract. For example,
`4k3/8/8/8/8/8/4R3/4K3 w - - 0 1` admits the pseudo move `e2e8`, even though
this parent cannot follow a legal shipping history. DEV keeps the explicit
king-capture rejection for this case. An arbitrary `make(p,m)` call outside
the generated legal-history contract is not supported by this specialization.

## Actual generator capacity theorem

Startpos has 16 pieces of each color including exactly one king. Ordinary
moves preserve piece counts; captures and EP reduce the opponent count;
promotions replace a pawn. Castling rights originate at startpos and are
cleared when the original king/rook moves or a rook home is captured.
Consequently an admitted castle relocates an existing rook and cannot create
one. These facts preserve at most 16 pieces per color and exactly one king.

| Piece | Maximum entries emitted by the actual walker |
| --- | ---: |
| Queen | 27 |
| Rook | 14 |
| Bishop | 13 |
| Knight | 8 |
| Pawn | 12 |
| King | 8 ordinary + 2 castles = 10 |

A promotion-rank pawn has at most three destinations and emits exactly four
promotion choices for each: at most 12 entries. A nonpromotion pawn has at
most a single push, double push and two diagonals: at most four. EP occupies
one of the same diagonal entries. Rays/deltas do not duplicate destinations;
castles have different destinations from one-step king moves. Therefore:

```text
count <= 10 + 15 * 27 = 415 < MOVES = 512
```

Attack-mode recursion emits no moves. The shipping `add` capacity check is
unreachable under this closed contract. DEV keeps its original check. The
experiment does not resize arrays or change `MOVES`.

## Fixed costs and identities

The producer admits the exact qualified v4 manifest and freezes every recipe
input before use. It retains the same selected identifier mapping, manual
function spellings, resource substitutions, compiler invocation
`cc -Os -x c - -o x -s`, source-literal encoding, shell prefix, compiler/signal/
fd-exec cleanup bootstrap, and XZ LZMA2 preset9 extreme `lc=2,lp=0,pb=0`
CRC64 settings. No compiler, spelling, encoding or compression sweep occurs.
The source argument is the only replacement inside the existing bootstrap.

| Actual form | Exact control | Specialized | Difference |
| --- | ---: | ---: | ---: |
| Compact shipping C | 11,192 B | 11,148 B | -44 B |
| Stripped native ELF | 22,664 B | 22,664 B | 0 B; program bytes differ |
| Complete source launcher | 5,223 B | 5,207 B | **-16 B** |

Source generation, native compilation and complete packaging were each
performed twice per form and required identical bytes. The control also
reproduced every previously qualified source/native/whole/DEV hash. Actual
executable-bootstrap source restoration was decoded and checked exactly.

| Identity | Control SHA-256 | Specialized SHA-256 |
| --- | --- | --- |
| Readable source | `38d6c829a4d98a172b01c945a20e091bd529a5998174896dbf0ad2dbc01a0a7b` | `321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d` |
| Compact source | `b70dce2bd28834f6218b72e255ee5689028ab187be91bf2df661c6c48af55092` | `5e0e77321110371aec3a7a06f93290e7581f08f721fc9bb07fcef26c406429b7` |
| Native ELF | `60797c218437055bdc56a46e9ff37d9007ba39e547bccccfa36d8f5acb9cb430` | `d39167146236aafde21b59439b853bd10561f04e9186c18b839c2f84f2e16e12` |
| Complete launcher | `fbb416160e98beb8f10cc5fec6b3792f4591055626344dcbe31cb50ffce41ee9` | `085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36` |

Both DEV sources have SHA-256
`8a0985aad0b1514aa78a6aafc59c0fc1cc511d1b06a441bab91a404cdd98a477`;
both DEV executables have SHA-256
`dad84ccaa35f6c9d7860b1bd39d283f8bdb7d5a1c74ec6c25615e443376974ce`.
WSL Ubuntu uses GCC 13.3.0, binutils 2.42, Python 3.12.3 and xz 5.4.5;
the build receipt records complete tool version strings.

## Qualification and reproduction

`verify.py` pins and freezes the unchanged minimal-policy verifier, raw
process helper and independent chess oracle. Both experiment forms have the
same minimal finite-UCI policy, so the helper receives its minimal-policy id
inside distinct output directories; each receipt also records the original
experiment identity. This does not weaken or relabel the separate strong-stop
validator. The physical gate passed all eight native/complete-launcher runs
across both forms and active quit/EOF. Startup and post-fence observations
verified the actual native image SHA, exactly three persistent TIDs, only
stdio, no helper children and empty working/temporary directories. Bare and
`infinite` defaults, white/black clocks, ignored commands, next-go and position
fences, exactly one outstanding shutdown result and physical process absence
passed. Fifteen fixed-clock candidate dispatch cases separately passed; their
modeled completions are not physical-worker evidence. Independent oracle
self-checks also passed. Deadline observations are bounded liveness checks,
not strict real-time or performance guarantees.

The measured build is
`/home/stemxstudio/rove4k-tiny-preconditions-20261020-v1/build.json`, SHA-256
`59f2b8b30ca17d8e084474f1dff8b7effb1e177ebaa2fb3f9f69e09b6c27a9d1`.
The physical receipt is
`/home/stemxstudio/rove4k-tiny-preconditions-runtime-20261020-v3/results.json`,
SHA-256 `4dd216571cdbed88bc74965938d02a29cb33f0eb58257a690f4829b8f3b643fd`.
Earlier successful runtime receipts remain immutable. Independent review
found that its aggregate alarm could interrupt the reused instrumentation
executor without collecting its owned subprocess. The experiment verifier
now registers every directly launched new-session process while the alarm is
blocked, restores the original child mask, and performs TERM, bounded wait,
then KILL/join in its outer `finally`. The v3 physical run repeated all eight
checks and settled all 24 directly registered groups. A
separate intentional alarm during a compiler wrapper also terminated its
sleeping grandchild; both PIDs became physically absent. This failure fixture
is preserved at
`/home/stemxstudio/rove4k-tiny-preconditions-cleanup-fixture-20261020-v2/receipt.json`,
SHA-256 `9a633ccb7c23ebe22fed8f87b6449bba9658c4d2b7fa88b53069023664273ef0`.
That fixture also verifies that the child inherited its prior signal mask.
This is evidence for directly registered and actually observed groups, not a
claim of arbitrary cancellation coverage for every nested restoration phase.

`transitions.py` and its test-only `transitions.c.in` include exact frozen
shipping source with `DEV=0` and rename only its entry point. Original
`set_position`, `gen`, `make`, `search`, `think`, structures and callbacks
remain untouched. An independent 64-square Python oracle checks complete
legal sets and separately recomputes HCE, legal EP, FIDE hash, castling,
side, halfmove, the full game-key prefix and reversible path context.

Eight sequential forms passed: control/specialized, O2/O2+ASAN+UBSAN and
PLY128/4. Each PLY128 form checked 559 snapshots, 325 endpoint legal-child
transitions, 55 invalid-input transactional rollbacks and six actual fixed-depth
searches. Histories include both colors' EP, both castle directions for both
colors, every promotion choice for both colors, rook-right removal, repetition
and two deterministic 64-ply legal games. Every accepted state originates from
startpos; FEN injection is tested only as a rejected shipping transaction.
All observation hashes matched between control and specialization for each
compiler/PLY pair. Gen-entry and all-child tests checked endpoint/ownership,
friendly target, absent king target, promotion, EP victim, castling rights and
rook preconditions, piece counts and the 415 bound. Maximum observed pseudo
count was 50; the mathematical bound comes from the proof above, not that
empirical maximum.

O2 perft4 returned 197281 with 206603 legal transitions; ASAN/UBSAN perft3
returned 8902 with 9322 legal transitions. The PLY4 matrix separately called
real search and `think`, restoring history and preserving the completed
depth1 score54/`g1f3` witness when deeper search aborted. Search score, best
move, nodes, heuristic digest and root/history preservation matched exactly.
These instrumented function checks are distinct from the measured executable
and complete-file physical gate. The transition receipt is
`/home/stemxstudio/rove4k-tiny-preconditions-transitions-20261020-v1/results.json`,
SHA-256 `0b9d4bb9725c2ba2b7dbc6255f8aa3c19535246259f0d2692c881e00cbb0458c`.

The original control and every generated source, binary, recipe and report
remain outside Git. Only readable experiment producers/tests and this scope
document belong in the checkout.

```sh
python3 -B engines/experiments/tiny-preconditions/build.py \
  --control /home/stemxstudio/rove4k-tiny-uci-min-20261020-v4 \
  --out /home/stemxstudio/rove4k-tiny-preconditions-new
python3 -B engines/experiments/tiny-preconditions/verify.py \
  --build /home/stemxstudio/rove4k-tiny-preconditions-new/build.json \
  --out /home/stemxstudio/rove4k-tiny-preconditions-new-runtime
python3 -B engines/experiments/tiny-preconditions/transitions.py \
  --control /home/stemxstudio/rove4k-tiny-preconditions-new/control/combined.c \
  --candidate /home/stemxstudio/rove4k-tiny-preconditions-new/specialized/combined.c \
  --candidate-sha 321ab861fe8e8ebc1791cbd389edbecc53091ede195e172e9983f2455ee12c6d \
  --manifest /home/stemxstudio/rove4k-tiny-preconditions-new/build.json \
  --out /home/stemxstudio/rove4k-tiny-preconditions-new-transitions
```
