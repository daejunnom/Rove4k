> 이전 준비 단계의 기록입니다. 2026-10-19에 사용자가 **Rove4k**와 **NVCompact** 저장소를 생성하고 MIT 라이선스를 선택했습니다. 현재 상태는 루트 README와 LICENSE-STATUS.md를 따릅니다.

# NVCompact 모노레포·npm 패키징 결정

## 목적과 현재 상태

NVCompact 0.2의 Python 구현을 보존하면서 npm으로 설치·실행할 수 있는 개발 도구를 준비한다. 새 JavaScript 구현으로 알고리즘을 다시 옮기는 작업은 이번 패키징의 범위가 아니다. 패키지 버전은 기존 도구와 같은 `0.2.0`이며, 배포 준비와 알고리즘 개선의 근거를 구분한다.

현재 작업은 로컬 모노레포, npm tarball, 실행·설치 검증과 문서 준비를 대상으로 한다. 원격 GitHub 저장소 생성과 npm 레지스트리 게시를 완료했다고 뜻하지 않는다. 이번에 새 Rook4k 엔진을 구현한 것도 아니다.

## 저장소와 workspace 경계

| 위치 | 패키지 이름 | 책임 | 현재 게시 설정 |
|---|---|---|---|
| 루트 | `nvcompact-monorepo` | 공통 규약, 작업공간, 설치 잠금 파일, 검증·패키징 명령 | `private: true` |
| `packages/nvcompact` | `nvcompact` | Node CLI 진입점, Python 도구, 작은 예제·링커 스크립트·프로필 | `private: true` |
| `packages/tcec4k-lab` | `nvcompact-tcec4k-lab` | 검토한 엔진 매니페스트, 원본 입력, 대응 소스·라이선스, 출처 자료 | `private: true` |
| 저장소 바깥의 핸드오프 | npm 패키지 아님 | 이전 조사·상세 설계·판단 이력 | 게시 대상 아님 |

루트의 `workspaces`에 두 패키지를 명시한다. 실험 workspace는 `nvcompact: "0.2.0"` 의존성을 선언한다. npm workspaces는 루트에서 설치할 때 일치하는 로컬 패키지를 연결하므로, 개발 중 레지스트리에 먼저 게시할 필요가 없다. 자세한 동작은 [npm workspaces 공식 문서](https://docs.npmjs.com/cli/v11/using-npm/workspaces/)에 근거한다.

이 구성은 책임과 배포 경계를 표현한다. 작업을 위해 모든 Python 모듈을 별도 npm 패키지로 쪼개거나 Nx·Turborepo 같은 프레임워크를 도입하지 않는다. 패키지 경계나 파일 구조는 영구 규약이 아니므로, 이후 검증된 개선에 따라 바꿀 수 있다.

## npm CLI와 Python 구현의 관계

| 계층 | 역할 | 설치·실행 조건 |
|---|---|---|
| Node CLI | 사용자 명령을 해당 Python 도구로 연결하는 배포 진입점 | Node.js 22 이상, 현재 지원 플랫폼 Linux |
| Python 구현 | 표기 변환, 빌드·링크 포트폴리오, 압축, UCI 검사, 재현, 엔진 캠페인 | CPython 3.11 이상 |
| 대상 도구 체인 | 선택한 입력을 컴파일·링크·해제·실행 | 선택한 엔진·매니페스트에 따라 외부 도구 필요 |
| UCI oracle | 선택적으로 합법 수와 프로토콜 결과를 검사 | 개발용 Python 의존성; 제출 엔진에 포함하지 않음 |

배포 패키지의 런타임 npm 의존성은 0개다. 이것은 “외부 실행 환경이 필요 없다”는 뜻이 아니다. Python, 컴파일러, 링커, 코덱 명령, 엔진별 런타임은 여전히 필요하다. 현재 패키지의 `os`는 Linux로 제한하며, 다른 플랫폼 지원은 실제 동작을 확인한 후 추가한다.

Python 구현 8개는 `packages/nvcompact/python/`에 배치한다. 이미 확인한 압축 알고리즘을 유지한 상태에서 명령 실행과 패키징 경계만 추가하면, 언어 이식에 따른 새 의미 차이를 만들지 않고 npm 소비 경로를 검증할 수 있다. 향후 Python 런타임을 제거하는 변경은 구현·성능·호환성을 함께 평가하는 별도 결정이다.

Node CLI를 엔진의 경기 중 실행 경로에 넣지 않는다. 향후 Rook4k는 NVCompact를 개발·빌드 도구로 사용하고, 실제 TCEC 제출 파일은 해당 규정에 맞는 독립 산출물로 만든다. npm tarball의 크기와 4,096바이트 엔진 제출 제한은 서로 다른 측정 대상이다.

## npm 패키지에 넣는 범위

`packages/nvcompact/package.json`의 `files` 목록으로 CLI, Python 구현, 작은 예제, 링커 스크립트, 프로필과 사용자 안내를 선택한다. 대형 엔진 원본·제3자 대응 소스 묶음·캠페인 기록은 별도 workspace와 전체 작업 자료에 보존한다.

소비자는 일반 도구 설치만으로 모든 역사적 엔진과 실험 기록까지 받지 않아도 된다. 실험 자료를 다시 실행할 때는 모노레포와 입력을 함께 사용한다. 이는 파일을 삭제하거나 실험 근거를 폐기하는 결정이 아니다.

`files`, 실행 파일 연결을 위한 `bin`, `private`의 의미는 [npm package.json 공식 문서](https://docs.npmjs.com/cli/v11/configuring-npm/package-json/)를 따른다. `files` 목록만 보고 배포 파일 구성을 추정하지 않고 실제 `npm pack`의 목록과 tarball을 검사한다.

## 로컬 tarball과 검증

`npm pack`은 패키지 tarball을 생성하는 명령이다. 레지스트리에 게시하지 않고 실제 배포 형태를 만들고 검사할 수 있다. workspace 선택과 `--dry-run`, `--json`, `--pack-destination` 옵션은 [npm pack 공식 문서](https://docs.npmjs.com/cli/v11/commands/npm-pack/)에 설명되어 있다.

준비한 루트 명령은 다음 책임을 가진다. 실제 수행 결과와 해시는 해당 검증 기록을 따른다.

| 명령 | 목적 |
|---|---|
| `npm test` | npm 진입점과 패키징 경계의 동작 검사 |
| `npm run test:core` | 기존 Python 검사를 옮긴 환경에서 실행 |
| `npm run check` | 패키지 구성과 필요한 입력 경로 점검 |
| `npm run pack:cli` | CLI workspace의 실제 npm tarball 생성 |
| `npm run verify:package` | tarball을 격리된 소비 환경에서 설치·실행하여 workspace 외부 소비 확인 |

개발 폴더에서 실행되는 것만으로 패키지가 완성됐다고 판정하지 않는다. 실제 tarball 설치 후 패키지에 포함된 Python 모듈, 예제와 링커 경로를 사용할 수 있어야 한다. 반대로 tarball 설치 성공이 모든 외부 컴파일러·엔진이나 TCEC 출전 조건을 입증하지는 않는다.

오류가 발생하면 소스·상대 경로·명령 전달·패키지 포함 범위 등 원인 로직을 수정한다. 누락된 파일을 사용자의 임의 작업 디렉터리에서만 찾게 하거나, 실패한 빌드의 기대값을 바꾸는 식으로 성공 상태를 만들지 않는다.

## 버전·이름·라이선스의 준비 상태

표시 이름은 `NVCompact`, npm 이름 후보는 `nvcompact`다. 이번에 약어를 **N-Versions Compaction**으로 정의했으며, 이름과 엔진 이름 후보의 상세 판단은 [이름 제안](NAMING.ko.md)에 있다.

2026-10-19 **11:45 KST / 02:45 UTC** 공개 API 조회에서 npm `nvcompact`와 GitHub `daejunnom/Rook4k`, `daejunnom/Rove4k`, `daejunnom/NVCompact` 엔드포인트는 모두 HTTP 404를 반환했다. 이는 해당 공개 조회에서 메타데이터를 받지 못했다는 관측이며, 이름 확보나 게시 권한의 확인이 아니다. GitHub 비공개 저장소의 존재 여부도 알 수 없다. URL·응답·시각은 [이름 조회 기록](../evidence/name-availability.json)에 보존했다.

같은 조회에서 npm `ctk3`는 HTTP 200을 반환했고, 공개 메타데이터의 `latest`는 `0.1.1`, 라이선스 표기는 `MIT`, 저장소는 `daejunnom/Clearra`의 `packages/ctk3`였다. 이는 CTK3의 공개 패키지 배치와 메타데이터에 관한 관측이다. 이 정보를 NVCompact의 라이선스·소유 권한이나 이번 도구의 게시 승인으로 상속하지 않는다.

현재 자체 도구의 공개 라이선스가 사용자 선택으로 확정되지 않았으므로 루트와 자체 패키지에는 `UNLICENSED`를 기록하고 `private: true`를 유지한다. 이것은 제3자 엔진의 원래 라이선스를 변경하지 않는다. 실험 입력과 대응 소스는 각각 보존한 원래 라이선스와 출처를 따른다.

공개 배포를 위한 자체 도구 라이선스로 MIT를 검토할 수 있으나, 이는 제안이며 이미 권리를 부여한 상태가 아니다. 원격 소유자, npm 이름 또는 scope, 공개 라이선스와 게시 대상이 확정되면 그 구체적인 값으로 패키지 메타데이터를 갱신한다. 실험 workspace와 루트는 공개 CLI와 독립적으로 `private` 상태를 유지할 수 있다.

`private: true`는 npm 게시를 차단하지만 로컬 tarball 준비·설치 검증의 목적과 충돌하지 않는다. 이 설정은 아직 요청되지 않은 원격 게시를 완료한 것처럼 취급하지 않기 위한 현재 상태이며, 구현 검증을 멈추는 이유가 아니다.

## 이후에 달라질 수 있는 선택

| 선택 | 현재 판단 | 다시 검토할 근거 |
|---|---|---|
| Python 구현 + Node CLI | 기존 의미·재현 근거를 보존하면서 npm 소비 경로를 제공 | 런타임 설치 비용이나 실제 성능 문제가 확인될 때 |
| 단일 공개 CLI 패키지 | 설치·버전 조합을 단순하게 유지 | 독립 소비자와 독립 배포 주기가 생길 때 |
| private 실험 workspace | 범용 도구와 역사적 실험 입력을 각각 보존 | 재사용 요구와 라이선스·입력 배포 범위를 구체화할 때 |
| npm workspaces | 현재 두 workspace에 필요한 로컬 연결과 명령 실행 제공 | 실제 빌드 그래프·캐시·스케줄링 문제가 생길 때 |
| Rook4k 별도 엔진 저장소 | 범용 도구의 소비자로 자체 엔진을 개발 | 공유 변경의 빈도와 소유 범위에 관한 새 근거가 생길 때 |

이 문서의 구조와 선택은 현재 구현을 설명하는 결정 기록이다. [AGENTS.md](../AGENTS.md)와 [공통 엔지니어링 계약](ENGINEERING-CONTRACT.md)이 보장하는 설계 자유를 축소하는 영구 규칙으로 사용하지 않는다.
