# PR #13: 전체 제출 파일을 기준으로 선택하는 C 소스 압축

2026-10-21. [PR #13](https://github.com/daejunnom/Rove4k/pull/13)은 NVCompact의
후보 생성·선택·재현을 개선한다. 비교한 **26개 입력 모두 기존 최소 크기 이하**이며,
7개는 작아졌고 19개는 기존 winner와 바이트까지 같다. F material/move-TT는
기존 NVCompact의 **4,080 B에서 4,047 B**로 줄었다. 4,096 B까지의 여유는 49 B다.

이는 고정한 입력과 도구에 대한 압축·재현 결과다. F full을 4K에 넣었다는 결과나,
이번 세션에서 새 UCI·대국·기력 검증을 수행했다는 의미는 아니다. 실제 체스 엔진,
Python bootstrap, 자체 ELF loader는 실행하지 않았다. 컴파일러·decoder와 저장소의
작은 자체 산술 예제는 명시한 유한 자원 조건으로 실행했다.

전체 해시·실제 파일 대조·재현 기록의 검토본은 [비교 증거](../evidence/pr13/comparison.json),
[선택 편집](../evidence/pr13/selected-edits.json),
[자체 예제](../evidence/pr13/owned-examples.json),
[검증 범위와 실패](../evidence/pr13/validation.json)에 있다. 외부 엔진의 소스,
압축 payload, 실행 파일은 저장소와 npm 패키지에 넣지 않았다.

## 1. 비교 기준

| 항목 | 고정한 기준 |
|---|---|
| 이전 NVCompact 소스 | develop `56bfb5f45bff59a570d3f04f8eba06332d53c052` |
| 이번 실행에 사용한 구현 | `c5f4af0cfff7d7c6863dd142631f80b9f697e81a` |
| A–F 엔진 입력 | PR #12 `0e716e0b366272c66749f6e7194f64cb715e2d00` |
| 기존 도구 실행 파일 SHA-256 | `d96cd0bfd129fbb3b16e48c82036f8066a9bd678fada13a1644cba666eccda0f` |
| 새 도구 실행 파일 SHA-256 | `86bcf85c1dc2790003c26e84c273a9b263d6bb215c2f9bdea64400165749b986` |
| C 실제 컴파일러 / 링커 | GCC 13.3.0 / GNU ld 2.42 |
| C 분석 프런트엔드 | Clang 20.1.8, x86-64 LP64 |
| Rust / Node / Python | Rust 1.99.1 / Node 24.19.0 / CPython 3.12.14 |

이후 문서·증거 커밋의 head와 실제 측정에 사용한 구현 커밋을 구분한다. 기존 도구는
PR #12 snapshot에서도 NVCompact·Cargo 관련 경로가 위 develop과 동일함을 확인한 뒤
빌드했다. 새 도구는 최종 구현을 release로 빌드하여 별도 파일로 고정하고, 그 파일로
최종 campaign과 모든 replay를 수행했다.

외부 입력은 기존 General manifest 11개와 ELF manifest 2개의 원본 SHA를 그대로 사용했다.
**이번에 재실행한 baseline 13개는 저장소의 0.4 증거에 있는 이전 최소 크기와 SHA까지
모두 일치했다.** 따라서 더 나빠진 새 baseline을 기준으로 무회귀를 주장하지 않는다.
General에 있는 4k.c와 ELF v9.0은 같은 공개 파일을 서로 다른 부문 경로로 검사한 행이다.
26은 서로 다른 엔진 수가 아니라 고정한 입력·profile·부문 행 수다.

최종 정리 중 PR #12가 `8abcbc3a4af0ef02435ca1ba52f10b43715bf99c`로 진행한 것을
확인했다. 그 사이 정수 표현·초기화 공유·F terminal 처리와 명시적인 hash 정책 변경이
추가됐다. 아래 비교는 처음 고정한 **0e716e0 입력에 대한 결과**로 유지한다. 다른 head의
크기를 이 표의 baseline에 섞거나, 8abcbc3에 같은 절감량이 적용된다고 주장하지 않는다.
인계 문서에는 이미 반영된 변경을 표시했으며, 최신 head 통합 시에는 새 입력으로 비교한다.

General은 `--thorough --jobs 2`, A–F는 동일한 기본 codec 탐색과 `--jobs 2`를 사용했다.
A–F의 baseline/candidate manifest는 새 `source_search` 항목을 제외하면 같다.
source search는 최대 2라운드, 전체 파일 비용 평가 2,048회, scheduling deadline 300초다.
일반 평가 예산과 개별 compiler/decoder 제한은 구분한다. 300초는 실행 중 codec 호출까지
즉시 중단하는 엄격한 전체 wall timeout이라는 뜻은 아니다.

## 2. A–F 실제 전체 파일

원본은 해당 PR #12 head의 유지 recipe가 생성하는 전체 입력이다. 이전/새 NVCompact
열에는 header·bootstrap·payload 또는 자체 ELF 전체를 포함한다. 절감은 **이전 최소값
대비**다. 엔진 정책을 바꾼 서로 다른 F profile은 독립 행으로 유지한다.

| 입력 | 원본 | 이전 NVCompact | PR #13 | 추가 절감 | 4,096 B 기준 |
|---|---:|---:|---:|---:|---:|
| A | 4,652 | 4,637 | **4,616** | 21 | 520 B 초과 |
| B | 5,219 | 5,211 | **5,173** | 38 | 1,077 B 초과 |
| C | 4,992 | 4,979 | 4,979 | 0 | 883 B 초과 |
| D scalar, ELF | 5,966 | 5,966 | 5,966 | 0 | 1,870 B 초과 |
| D HQ, ELF | 6,175 | 6,175 | 6,175 | 0 | 2,079 B 초과 |
| E | 5,076 | 5,069 | **5,038** | 31 | 942 B 초과 |
| F full/default | 4,645 | 4,637 | **4,611** | 26 | 515 B 초과 |
| F material/noise | 4,369 | 4,359 | **4,331** | 28 | 235 B 초과 |
| F material/move-TT | 4,089 | 4,080 | **4,047** | 33 | **49 B 여유** |

A·B·E·F 세 profile은 검증된 C 표기 변경을 채택했다. C는 C 분석 용량 한도에 도달하여
새 C 편집을 채택하지 않았고, 기존 Python 표기 후보가 최종 선택됐다. 독립적으로 그
winner의 bytes 상수를 파싱하여 원래 10,174 B C 소스와 같음을 확인했다. D 두 행은
원본 ELF와 바이트가 같다. ELF 입력을 shell wrapper로 바꿔 작은 것으로 계산하지 않았다.

### F에서 줄어든 이유

F material/move-TT의 선택 편집은 한 단계 안에 조합한 12개 그룹이다.

| 편집 | 적용 지점 | raw C 길이 영향 |
|---|---:|---:|
| 지역 변수·매개변수의 한 글자 이름을 다른 한 글자로 변경, 10그룹 | 86 | 0 B |
| `0x88` → `136` | 5 | −5 B |
| `'\n'` → `10` | 3 | −6 B |
| 합계 | 94 | **−11 B** |

C는 7,821 B에서 7,810 B로 줄었지만, 주된 이득은 이름의 길이가 아니라 **압축 문맥**에서
나왔다. 고정한 제출 codec에서 실제 조합을 순서대로 재측정한 결과, 이름 편집들의
조건부 절감 합은 31 B, 상수 편집들은 5 B였고 전체 비용은 4,085 → 4,049 B였다.
최종 codec 포트폴리오를 다시 비교하여 4,047 B를 선택했다. 이 중간 경로의 출발점
4,085 B와 이전 NVCompact의 최소 4,080 B는 다른 값이므로, 최종 추가 절감은 **33 B**다.
개별 절감은 해당 순서·조합에 조건부이며 다른 입력에서도 더해지는 상수가 아니다.

실제 생성 native는 변경 전후 모두 18,576 B이며 SHA-256은
`c3fd3c09f8d72d4dd94cec47bfabd1c022cf151fd9624d29c1f750b90ba6126c`다.
컴파일러 stdout/stderr 해시도 같다. 전체 파일 재현 해시는
`1bf76bbcaaa3a4da6ef3bebd1cf8363991197eee0f2801424f2731074334361a`다.

A에서는 더 긴 표기도 이겼다. `33` → `041`을 4곳에 적용하면 raw C가 4 B 늘지만,
선택 중이던 조합의 전체 파일은 1 B 줄었다. `256` → `0400`도 같은 방향의 결과였다.
raw 길이 증가만 보고 후보를 버리는 방식으로는 이런 개선을 찾을 수 없다.

## 3. 외부 TCEC 대표 입력

공개 release·저자 제공 파일 또는 기존에 문서화한 대표 입력을 사용한다. 현재 비공개
대회 제출물과 정확히 같다고 주장하지 않는다. 출처·버전·대응 한계는
[`comparisons/general`](../comparisons/general)과 [`comparisons/elf`](../comparisons/elf)에 있다.

### General 4K

| 입력 | 원본 | 이전 최소 | PR #13 | 추가 절감 |
|---|---:|---:|---:|---:|
| 4k.c | 3,932 | 3,932 | 3,932 | 0 |
| 4ku | 4,093 | 4,088 | 4,088 | 0 |
| M4sseur | 4,095 | 4,092 | 4,092 | 0 |
| STRO4K | 4,096 | 4,078 | 4,078 | 0 |
| c4ke | 4,093 | 4,092 | 4,092 | 0 |
| ice4 | 4,087 | 4,082 | 4,082 | 0 |
| Molly | 4,096 | 4,095 | 4,095 | 0 |
| Moonfish | 3,941 | 3,889 | **3,871** | **18** |
| Pygone | 4,093 | 4,020 | 4,020 | 0 |
| Sunfish | 2,844 | 2,776 | 2,776 | 0 |
| we4k | 4,079 | 4,011 | 4,011 | 0 |

새 C source search는 이번 외부 입력 중 Moonfish에 활성화했다. 새 후보 생성의
대상 밖인 C++·Rust·Python 입력에도 기존 후보와 codec 탐색을 실행하여 이전 winner를
유지했다. 이 언어들의 binding rewrite를 새로 구현했다는 의미는 아니다.

Moonfish의 새 source는 원본과 같은 30,128 B native 파일을 생성한다. 기존에 있던
컴파일러 warning의 stderr SHA도 동일하다. 원본 public wrapper의 decoder 실패는
이전 기록과 같이 남아 있으며, 별도로 고정한 decoded payload와 새 candidate의 실제
decoder readback을 확인했다. 이 결과를 원본 배포 파일의 정상 실행이나 새 UCI 통과로
표시하지 않는다.

Moonfish에서는 이름·상수 편집에 더해 단일 문장을 감싼 중괄호 3쌍 제거가 채택됐다.
그 단계는 raw C를 6 B 줄이고, 그때의 고정 codec 전체 비용을 3,917 → 3,914 B로
줄였다. 선언·중첩 if·else 결합을 바꾸는 위치가 아님을 별도로 검토했다. 삼항연산자나
boolean 조건식 변경은 채택되지 않았다. 최종 추가 절감 18 B에는 이후 표기와 codec
조합도 관여하므로 중괄호 제거만의 기여로 표시하지 않는다.

### 4K ELF

| 입력 | 원본 | 이전 최소 | PR #13 | 결과 |
|---|---:|---:|---:|---|
| 4k.c v8.0 | 4,042 | 4,042 | 4,042 | 원본 ELF 바이트 유지 |
| 4k.c v9.0 | 3,932 | 3,932 | 3,932 | 원본 ELF 바이트 유지 |

native 파일 자체를 제출하는 경로에서는 native 바이트 동일성이 곧 파일 크기 동일성이다.
새 source portfolio가 실제 native ELF를 더 작게 만들었다고 보고하지 않는다. 자체
loader·코드 배치·데이터 표현의 개선은 별도의 native 의미·시작 계약으로 다뤄야 한다.

## 4. 자체 예제와 재현

| 예제 | 이전 최소 | PR #13 | 확인 |
|---|---:|---:|---|
| `native-build` | 16,056 | 16,056 | 압축하지 않는 링크 빌드, 바이트 동일 |
| `mixed` | 504 | 504 | C/Rust 조합, 바이트 동일 |
| `zero-tail` | 441 | 441 | 논리적 zero tail 복원, 바이트 동일 |
| `c-rewrites` | 2,141 | 2,141 | 기존·추가 조건 후보, 바이트 동일 |

네 예제 모두 측정 후보, winner 복사본, 내부 fresh build, 독립 replay의 두 복사본을
읽어 실제 크기·SHA를 대조했다. 독립 산술 oracle·build/verifier 계약과 기존 입력 해시가
유지되는지도 확인했다. 새 `c-rewrites` 후보는 기존 후보를 제거하지 않고 추가된다.

외부 General 11 + ELF 2 + A–F 9 = **22개**에 대해 baseline과 새 도구 각각 별도의
디렉터리에서 recipe replay를 완료했다. 최종 22개 모두 선택된 최소 파일과 크기·SHA가
일치하고, 필요한 decoder readback이 통과했다. source-search winner는 저장된 편집
단계를 다시 검증하며 native/diagnostic 동일성도 재확인한다. replay는 탐색 전체를
다시 실행해 우연히 같은 최소를 찾는 방식이 아니다.

## 5. 실제로 바뀐 NVCompact 동작

### 후보 생성과 실제 비용

`spell-c`는 지역 변수·매개변수의 binding을 보존하는 이름 후보와 정수·문자 표기 후보를
생성한다. 이미 한 글자인 이름, 같은 길이 또는 더 긴 표기도 후보에 남긴다. 전역·외부
linkage 심볼, member 이름, 매크로 문자열화 등은 같은 방식으로 추측해 치환하지 않는다.

`source_search`는 후보의 C 문자 수 대신 **복원 후 payload 전체를 실제 codec으로
재압축한 비용**을 측정한다. Python bytes에 C가 들어 있는 경우에는 명시한 literal 범위와
SHA를 확인하고 해당 C만 편집한다. 리터럴의 quoting·escaping 비용과 나머지 bootstrap을
모두 포함한다. outer Python AST와 지정 범위 밖 바이트도 확인한다.

조합한 편집의 비용은 다시 측정한다. 원본·기존 표기·기존 codec 후보를 보존하며,
새 source를 그 포트폴리오에 더한다. 조사 범위의 승자를 고르는 유한 탐색이므로 모든
편집·codec 조합의 전역 최적을 보장하지 않는다.

### 조건식과 삼항연산자

`rewrite-c --include-nonshrinking --individual-edits N`으로 raw 길이에만 묶이지 않는
후보를 생성할 수 있다. 새 boolean-domain 규칙은 `_Bool`, 증명된 boolean 연산,
0/1 literal, unsigned 1-bit field처럼 표현식의 값 범위가 확정된 경우만 다룬다.
일반 `int`나 signed bitfield를 이름·사용 관행만 보고 0/1로 가정하지 않는다.
`a!=1` → `!a`는 `a=2`에서 다른 결과이므로 일반 치환 규칙이 아니다.

기존 분기/삼항연산자 규칙의 타입·부작용·평가 횟수와 순서·NaN·volatile·atomic·macro
경계 검사를 유지했다. 완성한 후보는 다시 파싱하고, 선택할 때 실제 컴파일 결과까지
같아야 한다. **이번 A–F winner에는 조건식이나 삼항연산자 편집이 하나도 들어가지 않았다.**
지원 기능을 추가한 사실과 측정된 절감 원인을 구분한다.

### 코드 검토에서 발견하여 수정한 회귀

새 seed가 좋아지면 제한된 후속 codec 탐색에서 기존 seed가 밀려나고, 과거에 찾던
더 작은 refinement를 잃을 수 있었다. 단순히 원본 파일만 남기는 것으로는 기존 최소
무회귀가 성립하지 않았다. 기존 seed의 refinement를 먼저 보존하고 새 탐색 결과를
합치도록 수정했다. 자체 fixture는 실제 압축 결과에서 이 회귀를 재현하여 검사한다.

후보가 많을 때 전체 탐색 기록을 `summary.json` 안에 중복으로 넣으면 생성은 성공해도
reader의 32 MiB 제한을 넘을 수 있었다. 상세 기록은 별도 파일에 두고 summary에는
경로·크기·SHA·개수와 재현에 필요한 선택 recipe를 둔다. 실제 직렬화한 summary 크기도
쓰기 전에 reader 한도와 대조한다.

### C의 큰 헤더 분석

C profile의 10,174 B source는 SIMD 헤더 때문에 별도 진단에서 약 209 MiB
(218,675,664 B)의 Clang JSON AST를 만들었다. production의 bounded capture 한도는
32 MiB다. 분석 JSON의 크기를 엔진 자체의 런타임 메모리 요구와 혼동하지 않는다.

처음 구현에서는 이 한도로 선택적 source 탐색뿐 아니라 기존 유효 압축 결과까지
실패했다. 수정 후에는 **명확히 식별한 frontend output exhaustion**에 한해서,
동일한 flags로 제한된 syntax-only 검사를 성공한 뒤 탐색을 중단하고 마지막 검증된
후보를 유지한다. `frontend-output-budget`, `frontend_proof: incomplete`,
`truncated_output_accepted: false`를 기록한다. 잘린 AST를 읽거나 새 편집을 승인하지 않는다.
문법 오류·잘못된 설정·ABI/version 오류·native baseline 실패는 계속 오류다.
이미 채택한 편집을 replay할 때 필요한 증명도 완화하지 않는다.

## 6. 검증 결과와 남아 있는 한계

- Rust 전체: **60 passed, 0 failed, 0 ignored** — library 47, packing 10,
  source-search integration 3. 실제 Clang 20을 사용했다.
- Node launcher: 5/5, 전체 파일 비교 스크립트: 1/1. 실제 artifact/hash, 누락 행과
  이전 최소 회귀를 검사하며 엔진 실행을 대신한 성공을 만들지 않는다.
- 최종 코드 `c5f4af0`의 GitHub Actions: NVCompact Node 22·24 두 job과
  Repository lifecycle 모두 성공. npm tarball의 실제 offline 설치 검증도 포함한다.
  [NVCompact run](https://github.com/daejunnom/Rove4k/actions/runs/39544994949),
  [lifecycle run](https://github.com/daejunnom/Rove4k/actions/runs/39544994932).
- 독립 검토에서 source binding·typed literal·조건식·embedding·recipe replay 및
  codec 후보 보존을 대조했다. 다른 사람의 PR 승인으로 표시하지 않는다.

실패·미완료도 그대로 보존했다.

1. A–F canonical build의 일곱 historical native SHA gate는 이 환경에서 실패했다.
   읽을 수 있는 source·bootstrap·전체 입력의 핀은 일치하지만 과거 native SHA는
   달랐다. 기대값을 갱신하지 않았다. 이번 비교는 같은 환경에서 원본/후보가 동일
   native를 생성함을 확인한 별도 결과이며, historical build 재현 성공이 아니다.
2. 처음 `zero-tail`에 사용한 1 GiB 주소 공간 제한은 Node 24의 V8 CodeRange 예약에
   부족했다. 기존/새 도구를 명시적으로 2 GiB 조건에서 다시 확인했다. 원래 실패를
   보존했고 체스 엔진의 TT·worker 자원 설정을 바꾸지 않았다. baseline의 수동 재시도는
   기존 `runs.json` 밖의 실행이므로 해당 JSON만으로 명령줄을 복원했다고 주장하지 않는다.
3. 최초 Molly baseline은 PATH에서 rustc를 찾지 못했다. 명시적으로 준비한 Rust PATH로
   재실행하여 기존 최소와 동일한 결과를 얻었다. 누락 실행을 성공으로 채우지 않았다.
4. 최종 workspace 검사 첫 transcript는 완료 요약 없이 끝나 불완전으로 보존했다.
   원인은 확정하지 않았다. 재실행에서는 실제 subprocess return code와 모든 예상
   test-result 그룹을 함께 확인해 60개 완료를 기록했다.
5. UCI·체스 규칙·대국·성능·TCEC 서버 인수는 이번 세션에서 수행하지 않았다. 기존
   0.4 런타임 관측은 그때의 별도 증거로 유지한다. 새 wrapper의 실전 인수로 승격하지 않는다.

의미 보존의 근거는 타입·binding·편집 도출, 명시한 소스 관측 계약, 실제 native 및
compiler diagnostics 동일성, payload/decoder readback이다. 전체 native 동일성은
고정한 도구·recipe에 대한 강한 관측이며 모든 compiler/target에 대한 일반 정리는 아니다.
`no-token-observation`과 `compile-input-only`를 선언할 수 없는 입력에는 임의로 켜지 않는다.
정확한 적용 범위와 제한은 [SOURCE-PORTFOLIO](SOURCE-PORTFOLIO.md)를 따른다.

## 7. 재실행과 엔진 담당자 인계

아래는 저장소 root 기준이다. 외부 원본은 manifest의 SHA와 일치하는 파일을 별도
경로에 준비하고, `nvcompact`는 이번 구현으로 빌드한 실행 파일을 사용한다. `clang`은
검토한 Clang 20을 가리키게 한다. 새 출력 디렉터리를 사용한다.

```sh
NVCOMPACT_INPUTS=/absolute/external/inputs
NVCOMPACT_RUN=/absolute/external/pr13-general
NVCOMPACT_REPLAY=/absolute/external/pr13-moonfish-replay

nvcompact engines \
  --manifests tools/nvcompact/comparisons/general \
  --artifact-root "$NVCOMPACT_INPUTS" \
  --output "$NVCOMPACT_RUN" --thorough --jobs 2

nvcompact replay "$NVCOMPACT_RUN/moonfish/summary.json" \
  --output "$NVCOMPACT_REPLAY" --selection smallest
```

이전 결과와의 크기 비교는 별도 도구로 실제 파일을 읽는다.

```sh
node tools/nvcompact/scripts/compare-results.mjs \
  --manifests tools/nvcompact/comparisons/general \
  --baseline /absolute/external/baseline-general \
  --candidate /absolute/external/pr13-general
```

ELF는 `comparisons/elf`와 별도 출력 경로를 사용한다. A–F의 입력 식별자·embedding 범위와
분석 설정은 [입력 기록](../evidence/pr13/af-inputs.json)에 있다. PR #12 최신 head가
달라졌다면 그 head에서 정본을 다시 생성하고 source·literal SHA와 offset을 다시 확인한다.
이 문서의 0e716e0 입력에 맞춘 offset을 다른 head에 적용하지 않는다.

[PR #12 인계 문서](PR12-HANDOFF.ko.md)는 공통 변환으로 증명하지 못한 TT bound 조건,
0x88 유효 이동 범위, cast·signedness, tokenizer 소유권, SIMD 평가, loader 및 모델·탐색
변경을 따로 정리한다. 엔진의 worker·TT·탐색 정책을 줄이는 변경은 이 PR에 포함하지 않았다.
이 문서에서 측정한 0e716e0의 F full은 515 B, material/noise는 235 B가 초과한다.
다음 엔진 작업은 최신 head에서 새로 측정한 부족분을 기준으로 공통 처리 공유·데이터
표현·개별 알고리즘 변경의 비용과 의미를 판단해야 한다.
