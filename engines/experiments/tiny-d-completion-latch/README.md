# D completion latch: one native-first source candidate

This isolated experiment freezes the qualified maintained D's 18 ordinary
sources from commit `1f35a6e`. The control runtime is
`82c62b57e500918827721553d67d9e23073c6cb5ca79dc22cdb8e38ab15f8e63`.
`transform.py` changes seven exact runtime fragments and checks the inverse
complement. The one resulting runtime is 15,123 B, SHA
`5b20d4e60d60b5edfb4b7b5a15217346098f0bd9ccdd155a7369c90743e81ed1`;
the original is 15,249 B, a 126 B readable-source reduction. No external engine
or synchronization source is copied. Source size is not native or whole size.

## First native cost result

The one authorized fixed campaign reproduced all four literal control native
builds before any candidate build. Both candidate native and linked ELF pairs
are byte-identical across their two builds. All eight compilation commands and
two compiler/linker metadata commands exited 0 without forced cleanup or errors.

| Actual item | Scalar control | Scalar candidate | HQ control | HQ candidate |
| --- | ---: | ---: | ---: | ---: |
| Whole stripped native | 8,124 B | **8,092 B** | 8,512 B | **8,480 B** |
| `.text` | 7,607 B | 7,570 B | 7,913 B | 7,876 B |
| `.rodata` | 284 B | 284 B | 352 B | 352 B |
| `.data` | 0 B | **0 B** | 0 B | **0 B** |
| Actual `.bss` | 175,092 B | 175,092 B | 175,092 B | 175,092 B |

Both native files save 32 B; text saves 37 B. This is a small native saving,
not a measured complete own-ELF reduction. The BSS extent remains unchanged;
removing two atomic objects did not reduce this measured extent or page count.

Scalar native SHA is
`59829299f667cdb6682c5ed4a955fb50b76a5584209caf9e4bddf1c0ee2cd160`,
entry `0x401e28`, RX 2 pages at `0x400000`, BSS `0x402000` over 43 pages.
HQ SHA is `f1d6558ec5a13e400c2d6df182b01b3236bf1ee1e99f686e47f144a32d222c5c`,
entry `0x401f5a`, RX 3 pages, BSS `0x403000` over 43 pages. The parsed segment
set is exactly RX flags5 with file/memory size equal to the native file,
RW BSS flags6/filesz0/memsz175092 and non-executable GNU_STACK flags6.
Linked `.bss` is matching NOBITS storage; there is no interpreter, file-backed
writable data, WX segment or executable stack. These are static ELF observations,
not observations of restored mappings or initialized runtime memory.

Both current page geometries are retained. Derived loader geometry would retain
lower guard `0x3ff000`, scalar upper guard `0x42d000`/reservation `0x2f000`, and
HQ upper guard `0x42e000`/reservation `0x30000`; none is newly admitted or run.
The unchanged strict old packer rejects both as unknown native identities.
Root must review the new file/hash/entry declarations before any whole stage.

The original first-cost receipt is
`/home/stemxstudio/rove4k-tiny-d-completion-latch-native-20261020-v1/build.json`,
SHA `e8b23315a1f1a6756ec3b4a909d56de4b42ee01475fa9989b13c9b54c587b468`.
Its command is terminal 0. The separate immutable native-intake index SHA is
`b283ba4a56fca8281954c1baa03a8503ac77762d9fc82372c61ac03ab7dd2759`;
it preserves the original 23 producing inputs and all 86 files, including raw
headers/PHDRs, sections, eight native/linked pairs and logs. Its original no-pack,
no-execution and unqualified flags remain false. This later README does not
rewrite that original checkpoint. No candidate is promoted.

## Single-latch ownership model

Only `ready` and `completed` storage and their counter consumers are removed.
The persistent workers, `epoch`/seen deduplication, quitting publication,
full search/TT state, clone ABI, guarded stacks and kernel-CLEARTID joins remain.

| Stage | `pending` meaning | Completion rule |
| --- | --- | --- |
| Before clone | main runtime-stores WORKERS into zero-initialized BSS | no nonzero static data initializer |
| Worker entry | each worker release-decrements once, then wakes | main acquires 0 before reading input |
| GO publication | main stores WORKERS+1, then release-increments epoch | epoch acquire publishes job inputs |
| Finished searches | each worker acq_rel-decrements once | old==2 selects the final worker |
| Result publication | value 1 reserves ownership for `result()` | 1 is not completion |
| Reusable idle state | final worker release-stores 0 after all output | main's acquire 0 releases job storage |

The final worker's acq_rel RMW acquires the earlier finish release sequence before
reading all worker results. The entire unchanged `result()` runs before the
zero store; main may not reuse workers, position or fallback while it observes
1. The new wait preserves the stopped store and loops on acquire `pending`
with expected-value futex waits. It does not infer completion from a decrement
alone or merely from receipt of a wake.

Startup uses the same zero wait after all clones succeed. This intentionally
changes private idle `stopped` from 0 to 1 before the first command. Epoch remains
0, so workers cannot search; GO resets stopped to 0 before publishing the epoch.
Identification, ready responses, finite shipping policy and DEV stop/newgame
consumers are unchanged. Every existing wait caller retains its output-before-
mutation fence through the new zero observation.

Late startup or completion wakes may cross the next GO and are harmless loop
notifications. Their corresponding decrements already preceded the acquired
zero, so an old-generation decrement cannot corrupt a new counter. Main's own
WORKERS+1 store precedes its later wait load, preventing reuse of an earlier
zero; the futex expected-value check handles a change between load and sleep.
Only main publishes jobs, and each new job waits for the preceding zero.

Partial clone/allocation failure still jumps directly to shutdown and **bypasses
the startup latch wait**: missing workers remain in its count. Quitting and
epoch wake release created workers, and the original kernel-cleared TID joins
cover exactly the successfully created threads. Normal quit/EOF still wait for
zero before shutdown. No stack/TID ownership or error path is replaced.

Two independent read-only source reviews found no concrete race/ABA/lost-wake
blocker under these exact conditions. This is source-model reasoning, not an
executed concurrency or fault qualification. Any actual future execution needs
its own bounded observations, including delayed publication and partial creation.

## Native-first boundary

The only source input is this folder's closed ordinary snapshot and fixed
producer/transform. No mutable maintained path, generated runtime, historical
report or executable is a build input. The frozen original recipe keeps
WORKERS=2, TT_BITS=18, PLY=128, DEV=0, GCC `-Oz -flto`, five-unit order and both
linker/loader/codec sources unchanged. The other seven native source files
remain exact. There is one runtime candidate and no spelling/flag/profile sweep.

First reproduce scalar 8,124 B and HQ 8,512 B controls twice each, before either
candidate is compiled. Then independently generate and compile each candidate
twice with exactly the same flags and unit order. No diagnostic linker-map flag
is appended. Actual linked sections and stripped whole-native bytes, full ELF
headers/PHDRs, entry, RX page extent, zero file-backed data and BSS zero-fill
declarations are measured. BSS memory is not observed. Removing two atomic objects may change BSS extent, so an
old size or page count is not forced onto the observation.

The old exact production admission remains unchanged and must reject a changed
candidate. The report's observed geometry is not a new loader admission. Root
must review it before any separately authorized whole-file or CHECKPOINT build.
Native savings cannot be called complete own-ELF savings. This stage never
compiles a loader, invokes a codec, starts a native/whole engine or executes a
CHECKPOINT. It makes no runtime, strength, throughput, scaling or 4k claim.

All generated sources, linked/native files, logs, source snapshots and reports
stay outside Git. Maintained18, frozen proof40 and all historical inputs remain
unchanged. Root owns commits, shared documents and any following qualification.

## Separately authorized whole first cost

The native checkpoint above is closed and immutable. Root independently read
the candidate native bytes, complete headers and three program headers, then
approved the exact new scalar/HQ identities and their unchanged per-form
geometry for a separate whole-file cost stage. `whole.py` regenerates every
input from this folder's ordinary source closure; the earlier report or native
files are not inputs. It first reproduces both 7,478/7,718 B control whole files
twice, then generates each candidate twice with the same fixed loader, codec,
compiler flags and resource profile.

The new admission binds each candidate's full native hash, length, entry and
complete layout to that single form. The frozen original packer and its strict
old admission remain unchanged and continue to reject these candidates. No
generic two/three-page admission, codec variant, CHECKPOINT build, fault fixture
or native/whole engine execution belongs to this cost stage. Whole-file results
will be reported separately from native savings and runtime qualification.

The one authorized whole campaign completed with all old controls and both
candidate pairs reproduced byte-for-byte. All eight newly regenerated native
builds retained their exact identities; the old complete-file controls were
reproduced before candidate packaging. No retry, variant or expectation update
was used.

| Complete own-ELF cost | Control | Candidate | Change | Payload | Loader and headers |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scalar | 7,478 B | **7,457 B** | **-21 B** | 6,342 B | 1,115 B |
| HQ | 7,718 B | **7,707 B** | **-11 B** | 6,592 B | 1,115 B |

The scalar complete-file SHA is
`08c40aa381953df98aa6d6f893487ff90d9a43854acd552158795ce795afcc70`;
HQ is `1178c3e22ac3a2e9db549ddb5246f9b197b7136fa0fc89008577c52468217963`.
The original whole receipt is
`/home/stemxstudio/rove4k-tiny-d-completion-latch-whole-20261020-v1/build.json`,
75,219 B, SHA `628ea7e3eccae0c20ade39997836a838b03e60ed128dc1eadc8a0119fd556bca`.
The separate immutable whole-intake index SHA is
`26054aa2fb495ad9490d85493261d1106428532fa0be76d15a519d8c58ca6f1b`;
its 178 files preserve the producing source24, fresh nested native inputs,
actual complete files, payloads, linked files and command logs. This result
section is a later README-only update and does not rewrite that receipt.

The whole command exited 0 with empty failure and cleanup lists. Its nested
native producer and eight loader commands all exited 0 without forced cleanup;
each loader used CHECKPOINT=0. These small complete-file savings do not establish
runtime qualification or a 4k entry. No native/whole engine, restored mapping,
CHECKPOINT or fault fixture has executed. The pending-latch concurrency model,
partial-startup failure and physical quit/EOF behavior still require their
separately authorized actual-runtime stage.
