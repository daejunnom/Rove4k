# 같은 C ABI를 구현하는 C/Rust 후보 예제

이 예제는 체스 엔진에서 쓰일 법한 작은 정수 커널 두 개를 서로 교체하여 **완성된 실행 파일**을 비교하는 입력이다. 체스 엔진, UCI 구현, 기력 측정 또는 모든 입력에 대한 동등성 증명은 아니다. 프로젝트 최상위의 후보 탐색 도구로 전체 조합을 비교하거나, 아래 명령으로 특정 조합만 직접 빌드할 수 있다.

## 교체 지점과 의미

| 역할 | C 후보 1 | C 후보 2 | Rust 후보 | 공통 심볼 |
|---|---|---|---|---|
| 64비트 비트 수 | `popcount_kernighan.c` | `popcount_swar.c` | `popcount_rust.rs` | `uint32_t nv_popcount64(uint64_t)` |
| 중심 선호 점수 | `square_arithmetic.c` | `square_table.c` | `square_rust.rs` | `int32_t nv_square_bonus(uint32_t)` |

각 후보 실행 파일에는 **각 역할에서 정확히 한 객체**를 넣는다. 같은 심볼을 가진 대안을 전부 링크한 뒤 weak 심볼이나 링크 순서로 우연히 하나를 고르는 방식은 쓰지 않는다. 따라서 두 역할 각각 세 후보인 이 예제에는 아홉 조합이 있다. C/C, C/Rust, Rust/C, Rust/Rust 조합을 모두 포함한다.

`nv_popcount64`는 전체 `uint64_t` 영역의 1비트 수를 0~64로 반환한다. SWAR의 unsigned 곱셈은 의도적으로 modulo 2^64이다. `nv_square_bonus`는 0~63의 square를 받고, `square = rank * 8 + file`로 해석한다. 네 중앙 칸까지의 최소 Manhattan 거리를 d라고 할 때 점수는 `6 - 2*d`, 범위는 -6~6이다. 이 함수의 유효 입력은 64개 모두 검사한다. 다른 입력을 이 내부 함수에 직접 전달하는 동작은 계약 범위 밖이며 공통 driver가 먼저 거부한다.

두 함수에는 포인터, 소유권 이전, mutable 전역 상태, 할당, 예외 또는 unwinding이 없다. Rust는 edition 2021, `no_std`, 명시적인 `extern "C"`, native object 출력을 사용한다. Rust의 일반 ABI나 Rust 객체 레이아웃을 C에서 추정하지 않는다. 두 컴파일러는 동일한 target ABI와 호환되는 ISA를 사용해야 한다. 이 예제는 GCC와 Rust LLVM 사이의 교차 LTO를 요구하지 않는다. 다른 계약의 함수에 적용할 때는 호출 규약 외에도 aliasing, 수명, 정수 overflow, floating point, 예외, TLS와 초기화를 새로 확인해야 한다.

## 실행 파일의 binary protocol

stdin은 반복되는 **16바이트 little-endian** 레코드다.

| 오프셋 | 값 |
|---|---|
| 0~7 | unsigned 64비트 bitboard |
| 8~11 | unsigned 32비트 square, 0~63 |
| 12~15 | unsigned 32비트 reserved, 반드시 0 |

유효한 레코드마다 stdout에 **8바이트 little-endian** 결과를 쓴다. 첫 4바이트는 unsigned popcount이고 다음 4바이트는 signed 32비트 점수다. C driver는 음수 점수를 unsigned로 변환하여 modulo 2^32로 직렬화한다. 구조체 padding이나 host endianness는 wire 형식에 들어가지 않는다.

정상 EOF와 빈 입력은 exit 0이다. 유효하지 않거나 잘린 레코드는 exit 2이고 그 전에 완성된 정상 레코드의 결과만 출력한다. 감지된 I/O 오류는 exit 3이다. 비교는 정상적인 byte stream I/O 환경에서 수행한다. stderr의 진단 문구나 실제 실행 시간은 이 정수 출력 계약에 포함하지 않는다. 입력이 사용 가능한 순서, 상태 없는 두 커널의 결과와 stdout 순서는 동일하다.

## 두 링크 프로필

`driver_hosted.c`와 `linker/hosted.ld`는 보통의 C runtime을 이용한다. GNU ld의 `INSERT AFTER .text`로 default script를 보완하므로 CRT, 동적 loader, unwind, TLS, 생성자 section을 일괄 삭제하지 않는다. `-ffunction-sections`로 분리된 두 커널을 작은 별도 출력 section에 배치한다. 이 배치가 모든 프로그램의 크기나 속도를 개선한다는 보장은 없다.

`driver_linux_x86_64.c`, `start_linux_x86_64.S`, `linker/linux-x86_64-compact.ld`는 **Linux x86-64 전용**의 제한된 프로필이다. 기본 syscall로 읽기·쓰기·종료를 수행하고, C ABI 호출 전에 stack을 정렬한다. libc, allocator, dynamic relocation, GOT/PLT, writable 전역, 생성자, TLS와 unwind는 사용하지 않는다. RX image segment와 RW non-executable stack을 명시한다. ELF header와 program header도 image에 포함한다.

compact script의 `.eh_frame` 등 제거는 이 no-unwind 프로필에 한정한다. 이것을 일반 C/Rust 프로그램용 script로 복사하지 않는다. GNU ld가 합성하는 빈 GOT/PLT/relocation section은 명시적으로 배치하고 크기가 0인지 확인한다. 실제 내용이 필요하면 링크에 실패한다. `--orphan-handling=error`로 알지 못하는 section을 숨기지 않는다. 새로운 대상에서 실패하면 해당 section과 런타임의 필요성을 분석하여 올바른 프로필을 수정해야 한다.

## 특정 C/Rust 조합을 직접 빌드하는 예시

다음은 Rove4k의 `tools/nvcompact/` 디렉터리에서 실행한다. GNU C compiler/binutils와 host ABI에 맞는 `rustc`가 PATH에 있어야 한다. Cargo나 외부 crate는 사용하지 않는다. 대상은 Linux x86-64이며 compiler 최적화 옵션은 비교 가능한 설정의 한 예시다.

```sh
nv_example_out="$(mktemp -d)"
cc -std=c11 -Os -ffunction-sections -fdata-sections -fno-ident \
  -fno-stack-protector -fno-asynchronous-unwind-tables -fno-unwind-tables \
  -c examples/mixed/popcount_kernighan.c -o "$nv_example_out/pop.o"
rustc --edition=2021 --crate-type=lib --emit=obj \
  -C panic=abort -C opt-level=z -C relocation-model=static \
  -C force-unwind-tables=no -C codegen-units=1 \
  examples/mixed/square_rust.rs -o "$nv_example_out/square.o"
cc -std=c11 -Os -ffunction-sections -fdata-sections -fno-ident \
  -fno-stack-protector -fno-asynchronous-unwind-tables -fno-unwind-tables \
  -c examples/mixed/driver_hosted.c -o "$nv_example_out/driver.o"
cc "$nv_example_out/driver.o" "$nv_example_out/pop.o" \
  "$nv_example_out/square.o" \
  -Wl,--gc-sections,--build-id=none,-s,-T,linker/hosted.ld \
  -o "$nv_example_out/hosted"
python3 examples/mixed/verifier.py --binary "$nv_example_out/hosted"
```

같은 두 kernel object를 사용하는 compact 프로필:

```sh
cc -std=c11 -Os -ffunction-sections -fdata-sections -fno-ident \
  -fno-stack-protector -fno-asynchronous-unwind-tables -fno-unwind-tables \
  -ffreestanding -fno-pie -c examples/mixed/driver_linux_x86_64.c \
  -o "$nv_example_out/driver-compact.o"
cc -c examples/mixed/start_linux_x86_64.S -o "$nv_example_out/start.o"
ld --gc-sections --build-id=none --orphan-handling=error -s \
  -T linker/linux-x86_64-compact.ld \
  "$nv_example_out/start.o" "$nv_example_out/driver-compact.o" \
  "$nv_example_out/pop.o" "$nv_example_out/square.o" \
  -o "$nv_example_out/compact"
python3 examples/mixed/verifier.py --binary "$nv_example_out/compact"
```

`nv_example_out` 안의 결과가 필요 없어진 뒤 그 디렉터리만 정리한다. 전체 포트폴리오 도구는 같은 선택을 manifest와 recipe로 기록한다. 어느 component object가 더 작다는 사실만으로 완성 제출 파일의 승자를 결정하지 않는다.

## 링크 이후 ELF 배포 변환

현재 Rust 구현인 `src/elf.rs`의 `deployment_variants(data, allow_section_header_removal)`는 원본과 선택적인 section-header 제거 후보를 반환한다. 두 번째 인자 `true`는 호출자가 **self-file/section-header 관측을 배포 계약에 포함하지 않고, 수정할 ELF metadata bytes를 코드나 데이터로 재사용하지 않는다**고 선언하는 것이다. 도구가 임의 프로그램에서 이 의미 전제를 자동 증명하지 않는다. 과거 `nvelf.py`는 `reference/v0.3/`에 보존한 비교 자료이며 활성 API가 아니다.

이 선택은 byte-lossless codec이 아닌 배포 변환이다. ELF·program-header의 크기와 범위, 모든 program-header file extent를 확인하고 마지막으로 필요한 byte 뒤의 내용만 자른다. `e_shoff`, `e_shentsize`, `e_shnum`, `e_shstrndx`를 0으로 바꾸되 program headers는 보존한다. 현재 구현은 일반적인 비확장 ELF64LE x86-64 ET_EXEC/ET_DYN을 지원하며, 범위를 벗어난 구조를 읽거나 extended numbering을 추측하지 않는다. 입력을 거부할 때 원본을 변환 성공으로 보고하지 않는다. 실행 의미는 최종 후보를 실제 실행하여 따로 확인한다.

이 예제의 GCC 13.3/GNU ld 2.42/Rust 1.99.1 `-Os`/`opt-level=z` 조합을 직접 비교했을 때, compact의 C Kernighan + C arithmetic은 전체 ELF 736바이트에서 523바이트가 되었고 C Kernighan + C table은 808바이트에서 520바이트가 되었다. 이 수치는 해당 도구·옵션의 작은 커널 예제 관측이며 체스 엔진의 크기·성능 추정이 아니다. **링크 직후에는 더 컸던 table 후보가 최종 배포 변환 뒤에는 더 작아졌다.** 따라서 앞 단계에서 가장 작았던 component나 ELF만 남기는 greedy 선택으로 최종 포트폴리오를 대체하면 안 된다. 실제 확인한 C/Rust 아홉 조합의 두 링크 프로필 모두 원본과 sectionless 실행에서 전체 oracle를 통과했다.

위 수치는 보존한 이전 관측이다. Rust 0.4의 별도 `size-lto`/`compact` 포트폴리오는 18개 링크 후보와 396개 최종 후보를 검증했고 C Kernighan + C table의 504바이트 ELF를 선택했다. [0.4 검사 근거](../../evidence/0.4/mixed-selected-tool-replay.json)에 해당 옵션·해시·독립 재현을 기록했다. README의 이관 설명만 검사 후 갱신했으며, 당시 입력 해시를 새 문서 해시로 덮어쓰지 않았다.

## 실제 verifier와 확인 범위

`verifier.py --binary PATH`는 지정한 **최종 실행 파일 자체**를 실행한다. ELF뿐 아니라 동일한 stdin/stdout/exit 계약을 구현하는 허용된 wrapper도 이 인터페이스로 확인한다. 실행은 shell 문자열이 아닌 argv로 전달한다.

Python oracle은 `int.bit_count()`와 네 중앙 칸까지의 거리 정의를 사용한다. 구현 후보끼리의 다수결이나 동일 C 함수의 재사용으로 기대값을 만들지 않는다. 전체 모드는 세 high-bit mask 각각에 대해 16비트 부분공간 전체와 edge/random cases를 검사하여 199,360개 정상 레코드를 확인한다. 빈 입력, 유효 prefix 이후 잘린 입력, 레코드의 1~15바이트 절단, square·reserved 범위도 확인한다. 이는 유한한 입력 검증이며 전체 2^64 영역의 형식적 동등성 증명이 아니다.

`--quick`은 모든 square와 경계·고정 PRNG 입력을 포함한 1,216개 정상 레코드 및 짧은 오류 검사를 사용한다. 후보별 실행과 최종 후보의 더 넓은 검사에 서로 다른 모드를 사용할 수 있지만 결과에 모드가 기록된다. `--timeout`의 기본값은 전체 corpus 생성과 case 실행을 합쳐 20초다. 성공·실패와 corpus/oracle hash는 JSON 한 줄로 출력한다.

입출력은 임시 파일로 제한하고, 자식별 file-size/CPU/address-space 상한과 실행 timeout을 둔다. 종료 시 실행의 새 process group에 종료 신호를 보내고 직접 자식을 reap한다. 이 기능은 보안 sandbox, 전체 process tree의 자원 합계 측정 또는 detached descendant의 종료 증명이 아니다. 이 예제와 수락되는 wrapper는 daemonize/detach하지 않는다. CPU thread scaling이나 체스 기력은 이 verifier가 검사하는 계약이 아니다.

## 공식 근거

- [GNU ld INSERT와 default script 보완](https://sourceware.org/binutils/docs/ld/Miscellaneous-Commands.html)
- [GNU ld PHDRS](https://sourceware.org/binutils/docs/ld/PHDRS.html)
- [ELF header 형식과 section table의 부재](https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.eheader.html)
- [Rust C ABI](https://doc.rust-lang.org/reference/items/external-blocks.html#abi)
- [rustc codegen options](https://doc.rust-lang.org/rustc/codegen-options/index.html)
- [x86-64 System V psABI](https://gitlab.com/x86-psABIs/x86-64-ABI)
