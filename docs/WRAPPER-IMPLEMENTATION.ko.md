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
| 공통 owner | 정리 권한 단일화, waitable leader의 중복 대기, 별도 immediate-KILL 생성 | 첫 비용 후 공통 emitter 구현 중 |
| A/B/C/E template | environment 인라인·signal loop와 owner 축약의 개별/결합 비용 | 개별 첫 비용 완료, 공통 API 연결 전 |
| Reduced F | 각 원래 source/native/codec으로 최신 template·W1/W2/seek 연결 | 첫 비용 진행 중 |
| 단일 native | archive 일반성을 제거한 filesystem FD 정책 | 공통 packer와 focused 검증 구현 중 |
| Python memfd | 유효 ELF, 명시 executable flag, target 정책, 완전 기록과 FD exec | 파일 정책과 독립 구현·측정 중 |
| 최소 shell | 동일 source/native, 확인된 복원·compile 실패, 지연 삭제와 취소 차이 | 별도 첫 비용 진행 중 |
| Rust stream | 명시 Rust envelope의 W1/W2/seek, 고정 source의 resource env 제거 | 공통 입력 정의와 소비자 구현 중 |
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
| A template | 4807 | 4797 | -10 B, owner 변경과 미결합 |
| B template | 5281 | 5272 | -9 B, owner 변경과 미결합 |
| C template | 4944 | 4936 | -8 B, owner 변경과 미결합 |
| E template | 4897 | 4885 | -12 B, owner 변경과 미결합 |
| Rust D scalar body232 | 11080 | 11026 | -54 B, 아직 loader 진입 검증 전 |
| Rust D HQ body232 | 11440 | 11384 | -56 B, 별도 형식으로 측정 |
| Rust fixed2/18 prepared + resource env 생략 | 9009 | 8945 | -64 B, 두 native compile 전체 동일, runtime 전 |
| F material-noise aligned73 + state/grace | 4697 | 4616 | 원래 reduced 기능·codec 유지, runtime 전 |
| F material-move-TT aligned73 + state/grace | 4425 | 4342 | 원래 reduced 기능·codec 유지, runtime 전 |
| F full2 최소 source shell/inherit | 4590 | 4011 | 첫 비용, 지연 정리·SIGCHLD 관측 검증 중 |

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
구조로 추가하지 않았다. 아직 새 커밋의 CI 및 출전 적격성을 뜻하지 않는다.

Environment 인라인은 snapshot 시점과 동시 할당/파일 준비 실패의 첫 오류
순서를 바꿀 수 있다. Signal loop의 private binding 관측도 달라진다.
이 범위를 숨긴 채 임의 Python hook·introspection·전체 failure trace의
동등성을 주장하지 않는다. Immediate KILL은 부모 128+signal과 group 정착을
유지하더라도 compiler graceful 처리 기회를 제거하는 별도 계약이다.

## 대상과 외부 근거

[현재 TCEC 4K 규정](https://wiki.chessdom.org/Rules#7._4k_specific_rules)을
확인했다. 단일 4096 B, 60초 이내 시작, 남는 파일 정리와 허용 외부 명령,
최소 4K UCI를 일반 TCEC 옵션 요구와 구분한다. 예시 shell의 `rm` 사용과
명시 명령 목록이 일치한다고 가정하지 않고, 새 최소 shell은 허용된 Python
정리 경로로 비교한다. 다른 엔진이 사용했다는 사실만으로 적격을 확정하지
않는다.

[Linux memfd 정책](https://docs.kernel.org/userspace-api/mfd_noexec.html)의
`MFD_EXEC`, namespace의 `vm.memfd_noexec`와 Python FD exec 지원을 확인한다.
강제 금지에서 flags나 filesystem으로 우회하지 않는다. 현재 WSL의 성공은
출전 target 지원의 증명이 아니다. 이름 있는 삭제 파일에서 memfd로 바뀌는
`/proc/self/exe` 관측은 명시한다.

## 남은 인수

현재 첫 비용의 runtime·취소·정리 검증, 각 엔진의 독립 결합 비용과 재현,
새 compiler/codec/loader 정책의 소비자 pin 연결을 순서대로 진행한다.
관련 위험을 다루는 기존 검사와 작은 보완을 사용하며 새 의무 schema나
고정 검사 수를 만들지 않는다. 소스 동일성, 실제 실행, CI, PR 통합과
최종 출전 적격성은 각각 기록한다. 이 묶음의 완료가 전체 A–F의 4 KiB·기력·
대상 하드웨어 인수를 대신하지 않는다.
