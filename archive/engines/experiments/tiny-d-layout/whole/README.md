# Metadata-only complete-file cost

This separate producer preserves the first native-only experiment's 22 sources
without editing them. `recipe.json` pins their raw bytes and the two observed
metadata-only native identities and entry points as explicit literals. It
regenerates native source/images from that closed ordinary source copy and
requires the same original and candidate full hashes. No historical generated
file or external receipt is a runtime input to the producer.

```sh
python3 -B engines/experiments/tiny-d-layout/whole/build.py --out /absolute/new/whole-cost
```

The existing original codec and loader files are byte-identical to the raw18
control. Only `fixed_compress` after the original E8/E9 BCJ is used. Scalar and
HQ original whole files must reproduce the literal 7,540/7,800-byte controls
twice before candidate packaging starts. Candidate full native hash and exact
ELF headers are checked against a separate metadata-only cost declaration;
entry and RX file/memory length change, while the old three-page mapping,
zero-sized initialized data and complete BSS contract remain fixed. The original
production admission still rejects each candidate and is never edited.

Two independent encodes and loader compilations per candidate must yield equal
payload and whole bytes. Original loader flags, source order, mapping checks,
codec and source bodies remain unchanged. There is no preset, flag, layout or
loader-capability search. All ELF/loader headers and decoder bytes count in the
observed whole size. No production engine, restoration audit or runtime test is
executed. Whole cost is not semantic, physical-restoration or chess qualification.

The actual first cost completed with each original control reproduced twice,
followed by two independent candidate encodes/whole compilations:

| Form | Original whole | Metadata-only whole | Reduction | Candidate payload | Headers/loader/filter |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scalar | 7,540 B | 7,513 B | 27 B | 6,398 B | 1,115 B |
| HQ | 7,800 B | 7,748 B | 52 B | 6,633 B | 1,115 B |

Candidate scalar whole SHA-256:
`4946a11aaaac5642e2e1fed88c1a61ccecce345af1b2134d58274cd548e951ce`.
Candidate HQ whole SHA-256:
`355a883277571d00acac583ee26023b7eae6ac5670c221ff07ace3c9392e6bff`.
The whole-file receipt SHA-256 is
`255cb5028429d6a0aa5ddaba90673d7fe3964c278e4b381ed7666c21d337e1b5`.
It also includes a separate fresh native-only regeneration from the exact22
sources; its native hashes, sizes and compiler-only layout values agree with
the preserved first native comparison. The source22/native-first freeze receipt
is `7fbb3d041e4f695bf370b5342201b6bd8d67c1af445108175c7a8b5878005906`.
Neither receipt is read by the source producer.

Both complete files exceed 4,096 bytes by 3,417/3,652 bytes. Production runtime
sessions, restoration checkpoints and new Board/core tests remain zero. The
separate two-change layout-plus-search-phase experiment has its own copied
inputs and native-only results; its gains must not be added to these costs.
