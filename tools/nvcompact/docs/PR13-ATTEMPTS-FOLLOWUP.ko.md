# PR #13 후속: 실패 후보 보존·자동 비교·Boolean 인식

2026-10-21에 구현·검토·측정을 완료했다. **같은 입력과 같은 탐색 설정의 26개 입력·프로파일에서 이전 PR #13 최소 파일을 모두 바이트 단위로 유지했다.** 이번 후속 변경의 추가 파일 크기 절감은 0바이트이며, 크기 회귀도 0건이다. 이전 PR #13이 확보한 압축 이득은 그대로 유지된다.

- 규약·Boolean 체크포인트: `79b4b90a3c547e25802327fee944e4e9b73660f3`.
- 이번 구현: `83e8deda7cde105c57de697816b5b9eeffc93b34`.
- 이전 결과: PR #13 `5ff450725d240f502ea1da7286a96752c575bdee`, 실행 소스 `c5f4af0cfff7d7c6863dd142631f80b9f697e81a`.
- A–F 입력: PR #12 `0e716e0b366272c66749f6e7194f64cb715e2d00`. 이후 달라진 엔진 입력을 이 비교에 섞지 않았다.
- 상세 근거: [압축·재생성·보존 비교](../evidence/pr13-followup/comparison.json), [테스트·검토 기록](../evidence/pr13-followup/tests.json).

## 1. 실패한 압축 수정을 어떻게 보존하는가

루트와 NVCompact의 작업 규약에 실패·미채택 후보를 재검토할 근거를 남기도록 추가했다. 크기가 커서 탈락한 경우, 의미·컴파일·재현 검사에 실패한 경우, 예산 때문에 끝내 확인하지 못한 경우를 구분한다. 뒤의 성공으로 앞의 실패를 덮거나 입력별 예외와 검사 약화로 성공을 만들지 않는 원칙을 유지했다.

Rust 구현은 `source_search` 실행마다 원래 payload, 원래 C, 후보 C와 후보를 만든 기준 C를 해시별 파일로 저장한다. 편집 근거, 도구·계약, 실제 전체 파일 비용, 검증과 거절 이유는 append-only 이벤트에 남긴다. 실패한 조합도 구성 후보의 식별자와 기준 소스를 보존한다. 같은 소스가 같은 ELF로 컴파일되더라도 소스와 Python 리터럴 표기별 압축 비용을 합쳐 버리지 않는다.

| 파일 | 내용 |
| --- | --- |
| `context.json` | 입력·도구·계약·실제 비용 조건 |
| `objects/<sha256>` | 원래 payload/C와 보존 후보의 실제 바이트 |
| `events.jsonl` | 편집·측정·검증·거절·한도 기록 |
| `index.json` | 완료 상태와 파일별 해시가 있는 보존 목록 |
| `comparison.json` | 실행 종료 시 자동 생성하는 측정 비교 |

추가 후보 소스의 기본 보존 예산은 **64 MiB**이며 0–512 MiB로 설정할 수 있다. 원본 입력은 기존의 각각 8 MiB 한도에서 별도 보존한다. 보존 한도에 닿으면 새 선택적 탐색을 중단하고 마지막 검증 결과를 유지한다. 시간·출력·이벤트 예산도 별도로 존재하므로 모든 가능한 후보를 조사했다는 뜻은 아니다.

탐색 실패 뒤 보존 목록 마감이나 보조 오류 보고서 쓰기까지 실패하는 경우 원래 오류와 뒤의 오류를 함께 보고한다. 강제 종료로 마감되지 않은 기록은 부분 자료로 남는다. 없는 완료 상태를 만들어 비교 성공으로 처리하지 않는다.

## 2. 자동 비교의 범위

새 `compare-attempts` 명령은 최대 16개 보존 디렉터리 또는 `index.json`을 읽고, 총 1 GiB 읽기 한도 안에서 실제 파일 해시를 확인한다. 원본 입력, 컴파일러·Clang·NVCompact 빌드, 관측 계약, 원본의 재현된 native/진단 결과, header·decoder·codec 비용 조건이 맞는 기록끼리 비교한다. 조건이 다르면 별도 그룹으로 남긴다.

크기 순위와 의미 판정, 과거 실행의 선택 여부는 별도 필드다. 작은 파일이 나왔다는 사실만으로 의미 검증을 통과했다고 표시하지 않는다. 컴파일 성공 기록만 있고 명시적인 채택 판정이 없는 후보도 `not-checked`로 남긴다. 과거 결과를 읽는 동작은 새 도구에서의 재검증이나 후보 자동 재채택이 아니다.

실제 이번 캠페인에서는 소스 탐색을 사용한 **8개 기록의 13,037개 비교 행**을 새 CLI로 비교했다. 서로 다른 입력·비용 조건에 따라 8개 그룹이 만들어졌고 53,075,666바이트를 읽었다. 비교 행에는 같은 C의 여러 리터럴 스타일, 중간 채택, 미측정 기록이 포함되므로 고유 엔진 수나 독립 알고리즘 수로 해석하지 않는다. 각 실행이 자동 생성한 비교 파일도 보존됐다.

현재 체크아웃에서 도구를 빌드한 뒤 사용할 수 있는 명령은 다음과 같다.

```sh
npm run build:nvcompact
npm exec -- nvcompact compare-attempts \
  /absolute/external/run-a/source-search/source-search/attempts \
  /absolute/external/run-b/source-search/source-search/attempts/index.json \
  --output /absolute/external/attempt-comparison.json
```

위 경로는 `envelope --output /absolute/external/run-a`의 기존 중첩 출력 구조를 따른다. `--output`은 새 파일이어야 한다. 명령은 저장된 컴파일·엔진·loader·codec 명령을 실행하지 않는다. 새 의미·복원 검증을 포함한 채택은 현재 입력의 새 탐색 또는 기존 `replay` 계약으로 처리한다. 전체 사용법과 계약은 [소스 포트폴리오 가이드](SOURCE-PORTFOLIO.md#7-preserve-attempts-and-compare-recorded-measurements)에 있다.

## 3. Boolean 축약에서 실제로 고친 부분

`a != 1 → !a`와 `1 != a → !a`는 값의 범위가 `{0,1}`로 증명될 때 기존 규칙이 지원했다. 이번에 규칙을 중복 추가하지 않고, 실제 타입 판정이 놓치던 두 경우를 수정했다.

1. Clang 20은 `<stdbool.h>`가 활성화되면 실제 C `_Bool`을 AST에서 `bool`로 표시할 수 있었다. typedef를 desugar한 뒤 정확한 canonical `bool`만 `_Bool`로 정규화한다. `typedef int bool`은 끝까지 `int`다.
2. `const _Bool` 등은 실제 lvalue-to-rvalue 변환 뒤의 값 타입을 확인한다. 변환을 모두 벗긴 노드의 타입만 보다가 Boolean 증명을 잃던 문제를 수정했다. 나중에 Boolean 목적지에 대입된다는 이유로 원래 정수의 범위를 추론하지 않는다.

| 표현의 전제 | 처리 |
| --- | --- |
| 실제 `_Bool`/`bool` 또는 그 typedef, 적격한 qualified 값 | `a != 1`, `1 != a`를 `!a` 후보로 만들 수 있음 |
| 비교·논리식 등 기존의 0/1 결과 | 기존 Boolean-domain 규칙과 재파싱된 후속 pass 적용 가능 |
| `typedef int bool` 또는 일반 `int` | 이름만 보고 0/1로 가정하지 않음 |
| signed 1-bit field | -1 가능성을 유지하며 해당 Boolean 범위 증명 제외 |
| macro 영향, volatile/atomic 접근 등 보호 대상 | 기존 보호 조건 유지 |

예를 들어 일반 정수 `a=2`이면 `a != 1`은 1이고 `!a`는 0이다. 따라서 아무 정수 조건식에 적용하는 문자 치환은 구현하지 않았다. 실제 Boolean 반환 함수 호출과 postincrement도 평가 횟수를 유지하는지 자체 fixture로 검사했다. 연쇄 변환은 매 pass마다 변경된 소스를 다시 파싱한다.

원문이 짧아졌다는 이유로 최종 파일에 무조건 채택하지 않는다. 기존과 같이 타입·binding·변환 조건을 지키고 실제 compiler/native/진단 및 payload 복원 검사를 통과한 후보의 **전체 제출 비용**을 비교한다. 이번 고정 엔진 입력에서는 새 Boolean 후보가 추가 파일 절감으로 이어지지 않았다.

## 4. 같은 조건의 크기 비교

전체 26행은 A–F 9개, 공개 General 11개, 공개 ELF 2개, 자체 예제 4개다. General의 4k.c와 ELF v9.0은 같은 공개 파일을 서로 다른 부문 경로로 검사하므로 고유 엔진 26개라는 뜻은 아니다.

A–F와 ELF는 이전과 같은 `thorough=false`, General은 `thorough=true`, 모두 `jobs=2`와 동일한 notation 설정을 사용했다. 후보는 이번에 새로 압축하고 재생성했다. 기준선은 앞선 실제 결과를 재사용하면서 파일 크기·해시·검증 영수증을 다시 대조했다.

### A–F

| 입력 | 이전 PR #13 최소 파일 | 이번 결과 | SHA-256 |
| --- | ---: | ---: | --- |
| A | 4,616 B | 4,616 B | 동일 |
| B | 5,173 B | 5,173 B | 동일 |
| C | 4,979 B | 4,979 B | 동일 |
| D HQ ELF | 6,175 B | 6,175 B | 동일 |
| D scalar ELF | 5,966 B | 5,966 B | 동일 |
| E | 5,038 B | 5,038 B | 동일 |
| F full | 4,611 B | 4,611 B | 동일 |
| F material/noise | 4,331 B | 4,331 B | 동일 |
| F material/move-TT | 4,047 B | 4,047 B | 동일 |

F material/move-TT의 4,047바이트는 4,096바이트 아래의 축약 프로파일이다. full F는 4,611바이트이며 이 둘을 같은 기능의 결과로 표시하지 않는다.

### 공개 General

| 입력 | 이전 PR #13 최소 파일 | 이번 결과 | SHA-256 |
| --- | ---: | ---: | --- |
| 4k.c | 3,932 B | 3,932 B | 동일 |
| 4ku | 4,088 B | 4,088 B | 동일 |
| M4sseur | 4,092 B | 4,092 B | 동일 |
| STRO4K | 4,078 B | 4,078 B | 동일 |
| c4ke | 4,092 B | 4,092 B | 동일 |
| ice4 | 4,082 B | 4,082 B | 동일 |
| molly | 4,095 B | 4,095 B | 동일 |
| moonfish | 3,871 B | 3,871 B | 동일 |
| pygone | 4,020 B | 4,020 B | 동일 |
| sunfish | 2,776 B | 2,776 B | 동일 |
| we4k | 4,011 B | 4,011 B | 동일 |

### 공개 ELF

| 입력 | 이전 PR #13 최소 파일 | 이번 결과 | SHA-256 |
| --- | ---: | ---: | --- |
| 4k.c-v8.0 | 4,042 B | 4,042 B | 동일 |
| 4k.c-v9.0 | 3,932 B | 3,932 B | 동일 |

### 자체 예제

| 자체 예제 | 이전 | 이번 결과 | 검증 |
| --- | ---: | ---: | --- |
| native-build | 16,056 B | 16,056 B | 파일 동일·독립 verifier/replay 통과 |
| mixed | 504 B | 504 B | 파일 동일·독립 verifier/replay 통과 |
| zero-tail | 441 B | 441 B | 파일 동일·독립 verifier/replay 통과 |
| c-rewrites | 2,141 B | 2,141 B | 파일 동일·독립 verifier/replay 통과 |

22개 엔진·프로파일 모두 이번 binary로 독립 `replay`를 새로 실행하여 최종 파일을 정확하게 재생성했다. 자체 예제 4개는 별도 verifier와 독립 재빌드를 통과했다. source search가 채택한 native 파일과 compiler stdout/stderr는 해당 실행의 원본과 모두 일치한다.

## 5. 테스트와 독립 검토

- 전체 로컬 Rust 검사 **65개 통과**: 라이브러리 51, packing 10, source search 4.
- 마지막 보조 실패 보고서의 오류 전달 수정 뒤 영향받는 source search **4개를 다시 실행하여 통과**했다. 전체 65개를 그 직후 로컬에서 다시 실행했다고 주장하지 않는다. 실제 검사 대상 파일 해시와 좁은 변경 범위를 [테스트 기록](../evidence/pr13-followup/tests.json)에 남겼다.
- Boolean 관련 Clang 20 검사 **8개 통과**. 일반 정수 반례, stdbool·typedef·const, 명시적 cast, 반대쪽 피연산자, 부작용, 재파싱 후 연쇄 축약과 보호 대상을 다룬다.
- 보존 소스 변조, 비용 조건 불일치, 부족한 필드, 컴파일만 끝난 후보의 오인 수락 방지, 보존·평가 한도, 원본 컴파일 실패, codec 실패, 탐색과 보존 오류의 동시 발생을 검사했다.
- 별도 협업 에이전트들이 Boolean 적용 범위와 아카이브/선택 상태·경계 처리를 검토했다. 작성자 혼자 검토한 것을 외부 승인으로 표시하지 않는다.

구현 커밋의 [NVCompact CI](https://github.com/daejunnom/Rove4k/actions/runs/39549856293)는 Node 22·24 모두 통과했다. Rust 검사, launcher·회귀 보고·배포 경계 검사, 실제 offline-installed npm tarball 검사까지 포함한다. [저장소 수명주기 CI](https://github.com/daejunnom/Rove4k/actions/runs/39549856299)도 Node 22·24 모두 통과했다. 이는 확인한 구현 커밋의 상태이며 이후 문서 커밋의 CI와 구분한다.

## 6. 보존한 실패·불일치와 한계

첫 Boolean 테스트는 모든 규칙을 함께 사용하는 recipe가 특정 pass에서 반드시 Boolean-domain을 선택해야 한다는 과도한 단정 때문에 7개 통과·1개 실패였다. 실제로 더 짧은 동치 비교 반전도 선택할 수 있다. 독립 출력 oracle과 생산 코드는 유지하고, domain-only와 결합 recipe의 검사를 나누어 고쳤다. 첫 실패와 8개 통과 재실행 로그를 모두 보존했다.

첫 A–F 비교 helper는 이전의 `thorough=false`에 맞추지 않고 `--thorough`를 켰다. 이 조건 확대에서 A는 4,616→4,614바이트, C는 4,979→4,978바이트가 나왔지만, 소스·payload·native 결과는 같고 마지막 LZMA 조합 탐색만 달랐다. 이 결과를 이번 구현의 절감이나 같은 조건의 회귀 검사로 계산하지 않았다. 완료한 A/B/C/D 기록과 중단한 E 자료를 유지하고, helper가 이전 summary의 설정을 읽어 일치 여부를 검사하도록 수정한 뒤 별도 새 출력에서 다시 실행했다. 위 표는 이 수정된 비교만 반영한다.

기존의 7개 A–F historical native-pin 실패, 원본 Moonfish decoder 실패, C의 frontend 출력 한도는 원래 상태로 보존한다. 기대 해시나 엔진 TT·worker·탐색 정책을 바꾸어 통과시키지 않았다. 현재 고정 입력에서의 native 동일성과 원래 역사적 빌드 성공은 다른 주장이다.

엔진, Python bootstrap과 사용자 정의 ELF loader는 실행하지 않았다. compiler/decoder와 유한한 자체 산술 fixture는 실행했다. 이 보고서는 UCI, 기력, 대국, many-core 런타임이나 실제 서버 출전 인수를 새로 증명하지 않는다. 외부 엔진 소스·압축 payload·실행 파일·시도 아카이브는 저장소와 npm 패키지에 벤더링하지 않았으며, Git에는 구현·규약·검토된 출처와 결과만 추가했다.
