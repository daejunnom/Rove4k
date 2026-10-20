# A/F terminal-witness first cost

This is one fixed source candidate per family based on the source-only proposal
15ebcca91eec6b7fb2fd75bbec8cf1479b36173c6ae824066572ae104052ea4b.
The proposal estimated20–35 lexical bytes; pure preparation now fixes an actual
23-byte compact-source reduction for each family. The producing README recorded whole-file cost as pending; actual first cost
is now recorded below.
No whole saving, functional qualification, speed or4KiB acceptance is assumed.

Normal source and shared helpers remain read-only. All producer inputs here are
ordinary LF files. recipe.json pins both actual current shipping controls
(main/native/bootstrap/whole), current canonical source, unchanged compiler,
profile, codec, bootstrap/prefix, and every existing name/input/semantic helper.
It reads those controls in place; no baseline artifact is copied or recompiled.
No old report, executable execution, reference engine, Clang, AST, PP, new name
allocator or dynamic variant search is a producer dependency.

The only source changes are: relocate the unchanged contiguous text+parse
definitions before search; replace terminal gen/make first-legal iteration by
the existing nullable parse(p,0,&child); move the unchanged normal moves/scores/
count declarations and gen call after that terminal branch. Raw evaluation
stays immediately before the branch and its formula is unchanged. Claim,
draw/repetition/dead-material calculation, PLY behaviour, mate precedence,
TT context/coherence, score packing, ordering/learning, replay, clock and pool
are preserved. The config admits exact literal role pairs, including each
actual Board/Worker/function/local spelling. No new prototype is introduced.

profile.py performs three explicit spans, checks unique definitions/order,
protects all gaps byte-for-byte and reconstructs the full original with an
inverse. Moved definitions keep their exact hash. Generated legal Move values
are nonzero because from and to differ; query0 means no legal witness. In draw
or PLY terminal nodes this preserves gen order and make filtering. A legal draw
returns0 without abort; a legal non-draw cap sets stopped; no legal witness
still returns mate/stalemate. The same legal child scratch is discarded.
F's existing nullable parse still formats each candidate move; this extra
terminal work is intentionally retained and is not a speed claim.

Candidate A:9690 bytes /7d81c7f94fc2ff136fd52c20b589933f033c7eb3097a62a2067ff28b452d7539.
Candidate F:9705 bytes /a2803d7a8469ade33fa23b17337c7de078b07d0b93c85b5223fbcbae47c1e336.
A protected complement9153 bytes /be6f40b77c6cbe6a3b04d5f4ce2d97ece53674783f68fbfc12f892120ba7679d.
F protected complement9181 bytes /498e82b072e9f33046551eb97e9cbb06e183c18c11e9837f6d85ea822c54f63f.

Run sequentially, once each on the fixed qualified Ubuntu x86-64 toolchain:

```sh
python3 -I -B engines/experiments/tiny-af-terminal-witness/build.py --family A --out /absolute/new/external-A
python3 -I -B engines/experiments/tiny-af-terminal-witness/build.py --family F --out /absolute/new/external-F
```

Each invocation freezes the five owned sources before importing its pure
transformer, validates all actual controls/source pins, performs one compiler
stdin invocation in a private output directory and one ALONE encode. Existing
compiler argv are unchanged (A cc -Os -x c - -o x -s; F adds-pthread). Both use
the original77-byte prefix and exact bootstrap template/source-literal recipe;
the actual baseline bootstrap is compared in memory without copy/encode.
A retains original ALONE9extreme/lc2lp0pb0 defaults; F retains BT4/64MiB/nice32.
Strict Python EOF/no-unused decode and an independent lzma CLI decode must
restore the exact Python+C bytes. Manual fixed raw-literal/template recovery
checks exact source and compiler argv without AST/eval. All prefix/header/end
bytes count. Native/code layout may change; old native equality is not assumed.

Compiler/decode subprocesses have owned groups, bounded CPU/address space and
wall deadlines; termination and group absence are recorded, and only owned
groups may be signalled. First unexpected failure is preserved with no retry.
Native and wrapper are never executed by this producer. No fixture, functional
claim, wrapper session, normal promotion, DEV build, control compile, game or
benchmark is authorized here. After A1 thenF1 cost, stop for root decisions.

At source freeze this README records pending cost. Final results may be added
after the sole actual measurement, keeping its producing five sources frozen
outside Git and distinguishing metadata-only README updates.


## FINAL first-cost result — rejected for size

Exactly one A compile/ALONE encode followed by one F compile/ALONE encode ran,
sequentially. Both source/argv restoration and strict Python EOF/no-unused plus
independent CLI decode passed. Both owned subprocesses per family terminated
exit0 with their groups absent and no cleanup signals needed. No native engine,
wrapper, fixture or normal producer was executed. No retry or second candidate
was created. Compiler stderr was empty for both.

| Family | Compact C old→new | Native bytes old→new | Complete old→new | Decision |
| --- | ---: | ---: | ---: | --- |
| A | 9713→9690 (-23) | 22672→22672 | 4766→4775 (+9) | reject/stop |
| F | 9728→9705 (-23) | 18576→18576 | 4735→4738 (+3) | reject/stop |

A new native full SHA is
`476b3e8bb23546963b8ebf2ff85981307970cf94a83aa71d4b8cb62d5cfae2e8`;
new whole4775 SHA is
`e7b1caf995624bf32cf8d9d0b62fba9c6def03552f09ae6d6a988990bfe2baba`.
F new native full SHA is
`a33f5b041e6f2f6f1da64776b0b0774f066e8f4a610ddfd1dacc4c257c24900e`;
new whole4738 SHA is
`4b05fe9ea522adb6d74e036c9fa489badb5bcfc85411ecde85ec19fa106e99b8`.
Full natives differ from their controls despite equal byte counts. No native
identity, runtime semantic qualification or ABI equivalence exception is claimed.
The exact reason for the compressed size regressions was not experimentally
isolated; source reordering must not be treated as a known whole-file saving.

Actual A result receipt: `c3ad15651a1475be95ddea0cc31088ebd75291614666b6291776386f89e72a55`.
Actual F result receipt: `a70c80138f64689c6d9d8b479f30642ad099f3dbd6466429829f26dcb3dd7a28`.
Frozen producing source receipt:
`7a5f7d625ccc6642b1f76fab7310fbb878b386d22fc8bfead683c52458fedd9d`.
Only this README gains final result metadata after those runs; profile/config/
build/attributes remain exactly producing bytes. All generated files/reports
remain outside Git. Normal/shared/global files and Git/CI are untouched. The
maintained entries stay A4766/F4735. All handles are0; this lane is stopped.
