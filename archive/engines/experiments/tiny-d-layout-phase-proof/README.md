# Layout plus phase D: narrow semantic and physical qualification

This proof owns 40 ordinary files, including 31 immutable inputs: the complete
combined experiment's 28 sources, two qualified phase-observer sources and the
independent 64-square chess oracle. The inputs are copied here and pinned before
use. Future mutable sibling folders and historical generated C are not source
inputs. All generated programs, receipts, transcripts and archives stay outside
Git. This proof does not promote a maintained entry or change a shared guard.

## Exact source and measured images

The combined candidate changes only two fragments of the original finite D:
the Board declaration moves its unchanged metadata before its mailbox, and the
existing eight-argument PVS retry phase replaces four textual child calls with
one loop. Board fields retain their names/types, `sizeof(Board)` remains 176,
and all consumers use named fields or typed whole-object copies. There is no
assembly Board offset, new logical board representation, move-order change or rule deletion.
Other board/search surroundings, runtime, startup pool, loader, codec, flags and
fixed WORKERS=2/TT_BITS=18/PLY=128 shipping resources remain unchanged.

| Actual file | Original finite D | Combined candidate | Change |
| --- | ---: | ---: | ---: |
| Scalar native ELF | 8,348 B | 8,124 B | -224 B |
| HQ native ELF | 8,736 B | 8,512 B | -224 B |
| Scalar complete own-ELF | 7,540 B | **7,478 B** | **-62 B** |
| HQ complete own-ELF | 7,800 B | **7,718 B** | **-82 B** |

These are actual combined files, not sums of separate savings. The source-owned
whole producer reproduced both original controls twice before candidates; both
candidate native, payload and complete-file repeats matched. Loader/header
overhead remains 1,115 B and payloads are 6,363/6,603 B. The combined whole receipt
SHA is `4b0b4f62b4266c8e2e60c1d8b969fe28de0ff0970822c380a5d4156bd0716b83`.
The source28 handoff index is
`2bda9d37186d0d171a5a7f3928929082085595b25399ed63382bd271209b639e`.
The prior phase-only 7,501/7,753 B and historical A wrapper +16 B remain separate
results. No compiler, codec, spelling or layout sweep is performed here.

| Form | Native SHA-256 | Complete SHA-256 |
| --- | --- | --- |
| Scalar | `199da6e1e1a94c97fe853e0ff3d89b52e2057a55592052e7fbe5500147e4aeec` | `d4f2ba718c5e9391708c86468416338f78b6134d1f017267c6c34add187381f2` |
| HQ | `3f4269dc5c0d72c0b43bc73c6a11afdab5844836e12e7c31d60dde08c8ae2806` | `3bb8a6a97a27a77508848ab9bd388a4802e07f8d8ff0e37b536176423aa7028f` |

Candidate header SHA is
`e19749eb3315253e04171b89b8188df7e0db6b39ec4eb495187a6e158836823f`;
search is `48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c`.
The exact original header and search remain in `inputs/combined/control/native`.
Both inverse source transformations and all six other native inputs are checked.

## Search and representation contract

`contracts.py` reuses the exact original 20-case observer runtime body. The only
C additions are a normalization comment and compile-time representation guards:
Board 176 B; complete Worker 69,040 B with all field offsets; Entry 24 B with
lock/key/data offsets; game-key storage 32,768 B. Removing those two marked
regions must recover the pinned original observer byte-for-byte.

The real eight-argument search definition is reversibly renamed and the DEV
COUNT expression gains a post-increment observation hook. The wrapper forwards
all original arguments and does not replace depth, window, score, root or search.
Cross-subject Board output consists of named fields and the mailbox, excluding
unnamed padding. Same-process immutability checks still compare a byte snapshot
of the same actual object. Worker, complete TT and complete game-key storage
remain byte-compared, protected by the representation guards.

Four fixed libc test subjects, scalar/HQ times original/combined, use `-O2`,
WORKERS=1, DEV=1, TT_BITS=18, PLY=128 and a fixed clock. Each runs the unchanged
20 cases and node caps. Actual learning, retained/full-key TT rejection,
different ordered contexts for equal board/halfmove, cap 1 and cap 257 retaining
completed depth 2, pre-stop and live/mate PLY boundaries are exercised.

All result rows and 80 trace/state file pairs match exactly. Each subject records
33,534 search calls and returns, 51,807 counter events, 128 reduced probes,
20 full-depth null retries and 47 wide retries. Reduced improvement at or above
beta is observed zero times and remains **dynamically unproven**; exact source
branch reasoning is separate. This is not a shipping/SMP or performance claim.
The once-only command terminates 0 without forced cleanup. Its receipt is
`/home/stemxstudio/rove4k-tiny-d-layout-phase-proof-contracts-20261020-v1/results.json`,
SHA `e06e27d4c8c42e4db819afe3b8ab702a4fe61f0d9636e102efd05a4ea5ab2539`.

## Independent Board contract

`board.py` compiles the exact uninstrumented board/HQ bodies with the original
or reordered header. Its four fixed O2/WORKERS=1/DEV=1 subjects each observe
3,051 nodes across 24 cases. Every applied move belongs to actual gen and passes
actual make. Named fields, all 128 mailbox cells, legal order and both sides'
attacks on all 64 squares are recorded. Raw Board padding is not compared.

The pinned independent 64-square oracle checks legal sets and transitions.
Separate full mathematical recomputation checks signed-white HCE, repetition
keys, legal EP, castling rights, kings, halfmove and ordered reversible context.
The actual `verify_board` is a supplement, not the independent oracle. Fixed
perft depth-2 leaf counts 400, 2,039 and 191 pass. Focused cases include legal,
pinned, horizontal-discovery and absent-capturer EP; both colours' four quiet
and capture promotions; both castles and attacked transit/destination rejection;
rook-capture/missing-rook rights; half99; distinct knight-cycle contexts;
irreversible reset; newly created legal EP; and both-castle histories. Poison
initialization and populated-object reinitialization pass in every case.

All four actual outputs match byte-for-byte: 2,328,125 B each, SHA
`01af03f87824e64b6774c807fe4a1d70b20fda6976147a3216203c33b3cd71d2`.
The once-only command exits 0, with eight successful compile/execute commands,
empty failure/cleanup arrays and no forced cleanup. The receipt is
`/home/stemxstudio/rove4k-tiny-d-layout-phase-board-20261020-v1/results.json`, SHA
`c123692a26644738f31e0d3710161b44a37aaefb40517b5ec6843a88606110bb`.
This remains a Board test profile, separate from actual raw runtime evidence.

## Two explicit physical mapping classes

The scalar native crosses below 8,192 B. The old production admission continues
to reject both new identities. This new proof requires each complete literal
ELF header/PHDR and its own exact mapping class; it does not permit arbitrary
two- or three-page natives.

| Form | Entry | RX | BSS | Upper guard | Reservation |
| --- | --- | --- | --- | --- | --- |
| Scalar | `0x401e4d` | `0x400000`, 2 pages | `0x402000`, 43 pages | `0x42d000` | `0x2f000` |
| HQ | `0x401f7f` | `0x400000`, 3 pages | `0x403000`, 43 pages | `0x42e000` | `0x30000` |

BSS is 175,092 B within 176,128 mapped bytes. The lower guard is `0x3ff000` for
both forms. Root's earlier ELF read is static ancestry evidence; it did not
observe mappings. This proof's subsequent CHECKPOINT and production observations
are the new evidence for the exact two classes.

`audit.py` generates separate CHECKPOINT=1 images from the same payloads,
unchanged loader, codec and flags. Audit scalar is 7,501 B / SHA
`2d509965f30de9151b4e957e8a805b35f716ac7461960497b01c69639d8d815d`;
HQ is 7,741 B / SHA
`3253d027b6132e42e47e963e011dd230384aa96dae5c4b3f3f13a9ec8ea68a1a`.
Those files are 23 B larger than shipping and are not selected sizes. Build-only
receipt SHA is `8ffc4989e946df66392143b000c590468fdcf486fe06e653d139a8c2b8d5a3ff`.

Only after actual search and Board contracts passed did the physical verifier
run once: both forms times quit/EOF, four production sessions, plus one pre-entry
checkpoint per form. Its 15 non-main helper bodies are byte-identical to the
frozen maintained verifier. Main adds exact manifest/provenance pins and replaces
the former common three-page assertion with full literal per-form equality.
All other range, entry, BSS, guard, physical ownership and cleanup checks remain.

Both checkpoints restore the exact native into anonymous RX with zero padding,
zero initial BSS, guards, no WX mapping and a non-executable process stack. They
resume the original entries and exit 0. All four shipping sessions observe the
exact restored RX, three persistent startup TIDs, two guarded non-executable
worker stacks, stdio-only FDs and no children. Each physically observes active
search before quit/EOF, then one closing result and exit 0. Twelve total
bestmoves pass independent legality checks. Output EOF, joined readers and
owned-group absence settle without forced cleanup. `/proc/PID/exe` binds the
whole own-ELF; the anonymous RX hash separately binds the native.

The receipt is
`/home/stemxstudio/rove4k-tiny-d-layout-phase-proof-physical-20261020-v1/results.json`,
SHA `dfcebada0c43fee2dba85893385f261bc398b4c4808a90a6d90055ef1c922add`.
Its failures and interrupted-constructor cleanup arrays are empty.

## Reuse and limits

The finite runtime source stays exactly
`82c62b57e500918827721553d67d9e23073c6cb5ca79dc22cdb8e38ab15f8e63`.
Shipping omits optional identification/options, consumes stop/newgame/infinite,
and uses a 1,000 ms absent-own-clock search budget, **not a hard wall-time cap**.
Next go, position, quit and EOF retain the result-before-completed epoch fence
and kernel-TID joins. Existing finite arithmetic/TT-sentinel proof is reused by
exact body identity (`9d164b571a24181b1c93151e82a0ffe2472d77bb0635849409da7a65caf36756`).
Old DEV executable identities do not describe this new header/search pair.
The original phase/Board proofs and unchanged kernel/decoder fault receipts are
ancestry or unchanged-body evidence only. No old image identity is relabeled.
The old strong shipping stop/newgame/infinite lifecycle is not claimed.

There is no broad fault, sanitizer, game, benchmark, NPS, strength or scaling
campaign. The selected complete files remain 3,382/3,622 B over 4,096 B; this
does not qualify a 4k entry. The exact-image observations do not admit arbitrary
ELFs, decoder inputs, host personalities or all stack behaviours. Root owns
any later maintained promotion, Git stage/commit, shared documentation or CI.
