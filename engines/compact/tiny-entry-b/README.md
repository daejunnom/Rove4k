# Maintained B: seek-implied compiler-source flush — 2026-10-24

Fixed candidate whole **5285→5281 B (-4 B)**; bootstrap
11669→11659 B. Whole SHA-256:
`810657db271fe536605bf4c92d1b9bf4b5a60a1d7bf2cc96d8153c5fde5f8480`.

The final pure `compiler_seek.py` stage runs after every prior source/literal,
oldBOOT and W1W2 guard, including the exact current W1W2 bootstrap pin. It
receives that metadata plus the same frozen stdin-owner producer and inverse,
restores/replays the owner exactly, and removes only `f.flush();` before
`f.seek(0)`. One byte span, protected gaps and full byte/AST inverse are checked.

This contract covers builtin regular `io.BufferedRandom` from `open(w+b)` and
its direct seek0. Python3.12 specifies seek flushes its buffered writes.
A pending write failure now surfaces at seek, still before compiler spawn;
arbitrary filelikes, custom open, explicit flush hooks, syscall/traceback
identity and identical cancellation timing are outside the contract. Descriptor
ownership, original UCI FD0, source/argv spelling, masks/publication, WNOWAIT and
group settlement remain protected. No extra prepared-error injection is added.

Canonical/source/native/DEV, model/search/TT/learners, workers, codec and header
are unchanged. Producing status: PENDING ordinary --dev and unchanged selected.
These six producing files stay frozen; completion belongs to the external
receipt. The transform runtime-qualified flag remains false. Earlier cost,
normal and IO evidence below keep their original inputs and scope.

## Earlier producing and maintained evidence

# Maintained B: terminal compiler stdin and shared wait — 2026-10-24

Fixed W1+W2 first-cost winner: **5337→5285 B (-52 B)**; still 1189 B above4096.
Bootstrap 11789→11669 B. Whole SHA-256 is
`30ff407e5b5d4d81c812814858e53e7c5d4810ac9f0ae5bc4f163facaafd4165`.

The builder freezes the explicitly pinned `engines/scripts/compiler_stdin.py`
and calls `transform_bootstrap(script, shared_wait=True)` after every existing
literal/compiler-owner/late-bootstrap guard. The exact previous bootstrap
length and hash remain an operational guard. The helper reconstructs the
previous corrected owner, preserves opaque source/argv spelling and protected
regions, and verifies its complete byte/AST inverse. DEV bypasses packaging.

W1 writes, flushes and rewinds source in the existing private directory before
spawn and passes that regular file as compiler FD0. The original UCI FD0 stays
open. Compiler stdin becomes seekable, source preparation failures precede
spawn, and pending cancellation can be delivered after publication/unmask;
arbitrary source filesystem observations and preparation-cancel compiler0 are
outside this compile-input-only contract. W2 shares the existing leader/group
wait body while retaining WNOWAIT observation, deadline/KILL order, group drain
before final reap and existing workspace-retention failure behavior.

Source, native, canonical/DEV, model/search/TT/learners, fixed workers and codec
expectations are unchanged. Firstcost proves source transformation and whole
restoration only; ordinary --dev and selected runtime are pending. Historical
receipts below retain their original inputs and qualification scope.

## Previous maintained evidence

# Maintained B: completed-depth job token — 2026-10-24

Current corrected-owner whole **5342→5337 B (-5 B)**, source9759→9744 B,
bootstrap11804→11789 B. Candidate source SHA is
`4b3412e3dddbe4cc9b40172be66d577aa998dc65e4ffa5876827f6b92654c5a8`;
whole SHA is `8f3a296d682c1ea1db74288ed76d285de4582df3ebe4599078cae1c0f7b7b963`.
One fresh fixed-argv native discovery compiled26080 B/
`59eea719b15f84ef83dcdc1918e1037c234578df417a537f7997fa3593648e28`.
Native/layout identity and RAM savings are not claimed. One ordinary `--dev`
and the unchanged selected verifier passed for the actual new source/native.

`shipping_depth_token.py` changes six owned roles with seven protected gaps and
a full inverse. Signed worker depth uses -1 for published/unclaimed, 0 for
claimed/no completed depth, and1..126 for completed results. GO keeps U drain,
clock parsing and deadline order, then publishes pending2 and both -1 depths
under qj. Each stable owner pointer claims its own depth0 under qj before
think. Only think's earlier depth0 reset moves to that boundary; completed
best/score/depth commits and all search bodies stay unchanged.

Actual current B startup already folds readiness into qk=2 and the null-w
loop-head epilogue; there is no separate qn. An earlier external source-only
proposal incorrectly described old qn metadata as current. This candidate
preserves the actual folded startup and changes no ready counter. Last
pending0 retains result and own fflush before broadcast; the producer drains
before reusing root/history or publishing another job. Main and its
partial-create goto-shutdown/actual-created joins remain byte-identical.
Partial-create behavior is currently a source argument, with no new fault
injection or internal per-worker claim observation. Private direct-think
callers must seed depth0; arbitrary-entry equivalence is not claimed.

Legal-LVA/SEE incomplete handling, singular same-position/excluded TT and
learning policy, PVS/QS, full-key TT, all three learners, HCE/bitboard/move
rules and Worker score yl remain protected. Canonical/DEV source/native
expectations and model distinctions are unchanged. Previous source stages
and helper pins are preserved. Packaging restores9759, consumes the existing
generic B literal envelope and corrected compiler owner, then replaces only
the source bytes literal. B had no fixed prior literal-stage inverse guard;
existing fixed source-generation guards still precede the new late stage.

Finite firstcost used baseline encode0/candidate encode1, Python strict
inverse1 and CLI inverse1, compile/runtime0. The separate native discovery
compiled only the candidate once and ran no engine. Existing codec/header
and73 B prefix are unchanged. Candidate5337 remains1241 B above4096.
The ordinary command reproduced the shipping source/native/bootstrap/whole
twice and the unchanged old-minimax DEV source/native twice. The unchanged
selected verifier passed quit/EOF sessions with three stable startup TIDs
each, eight total legal GO results, the exact deleted new native image,
absent private path/helper children, one closing result and physical reader
EOF/exit0. Original ordinary/selected leaders were retained WNOWAIT until
other group members were absent, then reaped0; groups were absent with no
forced cleanup or owned handles. Source closure stayed fixed. No internal
per-worker claim observer or partial-create fault injection ran; their
ownership explanation remains source evidence. Whole-process activity and
physical exit do not prove cancellation causality or performance/strength.

Producing recipe251378 B/7edf65e0672c83cc46a6a7ac99544b958dd13734c96291fed435e039361246f3
contained pending-normal annotations. The final recipe only records the
completed normal evidence; source, compiler/codec and expected tuples are
unchanged by those annotations. Build receipt280405 B/
d8c14d57cc68aa6786240662fdf09b76caf337a6bde27bda8ee5ac6fd39c5c82,
runtime receipt97220 B/7547b839f2e74851d124f673ffa32872ac03aba9c426707cf5872b59a6daa95d.

# Previous owner qualification: EP normalization reuses the legal maker — 2026-10-24

기존 int alias 뒤 shipping 전용 `shipping_ep_maker.py`가 EP 정규화 C의
Board 복사·세 setter 호출·왕 공격 검사를 실제 legal maker h로 공유한다.
고정 source9797→9759 B, bootstrap10826→10788 B, 전체4954→4950 B(-4 B)다.
Native는26112 B로 크기가 같고 SHA는
`962a7e2be52ee84d5ca3112b95a483fe62efe90a7f978f557d57cf870b86be73`로 바뀌었다.
`.text`는92 B 줄었으며 whole SHA는
`47fa3140f96eda35ac3048d72239b53ed344ae2e19397a3fa06904f1166d21de`다.

실제 C는 h의 king-safety 뒤, metadata hash/context 최종화 전에만 호출된다.
e>=0이면 생성·검증된 double pawn push 뒤의 빈 EP target/victim pawn/half0이다.
합법 EP의 h 반환101을 nonzero로 소비한다. Inner h는 EP에서 e=-1을 설정하므로
nested C가 즉시 끝나며 half는0→1→0이다. B의 mailbox·bitboard·king 일치를
유지해야 하며 다른 가족의 mailbox-only scratch 가정을 적용하지 않는다.
이전 scratch는 own pawn→victim, 새 maker는 victim→own pawn 순서로 제거한다.
서로 다른 세 칸과 완료된 공격 판정만 사용하므로 실제 도메인의 합산/XOR는 교환 가능하다.
Inner scratch의 h/r/half/rights는 버리는 private 값이고 완성된 child/key로 게시하지 않는다.
새 time/atomic/TT/learner 접점은 없으나 추가 maker 작업·stack·타이밍과 시간제
nodes/depth/result 동일성·성능·기력 우월성은 주장하지 않는다.

단일 exact span/두 보호 gap과 전체 inverse를 검증한다. SEE legal-LVA/incomplete
stop·singular same-position/excluded·full-key TT·세 heuristic·SMP·promotion tactical
bit·입력 처리의 다른 source bytes, 정본, 기존 guards와 DEV/model flags는 보존한다.
기존 common literal은 새 C bytes를 그대로 소비하므로 별도 literal inverse adapter는
필요 없다. Compiler/codec nice32·73 B header·FD0 template은 이전과 같다.
ONE firstcost는 기준선 compile/encode0, 후보 각1과 strict Python2/CLI2 전체복원,
EOF/trailing0을 통과했고 원 outer/child가 terminal/reaped/group 부재/forced0/owned0이다.

EP_MAKER_NORMAL_PASS: actual 새 TU는 그대로 include하고, 이전 C와 h 정의에
정의 이름 두 곳·h의 C 호출 한 곳만 alias해 old normalizer 경로를 분리했다.
기존 B focused FEN ingress와 양쪽 EP를 재사용하고 양쪽 file-pin/rank-discovery를
최소 추가한 fatal GCC13 ASan/UBSan 1 compile/1 run을 통과했다. 실제 generated
double-push6·EP6(합법101 두 개, king self-check 거절0 네 개), normalizer pair8,
완료 Board20에서 old/new 반환·typed mailbox/14bb/k/HCE/hash/context/half와 부모
bytes 보존을 확인했다. 완료 child의 S를 먼저 제거해 entry를 역투영한 검사는
내부 C-entry observer나 모든 trace의 관측을 뜻하지 않는다. 주어진 entry의 h/r는
미완성 값이며 normalizer의 e 외 caller-field 불변과 inner scratch 폐기만 확인한다.
SAN은 가상 AS64TiB와 별도 hard RSS512MiB/CPU25초/wall30초를 사용했다.
Fixture compiler에 기존 C runner의 불필요한 -mavx2가 남은 실제 argv를 보존했다.
B source에 SIMD intrinsic은 없지만 이 SAN 결과로 B 최소 ISA 동일성을 주장하지 않는다.
실제 ordinary/selected는 원 B의 no-mavx2 compiler 그대로이며 새 native/whole 전체가
고정 firstcost와 같다. Ordinary --dev 한 번에서 shipping 두 사본과 실제 이전 DEV
두 사본의 전체 bytes를 재현했다. Unchanged selected 한 번은 새 image에서
quit/EOF 두 session·여덟 GO·3 startup TID·private-path 제거·closing bestmove 한 번·
reader 완료와 물리 종료를 확인했다. 이전 성공을 새 native의 검증으로 상속하지 않았다.
원 focused/normal outer와 child는 모두 terminal0/reaped/anchor 유지 중 extras0/
당시 group 부재/강제정리0/owned0이다. 이후 helper/build/expected는 그대로이고
recipe/README 완료 주석만 바꿨다. Cancellation causality는 unproven이며
시간제 trace·stack 크기·기력/성능·모든 core qualification·새 CI는 주장하지 않는다.

## 이전 단계 기록

# Maintained B: one pool condition — 2026-10-22

The fixed first-cost complete file is **5023 B**, source
**10242 B**, native **26224 B** and bootstrap
**11271 B**. Complete-file reduction is **9 B**
from the actual FD0 baseline; source reduction is 28 B.
The new entire native is `bc52f4a88573212b34e3365354cc257e1a63ddebf8499676cc9fc83784da87b5`.
The shared pure `tiny-entry-a/shipping_condition_bce.py` is called with
explicit family B after its original last shipping C stage. B uses a separate qn ready counter and qk pending0.
Its exact 5 spans/6 gaps/full inverse preserve every other byte.

All waits keep the same mutex and original while predicates; all four
notifications remain broadcasts in their original positions. Startup each
worker notification, pending2/epoch/seen, last result+printf/fflush before
completion notify and drain before root/history reuse stay intact.
Partial-create still skips normal drain and publishes quitting before
joining only created workers, without an additional stop store. Physical
termination relies on successful joins; the existing nonzero-join f2/free
error policy is unchanged and not newly proven safe.

One condition queue can additionally wake the wrong predicate class. Those
waiters recheck while under the same mutex, but reacquisition/contend,
scheduling/latency and deadline node/depth/result observations may differ.
No exact timed trace, performance, RAM or strength equivalence is claimed.
Canonical/DEV, all existing model/features/TT/learners/input/search bytes,
compiler/profile/codec/73-byte header and FD0 template stage remain fixed.
C keeps its own -mavx2 and nice64; B/E keep nice32.

Firstcost reused actual frozen baseline bytes, compiled/encoded the sole
candidate once and passed strict Python2/CLI2 bootstrap/source restoration
with EOF/no trailing data. Baseline compile/encode0 and candidate runtime0.
The original preparation syntax error and precompile B missing-FD0-context
gate failure remain preserved separately; neither executed a candidate
compiler/encoder. Corrected run uses the actual frozen readonly helper and
unchanged package function. Firstcost index SHA-256 is
`377774bfe8b574009a75a496c8bb988de9f24133fb86faa8bbbaf3ac0e34495f`.

Ordinary --dev ran once and reproduced shipping twice and unchanged DEV
twice. Entire source/native/bootstrap/whole matched the original firstcost
bytes, and DEV source/native matched the actual previous FD0 baseline.
The unchanged selected verifier ran once on the actual new wrapper: quit/
EOF two sessions, eight GO calls and main+two worker TIDs per session.
The new native image, private-path removal, finite input, closing bestmove,
reader completion and physical exit were observed. Build receipt SHA is
`4a056d0466aa6325cded98fc38bf180997958a70e47acf71acd656c4df93764c`; runtime SHA is
`86bd1bad6ceb6f58648751ede623a6acf3d964c93f99ab70a1494d7ee47cb206`.
All original handles settled/reaped with groups absent at settlement, no
forced cleanup and owned0. F4 original normal completed before the serial
B->C->E ordinary/selected stream; F next normal was notified only after all
BCE original handles closed. No late bare PID/TID probe or extra positive
run is used. Producing recipe SHA is `47b85eabe879f1420555a12e1595dd413420b98794cd3ed17470f14f6415f994`;
final recipe/README overlays are completion annotations only. Existing
runtime ancestry is separate; this validates the new image in the narrow
selected wrapper scope. No new SAN/NVC, codec/name sweep, optional consumer,
feature deletion, training, performance/RAM/strength or new-head CI claim.
The4096 B target and broader qualification remain open.

# Maintained B: shared fixed readonly flag template — 2026-10-22

The fixed first-cost file is **5032 B**, down10 from5042.
Bootstrap11309→11299 B removes10 bytes. Entire C,
native and DEV bytes, compiler/resources and original codec/header73 remain.
The4096 B target remains open. This is a Python template spelling change.

The explicitly frozen shared tiny-a/shipping_readonly.py accepts only this
family's fixed legacy template and one FD span, with two protected gaps,
full inverse and one C marker. Existing local/helper/legacy marker/prefix
guards run first; C also keeps its original Popen argv guard before this
stage. C source insertion and all prior literal helpers remain unchanged.
Standard Linux os.O_RDONLY equals0; open/path/FD/unlink/exec and exception
control are retained. Generic OS, os monkeypatch, Python source/bytecode/
traceback and timing equivalence are not claimed. F/F8/optional opt out;
source_package and shared prepare code are not modified or auto-enrolled.

Original four-family FD-only first-cost index:
`a4cf965cfd83aeba97c6bb9f372f0283371093edebf47cb627fdc1421457f14f`.
One candidate encode per family and strict Python/CLI restore passed, with
baseline/candidate compile0 and baseline encode0. The actual current C and
native were reused, not recompiled. Old sourceproof/preparation errors and
other LOSS/candidate records remain separate outside Git.

One ordinary --dev builder reproduced shipping source/native/bootstrap/whole
twice and old DEV source/native twice. Actual C/native/DEV entire bytes equal
their qualified predecessors; new bootstrap/whole equal the fixed firstcost
artifacts. One unchanged selected verifier passed quit/EOF2 sessions8 legal
GO epochs,3 stable startup TIDs each, the original exact restored deleted
native, absent private/compiler paths, finished readers and physical exit.
Cancellation causality, timed-node equality, performance and strength remain
unproven. Normal calls ran serially A→B→C→E with original owned handles.

Actual build SHA-256:
`9f959c0e51c559d81dfc32995aed19686b9ae626fc37d777e1af57069772f476`.
Actual runtime SHA-256:
`ac7f437c909bbb4aedce82bc7ebac13d0e3e7b80b91ef7a9ad97441005ee6049`.
All eight original command handles exited0, were reaped and had absent groups
at settlement; forced cleanup/owned handles0. No late bare PID/TID probe or
product retry is added. Producing recipe/source and final annotations remain
separate. After execution only recipe/README completion notes changed;
shared helper/builders/expected/profile/codecs stayed producing bytes.
Only the shared helper and A/B/C/E build/recipe/README are owned. No new
semantic fixture/SAN/NVC/game/codec search or rootdocs/Git/CI work is added.
Historical sections below retain their own identities and scope.

# Maintained B: direct shared-walker ports — 2026-10-22

The fixed first-cost result is **5042 B**, down31 from5073. Compact C is
**10270 B** (−124), native **26248 B** (−48), bootstrap **11309 B** (−124).
Native identity is new1494a7d9...; this is not prior-native runtime reuse.
The4096 B goal remains open with946 B remaining; no feature is removed.

The pure shipping_forwarders.py follows shipping_declarations only in
shipping. Nine exact regions remove l/e/v forwarding definitions and connect
seven consumers directly to the unchanged c walker. Ten protected gaps,
9945-byte complement and full inverse are checked. P's int check keeps !!c
so high-bit-only uint64 attack masks become0/1; Q keeps the entire mask.
Generation count remains0..432 within MOVES512. H's output parameter c is
renamed to private j to avoid hiding the walker, preserving its h output use.
Walker body/castle recursion, Move ordering, make/SEE/Board fields, HCE,
PVS/QS/singular/correction/learners/full-key TT and worker publication/drain/
join remain. Canonical, DEV and all earlier helper guards bypass this stage.
General external C ABI, removed implementation symbols and native/frame/
stack/timing equality are not claimed.

The original control bootstrap11433 was reconstructed exactly before one
candidate compile/encode with baseline compile/encode0. GCC13/C11/Os/pthread,
workers2/TT18/PLY128/DEV0 and73-byte header/ALONE9e/BT4/64MiB/lc2/nice32
are fixed. Python old/new2 and actual xzCLI old/new2 restored exact bootstrap
and source, with EOF/trailing0. Original firstcost and prior LOSS remain
outside Git. New fixture/SAN/NVC/search/codec sweep are not added.

One ordinary --dev builder and one unchanged selected verifier passed.
Shipping source/native/bootstrap/whole reproduced twice and match the fixed
firstcost entire bytes; old DEV source/native reproduced twice and remain
entire-byte equal to the actual qualified predecessor. The new native image
1494a7d9... was observed during quit/EOF2 sessions and8 legal GO epochs,
with3 stable startup TIDs per session, deleted exact restored image, absent
private/compiler paths, finished readers and physical process/group exit.
The two original command handles850/883 exit0/reap/group-absence at their
settlement; cleanup0/owned0. No late bare PID/TID gate is added. Cancellation
causality, timed-node equality, stack, performance and strength remain separate.

A original ordinary/selected terminal receipts precede B; E was notified only
after B's original full lifetime closed. Actual build198225 SHA-256:
`fbd9e07ff22644fc9daac389a68ded5d1c6a5422f947b3b6cf5b31c0b76a9e5d`.
Actual runtime49506 SHA-256:
`1be703746643cb1539dcf2d14864eb006b3252f6dd208c520d9db1a72184bf95`.
Producing recipe and source closure are frozen separately; only recipe/README
completion annotations change after execution. Helper/build, expected bytes,
all earlier guards/canonical/DEV/profile/codec remain producing bytes. No new
semantic fixture/SAN/NVC/fault/game/benchmark or final4KiB acceptance is added.
Only this helper/build/recipe/README are owned; rootdocs/Git/CI are separate.

First-cost index SHA-256:
`187a2a764613256ddedb1a1a152e0e61628d1c70198e6bc86465ecbc2f6377b9`.
Source-only proof SHA-256:
`5fe2b209e5fe3ca66d9f6b51afd086ee8b14b216a96209d3baee82ac35b481ee`.
Historical sections retain their checkpoint identities and scope.

# Maintained B: HCE declarations source −8, whole TIE, ordinary/selected PASS — 2026-10-22

The maintained whole remains **5073 B**, while compact C is **10394 B** (−8)
and native remains **26296 B**, entire bytes identical to the predecessor.
The original first-cost TIE0/unselected record is preserved. A subsequent
explicit selection uses source reduction with zero whole increase and full
native identity; this is a source-size choice, not a measured whole-file gain.
The4096 B goal remains open and every B feature is retained.

The pure B-owned `shipping_declarations.py` runs after cached-evaluation only
in shipping. It changes `;int j=` to `,j=` and `;int m=` to `,m=` in r(). The
same automatic int declarators keep their scopes, initializer full-expressions,
lexical dependencies and bounded arithmetic. Coefficients, abs calls, qi reads,
return and every other byte remain. Two exact spans, three gaps,10388-byte
complement and full inverse are checked on every application. Canonical/DEV
and all earlier helper input/output pins remain unchanged. Fresh source-closure
collection follows recipe helper_sha256; no fresh/archive execution was added.

One ordinary --dev builder regenerated exact shipping source/native/bootstrap/
whole twice and exact old DEV source/native twice. One unchanged selected
verifier passed quit/EOF2 sessions and8 legal GO,3 startup TIDs per session,
actual native restoration, absent compiler/private paths and physical process/
reader exit. Original parent/build/selected handles terminal0 with group absence
at original reap, cleanup0/owned0. No late bare PID/TID gate was added.
Cancellation causality remains unproven. C/E selected execution was serialized.

New source SHA-256: `61f6dabc7b171c864c3d3511906799e13b638023d96a537c1fa15a05a0648c63`.
Whole5073 SHA-256: `b7698bdcb13626ef19fc16156095f5991819a1c3d857d52b47ba6994052d8f26`.
Same native SHA-256: `b38c33127b9913366b58b24dc3275d371d66caba6af3d507bb330eb14efcb7ea`.
Build receipt: `55acc523acffc8209b4b8674777ceeddd9b5d58c996a2905fd0aa448f42c4d60`;
selected receipt: `59df1f3b6d4a6e2c2445c18ccae46fd3f4e637778b046df4c4c0fdd7c2ee684b`.
Producing recipe: `81887349ea604895a751a924038790f1054115d426384ba0faa8c2e15495dec1`.
The producing closure stayed frozen through both original commands; only
recipe/README completion annotations changed afterward, with no rebuild.

Actual fixed-compiler native proof and strict Python2/CLI2 restore reuse the
original compile1/encode1/baseline0 first-cost result. Its frozen TIE index is
`fce4d2edb706a48e54ddd1f5c7433d5a23906af61f4da151955e91eb4c809ad2`.
No extra semantic fixture/SAN/engine/game/performance check or codec/name sweep
was added. SEE/clock poll/TT/workers and termination policy remain unchanged.
Original source/TIE and distinct mate/halfmove/combined/M-two-pass losses remain
outside Git. General source/traceback, RAM/stack/speed and strength are not
claimed. Before/producing/final evidence remains in
`rove4k-b-hce-declarations-promotion-20261022-evidence/final-index.json`.
Historical sections below retain their own source/image/receipt scope.

# Maintained B: raw evaluation reuse and shared73-byte header; focused comparison and ordinary/selected validation passed — 2026-10-22

The combined maintained file is **5073 B**, compact C **10402 B**, native
**26296 B**. The sourcecache stage reuses the entry raw evaluation instead of
recomputing p->s*p->v, removing7 source bytes and2 actual whole-file bytes from
B5079 to5077. The shared73-byte header removes4 further bytes to5073.
Native length is unchanged but its entire image differs:
`b38c33127b9913366b58b24dc3275d371d66caba6af3d507bb330eb14efcb7ea`.
No native metadata exception or old runtime/stack class is inherited.
The4096 B goal remains open. Focused sourcecache-only actual old/new validation passed.
One ordinary --dev builder reproduced source/native/bootstrap and combined5073
whole twice, plus exact old DEV source/native twice. The unchanged combined5073
selected wrapper verifier passed quit/EOF2 sessions and8 legal GO,3 startup TIDs
each, exact new native restoration, absent helper/private paths and physical
process/reader exit0. All six startup TIDs were absent after the sessions.
Cancellation causality is unproven.

The pure B-owned `shipping_cached_evaluation.py` runs after singular-depth.
It replaces `int zE=zi-p->s*p->v;` with `int zE=zi-zF;` in one fixed span,
preserving two gaps,10389-byte complement and full inverse. zF is the same
raw int evaluation initialized once and never assigned/addressed again.
Actual make/SEE use distinct child copies, singular/excluded calls preserve
their input Board, root output is a separate N local, Worker/TT are separate
objects, and main drains both workers before replacing the published root.
This ownership argument is specific to the fixed actual call graph, beyond
const spelling alone. Clamp, learner updates and all other search bytes remain.
Canonical engine and DEV stay byte-identical, preserving all existing helper
readable/domain pins. The shipping representation is replayed from those
unchanged readable inputs; no opaque research artifact is a builder input.

Original first-cost index SHA-256:
`c543b5c2aa110873b1069ae7e79c92fc2a4a21febc22e6a25e81be062cf127af`.
Its candidate compile1/encode1 and strict Python2/CLI2 restoration are reused
without remeasurement. The sourcecache-only first cost retained cc/GCC13/profile/77-byte launcher/raw br
envelope and ALONE9e/lc2lp0pb0/BT4/dict64MiB/nice32; the final shared73-byte
header is a separately measured packaging change below.
Reports and before/producing/final evidence remain outside Git in
`rove4k-b-cached-evaluation-normal-20261022-evidence`. Timing/node equality,
RAM, strength, many-core and whole-project readiness are separate claims.
Older sections retain their original source/image and evidence scope.

Focused actual5079/5077 source pairs passed55 controlled searches under fatal
ASan/UBSan compile1/run1. Typed Board/job ownership,4224path keys,4096job keys,
all262144TT key/data/clearlocks and all3learners matched. Actual same-position
singular call/return was observed once per variant, and SEE entries8652 total.
Correction raw0/±256/±257 produced clamp0/±256 with actual update/seed-decay
assertions. Four explicit fixture-only observer ports have inverse proofs;
these are instrumented copies, not unmodified production includes or timed
shipping node/stack qualifications. Focused index SHA-256:
`9939f6e2d9120f0406d4d6fdc4170fcf9c1abfaa127eae2ef8f7ac214c0ed43e`.

Separately, shared `source_package.py` SHA-25655fa739e7c17fffdb3bf1191c7a26aa38d35e9e32473e4008c23ece3d5703d1f
supplies XZ_STDIN_HEADER73. The legacy launcher.sh77/template input check stays
intact. The exact5077 first-cost bytes were checked and the same compressed
payload was prefixed by73 bytes to measure5073 directly, encode0. Python and
the actual xz-d CLI restored full bootstrap/source bytes with EOF/trailing0.
Source/native/bootstrap/compiler/codec/DEV are unchanged. This combined header
has separate direct-measurement evidence and final5073 normal/runtime
receipts below. The original5077 sourcecache cost and focused scope remain distinct.


Ordinary build receipt SHA-256:
`ca944e8ca0c02071011beb4be60565d819c85141e1140a60094575b76e9f84da`;
selected runtime `57ff84af754dbf80a88d3438f65acaa93579515f13044ff51ed94154d1bb08fd`.
Actual producing recipe SHA-256:
`20995e85f7e9e02416598c460babd87434adeb490ee8bb4ba7bf895f7110c500`.
Inputs stayed stable until both commands exited; completion annotations are
separate. Metadata did not trigger a rebuild. Cost remeasurement, fresh, extra
fault/sweep/game/benchmark0. Reports and originals remain outside Git.

# Maintained B: shipping dead instrumentation cleanup ordinary reproduction and selected validation passed — 2026-10-22

The fixed first-cost file is **5079 B**, compact C **10409 B**, native
**26296 B**. Relative to qualified B5086, one shipping-only dead instrumentation
cleanup removes12 source bytes and7 actual whole-file bytes. Entire native
bytes remain exactly `67076339c1fcb72988d60a945125c37d1670e0a97fe14241b54e334ffe089f36`.
The4096 B goal remains open. One ordinary --dev builder reproduced shipping
source/native/bootstrap/whole twice and exact old DEV source/native twice.
The unchanged selected positive verifier passed quit/EOF2 sessions and8 legal
GO,3 startup TIDs each, exact restored native, absent helper/private paths and
physical process/reader exit0. All six startup TIDs are absent. Cancellation
causality remains unproven.

The pure B-owned `shipping_singular_depth.py` runs after piece-index. It
replaces `int zH=yr&&m==tt,z3=a-1+zH;if(zH){}` with
`int z3=a-1+(yr&&m==tt);` in one fixed span, preserving two unchanged gaps,
the10386-byte complement and full inverse. zH has only the declaration, depth
consumer and empty diagnostic condition. The decision stays int0/1, with
the same short-circuit order and one evaluation; all values are ordinary local
scalars with no side effects. The same int depth addition and four recursive
depth consumers remain. This changes no extension/search/learning/TT/pool or
protocol policy. Canonical/DEV retain their live COUNT extension observation
and bypass this shipping-only cleanup. Previous helpers remain unchanged.

The existing single cost used actual frozen package/template/raw br literal/
77-byte launcher and unchanged cc/GCC13, ALONE9e/lc2lp0pb0/BT4/64MiB/nice32.
Baseline bootstrap exact preceded candidate compile1/encode1; strict Python2/
CLI2 full restoration had EOFtrue and trailing0. Native bytes equal the current
qualified predecessor. First-cost index SHA-256:
`ea4de29610715a88f7a4e5c86b1e91cc4b7fd29f9fef29caa61c5d81dacc9ad2`.
No cost rerun, extra SAN/fault/sweep/negative/session or performance, RAM,
many-core, strength or whole-project readiness claim is added. Original cost
outputs and before/producing/final records remain outside Git in
`rove4k-b-singular-depth-normal-20261022-evidence`; older sections retain their
own original image and validation scope.

Ordinary build receipt SHA-256:
`3975c907b4ea578c876873c39db5e5ad38410601549aa8fa681b932ff3a74ebf`;
selected runtime `55b091d0f75459d1cc14d626cede4442a3c94b0b5d9726a1b8df4e35a1201d80`.
Actual producing recipe SHA-256:
`9b2293e01539bface7a3486a87e6d5dfa6ad0e434612e13fe1f814d19e65bb82`.
Producing inputs were stable until both commands physically exited; final
recipe/README completion annotations are separate. Metadata did not trigger
a rebuild. Source/normal/cost evidence remains external. Fresh/SAN/extra fault/
sweep/session/game/benchmark0. Deferred evaluation-cache work is not included.

# Maintained B: private piece-index inline ordinary reproduction and selected validation passed — 2026-10-22

The fixed first-cost file is **5086 B**, compact C **10421 B**, native
**26296 B**. Relative to the qualified B5098 predecessor, removing the sole
private `J(int)` definition and spelling its two calls as parenthesized
`int8_t + 6` expressions removes 30 source bytes and 12 actual complete-file
bytes. The entire native image remains exactly
`67076339c1fcb72988d60a945125c37d1670e0a97fe14241b54e334ffe089f36`.
The 4096 B goal remains open. One ordinary --dev builder reproduced shipping source/native/bootstrap/whole
twice and the exact old DEV source/native twice. The unchanged selected positive
verifier passed quit/EOF2 sessions and8 legal GO with three startup TIDs each,
exact restored native, absent helpers/private paths and physical process/reader
exit0. All six startup TIDs are absent. Cancellation causality remains unproven.

The pure B-owned `shipping_piece_index.py` runs last after history-depth.
It binds exact10451/10421 input/output identities, three spans, four unchanged
gaps, the protected10398-byte complement and a full positional inverse.
There are only the private definition and two actual calls; no address-taking,
macro or opaque-literal use exists in the fixed input. Each board element is
evaluated once and promoted from int8_t to int in both forms. Even the full
int8_t range plus6 is representable by int. Valid pieces[-6,6] map to[0,12],
including black king0, empty/root neutral6 and white king12 in zw[13][13].
The scoring/update consumers, recursive context, model, learners, search, TT,
pool publication and protocol bytes remain unchanged. Canonical diagnostics
and old-minimax DEV bypass the stage; no new layout or policy is introduced.

The existing cost was one compiler and one encode, with baseline bootstrap
exact before candidate compilation and strict Python2/CLI2 full restoration,
EOF and no trailing data. Actual frozen package/template/77-byte launcher/raw
br source envelope and ALONE9e/lc2lp0pb0/BT4/dict64MiB/nice32 are unchanged.
First-cost index SHA-256:
`a658e7465009fa6453e136cb76971a0a470dfe6144b96dae1eb3249a452741b8`.
The first preparation length-assertion error remains preserved externally;
the cost itself completed without error/retry. No cost rerun is required.
No performance, RAM, many-core, strength or whole-project readiness claim
is added. Reports and exact before/producing/final records remain outside Git
in `rove4k-b-piece-index-normal-20261022-evidence`; older sections below retain
their original image and validation scope.

Ordinary build receipt SHA-256:
`fb8993e2a84057d004f59ff36eca2426d010fa1f87ec14439e3ae1a5ef3c4d35`;
selected runtime `dc0bdf20c0579cd8754946035979179de2180bca56f2780da37ec9c3a4c63439`.
Actual producing recipe SHA-256:
`bb199ab41b3e6ff4202a872f8fa77f5449351fc40c3ac7e54359c13de9b88f90`.
The producing closure stayed unchanged until both commands exited; final recipe
and README completion annotations were then added separately. Original producing
sources and command receipts remain external. The original first cost was reused
without rerun. Fresh, SAN, extra oracle/negative/session, game and benchmark0.

# Maintained B: derived history length ordinary reproduction and selected validation passed — 2026-10-21

The fixed first-cost file is **5098 B**, compact C **10451 B**, native
**26296 B**. Against qualified lazy-fallback 5116 B, five exact C regions
remove 40 B and save 18 actual whole-file bytes. Native length is unchanged
but the full image differs; the new recipe admits its explicit identity.
The 4096 B goal remains open. One ordinary --dev builder reproduced shipping
source/native/bootstrap/whole twice and exact old DEV source/native twice.
The unchanged selected verifier passed quit/EOF in two sessions with eight
legal GO results, exact restored native, three startup TIDs each and physical
process/reader/private-path exit. These are local fixed2/TT18 observations.
Cancellation causality remains unproven.

The pure shared `shipping_history_depth.py` runs last, after lazy fallback,
only on shipping C. Exact input/output SHA-256, five regions, six protected
gaps, full inverse and protected complement guard this one form. It derives
the P-entry length as immutable job `qh+n`, reuses local W, writes the child
key at W and removes the private Worker cursor/reset/push/pop. The loop's
nonnegative condition retains max(0,length-1-halfmove), including short
histories with large halfmove clocks. Root qh is 1..4096; ply is 0..127;
the highest admitted child write is 4222 in 4224 key cells.

Same-position singular verification forwards the same ply and entry length;
four made-child PVS calls still pass ply+1. All seven 10-argument vectors,
SEE/cancel ordering, learner formulas, TT/Board, continuation row0/neutral6,
protocol and pool publication bytes remain protected. Main's existing
drain precedes root replacement, and job publication precedes worker entry.
Canonical diagnostics and the unchanged old-minimax DEV path bypass this
stage. The frozen helper registry also supplies existing fresh discovery;
fresh is not executed. Builds need no external research reports.

One fixed cost compile+encode and strict old/new Python/CLI restoration
completed without target execution. A separate fatal ASan/UBSan compile
and run passed 50 actual old/new search pairs: original B 36 plus 14 history
bounds, using both actual Worker layouts and typed common-state/full-TT/
Board comparisons. qh 1/4096, parity, short-history clamp, cap 127, write 4222,
TT/terminal/stop restoration and both singular-eligibility/excluded cases
passed. Eligibility and direct excluded observations do not establish
runtime singular-branch or each-PVS-port coverage. No live pool/main ran.
The ordinary image and restored runtime have separate passing receipts.
This is a fixed manual shipping-source contract; general source-location
or arbitrary observer equivalence and NV typed embedding remain unclaimed.
No Worker-size, performance, timing, many-core, game or strength conclusion
is added. Before/producing/final records stay outside Git in
`rove4k-b-history-depth-normal-20261021-evidence`. Older sections retain
their own historical image and validation scope.

Ordinary build receipt SHA-256:
`bfb25fe664fc2e8c584dc8c2c36b5f8f41234ad8ab335f7be588f12670a8c660`;
selected runtime `484c80b79ce100815e5529b19aff3ad2a0632c9759388b3564f09582d31111b8`.
Actual producing recipe SHA-256:
`2c26f4f898e9bf892c937a215cd0993a6c94e636f44b1f3ff9e7326a29ac1a6d`.
Final recipe/README annotations were added only after those commands exited.

# Maintained B: lazy fallback normal reproduction and selected validation passed — 2026-10-21

The fixed first-cost file is **5116 B**, compact C **10491 B**, native
**26296 B**. Against the exact 5122 B predecessor, this source removes16 B
and the actual whole file saves6 B. The new source/native/bootstrap/whole
identities are recorded in the recipe; full-native equality is not claimed.
One candidate compile and encode completed in the five-context portfolio,
with strict Python/CLI restoration; that cost phase ran no bootstrap or engine.
One ordinary --dev builder has now reproduced shipping twice and exact old DEV
source/native twice. The unchanged selected verifier passed quit/EOF in two
sessions with eight GO results, three startup TIDs each, exact restored native
and physical process/reader/private-path exit. Build receipt SHA-256:
`82d4762b83a135a103c7875b5ea1f29ac1b749661ba475c7118179386b38f47f`;
runtime `879469e6c1f8854e80f03019eab306f2b2128b29e5ddd917c6492b091db5f849`.
These are local fixed2/TT18 positive observations. Cancellation causality
remains unproven; no stack-peak, timing equality, many-core or strength result
is added. The cost-only statements below retain their original scope.

The shipping-only late stage follows continuation-context processing. Its
three exact regions remove the global fallback declaration and eager GO
query, then derive the same first legal move only when the selected worker's
last completed witness is zero. The fixed scratch name is `fb`; full inverse
and protected gaps bind the transformation to the exact predecessor source.
The existing helper freeze/import path records `shipping_lazy_fallback.py`.
Canonical diagnostics and the distinct old-minimax DEV path bypass the stage.

The last worker calls result while holding the pool mutex after all think
calls have returned. Main cannot replace the immutable root until that result
and its physical output finish. Completed-depth selection, fallback legality,
pending/epoch wrap, cancellation, quit/EOF join, TT, HCE and learners retain
their contracts. The first-legal query moves from GO setup to the last
worker's result stack; deadline work, scheduling and stack peaks are not
claimed identical or smaller. This cost result proves no runtime, strength,
many-core or final-target readiness. The 4096 B full-engine goal remains open.

First-cost receipt SHA-256:
`b9613dd993cfab433a479a43b80d8f1b4457f9cbe6147418661f5ca876d2276a`.
Before/producing records stay outside Git in the B subfolder of
`rove4k-common-lazy-fallback-promotion-20261021-evidence`.
Older sections below retain their own qualified image and execution scope.

# Maintained B: carried continuation row through singular search — 2026-10-21

Complete file **5122 B**, compact C **10507 B**, native **26304 B**. The
fixed source form removes 41 C bytes and saves 16 actual complete-file bytes
against the 5138 B environment-form entry. The file remains 1026 bytes above
4096. Native size is unchanged, but its complete bytes differ from the old
image; prior full-native identity is not a qualification claim for this form.

The root passes neutral continuation row 6. Four successful-made-child PVS
calls pass the actual signed destination piece slot, including promoted piece,
EP pawn and castling king. Same-position singular verification forwards the
entry row unchanged, with the same Board/ply, excluded TT move and learning0.
Black-king row 0 is valid and is never treated as the previous-move sentinel.
All other call arguments, depth/windows, SEE and cancel-poll source ordering,
singular eligibility/extensions, excluded TT and learning gates are retained.
The existing positive cutoff learner body is unchanged.

The current-row read advances into the caller after successful child make.
Its value correspondence uses the initialized private/immutable child Board;
general read timing and arbitrary observer equivalence are not claimed.
Forwarding the existing row in the singular call itself adds no Board read.
Quiet cutoff learning reuses the same slot as the old parent FROM column:
shipping bit3 excludes captures, EP and every promotion from that quiet gate.

The pure maintained helper follows clock and line-drain processing. It checks
the exact 10548-byte source, unchanged readable input, seven literal regions,
eight protected gaps, full inverse and exact 10507-byte output. Registration
enters the frozen helper inputs and the existing dynamic fresh source closure.
Canonical and DEV bypass this stage. Fresh was not executed. The HCE/model,
Move ABI, gen/make, repetition, TT, correction, worker/input/pool, compiler,
77-byte launcher and nice32/lc2 ALONE codec stay protected.

One fatal ASan+UBSan compile/run compared actual old/new P across 36 pairs,
including scores, best moves, nodes, complete Worker, complete TT key/data/lock
bytes and caller Board preservation with memcpy snapshots. Legal children128,
special children22 and both signed quiet contexts passed. Four black-king
row0 pairs passed. A legal seeded TT at depth6/ttdepth3/bound1/nonmate/ply1
satisfied singular eligibility before both calls; a separate excluded/learning0
pair ignored seeded exact TT score64, returned draw0 and preserved learners
and parent TT bytes. These are value/eligibility checks. Runtime singular and
all-four-PVS branch coverage were not instrumented or inferred from nodes.
The identical existing positive learner evidence was reused without another
exhaustive run.

One ordinary `--dev` builder reproduced shipping and unchanged DEV twice,
consuming the new frozen helper and both exact inverse/gap metadata rows.
The unchanged selected verifier passed quit/EOF2 sessions and eight legal GO
epochs, restored the exact new native, and observed three persistent startup
TIDs per session, absent private paths, physical process exit and reader EOF.
All six observed TIDs were absent afterward. Both owned groups were absent
with empty diagnostics. Cancellation causality remains unproven. No extra
fresh, SAN/core campaign, game, negative, trace, performance or CI run followed.

Current source SHA-256: `8c7a110e5282e75128cf76c4b706a0c79ca5890be25a93e38f1734e9fb53089e`.
Native SHA-256: `9a0faaef78894c73883fdd4e1a688d3d437d8dde0efcc4b6d209fb7d585cbcef`.
Bootstrap SHA-256: `df7ee285c8a63ff3f44f5caa01d28b39b29292b3192115d7e02e98aa5eae78f2`.
Whole SHA-256: `db430ad83be9bd323495653f98ed1c5457d45daf53b9c7452ff376c8dc444ef9`.
Build receipt SHA-256: `a906b7c87a3c5db7dfe9e513be43ed7ac88f77702afa80e689046edb303c7ecc`.
Runtime receipt SHA-256: `f16d0c12492c8859d76ff3e246506fc4e70e9037d4c838d66b105a3108bf6cb5`.

Before/producing sources and normal receipts are preserved in the external
`rove4k-b-continuation-context-normal-20261021-evidence` folder. The original
source proposal, read-timing clarification, first cost and first focused
outcome remain unchanged. Only completion metadata and this README were
annotated after execution. Historical sections keep their own image scope.

# Maintained B: compact environment snapshot — 2026-10-21

Complete file **5138 B**, compact C **10548 B**. The single
env constructor expression saves6 template bytes and 6 actual whole-file
bytes against the preceding 5144 B entry. `dict(os.environ,TMPDIR=d)`
copies the environment and overrides TMPDIR at the original location. Runtime
environment, compiler argv/C stdin, source/native/DEV, profile/model, signal
mask, Popen publication, cleanup and deleted-file FD exec are retained.
Source spelling/columns and failure-traceback bytes are not equality claims.

The finite15-form comparison kept old and unselected signal/helper-composed
forms. Although helper sharing removes39 raw bytes, env-only is actually
smallest in every measured full context. No compressed deltas were added.

One ordinary --dev build reproduces shipping and unchanged DEV twice. The
unchanged selected verifier passes two quit/EOF sessions and8 legal GO epochs,
exact native restoration,3 persistent startup TIDs, absent private paths and
physical process/reader exit. Cancellation causality remains unproven. No
new algorithm, strength, final hardware, game or performance result is claimed.

Build receipt SHA-256: `d46c3a02067be38973282d5b2629e1b932cb11081393c7971c8ecc644926f263`.
Runtime receipt SHA-256: `8551b042a6eb448804222cc1d75288c94d1eb37b63fb43830859acc678dc1ba5`.
Current whole SHA-256: `d048764814144c1b526f73a38112096be9ebefe64a4e91719852f7fc8c2d1366`.

The producing recipes, actual receipts and pre-annotation sources remain in
`rove4k-bootstrap-env-normal-20261021-evidence`; original costs and source
forms are preserved in the source/optional-cost evidence folders. Historical
sections below retain their own images and scope.

# Maintained B: shared line drain — 2026-10-21

Complete file **5144 B**, compact C **10548 B**, gap **1048 B** above4096.
The pure B-only `shipping_line_drain.py` follows clock presence and replaces
one85-byte missing-LF drain fragment with68 bytes. It combines the initial
`getchar` and repeated drain loop while preserving every stream read, terminal
LF/EOF admission, oversized-line discard and following-line recovery. The
full input/output pins, sole old span, inverse and complementary bytes are
checked. DEV bypass and every earlier source guard remain unchanged.

The actual fixed first cost is whole5146→5144B, source10565→10548B and
bootstrap11610→11593B. Native length stays26304B with a new full identity;
no metadata exception or equal-native claim is used. The measured native is
`456956420deddff56280323fdba19812256772929ab8179e9fc28233ddead5c7`.
No engine model, SEE, singular, TT, learning, rules or worker feature is removed.

The selected candidate first passed three actual boundary protocol sessions:
one quit and two EOF paths, full-buffer LF/EOF admission, overlong discard,
next-line recovery, exact responses and physical settlement. Receipt SHA-256:
`3ce117e0199f7c12ac9795a661273e2fe388c76a20bf8d491aef94a70e7ae11d`.
This remains separate from ordinary regeneration and selected verification.

Root source review found a producer bug before any normal/helper import:
ordinary Python bytes constants interpreted C backslash-n as LF, making the
OLD/NEW values83/67B instead of85/68B. The original helper/recipe, earlier
preparation error and static finding are retained outside Git. Only the two
literal prefixes became raw bytes and their helper hash references changed;
the measured C/native/bootstrap/whole expected values were not relaxed.
One pure helper replay then reproduced the exact measured10548-byte source.
Correction readback SHA-256:
`23c30c9319c476b3017c95fde03ea1b266207eb48dc96fe97d681b8a33df183c`.

One existing ordinary builder with `--dev` reproduced shipping source/native/
bootstrap/whole twice and the unchanged old full-minimax DEV tuple twice.
The unchanged selected verifier passed two actual quit/EOF sessions with8
legal finite GO results, exact restored native, stable3 TIDs, absent private
restoration paths/helpers, one closing result, reader EOF and physical exit0.
Cancellation causality remains unproven. No extra boundary/negative campaign,
game, strength, stack, scaling or final-target resource qualification was run.
Normal summary SHA-256:
`6f6111b89becb33e9a6a4a096bc03ae4896acd27a24d9280e8a7daa7a0edca7d`.

Producing recipe70466B SHA-256
`f192fdfbd98b0665f879c635d0a8fbeb02a8aae49d52b35fd3fcb0d9bca2e708`
is preserved separately from the following recipe/README result annotations.
No postannotation builder or verifier rerun is claimed. All generated outputs,
logs and receipts remain outside Git; these local2-worker/TT18 checks do not
establish final tournament strength or many-core/resource acceptance.

Current source SHA-256: `d91416e56e2b7716b9df2bec5db22c1f9d3f6ded5598d80741d68487ecc09bbb`.
Current whole SHA-256: `fa2196f2093d5701f946415260bb426b7f7f1feb6e6dc776b834bae5449fff21`.

Older sections below retain their own checkpoint identities and evidence scope.

# Maintained B: compact clock presence — 2026-10-21

Complete file **5146 B**, compact C **10565 B**.
Use UINT64_MAX for absent selected time and complement it for the presence
test. Actual numeric acceptance remains0..INT64_MAX; invalid/missing values
still become0 and count as a selected-time assignment. Token consumption,
budget caps, fallback and epoch publication remain. This removes12 raw
source bytes; the native has a new identity. DEV bypass remains exact.

Fatal ASan/UBSan compares20 old/new idle GO transitions per family. E also
checks1536 piece operands,27 order cases,26 legal children and78 nonlinear
leaf cases. Actual production main/workers are excluded from those fixtures.
Ordinary --dev regeneration then reproduces shipping/DEV twice for all seven
selections; unchanged selected verifiers pass14 actual quit/EOF sessions.
Normal summary SHA-256:
`8e30da1a34a87d6f68cc8a42aafab4e43cb49049ef38510cfb008776095e01b9`.

Current source SHA-256: `6124424eff02466a28e900ca7abf0f8ff36f74d39de020e4c83b6909b95387cf`.
Current whole SHA-256: `df570da8221bf92fe3f3f1d99df997955d24860ec1d4bf933ea3dd2dceda9c51`.

Local two-worker/TT18 checks do not establish final target resources,
many-core behavior or strength. The full A–F goal and compression beyond
size passage remain active. Older sections retain their checkpoint identities.

# Maintained B: smaller plain-Popen cleanup guard — 2026-10-21

Whole **5148 B**. The current template/script loses12 raw bytes
by testing the fixed plain Popen/None value directly. Poll, cleanup, signal mask,
compiler argv/C input, private path, descriptor exec and physical lifetime
operations remain unchanged. C source/native are entire-byte unchanged.

All seven selections regenerate --dev twice and pass unchanged actual selected
quit/EOF verification. This is local2-worker/TT18 evidence, with no new general
descendant cleanup, startup-fault or strength guarantee. Normal summary SHA-256:
`90e45a020a55ef5a3ff6af78dfa42908eb8625395fe5c991d860bde8d34b2ff6`.

Current source SHA-256: `d360c9ca23b30fe7f295d3f1e0012da9618a1a25a6b8b9cec19240fdac6396ae`.
Current whole SHA-256: `a4ef7accbca5d6f83d7ebf58c651df52e4a35536ffe335c36b9a84058114f199`.

Older sections retain their original checkpoint identities.

# Maintained B: final literal/poll compaction — 2026-10-21

Current whole **5154 B**, source **10577 B**.
Clock-first SEE guard; cancellation polling order/timing changes. Completed legal-LVA values and unknown propagation remain.
All full family features and DEV bypass remain. Final transforms operate on
separate reference copies where needed; raw policy preimages stay unchanged.

The ordinary --dev builder reproduces shipping and full DEV twice, and unchanged
selected verifiers pass actual quit/EOF, restoration, legal finite GO and physical
exit. Local2-worker/TT18 only; final resources and strength remain open. Final
normal summary SHA-256:
`af00002687cf6ed0d84f2e85f21169d381bb1cd8721005c05cc87a4fabe2bb96`.

Current source SHA-256: `d360c9ca23b30fe7f295d3f1e0012da9618a1a25a6b8b9cec19240fdac6396ae`.
Current whole SHA-256: `3130d6214fb6de833a7fb5543899e647f1bc43485f3c94e454f508c99b47acb0`.

Older sections retain their original checkpoint identities.

# Maintained B: literal include forms — 2026-10-21

Whole **5162→5161 B**, source **10588 B**.
Only the fixed literal angle-header gap is removed, after all prior shipping
stages. Every other source byte and directive boundary is preserved. The
entire native image equals the preceding qualified image. DEV bypasses this
pass; F's raw policy preimages are retained through separate reference copies.

Ordinary --dev reproduces shipping/DEV twice and unchanged selected verifiers
pass actual quit/EOF, restoration, finite clocks and physical exit. This is
local2-worker/TT18 evidence; no new functional or strength run is claimed.
Normal summary SHA-256:
`b6be10f54e68ea2c381ed85a5a8fce47253825bb5bafbd1639b5b9802e9c5137`.

Current source SHA-256: `13f1b0d74752f7aa2743616ad6465d1ee8e1497d70da7d3db242e38bdccc5c3b`.
Current whole SHA-256: `64c48807d6f308f931cabbae500260f9ef30a6fd89f93a316f38102fd48af229`.

Older sections retain their original checkpoint identities.

# Maintained B: job/startup and SEE source compaction — 2026-10-21

Whole **5196→5162 B**, source **10702→10595 B**, gap **1066 B**. The
shipping-only late pass combines TO127-equivalent SEE rank spelling, worker-owned
unconditional job reset, checked-calloc-covered plain TT zero stores and fixed
positive TT18 casts. Every atomic flag is still cleared. Full hybrid attackers,
legal-LVA ordering, singular, search, learners and SMP are retained. DEV bypasses
the pass. General TT-reset and arbitrary preseeded direct-think contracts are
not inferred from the production startup/job path.

The ordinary --dev builder reproduces shipping and DEV twice; its unchanged
selected verifier passes actual quit/EOF sessions, exact restoration, legal
finite clocks, stable3 TIDs and physical exit. Local2-worker/TT18 only; final
resources and strength remain open. Normal summary SHA-256:
`4b7b98ecc6cdb94d11a112e307d388633a03fb061d2000b08167b85ac70c72ca`.

Current source SHA-256: `036d9c1aaec37b68508ec76ea335e77775d486bf4141dd7d4e94698a6313e33b`.
Current whole SHA-256: `c3140e749c94bccb4a65842f09f823331b7023be5b9cd7c504a8802dd8d78b7f`.

Older sections retain their original checkpoint identities.

# Maintained B: integer source compression — 2026-10-21

The late fixed integer pass uses the existing unsigned64 alias and high-bit
decimal bound, retaining digit/end-pointer checks, clock consumption and all
budget clamps. The unused final limits header is removed except for C,
which has a later intrinsic include. Full/material F also omit two fixed
positive TT18 casts. Actual composed costs are used, not added deltas.

The entire native remains byte-identical to the previous maintained image;
no model, learner, search, rule, TT or worker feature is removed.

| Policy | Previous whole | Current whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| B | 5219 | **5196** | 23 | 1100 |

Each normal --dev build reproduces shipping and full-reference DEV twice.
The unchanged selected verifier passes new actual quit/EOF wrappers, exact
restored native, stable3 TIDs, legal finite GO, private-path/helper absence,
closing result, reader EOF and physical exit. Normal summary SHA-256:
`1de4261cbd87622c9326fe8c72137b0d96148fb4e1514b2c81e8dbda4031a2a5`.
The local2-worker/TT18 profile does not accept final resources or strength.

| Policy | Source bytes | Native bytes | Whole SHA-256 |
|---|---:|---:|---|
| B | 10702 | 26304 | `db693ef304ec35e8584a6ee6f53c8be4bb93fe1626853c6456eae687f7deb6eb` |

Older sections retain their original checkpoint identities.

# Maintained B: shared material-state compression — 2026-10-21

A shared late source pass replaces three material-classification accumulators
with one signed state, preserving the existing limited policy. Bare kings
and a single minor remain dead; KNN stays live. Bishop-only minor sets are
dead when confined to one square color. Full models/search/TT/
learning/rules/input/pool remain outside the one-function edit. This is not
a general theoretical dead-position oracle. Raw source grows18B per policy,
while actual complete-file cost decreases; independent deltas are not added.

| Policy | Previous whole | Current whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| B | 5229 | **5219** | 10 | 1123 |

Actual old/new classifiers and an independent material/count oracle agree
on109 canonical FENs per policy (31 dead/78 live), with entire Board bytes
unchanged, under ASan/UBSan. Each ordinary --dev build reproduces shipping
and full-reference DEV twice. The unchanged selected verifier exercises
new actual quit/EOF wrappers, exact restored native, stable3 TIDs, legal
GO, private-path/helper absence, closing result, reader EOF and physical
exit. Normal summary SHA-256:
`2c75a07e42a796030509be4ed6ea5f1046a5528911629463397222f1fdbe051f`.
These are local2-worker/TT18 results, not final resources or strength.

| Policy | Source bytes | Native bytes | Whole SHA-256 |
|---|---:|---:|---|
| B | 10745 | 26304 | `65cfbe6f391f620beeb8d8b190570ed5eed2c38b937ba87b1cbf4f547fe606b0` |

Older sections retain their original checkpoint identities.

# Maintained B: qualified source refinements — 2026-10-21

Main-owned token consumption and the valid-0x88 promotion predicate are shared. Actual make returns 1+material gain on success (0 on failure); SEE consumes that gain and shares the material table. Non-SEE callers consume only success truth.

| Policy | Previous whole | Current whole | Saved | Above 4096 |
|---|---:|---:|---:|---:|
| B | 5256 | **5229** | 27 | 1133 |

These are actual composed complete-file results, including the unchanged77-byte
prefix and current fixed compiler/codec. New native identities are admitted
explicitly; equal native lengths do not imply identical images. Canonical
full-reference DEV remains unchanged. The fixed replay helper uses complete
source pins, nonoverlapping literals, inverse and untouched-complement checks.

One ordinary --dev build per policy independently reproduced shipping source,
native, bootstrap and whole twice and DEV twice. The unchanged selected
verifier exercised the actual new wrapper in quit/EOF sessions: exact native
restoration, stable3 startup TIDs, legal finite GO, private-path/helper absence,
one closing result, reader EOF and physical exit. Component function proofs
and these wrapper observations have separate scopes. No strength or final
tournament profile acceptance follows from the local two-worker TT18 runs.

| Policy | Source bytes | Native bytes | Whole SHA-256 |
|---|---:|---:|---|
| B | 10727 | 26304 | `5739a6da7fa5e6ed63c1b201eb1d9a2ec6b9f1f675560e7e9351c4ebbeb388a9` |

Normal summary SHA-256:
`cc82bacb31cfd8fb020fa375a3a1d1b3ece7ac2991dc7ebcf2c7ed772e3d230e`.
This frozen summary binds producing inputs before subsequent receipt-only
recipe annotations. Older sections below retain their original identities.

# Maintained B: shared final shipping reductions

The final `engines/scripts/shipping_common.py` pass removes the sole unused
empty `TINY_H` definition after all existing family stages. A/C/E also omit
two redundant fixed-TT18 casts. ASCII source uses a raw bytes literal in the
unchanged bootstrap; every previous non-ASCII/CR/NUL/quote/backslash fallback
and the historical `pack_stream.py` API remain unchanged.

| Policy | Previous whole | Current whole | Saved | Above 4096 |
|---|---:|---:|---:|---:|
| B | 5267 | **5256** | 11 | 1160 |

These are actual composed complete-file measurements with each unchanged
compiler/profile/codec, not sums of separate candidate savings. Entire native
bytes match the previous maintained native for every policy; no metadata
exception applies. Canonical engine, search/model/TT/input/worker contracts
and full-reference DEV source/native are unchanged.

One ordinary `--dev` builder invocation per policy reproduced shipping
source/native/bootstrap/whole twice and DEV twice. The unchanged selected
verifier then ran each new wrapper through quit/EOF: exact restored native,
three stable startup TIDs, legal finite GO, private paths/helpers absent
at UCI, one closing result, reader EOF and physical exit. Alternate F DEV
is still the full-reference diagnostic, not alternate-model execution.

| Policy | New source | Native | Bootstrap | Whole SHA-256 |
|---|---:|---:|---:|---|
| B | 10941 | 26304 | 11998 | `41a6057b9a4c5ed8445d96b2fa19263dcf436cf6a5b7a25948323e7b9570fe5e` |

Exact source/bootstrap/native hashes remain in `recipe.json`. External normal
summary SHA-256: `4c2bc987c0947387ebe688ac76c7b91f41d1458149278e490638fb1428f7469f`.
Generated artifacts and reports remain outside Git. The following sections
describe earlier checkpoints and retain their original validation scope.

## Previous: Maintained B5267 recapture-promotion composition

The selected complete file is5267B,12 below B5279 and1171 above4096.
The last pure ordinary shipping_recapture.py consumes exact11009/ce6a8b input
after all prior stages and produces10957/c3a86d. One164B internal recapture
promotion span becomes112B. Actual legal make, shared l/h, initial gen4,
numerical ordering, unknown guard, PVS/QS, fullkey TT/singular/excludedlearning
and persistent SMP/input/resources remain unchanged. No QS SEE pruning exists.

Within the fixed-target legal-LVA exchange, each next capture removes the
different promoted target and converges to the same coherent child state.
Thus queen weakly maximizes the four completed recapture values. This is not
a full-chess underpromotion rule or legal-LVA/full-minimax equivalence.
There are fewer recursive calls and stop/deadline checkpoints, so finite-time
search/visit/cancellation schedule can differ. Canonical/DEV retains its old
full-minimax reference bytes, not coverage of this new production Q.

One first cost produced source10957/native26304/bootstrap12022/whole5267.
New native SHAc895bf3d2802d12014869e13726dce9c29da732e75e6c476c50436c1f39ac6ca;
whole SHA245a05f9d0656be4a1b79c63a884b06dcc526b4e78a9e5391c8b05c6489d3d76.
One O2 diagnostic TU compared actual old/new Q with common actual l/h against
155 independent expected values (153 legal/2 illegal),2 normalized EP
exclusions and6 fixture-clock guards on each function. Four-promotion
convergence passed10 groups/6 legal post-promotion replies. No production
clock, old DEV/newQ coverage, strength, performance or stack equivalence follows.

The helper embeds readable roles, full input/output/oldQ pins, one exact
literal pair, inverse and protected complement. It reads no experiment,
report, generated artifact, AST or network input. Existing maps/guards and
compiler/profile/original codec/77B launcher remain unchanged.
One ordinary --dev builder reproduced shipping source/native/bootstrap/whole
twice and the exact old DEV source/native twice. One unchanged selected
verifier passed quit/EOF2 sessions/8 legal GO epochs with the exact new
restored native,3 persistent startup TIDs each, no observed helper/private
restoration path, active closing search, one closing result, reader EOF and
natural physical exit0. Both outer groups and all6 observed TIDs are absent;
forced cleanup0. Cancellation causality and identical checkpoint schedule
remain unproven. DEV is the old reference, not newQ coverage. Fresh0; no
strength/performance/stack/scaling claim. Producing B27 and final completion
metadata are preserved separately, with no postmetadata builder/verifier run.
Build SHA a083ac7389979be45a294c7c6c7bc9cf40a5f807ccadc4041e6c81afc218dd26;
runtime SHA 88fa700eb1a85370b6fda28eea76cf98e440c2cbe51347097c441b4adf413e2a.

# Historical B5279 global-function spelling stage


The selected complete launcher is **5,279 bytes**, 61 below its
preceding complete file and **1183 bytes above4,096**. The final ordinary
`shipping_global_names.py` follows the type-token stage. It shortens 12 owned
global functions at 46 physical declaration/reference spans, source
11167->11009. No local names or model/search logic change.

| Selected artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C |11009|`ce6a8b884009a4735ad5c9dbc948b444fe1af185ee7b40dd6335946625b92587`|
| Full native |26304|`7fcfab6f5933f5a945ee7841a54204fd00bb9b3fa9caec23d96d4455a7b9e998`|
| Decoded bootstrap |12074|`097089946cd68344760ea20c8e13ec43db8a03f336d57c509a82a789193c8a8f`|
| Complete launcher |5279|`ac675d1954d10ead1a3df1fd33426aa8178118cccce5bc4d81abdf12c77e6f3a`|

Full native and full declared load-image identity to the predecessor are
false. The bounded object review compares all26 SHF_ALLOC sections: only the
explicitly pinned build-id note differs. Allocated code/data bytes, address,
flags and geometry otherwise match. Exact owned-name-normalized symbols retain
binding/type/size/address/visibility/section, with external dynsym/relocations,
PHDR and entry unchanged. The declared PT_LOAD bytes differ only in ELF
section-table-offset lowbyte at40 and build-id descriptor20B at888. Unallocated
symbol/string tables legitimately encode the declared implementation names.
This is a static ELF comparison, not process-memory observation or a generic
metadata exception. The compiler check requires only the one reviewed new
full-native pin above, never arbitrary metadata changes.

The helper owns full input/output pins, exact literal function/physical-span
map, token-width checks, inverse, protected complement/directives/opaque bytes.
main, header/external references, objects, types, members and all existing
family model/tag/SIMD/search/clock/resource guards remain unchanged. These are
owned names in a standalone shipping TU, not an external symbol API. No
AST/experiment/report/artifact dependency enters normal regeneration. DEV
bypasses the stage and retains its prior source/native and evidence scope.
Compiler arguments, original family codec, bootstrap and77B launcher stay fixed.

Source proposal SHAf59ddbe83d3561787207553d9de6b423ba7a227aedb97b1f8c8033ace531a6ec;
fixed cost SHAe192da7467cbf2dfa950bf50f3127d45e684ef7c484c110bd2a86ccb1d8899c2;
bounded metadata review SHA4f80b574c9bc0af5c5f7f16a5ba4f5e29601edad11e0856fb34cb099be353cc1.
Strict original whole/bootstrap reproduction and Python/CLI source/template/
argv restoration passed. Cost and read-object review executed no target.
Current ordinary source and controls were preserved, and producing source was
frozen before the sole normal --dev call. Shipping source/native/bootstrap/
whole reproduced twice with exactly the measured new full-native pin; prior
DEV source/native reproduced twice. The unchanged selected verifier completed
once: quit/EOF2sessions8legalGO, exact restored new native, stable three startup
TIDs each, private-path/helper absence, active closing search, exactly one
closing bestmove, finished readers and natural physical exit0. All six observed
TIDs are now absent. No normal retry or forced cleanup occurred.
Build SHAc90599c91b3842e7d057610c674894a72698179a21406a294fd597d507f0044d;
runtime SHA85fb029303d04913adeb853cec45dc923dd78b052ac69439ed58231fe3b321ad;
readback SHA5a91b08df7d76378dca0e04cf451e9f28e96957942877b5d18cdb7fa6fe7ba0a.
Producing source SHA8eb3087d63b4f3c2841b2b8d31482ea2714346f2e65e66d2cbb97350a0c36ec0;
producing recipe SHAfcda2fd4fd7d7b7941063467a96d66b45a8311b224f2b6c43f8a7d3e978bc4be.
Only README/recipe completion metadata changed after execution; other
24 source paths and all helper/expected/compiler/profile/codec
remain producing bytes. Unchanged fresh.py would discover26 ordinary
paths; no fresh extraction ran. Cancellation causality and the unchanged
builder's separate compiler-descendant lifetime proof remain unproven.
No DEV engine, new core matrix, games, benchmark, training or negative campaign
was added. Prior native/body proofs retain their exact source/static reuse
scope, and prior wrapper receipts are not relabeled as these new executions.

# Historical B5340 type-token stage

The selected complete launcher is **5340 bytes**, 17 below B5357 and **1244 bytes above4,096**. Shipping C is 11167 bytes (source delta -263). Final shipping-only `shipping_types.py` owns one fixed type map `{'uint64_t': 'D', 'Move': 'N'}` plus a19-byte uint64_t alias definition. The existing Move typedef is renamed with its type uses and exactly3 MOVE casts; int16_t and private Entry zb remain protected. All full native bytes match the actual preceding native, without a metadata exception.

The ordinary family helper pins the canonical readable, complete final-stage preimage/result, type-role offsets/counts, source/directive alias freshness, sole MOVE line, exact inverse and each unchanged gap. It reads no experiment, report, old artifact, AST or network input. Its pinned existing lexer is frozen before import. Existing canonical/map/core/input and family-specific stages remain ahead of the final type stage; DEV bypasses it and retains its prior diagnostic model scope. Only C admits the fixed later immintrin header at old offset4060; no header is moved and no generic exception is opened. Actual header conflicts must fail the fixed full-native gate.

Unchanged fresh.py dynamically includes the new helper, yielding 25 unique ordinary source paths. Canonical/DEV/verify/fresh/shared bodies, compiler/resources/bootstrap/77-byte prefix and per-family ALONE settings remain unchanged. The whole 17-byte gain is separate from the larger raw source reduction.

| Current artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 11167 | `6ae7748ee0e56a925405692385a8adfd141274aaee845efaae406416664b1755` |
| Native ELF | 26360 | `483a2b6c1f420a30d2f04f1acab9101f6b7dc44c06e1485117a2e8117f1365dd` |
| Complete launcher | 5340 | `bb27f4fafd19c2a8add29b26fe6aed55bb914212468ea0e17203d786b7bfd178` |

The sole normal builder invocation passed shipping C/native/bootstrap/whole twice and the prior DEV C/native tuple twice, retaining its historical model scope. The unchanged selected verifier then passed its sole quit/EOF invocation: two sessions/eight legal GO epochs, exact restored native image, three stable startup TIDs each, absent private restoration paths/helper children, one closing result, completed readers and physical exit0. Both bounded command groups are terminal0 and absent, with no retry or forced cleanup. Prior sources and raw binary controls were preserved outside Git; native/whole pins are never newline-normalized. Original preflight failures remain preserved separately; approved correction did not change any candidate. No new core fixture, fresh archive extraction, game, benchmark or alias/codec search is part of normal promotion. Historical diagnostic/core evidence is reused by exact native identity within its existing scope; cancellation causality and many-core performance remain unproven.

Normal build receipt: `f8add1c9961dfb57273c19bebc9f4b7460ef5a8473ea50a9945f08c6920aa116`. Normal selected runtime receipt: `45f82945092d2573bc4acc6f10421a2f796e65f721c95ca924ae76c0f3849a5e`. Producing recipe: `312dc24f0ca4d23fd83750ff1037019fe767e6db89f063802e4576d46397ccad`; producing ordinary-source freeze: `451f9061e970179e6d5f92e796ee961915dd283d22ab642f39ef1e525e05bc4a`. Only README/recipe completion metadata changed after execution; all helper/build/compiler/expected/codec bytes remain producing inputs. Git/CI and whole-project acceptance are separate parent work.

# Historical B5357 stage

The selected shipping source uses legal least-valuable-attacker exchange for
ordering after the fixed text input profile and tactical Move stage. Its
complete file is **5,357 bytes**,14 below B5371 and **1,261 above4,096**. It is not a4KiB
entry. The readable canonical engine.c remains28,953 bytes. Canonical and DEV
retain the old full legal minimax model and API as a distinct reference;
DEV-model equivalence to production legal-LVA is explicitly false.

The fixed Linux x86-64 target remains Ubuntu24.04.4/GCC13.3/binutils2.42/
glibc2.39/Python3.12.3/xz-lzma5.4.5. Resources remain2 workers,1 controller,
TT bits18 and PLY128. Those are provisional competition resources. The minimal
shipping UCI and public interface are unchanged; this stage adds no option.

```sh
python3 -B engines/compact/tiny-entry-b/build.py --out /absolute/new/B-build --dev
python3 -B engines/compact/tiny-entry-b/verify.py --build /absolute/B-build --out /absolute/new/B-runtime
```

One builder invocation generates shipping twice and, with --dev, the old
diagnostic reference twice. The unchanged selected verifier runs actual quit
and EOF sessions. Each wrapper restores its exact C stdin with the original
compiler argv before exec:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x
```

## Current generated-Move tactical stage

The last pure ordinary helper embeds ten exact disjoint spans, full inverse,
all-gap complement, fixed source pins and paired readable emitter role binding.
It reads no experiment/report/Clang/artifact input. The unused0x88 FROM bit3
holds generated capture-or-promotion metadata; FROM119 clears it, while TO,
PROMO and the existing17-bit TT payload positions stay unchanged. Production
TT/hash-move/exclusion comparisons retain the tagged raw Move consistently;
only external oracle coordinate comparisons clear the metadata bit.

Existing gen/add geometry classifies pawnpush2, pawncapture/EP3 and other
quiet/capture0/1. The shared all4promotion emitter sets bit3. SEE eligibility,
QS tactical eligibility and correction quiet guards consume this single tag,
removing the repeated mailbox classifier. Initial empty-target EP still adds100
only for a nonpromotion; recursive Q recaptures have occupied targets. The
legal-LVA score model and UNKNOWN-before-arithmetic boundary remain. Quiet
promotions now receive the capture tactical base ordering tier: this explicit
ordering policy change can alter search/learning. No equal tree/strength or
old raw-Move/DEV model equivalence is claimed.

One cost produced source11430 (-102), native26360 (-24) and whole5357 (-14).
The fixed native SHA is483a2b6c1f420a30d2f04f1acab9101f6b7dc44c06e1485117a2e8117f1365dd;
whole SHA8b8c3b565974813aa2ea54383bcc19240c1dcf506157d2aa0b44c8b24fa3d5be.
One actual candidate diagnostic TU passed99 boards,294 independent tactical
tags,1281 legal full child states,85 legal-LVA expectations,2 illegal moves,
2 normalized EP exclusions and6 cancel/deadline controls. Two fixture-only P
observers recorded qualified singular1/taken extension1 with actual tagged
capture12441, prime910/alternatives14<threshold898. Ordinary positive learning
and excludedroot TT/learning/board/path/deadline controls passed. ActualTT18
child fullkey readmiss0 is recorded; no oldTT20 child-depth gate is inherited.
Fixture clock/counters are not production wallclock or selected-image evidence.

One normal builder with --dev reproduced actual shipping source/native/whole/
bootstrap twice and the old DEV source/native tuple twice. The unchanged
selected verifier passed actual quit/EOF2 sessions and8 legal GO epochs with
the new exact native image,3 persistent TIDs, no restoration helper/private
path, active closing epoch and physical reader EOF/main disappearance/exit0.
Both outer owned groups settled without intervention. Cancellation causality
remains unproven. Canonical engine.c and old full-minimax DEV ABI remain
unchanged references, not new-path proof. No fresh/game/strength/scaling claim.
Build receipt SHA f1882be151f244f59afa30a1020daeeec9366d6299096840f0ed9911d4d581e8;
runtime SHA4496ea25f93e7623e7e3f3e163a91de85df2db18d53055696bc4d267fea29bf9.
Producing B24 source/archive and final README/recipe result metadata are
preserved separately; no postmetadata builder/verifier rerun occurred.

## Ordinary source decisions

Canonical preprocessing, minification, diagnostic stripping, shared89 spelling,
B storage/static/scope maps and their old exact guards remain unchanged. The
existing shipping_core.py first transforms12220 to12148 using its unchanged
incoming-Move full-minimax composition. The fixed input helper then produces
11829/11a32cc6c48ad16856e7968c5ba91456257c1b249590f0aa71a371d2fd276a93.
Only then does B-only shipping_order.py produce11702 bytes. The final
shipping_walk.py consumes those exact bytes and produces11532; the new
shipping_tactical.py then consumes that exact11532/3fca96 input and produces
11430/54759113 with the same old spelling/core/order/walk guards unchanged. No previous
map or guard is generalized to accept a new source domain.

shipping_order.py embeds paired readable/physical literals, fixed role and
identifier-count domains, full input/output pins, three disjoint inverse
regions and an exact11083-byte all-gap complement. It removes the Exchange
type, replaces the incoming-net/wrapper region with one recursive Q, and
removes the entire QS negative-SEE clause. The actual ordering Q call and its
SEE_INCOMPLETE guard remain exact. The pure helper reads no experiment,
report, generated source/artifact, compiler/Clang/AST result or network data.
Receipt hashes are metadata only and are never regeneration inputs.

After successful make, the declared model chooses the first legal recapture
source by pre-capture P,N,B,R,Q,K kind, then ctz square order. All four N/B/R/Q
promotions of that selected source are tried and maximized. If all choices
from a source are illegal, it continues to the next source. A selected legal
negative continuation is declined with max(0,value); it does not search a more
expensive source for a better exchange. Initial EP and promotion gain remain
inside the incoming move. Incremental mailbox/bitboard attackers are reused;
unchanged make filters pins, king safety and special-move legality.

This is a declared model and search-policy change from full legal minimax.
Ordering, QS tree, node use, scores and learned values can change. The
approximate negative value is never a pruning certificate: the QS SEE-negative
test is wholly removed. Incomplete values never adjust ordering. Shared
stopped/deadline is checked after successful make and UNKNOWN propagates before
arithmetic. Illegal -MATE and SEE_INCOMPLETE(-32001) remain distinct from legal
completed values. The old private million-visit state is removed with the
Exchange model. Old minimax, DEV, visit-counter or stack evidence is not inherited.

All bytes outside the three fixed regions remain identical to the accepted
input-profile source. Qualified single-singular, production excluded-root TT
and learning fences, full-key coherent TT, generator/make/attackers/material,
board/hash/HCE, rules/repetition, resources and pool/lifecycle are preserved by
that source complement. Source preservation does not imply identical search
results after changing the ordering and QS policy.

## Current identities and evidence

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C |11430|54759113c9949f0f3d619d5eefe5e8ac4d6b562baf4c09da7e7743907d3f8a2a|
| Native |26360|483a2b6c1f420a30d2f04f1acab9101f6b7dc44c06e1485117a2e8117f1365dd|
| Complete file |5357|8b8c3b565974813aa2ea54383bcc19240c1dcf506157d2aa0b44c8b24fa3d5be|

Bootstrap SHA-256 isac3cbb751445b451fecfb28d6b43ca711879b6c10797e52c35eb872a353ba523.
The old DEV source/full-native gates remain31ef1cb522371a0094effb098c8ea9c0a78ff800c01da9eef5087c5b43e18ec2
and9e5ac53ca94cf36e6ac43632d2e507598deb516e40405bafa6bd874e56069c30.
Their equality was observed twice in this normal run; they qualify the distinct
reference tuple, not the production LVA model.

Packaging remains prefix77 and fixed LZMA1 ALONE9e/lc2lp0pb0/BT4/dict64MiB/
nice32. The earlier LVA-only first cost used native1/package1 and strict pure decode2. Native
grew8 bytes and whole shrank35 versus the accepted input profile; neither
independent source savings nor prior reductions were added as predictions.
No native metadata exception applies. ALONE has no checksum; exact source,
bootstrap and argv recovery is separate evidence.

Focused production-model evidence used the exact11702 candidate in one O2
include fixture. Independent legal rules computed46 roots plus43 selected
subcalls:85 legal score/state/source/promotion rows,2 illegal initial rows,
2 normalized-away EP exclusions and6 cancel/deadline guards. Both colours,
kind-before-square priority, ctz tie order, pinned-source fallback, king
recapture legality, EP occupancy/removal, all initial and recapture promotions,
negative continuation decline and incomplete propagation passed. A fixture-only
external clock port made child cancellation deterministic; it is not evidence
about production wall-clock timing.

The counterexample k7/8/2p1B3/3n4/1rP1P1K1/1b6/8/8 w - - 0 1, e6d5
gave+90 in independent Python full legal minimax and-10 in actual production Q.
No old binary was compiled for that reference. This observed difference is
why approximate negative values are not used by QS pruning. The mirrored
case gives+90 under the changed ctz order; colour symmetry is not claimed.

Cost receipt SHA-256:01daf1ba45610f8121cc18ec5f781dea3eff46ddf250ff32c7aab59d48ed168e.
Focused proof receipt:5bb133e2d840c61c4d1f8fcee8042080ad1ebcfafdb0acfbafb18c37c08a9aa1.
Focused final receipt:08793fb0790909aa6057f6f42c3cf4630b23624a240c1fbf4e1caf52803dc462.
These are external evidence metadata; no evidence file is a normal input.

The inherited input profile accepts NUL-free text, max32767 bytes before LF or
final EOF including CR, and space/tab/CR/LF delimiters with exact first command
tokens. Overlong lines drain/drop; VT/FF are not delimiters and embedded NUL is
outside contract. Numbers are whole ASCII decimal0..LLONG_MAX. Four exact clock
keys consume one value; last own-side values win. Absent own clock defaults
1000ms and invalid/zero/missing time has at least1ms. Existing budget caps,
nullable legal query with made child and transactional replay remain unchanged.
Input-profile normal B5461 receipts c196fc146544681c216d7542a5ffc90fdb03361f2e769ba86acea2b61d73e424
and a20b0f0d1687d1786c63df32d58e8b93cb4211105b87c2292d53a442ff4b2078
remain ancestry for that prior image, not current-image execution.

The previous LVA-only normal builder completed shipping2 and DEV-reference2.
Its shipping tuple was B5426, not the current shared-walk pins above;
each DEV source/full native retained the old reference tuple. The unchanged
selected verifier completed quit/EOF2 sessions and8 legal GO. It observed the
exact new native image,3 persistent startup TIDs, absent compiler/helper
children and restoration paths, one closing result, finished readers, process
absence and physical exit0. Cancellation causality remains unproven. Its
unchanged compiler helper does not separately observe compiler descendant/group
absence. No old metadata exception was applied.

Normal build receipt SHA-256:f9c1c3b969cae739885dd3cccf2c5f6d88768504ae7ca67d46dbbd4e697a91c2.
Normal runtime receipt:a2d12a0fe8cafca23a9a4a4b862e655dc6364fc4d0c5ceeda9904668919b608c.
Producing closure22 was frozen before execution; only recipe validation metadata
and this README change afterward. The original producing recipe/README and full
ordinary source snapshot remain external. Unchanged fresh.py finds
the additional ordinary helper through recipe helper_sha256; fresh extraction
and archived rebuild are0 at this checkpoint. No additional fixture, DEV engine,
game, benchmark, strength, stack or scaling qualification is claimed.


## Shared forward geometry (unchanged B5371 predecessor stage)

The final pure shipping_walk helper replaces reverse attackers395 and gen727
with one forward walker/prototype/attackers wrapper900 and gen wrapper52,
source-170. It enumerates the actual incremental occupiedBB in ascendingctz.
Query mode returns every attacking source bit, tests target before friendly
occupancy rejection, counts empty pawn diagonals, and emits no push/castle.
Generation retains source/direction/push/all4promotion/castle order. Square0
is valid because mode is the move-buffer pointer. Castle query mode cannot
recurse into generation. LVA keeps its piece-BB kind intersections and all
other source bytes remain exact via10580-byte protected complement. Existing
BB/mailbox coherence, make legality, normalized EP, full-key TT, singular and
excluded-learning fences are retained. All previous source guards run first.
DEV bypasses the stage and remains the distinct old full-minimax reference.

The actual first cost is source11532/native26384/whole5371, reducing170/16/55
bytes respectively from the prior normal. Fixed compiler/profile/bootstrap77/
ALONE9e/nice32 remain unchanged. Cost receipt SHA-256 is
14a7cba0f1aa3a190f71d81276282ab3151d49bb7d5456eee8cf99879e56cf1d.

Focused actual old/new production-source fixtures passed99 complete pseudo-list
orders per source,12672 full geometric attacker masks per source against an
independent64-coordinate oracle, and1281 complete legal child states per source
against the existing independent rules oracle. They retain85 legal/2illegal
LVA rows,2 normalizedEP exclusions and6 clock/cancel guards per source. Open,
blocked, origin/transit/destination-attacked and missing-rights castles are
included. The clock port is fixture-only. Proof SHA-256 is
57367b67b1dd783c3c5c1740d01afa3ab5410d64ab0848698972b9edcf320579.

Queries may be slower: up to16friendly sources and their forward rays replace
target-centered rays. No performance, strength, exact timed-search result or
whole-stack equivalence is claimed. The single authorized normal builder
completed shipping2 and old DEV-reference2 with the exact pins above. The
unchanged verifier completed actual new-image quit/EOF2sessions and8 legal GO,
observing3 persistent startup TIDs, absent helpers/private restoration paths,
one legal closing result, finished readers, absent process and physical exit0.
Cancellation causality remains unproven. The unchanged normal compile helper
does not separately observe compiler descendant/group absence. Native metadata
exceptions remain0. Normal build receipt SHA-256:b17212d6914e3d0e02a4b0488a6aab27e34b55bf471bdce1274a04444ba8305d.
Normal runtime receipt:0de3dd1ac8d0b4b57808f0d116bbfdb69ee16ce1336f69aef62aa9b5307d4fcc.
Producing closure23 is frozen separately from completion recipe/README metadata.
Fresh0, extra fixture/oracle/wrapper session0, DEV engine0, game/benchmark/retry0.


## 고정 두 worker 결과 선택과 출력 잠금 축약

이 단계는 기존 condition_sharing 뒤에서만 적용되는 shipping 전용 pure 변환이다.
기존 guard와 원 참조 admission은 먼저 그대로 통과하며 전체 inverse는 정확한
post-condition 소스를 복구한다. canonical·DEV와 A/D/F/F8은 이 단계를 사용하지 않는다.
두 literal 영역/세 보호 gap 이외는 전체 bytes가 같고 raw 소스는 63B 감소한다.
깊이 비교는 worker1이 엄격히 클 때만 선택하므로 동점은 원래처럼 worker0이다.
양 worker의 검색 완료 게시와 동일 pool mutex 아래 결과 읽기는 그대로이다.
각 printf/puts 한 호출의 같은 FILE 내부 잠금과 결과의 자체 fflush 완료 후
completion notify·drain·다음 GO/position 게시 순서는 보존한다. 이는 한 OS write,
외부 raw-fd 원자성 또는 printf+flush 전체 트랜잭션 동등성을 뜻하지 않는다.
바깥 flockfile/funlockfile 제거로 main reply가 계산 중이나 printf와 flush 사이에
끼어들 수 있다. flush batch·가시 시각·stdio 경합·스케줄과 시간제 검색 결과는
달라질 수 있고, 기존 무시된 I/O 오류 정책도 바꾸지 않는다.

고정 ONEcost 결과는 전체 5023→5006B,
새 native SHA `e237a567db7c6140a11b26d38182b53f18891fed4701bf4556160f93902bb079`이며 원 native 전체 동일 주장은 없다.
소스·native·bootstrap·전체 expected는 원 firstcost bytes에 명시적으로 고정했다.
B/E nice32·C nice64 및 C -mavx2, GCC13·header73·FD0 literal/template는 그대로이다.
원 reply LOSS9 후보와 합성하지 않았다. 비용 stream B→C→E 당시 별도 D/F8 비용
stream이 겹쳤으며 wall time이나 성능·메모리·기력 개선을 주장하지 않는다.

OUTPUT_NORMAL_PASS: ordinary --dev를 한 번 실행하여 shipping 두 번과 기존 DEV 두 번을
재생성했다. 전체 source/native/bootstrap/whole은 원 firstcost bytes와 같고 DEV
source/native는 실제 이전 condition baseline bytes와 같다. unchanged selected는
새 실제 wrapper에서 quit/EOF 두 session, 합계 여덟 GO, 각 main+두 worker의 3TID를
관찰했다. 새 native image·private-path 제거·closing bestmove·reader 완료·물리 종료가
확인되었고 원 handle은 terminal0/reaped/당시 group 부재/강제정리0/owned0으로 닫혔다.
B→C→E 순서로 각 ordinary+selected를 한 번씩 수행했으며 late PID 조회나 추가 양성
재실행은 없다. Build SHA `893cb1b9d4154812fd160aeed2d52949c75cc207a7d61a19ce3defde251406cb`, runtime SHA
`e3aaab5a939ab49fb85413e67cd444930b334987590808f63d8a3862af24a81c`이다. Producing recipe SHA는
`772631687fe957a8229c567dd9696aac03a9e0957e685f3c0fc9fdfc1f0af2a9`이며 최종 recipe/README 차이는 완료 주석뿐이다.
기존 runtime ancestry와 새 이미지 검증을 구분한다. 이 결과는 좁은 selected 경로의
근거이며 grouped flush/timed trace 동일성, 성능·RAM·기력·전체 qualification이나 새 CI
성공을 뜻하지 않는다. 추가 SAN/NVC/codec검색/fault campaign/학습/선택 소비자는0이다.


## 공통 worker 시작·완료 epilogue 공유

새 pure `../tiny-entry-a/shipping_worker_epilogue_bce.py`를 기존 condition/output
chain 뒤 shipping에만 연결했다. 현재 소스 10179→10152 B,
native 26128→26112 B, 실제 73 B launcher를 포함한 whole
5006→4997 B이다. Source SHA `ce8d99777f61c50e44eb4a7c29783bf80b13ca9cbaeac660992eb5ebaec829df`,
whole SHA `5e6756ce518d05c7900b6445f108055d96590df5cd6d91a84510e615a86a71e3`를 고정했다.

worker local `w=0`이 startup만 표시하고 첫 epoch admission 전에 원래 static
worker 인자 p를 같은 mutex 아래 대입한다. Startup과 완료의 pending 감소·마지막
방송을 공유한다. B/E는 별도 ready 대신 pending=2와 직접 startup wait를 쓰며
새 U() 호출과 stopped store는 추가하지 않는다. C의 기존 pending/V startup은 유지한다.
Startup broadcast 2→1이므로 wake·lock 경합·고정 deadline의 탐색 순서는 달라질 수 있다.
최종 완료의 기존 result/own fflush 뒤 broadcast와 drain fence를 보존한다.

정확한 span/gap/complement hash와 full literal inverse가 post-output 소스로 돌아가며,
그 앞 output/condition의 원래 가드·역변환 체인은 유지한다. Canonical/DEV, B SEE/singular,
C 실제 SIMD, E untrained E19/model order, 공통 HCE/PVS/QS/full TT/learners/rules는
변경 외 바이트다. 부분 생성 실패는 기존 shutdown jump로 ending drain을 건너뛰고 실제
생성 수만 join한다는 소스 검토 범위이며 주입 실행은 하지 않았다.

WORKER_EPILOGUE_NORMAL_PASS: ordinary --dev를 한 번 실행하여 shipping 두 번과 기존 DEV
두 번을 재생성했다. Source/native/bootstrap/whole 전체는 고정 firstcost bytes와
같고 DEV source/native 전체는 실제 이전 output baseline과 같다. Unchanged selected는
새 실제 wrapper의 quit/EOF 두 session, 합계 여덟 GO, 각 main+두 worker의 3TID를
확인했다. 새 native image·private-path 제거·closing bestmove·reader 완료·물리
종료와 원 handle terminal0/reaped/당시 group 부재/강제정리0/owned0을 기록했다.
B→C→E 순서로 ordinary+selected를 각 한 번 수행했으며 새 owner outer TERM/KILL
grace는20초다. 원 runtime helper·verifier PINS/assertions는 그대로다. Build SHA
`475316ee431b69d14174638ade00bcc7e9d182600bc190db9a9c779ec4cee6b3`, runtime SHA
`f3794be822f65ed843883bc6ffb9d57068a744e77466a4c6ad94ea4f35b1461b`이다. Producing recipe SHA는
`aaa2cf9fd9847358f6ef672f06869d8a490e25e07b293f0dbc369adeaec8995f`이며 최종 recipe/README 차이는 완료 주석뿐이다.
Startup broadcast/wake와 고정 deadline의 방문·결과 trace 동일성은 주장하지 않는다.
cancellation causality는 unproven이며 partial-create/join fault·epoch wrap 주입,
SAN·추가 fresh·학습·성능·RAM·기력·전체 core qualification·새 CI는 실행/주장하지 않았다.
Firstcost는 family당 compile/encode 각1이며 baseline 재측정·추가 후보·cost 재실행은0이다.


## Piece setter의 제거·삽입 phase 공유

공통 pure `../tiny-entry-a/shipping_setter_phase_bce.py`를 기존 worker stage 뒤 shipping에만
연결했다. Source 10152→10062 B, native 26112→26112 B,
73 B launcher를 포함한 실제 whole 4997→4991 B이다. Whole SHA는
`68c8bd3a767a5e5c79d57fff0ae45be1e217c23cd792725e59b867fa5ecf0734`다.

setter에서만 쓰던 private hash/feature leaf를 합치고 n=-1/+1의 두 phase가 한 본문을
사용한다. Nonzero piece guard와 remove→mailbox 한 번 저장→add→king 순서, C의 개별
int16 대입 변환, B bitboard/HCE와 E19 feature식을 유지한다. 실제 square/piece domain의
정수 범위와 local Board 소유권을 검토했다. 원 helper guard·정본·DEV·SEE/singular·SIMD·
weights/order·full TT/learners/SMP/rules는 변경 외 영역이다. 두 spans/세 gaps/complement와
전체 inverse가 정확한 post-worker source로 돌아가며 별도 literal adapter는 필요하지 않다.

호출/loop/branch의 시간은 달라질 수 있어 고정 deadline의 방문 순서·TT interleaving·
nodes·bestmove 동일성은 주장하지 않는다. F의 동형 setter 후보는 별도 LOSS6/미채택이며
BCE의 gain을 F/F8에 일반화하거나 합성하지 않았다.

SETTER_PHASE_NORMAL_PASS: ordinary --dev 한 번으로 shipping 두 사본과 DEV 두 사본을
재생성했다. 새 source/native/bootstrap/whole 전체는 고정 firstcost와 같다. DEV
source/native 전체는 실제 previous-worker 산출물과 대조해 같음을 확인했으며,
이것은 진단 reference의 재현이고 새 shipping 모델의 동등성 증거를 대신하지 않는다.
원 selected는 새 native image에서 quit/EOF 두 session·여덟 GO·3 startup TID,
private-path 제거·closing bestmove 한 번·reader 완료·물리 종료를 확인했다.
원 여섯 command handle은 가족직렬로 terminal0/reaped/당시 group 부재/강제정리0/
owned0으로 마감했다. Runtime SHA는 `8d4577a333b9c3bf9284b32d27358af2bafe24756012557142a5b1df2d2bba46`이며
build/runtime 영수증은 recipe setter_phase.normal_validation에 연결했다.
Producing 후 recipe/README 차이는 완료 주석뿐이다. Causality는 unproven이며
추가 SAN/fault/epoch-wrap/fresh/학습/cost 재실행·성능/기력/새 CI는0이다.


## 고정 object macro 네 개의 직접 치환

공통 pure `../tiny-entry-a/shipping_constants_bce.py`를 setter 뒤 shipping에만 연결했다.
PLY=128, MOVES=512, HISTORY=4096, MATE=30000의 정의와 실제 code token만
같은 unsuffixed int literal로 바꾼다. 고정 spans·보호 gaps·전체 inverse와 기존
입출력 guard를 유지하며 정본·DEV·원 parser·codec·탐색 기능은 그대로다.
Firstcost 전체 header CPP token과 native 전체 bytes가 원 baseline과 같다.
Source 10062→9981 B, whole 4991→4955 B
(73 B launcher 포함, delta -36 B), whole SHA `bc21207f6f80ef68cce87e2440a299a72d169b607b326454f6ac3f401f5e8964`.
Macro-table와 진단 source 위치의 동일성은 주장하지 않는다.
CONSTANTS_NORMAL_PASS: ordinary --dev 한 번으로 shipping 두 사본과 DEV 두 사본을
재현했다. Source/native/bootstrap/whole 전체가 고정 firstcost와 같고 native와
진단 DEV source/native는 실제 이전 setter 산출물 전체와 같다. 원 selected의
quit/EOF 두 session·여덟 GO·3 startup TID·private-path 제거·closing bestmove 한 번·
readers 완료·물리 종료를 확인했다. 원 command 두 개는 terminal0/reaped/group 부재/
강제정리0/owned0으로 닫았다. Runtime SHA `479c096717156a7f4ce0dd0fa500d360e9821da53e8caf68c3cccefc8d924001`.
Recipe constants.normal_validation에 build/runtime 영수증을 연결했다. 이후 변경은
완료 주석뿐이며 causality는 unproven이다. 추가 SAN/fault/fresh/학습/기력/성능/새 CI는0이다.


## Shipping 단일 int alias — 2026-10-24

마지막 constants 단계 다음에 pure `shipping_int_alias.py`를 적용한다. 원래 독립
I token이0인 고정 source에서 실제 int keyword99개만 I로 바꾸고 모든 include
뒤에 `#define I int`14B를 둔다. Source9981→9797(raw−184), 실제 전체4955→4954
(−1B)이며 둘은 별도 측정이다. 전체 CPP header/code token이 같고 native26112/
274bf31c… 전체 bytes도 같다. Macro table과 진단 위치는 동일하다고 주장하지 않는다.
100 spans/101 gaps/전체 inverse는 원9981을 복원하고 기존 constant/setter/earlier
admission을 먼저 통과한다. DEV와 기존 모델 false flags는 그대로다. 실제 B package는
고정 소스 hash literal guard 없이 기존 common.source_literal의 raw-bytes-single을
소비하므로 literal inverse adapter를 추가하지 않았다. 실제 기존 package 함수와
FD0 template·header73·GCC13 stdc11/Os/pthread·LZMA9e/BT4/64MiB/nice32를 그대로
사용해 source/bootstrap/EOF/trailing의 Python/CLI 양쪽 복원을 확인했다.

INT_ALIAS_NORMAL_PASS: ordinary --dev 한 번에서 shipping 두 사본과 기존 DEV
두 사본을 재현했다. Source/native/bootstrap/whole 전체는 원 firstcost와 같고
DEV source/native도 실제 이전 constants baseline과 같다. Unchanged selected
한 번에서 quit/EOF 두 sessions·여덟 GO·3 startup TID·실제 native image·private-path
제거·closing bestmove·reader 완료·물리 종료를 확인했다. 원 driver/build/selected
핸들은 WNOWAIT leader identity 유지 상태의 extras[] 확인 뒤 reap했으며 종료 당시
group 부재·강제 정리0·owned0이다. Build SHA `fc97c7435135ebfaa49d80838128093b52c37f5bccb51d0f4e091e67f50cc380`,
runtime SHA `a45d47fed0632ef536dc2a9186d89da127712f4ccbdd03db535ae2ccb0b2a682`이다. Producing recipe SHA는
`b3c137086c54f4da26e33c8e0b0665b131b84c78eaa4f4f9b08dc67e5d33775d`이며 최종 recipe/README는 완료 주석만 달라졌다.
기존 모델 false flags와 DEV 진단 reference의 의미를 보존하며 DEV 재현을 새
shipping 모델의 oracle로 쓰지 않는다. FD 관찰·cancellation causality·성능/RAM/
기력·추가 후보/codec/framework/SAN/NVC/fault/fresh/학습·새 CI는0이다.

## Compiler-group ownership adoption

현재 생산자는 기존 source/literal/argv 검사를 마친 뒤 `engines/scripts/compiler_group.py`를 encoding 직전에 적용한다. 컴파일러 원 leader를 `WNOWAIT`로 보존한 채 살아 있는 같은 process-group 작업을 정산한 뒤 마지막에 reap한다. Python 진입 시 SIGCHLD disposition을 저장·정규화하고 native exec 전에 복원한다. 원 C/source·compiler argv/env/cwd·stdio·읽기 FD exec·legacy exitstatus는 유지하며, 단순 크기 손실로 이 수명 수정을 숨기지 않는다.

| 현재 생산 context | 이전 whole | 새 measured whole | 새 bootstrap |
|---|---:|---:|---:|
| B | 4950 | 5342 | 11804 |

위 값은 각 actual 기존 입력에서 고정 codec 한 번과 strict Python/CLI 복원으로 먼저 측정한 값이다. source/native/compiler/header/codec의 변경이나 다른 문맥 delta의 가산은 없다. 기존 frozen control과 과거 qualified receipts는 당시 범위로 보존한다.

이 entry는 local source/Data proof 및 fixed-cost 측정까지 수행했다. 새 HEAD의 ordinary/positive CI 검증은 별도로 필요하며, F 기본형 양성 결과를 이 프로필의 새 runtime 결과로 재라벨하지 않는다.
공유 세 형상의 기존 packaging suites는 stream5·ZIP4·restored-files5 tests 모두 통과했다(skipped0). 이 관측은 live same-group 정산이며 detached 작업이나 zombie를 포함한 문자 그대로의 group absence 일반 증명은 아니다.

실제 producing/measurement/normal receipt는 recipe의 `compiler_group_ownership`에 명시했다. 공통 source helper에 대한 alias-only 후보 raw−389/whole+8 손실은 과거 미채택으로 남고 여기서 재실행하지 않았다.
