# TCEC 4K 기준본의 빌드 요구 사항과 소스 대응 범위

기준일: 2026-10-19. 이 문서는 조사와 빌드 감사에서 확인한 **11개 비교 기준본**의 요구 사항을 기록한다. 제공된 원본을 다시 패킹하는 작업과, 편집 가능한 upstream 소스에서 그 원본을 처음부터 생성하는 작업을 구분한다. 최신 대회 제출물의 확보 여부는 [엔진 조사](ENGINE-ROSTER.md), 정확한 소스·라이선스 목록은 [vendor manifest](../vendor/source-manifest.json), 실행·압축의 최종 판정은 [결과 보고서](../docs/REVIEW-AND-RESULTS.md)를 따른다.

이 패키지는 원본 입력, 엔진 소스, NVCompact 소스와 재현 recipe를 제공한다. **컴파일러·인터프리터·Cargo crates·외부 빌드 도구를 모두 설치한 오프라인 toolchain 패키지는 아니다.** 아래에서 확인한 버전은 실제로 확인한 도구 버전이며, upstream이 지원하는 모든 버전의 목록이나 최저 요구 버전으로 해석하지 않는다.

## 1. 제공된 원본을 재패킹할 때

패키지 루트의 `inputs/<engine>`에 비교 원본이 있다. [engines](../engines/)의 각 manifest는 원본 SHA, 압축 해제 형식, 정확한 launcher와 필요한 compiler argv를 지정한다. 이 경로에서는 upstream의 원래 minifier·링커·원래 압축 포트폴리오를 다시 설치할 필요가 없다. 이미 만들어진 원본을 해제하고, NVCompact가 의미 근거를 확인한 표기와 포장을 비교한다.

NVCompact 개발 인터프리터는 CPython 3.11 이상이며 표준 `lzma`, `bz2`, `gzip` 모듈을 사용한다. 이번 기록에는 CPython 3.12.14, GCC 13.3.0, GNU ld 2.42, XZ/liblzma 5.4.5가 확인되어 있다. Rust가 필요한 검사에는 Rust 1.99.1을 사용했다. 실제 실행 argv와 compiler hash는 각 캠페인의 기록을 확인한다. [실측 환경](../evidence/environment/environment.json), [사용법](../README.md)

| 입력 종류 | 표기·재패킹 및 실제 제출 파일 실행에 필요한 것 |
|---|---|
| ice4 | C++ compiler, `-O3 -pthread`; 원래 launcher는 `c++`를 호출한다. |
| 4ku | C++20를 처리하는 G++; 원래 `-O3 -march=native -pthread -std=c++20`를 보존한다. |
| c4ke | C++23를 처리하는 G++; 원래 manifest의 최적화·CPU·스레드 옵션을 보존한다. |
| M4sseur | C++20 compiler; 원래 `-march=native -std=c++20 -pthread -O3 -DNDEBUG`를 보존한다. |
| molly | `rustc`; 원래 launcher의 `-Ctarget-cpu=native -O`와 명시되지 않은 edition 조건을 그대로 따른다. Cargo는 제공된 minified 입력의 즉시 컴파일에 필요하지 않다. |
| moonfish | C compiler와 `-lm -pthread -latomic`; 원래 launcher는 `unxz -Fraw`와 `cc`를 호출한다. C11 원자 연산·스레드 및 POSIX 환경이 필요하다. |
| sunfish | 실행용 `python3 -u`. 원래의 python-minifier는 제공된 packed 입력을 재패킹하는 데 필요하지 않다. |
| pygone | 실행용 `pypy3`. NVCompact 자체를 실행하는 CPython과 별도로 준비한다. |
| STRO4K, we4k | 제공된 native payload를 해제할 XZ 계열 도구와 해당 x86-64 명령어를 지원하는 Linux 환경. 이 경로에는 원래 assembler·Zig·Rust build helper가 필요하지 않다. |
| 4k.c | 원래 자체 해제 ELF를 실행할 x86-64 Linux 환경. 원본 자체를 후보로 보존하거나 패킹하는 데 저자의 특수 GCC를 다시 설치할 필요가 없다. |

셸 포장 파일은 각 manifest에 기록된 `sh`, `mktemp`, `tail`, codec decoder, `chmod`, `sleep`, `rm` 등의 도구도 호출한다. 이 표는 **실행 의존성**을 설명한다. 해당 명령의 TCEC 허용 여부는 [공식 규칙](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853) 및 [규칙 판정 경계](ENGINE-ROSTER.md#7-규칙에-관한-판정-경계)와 별개로 확인한다.

UCI 검사기의 합법수 oracle인 `chess==1.11.2`는 개발 의존성이다. 엔진 입력이나 제출 파일에 합쳐 사용하지 않는다. 실행 예시는 패키지 루트에서 다음과 같다. 명령은 새 출력 디렉터리를 사용한다.

```sh
python3 nvenvelope.py engines/sunfish.json \
  --output runs/sunfish-01 --uci --oracle-path .deps

python3 nvreproduce.py runs/sunfish-01/summary.json \
  --output runs/sunfish-01-replay \
  --selection accepted --uci --oracle-path .deps
```

## 2. 편집 가능한 소스로 upstream 원본을 다시 만들 때

아래 source archive는 [vendor manifest](../vendor/source-manifest.json)에 기록한 커밋으로 고정했다. archive 내부 root는 [available-artifacts.json](available-artifacts.json)의 `source_root_in_archive`에 있다. 원래 빌드 스크립트는 archive 안에 보존했으며, 빌드 작업은 새로 추출한 작업 사본에서 수행한다.

원래 소스 빌드와 NVCompact의 재패킹은 서로 다른 재현 주장이다. `original`의 보존·해제·재패킹이 재현되어도 upstream compiler부터 그 release asset을 다시 만들었다는 뜻은 아니다. 특히 시간·CPU·스레드·hash 설정이 빌드 입력인 엔진은 같은 버전 이름만으로 같은 대회 파일이라고 판단하지 않는다.

### ice4 — 공개 v6.1

- **제공 자료:** [소스 archive](../vendor/ice4/source.tar.gz), [GPL-3.0](../vendor/ice4/LICENSE). C++ 엔진 모듈, Rust minifier 전체, parser grammar, `build.rs`, `Cargo.toml`, `Cargo.lock`, `Makefile`, `compress.sh`, launcher를 포함한다. 소스 커밋은 `2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19`다. [upstream](https://github.com/MinusKelvin/ice4)
- **원래 빌드 진입점:** `make ice4-tcec`. `cargo run --release tcec`로 minify한 뒤 `compress.sh`와 `launcher.sh`를 결합한다. Rust/Cargo, Bash, XZ 및 일반 빌드 유틸리티가 필요하다. 결과 launcher를 실행하려면 C++ compiler가 필요하다.
- **별도 의존성:** minifier는 `lalrpop`, `lalrpop-util`, `once_cell`, `regex` 등을 사용한다. root `Cargo.lock`은 포함하지만 crate 소스 캐시는 포함하지 않았다. 재현할 때 lock을 보존해야 한다. workspace에 함께 있는 trainer는 minifier와 별도 작업이며, trainer의 학습 환경을 엔진 실행 의존성으로 추가하지 않는다.
- **확인 범위:** 같은 v6.1 태그의 소스와 저자의 `ice4-tcec` release asset을 대응시켰다. upstream minifier부터 그 release asset의 전체 바이트를 독립 재현하지는 않았다. 대회의 6.1.1과 공개 v6.1은 구분한다. 뒤의 crash-fix HEAD를 6.1.1 제출물로 대신 사용하지 않았다.

### 4ku — 공개 v5.1 mini

- **제공 자료:** [소스 archive](../vendor/4ku/source.tar.gz), [MIT](../vendor/4ku/LICENSE). C++ 엔진, Python minifier, `build-mini.sh`, launcher, Makefile/CMake 파일을 포함한다. 커밋은 `203ddd4bf9b331851c796d8b5d57eac08f6e6c18`다. [upstream](https://github.com/kz04px/4ku)
- **원래 빌드 진입점:** `bash build-mini.sh`. Python 3의 표준 라이브러리로 자체 minifier를 실행하고 `lzma`의 match finder와 nice 길이를 탐색한다. 스크립트의 brace expansion은 Bash 조건이다. 결과 launcher를 실행하려면 G++ C++20가 필요하다. CMake는 이 mini 스크립트 경로의 필수 도구가 아니다.
- **확인 범위:** 같은 release 태그와 mini asset의 대응 관계다. minifier부터 원래 4,093B asset의 독립 재생성은 미실시다. 공개 mini payload는 `D=1`, `E=64ull<<16`의 1 thread·64 MiB TT 프로필이다. 대회 버전 이름이 같다는 사실만으로 TCEC 서버용 프로필까지 동일하다고 주장하지 않는다.

### STRO4K — 공개 v5.0의 셸 포장 파일

- **제공 자료:** [소스 archive](../vendor/stro4k/source.tar.gz), [GPL-3.0](../vendor/stro4k/LICENSE). 모든 ASM 모듈, Rust build helper, `build4k`, `build4kdefault`, launcher와 관련 개발 소스를 포함한다. 커밋은 `d06d36c4655f99bf1d925ae7a2c22d6657d46e7b`다. [upstream](https://github.com/ONE-RANDOM-HUMAN/STRO4K)
- **원래 빌드 진입점:** `./build4k <output> <threads> <hash_mib> [--avx512]`. Rust/Cargo로 표준 라이브러리만 사용하는 `build4krs`를 실행한다. helper는 NASM으로 `NUM_THREADS`, `TT_SIZE_MB`, 선택적 `AVX512` 정의를 적용하고, **`ld`, `ld.gold`, `ld.lld` 세 링커**와 XZ의 raw LZMA2 설정을 비교한다. helper가 각 linker의 성공을 요구하므로 하나만 설치했다고 원래 전체 포트폴리오가 준비된 것은 아니다.
- **별도 의존성:** `git`, `make`, C 빌드 도구가 필요하다. helper는 [super-strip](https://github.com/aunali1/super-strip)을 버전 고정 없이 clone해 `sstrip -z`를 사용한다. super-strip의 소스·실행 파일은 엔진 archive에 포함하지 않았다.
- **확인 범위:** v5.0 소스와 release asset을 보존했다. release에 쓰인 정확한 thread/hash/CPU 옵션으로 native payload를 독립 재현하지는 않았다. 일반 VII의 5.0.1, ELF의 LESS_STRO4K 및 STRO4K 6.0에 대응하는 정확한 공개 제출 파일은 확보하지 못했다. 제공한 v5.0은 외부 XZ를 쓰므로 ELF-only 제출물로 간주하지 않는다.

### 4k.c — 공개 v9.0 자체 해제 ELF

- **제공 자료:** [소스 archive](../vendor/4k-dot-c/source.tar.gz), [MIT](../vendor/4k-dot-c/LICENSE), [Crinkler 유래 zlib 고지](../vendor/4k-dot-c/THIRD_PARTY_LICENSES). 엔진 C, 전용 linker scripts, `compressor.c`, `loader.asm`, Makefile 및 보조 스크립트를 포함한다. 커밋은 `880a877d6af2046cc5ce7deb85ea5ad2855b41a1`다. [upstream](https://github.com/GediminasMasaitis/4k-dot-c)
- **원래 빌드 진입점:** `make NOSTDLIB=true MINI=true loader`. GNU C의 `gnu2x` 모드, NASM, GNU 계열 linker 및 Makefile이 호출하는 유틸리티가 필요하다. C를 assembly로 출력하고 전용 linker script로 결합한 뒤 포함된 compressor와 ASM loader를 사용한다.
- **특수 compiler 조건:** v9 README는 14.2와 15.1 사이 개발 시기의 [저자 GCC fork](https://github.com/GediminasMasaitis/gcc)를 요구한다. 안내 링크가 branch를 가리키며, 이번 전달 기록에서 **release에 사용된 정확한 compiler commit은 확정하지 못했다**. 일반 GCC 13.3으로 다른 엔진의 즉시 컴파일이 성공한 사실은 이 ELF release의 재현 근거가 아니다.
- **경로별 구분:** README에는 저자의 apultra도 언급되지만, 보존한 v9 Makefile의 위 `loader` 경로는 포함된 `compressor.c`와 `loader.asm`을 호출한다. 해당 경로가 호출하지 않는 도구를 NVCompact 공통 필수 의존성에 추가하지 않는다.
- **확인 범위:** v9.0 release와 같은 태그 소스를 제공한다. source부터 release ELF를 독립 재생성하지는 않았다. 9.15 소스 커밋은 별도로 확인했으나 9.15.1 제출 파일은 미확보다. ELF header 내부에 실제 코드가 있으므로 일반적인 ELF header/section 정리를 자동 적용하는 전제로 빌드하지 않는다.

### c4ke — 공개 v3.0 TCEC asset

- **제공 자료:** [소스 archive](../vendor/c4ke/source.tar.gz), [MIT](../vendor/c4ke/LICENSE). 엔진 C++, 자체 C++ minifier, makefile, `compress.sh`, launcher를 포함한다. 커밋은 `22e318f59b3a9eed1d2b8161da832222d4a51033`다. [upstream](https://github.com/citrus610/c4ke)
- **원래 빌드 진입점:** `make tcec`. G++ C++23으로 minifier를 빌드한 뒤 `./mini tcec`의 출력을 Bash/XZ 압축 포트폴리오에 넣는다. 최종 launcher도 G++를 호출한다. 확인한 minifier는 제공된 C++ 소스와 표준 라이브러리로 구성되며 별도 패키지형 minifier를 요구하지 않는다.
- **확인 범위:** v3.0 태그와 공개 `c4ke-tcec` asset의 관계를 확인했다. upstream minifier부터 동일 release bytes를 재생성한 증명은 제공하지 않는다. 대회 최신 버전과 공개 release label은 일치한다.

### pygone — 역사적 표기 2-11b142

- **제공 자료:** [소스 archive](../vendor/pygone/source.tar.gz), [GPL-3.0-or-later](../vendor/pygone/LICENSE.md), [대응 증거](../vendor/pygone/source-correspondence.json). `board.py`, `search.py`, `pygone.py` 등의 editable modules와 `pyshrink.py`, `shrink.py`, `combine.py`, Makefile, `prepare.sh`를 포함한다. 정확한 커밋은 `11bf1426bc491753b66e945692c5ee4a8d510e45`다. [동일 커밋의 원본 파일](https://raw.githubusercontent.com/scs-ben/pygone/11bf1426bc491753b66e945692c5ee4a8d510e45/dist/pygone)
- **원래 빌드 진입점:** `make pygone`. Python 3로 세 가지 소스 축소·결합 스크립트를 실행하고 XZ 압축 후 `prepare.sh`가 launcher를 결합한다. `shrink.py`는 외부 **`python_minifier`를 import하며 upstream에 그 버전 lock이 없다**. PyPy3는 최종 엔진을 실행하는 데 필요하고, 빌드 스크립트가 호출하는 `python3`와 구분한다.
- **확인 범위:** 대회 표기에 생략된 `f`를 찾아 정확한 커밋을 확정했다. 그 커밋의 `dist/pygone`과 역사적 파일은 4,093B 전체가 동일하다. 이는 소스와 동일 원본이 같은 커밋에 존재한다는 근거다. 원래 minifier 전체를 별도로 재실행해 같은 packed bytes를 얻는 검증은 미실시다. 버전이 고정되지 않은 minifier의 임의 최신 버전으로 동일 결과를 보장하지 않는다.

### Sunfish — 2022-12-24 classic

- **제공 자료:** [소스 archive](../vendor/sunfish/source.tar.gz), [GPL-3.0](../vendor/sunfish/LICENSE.md), [소스 재현 증거](../vendor/sunfish/source-correspondence.json). 입력은 **`sunfish_uci.py`**이며 `pack.sh`, `pack_head.sh`도 포함한다. 커밋은 `ccecec26626b858a60d48cf715ebbdd603ee6f85`다. [해당 editable source](https://github.com/thomasahle/sunfish/blob/ccecec26626b858a60d48cf715ebbdd603ee6f85/sunfish_uci.py)
- **확인한 재현 환경:** **CPython 3.11.17, python-minifier 2.7.0, setuptools 65.6.3**. 당시 CLI 의존성을 포함한 조합이다. 다음 명령의 출력은 원래 내장 소스 5,837B와 동일했다.

  ```sh
  python3.11 -m python_minifier \
    --rename-globals --remove-literal-statements sunfish_uci.py
  ```

- **원래 포장:** `pack.sh`는 같은 minifier 옵션으로 생성한 소스에 XZ를 적용하고 `pack_head.sh`를 앞에 붙인다. 원래 CLI 이름은 `pyminify`다. 위 검증은 이 minifier 출력의 바이트 동일성을 확인한 것이며, 모든 XZ 버전의 포장 결과를 동일하다고 보장하지 않는다.
- **확인 범위:** 원래 payload의 SHA는 `f1a676e55763635a4ba517e7439249e2f1b15da818e83369b50f6b705178f78f`다. private TCEC upload 전체와의 독립 비교는 미실시다. 현재 `4k-entry-v1`의 다른 NNUE 구현을 이 classic 대응 소스로 바꾸지 않았다. archive에서 제외한 NNUE pickle 가중치는 이 classic 경로의 빌드 입력이 아니다.

### moonfish — 저자의 버전 미표기 공개 파일

- **제공 자료:** [소스 archive](../vendor/moonfish/source.tar.gz), [0BSD 문구](../vendor/moonfish/LICENSE.0BSD.txt), [라이선스가 있는 저자 홈페이지 원문](../vendor/moonfish/LICENSE-SOURCE.html). [저자 홈페이지](https://moonfish.neocities.org/)의 `moonfish.sh`에서 복원한 minified C 전체를 보존했다.
- **native 빌드 조건:** `cc -O3 -march=native -xc ... -lm -pthread -latomic`. GCC 13.3.0 계열 `cc`로 컴파일 성공을 확인했다. 소스에 C11 원자 연산·스레드 및 POSIX 호출이 있으며 별도 학습 가중치는 필요하지 않다. 정확한 stdin/output 배치는 [실행 manifest](../engines/moonfish.json)를 따른다.
- **확인 범위:** 현재 저자 다운로드에 내장된 소스와는 정확하게 대응한다. 기존 `git.sr.ht/~zamfofex/moonfish` 저장소가 404이므로 그 이전의 비축소 editable source와 minifier는 확보하지 못했다. 현재 파일에는 version ID가 없어 대회 `4aa32a0c`와 동일하다고 입증하지 못한다. 이 엔진에 대해서는 source archive를 이전 editable repository의 완전한 대체물이라고 설명하지 않는다.

### M4sseur — 1.0 소스 재빌드 기준본

- **제공 자료:** [소스 archive](../vendor/m4sseur/source.tar.gz), [MIT](../vendor/m4sseur/LICENSE). 엔진 C++ modules, `nanosrc/nanonizer.cpp`, Linux 빌드 스크립트, 압축 스크립트와 launcher를 포함한다. 커밋은 `470fa53925c1cafeaaf84db3612abb5eb0ae9e9f`다. [upstream](https://github.com/Diazepawn/M4sseur)
- **확인한 빌드:** GCC 13.3.0 계열 C++ compiler로 `nanosrc/nanonizer.cpp`를 `-std=c++20 -march=native -O3 -DNDEBUG`로 빌드했다. `nanonizer_gcc`가 만든 소스를 원래 `compress.sh`에 넣고 launcher와 결합했다. Bash와 XZ/LZMA가 필요하다. 별도 minifier 패키지는 없다.
- **기준본 생성:** 원래 2,700개 LZMA 설정 탐색에서 `preset=9e,lc=0,lp=0,pb=0,mf=bt2,mode=normal,nice=31,depth=0`을 선택해 4,095B 기준본을 만들었다. 스크립트 마지막 정보 출력 단계가 이미 존재하는 파일 때문에 exit 1을 반환했지만, 그 전에 만들어진 압축 스트림을 검사하고 명시적으로 launcher와 결합했다. 성공으로 보이도록 원래 스크립트나 오류 조건을 숨겨 수정하지 않았다. [압축 로그](build-logs/m4sseur-upstream-pack.log), [minifier 로그](build-logs/m4sseur-nanonizer.log)
- **확인 범위:** archive의 pinned source와 실제 기준본 생성에 쓴 source files가 모두 동일함을 확인했다. 공개 prebuilt release는 없으며, 이 4,095B는 재빌드 기준본이다. private TCEC upload 전체와 동일하다는 근거는 아니다.

### molly — 정확한 대회 커밋 e317a0c7b8의 재빌드

- **제공 자료:** [소스 archive](../vendor/molly/source.tar.gz), [MIT](../vendor/molly/LICENSE), [native 빌드 기록](../vendor/molly/native-build.json). Rust 엔진, syn 기반 minifier, workspace manifests, `Cargo.lock`, build script와 launcher를 포함한다. 커밋은 `e317a0c7b823832a87239027f536582cf0576111`이다. [올바른 upstream](https://codeberg.org/latuernich/molly), [공식 저자 문답](https://wiki.chessdom.org/Molly_questionnaire_20251015)
- **확인한 빌드:** Rust/Cargo **1.99.1**. lock을 보존한 minifier 빌드를 수행한 뒤 원래 `build.sh`를 Bash로 실행했다. 스크립트는 Cargo minifier, `lzma`, shell 배열·brace expansion 및 일반 파일 도구를 사용한다. 원래 스크립트 자체에 `--locked`가 명시된 것은 아니므로 재현할 때 `Cargo.lock`이 바뀌지 않았는지 확인해야 한다.
- **별도 의존성:** lock이 고정한 minifier 의존성은 `syn 2.0.69`, `quote 1.0.36`, `proc-macro2 1.0.86`, `unicode-ident 1.0.12`다. lock 파일은 포함하고 crate 캐시는 포함하지 않았다. 최종 엔진 코드는 이 parser/minifier crates를 실행 의존성으로 요구하지 않는다.
- **확인 범위:** upstream의 match finder·nice 길이 1,360개 탐색으로 payload 3,991B와 전체 4,096B 기준본을 만들었다. native compile도 성공했다. 공개 prebuilt asset과 비교한 것은 아니며, 이 파일은 정확한 대회 커밋의 소스 재빌드다. 기준본은 101 threads와 96 GiB startup TT 할당을 유지한다. [upstream 압축 로그](build-logs/molly-upstream-pack.log)

### we4k — 2022-12-21 공개 기본 프로필 재빌드

- **제공 자료:** [소스 archive](../vendor/we4k/source.tar.gz), [GPL-3.0](../vendor/we4k/LICENSE), [독립 native 재빌드 기록](../vendor/we4k/native-build.json). 모든 Zig/ASM 모듈, `build.zig`, `build4k.sh`, launcher를 포함한다. 커밋은 `93dde6ad4aef461bdf4c8dd9d413f92090fc16eb`다. [upstream](https://github.com/ONE-RANDOM-HUMAN/we4k)
- **확인한 도구:** **Zig 0.10.1, NASM 3.01**, `sstrip`, XZ 5.4.5 계열, 원래 autovndh.py. NASM으로 `src/asm/combined.asm`을 만들고 `zig build install -Drelease-small -Dcpu=skylake-vzeroupper` 후 `sstrip -z`를 적용했다. 같은 변경 없는 소스를 다시 빌드해 native payload **5,579B 전체의 동일성**을 확인했다.
- **원래 포장:** `build4k.sh <output>`은 [super-strip](https://github.com/aunali1/super-strip)을 clone해 빌드하고, [autovndh.py](https://gitlab.com/PoroCYon/vondehi/-/raw/master/autovndh.py)를 받아 `--xz --nostub` 포트폴리오를 실행한다. Git·curl·Make·C compiler·Python 3 등 이 보조 도구를 준비해야 한다. 두 URL은 upstream 스크립트에서 버전 고정 없이 사용하며, 보조 도구 소스는 엔진 archive에 포함하지 않았다.
- **확인 범위:** 원래 포장 탐색으로 **4,079B** 기준본을 만들었다. 확인한 반복 바이트 재현은 native payload에 해당한다. 공개 release asset이 없고, 원본 소스의 **4 threads/32 MiB**를 변경하지 않았다. TCEC의 `104th-64G` 파일과는 별도의 공개 기본 프로필 대표다. 최종 payload는 AVX2/BMI2 조건을 갖는다. [upstream 압축 로그](build-logs/we4k-upstream-pack.log)

## 3. 소스·라이선스 전달 감사의 결론

11개 source archive, 보존한 source member **274개**, 원문 라이선스 및 별도 고지 **13개**의 존재와 SHA를 확인했다. STRO4K와 we4k의 검사한 ASM `%include` 대상은 모두 포함되어 있다. [무결성 기록](vendor-integrity.json), [멤버별 목록과 제외 근거](../vendor/source-manifest.json)

이 감사에서 확인한 엔진 코드·자체 minifier·build/link scripts는 archive에 보존했다. 예외적으로 Moonfish는 현재 저자 배포물의 minified C만 확보했고, 이전 editable repository의 부재를 명시했다. 일반적인 compiler·interpreter·Cargo crate 캐시 및 위에서 특정한 외부 빌드 도구는 별도 준비 대상이다. 따라서 **오프라인 소스 열람·현재 입력의 재패킹 재현 근거 제공**과 **외부 의존성이 전혀 없는 upstream 전체 빌드**를 같은 제공 범위로 표시하지 않는다.

원래 공개 소스의 라이선스 바이트를 보존했다. 4k.c는 compressor/loader의 추가 고지를, Moonfish는 저자 홈페이지의 0BSD 허가 원문을 함께 제공한다. 로고, 이미 생성된 별도 배포 실행 파일, 이 classic 경로에서 사용하지 않는 NNUE pickle 가중치를 제외한 내역은 manifest에 있다. 이 제외를 엔진의 실제 build input 제거로 확대하지 않았다.

변환된 산출물은 NVCompact 소스, 표기·codec recipe, 원본 SHA 및 해당 캠페인의 original/selected payload와 연결된다. header만 변경한 후보는 원래 payload와 대응하며, `selected-payload`가 없다는 이유로 다른 native 코드를 사용했다고 판단하지 않는다. 정확한 대응 관계는 각 `summary.json`의 winner·payload hash와 독립 replay 기록을 확인한다.

## 4. 경로와 증거를 읽는 기준

- [실행 manifest](../engines/)의 `provenance.path_base`는 **manifest-directory**다. 예를 들어 `../vendor/ice4/source.tar.gz`는 해당 엔진 JSON에서 해석한다.
- [연구용 입력 목록](available-artifacts.json), [전체 roster](ENGINE-ROSTER.json), [vendor manifest](../vendor/source-manifest.json)의 배포 경로는 **패키지 루트 `nvcompact-v02` 기준**이다. 실제 source tree를 풀지 않았으므로 `source_root`는 null이고, 추출할 내부 경로는 `source_root_in_archive`에 있다.
- `source_archive_sha256`은 전달한 archive의 hash다. 정리 전 다운로드 archive의 hash를 함께 기록한 경우 이를 현재 archive에 대한 검사값으로 사용하지 않는다.
- `build-logs/`와 일부 vendor proof의 argv에는 당시 임시 toolchain 및 source work directory의 절대 경로가 남아 있다. 이는 **그때 실제 실행한 명령의 기록**이다. 이동한 패키지에서 그 절대 경로를 실행 진입점으로 사용하지 않는다.
- 초기 캠페인 snapshot의 provenance는 당시 확보 상태를 보존할 수 있다. pygone·Sunfish의 최종 대응 근거와 현재 소스 경로는 현재 `engines/*.json`, `available-artifacts.json`, `vendor/source-manifest.json`을 기준으로 읽는다. 과거 결과를 새 도구의 결과로 바꾸거나 evidence hash를 덮어쓰지 않는다.

빌드 성공은 엔진의 UCI 동작, 실제 서버의 메모리 할당 가능성 또는 대회 승인을 뜻하지 않는다. TT·스레드 상수를 줄여 실행한 다른 프로필을 원래 제출 파일의 검증이라고 기록하지 않으며, 실제 실행 판정은 최신 캠페인 보고서의 환경과 함께 읽는다.
