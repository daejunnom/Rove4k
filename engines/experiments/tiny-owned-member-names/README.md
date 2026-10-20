# One exact F owned-member map

This source-only experiment admits only the maintained F post-scope shipping C:
10,011 bytes, SHA-256
`4e7a2a76ea753ebc3ccbcb4371ea76810c06b193e45b2f6ca70e66bd79112e9a`.
It reads the existing external source file without making a control source copy.
It changes owned struct FieldDecl/member-reference physical identifiers after
the existing alpha, storage and scope stages; those stages and DEV are untouched.

The fixed candidate is **9,954 bytes**, SHA-256
`00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916`.
Exactly 13 fields and 57 physical tokens change, saving 57 source bytes.

| Owned record | Literal field-name changes |
|---|---|
| `za` (Board) | `zB` to `a` |
| `zb` (Entry) | `zF` to `a`; `zt` to `b` |
| `zc` (Worker) | `id,zu,z8,zf,zU,zG,zK,zC,zp,zq` to `a,b,c,d,e,f,g,h,i,j` |

Names are unique within each record. Reusing `a` across the records and with
ordinary local/global identifiers is confirmed by declaration-bound AST edges,
not spelling lookup. The atomic-macro member `zb.zN` is excluded entirely:
its expanded uses are macro-affected/nonphysical. One-letter existing fields,
typedef/tag names, ordinary identifiers, header fields, literals and macros
remain unchanged. In particular `tv_sec`, `tv_nsec`, atomic header `_Value`, and
the UCI `id name` literal are protected.

members.py calls the frozen tiny-scope-names API SHA
`02ca17d1c251945f1c021e3482272ef891485c2227a90b4712a36b987d29f08b`
for parse/snapshot/canonical-key and position-bound inverse. It does not modify
or copy that API, create a general parser, or invoke the normal engine builder.
inputs.json pins the exact source, API, 13 field identities/occurrence sets,
external libclang18.1.1 site-v2 files, and all 79 actually included headers.
Real Clang18 resource headers are used; no toolchain is vendored here.

The one actual candidate passes exact inverse, expected declaration shapes and
the whole 2,463-edge referenced-declaration graph. Every edited token is a
physical FieldDecl/MemberRefExpr token annotated with its exact field identity.
Wrapper reference edges must share one of those physical member positions.
All other physical tokens, literal/comment bytes, macro signatures and external
references stay unchanged. Record/field order, canonical field types, qualifiers,
arrays, bit offsets, size and alignment match after reparse. The fixed records
remain za176/align8, zb24/align8 and zc68976/align8, with 22 fields in total.
Asm, name/offset observers, attributes, anonymous-member/bitfield extensions or
unconfirmed occurrences are outside this exact-input policy.

Execution was limited to one original-input inventory parse and the adapter's
two before/after AST parses. Native compile, external PP command, codec, engine,
game and benchmark counts are zero. Source shrink is not a measured native or
whole-file gain; no runtime qualification, promotion or 4KiB claim is made.
The external receipts preserve the candidate, exact edits and tool/header pins.
Maintained/shared source, the frozen API, Git and global docs were not changed.
