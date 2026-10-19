# NVCompact 0.3 작업 기록

작성일: 2026-10-19. 저장소는 `daejunnom/NVCompact`, 함께 준비한 엔진 프로젝트는 `daejunnom/Rove4k`다. NV는 **N-Versions**를 뜻한다. 이번 작업은 구현·표현·도구·링크·압축 후보를 비교하는 도구의 개선이며 Rove4k의 탐색 엔진 구현이나 npm registry 게시가 아니다.

## 저장소와 공통 규약

Rove4k에는 `AGENTS.md`, `CONTRIBUTING.md`와 공통 엔지니어링 계약을 커밋했다. NVCompact에는 같은 원칙을 적용한 npm workspaces, CLI, Python 구현, C/Rust 링크 예제와 TCEC 실험 입력을 커밋했다. 사용자가 저장소에 제공한 MIT 라이선스를 각 프로젝트 자체 코드와 패키지 metadata에 반영했다. 실험에 포함한 외부 엔진의 라이선스는 원래 파일과 함께 유지한다.

공통 규약은 전체 제출 파일과 실전 성능, many-core의 총자원·경합 비용, 의미·소유권·수명, 재현 불일치의 원인 수정을 규정한다. 특정 탐색 방식, 언어, 스레드 수, 파일 수, 추상 계층이나 후보 수를 고정하지 않는다. 상세 알고리즘 설계와 과거 강한 규약 초안은 앞서 제공한 외부 핸드오프에 비규범적 참고 자료로 남긴다.

## 실행 경로를 구분했다

| 명령 | 빌드·압축 | 생성 프로그램의 실제 실행 |
|---|---|---|
| `build` | 선언된 컴파일·링크와 raw bytes 독립 재현. NVCompact 표기 변환·ELF 변환·codec·wrapper 생략 | 기본 미실행 |
| `build --verify` | 같은 native 경로 | baseline·후보·선택 파일 checker 실행 |
| native recipe의 `reproduce` | 같은 링크 파일의 bytes 재현 | 기본 미실행. 원 recipe가 검증됐어도 동일 |
| native recipe의 `reproduce --verify` | 같은 링크 파일의 bytes 재현 | 이번 호출에서 최종 checker 실행 |
| `run` 및 해당 압축 recipe의 `reproduce` | 기존 빌드·링크·배포·압축 경로 | 기존 실행 검증 유지 |
| `rewrite-c` | Clang 분석과 구조별 C 소스 생성 | C 프로그램 미실행 |
| `resource plan` | 지문·현재 자원 읽기, 계획 저장 | 엔진·compiler/version probe 모두 미실행 |
| `resource run ... --start` | 계획과 자원을 재확인 | 충족한 경우에만 실제 UCI 실행 시도 |

`build`의 기본 결과는 `built`와 `verification: not_run`이다. 이를 동등성 검증 통과로 표시하지 않는다. `--verify`도 실제 checker가 확인한 입력·상태·ABI 계약의 범위로 읽는다. 선언된 `post_link` 등 임의 빌드 명령 자체는 실행되므로, 기본 경로의 무검증을 build script의 행위를 제한하는 sandbox로 설명하지 않는다.

사용 명령과 상태의 상세 설명: [NATIVE-BUILD.md](NATIVE-BUILD.md), [MANIFEST.md](MANIFEST.md).

## C 표현 축약

`rewrite-c`는 원본과 개별 규칙·복합 규칙의 소스 후보를 생성한다. Clang AST의 원래 피연산자 타입, 묵시적 변환, 문맥과 원문 토큰을 함께 확인한다. 각 변경을 같은 frontend로 다시 파싱하고 적용 근거를 audit에 기록한다. 기존 `notation`의 object bytes 동일성 조건과 달리, 구조 후보는 서로 다른 component variant로 native runner에 연결해 실제 파일을 비교할 수 있다.

반환·대입의 조건식 전환, 조건부 효과와 short-circuit guard, boolean 정규화, 0 비교와 truth 문맥, 비교 반전·De Morgan, 복합 대입·증감, 단일 문장 중괄호·무한 루프 표현을 검토했다. 타입·전처리·부작용·수명 조건을 만족한 경우만 짧은 후보로 만든다. 범용적인 함수명 축약, 임의 산술 재배열, bit trick, 배열·상태표 변환이나 branchless 탐색 설계를 모두 자동 적용했다고 주장하지 않는다.

이번 검토에서는 다음과 같은 실제 실패 원인을 발견하고 일반 조건으로 처리했다.

- 분기별 반환 변환을 `?:`의 공통 타입 변환으로 바꾸면 signed/unsigned 값이 달라질 수 있다. 반환 타입으로 변환된 AST의 겉 타입만 비교하지 않는다.
- 새 키워드가 macro일 수 있고, empty macro와 `_Pragma`의 효과는 AST에서 사라질 수 있다. 원문과 전체 macro 정의를 함께 보호한다.
- AST 재파싱만 통과해도 토큰 결합으로 다른 식별자가 될 수 있다. lexer가 확정하지 못하는 식별자 표현은 관측 계약 밖으로 분명히 처리한다.
- callback의 실제 호출 속성, `returns_twice`, volatile/atomic, `_Generic`, `sizeof`, compound literal과 확장 AST 문맥을 일반 scalar 식처럼 취급하지 않는다.

원본보다 짧은 소스가 더 작은 실행 파일을 보장하지는 않는다. 컴파일러가 같은 기계어로 만들 수도 있고, 명령 배치·반복 패턴·압축 header 때문에 역전될 수도 있다. 원본 후보를 유지하고 응용 checker를 통과한 실제 완성 파일에서 비교한다. 원본이 동률 또는 최솟값인 결과도 정상적인 조사 결과다.

전체 자동 규칙·적용 조건·보류한 대안·실측과 재현 명령: [C-REWRITES.md](C-REWRITES.md).

### 작은 C 예제의 실제 비교

Clang 20.1.8의 같은 컴파일·링크 설정에서 원본과 13개 규칙별·복합 후보를 비교했다. 15개 source recipe에서 서로 다른 소스는 10개였고, 링크 후보 15개와 raw/gzip/xz의 전체 파일 45개를 검사했다.

| 후보 | C 소스 | 링크 ELF | gzip-9 완성 파일 | xz-6 완성 파일 |
|---|---:|---:|---:|---:|
| `raw` | 661 B | 14,480 B | 2,368 B | 2,197 B |
| `c-all` | 597 B | 14,480 B | 2,368 B | 2,197 B |
| `c-if-return` | 635 B | 14,480 B | 2,368 B | 2,197 B |
| `c-compound` | 649 B | 14,480 B | 2,368 B | 2,197 B |
| `c-leaf-braces` | 645 B | 14,480 B | 2,368 B | 2,197 B |

복합 후보의 소스는 64 B, 약 9.68% 줄었다. 그러나 모든 링크 ELF가 실제 bytes까지 같았으므로 구조 축약으로 추가로 절감한 최종 파일은 **0 B**다. 동점 순서에 따라 `raw + xz-6`가 채택됐으며 payload 1,600 B와 loader 597 B를 합한 2,197 B를 새 빌드와 별도 reproduce에서 재현했다. 이것은 compiler가 이번 작은 예제를 같은 결과로 정규화한 관측이며, 모든 C 프로그램이나 다른 toolchain의 동일성을 뜻하지 않는다.

## 고메모리 검증

ice4 v6.1과 c4ke v3.0의 256 GiB 할당, M4sseur 1.0의 64 GiB TT, Molly 해당 commit의 96 GiB TT 설정을 원본 프로파일로 기록했다. 각각의 원래 worker 구성과 UCI 옵션을 보존했다. 이 숫자는 소스에서 확인한 주요 설정이고 프로그램 전체 peak RAM을 측정한 결과가 아니다. 여유량·주소 공간 상한은 계획의 별도 추정값이다.

네 원본은 현재 환경에서 자원 조건을 충족하지 않아 계획에 `blocked`가 기록된다. **이번 개선에서 실제 고메모리 원본 실행은 0회다.** 작은 UCI fixture로 opt-in, 입력 변경·자원 부족의 사전 차단, 실제 자식 제한, symlink 호출 이름, 옵션 보존과 취소 후 자식·손자 종료를 확인한다.

가용 메모리 관측은 RAM 예약이 아니며 `RLIMIT_AS`·`RLIMIT_CPU`는 프로세스 단위다. 전체 프로세스 트리에 대한 정확한 RAM/CPU 격리가 필요한 서버는 별도 cgroup/container/job 조건에서 실행한다. 도구가 그런 서버를 생성하거나 기존 cgroup 설정을 바꾸지는 않는다.

실제 명령·계획 구조·제한 범위: [RESOURCE-TESTING.md](RESOURCE-TESTING.md). 계획 근거: [resource-plans-v03/summary.json](../evidence/resource-plans-v03/summary.json).

## Python 유지와 Rust 전환

이번 구현은 Python을 유지한다. 이후 Rust로 옮길 때는 입력·recipe와 결과 의미, 명시적 실행, 실제 자식 회수, bytes 재현의 계약을 먼저 보존한다. bounded worker, 불변 입력 공유와 대형 버퍼 복사 감소는 검토할 설계 방향이다. 외부 compiler나 codec가 실제 병목이면 언어 교체만으로 큰 개선이 없을 수 있으므로 실제 작업량과 자원으로 판단한다.

Rust의 타입·소유권만으로 논리 오류나 프로세스 종료가 해결된다고 가정하지 않는다. 옛 codec와 새 codec가 같은 입력을 복원해도 압축 bytes는 다를 수 있으므로 backend와 버전을 기록하고 재현 실패의 기대 hash를 자동 갱신하지 않는다. 상세 인수 방향: [RUST-ROADMAP.md](RUST-ROADMAP.md).

## 검사 근거의 수명

`evidence/`는 과거 0.2 연구·패키지 결과와 이번 0.3 변경 검사를 구분한다. 고정된 개수의 검사를 영구 규약으로 만들지 않으며 실제 수행·생략·미실행·실패를 각각 기록한다. 초기 원격 CI에서 Node 22가 지원하지 않는 테스트 CLI 옵션을 발견해 public `node:test` 실행 경로로 수정했다. GitHub Actions의 Node 22·24 결과와 로컬 설치본 결과는 각각의 실행에 귀속한다.

과거 11개 엔진 입력의 압축 수치와 UCI 결과는 이전 캠페인의 근거로 그대로 보존했다. 이번 작은 C fixture의 실행 성공이나 새 고메모리 계획으로 그 과거 미검증 엔진들을 통과 처리하지 않는다. 현재 package·core·설치 검사의 상세 결과는 [evidence 안내](../evidence/README.md)를 따른다.

### 이번 로컬 인수 결과

- 통합 검사: Python **77/77**, CLI **11/11**, skip **0**. 원본 high-memory 엔진은 사용하지 않았다.
- 통합 검사 후 설치본의 강한 관측에서 `platform.platform()`이 내부적으로 시간 예산 밖의 `uname -p`를 실행함을 발견했다. 설명용 platform 필드를 `os.uname()`으로 바꾸고 native 3개·runner 5개 검사를 다시 통과했다. 이 마지막 변경과 재검사 범위는 [integration-validation-v03.json](../evidence/integration-validation-v03.json)에 별도로 기록했다.
- 최종 npm tarball을 별도 소비자 디렉터리에 오프라인 설치한 검사는 **9개 check 그룹 통과**다. 기본 native build와 native reproduce는 직접 compiler 요청만 사용하며 Python codec 호출 시도는 0회였다. 두 `--verify` 경로는 각각 256개 정상 입력과 2개 오류 입력을 실제 검사했다.
- native 예제는 **16,056 B**, 압축을 사용하는 기존 C mixed 예제는 **520 B**를 독립 재빌드·재현했다. 두 숫자는 서로 다른 예제이므로 같은 프로그램의 전후 압축률로 비교하지 않는다. 후자는 199,360개 정상 record와 22개 case를 최종 oracle에서 검사했다.
- 최종 로컬 tarball은 **97,661 B**, 실제 파일 **42개**다. 설치·실행 전후 파일 bytes와 mode가 같고 임시 소비자 디렉터리를 정리했다. 압축기·프로그램 실행 차단 장치는 의도적으로 실패하는 양성 대조로 확인했으며, 발견된 문제를 피하는 allow-list 예외를 넣지 않았다.

설치본의 최초 실패와 수정 후 성공은 각 timestamp별 로그에 보존했다. 실제 설치 검사 결과: [package-validation.json](../evidence/package-validation.json). 설치본 audit는 npm이 실행한 Python 코어의 직접 subprocess 및 지정된 codec 진입점 범위이며 compiler/checker 내부 전체를 재귀적으로 추적했다는 주장은 아니다. 원격 Node 22·24 CI 결과는 GitHub의 해당 commit 실행에서 따로 확인한다.
