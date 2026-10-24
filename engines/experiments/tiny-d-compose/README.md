# Qualified protocol D + dedicated fixed restoration

This experiment composes two already qualified, project-owned changes and
measures the actual complete result. It changes neither `tiny-protocol` nor
`tiny-d-loader`, the canonical engine, codec, loader body, linker script, pool,
TT, worker count or search. There is no new codec or preset comparison. Neither
combined result is a 4 KiB entry.

## Exact admitted lineage

The protocol campaign is frozen at
`/home/stemxstudio/rove4k-tiny-protocol-20261020/results.json`, SHA-256
`17d7e72ecb66440d84e96dcb2f7051873e2efcb3ee2d31df3c0fab4ecee52275`.
Its original D build report hash `e49edad3...` matches the qualified original
8,540/8,928-byte controls. The external qualification `index.json` is copied
and checked against the campaign identity. The frozen protocol transform
`459516ac...` is reapplied to the frozen original `runtime.c`: the result must
match the candidate byte-for-byte. All other native source files must be
identical. Both scalar/HQ compiler invocations must match their original
controls after only declared source-prefix and output-path substitution.

| Protocol input | Native bytes | Exact SHA-256 | Entry |
| --- | ---: | --- | --- |
| Scalar | 8,476 | ba2d42473ca25a944b85da18f74f32eae18e68112010948a0e7c2dc0c69a7c5c | 0x401f89 |
| HQ | 8,864 | 09917666d5862c4f17ed77e33453000f608a7d83aa47f16f8726a063ec5f31ce | 0x4020c6 |

The unchanged archived v3 builder rejects both new inputs with `ValueError:
unknown TinyD image bytes: <form>`. Those rejection records and the original v3
source are preserved. Composition admission is a separate explicit allowlist;
it never changes expected hashes from observed output. Independent layout
review confirmed that RX lengths and entry values change, while the exact
three-segment shape, RX base/page span, BSS address/175,092-byte extent, both
guards and non-executable stack stay identical. A 64-byte file saving moves
entry by 29 bytes; the new entries are pinned from the actual headers.

The dedicated recipe is copied from
`/home/stemxstudio/rove4k-tiny-d-direct-loader-20261020-v3/recipe`. Its core hashes
are checked before import: loader `8a6a9cb9...`, codec `17165d1c...`, linker
`93934099...`, archived builder `fe43b4c5...`. The loader and codec bytes remain
unchanged. Only the reviewed `IMAGE_SIZE` and `IMAGE_ENTRY` constants differ;
mapping/BSS/guard/personality/ABI constants remain the same.

## Actual complete-file comparison

| Mode | Original raw D | Protocol raw D | Protocol generic own ELF | Separate v3 dedicated | Actual composition |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scalar | 8,540 | 8,476 | 8,763 | 7,665 | **7,640** |
| HQ | 8,928 | 8,864 | 9,081 | 7,918 | **7,881** |

The composition saves 25/37 bytes against separate v3, rather than the native
64-byte saving. BCJ plus one-final-fixed-Huffman Deflate payloads are
6,525/6,766 bytes; the unchanged full headers/decoder add 1,115 bytes. Actual
composition saves 836/983 bytes against protocol raw native and 1,123/1,200
against protocol generic restoration. Every final filename is `x`, and all
configuration, ELF headers, payload and restoration code count. These results
are not sums of isolated deltas.

## Reproduce and bounded qualification

```sh
python3 -B engines/experiments/tiny-d-compose/build.py \
  --protocol-root /home/stemxstudio/rove4k-tiny-protocol-20261020 \
  --protocol-index /absolute/external/qualified-protocol-index.json \
  --loader-root /home/stemxstudio/rove4k-tiny-d-direct-loader-20261020-v3 \
  --out /absolute/external/composition

python3 -B /absolute/external/composition/loader-recipe/test_runtime.py \
  --build /absolute/external/composition/build.json \
  --out /absolute/external/composition/image-check
```

The builder freezes both native controls, protocol/generic/dedicated complete
controls, original/native/protocol/loader recipes and qualified source bytes
outside Git. Each protocol native is rebuilt twice from those frozen source
bytes and selected original compiler flags, and must equal the original
qualified native hash. It independently encodes and compiles each whole loader
twice and requires exact complete-file SHA equality. This is reproduction within
each fixed recipe, with no claim of identity between different engine sources.

Both actual compositions passed a new physical observation campaign. Separate
CHECKPOINT audit builds stopped before native entry and showed exact full RX
identity and initially zero BSS/padding. Production files then showed immutable
RX after a real clocked search, guarded fixed mappings, RW-to-RX W^X, explicit
READ_IMPLIES_EXEC rejection, non-executable stack, original-entry handoff,
three persistent startup TIDs, only stdin/out/err and successful EOF shutdown.
The frozen v3 decoder's negative fixtures remain their own prior evidence.

The two new SHA-pinned whole files separately passed **10/10** common shipping
groups: protocol, lifecycle, legal selfplay, EOF and quit. Exact startup total
three, persistent task IDs and maximum three threads were enforced. They also
passed two colour-exchanged 12-ply games using the independent oracle. The
validator/oracle and manifest were frozen outside Git; previous protocol/v3
results were not reused or relabeled as these checks. Clocked result receipt
ordering does not prove cancellation causality. No NPS, strength or large-host
scaling claim follows.

The codec/loader implementation and its [scope](../tiny-d-loader/README.md)
remain unchanged, including auxv, initial brk, self-file identity and observed
toolchain limits. All code is project-owned under the root MIT license; no
external engine or decoder implementation was copied. Evidence lives outside
Git under `/home/stemxstudio/rove4k-tiny-d-composed-20261020`.
