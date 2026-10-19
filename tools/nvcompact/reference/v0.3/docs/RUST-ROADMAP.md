# Rust 전환 방향

NVCompact 0.3은 Python 구현을 유지한다. 이후 핵심 구현을 Rust로 교체하는 방향을 채택하되, 이번 버전이 Rust로 구현됐거나 이미 빨라졌다고 보고하지 않는다. 이 문서는 전환의 목적과 현재 제안을 설명하는 결정 기록이며, crate 개수·디렉터리·특정 병렬 프레임워크를 영구 규약으로 만들지 않는다.

## 목표와 비용을 구분한다

Rust 전환의 목표는 많은 후보를 처리할 때의 조정·복사·할당 비용을 줄이고, 소유권과 공유 접근을 언어 수준에서 더 명확히 표현하며, Python 설치 의존성을 단계적으로 제거하는 것이다. 실제 이득은 프로파일링과 동일 작업량 비교로 판단한다. 외부 compiler/linker와 C로 구현된 codec에서 대부분의 시간을 쓰는 작업은 orchestration 언어를 바꾸는 것만으로 크게 빨라지지 않을 수 있다.

Rust의 소유권·타입 시스템은 스레드 간 잘못된 소유와 공유를 컴파일 단계에서 제한하는 데 도움을 준다. 그러나 안전한 Rust만 사용해도 논리 오류·교착·프로세스 누수·잘못된 의미 변환까지 자동 방지되는 것은 아니다. 외부 C 라이브러리, LLVM frontend와 OS 인터페이스의 안전성도 별도로 판단한다.

근거: [Rust의 동시성 설명](https://doc.rust-lang.org/book/ch16-00-concurrency.html), [scoped thread API](https://doc.rust-lang.org/std/thread/fn.scope.html).

## 옮길 책임과 권장 순서

| 대상 | 먼저 보존할 계약 | 전환 시 확인할 비용 |
|---|---|---|
| 계획·입력·recipe 해석 | 입력 지문, 경로·argv, 원본 후보, 상태와 오류 의미 | 파싱·hash·복사, 대형 입력을 여러 번 읽는 비용 |
| 후보 스케줄링과 실행 수명 | 명시적 실행, 예산, 취소 후 실제 종료, 소유한 작업만 정리 | 작업자 수, 큐 크기, 외부 compiler의 자체 스레드와 총 RAM |
| 빌드·링크 및 결과 선택 | `build`의 무압축·기본 무검증, `run`의 검증, 전체 파일 비교 | compiler 호출 중복, 공통 object 재사용, 결과 보존 비용 |
| 표기·구조 후보 생성 | C 타입·부작용·관측 계약과 적용 불가 진단 | AST 전송·메모리, 반복 파싱, candidate별 source 복사 |
| codec와 배포 파일 생성 | header·loader·payload를 포함한 실제 크기, 복원 및 recipe | codec 작업 메모리, 사전 크기, FFI·순수 Rust 구현의 속도와 bitstream 차이 |
| UCI·resource 검사 | plan 무실행, `--start`, 옵션 보존, 실제 최종 파일, 상태·시간 | I/O, 출력 상한, 시작 시간, 대상 RAM과 자식 수명 |

첫 단계는 바뀌는 backend의 경계를 명확히 하고, 실제 병목이 있는 조정·입력·후보 처리부터 옮기는 것이다. 필요하면 Rust 실행 파일을 현재 npm CLI 뒤에 연결할 수 있다. 이후 검증된 Rust 구현이 기능을 대체하면 Python 경로를 줄인다. 전체 코드를 한 번에 다시 작성하거나 특정 FFI 구조를 먼저 고정할 의무는 없다.

## 병렬화와 메모리

후보마다 전체 소스·도구·사전을 복사하지 않도록 불변 입력을 공유하고, 작업별 가변 상태는 소유 범위를 분명히 한다. scoped threads나 bounded worker pool은 후보 선택지다. `Send`/`Sync` 제한을 우회하는 광범위한 `unsafe impl`을 성능 최적화로 취급하지 않는다.

`--jobs`만으로 compiler와 codec의 내부 스레드까지 제어된다고 가정하지 않는다. 실제 합계 CPU와 RAM을 기준으로 동시에 시작할 작업을 정하며, 메모리가 큰 codec 조합은 동일한 작업자 수에서도 동시성이 달라질 수 있다. 자원 추정 실패·작업 취소·정리 실패는 정상 결과와 구분한다.

큰 bytes는 가능한 한 재사용 가능한 불변 버퍼 또는 명시적으로 소유한 파일로 유지한다. 파일 매핑, reference counting, arena, 압축 cache는 실제 크기·수명·접근 패턴을 확인해 선택한다. zero-copy나 lock-free라는 명칭만으로 더 좋은 설계라고 판단하지 않는다.

## 프로세스 수명은 직접 보존한다

Rust의 `Child`를 drop하는 것만으로 실행 중인 자식이 종료되거나 회수되는 것은 아니다. 명시적인 취소 요청, 소유한 그룹의 종료, `wait`/reap, 출력 처리와 정리 상태 기록이 필요하다. 프로세스 그룹·cgroup·pidfd 같은 OS 수단은 선택한 플랫폼의 실제 지원과 권한을 확인하고 사용한다.

현재 npm/Python 경계가 보장하는 `build` 기본 무실행, `resource plan` 무실행, `resource run --start`, timeout과 owned cleanup을 전환 후에도 유지한다. Linux 프로세스 그룹과 개별 프로세스 자원 제한을 작업 전체의 hard RAM 예약으로 확대해 보고하지 않는다.

근거: [Rust Child 수명·kill·wait](https://doc.rust-lang.org/std/process/struct.Child.html), [Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html).

## 의미와 재현의 인수

Python 구현과 Rust 구현을 비교할 때 공유한 parsing/변환 코드가 같은 오류를 만들 수 있다는 점을 고려한다. 독립 관측이 필요한 위험에는 실제 compiler 실행, 별도 checker, bytes 대조와 입력·상태 관측을 사용한다. 검사기를 복제해 같은 잘못된 기대값을 만드는 방식은 피한다.

codec backend나 버전이 바뀌면 복원 결과가 같아도 compressed bytes가 달라질 수 있다. recipe에는 실제 backend·버전·입력·도구를 구분해 남기고, 옛 recipe를 새로운 결과에 맞춰 자동 갱신하지 않는다. 필요한 옛 구현은 명시적인 버전 재현 경로로 보존할 수 있다. 새 backend가 옛 backend와 바이트가 같다고 주장하려면 실제로 확인한다.

전환 중 차이가 나오면 원인 로직 또는 잘못 정의한 전제를 수정한다. 입력 이름별 예외, 검사 생략이나 자동 기대값 갱신으로 해결하지 않는다. 각 단계는 해당 변경의 구체적인 위험을 확인할 만큼 검증하며, 매 변경마다 모든 역사적 엔진과 거대한 메모리 실행을 반복하지 않는다.

## 이번 버전과의 관계

이번에 추가한 `build`, `rewrite-c`, `resource plan/run`의 명령·산출물·상태가 앞으로 옮길 외부 계약이다. 현재 구현 방식 자체를 Rust에 그대로 번역할 의무는 없다. 보다 나은 방식이 확인되면 생산자·소비자·문서와 관련 근거를 함께 갱신한다.
