# TinyD: metadata-first Board with the fixed search phase

This is one native-only composition. It combines the exact metadata-first
`Board` declaration with the already fixed PVS retry-phase template. It does
not add the savings from the two separate experiments: the combined source is
compiled and measured directly.

The experiment owns a closed copy of the maintained finite TinyD source:
18 raw files under `control/`, the fixed `transform.py` and `phase.c.in`, and
the original native-only layout producer under `dependencies/`. All are pinned
by raw byte length and SHA-256 in `recipe.json`. Historical outputs and the
original experiment folders are not execution inputs. The copied ordinary
`fresh.py` is provenance only; its original repository-root assumptions make
it unsuitable as a standalone driver from this folder.

Exactly two source fragments change:

* `native/tiny.h`: move `int8_t b[128]` after the unchanged metadata fields.
  There must be exactly one original declaration, and the source outside the
  replaced declaration must remain identical.
* `native/search.c`: apply the fixed retry-phase template to original search
  SHA `87bec413c4dcbccafd1b9c48e2a4ae878caae11747caf942f36a1036e88c7fb8`.
  The result must be exactly
  `48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c`.
  The template checks the old four and new one child-call sites and preserves
  the surrounding key push/pop and stopped boundary. All other native source
  files remain byte-for-byte identical.

Run only after the compiler slot is released:

```sh
python3 -B build.py --out /absolute/new/path/outside-git
```

The driver first builds the unchanged scalar and HQ control twice each. The
original stripped full-image hashes and original `packer.admit` checks must
accept the 8,348-byte scalar and 8,736-byte HQ images. It then builds the exact
combined scalar and HQ candidates twice each: eight native compilations in
total, with no extra compiler probe. Compiler flags, resource values, unit and
link order, linker script, and native section-header stripping are unchanged.
Only the source and output paths differ. Compile failures preserve diagnostics
and stop the run; repeats must have identical full native bytes.

Candidate bytes, full SHA-256, ELF entry, RX pages and BSS segment are recorded
separately. The unmodified old production admission must reject the candidates;
no expected image, source pin or mapping guard is automatically updated. If a
candidate crosses 8,192 bytes, its actual RX pages, BSS base and entry are
reported. A smaller native image can move the page-aligned BSS even though the
inferred C structure size is unchanged.

This stage performs no payload encoding, loader compilation, packaging, engine
execution, games or performance measurements. It does not qualify candidate
semantics, runtime ownership, DEV identity, a new mapping class, or 4KiB entry
readiness. All outputs are external. The baseline and candidate sources plus
producer inputs are frozen again in each output directory.

The first authorized native-only run completed with exit 0. Each control and
each combined candidate reproduced its complete native bytes in two builds.

| Form | Control native | Combined native | Actual saving | Combined RX pages | Combined BSS base | Combined entry |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Scalar | 8,348 B | 8,124 B | 224 B | 8,192 B | `0x402000` | `0x401e4d` |
| HQ | 8,736 B | 8,512 B | 224 B | 12,288 B | `0x403000` | `0x401f7f` |

The scalar candidate crossed the 8,192-byte boundary, reducing RX from three
pages to two and moving BSS down one page. The HQ mapping page class stayed
unchanged. These are direct combined measurements. The old production guard
rejected both candidates as unknown selected native images and remains intact.
The candidates have not been packaged or executed, and the scalar mapping
change has not been admitted as a new production contract.

The combined full native SHA-256 values are:

* Scalar: `199da6e1e1a94c97fe853e0ff3d89b52e2057a55592052e7fbe5500147e4aeec`
* HQ: `3f4269dc5c0d72c0b43bc73c6a11afdab5844836e12e7c31d60dde08c8ae2806`

The external run directory is
`/home/stemxstudio/rove4k-tiny-d-layout-phase-first-20261020`. Its `results.json`
records all eight compile outputs, source complement proofs, actual ELF
segments, and old-guard rejection. This directory is an output, never a source
input. No compiler probe, codec, package, loader build, runtime session or
benchmark was added after the eight native compilations.
