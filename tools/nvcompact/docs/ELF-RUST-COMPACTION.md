# ELF / Rust 추가 압축 조사와 실제 비교

2026-10-19, NVCompact 0.4.0 후속 작업. 아래의 큰 절감은 **직접 작성한 초기화 데이터
예제**에서 측정했다. 외부 TCEC 4k.c v8/v9에 같은 절감을 얻었다는 의미가 아니다.
외부 엔진의 소스·압축 스트림·실행 파일은 저장소에 포함하지 않는다.

측정·재현·실패 기록: [elf-rust-compaction.json](../evidence/0.5/elf-rust-compaction.json).
`evidence/0.5`는 후속 연구 묶음이며 현재 npm/Cargo 패키지 버전은 0.4.0이다.
추가 Rust 옵션과 도입 경계는 [RUST-SIZE-OPTIONS.md](RUST-SIZE-OPTIONS.md)에 정리한다.

## 1. 추가 구현: 파일의 마지막 0들을 ELF zero-fill로 표현

ELF `PT_LOAD`의 `p_filesz`는 파일에서 가져올 바이트 수, `p_memsz`는 메모리에서
차지할 바이트 수다. `p_memsz > p_filesz`이면 나머지 메모리는 0으로 초기화한다.
이는 일반적인 `.bss`를 적재하는 형식의 일부다.
[ELF gABI 프로그램 적재 규칙](https://gabi.xinuos.com/elf/07-pheader.html)

이를 이용해 **초기화된 writable 데이터의 끝에 이미 들어 있는 0들**을 파일에서
생략할 수 있다. 단순히 파일을 자르는 것으로 끝내지 않고, 해당 segment의
`p_filesz`를 정확히 줄인다. `p_memsz`, 가상 주소, 진입점, 권한, 나머지 프로그램
바이트는 보존한다. 초기화 값을 0으로 만드는 실행 코드를 삽입하지 않는다.

예를 들어 배열이 `[17, 0, ..., 0]`으로 초기화되면 첫 17 때문에 컴파일러가 전체
배열을 파일의 `.data`에 넣을 수 있다. 파일의 마지막 데이터라면 첫 바이트만
파일에서 가져오고 나머지를 적재 시 zero-fill로 만들 수 있다. 배열의 전체 크기와
각 주소의 초기값은 그대로다. 일반적인 전부 0인 `.bss`는 이미 파일에 저장되지
않으므로 이 변환의 추가 이득이 없다.

### 자동 적용 조건

새 선언은 `allow_load_zero_tail: true`이며, 기존
`allow_section_header_removal: true`도 필요하다. native manifest에서는 선택한
`link_profiles` 안에, 이미 만들어진 ELF의 envelope manifest에서는 최상위에 둔다.
기본값은 false다. 원본과 기존 sectionless 후보를 항상 보존한다.

현재 구현은 다음 범위로 제한한다.

- Linux x86-64의 보통 ELF64 little-endian `ET_EXEC` 파일.
- ELF/program-header가 겹치지 않고 모든 파일·가상 범위가 유효한 형식.
- 마지막 `PT_LOAD`가 읽기/쓰기 가능하고 실행 권한은 없는 RW segment.
- 4096바이트 페이지 기준으로 파일과 가상 주소의 나머지가 같고,
  load segment가 가상 주소 순서로 배열되어 가상 페이지를 공유하지 않는 형식.
- 생략할 부분은 최종 파일의 연속된 0 접미부이며, 다른 program segment의 파일
  범위와 겹치지 않는다. header 전체와 최소 한 바이트의 초기화 prefix를 유지한다.
- interpreter, dynamic linking, TLS, note와 그 밖의 미지원 program segment가 없다.
- 자기 파일, ELF/section/program header, `AT_PHDR`로 접근하는 header 값과 수정된
  메타데이터를 프로그램·배포 관측 결과로 사용하지 않는다.

원래 파일과 새 파일의 ELF header는 실제로 다르다. 메모리에 매핑된 header까지
바이트가 같다는 뜻이 아니다. 관측 계약은 이 변경을 명시적으로 제외해야 한다.
ELF header 필드에 실행 코드를 겹쳐 놓은 파일에는 적용하지 않는다.

Linux의 loader는 파일 내용 뒤의 부분 페이지를 직접 0으로 채우고 이후 메모리를
할당한다. 따라서 writable 여부와 virtual-page 공유는 실제 적재 동작의 조건이다.
이번 구현은 `p_filesz=0`으로 바꿀 때의 별도 적재 경로도 피한다.
[Linux ELF loader 구현](https://github.com/torvalds/linux/blob/master/fs/binfmt_elf.c)

입력의 구조 확인만으로 전체 의미 보존을 증명하지 않는다. 파일 배포 계약을
선언하고 실제 최종 artifact를 실행하여 확인해야 한다. 새 구현은 변환 후보와
측정 결과를 만드는 역할을 맡고, 기존 native verifier/replay 경로가 실제 검사와
선택을 수행한다.

## 2. C와 Rust로 작성한 실제 예제

[zero-tail 자체 예제](../examples/zero-tail/README.md)는 8192개의 writable byte를
17과 나머지 0으로 초기화한다. C와 Rust 구현이 같은 C ABI를 제공하고, 공통 driver가
입력 index를 검사한 뒤 이전 값을 반환하고 새 값을 저장한다. Rust 함수의 호출자
조건은 `unsafe extern "C"`와 문서에 명시했다.

독립 Node 검증기는 ELF header에서 기대값을 계산하지 않는다. 별도의 byte 배열
모델로 전체 8192주소, 두 방향의 상태 변경, 페이지 경계, 하위 8비트 변환, 반복
읽기, EOF, 불완전한 record와 범위를 벗어난 index를 검사한다. 한 최종 artifact마다
16,389개의 유효 record와 11개 case를 실제로 실행했다.

### GNU ld 빌드/압축 포트폴리오

컴파일러는 GCC 13.3.0, Rust 1.99.1을 사용했다. 표의 각 행에서 Rust LTO `off`,
`thin`, `fat`은 같은 native SHA-256을 만들었다. C에는 Rust LTO 설정을 적용하지
않았다. 이 예제는 단일 Rust object이므로 여러 crate를 통합하는 LTO의 효과를
대표하지 않는다.

| C / Rust 최적화 | 구현 | 링크 ELF | 기존 sectionless ELF | 새 zero-tail ELF | 새 기능 이전의 최소 전체 포장 파일 |
| --- | --- | ---: | ---: | ---: | ---: |
| `-Os` / `s` | C | 8,952 B | 8,672 B | **481 B** | 915 B |
| `-Os` / `s` | Rust | 8,928 B | 8,642 B | **451 B** | 906 B |
| `-Oz` / `z` | C | 8,920 B | 8,640 B | **449 B** | 909 B |
| `-Oz` / `z` | Rust | 8,912 B | 8,632 B | **441 B** | 903 B |
| `-O2` / `2` | C | 8,984 B | 8,704 B | **513 B** | 928 B |
| `-O2` / `2` | Rust | 8,968 B | 8,689 B | **498 B** | 927 B |
| `-O3` / `3` | C | 8,984 B | 8,704 B | **513 B** | 928 B |
| `-O3` / `3` | Rust | 8,968 B | 8,689 B | **498 B** | 927 B |

각 경우에서 zero-tail 변환 자체는 **8191바이트**를 없앴다. 예제의 초기화 배열에
있는 0의 개수에 해당한다. Rust와 C의 8~30바이트 차이는 각 컴파일러가 만든 명령과
정렬을 포함한 해당 빌드 결과다. 언어 일반의 우열로 해석하지 않는다.

총 **24개 링크 조합과 360개 최종 artifact**를 실제로 검사했다. 세 배포 방식
`original / no-section-headers / no-section-headers-zero-tail`마다 `raw`, `gzip-9`,
`xz-6`, `xz-bcj-6`, `lzma-6`을 비교했다. 모두 독립 oracle를 통과했다.

새 기능 이전에 이 포트폴리오에서 가장 작았던 완성 파일은 **903바이트**였다.
새 기능을 포함하면 **441바이트의 raw ELF**가 선택됐다. 이 수치는 header를 뺀
압축 payload가 아니다. wrapper 후보에는 597바이트의 loader를 포함했다.
새 raw 파일보다 작은 compressed payload가 있어도 loader를 더한 완성 파일은
더 컸으므로 선택하지 않았다. 이 비교는 여기서 선언한 5개 코덱에 대한 것이며,
일반 envelope 전체의 세밀한 codec 탐색 결과라고 확대하지 않는다.

독립 `reproduce --verify` 호출에서 선택한 441바이트 파일을 다시 빌드했고, SHA-256
`f0f8ffe01305587b35e52c0984cfcb103b60d476a2750d104032819f620a5ce7`과 실제 출력이
모두 일치했다. 디버그 빌드의 도구 실행 시간으로 release 성능 향상을 주장하지 않는다.

### ELF-only와 GNU ld / LLD 비교

별도 manifest에서 `category: "4k-elf"`, `codecs: ["raw"]`로 제한한 뒤 C/Rust 각각을
GNU ld와 Rust 배포판의 LLD로 링크했다. 실제 외부 decoder를 사용하는 후보는
ELF-only 선택에 들어가지 않았다.

| 링커 | C zero-tail ELF | Rust zero-tail ELF | 실행 검사 |
| --- | ---: | ---: | --- |
| GNU ld | 449 B | **441 B** | 각 original/sectionless/zero-tail 통과 |
| Rust 배포판 LLD | 449 B | **441 B** | 각 original/sectionless/zero-tail 통과 |

총 4개 링크 조합과 12개 artifact를 실제 검사했다. 8KiB가 넘는 원본과 sectionless
파일은 동작 검사에 통과해도 `over_size_limit`으로 남겼고, 4096바이트 이내인
zero-tail 후보만 크기 조건을 만족했다. 선택한 파일은 추가 독립 replay에서도
바이트와 oracle를 통과했다. 이 fixture에는 UCI가 없으므로 TCEC 출전 엔진으로
취급하지 않는다.

LLD가 GNU ld보다 작아지는 이득은 이 입력에서는 없었다. 따라서 링커를 무조건
교체하는 규약을 만들지 않는다. [LLD linker script 정책](https://lld.llvm.org/ELF/linker_script.html)

## 3. 실제 외부 TCEC ELF에서는 추가 절감하지 못했다

| 공개 입력 | 기존 최소 | 이번 최소 | 추가 절감 | 원인 |
| --- | ---: | ---: | ---: | --- |
| 4k.c v8.0 | 4,042 B | **4,042 B** | 0 B | 전체 파일이 단일 RWX load segment, 끝에 0 없음, header에 코드 중첩 |
| 4k.c v9.0 | 3,932 B | **3,932 B** | 0 B | 같은 형태이며 끝에 0 없음, 일반 header 제거의 전제 불성립 |

두 파일은 program header가 offset 56에서 시작해 64바이트 ELF header와 겹친다.
진입점은 최초 load segment의 offset 8이다. 보통 ELF에서 형식 정보라고 생각하는
영역이 이미 실행 코드다. `p_filesz`는 파일 끝까지 덮고 trailing zero도 0개이므로
이번 변환이 없앨 데이터가 없다. `strip`이나 임의의 header 재작성은 원래 코드를
삭제·변경할 수 있다.

새 실행 파일로 두 입력을 다시 비교하고 별도 byte replay를 수행했다. 크기와
SHA-256은 원본과 같았다. v8의 과거 UCI 관측은 [기존 기록](../evidence/0.4/elf-comparison.json)에
유지하며, 이번에 대국 실행을 반복하지 않았다. v9의 22GiB `p_memsz`는 가상 범위로
기록하고, 이미 확인한 호스트의 엔진 진입 전 `ENOMEM` 때문에 다시 실행하지 않았다.

실제 외부 입력의 0바이트 절감은 공개한다. 초기화 배열 예제의 8191바이트 절감을
외부 엔진의 결과로 옮기지 않는다. 이 결과로 ELF가 더 작아질 가능성이 전혀 없다고
결론내리지도 않는다. 코드·데이터 재배치나 내장 decoder 같은 다음 방법은 새 계약과
더 큰 구현을 필요로 한다.

## 4. 추가로 조사한 압축 지점과 적용 경계

| 지점 | 작은 파일에 유리할 수 있는 이유 | 계약·검사·우선순위 |
| --- | --- | --- |
| 함수·데이터별 section과 GC | 도달하지 않는 코드를 제거 | entry, export, constructor, registration section의 root를 보존. `KEEP`, `SHF_GNU_RETAIN`의 의미를 확인 |
| ICF | 동일한 기계 코드 section을 공유 | 함수 주소의 동일성, 상수 identity와 address-significance metadata가 관측되는지 확인. `all`을 자동 의미 보존 변환으로 취급하지 않음 |
| 링크 순서·section 순서 | alignment 구멍과 branch displacement, 압축용 반복 패턴이 변함 | 원래 순서를 유지한 후보와 함께 비교. 크기와 실제 전체 포장을 모두 측정 |
| RX/RW와 읽기 전용 segment 배치 | page padding과 program-header 수를 줄일 수 있음 | 가상 페이지 권한과 파일 residue, loader 동작을 확인. 실행·쓰기 권한을 조용히 넓히지 않음 |
| non-alloc section과 symbol strip | 실행에 쓰지 않는 정보를 제거 | self-file, symbol lookup, debug/unwind와 signing 관측을 계약에서 확인 |
| `.data`의 말단 0 | 적재 시 zero-fill로 대체 | 이번 구현. 이미 NOBITS인 `.bss`에는 추가 이득 없음 |
| relocation 감소·상대 offset | 64비트 pointer table과 relocation overhead를 줄임 | 소비자가 offset을 해석하게 바꾸는 설계 후보. 임의의 post-link integer 치환은 하지 않음 |
| 상수·문자열·테이블 재표현 | 비트폭, 반복, 대칭과 규칙을 활용 | 복호화 코드와 실행 비용을 포함. TT/search 자료를 매 node마다 비싸게 복원하면 이득이 사라짐 |
| Rust monomorphization과 inlining | 중복 코드와 call-site 팽창을 제어 | generic/trait 사용량, dynamic dispatch 비용, 코드 공유 효과를 실제 측정. 전면 금지 규약을 만들지 않음 |
| Rust `s/z/2/3`, LTO, CGU | machine-code 형태와 함수 경계를 변경 | 대상마다 후보로 비교. `z`가 항상 가장 작다는 보장은 없음 |
| Rust `no_std`, panic·unwind 정책 | 표준 runtime과 진단·unwind 데이터를 줄일 수 있음 | allocator, cleanup, TLS, thread 시작, 외부 ABI와 실패 시 동작을 별도로 설계. 자동 표기 압축으로 분류하지 않음 |
| 내장 native decoder | 외부 도구 없는 ELF에서도 압축 표현을 실행할 가능성 | decoder·ELF header·mapping/relocation·초기화 비용까지 제출 파일에 포함. 아직 구현한 기능으로 보고하지 않음 |

GNU ld의 GC는 symbol과 relocation의 도달 관계를 사용하며 공유 라이브러리의 외부
가시성 등도 고려한다. relocation이 없는 단순한 주소 계산만으로 참조하는 테이블과
등록 코드는 개발자가 root를 명확히 해야 한다.
[GNU ld 옵션 문서](https://sourceware.org/binutils/docs/ld/Options.html)

LLVM의 safe ICF는 address-significance 정보를 이용해 함수 주소를 구별해야 하는
경우를 보존하려고 한다. object의 metadata와 compiler/linker 조합에 의존하는 기능이며,
일부러 주소 identity를 무시하는 `--icf=all`과 같은 규약이 아니다. 이 프로젝트의
독립 출력 계약이 필요한 이유다.
[LLVM ICF 설계](https://lists.llvm.org/pipermail/llvm-dev/2018-May/123514.html),
[LLVM 구현](https://github.com/llvm/llvm-project/blob/main/lld/ELF/InputFiles.cpp)

Rust 공식 문서도 최적화 수준의 크기·속도 결과가 예상과 다를 수 있으므로 실제
비교를 권장한다. codegen-unit 수는 compiler의 병렬성과 최적화 범위 모두에 영향을
준다. 이번 단일 object 예제는 CGU를 1로 고정했고 여러 CGU의 성능·크기 개선을
측정했다고 주장하지 않는다.
[Cargo profiles](https://doc.rust-lang.org/cargo/reference/profiles.html),
[rustc codegen options](https://doc.rust-lang.org/rustc/codegen-options/index.html)

압축기 자체에 엔진의 4096바이트 제한을 적용하지 않는다. 이 문서의 `no_std`, 작은
link script, 실패 처리와 runtime 제한은 **특정 산출물 프로필**이다. NVCompact의
작업 규약이나 Rove4k 모든 설계에 대한 금지가 아니다.

## 5. 실패를 수정한 방식과 검증 범위

초기 Node `spawnSync` 검증은 모든 응답을 받았어도 EOF가 전달되지 않아 timeout으로
끝났다. 동일한 입력을 Python subprocess와 비동기 Node spawn으로 실행하면 종료했다.
검사 시간을 늘리지 않고 verifier가 명시적으로 `stdin.end(input)`를 호출하는 방식으로
수정했다. 원래의 입력 영역·기대값·3초 한도는 유지했다.

초기 linker script는 미지원 GOT, relocation, initializer와 TLS section을 한 출력
section에 모아 크기 0을 요구했다. GNU ld는 허용했지만 LLD는 빈 내부 section도
서로 다른 타입을 합칠 수 없다고 거절했다. section을 **타입별로 분리**하고 동일한
크기 0 ASSERT를 유지했다. `.shstrtab`도 nonloaded metadata로 명시했다.
`--orphan-handling=error`나 linker 진단을 완화하지 않았다.

이후 정본 Rust 함수에 호출자 조건을 `unsafe`로 명시하고 양 링커용 script를 수정한
뒤, 24개 native를 다시 전부 빌드했다. 이전 matrix의 native SHA-256과 **24/24 동일**했다.
그래서 해당 GNU 입력의 기존 360개 artifact 동작 검사는 같은 바이트에 대한 근거로
재사용했다. 수정한 script의 LLD 결과는 별도로 실제 실행했다. 원래 실패와 원인 수정,
재사용 범위는 evidence에 함께 남겼다.

구현에 필요한 검사는 기존 test suite에 zero-tail의 독립 적재 모델과 경계 반례를
더해 수행했다. readonly/RWX final segment, shared virtual page, 다른 segment의
suffix 관측, dynamic segment, overflow와 truncation을 거절하는 것을 확인했다.
33개 unit과 9개 packing 검사가 통과했고, 마지막 manifest boolean 검사 수정 뒤
packing 검사를 다시 통과했다. 새로운 테스트 수나 영구 실행 framework를 규약으로
만들지 않았다.

최종 release 빌드가 들어간 `nvcompact@0.4.0` tarball도 별도 consumer에 실제로
설치했다. 설치된 명령으로 C/Rust 두 조합의 `z`/raw ELF-only 캠페인과 독립 replay를
실행해 같은 441바이트·SHA-256·oracle 성공을 확인했다. 이는 개발용 debug 실행에만
새 기능이 존재하는 문제를 확인하기 위한 통합 검사다.
[실제 패키지 설치 근거](../evidence/0.5/release-preparation.json).
