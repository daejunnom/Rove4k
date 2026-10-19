# Manifest 사용 설명

모노레포에서 이 문서의 예제 소스 기준 디렉터리는 `packages/nvcompact/`다. 직접 Python 명령은 그 디렉터리의 `python/` 아래 진입점을 사용한다. 루트에서 실행하는 npm 명령은 [README](../README.md)에 있다.

이 문서는 `nvcompact.py`가 현재 읽는 JSON 필드와 결과를 설명한다. 추가 JSON schema, 별도 validator, 특정 파일 구조를 새로 강제하는 규약이 아니다. 완성된 입력은 [examples/mixed/manifest.json](../packages/nvcompact/examples/mixed/manifest.json)에 있다.

이하의 필수 baseline·checker, 배포·codec와 `accepted` 설명은 압축 포트폴리오 **`run`**을 기준으로 한다. 0.3의 **`build`**는 같은 구현·컴파일·링크 필드를 사용하되 압축과 NVCompact 배포 변환을 생략한다. 기본 `build`는 baseline·checker를 요구하거나 실행하지 않고, 필요한 빌드 도구만 준비한다. native 파일의 크기 상한은 `build --max-bytes`로 지정한다. native recipe의 `reproduce`도 기본은 bytes 재현이며, 실제 checker 실행은 매 호출의 `--verify`로 요청한다. 자세한 계약과 상태는 [NATIVE-BUILD.md](NATIVE-BUILD.md)를 따른다.

C 구조 축약은 `notation`의 object bytes 일치 조건과 별개다. [C-REWRITES.md](C-REWRITES.md)의 `rewrite-c --run-manifest`는 원본과 구조별 생성물을 각각 component variant로 만들어 같은 runner에서 native·최종 압축 파일을 비교한다.

## 1. 입력의 기준 경로와 기록

| 필드 | 값과 의미 |
|---|---|
| `format` | 예제의 문서 버전 표식은 `1`이다. 이 값만으로 도구가 모든 과거 형식을 자동 변환하지 않는다. |
| `project_root` | manifest 파일이 있는 디렉터리를 기준으로 한 프로젝트 루트. 생략하면 `.`. 예제는 패키지 루트를 가리키는 `../..`이다. |
| `target` | 요구하는 실행 대상. 예제는 `x86_64-unknown-linux-gnu`. 필수이며 packing 프로필 판단에 사용한다. |
| `contract` | 전체 프로그램의 관측 가능한 의미와 배포 조건을 설명하는 metadata. 파일 경로와 설명을 함께 적을 수 있다. |
| `inputs` | snapshot에 포함할 프로젝트 상대 파일 경로의 비어 있지 않은 목록. 소스뿐 아니라 header, script, generator, linker script, checker와 관련 설정도 명시한다. |
| `environment` | 빌드·링크·검사 명령에 추가하거나 덮어쓸 환경값. 이름과 값은 문자열이다. |
| `verify_requires_tools` | 최종 checker의 내부 script 등에서 사용하는 추가 도구 별칭 목록. 선택 recipe의 재생성 의존성에 포함한다. |
| `max_bytes` | 선택할 완성 파일의 최대 bytes. 예제는 `4096`. 생략하거나 `null`이면 이 파일 크기 상한을 적용하지 않는다. |
| `max_native_bytes` | 개별 object와 링크 직후 native 파일의 크기 상한. 기본값은 64 MiB, 예제는 2 MiB다. 전체 RAM·디스크 사용량 quota는 아니다. |

`inputs`는 파일 단위다. 절대 경로, `..`를 통한 탈출, 프로젝트 밖으로 해석되는 파일은 허용하지 않는다. 내부 symlink가 파일로 해석되면 snapshot에는 그 파일의 내용이 들어간다. 선언하지 않은 dependency를 자동으로 찾아 추가하지 않으며, 프로젝트 밖의 compiler·시스템 라이브러리는 snapshot 파일과 구분된다.

실행 시작 시 선언된 파일을 `snapshot/`에 복사하고 SHA-256을 기록한다. snapshot을 기준으로 정규화한 manifest는 `project.json`에 저장한다. 선택 전후와 재생성에서 해당 입력이 변하지 않았는지 확인한다. snapshot은 선언된 입력의 보존이며 모든 toolchain과 시스템 dependency를 포함한 hermetic build image는 아니다.

`target` 문자열은 compiler에 `--target`이나 ISA 옵션을 자동 주입하지 않는다. 각 `commands`와 `argv`가 같은 대상의 ABI·ISA를 만들어야 한다. 제공된 실행·ELF 배포 예제는 Linux x86-64에서 확인하는 구성이다.

## 2. 도구 별칭

`tools`는 별칭을 key로 하는 object다.

```json
{
  "tools": {
    "cc": {"executable": "cc"},
    "ld": {"executable": "ld"},
    "rustc": {"executable": "rustc", "version_args": ["--version", "--verbose"]},
    "python": {"executable": "python3"}
  }
}
```

`executable`은 PATH에서 찾을 이름이나 경로다. `version_args`는 실제 executable 뒤에 붙여 버전을 기록하는 문자열 목록이며 기본값은 `["--version"]`이다. 예시에서는 Rust의 host와 LLVM 정보까지 기록하기 위해 `--verbose`를 사용한다. 도구 spec의 `requires_tools`에는 해당 도구가 의존하는 다른 도구 별칭을 적을 수 있다. 예를 들어 예시의 `cc`는 `ld` 의존성을 선언한다.

CLI의 `--tool NAME=EXECUTABLE`은 그 별칭의 executable을 바꾼다. 재현할 때는 같은 bytes와 version을 가진 도구여야 한다. 드라이버가 symlink 호출 이름을 해석할 수 있으므로 호출 경로를 무조건 realpath로 바꾸지 않는다. rustup proxy가 정리된 환경에서 toolchain을 찾지 못한다면 선택한 실제 `rustc`의 절대 경로를 지정한다.

새 포트폴리오를 탐색하는 `run`은 manifest에 선언된 모든 도구를 먼저 찾고 version 명령을 실행한다. 선택 결과의 `reproduce`는 기록된 tool 의존성만 준비한다. 따라서 C-only winner를 다시 만들 때 선택되지 않은 Rust 대안 때문에 rustc를 추가 요구하지 않는다. 첫 포트폴리오 자체에서 일부 언어를 제외하려면 그 variant와 불필요한 도구 선언을 함께 정리한다.

선택 recipe의 도구 의존성은 선택한 unit·build·link 및 최종 검사 명령이 직접 참조하는 alias/실행 파일에서 찾고, 아래 선언을 함께 반영한다.

| 위치 | 필드 |
|---|---|
| build profile, link profile, variant/common unit | `requires_tools: ["도구별칭", ...]` |
| 개별 tool spec | `requires_tools: ["의존도구별칭", ...]` — 전이적으로 따라간다. |
| manifest | `verify_requires_tools: ["도구별칭", ...]` |

argv 안에서 단순한 변수로 compiler executable을 선택하거나 선언된 executable 이름을 직접 쓰는 경우도 확인한다. 하지만 script 내부에서 동적으로 실행하는 모든 프로그램을 소스 분석으로 발견하지는 않는다. 그런 의존성은 `requires_tools` 또는 `verify_requires_tools`에 명시한다. 선언한 별칭이 tools에 없으면 오류다. 동일 script의 literal 인자에 `{rustc}`라는 텍스트가 있다는 사실만으로 실제 Rust 실행 의존성이라고 간주하지 않는다.

runner는 기본 PATH, `LANG=C`, `LC_ALL=C`, `TZ=UTC`, `SOURCE_DATE_EPOCH=0`, `PYTHONHASHSEED=0`, `PYTHONCOERCECLOCALE=0`을 구성한다. PATH에는 선언한 도구의 디렉터리와 `/usr/bin`, `/bin`이 들어간다. 현재 shell의 `CPATH`, `RUSTFLAGS`, `LD_PRELOAD` 등이 묵시적으로 빌드를 바꾸지 않도록 전체 환경을 그대로 상속하지 않는다. 필요한 환경은 `environment`에 명시하며 실제 값은 report에 남는다.

## 3. 명령은 문자열이 아니라 argv 목록

`commands`의 각 원소, 링크 `argv`, `post_link`의 각 원소, `verify`, `verify_final`은 **비어 있지 않은 argv 배열**이다. runner는 이 배열을 shell에 넘기지 않고 프로세스 인자로 실행한다.

```json
["{cc}", "-Os", "-c", "{source}", "-o", "{object}"]
```

경로에 공백이 있더라도 추가 shell quoting 문자를 넣지 않는다. `"'{source}'"`처럼 quote를 데이터에 붙이면 그 quote가 실제 인자에 들어간다. 파이프, redirection, wildcard도 자동 해석되지 않는다. 그런 작업이 필요하면 선언한 script를 실행하거나 명시적으로 shell을 호출해야 하며, 그 script의 입력 처리 책임은 프로젝트에 있다.

### 사용할 수 있는 placeholder

| 위치 | placeholder |
|---|---|
| unit의 컴파일·생성 `commands` | 도구 별칭, 선택한 build profile의 변수, `{root}`, `{build}`, `{object}`, `{sources}`, `{source}`, `{unit_id}` |
| 링크 `argv`와 `post_link` | 도구 별칭, 선택한 build profile의 변수, `{root}`, `{build}`, `{objects}`, `{binary}` |
| `verify`, `verify_final` | 도구 별칭, `{root}`, `{build}`, `{binary}` |

- `{root}`: 이번 실행의 source snapshot 디렉터리.
- `{build}`: 해당 unit·링크·검사 작업이 소유하는 작업 디렉터리.
- `{object}`: unit이 최종 생성해야 하는 단일 `unit.o` 경로.
- `{sources}`: unit의 `sources`를 해석한 경로 목록.
- `{source}`: 첫 source의 경로. sources가 없으면 빈 문자열이다.
- `{unit_id}`: 해당 common 또는 variant unit의 안정적인 identity. 예제는 `-frandom-seed={unit_id}`로 compiler의 단위별 seed를 재현한다.
- `{objects}`: 실제 선택된 common·component object의 경로 목록.
- `{binary}`: 링크에서 만들거나 checker가 실행할 해당 파일의 경로.

scalar placeholder는 문자열 안에도 들어갈 수 있다. 예를 들어 `-ffile-prefix-map={root}=.`는 하나의 인자다. list placeholder는 토큰 전체를 차지할 때 여러 argv로 펼쳐진다. `["{cc}", "{objects}", "-o", "{binary}"]`의 `{objects}`는 객체마다 별도 인자를 생성한다. `--objects={objects}`처럼 list를 한 문자열 안에 끼워 넣는 것은 오류다.

`{identifier}` 형태의 알 수 없는 placeholder는 오류다. 모든 중괄호가 placeholder는 아니지만, code snippet이나 문자열에서 의도한 `{name}`을 확실히 그대로 넘기려면 다음처럼 `literal` object를 사용한다.

```json
["{python}", "-c", {"literal": "print('{binary}')"}]
```

이 경우 마지막 인자는 `print('{binary}')` 그대로 전달된다. `literal` object에는 문자열 값 하나만 둔다. 변수·tool alias와 예약 placeholder를 같은 이름으로 두면 context 덮어쓰기가 생길 수 있으므로 구분되는 이름으로 작성한다.

## 4. 교체 가능한 component와 구현 variant

`components`는 비어 있지 않은 목록이다. 각 항목에는 다음 필드가 있다.

| 필드 | 의미 |
|---|---|
| `id` | 교체 지점의 이름. 예: `popcount`, `square`. |
| `contract` | 모든 variant가 구현해야 하는 의미·ABI 계약. 비어 있으면 구성 오류다. |
| `variants` | 이 component에서 하나를 선택할 구현 목록. |

variant의 unit 필드는 다음과 같다.

| 필드 | 의미 |
|---|---|
| `id` | component 안에서 구별되는 구현 이름. |
| `language` | 사람이 읽는 metadata. compiler 또는 ABI를 자동 선택하지 않는다. |
| `sources` | 프로젝트 상대 입력 파일 목록. 첫 파일은 `{source}`, 전체는 `{sources}`로 제공한다. |
| `commands` | 순서대로 실행할 argv 배열 목록. 마지막까지 성공하면 `{object}`에 native object가 있어야 한다. |
| `requires_tools` | 명령 내부 script 등에서 사용하는 추가 도구 별칭. 선택 결과 재생성에 포함한다. |
| `notation` | 0.2의 opt-in 표기 조사. 격리한 source 복사본에서 다시 compile하고 원본과 complete object bytes가 같은 표기만 링크 이전에 확정한다. |

ID는 같은 목록 안에서 중복되면 안 되며 `[A-Za-z0-9][A-Za-z0-9_.-]*` 형태를 사용한다. 서로 다른 component에서 같은 variant ID를 쓰는 것은 가능하다.

각 링크 recipe에는 component마다 **정확히 하나의 variant**가 들어간다. 공통 심볼을 제공하는 모든 대안을 동시에 링크하지 않는다. 여러 소스에서 하나의 unit을 만들고 싶다면 여러 `commands`로 필요한 중간 결과를 만들고 최종적으로 `{object}` 하나를 생성할 수 있다. 생성기·설정·header도 `inputs`에 선언한다.

현재 runner는 서로 다른 component variant의 직교 곱을 만든다. 특정 두 variant의 조합이 원래 호환되지 않는다면 계약이나 component 경계를 먼저 정리하거나 호환되는 조합을 별도 포트폴리오로 나눠야 한다. 자동 constraint solver와 언어 간 adapter 생성기는 포함하지 않는다.

### C/Rust 계약에서 확인할 의미

예시의 scalar ABI는 `uint32_t nv_popcount64(uint64_t)`와 `int32_t nv_square_bonus(uint32_t)`다. Rust 측은 `extern "C"`로 동일한 심볼과 호출 규약을 제공한다. 고정 폭 정수, 입력 범위와 overflow 의미가 맞고 상태·할당·예외가 없도록 작은 문제를 골랐다.

다른 함수에는 pointer aliasing, alignment, lifetime, 소유권, 구조체 layout, float, allocation, TLS·초기화와 unwind가 추가될 수 있다. 이러한 계약은 함수 이름이나 반환값 샘플만으로 확인되지 않는다. 일반 Rust 타입의 layout을 C ABI로 추정하거나 `rlib`를 그대로 C object처럼 다루는 경로는 제공하지 않는다.

### 0.2: unit별 표기를 링크 전에 확정하기

`notation`은 variant와 common unit에서 동일하게 사용한다. 동작 예제는 [manifest-notation.json](../packages/nvcompact/examples/mixed/manifest-notation.json)이다. 기존 예제 manifest의 동작을 바꾸지 않고 별도 파일로 제공한다.

```json
{
  "id": "c_kernel",
  "sources": ["src/kernel.c"],
  "commands": [["{cc}", "-std=c11", "-Os", "-c", "{source}", "-o", "{object}"]],
  "notation": {
    "language": "c",
    "target": "c11-lp64",
    "token_contract": "no-token-observation",
    "compact": true,
    "max_variants": 3
  }
}
```

`language`는 필수이고 나머지는 [NOTATION.md](NOTATION.md)의 기본값을 따른다. `token_contract` 기본값은 `opaque`이므로 생략하면 원본 표기만 유지한다. `compact`는 JSON boolean, `max_variants`는 원본을 포함한 1..32의 정수다. 한 unit의 `sources`는 중복 없는 동일 언어 source 목록이어야 한다. 복수 source에는 같은 recipe ID를 함께 적용하며 파일마다 후보를 곱하지 않는다. Header·generator 등 읽을 dependency는 기존처럼 `inputs`에 선언한다.

실제 처리 순서는 다음과 같다.

1. 원본 snapshot과 기존 `commands`로 원본 object를 정상 생성한다.
2. NVNotation이 원본 source로 제한된 표기 portfolio를 만든다. 원본 snapshot은 바꾸지 않는다.
3. 바뀐 각 recipe마다 **선언한 전체 snapshot**을 별도 `notation/<id>/root/`로 복사한다. 상대 경로와 header 구조를 유지하고 해당 unit source만 후보 bytes로 교체한다.
4. `{root}`, `{source}`, `{sources}`는 이 복사본을 가리키고 `{build}`, `{object}`는 별도 작업 디렉터리를 가리키도록 원래 compile 명령을 다시 실행한다. `{unit_id}`와 build profile·도구는 유지한다.
5. 생성한 **전체 object bytes**를 원본과 직접 비교한다. hash만 비교하거나 section 일부만 비교하지 않는다. 같은 후보 중 source bytes가 가장 작은 표기를 audit의 `selected`로 확정한다. 동률이면 원본을 우선한다.
6. 실제 링크에는 처음의 원본 object를 그대로 사용한다. 후보의 source가 짧다는 이유로 bytes가 다른 object를 링크하지 않는다.

Compile 명령은 선언한 source와 context를 실제로 사용하는 신뢰된 빌드 명령이어야 한다. source 경로를 원래 절대 경로로 하드코딩하거나 snapshot 밖 파일을 읽는 명령을 도구가 자동 수정하지 않는다. `__FILE__`, debug 정보, LTO metadata, include 경로 등 때문에 object가 달라져도 차이를 무시하는 예외를 넣지 않고 후보를 거부한다. 필요하다면 프로젝트가 올바른 prefix mapping과 빌드 로직을 정리하고 새로 실행한다.

원본과 같은 source bytes를 만든 recipe는 `source_identical`로 기록하고 추가 compile하지 않는다. 바뀐 source의 object가 일치하면 `object_byte_identical`, 다르면 `rejected_object_difference`다. compiler 실패는 `failed`, 시간·로그 예산 부족은 `incomplete`로 남기며 원본 object를 보존한다. Candidate build가 원본 snapshot이나 원본 object를 바꾸면 정상적인 후보 탈락으로 숨기지 않고 입력/격리 오류로 중단한다. 격리 복사본의 선언한 입력이 compile 중 바뀌어도 그 후보를 승인하지 않는다.

`objects[].notation`과 각 unit의 `notation/audit.json`에 source 크기·hash·변환 근거·compile 명령·object 비교·거부 사유·선택 결과가 남는다. `notation.search_complete`는 이 opt-in 조사에 지정한 recipe를 끝까지 처리했는지 나타낸다. 바깥 `search_complete`는 기존 링크·완성 파일 조사 범위이며 이 둘을 같은 범위로 해석하지 않는다. `max_variants` 밖의 모든 표기를 조사했다는 뜻도 아니다.

`winner.recipe.json`에는 선택한 unit의 표기 확정 요약을 남긴다. Native 재생성에서는 원본 object를 다시 만들고 기존 native/final bytes와 실행을 검증하며 표기 portfolio를 다시 조사하지 않는다. 표기 후보가 실제 linked object를 대체하지 않았기 때문이다. Source 배포 후보 자체를 재생성·압축하는 작업은 별도 source packing 경로에서 처리한다.

이 단계의 선택 기준은 **동일 object를 만들 수 있는 짧은 source 표기**다. Source를 압축해서 시작 시 compile하는 배포에서는 더 긴 source가 codec에 유리할 수 있으므로, 이 결과만 남기고 raw·다른 표기 후보를 버리지 않는다. NVCompact의 서로 다른 C/Rust 구현 조합과 최종 파일 크기 비교는 기존 절차대로 진행한다.

## 5. build profile

`build_profiles`는 `id`, 선택적인 `variables`와 `requires_tools`를 갖는 비어 있지 않은 목록이다.

```json
[
  {"id": "size", "variables": {"c_opt": "-Os", "rust_opt": "z", "c_lto": []}},
  {"id": "speed", "variables": {"c_opt": "-O2", "rust_opt": "2", "c_lto": []}},
  {"id": "size-lto", "variables": {"c_opt": "-Os", "rust_opt": "z", "c_lto": ["-flto"]}}
]
```

변수는 unit 명령과 링크 명령의 placeholder로 사용한다. 값은 명확한 문자열 또는 argv로 펼칠 문자열 목록을 사용하는 편이 좋다. 프로필 이름은 설명용이며 `speed`가 실전에서 빠르다거나 `size`가 최종 압축 파일을 최소화한다는 판정을 미리 부여하지 않는다.

예시의 `{c_lto}`는 토큰 전체에서 list로 펼친다. 빈 목록이면 아무 인자도 추가하지 않고, `size-lto`에서는 C 컴파일·최종 링크에 GCC LTO를 사용한다. Rust object는 native 상태로 유지하며 GCC GIMPLE과 LLVM bitcode 사이의 직접 상호 LTO를 시도하지 않는다. compiler driver가 GNU ld와 GCC plugin을 연결한다. 자신의 toolchain에서 필요한 추가 옵션은 실제 manifest에서 확인한다.

한 campaign 안의 object 재사용 key는 build profile과 unit identity다. 같은 unit을 여러 링크 조합에서 사용해도 다시 컴파일하지 않지만, 다른 build profile이나 다른 variant는 별도 unit이다. 선택 결과의 독립 재빌드는 이 object 캐시를 재사용하지 않는다.

## 6. link profile과 전용 script

`link_profiles`는 다음 필드로 구성한다.

| 필드 | 의미 |
|---|---|
| `id` | 링크 프로필 이름. |
| `contract` | 링크/runtime/배포에 필요한 전제를 설명하는 metadata. |
| `common` | 선택과 관계없이 이 프로필에서 포함할 unit 목록. unit 형식은 variant와 같다. 생략 가능하다. |
| `argv` | `{objects}`를 링크해서 `{binary}`를 만들 명령. |
| `post_link` | 링크 후 순서대로 실행할 argv 목록. 생략 가능하다. 원본이 의미를 바꾸지 않았는지 검사는 이후 실행한다. |
| `allow_section_header_removal` | 선택적인 배포 변환 허용 여부. JSON boolean만 허용하며 기본값은 `false`다. |
| `requires_tools` | 이 링크 프로필의 직접 argv만으로 드러나지 않는 추가 도구 의존성. |

`common`은 선언 순서대로 먼저 배치하고 그 뒤에 recipe의 component 순서대로 variant object를 배치한다. 현재 `orders`는 common unit 내부 순서를 바꾸지 않는다.

전용 `.ld` 파일은 일반 입력 파일이다. `inputs`에 선언하고 다음과 같이 `argv`에서 참조한다.

```json
["{ld}", "--gc-sections", "--build-id=none", "-T", "{root}/linker/custom.ld", "{objects}", "-o", "{binary}"]
```

GNU compiler driver로 링크할 때는 예제처럼 `-Wl,-T,{root}/linker/hosted.ld`를 사용할 수 있다. script가 실제 입력의 loader·relocation·writable data·TLS·constructor·unwind 조건을 만족해야 한다. 단순히 section을 제거했다는 이유로 같은 의미라고 판정하지 않는다.

예제의 hosted profile은 GNU default script를 보완한다. compact profile은 no-runtime에 가까운 작은 Linux x86-64 예제의 제한된 contract를 가진다. 일반 프로그램의 `.eh_frame`, initialization, GOT/PLT 등을 설명 없이 버리는 template가 아니다. LTO 객체를 다른 compiler의 linker/plugin과 호환된다고 자동 가정하지 않는다.

### `allow_section_header_removal`

`true`는 다음 전제를 사용자가 선언하는 것이다.

- 실행·배포 계약이 자기 파일 bytes와 section-header table을 관측하지 않는다.
- 수정하는 ELF metadata를 코드나 데이터로 재사용하지 않는다.
- section 기반 도구가 그 최종 파일에 필요한 배포 기능이 아니다.
- 현재 변환기가 지원하는 ordinary ELF64LE x86-64 구조다.

변환기는 ELF/program/section header의 기본 구조와 범위를 확인하고, 모든 program-header file extent를 보존한다. extended numbering 등의 비지원 입력은 추측하지 않는다. semantic 전제를 소스나 binary에서 자동 증명하는 기능은 없다.

배포 후보 ID는 `original`과 `no-section-headers`다. 전제를 만족하지 않으면 flag를 끄거나 해당 요구를 지원하도록 배포 프로필의 근본 로직을 수정한다. 특정 파일 hash를 예외 처리해서 같은 변환의 성공인 것처럼 보고하지 않는다.

## 7. 객체 배치 순서와 baseline

`orders`의 각 항목은 `id`와 `components` 목록을 가진다. 목록에는 모든 component가 정확히 한 번씩 있어야 한다. 생략하면 component 선언 순서를 사용하는 `declared` 순서 하나를 만든다.

```json
[
  {"id": "declared", "components": ["popcount", "square"]},
  {"id": "reverse", "components": ["square", "popcount"]}
]
```

이 필드는 명시한 object 배치를 비교한다. linker script의 section 정렬, compiler가 만든 함수 순서 또는 모든 가능한 기계어 배치를 자동으로 열거한다는 뜻은 아니다.

`baseline`은 시작 시 먼저 빌드하고 최종 checker로 확인할 명시적인 recipe다.

```json
{
  "build": "size",
  "link": "hosted",
  "order": ["popcount", "square"],
  "variants": {"popcount": "c_kernighan", "square": "c_arithmetic"}
}
```

`build`와 `link`는 존재하는 프로필 ID여야 한다. `order`와 `variants`에는 각 component를 빠짐없이 지정한다. baseline은 CLI의 후보 탐색 필터와 독립적으로 검사한다. baseline의 output을 자동으로 정답 oracle로 사용하지 않으며, 그 baseline 역시 사용자가 제공한 `verify_final`의 검사를 통과해야 한다.

## 8. native·완성 파일 checker

`verify`는 필수 argv 명령이고, `verify_final`은 선택 사항이다. 후자를 생략하면 최종 검사에도 `verify`를 사용한다.

```json
{
  "verify": ["{python}", "{root}/examples/mixed/verifier.py", "--binary", "{binary}", "--quick"],
  "verify_final": ["{python}", "{root}/examples/mixed/verifier.py", "--binary", "{binary}"]
}
```

`verify`는 링크 직후 native 파일과 각 배포·압축 완성 파일에 적용한다. `verify_final`은 baseline과 독립 재빌드한 최종 선택 파일에 적용한다. checker는 `{binary}`의 실제 파일을 실행해야 하며, 압축 후보라면 wrapper를 포함한 경로가 전달된다.

프로세스 exit 0을 검사 성공으로 받아들이고 stdout/stderr를 로그에 남긴다. runner가 특정 JSON report를 해석해 semantic proof를 합성하는 것은 아니다. 예제 checker는 corpus·oracle hash와 수행한 범위를 보고하지만 다른 프로젝트는 해당 계약에 맞는 checker를 제공할 수 있다. checker가 파일 bytes를 바꾸면 오류로 처리한다.

검사 범위에는 필요한 input/output, 오류 처리, 상태 변화, ABI·실행 조건을 포함한다. codec roundtrip은 압축에 넣은 bytes가 복원된다는 확인이며 소스 변환의 동등성과 구분한다. 현재 runner는 모든 후보를 더 강한 `verify_final`로 재검사하지 않고, 최소 screening 후보를 먼저 선택한 뒤 그 하나를 독립 재빌드·최종 검사한다. 거기서 실패하면 winner를 게시하지 않는다.

## 9. codec 선택

`codecs`에는 family 이름이나 exact candidate ID를 지정한다. 생략하면 packer의 기본 family와 대상에 맞는 BCJ 후보를 사용한다. 빈 목록이면 raw만 만든다. 어느 경우든 `raw`는 한 번 포함된다.

| family | exact ID |
|---|---|
| `raw` | `raw` |
| `gzip` | `gzip-1`, `gzip-9` |
| `zlib` | `zlib-1`, `zlib-9` |
| `bzip2` | `bzip2-1`, `bzip2-9` |
| `xz` | `xz-0`, `xz-6`, `xz-9` |
| `xz-bcj` | `xz-bcj-0`, `xz-bcj-6`, `xz-bcj-9` |
| `lzma` | `lzma-0`, `lzma-6`, `lzma-9` |

명시한 순서는 안정적으로 유지하고 중복 요청은 합친다. 명시적으로 지원하지 않는 ID를 요청하면 오류다. x86 BCJ는 선언한 x86-64 Linux 대상과 ELF header가 맞을 때 적용한다. 비지원 대상에서 명시한 BCJ 요청을 조용히 건너뛰지 않는다.

압축기 설정과 container 정보는 packer recipe에 남는다. gzip timestamp·filename을 고정하고, XZ는 CRC32, zlib은 Adler-32 framing을 사용한다. LZMA-alone은 별도 container checksum이 없지만 생성 시 원래 bytes와 정확하게 roundtrip 확인한다. 최종 제출 파일의 무결성 근거는 별도로 SHA-256에 기록된다.

실제 선택은 payload 길이가 아닌 loader가 포함된 파일 길이로 한다. native file 자체가 매우 작으면 raw가 이기는 것도 정상이다. decoder와 실행 환경의 요구는 후보의 `requirements`에 남으며, raw와 Python memfd script는 서로 다른 deployment 의존성을 가진다.

## 10. CLI 필터와 조사 범위

| 인자 | 현재 동작 |
|---|---|
| `--profile ID` | 탐색할 build profile. 여러 번 지정 가능. |
| `--link-profile ID` | 탐색할 link profile. 여러 번 지정 가능. |
| `--max-candidates N` | 명시한 product 순서에서 최대 N개의 링크 recipe를 선택. 기본 128. |
| `--jobs N` | 동시에 처리하는 링크 recipe 작업 수. 기본 2. |
| `--max-seconds S` | campaign 명령 실행과 각 codec 시작 전에 확인하는 예산. 기본 600초. 독립 재빌드에 별도 campaign 예산을 부여한다. |
| `--command-seconds S` | 외부 명령 하나의 최대 실행 시간. 기본 30초. |
| `--max-log-bytes N` | 외부 명령 stdout/stderr 합계의 감시 상한. 기본 1 MiB. |
| `--out DIR` | 새로 만들 결과 디렉터리. 기존 경로는 거부한다. |
| `--tool NAME=EXECUTABLE` | manifest 도구 별칭의 실행 파일 override. |

후보 열거는 build profile, link profile, `orders`, component별 variant 목록의 순서를 사용한다. `--max-candidates`는 이 순서의 앞부분을 선택하는 상한이며 무작위·beam·Bayesian 탐색은 아니다. 따라서 작은 상한을 적용한 결과를 나머지 조합까지 조사한 것처럼 해석하지 않는다. 작업의 완료 순서는 동률 선택 순서를 바꾸지 않는다.

`--jobs`는 compiler 내부 스레드까지 합친 총 CPU quota가 아니며 native 엔진의 Threads 옵션과도 다르다. 같은 campaign에서 공통 객체를 재사용해도 final artifact 검사가 생략되었다는 뜻은 아니다. Python 내부 압축·snapshot 복사는 외부 명령과 동일한 hard timeout으로 즉시 선점되지 않는다. 매우 큰 입력이나 강한 리소스 격리가 필요한 실행은 별도 환경 관리가 필요하다.

## 11. report와 recipe의 해석

`report.json`에는 runner/runtime, 입력 hash, tools의 executable·hash·version, 실제 환경, 예산, baseline, 후보별 build/link 선택, native bytes·hash, artifact별 bytes·hash·requirements·검사 결과가 남는다.

후보의 상위 `status=completed`는 recipe 처리가 끝났다는 뜻이다. 그 아래 모든 artifact가 의미·실행 검사를 통과했다는 뜻이 아니다. 각 artifact의 `status`를 별도로 읽는다.

- `screened`: 후보 checker와 선언한 파일 크기 조건을 통과했다.
- `over_size_limit`: 후보 checker는 통과했지만 최종 파일 크기 상한을 넘었다.
- `failed`: 해당 명령·검사에 실패했다. phase와 오류·로그를 확인한다.
- `incomplete`: timeout, log limit 또는 campaign budget으로 처리를 완료하지 못했다.
- `internal_error`: 도구 내부나 지원 전제 처리에서 예외가 기록됐다. 정상적인 크기 비교의 패배로 바꾸지 않는다.

`search_complete`는 선택한 링크 recipe 수가 현재 필터의 계획 수와 같고, 모든 상위 recipe가 완료됐으며 하위 artifact에 `incomplete`가 없는지를 나타낸다. 이 값은 의미 검사에 실패한 모든 artifact가 없다는 뜻이 아니다. 모든 구현이 같은 의미라는 판정이나 manifest 밖의 전역 최적성도 나타내지 않는다.

선택 기준은 **실제로 검사까지 완료한 screened artifact 중 완성 bytes의 최솟값**이다. recipe의 상태가 `completed` 또는 `incomplete`이면 그 안에서 이미 완료한 screened 파일을 비교할 수 있다. 후속 codec의 예산 부족이 앞서 끝낸 파일의 검증을 없애지는 않는다. recipe 자체가 `failed` 또는 `internal_error`인 경우는 이 선택 집합에서 제외한다. 동률은 candidate ID, artifact ID로 결정한다. 선택한 파일만 독립 재빌드하여 native hash·artifact hash·실제 bytes와 최종 checker를 확인한다. 성공한 경우에만 top-level `accepted`, `winner`, `winner.recipe.json`이 생긴다. 다른 screened artifact의 `reproduction=not_run`은 그대로 남는다.

`winner.recipe.json`은 선택한 build/link·variant·order, 배포 변환 ID, exact pack ID, 입력 snapshot과 tool/runtime 근거를 담는다. 전체 project와 입력 hash는 보존하고 `tools`에는 선택 recipe의 도구 의존성만 담는다. 파일만 복사해서 재생성하려 하지 말고 recipe가 참조하는 `snapshot/`을 함께 보존한다. 다른 파일 시스템 위치로 옮겨도 필요한 입력 구조와 도구가 맞아야 하며 절대 build 경로에 의존하는 생성 로직은 독립 재빌드에서 드러날 수 있다.

별도 `reproduce`는 후보 탐색 없이 이 선택을 다시 만들고 `reproduction.json`에 `byte_identical` 또는 실패 근거를 남긴다. runner 소스·버전, 직접 사용하는 `nvpack.py`·`nvelf.py`·`nvnotation.py`, Python과 zlib의 재현성 fingerprint, 입력, 필요한 도구의 내용·version을 확인한다. 커널·플랫폼 설명은 근거로 기록하며 그 문자열의 동일성 자체를 gate로 사용하지 않는다. 실제 대상의 실행과 완성 bytes는 다시 확인한다. 사전 확인에서 실패하면 새 출력 디렉터리를 만들기 전에 종료할 수도 있다. 이전 winner와 recipe는 덮어쓰지 않는다.

재현되지 않은 결과의 hash를 갱신하거나 checker를 우회해서 맞추지 않는다. 실제 계약과 toolchain 환경을 기준으로 원인 로직 또는 잘못된 일반 전제를 수정한 다음 새로운 실행을 기록한다. codec의 단순 미적용 조건, 유효하지만 큰 후보, 검증 실패와 탐색 미완료는 서로 다른 결과다.
