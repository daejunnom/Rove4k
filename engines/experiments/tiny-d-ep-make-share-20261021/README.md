# EP normalization shares make — frozen first cost

Current dd6c5fb atomic16 native8 are copied byte-for-byte into control/native;
old atomic128 control8 are not the baseline. Only ep's manual trial becomes
`Board t;if(make(p,MOVE(q,p->e,0),&t))return;`, plus the private boolean-only
provisional-parent contract. The other seven native inputs remain exact.

The EP caller independently proves target rank/emptiness, victim, adjacent own
pawn and valid king cache. Trial displacement15/17 cannot create a new EP field,
so nested ep(-1) returns immediately. Intermediate h/r may be unfinished and the
trial Board is discarded; only legality is consumed. General arbitrary-move or
canonical-Board admission is not broadened. Extra generic metadata work and one
bounded make frame remain; no speed or stack benefit is claimed.

| Form | Baseline native | Candidate native | Text delta | Packet | Whole | Whole delta |
|---|---:|---:|---:|---:|---:|---:|
| Scalar |7932|7836|−73|4865|6002|−62|
| HQ |8288|8224|−73|5083|6220|−33|

Header+loader overhead stays1137B (176B headers +961B text). Candidate board raw
source9007B versus8770B includes functional fragment−81B and contract comment
+318B; this raw+237B is separate from actual machine-code and packet changes.
There is no NVCompact or compiler-flag variant. Both files remain above4096B.

Native scalar SHAad76de1424f4de80cbb5c9c19966cb666716c2ed6fc9703d3a2400daae4f3268;
HQ SHA1c5d426eafa3100e82bd659fac8b347a9686e80f91849c27e5c534d954e8dfe5.
Whole scalar SHAa95c25d791a39bb3d6d05fec010eb5407249c51fd9b2ad02be6045d8dd9c4b04;
HQ SHA1a5060465975f99bafb0a961b3e5b362b09b2180465272dbe3103a4e59544156.
Entries401d27/401e64 retain RX2/3, BSS402000/403000175092B/43pages, data0,
NX stack and same form-specific guarded reserve. The separate candidate packer
permits only these two full identities; current normal admission stays exact.

The source/flag/profile/codec/model/loader are fixed Linux x86-64 SSE4.2+CX16,
WORKERS2/TT18/PLY128. Two candidate native links, two fixed encodes and two
CHECKPOINT0 loader links completed once each. Two exact existing DATA helpers
read the new packets, compared BCJ then inverse-native full bytes, canaries and
owned32MiB table munmap. They did not enter either native image or own loader.
All13 owned tool/helper commands returned0, drained EOF, reaped leaders and
reported group absence; active handles0. This is an actual bounded observation,
not a generic async-cancellation/cleanup guarantee.

First-cost producing source21 and packaging source24 are preserved externally;
only this README changes in final24. Native receipt b19caeb5a30ec83bc278a72ad4ccc959c091a3101129c2d9d87f2a926faef52b;
whole receipt908d98b6755c308fda9d1e902a811d38b913e7d0e37d6a78876367afb9dd57ce.
Independent native-source and pack-source reviews are fb180632… and eb26372e….
Functional EP/state parity is a separate next stage; no old runtime proof is
relabelled as a test of this new call cycle. Engine/loader/audit/fresh runs,
normal/shared edits, control/repeat/helper compiles, new agents and Git writes0.
No negative/RIE/ptrace/register/personality, games, benchmarks or paid work.
