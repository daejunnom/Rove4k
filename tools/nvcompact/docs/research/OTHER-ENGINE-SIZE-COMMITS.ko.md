# TCEC 4k 외부 엔진의 크기 절감 커밋 검토 — 보조 엔진 편

작성일: 2026-10-21. ice4, 4ku, 4k.c는 별도 조사에 맡기고 이 문서에서는 중복하지 않는다.

## 해석 범위

공개 저장소의 실제 변경 diff를 읽어 **구현 방법, 적용 전제, 의미 변화, 검증 실패 사례**를 기록했다. 외부 엔진과 bootstrap, ELF loader, 빌드 스크립트는 실행하지 않았으며 새 압축률이나 속도를 계측하지 않았다. 아래 숫자는 전부 당시 upstream의 제목·README·소스 주석·실험 ledger 기록이다. 실제 Rove4k에 같은 이득이 생긴다는 추정치로 사용하면 안 된다.

같은 커밋에 여러 변경이 들어 있으면 전체 byte 차이를 한 기술의 효과로 귀속하지 않는다. 서로 다른 revision의 절감량을 합산하지 않는다. 원문 길이가 짧아진 것, 컴파일된 machine code가 줄어든 것, 최종 제출 wrapper를 포함한 compressed artifact가 줄어든 것은 각각 구별한다.

## NVCompact 설계로 가져올 핵심

1. **큰 중간 후보를 보존해야 한다.** Sunfish `eb8897cc`는 shebang 삭제만 하면 classic artifact가 4 B 커지지만 literal-hoist 비활성화와 합치면 22 B 작아졌다고 기록한다. 개별 단계에서 커졌다는 이유로 탐색 후보를 폐기하면 이후 조합의 최솟값을 놓친다. 탐색 범위의 Cartesian product 또는 명시적인 budget/coverage를 보고하며 greedy pruning의 한계를 감추지 않는다.
2. **소스 길이 대신 전체 artifact로 고른다.** c4ke의 임시변수 도입/제거, 선언 순서, `if`와 `?:`의 양방향 사례, STRO4K의 더 넓은 table과 literal table 복귀는 한 방향 canonicalization이 손해일 수 있음을 보여준다. typed/guarded alternatives를 유지하되 compiler output이 같으면 후속 작업만 공유한다.
3. **stage별 동등한 입력은 재사용한다.** STRO4K `48a8168d`는 assembly object를 한 번 만들고 linker 및 LZMA 설정을 교차 탐색한다. NVCompact는 source digest, compiler/toolchain/flags, link inputs/order/script, codec profile, wrapper, 검증 policy를 구분한 key를 사용해야 한다. source 후보가 같은 ELF로 수렴하면 link/pack work를 공유할 수 있지만 그 사실이 서로 다른 C 소스의 보편적 의미 동등성을 증명하지는 않는다.
4. **기존 후보와 실패 기록도 같은 비교 모델에 넣는다.** Sunfish `09b3b405`는 4096 B ceiling만 검사해 45 B 회귀를 놓친 사례다. 같은 pinned toolchain에서 baseline과 현재를 비교하고 원본 후보를 항상 포함한다. compile failure, semantic rejection, size loss, unsupported capability는 서로 다른 결과로 보존한다.
5. **원인 계층을 고친다.** c4ke `8acbb75d`는 minified bench가 원본을 재컴파일하던 검증 오류였고 molly `05ea434b`는 minified build만 TT 초기화가 빠진 오류였다. AST와 실제 제출 경로, macro/token boundary, scope/name binding을 모델링해야 하며 입력 이름 예외와 skip-marker로 가리는 방식은 범용 minifier의 근본 해법이 아니다.
6. **이름 배정은 결정적 후보 집합으로 둔다.** c4ke/M4sseur는 같은 길이 identifier alphabet 순서도 바꾼다. molly `891728b0`는 HashSet→BTreeSet으로 재현성을 고쳤다. 정렬 기준·빈도 기준·고정 seed alphabet 등 재현 가능한 후보만 생성하고 scope collision, exported/ABI symbol, macro stringification을 보호한다.
7. **data encoding은 decoder 포함해서 평가한다.** Sunfish `62456cf9`는 exact PST 재구성으로 97 B를 보고한다. `12d316aa`의 encoder×layout 비교는 압축된 데이터만이 아니라 decoder와 wrapper를 포함하고 독립 reference와 round-trip 검사를 둔다. lossless re-encoding과 quantization/feature deletion은 분리해야 한다.

## PR #12 엔진 작업자에게 전달할 아이디어

아래 항목은 Rove4k에서 이미 채택했는지와 관계없이 보존한다. 자동 NVCompact rewrite보다 엔진의 불변식을 아는 작업자가 먼저 증명해야 한다.

- **상태·코드 공유:** pawn/mobility/phase 평가를 기존 traversal에 결합, move parser 대신 기존 move generation+render를 활용, type 인자로 attack kernel을 공유, 동일한 PVS/ZWS 재검색 call을 하나로 합친다. 절감 가능성과 hot-path 작업 증가를 동시에 평가한다.
- **sentinel과 인코딩:** en-passant 없음의 zero hash 원소, ply-2 비교용 sentinel 평가, bitboard disjoint 불변식, 단일 king bit 불변식을 이용한다. sentinel 하나가 guard 여러 개를 없애지만 legal/invalid input domain을 문서화해야 한다.
- **표와 decoder:** table 중심값을 공통 material/offset으로 이동, unused leading entry 제거, MG/EG lane 통합, exact mixed-radix/bytes-literal startup 복원, literal data 대 생성 코드 양방향 비교. 튜닝 변경 없이 정확히 복원하는 경로부터 시도한다.
- **멀티스레딩과 lifecycle:** STRO4K `a3a2ecfd`는 counter를 넓혀 더 많은 worker를 지원하면서 BSS 배치/worker exit 공유로 21 B를 줄였다고 기록한다. 반대로 corrhist의 thread-local→global 변경, TT reference lifetime, root direct-stack-unwind는 단순 압축이 아니므로 별도 concurrency/cleanup 증명이 필요하다.
- **타입 폭의 역설:** 작은 타입이 항상 최소 artifact가 아니다. c4ke i16→i32 move, STRO4K 16→32-bit piece table은 extension/load instructions와 선언 반복을 줄일 수 있다. ABI·메모리·cache 비용까지 비교한다.
- **어셈블리·빌드:** register 배정, 짧은 즉시값의 push/pop, loop 펼치기/다시 접기, branch label 위치, linker의 section/order/ELF packing, x86 filter/raw container를 후보로 둔다. ISA와 startup/stack/loader 요구 조건을 명시한다.
- **허용되지 않는 자동 일반화:** queen-only promotion 출력, movestogo parser 삭제, node/nps 출력 삭제, TT mate 보정/pruning 삭제, Zobrist generator 교체, 양자화/미러링, polling 주기/검색 순서 변경은 기능·알고리즘 선택이다. 무손실 압축으로 보고하지 않는다.

## 명시적인 위험 사례

- C의 `a != 1`→`!a`는 a∈{0,1}이라는 type/range 증거가 있을 때만 가능하다. 역사에 등장한 `piece & 1`→`piece % 2`, `>=d-3`→`>d-4`, set-bit clear→XOR도 같은 방식으로 범위/불변식을 증명해야 한다.
- C++의 `(condition ? left : right) = value` 또는 XOR 대입은 일반 C에 그대로 옮길 수 없다. auto, const 삭제, namespace 축약도 type/overload/linkage를 바꿀 수 있다.
- 반복 식을 임시변수로 바꾸면 읽기 시점이 바뀐다. pygone `417d4240`의 `time_up` 포함 TT guard를 미리 계산하는 식은 검색 도중 갱신된 취소 상태를 놓칠 수 있다. volatile/atomic/shared memory는 순수 CSE처럼 취급하지 않는다.
- molly의 큰 const inline 성능 예외는 무작정 인라인이 실패한다는 증거다. PST/Zobrist라는 이름을 예외 목록에 추가하는 방식 대신 크기, 사용 횟수, constant promotion, alias와 재계산 비용을 모델링한다.
- 디코더와 table 검증은 변형된 코드에서 정답을 다시 추출해 자기 자신과 비교하면 안 된다. immutable 원본 또는 독립 생성 규칙을 reference로 두고 실제 artifact의 경로도 확인한다.

## 조사 범위와 한계


| 엔진 | 공개 non-merge history | 키워드 후보 | 실제 선택 diff | 관측 HEAD |
|---|---:|---:|---:|---|
| [c4ke](https://github.com/citrus610/c4ke) | 332 | 94 | 79 | `ca95d3ac5e59` |
| [STRO4K](https://github.com/ONE-RANDOM-HUMAN/STRO4K) | 720 | 48 | 19 | `51ea73a3d861` |
| [M4sseur](https://github.com/Diazepawn/M4sseur) | 17 | 2 | 5 | `470fa53925c1` |
| [we4k](https://github.com/ONE-RANDOM-HUMAN/we4k) | 10 | 0 | 2 | `352f7378a077` |
| [sunfish](https://github.com/thomasahle/sunfish) | 1363 | 123 | 10 | `e396948acbd8` |
| [Pytteliten](https://github.com/1337crisis/Pytteliten) | 43 | 6 | 8 | `ba711c475cff` |
| [pygone](https://github.com/scs-ben/pygone) | 351 | 15 | 11 | `cbaebeeaaa5a` |
| [molly-tcec](https://codeberg.org/latuernich/molly) | 110 | 15 | 15 | `a1867f8bad01` |

**총 149개 선택 커밋 diff/기록 검토.** 후보 집계는 모든 reachable non-merge refs에서 `byte / shrink / compress / minif / size / golf / pack / small` 제목 검색을 사용했다. 실제 검토에는 키워드에 걸리지 않는 관련 후속 수정도 포함한다. 모든 커밋을 읽었다거나 모든 가능한 압축 기법을 찾았다고 주장하지 않는다.

중요한 provenance: 현재 STRO4K public history가 roster의 모든 버전, 특히 6.0의 정확한 제출 소스임을 확인한 것은 아니다. Sunfish의 2026 NNUE 실험은 역사적인 classic 제출물과 구별한다. Pytteliten은 upstream이 TCEC4K 목표를 명시한 인접 프로젝트지만 기존 event roster에서 참가가 확인되지 않았다.

Moonfish는 zamfofex의 엔진만을 뜻한다. [공식 과거 저장소](https://git.sr.ht/~zamfofex/moonfish)와 [현재 배포 URL](https://moonfish.neocities.org/moonfish.sh)을 이번 웹 도구로 다시 열었으나 접근할 수 없었다. 이전 Rove4k metadata의 sourcehut 404 및 과거/current 일치 미확인 상태를 해소하지 못했으므로 임의의 동명 GitHub 저장소를 대체 근거로 사용하지 않았다. molly도 `mateoxh/molly` 동명 프로젝트는 제외했고 실제 TCEC upstream인 `latuernich/molly`만 검토했다.

## 커밋별 근거

분류: P=의미 보존 후보(별도 증명 필요), M=검색/평가/계약 변화가 혼합됨, B=빌드/packing, V=검증·정확성·재현성, F=기능 제거, D=문서 실험. 대상 `candidate`는 NVCompact 후보화 가능성이며 현재 안전한 자동 규칙으로 구현됐다는 뜻이 아니다.

### c4ke

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [422cec0aeb](https://github.com/citrus610/c4ke/commit/422cec0aeb64075e73178fe335d43d8a3dc5e485) | P · 제목: 4 B 절감 | 64회 DIAG 초기화를 832회 Zobrist 초기화 루프 안 i%64 인덱스로 합침 | DIAG 각 원소를 13회 쓰는 시간 증가; 초기화의 멱등성/루프 경계 증명 / engine-owner |
| [b0985397a2](https://github.com/citrus610/c4ke/commit/b0985397a2319214cfb662efcaaa82b3c740cc31) | P · 제목: 16 B 절감 | move 임시변수로 noisy/quiet history 갱신 표현을 통일하고 bonus 부호를 루프 밖에서 변경 | 임시변수 수명·bonus 복구·관찰 순서 필요; 짧은 원문보다 반복되는 문자열이 유리할 수 있음 / candidate |
| [ffb03259b7](https://github.com/citrus610/c4ke/commit/ffb03259b7e2973923395485c1a2bfb39d19e5d7) | M · 제목: 6 B 절감 | move/list를 i16에서 i32로 넓혀 기존 i32 선언과 합침 | 자료형/ABI/메모리 사용량이 바뀜; 좁은 정수가 항상 최저 파일 비용이 아님 / engine-owner |
| [d9aa411efe](https://github.com/citrus610/c4ke/commit/d9aa411efe126b78906753572303f021c4c9263e) | P · 제목: 5 B 절감 | 별도 protected-pawn popcount를 기존 pawn 평가 루프의 조건 추가로 통합 | 반복 순서와 정수 overflow 중간값을 확인; 추가 분기와 기존 popcount 비용 비교 / engine-owner |
| [eae91eaf09](https://github.com/citrus610/c4ke/commit/eae91eaf093afcf50ed65ee978278576882ea9b2) | P · 제목: 8 B 절감 | Board::edit에서 삭제·삽입의 piece 임시변수를 재사용해 같은 텍스트 표현 생성 | alias/상태 갱신 순서와 p의 실제 값 확인; 임시변수를 늘려도 압축 후 감소 가능 / candidate |
| [c2b056ec3e](https://github.com/citrus610/c4ke/commit/c2b056ec3e8416cf182fdb4ea0f1b65035dd2318) | M · 제목: 5 B 절감 | pawn/non-pawn hash 필드를 hash_corrhist[3] 배열로 통합 | 구조체 레이아웃과 인덱스 계약 변화 / engine-owner |
| [deddfedc02](https://github.com/citrus610/c4ke/commit/deddfedc02ca3718f868a0e66f574d592e3f15fd) | P · 제목: 5 B 절감 | 별도 color bitboard 바이트 반전을 6 piece-type 루프에 합쳐 각 color를 홀수 3회 반전 | 6회/홀수 불변식에 의존하고 초기화 시간이 늘어남 / engine-owner |
| [d756703225](https://github.com/citrus610/c4ke/commit/d7567032254b3566ac889fac3c89abcd829dfbf6) | P · 제목: 2 B 절감 | noisy reduction clamp를 제거하고 reduction>0 분기 안 호출에서 is_quiet?reduction:1 선택 | 정수 reduction의 양수 구간에만 동치; 분기 밖 일반화 금지 / candidate |
| [e7250ef24e](https://github.com/citrus610/c4ke/commit/e7250ef24e981ec2f66e446c3564d7d18bb48857) | M · 명시 바이트 수 없음 | tuner의 king-pawn threat/blocked-passer 파라미터와 관련 경로 삭제 | minifier 관련 제목과 달리 평가 특징 삭제가 섞임 / engine-owner |
| [50a3f43920](https://github.com/citrus610/c4ke/commit/50a3f439205495bbbc9280478abad85ea7c13000) | P · 제목: 7 B 절감 | 독립 선언/초기화 순서 변경, time 임시변수 대신 TIME_LIMIT 재사용 | 전역 값의 외부 관찰/동시성 및 평가 순서 확인 / candidate |
| [ca2614c213](https://github.com/citrus610/c4ke/commit/ca2614c213c3a77910e6974b071e6649a1575acb) | P · 명시 바이트 수 없음 | VALUE/LAYOUT 등 독립 상수 배열 선언 순서 변경 | 주소/섹션 배치와 초기화 의존성 영향 확인; 최종 압축 문맥으로 비교 / candidate |
| [4b0dcee9dc](https://github.com/citrus610/c4ke/commit/4b0dcee9dc0120e20e3e11389160e06c8b36b622) | P · 제목: 6 B 절감 | pawn attack 임시변수 순서 변경; north(north(pawns))를 <<16으로 표현 | north가 순수 unsigned 8-bit shift일 때만 축약 가능 / candidate |
| [7eca768851](https://github.com/citrus610/c4ke/commit/7eca768851cc3e4de9638ee2ae95a16e24000c43) | P · 제목: 9 B 절감 | 동일한 u64 전역들을 하나의 선언으로 합치고 순서 정리 | 선언 범위/초기화 순서/링크 배치 확인 / candidate |
| [1d8a604707](https://github.com/citrus610/c4ke/commit/1d8a6047075677fcad7e90582813785b0af6027d) | M · 명시 바이트 수 없음 | Board를 전역 BOARD로 두고 각 worker가 시작 시 복사; 인자와 lambda capture 제거 | root와 worker의 소유권/동기화 계약에 의존; 일반 local-to-global 변환 금지 / engine-owner |
| [9d6c91912f](https://github.com/citrus610/c4ke/commit/9d6c91912fc38e03ca4c71cbe1ded213f19d64ae) | M · 제목: 21 B 절감 | Board 필드 재배치/일부 u8 축소, literal suffix 제거, mask 표기, 평가 공통 8배 인수 축약 | 자료형·정수 반올림·범위 및 레이아웃 변경이 혼합됨 / engine-owner |
| [678f8d6647](https://github.com/citrus610/c4ke/commit/678f8d6647db52e6c1c73d544180ffb5690faa98) | P · 명시 바이트 수 없음 | PASSER/KING_PASSER 압축 데이터의 decode offset을 합산해 하나의 OFFSET_PASSER 사용 | 항이 같은 조건에서 같은 횟수 더해질 때만 offset 합산 가능 / engine-owner |
| [c29ae2f9a1](https://github.com/citrus610/c4ke/commit/c29ae2f9a16ad3af71cb3d1b226447352cecc26a) | M · 명시 바이트 수 없음 | passer decode/scaling/offset 통합, Boolean 곱, globals 통합; corrhist를 thread member에서 전역으로 변경 | 평가 산술뿐 아니라 학습 상태의 스레드 공유 정책이 변경됨 / engine-owner |
| [dbfa58a1bc](https://github.com/citrus610/c4ke/commit/dbfa58a1bc965651b953292010276c03b2d98ffc) | P · 제목: 5 B 절감 | 13×64 RNG 초기화 중첩 루프를 832회 루프 및 i/64,i%64로 선형화 | 방문 순서·반복 횟수 동일 증명; 나눗셈 비용 비교 / candidate |
| [de87bb2a6c](https://github.com/citrus610/c4ke/commit/de87bb2a6cb6deb72b32c2aaf4ec0695d2f83f46) | M · 제목: 10 B 절감, but risky | king/knight 생성 순서와 평가 순서 변경, quadratic scale를 linear로 바꾸고 bias 삭제 | 탐색 순서와 평가 자체가 달라짐; 무손실 압축으로 분류 불가 / engine-owner |
| [7056eff516](https://github.com/citrus610/c4ke/commit/7056eff516bfe3a9f72bb0618b82172fae8d2897) | P · 명시 바이트 수 없음 | 긴 __builtin 함수명을 C++23 countr_zero/popcount/byteswap로 바꾸고 minifier 키워드 보호 | 표준 버전/라이브러리와 zero 입력 의미가 다름; ctz(0) 전제 필요 / candidate |
| [2898f6edd0](https://github.com/citrus610/c4ke/commit/2898f6edd096d00ef79f4dadbcdcdc8cd6522443) | M · 제목: 9 B 절감 | void에 짧은 type alias를 도입하고 bound 변수를 i32 선언에 합침 | alias만은 후보지만 정수 폭/TT 저장 변환은 별도 검토 / candidate |
| [d5ca1719da](https://github.com/citrus610/c4ke/commit/d5ca1719dad56fa0b414a1a63fc86d7bd9f99428) | B · 명시 바이트 수 없음 | 생성 식별자 알파벳을 문자 빈도 etaoins... 순서로 재배열 | 원문 길이가 같아도 LZMA 문맥이 달라짐; 예약어/충돌 보존 후 실제 파일 비교 / candidate |
| [15aad646c5](https://github.com/citrus610/c4ke/commit/15aad646c521194711fb13da3a2bd73e6d318439) | M · 제목: 2 B 절감 | excluded move 판정을 child.make 뒤로 이동; LMR 부동소수 연산 순서 변경 | 부수효과 발생 여부 및 부동소수 반올림 변화 / engine-owner |
| [955a2036f1](https://github.com/citrus610/c4ke/commit/955a2036f13d8a41515ceb9bf61394af5212f07c) | F · 제목: 5 B 절감 | promotion 출력 lookup을 queen/space 선택으로 축소 | underpromotion이 가능하면 출력 의미가 달라짐; 엔진 계약으로만 허용 / engine-owner |
| [7780ed2c0c](https://github.com/citrus610/c4ke/commit/7780ed2c0cc18ee3c098476be5d23630b6d7dc32) | P · 제목: 2 B 절감 | end cursor 대신 입력 move-list 포인터를 증가시키고 시작 포인터 보관 | 인자 포인터가 값 복사인지, 범위와 반환 규약이 같은지 확인 / candidate |
| [e8b48f193b](https://github.com/citrus610/c4ke/commit/e8b48f193bb727aca2d1de7604778ba9df6d943e) | P · 제목: 8 B 절감 | selection sort에 self-compare 1회 추가, depth_next 재사용, terminal guard 분리 | 비교자가 순수해야 하며 추가 작업 및 return 조건 동치 필요 / candidate |
| [2104a34a00](https://github.com/citrus610/c4ke/commit/2104a34a00c7381ba4e23bdb8d82139b9da8fa4a) | P · 제목: 7 B 절감 | king mask 재사용, *this={} 초기화, outer guard 대신 중복 조건, 산술 분배 | C++ 초기화 의미/부수효과/정수 overflow에 의존 / candidate |
| [64bd1b27e1](https://github.com/citrus610/c4ke/commit/64bd1b27e1fb1a9ee52b2ac025e93b8fc4791daf) | M · 명시 바이트 수 없음 | TT mate score 보정과 aspiration window clamp 삭제 | 검색/점수 계약 변화; 자동 압축 대상 아님 / engine-owner |
| [1bf9069516](https://github.com/citrus610/c4ke/commit/1bf90695161a9bb89bc22aa2c1ff8bd0b95e2084) | P · 명시 바이트 수 없음 | Board의 증분 phases[2]를 없애고 기존 평가 traversal에서 phase 재계산 | 상태 크기와 hot-path 계산 비용의 교환; 동일한 phase 의미를 검증해야 함 / engine-owner |
| [09981f09dc](https://github.com/citrus610/c4ke/commit/09981f09dc4d47d041816db752e0ec198a050557) | V · 명시 바이트 수 없음 | token minifier의 +- 처리에서 음수 token 시작 여부를 검사하는 수정 | 문자열 처리만으로 C/C++ 산술 의미를 보장하지 못함; typed AST 필요 / validation |
| [b58a9cfa41](https://github.com/citrus610/c4ke/commit/b58a9cfa413322a8655f45201926a0478e4ac277) | M · 명시 바이트 수 없음 | attacker 인자를 square→bitmask로 변경해 ctz/shift 왕복 제거, halfmove/guard/상수/TT 수정 | 캐슬링 처리 및 평가 상수도 바뀐 혼합 patch; 부분 아이디어만 분리 / engine-owner |
| [a372d9739d](https://github.com/citrus610/c4ke/commit/a372d9739d0d7364a219f6b7843d2bb99f493454) | P · 명시 바이트 수 없음 | 큰 bitmask의 ULL suffix를 없애거나 U로 축소하고 미사용 define 제거 | 목표 ABI의 literal type·signedness·shift 결과가 보존되어야 함 / candidate |
| [af6412c796](https://github.com/citrus610/c4ke/commit/af6412c796346769a5ea253e04dfeabc173ef270) | P · 명시 바이트 수 없음 | TT slot reference 임시변수를 제거하고 동일 인덱스를 반복 표현 | 해시 값 안정성·중복 load의 동시성·alias 확인; 임시변수 제거/추가 양방향 비교 / candidate |
| [5da1f6adcd](https://github.com/citrus610/c4ke/commit/5da1f6adcdf77ad0715e8872a93f0e7b1dba6f87) | P · 명시 바이트 수 없음 | piece color 추출 &1을 %2로 변경 | nonnegative 정수 domain에서만 동치; 음수 signed 일반화 금지 / candidate |
| [655caf51a8](https://github.com/citrus610/c4ke/commit/655caf51a853a7ac3a785fbca140a349749da98e) | M · 명시 바이트 수 없음 | first-legal/PV 불변식으로 LMR/ZWS/PVS 조건 재구성 | 검색 tree와 call 순서의 엔진별 증명이 필요 / engine-owner |
| [00ebc3cbb3](https://github.com/citrus610/c4ke/commit/00ebc3cbb3c58838fa395da304e7b971be251033) | P · 명시 바이트 수 없음 | score=beta 초기값을 두고 선택적 reduced search 다음 ZWS call을 공유 | 깊이/실패 경계와 호출 횟수 동치 검증 필요 / engine-owner |
| [56c81e468f](https://github.com/citrus610/c4ke/commit/56c81e468f7cf468505f5c0c9eac8f5c98dee67f) | M · 명시 바이트 수 없음 | stand-pat의 alpha/best 대입을 조건식 안으로 이동하고 pruning/depth guard 재구성 | cutoff 전 상태 대입과 depth 조건 의미를 함께 검토 / engine-owner |
| [8db8ca532b](https://github.com/citrus610/c4ke/commit/8db8ca532bb88a7d4fb7882bedf0395c1fcf40e1) | P · 명시 바이트 수 없음 | TT entry를 먼저 load한 뒤 key miss에 zero 처리하는 형태로 반전 | 동시 TT 갱신 시 스냅샷 및 메모리 접근 의미 확인 / engine-owner |
| [65dc6f9157](https://github.com/citrus610/c4ke/commit/65dc6f9157556bc8b96afb2b2f397364bf74df0d) | P · 제목: 2 B 절감 | piece/2<KNIGHT를 piece<WHITE_KNIGHT로 축약 | 정수 인코딩과 nonnegative 범위 증명 필요 / candidate |
| [f49f79d63d](https://github.com/citrus610/c4ke/commit/f49f79d63d7f302a3b2965158346e041854ee76a) | M · 제목: 17 B 절감 | decoder 공통 offset 합치기, *0x10000→<<16, token +- 및 ±0 제거, 평가 분기 재배치 | signed shift/overflow/부동소수/단항/문자열과 평가 분기 위험; token 규칙을 범용 복사하지 않음 / candidate |
| [6febd97ecc](https://github.com/citrus610/c4ke/commit/6febd97eccf79f7626267eed1176fa6752b36dfc) | M · 명시 바이트 수 없음 | decoder int를 i32 alias로 통일하면서 평가 가중치 재조정 | retuning이 섞여 무손실 크기 효과로 귀속할 수 없음 / engine-owner |
| [014c726d74](https://github.com/citrus610/c4ke/commit/014c726d74ee164f5c70320e3a93b30d99270e30) | M · 명시 바이트 수 없음 | PST rank/file 평균을 MATERIAL로 이동하고 값 중심화/양자화/scale 재설계 | 가중치 재학습 및 반올림이 섞임; lossless offset 후보만 분리 / engine-owner |
| [8437d073af](https://github.com/citrus610/c4ke/commit/8437d073afba364bb9037d7672a895a063077347) | P · 명시 바이트 수 없음 | knight/bishop/rook/king attack 경로를 type 인자를 받는 공유 attack 함수로 합침 | inline/dispatch와 ISA 비용·방문 순서·hot path 속도 검증 필요 / engine-owner |
| [ce5705849e](https://github.com/citrus610/c4ke/commit/ce5705849e3535598721d031f40a0eba8c64b292) | P · 제목: 3 B 절감 | legals 증가 시점을 검색 뒤로 이동하고 관련 비교 임계값 변경 | 모든 소비자와 초기 상태를 동시에 바꾸어야 동치 / engine-owner |
| [e3e6858ce2](https://github.com/citrus610/c4ke/commit/e3e6858ce2539a33a8eb6a4faa456d43cece448a) | P · 명시 바이트 수 없음 | 조건부 대입 ternary를 if(condition) reduction=2 형태로 되돌림 | 삼항연산자 고정 선호 금지; 동일 후보를 양방향 실제 artifact로 평가 / candidate |
| [38b6000d80](https://github.com/citrus610/c4ke/commit/38b6000d8071acb90fbaf1f4878a2b2d99736725) | V · 명시 바이트 수 없음 | minifier가 상수 값 끝 whitespace/CR을 정리하도록 수정 | lexical 경계와 문자열 literal 보존 필요 / validation |
| [654dd4c520](https://github.com/citrus610/c4ke/commit/654dd4c5205f43f230ae01f438e47d4588b678cf) | V · 명시 바이트 수 없음 | minifier에 if/else/for/while statement scope 추적과 이름 교체 재귀를 복원 | upstream의 scope-awareness 주장은 범용 C++ 안전성 증명이 아님 / validation |
| [c55e8341b5](https://github.com/citrus610/c4ke/commit/c55e8341b5290167caf5cb4c48c65168d380b951) | P · 명시 바이트 수 없음 | Board enpassant 기본 초기화와 *this=Board{} reset으로 startpos API 단순화 | 반환 계약과 객체 수명·초기값 같음 확인 / engine-owner |
| [6044ae19e2](https://github.com/citrus610/c4ke/commit/6044ae19e2bfb3cf2325b1562503fec4679c3ff1) | V · 명시 바이트 수 없음 | minifier 보호 키워드에 jthread 추가 | 예약어 나열은 해결책 일부; 외부 심볼/타입 binding 원칙 필요 / validation |
| [bb4ccb3a76](https://github.com/citrus610/c4ke/commit/bb4ccb3a766a534dff4a5c05c902379198592244) | M · 명시 바이트 수 없음 | nodes prefix increment를 postfix로, 출력 statement를 comma로 병합 | 관측되는 증가식은 polling phase를 바꿈; 버려지는 값의 ++만 일반화 가능 / engine-owner |
| [4650f3e690](https://github.com/citrus610/c4ke/commit/4650f3e690a553040e4024ce9b3a3a56fd6f2495) | P · 명시 바이트 수 없음 | range-for 및 외부 id 증가를 index-for로 통합 | 스레드 배열 길이와 lambda capture 시점 동일해야 함 / candidate |
| [100aa28601](https://github.com/citrus610/c4ke/commit/100aa28601a55c99ba230688ddd51bcdb035ae86) | P · 명시 바이트 수 없음 | castling-right OR 대입을 논리 조건 안으로 이동 | 대입 결과가 nonzero이고 부수효과 순서가 같다는 증명 필요 / engine-owner |
| [f27bd18255](https://github.com/citrus610/c4ke/commit/f27bd1825548a1350419793228914745d02f94af) | P · 명시 바이트 수 없음 | comma-chain으로 braces 축소, quiet/noisy 배열을 ternary lvalue로 선택 | 후자는 C++ 구문이며 일반 C의 조건식은 assignable lvalue가 아님 / candidate |
| [72d8cd85f2](https://github.com/citrus610/c4ke/commit/72d8cd85f25272874138c93910f70ee9e6f2b014) | P · 명시 바이트 수 없음 | if/else hash XOR를 ternary lvalue target으로 합침 | C++ 전용 및 atomic/overloaded operator·평가 순서 고려 / candidate |
| [0b8dbdbe4a](https://github.com/citrus610/c4ke/commit/0b8dbdbe4a8e3019dc7de027ec454f85f0360198) | P · 명시 바이트 수 없음 | 결과가 버려지는 loop increment의 ++depth를 depth++로 변경 | builtin scalar에서 버려지는 값일 때만; overloaded increment 제외 / candidate |
| [8671d300aa](https://github.com/citrus610/c4ke/commit/8671d300aa07c126fc053b63887e979586d00c64) | P · 명시 바이트 수 없음 | (*ptr)[i][j]를 ptr[0][i][j]로 표현 | 순수 built-in pointer/array domain과 동일 bounds 확인 / candidate |
| [8acbb75da9](https://github.com/citrus610/c4ke/commit/8acbb75da9366a2ebb0f17ea7fd43982e438a41e) | V · 명시 바이트 수 없음 | minified bench가 원본 main.cpp를 다시 컴파일하던 오류를 mini.cpp 컴파일로 수정 | 원본 대 원본 비교는 변환 검증이 아니며 실제 제출 경로를 검사해야 함 / validation |
| [29f121b876](https://github.com/citrus610/c4ke/commit/29f121b876f5bc9e201bac92a8a856506cdfde18) | P · 명시 바이트 수 없음 | Zobrist에 zero sentinel 원소를 두어 enpassant 해시 XOR guard 제거 | 없음 인덱스가 실제 zero이고 모든 경로에서 bounds가 맞아야 함 / engine-owner |
| [bafec3dfc9](https://github.com/citrus610/c4ke/commit/bafec3dfc9fe5d3226b32aa21de09ad8751f6478) | M · 명시 바이트 수 없음 | packed MG/EG 점수에 부호를 적용하는 시점을 lane 추출 전으로 변경 | carry·반올림·음수 shift 의미가 달라질 수 있음 / engine-owner |
| [ade913bb27](https://github.com/citrus610/c4ke/commit/ade913bb2720632bc7fb916979f5b4354328f69f) | P · 제목: 6 B 절감 | 확실히 set된 bit의 clear를 XOR로 변경하고 mask 식 inline | set-bit 불변식 없이는 and-not와 XOR가 다름 / engine-owner |
| [e0db838e13](https://github.com/citrus610/c4ke/commit/e0db838e131f844839c5530a56f9dc6055d946dd) | P · 제목: 1 B 절감 | enpassant assignment를 hash index 내부에서 별도 statement로 분리 | 원문이 길어져도 압축 후 짧아지는 사례; evaluation ordering 보존 / candidate |
| [457f4fbf91](https://github.com/citrus610/c4ke/commit/457f4fbf91ec54d65d92fed5adaa759970cbb648) | P · 제목: 1 B 절감 | && 체인에서 is_quiet 조건 위치 변경 | 순수 load인지, short circuit/volatile/공유 상태 관측 같은지 확인 / candidate |
| [4d6c8a06cd](https://github.com/citrus610/c4ke/commit/4d6c8a06cd353a2a02e456ffaa758e5eab5ab484) | P · 제목: 1 B 절감 | C++ 함수 기본 인자를 넣어 여러 call의 명시 FALSE 제거 | 선언 가시성·overload·call-site 계약을 모두 추적 / candidate |
| [87e4b1613f](https://github.com/citrus610/c4ke/commit/87e4b1613f5953a7b15fc597ace5f8414bd0e374) | P · 제목: 18 B 절감 | 동일 타입 선언을 합치고 locals 위치/초기화를 공유 | C++ nontrivial 수명과 definite assignment·scope shadowing 제외 또는 증명 / candidate |
| [bda1a5ec36](https://github.com/citrus610/c4ke/commit/bda1a5ec368526ed40cb8e51f61aa204a863f533) | P · 제목: 10 B 절감 | PST decode offset과 scale를 공통화하고 piece 조건 단순화 | 정수 중간값/호출 순서와 offset 적용 횟수 증명 / engine-owner |
| [a49b68f156](https://github.com/citrus610/c4ke/commit/a49b68f15660a98b646343c20fdc1e3634f4fe87) | P · 제목: 5 B 절감 | 접근하지 않는 table leading zero를 제거하고 INDEX를 보정 | 모든 가능한 index와 sentinel 경로 확인 필요 / engine-owner |
| [7addd27d49](https://github.com/citrus610/c4ke/commit/7addd27d49eada59c09c1ccca57ec92b12699fed) | M · 제목: 9 B 절감 | 짧은 이름 alphabet에 _ 추가, statement scope 추적 비활성화, literal suffix/complement 표현 | 이름 후보는 일반화 가능하지만 scope 제거와 signed literal shift는 안전하지 않음 / candidate |
| [3604ce1271](https://github.com/citrus610/c4ke/commit/3604ce127184404f7228936dfabf0aa7a9a0cd95) | P · 제목: 18 B 절감 | 2원소 임시 배열을 scalars로 분해하고 평가 합산식을 한 표현으로 묶음 | alias/주소 노출 없다는 조건, signed intermediate overflow 확인 / candidate |
| [70aa3de3a4](https://github.com/citrus610/c4ke/commit/70aa3de3a418e92021ca4e8f3836a4f0ca5b8af9) | P · 제목: 1 B 절감 | castling_rights 임시변수를 없애고 식을 두 call-site에 반복 | 중복 계산과 읽기 시점 보존; factoring의 역방향도 후보로 유지 / candidate |
| [5f70585d9f](https://github.com/citrus610/c4ke/commit/5f70585d9f5adafb031faa91a04ba100bf461110) | M · 제목: 9 B 절감 | helper를 Board member로 이동, from 임시변수 제거, C++ initializer = 삭제, enpassant hash index 수정 | hash 수정이 섞여 전체 patch는 동치 압축으로 취급 불가 / engine-owner |
| [b0270cee22](https://github.com/citrus610/c4ke/commit/b0270cee22e10f7156441945ab3ee831ae51abaf) | P · 제목: 4 B 절감 | extension 임시변수를 제거하고 depth_next에 직접 증가 | 초기 depth/확장 guard와 변수 수명 증명 필요 / engine-owner |
| [f139e20052](https://github.com/citrus610/c4ke/commit/f139e2005211e4920eeba59632d4b4cf430c868e) | M · 명시 바이트 수 없음 | KEYS에 zero sentinel 확장, enpassant/halfmove 처리 및 visited loop 수정 | sentinel 설계 외에 correctness 수정이 섞임 / engine-owner |
| [e2c61f1ae1](https://github.com/citrus610/c4ke/commit/e2c61f1ae1010eae7650d732592cd2f8567ec782) | P · 제목: 1 B 절감 | tt.depth>=depth-3를 tt.depth>depth-4로 경계 정규화 | bounded integer domain과 underflow/overflow 안전성 필요 / candidate |
| [0f320abb53](https://github.com/citrus610/c4ke/commit/0f320abb538824f9023b479c0f255b64366591fc) | P · 제목: 4 B 절감 | qsearch quiet-prune에서 board.checkers guard 제거 | 이 분기의 도달 조건이 이미 not-in-check임을 엔진에서 증명해야 함 / engine-owner |
| [fef9801c92](https://github.com/citrus610/c4ke/commit/fef9801c927913328c869a6cdd7c97e3734edaa6) | P · 제목: 1 B 절감 | pawns[2]를 만들어 attack/phalanx 등 반복 표현 공유 | common-subexpression 후보이나 배열 비용/범위/alias 확인 / candidate |
| [f53a484241](https://github.com/citrus610/c4ke/commit/f53a4842418d9256a7f9585c17ca4e917de0c8d5) | M · 제목: 10 B 절감 | make의 bool legal 반환을 illegal attack mask로 바꾸고 호출 조건 반전; 배타 명령 guard 분리 | API/반환 의미가 바뀌는 대규모 계약 재설계 / engine-owner |
| [900cd28980](https://github.com/citrus610/c4ke/commit/900cd2898039c1f2aec3387be610d274162ae756) | P · 제목: 5 B 절감 | mask/occupied 임시변수를 제거해 긴 표현 반복, else braces 제거, 피연산자 순서 변경 | INT_MIN 부호 반전 등 정수 정의역과 duplicated read 확인 / candidate |
| [3c694dabaf](https://github.com/citrus610/c4ke/commit/3c694dabaf1a7b4ead8a761b761bf4f44def60dd) | P · 제목: 6 B 절감 | piece/2 비교를 인코딩 범위 비교로, 6회 ray expansion을 반복 텍스트로 펼침 | 원문 길이 증가가 압축 패턴을 도울 수 있음; 반복 횟수/overflow 증명 / engine-owner |
| [ef496b6bb4](https://github.com/citrus610/c4ke/commit/ef496b6bb42d95cb23dd595b32af3d4de0095d64) | V · 명시 바이트 수 없음 | minified bench identity 확인 경로 추가; 후속 8acbb75d에서 실제 대상 오류 수정 | 검증 기능 자체도 원본/변형 입력을 다르게 받는지 positive control 필요 / validation |

### STRO4K

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [48a8168d3c](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/48a8168d3cd0b9e11f61f704253e71761bd157fe) | B · README: 4073→4044 B (29 B) | NASM 1회 뒤 ld/gold/lld/mold × lc/lp(sum≤4) × pb × 5 match finder의 1500 설정을 시도하고 최저 packed 결과 선택 | 유한한 선언된 search space이며 모든 가능한 프로그램은 아님; 객체 재사용·linker 실패 기록·전체 wrapper 비용 검증 / build-profile |
| [4b6bb2679a](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/4b6bb2679a993b2c5f7e7ebd15da41f42a5454fc) | B · README: 4095→4073 B (22 B) | 링커를 ld.lld에서 ld.gold로 교체 | 동일 object의 ELF 배치가 codec 결과를 바꿀 수 있음; ABI와 실행 의미 검증 / build-profile |
| [bf700077f9](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/bf700077f9898a423fcfa6f5b827a54ec90a4bf9) | M · README: 4083→4040 B (43 B) | xz container를 raw x86+LZMA2 및 대응 header로 바꿈; Rust newgame reset도 수정 | 43 B 전체를 codec만의 효과로 귀속 불가; decoder/header와 reset 의미 확인 / build-profile |
| [c974200698](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/c9742006980dd8f3140341cfdcf79f17b6c37e21) | P · README: 4091→4083 B (8 B) | packed 값의 런타임 8-entry shift-table 초기화를 literal dq 테이블로 대체 | 정적 data가 커져도 decoder 제거와 zero 반복성으로 최종 감소; startup/data 양방향 비교 / engine-owner |
| [199b7351de](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/199b7351dedaee6e590a0520ab8bf3e3de53cce4) | P · README: 4051→4046 B (5 B) | PV/check flag의 별도 test/branch를 하나의 OR mask test로 합침 | 같은 flags lifetime과 분기 목적지 증명; 성능은 branch/압축 문맥에 따라 다름 / candidate |
| [31621bfa4a](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/31621bfa4a03f9c62a9a2584e0f8dda7d04ccdc9) | P · README: 4091→4085 B (6 B) | dummy dec 삭제, history 계산/포인터 재사용, memory zero 비교를 base+offset 비교로 바꿈 | 주석은 dummy가 때때로 압축을 돕는다고 명시; DCE 항상 유리하다는 가정 금지 / engine-owner |
| [080562ead2](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/080562ead240e6fc4495ea04e94fe9cbf23e3284) | P · 명시 바이트 수 없음 | AVX512 broadcast를 GPR source로, mov immediate를 push/pop으로, imul register 역할 재배열 | 목표 ISA·stack/flags/register liveness 계약에 묶이는 assembly 최적화 / engine-owner |
| [ff0c71af1f](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/ff0c71af1f0eb30ac19c495568bc267f4c0de741) | P · 명시 바이트 수 없음 | 5개의 corrhist 갱신 block을 lodsq cursor와 공통 NASM %rep body로 통일 | 실행 코드가 loop가 아니라 unrolled 반복일 수 있음; pointer-array 레이아웃 불변식 필요 / engine-owner |
| [81ae24f3a4](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/81ae24f3a42bbe2831ea2bd22f3f0b24466461c4) | P · README: 4032→4016 B (16 B) | gives-check를 al에 보존하여 save/retest 제거; 입력 read 2회 loop를 펼침 | register liveness·읽기 순서와 고정 반복 횟수 증명 / engine-owner |
| [e0c4e6fc5f](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/e0c4e6fc5f6ab9a6c639d59d2a57343ae136f915) | P · README: 4025→4022 B (3 B) | color swap을 loop entry에 배치해 공통 처리하고 제어 흐름 재배치 | entry/back-edge/exit 각각의 swap 횟수 확인 / engine-owner |
| [28a90b06cf](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/28a90b06cf7b2c858db312fc393424b823530c27) | P · README: 4096→4086 B (10 B) | 2개 sentinel ply의 static_eval을 i16 MAX로 초기화하고 ply>=2 guard 삭제; ply-data pointer 유지 | sentinel의 평가 비교 결과, depth 경계, custom register convention 증명 / engine-owner |
| [ccdd47284c](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/ccdd47284cbbf719326f37d2f439c73bc588c508) | M · 명시 바이트 수 없음 | pawn serialization 순서 변경, AES hash round 제거, castling check 재배치 | move order와 hash 품질/충돌 특성이 달라짐; 검색 의미 보존 변환 아님 / engine-owner |
| [5cf08fcc4e](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/5cf08fcc4e9adaee2cc25b31afbd3593d5d2dd33) | M · 명시 바이트 수 없음 | hash seed를 Board 인접 16 B load로 구성; vpternlog, push/pop 순서, TT key test를 재설계 | board 레이아웃·hash 의미와 zero-entry admission 계약 변경 / engine-owner |
| [a3a2ecfd72](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/a3a2ecfd724d870a566b219fa9a1598595d208ce) | P · README: 4054→4033 B (21 B) | worker counter를 byte→dword로 넓히고 BSS stacks/TT 배치, 시작 pointer, 공통 worker exit 경로 통합 | 더 많은 threads 지원과 파일 감소가 동시에 가능; atomic 종료/stack bounds 검증 필요 / engine-owner |
| [2a84984784](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/2a84984784df728c15ea0ce14b97b9b26715eb29) | P · README: 4034→4032 B (2 B) | piece-value table을 16→32 bit로 넓혀 movzx/임시 register를 줄임 | table raw size 대신 전체 machine code+compression 비용을 평가해야 함 / engine-owner |
| [ef68fd0b36](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/ef68fd0b3604ac5fa1f2cd11f334f4d5ab3eeadb) | M · README: 4054→4038 B (16 B) | search failure flag의 매 return 전달 대신 saved stack pointer로 root 직접 복귀 | destructor/cleanup/board restoration/ABI를 우회할 수 있어 엔진별 전문 설계 필요 / engine-owner |
| [fde5bd9079](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/fde5bd90791bdc25cd7e7ea5ef07c34b2224363e) | P · README: 4106→4088 B (18 B) | worker exit 공유, 반환 move를 ebx에 보존해 stack 왕복 제거, newline read loop 단순화 | 사용자 정의 calling convention의 모든 호출자를 함께 검증 / engine-owner |
| [53e9e47766](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/53e9e47766ef16466abb590cb5e4c2433b78d888) | P · README: 3755→3747 B (8 B) | pawn MG/EG 상수를 interleave하고 vector widening/SWAR multiply 및 mask 재사용 | packed lane carry·overflow 및 sign/scale 의미 증명 / engine-owner |
| [181bfa593e](https://github.com/ONE-RANDOM-HUMAN/STRO4K/commit/181bfa593ee61682413f8722721c0d3899c05e78) | P · README: 3739→3711 B (28 B) | is-check/improving/PV/pruning 상태를 flag byte로 묶고 test/branch 공유; dead hash 삭제 | 상태 lifetime과 bit alias 검증; 짧은 jump 자체가 압축 결과를 개선한다고 가정하면 안 됨 / engine-owner |

### M4sseur

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [470fa53925](https://github.com/Diazepawn/M4sseur/commit/470fa53925c1cafeaaf84db3612abb5eb0ae9e9f) | M · 명시 바이트 수 없음 | 짧은 식별자 alphabet의 x/p 위치 및 2자 이름 순서를 바꿈; zero initializer 명시 | 시간 관리/검색 깊이/탭 가중치 변경도 있어 전체 patch는 동치가 아님 / candidate |
| [f9b89d2c7e](https://github.com/Diazepawn/M4sseur/commit/f9b89d2c7eda33eabfac485fb9e74232faed90c0) | M · 명시 바이트 수 없음 | minifier에서 서로 다른 scope 변수에 같은 짧은 이름 배정, TT 선언 합침, sleep loop→sleep_until | hardcoded 이름 예외/스레드 시간 정책 변경, 출력 nodes 삭제가 섞임 / engine-owner |
| [fa887befbc](https://github.com/Diazepawn/M4sseur/commit/fa887befbc5f5cdaf1c53ff5928efa8d91b81496) | B · launcher offset: 136→134, 139→137; 각각 header 2 B | POSIX-compatible launcher의 shebang을 /bin/bash→/bin/sh로 변경 | shell 기능이 POSIX subset일 때만 가능; wrapper offset 재계산 필요 / build-profile |
| [23fef58bf9](https://github.com/Diazepawn/M4sseur/commit/23fef58bf9773a798bc2a000335d0996864f6dfd) | M · 명시 바이트 수 없음 | 이름 alphabet 및 scope별 이름 재사용 지정 확대; thread 상수 52→103 | rename 규칙과 engine hardware policy 변경을 분리해야 함 / candidate |
| [1016b17554](https://github.com/Diazepawn/M4sseur/commit/1016b17554ab16f02fe8090b235f9efe9c56467b) | M · 명시 바이트 수 없음 | packed evaluation string/weights를 수정하고 여러 튜닝 대안을 보존 | size 후보 탐색에서 발견했으나 평가 값 변경; lossless compression 사례 아님 / engine-owner |

### we4k

선택 build/README/Board 파일을 검토했으며 같은 commit의 전체 평가/검색 변경은 범위 밖이다.

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [93dde6ad4a](https://github.com/ONE-RANDOM-HUMAN/we4k/commit/93dde6ad4aef461bdf4c8dd9d413f92090fc16eb) | B · README는 4096 B 안으로 packing 가능하다고 설명; 실제 byte 수 미기재 | Zig ReleaseSmall+NASM, sstrip -z, vondehi --xz --nostub, 83-byte shell header; OptionalSquare wrapper를 u8로 단순화 | 현재 toolchain에서 같은 크기 보장 안 됨; 당시 script는 외부 도구를 다운로드하므로 재현 시 pinning과 별도 실행 승인이 필요 / build-profile |
| [d30fdbc61f](https://github.com/ONE-RANDOM-HUMAN/we4k/commit/d30fdbc61fe78969c6bf7b788547e77b798e856f) | V · 명시 바이트 수 없음 | Zig build API와 -Drelease-small→-Doptimize=ReleaseSmall migration | compiler/API 변화가 과거 build 재현을 깨뜨리는 사례; 최신 코드와 당시 제출물을 구별 / validation |

### sunfish

큰 commit은 packer·entry·generator·harness·관련 ledger로 범위를 제한했다. `12d316aa` 개별 codec 전체는 감사하지 않았다.

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [892c2e76ce](https://github.com/thomasahle/sunfish/commit/892c2e76ce9328021d19f06d72af1ff47c04f947) | B · header 116→74 B (42 B); README 전체 수치는 다른 변화가 섞임 | named interpreter에 bash process substitution으로 payload를 전달해 tmp/chmod/cleanup 제거 | bash 및 /dev/fd 요구; artifact self-read/__file__ 계약, stdin와 argument forwarding 확인 / build-profile |
| [eb8897cc6c](https://github.com/thomasahle/sunfish/commit/eb8897cc6c884555992db0d9c2a745b90e2ee32c) | B · 주석: classic 3232→3210 B, nnue 3931→3900 B, pst_entry 3341→3295 B 등 | literal hoisting 비활성화+payload shebang 삭제를 조합; 더 긴 minified text가 더 작게 압축됨 | shebang만 삭제하면 classic +4 B 보고; 개별 역효과 후보를 탐색에서 미리 버리면 조합 이익을 놓침 / candidate |
| [09b3b4057c](https://github.com/thomasahle/sunfish/commit/09b3b4057c815c8acc383a4add9371a9f2f6e390) | V · 기록: shipped entry 3455→3410 B (45 B), 재측정 아님 | 다른 branch에만 있던 no-hoist/shebang 최적화를 복원하고 실제 packer A/B test 추가 | 4096 B ceiling만 통과시키면 45 B 회귀를 놓침; 원본 baseline과 같은 toolchain 비교 필요 / validation |
| [2e1e35f277](https://github.com/thomasahle/sunfish/commit/2e1e35f27725c9e59fa45ac3072979504daae23f) | P · 3812→3790 B (22 B), commit 본문과 source 주석 | big-int 인코딩 후 그대로 역추출하는 identity pipeline 제거; LSB-first bytes literal 및 단일 alphabet gap | 기존 decoded vector와 bit-exact round-trip 증거 필요; alphabet/인덱스/escaping을 함께 변경 / engine-owner |
| [18bad55575](https://github.com/thomasahle/sunfish/commit/18bad55575552280630b85f47c517e7057153eb1) | P · 제목: 29 B 절감, 전체 campaign NPS +29.59%; 이 commit 단독 속도값으로 해석 금지 | Move namedtuple을 tuple로 바꾸고 constructor/attribute 접근을 제거 | API 소비자 수정과 sorting tie order 유지 필요; Python reflection 차이 및 공개 API 제약 / engine-owner |
| [62456cf992](https://github.com/thomasahle/sunfish/commit/62456cf9928fa2e3d03bd3f7b67b5151a12ce1d4) | P · 3475→3378 B (97 B), generator 주석과 commit 제목 | 384 PST 값을 base90 string/mixed-radix 210로 저장하고 startup에서 원래 tables 복원 | 기존 literal tables를 독립 reference로 비교; quantization/mirroring 대안과 정확한 재인코딩을 분리 / engine-owner |
| [881dc747ad](https://github.com/thomasahle/sunfish/commit/881dc747ad9ae933279c820aa8b66f4886505d6b) | B · header tail offset +73; 같은 commit의 전체 압축 delta 미기재 | 2022년 pyminify+rename-globals+xz+shell self-extractor packing 도입 | 최종 header+compressed source를 비교; 최신 2026 NNUE tooling을 당시 제출과 혼동하지 않음 / build-profile |
| [202d772e9b](https://github.com/thomasahle/sunfish/commit/202d772e9b795a440f70af78fb8a19856963d378) | D · 기록은 +5 B (3350→3355), 절감이 아님 | root gamma seed를 pos.score-150로 바꾸면 첫 fail-high를 앞당긴다는 실험 문서 | 실제 검색 순서/중단 시 move가 바뀜; 작은 추가 용량으로 correctness 여유를 사는 엔진 아이디어 / engine-owner |
| [48508947f2](https://github.com/thomasahle/sunfish/commit/48508947f2eafbff9b4df3efb67fca2b2af666d1) | D · 기록: joint 15525 B vs split 16532 B; base3+LZMA 2840 B vs raw base3 3840 B(예시) | 실제 가중치로 조사하니 random-byte 실험 결론이 반전: alphabet packing 뒤 LZMA, code/data joint stream | 4K 적합 결과가 아니라 더 큰 실험; lossy quantization과 lossless encoding을 구별하며 byte 효과 합산 금지 / candidate |
| [12d316aa38](https://github.com/thomasahle/sunfish/commit/12d316aa3859adac136491ff6831328b46a51a64) | B · 도입 commit은 최저 byte 수 미기재 | 등록된 encoder × joint/split layout을 비교하고 독립 decoded-data reference와 실제 artifact boot/size로 랭킹 | 검토는 harness 및 공통 arm protocol; 모든 개별 codec 구현과 정확성을 감사한 것은 아님 / candidate |

### Pytteliten

실제 참가 확인 전의 인접 TCEC4K 목표 프로젝트.

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [4d69e29568](https://github.com/1337crisis/Pytteliten/commit/4d69e295684c09ec55827d6d8f0d6d3cf7785d62) | P · 명시 바이트 수 없음 | 별도 UCI move parser를 삭제하고 기존 move generation+moveToString으로 입력 move를 매칭 | 합법/지원 입력 domain에서만 같은 의미; parsing startup 비용과 잘못된 입력 처리 변화 / engine-owner |
| [ff2adb6916](https://github.com/1337crisis/Pytteliten/commit/ff2adb6916d3491851aa1323dc16aec184255e89) | P · 명시 바이트 수 없음 | mate/stalemate nested if를 return condition?mate:0로 변경 | C++ branch expression conversion 및 evaluation domain 필요; 최종 packed 개선은 별도 측정 / candidate |
| [d245275482](https://github.com/1337crisis/Pytteliten/commit/d24527548233b35d3ecb7303251b7f4a7176d1ca) | M · 명시 바이트 수 없음 | 긴 명시 return/parameter 타입을 auto로 변경 | template instantiation·deduced type·implicit narrowing가 달라질 수 있음; C에 적용 불가 / engine-owner |
| [057937a5e0](https://github.com/1337crisis/Pytteliten/commit/057937a5e01e11311d5c6bda25f3cbe970b4c423) | M · 삭제된 주석에 2369 B가 있으나 delta 근거 아님 | minifier가 모든 const token을 제거하도록 함 | const overload, constexpr, linkage, alias·readonly 및 최적화 의미를 바꾸므로 범용 규칙으로 금지 / reference |
| [9f3b46b322](https://github.com/1337crisis/Pytteliten/commit/9f3b46b32218dbe83a9d1521b7164f8fa4d34b99) | P · 추가 주석 1939 B; 이전 대비 delta 미기재 | using namespace std로 반복 std:: qualification 제거 | minified whole-program에도 name lookup/ADL/overload 충돌을 검증해야 함 / candidate |
| [d18a1730d3](https://github.com/1337crisis/Pytteliten/commit/d18a1730d3ea6540a1ba048c6b729e81ee949cb2) | V · 명시 바이트 수 없음 | minifier에서 struct/main을 보호해 struct 사용을 지원 | keyword whitelist의 작은 수정이며 scope-aware name resolution 증명은 아님 / validation |
| [ba711c475c](https://github.com/1337crisis/Pytteliten/commit/ba711c475cffd96a942fc24ae1e1c6f3ea27ea99) | V · 명시 바이트 수 없음 | 삭제 구간 주석을 #ifndef MINIFIED 및 build define으로 통일 | 원본과 축소 profile을 각각 실제 컴파일할 수 있게 하지만 의도적 기능 차이는 계속 별도 명시해야 함 / validation |
| [0cbb902cee](https://github.com/1337crisis/Pytteliten/commit/0cbb902cee7102d591a42f58f2cc884393df5bf9) | F · 명시 바이트 수 없음 | minifier deletion regions 도입 | 표시된 코드 삭제는 동치 증명이 아니며 feature profile로 다뤄야 함 / engine-owner |

### pygone

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [7432094865](https://github.com/scs-ben/pygone/commit/7432094865fb6ea9cbbb7db3d9a93c9328813672) | P · 명시 바이트 수 없음 | 클래스 piece-value constant를 모듈 전역으로 옮겨 반복 Board./self. 접근 제거 | Python reflection, subclass/attribute rebinding, monkey-patching이 관찰되지 않는 폐쇄 프로그램 조건 필요 / engine-owner |
| [ab7e4b6c5f](https://github.com/scs-ben/pygone/commit/ab7e4b6c5fba2f0343f8a9e979c36670ebce91aa) | P · 명시 바이트 수 없음 | if/else 선택식, castling mask shift 공통화, 공통 계수 인수분해, Boolean sum/add로 분기 표현 | Python int와 bool domain에서는 유망; overloaded object/side effect/short circuit 제외 / candidate |
| [98d2a6a19b](https://github.com/scs-ben/pygone/commit/98d2a6a19ba677cac35fcc1613be76347f93ea0e) | M · 명시 바이트 수 없음 | root movegen의 killers argument 삭제; None 검사 대신 truthiness 사용 | move order 변화와 falsey 유효값 존재 여부 확인 필요 / engine-owner |
| [7a67547886](https://github.com/scs-ben/pygone/commit/7a67547886babc8c44e64dd282e5eedb98938e55) | P · 명시 바이트 수 없음 | 한 번만 쓰는 from/to/promotion 지역 변수를 호출 인자에 inline | Python evaluation 순서·예외·locals reflection 차이를 확인 / candidate |
| [ad5f1c1f4e](https://github.com/scs-ben/pygone/commit/ad5f1c1f4e7afb3b2abdd5521f847f10dd051929) | V · 명시 바이트 수 없음 | inline module 코드의 backslash를 escape하고 minified shebang을 pypy3로 변경 | 코드를 다시 문자열에 담는 층에서 escape가 깨지는 실제 실패; 여러 encoding layer 구분 / validation |
| [0db781aa5f](https://github.com/scs-ben/pygone/commit/0db781aa5fc850bb1cea4269c2d6acf64c20d2cb) | M · 명시 바이트 수 없음 | builtin alias와 python_minifier 단계를 제거하고 직접 replacement/공백 정리 경로로 전환 | blank line 삭제는 multiline string에 영향을 줄 수 있음; fallback을 안전한 범용법으로 채택하지 않음 / validation |
| [172686702d](https://github.com/scs-ben/pygone/commit/172686702da4c74e43c6832ec8e907de6431fd1c) | M · 명시 바이트 수 없음 | quiescence alpha 갱신/return 구조 재배치와 delta-like early return 삭제 | binary shrink 제목이 있어도 검색 pruning 삭제임; 동일 의미 자동화 불가 / engine-owner |
| [417d42409e](https://github.com/scs-ben/pygone/commit/417d42409e53c76ea65fbc2acb8a6480fd3ed799) | M · 명시 바이트 수 없음 | disjoint bitboard OR→sum, king LSBit→bit_length, 임시변수 제거, 반복 TT guard hoist, 짧은 launcher | disjoint/king-singleton 불변식 필요; time_up을 미리 캡처하면 중간 취소 관찰이 달라짐; 예측 가능한 tmp 경로 주의 / engine-owner |
| [cbf5e9363e](https://github.com/scs-ben/pygone/commit/cbf5e9363e8f696e2fc841aff35bd2dd65f7ed12) | F · 명시 바이트 수 없음 | UCI movestogo 옵션 parsing 제거 | 프로토콜 지원 기능 삭제; 동일 의미 압축으로 분류 불가 / engine-owner |
| [30a1e4734a](https://github.com/scs-ben/pygone/commit/30a1e4734a4ce256f6ee39fa11b784118e081e82) | D · 명시 바이트 수 없음 | copyright preamble 연도/저자만 정정 | 제목만 보고 압축 후보로 분류하면 생기는 false positive의 예 / reference |
| [8d9fa29bdf](https://github.com/scs-ben/pygone/commit/8d9fa29bdf785d9b14d1739f49a5dcc67fd3c509) | M · 명시 바이트 수 없음 | 같은 값을 반환하는 TT guards를 OR로 합침; 시간 체크 주기를 매 node로 변경 | guard factoring은 후보지만 time polling 변경은 성능/중단 타이밍 의미 변화 / candidate |

### molly-tcec

| 커밋 | 분류 / upstream 크기 기록 | 확인한 기술 | 전제·위험 / 적용 경로 |
|---|---|---|---|
| [891728b00d](https://codeberg.org/latuernich/molly/commit/891728b00deccadf997d73f30dd99a7632b1023e) | V · 명시 바이트 수 없음 | rename 대상 집합을 HashSet→BTreeSet으로 바꾸어 이름 배정 순서를 결정적으로 고정 | HashMap iteration에 따라 다른 파일이 나오는 재현성 문제를 구조에서 해결 / validation |
| [b327cd08b2](https://codeberg.org/latuernich/molly/commit/b327cd08b27eaa94026c5e162d72aeed9e19bc45) | P · 명시 바이트 수 없음 | syn visitor로 main을 제외한 함수명을 수집하고 짧은 이름으로 변경 | 식별자 문자열 전체 치환은 scope/namespace/매크로/충돌 분석을 대신하지 못함 / candidate |
| [dc8ce701ca](https://codeberg.org/latuernich/molly/commit/dc8ce701ca8b3c30007624f42827dc771233f202) | B · 명시 바이트 수 없음 | 5종 match finder × nice 2..273의 1360개 LZMA1 설정을 비교, lc=2,pb=0 고정 | 명시 범위의 grid search; 원문 minification과 codec 후보의 교차 결과를 봐야 함 / build-profile |
| [7cdff1e4c6](https://codeberg.org/latuernich/molly/commit/7cdff1e4c666557d4ec7584c3092603df2225733) | P · 명시 바이트 수 없음 | binary literal을 decimal로, pawn 방향 함수를 선택해 중복 연산 공유, diagonal helper 재사용 | Rust 타입 추론/함수 pointer 선택 및 inline 비용 확인 / candidate |
| [4e654ad423](https://codeberg.org/latuernich/molly/commit/4e654ad423be70a6e133d45bdc6809132183258e) | P · 명시 바이트 수 없음 | castling mask 0b11/0b00001110/0b01100000을 짧은 decimal로 표현 | 같은 정수 타입과 연산 문맥이면 후보; 최저 source 길이가 최저 packed 길이를 뜻하지 않음 / candidate |
| [5895e746b0](https://codeberg.org/latuernich/molly/commit/5895e746b0e7a72d09e531d21e6e9210f7f5514f) | M · 명시 바이트 수 없음 | Zobrist const fn를 const block에 합치고 RNG recurrence/seed를 짧게 재설계 | hash 값이 변경됨; const block 단순화와 RNG 변경은 분리 / engine-owner |
| [97e37caff2](https://codeberg.org/latuernich/molly/commit/97e37caff2db5f0fbebc97f13da6cbb4c4be7725) | V · 제목은 큰 const inline의 성능 악화를 보고; 바이트 없음 | PST/ZOBRIST_KEYS를 const 인라인 대상에서 제외하는 name-based 예외 추가 | 예외를 NVCompact에 복사하지 말고 크기/재계산/constant promotion/수명 모델로 판단 / validation |
| [f943f605c5](https://codeberg.org/latuernich/molly/commit/f943f605c5dedbfb19c2cc6f0333bb4afa147993) | V · 명시 바이트 수 없음 | macro argument 안 const 치환 누락을 피하려고 검색 결과를 임시변수에 저장해 println에 전달 | macro token-tree는 일반 AST walk에 자동 포함되지 않음; 불완전 치환 경계 모델 필요 / validation |
| [d12cbe21a5](https://codeberg.org/latuernich/molly/commit/d12cbe21a5f072b32b1d3f36543a518c742b46aa) | P · 명시 바이트 수 없음 | syn 기반 const initializer 수집 후 Expr::Path와 match Pat::Ident에 대입, const 선언 삭제 | 전역 문자열 map은 binding resolution이 아님; forward reference/타입/매크로/패턴 경계 필요 / candidate |
| [9a0b655992](https://codeberg.org/latuernich/molly/commit/9a0b6559927e7ed2cbf5903d574b3a8a663c03be) | P · 명시 바이트 수 없음 | syn/proc_macro2 token stream으로 comments/whitespace를 제거하고 delimiter 재출력 | punctuation spacing, doc comments/attributes와 매크로 token 의미 보존 필요 / candidate |
| [1941cc396e](https://codeberg.org/latuernich/molly/commit/1941cc396e600322f490e3be14cd9ab9381bd29c) | V · 명시 바이트 수 없음 | 별도 indexer/inline visitor로 const 치환을 재구성; vec!를 std::vec::from_elem으로 변경 | 수집/변환 분리는 개선이나 식별자명만으로 binding 판정하면 한계; macro 경계를 명시해야 함 / validation |
| [05ea434b16](https://codeberg.org/latuernich/molly/commit/05ea434b165ffda6f06238482cd2974b72377729) | V · 명시 바이트 수 없음 | TT 초기화 앞뒤 minify skip 표시를 제거해 minified 실행에서 실제 TT를 설정하도록 고침 | development 경로만 검사하면 제출 artifact가 다른 의미가 될 수 있는 직접 사례 / validation |
| [ff89cde6c5](https://codeberg.org/latuernich/molly/commit/ff89cde6c504d4986adcbeb8433037a166d3accf) | M · 명시 바이트 수 없음 | PST 평균을 별도 material 값으로 분리하고 좁은 residual 값을 저장 | diff의 수치가 단순한 정확한 offset 차만은 아님; retuning/rounding 포함, lossless 재인코딩만 따로 후보화 / engine-owner |
| [45b1cbf0bd](https://codeberg.org/latuernich/molly/commit/45b1cbf0bdd2fa96c4d31cc8bec54a565121c697) | P · 명시 바이트 수 없음 | TT entry를 &mut로 잡아 lookup/storage에서 같은 변수 재사용 | 재귀 검색과 공유 TT 사이 long-lived mutable reference alias는 별도 안전성 검토; 무조건 자동화 금지 / engine-owner |
| [ff85421ac9](https://codeberg.org/latuernich/molly/commit/ff85421ac9ad80a3a52f953cf4f0898e78137d26) | F · 명시 바이트 수 없음 | minify skip 구간으로 node-count argument/update 및 info nodes/nps 출력 삭제 | 관찰 가능한 UCI output 기능 제거; 무손실 압축 기준과 분리 / engine-owner |

## 보관 원칙

이 문서와 JSON에는 분석·커밋 식별자·링크만 담는다. 외부 엔진 소스, 바이너리, 가중치, loader 및 bootstrap을 Rove4k에 벤더링하지 않는다. 각 기술의 채택/보류/거절 상태는 이 근거 기록을 삭제하는 이유가 되지 않는다. 적용 시 별도의 pinned build 결과와 semantic/performance gate를 연결한다.

