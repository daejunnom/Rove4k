> 이전 준비 단계의 기록입니다. 2026-10-19에 사용자가 **Rove4k**와 **NVCompact** 저장소를 생성하고 MIT 라이선스를 선택했습니다. 현재 상태는 루트 README와 LICENSE-STATUS.md를 따릅니다.

# NVCompact 0.2.0 — 저장소 이름, 모노레포와 npm 패키지

작성일: 2026-10-19. 이 문서는 이번에 준비한 코드와 실제 검사 결과를 설명한다.

## 1. 추천 이름과 짧은 GitHub 설명

체스 엔진 이름은 **Rook4k**를 가장 추천한다. `R`로 시작하고 `4k`로 끝나는 6글자이며, rook라는 체스 기물과 목표 부문을 바로 연결한다. 탐색 알고리즘, 평가 방식, 구현 언어나 병렬화 방식을 이름에 고정하지 않는다.

| 이름 | ASCII 글자 수 | 판단 |
|---|---:|---|
| **Rook4k** | **6** | 체스 프로젝트라는 뜻이 가장 직접적이다. 1순위 추천. |
| **Rove4k** | **6** | RoveZero/Rovent의 계보를 이어 가는 대안. |
| **Ray4k** | **5** | 기물의 이동선을 연상할 수 있고 짧다. |
| **Rank4k** | **6** | 체스판의 rank와 연결되지만 순위라는 뜻도 있다. |
| **R4k** | **3** | 가장 짧은 실용 후보지만 이름 자체의 정보가 적다. |

새 엔진 저장소의 초기 GitHub 설명:

```text
A UCI chess engine project targeting TCEC 4K.
```

동작하는 엔진을 구현한 뒤에는 다음처럼 줄일 수 있다.

```text
A compact UCI chess engine for TCEC 4K.
```

NVCompact 저장소와 npm 패키지의 공통 설명:

```text
N-versions compaction with verified builds, packing, and reproducible results.
```

더 짧은 대안:

```text
Compare verified build variants and pack smaller programs.
```

추천 조합은 범용 도구 저장소 `nvcompact`, 향후 엔진 저장소 `Rook4k`, npm 패키지 후보 `nvcompact`다. 이름은 제안 상태이며 이번 작업에서 원격 저장소를 생성하거나 레지스트리에 게시하지 않았다.

2026-10-19 02:45 UTC의 공개 API 조회에서 npm `nvcompact`와 GitHub `daejunnom/Rook4k`, `daejunnom/Rove4k`, `daejunnom/NVCompact`는 HTTP 404를 반환했다. 이는 공개 메타데이터를 받지 못했다는 관측이다. 이름 예약, 게시 권한, 비공개 저장소의 부재나 실제 생성 가능성을 보장하지 않는다. 원시 결과는 모노레포의 `evidence/name-availability.json`에 있다.

## 2. NVCompact의 뜻

이번에 약어를 **N-Versions Compaction**으로 명확히 정리했다.

| 구성 | 뜻 | 기능과의 관계 |
|---|---|---|
| **NV** | **N-Versions** | 여러 소스 표기, 대체 구현, 컴파일·링크 조합과 압축 후보를 비교한다. |
| **Compact** | **Compaction** | 선언한 계약과 검사를 만족하는 후보에서 전체 배포 파일이 작은 결과를 선택한다. |

이전 코드에 이미 명시된 약어를 인용한 것은 아니다. 지금 정한 설명은 사용자가 요청한 CTK3의 n-versions 방식과 NVCompact의 후보 포트폴리오 구조를 반영한다.

후보 수가 곧 독립적으로 작성한 구현 수는 아니다. 같은 결과를 낸 후보가 여러 개 있다는 것만으로 일반적인 의미 동등성이나 전역 최소 크기가 증명되지 않는다. 이 도구의 결과는 실제 검색한 후보, 대상 환경, 의미 계약과 수행한 검사의 범위에서 해석한다.

## 3. 구현한 모노레포

| 경로 | 책임 |
|---|---|
| `packages/nvcompact` | npm CLI, 기존 Python 코어, C/Rust 예제, 링커 스크립트, UCI 프로필 |
| `packages/tcec4k-lab` | 11개 기존 엔진 입력·매니페스트, 대응 소스·라이선스와 출처 |
| `scripts` | 구성 검사, npm pack, 실제 tarball 설치 검증, Python 검사 진입점 |
| `tests` | CLI 계약, 하위 프로세스 수명, 실제 패키지 내용 검사 |
| `docs` | 의미·재현 계약, CLI와 패키징, 이름과 향후 배포 안내 |
| `evidence` | 원본 코어 이동, 이전 엔진 실험, 이번 설치·실행·재현 기록 |
| `nvcompact-monorepo-handoff/` | 모노레포의 형제 디렉터리. 이전 상세 설계와 판단을 보존한 비규범적 핸드오프 |

루트에서 npm workspaces로 두 패키지를 연결한다. `nvcompact-tcec4k-lab`은 `nvcompact: "0.2.0"`을 선언하므로, 로컬 개발을 위해 npm 레지스트리에 먼저 게시할 필요가 없다. 패키지 선택·연결은 [npm workspaces 공식 문서](https://docs.npmjs.com/cli/v11/using-npm/workspaces/)를 따른다.

현재 공개용 CLI 후보 하나와 private 실험 workspace를 두었다. 이 경계는 현재 책임과 설치 대상을 정리한 구현 선택이며 영구 규약이 아니다. 새 근거가 있으면 에이전트가 패키지 경계나 알고리즘을 바꿀 수 있다.

Rook4k는 향후 자체 엔진 프로젝트의 이름 제안이다. 이번에 새 체스 엔진을 구현한 것은 아니며, `tcec4k-lab`은 기존 엔진 실험 자료를 담는다.

### 보존한 내용

기존 Python 코어 8개, 총 **190,580바이트**는 원본과 SHA256이 일치한다. 원본의 작은 예제와 링커·프로필도 함께 배치했다. 이 기록은 이번 이동의 근거이며 향후 코어 개선을 금지하는 규칙이 아니다.

PALS의 탐색–엔진 소통 아이디어, 많은 코어를 활용하는 병렬 탐색과 이전 압축 설계는 외부 핸드오프에 유지했다. 공통 규약에는 의미·수명·전체 성능·원인 수정·실제 검증의 원칙을 남겼다. 특정 과거 파이프라인과 모양이 다르다는 이유로 개선을 거절하지 않도록 했다.

## 4. npm CLI의 실제 동작

| 명령 | 용도 |
|---|---|
| `nvcompact --help`, `--version` | 패키지 안내와 버전. Python 없이 실행 가능. |
| `nvcompact doctor --json` | CPython과 압축 API의 실제 왕복 실행, 코어 버전·런처 SHA 기록 |
| `nvcompact notation` | 적용 계약을 만족하는 표기·토큰 변환 후보 생성 |
| `nvcompact run` | 구현·컴파일·링크·압축 포트폴리오 실행 |
| `nvcompact reproduce` | 선택한 네이티브 빌드 recipe의 독립 재현 |
| `nvcompact envelope` | 검토한 배포 파일의 압축 후보 비교와 선택적 UCI 실행 |
| `nvcompact replay` | 배포 파일 선택의 재현과 선택적 UCI 실행 |
| `nvcompact uci` | 최종 엔진 파일의 프로토콜 검사 |
| `nvcompact engines --manifests ...` | 명시한 로컬 엔진 매니페스트 집합 실행 |

Node CLI는 기존 Python 구현으로 명령을 연결한다. 런타임 npm 의존성은 **0개**이며 설치 훅으로 Python·컴파일러를 다운로드하거나 코드를 컴파일하지 않는다. npm 패키지의 `bin`과 `files`를 명시하고 실제 tarball을 검사했다. [package.json 공식 문서](https://docs.npmjs.com/cli/v11/configuring-npm/package-json/)와 [npm pack 공식 문서](https://docs.npmjs.com/cli/v11/commands/npm-pack/)가 관련 동작의 근거다.

실행 조건은 **Linux, Node.js 22 이상, CPython 3.11 이상**과 선택한 매니페스트에 필요한 외부 컴파일러·링커·해제 도구다. UCI 합법 수 검사를 위한 `chess==1.11.2`는 선택적인 개발용 의존성이다. 실제 수행 환경은 Linux x64, Node 24.19.0, npm 11.9.0, CPython 3.12.14였다. Node 22/24 CI 구성은 작성했으나 원격 CI를 실행한 결과는 아니다.

NVCompact는 빌드 도구다. 이 npm 래퍼를 엔진의 경기 중 탐색 경로에 넣지 않으며, npm 패키지 크기는 TCEC 제출 파일 크기와 별개다. `--jobs`는 압축 도구의 작업자 수다. 엔진 자체의 탐색 스레드 수나 many-core 성능을 뜻하지 않는다.

### 명령 전달과 작업 수명

`NVCOMPACT_PYTHON`은 하나의 실행 파일 이름 또는 경로다. 공백과 셸 문자가 있는 경로도 그대로 전달하며 셸 명령 문자열로 해석하지 않는다. 현재 디렉터리, 인자, 표준 입출력과 실제 하위 프로세스 종료 코드를 유지한다. Python이 없거나 지정 경로가 잘못되면 실패를 반환한다.

추가한 Python 런처는 SIGINT/SIGTERM을 받으면 소유한 하위 프로세스 그룹과 알려진 중첩 Python helper를 정리하고, 대기 작업을 취소하며 실행 중인 작업의 종료를 기다린다. 정리가 끝나지 않으면 incomplete 상태를 기록한다. 임의의 외부 helper가 별도의 세션을 만들어 분리한 자식은 그 helper가 수명을 관리해야 한다. SIGKILL·호스트 종료에는 일반적인 정리 절차를 보장할 수 없다.

`engines`는 명시적인 기존 `--manifests` 경로와 비어 있지 않은 입력 집합을 요구한다. 없는 경로, 빈 집합과 알 수 없는 `--only` 선택은 실행 전에 거절한다. 이는 새 CLI 경계에서 적용한 검사이며 원본 runner 파일의 바이트를 변경한 것은 아니다.

코어 recipe의 해시만으로 새 런처까지 특정할 수 없으므로 실행 시 npm tarball 해시와 `doctor --json` 결과를 함께 보존하도록 문서화했다.

## 5. 바로 실행하기

### 다른 프로젝트에 로컬 npm 패키지 설치

제공한 `nvcompact-0.2.0.tgz`를 프로젝트 디렉터리에 둔다.

```sh
npm install --save-dev ./nvcompact-0.2.0.tgz --ignore-scripts --no-audit --no-fund
npm exec -- nvcompact --version
npm exec -- nvcompact doctor --json > nvcompact-runtime.json
```

다음은 C++ 표기 후보를 생성하는 예시다. `engine.cpp`는 실제 입력 파일로 바꾼다. `no-token-observation`은 소스 문자열화·토큰 붙이기 등 토큰 관측이 없다는 실제 입력 계약에 맞게 선택해야 한다.

```sh
npm exec -- nvcompact notation engine.cpp \
  --language cpp --target cpp17-lp64 \
  --token-contract no-token-observation --compact \
  --portfolio runs/spellings-01
```

번들 C/Rust 예제는 `cc`, `ld`, `rustc`, `python3`을 설치한 환경에서 실행한다.

```sh
npm exec -- nvcompact run \
  node_modules/nvcompact/examples/mixed/manifest-notation.json \
  --out runs/mixed-01 --jobs 2
```

### 모노레포 개발·검증

압축을 푼 뒤 `nvcompact-monorepo/`에서 실행한다. 아래 `.deps` 설치에는 패키지 다운로드가 필요하다.

```sh
npm ci --ignore-scripts --offline --no-audit --no-fund
python3 -m pip install --target .deps chess==1.11.2
NVUCI_ORACLE_PATH="$PWD/.deps" npm test
NVUCI_ORACLE_PATH="$PWD/.deps" npm run test:core
npm run check
npm run pack:cli
npm run verify:package
```

UCI oracle 없이 `npm test`만 실행하면 UCI 취소 검사 3개를 skipped로 보고한다. 이번 최종 실행은 oracle을 지정해 **11개 모두 실행**했다.

`pack:cli`의 결과는 `dist/nvcompact-0.2.0.tgz`이며 `dist/pack.json`에 실제 파일 목록·크기·해시를 남긴다. `verify:package`는 실제 tarball을 별도 소비자 디렉터리에 오프라인으로 설치하고 CLI와 예제를 실행한다.

현재 이름을 레지스트리에 게시한 상태는 아니므로 제공한 로컬 `.tgz`를 사용한다.

## 6. 실제 검사 결과

| 검사 | 이번 결과 | 입증 범위 |
|---|---|---|
| 기존 Python 검사 | **55/55 통과, skip 0** | 코어를 옮긴 환경에서 기존 회귀 검사 통과 |
| CLI·패키지 검사 | **11/11 통과, skip 0** | 명령 전달·실패 보존·실제 UCI 취소·worker 정리·tarball 포함 범위 |
| 별도 프로젝트 설치 | **통과** | 실제 최종 `.tgz`의 오프라인 설치와 실행 |
| Python 표기 압축 예제 | **64 → 35바이트** | 원본·변환본을 실행한 출력 일치, 경로·인자 보존 |
| 설치된 네이티브 예제 | **C 링크 조합 4개, 전체 파일 8개 비교** | 번들 예제·링커·검사 경로가 workspace 외부에서 동작 |
| 선택한 예제 파일 | **520바이트** | 22개 검사 사례, 유효 레코드 199,360개 검증 |
| 독립 재현 | **동일 SHA256** | 새 디렉터리에서 빌드한 520바이트 파일과 full oracle 결과 일치 |
| 설치 내용 보존 | **32개 파일 그대로** | 실행 전후 바이트·권한 일치, 패키지 내부에 캐시·결과물 추가 없음 |

네이티브 설치 검증은 함께 제공한 C/Rust 예제에서 Rust 후보·도구·입력만 제거한 **C 전용 검증 시나리오**다. 배포 예제 자체에는 원본 Rust 입력도 유지했다. 520바이트는 이 정수 커널 예제의 결과다. 새로운 체스 엔진 크기나 기력 결과가 아니다.

최종 npm tarball은 **73,802바이트**, 펼친 파일 합계 **263,837바이트**, **32개 파일**이다.

```text
SHA256(nvcompact-0.2.0.tgz)
3a15d37f5cb37bcc7118e4a5401e172aeb67c531909514d927d2b8f6dcc9aaef

SHA256(520-byte example)
ad772ca3724d250668c7dbfad8b24e67f780dc8cae3a6221c8643b4d164c23dd

SHA256(Python launch adapter)
0fe4fd0aeb21abaceba94587ab69e8625c73d7d3d3026c373b4abc1387001b08
```

자세한 명령·기록은 `evidence/package-validation.json`과 그 파일이 가리키는 실제 실행 로그, `evidence/cli-validation.json`, `evidence/core-validation.json`에 있다. 제공한 `NVCompact-Npm-Checks.json`은 이 결과를 한곳에 묶는다.

기존 11개 엔진 캠페인은 이번 패키징에서 새로 실행하지 않았다. 이전 입력·결과·출처는 보존했고, 전체 과거 실험 로그와 원래 배포물은 앞서 제공한 `nvcompact-v02.zip`에 있다. 새 런처에 대해서는 위 검사와 설치된 예제의 독립 재현을 수행했다. 전체 엔진에 대한 새 UCI·기력·많은 코어 성능 검증으로 해석하지 않는다.

## 7. 공개 배포 준비 상태

이번에 로컬 모노레포, lockfile, npm CLI tarball, 구성·검사·pack 스크립트, 설치 검증, CI 설정과 배포 안내를 만들었다. 원격 GitHub 저장소 생성이나 npm 게시 명령은 실행하지 않았다.

기존 NVCompact에는 자체 프로젝트의 공개 라이선스가 없었다. 현재 자체 패키지는 `private: true`, `license: UNLICENSED`로 기록했다. 자체 도구의 공개 라이선스로 **MIT를 제안**하며 아직 적용한 상태는 아니다. CTK3의 공개 메타데이터에 MIT가 있다는 이유로 이 프로젝트에 같은 권리를 자동 부여하지 않는다. 외부 엔진의 원래 라이선스는 해당 입력·대응 소스에 유지한다.

이 상태에서도 로컬 npm tarball 생성·설치·실행은 완료했다. 향후 공개 배포 때 확정한 소유자·저장소 URL·패키지 이름 또는 scope·자체 라이선스를 실제 메타데이터에 반영하고, 바뀐 tarball을 다시 검사할 수 있도록 `docs/RELEASING.md`에 정리했다.

## 8. 제공 파일

| 파일 | 내용 |
|---|---|
| `nvcompact-monorepo-0.2.0.zip` | 모노레포 전체 코드·예제·실험 입력·대응 소스·검사 근거와 외부 핸드오프 |
| `nvcompact-0.2.0.tgz` | 다른 프로젝트에서 직접 설치할 수 있는 실제 npm 패키지 |
| `NVCompact-Monorepo-Npm-Guide.ko.md` | 이 안내 문서 |
| `NVCompact-Npm-Checks.json` | 전달 파일 해시, 패키징·설치·실행·재현 결과와 검사 범위 |

전체 zip의 두 형제 디렉터리를 함께 두면 공통 규약에서 외부 핸드오프를 가리키는 경로가 유지된다. 생성 캐시와 `node_modules`는 제외했다. 설치 tarball과 모노레포의 tarball은 같은 바이트다.
