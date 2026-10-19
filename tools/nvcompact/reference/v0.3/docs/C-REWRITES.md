# C 구조 압축과 최종 파일 비교

`nvcompact rewrite-c`는 C의 타입과 식의 문맥을 Clang AST로 확인하고, 적용 조건을 만족하는 짧은 표현 후보를 만든다. Python 코어를 유지하며 Clang은 이 명령에만 필요한 선택적 개발 도구다. 일반 `build`, `resource plan`, 이미 만들어진 recipe의 재현에 Clang AST 분석을 강제하지 않는다.

기본값은 `--token-contract opaque`다. 이 상태에서는 Clang을 실행하지 않고 원문 `raw`만 보존한다. 실제 구조 변환에는 `--token-contract no-token-observation` 또는 `preprocessed`를 명시한다. 이는 프로그램이 소스·토큰·위치 표기 변화를 관측하지 않는다는 입력 계약이며, 옵션을 썼다는 사실이 그 계약을 증명하지는 않는다. `preprocessed`도 원문을 자동 전처리하는 명령은 아니다.

## 사용 경로

Linux, CPython 3.11 이상, Node.js 22 이상과 C11/C17 AST JSON을 제공하는 Clang을 사용한다. CLI를 설치한 뒤의 명령은 다음과 같다. 모노레포 안에서는 `nvcompact` 대신 `node packages/nvcompact/bin/nvcompact.mjs`를 쓸 수 있다.

```sh
nvcompact rewrite-c program.c \
  --clang clang --standard c11 \
  --token-contract no-token-observation \
  --portfolio out/c-portfolio
```

이 단계는 컴파일러의 전처리·구문 분석만 수행한다. 대상 프로그램을 링크하거나 실행하지 않는다. 포트폴리오 디렉터리는 새 경로여야 하며 원본 C, 결합 후보, 규칙별 후보, 적용 위치와 근거를 담은 `audit.json`을 만든다. 같은 바이트가 나온 규칙도 recipe의 출처를 남긴다.

한 후보만 내보낼 수도 있다. 암시적 기본 후보는 생성되었으면 `c-all`, 그렇지 않으면 `raw`다. 명시적으로 요청한 `--variant`가 없으면 오류로 처리한다.

```sh
nvcompact rewrite-c program.c --output out/unchanged.c
nvcompact rewrite-c program.c --clang clang \
  --token-contract no-token-observation \
  --variant c-all --output out/program.c --audit out/program-audit.json
```

첫 번째 명령은 기본 opaque 계약에 따라 원문을 그대로 내보낸다. 원본을 덮어쓰지 않으며 출력 파일이 이미 있어도 덮어쓰지 않는다.

### 링크·압축·검증까지 연결하기

다음 예제는 패키지에 포함된 작은 프로그램을 대상으로 한다. 정해진 16행의 정수 결과, 종료 코드, stderr를 독립 Python 수식으로 검사한다. 고메모리 엔진을 실행하지 않는다.

```sh
nvcompact rewrite-c packages/nvcompact/examples/c-rewrites/program.c \
  --clang clang --standard c11 \
  --token-contract no-token-observation \
  --portfolio out/c-portfolio \
  --run-manifest \
  --verifier packages/nvcompact/examples/c-rewrites/verify.py \
  --run-target x86_64-unknown-linux-gnu \
  --run-contract '16 independently computed integer rows, zero exit, empty stderr; no self-file/path observation' \
  --codec gzip-9 --codec xz-6

nvcompact run out/c-portfolio/manifest.json \
  --out out/c-run --jobs 2 --max-candidates 64

nvcompact reproduce out/c-run/winner.recipe.json --out out/c-reproduced
```

`--run-manifest`는 실행 계획 파일만 만든다. 다음의 `run`이 원본 baseline과 각 실제 바이너리를 명시된 verifier로 실행하고, 링크 결과·압축 payload·loader를 합친 전체 파일을 비교한다. 채택 결과는 새 빌드에서 바이트와 verifier를 다시 확인한다. 압축 recipe의 `reproduce` 역시 verifier를 수행한다. 실행 경계가 다른 일반 링크 빌드는 [NATIVE-BUILD.md](NATIVE-BUILD.md)를 참고한다.

생성 manifest는 원문 `raw`를 baseline으로 유지하며 모든 C 후보를 같은 component의 실제 소스 variant로 연결한다. 생성 당시 Clang executable, C standard와 ABI/frontend 인자를 compile/link 명령에 전달한다. 단일 translation unit과 시스템 `<...>` include만 자동 포장하며 로컬 header·외부 sysroot·보조 object는 캡처한다고 가장하지 않는다. 그런 프로젝트는 입력을 스냅샷하는 일반 NVCompact manifest에 각 생성 C 파일을 variant로 등록한다. `--run-target`은 실제 toolchain/ABI와 일치시켜야 한다.

verifier는 후보 실행 파일의 절대 경로 한 개를 인자로 받아 성공 시 0으로 종료하는 독립 Python 파일이다. helper 파일에 의존하는 checker는 명시적인 프로젝트 manifest로 함께 캡처한다. 생성 도구가 실행 도메인이나 체스 탐색 의미를 추측해 채우지 않는다.

## 현재 자동 변환

기본 포트폴리오는 `raw`, `c-all`, 아래 13개 규칙별 후보로 구성된다. 각 pass에서 겹치지 않는 짧은 변환을 선택하고, 같은 frontend로 다시 파싱한 뒤 다음 pass를 수행한다. 기본은 2 pass이며 `--max-passes 1..8`, `--max-variants 1..32`로 작업량을 제한한다. 아래 예시는 규칙을 설명하는 형태이며 실제 적용은 타입·원문 위치·부모 문맥·전처리 보호 조건을 모두 확인한다.

| 규칙 | 비교하는 형태 | 주요 적용 조건 |
|---|---|---|
| `if-return` | `if(c)return a;else return b;` → `return c?a:b;` | return 문맥 변환 **이전** 두 값의 타입이 같은 지원 scalar 타입 |
| `return-tail` | `if(c)return a;return b;` → `return c?a:b;` | 같은 block의 연속 문장, 같은 타입 조건 |
| `if-assignment` | `if(c)x=a;else x=b;` → `x=c?a:b;` | 같은 평범한 변수, RHS 원래 타입 일치, volatile/atomic 제외 |
| `if-effect` | `if(c)f();else g();` → `c?f():g();` | 버리는 표현 결과가 동일 지원 타입 또는 둘 다 void; 선택된 쪽만 평가 |
| `guard` | `if(c)f();` → `c&&f();` | 결과가 정수/포인터인 식 문장; 조건과 효과를 각각 한 번 평가 |
| `boolean` | `c?1:0` → `!!c`, `c?0:1` → `!c` | 정확한 int 0/1 결과; 기존 비교식의 중복 0/1 정규화도 축약 |
| `zero-test` | `x==0` → `!x`, `x!=0` → `!!x` | C scalar의 0 비교, 결과 타입과 평가 횟수 보존 |
| `truth` | 조건 위치의 `!!x`, `x!=0` → `x` | 실제로 값이 아닌 참/거짓만 소비되는 조건·short-circuit 위치 |
| `negation` | `!(a==b)` → `a!=b`; `!(a&&b)` → `!a||!b` | 비교 반전과 De Morgan의 평가 순서 보존; 순서 비교 반전은 부동소수점 제외 |
| `compound` | `x=x+y` → `x+=y` 등 | 같은 단순 변수, 지원 산술/비트 연산, RHS에 호출·대입·증감 없음 |
| `increment` | `x+=1` → `++x`, `x-=1` → `--x` | 정확한 원문 int literal 1, 단순 정수/포인터 변수, 새 값 결과 유지 |
| `leaf-braces` | `if(c){x++;}` → `if(c)x++;` | 선언·label·중첩 if·복합 literal 수명이 없는 한 개의 leaf 문장 |
| `forever` | `while(1)` → `for(;;)` | 0이 아닌 정수 literal 조건; `for` 매크로 충돌 없음 |

규칙은 실제 소스 바이트가 줄 때만 후보 편집을 추가한다. 이는 **소스 길이의 국소 판단**이다. `c-all`은 전역 최적해가 아니며 규칙별 단독 후보와 원문도 최종 링크·압축 경쟁에 남긴다. 구조 변경이 더 나은 명령어 배치나 코드 생성을 만들 수도 있고, 이미 컴파일러가 같은 형태로 정규화하면 최종 바이트가 그대로일 수도 있다.

기존 `notation`은 literal·공백·주석 등 표현 후보를 다룬다. 구조 변환은 object가 달라질 수 있으므로, 기존의 object 동일성을 요구하는 조기 표기 확정 경로에 억지로 넣지 않는다. 실제 source variant를 빌드하고 응용 계약을 검증하는 경로를 사용한다.

## 무조건 짧게 만들면 달라지는 의미

다음 C 코드는 LP64 환경에서 직접 컴파일해 서로 다른 결과가 나오는 반례다.

```c
unsigned long original(int c) {
    if (c) return -1;
    else return 1U;
}
unsigned long incorrect(int c) {
    return c ? -1 : 1U;
}
```

`original(1)`은 18446744073709551615, `incorrect(1)`은 4294967295였다. 원래는 각각 unsigned long으로 return 변환하지만, 합친 식에는 signed/unsigned 피연산자 사이의 조건 연산자 타입 결정이 먼저 개입한다. AST의 이미 변환된 return 자식 타입만 비교하면 이 문제를 놓친다. 구현은 원문 값 타입을 확인하며 이 병합을 하지 않는다.

같은 이유로 `x+=1U`를 일괄 `++x`로 줄이지 않는다. NaN에 대해서는 `!(x<0)`과 `x>=0`도 같지 않다. 실제 회귀 입력에서는 전자가 1, 후자가 0이었다. `&&`를 `&`로 바꾸거나 두 분기를 미리 모두 계산하는 branchless 표현 역시 평가 순서·부작용·유효하지 않은 주소 접근을 바꿀 수 있으므로 이 기능의 일반 변환이 아니다.

### 전처리와 토큰 경계는 별도 보호한다

Clang의 AST에는 전처리에서 사라진 동작이 남지 않을 수 있다. 실제 검토에서 다음 두 종류의 실패를 발견하고 일반 적용 조건을 수정했다.

- `else{\u03b1=3;}`를 단순 연결하면 `else\u03b1=3;`라는 별도 변수 대입이 될 수 있었다. 구문 재검사도 통과했다. 현재 byte lexer가 확인할 수 없는 UCN·UTF-8 식별자·`$` 같은 확장 식별자 입력은 원문만 보존한다. 문자열과 주석의 Unicode·escape는 그대로 지원한다.
- block 안의 `_Pragma("pack(1)")` 또는 그것만 생성하고 사라지는 macro alias를 삭제하면 뒤쪽 struct 크기가 5에서 8로 달라졌다. 구현은 전처리 과정의 macro 정의 전체 집합을 수집하고, 함수 원문에 나타나는 macro 이름·pragma 연산자·directive를 보호한다. 뒤에서 `#undef`한 정의도 보수적으로 포함한다.

새 `for` 키워드의 macro 충돌, `else`와 `break` 등 인접 token의 합쳐짐도 검사한다. 소스 범위가 매크로·다른 파일을 가리키거나 알려진 AST 모양에 맞지 않으면 적용하지 않는다. 재파싱이 성공했다는 사실만으로 의미가 보존되었다고 판정하지 않는다.

## 보호 범위와 한계

현재 구현은 관련 함수에서 volatile/atomic 타입·접근, `_Generic`, `sizeof`/`_Alignof`, compound literal, statement expression, inline assembly, 지원하지 않는 expression kind, 수명에 영향을 줄 수 있는 aggregate 호출 결과를 보호한다. `setjmp`, 알려진 source/context 관측 builtin, `returns_twice` 선언을 사용한 함수도 보호한다. 간접 함수 호출은 대상의 이러한 속성을 AST로 확정할 수 없으므로 자동 변환하지 않는다.

일반 C의 전역 의미 동치를 증명하는 도구는 아니다. Clang JSON AST 형식은 자체적으로 장기 안정성을 보장하는 공개 interchange schema가 아니므로 실제 frontend 버전·실행 파일 hash·standard·인자를 audit에 남긴다. 다른 컴파일러나 ABI로 바꿀 때 같은 결과라고 추정하지 않고 해당 target에서 다시 생성·빌드·검증한다.

frontend 실행은 기본 parse당 30초, 주소 공간 1GiB, AST/전처리 출력 32MiB 한도로 제한하고 자식 process group을 정리한다. `--frontend-seconds`, `--frontend-memory-mib`, `--ast-mib`로 조정한다. 이는 compiler 작업의 자원 한도이며 임의 C나 plugin을 실행하는 보안 sandbox가 아니다. plugin·response file·임의 compiler action 옵션은 이 frontend 인자 계약에서 받지 않는다.

## 더 넓은 압축 후보에 대한 판단

| 후보 영역 | 현재 판단과 비교 방법 |
|---|---|
| 불필요한 괄호, return 공통 부분, 대입 방향 통합 | AST 부모의 우선순위·결합 방향·값 종류를 더 완전하게 증명한 뒤 추가할 수 있다. 이번에는 임의 괄호 삭제를 넣지 않았다. |
| 함수 인라인, 공통 식/분기 합치기, tail duplication | 빌드 프로필과 compiler 결과를 우선 비교한다. 호출 수·alias·예외적 제어 흐름에 영향을 주는 소스 이동은 별도 분석이 필요하다. |
| unsigned 나눗셈·나머지와 shift/mask, 작은 lookup table | 정확한 타입·값 범위·overflow·shift 폭 계약을 입증한 프로젝트 variant로 비교한다. 산술 항등식만으로 모든 signed 입력에 적용하지 않는다. |
| boolean multiplication, mask 선택, branchless min/max | 양쪽 평가와 메모리 접근, overflow·NaN을 바꿀 수 있다. 표준 규칙 목록에 무조건 넣지 않는다. |
| 선언 합치기, 초기화/테이블 재배열, 데이터 공통화 | linkage·alignment·lifetime·padding·relocation을 함께 비교한다. 기존 linker variant와 명시적인 component 계약을 활용할 수 있다. |
| 지역 이름 단축, 주석/공백, literal 표기 | 소스 관측과 타입 계약 아래 기존 표기 포트폴리오와 연결한다. 배포가 ELF면 소스 길이 감소가 최종 파일 감소를 보장하지 않는다. |
| C/Rust 동등 component 교체 | C ABI, 입력 도메인, overflow·alias 규칙과 호출 비용을 명시해 기존 mixed-language linker 포트폴리오로 비교한다. C의 `?:` 규칙을 Rust에 텍스트 치환하지 않는다. |

이 항목들은 영구적인 금지 규약이 아니다. 더 정확한 분석이나 특수화 계약이 생기면 구현을 교체하고 근거와 회귀 사례를 갱신한다. 재현 불일치를 입력별 제외 목록이나 기대 hash 자동 갱신으로 통과시키지 않는다.

## 검증 근거

Clang 20.1.8, C11, `-Os`와 동일 linker 설정으로 번들 예제를 실제 실행했다. 15개 source recipe에서 서로 다른 소스 10개가 나왔고, 링크 15회와 raw/gzip-9/xz-6 전체 파일 45개가 verifier를 통과했다.

| 후보 | C 소스 | 링크 ELF | gzip-9 전체 파일 | xz-6 전체 파일 |
|---|---:|---:|---:|---:|
| 원문 `raw` | 661 B | 14,480 B | 2,368 B | 2,197 B |
| 결합 `c-all` | 597 B | 14,480 B | 2,368 B | 2,197 B |
| `c-if-return` | 635 B | 14,480 B | 2,368 B | 2,197 B |
| `c-compound` | 649 B | 14,480 B | 2,368 B | 2,197 B |
| `c-leaf-braces` | 645 B | 14,480 B | 2,368 B | 2,197 B |

결합 후보는 C 소스를 64 B, 약 9.68% 줄였다. 그러나 **모든 링크 ELF가 바이트 단위로 동일**했고, 이 예제에서 구조 변환으로 추가로 줄어든 최종 파일은 없었다. 컴파일러가 이미 같은 코드를 생성했다는 관측에 맞춰 원문 후보가 안정적인 동점 순서로 선택됐다. 채택된 xz-6 파일은 payload 1,600 B와 loader 597 B를 합친 2,197 B였고, 새 빌드 검증과 별도의 `reproduce` 모두 같은 SHA-256 `7b17b8a3e98434b9a2b22138e5579464032803875a73fe983fbedac81a74c490`을 만들었다. 소스 길이만으로 최종 결과를 고르지 않는 이유를 실제로 확인한 사례다.

현재 회귀 검사는 GCC와 실제 Clang에서 정수 반환 타입, 부작용 추적, NaN, 포인터, 중첩 분기, 반복문, volatile/atomic, `_Generic`, `sizeof`, returns-twice·간접 호출, macro·pragma·토큰 경계와 원문 보존 경로를 확인한다. 이 작은 프로그램 검사는 체스 엔진의 모든 탐색 의미·Elo·고메모리 동작 검증을 대신하지 않는다. 실제 포트폴리오 측정과 재현 결과는 [c-rewrites-v03.json](../evidence/c-rewrites-v03.json)에 기록한다.

```sh
NVCOMPACT_CLANG=clang python3 -m unittest discover \
  -s packages/nvcompact/python/tests -p test_cflow.py -v
```

Clang이 없으면 선택적 semantic 검사는 skip된다. CI나 의미 검증을 인수하는 실행에서는 `NVCOMPACT_CLANG`에 실제 executable을 지정하고 skip 상태를 함께 확인한다.

## 참고한 일차 자료

- [WG14 N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf): 6.3 변환, 6.4 토큰, 6.5.13–16 논리·조건·대입, 6.8 문장, 6.10 전처리, 7.13 비지역 점프.
- [Clang AST 소개](https://clang.llvm.org/docs/IntroductionToTheClangAST.html): 문법과 타입·implicit cast를 함께 읽는 AST 구조.
- [Clang JSONNodeDumper](https://clang.llvm.org/doxygen/JSONNodeDumper_8h_source.html): 사용한 AST JSON 생성 구현과 버전별 형태 검토.
- [GCC 최적화 옵션](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html): compiler 최적화와 target-dependent 크기·코드 생성 비교의 근거.

참고 자료의 C 규칙에서 도출한 적용 조건과 이 저장소의 현재 구현·실험 결과는 구분해 읽는다. 모든 표 항목이 일반 C 전체에 대한 자동 증명을 제공하는 것은 아니다.
