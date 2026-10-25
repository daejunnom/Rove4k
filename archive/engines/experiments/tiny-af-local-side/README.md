This single A candidate is rejected for complete-file size: **4,846 → 4,853
bytes (+7)**. No engine or wrapper was executed, and no further variant was
attempted. The maintained A/F sources and helpers are unchanged.

The six fixed expressions interpret only the local mover/kind as own-side
positive. Absolute mailbox storage, moves, HCE, FIDE keys, reversible path,
history/continuation/correction domains, search, clock and worker lifetime are
unchanged by the declared edit. `side.py` pins both readable and final shipping
inputs, verifies the fixed identifier relationships within those expressions,
checks their function ownership and unique occurrence, then proves the exact
inverse and unchanged byte complement. No AST, preprocessor, lexer, alias
allocator, macro or broader transformation is used.

| Measurement | Reused maintained control | Actual candidate |
|---|---:|---:|
| Final shipping C | 9,910 | 9,891 (−19) |
| Native ELF | 22,672 | 22,672 |
| Whole file, including 77-byte prefix | 4,846 | 4,853 (+7) |

The six readable expression lengths differ by −22 characters; the fixed final
aliases make the actual shipping difference −19 bytes. These are separate
measurements. The candidate native image is **not** byte-identical to the
control, despite equal size:

- Control native SHA-256:
  `84ce7fd107783474af8f39aeec7b95c244d475ab797eefd2627b9741b265210a`
- Candidate source SHA-256:
  `ca13ea9e3a0c58ca8e06d8beaf1cbf5c4c6e90e26d575171311740bb9c274a00`
- Candidate native SHA-256:
  `4c1e14ac21be206ae3d25e7f7058b47fe7acb7f26fe50d4163a9db88da2ec208`
- Candidate whole SHA-256:
  `3cb2927eac7651992f90f92f29c833aaa0926a8f425aae4ff5fc6bacb2b317b7`

`build.py` accepts existing explicit pinned controls rather than regenerating
or copying them. It preserves its actual ordinary producer externally, reads
the maintained canonical/template only under their exact input pins, compiles
the candidate once through `cc -Os -x c - -o x -s` with stdin in a new private
cwd, and compresses its bootstrap once. The codec is the unchanged A ALONE
LZMA1 preset 9 extreme, lc2/lp0/pb0 and 64MiB dictionary; no nice-length or other
setting is changed. The exact 77-byte prefix counts toward the whole file.

Strict single-stream decoding checks the ALONE header, end of stream and zero
unused bytes. Exact-template binding, direct raw-single literal recovery and
the fixed literal command recover the source/argv without Python AST, eval or
bootstrap execution. ALONE has no container checksum. This is a bounded exact
restoration check, not general Python safety or runtime qualification.

The only actual campaign was:

```sh
python3 -I -B engines/experiments/tiny-af-local-side/build.py \
  --baseline /home/stemxstudio/rove4k-tiny-scope-names-ABCE-first-20261020/A \
  --canonical /absolute/checkout/engines/compact/tiny-entry-a/engine.c \
  --template /absolute/checkout/engines/compact/tiny-entry-a/bootstrap.py.in \
  --out /home/stemxstudio/rove4k-tiny-af-local-side-A-first-20261020
```

The actual output tree contains `main.c`, `native/x`, compiler stdout/stderr,
`bootstrap.py`, `x`, `results.json` and the actual ordinary producer snapshot.
There was one candidate compile and one compression, zero control compiles or
control copies, zero F candidates, zero AST/preprocessor/engine/wrapper runs,
zero games or benchmarks. The command finished with exit 0; no owned handle
remains. No second repetition or new source/flag/codec/alias variant was run.
The failed size result does not imply a rules/search/runtime PASS, canonical
promotion, tournament acceptance or 4KiB eligibility.
