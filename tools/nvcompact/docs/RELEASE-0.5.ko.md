# NVCompact 0.5.0 릴리스 노트

이 문서는 0.5.0 소스와 패키지 메타데이터의 배포 준비 사항을 기록한다.
최종 main 커밋의 Linux CI, 실제 tarball 검증, npm 게시와 GitHub Packages
미러 게시는 각각의 실행 결과로 확인해야 한다. 이 문서만으로 게시 완료나
새 패키지의 설치 검증을 주장하지 않는다. 기존 0.4.0·0.4.1 배포 근거는
해당 버전의 역사 기록으로 유지한다.

## 추가 및 변경

- `spell-c`와 opt-in `source_search`는 C 자동 지역 변수 이름과 타입을
  보존하는 리터럴 표기 등을 유한한 후보로 다룬다. 선택 기준은 소스 문자
  수만이 아니라 launcher와 payload를 포함한 완성 제출 파일의 실제 크기다.
  적용되는 바인딩·타입·관측 계약을 검사하고, 선언된 recipe에서 전체 native
  파일과 compiler diagnostics가 일치해야 후보를 채택한다. `replay`는 검색을
  다시 수행하지 않고 채택된 파생 과정을 복원한다.
- 소스 검색은 원본과 후보 소스, 파생 과정, 실패 및 미선택 결과를 외부의
  bounded attempt archive에 남긴다. `compare-attempts ARCHIVE... --output
  NEW_JSON`은 저장된 파일의 실제 hash와 입력·도구·관측·codec 문맥을 검사해
  호환되는 완성 파일 비용을 비교한다. 저장된 compiler, engine, loader 또는
  codec 명령을 실행하거나 과거 후보를 자동으로 재채택하지 않는다.
- guarded Boolean rewrite는 실제 C `_Bool`·`stdbool.h` 타입과 그 alias를
  지원한다. `a != 1` 또는 `1 != a`를 `!a`로 바꾸려면 평가되는 값이 0 또는
  1임을 증명해야 한다. `typedef int bool`이라는 이름만으로는 그 영역을
  가정하지 않는다. 목적지 타입으로 소스 값의 범위를 추정하지 않으며,
  평가 횟수·결과 타입·macro 경계·volatile/atomic 보호를 유지한다.
- 후보 실패 상태와 실행하지 않은 결과를 구분하고, 종료 정리 중 추가
  오류가 발생해도 최초 실패를 성공으로 덮어쓰지 않는다.

설정과 지원하지 않는 경우는 [source portfolio guide](SOURCE-PORTFOLIO.md)에
있다. Attempt archive의 후보 추가 저장 예산은 기본 64 MiB이며 0–512 MiB로
설정할 수 있고, 원본은 각 8 MiB 제한으로 별도 보존한다. 예산에 도달하면
선택적 검색을 멈추고 마지막으로 검증된 incumbent를 유지한다.
`compare-attempts`는 최대 16개 기록과 총 1 GiB 읽기 한도를 사용한다.
검색의 scheduling deadline은 전체 실행 시간을 강제로 제한하는 hard wall
clock timeout과 다르다.

## 기존에 측정한 범위

[PR #13 측정](PR13-RESULTS.ko.md)은 PR #12 커밋
`0e716e0b366272c66749f6e7194f64cb715e2d00` 기준 A–F 입력·프로필 9개,
공개 general 4k 입력 11개, 공개 ELF 입력 2개, 자체 예제 4개를 합친 26행을
이전 NVCompact 결과와 비교했다. 완성 파일 7개가 작아졌고 나머지 19개는
기존 winner와 전체 바이트가 같았다. 이후 [attempt 보존·Boolean 후속
검사](PR13-ATTEMPTS-FOLLOWUP.ko.md)에서도 같은 조건의 26개 결과가 PR #13
winner와 전체 바이트가 같았다. 이 값은 현재 Rove4k 엔진 전체를 새로
압축하거나 실행한 결과가 아니다.

F의 material/move-TT opt-in 프로필에서 기록된 4,047 B 결과는 full/default F의
4 KiB 달성이나 모든 A–F 엔진의 출품 적격성을 뜻하지 않는다. 소스·native·
진단·복원 일치, 실제 UCI 검사, 대회 규칙 적합성, 최종 서버 자원 및 대국
성능은 별도 관측이다. 이 릴리스 준비는 새 대국·strength 검증을 추가하지 않는다.

## 호환성과 배포

- npm 패키지와 실행 파일 이름은 계속 `nvcompact`이며 Node 22 이상이 필요하다.
- 번들 native target은 Linux x64/glibc다. Release CI는 Ubuntu 24.04를 사용하며,
  glibc 2.39 이상, zlib 및 GCC runtime이 필요하다. Windows·macOS·ARM·musl
  번들은 제공하지 않는다. WSL Ubuntu는 Linux 환경으로 사용할 수 있지만
  실제 ABI와 필요한 도구의 조건을 별도로 충족해야 한다.
- C/C++ 빌드는 선언한 compiler를 사용하고 typed C 변환에는 Clang이 필요하다.
  Decoder·interpreter·verifier 요구 사항은 선택한 deployment 계약에 따른다.
  외부 엔진이나 compiler를 npm 패키지에 포함하지 않는다.
- 빌드·패키지·검증 산출물은 저장소 밖에 둔다. `--no-build`는 임의의 과거
  실행 파일을 허용하는 옵션이 아니며 기록된 소스·호스트·실행 파일 신원을
  확인한다. 최종 배포는 병합된 main의 새 clean source에서 준비해야 한다.

실제 tarball 설치 예시는 `nvcompact-0.5.0.tgz`를 사용한다.
게시 절차와 기존 OIDC 경계는 [publishing guide](PUBLISHING.md)를 따른다.
이 릴리스의 source version 갱신은 dependency 추가나 업데이트를 포함하지 않는다.
