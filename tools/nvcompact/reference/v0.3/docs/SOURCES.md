# 근거 자료와 주장 범위

확인일: 2026-10-19. 아래는 언어·도구·대회 규칙의 1차 자료다. 실제 크기, 실행 결과와 재현 여부는 [실측 보고서](REVIEW-AND-RESULTS.md) 및 [이전 캠페인 요약](../evidence/engine-results-v02.csv)의 직접 관측을 따른다. 공개 문서가 NVCompact의 압축률이나 임의 프로그램 동등성을 보장하는 것은 아니다.

## 1. TCEC와 프로토콜

| 자료 | 확인하는 내용 |
|---|---|
| [TCEC 4k Rules, revision 7853](https://wiki.chessdom.org/index.php?title=TCEC_4k_Rules&oldid=7853) | 일반 4K의 4096B·한 파일·60초 시작·파일 정리·허용 명령/라이브러리·최소 UCI, 별도 ELF 규칙, 30분+3초 대국 조건 |
| [현재 규칙 URL](https://wiki.chessdom.org/TCEC_4k_Rules) | 이후 규칙 변경 여부를 확인할 정본 |
| [UCI 원문 보존본](https://backscattering.de/chess/uci/) | TCEC 규칙에서 연결한 2006년 프로토콜 문서; 일반 UCI와 4K 필수 subset의 구분 |
| [python-chess Core](https://python-chess.readthedocs.io/en/latest/core.html) | 개발 검사기의 독립 Board·legal_moves oracle; 검사한 패키지는 chess 1.11.2 |
| [Current Engine Status, revision 9511](https://wiki.chessdom.org/index.php?title=Current_Engine_Status&oldid=9511) | 발표된 S31 명단과 VII·ELF III 결과; 모든 역사적 엔진을 망라하는 단일 출처는 아님 |
| [TCEC-Chess/tcecgames](https://github.com/TCEC-Chess/tcecgames) | 공식 PGN과 참가 엔진의 실제 이름·버전 |

명령 목록의 `rm` 누락과 규칙의 `rm` 사용 예제, 공개 launcher의 `g++`·`unxz` 사용은 서로 다른 관측이다. 운영진 재량 조항이 있으므로 공개 파일의 존재를 해당 명령의 명시 허용 또는 현재 환경 승인과 같게 취급하지 않는다. UCI 도구는 외부 라이브러리의 대회 승인 전체를 자동 판정하지 않는다.

## 2. 숫자·토큰·소스 표기

| 자료 | 구현에 반영한 부분 |
|---|---|
| [C11 draft N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) | §6.4.4.1 정수의 기수·타입 후보, §6.4.4.2 float, §6.4.8 pp-number, macro 문자열화·붙이기와 전처리 단계 |
| [C++ draft: integer literals](https://eel.is/c++draft/lex.icon) | decimal과 non-decimal의 다른 타입 선택, suffix; 현재 초안의 모든 기능을 C++17에 소급하지 않음 |
| [C++ draft: floating literals](https://eel.is/c++draft/lex.fcon) | decimal/hexadecimal float와 suffix; 실제 target 컴파일을 별도로 확인 |
| [Rust Reference: tokens](https://doc.rust-lang.org/reference/tokens.html) | 숫자 suffix, raw string, macro token과 예약 prefix; Rust 2021 target 범위 |
| [Rust Reference: literal expressions](https://doc.rust-lang.org/reference/expressions/literal-expr.html) | literal 타입과 정수·float 추론 구분 |
| [Python tokenize](https://docs.python.org/3/library/tokenize.html) | 표준 tokenizer와 token 재출력의 계약; token 동일성이 최소 공백이나 원래 위치를 보장하지 않음 |
| [Python lexical analysis](https://docs.python.org/3/reference/lexical_analysis.html) | 들여쓰기, 명시·암시 line joining, encoding, integer/float/string 문법 |
| [Python ast](https://docs.python.org/3/library/ast.html) | 전체 AST 구조와 literal 값의 비교; 위치·원문 관측은 별도 계약 |

LP64 정수 모델, 정확한 유리수와 IEEE 모델 bits, source 비관측 계약, 동일 native/object 파일 확인을 결합한 적용 게이트는 NVCompact의 설계다. 언어 표준만으로 모든 compiler 플래그, 확장 타입, macro, introspection을 지원한다고 주장하지 않는다. [NOTATION](NOTATION.md)에 실제 지원·미지원 범위가 있다.

## 3. 압축과 decoder

| 자료 | 구현에 반영한 부분 |
|---|---|
| [XZ 공식 man page](https://tukaani.org/xz/man/xz.1.html) | LZMA-alone·XZ·raw 형식, lc/lp/pb, dictionary, match finder, nice length, x86 BCJ와 stdout 해제 조건 |
| [Python 3.12 lzma](https://docs.python.org/3.12/library/lzma.html) | container/raw 형식, filters, presets, roundtrip과 원시 decoder 설정 |
| [Python 3.12 gzip](https://docs.python.org/3.12/library/gzip.html) | level·mtime과 구현별 출력 조건; mtime=0만으로 도구 버전 간 byte 동일성을 보장하지 않음 |
| [Python 3.12 bz2](https://docs.python.org/3.12/library/bz2.html) | bzip2 압축·해제와 bounded 처리를 위한 API |
| [PyPy 공식 checksum](https://pypy.org/checksums.html) | 조사에 별도 설치한 PyPy 3.11 v7.3.23 배포 파일의 원문 SHA-256 |

XZ의 높은 preset이 짧은 모든 입력에서 가장 작은 결과를 만든다는 보장은 없다. raw 형식은 대응 decoder/filter 조건을 알아야 한다. NVCompact는 source·compressed payload·header 비용과 실제 tail/decoder 호출을 함께 비교한다. 원본 압축 blob도 그대로 후보에 보존한다.

이번 Python 개발 런타임은 CPython 3.12.14다. 엔진의 PyPy 요구와 압축 도구의 interpreter 요구를 구분했다. `/tmp`에 설치한 compiler·runtime 전체는 전달물에 포함하지 않고 버전·출처·확인 SHA를 기록했다.

## 4. C/Rust·링커·ELF 기반

0.1에서 구현해 0.2가 유지한 native 링크 경로의 주요 근거다.

- [GNU ld Linker Scripts](https://sourceware.org/binutils/docs/ld/Scripts.html), [SECTIONS](https://sourceware.org/binutils/docs/ld/SECTIONS.html), [PHDRS](https://sourceware.org/binutils/docs/ld/PHDRS.html): section 배치와 program headers. 특정 script의 실행 적합성은 실제 대상에서 확인한다.
- [GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html): 최적화와 LTO 조건. 일반 ELF object 혼합과 cross-language LTO는 다른 경로다.
- [GCC Developer Options](https://gcc.gnu.org/onlinedocs/gcc/Developer-Options.html): random seed 등 빌드 입력 조건. seed만으로 재현을 보장하지 않는다.
- [Rust Codegen Options](https://doc.rust-lang.org/rustc/codegen-options/index.html), [linker-plugin-lto](https://doc.rust-lang.org/rustc/linker-plugin-lto.html): codegen/LTO와 toolchain 호환성.
- [Rust External Blocks](https://doc.rust-lang.org/reference/items/external-blocks.html): 외부 ABI와 선언 계약. C/Rust 코드가 수학적으로 유사해도 ABI·overflow·panic 의미는 별도 확인한다.
- [System V ELF ABI: ELF Header](https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.eheader.html): section-header가 없는 ELF의 표현. 헤더에 실제 코드가 있거나 self-file 관측이 있으면 임의 stripping을 적용하지 않는다.
- [Python os.memfd_create](https://docs.python.org/3.12/library/os.html#os.memfd_create), [execve](https://docs.python.org/3.12/library/os.html#os.execve): 익명 descriptor 실행과 Linux·libc 의존 조건.

이 경로의 예제는 작은 정수 kernel이다. 체스 엔진·UCI·실전 기력 결과로 대신 인용하지 않는다. [NATIVE-LINKING](NATIVE-LINKING.md)과 [MANIFEST](MANIFEST.md)가 실행 입력을 설명한다.

## 5. 공개 엔진과 대응 소스

엔진 원본·버전·라이선스·정확한 commit 및 대응 검증 수준은 [연구 보고서](../packages/tcec4k-lab/research/ENGINE-ROSTER.md), [현재 입력 metadata](../packages/tcec4k-lab/research/available-artifacts.json), [vendor source manifest](../packages/tcec4k-lab/vendor/source-manifest.json)에 있다.

공식 PGN 17개와 발표 명단 2개를 조사하여 11개 구현을 확인했다. we4k와 후계 STRO4K를 하나로 묶은 10계열 분류는 이 관측과 upstream 계보에 근거한 정리다. 단일 공식 페이지가 모든 과거 제출물의 공개 여부를 인증한다는 뜻이 아니다.

확보 가능한 공개 대표 파일 전체를 압축했다. ice4 6.1.1, STRO4K의 최신 일반·ELF 제출본, 4k.c 9.15.1 등의 정확한 제출 bytes는 확보하지 못했다. 공개 재빌드 baseline과 실제 공개 release artifact도 구분한다. GPL/MIT/0BSD 및 4k.c의 별도 third-party license는 원문을 보존했다.

## 6. 실측·설계·추론의 구분

**실측:** 입력 SHA, 전체 파일 byte 수, 실제 decoder 출력, native/object SHA, UCI command/response, 합법수 oracle 결과, 별도 프로세스 recipe 재현이다. 전체 JSON과 source audit를 보존한다.

**설계:** 한 파일의 표기 계열 portfolio, 두 유망 codec 계열의 match-finder refinement, 원본 fallback, 측정 최소와 accepted 분리, 동일 object를 쓰는 prelink 정리다. 현재 탐색의 한계를 기록하며 전역 최적성을 주장하지 않는다.

**원인이 확인된 관측:** ice4의 동일 256GiB calloc probe 실패와 실제 search crash, pygone의 고정 3초 시간 배분과 2초 probe timeout, Moonfish의 현재 XZ decoder 오류다.

**아직 추론인 원인:** 4k.c와 STRO4K의 첫 실행 실패를 특정 ELF mapping 또는 loader 조건 하나로 단정하는 것이다. 직접 확인한 SIGSEGV와 필요한 주소 공간, 원인 미확정을 구분한다.
