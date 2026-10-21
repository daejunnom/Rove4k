# NVCompact 탐색 구조와 완료 범위

NVCompact는 후보를 만드는 일, 탐색 순서와 예산, 의미 판정, 실제 제출 비용,
실패 근거의 보존을 서로 다른 소유자가 처리한다. 이 문서는 현재 구현의 책임과
관측 가능한 한계를 설명하는 기술 문서다. 구체적인 타입, 파일 배치와 후보 전략을
이후 설계의 고정 규약으로 삼지 않는다.

이 변경에는 develop `9b73693216ea289681a59e93902c52d16a3894a7`의 0.5.0
메타데이터와 출시 문서를 유지했다. 아래 구조 설명은 과거 출시 산출물의 동작,
현재 변경의 배포 완료, 또는 실측 성공 기록과 구분한다. 입력 선언과 명령 사용법은
[source portfolio 안내](SOURCE-PORTFOLIO.md), 과거 릴리스 범위는
[0.5.0 출시 기록](RELEASE-0.5.ko.md)에 둔다.

## 1. 해결하는 문제

이전 탐색은 단독으로 작아진 spelling만 조합하고, 채택한 집합에 하나씩 추가했다.
같거나 더 큰 단독 후보를 보존하더라도 조합 대상으로 삼지 않으면, 둘을 함께
적용할 때 압축이 좋아지는 경우를 찾을 수 없다. 또한 제출된 codec 하나의 승자만
최종 codec 비교에 보내면 다른 codec에서 더 유리한 source를 놓칠 수 있다.

현재 구현은 기존 개선 순서를 먼저 실행하고, 방문한 각 기준 source의 spelling
부분집합을 별도로 조사한다. Envelope에서는 제출 codec 우선 전략과 전체 codec
정책을 비용으로 쓰는 전략이 같은 평가기를 공유하며 각 승자를 최종 비교에 남긴다.
재사용은 후보의 source/native/제출 파일 정체성을 합치는 방식으로 처리하지 않는다.

## 2. 책임과 실제 소유 상태

| 소유자 | 소유하는 입력과 상태 | 소비자에게 제공하는 결과 |
| --- | --- | --- |
| `FrontendSession` | 고정 Clang 실행 경로·해시, 언어·ABI·include 설정, 임시 translation unit, 프로세스 한도와 실행 통계 | AST·macro·preprocessing 관측, 문맥 재확인, 구체적인 실행/용량 오류 |
| `SourceContext` | 한 search/replay의 원본 source, 전용 frontend session, 최초 preprocessing 바이트의 관측 | Round·candidate AST 수명과 독립적인 실행 문맥 재확인; 변환이나 AST 의미 증명을 제공하지 않음 |
| `PreparedSource` | 불변 기준 source, spelling 설정, 토큰, 원본 AST와 타입/binding 서명, 해당 frontend session | 후보 생성, 같은 basis의 edit 조합, 변경 후보 검증, 설정이 맞는 flow 분석에 원본 관측 제공 |
| `Combinations` | 선택지 수와 다음 부분집합의 인덱스 | 거대한 powerset을 미리 만들지 않는 결정적 iterator |
| `RoundSpace` | 방문한 priority basis, 그 basis의 후보, 그곳에 도달한 accepted-step prefix | Deferred systematic 탐색과 재생 가능한 branch 복원 |
| `RunBudget` | 시작 시간, 평가 횟수·상한, scheduling deadline, 중단 사유 | 신규 탐색·기존 측정 후보 검증 가능 여부와 취소 확인 |
| `EvidenceJournal` | 외부 archive, 상세 기록·바이트 수, 보존 중단 영수증 | 측정 전 후보 snapshot 보존, 성공·실패·미완료 기록 |
| `CostMemo` | 한 source-search 실행 안의 payload 해시 → 전체 파일 비용 | 같은 payload의 비용 재사용; 의미 판정이나 독립 재현을 제공하지 않음 |
| `SearchRun` | 위 실행 소유자와 실행 수명의 `SourceContext` 조립, frontend 용량 중단 상태 | 생성·측정·admission 순서와 문맥 관측 경계 조정 |
| `CodecPortfolio` | 고정 recipe 목록 또는 legacy 생성·refinement 정책 | 실제 조사할 codec 순서와 그 범위 |
| `WholeFileObjective` | Inspected header·decoder, codec 정책, worker 한도, 제한된 codec/header cache | 전체 header와 encoded payload 비용, 실제 후보, fresh 재생성과 재사용 통계 |
| `envelope_source` | 동일 원본에 대한 전략 순서와 서로 다른 objective view | 전략별 결과·archive를 분리한 최종 payload 후보들 |

구현 근거는 [공통 frontend](../src/c_frontend.rs), [준비된 source](../src/csource.rs),
[탐색기](../src/source_search.rs), [런타임 상태](../src/source_search/runtime.rs),
[부분집합 계획](../src/source_search/plan.rs), [codec 정책](../src/codec.rs),
[전체 파일 평가기](../src/envelope_cost.rs), [전략 조정](../src/envelope_source.rs)다.

## 3. 원본 분석 재사용과 다시 확인하는 경계

한 `PreparedSource` 안에서는 원본 토큰·AST·binding 서명을 후보마다 처음부터
구하지 않는다. 같은 frontend 설정의 spelling/flow 분석도 원본 관측을 공유할 수 있다.
기준 source가 바뀌면 새 준비 객체를 만들며, deferred round마다 AST를 계속 보관하지
않고 source와 derivation을 보관한 뒤 해당 basis를 다시 준비한다.

원본 관측의 재사용에는 현재 preprocessing 확인이 따른다. Clang 실행 파일은 실제
호출 전후에 확인하고, cached 원본 AST를 검증 근거로 쓰기 전후에 include·macro
문맥의 preprocessing 해시를 다시 대조한다. 변경 후보는 새로운 AST를 얻는다.
후보 parse가 실패해도 원본 문맥을 다시 확인하므로 include 변경으로 생긴 실패를
후보 하나의 의미 거절로 숨기지 않는다.

이 round별 AST 재사용과 별개로 `SourceContext`는 한 source-search 실행의 최초
원본 preprocessing 관측을 끝까지 소유한다. 이후 기준 source나 `PreparedSource`가
바뀌어도 관측 기준을 새 header 상태로 교체하지 않는다. 이 guard 자체는 AST나
LP64 probe를 요구하지 않으며, header의 비 UTF-8 바이트도 그대로 해시한다.
이는 spelling 분석의 별도 타입 모델·인코딩 계약을 완화하지 않는다.

실행 수명의 guard는 baseline native 두 번과 초기 비용, admission의 실제 native
컴파일, 변경 source의 final native와 fresh 비용 같은 경계의 전후를 관측한다.
`observe`로 감싼 작업이 실패해도 사후 문맥 확인을 수행하며, 문맥과 작업이 함께
실패하면 작업 오류 설명을 남기면서 typed `FrontendContextChanged`를 유지한다.
Native 작업의 `observe_record`는 완료된 컴파일 영수증을 사후 문맥 확인 전에 보존하고,
영수증 저장 자체의 실패도 관측 대상 작업 안에 둔다. 증거 저장 오류가 동시에 발생한
문맥 변화를 가리지 않게 하기 위함이다. 사전 관측이 실패하면 해당 작업을 시작하지
않는다. 일반 후보의 비용 측정마다
preprocessing을 반복하지는 않는다. 비개선 후보만 조사해 원본을 선택한 경로에도
최종 recheck가 있으므로, source byte identity가 실행 중 변한 문맥의 수용 근거가
되지 않는다. 후보 비용 자체의 오류는 여전히 실행 실패이며, 모든 비용 오류가
문맥 변화로 재분류된다고 주장하지 않는다.

AST/preprocessing 출력 한도는 별도의 상태다. 같은 설정의 syntax-only 확인이
성공한 초기 관측·후보 분석의 용량 부족은 `frontend-output-budget`으로 기록할 수
있으며 잘린 출력은 AST나 증명으로 인정하지 않는다. 최초 관측을 만들지 못한 경우에는
guard가 없는 용량 중단 상태로 baseline 검사와 원본 보존 경로만 남는다. 이미 성립한
원본 관측을 재확인하다 include 읽기·preprocessing·출력 한도에 실패하거나 내용이
달라진 경우는 `FrontendContextChanged`다. 이를 `semantic-rejected`나 선택적인
용량 중단으로 바꾸지 않는다.

수락된 source derivation step이 있는 독립 `replay`는 새 원본 `SourceContext`를
만들고 baseline, step 재구성·native, final native 경계를 관측한다. Step이 없는
source identity replay는 기존 native/embedding 검사 경로를 사용하며 이 guard를
실행했다고 표시하지 않는다. Search report의 `source_context`는 실행 수명의 관측과
작업 통계를 `frontend_work`의 round별 분석 통계와 구분해 남긴다. 이 관측은 해당
실행 안에서의 일관성 확인이며, 과거 replay 실행과의 영구 include snapshot 일치나
모든 동적 라이브러리의 동일성을 증명하지 않는다.

## 4. 실제 spelling 탐색 공간

각 전략은 다음 순서로 실행한다.

1. 원본 native를 두 번 대조하고 원본 전체 파일 비용을 측정한다. 선언된 embedding의
   literal 표기 대안도 전체 payload로 비교한다.
2. 기존 priority round를 먼저 수행한다. 같은 basis에서 생성한 spelling을 측정하고,
   개선 single을 안정된 순서로 검증·조합한 뒤 조건식 recipe를 조사한다. 각 round의
   모든 보존된 spelling 선택지는 단독 비용과 관계없이 deferred 공간에 남긴다.
3. Priority round가 끝나면 각 방문 basis의 크기 2 이상 부분집합을 작은 cardinality부터
   lazy iterator로 조사한다. 겹치는 edit와 binding 계약 충돌은 적용 불가로 기록한다.
   동일 source 바이트는 중복으로 셀 수 있지만 비용과 검증 성공을 새로 만들어내지 않는다.
4. 조합은 실제 전체 payload로 측정한다. 개별 절약량을 더하지 않는다. 현재 승자보다
   작고 source/native/embedding 검사와 증거 보존을 통과한 경우에만 교체한다.
   예전 basis의 조합이 이기면 그 basis에 해당하는 prefix로 recipe를 복원한다.

선택지 수가 `n`이면 nontrivial subset 수는 `2^n - n - 1`이다. 원본과 singleton은
앞 단계에서 다룬다. 숫자는 임의 정밀도 정수의 십진 문자열로 보고하며 실제 부분집합
목록은 미리 할당하지 않는다. 같은 함수의 대체 이름 충돌과 편집 겹침 등 composer의
적용 조건도 이 선언된 공간의 일부다.

`max_combinations`는 **전략당** 기본 16384, 허용 범위 1–1048576이다. 충돌로
거절된 부분집합도 시도 횟수에 포함한다. 비용 평가 한도와 별개이며, 생성 시의
`max_candidates`, 이름 그룹·대안 제한, source 바이트 제한을 없애지 않는다.
기본 `max_rounds=2`, `max_evaluations=2048`, `max_seconds=300` 역시 전략마다
적용한다. Deferred plan의 source buffer 한도는 64 MiB다.

따라서 완료 주장은 **방문한 priority basis에서 실제 생성·보존된 spelling 선택지의
부분집합**에만 적용한다. 아직 생성하지 않은 이름, 다른 source에서 시작한 경로,
systematic 승자 이후의 모든 재작성 순서, 모든 C 프로그램은 그 범위에 포함되지 않는다.
조건식은 등록된 all-rule/single-rule recipe와 제한된 개별 편집을 사용한다. 그 내부의
greedy non-overlap 선택과 pass 제한을 모든 flow 편집의 부분집합 탐색으로 부르지 않는다.

### 완료와 미완료의 구분

`coverage.basis_spaces`에는 basis 해시, generator 제한, 선택지 수, 부분집합 수,
시도·충돌·중복 횟수와 중단 이유를 기록한다. `exhausted`는 subset 열거의 소진이고,
`all_declared_costs_evaluated`는 해당 basis의 비용 탐색 완료다. 두 필드는 처음부터
명시적 값으로 존재한다. `declared_basis_spaces_complete`는 basis별 완료를 합친다.

최종 상태는 실제 실행 예산 중단인 `budget-exhausted`, plan 용량 등으로 선언 공간을
마치지 못한 `space-incomplete`, 해당 공간을 마친 `completed`를 구분한다.
`status_scope`는 generator의 더 넓은 후보 제한과 flow/codec 휴리스틱을 별도로
읽도록 명시한다. `all_equivalent_programs_explored`와
`all_rewrite_sequences_explored`는 `false`다.

## 5. Envelope의 기본 두 전략

Manifest에 최상위 `source_search`를 선언하고 notation을 활성화하면 다음 두 전략을
차례로 실행한다. `source_search`가 없거나 `--no-notation`이면 이 탐색을 시작하지 않는다.

| 순서·전략 ID | Source 선택 비용 | 결과와 증거 |
| --- | --- | --- |
| 1. `source-search` | 제출된 `envelope.payload_codec` 하나로 whole payload를 압축하고 해당 decoder의 전체 inspected header를 더한 비용 | 기존 목적의 승자를 유지하는 전략; 독립 source-search budget와 archive |
| 2. `source-search-portfolio` | 같은 whole payload에 현재 codec 정책을 적용해 얻는 최소 전체 파일 비용 | 다른 codec에서 유리한 source도 조사; 별도 budget·objective 문맥·archive |

두 전략은 원본에서 각각 시작한다. 두 번째가 첫 번째의 결과를 지우거나 그 비용을
자기 archive의 측정값으로 가져오지 않는다. 최종 비교에는 두 전략의 승자,
기존 notation 후보, 원본 전체 파일과 원래 압축 스트림이 함께 남는다. 동일 payload는
최종 후보에서 합치더라도 `canonical_variant`/`alias_of`와 전략별 근거를 유지한다.

필요하면 manifest의 **최상위**에 다음을 추가해 두 번째 전략만 명시적으로 제외한다.

```json
{"source_search_portfolio": false}
```

이 옵션의 기본값은 `true`다. `source_search` 내부 필드나 CLI 플래그가 아니다.
요약의 `source_search`는 첫 전략을 보존하는 호환 필드이며,
`source_search_portfolio` 배열에 모든 전략의 report·recipe·cost objective가 들어간다.
Archive는 각각 `source-search/source-search/attempts/`와
`source-search-portfolio/source-search/attempts/`에 생성한다.

전략별 한도는 공유된 단일 카운터가 아니다. 기본 두 전략의 합산 상한은 complete-payload
평가 4096회, 조합 시도 32768회, scheduling 시간 600초이며,
`source_search_budget`에 실제 활성 전략 수와 함께 기록한다. 한 payload 평가는 여러
codec 실행을 포함할 수 있다. 진행 중인 유한 작업과 최종 acceptance, 최종 codec 비교는
별도이며 600초를 전체 명령의 강제 종료 시각으로 약속하지 않는다. Source snapshot과
상세 기록 한도도 archive별로 적용한다.

이 보존 전략은 기존 순서와 후보를 지키려는 설계다. 모든 wall-clock 환경·toolchain·
자원 상황에서 과거 실행의 최소값을 반드시 재발견한다는 보장은 아니다. 실제 회귀
판정에는 같은 입력·도구·설정·실행 범위의 이전 파일과 현재 파일 비교가 필요하다.

## 6. Codec 정책과 전체 파일 비용 재사용

`WholeFileObjective`는 source spelling과 최종 codec 비교에서 공통으로 쓰인다.
비용은 전체 inspected header와 압축 framing을 포함한 whole payload다. Python
embedding의 escape와 수정하지 않은 bootstrap 바이트도 포함된다. Source 길이나
같은 native ELF를 전체 제출 비용의 대리값 또는 다른 source를 합치는 키로 쓰지 않는다.

Codec 영역에는 다음 두 모드가 있다.

| 정책 | 완료했다고 말할 수 있는 범위 |
| --- | --- |
| Rust API `CodecPortfolio::fixed(recipes)` | 순서를 보존하며 중복 제거한 명시적 recipe 목록 전체. 기본 refinement는 없음. 목록은 1–16384개이며 이 범위에서 source × codec 비교를 정의할 수 있음 |
| Envelope 기본 `CodecPortfolio::legacy(...)` | Legacy 초기 recipe와 제출 recipe, 그 측정값으로 선택한 refinement의 합집합. Source별 seed 선택은 adaptive 휴리스틱이며 가능한 모든 codec 옵션 조합은 아님 |

Legacy refinement는 기존 초기 집합만으로 선택했을 refinement와 제출 recipe를 추가해
선택한 refinement를 합친다. 새 seed 때문에 과거에 조사했을 refinement가 사라지지
않도록 하기 위함이다. `--thorough`는 이 유한 정책을 넓힌다. 고정 recipe API가 있다는
이유로 현재 envelope 기본 실행을 고정된 codec 공간의 전수 탐색으로 보고하지 않는다.

재사용 키는 한 objective의 고정된 header·codec 구현 문맥 안에서 payload SHA-256과
길이, 전체 typed `Recipe`다. Codec cache에는 압축 후 바이트 복원이 성공한 결과만
들어간다. Decoder별 header 도출도 같은 inspected header 안에서 재사용한다. 실패를
성공 cache로 만들거나 별도 source-search의 의미 판정 상태를 재사용하지 않는다.

기본 retained cache 한도는 codec 64 MiB/4096 entries, header 1 MiB/16 entries다.
FIFO 삽입과 동률 선택은 recipe 선언 순서를 따르므로 worker 종료 순서가 결과를
결정하지 않는다. Cache 예산은 활성 codec scratch·복원 버퍼, objective 입력,
현재 최선 artifact와 호출자 report 등을 포함하는 프로세스 전체 메모리 보장이 아니다.

Codec batch는 한 번에 최대 `jobs`개 recipe를 처리하며 같은 scoped worker를 해당
batch의 다음 window에서 재사용한다. Serial 또는 cache-only batch에는 worker thread를 만들지
않는다. Batch 종료·실패 시 worker를 join하며 다른 source 평가까지 worker가 살아 있는
전역 pool로 표현하지 않는다. `--jobs`는 source 생성이나 candidate compile을 병렬화하지
않는다. 통계는 실제 codec/header 실행, cache hit, 실패와 fresh 실행을 구분한다.

최종 변경 source의 `fresh_measure`는 retained codec/header cache를 우회한다.
Portfolio 전략은 이전 winning codec 하나만 다시 압축하지 않고 현재 정책 전체와
adaptive seed 선택도 새로 평가한다. 이후 envelope는 최종 채택 recipe의 전체 파일을
독립 재생성해 바이트를 대조한다. 별도 `replay` 역시 새 평가 경계를 사용한다.
원본 payload를 그대로 선택한 경우에는 `unchanged-input-baseline-measurement`로
표시하며 수행하지 않은 fresh 비용 검사를 주장하지 않는다.

## 7. 실패 보존과 검증 범위

후보는 비용 측정 전에 원본 basis와 snapshot, 재구성 가능한 derivation을 보존한다.
`EvidenceJournal`의 한도에 도달하면 새 candidate를 채택하지 않는다. 비용 탐색만
끝난 경우 이미 측정된 single은 검증할 수 있지만, 보존·시간 한도는 그 검증도 제한한다.
`RunBudget`는 최종 fresh 비용 측정 1회를 남겨 두고, `CostMemo`의 재사용은 그 검사를
대체하지 않는다. [실패 보존 안내](SOURCE-PORTFOLIO.md#7-preserve-attempts-and-compare-recorded-measurements)의
`compare-attempts`는 같은 objective의 기록을 비교하며 다른 전략의 비용을 섞어 순위를
만들거나 과거 명령을 실행하지 않는다.

검증 fixture는 다음 성질을 겨냥한다. 이 목록은 테스트 목적이며 특정 환경의 통과
개수나 외부 엔진 실행 완료를 보고하는 표가 아니다.

| 검증 대상 | 필요한 구분 |
| --- | --- |
| 단독 손해인 spelling 둘의 조합 | Raw/single 열세가 조합 후보 삭제로 이어지지 않는지 |
| 평가 3회·조합 1회 같은 작은 예산 | 측정 완료 single과 최종 fresh slot의 보존, 미완료 coverage |
| Fresh 비용 불일치 | Cache hit로 최종 재현 실패를 숨기지 않는지 |
| Include/frontend 문맥 변경 | Round AST와 독립인 원본 관측 수명, 실패한 관측 대상 작업의 오류 보존, 비개선 경로의 최종 확인과 fatal 분류 |
| Serial/parallel·cache eviction·worker 실패 | 바이트와 동률 순서, 실패 비재사용, worker 종료와 유한 보존 |
| 독립 source/ELF/payload와 재생 | Source가 다르면 codec 비용을 합치지 않고 accepted branch를 정확히 복원하는지 |
| 두 envelope 전략 | 별도 objective/archive·합산 한도·두 승자의 최종 유지와 역사 요약의 replay 호환 |

근거 코드는 [source-search 통합 fixture](../tests/source_search.rs),
[frontend 검증](../src/c_frontend.rs), [준비된 source 검증](../src/csource.rs),
[평가기 검증](../src/envelope_cost.rs)에 있다. Compiler·typed proof·압축 복원 검사는
실제 UCI, 대국 기력, 대용량 엔진 실행, TCEC 서버 인수와 구분한다.

## 8. 외부 절감 커밋과 엔진 핸드오프

[외부 절감 커밋 종합](EXTERNAL-SIZE-COMMITS.ko.md)은 실제 diff를 읽은 커밋을
의미 보존·엔진 전제·탐색/평가 변경·배포 조건으로 나누며, 채택 여부와 관계없이
아이디어를 보존한다. 개별 열세가 결합 이득으로 바뀐 기록, 링크·codec의 명시적
조합, 빌드 중간 결과 재사용과 실패 사례는 현재 설계 판단에 참고할 수 있다.
Upstream의 당시 보고 크기와 이 변경의 실측은 같은 결과로 취급하지 않는다.

엔진 전용 결정과 PR #12의 고정 head에서 이미 적용한 변경은
[PR #12 핸드오프](PR12-HANDOFF.ko.md)에 둔다. 그 자료는 범용 변환의 적용 전제와
분리한다. 외부 엔진 source·binary·전체 diff를 저장소에 벤더링하지 않으며,
압축 도구의 구조 개선을 새로운 엔진 기력이나 바이트 절감의 실측 증거로 삼지 않는다.
