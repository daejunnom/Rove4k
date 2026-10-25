# D worker-owned job reset: one native-first candidate

This is a semantic ownership rewrite in runtime.c, not object-identical
spelling compression. It removes go's all-Worker reset loop and sets only
w->best=0 after work's seen=current, immediately before unchanged think.
Think already resets nodes/depth/score; its direct-call seeded-best API stays
byte-identical. No other native source or public protocol is changed.

The source proposal and independent static review are preserved outside Git;
proposal SHA f85e247be08fe8407411b96b4a78cf9e04f35c2bbb25b733958e2b731a2da99a.
The accepted ownership chain remains epoch release/acquire, worker-local reset,
think, acq_rel pending 3/2/1 completion, output reservation1, output then
release0/main acquire0. Quitting, startup partial-failure bypass, guarded
stacks, kernel-CLEARTID joins, full-key TT, all promotion/legality and clocks
are unchanged. The extra reset must never enter the idle loop or think body.

Only this folder's transform/recipe/producer and documentation are maintained
here. Exact ordinary native8/parser inputs are read from maintained tiny-entry-d
with explicit SHA admission; changed originals fail closed. No original/control
source tree or historical generated source is copied into this experiment.
The producer emits one external candidate-source8 (seven unchanged inputs plus
the one transformed runtime). Exact original runtime is required and an inverse
transform proves the untouched complement. The selected codec/decoder/loader,
normal recipe and normal packer.admit remain unchanged.

```sh
python3 -I -B engines/experiments/tiny-d-worker-reset/build.py \
  --out /absolute/new/external-native-cost
```

There is one candidate and fixed WORKERS2/TT_BITS18/PLY128/DEV0, fixed native
Oz/LTO flags/unit order and x86-64 raw ABI. Four old actual source-qualified
native repeats are hash-checked without running or recompiling them, with the
old linked files bound to the same exact native bytes for section costs.
Each candidate form is compiled once. These new binaries are not independently
repeated, and are not admitted by normal exact-image guards. Parsed entry,
PHDRs, text/read-only/zero data/BSS and derived guard geometry are static
observations, not restored mappings or RAM measurements.

The entire native costs include ELF headers; 46B old go stores are gross
observations and are not a net saving prediction. Source fragment reduction
is 96B without extra shipping comments. No whole/encoder/native-target/audit/
fresh/negative/game/benchmark command belongs to this stage. Root must inspect
new identities/layout before a separately authorized whole or runtime stage.
Failures retain incomplete receipts and owned compiler output. Compiler calls
are serial, with aggregate120s, each45s wall/30sCPU/2GiB address-space limits;
owned process groups are settled. All generated files/logs stay outside Git.

## Native first cost and separate whole first cost

The original two native compiler commands exited0; there are no candidate
native repeats. Scalar8092→8060B and HQ8480→8448B, each native−32B.
Text7570→7528B and7876→7834B, each−42B; ten more alignment bytes absorb part
of that text reduction. Read-only data284/352B, zero initialized data and
BSS175092B remain unchanged. Runtime15123→15027B is source−96B, SHA
51902e800066562f7dbc5d240db57a6635b20c74ed8fede3a4cd71329fc62a38.
Source8set23700202ce6574379cee0303e8da3a7f72080e1de5cbed741407ad5e83de7782
has only runtime changed. Original native receipt a7fea2a6950f6a5d93f15ea902b425839c63059b7aefb9f67bb4daa6e5d74f76
was produced by build33031ef; after that success, source-only review fixed
failure completeFalse, TERM-masked cleanup/final save and killpg_sent tracking.
Final build6757f71 was read-reviewed CLEAR but not rerun. Original producer5
and receipt remain separate; its absent killpg_sent field is not inferred.

Root then read both exact new natives and approved their separate literal cost
admission in whole.py. Normal packer.admit/recipe/source21 remain untouched.
whole-recipe.json fixes native source8 and two actual native paths plus the
normal own encoder/decoder/model/loader pins. No native/control compile or
control tree copy belongs to this separate stage.

```sh
python3 -I -B engines/experiments/tiny-d-worker-reset/whole.py \
  --out /absolute/new/external-whole-cost
```

| Actual form | Native SHA | Entry / RX | Complete own-ELF | Full whole SHA |
| --- | --- | --- | ---: | --- |
| Scalar | 381fd1f478b090372365371d39337920c11fee4ab04ed59ab8616d0286b125d1 | 0x401dfe /2pages | 6387B | 4c2f7a8839f2d97c19631bf010050fccf3c90df67b7aef5e321cf1412d4b0df8 |
| HQ | 215ee72678b41032e7f3283bf40fda752f385833df46d2b430bfc2d5c5f89008 | 0x401f30 /3pages | 6580B | 07bedfa1707c302fe29d776f0c25b3a63c5bc560a8de4cd08abb96db90ede3a8 |

The full whole files save14/34B against6401/6614B. Each was encoded and built
once, with no repeat/variant/retry. Scalar packet5020B=29header+4987body+4real
zero tail; HQ5213B=29+5180+4. Actual overhead1367B=176ELF/PHDR+1191text,
with no other allocated section/padding. Outerentry100000b0/base10000000,
sectionless singleRX LOAD and NXstack remain. NativeBSS is402000/403000,
43pages; derived upperguard42d000/42e000 and reserve2f000/30000 match each
old form. These are static geometry declarations, not observed mappings.

The whole receipt c89c7ec1a595ded61c11844352e80f244149eb29088eaa62b3ec6499ce9d2063
records exactly encoder2+CHECKPOINT0loader2, both compiler rc0, killpg_sentFalse
and ownedgroups absent. No native/control compile, target/audit/fresh/negative
execution occurred. The fixed encoder applies one BCJ internally. All seven
producer sources plus actual source8/images/reports are hash-bound externally.
These measured gains are not functional qualification, normal promotion,
independent byte reproduction, performance/strength or a4KiB entry claim.
Further focused ownership/shipping proof is a separately authorized next stage.
