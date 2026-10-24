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

현재 후속 선택과 실행 상태는 [후속 압축과 엔진별 Bash 인수](#후속-압축과-엔진별-bash-인수)에
기록한다. 아래 감사 기준과 시작 기준의 숫자는 각각 명시한 과거 source에 한정한다.

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
