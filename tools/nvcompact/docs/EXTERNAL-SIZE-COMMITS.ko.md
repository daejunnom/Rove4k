# 외부 4k 엔진의 바이트 절감 이력과 적용 경계

조사일: 2026-10-21. 이 문서는 공개 엔진의 실제 커밋 diff에서 얻은 아이디어를 연결하는 비규범적 연구 안내다. 현재 Rove4k에서 채택한 방법도 기록하며, 미채택·역효과·정확성 실패를 숨기지 않는다. 기존 설계와 다르다는 이유로 새 아이디어를 배제하거나 이 목록을 필수 구현 과제로 삼지 않는다.

## 1. 자료와 조사 범위

| 자료 | 내용 |
|---|---|
| [ice4 · 4ku · 4k.c 상세 조사](research/PRIMARY-ENGINE-BYTE-COMMITS.ko.md) | 206개 커밋, 방법·적용 조건·작성자 기록·미검토 범위 |
| [나머지 엔진 상세 조사](research/OTHER-ENGINE-SIZE-COMMITS.ko.md) | c4ke, STRO4K, molly, pygone, Sunfish, M4sseur, we4k와 인접 Pytteliten의 149개 커밋/기록 |
| [기본 3개 엔진 메타데이터](evidence/external-size-commits/primary-engine-commits.json) | full SHA, URL, 검토 범위, patch digest, 적용 분류, 남은 후보 |
| [보조 엔진 메타데이터](evidence/external-size-commits/other-engine-commit-review.json) | full SHA, URL, 기술, 의미·성능 위험, 당시 크기 근거, 조사 inventory |
| [PR #12 고정 소스 확인](evidence/external-size-commits/pr12-68db496f-review.json) | `68db496f...`의 읽은 파일·blob·SHA-256, recipe의 기대 크기/identity |
| [PR #12 후속 head 참고](evidence/external-size-commits/pr12-b65a7498-review.json) | `68db496f...`→`b65a7498...`의 실제 변경·채택 상태와 관측 계약; 이번 캠페인 미측정, 외부 355건과 별도 |
| [PR #12 bootstrap 환경 복사 후속](evidence/external-size-commits/pr12-7a112cbf-review.json) | `b65a7498...`→`7a112cbf...` 1개 커밋·17개 파일 diff, 채택·크기 열세와 수동 wrapper 관측 계약; 비교 입력은 `68db496f...` 유지 |
| [PR #12 담당자 인계](PR12-HANDOFF.ko.md) | 고정 비교 기준·역사적 표와 후속 head 참고를 분리한 엔진별 판단 |

총 **355개 선택 커밋 diff 또는 실험 기록**을 검토했다. 기존 roster에 대응하는 **10개 엔진 계열 347건**과, 실제 참가가 확인되지 않은 **Pytteliten 8건**을 구분한다. 355건을 모두 성공한 무손실 절감이나 독립적인 최적화 355종으로 해석하지 않는다. 혼합 변경, 실패 수정, 문서 실험과 제목 검색의 false positive도 포함한다.

| 엔진 계열 | 검토한 커밋/기록 | 범위 설명 |
|---|---:|---|
| ice4 | 60 | 전체 diff 58개와 관련 hunk 2개 |
| 4ku | 55 | 선택 전체 diff 55개 |
| 4k.c | 91 | 전체 diff 90개와 관련 hunk 1개 |
| c4ke | 79 | minifier·표기·데이터·검색 변경을 함께 분류 |
| STRO4K | 19 | source/assembly/packing, 공개 branch에 한정 |
| molly | 15 | `codeberg.org/latuernich/molly`; 동명 GitHub 프로젝트 제외 |
| pygone | 11 | `scs-ben/pygone`; 직접 shrink 및 관련 후속 변경 |
| Sunfish | 10 | 2022 packing과 2026 source/data/harness 실험을 구분 |
| M4sseur | 5 | 이름 배정·launcher와 혼합 튜닝 변경 |
| we4k | 2 | build/README/선택 Board diff; 전체 검색 변경 감사 아님 |
| Pytteliten | 8 | upstream이 TCEC4K 목표를 밝힌 인접 참고, 참가 확인 없음 |

기본 3개 엔진은 고정 HEAD 계보의 제목 후보를 중심으로, 보조 엔진은 전체 reachable non-merge refs의 제목 후보와 수동 후속 수정을 중심으로 조사했다. 조사 단위가 다르므로 history·후보 수를 하나의 완전한 coverage 비율로 합치지 않는다. 상세 JSON의 미검토 후보와 각 행의 검토 범위를 유지한다.

Moonfish는 zamfofex의 엔진만을 뜻한다. 공식 과거 SourceHut와 현재 Neocities 배포 URL의 이력을 이번 도구로 확인할 수 없었고, 과거 제출과 현재 무버전 파일의 동일성도 확정하지 못했다. 임의의 동명 GitHub 저장소로 대체하지 않았다. STRO4K의 공개 history가 roster의 모든 버전, 특히 6.0의 정확한 제출 소스임을 확인한 것은 아니며 Sunfish 2026 NNUE 실험도 역사적인 classic 제출물과 같다고 가정하지 않는다.

## 2. 숫자가 증명하는 것과 증명하지 않는 것

이 조사는 **읽기 전용 소스 분석**이다. 외부 엔진, compiler, compressor, bootstrap, ELF loader나 대국을 실행하지 않았다. 표의 숫자는 upstream 작성자의 커밋 제목·README·CHANGELOG·source 주석·실험 ledger에 남은 기록이다. 이번 NVCompact의 재현 실측이나 Rove4k 예상 절감량으로 바꾸어 적지 않는다.

- 한 커밋에 여러 변경이 있으면 전체 차이를 한 기술에 귀속하지 않는다.
- 서로 다른 source/codec/toolchain의 byte 차이를 합산하지 않는다.
- 특히 ice4 `99525f9c6d43`는 메시지의 size 기준을 TCEC build로 바꾼다고 명시한다. 전후 숫자를 같은 계열의 연속 측정처럼 연결하지 않는다.
- `-N bytes`라는 제목과 실제 CHANGELOG가 모순되면 본문 근거를 보존한다. 4k.c의 미사용 blockers를 0으로 바꾸는 [c7e570ef](https://github.com/GediminasMasaitis/4k-dot-c/commit/c7e570efdaa8104d791cadf5e46e00ea746ba9c3)는 CHANGELOG상 **+8 B**다.
- raw source, native ELF, codec stream, header/loader를 포함한 whole submission은 서로 다른 비용이다. 작은 중간물이 최저 제출 파일을 보장하지 않는다.

## 3. 적용 분류

두 catalog의 기존 분류를 지우거나 하나의 `safe` flag로 합치지 않는다. 한 patch가 여러 범주에 걸칠 수 있다.

| 적용 범주 | 대표 기술 | 필요한 판단 |
|---|---|---|
| NVCompact 공통 후보 | binding을 보존한 이름 대안, typed literal/조건식 대안, 순수 임시변수·반복 표현, 결정적 codec 설정 | 언어·타입·효과·관측 계약을 분석하고 원본을 포함한 최종 파일로 비교 |
| 엔진 불변식이 필요한 후보 | sentinel, movegen/search API, field order, table decode, 공유 evaluation traversal | legal domain, 상태 소유권, cache/TT·탐색 소비자, hot-path 성능을 엔진 담당자가 판단 |
| 명시적인 의미·기능 변화 | hash/TT 정책, pruning·시간관리, feature/출력 삭제, 가중치 양자화·재학습 | 표현 압축과 별도 실험으로 기록하고 목표에 맞는 검증과 기력 판단 수행 |
| 배포·타깃 조건이 필요한 후보 | linker·section 배치, raw codec/BCJ, shell wrapper, custom ELF/ABI/ISA | 실제 부문·OS·ABI·시작/종료·loader 계약과 전체 산입 비용 확인 |
| 실패·검증 교훈 | 잘못된 binding/precedence, 원본 대 원본 비교, 누락된 TT 초기화, 비결정적 이름 배정 | 입력별 예외가 아니라 공통 분석·생성·검증의 원인을 수정 |

기본 catalog의 `N/E/T/R`, 보조 catalog의 `P/M/B/V/F/D`와 `nvcompact_route`는 이 구분을 보완한다. `N`이나 `P`는 검토된 문맥 밖에서도 안전한 자동 규칙이라는 뜻이 아니다.

## 4. NVCompact 탐색과 재사용에 주는 근거

### 최종 파일을 기준으로 대안을 남긴다

4ku의 [f2be6e67](https://github.com/kz04px/4ku/commit/f2be6e678273b688587c1a0317367378b445c6a4)는 사용하지 않는 짧은 `0` 인자를 이미 반복되는 더 긴 표현으로 바꾸고 bound·분기 구조도 함께 수정했다. 전체 patch의 기록은 3988→3983 B이며, 5 B를 인자 변경 하나에 귀속하지 않는다. c4ke [e3e6858c](https://github.com/citrus610/c4ke/commit/e3e6858ce2539a33a8eb6a4faa456d43cece448a)는 조건부 대입 삼항식을 `if`로 되돌렸다. 상수 접기·임시변수 인라인·분기 제거를 항상 짧아지는 canonical form으로 확정할 근거는 없다.

[Sunfish eb8897cc](https://github.com/thomasahle/sunfish/commit/eb8897cc6c884555992db0d9c2a745b90e2ee32c)는 shebang 삭제만으로 classic이 4 B 커졌지만 literal hoisting 비활성화와 결합하면 3232→3210 B가 됐다고 기록한다. 개별 크기 열세만으로 조합 후보를 제거하면 이 이득을 놓친다. 실패·미채택 후보는 당시 문맥과 이유를 보존하고 새로운 문맥에서 재측정할 수 있어야 한다.

### 선언한 유한 공간과 휴리스틱 선별을 구분한다

4k.c의 [9e4c8bb3](https://github.com/GediminasMasaitis/4k-dot-c/commit/9e4c8bb37ba1c5c6c71f6a248916d8a2c2f9080e)는 독립이라고 표시한 그룹마다 local permutation을 수행한 뒤 그룹별 순열의 Cartesian product를 열거했다. 이는 선언한 그룹·순열 공간에 대한 exhaustive 탐색이다. 임의의 모든 동등 프로그램을 생성했다는 뜻은 아니다.

STRO4K [48a8168d](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/48a8168d3cd0b9e11f61f704253e71761bd157fe)는 assembly object 1개를 재사용하면서 4개 linker × 15개 lc/lp × 5개 pb × 5개 match finder를 비교했고, 당시 README는 4073→4044 B를 기록한다. 이러한 명시적 domain과 예산, 생성·중복·실패·검증·계측·미완료 수를 보고하는 것이 적절하다.

### 동일한 단계 입력의 비용을 공유한다

4k.c [33d8ab89](https://github.com/GediminasMasaitis/4k-dot-c/commit/33d8ab894ad5d9f4df7be29e75e67f2152ee8e8d)의 persistent compression server, 변경한 model slot 복원과 warm cache는 반복 초기화 비용을 줄이는 아이디어다. 다만 warm 결과로 탈락시킨 후보가 full model에서도 불리하다는 증명은 없으므로 그 경로는 heuristic으로 남는다. 논문식 전역 최적성으로 승격하지 않는다.

NVCompact에서는 parse/typed facts, 동일 compile 또는 link 입력, codec 호출을 각 책임의 소유 범위에서 재사용할 수 있다. cache key는 source/물리 byte뿐 아니라 compiler/linker/codec, flags, target, link 순서·script, wrapper와 관측 계약의 영향도 반영해야 한다. **동일 native는 General의 서로 다른 source payload를 같은 비용 후보로 합칠 근거가 아니다.** ELF packing 비용을 공유하는 것과 source 포함 제출의 비용을 생략하는 것은 다른 작업이다.

### 검증 대상을 정확히 고정한다

ice4 [084e1fbf](https://github.com/MinusKelvin/ice4/commit/084e1fbf3e3f4dedf597637081bfd4e58da31a2d)는 packed MG/EG 괄호 오류로 저자 보고 65 Elo를 잃었던 문제를 고쳤다. c4ke [8acbb75d](https://github.com/citrus610/c4ke/commit/8acbb75da9366a2ebb0f17ea7fd43982e438a41e)는 minified bench가 원본을 다시 컴파일하던 오류를 수정했다. molly [05ea434b](https://codeberg.org/latuernich/molly/commit/05ea434b165ffda6f06238482cd2974b72377729)는 minify skip으로 빠진 TT 초기화를 복구했다.

이는 단순 빌드 성공이나 원본 대 원본 비교를 semantic gate로 사용하면 안 된다는 근거다. 생성 입력, 실제 변형, 사용한 compile/link/pack 경로와 검증 artifact를 연결하고, 재사용한 관측을 새 독립 검증으로 보고하지 않는다. 전체 파일 4096 B ceiling과 이전 baseline 대비 회귀도 별개다. Sunfish [09b3b405](https://github.com/thomasahle/sunfish/commit/09b3b4057c815c8acc383a4add9371a9f2f6e390)는 ceiling만으로 발견하지 못한 45 B 회귀를 수정했다.

## 5. 엔진 쪽에서 보존할 아이디어

상세 catalog는 현재 채택 여부와 무관하게 모든 검토 행을 유지한다. 다음 묶음은 탐색 출발점이며 전부 새 미구현 과제를 뜻하지 않는다. PR #12에서 이미 적용한 부분은 [고정 head 인계](PR12-HANDOFF.ko.md)의 반영 상태와 대조한다.

- 표현과 API: 내부 field 순서·AoS/SoA, 짧은 displacement에 hot field 배치, count-pointer 대 advancing output pointer, bitboard 직접 인자로 ctz→shift 왕복 제거, private helper와 literal 공유.
- 순회와 상태: 두 색 평가를 공통 loop로, 이미 만든 child/best move/score 재사용, 증분 state와 기존 traversal 재계산의 교환, consumed sort prefix 쓰기 제거, 명시된 sentinel로 guard 삭제.
- 데이터와 decoding: 반복 table 통합, lossless block offset/low-high stream/부호 표현, exact mixed-radix/byte string, 더 넓은 table을 통한 load/extend 명령 감소, 정적 literal 대 runtime generator 비교.
- 동시성과 수명: worker 시작/종료 코드 공유, counter 폭/atomic representation·BSS/stack layout, 제한된 stream grouping. TT key 폭 축소·thread-local state 공유·direct stack unwind는 concurrency나 알고리즘 계약 변화로 별도 판단한다.
- 제출 packaging: linker/compile profile, ELF header·segment·decoder ABI, raw codec와 x86 filter, wrapper·해석기 진입점과 startup cleanup. 외부 명령을 쓰는 General 경로를 own-ELF에 그대로 옮기지 않는다.

## 6. 저장·패키징 경계

이 하위 문서와 JSON에는 분석, 짧은 설명, commit 식별자, 출처 URL과 metadata만 둔다. 외부 clone, 원본 source, 전체 patch, 바이너리, 압축 source, loader 및 가중치를 벤더링하지 않는다. JSON의 patch digest는 원문 patch 자체가 아니다.

현재 [npm files](../npm/package.json)와 [pack staging](../scripts/pack.mjs)은 `bin/`, `lib/`, 준비된 `native/`, README와 LICENSE를 포장한다. 이 연구 문서와 `docs/evidence/`는 staging 대상이 아니므로 npm 실행 패키지의 배포 범위를 늘리지 않는다. 이 판단은 관리 코드 읽기 결과이며 새 npm tarball을 만들거나 게시한 결과가 아니다.

후속 작업은 이 catalog를 삭제하거나 기대값을 현재 결과에 맞추어 갱신하는 방식으로 실패를 해소하지 않는다. 새 조건의 실제 결과와 채택 이유를 추가하고 원래 입력·실패·미검토 범위를 보존한다. 현재 지원하는 변환·탐색·검증 범위는 [NVCompact 안내](../README.md) 및 해당 구현 문서를 기준으로 삼는다.
