# C++·Rust 숏코딩 자문: 언어 경계와 지원 계약

## 1. 입력 언어를 명시한다

`advise-source SOURCE --language c|cpp|rust`는 사용자가 고른 언어의 정적 자문을 수행한다.
`c++`도 `cpp`의 별칭으로 받는다. 기존 `advise-c`는 C 전용으로 유지한다.
확장자나 C와 비슷한 구문만으로 다른 언어를 C 분석에 넣지 않는다.

Python·JavaScript 등 다른 언어는 `unsupported advisory language` 오류와 비정상 종료 상태를 반환한다.
이 경우 frontend를 호출하거나 보고서·계측 파일을 만들기 전에 중단한다.
이는 해당 언어를 압축할 수 없다는 뜻이 아니다. 이 명령의 고정 폭 값 영역·식 합성 분석을
지원하지 않는다는 명시적 계약이다. Python 원문의 bytes를 포장하는 기존 계약과도 별개다.

| 언어 | 선택과 기본 문맥 | 구현한 의미 경계 |
| --- | --- | --- |
| C | `--language c`, 기본 `c11` | 기존 LP64·2의 보수 정수 분석, 선택형 C 계측·표본 수입 |
| C++ | `--language cpp`, 기본 `c++17` | Clang의 실제 C++ AST에서 허용한 built-in scalar 부분집합 |
| Rust | `--language rust`, 기본 `rust2021` | 매크로를 확장하지 않는 제한된 primitive scalar 구문·타입 분석 |
| Python 등 | 명시적 미지원 | 다른 언어로 재해석하거나 고정 폭을 가정하지 않음 |

C++의 표준 선택은 C++17/C++20 및 GNU 변형이다. Rust는 `rust2021`/`rust2024`에서
공통으로 지원하는 구문 부분집합을 다룬다. 지원 표준을 선택해도 그 언어 전체를 분석한다는 뜻은 아니다.

## 2. 공유할 책임과 언어가 소유할 책임

값 영역의 교집합·합류·known bits·유한 값 집합과 제한된 후보 문법은 공통으로 사용한다.
같은 입력 영역에서 같은 부분식을 반복 평가하는 비용도 공통 n-version 엔진이 관리한다.
각 언어의 바인딩, 타입 추론, 실행될 연산, 후보 spelling과 최종 판정은 언어 어댑터가 소유한다.

현재 공통 후보 생성 IR은 C 정수 모델을 사용한다. C++·Rust 어댑터는 이를 **후보를 찾는 내부 표현**으로
사용하며, 이 IR의 비교 성공만을 원래 언어의 제안으로 내보내지 않는다.
실제 source-language 타입·정의성 조건을 다시 만족한 후보만 finding이 된다.
C++는 공통으로 정의된 연산만 허용하고 Clang의 노드별 타입·value category와 후보의
표면 타입을 확인한다. Rust는 별도의 Rust evaluator로 원본과 후보를 다시 평가한다.
두 어댑터가 모두 별도의 전체 언어 실행기를 두었다는 뜻은 아니다.
따라서 공통 IR이 표현하지 못하는 유효한 C++·Rust 대안은 발견하지 못할 수 있다.
이 제한을 언어의 정의되지 않은 동작이나 전체 최적성으로 설명하지 않는다.

보고서의 공통 `findings`·`ranges`는 소비자가 확인할 위치와 결과다.
C++·Rust의 상세 식·언어 타입·영역·판정 근거는 `language_details`에 둔다.
기존 C의 `expressions` 필드에 다른 언어의 내부 carrier 증명을 넣지 않는다.
기존 range의 `c_type` 키는 호환성을 위해 유지하며 해당 언어의 타입 spelling을 기록한다.
frontend/context는 언어·표준·의미 모델을 식별한다. 다른 언어의 cache·관측을 재사용하지 않는다.

## 3. C++에서 추가로 확인하는 내용

C++ frontend는 `-x c++`와 선택한 표준으로 실제 AST·타입·binding을 얻는다.
기존 압축·C rewrite frontend의 C 표준 허용 범위를 넓혀서 우회하지 않는다.
C++ 자문에서만 별도의 명시적 frontend 진입점을 사용한다.

C++ built-in 비교·논리 연산의 결과는 `bool`이다.
따라서 `x==1`과 정수 `x`가 0·1 값을 같게 내더라도 일반 값 문맥의 타입이 같지는 않다.
어댑터는 bool과 정수의 source 타입을 구분하고, 정수 승격·명시적 변환도 유지한다.
예를 들어 정수 rank 식의 논리 결과와 mask의 논리 부정은 모두 bool일 수 있지만,
같은 값을 내는 정수 산술식으로 바꾸는 것은 별도의 타입 판정이 필요하다.

값과 타입이 같아도 lvalue/prvalue가 다르면 `decltype`·overload 문맥에서 차이가 난다.
현재는 prvalue 대상만 제안하며, 변수 `x`나 glvalue인 `x?x:x`를 수치만 같다는 이유로
prvalue의 대안으로 채택하지 않는다. 후보의 타입과 value category를 함께 보존한다.

초기 지원 대상은 namespace·language-linkage 안을 포함한 비오버로드 free function과
보통 자동 저장의 `int`·`unsigned int`·`long`·`unsigned long`·`long long`·`unsigned long long`이다.
중간 bool 식과 bool literal은 처리한다. bool 변수·매개변수, pointer/reference,
qualified/static 지역변수, nonlocal 읽기·호출, named cast와 알 수 없는 AST node는 함수 전체를 보류한다.

오버로드된 연산자, 사용자 정의 변환, reference alias, template 의존식, 객체 수명과
비정상 제어 흐름을 보통 정수 연산으로 낮추지 않는다.
허용 범위를 벗어나는 함수는 이유와 함께 보류한다.
내부 C 의미의 보수적 제한 때문에 음수 signed shift 등 일부 유효한 C++ 연산도
현재 후보 발견 범위에서 제외될 수 있다.
유한 numeric 대표 후보를 먼저 보관한 뒤 C++ 타입·category로 걸러내므로,
이 대표 예산 밖의 유효한 C++ 대안을 모두 열거했다고 주장하지 않는다.

## 4. Rust에서 추가로 확인하는 내용

Rust 입력은 bounded tokenizer/parser로 허용한 구문만 읽는다.
원본 crate를 빌드하거나, Cargo build script·procedural macro·선언 매크로를 실행하지 않는다.
파일 최상위에는 `fn`·`pub fn`만 허용한다. `use`·`type`·`const`·`mod`·`impl`·attribute·macro 등
다른 item이 있으면 **파일 전체를 보류**한다. 원시 타입의 이름을 가리는 주변 문맥을 무시한 채
함수만 추출하지 않는다. 함수 본문에 지원하지 않는 구문이 있으면 그 함수 전체를 보류한다.

명시적인 `i32`·`u32`·`i64`·`u64`·`bool` 매개변수와 초기값이 있는 지역변수,
`mut` 지역 대입, `if`/`else` block, `return`, 함수 끝의 식, primitive scalar 연산과 정수 `as` cast를
처리한다. 호출·메서드·참조·반복문·변수 shadowing은 현재 지원하지 않는다.
`else if`는 현재 parser의 지원 구문이 아니다.
bool의 범위와 타입은 분석하지만 bool 입력을 대상으로 한 후보 합성은 명시적으로 보류한다.
정수 입력으로부터 bool 결과를 만드는 비교·논리식은 후보 합성 대상이다.
허용된 함수 안의 typed 정수 상수 중복과 읽히지 않은 매개변수·지역변수도 보고한다.
crate 전체의 미사용 함수를 판단하지는 않는다. Rust에서 `--compiler-arg`는 거절한다.

Rust는 C의 implicit integer promotion을 사용하지 않는다. 비교 결과는 bool이고
bool은 일반 산술 정수가 아니다. `!integer`는 bitwise NOT, `!bool`은 logical NOT이다.
렌더러는 이 차이와 Rust 우선순위를 따르며 C 식 문자열을 기계적으로 치환하지 않는다.
예를 들어 C의 정수 logical-not 후보는 Rust에서 정수와 0의 비교로 표현해야 한다.

일반 `+`, `-`, `*`의 overflow는 checked 빌드에서 panic을 일으킬 수 있다.
따라서 포함 영역 전체에서 overflow가 없는 후보만 허용하는 보수적 계약을 사용한다.
unsigned라는 이유로 C의 modulo wrap을 Rust 일반 산술에 적용하지 않는다.
분모 0, signed 최솟값/-1, 잘못된 shift count, cast와 음수 right shift도 Rust 규칙으로 판정한다.
signed right shift는 산술 shift이며 left shift는 밀려나간 상위 비트를 버린다.
정수 `as` cast는 대상 폭으로 자르거나 부호를 재해석한다.
명시적 wrapping/saturating 메서드는 일반 산술과 다른 연산이며 지원하지 않으면 보류한다.

Rust 후보는 원본과 후보의 source-language 타입을 확인하고 같은 finite domain의 모든 입력에서
Rust 의미로 다시 비교한다. 내부 후보 검색의 통과만으로 이 단계를 대신하지 않는다.
출력할 후보 문자열을 다시 파싱·타입 검사하므로 cast 뒤의 `<`·`<<` 같은 Rust 문법 차이도
검증한다. 보고서에는 해당 재평가의 예산과 생략 여부를 남긴다.

범위 전파는 단일 바인딩의 유한 값 집합을 직접 평가해 상관관계를 유지한다.
그 방식으로 입력 전체를 열거할 수 없어도 `(x & 1) + constant`처럼 중간값이 작아지는 연산은
피연산자의 유한 값 집합으로 전파한다. 여러 피연산자의 상관관계를 잃는 경우에는 가능한 값의
Cartesian product를 취해 보수적인 포함 영역을 만든다. 최대 4,096개 조합과 공통 작업 예산을
넘거나 연산을 확인할 수 없으면 전체 타입 범위로 넓힌다.

입력은 최대 8 MiB, token은 250,000개, 함수와 함수당 binding은 각각 4,096개다.
식은 최대 256 node와 parse depth 64로 제한한다. 입력당 원본 평가·공통 후보 검색·Rust 후보 재평가는
같은 `--max-nversion-work` 예산을 소비한다. 유한 흐름은 별도 `--max-finite-flow-work`를 사용한다.
한도에 도달한 분석은 `complete=false`와 실제 생략·보류 이유를 남긴다.

## 5. 정적 분석과 계측 지원을 구분한다

이번 C++·Rust 확장은 정적 분석이다. `--instrument`·`--profile`을 함께 요청하면 명시적으로 거절한다.
C의 `_Generic`·atomic 계측 헤더를 다른 언어에 주입하지 않는다.
라이브러리 API도 C++·Rust report를 C 프로파일 처리에 넣으면 거절한다.

C의 관측 알고리즘은 계속 제공한다. 반드시 실행되는 entry read의 표본에서 최소~최대 구간 전체를
비교하고, 그 밖의 제한된 반례를 찾는다. 관측이 정적 범위를 좁히지는 않는다.
C++·Rust 동적 지원을 추가하려면 각 언어의 읽기·타입·수명·로그 문맥 계약과
trace fingerprint를 구현하고 별도로 검증해야 한다.

## 6. 사용과 검토

```sh
nvcompact advise-source final.cpp --language cpp --standard c++17 \
  --clang clang --report /absolute/external/cpp-advice.json

nvcompact advise-source final.rs --language rust --standard rust2021 \
  --report /absolute/external/rust-advice.json

nvcompact advise-source final.py --language python
# explicit unsupported-language error; no frontend invocation
```

Clang 인자는 실제 입력의 전처리·include 문맥을 나타내야 한다.
Rust 제한 파서는 compiler flags·외부 crate·macro를 임의로 해석하지 않는다.
`complete`, 함수 보류 이유, 영역의 출처, 언어별 proof와 byte 추정 범위를 함께 읽어야 한다.
C/C++의 `complete=true`는 보고·탐색 예산상 생략이 없다는 뜻이며 명시적으로 보류한
함수와 함께 나타날 수 있다. Rust 부분집합 보고서는 함수·파일 보류도 `complete=false`로 표시한다.
어느 언어에서도 이 필드를 전체 프로그램 분석·동치 증명으로 읽지 않는다.
원문 길이 차이는 압축·native·최종 제출 파일의 절감량이 아니다.

공통 설계는 [도메인 n-version](DOMAIN-NVERSION.ko.md), C 단계와 refinement 측정은
[결과 기록](DOMAIN-PERFORMANCE-RESULTS.ko.md), 기존 상수·미사용·raw byte 유틸리티는
[자문 도구 안내](SHORTCODE-ADVISOR.ko.md)를 참고한다.
언어별 native 비교·수정한 결함·전체 TCEC 입력의 실제 보류 결과는
[언어 확장 검증 기록](LANGUAGE-RESULTS.ko.md)에 있다.

## 의미 기준

- [Rust Reference: operator expressions](https://doc.rust-lang.org/reference/expressions/operator-expr.html)
- [Rust primitive type names and shadowing](https://doc.rust-lang.org/std/primitive/index.html)
- [C++ working draft: logical OR](https://eel.is/c++draft/expr.log.or)
- [C++ working draft: shifts](https://eel.is/c++draft/expr.shift)

위 최신 draft의 모든 기능을 구현했다는 뜻은 아니다. 명시한 표준·부분집합과 보수적 제외 범위가
현재 도구의 실제 계약이다.
