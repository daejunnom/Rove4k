# 값 영역·n-version 제안과 refinement 성능 검증

이 문서는 PR #16의 후속 C 영역 분석과 refinement 알고리즘을 검증한 기록이다.
비교 기준은 `d0c962ae49d2a4a664f9feef41bf8c7a285c16bd`이며,
앞선 streaming/cache/worker 개선의 기록은 [이전 결과](PERFORMANCE-ADVICE-RESULTS.ko.md)에 보존한다.
여기의 시간 차이는 NVCompact 개발 도구의 측정이다. 엔진 기력·탐색 속도·제출 크기 개선을 뜻하지 않는다.
C++·Rust 확장은 이 C 단계 이후 별도 언어 의미 검증을 거쳤으며,
최종 수치와 전체 입력의 보류 범위는 [언어 확장 결과](LANGUAGE-RESULTS.ko.md)에 있다.

## 1. 실제로 추가한 분석

구간, 알려진 0·1 비트, 선택적 유한 집합을 한 `Domain`에 보관한다.
분기 합류, 대입, 루프·별칭 등에 따른 무효화가 같은 사실의 수명을 관리한다.
단일 안정된 정수 바인딩의 순수 식을 공통 typed IR로 낮춘 뒤,
보수적 포함 영역의 모든 값을 비교하여 알고리즘 계열별 대안을 남긴다.
관측 기반 경로도 같은 비교기를 사용하되 정적 사실로 승격하지 않는다.
설계·타입·예산·캐시 계약은 [DOMAIN-NVERSION.ko.md](DOMAIN-NVERSION.ko.md)에 있다.

### PR #12의 rank 식

원본 `(to>>4)==0||(to>>4)==7`는 ASCII 22 B다. 사용 지점에서 `0 <= to <= 127`을
확인한 자체 fixture에서는 다음 대안의 타입과 값을 전체 128개 입력에서 비교했다.

| 보존한 대안 | 원문 길이 | 검사한 입력 |
| --- | ---: | ---: |
| `!(to+16&96)` | 11 B | 128 |
| `to<16||to>111` | 13 B | 128 |
| `(to-16&96)==96` | 14 B | 128 |
| `(unsigned)to-16>95` | 18 B | 128 |

이 결과는 64개 legal 0x88 square보다 넓은 `0..127`에서도 성립한다.
반대로 `!(to&0x88)`만으로 상한을 증명하지는 못한다. 256은 이 mask 검사를 통과하지만
원본과 `!(to+16&96)`의 결과는 다르다. 128·135도 영역 밖 반례다.
음수 signed right shift와 signed overflow는 지원 의미에서 보류한다.

합성기는 변수 이름, 16, 96, 체스 보드를 정답으로 등록하지 않는다.
같은 생성 규칙으로 `0..63`의 `!(x+8&48)`, `0..511`의 `!(x+64&384)`도 확인했다.
원본 128값 사례의 생성 후보는 3,656개, 비교 후보는 3,638개,
평가 방문은 25,048회, cache hit는 13,580회였다. 전체 결과 벡터 15개를 색인하고
의미 별칭 5개를 만들어 중복 cache 값 640개를 회수했다. 이 유한 문법의 탐색은 완료됐다.

### 관측을 이용한 조건부 제안

전체 식에 들어갈 때 반드시 실행되는 읽기를 표본의 기준으로 사용한다.
단락 연산 오른쪽의 일부 표본을 전체 식의 입력으로 대체하지 않는다.
관측 최소와 최대가 0·127이면, 표본에 없었던 값까지 포함한 128개 구간 전체를 검사한다.
관측된 고정 비트나 sparse sample 자체로 그 구간을 더 줄이지 않는다.

실제 계측 사본에서 얻은 0..127 로그는 조건부 mask 제안과 영역 밖 128 반례를 만들었다.
135·256을 추가한 로그는 0..256 closure를 만들었고 해당 전체 rank 식에 대한 대안을 통과시키지 않았다.
정적 영역과 충돌하는 표본은 비교를 보류했다. 원본 bytes와 정적 범위는 그대로였다.
표본은 이후 모든 실행의 범위를 증명하지 않는다.

## 2. 독립 감사와 검사

C 단계의 전체 Rust workspace 결과는 **136개 통과, 실패 0개**다.
library 114개, advice 통합 2개, packing 10개, source-search 10개이며
0개인 main/doc-test 그룹을 성공 개수에 더하지 않는다.

| 검사 | 실제 확인한 범위 | 결과 |
| --- | --- | --- |
| Native C11 정수 oracle | 여섯 정수 rank의 연산·cast·shift·단락·삼항식, `_Generic` 타입과 값 | 7,757개 평가 일치, UBSan 오류 0 |
| 위험한 의미 경계 | 잠재적 UB 또는 implementation-defined 평가 | 931개 보류, native 실행하지 않음 |
| 실제 출력 제안 적용 | 자체 원본 함수에 94개 positive 제안을 각각 삽입·컴파일 | 124,738개 입력 비교, 불일치·UBSan 오류 0 |
| Domain oracle | signed/unsigned 4비트 구간·consistent known bits·경계 교차, sparse 합류 | 65,025개 sparse set 합류 포함 통과 |
| 계측→로그→재분석 | entry read, RHS-only, sparse 표본, 135·256 확장, 정적 모순 | 모든 요구 경계 확인 |
| Codec와 비용 owner | 이전 정렬 알고리즘의 ordered domain, seed union, stream boundary, cache/fresh/worker | 별도 11개 통과; 통합 suite에도 포함 |

자체 19함수 CLI fixture는 64개 식을 보관하고 8개를 출력 한도로 생략했다.
2개 탐색도 한도에 도달하여 보고서의 `complete=false`를 유지했다.
94개 검사는 실제로 출력된 positive finding에 대한 검사이며 생략된 모든 후보를 검증한 결과는 아니다.
증거의 소스·바이너리·명령·원시 기록 지문은
[domain-validation.json](../evidence/pr16/domain-validation.json)에 있다.

### 감사에서 근본 경계를 수정한 항목

| 발견한 원인 | 수정한 책임 |
| --- | --- |
| 유한 흐름 평가가 후보 합성 예산 밖에서 반복됨 | 흐름 owner에 별도 예약 예산과 exhaustion을 두고 정밀도 보수적 축소 |
| 순수 삼항식의 sparse 결과가 `if/else`보다 일찍 사라짐 | 양쪽에 같은 typed finite image·분기 합류 원칙 적용 |
| LP64 검사만으로 64비트 모델·signed 표현을 충분히 식별하지 못함 | frontend의 기존 모델 probe에서 확인하는 정수 표현 강화 |
| 큰 유한 집합의 JSON 목록 생략을 정확한 소속 검사처럼 읽을 위험 | cardinality/omission과 `static_membership_scope`를 보고, 구간+known bits로 넓게 재구성 |
| 후보별 공통 식을 다시 계산함 | 요청 수명의 DAG와 전체 typed 결과 벡터만 재사용, 부분 벡터 별칭 금지 |

별도 에이전트 감사는 사람의 PR 승인이나 모든 프로그램의 의미 증명이 아니다.

## 3. 같은 Rove4k·TCEC 입력을 다시 확인한 결과

기존 general 11개와 ELF 2개, **13개 original artifact의 SHA-256을 모두 다시 대조**했다.
외부 엔진 소스·실행 파일은 저장소에 추가하지 않았다.
다음 표는 C 단계의 지원 범위를 고정한 비교다. 이후 언어 어댑터의 성공으로 소급하지 않는다.

| 입력 | 같은 문맥의 비교 | 결과와 한계 |
| --- | --- | --- |
| PR #12 F 정본 | source 25,755 B, C11·`-pthread`; baseline/final frontend 문맥 일치 | 분석 26함수·보류 8함수·읽기 99곳 유지. finding 5→6, `promotion?2:0` → `promotion*2` 추가 |
| Moonfish payload | source 10,608 B, GNU11·`-pthread` | 분석 34함수·보류 2함수·읽기 70곳 유지. 새 expression 47곳, 기존 상수 그룹 8개, 새 replacement 0개 |
| 4k.c v9 정본 | 실제 Makefile의 GNU2x/C23 문맥 | 현재 C frontend의 미지원 표준으로 거절. `bool`·`true`·attribute를 임의 수정해 성공시키지 않음 |
| ice4·4ku·c4ke·M4sseur | C++ 입력 | 이 C 단계에서는 source-domain 분석 미지원 |
| molly | Rust 입력 | 이 C 단계에서는 source-domain 분석 미지원 |
| PyGone·Sunfish | Python 입력 | 고정 폭 C 정수 영역 모델 미지원 |

PR #12 확인 head는 `b53ef1f5891b46ff1da4e1f326c78c9a6778ef37`이며 F source 지문은
`ec39b5641ac9fc5ab19a0c919c05e0d68169b461cc1d32afeee83274926becbd`다.
F의 rank 식은 호출자 move-generator 전제가 함수 밖에 있어 이 분석이 `0..127`을
자동으로 주장하지 않았다. shipping transformation의 기존 전제를 일반 함수의 증명으로 가져오지 않는다.

Moonfish의 `av*32` 탐색은 후보 10,000개 제한에 도달했다.
호출자·메모리 별칭 관계가 필요한 영역과 탐색 한도 때문에 얻지 못한 제안을 구분한다.
새 대안 0개는 전체 최적성의 증명이 아니다. 4k.c의 소스 commit은
`880a877d6af2046cc5ce7deb85ea5ad2855b41a1`이고 source 지문은
`69d9620e0c274f7bc2e862c5dbbadfac07f329011320fa886c99390bdedd6ea2`다.

## 4. 채택한 성능 알고리즘

기존 adaptive refinement는 initial recipe 전체를 복제하고 legacy와 augmented domain을
각각 정렬한 뒤, 두 refinement domain을 모두 확장하여 커지는 벡터에 `contains()`를 반복했다.

새 경로는 `(cost, declaration index)` 순서에서 서로 다른 최상위 두 family를 선형으로 찾는다.
최대 네 seed의 identity를 확장 전에 비교한다. 정규화로 지우는 필드는 실제 expansion이
덮어쓰는 `mf`, `nice_len`뿐이며 나머지 typed recipe 필드는 모두 남긴다.
같은 identity가 만드는 ordered domain은 같고 서로 다른 identity의 domain은 겹치지 않는다.
따라서 한 번만 materialize해도 기존 recipe 목록·순서·동률·오류 경계가 유지된다.

planning의 최악 작업은 대략 `O(n log n + r²)`에서 `O(n+r)`로 줄었다.
initial recipe 전체 clone과 두 번째 expanded-domain 임시 벡터도 없어졌다.
codec 실행, 후보 범위, worker window, cache identity와 fresh 재생성 규칙은 그대로다.

### 최종 비교: 조건·버전마다 4회, 총 96회

같은 benchmark 예제를 별도 build target으로 빌드했다. CPU 0–3을 사용하고
다른 에이전트의 CPU 작업을 멈춘 구간에 버전을 번갈아 측정했다.
공유 호스트의 외부 변동은 통제하지 못했다. 수치는 wall time 중앙값이다.

| 조건 | 기준 | 최종 | 시간 변화 |
| --- | ---: | ---: | ---: |
| Thorough planning 128회 | 1.759921 s | 0.020000 s | −98.86%, 약 88배 |
| Normal legacy 실제 비용, jobs=4 | 0.742630 s | 0.708408 s | −4.61% |
| Tiny cold gzip, jobs=1 | 0.108600 s | 0.117531 s | +8.22% |
| 16 KiB cold, jobs=1 | 0.617599 s | 0.603180 s | −2.33% |
| 16 KiB cold, jobs=4 | 0.277009 s | 0.277369 s | +0.13% |
| 512 KiB mixed, jobs=1 | 3.540638 s | 3.405630 s | −3.81% |
| 512 KiB mixed, jobs=4 | 2.243866 s | 2.180934 s | −2.80% |
| 8 MiB restore, jobs=4 | 0.057307 s | 0.052896 s | −7.70% |
| 4ku retained source bytes, jobs=4 | 0.160506 s | 0.158879 s | −1.01% |
| ice4 retained source bytes, jobs=4 | 0.140682 s | 0.147968 s | +5.18% |
| Moonfish retained source bytes, jobs=4 | 0.172032 s | 0.159338 s | −7.38% |
| 4k.c original ELF bytes, jobs=4 | 0.075636 s | 0.073395 s | −2.96% |

**88배는 planning-only 결과**다. initial 605개, refinement 4,050개와 synthetic cost를
사용하며 codec을 실행하지 않는다. 실제 legacy 비용의 4회 범위는 서로 겹쳤다
(기준 0.649–0.851 s, 최종 0.633–0.871 s). 보편적인 압축 가속 보장으로 읽지 않는다.
나머지 fixed portfolio는 adaptive refinement를 실행하지 않는 대조군이다.
그 시간 차이는 새 planning 알고리즘의 성과로 귀속하지 않는다. Tiny·ice4의 느린 중앙값도 보존했다.

RSS는 대부분 inherited launcher footprint의 영향을 받았고 mixed jobs=4 중앙값은
25,228→25,532 KiB였다. **이번 변경으로 process RSS가 줄었다고 주장하지 않는다.**
새로운 multithreading 정책도 추가하지 않았다. 앞선 bounded worker와 fresh 경계를 보존하면서
그 앞의 serial planning 중복을 제거했다.

4ku·ice4·Moonfish source payload는 각각 10,308·8,750·10,608 B,
4k.c ELF는 3,932 B다. benchmark의 inert header를 썼으므로 실제 엔진 envelope의 제출 크기 비교가 아니다.
엔진을 실행하지 않았으며 실제 제출물 적격성·UCI·기력 캠페인 결과를 만들지 않았다.

### 산출물·실행 동일성

88개 cost process와 8개 planning process에서 149,104회 timed codec 실행을 확인했다.
codec cache hit·실패·not-started는 모두 0이다. input 길이·hash, timed minimum-cost vector,
대표 recipe 전체 결과 vector, winner 길이·hash, planning recipe 순서가 기준/최종에서 같았다.
3,352개 대표 recipe-result record를 fresh 결과와 비교하고 88개 대표 winner bytes를 직접 비교했다.

각 timed codec은 자기 실행 안에서 입력 bytes 복원을 확인한다.
버전 사이의 recipe별 encoded stream 비교는 이후의 대표 base payload에 대한 것이다.
timed unique 입력의 모든 중간 stream bytes를 버전 사이에서 전수 대조했다는 뜻은 아니다.
전체 96회 기록, 범위, source/binary 지문, 입력 출처는
[domain-performance.json](../evidence/pr16/domain-performance.json)에 있다.

### 채택하지 않은 실험

출력 한도 크기의 heap scratch는 첫 cold pilot에서 tiny 시간이 115.487→171.139 ms로
느려져 제외했다. stack의 필요한 prefix만 초기화하는 방식도 별도 96회 matrix와
60회 ablation에서 넓은 이득을 확보하지 못했고 small jobs=4의 느린 중앙값이 남았다.
이 방식도 64 KiB stack 예약·probe는 유지되어 실제 stack/RSS 감소를 뒷받침하지 못했다.
추가 unsafe 변환을 채택하지 않고 기존 initialized scratch를 유지했다.
실패·미채택 source snapshot과 측정 위치를 evidence에 보존했다.

공유 Cargo target에서 stale example을 동일 binary hash로 발견한 초기 시도도 기록했다.
최종 기준/후보는 별도 target에서 다시 만들었으며 최종 96회에 stale binary 측정은 포함하지 않았다.

## 5. 재현 접점과 전달 범위

자체 예제는 [domains.c](../examples/advice/domains.c)이며 `advise-c`로 분석한다.
성능 접점은 `cargo run --release -p nvcompact --example performance -- MODE JOBS`다.
`tiny`, `small`, `legacy`, `mixed`, `restore`, `planning`을 지원하며
실제 bytes 비교는 `performance file JOBS INPUT`으로 실행한다.
같은 예제를 기준/후보 양쪽에 사용하고 evidence의 recipe·환경·입력 hash를 맞춰야 한다.

PR #12 인계 문서는 이미 NVCompact PR #16의 변경 파일에서 제거해 별도 보존했다.
이 도구의 제안은 실제 압축 후보나 rewrite admission으로 연결하지 않았다.
범용 CFG 고정점, 함수 간 요약, 여러 변수의 관계, 일반 메모리 모델과 대형 영역의 SMT 증명은
현재 지원 범위 밖이다. PR 병합과 npm 공개 게시는 이 검증에 포함되지 않는다.
