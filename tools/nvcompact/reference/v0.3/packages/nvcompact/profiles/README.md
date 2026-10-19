# 로컬 프로토콜 검사 프로필

`protocol-15s.json`은 모든 엔진에 공통으로 적용하는 다음 설정이다.

```json
{"clock_ms":15000,"search_seconds":16.0}
```

입력은 `go wtime 15000 btime 15000 winc 0 binc 0`이다. 기본 `clock_grace_ms=1000`을 유지하므로 응답 deadline은 16초다. 실제 남은 시간보다 훨씬 짧은 별도 cap으로 먼저 중단하지 않도록 맞췄다. 이 1초는 로컬 스케줄링 관측 여유이며 TCEC의 시간 초과 규칙에 추가되는 시간이 아니다.

이 프로필은 TCEC 4K 필수 UCI 동작을 샘플링하기 위한 것이다. 실제 대회의 30분+3초 기력·안정성 실험을 수행한 것으로 해석하지 않는다. Hash·Threads, 초기 시작 제한과 여섯 국면·정리 조건은 `nvuci.Config`의 다른 기본값을 따른다.

도구 기본 2초 clock / 증분 0의 초기 캠페인은 `evidence/short-clock-campaign`에 보존했다. pygone은 원본이 고정 3초 항을 더해 탐색하므로 그 조건에서 실패했다. 별도 15초 clock / 5초 검사 cap에서도 timeout이 관측되어, 실제 15초가 소진됐다는 결론과 구분했다. clock과 deadline을 맞춘 최종 별도 진단에서는 원본과 최소 파일 모두 여섯 수열을 연속 통과했다. 최종 전체 캠페인도 같은 공통 프로필로 실행한다. 특정 엔진의 실패를 성공으로 처리하는 예외는 없다.

`nvenvelope.py`, `run_engines.py`, `nvreproduce.py`에 `--uci-config profiles/protocol-15s.json`을 전달한다. `nvuci.py`를 직접 호출하면 `--clock-ms 15000 --search-seconds 16`을 전달한다. 검사 결과의 실제 config와 transcript가 실행 조건의 정본이다.
