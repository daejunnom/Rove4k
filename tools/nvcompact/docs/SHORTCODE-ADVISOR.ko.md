# NVCompact 숏코딩 제안 도구

이 기능은 후속 PR의 소스 빌드에서 제공한다. 게시된 npm 0.5.0에 이미 포함되어
있다는 의미가 아니며, 공개 패키지 배포는 별도 절차다.

## 1. 목적과 실행 경계

언어를 명시하는 `advise-source SOURCE --language c|cpp|rust`도 제공한다.
C++·Rust는 각 언어의 타입·연산 규칙을 검사하는 정적 scalar 부분집합이며,
Python 등은 고정 폭 영역 분석의 명시적 미지원으로 처리한다.
지원 문법·정적 계측 구분·보고서 경계는 [언어별 자문 계약](LANGUAGE-ADVISOR.ko.md)에 있다.
이 문서의 `advise-c` 계측·관측 설명은 C 전용이다.

`advise-c`는 최종 생성 C 또는 명시적으로 추출한 C payload를 읽어 중복 상수,
참조가 없는 선언, 실제 사용 위치의 정수 값 범위와 축약 후보를 보고한다.
`inspect-binary`는 완성된 제출 파일에서 반복되는 4·8바이트 구간을 찾는다.
두 명령은 `envelope`, `build`, `run`, source-search의 후보 생성·채택 경로와
연결되지 않는다. 보고서를 읽는 것만으로 압축 결과나 원본이 바뀌지 않는다.

선택형 `--instrument`는 별도 진단용 C 사본과 계측 헤더만 생성한다. 컴파일이나
대상 실행을 자동으로 시작하지 않는다. `--profile`은 사용자가 수집한 표본을
정적 분석 보고서에 추가하며 정적 범위를 좁히거나 source rewrite를 만들지 않는다.

| 접점 | 입력 | 출력의 의미 | 하지 않는 판단 |
|---|---|---|---|
| `advise-c` | C source와 Clang 문맥 | 타입·binding 기반 관측 및 지원 흐름의 사용 지점 범위 | 프로그램 전체 동치·압축 채택 |
| `advise-c --instrument` | 같은 source·분석 결과 | 독립 계측 사본·헤더·위치 목록 | 원본 수정·빌드·실행 |
| `advise-c --profile` | 같은 source·문맥과 stderr trace | 유한 표본의 최소·최대·횟수와 조건부 제안 | 모든 실행의 값 범위 증명 |
| `inspect-binary` | 최종 파일 bytes | 정확히 같은 raw byte window의 위치 | 상수의 의미·명령어 경계·안전한 제거 |

지원 C 표준은 기존 frontend와 같은 C11/C17/GNU11/GNU17이다. 값 범위는
frontend가 확인한 LP64·2의 보수 정수 모델에서 `_Bool`, `int`, `unsigned int`, `long`,
`unsigned long`, `long long`, `unsigned long long`을 다룬다. Plain char의
부호, short·enum·bitfield 폭, 128비트 정수, 실수, 배열·포인터 대상의 범위와
함수 간 관계를 추정하지 않는다. 이런 경우에도 직접 literal·참조 진단은
별도로 가능할 수 있다.

보고서의 `complete`는 finding·range·expression 출력 예산, 유한 흐름 분석 예산과
후보 비교 예산 때문에 항목이나 탐색을 생략했는지를 뜻한다. true여도 지원하지 않는 함수가 보류될 수 있으며 전체 C 의미·프로그램을
빠짐없이 분석했다는 뜻은 아니다. 해당 범위는 statistics와 limitations를 함께 읽는다.
도메인·n-version 확장 보고서는 `format_version: 2`다. 기존 trace의 필드 형식은 유지하지만
분석 알고리즘과 흐름 예산이 context 지문에 들어가므로 이전 분석 trace를 새 증명으로 재사용하지 않는다.

## 2. 책임과 상태 소유

`c_frontend`는 Clang 실행, 제한된 출력, 실제 executable identity, include
문맥과 preprocessing observation을 소유한다. 기존 변환기의 실행 경로를
복제하지 않는다. `advisor`는 한 번 얻은 AST를 자식 index를 가진 평탄한
구조로 옮겨 binding·위치·타입을 함께 사용한다. 각 AST subtree를 모든 조상에
복사하지 않는다.

`advisor::flow`는 함수마다 지역 환경을 소유한다. 키는 변수 이름이 아니라
Clang declaration ID다. 따라서 같은 이름을 가진 내부 블록 변수와 바깥 변수를
혼동하지 않는다. 환경의 값은 `advisor::domain`이 소유한 구간·known bits·유한 집합과
그 사실이 생긴 근거다. 분기 사본은 유한 집합을 공유하며 변경할 때만 복사한다. 범위는 선언 전체의
속성이 아니라 읽기가 실행되는 위치의 사실이다.

`advisor::expressions`는 Clang AST를 하나의 타입 있는 순수 식으로 낮추고 식 진입 지점의
도메인과 읽기 위치를 묶는다. `advisor::nversion`은 그 명시된 유한 도메인에서 후보들을
비교한다. 정적 분석과 동적 표본 해석이 서로 다른 산술 의미 구현을 만들지 않는다.

`advice_profile`은 진단용 사본 생성과 trace 해석만 소유한다. `artifact_advice`는
raw bytes의 중복 inventory만 소유한다. 이 모듈들은 `Variant`, 비용 목적함수,
압축 cache 또는 verifier의 합격 상태를 생산하지 않는다.

## 3. 중복 상수와 미사용 선언

### 타입이 같은 상수

Clang이 해석한 정수 값과 타입이 같은 직접 literal을 묶는다. 예를 들어
`0x5555555555555555ULL`과 `6148914691236517205ULL`은 같은 그룹이 될 수 있다.
LP64의 `0xffffffff`와 `4294967295`는 값만 같다는 이유로 같은 치환 그룹에
넣지 않는다. 너무 짧은 literal은 magic-number 진단에서 제외한다.

각 그룹은 원문 위치와 다른 occurrence의 위치를 보여 주며, 기존 named const
후보가 있으면 함께 안내한다. 공유 macro·typed alias를 선택할 때는 가시 범위,
이름 충돌, 정수 상수식 요구, 정확한 타입과 전처리 관측을 별도로 확인해야 한다.
C의 `const` 객체가 모든 정수 상수식 문맥을 대체하지는 않으며 큰 정수를 enum으로
옮길 수 있다고 가정하지 않는다. 반복 문자열은 이미 잘 압축될 수 있으므로
그룹 발견 횟수를 최종 절감 바이트로 계산하지 않는다.

### 참조가 없는 변수·함수

`no-reference`는 분석한 translation unit에서의 AST 참조 부재다. 함수 주소가
함수 포인터에 들어가면 사용으로 센다. `used`, `retain`, constructor와 같은
알려진 보존·진입 속성도 고려한다. 외부 linkage 선언에는 다른 translation unit,
linker·assembly·동적 호출이 남아 있을 수 있음을 명시한다.

`int unused = side_effect();`는 변수 읽기가 없더라도 initializer를 지울 수 있는
증거가 아니다. 진단에는 initializer·수명·ABI를 확인할 요구를 붙이며 삭제 patch를
생성하지 않는다.

`write-only-local`은 지원하는 자동 정수 지역변수의 모든 참조가 단순 `=` 대입의
좌변인 좁은 경우를 별도로 알린다. 복합 대입·증감·주소 취하기·읽기가 있으면 이
진단을 내리지 않는다. 저장된 값을 나중에 읽지 않아도 우변의 부작용과 평가 순서,
대입식 자체의 값은 남아 있다. 예를 들어 `return x=5;`에서 x 저장을 없애더라도
반환값 5는 보존해야 한다. 모든 dead store, 별칭을 통한 사용, 전체 call graph
reachability를 해결한 것으로 보고하지 않는다.

## 4. 실제 연산 위치의 값 범위

### 범위 계산

매개변수는 확인한 선언 타입 전체 범위로 시작한다. 지역변수의 지원 initializer,
대입·증감·복합 대입을 읽으며 상태를 갱신한다. Clang의 implicit cast를 따라서
정수 승격·signedness 변환을 반영한다. 구간 연산이 안전하게 표현되지 않으면
타입 전체 범위로 넓힌다. 계산 중 checked arithmetic을 사용하며 분석기 자신의
오버플로로 좁은 사실을 만들지 않는다.

분기에서는 조건을 true/false로 나누어 가능한 범위를 줄인다. 합류에서는 살아
있는 양쪽 범위를 합친다. 먼저 return한 경로는 다음 문장에 합류하지 않는다.
`&&`, `||`, 조건 연산자는 실제 도달 가능한 피연산자 문맥을 구분한다.
구간 안의 모든 값이 실제로 가능한 것은 아니므로, bounded typed filtering으로 남은
유한 집합과 알려진 0·1 비트를 함께 보존한다. 합류 시 가능한 값은 합집합,
확정 비트는 공통 부분이다. `if/else` 대입과 순수 삼항식 결과도 같은 집합 합류를 사용한다.
음수가 아닌 mask의 zero/equality 조건은 해당 비트를 제한하지만, 여러 비트의 nonzero
검사를 모든 비트가 1이라는 조건으로 바꾸지 않는다.

예를 들어 `int flag=x&1; if(flag==1)...`에서는 첫 조건의 flag가 0..1이다.
이후 `flag=2`가 실행되면 그 위치의 범위는 달라진다. 이전 조건에서 얻은
0..1을 변수의 남은 수명 전체에 붙이지 않는다. `if(x<0||x>1)return;` 뒤의
지원된 int 읽기는 0..1이라는 경로 조건을 사용할 수 있다.

### 보수적으로 범위를 버리는 경우

반복문의 진입·종료와 continue가 합류하는 increment/조건에서는 필요한 상태를
타입 범위로 넓힌다. 반복 횟수를 임의로 가정하거나 한 번의 body 실행을
고정점으로 간주하지 않는다. 이는 범용 CFG solver의 완전한 고정점 분석을
구현했다는 주장이 아니다.

주소를 취한 변수, static·extern·volatile·atomic 객체는 좁은 지역 추적에서
제외한다. 알 수 없는 호출·지원하지 않는 연산은 사실을 무효화하거나 넓힌다.
goto·label, assembly, 비지역 점프, GNU statement expression 등의 흐름은
함수 단위 범위 분석을 보류하며 이유를 limitations에 적는다. VLA의 sizeof,
배열·typedef 선언과 타입 cast에 숨은 길이 식은 실행 중 부작용이 있을 수 있어
일반적인 unevaluated read와 혼동하지 않는다.

### 축약 제안

지원 범위에서 다음 종류를 찾는다. 실제 적용 가능성은 보고서의 원문·위치·근거·
요구사항에 따른다.

- Boolean 범위의 `x == 1`, `x != 1`, `x == 0`, `x != 0` 등 비교.
- 구간상 항상 true/false인 비교.
- 오른쪽의 연속 하위 bit mask `2^k-1`에 이미 들어가는 비음수 값의 중복 `&`.
- 양의 상수 d에 대해 `0 <= x < d`일 때 타입 조건을 지키는 `x % d`와 `x / d`.
- 조건이 0..1이며 타입·조건 문맥이 맞는 `c ? 1 : 0`.

조건 결과가 같은 것과 C 타입까지 같은 것을 구분한다. 예를 들어 unsigned
0..1 값은 if 조건에서 비교를 대신할 수 있지만, 일반 값 문맥에서 `int` 비교
결과를 unsigned 식으로 바꾸면 타입이 달라진다. 부작용 없는 지원 표현만 제안하며,
바깥 괄호·우선순위·token 관측은 수동 변경의 검토 조건으로 남긴다.

`estimated_source_bytes_saved`는 해당 spelling의 원문 길이 차이만 의미한다.
공유 상수처럼 선언 비용과 영향 문맥을 계산하지 않은 제안은 null이다.
전체 압축 파일의 이득은 실제 빌드·포장 후 별도로 비교해야 한다.

### 도메인 전체의 n-version 비교

지원하는 단일 지역변수의 순수 식에는 비교·shift·mask·산술·Boolean·조건식을
조합한 유한 후보 문법을 적용한다. C 정수 승격, signed/unsigned 및 long/long long의
서로 다른 rank, 단락 평가와 정의되지 않은 연산을 검사한다. 이름이나 특정 체스
보드 표현에 따른 예외를 두지 않는다.

예를 들어 `(to>>4)==0||(to>>4)==7`는 `0 <= to <= 127`이 성립하는 사용 지점에서
`!(to+16&96)` 등과 전체 128개 값을 비교할 수 있다. `!(to&0x88)`만으로 그 범위를
정했다고 가정하지 않는다. 256이 mask 검사를 통과하고 두 식의 결과는 달라진다.
소스 밖에서만 보장되는 move-generator 전제는 현재 함수 분석의 사실로 자동 수입하지 않는다.

같은 타입의 전체 결과 벡터를 가진 중간 식은 해당 domain에 한정하여 재사용한다.
hash 충돌은 전체 벡터로 재확인하며 일부 값만 평가한 식은 동치로 합치지 않는다.
짧은 winner 하나만 보관하지 않고 알고리즘 계열별 대안도 남긴다. 더 긴 원문이 다른
압축 문맥에서 유리할 수 있으므로 최종 파일 비용은 별도 측정 대상이다.

기본 한도는 식 64곳, 도메인 4,096값, 식당 후보 10,000개·평가 단계 2,000,000회,
정적 비교 전체 16,000,000회다. 유한 흐름 전파에는 별도의 보수적 node-work 예산
8,000,000을 적용한다. `--max-nversion-targets`, `--max-nversion-work`,
`--max-finite-flow-work`로 조절하며, 한도에 도달하면 부분 결과와 이유를 표시한다.
읽기 보고서의 집합 목록은 256값까지 출력하며 더 큰 집합은 cardinality·생략량을 기록한다.
자세한 전제·후보 문법·캐시 소유·동적 알고리즘은 [도메인 n-version 설계](DOMAIN-NVERSION.ko.md)에 있다.

## 5. 선택형 실행 표본

### 안정적인 분석 문맥

trace는 source SHA-256, 분석 문맥 SHA-256, `range:start:end` 위치 ID와 정수
값을 기록한다. 문맥에는 compiler identity·표준·인자·include 위치와 preprocessing
내용이 포함된다. 원본 source hash만 같은데 header나 macro가 바뀐 경우를
같은 분석으로 받아들이지 않는다.

기존 source-search의 같은 세션 내 preprocessing 비교는 원래의 정확한 hash를
유지한다. 재실행되는 advisor용 fingerprint만 소유한 임시 translation unit의
전처리 line-marker 경로를 정규화한다. 실제 header 경로·내용을 지우거나 다른
텍스트까지 일반 경로 치환하지 않는다. `__FILE__` 같은 위치 관측이 문맥을
변화시키면 그 불일치를 조용히 무시하지 않는다. `__FILE__`, `__BASE_FILE__`,
날짜·시간 macro의 실제 문자열 확장은 그대로 남기므로, 이런 관측이 있는 입력의
재분석은 문맥 불일치로 거절될 수 있다. 이는 로그가 손상되었다는 단정이 아니라
같은 분석 문맥을 입증하지 못했다는 의미다.

### 계측 사본

`--instrument`는 source의 직접 식별자와 정확히 일치하는 일반 지역 정수 읽기만
감싼다. 대입 좌변·주소·macro expansion·volatile·atomic·일반 sizeof의 비실행
피연산자는 probe가 아니다. 값을 한 번 평가하고 원래 builtin 정수 타입으로
되돌린다. signed/unsigned 64비트 출력은 각각 정수 서식으로 기록한다.

진단 헤더는 C11 atomic counter로 생성된 translation unit의 전체 스레드 표본 수를 제한하며 stderr에
한 레코드씩 출력한다. 표준 stdio의 동시 호출 직렬화와 atomic quota를 사용한다.
errno는 logging 전후로 보존한다. 기본은 최대 128개 위치·100,000개 표본이며,
위치는 4,096개·표본은 1,000,000개를 넘길 수 없다.
같은 헤더를 독립적인 translation unit 여러 개에 복제한 구성의 전역 quota는
제공하지 않는다.

계측은 I/O·타이밍·스택·include 및 source location 관측을 바꾼다. 따라서 이
사본의 실행은 shipping 동치·성능 검사로 사용하지 않는다. 분석한 compiler
인자와 원본의 quote-include 디렉터리를 유지해 진단 빌드를 명시적으로 실행한다.
명령이 출력하는 manifest에는 소유 파일 hash와 실제 선택·생략한 위치를 기록한다.

probe는 일반 스레드 실행을 위한 것으로 async-signal-safe하지 않다. signal·
interrupt handler에서 실행될 수 있는 코드에는 사용하지 않는다. translation unit의
간접 등록만으로 모든 handler 문맥을 알아낼 수 있다고 가정하지 않는다.

### trace 수용

수집한 stderr를 `--profile`로 넣으면 source·문맥·위치·타입 범위를 확인한다.
잘못된 ID, 다른 소스·header 문맥, 정수가 아닌 값이나 타입을 벗어난 값을
성공한 관측으로 바꾸지 않는다. 64비트 정수는 JSON에서도 십진 문자열로
유지해 JavaScript number의 정밀도 손실을 피한다.
인식한 마지막 레코드가 newline 없이 끝나면 잘린 숫자를 정상 표본으로 읽지
않도록 trace를 거절한다. 그 앞의 성공처럼 보이는 레코드로 오류를 숨기지 않는다.

각 위치의 표본 수·최소·최대와 실제 연산을 보고한다. 0/1만 관측됐으면 Boolean
축약의 조사 후보를 제시하되 `observed-samples-only`로 표시한다. 관측값이 정적
구간 밖이면 모순을 명시하여 입력·문맥·계측 빌드·분석 전제를 확인하게 한다.
이를 정적 범위의 자동 수정이나 rewrite 근거로 사용하지 않는다.

단일 변수 식에는 식 진입 시 반드시 실행되는 읽기를 선택한다. `&&`·`||`의
오른쪽에서만 모은 표본은 전체 식의 입력 분포를 대신하지 않는다. 그 읽기의
관측 최소~최대 사이 **모든 정수**를 조건부 domain으로 만들어 같은 n-version
비교기를 실행한다. 관측한 몇 개의 값이나 확정되어 보이는 비트만으로 domain을
좁히지 않는다. 식마다 원래 정적 domain, 관측 가설, 전체 가설 domain의 비교 결과를
함께 표시하며 정적 finding을 덮어쓰지 않는다.

관측 단계의 기본 비교 예산은 별도로 16,000,000회다. 따라서 `--profile` 한 번은
정적 단계 16,000,000회와 관측 단계 16,000,000회를 각각 사용할 수 있다. 범위 밖
진단은 식당 최대 8개 후보 × 32개 값으로 별도 제한하며, 합성 평가 단계 수에
포함되었다고 표시하지 않는다. 밖의 반례는 적용 전제를 보여 주지만, 반례를 찾지
못했다는 사실은 모든 값에 대한 동치 증명이 아니다.

정적 interval·known bits·출력한 유한 집합과 모순되는 표본은 해당 동적 제안을 보류한다.
읽기 보고서에서 256값을 넘어 집합 목록을 생략했다면 profile 재구성은 interval과
known bits만 검사할 수 있다. 이때 생략된 구멍의 위반까지 검사했다고 주장하지 않으며
`static_membership_scope`에 더 넓게 재구성한 검사 범위를 표시한다.

종료·중단·표본 상한·테스트 선택 때문에 관측되지 않은 경로가 있을 수 있으므로
`coverage_complete`는 false다. 관측 부재는 unreachable의 증거가 아니다.

## 6. 최종 파일의 반복 바이트

`inspect-binary`는 매 바이트 offset에서 선택한 폭의 window를 읽어 정렬한다.
정렬된 구간별 반복 횟수, 겹침을 포함한 offset, 겹치지 않는 occurrence 수,
little/big-endian 숫자 표기와 raw hex를 보고한다. 0·0xff padding 가능성이
큰 그룹은 표시하고 후순위로 둔다. 0x55 mask처럼 의미 있을 수 있는 반복은
단순 uniform bytes라는 이유로 제외하지 않는다.

입력은 최대 4 MiB이며 정렬 index는 window당 최대 16바이트다. 모든 중복 그룹의
객체를 누적하지 않고 bounded heap으로 상위 결과를 보존한다. 기본 결과는
128개 그룹·그룹당 64개 offset이며 생략한 그룹 수와 offset 절단 여부를 명시한다.

동일 bytes는 linker relocation, 명령어 일부, 데이터, header 또는 압축 스트림일
수 있다. 따라서 semantic constant와 실제 예상 절감은 null이다. C 상수 의미가
필요하면 최종 생성 C 또는 선언된 payload를 `advise-c`로 분석하고 두 결과를
사람이 연결한다. 이 도구는 파일을 decode·load·execute하지 않는다.

## 7. 사용 예

아래 경로는 사용자가 소유한 새 출력 디렉터리로 바꾼다. `NVCOMPACT_CLANG`는
테스트용 환경 변수이며 CLI는 `--clang`으로 분석기를 명시한다.

```sh
nvcompact advise-c final.c --clang clang --report advice.json
nvcompact advise-c final.c --clang clang --instrument diagnostic
clang -std=c11 -iquote /absolute/original/source-directory diagnostic/instrumented.c -o diagnostic/probe
diagnostic/probe 2> observations.log
nvcompact advise-c final.c --clang clang --profile observations.log --report observed-advice.json
nvcompact inspect-binary submission --word-bytes 8 --report repeated-bytes.json
```

`--report`는 기존 파일을 덮어쓰지 않는다. `--instrument`도 새 디렉터리를
요구한다. 보고서가 없는 경우 stdout에 JSON을 출력한다. npm 진입점은 같은
Rust 명령에 인자를 전달하므로 별도 분석 backend가 없다.

## 8. 검증 원칙과 참고

검사는 결과 문구나 파일 수 대신 실제 의미 경계를 확인한다. 타입별 상수 그룹,
함수 포인터 참조, 부작용 initializer, 변수 shadowing, 대입 이후 범위, 분기·
early return, 음수 나머지·unsigned wrap, 반복문·주소 escape·volatile·macro,
VLA sizeof, 정적/동적 보장 구분과 잘못된 trace의 거절이 대상이다.

실제 계측 사본을 컴파일·실행해 원본의 계산 결과와 비교하고, 다중 스레드에서
표본 quota와 레코드 무결성을 확인한다. 이 작은 자체 예제의 결과를 엔진 전체
동치나 다코어 기력 인수로 확장하지 않는다. 성능 변경의 비교와 실행 근거는
별도 결과 문서에서 실제 범위를 보고한다.

- [C11 위원회 초안 N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf): 정수 승격·변환, 표현식, shift·sizeof와 부작용.
- [Clang Data Flow Analysis](https://clang.llvm.org/docs/DataFlowAnalysisIntro.html): 경로별 사실, 합류와 고정점의 기본 원리.
- [Clang diagnostics](https://clang.llvm.org/docs/DiagnosticsReference.html): unused와 unused-but-set 등 진단의 범위.
