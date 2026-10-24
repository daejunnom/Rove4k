# 실행 래퍼 후속 구현

사용자가 2026-10-24에 외부 `Rove4k-Wrapper-Handoff.md` 전체를 단계적으로
진행하도록 요청한 작업 기록이다. 문서는 참고자료이며 저장소 규약을 대체하지
않는다. 참고 파일 SHA-256은
`6f66e6c5f5f7c096881952ec903edfbaa80c9c45a30e280fa587b6f9bf557b22`다.

시작 기준은 `3326f56b941dbb94bd779d94e1973a782e20ca9b`,
tree `7f9c522f3b666647228c4448e67d421fd605cbca`다. 같은 feature branch와
Draft PR #12를 재사용한다. 학습·AWS·유료 자원·예약 작업·npm 배포는 포함하지
않는다. Full 엔진과 고정 worker/TT를 유지하는 기본판을 우선하며, 종료 유예나
포장 계약을 바꾸는 후보는 별도 build 선택과 산출물로 식별한다.

이전 standalone 후속 선택과 실행 상태는
[후속 압축과 엔진별 Bash 인수](#후속-압축과-엔진별-bash-인수)에 기록한다.
아래 감사 기준과 시작 기준의 숫자는 각각 명시한 과거 source에 한정한다.
Compiler ownership의 다음 후보 비교는
[종료 소유 모델 후속 실험](#종료-소유-모델-후속-실험)에 별도로 기록한다.
추가 사용자 지시에 따른 현재 출품 우선순위는
[TCEC 필수 범위 전문화](#tcec-필수-범위-전문화)다. 강한 compiler owner의 축약을
TCEC 제출판의 선행 조건으로 두지 않는다.

## 감사 기준 d8bdd0e1과 역사 기록

2026-10-25의 외부 `Rove4k-Artifact-History-Audit.md`를 현재
`d8bdd0e178ff7536db9875c316b0b8fb698c3729` 및 지목한 과거 Git 기록과
대조했다. 참고 파일 SHA-256은
`99eca0e3433ece103dcbb01e1c0b7c8a3cac0605377fe916443c61016a541d81`다.
첨부의 권고는 참고자료이며, 사용자가 별도로 요청한 표시 정리와 후속 압축·검증을
단계적으로 진행한다. 이 대조 자체는 새 바이너리 계측이나 기력 검사가 아니다.

| Full 엔진 | 과거 기본 최소 | 현재 기본 grace | 현재 Bash shell | 현재 shell 상태 |
|---|---:|---:|---:|---|
| A | 4489 | 4785 | 4232 | 비용 계측, 엔진별 실행 인수 전 |
| B | 4950 | 5259 | 4712 | 비용 계측, 엔진별 실행 인수 전 |
| C | 4628 | 4924 | 4375 | 비용 계측, 엔진별 실행 인수 전 |
| E | 4586 | 4878 | 4323 | 비용 계측, 엔진별 실행 인수 전 |
| F2 | 4275 | 4576 | 4026 | 별도 Bash 계약의 재현·선택 실행 완료 |
| F8 | 4284 | 4588 | 4028 | 별도 8-worker 재현·선택 실행 완료 |

과거 최소의 compiler owner와 현재 grace는 종료 계약이 다르다. 주된 증가점인
`3069597`에서 A/B/C/E의 source·native·compiler·codec은 그대로이고
bootstrap이 각 1016 B, whole이 374/392/374/377 B 늘었다. 이후 같은 계약의
축약으로 일부를 회수했다. 최신 shipping source는 과거 최소보다
A/B/C/E/F 각각 20/15/22/43/55 B 작다. 과거 커밋 전체로 돌아가면 이 축약도
잃으므로 현재 source에서 같은 계약의 후보끼리 비교한다.

F의 4260 B는 `3069597` 안의 old-owner 중간값이고 그 커밋의 최종 기본값은
4640 B다. 현재 `legacy`는 quiet/seek 축약을 포함한 `3326f56b` 기준
F2 4590 B/F8 4602 B의 직접 predecessor다. Historical
old-owner 최소 4275/4284 B를 복원하는 옵션이 아니다. Reduced F의 현재
grace 4616/4342 B 및 kill 4591/4311 B도 각각 원 기능 정책으로 비교한다.

F ordinary `build.json`은 이미 policy/wrapper override 이후의
`expected_contract`와 별도 `wrapper_contract.predecessor_expected`를 기록한다.
감사 권고에서 보고서의 잘못된 선택값 출력을 가정한 부분은 확인되지 않았다.
README 첫머리와 stdout에 현재 선택을 명시하고, 실제 실행에는 저장된
`selected_verifier.command`와 effective recipe를 사용하도록 안내한다.

기존 producing 기록의 PENDING·실패는 동결 당시 상태로 남긴다. 후속 성공은
아래 인수 기록과 엔진 README 상단에서 연결한다. 4011 B sh/inherit는
cleanup child 회수 조건 때문에 미선택이며, F2/F8 Bash의 70/68 B 여유는
파일 크기 조건에 한정한다. Compiler cancellation, 호스트의 orphan 처리,
시작·잔존 파일 조건과 출전 적격성은 대상에서 별도로 판단한다.

## 후속 압축과 엔진별 Bash 인수

추가 유한 source 탐색에서 full F2의 source를7740에서7712 B로 더 줄였다.
현재 선택 비용은 full F2 grace/kill/shell **4547/4519/4018 B**이며 Bash
여유는78 B다. A/B/C/E와 F8 비용, reduced F 및 legacy 출력은 아래 첫 통합
값을 유지한다. 이 표현 단계의 실제 ordinary/selected 인수는 아래 별도
기록으로 구분하며 cdbf49a의 실행 통과를 자동으로 승계하지 않는다.

### 첫 통합 cdbf49a: 공통 owner와 static alias

2026-10-25 후속 source의 비용은 A/B/C/E grace 4768/5245/4906/4859 B,
F2 full grace/kill/shell 4553/4529/4026 B, F8 full grace/kill/shell
4571/4542/4028 B다. Reduced F noise grace/kill 4594/4566 B,
move-TT 4325/4297 B다. 새 ordinary 재현과 selected 실행을 모두 마감했다.
아래 실제 종료 결과와 해당 PR head의 CI를 별도로 인수하며 과거 통과로
대체하지 않는다.

| Full 엔진 | 감사 기준 grace | 새 grace | 절감 | 별도 Bash shell |
|---|---:|---:|---:|---:|
| A | 4785 | 4768 | 17 | 4232 |
| B | 5259 | 5245 | 14 | 4712 |
| C | 4924 | 4906 | 18 | 4375 |
| E | 4878 | 4859 | 19 | 4323 |
| F2 | 4576 | 4553 | 23 | 4026 |
| F8 | 4588 | 4571 | 17 | 4028 |

모두 같은 full 기능과 고정 자원을 유지한다. A/B/C/E/F8의 source/native는
동일하고, F2 source 표기만 바뀌며 전처리/native 전체가 동일하다. F2 legacy는
7830 source/4590 whole을 그대로 두고 새 alias를 적용하지 않는다.

공통 `compact_private_owner`는 현재 state=True C prepared-owner의 닫힌
구조를 인수한다. Private helper 이름과 truth 소비 전용 값·guard, Linux
procfs의 ASCII PID 이름 검사만 줄인다. 완전 역변환과 외부 AST·source
expression을 대조하고 WNOWAIT·group 정착·마지막 reap·125 보존은 유지한다.
최종 frozen 공통 검사 15개가 skip 없이 통과했으며 original/new owner의
20개 fixture에서 실제 손자 종료, 취소, 실패, FD exec와 상태 보존을 확인했다.

F2의 순수 static alias는 source7830을7740으로 줄인다. 27개 keyword 사용과
macro 삽입의 모든 구간·보호 complement·전체 역변환을 확인했다. 기존·static·
static+const 세 입력의 전처리 전체64543 B 및 native18576 B가 각각 동일했다.
Static+const는 더 짧은 source라도 shell이1 B 커져 미선택이다. F8 alias는
shell이2 B 커져 미선택이며 현재 F8은 정확한 F2 alias 역변환 후 원래
resource proof를 적용한다. 공통 owner와 F2 alias의 결합 whole4553 B는
별도 인코딩한 실제 값이다. 독립 절감량을 합산하지 않는다.

A/B/C/E에 명시 build-only `--wrapper shell`을 연결하고 공통 Bash verifier의
입장 범위만 fixed A/B/C/E2 또는 F2/F8, TT18/PLY128로 넓혔다. 기존 실제
native·stdio·TID·child·경로 정리·quit/EOF 검사를 그대로 사용한다. A root
정책은 해당 선택을 거절하며 새 grace 축약도 기존 미적용 범위를 유지한다.
Shell은 각 엔진 실제 실행 후에만 인수한다. Full 기능·고정 자원·기본 grace는
유지하며 새 UCI 옵션은 추가하지 않는다.

ABCE 후속 ordinary 8회와 selected 8회는 원 관리 session92085를 끝까지 유지해
exit0으로 마감했다. 각 ordinary 독립2회 생성으로16회 재현,
quit/EOF16세션·64 legal GO가 통과했다. Compile CPU2/runtime CPU2–3에서
엔진별 native·TID·stdio·초기 named path와 같은 엔진이 살아 있는 동안의
경로 삭제·cleanup child 소멸·SIGCHLD IGN·NX/no-WX를 확인했다. Source9와
동결 input139가 실행 전후 같고 forced cleanup0/owned process0이다.
현재 A/B/C/E shell은 비용만 확인한 후보를 넘어 해당 별도 계약의 실제 실행을
확인했다. 모두4096 B보다 크며 기력·대회 적격성이나 CI 완료를 뜻하지 않는다.
외부 final index SHA-256은
`b6579e2f9c462a7e6554d4c3434c9e4a8d8ee298cae497db790cac9b1a1da07f`다.

F2의 full grace/kill/shell과 reduced grace/kill 네 조합, F8 grace/kill/shell의
총10개 선택도 원 session32432를 유지해 exit0으로 마감했다. Ordinary10회가
각2회 재현했고 selected10회의 quit/EOF20세션·80 legal GO가 통과했다.
Full F2 grace의 기존 DEV도2회 재현했다. F8 세 경로는 단독 CPU0–7에서
9 TID와 모든8worker의 양수 CPU tick을 확인했다. 소스83과 producer4는
동결 전후 동일하고 forced cleanup0/owned process0이다. ABCE와 합쳐
18개 선택·36회 독립 생성·36세션·144 legal GO다. 보조 compiler fixture나
과거 실행을 이 수에 합치지 않는다. 로컬 실행은 기력·스케일링 판정이 아니다.
F 인수 final index SHA-256은
`b1ef0f9602cf4f136c0e136499d1a358d8056351ac0d07f187e0012fcacb6313`다.

새 full F2 shell은4026 B/
`c0ba0e13d0c81d3f779996e1782d04d5c1f294cdb120192e749d480ddc8b372b`이며
F8 shell은4028 B/`72a41ba1eb5cc889a2944d2de4d793d5e135be9be4a68fdc3d06e81874fbfaaf`다.
두 제품과 manifest는 새 외부 인수 폴더의 submissions에 별도 복사·해시 확인했고
이전 d8 제품을 덮어쓰지 않았다. F2는 이전4026 B와 크기만 같고 source와
whole SHA는 다르다.

중간 표시 정리 commit `0de220a5e285d1e16f75b0cdfb0c28223f827c89`의
Engine CI40123885682는 F README 변경에 대한 F8 source closure pin을 함께
갱신하지 못해 실패했다. 실제 C job120961062486의 F8 실행 전 입장에서
`project source closure changed: engines/compact/tiny-entry-f/README.md`를
확인했다. Rust·NVCompact·Repository는 통과했지만 중간 전체 CI는 실패다.
원 실패와 로그를 보존하고, 후속 F8 dependency refresh와 최종 source CI를
별도 확인한다. 실패를 단순 문서 변경이라는 이유로 성공 처리하지 않는다.

최종 source의 workflow는 ABCE shell 네 실제 빌드·선택 검사를 추가한다.
기존 F2 kill/shell, F8 shell 및 Rust 검사를 유지하며 duplicate-key YAML과
33개 run block의 bash syntax가 통과했다. 현재 최종 CI 결과는 같은 Draft
PR #12의 해당 head checks 및 외부 통합 인덱스에서 확인한다. 이 문서의
로컬 통과로 CI 성공을 미리 기록하지 않는다. 남은 작업은 grace의4096 B,
다른 A–F 경로의 축약과 full 기능, 대상 호스트의 시작·정리 조건 및 실전 비교다.
기준선별 source·wrapper·기능을 구분하며 크기 목표 이후에도 유효한 축약을 찾는다.

### 추가 표현 축약: source7712 / shell4018

첫 통합의 4026 B 통과 뒤에도 source 탐색을 계속했다. 유한6개 계측에서
각 initializer의 mask 괄호, 기존 unsigned typedef cast, 고정 TT clear
index 타입, 단일 MTD 대입문의 braces, continuation subscript의 괄호를
줄이는 결합이 source28 B/whole8 B를 더 줄였다. `shipping_expression.py`는
정확한7740 입력을 받아7712로 변환하고7구간·8개 보호 complement·전체
역변환을 검사한다. Static helper와 이전 producing 기록은 바꾸지 않았다.

현재 GCC13.3.0에서 unsigned/int4 B, size_t/pointer8 B를 확인했다. `Y`는
정확히 unsigned이고 TT index는0..262143만 사용해262144에서 종료한다.
세 mask는 순수 식별자의 scalar initializer이고, 단일 대입문의 else binding과
subscript expression 경계는 유지된다. 같은 명령의 old/new native 전체는
18576 B/`3aaaacf7891a2a4660f45d75b2b3e550ab40bf01c0c1766768517719cd1e63ec`로
동일하다. 전처리 bytes 동일성은 앞선 static-only 단계의 근거이며 이 표현
단계까지 그대로 확대하지 않는다.

실제 cdbf full grace/kill/shell의 old whole4553/4529/4026를 먼저 다시
재현한 뒤 새 C literal을 넣어4547/4519/4018를 별도 인코딩했다. 새 helper
SHA는`a2b678c5c5000d1d1acf9be19cbe5c31b33994bdcd4ad9c9aba8192ba9187b58`,
source SHA는`546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e`,
shell SHA는`b559c980e3146bd76ac62d2ad4d6176240e8a284b186a22b592f9be8b8877d8e`다.
F8 입장은7712에서 expression inverse7740, static inverse7830를 거쳐
기존 resource source7868을 생성한다. 이 단계의 native·source 증명은
완료했고 별도 ordinary/selected runtime도 마감했다.

원 session51021의 terminal exit0을 확인했다. Full F2 grace/kill/shell과
F8 grace/kill/shell 총6개가 각각2회 재현됐으며, selected quit/EOF12세션·
48 legal GO가 통과했다. F2 grace의 unchanged DEV2회도 포함한다. F8의
6세션은 새 입력의 이중 역변환과 동일 native/TID, 전체8worker CPU tick을
확인했다. Source84는 동결 전후 동일하고 forced cleanup0/owned process0이다.

이 최신6개 실행과 ABCE8개·reduced F4개의 앞선 불변 산출물 근거를 구분한다.
Current18개 선택의 coverage는36세션·144 legal GO이며, 이번 두 통합 단계에서
실제로 수행한 주 엔진 실행은48세션·192 GO다. 이전 full F2/F8 통과를 새
expression의 fresh 실행으로 재집계하지 않는다. 최종 CI는 최신 source의
전체 필요한 경로를 다시 실행한다. 새로운 F2 shell4018/b559c980 제품은 새
표현 인수 폴더의 submissions에 별도 복사하고 원 실행 파일의 해시와 대조했다.
이전4026 제품과 실패·미채택 계측 기록은 보존한다.

## 종료 소유 모델 후속 실험

2026-10-25 사용자가 외부 `Rove4k-Compiler-Ownership-Review.md`의 동등 계약
축약부터 별도 ownership 후보 실험까지 단계적으로 진행하도록 요청했다.
첨부는 참고자료이며 SHA-256은
`df5c540ec65f78fb162f391142d51841359b4ffc7a5a028d1ab86b6959e3f050`다.
시작 source는`6ea43d441a6c5d3ac34003567e89d070777ce02e`, tree는
`3f5cd24c130f407c43149d7f8a4919667a061558`다. 현재 full C7712/native18576,
F2 grace4547/kill4519/shell4018과 F8 grace4571/shell4028을 대조군으로 둔다.

공개 [TCEC 4k 규칙](https://wiki.chessdom.org/Rules#7._4k_specific_rules)을
다시 읽었다. 단일4096 B, 시작60초·잔존 파일, 허용 의존성 및 최소 UCI 조건을
지키되 현재 WNOWAIT/procfs/단계별5초/125 구현을 규칙 자체로 고정하지 않는다.
실행 책임과 내부 구현을 구분하고, 강한 grace와 작은 full shell의 차이는 유지한다.

| 별도 후보 | F2 whole | 기존4547 대비 | 비용·계약 판단 |
|---|---:|---:|---|
| 실패 결과 단일화 DeMorgan | 4547 | 0 | 같은 helper 호출·예외 순서, 실제 bootstrap40 B 감소 |
| 실패 결과 단일화 short-or | 4548 | +1 | 같은 호출 순서, 실제 bootstrap45 B 감소 |
| subreaper/유일 raw reaper | 4618 | +71 | PRCTL 설정·원상복구·status·새 소유 불변식 포함 |
| group grace/KILL 두 단계 | 4549 | +2 | 원 leader waitability와 live group 모두 확인한 수정 후보 |
| pidfd/poll leader 대기 | 4650 | +103 | 생성·등록·오류 정리·close와 기존 group drain 포함 |
| 외부 host PGID + 기존 full Bash | 4018 | 제품 변화 없음 | host tool은 개발용 별도 책임이며 제출 크기 절감으로 합산하지 않음 |

원문 fragment37 B와 실제 전체 bootstrap40/45 B를 섞지 않는다. 모든 비교는
동일한 full source·compiler·codec·header의 완성 파일을 인코딩·복원한 값이다.
더 작은 fragment를 whole 절감으로 계산하지 않는다. 기본판보다 작은 동등 계약
승자가 아직 없어 기존 compiler owner와 제출 파일은 유지한다. 후보는
`engines/experiments/compiler-ownership/`에 정본으로 보존하고 새로운 공개
`--wrapper` 옵션으로 자동 승격하지 않는다.

Group 정책의 초기4543 B 후보는 main thread가 Z이고 다른 thread가 살아 있는
경우를 고려하지 않아 미인수로 보존했다. 수정 후보는 leader의 WNOWAIT 종료와
live group을 함께 확인한다. Group 유예5초/KILL 후5초와 cleanup 오류의
workspace 보존은 기존 grace의 세 단계와 다른 계약이다. 10초의 엄격한 wall
상한이나 기존 grace와의 손실 없는 동일성으로 표시하지 않는다.

Subreaper는 고정 PGID·유일 reaper·SIGCHLD DFL 아래에서만 다룬다.
waitpid 결과0일 때만 group 신호 권한을 갖고 양수 PID 뒤에는 즉시 다시 wait,
ECHILD 뒤에는 해당 PGID에 더 신호를 보내지 않는다. Raw compiler status와
parent cancellation을 구분하며 C compiler -15의 기존 wrapper241을 parent143으로
바꾸지 않는다. PR_GET으로 원 subreaper 상태를 보존해 engine exec 전에 복원한다.

새 pidfd 예비실험은 일반 종료·TERM·FD1100에서 POLLIN, 반복 WNOWAIT의 동일
identity/status, proc state Z와 실제 FD close를 확인했다. 첨부의 이전 S/Z 실패는
재현하지 못했고 원인은 미확정으로 남긴다. Normal compile은 이미 blocking이므로
NPS·정상 시작 성능 개선으로 표시하지 않는다. Group 정착은 별도 책임이다.

로컬 WSL의 현재 `/init.scope`에는 `cgroup.kill/events`가 있지만 UID1000의
쓰기 권한은 없다. 이후 읽기 전용 조사에서
`user.slice/user-1000.slice/user@1000.service`의 directory/procs/subtree_control은
현재 사용자에게 쓰기 가능함을 확인했다. 현재 group의 제한만으로 로컬 전체의
위임 부재를 결론 내리지 않는다. 기존 user manager에서 시작하는 유한 transient
job의 실제 권한과 compiler 하위 범위는 아래 별도 실험에서 검증했다. 시스템 설정
변경·상시 서비스를 전제하지 않는다. Root에서 파일이 없는 현상도 API 미지원으로
해석하지 않는다.
[Kernel cgroup 문서](https://docs.kernel.org/admin-guide/cgroup-v2.html)의
계층 종료·populated와 child status 회수·reader 종료를 구분한다. 호스트 PGID 실험은
기존 Owned/Budget를 재사용해 job 종료를 소유하며 compile 직후의 별도 완료 fence나
다른 PGID의 containment를 보증하지 않는다. 권한 변경이나 새 서비스를 가정하지 않는다.

동등 fold는 두 표현 각각 모형6048조합과 실제14개 method/20개 compiler
fixture를 통과했다. Group 정책은9개 method/12개 wrapper port를 통과했으며,
주입125와 signal 오류는 외부 fixture가 회수한 경우를 artifact 정착 성공과
구분한다. Subreaper는12개 lifetime/error 사례와2개 직접 FFI/native flag 검사를
통과했고 directory cleanup9회가 terminal ECHILD 뒤인지 확인했다. Subreaper에는
변환 byte-inverse API가 없으므로 source/Popen/exec 보호·codec 복원·반복 생성과
실행 근거를 명시하며 다른 세 후보의 byte-inverse 증명을 승계하지 않는다.

Pidfd는7개 method와 실제 wrapper9개, high FD 및 마지막 thread probe를
통과했다. Main Z/2 TID 상태는 readable이 아니었고 마지막 thread 종료 뒤에만
POLLIN/WNOWAIT가 성립했다. EMFILE/ENOMEM은 경로 주입이며 실제 자원 고갈
재현으로 표시하지 않는다. 새 poll 오류가 이전 compiler7보다 먼저 보고되어
exit1이 되는 반면, 이미 진행 중인 parent 취소143은 유지되는 오류 우선순위도
별도 계약으로 기록한다.

호스트 PGID 모델은 record-only INT/TERM과 취소를 확인하는 Budget checkpoint를
사용해 setup/finally 중 비동기 예외를 던지지 않는다. 작은 고정 UCI 상호작용
범위의 모델이며 임의 blocking IO/spawn의 엄격한 wall-time 감독기로 일반화하지
않는다. 최신 canonical checker는7개 API 사례/6개 실제 job과 full Bash
quit/EOF2세션·8 legal GO를 통과했다. 실제 compiler 취소·보고 IO·정리 오류의
주 상태와 물리 정착을 구분했고 artifact4018/native identity는 그대로다.

네 Python 후보의 별도 실제 full F2 실행도 마감했다. 최종 v2에서 각2회 생성과
quit/EOF8세션·32 legal GO, 실제 GCC가 만든 native18576/3aaaacf7 및 source7712를
확인했다. Worker2개의 runnable 상태와 합계 CPU 증가를 관찰했으며 개별 worker
각각의 CPU 증가 증명으로 확대하지 않는다. Source/recipe 입력 연결이 약했던
v1의 실제8세션·32 GO는 별도로 보존하고 강화한 v2 통과로 소급하지 않았다.

Cgroup 실험은 기존 user manager가 시작한 고유 transient user service 안에서
완료했다. 자신이 만든 compiler 하위 cgroup에 한정해 다른 PGID의 후손까지
종료하고 populated0 → 원 자식 wait/reap → reader EOF/join → workspace 삭제를
확인했다. 두 fence는 compiler7 및 -9 오류 경로이며 실제 Rove compile/engine
성공 경로로 확대하지 않는다. Manager job-end cleanup과 launch 중 TERM143도
확인했으며 정확한 생성 unit들은 종료/not-found 상태다. 영구 unit·시스템 설정을
변경하지 않았다. 이는 toy compiler의 별도 호스트 기구 검증이며 현재 Bash
제품이나 외부 TCEC runner가 이 기구를 요구·제공한다는 뜻은 아니다.

동등 fold의 크기 동률과 나머지 후보의 크기 증가 때문에 현재 제출판에는 연결하지
않았다. 모든 새 정본은 별도 실험 폴더에 보존하며 모델·source 검토·실제 kernel
관측·full protocol 실행을 구분한다. 이후 TCEC 범위 축소 지시에 따라 이 실험들의
우선순위를 낮추고 종료 상태를 고정했다. 개발 runner는 자기 프로세스와 실패
근거를 계속 회수하지만 그 구현을 제출 payload에 싣는 의무를 만들지 않는다.

## TCEC 필수 범위 전문화

사용자가 2026-10-25 추가한 `Rove4k-TCEC-Scope-Audit.md`의 비필수 범위 축소를
적용하도록 요청했다. 첨부 SHA-256은
`c9bd1fd650b36472d61dd90cc98d299b454ef282382301dca1eaf35b9ac665c8`다.
이후 대회판의 비교 기준은 full 엔진과 작은 wrapper다. Full/reduced 기능 정책과
compiler·thread 실행 정책을 분리하고, N/B/R/Q 프로모션·합법수·반복·시간 관리와
GO 사이 상태 재사용을 유지한다. R/B 제거와 50수 기능 축소는 적용하지 않는다.

병렬 구현 범위는 최소 header, 프로세스 최종 종료 전용 join/free 제거, Rust A의
미사용 공유 observer·선택 UCI 제거, 매 GO thread 생성 구조, valid 입력 전용
parser다. Standalone grace와 개발 진단판은 기존 범위로 남기고 TCEC 출품에
WNOWAIT/procfs/125·같은 TID·Python 오류 순서의 전체 계약을 승계하지 않는다.

최소 header 동결 후 실제 비용은 기존 full source 그대로 A/B/C/E/F2/F8 각각
4080/4527/4223/4171/3866/3876 B다. Header는155/170/162/155/164/164 B다.
B는 사용되지 않는 -DWORKERS/-DTT_BITS/-DDEV만 제거했고 -std=c11은 유지했다.
Old/new CPP 전체와 native가 같음을 확인했으며33 B를 source 변경과 별도 기록한다.
해제·compiler 실패 시 실행 중단과 정상 지연 unlink는 유지하되 실패 전 임시파일
보존·임의 compiler family 정착·cleanup child 회수 등은 이 header의 보장이 아니다.

Process-final 후보는 종료 전용 flag·handle/created 복구·join/free를 묶어 제거한다.
여전히 살아 있는 다음 GO나 position의 완료 동기화는 유지한다. Per-GO는 learner
배열을 프로세스 동안 보존하고 thread만 생성·합류한다. 동기 후보의 ready 지연은
공식 UCI 동등성으로 표시하지 않는다. 선택 후보는 main 입력을 유지하고 마지막
worker의 atomic completion 뒤 결과를 내보내는 async 구조로 비교한다. 공식
isready/readyok는 선택 삭제 대상이 아니다.

Rust A는 shipping의 소비되지 않는 공유 nodes/quota·결과 복사와 선택 UCI를
분리하고 local nodes의256단위 시계 확인, stop atomic·TT lock·job/result
publication·완료 barrier를 유지한다. tiny_dev 진단 동작은 별도로 보존한다.
Source 재생성·native·whole·protocol의 새 근거를 만든 후에만 선택값을 갱신하며
기존8945 B를 새 입력의 통과로 승계하지 않는다.

### 현재 full 출품 선택

개별 runtime·header 이득을 단순 합산하지 않고 실제 결합 파일을 재생성한다.
새 정본은 `engines/experiments/tcec-scope/`와 Rust stream의 `tcec_build.py`다.
선택 literal recipe는 성공한 별도 비교와 실제 실행을 검토해 고정하며 빌더가
실행 출력으로 기대값을 자동 갱신하지 않는다. 전체 비용은 다음과 같다.

| Full 경로 | 이전 Bash/stream | TCEC whole | 절감 | 4096 B 기준 |
|---|---:|---:|---:|---|
| C A2 | 4232 | 3894 | 338 | 202 B 여유 |
| C B2 | 4712 | 4265 | 447 | 169 B 초과 |
| C C2 | 4375 | 4031 | 344 | 65 B 여유 |
| C E2 | 4323 | 3980 | 343 | 116 B 여유 |
| C F2 | 4018 | 3576 | 442 | 520 B 여유 |
| C F8 | 4028 | 3591 | 437 | 505 B 여유 |
| Rust A2 | 8945 | 7502 | 1443 | 3406 B 초과 |

C A/B/C/E는 process-final immediate → valid-input → getline-word를 적용한다.
B는 그 뒤 dead shipping score·재귀 전달 전용 SEE 인자·동등 상수/좌표/promotion
표현과 return/static macro를 축약하고 struct member namespace를 별도로 줄였다.
좌표와 promotion의 실제 유한 domain, 실제 원본/후보 c/h/Q/P의22 position·12검색·
34SEE Board/learner digest를 대조했다. Field 단계는 전 단계 native25912 B와
전체 bytes가 같으며 field 순서·타입·배열 폭을 바꾸지 않는다.

F2/F8는 async per-GO → valid-input → atomic operators → getline을 적용한다.
직접 atomic 대입·prefix decrement는 C11 seq_cst이며 정확히 W번의 감소와
마지막 worker의 결과 공개를 유지한다. F2는 word, F8는 같은3591 B에서 추가
타입 전제가 필요 없는 size_t를 택했다. Word는 실제 compiler의 size_t pointer
호환 assertion과 assertion 포함/미포함 native 동일성을 요구한다.

F2 source는7712→6901 B, F8는7868→7049 B, B는9744→8770 B다. Rust A는
22981→20655 B이며 공유 quota/observer·선택 shipping UCI·미사용 formatter를
제거했다. Native는339880→336960 B다. 읽기 전용 ELF 추출에서 Worker::search의
공유 qword lock은2→0, Table::slot의 별도 byte lock은1→1임을 확인했다. NPS나
기력 향상으로 확대하지 않는다. Tiny_dev의 quota·규칙·state·search·lifecycle·
selfplay·EOF·quit와 Rust14개 unit은 수정된 실제 all suite에서 통과했다.

Getline은 고정32KiB 배열과 oversized drain을 가장 긴 논리 줄까지 늘어나는
재사용 버퍼 하나로 바꾼다. 기존6입력과 operator 합성2입력의 두 선언형을 실제
검증해72compile/112실행이 모두0, stderr0이었다. 32767/32768/131073 B position과
1MiB 미지원 명령, 마지막 LF 없는 EOF, ENOMEM/EIO의 NULL·poison·첫 정상 읽기 후
실패를 포함하며 실패 버퍼를 검사하지 않는다. OOM은 API 실패 주입이며 호스트
메모리 고갈을 일으킨 실험은 아니다. Search가 읽는 상태의 수명은 계속 보호한다.

최소 wrapper는 정상 unlink를 유지하지만 실패 전 임시파일 잔존과 cleanup child
별도 reap을 보장하지 않는다. 최종 quit/EOF는 진행 중인 마지막 GO 결과를 생략할
수 있다. 다음 GO/position의 join·완료, learner 보존·게시와 active readyok는
이 양보와 별개로 유지한다. Wrapper의 실패 포트는 valid ELF를 남긴 compiler33,
tail 오류와 잘린 LZMA에서도 실행이 일어나지 않음을 실제 확인했다.

새 verifier는 선택한 thread 수명과 native image를 검사한다. Per-GO에 예전
stable TID·정확한 FD 집합·owner125를 자동 승계하지 않는다. F8는 로컬 CPU0–7을
단독 사용해8 worker 각각의 실제 CPU 증가와 active9/between1 TID를 확인했다.
이는128/256코어 확장성이나 기력의 근거가 아니다. Normal quit/EOF와 active
quit/EOF의 실제 source-JIT 네 세션을 프로필마다 별도로 수행하며 CI 인수는 최종
소스의 별도 run·artifact 결과로 기록한다.

기존 실패도 보존한다. C-final의 immutable oracle/FEN fixture 오류, B checker의
누락 minifier 경로, F8 외부 host AS2GiB와 기존 nested builder AS4GiB의 충돌은
원인별 새 실행으로 확인했다. 최초 preflight 실패를 engine 실패/통과로 바꾸지
않는다. Rust objcopy가 수정한 두 관측 복사본은 SHA gate에서 거절·격리하고 독립
원본 해시로 복원해 읽기 전용 추출로 재검증했다. 이전 full-objdump 한도 실패도
남겨 두었다. 이들은 정상 제품의 숨은 fallback이 아니다.

프로모션·draw·검색 기능을 축소한 결과를 full 경로의 성공으로 바꾸지 않는다.
외부 peer source는 비교에만 읽고 저장소에 포함하지 않는다. A/C/E/F가4KiB 안에
들어온 뒤에도 getline·F operator·B namespace 같은 추가 축약을 실제 비교했다.
B·Rust A의 남은 크기, 다른 A–F 후보와 D 경로, 실전 기력·대상 ISA·출전 적격성은
후속 범위다. Strong standalone owner를4KiB에 넣는 일을 출품판의 기본 목표로
되돌리지 않는다.

## 기준과 바로잡은 전제

- Full A/B/C/E/F2/F8의 완성 파일은 4807/5281/4944/4897/4590/4602 B다.
  D scalar/HQ는 5527/6037 B, Rust D scalar/HQ는 11080/11440 B다.
- Reduced F material-noise/move-TT는 4697/4425 B이며 아직 최신 full wrapper와
  같은 조합이 아니다. 이 차이를 기능 비용으로 계산하지 않는다.
- Rust의 9074 B는 보존된 four-file ZIP 대조군이다. 고정 2/18 source stream의
  현재 기록은 9009 B다. 해당 stream은 이미 Python 표준 라이브러리 decoder를
  사용하므로 self-decoder 도입을 새로운 성과로 집계하지 않는다.
- C 기반 memfd/execveat backend도 이미 있다. 새로운 Python single-native
  후보와 기존 C backend, ownELF 직접 메모리 진입은 서로 다른 포장이다.
- Rust D는 RFC1951 fixed-Huffman codec이다. C D H28의 512 MiB context를
  이 경로의 조건으로 가져오지 않는다. Rust D의 initialized pointer8 B와
  BSS4 B를 분리해 보존한다.

## 진행 단위

| 단위 | 구현과 판단 기준 | 시작 상태 |
|---|---|---|
| 공통 owner | 정리 권한 단일화, waitable leader의 중복 대기, 별도 immediate-KILL 생성 | 정식 API·focused·소비자 연결 및 실행 통과 |
| A/B/C/E template | environment 인라인·signal loop와 owner 축약의 개별/결합 비용 | 결합 16개 비용 후 grace 승자 정식 재현·실행 통과 |
| Reduced F | 각 원래 source/native/codec으로 최신 template·W1/W2/seek 연결 | grace/kill 각각 정식 재현·실행 통과 |
| 단일 native | archive 일반성을 제거한 filesystem FD 정책 | API·실제 ELF fixture·generic CLI 전달 통과, source 포장보다 큼 |
| Python memfd | 유효 ELF, 명시 executable flag, target 정책, 완전 기록과 FD exec | 별도 API·실행 검증 통과, 기존 source 포장보다 큼 |
| 최소 shell | 동일 source/native, 확인된 복원·compile 실패, 지연 삭제와 취소 차이 | F2/F8 명시 Bash 정책 재현·실행 통과, 출전 대상 미확정 |
| Rust stream | 명시 Rust envelope의 W1/W2/seek, 고정 source의 resource env 제거 | Git LF 입장 경계 수정 후 8945 B 재현·선택 실행 통과 |
| Rust D body | exact prefix232/restored image/absolute BCJ/decoder bound | 두 형식 normal/positive 통과, 첫 공유 묶음 |

## 소유권과 연결

Compiler cleanup의 생성 책임은 `compiler_group.py` 안에서 공유한다. 기존
정확한 legacy 출력은 과거 검사와 대조군을 위해 유지하며, 새 policy를 명시해
선택한다. 새로운 표현을 각 builder에 복제하거나 과거 입력의 hash 검사를
느슨하게 만들지 않는다. `compiler_stdin.py`의 Rust envelope는 별도 명시적
contract로 재구성하고 C 기본 admission과 출력은 유지한다.

Rust의 `r4s-` prefix, compiler environment, 음수 returncode의 128+signal
mapping, engine argv[1:]를 C와 무심코 통일하지 않는다. Generic native는
기존 sys.argv 전체와 부모 environment를 유지한다. 새 single-native는
command 없는 단일 유효 ELF에만 적용하며 multi-file/source/script에 숨은
fallback을 만들지 않는다.

기본 owner는 원 leader를 WNOWAIT로 유지하고 group 정착 후 reap한다.
leader의 종료는 손자의 종료가 아니다. 정상 compile의 무제한 대기와 단계별
5초 budget은 합치지 않는다. 정착 실패의 125·workspace 보존과 준비/spawn
실패의 원래 오류·cleanup을 구분한다. Test host도 회수한 옛 PGID에 뒤늦게
signal을 보내지 않도록 실제 소유 경계를 고친 후 실패 검사를 실행한다.

## 현재 첫 비용

| 후보 | 대조 whole | 후보 whole | 해석 |
|---|---:|---:|---|
| Full F2 정리 권한 단일화 | 4590 | 4576 | -14 B, 정식 ordinary/selected 통과 |
| Full F2 중복 leader wait 재구성 | 4590 | 4591 | +1 B, 별도 후보로 보존 |
| Full F2 위 두 변경 결합 | 4590 | 4577 | -13 B, state-only보다 1 B 큼 |
| A template + state | 4807 | 4785 | -22 B, 정식 ordinary/selected 통과 |
| B template + state | 5281 | 5259 | -22 B, 정식 ordinary/selected 통과 |
| C template + state | 4944 | 4924 | -20 B, 정식 ordinary/selected 통과 |
| E template + state | 4897 | 4878 | -19 B, 정식 ordinary/selected 통과 |
| Full F8 state | 4602 | 4588 | -14 B, 정식 ordinary/selected 통과 |
| Rust D scalar body232 | 11080 | 11026 | -54 B, 아래 normal/positive 인수 완료 |
| Rust D HQ body232 | 11440 | 11384 | -56 B, 별도 형식으로 측정 |
| Rust fixed2/18 prepared + resource env 생략 | 9009 | 8945 | -64 B, native 전체 동일, 선택 실행·fixture 통과 |
| F material-noise aligned73 + state/grace | 4697 | 4616 | 원래 reduced 기능·codec 유지, ordinary/selected 통과 |
| F material-move-TT aligned73 + state/grace | 4425 | 4342 | 원래 reduced 기능·codec 유지, ordinary/selected 통과 |
| F full2 최소 source shell/inherit | 4590 | 4011 | SIGCHLD 기본 상태의 child 회수 조건 미충족, 미선택 |
| F full2 Bash source shell/ignore-after-compile | 4590 | 4026 | header316 + source payload3710, 정식 재현·실행 통과 |
| F full8 Bash source shell/ignore-after-compile | 4602 | 4028 | header316 + source payload3712, 정식 재현·실행 통과 |

이는 고정 입력·codec·header의 실제 완성 파일 첫 비용이다. 단독 절감량을
합산하지 않는다. 실패 원본과 비교 입력, 실제 제품·보고서는 저장소 밖에
보존한다. 정식 source와 선택한 recipe에서 재현하고 실제 새 파일의 실행
범위를 확인한 후에만 유지 후보로 기록한다.

### Rust D body232 인수

위 body232 첫 비용 이후 정식 source7을 동결하고 기존 ordinary를 한 번
실행했다. Scalar/HQ native4·audit2·encode4·loader4가 모두 원 기대 tuple을
재현했다. Compiled native16816 B와 기존 load16392 B는 보존하고, prefix232가
zero인 restored image를 별도 파일·SHA로 기록한다. Initialized memcpy pointer8 B,
BSS4 B, entry와 mapping 주소·권한·guard는 그대로다. `--image-policy legacy-full`
선택도 원래 tuple을 보존하며 이번 새 runtime은 body232 선택에 한정한다.

기존 positive 한 번이 native/whole × scalar/HQ × quit/EOF의 8세션과
64개 legal GO를 통과했다. 각 3 TID, 실제 five-page image, data8·BSS4·padding,
guarded worker stacks, stdio·reader·물리 종료를 확인했다. Compile은 CPU2,
positive는 CPU2–3이었다. 기존 원 owner의 WNOWAIT 정착 후 reap으로
forced0/owned0이며, source7과 선언된 closure18은 실행 전후 같다.

Actual build475492 B의 SHA-256은
`b76222600aa4d5ff168d6373931ecb5ea9c5d9fbaac51dd569be688508eb7253`,
runtime206000 B는
`549c778566c761d39fd06c131571f518d004034108afa1f4bf88c4fbe75f7646`다.
현재 standalone native audit를 유지하며, C D의 CHECKPOINT 방식을 새 필수
구조로 추가하지 않았다. 출전 적격성과 전체 loader fault 인수는 별도다.

첫 공유 커밋 `cd79ffd84baf3d69ac778691d455caf4f5e7e5ba`의
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/40103605933),
[NVCompact CI](https://github.com/daejunnom/Rove4k/actions/runs/40103605917),
[repository CI](https://github.com/daejunnom/Rove4k/actions/runs/40103606021)는
모두 성공했다. 새 Rust 실제 JSON4개는 body232 두 형식의 재현·복원·8세션64GO와
기존 queue 경계2건을 현재 Git source에 연결한다. 최종 인덱스150419 B의
SHA-256은 `148093888932769fc9388ddfa8296ba34efedb6fc478810bd2c32d44f2138ea6`다.
이 커밋 뒤의 공통·shell·consumer 변경은 위 CI에 포함되지 않는다.

### 공통 API와 개별 결합 비용

`compiler_group.py`의 `render_cleanup`은 기존 emitter와 새 prepared-owner가
공유한다. `normalize_bootstrap` 뒤 `compact_cleanup(state=True, wait=False)`를
호출하고 역순으로 두 inverse를 적용한다. 원래 legacy 여섯 형태의 전체
bytes·metadata는 유지된다. 새 focused 검사는 surviving grandchild, 두 125
보존 경로의 deadline 반환 주입, preparation/spawn/compiler 실패, grace와
kill의 차이를 실제 작은 fixture로 확인했다. 실제 kernel D 상태를 유발한
검사는 아니다.

ABCE의 state-only/template-only/결합을 각각 실제 encode했다. 선택한 결합은
4785/5259/4924/4878 B이며, wait 결합은 각각 2 B 더 컸다. F2 state/wait/결합은
기존 첫 비용을 현재 API의 바이트 재생으로 연결했고, F8 state는 독립 4588 B다.
즉시 KILL은 F2/F8 4551/4565 B, reduced material/move 4591/4311 B다. 이 수치는
서로 다른 종료 계약이며 기본 grace의 성공으로 합치지 않는다.

새 helper들을 함께 둔 기존 scripts unittest도 한 번 실행했다. 48개 method 중
47개 통과, optional identifier compiler gate가 설정되지 않은 1개는 skip이다.
전후 source/test closure32가 같고 원 owner는 WNOWAIT·group 정착·최종 reap,
forced0/owned0으로 닫혔다. 별도 strace나 compiler shim은 넣지 않았다.
인덱스36682 B의 SHA-256은
`7af82f2d3cfbcc80fc04741f4ecde2f5c7433100bd5816d85fcd3af756302658`다.

ABCE의 정식 source12를 동결한 뒤 각 ordinary `--dev`와 변경하지 않은 selected
verifier를 한 번씩 순차 실행했다. Shipping과 DEV 각 두 번을 재현했고, source와
native의 기존 identity는 유지됐다. 새 bootstrap/whole은 첫 비용의 전체 바이트와
같다. 실제 quit/EOF 8세션을 통과했고, 각 엔트리의 기존 관측 범위 안에서 native,
startup3 TID, private path·children 부재, 합법 결과와 물리 종료를 확인했다.
FD 열거 등 기존 verifier가 기록하지 않는 항목을 새 성공으로 넓히지 않는다.
실행 전후 producing source12/closure가 같고 forced0/owned0이다. 외부 인덱스
92142 B의 SHA-256은
`2898072ce127dc3ec357300196cc6e46e6eec34a977b01912c7c7e9c383b9de5`다.

### Single-native 소비자 인수

`pack.py`는 `native_backend=archive|file|memfd`를 제공하고 generic `build.py`의
`--native-backend`가 first/repeat 양쪽에 같은 frozen ELF validator를 전달한다.
기본 archive와 source 출력은 이전 전체 bytes·metadata를 유지한다. `--no-pack`
에서는 새 preflight나 ELF callback을 호출하지 않는다. 정책 거절은 compile
전에 기록되며 filesystem이나 약한 memfd flags로 fallback하지 않는다.

실제 tiny ELF의 두 transport × file/memfd 실행, argv/environment/stdio/exit17,
short write·zero progress·write/exec/secondary-close 오류, INT/TERM의 물리
130/143과 cleanup을 확인했다. Generic CLI와 실제 packaging AST 전달 검사도
통과했다. 전체 generic engine main의 새 실행이나 canonical TinyRust CLI의
새 선택 노출로 확대하지 않는다.

| 같은 native의 고정 LZMA/ZIP 포장 | archive | file | memfd | maintained source |
|---|---:|---:|---:|---:|
| F2 native18576 | 7744 | 7764 | 7710 | 4590 |
| C D scalar native7292 | 5911 | 5935 | 5881 | 5527 |

각 native API는 구현·focused 검증까지 완료했지만 이 조건에서는 maintained
source/ownELF보다 크므로 기본 제출 경로로 선택하지 않는다. 값은 각 whole의
실측이며 archive 대비 이득을 source 대비 이득으로 바꾸지 않는다.

### Rust stream 인수

고정 source22981 B에만 두 resource env override를 생략한다. W1/W2/seek-only
8961 B, env-only8989 B, 결합8945 B를 각각 측정했다. 실제 ordinary는 ZIP2와
세 stream codec 각각 두 번을 재현했다. 선택 XZ8945 B의 실제 실행은 queued
uci/isready, seekable compiler FD0, private0700 경로, live native339880 B의
원래 c477f362… 해시, 3 TID, 두 수의 합법성 및 quit exit0을 확인했다.
독립 oracle는 in-process chess oracle이며 전체 shipping suite는 별도다.

준비 입력 fixture는 legacy6/prepared42 encode와 실제 Rust control/artifact
compile2를 포함한다. SIGCHLD 복구, compile 실패, TERM/INT의143/130, 원 leader
WNOWAIT→group 정착→reap과 owned0을 기록했다. 현재 선택 host compile은
Rust D의 기존 owner/reader를 소비하도록 고쳤다. Canonical TinyRust의
`stable.run` 및 선택하지 않은 `--smoke-selected`의 모든 timeout 경로까지
고쳤다고 주장하지 않는다. Runtime 인덱스는19850 B,
SHA-256 `94bd6d46974971800098340c69f369f8a1dbec9f1072446cab014b8e0f48d3ff`다.

Environment 인라인은 snapshot 시점과 동시 할당/파일 준비 실패의 첫 오류
순서를 바꿀 수 있다. Signal loop의 private binding 관측도 달라진다.
이 범위를 숨긴 채 임의 Python hook·introspection·전체 failure trace의
동등성을 주장하지 않는다. Immediate KILL은 부모 128+signal과 group 정착을
유지하더라도 compiler graceful 처리 기회를 제거하는 별도 계약이다.

### 최소 shell의 관측 계약

Source shell은 먼저 압축 payload를 별도 파일로 확보하고 xz 복원을 확인한 뒤
compile하므로 POSIX pipeline의 마지막 status만 믿지 않는다. Private mktemp
directory와 compiler TMPDIR, stage별 실패 상태·EXIT cleanup, 원 cwd/env/argv의
관계를 작은 실제 fixture로 확인했다. Native shell도 유효 ELF를 요구한다.
F native shell7308 B는 source 후보보다 커서 선택하지 않는다.

가장 짧은 sh/inherit4011 B는 cleanup child의 zombie를 엔진이 회수해야 한다.
Dash에 `trap '' CHLD`를 추가해도 exec 대상의 SIGCHLD는 DFL로 관측되어 첫 검사가
실패했다. 같은 ignore 정책을 명시 `/bin/bash`로 실행한 tiny source/native는
SIGCHLD IGN을 유지하고 종료한 cleanup child를 남기지 않았다. 따라서 최종
ignore 후보는 header316 B의 Bash이며 sh로 fallback하지 않는다. 이 정책은
process child를 fork/wait하지 않는 고정 엔진에만 선택한다.

Bash에 부모만 TERM을 보낸 별도 관측은 parent signal15, 살아 있는 compiler
자손과 host의 강제 정리1을 기록했다. Private directory의 EXIT 삭제와 compiler
group의 물리 정착은 다른 결과다. Grace owner의 신호 mapping·group 보장을
승계하지 않는다. 지연 삭제가 끝나기 전의 경로·cleanup child 존재, engine
조기 종료 뒤 orphan 회수의 target 의존성도 명시한다.

동일 원 source/compiler/codec으로 비교한 Bash whole은 A4232/B4712/C4375/E4323,
F2/F8은4026/4028 B다. ABCE는 아직4096 B를 넘는다. 각각의 header와 payload를
실제 측정했으며 F의 이득을 다른 엔진에서 단순 차감하지 않았다. ABCE shell은
첫 비용으로 보존하며 runtime 채택은 하지 않는다.

F2는 full/material-noise/material-move-tt 세 기능 정책과 grace/kill의 여섯 조합, full shell 한
조합을 각각 두 번 재현했다. 요청한 grace 세 조합의 변경 없는 DEV도 두 번씩
생성했다. Strict 12세션48 legal GO와 별도 shell 2세션8 legal GO를 통과했다.
최초 shell snapshot parent 생성 누락은 compile 전에 실패했고 원 결과를 보존한
뒤 mkdir 한 줄로 수정했다. 기존 여섯 producer의 source snapshot과 후속 수정
builder를 한 closure로 거짓 표기하지 않고 정확한 한 줄 inverse와 새 shell
ordinary로 연결한다. 통합 인덱스20019 B의 SHA-256은
`8544749bec79b6a29a844c7b5e9fa5afdec92f8fd6c29e228bd38f8c43b7737d`다.

F2 shell의 정식 4026 B whole은 quit/EOF 두 세션에서 초기 named executable과
cleanup child를 관측하고, 같은 native와 TID가 살아 있는 동안 경로·child가
사라졌음을 확인했다. 원 stdin pipe·FD012·SIGCHLD IGN·NX/no-WX와 closing result,
reader EOF·물리 종료를 확인했다. 정리 관측은 약2초이며 target의 보장 시간으로
일반화하지 않는다. Runtime23274 B의 SHA-256은
`7d048716f11e18d4b884eabce352128edfdcf112cb5a4bc97e0291bef173da57`다.

F8도 grace/kill/shell ordinary와 각 selected를 순차 실행했다. Whole은 각각
4588/4565/4028 B를 두 번 재현했고 native6 compile·shipping6 encode·control3
encode·strict restore6을 기록했다. 총6세션24 legal GO에서 동일9 TID,
main S·모든8 worker R와 개별 CPU tick 증가, native identity·stdio·NX/no-WX와
정착 후 reap을 확인했다. Shell은 초기 경로·child와 약2초 후 삭제·자동 회수를
추가로 확인했다. Source4와 closure80은 전후 같다. Compile CPU0, selected는
CPU0–7 단독이었다. Ordinary의 원 parentAS4/childAS1 GiB, strict의AS4 GiB,
shell의AS2 GiB를 구별해 유지했다. 모든 원 owner가 forced0/owned0으로 닫혔다.
F8 최종 인덱스41184 B의 SHA-256은
`762d88a0550d60aaff9be763cfa3b240a348f4ed0dd1f560bc9ee3bd70f38a80`다.

## 대상과 외부 근거

고정 커밋의 [c4ke launcher](https://github.com/citrus610/c4ke/blob/ca95d3ac5e59f4759534dffb7ab1b28afa922d74/launcher.sh),
[ice4 launcher](https://github.com/MinusKelvin/ice4/blob/fabe3b1a805a1418e56899a3a143a955a399535c/launcher.sh),
[4ku launcher](https://github.com/kz04px/4ku/blob/917a08741cef43d6ae00552df214cc66d0c46489/src/launcher.sh),
[STRO4K unpack](https://github.com/ONE-RANDOM-HUMAN/STRO4K/blob/51ea73a3d86141d96ad428402dc387722fc0f9b1/unpack.sh)의
실제 원문을 외부에서 읽었다. 앞의 두 source compile 경로, 4ku의 임시 파일로
redirect하는 출력, STRO4K의 native 복원과 지연 삭제를 구분했다. 이들의 짧은
launcher 원문 길이를 Rove4k 공동 압축 bootstrap 비용에서 직접 차감하지 않는다.
외부 엔진 source는 저장소에 추가하지 않았다.

[현재 TCEC 4K 규정](https://wiki.chessdom.org/Rules#7._4k_specific_rules)을
확인했다. 단일 4096 B, 60초 이내 시작, 남는 파일 정리와 허용 외부 명령,
최소 4K UCI를 일반 TCEC 옵션 요구와 구분한다. 예시 shell의 `rm` 사용과
명시 명령 목록이 일치한다고 가정하지 않고, 새 최소 shell은 허용된 Python
정리 경로로 비교한다. 다른 엔진이 사용했다는 사실만으로 적격을 확정하지
않는다.

별도의 4K ELF 규정은 외부 프로그램을 금지한다. 새 Bash/Python 포장은 일반
4K의 script 경로이며 이 ELF 종목의 자기완결 요건을 통과했다고 표시하지 않는다.

[Linux memfd 정책](https://docs.kernel.org/userspace-api/mfd_noexec.html)의
`MFD_EXEC`, namespace의 `vm.memfd_noexec`와 Python FD exec 지원을 확인한다.
강제 금지에서 flags나 filesystem으로 우회하지 않는다. 현재 WSL의 성공은
출전 target 지원의 증명이 아니다. 이름 있는 삭제 파일에서 memfd로 바뀌는
`/proc/self/exe` 관측은 명시한다.

## 공유 상태와 남은 인수

F2와 F8에는 build-only `--wrapper grace|kill|legacy|shell`을 연결했다. 기본은
grace이며 engine 기능 `--policy`와 별개다. Shell은 full 기능에만 노출하고
header와 Python bootstrap을 다른 산출물로 기록한다. F2의 처음 여섯 ordinary는
통과했지만 새 shell snapshot의 recipe parent 생성 누락으로 일곱 번째가 compile
전에 실패했다. Parent mkdir 한 줄로 원인을 수정했고 원 실패와 앞선 여섯
producing snapshot을 보존했다. 후속 shell ordinary와 strict 실행, F2/F8 shell
전용 positive 및 F8 세 정책의 단독 인수는 위 범위대로 완료했다.

구현 커밋 `d0d67dfb4d65256879ded738a074b1a2acbc0a68`의 자동
[engine CI](https://github.com/daejunnom/Rove4k/actions/runs/40106422656)는 C job이
성공하고 Rust job은 source stream의 LF 입력 경계에서 실패했다. 새 C actual22개는
기본 여섯 경로와 reduced F grace 두 개, full F kill/shell, F8 shell의 각 재현·
선택 실행을 포함한다. [NVCompact](https://github.com/daejunnom/Rove4k/actions/runs/40106422653)와
[repository](https://github.com/daejunnom/Rove4k/actions/runs/40106422649)는 성공했다.
Rust의 prepared fixture는 통과했지만 해당 run의 ordinary/selected와 뒤 단계는
성공으로 승계하지 않는다. 실패 인덱스100114 B의 SHA-256은
`b01127eade35d8f6842ceb39da4a5229bc151cbfaf420e84b1fc405516709935`다.

원인은 Windows raw `search.rs`의 마지막 DEV test 선언 뒤 CRLF 한 바이트를
원래 checkpoint가 고정했던 것이다. Git 정본9047 B와 작업사본9048 B는 해당
CRLF→LF 한 곳 외 전체가 같고, specialize/prune·merge·resource embodiment·
bootstrap 생성 결과가 각각 전체 동일하다. 이 확인은 pure source 경로이며
새 native/whole 재현을 대신하지 않는다. 후속 builder는 known source/helper
텍스트를 CRLF→LF로 정규화하고 lone CR을 거절한 뒤 Git LF 단일 SHA를 검사한다.
원 raw와 canonical bytes·SHA, EOL 변경 여부를 별도 input manifest에 보존한다.
Canonical Rust 엔진 원문과 `.gitattributes`, stable TinyRust builder는 바꾸지
않았고 raw 해시 예외 목록을 늘리지 않았다.

Windows 원 raw를 그대로 둔 새 ordinary `--reproduce`와 selected가 다시 통과했다.
LF canonical intake와 Windows CRLF intake가 같은 frozen closure를 만들며 단일
변조는 hash guard에서 거절한다. ZIP9074 B, stream8945 B, native339880 B의 전체
기존 identity와 반복 재현이 유지된다. 이전 실패 run은 보존하며, 이후 원격
CI의 정확한 commit·결과·actual intake는 같은 Draft PR #12와 외부 인덱스에
기록한다. 로컬 통과를 원격 CI 통과로 바꾸지 않는다.

이번 여덟 단위의 구현·고정 비용 비교·관련 로컬 인수는 완료했다. 더 큰 native,
wait 결합과 sh/inherit 후보는 미선택 근거를 보존한다. 다음 작업은 ABCE와 D의
full 파일 축약, F의 grace 계약을 유지하는 추가 축약 및 Bash 경로의 여유 확대,
대상 환경·ISA·시작/정리·기력과 비교 대국이다. 관련 위험을 다루는 기존 검사와
작은 보완을 사용하며 새 의무 schema나 고정 검사 수를 만들지 않는다. 소스
동일성, 실제 실행, CI, PR 통합과 최종 출전 적격성은 각각 기록한다. 이 묶음의
완료가 전체 A–F의 4 KiB·기력·대상 하드웨어 인수를 대신하지 않는다.
