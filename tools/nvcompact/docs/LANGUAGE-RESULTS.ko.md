# C++·Rust 자문 확장: 실제 검증과 미지원 범위

이 기록은 PR #16의 C 도메인·n-version 구현 뒤에 추가한 언어 확장을 다룬다.
설계와 명령 계약은 [LANGUAGE-ADVISOR.ko.md](LANGUAGE-ADVISOR.ko.md),
C 단계·refinement 성능의 비교 기준과 결과는
[DOMAIN-PERFORMANCE-RESULTS.ko.md](DOMAIN-PERFORMANCE-RESULTS.ko.md)에 있다.
각 단계의 과거 검사 수를 최종 검사 수에 중복해서 더하지 않는다.

## 1. 구현한 기능

`advise-source SOURCE --language c|cpp|rust`를 추가했다. `c++`는 `cpp`의 별칭이다.
기존 `advise-c`와 C rewrite는 C 전용 의미 계약을 유지한다.
원문 bytes를 다루는 압축 기능은 언어와 독립적이다.
Python·JavaScript 등은 입력 읽기와 frontend 호출·출력 생성 전에 명시적 미지원 오류로 종료한다.
고정 폭 분석의 미지원은 원문 bytes를 압축하는 기능의 미지원을 뜻하지 않는다.

| 책임 | 구현 |
| --- | --- |
| 공통 포함 영역 | 구간·known bits·유한 집합, 분기 정제·합류·대입 시 사실 무효화 |
| 공통 후보 탐색 | 유한 정수 문법, 공유 DAG, 전체 typed 결과 벡터를 이용한 중복 계산 제거 |
| C++ admission | Clang의 실제 AST·binding·타입·value category, 보수적인 built-in scalar 함수 부분집합 |
| Rust admission | 주변 item을 포함한 bounded parser, primitive 타입 확인, 별도의 Rust evaluator |
| Rust 최종 후보 | Rust 문법으로 렌더링한 뒤 재파싱·타입 검사·포함 영역 전체 재평가 |
| 보고서 | `findings`·`ranges`와 언어별 `language_details`, 원본 변경·압축 후보 생성 0 |
| 동적 관측 | 기존 C에서만 지원. C++·Rust의 profile·instrument 요청은 명시적 거절 |

C++에는 prvalue 대상만 제안하고 후보의 타입과 값 범주를 함께 보존한다.
정수와 bool은 구분하며 실제 승격·변환을 유지한다. 오버로드·객체·참조·비지역 읽기 등
허용 범위를 벗어난 함수는 전체를 보류한다.

Rust의 파일은 최상위 `fn`·`pub fn`만 허용한다. import·type alias·attribute·module·impl·macro 등은
파일 전체를 보류하고, 알 수 없는 본문 구문은 해당 함수 전체를 보류한다.
`i32/u32/i64/u64/bool`의 명시적 바인딩, 지역 대입·분기·return·순수 scalar 식을 지원한다.
bool 입력의 후보 합성, 반복문·호출·참조·shadowing·전체 crate liveness는 지원하지 않는다.

## 2. 독립 네이티브 비교

도구가 실제로 출력한 positive finding을 자체 원본 함수에 하나씩 삽입했다.
따로 컴파일한 원본과 제안 함수의 입력별 결과를 비교했다. 외부 엔진을 컴파일하거나 실행한 검사가 아니다.

| 의미 문맥 | 실제 제안 | 원본 함수와 입력 비교 | 추가 검사 | 결과 |
| --- | ---: | ---: | --- | --- |
| C++17 | 73 | 87,809 | 73개 `decltype` 타입·값 범주 검사, UBSan | 불일치·UBSan 오류 0 |
| C++20 | 73 | 87,809 | 73개 `decltype` 타입·값 범주 검사, UBSan | 불일치·UBSan 오류 0 |
| Rust2021, overflow checks ON | 54 | 64,366 | 54개 결과 타입 검사 | 불일치 0 |
| Rust2021, overflow checks OFF | 같은 54 | 64,366 | 같은 54개 결과 타입 검사 | 불일치 0 |

C++은 여섯 지원 정수 타입, Rust는 네 지원 정수 타입을 포함했다.
동일한 Rust 후보를 두 overflow 설정에서 검사한 것이므로 서로 다른 제안 108개로 세지 않는다.
이 표는 유한 fixture 비교이며 전체 프로그램의 동치나 모든 가능한 후보의 증명이 아니다.
상수 cast 접기 전 Rust 결과는 24개 제안·30,936개 입력 비교였다. 그 기록을 보존하고,
최종 typed 상수 접기 이후 같은 fixture를 다시 분석해 위 54개 제안·64,366개 비교를 확인했다.
최종 Rust fixture는 11함수·34식·37읽기에서 생략·함수 보류·불완전 탐색 없이 54개 finding을 냈다.

### Rust 전용 범위 의미

후보 생성용 C 모델이 일부 Rust 연산을 보류하므로, 출력된 후보 비교만으로는 Rust 범위 전파의
모든 지원 연산을 확인할 수 없다. 이를 보완하기 위해 자체 함수 8개에서 다음을 별도로 확인했다.

- 정수 `!`와 음수 signed right shift.
- 상위 비트가 버려지는 signed/unsigned left shift.
- signed/unsigned 재해석, 폭 축소·확대 cast.
- bool에서 정수로의 cast.

overflow checks ON·OFF 각각 **5,402개**, 총 10,804개 native 관측값이 보고된 포함 영역 안에 있었고,
관측된 결과 집합은 보고된 유한 결과 집합과 일치했다. 이는 입력 타입 전체의 전수 실행을 뜻하지 않는다.
보고서의 Rust 식 41개에 대해 직렬화한 `domain_values`, cardinality, hash와 후보의 영역 hash도 확인했다.
유한 영역 목록은 display summary의 256개 생략 한도와 별개로 최대 4,096개까지 남긴다.

### admission·자원 한도

늦게 나타나는 최상위 item의 파일 전체 보류, 본문의 함수 전체 보류, raw string 안의 가짜 함수,
reserved name, cast 뒤의 `<`·`<<` 문법, checked overflow, 5,000개 cast chain을 확인했다.
flow와 n-version 예산을 각각 1,000으로 제한했을 때 실제 계수가 그 한도를 넘지 않았고,
불완전한 결과를 `complete=false`로 보고했다. Python은 존재하지 않는 입력·compiler를 넘겨도
먼저 명시적 언어 오류로 종료했다.

## 3. 감사에서 수정한 근본 원인

| 원인 | 반영한 수정 |
| --- | --- |
| C++ 전용 생성자가 내부에서 C-only 표준 검사를 다시 호출 | 전용 frontend 진입점에서 언어별 설정 검증을 일관되게 소유 |
| C 정수 carrier만으로 C++ bool·값 범주가 사라질 수 있음 | 노드별 실제 타입·category 확인과 명시적 변환 보존, 후보 surface 재검사 |
| 숫자 literal이 bool 문맥으로 추론되는 오류 | 일반 타입 resolver에서 정수 spelling과 bool을 분리; guard·return·논리·bitwise·local에 적용 |
| Rust cast 뒤의 angle 연산자가 generic 문법으로 해석될 수 있음 | 언어별 괄호 렌더링과 최종 후보 재파싱·타입 검사 |
| 평평한 `as` chain이 깊이 제한만으로 충분히 제한되지 않음 | expression node 수에 cast도 포함 |
| primitive 이름을 바꾸는 주변 item을 무시할 위험 | 함수 추출 전에 전체 파일 item 계약을 확인 |
| `(x & 1) + constant`의 중간 유한 영역을 잃음 | exact scalar image 뒤에 유한 피연산자 영역의 보수적 Cartesian 전파를 추가 |
| 후보 상수에 C 승격을 나타내는 Rust cast가 남아 `u32/i64/u64` 축약 길이가 늘어남 | 하나의 `cast_node`에서 정수 목적 타입의 상수값을 기존 Rust cast 의미로 접고 타입·위치는 유지 |
| 전체 식과 단락 RHS 읽기 영역을 같은 값으로 기대한 테스트 | 전체 entry 64개와 RHS 56개·16..119를 각각 독립적으로 확인 |

초기 Rust 검사 실패 로그와 수정 전후 이유는 그대로 보존했다.
부분적으로 계산한 값이나 예산 소진 뒤의 결과를 완전한 집합으로 채택하지 않는다.
서로 다른 에이전트가 설계·통합과 flow·예산·타입 경계를 읽기 감사하고 별도 oracle을 실행했다.
이 검토를 사람의 PR 승인으로 표현하지 않는다.

## 4. 이전 TCEC 입력을 그대로 비교한 결과

과거에 보존한 원문 bytes를 사용했고 원문·헤더를 제거하거나 함수만 추출해 성공으로 바꾸지 않았다.
분석용 Clang 구문 문맥과 release 컴파일은 다르다. 외부 엔진의 build/run은 하지 않았다.

| 입력 | 정본 지문·크기 | 실제 분석 결과 |
| --- | --- | --- |
| 4ku | `a5d32dc962ebf717faccbff2a2b3644b61c2f4e7d7304cf6a3cd9810936950e7`, 10,308 B | 정본 wrapper의 C++20 문맥으로 재확인했지만 전체 TU AST가 128 MiB 출력 한도에 도달. 증명 불완전 오류 |
| ice4 | `0980ed274f09d24069160427cba3885e8324076b39ca42e087c4e5ed6fa1dbf0`, 8,750 B | GNU++17, 같은 128 MiB AST 출력 한도. 증명 불완전 오류 |
| Molly | `9411457e5b9f17ce3bc5dde00c6e198aafa2a3cd5a4f074bc944be58bd78cb0a`, 13,486 B | Rust2021 보고서 생성, 주변 item에 의해 파일 전체 보류. 분석 함수·finding 0, `complete=false` |

4ku의 첫 GNU++17 시도는 잘못 고른 분석 문맥이었다. 그 실패를 보존하고, 실제 catalog·wrapper의
C++20 및 `-pthread`·`-march=native` 문맥으로 한 번 수정해 확인했다. 소스는 바꾸지 않았다.
지원 언어를 늘렸어도 이 전체 엔진들에 대한 정적 축약 성공을 얻었다고 주장하지 않는다.

PR #12 F·Moonfish의 C 결과와 4k.c의 C23 미지원, Python 고정 폭 분석의 미지원은
[C 단계 결과](DOMAIN-PERFORMANCE-RESULTS.ko.md)에 별도 기록되어 있다.
언어 어댑터 지원은 전체 프로그램 CFG·함수 간 계약·메모리 별칭·템플릿·crate 분석을 완성한 상태가 아니다.

## 5. 전체 통합 검증과 근거

Rust 1.99.1과 실제 Clang 20을 지정한 전체 workspace 테스트에서 **152개 통과, 실패 0개**를 확인했다.
library 125개, advice 3개, C++ advice 4개, packing 10개, source-search 10개다.
0개인 main/doc-test 그룹은 합계에 추가하지 않는다.
이후 상수 cast의 일반적 접기와 회귀 검사 1개를 추가했으며, 영향받는 Rust 검사 **10개가 모두 통과**했다.
`u32/i64/u64`에서 `x+8&48==0`를 실제로 생성·보존하고 각 64개 입력과 bool 타입을 확인했다.
최종 head의 전체 CI 상태는 PR에 별도로 기록한다.
Node launcher 5개, comparison reporter 1개와 repository lifecycle 7개도 통과했다.
Lifecycle의 첫 sandbox 실행은 임시 fixture의 `git init`에서 `EPERM`으로 실패했다.
테스트를 수정하지 않고 허용된 재실행으로 7개가 통과했으며 양쪽 로그를 보존했다.

첫 독립 감사에 고정한 debug CLI는
`fa190e0963cfa42c993373c81884d021e394daa3c2a333d4b6a1d2f7cb5c8837`이다.
workspace edition에 맞춘 rustfmt와 상수 cast 접기 이후 최종 debug CLI는
`d413e8169df96090dd39e2b3a4d7441366812bb95bdfa8bf9c8fb7a611c6ad36`이다.
영향받은 Rust 네이티브 비교를 다시 수행하고, 바뀌지 않은 C++·외부 입력 결과는 해당 소스 지문으로 연결한다.
앞선 snapshot의 로그·바이너리·결과는 보존했다. 성능 소스는 이 언어 확장에서 바뀌지 않았다.

실행 명령, 소스·바이너리·보고서·원시 로그 지문, 실패·보류 결과는
[language-validation.json](../evidence/pr16/language-validation.json)에 있다.
0.6.0 버전을 올리기 전 개발 패키지와 통합 검증 기록은
[language-integration.json](../evidence/pr16/language-integration.json)에 둔다.
이 snapshot은 source version 0.5.0을 사용한 후속 개발 빌드다. 이미 게시된 npm 0.5.0과는
다른 artifact이며, 아래 hash를 새 0.6.0 배포 파일의 식별자로 사용하지 않는다.
후속 버전·게이트·공개 결과는 [0.6.0 릴리스 노트](RELEASE-0.6.ko.md)의 경로에서 확인한다.

### 버전 갱신 전 release-mode 개발 빌드·설치 패키지

공식 build 접점으로 당시 최종 소스를 빌드하고, 그 source fingerprint가 당시 입력과 일치하는 것을
확인한 뒤 tarball을 만들었다. 실제 오프라인 설치본에서 **10개 계약 검사·11회 명령 실행**을 통과했다.
자체 native fixture의 정상 입력 256개·오류 입력 2개, 독립 재현과 명시적 실행 검증 경계,
새 Rust 자문, 설치 파일 bytes·mode 불변을 포함한다. Node는 v24.19.0이다.

같은 설치본에서 공개 자체 C++·Rust 예제도 추가 실행했다. 각각 3함수를 분석했고,
C++ template 1개와 Rust method 호출 함수 1개는 예상대로 보류했다.
C++는 15개 finding·9곳의 읽기, Rust는 19개 finding·8곳의 읽기를 기록했다.
두 입력 원문과 설치 파일은 바뀌지 않았고 압축 후보 수는 모두 0이었다.
공백을 포함한 원문 byte 차이도 finding 길이에 포함되므로 finding 수를 구조적 개선 수로 읽지 않는다.

- 이 snapshot의 release-mode CLI: 12,320,360 B,
  SHA-256 `78acfdc10d3c64e9b4745c64991d39365e41ba92648424f0e6f4bffd1739e92b`.
- 로컬 tarball: 4,220,740 B,
  SHA-256 `8fdfb43b56d2c47bf532aff9e83d82b77fad7b10225f7effb6b86956211c973d`.
- package inventory: 도구 실행 파일·launcher·metadata·문서·license 9개 파일.
  외부 엔진 소스·실행 파일은 포함하지 않는다. 이 개발 도구의 크기는 엔진 4 KiB 제출 크기와 별개다.

이 snapshot의 검증 작업에는 npm registry 게시와 PR 병합을 포함하지 않았다.
