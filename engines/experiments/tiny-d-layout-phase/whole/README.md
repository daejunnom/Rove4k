# Combined TinyD whole-file cost

This is a separate cost-only producer for the fixed metadata-first Board and
search-phase composition. It preserves the preceding 25-source native-only
closure and adds only this directory's `build.py`, `recipe.json` and README:
28 source files in total. The original 24-file executed/native-cost receipt
and later 25-file LF-attribute freeze remain separate, unchanged records.

`recipe.json` fixes the raw bytes/SHA-256 of all 25 original source files. The
producer copies them into a new external source tree, then invokes the frozen
native-only `build.py` with SHA
`5a006ad659f890d20e553d387e39b95e2ff005fe8525f1f24bebaef0f048666b`.
That source-only producer regenerates the unchanged control and exact combined
native images twice each. No historical report, native binary, payload or
complete-file artifact is a regeneration input. Provenance hashes in reports
are metadata only.

The unchanged original whole-file controls are rebuilt first, twice per form:

* Scalar: 7,540 B,
  `26eaedc2560776a226a8e17886e209501346524e97fc2b47483f13335fbde013`
* HQ: 7,800 B,
  `3c863ceba32bf9173bf53d72f575c9e28e2ce2eb1cc43fde38bf03d6c9eff3ca`

Each combined native then requires its previously measured complete native
hash, byte length, entry and full parsed ELF to match its explicit literal
row. The unchanged original production `packer.admit` must reject it. A
separate cost-only declaration supplies these root-reviewed loader macros:

| Form | Native | Entry | RX pages | BSS base | BSS bytes/pages | Upper guard | Reserve |
| --- | ---: | --- | ---: | --- | --- | --- | --- |
| Scalar | 8,124 B | `0x401e4d` | 2 | `0x402000` | 175,092 B / 43 | `0x42d000` | `0x2f000` |
| HQ | 8,512 B | `0x401f7f` | 3 | `0x403000` | 175,092 B / 43 | `0x42e000` | `0x30000` |

Both declare image base `0x400000` and lower guard base `0x3ff000`. Guard and
reserve values are explicit cost-only loader declarations, **not native ELF
segments or observed physical mappings**. No production admission or old
mapping guard is modified, and this stage does not qualify a new production
mapping contract.

The codec and loader source bodies, loader compiler flags, macro order and
linker script are unchanged. Every attempt independently performs BCJ plus
the existing fixed-Huffman encoder, verifies its inverse, and compiles the
same loader with `CODEC_FIXED=1`, `CHECKPOINT=0`. Each form must reproduce both
payload and complete-file bytes in two attempts. The combined whole cost is
measured directly; separate native/layout/phase savings are never added to
infer a complete-file result.

```sh
python3 -B whole/build.py --out /absolute/new/path/outside-git
```

This stage permits eight fresh native compilations and eight whole-file
loader compilations. It performs no compiler probes, CHECKPOINT build or
execution, production runtime session, game or performance measurement.
Payload inverse equality and raw ELF identities do not prove physical
restoration or runtime ownership.

The first bounded run completed with exit 0. The source-only native producer
regenerated all four native forms twice, then the whole producer rebuilt each
original control and each combined candidate twice. All paired payloads and
complete-file bytes were identical.

| Form | Original whole | Combined whole | Actual whole saving | Combined payload | Loader and headers |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scalar | 7,540 B | 7,478 B | 62 B | 6,363 B | 1,115 B |
| HQ | 7,800 B | 7,718 B | 82 B | 6,603 B | 1,115 B |

These are measured combined costs, not a sum of separate savings. The complete
candidate SHA-256 values are:

* Scalar: `d4f2ba718c5e9391708c86468416338f78b6134d1f017267c6c34add187381f2`
* HQ: `3bb8a6a97a27a77508848ab9bd388a4802e07f8d8ff0e37b536176423aa7028f`

The external result is
`/home/stemxstudio/rove4k-tiny-d-layout-phase-whole-first-20261020/results.json`,
SHA `4b0b4f62b4266c8e2e60c1d8b969fe28de0ff0970822c380a5d4156bd0716b83`.
Its native-first subtree contains newly generated source/native proof; neither
that output nor the earlier native-only output is a future regeneration input.
The old production guard still rejects both native candidates. No CHECKPOINT
or production runtime session, physical mapping observation, new production
admission, semantic qualification, game or benchmark was performed.
