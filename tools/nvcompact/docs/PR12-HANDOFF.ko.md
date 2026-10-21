# PR #12 엔진 담당자를 위한 압축 인계

이 문서는 NVCompact의 공통 변환과 엔진 지식이 필요한 변경의 경계를 정리한다.
최신 검토는 **PR #12의 `68db496f478735411e2036231f03e3f35c76f088`에 고정**한다.
진행 중인 PR의 이후 변경을 혼합하지 않으며 `0e716e0`/`8abcbc3` 기준 PR #13 인계와
크기 표는 2절에 역사로 보존한다. 새 엔진 설계를 고정하는 규약이나 모든 제안의
구현 지시가 아니다. 직접 PR #12에 댓글·메시지를 게시하지 않고 이 문서를 인계로 갱신한다.

외부 조사에서는 **355개 선택 커밋 diff/기록**을 검토했다. 그중 Pytteliten 8건은
실제 참가가 확인되지 않은 인접 참고다. 원본 외부 소스는 벤더링하지 않으며, 채택 여부와
무관한 아이디어·실패·조건은 [종합 안내](EXTERNAL-SIZE-COMMITS.ko.md)와 두 상세 catalog에 둔다.

## 1. 현재 고정 검토 기준과 반영 상태

검토일은 2026-10-21이다. 고정 head의 실제 shipping helper, builder 연결부,
D native diff와 recipe `expected`를 읽었다. [확인한 blob·SHA-256·범위](evidence/external-size-commits/pr12-68db496f-review.json)를
남겼으며 이번 인계 갱신에서는 generator·compiler·codec·엔진·loader·UCI·대국을 실행하지 않았다.
아래 크기와 기존 검사의 통과는 해당 PR의 저장된 기록이다.

### 1.1 유지 recipe가 기록하는 현재 전체 파일

| 제출 경로 | 고정 head recipe | 기록된 전체 파일 | 4,096 B와의 차이 |
|---|---|---:|---:|
| A | [recipe](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-a/recipe.json) | 4,610 B | 514 B 초과 |
| B | [recipe](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-b/recipe.json) | 5,144 B | 1,048 B 초과 |
| C | [recipe](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-c/recipe.json) | 4,952 B | 856 B 초과 |
| D scalar / HQ | [recipe](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-d/recipe.json) | 5,937 / 6,148 B | 1,841 / 2,052 B 초과 |
| E | [recipe](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-e/recipe.json) | 5,011 B | 915 B 초과 |
| F full/default | [recipe](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-f/recipe.json) | 4,537 B | 441 B 초과 |
| F material/noise | 같은 recipe의 `alternate_policies` | 4,325 B | 229 B 초과 |
| F material/move-TT | 같은 recipe의 `alternate_policies` | 4,051 B | 45 B 여유 |

이 값은 이전 PR #13의 NVCompact 최소와 **서로 다른 source/recipe 기준**이다.
따라서 과거 move-TT 4,047 B와 현재 4,051 B를 같은 입력의 4 B 회귀로 판정하거나,
옛 NVCompact 절감량을 현재 표에 더하지 않는다. 현재 head로 다시 압축 비교할 때는
현재 original과 후보를 같은 toolchain·프로필·wrapper로 맞춰야 한다.

local profile은 search workers 2개, TT18, PLY128이며 전체 startup 관측은 controller를
포함한 3 TIDs다. 기록된 local positive 검사만으로 최종 다코어 서버 자원, 스케줄링,
기력이나 실제 TCEC 인수를 확정하지 않는다. D는 scalar/HQ 모두 4 KiB를 초과한다.
F move-TT의 통과는 축약 정책의 통과이며 full/default F의 완료로 표시하지 않는다.

### 1.2 8abcbc3 이후 실제 코드에 반영된 변경

아래는 **반영 완료 상태**다. 같은 아이디어가 외부 catalog에 나오더라도 신규 미구현
과제로 다시 세지 않는다. 크기 변화는 고정 head의 구현 기록에서 읽은 당시 결과이며
이 표의 행별 수치를 합산하여 현재 최소를 계산하지 않는다.

| 반영 영역 | 실제 읽은 구현과 변화 | 일반화할 때의 경계 |
|---|---|---|
| literal include / mixer | [include stage](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/scripts/shipping_includes.py), [mixer stage](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/scripts/shipping_mixer_literals.py): literal header 앞 공백 및 고정 LP64의 큰 unsigned hex wrapper 축소 | A의 include, B의 mixer는 당시 whole-file 열세로 미채택. 이름별 영구 금지가 아니며 다른 문맥에서 재비교 가능. `UINT64_C(1)` 같은 작은 literal에 같은 논리를 적용하지 않음 |
| compiler 정리 guard | [bootstrap](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-a/bootstrap.py.in): `p is not None`을 고정 Popen 객체의 truthiness로 표현 | Python None/Popen 생성 계약에 한정. 임의 객체의 falsey 의미나 compiler 종료·wait 처리를 삭제하는 변환이 아님 |
| B SEE polling | [shipping_guard.py](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-b/shipping_guard.py): clock-first 판정과 sticky stop 읽기를 재구성 | **취소 관찰 순서와 clock-call trace가 달라지는 명시적 timing policy**. 무손실 조건식 축약으로 등록하지 않음 |
| F correction clamp | [shipping_clamp.py](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-f/shipping_clamp.py): plain nonescaping local int의 두 clamp를 한 대입 삼항식으로, 당시 4,575→4,574 B | 모든 representable int에서 값이 같고 같은 값의 추가 대입을 관찰하는 경로가 없다는 구체 조건. volatile·atomic·주소 escape 일반화 금지 |
| F helper / constant inline | [shipping_source_forms.py](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-f/shipping_source_forms.py): private piece-index helper 3회와 HISTORY int literal 4회를 inline; 조합 당시 4,574→4,553 B | 실제 int8_t operand의 int 승격 및 단일 평가, 동일 int token/array extent를 확인. 원문 macro dump·line identity는 관측 계약 밖으로 구별 |
| A/B/C/E/full F clock presence | [shipping_clock.py](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/scripts/shipping_clock.py): 별도 flag 대신 UINT64_MAX sentinel, `~time`으로 presence 판정 | numeric helper의 admitted 결과가 0..INT64_MAX이며 malformed/missing은 0이라는 계약. 일반 unsigned 전체 범위에서 임의 sentinel 제거로 확대하지 않음 |
| E19 physical slots | [shipping_zero_slots.py](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-e/shipping_zero_slots.py): physical table 21칸 중 0/6을 zero slot으로 두고 consumer index 재배치 | **logical coefficient는 그대로 19개**. logical extraction과 signed16-LE digest 유지. E19→E21 모델 증가나 가중치 재학습이 아님 |
| full F result stream | [shipping_result_stream.py](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-f/shipping_result_stream.py): 단일 complete bestmove printf 주변 explicit flock/unlock 제거; 당시 4,548→4,537 B | **multi-call grouping을 완화하는 배포·동시성 변경**. glibc/POSIX 개별 stdio lock과 job mutex의 완료 순서를 전제로 하며 정확한 응답 순서 동치는 주장하지 않음 |
| D consumed sort prefix | [native/search.c](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-d/native/search.c): 선택한 Move는 local에 남기고 소비 완료 prefix의 move/score 저장 제거; 당시 scalar/HQ −19/−6 B | 다음 suffix와 tie 순서를 보존하고 이미 소비한 prefix를 learner가 다시 읽지 않는 현재 소비 계약. ice4처럼 prefix로 history penalty를 계산하는 구현에 그대로 적용하면 안 됨 |
| D coefficient packing | [native/board.c](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-d/native/board.c): material/advance/biased-center를 10/3/4-bit로 묶은 7-entry int table; 당시 scalar/HQ −10/−21 B | Board cache는 decoded signed int 그대로. packed score lane 정책 변경과 구별하며 계수·범위·empty/king의 의미를 보존 |
| B overlong-line drain | [shipping_line_drain.py](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-b/shipping_line_drain.py): 최초 getchar를 loop에 합치고 nonterminal 존재를 bad flag로 보존, 85→68 source B; whole 5,146→5,144 B | LF/EOF·입력 경계·읽기 횟수·discard를 보존하는 B 고정 domain. 같은 형태는 다른 family에서 크기 열세였으며 당시 미채택 근거를 유지 |

B/E/F [build 연결부](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/engines/compact/tiny-entry-f/build.py)도
읽어 stage 순서, DEV bypass, optional 정책 및 별도 full reference 경계를 확인했다.
고정 source preimage·offset·inverse는 **그 구성의 재생 identity**를 보장하는 장치다.
임의 입력을 다루는 NVCompact에 그대로 붙여 엔진 이름별 예외가 되는 방식을 뜻하지 않는다.

현재 [구현 기록](https://github.com/daejunnom/Rove4k/blob/68db496f478735411e2036231f03e3f35c76f088/docs/ENGINE-IMPLEMENTATION.md)은
실패한 B helper의 bytes escape 준비, 실행 권한이 없어 시작되지 않은 F wrapper 시도,
뒤의 수정·새 검증을 별도 기록으로 보존한다. 이전 실패를 지우지 않고 새 문맥의 결과로
비교하는 원칙과 잘 맞는다. 이 문서 갱신에서 그 검증을 독립 재실행하지 않았다.

## 2. 이전 PR #13 인계와 측정 이력

아래 `0e716e0`의 표와 `8abcbc3` 후속 설명은 당시의 기록으로 보존한다. 이 절의
“현재”, “새 최소”, “후속 head”는 그 인계 시점을 뜻하며 1절의 고정 head 값으로
덮어쓰거나 이후 절감량을 더하지 않는다. PR #13은 현재 병합된 상태다.

검토 기준은 PR #12의 `0e716e0b366272c66749f6e7194f64cb715e2d00`이다.
PR #13은 별도 `feature/*` 브랜치에서 `develop`을 대상으로 작업한다. 엔진 담당자는
통합 전에 자신의 최신 head와 이 기준 사이의 차이를 확인해야 한다. 과거 byte offset이나
고정 입력 SHA를 다른 head에 그대로 재사용하지 않는다.

| 유지되는 제출 경로 | 기준 전체 파일 | 4,096 B 초과분 |
|---|---:|---:|
| A | 4,652 B | 556 B |
| B | 5,219 B | 1,123 B |
| C | 4,992 B | 896 B |
| D scalar / HQ | 5,966 / 6,175 B | 1,870 / 2,079 B |
| E | 5,076 B | 980 B |
| F full/default | 4,645 B | 549 B |
| F material/noise | 4,369 B | 273 B |
| F material/move-TT | 4,089 B | 0 B, 여유 7 B |

표는 해당 커밋의 유지 recipe가 명시하는 값이다. PR #13에서 새로 실행한 결과는
별도 [최종 회귀 기록](PR13-RESULTS.ko.md)으로 구분한다. 새 최소는 A 4,616 B,
B 5,173 B, C 4,979 B, D scalar/HQ 5,966/6,175 B, E 5,038 B,
F full 4,611 B, F material/noise 4,331 B, F material/move-TT 4,047 B다.
F full은 515 B, material/noise는 235 B가 여전히 초과하며 move-TT는 49 B 여유가 있다.
이 결과에 새 UCI·대국 인수를 포함하지 않는다. 과거 native 핀 7건의 실패도 유지한다.
현재 local profile은 search worker 2개와 controller,
TT18, PLY128이다. 이 값으로 최종 TCEC 서버 자원·기력·실행 적격성을 인수하지 않는다.

이전 조사 기준 `364e316` 이후 이미 반영된 변경을 다시 미구현 과제로 세지 않는다.

- `9dce883`: C/E/full F의 main 소유 tokenizer 공유와 full F mate-score 조정식.
- `0e716e0`: 일곱 source profile의 material classifier를 세 accumulator에서
  하나의 signed state로 변경. 기존의 제한된 dead-material 인식 정책을 보존한다.
  KNN을 dead로 새로 분류하지 않는다. raw source는 profile당 18 B 늘었지만
  전체 제출 파일은 4–10 B 줄었다.

원문: [구현 기록](https://github.com/daejunnom/Rove4k/blob/0e716e0b366272c66749f6e7194f64cb715e2d00/docs/ENGINE-IMPLEMENTATION.md),
[material-state 생성 단계](https://github.com/daejunnom/Rove4k/blob/0e716e0b366272c66749f6e7194f64cb715e2d00/engines/scripts/shipping_material_state.py),
[후기 개별 변환](https://github.com/daejunnom/Rove4k/blob/0e716e0b366272c66749f6e7194f64cb715e2d00/engines/scripts/shipping_refinements.py).

### 당시 최종 인계 시점의 후속 head: 8abcbc3

비교 실행 중 PR #12가 `8abcbc3a4af0ef02435ca1ba52f10b43715bf99c`까지 진행했다.
0e716e0 이후 세 커밋과 실제 생성 단계를 추가로 읽어 아래를 확인했다. 이 후속 head는
위 NVCompact 크기 표의 측정 대상이 아니며, 기존 head의 절감량을 그대로 더하지 않는다.

- `8bc1abe`: 고정 unsigned64 숫자 admission의 high-bit 표현, 일부 limits include 제거,
  full/material F의 고정 TT18 cast 제거, full F terminal legal-loop 공유가 반영됐다.
- `8abcbc3`: B/E worker job 초기화 공유, B/C/E의 checked calloc 직후 plain TT zero-store
  제거, B의 TO127 SEE 승격 조건과 고정 TT18 cast 제거가 반영됐다. atomic flag 초기화는
  계속 수행한다. 직접 preseeded think 호출 등의 경계는 engine 계약으로 구분돼 있다.
- 같은 `8abcbc3`의 full F mixer pre-add 제거는 **명시적인 hash 정책 변경**이다.
  이를 같은 native의 표기 압축으로 NVCompact가 일반화하지 않는다.

따라서 아래 조건·상태 표는 일반화의 증명 경계로 읽는다. 이미 적용된 cast·승격 조건·
terminal 공유를 새 구현 과제로 다시 세지 않는다. 통합 대상은 최신 head의 정본·recipe를
다시 고정하고 변환 후 native 및 실제 전체 파일을 대조하는 경로다.

후속 근거: [정수 표현](https://github.com/daejunnom/Rove4k/blob/8abcbc3a4af0ef02435ca1ba52f10b43715bf99c/engines/scripts/shipping_integer_forms.py),
[초기화와 SEE](https://github.com/daejunnom/Rove4k/blob/8abcbc3a4af0ef02435ca1ba52f10b43715bf99c/engines/scripts/shipping_compaction.py),
[terminal 공유](https://github.com/daejunnom/Rove4k/blob/8abcbc3a4af0ef02435ca1ba52f10b43715bf99c/engines/compact/tiny-entry-f/shipping_terminal.py),
[hash 정책](https://github.com/daejunnom/Rove4k/blob/8abcbc3a4af0ef02435ca1ba52f10b43715bf99c/engines/compact/tiny-entry-f/shipping_hash_policy.py).

## 3. NVCompact의 공통 변환으로 다룰 부분

NVCompact는 명시한 소스 관측 계약 아래 AST binding, literal 타입·값, 평가 효과를
유지하는 후보를 만들고 실제 전체 제출 파일로 비교한다. 원본 후보와 이전 유효 후보는
남긴다. 함수·변수명이 이미 한 글자여도 압축 문맥에 맞는 다른 한 글자가 더 작을 수 있다.
동일한 native ELF를 만드는 소스들이 서로 다른 압축 크기를 갖는 것도 정상이다.

| 공통 변환 영역 | 일반화할 조건 | 엔진 담당에게 요구하지 않는 것 |
|---|---|---|
| 지역 변수·매개변수 이름 | 선언과 참조의 binding, scope 충돌, macro/소스 관측 경계 보존 | 이름별 예외나 고정 source offset |
| 정수·문자 표기 | 대상 정수 모델에서 타입·값 유지, preprocessing token 경계 확인 | `100000`과 `1e5`를 같은 타입으로 취급 |
| 조건식·삼항연산자 | 분기 타입, 진리값 문맥, 평가 횟수·순서·부작용 보존 | 주석만으로 boolean·nonnegative 범위 추정 |
| 후보 선택 | header·bootstrap·payload를 포함한 전체 파일 비용 | raw source 감소량을 절약량으로 보고 |
| replay·검증 | 실제 입력·생성 경로·도구를 고정하고 재현 | 과거 native pin 불일치를 metadata 제외로 통과 |

이 경계 밖의 상태·모델 변경도 설계 후보가 될 수 있다. 다만 같은 의미의 표현 후보와
분리해 명시한 계약으로 빌드·비교한다. NVCompact가 엔진의 search, TT, worker 정책을
몰래 수정해서 더 작은 파일을 만들지 않는다.

## 4. 조건식 후보의 엔진별 증명 요청

다음은 일반 문자열 치환 규칙으로 등록할 수 없는 대표 사례다. 기존 성공 사례를
다른 코드에 옮길 때에는 같은 전제가 실제 호출 경로에서 성립해야 한다.

| 후보 | 확인해야 할 엔진 전제 | 깨지는 경계·필요한 관측 |
|---|---|---|
| `a!=1` → `!a` | 읽는 값이 항상 `{0,1}`이고 같은 평가가 이루어짐 | `a=2`는 반례. 단순 `int`·enum 이름만으로 증명되지 않음 |
| TT bound의 논리식 → `I!=2+(H>=d)` | 바깥 gate가 0을 제외하고 I가 exact/lower/upper의 1/2/3, 비교 operand가 효과 없는 local | gate 밖·다른 bound encoding에서 적용 금지. invalid 0을 포함한 truth table과 실제 probe 소비를 확인 |
| 승격 rank 두 비교 → `!(to+16&96)` | to가 실제 유효 0x88 destination | 범위 밖 to=135는 반례. 생성 move, raw/provisional EP, 외부 입력의 경계를 구분 |
| `(size_t)1<<18`의 cast 제거 | int32, 고정 양수 shift18, 후속 연산·소비가 같은 값·타입 변환을 사용 | TT bits 확장 시 signed shift/overflow가 달라질 수 있음 |
| noise식의 suffix/cast 제거 | Move·worker id의 signedness, 중간 곱·합·나머지 범위, 조건 연산자와 최종 대입 타입 | 값 표본의 일치만으로 integer conversion 전체를 보장하지 않음 |
| mate score branch 공유 | score 저장·복원 범위, ply, cutoff/witness와 terminal 값의 계약 | 조건 평가·overflow·짝이 되는 decode/store를 함께 대조 |

NVCompact가 해당 범위·효과를 증명하지 못하면 미적용으로 남기는 것이 기본이다.
엔진 담당자는 적용 가능한 국소 입력 범위를 증명하거나, 읽을 수 있는 정본에서
해당 조건이 드러나는 별도 구현을 제안할 수 있다. 함수 이름에 맞춘 예외를 추가하지 않는다.

이미 적용된 bound·promotion·mate 변환의 절감량은 새로운 절감량에 더하지 않는다.
특히 어떤 promotion식은 한 profile에서 작아져도 다른 profile에서는 전체 파일을 키웠다.

## 5. PR #12 담당자가 결정할 개별 변경

| 담당 영역 | 검토할 변경 | 보존·구분해야 할 계약 |
|---|---|---|
| A / 공통 move 처리 | attack·movegen 순회 공유, 이미 만든 child 재사용, 생성 move 전용 API, private capture bit | castling·promotion·EP, hash·history·halfmove, 실패 시 이전 상태. 미검증 외부 move를 같은 API로 받지 않음 |
| B / SEE | make와 SEE gain 계산 공유, 재귀 승격 처리, legal-LVA 또는 다른 ordering 모델 | full minimax SEE와 legal-LVA는 다른 결과를 낼 수 있음. pruning과 ordering을 구분하고 기력 변화는 별도 판단 |
| C / SIMD HCE | signed lane·incremental state·reduction 표현 | 평가 범위, saturation/overflow, board 갱신·undo, scalar oracle. XMM 사용만으로 기존 AVX2 배포 조건이 사라지지 않음 |
| D / 자체 ELF | loader/native 공통화, 모델·BCJ 표현, 실제 함수 공유와 배치 | entry·mapping·relocation·syscall·ISA·atomic TT 및 decoder의 수명. 외부 명령 없는 ELF 부문의 전체 비용 |
| E / 모델 | coefficient 표현, feature와 consumer 결합, 다른 모델 제안 | E21→E19와 feature 삭제는 별도 모델 변경. 학습이나 동등 기력을 수행하지 않았으면 주장하지 않음 |
| F / MTD와 TT | terminal scan·witness·last-completed 경로 공유, bounds 표현, full 또는 move-only TT 정책 | full-depth MTD의 완료 보장, 재검색, stop, witness. bound/depth/score를 생략하는 것은 표현 압축이 아님 |
| 입력 소유권 | main 전용 tokenizer·응답 생성 경로 공유 | 다른 worker/호출자가 token cursor를 건드리지 않는 수명. `strtok_r`→`strtok`를 범용 다중 스레드 rewrite로 등록하지 않음 |
| 동시성·자원 | record packing, atomic 폭, 게시·교체 정책, startup와 epoch state 공유 | data race, coherent snapshot, 초기화·종료·재사용. try-lock의 miss/drop 제거는 ordering/scheduling 계약 변화 |

F material/noise와 material/move-TT는 명시적인 opt-in 정책이다. full/default의
크기 부족을 해결한 것으로 표시하지 않는다. 공간 확보를 위해 자동으로 worker 수,
TT 크기, 검색·평가 feature를 줄이지 않는다. 원래 많은 코어를 활용하는 목표도 유지한다.

## 6. 후속 작업 항목

1절의 반영 완료 항목을 다시 미구현 과제로 세지 않는다. 아래는 새로운 후보나
다른 입력·도구 문맥을 검토할 때의 인계 접점이며, 같은 검증을 무조건 반복하는
체크리스트가 아니다.

- [ ] 수정 파일: `engines/compact/tiny-entry-*/recipe.json`, 구현 내용: 최신 head와 profile의 source·compiler·bootstrap·whole 식별자를 고정해 NVCompact 후보의 기준을 제공한다. 기존 실패 pin을 지우거나 자동 갱신하지 않는다.
- [ ] 수정 파일: 해당 엔진의 읽을 수 있는 정본·생성 단계, 구현 내용: 위 표에서 공통 AST 분석으로 증명되지 않는 조건의 도메인·소유권을 검토한다. 고정 offset은 재생 근거이며 범용 의미 증명을 대신하지 않는다.
- [ ] 수정 파일: 입력·terminal·TT의 실제 소비 경로, 구현 내용: 새로 제안하는 응답 공유·private counter 등의 후보를 별도로 비교한다. 이미 반영한 F result-stream 변경과 구별하고, 개별 함수의 비용과 조합된 전체 파일의 비용을 분리한다.
- [ ] 수정 파일: 해당 profile의 기존 검사 접점, 구현 내용: 바뀐 함수·상태의 경계와 독립 oracle을 대조하고 실제 wrapper의 시작·UCI·종료 확인을 해당 권한·자원에서 수행한다.
- [ ] 수정 파일: `docs/ENGINE-IMPLEMENTATION.md`, 구현 내용: 의미 보존·모델/탐색 변경·배포 변경을 구분하고 선택·거절 후보의 실제 전체 파일 차이를 기록한다. 별도 실험 절감량을 합산하지 않는다.

새 변환을 엔진에 유지할 때에는 readable input부터 다시 생성되는 경로를 남긴다.
생성된 C나 압축 stream만 손으로 수정한 결과를 정본으로 승격하지 않는다.

## 7. 비교 입력과 회귀의 경계

외부 비교 엔진은 [`comparisons/general`](../comparisons/general) 11개와
[`comparisons/elf`](../comparisons/elf) 2개다. 공개 대표 입력의 SHA는 이미 manifest에
고정돼 있다. 공개 release·source rebuild와 정확한 비공개 대회 제출물은 같다고
가정하지 않는다. source와 binary는 저장소·npm 패키지에 포함하지 않는다.

이전 최소 크기는 [General 기록](../evidence/0.4/general-comparison.json)과
[ELF 기록](../evidence/0.4/elf-comparison.json)에 있다. 같은 입력의 새 결과가 원본보다
작아졌어도 이전 NVCompact 최소보다 크면 회귀다. 새로운 source head·컴파일러·서버
profile로 바뀐 결과는 그 사실을 표시하고, 같은 조건의 원본/후보 대조를 별도로 한다.

`scripts/compare-results.mjs`는 별도의 manifest 목록을 기준으로 baseline/candidate의
실제 `original`·`smallest` 바이트와 해시·크기를 읽는다. 같은 입력을 비교하는지,
행이 누락됐는지, 선택 파일이 보고서와 다른지, 이전 최소보다 커졌는지를 판정한다.
복원·recipe 검사 기록은 읽지만 독립 실행을 새로 수행한 것으로 표시하지 않는다.
이 도구는 엔진·compiler·검증기를 시작하지 않으며 의미·UCI·기력 인수를 발급하지 않는다.

무거운 엔진의 기존 TT·thread 설정을 작은 호스트에 맞추어 바꾸지 않는다. `resource plan`과
명시적 `resource run --start`의 경계를 유지하고, compile-only·byte replay·UCI·실전 기력의
확인 범위를 각각 보고한다. 새 표기 후보가 전체 native와 같다는 관측은 그 특정 compiler와
recipe에 관한 근거이며 C 전반의 모든 target에 대한 정리를 대신하지 않는다.

## 8. 외부 이력과 현재 엔진을 연결한 후속 판단

전체 355건의 방법은 [외부 연구 안내](EXTERNAL-SIZE-COMMITS.ko.md)와 상세 표에 보존한다.
특정 변경이 Rove4k에 없다고 판단하려면 해당 head의 실제 소비 경로를 더 읽어야 한다.
이번에 반영 여부를 확인하지 않은 항목은 미구현으로 단정하지 않고 후보로만 남긴다.

| 아이디어 묶음 | 현재 고정 head에서 확인한 상태 | 다음에 판단할 내용 |
|---|---|---|
| 조건식/임시변수/상수의 여러 표기 | F clamp 및 helper/HISTORY inline 반영 | 같은 native를 만드는 대안도 General의 source 비용은 각각 유지; raw 길이나 단독 크기만으로 조합 제거 금지 |
| sentinel과 table 표현 | clock presence, E19 zero slots, D packed coefficients 반영 | 다른 sentinel이나 exact re-encoding은 각 consumer·bounds·startup/hot-path 비용을 먼저 검토 |
| consumed prefix와 공유 traversal | D sort prefix 저장 제거 반영 | 다른 family의 penalty/history consumer가 prefix를 읽는지 확인 후 판단; 적용 가능성을 전역 추정하지 않음 |
| field 순서·AoS/SoA·direct-index 확대 | 이번 인계에서 전체 adoption audit 미수행 | ABI·직렬화·hash의 memory read, 짧은 displacement, 메모리와 cache를 함께 비교 |
| movegen API·parser 재사용·attack kernel 공유 | 이전 인계의 일반 제안으로 유지; 전체 adoption audit 미수행 | 합법 입력 domain, invalid/EP/promotion 처리, 출력 pointer 수명 및 hot-path 호출 수 확인 |
| linker/codec/layout 조합 | D own-ELF와 각 General recipe가 따로 존재 | 선언한 적격 후보의 교차 결과를 전체 파일로 비교; 외부 명령 General 방식을 own-ELF에 혼합하지 않음 |
| worker/TT/stream 수명 | 2 workers 유지, F stdio grouping 변경은 명시적 정책으로 반영 | 많은 코어에서의 자원·종료·정보 보장 수준은 별도 근거; thread-local→shared나 atomic 폭 변경은 단순 압축 아님 |
| lossy/model/search 특수화 | F optional 정책과 기존 hash/timing 변경을 full 동치 후보와 구분 | feature 삭제·TT 정보 축소·양자화·학습 변경을 무손실 압축으로 보고하지 않음 |

- [ ] 수정 파일: 해당 family의 정본과 기존 생성·비교 접점, 구현 내용: 외부 catalog의 후보를 선택할 때 현재 반영 상태를 먼저 대조하고, 이미 반영한 방법의 재구현 대신 다른 대안·조합·소비 범위의 가치를 판단한다.
- [ ] 수정 파일: 실제 선택 후보의 계약과 검증 접점, 구현 내용: domain·타입·효과·수명 증명이 필요한 engine-specific 변환을 공통 NVCompact 이름 예외로 옮기지 않고 필요한 사실을 드러내는 설계로 제안한다.
- [ ] 수정 파일: 기존 비교 기록과 `docs/ENGINE-IMPLEMENTATION.md`, 구현 내용: 크기 열세·의미 실패·환경 미완료를 구분해 유지하고 source/codec 문맥 변경 후 재검토 결과를 새 기록으로 연결한다. 동일한 조건의 반복 검사나 새 전용 registry를 의무화하지 않는다.

이 인계는 PR #12의 `68db496f478735411e2036231f03e3f35c76f088` 이후 내용에 대해
채택·거절·크기·검증 상태를 주장하지 않는다. 후속 head를 사용할 때에는 source와
recipe를 다시 고정하고 이 문서의 역사와 새 결과를 나누어 갱신한다.
