# TCEC 4K 공개 구현 전수 조사와 압축 입력 자료

기준일: 2026-10-19. 이 문서는 **어떤 엔진을 비교했는가, 원본이 무엇인가, 편집 가능한 소스가 어디까지 대응하는가**를 기록한다. 실제 NVCompact 압축 결과와 UCI 실행 결과는 별도 캠페인 결과를 기준으로 판단해야 한다.

제공된 원본의 재패킹과 편집 가능한 upstream 소스부터의 원본 재생성에 필요한 도구·버전·추가 의존성은 [빌드 요구 사항과 소스 대응 범위](BUILD-REQUIREMENTS.md)에 구분해 정리했다.

## 1. 전수 범위

공식 일반 4K I–VII의 본선·결승, ELF I–III, VII의 대체 미니파이널 보너스와 발표된 S31 명단을 확인했다. 공식 PGN 17개에서 엔진 이름과 버전을 직접 추출했다. 테스트 전용 후보와 크기 제한이 없는 보너스 상대 엔진은 모집단에 넣지 않았다. 원본 PGN URL, 날짜, SHA-256은 `ENGINE-ROSTER.json`과 `official-event-roster.json`, `official-final-roster.json`에 있다. [공식 4K 분류](https://wiki.chessdom.org/Category:TCEC_4k), [공식 TCEC 게임 저장소](https://github.com/TCEC-Chess/tcecgames), [현재 엔진 상태](https://wiki.chessdom.org/Current_Engine_Status)가 모집단의 근거다.

이 범위의 일반 4K 참가 구현은 **11개**다. we4k와 후계 STRO4K를 한 계보로 묶으면 **10개 계열**이다. ELF 제출명 LESS_STRO4K까지 세면 역사적 명칭은 12개다. 모든 계열에서 공개 소스 또는 소스가 내장된 저자 배포물을 찾았다. 이것은 모든 역사적 대회 제출 파일이나 최신 ELF 제출 파일까지 확보했다는 뜻은 아니다.

| 행사 | 일반 부문 참가 버전 |
|---|---|
| I, S23 | 4ku 1.0, ice4 9e94b82, pygone 1.5.2, sunfish 2022-12-24_classic, we4k 104th-64G |
| II, S24 | 4ku 3.0, M4sseur 1.0, STRO4K 1.0, ice4 v3, pygone 1.5.4, sunfish 2022-12-24_classic |
| III, S26 | 4ku 4.0, M4sseur 1.0, STRO4K 2.0, ice4 4, moonfish d7b5af5c, pygone 1.5.5 |
| IV, S27 | 4ku 5.0, M4sseur 1.0, STRO4K 3.0, ice4 5, molly e317a0c7b8, moonfish 4aa32a0c, pygone 1.5.5 |
| V, S28 | 4k.c 1.0, 4ku 5.1, M4sseur 1.0, STRO4K 4.0, ice4 6, molly e317a0c7b8, pygone 1.5.6 |
| VI, S29 | 4k.c 5.0, 4ku 5.1, STRO4K 5.0, c4ke 1.0, ice4 6.1, molly e317a0c7b8, pygone 1.6.5. 결승의 c4ke는 수정본 1.1 |
| VII, S30 | 4k.c 9.0, 4ku 5.1, STRO4K 5.0.1, c4ke 3.0, ice4 6.1.1, molly e317a0c7b8, pygone 2-11b142. 대체 미니파이널은 4k.c 9.15와 4ku 5.1 |

| ELF 행사 | 참가 버전 |
|---|---|
| I, S28 | 4k.c 1.10, LESS_STRO4K 4.0 |
| II, S29 | 4k.c 5.8, LESS_STRO4K 5.0 |
| III, S30 | 4k.c 9.15.1, STRO4K 6.0 |

공식 현황 문서의 S31 일반 명단은 c4ke 3.0, ice4 6.1.1, 4ku 5.1, 4k.c 9.15.1, STRO4K 6.0, molly e317a0c7b8, pygone 2-11b142다. 다음 ELF 명단도 4k.c 9.15.1과 STRO4K 6.0이며, 문서에는 이미 끝난 행사 번호와 같은 “S31 4K ELF III”라는 제목이 적혀 있다. JSON은 이 제목을 임의로 고치지 않는다. 현재 문서가 기록한 VII 우승은 c4ke, 준우승은 ice4다. [공식 현황 revision 9511](https://wiki.chessdom.org/index.php?title=Current_Engine_Status&oldid=9511)

## 2. 실제 압축 캠페인에 제공한 원본 11개

아래 크기는 실행 파일, 런처, 압축 페이로드를 모두 포함한 **단일 입력 파일 크기**다. 재빌드로 만든 기준본은 그 사실을 표시했다. 원본을 유지하는 후보도 반드시 비교에 포함해야 한다.

| 구현·공개 출처 | 제공 기준본 | 바이트 | 내부 표현 | 실제 라이선스 |
|---|---|---:|---|---|
| [ice4](https://github.com/MinusKelvin/ice4) | 공개 v6.1 `ice4-tcec` | 4087 | C++ 소스 → LZMA-alone → C++ 즉시 컴파일 | GPL-3.0 |
| [4ku](https://github.com/kz04px/4ku) | 공개 v5.1 `4ku-5.1-mini` | 4093 | C++20 소스 → LZMA-alone → G++ 즉시 컴파일 | MIT |
| [STRO4K](https://github.com/ONE-RANDOM-HUMAN/STRO4K) | 공개 v5.0 `STRO4K-tcec` | 4096 | 어셈블리 기반 ELF → x86 BCJ + raw LZMA2 → 실행 | GPL-3.0 |
| [4k.c](https://github.com/GediminasMasaitis/4k-dot-c) | 공개 v9.0 `4kc-mini` | 3932 | C 기반 자체 해제 ELF, ELF 헤더에도 코드 저장 | MIT; Crinkler 유래 부분 zlib |
| [c4ke](https://github.com/citrus610/c4ke) | 공개 v3.0 `c4ke-tcec` | 4093 | C++23 소스 → LZMA-alone → G++ 즉시 컴파일 | MIT |
| [pygone](https://github.com/scs-ben/pygone) | 저장된 `pygone2-11b142` | 4093 | Python 소스 → XZ → pypy3 | GPL-3.0-or-later |
| [sunfish](https://github.com/thomasahle/sunfish) | 2022-12-24 커밋의 classic packed 파일 | 2844 | Python 소스 → XZ → python3 -u | GPL-3.0 |
| [moonfish](https://moonfish.neocities.org/) | 저자가 공개한 현재 버전 미표기 `moonfish.sh` | 3941 | C 소스 → raw LZMA2 → cc 즉시 컴파일 | 0BSD |
| [M4sseur](https://github.com/Diazepawn/M4sseur) | 공개 1.0 소스의 upstream 파이프라인 재빌드 | 4095 | C++20 소스 → 자체 minifier → LZMA-alone → C++ 컴파일 | MIT |
| [molly](https://codeberg.org/latuernich/molly) | 정확한 대회 커밋 e317a0c7b8의 upstream 재빌드 | 4096 | Rust 소스 → syn 기반 minifier → LZMA-alone → rustc | MIT |
| [we4k](https://github.com/ONE-RANDOM-HUMAN/we4k) | 2022-12-21 소스의 변경 없는 공개 기본 프로필 재빌드 | 4079 | Zig + 어셈블리 → ELF → sstrip → XZ → 실행 | GPL-3.0 |

`available-artifacts.json`에는 파일 경로, 원본 및 페이로드 SHA-256, 런처의 정확한 문자와 길이, 해제 형식, 컴파일러 argv, 소스 아카이브, 실제 라이선스 경로가 있다. `vendor/source-manifest.json`은 전달용 경로를 프로젝트 기준 상대 경로로 기록한다.

## 3. 최신 대회 버전과의 차이

ice4는 6.1.1이 대회에 등장하지만 공개 릴리스는 6.1까지다. HEAD fabe3b1a에는 한 줄의 크래시 수정과 크기 4091이라는 저자의 커밋 기록이 있으나, 이를 임의로 6.1.1 제출 파일로 취급하지 않았다. 비교 원본은 공개 v6.1 릴리스다.

STRO4K의 공개 릴리스는 5.0까지다. 일반 VII의 5.0.1, ELF의 LESS_STRO4K 4.0·5.0과 STRO4K 6.0에 해당하는 공개 제출 파일 또는 분명한 버전 태그를 확보하지 못했다. 제공한 5.0은 외부 `xz`를 쓰는 일반 부문의 셸 포장 파일이다. 이것을 ELF 부문의 제출본으로 세면 안 된다.

4k.c 9.0은 일반 VII의 버전과 공개 릴리스가 일치하고 파일 형식도 자체 해제 ELF다. 9.15의 공개 소스는 커밋 `44072f4af03499ea5d8fa5c7dfd1ee51c8bb6782`까지 추적했지만 9.15.1 제출 파일은 확보하지 못했다. 현재 master의 더 새로운 코드를 같은 제출본이라고 주장하지 않는다.

we4k에는 공개 릴리스가 없다. 공개 역사 소스는 **4스레드·32MiB**이고 대회 명칭은 **104th-64G**다. 공개 기본 프로필을 변경 없이 빌드하여 비교 대상으로 제공했다. 이 파일을 당시 104스레드 대회 파일이라고 부르면 안 된다.

Moonfish의 올바른 저자는 zamfofex다. 공식 엔진 목록이 연결한 저자 홈페이지의 소스 내장 파일을 확보했다. 동명의 Python 엔진이나 Stockfish 파생 저장소를 사용하지 않았다. 현재 파일에는 버전 식별자가 없고 이전 `git.sr.ht/~zamfofex/moonfish` 저장소는 404다. 마지막 대회 버전 4aa32a0c와 현재 다운로드의 일치는 미확인이다. Molly 역시 동명의 무관한 GitHub 저장소 대신 [공식 저자 문답](https://wiki.chessdom.org/Molly_questionnaire_20251015)이 연결한 Codeberg 저장소를 사용했다.

## 4. 대응 소스 확인에서 해결한 두 가지 혼동

**pygone의 대회 표기에는 실제 커밋 접두사의 f가 빠져 있다.** `2-11b142`만 찾으면 소스 커밋을 찾을 수 없지만 실제 이력에는 `11bf1426bc491753b66e945692c5ee4a8d510e45`가 있다. 이 커밋의 `dist/pygone`과 나중의 `historical/pygone2-11b142`는 4093바이트 전체가 일치한다. SHA-256은 `f44c111d821c5bffb9117154dcffbfb0e83ab41b35e174b084a9bb5000ee1768`이다. 따라서 현재 master를 대응 소스라고 대신 제공하지 않고, 정확한 커밋의 편집 가능한 모듈과 축소·빌드 스크립트를 제공한다. [정확한 커밋의 원본 배포 파일](https://raw.githubusercontent.com/scs-ben/pygone/11bf1426bc491753b66e945692c5ee4a8d510e45/dist/pygone)

**Sunfish의 대응 입력은 `sunfish.py`가 아니라 `sunfish_uci.py`다.** 2022-12-24 커밋의 이 소스를 upstream `pack.sh`와 같은 옵션으로 python-minifier 2.7.0에 넣었더니 원본 페이로드 5837바이트를 정확하게 재현했다. 두 SHA-256은 모두 `f1a676e55763635a4ba517e7439249e2f1b15da818e83369b50f6b705178f78f`이다. 실행 조건은 CPython 3.11.17, python-minifier 2.7.0, 당시 CLI가 필요로 하는 setuptools 65.6.3이다. 설치된 Python 3.12가 옛 minifier의 지원 범위 밖이어서 요구 조건을 무시하지 않고 호환 인터프리터를 따로 사용했다. [정확한 편집 소스](https://github.com/thomasahle/sunfish/blob/ccecec26626b858a60d48cf715ebbdd603ee6f85/sunfish_uci.py)

## 5. 오프라인 소스 전달

`vendor/`에는 11개 구현의 소스 아카이브와 라이선스가 있다. 아카이브 합계는 1,706,645바이트다. 배포 실행 파일과 외부 컴파일러 설치물을 중복 포함하지 않았다. 별도 NNUE 모델, pickle 가중치, 로고, 기생성 배포 파일을 제외했고, 보존한 각 소스 멤버가 공개 upstream의 원래 바이트와 동일한지 SHA-256을 기록했다. 제외 항목도 manifest에 남겼다. Sunfish의 대체 NNUE 프로필 소스는 있어도 그 가중치는 이 classic 엔진의 빌드 입력이 아니다.

라이선스 파일은 원본 바이트를 그대로 복사했다. Moonfish는 저자 홈페이지에 라이선스가 있으므로 원래 홈페이지 응답과 해당 0BSD 문구를 함께 보존한다. ice4의 실제 라이선스는 **GPL-3.0**이며 MIT로 기재하면 안 된다. 4k.c의 compressor/loader에는 별도 `THIRD_PARTY_LICENSES`를 동봉했다.

검증 수준은 구분한다. Sunfish는 편집 가능한 소스에서 원본 페이로드를 재현했다. we4k는 같은 공개 프로필의 네이티브 페이로드를 두 번 빌드해 바이트 일치를 확인했다. pygone은 정확한 커밋에 편집 소스와 동일한 원본 배포 파일이 함께 존재한다. Molly와 M4sseur는 원래 빌드 파이프라인으로 기준본을 만들었다. 나머지 공개 릴리스들은 일치하는 태그 소스와 저자 릴리스 파일을 보존했지만 전체 네이티브 빌드를 독립적으로 재현했다고 주장하지 않는다.

## 6. 실제 UCI 검증에 필요한 실행 조건

압축·해제의 정확성과 엔진 실행 가능성은 서로 다른 결과다. 원래 TCEC 프로필을 임의로 축소한 뒤 원본을 검증했다고 표시해서는 안 된다.

| 기준본 | 확인한 실행 조건 |
|---|---|
| M4sseur | minifier가 103스레드와 64GiB TT를 넣는다. 시작 시 테이블을 초기화한다. |
| molly | 101스레드, TTEntry 2^32개. 현재 컴파일 결과의 실제 할당 상수는 `0x1800000000`, 즉 96GiB다. UCI 입력 전에 할당한다. |
| STRO4K-tcec | ELF LOAD의 `p_memsz`는 `0x427c403000`으로 약 266GiB의 가상 주소 공간을 요구한다. 물리 메모리 사용량과 같다고 단정하지 않는다. |
| pygone | PyPy3가 필요하고 `[None]*2**27`은 64비트 포인터 저장만 최소 1GiB다. |
| moonfish | `sysconf(_SC_NPROCESSORS_ONLN)`으로 스레드 수를 정한다. 컨테이너 CPU 할당량과 온라인 코어 수가 다를 수 있다. |
| we4k 공개 기준본 | 4스레드·32MiB, AVX2/BMI2가 필요하다. |
| 4k.c | ELF 헤더에 실제 명령을 배치한 자체 압축 파일이다. 일반 ELF section stripping을 무조건 적용하면 안 된다. |

이 조사 작업에서는 원본 엔진을 실행하지 않았고, Molly·M4sseur·Moonfish는 컴파일까지만 확인했다. 실행 판정은 자원 제한이 있는 별도 캠페인이 맡는다. 컴파일 로그와 소스 대응 증거의 경로는 manifest에 연결했다.

## 7. 규칙에 관한 판정 경계

공식 규칙은 단일 파일 4096바이트, 60초 이내 시작, 파일 정리, 최소 UCI 부분집합을 요구한다. 일반 4K의 외부 프로그램 허용 목록은 `bzip2`, `bash`, `c++`, `cargo`, `cc`, `clang`, `chmod`, `gzip`, `lzma`, `mktemp`, `perl`, `python`, `python3`, `pypy3`, `rustc`, `sh`, `sleep`, `tail`, `xz`다. ELF 부문은 외부 프로그램 실행을 허용하지 않고 자체 ELF와 명시된 시스템 라이브러리를 사용한다. [공식 규칙 revision 7853](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853)

공식 예제 자체가 목록에 없는 `rm`을 사용하고, 공개 엔진에는 `g++`, `unxz` 같은 이름도 있다. 목록 밖 명령은 운영진의 재량으로 추가될 수 있다는 조항이 있으므로, “공개 원본에서 사용됨”, “문서의 명시 목록에 있음”, “운영진의 해당 환경 허용이 확인됨”을 한 가지 판정으로 합치지 않는다. 원본의 UCI 동작 확인만으로 대회 참가 승인을 대신할 수 없다.

## 8. 압축기 설계에 직접 반영할 관찰

이미 여러 원본이 상당한 후보 탐색을 한다. STRO4K의 build4krs는 세 링커와 LZMA2의 lc/lp/pb/mf 조합을 비교한다. M4sseur는 LZMA1 설정 2700개를 비교했고, Molly는 match finder와 nice 길이 1360개를 비교했다. we4k의 autovndh도 필터 순서와 LZMA 설정을 탐색한다. 따라서 단순히 “LZMA -9를 썼다”는 설명만으로 개선을 입증하기 어렵다. 실제 제출 파일 전체, 해제기 선택, 런처 길이, 컴파일 옵션과 의미 보존을 함께 비교해야 한다. 이 근거는 동봉된 각 upstream 빌드 스크립트다.

추가 후보가 모두 커졌다면 원본을 채택해 크기 비증가를 보장할 수 있다. 그 경우는 “더 압축했다”가 아니라 “원본이 포트폴리오의 최소값이었다”로 기록한다. 자체 ELF에서 외부 해제기를 사용하는 셸로 바꾸는 후보는 일반 부문에서만 비교할 수 있다. 파일의 실제 분류와 실행 조건을 보존해야 비교 결과가 다음 구현 에이전트에게도 유효하다.
