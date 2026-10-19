# TCEC 4K 외부 예제와 비교 기준

확인일: 2026-10-19. 비교 입력은 **일반 4K 공개 예제 11개**와 **별도로 표시한 ELF 공개 예제 2개**다. 현재 대회의 모든 제출 파일을 확보했다는 뜻은 아니다. 저장소에는 입력의 출처·해시·크기·실행 계약만 두며, 엔진 소스·압축된 소스·실행 파일·소스 아카이브를 포함하지 않는다.

## 두 부문의 측정 경계

[공식 규칙 revision 7853](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853)에 따르면 두 부문 모두 제출 파일은 최대 4096바이트다. 일반 부문은 허용된 외부 도구를 쓰는 스크립트 또는 실행 파일을 받지만, ELF 부문은 외부 프로그램을 실행하지 않는 ELF를 요구한다. 시작은 60초 이내여야 하며 엔진이 파일을 남겨서는 안 된다. 파일명에 엔진 정보를 숨길 수 없고, 옵션으로 전달하는 엔진 코드는 용량에 포함된다. 실제 Hash/Threads 설정은 별도로 취급된다.

일반 부문의 명시적 명령 목록은 `bzip2 bash c++ cargo cc clang chmod gzip lzma mktemp perl python python3 pypy3 rustc sh sleep tail xz`다. 시스템 라이브러리, CUDA/OpenCL, NumPy는 허용되지만 python-chess는 제출 파일에 포함해야 한다. ELF 부문은 x86-64 로더와 libc, libdl, libgcc_s, libm, libpthread, libstdc++의 지정 경로만 열거한다. liblzma·libbz2·libzstd는 이 ELF 목록에 없다. 그 밖의 허용 여부는 주최 측 판단이다.

공식 예제의 `rm`, 일부 공개 엔진의 `g++`·`unxz`처럼 명시 목록과 실제 예제가 다른 부분도 기록한다. 원본이 사용했다는 사실만으로 NVCompact가 대회 허가를 발급하지는 않는다. 개발 도구에 연결한 압축 라이브러리와 제출물의 실행 의존성도 구분한다.

이번에 전체 원본과 측정 최소 파일의 launcher를 직접 읽은 결과는
[엔진별 명령·정리 검토](../evidence/0.4/launcher-rule-review.json)에 있다. 일반 입력 중
10개 shell 원본과 그 최소 후보가 모두 `rm`을 사용한다. 그 외 명시 목록 밖의 토큰은
4ku·c4ke의 `g++`, Moonfish 원본의 `unxz`, PyGone의 복원된 script shebang에 있는
`env`다. Moonfish 최소 후보는 `xz`를 사용하지만 다른 미확정 명령의 허가까지 해결하지는
않는다. `exec`와 `exit`는 검토한 shell의 builtin으로 외부 도구 목록과 구분했다.

정리 방식은 대부분 `mktemp`로 만든 파일을 지연 삭제하는 구조이며, Sunfish는 interpreter가
반환한 뒤 삭제한다. 이 정적 검토는 삭제 의도를 확인한 범위다. 실제 실행에서 관측한 시작·종료와
소유 임시 디렉터리 정리는 별도 증거이고, 모든 signal 경로·컴파일러 자식·동적 라이브러리·전역
파일시스템을 감사했다는 뜻이 아니다. metadata에는 명령 토큰과 header 크기·해시만 기록하고
upstream header 원문은 저장하지 않는다.

## 확보한 공개 입력

다음 숫자는 전체 원본 파일 크기와 **과거 Python v0.2가 관측한 최소 크기**다. 과거 최소값은 새 Rust 결과도, 당시 모든 엔진이 실행 검사를 통과했다는 뜻도 아니다. 새 결과는 같은 해시·같은 부문·같은 설정으로 별도 측정한다. 각 이름의 링크에 전체 SHA-256과 고정된 출처가 있다.

| 일반 4K 입력 | 공개 버전·형태 | 원본 B | 과거 최소 B | 비교의 중요한 제한 |
|---|---|---:|---:|---|
| [ice4](../comparisons/general/ice4.json) | v6.1 TCEC 소스 압축 스크립트 | 4087 | 4082 | 최신 표기 6.1.1과 동일 파일임을 확인하지 못함; 256 GiB·256 workers |
| [4ku](../comparisons/general/4ku.json) | v5.1 mini 소스 압축 스크립트 | 4093 | 4088 | 공개 mini는 1 worker·64 MiB; 같은 버전명이 서버 설정까지 보증하지 않음 |
| [STRO4K](../comparisons/general/STRO4K.json) | v5.0 TCEC ELF 압축 스크립트 | 4096 | 4078 | 일반 부문용 래퍼; ELF 제출 파일이 아님; 256 GiB·509 workers·AVX-512 VAES |
| [4k.c](../comparisons/general/4k.c.json) | v9.0 자체 복원 ELF | 3932 | 3932 | LOAD 가상 영역 22 GiB; 이 환경에서 커널의 실행 매핑 허가가 실패함 |
| [c4ke](../comparisons/general/c4ke.json) | v3.0 TCEC 소스 압축 스크립트 | 4093 | 4092 | 256 GiB·256 workers |
| [pygone](../comparisons/general/pygone.json) | 2-11b142 역사 파일 | 4093 | 4020 | 실제 대응 commit은 `11bf1426…`; PyPy 포인터 테이블만 최소 1 GiB |
| [sunfish](../comparisons/general/sunfish.json) | 2022-12-24 classic | 2844 | 2776 | 고정 소스로 payload를 재현했지만 비공개 대회 업로드와의 일치는 독립적으로 확인되지 않음 |
| [moonfish](../comparisons/general/moonfish.json) | 작성자 사이트의 무버전 스크립트 | 3941 | 3889 | 역사 버전 `4aa32a0c` 대응 미확인; 원본 decoder 실패와 후보 실행을 구분 |
| [M4sseur](../comparisons/general/M4sseur.json) | v1.0 고정 소스에서 원래 빌드 재현 | 4095 | 4092 | 공개 release 파일 없음; 64 GiB 초기화·103 workers |
| [molly](../comparisons/general/molly.json) | `e317a0c7b8` 원래 빌드 재현 | 4096 | 4095 | 실제 대회 소스 commit이지만 비공개 제출 파일과 동일함을 보증하지 않음; 96 GiB·101 workers |
| [we4k](../comparisons/general/we4k.json) | `93dde6ad` 공개 기본 설정 재현 | 4079 | 4011 | 공개 기본 4 workers·32 MiB는 역사 대회의 104 workers·64 GiB와 다른 입력 |

자원 숫자는 출처에서 확인한 큰 할당·설정이다. 실제 peak RSS나 기력 측정값으로 바꾸어 읽지 않는다. 특히 ELF의 `p_memsz`는 가상 주소 영역이다. 4k.c v9.0의 더 작은 소스 기본 설정을 release 파일의 실제 물리 메모리 요구량이라고 단정하지 않는다.

| ELF 비교 입력 | 원본 B | 용도와 제한 |
|---|---:|---|
| [4k.c-v9.0](../comparisons/elf/4k.c-v9.0.json) | 3932 | 공개 v9.0 ELF; 최신 ELF 대회 9.15.1의 대체 파일이 아님 |
| [4k.c-v8.0](../comparisons/elf/4k.c-v8.0.json) | 4042 | 추가 역사 공개 ELF; LOAD 영역 256 MiB, 최신 제출 파일의 결과로 합산하지 않음 |

[공식 현재 상태](https://wiki.chessdom.org/Current_Engine_Status)는 ELF의 4k.c 9.15.1과 STRO4K 6.0을 표시한다. 확인한 공개 release는 각각 v9.0과 v5.0까지다. STRO4K 공개 branch 469개도 검사했으나 이름으로 식별되는 6.0/ELF branch를 찾지 못했다. 이 검색 범위 밖의 모든 미러가 없다는 주장은 하지 않는다. 최신 파일 미확보는 [입력 카탈로그](../comparisons/metadata/artifacts.json)의 별도 항목으로 남긴다.

과거 ELF I의 4k.c 1.10/LESS_STRO4K 4.0, ELF II의 4k.c 5.8/LESS_STRO4K 5.0, ELF III의 4k.c 9.15.1/STRO4K 6.0은 [공식 PGN 출처 목록](../comparisons/metadata/event-roster.json)에서 확인한다. 참가자 명단은 제출 바이트를 제공하는 증거와 다르다.

## 외부 입력 배치와 압축 실행

`comparisons/general/`과 `comparisons/elf/`의 JSON은 입력 파일을 다운로드하거나 포함하지 않는다. `name`과 `artifact_key`가 외부 디렉터리 안의 파일 이름이다. 각 입력을 공개 artifact URL에서 받거나, 고정 소스와 원래 빌드 절차로 재현한 뒤 그 이름으로 배치한다. 실행 전에 manifest의 전체 해시가 강제로 확인된다. 재현 결과가 다르면 먼저 도구·입력·빌드의 원인을 확인하며 기대 해시를 출력에 맞춰 고치지 않는다.

아래 경로 변수는 사용자가 준비한 **저장소 밖**의 디렉터리와 고정된 NVCompact 실행 파일을 뜻한다. shell header는 manifest에 복사하지 않고 `header_bytes`와 `header_sha256`으로 외부 파일의 해당 영역을 확인한다.

```sh
NVC_BIN=/path/to/nvcompact
NVC_INPUTS=/path/to/external/tcec-inputs
NVC_RESULTS=/path/to/external/new-results

"$NVC_BIN" engines \
  --manifests tools/nvcompact/comparisons/general \
  --artifact-root "$NVC_INPUTS" \
  --output "$NVC_RESULTS/general" --jobs 2 --thorough

"$NVC_BIN" engines \
  --manifests tools/nvcompact/comparisons/elf \
  --artifact-root "$NVC_INPUTS" \
  --output "$NVC_RESULTS/elf" --jobs 2 --thorough
```

ELF 입력은 `4k.c-v9.0`, `4k.c-v8.0`이라는 별도 이름으로 준비한다. 일반 부문의 `4k.c`와 v9.0 ELF 입력은 원본 해시가 같다. 부문별 후보 제약은 다르다. ELF 부문에서는 shell loader로 감싼 결과를 작은 ELF로 채택할 수 없다. 이 두 공개 ELF는 header에 코드가 겹치는 형태이므로 일반적인 section-header 제거도 허용하지 않았다.

기본 압축 명령은 크기·복원·후보 재현 검사를 수행한다. 이것을 실제 엔진 실행 결과로 보고하지 않는다. `--uci`를 더하면 유한 프로토콜 검사도 요청하지만, 큰 원래 자원 설정은 별도의 계획/시작 경로로 보낸다. [resource 예제](../comparisons/resource-examples/)는 그런 계획의 출발점이며 호스트 용량 보증이 아니다.

## UCI와 자원 계획

TCEC 최소 프로토콜 검사는 시작/ready, 명령 허용, 여섯 가지 `startpos moves` 이력, clocked `go`, 합법적인 `bestmove`, 종료와 정리를 확인한다. 이력에는 캐슬링·앙파상·승격이 포함된다. 독립적인 cozy-chess 판정기는 NVCompact 개발 도구에만 연결되며 제출물에 들어가지 않는다. 전체 UCI 확장은 별도 선택이다.

기본값은 엔진의 Hash/Threads와 내장 상수를 보존한다. 검사기가 작은 Hash를 자동 설정하거나 CPU 수를 줄여 놓고 원래 TCEC 설정을 실행했다고 주장하지 않는다. 2초 등 짧은 clock 입력과 공식 `1,800,000 ms + 3,000 ms` 입력도 다른 증거로 남긴다. 공식 숫자를 보낸 여섯 위치의 검사는 전체 대국·TCEC 서버 인증·Elo 측정이 아니다.

`case_ids`로 일부 이력만 선택하면 요청/완료 목록과 전체 corpus 포함 여부를 함께 기록한다. 예를 들어 공식 clock의 한 위치만 실행한 결과를 여섯 위치 성공으로 바꾸지 않는다. 제공한 clock이 끝나기 전에 검사기의 관측 예산이 끝나면 `incomplete`다. 이는 엔진의 시간패나 TCEC 프로토콜 결함의 증거가 아니다.

```sh
"$NVC_BIN" resource plan /path/to/external/prepared-spec.json \
  --output "$NVC_RESULTS/plan.json"

"$NVC_BIN" resource run "$NVC_RESULTS/plan.json" \
  --output "$NVC_RESULTS/run" --start
```

계획 단계는 엔진·컴파일러·할당 probe를 실행하지 않는다. 입력·실제 executable·선언 도구·검사기 자신을 fingerprint하고 현재 물리 메모리, 보이는 cgroup 계층과 상속된 limit을 읽는다. 실행 단계는 명시적 `--start`, 계획 checksum과 현재 입력/자원 재확인을 요구한다. 부족하거나 바뀐 입력은 `blocked`로 남긴다. engine option 변경, 상위 process limit 인상, 부모 환경 수정은 이 문제의 우회책이 아니다.

명령 이름뿐 아니라 실제 해석된 도구도 보존한다. 예를 들어 PyPy 배포의 bin 디렉터리를 PATH
앞에 놓으면 `pypy3`뿐 아니라 그 디렉터리의 `python3`도 선택될 수 있다. 이런 관측은 PyPy
profile로 표시하고 기본 `python3`의 CPython 관측과 구분한다. 같은 interpreter의 메모리 제한을
높여 재검사한 결과는 원본 엔진 상수를 줄인 결과와도 다르며, 앞선 실패를 별도로 보존한다.

프로세스당 AS/CPU/file limit, 전체 검사 wall limit, 세션별 출력 limit과 소유 process group 정리를 사용한다. 메모리 관측은 예약이 아니며, 실제 자식 전체를 묶는 새 memory cgroup을 만드는 기능도 아니다. 부모와 다른 세션으로 이탈한 프로세스나 전역 파일시스템까지 감사했다고 주장하지 않는다.

## 크기·의미·제출 적합성의 별도 판정

목표는 같은 입력에서 `후보 전체 바이트 ≤ 원본 전체 바이트`이며, Rust 이식에는 `후보 전체 바이트 ≤ 과거 동일 입력 최소 바이트`도 적용한다. 원본 identity 후보는 첫 조건의 안전망이고 추가 압축 이득은 0바이트다. 절감률은 `(원본−후보)/원본`으로 보고한다. 기존 출력보다 커졌다면 원인을 수정하며 과거 기준을 느슨하게 바꾸지 않는다.

압축 source가 더 짧아져도 컴파일된 ELF가 같을 수 있다. 전처리·컴파일·최적화가 그 표현 차이를 같은 기계 코드로 만들기 때문이다. 링커가 C의 의미를 무시하거나 임의의 동등 알고리즘을 같은 코드로 치환한다는 뜻은 아니다. 압축 source를 제출하는 일반 부문에서는 **최종 ELF가 같더라도 source payload 압축이 개선될 수 있다.** ELF 부문은 제출하는 ELF의 전체 바이트가 기준이다.

복원 payload 일치, 고정 compile recipe의 전체 결과 일치, 선택 recipe 재실행 일치, 실제 UCI 성공, 외부 명령/라이브러리 검토, 원래 비공개 제출 파일과의 일치는 각각 기록한다. 특히 과거 4k.c의 UCI 실패, Moonfish의 원본 decoder 실패와 후보 성공은 보존한다. 최소 크기를 찾았다는 이유만으로 모든 항목을 통과 처리하지 않는다.
