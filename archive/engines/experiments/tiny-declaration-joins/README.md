# Adjacent scalar declaration inventory

This source-only lane proposes one conservative declaration-join policy for the
exact maintained F shipping C, 9,954 bytes with SHA-256
`00239e23500d41c45801cdb19c4e7c8cc8b22cf29bebd7e4fbc8fdd1e08c7916`.
It reads the qualified source outside Git and never copies that source into the
repository. Normal entries and existing shared/experimental tools are unchanged.

`inventory.py` reuses the frozen scope AST API
`02ca17d1c251945f1c021e3482272ef891485c2227a90b4712a36b987d29f08b`
with the recorded external libclang 18.1.1 and real Clang 18.1.3 resource headers.
It parses exactly one AST. All diagnostics and admitted original locations are
written to a new external `inventory.json`. It constructs no changed C, invokes
no native compiler or codec, and runs no engine.

The proposed policy considers immediately adjacent `DeclStmt` siblings in the
same `CompoundStmt`. Each statement must contain exactly one implicit-automatic
arithmetic scalar `VarDecl`, with an identical raw explicit type prefix and the
same bound type, qualifiers, size/alignment and typedef references. Pointers,
arrays/VLAs, enums/records, storage-class specifiers, volatile/atomic types,
attributes, type observers, macros and opaque join boundaries are excluded.

An admitted boundary proposes changing the first semicolon to a comma and
removing only the second declaration's repeated type prefix. Declarator order,
every initializer byte, existing scope and the relative declaration points must
remain fixed. The inventory counts duplicate-prefix bytes arithmetically;
these are unmeasured source targets, not a generated candidate, native equality
claim or compressed whole-file saving.

Policy review precedes any mutation. A later authorized candidate would need
its own physical-span/inverse checks, real AST reparse/binding checks and actual
native/whole measurements. This inventory does not establish those results.

The first recorded inventory parsed 34 main-file functions and 88 compound
blocks with no diagnostics. Of 77 direct declaration statements and 27 adjacent
pairs, this policy proposed only two join boundaries: the `i`/`j` declarations
in shipping function `ad` and the `m`/`o` declarations in `aG`. Each duplicate
prefix is exactly `int `, four bytes. Total raw target is eight bytes; 9,946 is
only the arithmetic length after those proposed deletions. No candidate or
native/whole result was generated. Existing multi-variable declaration
statements are deliberately outside this first policy.

Both second initializers reference the preceding variable. That is compatible
with the proposed preserved order: C11 N1570 sections 6.8 paragraphs 3–4 order
automatic initializations by declarators and treat each initializer as a full
expression; section 6.2.1 paragraph 7 starts each identifier's scope after its
own declarator. This source inventory is not a general proof for GNU extensions
or a substitute for the later binding/native checks.
