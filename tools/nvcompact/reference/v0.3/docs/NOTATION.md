# NVNotation 0.2 — 표기 후보 생성과 적용 계약

모노레포에서 이 문서의 예제 소스 기준 디렉터리는 `packages/nvcompact/`다. 직접 Python 명령은 그 디렉터리의 `python/` 아래 진입점을 사용한다. 루트에서 실행하는 npm 명령은 [README](../README.md)에 있다.

NVNotation은 숫자·일부 연산자·Python 문자열의 표기를 자동으로 비교하는 NVCompact의 source 단계 도구다. 기존 파일은 `raw` 후보로 유지하고, 선언한 언어 모델에서 가능한 표기들을 제한된 수의 전체 파일 후보로 만든다. 후보는 기존 빌드·링크·완성 파일 압축·실행 검증 절차로 전달한다.

`100000`과 같은 값의 지수 표기는 `1e5`다. `1e6`은 `1000000`이다. 그러나 이 수학적 동등성만으로 프로그램에서 바꿔도 된다는 결론은 나오지 않는다. C/C++에서 `100000`은 정수 literal이고 `1e5`는 `double` literal이다. Rust에서도 정수 추론과 부동소수점 추론이 달라진다. Python도 `int`와 `float`를 구분한다. 따라서 NVNotation은 정수 literal을 지수 표기로 바꾸지 않는다. 이미 부동소수점인 `100000.0`은 해당 계약에서 `1e5`로 바꿀 수 있다.

## 빠른 사용

패키지 루트에서 실행한다. Python 표준 라이브러리만 필요하다.

```sh
python3 python/nvnotation.py engine.cpp \
  --language cpp --target cpp17-lp64 \
  --token-contract no-token-observation \
  --compact --variant shortest-compact \
  --output generated/engine.cpp \
  --audit generated/engine.notation.json
```

`--output`은 새 파일이어야 한다. 원본 입력을 덮어쓰지 않는다. `--audit`도 새 파일로 생성한다. source를 직접 읽는 프로그램, 원문을 문자열화하는 macro, 위치 정보가 관측되는 프로그램에는 해당 계약을 부여하지 않는다.

전체 후보와 audit를 받으려면 다음과 같이 실행한다.

```sh
python3 python/nvnotation.py engine.c \
  --language c --target c11-lp64 \
  --token-contract no-token-observation \
  --compact --portfolio generated/candidates
```

Python 엔진에도 같은 인터페이스를 사용한다.

```sh
python3 python/nvnotation.py engine.py \
  --language python --target python3 \
  --token-contract no-token-observation \
  --compact --portfolio generated/python-candidates
```

`--list-variants`는 파일 생성 없이 각 recipe의 크기·변환 근거를 JSON으로 출력한다. `--variant shortest`는 공백과 주석을 그대로 두고 표기만 바꾼다. `--variant shortest-compact`에는 `--compact`가 필요하다.

## 지원 모델

| 언어 | target | 실제 후보 범위 |
|---|---|---|
| C | `c11-lp64` | 10·8·16진수, 정수 suffix, decimal/hexadecimal floating literal |
| C | `c23-lp64` | 위 범위와 2진수·digit separator; bit-precise suffix는 유지 |
| C++ | `cpp17-lp64` | 10·8·16·2진수, digit separator, 정수 suffix, floating literal, alternative operator token |
| Rust | `rust2021` | 10·8·16·2진수, `_`, 명시적 정수/float suffix와 추론 종류 보존 |
| Python | `python3` | 표준 tokenizer/AST가 해석하는 정수·유한 float·일반 문자열·bytes 표기 |

`c++`는 `cpp`, `py`는 `python`의 별칭이다. C/C++의 `int`는 32비트, `long`과 `long long`은 각각 별개의 64비트 타입인 LP64 모델을 사용한다. Windows LLP64나 32비트 ILP32에 LP64 계약을 사용하면 안 된다. C/C++ binary32 `float`와 binary64 `double`을 대상으로 하며 `long double`, 확장 부동소수점 suffix, C++ user-defined literal은 변환하지 않는다.

Rust의 `0x01_f32`는 suffix가 `f32`인 부동소수점이 아니라 16진수 정수 `7986`이다. tokenizer와 literal parser가 이 경우를 구분한다. 정수 `100_000u32`의 `_`는 없앨 수 있지만 `u32`를 문맥 없이 제거하지 않는다. `100_000f32`는 float 표현이므로 `1e5f32` 후보를 만들 수 있다.

## 숫자 후보를 만드는 방법

### C/C++ 정수

입력 literal을 기수와 suffix로 분해하고, 표준의 타입 후보 순서에 따라 실제 타입을 결정한다. 같은 값으로 10·8·16진수와 언어가 허용하는 2진수를 생성한 뒤, suffix 조합을 다시 대입해 **값과 타입이 모두 같은 것만** 유지한다. `long`과 `long long`이 모두 64비트여도 같은 타입으로 취급하지 않는다.

예를 들어 LP64에서 decimal `2147483648`은 `long`인데 `0x80000000`은 `unsigned int`다. 따라서 이 둘을 교체하지 않는다. `0x80000000l`처럼 타입을 보존한 후보는 비교할 수 있다. 반대로 `4294967295u`는 `0xffffffff`로 바꿔도 이 모델에서 `unsigned int`를 유지한다.

부호는 literal의 일부로 흡수하지 않는다. `-1`은 unary minus와 정수 literal로 취급한다. `1<<n`, 곱셈식, cast, 보수식, 배열 접근 등으로 치환하는 expression 재작성은 이번 표기 도구의 범위에 포함하지 않는다. 그런 변환은 overflow·usual arithmetic conversion·constant expression 조건·평가 순서를 별도로 다뤄야 한다.

### 부동소수점

원문을 호스트의 `float`로 먼저 읽어 값이 같다고 판정하지 않는다. decimal과 hexadecimal significand/exponent에서 정확한 `Fraction`을 만들고, 같은 정확한 유리수를 나타내는 다음 표기를 비교한다.

- 불필요한 0과 소수부 자리를 줄인 decimal 표기.
- exponent의 `+`와 앞자리 0을 정리한 과학적 표기.
- significand의 소수점 위치를 달리한 유한 후보.
- C/C++에서 정확히 표현할 수 있는 hexadecimal floating 표기.

같은 literal 타입 또는 Rust의 같은 추론 종류를 유지한다. audit에는 정확한 유리수와 binary32/binary64의 round-to-nearest, ties-to-even 모델 bits를 남긴다. C/C++의 실제 변환 정책은 compiler 조건에 속하므로 해당 target으로 빌드한 결과를 비교해야 한다. C 표준이 모든 구현에서 decimal 변환을 하나의 방식으로 강제한다는 주장을 하지 않는다.

값을 한 번 binary64로 반올림한 뒤 그 근처의 다른 decimal을 출력하는 방식은 C/Rust 경로에 쓰지 않는다. Python 경로는 실행 중인 Python interpreter의 실제 `float` 값과 타입·bits, 최종 전체 AST를 대조한다.

## 숫자와 유사한 표기 압축

현재 자동 적용 범위는 다음과 같다.

| 처리 | 보존 조건 |
|---|---|
| 정수 앞자리 0·기수·suffix 정리 | 해당 언어의 값과 타입 유지; C octal 해석 반영 |
| float exponent·소수점 정리 | 정확한 값과 타입/추론 종류, target 변환 조건 유지 |
| C/C++ digraph | preprocessing directive 밖에서 동일 punctuator로 변환 |
| C++ `and`, `or`, `not`, `bitand` 등 | C++ alternative operator token에 한정 |
| Python 일반 문자열의 quote·escape 선택 | literal AST와 전체 AST 일치; source encoding으로 표현 가능 |
| 주석·공백 정리 | 명시적 비관측 계약; C 계열 전체 token sequence 또는 Python 전체 AST 일치 |

C에서 `and`가 변수 이름인지 `<iso646.h>` macro인지 추측해서 바꾸지 않는다. C/C++/Rust 문자열은 따옴표와 escape를 재작성하지 않는다. Python f-string, complex literal, bool, `None`도 재작성하지 않는다. 변수명·외부 심볼명·함수 signature를 바꾸는 기능은 없다.

## macro·문자열·전처리 보호

`--token-contract opaque`가 기본값이며, 이 상태에서는 `raw`만 반환한다. “언어의 literal 의미가 같다”는 사실이 “원문을 관측하는 macro에도 같다”는 뜻은 아니기 때문이다. `--token-contract no-token-observation`은 다음을 명시한다.

1. 변환한 source의 숫자·공백·주석 표기와 위치를 프로그램 동작으로 관측하지 않는다.
2. 외부 header나 compiler 옵션으로 주입된 macro가 변환 대상 표기를 stringify/paste하거나 예기치 않은 token tree로 재해석하지 않는다.
3. `inspect`, `__FILE__`, `__LINE__`, `line!`, `column!`, traceback·panic 위치, 자기 소스 읽기 등이 바뀐 위치·파일·표기를 결과 계약으로 요구하지 않는다.
4. 명시한 언어/target 모델과 실제 compile 옵션이 일치한다.

도구는 이 계약을 선언했다고 macro 내용을 공격적으로 바꾸지는 않는다. C/C++의 모든 preprocessing directive를 보존하고, 식별자 뒤 괄호는 외부 header에서 정의한 함수형 macro일 가능성이 있어 내부를 보존한다. Rust의 macro 호출·macro_rules 정의·attribute token tree와 tuple field 표기를 보존한다. quoted string, raw string, comment 내용은 숫자로 오인하지 않는다. Rust doc comment는 attribute 의미가 있으므로 주석 제거 대상으로 취급하지 않는다.

전처리 전 line-splicing/trigraph처럼 작은 lexer가 단계별로 해석하지 않는 입력은 identity와 사유를 남긴다. 이런 경우 정규식을 더 얹어 강제로 변환하지 않는다. 실제 compiler의 전처리를 거친 뒤 `preprocessed` 계약을 사용할 수 있다. 이 계약은 C/C++ 전용이며, 이미 macro 확장을 끝냈고 원문 위치·표기를 관측하지 않는다는 의미다. 도구가 전처리기 자체를 대신하지는 않는다.

원래 공백을 제거하거나 숫자를 줄여 `0xe+2`, `++`, `/*`, 새 directive, 다른 suffix가 생기는 문제도 검사한다. 원래 이웃 token과 바뀐 token을 다시 lex하고, compaction 이후에는 전체 token sequence를 대조한다. 맞지 않으면 해당 compaction을 적용하지 않고 audit에 이유를 남긴다. 유효하지 않은 입력을 고치는 도구가 아니므로 원본도 실제 compiler 또는 interpreter로 검사해야 한다.

## Python의 추가 근거와 한계

Python은 정규식 lexer 대신 `tokenize`를 사용한다. token 종류와 위치를 보존한 literal 교체를 한 뒤, `ast.dump(..., include_attributes=False)`로 전체 프로그램을 다시 비교한다. 이 비교에는 `int`와 `float`, 일반 문자열의 값, AST 구조가 포함된다. float는 binary64 bytes도 비교한다. 선택한 spelling이 source encoding에 들어가지 못하면 해당 spelling은 사용하지 않는다.

`--compact`는 원래 token 위치를 기준으로 일반 주석과 줄 중간의 가로 공백만 줄인다. token들을 `untokenize`로 재직렬화하지 않으므로, 이미 minify된 입력에 공백을 다시 넣어 source가 커지지 않는다. 먼저 숫자·문자열 표기를 선택한 뒤 공백 정리를 적용한다. 공백 정리 자체는 해당 표기 후보보다 source를 늘리지 않는다.

compactor는 shebang, encoding cookie, UTF-8 BOM, 원래 들여쓰기, LF/CRLF와 명시적 `\\` 줄 연결을 보존한다. 줄·열 위치는 Python tokenizer의 물리적 줄 기준으로 계산하므로 문자열 안이나 들여쓰기에 들어 있는 form-feed를 별도 줄로 오인하지 않는다. 인접 token들을 다시 tokenize해서 종류와 spelling이 그대로일 때 공백을 제거하며, 필요한 구분은 한 칸으로 줄인다. `1 .real`이 `1.real`이 되거나 인접한 `"" ""`가 잘못된 triple quote가 되는 변경은 허용하지 않는다. `1 if`처럼 tokenizer는 구분해도 parser가 경고하는 숫자·식별자 경계도 유지한다.

마지막으로 주석을 제외한 전체 token sequence, 들여쓰기 token, 실제 newline token, 전체 AST를 다시 비교한다. 이 검증에 실패하면 공백 정리만 보류하고 원래 표기 후보와 사유를 남긴다. 삭제한 주석 수, 줄인 가로 공백 구간 수, source byte 감소량도 audit에 기록한다. 문자열 표기 후보 자체는 같은 값의 escape 표현으로 바뀔 수 있지만, compactor는 선택된 문자열 token 내부를 건드리지 않는다.

모든 Python whitespace를 전역적으로 최소화하거나 indentation 최적화를 탐색하지는 않는다. AST가 같아도 코드 위치와 원문을 읽는 프로그램에서는 관측값이 달라질 수 있으므로 비관측 계약이 여전히 필요하다.

## 후보 수와 선택

`raw` 뒤에 `shortest`, `hex`, `decimal`, `scientific`, `octal`, `binary`를 생성한다. `--compact`를 켜면 각각의 compact 버전도 만들어 총 13개 recipe까지 비교한다. 기본 `--max-variants`는 16이고 실제 생성 상한은 현재 recipe 수다. `--max-variants`는 1부터 32까지 받으며 `raw`도 수에 포함한다. 앞부분은 `raw`, `shortest`, `shortest-compact` 순서라 작은 budget에도 핵심 후보가 남는다.

개별 숫자마다 모든 대안을 선택하는 Cartesian product는 만들지 않는다. 각 전체 파일 recipe가 기수·표기 계열을 선호하는 방식으로 동작한다. 같은 bytes를 만든 recipe도 ID와 provenance는 보존하며, 호출자가 hash/bytes로 중복 실행을 제거할 수 있다. 입력 파일은 최대 8 MiB, literal은 최대 512자이며 과도한 exponent와 미지원 literal은 원본으로 남긴다.

`shortest`는 바뀌는 token의 문자 수가 더 짧을 때만 선택한다. 다른 계열 recipe는 압축 dictionary·반복 패턴의 이득을 보기 위해 더 긴 표기도 만들 수 있다. `shortest-compact`라는 이름도 전체 압축 파일의 최적성을 뜻하지 않는다.

## 링크 조합 전에 확정해도 되는가

소스가 짧다는 사실만으로는 최종 압축 파일이 작다고 확정할 수 없다. 다른 literal과 prefix를 공유하는 hexadecimal 표기가 token 하나로는 길어도 최종 codec에서는 유리할 수 있다. compiler가 같은 명령어와 데이터를 만들면 원문 축약이 실행 파일 크기에 전혀 반영되지 않을 수도 있다.

따라서 일반적인 순서는 다음과 같다.

1. source 후보와 변환 audit 생성.
2. 동일한 compiler·옵션·입력 계약으로 원본과 후보 컴파일.
3. object 또는 native 파일 bytes가 같은 후보는 해당 **native 배포 경로**에서 중복 제거.
4. 서로 다른 결과는 정상적인 링크·완성 파일 검증·크기 비교 대상으로 유지.
5. source 자체를 압축해 배포하고 시작 시 compile하는 경로에서는 source bytes가 비용이므로, native bytes가 같아도 source packing 후보를 버리지 않음.

예상 결과를 새 값으로 덮어쓰거나 특정 엔진 이름을 예외 처리하여 재현을 통과시키지 않는다. bytes 또는 검사 결과가 예상과 다르면 source 변환·target 모델·toolchain·검사 계약 중 실제 원인을 확인한다. 원본은 identity 후보이므로 압축을 적용하지 않는 선택도 명시적인 정상 결과다.

## Python API

```python
variants = nvnotation.generate_variants(
    source_bytes,
    language="cpp",
    target="cpp17-lp64",
    token_contract="no-token-observation",
    compact=True,
    max_variants=16,
)
```

반환값은 `id`, `data`, `source_bytes`, `bytes`, `sha256`, `audit`, `notes`, `contract`, `size_claim`을 가진 dict의 리스트다. `data`만 bytes이고 나머지는 JSON으로 기록할 수 있다. `audit`는 원래 범위·표기·후보·타입·값과 검토 근거를 담는다. C 계열의 offset은 원본 bytes 기준이고 Python은 원본 line/column 기준이다.

`literal_candidates(token, language=..., target=...)`는 일반 식 문맥의 단일 literal에 대해 가능한 표기·표기 계열·모델 근거를 반환한다. source 전체에 이것을 정규식으로 적용하면 macro 보호를 우회하므로 실제 파일 변환에는 `generate_variants`를 사용한다.

## 검토 근거

`tests/test_notation.py`는 숫자의 값·타입 경계, macro/raw string/UDL 보호, pp-number와 comment가 합쳐지는 문제, Python AST/실행 결과, 실제 GCC/G++/Rust compiler를 검사한다. Python은 이미 minify된 코드의 비확대, 숫자·키워드 경계의 `-Werror` 실행, Latin-1과 UTF-8 BOM, CRLF, tab/form-feed 들여쓰기, 명시적 줄 연결과 multiline string을 포함한다. C의 모든 생성 정수 후보는 compiler가 판단한 원래 타입과 `_Static_assert`로 비교한다. 부동소수점 후보는 실제 타입과 메모리 bytes를 비교한다. C++/Rust 전체 파일 portfolio도 각각 compile하고 실행한다.

이 검사는 정해진 target과 사례에 대한 근거이며 임의의 C/C++/Rust 프로그램 동등성 증명이나 모든 압축 설정에 대한 전역 최적성 증명이 아니다. TCEC의 UCI·시작 시간·외부 명령·제출 크기 조건은 완성 파일 검사 단계에서 별도로 확인한다.

## 1차 출처

- [C11 committee draft N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf): §6.4.4.1 정수 타입 후보, §6.4.4.2 floating constant, §6.4.8 preprocessing number, §6.10 macro 처리.
- [C++ draft: integer literals](https://eel.is/c++draft/lex.icon): 기수·suffix와 정수 타입 후보. 문서의 최신 추가 기능 전체를 C++17에 소급하지 않고 `cpp17-lp64`가 허용하는 범위만 사용한다.
- [Rust Reference: tokens](https://doc.rust-lang.org/reference/tokens.html): literal token, raw string, tuple index, suffix와 숫자 경계.
- [Rust Reference: literal expressions](https://doc.rust-lang.org/reference/expressions/literal-expr.html): 정수/float suffix·추론과 literal 값 변환.
- [Python tokenize](https://docs.python.org/3/library/tokenize.html): 표준 tokenizer, encoding 감지와 token 위치; `untokenize`는 token 간 간격까지 원본대로 보장하지 않는다.
- [Python lexical analysis](https://docs.python.org/3/reference/lexical_analysis.html): integer/float/string literal 문법. 실제 AST 검증은 도구를 실행한 interpreter 버전에서 수행한다.
