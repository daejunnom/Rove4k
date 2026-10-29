# D residual leaper walker: one first-cost candidate

The exact D board walk processes a=3/4/5 with d_sliding and then continues
in both attack and generation modes. Every remaining own piece is therefore
a=1/2/6 on admitted boards. The former generic ray visits at most one valid
destination per direction: its a<3||a==6 termination is always true here.
This candidate removes only the dead a==3/a==4 range branches and replaces
that inner ray with one bounded destination check. No new direction table or
piece representation is introduced.

Pawn directions remain white12..13/black14..15, knight0..7 and king8..15.
The order is still 0x88 boundary, attack-target return, friendly/pawn-EP
generation filter, then add. Attack-target return deliberately precedes the
friendly filter so attacks on defended friendly squares remain attacks.
Pawn pushes/doubles, all four promotions, king/castle order, legal EP and
own-king legality remain outside the exact changed fragment.

start creates only signed1..6, DEV FEN admits only PNBRQK, and successful
generated make preserves this domain (promotion2..5, rook4, pawn/zero EP).
EP temporary boards also modify only pawn/zero. Runtime replay/fallback,
search and DEV perft/legal apply gen members; TT moves only order that list.
This is an admitted internal Board/caller contract, not a promise for raw
arbitrary piece bytes or arbitrary make inputs. No bound or legality guard
is removed. An independent existing child read-only review found no blocker
under these exact ranges/order/domain conditions.

Only this producer/recipe/transform is maintained here. It requires the exact
current normal recipe and source hashes, freezes one external ordinary input
tree, and transforms board only with byte-exact inverse reconstruction. Seven
other native files and all loader/encoder/model inputs remain unchanged.
Normal packer.admit is never called for a new identity or changed. Experimental
admission explicitly checks sectionless static ELF64, all three PHDRs, NX,
zero writable file bytes, entry extent and per-form RX/BSS/guard geometry.
Scalar must stay RX2; HQ may stay RX3 or shrink to RX2. BSS must stay175092B,
rounded43pages, with inaccessible surrounding guard pages. Unknown geometry
stops before encoder/loader. No broad normal image permission is introduced.

```sh
python3 -I -B engines/experiments/tiny-d-leaper-walk/build.py \
  --out /absolute/new/external-cost
```

Fixed current native flags/unit order and WORKERS2/TT18/PLY128/DEV0 are used.
Actual old native/whole bytes are hash-checked without copying or compiling.
Native2 are compiled once, then both strict static structures are checked.
Only then the fixed context encoder and exact BCJ loader run once per form
(CHECKPOINT0). Native identity equality, source/section/full-file costs and
actual complete whole differences are observations; no repeat or performance
claim is made. Compiler calls are bounded/owned and all outputs stay outside
Git. Target/audit/fresh, negative/fault/stub/game/benchmark runs are0.

Even a smaller whole is only first-cost evidence. It requires separately
authorized functional qualification before any normal promotion.

## Frozen first-cost observations

One fixed invocation completed: native2, independent fixed encode2 and
CHECKPOINT0 loader2. No compiler/native/encoder repeats or retries occurred.
All four compiler commands returned0 with empty stdout/stderr, killpg_sentFalse
and owned groups absent. Target/audit/fresh/negative/fault/stub/game/benchmark0.

| Form | Native old→new | Text delta | Packet old→new | Complete whole old→new |
| --- | --- | --- | --- | --- |
| Scalar | 8060→7964B (-96) | -103B | 5020→4979B | 6313→6272B (-41) |
| HQ | 8448→8352B (-96) | -92B | 5213→5159B | 6506→6452B (-54) |

Board8880→8770B is source-110B, SHA
d412aa04f0609c0b10217d021f18fc2a888b863ece09064ffd9ad02a337963db.
Only board changes; other native7 and all codec/loader/model sources remain
exact. Native new identities differ from controls, so no prior native equality
or prior candidate runtime qualification is claimed.

Scalar native SHA24a6856e00fb902a2c11580616a8048f2832f8b9d0cf35a29a8861e5841eedb8,
entry401d97/RX2/BSS402000/upper42d000/reserve2f000. HQ native SHA
6acbd92ccd37b51b6745115336576a15ddaa1018e6521471a98e295bc2308626,
entry401ed4/RX3/BSS403000/upper42e000/reserve30000. Both remain sectionless
static ELF64 with3exactPHDRs, RWfilebytes0, BSS175092/43pages, NX stack,
guard3ff000. These are static byte/layout checks, not observed mappings.
Read-only data284/352B and zero data are unchanged; text is7425/7742B.

Actual whole scalar SHA
145cba2da1fd883b00b4f61ba825a2a87f69ddceb105504213d1b793041fae0c,
HQ SHA c42602b427c98b88f7cf25ec1223634ae85a36c63e3b76790cf3ba920795a38f.
Outer entry100000b0/base10000000 and sectionless singleRX/NXstack remain.
Packets4979/5159B include29Bheader+4946/5126Bbody+4realzero tail;
actual header/loader overhead1293B is unchanged. Full receipt SHA
96e7eda66d500b312e93f47b42fe55896f8f0f10bbf14ebfd8da6b84b14bc443
is preserved externally. Producing5 is separate from this README-only overlay.

The positive size results remain first-cost only. No new native or whole ELF
was executed, no actual decoder restoration/Board legality was observed, and
normal admission/selection remains6313/6506 unchanged. Functional fixture,
runtime, new audit and fresh promotion require separate authorization.
