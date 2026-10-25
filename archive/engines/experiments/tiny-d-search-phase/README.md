# D search retry phase: fixed cost and narrow qualification

This optional experiment freezes the current finite maintained D's 18 ordinary
sources. It changes exactly one source fragment: four textual child-search
calls become the already project-owned `tiny-search/pvs_loop.c.in` expression.
No other search, board, runtime, loader, codec, flag, profile or mapping policy
is optimized. The input copies are independent of future maintained changes.

## Measured cost

The one fixed expression reduces both actual stripped native files by 64 B:

| Measured item | Control | Phase candidate | Difference |
| --- | ---: | ---: | ---: |
| Scalar native | 8,348 B | 8,284 B | -64 B |
| HQ native | 8,736 B | 8,672 B | -64 B |
| Scalar `.text` | 7,825 B | 7,750 B | -75 B |
| HQ `.text` | 8,142 B | 8,067 B | -75 B |
| Map `.text.search`, either form | 2,308 B | 2,233 B | -75 B |
| Scalar complete own-ELF | 7,540 B | **7,501 B** | **-39 B** |
| HQ complete own-ELF | 7,800 B | **7,753 B** | **-47 B** |

Read-only data remains 284/352 B, data 0 B and BSS 175,092 B. Additional alignment
padding absorbs 11 B of the text reduction. The search source shrinks 6,269→6,209 B
(replacement 580→520 B). This is a small D-native saving, below the intended
hundreds-byte target. It does not reverse the historical A wrapper result.

Both literal controls reproduce exactly before candidate compilation. Both
candidate source generations, plain/native/map repeats and all resulting
native bytes reproduce exactly. The candidates keep three RX pages and BSS at
0x403000 over 43 pages; entries become scalar 0x401edc and HQ 0x402019. Current exact
image admission rejects their new hashes without a guard or expectation edit.

Scalar candidate SHA-256 is
`875a8263ab335778fc7be58fda2a9975425a5445ffd7300c80c04f5179e2e841`;
HQ is `4d42ad7e663f826601d01b3f06d778483fc7ba2ec82d80b619967a1fb952061f`.
Candidate search SHA is
`48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c`.
The first-cost report is
`/home/stemxstudio/rove4k-tiny-d-search-phase-20261020-v1/build.json`, SHA-256
`2af7f2aadda128a58f793dc4b4b62e30042195884e9916a3aa357b0372c3a9a1`.
Its single command terminated 0. That original native checkpoint did not run
an engine, loader or codec. Its scope and original booleans remain unchanged;
later whole cost and qualification are separate receipts. No candidate is
promoted by this experiment.

The immutable native-intake snapshot separately preserves the original native
receipt, its exact 24 producer inputs, eight native and linked files, four maps
and compiler logs. Its external index SHA is
`961f36a4909950187542959636fc39bee8db2d42ba2ca6fa602a3aff50fee088`.
The later `cost.py` stage is separately authorized first whole cost only. It
pins those exact native inputs and their two new entries, then calls the
unchanged original `packer.admit` with the explicit new identities and every
old three-page/BSS/guard constant. It reproduces old 7,540/7,800 B whole controls
before packing each candidate twice through the same BCJ/fixed codec and loader
flags. It never rewrites observed whole hashes into old expectations. Both
complete repeats are byte-identical. The unchanged loader overhead is 1,115 B;
scalar payload is 6,386 B and HQ payload 6,638 B. No audit or production execution
belongs to that cost stage. Its report is
`/home/stemxstudio/rove4k-tiny-d-search-phase-whole-20261020-v1/build.json`, SHA-256
`9f632a7e5fc90256044067790a9d62568411607fcf798b4466874df874d1f6d8`.
The separate immutable whole-intake index is
`1891c09ed1919455e24c7596a34a051026fc75d037f94f7f7474939bf237c209`.

Selected complete scalar SHA-256 is
`c18007cc3649df8e0ee8c4488f6967a17d8df0b26a5c88370e4094d9ca3129c0`;
HQ is `04c4cb588b103d6d31a302ab5177c58dd532278b7ab7eb4ef0ac6098603994c6`.
They remain 3,405/3,657 B above 4,096 B. These measurements establish no NPS,
game-strength, scaling or 4k eligibility result.

This is a D raw `-Oz -flto` native reevaluation. The historical TinyA template
passed deterministic search-state parity but its complete source wrapper grew
16 bytes. That adverse source-file result is retained and supplies no D size
saving. No alternate phase spelling or compiler/codec sweep is performed.

First legal moves and QS use one wide call. Other moves begin with a null
window; a reduced score above alpha always gets an unreduced null retry, even
if the reduced score already exceeds beta. A subsequent in-window score gets
the wide retry. PVS/correction counters and reduction eligibility are evaluated
once. The key push precedes all retries; the key pop and existing stopped check
follow them unchanged. No new early-stop shortcut or previous-move conversion
is added. All full-key TT/HCE/PVS/QS/learning and legal transition code remains.

## Actual-core deterministic contract

The exact eight-argument D search definition and DEV `COUNT` expression receive
reversible observation hooks. Reversing the hooks must recover the original
control/candidate source byte-for-byte. The wrapper forwards the same eight
arguments; it does not replace a search, score, window, depth or root result.
Board, header and HQ sources are the frozen ordinary inputs. The existing
TinyA phase proof is reused only for this exact expression and its surrounding
unchanged conditions; it is not relabeled as a new D execution.

`contracts.py` runs four fixed test subjects: scalar/HQ times control/candidate,
`-O2`, `WORKERS=1`, `DEV=1`, `TT_BITS=18`, `PLY=128` and a fixed clock. Each runs
20 cases. The first existing startpos is depth 5 under the same 100,000-node cap;
the other corpus cases and limits remain fixed. There is no depth, score,
position, flag or phase-expression sweep.

Each candidate matched its own control in all rows and 20 trace plus 20 complete
state files. Across both forms that is 80 equal file pairs. Per form the exact
comparison covers 127,870,640 state bytes and 30,432,000 trace bytes. State includes
the complete Worker storage, full coherent TT storage and game-key storage;
traces observe actual arguments, returns, logical Board fields and counter order.
History, continuation and correction learning are exercised. Retained TT,
same-index different full-key rejection, reachable distinct reversible contexts
at equal board hash/halfmove, claim limits 1 and 257, previous completed depth,
pre-stopped entry, live PLY abort and mate-before-PLY adjudication are included.

Every subject recorded 33,534 search calls and returns, 51,807 counter events,
128 reduced probes, 20 reduced-to-full-null retries and 47 null-to-wide retries.
First-wide, QS, late null and unreduced fail-high paths were also observed.
Reduced improvement at or above beta was observed **zero times**. Its dynamic
coverage remains **unproven**; exact branch-expression reasoning is separate.
This is a single-worker DEV observation profile, not shipping/SMP or performance
evidence. No broad game, fault or sanitizer campaign was repeated.

The once-only command terminated 0 with no forced cleanup or cleanup errors:
`/home/stemxstudio/rove4k-tiny-d-search-phase-contracts-20261020-v1/results.json`,
SHA-256 `0ca463758b44fdff261ed89803be0301dc394cc61e19c6516276d095308f8256`.
The reviewed helper hashes are
`contracts.py` = `99c7e95554fe5c688aa355c855f376f31d5f4c7efacb24eafa758cae8555ccd2`
and `contracts.c.in` =
`fc9df8fc4908e26375098b5265ab5182e9bf26fe866e7aeac553e0820464feee`.

## Selected own-ELF physical observation

`audit.py` builds a separate, explicitly pinned CHECKPOINT class using the exact
same payloads and loader source with only `CHECKPOINT=1`. Scalar/HQ audit files
are 7,524/7,776 B, each 23 B larger than shipping. They are not selected shipping
sizes. Its build-only report SHA-256 is
`29818aee07f129faa135fe5bf65ab5bd69507cbfcdc01741dc05c72c9f38d4f1`.

After the actual-core contract passed, the admitted-image verifier ran once:
one pre-entry checkpoint per form and both quit/EOF sessions per selected whole
file. The existing verifier's non-main function/class bodies are byte-identical
to the frozen maintained verifier. New native/whole/audit/entry identities are
literal pins fixed before execution; no original layout guard is weakened.

Both checkpoints restored the exact native into anonymous RX, with zero RX/BSS
padding before entry, lower/upper guards, no writable executable mapping and a
non-executable process stack. They resumed the original entries and exited 0.
All four production sessions observed the exact restored RX, three persistent
startup TIDs, two guarded non-executable worker stacks, stdio-only descriptors
and no children. Three clocked searches per session returned 12 legal bestmoves
in total. An active search was physically observed before each quit/EOF; one
closing result preceded exit 0, stdout/stderr EOF, reader joins and owned-group
absence. Normal success required no forced cleanup.

`/proc/PID/exe` identifies the whole own-ELF; anonymous restored RX identifies the
native. Those two identities are checked separately. The fixed three RX pages,
BSS 175,092 B over 43 pages and both guard extents remain unchanged. The receipt
is `/home/stemxstudio/rove4k-tiny-d-search-phase-physical-20261020-v1/results.json`,
SHA-256 `7e2b98d0712f766858abdfda110a46270b9ad4c7bdaec583808162f75c5c185b`.
It has no failures, interrupted constructors or forced cleanup. This narrow run
does not prove every OS fault, decoder input, host personality, game or runtime
stack condition.

The finite shipping policy is unchanged: no optional id/options; stop/newgame
are consumed; infinite is consumed and absent own clock uses a 1,000 ms search
budget, **not a hard wall-time cap**. Next go, position, quit and EOF keep the
exact completion-epoch fence after output and kernel-TID joins. DEV protocol
semantics remain those of the frozen runtime; this experiment changes search
source, so old DEV executable hashes are ancestry evidence, not new binaries.

Unchanged finite dispatch/TT-sentinel/arithmetic evidence is reused by exact
runtime source `82c62b57e500918827721553d67d9e23073c6cb5ca79dc22cdb8e38ab15f8e63`
(receipt `9d164b571a24181b1c93151e82a0ffe2472d77bb0635849409da7a65caf36756`).
Broader board/HQ, kernel/fault and decoder evidence is reused only for unchanged
bodies and the same mapping contract. The old strong stop/newgame/infinite
shipping lifecycle is not applicable and is not claimed. No shared validator is
changed. The frozen maintained input README retains those provenance boundaries.

`build.py` accepts only a new absolute external `--out`. It freezes these inputs
before importing any local helper, reproduces literal scalar 8348/HQ 8736 controls
first, then compiles one candidate. Each form/control has two independent builds.
The first command uses the original recipe; the second appends only a linker
map output flag, retaining every code/link flag and order including `-s`.
Plain and diagnostic repeated native bytes must match exactly. The map is
partial under LTO and stripping; ELF `.text`, `.rodata` and whole stripped native
sizes are authoritative. No source-function size is invented for absent symbols.

The native producer never runs an engine or invokes loader/codec compilation. It
records actual ELF headers, entry, RX/BSS extents, section costs, source bytes,
hashes and partial maps. The current exact-image admission must reject a changed
candidate. A changed page/mapping class is an explicit parent checkpoint;
neither the three-page guard nor expected hashes are updated automatically.
Scalar starts only 156 B above 8192; HQ starts 544 B above 8192. Native savings cannot
be called complete own-ELF savings without a separately authorized restoration
step. A loss/tie remains a first-cost result and does not start runtime proof.

All generated sources, linked/native files, maps, logs and reports stay outside
Git. The maintained 18, frozen finite 27 and shared files are untouched. The root
MIT license applies to these project-owned ordinary source inputs.

The cost and qualification drivers deliberately bind the exact staged external
receipts; they are experiment evidence tools, not a new maintained entry build
API. Ordinary native/loader inputs are frozen here, and historical receipts
never substitute for candidate source or silently update expectations. The
native and whole first-cost intakes remain immutable even after later README,
contract and physical-proof additions. Root owns any promotion or CI change.
