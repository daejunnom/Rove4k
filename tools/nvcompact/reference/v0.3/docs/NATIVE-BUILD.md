# 압축 없이 컴파일·링크하기

`nvcompact build`는 매니페스트에 선언한 구현·컴파일·링크 조합을 만들어 **링크 산출물 자체의 bytes**로 비교한다. 기본 실행은 생성한 프로그램을 검사 목적으로 시작하지 않는다. 가장 작은 완료 산출물을 새 소스 디렉터리에서 다시 빌드하여 bytes가 일치하면 `winner`와 recipe를 남긴다.

NVCompact의 소스 표기 감사, ELF section-header 제거, codec과 실행 wrapper를 적용하지 않는다. 컴파일러 옵션과 전용 linker script는 매니페스트에 선언한 그대로 사용할 수 있다. `post_link`가 있으면 그것도 사용자가 명시한 빌드 명령으로 실행하며, 그 명령까지 끝난 산출물을 보존한다. 명령 안에서 별도 압축기나 프로그램을 실행하도록 선언한 경우까지 도구가 자동으로 분석·제거하지는 않는다.

## 바로 실행할 수 있는 C 예제

모노레포 루트에서는 다음 명령을 사용한다. 아직 존재하지 않는 결과 디렉터리를 지정한다.

```sh
npm exec -- nvcompact build \
  packages/nvcompact/examples/native-build/manifest.json \
  --out runs/native-01 --jobs 2
```

별도 프로젝트에 npm 패키지를 설치했다면 예제 경로를 `node_modules/nvcompact/examples/native-build/manifest.json`으로 바꾼다. Python 코어를 직접 실행할 수도 있다.

```sh
python3 packages/nvcompact/python/nvcompact.py build \
  packages/nvcompact/examples/native-build/manifest.json \
  --out runs/native-python-01 --jobs 2
```

[예제 매니페스트](../packages/nvcompact/examples/native-build/manifest.json)는 C 곱셈 구현과 반복 덧셈 구현을 두 개의 컴파일 설정으로 조합한다. Linux x86-64와 GNU C compiler를 대상으로 하며, 입력 범위 0~255의 제곱을 계산하는 작은 프로그램을 링크한다. 일반 C runtime과 ELF section table이 유지된다. 여기서 나온 크기·속도를 체스 엔진의 기력이나 다중 코어 성능으로 확대하지 않는다.

## 실행 검사는 매번 명시적으로 시작한다

기본 `build`에는 `verify`와 `baseline`이 없는 간단한 매니페스트도 사용할 수 있다. 필요한 소스·header·script를 `inputs`에 선언하고, 실제 컴파일·링크 명령과 도구를 지정한다. 명령의 경로와 입력이 잘못되었거나 빌드가 실패하면 오류를 기록한다.

`build --verify`를 지정하면 기존 native portfolio의 baseline 검사와 후보별 checker, 선택 파일의 독립 재빌드·최종 checker를 실행한다. 이때에는 매니페스트에 `verify`와 명시적인 `baseline`이 필요하다. `verify_final`은 생략하면 `verify`를 사용한다.

```sh
npm exec -- nvcompact build \
  packages/nvcompact/examples/native-build/manifest.json \
  --out runs/native-checked-01 --jobs 2 --verify
```

checker는 생성된 프로그램을 실제 실행할 수 있다. 메모리가 큰 엔진에는 필요한 자원과 실행 조건을 먼저 확보하고 그 실행을 명시적으로 시작한다. `build` 자체는 컴파일러·링커·매니페스트의 빌드 명령을 실행하므로, 신뢰하는 프로젝트 명령을 사용해야 한다. `--verify`의 부재를 임의 빌드 스크립트에 대한 보안 sandbox로 해석하지 않는다.

별도 고메모리 검사는 [자원별 실행 안내](RESOURCE-TESTING.md)를 따른다. `nvcompact resource plan`은 엔진을 시작하지 않고 계획을 만들며, 실제 실행은 `nvcompact resource run ... --start`로 구분한다.

## recipe와 재현

native recipe에는 `packing: "none"`, `deployment: "linked"`, `pack: "none"`과 실제 입력·빌드 도구·산출물 hash를 기록한다. 재현에서도 이 경로를 사용하며 codec이나 배포 변환을 거치지 않는다.

```sh
npm exec -- nvcompact reproduce runs/native-01/winner.recipe.json \
  --out runs/native-replayed-01
```

**native recipe의 `reproduce`도 기본은 bytes 재현만 수행한다.** 처음에 `build --verify`로 만들었던 recipe여도 새 `reproduce` 호출에서 프로그램을 자동 실행하지 않는다. 그 호출에서도 최종 checker를 실행하려면 `--verify`를 붙인다.

```sh
npm exec -- nvcompact reproduce runs/native-01/winner.recipe.json \
  --out runs/native-replayed-checked-01 --verify
```

처음 `build`에서 checker를 실행하지 않았다면 나중의 `reproduce --verify`가 checker 전용 도구를 처음 요구할 수 있다. 그 도구는 해당 실행에서 확인·기록하고, 처음 실제 사용한 빌드 도구의 fingerprint는 그대로 대조한다. 반대로 bytes만 재현할 때는 사용하지 않는 checker 런타임을 요구하지 않는다.

기존 `run`에서 만든 압축 portfolio recipe는 기존처럼 재현 시 최종 checker를 실행한다. native의 실행 선택을 과거 압축 recipe의 검증 완화로 적용하지 않는다. 다른 소스 경로에서 bytes가 달라지면 빌드 입력·도구·환경·생성 로직의 원인을 고친다. 기대 hash를 새 출력에 맞추어 바꾸지 않는다.

## 결과를 구분해서 읽기

| 결과 | 의미 |
|---|---|
| `report.status = built` | 컴파일·링크와 선택 파일의 독립 bytes 재현이 완료됐다. 프로그램 실행 검사는 수행하지 않았다. |
| `verification.status = not_run` 또는 recipe의 `verification = not_run` | 실행 검사를 요청하지 않은 상태다. 동등성 통과를 뜻하지 않는다. |
| `report.status = accepted` | 명시적으로 요청한 baseline·후보·최종 checker와 bytes 재현이 통과했다. 실제 checker의 범위로 해석한다. |
| `reproduction.status = byte_identical` | 선택 recipe의 새 빌드 bytes가 일치했다. 실행 검사 여부는 별도의 `verification`에서 확인한다. |
| `failed`, `incomplete`, `internal_error` | 해당 실패·예산 부족·내부 오류가 기록된다. 다른 성공이나 미검증 상태로 바꾸지 않는다. |

기본 `build`는 완료한 링크 파일 중 bytes가 작은 파일을 선택한다. 선언한 서로 다른 구현이 실제로 같은 의미인지 자동으로 보장하지 않는다. `--verify`를 사용하면 checker를 통과한 후보에서 선택한다. 선택 파일의 더 강한 최종 검사나 독립 재현에서 실패하면 실패로 끝나며, 다른 후보를 조용히 승격하지 않는다.

`winner`는 선택한 실제 링크 산출물이다. 비교 원본은 `report.winner.artifact`에 기록된 `candidates/.../native`이며, `winner` bytes와 동일하다. recipe와 `snapshot/`은 함께 보존해야 한다.

## 크기·작업 범위와 의존성

`build`는 압축 제출 파일용 `manifest.max_bytes`를 사용하지 않는다. raw 파일 크기를 제한하려면 명시적으로 지정한다.

```sh
npm exec -- nvcompact build \
  packages/nvcompact/examples/native-build/manifest.json \
  --out runs/native-limited-01 --max-bytes 32768
```

`max_native_bytes`는 객체·링크 출력의 파일 크기 한도로 계속 적용한다. `--profile`, `--link-profile`, `--max-candidates`, `--jobs`, 시간·로그 예산과 `--tool`은 기존 native runner와 같은 의미다. 컴파일러 내부의 모든 스레드와 메모리를 `--jobs` 하나로 제한하는 기능은 아니다.

기본 native build는 선택한 compile/link 명령에 실제 필요한 도구의 의존성만 확인한다. 선택 범위 밖의 Rust compiler나 실행하지 않는 verifier만을 위한 Python 경로가 없어도 해당 C 빌드를 만들 수 있다. 검증을 요청한 실행에는 그 checker와 baseline에 필요한 도구도 포함한다.

native bytes 재현에는 실제 실행하는 `nvcompact.py`, Python, 선택한 입력과 빌드 도구를 기록한다. 호출하지 않는 표기·ELF 변환·압축 모듈이나 codec 구현의 변경을 native recipe의 재현 조건으로 강제하지 않는다. npm 런처의 버전과 실행 어댑터는 패키지 및 런처 진단 기록에서 별도로 확인한다.

소스 축약을 먼저 수행하고 싶다면 검토한 생성 소스를 새 입력으로 선언한 뒤 이 `build` 경로에 전달할 수 있다. 생성 소스의 의미 보존, native 파일의 bytes 재현, 실행 검사의 통과는 서로 다른 근거다. `build`가 호출하지 않은 소스 생성기를 대신 검증했다고 보고하지 않는다.
