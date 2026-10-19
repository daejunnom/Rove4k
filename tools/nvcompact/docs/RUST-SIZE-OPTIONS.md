# Rust·ELF 추가 크기 최적화 조사

2026-10-19에 확인한 후속 조사다. NVCompact의 버전은 현재 `0.4.0`이며,
이 문서는 엔진 설계를 고정하는 규약이 아니다. 구현한 zero-tail 변환과 자체
C/Rust 실측은 [ELF-RUST-COMPACTION.md](ELF-RUST-COMPACTION.md)에 따로 기록한다.
아래에서 **조사 후보**는 이 세션에서 성능이나 압축 이득을 입증했다는 뜻이 아니다.

## 판단 단위

비교 대상은 실제 배포 파일 전체다. native ELF에서는 ELF·program header, 코드,
초기화 데이터와 파일 padding을 합산한다. General wrapper에서는 복원 명령과
payload도 합산한다. ELF 전용 제출에서 외부 `xz`를 실행하는 shell wrapper의
작은 크기를 ELF 압축 성공으로 계산하지 않는다. ELF 안에 decoder를 넣는 방식을
추가한다면 그 decoder와 로더의 모든 바이트도 포함한다.

서로 다른 소스가 같은 ELF를 만들 수 있는 이유는 compiler의 lowering·최적화,
object 생성, relocation 처리와 linker의 배치·제거·병합이 결합하기 때문이다.
링커가 임의의 C/Rust 소스 의미를 다시 해석해 모두 같은 프로그램으로 바꾸는 것은
아니다. **같은 고정 입력의 ELF 바이트가 동일한 사실**, 실행 표본의 결과가 같은 사실,
언어 수준에서 모든 허용 입력의 의미가 같은 주장은 서로 다른 근거다.

선택은 다음 순서로 설명한다. 원본 후보를 보존하고, 적용 계약을 만족하는 변형을
생성하고, 완성된 파일을 측정하고, 주장에 필요한 실제 실행을 검증한다. 원본보다 큰
후보도 결과에 남길 수 있으나 작은 값을 만들기 위해 실패를 성공으로 취급하지 않는다.
엔진의 TT 크기·스레드 정책·탐색 선택이 바뀌면 별도의 성능 변경으로 판단한다.

## 후보별 적용 경계

| 부분 | 비교할 방법 | 작아질 수 있는 이유 | 필요한 관측 계약·검사 |
|---|---|---|---|
| 마지막 초기화 데이터 | 마지막 RW `PT_LOAD`의 저장된 0 suffix를 zero-fill로 표현 | 같은 가상 메모리를 더 적은 파일 바이트로 표현 | 이번에 구현. 정적 x86-64 ET_EXEC, 페이지 비공유, 원본 파일·변경 header 비관측. [실측 문서](ELF-RUST-COMPACTION.md) 참고 |
| 파일 배치 | 필요한 PHDR만 유지, 코드·데이터 순서와 정렬 후보 비교 | page/file padding과 짧은 분기·relocation 배치가 달라질 수 있음 | loader 제약과 각 section의 정렬 보존. RX/RW 분리·TLS·constructors 등 필요한 실행 기능을 먼저 확인 |
| 도달하지 않는 코드·데이터 | section 단위 GC, 최소한의 export/visibility, 정확한 linker `KEEP` | 실제 쓰지 않는 section의 제거 | 동적 조회·초기화 목록·FFI export·inline assembly의 숨은 참조를 도달 불가로 오판하지 않음 |
| Rust 최적화 profile | `s`, `z`, `2`, `3`; LTO off/thin/fat; 적절한 codegen-unit 수 | inlining·vectorization·상수 전파·중복 제거의 결합 차이 | `z`나 fat LTO의 최소 크기를 가정하지 않음. 실제 linked/packed 크기와 성능을 각각 측정 |
| C/Rust 경계 | 동일 C ABI의 자체 구현 교환, 별도 후보로 cross-language LTO | 서로 다른 frontend 결과 및 경계 간 상수 전파 | ABI·layout·호출 규약·panic/예외 경계 보존. bitcode 도구 호환성 확인. 일반 object 링크와 LTO를 구분 |
| Generic 코드 | 큰 공통 본체를 공유하고 작은 type-specific wrapper를 유지하는 변형 | 여러 monomorphized 본체의 중복을 줄일 가능성 | 핫패스의 specialization·inlining 손실과 간접 호출 비용 비교. trait object를 일괄 강제하지 않음 |
| 출력과 cold path | 정수 전용 formatter, 공통 오류 처리, cold code outlining의 자체 n-version | 범용 formatting·여러 오류 경로의 코드/문자열 감소 가능성 | 부호, 최솟값·최댓값, EOF, 부분 쓰기, 오류 코드 등 외부 계약을 독립 검증. 공개 진단 변경은 명시 |
| 상수·표·상태 배치 | 공유 static, 동일 값 생성식, 0 상태의 BSS, 생성 시점 변경 후보 | 반복 데이터·relocation·초기화 이미지의 감소 가능성 | `const`/`static` 변경의 주소·identity·수명·초기화 관측 확인. 생성 비용과 thread 최초 접근 경합도 비교 |
| 좁은 타입·enum 표현 | 도메인이 입증된 필드 폭·표현의 후보 비교 | 데이터·load/store·산술 명령이 달라질 수 있음 | 범위·sentinel·overflow·직렬화·FFI layout 보존. 타입이 좁아졌다는 이유만으로 코드도 작다고 가정하지 않음 |
| 압축 친화적 순서 | function/object/data 순서, BCJ 등 선언된 필터와 codec 조합 | 반복 패턴·분기 주소 표현·dictionary 활용이 달라짐 | 링크 순서가 symbol 선택·초기화 순서를 바꾸지 않는 계약. filter 복원과 완성 wrapper까지 측정 |
| 실행 시 복원 | 자체 decoder를 포함한 native packer | 코드·데이터의 중복을 runtime 복원 비용과 교환 | decoder+ELF header의 순이득, auxiliary vector·권한·스택·thread 시작을 포함한 실제 실행. 현재 조사 후보 |

Rust 공식 Cargo 문서도 `s`/`z`가 반드시 가장 작은 결과를 만들지는 않는다고 설명한다.
`z`는 loop vectorization을 비활성화한다. 작은 소스 하나의 비교만으로 엔진의
여러 crate·thread·hot path에 같은 최적점을 주장할 수 없다.
출처: [Cargo profiles](https://doc.rust-lang.org/cargo/reference/profiles.html).

이번 자체 예제는 Rust object 하나를 `codegen-units=1`로 생성했다. 따라서
off/thin/fat 비교를 **대규모 multi-crate LTO 성능 검증**으로 해석하지 않는다.
일반 object를 연결하는 C/Rust 선택 기능은 LLVM bitcode LTO가 없어도 사용할 수 있다.
cross-language LTO는 별도 후보로 준비하고 `rustc -vV`, clang, linker/plugin의
실제 버전을 recipe에 남긴다. Rust 공식 문서는 참여 compiler가 만든 bitcode를
plugin이 읽을 수 있어야 하며, 동일 LLVM 버전 조합을 가장 좋은 기준으로 권한다.
출처: [rustc linker-plugin LTO](https://doc.rust-lang.org/rustc/linker-plugin-lto.html).

## 일괄 자동 적용하면 안 되는 옵션

### Panic·unwind·진단 정보

`panic=abort`는 단순 문자열 압축이 아니다. unwinding, destructor 실행,
`catch_unwind`, thread별 실패 처리와 프로세스 종료의 관측이 달라진다. 제출 엔진이
해당 실패를 어떻게 정의하는지 확인한 특수 profile에서는 후보가 될 수 있지만,
NVCompact 개발 도구의 일반 동작을 줄이기 위해 자동으로 바꾸지 않는다.
unwind table 제거, custom panic handler, backtrace와 경로 정보 제거도 같은 기준으로
따로 판단한다. `--remap-path-prefix`조차 관측 가능한 진단 문자열을 바꿀 수 있다.
출처: [Rust panic strategy](https://doc.rust-lang.org/rustc/codegen-options/index.html#panic),
[Rust panic](https://doc.rust-lang.org/reference/panic.html).

오래된 초소형 Rust 안내의 `-Zbuild-std-features=panic_immediate_abort`를 현재
명령으로 복사하면 안 된다. 확인한 최신 core 소스는 이 기능을 실제 panic strategy로
옮겼다고 알린다. 현재 nightly Cargo 문서는 `panic-immediate-abort` 기능과
`panic="immediate-abort"` 설정을 설명한다. core/std도 적절하게 다시 빌드해야 하며,
이 실험은 현재 stable `1.99.1` 빌드·배포 경로에 적용하지 않았다.
출처: [core panicking source](https://doc.rust-lang.org/stable/src/core/panicking.rs.html),
[Cargo unstable panic-immediate-abort](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#panic-immediate-abort).

nightly `-Zlocation-detail`은 panic·`track_caller` 위치 정보와 관련된 크기 후보다.
위치 차이가 사라져 코드가 합쳐질 가능성이 있으나 진단 관측도 달라진다. std를
그대로 사용하면 std 안의 정보는 남을 수 있다. 실제 pinned nightly와 rebuild-std
실험을 하기 전에는 이득이나 재현 성공을 보고하지 않는다.
출처: [location-detail](https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/location-detail.html).

### 함수 병합과 주소 의미

ICF는 같은 section 내용을 합쳐 파일을 줄일 수 있지만, 함수 주소를 비교하거나
주소 identity로 dispatch하는 프로그램의 계약을 검토해야 한다. `--icf=all`을
일반 의미 보존 변환으로 등록하지 않는다. `--icf=safe`도 compiler가 만든 주소
중요도 정보와 linker 구현을 사용하므로 NVCompact의 독립 검증을 대체하지 못한다.
LLVM의 공식 linker 설명도 함수 주소의 차이를 관측하는 경우를 구분한다.
출처: [LLD ICF](https://lld.llvm.org/NewLLD.html#icf-identical-code-folding).

Rust 프로젝트에는 function pointer provenance와 `--icf=safe`를 함께 사용한
실제 오컴파일 보고도 있다. 그 보고는 특정 Mach-O/LLVM 조합이므로 현재 Linux
ELF 결과의 실패 증거로 확대하지 않는다. 다만 옵션 이름만으로 모든 toolchain과
프로그램에서 동등성을 보장할 수 없다는 구체적인 검토 근거다.
출처: [rust-lang/rust #160267](https://github.com/rust-lang/rust/issues/160267).

### no_std·시작 코드와 멀티스레딩

`no_std`, 자체 `_start`, syscall I/O는 작은 자체 예제에 적합한 후보다. 그러나
표준 runtime을 없애면서 stack alignment, FFI, thread 생성·종료, TLS, allocator,
signal, cancellation 같은 필요한 책임도 사라졌다고 가정하면 안 된다.
no_std 언어 지원과 실제 운영체제 실행 책임은 다른 층이다.
출처: [Rust no_std](https://doc.rust-lang.org/reference/names/preludes.html#the-no_std-attribute),
[ELF program loading](https://gabi.xinuos.com/elf/07-pheader.html).

Rove4k는 많은 코어를 활용하는 효과가 중요한 프로젝트다. thread-local 상태를
공유 static으로 바꾸거나 atomic을 일반 접근으로 바꿔 얻은 크기는 동등한 압축으로
계산하지 않는다. compact startup/loader는 엔진의 병렬 탐색과 독립적으로 작게
설계할 수 있지만, 실제 선택은 제출 규정과 실전 처리량·탐색 품질·메모리 비용을
함께 비교한다. 이번 zero-tail 예제는 단일 실행의 상태 표현을 검증하며 멀티스레드
엔진의 성능 실험이 아니다.

### Native packer

UPX의 Linux 문서는 packed executable이 저장 공간을 runtime 메모리와 복원 CPU
비용으로 교환한다고 설명한다. 이 원리는 추가 후보를 설계할 근거지만, 문서의
일반 압축률이나 오래된 특정 32-bit stub 크기를 현재 x86-64 4 KiB 제출 수치로
사용할 수 없다. 이번에는 UPX를 TCEC 엔진에 적용·검증하지 않았다.
출처: [UPX official manual source](https://github.com/upx/upx/blob/devel/doc/upx.pod).

소형 native decoder를 추가하려면 `raw`를 계속 후보로 두고, native ELF·decoder·
compressed payload의 전체 합이 실제로 줄었을 때만 선택한다. 실행 시 복원 경로는
단순 파일 roundtrip 검사 외에 loader와 프로그램의 관측 계약을 확인해야 한다.
새 외부 실행 파일·라이브러리가 필요하면 해당 TCEC 부문의 허용 여부도 별도 근거가
필요하다. npm으로 배포하는 NVCompact 자체의 크기는 엔진 제출 크기에 포함되지 않는다.

## 다음 실험의 우선순위

우선 기존 n-versions 경로로 object/function 순서와 compiler profile을 비교하고,
현재 엔진에 실제로 많은 바이트를 쓰는 formatting·generic 본체·데이터를 찾아
작은 자체 교체 후보를 설계한다. 그 다음 bitcode 호환성을 고정할 수 있는 경우에
cross-language LTO를 비교한다. Native packer와 header/code 중첩은 별도의
loader 설계가 필요하므로 앞선 저비용 후보보다 후순위로 둔다.

이 순서는 현재 근거에 따른 연구 제안이다. 새 profile이 기존 후보보다 작지 않으면
원본 또는 기존 승자를 유지한다. 작은 파일을 만들었다는 이유만으로 새로운 게임 성능,
TCEC 적격성, 메모리 안전성이나 모든 입력의 의미 보존을 자동으로 주장하지 않는다.
