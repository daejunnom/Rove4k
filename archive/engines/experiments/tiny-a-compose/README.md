# One fixed A source/transport composition

The measured complete composition is **5,140 bytes**, SHA-256
`75dc3d610d39bbc0702c6eda219fa0acb4d167c40d3c78e241cf867a33e5a4e7`.
It combines exactly the qualified ownership-query/job-reset source with the
qualified fixed LZMA-alone transport. There is one combination, not a source,
name, resource, flag, preset or codec search. All engine source is the project's
own MIT implementation.

| Complete executable, including prefix/bootstrap/compiler/source | Bytes | SHA-256 |
| --- | ---: | --- |
| Old source + XZ control | 5,207 | `085fcf6bd411a59111aaebbdc6bd59e2687a5c38de2ce28f0ad9643882633e36` |
| Old source + LZMA-alone | 5,163 | `4f1562199786596c4addb36c1b47ecdcee143ca0338e8c986d350fe5639d1f8c` |
| Ownership source + XZ | 5,183 | `9a4911a0364c881e88764dbf41832c051eead2961160cae97136668405cbfa7b` |
| **Ownership source + LZMA-alone** | **5,140** | `75dc3d610d39bbc0702c6eda219fa0acb4d167c40d3c78e241cf867a33e5a4e7` |

The actual result is 23 bytes below 5,163 and 43 below 5,183. The separate
24/44-byte gains are not additive: their sum would predict 5,139. This result
is still 1,044 bytes above 4,096, without an eligibility or strength claim.

## Bounded cost producer

```sh
python3 -B engines/experiments/tiny-a-compose/build.py \
  --control /home/stemxstudio/rove4k-tiny-entry-a-5207-final-20261020-v2/build-1 \
  --ownership /home/stemxstudio/rove4k-tiny-a-ownership-closure-rebuild-20261020/candidate \
  --transport /home/stemxstudio/rove4k-tiny-lzma-entry-first-20261020-r3/attempt-1 \
  --ownership-summary /mnt/c/Users/강민수/Documents/Codex/rove4k-tiny-a-ownership-20261020-evidence/summary.json \
  --out /absolute/new/external-compose-cost
```

Input paths may relocate identical bytes; literal hash admission does not
change. This first-cost experiment intentionally reads the three immutable raw
controls, unlike the separately promoted canonical builder. It copies every
admitted input, its own producer and the exact ownership qualification summary
before use. Unknown inputs fail. The original controls and failures stay intact;
no old canonical recipe expectation is rebound for the cost stage.

The producer re-encodes each complete control twice with the original fixed
parameters and requires exact whole-byte equality. Each repeat strictly decodes
through Python with true EOF/no unused bytes and independently through `xz -dc`
or `lzma -dc` with exit zero, empty stderr and exact bootstrap output. The source
argument and compiler argv are parsed through Python AST without executing them.
Only decoder subprocesses run; no compiler, bootstrap or engine runs here.

The one composition retains ownership's 11,948-byte bootstrap, 10,958-byte C
input, stripped-native identity and fixed `cc -Os -x c - -o x -s` argv. It uses
the exact 77-byte LZMA launcher addressing byte 78 and FORMAT_ALONE/FILTER_LZMA1,
preset 9 extreme, lc=2/lp=0/pb=0, CHECK_NONE, 64MiB dictionary. The complete
13-byte header `0200000004ffffffffffffffff` and coding termination count. It
has no XZ CRC64 field; no equivalent corruption-detection claim is made.

| Retained ownership component | SHA-256 |
| --- | --- |
| Readable source, 24,921 B | `79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed` |
| Compiler C input, 10,958 B | `5ed00fd936cf6228ec7f73d6c1fddd0f18bfe899aff82b5aa695732240079b59` |
| Stripped native, 22,664 B | `6d9a3c192078f22914e17a0332ef2f0dbd134050833c1fceb0ccb221ecba34e2` |
| Bootstrap | `833d83371cd7ddb11a4a940801fe99c4e2ffc11fc2da32482ee264f20883b095` |

The native is ownership's `6d9a…`, not the old source's `d391…`. Reused source
and native evidence is separate from the new compressed stream's exact decode.
Both independent combined encodes and strict/CLI decodes pass. The first cost
is `/home/stemxstudio/rove4k-tiny-a-compose-first-20261020/results.json`, SHA
`e64bb57448049fe95d63859ebb4a04cdac2fd4ab1783f2154a12bcace6686fe3`.
Its `runtime_qualified:false` stays unchanged after later qualification.

## Qualification and canonical boundary

The source/query/job contract is the frozen ownership summary
`671717f28b8efdf6417c2d660aac1a2a9bde0dff3661cb22caff3b4b78090407`.
It explicitly records separate nonalias query scratch, transactional replay,
worker-entry best/reset ownership and the changed broader direct-think contract.
The board/search body remains exact at
`557f9e15c072410fc16c7f3aad8320e904e02574b99b1c625a9047c620b85b57`.
The new composition does not rerun or rename the ownership O2/sanitizer/query
and actual eight-epoch XZ process checks as new ALONE tests.

The transport's input-path revision final receipt
`2a07487768738bb9cd87f24f27a0e41b084cce7dd12322d90435a2e5c4975219`
was explicitly frozen before canonical editing. It removes the transport
adapter's future dependency on mutable canonical A inputs while preserving
its earlier execution record. The original 5,207-byte nine-file canonical and
Git archive, all three controls and their proofs remain outside Git.

The separate `engines/compact/tiny-entry-a/` canonical source/recipe now produces
the selected composition directly from ordinary tracked source/helpers. It does
not execute this experiment or read its historical controls. Its fresh named
source archive, two extracted builds with independent repeats and new selected
whole-file quit/EOF sessions are separate receipts. No general engine matrix,
many-core scaling, fair NPS study, strength match or CI success is implied here.
