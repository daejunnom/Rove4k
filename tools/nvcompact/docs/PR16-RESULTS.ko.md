# PR #16: 탐색 구조 개선과 같은 입력 회귀 비교

이 문서는 아래 고정 커밋에서 수행한 앞선 비교 기록이다. 이후 메모리·실행 비용
개선과 자문 도구의 새 측정·검사는 [후속 결과](PERFORMANCE-ADVICE-RESULTS.ko.md)에
구분한다. 이 문서의 26+7행을 후속 구현에서 재실행한 것으로 보고하지 않는다.

**같은 입력의 원래 26행에서 크기 회귀 0건, 최소 파일 SHA 동일 26행, 독립 replay 26/26을 확인했다.** Wrapper 원문을 보존하는 별도 7행도 크기·SHA가 같고 원문 복원·독립 replay 7/7을 통과했다. 원래 matrix의 Python embedding 7행은 외부 관측 전제가 별도로 필요한 조건부 측정이며, 전체 wrapper의 의미·TCEC 인수로 승격하지 않는다.

이번 고정 입력에서는 추가 바이트 절감이 없었다. 탐색 범위·admission 기회와 재사용 구조를 개선했으나 이를 새 압축률 이득으로 보고하지 않는다.

이번 변경은 후보 공간, 탐색 순서, 의미 판정, 실제 제출 비용과 실패 보존의 소유권을
분리한다. 단독으로 이기지 못한 spelling도 조합하고, source 탐색과 최종 비교에서
같은 전체 파일 평가기를 사용한다. 최종 파일의 추가 절감, 선언한 공간의 조사 완료,
일반적인 의미 보존, 기력 향상은 서로 다른 주장으로 구분한다.

## 1. 고정한 코드와 입력

| 구분 | 기준 |
| --- | --- |
| 측정한 구현 커밋 | `04d4a553bf36744b49f414834381ad7e26d8ea12` |
| 구현 tree | `441ef779321d740ad3b41869b5303cd45529cd80` |
| 통합 기준 develop | `9b73693216ea289681a59e93902c52d16a3894a7` |
| 같은 입력을 처리한 이전 NVCompact | `29dfde6916017b6b78d0cc1ee9f97f5a70f392e2` |
| 이전 실행 파일 SHA-256 | `2971a68daca0558241516b94353adab00137a22a8b62664ee5197eec2ea5145f` |
| 최종 실행 파일 SHA-256 | `dd1bb60450590f5a734690a6a45c87933d235e5f69f7d4d5b5a1e03ae858ce66` |
| A–F 비교 입력 | PR #12 `68db496f478735411e2036231f03e3f35c76f088` |
| PR #12 후속 검토만 한 최신 확인 head | `7a112cbf15f4efa5360b44dc2dbeece9e8ef5d52` (2026-10-21 10:03 UTC 원격 확인) |

전체 검사, release build, 비용 재사용 실험 사이에 소스·검사·example·Cargo 입력의
해시가 바뀌지 않았는지 확인했다. 빌드한 바이너리를 외부 고정 경로로 복사하고 같은
해시를 확인한 뒤 최종 비교에 사용했다. [검증 metadata](../evidence/pr16/validation.json)에
명령, 코드 tree, 입력별 해시와 build receipt를 남긴다. 후속 문서/evidence 커밋을
새 구현 바이너리의 실측인 것처럼 표시하지 않는다.

원래 26행은 외부 13개 부문·버전 행, A–F 9개 profile, 자체 예제 4개다.
서로 다른 엔진 26개라는 뜻이 아니다. 외부와 자체 예제는 역사적으로 고정한 입력을
사용하고 A–F는 위 `68db496f` 입력을 쓴다. [PR #13 결과](PR13-RESULTS.ko.md)의
과거 A–F `0e716…` 입력이나 후속 PR #12의 엔진 변경을 이번 NVCompact 개선량과
합치지 않는다.

## 2. 수정한 원인과 책임 경계

| 책임 소유자 | 실제 변경 |
| --- | --- |
| `PreparedSource` / `FrontendSession` | 한 불변 basis의 토큰·원본 AST·타입/binding 서명과 실행 문맥을 소유한다. 같은 basis를 쓰는 생성·spelling·가능한 flow 분석이 원본 준비를 재사용하고 변경 후보는 다시 검증한다. |
| `SourceContext` | 한 실행의 최초 원본 preprocessing 관측을 유지한다. 새 round가 바뀐 include 상태를 새 정상 기준으로 받아들이지 않게 한다. |
| `RunBudget` / `WorkWindow` | 실행·phase의 신규 시작 예산과 이미 시작한 후보의 bounded 완료를 구분한다. 취소·보존 실패·frontend 중단이 시간 초과로 덮이지 않게 한다. |
| `EvidenceJournal` / `CostMemo` | archive 보존과 같은 비용 문맥의 재사용을 각각 소유한다. 비용 cache hit를 의미 검증 성공으로 올리지 않는다. |
| `RoundSpace` / `WorkQueue` | basis·선택지·실제 accepted prefix·다음 singleton/subset 위치를 함께 소유한다. 단독 손해인 선택지도 유지하고 중단한 queue를 이어 간다. |
| `Incumbent` / `SeedFinalizer` | source·payload·score·실제 재생 경로를 묶는다. 같은 basis의 sibling winner는 그 basis의 prefix에서 재구성하며 최종 winner와 별도 priority seed에 같은 fresh/native 계약을 적용한다. |
| `WholeFileObjective` | inspected header·decoder·codec 정책·유한 cache·worker를 소유한다. Source 탐색과 최종 envelope가 같은 전체 파일 비용을 사용한다. |

파일·타입 수를 SRP의 증거로 삼지 않는다. 공통 처리를 소비하는 경계와 상태 수명을
바꾼 것이 핵심이다. [구조 문서](SEARCH-ARCHITECTURE.ko.md)에 구현 링크와 계약을 둔다.
루트와 NVCompact의 `AGENTS.md`에는 원인 경계 수정, 상태 소유, 재사용 계약, 탐색
범위의 정직한 보고를 남겼다. 현재 타입 배치나 두 전략을 영구 규약으로 고정하지 않는다.

### 실측에서 드러난 scheduling 문제도 수정했다

전체 codec 목적에서 singleton과 payload style을 먼저 모두 채점하면, 채점만으로
300초를 소모해 admission과 조합이 시작되지 않을 수 있었다. 앞선 `32fa6de`의 완료
결과도 보존하며 이 문제를 단순 시간 상향이나 입력별 예외로 처리하지 않았다.

현재 제출 codec 전략은 `legacy_priority`, 전체 codec 전략은 `interleaved_online`이다.
Online은 singleton과 subset을 교대로 조사하고 실제 개선값을 얻으면 바로 공통
admission을 진행한다. 초기 round/family에 남은 예산의 몫을 배정하고 미완료 queue는
초기 phases 뒤에 같은 위치에서 재개한다. 이미 시작한 후보의 유한 검증을 마칠 수
있다는 것이 새 후보 시작 기한이나 취소·보존 한도를 무시한다는 뜻은 아니다.

Deferred fixed-codec 승자가 기존 priority source를 대체해도 그 source가 다른
최종 codec에서는 더 좋을 수 있다. 따라서 필요하면 추가 fresh slot을 예약하고
priority seed도 공통 finalizer로 검증해 최종 envelope 비교에 남긴다. 보고서의 seed
개수와 실행 strategy 개수는 다르며 같은 strategy/detail report를 seed마다 합산하지 않는다.

### 재사용한 문맥이 달라지면 실행을 중단한다

원본 AST 재사용과 별개로 성립한 `SourceContext`는 baseline, admission, final 경계의
전후를 최초 preprocessing 관측과 대조한다. Accepted step이 있는 replay도 새 원본
관측을 대조하며 step이 없는 identity replay는 기존 native/embedding 경로를 사용한다.
감싼 compile/fresh 작업이 실패해도 사후
확인을 수행하며 문맥 변화는 typed 오류로 남긴다. 단순 후보 거절이나 선택적 capacity
중단으로 숨기지 않는다. 완료한 native 영수증은 사후 확인 전에 보존한다.

최초 AST/preprocessing을 출력 한도 때문에 얻지 못한 경우에는 그 사실을 밝힌 원본
보존 경로가 가능하다. 이미 성립한 문맥이 바뀌거나 재확인에 실패한 경우와 다르다.
최초 관측이 성립한 실행에서는 원본을 선택한 경로에도 최종 문맥 확인이 있다.
이것은 실행 중 관측한 일관성 확인이며
모든 header/library의 영구 snapshot이나 임의 동시 변경에 대한 격리를 증명하지 않는다.

## 3. n-versions의 실제 범위

Spelling 선택지 `n`개에 대해 크기 2 이상 부분집합은 `2^n - n - 1`개다.
이들을 lazy iterator로 만들어 메모리에 powerset을 미리 올리지 않는다. 단독 손해·동률
선택지도 조합하며 전체 payload 비용을 다시 측정한다. 개별 절감량의 합으로 비용을
추정하지 않는다. 겹치는 edit와 binding 충돌은 적용 불가로 기록한다.

| 공간 | 완료 주장이 적용되는 범위 |
| --- | --- |
| Source spelling | 실제 방문한 불변 basis에서 생성·보존한 선택지와 부분집합. 아직 생성하지 않은 이름·새 basis를 거치는 모든 경로는 포함하지 않음 |
| 조건식/flow | 등록한 recipe, 개별 edit와 pass 제한. 모든 flow 편집 조합·순서는 아님 |
| `CodecPortfolio::fixed(recipes)` | 선언한 유한 recipe 목록. 목록 밖 설정은 포함하지 않음 |
| 기본 envelope codec | 기존 initial/submitted recipe와 측정값에 따라 선택한 refinement. Adaptive 휴리스틱 |

기본 한도는 전략마다 round 2, payload 평가 2048, 조합 시도 16384, scheduling 300초다.
충돌 조합도 시도 한도를 사용한다. Online의 조합 한도에 도달해도 남은 singleton lane은
조사할 수 있다. 두 전략을 실행하면 평가 4096·조합 32768·scheduling 600초이며,
진행 중 bounded 작업과 최종 수락·envelope 비교까지 포함한 명령 전체의 hard timeout은 아니다.

Report는 실제 시도·미조사 singleton/subset, 초기 quantum, 재개, 공간 소진과 비용
평가 완료를 나눈다. `completed`, `budget-exhausted`, `space-incomplete`를
구분하며 `all_equivalent_programs_explored`와 `all_rewrite_sequences_explored`는
`false`다. 같은 source/native라는 사실만으로 General의 다른 payload를 비용상 합치지 않는다.

### 최종 비교에서 관측한 탐색 범위

| 입력 | 비용 전략 | 평가 수 | 부분집합 시도 | 최종 step 수 | 종료 상태 |
| --- | --- | ---: | ---: | ---: | --- |
| Moonfish | 제출 codec | 2047 | 1424 | 3 | budget-exhausted |
| Moonfish | 전체 codec | 55 | 22 | 0 | budget-exhausted |
| A | 제출 codec | 2048 | 0 | 2 | budget-exhausted |
| A | 전체 codec | 648 | 91 | 1 | budget-exhausted |
| B | 제출 codec | 2048 | 0 | 2 | budget-exhausted |
| B | 전체 codec | 530 | 71 | 2 | budget-exhausted |
| C | 제출 codec | 4 | 0 | 0 | budget-exhausted |
| C | 전체 codec | 4 | 0 | 0 | budget-exhausted |
| E | 제출 codec | 2048 | 0 | 1 | budget-exhausted |
| E | 전체 codec | 569 | 74 | 3 | budget-exhausted |
| F material | 제출 codec | 2048 | 0 | 2 | budget-exhausted |
| F material | 전체 codec | 650 | 86 | 2 | budget-exhausted |
| F move-TT | 제출 codec | 2048 | 0 | 2 | budget-exhausted |
| F move-TT | 전체 codec | 729 | 98 | 1 | budget-exhausted |
| F full | 제출 codec | 2048 | 0 | 2 | budget-exhausted |
| F full | 전체 codec | 612 | 82 | 1 | budget-exhausted |

전략 report 16개 중 선언한 basis 공간이 미완료인 것은 14개다. 중단된 공간을 완료로 보고하지 않았다. 각 basis의 미조사 선택지 수, quantum과 중단 사유는 비교 metadata에 남긴다.
나머지 2개인 C의 두 전략은 Clang 출력 32 MiB 한도에서 basis 생성 전에 중단됐다. 빈 basis 목록의 declared_basis_spaces_complete=true는 생성 성공이나 source 탐색 완료를 뜻하지 않으며, 실제 상태는 두 경우 모두 frontend-output-budget의 budget-exhausted다.

E의 전체 codec 전략은 앞선 실행의 조합 0개·최종 step 0개에서 이번 조합 74개·최종 step 3개로 진행했다. 최종 envelope의 추가 절감 여부는 아래 최소 파일 표에서 별도로 판단한다.

같은 strategy의 여러 seed는 위 통계에서 한 번만 센다. `accepted_steps`는 해당
최종 source의 재생 경로 길이이며 실행 중 모든 admission 횟수와 같다고 해석하지 않는다.
`frontend_work`는 추적한 priority/online/systematic 및 condition-generation 준비 객체의
부분 통계다. SourceContext와 임시 admission·replay 등 전체 Clang 호출을 포함하지 않는다.
기존 버전의 동일 범위 AST 총량을 계측하지 않아 AST 호출 감소율을 주장하지 않는다.

## 4. 중복 비용 재사용의 실측

자체 inert payload 8개를 각 16회, 고정 gzip recipe 3개로 평가했다. 정책당 4회,
양쪽 정책이 먼저 실행되는 경우를 각 2회로 교대했다. `jobs=1`이며 engine·shell·compiler는
실행하지 않았다. 각 실행에서 128번의 전체 파일 objective 호출이 384개 recipe 비용을
요청한다. 최종 artifact의 SHA는 반복·정책·trial 사이에서 모두 같았다.

| 실행당 지표 | Cache 비활성 | Cache 활성 |
| --- | ---: | ---: |
| 실제 codec 호출 | 384 | 24 |
| Codec cache hit | 0 | 360 |
| Header 도출 | 385 | 1 |
| 측정 시간 중앙값 | 68.37 ms | 8.92 ms |
| 측정 뒤 별도 fresh codec 호출 | 24 | 24 |

측정 시간의 중앙값 비율은 약 **7.67배**다. 이 수치는 수십 ms 규모의 로컬 반복 비용
실험이며 실제 엔진 압축 전체의 속도 향상률이 아니다. 타이머는 objective 생성, 압축·복원,
후보 기록, 전체 artifact 구성과 hashing을 포함한다. 별도 untimed warmup은 없고 fresh
확인 타이머는 따로 기록했다. Fresh는 이전 winner 하나가 아닌 고정 recipe 목록 전체를
다시 평가했고 모든 고유 입력에서 동일 artifact를 얻었다.

Cache에는 압축·복원에 성공한 결과만 넣는다. Payload SHA-256·길이·완전한 typed
recipe와 고정 objective 문맥을 키로 사용한다. 기본 retained 한도는 codec 64 MiB /
4096 entries, header 1 MiB / 16 entries다. 활성 codec scratch·복원 버퍼를 포함한
전체 프로세스 메모리 한도는 아니다. Worker는 batch의 여러 window에서 재사용하고
동률은 recipe 순서로 정한다. Fresh·독립 replay는 cache 성공으로 대신하지 않는다.

실제 회귀 matrix에서는 envelope 행 22개 중 objective 통계가 있는 17개를 합산했을 때
codec 요청 1,673,361회 중 cache hit가 372회, 약 **0.022%**였다. 실제 codec 실행은
1,672,989회, 별도 fresh 실행은 2,006회다. Header 도출 95회와 header hit 1,673,283회는
다른 종류의 작업이다. 나머지 5개 ELF 직접 경로에 codec cache 성공을 가정하지 않는다.
고유 source strategy report 16개의 retained 비용 요청은 18,411회이며 memo hit 304회다.
이 숫자들은 한 payload 평가와 그 안의 여러 codec 평가를 서로 다른 단위로 센다.
실제 codec hit 비중이 작고 새 탐색은 더 많은 후보를 평가하므로, 반복 입력 실험의
7.67배를 전체 엔진 비교의 가속으로 적용할 수 없다. 실제 source 탐색에는 동일 입력
재사용 외에도 새로운 payload의 압축 비용을 줄이는 별도의 연구가 필요하다.

재실행 접점:

```sh
cargo run --release --locked -p nvcompact --example cost_reuse
```

[Example](../examples/cost_reuse.rs), [개별 trial과 work 통계](../evidence/pr16/cost-reuse.json),
[실행 receipt](../evidence/pr16/validation.json)를 함께 보존한다.

## 5. 같은 입력의 최소 파일 크기

단위는 byte다. `입력`은 전체 제출 파일, `이전`은 이번 같은 입력을 이전 NVCompact로
처리한 최소, `현재`는 고정한 최종 바이너리 결과다. 입력→이전의 절감은 PR #16의
새 이득이 아니다. 자체 build 예제에는 단일 입력 제출 파일이 없어 `—`로 표시한다.

`†`의 7개 행은 아래 wrapper 관측 계약에 따른 **조건부 source-search 측정**이다.
다른 행에도 이 표만으로 UCI·기력·실제 TCEC 서버 인수가 성립하는 것은 아니다.

| 부문/범위 | 입력/profile | 입력 | 이전 | 현재 | 추가 절감 |
| --- | --- | ---: | ---: | ---: | ---: |
| General | 4k.c | 3932 | 3932 | 3932 | 0 |
| General | 4ku | 4093 | 4088 | 4088 | 0 |
| General | M4sseur | 4095 | 4092 | 4092 | 0 |
| General | STRO4K | 4096 | 4078 | 4078 | 0 |
| General | c4ke | 4093 | 4092 | 4092 | 0 |
| General | ice4 | 4087 | 4082 | 4082 | 0 |
| General | molly | 4096 | 4095 | 4095 | 0 |
| General | Moonfish | 3941 | 3871 | 3871 | 0 |
| General | pygone | 4093 | 4020 | 4020 | 0 |
| General | Sunfish | 2844 | 2776 | 2776 | 0 |
| General | we4k | 4079 | 4011 | 4011 | 0 |
| own-ELF | 4k.c v8.0 | 4042 | 4042 | 4042 | 0 |
| own-ELF | 4k.c v9.0 | 3932 | 3932 | 3932 | 0 |
| A–F | A † | 4610 | 4580 | 4580 | 0 |
| A–F | B † | 5144 | 5097 | 5097 | 0 |
| A–F | C † | 4952 | 4938 | 4938 | 0 |
| A–F | D HQ | 6148 | 6148 | 6148 | 0 |
| A–F | D scalar | 5937 | 5937 | 5937 | 0 |
| A–F | E † | 5011 | 4970 | 4970 | 0 |
| A–F | F material † | 4325 | 4293 | 4293 | 0 |
| A–F | F move-TT † | 4051 | 4018 | 4018 | 0 |
| A–F | F full † | 4537 | 4505 | 4505 | 0 |
| 자체 예제 | native-build | — | 16056 | 16056 | 0 |
| 자체 예제 | mixed | — | 504 | 504 | 0 |
| 자체 예제 | zero-tail | — | 441 | 441 | 0 |
| 자체 예제 | c-rewrites | — | 2141 | 2141 | 0 |

원래 26/26행의 같은 입력 비교와 새 recipe의 독립 replay가 완료됐다. 크기 회귀는 0건, 이전 winner와 SHA까지 같은 행은 26개다. 이번 고정 입력에서는 추가 바이트 절감이 없었다. 탐색 범위·admission 기회와 재사용 구조를 개선했으나 이를 새 압축률 이득으로 보고하지 않는다.

4096 B ceiling과 이전 결과 대비 회귀는 별개다. D 두 profile처럼 이전과 같더라도
4096 B를 넘을 수 있다. `native-build`는 압축 없이 링크하는 경로로, 제출 규격 통과를
목적으로 한 행이 아니다.

### Wrapper 원문을 보존하는 별도 7개

같은 원본 artifact에서 `source_search`를 제거하고 Python notation을 opaque로
지정한 외부 manifest 사본을 양쪽 버전에 똑같이 사용했다. 엔진 이름 예외나 도구 내부의
검사 완화를 추가하지 않았다. 원래 matrix를 이 좁은 portfolio의 baseline으로 덮지 않는다.

| Profile | 이전 | 현재 | 원본 bootstrap 복원 | 독립 replay |
| --- | ---: | ---: | --- | --- |
| A | 4598 | 4598 | 동일 | 통과 |
| B | 5139 | 5139 | 동일 | 통과 |
| C | 4938 | 4938 | 동일 | 통과 |
| E | 5004 | 5004 | 동일 | 통과 |
| F full | 4528 | 4528 | 동일 | 통과 |
| F material | 4316 | 4316 | 동일 | 통과 |
| F move-TT | 4044 | 4044 | 동일 | 통과 |

7/7에서 baseline과 최소 파일 크기·SHA가 같고 실제 decoder로 복원한 bootstrap payload가
원본과 byte-identical이다. 새 실행의 recipe를 같은 고정 바이너리로 독립 replay해
7/7 통과했다. 이 행들은 source 표기 탐색을 끈 별도 조건이며 위 source-search 행의
추가 절감이나 조건부 성공을 이 표의 성공으로 바꾸지 않는다.

## 6. 의미·관측 계약의 검증 범위

C native/진단 identity와 Python masked AST는 wrapper가 source/token/location/traceback을
관측하지 않는다는 외부 전제를 증명하지 않는다. 기존 A/B/C/E/F 7개 manifest의
`compile-input-only`와 `no-token-observation` 선언은 원래 비교를 재현하기 위해
유지하되 이 캠페인만으로 전체 wrapper의 의미 보존·제출 인수를 확정하지 않는다.
Tool report에도 호출자가 성립시켜야 하는 관측 전제임을 명시했다.

앞선 `32fa6de` 7개 실제 winner에서는 AST 위치와 CPython code/line metadata가
원본과 같았다. 따라서 그 실제 결과의 traceback 위치가 달라졌다고 주장하지 않는다.
개별 winner의 한정된 위치 관측과 모든 자동 후보가 만족해야 할 비관측 계약은 다르다.

최종 바이너리의 실제 최소 파일을 별도 bounded codec readback으로 복원해 Python winner 7개를 정적으로 비교했다. 상수값을 제외한 AST 구조 동일 7/7, AST 위치 동일 7/7, 재귀 code/line/exception-table/position metadata 동일 7/7였다. 이 검사는 ast.parse와 compile-to-code-object만 수행했고 code object를 실행하지 않았다. 상수값의 타입·길이·해시는 별도로 비교했으며 6개 winner에서 각각 embedded C의 bytes Constant 하나만 값이 달랐고 C profile은 원본 payload와 같았다. 값과 위치를 분리한 이 검사는 전체 Python 코드객체의 동일성이나 모든 실행 경로의 의미 동치를 증명하지 않는다. 개별 관측값은 comparison metadata의 bootstrap_static_observation_audits에 보존한다.

외부 엔진·Python bootstrap·custom ELF loader·UCI·대국은 실행하지 않았다. Header와
payload 복원, source 후보의 선언된 compiler/options에 대한 typed/binding·native·
진단 검사, 전체 파일 recipe 재생을 다뤘다. 자체 `mixed`, `zero-tail`, `c-rewrites`만
선언된 작은 산술 verifier를 사용했고 `native-build`는 build/replay를 비교했다.
대용량 ice4 실행·체스 규칙·기력·실제 TCEC 서버 인수로 결과를 확대하지 않는다.

## 7. 검증과 실패 이력

최종 코드의 로컬 Rust 검사 **87개**가 통과했다. Library 67개(105.76초), packing 10개
(21.68초), source-search 10개(196.77초)이며 실패·ignored·filtered-out은 0개다.
전체 명령은 331.84초, release build는 60.85초였다. 단독 손해 둘의 결합,
초기 phase 예산, 같은 basis의 sibling 재생, 조합 cap 뒤 singleton 진행, priority seed
fresh 예약, cache를 우회하는 fresh 불일치, include 문맥 변경, 보존 실패와 replay의
runtime pin 등 실제 경계와 반례를 검사했다.

[코드 커밋 NVCompact CI](https://github.com/daejunnom/Rove4k/actions/runs/39579034167)의
Node 22 job `119151734694`와 Node 24 job `119151734433`가 성공했다. Launcher,
comparison reporting, release/GitHub mirror 경계, Rust, native build, tarball, 실제
offline 설치 검사를 포함한다. [Repository lifecycle](https://github.com/daejunnom/Rove4k/actions/runs/39579034164)도
성공했다. 이는 npm 게시나 사람의 승인, 엔진 인수를 뜻하지 않는다. 후속 문서/evidence
head의 CI 관측은 PR 본문에 해당 head/run으로 따로 기록한다.

다음 실패·중간 실행은 후속 성공으로 덮지 않았다.

- PR #12 정본 build의 A/B/C/E/F 3개 profile, 총 7개 역사적 native pin이 현재 compiler에서
  일치하지 않았다. D scalar/HQ는 성공했다. 기대 해시를 새 출력으로 바꾸지 않았다.
- 별도 packaging으로 source·bootstrap·전체 제출 파일의 고정 해시를 복원했다. 이 성공은
  역사적 native build 실패를 해결한 것이 아니다.
- 초기 도구 준비·output-path guard 실패, source-context 수정 전 취소한 캠페인,
  구 recipe를 다른 바이너리로 재생해 runtime pin이 거절한 시도를 유지했다.
- 중간 바이너리의 18개, `32fa6de`의 26개 완료 비교는 각 바이너리·범위의 결과로 남긴다.
  마지막 실행의 성공으로 옛 record를 바꾸거나 recipe pin을 수정하지 않았다.

[비교 metadata](../evidence/pr16/comparison.json)에 각 실행·해시·replay와 이전 비교를,
[이전 검증 metadata](../evidence/pr16/iterations/32fa6de-validation.json)에 당시 검사를,
[현재 검증 metadata](../evidence/pr16/validation.json)에 현재 코드 검사와 build를 둔다.

## 8. 외부 커밋 조사와 PR #12 인계

[외부 조사 안내](EXTERNAL-SIZE-COMMITS.ko.md)는 총 **355개 선택 커밋 diff/기록**을
연결한다. Roster 대응 10개 엔진 계열 347건과 참가 미확인 Pytteliten 8건을 구분한다.
ice4 60, 4ku 55, 4k.c 91, c4ke 79, STRO4K 19, molly 15, pygone 11, Sunfish 10,
M4sseur 5, we4k 2, Pytteliten 8건이다. 355종의 성공한 무손실 최적화나 전체 history
감사라는 뜻은 아니며 미검토 SHA와 접근하지 못한 Moonfish history를 명시했다.

| 실제 upstream 근거 | 이번 판단 |
| --- | --- |
| Sunfish `eb8897cc`: shebang 삭제만으로 +4 B, literal hoisting 비활성화와 결합하면 3232→3210 B | 단독 크기 열세를 조합 자격에서 제거하지 않음 |
| STRO4K `48a8168d`: object 하나로 linker 4 × lc/lp 15 × pb 5 × match finder 5 비교, 당시 4073→4044 B 기록 | 동일 단계 입력 재사용, 선언한 유한 domain과 실제 완료 범위 구분 |
| 4k.c `9e4c8bb3`: 선언한 독립 그룹의 순열과 Cartesian product | 한정된 공간의 소진을 전역 프로그램 최적성과 구분 |
| 4k.c `33d8ab89`: persistent compressor와 수정 slot 복원 | 반복 준비 비용을 줄이되 warm heuristic을 증명된 pruning으로 승격하지 않음 |
| c4ke `e3e6858c`: 삼항식의 조건부 대입을 `if`로 되돌림 | 짧은 source 표기를 유일한 canonical form으로 고정하지 않음 |
| 4ku `f2be6e67`: 짧은 unused 인자를 더 긴 반복 표현으로 변경하는 등 혼합 수정 | 전체 patch 3988→3983 B. 5 B를 인자 하나에 귀속하지 않음 |

위 크기는 **upstream 당시 기록**이다. 이번 NVCompact 실측이나 Rove4k 예상 절감량으로
환산하지 않는다. Packed-score 괄호 오류, minified bench가 원본을 컴파일한 오류,
TT 초기화 누락 등 실패 수정도 분류했다. 모든 근거의 full SHA·URL·검토 범위는
[기본 3개 엔진](research/PRIMARY-ENGINE-BYTE-COMMITS.ko.md)과
[나머지 엔진](research/OTHER-ENGINE-SIZE-COMMITS.ko.md), 연결된 metadata에 있다.
외부 원본·전체 patch·실행 파일·가중치는 벤더링하지 않았다.

엔진 담당자용 인계 원문은 사용자 요청에 따라 별도 전달 파일로 보존하고 PR에서 제거했다.
이 절과 연결된 연구·metadata는 당시 조사 결과를 보존한다.
범용 후보와 엔진 불변식·기력 판단이 필요한 변경을 나누며, movegen/search API,
field/table 배치, 공유 evaluation 순회, sentinel, TT·thread 정책과 loader/ABI 변경을
이름별 예외 rewrite로 넣지 않는다.

후속 head `b65a7498`의 엔진 변경 4개 커밋, 관련 18개 파일의 변경 hunk와 새 helper
3개도 읽었다. C continuation slot·양수 bonus, D clock/inc parser 공유, E argv
`.split()`, full F depth/repetition·고정 macro는 **이미 반영된 방법**으로 표시했다.
후속 recipe의 C 4934, D 5914/6125, E 5010, full F 4505 B는 해당 PR의 기록이며
이번 고정 입력 캠페인의 결과가 아니다. B/C argv와 F formatter 등 열세 결과도 남겼다.

최종 원격 확인에서 추가된 `7a112cbf`의 17개 변경 파일과 다섯 bootstrap 본문도 읽었다.
환경 복사와 TMPDIR 대입을 `dict(os.environ,TMPDIR=d)`로 표현한 변경은 이미 채택된
기술로 당시 인계 기록에 추가했다. 새 helper는 없으며, 후속 기록은 A 4606, B 5138,
C 4924, E 5004, F full/material/move-TT 4497/4319/4045 B다. Signal helper와 결합
후보의 크기 열세도 보존했다. 이는 수동 wrapper 관측 계약 아래의 후속 PR #12 기록이며
이번 NVCompact 실측·현재 자동 embedding의 인수나 범용 Python rewrite로 취급하지 않는다.

## 9. 남은 구조·성능 개선 여지

이번 변경이 모든 동등 코드 생성기나 모든 중복을 제거한 것은 아니다.

- 두 source 전략의 baseline native·일부 frontend 준비·후보 생성은 각각 실행한다.
  향후 source 공간을 공유할 수 있으나 서로 다른 비용 문맥·proof를 합치면 안 된다.
- 새 payload의 full-codec 압축은 실제 계산이 필요하다. 같은 입력 cache의 효과를
  비슷한 입력이나 전체 캠페인 시간에 그대로 적용할 수 없다.
- 병렬화는 codec batch에 한정된다. Source 생성·native compile, 모든 평가에 걸친
  상주 worker pool은 후속 검토 대상이다. 취소·출력 소유권·메모리·결정적 수락 순서를
  함께 설계해야 한다.
- Lazy 부분집합은 지수적인 경우의 수를 없애지 않는다. 증명 가능한 충돌의 사전 인덱싱과
  edit 구조 공유는 가능성이 있으나 휴리스틱 탈락을 전수 조사로 표시하면 안 된다.
- Legacy priority의 비용 정렬·greedy composition·condition 조정 경로는 남아 있다.
  기존 순서를 보존하는 제안 정책으로 표현해 공통 admission을 더 통합할 여지가 있다.

Final fresh·native 재확인·독립 replay는 의도적으로 유지한 검사다. 같은 실패를 분기마다
덧붙이기보다 공통 입력·상태의 소유자와 적용 전제를 수정한다는 규약을 후속 개선에도 적용한다.

