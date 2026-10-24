# Separate B new-image metadata qualification and cost

This stage uses the identical storage18 B source13071B. It preserves the
original52 ordinary files, original producer, recipe, literal map and first
full-native failure unchanged. `README.md` documents that frozen first phase.
The phase1 FINAL summary is19885B, SHA-256
`0bf7fa1b7fc6d74b40a0d59c30bf91c5bca7c6f729a90330d5129851c6193e66`,
stored outside Git at
`C:/Users/강민수/Documents/Codex/rove4k-tiny-alpha-storage-bce-20261020-evidence/summary.json`.
This reference is provenance metadata, not a normal-build input.

The old image remains26592B / `221a865e2712cb3e704128e0ae8353edd358343f564fe53093040f6515d522ec`.
The new image is a distinct26496B /
`5a315a66f86ff81f9b0feb679b25f919c5aaf63bb9db2d157040a5b7ce6bbb4b`.
No strip, flag change, byte normalization or identity-equivalence exception
is used. The qualifier compares the two actual images and records their
different full hashes. It never creates a normalized executable or presents
the candidate as the old full-native image.

The boundary is intentionally fixed to this one image pair:

- The complete program-header table, all PT_LOAD placement and section
  identities/flags/types/addresses/alignments remain equal. Dynamic symbols,
  strings and relocations remain byte-identical.
- Every allocated section's payload remains identical except the20B
  descriptor inside the36B GNU type3 build-ID note. Its header, GNU name,
  shape, address and size remain fixed. Both descriptors are literal pins;
  the exception does not admit other allocated data changes.
- The ELF header changes only its literal section-table pointer. Nonallocated
  `.strtab` may have its pinned new payload/size; `.shstrtab` retains content
  and changes only its pinned file offset. The final zero alignment gap has
  the literal old5B/new4B length. Other file gaps remain equal.
- `.symtab` retains103 entries. Its19 object names use one literal map,
  including `back.0→qa.0`, `material→qi` and `material.1→qi.1`. Types, binding,
  visibility, raw `st_other`, values, sizes, section indices and multiplicity
  are preserved for every symbol. Global ordering and string offsets may
  change. No regex suffix inference or automatic alias discovery is used.

These names identify objects in the sole stdin C translation unit. The
shipping executable has no engine companion object or exported object ABI
consumer; its dynamic symbol/relocation data remain identical. The source
policy still preserves directives, literals, APIs and `Move`/`MOVE`, proves
raw full-preprocessor alias-only inversion and retains resource values and
macro multiplicity. Both distinct B `material` objects preserve their
addresses, sizes, storage duration and initializers. Existing unchanged-body
rule/search evidence can be considered only within this explicit new-image
boundary; this stage provides no runtime, ABI outside that boundary, strength
or release acceptance.

Normal builds use only own ordinary sources. `metadata_recipe.json` embeds
literal pins for the original52 sources and the new producer helpers. It
does not read old executables, reports, phase1 artifacts, the live maintained
tree or AF experiment outputs. Known first-phase image observations provide
the transcribed literal policy, rather than a dynamic allowlist source.

`metadata_build.py` first reproduces the original B5955 control twice using
its frozen builder. It then performs exactly two independent candidate
compiles with the original unstripped compiler/profile. Each must match the
new full-image pin and pass the separate qualifier. Only after both native
gates pass can it run exactly two original bootstrap/XZ-LZMA2 packaging
operations, with the original75B launcher, preset9 extreme, lc3/lp0/pb2,
CRC64 and original source-literal helper. C/E candidate compiles and all
engine executions stay zero. No source, name, flag, codec or ordering sweep
is performed. All output paths must be new absolute locations outside Git.

```sh
bce_experiment='/mnt/c/Users/강민수/Documents/Codex/rove4k-engines-af-20261020/engines/experiments/tiny-alpha-storage-bce'
python3 -I -B "$bce_experiment/test_metadata.py" --policy "$bce_experiment/metadata_recipe.json" --old /home/stemxstudio/rove4k-tiny-alpha-storage-bce-first-native-20261020/control-B/native/x --new /home/stemxstudio/rove4k-tiny-alpha-storage-bce-first-native-20261020/candidate-B/native/x --out /home/stemxstudio/bce-B-metadata-fixtures-new
python3 -I -B "$bce_experiment/metadata_build.py" --out /home/stemxstudio/bce-B-metadata-new
```

The first command is a pure byte fixture suite; it does not execute an ELF.
Its explicit historical images are test inputs only. The normal producer in
the second command regenerates both images from the closed ordinary source
inputs and has no dependency on those historical paths.

## Measured result

The separate fixed campaign passes the 44 pure-byte fixtures and two fresh
candidate native/whole builds after the two original B5955 controls. The source
is 13,071 bytes, native 26,496 and complete file **5,851 bytes**, saving **104**
whole bytes. The new whole SHA is
`25b2c6a1198d5e600be252ae57da84ca9f9e40c3167021ce33f3f9eff29f425c`;
cost receipt SHA is
`d5d4729a808e031f5f76d63e946be00a2e321c16ae47a8bb919d8d723debf9d4`.

Independent actual-file readback verifies both full native/whole identities,
all program headers and 26 allocated-section geometries, unchanged remaining
allocated payloads, strict XZ restoration and the exact packaged compiler-stdin
source. That readback receipt is
`84030a2193e74b2804dbba3d294aae1bd41247583ec1a08a8b9c03b7217fae13`.
Candidate C/E compile and target execution counts stay zero in this cost stage.
The subsequent maintained-B build and selected-wrapper checks have separate
receipts; their runtime results are not backfilled into this cost producer.
The original full-native failure remains failed.

Before this campaign the pure fixture loader was changed to an explicit local
file import so the documented `python3 -I` invocation works. The qualifier and
its literal policy did not change. The producing 57-source snapshot/archive is
preserved outside Git; this final result text is the only post-cost source
change. Final maintained resource/strength/4KiB acceptance remains open.
