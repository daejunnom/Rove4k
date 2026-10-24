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
| 공통 owner | 정리 권한 단일화, waitable leader의 중복 대기, 별도 immediate-KILL 생성 | 정식 API와 focused 통과, 소비자 연결 중 |
| A/B/C/E template | environment 인라인·signal loop와 owner 축약의 개별/결합 비용 | 결합 16개 비용 완료, grace 승자 연결 중 |
| Reduced F | 각 원래 source/native/codec으로 최신 template·W1/W2/seek 연결 | grace/kill 각각 측정 완료, 정식 연결 중 |
| 단일 native | archive 일반성을 제거한 filesystem FD 정책 | API·실제 ELF fixture·generic CLI 전달 통과, source 포장보다 큼 |
| Python memfd | 유효 ELF, 명시 executable flag, target 정책, 완전 기록과 FD exec | 별도 API·실행 검증 통과, 기존 source 포장보다 큼 |
| 최소 shell | 동일 source/native, 확인된 복원·compile 실패, 지연 삭제와 취소 차이 | Dash SIGCHLD 실패 보존, 명시 Bash 정책 검증 중 |
| Rust stream | 명시 Rust envelope의 W1/W2/seek, 고정 source의 resource env 제거 | 8945 B 재현·선택 실행·prepared fixture 통과 |
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
| Full F2 정리 권한 단일화 | 4590 | 4576 | -14 B, 아직 runtime 채택 전 |
| Full F2 중복 leader wait 재구성 | 4590 | 4591 | +1 B, 별도 후보로 보존 |
| Full F2 위 두 변경 결합 | 4590 | 4577 | -13 B, state-only보다 1 B 큼 |
| A template + state | 4807 | 4785 | -22 B, 정식 ordinary/selected 통과 |
| B template + state | 5281 | 5259 | -22 B, 정식 ordinary/selected 통과 |
| C template + state | 4944 | 4924 | -20 B, 정식 ordinary/selected 통과 |
| E template + state | 4897 | 4878 | -19 B, 정식 ordinary/selected 통과 |
| Full F8 state | 4602 | 4588 | -14 B, 정식 소비자 실행 전 |
| Rust D scalar body232 | 11080 | 11026 | -54 B, 아래 normal/positive 인수 완료 |
| Rust D HQ body232 | 11440 | 11384 | -56 B, 별도 형식으로 측정 |
| Rust fixed2/18 prepared + resource env 생략 | 9009 | 8945 | -64 B, native 전체 동일, 선택 실행·fixture 통과 |
| F material-noise aligned73 + state/grace | 4697 | 4616 | 원래 reduced 기능·codec 유지, runtime 전 |
| F material-move-TT aligned73 + state/grace | 4425 | 4342 | 원래 reduced 기능·codec 유지, runtime 전 |
| F full2 최소 source shell/inherit | 4590 | 4011 | SIGCHLD 기본 상태의 child 회수 조건 미충족, 미선택 |
| F full2 Bash source shell/ignore-after-compile | 4590 | 4026 | header316 + source payload3710, 정식 실행 전 |
| F full8 Bash source shell/ignore-after-compile | 4602 | 4028 | header316 + source payload3712, 정식 실행 전 |

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
실제 측정했으며 F의 이득을 다른 엔진에서 단순 차감하지 않았다. 새 선택은
정식 producer 재생성과 전용 `verify_shell.py` 실행을 마친 뒤 채택한다.

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

## 남은 인수

F2와 F8에는 build-only `--wrapper grace|kill|legacy|shell`을 연결했다. 기본은
grace이며 engine 기능 `--policy`와 별개다. Shell은 full 기능에만 노출하고
header와 Python bootstrap을 다른 산출물로 기록한다. F2의 처음 여섯 ordinary는
통과했지만 새 shell snapshot의 recipe parent 생성 누락으로 일곱 번째가 compile
전에 실패했다. Parent mkdir 한 줄로 원인을 수정했고 원 실패와 앞선 여섯
producing snapshot을 보존한다. 현재 후속 shell ordinary와 strict 실행, F2/F8
shell 전용 positive 및 F8 세 정책의 단독 인수가 진행 중이다. 새 source의 CI와
이 로컬 인수는 완료 전까지 별도 pending이다.

현재 첫 비용의 runtime·취소·정리 검증, 각 엔진의 독립 결합 비용과 재현,
새 compiler/codec/loader 정책의 소비자 pin 연결을 순서대로 진행한다.
관련 위험을 다루는 기존 검사와 작은 보완을 사용하며 새 의무 schema나
고정 검사 수를 만들지 않는다. 소스 동일성, 실제 실행, CI, PR 통합과
최종 출전 적격성은 각각 기록한다. 이 묶음의 완료가 전체 A–F의 4 KiB·기력·
대상 하드웨어 인수를 대신하지 않는다.
