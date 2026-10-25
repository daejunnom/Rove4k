# A–F engine implementation checkpoints

The full implementation scope is recorded in [the accepted plan](ENGINE-PLAN.ko.md).
The current user request includes the complete C A–F implementation, AWS evaluation
preparation and E19 data/trainer/export preparation. Production optimizer steps remain
zero and the initial model weights remain unchanged; trained strength is not claimed.

## Current execution scope, 2026-10-25

The user resumed the complete accepted plan. The current contract, dependency
graph and critical-path estimate are in ENGINE-PLAN.ko.md. General4K is mandatory
for C A–F; ELF is optional for every family and deferred above4096B. Submission
W256/256GiB-TT-cap is distinct from TEST P4/P28. Source/state encapsulation,
64-bit resource consumers, real parallel TT initialization, the evaluator/AWS
campaign and real E19 preparation to production optimizer step0 are in scope.
Earlier pause/exclusion statements below retain their original historical date.
New source, size, startup, resource and runtime evidence is required; the old391
receipts and experimental4088/5505 results are not new-profile acceptance.

### Source integration checkpoint, 2026-10-25 12:20 UTC

New family-specific producers derive fresh C from the admitted own source closures,
with W4/W28/W256 and 64-bit TT consumers. ABCEF uses24-byte entries (192GiB at
the provisional cap), D uses16-byte entries (256GiB). Actual scaled initialization
fixtures cover disjoint parallel clear, poisoned storage, selectors and the
before-UCI barrier; D also exercises256 actual workers and pending257 at small TT.
These fixtures do not prove full-size startup or many-core performance.

| Family | TEST-P4 whole | Provisional submission whole | Current evidence boundary |
|---|---:|---:|---|
| A | 3834B | 3836B | source-JIT functional/rules pass; target-host pending |
| B `tcec-final-lf` | 4089B | 4087B | explicit selected variant, full semantics and actual JIT/rules pass |
| C | 3982B | 3981B | incremental SIMD source retained, functional/rules pass |
| D `prefix` | 5429B packed; 7812B JIT | 5425B packed | functional/rules pass; general4K blocked_size |
| E | 3926B | 3928B | canonical E19 binding and actual consumer retained |
| F | 3644B | 3645B | full MTD/witness/learner preserved, functional/rules pass |

The selected P4 cohort has24 naturally settled engine groups,144 GO and134
legal results. D's JIT alternative and B's actual W28/384MiB supplemental run
also pass their functional scopes. Those runs used one physical core with SMT:
zero entries are promoted to scored TEST or final TCEC qualification. Actual
shipping move generators independently match plain/UBSan legal sets for105
positions and2858 moves per family, including N/B/R/Q, castling and en passant.

All five newly measured optional ELF files are above4096B (A11402, B13957,
C11710, E11687, F11026) and deferred_size. D's optional ELF target remains
separate from its mandatory general entry. No feature-reduced result replaces full F.

E19's13 source inputs match the final step0 record. Real Jan/Feb2013 data yields
48313 retained games and741882 positions after eligibility, split, duplicate and
holdout checks. Integer weights retain SHA-256
`a5bb11099b62489aca43a011619e15076b0637b2f2e460d89772162965cd5424`.
The21 focused tests and actual C/UBSan consumer checks pass without a production
optimizer update. This is preparation and inference evidence, not trained strength.

The evaluator/AWS branch passes145 focused tests, actual patched Fastchess
barrier/deadline/fault fixtures and two peers' local four-physical-core P4 checks.
Peer sources and binaries remain outside Git. Local peer checks explicitly lack
the scored-host controller reserve and NUMA/many-core acceptance. c4ke P28 is4098B
and excluded; no configurable-native fallback is admitted.

AWS project name Rove4k and ACTIVE state were read through the account API;
the named CLI profile is rove4k, workload region ap-southeast-2. CLI2.38.5,
uv0.13.5, the Toolkit catalog and the Codex MCP profile/STS smoke are verified.
The project is FREE with100USD remaining credits. No workload resources or paid
campaign were created. PAID, fresh Advisor<5%, quota/capacity, target AMI and actual
S3/watchdog/NUMA validation remain launch gates. The public Advisor object observed
onOct25 was last modifiedMar20 and is not accepted as fresh interruption evidence.

GCC11.4 compatibility remains a distinct pending gate: the first external Jammy
SDK audit found an absolute interpreter symlink escaping to the Noble host. The
strict checker rejected it; a separately audited SDK revision is being prepared.
The old7b95599 engine/NVCompact/repository CI runs passed. The new foundation CI
registers the production, E19 and evaluator unit suites; new-profile generation,
actual target runtime and final release qualification are separate follow-up jobs.
All receipts, raw games, data, failures and generated files remain outside Git.

## Previous user scope: all engine Rust retired and work paused, 2026-10-25

The user first discontinued Rust A, then explicitly discontinued every engine
Rust path and requested a pause. Active coverage is C A–F, six implementations.
Generic Rust B–F, independent Rust D, Rust-specific packaging and comparisons
are retired too. Historical sources/receipts and shared C tools are preserved;
NVCompact's internal Rust tool is a separate scope. Earlier twelve-core
checkpoints retain their historical scope and are not relabelled as C-only.
New experiments, compilers and games stopped; existing owned work was settled.

The latest accepted C checkpoint391fad6 reproduces full A/B/C/E/F2/F8 at
3731/4092/3873/3817/3530/3548 B and passes exact-head CI with the declared
runtime contract. Current commands and evidence are in the
[next TCEC entry guide](../engines/experiments/tcec-next/README.md) and
[wrapper implementation record](WRAPPER-IMPLEMENTATION.ko.md).
This does not close D's mandatory4096-byte self-restoring ELF requirement,
the remaining algorithm/parallel-policy evidence or final recommendations.
The current work audits those plan requirements while extending B's small
margin and reducing D without discarding their unique full features.

At pause, selected B is still4092 B. The qualified4088-byte expression candidate
is unintegrated: no new selected-source regeneration/JIT or recipe promotion
was performed. D5505 B is a separately reproduced/runtime-checked experiment,
not the maintained5527-byte selection and still1409 B above4096. C native
packaging measured7244 B versus selected source3873, so source remains selected.
C scalar/SIMD timing is prepared but unexecuted. The E five-policy C/Rust
preparation completed before retirement; its10 programs/20 startup checks are
historical. No new benchmark or26-game study was launched.

## Wrapper handoff implementation: 2026-10-24

The user approved the complete external wrapper handoff in stages. Its scope,
corrected premises, measured alternatives and current acceptance are recorded
in [the wrapper implementation record](WRAPPER-IMPLEMENTATION.ko.md). The
attachment remains reference material; repository contracts and the user's
request govern implementation. This continues the full A–F objective.

The first shared checkpoint cd79ffd reduces Rust D scalar/HQ whole files to
11026/11384 B through exact body232 restoration, preserving native/load bytes,
absolute BCJ, initialized data8, BSS4 and memory geometry. Both forms reproduce
twice and the existing positive campaign passes eight sessions/64 legal GO.
The common API, consumer wiring and separate shell/native policies continue
in that linked record. Historical checkpoints below retain their original
source and execution scopes; they are not automatically new-policy evidence.

## Further common and family source reductions: 2026-10-24

The W1/W2 rollout below remains a separate accepted checkpoint. A further
terminal compiler_seek stage removes only the explicit f.flush();10 B from
the builtin regular BufferedRandom write/seek preparation. Python3.12 seek
flushes the pending write before rewind and publication. A write failure can
now surface at seek; arbitrary filelikes, custom open/flush hooks, exact
tracebacks/syscalls or cancellation timing are outside that contract.
The original compiler_stdin25300/ee9ba2c9 remains unchanged. New helper8813 B
has SHA2568ca5fd736f010cd9dd1e3b668065c0cf7d82f9e98653580b8f9b4c23e7d75a41.
It restores and replays the caller's exact frozen owner, deletes one AST
flush expression with UTF8 byte offsets, and checks both gaps, opaque source
spelling, declared AST change and complete byte/AST inverse. Five focused
tests include real pending-write flush/rewind and seek-EFBIG before the next
boundary. They do not qualify arbitrary error/close/exception observations.

Each of A/B/C/E/F8 has its own candidate encode and strict Python inverse,
reusing its exact173 control bytes and original strict-restoration receipt.
The seek-only complete costs are4807/5281/4944/4897/4604, saving3/4/4/4/3 B;
the raw10-byte saving is not a prediction of compressed savings. The finite
five-cost index10957 B has SHA256
96e36fede04328eaa2af9402e18fb454a80d34c82e126ba74c4e23acdc7079d6.
Old source/literal/owner/W1/W2 bootstrap guards execute before the new stage.
No original helper pins, source/native/DEV, codec or fixed resources change
for A/B/C/E. Their expected changes are exactly whole/bootstrap bytes/hash.
Each ordinary --dev reproduces shipping2/oldDEV2; each unchanged selected
verifier passes quit/EOF2, eight legal GO, three TIDs, exact restored native,
private-child cleanup, readers and physical exit0. A/B FD enumeration stays
unobserved; C/E observe stdio0/1/2. Actual run lanes A0-1/E2-3/BC4-5 are
bounded, all original owners settle before reap, forced0/owned0. Optional A
root-policy and DEV generation bypass the terminal source change.

Scalar D separately removes an unread Worker score field/reset/completion
store and unused search-return binding. Scalar sources save42 B in four
roles; search calls/scores, TT, learners, full promotions and publication
remain. HQ/DEV source mappings bypass the projection. Actual Clang18 layout
observes best12->8 while nodes16, later fields and sizeof68976/align8 stay
equal, so no RAM gain is claimed. Native7324->7292/text6815->6808 plus the
25-byte alignment-gap disappearance yield packet4471->4458 and complete
5540->5527. Only the exact new native/layout/model/restored-image class is
registered; old classes and generic mapping/owner/observer bodies remain.
The actual audit5550/8e560ac0 is statically admitted, then ordinary reproduces
scalar/HQ native2/whole2 and audit1 each. Default positive passes preentry2,
quit/EOF4 and12 legal GO, exact RX/initial BSS/padding/guards/NX/stdio,
persistent three TIDs, readers and physical settlement. Normal index5670 B
SHA25659119e313b063bb7f740f3ad9902196109b8f79c4e4153a0d98339de4a9aa94b.
The original audit driver NameError/exit1/completefalse is preserved; its
actual completed tools/static companion and later normal success are
separate evidence. No new DEV, fresh, fault or game campaign is inferred.

Full F reuses the existing Q only in the quiet nonpromotion cutoff learner
update. Successful make leaves the same piece at the child destination,
including castling; recursive qr does not mutate that Board. Quiet ordering,
which can include promotions, is unchanged. Source7840->7830 changes native
bytes18576/e92b39->18576/3aaaacf7. Old/new actual compact qr ASan/UBSan runs
compare36 cases, typed state3807540 B and successful-make trace247248 B
byte-exact, covering quiet pieces, four castles, depth3, captures, quiet/capture
NBRQ promotions and preset stop. Correction update, async cancel and SMP are
not covered by that fixture. Quiet-only4593 and seek-only4591 combine to an
actual4590, not their summed saving. Full ordinary shipping2/oldDEV2 and
unchanged selected quit/EOF2/eight GO pass. Actual prior DEV files and the
8538-byte pre-name source compare byte-equal. Production source4 is frozen;
new full references do not change the two reduced policies' actual tuples.
The old7840 literal and9786 owner guard execute before changing only the
opaque source expression, exact new-owner replay, frozen stdin and seek.
F followup index8829 B SHA256
f5e4cd5afb20dfa477c090611b5d8bc0042fd1a2e2e88a5215be9aa28be9d3f8.

F8 quiet+seek firstcost is4602, two bytes smaller than seek-only4604. It
retains full8/TT18, source7868 and native18576/8c98349f. Its new declared
producer composition first inverses F2 quiet7830 to exact old7840, consumes
the unchanged six-role resource transform, admits old F87878, then applies
the same quiet source reduction. New classv11/base-after-quiet is explicit
in builder/validator; the original six-role helper stays byte-identical.
Ordinary reproduces source/native/bootstrap/whole/payload2 and strict restore2,
then a separate positive passes quit/EOF2, eight legal GO, nine TIDs, all-eight
worker CPU activity, native/FD/children/maps/NX, readers and physical exit0.
All other local lanes are closed before this eight-CPU qualification. Both
actual reports consume the same79-source closure, new F producer and D
verify18faa69a. Build48542 B SHA256
0e24b4a1ce3c398b9e7d1a479084336679ff74a6c1242a5bcc9902fccc97f78d;
runtime74771 B SHA256
679153416875c4d056805d2873460dbb771c2db3a265b0664171514c1165e17a.
Producing source5 stays frozen. The old173 F8 receipt retains its own closure.

| Full maintained path | Before this followup | Locally reproduced and run | Gain | Over4096 |
|---|---:|---:|---:|---:|
| A loose2 | 4810 | 4807 | 3 | 711 |
| B2 | 5285 | 5281 | 4 | 1185 |
| C2 | 4948 | 4944 | 4 | 848 |
| D scalar | 5540 | 5527 | 13 | 1431 |
| E2 | 4901 | 4897 | 4 | 801 |
| F full2 | 4595 | 4590 | 5 | 494 |
| F full8 | 4607 | 4602 | 5 | 506 |

All producing family files remain unchanged after their normal runs;
completion records live here and in external receipts rather than rewriting
their producing-time pending annotations. No features, model/TT/learner,
promotion choice or fixed worker/memory profile is removed. All full paths
still exceed4096. This followup's current-head CI, comparable strength and
target-resource/tournament admission remain separate work.

## W1/W2 rollout to A/B/C/E/F8: 2026-10-24

Each existing complete file is reproduced with its own current codec/header
before one W1/W2 candidate is encoded. Control5/candidate5, strict Python5
and CLI5 pass. The fixed current compiler_stdin helper ee9ba2c9 is unchanged.
The candidate source bytes and literal spelling are exact, and complete
byte/AST inverses restore each original compiler owner.

| Default full path | Previous whole | Maintained local whole | Gain | Bootstrap |
|---|---:|---:|---:|---:|
| A loose, two workers | 4854 | 4810 | 44 | 10185 |
| B, two workers | 5337 | 5285 | 52 | 11669 |
| C, two workers | 4995 | 4948 | 47 | 10827 |
| E, two workers | 4946 | 4901 | 45 | 10376 |
| F full, eight workers | 4652 | 4607 | 45 | 9714 |

Each bootstrap saves120 raw bytes. No resource/profile, engine source,
native, DEV, TT, model, learners, search or N/B/R/Q promotion is removed.
Old source/literal/owner and late BOOT guards execute first. A applies only
to default loose, retaining the three optional root-policy bypasses. Each
recipe explicitly freezes the common helper and records its own predecessor
and measured tuple. Savings are independent observations, not sums.

One ordinary --dev per A/B/C/E reproduces shipping twice and old DEV twice.
Each unchanged selected verifier passes quit/EOF, eight legal GO, stable
three TIDs, exact deleted native/private-child checks, readers and physical
exit0. A/B do not enumerate live FDs; C/E observe stdio0/1/2. F8 separately
reproduces twice and passes two positive sessions/eight legal GO, nine TIDs,
positive CPU deltas for all eight workers, FD/children/native/maps and
physical settlement. Runtime lanes are bounded, with the F8 positive alone;
no game, NPS/Elo or target-hardware scaling conclusion is inferred.

Production recipe/README bytes remain frozen after these runs. Their earlier
pending wording is a producing-time record; completion is recorded here and
in external receipts. All original command leaders settle before reap, with
forced/owned0. The finite-cost index45092 B has SHA256
2a35e93aa0bd3382a42ee7bb9147c1c88165be46113ec267936c1be3a232cb89.
F8's successful local build/runtime consume the original D verify461f685a.
A subsequent independent D source WIP changes that shared file in the
working copy: this does not rewrite the successful receipt, and that D WIP
is excluded from the wrapper checkpoint's Git tree. Its later integration
requires an explicit F8 helper-pin refresh and fresh verification.

The fresh archive collectors also include recipe.local_input_sha256 keys,
not only the historical fixed LOCAL list. This repairs omitted late local
generators instead of duplicating them into the shared-helper catalog.
Identical paths with several input roles are archived once. A's actual
fresh run makes two independent Git archive checkouts, each shipping2/DEV2,
including its previously omitted dead-score helper and compiler_stdin with
exact bytes. Both checkouts reproduce4810. Fresh22040 B has SHA256
03fc9fdad02eb2d9a567848c2f1871c6a7eebca68f18d61d64ad795351501ad0.
That extra archive execution is A-only; other updated collectors retain
source-review scope. The wrapper checkpoint173c2c65/tree04363c7e is then
qualified by engine40086797011 (C/Rust), NV40086797012 (Node22/24), and
repository40086797045 (Node22/24), all success. Tested merge77770149 has the
same tree. The actual C ZIP1077333 B/API digest/CRC and ten selected
A/B/C/E/F8 build/runtime JSONs pass, binding Git173 inputs47/50/48/50 and
F8 closure74, old guards, ee9 W1/W2/full inverse, both shipping/DEV attempts
and actual runtime. F8 uses Git173 D verify461f, not mutable D WIP. The
final index184564 B SHA256 is
e519e5b2b4d436ccc7dc9b520856892406121202ee9ee1e7bf429707d2686588.
Original engine/NV/data handles finish0, restart0/owned0. Generic catalog
291 paths has10 changed pins, separately from unchanged generic producers;
default/reduced F ordinary68 and snapshot3 stay exact. New fresh execution,
new root-policy JSON intake and unchanged whole-closure claims are not added.

Parallel additional costs remain separate: seek-implied flush F4595→4591,
quiet nonpromotion continuation-index reuse F4595→4593 with a changed
native, and scalar D dead-score projection5540→5527. Their regular-file,
source/static or first-cost evidence is not current maintained integration,
complete loader admission or actual-search equivalence. All full paths
still exceed4096 and the full A–F objective remains unfinished.

## Wrapper and NVCompact design review: 2026-10-24

The external Korean wrapper/NVCompact design document is reference material,
not repository instructions. Its SHA256 is
b36154eb6d24ef93e20c86e1e617339eff460b53499f6044b975d5d1464e5876.
Its b459 baseline is checked against current e339: the common C compiler owner,
F source/codec and NVCompact candidate logic discussed here remain unchanged.
Full N/B/R/Q promotion stays the default; no search-policy reduction is made.

W1 prepares the complete source in a private buffered regular file before
spawn, then gives it to compiler FD0 with the existing stdin argv. One fixed
control reproduces4640 B exactly; one candidate measures4596 B, GAIN44, with
bootstrap9786→9702. Source7840/native18576, header73 and codec remain fixed.
Strict restoration and the declared transport AST/full inverse pass. FD0
seekability, private c-path observation and the masked preparation interval
are explicit changed observations: pending cancellation can still arrive
after publication. This first cost has compiler/engine/runtime/integration0.

W2 separately shares wait predicates and per-entry deadlines. Its control,
candidate and two-call clock combination measure4640/4634/4636 B. Source
inverse and strict restoration pass; runtime/integration are0. Existing
four-call clock4633 remains smaller than W2 alone. Costs are not summed, and
the W1/W2 combination is a separate comparison. All finite inputs/candidates,
tools and failed or unselected costs remain outside Git.

NVCompact adds independent declaration/reference candidates for shadowed
same-spelling locals and parameters. The previous whole-spelling batch and
the complete legacy name→literal candidate prefix retain budget priority;
new independent alternatives follow them. Fresh whole-function destinations,
composition conflict checks, typed AST/binding, native and diagnostics gates
remain. Reference lookup is indexed once per function. This is not general
scope reuse, simultaneous swap, advisor mutation or domain-based rewriting.
The first focused csource run uses actual Clang18 and passes12 tests,
including three new binding/budget regressions. The separate existing
source-search integration run passes10 tests for whole-file/native/diagnostics
and replay boundaries. Both original managed handles terminate0 without
restart. No whole-file engine saving is attributed to this extension.

## Full F prepared stdin and shared wait, local adoption: 2026-10-24

The independently encoded W1+W2 combination measures4595 B, GAIN45 from
4640; its bootstrap is9666 B. Strict restoration and the composed W2→W1
inverse recover the exact old owner. The maintained pure compiler_stdin
helper reconstructs that owner before applying declared transport/wait
stages; it has no filesystem/environment/process operations. Stream and ZIP
stdin receive W1, while restored-files explicitly skips W1. W2 is a separate
stage with its own spans/gaps and per-call deadline. This is a declared
transport contract, not general Python or arbitrary-compiler equivalence.

The full F producer freezes this helper and applies it only after the exact
old9786/0cf100be bootstrap guard. Its current source7840/native18576 and DEV
remain unchanged. Optional policies bypass the new stage. F8 updates only
the producing F builder's provenance pin; its actual separate source,
packaging and4652 B expectations are unchanged. No F2 saving is attributed
to F8 or other families without measuring their actual files.

One fresh ordinary --dev reproduces shipping twice and old DEV twice, then
its frozen selected verifier passes quit/EOF with eight legal GO, readers
and physical exit0. Supplementary metadata observes both original child
PIDs/start ticks: the initial UCI pipe inode matches the verifier's writable
end and remains FD0 after native exec; FD set is0/1/2, private c/x/parent and
all TID children are absent. No pipe content, signal, stop or extra wait is
introduced by this observer. These samples do not prove every intermediate
FD event. Both outer commands settle naturally before original-leader reap,
pre-reap extras empty, forced/owned0. The final current-input build317081 B
has SHA256
df79156221a701eccc905986b7e8bc5ace5f69c7c50cff07823c0a248c6f722e;
runtime83367 B has SHA256
229239b97ea2e9f6c4b72c6deadd21c93a6568897787d8a93f53595c125df704.

The frozen maintained helper also reproduces the exact measured F bootstrap
without compiling. Six focused tests pass, including pre-spawn open/write/
flush/seek fault subcases with compiler0, original exception, closed source
FD, removed private directory and unchanged parent FD0. Existing stream5,
ZIP4 and restored-files5 suites pass with their actual owner→terminal
callback substituted, not merely the old callback. They cover fixture
source bytes, codecs, argv/environment/stdin/FD exec, normal compiler failure,
missing compiler and cooperative SIGTERM/group cleanup. Five original outer
commands terminate0 with retained leaders, no extra/adopted children before
reap, no forced cleanup and owned0. The original8810 session ends0 without
restart. Rust lexical checks pass but their optional rustc compilation is
not run because rustc is absent from that fixed fixture PATH. The actual
packaging report8536 B has SHA256
ae668829f2977784bc98ac5185d6c2cd852524efc9f21f90fbf1797886559390.
That fixture run consumes helper d50b6f59. Cached diff-check then finds two
extra EOF newlines, removed without changing any AST node or location. The
complete AST including locations matches; these fixture results retain that
explicit reuse scope. The final helper25300/ee9ba2c9 and its updated recipe
pin receive a new ordinary/selected pair under original149321 (terminal0),
not rewritten manifests or a restart of the successful earlier run. The old
d50b6f59 normal/index remain preserved separately. Current source/native,
whole and observed stdin/FD/physical-exit results remain unchanged.

The preceding NVCompact source commit83ff21c passes automatic engine
CI40081848402, repository40081848372 and NVCompact40081848393. Its merge
tree28555a15755e2ae635beb7d96d438f402182441f matches that head. NV uses
Ubuntu24.04/Node22+24/Rust1.99.1, workspace core tests, native build, local
tarball and actual offline installed-bundle checks; no publication occurs.
Tool-dependent CI assertions may early-return without frontend availability,
so explicit local Clang12/source-search10 evidence stays separate. The
external CI index12076 B has SHA256
8fe987a2f52b02c5a13069f087d634fbc544ba1ceed7236ebd309938d901c09a.
This precedes the new wrapper commit and does not qualify its source tree.
Current full F is still499 B above4096. Further families, optional policy
costs, forced TERM/KILL/125 and cancellation-boundary campaigns retain their
separate scope; no strength or final tournament acceptance is inferred.

## A unused score and E sole-GO boundary: 2026-10-24

Default full A loose removes its unused published Worker score, reset/store
and unused think return binding. Four exact spans, five protected gaps and
the full inverse retain the search call/arguments, internal scores, TT,
learners, completed best/depth and pool ownership. The source is restored
through the previous literal guards and compiler owner before the final
literal replacement. Canonical/DEV and all three root policies bypass this
stage. Worker size68976/align8 remain; best offset12 becomes8, with following
arrays unchanged. This is not a RAM reduction. Source8355→8335, fresh native
18576 B differs, bootstrap10325→10305 and whole4863→4854 B save9 B.

Full E moves the byte-identical407 B sole-GO body into a nested block at its
only call site. Two exact spans, three protected gaps and the full inverse
retain token/clock parsing, drain/deadline/stop, mutex, pending2 publication,
broadcast order, model, TT, learners and search. Packaging restores the old
source through the previous dead-score and literal guards, compiler owner
and dead-score bootstrap stage before replacing only the final literal.
Source8549→8526, bootstrap10519→10496 and whole4953→4946 B save7 B. The newly
compiled18576 B native is byte-identical to the qualified previous E image.

Both existing ordinary --dev builds reproduce shipping twice and exact old
DEV twice. Each unchanged selected verifier passes quit/EOF, eight legal
GO, three startup TIDs, exact deleted-native restoration, private-path and
compiler-child absence, readers and physical exit0. E observes stdio-only
live FDs; A's selected verifier does not enumerate live FDs. Original leaders
settle before reap; forced cleanup/remaining owned handles are0. Producing
recipes are separate from later normal-result annotations. These are local
qualifications; exact9f134646 CI qualification is recorded below. A remains758 B and E850 B
above4096. No speed, strength or hardware scaling gain is inferred.

The preceding bbc999b177c77babde5e172139694baa85e7f3e9 automatic engine
CI40053782461 and repository CI40053782364 both succeeded. The tested merge
tree equals head tree4abe5149e8fd25909505b9015a83d459da0ffedc. Actual C ZIP
digest/CRC, B/C/E build/runtime JSON, complete late source/bootstrap chains,
Git-frozen producing inputs, shipping reproduction and unchanged DEV pass.
Unchanged A root/F/F8/D detailed proofs retain their earlier scope through
actual consumed-source comparison. Generic C/Rust local-dev process checks
pass; their expanded provenance catalog is not a changed runtime producer,
and no new generic native-byte equality is claimed. The external final CI
index25360 B has SHA256
6dc2dcafbdf151307df67213d88a1b6599a2ff9df3458c77036aefcc7ae45c38.

Exact9f134646379c1b60c0419a86ab8a7c6f6a6fae34 engine CI40055663531
and repository CI40055663533 succeed for C/Rust and Node22/24. Tested merge
04adac3bc51967054288a1dd18bc750badcba23a has the head tree
baf6388186ff3c1347cc4124e1c7852f2ce5547d. Actual C ZIP API digest/CRC and ten
A/E/A-root build/runtime JSON pass. A/E source/bootstrap chains, two shipping
attempts, exact old DEV and current Git-frozen inputs match recipes. A root
hint/NORMAL/PALS are fresh reports with their new input catalogs, not reused
old closures: complete files5528/5510/7135 and selected quit/EOF pass while
the default-only transform is bypassed. B/C/F/F8/D retain their earlier
detailed scope through actual consumed-source comparison. Generic catalog
286→288 metadata changes are distinct from unchanged actual native producers;
new generic native-byte equality is not asserted. Original watch/intake
handles terminate0 without restart; remaining owned handles are0. The final
index35096 B has SHA256
464cbf65899d01910c0a4fee73be36dbc3a0581d10a6687da06721762a991a6c.

## Additional finite costs, not maintained entries: 2026-10-24

The C D9-bit sentinel reservoir keeps the actual packet4471/native7324 B
and the same production loader argv, but one loader link measures whole
5540→5541, text893→894: LOSS1, unadopted. C-width Python shadow fixtures
and source/inverse checks preserve bit/cursor/refill/output data, including
actual body restoration; they are not execution of the generated C decoder.
Native compile/encode/engine/normal/HQ/CI are0. Its final index2207 B has
SHA256875b8057d7e4076e7b52fbb572faeb57f4c138283216a69045d5fd1a79584382.

A separate scalar target-centered attack query retains geometric attacks
and the old ordered generation by two exact source spans and three gaps.
The actual source grows476 B, native7324→7452 and text6815→6949. One native
link/encode/loader link makes packet4471→4555 and whole5540→5624: LOSS84,
unadopted. Loader/header1069 B remains. DATA/BCJ/body restoration matches
the exact new native; behavior fixture/engine/normal/HQ/CI remain0. This
does not establish the source candidate's behavioral correctness by run.
The reservoir candidate is not combined. Current D stays5540/6037 B.

Rust D removes only shipping Result.score/nodes declarations and completed
initialization through cfg attributes in two exact spans. Worker.nodes,
all search scores, TT, learners, stop/deadline and best/depth publication
remain. One scalar link/codec/loader link measures text13257→13193 and
whole11108→11080, GAIN28; native16816 B remains the same length. Actual Child
stride56→40 and two-child allocation request112→80 differ, but both fit one
page and no RSS gain is inferred. Think is inlined; standalone return ABI
is unobserved. HQ/normal/engine/CI and maintained integration are0 at this
first-cost checkpoint. The separate native admission record contains unused
old whole/HQ metadata and is not a release recipe. The final index13773 B
has SHA256663457cea72afa7800b9a863610218b84f1f88aa3d1e5cb3f0b9132170b32ba2.

The corrected common owner has four time.monotonic calls across wait and
group-drain scopes. Binding c=time.monotonic once and replacing just those
four callable references retains the original timestamps, time.sleep,
WNOWAIT/mask/publication/settlement and failure125 flow. Five exact spans,
six protected gaps, AST binding and complete byte/AST inverse preserve the
entire embedded C literal. One actual F2 encode with its unchanged73 B
header/codec measures bootstrap9786→9751 and whole4640→4633, GAIN7. Strict
Python EOF/unused0 and CLI inverse pass. Other profiles, integration, compile,
engine, normal and CI are0; this is not the maintained F size. Original
handles terminate0, forced/owned0. The final index5704 B has SHA256
43b82a65497b282f26e6c7615a45b19553e2e0de26fc7ef894847adf3ca13eb9.

The pure terminal prototype is also measured on five actual default inputs:
A4854→4853, B5337→5329, C4995→4992, E4946→4945 and F84652→4648 B. Each
bootstrap saves35 raw bytes. Current encoder controls reproduce all five
predecessor payloads/whole files byte-exact before candidate encoding. This
adds five control encodes to the original finite plan because old reports
did not freeze historical executable/_lzma/liblzma SHA identities. Current
tool pins/version strings are recorded; historical binary identity remains
unproven. Candidate strict Python EOF/unused0 and CLI inverses pass. Actual
F prototype bytes equal its already measured9751/8241893b candidate with
new F encodes0. Total new control/candidate encodes10; native/compile/engine,
normal/common-API integration/CI are0. All original12 child commands settle
before leader reap, forced/owned0. These remain first costs, not maintained
sizes. The final index27401 B has SHA256
75e049ef2fb5b83f1b322ddb993bf42f74410aa44a08c7c7db528d36e0c9453c.

## Rust D Result projection, maintained local qualification: 2026-10-24

The shipping generator appends the two reviewed Result cfg spans to its
original17 edits, preserving canonical7 and every previous inverse/gap guard.
Both literal scalar/HQ tuples are discovered separately: whole11108→11080
and11476→11440 save28/36 B, text decreases64 B each and native remains16816 B.
The packaging/codec/loader and nonshipping Rust sources are unchanged. No
gain is inferred from standalone ABI, RSS, throughput or playing strength.

The host builder's former communicate/poll→reap→killpg flow is separately
repaired with regular-file output, retained original WNOWAIT identity,
mask/spawn/publication/unmask under finally, pre-reap empty-group settlement,
final output cap and SIGCHLD restoration only after owned handles settle.
This development-tool repair does not contribute to the engine file gain.
One actual ordinary build reproduces native/whole twice per form, adds one
unstripped static audit per form and passes all gates. All23 actual tools
exit0 with pre-reap extras empty, forced0/reaped/group absent/owned0.
The preceding CLI PATH preflight failure occurs before output creation or
compiler execution; it remains preserved. The corrected command explicitly
selects the same measured Rust compiler through the existing --rustc option.

The unchanged positive verifier passes eight sessions and64 legal GO across
scalar/HQ native/whole and quit/EOF. Actual three TIDs, two guarded stacks,
restored data8/five-page image, stdio, readers, replacement fence and physical
termination pass. Negative/fault/ptrace campaigns are not run, and positive
admission is not full loader/rules qualification. All four maintained source
files are byte-identical to the ordinary/runtime producing snapshots; later
result annotations are in this checkpoint. Build470838 B has SHA256
7d49f8d93a8fbbea76c417aaf1a53b11538a3bc8fc54ca2fc3ef73fb49f87c06;
runtime217031 B has SHA256
c2977282bfb66d59a38461a898e9bad933a4e4c291de46d2d6d0b4bfd5bbc9c7.
The subsequent exactb459c8158a511ef2d092562eb4f0fc30ad63a22e automatic
engine CI40057648188 and repository CI40057648190 succeed for C/Rust and
Node22/24. Tested merge05179a49ddbef435ca84cd8b4fcb49149fc8a457 has the
head tree48d0ceb6d3cf107c2b5bfa40b87cc3f1045f8216. The actual Rust ZIP's
API SHA256 and full CRC pass. New shipping build/source-proof/runtime JSON
bind18 Git-frozen inputs,19 spans/26 gaps/full inverse, two attempts per
form,23 owned tools and eight sessions/64 legal GO/16 mapping observations.
Runtime admission/all-loader booleans remain false. C maintained closures
and canonical Rust D actual producers retain earlier scope through Git-byte
comparison; generic catalog288 stays the same size with two Python pin
changes, separate from unchanged actual generic producers. No new C ZIP or
generic executable-byte equality is asserted. Original watch/intake close0,
restart/remaining handles0. The final index45779 B has SHA256
709305d87715cc4e0d652b3a380d19d007da9de5a4c9e1f374fdcf93999f67b4.
This proof uses b459 Git bytes and excludes subsequent waiter-source WIP.

## Rust D response waiter ownership repair: 2026-10-24

The shipping Queue.until previously delegated to the legacy response waiter,
whose Popen.poll could reap the original leader before Owned recorded it.
The existing cleanup then refused the missing WNOWAIT identity before its
destructive group signal. The observed defect is interrupted ownership and
cleanup/error reporting; a post-reap destructive signal is not claimed.
The replacement observes exit with waitid(WNOWAIT), retaining the existing
queue/prefix/pump/timeout ordering and leaving reap to the original owner.

The focused regression uses the actual Queue, Reader, Owned and Budget with
two small external fixtures. Missing readyok after natural exit17 preserves
the expected AssertionError and original leader until cleanup. A queued
readyok after natural exit0 also preserves that leader until finish/cleanup.
Both readers join and groups disappear without force or remaining handles.
The first error path intentionally records settled_before_cleanup=false.
The test is a separate validation input, not a new production dependency;
the engine workflow runs it before the existing shipping build and verifier.

A fresh ordinary build and positive verifier consume the changed verifier
and identical actual production source sets. All23 tools settle before reap,
with return0, no pre-reap extra members, forced0 and owned0; scalar/HQ native,
load and whole files reproduce twice and remain11080/11440 B. Eight fresh
sessions pass64 GO/64 legal results, observed mappings/stacks/stdio, joined
readers and natural physical exit. Both original managed sessions terminate0
without restart. The focused and ordinary/runtime receipts are preserved
separately. Build471367 B has SHA256
06ee90e0cedaab70a30ce1b1999ddafc4e341bb4fe297dc4e0766c7aa505d19e;
runtime216745 B has SHA256
c060baf46afaf512917572f5925e6dbd704272ffe434700cd749dab6676325ee.
The combined local index32142 B has SHA256
693bdd7221796d5eff7f34bca565fbee07133fe598d4389513d80239974f7b96.
This is local qualification; the next exact-head CI is pending. Runtime
admission/all-loader booleans remain false and no engine size gain is
attributed to this validator repair.

## Full F2/F8 paired resource games: 2026-10-24

The actual maintained full C files4640/4652 B play four fixed openings with
colors exchanged, eight games at5000ms+25ms. Both inherit the same CPUs0–7
on WSL's eight exposed logical CPUs/four core IDs; the observer sharesCPU0.
One GO is active at a time, with fresh two-player pools per game. Timestamp
and complete-newline publication share a lock before log I/O; queued results
accepted by expiry remain valid after consumer delay. Cumulative clocks,
independent legality, terminal-before-cap and late-result accounting are
checked. The240 searched-ply cap is an unfinished*, not a draw.

Seven games finish by mate: F8 wins6, F2 wins1. The eighth reaches240 plies
unfinished; draw/flag/protocol/physical failures are0. Actual1180 searched
and36 opening plies replay with the pinned referee. All16 source entries
complete their internal startup compilation outside the game clock, restore
the expected natives, keep3/9 TIDs and affinity, and terminate naturally with
both reader EOFs. Original unreaped leaders retain identity through empty
pre-reap groups; forced cleanup/owned handles are0. Input pins before/after
and post-replay match. The one original managed session99680 ends0 in107.986s.

Per-turn /proc brackets total F2 CPU96.74s for clocked48.941s(1.977CPUs),
F8 CPU384.09s for49.070s(7.827CPUs). Observed max VmRSS is8126464/8912896 B,
VmSize25935872/76509184 B. These are sampled native-process resources, not
compiler peak, simultaneous memory peak, per-position speed, NPS or stack
high-water proof. Eight games do not establish Elo, final profile choice or
target512-core scaling. Both full files still exceed4096. The final
index42412 B has SHA256
029b40a4bcc555f5977595003a8fc77bf638ac92c09fcf433032a60f2c0d891c.

## B completed-depth job token: 2026-10-24

The full B shipping source represents job publication/claim with its signed
completed depth: -1 published/unclaimed,0 claimed without a completed depth,
1..126 completed. GO drains the old job before publishing both -1 values
under the existing mutex; each stable owner claims0 there before think.
The pending2/null-worker startup, result-before-notify, shutdown and actual
created-thread joins remain. An early proposal mistakenly described a
separate qn ready counter; the actual final source already had no qn, and
its pending startup was preserved. This is a closed state-protocol change;
private direct-think callers must seed depth0. It is not a general lexical
or arbitrary-entry equivalence. Six exact roles/seven protected gaps retain
singular/PVS/exclusion/SEE, TT, learners and evaluation source bytes.

The regenerated complete file is5337 B,5 B below actual corrected-owner5342;
source9759→9744 and bootstrap11804→11789. Fresh native26080 B differs from
the previous26112 B image. One ordinary --dev build reproduces shipping
twice and exact old DEV twice; the unchanged selected verifier passes
quit/EOF, eight legal GO, three startup TIDs, selected deleted-native,
private paths/readers and physical exit. Original leaders settle before
reap with forced0/owned0. Internal claim instrumentation, per-worker CPU
activity and partial-create fault injection were not performed; unchanged
failure-path bytes and source ownership arguments have that limited scope.
No speed, strength, RAM or target-hardware scaling improvement is inferred.

## C/E unused shipping score state: 2026-10-24

Two independent late transforms remove only the unconsumed Worker score,
its reset/completed store and the unused return binding in think. Actual
shipping result/pool consumers read completed depth and best move; canonical
DEV still consumes score and bypasses these stages. Search calls/arguments,
local scores, TT/learners, C signed-net SIMD and E's21 physical coefficients
and five ordering features remain byte-identical outside four exact spans.
Each transform retains five protected gaps and a complete inverse. Package
generation restores the old source through all previous literal guards and
the compiler owner, then substitutes only the final source literal.

On the same repaired owner/codec/header, actual complete C5002→4995 B and
E4963→4953 B save7 and10 B. Actual fresh native identities change in both
families; C remains22672 B and E becomes18576 B. Typed current-ABI probes
show Worker68976 B/align8 unchanged and best-move offset12→8, with following
64-bit/array offsets unchanged. These are file/layout observations, not RAM,
search-speed or strength improvements. Both existing ordinary --dev builds
reproduce shipping twice and retain exact old DEV twice. Each unchanged
selected verifier passes quit/EOF, eight legal GO, three startup TIDs,
native/stdio/private-path/readers and physical termination. Original owned
groups settle before reap; forced cleanup and remaining owned handles are0.
Producing recipes are preserved separately from later result annotations.
The subsequent bbc999b CI qualification is recorded above; that exact tree
does not include the later A/E boundary changes.

## Shared compiler-group ownership repair: 2026-10-24

The source package producers share one late compiler-owner transformation
after their existing source/argv/literal guards and before encoding. It
admits the project's stdin stream, stdin ZIP and restored-files shapes by
exact reconstruction, preserves their source/command/env/FD/exitstatus, and
retains the original leader with WNOWAIT until live members of that process
group have settled. Manual unbuffered stdin feed handles partial writes and
BrokenPipe; the outer finally covers publication and unmask. SIGCHLD is
normalized during compilation and restored before FD exec. Failed settlement
returns125 with the private workspace preserved. The readable-/proc Linux
profile and live-member scope do not establish detached-descendant or
zombie-inclusive group absence.

All current source consumers receive the frozen helper explicitly, including
A's three optional root policies, F's two reduced policies, generic C/Rust
source packers and F8. Native-only launchers and D's own-ELF do not run a
compiler. Historical comparison producers use explicit frozen copies of
Rove's previous packers; their old outputs and known ownership limitation
remain historical controls. No external engine source is copied into Git.

This correctness repair has a real size cost. Exact source/native/codec
inputs give measured whole A4863, B5342, C5002, E4963 and full F4640 B;
A hint/NORMAL/PALS are5528/5510/7135 and reduced F4697/4425 B. Every envelope
passes strict Python/CLI restoration. Existing packaging suites pass all
14 tests across the three compiler shapes. Current F ordinary --dev and
unchanged selected verification reproduce shipping/DEV and pass quit/EOF,
eight legal GO, native/FD/private-path/readers and physical exit. The exact
`306959720ec2ba432af584a4dc7a6cc3118f7667` automatic engine CI40051718880
and repository CI40051718946 succeeded. The tested merge tree equals head
tree6a8675685a9be2a6569d04c4d715ee7381728214. Actual C/Rust artifact ZIP
digests and CRC checks pass; the ten common-owner profiles' frozen inputs
match exact Git blobs, reproduce their recorded tuples and pass runtime.
F8's separate positive receipt confirms eight worker CPU observations and
physical settlement. Generic C/Rust A–F process checks also pass within
their local-dev worker1/TT16 scope. D's25 unchanged source inputs retain
the previous e8ccae48 detailed CI scope. This checkpoint does not qualify
the subsequent B/C/E source changes above. The external CI index39410 B has
SHA25699bc7d843df30af5bf0d59729d0c385d57ad580d055ac129c024fbe80b62d14d.

On the same repaired wrapper, the old7885 B F source costs4654 B and the new
7840 B source costs4640 B: a separately measured14 B compression gain.
The previous-owner source changes4275→4260 are recorded below in their own
context. Five declared repaired-wrapper codecs are compared once each;
current preset6/BT2/16KiB/lc2/nice24 costs4654 B, three BT4 variants cost
4655/4655/4658 and BZip2 costs4918 including its decoder prefix. No global
codec optimum or measured startup/strength benefit is inferred.

F8 v10 consumes the actual7840 B full source and the same six resource roles
with their new source order. Its7878 B C retains raw+38, new18576/79681f35
native,9834 B repaired-owner bootstrap and4652 B whole. The old4284 B tuple
uses the previous owner and is not a compression baseline for the repaired
envelope; the actual complete-file change is+368 B and556 B above4096.
Ordinary independently reproduces twice, and unchanged substantive positive
assertions pass quit/EOF, eight legal GO, nine TIDs/all-eight CPU activity,
stdio-only FD/no children, native/maps/NX/no-WX/main stack, readers and
physical exit. Its actual D helper is461f685a; oldf5ed runtime receipts and
the old v9 producing recipe remain historical. No F2 gain is added to F8.
Original ordinary/positive handles settle before reap with forced0/owned0.
The external local final index7732 B has SHA256
`49abfb5b87ed90d92c9326ffd859f0c283f16c7c9eb0ab859b7c668cd7aa9f6d`.

## D scalar TT in loader-owned zero BSS: 2026-10-24

A scalar-only late transform replaces the fixed4 MiB TT pointer/allocation
with an uninitialized Entry[1<<18] array. The three exact source fragments
retain a full inverse and all unaffected bytes; canonical native inputs,
HQ/DEV, full64-key/payload CAS, search, learners, worker stacks and joins
remain. Scalar gets a separate generated-source directory so HQ keeps its
previous actual native and package. The readable-source delta is-46 B.

Actual scalar native7388 becomes7324 B, text6874 becomes6815 B and entry is
0x401b35. Its new exact PHDR class has RX400000/7324 B, zero-file RW402000
with memsz0x42ac04 and rounded BSS0x42b000(1067 pages), plus NX stack.
Lower/upper guards are3ff000/82d000 and reservation is42f000. The packer and
independent verifier bind that complete identity/layout; no accepted BSS
range is widened. The unchanged H28 codec/shared-refill loader makes packet
4512 become4471 B and whole5581 become5540 B, gain41 including all1069 B
loader/header overhead. Strict DATA restoration reconstructs the exact
new native and zero232 image. A separately discovered exact5563 B audit
loader is admitted before execution.

Ordinary reproduces scalar5540 and unchanged HQ6037. Existing positive
verification scoped to scalar completes the production and pre-entry
checks, including the larger zero BSS and strict guards. This is the new
scalar layout's runtime evidence; old TT-mmap fault evidence is not reused.
The shared Owned/function interval consumed by F8 stays byte-identical.

Allocation timing intentionally changes: the larger BSS reservation exists
while the512 MiB decoder context is alive, increasing transient virtual
reservation by about4 MiB. This is not a measured RSS increase. Reserve,
context allocation or final BSS protection can now fail before native entry
through bad126 instead of the old TT mmap's native status2. The direct native
ELF has its separate kernel mapping-failure behavior. Capacity remains
262144 aligned16 B entries. Whole5540 still exceeds4096 by1444 B; neither
this checkpoint nor unchanged HQ constitutes a completed4K submission.

Commit e8ccae48 passes [C/Rust engine CI40049947759](https://github.com/daejunnom/Rove4k/actions/runs/40049947759)
and [Node22/24 repository CI40049947566](https://github.com/daejunnom/Rove4k/actions/runs/40049947566).
The actual merge f20534ce and head share tree52f17d48. API ZIP size/digest,
two selected D build/runtime members and actual producer/verifier blobs
match. Both scalar/HQ reproduce and pass two pre-entry checks, four quit/EOF
sessions and twelve legal GO results with natural physical settlement.
The external CI final index7430 B has SHA256
`ea34eaf9041ad69ed2a385aaad8a555fc7ad4aa0871c1c731a62cf0916b8a8e0`.

## Full F local MTD state and sole GO body: 2026-10-24

The completed MTD score seed and attaining witness stay local to one worker
job instead of storing/reloading an otherwise unread Worker score field.
The public completed-depth/best stores keep their original boundaries; stop,
conflict and incomplete convergence leave the last completed result intact.
Four fixed edits shrink7885 to7863 B. A second transform moves the sole
399 B GO function body unchanged into a nested block at its sole exact-go
call, removing only the definition/call. Clock-key ordering, numeric checks,
drain, deadline and pool publication remain. Two edits shrink7863 to7840 B.
Both transforms retain protected complements and complete inverses, then
consume the real FROM and earlier literal guards before forward emission.

The first change makes a different18576/e92b39f0 native and reduces whole4275
to4264 B. Existing actual-source MTD fixtures, minimally adapted for typed
logical state rather than Worker padding or the deleted field, pass old/new
fatal-UBSan runs. Completed score/best/depth, nodes, paths, all three learners
and the logical full TT match, including pre-stop, expired deadline,
last-completed cancellation and restart cases. The second change preserves
that entire native and reduces whole4264 to4260 B, a separate measured gain4.

Ordinary --dev1 reproduces shipping twice and old DEV twice; unchanged
selected1 passes quit/EOF, eight legal GO, three TIDs, restored native,
private-path removal, readers and physical exit. Two optional ordinary
builds retain their4319/4045 selected tuples and consume the new7840 full
reference. The original managed cohort41433 finishes rc0 with failures[]
and owned0. No additional SAN, game or performance campaign is run.

These4260 B measurements use the previous compiler-owner wrapper. They are
not the final cost of the separate common compiler-group repair, and its
cost must not be hidden by carrying this tuple into the repaired wrapper.
F8 needs its own source/profile and package measurements. Source-only
c4ke reference comparisons remain external; no foreign source is adopted.

## C late object-constant inlining: 2026-10-24

The compact C cross stage reintroduces PLY/MOVES/HISTORY/MATE definitions
after the earlier common constant pass. A final fixed transform removes only
these four definitions and expands24 code uses to the same unsuffixed integer
tokens128/512/4096/30000. Its28 roles/29 protected gaps/full inverse retain
all other directives, literals, function macros and code. Source9075 becomes
8992 B, bootstrap10036 becomes9953 B and whole4666 becomes4628 B, gain38 and
532 B above4096. Actual full-header CPP340501 tokens match (raw whitespace
differs), and the22672/5c447040 native remains entire-byte equal.

The producer restores8992 to9075, then consumes the real pool/cross/common
source and bootstrap guards before applying this final representation.
Canonical/DEV, eight-lane HCE/SIMD128, PVS/QS/TT/learners/pool, workers2/TT18,
compiler/AVX2 target/codec/header remain. Ordinary --dev1 reproduces shipping
twice exactly against first-cost and old DEV twice. Unchanged selected1
passes quit/EOF, eight legal GO, three TIDs, the actual native/private path,
readers and physical exit. Original commands settle before reap, with
forced0/owned0; no new semantic/SAN/fault/game fixture is added. External final
index6584 B:
`fdb7cef81ce29c1b862c90ea2a5ee7bf197e276ad2cdfd2057caa0fe4aa5a5d3`.

A separate candidate adds post-immintrin J/return and L/int aliases, renaming
only four proven TT-local declaration/reference tokens. Source8992 becomes
8826 B, raw-166, and bootstrap9787 B, but whole4628 grows to4650 B, LOSS22.
The full-header340501 tokens match only after those four binding-owned token
correspondences, and the entire native remains equal. Compile1/encode1 and
strict Python/CLI restoration pass; no candidate engine/normal/adoption runs.
Its original argv-AST preparation error precedes every product command and
is preserved; the corrected runner retains the same candidate/argv. External
cost index16270 B:
`27817e63b785609c336d3bac93a0f12c9d336c43c3731ed7a979f74a6841dca3`.

## Full F exact FROM macro expansion: 2026-10-24

The definition of FROM is removed and its three fixed unsigned-local-m calls
expand to the exact original ((m)&119) tokens. TO/PROMO/MOVE/atomic macros and
all bodies remain. Source7905 becomes7885 B, bootstrap8827 becomes8807 B and
whole4276 becomes4275 B, gain1 and179 B above4096. Both actual full-header CPP
outputs are86599 B/67dbe911 and entire-byte equal, with20286 matching tokens;
the18576/98818a94 native is entire-byte equal. The four edits/five protected
gaps/full inverse consume the actual quiet/format/frequency/pool and earlier
literal guards. Canonical/DEV and optional selected source pipelines bypass.

Ordinary --dev1 reproduces shipping twice and old DEV twice; unchanged
selected1 passes quit/EOF, eight legal GO, three TIDs, actual native/private
path/readers and physical exit. The two optional ordinary builds reproduce
their selected4319/4045 tuples twice each and consume the new7885 full
reference. Original outer/four commands settle before reap, forced0/owned0.
An initial source-extraction assertion stops before any child/product launch;
its original failure is preserved separately from the single actual cohort.
No new semantic/SAN/fault/game fixture is added. External final index7961 B:
`02cf20dd605df9ed8e94361a93d7b8c5b17bf5c7171ac7dfce80cd894e4b673a`.

F8 v9 consumes actual7885 and applies the same six resource roles to7923 B,
still raw+38 relative to full fixed2. Its own8855 B bootstrap and nice24/header73
whole4284 improve the prior4286 by2 B, independently of fixed2's gain1.
The entire18576/26182257 native remains equal. Ordinary reproduces twice;
unchanged positive assertions pass quit/EOF/eight legal GO/nine TIDs/all-eight
activity, FD/maps/NX/no-WX/native/private path/readers and physical exit. Only
class/stage literals change in build/verify; shared D f5ed stays exact. Build
runtime_qualified=false remains separate from positive runtime. Original
ordinary/positive commands settle with forced0/owned0. A legacy cost-index key
was labeled normal although its path was cost; the original and correction
are preserved and the actual independent normal tuple matches in full.
External final-v3 index7581 B also corrects two stale external annotation
domain labels without code/expected/product changes:
`8ea4f1fa5acc63766c529462dd73d04548f795a10e59eb9915098992cc5469d6`.

## Default A EP-maker sharing: 2026-10-24

After scoped frequency names, default Loose A shares EP legality with its
existing move maker. Removing the duplicate three-square trial and adding
one forward declaration changes source8397 to8355 B, bootstrap9351 to9309 B
and whole4499 to4489 B, gain10 and393 B above4096. The new18576/f99afdba
native differs. The only nonempty shipping input follows a legal doublepush,
with half0 and initialized bounded HCE/king cache. Trial15/17/PROMO0 leaves
child EP empty, so the nested normalizer returns immediately; maximum v/D
nesting is2. Fully initialized provisional unsigned hash/context is discarded
and only own-king legality is consumed. Arbitrary poisoned/high-half Board
equivalence, timing and stack improvements are not claimed. Canonical/DEV
and all three root-policy dictionaries/source pipelines bypass this stage.

Actual candidate TU with old-D/name-only reference and an independent
64-square oracle passes the same12 roots,21 legal replay states and122 legal
children in one optimized and one fatal-UBSan execution. Ordinary --dev
reproduces shipping twice and old DEV twice; unchanged selected passes
quit/EOF, eight legal GO, three TIDs, the actual new image, private path
removal, readers and physical exit. Original commands settle before reap,
with forced0/owned0. Named reports remain intact after an outer stdout
capture/child-label filename collision; the capture is not independent child
stdout evidence and the original is preserved without rerun. External final
index6515 B is
`b6fc93cf58bb81bd3eb7fb52cdcb79af69fa0fe99246c2772db371aed7c5b15c`.

## Full F quiet ordering, F8 and E legal-square walks: 2026-10-24

Full F removes its unique private quiet-order helper and reuses the caller's
already decoded FROM/TO and prior-piece index. History, continuation,
correction and unsigned noise arithmetic remain. The two edits and three
protected gaps shrink7979 to7905 B; the existing format/frequency and earlier
literal guards are consumed through the full inverse. Bootstrap8901 becomes
8827 B, whole4304 becomes4276 B, gain28 and180 B above4096. The entire
18576/98818a94 native remains byte-identical. Ordinary --dev reproduces two
shipping and two old DEV tuples; unchanged selected passes quit/EOF, eight
legal GO, three TIDs, actual native/path/readers and physical exit. Two
optional builds preserve their actual4319/4045 complete tuples twice each
and consume the new7905 full reference. No new core/SAN fixture is added.
The external final index7723 B is
`5efb7f95898880afd9bf9881dd513d40fd21ab24dd2d5f4149a8c0bc4db9238d`.

E's move/attack and insufficient-material loops visit only valid squares with
q=q+9&~8. The same64 squares occur in the same order, iterator arithmetic
stays0..128 and existing continue/early-return behavior is retained. Two
headers/invalid-skip spans shrink8598 to8569 B, bootstrap9552 to9523 B and
whole4599 to4586 B, gain13 and490 B above4096. Model19/physical21, all five
ordering features, PVS/TT/three learners and pool bodies remain in protected
gaps. New native22672/0449f0ea differs. Ordinary --dev reproduces shipping
twice and unchanged old DEV twice; unchanged selected passes quit/EOF/eight
legal GO/three TIDs, the new image, readers and physical exit. No new projected
unit/SAN/model matrix is required by this exact finite iterator proof.
The external final index4849 B is
`90041780f51c2843af00dc70b8a699752304029c3ed38f390ff14d379bf9330c`.

All six original F/E commands settle their groups while leaders remain
unreaped, then reap, with forced0/owned0. These are normal selected-wrapper
observations; the separately recorded early compiler-leader-exit limitation
is unchanged and is being addressed in a separate common-bootstrap change.

The separate F8 v8 producer consumes actual F7905 and applies its six fixed
resource roles to7943 B, raw+38. Its own8875 B bootstrap/nice24/header73
whole is4286 B, gain30 from4316 and190 B above4096. The entire18576/26182257
native equals old F8, independently from F2's native identity and gain28.
Ordinary reproduces both full tuples and the existing positive verifier
passes quit/EOF/eight legal GO/nine TIDs/all-eight activity, stdio-only FD,
maps/NX/no-WX, native restoration, readers and physical exit. Shared D f5ed
and the substantive positive assertions are unchanged. Original ordinary
and positive groups settle with forced0/owned0; no new core/SAN/fault runs.
Build runtime_qualified=false remains separate from the actual positive result.
The external final index6728 B is
`35051ca82a563df92ea18e6622480831cc1786c261c7e2f9aca1da173bfb3cb1`.

D separately tests one syscall-input-list specialization: mmap retains six
arguments, futex WAIT retains its fourth NULL timeout and the remaining
calls omit unused high-register zero inputs. Runtime source shrinks48 B,
linked text24 B and native32 B, but H28 packet4512 grows to4527 B. Current
refill overhead1069 stays exact and whole5581 grows to5596 B, LOSS15.
Only native1/encode1/loader1 and exact DATA inverse run. No entry, syscall,
worker, audit or normal runtime is claimed; current D remains5581/HQ6037.
All original tools end naturally with forced0/owned0. External index3417 B:
`e097890b47dcb6c59abe4e417b54455a1fdd41dc4f4192bd1c6bd8ca41b78a13`.

B's two nonzero-ctz bit-index expressions are separately folded from
(i&7)+(i&56)*2 to i+(i&56), equal for all64 indices. Source9759 becomes9747 B
and bootstrap10788 becomes10776 B, but whole4950 ties4950 with changed bytes.
Native26112 keeps its length but differs, and linked text grows1 B. Candidate
compile1/encode1 and strict restoration pass; no engine/normal/adoption runs.
Current B remains its prior4950 tuple. Original driver/five children end
naturally, forced0/owned0. External index11893 B:
`1d5da5d10c757d871d323b374729533fd6a6408369e3215767d26d26d2eebb20`.

## Common C compiler-group correction, external candidate: 2026-10-24

The maintained C wrappers can reap an early-exiting compiler leader before
its live same-group child is settled. Normal selected runs do not prove this
case absent. A late transform preserves the actual compiler command, source
expression, environment and FD exec, while normalizing/restoring SIGCHLD,
handling partial stdin writes, covering masked Popen publication/unmask with
the outer finally, and keeping the original leader unreaped through live
same-group settlement. Only then does it reap and remove the private path.
Unsettled cleanup exits125 and preserves the directory; readable /proc is a
profile assumption. Non-zombie drain is not literal zombie/group absence or
detached-descendant cleanup.

One actual F4276 context grows bootstrap8827 to9851 B and whole4276 to4657 B,
cost381 B. Encode1 and strict Python/CLI inverse pass. The actual whole with
real cc restores the exact18576/98818a94 native, reaches uciok/readyok in the
observed0.3859s, removes its path and exits on quit. Two separate direct-Python
source-bound trace cases observe an early compiler exit/live child with
inherited SIGCHLD_IGN, and pending TERM at the actual publication/unmask edge.
They pass unreaped-leader/not-live-child/reap/cleanup/exec ordering and143
termination respectively. These are three bounded paths, not a six-family
fault matrix or general scheduler proof. Original handles/pidfds settle with
forced0/owned0. Final index9470 B is
`5c1815c7229928b393e617e54158b47dbe79375492252bcc557d4bd959c05923`.

A separate notation-only candidate caches fresh module/private/attribute
bindings while preserving all branches and alias-expanded AST. Its source
shrinks9851 to9462 B, but complete4657 becomes4665 B, LOSS8. Encode1 and strict
Python/CLI inverse pass; no candidate runtime or adoption occurs. Final
index9605 B is
`a73757440746529bd0a8be96c6cef2aae79facca9c68fc557bcaab90d842dc66`.
Both prototypes and the six-consumer hook design remain outside Git. Current
size rows and normal-runtime evidence retain their prior maintained wrappers;
neither candidate resolves this limitation for those shipping files yet.

## Compact A PALS bounded deeper observation: 2026-10-24

The actual current optional PALS source15535/6361f015 and the existing fatal
UBSan observer222392/de5bfc8e are checked before one runtime cohort. Current
root-policy generation/package projections match the original producer;
the two changed default-builder/recipe files do not alter this optional path.
Two previously replayed QGD/KID positions use public480000ms clock inputs,
nominal16s each, followed by the original active GO/50ms quit. No score,
TT, history, slot or refutation is injected and no case/seed search occurs.

The32.0817s original runtime exits0 with17 actual counters, zero valid
refutations, zero Repair/recheck/Repair score adoption and421 direct NORMAL
acceptances/five direct completed best commits. Safety assertions and both
reader EOF/join pass; group settlement precedes leader reap, forced0/owned0.
No new legality/three-TID oracle runs. Repair/recheck remains unobserved;
this is not positive runtime qualification of that branch or strength evidence.
Compile0/runtime1 and no automatic retry. The external final index6814 B is
`32bbfbfeb504a868d9f760fe7b7262c51eb8fd3f7106468a8038c392fc98009a`.

## D shares initial prefill and subsequent refill: 2026-10-24

The scalar H28-private decoder starts range at1 and uses one loop-head
normalization for both the initial31 input bits and subsequent refill. One
extra loop-head visit preserves the final refill. Its three source spans
shrink3422 to3375 B; the linked loader text shrinks961 to893 B. Packet4512,
native7388/395fea4d and the entire zero232 restored image remain unchanged.
Header/loader1137 becomes1069 B and whole5649 becomes5581 B, gain68 and
1485 B above4096. HQ keeps its original H24 decoder and6037 B whole.

Valid fixed packets retain decoded bytes and input cursor. Malformed packets
can differ in private partial-write ordering and error4/5 priority; the actual
loader still exits126 before native entry on either error. This specialization
does not claim a generic decoder API's failure-state equivalence. The old
H28 transient512 MiB allocation remains; previous startup/RSS observations
are not relabeled as fresh measurements for this loader.

Ordinary regeneration reproduces both shipping forms twice. The existing
positive verifier passes two CHECKPOINT audit images, four production
quit/EOF sessions and twelve legal GO, restored RX/initial BSS, guard/NX/W^X,
stdio-only descriptors, no children, three TIDs, readers and physical exit.
Original groups settle before leader reap with forced0/failures0/owned0.
The final verifier adds exact decoder-policy/whole/audit selection and retains
the shared process-owner bodies consumed by F8.
The external promotion index7141 B is
`6f080009ea4b96e39b56ff741bf4f7098d78ce82d412b3ba5b3bdf0389c1e80d`.
F8 updates only recipe/README provenance for the new D verifier. Its actual
direct and transitive helper definitions, imports and OWNED state are exact;
the current source closure and source/native/bootstrap/whole pins are checked.
No local F8 compile/encode/runtime repeats, and old v7 receipts retain their
original verifier source identity. The external provenance index13828 B is
`689c6672e6eec8fe422fbc8289c38a692e9ba7f72dbe72985054b742b8505e1f`.

A separate native terminal-loop proposal shrinks source25 B, native64 B and
linked text39 B, but H28 packet grows1 B and complete file5649 becomes5650 B.
It is rejected before engine execution or combination with shared refill.
Its external index3913 B is
`cf02c1912503e8f281d58402d834993413711ac7a74e4527da62385f6bdadab9`.

## A scoped frequency names and C/E depth-token ownership: 2026-10-24

Default A reuses names whose local reference scopes do not overlap the renamed
globals. Its fixed seven-binding map preserves253 declarations/2441 reference
edges,54 physical edits/55 protected gaps and the full inverse, including four
atomic stores and one flag-clear argument bridge. J/return and L/int macros,
local/member/header tokens and the three optional root-policy paths remain.
Source8443 becomes8397 B, bootstrap9397 becomes9351 B and whole4505 becomes
4499 B, gain6 and403 B above4096. The entire18576/35056c24 native is unchanged.
Ordinary --dev reproduces shipping twice and unchanged DEV twice; unchanged
selected verification passes quit/EOF, eight legal GO, three TIDs, actual
native restoration, readers and physical exit. Optional dictionaries and
pipelines are preserved; no new optional runtime is claimed. Final index4618 B:
`70f809e8adca76efce9e0931857f1ab122807c865edf66c6ce1cd76346f9012e`.

C and E apply the already reviewed completed-depth job-token principle in
their own six source roles. GO drains first, then publishes both depth-1
tokens under the existing mutex. Each worker claims0 before unlocking/think.
The null startup-result sentinel, last completion/output/flush/broadcast,
pending drain and partial-create joins remain. Their unique shipping think
callers establish the new entry invariant; private direct think callers must
seed0 explicitly. Canonical DEV and model/search/TT/learner bodies bypass or
remain protected. Seven gaps and full inverses consume each previous package
guard before forwarding the final literal. This is an internal representation
change, not a claim of arbitrary direct-entry or timed-search equivalence.

C source9093 becomes9075 B, bootstrap10054 becomes10036 B and whole4672
becomes4666 B, gain6 and570 B above4096; new native22672/5c447040 differs.
E source8616 becomes8598 B, bootstrap9570 becomes9552 B and whole4605
becomes4599 B, gain6 and503 B above4096; new native22672/cbe2a523 differs.
Each ordinary --dev reproduces shipping twice and unchanged old DEV twice,
and each unchanged selected verifier passes quit/EOF/eight legal GO/three
TIDs, new restored images, readers and physical exit. The source caller proof
and prior A/F ownership evidence are reused rather than adding a new projected
think fixture. Original groups settle before leader reap, with forced0/owned0.
C index8698 B: `0dff261dc8fe8bfaab2319106514592963417ef51f8c9eb243b3a66d6268e569`.
E index4821 B: `2908c63402724ebf67af9349a018e6200fd74ee7678c232122f14d5922570fe7`.

B's separate wait-only helper preserves startup's lack of a stop store and
shares lock/wait/unlock at two regions. Source9759 becomes9702 B, raw-57, but
native26112 becomes26136 B and whole4950 becomes4954 B, LOSS4. Only its fixed
compile/encode/strict restoration run; no engine runtime or maintained change
is added. The external index8657 B is
`2d91d05f28468ebfd0f7553585291132fd2d02837a9e0f2572d27093a1527742`.

F's current154 B input-move matcher also has a source-only packed-input
proposal. Preserving short-token bounds, all four coordinate ranges, exact
length/promotion spelling, capture-bit-only masking, actual legal maker and
NULL fallback requires299 B, raw+145. No candidate file, compile, codec or
engine is run. The formatter remains necessary for bestmove output. A bare
0x88 test is insufficient: invalid file q in q1a1 can alias a valid square
after unchecked arithmetic. This is a source-priority decision, not a measured
whole-file loss or performance result.

## Current compact A–F ring screen: 2026-10-24

The actual A4505/B4950/C4672/D5649/E4605/F4304 files run six exchanged-color
pairs on the A-B/B-C/C-D/D-E/E-F/F-A ring. At1500ms+10ms and at most80 searched
plies per game, twelve games contain924 legal searched plies. One game ends
with D mating C; eleven reach the ply cap and remain `*`, not draws. There are
no flags, protocol failures or cleanup failures. All24 original entry processes
exit naturally with both pipe EOF/readers joined, no extra owned group members
before reap and forced0/owned0. D's own-ELF identity is checked separately from
its previously qualified restored RX. This45.148s screen advances current-file
legality/protocol/clock/lifetime evidence without a strength or Elo conclusion.
The external final index29278 B has SHA256
`4480742f90989903f52fc44df68ba8c5611461f37d0380d1dd999d0aceac4b92`.

## F8 v7 consumes the actual smaller full source: 2026-10-24

The separate eight-worker profile consumes final F7979/03fc7a4d and applies
six fixed resource roles to produce8017/ea06bad1, raw+38 rather than the old
v6+37. Under the existing renamed mutex J, GO marks all eight depth fields-1
before broadcast. Startup, claim0, pending/flush, strict first-depth maximum
and actual-created-count joins remain. New native18576/26182257 and the
8949 B bootstrap use F8's own wrapper and unchanged nice24/header73 codec.
The actual complete file is4316/e58e5302, gain11 and220 B above4096; F2's
size or separate gains are not inherited.

Ordinary regeneration reproduces shipping twice. Separate existing positive
assertions pass quit/EOF, eight legal GO, nine stable TIDs, all eight workers'
CPU activity, stdio-only FD/no children, maps/no-WX, nonexec main stack,
native restoration, reader completion and physical exit. The shared D
WNOWAIT owner is consumed, and F8 startup replaces its early poll with
non-reaping exit observation. Guard counts/sizes, peak stack and target
scaling remain unproven. Build runtime_qualified=false and the separate
positive result retain their distinct scopes. Original groups settle before
leader reap, with forced0/owned0. The actual producing source closure has68
files; this observation is not a mandatory size/count gate.
Its final corrected index6845 B has SHA256
`6c11ac3107d39319dbedcca48a45582bdcc97a060aa39f6fe620ad4cb90a9abf`.
The correction changes only README's F2 codec description to actual nice24;
the original index, producing inputs and execution receipts remain preserved.

## Current generic C/Rust twelve at target512: 2026-10-24

The current canonical C/Rust/model/profile inputs are rebuilt into twelve
original natives, with one sequential compiler per file and no compact forms,
packaging or reproduction. Actual old/current source comparison finds changed
search/parallel inputs; all twelve new native hashes differ from the historical
de5676d files, so no old runtime row is relabeled as current.

One bounded sequential cohort passes all twelve actual files with511 search
workers plus main,512 stable startup TIDs, TT26/loose and DEV off. Each has two
legal-result epochs, with six stop and six active quit paths across the cohort.
Independent move legality, positive worker CPU activity, stdin/stdout/stderr
EOF, saved worker-identity disappearance and group-others absence are checked
before WNOWAIT final reap. All exit naturally0; retries/forced/owned are zero.
The twelve native hashes remain unchanged after execution. A concurrent F8
builder provenance edit does not affect the frozen runtime adapter or any
canonical engine/model/profile input.

This runs on eight affinity CPUs in WSL, not512 hardware threads. AS/DATA8 GiB,
CPU60s and wall45s per process are finite; observed maximum sampled RSS is
2176450560 B and virtual size6547410944 B. These samples, the two short epochs
and thread counts do not prove a true peak, scaling, strength or compact-entry
eligibility. The external runtime index3132 B has SHA256
`1a72b39692c55e92c2de357afdd241478b606ff180aff9142187b7116a95c303`;
the actual899068 B report has SHA256
`30309d181f0a12676869eef44b138f79fd31a132257544ede4c4a5df90c3f48d`.

## Full F combines frequency spelling and a shared formatter: 2026-10-24

A fixed20-binding assignment gives shorter available names to frequent globals
without changing local/member/header/API/string tokens. The existing Clang
graph confirms247 declarations and2300 reference edges;124 physical edits,
125 protected gaps and the full inverse preserve binding identity, including
six explicit atomic macro-argument provenance cases. This stage alone makes
source8094 become8020 B and whole4317 become4308 B. The entire native stays
4a8d1329. No name or codec sweep is used in ordinary builds.

The move formatter then shares four coordinate writes in a fixed loop with
shifts0/4/7/11 and mask7. Capture bit3, promotion suffix/NUL and the final
`0000` bytes remain. Actual old/new formatter checks cover40960 combinations
with canaries,86 legal input/child comparisons and93 actual output records,
including both-color EP and quiet/capture promotions. This stage alone gives
4312 B; the actual combined file is4304 B, gain13 rather than the sum14.
Combined source is7979 B, bootstrap8901 B and native18576/98818a94, entirely
equal to the formatter-only native and different from the predecessor.
Full F remains208 B above4096 with HCE, all three learners, full-key bound TT,
MTD, persistent SMP and the root attaining-witness path intact.

One ordinary --dev reproduces combined shipping twice and unchanged old DEV
twice. The unchanged selected verifier passes quit/EOF, eight legal GO,
three TIDs, new native restoration, reader completion and physical exit.
Two optional ordinary builds also consume the new full-reference chain while
their actual4319/4045 source/native/bootstrap/whole tuples remain unchanged in
two reproductions each; those build checks are not new optional runtime.
Original owned groups settle before leader reap, with forced0/owned0.
The final F index13031 B has SHA256
`661ed52c4af729fbf9260355474c34f61d33372c0051b39351b3d7f4ad1c092a`.

## D scalar spends transient memory on a smaller packet: 2026-10-24

The scalar own-ELF now stages an H28 context codec from the preserved H24
producer sources. Sixteen exact edits across five producer files change only
the format identity, table size and hash index. Native7388/395fea4d, the21
coefficients, BCJ/body232 geometry and restored image b2982877 remain exact.
The packet4580 becomes4512 B; loader/header1137 B is unchanged, giving whole
5717 to5649 B, gain68 and1553 B above4096. HQ keeps its H24 source and6037 B
file. Canonical native, original loader/packer and old H24 APIs remain stored.

The tradeoff is a512 MiB temporary context table versus32 MiB. Ordinary builds
reproduce scalar and HQ natives/files twice. Actual scalar quit/EOF startup
takes0.4418/0.4510s, within the4K60s limit on this local host; kernel VmHWM is
522624 KiB (510.375 MiB). At ready, VmSize is6504 KiB, and the original512 MiB
extent is not retained. Some addresses are reused for small worker/TT mappings,
so the stronger sampled no-overlap metric remains false. Checked munmap source
and ready mappings support release without claiming a syscall trace or final
target RAM eligibility.

The production verifier passes two CHECKPOINTs and four quit/EOF sessions with
twelve legal GO, full restored RX, separate initial BSS/padding, guards, no-WX,
stdio/no-children, three TIDs, reader completion and physical exit. The validator
also fixes its own process settlement to keep the original leader unreaped
until other group members are absent. A later narrow fix replaces CHECKPOINT's
potentially reaping waitpid with WNOWAIT waitid stop/exit observation. Only the
two unchanged audit files are rerun for that final validator source; the four
production sessions keep their original source identity. All original groups
close with forced0/owned0. The final D index8750 B has SHA256
`adb5f75196e0fb19b9b332d06ff961e3d70a2a9c071821652c0152f59c28241c`.

## E shares ordering coordinates with its caller: 2026-10-24

E's sole private ordering leaf is now inlined into the actual ranking loop.
That caller already decodes origin, destination and mover-plus-six, so the
five ordering terms reuse those values. Promotion additions share one term.
All19 coefficients remain independent; the physical21 slots, model arithmetic,
incremental Board and hash, TT, search and SMP bodies retain their contracts.
Two owned regions/three protected gaps and the complete inverse reduce8702 to
8616 B, bootstrap9656 to9570 B and whole4630 to4605 B, gain25 and509 B above
4096. Native grows18576 to22672 B with new identity722e744e; smaller native,
equal timing or stronger play is not claimed.

The actual old/new ranking blocks pass1788 paired full-rank observations in
three contexts against the independent E19 oracle and old actual leaf. The
actual search hook also checks ordering; existing model/Board/refresh and
both-color special-move fixtures pass. Ordinary --dev reproduces shipping
twice and unchanged old DEV twice. The unchanged selected verifier passes
quit/EOF, eight legal GO, three TIDs, new native restoration, readers and
physical exit. Both original groups settle before leader reap, with forced0
and owned0. The previous keyword/cross/source/literal guards remain consumed;
old DEV is a separate diagnostic reference, not the E19 oracle.
The final E index4664 B has SHA256
`2c811075076e17a7fdf84dbccb254f8bfeb0e8626aeeaa71a2a56a5d2c7fc380`.

## B reuses its legal maker for EP normalization: 2026-10-24

B removes the duplicate three-square EP simulation from its private normalizer
and consumes the existing maker's nonzero legality result. Actual nonempty EP
input follows a double pawn push; the inner EP maker clears EP, so its nested
normalizer returns immediately. Legal EP returns101. Completed mailbox,
bitboard and king state are coherent, while the inner scratch hash/context is
discarded. The two pawn-removal orders, extra stack/work and timing differ;
native and timed-search equality are not claimed. SEE, singular exclusion,
full-key TT, the three learners and persistent SMP remain connected.

One source region/two protected gaps and the complete inverse reduce9797 to
9759 B. Bootstrap10826 becomes10788 B and whole4954 becomes4950 B, gain4 and
854 B above4096. Native remains26112 B with new identity962a7e2b and text92 B
smaller. The focused actual-function old/new check passes six double pushes,
six EP cases including four king-safety rejections, eight normalizer pairs and
twenty complete Board comparisons. That sanitizer fixture also uses-mavx2;
it is not a minimum-ISA proof. Ordinary B uses its unchanged compiler without
that flag and reproduces shipping twice and unchanged old DEV twice. The
unchanged selected verifier passes quit/EOF, eight legal GO, three TIDs,
actual native restoration, readers and physical exit. Original owned groups
settle before leader reap; forced cleanup and owned handles are zero.
The final B index13594 B has SHA256
`1dda106dcc7054a175cd0515484ab5f8f8a45348ea46bfcbf2ffd852da7ded2e`.

## Default A worker-state compression: 2026-10-24

Default A transfers the same negative completed-depth job token principle to
its own shared startup/completion loop. A typed pointer preserves the null
startup-result sentinel; GO publishes both depth fields under the mutex and
the only shipping think caller claims0 before entering search. Six fixed
regions/seven protected gaps and the inverse preserve all other code, including
the keyword aliases. Source8461 becomes8443 B, bootstrap9415 becomes9397 B and
the actual complete file4511 becomes4505 B, gain6 and409 B above4096.
Its new18576/35056c24 native differs from the predecessor. One ordinary --dev
reproduces shipping twice and unchanged old DEV twice; the unchanged selected
quit/EOF sessions pass eight legal GO, three TIDs, exact restored native,
private-path/readers/process exit and forced0/owned0. All three optional root
policies bypass the new stage and retain their dictionaries, source and literal
paths. The original source/guard chain is consumed before the final literal
replacement. Private direct think callers must seed depth0; canonical DEV is
unchanged. This is a default-only internal representation change.
The maintained A final index4698 B has SHA256
`b6aea32776d7f5bee1204db4a2de20124dba1027580098793de6f41e74eb46f3`.

## C SIMD model with the smaller common search/runtime: 2026-10-24

C now composes its actual signed-net eight-int16 Board/evaluation regions
with the smaller common A-derived mailbox/PVS/runtime. The current C input
already uses mailbox. Its qm coefficients, incremental remove/store/add,
king update, actual128-bit madd/four signed32 sums and explicit `-mavx2`
target remain connected to recursive evaluation. King-capture/move-buffer
guards and QS draw handling remain. This is a source/compiler/search variant;
old-C traces, native identity and playing-strength equality are not claimed.

Source9527 becomes9093 B and bootstrap10566 becomes10054 B. The selected
compiler is explicitly `cc -Os -mavx2 -x c - -o x -s`; the original
preprocessor/DEV flags remain unchanged. The actual old source, literal and
bootstrap are consumed before the compiler/literal adapter. Native26152
becomes22672 B and the fixed existing codec gives whole4672 B,106 B below
4778 and576 B above4096. Independent int64/refresh comparison passes2965
model scans,2784 completed put boundaries,189760 scalar checks,88 int16
numeric cases, four EP scratch cases and154 legal children, including both
colors, castles and promotions. One ordinary --dev reproduces the entire
first-cost shipping tuple twice and old DEV twice. The unchanged selected
verifier passes quit/EOF, eight legal GO, three TIDs, new native/private-path
restoration and physical exit. Original groups settle before leader reap;
forced cleanup and owned handles are zero.
The maintained C final index14082 B has SHA256
`4c41434e8d6db2a08f91a4d51a1935b41e556e5a88fc0e4598b0677003bd7d5f`.

## Full-F TT and worker-state compression: 2026-10-24

Full F now stores its private TT depth/bound as one byte
`2*(depth+1)+upper`. Its only production writer emits LOWER/UPPER, depth is
0..126, and valid metadata2..255 excludes empty0. Move17, score16, full keys,
coherent publication, mate normalization and the root attaining-witness path
remain. One equality checks exact depth and bound direction after score
normalization. Fresh calloc and no external TT ingress keep old/new formats
separate. The independent source review and focused actual-function comparison
cover six fresh/retained MTD calls per form against independent depth3 minimax,
legal attaining witnesses, matching nodes/learners/normalized logical TT,
actual lower/upper writers, full-key collision miss and both mate directions
at probe ply1/126. This does not claim arbitrary-depth runtime equivalence.

The pool removes its separate global/local epoch state. Under the existing
mutex, GO marks every worker's completed-depth field -1; each worker claims0
before think. The only shipping think caller is this worker path. Direct
private fixture callers must now seed depth0 explicitly. Pending/startup,
spurious-wake predicates, quit, output/flush and joining the actual created
prefix retain their contracts. These internal representation changes produce
a different native image; they are not native-identity spelling changes.

One fixed cost gives TT alone4327 B, and an actual combined cost with the
pool gives4317 B,33 B below maintained4350 and221 B above4096. The two gains
are not added. Source8153 becomes8094 B, bootstrap9075 becomes9016 B and the
new18576/4a8d1329 native is reproduced. One ordinary --dev reproduces the
complete combined tuple twice and unchanged old DEV twice. The unchanged
selected verifier passes quit/EOF, eight legal GO, three persistent TIDs,
restored native/private path, reader completion and physical exit. Original
groups settle before leader reap; forced cleanup and owned handles are zero.
The maintained final index10712 B has SHA256
`7189b9058adee77b89955246e3a8e4baf8b6885e3ff236c70124ea052b7c4d0a`.

Fixed-eight-worker F v6 directly specializes the actual8094 B full source
through six resource roles. Job publication marks all eight depth fields -1
under the same mutex; a two-worker-only reset would leave six workers asleep.
Source8131/native18576/bootstrap9063/whole4327 reproduces twice,33 B below
prior4360 and231 B above4096. The original positive assertions pass quit/EOF,
eight legal GO, nine stable TIDs, all eight workers active, stdio-only FD,
no children, mappings/no-WX, native restoration and physical exit. The new
native dba06bb3 differs from v5. Guard sizes/counts and final scaling are not
asserted. The original ordinary and positive groups settle before leader reap;
forced cleanup and owned handles are zero.
The fixed8 final index5602 B has SHA256
`05e4689dec300a72e2b72afc47ec2a098c0d85a8539a236e46aa1ebdac33d8fd`.

## E keyword aliases after model/search composition: 2026-10-24

The last E shipping stage now uses `J return` and `L int` after all seven
includes. Four owned TT-local tokens move J/L to j/k before their later
inner shadows;89 int and45 return tokens use the aliases. The139 edits,
140 protected gaps and full inverse reduce source9074 to8702 B and bootstrap
10028 to9656 B. Full-header CPP tokens match after reversing those four local
tokens, and the complete18576/802704e6 native is unchanged. The fixed existing
codec gives whole4630 B,16 B smaller than4646 and534 B above4096.

The actual prior package chain remains live: restore keyword source9074,
restore cross source9866, consume its original literal/template10868, validate
the cross bootstrap10028, then replace the final source literal. The current
E19 coefficients, incremental model, search, resources and old DEV path are
unchanged by this stage. One ordinary --dev build reproduces shipping twice
and actual old DEV twice; the unchanged selected verifier passes quit/EOF,
eight legal GO, three persistent TIDs, native restoration and physical exit.
Both original command groups settle before leader reap; forced cleanup and
owned handles are zero. These local results are distinct from predecessor
264ae12 CI and do not establish equal timed traces or playing strength.
The maintained final index4380 B has SHA256
`4616f30939843d3802d4c30f7c1021099e6236465dc8fdfad485a63e121f8d16`.

The shared1315b17 checkpoint passes C/Rust in
[engine CI40028110258](https://github.com/daejunnom/Rove4k/actions/runs/40028110258)
and Node22/24 in
[repository CI40028110203](https://github.com/daejunnom/Rove4k/actions/runs/40028110203).
Both actual job checkouts use568f4766cde10140433a5a45859da22265a86f4e;
its d1aded22d65dfa4e8fa26e6e6456126413b65dd5 tree equals1315b17.
Both artifact downloads match API size/digest. Only the two named E
build/runtime reports are read:4630 B, shipping2/old DEV2, quit/EOF,
eight legal GO, three TIDs and physical exit. Their frozen builder0e5cc537
and helper8d69bac1 match the shared source. CI index3730 B has SHA256
`4ee352e5f3ff07cb717df952d7955b2eb63ac9c3b02b3cb4a68860494a620b4a`.

One bounded current-file game screen runs actual E4630 against prior E4825
with four exchanged-color opening pairs,1500ms+10ms, at most80 searched plies
per game and fixed2/TT18. All511 searched plies are legal; eight protocol and
physical-exit sessions pass with16 fresh restored-native processes, quit8/
EOF8, stable three TIDs, reader EOF/join and forced0/owned0. E4630 wins2 and
E4825 wins1 by mate; five ply-limit games remain `*`, not draws. There are no
flags or protocol failures. This advances current-file validation without
establishing strength/Elo or hardware scaling. Final index17496 B has SHA256
`d0530d97e973d09e461e14d870164cb7cc9f75c413faa9fe308dff954fa5409c`.

## Scope-aware A keyword aliases: 2026-10-24

Default A now uses `J return` and `L int` after its seven includes. Two TT
locals previously named J/L reuse j/k at four physical tokens; all their outer
uses finish before the later inner shadows. The aliases cover43 return and
88 int tokens. The136 edits/137 protected gaps and whole inverse reduce
source8821 to8461 B and bootstrap9775 to9415 B. Full-header CPP tokens match
after reversing only the four admitted local-name tokens, and the entire
18576/5fd8f877 native remains identical. Whole4525 becomes4511 B, gain14.
One fixed first-cost compile/encode and independent strict restores precede
one ordinary --dev reproduction (shipping2/old DEV2) and the unchanged selected
verifier (quit/EOF two sessions, eight legal GO, three TIDs, native restoration
and physical exit). Original groups settle before leader reap; forced cleanup
and owned handles are zero. The new stage and literal adapter run only for
default Loose; all three root-policy dictionaries and their8821 base/literal
guard chains remain. This changes macro tables and diagnostic locations, not
the observed native bytes; no general keyword-macro optimizer is claimed.
The first-cost index20677 B has SHA256
`0368c766dfd8ce6660f40e7f433284a853ec58bed02d550357330fcdeae8abd6`.
Local maintained qualification is separate from the preceding5f2cade CI below.
Its final maintained index16065 B has SHA256
`943e5128209766a5f556df858f60a0d89653e2ee687a6862316166914f1d94c5`.

## B single int alias: 2026-10-24

B adds one `I int` definition after the includes and changes99 admitted int
tokens at the final shipping stage, after the earlier constant/setter guards.
Source9981 becomes9797 B, raw gain184; whole4955 becomes4954 B, gain1,858 B
above4096. Full-header CPP tokens and entire26112/274bf31c native match the
predecessor. Exact100 edits/101 gaps and full inverse limit the transform;
DEV and all earlier model/admission flags remain unchanged, including the
false shipping/diagnostic-model-equivalence flag. The original package body
already consumes arbitrary admitted source bytes, so no fixed-literal guard
is bypassed or replaced. One ordinary --dev reproduces shipping2/old DEV2,
then the unchanged selected verifier passes quit/EOF, eight legal GO, three
TIDs, actual native restoration and physical exit. Original commands settle
before leader reap, forced0/owned0; no extra candidate or codec sweep is run.
First-cost index19708 B:
`ab20d5a8db8fbc9a3bd4d5bbe82f8ac436274e33b9008f2d5fd64ccd1ee2e1f9`.
Maintained final index15409 B:
`422ea5e28d0d15a944f9bfcef80613cccb22d90a7e6bb2d326f3a3557c6930d3`.

## E19 with the smaller common mailbox search: 2026-10-24

E's shipping source now combines the smaller full A-derived Board/PVS/runtime
presentation with the current E19 model. Both previous E and selected E are
mailbox implementations; bitboard removal is not a reason for the gain.
Five actual model regions are extracted from the previous9866/51e1db47 source,
positionally rebound and inverse-checked. Logical19 coefficients/physical21
slots (zero0/6), Q, incremental M/A, quadratic/clamp/tempo and all five move
ordering features remain connected to actual recursive evaluation and every
pseudo-move score. Full PVS/QS, coherent full-key-bound TT, history/continuation/
correction and persistent two-worker SMP remain. The common implementation
changes the search representation/policy; old-E traces and strength are not
claimed equal. Old DEV21 stays an unchanged control, not an E19 model oracle.

Source9866 becomes9074 B. The actual old package consumer first reconstructs
the old9866 source/literal and10868 B bootstrap; a two-region compiler/literal
adapter then makes the selected10028 B bootstrap. The shipping compiler uses
the selected A flags; the original preprocessor and DEV flags are unchanged.
Whole4825 becomes4646 B, gain179, leaving550 B above4096. A fixed first cost
is followed by representative model/Board comparison and selected execution.
The independent64-bit fixture observes3338 Board pairs,10504 refreshes,
13828 activity pairs and581 legal children, including both-color captures,
EP, castles, four promotions/promotion captures, parent/path hashes and actual
depth2 model consumption. Mate/stalemate/dead/halfmove and mate priority pass.
The compiler's original warnings remain preserved; warning-clean/SAN is not
claimed. One maintained --dev build then reproduces shipping2 and old DEV2,
matching the entire first-cost tuple. The unchanged selected verifier passes
quit/EOF, eight legal GO, three TIDs, native/private-path restoration and
physical exit. Original groups settle before leader reap, forced0/owned0.
The frozen pre-promotion index4815 B is
`a6624376a08a8c5de853fc8fb44e34a0a853e51ee9bbffe9bea64514e70ae0f1`;
maintained final index5983 B is
`31eafbe64b7f5a0c19171bb5b9cb3262e645f4de7d29ed304f25084e60a4e114`.
Maintained reproduction and future CI retain separate receipts. No training,
new data collection, equal search trace or strength acceptance is inferred.

## Four local names, fused D rays and optional A PALS: 2026-10-24

The subsequent fixed-nice24/annotation checkpoint `5f2cade` also passes
C/Rust in [engine CI40022464371](https://github.com/daejunnom/Rove4k/actions/runs/40022464371)
and Node22/24 in [repository CI40022464392](https://github.com/daejunnom/Rove4k/actions/runs/40022464392).
Actual checkout `11fd55e5acb92671413a49464e293458edc20592` has tree
`55ddf6518f0fac3e432de691aa65ed8c86abf02a`, equal to that head. The972250 B
C artifact matches API size/digest; ten named build/runtime reports confirm
F4350, unchanged F84360 and APALS6677, and optional4319/4045. Final CI index
19454 B has SHA256
`922163e6e0d221d54dc738de4b309045003cd54329696fa355802c98f4cd609c`.
That CI precedes the later A keyword/E composition changes.

The shared `8fc23dd` checkpoint passes C/Rust in
[engine CI40021134454](https://github.com/daejunnom/Rove4k/actions/runs/40021134454)
and Node22/24 in
[repository CI40021134449](https://github.com/daejunnom/Rove4k/actions/runs/40021134449).
Its actual checkout `c31504aa504328c7672eefc30d084585bbed95b9` has tree
`090238737343a8456c334b997664774550c481be`, identical to that head.
The C artifact971978 B matches its API size and SHA256
`4b85a9d02c737be58e261cac46993b979022e844d6e03178f9b5bef295da90e6`.
This CI includes the new optional A PALS step and D/F/F8 changes below;
the subsequent full-F nice24 update retains separate local qualification.

The preceding `15aa9be` checkpoint passes C/Rust in
[engine CI40003349245](https://github.com/daejunnom/Rove4k/actions/runs/40003349245)
and Node22/24 in
[repository CI40003349299](https://github.com/daejunnom/Rove4k/actions/runs/40003349299).
The actual engine checkout `9728a5ee9f35f57a2d3ae37e5e49e4f6252e3cb7`
has the same tree as that head. Fourteen named artifact reports confirm its
B/C/E, full F, F8 and optional F outputs. Those jobs precede the changes below.

Full F now shortens four remaining local bindings at fourteen physical tokens,
including three owned macro arguments. The declaration/reference graph has
the same 251 declarations and 2310 reference edges apart from the four names;
protected gaps and the full inverse are checked. Source8167 becomes8153 B,
bootstrap9089 becomes9075 B, and the complete file4369 becomes4353 B, gain16.
The entire18576/a9e5d648 native remains identical. An ordinary --dev build
reproduces shipping twice and the unchanged DEV control twice. The original
selected verifier passes quit/EOF, eight legal GO, three TIDs, private native
restoration, reader completion and physical exit. Both optional F tuples remain
entire-byte identical in two reproductions each. The final local index9580 B is
`90c5c7cf76f9a44ebc18a68999c23b279fdef310c84276db9cfcc393e82453fd`.

F8 v5 specializes this actual8153 B input through the same six resource roles,
producing8178 B source and9110 B bootstrap. Whole4381 becomes4360 B, gain21;
the entire18576/d2bec657 native is unchanged. Two ordinary reproductions match
the first cost. Existing positive assertions pass two quit/EOF sessions,
eight legal GO, nine persistent TIDs, all eight workers with positive CPU
deltas, strict stdio-only FD/no-children, no-WX, nonexec main stack, reader
completion and physical exit. Guard counts/sizes and final scaling are not
asserted. The explicit closure includes the new F helper and builder; the
consumed D positive function body remains byte-identical after its selector
update. Final index5219 B:
`1a1f084abe6a516aad47fc4b954e734c73bff41fec70fe4fae23f43deb4c89db`.

D scalar now uses a fused mailbox-ray walker only in its shipping branch;
HQ and DEV select the original walker. Canonical native sources are unchanged.
Scalar5836 becomes5717 B, gain119; HQ6037 is entire-byte identical to before.
The compiled scalar native7388/395fea4d is distinct from the restored image
with zero232/b2982877 and whole own-ELF5717/759f10c7. The prior independent
402-state/51456-attack and three perft oracles qualify the changed walker.
Ordinary production reproduces both native/packet/own-ELF forms twice; the
existing positive bodies pass four quit/EOF production sessions and12 legal
GO, three TIDs, actual worker activity, mappings, FD/children and physical exit.
Initial BSS/padding zero is observed before original entry in the separate
5740/6060 B CHECKPOINT audit files, not directly before the production entry.
Direction-major, near-to-far visitation changes move order; equal timed search
or strength is not inferred. Final index13011 B:
`51cbde5caf816e86ed4880b98c9d17eeb7c1c658a69b5784d537c8f301f74c80`.

Optional A `root-pals-feedback` extends the actual NORMAL-slot source with
completed score/reply reuse, root-perspective counterreply diagnostics,
same-first unrestricted Repair and rechecking of the challenged reply before
root acceptance. Diagnostics do not become normal root bounds or learner
updates; original deadline, epoch, TT ownership and callback drain remain.
This is new search functionality:15535 B source and whole6677 B,1545 B above
NORMAL5132, rather than a same-behavior compression gain. Ordinary production
reproduces two shipping tuples and two unchanged DEV controls; selected
quit/EOF sessions pass eight legal GO, three TIDs and physical exit. Build
154265/569b0c75 and runtime4752/aaa2ab1e retain their actual observations.
One fatal-UBSan observer compile and two bounded actual-main runs now observe
1154 direct NORMAL acceptances,12 completed-depth bests from direct slots and
40 actual counterreply searches. All40 are nonrefuting; Repair/recheck execution
and bests from Repair remain unobserved. Helper TT payload writes and drain
errors are zero; active quit and incomplete-depth rejection are observed.
Scores/slots/TT are not injected and no further coverage search is run. These
observations do not claim branch-complete validation. Final index7259 B:
`a9ecf5142303121ab8fa8748bb2525de27a21803b6e9f3125f92760028b4cb06`.
The new optional policy is accepted by the fresh-archive CLI (fresh execution
not run) and passes the shared8fc23dd CI selected step. Loose4525, hint5151
and NORMAL5132 remain unchanged.

Two bounded full-F codec comparisons retain separate first-cost evidence:
nice24 yields4350 B, gain3 over4353; nice32 yields4354 B, loss1. Both restore
the entire same9075 B bootstrap in Python and xz. The fixed nice24 is now
maintained: an ordinary --dev reproduces shipping twice and old DEV twice,
then the unchanged selected verifier passes the new wrapper's quit/EOF,
eight legal GO, three TIDs, exact native restoration and physical exit.
Source/native/bootstrap remain entire-byte identical. F8 only updates its
upstream F builder provenance pin: it never calls/imports that builder, and
its own input, code, codec and output tuple are unchanged; no local F8 rerun
is claimed. The original F8 producing closure/receipts remain frozen.
Nice24 final index7588 B:
`4945785c335b97e69a449341553fcdb80dac3a6faab291e04a60187dbc08c356`.
The later E19/mailbox composition above now costs4646 B after its own
model/search/runtime admission and maintained reproduction. It is included
in the current table. No foreign source is vendored.

A separate D number-parser threshold experiment removes one64-bit division
using the successful-digit invariant and LLONG_MAX=10q+7. Native7388 becomes
7356 B, but the fixed packet4580 grows to4595 B and whole5717 to5732 B,
LOSS15. Loader size remains1137 B and the complete zero232 image restores
exactly. Only one candidate compile/encode/production-loader build is run;
there is no baseline/HQ/DEV/engine rerun or adoption. Smaller machine code is
not treated as a smaller submission file.

All local original commands above settle their groups before reaping retained
leaders, with forced cleanup and remaining owned handles zero. These are
bounded functional and resource observations, not strength acceptance. The
remaining full A-F work is an eligible full-feature file per family (D own-ELF
required), selection/execution of final resource and ISA profiles, current-file
games and final recommendations. Generic C/Rust already implement all five
parallel policies; compact integration is optimization work, not a missing
generic implementation or a required Cartesian product. The old target512
short-search evidence belongs to `de5676d`, not the changed current sources.
Training/data collection, AWS/paid resources and scheduled work remain excluded.

## c4ke-inspired source compression: 2026-10-24

The external reference is citrus610/c4ke at
`ca95d3ac5e59f4759534dffb7ab1b28afa922d74`. Its
[minifier](https://github.com/citrus610/c4ke/blob/ca95d3ac5e59f4759534dffb7ab1b28afa922d74/minifier/mini.h)
inlines existing object-like constants and assigns short identifiers by scope
and frequency. KEYWORDS excludes language keywords from renaming; it does not
generate keyword macros. Its frequency objective does not measure LZMA cost.
The current [UCI implementation](https://github.com/citrus610/c4ke/blob/ca95d3ac5e59f4759534dffb7ab1b28afa922d74/src/main.cpp)
still uses string/getline/stringstream, first-character command dispatch and
fixed input-order assumptions. Rove's shipping paths already use C and a
main-owned token cursor. Exact command matching, arbitrary clock-key order and
existing input draining remain. No foreign engine source or scripts enter Git.

A later fixed three-entry dictionary stores `static `, `pthread_` and
`atomic_` as absent single-byte markers inside F's C literal, then restores
them in the actual compiler-input expression. It preserves the complete8094 B
C input and the surrounding bootstrap AST/control flow. Bootstrap9016 becomes
8687 B, but the same complete-file codec gives4321 versus4317 B, LOSS4.
Strict Python/CLI bootstrap restoration and complete C reconstruction pass;
native compilation and engine execution are not run for this rejected form.
The smaller raw representation is therefore not adopted. Its external final
index4181 B has SHA256
`cb0f08dde4e025194dae8dfcc35988b8456a704134fdc77fc8066b51421a2fde`.

Sharing just the two exact `uci`/`isready` response output statements is also
measured on the later7979 B F source. Both exact comparisons retain their
short-circuit order; the leading character selects a response only after that
exact match. Source becomes7957 B and bootstrap8879 B, but whole4304 becomes
4313 B, LOSS9. Native changes and only compile/strict restoration run. This
form is rejected rather than substituting c4ke's first-character dispatch.
Its external final index10411 B has SHA256
`8a853dbc650246ac167a8d0fde35a1c6332dc2fd92b291a74f2f0107a4b62501`.

The4K-specific rules are rechecked on2026-10-24 at
[TCEC4K Rules, revision7853](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853):
one file at most4096 B, startup within60s without leftover files, the smaller
UCI subset and tolerance for unsupported tournament commands. The ELF section
separately prohibits external programs. This check does not add ordinary TCEC's
full UCI surface or runtime resource options to shipping entries.

Two later Python module-alias costs keep the actual full-F C/native fixed:
signal→a makes bootstrap9075→9025 B but whole4350 is a TIE; adding
subprocess→b makes bootstrap9003 B and whole4354, LOSS4. Neither is adopted.
Likewise D's one post-BCJ operand-stream split preserves the entire native and
restored image but grows packet41 B and loader/header87 B, whole5717→5845,
LOSS128. Only data inverse and loader compilation are run; that loader is not
executed. These fixed measured losses remain external rather than being
silently retried or used as evidence for the selected files.

The maintained common B/C/E transform replaces only the four admitted integer
macros PLY128/MOVES512/HISTORY4096/MATE30000 after the previous setter stage.
It removes their definitions and inserts the exact unsuffixed integer tokens
at fixed uses, with protected gaps and a full inverse. B/C/E sources decrease
10062/9612/9951 to9981/9527/9866 B. Their complete files decrease
4991/4815/4865 to4955/4778/4825 B: gains36/37/40 B. Full-header preprocessor
tokens match, including C's late SIMD header, and all three native files are
entirely byte-identical to their predecessors. Three ordinary --dev builds
reproduce six shipping tuples and six unchanged DEV controls; the original
selected verifiers pass six quit/EOF sessions,24 legal GO and three TIDs per
session, actual restored images, reader completion and physical process exit.
The frozen local promotion index16963 B has SHA256
`a66ffc0856a82e23e74121b760988c3c007a687ebf563dc6505caae6dad8142d`.

Full F adds one17-byte `#define H return` after its seven includes and replaces
42 keyword tokens. Source8360 becomes8167 B, bootstrap9282 becomes9089 B,
and the complete file4378 becomes4369 B, gain9. Entire preprocessed output and
the18576/a9e5d648 native are unchanged. Exact-input,43-span/44-gap and inverse
checks limit this to the admitted full source. Ordinary --dev reproduces two
shipping tuples and two unchanged DEV controls; the unchanged selected verifier
passes quit/EOF, eight legal GO, three TIDs and physical exit. Optional selected
4319/4045 source/native/bootstrap/whole remain byte-identical in two ordinary
reproductions each; their separately generated full references use8167 B.
No new optional runtime is claimed. The frozen execution index15476 B is
`c9bf754fd3a8162f19bb5b3d2862bee632d16eeae29713acc3c1445ea77c57dc`.

F8 v4 explicitly specializes the new8167 source through the same six resource
roles, producing8192/100fcb8a source and9124/9429c105 bootstrap. The complete
file4392 becomes4381 B, gain11 at its separate unchanged nice24/header73
recipe; its18576/d2bec657 native is entire-byte identical to v3. One ordinary
build reproduces both tuples, then the original positive assertions pass two
quit/EOF sessions, eight legal GO, nine persistent TIDs, all eight workers
with positive CPU deltas, strict FD0/1/2/no-children, no-WX, nonexec main stack,
private-path removal, reader completion and physical exit. These checks do
not assert eight worker guard counts/sizes or establish final target scaling.
The builder also settles child groups while their original leaders remain
unreaped, covering publication, pending-signal delivery and monitoring with
one cleanup boundary. Normal execution uses this corrected source; fault
injection is not performed. Build20072 B and runtime71338 B have SHA256
`ba38dad6aa04c65701bc8f8abbe2f45c5f09dbde2d6b1d598b99655c663d1252`
and `1f34a6c93e2f8430282031284b3220c4d5fde68fa20c134528ea108f48d27af4`.

Measured alternatives retain separate evidence: six keyword aliases yield4372 B;
adding seven API aliases yields4373 B; the exact clock-suffix pointer rewrite
alone yields4383 B, LOSS5, and combined with return yields4375 B,6 B worse
than the selected4369 B. These alternatives are unadopted. Shorter raw source
does not imply a smaller compressed file, and individual gains are not summed.
Fragile textual comment/arithmetic stripping is not imported as a general C
transformation. Scope-aware frequency reassignment was still a proposal at
this earlier checkpoint; the later maintained A/F mapping checkpoints above
supersede that status.

All original local commands close normally with retained leader identity until
group members are absent, then reap; forced cleanup and remaining owned handles
are zero. These checks establish expression compression and bounded runtime
behavior, not equal timed traces, strength or final hardware scaling. The prior
08893b3 checkpoint passes C/Rust in
[engine CI39924735357](https://github.com/daejunnom/Rove4k/actions/runs/39924735357)
and Node22/24 in
[repository CI39924735573](https://github.com/daejunnom/Rove4k/actions/runs/39924735573).
That result predates those source changes. The earlier4369 B full F file was
273 B above4096; current sizes appear in the summary above. The full A-F
objective remains open.

## Shared B/C/E setter and actual NVCompact replay: 2026-10-23

The maintained shipping-only setter transform shares remove/store/add phases
while preserving each family's feature representation and update order. It
removes a setter-only leaf, visits nonzero old/new pieces in phases-1/+1,
stores the mailbox once between phases, and updates the new king binding
last. Each family has two exact spans, three protected gaps and a full inverse.
Canonical inputs, DEV, previous transform guards and fixed resources stay.
Raw B/C/E decreases90/54/54 B; complete files decrease4997/4825/4869 to
4991/4815/4865 B, gains6/10/4. Both shipping reproductions and both unchanged
DEV controls pass for each family. Unchanged selected verifiers pass a total
six quit/EOF sessions,24 legal GO, three startup TIDs/session, new native
restoration and physical exit. Products run as WSL user stemxstudio; original
handles are reaped with groups absent and no forced cleanup. This does not
claim equal timed search traces, new model qualification, strength or4KiB.
The local promotion index10277 B has SHA256
`97df08a1355ef8c02464567a3d5c459b0c37c58d2ad712e6c748c0e9f8769304`.

The preceding A NORMAL checkpoint6c6a117 passes C/Rust in
[engine CI39923513818](https://github.com/daejunnom/Rove4k/actions/runs/39923513818)
and Node22/24 in
[repository CI39923513820](https://github.com/daejunnom/Rove4k/actions/runs/39923513820).
Actual checkout2371a2bb187e119928e1e6d84040e229f0e4c902 has tree
3d3e73d5db6053feea2937a37ae3969653f89846, identical to head6c6a117.
Named A NORMAL build/runtime reports confirm5132 B, two shipping and DEV
reproductions, quit/EOF/eight GO/three TIDs and physical exit. The new step's
actual UID is1001, distinct from local UID0. Artifact digest/size matches API.
Its final CI receipt5601 B is
`38b45bf861645ca1abd638a4834eef2c89812d16c689602026e74f2320e4a537`.
That CI predates this B/C/E source change; this checkpoint needs its own CI.

The previously prepared NVCompact0.6.0 Rust CLI is actually used twice on the
current full-F bootstrap9282/7a8c791f, distinct from the earlier9307 input.
For fixed BT2/nice16, depth8 gives4380 B (LOSS2) and depth32 gives4378 B
(byte-identical TIE). Two owner-authored exact-recipe descriptors are replayed;
this is not an automatic portfolio search. Python whole-byte/EOF/trailing
checks, independent xz restoration and actual NVC whole-file reproduction
pass. Native compile, baseline encode and engine runtime are not repeated.
The original4378 B file remains. External final index20802 B:
`5a6a8bd4019e141236e2a2eb1a3c88755e12e8049d302623c542f72056a663a6`.
All nine commands close naturally with groups absent. A static unused cleanup
branch's potential PGID identity issue is retained in the external NOTE;
no signal or forced cleanup occurs in this run. That supervisor must be
corrected before future reuse; original results are not rewritten.

The separate native-payload/memfd wrapper restores the full existing18576 B
native exactly but costs7340 B: header436 plus XZ6904. It is not adopted.
Full F's setter-phase candidate also remains unadopted at4384 versus4378 B.
D scalar5717 and A NORMAL profile8/5122 retain separate experimental status.
Their costs do not change the maintained default table. All default families,
full F included, still exceed4096 B; final compact policies, profiles, scaling,
candidate games and eligible submission files remain open.

## Direct A NORMAL reuse and new compression costs: 2026-10-23

The optional maintained A `root-normal-slots` policy costs5132 B. It is an
alternative to hint/leader-Repair5151, while default Loose4525 and its DEV
control remain unchanged. A helper runs the same A NORMAL evaluator and
ordinary selective policy at the requested child/depth/full window. A completed
valid nonstopped slot supplies leader `l` directly; other slots retain local
PVS. Private ordering/history/ordinary LMR variation is allowed. This does not
claim identical private searches, formal minimax or equal strength. Helper TT
payload writes remain blocked, and round/job callback drains precede reuse.

One ordinary build reproduces two shipping tuples against the fixed first
cost and two unchanged DEV controls. The unchanged selected verifier passes
quit/EOF two sessions, eight legal GO, three startup TIDs, actual new native
and physical exit. One fatal UBSan compile/runtime observes243 completed
helper publications, direct leader consumptions, local-child bypasses and
post-stop-gate acceptances. Direct values improve root score/move five times;
three completed-depth commits retain a direct-slot best. Actual stopped
state4 take/fallback/root-depth rejection is observed three times. Helper TT
payload writes and handoff/drain/commit-value errors are zero. These local
products used explicit WSL user root; unprivileged/permission acceptance is
not established. Direct-ready/stop races and invalid/score-range rejection
remain unobserved. The final external index is15879 B,
SHA256 `3849f7ffa6d943529fa3f8e348656c1863ad52246fbd8fdaf0c46a4ee23e8728`.
CI now includes this optional policy separately and logs its runner UID;
registration is not a claim that this new checkpoint has passed CI.

External first-cost candidates, before runtime promotion, are B4991 (-6),
C4815 (-10), E4865 (-4), D scalar5717 (-119), and an eight-worker A NORMAL
profile5122 (-10 versus fixed-two NORMAL). D changes slider visitation order;
the A profile changes resources and callback accounting. Neither is an
equal-search compression claim. Full F's setter-phase source shrinks41 B but
whole grows4378 to4384 B, so it is not adopted. Native-payload deployment and
the current full-F bootstrap's prepublication-NVCompact comparison are separate
bounded experiments. No unmeasured combination gain is added to these costs.

The full A-F objective remains open: each default family is above4096 B,
compact PALS/groups/hybrid integration and final resource/strength comparisons
remain. Reduced-feature F4045 is not acceptance of default full F. Generic
C/Rust policies already exist; these compact integration gaps do not erase
their implementation. Training, AWS, paid resources and schedules are excluded.

## Current acceptance state

The original full twelve-core comparison used `de5676dcbc498d77477c66064aca926633c851ff`.
Its [Linux CI](https://github.com/daejunnom/Rove4k/actions/runs/39339036826)
passed both C and Rust jobs. The immutable local rebuild passed 144/144 behavior
groups, independent byte reproduction of all 24 native forms, and four bounded
A/F C-versus-Rust games. The sections below preserve checkpoint results as
history. That full comparison does not qualify the source or artifacts of a
later changed head.
The later source/tooling checkpoints `5e24f2a` and `a681ff8` also pass both
language jobs in their respective exact-head CI runs
([5e24f2a](https://github.com/daejunnom/Rove4k/actions/runs/39340690254),
[a681ff8](https://github.com/daejunnom/Rove4k/actions/runs/39342301394)).
The compact-portfolio checkpoint `830eaa0` also passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39345975382),
including the new standalone D checks and Rust structural unit/reproduction path.
The process-lifetime follow-up `df5c1d1` also passes both language jobs and
repository lifecycle checks in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39346330566).
The consumer/layout checkpoint `d7a38d7` also passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39348805876),
including the independent tiny Rust builder, rule, process and clock contracts.
Its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39348805878)
also succeeds. Later local experiments below retain their own exact artifact
proof; this CI result is not relabeled as a run of a future head.
The D-composition/priority/signal checkpoint `147d9e2` also passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39349918237)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39349918247).
The Rust-stream/semaphore checkpoint `b2bf5ce` also passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39351271963),
including the new actual Rust stream, resource-binding and controlled semaphore
steps. Its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39351272214)
also succeeds.
The minimum-UCI/visitor-cost checkpoint `fce70d1` also passes both language jobs
in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39352032977)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39352032876).
The newer locally qualified candidates below retain their exact source and
artifact receipts; that completed CI is not a result for a later head.
The maintained-A/no_std-Rust-D checkpoint `ca3aae5` passes both language jobs
in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39354935832)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39354935728).
That run actually regenerates the 5,207-byte A file and admits both exact
16,824-byte Rust D images before runtime and controlled production tracing.
The maintained-portfolio/A-composition checkpoint `4e3af24` passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39358129123)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39358129198).
It regenerates the 5,140-byte A, the maintained B/C/E/F wrappers and both
maintained C D own-ELFs, then runs their selected files and restored images.
Both no_std Rust D paths also retain their actual runtime/trace checks.
The B/C experiment-source checkpoint `7d86a07` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39359052804)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39359052729).
Its ordinary maintained entries are exercised; the separately recorded B6155
and C5947 experimental qualification is local evidence, not an additional CI step.
The maintained-C-cache checkpoint `829f27d` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39360106393)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39360106274).
This run regenerates the promoted C5947 and executes that exact selected file.
The maintained-A-startup checkpoint `39cab5e` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39362161257)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39362161296).
It regenerates the 5,129-byte A and exercises the maintained entries.
The later finite-D/F/Rust-ingress checkpoint `b2ba5ae` passes both language jobs
in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39364246525)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39364246190).
It actually regenerates and exercises F5407, D7540/7800 and both Rust D16816
production paths. The separately qualified source-spelling experiment retains
its own cost/runtime evidence; it is not an additional CI step.
The maintained-B/C/E-spelling checkpoint `7910a33` passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39365629437)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39365629402).
The C job actually regenerates and runs the promoted B5955/C5723/E5679 entries.
The independent packed-Rust checkpoint is source-only in this CI claim.
The source-composition checkpoint `418435c` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39367412574)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39367412571).
Its B target/alpha, D metadata layout and Rust constructor experiments retain
their separate local proof scopes; these are not additional CI executions.
The maintained-F/qualified-composition checkpoint `8fc4267` passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39368674853)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39368674790).
The C job actually regenerates and executes F5179. The A/F, D phase/composition
and Rust data8 experiments below retain their separate local evidence scopes.
The maintained-A/D checkpoint `1f35a6e` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39370590464)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39370590452).
It actually regenerates and executes maintained A5072 and D7478/7718. The
separately recorded E fusion loss is source/cost evidence, not a CI engine run.
The maintained-A/F-storage checkpoint `23e6482` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39372260910)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39372260921).
It regenerates and exercises A4980 and F5083 with their exact existing native
images. The B dead-bb neutral cost and C composition first cost retain their
separate local evidence scopes; their candidate engines are not CI steps.
The C-proof/D-latch-cost checkpoint `9cf8cdf` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39390557965)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39390557983).
Its new experiments retain their local qualification/cost/failure boundaries;
they are not additional engine CI executions.
The maintained-C-composition checkpoint `034e9d8` passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39391598903)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39391598852).
The C job actually regenerates and exercises the maintained 5,687-byte entry.
The fixed-macro-loss checkpoint `c7be9ea` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39392239296)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39392239338).
The A/F macro experiment remains a local cost-only loss, not a new CI engine run.
The maintained-B-storage checkpoint `2a0d99a` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39393850340)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39393850575).
The C job actually regenerates and exercises the 5,851-byte maintained B entry.
The D-publication checkpoint `1c8be9d` passes both language jobs in its
[exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39395877875)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39395877918).
The new D output-reservation observation remains a separate local runtime
result; the CI does not execute that new experiment or promote its candidates.
The maintained-D/source-cost checkpoint `a3546f1` passes both language jobs in
its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39399550146)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39399550128).
The C job regenerates and executes the new 7,457/7,707-byte maintained D pair;
the separately frozen A/F costs and failed C/E observation remain local results.
The maintained-F/source-composition checkpoint `71a0791` passes both language
jobs in its [exact-head CI](https://github.com/daejunnom/Rove4k/actions/runs/39404347515)
and its [repository lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39404347797).
The C job regenerates and executes the maintained 5,051-byte F file. Other
source-cost experiments retain their local execution scopes.
The fixed-codec/source-comparison checkpoint `647f04a` also passes both jobs in
its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39405755104)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39405755067).
Its source-only codec experiment is not an additional runtime CI execution.
The maintained-F-scope checkpoint `195b541` passes both language jobs in its
[exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39408227153)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39408227165).
It regenerates and exercises the maintained 4,839-byte F file.
The maintained-A/B/C/E-scope checkpoint `ffb2799` passes both language jobs in
its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39410522104)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39410522081).
It regenerates and exercises A4846/B5558/C5395/E5400/F4839. The separately
qualified context-D experiment and encoder remain local evidence; this CI
still regenerates and exercises the maintained old-codec D7457/7707 pair.
The maintained-context-D/F-member checkpoint `e266ea5` passes both language
jobs in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39413637855)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39413637981).
It regenerates and exercises the new maintained D6401/6614 own-ELFs and F4814,
alongside A4846/B5558/C5395/E5400. Later cost-only candidates remain separate.
The subsequent source-cost checkpoint `03018dd` also passes both language jobs
in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39417816887)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39417816891).
It exercises the same maintained entries; the newly recorded experiments are
local cost evidence and are not extra CI runtime steps.
The following cost-source checkpoint `6cf2ff1` also passes both language jobs
in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39419480599),
[repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39419480600)
and the [NVCompact checks](https://github.com/daejunnom/Rove4k/actions/runs/39419480680).
Those jobs still regenerate the preceding maintained entries, not the later
EP-only F or reset/BCJ D candidates under local qualification below.
The BCJ-cost/ownership checkpoint `b8bb037` also passes both language jobs
in its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39420784684)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39420784662).
It still exercises D6401/6614 and F4814; the subsequent normal-source promotion
requires its own exact-head result.
The shared traversal/storage checkpoint `4a4cf62` passes both language jobs in
its [exact-head engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39455386213)
and [repository lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39455386245).
It regenerates and exercises A4762/B5371/C5159/D6165/6345/E5281/F4730.
The later PALS and hardware-CRC work below retains its own source and runtime
boundaries; those earlier CI runs are not relabeled as results for new bytes.

The D HQ-history checkpoint `cf4a152` passes both language jobs in its
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39594373382) and
Node22/24 [repository checks](https://github.com/daejunnom/Rove4k/actions/runs/39594373244).
Both actual language-job checkouts use merge9f25a035, whose tree equals that
head's tree. The common fallback/QS changes below have their own later local
qualification; that completed CI is not relabeled as a run of later bytes.

The shared fallback/QS checkpoint `28edec8` passes both language jobs in its
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39596928208) and
Node22/24 [repository checks](https://github.com/daejunnom/Rove4k/actions/runs/39596928230).
Both actual engine-job checkouts use merge0c2a7a7a, with the same tree as that
head. The subsequent B/E history and resource8 local qualifications below
retain their own identities; this CI result does not qualify later bytes.

The B/E history and fixed-eight-worker checkpoint `726158f` also passes both
language jobs in its [engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39601974098)
and Node22/24 [repository checks](https://github.com/daejunnom/Rove4k/actions/runs/39601973964).
Both engine jobs actually check out merge `21c2d152`, whose tree equals that
head. The C job executes the new fixed-eight-worker positive step. These results
precede the additional generic fixed-root source path described separately.

**F's opt-in material/move-TT file is locally reproduced and exercised at
4,045 bytes; default full F is now 4,350 bytes.** This optional reduced-feature
size result does not complete default F or the A–F portfolio. All twelve
cores have functional evidence, but portfolio completion still requires source
reduction, D's eligible own-ELF artifact, final candidate comparisons and games,
and selected profile/resource and target-hardware evidence. The first matched
C/Rust structural comparison and the twelve original target512 short searches
now have their own bounded evidence; these do not accept future smaller cores.
Startup-only evidence and small-profile games have the narrower scopes below.

The current maintained local entries are listed here; older tables below record
their historical checkpoints. The fixed local profile has two search workers
plus the controller and TT_BITS=18. These are not final target profiles.

| Family | Complete file | Remaining above 4,096 B | Current source decision |
| --- | ---: | ---: | --- |
| A | 4,489 B | 393 B | EP legality shares the existing maker on initialized legal doublepush states, with bounded nesting2 and provisional hash/context discarded; scoped fixed seven-binding names; default Loose reuses completed depth -1 as a mutex-published job token while preserving the null startup sentinel and shared epilogue; earlier J/return and L/int aliases retain their full-header CPP/native identity proof separately; full HCE/PVS/QS/full-key TT/history/continuation/correction/SMP and all three optional root policies remain; main-owned token cursor, fixed resources, guarded original literal chain, strict fixed2 depth selector and individual stdio locking |
| B | 4,950 B | 854 B | EP normalizer reuses the actual legal maker with nonzero result101 and king-safety guards; preceding I/int alias covers99 tokens with full-header CPP and entire native identity; worker-owned job reset, calloc-covered plain TT zero stores omitted with explicit atomic flag initialization; TO127 SEE promotion predicate and fixed TT18 casts; existing hybrid attackers/singular, full search/learners retained; made-child continuation row passed through PVS and same-position singular verification; literal include gaps and overlong-line drain compacted; clock-first SEE poll; cancellation timing changed; compact environment snapshot; fallback queried from the immutable completed root only when selected best is zero; private history length derived from immutable published job base plus ply; private piece-plus-six helper inlined at its two consumers with complete native identity; singular-depth temporary and empty shipping instrumentation branch removed; adjacent HCE int declarations merged; three walker forwarders removed with explicit full-mask/Boolean/count consumer domains |
| C | 4,628 B | 532 B | Late inlining removes four integer macros reintroduced by the cross stage with full-header token and entire preceding-native identity; completed-depth tokens replace separate worker epoch state with the startup sentinel retained; current signed-net eight-lane HCE and actual128-bit madd/four signed32 sums combine with the smaller full common A-derived mailbox/PVS/runtime, explicit -mavx2 target; older architecture native identity is not claimed; exact incremental evaluation, king-capture/move-buffer/QS draw guards, full-key TT, three learners and persistent SMP remain; selected compiler/literal adapter consumes the original C package and old DEV is unchanged |
| D scalar / HQ | 5,581 / 6,037 B | 1,485 / 1,941 B | Scalar H28-private decoder shares initial prefill and subsequent refill with unchanged packet/native/restored image; transient512 MiB table remains and old startup/RSS observations keep their prior scope; HQ retains H24; shipping scalar fused mailbox rays with direction-major near-to-far visitation; HQ/DEV original walker; HQ-only history length derived from immutable job length plus ply; exact clock/inc parsing and ordered K/Q castling branches shared; consumed sort-prefix writebacks omitted; capture-only Move bit3; full-key aligned atomic16 TT with a shared finite-stage asm body, HCE/PVS/QS/learners, explicit SSE4.2/CX16 and fixed21 guarded own-ELF retained; exact fused-scalar body232 class restores dormant internal ELF metadata as zero while preserving body addresses |
| E | 4,586 B | 490 B | Direct64-square successor preserves move/attack/material visit order and loop bodies; completed-depth tokens replace separate worker epoch state with the startup sentinel retained; actual ranking loop reuses decoded coordinates/mover and keeps five ordering features and19 independent coefficients; current exact untrained E19 logical19/physical21 model bodies and all five ordering features combine with the smaller full common A-derived mailbox/PVS/runtime; old-E search traces are not an equivalence claim; full-key-bound TT, exact model evaluation, history/continuation/correction, persistent SMP, terminal/draw guards and fixed resources retained; final int/return aliases retain the entire preceding native; previous E chain remains the guarded model/input authority and old DEV stays unchanged; selected compiler/literal adapter consumes the actual previous package before constructing the smaller bootstrap |
| F full (default) | 4,275 B | 179 B | Exact expansion removes the three-use FROM definition with full-header CPP/native identity; unique quiet-order helper is inlined into its coordinate-owning caller with the entire native preserved; fixed binding-frequency spelling and four-coordinate formatter sharing; packed positional HCE, learners, full-key score/bound TT, full-depth MTD(f)/SMP retained; private TT depth/bound shares one byte with empty0 excluded, worker completed-depth -1 publishes jobs under the existing mutex; history length derived from immutable job length plus ply; nonnegative QS depth, repetition-distance loop, fixed integer macros and plain-int keyword spelling compacted after the no-preadd hash, terminal, correction and source-form stages; compact environment snapshot; default size target remains open; lazy fallback and first-legal quiet-QS standpat cutoff; immutable global job-prefix keys shared while workers store only private path keys; fixed 73-byte stdin/xz header and BT2/16KiB ALONE with nice24; four further local names shorten14 tokens with declaration/reference and macro-argument ownership preserved; compact handler-pair loops, fixed2 completion selector and positional wait timeout; pure HCE rank normalization shares advance/center rank; ASCII unsigned first-digit guard and Linux readonly-open flag spelling compacted |
| F full (fixed8) | 4,284 B | 188 B | Separate eight-search-worker profile with nine startup TIDs; actual F7885 after exact FROM expansion specializes through six roles to7923, including all-eight job-depth reset; full TT/MTD/HCE/learners and condition synchronization remain; unchanged native18576/26182257, fixed nice24/header73; WNOWAIT exit observation and strict task/mapping/activity/lifetime checks pass locally; guard sizes and final target profile remain open |
| F material/noise (opt-in) | 4,319 B | 223 B | Unsigned64 number forms and two fixed TT18 casts omitted; one-state material classifier, fixed material/stateless order and full-bound TT; optional positional HCE/learners omitted; literal include gaps compacted; fixed LP64 mixer literals; compact environment snapshot |
| F material/move-TT (opt-in) | 4,045 B | 0 B (51 B spare) | Unsigned64 number forms; one-state material classifier, fixed material, main-owned token cursor, terminal-loop sharing and coherent atomic64 Move17/high46 plus index18; local size eligibility only, full F and strength acceptance remain open; fixed LP64 mixer literals; compact environment snapshot |

The canonical Rust D native images are16,816 bytes each. The separate maintained
finite Rust shipping entry also has16,816-byte natives with new identities and
11,108/11,476-byte scalar/HQ own-ELFs. Its normal qualification below does not
replace the C D table or establish4KiB eligibility.

## Common worker sharing, full-F square iteration and prepublication NVCompact: 2026-10-22

The preceding fbb33f2 checkpoint passes C/Rust in
[engine CI39761683155](https://github.com/daejunnom/Rove4k/actions/runs/39761683155)
and Node22/24 in
[repository CI39761683062](https://github.com/daejunnom/Rove4k/actions/runs/39761683062).
All four actual checkout logs name ae076c976046b20d2271d733a0b9415164823043,
parents761bdc0+fbb33f2 and tree0844812b2ea9c529c0be04944b21e8de806cbe6f,
identical to the requested head tree. The actual optional-A reports confirm
two shipping/oldDEV reproductions,5151 B and fresh quit/EOF/eight GO/three TIDs.
Frozen CI index19701 B:
`16828fd9c99fcfab780d8fc812303693df9d88702261d69e714ada15158b6983`.
This does not qualify the following source changes at a new head.

One common B/C/E worker transform shares startup and completion epilogues
using a worker-local null pointer as the startup marker. B/E drop their
separate ready counter and initialize pending2; C already used pending2.
Each completed startup or search decrements pending under the same mutex;
only a real job invokes result output. The last startup arrival broadcasts
once instead of twice. Original epoch/stop/drain/flush/partial-create/join
ownership remains; wake ordering, scheduling and timed traces can differ.
Source10179/9700/10041 becomes10152/9666/10005 B, raw-27/-34/-36.
Actual whole5006/4827/4880 becomes4997/4825/4869 B, gain9/2/11.
Each family passes one ordinary --dev and its unchanged selected verifier;
all six original command handles close normally. The earlier12-second outer
cleanup grace limitation is preserved with its successful first-cost result;
the later normal owner uses20 seconds. First-cost index7498 B:
`5f3fd219443861f79d671dd5e6cf01ce36946c3ff57bc159fb6459d016d52da6`.
The maintained ten-file promotion passes six shipping and six oldDEV
reproductions, six selected quit/EOF sessions and24 legal GO with three TIDs,
actual new natives and normal reader/private-path/process exit. Producing and
final95-path closures differ only in six recipe/README completion annotations.
Frozen promotion index10781 B:
`ae193befab40b4b0d60245c4c8e879407d961bf50cfc9d298c11cc97fe10a9b9`.

Full F replaces two valid-square scans with (index+9)&~8, preserving the64
valid0x88 squares in order and exit128. Two spans/three gaps/full inverse
preserve8304 other bytes. Source8385 to8360, bootstrap9307 to9282 and whole
4385 to4378 B give gain7; native remains18576 B with new identitya9e5d648
and .text grows1 B. Existing integer guards remain. The full-only literal
adapter inverses to8385, consumes the prior common/pack path, then forwards
with exact AST byte restoration. HCE/learners/full-key bound TT/MTD/SMP stay.
One ordinary --dev reproduces both new shipping tuples and old DEV twice;
the unchanged selected verifier passes quit/EOF/eight GO/three TIDs/new
restored native/private-path and physical exit. Optional selected4319/4045
and the prior pre-name8538 remain unchanged; optional normal/fresh/SAN were
not rerun. Frozen local promotion index10633 B:
`943c4961a2e6ff54735c62b71a79fdf9fd4179ecaeb2308f7935a3f436951110`.

F8 v3 directly consumes the new8360/b4e8f796 full-F2 source. The same six
resource edits/seven gaps/full inverse yield8385/a9237511 C,18576/d2bec657
native and9317/f80376e2 bootstrap. Its separate nice24/header73 package shrinks
4399 to4392 B, gain7. One ordinary build reproduces both whole tuples against
first cost, then one unchanged-body positive verifier passes quit/EOF, eight
legal GO, nine persistent TIDs, all eight workers with positive CPU deltas,
FD0/1/2, no children, global no-WX, nonexec process stack and physical exit.
The eight-worker active lane runs after F/BCE/NV codec products close. Class,
base-stage and exact input pins change; runtime assertions are unchanged.
The actual F8 call path consumes D tasks()/mapping(), which do not assert
eight worker guard counts or sizes. Raw maps and the separate D guard checks
must not be promoted into that stronger F8 claim. Final target scaling,
strength and4KiB eligibility remain open.
Producing/final62-path closures differ only in recipe/README completion
annotations. Frozen five-file promotion index15407 B:
`a1e2a1b8e4069bc2e3c9ed44905467ac99c089dcb4865df5a3005c4ede569d1f`.

Public npm0.6.0 is already released from main8646205; the current registry
identity matches the newly rehashed stored public tarball and frozen prior
CI-byte-identity record. No duplicate publication is needed. The known
prepublication0.6.0 nativebea92950 is used for two actual bounded replays on
the old full-F bootstrap9307, keeping header73/BT2/dict16KiB/nice16 fixed.
Encoder depth8 yields4391 B, LOSS6; depth32 yields4385 B, byte-identical TIE.
Python measures each once and installed NVCompact replays each owner-authored
single-recipe descriptor once, four actual encodes total. This is not a
tool-generated portfolio search. Both replay wholes and strict restorations
match the measured files; no baseline encode, compile, engine or maintained
recipe change is made. New successor8360/9282 and the older239 unvisited
source subsets remain unmeasured by this lane. Frozen index17342 B:
`59f7639ce0bda93d01bc3851b184cde16bce52d93583eeeac2c2b35b48510f6d`.

The separate external fixed2 direct NORMAL policy now has a first cost:
source10835/bb15535f, native22672/b3700269, bootstrap11789/20b21324 and
whole5132/3b719799. It directly consumes a completed helper slot as leader l,
retaining leader-only TT publication, original deadline and round/job drain.
This adds607 B over default4525 and is19 B below the separate hint/Repair
policy5151; these are different policies, not equal-search compression ranks.
The actual prior output/condition/names literal callback is exercised once,
superseding only the earlier witness-only validation limit. One native compile
and one encode close normally, with old/new Python2/CLI2 strict restoration;
baseline rebuild/encode, engine runtime, SAN and maintained integration remain0.
The earlier source-only report and its provenance limits remain unchanged.
First-cost receipt11115 B:
`836e50353285e48ed1dbe86c455ac93e33062e83e003c18b2b354838e86dfa15`.

## e355078 CI, H30 resources and NORMAL contract review: 2026-10-22

Checkpoint e355078304a13743327cea7fc2d4908833fede4b passes both language jobs in
[engine CI39681953418](https://github.com/daejunnom/Rove4k/actions/runs/39681953418)
and Node22/24 in
[repository CI39681953443](https://github.com/daejunnom/Rove4k/actions/runs/39681953443).
All four actual checkout logs name7e3a9712b0c9586687a514419ec9faa3f3e2c7ba,
parents761bdc0+e355078, tree938738fe697b50eac582494d080925e671a4781c,
identical to the requested head tree. Eight actual B/C/E/F8 build/runtime
reports confirm5006/4827/4880/4399 B and their selected positive lifetimes.
Frozen CI index23159 B:
`c19dc611df4a0d8751fa693b380318fc5e28d1800375a491359ea1d3ea38ad96`.
This success covers that checkpoint; later source and policy work needs its
own qualification.

The external D scalar H30 codec keeps the fixed21 model, native7612 B and
zero232 restored image, but expands context scratch from32 MiB to2 GiB.
Packet4699 to4629 B and loader1137 to1139 B give whole5836 to5768 B, gain68.
It remains1672 B above4096 and is not the maintained H24/default profile.
Two fresh ownELF sessions pass quit/EOF, eight legal GO, three persistent TIDs,
restored RX identity, W^X/NX, guards, stdio/children and physical exit. Startup
ready takes1.858862/1.260983 seconds. Kernel VmHWM reaches1623040/1623168 kB,
about1.55 GiB. The exact2 GiB RW extent is absent after ready, but overlapping
reused address ranges prevent a syscall-level scratch-unmap claim. Initial
BSS-zero observation, HQ H30 and final target RAM/ISA eligibility remain open.
No product rebuild or rerun was needed for this positive lane. A post-run
collector dictionary comparison error is preserved separately; only metadata
collection was repaired. Frozen positive index10621 B:
`7ff5d432edc8054541bb9b2c1452c667ebb45f422fe9a553b7c2f39979ed2034`.

A subsequent source review corrects the blanket private-state-equality premise
in the earlier A root-policy rejection below. ENGINE-PLAN section4 permits
independent worker state, ordering diversity and compatible NORMAL results.
Canonical C NORMAL itself uses private history/continuation/killers/id and
order-dependent LMR; its completion consumer checks generation, first, depth
and applicable bound, not equality of all mutable learners. Rust freezes
evaluation correction while retaining private ordering. F deliberately has
stronger exact-depth/no-LMR semantics. Different evaluators, restricted replies,
role-specific extra reductions and incomplete work still cannot be mixed as
NORMAL bounds. A full-window completed selective NORMAL result is an engine
bound classification, not fixed-depth minimax or equality with a later leader
re-search. Opening helper work before the first child completes is a distinct
speculative root schedule; the plan does not mandate strict YBWC. The old
proposal, branch witness and rejection record remain preserved. This review
does not qualify a direct compact NORMAL implementation or relabel the separate
hint/leader-Repair policy. External contract audit9788 B:
`d7477c4a064847063c26a2dc0e5fdc534c8b6e7325df7202ba1d31ce9202379c`.

The separate optional A root-hint/leader-Repair policy is now produced by a
maintained build-time selector. Default Loose4525 B and its DEV control stay
unchanged. Selected source10873/native22672/bootstrap11827/whole5151 B adds
626 B for the new policy. Ordinary --dev reproduces both shipping tuples and
old DEV twice; the policy-matched selected verifier passes quit/EOF, eight
legal GO, three TIDs and physical exit. One separately instrumented fatal
UBSan build/run of the actual h/R2 records216 ready-hint leader entries and
216 accepted leader scores,9 LMR exemptions and49 leader-owned TT returns.
Helper TT payload writes are zero;11 drains and8 depth commits have no bad
tokens. Active quit finishes with pending/open/busy zero and both worker joins.
These observations do not establish same-Loose results, compatible NORMAL
reuse, exhaustive schedules or strength. Fresh only forwards the policy in
source; its archive path was not executed. Frozen local index11238 B:
`6b5dd3fee179d9d63cb18f379d287188b59d634e3a46581957c11206b83b244c`.
The workflow adds a distinct ordinary build/selected-runtime lane for this
opt-in. New-head CI is pending; earlier e355078 success does not cover it.

## B5006/C4827/E4880 output and late full F8: 2026-10-22

The A4525/F4385 checkpoint61b0d02 passes C/Rust in
[engine CI39679560987](https://github.com/daejunnom/Rove4k/actions/runs/39679560987)
and Node22/24 in
[repository CI39679560935](https://github.com/daejunnom/Rove4k/actions/runs/39679560935).
All four actual checkouts use0319314259d749a4937f4f0af2cab8eafe1fc744,
parents761bdc0+61b0d02 and treee444d82172f23c349bb691ef5be510b0a5be5256,
identical to that head. Six actual A/F/F8 build/runtime reports confirm A4525
and F4385 two reproductions and fresh quit/EOF/eight-GO/three-TID sessions.
F8 retains4442 B and passes closure61, nine TIDs/eight active workers,
strict FD/children/no-WX samples and normal process/reader/group exits.
Nice24/pre-name8538 are separately bound by the exact recipe/build blobs.
Final CI index24190 B:
`1c2a70d6e515f1117cbd4c7d549099ac3f165a5df66722234f28d6569359485a`.

B/C/E each have one new result-output source candidate: fixed2 strict-depth
selection and removal of the outer stdout lock pair, raw-63 B. Single-call
line output and own flush-before-notify/drain stay; main reply interposition,
flush grouping, contention and timing may differ. Their fixed first costs
are whole5023→5006,4845→4827 and4897→4880 B, gain17/18/17. This is separate
from the earlier reply-branch LOSS9. Frozen first-cost index7582 B:
`59600991d0795aae61e963af2fcccff9f0278b436a31519fefb82d2797c9ff5e`.

One pure common output helper is applied only after each family's condition
stage. Each family then passes one ordinary --dev build and one unchanged
selected verifier: two shipping/oldDEV reproductions, first-cost whole-byte
identity, quit/EOF two sessions/eight legal GO/three TIDs/new native/private
path cleanup and physical exit. All six original commands settle normally,
forced0/owned0; B→C→E run serially before the F8 positive lane. Final ten-file
index10268 B:
`f9fdd6ebaaf78753473b5bb33d3cbcbde7ef2d122d5153202ca62612ae57a7de`.

The external late-F8 source proposal takes exact final F2 C8385/acae5c84,
does not repeat private-name conversion, and changes six resource roles.
Its C8410/c415265d is128 B below oldF8 and25 B above F2. Existing nice24,
template947/header73/compiler give measured whole4442→4399 B. The original
cost supervisor exits1 after all compile/encode/strict-restore children have
returned0/reaped/group absent: baseline metadata shadows its signal-handler
dictionary during final restoration. Original script/trace/exit1 are kept;
this is measurement_complete, supervisor_success=false and unadopted at cost
closure. Runtime/normal and old4442 acceptance do not transfer to4399.
Frozen first-cost index9617 B:
`b2285e68784f3408ef625c06caa1f1f9471f024e89011d3dc246eeb8b406c108`.

Later explicit class full-F-late-fixed-resource8-TT18-v2 connects the maintained
producer and consumer to final F2 C8385, omitting the former name pass and
enforcing exact six roles/raw+25. The CI F8 base argument now selects final
main.c. The positive verifier adds class/base-stage/base snapshot identity;
its original startup wait, strict9-TID/eight-CPU/FD/children/no-WX/stack and
physical-lifetime checks remain. One ordinary build reproduces new C8410,
native18576/e735dae1, bootstrap9342/fdf6da04 and whole4399/89f442dd twice,
entire-byte identical to first cost. One positive verifier passes fresh
quit/EOF two sessions/eight legal GO/nine TIDs/eight active workers and normal
exit. Original667/683 both settle rc0/reaped/group absent/forced0/owned0 after
the six B/C/E commands; the first-cost supervisor exit1 remains unchanged.
Final six-file index6901 B:
`75f5cb75e0b0439859eb852a5614279a6bb36bb97ac506fef455bdc2de69b075`.
The producing and final61-file closure differ only in recipe/README validation
annotations. Build/specializer/verifier/workflow and operational expectations
keep their producing bytes. Current4399 local qualification is not new-head
CI, final4KiB eligibility or target-hardware/scaling/strength acceptance.

D's separate full64-key payload-BUSY atomic64 TT candidate grows native
7612→7676/8000→8032 B and whole5836→5864/6037→6070 B, LOSS28/33.
Two native compiles/two encodes/two DATA inverses/two production-loader
compiles close all ten original children normally. Current scalar/HQ
5836/6037 remain; no new candidate runtime or maintained map is admitted.
This proposal changes cache contention/replacement policy and is not lossless
CAS16 substitution. External exact identity/form/layout/model descriptors
preserve compiled-native, zero232 full restored image and ownELF identities.
Frozen cost index17066 B:
`d9d496035ed2ff23d8cfeb79b75bcee7aabcc40914c77b88604e8d63b0c5a74d`.

The external maintained-A root v1 has source/lifetime evidence but cannot
claim leader-compatible NORMAL EXACT from helper-local full-window completion
alone. Leaf HCE scale is equal; private ah/zC/an/id alter descendant ordering
and LMR, and an unretried reduced fail-low can differ. R2 job/first/depth
lifetime does not establish selectivity compatibility. The independent review
11066 B/799dee7306108d9af62ac7b0df6604f3b2d17162e9406d5ed9bb7d4d66e38f25
records a production-integer branch witness, not an executed FEN counterexample.
The v1 proposal/index stay; current maintained Loose source is unaffected.
Normal partial-result integration remains open while a hint/leader-Repair
alternative is developed. These later experiments are outside61b's CI scope.
The separate v2 source-only hint/leader-Repair proposal is10938 B, baseline
8886+2052, with10 spans/11 gaps/full inverse. It uses helper proposal only to
exempt a root-edge LMR and suppresses helper TT writes; leader h/PVS computes
every authoritative score. It is not direct NORMAL bound reuse, and no
compile/runtime/maintained acceptance is inferred from its source review.

## A4525 output, full F4385 expressions and next structural work: 2026-10-22

The preceding32c8efb checkpoint passes both language jobs in
[engine CI39674512872](https://github.com/daejunnom/Rove4k/actions/runs/39674512872)
and Node22/24 in
[repository CI39674512935](https://github.com/daejunnom/Rove4k/actions/runs/39674512935).
All four checkout commits are e12a1d1310617101bb170c4dbe07393191415272,
tree3d252a55de10740671608eb03609a2aede356d1f, identical to32c8efb's tree.
Ten actual B/C/E/F/F8 build/runtime reports confirm that preceding scope,
including fresh F8 closure60, nine TIDs/eight active workers, strict FD/children
and normal exit. This is not CI evidence for the new A4525/F4385 source below.

A's fixed-two-worker output stage reduces C8886 to8821 B, bootstrap9840 to9775 B
and whole4541 to4525 B,429 B above4096. Three exact spans/four gaps/full inverse
replace the depth-selection loop with the same strict-greater/tie-worker0
comparison and remove the outer flockfile/funlockfile pair. The callback keeps
qj through its single bestmove printf and fflush, before completion/drain.
Individual stdio calls lock the stream, but main puts/fflush may interpose
between worker printf/fflush. Grouped visibility, scheduling, contention and
error/signal timing are not trace-equivalent; no active-ready interposition
exhaustive runtime proof is claimed. Search/features and the2-worker pool stay.

The new literal adapter inverts to8886, invokes the unchanged condition/names
guards and forwards again. Compiler stays implicit GNU17/Os/no-pthread, with
the original nice24/header73/FD0 package. Native18576 B has new5fd8f877; whole
4525 SHA256 is2ca2872720c4fe42d936670867319e89a4de3bef87bc7d70ad2657d01fd26135.
One ordinary --dev build reproduces shipping twice/oldDEV twice, exactly equal
to first cost. The unchanged selected verifier passes quit/EOF two sessions,
eight legal GO/three TIDs/new native/private path and physical exit. Both
original commands close rc0/reaped/group absent/forced0/owned0. A has no FD-list
observer, and cancellation causality remains unproven. Separate packed-HCE
source8874 is not composed or costed in this output result.
Frozen final four-file index13815 B:
`02975522580e94892c8c9e363417283facbc5543466b5ec9f1c35af4e7ac8519`.

After the direct-walker stage, seven exact private integer-expression spans
reduce full-F C8410 to8385 B and bootstrap9332 to9307 B. Whole4396 becomes4385 B,
289 B above4096. TT mask262143, ply/depth127 and mate29872 retain their values;
MTD q+(q==d) keeps the original private interval/read contract. Eight protected
gaps and the full inverse preserve the other source. The new native remains
18576 B but changes its entire hash to91d2a5f9; .text6974 grows to6985 B. Neither
raw source nor native text size substitutes for the actual whole-file cost.

The frozen first cost uses one candidate compile/encode, baseline0/0 and
strict Python2/CLI2 restores. One ordinary full --dev build reproduces the
shipping tuple twice and old DEV twice. The unchanged selected verifier passes
quit/EOF two sessions/eight legal GO/three TIDs, exact new native and physical
exit. Optional --dev products4319/4045 and DEV remain entire-byte identical;
their separate full-reference source reproduces8385 B twice each. The four
original commands633/674/709/742 close rc0/reaped/group absent/forced0/owned0.
Final six-file index9955 B:
`9d9f89bae110f47f474320b28e5252a2ed66f7cb25cb0dc102592f47b8d7b580`.
Its first-cost index16379 B is
`f70af407d3d9abbfe9e8968413450424c13684f11bad49dcd2ad9a14bab6c416`.

F8 retains pre-name8538/47353a15, own4442/nice24 and verifier6f407b27.
The new producer helper changes its current source closure to61 files
(base54+positive2+own5). All61 are reread; no new local F8 product is executed.
The earlier60-file local runtime and exact32c8efb CI success retain their
original scope. A future current-head CI must regenerate the new closure.

The B/C/E single reply-branch source proposal reduces each source by22 B,
but fixed candidate compile1/encode1 per family gives whole LOSS9 each:
B5023 to5032, C4845 to4854, E4897 to4906 B. Strict restores pass, all original
commands settle, and no family is promoted or run as a new selected engine.
Frozen external first-cost index7519 B:
`07231d3ffa4e34f41a00f5db3ab3e44f4b0347794cdbcccaf374863575903aa8`.
This finite-context loss does not establish a general reply-sharing result.

The remaining portfolio work includes eligible default A-F files, maintained
compact root/group/PALS/Repair/hybrid integration, same-function language and
combined-feature comparisons, final resource/stack/profile/ISA observations,
scaling, games and recommended submission files. Generic C/Rust already have
the parallel policies; their implementation is not counted as missing. The
accepted plan requires an eligible file per family, not both languages below
4096 B. Training/data collection, AWS/paid resources and scheduled tasks stay
outside the current goal. New D TT and maintained-A root proposals are
source-only and are not qualified by this checkpoint's full-F results.

## B5023/C4845/E4897 conditions, F4396 direct walker and F8 startup: 2026-10-22

One common pure helper applies independently pinned B/C/E condition sharing
after each family's original final C stage. Source changes B10270→10242,
C9800→9763 and E10142→10104 B; whole5032→5023,4860→4845 and4914→4897 B.
B/E retain separate ready counters and startup waits; C retains pending2
startup/decrement/drain. Their original four broadcasts, same-mutex while
predicates, epoch publication, pending0/result/flush/notify order and direct
partial-create shutdown/created-thread join code stay. Additional unrelated
wakes, mutex contention, scheduling and timed results may differ. Existing
nonzero-join failure policy is unchanged, not newly proven. Canonical/DEV,
compiler/codec/header and A/D/F callers remain; C keeps actual nice64/-mavx2.

Each family passes one --dev build (shipping2/oldDEV2) and unchanged selected
quit/EOF two sessions/eight legal GO/three startup TIDs/new native/physical
exit. All six original commands close rc0/reaped/group absent/forced0/owned0,
serial B→C→E. Frozen final10 index11114 B:
`13075fd1b0576194f96cb9c47050cef573fa814ee6baed8e0ee91f0d3120f26d`.
The actual closure is93 unique paths, from family47/44/43; root docs/other
families are outside this producing input scope. A precompile missing-FD0
template-context gate, preparation syntax error and later B-specific closing
schema error are preserved separately; none executes an extra candidate
compile/encode or product retry. First costs use one compile/encode per
family, baseline0/0, with strict Python2/CLI2 restores.

F removes its attack and generation forwarding definitions, reusing the
deleted T name for the static walker to avoid three existing local g bindings.
Six attack and two generation consumers pass the original walker arguments;
Boolean0/1, castling short-circuit, generation order/count/capacity512/abort
remain. Twelve spans/thirteen gaps/full inverse reduce source8469→8410 B,
bootstrap9391→9332 B and whole4410→4396 B. Native18576 B has newc18d793b.
External c/T symbol/arity ABI, frame, stack, trace and timing equality are
not claimed. Full TT/MTD/HCE/learners and the condition stage stay.

F passes full --dev shipping2/oldDEV2, unchanged selected quit/EOF two sessions,
eight legal GO, three TIDs and exact new native/physical exit. Optional --dev
products4319/4045 and DEV stay entire-byte identical while their explicit
separate full-reference source becomes8410 B. After BCE's six commands close,
F's four commands precede a fresh F8 ordinary build and positive verifier.
F8 reproduces its unchanged4442/nice24 products twice, with closure60
(base53+positive2+own5), then passes fresh quit/EOF two sessions/eight legal GO,
nine stable TIDs/eight active workers, original strict FD/children checks and
physical exit. Its count/state startup waiting remains distinct from strict
resource acceptance. The preserved e8 failure and unknown FD3 cause below
are not relabeled by this new local result.

Final seven-file index21437 B:
`14aa8984dfec76fe47ed0251ecba67ea5a3d092bcdeccc336f0b8a41ee605c1c`;
final pins2467 B:
`0e2e21de57eef1f6502faded3c675ea9a33b2e311f5ba9d3433eab7c0cbad025`.
Walker/F builder/F8 verifier retain producing bytes; recipe/README changes
after execution only complete validation annotations. The six F/F8 commands
close rc0/reaped/group absent/forced0/owned0. New local F8 runtime:
`a6445da7f4e8a6ed1a5c4c9555075083ae0e47f6ccea8b3e8bd854697c88bd67`.

Every default remains above4096 B. Final resources/stack, compact-policy
comparison, many-core scaling and strength remain open. No training, AWS,
scheduled task, fault campaign or third-party vendoring is added.

## e8d6c31 F8 startup observation failure: 2026-10-22

[Engine39671987409](https://github.com/daejunnom/Rove4k/actions/runs/39671987409)
fails at F8 positive verification; Rust and
[Repository39671987630](https://github.com/daejunnom/Rove4k/actions/runs/39671987630)
Node22/24 succeed. Four actual checkouts use1c1e8de49ff6fc962c6dc4729921dbc0f67a557f,
parents develop761bdc0 pluse8d6c31, tree0364fe6e identical to that head.
F4410's new two reproductions and quit/EOF two sessions pass. F8's builder
also reproduces4442 B twice with matching closure59. Its quit session passes
nine TIDs/four legal GO/normal exit, but EOF startup fails the shared strict
descriptor assertion with0/1/2/3. FD3 identity and cause remain unknown.
No EOF startup/native/TID/GO observations are saved. EOF cleanup is forced,
settled_before_cleanup=false, group absent/readers joined/errors0. This is
F8 overallpassed=false, not two successful sessions. Later C semaphore/D/root/
generic stages are skipped. The original watch closes exit1; no CI retry is
performed. Frozen index57599 B:
`77818bb53e974a894ef680fa18d0854b4d26ff56fe2e7b650ce9002d3c41b6ea`.

The F8 observer currently calls strict tasks/FD inspection after native
identity but before checking its nine-TID startup phase. The follow-up changes
this observation order: count/state-only waiting first establishes stable
nine idle TIDs; the original strict tasks/FD/children checks still decide
resource acceptance. Waiting samples are not readiness acceptance; a lasting
FD3 after startup still fails. No shared D helper/assertion relaxation or
AssertionError catch is used. New local/current-head F8 results are separate
from the preserved e8 failure, without claiming its unknown descriptor cause.

## F4410 shares one condition object: 2026-10-22

Four fixed spans share F's two condition objects after the digit guard,
reducing source8497→8469 B, bootstrap9419→9391 B and whole4424→4410 B.
Native stays18576 B with new SHA851069e0 and .text6998→6994 B. Unlike A,
F notifies every startup arrival, including2→1. All four broadcasts, both
while predicates and qj remain; GO epoch/pending publication, last-completion
strict-depth/tie0 selection and flush-before-notify, and partial-create drain
bypass/created-thread joins keep their original order. Extra unrelated wakes,
mutex competition, timing and native storage differ. Fault schedules remain
source arguments. The four-span/full-inverse source proof is separate from
new selected execution.

One full --dev build reproduces shipping twice and unchanged DEV twice.
The unchanged selected verifier passes quit/EOF two sessions, eight legal GO,
three startup TIDs, exact new native restoration and physical process/reader
exit. Each optional --dev build retains its entire selected4319/4045 artifacts
and DEV while its explicit separate full reference becomes8469 B. F8 bypasses
this stage and keeps pre-name8538/47353a15, own4442/nice24/9-TID profile; only
producer closure provenance adds one helper, base52+positive2+own5=unique59.
No new local F8 execution is claimed. All four original commands return0,
are reaped and close with group absence, forced cleanup0 and active handles0.
Fixed first-cost index8429 B:
`9d0c8ed713c93b107da69702013a5850b7c400c5ca68260c9e35fb792002e6f5`.
Final six-file qualification index9603 B:
`6fea8daeed2033cffe490b022d94555fd03970bad4c552f1cb4ebd6d8574a11d`;
build `23f88092dde9bc9147510dda8b7634a3492eddaa5713c7c5498d275c08d74fc5`;
runtime `d96585d63a88cd04e6faf53fef1c5467887a8d3fb118fa3c9edc07c690b9d920`.
Helper and builder retain producing bytes; final recipe/README changes only
complete the ordinary-validation annotations. Later external direct-walker
and B/C/E condition candidates are outside this maintained checkpoint.
The default remains314 B over4096, with final resources/scaling/strength open.

Preceding head8466389 passed C/Rust in
[Engine39670382405](https://github.com/daejunnom/Rove4k/actions/runs/39670382405)
and Node22/24 in
[Repository39670382392](https://github.com/daejunnom/Rove4k/actions/runs/39670382392).
All four actual checkouts use e4003de03efe16c641e527d77c9f8f99f7b93f6b,
parents develop761bdc0 plus8466389 and treebe08e53e identical to that head.
Eight current A/B/C/E build/selected reports directly confirm4541/5032/4860/4914,
original C/native/DEV controls and fresh two-session/eight-GO/three-TID exits.
F8's internal nine-TID report is not reread at this checkpoint; F4410 is WIP
outside it. CI index86876 B:
`bce82fcec59e80e5af8275103ff1a5682c532f3a30a05b984e556b95daca426e`.

## A4541/B5032/C4860/E4914 common readonly template: 2026-10-22

One pure common shipping_readonly helper changes the single standard-Linux
readonly flag spelling in four fixed legacy templates before C insertion.
Their original template/name/marker guards run first; C also retains its
original Popen argv AST check. Four family-specific before/after pins, one
owned span, two protected gaps, full inverse and one source marker guard the
transform. No shared source_package/prepare implementation or F/F8/optional
consumer changes. Source/native/DEV, compiler, worker/TT profile, header73 and
each original codec stay; C retains its actual nice64 setting.

The four bootstraps each lose10 raw bytes. Complete files change A4550→4541,
B5042→5032, C4869→4860 and E4924→4914 B. Each ordinary --dev build reproduces
shipping twice and unchanged DEV twice, then the unchanged selected verifier
passes quit/EOF two sessions, eight legal GO epochs, three stable TIDs, exact
original native restoration, private-path cleanup and physical process/reader
exit. These eight commands are serial A→B→C→E; all return0 and are reaped with
group absence recorded at closure, forced cleanup0 and active owned handles0.
A's observer has no FD-list observation; none is inferred from the flag form.
No new SAN, fault, NVC, game or performance run is included.

The final13 source pins and actual producing inputs/reports are bound by
`rove4k-common-fd0-promotion-20261022-evidence/final-index.json`,27952 B,
SHA `fa61a83b080473c735bf14f2f2bacde9f46c0607bc12c10dfbffe0b74cdaea18`.
The original normal command receipt is23957 B,
`b8fa0c7efabe29a297eb1c0b37bb87fe20944027060d48b15eaed5dd5de4fd3e`.
Only eight recipe/README completion annotations change after execution;
the common helper and four builders retain producing bytes.

Preceding headaeb6977 passed C/Rust in
[Engine39667440376](https://github.com/daejunnom/Rove4k/actions/runs/39667440376)
and Node22/24 in
[Repository39667440557](https://github.com/daejunnom/Rove4k/actions/runs/39667440557).
All four actual checkouts used mergeb8880a67c5324d2d6f2f8d5941a33a2de3baf609,
parents develop761bdc0 plusaeb6977, treef00d6ba1 equal to that head. Actual
new E4924/F4424 reports and two selected sessions each were read directly.
F8 freshly binds closure58 and its4442 B artifact to two actual nine-TID
sessions, main S/eight workers R with positive CPU deltas, four legal GO per
session and physical exit. E's exact diagnostic control does not qualify its
current E19 model. CI index70897 B:
`2970202ad0b9f38e578ec1f525c78da16d654d03b0a21ae711b8a051b2903e54`.
This preceding CI does not qualify the new common template change. Every
default family remains above4096 B; target resources, scaling and strength
remain open. No training, AWS or scheduled execution is added.

## E4924 shared terminal loop and F4424 parser/bootstrap forms: 2026-10-22

E ports the previously qualified terminal-loop sharing structure to its actual
E19/physical21 implementation. Four exact regions reduce source10190→10142 B,
bootstrap11202→11154 B and whole4933→4924 B. Native26336 B has new identity
5a1f68ee. A terminal mask preserves draw/cap priority and no-legal mate/stale,
skips the entire G TT call and QS stand-pat, and returns after the first legal
private make before ++Z/path/root/learners/TT-store. Entry claim stays first.
Additional terminal scoring/sorting reads are bounded for valid Boards,
generated moves and initialized Worker/yb0..12. Private ordering/first child,
work, time and cross-worker scheduling may differ.

One fatal ASan/UBSan compile/run compares28 old/new terminal and claim-reject
calls using the actual new TU unchanged and only the old M definition aliased.
E's actual21 feature slots, typed Board/two Workers/path/history/correction,
root/node/stop and TT key/data/lock snapshots agree. An exact137/depth255 warm
TT witness covers forbidden terminal cutoff. Transient atomic-probe absence
remains a source argument, separate from snapshots. Focused index:
`4ae4eb41a5c90be920572a260e077d025318a5854ad7e2629eae8fd9e5a93a7c`.
One --dev builder reproduces shipping and unchanged DEV twice; unchanged
selected quit/EOF two sessions pass eight GO with three TIDs, exact new native
and physical reader/process/group exit. Final E index:
`9c7801d2d735cf6f07d6de4957e62fc337351116116268c3853ce5b042f6fb89`;
build `769e345bfacc0c614a5fe0073e2a88df61b2cd81eb216213bb88c1bd825bbabe`;
runtime `d9dd187e9d4c50e6c9974c3bd2309cf1661910a68bc84890643592af0efc14c5`.

F's common-pattern source study replaces the initial digit expression by
`*s-48u` in one fixed ASCII/int32/unsigned32 domain. Null short circuit, one char
load, strtoull/end/high-bit validation and all clock consumers remain. Source
8509→8497 B produces the entire identical nativeea471236. A separate prepared
full-template span uses Linux's standard readonly flag0, reducing947→937 B
before C literal insertion. Path/FD lifetime/cleanup and execution order stay;
Python attribute/source/bytecode/timing equivalence is outside this contract.
The shared template module, optional selected templates and F8 are unchanged.

Independent fixed-codec costs are4432 B for the digit guard and4429 B for FD0.
Their disjoint composition yields bootstrap9419 B and whole4424 B,13 B below
the qualified4437 predecessor; its first-cost index is
`d6287c9adf1b74a6d1ef924f179562738ee0175c19943a3f89f41f78b01b11d9`.
The pure late source/template helper is applied only to full shipping and its
separate optional full-reference source. One full --dev reproduces shipping
and unchanged DEV twice, and unchanged selected quit/EOF two sessions pass
eight GO with three TIDs, identical native and physical reader/process exit.
Both existing optional builders each run --dev once: selected4319/4045 entire
products remain byte-identical while separate full references use8497 B.
F8 adds only the new helper and producer provenance, making unique closure58;
pre-name8538/47353a15, own nice24/4442 B and nine-TID conditions stay. New local
F8/optional selected executions are not claimed. A→B→E→F positives are serial.
Final F index `ad344def62681c45f2b54ba319e3d3c894f9751817d6d6f971fcdc6199595434`;
build `f37fa223dac52b632f89c337fe27aa1658f0bff52ba029a9d3062b159ef538a8`;
runtime `a3935e9342efbb809b73b66b405cc9e179b8e3d3d7ebceb62b4f6cb7ec523ccd`.

Preceding head52b1707 passes C/Rust in
[Engine39665359715](https://github.com/daejunnom/Rove4k/actions/runs/39665359715)
and Node22/24 in
[Repository39665359939](https://github.com/daejunnom/Rove4k/actions/runs/39665359939).
All four checkouts use dc7c34bc414311d558d0f77e6207f3c923ddce1a, parents761bdc0
plus52b1707 and tree218cdedd equal to the requested head. It directly confirms
new A4550/B5042 and their selected images, but E4933/F4437 are predecessors of
these local E/F qualifications. CI index:
`faa9519f511495eb6f5688ab3078e22a0507c2a7388c3d84ce3f651b07799350`.

D's external shared-first cost remains separate: scalar5836→5849 is LOSS13;
HQ6037→6031 is an unqualified GAIN6. The new HQ-only source selection is source
only and increases physical maintained-source proposal bytes855 B while
selecting the measured HQ tokens. Neither D candidate changes this table.
Default4KiB files, final resource/stack profiles, compact-policy comparisons,
target scaling and strength remain open. No training, AWS or schedule is added.

## A4550 shared condition and B5042 direct walker ports: 2026-10-22

A shares its two condition objects under the existing mutex. All three notify
sites remain broadcasts and both original while predicates remain. Completion
flush precedes pending-zero publication; final startup arrival, GO epoch and
shutdown publication preserve their order. Broadcasting all registered waiters
avoids selecting only a waiter for the other predicate. Idle workers may wake
and contend more often before rechecking the same epoch. Exact scheduling,
timing, condition addresses and general partial-create/fault traces are not
claimed. Source8914→8886 B, bootstrap9878→9850 B and whole4559→4550 B; native
length18576 B stays but identity becomes e00da92c. The late pure helper and its
literal adapter preserve all previous source/name guards: inverse to the old
literal, call the unchanged names guard, then forward only the same three spans.

B removes three forwarding definitions over the existing shared walker and
ports seven consumers directly. Full64-bit SEE masks, explicit !! Boolean
conversion at the int check consumer, generated count0..432 and move order
remain. The runtime H output parameter is renamed locally to avoid shadowing
the walker. Source10394→10270 B, bootstrap11433→11309 B, native26296→26248 B
and whole5073→5042 B. The walker body, make/SEE/search/TT/learner and worker
control are protected. Removed implementation symbols, general external C ABI,
compiler frame/layout and timing are outside the equivalence claim.

Each maintained --dev builder runs once, reproducing shipping twice and the
unchanged DEV twice. Each unchanged selected verifier then passes quit/EOF two
sessions and eight legal GO results with three startup TIDs, exact new native,
private path cleanup, reader closure and physical process/group exit. A runs
before B; original owned handles exit0 and are reaped with no forced cleanup or
remaining handles. A's observer does not record a descriptor list; no FD-check
success is inferred. New semantic/SAN/fault/game/performance campaigns are not
added for these source-only condition and forwarding contracts.

Final A index `648e05b4754f93558e48923b9b76cdce766f42cae99fc21b4674f7ab8b10dae2`;
build `d5106d72123363df60c86330dde6eaabbffc3de85d0107083a60ace3ab2e6854`;
runtime `2730e1c1ad22ea12db2a2c2a18ab8a126648a4cd5e2d2885fcb85ecae5ff17a5`.
Final B index `3bed0007fe0416f57e587d583fa1d5fb96a3bdf7f3f6055e0b2a43893c2afad9`;
build `fbd9e07ff22644fc9daac389a68ded5d1c6a5422f947b3b6cf5b31c0b76a9e5d`;
runtime `1be703746643cb1539dcf2d14864eb006b3252f6dd208c520d9db1a72184bf95`.

Preceding head6c1f1af passes C/Rust in
[Engine39662222702](https://github.com/daejunnom/Rove4k/actions/runs/39662222702)
and Node22/24 in
[Repository39662222559](https://github.com/daejunnom/Rove4k/actions/runs/39662222559).
All four actual checkouts use merge27034b7b30f72bf46db078c17514f516d2fe43f8,
parents761bdc0 plus6c1f1af and tree6a2eee50 equal to the requested head. That CI
regenerates F4437 and current F8 closure57/4442/nine-TID positives, but its
A4559/B5073 artifacts precede these new local qualifications. Frozen CI index:
`1d808e53b1df0be1817a60fa7e0261fba75d4b54f246e6879252262c3d1076ee`.

Both default files still exceed4096 B. E terminal and common numeric/FD source
proposals, F controller losses and D shared-first candidates retain separate
external source/cost/qualification states; they are not included in this pair.

## Full-F4437 codec and bounded NVCompact comparison: 2026-10-22

Default full F changes only ALONE nice_len24 to16. Source8509 B, native18576 B,
bootstrap9441 B and exported pre-name8538 B remain entirely byte-identical to
the qualified rank-sharing predecessor. The complete file4438→4437 B has new
SHA256 `70ca8010621be6783020c50aed2f2ca326bc763231454ac824e0f3453e6f0d05`.
All other codec settings and73-byte header remain. This is an encoder-setting
gain, not additional source compaction. Optional policies keep their own codecs
and4319/4045 B outputs; F8 keeps its own nice24,4442 B and nine-TID contract.
Its producer closure pin alone advances after exact pre-name byte comparison.

One ordinary full --dev call reproduces shipping and unchanged DEV twice.
The unchanged selected verifier passes quit/EOF two sessions and eight legal
GO results with exact restored native, stable three TIDs, readers and physical
process/group closure. No new semantic/SAN/strength campaign is implied.
Final index `31a7c03fe0487ad1b8225e2c8fbcb1e6924e668462a942ed3199c8e70a11b3d7`;
build `e5b15d5f6290bafc4a4e67d3c6f1e2ff295e7dd2141a472a912a11ce5f63b783`;
runtime `506a13c0d685ce331f5e49d6dca1380c2640cf697e2d0ef5e8031b37496ccc80`.

The bounded prepublication NVCompact0.6 controller experiment preserves its
initial unsupported-frontend-flag validation error separately. The corrected
run reaches60/64 evaluations and8/8 combinations with accepted_steps0;239
nontrivial name subsets remain unvisited. It keeps the8415 B candidate and9347 B
bootstrap unchanged. Its final codec portfolio selects nice16, yielding4444 B.
Matched original-full and rank-full controls with that same setting yield4438
and4437 B, so the source-shorter controller remains unselected. Actual codec
calls total447 including two matched controls. No exhaustive source optimum or
general controller impossibility is claimed. Corrected-run final index:
`097bfd6938d9c3cc82d2fcada2eb48b6ff4f71bd9dd553cd8d55dc37be104a48`.

Preceding committed checkpoint bde316a passes both language jobs in
[Engine39660003941](https://github.com/daejunnom/Rove4k/actions/runs/39660003941)
and Node22/24 in
[Repository39660003831](https://github.com/daejunnom/Rove4k/actions/runs/39660003831).
All four logs use actual mergeba5468a1a598d4207d35e22cdebf1bcc4fa5e8c1,
parents develop761bdc0 plus bde316a, with tree22f742bc equal to the requested
head. Current artifacts regenerate D5836/6037 with its separate full-zero232
RX identities, audit/pre-entry2 and production4 sessions/12 GO; F4438 has fresh
selected quit/EOF sessions. F8 regenerates4442 B from its explicit pre-name
input with current57-file closure, nine stable TIDs and eight active workers.
Fresh.py is not invoked in that workflow. This preceding CI does not qualify
the later nice16 encoder setting. Frozen CI index:
`4c2d706101e6a2155a5783e4c15568a158652aa59202d1eac69c36d4616685f3`.

Default F still exceeds4096 B by341 B. Target resource profiles, compact policy
comparison, scaling and game strength remain open; reduced-feature4045 B is
not default-F completion. No scheduled follow-up, training or AWS is added.

## D body232 and full-F4438 rank sharing: 2026-10-22

D's new explicit v3 class codes whole_BCJ(native)[232:] and restores
zero232||native[232:] at the original addresses. The unchanged compiled native
ELFs remain7612/8000 B; their dormant internal ELF/PHDR metadata is no longer
compression input. This changes the private restored-image observation
contract. It does not assert full compiled-native/RX byte identity or apply to
arbitrary header-consuming programs. Whole scalar5908→5836 and HQ6111→6037 B;
packets4771→4699 and4974→4900 B, with the nonpacket contribution1137 B unchanged.

Codec, packer, builder and verifier bind compiled native, complete restored RX
including all232 zero bytes, and own ELF to separate strict identities. Full-N
entry/pages/BSS/guards/model geometry remains; decode count isN−232. Actual
BCJ scans synchronize at232 with no crossing operand. V2 encode/default APIs,
old native admission and full-RX comparison remain. Source review closes the
mixed old-HQ-layout/new-descriptor case through central class binding and keeps
the original explicit-None HQ rejection. These are developer admission fixes,
not relaxed runtime image checks or prefix exceptions.

The final ordinary build regenerates both native/whole images twice and audit
images once. Two earlier passing builds are preserved while those admission
guards were corrected; all artifacts agree. One new positive verifier passes
two pre-entry whole-RX/BSS/padding/guard/NX checks and four quit/EOF sessions,
12 legal GO results, three persistent TIDs per session and physical reader/group
exit. Existing old runtime is not relabeled as new-image evidence. Initial
preexec limit failure ran no encoder/loader and is preserved separately. Total
actual lane cost is12 native compiles,14 encodes,22 loader compiles and2 DATA
inverses; no fresh/fault/negative/ptrace/RIE/personality or game campaign follows.
D final index:
`bff87a5dc74e3a13c3b6093401019486c289241dd661b32ee4294771c6b67acf`.

Full F normalizes rank inside its pure packed-HCE value function. For rank0..7,
XOR7 equals7-rank and the absolute center term is reflection invariant. This
shares the advance/center rank and removes one local, source8513→8509 B and
whole4439→4438 B. Board, Move, key, TT and learner orientation do not change.
An actual C comparison covers all832 valid square/signed-piece pairs, including
empty piece. Native remains18576 B long with new identityea471236, so new
ordinary and selected execution are required rather than old-native reuse.

One full --dev builder reproduces shipping and unchanged DEV twice. Existing
optional builders each run once: selected4319/4045 artifacts stay byte-identical
while their separate full-reference source becomes8509 B. The unchanged full
selected verifier passes quit/EOF sessions with8 legal GO results, three startup
TIDs, the new native and physical exit. F8 still consumes pre-name8538 B through
its own specialization; new rank code is bypassed. Its provenance closure adds
the new helper and synchronizes the D generic-positive-helper whole-file pin
after exact consumed-body review. No new local F8 compile/codec/runtime is
claimed. Full F final index:
`38f3dbc87ed8d8729f62469ab3cac34760602f340879b4b9575357231344be7f`.

Both changes remain above4096 B. No final target-resource, scaling, stack,
strength or whole-plan acceptance is inferred.

## C4869 shared terminal legality loop: 2026-10-22

C shares its dedicated terminal legal-make scan with the ordinary ordered loop.
A private mask distinguishes ordinary, draw, cap-only and draw+cap. Terminal
paths skip the entire atomic TT call and QS stand-pat/pruning, returning after
the first legal private child before root/path/learner/TT writes. If no legal
child exists, the existing mate/stalemate epilogue wins over cap-stop. Draw+cap
retains draw priority; only a legal cap-only witness stores stopped. Entry
stop/deadline claim and actual SIMD evaluation stay at their old positions.

Four exact regions reduce source9848→9800 B and whole4874→4869 B. The complete
26304-byte native has new identity011e671f; it is not inherited from C4874.
Canonical, DEV, coefficients, features, learners and the fixed profile remain.
Terminal ordering newly reads initialized path/history/continuation/id and
sorts local scratch. Private child order/work, cap-stop wall time and other
workers' scheduling can differ. This is not a timed-node or private-trace
equivalence claim, and arbitrary uninitialized private calls are outside the
production domain.

One fatal ASan/UBSan compile/run includes the actual new TU unchanged and old P
with only its definition name aliased. All28 paired calls are terminal/claim
failure paths before recursion. Return/stopped/root/node and typed Board,
Worker/history/path/learner state agree. A warm full-key exact cutoff witness
exercises TT suppression. Snapshot key/payload/held-lock observations do not
measure transient probes; probe absence follows the unevaluated conditional
operand in source. Private FEN/cap adapters are not public game reachability.

One ordinary --dev builder reproduces shipping and unchanged DEV twice. The
unchanged selected verifier passes quit/EOF sessions with8 legal GO results,
three startup TIDs, exact new restored native, stdio/private path cleanup and
physical process/reader exit. Existing first-cost and LOSS records remain
unchanged; metadata readback path errors are preserved separately from product
execution. No new game, resource-profile, stack or strength acceptance follows.
Final focused/normal index:
`07781359bb230d7d11a4979b40955369634af3bdcd0a83f82dc8bce80ed25b66`.

## B declarations and E4933 center sharing: 2026-10-22

B merges two adjacent ordinary int declaration separators inside its pure HCE
value function. The declarator types, scope, initializer dependencies and
full-expression order are retained. Two exact spans reduce source10402→10394 B
and bootstrap11441→11433 B. Its entire26296-byte native remains b38c3312;
whole length stays5073 B with new identity b7698bdc. The original first-cost
TIE/unselected receipt is preserved. A separate subsequent choice uses smaller
source with no whole-size increase and exact native identity as its secondary
criterion; it does not rewrite that earlier result as a byte gain.

One ordinary --dev builder reproduces shipping and unchanged DEV twice, and
the unchanged selected verifier passes quit/EOF sessions with8 legal GO results,
three startup TIDs, actual restored native, absent private paths and physical
process/reader exit. No new semantic fixture or SAN is needed for these two
same-type declaration separators. B normal/selected index:
`58c56424effa83e39e5cd126ebf59018cc5f5b601f7d692c8750d597462e122a`.

E shares the two symmetric center-axis minima as a centered Manhattan sum.
For valid0x88 q=16r+f, q%8=f and q/8=2r. Both absolute-value terms are odd in1..7,
so their sum divided by2 is exact; the result remains0..6. All64 valid squares
agree, and actual consumers are piece-activity updates and generated FROM/TO
ordering deltas. Arbitrary offboard inputs are outside this contract: q8 is
an explicit old/new counterexample. No model coefficient, feature, Board access
or update order changes. One exact span reduces source10200→10190 B and
whole4935→4933 B. Native length26336 B stays the same, with new identity953d8bd5.

One ordinary --dev builder reproduces shipping and unchanged DEV twice; the
unchanged selected verifier passes quit/EOF sessions with8 legal GO results,
three startup TIDs, the new restored native and physical cleanup. B then E
selected execution is sequential. No repeated ordering SAN campaign, game,
target-resource, stack or strength acceptance is claimed. E normal index:
`8cebfa41cb845f452c00f0518e6633388cdeb6f8368cb6ad49846c9b32ffd47e`.

A separate full-F controller proposal shares drain/GO/shutdown mutex frames
under private modes0/1/2. Its source8513→8415 B, but fixed first cost grows
whole4439→4448 B with a new native identity. Independent source review retains
the exact stop-before-lock and partial-create/no-stop-write contracts; this
does not establish a whole-size gain. The candidate is externally preserved
and unselected in that context, with no engine or SAN execution. Cost index:
`7dfad50f8241e985177e1ccc7dd6d3aa618c1794b0812fde3b93bd61dbc31638`.

## E4935 generated-mover side reuse: 2026-10-22

Checkpointd26e503 passes terminal C/Rust and Node22/24 CI in
[engine39649251081](https://github.com/daejunnom/Rove4k/actions/runs/39649251081)
and [repository39649250778](https://github.com/daejunnom/Rove4k/actions/runs/39649250778).
All four actual checkouts use merge91cc4118dbcc8130c7c32b406d41198d9e7d0c8f,
parents761bdc0/d26e503, treeda17387b34158e66f5e74ab7eaa065d8d99dd6bf.
That run regenerates A4559/F4439/F84442 and D's unchanged5908/6111 files from
its new6317-byte source. Its E is4946, before the local change below. CI index:
`f857c2c56f2bb176dd27f3267675589d51256f4771b55048d6d39386f1537e63`.

E's ordering receives only moves generated on the same Board. Their nonzero
origin piece belongs to p->s, so the pawn rank term reuses p->s instead of
recomputing its sign. Removing the sign-only local makes two exact edits,
source10210→10200 B and bootstrap11222→11212 B; whole4946→4935 B. The nineteen
logical model coefficients and physical21 slots, remaining ordering features,
evaluation/search/learners and DEV are unchanged. Native length26336 B stays
the same but its complete identity changes to77a43ff9. Arbitrary empty or
opponent-origin moves passed directly to R are outside the declared domain.

One fatal ASan/UBSan compile/run includes the actual new TU unchanged and the
actual old R body with its definition name alone aliased. Same-model old/new
scores and typed full Board invariance pass for136 root/child boards and2472
generated moves, including both-colour EP/promotion and all four castling wings.
The existing generator/make catalog is reused without TT or search campaigns.
External focused index:
`a41c3ed9694f962b48eb79846484c3864f4d4845bfbcde7f6c5ca28559229cb3`.

One ordinary --dev builder reproduces shipping/unchanged DEV twice and the
unchanged selected verifier passes actual quit/EOF sessions with the new native.
Complete source/native/bootstrap/whole match the preserved first cost. The
preparation's M-call string check originally misidentified FROM and failed
before compilation; that first error is retained separately, and only the
inspection expression was corrected. No product failure is relabeled as success.
This source-only expression change does not claim a new model, strength,
timed-node equality, target resource profile or final4KiB acceptance.
External E normal/selected index:
`936193c25ad5a7c1471c5664045efdcb19d8e8595a9034e601ae7fd6b327ef8e`.

Checkpoint8f9890e then passes terminal C/Rust and Node22/24 CI in
[engine39652127019](https://github.com/daejunnom/Rove4k/actions/runs/39652127019)
and [repository39652127018](https://github.com/daejunnom/Rove4k/actions/runs/39652127018).
All four actual checkouts use merge9b988c6195c871f054a25f881c970b1cce815fe3,
parents761bdc0/8f9890e, treec132310a4f44afa0a802217965e8046bd8abf3d9.
Its C job directly regenerates E4935 with source6d336854/native77a43ff9 and
whole d796caf3, followed by fresh selected quit/EOF sessions. Other maintained
sizes, D's two forms and F8 regeneration/positive sessions also pass. CI index:
`517f07be2ac0b6526e59b39a3eeb0df6bad5c71c8da16ce587031ddc91886062`.

A separate C zero-piece update proposal adds an explicit H(0) identity and
shares K's old/new occupancy handling. The declared domain requires an already
initialized private nonvolatile Board and separate full-expression H calls.
Two exact spans remove7 raw bytes, but fixed first cost grows native26304→26312
and whole4874→4875 B. One candidate compile/encode and strict restoration pass;
no SAN, normal or engine runtime follows this size loss. It is not maintained,
and the original source, contract addendum and actual candidate are preserved.
This result is limited to the current C source/compiler/codec context. Index:
`3c03c91b1b75e211c82db1e2420f4a943216d72641fca84d49dcd396f4b2e33b`.

A separate B mailbox/bitboard put proposal shares the old-piece removal and
new-piece addition in a finite two-pass loop. Its production domain preserves
mailbox publication order, full hash, cached white-perspective HCE and the
new king square, with bounded signed arithmetic. Source10402→10362 B and
bootstrap11441→11401 B, but fixed complete cost grows5073→5086 B. Native file
length stays26296 B with a new complete identity: .text8562→8493 B and
.eh_frame1348→1372 B. Smaller native code therefore does not imply a smaller
source-embedding submission. One candidate compile/encode and old/new strict
Python/CLI restoration pass; baseline recompilation/re-encoding and engine,
SAN or normal execution are0. Current B5073 is retained. Original inputs and
the candidate remain available for a changed compiler/codec/source context;
this loss is not a permanent exclusion. Frozen first-cost index:
`ae6c5931913ee594a9575638161d44f6df6cc3f3b3f3d4426d423ba410d74c61`.

## Further source and shared full-F reductions: 2026-10-22

Checkpoint973e7b5 passes terminal C/Rust and Node22/24 CI in
[engine39645569157](https://github.com/daejunnom/Rove4k/actions/runs/39645569157)
and [repository39645569148](https://github.com/daejunnom/Rove4k/actions/runs/39645569148).
All four actual checkouts use merge0a0989784345263af0d6563661e3af77c978f855,
parents761bdc0/973e7b5, tree4cfb892998bea1940936b9874e20b9b048006710.
That run regenerates A4569/C4874, defaultF4445 and fixed8F4445 with selected
sessions; it precedes the following local changes. External CI index:
`07c5ae03cea0986bea32b1d2f0ca86c189f4759d07c17770e9a813019a1e3c9c`.

The prepublication NVCompact0.6.0 tool runs one bounded A-only private-name
search against current8914-byte C. The make destination parameter t becomes w
at24 one-byte tokens, with25 protected gaps and full inverse. Same raw C bytes
are embedded using triple-double instead of triple-single quotes. The old codec
gives4569→4568 from the literal and4568→4567 from the name. The selected fixed
ALONE preset6/BT2/dict16KiB/nice24 gives original payload4560 and chosen4559;
the latter1 B is the combined literal/name difference in that codec context.
The full10 B is not attributed to the name alone. All four tool native compiles
and actual retained images equal the existing18576-byte native7700f116.
The45/64 evaluations stop at8/8 combination attempts with18 nontrivial subsets
unvisited. No optimum or exhausted complete space is claimed. Normal --dev
reproduces shipping/unchanged DEV twice, then the unchanged selected verifier
passes two actual sessions. Pure shipping_names reads no search/report artifact.
External A promotion index:
`f8f73a54e4633b7021cdf938a8543b8b36a5c81a004175a83d117ccf9b5d5c69`.

Full F2 shares exactly-two-worker result selection in one strict-greater pointer
expression, preserving first-worker ties and completed-root fallback. One49→24 B
region makes source8538→8513 B; native92671066 remains entirely identical.
Its post-name stage preserves pre-name47353 and the original names400ad output
for F8, whose six resource roles and eight-worker selection loop stay separate.
First-cost and ordinary/selected qualification of4445→4442 are preserved before
the following common wrapper change. Both optional builders reproduce their
unchanged selected tuples and the new separate full-reference source.

Shared bootstrap_full adds one positional spelling edit, wait(timeout=5)→wait(5),
after its four existing preparations. Actual CPython3.12 Popen.wait binds the
same timeout5. Signal order, kill escalation and final wait/reap stay intact.
The prepared template955→947 B makes F2selector4442→4439 and F84445→4442 B.
Source/native/header/codec are unchanged by this edit. Both ordinary builders
reproduce twice and unchanged selected verifiers pass actual quit/EOF sessions;
F8 keeps9TIDs and eight active workers. Runtime ownership is coordinated with
the other selected sessions. F2's new promotion index is:
`debf5ec34ebbb2d084a35923f325972d3f34e28902bb7f36216880dc69c7dcc9`.
F8's new4442 promotion index is:
`3d67631aac33fbdd0e1e51991319ba646b4899adb221b4e3dc4abf23c8e960eb`.
The prior4442/4445 results retain their own frozen evidence. Fixed local
profiles, source/no-token-observation assumptions and final resource/strength
acceptance remain distinct from these local reproduction/protocol results.

D shares the duplicated probe CMPXCHG16B instruction body in a bounded stage
loop. Every zero write argument performs one coherent read CAS; every nonzero
int performs that read and one write CAS, with no success-driven retry. Full
key/payload width, aligned Entry, carried lo/hi expected pair, clobbers and
drop-on-write-failure semantics are unchanged. The exact405→321 B region makes
search.c6401→6317 B. Separate scalar/HQ first costs preserve every native,
packet and whole byte. One ordinary builder repeats both shipping forms and
their existing audit images with unchanged ELF/BSS/layout/identity gates.
Build receipt:
`7376bb3710b244032df7c871446419801faa1de612afdc410714b2fcef3a43e8`.
Existing positive evidence is reused by entire artifact identity; new runtime
and fault/ptrace campaigns are0. This is84 B of canonical-source reduction and
zero shipping-byte gain. DEV caller reasoning is source-only; DEV codegen and
stack acceptance are not newly measured.
External D source-promotion index:
`047b060bd871b05aab1143f94e5e0823a812e11c06d2feb5818e031b7bb22ef2`.

## A4569 terminal sharing and C4874 SIMD reduction: 2026-10-22

A shares its terminal-only legal-move scan with the ordered make loop. The
four exact edits shorten shipping C8965 to8914 B and bootstrap9929 to9878 B;
whole4580 becomes4569 B. Draw/cap flags suppress the TT probe and return at
the first legal child before path, root witness, learners or TT writes. Draw
returns0 without setting stop; cap-only sets stop, while no-legal mate/stalemate
retains its original score. Terminal private ordering and child scratch can
change, so raw work, stack and timing identity are not claimed. Actual old/new
focused fatal ASan/UBSan passes18 cases, including poisoned TT bounds, with
exact typed Board, root/result metadata, path/job keys, learners, TT and nodes.
Ordinary --dev reproduces shipping/unchanged DEV twice and the unchanged
selected verifier passes two sessions. Build/runtime receipts:
`b8c45eb404085d66ad43737fddd241330018bc6129fcbcaeb75fd980a3127cf4` /
`8b13597a78fa65bdeada3ec79c24dc297d3730d2db85b72d63a4527bae643d7e`.
External normal/selected index:
`1118be88dcfaadfc9d42e1cbae3402bc1a3c7f9ea8ed6a17e7204850b8bcfd5b`.

C keeps both16-byte loads and actual128-bit madd, then sums its four signed32
lanes instead of two hadd intrinsics plus extraction. Coefficients and all eight
signed16 features are unchanged; every intermediate sum is bounded in absolute
value by70483968. One exact194→160 B region shortens source9882 to9848 B and
bootstrap10931 to10897 B; whole4880 becomes4874 B. Actual old/new evaluator
bodies run under fatal ASan/UBSan with80 basis and8 mixed numeric inputs per
variant, independent mailbox/hash/features, real make/search calls, legal children
and ordering. Their complete stdout matches. Synthetic signed16 extrema are
distinct from normal mailbox reachability. Ordinary --dev reproduces shipping
and unchanged DEV twice, then the unchanged selected verifier passes two sessions.
External promotion index:
`4fc4ffaf57d55fd9bc91c1a363a19f12f1901538d12b819db37156e66399c3a1`.

Both new natives have different complete identities from their preceding
artifacts. These focused and selected runs do not establish timed-node equality,
target resources or strength. Canonical readable sources and DEV are unchanged.

Further source reductions are preserved without promotion. B/E mate and halfmove
edits have four measured states in the same fixed context: B5073/5074/5077/5077
and E4946/4948/4949/4952 (base/mate/clock/both). The union removes25 raw bytes
but loses4/6 whole bytes. Each new standalone/combined candidate is compiled and
encoded once, strictly restored, and not runtime-qualified. Combined indexes:
`041862d9cb568ccb4314842c38d65045ff06a89929eec8742f0f406638494b29` /
`0c6c8c374b59f5ba9dcfa883082ccaa619eee93d2129efaf3c4b9e010ccf19c9`.
D's put-pair loop removes26 raw bytes but ties whole5908/6111 in scalar/HQ;
new native and packet bytes differ. Empty-piece identity removes29 raw bytes
but increases scalar native32 B and whole24 B to5932. The latter extends the
private piece(0,q) call domain explicitly. These fixed first costs include DATA
restoration, not generated-ELF execution; no failed-size candidate is adopted.
External empty-piece index:
`0c823b9ba3a105cc6bc16b2ad4543666a1bd8c2ff1e033ad767515d8c4d9c36c`.

## Fixed8 F4445 and shared full bootstrap: 2026-10-22

Checkpoint32d43b2 passes terminal C/Rust and Node22/24 CI in
[engine39639557267](https://github.com/daejunnom/Rove4k/actions/runs/39639557267)
and [repository39639557331](https://github.com/daejunnom/Rove4k/actions/runs/39639557331).
All four actual checkouts use mergef28b381c with parents761bdc0/32d43b2 and
the same25693baf tree as the requested head. That run executes A4580/C4880,
F2full4445 and F8legacy4474; subsequent local changes retain their own evidence.
External CI index:
`2cdcef4eada047631df41a9def3f300a8589ff0c271df2ab9e8f1bb85aa37366`.

F8 now reuses the strict F2 private-name helper on its original pre-name base,
then applies only its six worker-resource roles. The combined65 edits commute
and have exact inverse and protected-gap proofs. Its selected source is
8538/SHAad02fbb8; the complete18576-byte native remains exactly33509091 from
the old eight-worker profile. A shared pure bootstrap_full.prepare_template
owns the four full-template preparations. Callers still insert their own C;
source_package owns fixed encoding. Both full profiles use the73-byte header
and ALONE preset6/BT2/dict16KiB/lc2/lp0/pb0/nice24. Optional policies retain
their legacy template/header/codec, and the F2 artifact remains4445 unchanged.

The actual F8 first cost is4474→4445 B. Ordinary F8 generation independently
reproduces source/native/bootstrap/whole twice, then the unchanged positive
verifier body passes quit/EOF sessions,8 legal GO, persistent9TIDs with eight
worker CPU observations, exact restored native, absent private paths/readers
and physical exit. No old F2 runtime is relabeled as an F8 run. Its external
normal index is
`a4b0a1653b3c5d05874b75055263b82c14d5df14e3fbe45329b40575297ef979`.
F2's helper extraction separately passes one ordinary --dev build and complete
byte comparisons of shipping, DEV and all three pre-name outputs; its existing
selected-runtime evidence is reused by exact artifact identity. External index:
`218335abe9b267fb834609e104fb572bd1b829bd1d9a5d49583ab98b04c4dd31`.
These are fixed local profiles, not final512-core scaling or strength evidence.

## A4580 worker epilogue and F4445 handler pairs: 2026-10-22

A shares worker startup arrival and completed-job reporting at the loop head.
The existing local worker pointer is null only during startup and becomes the
nonnull worker argument before think. This marker is independent of epoch wrap.
Both phases decrement pending once under the same mutex; spurious command
wakes remain inside the predicate loop. Startup finished broadcasts change2→1,
while final readiness and all job-result/drain notifications retain their
predicate and ownership order. Partial-create, wrap and spurious-wake paths are
source-reviewed; no new fault-injection coverage is claimed.
Source8987→8965 B and bootstrap9951→9929 B give whole4582→4580 B.
Native length stays18576 B but the complete native identity changes.
Ordinary --dev shipping/DEV reproduction and the unchanged actual selected
verifier pass; startup, multiple GO, cancellation/drain and quit/EOF have
their existing positive-session scope. Build/runtime receipts:
`a2ceb3096e1afd0985f91f35be6fdd46a7f2a582a28f560ce92e49cfc5242a86` /
`c1c182308bd7d5bfce0fc4232c28f92a326dfd89f177d668b714d410701c2c2b`.
External A promotion index:
`126bf6de6e37a3269e8d72affed206b1818c9748ec53965059df97101b501082`.

F expresses each signal2/15 install/reset pair as the same ordered calls in
a small for-loop. The new module-local s is not consumed by later logic and
does not capture the stop handler's local signum. Masks, blocked child spawn,
private directory, compiler group cleanup, fd exec, argv and stdin retain
their expressions. Bootstrap9506→9478 B gives whole4447→4445 B with unchanged
source/native/DEV and header/codec. Ordinary --dev shipping/DEV reproduction
and actual selected quit/EOF sessions pass8 legal GO, exact native, stable3TIDs
and physical exit. Build/runtime receipts:
`4d06f4e12ee52d99ef4fda8b745b33757e2a193dbd4247ecc8ddd95225267145` /
`2df071c90e8e4a883810ef2509be1a2e23b985b095105fe1673bd3039af39917`.
External F promotion index:
`3d56a7ecee712852fe2cb21de6097f4848d53242cf447ed9af51f604bfff4e8d`.
The original wrong raw-length expectation failed before encoding and stays
external; no successful first-cost or product run is repeated.

F8 updates only its F-builder provenance pin. All three actual pre-name
outputs and current source closure retain its exact base; its own4474-byte
normal/9-TID positive evidence is reused without a new local product run.
External consumer index:
`71e090c1c77a330632efcb2863642e3e21ad87d7231c59b160e5f64242efef80`.
Optional F's4319/4045 policies and current full-reference C are unaffected
by the bootstrap-only change. These local fixed2/TT18 results leave484/349 B
above4096; final resources, compact policies and strength remain open.

Separate B/E mate-distance branch sharing shortens each actual C by20 B,
but whole5073→5074 B and4946→4948 B are size losses. Each fixed candidate
gets one compile and encode plus strict restoration; no normal or runtime
qualification is run and neither is selected. Source contracts preserve
the bounded signed TT decode, ply and actual E evaluation clamp. Their
native lengths tie but complete bytes differ. External B/E cost indexes:
`ac93c8941fa1d367b6b5f36d25e3ba94aa3434fa69bfe73e00aa7e6cfa4c2805` /
`c8c3aaafc5f7b6e77c44ec8e92745ddb625264ee9b6ad56224cc7c4626ab2099`.

## Full F4447 and the explicit F8 source stage: 2026-10-22

The prepublication NVCompact0.6 tool artifact finds five private binding-name
changes in the current F4468 context. Source8538 and bootstrap9506 retain
their lengths; whole4468→4447 B uses the same73-byte header and fixed BT2/
16KiB ALONE recipe. All59 one-byte token edits have exact inverse and unchanged
gap proofs. Actual typed binding and macro checks, eight newly produced native
compiles and a complete-byte readback retain native18576/SHA92671066. The
bounded search reaches512 evaluations with unvisited round2 singles and
systematic combinations; neither complete-space search nor optimality is claimed.

The pure maintained shipping_names.py replays those edits after history_path
from current canonical inputs. It reads no research artifact, AST or tool output.
Ordinary full --dev regeneration reproduces shipping and unchanged DEV twice;
the unchanged selected verifier executes the actual4447 wrapper in quit/EOF
sessions with8 legal GO, exact native restoration, stable3TIDs, absent private
paths/helpers, reader EOF and physical exit0. Both optional normal builders
also reproduce their unchanged4319/4045 tuples twice, while their separate
full-reference copies follow the new spelling stage. Optional DEV/runtime are
not rerun. External promotion index:
`e326abd82394b02a0e88a00c9ceff370fe1067ae60ba655acc3543473149bb30`.

The producer now emits source-before-names.c at its selected output and both
attempts. Those three files remain8538/SHA47353a15. F8 explicitly consumes
that stage instead of the selected renamed main.c; workflow and producer
closure pins follow the same contract. Its six-role specialization, base C,
native, legacy77-byte bootstrap/header, BT4 codec and4474-byte package are
unchanged. Existing source_closure and actual pre-name readback pass; prior
normal/9-TID positive receipts are re-read and reused, with no new local F8
compile/encode/runtime. A collector's initial wrong complete-field assumption
is preserved separately from the existing positive passed result. Consumer
index: `b9c2007805486e2414163e8e08954f671813934c351e014b37a0f77834aaa818`.

Checkpoint30b79d0 passes terminal C/Rust and Node22/24 CI in
[engine39637804738](https://github.com/daejunnom/Rove4k/actions/runs/39637804738)
and [repository39637804644](https://github.com/daejunnom/Rove4k/actions/runs/39637804644).
All four actual checkouts are mergec0b1f259, parents761bdc0/30b79d0, with
the requested20132288 tree. C regenerates F4447 and optional4319/4045 with
selected sessions, D5908/6111 and its two positive engine forms, and F8 using
the explicit source-before-names.c input with its4474 identity and two positive
sessions. Subsequent A4580/F4445 are not part of that run. External CI index:
`e8711c6437ef4631fd25abeaa2722df57664d5a29a5a89f20ba38ce1b18829af`.
Final4KiB eligibility, resources, compact policies and strength remain separate.
No npm republish is needed: public
NVCompact0.6.0 and its direct-OIDC release are already complete, and the public
tarball matches the prepublication tool artifact used by these experiments.

## Shared stream headers and cached B evaluation: 2026-10-22

Checkpoint4ad936b passes terminal Engine C/Rust and Repository Node22/24 CI in
[engine39635516445](https://github.com/daejunnom/Rove4k/actions/runs/39635516445)
and [repository39635516557](https://github.com/daejunnom/Rove4k/actions/runs/39635516557).
All four actual checkouts are mergefc99bdd2, with parents761bdc0/4ad936b and
the same1777240c tree as the requested head. The C log regenerates
A4582/B5073/C4880/E4946/F4468 and optional4319/4045; each selected file passes
two runtime sessions. F8 separately reproduces its exact4474 identity through
actual recipe/build/verifier gates and passes two positive sessions. That
size is source-gated, not a direct size field in stdout. C-only maintained/F8
steps are skipped in Rust; Rust's own contracts, generic A-F build and actual
process verification pass. External CI index:
`5f5d1039b54677efab94822d1256208fc8632ee98107f47385d90d5b656ce369`.

The preceding0f41df9 head passes terminal Engine C/Rust and Repository Node22/24
CI in [engine39630537886](https://github.com/daejunnom/Rove4k/actions/runs/39630537886)
and [repository39630537927](https://github.com/daejunnom/Rove4k/actions/runs/39630537927).
All four actual checkouts are merge154b62ef, with the same856c8b2f tree as that
head. Its logs execute A4586/B5079/C4884/E4950/F4470, optional4319/4045 and
fixed8 positive runtime; they precede the following new local bytes. External
CI index: `23bc67dbdf98f16daece00768e375cd564335f8b437cd8193f17b82eec764cdd`.

A/C/E now select the shared73-byte stdin/xz header from frozen source_package.py.
Their existing local77-byte launcher inputs and bootstrap templates remain
available to legacy consumers; encoding, source, bootstrap and complete native
are unchanged. Each new whole is first bound by replacing only the exact old
header in the actual qualified artifact. No encode is needed for that cost
proof, and strict restoration recovers the same whole bootstrap. The ordinary
builders independently reproduce shipping and DEV twice, followed by unchanged
selected quit/EOF sessions: two sessions/eight legal GO results per family,
exact native restoration, three startup TIDs and physical exit. A4586→4582,
C4884→4880 and E4950→4946 each save4 B. External normal index:
`67e0a521d6fd089f0ab0b6da465d523c8ce86d1be84983f0d254fe9a007e0855`.

B reuses the unchanged raw static evaluation in correction error calculation.
The sole shipping expression changes zi-p->s*p->v to zi-zF; source10409→10402 B,
bootstrap11448→11441 B and fixed77-byte whole5079→5077 B. Native remains26296 B
but has a new full identity; old native qualification is not inherited by size.
Actual-source fatal ASan/UBSan focused comparisons cover55 paired cases,
including actual same-position singular calls, SEE and correction clamp edges,
with typed Board/job/history/TT/learner agreement and input Board immutability.
The shared73-byte header then gives combined5073 B using the identical payload.
One ordinary --dev build reproduces the final tuple and unchanged DEV twice;
the unchanged selected verifier executes that5073 wrapper in quit/EOF sessions,
eight legal GO results and physical exit. The source-only5077 cost/focused scope
and combined5073 normal/runtime scope remain distinct.
External B normal index:
`7721b85ad77501c65983abb3eb3bc082e949c621abc1f819624b37dced5dfd94`.

F's full-only bootstrap preparation now inlines its single-use compiler
environment dictionary. Environment copying moves inside the blocked-spawn try;
no code or handler between the two locations changes the environment, and
existing mask restoration, PID publication, child cleanup, private directory
and descriptor exec remain. Shared legacy template, optional policies and F8
own packaging are unchanged. Bootstrap9511→9506 B gives whole4470→4468 B;
source/native remain8538/18576 B with their exact prior identities. One ordinary
builder reproduces shipping/DEV twice and actual4468 quit/EOF sessions pass
8 GO, exact native restoration, three TIDs and physical exit. F8 binds only
the new producer build pin; nonexecuting closure readback passes53 inputs with
the exact same base C, while its own4474 normal/runtime receipts are reused.
External F normal index:
`dee6faf9042035ed7c7e0ac292d9f4577baee1db6f9b79eb4c03eaadeaaf54a0`.

Two independent structural first costs are not selected. A's same-order pawn
push/ray sharing cuts source46 B but changes the native from18576 to22672 B
and whole4586→4594 B under the original77-byte context. D's HQ global-prefix/
private-path proposal changes raw source+5 B, native8000→7968 B and actual
BSS175064→109540 B, but fixed packet4974→4978 B and whole6111→6115 B. Existing
mapped extent/guards/ISA/codec remain. These are whole-size losses, not semantic
failures or claimed RAM/performance improvements; candidate runtime is not run.
Original guard rejection, source/identity contracts and costs stay external.
A post-terminal bare-PID reporting assertion also fails separately; subsequent
reads cannot establish its cause, and the actual cost is not rerun or relabeled.
External A loss index: `6aec7a12abc12f50109beb004921c7885cb5474621c8f7c6d560adc88aaddbd7`;
D loss index: `f41538beb60871187692589427ca0febb213bc616dd83343e101875513995872`.

A separate old-HQ loader-only compiler trial keeps the exact8000-byte native,
4974-byte packet, source/flags/format and changes only cc to Clang18.1.3; both
recipes already use-Oz. Loader/header1137→1220 B gives whole6111→6194 B(+83).
One loader link runs; native compile, encode, baseline relink, ELF execution
and reproduction are zero. The same entry/PHDR permissions are observed with
the larger LOAD file/memory size. This candidate is also not selected. External
index: `8cfb0393a09b18d8ea0abd04bb73ee34505f344b42f50dc2780b030352c51055`.

Every default remains above4096 B. Further source/codec/layout work, an eligible
D own-ELF, final profile/policy choice, resource and candidate-game evidence
remain open. Training, AWS and reservations remain outside this work.

## C/E capture metadata: 2026-10-22

The preceding bd23577 checkpoint passes both language jobs and the terminal
workflow conclusion in
[engine run39629093009](https://github.com/daejunnom/Rove4k/actions/runs/39629093009),
and Node22/24 in
[repository run39629093308](https://github.com/daejunnom/Rove4k/actions/runs/39629093308).
Actual checkouts use mergef9b59db8 with the same4b220950 tree as bd23577.
The C log actually regenerates and executes A4586/B5079/full F4470, optional
F4319/4045 and the separate fixed8 positive path. Those CI results precede the
following new C/E bytes; their own next-head CI is a separate observation.
External bd23577 CI index:
`055b74efa2c0feef2e9337f66829a6903a6c28281eced60763e7940891c0ad93`.

C and E now store capture-only metadata in the free bit3 of a valid0x88 from
square. FROM uses119, while TO, PROMO and the17-bit TT move domain keep their
roles. Generator classes0/1/2/3 separate quiet moves, nonpawn captures, quiet
pawn pushes and pawn captures/EP. Quiet promotions keep tag0 and still use the
separate promotion predicate, preserving quiet ordering/noise. The generated
metadata replaces the repeated mailbox capture helper and its three consumers.
Canonical and DEV remain in their existing representation; the late shipping
helpers own each exact input/output and preserve the complementary source.
Old and new live TT raw states must not be mixed.

C shipping source falls9958 to9882 B, native26336 to26304 B and whole4897 to4884 B.
E shipping source falls10286 to10210 B, native26368 to26336 B and whole4962 to4950 B.
Both retain full search, learners and TT. C's signed-net eight-lane/128-bit SIMD
and E's untrained E19 model,19 logical coefficients and21 physical slots are
unchanged. These are source/representation changes, without feature removal.

Existing actual-source fatal ASan/UBSan fixtures cover51 C and52 E search/state
cases plus affected-move bridges. They compare decoded moves, Board/evaluation,
ordering, history/continuation/correction and full TT state, normalizing only
the new move metadata; separate mailbox observations check capture tags,
EP/pinned EP, quiet/capture promotions, castling and king-capture rejection.
This is not raw Move/native identity or complete state-space/PVS coverage.
Each ordinary builder reproduces shipping and unchanged DEV twice; unchanged
selected verifiers execute the actual4884/4950 wrappers in quit/EOF sessions,
eight legal GO results each, exact native restoration, three startup TIDs and
physical exit. Generated fixtures, outputs and failed preparation remain external.

C's first cost supervisor fails before compiler/codec execution because its
serialized edit offset is a float. The corrected external supervisor changes
only that offset type and executes the one candidate cost; the original error
is preserved. E's first fixed cost and qualification have no failed attempt.
No model training, AWS use, games or target scaling comparison is included.

External C normal index:
`b5c8328cce75c499f11f1700631ea0a8baf319f416f139097cb017947e92cefe`;
focused index: `023f106532478d7819f2386bb7da95c040eb775cd9971445c780a60e04f45168`.
External E promotion index:
`7f4d5411f6a3aca0fa868beb3d7a125afa8fc75af61d702a158a4d3b2b65ba7e`.

## Cached evaluation, dead instrumentation and fixed packaging: 2026-10-22

A reuses its unchanged raw evaluation in correction error calculation. The
canonical uses `best-evaluation`; the shipping source changes `H-p->s*p->v` to
`H-F`. Existing spelling passes consume an explicitly recovered reference and
the final shipping stage restores the same cache expression. Canonical text
increases one byte; actual shipping source falls8995 to8987 B and the complete
file falls4587 to4586 B, with a new18576-byte native. Fatal Clang18 UBSan-trap
old/new search observations cover correction use/update, recursive Board
immutability and exact logical snapshots over three deterministic states.
The initial missing sanitizer-runtime link failure remains separate. Ordinary
shipping and new DEV reproduce twice; the unchanged selected verifier passes
quit/EOF, eight legal GO results, three startup TIDs and physical exit. External
promotion index: `5c3d6a7d54b81890361d59588bb0fb9cfa8424e59bc995c39ef8f613fc5e7eef`.

B removes the private singular-depth temporary and the empty instrumentation
branch left after shipping counter removal. The same short-circuit condition
still contributes0/1 to the same four child-depth consumers. Shipping source
falls10421 to10409 B and the complete file falls5086 to5079 B; its complete
26296-byte native and canonical/DEV remain byte-identical. Normal shipping and
DEV reproduce twice; actual selected-wrapper quit/EOF sessions pass eight legal
GO results and the existing restoration, reader and physical-exit checks.
External B promotion index:
`ec64f58df447acd92ed5b93581a02cd58d145f02549b68fe4f8322840d819780`.

Full F now adopts the separately replayed NVCompact0.6 result:4476 to4470 B.
The new shared `engines/scripts/source_package.py` owns fixed ALONE encoding
and a73-byte stdin/xz shell header. The full recipe selects preset6,16KiB
dictionary,lc2/lp0/pb0, BT2 and nice24. Numeric liblzma match-finder18 is BT2;
an initial HC4 name-translation error produced a different whole file and is
preserved as a failed build, rather than accepted by changing expectations.
The corrected ordinary builder reproduces the exact trial/replay4470 bytes
and unchanged DEV twice, and its actual selected wrapper passes quit/EOF,
eight legal GO results, exact native restoration and physical exit. Source8538,
bootstrap9511 and native18576 remain byte-identical to the preceding full F.
The optional material/noise and material/move-TT branches explicitly retain
their legacy77-byte header and fixed codecs; their4319/4045-byte evidence is
reused where the complete influence inputs are unchanged. The separate F8
profile retains its own4474-byte package and resource evidence. Its producer
closure now binds the new F build and shared packer; its actual source, own
encoder, build, verifier and expected output remain unchanged. One read-only
closure check passes; existing normal/runtime receipts are reused. External
F packaging index: `a7983d0a342c7f273dbaab72b04503ca203d238ba2ca0960333f795df627d904`;
F8 closure index: `dcd399596545a9ce67126558cd022962030429f7616b044bc825cfbe1189e4ee`.

The preceding b9c3a5c checkpoint has terminal-success C/Rust jobs in
[engine run39625474239](https://github.com/daejunnom/Rove4k/actions/runs/39625474239)
and Node22/24 jobs in
[repository run39625474539](https://github.com/daejunnom/Rove4k/actions/runs/39625474539).
Both engine checkouts are mergec68874ae, whose tree equals b9c3a5c's tree.
The Engine run aggregate was still in_progress/null at the last15:39:19Z API
observation; job success is not relabeled as a terminal workflow conclusion.
Those logs actually regenerate B5086, full F4476, optional4319/4045 and the
fixed8 positive runtime. They precede the new local A/B/F changes above.
External CI index: `97fa982b3648bec25c9023595370409e1361f768808c07ef3676ba5e0338cce8`.

Every default family still exceeds4096 B. Source/dataflow reduction, D's own-ELF
size, final compact policy/profile selection, target resources and candidate
games remain open; training and AWS remain excluded. Local byte reproduction,
focused semantics, process lifetime, CI, strength and organizer acceptance keep
their separate scopes. No reservation or scheduled follow-up is used.

## Maintained B/F history checkpoint and NVCompact 0.6: 2026-10-22

B now removes its private piece-plus-six function and substitutes the same int
addition at its two consumers. The signed-piece domain, single argument evaluation,
13-by-13 learner indexes and all remaining source bytes are retained. Source falls
10451 to10421 B; the complete26296-byte native remains byte-identical. Normal
shipping and unchanged DEV each reproduce twice, followed by the unchanged
selected verifier: two quit/EOF sessions, eight legal GO results, three startup
TIDs and physical exit. Complete B falls5098 to5086 B. External normal index:
`12b2a28fe56942d0768bc2b5b3cc801a3bd9c6ce395127491f52a48b945c0378`.

Full F shares the immutable published job-prefix history and stores only active
branch keys in each worker. Equality at repetition distance==ply still selects
the current root key from the global prefix. Main may replace that prefix only
after every worker finishes think/MTD/correction/result and drains. The four
positioned edits retain every comparison, halfmove test, learner and TT site;
32 earlier focused paired observations retain their own bounded scope. Source
8559 to8538 B yields complete4479 to4476 B. The ordinary builder reproduces
shipping and unchanged DEV twice; selected quit/EOF sessions pass eight legal
GO results and process/image/path/reader exit fences. Existing optional4319/4045
files retain their exact bytes. External full-F promotion index:
`0388f86ebc1d9619bb169c351dff77fe1e87bfe758867ad1d4b57c08e6743733`.

The separate fixed-eight-worker F specialization is measured and normally
reproduced at4474 B, down from4478. Its unchanged positive verifier observes
persistent nine TIDs, activity from all eight search workers and eight legal GO
results over quit/EOF sessions, followed by physical exit. Its own source/native
identity is distinct from full F's two-worker profile. Initial missing-parent
and raw-CRLF-versus-frozen-LF hash failures occurred before compiler/codec work
and remain preserved; the successful normal run uses the existing LF freeze
contract. External F8 promotion index:
`2549d360f52ab7a3a07ba65e51bebbdf3ac96c6ad9f7dcabe05125f1cd6703c2`.

NVCompact0.6.0 is publicly published by the exact main8646205 OIDC
[release run39621550516](https://github.com/daejunnom/Rove4k/actions/runs/39621550516).
The public tarball and the installed CI artifact are byte-identical. One bounded
external trial on full F measures4470 B, six below4476, with the original8538-byte
C and complete native unchanged. This is a73-byte shell header and codec choice;
source search accepts no C edit and stops at its declared evaluation budget.
A separate replay reproduces the whole file; independent strict ALONE restoration
recovers the exact original bootstrap/C, and a short default-preserving UCI probe
passes eight cases with three legal GO results. This external candidate has not
replaced the maintained4476 recipe. Its replay/quick observations are not the
complete selected verifier, strength, many-core or organizer acceptance. External
trial index: `6bc1c44ba006816528bdeab99983b03e9272fdd05abe78aeb7ea6c31690d12f8`.

All default entries remain above4096 B. Remaining work includes source/dataflow
reduction across each family, D's eligible own-ELF, compact policy integration
where selected, final profiles/resources and bounded candidate games. Training
and AWS remain excluded. These local receipts precede this checkpoint's new CI.

## Generic fixed-A root source specialization: 2026-10-21

The general C and Rust engines already implement explicit root splitting,
groups, PALS and hybrid policies. This checkpoint derives a smaller source
form from each existing mode 1 root scheduler. It does not add another scheduler
or replace the maintained tiny entries' loose policy. The new generic forms
require A/shipping/model0, two search workers, TT18 and three total engine TIDs.
No public resource UCI options are added. Canonical engines and existing loose
source/metadata remain unchanged.

C removes unreachable policy branches from bound canonical files, retaining
its completed NORMAL-slot reuse for compatible first/depth/generation/window
and bound. Rust derives its scheduler from canonical tokens instead of the
loose template. Its exact first proposal seeds the incumbent and finished=1;
cache=None and first_job=1 skip that first task. Mode 1 does not produce the
PALS Some-cache or approved Repair results. Each language retains its own
evaluation, correction and TT meaning; this is a same-language source
comparison rather than a language-only matched pair.

One ordinary shared build compiles seven natural forms with GCC 13.3 and
Rust 1.97. There is no independent second native rebuild in this checkpoint.
The lexical-to-root comparisons are:

| Language | Actual compile-input source | Native ELF | Generic whole source package |
| --- | ---: | ---: | ---: |
| C | 60,283 → 44,098 B | 30,768 → 30,768 B, distinct hashes | 21,175 → 15,140 B |
| Rust | 64,853 → 38,458 B | 374,952 → 373,672 B | 24,961 → 16,151 B |

The C source comparison includes compiler conditional specialization and
function pruning; Rust uses structural then lexical generation. The separate
whole costs use the same frozen generic LZMA/XZ-preset9/base85 envelope and
include source restoration and compiler settings. Four encodes and four strict
restorations pass exact source maps, archive/argv/environment, XZ EOF/trailing
checks and lifecycle AST comparison. Those packages are not executed by the
cost check. This generic context does not replace the maintained tiny-entry
sizes above or establish 4096-byte eligibility.

Existing structural unit regressions pass 13 C and 16 Rust tests without skips.
Separate real-search adapters consume exact canonical/generated sources with
shipping constants: C uses two UBSan compile/run pairs, Rust two non-test
compile/run pairs. They exercise actual first-child ply1/history, TT/window
bounds, mate/draw and partial-result/root-TT separation, completed-depth
retention and the unchanged deadline value. C additionally observes actual completed
NORMAL reuse and lower-cutoff aggregation. Rust observes the final first-job
skip/completion state and 40 real jobs over two depths; the initial finished=1
publication instant remains a source observation. Time-limited node traces
are not required to be identical and are not performance comparisons.

Production original/selected pairs separately pass four quit/EOF sessions per
language: 12 C and 28 Rust legal GO results, fixed 3-TID startup, GO/position drain
fences, GO-followed quit/EOF, reader/sampler joins and physical process/group/TID
absence. No forced cleanup or product source repair is needed. These checks
do not establish strength, scaling, race-freedom by measurement, PVS-retry
coverage or final-server acceptance. C does not independently observe whether
the GO-followed shutdown reaches pending or active work, or a midflight wall
deadline; Rust separately observes active work. The CI step compiles the new forms and
records any startup checks allowed by the existing local execution policy;
the external actual-search fixtures retain their narrower local scope.

The first supervisor attempt fails before CLI exec because its child limit
exceeds its inherited hard limit. That failure is preserved separately; the
successful second supervisor changes only limit inheritance and performs the
one actual shared CLI build. Source-index intake verifies 111 explicit file
references before documentation annotations. Reports, adapters and generated
artifacts stay outside Git.

## Reattached size analysis and next structural work: 2026-10-21

The reattached Korean PR12 analysis describes `a3546f1`, not the current
maintained entries. Its recommendations are reference material, rather than
new execution instructions. Current source already contains F's beta-only
kernel, C/E's TT sentinel and consumed-sort-prefix reductions, A's fixed
lexical reuse, and D's own context decoder. Historical byte savings cannot
be added to the current table. Fixed engine-local declaration reuse also
does not establish a general NVCompact block-scope allocator.

The separate Rust D structural path generates a finite shipping
entry from the exact canonical seven-file closure. Canonical sources,
builder, nonzero node/depth diagnostics and legacy infinite/stop trace keep
their existing identities and assertions. The generated shipping path uses
uciok only, finite bare/clock GO and unsupported-command consumption; it
omits global diagnostic node-budget observers and reset jobs while retaining
worker-local deadline polling, Result.depth selection, TT/correction and
all completion/join ownership. This is an explicit shipping protocol change,
not equivalence for every legacy input. The existing data8 geometry guard
must admit the actual new image before packing. Source design alone is not
a size, execution or many-core result.

The external reconciliation and concrete before/after design are preserved
in `rove4k-analysis-reconciliation-20261021-evidence`. The attachment SHA-256
is `c2dc4b008fa51310bf41caa1eab21e1362488304cdc9183797d525effc1736eb`;
reconciliation is `54e6618c1f69531091d29bc4191347f6cc91b3ed6058678c60572f50a976455c`.
Current normal entries at `eb5e05b` pass both language jobs in the
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39586669714)
and Node22/24 [repository checks](https://github.com/daejunnom/Rove4k/actions/runs/39586669681).
The checked-out merge tree equals that head's tree; future source candidates
retain separate qualification states.

A full F Board check-cache candidate, informed by the actual ice4 source
comparison, measures 4,495 to 4,493 complete bytes. Its one fatal ASan/UBSan
compile/run passes eight fixed actual-search/MTD cases with typed Board,
keys/learners/TT, score/witness and node equality; 59,060 cache oracle checks
also pass. However, actual search-phase attack calls increase from65,023 to
120,469: +55,446, or85.27%. Make calls and successful makes stay59,087 and
58,877. The increase exactly equals successful makes minus3,425 claimed
search entries and six root correction guards. This finite work count is
not a wall-time or strength measurement. The two-byte size gain remains
unselected in this source context; normal production/SMP is not run for it.

## Fixed eight-worker full-F local comparison: 2026-10-21

The separate tiny-entry-f-resource8 entry consumes the exact8559-byte full F
base source plus a frozen project source closure. A pure six-literal late
specialization fixes8 search workers and TT18, with9 native TIDs including
the controller. Chess constants, successful-created-count shutdown, full HCE,
learners, coherent full-key TT and full-depth MTD(f) remain. Existing F profile2,
canonical/DEV and reduced policies are unchanged. No public resource option or
external research receipt/native is a normal build input.

Complete profile8 is4478 B, one byte below its same-context profile2 control.
It remains382 B above4096 and does not replace the two-worker table above.
One ordinary builder reproduces source/native/bootstrap/whole/payload twice.
One positive verifier passes quit/EOF two sessions with eight legal GO results,
the actual stable9 TIDs, all eight workers' active state and CPU-tick increase,
native/private-path identity, position fence, reader completion and physical
process/group/observed-TID exit. No forced cleanup or error remains.
VmSize74972 kB, startup VmRSS7552 kB and active VmRSS8320/8064 kB are snapshots,
not peaks, timed strength/scaling results or final-server resource acceptance.

The new verifier's process-publication signal issue is fixed locally before
normal execution, with independent source review; generic helpers, original
child masks and legacy3-TID assertions are unchanged. The first-cost package
envelope omission is preserved, with successful native reuse only in a separate
packing extension. Normal two-fold regeneration is independent of that cost.
The C-only CI step uses the existing ordinary F main.c as --base-source, then
runs this profile's own builder/verifier; existing artifact globs cover it.

Root checks25 normal-index file references and all51 registered source hashes.
The external final index is b4afc17ea61b1f0be235ef156d437d01245942a7fee42bd33933a120bf2974a9.
Official4k rules and the4kVII event page do not specify the final thread/RAM
allocation used here; that allocation remains unknown. The general TCEC
512-thread description is not substituted for an official4k assignment.

## Preserved metadata and QS-query costs: 2026-10-21

The single full-F signed8 Board metadata candidate ties4479 whole bytes with a
new native identity; layout, RAM, stack and functional execution are unmeasured,
so it is not adopted. A's corresponding independent candidate saves one whole
byte4587→4586 but expands native18576→22672: RX grows60 B and its following
alignment gap grows4036 B. Header-derived LOAD address union grows one4KiB
interval; actual RSS/Board/stack/speed are unknown. That candidate stays held.

A separate F QS-query-sharing candidate moves unchanged legal-query functions
and connects a common terminal/draw epilogue. It costs4494 B,15 B above4479, so
it remains unselected without focused or target execution. Original candidates,
inverse/gap proofs, fixed package contexts, costs and reasons remain outside Git;
none is a permanent exclusion for another source, packaging or resource context.

## Shared B/E derived history length: 2026-10-21

B and E remove a private Worker history cursor and derive the same entry
length from immutable published job history plus existing ply. The existing
repetition-bound local is reused; the scan retains its nonnegative clamp,
parity and reversible window. Ordinary children write the same key index
and advance ply; B's same-position singular verification keeps the same ply
and history length. All recursive argument vectors are byte-protected.

One shared pure shipping_history_depth.py maintains the two fixed source
classes with five edits, six protected gaps, complement pins and full inverse.
It runs after lazy fallback, only for shipping. Canonical/DEV, B's selected
SEE/singular/learner policy and E19 evaluation/ordering/physical21 slots remain.
Raw source shrinks40 bytes in each family. Complete files change B5116→5098
and E4974→4962, with explicit new native identities; Worker layout/native
equality or measured memory savings are not claimed.

One fatal ASan/UBSan compile/run per family passes50 B and52 E actual old/new
pairs. Original cases and learner observations remain, with targeted history,
parity, half99/100, TT, terminal, stop and cap127/max-write4222 boundaries.
Independent actual Worker types retain all typed fields, keys, three learners,
Board and full TT/locks; the old restored cursor equals base+ply. Direct
fixture-only base adapters do not enlarge the public history1..4096 contract.
Individual PVS/singular branch runtime coverage remains unmeasured.

Each ordinary builder runs once, reproduces shipping twice and unchanged DEV
twice, then its unchanged selected verifier passes quit/EOF two sessions with
eight legal GO results, exact restoration, three TIDs, private-path cleanup
and physical process/reader/group exit. All first executions pass; final
recipe/README annotations are separated from producing inputs. Root checks59
B and103 E normal-index file references. Their external normal indices are
eba1dc0dcdaf0e540b3916de309154d472217e7bae5116020bf1b0992f27074a
and7cdb375654ba80410febd47512101e36721df931b890de202e21038f1a80e843.
No fresh/archive, added core/game, or many-core/strength acceptance is claimed.

## Shared lazy fallback and full-F legal QS cutoff: 2026-10-21

A/B/C/E/F remove a stored global fallback and its eager GO query. The sole
result consumer queries the same immutable root with private scratch only
when the selected completed best is zero. That last worker still owns the
mutex after all think calls return; output/flush precedes completion wakeup.
Three owned regions and four protected gaps retain winner/tie selection,
generation, wait and join. GO work, query timing and scratch stack ownership
change; no stack-peak, timed speed or many-core result is claimed.

Complete normal files change A4592→4587, B5122→5116, C4908→4897 and E4986→4974.
Full F selects the combined lazy/QS form4483→4479. Its lazy-only4478 form is
one byte smaller, but the selected QS form stops after the first legal make
when a quiet QS standpat already reaches beta. It retains terminal precedence,
legal witness, score/depth0/lower-bound/full-key TT publication and learners.
The component's eight fixed serial cases retain typed state and3425 nodes;
make calls59087→18119 and attacks65023→24055 count omitted pure work, not
timed speed or strength. Lazy fallback's separate seven-case actual-output
comparison covers both zero-best sides, terminal0000, depth winners and ties.

Seven ordinary builders and five unchanged selected verifiers pass on their
first executions. Every default reproduces shipping and unchanged DEV twice
and passes quit/EOF sessions with eight legal GO results, exact restoration,
three startup TIDs, private-path absence and physical process/reader exit.
Both optional F actual files stay4319/4045 byte-exact while their full reference
passes history→lazy→QS8559. Optional DEV/runtime is not repeated.
A preparation schema KeyError occurred before builder/compiler/codec/target
execution; its original script/trace is preserved separately, then its adapter
was corrected. No ordinary builder or selected execution was retried.

The normal handoff is preserved outside Git in
rove4k-common-lazy-fallback-promotion-20261021-evidence/
qualified-normal-handoff.json, SHA-256
bf30aed69b7ebac32d6067538a01d3d5ff60abe1eefc6915f1dbb685946b3303.
Root independently checks its37 raw file pins. The completed normal index
is61628 B/SHA-256386182d0c92a2212dd7316161c6963748b7500e78451db346106d66ef3f97f66,
in the same external folder. Root checks129 distinct file references, resolving
historical working-source identities through portfolio-producing-v2 and current
source through final17. Normal results total10 sessions/40 GO. Source reviews
find no actionable shared-helper or F-hook issue. Canonical/DEV and reduced actual F
bypass both new stages. All default entries remain above4096; final resource,
many-core, explicit split/group/PALS integration and strength work stay open.

## D HQ-only derived history length: 2026-10-21

The HQ shipping path removes its private Worker history cursor and derives
the same length from immutable game_length plus ply. Scalar and every DEV
branch retain the original declaration, repetition, push/pop and reset text.
The scalar trial's5-byte size loss remains unselected; actual ordinary
regeneration preserves the old scalar native, packet, whole and audit bytes.
HQ changes6,123 to6,111 complete bytes with new8,000-byte native identity
`3c662941aa11af8521d3c601322e9aa38405a3bfbeb9332d55008907217a4b2e`.

The first static attempt stops at its old exact BSS contract: actual memsz
is175,064 instead of175,092. That failure is preserved. A new literal HQ
class binds the actual hash/size/entry and BSS175,064 while keeping RX2pages,
BSS176,128-byte mapping, guard/reserve/NX and fixed21 model. Old identity
classes stay admitted and the guard bodies are unchanged. This section-size
change is not a Worker sizeof or physical RAM measurement.

One fatal ASan/UBSan compile/run passes18 actual old/new HQ search pairs,
typed keys/three learners/Board, full atomic16 TT, score/witness/nodes and
old cursor restoration. It covers history1/4096, repetition/parity/half99/100,
ply127/child4222 and claim/stop/TT/terminal/QS paths. Branch coverage is not
inferred from nodes. A single compile-only CHECKPOINT identity discovery
prepares the new6,134-byte audit; it does not execute the target.

One ordinary builder reproduces both native/whole forms twice and one audit
per form. The unchanged positive verifier passes two pre-entry observations,
four quit/EOF sessions and12 legal GO results, actual RX/BSS/padding/guard/NX,
persistent startup TIDs, stdio, child absence and physical reader/process
exit. Only its EXPECTED data changes; root verifies the other29,214 bytes
retain SHA-256 `389ac04925b5ab4597a34a9ac8b318de572da9b0d9b293b384eea785f10cc4fa`.
The external normal index is
`rove4k-d-hq-history-normal-promotion-20261021-evidence/final-index.json`,
9,141 B/SHA-256 `5d71546fa5490c44960fbadd6b44c810cd968d257d4463d4c71a222908ce2158`;
root checks26 exact file pins. No new trace/RIE/negative/fault campaign runs;
4KiB, final target resources, many-core and strength remain open.

## C derived history length: 2026-10-21

C removes its private cursor in five fixed shipping spans and derives length
from immutable game_length plus existing ply. The prior repetition-end local
holds that length; i>=max(0,length-1-half) becomes the same bounded parity
scan with two conjuncts. Root, four child/re-search ports, balanced returns
and job publication preserve the relation. SIMD/evaluation, canonical/DEV,
model, existing stages and recursive arguments remain unchanged. Source
10,032 to9,992 B gives whole4,924 to4,908 B, with a new26,368-byte native.

One fatal ASan/UBSan compile/run passes51 actual old/new SIMD search pairs,
retaining all31 prior search/special-child cases. Typed keys/three learners,
Board and eight vector lanes, complete TT key/data/locks, score/witness/nodes
and old-cursor restoration agree. Root lengths1/4096, repetition/parity,
half99/100, ply127 and actual child slot4222 are covered. Private entry-ply
adapters retain their domain; branch coverage is not inferred from nodes.
The unchanged learner exhaustive proof is reused rather than rerun.

One ordinary --dev builder reproduces shipping and unchanged DEV twice;
the unchanged selected verifier passes quit/EOF sessions with eight legal
GO results, native restoration, startup TIDs, private-path absence and
physical process/reader exit. A parent preflight schema-key failure occurs
before any builder/compiler/target execution; the original is preserved,
and a one-line adapter correction precedes the single actual normal run.
The external normal index is
`rove4k-c-history-depth-normal-20261021-evidence/final-index.json`,20,391 B,
SHA-256 `0c76e4521fde16c0be16417e760635970accef23932a2c8474001aecb7535d4a`;
root checks its69 exact file-reference pins. C remains812 B above4096.

## Maintained finite Rust D shipping: 2026-10-21

[tiny-rust-d-shipping](../engines/compact/tiny-rust-d-shipping/README.md)
specializes the exact canonical seven inputs using17 fixed spans and full
inverse/gap guards. The original Rust D sources, builder, nonzero-budget
diagnostics and legacy trace stay unchanged. Nine maintained source files
provide generation, fixed2/18 scalar/HQ build/packing and a separate positive
verifier, without external report inputs. Minimal finite protocol, global
diagnostic observer removal and reset-job removal are explicit shipping
contract choices. Worker-local deadline polling, Result.depth selection,
TT/correction, publication and physical join remain.

Whole costs are11,108/11,476 B,295/286 B below the same-model controls. Native
lengths tie16,816 B with different identities; fixed data8 geometry and
native/load/payload/whole pins are separately admitted without broadening
the original packer's C class. The ordinary builder reproduces native and
whole twice per form and passes unstripped/static/no-undefined audits.
One positive verifier checks native/whole scalar/HQ with quit/EOF: eight
sessions and64 GO/initial-position legal results, actual mapped image,
three persistent TIDs, two guarded stacks, finite clocks/bare GO, bounded
ASCII/replay and physical reader/group/TID exit. Sleeping idle workers,
hard real-time deadlines, all loader conditions, many-core and strength
are not established by this positive run. Existing legacy checks remain
separate; no new ptrace/RIE/fault/negative campaign runs.

The original first-cost linker resource failure and runner handler-shadowing
error remain preserved. A separate corrected finite-AS attempt succeeds;
that success does not diagnose the original linker's exact resource cause.
The final normal index is
`rove4k-rust-d-shipping-maintained-normal-20261021-evidence/final-index.json`,
18,779 B/SHA-256 `07967b276ffbf6c9fe4c2fe08fa1c3c971cd478f872e523cf9c7b1fd38e5af46`;
root checks38 exact file pins. An independent source-only review finds no
actionable issue, including actual helper/oracle closure. The workflow now
registers this new entry's ordinary build and positive verification beside
the unchanged canonical Rust D checks; dispatch and success remain separate.

## Full F derived history length: 2026-10-21

Six fixed shipping spans remove Worker.g and its balanced reset/push/pop;
repetition reads and child-key writes derive the same indices from immutable
job qh plus existing recursion ply. Every actual U child advances ply even
when QS depth saturates at0; each MTD root re-enters at ply0. Public qh1..4096,
ply0..127 and the4224-key capacity are unchanged. Source shrinks8,587 to8,566 B
and the actual complete file4,495 to4,483 B. The18,576-byte native has a new
identity, `cc751d06f4e215e6ac80c39ae906a67d9230b677fbb43520df0d77789bb191cb`.

One fatal ASan/UBSan compile/run passes90 old/new pairs: all18 prior search,
13 TT-horizon and44 history cases, plus15 boundary/re-entry cases. Typed
Worker keys/learners and Board values, full TT key/data/locks, score/witness,
nodes and old-cursor restoration agree; raw Worker layout is not the oracle.
The maximum child slot4222 is actually written. Direct nonzero-entry-ply
fixtures retain explicit private base=length-ply adapters, which do not
extend the public qh domain. That fixture does not run think or the pool.

The ordinary full --dev builder reproduces shipping and unchanged DEV twice;
the unchanged selected verifier passes two quit/EOF sessions with eight legal
GO results, exact new-native restoration, stable startup TIDs, absent private
paths and physical process/reader exit. Both optional ordinary builders
reproduce unchanged4,319/4,045-byte actual files and consume the new8,566-byte
full reference. Optional DEV/runtime and extra fresh/core/game/SAN runs are
not repeated. The external normal index is
`rove4k-full-f-history-derived-normal-20261021-evidence/final-index.json`,
11,187 B/SHA-256 `4895d4a0381bf7b289d15c5a91d714ad90931afbf28f6619cc5617c5f958c52e`.
Root independently checks its35 exact file pins.
Full F retains positional HCE, all learners, full-key bound TT and MTD/SMP;
387 B above4096 and final hardware/many-core/strength remain open.

## B continuation context: 2026-10-21

B passes the successful made child's signed piece slot through all four PVS
calls, supplies neutral6 at root, and forwards the current row through
same-position singular verification. Black-king row0 is valid. Excluded TT,
learning0 and the other search arguments, SEE, cancellation and the existing
positive learner are protected. The child row read moves to its initialized
private caller Board; general read-timing equivalence is not claimed. Seven
fixed spans/eight gaps and inverse replay shrink source10,548 to10,507 B;
whole5,138 to5,122 B. Native remains26,304 B with a different identity.

One fatal ASan/UBSan compile/run compares36 actual old/new search pairs,
full Worker/TT/Board and score/witness/nodes. It includes128 legal children,
22 special-child pairs, four black-king row0 pairs, signed quiet contexts,
seeded singular-eligibility conditions and direct excluded/learning0 state
preservation. Runtime singular-call/PVS-branch coverage is not instrumented;
eligibility and node counts do not establish those branch observations.
One ordinary --dev builder reproduces shipping and unchanged DEV twice, and
one unchanged selected verifier passes quit/EOF sessions with eight legal
GO results, native restoration, three startup TIDs, private-path absence and
physical process/reader exit. Canonical/DEV and the existing SEE policy remain
unchanged. This local result leaves1,026 B above4096 without a new strength
or many-core claim.
The external normal index is
`rove4k-b-continuation-context-normal-20261021-evidence/final-index.json`,
9,951 B/SHA-256 `58339d45c3f6b1c068282c4d448bf5ffe1328d65822d64f5f58c19053f0fdd4b`;
root independently checks its30 exact file pins. The unselected F cache
focused index separately has17 checked pins, without promotion.

## A derived history length: 2026-10-21

The last shipping stage removes the private Worker cursor and derives its
value from immutable job history length plus existing recursion ply. Root
establishes that relation, all four child/re-search calls advance the same
ply, and the old balanced push/pop restores it before cancellation handling.
The production pool waits for prior work before publishing a new position,
so job history length cannot change during think. The two repetition bounds
and child key write retain their exact indices; no recursive argument is
added. Six fixed spans, seven protected gaps and full inverse guard the
9,040 to 9,011-byte source transform. Canonical/DEV and earlier stages remain
unchanged. Worker layout and native identity change.

One fixed compile/encode measures 4,606 to 4,592 complete bytes. A fatal
ASan/UBSan compile/run compares 16 actual old/new search cases using typed
logical fields, full key and three learner arrays, TT key/data and lock state,
score/best/nodes and old-cursor restoration. It covers root history 1/4096,
repetition windows and parity, terminal/TT/claim/stop paths and direct boundary
entry at ply127 and maximum child slot4222. Raw Worker layout/padding is not
the equality oracle. These direct boundary calls are not claimed reachable
as a complete game; node counts do not establish runtime PVS/LMR coverage.

One ordinary `--dev` builder reproduces shipping and unchanged DEV twice;
the unchanged selected verifier passes two quit/EOF sessions and eight legal
GO results, exact new-native restoration, stable startup TIDs, private-path
absence and physical reader/process exit. No extra fresh/core/game/performance
run occurs. The normal index is
`rove4k-a-history-depth-normal-20261021-evidence/final-index.json`, 5,093 bytes,
SHA-256 `7f101ee6d44a25507a1022e439895dd6ad62a0368e2b0c328db5bfccb3a5cff9`.
The separate paths.json resolves its 28 reference pins to 27 exact files;
root independently verifies all of them without changing the original index.

## D ordered castling sharing: 2026-10-21

Two independent K/Q castling branches become one +1/-1 direction loop in
maintained native/board.c. Ordinary king moves still precede K then Q;
rights masks, b/c/d/f/g emptiness, home/transit attack short-circuit order
and raw Move values are preserved. The 255 to 198-byte fragment reduces the
board source by57 bytes. Actual whole cost changes from 5,914/6,125 to
5,908/6,123 scalar/HQ. Native sizes change to 7,612/8,000 with new identities.

One fatal ASan/UBSan scalar compile/run compares actual old/new walk on448
roots: both colors, all16 rights masks, blockers, home/transit attacks,
rook absence and king away from home. Complete pseudo ordering,9,936 moves,
512-slot tails, Board preservation and592 actual attacked calls per lane
match, including call order/arguments/results and Board snapshots. The
changed fragment is common to both slider backends; HQ SAN is not repeated.

One ordinary builder reproduces each scalar/HQ native and complete file twice
and each CHECKPOINT audit once. One unchanged positive verifier passes two
pre-entry observations and four quit/EOF sessions with12 legal GO results,
exact RX restoration, zero BSS/padding, guard/NX, three persistent startup
TIDs, stdio-only descriptors, child absence and physical reader/process exit.
Only the packer's two exact identity/model maps and verifier EXPECTED data
change. Root confirms the other29,214 verifier bytes retain SHA-256
`389ac04925b5ab4597a34a9ac8b318de572da9b0d9b293b384eea785f10cc4fa`.
The runtime source, model/ISA/profile/codec, RX2-page/BSS175,092 geometry and
guard logic stay fixed. No new negative, fault or trace campaign runs.

The external normal index is
`rove4k-d-castle-direction-normal-promotion-20261021-evidence/final-index.json`,
7,677 bytes, SHA-256
`e9b81b8594c769d21e3fd8b020c2bd251fa7352e0003a31edc7a2e7e6a3a8bf2`.
Root verifies its21 exact file pins. Producing inputs and raw receipts remain
separate from receipt-only annotations. Neither this fixed local result nor
the reduced size establishes final target resources, many-core strength or
4KiB eligibility.

## E continuation context and positive bonus: 2026-10-21

The final shipping-only stage passes the signed already-made child piece slot
through all four PVS calls and supplies neutral slot 6 at the root. A quiet
nonpromotion cutoff reuses that slot as the previous parent-FROM learner
column. The learner's only two callers pass positive depth squared within
1..126, so abs(bonus) is redundant in this fixed domain. Seven exact spans,
eight protected gaps, full inverse and unchanged readable-source identity
guard the 10,400 to 10,360-byte transform. E19 coefficients, evaluation and
ordering, board/move generation, TT, correction and pool/input bodies remain
byte-identical; canonical/DEV bypass the stage.

One candidate compile and one fixed encode measure 5,004 to 4,986 complete
bytes. Native length stays 26,400 bytes but its complete identity changes to
`1b034d2f517e847acdd950590d212bc1cd1c8b76a20a95f7735938e0ebae8781`;
old full-native equality is not claimed. A fatal ASan/UBSan compile/run compares
34 actual old/new search pairs, complete Worker/TT state, score/best and
caller Board preservation. It covers 128 legal children, 22 special children,
both signed quiet contexts and observed history/continuation updates. The
35 learner boundary cases supplement the separately reused C exhaustive
proof after checking the exact same formula, types and bounded caller domain.
Four source PVS ports are checked; runtime coverage of all four branches is
not claimed.

One ordinary `--dev` builder reproduces shipping and unchanged DEV twice.
The unchanged selected verifier passes two quit/EOF sessions and eight legal
GO epochs, exact new-native restoration, three startup TIDs per session,
private-path absence and physical process/reader exit. No fresh, additional
core, strength or timing campaign is run. Cancellation causality remains
unproven. Producing recipes/sources and the initial pre-execution heredoc
SyntaxError are preserved separately from final PASS annotations.

The external normal index is
`rove4k-e-search-context-normal-20261021-evidence/final-index.json`, 9,893 bytes,
SHA-256 `54f2a9ade366ef28067316762fa68207a0874a7497e1e39f195be1708af91420`.
Root independently verifies all 26 referenced file pins. The helper is frozen
by the ordinary builder and included by the dynamic fresh source closure;
fresh extraction itself is not executed. Source, component proof, normal
selected execution and subsequent-head CI keep their separate scopes.

## Full F plain-int spelling: 2026-10-21

A single fixed source form inserts `#define S int` after the seven includes
and replaces 91 genuine plain-int keyword tokens with S. No S token existed
in the admitted source or its directives. Headers, integer-width identifiers,
literals and all 93 intervening gaps remain exact. The late pure helper
checks the full 8,755-byte input, 8,587-byte output, 92 edits and complete
inverse; it runs after fixed macro expansion in full shipping and the optional
policies' separate full-reference generation. DEV and actual optional sources
bypass it. Source locations and macro/source dumps are outside this manual
fixed-source representation contract.

Two actual fixed-compiler preprocessing runs have identical complete 87,169-byte
output and 20,564-token sequence. One candidate compile reproduces the entire
18,576-byte native with empty diagnostics. One unchanged-codec encode measures
4,497 to 4,495 bytes; Python and independent CLI strict restoration pass. This
is a two-byte complete-file gain, not the 168-byte raw-source delta.

One ordinary full `--dev` builder reproduces shipping and unchanged DEV twice,
and the unchanged selected verifier passes two quit/EOF sessions and eight
legal GO results. Both optional builders reproduce their unchanged complete
shipping files twice and actually check the new 8,587-byte full reference;
optional DEV/runtime are not repeated. Normal commands finish with rc0 and
no live owned process groups. No new core, strength or cancellation-causality
claim is made under this full-native-identical change.

The external normal index is
`rove4k-full-f-int-token-normal-20261021-evidence/final-index.json`, 10,409 bytes,
SHA-256 `979a69ce7dce6abdc6e8ecaad9e298fe4c163226b8801c9181d7cd60751cb02e`.
Root checks all 33 referenced file pins, independently of the earlier 30-pin
first-cost index. Producing sources and recipe precede the final PASS
annotations. The first source-preparation offset assertion failure is kept
separately; it occurred before candidate/compiler/codec output and is not
overwritten by the successful fixed boundary.

## Shared environment snapshot: 2026-10-21

The A/B/C/E/F bootstrap templates now construct `e=dict(os.environ,TMPDIR=d)`
at the same point as the previous copy-and-assignment expression. The copy,
TMPDIR override, compiler argv and stdin, signal masking, Popen ownership,
cleanup, signal restoration and deleted-file FD exec retain their contracts.
The six-byte source reduction leaves each compact C source, native image,
DEV output, model and resource profile byte-identical. Source spelling,
columns and failure-traceback bytes are outside this manual representation
equivalence claim; this is not NVCompact compile-input-only admission.

The fixed comparison measured three forms against each exact existing control;
the following numbers include the complete launcher and compressed payload.
Signal-helper sharing removes 39 raw bytes but loses in every measured context.
The combined form also loses to env-only. All controls, transformations and
unselected forms remain reconstructible in the external source-plan evidence.

| Context | Existing | Signal helper | Environment only, selected | Both |
| --- | ---: | ---: | ---: | ---: |
| A | 4,610 | 4,618 | 4,606 | 4,611 |
| B | 5,144 | 5,150 | 5,138 | 5,143 |
| C | 4,934 | 4,937 | 4,924 | 4,930 |
| E | 5,010 | 5,018 | 5,004 | 5,014 |
| F full | 4,505 | 4,509 | 4,497 | 4,499 |

The original codecs stay fixed per context, including A's existing encoder
settings, C's nice_len 64, B/E/F's nice_len 32 and optional F MoveTT's lc0.
Two additional fixed optional-F encodes measure 4,319 and 4,045 bytes; their
source/native identities are unchanged. The shared F template's three policy
expectations and both optional hardcoded consumer dictionaries are updated
together. These optional results do not qualify default F.

Each of the five ordinary default `--dev` builders reproduces shipping twice
and unchanged DEV twice. Each unchanged selected verifier passes its two
quit/EOF sessions and eight legal GO epochs, exact native restoration, three
persistent startup TIDs, private-path absence and physical process/reader exit.
Each optional F builder independently reproduces shipping twice and checks its
new full-reference source path; optional DEV and runtime are not repeated.
All seven builders and five verifiers finish at the first attempt with rc0.
Cancellation causality, new strength and final hardware are not established.

The final external index is
`rove4k-bootstrap-env-normal-20261021-evidence/final-index.json`, 20,482 bytes,
SHA-256 `31677eccefc1c3d51fa012efb4dd242076ad361fda1b69f04b87b273a93baa91`.
It pins the actual raw receipts and producing recipes separately from later
PASS annotations. Root independently verifies all 68 referenced file pins.
This local qualification does not relabel earlier-head CI as a run of these
new wrappers. Further source reduction, default F's remaining 401 bytes, D's
eligible own-ELF and final many-core/resource and candidate-game comparisons
remain active work; training and AWS remain excluded.

## Rust D source-sharing costs: 2026-10-21

Two independent fixed proposals keep the maintained seven-source closure,
compiler, two-worker/TT18 profile and archived data8 ASCII packing context.
The first carries child continuation context and specializes the reachable
positive learner. The second outlines the generic Linux syscall helper;
raw_spawn and its new-stack assembly trampoline remain separate. Both shorten
source but increase actual executable text and complete packed cost.

| Fixed form | Scalar complete bytes | HQ complete bytes | Text delta scalar / HQ |
| --- | ---: | ---: | ---: |
| Reused control, independently re-encoded | 11,403 | 11,762 | 0 / 0 |
| Search context and positive learner | 11,418 (+15) | 11,778 (+16) | +80 / +64 |
| Outlined syscall | 11,435 (+32) | 11,793 (+31) | +48 / +48 |

All complete native files stay at 16,816 bytes due to layout; that length tie
does not hide the changed text or substitute for whole-file measurement.
Four primary native links, six encodes and six loader links finish. Both
control whole hashes reproduce exactly and all six fixed strict roundtrips
and existing data8 geometry predicates pass without relaxing their guards.
No engine, loader, trace, negative campaign, repeat or unstripped run occurs.
Neither candidate is selected or runtime-qualified. Inputs, exact inverse,
comparison conditions and unselected forms remain outside Git for later
same-context comparison; these losses impose no permanent name-based ban.

The actual first-cost receipt is
`rove4k-rust-d-source-sharing-cost-20261021-v1/cost.json`, 91,218 bytes,
SHA-256 `a4d5c97430ceb127a1d2e0722adf3c00d8f1ef69916bcdd29a1375fb5c243419`.
These Rust packed costs do not replace the maintained C D pair or establish
4KiB eligibility for either language.

## Starting checkpoint: 2026-10-20

Base: develop `56bfb5f45bff59a570d3f04f8eba06332d53c052`.
The base contains NVCompact and repository contracts, but no chess engine.
The implementation uses a separate owned feature worktree. Existing checkouts
and completed package release worktrees are preserved.

| Workstream | Implemented evidence at start | Work still required |
| --- | --- | --- |
| A, C and Rust | None | Legal state, incremental bookkeeping, HCE, PVS/QS, TT, histories, correction, SMP |
| B, C and Rust | None | Bitboards, shared attacker calculations, SEE, qualified singular exclusion |
| C, C and Rust | None | Real AVX2 operations, scalar comparison, native build and restoration |
| D, C and Rust | None | Small OS/start path, scalar/HQ, internal ELF restoration and integrated SMP |
| E, C and Rust | None | Frozen integer evaluation and ordering, exact encoding/decoding, inference bounds |
| F, C and Rust | None | MTD(f), lower/upper convergence, stable evaluation and interrupted iteration handling |
| Parallel policies | None | Shared search, explicit tasks, groups, all three PALS stages, hybrid selection |
| Submission artifacts | None | Source/native wrappers, standalone ELF, complete size accounting and reproduction |
| Acceptance | None | Independent move oracle, special moves, search/lifecycle, candidate features, size and bounded games |

Implementation ownership is divided between C, independent Rust, frozen model
data, parallel scheduling, build/packing, and behavioral verification. Shared
interfaces are coordinated before another owner edits a source file. Generated
executables, test logs and archives stay outside the repository.

## Runtime contracts

Shipping builds expose the 4K command subset: `uci`, `isready`, `position startpos
[moves ...]`, clocked `go`, one final `bestmove` per search, `quit` and EOF.
`stop`, `ucinewgame` and unsupported commands are consumed safely. Development
builds may additionally expose FEN, perft, legal moves, state/hash/evaluation,
depth/nodes/movetime and diagnostics. Resource option parsing is outside the
shipping executable.

The search worker count and TT allocation are build inputs. The stdin/control
thread counts toward the process total; a profile with 512 total threads may
therefore contain 511 search workers. Local verification uses small fixed
profiles on the available eight logical CPUs. Profile generation is not evidence
that a 256/509/512-thread target has been run or scales well.

All jobs in one search share its cancellation and original wall-clock deadline.
An interrupted iteration is not a completed bound. Position replacement, reset,
quit and EOF wait for owned workers before their state is reused. Hints,
completed compatible bounds and rule conclusions remain distinct.

## Verification environment

WSL2 Ubuntu 24.04.4, x86-64, glibc 2.39 is available locally. Current tools:
GCC 13.3.0, Python 3.12.3 and Rust 1.97.0. AVX2 is exposed; AVX-512 is not.
WSL execution explicitly selects the existing `stemxstudio` account.
The 2026-10-20 read-only refresh confirms kernel
`6.6.87.2-microsoft-standard-WSL2`, eight visible/affinity CPUs, and Rust through
`/home/stemxstudio/.cargo/bin/rustc` rather than the noninteractive default PATH.
Subsequent Linux build, ELF/syscall, pthread, `/proc`, restoration and process
lifetime checks may use this environment, with their actual artifact bindings.
This is consistent with Microsoft's documented
[WSL2 Linux kernel and syscall support](https://learn.microsoft.com/en-us/windows/wsl/compare-versions).
AVX-512, final server timing, resource behavior and target-hardware scaling
still need their corresponding target environment; eight virtual CPUs cannot
establish 512-core performance.

The Windows managed-worktree `.git` pointer contains a Windows drive path that
Linux Git cannot interpret. Git operations therefore use Windows Git; Linux
builds use a fixed input snapshot and external output directory. Build-intensive
work uses the Linux filesystem, following Microsoft's
[filesystem guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems).
Exact source bytes and LF policies remain explicit when crossing filesystems.
New source builds and execution evidence must identify their actual inputs;
earlier NVCompact package checks do not establish engine correctness.

## Completion accounting

For each family and language, retain separate facts for functional behavior,
final counted file bytes, reproduction, fixed-resource runtime and performance.
Every family needs at least one complete artifact no larger than 4096 bytes;
D specifically needs a self-restoring ELF with no external decoder. Two wrappers
around the same engine do not establish independent C and Rust cores.

Small games are smoke evidence, not Elo or TCEC acceptance. Missing hardware,
unverified scaling or an oversized file remains an explicit outstanding item.
The goal stays active until the full in-scope plan has corresponding evidence.

## First functional checkpoint: 2026-10-20

The local `c-second` build snapshot compiled A–F in C, both original and lexically
compacted sources. The corresponding executable bytes matched for each family.
All six original executables passed the independent process harness: 48 grouped
checks covering known perft counts, special moves, legal move replay and state,
hash/repetition/halfmove bookkeeping, search output, clocks, stop/replacement,
bounded self-play and active-search quit/EOF. This snapshot used one search
worker plus stdin control. It is evidence for that snapshot, not future changes.

The independent review found and prompted fixes to rule-context TT keys,
exhausted clocks and model initialization. The initial failed builds and runtime
observations remain separate from subsequent passing evidence. Rust original A
compiled, but its compacted source exposed lexical token joining defects in the
new compactor; full Rust candidate validation was still pending at this checkpoint.

The frozen E model uses 21 signed coefficients in 26 encoded bytes. Its generator,
signed-16 exhaustive round trip, malformed stream rejection, feature references
and accumulator bounds passed nine model tests. Actual C/Rust consumers initialize
the same parameters; this is an untrained hand-authored integer model.

Outstanding work remains substantial: finish the independent Rust matrix and
algorithm-specific checks; connect and verify all parallel policies in real
engines; move allocation/workers into the startup lifetime; validate shipping
and restored execution; specialize and reduce source; measure complete artifacts;
meet each family's 4096-byte requirement; reproduce selected outputs; compare
features, cross-candidates and bounded performance. Development C binaries at
this checkpoint were 30,768 bytes, and no size eligibility was established.

Completed model work was reassigned to the planned SIMD plus E cross-candidate.
Parallel scheduler protocol tests are supporting evidence; they do not establish
that the full engine uses the scheduler correctly.

## Fixed-pool and semantic checkpoint: 2026-10-20

Both languages now contain their own A–F search cores. A uses incremental HCE
at the actual leaf; B uses legal SEE and a qualified same-ply excluded singular
search; C consumes AVX2; D consumes HQ sliding attacks; E consumes the frozen
evaluation and ordering model; F runs MTD(f) with matching-depth TT intervals
and preserves the lower-bound move witness. These are implementation facts,
with the focused evidence below, rather than final portfolio acceptance.

The startup lifetime includes every search thread, TT, worker history, correction,
PV and scheduler workspace. In both languages the coordinator is worker zero;
the input thread makes the total `search workers + 1`. Repeated searches retain
the same Linux task IDs. The five policies have actual engine integration and
small-profile runtime evidence. Rust still allocates `Vec` objects in board move
generation and play, so startup preparation does not establish allocation-free
search or a fixed total RSS. Target256/509/512 profiles remain compile-only.

The frozen `pool-matrix` snapshot built all 12 candidates from original and
lexically compacted sources. Every form was independently compiled again with
identical resulting bytes for that form. C original/compact files also matched
one another; Rust original/compact files differed and require separate runtime
checks. The external process matrix passed 83 of 96 groups. Its 13 failures were
terminal score/stale root result handling and F's repeated-search horizon
contract. Newer sources fix those causes; that older run remains a failed
snapshot. The first exact-head CI also failed on a model fixture admitted as a
second C main and the terminal Rust cases. Production model input admission and
the fixture suffix have been corrected. Fresh matrix and CI evidence is required
for the new combined source.

Focused current-source evidence includes:

- C A/D: 4,158 legal states per family, 532,224 independent attack queries per
  run, incremental state/evaluation parity and 45 special moves; optimized and
  ASan/UBSan signatures match.
- C B: ten SEE fixtures, cancellation, a real depth-3 TT qualification followed
  by depth-6 singular execution, and excluded-search preservation of TT, board,
  path and learning. Positive controls demonstrate normal continuation, killer
  and correction updates before checking their absence under exclusion.
- C C: 400 actual SIMD evaluations match an independent scalar recomputation.
- C F: three low-branch positions match independent full minimax, including an
  attaining move, TT-retained repeats and cancellation preserving the last
  completed result. Five repeated `go infinite` searches no longer terminate
  early from contradictory mixed-horizon bounds.
- C actual A/PALS, B/loose and F/loose: four-worker lifecycle runs pass ASan/UBSan
  with stable startup task IDs and bounded node consumption.
- Rust: 28 optimized integrated unit tests pass in WSL. D HQ matches independent
  scalar rays over 786,432 occupancy cases; B SEE observes original cancellation
  inside recursion. Terminal reuse and F bound/move witnesses have regressions.

Source work is independent of NVCompact. Conditional specialization, source
reachability pruning, a fixed-policy scheduler and a smaller shipping UCI path
reduced an A complete source ZIP from 12,734 to 9,513 bytes in the first structural
snapshot. Later representations and native forms need their own records. This
remains above 4,096 bytes. The own-ELF decoder executes real restored C/Rust
payloads without an external unpacker, but no complete A–F ELF is size eligible.

The C+E comparison uses identical frozen sources and profile, changing only the
explicit model flag. Runtime-verified minimum complete files are C baseline
12,931 / C+E 13,873 bytes and Rust baseline 20,586 / C+E 20,588 bytes. These
minima can select different packaging forms; matched-form deltas are retained
in the external comparison. Thirty-six shipping searches establish bounded
responses, one final move and clean exit; they do not establish NPS or strength.

Remaining work is the fresh final-source matrix/CI, shipping/restored chess
validation, further candidate-specific source and runtime reduction, at least
one actual complete file at or below 4,096 bytes for every family, D's eligible
own-ELF path, and bounded comparable games/performance. Full target resource
execution and scaling have no evidence on this eight-logical-CPU WSL host.
Training and AWS remain excluded. The full A–F goal stays active.

## Whole-matrix checkpoint: `d31056a`

An immutable Git archive of `d31056a459942369f219bf98e91111af8b6154dd` was built
in a separate Linux directory. All 24 original/compact native forms compiled;
each form's independent second compilation produced identical bytes. The six C
compact files match their original executable hashes and reuse only that exact
runtime evidence. The twelve Rust executable hashes are checked independently.

The final process matrix passed **144/144 groups across 18 distinct executables**:
six C and twelve Rust original/compact forms. Every group checks its actual fixed
startup total of two tasks before UCI input, with stable task IDs through search
and cancellation. Two C/Rust pairs (A and F), each with colors exchanged, also
passed four bounded games. These remain short legality/lifecycle games, not a
playing-strength comparison. The final reports and transcripts are retained
outside Git under `final-d31056a` and `final-d31056a-verification`.

The corresponding [CI run](https://github.com/daejunnom/Rove4k/actions/runs/39335785952)
passed the full Rust job. C stopped before engine compilation because the newly
added standalone scheduler fixture relied on an include-directory flag absent
from CI. The fixture now includes its header relative to its own source, and
the exact CI compile/run command passes locally. Commit `491415d` contains only
that fixture correction. Its [fresh CI run](https://github.com/daejunnom/Rove4k/actions/runs/39336276080)
completed successfully for both C and Rust. The repository lifecycle workflow
also passed for that SHA. This does not cover subsequent uncommitted source work.

Further source reduction is assigned by actual cost: the optional A shipping
board removes unconsumed bitboard/fullmove/material fields while retaining
incremental HCE/hash and exact legal replay; compact search work preserves the
family-specific algorithms; Rust work replaces per-node heap collections with
bounded storage; E compares lossless coefficient representations including their
decoder and consumer cost. None changes the full portfolio completion criteria.

## Coherent TT and bounded Rust storage: `de5676d`

A deterministic mixed-publication example exposed a false hit in the old C
XOR key/payload protocol. A–E now use a full 64-bit key and seven payload bytes
under one exclusive atomic-byte CAS, retaining a 16-byte slot. F's paired
32-byte slot protects both directions under the same lock; key replacement
invalidates both payloads. A busy reader misses and a busy writer skips the
slot. No concurrent plain payload access occurs outside the lock. Optimized
and sanitizer fixtures exercise actual engine publication and replacement,
including eight-thread collision runs. This is a correctness change, not a
notation-only optimization.

Rust now uses a checked 512-entry move list with an initialized prefix and a
101-key reversible history. Admitted positions contain at most sixteen pieces
and eight pawns per side; the conservative pseudo-move bound fits the list.
History older than the retained suffix cannot change the halfmove-100 result;
checkmate still takes precedence. Actual A–F depth-three searches perform zero
allocations after startup. The larger fixed Board is 1,080 bytes, versus the
previous 288-byte heap-backed value, so this is not reported as a Board-size
reduction. A normal B search reaches ply 96 on a 1 MiB worker stack in both
optimized compiler profiles and returns an unfinished result at its limit.

Direct start-position construction removes the shipping FEN dependency. Rust
test bodies now live under `engines/tests/rust`, with unchanged `rustc --test`
entry points, and are absent from production source archives. In a matched A
shipping recipe the complete minimum source file decreases from 21,732 to
18,427 bytes. Frozen input, compiler and actual file hashes accompany each
phase; this remains oversized.

The new immutable native matrix again passes **144/144 groups across eighteen
distinct executable byte streams**, plus four bounded A/F games. Every process
has two startup tasks with stable task IDs. All twenty-four native forms match
their own independent second compilation. The actual archive inputs use CRLF;
their LF-normalized contents match the named Git commit. Reports hash the
actual input bytes and do not assert raw Git-blob byte identity. External
records are `final-de5676d/build.json` and
`final-de5676d-verification/results.json`.

## Controlled structures and complete-file costs

The optional [A mailbox experiment](../engines/experiments/mailbox/README.md)
implements all four real engine combinations, with one frozen source basis,
evaluation, search features and fixed resources:

| A representation | Minimum complete source | Minimum complete native wrapper | Board | Worker |
| --- | ---: | ---: | ---: | ---: |
| 0x88 / copy-make | 13,035 B | 16,000 B | 696 B | 211,936 B |
| 0x88 / make-unmake | 13,378 B | 16,406 B | 696 B | 211,936 B |
| 10x12 / copy-make | 13,053 B | 16,416 B | 664 B | 196,064 B |
| 10x12 / make-unmake | 13,396 B | 16,792 B | 664 B | 196,064 B |

All four agree on the score, PV, completed depth and node count of six
single-worker searches. Eight optimized/sanitizer oracle runs, 72 native
behavior groups, 40 selected whole-wrapper groups and 32 two-worker groups pass.
This records the declared frozen experiment, not automatic acceptance of those
older artifacts as the latest coherent-TT submission.

The [F experiment](../engines/experiments/f/README.md) compares actual C/Rust
paired/single TT storage and previous-depth/same-parity first guesses. The
default remains paired/previous. All four configurations retain full keys,
matching-depth intervals, the attaining lower-bound move, completion-only guess
updates and cancellation. Selected complete files reproduce and pass actual
shipping checks. At 262,144 slots the paired/single TT allocations are C 8/4 MiB
and Rust 6/4 MiB. The measured source files are C 13,167–13,207 bytes and Rust
18,980–18,996 bytes: a smaller TT does not automatically make a smaller file.
Observed C coordinated root rounds and Rust summed worker probes are distinct
metrics and are not compared across languages.

The D scalar/HQ comparison uses exactly the same frozen producer, source,
toolchain, profile and flags except for the attack implementation. All 140
complete artifacts pass startup and independent reproduction. The selected
whole-file costs are:

| D language | Scalar source / HQ source | Scalar native wrapper / HQ wrapper | Scalar own ELF / HQ ELF |
| --- | ---: | ---: | ---: |
| C | 12,995 / 13,152 B | 13,528 / 13,726 B | 20,205 / 20,476 B |
| Rust | 18,960 / 18,962 B | 155,757 / 156,082 B | 248,162 / 248,948 B |

All twelve selected D files now also pass sixty full shipping behavior groups
using clocked go: actual source/native/self-ELF execution, legal results,
replacement, stop, quit and EOF. A separate strengthened rerun pins every actual
file SHA and requires exactly three startup tasks, stable identities and a
three-task peak; all sixty groups pass. The earlier observation-only report is
preserved, not rewritten. Concurrent producer startup observations are not used
to rank performance. All forms exceed the size limit. The validators record
output/signal ordering without proving cancellation causality.

Additional optional C source work shares PVS/QS control, specializes fixed
Loose SMP, removes unreachable production code and narrows proved worker state.
The qualified coherent-TT source minima for A–F are respectively 9,356, 9,953,
9,659, 9,668, 10,176 and 9,546 bytes. Corresponding source/native launchers pass
sixty shipping groups; their final lexical forms execute the same hashed ELF
bytes. This source work does not depend on NVCompact. The new central
`--shipping-operations` integration passes its separate full generation pipeline:
all thirty-six native forms start and reproduce, including independent source
regeneration. The six new operations natives also pass thirty shipping groups
with exact three-task startup and stable task IDs. This integration run does
not create complete wrappers. Its deadline sampling is explicitly per-worker
rather than aggregate.

E storage work retains every coefficient of the untrained model. Six exact
representations have complete-file cost evidence; a 42-byte immutable table
outperforms the 17-byte encoded payload in that frozen recipe once decoder and
consumer costs are counted. The central `--model-format varint|static16` path
freezes its pure source transform and canonical model. Fresh `de5676d` varint
and static16 producers now pass 140/140 artifact startups and reproductions.
Actual C consumers pass coefficient/evaluation/ordering/clamp checks under
ASan/UBSan; both Rust consumers pass sixteen tests using separately hashed
validation fixtures. Selected complete-file costs change as follows:

| E language | Varint / static16 source | Varint / static16 native wrapper | Varint / static16 own ELF |
| --- | ---: | ---: | ---: |
| C | 13,771 / 13,689 B | 14,049 / 13,929 B | 20,928 / 20,764 B |
| Rust | 18,960 / 18,801 B | 156,879 / 156,605 B | 249,903 / 249,367 B |

The twelve selected complete files also pass sixty shipping behavior groups,
with actual hash admission and exact stable startup task sets. Default varint
is retained; static16 is explicit. No coefficient or inference-scale change
occurs. Output/signal ordering is recorded without claiming cancellation
causality.

## Fixed-resource runtime and bounded policy study

An opt-in [target startup harness](../engines/tests/target_startup.py) admits
memory and PID headroom before launching a single process. On the eight-CPU
WSL host, A/F in both languages pass **24/24 startup cases**: totals 256, 509
and 512, each with quit and EOF. Exact task sets remain unchanged before input,
after UCI and after two readiness barriers. All processes exit normally without
forced cleanup. Startup readiness is 0.531–2.179 seconds including the stability
sampling period; maximum sampled RSS is 2,153,512,960 bytes and maximum virtual
memory is 6,547,410,944 bytes. Resource limits, admission facts and actual native
hashes are retained. No search is sent in this campaign. It proves software
startup/lifecycle under oversubscription, not target-profile search memory or
512-hardware-thread scalability. All A–F C/Rust now also compile under all three
target profiles: thirty-six configurations, seventy-two original/compact native
files and seventy-two independently rebuilt files have matching reproduction
hashes. Their central manifests explicitly retain unexecuted runtime fields;
the separate startup evidence applies only to the A/F originals just described.

A separate opt-in `target_search.py` campaign now executes all twelve A–F
C/Rust **originals at target512**, one process at a time. Each completes a short
clocked start-position search and a second search after e2e4 with work observed
before stop or quit. The independent oracle accepts exactly one legal result
per epoch. All 512 startup task IDs remain stable; every process exits normally
with no surviving owned group or forced cleanup. Maximum sampled RSS is
2,179,072,000 bytes; maximum virtual memory is 6,547,410,944 bytes. Admission and
8 GiB AS/DATA, 3 GiB sampled RSS, 60 CPU-second and 45 wall-second limits are
recorded. The initial A/F four cases and later B–E eight cases keep separate
reports, hashes and an explicit combined index. AVX2/AVX/XSAVE were verified
before C's execution. This proves those exact short searches, not arbitrary
depth memory, lower-profile search execution, distinct Rust compact forms or
hardware scalability. A byte-identical C compact may reuse its original's
execution evidence.

The five-policy A study uses four search workers plus stdin, TT bits 18, CPU
affinity 0–4 and one immutable `de5676d` source basis. **180/180 fresh-process
workloads and 26/26 bounded games pass**. Node-budget workloads finish at exactly
12,000 nodes. Every process has the same five startup tasks throughout. Games
contain 1,973 timed plies; six end in checkmate and twenty reach the declared
80-ply limit with result `*`, not a draw. Independent legal replay, clock
accounting, SAN and PGN checks agree. The study does not show that the additional
policy costs repay themselves on these small workloads. Four workers provide
only one TT group, so this is not a cross-group scaling test.

C/Rust policy runs use their actual implementations. Their HCE coefficients,
search heuristics and TT bytes per slot differ; these results therefore do not
isolate a language effect. A separately generated E experiment now aligns the
actual evaluation, ordering, heuristics, TT key/layout and resource policy for a
bounded structural comparison, described below.
No Elo, strength ranking or many-core recommendation follows from these games.

The next work is candidate-specific source reduction, fresh acceptance of
selected new cores, final candidate comparisons, further selected profile
workloads and eligible complete files for every family. Each smaller architecture
retains its own source and whole-file validation. Training and AWS remain excluded.

## Smaller A architecture and shipping command boundary

The optional [smaller A core](../engines/compact/tiny-a/README.md) is now recorded
as readable source plus a separate producer. It shares a forward piece walker
for attacks and generation, relies on the explicitly proved generated-move
precondition inside make, orders definitions before callers and removes only
known no-op shipping diagnostics under complete native-byte identity. The
512-move capacity has a conservative admitted-position proof and checked
overflow; it never silently truncates moves.

PVS/QS, incremental HCE/hash, coherent full-key TT, history, continuation,
correction-controlled reduction and startup SMP remain actual search paths.
Correction does not alter the shared TT's fixed leaf scale. Dead material,
legal EP context, repetition, mate precedence and unfinished ply-limit handling
have dedicated tests. This architecture is A only; it does not claim B–F's
distinct algorithms.

Its measured complete stream is **5,671 bytes**, still 1,575 bytes over budget.
The 75-byte shell prefix and 5,596-byte compressed stream are both counted.
Python bootstrap and C share that stream, so 75 bytes is not the complete
restoration cost. All twenty-seven native/wrapper artifacts reproduce. The
three native forms plus actual selected whole wrapper pass twenty-three
black-box groups; nine packer groups separately exercise byte preservation,
real compiler/argv/environment/I/O/status, compiler-child signal forwarding,
physical exit and cleanup. The producer now emits a hash-pinned
`validation-manifest.json` for those same four executable entries.
The single-translation-unit producer explicitly normalizes CRLF to LF while
retaining original input hashes. Twelve producer tests include LF/CRLF byte
equivalence and guarded declaration failures; the normalization leaves the
already qualified assembled C and complete artifact unchanged.

The separate [tiny-search experiment](../engines/experiments/tiny-search/README.md)
reduces this complete file from 5,671 to **5,419 bytes**, still 1,323 bytes over
budget. It removes a proved unreachable HCE clamp, unconsumed selection-prefix
stores and constant/private argument work, then accepts spelling transformations
only when actual compiled native bytes match. Its guard pins the value and
piece-admission contracts; all 768 piece-square values have absolute value at
most 910, and 32 admitted pieces cannot reach the mate-score band. An unsupported
ply limit fails preprocessing. Six structures across twelve deterministic
positions match score, best move, nodes, complete TT state and learning/path
state; baseline/winner sanitizer runs and the actual selected whole-file
shipping checks pass. Both native and whole-file independent reproduction pass.
These optional tools preserve the unmodified readable smaller A baseline.

Shipping lifecycle tests now send long **clocked go**, matching the approved
minimum interface. DEV retains infinite-search and strict node checks. Reports
distinguish work observed before a signal, output observed after it and searches
already completed before it; immediate legal completion does not establish
active cancellation. These harness changes have clock-only and immediate-result
fixtures plus a current A DEV regression. Broader D/E/operations shipping runs
use their own preserved validator inputs and remain separately tracked.

## Smaller portfolio and structural Rust checkpoint

The new compact cores make every family's specific implementation cost visible.
They are optional, separately generated candidates; the twelve canonical cores
remain available. These local measurements include the entire selected file.

| Family | Smaller selected complete file | Format and actual distinct logic | Remaining over 4,096 B |
| --- | ---: | --- | ---: |
| A | 5,283 B | Source stream; mailbox HCE/PVS, retained learning and SMP | 1,187 B |
| B | 6,283 B | Source stream; incremental bitboards, shared attackers, legal SEE and singular exclusion | 2,187 B |
| C | 6,059 B | Source stream; AVX2 gather/arithmetic HCE used by search | 1,963 B |
| D scalar / HQ | 8,540 / 8,928 B | Standalone syscall native ELF; persistent clone/futex pool and actual scalar/HQ | 4,444 / 4,832 B |
| E | 6,107 B | Source stream; all 21 untrained coefficients in evaluation and ordering | 2,011 B |
| F | 5,551 B | Source stream; exact-horizon full-depth MTD(f) with attaining bound witness | 1,455 B |

A's [encoding experiment](../engines/experiments/tiny-encoding/README.md)
reproduces the 5,419 → 5,303 → 5,283-byte chain. Fixed-resource spelling and
compiler-argument changes preserve exact native bytes within their declared
stripped/unstripped identity classes. Seven bounded XZ settings add a further
20-byte saving. The final whole file passes five shipping groups and actual
restored-image identity, startup-thread and cleanup checks. Its compiler command
`cc -Os -x c - -o x -s` is qualified only on Ubuntu 24.04.4 / GCC 13.3 / glibc
2.39; omitting `-pthread` leaves the real pthread functions and their glibc 2.34
symbol requirements present. This is not a broad compiler/host portability claim.
The 75-byte shell prefix is counted together with the compressed Python/C/argv
payload; it is not the whole bootstrap cost.

[TinyB](../engines/compact/tiny-b/README.md) passes 23 process groups, its
optimized and ASan/UBSan SEE/singular contracts, producer guards and actual
feature/context/EP/dead-material/ply-cap checks. Singular tests verify both real
qualification and a genuinely extended child, and fence excluded-node TT and
learning effects. The selected whole file also restores the exact independently
compiled stdin image, keeps three startup TIDs and leaves no compiler children
or owned temporary files. All 24 complete forms reproduce.

[TinyC and TinyE](../engines/compact/tiny-ce/README.md) pass 56 process groups
across their DEV, original, lexical, selected source and selected native files.
The AVX2 kernel's optimized and sanitizer runs compare 369,255 board positions
and 738,510 evaluations each. Actual completed C search consumes SIMD leaves.
E's production consumer checks 2,007 arbitrary/dense positions against the
independent frozen oracle, including raw/clamped evaluation, ordering and special
moves; actual search consumes both model outputs. Source and native launchers
restore their exact expected images with fixed three-task startup and cleanup.
Their board-oracle reuse is limited to byte-identical frozen board/header code.

[TinyF](../engines/compact/tiny-f/README.md) is an explicit full-depth policy
candidate: MTD(f) probes retain a stable HCE leaf scale, use only exact-horizon TT
cutoffs and publish a lower-bound attaining witness. Selective LMR is absent;
correction learns and affects actual quiet ordering rather than leaf values or
depth. This differs from the selective A/canonical policy and is not presented
as a pure spelling transform. The 5,763 → 5,703-byte structural change preserves
36 single-worker result/state observations and a 3,785-node total. Fixed-profile
spelling/argv plus two bounded XZ settings yield the selected 5,551-byte file.
Its stripped native identity is separate from the unstripped control.

The final proof passes 28 process groups, twelve independent minimax/witness
fixtures, real horizon/QS/root/mate/correction-ordering controls, node-32 and
`PLY=4` last-completed-result retention, and optimized/sanitizer full-key TT
contention contracts. Ten Linux admission/ownership cases reject cross-build,
source/native/input drift and outside paths and reap an actual orphan. The
selected whole file restores its exact expected image, keeps three stable TIDs
and leaves no compiler children or owned temporary files. Earlier audit failures
and the fixes for proof-input freezing and exception cleanup are retained.

[TinyD](../engines/compact/tiny-d/README.md) supplies `_start`, raw syscalls,
guarded worker stacks and a persistent clone/futex pool without libc, TLS,
interpreter or per-search worker creation. The selected `-Oz -flto` six-form
campaign passes 36 process groups and two bounded games. Five positions have
exact scalar/HQ depth-four score, nodes, PV and best move. Actual search and
context/abort contracts, 4,932,096 HQ kernel comparisons per mode/build and
eleven raw-runtime fault probes pass. Scalar/HQ startup-only profiles with 511
search workers pass four quit/EOF cases with 512 stable TIDs; TT bits 18 and no
search make this separate from the canonical large-TT target512 campaign.
Own-loader alternatives are larger at 8,806/9,142 bytes. The scalar ELF contains
7,952 bytes of text, 348 read-only bytes and 240 header/padding bytes. All bytes
count; neither the raw ELF nor its wrapper meets the size gate.

The D algorithm driver now applies a shared aggregate wall deadline and fixed
per-command deadlines, cleans its owned process group and writes failure/partial
transcripts in `finally`. A follow-up also runs compiler/retained-check wrappers
in owned process groups and cleans descendants on every exit path. Seven focused
fake-process cases cover normal replies, continuous info without bestmove,
exit 17, compile-stage failure and actual parent/child timeout/exit boundaries;
all terminate and preserve the intended reports. The original four-case report
and checker remain immutable. This control-flow evidence changes no engine bytes
and does not replace the earlier executable campaigns.

The separate [streaming picker experiment](../engines/experiments/tiny-stream/README.md)
is a retained failure: a shared walker/visited-ordinal design increases the whole
A file from 5,419 to 5,579 bytes. Its real legality, feature, context and shipping
checks pass, but its new plumbing costs more than the removed sorting. It also
changes tie/re-evaluation policy; no speed or strength improvement is claimed.

Rust's [guarded structural generator](../engines/compact/rust/README.md) is
integrated through the explicit `--rust-structural-compact` option. It currently
accepts only A/shipping/loose with the pinned canonical source. The pure transform
removes inactive families, diagnostics and scheduling while preserving effectful
TT writes, frozen evaluation epochs, paired bounds/witnesses and startup/physical
completion barriers. Actual raw hashes and CRLF counts are retained; only the
verified CRLF-to-LF Rust normalization is accepted, and content drift is rejected.

The central producer changes source totals from 88,157 original / 61,773 lexical
to 34,335 structural / 34,341 structural-lexical bytes. Its best complete source
file is **11,645 bytes**; native wrapper and own ELF are 155,028 and 247,102 bytes.
All 56 central artifacts pass startup and independent source/native/package
reproduction. Four selected complete files pass twenty shipping groups with
exact stable three-task startup. Sixteen transform tests include nine compiled
behavior pairs; an additional 44-position driver compares board/evaluation/search
and independent perft. The original LF/CRLF admission failure is preserved.
Earlier owner-recipe 11,675-byte results use a different packaging recipe and
are not silently substituted for these central values. Other Rust families are
not supported by this optional specialization yet.

The manifest loader also fixes compact variants to their own actual SHA rather
than inheriting the original file pin and rejects expanded-ID collisions in both
input orders before starting any process. Twelve metadata-only cases, including
two old-validator defect controls, pass. This does not rerun or replace earlier
engine runtime evidence.

Further structural work is assigned in separate experimental paths: one span
scanner/direct coordinate input path, a tagged 120-square sentinel mailbox, and
a pure bitboard D representation that removes mailbox/HQ adapters. A separate
genuinely Rust tiny core is also being implemented. Each must earn new whole-file
and runtime evidence; no size saving or final acceptance is assumed. All full-key
TT, rule, completed-result and fixed-startup contracts remain part of the work.

## Matched C/Rust implementation and submission costs

The separate [matched E experiment](../engines/experiments/matched/README.md)
uses the same actual 21-coefficient model, PVS/QS, learning/update equations,
LMR policy, total move-order tie, full-key 16-byte TT, identical Zobrist/pawn and
ordered reversible keys, four-MiB allocation and one-MiB search stacks. Both
clear and touch the whole TT before input admission. One or four search workers
run fixed loose sharing; language-specific board/rule implementations remain.
Neither common policy nor identical nodes isolates a causal language effect.

Five hash-overlay tests cover all 1,561 keys and 146 special-move/history states.
Six one-worker cold fixtures agree on every completed score/node count and final
move, while four-worker fixtures require semantic equality and stable five-task
startup without pretending shared-TT schedules are identical. Both profiles pass
sixteen independent black-box groups each.

The bounded timing campaign contains **18 valid pairs / 36 paired fresh-process
runs** across three positions, two profiles and three samples. Its first quiet
window expired after sixteen pairs because dispatch/forwarding consumed most of
the reserved interval. That report remains failed/partial, with its extra C
singleton and incomplete Rust attempt excluded from paired summaries and retained
separately. A second reserved window ran only the missing four-worker Kiwipete
sample indices 1 and 2; it passed and physically exited. Nine measurement functions
and all runtime inputs/native/tool identities are invariant across the helper
selector change. The combined index links the immutable reports instead of
rewriting the failed campaign as success.

At one worker, median parent-observed search wall times for C/Rust are
142.48/185.67 ms at startpos, 224.18/266.20 ms in the opening and 325.00/326.83 ms
at Kiwipete; exact corresponding node totals are 84,834, 92,847 and 88,002. At four
workers medians are 70.52/88.27, 114.71/130.70 and 181.44/162.50 ms, with different
actual work. These are three short local samples of exact DEV speed artifacts,
not a general language, strength or scaling ranking. Process CPU is `utime+stime`
without double-counting threads; its conservative endpoint quantization bound is
20 ms. The supervisor lacks a separate physical core, and RSS is approximate
kernel accounting. Full raw endpoints, affinity, startup, memory and order remain.

A separate size recipe reproduces and executes all sixteen selected role files:

| Search workers | Language | Whole source | Whole native wrapper | Raw native ELF | Own restoring ELF |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | C | 13,942 B | 13,918 B | 34,864 B | 20,811 B |
| 1 | Rust | 18,717 B | 164,362 B | 367,568 B | 253,793 B |
| 4 | C | 13,944 B | 14,043 B | 34,864 B | 20,980 B |
| 4 | Rust | 18,719 B | 165,799 B | 371,720 B | 256,580 B |

The [cost report](../engines/experiments/matched/COST.md) counts every decoder,
header, model and fixed compiler argument. Selected payloads and actual running
images are compared; each role passes clocked play, zero clocks, active stop/quit,
stable startup identities and physical cleanup. Larger measured encodings are
not all runtime-qualified. DEV timing binaries and shipping size binaries remain
distinct; no speed is attributed to these compressed files. Every row is oversize.

## Consumer, source-layout and dedicated-loader experiments

These separately frozen experiments extend the preceding portfolio. They do not
change the canonical C/Rust cores or silently combine separately measured gains.
The smallest new qualified C/E source files are 6,015/6,095 bytes; the dedicated
D own-restoring ELF is 7,665/7,918 bytes for scalar/HQ. All are still oversize.

| Actual experiment | Frozen control | Result | Scope |
| --- | ---: | ---: | --- |
| C startup PSQT gather | 6,059 B | 6,015 B | Same HCE, actual AVX2 leaf |
| C readonly PSQT | 6,059 B | 6,455 B | Retained adverse storage result |
| E unused shipping HCE cache | 6,107 B | 6,095 B | Cache maintenance only; tactical value() remains |
| D direct fixed-Deflate restore, scalar/HQ | 8,806 / 9,142 B | 7,665 / 7,918 B | Complete own ELF, exact admitted native images |
| D direct LZ restore, scalar/HQ | 8,806 / 9,142 B | 8,721 / 9,057 B | Larger than raw native; retained |
| D span input, scalar/HQ native | 8,540 / 8,928 B | 8,476 / 8,864 B | Parser policy changes declared |
| A span input | 5,283 B | 5,523 B | Unselected size regression |
| A tagged sentinel, controlled/new domain | 5,531 B | 5,743 / 5,719 B | Matched readable control, not the 5,283-byte control |
| A moving-side orientation | 5,527 B | 5,559 B | Relative history/tie policy differs |
| D pure bitboard, scalar/HQ native | 8,540 / 8,928 B | 8,800 / 9,088 B | Smaller RAM state, larger file |

The [C table experiment](../engines/experiments/tiny-c-table/README.md) retains
all 832 exact signed-piece/square values. The startup representation adds 3,328
shared table bytes, including 3,352 BSS section bytes after alignment, and 832 HCE
calls before workers. The readonly representation stores the same values in
source. Optimized and sanitizer production-consumer tests, real SIMD search,
all 56 black-box groups, restored-image identity and fixed startup/cleanup pass.
Its small file saving is not an NPS claim.

The [E state experiment](../engines/experiments/tiny-e-state/README.md) removes
only cached HCE from shipping Board and its two unused incremental arithmetic
updates. The capture priority still reads `value()`, so that function stays.
DEV cache/state diagnostics are unchanged. Shipping Board changes 176 →168
bytes, native ZIP 10,164 →10,113 bytes; equal raw ELF lengths do not imply equal
images. Six consumer forms per representation pass 20,000 raw/clamped model
positions, 160,000 ordering cases and 206,389 legal transitions per run, with
matching state/search/learning observations. Both forms pass 28 black-box groups
and actual source/native wrapper image/startup/cleanup checks.

Its source catalog was also replayed against all 23 actual Git blobs. One
provenance JSON has verified 1,503-byte CRLF and 1,462-byte LF encodings; all other
22 inputs match literally. Only those two exact encodings at that one path are
admitted, with actual raw hashes/counts and a separate normalized identity.
Mixed endings, lone CR and content drift fail. The original failure/catalog stay
preserved. Fresh LF baseline/state, archived LF recipe and CRLF production each
reproduce all generated sources, ten native files and 36 wrappers. Prior runtime
evidence is reused only through exact bytes; fresh LF image/startup/cleanup also
passes. Five admission/transform unit groups cover this boundary.

The [span parser](../engines/experiments/tiny-protocol/README.md) decodes external
coordinates, requires production-generator membership and applies each move once.
Replay commits only after all moves succeed. Forty-nine common groups across
eight actual forms, raw-input boundaries, seven production parser configurations,
retained search/context/ply-cap checks and eleven D runtime faults pass. New
ASCII-whitespace, malformed-number recovery and no-argument command handling
are explicit policy changes. D benefits modestly; A does not.

The [sentinel](../engines/experiments/tiny-sentinel/README.md),
[moving-side orientation](../engines/experiments/tiny-oriented/README.md) and
[pure bitboard D](../engines/experiments/tiny-d-bitboard/README.md) experiments
are retained size regressions. Their independent special-move/perft/transition,
hash/HCE/context, actual search, whole-file lifecycle and reproducibility checks
pass within their recorded scopes. Sentinel controlled search matches complete
normalized TT/heuristic/path state; orientation and pure-BB change ordering and
do not claim identical nodes. Pure BB reduces Board 176 →104 bytes and Worker
68,976 →44,400 bytes, while native/own files grow. Its checker now shares the
stable D driver's absolute deadlines, owned-group cleanup and finally-written
failure reports; a separate narrow replay preserves the old proof and matches
the actual algorithm binaries. The reduced RAM does not make it a size winner.

The [dedicated D loader](../engines/experiments/tiny-d-loader/README.md) admits
exact native hashes and geometry, restores original RX bytes at the original
entry and uses zero anonymous BSS. It rejects READ_IMPLIES_EXEC, reserves guarded
address space without replacement, decodes RW then changes it to RX, and never
uses RWX. Four files reproduce and pass pre-entry audits, production image/search/
startup/stdio/quit/EOF checks, twenty shared shipping groups and two bounded
colour-exchanged games. Four malformed decoder controls and fourteen input/layout
admission cases pass. Pre-entry audit executables remain distinct from shipping
files. Auxv, initial brk and executable identity still describe the loader; this
scope accepts only the known static images, not general ELF process equivalence.

Fixed-Deflate payloads are 6,550/6,803 bytes plus 1,115 decoder/header bytes.
Generic LZ controls contain 7,931/8,267 payload bytes plus 875 overhead bytes.
Further progress needs a smaller engine image or a better total representation.
The separate [range-code experiment](../engines/experiments/tiny-d-range/README.md)
tests exactly two intrinsically adaptive lossless profiles without training or
parameter fitting. Its best files are 7,998/8,299 bytes and remain unselected.
Codec/reference/native restore, malformed-frame, guard/ABI and bounded production
startup/search checks pass; no full shared game matrix was run for this loss.

The new [independent tiny Rust A](../engines/compact/tiny-rust/README.md) has a
160-byte mailbox, unified PVS/QS, coherent single-bound TT, private heuristics,
fixed startup pool and one frozen correction epoch per GO. It is a new policy,
not a behavior-preserving rewrite of canonical Rust. Source totals are 33,693
readable / 25,698 lexical / 23,334 DEV-pruned bytes; the selected complete source
file is **9,074 bytes** and native wrapper 145,081 bytes. Every native form and
twelve complete artifacts independently reproduce. Fourteen contracts, actual
shipping/DEV interfaces, both final wrappers' ten shipping groups and twenty
natural malformed-clock completions pass. The clock-presence bug and older
9,067-byte artifact remain preserved before the final fix.

An actual DEV-free production search reaches ply 127 on a one-MiB thread with
zero recursive allocations and aborts without publishing a partial bound. Its
measured CFA components give a representative 669,504-byte deep path, not a
universal async/standard-library stack theorem. Only A has this tiny Rust port;
all canonical Rust B–F cores remain available. CI adds its actual unit/builder/
process/clock checks at a separately named small profile.

The next isolated work covers packed move/priority state, smaller synchronous
startup-pool protocols and a single-stream Rust module layout. Selected D parser
and restoration gains must be combined and measured rather than added on paper.
No family has earned a complete 4,096-byte artifact; final candidate games,
selected-profile resources and target hardware scaling remain outstanding.

## Composed D restoration and worker/priority representations

The [D composition](../engines/experiments/tiny-d-compose/README.md) actually
combines the qualified span-input natives with the unchanged dedicated v3
fixed-Deflate decoder. The two complete files are **7,640 / 7,881 bytes**,
compared with separate v3's 7,665 / 7,918. The 64-byte native reduction thus
saves 25 / 37 bytes in the complete representation. Payloads are 6,525 / 6,766
bytes with the same 1,115-byte header/decoder overhead. Both remain 3,544 /
3,785 bytes above the limit.

Both natives are rebuilt twice from frozen protocol sources and flags. The
original v3 admission really rejects them; a separate known-image admission
pins the new hashes, sizes and entry addresses, with identical BSS, mappings
and guards. Independent layout review, whole-file reproduction, pre-entry RX/
zero-BSS audits and production post-search RX, permissions, fixed three TIDs,
stdio and EOF checks pass. The two new files separately pass ten common
shipping groups and two colour-exchanged twelve-ply games. No old result is
reclassified as proof for the composition. Evidence is preserved outside Git
under `rove4k-tiny-d-composed-20261020`; the external summary hash is
`d98218c08f05a9e39af40016e731aba1d1b02846524a2fb412e45e02868aa0fc`.

The [packed-priority experiment](../engines/experiments/tiny-ranked/README.md)
replaces two local arrays with one widened move/priority representation. The
two complete source files are **5,299 / 5,303 bytes**, both larger than their
exact 5,283-byte control. Priorities are snapped before descendants, compared
without raw-move tie breaking and stripped before every public/TT consumer.
The actual ordered search streams and full normalized TT/learning/path states
match in the bounded optimized and sanitizer comparisons. Negative signed
learning, all promotion bits, two worker IDs and destructive equal-priority
ties are exercised. Twenty-six common groups, retained/context/PLY contracts,
actual restored images, startup, cleanup and independent reproduction pass.
This widens public move lists and some frames; removing an array is not a RAM
or complete-file saving. The two layouts remain unselected.

The [private-signal D pool](../engines/experiments/tiny-d-signals/README.md)
preserves the frozen board/search inputs and uses blocked, thread-targeted
synchronous notifications around authoritative atomic epochs. Its native
files grow 256 bytes each to **8,796 / 9,184**, and generic own-restoring files
grow to **9,008 / 9,363**. It remains unselected. Six actual files pass 36
common groups and two bounded colour-exchanged games, plus retained features,
context/PLY and scalar/HQ search comparisons. Thirteen separate runtime probes
cover rapid generations, pending/stale/wrong-target notifications, inherited
signal state, idle sleep, partial clone failure, interrupted waits, fatal
syscall errors and late shutdown ESRCH. All owned groups terminate. These
runtime-only probes are separate from the real chess executable evidence.
An uninterrupted job requires W+1 targeted sends, so 511 search workers imply
512 such calls; no dispatch-speed or target-hardware scaling claim is made.
The external final index hash is
`d458f2fe14282d9a2dff751ebcec864238fa44314b3224d91474e79041b0d8b0`.

The exact LF working bytes of all 24 new source/recipe files in these three
experiments match their staged Git objects. Their output files, large raw
traces, logs, failure reports and immutable manifests remain outside Git.
Semaphore coordination and the independent Rust single-stream source layout
are still separately owned work until their final qualification handoffs.
Larger source-kernel redesigns are being evaluated because these measured
representation changes have not closed any family's complete 4 KiB gap.

## Qualified Rust stdin source and semaphore completion

The [Rust stream experiment](../engines/experiments/tiny-rust-stream/README.md)
merges the four exact DEV-pruned modules into inline modules, then embodies
the fixed two-worker/TT18 profile and removes only its unused compile-time
number parser. Board, search, runtime and main token contracts are retained;
source locations change and native hashes belong to a new class. Source shrinks
23,334 →22,981 bytes, and the complete file shrinks **9,074 →9,009 bytes**.
The final whole hash is
`d996efd72a4fed56daba9a9e9a560846e4e0b49a4aad76ad9a7702d3c5a821fc`;
an earlier same-size artifact has different bytes and remains separate.
The unchanged four-file ZIP baseline is independently reproduced byte for byte.

The final stream stores source and Python bootstrap in one 8,896-byte payload
plus a 113-byte stub; that stub is not the entire restoration cost. Runtime
uses literal `rustc` from the caller's PATH and no external crate or C backend.
The helper observes compiler exit with `waitid(WNOWAIT)`, retaining leader
identity while draining its process group before the final reap. It saves and
normalizes SIGCHLD for that waitable compiler, then restores the Python-entry
disposition before the engine exec. Decoder-entry signal handling, compiler
status/signals, a leader exiting before its child, inherited SIGCHLD, queued
stdin/argv/environment, temporary cleanup and actual fd-exec are separately
exercised. The shebang shell's earlier signal normalization stays an observed
boundary rather than an assumed Python guarantee.

Two stdin native compiles and all three whole codec forms reproduce. The
selected source is `516aab3e…56e0b`, actual live ELF is `c477f362…e6309`, and
three persistent startup TIDs match the exact selected artifact. The native and
wrapper pass ten shipping groups and twenty natural malformed/missing/zero
clock completions. A diagnostic assembly build is entirely byte-identical to
that selected native. Production CFA components are 4,640 /73,344 /2,240 bytes;
an actual one-MiB worker reaches ply 127 with 128 nodes, no search allocation
and a propagated incomplete result. These are bounded observations, not a
universal asynchronous-stack or hardware-scaling proof. All old failed and
intermediate 9,009/9,121/8,989-byte streams remain preserved. The final external
aggregate is `rove4k-tiny-rust-stream-qualified-20261020-evidence/phase-summary.json`,
SHA-256 `e7ce47d6ce6ac81c24e9028a1cf68802ece90e088f383961191612dc3b7781a5`.

The [semaphore experiment](../engines/experiments/tiny-semaphore/README.md)
changes the condition-variable runtime only, with exact board/header/search
bytes. Its matched readable control is 5,527 bytes and the candidate **5,515**;
the previously qualified 5,283-byte candidate remains a distinct, smaller
control. Its 137-byte shipping-source reduction is not added to that earlier
file. Shared completion starts with one token; GO consumes it, posts one private
token per worker, and the last worker posts completion only after output flush.
Stored tokens and the release/acquire chain retain jobs posted before waits.
Initialization/creation prefixes are destroyed/joined only after ownership
ends, and fatal wait/post paths terminate with status 2.

Thirteen actual DEV/whole-file groups, retained PVS/QS/TT/history/continuation/
correction and context/PLY contracts, actual restored-image identity, fixed
three TIDs, normal physical cleanup and independent source/native/whole
reproduction pass. A separate final 26-case runtime fixture proves generations
1..97, workers [0,1] for each, 194 jobs and 98 private posts per worker including
quit. It explicitly observes initial and second real waits, tokens before a
wait, delayed workers, and physical output before position publication. Partial
init/create, allocation, wait/post/join and EINTR cases terminate as expected;
no timeout cleanup signal was used. Its earlier cross-pipe observation failure
and unavailable unsaved trace are retained as partial evidence; the production
runtime stays unchanged. The final external summary hash is
`48dc518a018a4c7d9cc8570e0167f991b7064f9e1e40bf35edf8cb80fd603a6e`.

CI now invokes the exact production Rust merge/resource bindings, real Rust
bootstrap fixtures and controlled semaphore runtime phases on a Linux Git
checkout. Registration alone does not prove a new-head CI success; the local
selected whole-artifact proof and old `147d9e2` CI keep their own identities.
The qualified Rust stream driver originally has 391 CRLF endings and no lone
CR. Before Git integration it is canonicalized to LF with exact Python AST and
compiled-bytecode identity. Its original raw receipt stays preserved and the
new source encoding has a separate receipt. Runtime inputs and all producer
bytes remain unchanged; new-head CI executes the canonical driver itself.
The next source work is a minimal shipping UCI policy, one fused generation/
search kernel and an independent no_std scalar/HQ Rust D. Training and AWS stay
excluded. Every family still needs a complete <=4,096-byte submission, final
selected-profile/resource/strength comparison and target-hardware evidence.

## Minimal shipping policy and failed visitor fusion

The [minimal UCI candidate](../engines/experiments/tiny-uci-min/README.md) is a
qualified **5,223-byte** whole source launcher, 60 bytes smaller than its exact
5,283-byte control and still 1,127 bytes above the size limit. Compact source
is 11,351 →11,192 bytes; the 22,664-byte native length stays equal while its
bytes change. Source/native/whole generation is independently repeated twice.
The final whole SHA-256 is
`fbb416160e98beb8f10cc5fec6b3792f4591055626344dcbe31cb50ffce41ee9`.

This is a declared protocol policy change. Shipping emits `uciok` without id,
consumes stop/newgame without cancellation or TT reset, and gives bare go a
1,000-ms budget. An unsupported infinite token leaves that same finite default.
The own-side clock calculation stays unchanged. Go/position/quit/EOF retain
internal cancellation and physical completion fences; startup still initializes
all TT locks. DEV preprocessing and native bytes remain exactly unchanged.
This distinction follows TCEC4k 7.9-7.11 and the accepted plan's consume-only
minimum, not the full general UCI behavior. A finite default does not imply a
strict wall-time upper bound because deadline sampling is every 256 nodes.

All eight actual native/wrapper process runs pass with exact image hashes,
three stable pre-input TIDs, only stdio descriptors, no compiler children or
temporary files, next-job/position fences and quit/EOF physical exit plus
reader join. The final driver also passes twelve independent oracle perfts
and one strict unchanged DEV session. Thirty separately modeled dispatcher/
budget/TT-sentinel cases have no physical worker threads; their state/TT claims
are not expanded to the actual threaded observations. Ignored-control CPU
progress and result ordering are not reported as cancellation causality.
The old stronger common checker stays unchanged. Original failed producer
directories and their corrected exact DEV comparison are preserved. The
external freeze receipt is
`b99b6f9aa911df3d3e0a3d17e4364fabcf36dd367f0ff957352f623822f4203b`.

The [visitor fusion](../engines/experiments/tiny-fused/README.md) removes real
gen/make/first/match consumer boundaries and the move/score lists, but its Fact,
Visit and mode glue makes compact source grow **11,351 →12,655 bytes** and the
whole file **5,283 →5,739 bytes**. It is an unselected negative result, with no
post-result sweep or full test-count campaign. Its fixed TT/best-tactical/
tactical/best-quiet/quiet staging is an explicit move-order/LMR policy change.
Independent precompile review corrected material-draw/PLY precedence and a
quiet TT hint prematurely ending QS captures. Bounded optimized and sanitizer
production fixtures cover those boundaries, all four promotions, legal EP,
castle/hash/context transitions, third repetition, invalid-input rollback,
actual positive learners and raw prefix uniqueness. One actual whole wrapper
passes four clocked/cancelled epochs with exact restored image, startup TIDs,
cleanup and physical join. This evidence is intentionally narrower than the
canonical full suite. The external index hash is
`5e0c9a82414453af695d9fec3a6c3c3409d3acef70c5d1ad5a1e970730c4383e`.

Source work continues with a direct kernel that avoids that context layer,
minimal-UCI B/C/E/F candidates, a fresh-checkout canonical A source/recipe, and
an independent no_std Rust D scalar/HQ runtime. Each remains separately owned
until its actual final artifact and relevant runtime proof are handed off.
No family yet has a complete 4,096-byte file; source reduction, selected
profiles/resources, final strength comparison and target hardware remain open.

## Maintained minimal source and portfolio policy checkpoint

The smallest locally qualified complete files now have the following costs.
These are measured complete launchers, including their decoder/bootstrap, not
the lengths of a C source fragment or a restored native executable.

| Family | Qualified whole file | Remaining above 4,096 B | Selected local change |
| --- | ---: | ---: | --- |
| A | 5,207 B | 1,111 B | Minimal UCI and generated-move preconditions |
| B | 6,219 B | 2,123 B | Minimal shipping UCI |
| C | 5,955 B | 1,859 B | Startup PSQT gather plus minimal shipping UCI |
| D scalar / HQ | 7,640 / 7,881 B | 3,544 / 3,785 B | Previously qualified own-ELF composition |
| E | 5,899 B | 1,803 B | Capture-prior removal plus minimal shipping UCI |
| F | 5,479 B | 1,383 B | Minimal shipping UCI |

The [maintained A entry](../engines/compact/tiny-entry-a/README.md) is now a
readable canonical program and a fixed recipe. Its ordinary checkout inputs
are nine owned files and five SHA-pinned build helpers; two pinned test helpers
complete its verification closure. It reads no historical build/report or
generated engine directory. A fresh sixteen-file Git tree was archived and
extracted twice, and both extracted builders independently repeated generation,
compilation and packing. Compact C is 11,148 bytes, native ELF 22,664 bytes and
the whole launcher 5,207 bytes, with whole SHA-256
`085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36`.
The fresh source tree is `a6cb91a7c6441977c6525ebf279b6639d0163689`;
its external final index SHA is
`8c4ad6f919f5737005acf289c42c53c083410a0989eded752e00c49a35590470`.
Two actual selected-wrapper sessions bind the regenerated native image,
three stable pre-input TIDs, legal white/black/bare-go results, removed
restoration directory/helpers and active quit/EOF physical exit with one final
legal result. Historical broader proof is reused by exact identity. The
previous 5,223-byte canonical source/archive and evidence remain preserved.

The final A change keeps the king-capture and move-list-capacity guards in DEV
and omits them only in shipping. The [precondition proof](../engines/experiments/tiny-preconditions/README.md)
traces every shipping make/add consumer: only generated moves from startpos
histories enter make, and TT hints only reorder or cut search. The preceding
legal transition preserves the king-safety invariant; the actual pseudo-move
bound is `10 + 15*27 = 415 < 512`, including all promotions. Own-king safety,
EP/castle checks and transactional replay remain. This removes 44 compact C
bytes and 16 whole-file bytes; DEV source and native bytes are identical.
Eight O2/sanitizer/PLY forms, eight actual native/whole runtime sessions and
fifteen separate modeled clock cases pass. The final runtime driver also
corrects its owned-process cleanup on aggregate alarm; the deliberate timeout
fixture observes leader and grandchild disappearance. Neither that fixture
nor active-search exit establishes arbitrary nested cancellation causality.

The [B/C/E/F minimum-UCI experiment](../engines/experiments/tiny-uci-portfolio/README.md)
reproduces each old control before applying the same qualified command policy.
Whole-file changes are B 6,283→6,219, C 6,015→5,955, E 6,095→6,031 and
F 5,551→5,479 bytes. Everything outside go/main is byte-identical to each
readable control, and DEV preprocessing/native pairs remain exact. Eight actual
whole-file sessions and four strict DEV sessions pass. New focused B/C core
checks and thirty modeled B/F dispatch cases have separate scopes; unchanged
SEE, singular, SIMD, model and MTD(f) coverage is reused only through exact
source/harness/image bindings. The final external receipt SHA is
`71d1a8f86d09364fbe9f1f0a2138b5c87a8361a86b46e6756a182f754c9b9f9d`.

The [E ordering change](../engines/experiments/tiny-e-order/README.md) removes
the old HCE/PST capture prior because the unchanged frozen model already has
its material-order term. It keeps the 500,000 capture class, promotion/TT
priorities, all 21 untrained coefficients, model leaf/clamp and full model
ordering sum. This explicitly changes move order, later reductions and
learning, so no unchanged-search or stronger-play claim is made. It reduces
compact C 14,896→14,547, native 26,504→26,440 and whole file 6,095→5,959 bytes.
Six actual production forms per policy pass O2/sanitizer model, legal-transition
and priority-consumer checks, and both policies pass their 28-group bounded
process suite. Selected source/native restorations have exact image/startup/
cleanup proof. The final metadata-only clarification preserves every tested
engine byte, bound by external receipt SHA
`ee0d1015fb2090a5fd52349dfa5a09518fa5d5adb99a69a96b4743459f286332`.
The separate [actual composition](../engines/experiments/tiny-e-compose/README.md)
reproduces the 5,959-byte order control and 6,031-byte UCI control, then measures
5,899 bytes, not the 5,895-byte arithmetic prediction. Compact C is 14,352 bytes
and restored stdin ELF 26,408 bytes. Both transform orders and a separate
whole-function transplant produce the same source; all 23,218 readable bytes
outside go/main equal the qualified order-only core. Two actual whole-file
sessions and one strict ordered-DEV session pass, with exact native/image/TID/
cleanup and physical completion gates. Six earlier model-consumer forms and
positive search/learning proof are reused through literal source/report pins.
The final proof-tool-only fixes keep every tested engine byte identical and
preserve the first runtime record. Final external receipt SHA is
`cbb9f44160caac83d1e52a4dd224513d819c493b519faffb65ff7c9f49d08590`.
Git preserves the exact CRLF bytes of the fixed E-order and E-composition
input-map JSON files through path-specific attributes; other source inputs
are unchanged. This metadata preservation is separate from the frozen
eight-file experiment receipts.

The [direct kernel](../engines/experiments/tiny-kernel/README.md) avoids the
visitor/context layer but still loses: compact C before fixed spelling grows
13,366→13,654, encoded C 11,351→11,876, native 22,664→26,760 and whole file
5,283→5,543 bytes. The five generation stages, frozen rank threshold and worker
file order are explicit search-policy changes. Independent byte reproduction,
bounded legal/attack/transaction contracts, optimized/sanitized positive search
fixtures and one actual whole-file lifecycle pass; no full-suite, strength or
scaling claim follows. This losing architecture is retained as evidence and
does not replace the selected A source.

A single original [source PPM experiment](../engines/experiments/tiny-source-ppm/build.py)
also stops on first cost. Its order-four exclusion model compresses the exact
11,148-byte C to a 4,675-byte frame, but its complete standard-library decoder,
bootstrap reconstruction and launcher produce 7,483 bytes, 2,276 bytes larger
than the reproduced 5,207-byte control. Independent reference decoding twice
and intercepted final exec restore the exact C and original bootstrap. There
are zero compiler invocations or engine executions in that first-cost proof;
it supplies no new runtime, strength or eligibility evidence.

## Independent no_std Rust D runtime checkpoint

The [separate Rust D implementation](../engines/compact/tiny-rust-d/README.md)
has its own Linux x86-64 entry, raw syscall/clone trampoline, futex coordination,
guarded worker stacks and assembly memory primitives. It uses Rust core without
external crates, libc, pthread, TLS, interpreter or a C backend. Both actual
scalar and HQ paths independently reproduce **16,824-byte complete ELFs**.
HQ SHA is `2c84c684d840ad7e7f0567b2b76d9c28693a00f6f95779675fb45ff84c06d3b3`;
scalar SHA is `0c364208165b79d95f146650ec8ae144f1e4cb6427197b80f37f0e97a90a4eb3`.
Static gates inspect an auxiliary unstripped link and require its allocated
sections/addresses/BSS to equal the stripped image, with no unresolved symbols,
dynamic dependency, interpreter, TLS or executable stack.

Fresh ordinary sessions of both actual shipping images pass three-TID startup,
clock/search/stop/position/reset/quit/EOF, cumulative per-GO result totals and
full output EOF. Separate owned-child ptrace runs of the same images hold actual
output and exit syscalls: finished stays old before bestmove output while OUTPUT
is held, and the new generation is published only after the full write with
OUTPUT released. The kernel clear-TID contract is observed before successful
stack unmap. Waitpid notification ordering is a separate observation and is
not used as a substitute for this join. No GO-time clone/mmap/mprotect occurs.
The single main controller owns start/reset/shutdown; this is not a general
pool API safe for concurrent external controllers.

Exact-body std board drivers pass twenty published perft totals per lane,
128 independent positions, 3,590 child transitions, 16,384 attack queries and
148,480 raw HQ/ray cases; full scalar/HQ responses match. Eleven search contracts
per lane retain positive search/learning, coherent full-key/context TT and
completed/interrupted witness evidence. Separate no_std deep diagnostic images
reach the 128-ply abort on the actual guarded 1 MiB stack path and join before
unmap. Fourteen fault images cover failed second clone after one physical
worker exists, worker clock failure after startup and GO, short I/O, retries
and actual lower/upper guard faults. These diagnostic images and the std
allocator probes remain separate from unchanged shipping-image proof.

The actual HQ shipping ELF also equals an auxiliary frame-audit image: search
CFA 4,880 bytes, worker entry 73,200, pseudo generation 2,224 and main 431,952.
The observed deep path and these frames are not a universal stack bound.
Production Rust/assembly/linker bytes did not change during qualification;
first harness failures and final strict runtime/trace verifier fixes are
preserved with the versions that produced each receipt. Final seventeen-file
source/evidence aggregate SHA is
`a79b90ec7deed06cff221b9cfbb94edc722eb101f71a08484d2605a65823c0a9`.
Git integration removes one extra final LF from only the search test fixture;
the old seventeen-file receipt remains historical, with a separate exact
normalization/hook/unit-image receipt. Production sources and runtime evidence
retain their original identities.
No compressed-loader, 4 KiB, strength, NPS or 512-worker scaling claim follows.

CI now builds the maintained A source with its fixed expected bytes and runs
that exact selected launcher from a clean checkout. It also builds/reproduces
both Rust D lanes and invokes actual runtime, production tracing, board and
search-unit checks after explicit expected native-hash admission.
Adding these steps is not a
claim that the new head has passed it. Training and AWS remain excluded;
eligible complete files, final selected-profile resource/strength comparisons
and target-hardware scaling are still required for portfolio completion.

## Maintained portfolio sources and actual A composition

All six selected C implementations now have ordinary maintained source and a
fixed checkout-only recipe under `engines/compact/tiny-entry-{a,b,c,d,e,f}`.
The maintained selected complete-file costs are:

| Family | Complete selected file | Above 4,096 B | Maintained submission form |
| --- | ---: | ---: | --- |
| A | 5,129 B | 1,033 B | Ownership/query source, shared startup phase counter, LZMA-alone |
| B | 6,219 B | 2,123 B | Minimum-UCI source entry |
| C | 5,947 B | 1,851 B | SIMD/PSQT entry with DEV-only HCE cache |
| D scalar / HQ | 7,640 / 7,881 B | 3,544 / 3,785 B | Own self-restoring ELF |
| E | 5,899 B | 1,803 B | Untrained model/order composition source entry |
| F | 5,479 B | 1,383 B | Full-depth MTD(f) source entry |

These are the measured local two-search-worker/TT18 profiles. They are not
final target-profile costs, strength recommendations or 4 KiB acceptance.
The independent C/Rust cores and earlier structural comparisons remain
available; this source promotion does not substitute one language for the other.

B/C/E/F each retain their exact readable program and qualified shipping C,
native, bootstrap, complete file and DEV bytes. Their source closures contain
15/15/15/16 files respectively: nine local files plus only the actual required
build/test helpers. B has no name-replacement stage; C/E retain their own
SIMD/model pipeline and compiler argv; F retains its 34 fixed spellings.
A's spelling, stripped compiler or encoder choices are not imposed on them.
Each closure was archived as an isolated Git tree and extracted twice. Each
extracted builder repeated generation/compilation/packing, followed by two
actual selected-wrapper sessions per family. Image, startup-TID, legal-clock,
restoration cleanup and physical quit/EOF gates pass. Existing broader SEE,
singular, SIMD, model or MTD(f) proof is reused by exact identity rather than
reported as new execution. Final external source receipts are B/F
`13b33f6da3fe434ae17957048f762f89026dfc27b6a14f379267b0e015770a4c`, C
`6bf1a0b9a8c967618409a763f0531bdbe69f5a225c9d380c805245cba1f9a44c`, E
`6a7e5e3c3de7ea3a8d383f8c1d6a4f849a0f86cfda0744eb9881a38086b7e452`.

D retains eight native sources and three loader/codec/linker inputs in its
18-file maintained entry. Its explicit twenty-file archive also includes
LICENSE and the independent oracle. Two isolated extractions independently
reproduce both native images, both complete own-ELFs and the same CHECKPOINT
audits. Eight production cases and four pre-entry audits distinguish the whole
`/proc/exe` identity from anonymous restored RX bytes, then check zero BSS,
guards/W^X, original entry handoff, startup TIDs, stdio/child state, legal clocked
responses and physical exit. The ordinary single-TERM compiler-stall fixture
also verifies owned-process cleanup and retained incomplete reports/output.
Its final source/evidence index is
`7c6b2dd18d72c003c839f228df96639d4cef90d9f9c5c69c880cef7866fe311a`.
Existing kernel/protocol/loader fault proof stays attached to its original
images and verifier versions. There is no new layout or image-class admission.

The [A ownership change](../engines/experiments/tiny-a-ownership/README.md)
unifies first-legal and exact-text move queries and returns the already-made
child. Replay commits that child, and each worker resets its per-job result at
think entry before any claim or pending decrement. Readable C shrinks
25,131→24,921 bytes and compact shipping C 11,148→10,958. Query output must be
non-aliasing caller-owned scratch, discarded on failure. Published GO jobs
preserve their old fallback/results; a direct internal think call with a
preseeded best now clears it. That broader private API difference is explicit.
Three optimized/sanitized query forms check complete child state, exact token
admission, special moves, transactional HISTORY boundaries and both direct
reset cases. Two actual wrapper sessions cover eight repeated/replaced jobs,
position reuse, zero clocks and active quit/EOF. Board and search bodies stay
exact, while the changed boundary has its own proof.

The [LZMA-alone transport](../engines/experiments/tiny-lzma-entry/README.md)
keeps the exact old source/bootstrap/native but reduces 5,207→5,163 bytes.
Its prefix grows 75→77, format/check/padding/index cost falls 58→13 and actual
coded data falls by one byte. LZMA1 replaces LZMA2; this is not just a container
claim, and ALONE has no equivalent XZ CRC64 protection. Strict Python and real
CLI decodes bind the full bootstrap. Two actual selected sessions passed with
the original adapter. Its later input-path-only revision archives the old
verifier/recipe so canonical promotion cannot break the experiment. The new
adapter is statically bound and unexecuted, explicitly reusing the earlier
runtime rather than relabeling it. The PPM losing experiment likewise derives
its old template/prefix only from admitted controls, and repeats the same
7,483-byte result after removing its live-canonical dependency.

The [actual A composition](../engines/experiments/tiny-a-compose/README.md)
preserves and reencodes all three 5,207/5,183/5,163-byte controls, then measures
one fixed combination at **5,140 bytes**, not the additive prediction of 5,139.
The maintained A now contains the qualified ownership program and fixed
77-byte/LZMA1-alone 9-extreme lc2/lp0/pb0/CHECK_NONE recipe. Its native stays the
ownership image, and the new ownership DEV source/native pins replace the old
5,207-byte program's DEV pins. Two fresh sixteen-file source extractions each
repeat every output, then the actual new selected file passes two fresh
quit/EOF sessions. The whole SHA is
`75dc3d610d39bbc0702c6eda219fa0acb4d167c40d3c78e241cf867a33e5a4e7`;
final eleven-source/receipt aggregate is
`85da3ed9dec657baa9e27e0c5ca98394cf66c5753b507b8f1c1ae4506cb38657`.
All prior canonical inputs, archives and controls remain preserved. Active
search exit is observed; cancellation causality is still unproven.

The [Rust affine-HCE first-cost experiment](../engines/experiments/tiny-rust-affine/README.md)
preserves safe indexing and proves all 832 admitted piece/square pairs before
compilation. Function size falls 216→150 bytes, and allocated text/rodata shrink
106 bytes. The unchanged linker absorbs them as padding before data at offset
0x4000, so both complete scalar/HQ ELFs remain 16,824 bytes; readable source
grows seven bytes. It stops at cost without executing an engine or claiming
runtime qualification. This losing whole-file result is not promoted.

CI now regenerates A/B/C/E/F and runs each selected source wrapper, plus
rebuilds both maintained D own-ELFs and checks their distinct restored images.
Those steps pass in the exact `4e3af24` C job; its Rust job and repository
lifecycle also finish successfully at the linked runs above. Later experiments
retain separate local evidence and are not included in that CI claim. No family
yet has a qualified <=4,096-byte file. Further source reduction, actual final
target profiles/resources, candidate-specific games and hardware scaling
remain required; training and AWS remain excluded.

## Focused B target emitter and C cache experiments

The fixed [B target-emitter candidate](../engines/experiments/tiny-b-target/README.md)
reuses the existing `attackers()` path for ordinary generation and SEE capture
enumeration. The exact 6,219-byte control is reproduced; compact source falls
15,566 to 15,456 bytes, native grows 26,592 to 26,624, and the actual complete
file falls to **6,155 bytes**, a 64-byte saving and still 2,059 bytes oversized.
Independent generation/compile/package repeats match. Optimized and sanitized
special-move/SEE/singular/excluded-learning checks, the independent oracle's
15 roots and 207 legal children, and two actual selected-file quit/EOF sessions
pass. Move generation order changes and up to 64 reverse attack queries per
ordinary generation may slow nodes; no performance or strength claim is made.
One byte-identical diagnostic compile accounts for 692,520 worker-stack bytes,
including the new SEE move arrays and same-ply singular frames. Library,
pthread/signal/entry and deepest-path runtime use remain unmeasured:
`whole_runtime_stack_qualified` is false. The original eight-source aggregate
is preserved; adding only the ninth LF policy file changes the final aggregate
to `d3ddcb059e9f5f0739cbf982f07164e928fb88250ff6cb1e981a391def14cdf3`
without rerunning or relabeling earlier execution.

The fixed [C shipping-cache candidate](../engines/experiments/tiny-c-state/README.md)
guards only the unused shipping HCE cache field and its two `put` maintenance
sites as DEV. Shipping source falls 14,244 to 14,206 bytes and actual Board size
176 to 168; native length remains 26,464 while the complete file falls from the
exact reproduced 5,955-byte control to **5,947 bytes**, still 1,851 oversized.
The actual SIMD/search consumers stay unchanged, `value()` remains for PSQT
construction and move priority, and both DEV source/native identities stay exact.
Optimized and sanitized shipping-layout comparisons each cover 160,432 positions,
150,419 legal children and actual TT/draw/mate/learning/PLY contracts. The PLY
fixture installs a real direct-search result into completed fields before the
abort call; it is not a new observation of think publication. Cross-form exact
search scores, nodes and learned tables are not compared. Two actual selected
wrapper sessions bind the new native image, persistent three-TID startup,
legal clocks/bare go and physical quit/EOF. The fourteen-source final receipt is
`67d7dce0b1852f7227f62f87c9b9568c9ebbc365274d182a4515e707200f2d11`.

Both experiments keep their original cost reports separate from later focused
qualification. At their experimental checkpoint the maintained B/C entries
remained unchanged. Neither is accepted as the final profile or for 4 KiB. Actual active exits retain
cancellation causality as unproven. These later local results are outside the
`4e3af24` CI claim. Final resource/stack/profile comparisons, games and target
hardware work remain outstanding.

The exact C5947 candidate is subsequently promoted to the maintained C entry.
Only readable `engine.c`, the explicitly pinned recipe and README change; the
builder, verifier, fresh driver, compiler/profile, codec, prefix and bootstrap
remain identical to the preserved C5955 predecessor. The historical experiment
has its own control source and does not consume the mutable maintained entry.
Two independent extractions of the new fifteen-file source archive each repeat
shipping/DEV generation and run two actual selected-file sessions, for four
new physical sessions total. Shipping/native/whole and unchanged DEV pins all
match the qualified candidate. The promotion receipt is
`69cf45d8c105e2c5c8622a5319d09cb0248c8a2a122d6ce2e63fe77206b104d4`;
source tree `13f03c96bb8daa802dd56a48ba831f63b1f548ab` and archive
`089f36326e7ec3a441b0f11766ee1ed1ed3dd74b57c2a139cbdf239b1e065a73`.
Broad state/search proof is reused by exact candidate identity; it is not rerun
or replaced by source regeneration. This source promotion still requires its
own later-head CI result and does not select the final target profile.

## A startup phase ownership

The fixed [startup-counter source change](../engines/experiments/tiny-a-startup/README.md)
uses `pending` during the disjoint startup and search phases. It starts at the
fixed worker count; worker entry decrements it separately from the existing
job-completion/result branch. After every create succeeds, main uses the existing
`wait()` instead of a separate arrival counter and loop. Partial-create failure
still goes directly to shutdown and joins only actually created workers.
Board, TT, search, think, queries, parser, epoch and shutdown bodies remain exact.

The exact 5,140-byte maintained control is independently reproduced. Readable
source falls 24,921 to 24,820 bytes and compact C 10,958 to 10,855; native grows
22,664 to 22,672 while the actual complete file falls to **5,129 bytes**, an
11-byte saving and still 1,033 bytes oversized. A second isolated copy of the
owned source closure independently repeats both forms twice, matching every
readable/compact/native/bootstrap/whole output without mutable canonical inputs.

One separate instrumented compile passes five forced startup schedules: both
arrivals before main waits, a late arrival after the real wait predicate, no
successful create, one early worker before second-create failure, and a worker
entering after the real shutdown broadcast. Actual entry/exit/join identities
and TT free after successful joins agree. These are diagnostic pthread wrappers,
not the shipping native image or a general scheduler/join-error proof. Successful
startup now leaves internal `stopped=1` instead of zero; first GO already clears
it. A private consumer bypassing GO must clear it explicitly.

Two actual selected-wrapper processes pass eighteen individually fenced GO
epochs, including white/black zero clocks, active GO replacement and position
reuse, final quit/EOF, exact native bytes, stable three-TID startup, restoration
cleanup, reader EOF and absent owned PID/TID/observed-descendant identities.
The black-box sessions do not intercept pthread joins or prove cancellation
causality; those limitations remain explicit. No SAN/TSAN, broad board/search,
games or performance campaign is rerun. The final twenty-four-source index is
`f09a0b388e6417f5e80964b39eac1b2341fb2809314a5e24ef8c82f918fb0f60`;
the selected complete file is
`5da238b8f2cc622e5f71a2da07a4f3a787c6679fa29f78b27546800174578527`.
First cost, isolated reproduction, actual-wrapper and diagnostic receipt hashes
remain separate, including the actual runtime receipt
`f13080626ea2e169651c379321de1a69fcfe2061fa458a8c527ba4b031ccb960`.

The exact startup candidate is promoted to the maintained A source. The prior
nine files, source archive and shipping/DEV controls are preserved before editing.
Only `engine.c`, recipe and README change; builder, fresh/verifier code, template,
prefix, compiler, spelling/resource decisions and codec remain exact. New DEV
source/native are independently compiled twice from the qualified candidate
before literal admission; their identities deliberately differ from A5140 DEV.
Two isolated sixteen-file source extractions each reproduce shipping/DEV twice.
Two new actual selected-wrapper quit/EOF sessions pass, reusing the separate
five-schedule startup and eighteen-epoch proof through exact input bindings.
The promotion receipt is
`1b585bf749a7bde6cef3d3006b8856ff9624e286366afbd7fe537ff61abdc6b9`;
source tree `162cef5a32f3b58308b1623a237d985f5448fbc4` and archive
`8ffdde2d02fcdc8fa18bd6da08b5f8349c04ef487f97382a999282cd030ad7fb`.
Earlier experiments use preserved controls and do not acquire a dependency on
this new mutable canonical source. This remains a local source promotion until
the later exact-head CI runs; eligible size and final target acceptance are open.

## F integer-unit-window source specialization

The [F beta-only candidate](../engines/experiments/tiny-f-zero/README.md)
specializes the private recursive search API to the integer unit windows that
the production full-depth MTD driver actually supplies. Children receive
`1-beta`; a completed score stores a lower bound iff it reaches beta, otherwise
an upper bound. This removes first/later PVS dispatch and an unreachable interior
re-search. The coherent full-key single-bound TT and the driver's lower/upper
interval remain distinct. It is not a general wide-window search API.

Readable C falls 26,360 to 26,100 bytes, compact shipping C becomes 12,722 bytes,
and the actual complete wrapper falls **5,479 to 5,407 bytes**. Native remains
22,664 bytes with new exact contents. The focused proof compares the real old
unit-window search and new beta API in optimized and sanitizer forms, including
compact DEV=0 source, 51 finite thresholds/special states, retained MTD minimax
and attaining witnesses, interruption and PLY/context/learning controls. The
former seven wide-window fixtures are not reused for this changed API.
The proof receipt is
`96678ed411e4fea4fcd0b176fe5cd707f073d49166e541dd9112b3d1bfa49e12`.

The [maintained F entry](../engines/compact/tiny-entry-f/README.md) now contains
that exact readable program. Its builder removes counters using an owned strict
beta-only schema rather than the former shared overlay's PVS assumption.
Compiler, profile, codec and launcher stay fixed. Two fresh source extractions
each reproduce shipping/DEV outputs and run the selected wrapper for quit/EOF,
four new physical sessions in total. The selected whole-file SHA is
`e562a49a06257d46bbbb9e0481023f3716926e4cf2a8086dcd5307b3e8a96078`;
promotion receipt is
`a60b7d60b40d45863a1de2b3e0b378bd0764f1d980f9a67faab4eca109e1e23f`.
No broad campaign, strength or target stack/profile acceptance is inferred.

## D finite minimum shipping protocol

The [finite-D candidate](../engines/experiments/tiny-d-finite/README.md)
omits optional identification and consumes unsupported `stop`, `ucinewgame`
and `infinite` without adding controls. Clock allocation for the moving side
stays unchanged; absent that clock, a GO receives a finite 1,000 ms budget.
This is a search budget, not a hard wall-time cap. Next GO, position, quit and
EOF still wait for result publication and physical completion before reuse.
DEV retains the previous stronger controls.

The exact scalar/HQ natives shrink 8,476/8,864 to 8,348/8,736 bytes. Complete
own ELFs shrink **7,640/7,881 to 7,540/7,800 bytes**. Core, clone/futex pool,
fixed codec and loader stay unchanged; the admitted image class retains three
RX pages, 43 BSS pages and its guards. The original focused command/clock/TT
sentinel proof and broader physical sessions retain their original receipts.
The common strong-stop lifecycle harness is unchanged and is not claimed as
proof for the new consume-only shipping policy.

The [maintained D entry](../engines/compact/tiny-entry-d/README.md) promotes this
exact runtime and literal native/whole/checkpoint pins. Two independent source
extractions each reproduce both forms, their repeats and pre-entry audits.
Eight new production sessions and four pre-entry checkpoints pass image/RX/BSS,
permissions, legal results, persistent startup TIDs and quit/EOF settlement,
with no forced cleanup. The promotion index SHA is
`bbfdaa3f012f400b2ca575dae8ce91dbf0687379065f746a96e689bf5facf1d6`;
the fresh results SHA is
`80860d7be1d1b0ed5ba7e7d16a82653ae85a4ab3abd3b4347a1893daabac39ad`.

## Rust D borrowed ASCII ingress

The [ASCII ingress candidate](../engines/experiments/tiny-rust-d-ascii/README.md)
replaces the stored 16,384-token array with a borrowed byte stream. It rejects
a complete NUL/non-ASCII line before command dispatch and accepts ASCII space
and bytes 9 through 13 as whitespace. Unsigned parsing, successful-only numeric
lookahead consumption, transactional replay and the safe `parse(&str)` wrapper
remain explicit. Unicode whitespace admission is intentionally removed.

This change increases readable Rust by 836 bytes. Actual text plus rodata falls
1,403 bytes, absorbed by the unchanged linker alignment. Removing the unused
comparison GOT slot reduces data from 16 to 8 bytes, so both complete native
images fall only **16,824 to 16,816 bytes**. Main's measured prologue allocation
falls 431,952 to 169,824 bytes; this is not a universal stack bound or a source
minification result. No new unsafe indexing, search, OS, runtime, compiler or
linker policy is introduced.

The [maintained Rust D](../engines/compact/tiny-rust-d/README.md) promotes the
exact main/board sources and an owned strict verifier with ASCII negative and
whitespace/numeric/replay checks. Two fresh source extractions each reproduce
both native profiles twice. Actual new production ELFs pass 126/126 admitted
GOs across sixteen sessions. Both new production ptraces observe output before
completion publication and shared clear-TID join before stack unmap; the tracer
source is unchanged. Older deep/fault/board/search runs retain their original
scope and are not relabeled as new executions. The promotion receipt SHA is
`ff7bc32bbb4d00139848cb349180441b3c2cdc064cab9258ffc068244e173a80`.
CI pins the two new 16,816-byte identities literally. The root LF rule for this
subtree is repository metadata added separately from the qualified seventeen
source inputs; it does not change their bytes or their source archive.

These promotions are still oversized. All six eligible artifacts, selected
final resources, candidate-specific strength comparisons and target-hardware
scaling remain outstanding. Training and AWS connections remain excluded.

## Fixed B/C/E source spelling portfolio

The [alpha portfolio](../engines/experiments/tiny-alpha-portfolio/README.md)
shortens admitted automatic locals/parameters, private members and owned type
names, plus the already fixed WORKERS/TT_BITS literals. Protected functions,
global/static storage, directive consumers, external APIs, strings and compiler
arguments remain unchanged. Alias freshness/injectivity and exact occurrence
counts are explicit. Reversing aliases in the full preprocessed translation
unit reproduces the original bytes, and each full native ELF remains exact.

| Family | Compact C before / after | Whole file before / after | Whole saving |
| --- | ---: | ---: | ---: |
| B | 15,566 / 13,606 B | 6,219 / 5,955 B | 264 B |
| C | 14,206 / 12,526 B | 5,947 / 5,723 B | 224 B |
| E | 14,352 / 12,641 B | 5,899 / 5,679 B | 220 B |

Two independent candidate generations/builds per family reproduce those exact
source/native/bootstrap/whole identities. Six new selected-wrapper sessions,
quit and EOF for each family, pass exact restored native bytes, persistent
three-TID startup, legal white/black zero-clock and bare-GO output, active closing
output, reader EOF, process absence and temporary restoration cleanup. Compiler,
profile, codec and DEV are unchanged; historical core proof is reused by exact
native identity. There is no new game, benchmark or cancellation-causality proof.

The first-cost receipt SHA is
`e0527b2c9c566150791f6095346694961b81dc007fb9f89e1c135755ab81a1d8`;
actual new wrapper results SHA is
`5fbd18434187219b571dfb962058298616d560c671485c32d320a368607df427`;
the frozen forty-four-source aggregate is
`436d7cbdc6ad7fa52b73d5b1e9075971b9249f64d8225b775585a4dbd5b0ad80`.
This experimental closure has its own immutable historical control inputs.
At that experiment checkpoint, maintained B/C/E promotion was still a separate
next step. The following promotion now supplies those exact selected bytes.

The maintained B/C/E entries use a standalone ordinary-source helper containing
the identical readable policy bytes. Its transformation function bodies remain
identical; it reads no experiment files, side policy file or historical report.
Only each builder/recipe/README and the new helper change. Readable engines,
DEV, compiler, resource profile, codec, launcher and existing helpers stay exact.
The new helper has an explicit repository LF rule, separate metadata from the
qualified source closure.

Each seventeen-file source archive is extracted twice; each builder repeats
shipping and DEV generation/compilation. All twelve shipping and twelve DEV
builds match their literal pins. Six new selected-wrapper quit/EOF sessions
pass exact old native bytes and the new complete files, startup TID stability,
legal results and physical settlement. Earlier preprocessor/core proof is reused
by exact identity rather than rerun. The final promotion index SHA is
`6bbfcd6ffbf2b1dc029fa62295fb8cefe5687a430004a896de292c6d63aca712`;
the ten-source/union-thirty-six-input raw freeze is
`d2d9eb5182876708a95e4755693941b54e335f54b68021ee7d777398b61d7b83`;
fresh actual results SHA is
`ebacff60e489f3cb230313b4474b0cce57e206730745d5e077c2a052a6b89f53`.
This is a local source promotion until its later exact-head CI succeeds, and
none of the new whole files fits 4,096 bytes.

## Independent Rust D self-restoring ELF checkpoint

The [Rust packed experiment](../engines/experiments/tiny-rust-d-packed/README.md)
connects the independent no_std Rust core to the project's owned fixed decoder
and entry wrapper. It owns seven historical Rust production inputs and the
packaging sources; it does not call a C chess engine or an external decoder.
This uses the qualified pre-ASCII 16,824-byte native controls, not the newer
16,816-byte maintained inputs. The original C image admission remains unchanged.

The explicit Rust class removes only ELF section metadata outside PT_LOAD and
normalizes the section-header fields. Its 16,400-byte decoded span preserves
entry, program headers and all allocated text/rodata/data. The final mappings
are four RX pages and one RW page containing sixteen initialized pointer bytes,
four zero OUTPUT bytes and zero padding. Original-native, sectionless, payload
and whole-file identities are separate. Copying section metadata over BSS is
rejected rather than treated as a valid loaded image.

Two independent builds per profile reproduce complete self-restoring files of
**12,554 B HQ / 12,194 B scalar**, including the 1,115-byte header/loader cost.
These save 4,270/4,630 B over the direct Rust native controls and remain far
above 4,096 bytes. First-cost execution was zero; later runtime is a separate
campaign. The original first-cost index SHA is
`b9e9325c4a5cbcf04515012afd733a25dd5caec92f0e3e929bad3d19bd5eff3d`.

Actual new packed-file observations pass two distinct pre-entry CHECKPOINTs
and four shipping sessions, both profiles with quit and EOF. The checkpoints
bind the anonymous decoded bytes, initial data/BSS, guards, permissions and
original entry. Shipping covers 24 legal results for 24 GOs, persistent three
startup TIDs and guarded stacks, active replacement/position/shutdown, complete
output/readers and physical process/TID/group disappearance. None of these six
positive sessions needed forced cleanup. Older raw-native kernel/deep/fault
proof is not relabeled as a new packed execution.

The full campaign stays **incomplete**. Its READ_IMPLIES_EXEC rejection fixture
did not reach the intended boundary: a confirmed pre-exec flag was zero in the
loader's actual post-exec personality query. That diagnostic reached restoration
and was stopped at its event cap, with forced cleanup explicitly recorded.
It is not a guard-rejection success; the scalar negative was unexecuted.
A logging-only revision preserves events immediately but has not rerun the full
campaign. A later register-modifying debugger fixture was not executed and is
kept outside Git. The admitted nineteen-source checkpoint therefore preserves
the original positive results, failed report and unproven negative separately.
Its external index SHA is
`95c581b682b3cec6398a6d29864b810aa99b5fd01457fa0abb9c74685c2d63c4`.
This checkpoint establishes implemented and observed Rust restoration paths,
not complete runtime admission, eligible size, strength or target scaling.

## Rust D constructor reuse first cost

The [runtime-start candidate](../engines/experiments/tiny-rust-d-start/README.md)
changes only `Board::start()`: initialize the fixed 32 occupied squares through
the already-shipping `put`, then finish state hash/context. Arbitrary-input
rebuild, canonical EP, move/search/TT/learning, OS/SMP, ABI, compiler and linker
remain unchanged. No const factory, dispatch change or unsafe shortcut is added.

Both exact ASCII controls reproduce before candidate compilation. Each candidate
reproduces independently and passes the existing ELF gates. Allocated `.text`
falls **272 B** in both profiles; `.rodata` stays 304 B and `.data` 8 B. The
unchanged data alignment absorbs that gain, so both complete natives remain
**16,816 B**. Readable and identically merged measurement source each grow 16 B.
Existing `put` stays 314 B and `start` shrinks 545 to 322 B; changed inlining of
the unchanged canonical-EP body explains the remaining allocation effect.

Separate ordinary-runtime std units compare all ten Board fields and 151
elements between original/candidate and check Copy/fresh-start independence.
Both HQ and scalar pass two tests each. These diagnostics do not compile the
raw runtime or search. At this constructor-only checkpoint the new production
ELFs have not been executed; the later packed cost and observation are recorded
separately below. Twenty-four ordinary LF sources
retain the control and constructor producer without a live-maintained dependency.
Final aggregate SHA is
`689a3d5b662bd6d8163fbce5ec882a31dfb6a980d596aa44212e5b5b98b53db5`;
source manifest SHA is
`15778ac39d3b529926881c0486df98d7be512e0efca938785e741fd33c26d655`.
This is an allocated-code saving with narrow constructor proof, not a smaller
whole file, a source-minification result or a qualified new shipping runtime.

## B target emitter with fixed source spelling

The [target/alpha composition](../engines/experiments/tiny-b-target-alpha/README.md)
reproduces the maintained 5,955-byte B and combines the earlier target emitter
with its own literal adaptation of the same 89-name alpha policy. The actual
whole file is **5,899 B**, a 56 B saving, rather than the additive prediction
from the separate target-only and spelling results. Compact source falls
13,606 to 13,559 B; native grows 26,592 to 26,624 B and remains byte-identical
to the previously qualified target image. No additional core policy changes.

The target uses eighty of the mapping names. Its exact 607 token occurrences,
unchanged opaque regions, fresh aliases and candidate identities are admitted
separately; the original alpha helper and its three admitted domains stay
unchanged. Actual resource/header/full-preprocessor inverse checks and two
independent source/native/whole generations pass. Two actual selected-wrapper
quit/EOF sessions pass the unchanged original verifier with literal new source,
bootstrap and whole-file pins and the already qualified target native pin.

The target's changed generation order and up to 64 reverse attacker queries per
ordinary generation retain their unmeasured speed tradeoff. No new core/game/
NPS campaign or universal stack claim follows from the source composition;
whole-runtime stack qualification stays false and cancellation causality
unproven. This remains an experimental candidate, 1,803 B oversized, rather
than an automatic replacement for the maintained B profile.

Thirty-one ordinary LF source files close the experiment without live maintained
or generated-engine inputs. One later repository-only ignore override admits
its three ordinary `control/target` sources while keeping other target outputs
ignored; the original thirty-one bytes/hashes and executions stay unchanged.
The final summary SHA is
`f63ff76aff763489621ec6c1115e0a7541334050a86016eae4ad7d4584538c2e`;
cost receipt is
`c6b104022c8b1580febcc81f8826c2b2f34c25fa87323540f5c8c4ce8b8da4b7`;
actual selected runtime is
`141ccb1f841b6d3687a09d7fa914b13c4b270a673635a96fa47d3f940214e0eb`.

## D metadata-first Board cost

The [D layout experiment](../engines/experiments/tiny-d-layout/README.md)
moves the Board's existing metadata before its 128-byte mailbox. Field types,
board/search/runtime statements, compiler/profile and loader/codec stay fixed.
Both layouts measure size 176, alignment 8 and four padding bytes. Metadata
offsets become small while mailbox indexing gains an offset; no size advantage
is assumed before compilation. Read-only consumers show no exposed Board ABI,
raw serialization or assembly field offsets, but semantic/physical candidate
qualification is not inferred from that audit.

Original scalar/HQ natives 8,348/8,736 B reproduce first. The one fixed layout
then reproduces at **8,220/8,576 B**, saving 128/160 B. With the unchanged fixed
codec and loader, actual whole files reproduce at **7,513/7,748 B**, saving
27/52 B from the original 7,540/7,800. Header/loader remains 1,115 B. These
are measured first costs, not qualified new runtime files. The experiment has
no engine or restoration-checkpoint executions; original image admission still
rejects the new native identities.

Twenty-five ordinary sources preserve the original native producer and the
separate whole-cost producer. Final handoff SHA is
`4f154f5869fb23a91165658a52ac875f319dbfd49c30ccd2ef83e34acf4a7cbe`;
final raw-source freeze is
`d807aa5889e2d43fb5da95160143dd2a2e8d46652d1779da54c137c30675e0d3`;
whole-cost receipt is
`255cb5028429d6a0aa5ddaba90673d7fe3964c278e4b381ed7666c21d337e1b5`.
The separately measured retry-phase/layout combination changes the scalar RX
page class and remains under its own explicit admission and qualification work.
Its gains are not added to these individual measurements.

## Fixed A/F private spelling and maintained F promotion

The [A/F spelling experiment](../engines/experiments/tiny-alpha-af/README.md)
applies one fixed role-audited map of 73 private type/member/local names.
Functions, global/static objects, external APIs, macros and opaque bytes stay
protected. No name, compiler or codec sweep is performed. For F, compact source
falls 12,722 to 11,216 B and the actual whole file falls **5,407 to 5,179 B**.
Both independent builds reproduce the exact original 22,664-byte native ELF,
including build ID and nonallocated bytes. Full raw preprocessor alias-only
inverse and final macro-dump equality pass. Two actual selected-file quit/EOF
sessions pass exact restored image, fixed startup TIDs, legal clock/bare results,
active closing output and physical settlement.

The original A attempt has a different outcome: replacing PLY with its equal
128 literal changes whitespace in the raw expanded expression. Its strict full
preprocessor inverse fails before candidate compilation, codec or engine
execution. That failure remains recorded; F's success does not admit A. An
initial diagnostic incorrectly expected configured resources in the compiler's
final macro dump. The corrected gate compares actual final dumps exactly and
keeps the original configured 2/18/128 probe separate; it does not normalize
whitespace or numbers to admit the failed A candidate.

Forty-two ordinary sources freeze both outcomes. Final experiment index SHA is
`6a955eae59e558c67ca4902ef1e75f18ee3d13a8372ef039105ff9887688e837`.
The two F engine sessions used the preserved original outer adapter. Its later
ownership repair was checked with stub children only, so those sessions are
not attributed to the revised adapter.

The maintained F builder now owns an ordinary `shipping_alpha.py`, embedding
the original policy bytes and the identical generic scanner/rewrite function
bodies. It admits only its exact canonical F and compact input; the experiment
folder, historical receipts and another engine's source are not build inputs.
DEV bypasses the new stage. Engine, native and DEV bytes, profile, compiler,
codec, launcher and existing helper bodies remain unchanged. The four-file
promotion expands fresh closure to sixteen ordinary sources.

Two independent source extractions each reproduce shipping and DEV twice.
Four new actual wrapper sessions cover sixteen GO epochs, exact native image,
persistent startup TIDs, legal results, active quit/EOF and reader/process/path
settlement. No forced cleanup is needed; cancellation causality stays unproven.
Whole-file SHA is
`41a730c266082b1c8285fef7972eb158704cd7411a475d4eecc9dd058ef587aa`;
promotion receipt is
`121713961ca1987f7fe299fc645f4572e80b4013206b698c1df77d19a6647a80`;
raw ten-local/sixteen-closure freeze is
`165855fcac4de546f3ae3b2de7bc16fc7ee741cdca39f5a007851b51c6204560`.
The 228-byte saving leaves F 1,083 B above 4 KiB. Core evidence is reused only
through exact native identity; no new strength or target-profile claim follows.

The later [A-only macro-preserving candidate](../engines/experiments/tiny-alpha-a/README.md)
retains the exact 31 A-present alias pairs and their gaps, while protecting all
eight PLY code uses instead of replacing that equal-length macro. This is a new
fixed candidate; the joint A failure above remains unchanged. It saves 249 B of
source and 57 B of actual whole file, **5,129 to 5,072 B**. Raw full-PP inverse
uses aliases alone, with no whitespace/number normalization; final dumps and
the separate configured 2/18/128 probe pass. Both complete native files equal
the original 22,672-byte literal before codec; DEV and all runtime/compiler/
profile/ALONE choices remain unchanged.

Two actual selected-wrapper quit/EOF sessions pass eight GO epochs, exact
restored native, persistent three TIDs, legal results and physical settlement.
The corrected outer ownership adapter is the executed version for these new A
sessions. This does not rerun broad core, sanitizer, game or performance proof;
core reuse is through exact native identity and cancellation causality stays
unproven. Thirty-three ordinary LF sources close the producer and verifier.
Final index SHA is
`5d0878cab7b9f7758bb12a11ea490c6e3fdc01f208aebdbdcb5536adcdf55f7b`;
actual runtime receipt is
`c7e8a9ef92184e6a30f5e8d7a7d5ebe067eeaade38ab6651539a5b77e0a549c7`;
whole-file SHA is
`47370ce2d27e84349eade3f7b3ff698f5e76f1cb382531e409420b6dbbbb8f2d`.
This separate local candidate remains 976 B oversized; its maintained-source
promotion has its own subsequent reproduction/runtime step.

The maintained A now promotes that exact candidate through four files: builder,
recipe, README and an owned ordinary `shipping_alpha.py`. Original forty-five
renames, fixed resources and thirty-one function spellings keep their order;
the new fixed map is the final shipping stage. DEV bypasses it. Canonical engine,
full native/DEV bytes, compiler, profile, launcher, template, existing helpers
and ALONE settings remain exact. The helper reads no experimental/historical
or generated-engine input. Original nine sources/archive and shipping/DEV
controls are preserved before replacement.

Two independent seventeen-file source extractions each reproduce shipping and
DEV twice. Four actual selected-wrapper sessions pass sixteen GO epochs,
restored image identity, persistent three-TID startup, legal zero-clock/bare
results and active quit/EOF reader/process/path settlement. Historical raw PP
and core proofs remain reused by exact identity; no broad campaign is rerun.
Promotion receipt SHA is
`41516d5993b1be2473c33dc7b3f42864a22d67963a63453f665eaef9e4122fb5`;
ten-local/seventeen-closure source freeze is
`54d773e921f115a4c6c801a485773621b4f81b94f348c1c55d3e2fecdc0da9b4`.
The original A/F failure and all frozen experiments remain unchanged. This is
a local source promotion pending a subsequent exact-head CI, still oversized.

## D retry-phase qualification and metadata composition

The [D retry-phase experiment](../engines/experiments/tiny-d-search-phase/README.md)
reuses the previously investigated finite retry-loop expression for D's real
eight-argument PVS calls. It keeps reduced null-window, full-depth null-window
retry and full-window retry decisions explicit. This is not a new search
algorithm, and the earlier A whole-file loss remains historical evidence.
Compact source falls 6,269 to 6,209 B; native scalar/HQ falls 8,348/8,736 to
8,284/8,672 B. Actual whole files reproduce at **7,501/7,753 B**, saving 39/47 B.

Four actual optimized one-worker DEV subjects pass twenty fixed cases against
the old source, comparing result rows, search trace, Worker, TT and game state.
Reduced-null, full-null retry and full-window retry branches are observed.
Beta-high has no dynamic hit in this finite campaign and retains source-path
reasoning only. Four actual selected-file sessions and two new pre-entry audits
pass image, three RX pages, 43 BSS pages, guards, permissions, fixed startup
TIDs, twelve legal results, reader/process settlement and no forced cleanup.
There is no new broad fault, game or performance campaign. Twenty-nine sources
and the final proof index are frozen at
`0649c0f6978a601b7e9297abd156c0c22b95a4d2e10b7f3cfa2170adbc4e0313`.

The separate [layout/phase composition](../engines/experiments/tiny-d-layout-phase/README.md)
combines exactly the metadata-first Board declaration and this search fragment.
Two independent builds reproduce scalar/HQ natives **8,124/8,512 B** and actual
whole files **7,478/7,718 B**. These measured whole savings are 62/82 B from the
original 7,540/7,800 B; they are not sums of the separate experiments. The same
fixed payload codec and 1,115-byte header/loader are used.

The actual scalar native now has two RX pages and BSS at 0x402000; HQ retains
three RX pages and BSS at 0x403000. Both retain 43 BSS pages. Root independently
read the exact repeat natives' ELF headers/program headers; the loader's new
per-form guard/reserve constants are still declarations, not physical proof.
Old production image admission remains unchanged and rejects the new natives.
The cost producer has no CHECKPOINT or engine executions. Named-field Board,
special-move/search and the new two-/three-page physical qualification are a
separate subsequent proof below; neither cost nor phase-only proof promotes
the combined image automatically. Twenty-eight ordinary sources are frozen;
handoff index SHA is
`2bda9d37186d0d171a5a7f3928929082085595b25399ed63382bd271209b639e`.

The separate [combined-image qualification](../engines/experiments/tiny-d-layout-phase-proof/README.md)
now closes forty ordinary source inputs without editing the frozen cost or
phase-only producers. Four optimized one-worker DEV subjects pass the same
twenty actual search cases, comparing normalized named Board fields/mailbox,
full Worker, TT and game state. A separate independent-oracle Board campaign
passes twenty-four fixed cases per subject, 3,051 nodes each, including perft
400/2,039/191, initialization, special moves/rights, all-square attacks, full
HCE, hash and reversible-path state. Layout normalization is limited to Board;
raw within-object snapshots and the other unchanged representations stay exact.
Reduced-null/full-null/full-window retries retain their observed coverage;
beta-high remains dynamically unproven in this finite set.

Four actual shipping quit/EOF sessions and two separate pre-entry CHECKPOINTs
pass exact native/restored bytes, RX/BSS padding, permissions, image and worker
guards, FD012/no children, three persistent startup TIDs, twelve legal results,
exit 0, reader join and owned group/TID absence. Scalar's two-page RX, BSS at
0x402000, upper guard 0x42d000 and reserve 0x2f000 are now physically observed;
HQ retains its separately observed three-page class. Both have 43 BSS pages.
No forced cleanup is required. Loader/codec/runtime/pool are unchanged source
inputs, not new broad fault or game executions. Original production admission
remains unchanged during this experimental proof. Final index SHA is
`b05e3e344983c0bc340c28570b0229c8c5ab3cb1e579ca0e3bf290ac8a51cc83`;
actual physical receipt is
`dfcebada0c43fee2dba85893385f261bc398b4c4808a90a6d90055ef1c922add`.
The qualified experiment remains 3,382/3,622 B oversized. Its separate
maintained-source promotion has not been included in these experimental runs.

The maintained D entry now promotes that exact header/search pair and the
qualified native/whole/audit literals through seven files. Six other native
sources, runtime/pool, loader/codec, compiler/flags/profile, fresh-source tool
and LF policy remain exact. Packer admission binds each full native SHA/size
to its own HQ flag, entry and complete mapping class. The independent verifier
requires the full per-form literal layout. This is not a generic two-/three-page
permission, and historical experiment guards remain unchanged. Earlier DEV
identities are explicitly ancestry only; the changed Board/search does not
claim byte-identical DEV binaries.

Before editing, the old eighteen sources, archives and native/whole/audit
controls are preserved externally. Two independent twenty-member source
extractions reproduce eight natives, eight whole files and four separate
audits. Eight new actual shipping sessions and four pre-entry checkpoints
pass exact restored images, the two mappings, twenty-four legal results,
startup/guard/permission checks and physical settlement, with no forced cleanup.
The new maintained source closure reuses the separate Board/search proof by
exact fragments; it does not rerun broad fault, game or benchmark campaigns.
Final promotion index SHA is
`b8f7c95d3606caae4ce251258e9ed1a60522690f805a64ce1683166f61c49421`;
fresh actual results SHA is
`87b78afdc9438aaf34d43f5b118ce89e1fa5558030d437ccc4ba3730c741e8fc`;
closed source archive SHA is
`49a1fd6266dfe3a374a250d962eb82473e6f38e5ab9367647e339cee9fa2f184`.
This local source promotion awaits its subsequent exact-head CI and remains
oversized; reduced beta-high dynamic coverage, strength and target scaling
are not enlarged by the promotion.

## Rust D ASCII data8 packed cost and positive observation

The [new data8 experiment](../engines/experiments/tiny-rust-d-packed-ascii/README.md)
combines the preserved borrowed-ASCII inputs with the constructor candidate in
an explicit class separate from the old data16 packed image. All four matched
forms reproduce full native and whole bytes twice before observations.

| Form | Payload | Whole file | Saving from matched ASCII control |
| --- | ---: | ---: | ---: |
| ASCII control HQ | 10,647 B | 11,762 B | Baseline |
| ASCII control scalar | 10,288 B | 11,403 B | Baseline |
| Put-start HQ | 10,450 B | 11,565 B | 197 B |
| Put-start scalar | 10,091 B | 11,206 B | 197 B |

Each whole includes 1,115 B of loader/headers. Constructor `.text` reduction of
272 B therefore becomes an actual packed saving of 197 B. The older data16 to
ASCII-control saving, 792/791 B, is a different comparison. Original full native,
sectionless span, payload and whole identities remain distinct. The sectionless
span is 16,392 B; data8 stores only memcpy at 0x400146. OUTPUT is four bytes at
0x404008, followed by padding at 0x40400c. RX4/RW1 and five decoded pages remain.

Two actual pre-entry CHECKPOINTs bind a single stopped TID, FD012/no children,
all five restored pages, initial zero OUTPUT/padding, data8, guards and observed
permissions. SIGCONT is followed by protocol/exit; no new instruction-pointer
trace is claimed. Four shipping quit/EOF sessions bind three persistent startup
TIDs and two guarded 1 MiB worker stacks. Each session observes CPU tick growth
and active workers at GO replacement, position replacement and shutdown. All
twenty-four admitted GOs have exactly twenty-four consumed legal bestmoves,
with complete output/readers, exit 0 and no forced cleanup. An independent
postrun check verifies sixty-nine preserved files and ten five-page snapshots.

The positive observation is complete for this fixed profile. Runtime admission
and all loader conditions remain incomplete; READ_IMPLIES_EXEC rejection and
cancellation causality remain unproven. No negative/personality/register/ptrace,
new kernel join trace, deep/fault, benchmark, game, training or AWS campaign is
attributed to this class. The old failed fixture and controls remain preserved.
Twenty-two ordinary sources are frozen. Final index SHA is
`eaae61309580f5dfa0758f3b38df98a41c58eef296749836fc9c226ca25601d3`;
actual positive runtime receipt is
`a5221549c16adb9af08c0d46a90e023481f269773fa61916703353131f98aeb4`.
Both whole files remain oversized, and this experiment does not replace the
maintained Rust D profile or establish final target strength/scaling.

## E feature/material-pass composition: measured loss

The [E fusion experiment](../engines/experiments/tiny-e-feature-dead/README.md)
collects the existing insufficient-material classification during the existing
twenty-one-coefficient leaf feature pass. DEV retains the prior source path;
the candidate's normal shipping source uses one fixed structural composition
and the same fixed eighty-nine-name policy with its own literal input counts.
No existing helper or historical guard is broadened.

The exact maintained E5679 control reproduces twice first. Candidate shipping
source falls **12,641 to 12,626 B** and native falls **26,408 to 26,376 B**, but
the actual complete file grows **5,679 to 5,683 B**. Both independent candidates
reproduce source/native/bootstrap/whole bytes. Candidate alias-only full-header
inverse, final macros and pre-/post-alias full native equality pass; the
structurally changed image is not equal to the old E native. The measured
whole-file loss ends this candidate. There is no candidate engine/semantic,
DEV-native, game, benchmark or promotion campaign; maintained E stays 5,679 B.

Twenty-five ordinary LF source inputs preserve the candidate and the control.
Final index SHA is
`cb99a23f854792459be534a06bbb5836d138cb68850852bf078e20a5d8ee1ff9`;
actual first-cost receipt is
`2c2417db620d65f12d31807529dc13a055bcd3b037c6a69c328b7382e0149b0b`.
This records a rejected size result, not new functional acceptance for E.

## A/F private object spelling

The [storage18 experiment](../engines/experiments/tiny-alpha-storage-af/README.md)
adds one fixed `qa` through `qr` mapping for eighteen private shipping objects
after the earlier type/member/local policies. The original conservative object
protection was audited against actual consumers: pthread/atomic calls use their
addresses and values, and these single-translation-unit entry builds have no
consumer of the remaining object spellings. Public/API functions, directive
consumers, types, members and strings remain protected. In particular Move is
still consumed by the MOVE directive and remains unchanged. Aliases are not
searched or retried; actual source and expanded-header freshness are checked.

| Family | Compact source before / after | Whole before / after | Actual whole saving |
| --- | ---: | ---: | ---: |
| A | 10,606 / 10,184 B | 5,072 / 4,980 B | 92 B |
| F | 11,216 / 10,745 B | 5,179 / 5,083 B | 96 B |

A uses seventeen names at 87 occurrences and F uses eighteen at 99. Actual
source savings are 422/471 B; the earlier manual estimate missed one mutex
occurrence per family and remains preserved separately. Both independent
candidate natives match the original complete ELF bytes before codec. Raw
full-PP alias-only inverse, complete final macro dumps and separate configured
profile probes pass. DEV, native code, compiler, profile, codec and launchers
remain unchanged. These equivalences are scoped to the admitted A/F entries,
not an assertion about unstripped entries in other families.

Four actual selected-wrapper sessions pass sixteen GO epochs, exact restored
native image, three persistent startup TIDs, legal results and physical
reader/process/path settlement. Cancellation causality remains unproven.
Forty-four ordinary sources freeze the producer and the executed adapter.
Final index SHA is
`2824e102ceb29316a522982fb8c249c0f8fd8588a2cfa0e4b6b4d5fb9649074c`;
actual runtime receipt is
`304b37c55065752cb1c723ad73e9d713f6681c32fc8ad91616a2ac340afc7ea1`.
The candidates remain 884/987 B oversized. Their subsequent maintained-source
promotion and fresh-archive execution are separate steps.

The maintained A/F entries now promote those exact selected bytes through six
builder/recipe/README files and one shared ordinary
`engines/scripts/fixed_shipping_storage.py`. The helper embeds the identical
fixed policy and lexical/opaque checks; its readable reservation union is
embedded from the exact audited canonical inputs. A caller supplies only its
own family's canonical/source bytes. There is no runtime experiment/report,
other-family file or generated-source dependency. The stage follows the local
alpha map, and DEV bypasses both shipping stages. Existing engine/local alpha,
fresh/verifier tools, compiler/profile/template/launcher/codec remain exact.
The root helper LF attribute is separate repository metadata.

Old A10/F10 sources, closures, archives and shipping/DEV outputs are preserved
before editing. New normal source closures contain eighteen A files and
seventeen F files, twenty-eight unique files. Each family archive has two
independent extractions, each repeating shipping and DEV generation/compilation.
The full native ELF and both DEV identities remain unchanged, without build-ID
or nonallocated-section exceptions. Eight new actual wrapper sessions pass
thirty-two GO epochs, exact native image, persistent three-TID startup, legal
clock/bare output and active quit/EOF physical settlement. No new broad core,
PP, game, benchmark or DEV-engine run is inferred; earlier source/PP/core proof
is reused by exact source/native identity.

Final maintained promotion index SHA is
`71b68e367a2505b3bf21b6f36ad527f5da52b317b4549da27a75a1186661dcb5`;
raw-source/output freeze is
`fa731d627a422c08ad94311fea50b14ac29667db726fb7c3b0fb3ccd6764b047`;
normal-source union archive is
`ab663f9f8aae0ce2ca40634566256917c4c639be52a9af03a52ec1ad9e2bb7ae`.
This local source promotion awaits its exact-head CI. Both families remain
oversized and cancellation causality remains unproven.

## B bitboard material predicate: unchanged whole cost

The [B dead-bb experiment](../engines/experiments/tiny-b-dead-bb/README.md)
replaces only the insufficient-material mailbox scan with existing coherent
piece/occupancy bitboards. It introduces no new Board state or table. Its
unsigned minor-population and bishop-color expression is statically equivalent
under the canonical bb/mailbox consistency contract; no repair of stale or
arbitrary manual objects is implied.

Readable source falls 77 B, pre-alpha shipping falls 47 B, but after the same
fixed policy compact source falls only **13,606 to 13,602 B**. Native text grows
7 B while the full ELF remains 26,592 B with different contents. The actual
complete file stays **5,955 B**, a zero-byte saving. Both original controls and
independent candidates reproduce. Candidate alias-only full PP inverse, macro
definitions and full native equality before/after alias pass; the old and new
structural natives are different identities.

Twenty-four ordinary sources freeze this neutral first cost. Final index SHA
is `f77eab167403f98d570adfe7063f831d259470f6e0fb05f23a0f8fbc012b6148`;
actual cost receipt is
`a0abaebf810de912c9a997a5ac9000aed6b203574c3f88a2e694550f05824bb3`.
There is no candidate engine/material fixture/board/search/runtime/game or
benchmark execution, no promotion and no speed claim. The target5899 source
remains a separate candidate and is not combined with this measured result.

## C query/reset/startup composition first cost

The [C entry composition](../engines/experiments/tiny-c-entry-composition/README.md)
transfers three source decisions into the actual C program: nullable-text query
and made-child replay share one legal walk; think owns best reset instead of a
GO-wide worker loop; startup arrivals share pending and the existing wait.
The entire prefix before think, including Board/shipping-v handling, rules,
PSQT constructor, actual AVX2 leaf, TT and search, remains byte-identical.
King-capture/list guards and compiler/profile/codec remain unchanged. Initial
stopped becomes one before first GO and direct think resets best; these private
differences require their own C tests rather than inherited A acceptance.

Readable source falls **27,003 to 26,692 B**, compact source **12,526 to
12,224 B**, native **26,464 to 26,424 B** and actual whole **5,723 to 5,687 B**.
Original shipping/DEV controls reproduce twice, and both independent candidate
source/native/bootstrap/whole files match. Candidate full native bytes before
and after fixed89 alias are equal; they differ from the old C native.

The first attempt stopped before candidate compilation because a new owned guard
incorrectly requires raw macro-dump order equality. Complete raw definitions
and duplicate counts are equal, with order only different. The failed run and
its source snapshot remain preserved. The corrected owned gate uses
Counter(raw.splitlines(keepends=True)): every definition byte/ending and count
must match, while raw-order equality is recorded separately as false. No
whitespace or numeric normalization is introduced, full raw PP alias inverse
remains strict, and existing frozen helper/guard domains stay unchanged.
Independent review also repairs a nonunique inverse site and establishes owned
process-group lifetime for candidate preprocessing before successful compilation.

Twenty-eight ordinary sources close this cost-only candidate. Final index SHA
is `f98cfee22ee4c2895719d4a6286873c12d49ca4cdce11c9ee4a16eea40b65244`;
successful actual cost is
`88e1dc9273c7231e33ff2783323b55353937c9a6c795b6727fc3fb31ba208932`;
preserved first failure is
`9e67f4282cb8ad710e51a996d1229bea2cff66c3453b5fea9a68ff9bccdc49db`.
At this first-cost checkpoint candidate DEV/engine/semantic execution is zero.
Selected executable candidate-1/2 files are mode 0755; the selected/x copy is
0644 and has not been executed. C-specific query/ownership/startup/SIMD and
selected-wrapper proof is a separate in-progress step. This candidate remains
1,591 B oversized and does not replace the maintained C entry automatically.

## C composition: bounded functional qualification

The [C composition proof](../engines/experiments/tiny-c-entry-composition-proof/README.md)
now qualifies the same 5,687-byte candidate through its changed query, startup
and GO ownership paths. Four actual old/new O2 and ASAN+UBSAN forms pass the
independent Board/query checks, including legal children, invalid text,
transactional replay, repetition hash, reversible-path digest and raw SIMD
HCE/scalar parity. Five controlled pthread startup schedules cover early/late
arrivals and creation failure after zero or one successful creation. The real
epoch fixture observes four GO epochs and pending completion before root reuse.
The unchanged actual SIMD evaluator and standalone native disassembly are
checked separately from those ownership fixtures.

Exactly two selected whole wrappers, one quit and one EOF, produce eight legal
GO results. The unchanged C verifier observes the new native identity,
three startup TIDs, FDs 0/1/2, one closing result per session and physical
reader/process/private-path cleanup. These are actual restored candidate
executions, not inherited A results. Candidate DEV has not been built or
admitted in this proof, and old C full-native equality is not claimed. The
epoch fixture covers early claim abort and depth-zero fallback; it does not
establish deep iteration publication or general race freedom. Cancellation
causality remains unproven.

The first query fixture incorrectly labels a move legal in its pinned-rook
root as invalid. Its abort and source are preserved; only that text token is
corrected, independently rejected on all roots, before the four passing forms.
The final record accounts for all five attempted query executions. Fifty
ordinary sources are frozen with final index
`f3278861a28f37adfb2aead6f7ce2f8558caf261ff77f8f68c70380d996e0641`,
source freeze `a22ecac4bcd283128793b2fb7256504dbc3bcc669dca64eee25d4274fb7547b0`
and source archive `7262ca5ac6c734698d7ba80aa1101e5d7829a7724dc476b77cf36857a139186a`.
The recorded 48 owned PIDs/TIDs and both restoration paths are absent at final
settlement. Maintained C promotion is a subsequent, separate step.

## B/C/E storage spellings: original native-identity failure

The [B/C/E storage experiment](../engines/experiments/tiny-alpha-storage-bce/README.md)
applies the same fixed eighteen object spellings to ordinary B5955/C5723/E5679
controls. Source falls by 535/461/449 bytes respectively, but the original
full-native-identity contract fails on the first B candidate. Baselines for
all three families reproduce twice before that compile. Candidate native
compilation then stops: B has one attempt, C/E have none, and candidate codec,
whole-file measurement and engine execution remain zero.

The observed B file changes from 26,592 to 26,496 bytes. Direct ELF inspection
finds unchanged program headers, allocated-section geometry, code/data,
dynamic symbols and relocations. The GNU build-ID descriptor and nonallocated
symbol/string/section metadata differ after source object renaming. These
observations do not satisfy the original full-file identity assertion and do
not prove semantic or ABI qualification. The failed original producer and its
52 ordinary sources remain frozen; a new, separately named metadata boundary
can be evaluated without relabeling this failure as success. Original final
index is `0bf7fa1b7fc6d74b40a0d59c30bf91c5bca7c6f729a90330d5129851c6193e66`.

## D completion latch: measured cost before lifecycle qualification

The [D completion-latch experiment](../engines/experiments/tiny-d-completion-latch/README.md)
reuses pending for startup arrival and search/result completion while retaining
epoch and quitting. A GO publishes WORKERS+1; the last search result owns the
remaining value one until output finishes, then releases zero for main-thread
reuse. Startup creation failures bypass the arrival barrier and retain
kernel clear-TID joins before stack/TT reclamation. Board, search, HQ logic,
compiler profile, loader and codec stay unchanged.

Both ordinary controls reproduce twice before the candidate whole builds.
Scalar native falls 8,124 to 8,092 bytes, HQ 8,512 to 8,480; actual whole files
fall 7,478 to **7,457 bytes** and 7,718 to **7,707 bytes**. Both independent
candidate builds match. The unchanged loader/header cost is 1,115 bytes;
payloads are 6,342/6,592. BSS remains 175,092 bytes despite the removed source
objects. The original admission rejects the new native identities; only the
separate exact cost adapter admits them for this measurement.

Independent actual-file review confirms whole/linked byte relationships and
bounded Deflate plus BCJ restoration to the fresh native bytes. This is data
restoration and cost evidence; candidate engine, checkpoint and runtime mapping
execution are zero at this frozen stage. Lifecycle qualification is separate.
Twenty-four ordinary sources freeze the final cost index
`05b027c5ec0e21da9ab6fdc91c8120984e2cea2e11b993edd5ceed1076748e0e`;
actual whole receipt is
`628ea7e3eccae0c20ade39997836a838b03e60ed128dc1eadc8a0119fd556bca`.
Neither measured file meets 4KiB, and no performance or strength gain is claimed.

## Maintained C composition source promotion

The [maintained C entry](../engines/compact/tiny-entry-c/README.md) now owns the
qualified 5,687-byte composition as its ordinary readable engine source.
Five local files change: engine, builder, recipe, README and one new local
shipping-alpha helper. The helper embeds the exact original C composition
policy and calls the existing pinned shared generic scanner/rewrite with its
own canonical bytes. It neither calls nor widens the old shared admission;
B/E and all existing shared helper bytes remain unchanged. The compiler,
profile, codec, bootstrap, launcher, fresh/verifier and core prefix are exact.

The old seventeen-file C5723 closure and shipping/DEV files are preserved and
reproduced from two independent archive extractions first. New DEV source and
native are generated twice from the qualified readable and explicitly pinned;
old C5723 DEV/native equality is not claimed. New normal generation consumes
eighteen ordinary sources, including the local helper, and reads no historical
report, experimental folder or old generated artifact.

Two independent new source archive extractions each regenerate shipping and
DEV twice. All source/native/bootstrap/whole and new DEV bytes reproduce.
The unchanged verifier then executes both selected builds: four actual
quit/EOF wrapper sessions, sixteen legal GO results, exact restored native,
three stable startup TIDs, FDs 0/1/2 and physical reader/process/path cleanup
pass. No new DEV engine or game/benchmark is executed. The earlier C-specific
query/startup/epoch/SIMD proof is reused through exact readable, shipping and
native identities; cancellation causality remains unproven.

The final promotion receipt is
`a3d54a16e4df0f18a3da3ea2361fd8138ec91903140f19fe06256922bef970be`;
normal source archive is
`a613040357d46f33bf5c59c72a2fc7a8d1830fce9a14fc6d0420d3a46835a75c`.
New whole is 5,687 bytes, saving 36 and still exceeding 4KiB by 1,591.
Its own `034e9d8` exact-head C/Rust and repository lifecycle CI passes, as linked
above. The C job regenerates and runs this maintained entry. This does not
replace other experimental scopes with additional CI engine executions.

## A/F stop-load macro: smaller source, larger whole files

The [fixed qA experiment](../engines/experiments/tiny-af-stop-macro/README.md)
replaces the three A and four F identical relaxed stop-load expressions with
one fixed macro after the final include. The macro still expands at each
original site and retains F's short circuit. All original controls reproduce
twice before the candidate work. Actual full expanded bytes are identical,
and raw macro-line Counters differ only by the one exact new definition.
Both complete candidate natives equal their original full ELF bytes before
either fixed codec call; two independent packages per family reproduce.

The define-inclusive source falls A10,184 to 10,110 and F10,745 to 10,627
bytes. Actual whole files grow A4,980 to **4,983** and F5,083 to **5,087**.
Both candidates are rejected for promotion. Maintained A/F remain unchanged,
and candidate wrapper, DEV, semantic fixture, game and benchmark counts are
zero. No alternative spelling, placement, compiler flag, codec or retry is
attempted. This measured loss is retained instead of inferring whole savings
from source length or starting runtime tests for an unselected candidate.

Thirty-seven ordinary sources close the producer. The raw thirty-tool receipt
is `c3d67f5d81de3f67fa50e9032696406ed66931e191b88a95a55cc336cb944d2d`;
final source/cost index is
`6a78e50f2819950dde3ade2bf55c4bbb5a9ca4230a122e33017b4f6e4f04b0fe`.
All tools terminate without forced cleanup. The producing source snapshot is
preserved; the final README result is the only post-cost source change.

## B storage spellings: distinct metadata class and maintained promotion

The separate [B metadata stage](../engines/experiments/tiny-alpha-storage-bce/METADATA.md)
now measures the same fixed storage18 source under an explicitly different
native-image contract. The original full-native assertion stays failed. The new
qualifier pins both entire files and accounts for the header, section payloads,
symbol/string records and intervening bytes. All program headers and allocated
section geometry remain exact; code/data, dynamic symbols/strings and
relocations are exact. Only the literal build-ID descriptor, section-table
pointer and the specified nonallocated metadata of nineteen object symbols may
change. Local symbol ordering and raw attributes remain fixed; permitted global
symbol order is compared with exact mapped record multiplicity. No stripping,
normalized executable or general ABI equivalence is claimed.

Forty-four pure byte fixtures pass, including repinned structural mutations.
The fixed normal producer first reproduces B5955 twice, then independently
compiles and packages the new candidate twice. Candidate C/E compiles and all
target executions remain zero in that cost stage. Actual whole cost is
**5,851 bytes**, saving 104; shipping source is 13,071, saving 535. Independent
actual-file readback confirms the two full natives/wholes, 26 allocated-section
geometries, unchanged remaining payloads, strict XZ restoration and the exact
compiler-stdin source. Cost receipt is
`d5d4729a808e031f5f76d63e946be00a2e321c16ae47a8bb919d8d723debf9d4`;
readback is `84030a2193e74b2804dbba3d294aae1bd41247583ec1a08a8b9c03b7217fae13`.
The pure fixture loader uses an explicit local import for its documented
isolated Python invocation; the qualifier and its literal policy are unchanged.
The producing 57-source snapshot remains preserved, with only the final result
documentation added afterward.

The [maintained B entry](../engines/compact/tiny-entry-b/README.md) now applies
this fixed mapping through one local embedded-policy helper after unchanged
shared89 alpha. Canonical B, DEV, compiler/profile/codec/bootstrap/launcher and
the existing shared C/E helpers remain unchanged. The three generic scanner/
rewrite function ASTs match the experimental reference. Normal builds consume
eighteen ordinary sources, without experiments, other canonical families,
historical reports or old generated files as inputs. Admission requires the new
full native SHA; it never presents this image as the old B native.

The old seventeen-source normal closure and shipping/DEV files are preserved
and reproduced first. Two independent new source extractions regenerate
shipping and DEV twice each. Both fresh wrappers then pass the unchanged B
verifier: four actual quit/EOF sessions, sixteen legal GO results, new native
identity, stable three-TID startup, no live compiler child/private path and
physical reader/process settlement. New DEV bytes equal the old full files;
there is no new DEV runtime, game or benchmark. Existing rule/search evidence
is reused within the exact canonical/source and machine-code boundary, not
through an assertion of old full-native equality. Cancellation causality remains
unproven.

The final promotion receipt is
`7837cec084aa65e2a7541765fa2a7a60a8050445d14f2fe297e6d0fc7fdacbf6`.
The executed normal-source archive is
`eb6d28e0a58dc8d96035fff51359d1b82c26a8c116635f4690139cf9bc58069b`.
After those runs, README alone removes an unsupported FD-observation claim;
the receipt pins both documentation versions and all unchanged executable
inputs. The first collector's mistaken C-only field lookup is preserved as a
collector failure, not an engine failure; it causes no engine rerun. FDs are
not claimed as observed by the unchanged B verifier. This maintained promotion
subsequently passes exact-head `2a0d99a` CI, recorded above, and remains
1,755 bytes above 4KiB.

## D completion latch: actual output reservation observed

The [D publication observation](../engines/experiments/tiny-d-completion-latch-proof/README.md)
executes the exact unmodified 7,457/7,707-byte scalar/HQ first-cost shipping files.
Its parent fills an empty blocking stdout pipe, then queues GO, a replacement
position and the next GO. Read-only /proc inspection observes a worker blocked
in its actual bestmove write and main blocked in the private futex wait, while
the BSS word addressed by that futex is **pending=1**. Both forms retain the
original futex expected argument three from the earlier wait; that argument is
recorded separately from the current word one. The old result therefore still
owns the output reservation while main is waiting to reuse engine state.

After draining only the parent's filler, both ordered old/new-root results are
independently legal and pending subsequently becomes zero. Two actual wrappers
execute four GO epochs with stable three-TID startup, natural quit and output
EOF settlement, no forced cleanup. Actual own-loader/native identities, RX padding,
mapping permissions and guards, nonexecutable main stack and descriptors 0/1/2
are observed. There is no target code/memory/register patch, personality change,
compiler invocation, game or benchmark in this check.

The exact runtime receipt is
`99320b49fefaa20644a1261bbe82fd29984e6d9d674367b2a6a3643a0c5b28bc`;
source/runtime intake is
`901012de7ebd790e8aea3e87ecae0a88c8bff96276fa3761822880df595b1857`.
Both validator source files are frozen, the existing oracle is raw-hash pinned,
and all six recorded TIDs are absent at final intake. This is bounded output
publication evidence, not general race freedom, new startup/partial-clone fault
coverage, initial zero-BSS observation, cancellation causality or maintained D
promotion. The earlier cost receipt retains its original zero engine-execution
count; these new sessions remain separate. Normal-source promotion and newly
bound pre-entry audits were open at that observation checkpoint; the following
promotion supplies their separate evidence.

## Maintained D completion latch and fixed A/F source costs

The [maintained D entry](../engines/compact/tiny-entry-d/README.md) now regenerates
the exact 7,457/7,707-byte scalar/HQ completion-latch files from eighteen ordinary
sources. Six files change: runtime, build metadata, recipe, exact packer/verifier
admission and README. The twelve other files, including seven native inputs,
loader/codec and fresh driver, retain their raw bytes. Board/search/HQ, compiler,
resources and finite public policy stay within their existing source contracts.
New full native identities and entry points are explicit; no generic page-range
admission or old-image fallback is introduced.

New CHECKPOINT audit images measure 7,480/7,730 bytes. Two independently created
closed source archives and the archive used by the unchanged fresh driver have
identical bytes. Two source extractions independently reproduce eight native,
eight whole and four audit files. Eight actual shipping sessions (four quit,
four EOF) produce 24 independently legal results, and four pre-entry sessions
observe zero BSS/padding and exact restored RX/guard permissions. All twelve
sessions settle naturally with reader EOF/join and absent owned groups. The
routine verifier does not resample the pending latch; the separate actual
output-reservation observation above supplies that narrower fact.

The final source/promotion index is
`8ace0b06b07dcf4d44a12d5210a068ed357f0bf1149c6322f3d8bc77d02f5dd1`;
fresh execution is
`d656183b4a41fbc35fdfb2eb6ca8b786e3e3666ce2c7d970251050703711cc04`.
The actual source archive is
`965f0e33150a02cdbea35efdfe4349ee0486d06e7a37ad3eb49b966d436669f5`.
Partial-clone failure bypass and created-TID joins are source-complement reuse,
not new fault executions. The actual reclamation order is created-TID join,
main return and exit_group; there is no explicit stack munmap or TT free.
New DEV identity, general race freedom, cancellation causality, strength,
scaling and 4KiB acceptance remain unclaimed.

The [fixed A retry experiment](../engines/experiments/tiny-a-source-composition-next/README.md)
consolidates four child-search call sites into one retry-state loop. Its
protected 24,228-byte source complement remains exact. Original A4980 is
reproduced twice first; the sole candidate then reproduces twice. Readable
source falls 69 bytes and shipping source 28, but the complete file grows
**20 bytes to 5,000**. Its new native has the same length and a different full
identity. This is a measured loss, so maintained A4980 remains selected. No
candidate engine, DEV, game or runtime qualification runs. The final 26-source
receipt is `d5c8b61991877935c2645f43ce70197bc5b06878c2290c12e9146c66609e1baa`;
cost is `429597181a78b6ac825078cf5394a3e01076d1f593bfc7ab3b5eacfaae6e0378`.

The [fixed F composition experiment](../engines/experiments/tiny-f-source-composition-next/README.md)
shares nullable legal query/made-child replay, think-owned reset and startup
pending. The complete 15,340-byte search prefix and 1,354-byte MTD driver remain
exact. Its original 73 alpha and eighteen storage maps retain their decisions;
the new source/count domain is separate and literal. Original F5083 reproduces
twice first. The sole candidate independently reproduces source, native and
whole twice: shipping source falls 268 bytes to 10,477; the new native grows
eight bytes to 22,672; the whole file falls **32 bytes to 5,051**. Actual raw
preprocessing alias inversion, macro-definition bytes/multiplicity and header
freshness pass. This is cost evidence only; maintained F5083 remains selected
while new F-specific query/startup/result qualification proceeds separately.
Engine/DEV/runtime executions remain zero in the immutable first-cost receipt
`c9b2cbb83662610965b9ccd1ebc3935f73db605ec5853775836d5abd3c219313`.
The 28-source final summary is
`4c5a0779fbd5aa2c16fbc0a43aa8bbfc5d70d10247c35a26df8b4885603f409d`.
Root independently reads both cost files' actual representations, strict LZMA
restoration and compiler-stdin source; source/archive/frozen bytes match.

## Current C/E storage observation: original string-packing failure

The [current C/E storage study](../engines/experiments/tiny-storage-ce-current/README.md)
uses current C5687 rather than the older C5723 domain. Both original builders
reproduce their shipping files twice before the first candidate native. Its
fixed eighteen-name map reduces C source by 422 bytes and E source by 449.
Only the first C candidate native is compiled. Full native equality is not
asserted: old C is 26,424 bytes and this new identity is 26,344.

The observer passes program headers, allocated section geometry, other payloads
and the seventeen mapped object records, then rejects its complete stored
string-entry Counter. That failure is preserved. C's second and E's candidate
compiles, all candidate codecs/whole files/engines and the later file-gap loop
are zero/unreached. The observer is not edited to turn this result into success.

Independent physical parsing identifies the precise representation assumption:
old global object table references byte 130, a suffix five bytes into stored
tiny_table at 125. New tiny_table remains a local BSS object with the same value
and size, while qq has a separate stored entry at 818. The only extra complete
stored entry beyond the literal mapped Counter is qq. ELF string indices can
reference substrings; this is permitted by the
[ELF gABI string-table contract](https://gabi.xinuos.com/elf/04-strtab.html).
A separately named exact suffix-packing class requires its own source/actual
byte review; no metadata, runtime or maintained promotion is yet claimed.

The immutable original 38-source final summary is
`83ca8460a6d06ddf5def9e6cbd470b3d8f182d6a25e630d1792a07c3034497ed`;
the failed producer is
`dfa01b450ab9fefc1fe795ae8bf8b8f8d0211c364ab92779a1be7250683841e7`.
Root verifies all current raw inputs and the actual suffix/object attributes.
Old B's independent nineteen-pair qualifier and its earlier failure stay exact.

A separate read-only A/F bootstrap audit finds no safe substantive size
simplification. It also narrows prior cleanup claims: existing poll/leader-wait
logic does not establish absence of same-group compiler descendants after an
early leader exit. This is a static control-flow limitation, not an observed
failure of the successful startup sessions or a new executed fault campaign.
The external audit is
`55567a59592a9db13b5027ed57c073087e854441f3fab436df2d3575a50efd38`.

## F5051 functional qualification and separate E5647 first cost

The [F-specific proof](../engines/experiments/tiny-f-source-composition-proof/README.md)
qualifies the exact F5051 source composition without changing its frozen cost
inputs. Old/new optimized and sanitizer query forms compare shipping Board176's
incremental v/h/r, legal children, special positions and atomic replay/history
transactions against an independent 64-square oracle and scalar evaluation.
Five actual pthread startup schedules cover two successful arrival orders and
three expected partial-create failures. A four-GO actual runtime diagnostic
observes positive-pending replacement/position waits, natural own-clock expiry,
result ownership, two joins and subsequent TT free.

Focused old/new DEV1 diagnostics execute six actual think calls. Independent
minimax checks the completed quiet depth-three value and attaining witness.
A new startpos job completes depth one at 31 nodes, then a limit of 32 interrupts
the next iteration while retaining that same job's completed best/score. Old/new
observed states match. This is a narrowly bound diagnostic, not a packaged DEV
identity, search-strength comparison or inherited C proof.

The unchanged F verifier then runs exactly two actual F5051 wrappers, quit and
EOF, producing eight independently legal GO results. New restored-native SHA,
three startup TIDs, compiler-child/private-path cleanup, reader settlement and
physical exit pass. The genuine cost receipt is copied verbatim for explicit
QA artifact admission; the executable link targets the actual mode-0755 first
cost file. FD012 is not claimed because the unchanged F verifier does not record
FDs. Cancellation causality remains unproven. The private stopped/best-reset/
failed-child and bounded nullable-text-work differences remain explicit.

All 61 proof sources, actual snapshots and archive bytes are frozen; the 28
cost sources retain their original bytes. Final proof summary is
`eed7014b750abfdd19381be83091ecf7ede32e60973228dc6b548ed87153a4f0`.
Actual wrapper outer/original-verifier receipts are
`e88aa70a80b473801e5fe2e62e4b73d1fdf83afa0b2a0fa72fd29b4b267b16b3`
and `e595137d5aaa03394dd1f1618eb36896fb40167e4cd9b6bd2ec48843e8b4dc49`.
All 31 recorded PIDs/TIDs are absent at final intake. Normal F promotion remains
separate and must discover and pin its new DEV bytes from ordinary source.

The [separate E composition](../engines/experiments/tiny-e-source-composition-next/README.md)
applies the analogous nullable query, made-child replay, think reset and startup
pending changes to E5679. Its E-only DEV order call keeps tiny_order on the
original position rather than the made child. All 21 coefficients and the
18,042-byte Board/model/search prefix retain their exact source. New local
literal admission keeps the same 89-name map without widening shared domains.

The one candidate measures source 12,339, native 26,376 and whole **5,647 bytes**,
saving 302/32/32 respectively against E5679. Both final representations reproduce
twice; actual full-PP alias inversion, raw macro multiplicity and freshness pass.
Engine/DEV/runtime executions remain zero at this immutable cost checkpoint.
Its 23 ordinary sources are unchanged after execution; cost summary is
`37976679f0b99e2fc4877ea20ff6367cf70d7f253bc169b34ce9a7ab4bff5012`
and cost receipt is
`6857c539c7d881a7e6a897b27f694ac0d2e76634ae64fdda888209b326b35a28`.
The current maintained table is not replaced by this first-cost result.

Actual work includes four control compiles/packages: an outer pipeline pair,
then an unchanged ordinary-builder pair. Two additional pre-alpha candidate
compiles completed before scope correction arrived; their outputs/counts are
preserved and are not presented as required validation. Two earlier preparation
errors stopped before preprocessing/compiler/codec work and remain separate
incomplete receipts. Candidate wrappers are preserved as mode0644; future
execution uses an explicitly bound separate executable copy. Cost tools returned
terminally, but no new group-absence/reader proof is asserted for that stage.
Root independently verifies current sources, both actual representation pairs,
strict XZ restoration and AST compiler-stdin source for E as well as F.

## Maintained F5051 and new size-analysis intake

The ordinary F producer now includes the qualified query/reset/startup change.
Its six changed files use the same fixed alpha73/storage18 decisions in local
helpers; shared domains, compiler, profile, bootstrap and codec stay fixed.
The normal source closure has 17 files. Two independent source extractions,
each with two shipping/DEV builds, reproduce the complete new tuples. Four
actual wrapper sessions produce 16 legal GO results and settle naturally.
DEV source/native identities are newly generated and pinned; DEV engines are
not executed. No previous DEV identity is inherited. Final promotion index is
`af79c02bfca0450c23bd6ef5b4645e81b21614ffb208072045b2aa37ed05b375`.
The maintained file is **5,051 B**, source 10,477 B and native 22,672 B, with
whole SHA `ad4030ad32af47469ca067e4f10c4b60103eddcc6afdfefd22dedea1269052ce`.
Local reproduction and runtime qualification do not claim future-head CI success.

E5647 separately passes old/new optimized and sanitizer query/model checks,
five startup schedules, four actual GO epochs and two unchanged-verifier
wrapper sessions. Its exact model/search prefix remains source reuse; features
12/14 are not observed nonzero and the clamp is not exercised. The 59-file
proof summary is `e5141d5d714061101767d8c6f4b043990282a94011407c845f784e4ffa8228af`.
E remains 5,679 B in the maintained table pending a normal-producer change.

The C/E storage experiment preserves its original failed C string-Counter
comparison. A separate observer admits the exact suffix-sharing class and
checks allocated contents, headers, relocations and remaining byte gaps. Both
final native forms repeat. Two packages each measure **C5603/E5595**, saving
84 B each with the original codec. Strict decoding and AST source/argv binding
pass; candidate engines and normal-producer promotion remain unexecuted.
Its final 46-file cost summary is
`19940b30277a38afedd522eedc78480ec6b85c9448bd96a84e83a357609117ef`.

The user-supplied PR12 size analysis is reference evidence from another
environment. Its reported hashes, codec minima and full-native equality are
not treated as current reproduction. Work now tests independently implemented
function-local name reuse, fixed LZMA1 settings, Rust D's shipping node-accounting
path and D's internal context decoder. Fixed upstream ice4, 4ku, 4kc and STRO4K
sources and licenses are compared outside this repository. No upstream engine
source is vendored or used as a Rove4k build input. Policy differences such as
queen-only generation, twofold repetition and per-GO thread creation cannot
silently become equivalent source compression.

Two other fixed candidates keep distinct dispositions. A's merged castle
emission costs 4,959 B, down 21 B, with a new native and changed private move
order; its focused functional proof is a separate follow-up. B's first-ray
attacker merge shrinks shipping source 11 B but grows the complete file
12 B to 5,863 B. B is rejected before engine/runtime qualification. Existing
maintained A/B images stay selected. The B final summary is
`2dd665666a308b9586560af615815a362612d9442d99bd693d9f13023d5b8c2d`.
Two copied proof control files retain a pre-existing extra blank EOF line to
preserve their exact producing bytes; diff-check reports those whitespace
warnings. They are not functional test failures or silently normalized inputs.

## Fixed-codec reproduction and upstream source comparison

The [fixed-codec producer](../engines/experiments/tiny-source-codec/README.md)
first reproduces the original source/bootstrap/whole pins from `a3546f1` and a
separate ordinary F5051 source snapshot. It then measures one specified LZMA1
9-extreme configuration: lc2/lp0/pb0, BT4, 64-MiB dictionary, and nice lengths
A273/B32/C64/E32/F32. Complete costs include the 77-byte launcher, 13-byte ALONE
header and end bytes. They are observed costs, not sums of prior reductions.

| Fixed source | Original whole | Candidate whole | Saved |
| --- | ---: | ---: | ---: |
| a354 A | 4,980 | 4,980 | 0 |
| a354 B | 5,851 | 5,796 | 55 |
| a354 C | 5,687 | 5,624 | 63 |
| a354 E | 5,679 | 5,613 | 66 |
| a354 F | 5,083 | 5,032 | 51 |
| Separate F5051 | 5,051 | 5,003 | 48 |

Each original/candidate package repeats independently. Six real preprocessing
commands and 24 compression/strict-decode checks run; native/bootstrap/engine
executions are zero. Root separately reads all 54 ordinary source pins and the
six selected physical packages, then decodes each and checks exact bootstrap,
compiler argv and compiler-stdin bytes. This does not qualify future runtime.
XZ-to-ALONE removes CRC64 container checking; exact normal-byte recovery does
not preserve corruption detection. A was already ALONE and is byte-identical.
The other environment's codec-only minima are not relabeled as reproduced.
Final summary: `9856ce3abaeb3d30c9e5258d6600e03f04c952d3d9720d8a4d5e294cc0deb642`.

Comparison uses pinned original sources outside Git. The
[ice4 semantic analyzer](https://github.com/MinusKelvin/ice4/blob/2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19/minifier/semantic_analysis.rs)
and [renamer](https://github.com/MinusKelvin/ice4/blob/2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19/minifier/renamer.rs)
bind declarations/references and group nonconflicting names. Rove4k's new
independent experiment starts with AST-bound automatic locals and parameters,
unique names within each function and reuse between functions. Static/global,
member/type, macro and ABI spellings remain outside that initial policy.

The actual [4ku search](https://github.com/kz04px/4ku/blob/203ddd4bf9b331851c796d8b5d57eac08f6e6c18/src/main.cpp)
shares main/quiescence search and consumes only the remaining selection-sort
suffix. Its side-relative board and packed tapered evaluation differ from the
current A/F scalar model. A/B/F already share their recursive main/QS bodies;
that source does not reveal a duplicate full search body to delete here.
The [ice4 UCI path](https://github.com/MinusKelvin/ice4/blob/2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19/src/uci.cpp)
uses fixed-position clock parsing and joins per-GO workers before continuing
the input loop in its TCEC branch. These are different runtime policies.
Pinned ice4 actually uses an atomic eight-byte TT with a 16-bit tag and Lazy
SMP; it is not classified as a plain single-thread TT implementation. Its
search generates queen promotions and accepts one prior repetition match,
while replay underpromotions are a separate path. Pinned 4ku generates all
four promotions and uses a full-key plain 16-byte TT, default one thread and
per-GO jthreads. Its shared plain stop/TT does not establish Rove4k's coherent
publication contract. The comparison preserves Rove4k's full-key context,
third-occurrence rule, all promotions, B SEE/singular fences and F MTD witness.
The external comparison summary is
`ea5672341e0b73952e49b96ebeb3d3c9311dad46a1497554f6830ec163ad8056`.

The [4kc loader](https://github.com/GediminasMasaitis/4k-dot-c/blob/26e936860c8da80de73ea3041ccade96ba8112a3/loader.asm)
reads a 16-bit output bit count and overlaps executable code with an RWX ELF
header. A 32-bit context stream and guarded RW-to-RX restoration require a
separate Rove4k decoder/layout; a smaller payload alone is no complete own-ELF.
[STRO4K's build documentation](https://github.com/ONE-RANDOM-HUMAN/STRO4K/blob/51ea73a3d86141d96ad428402dc387722fc0f9b1/README.md)
separates its NASM 4K build from the Rust STRO development program. Its reported
4,092 bytes are not a reproduced Rust D result. External source/license bytes
remain outside the repository and are not linked or copied into these engines.

The separate [A castle proof](../engines/experiments/tiny-a-castle-proof/README.md)
runs old/new O2 and ASan/UBSan forms. Each checks 32 selected positions, 749
legal child states, 4,096 attack values and 14 replay states against an
independent oracle. Child sets/full states match; move order changes in 24
positions. Two depth-two castle searches retain score 1,028 and legal witnesses.
The actual 4,959-byte file passes two unchanged-verifier quit/EOF sessions with
its new native identity and no inherited DEV/runtime receipt. This is separate
qualification, not maintained promotion, strength or stack proof. Final proof:
`4396c9af4b5c0b7ea7ee9f68c1333e48925cd6974ce9ecd1035ae68ca6214d0a`.

The [D TT payload-lock experiment](../engines/experiments/tiny-d-tt-payload-lock/README.md)
uses payload bit 63 for slot ownership and preserves full keys. All eight
control/candidate native builds complete. Candidate scalar/HQ native lengths
tie at 8,092/8,480 B, with text +5 B, BSS +4 B and source +197 B. Static
disassembly/ABI dataflow shows Entry24-to-16 and TT request 6-to-4 MiB for the
same slot count; this is not runtime RAM measurement. The original exact-image
packer rejects the new identities. No candidate whole, loader/codec, engine or
DEV qualification runs, and the candidate stays unselected. Final index:
`2c65f9c96e35a767156f7547fa0f3cce25fe25a64469476099cc594ddca079a3`.

## Declaration-bound names and maintained F4839

The [independent AST experiment](../engines/experiments/tiny-scope-names/README.md)
implements function-wide automatic-local/parameter names, restarting the alias
pool between functions. Physical declaration/reference offsets, main-file
declaration and macro ordinals, exact macro-body token signatures, opaque/macro
exclusions, inverse source recovery and reparse binding graphs form its source
checks. It uses external libclang and real resource headers, not copied ice4
implementation. Ten focused fixtures cover capture, initializer shadowing,
macro targets/body changes, static/member/string preservation and asm exclusion.

| Original-codec source | New source | Actual whole | Saved whole | Complete old native |
| --- | ---: | ---: | ---: | --- |
| A4980 | 9,910 | 4,846 | 134 | exact |
| B5851 | 12,485 | 5,659 | 192 | exact |
| C5687 | 11,704 | 5,507 | 180 | exact |
| E5679 | 12,093 | 5,515 | 164 | exact |
| F5051 | 10,011 | 4,891 | 160 | exact, twice |

Two B preparations stop before native compilation: moved macro source offsets
first break external-USR identity; the ordinal retry exposes undefined libclang
declaration attributes queried on a preprocessing cursor. The final producer
uses stable macro ordinal/body/use identities and preserves every edge. It does
not ignore the mismatches. F/A/C/E executed snapshots and both B failures remain
outside Git. The final ordinary experiment has seven source files; final summary
is `f185a2c2fcff2dab9c8607a7b2776bf0d75e8f66137c6e292b6bbe127b976785`.
This v2 index corrects one historical fixture path; source and artifact bytes
are unchanged and the original inventory remains preserved.
There are six actual native compiles and no engine executions in this experiment.

F's actual name-plus-codec composition is **4,839 B**, down 212 from F5051.
It is 77 B launcher plus 4,762 B ALONE stream. Two independent whole files and
strict source/argv recovery match. The 160-B name saving plus standalone 48-B
codec saving is not added; actual combined saving is 212 B. Composition receipt:
`83a25431528e48b503afa4f146b90d1fde9f3fb36c9d2d1dd790926fb0784694`.

The normal F source producer now replays that exact declaration-bound map in
`shipping_scope.py`, admitted only for the complete post-storage input hash and
each physical occurrence, with exact inverse/output checks. No libclang or
external reference source is needed by the maintained 18-file closure. Canonical
engine, compiler, DEV and full native bytes stay fixed; transport changes from
XZ/CRC64 to fixed ALONE/no checksum. Normal shipping and DEV tuples reproduce
twice, and the unchanged verifier runs the new file in two quit/EOF sessions,
producing eight legal results with exact restored native, three startup TIDs,
private-path cleanup, reader EOF and physical exit. Normal build/runtime receipts:
`3802290d2aa8beb3ce464b98ccedea93efeda9afbe430528f4792ff8b3e72ea6` /
`bd4803e0d6c16cf52086d65ac38b0e72fcf26dfca52ead045832b9bd0a407080`.
Producing recipe is preserved before a qualification-metadata-only update.
FD012 is not newly observed by F's verifier; cancellation causality is unproven.

The [C/E core composition](../engines/experiments/tiny-ce-core-size/README.md)
removes C's zero ordering function, consumed selection-prefix writes and the
separate TT write argument. All production writes have bound 1..3 in bits41..42,
so payload is nonzero even for zero move/score/depth. E's real ordering remains.
Twenty-nine selection cases and 189 payload boundaries pass. One control and
one candidate per family cost **C5643/E5655**, down 44/24. Candidate native code
differs and grows 32 B; runtime/repeat/normal qualification has not run. Clamps,
model/AVX2 and other source complements stay fixed. The failed raw `-dM` order
check is preserved; complete definition multiset comparison corrects that
unordered-output assumption. Final receipt:
`e466ab69e833bd5410e6a845f26474babedf0e6d9622898d8a5a2d815f22aadb`.

The fixed external 4kc codec is also actually reproduced: scalar/HQ streams
5,028/5,243 B restore the exact current native through decode and inverse BCJ.
The reference C reader is not bounded at input end, so separate decode inputs
include four actual zero bytes while original payloads are preserved. A new
independent bounded u32/software-CRC decoder and guarded complete ELF first-cost
are in progress. No new complete D result or decoder cost is inferred from the
payload. External reproduction index:
`5af5628f200c3eafe772f320ed751d3f3b7455f9f272aea8712a09d4bcc51ed0`.

The new independent bounded decoder then passes one diagnostic build and two
guarded valid-stream calls, recovering exact BCJ output bytes. A separate
first-cost builds two actual own-ELFs: **scalar6401/HQ6614**, saving 1,056/1,093
from maintained D7457/7707. Actual total is 176-B ELF/PHDR + 1,191-B text + 29-B
u32/model header + 5,001/5,214-B arithmetic body + four real tail bytes; no extra
rodata/padding is omitted. The 1,367-B nonpayload cost is measured rather than
reusing the old 1,115 B. New complete D files are not executed or runtime
qualified, and the encoder is an explicit external-data first-cost producer,
not a closed maintained source encoder. Cost receipt:
`432ec934af089db4d23edf4c3b269ee5e86941634aeb77e88f037c96f232f7a9`.

## Normal A/B/C/E names and separate runtime follow-ups

Normal A now replays its 70-declaration/274-occurrence map, retaining original
ALONE, compiler, canonical engine, complete native and DEV bytes. The maintained
file is **4,846 B**, down 134 B. Shipping and DEV each reproduce twice, and two
unchanged-verifier quit/EOF sessions produce eight legal results. All four owned
files and the 19-file ordinary source closure are frozen; no libclang or
experimental input is required by normal generation. Final promotion summary:
`39310589b4e16d23b82a32fd19839a941ed1f0f7a0b1779d7330a905bc9f032c`.

The static-function experiment first admits only real owned static function
declarations/direct references, excluding address-taken workers, constructors,
macros, external ABI and name observers. Each actual candidate retains all
PHDR/allocated code/data/dynamic/relocation bytes except the exact GNU build-ID
descriptor; e_shoff and nonallocated symbol/string/section metadata also change.
Full-native equality to the maintained predecessor is false. Automatic names
on top reproduce those new static-only natives exactly. Actual combined codec
cost is measured on the resulting source, not added from separate savings:

| Family | Final C | Combined original XZ | Fixed ALONE | Saved from maintained predecessor |
| --- | ---: | ---: | ---: | ---: |
| B | 12,220 | 5,619 | 5,558 | 293 |
| C | 11,455 | 5,459 | 5,395 | 292 |
| E | 11,803 | 5,455 | 5,400 | 279 |

Normal B/C/E now use two exact position-bound replay stages and fixed ALONE.
Each shipping/DEV tuple reproduces twice; each unchanged verifier runs two new
quit/EOF wrapper sessions. The combined 15-file change preserves all canonical,
DEV, bootstrap, shared policy and verifier inputs. Normal closures have 19/19/18
files. There is no Clang, report, upstream engine or experimental source normal
dependency. A stale early C XZ-format check stops one CLI before output/compiler;
it is corrected consistently for C/E and the failed preparation is preserved.
Final promotion summary:
`8280977aa06c274444984dacc1dfab077515eacf1e4a9d1efa687b27418f5bf6`.
An independent read-only source review is clear. These are local normal results;
CI is reported only for the actual later committed head.

The separate B source-sharing candidate costs 5,843 B, saving only eight despite
161 B less shipping C. It shares old/new put updates and exact clock-token
consumption, and forwards continuation piece context. New native code differs;
engine/runtime/repeat qualification is zero. It is not combined with names or
selected over B5558. Summary:
`6faacbe5e5bb85f75287c7e1a7cd651b0cc05c5ab141fa49938e7127580ac6a7`.

The Rust D explicit shipping-node-budget specialization preserves parser,
stop/newgame/infinite/bare-GO policy, local deadline/result counts and correction
epochs. Focused default/DEV/node/deadline fixtures pass, but complete scalar/HQ
costs **11,404/11,770 B**, up 1/8 B. Native length ties at 16,816 B while RX
grows 16 B. The sole candidate is size-rejected without production ELF execution
or more variants. Final handoff:
`69c7d84fe16bda6b8380123fc81acc2fbaa0c10a181ca020f93a8bd44040672b`.

The D context whole then passes four actual scalar/HQ quit/EOF sessions, with
12 independently legal results, exact restored native RX and padding, guards,
three persistent TIDs, stdio-only FDs, absent children, reader EOF and physical
group settlement. The adapter admits only the two new whole hashes and exact
old native/layout/helper inputs, leaving the old verifier main/EXPECTED intact.
At eight map observations no RW interval of at least 32 MiB appears in this
local profile; context-address/munmap causality and CHECKPOINT initial BSS are
not inferred. New RIE/ptrace negative tests are zero. Actual runtime receipt:
`dad61bc39bc3ee777fcbef79081a78a786f7fdeb8e27990c3cd510ccd1d3bc82`.

An independent standard-library Python fixed-model encoder also restores three
small fixtures and both exact native inputs through the existing guarded C
diagnostic. Its two isolated CLI encodes happen to reproduce the complete
5034/5247-byte payloads, without an upstream program or model search. Exact old
payload matching is a comparison rather than a forced termination-bit rule.
Encoder receipt:
`705e720ea01d5eb1f4254c6a8cda646e323d67bf9ffcc4653cb27841bae33b66`.
Closing the maintained D source encoder/audit consumers remains separate work.

## Exact F member names and an incomplete lexical experiment

The exact-F owned-member map renames 13 fields at 57 physical declaration/use
positions, reducing post-scope source from 10,011 to 9,954 B. Independent Clang
reparse preserves the complete 2,463-edge reference graph, all other physical
tokens and all 22 fields' order, types, qualifiers, offsets, sizes and alignments.
The atomic-macro field zb.zN and all external/header members remain protected.
The source-only proof and a separate read-only review are frozen; source saving
alone is not treated as packed saving.

One exact candidate native is then byte-identical to the maintained 22,672 B
native, with no metadata exception. One fixed ALONE package costs **4,814 B**,
down 25 B from F4839. Normal F now replays that map as a second stage in the
existing helper; the original 98-declaration/451-position automatic map stays
byte-identical. Canonical, DEV, bootstrap, compiler, launcher and resources stay
fixed. No Clang, experimental source or receipt is needed for normal generation.

Normal shipping and DEV each reproduce twice. The unchanged verifier passes
two actual quit/EOF sessions and eight legal results against the new wrapper.
Whole SHA is `30240a27c0682519b1d2539c58d153ebaf7dcf4b9d9dde631f985f3c27261285`;
source SHA is `00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916`.
Normal build/runtime receipts are
`522f9c565914bf1fda1cd74cbb7e5133c6e74bdf90198fa4f26d1dbff222e26f` /
`acbde1bf6f0438cb0f16502d1b4a9cc28951d9309333e4e28845841c4eea1e12`.
The independent first-cost receipt is
`2b2eb28b291d10f913e00d78d9eff398608f80fa66785ae6ee3eec08ce43873a`.

The separate lexical alias prototype remains **incomplete and unselected**.
Its first run aborts on an unclassified parameter-redefinition diagnostic;
the second aborts on an unclassified tentative-shadowing int-to-Move-pointer
diagnostic. Both failures and their original incomplete checkpoints remain
preserved. The last checkpoint processes only 20/98 declarations and 56 greedy
trials. A separate final two-parse validation admits its exact forward/inverse,
protected declaration shapes and observed reference projection, without changing
those failed runs into success. Its 10,011 B source changes only two aliases at
four tokens and saves zero raw bytes; native, codec and engine execution remain
zero. Final handoff: `1f57db2fcdb5ef340763889bd9b6d7d41eb81a5153e58a049dc7f6b2c74345b9`.

## Maintained D context producer and fresh pre-entry qualification

Normal D now generates its own fixed H24/base10/u32 context packets from the
eight unchanged native sources. The exact independently authored encoder,
range module, fixed models and decoder are ordinary local source inputs. All
native/loader pins are checked, and the 17 producer inputs are copied before
importing the encoder.
There is no upstream compressor, historical packet, external artifact or
experimental-source dependency in normal generation. The original two native
images, compiler/link flags, resources, native admission and physical verifier
helper bodies remain unchanged.

The maintained complete own-ELFs are **6,401 / 6,614 B**, saving 1,056/1,093 B
from D7457/7707. Their exact shipping hashes remain those of the separately
qualified context experiment. All 1,367 B of headers/loader plus packet framing
and real zero tail are counted. Initial discovery compiles shipping twice and
the two new CHECKPOINT variants once each, without executing them. The actual
audit files are 6,424/6,637 B, with hashes
`07f0a624c85bec6a716cf40a738d6a455c555d6ea230528a4c531ae9d084b59f` /
`854595138f823be31da5d189161ed7e7e802ee8f5dc836c7c534949f9dea3a6f`.
They are explicitly admitted only after source and physical ELF review; no old
decoder audit identity is reused. CHECKPOINT stops after checked context unmap,
inverse BCJ and final RX/BSS protection, immediately before native entry.

The unchanged fresh contract then passes on two independent extractions of
exactly 23 ordinary archive members: local21 plus oracle/LICENSE. Actual native,
whole and audit bytes match across extractions and repeated generation. This
runs eight native, eight shipping-loader and four audit-loader compilations,
then eight actual shipping quit/EOF sessions and four positive pre-entry audits.
Each audit observes the exact restored RX, zero RX padding and rounded initial
BSS, guards and permissions, then resumes the original entry and exits cleanly.
No forced cleanup, errors, retries, RIE/ptrace mutations, games or benchmarks
are introduced. This qualifies the new context path separately from old fault
receipts and from the earlier production-only adapter.

The producing source21 set is
`f32b345cdc1f5b031130dcfe8ca52a5778f310a132af772e7d2208e6390be5e0`.
The source archive is
`4a05643884df255f56e16e50da70c10cb9536b3af1ff7b316a7bf30be924e09f`.
Fresh result/readback receipts are
`3e8ab7c220c5ed26da56dde77fa5b086d4f5f8165518181a10b7676f7611e35b` /
`26ced4a9aa2bdec75f1f16c7018401eec289d0b44b33eda95d59b86c2a098776`.
Post-run qualification metadata is distinguished from these producing inputs.
Current-head CI and 4 KiB eligibility are still separate acceptance conditions.

## Further source sharing: first costs, not maintained entries

The next bounded experiments keep the maintained `e266ea5` sources and exact
admission guards unchanged. Each row below is one physically generated complete
file, including its original launcher or ELF header/loader. Independent gains
are not added together.

| Exact candidate | Maintained whole | Candidate whole | Change |
| --- | ---: | ---: | ---: |
| A local own-side piece expressions | 4,846 | 4,853 | +7; rejected |
| F guarded TT-bound predicate | 4,814 | 4,811 | -3 |
| F EP legality through existing make | 4,814 | 4,808 | -6 |
| F EP plus bound predicate | 4,814 | 4,808 | -6; ties EP alone |
| F shared GO field parsing | 4,814 | 4,812 | -2; separate unqualified candidate |
| F full-key 16-byte CMPXCHG16B TT | 4,814 | 4,862 | +48; rejected |
| D worker-owned reset, scalar | 6,401 | 6,387 | -14 |
| D worker-owned reset, HQ | 6,614 | 6,580 | -34 |
| D reset plus fixed-width inverse BCJ, scalar | 6,401 | 6,313 | -88 |
| D reset plus fixed-width inverse BCJ, HQ | 6,614 | 6,506 | -108 |

F's predicate retains the outer nonzero-bound gate. Its eight decoded-bound /
score-relation truth rows agree even though the isolated inner expression
differs for bound zero. Only nine shipping-source bytes change. The EP candidate
shares the three-square board edit and own-king legality check through `make`.
Its trial child is discarded; a temporarily noncanonical scratch hash cannot
escape to TT, history or results. Its inner EP immediately returns because the
trial capture cannot create a double-push target. Both candidates produce new
native identities and retain separate functional qualification requirements.
The guarded-predicate cost receipt is
`187fd808c759720d23f4777d164d659f05c0a141955612674ff7f21de2777f04`;
the EP cost receipt is
`c59a93ae67cce82b0accac9d743099d663b264d4c1af49402f01afc7a5d816cb`.
One actual combination of those two transformations costs the same 4,808 bytes
as EP alone, despite its 9,916-byte source being nine bytes shorter. It is not
selected over the simpler EP-only candidate. Its separate new native and whole
identities are retained in external receipt
`a1eea975549fb09481cd72ba500f41d2163faf99960b972a0836f6f786c8389c`.

The CAS16 experiment preserves all 64 key bits and all payload bits in a single
coherent operation. It changes contention policy: reads obtain a coherent
snapshot and a failed single store attempt drops its update. Inline codegen and
the added `-mcx16` bootstrap are included in the cost. The first checker wrongly
expected two static CAS instruction sites; the original failure is preserved.
An explicit read-only admission identifies three legitimate sites (read
snapshot, write snapshot, conditional write), reuses the unchanged native, and
allows the sole package measurement. The larger complete file rejects this
candidate without runtime or additional flag/codec variants. The 24-to-16-byte
entry reduction is allocation arithmetic, not a measured RSS or file saving.

D removes the controller's duplicated all-worker result-reset loop. Each worker
clears its own best move immediately before the unchanged `think` reset of
nodes, depth and score. Epoch publication, completion/output reservation and
storage-reuse ownership remain explicit. Scalar/HQ natives shrink by 32 bytes
each to 8,060/8,448; their distinct compressed savings are measured, not inferred
from native lengths. The fixed context packets cost 5,020/5,213 bytes, with the
same 1,367 bytes of ELF header and loader. The first whole-cost receipt is
`c89c7ec1a595ded61c11844352e80f244149eb29088eaa62b3ec6499ce9d2063`.
New-code runtime and pre-entry qualification are not inherited from the former
native identities.

The separate adjacent-declaration inventory finds only two conservative plain
`int ` joins in the exact F source: eight raw duplicate-prefix bytes. No changed
C, native or package is generated for that lane. Its independent policy review
is clear for those two positions, without a general GNU-extension or typedef
chain claim. The inventory is closed without treating its arithmetic target as
a realized saving. Scope coloring remains the earlier incomplete experiment.

A separate source review traces pinned 4ku's side-relative bitboards and
recomputed hash/evaluation, and ice4's absolute board plus direction/sign
parameters. They do not establish a large drop from physically flipping the
current A/F board. The earlier complete flip already grows by 32 bytes. One
smaller six-expression A candidate keeps absolute board/key/move domains and
normalizes only local mover values. Its shipping source shrinks 19 bytes, but
one actual package grows by seven bytes to 4,853. It is size-rejected without
runtime or F variants. The new native differs despite tying in file length.
Its actual first-cost receipt is
`0674ab007661efee495abb350bbac896697cf4691f809b9a32f67671252d9131`.

All compiler outputs, complete files, source snapshots, receipts and external
engine comparisons stay outside Git. Only independently authored experiment
sources are committed. No third-party engine implementation is vendored; no
games, training, AWS or target many-core benchmark is part of these costs.

The EP-only candidate subsequently passes one diagnostic fixture with 16 EP
roots, 106 full real-child states and three replays against the independent
board oracle, then both actual 4,808-byte shipping quit/EOF sessions with eight
legal results. The diagnostic uses the same readable EP change, without a
substituted search or function-instrumentation observer. Existing-image
disassembly shows the local EP attack chain growing by 256 stack bytes from
432 to 688; search's own 4,432-byte frame stays unchanged. Bounded recursion is
source-proven, while final-target stack and speed claims remain unmeasured.
Actual selected-wrapper runtime receipt is
`53f620c73bec830835374c5662373b4492dabb695497782ad80aeaff0695b745`.

The reset-only D images subsequently pass four actual production sessions
(12 GO epochs) and two existing output-publication cases (four GO epochs).
The latter observe pending=1 while the old result write is blocked and the
controller waits, then legal ordered old/new-root results and pending=0. Both
forms preserve the restored native identity, RX/BSS permissions, guards,
persistent TIDs, stdio-only descriptors and natural exit/readers. This is
post-entry ownership evidence, not initial-BSS or pre-entry audit evidence;
cancellation causality stays unproven. No substituted search, target writes,
fault campaign, compiler or codec is added. Actual receipt is
`bb01f2daf8960b73a2cb81b51776249d0ac25b5aca98c1d1f2754953d4894476`.

The further D BCJ candidate replaces only byte gather/scatter with two
four-byte `__builtin_memcpy` expressions on the fixed AMD64 little-endian
target. Actual codegen is one unaligned 32-bit memory add, with the same
opcode test, bounds, modulo subtraction and five-byte skip; no copy helper
or new dependency appears. Two loader compilations reuse the exact reset
native/packet pair, without native compilation, encoding or target execution.
Loader text falls from 1,191 to 1,117 bytes; all 176 ELF/PHDR bytes are counted,
so total nonpacket cost is 1,293 and complete costs are 6,313/6,506. The source
literal inverse and independent codegen review pass. This is an actual reset
plus BCJ composition; new-loader restoration qualification remains separate.
Cost receipt:
`86679cee87d5ac07b574b5da82c0edc65756e6fbbeddf53c1cd7ef90fc6dbb3c`.

One standalone F GO-parser candidate also shares time/increment token parsing
while retaining both assignments inside the own-side condition. Exact token
consumption, number parsing and last-value policies are source-reviewed. Its
source shrinks 58 bytes but whole only two, to 4,812; native identity changes.
It is not combined with EP and receives no parser-runtime or normal-promotion
claim. Cost receipt:
`cc40b3ba82fe6961328c52e2a01750954a99acc550ae753735bc8117dad907f5`.

## Maintained EP-only F and worker-reset/BCJ D

The selected normal F pipeline now applies EP source sharing from ordinary
`shipping_semantics.py`. Its readable body is the semantic source for both
DEV-before-specialization and shipping-after-members. The old engine base and
all alpha/storage/scope/member guards stay byte-identical. The fixed helper
checks each exact source identity, readable/shipping role relation, literal
occurrence, protected complement and inverse. Normal generation imports no
experiment or historical artifact. Its fresh archive closure includes the
helper through the existing recipe helper list.

Normal shipping source/native/whole/bootstrap reproduce twice at
9,925/22,672/4,808/10,924 bytes. The newly identified DEV source/native also
reproduce twice at 19,488/26,984 bytes; they are not labeled equal to old DEV.
The unchanged selected-wrapper verifier passes two actual quit/EOF sessions
and eight legal results on the normal 4,808-byte file. Source/native/whole
hashes are
`3549063cbdca22c83536e0879b5e7baff8c7cbef3b5911f4152850732c86300c` /
`9b4ca00fd54b67c33c01e92389c4f9130751233633faa828b6eb46e3b20890db` /
`93377e104d934d5bde1e8c7a491b54b72d0a7a6e9d40b845f94f86bc0c2f6956`.
The actual normal build/runtime receipts are
`0fc04401edd284fe072f2ff43d1c2489713944b1b44a06345f3e91d77e676777` /
`49e6a6ed062667ca94fdc338ab6a73a2f3fb71a14cd71cb46328eda6c5c2a18d`.
This selects EP alone: the bound-expression combination ties in whole cost,
and the GO-field experiment is not silently composed with it.

Normal D now owns both the worker-reset runtime and the fixed-width BCJ loader.
Only those two runtime bodies change. Exact native admission is updated to the
new 8,060/8,448-byte pair, with its literal entry and private mapping geometry.
Encoder, range math, fixed models, decoder, linker, flags, profile and other
seven native sources remain unchanged. Packets and shipping whole identities
match the actual independently measured reset/BCJ composition. No external
program or experiment is required by normal generation or runtime restoration.

The new audit files are discovered without target execution, then statically
reviewed and explicitly admitted: scalar 6,336 bytes with SHA
`93df62352f49aee0d01e4022c6a7acc773593255dfa252c28a200d3e521df905`;
HQ 6,529 bytes with SHA
`9bf7165d3840488c9cdd674caa2e7cb2379c6d6eed917005cd8ce2d48129a8fd`.
The source CHECKPOINT still follows checked context unmap, inverse BCJ and
RX/BSS protection, immediately before native entry. Old audit identities are
not reused and the physical verifier helper bodies stay unchanged.

The existing fresh contract passes once on two independent extractions of the
same 23-member ordinary archive. It actually runs eight native, eight shipping
loader and four audit loader compilations; eight shipping sessions with 24 GO
epochs and four positive pre-entry audits pass. Exact native RX, zero mapping
padding and rounded initial BSS, guards, NX permissions, original entry resume,
readers and natural group exit are observed. No forced cleanup, target writes,
new fault campaign or retry occurs. A readback-only tool-schema mistake is
preserved separately; correcting that observer does not rerun or relabel the
completed fresh execution.

The producing source archive is
`f8a86aca8e0632d34f10d9a99d53b9ad6382e76420264853158b1b899ae010c6`;
the actual fresh receipt is
`e4838c7aeed82688983244a1fb91f85c570e35a51433570015f20d4d2aa20c0c`.
The complete shipping files are 6,313/6,506 bytes with SHA
`66f70074da2270f1d6aa33beb50c1f34038b4bc36e4272d748c1720935fb4a9a` /
`7ba4858dcf40c837d107f865e14b82d19ede40570059dcff1ca4bd3012ff7234`.
Post-run README/qualification metadata is distinguished from producing inputs.
These normal local results are separate from the next exact-head CI, final
resource/profile, strength and 4 KiB acceptance conditions. No family is yet
size-eligible, and all twelve independent cores remain in scope.

## Further source compression after the EP/BCJ promotion

The next isolated candidates start from committed `9e2a152`, rather than the
attachment's older `a3546f1` baseline. Their measured savings are not added to
earlier standalone experiments. First-cost recipes were kept separate until
source generation and focused functional validation completed; the later
normal-promotion section records the resulting maintained entries.

| Candidate | Maintained whole | Actual candidate whole | Difference | Current evidence |
| --- | ---: | ---: | ---: | --- |
| A shipping text profile | 4,846 | 4,766 | -80 | Focused input, normal reproduction and actual wrapper pass |
| B incoming-move SEE | 5,558 | 5,546 | -12 | Focused SEE, normal reproduction and actual wrapper pass |
| C structural composition | 5,395 | 5,344 | -51 | Focused TT/sort/eval, normal reproduction and actual wrapper pass |
| D scalar residual leapers | 6,313 | 6,272 | -41 | Focused board/oracle and normal fresh/runtime/pre-entry pass |
| D HQ residual leapers | 6,506 | 6,452 | -54 | Same focused and normal fresh scope |
| E structural composition | 5,400 | 5,366 | -34 | Focused TT/sort/eval, normal reproduction and actual wrapper pass |
| F shipping text profile | 4,808 | 4,735 | -73 | Focused input, normal reproduction and actual wrapper pass |

The F candidate shares the own-side clock classifier, uses bounded `strtoull`
admission and replaces the byte reader with a bounded text-line loop. Clock
fields remain order independent; absence and an explicit zero retain different
budget meanings. It explicitly selects NUL-free text and exact first command
tokens, so malformed extras and leading whitespace are a changed input policy,
not universal parser equivalence. Search, TT, MTD bounds, worker publication
and physical output ownership are outside the changed source regions. The
compiled 9,728-byte shipping source and 18,576-byte native have new identities.
The initial readable DEV wrapper has a missing directive newline; that separate
uncompiled representation is preserved as a failed preparation and cannot be
used as normal-generation evidence. A boundary-only producer correction now
creates readable `fe1309f3...` and exactly the same compiled shipping source;
it adds no compiler or codec run and does not yet establish DEV generation.

The D candidate preserves slider handling and specializes only its residual
pawn/knight/king path. The old inner ray always stopped after its first square
on this admitted piece domain. Attack-before-friendly filtering, direction and
promotion order, EP and castle paths remain explicit proof obligations. Native
size falls 96 bytes in each form; BSS, guards, NX and the existing two/three-page
RX layout classes pass static checks. The actual first-cost receipt is
`96e7eda66d500b312e93f47b42fe55896f8f0f10bbf14ebfd8da6b84b14bc443`.

C/E sentinel, consumed-prefix, inactive-clamp and C zero-order changes have
now been measured with the current names and codec. The actual 5,344/5,366-byte
files save 51/34 bytes, rather than the sum of old standalone measurements.
Native images each grow 24 bytes and have new code identities; no metadata
exception is used. C still contains actual AVX2 gather and horizontal-add
instructions, and E retains all 21 coefficients and its inner clamp. The cost
receipt is `69b2553811f983744e9a0a33e5e9590076a983c472ffa5c4db4358844879d689`.
Focused fixtures and selected wrapper checks remain separate from this cost.
A separate B proposal shares initial and recursive SEE move/gain
ownership while preserving full legal minimax and incomplete-result fences;
its initial 84-byte code projection was not a shipping or whole-size result.
The sole actual candidate now saves 72 bytes of final C, 32 bytes of native and
12 bytes of whole, yielding 5,546 bytes with SHA
`70e5ea64a97efaa84385a429bca84bad2924a5256c478973cc2798a4b070ad2f`.
It changes the recursive helper's internal return meaning to incoming move net
gain; the full legal recapture tree, all promotion choices, incomplete fence,
singular policy and excluded-root learning/TT rules remain explicit obligations.
No LVA approximation or playing-strength claim is substituted for them.

The same fixed text policy is independently ported to A's actual source/name
domain. Its 9,713-byte source and 4,766-byte whole are measured with A's own
original ALONE preset; F's nice32 setting and 73-byte saving are not reused.
The new 22,672-byte native has SHA
`28260858a130711bb5fa70816e950b7666440168e8835bb4802b98675b972422`;
the actual whole is
`8a783ff2d0f5d3546e54dba3d8c4c5931ba9b72c95270deca69eeabd33136226`.
This first-cost uses one compiler and one compression, with no control rebuild
or runtime qualification. A's focused validation follows separately.

The next focused checks pass on the actual changed source, with original
failures and first-cost producers preserved. B's single fixture covers 38
score/visit rows plus seeded visit-limit, cancellation and expired-deadline
cases; these are not million-node searches. Its search/TT/singular/learning
caller bytes remain exact, and its actual wrapper passes two quit/EOF sessions
with eight GO epochs. New recursion stack capacity is not qualified. Proof:
`fbdca8c590e7dabaf6d21d0e1b49cb075f5abfc9f86e291ad76da8cda1230421`.

C/E each pass 26 TT, 29 sort-suffix and 39 admitted-board cases in one compiled
fixture. C additionally checks 768 piece-square pairs against scalar/AVX2;
E checks all coefficients and 938 ordering values. Two nonadmitted E clipping
examples are labeled separately. Four actual wrapper sessions produce 16 GO
epochs with exact new process images and natural quit/EOF settlement. D's two
compiled fixtures each pass 12 roots, 177 full board records and 22,656 attack
queries against an independent oracle; scalar/HQ raw states and move order
match. Its shipping execution and new pre-entry audit are still pending.

F's one compiled fixture passes 25 numeric, 26 GO, 25 transaction, six special
root and 96 full-child checks. Its workerless manual publication setup does
not prove physical SMP. That evidence comes separately from the unchanged
verifier's two actual sessions/eight GO and one actual text-only session.
The latter observes LF-before-length 32,767 admission, 32,768 draining, CR's
contribution to the CRLF boundary, final EOF and exact command-token policy.
The functional/runtime/text receipts are
`5311a603eef2910af95582d4e8db155ac02f4bb41a49bee5c023fd07a1442113` /
`cb93679523bc078b7554a5f99bcf2ff47cf40e5588618d86540cb5bddbad53fd` /
`f55ce1a122c83fab585461910d4f7ce3cc67be8d78fd82ddb4409ac046760491`.
Natural physical settlement does not establish cancellation causality.

## Maintained text, SEE, C/E core and D leaper specializations

All six measured source changes above now pass their normal local generation
and selected-file checks. The maintained table near the beginning reflects
4,766 / 5,546 / 5,344 / 6,272–6,452 / 5,366 / 4,735 bytes. Each cost is the
actual complete file at its unchanged family codec settings; independent
standalone savings are not summed. No family is yet within 4,096 bytes.

A/B/C/E/F each run their ordinary builder once, reproducing shipping and DEV
twice. All five DEV tuples are compared with their prior full source/native
identities and match. Each unchanged normal verifier then runs its actual new
whole file for quit/EOF sessions and eight legal GO epochs: ten sessions and
40 GO in total. The newly added ordinary helpers are recipe-pinned and need no
experiment, historical artifact, upstream engine or Clang installation. Their
ordinary closures are A20/B20/C20/E19/F20; fresh extraction is not run for these
five in this checkpoint.

B/C/E apply exact production-domain source transformations only after their
unchanged spelling/scope guards. Original readable and diagnostic APIs remain
available for their broader domains. A/F additionally feed corrected dual
readable input into DEV specialization, where the original diagnostic branches
are selected; their original canonical bytes still reach every old shipping
guard. A/F text policy counts CR among the 32,767 bytes before LF, preserves
order-independent clocks and explicitly selects its documented malformed-input
behavior. This is source-level specialization, not a native-byte rewrite.

The normal A build/runtime receipts are
`b53178618951654aa0ab9bd1d5413162eff6a0de8178b9fc083af2d3b12e09a9` /
`822bf19b4c150ca784bed9272399f9d0ef03de4a58f2da428798e1e98c9309d0`.
Its focused fixture and three actual wrapper sessions pass the same explicitly
bound input policy on A's own code and new native. The normal B receipts are
`f43079a91203007704789a62bdaa5e73403af9153870427c4e3d56588e35a069` /
`3554ba9a0a05d6d34453f5c7ae75cbe580101bd6820ba7c64bbbf12b08bc642d`.
C/E's combined normal receipt is
`f20d8f40bdb099af8a359f24a4b3f5c387f0550c16bd7438a0dd84ee8239a05a`;
their final summary is
`eeb670a30cd6d429a4f0788df232d803adebb1b91c4e72af0d9ca470c1323e81`.
The normal F build/runtime receipts are
`dd8d4d81057cb5352b51831eca446b6d43716027873442e785a419e8bddc79af` /
`b837a43829868645ac82e6f158c41247380f2d761df2eb5687858fc7bfbf2eeb`.
The new shipping native identities are explicit; old metadata-only or stack
observations are not extended to the changed code. Final recipe qualification
metadata and README results are kept separate from the exact producing files.

D changes its readable board walker itself. Seven other native inputs and all
encoder, model, decoder, loader, linker, flags, resources and observer bodies
remain unchanged. Two new CHECKPOINT files are discovered without execution,
then their exact bytes and layout are independently read before admission:
scalar 6,295 bytes / `ce72966846e52a7f72d49c577ad9eb799fd81b195308b5e02def39cf84526b8f`;
HQ 6,475 bytes / `3660dc07190104f062fabe57e2f0603df21d94d47aa9c41cb487204f2a4f4547`.
The unchanged fresh contract passes on two independent 23-member ordinary
source extractions. Eight native, eight shipping-loader and four audit-loader
compilations reproduce the new identities; eight shipping sessions/24 GO and
four positive pre-entry audits pass. Exact restored RX, RX padding, rounded
initial BSS zero, guards/NX, original entry resume, stable workers, readers and
natural exit are observed. There is no target mutation or negative campaign.
Actual fresh receipt:
`3a32b4420c299c2f826cf90d7c8760578e275abb7da16179dc5c00936a2c82c5`.

The shared experimental-source head `72d5e70` passes both C/Rust jobs in
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39426741555) and
[repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39426741244).
That run exercises the preceding selected recipes. CI of the later normal
promotion is reported separately for its committed SHA in the draft PR. Final resources,
target hardware/scaling, remaining size gaps and strength validation remain
open across the complete independent C/Rust portfolio.

## Maintained C residual-vector evaluator

The following C-only checkpoint changes the maintained complete file from
5,344 to **5,245 bytes**, a measured 99-byte reduction at the same compiler,
profile, bootstrap and ALONE settings. Shipping C falls from 11,284 to 11,086
bytes and native ELF from 26,408 to 26,376 bytes. The other five maintained
families remain at the preceding table values. C is still 1,149 bytes over
4,096; all six family size gates remain open.

The shipping evaluator replaces the 13x64 table, its constructor and gather
leaf with sixteen local signed-16 features. Each color contributes six piece
counts, its own-perspective positional residual and one zero lane. Weights
are the original material values plus residual weight one, with opposite
signs for black. Residual is sign(piece)*value(piece,square)-material(kind),
including the negative king-center coefficient. It is not abs(value).
Within the admitted sixteen-pieces-per-color domain, residual prefixes are
bounded by 1,008, counts by 16, and the signed dot/reduction uses 32-bit sums.
The conservative raw HCE bound remains 29,120.

An actual YMM `vpmaddwd`, extraction and horizontal reduction feed the side
multiply, search evaluation and QS comparison in the new native. Both vector
halves carry evaluation data. This is a new full native identity, not a dummy
SIMD operation or a metadata-only exception. Board/put/make/hash/context,
capture ordering, TT and search remain outside the changed source fragment.
Speed, strength and target-stack effects are not measured by this checkpoint.

The fixed new ordinary `shipping_simd.py` runs after the unchanged core stage.
It owns its readable/shipping literals, exact canonical and post-core inputs,
paired token roles, positional inverse, untouched complement and final source
identity. It imports only hashlib/re and consumes no experiment, external
report, executable or Clang installation. DEV bypasses all shipping stages;
the original readable source and existing guards remain unchanged.

Focused diagnostic v1 failed compilation because its fixture used canonical
field `half` on shipping struct `za`. That failure is preserved. Explicit v2
changes only those three fixture field tokens to the actual `zL`, with exact
inverse/complement, leaving the candidate and v1 records unchanged. One v2
compile/run passes 3,399 assertions: 832 piece/square components (not legal
full-board claims), 39 admitted-shape boards, ten special children and 98
side/padding probes each. Actual raw SIMD scores match an independent scalar
formula. Its result is
`47567e88e61d660b4f015778c54d47093271e784ba66534a3c85b0ed422a69a9`.
The actual candidate wrapper passes two quit/EOF sessions and eight legal GO;
receipt `ad108b597a8263a3f860c6054f2764dc5daa47ba5e6b8b63ec06da1bc5dd05d0`.

The normal builder then independently reproduces shipping twice and DEV
twice. Source/native/whole/bootstrap match the measured candidate, while both
DEV source/native tuples actually match their preceding full identities.
The unchanged normal verifier passes two additional actual quit/EOF sessions
and eight legal GO, observing the new process image, stable startup TIDs,
unlinked private paths, readers and natural physical exit. No fresh archive
extraction, extra candidate, game or benchmark is run. Cancellation causality
remains unproven. The ordinary C closure is now 21 files.

Normal build/runtime receipts are
`c07ff5af9bceeed62ecaaf3f2fb36d20ca6ec76f4ce5f76ad511ccdfc82124ad` /
`11d28534dda26349dadeff13a2d606cdd1f7127aada4e5e9bdb3a43d5e187361`;
combined normal receipt is
`d36cf1eea2697d24af6bcd33c3c24bd08faf9171028e8f0ee23863dfe1bc8436`.
New source is
`90a566c5e814cf87dd38f92f40ce8fe7115c4d4d07f75d9ff0981ffaae1fbc28`,
native `c32772b3d1bb9ce985bfdecbd31dc4cc5fd06721f03aa6259a4021a4fbb0c788`,
whole `de57a0a21e8ecb2f958207c3e71bcc7d791448340acc103faaea5f1010433933`.
Producing sources/recipe and later completion metadata remain separately
preserved. The frozen experiment records its first-cost stage only.

The preceding normal head `d982717` passes both jobs in
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39431496618)
and [repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39431496637).
CI for the later C promotion is reported separately against its actual head
in the draft PR. Those earlier successes do not accept a future source.

A separate source-only A/F review finds that nullable parse can share the
terminal branch's first-legal-move scan. Its estimated 20-35 compact C bytes
per family are unmeasured, with no candidate or whole-size saving included.
The next structural work is prioritized against the complete family gaps;
the twelve independent cores, final resource profiles, parallel comparisons,
target hardware/scaling and strength validation remain open.

## A/F terminal witness: source shrink with complete-file regressions

The previously unmeasured nullable-parse/terminal-witness proposal is now
measured as one fixed candidate per family. Unchanged text/query definitions
move before search; the terminal branch reuses the query, and ordinary move
generation moves after that branch. Exact span inverses and every untouched
gap are checked. Each compact C file loses 23 bytes, but A's complete file
grows 4,766 to 4,775 bytes and F's 4,735 to 4,738 bytes. Both candidates are
rejected for size; the maintained A/F selections remain unchanged.

Each family runs one stdin native compile and one fixed ALONE encoding,
sequential A then F. Strict bootstrap/source/argv recovery and independent
CLI decode pass. Native byte counts stay 22,672/18,576, but full identities
differ; equal sizes do not establish native or runtime equivalence. No
functional fixture, native/whole execution, DEV build, normal promotion,
control compile, retry, game or benchmark follows these losses. Owned groups
are absent and handles terminal. The exact compressed-size cause is not
isolated, so function relocation is not counted as a general size benefit.

Actual A/F cost receipts are
`c3ad15651a1475be95ddea0cc31088ebd75291614666b6291776386f89e72a55` /
`a70c80138f64689c6d9d8b479f30642ad099f3dbd6466429829f26dcb3dd7a28`.
Final experiment handoff is
`5a4cbe7bd69cd09e4b251114e196c3abbf941c2e5bb231b2cc613d9bc79e815b`;
five ordinary experiment files are frozen separately from generated artifacts
and producing snapshots. The measured 92dfc34 normal selections pass both jobs
in [C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39437607789)
and [repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39437607775).
Later WIP experiment heads report their own CI separately in the draft PR.

## B/C/E input profile and B ordering model: measured candidates

The A/F input policy is independently projected onto the current B/C/E
shipping sources. Numeric admission uses an initial ASCII digit, complete
`strtoull` consumption and a signed-64 upper bound. The four exact clock keys,
last own-side value, absent-versus-zero time and budget calculation are
preserved. A bounded line reader drains oversized/NUL input, admits a final
line without LF and retains CR in the physical limit. B/E now share the
nullable legal-child query between replay and first-move selection; C already
had that query and retains it byte for byte. Search, worker reset, SEE,
model, SIMD and state updates remain outside the changed regions.

One fixed native/ALONE cost per family produces the following actual files.
That first-cost stage is distinct from the later normal qualification below.

| Family | Shipping C | Complete file | Complete-file change |
| --- | ---: | ---: | ---: |
| B | 12,148 -> 11,829 | 5,546 -> 5,461 | -85 |
| C | 11,086 -> 10,886 | 5,245 -> 5,173 | -72 |
| E | 11,703 -> 11,378 | 5,366 -> 5,281 | -85 |

Actual cost receipt is
`17fec69bafea30a4b53d9913744f9abf2889a438df439aeeb4e2c682a6e5be99`.
The focused include-fixture then passes, per family, 25 numeric, 26 GO and
25 transaction cases, six special roots/96 child states, nullable-first and
invalid query checks. B bitboards are independently reconstructed from its
mailbox; C/E do not claim a nonexistent cached scalar field. Actual start
and legal e2e4 child boards supply both GO sides. This workerless fixture
does not establish production pool execution. Its receipt is
`2f5308246118a6c4a5d9771c036b0129005c3fc617a2de04074696a4517a37c9`.
Three actual whole-file text-only sessions also pass eight ingress payloads
each, with zero search GO; receipt is
`05a3f10389604e6e5773bd08a56ed6a0de4461a46767e28356a46ea5089a8452`.
The normal verifier alone will handle the identical whole's quit/EOF search
sessions; no duplicate focused quit/EOF qualification is added.

Normal qualification then passes all three entries. One builder per family
reproduces shipping twice and DEV twice, with all source/native/whole/bootstrap
bytes matching the measured candidates. The full previous DEV source/native
tuples actually match both new attempts. The new pure shared ordinary helper
runs last after each family's existing core/SIMD stage; original canonical
guards and protected code remain. DEV selects old bodies from the dual
readable while retaining original canonical bytes for the existing guards.
Normal generation imports no experiment or external report/Clang installation.
The ordinary B/C/E closures become 21/22/20 files.

The three unchanged selected verifiers pass six actual quit/EOF sessions and
24 legal GO, observing the new native images, three stable startup TIDs per
session, private-path removal, readers and natural physical completion.
Fresh extraction, extra variants, games and benchmarks remain zero.
Cancellation causality remains unproven; the unchanged normal compiler helper
does not separately observe compiler-descendant process-group absence.
Actual combined normal receipt is
`243c9017e0fc9ddf225a65363ace9384d46cea397da912319f6afa1bd7b5b92e`.
B/C/E build receipts are
`c196fc146544681c216d7542a5ffc90fdb03361f2e769ba86acea2b61d73e424` /
`d009eb2fce9e758da78042e8541b346c09439ac8b9a2c93959cb0921452b219b` /
`39e7acb5b988dc1f839ae343355f39d0f17072739186751c83ba0beb6df32d9c`;
runtime receipts are
`a20b0f0d1687d1786c63df32d58e8b93cb4211105b87c2292d53a442ff4b2078` /
`8d644dd4f84bcd551d15af3b46de5e7115052dfe723c0286b5ac9c41cb0d9c8b` /
`daa28c9ee2fa8c9a20709382366249923eaf6c140d4b28de4ee995c46ace28c0`.
Producing sources and later qualification metadata are preserved separately.

A separate B candidate changes the declared SEE model to deterministic legal
LVA for ordering. It selects the least pre-capture piece kind, then the lowest
source square; illegal sources are skipped, and all four promotions of the
selected pawn are considered. A negative continuation can be declined. The
shared cancellation/deadline unknown value propagates before subtraction.
This is not the former full legal minimax model. Its negative values are not
pruning certificates: the QS negative-SEE pruning clause is removed entirely.
The existing ordering call and unknown guard remain byte-identical.

Combined with the actual input-profile B, source falls 11,829 to 11,702 bytes,
native grows 26,392 to 26,400 bytes and the complete file falls 5,461 to 5,426
bytes (-35). The measured combined difference from the preceding maintained
5,546 file is -120; no unrelated saving is added arithmetically. Actual cost
receipt is
`01daf1ba45610f8121cc18ec5f781dea3eff46ddf250ff32c7aab59d48ed168e`;
whole identity is
`cb19a87f31df9b27ff76f445518768f6a051c51056e9ba6f2ddc53e3eb4a5093`.
One native compile, one ALONE encoding and two pure strict decodes run in that
cost stage, with no baseline compile/copy, engine/oracle, DEV or strength
execution. Both producing and final ordinary source sets are retained;
generated artifacts stay outside Git.

Separate model qualification subsequently passes one production-source
include-fixture compile/run. An independent 64-cell oracle supplies 85 legal
score/state/policy rows, two illegal initial moves, two normalized-EP exclusions
and six immediate/deep cancellation/deadline guards. Actual child placement,
side, EP, halfmove and rights, plus rebuilt native hash/HCE/bitboards, agree.
All selected-source promotion branches are evaluated. A losing queen
continuation is declined as zero; pinned attackers, king safety and EP removal
are covered. The fixture-only external clock does not change target source
bytes and does not establish production wall-clock behavior.

The explicit FEN `k7/8/2p1B3/3n4/1rP1P1K1/1b6/8/8 w - - 0 1`, e6d5,
has independent full-minimax score +90 and actual legal-LVA score -10.
The rotated case scores +90 under its different ctz priority. This documents
the intended model difference, not equivalence or a strength improvement.
Focused proof/final receipts are
`5bb133e2d840c61c4d1f8fcee8042080ad1ebcfafdb0acfbafb18c37c08a9aa1` /
`08793fb0790909aa6057f6f42c3cf4630b23624a240c1fbf4e1caf52803dc462`.

The new pure ordinary B-only shipping_order.py is applied after the unchanged
input helper. It embeds its literal roles/counts, input/output pins and
11,083-byte protected complement; normal builds read no experiment/report/AST.
Canonical and DEV retain full legal minimax as an explicitly different
reference model. One normal builder reproduces the new shipping twice and
the old full DEV tuple twice. One unchanged verifier passes two actual
quit/EOF sessions and eight legal GO, with the new full native image, three
startup TIDs, readers, private-path removal and physical exit. No additional
focused wrapper, fresh rebuild, oracle, game or benchmark is run. Stack and
strength are not qualified; cancellation causality remains unproven. B's
ordinary closure is now 22 files. Actual normal build/runtime receipts are
`f9c1c3b969cae739885dd3cccf2c5f6d88768504ae7ca67d46dbbd4e697a91c2` /
`a2d12a0fe8cafca23a9a4a4b862e655dc6364fc4d0c5ceeda9904668919b608c`.
Producing and completion-only metadata are separately preserved; final
source handoff is
`692f41fab64ef6d68203b515fbaf6022a723cba44ded1cf79120c303ffd472f6`.

## D fixed-model replay: first complete-file cost

The new D packet removes its redundant coded-bit count and WMASK words.
The exact native IMAGE_SIZE determines the count; the validated selected
scalar/HQ model supplies a fixed unsigned-32 WMASK to the decoder. The 21
mask bytes and range body retain their order. For each coded bit, the decoder
replays unary WMASK weights and seeds in that same order, collects all
probability slots, then performs the existing alias-sensitive updates.
The temporary 21 seed words and 21 weights disappear, while the 21 slot
offsets remain. Unsigned wrap, range math, prefix history and the fixed
H24/base10 model are unchanged. This changes the packet ABI and tag; it does
not change the version of the model's JSON schema.

Each form's new packet loses eight bytes and nonpacket overhead falls
1,293 to 1,194 bytes (176 ELF/PHDR + 1,018 text), so the actual complete
scalar/HQ files fall 6,272/6,452 to 6,165/6,345 bytes, respectively (-107
each). Native files remain exactly 7,964/8,352 bytes with their full previous
identities and layouts. Two positive C decoder diagnostics restore the
entire BCJ and native bytes, check canaries and unmap their context. Two
CHECKPOINT0 loaders are compiled for cost; neither shipping nor audit engine
is executed in this stage. Actual cost receipt is
`0f08bb54783aef070a3d75eefeb28a005868156452243513da624bf7708d8137`;
final six-file experiment index is
`2f06d3ecc4d9e0f5fb294f6adfe533aa4559867fd31b4fad10604ed4060a5bf3`.
No native/control compile, control encode, negative fault, sweep or retry
runs. The first-cost stage does not inherit the previous whole's physical audit.

Normal integration now closes that separate qualification. The required
internal MODEL_WMASK argument is bound to the exact admitted native/form
geometry. The packet tag changes in the encoder, builder and verifier while
the model-source tag and integer coder stay unchanged. The independently
checked native/full-layout guards and physical observer bodies are retained.
Seven ordinary files change; native8, loader.c/image.ld, range_bits/models,
fresh.py, flags and resource policy remain unchanged. The closed normal
source set stays 21 local files plus oracle and LICENSE.

Separate CHECKPOINT1 discovery reuses exact first-cost native/packet inputs
and compiles two audit loaders without executing them. Root and an independent
reader inspect actual bytes, program headers and the entire embedded packet.
Only the observed scalar 6,188/df364080... and HQ 6,368/8d4c4ceb... audit
identities are registered in the recipe and independent verifier literals.
The discovery receipt is
`9d886f3ce1ecedbd3b68d715a796d4c686cb9cf58b574dbe8caf9d65655dc6ce`.

One unchanged fresh campaign then passes two independent closed 23-member
source extractions. It performs eight native, eight shipping-loader and four
audit-loader compiles. Both forms' native/full whole/audit bytes reproduce
across both extractions. Eight production quit/EOF sessions run 24 legal GO;
four positive pre-entry audits observe exact restored RX bytes and padding,
zero BSS and padding, guards, NX and original-entry resume before natural
target/reader/process cleanup. No additional native fixture, negative fault,
RIE/ptrace/register/personality campaign, retry, game or benchmark is added.
Actual fresh receipt is
`5c431c0417c82f2c579d198c27a754ba6a928a33c06b8ac33b4e7a977bf0e113`;
actual readback is
`c76b705fce499646a46e938280e1b9fa340e57b252aaaffd2668f5351b081572`.
The producing archive and later qualification metadata stay distinct.

## F lexical reuse: equal source/native size, larger complete file

A separate fixed-current-F experiment inventories one-character automatic
locals and definition parameters directly, rather than invoking the older
long-name eligibility path. It uses original physical declaration/reference
positions and deterministic greedy aliases. Globals, statics, members, types,
ABI, macros, external names and opaque spans stay protected; unsupported
name/type observers and variably modified type contexts are excluded. Each
accepted trial requires zero parser errors, exact declaration/type shapes,
original-position reference bindings with multiplicity, remaining tokens,
header closure and positional inverse/complement. This fixed-source CIndex
projection is not an arbitrary-C equivalence claim. The pinned external
ice4 renamer informs the comparison only; no upstream implementation is copied.

Revision 1 aborts when ordinary alias-collision diagnostics hit Clang's default
fatal error-count limit. Its source, fatal trial and incomplete checkpoint are
preserved. Explicit revision 2 adds only `-ferror-limit=0`; ordinary errors
still reject aliases and genuine fatal/nonlocal errors still abort. One fresh
60-second pass processes 102 of 169 eligible declarations. All 169 start with
one-character names. Greedy completion is false, but an independent final
parse validates the retained candidate: 94 changed declarations/490 physical
identifier positions, 278 declaration shapes and 2,429 reference edges with
multiplicity. The 544 parses and 60.679 seconds belong to source analysis,
not a codec or engine search. V1's failed 86 parses are separate evidence.

The validated candidate is still 9,728 source bytes. One normal-argv stdin
compile gives the entire old 18,576-byte native exactly; no metadata exception
is used. One unchanged ALONE encoding nevertheless grows the complete file
4,735 to 4,763 bytes (+28), so the candidate is rejected and normal F stays
4,735 bytes. Strict bootstrap/source/argv recovery passes for baseline and
candidate. No control compile/copy, additional AST/PP, engine/wrapper, DEV,
normal promotion, game, benchmark or retry follows this cost. Compiler-group
absence is not separately observed by the unchanged compile helper.
Source-only v2 and cost final indices are
`ee5506b4eacb7c555e967fe6db0810e4c5a56e1aed13ee1232e1120138d536c3` /
`621b3cb56572b630611e98afa6f90c93fa3e9ce13c43bec675b2dab61af30245`;
actual cost receipt is
`90f523773740ae5b05566a69319bd2d7127dbe35f42981831a448e884447a151`.
Producing ordinary source5 stays frozen separately from external results.

The preceding B/C/E promotion head `2c4482bc60ebf66c2e16010f94564152b5450921`
passes both jobs in
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39446196913)
and [repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39446196928).
The later B/D promotion and F failed-cost head reports its own checks in the
draft PR. No family yet meets 4,096 bytes. Final resource/ISA profiles,
integrated parallel-policy comparisons, scaling and strength remain open;
training and AWS remain outside the active goal's scope. A/F's next bounded
source lane investigates duplicated hash/HCE remove/add updates with explicit
empty-piece hash zero, without changing the maintained entries at this point.

## A/F combined square-state updates: first-cost losses

That next state-update proposal is now measured. Private piece(0,q) is
explicitly made zero; value(0,q) already equals zero. The two remove/add
branches in put can then share final hash/HCE arithmetic while retaining the
king-square update and all caller/state/EP/rights/halfmove/context bytes.
The zero guard is essential because the original unused piece-zero domain
returns mix(q+768). Paired readable/shipping roles, direct private callers,
two positional inverses and every protected gap are checked. No external
engine code, new name allocator or board representation is introduced.

One native/ALONE cost per family, A then F, saves 22 source bytes each but
grows complete A 4,766 to 4,772 (+6) and F 4,735 to 4,738 (+3). Both are
rejected; maintained A/F stay 4,766/4,735. Native sizes remain 22,672/18,576
but full identities differ. These are cost observations and source reasoning,
not executed functional equivalence. Strict source/argv/true-EOF and
independent CLI restoration pass. Owned commands/groups terminate; no
functional fixture, native/whole engine, DEV, normal promotion, control
compile/copy, additional variant, retry, game or benchmark follows.

Actual A/F cost receipts are
`b127b7509df088340f16ac99da31aa2dfd28ebaf5bc0568f16ce94c0b16d8775` /
`dfafa09d28fe1513587e7138830a902b51f73a02547bbab01d9b0278c12aa068`;
final five-file experiment index is
`e1295ebb74bbfa1cd928692342a7169d1d12c83357ee07a62f3f6d5ec774a253`.
Producing source/config stays separate from the final README result metadata.
The qualified B/D promotion head `77dd96126b43d03ef787f0ddf856071609f28802`
passes both jobs in
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39447827788)
and [repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39447827767).
This later failed-experiment-only checkpoint leaves maintained code and
selected identities unchanged; its own CI is reported separately in the PR.

## Additional review of the external PR12 size analysis

The user supplied `Rove4k_PR12_Size_Analysis.ko.md` on 2026-10-21. Its pinned
head is `a3546f1f409337bc0cf176cdfefc14bbdd1a3693`, before the current
`fd262f768166ea4c37b190942e521461dc0c435a` checkpoint. Its checklists are
reference proposals, not additional authority or a change to the engine plan.
The current recipes already contain function-local names/internal symbol
changes, fixed ALONE decisions, the C/E TT/sort/clamp reductions, C's real
16-lane AVX2 residual-feature dot, B's declared legal-LVA ordering without
negative SEE pruning, bounded input profiles and D's fixed21 own decoder.
The older document's reductions and minima are not added to current savings.

Pinned upstream implementation was inspected outside the checkout: ice4
`2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19` (actual board/search/UCI and
minifier passes), 4ku `203ddd4bf9b331851c796d8b5d57eac08f6e6c18` (actual
board/evaluation/search), 4kc `26e936860c8da80de73ea3041ccade96ba8112a3`
(actual C/codec/loader), and STRO4K
`51ea73a3d86141d96ad428402dc387722fc0f9b1` (actual common/UCI/search/game
assembly). New reference downloads stay in the external comparison folder.
No upstream implementation is copied into this repository. Existing upstream
comparison descriptors are metadata, not vendored engines.

ice4's adjacent declaration and sequenced-expression passes motivate a small
independently written fixed C expression candidate. Its weighted lexical
allocator does not establish that a new rename helps already one-character
Rove locals; the measured F rename loss remains rejected. ice4's 16-bit TT
signature/queen promotion and STRO4K's 16-bit signature/per-GO clone do not
replace Rove's full-key coherent TT, four promotions or persistent pool.
4ku's side flip and shared PVS/QS are useful structural comparisons, but
Rove's flip experiment is already a measured loss and its QS/main share a
kernel. 4kc's RWX overlapping loader is not used to bypass Rove's W^X,
guarded restoration and NX stack requirements.

Source inspection rejects several apparent large reductions before new
compilation. C's `value` has two capture-ordering consumers in addition to
the SIMD accumulator, so deleting it is invalid; changing only the SIMD
residual expression adds 81 source bytes. A's TT payload ownership proposal
saves only 17 compact-source bytes after paying its new type/probe costs.
D's search-argument proposal adds four readable bytes; current disassembly
identifies only 12 removable argument push/pop bytes at two call sites,
before new cursor/rollback costs. These are source-only rejected hypotheses,
not measured executable savings or feature deletions.

The following fixed candidates were actually compiled and packed with each
family's unchanged compiler/profile/launcher/codec. Raw source reductions are
not substituted for complete-file measurements.

| Candidate | Shipping source before / after | Complete file before / after | Complete-file change |
| --- | ---: | ---: | ---: |
| A adjacent declarations and completion sequence | 9,713 / 9,687 B | 4,766 / 4,762 B | -4 B |
| B shared source-forward attacker/generator walk | 11,702 / 11,532 B | 5,426 / 5,371 B | -55 B |
| C shared material/SIMD coefficient storage | 10,886 / 10,831 B | 5,173 / 5,159 B | -14 B |
| F adjacent declarations and completion sequence | 9,728 / 9,702 B | 4,735 / 4,730 B | -5 B |

A/F's six declaration boundaries keep their initializer order and scope. A
completion comma expression retains result/output before broadcast inside the
existing lock. Each candidate's entire native is byte-equal to its previous
selected image, not merely the same length or mapped code. Both now regenerate
through ordinary family-owned `shipping_declarations.py` closing stages after
the input profile; no parser, upstream source, experiment or artifact is a
normal regeneration input. Each normal builder reproduces shipping and the
unchanged DEV twice; each unchanged selected verifier passes two sessions and
eight GO/result pairs with exact restored image, three startup TIDs, and
physical quit/EOF exit. The joint normal summary SHA is
`7f70249dd7fcfd4a702997e73c2ebcc42748393839e5da7a16d1a2b94db54f0f`.

B's new ordinary `shipping_walk.py` runs after its existing input and legal-LVA
stages. A non-null buffer produces moves; a null buffer accumulates all source
bits attacking a target. Friendly target defense, empty pawn diagonals, four
promotions, normalized EP and castle origin/transit checks remain. Occupied
bitboard ctz order matches the prior mailbox source order. Exact old/new
production fixtures agree on all pseudo-list ordering for 99 boards, 12,672
full attacker-mask queries and 1,281 complete legal child states per source,
also checked against independent geometry/rules. The existing 85 legal and
two illegal LVA cases, two EP exclusions and six cancellation/deadline guards
pass. The focused receipt SHA is
`57367b67b1dd783c3c5c1740d01afa3ab5410d64ab0848698972b9edcf320579`.
Normal B then reproduces shipping and old-minimax DEV twice, and its unchanged
verifier passes two sessions/eight GO. Normal summary SHA is
`1b9650f67590c3a3e71fb83a08c183ca6314242322d82ccfe2b7c37888c203d9`.
This query examines friendly sources rather than eight reverse rays and may
cost more work in make/EP/SEE. Performance, strength and new-frame stack
qualification remain open; no benchmark is claimed.

C's actual `value` consumers remain. The shared sixteen signed16 coefficients
give material as `-qm[abs(piece)+7]`, including zero and king; the same complete
vector still feeds the real AVX2 dot and both reduction halves. Direct actual
shipping fixtures pass 832 value cases, 832 singleton vector cases, six
population cases, startpos and twenty legal children, plus 10,816 capture-order
cases against old functions and independent arithmetic. Focused receipt SHA is
`d9ab97dcf6c7f392526274e5cbde277506fc87820bba097acdc6f1a292986bb9`.
Its selected native has a new identity; the old full-native equality claim is
not reused. Its ordinary closing `shipping_material.py` then reproduces
shipping twice and the unchanged DEV twice. The unchanged selected verifier
passes two quit/EOF sessions and eight GO with the exact new restored image,
three startup TIDs, private path/helper/FD cleanup and physical reader EOF.
Normal build/runtime receipt SHAs are
`b19af6e3a544943130cb6def0eb18219f149b103326d6106e8ac0cc71f76f4f9` /
`57db9cc49da2c577d1aef24400c1ca34c98fcfdf3b421446026f8eb25fb2bc33`.

The independent Rust D query/made-child experiment is rejected. It shares
exact pseudo membership and copy-make between parsing, fallback and best
validation while retaining their phase positions. Raw Rust grows 418 bytes;
both native .text sections shrink 96 bytes, but page layout keeps complete
natives at 16,816 bytes. Fresh original controls reproduce native and packed
identities. With the unchanged own data8 BCJ/Deflate/loader, scalar complete
file grows 11,403 to 11,420 (+17), HQ 11,762 to 11,774 (+12). All four payloads
strictly decode and inverse-BCJ to exact image spans; no produced ELF is run.
Existing guards are unchanged, and a separate literal candidate class retains
every data8 geometry condition. The phase-summary SHA is
`d0d6ebfc717c3d0e0ec4f81c92fd45eef30e9a25798eed09f6611ef833d8e189`.
Maintained Rust D, its runtime and old identities are unchanged. There is no
functional follow-up, codec/flags sweep or retry after this measured loss.

This checkpoint changes no resource profile, E model, maintained D loader,
canonical C/Rust policy implementation, NVCompact dependency or release state.
Selected entries remain above 4,096 bytes: zero of six families is size-eligible.
Target resource/ISA selection, integrated policy comparisons, scaling and
strength remain open. No training, AWS/paid execution or game/strength
benchmark is performed during this additional compression work. All generated
source/native/whole files, fixtures, reports and archives remain outside Git.

## PALS feedback and further source-cost follow-up

Canonical C and Rust now implement a finite selected-challenger PALS exchange.
A completed normal proposal supplies the claim; a requested legal reply is
searched in the fixed root-perspective window `[claim-1, claim]`. Only a
compatible completed EXACT/UPPER result below the claim is a diagnostic
refutation. C accepts an EXACT/LOWER proposal for this purpose; Rust's proposal
uses its full normal window. A nonrefuting diagnostic skips Repair. A refuting
diagnostic triggers one unrestricted same-first Repair followed by one
mandatory review of the same reply against the repaired claim. Persistent
contradiction, incomplete work, mismatched context or cancellation rejects the
depth and preserves the previously completed depth. Restricted scores and
reply selection never enter the normal root/cache aggregate. Original
deadline and node budgets remain in force. This selected-reply diagnostic is
not exhaustive certification of every opponent response.

Actual retained-TT testing found that ordinary hinted Repair could return the
old claim immediately without investigating its challenger. Both search cores
now order the hint before the TT move and bypass TT score cutoff only at the
hinted response ply. Descendant TT reuse and normal TT publication remain.
C also resets the old root alpha when a repaired proposal becomes lower.
The persistent C search contract proves an ordinary optimistic TT value of
700 is returned in one node, then actual hinted Repair searches 81 nodes and
recovers the unpoisoned baseline 22; the subsequent normal lookup uses 22.
The existing B/C/F runner registers this regression without a workflow change.
Its final run also passes SEE/singular, 400 actual SIMD/reference positions
and MTD/minimax/retained-horizon/cancellation tests. Final receipt SHA is
`1bbdfd5c89a9083001c76a3abd6adb1551b83d957e95dadf2fd8a3b40b9796dd`.

An independent review found another real boundary: forcing a reply after a
first move that already reaches a draw could reset the halfmove/repetition
state. Diagnostic search now honors the root and first-child draw before
continuing, while still validating and echoing the requested reply. Actual
clock-99/quiet-first/pawn-reply and seven-ply knight-cycle/third-repetition/
pawn-reply fixtures prove the discarded continuation has nonzero evaluation
and resets the draw context, while the constrained diagnostic and normal
first-move search remain zero. These are source/search fixes, not expression
compression. The earlier C A/PALS four-worker run, two sessions/ten GO and
five stable startup TIDs, belongs to the version before this final draw fix;
it is not relabeled as an execution of the final callback. Current C callback
branches are exercised directly by the new B/C/F contract.

Rust's final source passes all 44 unit tests. The new draw regression first
fails against the old actual method with diagnostic 505 versus normal 0;
that failure is preserved. After the fix, actual cfg(not(test)) A/PALS at
clock99 completes depth1/2/3 with scores0/0/0 and two clauses/no Repair.
A retained-TT repeat still produces one real refutation/Repair/recheck.
Final DEV and shipping focused sessions both exit0. The final receipt SHA is
`960f7fe459f36c99ae79060ef55f877dfde5d2e91a3c5cf69ba312fa9eadcda2`;
the earlier 43-unit/three-session receipt is preserved separately.

The Rust fixed-loose source producer explicitly admits the reviewed canonical
source hashes. Its first comparison preserved five of six outputs exactly;
generated search grew 67 B from the hint priority/cutoff gate and a trailing
comma after stripping the test-only observer. All hint producers in this
fixed-loose output are None. A test-only observer spelling initially exposed
an existing cfg-strip boundary that consumed the following `let quiet`;
the canonical observer was wrapped in the already supported block form,
without loosening the parser or source guard. Old output equality is false;
the new output was reviewed as a distinct source identity.
The subsequent terminal-draw fix changes only methods that this fixed-loose
producer already removes. A fresh six-file dictionary comparison is exactly
equal to the reviewed new output, and the final normalized source binding
explicitly admits search `5107c61b...` / parallel `f7d7b2fe...`. ProducerGuards
passes five tests at each reviewed admission; compiler fixtures are deferred
to the existing CI path rather than inferred from those guard tests.

A separate canonical A policy cost compares exactly four native builds at
workers2/TT18/DEV0, using each language's unchanged compiler recipe and only
common lexical compaction. It freezes C search `6fd8196e...` and Rust search
`db3918e2...`, before the later terminal-draw fix. These remain valid historical
measurements of those exact sources, not costs for the newer final source.

| Frozen canonical profile | Native bytes | Fixed native-wrapper whole |
| --- | ---: | ---: |
| C loose | 30,768 B | 16,829 B |
| C PALS | 30,768 B | 17,799 B |
| Rust loose | 372,376 B | 194,654 B |
| Rust PALS | 377,808 B | 198,069 B |

Within these controls PALS changes the fixed wrapped native by +970 B in C
and +3,415 B in Rust. Unspecialized canonical source wrappers still contain
all policies and measure 21,150 B for C / 24,926 B for Rust. None of these
rows is a specialized tiny entry, its policy delta, or a strength/scaling
result. Four native compiles, four native wrappers and four trivial source
wrappers were made; no produced engine was run. The cost receipt SHA is
`d49b689c6ed5bd4d44b6a30317f2715e1de01e13a56ef91e9486f46e4ecd6ef2`.

The E generation/leaf-feature fusion is rejected after one first cost.
It accumulates the same leaf terms during move generation and preserves all
21 coefficients/order expressions, but raw source 11,378 to 11,349 B (-29)
produces a new same-length native and whole 5,281 to 5,300 B (+19). The new
92-byte recursive Features scratch has no inherited frame/stack proof.
One compile/ALONE package and two strict decodes pass; functional/model/stack
qualification and engine execution stop at the measured loss. Maintained E
is unchanged. The summary SHA is
`7155eeba3327110e21fafa57841a39debb3493696b5d7a1f291d67d27ddd0e51`.
The ordinary experiment contains project-owned transform/cost/configuration,
not generated native, source outputs or reports.

D's independently authored hardware CRC32C byte candidate changes only
`cx_crc`: the instruction consumes the original 32-bit seed and byte, without
the old software pre-XOR. It requires an explicit Linux x86-64 SSE4.2 profile.
CRC-only checks pass 5,673 comparisons, including seed/byte basis inputs,
all byte values across six fixed seeds and deterministic random inputs.
Both actual fixed21 packets decode to the complete exact BCJ image and inverse
native, with owned-buffer canaries and context-table release checked.
Unchanged packets/native and two new shipping-loader compiles give scalar
6,108 B / HQ 6,288 B, both -57 B; overhead is 176 B header/PHDR plus 961 B
text instead of 1,018 B text. Static disassembly confirms the byte-input,
32-bit-output CRC instructions. The first-cost result SHA is
`b645ec13306c0f40ea7cd19be045fe140354482fa37f13434d0a2f6a7cd4b2c1`.
Five compiles, three isolated diagnostics and two static disassemblies all
settle normally; this first-cost stage executes no produced shipping ELF.
These data diagnostics are separate from production restoration/entry proof.

Normal-source integration declares `linux-x86_64-sse4.2-crc32b-v1` explicitly
in recipe/build/verification. Verification checks exposed SSE4.2 on every CPU
in its inherited affinity before launching an owned target. The original
21-file/23-member source closure, complete predecessor recipe and eight
selected native/packet/shipping/audit controls are preserved outside Git.
Only the CRC function and narrow profile/admission metadata change; packer,
fresh extraction and physical observer/cleanup bodies remain byte-exact.
Audit discovery compiles two actual CHECKPOINT1 files at 6,131 / 6,311 B,
with hashes `0b48475cd8ac138662a8414981e38dea49a17e892637fc951d84849303390cd7`
and `a6a5b1c1bc5cad1fdca2fdb4c3744fba95873a325a8381d877c73795552e5b88`.
Both compiler processes return0, reap and leave their groups absent. The
outer discovery driver nevertheless exits1 because a temporary row variable
shadows its saved signal handler during final restoration. Its raw report's
premature `complete:true` is retained as inaccurate, with a separate
`complete:false` failure companion SHA
`b8d7dc74d6a707ec083afaf995df751ff522ba89dc6b4aab1fb9524aed3801dc`.
The overall discovery is not reported as PASS; actual compiled artifacts and
their static review are a separate admission basis. No discovery retry or
target execution is used to turn that driver failure into success.

After actual static readback and root intake of those two audit literals, one
separate unchanged normal `fresh.py` run passes with terminal0 and no retry.
It archives 23 ordinary members, extracts twice independently, and reproduces
all eight native, eight shipping whole, four audit and twelve packet outputs
exactly. Eight shipping sessions/24 GO and four positive pre-entry observations
pass with restored RX identity/padding, initial BSS/padding zero, exact guards,
NX stacks, original entry resume, two persistent workers, reader EOF and
natural target/group exit; forced cleanup is zero. Both verifier invocations
confirm SSE4.2 on every affinity-available CPU. Compiler commands return0;
the unchanged builder does not separately observe compiler group absence.
The fresh receipt SHA is
`96fa649d7b192addc135104313e2692121ec1df69acaf41666eb9bb796079d83`,
and actual readback SHA is
`6129b0dfd350bf83c04fd0642631e7073cf513564b8241292564c3ab14bde5bf`.
This qualifies the new local SSE4.2 maintained pair at 6,108 / 6,288 B,
still 2,012 / 2,192 B above the limit. It does not repair or relabel the
earlier failed discovery driver, infer current tournament-server support,
or measure performance/strength. Only README and recipe qualification
metadata are overlaid after the actual producing source/archive freeze;
the executed source set and later explanatory set remain separate.

At this historical checkpoint the A/F single-condition proposals removed28
raw bytes each and were uncompiled/unselected; later dated sections above
record A's fixed-two-worker promotion and F's separate current-source study.
Sharing startup notification with epoch waiters
can cause quadratically many redundant wake attempts during many-worker
startup; a source-byte reduction alone does not justify accepting that cost.
The exact proposal stays outside Git. No training, AWS, paid execution, game
or strength/performance benchmark is part of this follow-up. The six-family
4KiB objective remains incomplete.

## Further fixed source representations: incremental state and coefficient packing

Actual pinned ice4 board/evaluation and 4ku source were compared again with the
new Rove drafts outside Git. ice4's `Board::edit` owns incremental evaluation,
phase and piece counts; this supports concentrating derived-state maintenance
in the existing square writer. 4ku's side flip, feature rescan and packed MG/EG
evaluation have different board/hash/evaluation data flow. Rove's candidates
retain their own HCE, SIMD and dead-material meanings; no tuned coefficients
or implementation were copied. The minifier description is specifically
occurrence-weighted lexical-scope conflict coloring/grouping, not CFG liveness
coloring. The external comparison report SHA is
`f02d7dc79d470614dc37206c72706e1c5ffa5f9a9e67fbc6c9dfaaded1a40fd9`.
A narrow tracked-path check finds 62 external-engine-named JSON descriptors
and zero implementation-extension paths with those names. This is not a full
provenance proof for arbitrarily renamed files. All new source in this lane is
project-owned; upstream source remains outside the checkout.

Each first cost uses the actual current family control and unchanged compiler,
resource, launcher and codec decisions. Individual reductions are not added.

| One fixed candidate | Raw source change | Actual whole before / after | Decision |
| --- | ---: | ---: | --- |
| A incremental dead-material summary | -57 B | 4,762 / 4,776 B | Reject, +14 B |
| F incremental dead-material summary | -57 B | 4,730 / 4,738 B | Reject, +8 B |
| A packed HCE coefficients | -12 B | 4,762 / 4,766 B | Reject, +4 B |
| F packed HCE coefficients | -12 B | 4,730 / 4,728 B | Normal promotion qualified |
| C incremental 16-lane residual vector | -28 B | 5,159 / 5,152 B | Normal promotion qualified |
| Rust D fixed castling bounds, scalar / HQ | +18 B | 11,403 / 11,383 B; 11,762 / 11,741 B | Cost gain only, runtime unqualified |

The material summary uses six-bit counts for two bishop square colors,
knights and pawn/rook/queen material. Its O(1) dead predicate is statically
equivalent through the bounded 32-piece construction prefix. Despite the
shorter source, both complete files grow. Exactly one candidate compile and
ALONE package per family and four total strict decodes finish normally.
No engine, DEV, layout probe or functional qualification follows these losses;
normal A/F material state stays unchanged. Their cost receipt SHAs are
`5b8f96148db40738cc0b4114a47316d4d72aca147ddb87c3d89d4ee8cba794ed` and
`418f3324fce4a817f7818f29a6a59948d4461ef9a54e014b9263097d968e57a4`.

F's selected coefficient stage packs the original material/advance/center
triple into a signed int, retaining the zero value, king center -3 and both
colors. The actual candidate fixture passes 832 unique values, explicit zero
checks and 384 unchanged-put updates against the old function and independent
integer arithmetic. The conservative at-most-32-piece HCE bound remains
29,120 below the existing 29,871 threshold. One ordinary normal builder then
reproduces shipping twice and the unchanged DEV twice. Its unchanged selected
verifier passes quit/EOF two sessions and eight GO with the exact new native,
three stable TIDs, path/helper/FD cleanup, reader EOF and physical exit0.
Observed TIDs are subsequently absent. Build/runtime receipt SHAs are
`abdb1f451ccc2dfcf238c95ccac7067c58a0bb8b6cacdc1736bb63dee12cff21` /
`38cb0364889da52b690e1152c1832e4f51486c89a07f2544bc26dac246774a9b`.
The new ordinary closing helper follows declarations, has exact inverse and
complement guards, and has no experiment/report/artifact regeneration input.
No fresh archive or DEV engine execution is inferred from this direct run.

C's candidate keeps the original sixteen signed16 lanes in private Board state
and updates them in the existing nonzero square/hash helper. The leaf uses the
same AVX2 madd and both reduction halves. The actual candidate and fixed DEV
reference each compile and run once with ASan/UBSan. Start, captures, both EP
colors and pinned EP, both castles, all four capture/noncapture promotions and
154 legal children agree. The actual shipping SIMD body is preserved inside
a test-only observation wrapper; all 1,464 consumed vectors match independent
mailbox reconstruction, scalar HCE and hash checks. Capture ordering agrees
in 10,816 cases, four poisoned EP scratch checks pass, and two actual depth2
searches agree with DEV on score, best and node count. The focused receipt SHA
is `2b52cd2d9ec912d3a74b90c61622eb886c616258c2bd0f9595e9ee5e78cb1046`.
Actual sizeof changes 168 to 200 B; the production P stack allocation changes
4,384 to 4,416 B. These observations replace the earlier analytic layout
estimate, but do not prove many-core stack scaling or performance. Normal
promotion then runs once through the ordinary builder, reproducing shipping
twice and the old DEV twice. The unchanged selected verifier passes two
quit/EOF sessions and eight legal GO with the exact new restored native,
three startup TIDs per session, path/helper/FD cleanup, one closing bestmove,
physical exit0 and reader EOF. Build/runtime receipt SHAs are
`5b5f831b89629e605e725316f9d0bed316c186ce12cba1f64a7c535f8f2cb57e` /
`bed3061a619a0ab7f97fe1fee99ea2a4f61e33a66d7cffe06e780e151ff91648`.
The exact four-region ordinary closing helper follows the material stage;
canonical/DEV and previous source guards remain unchanged. Direct generation
does not imply a new fresh/archive run.

Rust D's three masks expose the fixed castling-tuple bounds to the compiler
without changing any original coordinate, adding unsafe access or changing
condition/move order. Two actual candidate native links reduce each .text by
64 B while page alignment keeps each whole native at 16,816 B. The three
targeted checks/tails disappear; the separate double-pawn bound remains.
The unchanged own data8 BCJ/Deflate/loader has two candidate encodes/links and
four strict complete decode/inverse checks against original/candidate spans.
Headers plus loader remain 1,115 B. Actual complete experiments shrink by
20/21 B, with packing receipt SHA
`3fa7e0f5953aa772c9958279a04ccffb666a0eb31ac6a1f3b0dc324dd00926af`.
No generated ELF, loader or negative runtime test executes. Maintained Rust D
and the selected C D pair are not replaced by these unqualified experiments.

The remaining six size gaps, final resource/ISA profile and performance,
scaling and strength evidence remain open. This lane performs no training,
AWS/paid execution, games, benchmark, main promotion or release.

## Further model and generated-move structure reductions

The following are selected ordinary C shipping changes after `51f2986`.
They retain the fixed local two-search-worker/TT18/PLY128 profile. Model and
ordering changes are identified explicitly; they are not value-preserving
spellings of the old engine. The old source closures and actual controls are
preserved outside Git before promotion. External evidence paths below are
observations, never regeneration inputs.

| Entry | Previous whole | Selected whole | Shipping source | Native | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| B | 5,371 B | 5,357 B | 11,532 to 11,430 B | 26,384 to 26,360 B | Private tactical Move tag; quiet-promotion ordering changes |
| E | 5,281 B | 5,176 B | 11,378 to 11,105 B | 26,384 to 26,416 B | Explicit new hand-authored, untrained E19 model |

B uses the previously unused FROM bit3 of valid 0x88 coordinates for the
capture-or-promotion class produced by generation. FROM decodes with mask119;
TO, PROMO and the 17-bit TT payload positions remain unchanged. Ordering,
initial SEE eligibility, QS/reduction classification and correction quiet
guards consume this one tag, removing the repeated mailbox classifier. Quiet
promotions now receive the capture tactical base tier. Initial SEE awards the
EP pawn only for nonpromotion tagged moves with an empty target; recursive
SEE moves without the tag already have occupied targets. Full-key TT, singular
exclusion and learning use the actual tagged identity. Canonical/DEV retains
the old Move ABI and minimax model, and is an ancestry reference rather than
proof of this production path.

One focused diagnostic compilation/run checks 99 boards, 294 independent
tactical tags, 1,281 legal child states and the existing legal-LVA numeric
expectations without regenerating them. The actual singular positive control
takes one qualified extension; excluded probes preserve root TT, learning,
board, active path and the original deadline. The actual TT18 child-key read
is a miss, recorded as such; the earlier TT20 child-depth witness is not
claimed. The focused receipt SHA is
`4a27c68d86ed32d65c71d9f909e69a9d244bf26ea2f6ae8adae332850ac6110e`.
One ordinary builder reproduces shipping twice and the old DEV twice, followed
by the unchanged verifier's quit/EOF two sessions and eight legal GO. The
exact new native image, three persistent TIDs, private-path/helper cleanup,
reader EOF and physical exit0 are observed. Cancellation causality remains
unproven. Build/runtime receipt SHAs are
`f1882be151f244f59afa30a1020daeeec9366d6299096840f0ed9911d4d581e8` /
`4496ea25f93e7623e7e3f3e163a91de85df2db18d53055696bc4d267fea29bf9`.
The normal helper follows `shipping_walk` and consumes only ordinary source
and fixed role/literal pins. Whole SHA is
`8b8c3b565974813aa2ea54383bcc19240c1dcf506157d2aa0b44c8b24fa3d5be`.

E's `e-hand-quadratic-19-1` stores 19 exact signed16 coefficients, hand-authored
without training or data. It removes doubled/isolated pawn and bishop-pair
features, keeps material/center/pawn advancement, and adds a global signed
activity interaction. Actual inference is
`clamp(M+A+A*abs(A)/128+side*tempo, -20000, 20000)` with C integer division.
The existing nonzero piece/hash update maintains M and A privately in Board.
The five original ordering features and coefficients `[16,-1,12,2,4]` remain
active, with relocated coefficient indices. The nonlinear residual is actual
and nonadditive: g(32)=40, while g(16)+g(16)=36. Conservative bounds are
|M|<=14,400, |A|<=1,728, product<=2,985,984 and raw<=39,466 for the fixed gain1;
future parameter changes must rederive those bounds. The separate frozen E21
model and Rust E21 are not modified or used as E19 equality evidence.

One ASan/UBSan focused compilation/run observes the actual S/R bodies through
definition-name-only wrappers reached by production search. Independent board,
hash, model and ordering reconstruction, both colors' capture/EP/castle and
all promotion kinds, 534 legal children, complete admitted activity interval
and actual nonadditivity pass. Board grows 168 to 176 B, while the actual -Os
search stack allocation grows 4,392 to 4,408 B. The earlier observer preflight
failed before any compilation/runtime because it assumed a single stack
subtraction; the corrected observer sums the actual stack-clash prologue and
checks its epilogue. Both receipts are preserved. After the executed focused
driver, its interruption cleanup is improved in source only; that revision is
not relabeled as the executed driver. Focused receipt SHA is
`3b1531a9fb64cd0460f93288cb548c2d702d2e2d1f9529ba3b04f1234f7241b6`.
One ordinary builder reproduces E19 shipping twice and unchanged DEV21 twice.
The unchanged selected verifier observes the exact new native in two quit/EOF
sessions/eight legal GO, three TIDs, FD012, private-path/helper absence and
physical exit0/reader EOF. Build/runtime receipt SHAs are
`1d7409d1221b48d31cb9ccd41636e3483da714967e939dad0f635d9281c1be72` /
`2e9d6f7746d903cd125091f3058cf2e9f3c7a7817126ee453ecbe6c69084868a`.
The ordinary model fragment and closing helper are regeneration inputs; the
experiment and reports are not. Whole SHA is
`a3a36bdc0de02931b03434e760c983b4d7689ff432229e1c4173d26a6a664db6`.

Two additional source-only investigations close without a cost candidate.
F's runtime/input/query bodies already share the meaningful lifecycle work;
the apparent duplication has different ownership fences. D's recursive search
already shares normal/QS, ordering, make and the re-search call site. Replacing
it with an explicit per-ply state machine would retain the 2,190 B search body
and add resume/frame traffic. Its 43 B prologue and 19 B epilogue are not a
credible hundreds-of-bytes saving. TT read/write and learning regions likewise
contain distinct necessary work, not whole duplicated blocks. No candidate,
compilation, codec or engine execution is inferred from these rejections.

These selected entries remain above 4,096 B. Their local checks establish the
described source/model and lifecycle scopes, not improved playing strength,
many-core scaling, final ISA/resources, main promotion or release. No training,
AWS/paid work, games or performance benchmark occurs in this checkpoint.

## Uniform type tokens with identical complete native images

A and the full-key F baseline apply one fixed type policy to the actual final
shipping source: `uint64_t` to W, `int16_t` to X, Move to Y and the private
Entry typedef to Z. The 37 B alias definitions follow all includes and precede
the first type use. Fixed family-specific role ledgers cover declarations,
casts, sizeof and the three casts in the MOVE macro. Existing source/directive
names cannot shadow the fresh aliases; external function names, object layout,
string literals and other directives are unchanged. Exact inverse and protected
complement checks bind this particular presentation, rather than a general
identifier allocator or claim about arbitrary headers.

| Entry | Source before/after | Whole before/after | Entire native |
| --- | ---: | ---: | --- |
| A | 9,687 / 9,476 B | 4,762 / 4,748 B | All 22,672 bytes identical |
| F full-key | 9,690 / 9,464 B | 4,728 / 4,720 B | All 18,576 bytes identical |

The actual native equality is checked before each first-cost codec invocation,
including the compiler/header namespace boundary. Each cost uses one candidate
compile and one unchanged ALONE package with strict baseline/candidate decodes.
One ordinary family builder then reproduces shipping twice and unchanged DEV
twice. Each unchanged selected verifier passes two quit/EOF sessions/eight GO,
the exact restored image, three persistent TIDs, private-path/helper absence,
reader EOF and physical exit0. No new core fixture is inferred from identical
native bytes, and no new archive/fresh extraction or performance run occurs.

Ordinary family-owned closing helpers follow the previous last source stage.
They contain their own literals/role ledgers and use the existing pinned lexer;
normal regeneration has no experiment, report or old-artifact input. The four
changed ordinary files per family are the helper, builder, recipe and README.
Old closures/controls and producing closures remain preserved outside Git;
only README/recipe qualification metadata changes after execution. F retains
its complete full-key TT, and has no partial-tag policy composition here.

A build/runtime receipt SHAs are
`ec562d8fd24723a8792e97e27a1c0cb24710ffd99d4e7f79336918aed7d02d7d` /
`cb90a87d40f90f336d01a2c79a2b126117cca002aa9d19749914330e0d8c05c4`.
F build/runtime SHAs are
`6d2570002cd60191971d0b82eb52649eb75b3c36b9fb6f8c51839b7ab040d914` /
`d8d91e35afe725922a0cee5a9601c0d407e8d70366789de0c9d11f6898244bc1`.
The external final index SHA is
`c22baf3b3d39937fe682f64d8a27b8dede397a2fde3a600779f27d57be3e59aa`.

## C signed-net SIMD state

C folds the previous color-separated sixteen signed16 lanes into eight:
zero padding, white-minus-black PNBRQK counts and the signed positional
residual. The coefficient vector becomes `[0,100,320,330,500,900,0,1]`.
The existing put/hash update changes the signed count and residual; the actual
128-bit load/madd/two horizontal sums evaluate the same material-plus-position
HCE. Natural piece indices preserve value(0,q)=0, while the zero king-material
lane still contributes its PST through the residual. Counts are bounded by16
and the residual by2,016 in the admitted domain, fitting signed16. This is a
representation change rather than a new evaluation model.

The complete file decreases 5,152 to 5,092 B, source 10,803 to 10,656 B, while
native stays 26,376 B with a new full identity. Whole SHA is
`175b73a5a720e2197c3842a8e61ed0a335b927491e43d00e60e42cc8509836b4`.
One first-cost native/package invocation and two strict decodes are followed
by one actual candidate ASan/UBSan compilation/run. Definition-name-only U
observation preserves its body and checks every actual production search
consumer. Independent mailbox/hash/scalar-HCE and old16-to-signed8 arithmetic,
all lanes, zero/king material, 10,816 ordering cases, 154 legal children and
four poisoned geometry-only EP scratch checks pass. Both colors' actual depth2
searches retain the pinned old DEV scores/best/nodes. That old executed DEV
receipt is reused explicitly; no new DEV fixture execution is claimed.

Actual Board changes 200 to184 B. Production search allocation changes 4,416
to4,392 B with eight to six pushes and no former 32-byte alignment mask.
Disassembly shows `vmovdqu` XMM, `vpmaddwd` XMM and two `vphaddd` instructions.
The fixed compiler remains `-mavx2`; the intrinsic minimum SSE2+SSSE3 does not
establish a lower runtime ISA profile, and a 256-bit AVX2 leaf is no longer
claimed. These local layout observations are not scaling or strength evidence.

One ordinary builder reproduces shipping twice and unchanged DEV twice; the
unchanged selected verifier passes two quit/EOF sessions/eight legal GO with
the exact restored image, three persistent TIDs, private-path/helper absence,
reader EOF and physical exit0. Build/runtime receipt SHAs are
`12c85436abbe41f246d916c4b91a0580c6435ee5b349ae44f721274a5a05e357` /
`d18ee2e01c7d38163599784e35ec8736530bd5d6ec011db0e60c98f5aa30aacd`.
The five-region ordinary closing helper follows the incremental stage and
retains every preceding source guard, canonical/gather DEV and verifier.
The old closure/controls and producing recipe remain outside Git; only final
recipe/README qualification metadata changes after execution. Final aggregate
SHA is `2f83669e0b7cf5f45316b34816c7f5dbb1c4c095d0c2596b402895f264909692`.

## Separate F single-word partial-tag TT policy candidate

Maintained F stays at the full-key 4,720 B type-token entry. A separate
project-owned experiment replaces its preserved 4,728 B predecessor's 24 B
locked full-key entries with one relaxed atomic uint64 word: high21 key tag,
low43 unchanged move/score/depth/bound payload and low18 slot index. Full64
board/history/halfmove context formation remains; only TT identity truncates.
At TT18, storage becomes2 MiB rather than6 MiB. Each query compares the tag
and extracts payload from the same atomic load; each store publishes a whole
word. Initialization precedes worker creation. This is a probabilistic cache
policy change, not lossless full-key compression. Key bits18..42 are ignored.

The one fixed first cost is source9,626 B (-64), native18,576 B with a new
identity and whole4,711 B (-17 against its measured 4,728 B control). Whole SHA
is `90a2f0ceac618b75990ad1d924ad9f26dfbbf50628b14fd13d043e4fcf37db6d`.
The nominal9 B difference from today's full-key4,720 B entry is not a measured
composition of the two transformations. The source policy has no alias/codec
sweep or new shipping profile assertions. Fixed compiler macros and an actual
focused observation establish sizeof8 and lock-free atomic only on this local
Linux64/GCC target.

One O2 diagnostic compilation/run uses the actual candidate plus seven
inverse/complement-checked test hooks. Two writers perform40,000 stores and
one reader40,000 queries, observing only coherent whole-word values and then
joining. A constructed bit18 alias is accepted by the candidate and rejected
by the old full-key probe; a different tag misses. The original nine horizon
expectations, full64 context formation cases and three quiet roots at retained
depths3/3/1/2 pass unchanged independent minimax/attaining-witness expectations.
Startpos completes depth1 score54 in31 nodes; same-job node32 interruption
preserves that completed witness. A separate adversarial alias-bound injection
reaches an actual conflict/stopped branch while retaining the completed depth1
witness. It demonstrates defensive abort for that case, not minimax correctness
under a false cache identity. Ordinary cases have no observed conflicts.

Cost/focused receipt SHAs are
`dd650b429fbf870d0dfd09abee0ab2ead32507bf4a9cb69dd6f2678003c33ad5` /
`c8c496993708edd0787114ced7b914217cff4faac21645c3a0639402dbcdc8ce`.
The external proof index SHA is
`5ac6b6934ce41f568617e8cec8348d3f2ebecf1f2127d40460bf37cefd1781c3`.
Only four ordinary first-cost source/configuration files belong to the Git
experiment. The actual target/instrumented/reference fixture and executed
driver stay outside Git with their pins; the unexecuted driver before its
interruption-cleanup correction is preserved separately.

There is no product main/pool/wrapper execution, normal promotion, composition,
all-schedules proof, target performance/scaling or playing-strength claim.
The tag's conditional2^-21 random-alias model assumes independent uniform keys
and is not a whole-search error probability. The candidate is retained for a
later policy/resource comparison while the selected full-key baseline remains.

## B occupancy-swap first-cost rejection

A separate ordering-only SEE candidate uses one real initial make, then
geometry-only occupancy removal and a bounded32-word gain stack instead of
recursive full Board transitions. Shared attacker queries remain active; a
selected king needs a geometric destination check and terminates the sequence.
Non-king pins are deliberately ignored, so this is a different approximate
ordering policy. Its negative result is never a QS pruning certificate. The
scratch is never a valid Board after origin removal and cannot reach normal
make/search/hash/HCE/TT/learning. Promotion dominance is limited to this fixed
target-geometry model, not inherited as a legal-LVA theorem.

One fixed candidate grows source11,430 to11,487 B and shrinks native26,360 to
26,328 B, but the actual complete file grows5,357 to5,423 B (+66). The loss
closes the experiment without fixture/engine/normal follow-up. Maintained B
stays5,357 B with legal-LVA. No stack, performance, strength or semantic
equivalence claim follows from the new native. The actual cost receipt SHA is
`4db5f51b7902d3bb789ca7c68146ea771b9b48f7fd160f06af38cc9038831804`.
Five ordinary cost sources stay fixed at producing/final aggregate
`96e70424bf70f2a36ff68621c32787caafc120e922b56511112df2a19b4e5601`.
A preparation-only CRLF freeze failure remains separate; only recipe newline
serialization changes before the sole actual compile/ALONE/two strict decodes.
No alternate candidate or codec/name search repairs that measured loss.

## D full-key atomic16 TT and positive normal qualification

D keeps the entire64-bit context key and64-bit payload in an aligned16-byte
entry instead of a24-byte entry with a separate flag. Two explicit GNU x86-64
`lock cmpxchg16b` asm blocks implement a coherent pair read and one best-effort
write CAS, with memory/condition-code clobbers. All concurrent pair accesses
use this primitive. A lost write is allowed; its return is not a CAS-success
acknowledgement. The read/write contention policy differs from the former
try-lock miss/drop policy, while key identity and valid payload transport stay
full-width. The fixed TT18 allocation becomes4 MiB rather than6 MiB.

Fresh anonymous-zero TT allocation precedes worker creation, so the shipping
clear loop is removed. DEV's wait-then-clear remains quiescent. Header layout
assertions bind size/alignment16 and key/data offsets0/8. The explicit execution
profile is now `linux-x86_64-sse4.2-cx16-crc32b-v1`; CX16 is required alongside
the previous CRC32C instruction. No generic or current tournament-server CPU
compatibility is inferred from local execution.

| Form | Native before/after | Complete before/after | Packet | Header/loader |
| --- | ---: | ---: | ---: | ---: |
| scalar | 7,964 / 7,932 B | 6,108 / 6,064 B | 4,927 B | 1,137 B |
| HQ | 8,352 / 8,288 B | 6,288 / 6,253 B | 5,116 B | 1,137 B |

One first cost compiles each native and unchanged fixed21 package once. The
existing positive data-only CRC decoder helper is reused for both new packets;
complete packet-to-BCJ-to-native bytes, canaries and owned-table unmap agree.
It never jumps to the new engine. One separate positive unit compilation/run
includes the actual unchanged probe, checks literal full-key/payload and
mate/depth/bound cases, and runs two bounded writers plus one reader. All hits
carry their matching entire key/payload; misses and dropped writes are allowed.
It joins and unmaps normally. Actual CAS-drop causality remains unobserved.
A preparation-driver Python syntax error occurred before any C compile/run;
the original failure and typo-only corrected executed driver are separate.
Unit receipt SHA is
`6f5a330994a54546cf1eea9a544f87b15ae34079eada191b62892877db378d2e`.

Two unchanged CHECKPOINT loader compiles reuse the measured packets without
new native compilation/encoding or target execution. Root independently reads
all eight native/packet/shipping/audit full identities, both ELF headers and
the exact mapping/literal changes before admitting only the two new audits.
Scalar audit is6,087 B / `9e8831581ee618d9ecb99373ee8eb39c312d7a7e696ea569e1b3a56e694cc07c`;
HQ audit is6,276 B / `db6cdcfa09b94f0d9441384f5646678258d5e7cbeeaa9537ca149127f663985e`.
Strict native/model/layout and audit gates remain. The verifier adds the
all-affinity CX16 check and exact new identities; mapping/lifecycle bodies
are unchanged.

One ordinary normal builder reproduces four native images, four shipping ELFs
and two audits exactly. One selected positive verifier then passes four
shipping sessions/twelve GO plus two pre-entry observations. Actual restored
RX bytes, zero BSS/padding, original entry resume, guards/NX, persistent worker
TIDs, active workers at shutdown, only stdio, reader EOF and natural physical
exit0 are observed. SSE4.2 and CX16 are present on all eight available local
CPUs. Build/verifier receipt SHAs are
`12c7096e312e4ed3d6761da81569eb222b54f8c99556eef3bef566c203bcf1a8` /
`f4536e49cf9276a123a8954c91a12a4bfe9060cb3cd4387b597006dda017059a`.
There is no new fresh/archive execution, negative/fault campaign, all-schedules
race proof, target scaling, game/performance test, main promotion or release.

## B/C/E fixed type-token completion

The same type-presentation mechanism is now selected for B/C/E with each
family's actual namespace. W/X/Y/Z is not blindly reused: the fixed maps are
`uint64_t->D, Move->N` for B, `uint64_t->M, Move->T` for C and
`uint64_t->I, Move->T` for E. Each19 B typedef prefix is included in cost.
int16 and the private Entry typedef stay unchanged. Exact role ledgers,
MOVE's three casts, fresh ordinary/directive names, inverse and protected
complement bind these particular outputs. There is no name or codec sweep.

| Entry | Source before/after | Whole before/after | Entire native |
| --- | ---: | ---: | --- |
| B | 11,430 / 11,167 B | 5,357 / 5,340 B | All26,360 B identical |
| C | 10,656 / 10,445 B | 5,092 / 5,078 B | All26,376 B identical |
| E19 | 11,105 / 10,891 B | 5,176 / 5,158 B | All26,416 B identical |

C retains the exact later `immintrin.h` include at old byte4060; its alias
prefix precedes the first owned type. The former all-includes-before-aliases
helper precondition rejected this source before compilation. Admitting this
one fixed existing include keeps the source/map/insertion unchanged; actual
compiler/header namespace compatibility is checked by full-native equality
before the codec. This does not create a general header exception or imply a
different runtime ISA. B/E have no later include.

A separate preparation bug incorrectly LF-normalized binary control hashes.
The first B preflight failed before any compiler/codec invocation; E/C had not
started. Original source5, rejection and partial outputs remain outside Git.
The correction pins binary controls as raw bytes, while explicitly normalized
source remains text. Candidate bytes and maps are unchanged. The corrected
first costs compile/package each candidate once and strictly decode baseline
and candidate once each. Every complete native matches its own actual control
before packaging. These preparation failures are not hidden compiler retries.

Ordinary family-owned closing helpers follow tactical, signed-vector and E19
model stages respectively. They have no experiment/report/artifact input and
retain all prior guards and canonical/DEV references. Each ordinary builder
runs once, reproducing shipping twice and old DEV twice, followed by each
unchanged selected verifier's two quit/EOF sessions/eight legal GO. Exact new
whole identities, the same native images, three persistent TIDs, private-path/
helper cleanup, reader EOF and physical exit0 pass. E's DEV21 stays ancestry,
not proof of E19. Only recipe/README result metadata changes after execution;
no extra core fixture, fresh/archive execution, game or benchmark is claimed.

Final external B/C/E normal index SHA is
`ba14ee1fa96d127cbd89bacd05792f5669f65fe0f1bca00d811a4683400164f1`.
The actual build/runtime pairs are B
`f8add1c9961dfb57273c19bebc9f4b7460ef5a8473ea50a9945f08c6920aa116` /
`45f82945092d2573bc4acc6f10421a2f796e65f721c95ca924ae76c0f3849a5e`, C
`fe1ddd10928fd10f7c5b2f10e00db89e5794a32a73693576c814e3e2d17bfdf8` /
`26fc3930595ff4c5d9b5d370a71e5201db862a85d09af4c19d4c35c84377a29a`, E
`d7744f49379a1efd164fd379f3f1745cf1f21887928321c4838acd1887d4243d` /
`f17d63b577155e3e1bb403496b0a9fa37c2841cf00d4f833cee9c97c9c30757e`.

## Additional external size-analysis intake

The supplied `Rove4k_PR12_Size_Analysis.ko.md` has SHA
`c2dc4b008fa51310bf41caa1eab21e1362488304cdc9183797d525effc1736eb`
and describes historical head `a3546f1`. Its checklist is reference material;
the current request authorizes further compression and actual upstream source
comparison. Its old candidate sizes and body-erasure diagnostics are not new
maintained measurements or additive savings. At intake head `dd6c5fb`, the
maintained complete files are A4748/B5340/C5078/D6064-scalar6253-HQ/E5158/F4720.
Scope names, adjacent declarations, type tokens, B's legal-LVA/tactical
metadata, C's incremental signed8 vector, E19 and D's fixed context restoration
already have their distinct implementation and qualification records above.

Pinned external ice4 and 4ku source comparisons preserve the distinction
between general design ideas and equivalent engine semantics. In particular,
ice4 uses occurrence-weighted lexical-scope conflict grouping, rather than
liveness coloring; the current function-wide maps leave a narrower further
scope experiment possible. Their packed MG/EG evaluation and side-oriented
boards are different models/representations, not replacements that preserve
our scalar HCE by inspection. External source trees remain outside Git; their
implementation and tuned coefficients are not inputs to the ordinary builders.

Actual pinned 4kc `26e93686` and STRO4K `51ea73a3` sources were also read.
4kc's context/hardware-CRC concept is already independently implemented in D;
its original word-length/RWX/header-overlap loader is not our guarded RX/NX
restoration contract. STRO4K's cited4092-byte distribution is assembled code
with raw LZMA2/BCJ and a shell prefix using external programs, not evidence of
a4092-byte pure Rust or own-ELF entry. Its partial-fingerprint TT and GO-created
helpers also differ from D's full-key atomic16 and persistent workers.
These comparisons do not contribute new measured savings. The actual source
comparison note SHA is
`c3b6b9a93f5d2579c497e02ac0d50809a2a1c6703896c3326b1eb57d610a18f5`;
upstream implementation files and that note stay outside Git.

### Rejected F pthread-preserving futex pool

One current F4720 candidate retains pthread create/join and changes the mutex
and two condition variables to three sequentially consistent atomic words
plus private futex notification. Pending3 reserves final output: the last
worker changes2 to1, prints and flushes the result, then publishes0. Ordinary
quit/EOF and successful partial-create-prefix joins remain. Unexpected futex
failure exits2; this fatal path is not reported as successful join completion.

The old pool-related778 source bytes become585, but errno, correct syscall
declaration and explicit platform/ABI checks add299 bytes, including249 bytes
of compile-time target/ABI conditions in the submitted source. Actual source
is9464 to9570 (+106), native remains18576 with a new identity, and the complete
file grows4720 to4864 (+144). One unchanged-argv compile, one original fixed
ALONE compression and strict source/bootstrap/argv restoration complete.
There is no candidate engine/bootstrap execution, lifecycle qualification or
normal promotion. The actual loss closes this fixed candidate; the current
maintained F remains4720. A preparation-only recipe CRLF rejection happened
before compilation/encoding and remains separate from the sole actual cost.
The cost/decode receipt SHAs are
`3b625fca1710d3379839f76b9a366eb648439cde2228d6f35ecf38c607840a49` /
`1328d9d1c70dd8b92ae07122ac65ed080ef4ba4251217942da9a0b43a38b3b99`;
the final five-source index SHA is
`80292d9932c4d2950978584828de03be465d2c809e4fdbec1d05156e63f9bcc2`.

### Rust D node-observer duplicate

Current Rust D ordinary17 files are raw-byte identical to the existing
`rust-d-finite-shipping/control`17. The parser always starts with nodes0 and
does not set a node limit, while worker-local nodes still drive deadline polls.
Limits.depth and Result.depth remain actual iterative-depth/result-selection
state. Removing only global node accounting under an explicit shipping cfg is
the already measured same-input candidate: native16816 stays16816 and its
data8 packed scalar/HQ files grow11403/11762 to11404/11770 (+1/+8). These are
reused historical costs, not new builds. The duplicate is closed before any
new candidate, compile or codec run. Current source review receipt SHA is
`71e6ccab690e0cf3d211530ebc0d06561cb36ebf45b2b1e1c0a53a45f1358981`.

### F unit-window TT bound expression

F's existing bound0 gate and codes1-exact/2-lower/3-upper permit replacing
`bound==1||(bound==2&&score>=beta)||(bound==3&&score<beta)` with
`bound!=2+(score>=beta)`. For score below beta, reject2; for equality or above,
reject3. Exact1 remains accepted and empty0 remains rejected by the retained
gate. C comparisons produce int0/1, so the added2 cannot overflow and all
operands are side-effect-free locals. Requested-horizon equality/QS0, mate
adjustment, full-key coherent transport, root cutoff prohibition, cancellation
and MTD lower-bound witness ownership remain in the exact protected complement.
This is an equivalent F unit-window expression, not adoption of 4ku's depth
or TT policy and not a change for arbitrary A/PV windows.

One fixed first cost changes source9464 to9442 (-22) and the complete file4720
to4709 (-11). Native size remains18576 but its entire identity changes to
`a25b88d5f97279b6b4cbee33d5af879e543d9796b0864f6b3331869e69415f9c`;
it is not called native-identical. The whole SHA is
`2b9e91889a6c963db9bf752ad6b4ace95bc6036f342e4f0e411fb46b0488d04b`.
An independent source read verifies the single66-to44-byte guarded span,
inverse, remaining9398 bytes and all four flags across low/equal/high scores.

The ordinary `shipping_unit_bound.py` closes after type tokens, has no
experiment/AST/report inputs and is bypassed by DEV. One normal builder call
reproduces shipping twice and unchanged DEV twice. The unchanged selected
verifier executes the actual new4709-byte file in two quit/EOF sessions/eight
legal clocked GO and observes its new restored native, three persistent TIDs,
private-path/helper cleanup, reader EOF and natural exit0. Prior core receipts
remain predecessor evidence; there is no new game/strength/scaling or complete
F search-fixture qualification inferred from those protocol sessions.
The actual normal build/runtime receipt SHAs are
`7552e9b15f59441f462d24f5623669fe72bbd3401a56716489276ae22d179395` /
`150c838dc53690c47db2eba738dc66c46584437a98c74b814c69f3bfab1e2f01`;
the closed first-cost/promotion index SHA is
`1c5ee6382c59aae6bbf49c2c345da25f9970ea2100a087090a51edcb6feecfe3`.

### A bounded lexical-scope name reuse

One fixed five-declaration map reuses names across disjoint nested search
blocks. It moves the inner N first, then renames the outer best move ab to N;
sibling ordering/search locals reuse P/R and separate reduction/cutoff/
correction blocks reuse S. There are21 physical identifier edits, not a new
generic allocator or identifier search. Existing Clang18.1.1 compares269
declaration shapes and2442 reference edges before/after; only those five
declared names differ. An initial physical-offset guard rejects the expanded
PROMO(ab) reference before compilation. The corrected proof binds its exact
pure macro definition, invocation, physical argument and expanded declaration;
there is no token-paste/stringification or other macro exception. The original
guard failure remains distinct from the executed corrected analysis.

Source9476 becomes9470 (-6), its entire22672-byte native is byte-identical,
and fixed original ALONE packing changes4748 to4739 (-9). Whole SHA is
`bcc529093299e2d6654b4bf9473442995df00a6ea3ab62c31bd4bd24c75f05d5`.
The ordinary `shipping_lexical_scope.py` closes after types, owns the fixed
declaration/token/macro ledger and needs no AST, experiment or external report
at normal build time. Canonical and DEV source, verifier, resources, compiler
and codec remain unchanged. One normal builder call reproduces shipping twice
and DEV twice. The unchanged selected verifier passes two quit/EOF sessions/
eight GO using the actual new4739-byte wrapper, exact restored image, three
persistent TIDs, private cleanup, reader EOF and physical exit0. Existing core
qualification is reused through entire-native equality; the new wrapper's
runtime observations are separate.

The actual normal build/runtime receipt SHAs are
`7cd0b4cbc524230547e8bde7d7b797d26fa81f7d652f12a863753fbf33b7ceaf` /
`90e3217b7abb366cdd3d7e01a6cb65fab01ec5f77c8b877b4cc6a6cd4c6bc72a`.
The final normal index SHA is
`150ce129a20ece74d69b81dc1026df87cd3f2dd623632612111ceb1c4fbed954`.

### D EP transition sharing

EP normalization now delegates its private three-square capture/own-king trial
to existing make. A provisional EP parent has a valid side/king cache, empty
target on the proper rank, opposing pawn behind it and an adjacent own pawn.
Those facts come independently from a generated double push or DEV FEN/board
admission; already-normalized EP is not assumed circularly. The trial capture
has displacement15/17 and no promotion, so its child e stays-1 and nested ep
returns immediately. Only the boolean result escapes. Its temporary h/r may
be unfinished during outer normalization; the child is discarded and cannot
reach search/TT/history/evaluation. The private make contract documents this
exception. Existing full-key atomic16 TT, search, model, pool and loader remain.

The functional fragment shrinks by81 readable bytes; an explicit318-byte
contract comment makes board.c8770 become9007 (+237). Comments are not native
payload. Actual .text shrinks73 bytes in each form; alignment makes complete
native7932/8288 become7836/8224 (-96/-64). Fixed21 packets4927/5116 become
4865/5083 and the complete own-ELFs6064/6253 become6002/6220 (-62/-33).
Nonpacket headers/loader stay1137. Source/native/packet/whole differences are
measured separately, not added. The new make frame and extra generic metadata
work are not claimed as speed or stack improvements.

One fixed cost links each native/package once. Existing positive DATA-only
decoder helpers recover both exact BCJ/native byte streams with canaries and
table unmap, without entering the engine. A separate ordinary DEV1 unit uses
the actual old/new board sources, namespace-renaming only the control. Scalar
and HQ each compile/run once with ASan/UBSan. Both pass20 mirrored EP roots,
150 named Board/child records and26 FEN/history observations against control
and independent rule/hash/HCE/path reconstruction. Both colors, one/two
origins, pins/discoveries/check evasions and double pushes are covered. Test
layer function-entry hooks observe make/ep maximum depth2 without changing
Board contents, arguments or production code; source child e=-1 establishes
the termination mechanism. No trial metadata poisoning or escape experiment
is performed. Unit receipt SHA is
`2e21ea646a7dfddc3c55d7e95bccb6ba80278a5f44b8b72a025f2f11c446a69d`.

The first-cost24 ordinary sources remain frozen separately from that external
unit source. Its final index SHA is
`e82210b98dc5feaa58dc4140ac11a8e3cbd9817da4dff537313152a7aa8cc447`.
Git's existing LF attributes require a later newline-only pack-recipe closure:
226 CRLF pairs become LF, with identical parsed JSON and the other23 files
unchanged. Original FINAL24/producing bytes remain preserved. No code/codec
rerun or gate change accompanies this; the separate Git-final index SHA is
`9b732710e32542bcb4239dde5781985d0fb9804b1de62e6cc5250c0e5354f9c2`.

Two new CHECKPOINT1 audits are generated without target execution from the
measured packets and unchanged loader. Root reads their complete identities
and ELF headers before admitting scalar6025/
`81931ddcd89feed7f87d5849db20ab0b21150ea7c63f30b207316986ed32b658`
and HQ6243/
`e894c94a6917aaf43817792659fefb0ff0716cf1f3c66da6d1be5e25613fbead`.
Only the board fragment/comment, exact packer/verifier identity literals,
recipe and README change. Builder/fresh, loader6, native7 and verifier
function/class bodies remain unchanged; old source23 is retained externally.

One ordinary normal builder reproduces native4/whole4/audit2 exactly, followed
by one selected positive verifier's four shipping sessions/twelve GO and two
pre-entry observations. Actual restored RX bytes, zero BSS/padding, guards/NX,
new native entry resume, persistent three TIDs, active-worker shutdown, only
stdio, reader EOF and natural physical exit0 pass. SSE4.2/CX16 admission remains
the explicit local profile. Build/positive receipt SHAs are
`fed982d44a7ec06641b442135751329043a205cf438d02518c762ea5a54a0d50` /
`3786ac409f2c60e18b261d43fbbafdf07cc0a1d5ffc661770e33c47bca97382e`.
Root's final source23/native4/whole4/audit2 readback index SHA is
`852d923dc796da8037937160d9b3eb03c52f1a9899ca9af8204efa279b7900b7`.
There is no new fresh/archive, negative campaign, general race proof, shipping
stack/performance/scaling, game/strength or tournament-host qualification.

### Separate A capture-only Move-bit first cost

The next independent A candidate records capture-only classification in private
Move bit3 while retaining17-bit TT moves and decoding FROM with119. The reused
emitter argument distinguishes quiet/castle/doublepush0, nonpawn capture1,
single pawn push2 and pawn capture/empty-target EP3. Promotion eligibility uses
the pawn bit; quiet promotion retains capture bit0 and its existing ordering/
noise/history behavior. This differs from B's promotion-inclusive tactical bit.

One fixed cost changes current A9470 to9391 source bytes (-79) and complete
4739 to4727 (-12); native remains22672 bytes but has a new entire identity.
Eight exact regions/inverse and9130 protected complement bytes bind the source.
One unchanged-argv compile and original fixed ALONE compression pass old/new
strict transport restoration. That cost-only checkpoint did not qualify tag
semantics, legal children, TT17/private ABI, search/learning or runtime;
maintained A then stayed4739, with no automatic F application. The next proof had to check
actual producer/classification, EP and all quiet/capture promotions, decoded
children, text/query/witness/TT consumers and unchanged quiet ordering state.
The actual first-cost receipt SHA is
`e55a5cf1c56dad8fb852fac79cfef829f473020e2e7e912b6425ba6af3d1db85`;
final five-source index SHA is
`07443b69673554935cfdaaad7126dc745e642c5169a9db828d052eca18150bd4`.

### A capture-only bit: focused semantics and ordinary selected execution

The exact old9470/new9391 sources were subsequently included in the same
ASan/UBSan fixture, with product main renamed and never called. It invoked
actual shipping generation, make, attack, text/query, TT and one-worker search
functions. Decoded FROM/TO/PROMO and an independent mailbox capture predicate
were compared rather than requiring the deliberately changed raw moves to be
equal. Across59 admitted boards and1529 ordered pseudo moves,1421 complete
legal children and108 self-check rejections matched. Independent attack,
hash/HCE/path state and parent immutability were checked. Positive cases include
both-color empty-target EP, nonpawn quiet moves to the same EP target, castles
and all N/B/R/Q quiet/capture promotions. Quiet promotion remains capturebit0.

Actual17-bit TT move transport and same-slot different full-key misses passed.
Five fresh-TT18 depth1-to2 searches matched scores, nodes, best/text/query
witnesses and the entire normalized702380-byte Worker/populated-TT snapshot
(`83bad542e2bcb9a94e05c799c9f2119661d53748b9b4369d1d2a748026858be9`).
Only the deliberately added capture bit is removed from recorded move fields.
History, continuation and correction updates were positively exercised, as was
an actual third-repetition history. Both units exit0 without sanitizer output;
compiler warnings and all original outputs remain external. This is not a new
LMR-depth, concurrent-TT, cancellation, product-main or wrapper proof. Focused
FINAL index SHA is
`0b2f9f62327dc40b39a47de047209b3df6dc1a179577e49ffb04520ae0e1a385`;
actual receipt is
`f9766271159cacc8fe46a21fa0d96cf9702014b76f6797c8ed9309bed241ffcd`.

The ordinary self-contained `shipping_capture.py` now owns the literal eight
regions, exact inverse and protected complement after lexical naming. It has
no experiment/report/fixture dependency. Canonical readable source and DEV
remain unchanged. One ordinary builder with `--dev` reproduces2shipping/2DEV:
source9391/b4aa3453, native22672/99c729d5, bootstrap10381/11b68e9e and actual
whole4727/a288bc81. One unchanged selected verifier then passes two quit/EOF
sessions/eight GO with that exact new wrapper and restored image, stable three
startup TIDs, private-path/helper absence and physical reader/process exit.
Cancellation causality remains unproven; earlier core receipts retain their
ancestry scope. Build receipt SHA is
`814d64942d6b6db2e37e88fd79befe2fc32aeaf60d26f5304469949bddcbd61a`;
runtime receipt is
`33d100bae2ef94c97af06b9b14354aead21a648a43d8d4190159595f091c76a1`.
Producing and final metadata snapshots are separate; the A4727 FINAL index is
`ce85eb27c2e8a6bcce77fb369fa90ef91a3ec97a2d1f4c4be77be1c5473153c4`.
The later startup-only change below does not relabel this fixture or native.

### Two further cost candidates rejected or closed without promotion

An A bootstrap-only spelling candidate aliases `pthread_sigmask` and uses loops
for the same two signal installs/resets. Its template shrinks997 to925 bytes,
but original fixed ALONE makes the actual whole4727 to4730 (+3). Strict Python
and CLI restoration pass; compiler/bootstrap/engine execution is0. It is not
selected. The original template, private compiler process-group handling,
cleanup and fd-exec remain in use.

An independent Rust D candidate moves pseudo generation into an appender on
fresh, fully initialized caller-owned Moves. The current native really has a
2056-byte pseudo temporary/return copy. In the new scalar/HQ images that copy
vanishes from the generator, but a2056-byte local/return copy appears in legal;
the safe capacity guard remains. Actual `.text` grows80 bytes in each form,
complete native lengths remain16816 and raw source grows292. These exact
outputs justify closing the native-size lane; whole-file cost is unmeasured,
with codec/target execution0. Source7 controls/candidates and positioned inverse
remain external. An initial inverse-uniqueness preparation failure occurred
before compilation and is preserved; the corrected producer performs the sole
native pair. No normal Rust source changes follow. Native cost receipt SHA is
`357eea76d76b52c8277393211dce3bcd2ea34b1e873b002d4bcd3b9872137ee2`;
FINAL index is
`c219d3d3225463a359ca14826344e0c6c6d8468e02c6d6a93a1a121ecd2eedbb`.

### A/F startup-only TT initialization sharing

Both shipping entries allocate the TT with checked `calloc`, then call their
static initialization function once before creating any worker. Their key/data
fields are exact-width unsigned64, so calloc's zero bytes already represent0.
Each entry's `atomic_flag_clear` remains explicit. Only the duplicated key/data
zero stores and unnecessary braces are removed. The functions are now admitted
as startup initialization, not reusable reset; DEV bypasses this stage and
retains its original quiescent clear/new-game path. Full-source, type, sole
caller/order and inverse/complement guards bind this narrower contract. No TT
layout/probe, full-key, search, clock, pool or resource policy changes follow.

For A, a self-contained stage after capture changes source9391 to9370 (-21)
and complete4727 to4716 (-11). Entire native remains22672 bytes but changes to
`47ec496697134d91a4efb71e14441e5a542df93278c64a2dfdcf1e7eec0de9dc`;
whole SHA is
`928438fdbe0ea0c83e5b03b00c1a7e8aed2a94d0df43976364b85fb439dd5678`.
One ordinary `--dev` build reproduces2shipping/2DEV, and one unchanged selected
verifier passes two sessions/eight GO with the actual4716-byte wrapper. Build
receipt SHA is
`bd98edca98f6903f567c02dca89e3210d38f061dc58c1c028709842180eff1ed`;
runtime receipt is
`c8888416a51f4061a51c7822348c42c1b9799199add629092e7106e6313ba7d2`.
The final A4716 source/normal index is
`400cb9016830d02f643beb5ed7f60047270e94a8e371864699cdf00b2f2cf07e`.
The preceding focused capture fixture remains bound to source9391/native99c7;
this new wrapper execution is recorded separately.

F was measured independently from the current unit-bound source, without
importing A's capture-bit change. Source9442 becomes9422 (-20), complete4709
becomes4702 (-7), and entire native18576 changes to
`a528c8ac63976666599d4d5f5e5c8510b41df73f9c857d5919be323375dd9d0a`.
Whole SHA is
`359313ad9a6d63d78e2207044905dbfb4adee80338d0334945ba37508170935e`.
An initial cost driver incorrectly borrowed A's default ALONE settings and
failed exact F control after its sole successful native compile. That incomplete
receipt stays preserved. A pack-only correction uses F's unchanged fixed
BT4/64MiB/nice32 recipe, restores old/new exactly and does not recompile.
One ordinary `--dev` builder then reproduces2shipping/2DEV, followed by one
unchanged verifier/two sessions/eight GO. Build receipt SHA is
`2a0363b4ced6fd880cb3e27242985b90ec2a3af9bf8980daf2022a84d4ffe0bc`;
runtime receipt is
`390a7657598c9a267489fdff71e625df8ae0585357aba5d68dfc213969b345d1`.
Final source25 manifest SHA is
`b221a21b42032800d797323ab3c88e5529f8bb0259c22955b6fc839c8a9e2f6d`.

Both selected executions verify the exact restored native image, private
directory/helper absence, stable three startup TIDs, legal bounded GO, active
quit/EOF completion and reader/process physical exit0. DEV bytes reproduce but
DEV engines are not rerun. Cancellation causality remains unproven. Producing
inputs and final README/recipe metadata are preserved separately. There is no
new fresh/archive, broad core/race proof, performance/scaling, game/strength or
tournament-host acceptance. All six complete-file gaps remain open.

### Separate D NUL-token representation: fixed cost only

A new external candidate replaces private pointer/length spans with mutable
NUL-terminated tokens. Nondigit amount lookahead must remain nondestructive,
digit-leading invalid/overflow input must consume its complete token, and DEV
FEN must locate its moves boundary without destroying field spaces. Read-line
draining/EOF/EINTR, clock limits, position transactionality, publication and
startup/shutdown remain protected source regions. This is a new representation
cost, not a repeat of the earlier GO-arm or private-signal alternatives.

Six exact regions and seven inverse-preserved gaps change runtime source by
+71 bytes. The sole scalar/HQ compile pair reduces `.text`31 and native32 bytes
per form, to7804/8192. HQ now fits exactly two RX pages with BSS at402000 and
the same43 BSS pages. An old page-class equality guard rejects this new layout
after both successful compiles; its incomplete receipt stays preserved. Root
reads back the actual four native/linked files and admits only those two new
hashes/entries/layouts for external cost packaging. The old guard is not
generally weakened, and the compilers are not rerun.

One unchanged fixed context21/BCJ codec and own-loader pair produces packets
4866/5067 with1137 nonpacket bytes each. Complete scalar6003 is1 byte larger;
HQ6204 is16 bytes smaller than maintained6002/6220. Whole SHAs are
`2c914e2fd88caae812df55ab4e5707580c7e85562f2842c088c173d742fbad06` /
`33407e1a85327ade6c67cf6c1f68cbfc4dd4fff7c87cd65fad5b3b2880116cbe`.
The existing positive DATA-only decoder restores exact BCJ/native bytes with
canaries/table unmap; it never enters the generated engine or loader. No
protocol fixture, product main, worker pool, selected audit/runtime or normal
promotion follows. D6002/6220 remains maintained. This small HQ cost win is
not yet a semantic, resource, performance or tournament qualification.
The external fixed-cost FINAL index is
`09063837468e0997398aac1407c07eb8aeb725e0bd4f23ab1670135ce2c71d63`;
actual cost receipt SHA is
`eed34e32e0ab3265351f08aea2b2182996f131c8a4cc1fa78fa23a6a5bef23ae`.

### F fixed global function aliases: native-identical ordinary promotion

A separate namespace study starts from exact F9422/109cb9df after startup.
It assigns unique one-character aliases to28 owned two-character functions,
with104 physical declaration/reference edits and no local renames. Names
declared anywhere in each referencing function are conservatively blocked;
this does not assume nonoverlapping live ranges. Four functions remain as-is.
Main, objects, types, members, header/external references, directives and all
opaque text remain protected. Eight owned definitions have C external linkage;
their names are private to this standalone program, not a library symbol API.
The fixed ice4 source is a reference for occurrence weighting and scope
conflicts, but no implementation or grouping algorithm is imported.

Two libclang semantic parses, including internal preprocessing of pinned
headers, give zero diagnostics and exact declaration/type/layout/reference
projection. The fixed proposal/inverse produces source9318/e280d859 (-104).
One original-argv native compile is entirely byte-identical to the maintained
18576/a528c8ac image, without a metadata exception. Original fixed F ALONE
packing produces whole4692 (-10), SHA
`45ccd4d0e077e7bd085be3137a852354bbfc494ed80a4d5aa182089fc590f827`.
Control packing and old/new strict Python EOF/CLI restoration pass. These
results do not establish an optimal namespace map or a new target-toolchain
qualification. The source/cost index SHA is
`9bac5258d0d32c1c11061f0e8e3bb36b2856f91ceef814c56665a5af51e44c3e`.

Ordinary `shipping_global_names.py` replays the owned literal map after startup,
with exact input/output, token inventory, inverse and opaque/directive guards.
It needs no AST, experiment, report, old artifact or external engine source at
build time; DEV bypasses it. An initial Python regex delimiter preparation
error was found statically before normal execution. Its source26 snapshot is
preserved; only the Python delimiter changes in producing v2, with no C
candidate change or normal retry.

One ordinary builder `--dev` reproduces2shipping/2DEV. One unchanged selected
verifier passes two quit/EOF sessions/eight GO using the actual4692-byte new
wrapper and exact old native image, stable three startup TIDs, private-path/
helper absence and reader/process physical exit0. DEV bytes reproduce but
DEV engines are not rerun. Cancellation causality stays unproven. Build SHA is
`2e2ce0048f1d56402a27c5b5e327b1c229bb85feca6407c514266bd9fda593a9`;
runtime SHA is
`c8463dcd28811ba86474e9fed02770dfc4f28cc4f5b652684c7438114120a85b`.
Final source26 SHA is
`81840d0436bb8cf35928c73ca7e7c01a3b465874b7e8aeaf654087e70e9bc621`;
normal FINAL index SHA is
`c49531f8f56e67426b4f903da5479ff3acd7b5167933ad629a24b0e19cf70e7c`.
Post-execution README/recipe metadata is separate from producing inputs. No
other core, policy, resource, codec, bootstrap or canonical DEV path changes.
The independent F capture-bit proposal still has its own source/cost/proof
identity and cannot be combined by adding these measured byte reductions.

### Separate compact F material/noise policy: measured cost, not selected

The plan permits F to use a smaller fixed evaluation and ordering model while
retaining its independent MTD(f), converged bounds, attaining root witness,
last-completed result and SMP. The richer full F remains maintained. This
candidate does not remove A's required history/continuation/correction or
change another family's implementation.

One separately frozen `F-MTD-MaterialNoise-v1` candidate starts from F9422,
not the newer namespace source. It uses incremental signed material with the
original basic piece values and retains TT/capture/promotion ordering plus
the existing stateless worker/move noise. Positional HCE terms and optional
persistent quiet learning/correction are removed. Repetition keys, full-key
coherent TT, exact requested horizon, QS, rules, cancellation checks and MTD
control are protected. This changes evaluation and finite-time move choice;
it is not lossless compression or an old-PV/strength claim.

The exact 17-role edit and 18-gap inverse gives source8779 (-643), SHA
`a4f3dafc7a99ac180d582350a34ec41a78e6f51f6ec202bc1e88dcda8fd24323`.
One unchanged compiler invocation produces native18576 with a new identity;
its .text decreases652 and .bss70304 bytes. One original fixed F ALONE encode
gives complete4413 (-289), SHA
`f4ccaceada152bdf7ad8a25ba7b4ae87598333b1480a2becddbfd7b697b7e821`.
Strict Python EOF/source/argv and CLI restoration pass. This is still317
bytes above4096. It is not composed with either namespace or capture changes.
No target, bootstrap, pool or unit executes in this cost receipt. Final cost
index SHA is
`c7eaffea2f1b7dc7e225b9c9a3ba1274febeb5b231a73132f9d34378dd26b0d4`;
root source/artifact readback SHA is
`f1664c5968b8f2db8cb147038717664b5ccf4301a9c78789ab31be2a502d66ce`.
At this cost checkpoint focused new-model functional checks are still pending;
the candidate does not replace the current selected F table or qualify a 4 KiB
entry. Later functional/policy evidence is recorded separately below.

### F capture-only bit composed with global aliases

F's private 0x88 Move representation now has its own capture-only proposal:
FROM119 removes bit3, emission distinguishes pawn pushes/captures from other
geometry, and actual capture consumers read that bit. Quiet promotions retain
capturebit0 and remain tactical through PROMO. The make-only raw EP constructor
does not enter a classifier. F's quiet move-keyed noise/correction stays exact
because quiet raw moves do not change. This is separate from B's
promotion-inclusive tag and from A's source/proof.

The focused old/candidate ASan+UBSan pair runs unchanged actual board,
generation, transition, TT and search functions plus an explicitly bounded
depth2 projection of the MTD driver. The projection changes only its name,
loop upper bound and observer insertions, with exact inverse. It is not
execution of byte-identical product think/main or a selected wrapper. Coverage
is59 boards,1529 pseudo moves,1421 legal children,108 king rejects, both-colour
EP/castling and all four quiet/capture promotions. Actual lower/upper probes,
completed depth1/2 scores and attaining moves agree with a no-TT minimax/QS
control; that control shares actual gen/make/raw HCE/dead-material functions,
so it is not an independent full-board oracle. Matching-depth cuts and deeper
cached-to-shallower full research are observed. Persistent actual quiet
learning/correction is exercised without fake TT payload or witness injection.
Only bit3 in actual best/TT move fields is normalized;837040 bytes of remaining
Worker/TT state and semantic transcripts match. All four compile/unit
processes exit0 and are reaped. Proof index SHA is
`e73c364d83a5ba933989f7540d832bb0359430bc1721711e1676bc5e63e9000f`;
root actual-input/result/state readback SHA is
`b264517c9bc4eb3820faed1d8d55e05b2c627ee17958a87569f0d88c61cfa6ca`.

Composition is measured from actual current source9318/e280d859. Its eight
capture-role fragments use the current emitter/classifier aliases; old AST
offsets are not replayed. Removing the classifier also removes four alias
occurrences, so the raw reduction is76, not the independent candidate's80.
Source9242/61e0f5c7 produces complete4681 (-11 from4692), SHA
`4596f11ad8ccaea7adc6d52a3de1b3f8c0b4c37295abb37fd2244897c3faf03d`.
Entire18576-byte native SHA
`bb6f0fa9e45615cbc0651d23dfee86bc59274c406d25e0ba0968da48668976bc`
equals the independently measured captured image and differs from uncaptured
a528c8ac. Original compiler/codec/prefix, exact source inverse and strict
old/new restoration pass. Cost FINAL index SHA is
`640ffe62ddfea8959b157e4026829b5ef30b2a1a732b430784734ffc3bf9b529`.
The focused proof, native identity, and ordinary selected execution have
separate scopes; no deltas or runtime receipts are combined arithmetically.

Ordinary `shipping_capture.py` owns this fixed eight-role map after global
names; normal builds need no experiment/report/AST/upstream inputs. One
ordinary `--dev` build reproduces shipping and unchanged DEV twice. One
unchanged verifier executes the actual4681-byte wrapper in two quit/EOF
sessions/eight legal GO epochs, verifies the new restored bb6 image, three
stable startup TIDs, absent private paths/helpers and reader/physical exit0.
Build and verifier are reaped, and observed TIDs are absent on readback.
Cancellation causality remains unproven. No new core fixture, DEV engine,
fresh archive, game or performance run is claimed. Build SHA is
`7d4c14f1e23d480877c227f9c50149cbc9828c2a47d59c34745f13bff2abd454`;
runtime SHA is
`6c5fc8a16e03cd41a6a6797e3f0a723d1fa1f1c24b7b8be1718cb24a4164b667`.
Final normal index SHA is
`86f017cd45175b119313fec83aeb889dd06dda4dc6113febb84f8f5a98ff58f0`;
root source/artifact readback SHA is
`bb33643cf62cbb0cb8753cba2a8af89e4ea49ef919ba26714152604571607bba`.
Producing source27, predecessor source26 and prior globalnames receipts remain
separate; only recipe/README completion metadata changes after execution.

### F bootstrap module aliases: complete-file loss

One fixed `signal`/`subprocess` module-alias proposal preserves the binding-
normalized complete Python AST, embedded C source, compiler argv and all
signal/process-group/TMPDIR/fd/unlink/exec paths. Imports add10 raw bytes and
receivers remove97: template1006 to919, bootstrap10241 to10154. One fixed
original ALONE encode instead grows whole4681 to4682 (+1), SHA
`9cd42414ede788b73f71d37512e991bbd3ea6fe5b208b192e8f4449584644e5d`.
Control/candidate strict decode passes; compiler/bootstrap/target execution
and normal/Git changes are0. Receipt SHA is
`9ce4bcd1122e0f118144a4aaa04a01a9fb94bb7ef75115c9547f0713392003a1`.
The candidate is rejected without another alias or codec sweep.

A separate source-only shell assessment does not justify317 bytes of whole
savings. Python's fixed983-byte code is currently compressed together with
the source. Even an incomplete shell outline would grow uncompressed prefix
77 to238 before safe signal/group publication, cancellation and physical wait
code. FD-based unlinked exec also changes inherited descriptor and argv0
contracts; a parent-shell design adds a resident process and active private
executable path. No shell candidate is built or run. A source-only compressed
stream or its difference from the current whole is not removable bootstrap
overhead or a submission lower bound.

### Independent A/B/C/E global-name maps and A ordinary promotion

The current four shipping sources are analyzed separately, including their
actual compiler flags and pinned headers. Frequency-first function aliases
respect conservative referencing-function scope conflicts, existing one-
character functions and all opaque/directive/header tokens. There are no new
local-variable renames. Exact inverse, declaration/type/layout/reference
projection and remaining physical tokens pass. This is a fixed-source binding
argument, not generic C equivalence, optimal coloring or live-range reuse.
A uses2 semantic parses; an initial F-only length eligibility mistake in BCE
is preserved before the corrected comparison, for3 actual parses per BCE.
That incomplete result is not reported as no compression opportunity.

| Family | Source before/after | Physical edits/functions | Complete before/after | Native observation |
| --- | ---: | ---: | ---: | --- |
| A | 9370/9265 | 105/28 | 4716/4690 | Entire22672-byte image identical |
| B | 11167/11009 | 46/12 | 5340/5279 | Unstripped image changes; metadata review separate |
| C | 10445/10305 | 37/10 | 5078/5036 | Unstripped image changes; metadata review separate |
| E | 10891/10755 | 36/10 | 5158/5118 | Unstripped image changes; metadata review separate |

Every complete control reproduces with its own unchanged compiler, template,
prefix and fixed codec, including C's actual -mavx2. Each candidate has one
compile and encode with strict old/new restoration. These source deltas do
not predict codec gains. At this checkpoint the BCE measurements still require
ordinary promotion and allocated-section/symbol/layout review, recorded below; full
native identity is not asserted for them. A's capture-only tag/PROMO lexical
bridge, B's promotion-inclusive OR tag, C's actual XMM eight-lane madd/hadd2,
and E's current19 parameters and five-feature ordering remain protected.
Source-only final index SHA is
`8daad35c83b343a1d58ceff65b4f7c2bb98843ab03a6bae1b667b41ad754f1fa`.

A's ordinary `shipping_global_names.py` replays its own28-function/105-span
map after startup, with exact source/inverse/token guards and no external
analysis/runtime input. Two unmapped functions remain. One ordinary --dev
build reproduces2shipping/2unchanged DEV; entire native remains47ec4966.
Source9265/06ca0bc2 and complete4690, SHA
`c72f691a64c4813e4c988a5f5b3b7ddfa069c3e936ba4756862eb090eb588d78`,
are executed through one unchanged selected verifier: two quit/EOF sessions,
eight legal GO epochs, stable three startup TIDs, absent private paths/helpers
and reader/physical exit0. Build SHA is
`228cdb10e989005f72e0e22d38abae01c6c5d9816c20d8a0b9da5b4d0bd16186`;
runtime SHA is
`7d68692df6dad32647e67ddb898eeb775337a46b4812a28b06435361121c3881`.
Final normal index SHA is
`130c675f0ea2a8805c0986be1fb545dc6dc1b68673233614bfc3e3e3b30c3fd8`;
root actual source/output/receipt readback SHA is
`1c2652c14331ade61cf9cca8edcc126929ed83ca9e573ff82f4d0794a9581eeb`.
Producing and final source26 differ only by completion metadata. An external
copied metadata label is corrected with the original preserved, without a
source or execution change. Cancellation causality remains unproven; no new
core, DEV engine, fresh archive, game or performance execution is claimed.

### F decode-once UCI coordinates: source-only closure

Current selected F parse is164 source bytes; text remains183 bytes because
bestmove output needs it. Parse already makes a selected legal child only
once. Removing its local text buffer/call saves20 raw bytes, while a direct
coordinate/promotion matcher must add exact4/5 length, a..h/1..8 and lowercase
NBRQ-language validation. One straightforward defined-C spelling of that
validation/pack is247 bytes, giving local raw+228 after the masked comparison.
This is not a minimum-size proof or a whole prediction, but provides no
defensible gain for constructing a candidate now. A future version must
match geometry excluding only capturebit3 and still return/make the actual
generated tagged move, preserving NULL fallback and transactional admission.
The older tiny-protocol bundled rewrite's Awhole+240 is not falsely assigned
to this standalone F idea. No candidate C, compile, codec or target runs.
Source-only index SHA is
`a080105a2f04e7f668ab26599aed6eaaddc3bbc04e789846d6ff4c7d78d375d8`.

### B/C/E namespace: bounded ELF review and ordinary promotion

The three new unstripped native images are not byte-identical to their
predecessors. An explicit read-object comparison confirms all26 allocated
section geometries and contents except the separately pinned build-id note;
text, data, relocations,30 dynamic symbols, entry and13 program headers match.
All symbols under only the exact owned STT_FUNC map preserve binding, type,
visibility, address, size and section. Physical symbol/string indices may
reorder. Each declared PT_LOAD file difference is exactly one byte at ELF
e_shoff offset40 and20 build-id descriptor bytes at888; there is no blanket
metadata exception or whole loaded-image equality claim. Review SHA is
`4f80b574c9bc0af5c5f7f16a5ba4f5e29601edad11e0856fb34cb099be353cc1`;
root frozen input readback SHA is
`4a70be786fdc47732288fda200496f47551bd176d6046026b72f160064c6dc3f`.
This source/ELF review is separate from runtime acceptance.

Each ordinary builder now has a family-owned fixed global-name stage after
type tokens, with exact inverse, complement and protected token guards. No
AST/report/upstream source is a build input, and DEV bypasses the stage. The
three ordinary --dev builders reproduce6shipping/6unchanged DEV in total;
strict exact new-native/output pins remain enforced. The three unchanged
selected verifiers execute the actual new wrappers in6quit/EOF sessions and
24legal GO epochs with exact restored images, stable three startup TIDs,
private-path/helper absence and reader/physical exit0. All six outer commands
exit0/reap, all18 observed TIDs are absent and no retry/forced cleanup occurs.

| Family | New native SHA-256 | Complete file SHA-256 | Normal build / runtime SHA-256 |
| --- | --- | --- | --- |
| B5279 | 7fcfab6f5933f5a945ee7841a54204fd00bb9b3fa9caec23d96d4455a7b9e998 | ac675d1954d10ead1a3df1fd33426aa8178118cccce5bc4d81abdf12c77e6f3a | c90599c9 / 85fb0293 |
| C5036 | afa5b0bbc81a232d6c1600f486438235d97655e966f8ac6d50f4f6e34abacad4 | 18caf239012ad04552def951b2e77a72f2ac4f486996b28a8fbe268857d19c65 | 65ab2043 / 9e5d89fd |
| E5118 | 2882e45f06e6604bb50ab00269a04e1febca65f590a523c490b3f8267c400734 | 3d90f959ae9a41cac62f7d8e5fb67c8a9e7f6dae4059df344f6c16a8b8b75df2 | a1d7b963 / e92b3ba7 |

The full receipt identities are in each maintained recipe/README. Normal
FINAL index SHA is
`7b3d98645023a47f83a951bf896b9c809aa22e508342c136b34038480ae7dfcc`;
root actual source/output/receipt readback SHA is
`e63c51c6869a0d5c1ad3786ad8cd304b45be9e07b0b09cb962682b16917a136f`.
Post-execution recipe/README completion metadata is separated from producing
source26/27/24. No canonical model/rule/worker/codec or verifier changes;
cancellation causality remains unproven. These are new package execution
receipts, not reruns of core/DEV/fresh/game/performance campaigns.

### Opt-in F-MTD-MaterialNoise-v1: new-model proof and ordinary entry

This fixed C alternative is now maintained beside default full F, without a
runtime UCI option. `build.py --policy material-noise --dev --out <absolute>`
selects its own exact source/native/bootstrap/whole expectations before
freezing inputs. The fixed17-role/18-gap helper branches after source9422
startup and before full-F aliases/capture. It does not combine their deltas.
Full F's expected values, qualified receipt, compiler/profile and canonical
C/Rust remain unchanged; source9242/61e0 full generation is checked twice as
part of the alternate build. Its DEV output is the unchanged full-reference
diagnostic form, not material-model DEV coverage.

One ordinary O2 function unit checks12 legitimate roots,152 full legal children
and13 material values against independent rules/material, with4castles,
2EP and both colours' four promotions.24 zero windows and17 actual MTD jobs
produce78 probes/39 completed depths with bounded quiet-frontier independent
minimax, interval and attaining-witness checks. Only the actual driver's
depth ceiling and two observation hooks change; exact inverse preserves
actual claim/search bodies and real clock/deadline handling. A real-deadline
job retains its last completed depth4 while depth5 is unfinished. That
deep job's value/attainment is not independently solved, and stop causality
is not separately instrumented. This is single-worker function evidence,
not product main/pool/restoration, arbitrary frontier or strength coverage.
Proof FINAL index SHA is
`6fa0a079a13089d9c87690e0a770bb4a3f42383295ec7b5cf6e3436240a694dd`;
root actual source/projection/result readback SHA is
`17887497c949c22c356e09e5b9e4f8e22494a5435cfc0eb5ba0d227a8e4ecb6e`.

One ordinary alternate --dev build reproduces2shipping and2old full-reference
DEV source/native images. Source8779/a4f3dafc, native18576/468453a0,
bootstrap9778/57fb4a19 and whole4413/f4ccacea exactly reproduce first cost.
Because the unchanged verifier reads its sibling recipe, the builder freezes
its exact source and two pinned test helpers under
`<build>/selected-verifier/`, beside a deterministic effective selected recipe.
It records both ordinary/effective identities. The unchanged relocated
`engines/compact/tiny-entry-f/verify.py` then enforces the alternate's exact
literal expectations; no expected/native check is waived. Qualified model
evidence references the new material unit rather than old HCE/learner proof.

The actual4413-byte wrapper passes2quit/EOF sessions and8legal GO epochs,
exact restored native identity,3stable startup TIDs, absent private paths/
helpers and reader/physical exit0. All outer commands are terminal/reaped,
forced cleanup0. Build SHA is
`da69bbebdeea3a35627f03f396f5a98859ecf1cf6d12b88373e3b14c027befcd`;
runtime SHA is
`a9da85a402152ffeed34abdfd7f65af23386659898450b30be10f1dd16943c0c`.
Normal FINAL index SHA is
`696742bcdc255ee61ee55b52aabfc6f3f5a83afa0aa1ae9016afb1260ba69e8b`;
root source/output/default-contract readback SHA is
`d31adac03cdaafb2fd9e2578453547ae59d20c6fa425d30f91c559048622c649`.
Producing source28/recipe are preserved separately from final completion
metadata and the restoration of old JSON Unicode spelling. CI explicitly
builds and runs this optional policy alongside the five default source entries.
No full-reference strength equivalence, matched Rust material policy, games,
performance/scaling or <=4096 entry is claimed. The richer full F is retained.

### Material-policy namespace: fresh binding map and actual4402-byte entry

The material model removes functions and changes references, so full F's old
namespace map/offsets are not replayed. Two fresh semantic parses of exact
source8779/a4f3dafc preserve declaration/type/reference projection and79-header
closure. A new29-function/102-span map has no local, macro or opaque edits.
Exact inverse/complement gives source8677, SHA
`dd1599d4d414107383fd534701c3c7e58a4eb861a47ab174a405f7a8cc64335e`.
One unchanged compiler invocation preserves the entire18576-byte material
native468453a0 without a metadata exception. One original F ALONE encode
gives bootstrap9676/4815a264 and complete4402 (-11 from actual4413), SHA
`10c5e2d49b1024a243f9e8252a0d34d9a7a567e9e025ded633cb29467e72b78e`.
Control4413 and candidate strict EOF/CLI/source/argv restoration pass. Cost
FINAL index SHA is
`6e33865c134c5a7ed64355952db933a941fb5c0dc7110646414dd17a88578c7e`;
root source/proposal/cost/output readback SHA is
`6587d9f2c4917e247ce8bb520690edd736e023a54bc04bc6d04529f845526cbe`.

Ordinary `shipping_material_names.py` owns the fixed map after material policy
generation. Default full and DEV bypass it; the model helper and old4413
positive/unit/normal receipts remain separately frozen. One ordinary
--policy material-noise --dev builder reproduces2new shipping/2unchanged
full-reference DEV. One unchanged effective-recipe verifier executes the
actual4402-byte wrapper through2quit/EOF sessions/eight legal GO, exact new
restored material native,3stable startup TIDs, absent private paths/helpers
and reader/physical exit0. Outer commands exit0/group-absent, forced cleanup0.
Build SHA is
`09826d33357321cd5cc58ef05f5e509213e89cbacc718ed04972704ab54bdd87`;
runtime SHA is
`41a6f437e766b3f7528533220e9200269d3d443d6e50ae122d2b42a69fa1f2f5`.
This reuses the new-model function proof through exact source/name and entire
native identity; it does not rerun or relabel that unit as wrapper evidence.
Normal FINAL index SHA is
`eb042bd2b668640247f61048fa0190994cee438f4d7270eacc7af158602b43e8`;
final source29 SHA is
`13f6bcead982110e68973e3350de04c1755c0454631c902e0e4542d44912247a`;
root current source/output/default-contract readback SHA is
`26865674fce5c45e74c950a343f8f486161de75971fa14baf98edb29bc2a3abb`.
Producing29, predecessor28 and old4413 effective recipe remain immutable;
post-execution changes are README/alternate completion metadata only. No
additional core/DEV engine/fresh/game/performance or negative campaign runs.

### Material-policy capture representation: actual4386-byte entry

The material branch now has its own seven-role capture-bit transform after
its function-name map. It uses the current emitter/classifier and omits the
absent correction tail; full F's offsets are not replayed. The exact inverse
and protected complement bind source8677/dd1599d4 to8602/3752a0c7. Capture
bit3, FROM119 and the unchanged17-bit TT move retain all four promotions,
castles and EP, with the raw EP trial remaining make-only. Material values,
quiet noise, TT bounds/horizons and MTD driver remain unchanged.

One old/new ASan+UBSan function pair checks59 boards,1529 ordered pseudo moves
and1421 legal full children against independent64-square rules/material.
The bounded independent minimax also checks12 completed depths and attaining
witnesses in each form. Normalized Worker/TT state is byte-identical after
normalizing only private Move bit3. This is function evidence, not a product
pool, arbitrary-search or strength claim. Adapter preparation errors were
preserved and corrected before compilation. Proof index SHA is
`e9c88f93b578c77cdfb2faf2812d6040ac6437d786c14cfdd4cb98b1453bf7e6`.

The ordinary selected --dev builder reproduces the new shipping source,
native and complete4386-byte file twice, plus the unchanged full-reference
DEV twice. The unchanged selected verifier runs the actual new wrapper in
two quit/EOF sessions/eight legal GO epochs, checking restored native identity,
three stable startup TIDs, private-path/helper absence and reader/physical
exit0. Cancellation causality remains unproven. Full/default F and its
qualified receipt are preserved. New native SHA is
`c882ff2ae11ec177f96542fa13db84e611a27572a21b79b93d53edc1b45652f6`;
whole SHA is
`e6d8e5e982659de7d5e4528976420f5d5881620cbd198910802d7cee368f808d`.
Build/runtime SHA values are
`3852c728dd5bd77e2d1d707d11bbbb1ea6fa610370fdf6afb0fd6d71e971a086` /
`9f5a0baff79b69adb56cf4310ded5ae82a3795cd3c3ff3d4b9a2cbbb3dfe382c`.

### Continued external-source comparison and separate TT policy cost

The supplied PR12 analysis is a historical a3546f1 snapshot and reference
material. Its individual savings are not added to current results. Upstream
trees and generated outputs stay outside Git. The pinned
[ice4 renamer](https://github.com/MinusKelvin/ice4/blob/2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19/minifier/renamer.rs)
groups identifiers by occurrence count and scope conflicts; it does not prove
variable liveness. The pinned
[4ku TT/search](https://github.com/kz04px/4ku/blob/203ddd4bf9b331851c796d8b5d57eac08f6e6c18/src/main.cpp)
uses16-byte full-key entries, a particular bound enumeration and depth>=
cutoff. Those conditions are not interchangeable with Rove's exact-horizon
TT. Current B already uses legal-LVA ordering; the old exact-SEE-to-LVA saving
cannot be counted again. The pinned
[4kc loader](https://github.com/GediminasMasaitis/4k-dot-c/blob/26e936860c8da80de73ea3041ccade96ba8112a3/loader.asm)
uses a16-bit restored length and RWX header/code overlap, so its loader size
does not establish the cost of Rove's own ELF contract.

One separate F policy cost removes score/depth/bound TT reuse and stores only
a full64-bit position key and Move under the same coherent try-lock. TT moves
only rank generated members; every search bound is recomputed. This permits
removing the TT-only reversible-path field while retaining actual repetition
history and halfmove/draw checks. The record becomes16 rather than24 bytes.
The MTD driver, unit windows, convergence/conflict handling, attaining witness,
last-completed publication and persistent pool remain. This changes search
information and may change completed depth/strength; it is not lossless
compression or a replacement for the full-bound reference by assumption.

The first policy-only source is8340 bytes (-337 from8677) and complete4234.
The actual combination with capture representation is8265 bytes, complete4223
under the original codec; a bounded42-encode comparison gives4217 with
lc0/lp0/pb0/BT4/nice32/dictionary64MiB. The6-byte codec change is measured on
that exact combined source. Whole SHA is
`e37761cffeaa6bcf2e72d4f8aa094a6b871f70165ba42b5c0a7b9ec27e0ff26f`.
These are compiler/codec cost results pending functional and ordinary-entry
qualification;121 bytes still remain above4096. No game, performance,
scaling, training or AWS run is represented by these costs.

### A continuation slot reuse: actual4689-byte entry

The successful make path already computes the moved piece's continuation
slot. On a quiet non-promotion cutoff that piece is identical to the source
piece, including castling, so the learning update reuses the existing local
instead of recomputing the index. Only one20-to11-byte span changes; source
9265 becomes9256/c5e2d299 and the actual complete file4690 becomes4689.
All A HCE/history/continuation/correction, rules, PVS/QS/TT and SMP remain.

The new native has the same22672-byte size but a different code identity;
no native equality is claimed. An actual-function old/new ASan+UBSan pair
checks five quiet learning cases including king/both castles and five
excluded promotion paths. Full learner arrays, completed result, best move,
node count and before/after update observations agree. The normal --dev
builder reproduces two shipping/two unchanged DEV images; the unchanged
selected verifier runs the actual new wrapper through two quit/EOF sessions
and eight legal GO epochs, exact restored image, stable TIDs and physical
exit0. Cancellation causality and broader performance remain unproven.

New native SHA is
`2190f140858effe734abacac7b03b5794ba5e4d0677620a4da50e170016eaecb`;
whole SHA is
`e1e3386c21412c1530a5f9c747679312661243fe522db33eb437728bc5b63749`.
Normal build/runtime SHA values are
`da911e6bd262fac92809b384ec3052e207e963478794ce5b89fc87de449a69b1` /
`24c67e8cee5dd46b734f4086d1ff3931a0b443e97b4183a96c7d1127819054c8`.
Normal index SHA is
`e76410ea895c6081fe0fa0ffbbd75823a88562d12aa81ea08865a26578bbed6f`.

### F move-only TT: positive function proof and actual4217-byte entry

The separate `--policy material-move-tt` is now a maintained build selection,
without adding a UCI option. Its fixed eight-role/nine-gap helper consumes
the8602-byte captured material form and produces8265/c858083e. Full F and
the existing4386-byte material/noise policy remain separate, unchanged
references. Every selected shipping generation checks both reference source
identities; its DEV remains the unchanged full-F diagnostic form.

An ordinary O2 function unit includes the actual new probe/claim/search and
only projects the driver's depth ceiling and two observers. It checks the
16-byte coherent record, key0, zero-as-read, full-key slot collisions and busy
misses, plus a bounded two-writer/reader exercise. Twelve roots/152 children
match independent rules/material, including EP/castles/four promotions and
the remaining Board state/hash. Twenty-four windows and17 MTD jobs produce
78 probes/39 completed depths with guarded independent quiet minimax,
interval and attaining-witness observations. Reused move-cache cases retain
different halfmove and actual threefold results, dead material, mate and
stalemate. A real-deadline job retains depth4 when depth5 is unfinished;
that canceled job's deep attainment and stop causality remain unproven.
This is bounded function evidence, not general SMP/strength equivalence.
Function result SHA is
`131de9b7eccfaf063d55e8fcebf16b37aa6872bf3937a10267c5aec511d13661`;
proof index SHA is
`23a2e404ecf96b3d3ab165aa77b64bf31f4a3e7021fca3c84c443d72b560c2fb`.

The ordinary builder reproduces shipping twice/full-reference DEV twice and
freezes the unchanged selected verifier beside the effective exact recipe.
That verifier runs the actual4217-byte wrapper through two quit/EOF sessions
and eight legal GO epochs, exact restored native18576/dbbe4984, stable three
startup TIDs, private-path/helper absence and reader/physical exit0. No
expected-image gate is waived. CI explicitly selects all three F policies.
Build/runtime SHA values are
`0bd6316dd9add8d0b53f1094c6dd4605901ff08c6cba9ad1cc042c2fda1c4df2` /
`2b14761769a6b0768c69386bf3ba08f23ca2b64287e0a0ed02e9673ad889fd0c`.
Normal index SHA is
`5ce914d03543b6269d89c4ad60d5e40c43f2ac2ff62ac68989dd992ef00d1a28`.
The actual producing manifest has29 deduplicated inputs; an earlier proposed
31 count was corrected without adding files. Completion metadata is separate
from the frozen producing inputs. This remains121 bytes above4096.

### B fixed-target recapture promotions: actual5267-byte entry

The current shipping baseline already uses legal-LVA SEE, so the historical
full-minimax-to-LVA saving is not repeated. One internal recapture span now
uses the queen's weakly maximal completed exchange value. Each later legal
recapture removes the differing promoted target and converges to the same
complete child state; the target value contribution is monotone. The actual
make/pin/king/EP checks and all four initial generated promotions stay intact.
No negative-SEE QS pruning is added. The164-byte span becomes112 bytes and
source11009 becomes10957/c3a86dd9; complete5279 becomes5267 (-12).

One O2 function fixture compares the exact old/new Q against independent
legal-LVA expectations:153 legal values, two illegal values, two normalized
EP exclusions, plus the existing six clock/stop guards for each form. Ten
promotion groups/six legal replies check attacker/legality/full-child
convergence. Completed-value preservation does not imply full-minimax
equivalence or identical finite-time cancellation/visit schedule; fewer
recursive calls change when those observations occur.

The ordinary --dev builder reproduces two shipping/two unchanged full-minimax
DEV artifacts. The unchanged selected verifier runs the actual5267-byte new
wrapper in two quit/EOF sessions/eight legal GO epochs, checking exact new
native, stable TIDs, absent private paths/helpers and reader/physical exit0.
New native SHA is
`c895bf3d2802d12014869e13726dce9c29da732e75e6c476c50436c1f39ac6ca`;
whole SHA is
`245a05f9d0656be4a1b79c63a884b06dcc526b4e78a9e5391c8b05c6489d3d76`.
Build/runtime SHA values are
`a083ac7389979be45a294c7c6c7bc9cf40a5f807ccadc4041e6c81afc218dd26` /
`88fa700eb1a85370b6fda28eea76cf98e440c2cbe51347097c441b4adf413e2a`.
Final summary SHA is
`3bb471528128c58355a2f1579bbe2f19e960c962ab774b99d41bc7aa6591ee1c`.
All experiment sources, fixtures, logs and generated outputs are outside Git.

### F move-TT object/type/member bindings: actual4180-byte entry

One fixed map shortens18 global-object/type/member roles at117 physical
tokens, source8265 to8148/5ee725c0. The actual242 declarations/1979 references,
full-position reference multiedges, canonical types/layout/offsets and byte
complement are preserved. Nine atomic macro arguments have exact physical
declaration bindings plus unchanged macro definitions/expanded references;
macro names, directives, headers, external API, main and opaque tokens stay
unchanged. An initial forward-declaration context bug was caught by reparse
before compilation, preserved, and corrected using actual function definitions.
The maintained fixed helper reads only exact source bytes, not ASTs/reports.

One unchanged compiler invocation produces the entire same18576-byte native
dbbe4984, without any metadata exception. The selected codec gives complete
4180, SHA
`3fe2ad6b1e7863f42f1d269a1ebb08069bc9857af587070dad513b9115821bcf`.
Control4217 is reproduced exactly; individual delta addition is not used.
The new policy function proof carries through full native equality, so no
additional core unit runs. One ordinary selected --dev builder reproduces
shipping twice/old full-reference DEV twice; the unchanged selected verifier
executes the actual new wrapper in two quit/EOF sessions/eight legal GO,
exact restored native, stable TIDs and physical exit0. Other policies' source
guards/expected/qualification remain unchanged; their runtime is not rerun.

Build/runtime SHA values are
`61da4d2b691d613c53709c7c1f2c3408dffa61d9806d9cbc1b46c993c07e5b66` /
`1892dc99086ffffcccd72005ba4748d812a964a4cee9234d334730081a5b9967`.
Normal aggregate SHA is
`f646efe27568814344c8a0540adb1396d31c8b7b60c488aa8377a02504e5d3db`.
Producing inputs and later qualification metadata remain separate. No
strength/scaling or <=4096 claim follows from this names-only change.

### D one-state dead classifier: actual5987/6194-byte own-ELFs

The classifier replaces three accumulators with one signed state and early
live exits. Knight/bishop mixtures, multiple knights, opposite-color bishops
or any pawn/rook/queen are live; remaining material has the old dead result.
One ordinary O2 function unit checks109 legitimate two-king FENs against an
independent material-count/color oracle and verifies unchanged Board bytes.
The readable body grows37 bytes while native .text shrinks24 bytes per form;
raw source length is not treated as complete-file cost.

Scalar whole6002 becomes5987, native7836/b758934f; HQ whole6220 becomes6194,
native8192/da682cc7. Both now occupy two RX pages, with the exact BSS/guard
geometry and original scalar/HQ fixed21 models retained. Packer admission
changes only the two exact native/hash/entry/layout tuples. No general
length, guard, mapping or output check is weakened. New whole SHA values are
`74e909cc3fa66d1ddb272efa4e8b196d1ef189d9727c4e736f42cdab00f640c3` /
`a0199047ab2b72d3d75c3bf00b5e09e0125a33e568c649a91e14b9a196b19573`.

DATA decoder/native restoration is separate from positive entry execution.
The ordinary builder reproduces both natives/shipping files twice and audit
files once; the positive verifier checks two pre-entry images and four
quit/EOF shipping sessions/twelve legal GO epochs, exact restored RX and
initial BSS/padding, guards/NX/W^X, stable startup TIDs, stdio/no-child and
reader/physical exit. Actual build/verifier commands both exit0 with owned
groups absent and no forced cleanup. Build/result SHA values are
`5f198f4a25d62c01c20ed689fd39072a8b7ddfac7e444431bfdb8bf49703b732` /
`ae352db6ae110f16c1f6c12e59f38d0bdb10a8a5da34bfa8507e3428264f3df3`.

After those commands, the external collection driver looked for runtime.json
instead of the actual results.json and exited1. Its original complete:false,
FileNotFoundError and executed source remain preserved. A separate read-only
companion confirms actual_commands_complete:true/outer_driver_complete:false;
no target rerun repairs the reporting failure. Companion SHA is
`5aecb6ffb239b7595383a383ca59a31852e76f4ea3554480869f5548eb92a59d`;
final index SHA is
`23077980022e8ea97b4da4e7080647fba2c1cba0186f5eff8d967f4892b9d24b`.
No fresh, negative/fault/intrusive, game, performance or scaling campaign runs.

### F fixed declarations/expressions: actual4174-byte entry

Four exact regions merge same-block integer declarations, remove a quiet-noise
cast/suffix under the fixed unsigned-Move/id0..1/value-range contract, spell
the unchanged ply bound127 and express the same depth range1..126. No quiet
noise, stop/bound check, model or search policy is removed. The pure helper
preserves inverse/complement and all directives/opaque tokens. Source8148
becomes8130/c63cf3d6. The actual compiler preserves the entire dbbe4984 native,
and fixed codec whole4180 becomes4174, SHA
`0111de5226d69c9467a6cae18e8268a259ae05e6b7b1399433a9c819b7969cc1`.

One ordinary selected --dev builder reproduces shipping twice/unchanged
full-reference DEV twice; one frozen unchanged verifier executes the actual
4174-byte wrapper through two quit/EOF sessions/eight legal GO with exact
restored image, stable startup TIDs and physical exit0. Existing default/
material expected and qualification objects stay unchanged; no extra core
unit is needed through the exact native identity. Build/runtime SHA values
are
`ce646ea452a75aa803d13689314bfa18a9aaeded913ebbb6066f0e064980da59` /
`a39c5b977c058f845993261e4d52e70838393700b0b9fd2fcda9a05f21e2d219`.
Normal index SHA is
`80c73ad6b7adf6ad1c900cb60bf7ca6c89a05fe302fc11767da557581e3c9ef5`.
This is78 bytes above4096, not a qualified4KiB entry.

A separate, unselected atomic32 Move17/tag15 ordering-policy cost is4166
bytes from the earlier8148-byte names source. It uses hash low18 bits for
the index and bits18..32 for the tag; this is not a full-key record. An alias
can change generated-move ordering but supplies no cached score/direct move
execution. It retains full64-bit repetition history. Its new native and
whole have only compile/codec/strict-restore evidence, unit/normal execution0.
Whole SHA is
`d2b84c110cf5f59f10bc7faba2f1cfbc6489095883efb69f50808cdef87f55aa`;
cost index SHA is
`e1ab869cb227ca067e2174dc03d0f0c2c7e5aa624daa512079508ec8d294f1be`.
The14-byte cost delta and later6-byte expression delta are not added; their
composition is unmeasured. It does not replace the maintained4174 policy.

## Shared final shipping reductions — 2026-10-21

The maintained A/B/C/E/F entries consume their own fixed engine snapshots.
Changing an ancestor common `main.c` alone does not reduce these submissions.
The new `engines/scripts/shipping_common.py` therefore runs once after each
existing fixed shipping chain, with one shared literal API during packaging.
Historical helpers, maps, default `pack_stream.py` and canonical/DEV inputs
remain unchanged. D uses its separate own-ELF path and is unchanged here.

The source pass removes the sole empty, unused `TINY_H` definition. The old
and guard-only preprocessed compiler text and entire native match for all
seven policies. A/C/E additionally omit `(size_t)` in exactly two fixed TT18
roles: calloc's count and a size_t-indexed clear-loop bound. On the pinned
Linux x86-64 int32/size_t64 profile, `1<<18` is positive int262144 and both
contexts convert to the same size_t value. Full role spans, contextual inverse,
unchanged complement, current input and final output are pinned. This is not
a general cast-elimination rule or a different memory profile.

The packaging API emits `br` literals only when the unchanged previous API
selected a raw ASCII string. It removes the redundant `.encode()` envelope
without changing compiler-stdin bytes. Non-ASCII UTF8, invalid bytes, CRLF,
NUL, delimiters and odd trailing backslashes retain their prior fallbacks.
The 77-byte shell prefix, signal/mask/process-group handling, private TMPDIR,
fd-exec, argv and all other bootstrap code remain unchanged. A shorter shell
AND-list outline was rejected before encoding/execution because decoder
failure could continue parsing the compressed binary tail.

Every complete file below is directly encoded with its current fixed codec;
individual candidate deltas are not added. Source decreases are32 bytes for
A/C/E and16 for B/F; bootstrap decreases are40 and24 respectively.

| Entry | Previous | New whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| A | 4689 | 4674 | 15 | 578 |
| B | 5267 | 5256 | 11 | 1160 |
| C | 5036 | 5020 | 16 | 924 |
| E | 5118 | 5104 | 14 | 1008 |
| F | 4681 | 4668 | 13 | 572 |
| F-material | 4386 | 4374 | 12 | 278 |
| F-move | 4174 | 4162 | 12 | 66 |

All seven ordinary `--dev` builds and unchanged selected verifiers passed in
WSL Ubuntu. Each build reproduced shipping source/native/bootstrap/whole and
full-reference DEV twice. Every selected entire native is identical to the
preceding maintained native, with no metadata exception. Fourteen fresh
quit/EOF wrapper sessions observe exact native restoration, stable3 startup
TIDs, legal finite GO, private-path/helper absence at UCI, one closing result,
reader completion and physical exit. These checks do not establish strength,
target tournament resources or universal compiler-descendant lifetime. The
existing stop-causality evidence boundary is unchanged.

The new compiler-stdin capture test passes all12 literal/fallback inputs;
it runs a Python capture stub rather than an engine. Existing engine/core
proofs are reused through full-native identity, not relabeled as fresh units.
The normal producing-source readback matches every frozen build input.

External normal summary: `4c2bc987c0947387ebe688ac76c7b91f41d1458149278e490638fb1428f7469f`.
Guard/literal composition: `5f59dcc89397f4c4934b17482dc89bda18a0d827247c083670247528d27177aa`.
Guard/casts/literal composition: `665b72e861fa9913e75a507ca9faa87693c85fc5310ca3202e1dc6979a737fed`.
Preparation-only path/recipe-key failures remain preserved in the external
cost roots; they are not engine failures or repaired success receipts.

A separate common main-owned strtok cursor candidate removes104 raw bytes
and measures A4689→4678/B5267→5253 with new native identities. Static ownership
review found no interleaved worker tokenizer or parent-token resumption, but
function/wrapper runs are zero. It remains cost-only and is not composed into
the table above. A valid-0x88 promotion-rank predicate is a further source-only
proposal; no complete-file savings are assigned to it.

All six family size gaps remain. No training, games, AWS or paid execution,
main/develop promotion or release was performed by this checkpoint. External
reference engines and generated artifacts remain outside Git.

## Qualified common and per-family composition — 2026-10-21

The preceding 0da35e2 checkpoint passes both language jobs in
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39528795707)
and [lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39528795769).
Synthetic merge a78c9ddcf4d58e168e388f0c3742c980fc23b4e0 has the same
9a1c62210929cf8e867b579c52fbc59fd10af3cd tree, with develop56bfb5f and
head0da35e2 parents. This success does not qualify the newer sources below.

The maintained late replay now composes qualified source changes after
shipping_common. Embedded full-source pins, nonoverlapping literals, inverse
and untouched-complement checks require the exact source. No external receipt
is a build dependency. Historical snapshots and full-reference DEV are retained.
The new helper SHA is
62ac2fc6d1d8d7525d35d84cb6deeed0b2cff366e74604b0b7f9d219278fd685.

| Entry | Previous whole | New whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| A |4674|4661|13|565|
| B |5256|5229|27|1133|
| C |5020|5016|4|920|
| D scalar |5987|5966|21|1870|
| D HQ |6194|6175|19|2079|
| E |5104|5101|3|1005|
| F full/default |4668|4667|1|571|
| F material/noise opt-in |4374|4374|0|278|
| F material/move-TT opt-in |4162|4093|69|0 (3 spare)|

Every value counts the actual complete file, not added candidate savings.
New native identities are explicit even where length is unchanged. These are
local2-worker/TT18 artifacts, not final resource or strength acceptance.
**Default full F remains an open size target.** The4093 opt-in omits positional
HCE/learners and caches only ordering moves; it does not replace default F.
Per the user's update, common and individual compression continues after size
eligibility, with room reinvested in useful retained/improved features.

The promotion emitter uses !(to+16&96) only for generator-admitted valid0x88
destinations. Invalid to135 is an explicit counterexample outside that scope.
Six winners pass independent old/new ASan/UBSan emitter checks on245760 cases
and337920 moves, including all four promotions in order. F material costs+1B
and remains unchanged. Proof:
3ff8c91b730b6c185e11087deda134ef5c0bf9bbb334663ce5dcea1adbb22307.

A/B and opt-in F MoveTT share one main-owned strtok cursor through nt().
Workers do not tokenize and main does not resume a parent token stream.
Each policy's functions compare74 GO/23 position cases, full Board/history
transactions, missing-value/key consumption and next-line reset. Component
wrappers also execute quit/EOF. AB/F indexes:
fe9bce608f0fd896b65421bb93733aacda48f406ebf011fbf662f4458e514a11 /
4ff7f31d6639e306b61a5f4c20ab752d487e1fc861234fa1b74286cfed2cb7ad.

B shares actual make's material gain with legal-LVA SEE as positive1+gain;
other callers use truth only. One material table replaces the duplicate.
The focused proof compares2323 generated/2043 legal/280 illegal moves, full
child state/gain,158 SEE queries and6 cancellation guards. Two private initial
untagged-EP cases remain explicit exclusions; production receives generated
tags. Proof:8cdcc8b2996291430e5f534ab4ec7fa4d1243f4f04905b58b3737c6c55f142e6.

Opt-in F shares the terminal legal-child scan with the ordered loop and uses
coherent8-byte seq_cst atomic records. Slot index18 plus stored high46 retains
full64 key identity with Move17; zero queries and key0 remain valid. TT falls
4→2MiB. Busy misses/write drops disappear, so ordering, scheduling and strength
equivalence are not claimed. Two fixed positive TT18 casts are also omitted.
The actual final7803-byte TU passes one ASan/UBSan fixture compile/run: real
atomic type/init/N, low18/high46 distinctions, seven Move forms, two writers
20000 stores/40000 queries and fifteen terminal/MTD queries, including an
independent depth1 witness and last-complete preservation. Final function SHA:
d6f97a3f30f1929fec963597a91e86390d60f5a119b637fa8988cb1f34a076d0.
Actual combined cost SHA:
564f52fbfc60e0d9757254d1d4a7abf62c6dc927493d2590646cd34b35744457.

All seven source-wrapper entries pass ordinary --dev builds and unchanged
selected verifiers. Shipping source/native/bootstrap/whole and full-reference
DEV reproduce twice. Fourteen actual quit/EOF sessions observe exact native,
stable3 startup TIDs, legal finite GO, private-path/helper absence, closing
single bestmove, reader EOF and physical exit. These are separate from function
proofs and do not extend failure-path lifetime or strength guarantees.
Normal summary18436B/SHA:
cc82bacb31cfd8fb020fa375a3a1d1b3ece7ac2991dc7ebcf2c7ed772e3d230e.
It checks producing inputs before later receipt-only recipe annotations.
Frozen inputs and preparation failures remain outside Git.

D separately adopts capture-only Move bit3, FROM119 and generated-tag replay;
the provisional EP trial remains raw and boolean-only. ASan/UBSan function
checks cover19 roots/286 pseudo/282 legal moves and14 old/new search pairs per
form, normalizing only Move bit3. Full Worker/TT payload and all full search
features remain. Exact new audit literals were admitted after static discovery;
observer gates are unchanged. The ordinary builder reproduces native/whole
twice and audit once. The existing positive verifier passes pre-entry2 and
four quit/EOF sessions/12 legal GO results. Build/runtime SHA:
8820abbf8bb205231028999cecc49d057b007700811746ec33d8ab238112db2e /
9d7ff8085c0c44c57fcfe35cc73ca5b7cacbae48bac74b644451b606c063aee8.
The prior rejected negative campaign was not retried.

External-only C/E static-AB/move-TT experiments cost4584/4651B and have focused
function proofs. Actual SIMD/E19 and rules/history remain, but optional
learners/PVS reductions/score TT are omitted. No maintained producer or pool
wrapper qualifies these alternatives; full-default C/E targets remain open.
A nullable-legal-query sharing experiment costs C/E+1B and is closed.

### Current 4K rules and continued source compression

The [4K rules](https://wiki.chessdom.org/TCEC_4k_Rules), retrieved2026-10-21,
page oldid7853, require one4096B file, startup within60s and no own files left.
The4K UCI subset includes bare/clocked go, startpos/moves, readiness, uci and
quit; stop/ucinewgame must be tolerated. Extra UCI features are optional.
4K ELF additionally forbids external programs. Normal league option/info
requirements are not imported into shipping. Information hidden in engine
configuration counts toward size. Recheck event conditions for final selection.

Continue full-default F source compression alongside common and individual
work in the other families. Tokenizer expansion to C/E/full F and full F TT
mate-adjust branch sharing now have source-only proposals; neither has a new
cost or runtime claim. External engine implementations remain outside Git.
Each family's size gap, D eligible own-ELF, final resource profiles and their
actual short-search/runtime/strength evidence remain open. Training/data
collection, AWS/paid execution and release are outside this checkpoint.

## Continued full-default source reduction — 2026-10-21

Checkpoint364e316 passes both language jobs in
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39534488838)
and [Node22/24 lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39534488793).
Its PR synthetic merge676d284f15107d836fbcfa5b34e72195ce03d39e has the same
c0afc04ade74f4007f885dbfbcb3eb3407e9dd81 tree as the head; parents are
develop56bfb5f and head364e316. This is evidence for that exact checkpoint.

Further full-source work now extends the main-owned tokenizer to full C/E/F.
Current worker/parse/gen/make call paths have no tokenizer and the parent
does not resume iteration after POSITION/GO. Actual old/new function fixtures
compare74 GO/23 position cases per entry, including C's complete eight-lane
state, E's v/activity model state and F's v/context state, entire history,
fallback, budget, publication and worker bytes. First C fixture compilation
failed because a helper collided with the real command condition variable;
static review also caught a fallback variable comparing itself. Both causes
are preserved. V2 changes only fresh fixture names and passes one ASan/UBSan
compile/run per entry, with candidate/cases/reference bodies/flags unchanged.
Function receipt:5be455c9e3ef668103913c1eb41b15feb0e0a351376c0779387ef67dfdb24a40.

Full F additionally combines exclusive positive/negative mate-score adjustment
branches. Decode operates on promoted int16 values and ply0..127; encoding
uses the actual bounded production score domain. Exhaustive8388608 decode
and7680128 store cases use the real full-key V. Actual U has99 threshold/cp/
bound queries and old/new QS/mate-in-one score, complete payload and witness
comparisons. The first fixture wrongly expected material-only QS0; its run
failed and remains recorded. Independent full HCE97+9−101−15=−10 and actual
old U comparisons resolve the premise, without changing production source.
The corrected ASan/UBSan run passes; receipt:
fa901776d08e97ddb5d6211b5a9ac59c76f28ec868acac53cdd9410247e81e47.

| Full/default entry | Previous whole | New whole | New source | Above4096 |
|---|---:|---:|---:|---:|
| C |5016|5001|10156|905|
| E |5101|5086|10606|990|
| F |4667|4654|9091|558|

F tokenizer alone measures4654B; mate alone4666B; their actual combination
is4654B, so no separate1B is added. The composition has18 fewer source bytes
than tokenizer alone and is selected for source minimization at equal whole
cost, retaining every full-default feature. Exact V-through-U bytes match the
mate-qualified TU. Full F still needs558B; the optional4093B F is a separate
intermediate result. Defaults, full-bound TT, positional HCE/model/learners,
rules/history, MTD convergence and persistent worker policy remain.

Only three fixed rows of shipping_refinements change. Four other literal
cases and every helper function body are exact. All seven source domains pass
input/output/inverse/complement checks. The helper is16627B/SHA
6ecb62499035cedaf6308539de0744a011f7b183ca768984462c4f0435406804.
Each of the three ordinary --dev producers independently reproduces shipping
source/native/bootstrap/whole twice and full-reference DEV twice. Unchanged
selected verifiers execute six actual new-wrapper quit/EOF sessions: exact
native restoration, stable3 startup TIDs, legal finite GO, no private paths/
helpers at UCI, one closing result, reader EOF and physical exit. Normal
producing-input readback matches, before receipt-only recipe annotations.
Normal summary10409B/SHA:
7820f2fe387eee0c1c42df6238b497c2d79efc648d0c6d0fac9aae1d8c7b27b6.
These remain local2-worker/TT18 results, without strength/final-hardware claims.

### Actual upstream sources and rejected compression paths

Current primary sources are pinned outside Git: ice4
fabe3b1a805a1418e56899a3a143a955a399535c and4ku
917a08741cef43d6ae00552df214cc66d0c46489. Seven explicit UCI/search/eval/
launcher/minifier files are read; trainers/weights are excluded. Source index
ee8ce9866f3bf0bed0bdaa72d924a28eba0b6982710e5d6984b1f58eb8668237 and companion
d6b511aa780f3e18b2e729fea4c2335e896f6b91a350554d41b7eae452afe56e retain
raw-byte hashes and actual LF line numbers. Web text extraction has different
blank-line numbering; blob links below use the downloaded file's LF lines.

[4ku's search retry loop](https://github.com/kz04px/4ku/blob/917a08741cef43d6ae00552df214cc66d0c46489/src/main.cpp#L793-L829)
and [ice4's reduced/null/full-window sequence](https://github.com/MinusKelvin/ice4/blob/fabe3b1a805a1418e56899a3a143a955a399535c/src/search.cpp#L245-L277)
motivate sharing repeated child-search calls while retaining Rove's exact
windows, singular extension, learning arguments, history and stop sequence.
The actual current B adaptation shrinks source31B but measures5229→5248B,
so it is rejected. This is separate from historical A4980→5000B. Neither is
promoted or relabeled a win. B loss receipt:
fc1c65c55db443c94e3a1bf250b6ba0496099f258544697313caa76dc26bcef1.

[ice4's shipping UCI](https://github.com/MinusKelvin/ice4/blob/fabe3b1a805a1418e56899a3a143a955a399535c/src/uci.cpp)
uses fixed clock positions and per-GO threads. Those choices and delayed
pathname deletion in the launchers change current Rove input/lifetime contracts.
[4ku's minifier](https://github.com/kz04px/4ku/blob/917a08741cef43d6ae00552df214cc66d0c46489/minifier/minify.py)
has scope-frequency renaming but heuristic bindings and broad token filters;
it does not replace the current binding/offset/inverse checks. Current E19 is
distinguished from historical E21. No upstream implementation is vendored.

A full F embedded payload-bit63 lock also shrinks source11B and requests4MiB
instead of6MiB for TT, but actual whole4667→4673B and text7193→7218B lose.
The fetch_or lowers to a cmpxchg loop. It is not promoted and has no function/
engine execution claim; receipt:
fcbc8120b8a666d5bc90b9faf97462f9f47f6e947394d4855d46484652cfb74c.
Further shared material-classifier work remains a separately scoped candidate.
Compression and full-default size work continue beyond eligibility; no
training, AWS, paid execution, merge or release is added.

## Shared one-state material classification — 2026-10-21

The preceding full-source checkpoint9dce883 passes
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39536538621)
and [Node22/24 lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39536538692).
Its synthetic mergee26acd5ee94d40be3b7f8e8f627c49be5abdd24b has the same
77ca94e25854c2c1b80ed69b66a6a4608978166f tree, with develop56bfb5f and
head9dce883 parents. This CI success keeps that exact source scope.

The new shipping_material_state.py applies after shipping_refinements to all
seven fixed source profiles. It adopts D's existing one-state classifier and
changes only one full function per source. State0 means no minor,−1 one knight,
1/2 only bishops on one square color. A second knight, knight/bishop mixture,
opposite-color bishops or P/R/Q returns live. KNN remains live; arbitrarily
many same-square-color promoted bishops retain the previous dead result.
This is the same limited recognition policy, not a theoretical dead-position
oracle. Models, learning, search, rules/history, TT, input and pool remain in
the protected complement. No feature is removed from the full/defaults.

| Policy | Previous whole | New whole | Saved | Source delta | Above4096 |
|---|---:|---:|---:|---:|---:|
| A |4661|4652|9|+18|556|
| B |5229|5219|10|+18|1123|
| C |5001|4992|9|+18|896|
| E |5086|5076|10|+18|980|
| F full/default |4654|4645|9|+18|549|
| F material/noise |4374|4369|5|+18|273|
| F material/move-TT |4093|4089|4|+18|0 (7 spare)|

Each source grows18B while the logical state and actual whole cost shrink.
The existing compiler/77B prefix/bootstrap/fixed ALONE settings are retained;
neither D's historical gain nor other-family deltas are transferred or added.
Actual A native crosses a file-layout boundary22672→18576B; this is not a
metadata exception. All new native/whole pins are explicitly admitted.

Actual old/new functions and an independent rank/file material-count oracle
run on109 canonical FENs for each profile under ASan/UBSan. All seven agree
on31 dead/78 live and leave the entire Board unchanged, including B bitboards,
C vector state, E model caches, HCE/hash and context where present. Actual
PUT/STATE populate the boards; F MoveTT's absent context field is not invented.
Each included TU is unchanged and main is renamed without being called.
Six-function receipt:
ed44c77b2a10caa257b2dde348e06be8b5e31927156f490d09bef7e501d44500.
Independent B receipt:
c38b7cec15f18a4106b2e6f068c25bfc7a3780070609753fb92fe6182e7e9c7c.
Readback companions bind actual included source, fixture, commands and current
pins for these finite executions; the original runners are not relabeled as
general pre/post hash-fenced executors. No redundant replay is performed.

The pure helper embeds seven exact input/output identities, full-function
literals/offsets, inverse and unchanged-complement checks. It imports only
hashlib and reads no external receipts/artifacts during builds. Its7196B SHA:
eded8d82eed40c383564603a51582e829ff9de2fc626bdc11eab26e6c424b380.
Canonical/DEV inputs bypass the stage. F checks new full/material reference
copies while retaining raw source for its earlier fixed transforms. Explicit
material/move expectations are updated to the measured identities; codecs,
verifier snapshots and normal acceptance logic are unchanged.

All seven ordinary --dev producer invocations and unchanged selected verifiers
pass. Shipping source/native/bootstrap/whole and full-reference DEV reproduce
twice per policy. Fourteen actual quit/EOF sessions observe exact restored
native, stable3 TIDs, legal finite GO, private-path/helper absence, one closing
result, reader EOF and physical exit. Producing-input readback matches before
later receipt-only annotations. Summary22137B/SHA:
2c75a07e42a796030509be4ed6ea5f1046a5528911629463397222f1fdbe051f.
Root's F reference-block indentation preparation defect was caught before any
F builder/compile/engine invocation, preserved externally and corrected using
the actual line's indentation. A/B/C successful commands were not repeated.

Default full F is4645B and still needs549B. The optional4089B file has seven
bytes spare and remains a reduced-feature intermediate. Its further4B gain
demonstrates continued compression after size eligibility. All other family
size gaps and D own-ELF eligibility remain open, as do final profiles and
performance/strength evidence. No training/data collection, AWS/paid work,
main/develop promotion or release is introduced.

## Continued compression: response sharing and counter costs — 2026-10-21

The material-state checkpoint0e716e0 passes both exact-head workflows:
[C/Rust engines](https://github.com/daejunnom/Rove4k/actions/runs/39538184425)
and [Node22/24 lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39538184251).
Synthetic mergef1465092f72c2b03f5aa7b2bf45030afa8128731 has the same
2e5b8459cd2f2b72b10f8d74b4bd4ee533e8508e tree, with develop56bfb5f and
head0e716e0 parents. These successful checks precede the cost-only work below.

One shared UCI response-body candidate computes the exact `uci` comparison
once and selects `uciok` or `readyok` inside a common puts/fflush body. It
preserves the null-token guard, full-string comparisons in the same order,
one response/flush, and the later quit/position/go chain. The fresh block-local
`ok` identifier has no previous binding in any input. Each source shrinks17B.
Actual whole costs all grow, so every candidate is closed without promotion:

| Policy | Current whole | Candidate whole | Change |
|---|---:|---:|---:|
| A |4652|4664|+12|
| B |5219|5229|+10|
| C |4992|5002|+10|
| E |5076|5087|+11|
| F full/default |4645|4656|+11|
| F material/noise |4369|4382|+13|
| F material/move-TT |4089|4102|+13|

Each uses one candidate compilation and one encode under its existing fixed
compiler/profile/codec/prefix. Existing controls are read in place, without
recompilation or re-encoding. Exact inverse/complement and old/new strict
restoration pass. Native lengths remain equal but complete bytes change;
previous engine execution evidence is not transferred to those images.
No function, protocol, engine, normal builder or game execution follows the
losses. Six-policy receipt SHA:
0976704c8c600f9d1220b3615810155cccc34385fa01fa072f77d30072b3aa22.
Independent B receipt SHA:
c92b343dd5f911c1cc8f1a15572572780779fd4d801330691bb4fd609c07a534.

A separate full-F counter candidate groups the shipping node-phase counter
with unsigned32 instead of uint64. Its only consumers reset, increment and
test the low8 bits; unsigned32/64 wrap both preserve that phase. Canonical DEV
node diagnostics remain separate. Source9109, native18576, bootstrap10100
and whole4645 sizes all tie. Native/whole identities change, with no execution
qualification. With neither source nor whole savings, the original counter
is retained. This candidate also runs one compile/encode and strict restoration
only; cost5262B SHA:
7847ddd92240227fb7bf88fe7e38c2a93a0c79d97161a3190473fcb323ead7db.

A full-F N+1 semaphore candidate also loses. It uses two private job semaphores
and one shared done semaphore, with a main-owned active flag and an acq_rel
pending chain. Startup done is consumed before input. The last worker calls
the unchanged result printer, returns from fflush/funlockfile, then posts done;
main consumes that completion before reusing job/root state. Prefix init/create
cleanup, EINTR-only retry, fatal wait/post errors, and join-fatal before shared
destroy/free are included. Eight literal edits preserve the entire actual
TT/search/think/result/position bodies and8098 complementary bytes. Independent
source review finds no blocker; that is not dynamic phase qualification.

All added headers, wrappers, initialization and destruction count in source:
9109→9029B(-80). Actual whole4645→4655B(+10), native18576B with new identity,
text7073→7147B(+74), BSS171176→171104B(-72). This is distinct from the older
N+2 TinyA semaphore gain and the separate F futex loss. One compile/encode and
strict old/new restoration complete; no pool fixture or engine execution follows.
The candidate is closed unadopted. Cost11507B SHA:
47f76e9020a9d07a617f38a71b138d021878f2ee144f4fadf275fcb117162889.

A distinct full-F TT candidate moves the try-lock into key bit0. The logical
slot retains the omitted index bit, so masked-key equality plus equal slot
still checks all64 key bits; the slot is selected before masking. Payload
remains plain under ownership, and mismatched reads restore the previous key.
This does not reuse the payload-bit63 result. Its three actual edits save14
source bytes, but whole4645→4649B(+4) and text7073→7090B(+17) lose. The fetch_or
again lowers to a lock-cmpxchg retry loop. One compile/encode, strict restoration
and static native readback complete; no new TT/function/engine execution or
promotion follows. Cost11580B SHA:
1ae72a1e1a0d1666591125b17f3ccbd01bf8ac4c6ed2b0265abd8226d32c34e2.

All producing inputs, candidate files, failures and terminal process receipts
stay outside Git. The maintained size table is unchanged. Full/default F's
549B gap remains the target; the optional4089B result does not satisfy it.
Further common and per-family source work continues beyond size eligibility.

## Shared integer forms and full-F terminal sharing — 2026-10-21

The preceding source checkpointcc43e4d passes both
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39540981556)
and [Node22/24 lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39540981550).
The new ordinary shipping_integer_forms.py replays fixed final integer forms
on all seven material-state outputs, after shipping_refinements/material_state.
It imports only hashlib and reads no external artifact or receipt during builds.

The number helper retains its null/initial ASCII-digit guard, actual strtoull
call, end-pointer rejection and all clock-token consumption. Its local uses
the existing uint64_t alias, and `n>>63` replaces `n>LLONG_MAX`. On the fixed
Linux x86-64 unsigned-long-long64/uint64_t64 domain, the assignment loses no
value and the high-bit test rejects exactly2^63..2^64-1, including overflow's
ULLONG_MAX. Signs, empty/missing values, suffixes, leading zeros and errno
effects retain the previous policy. All budget clamps stay. Six now-unused
final limits.h includes are removed; C keeps its include because an actual
later immintrin.h lies outside that final-header premise. This is a fixed
source decision rather than a header-removal sweep.

Full/material F additionally omit two size_t casts at fixed positive TT18
calloc/count roles. Their actual compositions are measured, not summed. The
integer-only selected native is entire-byte identical to its preceding native
for all seven cases. Standalone number whole savings are16..24B; the two F
cast compositions save another3B each relative to their actual number outputs.
Numeric cost28107B SHA:
4b7cec0d6e7019a4a094a67925ea77bb5943acd4fb5cf0d40ec02fa0b9b9b26c.
F numeric/cast composition13381B SHA:
bc988d78c19ef8b458c93d6873aa023ec826bcc23bce19a634ece73a889ab086.

Full/default F then uses its own shipping_terminal.py, after integer forms.
It removes the separate terminal legal-make scan and shares the ordinary
ordered legal loop. Draw/ply bits distinguish ordinary, draw, cap-only and
draw+cap; the first successful make returns before QS/path/recursion/witness/
learning/TT writes. Terminal sets F=0 instead of probing TT, so a cached bound
cannot bypass terminal rules. With no legal move the original mate/stalemate
return wins even at halfmove100 or the ply cap. Cap-only with a legal move
sets stopped; draw+cap does not. Full HCE, all learners, full-key score/bound/
exact-depth TT, full-depth MTD(f), completed-iteration witness and SMP remain.
Terminal paths now perform existing pure scoring/sort work and may find a
different first legal scratch child. Timing, work amount and strength equality
are not claimed. Ordinary node ordering is unchanged.

One actual ASan/UBSan fixture includes the unmodified candidate and an old U
reference with only its declaration/two recursive callee names changed. Sixteen
old/new cases agree on score, root, stopped and entire Worker/TT state. They
cover draw/cap/mate/stalemate precedence, check escape, real threefold, dead
material, prestop/expired claim and terminal full-bound TT poison. Independent
full HCE gives quiet-root-10, depth1+12 and QS-10; material0 is not reused.
Ordinary actual TT137 and quiet history/continuation/lower-bound publication
are positive controls. Proof6084B SHA:
3d3815c6dd155871b8ae2142b4aa5c6828f9073e795e4cb8b9c619dfb3320bf8.

The final F8998 source contains the exact qualified1272B U and the entire
terminal-only native. Its actual complete file is4609B, compared with original
4645, integer-only4621 and terminal-only4633. Full-native identity to the original
is not claimed. Both pure helpers pin exact source inputs/outputs, literal
spans, inverse and protected complement. Canonical/DEV bypass both. F's
separate full/material reference copies use the new late stages, while raw
preimages continue into their older fixed policy transforms unchanged.

| Policy | Previous whole | Current whole | Saved | Source delta | Above4096 |
|---|---:|---:|---:|---:|---:|
| A |4652|4628|24|-43|532|
| B |5219|5196|23|-43|1100|
| C |4992|4976|16|-23|880|
| E |5076|5056|20|-43|960|
| F |4645|4609|36|-111|513|
| F-material |4369|4343|26|-59|247|
| F-move |4089|4067|22|-43|0 (29 spare)|

All seven ordinary --dev builds and unchanged selected verifiers pass in WSL
Ubuntu. Shipping source/native/bootstrap/whole and full-reference DEV reproduce
twice per policy. Fourteen actual quit/EOF wrappers observe exact restored
native, stable3 TIDs, legal finite clock/bare GO, private-path/helper absence,
one closing result, reader EOF and physical exit. Six final natives remain
entire-byte equal to the preceding maintained images; full F uses the explicitly
admitted terminal image. Component function qualification and final wrapper
observations remain separate. These are local2-worker/TT18 results, not final
resource, many-core, performance or strength acceptance. Normal producing-input
readback precedes receipt-only annotations. Summary48143B SHA:
1de4261cbd87622c9326fe8c72137b0d96148fb4e1514b2c81e8dbda4031a2a5.

The number preparer's initial Markdown CRLF-fence failure and the compound
cost preparer's incorrect assumed next-function delimiter both occurred before
any C compilation/encoding. Their original failures are preserved; only those
preparation boundaries were corrected. Successful compilations were not repeated
to repair collection. Generated files, reports and third-party references stay
outside Git. The current TCEC4k rules were refreshed at oldid7853 on2026-10-21:
the4K minimum UCI subset, single4096B file, startup60s and script/ELF boundaries
remain the relevant contract. No general-TCEC option expansion is added.

Default full F still needs513B. The4067B reduced-feature opt-in has29B spare,
and is further compression after prior eligibility; it does not complete full
F. All other family size gaps and final profiles/comparisons remain open. No
training/data collection, AWS/paid run, game, merge or release is introduced.


## Startup/job source sharing and explicit full-F hash policy — 2026-10-21

The preceding source checkpoint8bc1abe passes both
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39542751208)
and [Node22/24 lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39542751181).
This checkpoint adds pure late source replays from maintained readable inputs;
external cost outputs and third-party source remain outside Git. The new
shipping_compaction.py reads no external artifact and is bypassed by DEV.

B/C/E's sole shipping TT-clear call immediately follows successful calloc,
before board initialization, threads, input or TT access. Plain uint64 key/data
therefore already equal0. Removing their repeated stores and loop braces keeps
every atomic_flag_clear. No assumption is made about the flag's zero bit
representation. This shipping helper is now an initial-flag pass, not a general
reset API; canonical/DEV's real ucinewgame reset remains unchanged. B also omits
the two remaining fixed positive TT18 size_t casts.

B/E move best=0 into think's unconditional prefix and remove the GO four-field
reset loop. Worker results are inspected only after every worker returns and
the last pending decrement occurs under the existing mutex. Pre-stopped and
late-starting workers still initialize before completion; the last-complete
result, current-root fallback, history, learners, job publication and joins
remain. A private direct-think caller that preseeded best without production
GO now has a different contract. C already had this ownership and is unchanged
by the reset part. This is a source/lifecycle ownership change, not a resource
or scheduling-policy change.

B's SEE replaces only its rank test with `!(yv+16&96)`. TO masks yv into0..127;
the new and old predicates are identical on every such value, and the addition
cannot overflow. Generated initial tactical moves, the h-first legality test,
same occupied recursive target, queen recapture promotion, unknown guard and
ordering-only consumption remain. It does not broaden arbitrary private raw
untagged EP support or add QS SEE pruning.

Full/default F's own shipping_hash_policy.py deletes only the32B pre-add from
its pure by-value mixer. **This is an explicit hash-policy change.** Remaining
64-bit XOR shifts and odd multipliers are bijective; all piece/state hashes,
rolling history, full TT context and correction buckets nevertheless change.
Individual-token bijection does not prove position-XOR collision quality or
equal search/learning/strength. Black Ka1's individual piece token is now0;
this neither implies whole-board hash0 nor adds a forbidden-zero key contract.
Actual TT key0 store/load and same-slot nonmatching keys remain supported.
Full HCE, history/continuation/correction, full-key bound/depth TT, full-depth
MTD(f), completion witness, rules and SMP are retained. DEV keeps its previous
policy; both optional F selections keep their own previous bytes, while their
separate full-reference copy reproduces the new default policy.

| Case | Previous whole | Current whole | Saved | Previous source | Current source | Above4096 |
|---|---:|---:|---:|---:|---:|---:|
| B |5196|5162|34|10702|10595|1066|
| C |4976|4969|7|10151|10123|873|
| E |5056|5028|28|10581|10477|932|
| F full |4609|4592|17|8998|8966|496|
| F-material |4343|4343|0|8545|8545|247|
| F-move |4067|4067|0|7778|7778|0 (29 spare)|

The B/E values are actual combined measurements, not sums of independent
costs. Standalone TT-zero saves B10/C7/E9, reset B14/E19 and SEE-rank B8.
The final native files for B/C/E/F have new identities despite unchanged file
lengths. Both optional F files remain entire-byte equal. A4628 and D5966/6175
are unchanged and their prior qualification is reused, not freshly executed.

Focused ASan/UBSan fixtures use actual final candidate TUs. Startup checks
observe all262144 slots through atomic operations and real TT key0/matching/
same-index nonmatching access. B/E reset checks compare old GO-reset+old think
against new think, using actual completed depth1 seeds, pre-stop/expired zero
completion, successive root and current fallback output. A manual late-worker
value boundary is not an actual SMP-schedule execution. The F proof compares
978 mix,832 piece and288 state values to an independent modulo64 specification,
then15 rule paths/39 states/24 transitions to independent board/legal/HCE/hash/
history/context expectations. Its16 terminal cases use new helpers on both U
bodies; old hash goldens are not reused. Hash quality and strength remain open.

All six changed ordinary builders (B/C/E and three F selections) pass --dev and
unchanged selected verifiers. Shipping source/native/bootstrap/whole and full
DEV reproduce twice per selection. Twelve actual quit/EOF sessions verify
restored native, legal finite GO, stable3 TIDs, private-path/helper absence,
one closing result, reader EOF and physical exit. Producing recipe/source
readback precedes receipt-only annotations. This is local2-worker/TT18 evidence,
not final target resources, many-core performance, games or portfolio acceptance.
Normal summary18106B SHA:
4b7b98ecc6cdb94d11a112e307d388633a03fb061d2000b08167b85ac70c72ca.

A further full-F worker pending-loop sharing candidate reduces source18B and
native text6B, but its whole file ties4609B. It is closed without pool runtime
or adoption; it was not combined with the hash policy. The new hash preparer's
optional-field KeyError, B fixture producer's UTF-8 serialization failure and
the first B SEE fixture's missing defended-promotion coverage are preserved as
separate failures. The latter reached its positive-coverage assertion rather
than establishing a successful whole fixture. Corrective coverage uses existing
independent frozen cases; candidate source and expected scores stay unchanged.

The latest [TCEC4k rules](https://wiki.chessdom.org/TCEC_4k_Rules), revision7853,
were rechecked: whole4096B/single file, startup within60s/no leftover own files,
4K minimum UCI and tolerance of unsupported tournament commands remain the
basis. General TCEC options are not imported as minimum requirements. The pinned
[ice4 search](https://github.com/MinusKelvin/ice4/blob/fabe3b1a805a1418e56899a3a143a955a399535c/src/search.cpp)
and [4ku source/minifier](https://github.com/kz04px/4ku/blob/917a08741cef43d6ae00552df214cc66d0c46489/src/main.cpp)
comparisons remain external references; no engine source is vendored. Passing
the optional F size threshold remains an intermediate result. Full/default F
still needs496B; A–F compression and feature work continue beyond size passage.


The corrective B SEE input selection adds only the two omitted existing
defended-promotion parents89/90. It preserves every C assertion and frozen
score/state, and reuses the already successfully compiled ASan/UBSan binary;
there is no second compile. The56 input rows produce54 actual old/new Q
comparisons plus2 normalized-EP exclusions,128 rank checks,6 cancel/deadline
guards and positive cross-promotion convergence4groups/2legal replies. One
corrective runtime passes; the original v1 coverage failure remains intact.
SEE proof12019B SHA:
996b2dfec43f19e863e6a8bb96c002dbc7b8432fe3f86c1f31726d73299f96b6.
Startup proof15219B SHA:
545620380b18fc35287906631266a6b300ef159f4baf426ae473747cf7d7f826.
Reset proof5013B SHA:
af1c72e264e470481a7b3ae0204d4566ef07d82573b69e159d77a75c8d8b7357.
New hash proof10988B SHA:
62545d3a20037615dc645f1ca399e9f6c7f44058b5332336b964f1bea15d46b7.


## Literal include gaps with identical native images — 2026-10-21

The preceding source checkpoint8abcbc3 passes both
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39545848195)
and [Node22/24 lifecycle CI](https://github.com/daejunnom/Rove4k/actions/runs/39545848206).
The late shipping_includes.py removes exactly the single space in fixed
whole-line `#include <literal.h>` directives. It preserves header bytes/order,
newlines, all macro/conditional directives and all other source bytes. The
identifier include and angle-header remain distinct preprocessing tokens.
This is not a general directive-whitespace relaxation or header deletion.

The six selected cases use seven directives each except C, which has nine,
including its limits.h and later immintrin.h. The pass follows all existing
fixed-offset stages. F's selected full/material/move paths, full_reference and
material_cleaned each apply the matching case only to their final copy; raw
preimages still feed the existing policy transforms. DEV bypasses the pass.
All four builders pin and freeze the helper before import. Exact input/output,
literal offsets, inverse and each protected gap are verified without external
cost/source/receipt reads during ordinary builds.

| Selection | Previous source | Current source | Previous whole | Current whole | Whole delta |
|---|---:|---:|---:|---:|---:|
| B |10595|10588|5162|5161|-1|
| C |10123|10114|4969|4968|-1|
| E |10477|10470|5028|5027|-1|
| F full |8966|8959|4592|4589|-3|
| F-material |8545|8538|4343|4341|-2|
| F-move |7778|7771|4067|4067|0|

F-move is deliberately admitted as a7B raw-source reduction with tied whole
size and unchanged29B spare. Its new wrapper bytes are reproduced and tested;
whole-byte equality is not claimed. A's identical proposal loses1B of whole
size (4628->4629) and is excluded from both the helper and wiring. No loss is
hidden by a metadata exception or a changed codec.

All seven fixed costs preserve their actual compiler/package settings:
A uses its original preset defaults; C retains -mavx2 and nice64; B/E/F retain
their existing settings and F-move retains lc0. Each candidate compiles/encodes
once, controls neither. Every entire native equals its actual preceding image,
not merely its length or sections. Old/new strict Python and CLI restores all
match source/compiler-argv/bootstrap. Cost110005B SHA:
1c5140ba629d196054e275e2994cb1299f85ffdfc2a61cdbbd384777aeef3eea.

The selected six ordinary --dev builders reproduce shipping source/native/
bootstrap/whole and full-reference DEV twice. All twelve actual selected
quit/EOF wrappers pass unchanged verifiers, exact restoration, stable3 TIDs,
legal finite GO, private-path/helper absence, closing result, reader EOF and
physical exit. Component function proofs are reused under entire native
identity; no fresh ASan/function or strength run is claimed for this spelling
stage. Producing-input readback precedes receipt-only annotations. Normal
summary18755B SHA:
b6be10f54e68ea2c381ed85a5a8fce47253825bb5bafbd1639b5b9802e9c5137.
This remains local2-worker/TT18 evidence. A/D and their prior qualification are
unchanged; full F's hash policy is unchanged from8abcbc3. Its493B remaining
size gap, final resources, games/strength and portfolio acceptance remain open.

A separate fixed full-F castling-right-mask lookup changes79 source bytes to78
while preserving all int inputs, but whole4589->4601 loses12B. It is closed
without adoption, alternative constants/layouts, A cost or function runtime.
Rights cost6215B SHA:
400e2d68c6482e23e08cbe02a170c75ae7b5fb5239bdbd19cef795fcd51c0c87.
The comparison engine's minifier suggestion is used only as a narrow design
reference; third-party source remains outside Git.


## Fixed mixer literals and B clock-first SEE polling — 2026-10-21

The final source chain retains the preceding include-only stage and adds one
late fixed decision per family. A/C/E/F use shipping_mixer_literals.py; B uses
its own shipping_guard.py. Both are pure literal replays with exact source
pins, inverse and protected gaps, frozen by recipe before import. DEV bypasses
them. F's final selected/full-reference/material-reference copies are transformed
after includes; earlier material/move transforms still receive raw preimages.

Only three large mixer constants lose UINT64_C wrappers. Each lies strictly
between2^63 and2^64. On the fixed LP64 hosted-C target, unsuffixed nondecimal
type selection first fits unsigned long64, the same type/value as the actual
header's UL macro expansion. Add/multiply/shift operands and hash values stay
unchanged. This is representation compression, not another hash policy.
Full F has two constants after its previous no-preadd policy; the others have
three. Headers stay. B's important UINT64_C(1)<<bit(0..63) is never converted
to int32. B's standalone mixer spelling loses2B (5161->5163), so it is excluded
without retrying layouts or combining that measured loss with the guard.

B replaces the114B SEE cancellation guard with103B: sample monotonic time,
set stopped if expired, then load stopped. The actual GO waits for every old
worker before updating the deadline and resetting stopped; within a job the
deadline is immutable and stop sticky. Illegal make still returns before the
guard. Completed legal-LVA results, recursive unknown propagation and the
ordering unknown guard stay; QS still does not use SEE as a negative-pruning
certificate. Poll ordering and cancellation observation change. Equal cancelled
visit/clock/TT/learning traces or latency are not claimed.

One actual new-candidate ASan/UBSan fixture compares the current old Q renamed
only at declaration/recursion against new Q. Its56 frozen inputs give54 Q
comparisons plus2 normalized-EP exclusions,128 rank checks,6 cancellation/
deadline guards and positive convergence4groups/2replies. Completed scores and
uninterrupted clock calls agree; Board/two Workers stay unchanged. Old guard
calls[1,2,2,3,3,4] and separately predeclared new[1,1,1,2,2,3] both pass. One
compile/run, no retry. Proof9566B SHA:
9139d25cccc5f57f2f49e52c0af486cb4174a5534a9057164cb732554348cd31.

| Case | Before mixer/guard whole | Current whole | Stage saved | Current source | Above4096 |
|---|---:|---:|---:|---:|---:|
| A |4628|4619|9|9052|523|
| B |5161|5154|7|10577|1058|
| C |4968|4960|8|10084|864|
| E |5027|5019|8|10440|923|
| F full |4589|4581|8|8939|485|
| F-material |4341|4330|11|8508|234|
| F-move |4067|4057|10|7741|0 (39 spare)|

All six selected mixer costs have entire native identity to their preceding
images, including A's compiler/default codec, C's -mavx2/nice64 and F-move lc0.
B has a new native identity and text16B smaller. No file-length-only identity
or metadata exception is used. Mixer cost101590B SHA:
1953e28c850e1c49ad5783c255241b28466eb863f18496686e0e03c38d433755.
B guard cost15623B SHA:
df55297d11d185e92f1415ef609250340cff5ccd70ba0408a4bbc6be20ed0543.

All seven final ordinary --dev builds and unchanged selected verifiers pass.
Shipping source/native/bootstrap/whole and full-reference DEV reproduce twice
per selection. Fourteen actual new quit/EOF wrappers observe exact restored
native, stable3 TIDs, legal finite GO, private-path/helper absence, one closing
result, reader EOF and physical exit. Six function qualifications are reused
under complete native identity; B's focused Q proof and final wrapper checks
have their distinct scopes. Producing-input readback precedes receipt-only
annotations. Final normal summary21274B SHA:
af00002687cf6ed0d84f2e85f21169d381bb1cd8721005c05cc87a4fabe2bb96.

Relative to8abcbc3, whole savings are A9/B8/C9/E9/F11/F-material13/F-move10B.
Their source reductions are30/18/39/37/27/37/37B. D is unchanged5966/6175B.
Full/default F still needs485B. Optional F-move's39B spare is an intermediate
reduced-feature result. The goal remains active: all A–F source compression,
D's eligible own-ELF, selected resources/target hardware and strength/candidate
acceptance remain open. No new games, training/data collection, AWS or paid
execution is performed. Passing a size threshold does not end compression.


## Plain-Popen cleanup guard source compaction — 2026-10-21

The preceding source checkpoint0458092 passes
[C/Rust engine CI](https://github.com/daejunnom/Rove4k/actions/runs/39548145732).
Each maintained compiler bootstrap replaces only
`if p is not None and p.poll() is None:` with `if p and p.poll() is None:`.
The current plain CPython3.12 Popen class defines neither bool nor len and is
always truthy; p is only None or the actual returned Popen. None short-circuits
without poll and every Popen makes the same single poll/cleanup decision.
Falsey monkeypatched Popen objects are outside this fixed runtime domain.

Compiler argv/raw C input, PID publication signal mask, handlers, killpg/wait/
timeout/returncode, private TMPDIR, TemporaryDirectory cleanup, unlink-before-
descriptor exec, argv/env and the77B shell prefix stay byte exact outside that
line. This neither improves nor proves a general exited-leader/remaining-
descendant cleanup guarantee. No new fault campaign or generic Python rewrite
is added. Historical generic pack_stream bootstrap is not a current producer
and remains unchanged; the actual five tracked templates are updated directly.

| Selection | Previous whole | Current whole | Saved | C source bytes (unchanged) |
|---|---:|---:|---:|---:|
| A |4619|4613|6|9052|
| B |5154|5148|6|10577|
| C |4960|4954|6|10084|
| E |5019|5014|5|10440|
| F full |4581|4575|6|8939|
| F-material |4330|4325|5|8508|
| F-move |4057|4051|6|7741|

Each emitted script and owned template loses12 raw bytes. The seven fixed costs
encode once each and never recompile unchanged C. Existing normal native files
are explicitly reused as identity inputs, not claimed as new compile results.
Python strict14/CLI14 decodes restore exact C/argv/bootstrap; inverse, raw
complement and all other AST nodes match. Case-specific A defaults, C nice64/
-mavx2 and F-move lc0 remain. Cost26764B SHA:
ecf965ab3eba1474b85d2d75a9a8dec46ede51e3a9bef3ea02282dea0900d75b.

Actual ordinary regeneration from the new tracked templates then passes all
seven --dev builders and unchanged selected verifiers. C/native and full DEV
remain entire-byte equal to preceding outputs; new scripts/whole reproduce
twice. Fourteen actual new quit/EOF wrappers pass exact restoration, stable3
TIDs, legal finite GO, private-path/helper absence, closing result, reader EOF
and physical exit. Function proofs are reused; no new function/strength or
startup-fault result is claimed. Producing-input readback precedes annotations.
Normal summary15346B SHA:
90e45a020a55ef5a3ff6af78dfa42908eb8625395fe5c991d860bde8d34b2ff6.

The preparatory metadata query's rows/cases field typo and the cost owner's
post-run readback filter typo are preserved as read-only preparation/collection
errors. Neither changes candidates, expected output or prior cost results;
successful compilers/encoders are not repeated to repair reporting.

Full/default F now needs479B. Optional F-move4051B has45B spare and remains a
reduced-feature intermediate. D stays5966/6175B. The A–F goal and compression
beyond size passage remain active; final target resources, many-core behavior,
candidate/strength acceptance and D's eligible own-ELF still require evidence.
Training/data collection, AWS, paid runs and new games stay excluded.

## Full-F local correction clamp — 2026-10-21

The plain, non-escaping local int clamp changes only
`if(l>256)l=256;if(l< -256)l=-256;` to
`l=l>256?256:l< -256?-256:l;`. For every representable int, both yield256
above256, -256 below-256 and the original value otherwise. The additional
same-value assignment in the last case has no observer. There are no calls,
volatile/atomic accesses or overflowing operations in this expression.
Initializer, quiet/capture/promotion/check/mate guards, correction bucket and
EMA remain exact. Full positional HCE, history/continuation/correction, coherent
full-key score/bound/depth TT, full-depth MTD(f), completion witness and SMP stay.

Source8939→8933B, bootstrap9918→9912B and whole4575→4574B. The fresh18576B
native is entire-byte equal to the preceding d7ce48d6... image; metadata
exceptions are not used. One compile/one fixed encode and two Python/two CLI
strict restorations pass. First-cost receipt4958B SHA:
7b72e1af5e5a0b9135992a972aa6e5edf381cb3520fb508806dec8855bf45f5b.

The tracked pure shipping helper follows mixer literals for selected full F and
the separate full reference used by optional builds. Earlier raw policy inputs
and every DEV path retain their prior bytes. Ordinary --dev regeneration and
unchanged selected verifiers pass all three F selections: shipping/DEV reproduce
twice, all natives/DEV and optional artifacts remain entire-byte equal, and six
fresh actual quit/EOF sessions pass restoration, stable3 TIDs, legal finite GO,
private-path/helper absence, closing result, reader EOF and physical exit.
Producing recipe/source readback precedes receipt-only annotations. Normal
summary6902B SHA:
5e079fce09822966fcc5ca90789405eac2bc7c16bc81fbc93a2b5ed992af9270.
Function evidence is reused under entire-native identity; this is no new fault,
strength, target-resource or 4KiB acceptance. Full F still needs478B. Optional
4325/4051B policies and D5966/6175B are separate. Compression continues after
size passage; the all-family goal remains active.

The latest [TCEC 4k rules](https://wiki.chessdom.org/TCEC_4k_Rules), reread on
2026-10-21, still resolve to oldid7853. The minimum 4k UCI subset, tolerance of
unsupported tournament commands, single4096B file, startup60s/cleanup and the
separate self-contained own-ELF rule remain the applicable boundaries. No
ordinary-league full UCI options are added as mandatory work.

Source-only next candidates are the pure piece-index inline, single HISTORY
macro inline and clock-presence sentinel. Their raw savings are not whole
savings or adoption. The D prefix-discard proposal is also separate: current
D consumers keep local m and never reread the consumed sort prefix.
[4ku's fixed source](https://github.com/kz04px/4ku/blob/917a08741cef43d6ae00552df214cc66d0c46489/src/main.cpp#L697)
similarly copies the suffix winner locally and uses a distinct evaluated-move
array for learning. In contrast,
[ice4's fixed source](https://github.com/MinusKelvin/ice4/blob/fabe3b1a805a1418e56899a3a143a955a399535c/src/search.cpp#L163)
retains full swaps and later reads the prefix for history penalties. That
difference must be checked per implementation. External engine sources remain
outside this repository; no code or measured savings are imported from them.

## Full-F fixed source forms and D consumed prefix — 2026-10-21

The source checkpoint5af20d0 passes all C/Rust engine and Node22/24 lifecycle
jobs. Two more full-F source forms retain that checkpoint's entire native:
delete the private32B piece-index helper and expand its three actual int8_t
arguments as parenthesized cell+6; delete the21B HISTORY definition and replace
its four ordinary expansions with the identical int token4096. Raw savings
are29B and33B. Each cell/index/pointer is evaluated once, int promotion/addition
and learner targets stay exact, and 4224/4096 key capacities and rejection
remain. Final macro/line identities change; canonical/DEV and earlier fixed
transformation inputs retain their bytes.

Each isolated cost is4564B, down10B from clamp4574B. The actual composition is
4553B, 11B smaller than either isolated result: savings are measured, not
added. A single pure nine-span helper maps8933→8871B with exact positional
inverse and all complementary bytes preserved. One fresh compile and fixed
encode yield entire-byte equal18576B native d7ce48d6...; strict Python/CLI old
and new restoration passes. Composition cost9563B SHA:
76899105c69ad3a61d44bed6712f5fbf7eee99e06d42a62d94ecc75b420f5635.

All three F ordinary builders reproduce shipping/DEV twice; unchanged selected
verifiers pass six actual quit/EOF sessions. Full-reference copies include the
new stage after clamp, while optional raw inputs, outputs and full DEV stay
entire-byte equal. Function proofs are reused under native identity. Producing
readback precedes metadata-only annotations. Normal summary7071B SHA:
9669f3aa030fd02a39a7d66704ae38c465b906eab7f035095627990b27830aaf.

D independently removes two writes to the consumed selection-sort slot and
their score temporary. The selected Move stays local; future suffix state and
strict-greater tie permutation are identical by induction. Current legal/QS
skips, PVS retries and positive cutoff learning never observe the old prefix.
Readable search6141→6102B; text falls13B per form. Scalar native7772→7740B,
HQ stays8128B with a changed identity. Fixed21 packets become4810/5032B and
whole5947/6169B, down19/6B. Nonpacket1137B, model masks, page/BSS/guard/reserve,
full-key atomic16 TT, HCE/PVS/QS/learners and SMP remain. Entry offsets follow
the actual new code. Exact known-native/form/model mappings and verifier
expectations admit only these bytes; inspection and lifecycle bodies stay.

Cost native2/encode2/loader2 and old/new independent Python restore4 precede
audit-loader discovery2 and root static admission of actual eight files/ELF
headers/packet suffixes. One ordinary builder then reproduces native/whole
twice and audit once. The selected positive verifier passes pre-entry2 and
quit/EOF4 sessions with12 legal GO, persistent3 TIDs, exact restored RX,
zero initial BSS/padding, guards/NX, stdio/no observed child and physical
settlement. No negative/fault campaign or game is run. Build77739B SHA:
9cd5c6748ec72de497957c7f6fc2ff20de4010b5f91ceb010df5153a27f23cc3.
Positive runtime58050B SHA:
c7ef4b272d6252fb602a8edf1be0c8d99ec157021a4c4aa84b711a049d86b5d9.
Producing21/build-input17 readback precedes README/recipe receipt annotations;
the final index5503B is b1212756633dfd63bfc069b6d458fdf77e3c0808749e969d051151328a5bd461.

Full/default F retains every family feature and still needs457B. Optional
material/noise4325B and MoveTT4051B remain separate policies. A/B/C/E currently
remain4613/5148/4954/5014B. Their common clock-presence sentinel has measured
source−12B each and whole−3/−2/−2/−1B, but changed natives: focused qualification
and normal intake are pending, so those costs are not in the current table.
The all-family goal remains active beyond size passage. Final resources,
target hardware/many-core behavior, strength/candidate acceptance and D's
eligible own-ELF still require evidence. Training/data/AWS/paid runs stay out.

## Common clock presence and E19 physical slots — 2026-10-21

All five source-compiled default families encode absent own time as UINT64_MAX
and use unsigned complement as the presence test. The actual parser admits only
0..INT64_MAX; invalid/missing/overflow input still returns0 and a selected-time
assignment still marks presence. Three fixed fragments remove12B per family.
The pure tracked helper follows each family's last shipping stage. DEV bypasses
it, and F's optional selection bypasses it while its separate full reference
includes it. Earlier raw policy preimages remain unchanged.

The V3 fixture ports clock_gettime only inside the actual included candidate TU;
it does not define libc's real clock symbol or intercept sanitizer/runtime clocks.
Actual old/new GO functions compare20 literal cases per family, including both
sides, absent/zero/duplicate/malformed/high-bit/overflow values and budget caps.
Actual token consumption, Board/history/worker storage preservation, legal
fallback, deadline and idle publication fields match. Fatal ASan/UBSan passes
five compiles/runs,100 comparisons, stderr empty, no timeout or remaining group.
This explicit idle adapter starts no production main or worker and establishes
no concurrent worker completion or timing equivalence. Receipt143004B SHA:
5699d958dd4a0b41818a4967f0068884c3e04c8e0a5a912c3dfd14cdbac8ecc0.

E separately inserts fixed int16 zero slots0/6 into its physical table and
remaps four fixed source regions. The logical19 coefficients are extracted as
physical[1:6]+physical[7:21], retaining signed16-LE SHA
a5bb11099b62489aca43a011619e15076b0637b2f2e460d89772162965cd5424.
There is no model/parameter increase: full nonlinear E19 and all five ordering
features remain. Actual d callers supply nonzero signed1..6; zero/invalid d is
not newly admitted. R handles victim0..6, EP and promotions through its actual
caller contract. One fatal SAN fixture checks1536 piece operands,27 independent
order cases,26 accepted make children and78 bounded numeric leaf cases, including
both clamps and nonadditivity. Numeric cache seeds are not reachable-board
claims. Receipt9628B SHA:
584911f5c954f83d37ecd65bda002a17b10e0fbbf5d16a1cbe6d9ad2ff794e85.

E's physical-slot stage follows clock presence and preserves all five gaps with
an exact inverse. Solo clock costs5013B; solo slots5012B; actual composition5011B
is1B below the measured solo minimum, with no additive saving assumption.
Composition source10400B, native26400B has a new identity; first-cost receipt
20469B SHA aafd59d7ef368f12d1934c627f3c976bb4053f008552a44087ed16f8a22ec9c6.
Other whole results are A4610/B5146/C4952/fullF4548B. All resources/features and
full DEV identities remain; natives have changed rather than being admitted
under metadata exceptions. F optional4325/4051B outputs remain entire-byte equal.

All seven ordinary --dev builders reproduce shipping/DEV twice and unchanged
selected verifiers pass14 actual new quit/EOF sessions: exact restoration,
stable3 TIDs, legal clocked/bare finite moves, private-path/helper absence,
closing result, reader EOF and physical exit. Producing input readback and saved
recipes precede receipt-only annotations. Summary15766B SHA:
8e30da1a34a87d6f68cc8a42aafab4e43cb49049ef38510cfb008776095e01b9.

The latest TCEC4k page was reread on2026-10-21 and still resolves to oldid7853:
[4k-specific rules](https://wiki.chessdom.org/TCEC_4k_Rules#7._4k_specific_rules).
Its4096B single-file, startup60s/cleanup, minimal UCI/toleration and separate
self-contained own-ELF boundaries remain the applicable contracts. No ordinary
league option inventory is added. External4ku/ice4 reference source stays outside
Git. Full F still needs452B; the all-family goal continues beyond size passage.
Final target resources, many-core behavior, strength/candidate acceptance and
D's eligible own-ELF remain separate. Training/data/AWS/paid runs stay excluded.

## Full-F single result stream operation — 2026-10-21

The shipping result callback contains one complete printf bestmove line followed
by fflush. Its explicit flockfile/funlockfile pair is removed. The fixed glibc
stdio premise is per-operation internal stream locking, as documented in the
[glibc2.39 stream-locking source](https://github.com/bminor/glibc/blob/glibc-2.39/manual/stdio.texi#L443)
and [vfprintf implementation](https://github.com/bminor/glibc/blob/glibc-2.39/stdio-common/vfprintf-internal.c#L1473).
No unlocked/raw-FD/signal writer is admitted in this shipping source. DEV's
multi-call info sequence and selected optional policies bypass the new stage.

This deliberately relaxes the outer multi-call output grouping: controller ack
operations may run during aggregation or between result printf and fflush, and
may flush buffered output themselves. Individual complete stdio operations
retain stream exclusion. Callback selection, result flush and completion
broadcast stay under the actual job mutex, so the controller's next position,
GO and closing fence still follow callback completion. Exact timing, response
order, forced collision, cross-process or signal-handler atomicity is not claimed.

The pure exact two-deletion helper follows clock on selected full F and separate
full-reference copies. Source8859→8821B, bootstrap9838→9800B and whole4548→4537B.
The fresh18576B native changes identity; no metadata exception is used. One
compile/encode and strict old/new Python/CLI restoration pass. Cost9634B SHA:
fdc94debb1e962a62daabeb09e6ab2142b248540d40bba91468779059294ec6e.

Actual measured-wrapper protocol observation first failed before engine launch:
the cost artifact had mode0644. The original complete:false/terminal:true receipt
and launch-intent log remain, with engine sessions0. Only that owned artifact's
mode changes to0755; raw4537B identity remains. A new V2 output/source preserves
the earlier failure and runs two actual sessions. GO0+isready is posted in one
write/flush; exactly readyok then legal bestmove g1f3 appears in both, with no
extra/partial line through quit/EOF. Actual native identity, private-path/helper
absence, stable3 TIDs, physical reader EOF, rc0 and main/group absence pass.
Actual overlap causality remains unproven and close occurs after the response
pair. V2 runtime4349B SHA:
2df168c7fe2b4a59ac132e5c983af87456f6d6b22d2a70746b588208ab9a9f5b.

All three maintained F builders then reproduce shipping/DEV twice; unchanged
selected verifiers pass six fresh quit/EOF sessions including active closing
search observation. Selected optional artifacts and every DEV remain entire-byte
equal. Producing input readback/saved recipe precede receipt-only annotations.
Normal summary6407B SHA:
094a1234527c26c3c28ad3806c139cf0ad6faebcad766f2a3cfca02391c87df7.
Full/default4537B still needs441B, retaining full HCE, all learners, coherent
full-key bound TT, full-depth MTD(f), completion witness and SMP. A/B/C/E and D
stay at their preceding maintained values. Goal and compression beyond size
passage remain active; resources/many-core/strength/eligibility remain separate.

## D packed HCE coefficient table — 2026-10-21

Only board.c value()330→318B changes. A static seven-int table packs material,
advance and biased center coefficients into disjoint10/3/4-bit fields. Encoding
P=M+(A<<10)+((C+3)<<13) and decoding P&1023, (P>>10)&7, (P>>13)-3 preserve
all original coefficients. P is signed nonnegative<=98624; empty24576 and king0
are distinct. Board.v remains decoded signed int. Each value's abs<=910 and a
conservative64 occupied valid squares bound58240 fits int32, while a legal32-piece
position bound is29120. No packed cache or carry/unsigned/narrow16 policy appears.

Actual old/new definition-name-only functions pass832 valid piece/square cases
against a separate M/A/C oracle and bit unpack in one fatal host SAN compile/run.
This component does not execute put/cache/Board/search/main/loader. Receipt11043B
SHA8f81b48f0ff8be3a073ef5af80ba1e5e050a63d1e82f34af8b0ee1920174722d.
Only the coefficient function changes; hash/update/full HCE/PVS/QS/learners,
coherent full-key atomic16 TT, SMP and explicit SSE4.2/CX16 profile remain.

Native scalar7740→7708B and HQ8128→8096B; text falls37B each. Fixed21 packet
4810→4800B and5032→5011B, nonpacket1137B unchanged, whole5947→5937B and
6169→6148B. Actual cost native2/encode2/shipping-loader2/control0 and Python
old/new restoration4 pass. Cost34687B SHA:
ce4028902b8334190fbe0db2a5fbc30f4c70c242b2595473d3d1bbc91f6ef953.
Audit-loader discovery compiles two exact CHECKPOINT images without executing
them. Root independently reads all eight files, raw ELF64/PHDR, entry offsets,
RX/BSS/guard geometry and packet suffix. Exact identity/form/entry/model literals
and verifier EXPECTED follow these bytes; inspection/lifecycle bodies are unchanged.

One ordinary builder reproduces both native/whole twice and audit once. The
selected positive verifier passes pre-entry2, quit/EOF4 sessions and12 legal GO,
exact restored RX, zero BSS/padding, guards/NX, stable3 TIDs, stdio/no observed
helper, reader EOF and physical settlement, with no forced cleanup. No negative
decoder, RIE/ptrace/register/personality campaign or game is run. Producing21 and
build-input17 readback precede README/recipe-only annotations. Final index SHA:
8518028b77b41e4ae813ee3e3d2b7b47281f04ce838f9c7153f13c879a2e7f37.

Full F remains4537B/441B over;
all-family goal and compression beyond size passage remain active. Final target
resources/many-core/strength and own-ELF4KiB eligibility remain separate.

## B overlong-line drain and retained-attempt policy — 2026-10-21

B's full-shipping drain replaces an85-byte span with68 bytes while retaining
getchar order, LF/EOF admission, and full discard when any nonterminal byte is
present. The exact replay stage follows clock presence; DEV bypasses it.
The actual complete file decreases5146→5144 B (1048 B above4096), with source
10548 B/SHA-256 `d91416e56e2b7716b9df2bec5db22c1f9d3f6ded5598d80741d68487ecc09bbb`
and whole SHA-256 `fa2196f2093d5701f946415260bb426b7f7f1feb6e6dc776b834bae5449fff21`.
The entire native has a new identity; equal native length is not native equality.

The measured selected wrapper passes three actual boundary sessions covering
32767/32768-byte LF/EOF admission and recovery. Ordinary --dev regeneration
then reproduces shipping and unchanged DEV twice. The unchanged selected
verifier passes actual quit/EOF sessions, eight legal finite GO results,
exact restored native, stable three startup TIDs, private-path/helper absence,
closing result, reader EOF and physical exit. Its summary SHA-256 is
`6f6111b89becb33e9a6a4a096bc03ae4896acd27a24d9280e8a7daa7a0edca7d`.
Cancellation causality remains unproven. These local two-worker/TT18 observations
do not establish final server resources, many-core behavior or strength.

The first prepared helper used Python bytes literals that decoded backslash-n
into LF. Static review caught the mismatch before its execution; the original
helper and finding remain external evidence. Raw bytes literals correct the
cause, and exact pure replay plus the ordinary build use the corrected helper.
This preparation failure is distinct from the measured C candidate and is not
erased by the successful normal run.

PR13's retained-attempt rules apply to subsequent work: prior size losses remain
context-specific observations, not permanent name exclusions. The same drain
was larger for A/C/E/full F in this measured context, and B's two-pass piece
updater was also a size loss; their inputs, derivations, costs and unqualified
status remain preserved. Changed source/tool/codec conditions require a new
measurement and the necessary current semantic/native/restoration checks.
Recorded comparison does not revalidate or readmit an old candidate. The engine
plan now states this boundary, and ordinary fixed-recipe builds remain replay
of the selected construction rather than hidden research searches.

## Fixed compiler argv comparison and maintained E5010 (2026-10-21)

The current B/C/E wrappers compare a literal argv list with a fixed ASCII
string followed by zero-argument `.split()`. Every compiler argument is nonempty
and whitespace-free, so the ordered argv is identical; source, native, codec,
Popen keywords, private temporary path and compiler/exec lifetime logic remain
unchanged. Source spelling/columns and failure-traceback bytes are outside this
manual representation comparison. It does not assert NVCompact's separate
`compile-input-only` observation contract.

The actual complete-file results are B5144→5145, C4952→4953 and E5011→5010 B.
All six old/new strict Python and independent CLI restores pass. B and C remain
unchanged: their larger candidates are retained size losses, not semantic or
restoration failures, and may be measured again in a changed source context.
The frozen source plan and bounded cost producer are preserved externally at
`rove4k-bce-bootstrap-argv-source-20261021-evidence`; the actual cost receipt is
26855 B/SHA-256 `5610bf56f5f0ca8776490f395e662a9b4419154f149d3661ecece0c78ef8308f`.

Only E adopts this spelling. Its ordinary --dev builder reproduces shipping
and unchanged diagnostic forms twice; the unchanged selected verifier passes
two quit/EOF sessions with eight legal GO results, exact restored native,
three startup TIDs, absent private paths/helpers and physical exit. The build
receipt SHA-256 is `f25d18bf04902d67b8f5894cdb9a2a7f3c91fe9f7d2c29541637f67f07930868`;
runtime receipt is `64744c39bf9130ab16abbff516d872331c274e7cfbdd066564d66d609fd6e93e`.
No cost, normal-build or selected-runtime retry was needed. This is a local
two-worker/TT18 size and execution result, with no new game, strength or final
server-resource claim. E remains914 B above4096.

## C4934 caller-owned continuation slot (2026-10-21)

C's shipping search passes the already-made child's signed piece slot to all
four recursive calls, rather than passing a Move and decoding the same child
piece again. The root explicitly supplies neutral6. Quiet cutoff learning
reuses that slot, including the correct child roles for promotion, EP and
castling. The learner's only two callers use positive depth-square bonuses,
allowing its redundant abs to be omitted in this fixed caller domain.
The readable engine, DEV API and SIMD evaluator body remain unchanged.

Source10072→10032 B gives an actual complete-file4952→4934 B. One native
compile compares the old list wrapper4934 with the retained split wrapper4935;
the list remains selected. The new native has a different full identity,
despite the unchanged26368-byte length. No old native/core execution receipt
is relabeled as a run of this image.

One fatal ASan/UBSan fixture run compares31 actual old/new search pairs,
including22 special-child adapters and128 legal children, plus8257536 positive
bonus/int16-cell cases. Scores, witnesses, full Worker/learner and TT bytes
agree; nonzero history and continuation updates are observed. The component
fixture starts no production main or worker pool. Its SHA-256 is
`fff573aab97d612de83984bc29410ab29f9c396f91aec03e9153c754c141a0be`.
An initial preparation used a struct assignment for a byte-level snapshot;
the preserved correction uses memcpy before any compile/run, rather than
changing a score or expected behavior.

Ordinary --dev regeneration then reproduces shipping and unchanged DEV twice.
The unchanged selected verifier passes quit/EOF sessions with8 legal GO results,
exact restored native,3 startup TIDs, absent private paths and physical exit.
Build receipt: `949ba4a6c9ed86354ec7ba6a9b50084a42fb34fc00df90f70ac46da1ec53a31e`;
runtime: `0108890c067ff67c95c81205ee57951f921e4c311664fed9946d5e63598c153e`.
Inputs, failed preparations, the finite list/split comparison and producing
versus annotated recipes are preserved in the external
`rove4k-c-search-context-*-20261021*` evidence folders. C remains838 B above4096;
final hardware, many-core behavior and strength are separate open work.

## Full/default F4505: depth, repetition and fixed integer tokens (2026-10-21)

The full F source changes8821→8793 B by saturating private QS depth at0 and
expressing repetition as same-parity distances2,4,... bounded by halfmove count
and history length. Production root depth is1..126; the relation is
new_depth=max(old_depth,0), preserving TT's zero-QS horizon, positive-depth
learning, check evasions and the unchanged ply/mate limit. Arbitrary direct
negative-depth calls to the new private U are outside this contract. Stable
worker history length1..4223 keeps the same key order inside4224 entries.

Actual QS-only4533 and repetition-only4526 compare with their separately
compiled/encoded composition4521, from4537 B. A further fixed-int specialization
removes MOVES512/MATE30000 definitions and expands their11 uses; source becomes
8755 B and the complete file4505 B. This last step has the same entire native
as the8793-byte candidate. A coordinate formatter loop is retained but not
selected:4523 B alone and4507 B with macros are larger than4505. Those are
context-specific size results, not permanent exclusions or runtime qualification.

One fatal ASan/UBSan compile/run compares18 actual old/new U cases,13 TT-horizon
pairs and44 synthetic history pairs, including explicit negative-to-zero QS
adapters. Worker, TT, score/witness and history-key order agree. The actual
think/MTD driver is unchanged in source; this fixture does not call it, and
synthetic histories are not presented as legal games. Focused receipt:
`0fe01764a65c81c9c620eee164086cdb65e3a5abe47c448fc8313155661f978f`.
The first fixture preparation's inappropriate raw-HCE witness assertion for a
dead-position score0 was corrected before any compile/run; its original
source and the unchanged score0 expectation remain preserved separately.

The ordinary full --dev build reproduces shipping and unchanged DEV twice.
The unchanged selected verifier then executes the actual driver in quit/EOF
sessions, with8 legal GO results, exact native restoration, stable3 startup
TIDs, absent private paths/helpers and physical exit. Full build receipt:
`32f9b1c30c6a126dd05561b43c4bc1241ec62bfc01eff836c8358b420df63267`;
runtime: `f7b3d66eee190d87b548c4cb80d2205b2c6fa9ef44d6e2a98759369445df3e73`.
Separate ordinary optional-policy builds preserve4325/4051 B and generate
the new full_reference through both added stages; no optional-policy DEV or
runtime is rerun. Full's source/native/whole SHA-256 values are respectively
`8a6383c9185defbcb68c03a3acfca72c0b16f2ccec09a44d9575d80a262365ae`,
`6b59a5440c580c8073defe03518b5bfe25269547d299dff63ab98e5da6dd356f` and
`4608c2c875cebf7b353c417f5d3aa9623ed3c85ef02affb666b30339624f8c7c`.
Full remains409 B above4096, retaining positional HCE and all learners.

The source plans, finite costs, unselected candidates and preparation failures
remain external in the depth/repetition and format/macro evidence folders.
Current NVCompact0.5 automatic whole-payload search is separately not admitted:
unrestricted literal-style/line changes can affect the actual Python wrapper's
uncaught-error traceback locations, contrary to its compile-input-only contract.
Its preparation also stopped at missing Clang before writing a manifest; no
source-search candidate compile/codec/engine ran. Both facts remain in
`rove4k-nvc050-full-f-current-20261021-evidence/non-admission.json`, distinct
from the successful fixed source transformations above. No new strength,
many-core or final-server acceptance is inferred from this local profile.

## D5914/6125 exact clock/inc branch sharing (2026-10-21)

D's readable runtime shares only the wtime/btime/winc/binc branch, preserving
the original four exact-word tests in short-circuit order. It consumes amount
once even for opponent values, then classifies time/inc through a character
inside the already-admitted4/5-byte word. Missing nonnumeric values still
rewind D's cursor; own-side zero/duplicate/overflow handling, DEV branches,
budget, deadline, fallback and completion fences remain. Reply stays256 B.

Runtime14987→14885 B gives native7676/8032 B and complete own-ELF5914/6125 B,
23 B smaller in each form. Reply-only5936/6150 and the actual union5928/6129
are preserved but not selected. Full HCE/PVS/QS/learners, atomic16 full-key TT,
SMP, fixed21 models and explicit ISA remain. Static admission binds each new
native's hash/size/entry; RX2pages, BSS175092, guard/reserve/NX geometry and
guard bodies are unchanged. Only two packer identity/model literal blocks
change. The positive verifier's EXPECTED data changes, with its entire remaining
29214-byte body unchanged at SHA-256
`389ac04925b5ab4597a34a9ac8b318de572da9b0d9b293b384eea785f10cc4fa`.

One fatal ASan/UBSan compile/run compares34 parser/budget cases in four actual
old/new DEV0/1 host projections, with no production main or workers. Focused
receipt: `ceb2b0f3492bb5a82438d4dcd7ab31ecff744b44c8935d4cde7f81f1ba750817`.
The interrupted work's two completed checkpoint-loader discovery compilations
were recovered by exact receipt and terminal/PID evidence, rather than repeated.
Ordinary regeneration independently reproduces both native/packet/shipping and
checkpoint forms; positive verification passes two pre-entry inspections and
four quit/EOF sessions with12 legal GO results, the restored mapping, zero BSS,
padding/guards/NX,3 startup TIDs, stdio, absent children and physical exit.
No RIE/ptrace/register/personality/fault campaign is performed.

Build receipt: `2460e3cc44e722123733e973ea22cd1c9bf95dd55843f9126c027ed8d99544ad`;
runtime: `30929ddd6a8cfdce94222e535bd89f105098c4951d0cf406bfc561a4954ffeeb`.
Final source/cost/producing-recipe and post-execution annotation identities are
in external `rove4k-d-clock-normal-promotion-20261021-evidence/final-index.json`,
7498 B/SHA-256 `e97ef10a73b99f1c0c1f6adccdc3510f601d189f340386236623b00d02f802d6`.
These local two-worker/TT18 results leave1818/2029 B above4096, without new
strength, many-core or final-hardware acceptance.
