# Maintained A: terminal seek-implied flush — 2026-10-24

기본 `loose` full shipping의 측정 선택 파일은 **4807 B**다. actual W1+W2 전체
4810 B와 같은 source/native·73 B header·BT2/nice24/16KiB codec에서3 B 줄었다.
Bootstrap은10185→10175 B이며 4096 B까지711 B가 남는다. full 기능을 줄이지 않았고
출품 크기 통과나 검색·기력 개선으로 해석하지 않는다.

`compiler_seek.py`8813 B/`8ca5fd736f010cd9dd1e3b668065c0cf7d82f9e98653580b8f9b4c23e7d75a41`을
recipe helper catalog에 고정해 복사 후 로드한다. 기존 `compiler_stdin.py` ee9 바이트는
그대로다. source/literal/template/compiler-owner 및 dead-score의10305 B BOOT를
먼저 admission하고, 기존 W1+W2를 수행해10185 B/
`1da24c94ea091b5a40bb1d23e30872a25d29733032181accfa3b06e9eaa626a6`를 다시 확인한 뒤
seek terminal을 정확히 한 번 호출한다. 원 W1+W2 descriptor는 이 중간 단계의 selected
tuple로 유지하며, 새 terminal에 predecessor와 최종 tuple을 별도로 적는다.

Callback은 그 W1+W2를 만든 동일 frozen module의 transform/restore 함수와 실제
owner metadata다. 새 helper는 owner inverse와 재생성을 실제 대조한 뒤 explicit
`f.flush();` 한 구간만 제거한다. 두 바이트 gap과 전체 byte/AST inverse를 보존한다.
trusted callback은 admission 의존성이지 인증 경계가 아니다. 임의 callback이나
손상된 파일 객체의 의미 보존을 주장하지 않는다. root3와 DEV는 이 stage를 bypass한다.

적용 계약은 builtin `open(d+'/c','w+b')`가 반환하는 regular BufferedRandom이다.
`seek(0)`가 pending buffer를 raw stream에 기록한 뒤 되감으므로 compile 준비와
rewind가 spawn 전에 끝난다. Pending write error는 explicit flush 대신 seek에서
드러난다. Direct flush method hook, traceback 위치/동일성, monkeypatch와 임의
file-like 객체는 계약 범위 밖이다. source 표현·compiler argv·부모 UCI FD0·descriptor
소유권·mask/publication·WNOWAIT/group settlement는 바꾸지 않는다.

Root actual firstcost의 전체 파일은
`f3433444742ead94c7bb2ad2e06439dc468b7b575285faaa961bd0f2eb5fee78`, bootstrap은
10175 B/`9caeb9a45554a46a7ff0dd87945e8792152cb74495a9b6326050dddaf322dfec`다.
Source8335 B/2d077...와 native18576 B/9b0e162... 및 DEV/root3 기대값은 그대로이며
top-level expected의 bootstrap/whole 네 필드만 측정 literal로 바꿨다. 오류 뒤 실제
출력으로 기대값을 자동 갱신하는 경로는 없다.

PENDING: 기존 default builder `--dev --policy loose` 한 번과 변경 없는 selected
verifier 한 번을 CPU0 compile/CPU0–1 runtime lane에서 실행할 예정이다. 생성 소스는
그대로 동결하며 사후 repo 주석을 쓰지 않는다. 완료·실패·실제 producing 핀은 외부
`rove4k-a-seek-flush-promotion-20261024-evidence`에 기록한다. 새 game/benchmark/CI나
다른 profile 검증을 이번 결과에 섞지 않는다.

## 이전 기본 및 선택 정책 단계의 기록

# Maintained A: terminal W1+W2 wrapper — 2026-10-24

기본 `loose`의 full shipping 전체 파일은 **4810 B**다. 동일 source/native·73 B
header·BT2/nice24/16KiB codec의 actual4854 B 기준에서44 B 줄었다. 4096 B까지
714 B가 남으며, 크기 통과나 기력·검색 변경으로 보고하지 않는다.

`compiler_stdin.py`25300 B/`ee9ba2c938cfabf30261451961c424254d9f75a804d5c3e6d832b09bfcf4f247`를
recipe helper 목록에 고정해 복사한 뒤 로드한다. terminal 호출은 기본 정책의 모든
source/literal/template/compiler-owner 및 dead-score BOOT guard 뒤에만 둔다.
이전10305 B/`fb0e7c10dce6d4ce957e4c92e5bebbcf85b13bdcaf1cb034ed5d3d24771320f0`를
별도 predecessor로 admission하고, 기존 guard 기대값은 바꾸지 않는다.
DEV와 세 root 정책은 terminal 호출을 bypass하며 기존 expected/source flow를 유지한다.

W1은 compiler 입력을 private cwd의 `c` regular file로 옮겨 buffered write·flush·seek0
후 spawn한다. compiler argv와 정확한 C 표현은 유지하며 부모 UCI FD0은 바꾸지 않는다.
compiler FD0의 seek 가능성과 named `c`의 존재는 선언된 관찰 차이다. 현재 고정 C는
표준 angle include만 사용하고 FILE/상대 include/incbin/설정 파일 관찰이 없어 적용할 수
있다. arbitrary source/compiler 동등성을 주장하지 않는다. 준비 중 INT/TERM mask는
spawn/publication/unmask까지 pending cancel을 지연할 수 있으므로 준비 취소에서
compiler0을 보장하지 않는다. 파일 handle은 compiler owning try 안의 with에서 닫는다.

W2는 기존 leader/group wait 본체를 공유하며 WNOWAIT 원 leader, deadline·반복 KILL,
live-group settlement 후 reap, CHLD와 mask 복원·cleanFalse125 workspace 정책을 유지한다.
helper는 이전 corrected-owner scaffold를 정확히 재구성하고 선언된 구간 밖 byte/AST와
전체 inverse를 검증한다. 기존 보호를 건너뛰기 위한 앞단 치환을 넣지 않았다.

실제 control 재인코딩4854 B와 측정 W1+W2 candidate4810 B를 대조했다. 선택 whole은
`9b791410dca97f8cf0d1e32965e419888561db1935c3be96c000ce2f79c91090`, bootstrap은
10185 B/`1da24c94ea091b5a40bb1d23e30872a25d29733032181accfa3b06e9eaa626a6`다.
이 단계 source8335 B/`2d077291e5615790206a43399d809b23aca5a2deec17623cd4c32f40fcb1ebf4`와
native18576 B/`9b0e162a4f8f4073d2d16b6d5da336baacaf5bb5bc9e38e07f851d2afa8004f2` 기대값,
DEV·root3 기대값 및 기존 source helper pin은 그대로다. 측정 결과를 명시적으로 선택했으며
실패 뒤 actual을 expected로 자동 복사하지 않는다.

현재 기존 loose `--dev` builder 한 번과 unchanged selected verifier 한 번은 실행 전이다.
actual producing recipe와 이후 사실 주석은 외부
`rove4k-a-wrapper-W1-W2-promotion-20261024-evidence`에서 구분해 보존한다. root3 local,
새 CI·SAN·fault·game·matrix를 추가하지 않는다.

## 이전 기본 및 선택 정책 단계의 기록

# Maintained A: default Loose unused published score removed — 2026-10-24

현재 기본 정책의 실제 CLI 이름은 `loose`이며 full shipping 전체 파일은 **4854 B**다.
동일 corrected compiler owner·73 B header·BT2/nice24/16KiB LZMA codec에서
이전4863 B보다9 B 작다. 4096 B까지758 B가 남는다. 기존4489 B는 이전 owner의
별도 조건이며 현재 비용 기준으로 사용하지 않는다. 크기 통과나 기력 개선을 주장하지 않는다.

`shipping_dead_score.py`는 `not dev` 안의 `not root_policy` 분기에서 default EP
뒤에만 적용한다. 실제 Worker `M.l`의 reset·completed store 두 쓰기와 이를 위한
think 반환값 바인딩·필드만 제거한다. 결과와 pool은 완료 깊이 `C`와 best `H`만 읽는다.
`h(...)` 호출과 인수·부작용·검색 내부 score/TT/learners, stop 확인·best/depth 게시,
typed worker 전달·drain/result/flush/join은 그대로다. `L l=`는 int 매크로이므로
원문 절감은20 B다. 정본/DEV와 root-hint/NORMAL/PALS 세 정책은 이 단계를 bypass한다.
DEV result는 score를 읽으며 세 root 정책은 별도 score 의미와 literal guard를 유지한다.

package는 candidate를 실제 이전8355 B로 역변환하고 기존 common literal과
default EP→frequency→pool→keyword→output→condition→names 및 read-only template
보호를 실제 소비한다. 현재 compiler owner를 적용한10325 B bootstrap에서 source
literal만 교체한다. 네 source span·다섯 gap과 source/bootstrap 전체 inverse를
검증하며 source 밖 bootstrap·argv·기존 helper pin을 바꾸지 않는다. 새 helper는
recipe의 고정 local 입력으로 복사 후 로드한다. root3의 source 생성·기대 tuple과
literal 경로는 별도로 그대로 두며 DEV source/native 기대값도 유지한다.

실제 firstcost는 source8355→8335 B, bootstrap10325→10305 B, 전체4863→4854 B다.
Whole SHA-256은 `88e23a6a4f2894d6c3a58551444705c2cb5ef6e3f355bc8c5385873b92bd331e`다.
기준 encode0, 후보 encode1, strict Python EOF/trailing0·CLI byte inverse1씩과
실제 13 B LZMA header 일치를 확인했다. 기존 actual CI의 A 소비 입력45개도
현재 bbc999b HEAD Git blob과 동일함을 확인했지만 그 실행 성공을 후보에 상속하지 않았다.

후보를 동일 `cc -Os -x c - -o x -s`로 한 번 별도 컴파일해 native18576 B/
`9b0e162a4f8f4073d2d16b6d5da336baacaf5bb5bc9e38e07f851d2afa8004f2`를
새로 발견했다. 이전 native와 크기는 같지만 바이트는 다르다. 실제 old/new 선언
prefix의 compile-time probe 두 개로 Worker68976 B·align8 유지, H offset12→8,
a5와 뒤 배열 offset 유지를 확인했다. probe 실행·RSS/stack/속도 측정은 하지 않았다.
Discovery 원 그룹은 리더 identity를 유지한 채 정착을 확인하고 reap했으며 forced0/owned0다.

A_DEFAULT_DEAD_SCORE_NORMAL_PASS: 명시 `--policy loose`로 기존 builder
`--dev` 한 번을 실행해 shipping 두 사본의 source/native/bootstrap/whole을 실제
firstcost 및 fresh-native discovery와 동일하게 재생성했다. DEV 두 사본은 기존
source/native 전체와 동일하다. 변경 없는 selected verifier 한 번은 새 native의
quit/EOF 두 session·여덟 legal GO·3 startup TID·정확한 deleted native 복원,
private path 삭제·compiler child 부재·closing bestmove 한 번·reader 완료·물리 종료를
확인했다. 기존 A verifier는 live FD 목록을 열거하지 않으므로 FD 실행 증명은 추가하지
않는다. 원 outer592/632는 WNOWAIT로 identity를 유지한 채 other members0을 확인하고
reap했으며 terminal0·group 부재·강제 정리0·owned0이다. cancellation causality는 unproven이다.

이 실행이 소비한 recipe는213039 B/`f09dccc1f6bd573bbf9df6a2b2fda1c7caa37f2eab9d4e54d4f00a689a8a47c3`다.
실행 중 README111601 B/`3f66f37d2d2ba44639be2ab3fc84cf683db4f7c298a126de3a8b94753a51dfcc`도
바뀌지 않았으나 README는 builder 입력이 아니다. 실행 뒤 recipe의 normal status와
이 문단만 사실 주석으로 갱신했으며 helper/build/selected 기대값·DEV 및 root3 기대값은
동일하다. producing/final 해시는 외부 `rove4k-a-dead-score-promotion-20261024-evidence`에서
구분한다. root3 local·SAN·fault·game·matrix·새 CI를 추가하지 않았으며 이전 CI의
실행을 새 candidate 성공으로 상속하지 않았다. 시간제 score/TT interleaving·모든 검색
trace·기력·속도 동일성은 주장하지 않는다.

## 이전 기본 및 선택 정책 단계의 기록

# 기본 Loose4489: EP 정규화가 actual maker 재사용 — 2026-10-24

기본 frequency 뒤 `shipping_ep.py`만 추가한다. 기존 D200B를 새 D140B로
바꾸고 unchanged v 뒤로 이동하는 전방선언18B를 포함해 source8397→8355
(raw−42), 실제 완성4499→4489(−10B)다. Native18576/f99afd…는 새 신원이다.
Literal은8355→8397 inverse 뒤 actual frequency/pool/keyword/output/condition/
names guard를 소비한 다음 forward한다. Canonical/DEV와 root3는 우회한다.

Nonempty EP는 정상 legal Board의 doublepush 뒤 half0·valid king/HCE cache에서만
도착한다. Trial pawn15/17/PROMO0은 child.e=-1을 유지하여 nested D가 즉시 반환하고
v/D nesting은 최대2다. Fully initialized trial의 provisional uint64 h/r은 버리고
boolean own-king legality만 쓴다. Arbitrary poisoned HCE/high-half Board API
동등성이나 속도/stack 이득은 주장하지 않는다.

Actual8355 TU+oldD/unchangedv name-only reference의 optimized/fatalUBSan 각1회에서
각각12root/21legal replay/122legal child의 독립64-square legalset·전체 named
Board/hash/HCE/context·부모불변을 확인했다. 양색 legalEP/filepin/rank discovery,
두 origin/인접없음과 actual startpos EP replay를 포함한다. 기존 F/D 실행 자격을
이식하지 않는다. 원문/기능 증거와 새 normal/wrapper 실행은 구분한다.

EP_NORMAL_PASS: ordinary --dev1에서 shipping2의 source/native/bootstrap/whole은
실제 firstcost 전체와 같고, DEV2는 이전 qualified DEV와 전체 bytes가 같다.
Unchanged selected1의 quit/EOF2sessions·8GO·각3TID·새 f99afd… native image·
private path 제거·closing bestmove 한 번·reader EOF·물리 종료가 통과했다.
원 outer/ordinary/selected leader는 WNOWAIT identity를 보유한 채 extras[] 확인 뒤
reap했고 group 부재·forced0·owned0으로 종료됐다. 코드 helper/builder는 producing
bytes 그대로이며 이후 차이는 recipe/README 완료 문구뿐이다.
Build SHA a07e597b4dfeec19aa95253615a2553118ffdaaad05c589338f5a16c6f4d0257,
runtime SHA c03df5cdc9bef7bf84b39c0026120ccc5ab7a01a969ff767b15190d61fa4fd51.
외부 stdout capture는 outer child label과 파일명이 겹쳐 summary 텍스트 일부가
겹칠 수 있다. 원 named normal/physical/build/runtime 영수증은 온전하며 capture를
독립 JSON/immutable child stdout 증거로 주장하지 않는다. 재실행은 없다.
기존 root3 dictionary/source pipeline과 qualified DEV bytes를 보존하며 optional
runtime·새 core/SAN/fresh/game/performance·CI 주장은 없다. 아래4499는 역사적 증거다.

---

# 기본 Loose4499: 고정 binding 빈도 배정 — 2026-10-24

기본 Loose의 pool 단계 뒤 `shipping_frequency.py`를 연결했다. qj→I13,
qr→K8, ql→F7, qq→N7, ai→M7, qp→X8, X→qp4의 한 고정 배정이다.
모든52 한 글자가 이미 쓰이므로 문자열 전체 치환을 하지 않았다. 실제 A의
253 declaration·2441 reference graph를 대조해 h의 지역 I/K/F/N 가림과
signature 뒤 지역 M, 동시 X/qp 교환의 binding을 확인했다. 실제 atomic store
4곳과 flag-clear1곳은 expanded target과 정확한 physical 인자에만 대응한다.
Jreturn/Lint·기존 directive/header/literal/member/local은 보존한다.

54개 고정 span·55개 보호 gap과 전체 inverse로8397→8443을 복원한 뒤
기존 pool→keyword→output→condition→names/common guard를 실제 소비한다.
Source8443→8397(raw−46)과 whole4505→4499(−6B)는 별도 실측이며 native
18576/35056c24… 전체 bytes는 이전과 같다. 원 compiler(no-pthread), FD0
bootstrap·header73·ALONE6/BT2/16KiB/nice24 및 fixed2/TT18은 그대로다.
이름/codec sweep은 없다. Native 동일성 gate를 통과한 뒤만 encode했다.

FREQUENCY_NORMAL_PASS: ordinary --dev 한 번에서 shipping 두 사본의 source/
native/bootstrap/whole은 first-cost 전체와 같고, DEV 두 사본은 실제 이전 DEV와
전체 bytes가 같다. Unchanged selected 한 번에서 quit/EOF 두 sessions·여덟 GO·
각3 startup TID·실제 native image·private path 제거·closing bestmove 한 번·
reader 완료·물리 종료를 확인했다. 원 driver/build/selected 핸들은 WNOWAIT
leader identity를 유지한 채 extras[] 확인 뒤 reap했고 종료 당시 group 부재·
강제 정리0·owned0이다. Build SHA `827ceb40549d9d934d24295bdc14d3b48c04506db4bfb74abf54774f605fa375`,
runtime SHA `1e4b58ba2d6aeee1a93b35e989cdb54953a6cd03ec837ec78b3fee676f8000ae`.
코드 helper/builder는 생산 bytes 그대로이고 이후 차이는 완료 주석뿐이다.
세 optional root 정책과 DEV는 마지막 단계를 완전히 우회하며 기존 tuple과
원 guard를 유지한다. 해당 root 실행0이고 FD 관찰·cancellation causality·
성능/기력·새 core/SAN/fresh/CI 자격을 주장하지 않는다. 아래4505와 이전 증거는
각각의 원 scope로 남긴다.

---

# 기본 Loose4505: worker depth와 job token 소유권 공유 — 2026-10-24

기본 Loose에만 keyword 단계 다음 `shipping_pool_state.py`를 적용한다.
이전 job epoch `qd` 대신 각 worker의 완료 depth `C`에서 −1을 미수락 job,
0을 수락한 job으로 사용한다. main은 이전 pending0과 결과 flush 뒤 `qj`
아래 두 token을 게시하고 worker는 같은 잠금 아래 자기 depth0을 수락한다.
A의 기존 `w=0` startup sentinel과 공통 startup/completion epilogue는 유지하고,
별도 typed pointer `a=p`로 자기 worker의 predicate를 읽는다. Spurious wake와
marker-before-wait는 중복 검색을 만들지 않는다. 마지막 pending0은 두 worker가
반환하고 결과가 flush된 다음이며, partial-create의 wait 우회와 created-prefix
join·quit/EOF는 그대로다. 실제 shipping의 유일한 `C()` caller가 claim0을
소유하므로 `C()`의 중복 depth0 초기화만 제거한다. 직접 private `C()` 소비자는
별도로 depth0을 넣어야 한다. Canonical/DEV 함수 계약 변화는 없다.

6개 고정 span과 7개 보호 gap의 전체 inverse로 8443에서 이전8461을 복원한 뒤
기존 keyword→output→condition→names/common literal guard를 실제 소비하고
한 번 전진한다. Jreturn/Lint, TT j/k, 검색·보드·학습·parser 원문은 보호한다.
Raw source8461→8443(−18B)와 실제 whole4511→4505(−6B)는 별도 실측이다.
Native는18576/35056c24…로 바뀌며 이전 full-native 동일성을 주장하지 않는다.
Compiler·FD0 template·header73·ALONE6/BT2/16KiB/nice24·fixed2/TT18은 같다.

POOL_STATE_NORMAL_PASS: 기본 ordinary --dev 한 번에서 shipping 두 사본은
실제 first-cost source/native/bootstrap/whole 전체와 같고, DEV 두 사본은 이전
실제 DEV 전체와 같다. Unchanged selected 한 번에서 quit/EOF 두 sessions·여덟
GO·각3 startup TID·새 native image·private path 제거·closing bestmove 한 번과
reader 완료·물리 종료를 확인했다. 원 driver/build/selected 핸들은 WNOWAIT
leader identity를 유지한 채 extras[] 확인 뒤 reap했고 종료 당시 group 부재·
강제 정리0·owned0이다. 새 native의 실행 검증이며 이전 native 동등성은 아니다.
Build receipt `e814b7df2cd7bbb1c5472d983ab4cd8ad2d566bd7f4f6f0fec611a1ab63d78cf`,
runtime receipt `f321f2233c67878fb1b84df40c834fa589d989856876548f12dacc951c462dc4`.
세 optional root policies는 이 마지막 단계를 완전히 우회하며 기존 소스·함수·
expected·literal guards·생산/검증 metadata를 유지한다. 해당 정책의 새 실행은
0이다. FD 관찰·cancellation causality·성능·기력·새 SAN/fault/fresh/CI를
주장하지 않는다. 아래4511 기록과 과거 core 증거는 각각의 원 범위로 남긴다.

---

# 기본 Loose4511: keyword와 지역 scope의 고정 축약 — 2026-10-24

기본 Loose에만 마지막 shipping `shipping_keyword_scope.py`를 연결했다.
TT move J와 depth L의 h 지역 선언/참조 네 토큰을 j/k로 바꿔 한 문자 이름을
비운 뒤, 마지막 include 다음 `J=return`, `L=int` object macro로 실제 keyword
43/88개를 공유한다. 뒤 inner j/k의 scope는 outer 사용 이후이며 macro 인수,
문자열화/##, 기존 directive·literal·타입·평가 순서는 보존한다.
고정136 spans/137 gaps와 전체 inverse는8461에서 이전8821로 돌아가 기존
output→condition→names/common literal guard를 실제 소비한 뒤 한 번 전진한다.

소스8821→8461(raw−360)와 실제 전체4525→4511(−14B)은 별도 측정이다.
실제 GCC13 header 포함 CPP token은 네 local 이름의 정확한 위치 역대응 후
같고 native18576/5fd8f877… 전체 bytes도 같다. Macro table과 진단 source 위치
동일성을 주장하지 않는다. Compiler·FD0 template·header73·ALONE6/BT2/16KiB/
nice24와 fixed2/TT18 자원은 그대로이며 codec/name sweep은 없다.

기본 경로만 `not root_policy`에서 적용한다. root-hint/leader-Repair5151,
root-normal-slots5132, root-pals-feedback6677 세 정책은 기존8821 입력과
각각의 원 helper/literal pipeline·expected·생산/검증 metadata를 보존한다.
아래의 Loose4525 비교는 그 정책들이 측정된 당시의 기준선이다. 세 정책의 새
실행이나 새 변형을 주장하지 않는다. DEV도 새 shipping 단계를 우회한다.

KEYWORD_SCOPE_NORMAL_PASS: default ordinary --dev 한 번에서 shipping 두 사본과
기존 DEV 두 사본을 재현했다. Source/native/bootstrap/whole 전체는 원 firstcost와
같고 DEV source/native도 실제 이전 default baseline과 같다. Unchanged selected
한 번에서 quit/EOF 두 sessions·여덟 GO·3 startup TID·실제 native image·private-path
제거·closing bestmove·reader 완료·물리 종료를 확인했다. 원 driver/build/selected
핸들은 WNOWAIT leader identity 유지 상태의 extras[] 확인 후 reap했으며, 종료 당시
group 부재·강제 정리0·owned0이다. Build SHA `a699b5c93eda7b7e8a5c3378ecdcdff7ba1b3599dfed9d3cd25c68151a536ec5`,
runtime SHA `b9245b7b9e8b3e1ed61256b7340f9d0acdf030333ce8a3e65eba854c9a947d62`이다. Producing recipe SHA는
`5cbfe6ace63986eb3b4c3bf8f6c311a0026774394cfcc58cc42f37dfcb7ab2c0`이며 최종 차이는 완료 주석뿐이다.
세 root 정책은 재실행하지 않았고 원 metadata/expected/pipeline을 보존했다.
FD 관찰·cancellation causality·시간제 동일성·성능/RAM/기력·추가 SAN/NVC/fault/
fresh/학습·새 CI는 주장하지 않는다.

---

# Optional compact A full PALS feedback — bounded local execution recorded, 2026-10-24

`--policy root-pals-feedback` adds actual compatible completed NORMAL-slot reuse,
proposal reply selection, a constrained COUNTERREPLY, and same-first unrestricted
Repair with rechecking of the original challenged reply. It is a separate build
policy. Default Loose4525, root NORMAL5132 and hint/leader-Repair5151 keep their
existing descriptors and helper sources.

The frozen prototype15535 is now reproduced through a pure eight-span helper
following the actual maintained NORMAL transformation. Inverse/literal packaging
runs the existing NORMAL -> output -> condition -> names guards on the real input.
Initial actual cost is C15535, native22672/0767d28b..., bootstrap16489 and whole6677:
+1545B over NORMAL and +2152B over Loose for the additional policy, not an
identical-function compression loss. This is2581B over4096; no 4KiB acceptance.

Only unrestricted completed NORMAL or Repair scores can reach root acceptance.
Counterreply is a same-first diagnostic, never a root bound or cache score. Repair
keeps the challenged reply as an ordering hint and searches all legal replies;
its normal result is checked against that same reply before root H/G changes.
A persistent contradiction or incomplete review cancels the incomplete iteration
and preserves the last completed depth. It does not declare the whole root or
other first moves refuted. Original job, deadline, helper TT-write fence, stop,
round drain and physical pool ownership remain. Private NORMAL history/order and
ordinary LMR variation are allowed; this is not formal minimax or identical
private-function equivalence. Diagnostic TT behavior follows C's unrestricted
grandchild contract, not Rust's isolated whole clause.

The new policy passed one ordinary `--dev` build (two identical shipping tuples
and two unchanged DEV tuples) and the unchanged selected body in quit/EOF two
sessions, eight legal GO epochs, actual three TIDs and physical native exit.
The actual whole remains 6677 B. FD inspection was not performed by this verifier.

One fatal UBSan compile and two bounded actual-main runs used an observational
copy of the real policy, with no score, slot or TT injection. Aggregate direct
NORMAL accepts=1154, completed bests from direct slots=12,
actual counter searches=40, refutations=0,
Repair searches=0, original-reply rechecks=0.
The source contract for same-first unrestricted Repair is implemented; zero
natural branches in these runs remain unobserved and are not qualified by source
review or the earlier NORMAL observer. Helper TT payload writes and recorded
drain/job-reuse violations were zero. Original process handles reached terminal,
reap, pipe-reader EOF/join and group absence without forced cleanup.

Producing recipe: `5e6ed43b69728d4c96ccc1bb28d21f10a0cee7e4e3c5658b246f4e3c6bebca04`.
Normal receipt: `36949aa865ecfcda2bd6880eea4a87c479e34e264beff7fccd0aac1dfb4030aa`.
Initial focused receipt: `101d47190c1bf2007ee89ece72758e93bfc8b17a60ad4dd95f0d76d2145812d4`.
Final bounded followup: `772e8680526dfe270d3559ffe584bf027e491660cc8b7475a3df4aad9f793e92`.

Source helper `runtime_qualified:false` still describes the pure transform.
The observer can affect scheduling and layout; strength, performance, identical
search and formal minimax are untested. Root separately owns fresh CLI and CI
registration; no fresh run or CI success is claimed here. No further coverage
search was run after this one fixed deeper followup. Shared assertions are unchanged.

# Optional fixed2 A same-A NORMAL completed-slot reuse

Separate build-time opt-in: **root-normal-slots**, first-cost **5132 B**.
Default Loose4525 and the independent hint/leader-Repair5151 policy remain
unchanged. This is a new search/parallel policy (+607 B versus Loose,
-19 B versus hint), not an equal-search compression or performance verdict.

```sh
python3 -B engines/compact/tiny-entry-a/build.py --policy root-normal-slots --dev --out /absolute/new/normal-build
python3 -B engines/compact/tiny-entry-a/verify.py --policy root-normal-slots --build /absolute/new/normal-build --out /absolute/new/normal-runtime
```

The helper performs the actual first move, appends the actual child key at
job-history base, and calls the same unrestricted h at ply1/depth-1 with a
full window. Both roles use fixed HCE and the same ordinary selective
policy. Private ordering/history/id and normal-policy LMR variation are
permitted; no role-only evaluator, extra pruning/reduction, excluded reply
or reduced requested depth is admitted. NORMAL EXACT is the engine's normal
selective classification, not formal minimax or identical private searches.

Only completed valid nonstopped state3 results become leader l directly and
skip its local child search. Other slots use the existing local PVS. The
original stop check precedes H/G/root-result acceptance. Helper TT payload
writes remain blocked; the same-normal leader TT may be read. Fixed roles
start with empty TT. The root loop retains its aggregate/cutoff ownership;
round callbacks drain before completed-depth commit, and the original job
fence drains before root/history/epoch reuse. Queueing is speculative and
may start helpers before the leader's first legal move finishes.

The pure late source helper is an alternative to the hint helper after the
same output stage, not a transform layered on the hint source. Ten regions,
eleven protected gaps and full inverse bind source8821→10835. Its literal
adapter goes through the unchanged output→condition→names guards. Compiler,
FD0 template, header73, ALONE6/BT2/dict16KiB/nice24 and fixed2/TT18/PLY128 stay.
DEV remains the unchanged Loose diagnostic control. Fresh forwards the
selected policy; no fresh execution is claimed. Source/producer inputs were frozen before the local validations below.
No strength, speed, many-core,4KiB or CI success is claimed here.

<!-- A_ROOT_NORMAL_COMPLETION:PASS -->
One ordinary --dev reproduced two shipping source/native/bootstrap/whole
tuples exactly against firstcost5132 and two unchanged DEV controls. The
policy selected verifier retained its original assertions and passed
quit/EOF two sessions, eight legal GO, three startup TIDs/session, actual
new native, private path, helper/readers and physical exit. A has no FD-list
observer; the retained cancellation-causality field remains unproven.

One fatal UBSan compile/runtime observed produced3/take3/direct l/local-h
bypass/accepted 243/243/243/243/243. Direct values updated H/G/root move
5/5/5 times, and 3 completed-depth commits retained a direct-slot
best with exact move/score checks (total commits9). Actual helper ay qp/deadline
early returns were22/2; stop state4 publications24 included
23 after observed helper ay stop. Actual state4 take/rejection, original local
fallback child entry and root/depth stop rejection were3/3/3/3.
Actual payload writes were4516, helper0 and unknown role0;
helper store gates suppressed108084 sites. Round reuse/drain checks
were12/12, job drain/reuse checks8/3; all handoff, bypass,
commit-value and drain/reuse error counters were zero. Active quit was
observed, final pending/open/busy zero and both original worker joins passed.

The completed-slot/stop race at direct-ready acceptance, invalid-move and
score-range state4 rejection paths were unobserved in this run; they were
not filled using injected values, retries or extra cases. Added observer
atomics/TLS/arrays may affect scheduling, timing, stack and native bytes.
This is actual normal-policy path evidence, not identical private searches,
mathematical minimax, all pthread schedules, strength or speed evidence.

Product commands used explicit local WSL user root. Their results do not
establish unprivileged execution or file-permission acceptance. Ordinary/
selected original handles were reaped with groups absent; focused handles
also recorded session absence. Readers finished, forced cleanup and
unresolved owned handles were zero. No product retry, extra codec cost,
fresh archive execution, new fault campaign or CI dispatch was performed.
Old source/cost/hint records remain unchanged.

# Optional fixed2 A root-hint / leader Repair

The default remains qualified **Loose4525 B**, with the unchanged canonical
source, DEV control and old output/condition/names guards. Build-time opt-in:

```sh
python3 -B engines/compact/tiny-entry-a/build.py --policy root-hint-leader-repair --dev --out /absolute/new/root-build
python3 -B engines/compact/tiny-entry-a/verify.py --policy root-hint-leader-repair --build /absolute/new/root-build --out /absolute/new/root-runtime
```

This maintained optional policy is **5151 B**, source10873/native22672/
bootstrap11827. Its +626 B is new-policy incremental size, not an equal-search
compression result or a strength/performance verdict. One ordinary opt-in
`--dev` reproduced two shipping tuples byte for byte against the fixed first
cost and two unchanged Loose DEV controls. The policy-matched selected
verifier retained its original runtime assertions and passed quit/EOF two
sessions, eight legal GO epochs, three startup TIDs/session, actual new
native identity, private-path/helper/readers and physical process exit.
A's selected verifier has no FD-list observation. Cancellation causality
remains unproven in that original observer.

Helper proposals only steer a root-edge LMR exemption; the leader always
uses its existing h/PVS/TT path for the accepted score. Helper TT payload
writes are blocked. Compatible NORMAL cross-worker bound reuse remains
unfinished. Both roles use the original deadline, job epoch and callback
lifetime, with helper drain before completed-depth acceptance. Fixed profile:
two workers/TT18/PLY128, three total engine TIDs, no new UCI option and no
runtime policy switch; the TT starts empty and worker roles stay fixed.

The pure late helper follows output only in selected shipping. Its ten exact
regions/eleven gaps/full inverse preserve current8821 as preimage. The outer
literal adapter inverses to the unchanged output→condition→names chain and
forwards inside the guarded raw-double C body. FD0 template, no-pthread/
implicit GNU17 compiler, ALONE6/BT2/dict16KiB/nice24/header73 remain. Default
recipe values and the selected verifier's original assertion tail are intact.
Fresh forwards the chosen policy through both archived rebuild commands;
this was inspected as source only, with no fresh archive execution.

One fatal UBSan compile/run observed a copy of the actual maintained h/R2
and original UCI main on natural clocked startpos/replayed positions. It
recorded 216 ready proposals, 216 corresponding leader ply1 entries,
216 entries passing ay, and 216 actual leader scores passing the original
post-search stop check. The proposal>alpha LMR exemption was observed
(9), and leader-owned TT returns after a ready proposal were
observed (49). These are direct counters, not node-count
coverage inference. Helper store suppression reached 25094 completed search sites;
actual TT payload writes by the helper were 0 (unknown role 0).
Drain checks 11 and completed-depth commits 8 had no bad drain/commit
tokens. Active quit was observed; final open/busy/pending were zero,
done/quitting were set, and both original worker joins succeeded. Added
atomics/TLS/observation code can affect scheduling, timing, stack and native
bytes. This is bounded actual-path evidence, not a same-Loose score, full
schedule/race, partial-create/epoch-wrap runtime or performance proof.

The ordinary/selected original command handles were reaped with their
groups absent. The focused handles also recorded session absence. Both
phases had no forced cleanup or unresolved owned handle. There was no product retry, new fault/negative campaign,
playing-strength/full-core benchmark, fresh execution or CI dispatch.
Default Loose4525 and this separate opt-in5151 remain distinct; the4KiB
target and compatible NORMAL reuse are not completed by this policy.

# A fixed-two-worker output / individual stdio locking

Current selected fixed cost is **4525 B** (predecessor4541, −16 B). One ordinary
`--dev` and the unchanged selected verifier passed on this new native.
The pure shipping-only `shipping_output.py` follows the existing condition
stage: 3 exact regions,4 protected gaps (one empty),8797 complement bytes and
full inverse; source8886→8821. Strict completed-depth `>` keeps worker0 on ties.
The callback still holds qj through its single bestmove printf and fflush,
before completion/drain/root reuse. Canonical/DEV and the2-worker pool remain.

Removing the outer flockfile/funlockfile pair allows main puts/fflush between
worker printf/fflush. POSIX individual stream-call locking preserves each
single-call line; flush grouping/visibility/lock contention/scheduling and
signal/error timing are not claimed trace-equivalent. Source-only partial
create/epoch-wrap arguments remain distinct from selected observations.

The candidate literal is inverted to the original8886 raw literal, passed
through the unchanged condition→names literal guards, then forwarded again.
Old helpers/guards are unchanged; no external report/artifact is a builder
input. A remains `cc -Os` without `-pthread`,implicit GNU17 and fixed
ALONE6/BT2/16KiB/lc2/lp0/pb0/nice24/header73/FD0 template. Native18576 has
changed to5fd8f877…, bootstrap9775/c0662345…, whole4525/2ca28727…;
source-only HCE8874 is separate and not combined. A selected observer has no
FD-list observation; no FD-list claim is made. No full strength/performance
or general trace equality follows from this fixed-cost result.

<!-- A_FIXED_OUTPUT_COMPLETION:PASS -->
Ordinary build reproduced2 shipping and2 unchanged DEV tuples; source/native/
bootstrap/whole equal all four first-cost artifacts byte for byte. Selected
quit/EOF2 sessions completed8 legal GO with3 startup TIDs/session and actual
new native5fd8f877..., private-path/helper/readers/process physical exit.
Original command handles returned0, were reaped and their groups were absent
at settlement (no forced cleanup or late numeric-PID check). The A observer
has no FD-list observation. No exhaustive stdout-interposition schedule,
partial-create/epoch-wrap runtime, full-core/strength or timed speed claim is
added. Original selected cancellation causality remains unproven.

# Maintained A: shared fixed readonly flag template — 2026-10-22

The fixed first-cost file is **4541 B**, down9 from4550.
Bootstrap9850→9840 B removes10 bytes. Entire C,
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
`de45fc72cd6674589bd04903aa79275fadef2c9d4693dd8268c74cd894680d6f`.
Actual runtime SHA-256:
`ea596f92f20e723db6ca523b9f23b747ad7b7c7ceea0ab047d3749f9ac47abf7`.
All eight original command handles exited0, were reaped and had absent groups
at settlement; forced cleanup/owned handles0. No late bare PID/TID probe or
product retry is added. Producing recipe/source and final annotations remain
separate. After execution only recipe/README completion notes changed;
shared helper/builders/expected/profile/codecs stayed producing bytes.
Only the shared helper and A/B/C/E build/recipe/README are owned. No new
semantic fixture/SAN/NVC/game/codec search or rootdocs/Git/CI work is added.
Historical sections below retain their own identities and scope.

# Maintained A: shared condition object — 2026-10-22

The fixed complete candidate is **4550 B**, 9 B below A4559 and 454 B above
4096. Shipping C is 8886 B (-28), bootstrap9850 B and native18576 B. Native
length is unchanged but its full bytes differ; firstcost .text7346->7335.
The final A-only pure `shipping_condition.py` follows the existing destination
name stage. Three exact regions, four protected gaps and full inverse fix the
input/result. Canonical/DEV, all earlier helper guards, search/learners/TT,
two-worker/TT18 profile, no-pthread shipping compiler, implicit GNU17,73 B
header and BT2/dict16KiB/nice24 codec stay unchanged.

The two condition objects now share one. Actual notify3 sites remain
`pthread_cond_broadcast`, with signal0 and both original qj-protected while
predicates. Same mutex and while alone would not justify merging: broadcast
must include the intended controller/worker waiters even when another
predicate's waiter also wakes. A signal substitution could wake only an idle
worker at completion and is not allowed. Startup2->1 does not notify in the
current epilogue; only finalpending0 startup/completion broadcasts. Completion
result/flush stays under qj before broadcast and the controller's reacquire.
GO publishes pending/epoch under qj before broadcast; shutdown publishes
quitting and broadcasts. Late partial-create workers read quitting before
waiting; created-thread joins and epoch/null-startup marker stay unchanged.
Additional idle wakes, predicate rechecks, mutex contention, work/scheduling/
timing and condition-object address/native layout may differ. Partial-create,
epoch-wrap and other fault schedules remain source arguments, not new runtime
coverage or a many-core/performance/cancellation-causality claim.

The prior names literal guard is preserved exactly. A pure adapter inverses
the new raw-single source to its old fixed8914 source, invokes the unchanged
names guard, then applies the same3 edits only inside the guarded raw-double
body. Source/literal pins and full source inverse reject other inputs. No
external report/artifact/AST/compiler/codec is a normal helper input. Earlier
names-only native equality and source-token non-observation assumptions keep
their historical scope; they do not qualify this new native or liveness.

The ONE firstcost reused baseline compile0/encode0 and ran candidatecompile1/
encode1 with strictPython2/CLI2 exact source/compiler/bootstrap EOF/trailing
restoration. All original commands exited0 with empty stderr, reaped groups
absent and handles0. Baseline full bootstrap matched before compile/encode.
The source-only syntax preflight's report-brace typo was preserved separately
and corrected before any runroot/product execution. No firstcost replay,
make candidate composition, source/name/flag/codec search or new SAN ran.

One ordinary full `--dev` call reproduced shipping C/native/bootstrap/whole
twice, exactly matching the frozen firstcost tuple, and unchanged DEV source/
entire native twice. One unchanged selected verifier passed quit/EOF2 sessions,
8 legal GO, exact new native,3 startup TIDs each and private
restoration/helper paths/readers physical exit. Original build/selected handles
exited0, were reaped and left groups absent, with stderr0,forcedcleanup0 and
ownedhandles0. No normal retry occurred. These positive fixed-profile sessions
do not execute partial-create/epoch-wrap faults or prove cancellation causality,
complete concurrency/core coverage, many-core behavior, strength or performance.
Producing helper/build/expected/compiler/profile/header/codec remain unchanged;
final recipe/README only annotate the completed receipts.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C |8886|`d4132c23d226fa5490c5f213b3954ba6a9ce6f3f5f1a5594877a4d910685fe96`|
| Native |18576|`e00da92cdf1d6fdb7c7a6fbcaa5755bd6c1fd23942b28178f414716bd7e74471`|
| Bootstrap |9850|`5a40b94676ad5b1ba0046fdcee69815f2faf26ee798c86a86bdcbd3e88cca640`|
| Complete |4550|`257903ecc2313685da8194ecacdc90896ba14d28adcfbb1a91893009bc0068bd`|

Actual output: `/home/stemxstudio/rove4k-a-one-condition-promotion-20261022/normal/build`.
Build receipt `d5106d72123363df60c86330dde6eaabbffc3de85d0107083a60ace3ab2e6854`;
selected runtime `2730e1c1ad22ea12db2a2c2a18ab8a126648a4cd5e2d2885fcb85ecae5ff17a5`;
producing recipe `29ca7b4718bd7d272f0fd68620f982b824261fed70db911b7ec2a746021477dc`.
The unchanged fresh consumer discovers the extra helper from the recipe;
no fresh archive, shared consumer edit or extraction was executed.

# Historical A: private make binding and selected package — 2026-10-22

The selected complete file is **4559 B**, 10 B below qualified A4569 and
463 B above 4096. Shipping C remains 8914 B. `shipping_names.py` applies one
destination parameter rename in make `v`: `E*t` becomes `E*w` at 24 identifier
tokens. All 25 protected gaps (8890 B) and a full inverse are checked. Its
whole-function freshness preserves declarations/references, macro arguments,
member names and global calls. The existing GO function `w` is outside this
scope and is never referenced inside `v`. Board/type/alias/lifetime/dataflow,
rules/search/TT/learners/thread policy, canonical and DEV remain unchanged.

The complete 18576 B native is byte-identical to qualified A4569, not merely
the same size. The only new source spelling is the pointer binding; a separate
pure literal step emits the same C bytes as raw triple-double Python bytes
instead of raw triple-single. The 9878 B bootstrap retains all 956 B outside
the selected literal exactly. The fixed selected package is ALONE LZMA1,
preset 6 (extreme false), lc2/lp0/pb0, BT2=18, dict16384, nice24, CHECK_NONE and
the unchanged 73 B XZ_STDIN_HEADER. It is BT2, not HC4. Earlier package settings
are historical; the current recipe explicitly carries this selected tuple.

The single prepublication NVCompact0.6 run newly compiled baseline twice,
the improving candidate once and the final source once. All 4 actual native
receipts match the qualified full image and empty diagnostics; the retained
final image was read back against the qualified bytes without another
compile. Independent source review found no binding/capture counterexample.
Source/token/location/traceback non-observation remains an explicit
compile-input-only development assumption; AST and native identity do not
prove that assumption or new arithmetic/concurrency/core coverage. No new
SAN or large fixture was added for this names-only, identical-native change.

| Comparison | Whole bytes | Meaning |
| --- | ---: | --- |
| Original C/literal with original fixed codec | 4569 | Qualified baseline |
| Same C, raw triple-double literal,original fixed codec | 4568 | Literal choice saves 1 B |
| Renamed C, same triple-double literal,original fixed codec | 4567 | Binding choice saves 1 B more |
| Original payload with final codec | 4560 | Codec saves 9 B on original payload |
| Renamed C+double literal with final codec | 4559 | Current combined selection |

Thus fixed-objective source/literal selection saves 2 B and subsequent codec
selection saves 8 B on that selected payload. The 1 B difference under the
final codec compares original-single against renamed-double together; no
name-only crossed measurement under that final codec was performed.

The source run stopped at combination 8/8 with status budget-exhausted and
45/64 score evaluations, not a complete name-space search. It visited 5 singles,
encountered 3 incompatible subsets and left 18 nontrivial subsets unvisited.
Fresh reservations 2 are separate from actual retained seed 1. Source memo
events reused 1 cost and newly measured 43; baseline 1 and final fresh 1 complete
the 45 evaluation count. Global codec counters are separately 704 cached-domain
executions+2 fresh executions (source final cost and final selected encoding),
with 2 codec cache hits. No separate replay or second search ran.

One ordinary `build.py --dev` invocation reproduced shipping C/native/
bootstrap/whole twice, exactly matching the retained ONE-run candidate, and
reproduced unchanged DEV source/full native twice. The unchanged selected
verifier freshly ran the new wrapper in quit/EOF 2 sessions with 8 legal GO,
the exact restored qualified native, 3 startup TIDs each, removed private
restoration/helper paths,reader completion and physical exit 0. All normal
commands exited 0 and were reaped with their original groups absent; no timeout,
retry or forced cleanup occurred. Lifetime evidence comes from the original
supervisors/verifier, not later bare numeric PID lookups. Cancellation causality,
strength, performance and complete-core qualification remain outside this change.

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Shipping C | 8914 | `5319dd376e8e7fe6c03c6b40f6fc81b571902d75a663148ffbae00b615059c18` |
| Native | 18576 | `7700f1164da1b1a7ea8a784969742d1cf6d38a1f298986e41f564648ceaddf0c` |
| Bootstrap | 9878 | `04c1cdce33231ec62791905ab5e52560cb14d75e563dec0a60636ba7d9da032a` |
| Complete | 4559 | `ae756e0c014e32de6628ddeb54148d92e109731518a76a2eebb903daa96b27ce` |

Actual output: `/home/stemxstudio/rove4k-a-private-binding-promote-20261022/normal/build`.
Build receipt `923f668798a028e84e6bfe97a344c9cd7e124c876dc2fe86511bd498944a7e6d`;
runtime `23e389a3c5db19d2f2211d31faf84b9d73f3f69eea8ce600470947b5a005c957`;
producing recipe `2691cf5f0974c01c6fccb4f0511e9544b536b09c39342c3226f727fd4e0d8e3c`.
The source-producing closure has 34 ordinary inputs. Final recipe/README are
receipt-only annotations after that producing revision; source-producing code,
expected bytes and fixed codec are unchanged. No new first-cost or source/
codec search, archive/fresh, games, training, AWS or performance run was added.

# Historical A: shared terminal legality loop — 2026-10-22

현재 일반 생성 경로가 **4569 B whole**, **8914 B shipping C**, **18576 B native**를
두 번 재현했다. qualified A4580 대비 소스51 B, 제출 파일11 B가 줄었으며 아직4096 B보다
473 B 크다. native 길이는 같고 실제 바이트는 달라졌다. 현재73-byte header, compiler,
ALONE codec와 profile은 이번 비용 비교의 고정 조건이다.

- C SHA-256: `597d01d9cece4762880cc4a4c8c3a5329125ca76cb4b92eba6c31da3231c683a`
- native SHA-256: `7700f1164da1b1a7ea8a784969742d1cf6d38a1f298986e41f564648ceaddf0c`
- bootstrap9878 B SHA-256: `2291ecc835ddbb268d8e4ac12b5735610d8db519440e05ae77538a9e58b3f32c`
- whole SHA-256: `484d8b81b24bf0c6b11427b3224aca91226417f7edc909a995c25753f04675cf`

A 전용 마지막 `shipping_terminal.py`는 cached evaluation과 worker epilogue 뒤에서
기존 draw/ply-cap의 별도 합법수 검색을 일반 정렬 루프와 공유한다. 네 개 고정 치환과
다섯 보존 구간, 전체 inverse가 입력8965 B/출력8914 B를 고정한다. t=0/1/2/3은
ordinary/draw/cap-only/both를 나타낸다. terminal은 TT probe를 억제하고 첫 make 성공
직후 반환해 legal-count/path/root/재귀/learners/TT 쓰기에 도달하지 않는다. 기존
claim-node 증가는 유지하며 cap-only만 stop을 설정한다. 합법수가 없으면 원래
mate/stalemate가 draw/cap보다 먼저 결정된다. 기존 stop/deadline 검사가 먼저다.
canonical과 DEV, 다른 가족의 구현 및 이전 단계는 보존한다.

집중 검증은 실제 old/new h 본문을 사용했다. 새 full TU는 바꾸지 않았고 old h는 선언과
네 개 자기 재귀 호출의 이름만 바꿨으며 전체 inverse와 본문 밖 동일성을 확인했다.
한 번의 fatal ASan/UBSan compile/run에서18개 사례가 통과했다. draw/cap-only/both,
합법 quiet/capture, mate/stalemate, dead/threefold, 기존 stop/deadline, terminal의
poisoned exact/lower/upper TT escape를 확인했다. 일반 PVS는 독립 HCE/quiet-child
oracle, exact TT, full HCE-QS, quiet learning cutoff를 확인했다. score/stop/root/node,
typed board, 전체 path/job keys, 세 learner 배열과 full TT key/data/clear flags의
old/new 비교 mask는0이었다. terminal의 초기 seed 대비 허용 변화는 claim-node 증가와
명시적인 cap-only stop뿐이며 path/root/learners/TT 불변 assertion이 통과했다.

terminal에서 이제 scoring/sort를 수행하므로 첫 private child, 추가 읽기와 keymix,
공격 작업 순서·작업량·시간·stack peak는 달라질 수 있다. 이 private 작업은 비교 대상에
넣지 않았고 외부 상태를 광범위 정규화하지 않았다. 동일 native, timed-node/성능,
strength, peak RAM 또는 일반 race freedom을 주장하지 않는다. 실제 direct-call 집중
검증과 아래 selected wrapper의 관측 범위도 구분한다.

일반 `--dev` 빌더 한 번이 shipping tuple을 두 번 재현하고 기존 DEV source/native를
두 번 동일하게 재현했다. unchanged selected 한 번은 새 native로 quit/EOF 두 세션,
합법 GO8개를 마쳤다. 각 startup TID3개와 완료 GO 뒤 안정성, active quit/EOF의 합법
종료 결과 각1개, wait return0/process 부재와 reader 종료가 원 영수증에 기록됐다.
cancellation의 인과관계는 미증명이다. partial-create/epoch wrap/강제 wake/queued GO/
active position 교체는 이번 추가 실행 범위가 아니며 해당 source 검토와 구분한다.
DEV 엔진 runtime, first-cost 재실행, 추가 focused 실행은0이다.

원 producing recipe는 `c2368b74eba756d2a523e6027b48692ea5809ed38eab5bd4c0b559ac221dda2e`다.
생성에 사용한4파일을 외부 `producing/`에 보존한 뒤 recipe의 현재 receipt scope와
terminal receipt, 이 README의 현재 섹션만 완료로 갱신했다. helper/build, expected,
helper map과 generation input은 그대로다. 생성은 canonical/고정 helper/recipe만 읽고
외부 보고서나 fixture를 읽지 않는다. 과거 실패와 이전 단계 영수증은 각 원래 범위로 남긴다.

- focused final index: `C:/Users/강민수/Documents/Codex/rove4k-a-terminal-loop-focused-20261022-evidence/final-index.json`,5432 B / `f5dee98cefaf862dc1acd492980b01576e26d61a0e5cc87cbd45c23d69da8a80`
- normal/selected final index: `C:/Users/강민수/Documents/Codex/rove4k-a-terminal-loop-promote-20261022-evidence/final-index.json`,7288 B / `1118be88dcfaadfc9d42e1cbae3402bc1a3c7f9ea8ed6a17e7204850b8bcfd5b`
- actual build receipt:188698 B / `b8c45eb404085d66ad43737fddd241330018bc6129fcbcaeb75fd980a3127cf4`
- actual selected receipt:50102 B / `8b13597a78fa65bdeada3ec79c24dc297d3730d2db85b72d63a4527bae643d7e`

물리 종료는 원 owned command의 communicate/wait·terminal/reap·그 시점 그룹 부재와
selected의 자체 수명 영수증에 근거한다. 늦은 숫자 PID/TID/PGID 재조회는0이다.
변경하지 않은 compile helper에는 compiler 자손의 별도 수명 관측이 없다. 로컬 승격
범위만 완료하며 현재 CI/main/release나 A–F 전체4096 B 달성을 주장하지 않는다.

# Maintained A: shared worker epilogue — 2026-10-22

The ordinary producer now reproduces **4580 B** complete,**8965 B** shipping C
and**18576 B** native:22 source bytes and2 whole bytes below qualifiedA4582.
The new native has SHA-256
`d97930cd8a93f6a0a38f87fbbeff79c453a1b402f8124b29de1c8c0169e53634`;
its length equals its predecessor but its bytes differ. Whole SHA-256:
`373c3c6a3fb5d7b600bc9817b4549b0056a58b5d8c11882d000e10eba21d509b`.
It remains484 B above4096. The current73-byte header,bootstrap envelope,
compiler,codec,profile,search,learners,TT,rules and protocol remain in scope.

The A-only final `shipping_worker_epilogue.py` shares startup arrival and
completed-job reporting at the worker loop head. One308→286-byte region has
exact input/output pins,full inverse and two protected gaps. The existing
local worker pointer is null only at startup; every accepted dispatch sets it
to the existing nonnull worker argument before think. It stays nonnull across
completion and is independent of unsigned epoch wrap. Canonical/DEV retain
their existing worker function and exact source/full-native identities.

Startup finished broadcasts change2→1. The intermediate pending2→1 arrival no
longer notifies main; final pending1→0 readiness still does. This changes private
wake/interleaving timing. Job completion still decrements once per think; its
last worker calls result under the mutex before the final wake and before main
can pass its drain mutex. The original pending predicate,root/history lifetime,
epoch publication and created-thread join contracts are retained by source
review. This is not an identical-native or notification-count-preserving claim.

One ordinary --dev builder reproduced shipping source/native/bootstrap/whole
twice,exactly matching the first-cost candidate,and reproduced unchanged DEV
source/full-native twice. The unchanged selected verifier ran the actual new
wrapper in two fresh sessions. Each session observed3 startup TIDs,three
completed white-zero/black-zero/bare-finite GO epochs with exactly one legal
result and stable TIDs,then an observed-active epoch closed by quit or EOF.
Both closing epochs produced exactly one legal result,exit0,reader EOF,absent
process/observed descendants and removed restoration/helper paths. The original
owned command receipts record communicate/wait completion,terminal state,
group absence and handles0,with no forced cleanup. These own-lifetime receipts
are the physical completion evidence; a later numeric PID lookup is not a gate.
Build receipt SHA-256:
`a2ceb3096e1afd0985f91f35be6fdd46a7f2a582a28f560ce92e49cfc5242a86`;
runtime `c1c182308bd7d5bfce0fc4232c28f92a326dfd89f177d668b714d410701c2c2b`;
final index `126bf6de6e37a3269e8d72affed206b1818c9748ec53965059df97101b501082`.

Producing recipe `a931b6da2cd1c2d65dd66bd0e47020cebaeaf60007b00a2f2c48b861b511eef5` and all four
producing files are preserved outside Git in
`rove4k-a-worker-epilogue-promote-20261022-evidence/producing/`; this completion
changes recipe/README annotations only. No first-cost reexecution or additional
source search was performed. The original GAIN2 cost/source proof remains in
`rove4k-a-worker-epilogue-20261022-evidence` with its original hashes.

Partial thread creation failure,unsigned epoch wrap,forced spurious wake,
blocked result output and join-failure schedules remain source-reviewed or
unexercised,not fresh runtime coverage. The old controlled startup fixture
infers each arrival from its perworker finished broadcast; that hook is
unsuitable unchanged after the accepted notification change,so its historical
result is not reused as a fresh run. Selected verification did not invoke
queued-GO or active-position-reset scenarios. Cancellation causality remains
unproven. DEV runtime,new fault/strength/performance/many-core campaigns0;
the unchanged compile helper has no separate compiler-descendant lifetime
record. Older sections below retain their predecessor evidence domains.

# Maintained A: shared73-byte header — 2026-10-22

The selected complete file is **4582 B**, four bytes below A4586 and486 B
above4096. Its8987 B C,18576 B native,9951 B bootstrap and exact DEV tuple
remain unchanged. The only output change replaces the77-byte shell header
with `source_package.XZ_STDIN_HEADER` (73 B); all existing compressed payload
bytes and the compiler/codec/bootstrap remain identical. The generator freezes
and imports that shared constant after validating the legacy template marker
and77-byte input. Its existing encoder is retained.

`tail -n+4` skips exactly three header lines; piped `xz -d` restores the same
ALONE bootstrap. Decoder failure still exits, command substitution retains the
same trailing-newline behavior, and Python argv/exec are unchanged. The old
local launcher remains an ordinary legacy input. Exact old/new bounded ALONE
restoration binds the unchanged bootstrap; its source/argv/core proofs are
reused by identity. This is header packaging, not source/native compression.
The new whole SHA is
`7695d824549f10139fa740709e04c8e56934e643dc739def9bb1239631c97347`.
One ordinary --dev call reproduced shipping and the unchanged DEV tuple
twice. Its complete outputs equal the exact header-only substitution, with
the original compressed payload intact. One unchanged selected verifier
passed quit/EOF2 sessions8 legal GO, exact restored native, persistent3
startup TIDs, private-path/helper/readers cleanup and physical exit0. All
outer commands exited0, were reaped and left their groups absent. No
runtime failure or retry occurred. Generic signal/descendant/fresh/core/
game/strength/many-core coverage is not added by this packaging change.

Build receipt `83bbec21c8c19f617ab9d2d73c1a2d689996be71a5e36ad9d6577d5c4b2ef82a`;
runtime `cbbd2aaf3b84a4181cdc003ec375f5484ae4a375854e17dd67e44a5a3cc00cd1`;
producing recipe `92bc2a18e36bfbb1b24c458cef045da11552655ab652b3487e8d153bb97037af`.
Producing closure 37 ordinary files. Final recipe/README are receipt-only
annotations; source-producing code and expected artifact bytes are unchanged.

# Historical A: cached correction evaluation — 2026-10-22

The current complete file is **4586 B**, with **8987 B** compact C: 1 whole
byte and 8 shipping-source bytes smaller than the preceding 4587 B entry.
Canonical search now computes `error=best-evaluation`; fixed shipping uses
`S=H-F`. Both reuse the raw signed-int static evaluation already computed
for that search frame. TT score normalization and correction-based LMR
eligibility do not change this value. HCE, all learners, TT, LMR, worker and
memory policies are retained. The readable canonical grows one byte because
its descriptive local name is longer; the emitted compact C saves eight.

The pure A evaluation adapter derives the exact older readable reference
preimage for existing pinned spelling stages, then restores cached evaluation
at the final shipping boundary. The profiled DEV source also uses cached
evaluation and has a genuinely new source/native tuple; old DEV byte equality
is not claimed. Existing stage metadata describes their reference inputs.
No artifact, runtime receipt, codec or external source is a generation input.

Focused old/new direct-call searches pass at START depth1/depth4 and a black
root after e2e4 depth4 with a nonzero prior correction. Actual correction
updates/uses are 1/0, 21/17 and 16/17, with zero raw-evaluation mismatches.
Scores, best moves, nodes, keys, complete learner arrays and every TT key/data
field compare exactly in 12,789,906 bytes of logical snapshots. Every recursive
search checks its input Board's logical fields unchanged through return.
This is deterministic single-worker evidence, separate from the source review
of production root lifetime and pool drain.

The first Clang18 UBSan compile failed at link because the standalone runtime
archive is unavailable; the original failed command and diagnostic are retained.
The successful focused build uses Clang18 `-O1 -fsanitize=undefined
-fsanitize-trap=undefined -fno-sanitize-recover=all`, so exercised compiler
undefined-behavior checks terminate fatally without that runtime archive.
This covers the exercised normal inputs, not all arithmetic or concurrency.
Focused receipt SHA-256:
`88adec67adf9fc91996866ae4a1960b348c0b17459f7c2b4dc2f5c1fd4f56835`.

One ordinary `--dev` builder reproduces shipping and the new DEV tuple twice.
The unchanged selected verifier passes two quit/EOF sessions and eight legal
GO results, three stable startup TIDs per session, exact restored native,
absent private paths/helpers, reader EOF and physical exit0. Outer successful
groups are reaped and absent, with no forced cleanup. Build/runtime receipt
SHA-256 values are respectively:
`63f731846fe0f712e3af83e0e284cfb3683f6b450e25ceb1c4f1067429feec1e`
and `1d16ccccf45a741b86d4d3c829c110ef6bd6ee249fea9d6481e82962ea1644d8`.

Current source SHA-256:
`4fd5231ace3db9f7d8aca8c2e26871895905cd3e77cb38e4b41117bdca4f31d8`.
Current whole SHA-256:
`db6eaf173b985fcfa974af537a5bcfe4dafa3c696b3d1b68a5209204b46c2f58`.
Evidence and the producing pre-annotation recipe remain outside Git in
`rove4k-a-eval-cache-promote-20261022-evidence`; the original fixed first-cost
is preserved in `rove4k-a-nv060-source-20261022-evidence`. Actual NVC0.6 advice
was incomplete and withheld search analysis for AtomicExpr; candidate proof
comes from the source review and focused comparison, not tool certification.
These local fixed2/TT18 results do not establish strength, many-core or final
target acceptance. Cancellation causality remains unproven. Older checkpoints
and their validation scopes are retained below.

# Maintained A: lazy first-legal fallback — 2026-10-21

The fixed first-cost candidate is **4587 B** complete and **8995 B** compact C,
saving5 whole bytes against4592 and16 raw C bytes against9011. The final
shipping-only source stage removes the global fallback and its eager GO
scratch/query. Result aggregation retains the deepest completed worker and
the existing first-worker tie; only a selected zero best invokes the unchanged
pure legal query on the immutable root. A terminal root still renders0000.
Canonical and full-reference DEV source/targets remain unchanged.

The callback remains under the pool mutex after all think calls return. Main
cannot reuse the root until wait returns, and result output/flush still
precedes the completion broadcast. The query runs after the recursive search
frames unwind. Whole-worker stack peak is unmeasured. Removing work after
deadline setup and moving conditional query work before output changes work
timing; exact elapsed time, searched nodes and search-result identity under
the clock are not equality claims.

The five-context portfolio measured one fixed compile/encode per candidate;
its actual cost receipt SHA-256 is
`b9613dd993cfab433a479a43b80d8f1b4457f9cbe6147418661f5ca876d2276a`.
This A source has three changed regions, exact inverse and four protected
gaps. It has a new native identity. One ordinary --dev builder reproduced
shipping twice and the exact old DEV source/native twice; the unchanged
selected verifier passed quit/EOF in two sessions with eight GO results,
three startup TIDs each, exact restored native and physical process/reader/
private-path exit. The producing build and runtime receipt SHA-256 values are
`2b9986c5699684ad0b3090395bdc511f36ceaebe460601524163c231bdb9ba5b`
and `3b0f154c8ed3d30675e5262d0a964231eb2c0ac2f843dea96910e8d8db4ddbd6`.
These local fixed2/TT18 results do not measure whole-worker stack peak,
clock equivalence or cancellation causality; the latter remains unproven.
No new strength, many-core or final-target acceptance is claimed.

Expected source SHA-256:
`a52d492bcdfe623863153b9d5d651c6218fa1511e3253c3d6efe80b81c017101`.
Expected whole SHA-256:
`f84d4ab2140e15b94d420456d4f65fa55afeb23313a08aa282d88f26de7ad2c0`.
Before/producing records remain outside Git in
`rove4k-common-lazy-fallback-promotion-20261021-evidence/A`. The older sections
below retain their original checkpoints and validation scopes.

# Maintained A: derived private history length — 2026-10-21

Complete file **4592 B**, compact C **9011 B**. The final A-only shipping
stage derives the private history cursor from immutable job length plus
caller ply, removing the Worker field/reset/push-pop while retaining the
same repetition indices and child key writes. Raw C saves29 B; actual
whole saves14 B against4606. Worker layout and native identity change;
old native equality is not claimed. Canonical and full-reference DEV
sources remain unchanged. HCE/PVS/QS/full contextual TT/learners/SMP,
rules, input, clock and resource policy stay in scope.

One fatal ASan/UBSan compile/run compares actual old/new logical score,
best, nodes, keys, all learners and TT fields through bounded history,
window, cap, early-return and stop states. The four-call/push-pop
relation is source-proved; runtime PVS retry branch coverage is
unmeasured. Raw Worker padding/removed fields are not an oracle.

One ordinary --dev build reproduces shipping twice and the unchanged
full-reference DEV twice. The unchanged selected verifier passes the
new actual wrapper through2 quit/EOF sessions and8 legal GO epochs,
exact new native restoration,3 stable startup TIDs, absent private
paths/helpers, closing result, reader EOF and physical exit0.
Cancellation causality, runtime retry-branch coverage, final target
resources/many-core behavior and strength remain unproven.

Build receipt SHA-256: `17456fe64b6979b6760401d66a3c5942041e3c010b138d30a6c3476bd2b1420f`.
Runtime receipt SHA-256: `c17c63be4ad499dd9f9193644add32e2cb5c44051ddae76a5aac55689a99d2fc`.
Current whole SHA-256: `8117ab93e0074558618374b1897cdf1a2a1903abbab4e395d22e078035643864`.

Producing/before sources and receipts remain outside Git in
`rove4k-a-history-depth-*-20261021-evidence`. Older sections below
retain their original checkpoints and validation scopes.

# Maintained A: compact environment snapshot — 2026-10-21

Complete file **4606 B**, compact C **9040 B**. The single
env constructor expression saves6 template bytes and 4 actual whole-file
bytes against the preceding 4610 B entry. `dict(os.environ,TMPDIR=d)`
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

Build receipt SHA-256: `fff866130bfdc1b7dccdd07b2d89a63d063b41ce61f0f73b574037ce7a679898`.
Runtime receipt SHA-256: `9541f7a84c33e30a48a95295892eadd8412f7ca24015b115e8ac8da84d3dceb3`.
Current whole SHA-256: `0046ceec156bd67bac6ca29a32eda93a8b4a3bffbb8546faa1b398568b6cb900`.

The producing recipes, actual receipts and pre-annotation sources remain in
`rove4k-bootstrap-env-normal-20261021-evidence`; original costs and source
forms are preserved in the source/optional-cost evidence folders. Historical
sections below retain their own images and scope.

# Maintained A: compact clock presence — 2026-10-21

Complete file **4610 B**, compact C **9040 B**.
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

Current source SHA-256: `624ad8a28a9d555fda37efa82b468fce09f98d4c5b86b20739ee2e6f589ff5a8`.
Current whole SHA-256: `aebb5005720b1793d1bc963c59b73ae481f857a3565172fe3946fae2b0f57bc0`.

Local two-worker/TT18 checks do not establish final target resources,
many-core behavior or strength. The full A–F goal and compression beyond
size passage remain active. Older sections retain their checkpoint identities.

# Maintained A: smaller plain-Popen cleanup guard — 2026-10-21

Whole **4613 B**. The current template/script loses12 raw bytes
by testing the fixed plain Popen/None value directly. Poll, cleanup, signal mask,
compiler argv/C input, private path, descriptor exec and physical lifetime
operations remain unchanged. C source/native are entire-byte unchanged.

All seven selections regenerate --dev twice and pass unchanged actual selected
quit/EOF verification. This is local2-worker/TT18 evidence, with no new general
descendant cleanup, startup-fault or strength guarantee. Normal summary SHA-256:
`90e45a020a55ef5a3ff6af78dfa42908eb8625395fe5c991d860bde8d34b2ff6`.

Current source SHA-256: `d1d490074754c3468785b1cd7f8f3c841f3ed1115933003fcc06edc5314e452c`.
Current whole SHA-256: `e342aa55609cbb4a50ad59bb982ff5e749fb06b7ab823bff3904cbaa492ae1d6`.

Older sections retain their original checkpoint identities.

# Maintained A: final literal/poll compaction — 2026-10-21

Current whole **4619 B**, source **9052 B**.
Fixed LP64 large mixer hex literal wrappers omitted; values/types and the entire native image remain unchanged.
All full family features and DEV bypass remain. Final transforms operate on
separate reference copies where needed; raw policy preimages stay unchanged.

The ordinary --dev builder reproduces shipping and full DEV twice, and unchanged
selected verifiers pass actual quit/EOF, restoration, legal finite GO and physical
exit. Local2-worker/TT18 only; final resources and strength remain open. Final
normal summary SHA-256:
`af00002687cf6ed0d84f2e85f21169d381bb1cd8721005c05cc87a4fabe2bb96`.

Current source SHA-256: `d1d490074754c3468785b1cd7f8f3c841f3ed1115933003fcc06edc5314e452c`.
Current whole SHA-256: `e9a4e3110aabe23dc1c0d3da7f2abc5578f09bb4801c535188fe7a6793685231`.

Older sections retain their original checkpoint identities.

# Maintained A: integer source compression — 2026-10-21

The late fixed integer pass uses the existing unsigned64 alias and high-bit
decimal bound, retaining digit/end-pointer checks, clock consumption and all
budget clamps. The unused final limits header is removed except for C,
which has a later intrinsic include. Full/material F also omit two fixed
positive TT18 casts. Actual composed costs are used, not added deltas.

The entire native remains byte-identical to the previous maintained image;
no model, learner, search, rule, TT or worker feature is removed.

| Policy | Previous whole | Current whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| A | 4652 | **4628** | 24 | 532 |

Each normal --dev build reproduces shipping and full-reference DEV twice.
The unchanged selected verifier passes new actual quit/EOF wrappers, exact
restored native, stable3 TIDs, legal finite GO, private-path/helper absence,
closing result, reader EOF and physical exit. Normal summary SHA-256:
`1de4261cbd87622c9326fe8c72137b0d96148fb4e1514b2c81e8dbda4031a2a5`.
The local2-worker/TT18 profile does not accept final resources or strength.

| Policy | Source bytes | Native bytes | Whole SHA-256 |
|---|---:|---:|---|
| A | 9082 | 18576 | `6ef884d6d72c0bd46d8511e6843abd9fb006ce881c48cc6a06105a1ef60f71d8` |

Older sections retain their original checkpoint identities.

# Maintained A: shared material-state compression — 2026-10-21

A shared late source pass replaces three material-classification accumulators
with one signed state, preserving the existing limited policy. Bare kings
and a single minor remain dead; KNN stays live. Bishop-only minor sets are
dead when confined to one square color. Full models/search/TT/
learning/rules/input/pool remain outside the one-function edit. This is not
a general theoretical dead-position oracle. Raw source grows18B per policy,
while actual complete-file cost decreases; independent deltas are not added.

| Policy | Previous whole | Current whole | Saved | Above4096 |
|---|---:|---:|---:|---:|
| A | 4661 | **4652** | 9 | 556 |

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
| A | 9125 | 18576 | `fd7307213f35a16b111854125ec028e1fc4c07d0042bb0e5421976c8de244f20` |

Older sections retain their original checkpoint identities.

# Maintained A: qualified source refinements — 2026-10-21

Main alone now owns one strtok cursor; private POSITION/GO consumers use nt() and do not resume a parent token stream. The promotion predicate is shortened only for generator-admitted valid 0x88 destinations.

| Policy | Previous whole | Current whole | Saved | Above 4096 |
|---|---:|---:|---:|---:|
| A | 4674 | **4661** | 13 | 565 |

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
| A | 9107 | 22672 | `5adf7890d90114a0c7bc10f81394727b674b289a8d9421e48993c43d2be84c47` |

Normal summary SHA-256:
`cc82bacb31cfd8fb020fa375a3a1d1b3ece7ac2991dc7ebcf2c7ed772e3d230e`.
This frozen summary binds producing inputs before subsequent receipt-only
recipe annotations. Older sections below retain their original identities.

# Maintained A: shared final shipping reductions

The final `engines/scripts/shipping_common.py` pass removes the sole unused
empty `TINY_H` definition after all existing family stages. A/C/E also omit
two redundant fixed-TT18 casts. ASCII source uses a raw bytes literal in the
unchanged bootstrap; every previous non-ASCII/CR/NUL/quote/backslash fallback
and the historical `pack_stream.py` API remain unchanged.

| Policy | Previous whole | Current whole | Saved | Above 4096 |
|---|---:|---:|---:|---:|
| A | 4689 | **4674** | 15 | 578 |

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
| A | 9224 | 22672 | 10206 | `060ebae3049c62f1a237a5a264029465eee6e518d510aba042a4ccfb2ffb5461` |

Exact source/bootstrap/native hashes remain in `recipe.json`. External normal
summary SHA-256: `4c2bc987c0947387ebe688ac76c7b91f41d1458149278e490638fb1428f7469f`.
Generated artifacts and reports remain outside Git. The following sections
describe earlier checkpoints and retain their original validation scope.

## Previous: Maintained minimal A entry

The selected complete launcher is **4,689 bytes**, one byte below A4690 and
593 bytes above4,096. The final `shipping_continuation.py` stage reuses the
existing successful-child piece index only in the positive-depth quiet-cutoff
continuation update. Source9265 becomes9256 (−9); native length22672 and
.text7538 are unchanged, but actual machine-code bytes and full native identity
change. There is no predecessor-byte equality or metadata exception.

| Selected artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C |9256|`c5e2d2994ea12df6df8b3152c2c89a00f787ee03ae09b1d546c9082145b5c56d`|
| Full native |22672|`2190f140858effe734abacac7b03b5794ba5e4d0677620a4da50e170016eaecb`|
| Decoded bootstrap |10246|`7756248004a458a7012276799522b25333b876b541f4fabbd78c68c42ee66823`|
| Complete launcher |4689|`e1e3386c21412c1530a5f9c747679312661243fe522db33eb437728bc5b63749`|

The one expression `w->an[f][s(p->b[o])]` becomes `w->an[f][R]`.
R was already computed as `s(q.b[P])` after successful make, before recursive
search, and is not reassigned. The cutoff's !Q excludes every promotion,
including quiet promotions whose capture bit is0. Successful nonpromotion make
puts the same moving piece on the destination; castling moves the same king and
handles its rook separately. The same continuation cell therefore receives the
same learning call. No search signature/state, arithmetic, history/correction
policy, HCE/PVS/QS/full-key contextual TT, SMP, clock or resource contract is
removed. All remaining source bytes, canonical readable C and DEV are exact.

The ordinary helper admits only the complete9265/06ca input, one20-to11-byte
literal, its child-index/cutoff context, exact inverse and9,245 protected bytes.
It follows globalnames for shipping only, with no experiment/report/AST/native
artifact input. Expected new native identity is strict. A original compiler,
bootstrap/prefix and original ALONE defaults remain unchanged; no F nice32
settings are introduced. The fixed cost reproduced the complete4690 control
before compiling one candidate, packaging once and strictly restoring both via
PythonEOF/source/template/argv and independent CLI DATA decode. Whole−1 and
rawsource−9 are separate measurements. Previous rejected put/HCE/material-cache
or futex candidates are not combined.

Focused positive proof includes actual old/new shipping h/O with reversible
root-cutoff before/after observers and renamed, uncalled product main. Legal
knight/pawn/king quiet moves and both castles exercise five actual updates;
N/B/R/Q quiet promotions and one capture promotion exercise five excluded paths.
Entire history/continuation/correction arrays around each cutoff match the
oracle, and both executables produce identical score/best/nodes/full learner
observations. Two diagnostic ASan/UBSan compiles and runs passed. This is bounded
single-thread depth3 evidence, not a shipping image, pool/SMP or strength proof.
The initial unexecuted preparation sources are preserved; feature-header order
and bounded runner settlement were fixed before any compile or run.
Actual focused receipt:
`ae230de58519c98a3ae86c2e6a28083a23ce59da9770871a969a28e147430b5a`.
Names/type/local stages and all learner features remain independently required.

The predecessor26 source and actual4690 controls, including its producing
recipe, are preserved outside Git. Producing source27 was frozen before the
sole ordinary --dev invocation: shipping source/native/bootstrap/whole repeated
twice exactly match the fixed cost, and unchanged DEV source/native repeated
twice. The sole unchanged selected verifier completed the actual4689 wrapper in
quit/EOF two sessions and eight legal GO epochs, observing exact restored2190
native, three stable startup TIDs each, removed private paths/no helper children,
active closing work, exactly one closing result, finished readers and physical
exit0. All observed TIDs are absent. Both outer commands were reaped rc0 with
pipe EOF and absent groups, forced cleanup0/handles0. Build receipt
`da911e6bd262fac92809b384ec3052e207e963478794ce5b89fc87de449a69b1`;
runtime receipt
`24c67e8cee5dd46b734f4086d1ff3931a0b443e97b4183a96c7d1127819054c8`.
Only README and receipt metadata changed after execution; all other25 sources,
expected/native pins, compiler, codec and helpers retain producing identities.
Cancellation causality and the unchanged compiler-descendant lifetime limit
remain unproven. No fresh, DEV engine, broad core matrix, game, performance,
training or negative campaign followed. Historical receipts below retain their
earlier image/source identities; they are not relabeled as new2190 executions. No4KiB, speed, playing
strength or broad equivalence claim follows from this one-byte saving.

# Historical A4690 global-function spelling stage

The selected complete launcher is **4,690 bytes**, 26 below A4716 and
**594 bytes above4,096**. The final `shipping_global_names.py` stage follows
startup, shortening 28 owned global function names at 105 physical declaration
and reference spans. Source9370->9265; the entire22672B native is identical to
its predecessor, without a metadata exception. Source bytes are not whole
bytes. No4KiB, playing strength or broader target claim follows.

| Selected artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C |9265|`06ca0bc2871c2b1a8ce1eeccc24d65680bbc874066498db6e0c295af89003a46`|
| Full native |22672|`47ec496697134d91a4efb71e14441e5a542df93278c64a2dfdcf1e7eec0de9dc`|
| Decoded bootstrap |10255|`c8f790266aa38f727c6d4ca3099a96321bdd1931449836f1d7509ee2ec3c2e7c`|
| Complete launcher |4690|`c72f691a64c4813e4c988a5f5b3b7ddfa069c3e936ba4756862eb090eb588d78`|

The helper owns exact full input/output pins, one fixed28/105 map, physical
identifier inventories, exact inverse, protected complement, directive and
opaque guards. main/header/external references, objects, types, members,
capture-only bit3/FROM119 and the existing PROMO(N) lexical bridge remain
unchanged. Eight definitions retain C external linkage kinds while their
program-owned implementation names change inside the closed standalone TU;
these names are not an external symbol API. No AST/experiment/report/artifact
dependency is used in normal generation. All old guards run first. DEV bypasses
this stage and retains its preceding source/native tuple. Compiler arguments,
resource profile, bootstrap/prefix and the original A ALONE defaults remain
unchanged; no F codec settings are substituted.

The source-only proposal is ce4d72fca0153a8c5f8adf54bb9d950919024180aa3b174e13db2ab27daec05b.
Fixed sequential ABCE cost receipt is
e192da7467cbf2dfa950bf50f3127d45e684ef7c484c110bd2a86ccb1d8899c2.
Its sole A candidate compile reproduced the full predecessor native. Original
whole/bootstrap reproduction and strict Python/CLI source/template/argv
restoration passed. This cost ran no target/bootstrap/engine/loader.

Current ordinary25 and A4716 controls were preserved before mutation.
Producing source26 was frozen before the sole normal --dev invocation. Shipping
source/native/bootstrap/whole reproduced twice, and the preceding explicit
DEV source/native tuple reproduced twice. The unchanged selected verifier
completed once: quit/EOF2sessions8legalGO, exact restored full native, three
stable startup TIDs each, private-path/helper absence, active closing search,
exactly one closing bestmove, readers finished and natural physical exit0.
All six observed startup TIDs are now absent. Both outer groups terminated0
and were absent; there was no normal retry or forced cleanup.
Build SHA228cdb10e989005f72e0e22d38abae01c6c5d9816c20d8a0b9da5b4d0bd16186;
runtime SHA7d68692df6dad32647e67ddb898eeb775337a46b4812a28b06435361121c3881;
readback SHA3e34dae7dc503701bfeedbead0f5f6c021cdce947b35c2b285f0646405f3a484.
Producing source26 SHAafae93c1bdcaa564a11c3db7545a00627c4480ef9398ac58c142f6bbcabffb15;
producing recipe SHAbd2d463ada9e6fcb3e5f72e726c529df26ea3a2468d735ea33e02fd1970fbb89.
Only README/recipe completion metadata changed after execution. Other24 source
paths and helper/expected/compiler/profile/codec remain producing bytes.
Unchanged fresh.py would discover26 ordinary sources; no fresh extraction ran.
Cancellation causality and the unchanged builder's separate compiler-descendant
lifetime observation remain unproven. No DEV engine, new core fixture, game,
benchmark, training or negative campaign was added. Historical receipts below
remain predecessor executions, and Git/CI/project acceptance remain root work.

# Historical A4716 startup-zero stage

The selected complete launcher is **4,716 bytes**, 11 below A4727 and
**620 bytes above4,096**. Sole normal --dev regeneration and unchanged selected
verification both passed at their first invocation. Expected pins remain the
literal reviewed first-cost values, never refreshed from output. The preceding
4727 producing/final sources and actual normal receipts stay closed and preserved
separately. No4KiB acceptance, playing strength or broader target is claimed.

`shipping_startup.py` is the last shipping-only stage after capture bits. One
fixed clear-function literal removes redundant unsigned key/data zero stores
and the now-unneeded loop braces: source9391->9370. The helper guards exact
old/new hashes, canonical readable identity, one region/inverse,9,282 protected
bytes, exactly2 aX occurrences (definition+sole caller), one calloc and one
pthread_create site. The sole main caller follows successful fresh calloc and
precedes worker creation; no later table-reset consumer is admitted.

calloc gives all-bits-zero storage, and W is unsigned exact-width uint64_t, so
the two TT key/data fields already hold value0. Every explicit per-entry
atomic_flag_clear remains in its original order. This theorem concerns fresh
startup only; it is not permission to omit atomic_flag initialization or clear
an existing populated table. The native image changes. The capture fixture
still belongs to its exact9391-byte source; it is not relabeled as execution of
this new image. Board/search consumers are in the unchanged complement.

The helper reads no files and imports only hashlib. All prior canonical,
spelling, scope, input, type, lexical and capture guards remain unchanged.
It is pinned and frozen before import; DEV bypasses it and must reproduce its
prior explicit source/native tuple. Unchanged fresh.py now discovers25 ordinary
source paths; no fresh extraction or new core fixture is part of this stage.
Canonical engine, verifier, bootstrap, launcher, compiler/resources and original
ALONE profile remain unchanged. There is no experiment, evidence, artifact,
AST/library, external source or network dependency in normal regeneration.

| Current observed artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 9370 | `7dc2243e255e2b191e4bb7785826c69556c45534ed4c1832796ccdca637d4f55` |
| Full native | 22672 | `47ec496697134d91a4efb71e14441e5a542df93278c64a2dfdcf1e7eec0de9dc` |
| Decoded bootstrap | 10360 | `04d2eca05f6f2dc33170e06ed287cf9bbed38b03626ebb8494c42d3d4d80b685` |
| Complete launcher | 4716 | `928438fdbe0ea0c83e5b03b00c1a7e8aed2a94d0df43976364b85fb439dd5678` |

The original normal commands preserved below remain applicable. First-cost
compilation/transport, language-level initialization proof, normal regeneration,
selected process execution and project acceptance remain separate evidence.

The sole ordinary builder --dev invocation reproduced shipping C/native/
bootstrap/whole twice and the explicit preceding41ab/8733 DEV C/native tuple
twice. The sole unchanged selected verifier executed the actual4716 wrapper in
quit and EOF sessions, eight legal GO epochs total. It observed the full new
47ec4966... /proc/exe image, three stable startup TIDs in each session, absent
private paths/helper children, active closing work, exactly one closing bestmove,
finished readers and physical exit0. Both outer groups were terminal0/reaped/
absent, with no retry or forced cleanup. Cancellation causality stays unproven.
No fresh archive, focused fixture, negative campaign, game or benchmark ran.

Normal build receipt:
`bd98edca98f6903f567c02dca89e3210d38f061dc58c1c028709842180eff1ed`.
Normal selected runtime receipt:
`c8888416a51f4061a51c7822348c42c1b9799199add629092e7106e6313ba7d2`.
Producing recipe:
`0404b32f924b15a2a6e183ac86695bee7a995f2d0faa905388b124d3131a96d3`;
producing25-source manifest:
`d8c7066a485965db20c4dca7a5c90713a3036ecfd3b1177bbfa917ff49ff595f`.
Only recipe completion metadata and this README changed after execution;
helper/builder/expected/compiler/resources/codec retain producing bytes. Raw
normal and GitLF text hashes are distinguished from raw binary identities.
Git commit, CI and project readiness remain separate parent work.

# Historical A4727 capture-bit stage

The selected complete launcher is **4,727 bytes**, 12 below A4739 and
**631 bytes above4,096**. The normal builder reproduced all fixed shipping
artifacts twice and the prior DEV tuple twice; the unchanged selected verifier
then passed its sole quit/EOF invocation. Expected values are the literal
reviewed first-cost identities, never refreshed from output. The previous
A4739 source and ordinary23-input raw/LF closure were preserved before this
change. No4KiB, playing-strength or broader-target acceptance is claimed.

`shipping_capture.py` is the final shipping-only stage after lexical names.
It embeds eight literal old/new regions, exact9470/9391 source hashes, canonical
readable identity, source/output offsets, complete inverse and the9,130-byte
protected complement. It reads no files. All prior canonical/alpha/storage/
scope/input/declaration/type/lexical checks run unchanged first; the helper is
pinned in recipe.helper_sha256 and frozen before import. DEV bypasses this
stage and must reproduce its explicit prior C/native tuple. Unchanged fresh.py
will discover the helper, yielding24 named ordinary source paths; fresh archive
extraction is not part of this promotion. No experiment, evidence, historical
artifact, AST/library, upstream source or network is a normal generation input.

This changes the private generated Move encoding and the entire native image.
Capture-only bit3 uses the unused0x88 source-square bit, cleared by FROM119.
TO/PROMO and the17-bit TT move field stay unchanged. Emitter class0 covers quiet,
castle and double push;1 is a nonpawn capture;2 is a single pawn push;3 is a pawn
capture or empty-target EP. Promotion eligibility uses class>1, and quiet N/B/R/Q
promotions retain capture tag0 and their old quiet history/continuation/noise.
B's promotion-inclusive tactical tag is not imported. Only generated/tagged
moves may enter classification consumers; no old persistent raw-Move ABI or
old full-native equality is claimed.

| Current observed artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 9391 | `b4aa345388c20d4701732a2ce561bd2714b1f1d26b756aa79c05ae8dfc006cf8` |
| Full native | 22672 | `99c729d5d2100cbff4781500e0e7805637623b98ac5bb6446ceabcf367bb945b` |
| Decoded bootstrap | 10381 | `11b68e9ed08ce786781cc9ba4c63c0067f715b39b2c907625e21298ce5aff0fb` |
| Complete launcher | 4727 | `a288bc81f47a6a91eace846bab9675cbf9bf590b87a100d679bf0b74ece20376` |

The focused positive proof ran exact shipping functions under ASan/UBSan in
one fixed old/candidate fixture. It checked59 boards,1,529 ordered pseudo moves,
1,421 legal children, independent capture/attack/hash/HCE/rolling-context checks,
all quiet/capture promotions in both colors, EP, text/query and actual TT17/full
keys. Five freshTT18 one-worker depth1->2 searches produced identical scores,
nodes, decoded best witnesses and702,380-byte normalized Worker/TT snapshots;
actual history/continuation/correction updates were positive. This is bounded
source-function evidence, not execution of the selected native image or whole
wrapper. C>=4 LMR execution, concurrent TT contention, pool/cancellation and
playing strength were not newly proved. The focused index is
`0b2f9f62327dc40b39a47de047209b3df6dc1a179577e49ffb04520ae0e1a385`.
Compiler/resources/bootstrap/77-byte prefix and original ALONE settings remain
unchanged. The normal commands preserved below remain applicable.

The sole ordinary --dev build passed two independent shipping C/native/
bootstrap/whole generations and two DEV C/native generations, with the literal
prior41ab/8733 DEV tuple observed exactly. The sole unchanged selected verifier
executed the actual new4727 wrapper in quit and EOF sessions: eight legal GO
epochs, full new99c729... /proc/exe image, three stable startup TIDs per session,
unlinked private paths, no runtime helper children, active closing work, one
closing bestmove, finished readers and physical exit0. Cancellation causality
remains unproven. Both bounded outer groups were terminal0/reaped/absent; no
retry or forced cleanup occurred. No fresh extraction, repeated core fixture,
new negative campaign, game or benchmark ran for this promotion. The earlier
focused source-function proof is retained separately and does not substitute
for this newly observed selected-image execution.

Normal build receipt:
`814d64942d6b6db2e37e88fd79befe2fc32aeaf60d26f5304469949bddcbd61a`.
Normal selected runtime receipt:
`33d100bae2ef94c97af06b9b14354aead21a648a43d8d4190159595f091c76a1`.
Producing recipe:
`c90449f97080acdf87229bd11449959692ed84133dd274e8cab0260794836b31`;
producing24-source index:
`2118d5151569000df80dc9edc033b5ae8b90dab5b401c4d8036aecdc167c041b`.
Only this README and recipe completion metadata changed after execution.
Source/helper/expected/compiler/profile/codec inputs retain producing bytes;
normal LF text metadata, Git LF source identity and raw binary controls are
recorded separately. Git commit, CI and project acceptance remain parent work.

# Historical A4739 lexical-scope stage

The selected complete launcher is **4,739 bytes**, 9 below A4748 and **643 bytes above4,096**. The final shipping-only `shipping_lexical_scope.py` follows the unchanged type stage. It closes one5-declaration map in search au: bestmove ab->N, ordering-loop N->P/O->R, cutoff T->S and correction V->S. Moving the old inner N first frees N for the outer bestmove; P/R are sibling-loop names, and the3 S blocks are pairwise disjoint. There are21 position-bound identifier edits and6 raw source bytes saved. The actual full native stays byte-identical to the preceding native; no algorithm, ordering, TT, layout or ABI change is introduced.

The ordinary helper owns current9476/result9470 full hashes, canonical readable pin, exact declaration/reference occurrence ledger, alias inventory, inverse and every protected byte gap. One macro argument is explicitly bound: unchanged `#define PROMO(m) (((m)>>14)&7)`, sole old invocation5936:5945, physical ab5942:5944 and its expanded DeclRef to declaration169/4533. It admits no stringify/paste, definition edit or additional macro-affected token. Every other directive, literal, type/member/global/function and opaque region remains protected. The source proof compared269 declaration shapes and2442 reference edges before/after and kept the full binding graph, with only5 names changed. This proof is historical qualification bound to exact source, not a normal AST dependency.

Existing old function-wide scope/map/canonical/type guards remain before this last stage. DEV bypasses the new stage and retains its existing literal source/native tuple. The helper is pinned and frozen before import; unchanged fresh.py dynamically includes it, yielding23 ordinary source paths. No experiment, report, old artifact, analyzer/library, external reference code or network is a normal input. Compiler/resources/bootstrap/77-byte prefix/ALONE settings remain unchanged.

| Current artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 9470 | `90b7d08d450ff6865bdc07873693f90f549dcf3d3a5cf411ad37c7609dd5c527` |
| Full native | 22672 | `28260858a130711bb5fa70816e950b7666440168e8835bb4802b98675b972422` |
| Complete launcher | 4739 | `bcc529093299e2d6654b4bf9473442995df00a6ea3ab62c31bd4bd24c75f05d5` |

The sole normal builder --dev invocation passed shipping C/native/bootstrap/whole twice and the preceding DEV C/native tuple twice. The unchanged selected verifier passed its sole quit/EOF invocation: two sessions/eight legal GO epochs, exact restored native image, three stable startup TIDs per session, absent private paths/helper children, one closing result, finished readers and physical exit0. Both bounded groups are terminal0 and absent, with no normal retry or forced cleanup. The earlier physical macro-reference guard rejection remains preserved separately from its approved exact provenance correction and executed analyzer. Prior full-native core qualification is reused by exact entire native identity; the new wrapper's restoration/output/physical-exit evidence must be observed separately. No new core fixture, fresh extraction, game, benchmark, sweep or native retry is part of this promotion. Producing/final recipe metadata and the old ordinary source/raw binary controls are preserved separately. Cancellation causality, broader compiler compatibility and playing-strength claims remain unproven.

Normal build receipt: `7cd0b4cbc524230547e8bde7d7b797d26fa81f7d652f12a863753fbf33b7ceaf`. Normal runtime receipt: `90e3217b7abb366cdd3d7e01a6cb65fab01ec5f77c8b877b4cc6a6cd4c6bc72a`. Producing recipe: `92cedac85117bbd8d505f06eff809962bd4b9b2de827f3438c1b088a9fc73aa2`; producing23 source freeze: `5323ea2b90149683e1788a4429bfc2c253ee0201672ad5daa5ee5a1afb6f2cd6`. Only README/recipe completion metadata changed after execution; source/helper/compiler/expected/codec bytes remain producing inputs. Git/CI and project acceptance remain separate parent work.

# Historical A4748 type-token stage

The selected complete file is **4,748 bytes**, 14 below A4762 and **652 bytes above 4,096**. The final shipping-only `shipping_types.py` stage owns one fixed uniform type map: `uint64_t -> W`, `int16_t -> X`, `Move -> Y`, and the private anonymous-entry typedef `zb -> Z`. Its 37-byte typedef prefix and all encoded transport bytes count. Shipping C is 9,476 bytes, 211 below the preceding source. Actual first-cost full native bytes are identical to the A4762 image; no metadata exception is used.

The ordinary helper pins the unchanged canonical readable and exact post-declarations source, every admitted ordinary type/declarator offset and count, the sole MOVE directive's three casts, alias freshness, include boundary, full inverse, protected complement and complete output hash. Strings, other directives, external API spellings, other type names, layout and all old spelling stages are protected. Freshness against arbitrary future headers is not claimed: this fixed compiler/header environment must reproduce the entire admitted native. No AST allocator, experiment, report or old artifact is a normal generation input. Existing canonical/alpha/storage/scope/input/declaration guards run first; DEV bypasses only the new stage.

The new helper is pinned in `recipe.helper_sha256` and frozen before import. Unchanged fresh.py dynamically includes it: LOCAL9 + helpers11 + tests2 = 22 unique ordinary sources. Canonical/DEV/verify/fresh/shared source bodies, compiler, resource profile, bootstrap, 77-byte prefix and ALONE settings remain unchanged. A/F experiment FINAL5 is preserved separately; no F source or atomic-TT candidate is consumed by this A producer.

| Current artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 9476 | `71ae2a35736743103e72b2bb4738b8e71d2da9a78af44ad24b61c4157548ca27` |
| Full native | 22672 | `28260858a130711bb5fa70816e950b7666440168e8835bb4802b98675b972422` |
| Complete launcher | 4748 | `a997bd9dd620d0c8331c8fd2f2bae6090a76f6862b73939b5db1142e197bc966` |

The sole normal builder invocation passed two independent shipping C/native/bootstrap/whole reproductions and two DEV C/native reproductions, with the preceding DEV tuple observed exactly. The unchanged selected verifier then passed its sole quit/EOF invocation: two sessions/eight legal GO epochs, exact restored native image, three stable startup TIDs per session, absent private paths/helper children, exactly one closing result, finished readers and physical exit0. Both bounded outer command groups are terminal and absent; no retry or forced cleanup occurred. No new engine fixture, fresh extraction, game or benchmark is authorized. Prior native/core receipts are reused by complete native identity, not relabeled as new runs; cancellation causality and many-core performance remain unproven. The prior ordinary source and named actual controls were preserved outside Git before these four-file changes. Producing and final metadata will remain distinct.

Normal build receipt: `ec562d8fd24723a8792e97e27a1c0cb24710ffd99d4e7f79336918aed7d02d7d`. Normal runtime receipt: `cb90a87d40f90f336d01a2c79a2b126117cca002aa9d19749914330e0d8c05c4`. Producing recipe: `0ac71919bc8d2722ef1bdb0092fb00efff361bc4d1fab378980d08a76c41c052`; producing source22 freeze: `28f2e2531803a90f97cd7ace4328f718d605e6684c9f8cb3298e38b2eb6ef7c9`. Only this README and recipe receipt metadata changed after execution; all source/compiler/helper/expected/codec inputs retain producing bytes. Git, CI and overall 4 KiB acceptance remain separate parent work.

# Historical A4762 declaration stage

The selected complete file is **4,762 bytes**, 4 below A4766 and **666 bytes above 4,096**. The single new ordinary `shipping_declarations.py` stage runs after the existing shipping input profile. Its five adjacent-int regions remove six redundant type prefixes and its one completion comma expression removes one brace pair: source −26 B, complete file -4 B. The actual first-cost full native is byte-identical to the prior image; no metadata exception is used.

The helper embeds the exact readable/shipping source pins and six fixed literal pairs, unique source order, full inverse and protected complement checks. It has no experiment, report, old artifact, AST allocator or upstream-source input. Existing canonical/alpha/storage/scope/input/semantic guards remain before this last stage; DEV bypasses it. Registered in `recipe.helper_sha256`, it is frozen before import and included by unchanged fresh.py: LOCAL9 + helpers10 + tests2 = 21 unique ordinary source files. Compiler/profile/77-byte prefix/bootstrap/ALONE settings are unchanged. No source/alias/codec search runs.

| Current artifact | Bytes | SHA-256 |
|---|---:|---|
| Shipping C | 9687 | `6946861173a6b1dee660e83d72db40cde36a066be04e3c4457d4b67a6ab7ae4e` |
| Full native | 22672 | `28260858a130711bb5fa70816e950b7666440168e8835bb4802b98675b972422` |
| Decoded bootstrap | 10677 | `70d0ef0152c5aca432aa6fc4685a4e0b3584b4af8d5a28b929358fcc99e28220` |
| Complete launcher | 4762 | `e2fc1581198947298d4abe4c5552095fd57e93762f1da38704e45bb4545b3b7d` |

The sole normal builder invocation passed shipping source/native/whole/bootstrap twice and DEV source/native twice, with the old DEV tuple observed exactly. The unchanged selected verifier passed quit/EOF two sessions and eight legal GO epochs, exact restored native image, three stable startup TIDs, absent private paths/compiler children, completed readers and physical exit0. No retry, fresh extraction, core fixture, game or benchmark occurred. Cancellation causality remains unproven. The normal commands below remain applicable.

Normal build receipt: `65e50dd238b6206ea76f8b0b834843b2e9f873b3c5d34151e367fb9c7c4462f1`.
Normal runtime receipt: `04e249e4b51a8d078f247531dad7242fb96b2781658ddeb9a16f3f0a7a25d128`.
The producing recipe `83f6bc8acb1e1cf32706654081ee4a343e774df96daf7fa80a502e3728f3c7ca` and producing source21 snapshot are preserved outside Git. Final recipe/README add completed receipt metadata only; source/helper/expected/compiler/profile/codec inputs remain the producing values. Git commit and CI are separate parent work. The following preserved text describes the historical input-profile stage and its prior complete-file identities; its native and unchanged core receipts are reused only through exact identity. This stage does not claim 4 KiB acceptance, fresh extraction, game/strength or many-core performance.

# Historical A4766 input-profile stage

The complete selected launcher is **4,766 bytes**, 80 bytes below the prior
4,846-byte entry and still 670 bytes above 4,096. This folder does not claim
4 KiB acceptance or playing strength. The fixed target is Ubuntu24.04.4 x86-64,
GCC13.3.0/binutils2.42/glibc2.39, Python3.12.3 and xz/lzma5.4.5. Exact source,
native and complete-file identities fail closed on a different output. The
compiler remains `cc -Os -x c - -o x -s`; this fixed glibc target provides the
pthread interfaces without a separate link flag. Broader target compatibility
is not implied.

`engine.c` remains the unchanged 24,820-byte readable canonical source, with
its development and original shipping input bodies. The ordinary standalone
`shipping_input.py` owns one fixed input policy and its paired readable and
post-scope compact transformations. No experimental folder, report, generated
old C, executable, Clang tool or network resource is a normal build input.

From the repository root in that environment (WSL Ubuntu is supported):

```sh
python3 -B engines/compact/tiny-entry-a/build.py --out /absolute/new/external-output --dev
python3 -B engines/compact/tiny-entry-a/verify.py --build /absolute/new/external-output --out /absolute/new/external-verification
```

Output directories must be new, absolute and outside any Git checkout. Workers
remain fixed2, TT_BITS18 and PLY128. Both workers and the input thread exist at
startup. Shipping offers no resource options. The builder independently
regenerates shipping twice and, with `--dev`, diagnostic C/ELF twice. The selected
verifier is unchanged and separately runs quit and EOF sessions, eight GO in
all. Source generation/compilation and actual process evidence are distinct.

## Ordinary source pipeline

Every existing canonical/readable, resource, opaque-token, alpha, storage and
scope guard is preserved. Shipping starts from the original canonical source,
then uses the existing specialization/counter stripping,45 fixed renames,
resource substitutions,31 fixed function spellings, A31 alias policy,18-name
storage policy and70-declaration/274-location scope replay. The last step alone
produces the previous9,910-byte source. Only then does `shipping_input.py`
apply five exact literal roles: position, decimal number, line reader removal,
GO, and the input loop in main. It admits the actual old whole source and
readable SHA, checks every projected role once, protects all complementary
bytes, proves exact inverse and requires the sole new9,713-byte source.
The unchanged shipping complement is7,900 bytes, SHA
`b863c8745d6581631d37433bcf6b3c8b41cac9056c72113e3fe8cffa207fbb5b`.

DEV bypasses every shipping spelling/input-source stage. Before DEV
specialization only, the new helper makes the fixed27,687-byte dual readable:
old bodies under DEV and the new text profile in the other branch. Every
#else/#endif starts on a separate line. This readable pair has an exact inverse
and19,707-byte protected complement, SHA
`d3d1ab4591c85eff1230bc16c343c44091e3d96c47c85bb059bfdb049b1f14e3`.
The old diagnostic source/native tuple is an explicit comparison target;
actual normal generation must establish equality. No DEV engine execution or
new broad algorithm proof is implied by compilation.

The builder freezes and hashes all ordinary helpers before importing them from
its external inputs directory. Nine helper entries include local alpha/scope/
input helpers and six shared producers; the unchanged fresh.py discovers the
new helper through recipe.helper_sha256. With nine base local files and two
verification helpers, the named closure contains20 unique ordinary files.
Fresh archive extraction capability is separate from the checks actually run
for this promotion. CRLF source checkouts normalize to LF; lone CR fails. The
existing .gitattributes retains LF. No alias/compiler/codec sweep runs.

## Shipping text policy

This is an explicit shipping profile, with a narrower malformed-input domain
than the original robust parser; it is not all-input parser equivalence.

* Text is NUL-free and uses SP/TAB/CR/LF delimiters. LF and CRLF are admitted;
  an unterminated final EOF line is processed. The limit is32,767 bytes before
  LF including CR. One-byte lookahead handles an exact full buffer; an overlong
  line is drained through LF/EOF and discarded without consuming the next line.
* Commands match the complete first token. Extra arguments to simple commands
  such as uci/isready/quit are ignored. Unsupported stop/newgame/infinite tokens
  are tolerated. No general TCEC UCI option surface is introduced.
* GO accepts exact wtime/btime/winc/binc in arbitrary order; increments may
  precede clocks and last duplicates win. A missing numeric value consumes one
  following token. Own-clock absence defaults to finite1,000ms; present invalid
  or zero retains the1ms minimum. Opponent-only fields count as absence. The
  previous clock/30, increment3/4, increment clamp86,400,000, clock/5 cap and final
 86,400,000ms cap remain.
* Numbers must be full ASCII decimal0..LLONG_MAX. First-digit, end-pointer and
  unsigned-saturation checks reject signs, overflow and junk without signed or
  scanf overflow. Invalid tokens return0.
* Position starts with startpos and optionally moves. The unchanged legal
  parse/make child API executes a scratch Board and history transaction; only
  complete replay commits. Invalid prefixes, suffixes and history overflow
  preserve the full prior state. Promotion4, castling, canonical EP, hash/HCE,
  repetition/halfmove context, TT/search and persistent worker ownership remain
  in the protected program body.

## Fixed artifacts and transport

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| Canonical engine.c | 24,820 | `71f9ff6ce1b7f555ad85c3bf49766381c0627315da94acf0c49eeee7bee4a734` |
| Dual DEV/profile readable | 27,687 | `63821a63cbf6507393e0617da9f611b778ada46c9a89b49fdefc8996bb461e2c` |
| Compact shipping C | 9,713 | `1f4097d43c5f6e84d7cbd17906100354da25be205d44ca08fbf52732e63b624c` |
| Stripped native ELF | 22,672 | `28260858a130711bb5fa70816e950b7666440168e8835bb4802b98675b972422` |
| Complete launcher | 4,766 | `8a783ff2d0f5d3546e54dba3d8c4c5931ba9b72c95270deca69eeabd33136226` |
| Decoded bootstrap | 10,703 | `49ad9afc517afc541a64d0d64f15f1c83a258caa9f466e29c7e681c115899837` |

DEV comparison targets remain C
`41ab9f0f5d28183b76833d038c40e0bb6a2ee6ef9303766c293dd577680a4c9c`
and native
`8733dbf0814a2c2545251f6e0e17d243ecfd41fce7853fb325ca9720fedd1102`.
New shipping full-native identity differs from the prior84ce7fd1... image;
neither full-native equality nor a metadata exception is claimed.

The exact77-byte shell prefix calls lzma -dc at byte78. Payload is LZMA1 ALONE
preset9 extreme/lc2/lp0/pb0,64MiB dictionary, unknown size/end marker and header
`0200000004ffffffffffffffff`. Header and termination bytes count. ALONE has no
XZ CRC64; equivalent corruption detection is not claimed. The unchanged
builder checks header, strict Python trueEOF/no-unused decode and independent
lzma CLI output. The unchanged bootstrap compiles source, unlinks its private
path and execs the native through the original descriptor/signal/child logic.
Existing general descendant-group/bootstrap limitations are not broadened into
new claims by successful selected sessions.

## Qualification and producing metadata

The outside-Git focused FINAL index is
`6f821bd37e768308ecd1ad6e2076c527b843595668f926568bb30b1ed1cd580c`.
It passed one actual-shipping fixture compile/run:25 numeric,26 GO,25 replay
transactions and6 special roots/96 full children. Manual workerless GO field
publication is separate from actual pool evidence. Production quit/EOF2sessions
passed8GO and the third text-only0GO session passed8 ingress checks. Exact
A/F policy assignment equality permits only supporting F ingress reuse; no F
native execution is relabeled as A. Physical /proc/exe new-image identity,
startup3TIDs, unlinked paths, legal result uniqueness, active closing search,
physical exit/readers and cleanup were observed. Cancellation causality stays
unproven; no arbitrary standard-descriptor or broad performance claim follows.

The current recipe keeps the old A4846 expected identities and receipts nested
as historical metadata. They are not normal inputs or executions of this new
native. Expected pins are literal reviewed values; mismatches fail and are
never refreshed automatically. This producing recipe will be preserved before
later normal build/runtime receipt metadata is added. Normal reproduction and
selected runtime subsequently passed in the first authorized attempt, recorded
below; the earlier producing recipe remains preserved separately. No fresh archive
extraction, repeated focused fixture, game or benchmark is part of this stage.


The sole normal builder invocation passed two independent shipping generations,
compilations and whole packages plus two DEV generations/compilations. Shipping
source/native/bootstrap/whole exactly match the artifact table. The prior DEV
C and ELF comparison targets also matched in both attempts, now observed rather
than assumed. The unchanged normal verifier then passed its sole invocation:
quit/EOF two sessions, eight legal GO epochs, new native /proc/exe identity,
three stable startup TIDs in each session, unlinked private restoration path,
no compiler children, active closing search and exactly one closing result,
exit0, absent main process and finished readers. No focused fixture was rerun.

Normal build receipt:
`b53178618951654aa0ab9bd1d5413162eff6a0de8178b9fc083af2d3b12e09a9`.
Normal selected runtime receipt:
`822bf19b4c150ca784bed9272399f9d0ef03de4a58f2da428798e1e98c9309d0`.
The producing recipe is
`2eb63d94bee6eb847d8c2e0c962201bfc7e90d050f58cc149911cc0d7728a1af`
and source20 freeze is
`4ff9880794ffcc4c8106c6ff9e84f2790cf3250820e221aa5382b71a96c24064`.
Only recipe receipt/provenance metadata and this README were updated afterward;
source/compiler/helper/expected/codec inputs are unchanged. Producing and final
recipe identities are kept separate. Both managed command groups are terminal
and absent, with no retry/forced cleanup and no remaining owned handles.
Git commit, CI and whole-project acceptance remain separate work.

## Compiler-group ownership adoption

현재 생산자는 기존 source/literal/argv 검사를 마친 뒤 `engines/scripts/compiler_group.py`를 encoding 직전에 적용한다. 컴파일러 원 leader를 `WNOWAIT`로 보존한 채 살아 있는 같은 process-group 작업을 정산한 뒤 마지막에 reap한다. Python 진입 시 SIGCHLD disposition을 저장·정규화하고 native exec 전에 복원한다. 원 C/source·compiler argv/env/cwd·stdio·읽기 FD exec·legacy exitstatus는 유지하며, 단순 크기 손실로 이 수명 수정을 숨기지 않는다.

| 현재 생산 context | 이전 whole | 새 measured whole | 새 bootstrap |
|---|---:|---:|---:|
| A | 4489 | 4863 | 10325 |
| A-root-hint | 5151 | 5528 | 12843 |
| A-root-normal | 5132 | 5510 | 12805 |
| A-root-pals | 6677 | 7135 | 17505 |

위 값은 각 actual 기존 입력에서 고정 codec 한 번과 strict Python/CLI 복원으로 먼저 측정한 값이다. source/native/compiler/header/codec의 변경이나 다른 문맥 delta의 가산은 없다. 기존 frozen control과 과거 qualified receipts는 당시 범위로 보존한다.

이 entry는 local source/Data proof 및 fixed-cost 측정까지 수행했다. 새 HEAD의 ordinary/positive CI 검증은 별도로 필요하며, F 기본형 양성 결과를 이 프로필의 새 runtime 결과로 재라벨하지 않는다.
공유 세 형상의 기존 packaging suites는 stream5·ZIP4·restored-files5 tests 모두 통과했다(skipped0). 이 관측은 live same-group 정산이며 detached 작업이나 zombie를 포함한 문자 그대로의 group absence 일반 증명은 아니다.

실제 producing/measurement/normal receipt는 recipe의 `compiler_group_ownership`에 명시했다. 공통 source helper에 대한 alias-only 후보 raw−389/whole+8 손실은 과거 미채택으로 남고 여기서 재실행하지 않았다.


## Prepared normalization and path-authority grace — producing checkpoint

The default loose source-script path consumes all previous source/literal/compiler-owner/late-BOOT,
W1/W2 and seek admissions first. The exact previous prepared bootstrap
10175 B/9caeb9a45554a46a7ff0dd87945e8792152cb74495a9b6326050dddaf322dfec is then admitted before
calling the same frozen compiler_group.normalize_bootstrap and
compact_cleanup(state=True, wait=False, termination='grace'). The compiler_group
legacy emitter still returns the same bytes; its canonical cleanup renderer owns
both representations. No extra UCI/runtime policy selector is introduced.

Measured complete file 4807->4785 B saves22 B;
bootstrap 10175->10111 B. The independent fixed-codec
normalize+state+wait candidate is larger and is retained as an unselected cost.
Source/native/readable/DEV, worker2/TT18, codec and complete header are unchanged.
The recipe retains the full predecessor expected/helper/local-input closure and
a separate selected tuple. Only the four whole/bootstrap expected fields change.
All three optional root-policy expected contracts and generate/package branches bypass this new stage.

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
