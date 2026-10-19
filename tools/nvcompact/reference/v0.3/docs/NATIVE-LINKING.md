# C/Rust 구현 포트폴리오와 전용 링커 사용법

모노레포에서 이 문서의 예제 소스 기준 디렉터리는 `packages/nvcompact/`다. 직접 Python 명령은 그 디렉터리의 `python/` 아래 진입점을 사용한다. 루트에서 실행하는 npm 명령은 [README](../README.md)에 있다.

NVCompact는 같은 계약을 구현한 **C/C, C/Rust, Rust/Rust 조합을 실제로 빌드하고, 링크한 실행 파일과 압축한 최종 파일을 검사하여 선택하는 도구**다. Python 표준 라이브러리만 사용하는 후보 실행기, 두 종류의 GNU ld script, C/Rust 커널 예제, 독립적인 입력·출력 검사기를 함께 제공한다.

사용자가 명시한 구현 후보와 설정의 조합을 조사한다. 임의의 C를 Rust로 번역하거나, 두 함수의 의미가 같음을 자동으로 증명하거나, 서로 다른 결과의 다수결로 정답을 정하지 않는다. 검증기에서 실제로 확인한 계약과 범위는 결과에 남는다.

이 패키지는 앞서 작성한 v2 외부 설계 핸드오프를 실행 가능한 예제로 구체화한 부록이다. 이전 v2 문서와 보존본은 수정하지 않았다. 여기의 실행 방법은 도구 사용 설명이며 엔진 저장소의 새 AGENTS 규약이 아니다. 예제 코드와 도구는 이 작업에서 작성했으며 RoveZero/PALS 등의 저장소 소스나 가중치를 복사하지 않았다.

## 먼저 읽을 파일

| 파일 | 내용 |
|---|---|
| [examples/mixed/manifest.json](../packages/nvcompact/examples/mixed/manifest.json) | 바로 실행할 수 있는 후보 포트폴리오 |
| [examples/mixed/README.md](../packages/nvcompact/examples/mixed/README.md) | 두 정수 커널의 의미, C ABI, binary protocol, 직접 빌드 방법 |
| [docs/MANIFEST.md](MANIFEST.md) | 실제 manifest 필드와 명령 인자 확장 규칙 |
| [docs/REVIEW-AND-RESULTS.md](REVIEW-AND-RESULTS.md) | 이번 작업에서 수행한 비교·수정과 실제 결과 |
| [docs/SOURCES.md](SOURCES.md) | 컴파일·링크·ABI·압축 관련 공식 근거 |

## 1. 실행 환경

제공된 전체 예제의 대상은 **Linux x86-64**다. 다음 프로그램이 필요하다.

- Python 3.11 이상과 표준 `gzip`, `zlib`, `bz2`, `lzma` 모듈.
- GNU C compiler와 GNU binutils `ld`. 예시의 `cc`는 GNU 옵션을 지원하는 컴파일러여야 한다.
- 같은 host ABI를 대상으로 native object를 만들 수 있는 `rustc`.
- 압축된 script 후보를 실행할 때 `/bin/sh`, Python의 `memfd_create`와 fd 기반 `execve`, `/proc/self/status`, executable memfd를 허용하는 Linux 정책.

Cargo와 외부 crate, Python 패키지 설치는 필요하지 않다. 현재 Rust 예제는 작은 `no_std` 함수에 명시적인 `extern "C"`를 사용하고 `--emit=obj`로 native object를 만든다. 일반 Rust `rlib`, 표준 라이브러리, allocator, panic unwinding과 arbitrary dependency graph를 GNU ld에 직접 넘기는 범용 Rust 링크 방법을 구현한 것은 아니다.

프로젝트 명령은 해당 프로젝트가 신뢰하는 빌드·검증 명령으로 취급한다. 실행기는 임의로 받은 소스와 명령을 격리하는 보안 sandbox가 아니다. 제공된 예제는 daemonize하거나 별도 process group으로 분리되지 않는다.

## 2. 첫 실행

아래 명령은 이 패키지의 루트에서 실행한다. 첫 시도에서는 size 빌드와 compact 링크 프로필로 범위를 좁힌다. 명시된 baseline 검사는 이 필터와 별도로 수행된다.

```sh
python3 python/nvcompact.py run examples/mixed/manifest.json \
  --out runs/mixed-01 \
  --profile size --link-profile compact \
  --jobs 2 --max-candidates 32 \
  --max-seconds 600 --command-seconds 30
```

`--out`에는 아직 존재하지 않는 디렉터리를 지정한다. 실패한 실행의 기록이나 이전 winner를 덮어쓰지 않는다. 같은 명령을 다시 실행하려면 `runs/mixed-02`처럼 새 경로를 사용한다.

컴파일러가 PATH에 없거나 `rustc`가 rustup proxy인 경우 실제 compiler executable을 지정할 수 있다. 실행기는 빌드 환경을 명시적으로 구성하므로, 사용자 shell의 rustup 설정에 의존하는 proxy 대신 선택한 toolchain의 실제 `rustc` 경로를 지정하는 편이 명확하다. 다음 `/opt/toolchains/rust/bin/rustc`는 설치 위치의 예시이며 자신의 실제 절대 경로로 바꾼다.

```sh
python3 python/nvcompact.py run examples/mixed/manifest.json \
  --out runs/mixed-explicit-rust-01 \
  --tool rustc=/opt/toolchains/rust/bin/rustc \
  --profile size --link-profile compact --jobs 2
```

rustup을 사용한다면 현재 shell에서 `rustup which rustc`로 실제 경로를 확인할 수 있다. `--tool cc=...`, `--tool ld=...`, `--tool python=...`도 같은 방식이다. 필터로 일부 후보만 조사하더라도 manifest에 선언된 도구는 시작 시 모두 확인한다.

전체 예시 포트폴리오를 조사하려면 프로필 필터를 생략하고 새 결과 디렉터리를 지정한다.

```sh
python3 python/nvcompact.py run examples/mixed/manifest.json \
  --out runs/mixed-full-01 \
  --jobs 2 --max-candidates 128 \
  --max-seconds 600 --command-seconds 30
```

후보 개수와 실제로 완료한 범위는 `report.json`의 `planned_link_candidates`, `selected_link_candidates`, `search_complete`에서 확인한다. 이 값은 현재 manifest와 CLI 필터에 따라 달라진다. 후보 수 상한은 링크 recipe 개수에 적용하며, 각 recipe에서 나오는 배포 변환·codec별 파일 검사 수와 같지 않다.

## 3. 선택한 결과 재생성

성공한 실행은 `winner.recipe.json`을 제공한다. 전체 탐색을 반복하지 않고 선택된 조합만 새 디렉터리에서 다시 컴파일·링크·변환·압축하고 최종 검사를 수행한다.

```sh
python3 python/nvcompact.py reproduce runs/mixed-01/winner.recipe.json \
  --out runs/mixed-01-rebuilt \
  --max-seconds 600 --command-seconds 30
```

필요하다면 여기에도 `--tool rustc=/실제/절대경로/rustc` 등을 전달한다. 재생성에 필요한 도구의 실제 내용과 version 출력은 저장된 기록과 맞아야 한다. 선택한 recipe는 직접 참조한 도구와 명시적인 `requires_tools` 의존성을 보존하므로 C만 선택한 결과의 재생성에 불필요한 Rust compiler를 요구하지 않는다. 프로젝트와 입력 snapshot 자체는 그대로 보존한다.

소스, runner, Python·zlib의 재현성 기록을 확인하고 실제 bytes와 최종 동작을 대조한다. 커널·플랫폼 설명은 실행 근거로 남지만 문자열이 다르다는 이유만으로 재현을 거부하지 않는다. 실행 대상의 호환성은 실제 재빌드와 검사에서 확인한다.

`run` 자체도 winner를 공개하기 전에 다른 소스 경로에서 동일 recipe를 다시 빌드한다. 객체 캐시는 재사용하지 않으며, 링크 직후 native bytes와 완성 제출 파일 bytes의 동일성을 확인하고 `verify_final`을 실행한다. 외부 `reproduce` 명령은 사용자가 그 작업을 별도로 반복할 수 있게 한다.

이 기능은 기록된 환경에서의 선택 recipe 재생성이다. 툴체인·시스템 라이브러리·codec 구현 전체를 담은 hermetic 컨테이너를 자동으로 만들거나, 다른 운영체제와 도구 버전에서도 같은 bytes가 나온다고 증명하지 않는다. 재현 불일치를 만나면 source path, toolchain, 생성 순서, 환경과 변환 로직의 원인을 조사한다. 기대 hash를 현재 결과로 바꿔 성공으로 처리하지 않는다.

## 4. 무엇을 n-versions로 비교하는가

예제에는 두 개의 교체 지점이 있다.

| component | 계약 | 대안 |
|---|---|---|
| `popcount` | `uint64_t`의 1비트 개수를 `uint32_t`로 반환 | C Kernighan, C SWAR, Rust 구현 |
| `square` | square 0~63의 정해진 점수를 `int32_t`로 반환 | C 산술식, C 테이블, Rust 구현 |

각 component에서는 정확히 하나의 구현을 선택한다. 모든 대안을 한 executable에 넣은 뒤 weak symbol이나 링크 순서의 우연에 맡기지 않는다. 선택된 객체는 manifest의 순서와 링크 프로필에 따라 GNU ld로 링크한다.

비교 범위에는 구현 조합, C/Rust 최적화 설정, 명시한 객체 순서, hosted/compact 링크 프로필, 허용된 ELF 배포 변환, codec 설정이 들어간다. **개별 함수나 object의 최솟값을 이어 붙이는 방식으로 최종 승자를 추정하지 않는다.** 정렬·section 배치·링크 공통화와 압축 패턴이 서로 영향을 주기 때문이다.

현재 예제는 GCC object와 Rust LLVM object를 공통 native ABI에서 링크한다. `size`, `speed` 외에 `size-lto`가 C 쪽 GCC LTO를 비교하며 Rust는 native object로 남는다. GCC와 Rust 사이의 cross-language LTO를 가정하지 않는다. 링크는 compiler driver를 통해 GNU ld와 필요한 GCC plugin을 사용하고, unit identity에 따른 compiler seed를 고정한다. `language` 필드는 구현을 설명하는 metadata이며 자동 번역이나 적합한 compiler flags의 자동 선택을 유발하지 않는다.

동등성의 출발점은 component의 입력 영역·정수 의미·부작용·호출 규약에 대한 명시적인 계약이다. 같은 심볼, 같은 인자 개수, 같은 유한 테스트 출력만으로 arbitrary 프로그램의 의미 전체가 같아지는 것은 아니다. 예제 verifier는 별도의 Python oracle를 사용하며 그 유한한 검사 범위를 기록한다.

## 5. 전용 linker script와 배포 변환

[linker/hosted.ld](../packages/nvcompact/linker/hosted.ld)는 GNU default script를 보완하여 선택한 커널 section을 배치한다. 보통의 C runtime을 유지하는 프로필이다.

[linker/linux-x86_64-compact.ld](../packages/nvcompact/linker/linux-x86_64-compact.ld)는 해당 예제의 Linux x86-64 freestanding 입력에 맞춘 프로필이다. syscall driver와 별도 `_start`를 사용하며, 동적 링크·writable 전역·TLS·생성자·unwind 등을 요구하지 않는다. 입력에 필요한 런타임 기능을 분석하지 않은 채 이 script를 일반 Rust/C 프로그램에 적용해서는 안 된다. 예제는 orphan section을 오류로 처리하고 지원하지 않는 GOT/PLT/relocation 내용 등을 확인한다.

`allow_section_header_removal: true`인 링크 프로필에는 원본 외에 section-header 제거 후보가 생긴다. 현재 변환은 ordinary ELF64 little-endian x86-64 ET_EXEC/ET_DYN에 한정한다. ELF header와 program-header table 및 모든 program-header의 file extent를 보존하고, 필요한 마지막 byte 뒤를 자른 다음 section-table metadata를 수정한다.

이 flag는 자기 파일과 section table을 읽지 않고, 수정하는 ELF metadata bytes를 실행 코드나 데이터로 재사용하지 않는다는 배포 계약을 사용자가 선언하는 것이다. **section-header 제거는 byte-lossless codec이 아니다.** 적용 전제를 소스에서 자동 증명하지 않으며, 변환한 실제 실행 파일도 다시 검사한다. extended numbering이나 지원하지 않는 레이아웃을 추측해서 통과시키지 않는다. 필요하지 않은 프로젝트는 flag를 생략하거나 `false`로 둔다.

## 6. 압축한 완성 파일

`nvpack.py`는 raw, gzip, zlib, bzip2, XZ, x86 BCJ+XZ, LZMA-alone 후보를 생성한다. 패키지 기본 기능은 여러 설정을 지원하고, 예시 manifest는 그중 명시한 exact ID만 조사한다. `raw`는 항상 비교에 포함된다.

압축 후보는 `sh → exec python3 → anonymous memfd → fd exec`로 native ELF를 실행한다. payload뿐 아니라 이 실행부까지 합친 길이를 비교한다. 선택한 codec의 Python 표준 모듈만 사용하고, 파일 시스템에 executable을 추출하거나 일정 시간 뒤 지우는 background 작업을 만들지 않는다.

실제 구현에서는 다음 문제를 다뤘다.

- payload offset은 loader 자체 길이의 변화를 반영해 계산한다.
- codec 복원과 실제 내장 payload slice의 복원을 각각 확인한다.
- memfd 전체 기록과 flush를 완료한 뒤 exec하고 descriptor는 close-on-exec이다.
- Python이 바꾸는 SIGPIPE/SIGXFSZ의 ignored 상태와 LC_CTYPE를 복원한다.
- shell의 read 임시 변수는 subshell 안에 가둬 호출자의 export 환경값을 덮어쓰지 않는다.

이 실행부는 **일반 TCEC 4k script 프로필**의 후보이며 외부 프로그램이 금지되는 별도 ELF-only 프로필은 아니다. Linux의 memfd 실행 정책과 Python codec 지원은 실제 배포 환경에서 확인해야 한다. custom `argv[0]`, 자기 파일·`/proc/self/exe` 관측, `$ORIGIN` 상대 라이브러리, privileged executable, 정확한 startup 관측을 요구하는 프로그램에는 이 프로필을 그대로 적용할 수 없다. 이러한 계약에는 raw 또는 그 요구를 지원하는 다른 실행부가 필요하다.

## 7. 결과 파일과 선택 상태

| 출력 | 의미 |
|---|---|
| `winner` | 최종 재빌드와 검사까지 통과해 공개한 완성 실행 파일 |
| `winner.recipe.json` | 선택한 구현·build/link·순서·배포 변환·codec와 재생성 근거 |
| `report.json` | 조사 범위, 후보별 크기·상태·실패, 검사 로그 위치와 winner |
| `project.json` | snapshot 기준으로 정규화한 manifest |
| `snapshot/` | 명시적으로 선언한 입력 파일의 복사본 |
| `objects/`, `baseline/`, `candidates/` | 이 실행이 만든 중간 결과와 명령·검사 로그 |
| `reproduction/` | `run` 안에서 수행한 독립적인 재빌드와 최종 검사 |
| `reproduction.json` | 별도 `reproduce` 명령의 byte 동일성·최종 검사 결과 |

제출 파일 크기는 `winner` 한 파일의 크기다. recipe·snapshot·로그는 개발 근거이며 그 파일 안으로 암묵적으로 포함하거나 외부 engine code로 사용하는 것이 아니다.

선택은 다음 순서로 이루어진다.

1. 명시한 baseline을 `verify_final`로 확인한다.
2. 링크 recipe의 native executable을 `verify`로 확인한다.
3. 각 배포·압축 완성 파일을 `verify`로 실행하고 파일 상한을 적용한다.
4. 검사까지 완료한 `screened` 파일 중 가장 작은 파일을 선택한다. 후속 codec 작업이 예산에 도달해 recipe가 `incomplete`가 되어도 먼저 완료한 파일은 비교할 수 있다. recipe 자체의 실패·내부 오류는 별도로 처리한다. 동률은 안정적인 후보 ID와 artifact ID 순서로 처리한다.
5. 선택한 한 파일을 새 소스 디렉터리에서 다시 만들고 bytes와 `verify_final`을 확인한다. 성공해야 winner를 공개한다.

최종 검사나 재빌드가 실패하면 해당 실행은 실패로 기록한다. 그 결과를 조용히 제외하고 다음 파일을 새 winner로 승격하지 않는다. 처음의 screening을 통과한 이유와 더 강한 검사에서 드러난 차이를 조사해야 한다.

| 상태 | 해석 |
|---|---|
| `accepted` | 선택한 결과가 재빌드·최종 검사를 통과했다. 탐색 범위 전체의 완료 여부는 별도다. |
| `screened` | 후보별 검사와 파일 상한을 통과한 완성 파일이다. 각 파일의 독립 재빌드를 모두 끝냈다는 뜻은 아니다. |
| `over_size_limit` | 실행 검사는 통과했지만 선언한 `max_bytes`를 넘는다. |
| `incomplete` | 시간·로그 예산 등으로 관련 처리를 완료하지 못했다. 동등성을 입증하거나 반박한 결과가 아니다. |
| `failed` / `internal_error` | 명령·검사·구성 또는 도구 로직의 문제가 기록되어 있다. `phase`, `error`, 로그를 확인한다. |
| `interrupted` | 사용자의 중단 등으로 실행이 정상 완료되지 않았다. |

`search_complete=false`인 상태에서도 완료·검증한 집합의 winner가 승인될 수 있다. 이때는 **완료한 집합 안의 최소**다. `search_complete=true` 역시 해당 manifest와 필터의 조사를 끝냈다는 뜻이며, 모든 후보가 동등했다거나 세상의 모든 구현 중 최적이라는 뜻은 아니다. 현재 값의 상세 해석은 manifest guide의 결과 설명을 참고한다.

## 8. 병렬 실행과 예산

`--jobs`는 동시에 처리할 링크 후보 작업 수다. 같은 build profile의 공통 객체와 같은 variant 객체는 해당 campaign 안에서 한 번 만들고 재사용한다. 이는 엔진 자체의 SMP 설계나 TCEC 서버의 전체 코어 활용 성능을 측정하는 기능이 아니다.

compiler·linker·검사기 내부의 스레드는 `--jobs`에 포함된 총 CPU quota로 자동 제한되지 않는다. 많은 작업을 동시에 수행하면 메모리 사용, 스토리지, 압축 시간과 verifier 지연이 증가할 수 있다. 압축 후보 탐색과 엔진의 안정적인 속도·기력 측정은 서로 다른 실험으로 구성하는 편이 좋다.

`--command-seconds`는 개별 외부 명령의 timeout이다. `--max-seconds`는 campaign의 명령 실행과 각 codec 후보 시작 전에 확인하는 wall-time 예산이고, 새 재빌드에는 별도 예산이 생긴다. snapshot 복사나 이미 시작한 Python 내부 압축까지 즉시 선점하는 전체 프로세스의 hard watchdog은 아니다. `--max-log-bytes`는 수집한 stdout/stderr의 합계를 감시하며 polling 사이의 짧은 초과까지 차단하는 파일 시스템 quota는 아니다.

runner는 자신이 시작한 직접 process group을 정리하고 자식을 reap한다. 임의로 detach한 process tree 전체를 찾아 종료하거나 모든 자원의 합계를 정확하게 계측하는 도구는 아니다. 더 강한 자원 격리와 시간·메모리 측정이 필요한 실제 엔진 실험은 그 실행 환경에서 추가한다.

## 9. 자신의 엔진에 적용하기

먼저 독립적으로 교체할 수 있는 작은 지점과 그 입력·출력·상태 계약을 정한다. 같은 ABI의 C/Rust 구현이나 같은 언어의 여러 구현을 직접 준비하고 `components[].variants`에 등록한다. 고정 폭 정수, 범위 밖 입력, overflow, float 의미, 포인터 aliasing, 소유권·수명, allocation, TLS·초기화, exception/unwind와 동시성을 관련된 만큼 명시한다.

공통 driver 또는 엔진 본체는 링크 프로필의 `common`에 등록할 수 있다. 컴파일 전에 generator나 언어 기반 minifier를 실행하려면 해당 unit의 `commands`에 명령을 추가하고 generator와 정본·설정을 `inputs`에 포함한다. 현재 패키지가 generic minifier나 source translator를 자동으로 제공하는 것은 아니다.

실제 엔진의 checker는 선택한 의미 계약에 맞게 작성한다. UCI, legal move/state 복원, 정해진 budget에서의 탐색 동작, 배포 시작 조건과 리소스 요구는 이 정수 예제의 verifier가 대신 확인하지 않는다. SMP 실행에서 wall-clock 결과의 완전 일치가 적절하지 않다면, 왜 그런지와 무엇을 비교할지를 계약과 verifier에 반영해야 한다.

이후 build/link 프로필, 명시적인 배치 순서, codec 설정을 추가해 비교 범위를 넓힐 수 있다. 새로운 설계가 의미를 바꾸는 경우에는 같은 의미의 압축 후보라고 표시하지 말고, 그 설계의 별도 계약과 baseline을 세워 비교한다. 현재 예제의 실측은 [검토와 결과](REVIEW-AND-RESULTS.md)에 기록하며 체스 엔진의 제출 크기, NPS, SMP scaling 또는 기력으로 외삽하지 않는다.
