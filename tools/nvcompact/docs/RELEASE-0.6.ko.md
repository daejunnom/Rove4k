# NVCompact 0.6.0

0.6.0은 **압축과 분리된 숏코딩 자문**, C/C++/Rust의 보수적 값 영역·타입 분석,
제한된 n-version 식 비교, 탐색·캐시·검증의 중복 비용 개선을 제공한다.
패키지와 명령 이름은 `nvcompact`다. Cargo/npm 버전만 함께 올리며 의존성은 갱신하지 않는다.

## 새 명령과 지원 범위

```sh
nvcompact advise-source final.c --language c --report c-advice.json
nvcompact advise-source final.cpp --language cpp --standard c++17 --report cpp-advice.json
nvcompact advise-source final.rs --language rust --standard rust2021 --report rust-advice.json
nvcompact inspect-binary submission --word-bytes 8
```

기존 `advise-c`도 C 전용 진입점으로 사용할 수 있다. 자문 명령은 입력을 수정하지 않고
압축 후보를 생성하지 않는다. 상수·미사용 경고와 짧은 식의 제안은 검토 자료이며,
원본을 바꾸려면 별도의 의미·native·전체 제출 파일 검증이 필요하다.
표현식에서 줄어든 bytes를 압축된 파일의 절감으로 환산하지 않는다.

| 기능 | C | C++ | Rust |
| --- | --- | --- | --- |
| typed 상수 중복·재사용 제안 | Clang의 타입·값별 진단 | C++ 타입·값별 진단 | 허용 함수 안의 primitive 타입·값별 진단 |
| 미사용 변수·함수 경고 | translation-unit 참조와 local 읽기 관측 | 허용 문맥의 참조·local 읽기 관측 | 허용 함수의 매개변수·지역변수 읽기; crate 전체 함수 판정은 미지원 |
| 연산 위치별 값 영역 | interval·known bits·유한 집합 | 허용 built-in scalar 부분집합 | `i32/u32/i64/u64/bool` 부분집합 |
| n-version 비교 | C 타입·정의성·단락 평가 | 추가 bool·승격·value category 확인 | Rust 재파싱·타입 검사·모든 유한 값 재평가 |
| 동적 관측·진단 복사본 | 선택형 `--profile`·`--instrument` | 명시적 미지원 | 명시적 미지원 |

C++는 실제 Clang C++17/C++20 AST를 사용한다. 지원하지 않는 overload·template·참조·호출 등은
함수의 흐름·동치 분석을 보류한다. 직접 관측 가능한 typed literal 중복은 별도 진단에 남을 수 있다.
Rust는 매크로나 build script를 실행하지 않는 제한된 scalar parser다. 최상위 `fn/pub fn` 외 item은
주변 타입 문맥을 무시하지 않기 위해 파일 전체를 보류하며, 함수 안의 미지원 구문도 명시적으로 보류한다.
이 기능은 전체 C++ 프로그램·Rust crate 분석기라는 선언이 아니다.

Python·JavaScript 등은 이 고정 폭 영역 분석에서 명시적으로 거절한다. 확장자로 C를 추측하거나
무한 정밀도 정수를 고정 폭으로 낮추지 않는다. 원문 bytes를 압축하는 기존 기능과는 별개다.
지원하지 않는 언어와 C++/Rust profile·instrument 요청은 입력 읽기·출력 생성 전에 거절한다.

타입·구문·예산·보고서의 정확한 계약은 [언어 설계](LANGUAGE-ADVISOR.ko.md),
유틸리티 사용법은 [자문 도구 설계](SHORTCODE-ADVISOR.ko.md)에 설명한다.

## 영역 기반 n-version 비교

읽기 위치마다 분기 조건·대입·합류를 반영한다. 추론할 수 없는 연산과 예산 소진은 포함 영역을
넓히거나 제안을 보류하며, 표본의 최소·최대를 정적 보장으로 승격하지 않는다.
공통 DAG와 타입을 포함한 전체 출력 벡터를 재사용해 반복 평가를 줄이고, 부분 평가 벡터는 동치로 합치지 않는다.
후보 문법과 탐색 예산이 유한하므로 가능한 모든 최단 식을 찾았다는 주장을 하지 않는다.

예를 들어 C의 `(to>>4)==0||(to>>4)==7`은 사용 위치의 `to`가 `0..127`에 포함될 때
`!(to+16&96)`으로 제안할 수 있다. `!(to&0x88)`만으로는 더 큰 값도 통과하므로 같은 전제를
얻을 수 없다. 합성기는 이 상수를 특별 취급하지 않으며, 다른 shift·offset·mask도 같은 문법으로 비교한다.

Rust에는 C의 정수 logical-not를 그대로 옮기지 않는다. 허용된 영역에서 실제로 확인한 예는
`(x>>4)==0||(x>>4)==7` → `x+16&96==0`이며, Rust 타입·우선순위·overflow 계약으로 다시 평가한다.
C++는 값뿐 아니라 결과 `bool`과 prvalue 여부까지 맞춘다.
설계와 조건부 동적 비교의 범위는 [도메인·n-version 문서](DOMAIN-NVERSION.ko.md)에 둔다.

## 중복 비용과 메모리 개선

최종 파일 검사에서 전체 복원 버퍼를 만드는 대신 작은 고정 버퍼로 복원·비교하고,
비용 캐시는 완전한 key 비교와 유한 FIFO 수명을 유지한 hash index를 사용한다.
병렬 작업은 결과 순서·오류·최종 독립 재생성을 보존하면서 한정된 작업 창으로 제출한다.
refinement는 덮어쓸 옵션을 제외한 실제 recipe identity로 재료화 전에 중복을 제거하고,
전체 정렬 대신 필요한 family별 최소 후보를 안정적인 선형 선택으로 고른다.

| 기록된 실험 | 결과와 해석 |
| --- | --- |
| 앞선 48회 고정 입력 비교 | cache hit 작업 135.308 → 16.339 ms; churn 277.812 → 64.485 ms |
| 8 MiB 복원 검증·4 jobs | 최대 RSS 77,268 → 12,864 KiB; 그 실험의 메모리 결과 |
| 후속 96회 비교의 순수 계획 실험 | 1.759921 → 0.020000 s; codec을 제외한 합성 계획 비용 |
| 실제 legacy 검색·4 jobs | 중앙값 0.742630 → 0.708408 s; 약 4.61%, 분포가 겹침 |

전체 검색이 88배 빨라졌다는 뜻은 아니다. 변경한 refinement를 사용하지 않는 control도 포함했으며,
일부 조건의 시간·RSS 증가는 그대로 기록했다. 실패하거나 이득이 없었던 scratch-buffer 변경은 채택하지 않았다.
측정 입력·환경·분포·불리한 결과는 [첫 성능 기록](PERFORMANCE-ADVICE-RESULTS.ko.md)과
[후속 성능 기록](DOMAIN-PERFORMANCE-RESULTS.ko.md)에서 확인한다.

## 언어 의미 감사와 비교 입력

다음은 0.6.0 준비 이전의 해당 구현에 대한 고정 source 검증이다. 버전만 바뀐 실행 파일의
설치·배포 결과와 구별하며, 전체 C++·Rust 언어에 대한 증명으로 확대하지 않는다.

| 독립 native 검사 | 관측 결과 |
| --- | --- |
| C++17 | 제안 73개, whole-function 비교 87,809회, 타입·value category 확인 73개 |
| C++20 | 별도로 같은 73개·87,809회·73개 확인 |
| Rust 2021, overflow 검사 켬 | 제안 54개, whole-function 비교 64,366회, 정확한 타입 확인 54개 |
| Rust 2021, overflow 검사 끔 | 별도로 같은 54개·64,366회·54개 확인 |
| Rust transfer 함수 8개 | 모드별 5,402개 native 관측을 포함 영역과 대조 |

위 허용 영역에서 불일치와 sanitizer 오류는 관측하지 않았다. 초기 실패·수정 전 결과와
최종 재검증을 따로 보존했다. 전체 작업공간 152개 통과 뒤 마지막 일반 상수 cast-fold 개선을
Rust 10개 단위 검사와 독립 native 비교로 다시 확인했다. 이 기록을 최종 배포 SHA의 전체 CI 실행으로
대신 세지 않으며, 배포 workflow는 실제 최종 버전에서 전체 검사를 다시 수행한다.
이후 언어 구현 commit `8184e4301bf03780957437ef5de7cb0834a018ec`의
[NVCompact CI](https://github.com/daejunnom/Rove4k/actions/runs/39610883475)는 Node 22·24 양쪽에서
전체 Rust 153개 검사, build·pack·설치 검사를 통과했다. 0.6.0 준비는 그 뒤의 버전·설치 게이트·문서 변경이며,
C++ report의 보류 설명을 더 정확히 하는 문자열 변경 외에 언어 분석 알고리즘을 다시 바꾸지 않는다.
상세 결과·해시·범위는 [언어 검증 기록](LANGUAGE-RESULTS.ko.md)과 그 evidence에 둔다.

외부 TCEC 비교에서는 보존한 원문의 hash를 대조했다. Moonfish C 분석과 별개로,
4ku·ice4의 전체 C++ translation unit은 AST 크기 한도에 걸렸고 Molly의 Rust 전체 파일은
미지원 최상위 문맥으로 보류됐다. 성공한 분석이나 새 압축 결과로 집계하지 않았다.
외부 엔진의 새 빌드·대국·strength·출품 자격 검증을 수행한 릴리스가 아니다.

## 설치와 배포 게이트

Node 22 이상, Linux x64/glibc가 npm 번들의 대상이다. 공개 native 빌드는 Ubuntu 24.04에서
검사하며 glibc 2.39 이상, zlib와 GCC runtime이 필요하다. C/C++ 자문에는 별도 Clang이 필요하고,
Rust 자문 자체는 rustc나 Cargo를 실행하지 않는다. Windows·macOS·ARM·musl 번들은 제공하지 않는다.

`verify:package`는 실제 tarball을 공백·한글 경로의 독립 consumer에 오프라인 설치한다.
기존 build/reproduce/명시적 verifier 실행과 256개 정상·2개 오류 입력 검사에 더해,
설치된 C++/Rust 유틸리티·영역·제안, 반복 bytes와 명시적 미지원 경계를 확인한다.
입력·설치 파일의 불변과 압축 후보 생성 0을 함께 확인한다.

배포는 feature → develop PR 및 검증된 develop → main PR을 거친다.
등록된 OIDC workflow에 version `0.6.0`, 실제 main SHA, `operation=publish`를 전달한다.
package job의 전체 검사·build·pack·설치가 성공해야 publish job이 동일 tarball을 전달한다.
publish job은 재빌드·재포장하지 않으며 source·runtime·tarball 식별과 registry의 미게시 버전을 확인한다.
자세한 운영 경계와 기존 OIDC 성공 이력은 [배포 문서](PUBLISHING.md)를 따른다.

최종 공개 상태는 [release workflow](https://github.com/daejunnom/Rove4k/actions/workflows/nvcompact-publish.yml),
[npm 0.6.0](https://www.npmjs.com/package/nvcompact/v/0.6.0) 및 해당 PR의 실행 기록으로 확인한다.
로컬 포장·검사와 registry 게시 완료를 같은 상태로 보고하지 않는다.
