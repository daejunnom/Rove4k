# One fixed C/E complete-file cost stage

This stage consumes the exact C11802B/`89a217a6…` and E12192B/`25c6bff2…`
shipping sources. Their different full native images were already reproduced
twice: C26344B/`edf285f8…`, E26328B/`bd4080a4…`. They are not equated with
the old C/E images. The original38-file rejection and suffix41-input native
stage remain immutable. The suffix FINAL receipt is22625B, SHA-256
`d7c43218db2a37fcb21bf4fe2fd8dca2cfc09ba00f97f83d0d40cd3443e0f678`.

Root separately reviewed the actual C suffix and E direct metadata classes.
Only after those reviews was this one cost stage authorized. It performs no
compiler, native, bootstrap, engine, DEV, runtime, game or benchmark execution.
It changes no submitted source, alias, flag, profile, codec parameter or model.

`cost_recipe.json` closes over the frozen42 ordinary sources and the three
new production files, giving45 ordinary inputs. This document is an additional
maintenance source. Thirteen native-stage artifacts and six baseline-stage
artifacts are explicit, full-hash-pinned reuse inputs. The producer verifies
their identities and copies them into its new external output; it does not
claim artifact-free normal generation or silently resolve maintained paths.
The baseline whole files were already independently produced twice from
their ordinary source closure. No extra baseline or native build is run here.

For each family the producer independently creates exactly two complete
packages from the same frozen source, original bootstrap and75B launcher.
It uses the unchanged source-literal helper and original XZ/LZMA2 settings:
preset9 extreme, lc3/lp0/pb2 and CRC64. All bytes of the launcher, XZ headers,
compressed bootstrap+C payload and footer are included in the whole cost.
No alternative literal, name order, compression setting or candidate is tried.

`cost_decode.py` then strictly reads each produced whole file without running
it. It requires the exact75B prefix, one complete CRC64 XZ stream, EOF with
no unused bytes, and bootstrap bytes equal to the exact generated script.
The decoder does not infer encoder preset/lc/lp/pb from the stream; fixed
encoder settings are enforced separately by the producer and pinned recipe.

AST inspection requires one `subprocess.Popen` assigned directly to `p`,
with a literal argv equal to the original family compiler. It requires one
`p.communicate` call with one positional argument and no keywords. C stdin
is recovered only from literal bytes or an argument-free literal-str
`.encode()` and must equal the pinned candidate source byte for byte.
There is no `eval`, bootstrap execution or native compilation. Other Python
structure/bindings remain controlled by the exact original template bytes;
the AST checks are a narrow input-recovery proof, not general Python safety.

Two independent packages must agree as whole bytes and as decoded bootstrap.
Equal or larger cost is recorded and stops; gains are reported for root's
later functional and maintained-promotion decisions. A gain supplies neither
runtime acceptance nor4KiB acceptance. Original full-native identity failures
and the distinct new image hashes remain explicit in all receipts.

```sh
ce_experiment='/mnt/c/Users/강민수/Documents/Codex/rove4k-engines-af-20261020/engines/experiments/tiny-storage-ce-current'
python3 -I -B "$ce_experiment/cost_stage.py" --native-prior /home/stemxstudio/rove4k-tiny-storage-ce-current-suffix-20261020 --baseline-prior /home/stemxstudio/rove4k-tiny-storage-ce-current-native-20261020 --out /home/stemxstudio/current-ce-fixed-cost-new
```

All arguments are absolute. The new output must remain outside Git and both
prior outputs. All produced files and receipts remain outside Git. Future
functional checks, normal-producer integration, CI and promotion require
separate scope; this cost stage does not perform them.

The single authorized run completed successfully on 2026-10-20. Its external
output is `/home/stemxstudio/rove4k-tiny-storage-ce-current-cost-20261020`.
The original compiler/profile, bootstrap, launcher, aliases and XZ settings
were held fixed. Exactly four packages were produced: two for C and two for E.

| Family | Old compact C | New compact C | Source saved | Old complete file | New complete file | Whole saved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 12224 | 11802 | 422 | 5687 | 5603 | 84 |
| E | 12641 | 12192 | 449 | 5679 | 5595 | 84 |

For C the complete file is75B prefix+5528B XZ payload. Both attempts have
SHA-256 `67e1e8d363872b0be6709f791e602f8c8f51b2d81f9e8c0c0ce0e13e8b2cea71`.
The12877B restored bootstrap has SHA-256
`9ef7d13c5341a3f3e0d0b0e2c12c5aaf78066703d219c57e05f9cb91867f8a7e`.
Both strict decoder/AST receipts have SHA-256
`4201ff81c17d33e5a4cfd3db31dba2e459335cb2d0808c7ed903aa8d85ce8202`.

For E the complete file is75B prefix+5520B XZ payload. Both attempts have
SHA-256 `65da1c44dad0c04c0e542cbddb965f4b1e0384e5e87e96c09caa4fec6a20f965`.
The13257B restored bootstrap has SHA-256
`37e75a8342ae2444c08669d4b8f0aa4d07f8d479612ae1d1ba456ddd860b16d4`.
Both strict decoder/AST receipts have SHA-256
`26847248d52d7752664ca93302584aa5d6ebac9a76c81c2bc91cf86e43139ae2`.

The14837B raw `results.json` has SHA-256
`340225c97db88812b284e4b6a367abde158ff4d9c670e1de1218ddf248ffee43`.
It records all45 ordinary inputs,13 native-reuse inputs and6 baseline-reuse
inputs. The two independent complete byte sequences and restored bootstrap
bytes agree for each family. Each of the four actual package bytes passed
the strict XZ and AST compiler-stdin check against its exact candidate C.
Native compiles, compiler runs, bootstrap runs, engine runs, DEV runs and
runtime tests were all zero. This phase provides cost and input-restoration
evidence; it does not establish general ABI/runtime equivalence or normal
producer acceptance. The distinct new full native images remain C`edf285f8…`
and E`bd4080a4…`. Both complete packages remain larger than4096B.
