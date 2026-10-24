# Fixed B/C/E shipping identifier and resource policy

This experiment applies one reviewed spelling policy to the maintained B6219,
C5947 and E5899 controls at `829f27d1338be6fd9f3f2a270239bdc6e3d89a27`.
The ordinary entries, readable engine bodies, DEV forms, compiler arguments,
resources, bootstrap, shell prefix and codec settings remain the controls.
Only the specialized shipping C receives the additional lexical stage.

The first actual measurement and the separate selected-wrapper runtime stage
completed successfully. Exactly two fresh sessions per family, six in total,
bind the smaller whole files to the unchanged native images.

| Family | Control shipping C | Candidate shipping C | Source reduction | Control whole file | Candidate whole file | Whole reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B | 15,566 | 13,606 | 1,960 | 6,219 | 5,955 | 264 |
| C | 14,206 | 12,526 | 1,680 | 5,947 | 5,723 | 224 |
| E | 14,352 | 12,641 | 1,711 | 5,899 | 5,679 | 220 |

All sizes are bytes. Each candidate's complete native ELF equals the original
full native SHA-256, including the build-ID note and all non-allocated sections.
The source, native and complete compressed file independently reproduce twice.
All three complete files still exceed 4,096 bytes. No submission eligibility,
strength, throughput, target-machine performance or many-core result follows.

## One fixed policy

[`policy.json`](policy.json) contains all 89 old/new pairs, the exact three
shipping input identities, per-name occurrence counts and candidate identities.
The pairs were fixed after the read-only ownership audit, before compilation.
They are applied together without name trials, codec trials or a search loop.
The same mapping is used for all three families; a family can use a subset.

Old spellings use fixed ASCII ordering. Fresh two-character aliases are drawn
from the fixed `z*`, then `y*` sequence and do not reuse any spelling from the
canonical or shipping sources, including comments, literals and directives.
There are 82 used pairs in B, 73 in C and 70 in E. Examples are:

| Original | Fixed alias | Owned role |
| --- | --- | --- |
| `Board` | `za` | private typedef |
| `Entry` | `zb` | private typedef |
| `Exchange` | `zc` | B private typedef |
| `Worker` | `zd` | private typedef |
| `bestmove` | `zj` | automatic search variable |
| `continuation` | `zw` | owned Worker member |
| `created` | `zz` | automatic startup variable |
| `data` | `zA` | owned Entry member and automatic parameters |
| `moves` | `z1` | automatic arrays and parameters |
| `score` | `yl` | owned Worker member and automatic variables |

Functions, global objects and static-storage objects retain every spelling.
If a spelling also belongs to one of those roles it is excluded everywhere.
Headers, libc/pthread/atomic/SIMD names, strings, character literals, directives,
external `timespec.tv_sec`/`tv_nsec`, `main` and C's constructor are preserved.
`Move` is deliberately excluded: the retained `MOVE` macro body consumes it,
while the lexical rewriter leaves directive bodies opaque. The audited sources
have no direct asm, self-name, `offsetof`, string-based symbol lookup, token-paste
or stringification consumer requiring a new exception to this policy.

The two fixed resource substitutions affect code identifier tokens only:

| Token | Fixed literal | Occurrences in each family | Source reduction |
| --- | --- | ---: | ---: |
| `WORKERS` | `2` | 7 | 42 |
| `TT_BITS` | `18` | 3 | 15 |

`PLY` remains `PLY`: its value `128` has the same three-character length. The
resource macros remain defined by the unchanged compiler arguments or retained
source directives. The actual preprocessor must still report values 2, 18 and
128. The policy changes no resource value, array bound or startup allocation.

## Closed inputs and exact gates

`control/` preserves the original nine ordinary source files for each family,
plus eight fixed generation, lexical and runtime helpers: 35 files total.
[`recipe.json`](recipe.json) pins each normalized file and records the original
working-byte identity and any CRLF-to-LF normalization separately. The preserved
historical `fresh.py`, README and verifier files are archival inputs; the new
producer executes only its explicitly described call graph. No live maintained
entry or external historical report is a build dependency.

```sh
python3 -B engines/experiments/tiny-alpha-portfolio/build.py \
  --out /absolute/new/alpha-first-cost
```

The output must be new, absolute and outside a Git checkout. The fixed Linux
x86-64 controls are bound to their existing complete-file and native identities;
a different toolchain which cannot reproduce them is reported as a failure.
The observed first measurement used GCC 13.3, GNU ld 2.42, Python 3.12.3 and
XZ/liblzma 5.4.5. There is no install or system-configuration operation.

For each family the producer performs the following bounded work:

1. Run its unchanged preserved builder. Both shipping and unchanged DEV source
   and native forms reproduce independently twice, along with the original
   complete wrapper. The old expected identities remain mandatory.
2. Apply the fixed pure policy. Exact input, output and per-token count pins,
   injective fresh aliases, two independent lexical applications, and an opaque
   directive/literal/comment scanner must agree. DEV and readable bytes never
   enter this transformation.
3. Use the actual compiler arguments with only the final `-o x` removed for
   preprocessing. Baseline and candidate final `-dM` definitions must agree;
   resource values must be 2/18/128. No target alias may already occur in the
   actual expanded baseline or final macro names.
4. Reverse only the 89 identifier aliases in the full candidate `-E -P` output.
   It must equal the full original output byte for byte, including whitespace,
   strings and numeric spelling. Numeric 2/18 values are never reversed. This
   strict gate does not depend on a heuristic token compactor, and final macro
   definitions are not presented as a complete transient macro history.
5. Compile both candidate attempts. Each complete native must equal the old
   full native SHA. A mismatch stops that family before candidate compression;
   there is no build-ID exception, allocated-section-only comparison or relaxed
   object-identity guard.
6. After both native gates pass, independently create two complete files with
   the unchanged source literal, bootstrap, 75-byte prefix and fixed XZ LZMA2
   preset 9 extreme / lc3 / lp0 / pb2 / CRC64 recipe. No whole-file gain stops
   that family without an engine run.

Every source, compiler output, diagnostic, full PP output, final macro dump,
artifact and incomplete result stays in the external output. The command never
launches an engine. Its `complete` field means the bounded measurement campaign
finished; family status and the separate runtime record determine qualification.

## Actual measured identities

| Family | Candidate whole SHA-256 | Original and candidate full native SHA-256 |
| --- | --- | --- |
| B | `121e7fa70894df10fb945c1369cbfd3459000b2e7276749e2a3789ea412868d3` | `221a865e2712cb3e704128e0ae8353edd358343f564fe53093040f6515d522ec` |
| C | `76662acd5eac4e907a5e29bacf8f252118c9bc97bf3aec0dc890bd815c6ecac0` | `c948e31aea9f413614881b8e8e6060e5aa70314dd84b2d9b544e3f20edb99df2` |
| E | `83e8e7f22f24e3161268554ab4c5ff7ad7f6007822ea6892e6fae68670e80fb4` | `5429f2d80521f775bac6802ec4940e8e0ff1b344464ed8e9a0629ba6650eb675` |

The immutable first-cost report is
`/home/stemxstudio/rove4k-tiny-alpha-portfolio-first-20261020/results.json`,
SHA-256 `e0527b2c9c566150791f6095346694961b81dc007fb9f89e1c135755ab81a1d8`.
It records actual control DEV reproduction, strict header gates, both candidate
native hashes and both complete files. Original source-space calculations and
the independent ownership/header-gate code reviews are separate evidence.

Historical B SEE/singular, C SIMD/layout and E 21-coefficient ordering/core
qualification can be reused through the identical full native images. Those
core campaigns were not rerun here. The new source spelling, package bytes and
the restored-image sessions have their own fresh receipts. No canonical
promotion, workflow dispatch or CI success is implied by this experiment.

## Selected-wrapper runtime qualification

[`runtime-pins.json`](runtime-pins.json) fixes the exact first-cost receipt,
four executed producer inputs, 35 original control files and each candidate's
two physical attempts and selected bytes. [`verify.py`](verify.py) checks both
the owned control closure and the first-cost frozen closure before admission.
It cannot silently accept a new cost receipt or regenerate expected hashes.

```sh
python3 -B engines/experiments/tiny-alpha-portfolio/verify.py \
  --build /absolute/copy-of-the-pinned-first-cost \
  --out /absolute/new/alpha-selected-runtime
```

The runtime adapter admits the preserved first-cost report with the literal
SHA above. The two observed producer attempts have the same artifact bytes.
A new producer invocation writes path-dependent report metadata; its new report
is not automatically substituted for this reviewed receipt. Retain the original
report and its frozen inputs when copying the measurement to another location.

The original 35 control files and first-cost outputs are not changed. A separate
execution mirror keeps the original verifier and shared helpers byte-identical.
Three explicitly derived runtime-only recipes change exactly five expected
representation fields: source bytes/SHA, whole bytes/SHA and bootstrap SHA.
Original native, readable and DEV expectations remain fixed. The original and
derived recipe hashes and all five changes are written to the runtime report;
these derived configurations are never presented as original producer recipes.
Provenance explicitly limits historical reuse to the exact old native/core.

Each original verifier is called once and creates its existing quit and EOF
sessions. The adapter adds no independent engine launch, retry, game, benchmark
or broad core campaign. Each selected source wrapper performs its normal fixed
startup compilation; the adapter performs no separate producer compilation,
preprocessing or recompression. Existing bounded verifier helpers own each
session and cleanup.

All six actual sessions passed the unchanged selected checks:

- Minimal UCI startup and exactly three initial TIDs, with persistent thread IDs.
- Full `/proc/<pid>/exe` SHA equal to the original native, unlinked private image,
  private restoration path absent, and no live compiler/helper after startup.
- Exactly one legal white-zero-clock and black-zero-clock result, plus bounded
  bare `go` using the existing finite default.
- Observed active clocked work before quit/EOF, exactly one legal closing result,
  physical process disappearance and joined output readers.
- Original cost and owned control inputs, then all execution-mirror inputs,
  rechecked against their original or explicit derived configuration pins.

Cancellation causality remains `unproven`; process-level activity and the
receipt/exit ordering do not prove which event caused completion. Bare-go wall
times are bounded lifecycle observations, not comparative performance results.
The preserved verifier's existing small oracle self-checks also ran. Full chess
rules, model, SEE/singular and SIMD campaigns remain explicit exact-image reuse.
DEV had fresh unchanged source/native reproduction in the cost stage and no new
DEV runtime session in this stage.

The fresh runtime result is
`/home/stemxstudio/rove4k-tiny-alpha-portfolio-runtime-20261020/results.json`,
SHA-256 `5fbd18434187219b571dfb962058298616d560c671485c32d320a368607df427`.
It records `complete: true`, `fresh_sessions: 6` and successful final input
rechecks. The original first-cost report retains its historical
`gain_native_exact_runtime_pending` statuses; it was not rewritten to claim this
later execution.
