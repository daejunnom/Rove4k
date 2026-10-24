# Maintained C: seek-implied compiler-source flush — 2026-10-24

Fixed candidate whole **4948→4944 B (-4 B)**; bootstrap
10827→10817 B. Whole SHA-256:
`0cc1fe0f53eb862e76123b0f56b93778fca984ccdd81351cfc15ca4f5a6ca32f`.

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

# Maintained C: terminal compiler stdin and shared wait — 2026-10-24

Fixed W1+W2 first-cost winner: **4995→4948 B (-47 B)**; still 852 B above4096.
Bootstrap 10947→10827 B. Whole SHA-256 is
`6b7d44324a248caa9c38dac168298377ea45229f37ee25606eb9c656b6c69499`.

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

# Maintained C: unused published score removed — 2026-10-24

현재 full shipping의 전체 파일은 **4995 B**다. 동일한 compiler-owner 수정·73 B
header·nice64/BT4/64MiB codec에서 실제 이전5002 B보다7 B 작다. 기존4628 B는
이전 compiler-owner 조건의 기록이며 현재 비용 비교의 기준으로 사용하지 않는다.
4096 B까지899 B가 남아 있고 출품 크기 통과나 기력 향상을 주장하지 않는다.

`shipping_dead_score.py`는 late-four-constants 뒤의 정확한 full C source에만
적용한다. Worker의 사용되지 않는 score 필드 `l`, reset/commit 두 store와
think의 반환값 바인딩만 제거한다. 이 닫힌 shipping 경로에서 결과와 pool은
완료 깊이 `C`와 best `H`만 소비한다. `h` 호출의 인수·부작용·내부 local score,
고유 signed-net/SIMD, PVS/TT/learners, stop 확인·best/depth 게시와 worker
drain/result/flush/join 순서는 그대로다. 정본과 DEV는 이 단계를 통과하지 않는다.

생성기는 새 source를 원래8992 B로 역변환한 뒤 기존 constants→pool→cross와
common literal·read-only template 보호를 실제 통과한다. compiler owner를
적용한 실제10969 B bootstrap의 source literal만 마지막에 바꾸며 다른 바이트와
argv를 유지한다. 네 source span·다섯 gap과 source/bootstrap 전체 inverse를
검증한다. 이전 guard의 기대값은 변경하지 않았다. helper는 recipe의 local 입력으로
해시를 고정해 복사한 뒤 로드한다. 생성 파일만 직접 수정하는 방식이 아니다.

실제 firstcost: source8992→8970 B, bootstrap10969→10947 B, 전체5002→4995 B.
Whole SHA-256은 `82dcd3a73718b5b50febc94f936ac46125426a937c07c8431617eda8f3fe40ae`다.
후보 encode1·strict Python EOF/trailing0·CLI byte inverse1씩을 확인했다.
이후 실제 후보를 동일 `cc -Os -mavx2 -x c - -o x -s`로 한 번 별도 컴파일해
native22672 B/`976a841110eaf44209d0e6dbf6393609ef49472c5c1fae4c4b7fcd63bcc4a846`를
새로 발견했다. 이전 native와 파일 크기는 같아도 바이트 동일성은 성립하지 않는다.

실제 old/new 선언 prefix를 사용한 두 compile-time `sizeof`/`offsetof` probe는
Linux x86-64 현재 ABI에서 Worker68976 B·align8 유지, `H` offset12→8,
`a5`와 뒤 배열 offset 유지임을 확인했다. probe나 엔진을 실행하지 않았으며
RSS·stack·속도 개선으로 확대하지 않는다. 모든 discovery 자식은 원 리더를
reap하기 전 그룹 정착을 확인한 후 종료했고 강제 정리0·owned0으로 마감했다.

DEAD_SCORE_NORMAL_PASS: 기존 ordinary `--dev` 한 번에서 shipping 두 사본의
source/native/bootstrap/whole이 firstcost와 fresh-native discovery에 일치했다.
DEV 두 사본은 기존 source/native 전체와 동일하다. 변경 없는 selected verifier 한 번은
실제 새 native에서 quit/EOF 두 session·여덟 legal GO·3 startup TID·FD0/1/2,
private path 삭제·compiler child 부재·closing bestmove 한 번·reader 완료·물리 종료를
확인했다. 원 outer 두 개 모두 terminal0/reaped, reap 전 다른 group member0,
group 부재·강제정리0·owned0으로 종료했다. cancellation causality는 unproven이다.

이 실행이 소비한 recipe는208473 B/`6daac5714cf2679b0d313d597d0ed24716543aab339c613e04392339185139e2`로
별도 보존했다. 실행 중 README87861 B/`2ec6fa9867bfe635690072823ee1dbf8f335184f4600031f59588ad98583df3f`도
바뀌지 않았으나 README는 builder 입력이 아니다. 실행 뒤 recipe의 normal status와
이 문단만 사실 주석으로 갱신했다. helper/build/selected 기대값·DEV 기대값은 동일하다.
firstcost·fresh-native discovery·qualification과 producing/final annotation 해시는
외부 `rove4k-c-dead-score-promotion-20261024-evidence`에서 구분한다. 이전 receipt의
성공을 새 native의 성공으로 상속하지 않았다. 추가 SAN·fault·game·CI는 실행하지
않았으며 시간제 node/TT interleaving·모든 score trace·기력/속도 동일성은 주장하지 않는다.

## 이전 source/compiler 단계의 기록

# Maintained C: common PVS/runtime with original signed-net SIMD — 2026-10-24

현재 shipping은 C의 실제 `int16_t x[8]` signed-net 상태와 고정 8개 계수,
scalar HCE·제거/삽입 setter·128비트 `_mm_madd_epi16` 평가를 공통 mailbox
PVS/runtime에 연결한다. fixed2/TT18과 `-mavx2`를 유지하며 256비트 구현이나
새 lane 수를 요구하지 않는다. 모델 계수·기능은 삭제하지 않았다.

`shipping_cross_c.py`는 기존 constants 뒤의 shipping 분기에서만 호출된다.
전달된 실제 C 모델 세 영역을 역할별로 bind하고 읽을 수 있는 C-owned 영역을
기존 minifier로 조립한다. 원 C code도 같은 helper의 역변환 데이터로 남아
기존 common literal과 FD0 template 소비자가 실제 원 source를 먼저 검증한다.
부트스트랩은 compiler와 source literal 두 영역만 바꾸며 세 gap과 전체 inverse를
검증한다. 정본·기존 guard/helper 체인과 DEV reference는 유지한다.

선택한 compiler는 `cc -Os -mavx2 -x c - -o x -s`이다. 공통 A compiler 정책과
C ISA를 함께 이식한 별도 source/compiler 변형이다. 기존 C의 `-std=c11 -pthread`
shipping flags를 유지했다는 뜻은 아니며 이전 preprocessor와 DEV compiler는 그대로다.
Full-key TT, PVS/LMR, history/continuation/correction, king-capture reject,
draw/cap QS·TT guard, 512 move-buffer guard, pool drain/result/flush/join과 입력 규칙을
보존하도록 검토했다. 이전 C의 실행 trace·시간제 nodes/depth/result·기력·성능
동일성은 주장하지 않는다.

완료된 setter 경계에서 x[1..6]은 색별 count 차이고 x[7]은 signed positional
residual이다. 각 int16 저장과 remove→mailbox 한 번→add→king 순서를 유지한다.
현재 HCE의 center j는 [-7,5]이고 residual은 보수적으로 기물당 절댓값63,
32기물 합2016 이하라 int16에 안전하다. 실제 static HCE의 절댓값은29120 이하다.
고정 weight의 임의 int16 입력도 dot 절댓값70483968 이하라 madd/int32 합에 안전하다.
EP canonicalizer의 mailbox-only scratch는 lane이 일부러 갱신되지 않는 attack-only
임시값이며 평가·setter·검색으로 넘기지 않는다. Empty EP victim의 HCE(0,q)=0도 유지한다.

ONE firstcost는 source9527→9093 B, bootstrap10566→10054 B,
native26152→22672 B, `.text`7556→7505 B, 전체4778→4672 B(-106 B)이다.
73 B header와 기존 nice64/BT4/64MiB codec을 포함한다. Whole SHA는
`cd66a664d90d862b9c557c7586d1d24613474115f9670fca427113b89fdb1176`이고
new native SHA는 `f35ec4454b87468519ea5d58d659bc6f90247b1d8736bfa6526cfa266fb2ae46`다.
기준선 재compile/encode0, 후보 각1, strict Python2/CLI2 전체 source/bootstrap 복원과
EOF/trailing0을 통과했다. 원 outer/child 모두 terminal/reaped/group 부재/강제정리0/owned0이다.
준비의 native 경로 assertion은 제품0에서 실제 build.json 경로로 정정했고 원 진단을 보존했다.

CROSS_NORMAL_PASS: actual new TU를 바꾸지 않고 old C 고유 정의의 역할 이름만
alias한 finite focused를 1 compile/1 run했다. Fatal GCC13 ASan/UBSan에서 독립 int64
oracle·old scalar 합·actual old/new 8lane/SIMD·refresh·완료 put 사례2784·typed parent
보존을 확인했다. Model scan2965/scalar값189760/signed16 basis·mixed88/EP scratch4와
양side capture·EP·네 promotion·양쪽 castle을 포함한 legal child154가 통과했다.
수치는 실제 관측 범위이고 별도 test-count 의무나 모든 C/search 동등성 증명이 아니다.
ASan 가상주소64TiB와 별도 hard RSS512MiB/CPU25초/wall30초를 사용했으며 peak/stack
최적성은 측정하지 않았다. `put_phases` 출력은 중간 store 계측이 아닌 완료 put 사례 수다.
Ordinary --dev 한 번에서 shipping 두 사본의 source/native/bootstrap/whole 전체가
firstcost와 같고 DEV 두 사본은 실제 이전 C source/native 전체와 같았다.
Unchanged selected 한 번은 새 native에서 quit/EOF 두 session·여덟 GO·3 startup TID,
FD0/1/2·private-path 제거·closing bestmove 한 번·reader 완료·물리 종료를 확인했다.
원 focused와 normal outer/child 모두 terminal0/reaped/anchor 유지 중 extras0/
당시 group 부재/강제정리0/owned0으로 마감했다. Producing 이후 recipe/README 차이는
완료 주석뿐이며 helper/build/expected는 그대로다. 이전 성공을 새 image 성공으로 상속하지
않았으며 cancellation causality는 unproven이다. Old C trace/TT interleaving·시간제 nodes·
기력·성능·stack 크기·모든 core qualification·새 CI·학습/AWS는 주장하지 않는다.

## 이전 단계 기록

# Maintained C: one pool condition — 2026-10-22

The fixed first-cost complete file is **4845 B**, source
**9763 B**, native **26272 B** and bootstrap
**10802 B**. Complete-file reduction is **15 B**
from the actual FD0 baseline; source reduction is 37 B.
The new entire native is `ae8c853841040ad22c80dd49331a4491606b664315acd9db57ad278cb42104fb`.
The shared pure `tiny-entry-a/shipping_condition_bce.py` is called with
explicit family C after its original last shipping C stage. C uses startup pending2 and initial V drain, without a ready counter.
Its exact 4 spans/5 gaps/full inverse preserve every other byte.

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
`4c6b5e2470d02e381a32cc41ac51e73fe388c7302086f9a63beaf33067bb7d92`.

Ordinary --dev ran once and reproduced shipping twice and unchanged DEV
twice. Entire source/native/bootstrap/whole matched the original firstcost
bytes, and DEV source/native matched the actual previous FD0 baseline.
The unchanged selected verifier ran once on the actual new wrapper: quit/
EOF two sessions, eight GO calls and main+two worker TIDs per session.
The new native image, private-path removal, finite input, closing bestmove,
reader completion and physical exit were observed. Build receipt SHA is
`aa8655cef682440805e51a48039c9d4affecc93fbffacfa99d469ee2198005f0`; runtime SHA is
`366c393f36b5ca58f18782f8a630ba0fbde08fe11f70908c36e00d52a334eb2a`.
All original handles settled/reaped with groups absent at settlement, no
forced cleanup and owned0. F4 original normal completed before the serial
B->C->E ordinary/selected stream; F next normal was notified only after all
BCE original handles closed. No late bare PID/TID probe or extra positive
run is used. Producing recipe SHA is `fdb2caa7c9be3802540b49083121d7d092ac7cf8e383847afad1b8874ff963ab`;
final recipe/README overlays are completion annotations only. Existing
runtime ancestry is separate; this validates the new image in the narrow
selected wrapper scope. No new SAN/NVC, codec/name sweep, optional consumer,
feature deletion, training, performance/RAM/strength or new-head CI claim.
The4096 B target and broader qualification remain open.

# Maintained C: shared fixed readonly flag template — 2026-10-22

The fixed first-cost file is **4860 B**, down9 from4869.
Bootstrap10849→10839 B removes10 bytes. Entire C,
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
`651236816a91de72e7155af2501e766a6c339bd38422c5bafb50d2560582f4eb`.
Actual runtime SHA-256:
`f28f9c849079d5ffe3ef7a1a1d0652837dd59c24a640675b805924ae3568a4b4`.
All eight original command handles exited0, were reaped and had absent groups
at settlement; forced cleanup/owned handles0. No late bare PID/TID probe or
product retry is added. Producing recipe/source and final annotations remain
separate. After execution only recipe/README completion notes changed;
shared helper/builders/expected/profile/codecs stayed producing bytes.
Only the shared helper and A/B/C/E build/recipe/README are owned. No new
semantic fixture/SAN/NVC/game/codec search or rootdocs/Git/CI work is added.
Historical sections below retain their own identities and scope.

# Maintained C: shared terminal legal loop — 2026-10-22

The selected complete file is **4869 B**, 5 B below C4874 and 773 B above 4096.
Shipping C is 9800 B (48 B smaller), native 26304 B and bootstrap 10849 B.
The pure C-only `shipping_terminal.py` is last, after `shipping_lane_sum.py`.
It fixes 4 exact regions, 5 unchanged gaps and the full inverse. Canonical
`engine.c`, DEV, initialized signed8 Board state, all coefficients, actual
128-bit madd and signed32 lane sum, learners, full search/SMP policies,
fixed two-worker/TT18 profile, C11 `-mavx2`, 73 B header and C codec stay fixed.

Draw/cap bits 0/1/2/3 share the ordered legal-make loop. The terminal path
skips the whole TT atomic call and ordinary pruning, then returns immediately
after its first legal private child, before root, child path, learner or TT
writes. Cap-only stores stopped; draw+cap preserves draw precedence. No legal
child retains checkmate/stalemate precedence. Entry stop/deadline claim stays
first. Additional initialized own-worker ordering reads, local scratch and
private child order/work/timing may differ. Their traces, cross-worker clock
schedule and cancellation causality are not equated with the old scan.

The actual new TU was included unchanged. Only the old P definition name was
aliased, with exact inverse and all non-P source bytes protected. Every old
call was established as entry-rejected or draw/cap terminal before execution;
the residual recursive P references were never reached. One fatal GCC13 C11
O1 ASan/UBSan compile and run passed 28 finite inputs: entry prestop/deadline,
halfmove/reversible repetition/dead draw, cap-only/draw+cap, mate/stalemate
precedence and both-color EP/promotion/both-wing castling legality. Typed Board,
Worker/history/path/learners, root and job history stayed unchanged beyond
the entry node claim, with actual old/new scores/stops/root/node counts equal.
Full warm-TT payload/key and held-lock observations passed; zero transient
atomic probe is a separate source argument, not inferred from final snapshots.
Constructed cap/FEN/history boundaries are private initialized adapters,
not full public-game reachability or complete engine/concurrency proofs.

The SAN commands exited 0 with empty stderr, reaped groups absent and active
handles 0; the firstcost was reused without a new compile/codec search.
One ordinary `build.py --dev` call reproduced source/native/bootstrap/whole
twice, exactly equal to the frozen firstcost tuple, plus the unchanged DEV
source and entire native twice. One unchanged selected verifier passed quit/EOF
2 sessions and 8 legal GO, exact restored native, 3 startup TIDs each, stdio-only
FDs and private-path/helper/readers physical exit. Original build/selected
handles exited 0, were reaped and left groups absent, with empty stderr, no
retry, forced cleanup or active handle. Additional broad core/game/performance
coverage and cancellation causality remain unproven.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping source | 9800 | `32861867de077f5d09eb631650b854164cd6f32369a57200337743a88f717103` |
| Native | 26304 | `011e671f31d0fed3478087c9810a5fe6bef7a9ecb359d9ef1b929ab2c35defba` |
| Bootstrap | 10849 | `b7be7214684f6f87dff7a19ecb7c9571e4711c53a901df2faba1ac06faa4f232` |
| Complete | 4869 | `cbc770271bb9b71ae2e88ecbf13941de8e8a802211e08adbd68ff82123e011b8` |

Actual output: `/home/stemxstudio/rove4k-c-terminal-shared-promotion-20261022/normal/build`.
Focused receipt `03d493dd913b184bb5d33cf8debf33c16bb6cf1f4208c5bfac8a378520c45ac6`;
normal build `3966dd974488bada4a269d1f4de0d0c7aecd8cbcc69f1f98eae7eff65f3b9cf9`;
selected runtime `9575c719b395f452f9bc7e7828420948f60201484f8800b3aa9b350797d70125`;
producing recipe `221629b75cfc750887ad9725ec394df85586caefd33dc0379a5a4a25d9a07907`.
Only this README and recipe normal-validation annotation changed after the
producing revision. Helper/build, expected artifact identities, compiler,
canonical/DEV, profile, header and codec retain their producing bytes.

# Historical C: signed32 lane sum — 2026-10-22

The selected complete file is **4874 B**, 6 B below C4880 and 778 B above 4096.
Shipping source is 9848 B (34 B smaller), native 26304 B and bootstrap 10897 B.
`shipping_lane_sum.py` is a pure C-only late stage after capture metadata.
One exact 194→160 B evaluator region, 2 protected gaps and full inverse keep the
remaining source exact. Canonical `engine.c`, the older gather DEV reference,
all 8 features, coefficients, Board updates, learners, search/profile, 73 B header,
fixed ALONE codec and `-mavx2` compiler remain unchanged.

The same two 16-byte loads feed the same 128-bit `_mm_madd_epi16`. Its 4 signed32
lanes are summed through the fixed GCC13 `__v4si` value cast and constant lane
indices, in place of 2 horizontal-add intrinsics and extract. No pointer alias
cast or new ISA is introduced. With fixed coefficients 0,100,320,330,500,900,0,1,
every intermediate absolute sum is at most 70483968 for initialized signed16
lanes. This all-input mathematical bound is separate from finite execution.
The original source proof remains frozen; an additive readback corrects its
signed `__v4si` declaration citation to emmintrin.h:43 (line44 is unsigned).
Native bytes change. Static readback ofthe exact selected native retains an
XMM `vpmaddwd` in actual P; this is no performance or complete-core claim.

The existing signed8 fixture was minimally adapted to the current shipping
names and global history. Only U's definition name is changed (full inverse),
retaining the actual old/new bodies. Each variant passed fatal GCC13 -O1
ASan/UBSan execution of 80 widened one-term basis cases at INT16_MIN,-1,0,1,
INT16_MAX and 8 mixed-extrema cases over both sides. Zero-weight lanes 0/6 and
read-only Board behavior were checked. These synthetic vectors are private
evaluator inputs, not reachable-mailbox assertions. The existing independent
mailbox/hash/old16→signed8 rebuild checked 2674 states, 154 legal children,
10816 ordering comparisons, and 1464 actual P→U calls,including both-color
depth2 search. Both variants' complete stdout matched; SAN 2 compile/2 run
commands exited 0 with empty stderr, reaped groups absent and active handles 0.
Those finite checks do not replace the mathematical bound or prove all
arithmetic, concurrency, game strength or performance.

One ordinary `build.py --dev` invocation reproduced the new source/native/
bootstrap/complete tuple twice and the unchanged DEV source/full native twice.
One unchanged selected verifier passed quit/EOF 2 sessions and 8 legal GO, exact
restored native, 3 startup TIDs each, stdio-only FDs and private-path/helper/
reader physical exit. All outer commands exited 0, were reaped and left groups
absent, with no timeout, retry or forced cleanup. The earlier firstcost is
reused as firstcost only; it was not rerun for promotion.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping source | 9848 | `a661656a482be3ee8383443925c7c36114ce802e9d06ffed59f5479f7ccd37b9` |
| Native | 26304 | `b2d04d7c74ac3801a61f5f5b967311ceac45cad4ad2a878fbbb0338eddd3502d` |
| Bootstrap | 10897 | `992c6a573ddc40a08a2d64c7468dc5912e6bec02a6757d392326d5493f2628aa` |
| Complete | 4874 | `f6084a865f399d55179ab02a347c94609787eb02cedf79674ee0d8748ab0c290` |

Actual outputs: `/home/stemxstudio/rove4k-c-simd-lane-sum-promotion-20261022/normal/build`.
Focused receipt `14eb604d804fe97cec5606f5c66abc892979cfc951d4f0c11e2e0394e76dbc78`;
build `e27d7401fdd0caae2889a4ac10b86b5780e08e689dca9bb8c3756a942a3fecba`;
runtime `f3abe20bbb34a1cdd8000be7ddd713afaf4e349ab26d7060c1dabd1aad62d81f`;
producing recipe `639855a4ccb3248a4053a67795a7b952d907d47f2032fbd5d75b67a12ec2809a`.
Final recipe/README only annotate receipts after the producing revision.
No new fixture framework, firstcost/codec/ISA search, fresh archive, games,
performance, training or AWS execution was added.

# Historical C: shared73-byte header — 2026-10-22

The selected complete file is **4880 B**, four bytes below C4884 and784 B
above4096. Its9882 B C,26304 B native,10931 B bootstrap and exact DEV tuple
remain unchanged. Only the77-byte shell header is replaced with the pinned
shared `source_package.XZ_STDIN_HEADER` (73 B), after the existing legacy
marker/input validation. Every compressed payload byte is preserved, and the
existing ALONE encoder/compiler/profile remains unchanged.

The three-line header uses `tail -n+4` and stdin `xz -d`; decoder failure still
exits before Python, with unchanged command-substitution newline behavior,
argv and exec. The local77-byte launcher remains for legacy consumers. Exact
old/new bounded ALONE decoding recovers the same bootstrap, allowing reuse of
its source/argv/core proofs by identity. This is packaging, not new C or SIMD
compression. Whole SHA:
`660ce07e172134d1b1af3107dccfb4d1cdf4c858449f3b784d76b6a11c0d5e4e`.
One ordinary --dev call reproduced shipping and the unchanged DEV tuple
twice. Its complete outputs equal the exact header-only substitution, with
the original compressed payload intact. One unchanged selected verifier
passed quit/EOF2 sessions8 legal GO, exact restored native, persistent3
startup TIDs, private-path/helper/readers cleanup and physical exit0. All
outer commands exited0, were reaped and left their groups absent. No
runtime failure or retry occurred. Generic signal/descendant/fresh/core/
game/strength/many-core coverage is not added by this packaging change.

Build receipt `633d67efb28eb3c0c36c689451938cca785027a780efd1a353df9f64b3b05904`;
runtime `4992783c8e446ffeb3a9ea10246c665d734bfa09189c9a8bc1c3bcf8ff044fa8`;
producing recipe `c5980f1833193cdffbaaec0862ccdee4745709f19ec604e7c46b345064255baf`.
Producing closure 40 ordinary files. Final recipe/README are receipt-only
annotations; source-producing code and expected artifact bytes are unchanged.

# Historical C capture-only Move metadata — 2026-10-22

The ordinary builder now reproduces **9882 B** shipping C, **26304 B** native
and **4884 B** complete file. Against the selected4897 B predecessor this saves
76 B of source,32 B of native and13 B of the whole file. It is still788 B above
4096. The fixed compiler/profile,128-bit SIMD evaluator,Board,learners,rules,
pool,77-byte launcher and ALONE9e-lc2-nice64 recipe are retained.

The shipping-only late `shipping_capture.py` applies8 exact edits with9
protected gaps and full inverse. Actual gen carries capture-only metadata in
reserved source-square bit3; FROM119 strips it. TO/PROMO and17-bit TT move width
stay the same. Quiet promotions retain tag0 and separate PROMO handling,
including their old quiet noise tier. Raw Move and TT payload bytes change;
old/new natives or in-process TT state must never mix. Canonical/DEV remain the
old untagged reference domain. Qualification compares decoded logical moves
and normalizes only the new bit3 in best/publishedbest/TT payload; every other
TT bit and the full64-bit key are compared exactly.

One fatal ASan/UBSan compile/run passed the existing51 actual-source
search/history cases. The affected-move bridge additionally passed9 bounded
roots using actual gen,make,text,nullable parse and TT probe. It independently
checked mailbox capture classification,ordered moves,both colors of EP and
quiet/capture N/B/R/Q promotion,all four castle wings,king-capture make/parse
rejection,parent preservation and complete logical child state. This is the
C-specific changed-representation proof; it is not new generic core or pool
acceptance. Focused result SHA-256:
`9485f5c6572cd975b8cf07f3ff80dfeb1e116c14576b16bab9ef1d69dc5d080b`;
focused final index `023f106532478d7819f2386bb7da95c040eb775cd9971445c780a60e04f45168`.

One ordinary --dev builder reproduced shipping twice and exact old DEV source
and full native twice. The unchanged selected verifier completed quit/EOF in
two sessions with eight legal GO results,three startup TIDs each,exact restored
native image,stdio-only FDs and process/reader/private-path exit. Known outer
groups and observed native TIDs were independently absent after completion;
owned handles0,no forced cleanup. Build receipt SHA-256:
`1a5cf087a64ed27d598dd8e46fc93a5fe6d65f4f516e852155bfedbb8226d765`;
runtime `2b8f31e3bc4679a53423cfc4f87f5ba3460efe7520bddbc01abc7a0f4c912029`;
normal final index `b5c8328cce75c499f11f1700631ea0a8baf319f416f139097cb017947e92cefe`.
Producing recipe `8bc1d6de41c827b646704a586abd3465b95485705c8c6cdf24cc83c9a091699a`
and the four-file producing freeze are preserved externally before this
annotation-only completion. Helper/build bytes are unchanged by the overlay.

The original first supervisor failed before compiler/codec/decoder because an
external composite source index was serialized as a float. That failure is
preserved. Only external index types/owned paths were repaired before the one
actual first-cost compile/encode,Python2/CLI2 strict restorations and full EOF
checks. First-cost index `f91ef90a980e53d4b3f51e01632e49dbd8300f56cc489e782346540e53b1633f`;
cost `129fbed02327a7d6ae39287bed0e268c928b05ffb626be522a632235a694d7ef`.

Cancellation causality remains unproven. The unchanged compile helper has no
separate compiler-descendant lifetime record. No DEV engine runtime,fresh
archive,playing strength,performance or peak-RAM campaign was run. The older
sections below record predecessor stages and their separate evidence domains.

# Maintained C: derive fallback only when the completed result needs it — 2026-10-21

The fixed first-cost candidate is **4897 B**, compact C **9958 B**: source34B
and whole11B below the preceding4908B entry, still801B above4096. The ordinary
shipping pipeline now applies the shared `shipping_lazy_fallback.py` after every
existing source pass. It removes the stored fallback and the eager GO query.
The final worker derives the first legal move from the unchanged root only when
the selected completed result has no best move. Exact three-region replay,
input/output pins, inverse and protected gaps admit this fixed source alone.
Canonical/DEV, all search/model/SIMD features, compiler/profile/template,
prefix77 and ALONE9e-lc2-nice64 remain unchanged.

Worker selection still uses greatest completed depth and retains worker0 on
ties. The existing nullable legal query is reused; terminal roots still format
zero as `0000`. The query writes caller scratch only. Source ownership remains
the existing last-worker callback under the mutex after all `think` calls have
returned, followed by result flush and completion broadcast. Main changes the
root only after its existing wait returns; quit/EOF and joins retain that order.
These are source/lifetime relations, not a new pool, SMP or cancellation proof.

Work moves from before worker publication to the conditional result path. Since
the deadline is set before the old eager query, exact work duration, nodes,
search timing and best-move bytes are not equivalence claims. The extra query
runs after recursive search and `think` have returned; actual worker stack peak
for this result path remains unmeasured. No C component execution or playing
strength/performance result is claimed for this promotion.

The single fixed compile/encode first-cost receipt is
`b9613dd993cfab433a479a43b80d8f1b4457f9cbe6147418661f5ca876d2276a`;
plan `f306a0b5e77ba5237e7e538697a3ed986d3bb80a5a51b0876ddc9dfb528dbc3a`.
That first-cost phase strictly restored baseline/candidate without running
either bootstrap or engine. The new native identity is explicit. One ordinary
--dev builder has now reproduced shipping twice and exact old DEV source/ELF
twice. The unchanged selected verifier passed quit/EOF in two sessions with
eight GO results, three startup TIDs each, exact restored image and physical
process/reader/private-path exit. Build receipt SHA-256:
`068b6284d7fe315ac3bf9f76a28ff407dfa3883259c589b65183a765d3724605`;
runtime `aac374531728fca975b466d242ad61ee0709ad23fae9d13ded85bc665d30154d`.
Cancellation causality remains unproven; stack peak, clock equivalence,
many-core and strength remain unmeasured. Earlier normal receipts below keep
their own predecessor images.

| First-cost form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping source | 9958 | `1c7d102dfc3eda05cad0c7f2032537b67633f364341037ff57237a3600a209ad` |
| Native | 26336 | `9e2c649a2a459551d00a9622d005612b8c4cbd7bab877428f86dc6c906bbfa6e` |
| Bootstrap | 11007 | `b08f48163f7200210635460870293be40e252d15ae6a8c347bd38a4599f93451` |
| Complete | 4897 | `eea215b26a4ad623756a92cf0bf68eb3c01eb57d7ca33e6016b3d8738dc6fddc` |

Before/producing source records are preserved outside Git in the common lazy
fallback promotion evidence. Reports and measured artifacts are metadata only,
never helper inputs. The recipe-driven closure discovers the new helper through
`helper_sha256`; no fresh/archive execution is implied by this registration.

# Maintained C: derive history depth from the immutable job — 2026-10-21

Complete file **4908 B**, compact C **9992 B**: source40B and whole16B below
the preceding4924B entry, still812B above4096. The pure shipping-only helper
`shipping_history_depth.py` runs after `shipping_search_context.py`. It removes
the private cursor and derives L=game_length+caller ply, keeps the same parity
and reversible-window key scan, writes the identical child index, and removes
the balanced pop/reset. Five exact spans, all gaps, full inverse and input/output
pins admit only the qualified source. Worker layout and native identity change;
old native/layout byte equality is not claimed. Canonical/DEV and SIMD/model,
compiler/profile/template/prefix77/ALONE9e-lc2-nice64 remain unchanged.

One fatal ASan/UBSan compile/run compared51 actual old/new SIMD search pairs:
the original31 searches and22 special children with persistent learner seed,
plus history/parity/half99-100/claim/TT/terminal/stop/cap boundary adapters. It
compares typed Worker fields, all keys and three learners, Board/vector state,
full TT key/data and clear locks, score/best/nodes and old cursor restoration.
Production root lengths1/4096 and maximum child index4222 pass. Private nonzero
ply adapters explicitly set base=L-ply; negative private bases do not expand
the public history domain. The unchanged learner exhaustive loop was not rerun.
The four recursive call groups retain the same n+1 push/pop relation by source
induction. Runtime PVS retry coverage is unmeasured; node counts are not witnesses.
Focused receipt SHA-256: `7147f77ba80f11c19ba3b45af92050fc9e0c8c69d355ee470e3be79c3d8dd8b2`.

One ordinary --dev builder reproduced the exact shipping tuple twice and
unchanged DEV source/native twice. One unchanged selected verifier passed two
quit/EOF sessions and8 legal GO results, exact new native image,3 startup TIDs,
private-path/descriptor cleanup and physical process/reader exit. Cancellation
causality remains unproven. The helper is registered in the recipe-driven37-file
source closure/fresh discovery; fresh/archive execution was not repeated.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping source | 9992 | `c7b8eeb2488e4ec0b9ebbdd721db311397dc5b29abc91dcb1f153046ceb2bebd` |
| Native | 26368 | `09edf1e3bb108a6d3d169e3c73d1eaa61b268771f4fd23c8090f6ea30a988057` |
| Bootstrap | 11041 | `82fb98e44a115564956ff3f909aee639afa84a1c91ae9971a5a7a3186efd1aca` |
| Complete | 4908 | `3ddbc4f1aada92762f27bb0429f97e5f94d2922a1c35b42f43d067ee7d14aa7b` |

Build receipt SHA-256: `0597006e8aa6a7ffe7b34390000ee0c4de4792918699c834a6a9740ec6e20e49`.
Runtime receipt SHA-256: `982a77c6e424d63a9d4fd693b4a2998c7a293cbfcb3fc3b1a6a512a508737294`.
Actual build is `/home/stemxstudio/rove4k-c-history-depth-normal-20261021-v2/build`;
its exact producing recipea31ab5d4 remains in inputs. Final recipe/README only
close result metadata. A first external parent preflight used A's source-plan
key instead of C's and stopped before builder/verifier; the original failure is
preserved. One lookup key was corrected before the sole actual normal sequence.
No candidate or expected output was changed in response. Source/cost/focused/
before/producing evidence remains outside Git; older sections retain their
historical identities. No playing-strength or performance claim is made.

# Maintained C: compact environment snapshot — 2026-10-21

Complete file **4924 B**, compact C **10032 B**. The single
env constructor expression saves6 template bytes and 10 actual whole-file
bytes against the preceding 4934 B entry. `dict(os.environ,TMPDIR=d)`
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

Build receipt SHA-256: `274ed41a1c050b2f7a9cc2aa3b2cb59b99c5ef908103edbf2cdcf6340f28f285`.
Runtime receipt SHA-256: `e140e3c87df32f63e4b1e16e7d3fa8ed642568b7bdaf756394b1b81c221f8800`.
Current whole SHA-256: `508b11f9f808af648f3c7a951d9d7eb347b2eb1b6a90006deacfc50f5c38c9c3`.

The producing recipes, actual receipts and pre-annotation sources remain in
`rove4k-bootstrap-env-normal-20261021-evidence`; original costs and source
forms are preserved in the source/optional-cost evidence folders. Historical
sections below retain their own images and scope.

# Maintained C: child continuation slot and positive cutoff learner — 2026-10-21

Complete file **4934 B**, compact C **10032 B**. The fixed shipping-only
composition removes40 source bytes and18 whole bytes from the preceding
4952 B entry. Search passes the already-made child's signed piece slot to
its four recursive calls and neutral6 at the root; quiet cutoff continuation
learning consumes the same column. The two existing learner calls pass only
positive depth-square bonuses, so their redundant abs is omitted. Canonical
and DEV keep the previous APIs and general learner expression.

A fixed new-source comparison measured list4934 versus split4935 with one
native compile and the same C compiler/profile/ALONE64 codec. The existing
list template remains selected. The historical old-source split+1 B loss is
preserved separately; no byte deltas were added to predict this result.

Focused fatal ASan/UBSan compares31 actual old/new search pairs, including22
special-child adapters and128 legal child observations. Scores, best moves,
full worker/learner state and TT bytes agree. Both EP colors, all four castle
wings and all four promotions in both colors are observed. It exhausts
8,257,536 actual positive depth-square/int16 cell combinations. The component
fixture never starts production main/workers; special children are direct
ply0 caller adapters. Unchanged board/generator/make/SIMD/input/pool bodies
are protected by exact source gaps, with no new whole-core or strength claim.
Focused receipt SHA-256:
`fff573aab97d612de83984bc29410ab29f9c396f91aec03e9153c754c141a0be`.

The ordinary builder reproduces shipping and unchanged DEV twice. The
unchanged selected verifier passes two actual quit/EOF sessions and8 legal
GO results, exact native restoration, stable3 startup TIDs, private-path
cleanup and physical exit. This is local2-worker/TT18 evidence. Final target
resources, many-core behavior and strength remain open. Build receipt SHA-256:
`949ba4a6c9ed86354ec7ba6a9b50084a42fb34fc00df90f70ac46da1ec53a31e`.
Selected runtime receipt SHA-256:
`0108890c067ff67c95c81205ee57951f921e4c311664fed9946d5e63598c153e`.

Current source SHA-256: `7612b83cb6a274c9b67c5217aa9c983c6271378df234b6d853e8985d97e46b12`.
Current native SHA-256: `54d60a5d673a3315a120219fff89285570040a693f957244b83979a45c9b2639`.
Current whole SHA-256: `27e805397c36fa56994e822549cbb6bbce188f7ef82310663076620fb62011a6`.

The producing recipe is preserved by the build; final recipe annotations add
these result references without changing producer decisions or inputs. Older
sections retain their original checkpoint identities.

# Maintained C: compact clock presence — 2026-10-21

Complete file **4952 B**, compact C **10072 B**.
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

Current source SHA-256: `fc2209ce96c714d3828790cae882051f8cbf8980f4e874381954280f0c9d17a3`.
Current whole SHA-256: `824609ce753cb0e18d51db0532c0139e2a134113b7731393182bee4b537d78d0`.

Local two-worker/TT18 checks do not establish final target resources,
many-core behavior or strength. The full A–F goal and compression beyond
size passage remain active. Older sections retain their checkpoint identities.

# Maintained C: smaller plain-Popen cleanup guard — 2026-10-21

Whole **4954 B**. The current template/script loses12 raw bytes
by testing the fixed plain Popen/None value directly. Poll, cleanup, signal mask,
compiler argv/C input, private path, descriptor exec and physical lifetime
operations remain unchanged. C source/native are entire-byte unchanged.

All seven selections regenerate --dev twice and pass unchanged actual selected
quit/EOF verification. This is local2-worker/TT18 evidence, with no new general
descendant cleanup, startup-fault or strength guarantee. Normal summary SHA-256:
`90e45a020a55ef5a3ff6af78dfa42908eb8625395fe5c991d860bde8d34b2ff6`.

Current source SHA-256: `ed5b5fba543a7ab3a208af466e14744d0339447b0b812448a5092a068cd9715b`.
Current whole SHA-256: `f0ee42134a2d8604a3f363b0f9e9b350bf56f3de89ba166fadb35a0ce4f6b545`.

Older sections retain their original checkpoint identities.

# Maintained C: final literal/poll compaction — 2026-10-21

Current whole **4960 B**, source **10084 B**.
Fixed LP64 large mixer hex literal wrappers omitted; values/types and the entire native image remain unchanged.
All full family features and DEV bypass remain. Final transforms operate on
separate reference copies where needed; raw policy preimages stay unchanged.

The ordinary --dev builder reproduces shipping and full DEV twice, and unchanged
selected verifiers pass actual quit/EOF, restoration, legal finite GO and physical
exit. Local2-worker/TT18 only; final resources and strength remain open. Final
normal summary SHA-256:
`af00002687cf6ed0d84f2e85f21169d381bb1cd8721005c05cc87a4fabe2bb96`.

Current source SHA-256: `ed5b5fba543a7ab3a208af466e14744d0339447b0b812448a5092a068cd9715b`.
Current whole SHA-256: `342fb248af88d22b754b7f7f21ddac68826cdea24a3cd053a3674a5111f81062`.

Older sections retain their original checkpoint identities.

# Maintained C: literal include forms — 2026-10-21

Whole **4969→4968 B**, source **10114 B**.
Only the fixed literal angle-header gap is removed, after all prior shipping
stages. Every other source byte and directive boundary is preserved. The
entire native image equals the preceding qualified image. DEV bypasses this
pass; F's raw policy preimages are retained through separate reference copies.

Ordinary --dev reproduces shipping/DEV twice and unchanged selected verifiers
pass actual quit/EOF, restoration, finite clocks and physical exit. This is
local2-worker/TT18 evidence; no new functional or strength run is claimed.
Normal summary SHA-256:
`b6be10f54e68ea2c381ed85a5a8fce47253825bb5bafbd1639b5b9802e9c5137`.

Current source SHA-256: `fde89cdc49ef55d075343cd2480a5e65a02d18e94884271890b579ae60e93304`.
Current whole SHA-256: `19b88253046c526cba21053f5868012ee06de18d256912158a0a85a7523b40b0`.

Older sections retain their original checkpoint identities.

# Maintained C: startup TT source compaction — 2026-10-21

Whole **4976→4969 B**, source **10151→10123 B**, gap **873 B**. The
late shipping pass omits plain key/data stores covered by checked calloc before
all threads/input/TT use, while explicitly clearing every atomic flag. DEV's
general reset remains. Full signed-net/SIMD, search, TT, learners and SMP stay.
Current C already reset best inside think, so no extra reset saving is claimed.

The ordinary --dev builder reproduces shipping and DEV twice; its unchanged
selected verifier passes actual quit/EOF sessions, exact restoration, legal
finite clocks, stable3 TIDs and physical exit. Local2-worker/TT18 only; final
resources and strength remain open. Normal summary SHA-256:
`4b7b98ecc6cdb94d11a112e307d388633a03fb061d2000b08167b85ac70c72ca`.

Current source SHA-256: `0eeee8fd2c976cd5a0221365e1765ad01714c68609183381ea19eb8f4b3118ff`.
Current whole SHA-256: `e723a31bef3d0ab47d22bc50c5e22e2c0cd54f8b56f05776c7ab10bec2c85f96`.

Older sections retain their original checkpoint identities.

# Maintained C: integer source compression — 2026-10-21

The late fixed integer pass uses the existing unsigned64 alias and high-bit
decimal bound, retaining digit/end-pointer checks, clock consumption and all
budget clamps. The unused final limits header is removed except for C,
which has a later intrinsic include. Full/material F also omit two fixed
positive TT18 casts. Actual composed costs are used, not added deltas.

The entire native remains byte-identical to the previous maintained image;
no model, learner, search, rule, TT or worker feature is removed.

| Policy | Previous whole | Current whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| C | 4992 | **4976** | 16 | 880 |

Each normal --dev build reproduces shipping and full-reference DEV twice.
The unchanged selected verifier passes new actual quit/EOF wrappers, exact
restored native, stable3 TIDs, legal finite GO, private-path/helper absence,
closing result, reader EOF and physical exit. Normal summary SHA-256:
`1de4261cbd87622c9326fe8c72137b0d96148fb4e1514b2c81e8dbda4031a2a5`.
The local2-worker/TT18 profile does not accept final resources or strength.

| Policy | Source bytes | Native bytes | Whole SHA-256 |
|---|---:|---:|---|
| C | 10151 | 26368 | `c3f1499270040319d71e6e775699358b2c25c50215f91793cf8c5aff0f97d06e` |

Older sections retain their original checkpoint identities.

# Maintained C: shared material-state compression — 2026-10-21

A shared late source pass replaces three material-classification accumulators
with one signed state, preserving the existing limited policy. Bare kings
and a single minor remain dead; KNN stays live. Bishop-only minor sets are
dead when confined to one square color. Full models/search/TT/
learning/rules/input/pool remain outside the one-function edit. This is not
a general theoretical dead-position oracle. Raw source grows18B per policy,
while actual complete-file cost decreases; independent deltas are not added.

| Policy | Previous whole | Current whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| C | 5001 | **4992** | 9 | 896 |

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
| C | 10174 | 26368 | `07341bf4431dc2a6d412045377784bb28548baee5cd6142093a01c6d0b9d826b` |

Older sections retain their original checkpoint identities.

# Maintained C: further full-source compression — 2026-10-21

The full/default policy now shares the main-owned tokenizer. Its existing
clock-key consumption and transactional position replay remain. Full F also
combines the two exclusive mate-score adjustment branches. Full search,
models, learning, full-bound full-key TT and persistent SMP are retained.

| Policy | Previous whole | Current whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| C full/default | 5016 | **5001** | 15 | 905 |

Source10156B, native26368B; whole SHA-256
`8ce2685230f164cdc76059834fb116c8f5dce36ab3c8fd1c57e9d6ef9c11d28c`.
The ordinary --dev producer reproduces shipping/DEV twice. The unchanged
selected verifier runs the new actual file through quit/EOF, exact restored
native, stable3 TIDs, legal GO, private-path/helper absence and physical exit.
The local two-worker TT18 profile does not establish tournament strength.
Normal summary SHA:7820f2fe387eee0c1c42df6238b497c2d79efc648d0c6d0fac9aae1d8c7b27b6.
Earlier sections below retain their original checkpoint identities.

# Maintained C: qualified source refinements — 2026-10-21

Only the generator-admitted valid-0x88 promotion predicate is changed here. Actual signed eight-lane SIMD evaluation, full search, learners, TT and runtime retain their prior policy.

| Policy | Previous whole | Current whole | Saved | Above 4096 |
|---|---:|---:|---:|---:|
| C | 5020 | **5016** | 4 | 920 |

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
| C | 10260 | 26336 | `f9c113395db8327124197ef0a7b2aabdabf717d569c78ebe51da13a85fbb1718` |

Normal summary SHA-256:
`cc82bacb31cfd8fb020fa375a3a1d1b3ece7ac2991dc7ebcf2c7ed772e3d230e`.
This frozen summary binds producing inputs before subsequent receipt-only
recipe annotations. Older sections below retain their original identities.

# Maintained C: shared final shipping reductions

The final `engines/scripts/shipping_common.py` pass removes the sole unused
empty `TINY_H` definition after all existing family stages. A/C/E also omit
two redundant fixed-TT18 casts. ASCII source uses a raw bytes literal in the
unchanged bootstrap; every previous non-ASCII/CR/NUL/quote/backslash fallback
and the historical `pack_stream.py` API remain unchanged.

| Policy | Previous whole | Current whole | Saved | Above 4096 |
|---|---:|---:|---:|---:|
| C | 5036 | **5020** | 16 | 924 |

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
| C | 10273 | 26336 | 11340 | `ee8265985e4330ae0ae90042ac9fa5301c355edf6b865ce7341790c236ee47df` |

Exact source/bootstrap/native hashes remain in `recipe.json`. External normal
summary SHA-256: `4c2bc987c0947387ebe688ac76c7b91f41d1458149278e490638fb1428f7469f`.
Generated artifacts and reports remain outside Git. The following sections
describe earlier checkpoints and retain their original validation scope.

## Previous: Maintained minimal C entry

The selected complete launcher is **5,036 bytes**, 42 below its
preceding complete file and **940 bytes above4,096**. The final ordinary
`shipping_global_names.py` follows the type-token stage. It shortens 10 owned
global functions at 37 physical declaration/reference spans, source
10445->10305. No local names or model/search logic change.

| Selected artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C |10305|`597b74bd71a843b58be58944c6763d09a31159caaf571c9dc80d39253beadbab`|
| Full native |26336|`afa5b0bbc81a232d6c1600f486438235d97655e966f8ac6d50f4f6e34abacad4`|
| Decoded bootstrap |11380|`8e37663b5803debf4cf68cce1f2517b1f0295a3362dc61e5480ea5a549bdd97f`|
| Complete launcher |5036|`18caf239012ad04552def951b2e77a72f2ac4f486996b28a8fbe268857d19c65`|

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

Source proposal SHAf884a53e504ba9b2e58bb64149f879cb5b2c0048d9176e75b496de2905780722;
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
Build SHA65ab204335cee16df14c221b67c8bf24bce4f450c0fb63d6427cfcd505503375;
runtime SHA9e5d89fdbc236cc5f69388fd42ec6baaae4a970291876deb617d6ffa5226e96e;
readback SHA6d6ed9b8c66432d460a00ad7c8100d042abd1b1c0dd8665d0e03263e84dafe42.
Producing source SHAbba6beb89d3cd15cd293140ecc7efb9cd9645fec873fdcba7638bc730b5f400a;
producing recipe SHA3e1786eee30cc9261e1230603b54e97bc935d3dd1eedc1897dadf9e7130d9188.
Only README/recipe completion metadata changed after execution; other
25 source paths and all helper/expected/compiler/profile/codec
remain producing bytes. Unchanged fresh.py would discover27 ordinary
paths; no fresh extraction ran. Cancellation causality and the unchanged
builder's separate compiler-descendant lifetime proof remain unproven.
No DEV engine, new core matrix, games, benchmark, training or negative campaign
was added. Prior native/body proofs retain their exact source/static reuse
scope, and prior wrapper receipts are not relabeled as these new executions.

# Historical C5078 type-token stage

The selected complete launcher is **5078 bytes**, 14 below C5092 and **982 bytes above4,096**. Shipping C is 10445 bytes (source delta -211). Final shipping-only `shipping_types.py` owns one fixed type map `{'uint64_t': 'M', 'Move': 'T'}` plus a19-byte uint64_t alias definition. The existing Move typedef is renamed with its type uses and exactly3 MOVE casts; int16_t and private Entry zb remain protected. All full native bytes match the actual preceding native, without a metadata exception.

The ordinary family helper pins the canonical readable, complete final-stage preimage/result, type-role offsets/counts, source/directive alias freshness, sole MOVE line, exact inverse and each unchanged gap. It reads no experiment, report, old artifact, AST or network input. Its pinned existing lexer is frozen before import. Existing canonical/map/core/input and family-specific stages remain ahead of the final type stage; DEV bypasses it and retains its prior diagnostic model scope. Only C admits the fixed later immintrin header at old offset4060; no header is moved and no generic exception is opened. Actual header conflicts must fail the fixed full-native gate.

Unchanged fresh.py dynamically includes the new helper, yielding 26 unique ordinary source paths. Canonical/DEV/verify/fresh/shared bodies, compiler/resources/bootstrap/77-byte prefix and per-family ALONE settings remain unchanged. The whole 14-byte gain is separate from the larger raw source reduction.

| Current artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 10445 | `d424d14f5cb16d7e6a39383821a70ef96cd6c69bcc99c5a948dc4f5a907546d4` |
| Native ELF | 26376 | `4ffb9c371eb7c0949f34ed637350ff3be9c7164890d1784c12e3cd3d93912691` |
| Complete launcher | 5078 | `60a5822c4cb7851e30bd147b0d7b106a38304a60c4ab2c9f9e7c6567e520c31e` |

The sole normal builder invocation passed shipping C/native/bootstrap/whole twice and the prior DEV C/native tuple twice, retaining its historical model scope. The unchanged selected verifier then passed its sole quit/EOF invocation: two sessions/eight legal GO epochs, exact restored native image, three stable startup TIDs each, absent private restoration paths/helper children, one closing result, completed readers and physical exit0. Both bounded command groups are terminal0 and absent, with no retry or forced cleanup. Prior sources and raw binary controls were preserved outside Git; native/whole pins are never newline-normalized. Original preflight failures remain preserved separately; approved correction did not change any candidate. No new core fixture, fresh archive extraction, game, benchmark or alias/codec search is part of normal promotion. Historical diagnostic/core evidence is reused by exact native identity within its existing scope; cancellation causality and many-core performance remain unproven.

Normal build receipt: `fe1ddd10928fd10f7c5b2f10e00db89e5794a32a73693576c814e3e2d17bfdf8`. Normal selected runtime receipt: `26fc3930595ff4c5d9b5d370a71e5201db862a85d09af4c19d4c35c84377a29a`. Producing recipe: `5a34cba163890fcfaee7aec99a90acafa41beb8d64b1e35747cc1f11fad6a302`; producing ordinary-source freeze: `6a66bef2bd31d9982575ee13d35e7ff66c2179fb01129b9b0f3d8d0ce9887b0e`. Only README/recipe completion metadata changed after execution; all helper/build/compiler/expected/codec bytes remain producing inputs. Git/CI and whole-project acceptance are separate parent work.

# Historical C5092 stage

The current selected complete file is **5092B**,60B below previous5152 and
**996B above4096**. Shipping source10656/58e71a9c uses a private signed-net
8-lane vector; ordinary pinned sources regenerate native, bootstrap and wrapper.
Canonical engine.c and its PSQT/gather DEV reference remain unchanged.

The new ordinary shipping_signed_vector.py is last, after shipping_incremental.
It admits only exact10803/8fd326 source and produces exact10656/58e71a9c through
five literal regions with full input/output, inverse and protected-complement
guards. All previous helper guards are preserved; DEV bypasses the new stage.
Only ordinary local source is consumed. `fresh.py` remains unchanged and its
recipe-discovered closure is25files (LOCAL9+helpers14+tests2).

The eight signed16 lanes are zero padding, six white-minus-black PNBRQK counts,
and signed positional residual. Coefficients [0,100,320,330,500,900,0,1] retain
all old material values. Direct piece indexing preserves value(0,q)==0; king
material is0 and its position score remains in residual. Count<=16 and residual
<=2016 are safe; full dot equals the original scalar HCE. Real H/K deltas, zero
start and Board copies maintain this state through capture/EP/castling/promotions.
EP attack-only stale scratch remains confined to attacked/W, as source-reviewed
and dynamically checked with poison and original-mailbox comparisons.

U now consumes actual128-bit SIMD: productionP disassembly loads Board offset
0x80 into XMM, multiplies via vpmaddwd and reduces through vphaddd twice. The
intrinsic minimum is SSE2+SSSE3. The compiler remains the fixed **-mavx2** target,
and this is not a256-bit AVX2 leaf claim or a lower-ISA deployment qualification.
The fixed profile is workers2/TT18/PLY128; compiler/bootstrap/prefix77 and fixed
ALONE9e/lc2lp0pb0/BT4/64MiB/nice64 settings are unchanged.

```sh
python3 -B engines/compact/tiny-entry-c/build.py --out /absolute/new/C-build --dev
python3 -B engines/compact/tiny-entry-c/verify.py --build /absolute/C-build --out /absolute/new/C-runtime
```

One ASan+UBSan fixture passed actualH/K/U and independent mailbox/hash/scalar/
old16-to-signed8 algebra, all8lane perturbations including zero king/padding,
154legalchildren with both-color specialmoves,10816 ordering comparisons and
actualP searches in both colors. Scores0, best4742/10998 and nodes150/104 exactly
match the pinned old actualDEV receipt; that reference was reused, not rerun.
Actual Board is200->184B, P fixed allocation4416->4392B, pushes8->6 and prior
32-byte dynamic alignment is absent. No previous changed-layout proof is inherited.
Independent source/fixture read review was CLEAR. These facts do not measure speed.

Firstcost pins are source10656/58e71a9c, native26376/4ffb9c37 (same length, new
identity), bootstrap11731/9b664514 and complete5092/175b73a5. Expected identities
were set explicitly before normal execution. One normal builder passed two
shipping plus two unchanged DEV reproductions. The unchanged selected verifier
passed two quit/EOF sessions and eight legal GO, exact new native image, three
startup TIDs each, private-path/descriptor cleanup and physical process/readers
exit. Cancellation causality and playing strength/performance remain unproven.
Old normal24 closure/archive and actual controls were preserved outside Git
before edits. No fresh, games, performance, training or AWS ran for promotion.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping source | 10656 | `58e71a9c05cb48e4d1a8de83cd833981f64165344f53c41d0c39542fdfb1ae64` |
| Native | 26376 | `4ffb9c371eb7c0949f34ed637350ff3be9c7164890d1784c12e3cd3d93912691` |
| Bootstrap | 11731 | `9b6645146ca734dc7133cc6f50131f8a90c582246f7ae4b9ada75c24397c9451` |
| Complete | 5092 | `175b73a5a720e2197c3842a8e61ed0a335b927491e43d00e60e42cc8509836b4` |

Normal build receipt `12c85436abbe41f246d916c4b91a0580c6435ee5b349ae44f721274a5a05e357`
is /home/stemxstudio/rove4k-c-signed-vector-normal-20261021/build.json.
Runtime receipt `d18ee2e01c7d38163599784e35ec8736530bd5d6ec011db0e60c98f5aa30aacd`
is /home/stemxstudio/rove4k-c-signed-vector-normal-runtime-20261021/runtime.json.
Exact producing recipe7226874f is preserved in build inputs; final recipe
only closes result metadata. No expected output was updated automatically.

## Historical C16 incremental records

The following is historical5152B/16lane shipping and earlier ancestry. Current
128-bit/8lane identity and its qualification are stated above.

# Historical maintained C16 entry

The selected complete shipping file is **5,152 B**, 7 B below the previous 5,159 B and **1,056 B above 4,096**. Ordinary pinned source inputs regenerate C, native ELF, bootstrap and wrapper. Reports are qualification metadata, never generation inputs.

`engine.c` and DEV remain the unchanged older PSQT/gather reference, including their previous source/full-native identities. They do not by themselves qualify the new shipping Board state. Shipping generation applies existing alpha/scope/core/SIMD/input/material stages, then the new ordinary `shipping_incremental.py` closing stage.

The fixed local profile is two search workers plus one controller, TT18, PLY128, Linux x86-64 AVX2. Compiler, template and prefix77 remain:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -mavx2 -DDEV=0 -x c - -o x
```

```sh
python3 -B engines/compact/tiny-entry-c/build.py --out /absolute/new/C-build --dev
python3 -B engines/compact/tiny-entry-c/verify.py --build /absolute/C-build --out /absolute/new/C-runtime
```

A builder call reproduces shipping twice and optional DEV twice. The unchanged verifier uses quit and EOF wrapper sessions with eight legal GO results. The ordinary closure is 24 files (LOCAL9 + helpers13 + tests2); `fresh.py` discovers the extra helper through the recipe. No archive/fresh execution is implied by a direct build.

The closing helper admits only exact 10831/207b07 material-vector shipping and produces exact 10803/8fd326 shipping using four unique literal regions, full input/output pins, inverse and protected-complement equality. It takes only source bytes. No experiment, receipt, artifact or AST/name allocation is a generation dependency. All earlier helper pins and canonical/DEV admissions remain unchanged; DEV requires the new stage metadata to stay None.

Private Board `x[16]` now holds two colors of six kind counts, own-side positional residual and zero. Existing nonzero H/K calls remove the old contribution and add the new one, retaining the exact hash return. `U` loads this field through the original AVX2 signed16 multiply-add and both-half i32 reduction. The shared material coefficients, value/capture ordering, side multiplication, current clamp/search/correction/TT behavior and lifecycle remain. Counts are 0..16, residual lanes are within +/-1008, padding lanes remain zero. Start zero initialization and all full-Board copies carry the state. Capture, EP, castling and all four promotions use the existing K updates.

The legal-EP attack-only scratch Board deliberately edits only b; its stale x stays confined to attacked/W with null move output and does not reach U/search/hash or escape. New direct-b diagnostic fixtures must construct x before evaluation. The executed new-layout fixture did so and independently rebuilt x/hash/scalar from mailbox at each checked state and every actual P U call.

Actual sizeof Board grew **168 -> 200 B**, x/side/hash/context offsets are 128/160/184/192. Actual fixed-profile primary P static stack allocation grew **4384 -> 4416 B**, with the same eight prologue pushes and 32-byte alignment. This is a frame observation, not a performance claim. The native grew 24 B despite a 28 B source reduction.

| Form | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 10,803 | `8fd32643582b3b485cdfa077fb20ada4af67c8cc0f867206f4c4f425312b9caf` |
| Native ELF | 26,376 | `db608da6eecd01fef7d845bb3bd8b52fe792ed527f4d2501c7c05900aad64b9a` |
| Bootstrap | 11,878 | `d68e78956401df2e24adc4e294cb27e839998e599ae66b55795e23d10106c3c1` |
| Complete file | 5,152 | `6584d2d9e8e5b777e54dfeb450c0bf59a261aaf5023430753d9e4e361b11fed1` |

Packaging remains one fixed ALONE LZMA1 9-extreme/lc2/lp0/pb0/BT4/64MiB/nice64 stream with prefix77. First cost used one candidate compile/package and strict baseline/candidate decodes. Focused actual candidate + unchanged DEV reference fixtures each compiled and ran once under ASan/UBSan: full feature/hash rebuild, 154 legal children from semantic cases, both-color capture/EP/pinned EP/both castles/four promotions, 10816 capture-order comparisons, and both-color depth2 searches passed. Every actual candidate search U call passed the independent rebuild; actual shipping image disassembly shows Board x load, vpmaddwd, high-half extraction and reduction. Independent source/fixture review was CLEAR. No old Board proof was inherited.

First-cost receipt `3e714590a5e5994b3f25b31a2a2401a8095120a7bcb73d9b9a9238d0433bfdc8` and focused receipt `2b52cd2d9ec912d3a74b90c61622eb886c616258c2bd0f9595e9ee5e78cb1046` are external. Earlier material-vector and other receipts in recipe are ancestry. Direct normal generation reproduced shipping twice and unchanged DEV twice. The unchanged verifier passed two selected quit/EOF sessions with eight legal GO results, exact new native image, three persistent startup TIDs, private-path/helper cleanup, stdio-only FDs and physical process/reader exit. Cancellation causality remains unproven. No games, strength or performance result is claimed.

The current normal build receipt is `5b5f831b89629e605e725316f9d0bed316c186ce12cba1f64a7c535f8f2cb57e`; selected runtime receipt is `bed3061a619a0ab7f97fe1fee99ea2a4f61e33a66d7cffe06e780e151ff91648`. The exact producing recipe `6ac3689052c69be9fd418ba0d24050ddc690e09dc3ec148710e1ece11e85d67d` is preserved in the external normal inputs. Final recipe/README changes only close result metadata; they were not the producing recipe revision. No archive/fresh, games or benchmark ran for this promotion.


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

고정 ONEcost 결과는 전체 4845→4827B,
새 native SHA `04c2a2ea2a5ff34b86cec2cca766576d31a4da306821da1d583e33368b18cc36`이며 원 native 전체 동일 주장은 없다.
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
재실행은 없다. Build SHA `d983b4fa6fe03ea9ec47e8c6fff040428c97283126177dfeb7a6696987eadacf`, runtime SHA
`df3e2a3ac6049dff8c7e28ef0ae90b17286d7bf622990d0d56e3bda429c1cf9e`이다. Producing recipe SHA는
`c039f28538e735c14d9ce0da246ba787bd745b882d3c6abc620af24c51bec197`이며 최종 recipe/README 차이는 완료 주석뿐이다.
기존 runtime ancestry와 새 이미지 검증을 구분한다. 이 결과는 좁은 selected 경로의
근거이며 grouped flush/timed trace 동일성, 성능·RAM·기력·전체 qualification이나 새 CI
성공을 뜻하지 않는다. 추가 SAN/NVC/codec검색/fault campaign/학습/선택 소비자는0이다.


## 공통 worker 시작·완료 epilogue 공유

새 pure `../tiny-entry-a/shipping_worker_epilogue_bce.py`를 기존 condition/output
chain 뒤 shipping에만 연결했다. 현재 소스 9700→9666 B,
native 26184→26184 B, 실제 73 B launcher를 포함한 whole
4827→4825 B이다. Source SHA `8d589012454fa7810b11c58a3eeea870da0ae7c56f906e65c17be9c167ed25ee`,
whole SHA `38ad8788abbef2fae1a83a7acc4950bec6a8d024168f77dbe5cca51aeebc3672`를 고정했다.

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
`bd68321b335c6d9bb27881af46d97f9efca9bf480c169e8392c604350acd1f6f`, runtime SHA
`19d82c48f5568988f4dc92a0b89db29000221ff4ef0619b99a708595aa0ce660`이다. Producing recipe SHA는
`2c71aa748999690e259bbdede6196187c2731d56d71003226e8aca3cbbf16c24`이며 최종 recipe/README 차이는 완료 주석뿐이다.
Startup broadcast/wake와 고정 deadline의 방문·결과 trace 동일성은 주장하지 않는다.
cancellation causality는 unproven이며 partial-create/join fault·epoch wrap 주입,
SAN·추가 fresh·학습·성능·RAM·기력·전체 core qualification·새 CI는 실행/주장하지 않았다.
Firstcost는 family당 compile/encode 각1이며 baseline 재측정·추가 후보·cost 재실행은0이다.


## Piece setter의 제거·삽입 phase 공유

공통 pure `../tiny-entry-a/shipping_setter_phase_bce.py`를 기존 worker stage 뒤 shipping에만
연결했다. Source 9666→9612 B, native 26184→26152 B,
73 B launcher를 포함한 실제 whole 4825→4815 B이다. Whole SHA는
`2091e679394672314e580f2d5fbb249c71873fbf7266284b57f28540f8458a77`다.

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
owned0으로 마감했다. Runtime SHA는 `d8243abb3d6935295c6c95cfc990f1454dd0b710237406f80ed3e22c575b0237`이며
build/runtime 영수증은 recipe setter_phase.normal_validation에 연결했다.
Producing 후 recipe/README 차이는 완료 주석뿐이다. Causality는 unproven이며
추가 SAN/fault/epoch-wrap/fresh/학습/cost 재실행·성능/기력/새 CI는0이다.


## 고정 object macro 네 개의 직접 치환

공통 pure `../tiny-entry-a/shipping_constants_bce.py`를 setter 뒤 shipping에만 연결했다.
PLY=128, MOVES=512, HISTORY=4096, MATE=30000의 정의와 실제 code token만
같은 unsuffixed int literal로 바꾼다. 고정 spans·보호 gaps·전체 inverse와 기존
입출력 guard를 유지하며 정본·DEV·원 parser·codec·탐색 기능은 그대로다.
Firstcost 전체 header CPP token과 native 전체 bytes가 원 baseline과 같다.
Source 9612→9527 B, whole 4815→4778 B
(73 B launcher 포함, delta -37 B), whole SHA `bc2cddf33045d250cdeed20ec5cf473b726dfeb9071c8d88c561552b8319709d`.
Macro-table와 진단 source 위치의 동일성은 주장하지 않는다.
CONSTANTS_NORMAL_PASS: ordinary --dev 한 번으로 shipping 두 사본과 DEV 두 사본을
재현했다. Source/native/bootstrap/whole 전체가 고정 firstcost와 같고 native와
진단 DEV source/native는 실제 이전 setter 산출물 전체와 같다. 원 selected의
quit/EOF 두 session·여덟 GO·3 startup TID·private-path 제거·closing bestmove 한 번·
readers 완료·물리 종료를 확인했다. 원 command 두 개는 terminal0/reaped/group 부재/
강제정리0/owned0으로 닫았다. Runtime SHA `edf7129beaee41fc052e308e174c12b1a7065ef241aba49077f1951d3e34b8a4`.
Recipe constants.normal_validation에 build/runtime 영수증을 연결했다. 이후 변경은
완료 주석뿐이며 causality는 unproven이다. 추가 SAN/fault/fresh/학습/기력/성능/새 CI는0이다.


## C completed-depth pool token (4666-byte selection)

The fixed worker's signed completed depth C now also owns job publication:
static/calloc0 is idle, publisher sets both depths-1 under qj after j drains,
and each own worker claims0 under qj before unlocking and entering think C.
Think no longer repeats that reset; completed iterations publish1..126.
The ai*w=NULL startup sentinel is retained with a distinct typed a=p pointer.
The last worker still emits/flushes x before completion broadcast, and the
existing drain, shutdown and partial pthread-create joins are unchanged.
This contract is only the actual unique shipping A->C(w,&ql) domain. Future
direct think fixtures must explicitly seed depth0; no general direct-entry
API equivalence is claimed.

shipping_pool_state.py is a pure six-role replay with seven protected gaps,
literal input/output pins and full inverse. It follows the unchanged C cross
stage. Packaging first restores9093, actually executes all existing C cross,
readonly-template and common literal guards, then replaces only the new
compact-source literal. The helper reads no AST, report, external experiment
or executable. Canonical/DEV bypass it. Board, physical8xint16 features, SIMD128,
model coefficients, move ordering, PVS/QS, coherent full-key TT and all three
learning bodies are whole-byte protected. Compiler, ISA, codec and resources
remain fixed. This reuses the already verified A/F ownership principle and
the actual C caller/source-gap proof; no redundant projection unit is added.

The one actual compile/encode cost is4672 -> **4666 B (-6)**, still **570 B
above4096**. Compact C9075 SHAce9c91755d91ee8e9b58639d6d904e68ab6a4e4d65f45cb5a57b40b38093164b;
native22672 SHA5c4470406b35f32f2be263a242d9613f201a4af176483dc7f087e7e52d99649f;
bootstrap10036 SHA0b51f88fe6033b480c0429a41337e1ea100a82db05632d70d29f4678488b520a;
whole4666 SHAa934ea13f9ea1b70c142fc4c8519f12bebb4e32b5f71ce31da0b7efd1d882591.
The entire native differs, so the previous C execution receipt is ancestry,
not this candidate's execution proof. Normal shipping/DEV reproduction and
the unchanged selected verifier must close below before runtime qualification.


The one normal ordinary `--dev` and unchanged selected invocation completed.
Shipping source/native/bootstrap/whole exactly reproduced the fixed first-cost
tuple twice; the diagnostic source and native reproduced twice and also match
the preceding actual Ccross DEV bytes. The selected4666-byte wrapper passed
two fresh quit/EOF sessions, eight legal GO epochs, three persistent startup
TIDs, the restored newnative5c447..., reader completion and physical process
exit. This tests the actual pool publication/claim/completion path. No extra
projection unit, model/search matrix, SAN/fault/fresh/game/strength/NPS or C8
test was added; the six-role/gaps/caller proof and A/F principle are reused.
Cancellation causality is unproven and FD-list inspection is not claimed here.

Actual root `/home/stemxstudio/rove4k-c-pool-token-normal-20261024-v1/`:
build/build.json SHAe8d5f2c94c68429db25dbf0f4260816e949e77b89b94caf3aca5709635731ff0;
runtime/runtime.json SHA9b04c164b3b7d254555b4e3298c33e3d5ecb08334ed6438504e08266cbfa048f.
Outer and both original command leaders completed with empty pre-reap group
members, reap/group-absence, forced0/failures0/owned0. Only recipe and README
completion annotations followed execution. Code, helper, explicit expected
tuple, compiler, codec, resources and the canonical/DEV input remain producing
bytes. The current full C file is still570 B above4096.


## Late four C object constants (4628-byte first cost; normal pending)

The current Ccross had reintroduced PLY128, MOVES512, HISTORY4096 and MATE30000
after the earlier BCE constant stage. The final shipping-only helper removes
exactly these four project-owned definitions and expands their code-identifier
uses to identical unsuffixed integer bodies:28 fixed spans,29 protected gaps,
full inverse, raw9075->8992(-83). Function macros, other directives, strings,
comments, canonical/DEV, the physical8xint16 model/SIMD, search/TT/learning,
fixed resources, compiler/ISA and codec are unchanged.

The single authorized cost ran old/new full-header CPP once each. Raw CPP
whitespace differs, but all340501 tokens match. Candidatecompile1 reproduced
the preceding22672-byte native5c447040... in its entirety. One original fixed
encoding and strict Python plus CLI restoration gave4666->4628(-38), still532
above4096. Source8992 SHAa82b3d17f132fba5e3949c9d2750ad2eeb5e2034db36d27daca2d8d3cdcd1329;
bootstrap9953 SHAefc5e1c5156661dfe91386285b5fdedacebceb0eef8779f79ca22bf2f315a65c;
whole4628 SHAe632d02ac220d995b9718e4726430d5f2e5ab2c0a708e66c0e9d08067fd9fb32.
Macro-table introspection and source-location diagnostics are outside the
identity claim. Packaging restores8992->9075->9093 and actually consumes the
existing pool/cross/common/template guards before replacing this final source
literal; no historical report or executable is a build input.

This is the single constant-stage cost, not an addition of a J/L hypothesis.
Ordinary shipping/DEV reproduction and unchanged selected quit/EOF verification
remain pending the final joint source choice. No new runtime is claimed here.


The final selection remains the constants-only4628-byte wrapper. A separately
measured J/L joint source8826 produced4650 bytes:LOSS22 versus4628 despite
entire-native identity, so it is preserved as an unselected experiment. Its raw
or separate savings are not added to this selection.

One ordinary --dev invocation reproduced the selected shipping tuple twice and
the unchanged diagnostic tuple twice. All source/native/bootstrap/whole bytes
match the fixed firstcost. DEV bytes also match the previous actual Cpool build.
The unchanged selected verifier then passed two quit/EOF sessions, eight legal
GO epochs, three persistent startup TIDs, the restored native5c447... image,
private-path removal, reader completion and physical process exit. Original
ordinary and selected leaders completed/reaped with no pre-reap group members,
group absence, forced0/failures0/owned0. This is new wrapper/restoration execution
proof; unchanged board/search/model/SIMD/TT/learning coverage is exact-native
receipt reuse. No new unit, projection, SAN/fault/fresh/game/strength/NPS or C8
campaign was run, and cancellation causality remains unproven.

Actual normal root:/home/stemxstudio/rove4k-c-late-constants-normal-20261024-v1
build/build.json SHAd4ee774d9d1cb0541310fc1b888b761672813cc9f4c101a5fe5ce3b562544404;
runtime/runtime.json SHA991b8c5c8b0cd6c0f2897c3ddd376750f7ce04fd8d7720a5038d71a42a674cdf.
Only recipe/README completion annotations followed execution. Producing code,
fixed expected tuple, helpers, compiler, codec and resources are unchanged.
The selected file remains532 bytes above4096.

## Compiler-group ownership adoption

현재 생산자는 기존 source/literal/argv 검사를 마친 뒤 `engines/scripts/compiler_group.py`를 encoding 직전에 적용한다. 컴파일러 원 leader를 `WNOWAIT`로 보존한 채 살아 있는 같은 process-group 작업을 정산한 뒤 마지막에 reap한다. Python 진입 시 SIGCHLD disposition을 저장·정규화하고 native exec 전에 복원한다. 원 C/source·compiler argv/env/cwd·stdio·읽기 FD exec·legacy exitstatus는 유지하며, 단순 크기 손실로 이 수명 수정을 숨기지 않는다.

| 현재 생산 context | 이전 whole | 새 measured whole | 새 bootstrap |
|---|---:|---:|---:|
| C | 4628 | 5002 | 10969 |

위 값은 각 actual 기존 입력에서 고정 codec 한 번과 strict Python/CLI 복원으로 먼저 측정한 값이다. source/native/compiler/header/codec의 변경이나 다른 문맥 delta의 가산은 없다. 기존 frozen control과 과거 qualified receipts는 당시 범위로 보존한다.

이 entry는 local source/Data proof 및 fixed-cost 측정까지 수행했다. 새 HEAD의 ordinary/positive CI 검증은 별도로 필요하며, F 기본형 양성 결과를 이 프로필의 새 runtime 결과로 재라벨하지 않는다.
공유 세 형상의 기존 packaging suites는 stream5·ZIP4·restored-files5 tests 모두 통과했다(skipped0). 이 관측은 live same-group 정산이며 detached 작업이나 zombie를 포함한 문자 그대로의 group absence 일반 증명은 아니다.

실제 producing/measurement/normal receipt는 recipe의 `compiler_group_ownership`에 명시했다. 공통 source helper에 대한 alias-only 후보 raw−389/whole+8 손실은 과거 미채택으로 남고 여기서 재실행하지 않았다.


## Prepared normalization and path-authority grace — producing checkpoint

The default full source-script path consumes all previous source/literal/compiler-owner/late-BOOT,
W1/W2 and seek admissions first. The exact previous prepared bootstrap
10817 B/8e900e265ab617f110eaca931f728fc9b19004023ac5ec012d26f0079103ec77 is then admitted before
calling the same frozen compiler_group.normalize_bootstrap and
compact_cleanup(state=True, wait=False, termination='grace'). The compiler_group
legacy emitter still returns the same bytes; its canonical cleanup renderer owns
both representations. No extra UCI/runtime policy selector is introduced.

Measured complete file 4944->4924 B saves20 B;
bootstrap 10817->10753 B. The independent fixed-codec
normalize+state+wait candidate is larger and is retained as an unselected cost.
Source/native/readable/DEV, worker2/TT18, codec and complete header are unchanged.
The recipe retains the full predecessor expected/helper/local-input closure and
a separate selected tuple. Only the four whole/bootstrap expected fields change.

Normalization moves compiler environment dict creation from before source-file
write/seek to Popen argument evaluation. Current closed builtin values agree,
but environment/audit hooks, concurrent mutation, allocation/source first-error
ordering, private e/s snapshots and exact tracebacks are outside equivalence.
INT/TERM registration/reset remains2 then15. State compaction invalidates d only
at the two settlement125 exits, retaining the physical workspace; ordinary
preparation/spawn/nonzero compiler failures keep their original cleanup and error.
The original graceful signal, separate5s grace/post-KILL/group budgets, unbounded
normal WNOWAIT, unreaped leader and last reap stay intact. Immediate KILL is not
selected by this default path.

Frozen common API SHA256 a245174aba2505493737dd87c2fd8943335346ae8ac419e79c1b203543695735; C-default stdin API
fc92bb6146fcfc5a6c73cd9f68929192a90d22a875bf591caf2cf3b32b87055b preserves the prior C emission.
The shared package helper is finally frozen at SHA256 149f616c6e8d78b52dc88ccf0dd303d37ad2bcc513e16c40a54ac1daf09d7d2f.
No mismatch is silently accepted. PENDING: producing source qualification
requires actual ordinary regeneration and the selected verifier. Old runtime
receipts keep their original source scope. Completion is recorded separately
without changing producing recipe/README after qualification.
