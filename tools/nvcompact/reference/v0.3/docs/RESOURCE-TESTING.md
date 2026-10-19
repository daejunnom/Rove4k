# 자원이 큰 엔진을 별도로 검증하기

`nvcompact resource`는 **계획 생성**과 **실제 실행**을 분리한다. `plan`은 입력 파일·도구 경로·현재 자원만 읽고, `run`은 `--start`가 있는 별도 명령에서만 엔진 실행을 시도한다. 이 명령은 기본 `npm test`, 기본 엔진 압축 포트폴리오나 패키지 설치 훅에서 고메모리 엔진을 시작하지 않는다.

대상이 사용하는 TT, 스레드 수, 탐색 정책과 원래 launcher를 수정하지 않는다. 여기에 포함한 원본 프로파일은 UCI의 `setoption`도 보내지 않는다. 필요한 자원을 작게 바꾼 새 엔진을 원본의 성공으로 기록하는 기능이 아니다.

## 계획과 실행 명령

저장소 루트에서 ice4 공개 v6.1 원본의 계획을 만들 수 있다. 다음 명령은 원본 엔진, 메모리 할당 probe, compiler/version 명령을 실행하지 않는다.

```sh
npm exec -- nvcompact resource plan \
  packages/tcec4k-lab/resource-profiles/ice4-v6.1-original.json \
  --output runs/ice4-resource-plan.json
```

계획 파일에서 정확한 입력 SHA256, 원래 실행 명령, 선언한 메모리와 여유량, 유한 실행 상한, 현재 호스트/cgroup 관측과 `preflight_at_plan`을 검토한다. `status: planned`는 실행 완료나 프로토콜 통과를 뜻하지 않는다. `preflight_at_plan.status: ready` 역시 읽기 전제의 충족이라는 뜻이다.

실제 실행할 서버에서 계획을 생성하고, 다음 **별도 명령을 명시적으로 실행했을 때만** 해당 계획의 엔진을 시작한다. 이 문서의 예제는 실행 권한이나 서버 배정을 만들지 않는다.

```sh
npm exec -- nvcompact resource run runs/ice4-resource-plan.json \
  --start --output runs/ice4-resource-execution-01
```

`run`은 입력 지문과 도구 해석, 현재 메모리와 상속 자원 제한을 다시 확인한다. 부족한 메모리, 변경된 소스·프로파일·도구·실행기, 빠진 도구는 엔진 실행 전에 `blocked`로 기록한다. 과거 서버의 `runtime_blocked` 사유는 계획에 그대로 남기지만, 다른 서버에서의 현재 자원 관측과 구분한다.

입력·환경·실행기나 제한을 바꿨다면 specification을 수정하고 새 계획을 만든다. 계획 checksum을 수정하는 것은 재검토와 재생성의 대체 경로가 아니다. 기존 결과 디렉터리는 덮어쓰지 않는다.

## 제공하는 원본 프로파일

다음 수치는 번들 매니페스트의 정확한 배포 payload와 대응 소스에서 확인한 할당·worker 설정이다. 8 GiB 여유량과 주소 공간 상한은 **실행을 위한 명시적 설정값**이며, 프로그램 전체 최대 사용량을 실제 측정한 결과가 아니다.

| 프로파일 | 보존한 주요 메모리 설정 | 원래 worker | 계획의 추가 여유 RAM / 주소 공간 상한 |
|---|---|---:|---|
| `ice4-v6.1-original.json` | `calloc(1ull<<35,8)`: 256 GiB 요청 | 256 | 8 GiB / 288 GiB |
| `c4ke-v3.0-original.json` | `calloc(1ull<<35,8)`: 256 GiB 요청 | 256 | 8 GiB / 288 GiB |
| `M4sseur-1.0-original.json` | `0x100000000 * 16` 바이트 TT를 명시적으로 초기화: 64 GiB | 103 | 8 GiB / 96 GiB |
| `molly-e317a0c7b8-original.json` | `0x100000000`개의 24바이트 TT entry: 96 GiB | 101 | 8 GiB / 128 GiB |

프로파일은 [실험 workspace](../packages/tcec4k-lab/resource-profiles/)에 있다. 출처와 공개 파일/대회 파일의 대응 범위는 [BUILD-REQUIREMENTS.md](../packages/tcec4k-lab/research/BUILD-REQUIREMENTS.md), [엔진 매니페스트](../packages/tcec4k-lab/engines/)와 vendor 기록을 함께 읽는다. 새 테스트의 성공이 독립적인 소스→배포 파일 재생성이나 private TCEC 제출물의 동일성까지 증명하지 않는다.

STRO4K에는 약 266 GiB의 ELF 가상 메모리 세그먼트와 아직 원인이 확정되지 않은 시작 실패 기록이 있다. 가상 주소 공간의 크기를 물리 RAM 필요량으로 곧바로 바꾼 실행 가능 프로파일은 제공하지 않는다. 원래 loader/CPU/주소 공간의 실패 원인을 확인한 뒤 별도 요구량을 선언해야 한다.

Molly의 원래 launcher는 임시 파일 제거까지 9초를 기다린다. 제공한 프로파일은 원래 helper를 유지하고 종료 후 정리 관찰에 12초를 둔다. TCEC의 시작 한도는 60초로 유지하며 정리 유예를 시작 성공으로 산입하지 않는다.

## 범용 specification

매니페스트가 없는 프로그램도 `artifact`, 선택적인 argv `command`와 `tools`, `budget`, `uci` 설정으로 계획을 만들 수 있다. `command`의 `{artifact}`는 선택한 파일의 절대 경로로 치환된다. 첫 executable은 현재 경로에서 한 번 해석해 `executable_path`로 고정하지만, 실행 시 원래 `argv[0]`과 심볼릭 링크의 호출 이름은 유지한다. 지문에는 링크 대상 파일을 기록하고 실행 직전 링크 해석도 다시 비교한다. 암묵적으로 셸을 추가하지 않는다.

`manifest`를 사용하면 artifact 경로는 해당 엔진 manifest 디렉터리를 기준으로 해석한다. 직접 `artifact`를 사용하면 specification 디렉터리가 기준이다. 필요한 compiler/interpreter와 해제 도구는 `tools`에 명시할 수 있다. 도구를 자동 설치하거나 다운로드하지 않는다. 계획은 각 도구를 실행해서 버전을 묻지 않고 파일의 SHA256을 읽는다.

| 설정 | 의미 |
|---|---|
| `budget.required_memory_bytes` | 대상 실행과 그 보조 작업에 필요하다고 선언한 RAM |
| `budget.reserve_memory_bytes` | 추가로 남겨 둘 RAM의 명시적 추정치 |
| `budget.address_space_bytes` | 각 프로세스가 상속할 주소 공간의 유한 상한 |
| `budget.cpu_seconds_per_process` | 각 프로세스의 CPU 시간 상한; 전체 프로세스의 CPU 합계가 아님 |
| `budget.wall_seconds` | UCI 검증 작업의 전체 경과시간 예산; 유한 종료 정리는 별도 |
| `budget.file_bytes` | 각 프로세스가 만들 수 있는 한 파일의 최대 크기 |
| `budget.output_bytes_per_session` | 각 UCI 세션의 stdout+stderr 출력 상한 |
| `uci.preserve_engine_options` | `true`이면 Hash/Threads 등을 포함한 모든 `setoption` 전송 생략 |

`uci.preserve_engine_options`는 resource 계획에서 기본 `true`다. 일반 `nvcompact uci`의 기존 동작을 사용할 때도 `--preserve-engine-options`로 켤 수 있다. 옵션을 보존하는 동안 `threads`, `hash_mb` 값은 실제 설정 요청으로 사용하지 않으며, 보고서는 광고된 기본값과 `preserved` 상태를 남긴다. 이 설정을 명시적으로 끈 별도 프로파일은 변경된 UCI 실행 구성으로 표시한다.

UCI 검증 자체에는 기존 개발 전용 `chess==1.11.2` oracle이 필요하다. `uci.oracle_path`를 설정하거나 검증 Python에서 해당 모듈을 사용할 수 있게 준비한다. `plan`은 oracle을 import하지 않는다. Oracle module의 SHA256은 계획의 입력 지문에 고정하지 않으며 실제 UCI 실행 보고서에서 관측하므로, 계획 가능 여부와 실행 환경의 oracle 준비 완료는 구분한다.

## 메모리 관측과 제한의 실제 범위

현재 Linux의 `MemAvailable`, cgroup v2 경로 및 보이는 조상의 `memory.max`, `memory.current`, `memory.stat`을 읽는다. 상위 cgroup의 더 작은 제한도 고려한다. 기록한 메모리 추정은 물리 `MemAvailable`과 각 cgroup의 `max - current + inactive_file` 중 작은 값이다. cgroup raw headroom과 inactive file 추정치를 따로 남겨 캐시 회수 전제를 숨기지 않는다.

이 계산은 지금 관측한 가용량의 추정이며 RAM 예약, 향후 할당 성공, 충전된 전체 page cache의 즉시 회수를 보장하지 않는다. `memory.current`에는 page cache 등도 포함되고 `memory.max`는 cgroup의 제한이다. 도구는 기존 cgroup 설정을 쓰거나 바꾸지 않으며, 이 프로세스만을 위한 새 cgroup도 만들지 않는다. cgroup v1 메모리 accounting은 이 실행 경로에서 지원하지 않으므로 명시적으로 차단한다. [Linux cgroup v2 공식 문서](https://docs.kernel.org/admin-guide/cgroup-v2.html)

주소 공간·CPU 시간·단일 파일 크기와 core dump 상한은 **새로 실행하는 wrapper 프로세스 안에서만** 낮추고 원래 artifact로 `exec`한다. 부모 프로세스의 `RLIMIT`와 환경은 변경하지 않는다. `RLIMIT_AS`는 각 프로세스의 가상 주소 공간 상한이고 `RLIMIT_CPU`는 프로세스 단위 CPU 시간 상한이다. 두 값을 전체 자식 프로세스의 동시 resident RAM 또는 전체 CPU 합계의 hard cap으로 보고하지 않는다. fork한 프로세스와 compiler도 제한을 상속한다. [Python resource 공식 문서](https://docs.python.org/3.11/library/resource.html)

정확한 작업 전체 RAM/CPU 격리가 필요한 실제 서버에서는 별도로 구성한 cgroup/container/job 안에서 실행한다. 이 도구의 `--start`는 서버 생성, 유료 자원 배정 또는 기존 격리 조건 완화 명령이 아니다. 원래 많은 worker가 현재 환경에서 실행되는 동작과 대상 many-core 서버의 성능 평가는 별도의 근거가 필요하다.

UCI 세션은 자신의 작업 디렉터리와 원래 process group을 소유한다. 제한 초과·프로토콜 실패·종료 시 해당 group을 정리한다. CLI launcher는 취소와 생성 중 프로세스 소유도 관리한다. 임의 helper가 독립 세션으로 분리한 작업까지 시스템 전체 PID를 탐색해 정리하는 기능은 없다. procfs의 PID namespace가 현재 프로세스와 달라도 숫자 PID를 근거로 다른 작업을 죽이지 않는다. [Python subprocess 공식 문서](https://docs.python.org/3.11/library/subprocess.html)

## 결과와 현재 확인 범위

결과 디렉터리에는 입력 계획 `plan.json`, 전체 상태와 변경 관측 `result.json`, 실제 UCI 작업이 결과를 만들었을 때의 `uci.json`이 남는다. `blocked`, `error`, `interrupted`, `fail`, `incomplete`, `pass`를 구분한다. 시작 단계에서 wrapper만 생성되고 artifact의 handshake를 관측하지 못한 경우에는 artifact 실행 확정을 주장하지 않는다. `pass`는 해당 유한 UCI 표본과 검증 경로의 성공이다.

작은 fixture 검사에서는 계획 및 opt-in 누락의 무실행, 자원 부족과 입력 변경의 사전 차단, UCI 옵션·부모 환경·부모 RLIMIT·원본 바이트 보존, 실제 자식의 제한과 `argv[0]`, 링크 대상 변경의 사전 차단, timeout 후 자식·손자의 소유 lock 해제, 입력 변조 실패를 확인한다. 가짜 기대값 수정이나 TT 축소를 이용하지 않는다. 큰 원본 엔진들의 실행은 별도 작업이며, 이 기능을 구현한 검사를 그 원본들의 성공으로 바꾸지 않는다.
