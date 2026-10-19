# 원본 실행의 자원 계획과 관측

[index.json](index.json)은 공개 원본 8개에 대해 **같은 최종 Rust 실행 파일로 계획을 만들고
명시적 `--start`를 요청한 실제 결과**와 후속 후보 검사를 연결한다. `runtime_blocked`라는 과거 manifest
메모를 이번 실행 결과로 재사용하지 않았다. 원본의 TT 크기, 스레드 수, CPU 감지와 탐색
상수는 변경하지 않았다.

| 원본 | 첫 실행 결과 | 실제 확인한 범위 |
|---|---|---|
| ice4, c4ke, M4sseur, molly, STRO4K | `blocked` | 선언한 메모리와 여유분이 당시 관측한 가용 추정치를 초과하여 대상 프로세스를 시작하지 않음 |
| 4k.c v9.0 | `blocked` | 22 GiB ELF 가상 매핑을 보수적으로 반영한 계획이 자원 조건을 충족하지 않음 |
| PyGone | `blocked` | 1 GiB 포인터 테이블과 작업 공간·여유분을 합친 2 GiB 입장 조건을 충족하지 않음 |
| Moonfish | `fail` | 원본 wrapper는 시작했지만 raw `unxz` 호출이 실패하여 C 엔진이 만들어지지 않음 |

4k.c의 22 GiB는 ELF `PT_LOAD.p_memsz`에서 확인한 **가상 주소 매핑 크기**다. 실제 RSS
측정값 또는 물리 메모리 하한으로 해석하지 않는다. Moonfish의 실패는 이 실행 환경에서
원본 배포 경로가 실패한 관측이며, 탐색에서 불법 수를 낸 결과가 아니다. 후보가 시작하더라도
원본과의 엄격한 배포 동등성이 자동으로 성립하지 않는다.

## 같은 예산으로 수행한 후속 실행

압축·독립 재현의 컴파일러가 종료된 뒤 PyGone의 가용 추정치는 2,176,126,976바이트로
변했다. 이 값이 원래의 요구량과 여유분 합계 2,147,483,648바이트를 충족하여 **같은 원본
plan을 새 결과 디렉터리에서 다시 시작**했다. 원본·최소·독립 재현 파일 모두 원래 설정으로
6개 이력을 통과했다. 검사에 맞추어 예산을 낮추거나 cache를 강제로 비우지 않았다.

| 입력·역할 | 결과 | 전체 관측 시간 |
|---|---|---:|
| [PyGone 원본의 후속 실행](pygone-original-after-replay.json) | `pass`, 6/6 | 23.224초 |
| [PyGone 최소 파일](pygone-smallest.json) | `pass`, 6/6 | 20.614초 |
| [PyGone 독립 재현](pygone-replay.json) | `pass`, 6/6 | 19.340초 |
| [Moonfish 최소 파일](moonfish-smallest.json) | `pass`, 6/6 | 4.183초 |
| [Moonfish 독립 재현](moonfish-replay.json) | `pass`, 6/6 | 5.763초 |

이 시간은 시작과 정리를 포함한 해당 제한 검사의 소요 시간이며 성능 벤치마크가 아니다.
모두 10,000 ms 시계와 0 ms increment를 전달했다. Moonfish 원본의 배포 실패와 최초 PyGone
자원 차단은 삭제하거나 통과로 바꾸지 않았다. 현재 역할별 결과는 index의
`latest_observations[artifact_key][role]`에 있고, `entries`에는 총 13개 관측과 `role`·`attempt`가
있다. 최종 원본 상태는 6개 자원 차단, Moonfish 배포 실패, PyGone 제한 검사 통과다.

## Sunfish의 공식 시계와 별도 메모리 예산

[Sunfish의 추가 공식 시계 관측](sunfish-smallest-official-clock.json)은 같은 최소 파일
2,776바이트와 같은 PyPy interpreter로 수행한 자원 비교다. 앞선 1 GiB AS 제한에서는
21.721초에 전이표 삽입 중 `MemoryError`가 발생했다. 그 실패를 보존한 채 3 GiB 작업 예산과
256 MiB 여유분을 선언하고, 현재 자원 검사를 통과한 뒤 4 GiB의 child AS 제한으로 명시적으로
시작했다. 부모 limit이나 엔진의 전이표·탐색 상수는 바꾸지 않았다.

후속 검사는 같은 `1800000+3000 ms` 시계에서 `d2d4`를 51.967초에 받아 통과했으며,
시작·정리를 포함한 전체 시간은 52.290초였다. 요청한 위치는 `startpos_white` 하나이므로
6개 corpus 전체 성공으로 읽지 않는다. 이 관측은 index의 별도
`official_clock_resource_observations`에서 연결한다.

이 두 실행에서는 PATH 앞에 둔 PyPy 배포의 `python3` symlink가 해석되었다. 따라서 **같은
PyPy 환경 안의 자원 비교**로 보존한다. canonical `python3`가 CPython을 가리키는 실행과
합치지 않는다. interpreter의 해시·버전, 이전 실패 보고서 해시와 오류 요약을 기록했고, 원본
소스 행이 들어 있는 traceback은 저장소 밖에 보존했다. 특정 위치에서의 후속 성공은 모든
위치와 전체 게임에 필요한 메모리 크기를 증명하지 않는다.

## 파일을 읽는 방법

각 파일의 형식은 `nvcompact.portable-resource-evidence.v1`이다. 전체 원본 파일의 크기와
SHA-256, 검증기·선언 도구의 fingerprint, 계획과 실행 직전의 조건, 요청 예산, 실행 결과,
입력·부모 환경·부모 resource limit 보존 여부를 담는다. 엔진 코드·압축 payload·실행 파일과
호스트의 절대 경로는 포함하지 않는다. 원시 transcript와 실행 가능한 plan은 저장소 밖에
보존하며 `raw_evidence_id`로 구분한다.

`target_artifact_process_started`는 제출 파일의 프로세스가 시작했는지를 뜻한다. shell
wrapper가 컴파일 전에 종료할 수도 있으므로 체스 엔진의 탐색 시작과 같은 뜻으로 쓰지 않는다.
`configuration.threads`와 `hash_mb`는 공통 설정 객체의 기본값이다.
`preserve_engine_options: true`인 이번 실행에서는 이를 `setoption`으로 보내지 않았다.

가용 메모리는 물리 `MemAvailable`과 보이는 cgroup 상한을 모두 고려한 관측값이다. 이 버전은
cgroup file cache 중 `inactive_file`만 보수적으로 가산한다. 회수 가능한 clean active file
cache가 많으면 실행 가능한 작업을 차단할 수 있다. 관측값은 자원 예약이 아니며, 통과한 계획도
다음 시작 직전에 다시 확인한다. cache 강제 비우기, VM 설정 변경, 검사에 맞춘 예산 축소는
수행하지 않았다. 자연스러운 자원 변화 후 같은 예산으로 수행한 추가 관측은 별도 결과로 남긴다.

예산의 근거와 실행용 template은 [외부 비교 자원 계획](../../../comparisons/resource-examples/README.md),
전체 실험 범위는 [TCEC 예제 문서](../../../docs/TCEC-EXAMPLES.md)를 참고한다. 이 자료의
`pass`·`fail`·`blocked`는 제한된 로컬 실행의 결과이며 실제 TCEC 서버 인수 또는 전체 대국의
성공을 대신하지 않는다.
