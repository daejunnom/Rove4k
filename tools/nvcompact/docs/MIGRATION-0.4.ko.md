# NVCompact 0.4 — Rove4k 내부 Rust 도구로 이관

## 저장소와 책임

독립 `daejunnom/NVCompact`의 기준 커밋은
`4f238d1e56faca3a8c926098c6d5be2c98728cb8`이다. Rove4k의 이관 전 기준은
`3626b65fd8fe83814fee1a19821dcd237129cbb4`이다. 이관 후 운영 코드, 테스트,
문서, 예제, Cargo 및 npm 진입점은 모두 Rove4k에 있다. 독립 저장소를 네트워크
의존성이나 실행 경로로 사용하지 않는다. 이 작업에서 독립 저장소를 삭제하지 않았다.

NVCompact는 **N-version compaction**에서 온 이름이다. 서로 다른 언어·구현,
표기, 링크 배치, ELF 배포 형태와 압축 recipe를 비교한다는 뜻이다. 변수명 축약만을
가리키거나 모든 후보가 독립적인 알고리즘이라는 뜻은 아니다.

| 위치 | 역할 |
| --- | --- |
| 루트 `Cargo.toml`, `Cargo.lock` | Rust workspace와 잠근 개발 의존성 |
| `tools/nvcompact/src/` | Rust 운영 구현 |
| `tools/nvcompact/npm/` | private npm 진입점 `@rove4k/nvcompact` |
| `tools/nvcompact/examples/`, `linker/` | 프로젝트가 작성한 작은 예제와 링커 스크립트 |
| `tools/nvcompact/comparisons/` | 외부 엔진 입력의 URL·해시·배포 계약; 실제 입력 제외 |
| `tools/nvcompact/reference/v0.3/` | 필터링한 이전 Python 구현·검사·문서·결과 |
| `tools/nvcompact/AGENTS.md` | 내부 개발 도구의 별도 작업 규약 |

## 벤더링하지 않은 이관

전체 git 이력을 합치면 과거에 포함했던 외부 엔진 코드도 Rove4k 이력에 들어간다.
이를 피하기 위해 추적 파일의 필터링한 스냅샷을 사용했다. 이전 저장소의
`packages/tcec4k-lab/inputs/`와 `vendor/`에 있던 51개 외부 파일은 제외했다.
필터링 후 보존한 기존 추적 파일은 309개이며 이관 기록은 별도로 추가했다.

메타데이터 안에 있던 엔진 shell header 30개도 원문 대신 길이와 SHA-256으로
바꿨다. 대상 12개 JSON의 변환 전후 해시는
[이관 기록](../reference/v0.3/evidence/migration-v04.json)에 있다. 운영 envelope는
외부에서 제공한 원본의 앞부분을 읽고 이 해시와 길이를 확인하므로 header 소스를
저장소에 넣을 필요가 없다. 제3자 코드·실행 파일·압축 payload·아카이브를 npm에도
포함하지 않는다.

과거 Python 구현은 읽을 수 있는 비교 기준으로 남겼다. 과거 결과를 다시 조사할 때는
정확한 외부 입력과 당시 실행기를 별도로 준비해야 한다. 과거 출력과 현재 출력의
형식이 같다고 가정하거나 Rust에서 Python을 몰래 호출해 호환성을 만들지 않는다.

## Rust로 옮긴 운영 경로

- argv 기반 컴파일·링크 포트폴리오와 새 입력 스냅샷에서의 바이트 재현.
- 원본 파일을 포함한 gzip, zlib, bzip2, LZMA, XZ, raw LZMA2 및 x86 BCJ 후보.
- 전체 header·loader·payload를 포함한 크기 비교와 실제 decoder 복원 확인.
- C/C++/Rust/Python의 타입을 고려한 literal·trivia 후보와 Clang AST 기반 C 변환.
- 외부 제출 파일의 envelope 재압축과 General/ELF 구분.
- Rust 체스 규칙 라이브러리를 이용한 독립 합법수 검사와 유한한 UCI 세션.
- 읽기 전용 자원 계획, 별도 `--start`, 입력·도구·자원 재확인.
- 소유한 자식 프로세스 그룹, 유한한 시간·출력·CPU·주소 공간 제한과 취소·회수.

Rust 도구에 Python 인터프리터를 backend로 붙이지 않았다. 사용자가 선언한 외부
컴파일러·인터프리터와 독립 예제 검증기는 여전히 명시적으로 실행할 수 있다.
General 4K용 일부 제출 loader가 Python을 사용하는 것과 도구 자체의 운영 언어는
별개의 사항이다. Python 엔진의 구문 판정에는 Rust로 작성된 `rustpython-parser`를
사용한다.

압축과 링크 후보는 제한한 Rust worker에서 병렬로 평가한다. 후보 ID와 동률 선택은
완료 순서에 의존하지 않는다. 이는 엔진의 탐색 병렬성을 검증했다는 뜻이 아니다.
전체 후보 예산과 각 compiler/engine의 내부 worker도 함께 고려해야 한다.

## 실행 계약의 변화

`build`는 압축하지 않는 컴파일·링크 경로다. 기본적으로 target·검증기를 실행하지
않고 원시 링크 바이트를 새 스냅샷에서 재현한다. 실행 검사가 필요하면 `--verify`를
명시한다. `run`은 독립 oracle을 선언한 후보를 검증하며 최종 제출 형태까지 비교한다.

`envelope`의 `smallest`는 측정 최소다. UCI와 필요한 배포·규칙 조건을 확인하기 전에는
출전 가능한 `accepted`로 취급하지 않는다. `replay`는 압축 탐색을 반복하지 않고
선택 recipe를 별도 디렉터리에서 재현한다. Rust 실행 파일·codec 및 입력 fingerprint가
다른 과거 recipe는 조용히 새 구현으로 대체하지 않는다.

고정 해시·worker를 줄여서 대용량 엔진 검사를 통과시키지 않는다. 자원 계획은 실행을
하지 않으며, `resource run … --start`가 당시 조건을 다시 읽는다. 자원이 모자라거나
조사 범위가 부족하면 그 상태를 기록한다. per-process 제한과 관측한 가용 메모리는
전체 프로세스 트리의 메모리를 예약하는 cgroup과 다르다.

## 별도 작업 규약

[도구 규약](../AGENTS.md)은 Rovent와 MMMM의 실제 공개 규약을 읽고 책임·소유권·수명,
실패 원인 수정·근거 있는 검증을 가져왔다. 참조한 커밋과 문서 링크를 규약에 고정했다.
다른 프로젝트의 역할 ID, crate 수, 줄 수, GPU 예산과 임시 실행 권한은 가져오지 않았다.

엔진은 제출 용량과 매 노드 비용이 중요하다. 개발 도구에는 필요한 파서, 오류 처리,
진단과 적절한 라이브러리를 사용할 수 있다. 둘 다 구체적인 알고리즘과 물리적 구조는
에이전트가 개선할 수 있으며, 기존 설계와 다르다는 이유로 좋은 대안을 거절하지 않는다.
실패한 입력에 예외를 붙이는 대신 잘못된 원인 로직과 전제를 수정한다는 기준도 공통이다.

이전에 작성한 엔진·압축 설계의 외부 핸드오프는 그대로 참고 자료로 유지한다. 이관이
그 설계를 의무 아키텍처로 만들거나 이전 설계를 폐기하는 것은 아니다.

## 검증의 범위

이식의 압축률 판정은 동일한 공개 입력에 대해 이전 Python의 측정 최소와 원본 전체
파일을 각각 비교한다. 실제 결과, 재현, UCI, 자원 차단, 공개 파일 미확보 및 규칙 검토는
[TCEC 비교 결과](TCEC-RESULTS-0.4.ko.md)에 구분한다. npm 포장·설치 검사는 npm 공개
게시와 다르며 패키지는 private 상태다.
