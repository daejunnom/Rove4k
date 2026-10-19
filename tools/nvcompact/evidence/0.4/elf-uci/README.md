# 공개 4k.c ELF의 실제 UCI 관측

검사 대상은 공식 공개 release **4k.c v8.0 `4kc-mini`**다. 전체 4,042바이트의 SHA-256은
`6eb03195b277f42ece9488c42c1e459791ffcbf0dc197bdfa700dd9574715ace`이다.
공개 출처와 release commit은 [ELF 비교 manifest](../../../comparisons/elf/4k.c-v8.0.json)에
기록했다. 최신 대회 비공개 제출 파일과 동일하다는 주장은 하지 않는다.

| 관측 | 결과와 범위 |
|---|---|
| [짧은 시계의 6개 이력](4k.c-v8.0-short-clock.json) | 갱신된 debug 검증기로 `2000+0 ms`에서 백·흑 시작, 캐슬링, 앙파상, 미들게임, 승격 이력을 모두 통과 |
| [공식 시계의 시작 위치 1개](4k.c-v8.0-official-clock-one-case.json) | 최종 release 검증기로 `1800000+3000 ms`를 전달하고 `d2d4`를 62.155초에 받음. 6개 corpus 중 1개만 요청하고 완료 |
| [앞선 75초 관측의 정정](earlier-observation-classification.json) | 전달한 1,800초보다 검증기 관측 예산이 먼저 끝난 결과를 `incomplete`로 정정. 원시 결과는 보존 |

공식 시계 실험의 검증기 SHA-256은
`08a4b493b19382a6e8de46cdb50465053e5b6c850a304bb9c2fed034cc21357e`다. 최종 release로
원본·선택 파일·재현 파일에 대해 각각 수행한 짧은 시계 검사는 상위
[ELF 비교 결과](../elf-comparison.json)에 별도로 기록한다.

모든 관측은 원래 engine option을 보존했다. 기록한 통과 범위에는 handshake, 허용 명령에 대한
기본 응답, 해당 위치의 합법 수와 정상 종료·소유 임시 디렉터리 정리가 포함된다. cozy-chess는
개발 검증기의 독립 합법성 oracle이며 제출 파일에 링크하지 않았다. 캐슬링과 앙파상 이력은
`position startpos moves ...`로 전달한다. 전체 게임, 모든 UCI 선택 확장, 실제 대회 서버와 같은
하드웨어·실행 환경의 인수를 완료한 결과는 아니다.

검증기의 관측 예산이 실제 전달한 시계보다 먼저 끝나면 엔진의 시간패로 판정하지 않는다.
공통 UCI 로직에서 `probe_budget`과 corpus coverage를 분리하여 이를 처리했으며, 해당 엔진만
예외 처리하지 않았다. 앞선 실패 표기는 원시 기록과 정정 파일을 함께 읽어야 한다.
