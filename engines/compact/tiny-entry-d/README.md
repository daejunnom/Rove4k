# Maintained C D capture-only Move bit3 own-ELF

The selected internal Move representation reserves source-square bit3 for capture,
clears that bit in FROM, and sets it while generating moves. The existing emitter
argument now holds capture/pawn-promotion flags. Quiet promotions keep capture0;
capture promotions/EP carry1; castles and quiet N/K moves to an empty active EP
target carry0. All four promotions and move order are preserved. Runtime raw
coordinate queries mask only bit3 for comparison and make the actual generated
member. The separate provisional-parent EP make trial remains raw/untagged and
boolean-only. TT retains all17 Move bits; this is a private in-process ABI, with
fresh zeroed TT and no old-format interoperability promise.

| Form | Native | Fixed21-v2 packet | Complete own ELF | Change from dead-state | Nonpacket |
|---|---:|---:|---:|---:|---:|
| scalar-shipping |7772|4829|5966|-21|1137|
| hq-shipping |8128|5038|6175|-19|1137|

Readable native source is82B smaller across tiny.h/board.c/search.c/runtime.c.
Actual text shrinks54/65B; native files shrink64B each. Scalar entry401cd9,
HQ401e0b, exact RX2/BSS402000/175092B/43roundedpages, lower3ff000/upper42d000,
reserve2f000, zero-file RW and NX remain explicit per-identity literals. Models
stay0101127e/0810217e, independent of page count. Fullkey aligned16 TT, all score/
depth/bound payload bits, HCE/PVS/QS/history/continuation/correction, repetition,
rules, finite UCI, fixed pool/resources, hardware CRC decoder, linkers and flags
remain the existing policy. Packer/verifier permit only these exact two new
identity/form/layout/model tuples; their physical/guard observer bodies are exact.

Focused ASan/UBSan DEV functions pass19roots/286orderedpseudo/282legalchildren
per form, including quiet/capture promotions16/8, castles6, EP7 and nonpawn
last-rank captures6. Actual text/parse282 and raw-untagged EP7 pass; independent
rules, named Board/HCE/hash/context agree. Actual search14old/new pairs per form
at depth3/IDs0,1 compares complete initialized Worker and naturally published
fullkey TT with only Move bit3 normalized; history/cont/corr/PVS/QS are exercised.
Function receipt c618e8566df3d0d49b403ccc0e05fd6649cb505f498bdd104bb6c727264cb25a
is separate from shipping/SMP/lifecycle evidence. DATA decoder2 restored exact
full native/BCJ bytes, canaries and table release. Cost receipt c6a21d6edd93cc8cd1e0d8d15157a263654df5730207c575cb5bbb0210287f76.

Both new CHECKPOINT images were discovered compile-only and admitted after
static readback: scalar5989/cbb4d82be9ec59f9b1111c1cb9ebafbc227c90e134d696a97979f8f6026e42bd,
HQ6198/8e19b1daa7bf0e450c12d28bc4e50dc91b35b9c9752a0351643259457b9790d3.
The ordinary builder reproduced each native/whole twice and each audit once;
build receipt8820abbf8bb205231028999cecc49d057b007700811746ec33d8ab238112db2e.
The existing positive verifier passed two pre-entry zero/RX/guard/NX observations
and four actual scalar/HQ quit/EOF sessions with12 legal GO results, stable3
startup TIDs and physical exit; receipt9d7ff8085c0c44c57fcfe35cc73ca5b7cacbae48bac74b644451b606c063aee8.
No prior negative/fault/RIE/ptrace/register/personality campaign was retried.
Old dead-state evidence below retains its original identity. All generated and
failed-preparation records stay external. Both complete files remain over4096.

# Maintained C D signed-state dead-material own-ELF

The selected source changes only dead()'s three accumulators into one signed state. Zero means no minor,-1 means one knight without bishops,1/2 means only bishops on one square color. A second knight, knight/bishop mixture, opposite-color bishops or P/R/Q is live; all remaining admitted cases are dead. The original recognition policy is preserved, including KNN treated live and arbitrary same-color promoted bishops treated dead. This is not a full theoretical dead-position oracle.

| Form | Native | Fixed21-v2 packet | Complete own ELF | Change from EP-share | Nonpacket |
|---|---:|---:|---:|---:|---:|
| scalar-shipping |7836|4850|5987|−15|1137|
| hq-shipping |8192|5057|6194|−26|1137|

Readable board grows37B to9044/fda8cf1e while actual total native text shrinks24B each. Scalar file length stays7836 with a new identity; HQ8224→8192. Both forms now have literal RX2 at400000, BSS402000/175092B/43pages, guard3ff000/42d000, reserve2f000, zero-file RW and NX stack. Scalar entry401d0f, HQ401e4c. HQ keeps its declared0810217e model; page count never selects the model. Packer admits only the two exact identity/form/geometry tuples and matching size/entry/model keys. No generic image class is admitted.

All other7 native sources and loader/codec/models/range/flags/profile are unchanged. Fullkey aligned16 TT, HCE/PVS/QS/history/continuation/correction, repetition/halfmove/mate precedence, persistent clone/futex pool and completion fences retain their prior implementations. The changed function has actual positive coverage on109 proper two-king canonical FENs against independent count/color material logic, both signs, P/R/Q,0/1/multiple knights,same/opposite/multiple promoted bishops and mixed minors; both functions leave Board bytes unchanged. Receipt b5c9ccbc47fd5fa72663638c398525f65c63bd64157fc65d14425a1d7c36a86f is a function unit, not an engine runtime.

First-cost DATA helpers restored both complete BCJ/native byte strings exactly with canaries and table release. That is separate from entry/mapping execution. CHECKPOINT scalar6010/dfcce0ad andHQ6217/d691c451 were discovered by two compile-only commands and admitted after full static ELF/packet readback (root intake d4dd0b240ff8d61b2862002a3ed5ea366f3059f65b854f52aa0d2f06936e5bcc). The unchanged ordinary builder was called once and reproduced both native files twice, both shipping own-ELFs twice and each audit once, matching the exact first-cost/discovery identities. Build receipt:5f198f4a25d62c01c20ed689fd39072a8b7ddfac7e444431bfdb8bf49703b732. The current positive verifier was called once:two CHECKPOINT initial BSS/RX-padding zero, exact RX native bytes and lower/upper guards/NX observations resumed the original entry, then four scalar/HQ quit/EOF sessions returned12 legal GO results with stable three startup TIDs, only stdio/no child, joined readers and clean physical exit. Verifier results:ae352db6ae110f16c1f6c12e59f38d0bdb10a8a5da34bfa8507e3428264f3df3.

The two actual commands return0/pipe EOF/owned group absent/forced cleanup0. After both ended, the external driver incorrectly read runtime.json although the verifier wrote results.json, so that driver exits1 and its original report remains complete:false with FileNotFoundError. No command was replayed. Read-only companion5aecb6ffb239b7595383a383ca59a31852e76f4ea3554480869f5548eb92a59d records actual_commands_complete:true and outer_driver_complete:false; it does not turn the failed outer run into PASS.

The producing21 source manifest acd5a0b3e7298e3fdb8035c5ef1e790d60ed6ebe1e014f9b8c7f28800763e1a4 and actual builder inputs/recipe are preserved. Only README and qualification metadata change at final close; all producing code, exact expected identities, flags, profile and guards remain fixed. No fresh, old decoder-negative test, intrusive/fault campaign, game, strength or benchmark was run. Existing source ancestry and prior negative/fresh receipts retain their original scope. The current selected files remain over4096 by1891/2098B. The existing ordinary build and current positive verifier bodies remain unchanged; its positive CHECKPOINT stop/read-only observations/resume and four shipping sessions completed in the separately recorded actual verifier call. No fresh or negative/fault/RIE/ptrace/personality/register campaign is added. Historical EP/atomic128 results below remain their original ancestry and are not relabeled as this native execution.

# Maintained C D EP trial sharing and atomic128 TT own-ELF

EP canonicalization delegates its boolean legality trial to the existing make
path. The geometry checks prove a nonpromoting EP capture from a provisional
parent with valid side/king and pieces. Parent h/r may still be unfinished;
the trial child is discarded. Legality reads no h/r/v, and child e=-1 ends
nested EP immediately. The make contract comment records this narrow additional
caller. No other board, search, runtime or TT logic is changed.

| Form | Native | Packet | Complete own ELF | Change from atomic128 normal | Nonpacket |
|---|---:|---:|---:|---:|---:|
| scalar-shipping |7836|4865|6002|−62|1137|
| hq-shipping |8224|5083|6220|−33|1137|

Scalar native SHAad76de1424f4de80cbb5c9c19966cb666716c2ed6fc9703d3a2400daae4f3268;
whole SHAa95c25d791a39bb3d6d05fec010eb5407249c51fd9b2ad02be6045d8dd9c4b04.
HQ native SHA1c5d426eafa3100e82bd659fac8b347a9686e80f91849c27e5c534d954e8dfe5;
whole SHA1a5060465975f99bafb0a961b3e5b362b09b2180465272dbe3103a4e59544156.
Raw board source grows237B. Text shrinks73B in both forms; complete native
shrinks96/64B including alignment. These are separate actual measurements.
The complete files remain larger than4KiB.

Focused ordinary ASan/UBSan scalar/HQ units each cover20roots,150full-state/
child records and26FEN/history observations against the unchanged control and
independent hash/HCE/context oracle. Both observed actual make/ep maximum
call depth2 and passed. This unit evidence is separate from shipping native
execution. Unit SHA2e21ea646a7dfddc3c55d7e95bccb6ba80278a5f44b8b72a025f2f11c446a69d.

The execution profile stays linux-x86_64-sse4.2-cx16-crc32b-v1; before target
launch the verifier requires sse4_2 and cx16 on every affinity-available CPU.
Generic x86-64/current tournament-server ISA compatibility remains unverified.
The earlier official4K wiki429 response remains an unsuccessful check.

The aligned16B full64key/payload TT and its two CMPXCHG16B operations are
unchanged: one coherent read and one conditional write/drop without retry or
acknowledgement. WORKERS2, TT_BITS18, PLY128 and4MiB TT mapping stay fixed.
Fresh mmap zero-state startup, DEV quiescent wait/clear, learning/correction,
mate/bound/context handling and scalar/HQ algorithms remain the qualified
atomic128 implementation. Its positive unit and prior normal observations
remain separately scoped evidence, not new executions of these EP images.

The fixed21 CRC32 byte decoder/encoder/models/range arithmetic, BCJ, zero4,
full output bounds, both linkers and all compiler flags remain unchanged.
First-cost DATA helpers decoded each new packet to exact native bytes with
canaries and owned context table munmap, without entering the native image.
Scalar layout is RX2 at400000/BSS402000/entry401d27; HQ is RX3/BSS403000/
entry401e64. BSS175092B rounds to43pages. Existing exact guards/reserve, NX stack,
RW→RX and private guarded1MiB worker stacks remain the fixed mapping contract.

Finite-minimum UCI stays uci/isready/position startpos moves/go clock/quit/EOF,
without optional id/options. Shipping consumes stop/ucinewgame/infinite without
DEV semantics. Missing own clock gives1000ms budget, not a hard wall-time cap.
Next go, position, quit and EOF acquire pending0 after complete result output.
Persistent clone/futex ownership, partial-create bypass and clearTID joins stay
unchanged. Build/fresh/oracle and CPU/lifecycle/mapping verifier bodies stay exact.

Root admitted the actual new CHECKPOINT1 identities after full static readback:
scalar6025B SHA81931ddcd89feed7f87d5849db20ab0b21150ea7c63f30b207316986ed32b658;
HQ6243B SHAe894c94a6917aaf43817792659fefb0ff0716cf1f3c66da6d1be5e25613fbead.
Root intake SHA cbc7027129819d0d806823e60a3a978984e889a4523f90a5d0a6e1f18c617cfe.
Only exact literal identities replace their predecessor entries; guard/model/
permission bodies remain unchanged. Old6087/6276audits are not reused.

Current source23 was preserved before the five-file normal edit. The old
atomic128 whole6064/6253 and its successful normal build/positive receipts are
predecessor records. Earlier CRC discovery terminal1/raw complete:true and
TT-unit driver parse failure remain preserved with their actual boundaries.
No previous failure is repaired or relabelled by this new candidate.

The sole unchanged normal builder completed terminal0 and independently
reproduced native4/whole-loader4/audit-loader2/encoder4 exact identities. The
sole selected positive verifier completed terminal0: shipping quit/EOF4sessions,
12GO and positive pre-entry2 passed. Local affinity CPU0..7 exposed CX16 and
SSE4.2. Restored native/RX padding, initial BSS/paddingzero, guards/NX and
original entry resume were observed. Shipping retained startup3TIDs, private
guarded1MiB worker stacks, onlystdio, no children observed and legal white/
black/active results. Readers/process groups settled naturally, forced0; all
recorded TIDs were absent on readback. No fresh invocation was performed.

Normal build SHAfed982d44a7ec06641b442135751329043a205cf438d02518c762ea5a54a0d50;
positive verifier SHA3786ac409f2c60e18b261d43fbbafdf07cc0a1d5ffc661770e33c47bca97382e;
readback SHA630e7b4842624fd77c22a05583b7331928deb0f4f9f9ad483bd4b5eded1817a9.
Producing source23 manifest SHAa7c4ad7442df2c8123691dbba9c45db936dd2421da2c228f9bdca36dee2a0b3f,
recipe SHAce5f08c746724861eee9bb4bd91585b3b786880595248af4cef249688f2c44ec,
verifier SHAbc11ea494a6b812f15d0a957712086d1de211e76ccff046a8fb1339360b6a921.
Only this README and recipe qualification metadata were overlaid after that
run; other19local files and producing recipe fields remain exact. This is not
a second execution. The unchanged builder does not separately observe compiler
descendant/group absence. No general TT/SMP race freedom, contention-drop
causality, strength/performance, ignored-control/default-budget timing, exact
decoder-table unmap causality or tournament CPU compatibility is established.

The source closure stays21local files plus oracle/LICENSE=23. No negative/
RIE/ptrace/register/personality, game, benchmark, training or paid-resource
campaign is part of this work. Earlier source/proof/failure boundaries remain
explicit and are not retrospectively relabelled as runs of this EP image.
