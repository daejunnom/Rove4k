# Maintained minimal C entry

`engine.c` is the readable canonical program for the selected **5,687-byte** C
entry. It contains both shipping and development branches. Compact C, native
ELF, bootstrap and complete executable are generated from this source and the
fixed recipe. Normal regeneration needs no experimental directory, historical
report, generated artifact, executable or network input.

The source shares a nullable-text legal move query between first-move fallback
and text parsing, reuses its already-made child during transactional replay,
resets worker best in think, and shares pending between startup arrival and the
existing wait. The Board/rules/AVX2 evaluator/TT/search prefix before think is
unchanged from C5723. Shipping Board.v remains absent; development retains its
diagnostic state. Initial stopped is one before the first GO, and direct
pre-stopped think resets best. These private changes have their own C proof.

The file remains **1,591 bytes above 4,096**. This selection does not establish
4KiB eligibility, playing strength or many-core scaling. The exact-byte domain
is Linux x86-64, Ubuntu 24.04.4, GCC 13.3.0, binutils 2.42, glibc 2.39,
Python 3.12.3 and xz 5.4.5. A different compiler or encoder result fails the
identity gates rather than silently changing the selected artifact.

## Fixed build and ordinary source closure

From an ordinary checkout on the recorded Linux toolchain, including WSL Ubuntu:

```sh
python3 -B engines/compact/tiny-entry-c/build.py --out /absolute/new/C-build --dev
```

The output must be a new absolute directory outside any Git checkout. The
single shipping profile fixes two search workers, one controller, TT bits 18
and PLY 128. `--dev` also builds the separately pinned diagnostic source; it
does not choose a different shipping profile. Shipping compiler arguments are:

```text
cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -mavx2 -DDEV=0 -x c - -o x
```

DEV changes only `-DDEV=0` to `-DDEV=1`. The unstripped ELF, explicit AVX2
target, bootstrap compiler invocation, 75-byte launcher and XZ/LZMA2 preset 9
extreme (`lc=3/lp=0/pb=2`, CRC64) remain unchanged. All launcher, bootstrap,
source and restoration bytes count toward the complete file.

The seven normal helper inputs are `engines/scripts/specialize.py`,
`minify.py`, `rename_c.py`, `fixed_shipping_alpha.py`,
`engines/compact/tiny-a/stitch.py`, `pack_stream.py` and this folder's
`shipping_alpha.py`. The builder authenticates and copies their LF-normalized
bytes before import. The new local helper embeds the exact C composition
policy `9ac6fdd907a114d6748268c5777e5ee3fa54a53ce56ae07bd1d7fae37d1202c5`.
It uses the existing pinned shared generic rewrite, logical scanner and byte
binding functions with the caller's pinned lexer and readable C. It never
calls or widens the old shared transform admission. Shared B/E source domains,
all 89 aliases, protected symbol spellings and WORKERS/TT literals stay fixed.
DEV bypasses shipping counter removal and alpha rewriting.

Each builder invocation independently specializes, compacts, compiles and
packages twice and requires every source/native/bootstrap/whole identity below.
The optional DEV source and native must also reproduce twice. The named fresh
closure contains eighteen ordinary files, including the two unchanged verifier
helpers. `fresh.py` uses an isolated temporary Git tree/archive and two source
extractions without changing the calling checkout's index or repository:

```sh
python3 -B engines/compact/tiny-entry-c/fresh.py --out /absolute/new/C-fresh
```

## Selected identities

| Form | Bytes | SHA-256 |
| --- | ---: | --- |
| Readable C | 26,692 | `15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b` |
| Shipping C | 12,224 | `20f06b6ed9ada03db6f8719f05ecdf9cb52802ab0a1acc8999627999db899046` |
| Native ELF | 26,424 | `cc67f03a58f350a1bd0ab1f07e774c13cf8f6b628b469107834da6f505f7cf00` |
| Complete file | 5,687 | `0fc91619c63cd0fe163abc4825cc7badff3e8b19e4e88ad67cfec165223ab575` |
| Bootstrap | 13,299 | `f3f9ab2ce26f317d4c6e9d6c2ba7527fea88671297341a3cda008e613ca78047` |

New DEV source/native hashes are
`c6497c472b243b03cb19ab727b42a189a8be556d818e39d9bf7b74684daaa140` and
`5d481d97e7213d9ddad3d0419c0895176be726bfe4e9a1b18ef6c963ba43de7c`.
They were generated twice independently from the exact qualified readable and
unchanged compiler. They are new identities, not the old C5723 DEV files.
This source/native binding is not a DEV runtime test.

## Functional evidence and limits

The C-specific composition proof final index is
`f3278861a28f37adfb2aead6f7ce2f8558caf261ff77f8f68c70380d996e0641`.
Actual old/new DEV0 O2 and ASAN+UBSAN query forms pass independent legal sets,
Board/hash/reversible-path/raw HCE and SIMD/scalar checks. Five controlled
startup schedules cover early/late arrivals and partial pthread creation.
Four actual GO epochs observe pending completion before root reuse. The
unchanged SIMD evaluator is checked through actual parity and native
disassembly. The changed C paths use their own evidence, not inherited A runs.

Two original selected whole wrappers, quit and EOF, pass eight legal GO results,
the exact restored native image, stable three-TID startup, FDs 0/1/2, no live
restoration helper after initialization, one closing result and physical
reader/process/private-path settlement. Their source/runtime receipts are
metadata in the recipe, never normal generation inputs. The original invalid
query fixture abort is preserved and distinguished from the subsequent four
passing query forms. The unchanged prefix and selected byte identities connect
this ordinary source to that bounded proof.

The unchanged selected verifier can check a newly regenerated file:

```sh
python3 -B engines/compact/tiny-entry-c/verify.py --build /absolute/C-build --out /absolute/new/C-runtime
```

Its actual quit/EOF sessions include clocked and bare GO, legal result checks,
active search before close, native identity and physical cleanup. It does not
require optional ordinary-TCEC commands from the minimum 4K interface. Clocked
physical exit does not prove cancellation causality. The epoch fixture covers
early abort/depth-zero fallback, not deep iteration publication, general race
freedom, join failure, strength or final target resource behavior.

The old C5723 ordinary source closure and complete shipping/DEV artifacts were
preserved and rebuilt from two independent source extractions before this
update. Their native and DEV identities are ancestry only. The new ordinary
source reproductions and selected verifier runs have separate promotion
receipts outside Git; generated outputs, archives and logs stay outside Git.
