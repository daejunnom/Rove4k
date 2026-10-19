# 저장소와 개발 자료의 수명주기

이 문서는 Rove4k와 내부 NVCompact의 기여·공유·worktree·생성물 운영을 규정한다.
탐색·압축 알고리즘, 엔진의 코드 배치나 제출 파일에 관리 기능을 추가하지 않는다.
구현 선택은 [공통 엔지니어링 계약](ENGINEERING-CONTRACT.md)과 도구의 별도 규약을 따른다.

## 1. 최신 기준을 선택한 근거

2026-10-19에 두 저장소의 실제 develop과 최근 PR의 head, 변경 파일과 규약 blob을 대조했다.
기본 브랜치의 오래된 문서만 읽거나 가장 최근 제품 커밋을 가장 최근 규약으로 가정하지 않았다.

| 자료 | 확인한 기준 | 적용한 내용 |
|---|---|---|
| Rovent develop | `609819ded605795c9ff0653adad391e875b1c4b2` | feature PR, 작은 WIP 공유, 소유권·종료·보존 구분, 공통 검증·CI 격리 |
| Rovent 최신 구현 PR #27 | `a41bc05ffa886d6f67b3289e71e027aa718c58a3`, open Draft | 관련 규약의 최신성 대조. AGENTS·CONTRIBUTING·ENGINEERING·TESTING·PR template의 blob이 위 develop과 모두 동일 |
| MMMM 최신 구현 PR #1 | `79448abf8b8eaa7c86cb3840d6397d7410bff5b3`, open Draft | 최신 AGENTS·기여 절차·실제 빌드 관리 코드와 수명 문서. develop에 병합된 것으로 간주하지 않음 |
| MMMM 규약 보완 PR #2 | `8720d0724a34a27db746d6ed131a9966c0579aac`, open·미병합 | 구현 PR에 없는 최신 검증·테스트 판정 보완. 관련 원칙을 이 저장소에 명시적으로 채택 |

Rovent의 검증 보완 PR #26은 develop에 통합돼 있다. MMMM의 PR #2는 기여 절차와 기존
구현 규약을 그대로 두고 테스트 보완 문서와 PR template 참조를 추가한 별도 제안이다.
MMMM의 main/develop `e9fb5616673fc214d7c242a068e68a7f5d9397b8`만 기준으로 삼으면
진행 중인 관리 구현과 별도 보완을 놓치므로 둘을 나누어 읽었다.

고정 원문:

- Rovent [AGENTS](https://github.com/daejunnom/Rovent/blob/609819ded605795c9ff0653adad391e875b1c4b2/AGENTS.md),
  [CONTRIBUTING](https://github.com/daejunnom/Rovent/blob/609819ded605795c9ff0653adad391e875b1c4b2/CONTRIBUTING.md),
  [ENGINEERING-STANDARDS](https://github.com/daejunnom/Rovent/blob/609819ded605795c9ff0653adad391e875b1c4b2/docs/ENGINEERING-STANDARDS.md),
  [TESTING-STANDARDS](https://github.com/daejunnom/Rovent/blob/609819ded605795c9ff0653adad391e875b1c4b2/docs/TESTING-STANDARDS.md),
  [관리 실행 접점](https://github.com/daejunnom/Rovent/blob/609819ded605795c9ff0653adad391e875b1c4b2/scripts/run_managed.py),
  [PR #27](https://github.com/daejunnom/Rovent/pull/27).
- MMMM [AGENTS](https://github.com/daejunnom/MMMM/blob/79448abf8b8eaa7c86cb3840d6397d7410bff5b3/AGENTS.md),
  [CONTRIBUTING](https://github.com/daejunnom/MMMM/blob/79448abf8b8eaa7c86cb3840d6397d7410bff5b3/CONTRIBUTING.md),
  [build-system](https://github.com/daejunnom/MMMM/blob/79448abf8b8eaa7c86cb3840d6397d7410bff5b3/docs/build-system.md),
  [실제 storage 관리 구현](https://github.com/daejunnom/MMMM/blob/79448abf8b8eaa7c86cb3840d6397d7410bff5b3/tools/mmmm-xtask/src/storage.rs),
  [PR #1](https://github.com/daejunnom/MMMM/pull/1),
  [PR #2 TESTING-STANDARDS](https://github.com/daejunnom/MMMM/blob/8720d0724a34a27db746d6ed131a9966c0579aac/docs/TESTING-STANDARDS.md).

공통 운영 원칙을 가져왔으며 다른 프로젝트의 A~F 역할, 게임·신경망·DB 계약, 고정
빌드 슬롯 개수·GiB 한도·운영체제별 경로와 대형 supervisor 구현은 복제하지 않았다.
필요한 관리 기능은 이 저장소의 실제 도구와 위험에 맞게 아래 접점으로 구현한다.

## 2. 기여 수명

일반 흐름은 최신 `develop`에서 목표별 `feature/*`를 만들고 같은 목표의 Draft PR을
`develop`에 제출하는 것이다. 안정 승격과 hotfix 경로는 [CONTRIBUTING](../CONTRIBUTING.md)에 둔다.

작업 재개 시 실제 PR의 open/draft/merged/closed 상태, head/base SHA, 변경 소비자와
관련 검사를 읽고 로컬 branch·worktree·diff와 대조한다. 같은 목표를 이어가는 동안은
기존 branch와 PR을 재사용한다. PR이 없거나 원격 읽기가 실패한 상태를 성공으로 보고하지 않는다.
읽기 전용 조사와 독립 구현은 가능한 범위에서 계속한다.

원격 공유가 배정 범위이면 작은 의미 단위를 공유하며 장기 변경은 15~30분마다 확인한다.
WIP는 알려진 실패와 미실행을 포함할 수 있다. 통합에는 현재 주장과 영향에 맞는 실제
검사와 리뷰를 확보한다. 전체 무거운 캠페인이나 모든 플랫폼 검사를 매 중간 push마다
반복하지 않는다. 공유한 이력 수정은 후속 커밋을 사용한다.

## 3. 관리 명령

Node 22 이상과 Git을 사용한다. 관리 CLI는 런타임 npm 패키지나 제출 엔진에 포함되지 않는다.
출력은 현재 관측을 담은 JSON이며, 계정의 개인 절대 경로를 포함할 수 있으므로 PR에는
필요한 상대 경로·SHA·결과만 옮긴다. 출력물을 의무적으로 저장하거나 새 증거 등록부를
만들 필요는 없다.

| 명령 | 실제 동작 |
|---|---|
| `status` | 현재 SHA·branch·upstream·worktree와 staged/unstaged/untracked/ignored 상태를 읽는다 |
| `start` | 현재 원격 base와 로컬 tracking object를 대조하고 새 worktree 계획을 낸다 |
| `start --execute --expected-base SHA` | 확인한 같은 base에서 새 branch·locked worktree·소유 기록을 생성한다 |
| `share-plan` | stage된 경로와 WIP 상태를 읽는다. `--remote-check`로 실제 tip을 확인하면 명시적 대상 ref의 push argv를 제안한다 |
| `cleanup-plan` | 소유 기록·worktree·변경·원격 보존을 확인하고 정리 차단 이유를 낸다. 삭제하지 않는다 |
| `storage` | 명시한 외부 루트의 논리 파일 길이를 유한하게 열거하고 예산과 비교한다. 삭제하지 않는다 |
| `pr-check` | 실제 head/base 조합이 feature 통합·안정 승격·hotfix 경로인지 확인한다 |

일반 상태와 WIP 공유 확인:

```sh
npm run repo -- status --remote-check
npm run repo -- share-plan --remote-check
```

`--remote-check`는 `git ls-remote`로 읽으며 fetch·commit·push하지 않는다. 생략하면 원격
보존을 미관측으로 표시한다. stale tracking ref가 성공 근거가 되지 않게 한다. 공유 계획은
현재 branch의 명시적 ref를 사용하므로 잘못 설정된 `origin/main` upstream을 따르지 않는다.
stage된 내용과 소유 범위를 검토해 커밋한 뒤 계획을 새로 확인하고 제시된 argv에 따라
공유한다. push는 stage만 한 파일이 아니라 커밋된 HEAD를 전송한다.

새 격리 작업 예:

```sh
git fetch origin
npm run repo -- start --branch feature/elf-layout \
  --worktree /absolute/external/rove4k-elf-layout --owner elf-layout

npm run repo -- start --branch feature/elf-layout \
  --worktree /absolute/external/rove4k-elf-layout --owner elf-layout \
  --execute --expected-base REVIEWED_BASE_SHA
```

`REVIEWED_BASE_SHA`는 바로 앞 계획의 `base_sha`다. 일반 feature와 release는 원격
develop, hotfix는 원격 main을 사용한다. 대상 parent는 이미 존재하는 실제 절대 경로여야
하며 link/junction, 기존 디렉터리, 다른 worktree 내부·상위 경로, 기존 로컬/원격 branch는
자동 채택하지 않는다. 기존 checkout과 미커밋 작업은 변경하지 않는다.

생성 시 Git common directory의 `rove4k-worktrees/`에 branch digest별 작은 소유 기록을
독점 생성하고 Git의 worktree lock도 남긴다. 기록의 `reserved`는 생성 중단일 수 있다.
정상 생성 후에만 `created`로 바꾸며, 실패·중단한 기록과 경로는 자동으로 회수하거나
새 owner에게 인계하지 않는다. 이 기록은 협력 작업의 소유 정보이며 프로세스 lease나
OS 접근 제어의 증명이 아니다. 저장소의 신뢰한 Git 설정을 사용하는 관리 도구이며
적대적으로 동시에 바뀌는 파일 시스템을 격리하는 sandbox가 아니다.

## 4. worktree 정리와 자료 보존

```sh
npm run repo -- cleanup-plan --branch feature/elf-layout \
  --owner elf-layout --remote-check
```

정리 계획에는 다음이 독립적으로 나타난다.

- 소유 기록과 요청 owner의 일치, 미완료 예약 여부.
- 현재 연결된 worktree, 현재 checkout, 미커밋·미추적·ignored 자료.
- 새로 읽은 원격의 동일 tip 또는 같은 SHA를 포함하는 통합 이력.
- 프로세스의 물리적 사용과 다른 열린 PR 사용은 자동 관측하지 않았다는 사실.

물리적 비활성은 언제나 owner의 별도 확인이 필요하다. PID가 안 보이거나 시간이 지났다는
사실만으로 다른 namespace·컨테이너·호스트의 실행이 끝났다고 결론내리지 않는다.
작업이 끝나고 필요한 자료를 보존한 자신의 worktree에 한해 담당자가 lock을 해제하고
일반 `git worktree remove`를 사용할 수 있다. branch 정리는 `git branch -d`만 사용한다.
squash/rebase 병합으로 Git의 안전 삭제가 거절되면 보존하고 이유를 설명한다. 이 CLI는
자동 unlock·remove·prune·reset·강제 삭제·원격 삭제를 제공하지 않는다.

Git ignored 자료도 원시 비교 입력이나 실패 근거일 수 있다. `.gitignore`에 들어 있다는
이유로 폐기하지 않는다. 원격 branch tip만 보존했다고 미추적 파일이나 아직 열린 descriptor의
사용 수명까지 보존된 것으로 판단하지 않는다. 파일 unlink와 실제 디스크 반환도 구분한다.

## 5. 빌드·압축·실행 자료의 수명

| 분류 | 위치와 보존 원칙 |
|---|---|
| 정본 소스·자체 작은 예제·문서 | 저장소. Git으로 관리한다 |
| compiler target·코덱 cache·중간 복원 | 저장소 밖의 명시한 checkout/OS/대상별 고정 루트. 재생성 자료로 관리한다 |
| 외부 비교 엔진 입력 | 저장소 밖. 원본·해시·라이선스와 실제 선택 profile을 보존하며 벤더링하지 않는다 |
| 실행 stdout/stderr·실패·재현 근거 | 외부 보존 루트. 판단에 필요한 근거는 선택해 보존하고 검토 요약만 Git에 넣는다 |
| 제출 파일·npm tarball·recipe | 배포/인수 근거. 일반 cache 정리와 분리하고 해당 source·도구·SHA와 함께 보존한다 |

작업 전에 실제 CPU·memory·worker·time·output 범위와 정리 담당을 선택한다. checkout과
대상이 같은 재생성 cache는 기존 고정 루트에서 도구의 입력 검증으로 재사용할 수 있다.
PID·시간·SHA마다 무제한 새 빌드 트리를 만드는 것을 기본값으로 삼지 않는다. 후보와
독립 replay의 분리는 필요한 의미 단위로 유지하고 이전 실패를 덮어쓰지 않는다.

```sh
npm run repo -- storage --root /absolute/external/rove4k-artifacts \
  --budget-bytes 12884901888
```

위 12GiB는 명령 사용 예이며 저장소의 고정 예산이 아니다. `storage`는 기본 최대
100,000 entry를 열거하고 상위 경로별 논리 길이를 집계한다. 필요하면 `--max-entries`를
명시한다. 열거가 중단되거나 일부 항목을 관측하지 못하면 `complete=false`와
`within_budget=null`로 표시한다. symlink 대상은 따라가지 않고 별도로 센다. 이 결과는
디스크 quota·RSS·물리 할당량·예약·비활성 증거가 아니다.

빌드 전과 보존·종료 뒤 관측을 비교하고 실제 자원이 필요한 캠페인은 NVCompact의
기존 자원 계획/명시적 실행 경로를 사용한다. 이 CLI는 다른 프로젝트의 supervisor를
복제하거나 engine worker를 강제 축소하지 않는다. 자식 종료·출력 완료·필요 자료 내보내기
확인 후 자신의 재생성 파일만 기존 실행 도구의 소유 범위에서 회수한다. 취소·OOM·종료 불명은
원인과 자료를 남기고, 정리 성공으로 원래 실패를 성공으로 바꾸지 않는다.

## 6. CI와 원격 운영

상시 `Repository lifecycle` workflow는 PR route와 실제 임시 Git 저장소의 worktree,
WIP 대상 ref, 미공유 자료 보존을 검사한다. 문서만 바뀐 PR에도 발생한다. 검증을 통과해도
GitHub branch protection이 자동 설정되거나 병합 권한이 생기지 않는다.

NVCompact의 코드·패키지 검사는 별도 workflow에서 수행하고 원시 엔진 캠페인은
로컬/전용 서버에서 명시적으로 시작한다. 빌드 산출물과 npm 게시도 별도 수명이다.
배포 job만 필요한 OIDC 권한과 environment를 가지며 PR의 임의 산출물을 그대로
높은 권한으로 승격하지 않는다. cache hit·pack 성공·dispatch·실제 npm 게시를 구분한다.

임시 조사 workflow가 필요하면 기존 관련 PR/run과 겹치지 않게 목적·담당·종료 조건,
유한 실행·자원·보존 범위를 정한다. 같은 목표의 반복은 기존 workflow/run 흐름을 재사용한다.
종료 후 필요한 실패·인수 근거를 보존하고 workflow 제거는 PR로 처리한다. workflow 파일,
run, 로그와 artifact는 서로 다른 자료다. 열린 PR의 필수 근거·미해결 실패·릴리스 원본을
나이·개수만으로 삭제하지 않는다. 원격 보존/삭제는 실제 권한과 대상에 따라 수행한다.

## 7. 이번 관리 코드의 확인 범위

`npm run test:repo`는 외부 네트워크 없이 소유한 임시 bare remote와 Git worktree를 만들어
핵심 상태 전이를 확인한다. stale 원격 base, 기존/보호 branch, 잘못된 upstream,
ignored·untracked 자료, 다른 owner, 링크 경계와 유한 저장소 관측을 실제로 다룬다.
검사 수나 특정 문구의 존재를 합격 조건으로 고정하지 않는다.

이 검사는 GitHub 원격 보호 설정, 사람 리뷰, OS의 모든 process namespace,
대형 엔진 실행 또는 npm 게시를 인수하지 않는다. 그 상태는 해당 작업에서 직접 관측한다.
