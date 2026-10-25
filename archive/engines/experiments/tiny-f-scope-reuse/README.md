# Exact current F local alias reuse

This independent source-only experiment admits only shipping F9728 with SHA-256
845f731a0f1fabd62bae629ad191aadd39525d0db7d59628224e315f09c0519d.
It does not invoke the old long-name eligibility policy. Physical ordinary
automatic locals and real definition parameters, including one-character names,
are inventoried directly through the frozen Clang API. Macro/opaque-affected
declarations are excluded in their entirety. Global/static/member/type/ABI and
external names remain unchanged and conservatively reserved. Unsupported
name/type observers, VM/VLA and special declarators fail closed.
Excluded automatic-local names keep their bytes but are not globally reserved;
an alias may reuse their spelling only when every observed reference, including
those excluded declarations' references, retains its original binding.

One fixed greedy pass visits declarations at their original source positions and
tries lowercase then uppercase aliases in length-lexicographic order, never
increasing a declaration spelling's length. Future declarations retain their
original assignment until visited. Unchanged automatic-local spellings may be
reused only when actual C parsing preserves the complete observed binding
projection. This can miss a simultaneous recoloring. It is not optimal coloring
or a codec objective/search.

Each trial is reconstructed from the original input. Every accepted state has
zero parser errors, exact declaration and type shapes except admitted local
spellings, exact observed source-ordered referenced-declaration projection,
unchanged remaining physical tokens, literal header closure, and exact
position-bound inverse and byte complement. Any main-source parser error rejects
that alias. Resource, nonlocal, fatal and infrastructure failures abort the pass;
no error is accepted. The first rejected candidate and raw diagnostics remain
outside Git. There is one 60-second soft-budget pass with accepted checkpoints
and an independent final parse, including when the budget leaves it incomplete.
No automatic restart or repair is performed.

The frozen tiny-scope-names API is imported by exact raw hash. Existing colors.py
was read for policy comparison, not modified or invoked. ice4's GPL-3.0
minifier/renamer.rs at 2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19 was read outside
Git only: it assigns names from weighted interference groups, whereas this
implementation uses physical CIndex declarations and deterministic reparse-gated
trials. No ice4 code or external tool is copied into this repository.

Ordinary producer/admission files must be frozen outside Git before execution.
All reports, candidates, checkpoints and archives go outside Git. This document
precedes the one pass and is not a result receipt. Native, preprocessing, codec,
engine, game, benchmark and normal producer executions are zero in this scope.
Whole gain is unknown. A CIndex reference projection and fixed-source type/layout
checks do not prove arbitrary C equivalence or actual native identity.

The first execution admitted 169 one-character declarations but aborted after 30
completed declarations when a parameter collision emitted enough ordinary
diagnostics to trigger Clang's locationless Fatal error-count limit. Its exact
source4, first rejected trial, raw Fatal and accepted checkpoint are archived
outside Git; it has no independent final validation and remains incomplete.
Following explicit authorization, v2 adds only `-ferror-limit=0` to the parser
arguments and performs one fresh bounded pass. The producer algorithm is
unchanged: every main-source Error still rejects the alias, and genuine Fatal,
nonlocal/resource errors or infrastructure exceptions still abort. This
paragraph precedes v2 and does not assert its result.
