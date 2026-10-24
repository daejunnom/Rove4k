# Explicit shipping node-counter specialization

This isolated candidate enables `tiny_shipping` in an otherwise unchanged
Rust D native recipe. The public parser already supplies nodes=0 and does not
implement nodes/depth commands. This experiment preserves that parser, bare-go
and infinite behavior, clock allocation, stop/newgame/position handling and all
worker lifetime policy. It does not establish a new finite-UCI policy.

Only Control.nodes, Control.node_limit, their initialization/reset stores and
Worker::claim's global budget accounting are excluded by the explicit cfg.
Default and tiny_dev retain those original operations. Combining tiny_shipping
and tiny_dev is a compile error. Limits, local Worker.nodes, Result.nodes,
deadline/origin and the original local0/256/512 deadline checks are unchanged.
Runtime reset gates its matching counter store. No generation or correction
epoch is merged; frozen correction, deferred learning and worker0 publication
remain original source.

The source closure is owned here: control/ is the exact maintained ordinary17;
candidate/ changes search.rs, one runtime.rs store and the builder cfg flags.
The remaining four Rust/link inputs are byte-identical. packaging/ is the
unchanged project loader/codec/packer snapshot. reference/ records the earlier
strict data8 class and old data16 admission as immutable source references.
No external engine implementation is copied into this experiment.

cost.py reads each normal builder's one literal flags list using AST; it never
calls builder main. This deliberately performs one scalar and HQ main link for
each source form, four links total, with no auxiliary unstripped link. The
normal candidate builder itself passes the explicit cfg to first/repeat/audit
consumers through its common flags. Source/recipe are frozen before compilation.

The next packing phase requires inspecting the actual candidate geometry and
adding a separate literal identity admission. Existing class guards and loader
code are immutable. A layout outside the existing supported data8 contract
stops this campaign. Original packed control bytes may be reused only after
checking their full literal size/hash and provenance, and must be described as
reused rather than newly built.

The first-cost domain is compilation, static ELF inspection and build-time
codec roundtrip. A separate small std diagnostic may exercise three original
DEV tests and paired depth2/local-counter/deadline/default-budget checks; these
are not production ELF execution or runtime qualification. No production ELF,
ptrace/personality/RIE fixture, game, benchmark, training or AWS run is allowed.
Eligibility under 4096 bytes, strength and release readiness remain unproven.

The one fixed campaign completed and is **rejected on size** in both backends.
No source variant, alternate flag/codec, retry or sweep followed this result.

| Backend | Original native | Candidate native | Original whole reused | Candidate payload | Loader + headers | Candidate whole | Whole delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| scalar | 16,816 B | 16,816 B | 11,403 B | 10,289 B | 1,115 B | 11,404 B | +1 B |
| HQ | 16,816 B | 16,816 B | 11,762 B | 10,655 B | 1,115 B | 11,770 B | +8 B |

Both original native SHA values reproduced exactly. Candidate RX file spans
are 14,256/14,704 bytes, 16 bytes larger than their original spans. The readable
Rust source grows by 327 bytes. Complete native length remains aligned to the
same data8 file offset. Removing a global atomic operation did not produce a
whole-file saving with this fixed compiler and recipe.

Candidate scalar native SHA is
`df1945b23cbe3d7d6a4af5f775cc98ef6675758814feafa4ce56194541d78c7d`;
HQ is `b92d57e68d33c92fdc367ec7bfc339cbe7f53f0911082371ea5031ad8759f646`.
Complete scalar whole SHA is
`5387a1b598cb49703acc3fdca862faea3c3c65f5dad7bda645d848740ba730e5`;
HQ is `0311813dfa62fb60c4d002933427fe2e9b90b8077a7006a8d87716e0f6591bf9`.
The separate literal class is
`rust-d-tiny-shipping-node-counter-data8-v1`. Its admission function body is
exactly the prior immutable data8 function; only its two native identities and
class name are new. Original data8/data16 guards both reject the new natives
without modification. The fixed 16,392-byte span retains entry/PHDR/load bytes
apart from declared section-header metadata; data is the initialized memcpy
pointer, followed by BSS4 at 0x404008. Zero fill is a source/static contract here,
not a new memory observation.

Actual execution counts are four primary native links, two candidate loader
links, two reused original whole controls, two separate std diagnostic links
and four std fixture calls. The three selected original DEV units each report
1 passed/10 filtered. The paired depth2 witness gives identical best4742,
score0, Result/local nodes93 and the full correction array. Default budget2,
shipping quota omission, pre-stop clock reads0 and the local256 deadline
boundary pass. The combined-cfg compile error is source-checked only.
Diagnostics observe direct-child return, not descendant/group absence or the
raw OS clock/worker pool. All native/loader tool groups settled; no production
ELF, launcher, RIE/personality/ptrace fixture, game or benchmark was executed.

The executed source43 and earlier unexecuted runner review checkpoints are
preserved separately outside Git. This result paragraph was appended after
the last build; the final inventory records that README-only difference.
No maintained source or release was changed, and no runtime admission is made.
