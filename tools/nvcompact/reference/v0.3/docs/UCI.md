# 완성 파일의 TCEC 4k·UCI 검사

모노레포에서 이 문서의 예제 소스 기준 디렉터리는 `packages/nvcompact/`다. 직접 Python 명령은 그 디렉터리의 `python/` 아래 진입점을 사용한다. 루트에서 실행하는 npm 명령은 [README](../README.md)에 있다.

`nvuci.py`는 실제 실행 파일 또는 압축 wrapper를 실행해 프로토콜과 반환 수의 합법성을 검사한다. 소스의 특정 문구나 함수 이름을 요구하지 않는다. 검사기는 엔진에 포함하지 않는 개발 도구다.

## 1. 적용하는 규칙과 판정 범위

[TCEC 4k 규칙, 확인한 revision 7853](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853)은 일반 UCI 전체보다 작은 부분집합을 요구한다. `uci`, `uciok`, `isready`, `readyok`, `position startpos`와 수 목록, `go` 또는 clock을 포함한 `go`, `bestmove`, `quit`가 핵심이다. `stop`, `ucinewgame`처럼 대회 소프트웨어가 보내는 명령을 지원하지 않더라도 견뎌야 한다. `id`, `info`, `option` 등은 이 부문의 추가 기능이다.

일반 UCI는 [2006년 UCI 원문을 보존한 문서](https://backscattering.de/chess/uci/)를 따른다. 이 문서는 TCEC 규칙 페이지에서도 연결한다. 일반 UCI의 identification, FEN, 탐색 중 `isready`, `stop` 동작을 4k 필수 명령과 혼동하지 않는다.

| 결과 필드 | 의미 |
|---|---|
| `required_tcec4k_verdict` | 필수 부분집합에 대한 실제 검사 결과 |
| `extended_uci_verdict` | 요청한 일반 UCI 추가 probe 결과. 수행하지 않으면 `not_run` |
| `verdict` | `--profile tcec4k`에서는 필수 부분집합, `--profile uci`에서는 필수·추가 probe를 합친 판정 |
| `acceptance_verdict` | CLI의 최종 exit 판정. 명시적으로 요청한 결정적 차등 검사의 실패·미완료도 반영하며 protocol `verdict`는 보존 |
| `artifact.within_4096_bytes` | 파일 크기 조건. 프로토콜 판정과 별도로 남음 |
| `cases` | 각 조건·입력·관측 결과·실패 종류 |
| `sessions` | 제한된 transcript, stdout/stderr 분량, 종료·정리 결과 |
| `observations` | 실제 position, go, budget, bestmove, 시간과 일부 info 값 |

`pass`는 명시한 probe를 통과했다는 뜻이다. 모든 UCI 기능, 모든 국면, 엔진 성능, 외부 명령 whitelist 또는 TCEC 출전 자격 전체를 인증하지 않는다. 4k 필수 동작을 원본도 실패했다면 변환본의 같은 실패를 `pass`로 바꾸지 않는다.

응답별 deadline 초과는 해당 probe의 `fail`이다. 전체 검사 작업의 budget 소진은 `incomplete`다. 짧은 로컬 테스트 clock에서의 실패를 30분+3초 대국 전체의 성능 결론으로 일반화하지 않는다.

## 2. 개발 전용 합법수 oracle

합법수는 독립된 [python-chess의 Board·legal_moves](https://python-chess.readthedocs.io/en/latest/core.html)를 사용한다. 테스트한 패키지는 `chess==1.11.2`다.

```sh
python3 -m pip install --target .dev/uci-oracle 'chess==1.11.2'
```

검사 실행 시 `--oracle-path`에 이 디렉터리를 명시한다. 이미 검사기의 Python 환경에 설치했다면 생략할 수 있다. 도구는 실행 중 네트워크 설치를 하지 않는다. oracle 모듈의 실제 위치·버전·SHA-256은 결과에 기록한다.

TCEC 규칙은 엔진 자체가 python-chess를 사용하는 경우 이를 제출 크기에 포함하도록 규정한다. 여기서는 엔진 외부의 개발 검사기로만 쓰며, 검사 도구를 제출 ELF나 wrapper에 포함하지 않는다.

Python 3.11 이상과 Linux/POSIX process-group 실행 환경이 대상이다. interpreter 경로와 실행 환경은 검사자가 준비한다. GPL인 rules oracle의 코드를 엔진 소스에 복사하지 않는다.

## 3. 바로 실행하기

패키지 루트에서, 실제 완성 파일 경로를 지정한다.

```sh
python3 python/nvuci.py \
  --binary /absolute/path/to/engine \
  --oracle-path "$PWD/.dev/uci-oracle" \
  --report runs/engine-uci.json
```

실행 권한이 있는 ELF와 shebang wrapper 모두 같은 방식으로 검사한다. 명시적인 interpreter 실행이 필요한 파일은 argv를 JSON으로 지정할 수 있다.

```sh
python3 python/nvuci.py \
  --command '["/bin/sh","/absolute/path/to/engine.sh"]' \
  --artifact /absolute/path/to/engine.sh \
  --oracle-path "$PWD/.dev/uci-oracle" \
  --report runs/script-uci.json
```

`--command`는 shell 문자열이 아니다. 첫 항목은 실행할 프로그램의 절대 경로여야 한다. 다른 파일 인자도 절대 경로를 사용한다. 엔진은 검사기가 만든 임시 작업 디렉터리에서 실행하고, 그 안의 빈 `tmp` 디렉터리를 `TMPDIR`로 지정한다. `$0`으로 자기 파일을 읽는 정상 wrapper는 절대 경로를 통해 동작한다.

추가 UCI 동작도 조사하되 TCEC 4k 부분집합 판정을 유지하려면 다음과 같이 실행한다.

```sh
python3 python/nvuci.py \
  --binary /absolute/path/to/engine \
  --oracle-path "$PWD/.dev/uci-oracle" \
  --extensions \
  --report runs/engine-uci-extended.json
```

일반 UCI probe의 실패도 선택을 차단해야 하는 프로젝트라면 `--profile uci`를 사용한다. 이 경우 추가 probe가 자동으로 켜진다.

CLI exit code는 `acceptance_verdict`의 `pass=0`, `fail=1`, 설정 오류·미완료는 `2`다. 명시적으로 요청한 결정적 비교가 mismatch 또는 incomplete이면 protocol만 통과했어도 비영 종료한다. 보고서를 쓰면서 같은 JSON을 stdout으로 출력한다.

## 4. 검사 내용

### 필수 부분집합

프로세스 생성부터 `uci`·설정·첫 `readyok`까지 최대 60초를 허용한다. `--startup-seconds`로 더 짧게 조사할 수 있으나 60초를 넘겨 통과시키지는 않는다.

`uci`에서 광고한 option을 파싱한다. `Hash`, `Threads`, `MultiPV`는 광고한 범위 안에서 요청한 자원값을 선택한다. `OwnBook`, `Ponder`를 광고한 check option으로 제공하면 false를 보낸다. 광고하지 않은 기능을 강제로 `setoption`하지 않는다. 현재 적용값은 실제 엔진 내부 introspection이 아니라 보낸 명령이라는 점을 기록한다.

`ucinewgame`, 대기 중 `stop`, 알 수 없는 명령 뒤에 `isready`를 보내 생존과 응답을 확인한다. 다음 여섯 개의 합법적인 startpos 수열을 검사한다.

| 입력 | 주된 확인 범위 |
|---|---|
| 초기 배치 | 흰색의 합법수 |
| `e2e4` 이후 | 흑색 차례·수 목록 적용 |
| 백 캐슬링을 포함한 수열 | 캐슬링 후 보드·권리 갱신 |
| 앙파상을 포함한 수열 | 수 목록의 특수 capture 적용 |
| 개발과 흑 캐슬링을 포함한 중반 | 긴 수 목록·연속 position 설정 |
| 양측 승격을 포함한 수열 | 승격 기물과 capture 적용 |

각 position에 clock 기반 `go`를 보내며 기본 clock은 양측 2,000ms, increment는 0이다. 응답 기한은 초 단위로 `min(search_seconds, (clock_ms + clock_grace_ms) / 1000)`이다. 기본 grace는 1,000ms다. 이 여유는 로컬 검사 스케줄링 allowance이며 TCEC에서 추가 시간을 허용한다는 뜻이 아니다. 패키지의 최종 엔진 캠페인은 별도 공통 프로필인 `profiles/protocol-15s.json`으로 clock 15,000ms, search 16초를 지정했다. 초기 2초 stress probe의 실패 기록은 별도로 보존했다.

`bestmove`의 형식과 합법성을 검사한다. `ponder`가 있으면 첫 수를 적용한 뒤 상대의 합법수인지 검사한다. `0000`은 합법수가 없는 배치에서만 허용하고 `(none)` 등을 표준 nullmove라고 바꾸어 해석하지 않는다. 매 `go` 뒤 정확히 하나의 bestmove가 나와야 하며, 다음 readyok로 동기화하는 동안 중복 bestmove를 거부한다.

`quit` 뒤 엔진 leader는 기본 2초 안에 종료해야 한다. 그 뒤 원래 process group에는 기본 5초의 명시적인 cleanup grace를 둔다. TCEC 예시와 실제 원본 wrapper가 쓰는 `(sleep N; 삭제) & exec 엔진`의 유한한 정리를 끝까지 관측하기 위한 별도 단계다. `--cleanup-seconds`로 지정하며 60초를 넘길 수 없다. 종료 직후 group 존재, 실제 대기 시간, grace 뒤 잔존 여부를 모두 기록한다. grace 뒤에도 남은 worker는 실패하고 정리한다. 이 5초는 검사기의 설정이며 TCEC가 별도의 5초 quit 규칙을 명시했다는 뜻은 아니다.

`--quick`은 같은 명령 계약에서 position 수열을 앞의 세 개로 줄인 screening이다. 최종 후보에는 기본 여섯 수열을 사용하는 편이 적절하다.

### 일반 UCI 추가 probe

별도 프로세스를 시작해 결과와 상태를 필수 검사와 구분한다. 이름·작성자·option 문법을 확인하고 다음 동작을 조사한다.

- FEN과 후속 moves, 승격, 캐슬링, 앙파상, 체크메이트, 스테일메이트 배치.
- 고정 depth·nodes, movetime을 포함한 `go`.
- `go infinite` 도중 `isready`에 응답하고 `stop` 뒤 bestmove를 내는 동작.
- 탐색 도중 `quit`와 프로세스 수명.

누락된 `id`처럼 세션을 손상하지 않는 metadata 실패는 남긴 뒤 다른 probe를 계속한다. timeout·잘못된 수처럼 현재 탐색 상태를 신뢰할 수 없는 실패가 나면 해당 추가 세션은 중단한다. 미실행 뒤쪽 항목을 통과했다고 추정하지 않는다.

정해진 go 명령 뒤 수를 반환했다는 사실만으로 엔진이 depth·nodes budget을 내부에서 정확히 구현했다고 증명할 수는 없다. info 값은 관측 근거로 남긴다. 고정 budget 의미는 원본 소스·반복 실행 근거와 함께 판단해야 한다.

## 5. 원본과 변환본의 차등 비교

```sh
python3 python/nvuci.py \
  --binary /absolute/path/to/transformed-engine \
  --oracle-path "$PWD/.dev/uci-oracle" \
  --extensions \
  --baseline-report runs/original-uci-extended.json \
  --deterministic-mode depth \
  --report runs/transformed-uci-extended.json
```

`--deterministic-mode`의 기본값은 `none`이다. wall-clock 탐색은 같은 소스라도 스케줄링·스레드·탐색 완료 시점에 따라 최선수가 달라질 수 있어 exact bestmove 비교를 하지 않는다. 합법성·프로토콜 결과는 여전히 검사한다.

`depth` 또는 `nodes` exact 비교는 해당 엔진이 같은 고정 budget과 환경에서 결정적으로 동작한다는 호출자의 계약이 있을 때 요청한다. 대응되는 `position`·budget·mode가 있어야 하며 없으면 `incomplete`다. Threads·Hash 요청과 보낸 option 설정이 달라도 `control_differences`를 남기고 `incomplete`로 처리한다. bestmove와 제공한 ponder를 대조하며, `observed_equal`은 표본에서 같았다는 뜻이다. 전체 info 출력이나 엔진의 모든 상태·의미가 증명됐다는 뜻이 아니다. strict verdict를 차등 결과로 덮어쓰지 않는다.

차등 보고서는 다음을 구분한다.

| 항목 | 의미 |
|---|---|
| `regressions` | 원본에서 통과했던 probe를 변환본이 통과하지 못함 |
| `inherited_observed_failures` | 같은 probe가 양쪽에서 실패·미완료. 원인까지 동일하다고 증명하지 않음 |
| `improvements` | 원본의 실패 항목을 변환본이 통과함. 압축기가 의미를 보존했는지는 별도 검토 |
| `coverage_gaps` | 대응하는 probe가 한쪽에 없어 비교할 수 없음 |
| `exact_fixed_budget_observations` | 명시적으로 요청한 고정 budget 관측 비교 |
| `comparison_verdict` | 위 exact 비교의 pass/fail/incomplete. 기본값 none이면 not_requested |

원본의 UCI 결함을 압축 단계가 자동으로 고쳐 다른 엔진으로 만들지 않는다. 원본도 실패하는 조건은 보고서에 그대로 두고, byte-preserving 압축 경로의 근거와 source rewrite의 근거를 구분한다.

## 6. 호출 API와 NVCompact manifest 연결

```python
from nvuci import Config, verify_engine, compare_results

original = verify_engine(
    ["/absolute/path/to/original"],
    Config(oracle_path="/absolute/path/to/uci-oracle", extensions=True),
)
candidate = verify_engine(
    ["/absolute/path/to/candidate"],
    Config(oracle_path="/absolute/path/to/uci-oracle", extensions=True),
)
comparison = compare_results(original, candidate, deterministic_mode="none")
```

설정은 `Config` 또는 같은 field의 dict로 받을 수 있다. API 입력 오류는 `ValueError`이고 실제 protocol failure는 JSON 보고서다. 검사 대상으로 삼는 제출 파일은 `Config.artifact_path`에 명시하면 크기·SHA-256과 검사 전후 bytes 불변도 확인한다.

manifest의 `verify`와 `verify_final`은 기존의 argv interface를 그대로 사용한다. `nvuci.py`를 `inputs`에 넣고 Python 도구를 선언한 프로젝트에서 다음과 같이 연결할 수 있다.

```json
{
  "verify": ["{python}", "{root}/nvuci.py", "--binary", "{binary}", "--oracle-path", "/absolute/path/to/uci-oracle", "--quick"],
  "verify_final": ["{python}", "{root}/nvuci.py", "--binary", "{binary}", "--oracle-path", "/absolute/path/to/uci-oracle"]
}
```

oracle를 개발 dependency로 고정하고 해당 Python 환경을 준비한다. 외부 절대 경로의 oracle 설치는 source snapshot이 자동으로 보존하지 않는다. 이 예시에서는 보고서의 version·module hash와 환경 설치 기록이 근거다. 외부 runner의 command deadline이 시작·검사 budget보다 짧으면 runner가 먼저 중단하므로 `--command-seconds`도 실제 검사 범위에 맞춘다.

## 7. 수명·자원 경계와 알려진 한계

stdout과 stderr를 동시에 비동기로 읽어 한쪽 pipe가 가득 차면서 엔진이 멈추는 문제를 막는다. 기본 combined output 상한은 2 MiB, 한 줄은 64 KiB, 저장 transcript는 256 KiB다. transcript가 잘려도 실제 protocol 판정과 output 상한 검사는 계속한다. 대기 중에는 최대 50ms 간격으로 leader 종료를 확인하므로, 이미 죽은 엔진의 pipe를 cleanup helper가 보유하더라도 helper의 EOF까지 기다린 뒤 timeout으로 오인하지 않는다.

프로세스는 새 session/process group에서 시작한다. 실패·timeout 뒤 원래 group을 종료하고 직접 생성한 leader를 회수한다. 이 환경에서 `/proc`의 PID namespace가 실행 프로세스와 다를 수 있음을 확인했으므로 PID 숫자만 비교한 `/proc` scan에 종료 판정을 맡기지 않는다. `killpg(pgid, 0)`으로 원래 group의 잔존 여부를 확인한다. 실행기가 새 session으로 탈출한 임의 descendant까지 감시하는 sandbox는 아니다.

엔진의 현재 작업 디렉터리와 지정한 `TMPDIR`에 남은 파일은 **검사기의 임시 디렉터리 삭제 전에** 보고한다. 정상 quit와 cleanup grace가 끝났는데 파일이 남으면 실패다. 조기 종료·timeout 이후 검사기가 group을 강제 종료했다면 timer의 삭제 작업을 검사기가 끊었을 가능성이 있으므로, 잔여물은 `incomplete / cleanup_observation`으로 기록한다. 원래의 crash·timeout 실패는 그대로 유지하고, 불명확한 파일 정리 원인을 엔진의 별도 결함으로 단정하지 않는다.

미리 만든 빈 `tmp` 디렉터리 자체만 검사기 소유 입력으로 제외한다. `mktemp`·compiler가 `TMPDIR`을 따르면 해당 생성물을 관측할 수 있다. `/tmp`를 hard-code하거나 다른 외부 경로에 쓰는 프로그램까지 시스템 전체의 file syscall을 감사하지 않는다. TCEC가 예외로 둔 시스템 프로그램의 cache와 엔진의 임시 파일은 출전 검토에서 구분해야 한다. 외부 명령 whitelist·환경 라이브러리·ELF 부문 여부도 별도 배포 조건으로 확인한다.

광고한 Hash·Threads는 작은 값을 요청하지만 프로세스 전체 RAM과 모든 descendant의 CPU를 강제로 제한하는 cgroup sandbox는 아니다. 제출 엔진을 검사하는 목적의 bounded process runner이며 악성 프로그램 격리 도구라고 설명하지 않는다.

기본 검사는 Threads=1 요청으로 재현 가능한 조사 출발점을 제공한다. 실제 다코어 TCEC 배치 성능, TT race, many-core scaling, 실전 승률 검증은 포함하지 않는다. 옵션이 있다면 `--threads`로 별도 실행할 수 있으며 그 요청값과 광고된 지원 범위가 보고서에 남는다.
