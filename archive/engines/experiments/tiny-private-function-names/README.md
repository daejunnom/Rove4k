# AST-bound private static-function names

This experiment starts from ordinary B/C/E sources at Git commit
`71a0791c1a2a52c42537ef5e39788f617e1f1de8`. It reproduces each maintained
shipping C input through its existing preprocessing, counter removal and fixed
alpha/storage stages before changing any function name. Maintained sources,
shared helpers, NVCompact, root documents and Git state are not modified.

The supplied PR12 size analysis is reference material. Its older candidate
results and implementation recommendations are not an admission for these
inputs. No external chess-engine implementation is imported or vendored.

## One conservative source policy

`rename.py` considers only main-file static function definitions with internal
linkage. It records the complete same-function declaration set, including
forward declarations, and only direct-call `DeclRefExpr` references confirmed
by the real Clang AST. Every edit is an exact physical name byte span. A lexical
scan rejects same-spelled code consumers outside that set; it never performs
the transformation. Thus B's `first`/`result` and E's `first`/`piece` are
conservatively retained because they also name local objects.

Non-static global functions, main, libc/external names, types, members,
directives, strings and comments remain unchanged. Address/argument/indirect
function uses and attributed functions are excluded. In particular all three
`work` callbacks and C's constructor `tiny_eval_init` remain unchanged. Source
function-name observers, symbol/image introspection and inline assembly are
excluded. Protocol strings such as `go` are not C-symbol lookups and retain
their exact bytes even when the bound function changes spelling.

The fixed alias policy visits eligible old spellings in ASCII order and uses
the first globally unused short ASCII spelling. Raw and phase-two source
words, keywords and all observed header/source AST spellings are reserved.
There is no native-guided alias discovery or alternative mapping sweep.

The candidate is reparsed with the same real headers and arguments. A
source-preorder signature compares cursor kinds, names, types, valid declaration
storage fields, referenced declaration identities and child counts. Main-file
declarations and macro definitions use stable ordinals because their USRs can
contain source offsets. This is a structural/binding record, not serialization
of every semantic AST property; exact bounded name edits and opaque equality
are complementary restrictions. Native observation is a separate gate.

## Source preparation and tools

`prepare.py` reads fixed Git blobs and freezes 14 unique ordinary input files
outside Git. It invokes the existing real preprocessor and produces only C,
AST maps and source receipts. The fixed external tool installation is
libclang 18.1.1 with official Ubuntu Clang 18.1.3 resource headers. Both
installation receipts are checked. These receipt checks alone are not a hash
authentication of every loaded binding/library/system-header byte.

The Windows-managed worktree uses a Windows `.git` reference, so WSL uses an
explicit read-only Windows Git executable. No Git configuration is changed.

```text
python3 -B prepare.py --repo <WSL-checkout> \
  --git-program '/mnt/c/Program Files/Git/cmd/git.exe' \
  --git-repository <Windows-checkout> --out <new-external-directory>
```

The selected source-only receipt is
`/home/stemxstudio/rove4k-private-function-names-prepare-v4-20261020/prepare.json`,
SHA-256 `556bdff95f1e208141cb214e5866794beff695685ac1c05d8d6998d1adc29b9e`.
The actual maps and declaration/reference offsets are in each family's
`mapping.json`. Twelve focused real-AST fixtures passed; no native compiler or
engine is executed by the fixture runner.

| Family | Functions / edits | Shipping C before → after | Candidate SHA-256 |
|---|---:|---:|---|
| B | 24 / 95 | 13,071 → 12,678 | `fe8ef598de236d93738467b4aeaa41d6dff4128dcd7a03f0642431e85fb9957d` |
| C | 24 / 82 | 12,224 → 11,868 | `2bac34e9bd30d32551714772112c78c91ff99167506abc2e76cb4f673b499307` |
| E | 25 / 83 | 12,641 → 12,246 | `b54d840799ba0c63ae4adb4c2e90f62c3b10f443ff83ef05d1a9585d3cc9d95a` |

Earlier failed source-only attempts remain external: Windows worktree path
resolution; querying Clang storage class on an unsupported macro cursor; and
using offset-bearing main-file macro USRs without ordinal normalization. The
fixes address those causes. AST errors and missing real headers are not ignored.

## Actual native and original-codec observations

After explicit root authorization, `native.py` compiled each exact candidate
once using its original stdin compiler command. It reused existing baseline
natives only after full SHA/length verification. There were three candidate
compiles and zero baseline compiles, codec calls or engine executions in this
stage. All physical file-byte changes, section headers/data, PHDRs and ELF
headers are recorded without a preaccepted difference mask.

**Full native equality is false.** All program headers, allocated code/data,
dynamic symbols/strings and relocation headers/bytes are exact. The allocated
GNU build-ID descriptor differs. The only other changed loaded byte is offset
40 in `e_shoff`. B/C have 21 different loaded bytes; E has 20 because one byte
of its 20-byte build-ID descriptor happens to match. Nonallocated symbol/string
and section metadata also change; the `.shstrtab` data is exact but moves.

Root admitted this observed metadata class for the cost experiment. It does not
make the allocated note equal, prove behavior for programs observing their own
ELF metadata, or add any exception to a shared/maintained admission guard.

`whole.py` then encoded each source once with the unchanged XZ/LZMA2
9-extreme/lc3/lp0/pb2/CRC64 recipe and original 75-byte prefix/template.
Python strict EOF/trailing checks and independent `xz -dc` restored the exact
bootstrap. Static AST checks restored both the exact C input and actual Popen
compiler argv. Neither the wrapper nor restored native was executed.

| Family | Native before → after | Original-codec whole before → after | Whole saving |
|---|---:|---:|---:|
| B | 26,496 → 26,424 | 5,851 → 5,779 | 72 |
| C | 26,424 → 26,384 | 5,687 → 5,615 | 72 |
| E | 26,408 → 26,360 | 5,679 → 5,603 | 76 |

These are single actual fixed-candidate costs, not independent repeated
reproduction or runtime qualification. Source/native/whole artifacts and raw
readelf output remain outside Git. All candidates exceed 4,096 bytes. They
are not maintained promotions or TCEC acceptance.

## Actual static-plus-locals and fixed-codec composition

After separate root authorization, `compose.py` freezes the independent local
allocator from `tiny-scope-names/rename.py` at raw SHA-256
`02ca17d1c251945f1c021e3482272ef891485c2227a90b4712a36b987d29f08b`.
It calls that owner's unchanged generic API on the actual static-only sources;
it does not implement a second local allocator. The earlier `9b1f...` API
composition is preserved as superseded and was never compiled or encoded.
The final API records macro bodies through exact token-kind/spelling shapes
without querying undefined declaration attributes on preprocessing cursors.

`gate.py` compiles each final combined source once. All three complete native
files, including metadata, are byte-identical to the corresponding static-only
native. This gate admits no note/header exception. It does not change the
separate false full-native-equality result relative to maintained originals.
`bootstrap.py` then reconstructs and statically checks exact C/compiler argv
artifacts without running or encoding them.

The codec owner measured each actual combined source once with its original
XZ recipe, then twice with the one declared LZMA1-alone 9-extreme/lc2/lp0/pb0,
BT4 profile and 77-byte prefix. Nice lengths are B32, C64 and E32. Both complete
LZMA files per family were equal and strict recovery preserved source and argv.
No savings in this table are sums of independent candidates.

| Family | Combined C bytes | Actual combined original XZ | Actual combined fixed LZMA | Saving from maintained | Remaining above 4,096 |
|---|---:|---:|---:|---:|---:|
| B | 12,220 | 5,619 | 5,558 | 293 | 1,462 |
| C | 11,455 | 5,459 | 5,395 | 292 | 1,299 |
| E | 11,803 | 5,455 | 5,400 | 279 | 1,304 |

The exact combined source pins are B
`daa9ca6e03260320c13a0a551a0c2586ed53d24d49ebba74f87b57b57814ba9f`,
C `f70cd11e8cdd1a3d2503255189e80ca9070cf310777d2ff8a89ec9beff732f82`,
and E `acd417f903ada227092b0ba371d6ad960ab80b4925ab64633b9b8a2774a9b3aa`.
The codec owner's external `results.json` is at
`/home/stemxstudio/rove4k-tiny-source-codec-BCE-static-locals-20261020/`,
SHA-256 `2024bcef7ddef6dc24a5f67a5cf8260c12d9600e2f595ecb8ecb89a4fe22f4d0`.

Our native compile count is six: three static-only observations and three
combined full-byte gates. We performed three static-only XZ encodes. The codec
owner separately performed three combined XZ and six combined fixed-LZMA
encodes. Neither owner ran a bootstrap, restored engine or game in this work.
There is no runtime/strength/4KiB acceptance or maintained promotion.

LZMA-alone has no container checksum. Exact analysis recovery does not preserve
XZ CRC64's corruption-detection contract. Source/binding checks, the observed
native metadata class, full-byte local-name gate, packaging reproduction and
runtime acceptance remain separate claims.
