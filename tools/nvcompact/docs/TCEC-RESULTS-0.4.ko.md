# NVCompact 0.4 — 실제 공개 TCEC 4K 파일 비교

측정일: 2026-10-19. 운영 구현은 Rove4k 내부의 Rust 0.4.0이다.
이 문서는 **제출하는 단일 파일의 전체 바이트**를 기준으로 일반 4K와 4K ELF를
별도로 비교한다. 압축 전 소스 길이, 복원 후 실행 파일 길이, 개발 도구 자체의
크기를 제출 크기로 대신하지 않는다.

## 입력과 판정 범위

일반 부문 입력은 공개 예제 11개이며, ELF 부문 입력은 공개 4k.c release 두 개다.
일반의 4k.c와 ELF v9.0은 같은 원본 바이트지만 부문별로 허용하는 후보가 다르다.
we4k와 STRO4K는 같은 계보이므로 11개 입력을 11개의 독립 엔진 계보라고 부르지 않는다.
공개 원본 파일이 있는 경우 이를 사용했고, 소스에서 원래 빌드로 만든 경우에는
고정 commit·도구·해시와 그 사실을 별도로 기록했다.

최신 비공개 TCEC 업로드를 모두 확보한 것은 아니다. 예를 들어 ice4의 공개 입력은
6.1이고 기록된 대회 버전은 6.1.1이다. 공개 4ku와 we4k의 기본 메모리·스레드 설정도
역사 대회 설정과 다르다. 이를 조용히 고쳐 같은 입력으로 취급하지 않았다.
전체 출처와 대응 관계는 [예제 기준](TCEC-EXAMPLES.md)과
[입력 카탈로그](../comparisons/metadata/artifacts.json)에 있다.

크기 목표는 각 입력마다 다음 두 조건이다.

1. Rust 측정 최소 ≤ 공개 원본 전체 크기.
2. 이전 Python 결과가 있는 동일 입력은 Rust 측정 최소 ≤ 이전 최소.

원본 전체 파일과 원래 압축 스트림을 후보로 보존한다. 원본이 이기면 크기 보존이며,
새 압축 이득은 0바이트다. 크기 통과, 별도 재현 통과, 원본/후보의 UCI 통과,
실제 서버 자원 충족과 대회 규칙 검토는 각각 기록한다.

## General 4K 크기 결과

**11개 모두 원본 이하이며 이전 Python 최소와 같은 크기다. 최종 SHA-256도 11개 모두
이전 winner와 같다.** Rust 이식에 따른 크기 손실은 관측되지 않았다.

| 공개 입력 | 원본 B | 이전 Python 최소 B | Rust 0.4 최소 B | 원본 대비 절감 | 절감률 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ice4 | 4087 | 4082 | **4082** | 5 B | 0.122% |
| 4ku | 4093 | 4088 | **4088** | 5 B | 0.122% |
| STRO4K | 4096 | 4078 | **4078** | 18 B | 0.439% |
| 4k.c | 3932 | 3932 | **3932** | 0 B | 0.000% |
| c4ke | 4093 | 4092 | **4092** | 1 B | 0.024% |
| pygone | 4093 | 4020 | **4020** | 73 B | 1.784% |
| sunfish | 2844 | 2776 | **2776** | 68 B | 2.391% |
| moonfish | 3941 | 3889 | **3889** | 52 B | 1.319% |
| M4sseur | 4095 | 4092 | **4092** | 3 B | 0.073% |
| molly | 4096 | 4095 | **4095** | 1 B | 0.024% |
| we4k | 4079 | 4011 | **4011** | 68 B | 1.667% |

합계는 43449 → **43155바이트**, 294바이트(0.677%) 절감이다.
이는 서로 다른 입력의 바이트 합계이며 하나의 합쳐진 제출 파일이나 엔진별 기력 평균이 아니다.
`--thorough --jobs 2`로 214796개 후보 레코드를 평가했다. 같은 바이트의 서로 다른
recipe가 있을 수 있으므로 이를 모두 서로 다른 프로그램 개수로 해석하지 않는다.
[전체 비교 근거](../evidence/0.4/general-comparison.json)와
[크기 표](../evidence/0.4/general-comparison.csv)에 각 원본·winner·재현 해시를 기록한다.

일반 부문의 크기에는 shebang, shell header, decoder 선택, payload, 그 안에 포함된
컴파일 옵션이 모두 들어간다. 임시로 복원되는 ELF가 수만 바이트여도 그 ELF를
제출 파일로 잘못 세지 않는다. 반대로 payload만 세어 launcher 비용을 빼지도 않는다.

### 왜 작아졌는가

크기 절감은 원본의 코덱 선택, 반복 데이터의 표현과 전체 loader 비용을 함께 탐색한
결과다. 모든 숫자를 십진 지수로 바꾸거나 가장 짧은 소스만 먼저 고르는 방식은 아니다.

| 입력 | launcher 절감 | 압축 payload 절감 | 관측한 이유 |
| --- | ---: | ---: | --- |
| ice4 | 1 B | 4 B | 같은 native 바이트를 만드는 표기 후보와 LZMA 매개변수 조합 |
| 4ku | 5 B | 0 B | 원래 압축 stream 유지, tail/decoder 표기만 단축 |
| STRO4K | 2 B | 16 B | 원래 native payload를 x86 필터 + raw LZMA로 다시 압축 |
| c4ke | 1 B | 0 B | 원래 압축 stream 유지 |
| pygone | 0 B | 73 B | 원래 Python payload를 LZMA 모델·match finder 조합으로 재압축 |
| sunfish | 2 B | 66 B | typed Python AST를 유지한 source 표기·공백과 LZMA 조합 |
| moonfish | 5 B | 47 B | 같은 native 바이트를 만드는 source 후보 및 decoder 교체; 원본 loader 실패는 별도 |
| M4sseur | 3 B | 0 B | 원래 압축 stream 유지 |
| molly | 1 B | 0 B | 원래 압축 stream 유지 |
| we4k | -17 B | 85 B | x86 필터 + raw LZMA의 payload 이득이 더 긴 decoder 비용을 상쇄 |

음수 절감은 증가를 뜻한다. we4k는 launcher가 17바이트 늘었지만 payload가
85바이트 줄어 전체로 68바이트를 얻었다. ice4는 원래 source만 다시 압축했을 때
4086바이트였고 표기 후보가 4바이트를 더 줄였다. Moonfish는 같은 기준으로
3898 → 3889바이트, Sunfish는 2782 → 2776바이트였다. 반대로 4ku의 20바이트 짧은
source 후보는 최종 파일이 4094바이트여서 원래 source를 유지한 4088바이트에 졌다.

원래 압축 스트림이 선택된 경우는 새 코덱의 이득이 아니다. 소스가 더 짧은 후보를
만들었더라도 원래 stream이 더 작으면 그 원래 stream을 유지한다. 소스 표기와
압축 모델 사이의 상호작용 때문에, 지역적으로 짧은 문자열만으로 최종 최소를
확정할 수 없다는 실제 예다.

## 4K ELF 크기와 실행 결과

| 공개 ELF 입력 | 원본 B | Rust 최소 B | 추가 절감 | 별도 바이트 재현 | 실제 실행 범위 |
| --- | ---: | ---: | ---: | --- | --- |
| 4k.c v8.0 | 4042 | 4042 | 0 B | 통과 | 원본·최소·별도 재현 각각 짧은 시계 6국면 통과; 공식 시계 1국면도 통과 |
| 4k.c v9.0 | 3932 | 3932 | 0 B | 통과 | 현재 호스트에서 engine 진입 전 가상 주소 매핑이 실패; UCI 성공으로 처리하지 않음 |

두 파일 모두 원본 identity가 선택되었다. ELF 부문에서는 shell이나 외부 decoder로
감싼 파일을 ELF 후보로 인정하지 않았다. 이미 header 일부에 실행 명령을 겹쳐 놓은
파일이므로 일반 ELF의 section-header 제거도 적용하지 않았다. 이는 입력의 실제
배포 계약에 따른 미적용이며 엔진 이름별 압축 예외가 아니다.

v8.0은 4042바이트 파일을 독립 재현한 뒤 `uci`, `isready`, 명령 허용, 6개의
`position startpos moves` 이력과 clocked `go`, 합법수, `quit` 및 소유 범위 정리를
확인했다. 최종 Rust release로 원본·최소·재현을 각각 검사했다. 캐슬링·앙파상·승격
이력이 포함되며, 이때 보낸 시계는 10000 ms와 증가 시간 0이다.

별도로 원본 v8.0에 **1800000 ms + 3000 ms**를 보내 시작 국면 하나를 실행했다.
원래 옵션을 유지했고 62.155초 뒤 합법적인 `d2d4`가 나왔다. 요청·완료 범위는
**1/6 국면**이다. 실제 30분+3초 시계를 준 유한 검사이며 전체 대국, 최신 버전,
TCEC 서버 또는 기력 검사를 뜻하지 않는다.

v9.0의 `PT_LOAD.p_memsz`는 22 GiB의 가상 주소 영역이다. 이를 실제 RSS 또는
반드시 필요한 물리 메모리로 해석하지 않았다. 주소 공간 한도 28 GiB, CPU 3초,
wall 5초의 원본 시작 진단에서 `execve`가 `ENOMEM`을 반환했고 엔진에 진입하지
못했다. 이 관측을 UCI나 탐색 버그로 분류하지 않는다. 호스트의 overcommit 모드는
0이었으며, 이 모드에서 `CommitLimit`을 절대적인 할당 한도로 단정하지 않는다.
부모 limit, 커널 설정과 원본 ELF 바이트는 바꾸지 않았다.

최신 4k.c 9.15.1 및 STRO4K 6.0의 정확한 공개 ELF 제출 파일은 확보하지 못했다.
공개 STRO4K v5.0의 shell wrapper를 ELF 결과로 이름만 바꾸지 않았다. v8.0은 실제
ELF 실행을 추가로 확인한 역사 예제이며 최신 제출 파일의 대체 결과가 아니다.
[ELF 측정과 최종 release 검사](../evidence/0.4/elf-comparison.json),
[공식 시계 한 국면](../evidence/0.4/elf-uci/4k.c-v8.0-official-clock-one-case.json)에
해시와 관측 범위를 남겼다.

## 프로토콜, 원본 실패와 자원 차단

모든 General 최소 파일은 각각 별도의 `replay --selection smallest` 호출로 재현되어
**11/11 SHA-256 일치**를 확인했다. 그 후 실행 가능한 원래 설정에서 다음 검사를 했다.

| 입력 | 원본 | 최소 파일 | 독립 재현 파일 | 관측 범위 |
| --- | --- | --- | --- | --- |
| 4ku | 통과 | 통과 | 통과 | 각각 짧은 시계 6/6 국면 |
| Sunfish | 통과 | 통과 | 통과 | 기본 CPython과 별도 PyPy 프로파일에서 각각 짧은 시계 6/6 국면 |
| we4k | 통과 | 통과 | 통과 | 각각 짧은 시계 6/6 국면 |
| PyGone | 통과 | 통과 | 통과 | 각각 짧은 시계 6/6 국면; 같은 예산으로 재관측 후 시작 |
| Moonfish | 원본 loader 실패 | 통과 | 통과 | 후보·재현 각각 6/6; 엄격한 원본 배포 동등성 미확인 |
| ice4·c4ke·M4sseur·molly·STRO4K | 실행 전 자원 차단 | 실행하지 않음 | 실행하지 않음 | 압축·바이트 재현 결과와 엔진 실행을 구분 |
| 4k.c v9.0 | 실행 전 차단 | 실행하지 않음 | 실행하지 않음 | ELF 항목의 원본 매핑 진단과 같은 바이트 |

### 공식 시계의 추가 관측

아래 검사는 모두 최소 파일에 **1800000 ms + 3000 ms**를 주고 시작 국면 하나를
요청했다. 엔진의 원래 옵션과 source를 유지한 유한 관측이며, 전체 대국이나 공식
시계의 여섯 국면 전체 검사는 아니다. AS는 검사기가 제한한 가상 주소 공간이다.

| 입력·런타임 | 주소 공간 한도 | 결과 | 탐색 관측 |
| --- | ---: | --- | --- |
| 4ku | 1 GiB | `incomplete` | 120초 관측 한도까지 `bestmove` 없음; 전체 123.304초 |
| we4k, 원래 4 workers / 32 MiB TT | 1 GiB | 통과 | 60.106초에 합법적인 `e2e4`; 전체 60.167초 |
| Sunfish, PyPy 7.3.23 | 1 GiB | 실패 보존 | 전이표 삽입 중 `MemoryError`; 전체 21.721초 |
| Sunfish, 동일 PyPy의 별도 자원 계획 | 4 GiB | 통과 | 51.967초에 합법적인 `d2d4`; 전체 52.290초 |
| Sunfish, 기본 CPython 3.12.14 | 1 GiB | 통과 | 43.753초에 합법적인 `d2d4`; 전체 43.818초 |

4ku는 handshake와 명령 허용을 통과했지만 검사기의 120초 탐색 관측 한도 안에
응답하지 않았다. 원래 시간 배분은 이 초기 시계에서 최대 600초이고, 완성된 깊이
뒤에 적용하는 soft threshold도 60·180·300초 조건을 갖는다. 엔진에 제공한 실제
시계는 끝나지 않았으므로 시간패나 프로토콜 성공으로 세지 않았다.
[시간 배분과 공식 시계 관측](../evidence/0.4/general-time-management.json)에 원래
로직의 구조화된 근거와 실행 결과를 연결했다.

Sunfish의 두 PyPy 관측은 같은 interpreter 바이트와 같은 엔진 파일을 사용한다.
후속 관측에서만 검사기 자원 계획을 AS 4 GiB, 요구 메모리 3 GiB와 여유분 256 MiB로
별도 작성하고 계획 시점 약 3.794 GiB, 실행 직전 약 3.799 GiB의 가용 추정치를
확인한 뒤 시작했다. 전이표 상수나
탐색 설정은 바꾸지 않았고, 앞선 1 GiB 실패도 그대로 남겼다.
[별도 자원 관측](../evidence/0.4/resource-plans/sunfish-smallest-official-clock.json)은
원래 13개 자원 관측과 구분한 추가 공식 시계 기록이다.

### Python 실행 환경의 경계

초기 harness는 `pypy3`를 제공하려고 PyPy 배포판의 전체 `bin`을 PATH 앞에 놓았다.
그 배포판에는 `python3` 이름도 있어 Sunfish까지 PyPy로 실행되었다. 해당 결과를
CPython 검사로 보고하지 않고 interpreter 버전·실행 파일 해시와 함께 보존했다.

최종 기본 환경 검사는 `pypy3` 이름만 제공하는 별도 alias 디렉터리를 사용했다.
`python`, `python3`, `python3.11`, `cc`, `gcc`, `xz`, `gzip`, `bash`의 기존 해석이
바뀌지 않았으며 `python3`는 CPython 3.12.14다. 이 환경에서 Sunfish의 원본·최소·
독립 재현 각각 짧은 시계 6/6 국면을 통과했고, 공식 시계에서도 원래 1 GiB AS와
120초 탐색 한도 안에 정상 응답했다. 이는 엔진 압축이나 옵션 수정이 아니라 검증
환경의 명령 해석을 바로잡은 결과다.

PyGone의 `pypy3`는 앞선 관측과 실행 파일 해시가 같다. 이 근거로 기존 결과를
재사용했으며 새 PATH에서 다시 실행했다고 주장하지 않는다. 실행 이름만 같다는
이유로 두 interpreter를 동일 환경으로 취급하지 않는다.
[기본 Python 환경과 세 역할 검증](../evidence/0.4/general-canonical-runtime.json)에
이 차이와 앞선 관측을 함께 기록했다.

### 자원 차단과 원본 loader 실패

PyGone는 처음에 2 GiB의 기존 시작 조건을 만족하지 못했다. 컴파일과 재현 작업이
끝난 뒤 **같은 원본 plan·같은 요구량과 여유분**으로 재관측했을 때
2176126976바이트의 가용 추정치가 관측되어 명시적으로 시작했다. 원본·최소·재현은
각각 23.224초, 20.614초, 19.340초에 전체 검사를 끝냈다. 첫 차단 보고서와 후속 성공을
모두 보존했고, 기대값·TT·worker·캐시 정책을 바꾸지 않았다.

Moonfish 원본은 raw `unxz` 호출이 stdout 모드를 거절하면서 뒤의 compiler가
`main`을 받지 못했고 wrapper가 종료했다. 새 decoder의 후보가 돌아간다는 사실은
원래 실패한 배포와의 엄격한 실행 동등성을 증명하지 않는다. 따라서 52바이트 절감은
측정 결과와 후보 동작으로 기록하고 원본 통과로 바꾸지 않았다.

큰 원본에는 대략 64~256 GiB의 고정 할당과 101~509 workers를 사용하는 프로필이
포함된다. 이 수치는 실제 peak RSS 측정이 아니라 조사한 원래 설정이다. 호스트의
cgroup 메모리 상한은 8 GiB였으며 실제 TCEC 다중 코어 서버를 대체하지 않는다.
해당 원본을 더 작은 테이블이나 적은 스레드로 수정한 결과는 이번 동일 입력 결과에
섞지 않았다. [13개 자원 관측과 최신 역할별 결과](../evidence/0.4/resource-plans/index.json)에
원래 입력·도구·예산·차단 원인·후속 실행을 함께 남겼다.

기존 검사에서 제공한 엔진 시계보다 짧은 관측 시간 제한이 먼저 끝나는 경우를
`fail`로 분류하던 원인을 수정했다. 이제 실제 시계가 끝나지 않은 관측 중단은
`incomplete`이고, 실제 시계를 넘긴 경우와 구분한다. 앞서 v8.0에 공식 시계를 준
75초 검사의 기록을 지우거나 성공으로 바꾸지 않았으며,
[분류 정정 근거](../evidence/0.4/elf-uci/earlier-observation-classification.json)를 보존했다.

메모리 계획은 `MemAvailable`과 보이는 cgroup 제한·현재 사용량·inactive file cache를
읽는 보수적인 관측이다. 메모리 예약이나 할당 성공 보증은 아니다. 현재 구현은
회수 가능할 수 있는 active file cache를 모두 여유로 세지 않으므로 실제보다 엄격하게
차단할 수 있다. 같은 예산을 다시 관측하는 것은 허용하지만 기준을 낮추거나 캐시를
강제로 비워 성공을 만드는 방법을 사용하지 않았다.

## 실제 제출 기준의 규칙 경계

[공식 규칙 revision 7853](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853)은
단일 파일 4096바이트, 시작 60초, 파일명·옵션에 숨긴 엔진 정보의 산입,
General의 외부 명령 목록과 ELF의 외부 프로그램 금지를 규정한다. 실제 제출 판단에는
크기 외에도 이런 조건이 필요하다.

공식 명시 목록은 `bzip2 bash c++ cargo cc clang chmod gzip lzma mktemp perl python
python3 pypy3 rustc sh sleep tail xz`다. 공식 예제는 목록에 없는 `rm`을 사용하며,
일부 공개 파일에도 `g++`, `unxz`, `env` 같은 별도 이름이 나타난다. 같은 시스템
프로그램의 별칭이라는 사실과 조직자가 허용한다는 사실을 혼동하지 않는다.
이 불일치를 확인하지 않고 모든 공개 예제의 출전 적격성을 인증할 수는 없다.
[실제 original/winner launcher 11쌍의 검토](../evidence/0.4/launcher-rule-review.json)는
명령 토큰·header 해시·정리 방식을 기록한다. 10개 shell 쌍 모두 `rm`을 사용했고,
4ku·c4ke의 `g++`, PyGone의 복원 script shebang `env`, Moonfish 원본의 `unxz`를
추가 미확정 항목으로 구분했다. 엔진 source나 header 원문은 이 metadata에 없다.

개발 도구의 liblzma·zlib·libbz2·Clang·RustPython·cozy-chess 사용과 제출 파일의
외부 의존성은 별개다. 독립 합법수 판정 라이브러리는 NVCompact에만 들어가며
엔진 제출물에 넣지 않았다. 정적 launcher 검토와 소유한 cwd/process group의 정리는
전역 파일시스템, 이탈한 세션, 모든 런타임 분기에서의 외부 호출 감사와 다르다.

## 소스가 다른데 ELF가 같다는 뜻

컴파일러가 서로 다른 표현을 같은 계산으로 최적화하고, 같은 object들이 같은 링크
조건을 거치면 전체 ELF 바이트가 같을 수 있다. 링커가 C 소스를 무시하거나 임의의
알고리즘을 다른 알고리즘으로 바꾼다는 뜻은 아니다. LTO가 있으면 링크 단계에서도
컴파일러 최적화가 작동할 수 있지만, 그 경우에도 특정 도구·옵션·입력에 대한 결과다.

실제 4ku 비교에서 원본 소스는 10308바이트, `shortest-compact`는 10288바이트였고,
원래 컴파일 명령의 출력은 둘 다 **75336바이트이며 전체 SHA-256도 같았다.**
그럼에도 최소 제출 파일은 원래 압축 stream을 유지했다. source 20바이트 절감이
곧 제출 파일 20바이트 절감을 뜻하지 않는다는 직접적인 관측이다.

C의 `100000`을 `1e5`로 쓰면 정수 literal이 `double`로 바뀐다. 수학적 값만으로
일반적인 의미 보존을 주장할 수 없다. `100000.`을 `1e5`로 바꾸는 후보처럼 값과
타입, 주변 관측 계약이 맞는 경우를 구분한다. 16진수도 C의 정수 타입 선택에
영향을 줄 수 있다. 조건 연산자 역시 분기 결과의 통상 산술 변환이 의미를 바꿀 수 있다.
[Rust 변환 설계와 반례](RUST-REWRITES.md)에 적용 조건을 설명했다.

자체 혼합 C/Rust 예제에서는 9개 구현 조합과 2개 링크 순서로 18개 링크 후보를
실행했고, 396개 배포 후보가 독립 oracle을 통과했다. 선택한 504바이트 ELF는
별도 빌드로 동일하게 재현되었다. 이는 혼합 링크·선택 도구 재현 경로의 검증이며
체스 엔진 504바이트나 그 기력을 주장하는 결과가 아니다.

## Rust 이식과 검증

활성 컴파일·링크, 표기 변환, C AST 변환 조정, 코덱 탐색, envelope와 replay,
UCI와 자원 계획은 Rust다. Node는 npm 진입점·빌드·포장만 담당한다. 과거 Python은
`reference/v0.3/`에 비교 자료로 보존하며 활성 Rust backend로 호출하지 않는다.
사용자가 선언한 Python 엔진이나 자체 독립 oracle은 그 명시한 실행 계약으로 실행한다.

이식 중 발견한 원인 세 가지를 수정했다.

- Python token 두 개만 잘라 검사할 때 닫는 괄호의 문맥이 사라져 유효한 공백 제거를
  거절하던 문제를 lexer 문맥 복구로 해결했다. Sunfish 전용 예외를 추가하지 않았다.
  ice4·Moonfish·Sunfish의 13개 recipe씩 총 **39개 source 결과가 과거 Python과
  바이트 단위로 같았다.** 전체 token 및 AST 검사는 유지했다.
- C 후보가 이겼는데 전체 탐색에 참여했던 사용하지 않는 Rust compiler까지 재현의
  필수 도구로 요구하던 문제를 선택한 후보의 실제 도구 의존성으로 수정했다.
  필요한 도구의 해시 검증은 그대로 유지했다.
- 프로토콜 관측 한도와 엔진의 실제 시계 만료를 분리했다. 작은 관측 예산을
  대회 시간패로 보고하지 않는다.

최종 workspace 검사는 **Rust unit 33개 + packing integration 8개**, 실패·무시 없이
통과했다. Node launcher 5개 검사와 실제 tarball을 다른 소비자 디렉터리에 오프라인으로
설치한 9개 검증 그룹도 통과했다. 설치된 패키지로 plain 빌드·별도 재현·명시적
`--verify`·타입 표기 변환과 패키지 바이트 불변을 확인했다.

- [source parity](../evidence/0.4/notation-parity.json)
- [혼합 링크와 선택 도구 재현](../evidence/0.4/mixed-selected-tool-replay.json)
- [Rust·npm·실제 설치 검증](../evidence/0.4/package-validation.json)

실측 release 실행 파일 SHA-256은
`08a4b493b19382a6e8de46cdb50465053e5b6c850a304bb9c2fed034cc21357e`다.
개발 도구 자체의 10162344바이트는 TCEC 제출 파일 크기가 아니다.
코덱은 liblzma·zlib·libbz2의 native 구현을 사용하므로 모든 의존성을 순수 Rust로
새로 작성했다거나 FFI 경계까지 자동으로 안전해졌다고 주장하지 않는다.
Rust/Python 간 공정한 실행 시간 대조나 엔진 기력 향상도 이번 크기 결과에 포함하지 않는다.

## 재실행 명령

입력 파일은 저장소 밖에서 준비하고 manifest에 고정한 해시를 확인한다. 아래 변수는
실제로 준비한 절대 경로로 바꾼다. 명령은 Rove4k 루트에서 실행한다.

```sh
npm ci --ignore-scripts
npm run build:nvcompact
npm exec -- nvcompact --version

NVC_INPUTS=/absolute/external/tcec-inputs
NVC_RESULTS=/absolute/external/new-tcec-results

npm exec -- nvcompact engines \
  --manifests tools/nvcompact/comparisons/general \
  --artifact-root "$NVC_INPUTS" \
  --output "$NVC_RESULTS/general" --jobs 2 --thorough

npm exec -- nvcompact engines \
  --manifests tools/nvcompact/comparisons/elf \
  --artifact-root "$NVC_INPUTS" \
  --output "$NVC_RESULTS/elf" --jobs 2 --thorough

npm exec -- nvcompact replay \
  "$NVC_RESULTS/general/4ku/summary.json" \
  --selection smallest --output "$NVC_RESULTS/4ku-replay"
```

크기 탐색은 기본적으로 엔진을 실행하지 않는다. 큰 원본 설정은
[resource 예제](../comparisons/resource-examples/)로 계획을 만들고, 실제 시작을
별도 명령으로 요청한다. 계획 JSON의 입력·도구 fingerprint와 현재 자원을 실행 전에
다시 확인하며, 다른 도구 바이너리의 recipe를 조용히 재사용하지 않는다.

```sh
npm exec -- nvcompact resource plan /absolute/external/prepared-spec.json \
  --output "$NVC_RESULTS/plan.json"
npm exec -- nvcompact resource run "$NVC_RESULTS/plan.json" \
  --output "$NVC_RESULTS/resource-run" --start
```

압축을 전혀 적용하지 않는 빌드도 별도 경로다.

```sh
npm exec -- nvcompact build \
  tools/nvcompact/examples/native-build/manifest.json \
  --out /absolute/external/plain-build --jobs 2
npm exec -- nvcompact reproduce \
  /absolute/external/plain-build/winner.recipe.json \
  --out /absolute/external/plain-replay
```

`build`와 plain `reproduce`는 기본적으로 target·검증기를 실행하지 않는다. 실행 검사는
각 명령에서 `--verify`로 명시한다. 원본 소스는 읽을 수 있는 정본으로 유지하며,
생성 source·외부 엔진·압축 파일·원시 로그·npm tarball은 저장소 밖에 둔다.
운영 코드, 자체 예제와 검토한 메타데이터만 Rove4k에 남는다.
