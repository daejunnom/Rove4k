# One fixed A/F packed HCE coefficient cost

The only source change packs each original material/advance/center coefficient
triple into a signed int table entry. Low 10 bits encode material, next 3 advance,
and high bits encode center+3. The fixed table is
`{24576,48228,98624,65866,27124,41860,0}`. Existing signed int locals and signatures
remain; signed right shifts have nonnegative inputs. Do not narrow to 16 bits or
make the packed local unsigned. Empty value stays zero and king center stays -3.

The actual A4762/F4730 functions shrink from 219 to 207 source bytes. The whole
fixed candidates are A9675/c7734b9a and F9690/e0aa8dd9. One exact function span,
full input/output identities, inverse and protected complement are admitted.
All callers, board/HCE accumulation, ordering, search/MTD contracts, resources,
clock/UCI and previous source stages are outside the changed span. Independent
source arithmetic passed 832 unique piece/square values (896 with duplicated
zero for the two signs). This is not executed-C functional qualification.

The normal A and F baselines and completed receipts are read without copying,
recompiling or recompressing them. Each candidate is compiled exactly once via
its unchanged family argv, stdin, inherited environment and private cwd. A uses
the existing preset9-extreme/lc2/lp0/pb0 ALONE filter defaults; F additionally
fixes BT4/64MiB/nice32. Templates and the 77-byte prefix are unchanged. Baseline
and candidate ALONE decodes each require exact bootstrap, EOF and no trailing
bytes (four pure decodes total). New native identities are allowed and recorded.

No material-summary combination, normal edit/generation, D compile/package,
AST/PP, DEV, engine/runtime, game, benchmark, spelling/codec/flag sweep occurs.
D's source-only sibling draft remains deferred. Earlier 165-byte native value
regions do not promise a candidate native or whole saving. A gain requires a
later root decision; loss/tie closes without functional qualification.

All generated files and receipts must use a new output directory outside Git.

The single first-cost run completed with empty compiler stderr. A 4762 -> 4766
(+4 B loss) is closed without functional qualification. F 4730 -> 4728 (-2 B)
has new native 62acc534 and whole 83aa628e, with native length unchanged 18576.
Both candidate native compiles and both fixed packages completed once; four
strict pure decodes passed. Cost receipt SHA-256 is
bf0b16f8cab825e879568e2ea57344d6950765abf33647ed2c11d9c60f8b973a.
The exact producing four source files are preserved outside Git under
rove4k-af-packed-hce-first-20261021-evidence/cost-producing-source; this final
README is completion metadata. Its config binds the producing normal source
revision; later normal source advancement does not change the historical pins.

Root then authorized F alone: one actual value/put fixture compile/run passed
832 unique values, explicit zero 64 and 384 incremental put steps with the 29120
aggregate bound. Its receipt is 0d033f6d5df1b1b868b6d1d17436fd88f6a3ecd83364ad306c55189662ddfa22.
F ordinary integration then reproduced shipping 2 / DEV 2 and passed unchanged
selected quit/EOF 2 sessions and 8 GO. Maintained recipe records those separate receipts.
A was not promoted, D remains source-only/uncompiled, and material-summary
composition was never built. No extra cost variant/game/benchmark ran.
