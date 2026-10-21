# PR #12 엔진 담당자를 위한 압축 인계

이 문서는 NVCompact의 공통 변환과 엔진 지식이 필요한 변경의 경계를 정리한다.
새 엔진 설계를 고정하는 규약이 아니라 PR #13에서 준비한 작업 인계다. PR #12에
변경을 적용하거나, 아래 후보를 모두 구현·채택했다는 뜻은 아니다.

## 1. 비교 기준과 현재 상태

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
별도 회귀 기록으로 구분한다. 현재 local profile은 search worker 2개와 controller,
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

## 2. NVCompact의 공통 변환으로 다룰 부분

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

## 3. 조건식 후보의 엔진별 증명 요청

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

## 4. PR #12 담당자가 결정할 개별 변경

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

## 5. 실제 작업 항목

- [ ] 수정 파일: `engines/compact/tiny-entry-*/recipe.json`, 구현 내용: 최신 head와 profile의 source·compiler·bootstrap·whole 식별자를 고정해 NVCompact 후보의 기준을 제공한다. 기존 실패 pin을 지우거나 자동 갱신하지 않는다.
- [ ] 수정 파일: 해당 엔진의 읽을 수 있는 정본·생성 단계, 구현 내용: 위 표에서 공통 AST 분석으로 증명되지 않는 조건의 도메인·소유권을 검토한다. 고정 offset은 재생 근거이며 범용 의미 증명을 대신하지 않는다.
- [ ] 수정 파일: 입력·terminal·TT의 실제 소비 경로, 구현 내용: 응답 공유·private counter 등 아직 source-only인 후보를 별도로 비교한다. 개별 함수의 비용과 조합된 전체 파일의 비용을 분리한다.
- [ ] 수정 파일: 해당 profile의 기존 검사 접점, 구현 내용: 바뀐 함수·상태의 경계와 독립 oracle을 대조하고 실제 wrapper의 시작·UCI·종료 확인을 해당 권한·자원에서 수행한다.
- [ ] 수정 파일: `docs/ENGINE-IMPLEMENTATION.md`, 구현 내용: 의미 보존·모델/탐색 변경·배포 변경을 구분하고 선택·거절 후보의 실제 전체 파일 차이를 기록한다. 별도 실험 절감량을 합산하지 않는다.

새 변환을 엔진에 유지할 때에는 readable input부터 다시 생성되는 경로를 남긴다.
생성된 C나 압축 stream만 손으로 수정한 결과를 정본으로 승격하지 않는다.

## 6. 비교 입력과 회귀의 경계

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
