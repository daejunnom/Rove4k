# nvcompact npm 배포

공개 패키지 이름과 실행 명령은 모두 **`nvcompact`**다. 소스는 Rove4k의 내부
도구로 관리하며, npm 공개 단위만 별도로 둔다. 루트 workspace는 계속 private다.

2026-10-19 공개 registry의 `GET https://registry.npmjs.org/nvcompact`는 HTTP 404,
`{"error":"Not found"}`를 반환했다. 당시 등록된 패키지는 없었다. 조회로 이름을
예약하지는 못하며 실제 최초 게시가 최종 이름 확보 단계다. npm 계정 소유권이나
인증 상태는 공개 조회로 확정하지 않는다. 이 변경은 이름 설정과 배포 경로 준비이며,
실제 npm 게시·로그인·trusted publisher 설정은 수행하지 않았다.

관측 근거는 [이름 조회](../evidence/0.5/npm-name.json)와
[로컬 포장·실제 설치 검증](../evidence/0.5/release-preparation.json)에 둔다.
작업 중 생성한 검증용 bundle과 검토한 clean main에서 게시할 bundle은 구분한다.

## 설정과 지원 대상

[`release-config.json`](../scripts/release-config.json)이 게시자와 배포 대상을 둔다.
이 값은 런타임 알고리즘에 포함되지 않는다. 다른 계정으로 이관할 때는 이 설정,
package.json의 registry/repository와 실제 npm 소유권·trusted publisher 설정을
함께 변경한다. 설정 파일만 바꾸어 npm 권한이 이전되지는 않는다.

| 항목 | 현재 값 |
| --- | --- |
| 패키지 | `nvcompact` |
| npm 개인 계정 | `daejunnom` |
| Registry | `https://registry.npmjs.org/` |
| 배포 저장소 / 브랜치 | `daejunnom/Rove4k` / `main` |
| Workflow 파일 | `nvcompact-publish.yml` |
| GitHub environment | `npm-release` |
| npm CLI | `12.2.0` |
| npm dist-tag | `latest` |
| Native target | `x86_64-unknown-linux-gnu`, Linux x64/glibc |

공개 바이너리는 Ubuntu 24.04의 glibc 환경에서 빌드·설치 검사한다. 지원 기준은
glibc 2.39 이상, zlib와 GCC 런타임이다. 설치 시 Rust를 다운로드하거나 컴파일하지
않는다. Windows/macOS/ARM/musl 지원을 선언하지 않는다. 외부 엔진·개발 source·과거
Python은 npm tarball에 넣지 않는다.

## 최초 게시: 개인 계정으로 한 번 업로드

검토한 변경이 `main`에 통합된 clean checkout에서 준비한다. 준비와 업로드는
분리되어 있으며 `publish:nvcompact`는 포장이나 재빌드를 하지 않는다.
이 저장소의 준비·게시 스크립트는 **Linux에서 실행**한다. Linux x64 환경이 없는
로컬에서는 아래 GitHub `prepare` 작업으로 tarball을 만들고 플랫폼 중립 수동 업로드
경로를 사용한다. Windows에서 Linux native 바이너리를 실행하도록 요구하지 않는다.

```sh
npm run release:prepare
npm run publish:nvcompact
```

첫 명령은 현재 Rust source를 빌드하고 전체 tarball을 포장한 뒤, 별도 consumer에
실제로 설치해 기존 CLI/native 검사를 수행한다. 결과는 저장소 밖의 새 디렉터리에
`nvcompact-0.4.0.tgz`와 `release.json`으로 남는다. 이미 같은 source의 native 빌드가
준비되어 있으면 `npm run release:prepare -- --no-build`를 사용할 수 있다.
두 번째 명령은 해시·크기·커밋·계정·registry가 적힌 로컬 게시 계획만 출력한다.

**실제 업로드 명령:**

```sh
npm run publish:nvcompact -- --start
```

`--start`는 실제 registry 쓰기 요청이다. 이 경로는 npm의 `dry-run=false`와
`force=false`를 명시해, 전역 dry-run 설정을 실제 게시 성공으로 잘못 보고하지 않는다.
실제 업로드를 원하지 않으면 `--start`를 붙이지 않는다.

계정이 선택되어 있지 않은 경우에만 먼저 `npm login --registry=https://registry.npmjs.org/`로
`daejunnom`에 로그인한다. 업로드 경로는 `npm whoami`가 설정한 개인 계정과 같은지,
이름의 기존 관리자가 같은지, 버전이 미게시인지 확인한다. npm의 2FA prompt는 그대로
사용하고 토큰·OTP를 저장소나 명령 인자에 쓰지 않는다. 게시자는 필요할 때 이
스크립트를 통해 인증한다. CI 연결 준비를 위해 이 세션에서 대신 로그인하지 않는다.

다른 디렉터리에 보관하거나 CI의 prepare 산출물을 내려받은 경우:

```sh
npm run publish:nvcompact -- --bundle /absolute/path/to/release-bundle --start
```

bundle의 source commit과 현재 clean main, 현재 source fingerprint, 검증한 tarball의
해시가 일치해야 한다. 실패한 요청의 재시도 전에 npm registry에서 실제 게시 여부를
확인한다. 게시된 동일 버전 덮어쓰기나 실패를 숨기는 다른 이름·인증 방식으로의
전환은 하지 않는다. 이후 버전은 Cargo crate와 npm package의 버전을 함께 올린다.

### Windows/macOS 등에서 준비된 tarball만 업로드

GitHub의 `prepare` 작업이 생성한 release bundle을 내려받으면 Linux 엔진을 로컬에서
실행하거나 Rust를 빌드할 필요가 없다. 다음 표준 npm 경로는 운영체제와 무관하다.
`release.json`의 commit이 요청한 main SHA와 같고, 다음 계산의 bytes/sha256이 그
기록과 같은지 먼저 확인한다. `npm whoami` 결과는 `daejunnom`, pack 정보의 name/version은
`nvcompact`/검토한 버전이어야 한다.

```sh
npm whoami --registry=https://registry.npmjs.org/
node -e "const f=require('node:fs'),c=require('node:crypto'),b=f.readFileSync(process.argv[1]);console.log(JSON.stringify({bytes:b.length,sha256:c.createHash('sha256').update(b).digest('hex')}))" ./nvcompact-0.4.0.tgz
npm pack ./nvcompact-0.4.0.tgz --dry-run --offline --ignore-scripts --json
```

확인한 파일의 **실제 업로드 명령**은 다음과 같다. 이 표준 npm 경로에서는 위 계정,
commit과 파일 확인을 사용자가 수행하며 저장소의 Linux 게시 스크립트를 호출하지 않는다.

```sh
npm publish ./nvcompact-0.4.0.tgz --access=public --registry=https://registry.npmjs.org/ --tag=latest --ignore-scripts --dry-run=false --force=false
```

## OIDC 연결: 최초 게시 이후

사용자 요청의 `OCID`는 여기서는 **OIDC(OpenID Connect)**로 해석했다. npm trusted
publisher는 기존 패키지에 연결하므로 최초 수동 게시가 먼저다. 공식 npm 문서는
OIDC에 npm 11.5.1 이상과 Node 22.14.0 이상을 요구하며, 현재 GitHub-hosted runner를
지원한다. 이 workflow는 Node 24와 고정 npm 12.2.0을 사용한다.

npm 패키지 Settings → Trusted Publisher에서 GitHub Actions를 선택하고 다음을
입력한다. 필드는 대소문자까지 일치해야 한다.

| npm 설정 필드 | 입력 |
| --- | --- |
| Organization or user | `daejunnom` |
| Repository | `Rove4k` |
| Workflow filename | `nvcompact-publish.yml` — 전체 경로를 넣지 않음 |
| Environment | `npm-release` |
| Allowed actions | 아래의 실제 사용할 stage/direct 경로에 맞게 선택 |

현재 npm 정책에서는 새 연결의 stage publish가 기본이다. 직접 공개하는 workflow
입력 `publish`를 사용할 경우 npm 설정에서 **`npm publish`도 명시적으로 허용**해야
한다. stage-only 연결이 direct 권한을 자동으로 얻지 않는다. 이 저장소에는 그 권한을
확대하거나 실패 시 다른 인증으로 재시도하는 명령을 넣지 않는다.

계정 2FA와 npm 11.15 이상을 갖춘 CLI로 설정할 수도 있다. 아래는 **stage-only 연결**을
추가하는 사용자가 실행할 명령이다. 이 문서를 작성하면서 실행한 명령이 아니다.

```sh
npm trust github nvcompact --repo daejunnom/Rove4k --file nvcompact-publish.yml --environment npm-release --allow-stage-publish
```

새 trusted publisher는 **설정 후 2일 이내 첫 성공 게시**로 검증하지 않으면 만료된다.
다음 버전을 게시할 준비가 된 시점에 연결한다. 설정 저장만으로 연결 성공이 검증되지
않으며, 최초 실제 성공을 관측하기 전까지 OIDC 연결 완료로 보고하지 않는다.
GitHub `npm-release` environment에는 `main` 배포 제한과 원하는 reviewer 보호를
사용자가 설정한다. 이 workflow 파일만 추가해 environment 보호가 활성화되지는 않는다.

## 이후 배포 workflow

[`NVCompact release`](../../../.github/workflows/nvcompact-publish.yml)는
`workflow_dispatch`로만 시작한다. `main`을 선택하고 정확한 package `version`과
40자리 `commit`을 입력한다. PR·develop·fork·다른 workflow·다른 SHA의 요청은 거부한다.

| operation | 실제 동작 |
| --- | --- |
| `prepare` — 기본 | build/test/pack/실제 설치 후 bundle을 GitHub artifact로 보관. npm 게시 job은 시작하지 않음 |
| `stage` | 같은 bundle을 OIDC로 `npm stage publish`에 전달. npm maintainer의 2FA 승인 전 공개되지 않음 |
| `publish` | 같은 bundle을 OIDC로 `npm publish`에 전달. trusted publisher의 direct 권한 필요 |

package job에는 `id-token: write`가 없다. `npm-release` environment를 거친 publish
job에만 그 권한을 둔다. GitHub가 발급한 OIDC 환경을 요구하고 장기 npm publish token을
사용하지 않는다. 게시 job은 빌드하거나 포장하지 않고, 검사한 tarball의 바이트를 다시
확인한 뒤 전달한다. provenance도 함께 요청한다. 현재 공식 npm 지원 범위에서 public
repository/public package의 GitHub OIDC 게시에는 provenance가 생성된다.

예를 들어 GitHub CLI를 쓰는 경우 다음은 **사용자가 선택한 stage 요청**이다.
`<MAIN_SHA>`는 검토한 현재 main 커밋으로 바꾼다. `prepare`를 선택하면 npm 업로드 없이
동일한 빌드 산출물을 확인할 수 있다.

```sh
gh workflow run nvcompact-publish.yml --ref main -f version=0.4.1 -f commit='<MAIN_SHA>' -f operation=stage
```

stage 결과는 npm package 페이지 또는 `npm stage list nvcompact`로 검토하고,
출력된 stage ID를 대상으로 `npm stage approve <STAGE_ID>`에서 계정 2FA로 승인한다.
최초 0.4.0을 수동 게시한 뒤에는 같은 0.4.0을 OIDC로 다시 게시하지 않는다.

## 확인한 공식 자료

- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/): 지원 런타임,
  workflow/environment 연결, 현재 allowed actions·2일 만료·provenance 조건.
- [npm trust](https://docs.npmjs.com/cli/v11/commands/npm-trust/): 기존 package와
  계정 2FA 전제, `--file`, `--repo`, `--environment`, allowed-action 인자.
- [npm staged publishing](https://docs.npmjs.com/staged-publishing/): stage와 공개
  승인 단계의 구분. CLI 인자는 npm 12.2.0 배포 소스의 `stage/publish.js` 및
  `publish.js`에서도 확인했다.
- [unscoped public package 게시](https://docs.npmjs.com/creating-and-publishing-unscoped-public-packages/).

공식 npm trust 11 문서에는 과거 단일 publisher 제한 설명도 남아 있다. 현재 서비스의
연결 개수·동작은 더 최신의 trusted-publishers 안내를 사용하며 이 도구가 연결 개수를
고정하지 않는다.
