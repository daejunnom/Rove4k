# NVCompact 메모리·실행 비용과 숏코딩 제안 후속 결과

2026-10-21, PR #16의 후속 구현 기록이다. 기존 탐색 구조의 비교 기준은
`46cc1102390f3d973268efd87f0ba48a718b5063`이며, 이 문서의 새 결과는 아래에
명시한 성능 입력과 자문 도구 검사에 한정한다. 앞선 A–F·외부 비교의 26+7행을
이번 변경에서 재실행한 것으로 보고하지 않는다. npm 0.5.0에 이미 배포된 기능도 아니다.

## 1. 변경과 소유 경계

| 변경 | 원인과 결과 | 유지하는 계약 |
|---|---|---|
| 스트리밍 복원 비교 | 복원 전체 `Vec` 대신 최대 64 KiB 출력 scratch로 원본과 순차 대조 | 길이·내용·trailing input·잘린 스트림 거부, 기존 decode와 공통 처리 |
| 색인된 FIFO 비용 캐시 | 선형 검색과 `remove(0)` 이동을 hash bucket + ring slot으로 대체 | digest·길이·전체 typed recipe 재비교, FIFO 순서, 유한 메모리 |
| bounded window 작업 분배 | 기존 worker가 완료하면 같은 window의 다음 codec을 수행 | 동시 codec worker 상한은 jobs, 선언 순서의 결과·동률 승자·cache admission·오류 선택 |
| 비용 전용 호출 | 사용하지 않을 coverage JSON과 hex payload hash 생성 생략 | 보고서를 요구하는 evaluate 경로의 coverage와 record는 유지 |
| `advise-c` | 타입별 상수, 미사용 관측, 사용 지점 정수 범위와 축약 제안 | 원본 수정·압축 후보 생성·채택 없음 |
| 선택형 계측·trace | 독립 진단 C 사본과 유한 실행 표본의 범위 보고 | 자동 빌드·실행 없음, 표본으로 정적 범위를 좁히지 않음 |
| `inspect-binary` | 최종 파일의 모든 byte offset에서 반복 4·8바이트 검색 | decode·load·execute·수정 없음, 의미·절감량은 미확정 |

작업 window는 최대 `4 × jobs`다. 기존 jobs개를 넘어 보관하는 header와 encoded
output의 추가 허용량은 최대 16 MiB이며, 큰 입력·header에서는 window를 줄인다.
실제 결과도 계산한 길이 상한 안인지 확인한다. 코덱 자체 dictionary·scratch와
기존 기본 window는 이 추가 허용량과 다른 메모리다. 작업 중단 뒤 모든 worker를
join하며 시작하지 않은 요청은 `codec_not_started` / `fresh_codec_not_started`로
구분한다. 기존 scoped worker pool의 작업 배분을 개선한 것이며 새 영구 pool을
만들었다는 의미가 아니다.

캐시 메모리 예산에는 slot·bucket 배열과 문자열 capacity·공유 header 저장량을
포함한다. 메타데이터 때문에 아주 작은 캐시가 담는 항목 수는 줄 수 있다. 캐시의
성공은 비용 재사용이며 final fresh 재생성이나 의미 검증의 성공을 대체하지 않는다.

자문 기능의 상세 설계·명령·제약은 [SHORTCODE-ADVISOR.ko.md](SHORTCODE-ADVISOR.ko.md)에 둔다.
`parse_for_advice`의 세션 간 문맥 fingerprint는 자문 전용이다. 기존 압축 frontend의
정확한 preprocessing guard와 SourceContext 경로에는 추가 정규화·해시 비용을 넣지 않았다.

## 2. 성능 비교

같은 benchmark source를 기존 기준판과 최종 수정판의 별도 snapshot에 적용했다.
입력은 자체 생성한 inert bytes다. CPU 0–3에 고정하고, 버전 순서를 바꾸어 가며
조건·버전마다 4회, 총 **48회** 실행했다. cgroup은 CPU 8개·메모리 8 GiB,
각 실행에는 90초 상한을 사용했다. 시간은 해당 작업 구간의 wall time 중앙값이다.

| 작업 | 기존 | 최종 | 기존 시간 / 최종 시간 |
|---|---:|---:|---:|
| 4,096개 캐시를 채운 뒤 32,768회 hit | 135.308 ms | 16.339 ms | 8.281배 |
| 캐시를 채운 뒤 8,192개 신규 입력으로 교체 | 277.812 ms | 64.485 ms | 4.308배 |
| 512 KiB 혼합 코덱, jobs=1 | 3.484 s | 3.496 s | 0.997배 |
| 같은 혼합 코덱, jobs=2 | 2.739 s | 2.677 s | 1.023배 |
| 같은 혼합 코덱, jobs=4 | 2.439 s | 2.233 s | 1.093배 |
| 8 MiB 복원 검증, jobs=4 | 92.252 ms | 86.376 ms | 1.068배 |

혼합 코덱은 bzip2/gzip의 level 1–9, 총 18개 recipe를 세 번 측정한다. 복원 검증은
8 MiB의 반복 byte 입력에 gzip level 1–4를 적용한다. 캐시·교체 실험은 작은 고유
입력과 gzip level 1이다. 합성 입력·recipe 분포가 실제 엔진 캠페인과 같다고 가정하지 않는다.

| Process peak RSS 중앙값 | 기존 | 최종 | 해석 |
|---|---:|---:|---|
| 8 MiB 복원 검증, jobs=4 | 77,268 KiB | 12,864 KiB | **83.35% 감소** |
| 512 KiB 혼합 코덱, jobs=4 | 24,304 KiB | 25,992 KiB | 추가 결과 보관 window로 1,688 KiB 증가 |

RSS는 `wait4.ru_maxrss`로 process 전체 수명·warmup·마지막 fresh 확인을 포함한다.
64 KiB는 출력 비교 scratch의 크기이며 프로세스 전체 메모리 상한이 아니다.
공유 호스트에서 관측한 작은 시간 차이를 보편적 가속 보장으로 해석하지 않는다.
jobs=1은 약 0.34% 느렸으며, jobs=2의 작은 차이도 그대로 기록했다.

**48회에 기록한 입력 hash·비용 벡터 hash·대표 최종 artifact 크기와 hash가
기존/최종에서 같았으며, 각 실행의 대표 winner를 fresh로 다시 생성해 같은
bytes임을 확인했다.** Cache/churn의 비용 벡터는 warmup 입력 4,096개의 비용이고,
artifact와 fresh 비교는 첫 입력을 대상으로 한다. Churn의 신규 요청 8,192개는
시간 측정에 포함하지만 각각의 비용·산출물을 그 벡터에 보존하지 않았다.
Mixed/restore의 벡터도 해당 portfolio의 최소 비용이며 모든 recipe의 비용 목록은
아니다. 이 기록에서 확인한 동일성을 모든 중간 산출물·엔진 캠페인의 회귀 없음이나
추가 압축 절감으로 확대하지 않는다.

앞선 실제 PR #16 비교의 cache hit 비율은 약 0.022%였다. 따라서 8.281배의
cache-hit 실험을 전체 source-search 또는 엔진 캠페인의 가속도로 제시하지 않는다.
최종 비용 전용 JSON 생략 이전의 중간 측정도 외부 작업 경로에 보존했다.

### 재현과 지문

실행 접점은 `cargo run --release -p nvcompact --example performance -- MODE JOBS`다.
MODE는 `cache`, `churn`, `mixed`, `restore`이며 동일한 예제를 양쪽 구현에 사용한다.
보고서의 시간·RSS는 합격 threshold가 아니다. 모든 실행의 입력·출력·recipe 관련
지문과 환경·중앙값은 [performance-followup.json](../evidence/pr16/performance-followup.json)에 있다.

| 고정 항목 | SHA-256 |
|---|---|
| `src/codec.rs` | `1fc72fd85dc51cbef603e5a0f3b21d620e7c00efa4978fde6f99649b72cda575` |
| `src/envelope_cost.rs` | `7271eb5fdb76da99e95e3d5403f905c541bda80d4ae788ffef01f3536352a0a4` |
| `examples/performance.rs` | `902349ed0f923485c98da9996258a772930e20cd72d6ddd0240272b69bb6b926` |
| 기준 benchmark binary | `a5ecadd853911c30163978e4182b0d17d42292a3bf4198cab7388ce9c2be029f` |
| 최종 benchmark binary | `06e34fa6025f2b72f796d93a564c929c80405bc02d2fccff7d8ab4f4b8d9ac5c` |

## 3. 구현·감사 검사

Rust 1.99.1과 Clang 20을 명시해 전체 workspace 검사를 실행했다.
**113개 통과, 실패 0개**: library 91, 새 advice 통합 2, packing 10,
source-search 10이다. doc/main 테스트가 0개라는 사실을 별도 성공 개수로 더하지 않는다.

주요 의미 경계는 다음과 같다.

- 7개 codec family의 스트리밍 복원, 64 KiB 이후의 불일치, 짧음·길이 초과,
  trailing input, truncation, 빈 payload.
- cache hash collision·ring wrap·초과 항목, 유한 메타데이터 예산, fresh 경계,
  선언 순서 tie·오류 보존, jobs 1/2/4, header를 포함한 추가 window 상한.
- 타입별 literal grouping, 함수 포인터 사용, shadowing, 재대입·조기 반환·단락 연산,
  음수 나머지·unsigned wrap·혼합 부호 복합 대입, 별칭·volatile·VLA·macro 경계.
- 실제 제안 5개를 각각 적용한 자체 C와 원본을 컴파일하고, -100..100 및 정수 경계
  입력 13개에서 결과를 비교했다. 이 유한 검사를 모든 C 프로그램의 동치로 확대하지 않는다.
- 자체 pthread 4스레드 프로그램의 원본/진단 사본이 같은 stdout `384`와 exit 0을
  보였다. process 내 전체 quota 37개 레코드를 정확히 수집·재수용했고, 재분석 문맥
  hash·정적 범위·원본 bytes가 유지됐다. 기존 출력 디렉터리 덮어쓰기도 거절했다.
- 최종 파일의 unaligned `0x5555555555555555` 2곳을 정확히 찾았다. scan은 파일을
  바꾸지 않았으며 의미·절감량을 null로 남겼다.

별도 에이전트가 코드와 설계를 감사하고, 자체 C 함수 **24개·28개 assertion**을
최종 CLI로 독립 실행했다. 전부 통과했으며 35개 finding·36개 range site와 원본
bytes 불변을 확인했다. 구현자가 아닌 별도 에이전트의 검토이며 사람의 PR 승인이 아니다.

Node launcher 5개와 비교 보고서 1개 검사도 통과했다. 공식 build 접점으로 현재
소스를 release 빌드한 뒤 tarball을 만들고, 실제 오프라인 설치본에서 9개 계약 검사
(명령 실행 10회)를 통과했다. 자체 산술 fixture의 정상 입력 256개·오류 입력 2개,
독립 native 재현과 명시적 verify 경계, 설치 파일 불변을 포함한다. 이어 같은 설치본의
새 `advise-c`와 `inspect-binary`도 호출해 예제 finding 6개·range 9곳, magic mask
offset 3·16을 확인했다. 로컬 Node는 v24.19.0이며 npm registry에는 게시하지 않았다.

- 최종 release CLI SHA-256: `5b226f63d825b6d760186aa72187cce28cbbd33b552b3c5994733b4bc21f8584`
- 로컬 검사 tarball SHA-256: `a958f35c91d6205a1870081e3caa17f7242f0eb300368afe85fe163056ed2878`

### 감사에서 실제 수정한 문제

| 문제 | 수정 |
|---|---|
| 도달 가능하지만 값이 미지인 삼항 분기를 unreachable처럼 취급 | 살아 있는 미지 분기는 결과 타입 전체 범위에 포함 |
| VLA sizeof·선언·typedef·cast의 숨은 길이 식 부작용 | 해당 경계에서 사실을 넓히고 비실행 읽기와 구분 |
| 혼합 signed/unsigned 복합 대입의 계산 타입 | Clang의 computeLHSType·computeResultType을 먼저 적용 |
| 비교를 상수화하며 잠재적 div-zero·shift·signed overflow 제거 | 평가되는 식의 안전한 지원 범위를 확인해 제안 보류 |
| 세션별 임시 입력 경로로 인한 표본 문맥 불일치 | 자문 전용 line marker 경로만 정규화, 실제 macro 문자열은 보존 |
| 잘린 마지막 trace 숫자를 짧은 정상 정수로 수용 | 인식한 레코드에 terminal newline 요구 |
| 추가 작업 window의 header 메모리 누락 | header + encoded output을 함께 예산·실제 길이 검사에 포함 |
| 괄호 아래 읽기 누락·위치 계산의 반복 prefix 스캔 | 실제 lvalue-to-rvalue 읽기 추적·line-start 색인 |

## 4. Rove4k 현재 입력에 적용한 범위

PR #12의 현재 확인 head는 `eb5e05b97284da5467733b03ef862826ea6f818c`다.
그 `engines/compact/tiny-entry-f/engine.c`는 분석에 사용한 이전 snapshot과
동일 bytes임을 직접 확인했다. 크기는 25,755 B이고 SHA-256은
`ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd`다.

Clang C11·`-pthread`로 정본을 분석한 결과:

- 중복 typed constant 5그룹: `1000` 3곳, `1000000` 2곳, `0x88` 5곳,
  `1023` 2곳, `86400000` 4곳.
- 함수 26개에서 정수 읽기 99곳의 범위를 기록했다.
- AtomicExpr 또는 goto가 있는 함수 8개는 범위 분석을 보류하고 이유를 보고했다.
- 새 압축 후보는 0개, 원본 변경 없음. 이 정본에서는 추가 범위 축약 finding은 없었다.

처음 shipping compiler 인자의 `-Os`까지 전달한 시도는 기존 frontend 인자 정책에서
명시적으로 거절됐다. 이를 숨겨 성공 처리하지 않았으며 이후 결과는 `-Os` 없는 위의
선언한 분석 문맥이다. 실제 shipping용 생성 C·컴파일 문맥·최종 제출물의 분석이나
엔진 실행·크기 절감을 수행한 것으로 보고하지 않는다.

작은 공개 자체 예제 `examples/advice/program.c`에서는 사용자가 제시한 0x55 mask의
hex/decimal spelling을 같은 unsigned long long 값으로 묶었고, 미참조 선언 2개와
분기 문맥의 비교 축약 3개를 보고했다. 일반 루프·함수 호출 등에서 지원 범위를
넘으면 정적 사실을 넓히는 동작도 보고서에 남았다.

## 5. 전달 상태와 미완료 범위

PR #12 담당자용 인계 문서 `PR12-HANDOFF.ko.md`는 사용자의 요청에 따라
NVCompact PR #16에서 제거하고 별도 전달 파일로 보존했다. 살아 있는 문서 링크도
정리했다. 과거 측정 JSON을 다시 쓴 것은 아니다.

새 기능은 실제 압축에 관여하지 않는 자문 도구다. 메모리 모델, 일반 CFG 고정점,
함수 간 분석, 전체 dead-store/liveness는 구현 범위 밖이다. 실행 표본은 유한 관측이고,
계측 사본은 I/O·타이밍·스택·include 관측을 바꾸므로 shipping 성능·동치의 증거가 아니다.
probe는 async-signal-safe하지 않으며 signal/interrupt handler에 사용하지 않는다.

이번 작업은 엔진 A–F의 최종 4 KiB 적격성, D own-ELF, 실서버 자원·다코어 인수,
기력 비교를 완료하지 않았다. PR 병합과 npm 게시는 별도이며 수행하지 않았다.
실제 실행 지문·통과 범위는 [advice-validation.json](../evidence/pr16/advice-validation.json)에 둔다.
