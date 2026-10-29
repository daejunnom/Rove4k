# BCE private-storage spelling: first B native gate

This is an independent, fixed source-spelling experiment. Maintained B5955,
C5723 and E5679 remain unchanged. C query-composition5687 is excluded. The
ordinary controls were copied from checkpoint
`1f35a6eba8ad88070e96a2221549402bc45fbf8b`; normal builds read only this folder.

The literal policy `1256f5017753b43a3fd78a16bdc766a21b86f19ebf400ad61d72a35c4169a84d`
retains the same18 `qa` through `qr` pairs as the earlier storage-AF decision.
No name is reassigned when unused. The original BCE89 aliases, readable code,
DEV path, compiler/profile, bootstrap and compression decisions stay fixed.
No function, typedef, member, macro/directive, quoted text or external API is
renamed in this stage. `main` and `Move`/`MOVE` remain protected. PLY code uses
remain B9/C12/E12; no numeric inverse replacement is admitted.

| Family | Baseline C | Fixed candidate C | Lexical saving | Used storage names |
| --- | ---: | ---: | ---: | ---: |
| B | 13606 | 13071 | 535 | 18 |
| C | 12526 | 12065 | 461 | 18 |
| E | 12641 | 12192 | 449 | 17 |

E's `material` has zero shipping occurrences, so `qi` remains reserved. B's
two `material` arrays have different scopes and initializers: HCE block-static
king0 and SEE file-static king20000. Both original spellings become `qi` in
their original scopes; the objects are not merged.

The target is the original Ubuntu24.04 x86-64 GCC13.3/glibc2.39 environment.
B/E retain `cc -std=c11 -Os -pthread -DWORKERS=2 -DTT_BITS=18 -DDEV=0 -x c - -o x`;
C additionally retains `-mavx2` before `-DDEV=0`. These commands are unstripped.
Global spelling changes can alter the complete ELF even when machine-code
sections agree. Such a failure remains a failed full-native gate.

The producer first runs each of the three frozen control builders with
`--dev`. Each control independently regenerates two shipping C/ELF/bootstrap/
whole outputs and two unchanged DEV C/ELF outputs, checking the original full
literal identities. Only after all three controls pass can the producer
generate one B candidate native. Before that sole compile, it checks source
and header freshness, full raw preprocessor alias-only inversion, every full
phase-two logical macro definition with multiplicity, per-name duplicate
definition order and exact resource macro values/counts. Raw macro order is
recorded separately. No whitespace or numeric normalization is performed.

After the first B native, the producer always holds: no second B compile, no
C/E candidate compile, no candidate compression or whole-file measurement,
and no engine execution. On a native mismatch, `elf_observe.py` records full
ELF/program headers and section contents, including `.text`, `.rodata`,
`.data`, `.bss`, dynamic symbols/strings, relocations, build-ID, nonallocated
`.symtab`/`.strtab` and section-name tables. This read-only inventory supplies
no new semantic, ABI or release acceptance. No strip or flag exception exists.

Run from WSL with a new absolute output outside Git:

```sh
python3 -I -B engines/experiments/tiny-alpha-storage-bce/prepare.py --out /home/stemxstudio/bce-prepare-new
python3 -I -B engines/experiments/tiny-alpha-storage-bce/test_policy.py --sources /home/stemxstudio/bce-prepare-new
python3 -I -B engines/experiments/tiny-alpha-storage-bce/build.py --out /home/stemxstudio/bce-native-new
```

`build.py` returns2 for the expected preserved full-native identity failure;
this is distinct from a producer error or a successful native gate. Original
control compression is permitted only to reproduce its already-qualified
whole-file bytes. Candidate codec/whole/engine budgets remain zero. All
reports and generated artifacts belong outside Git. There is no runtime,
game, benchmark, policy, core-engine, CI or maintained-promotion claim here.

The bounded2026-10-20 result is a **preserved full-native identity failure**.
All B/C/E controls passed two shipping and two DEV reproductions. B's header
gate passed: raw expanded92268B restored exactly by alias inversion; all1062
logical macro definitions (1062 unique, zero actual duplicates) agreed in
Counter, per-name order and raw dump order; resources remained2/18/128/0.
The pure duplicate-definition fixtures separately exercise multiplicity and
order, because this actual dump has no duplicates.

| B full ELF | Bytes | SHA-256 |
| --- | ---: | --- |
| Original | 26592 | `221a865e2712cb3e704128e0ae8353edd358343f564fe53093040f6515d522ec` |
| Sole candidate | 26496 | `5a315a66f86ff81f9b0feb679b25f919c5aaf63bb9db2d157040a5b7ce6bbb4b` |

First difference is byte40: `e_shoff`24608 becomes24512. Program headers are
identical. `.text`, `.rodata`, `.data`, `.bss` metadata, `.dynsym`, `.dynstr`,
`.rela.dyn` and `.rela.plt` agree. The allocated `.note.gnu.build-id` changes
from `78c8243916f127510516042f4f9954b4dcdbed92` to
`834fda18251c790cf3a58bdc3e2813f0f3aa3508`. Nonallocated `.symtab` contents
change with size2472 preserved; `.strtab` changes1305 to1210B. `.shstrtab`
contents remain equal but its file offset24321 becomes24226. All these
observations retain the original full-native failure. No new native semantic
or ABI class was qualified.

Raw evidence is outside Git at
`/home/stemxstudio/rove4k-tiny-alpha-storage-bce-first-native-20261020/`:
`results.json` SHA-256
`adb6cfee3699bef82b786d953deb558d441168b733e0bf9b18e5083f53e9aed4`
and `candidate-B/elf-observation.json`. The producer input closure has48
ordinary files. The command's managed session48649 is terminal with host-tool
nonzero exit1; the inner Python exit was not captured separately. Its source
declares return2 for this preserved native mismatch, and the raw report is
complete with `full_native_gate_pass=false` and no unexpected producer error.
It was not rerun. Candidate native counts are B1/C0/E0; candidate codec,
whole-file and engine counts are all zero. Consequently no candidate
whole-file saving or4KiB progress is claimed.
