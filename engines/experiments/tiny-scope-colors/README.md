# F source-only lexical alias reuse prototype

One deterministic policy starts with the frozen function-wide automatic-name
allocator's exact eligibility and physical declaration/reference inventory.
Declarations are visited in source order. Each tries aliases in the fixed
lowercase/uppercase length-lexicographic order. Names may be reused in another
block or shadowed region, including names of unchanged short automatic locals.
Global, static, member, type, ABI, keyword, macro and referenced external names
stay reserved. The original macro/opaque/asm/name-observer exclusions stay in
force through the frozen reference inventory.

Every trial reapplies edits at original byte positions and independently
reparses the whole translation unit. A trial is accepted only when declaration
ordinals/shapes and the entire observed source-ordered CIndex reference projection
agree with the original, except for the declared local spellings. This checks declaration
point, shadowing and ordinary initializer capture through actual C binding.
Exact position-bound inverse and a final independent parse are required. This
projection is not all AST nodes, edge multiplicities or hidden type semantics.

This is a conservative greedy policy, not an optimal graph coloring algorithm.
Future declarations retain their known-safe function-wide assignment while an
earlier declaration is tried. A jointly possible recoloring may therefore be
missed. Alias trials are semantic admission checks, not a codec search. Raw size
may remain equal to the function-wide one-character baseline; increased reuse
could affect compression, which has not been measured.

The first prototype admits only F post-storage 10477/c63. The reference source,
external libclang inputs and real resource header are pinned. It does not claim
arbitrary C equivalence from a type-kind snapshot. VM/VLA declarations, array
parameter forms, bracket-containing sizeof/alignof operands, typeof, generic
selection and compound-literal type contexts are outside this first policy.

Only colors.py and admission/prose are prepared. This initial document precedes
execution; it is not a parser or cost receipt. Source-only trials have a fixed
60 second soft budget, checkpoint each accepted graph-safe state, and retain
the known-safe fallback or best-so-far when incomplete. Native, codec, engine,
game and benchmark are outside this prototype. Reports and any
candidate must be written outside Git. The frozen tiny-scope-names source
is referenced by explicit path/hash and is never modified or copied wholesale.

The actual greedy experiment stopped conservatively twice: first on an
unclassified parameter redefinition, then on unclassified int-to-Move-pointer
conversion errors. Both failed executions and their incomplete checkpoints
remain preserved. The final best-so-far reached 20 of 98 declarations and 56
checkpointed greedy trials. It is 10011 bytes, the same raw length as the
function-wide fallback, with only two declaration assignments/four physical
identifier occurrences redistributed.

A separate final validation of that unchanged checkpoint passed exact physical
forward/inverse, protected shapes and the observed CIndex reference projection.
Greedy remains incomplete, selected=false, and native/codec/engine executions
remain zero. The owned source archive contains four files; each external
execution snapshot additionally freezes one pinned reference.py dependency
(five files total). The reference folder/framework is not copied into this
prototype. This status paragraph is a metadata-only post-execution update;
the executed colors.py, inputs.json and .gitattributes bytes are unchanged.
