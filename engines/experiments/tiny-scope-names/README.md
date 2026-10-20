# Function-wide automatic names

This independent experiment changes only physical automatic-local and function
parameter identifier tokens in admitted shipping C. Aliases are unique across a
whole function and the allocator restarts for the next function. It does not
reuse names by lifetime or change global, static, function, type, member, ABI,
header, literal, compiler, resource, transport, or engine logic.

`rename.py` uses an explicit external libclang installation and real Clang
resource headers. Main-file declarations and macro definitions have stable
ordinal identities; physical token annotations must confirm every edited
declaration/reference. Macro definitions retain exact body-token signatures.
External declarations/macros retain their distinct canonical identity. Every
candidate must invert to the exact input bytes and reparse to the same binding
graph and protected declaration shapes. Functions observing names through asm
or supported name-observer spellings, and macro-affected declarations, are
conservatively excluded. Errors reject the source rather than bypass a guard.

The implementation is original. The GPL-3.0 ice4 source at commit
`2bd7a54f9bb47a61a7cd97f3db9f52eadd4e2c19` was read for comparison only, outside
this repository. No third-party implementation or library is vendored here.

The generic API is:

```python
rewrite(source: bytes, *, clang_site, resource_dir, arguments=(), protected=())
# -> candidate_bytes, exact_declaration_and_offset_metadata
```

The fixed campaign entry points require a new absolute output directory outside
Git. `build.py` admits the historical ordinary F5051 source closure in
`inputs.json` and independently regenerates shipping source, final native, and
the original XZ whole twice. The historical ordinary source extraction is an
explicit `--source-root`; a changed maintained source fails its pins.
`portfolio.py` admits existing A/B/C/E shipping source/bootstrap/whole outputs
from the separately qualified source-codec campaign and the small ordinary
template/compiler recipe inputs in `portfolio-inputs.json`. It compiles each new
candidate once, requires the full old native SHA, and only then packages it once
with that family's original codec. `--family B` isolates the corrected B retry.
Neither driver runs an engine.

Both entry points accept `--clang-site` and `--resource-dir`. The qualified
external setup is libclang 18.1.1 plus the actual Ubuntu Clang 18.1.3 resource
headers. These dependencies and their hashes are recorded in the output; they
are unnecessary for the maintained fixed-offset replay stage.

Actual first costs, including original launchers and format overhead:

| Source class | Source before / after | Whole before / after | Full old native |
| --- | ---: | ---: | --- |
| F5051 | 10477 / 10011 | 5051 / 4891 | exact, twice |
| A4980 | 10184 / 9910 | 4980 / 4846 | exact |
| B5851 | 13071 / 12485 | 5851 / 5659 | exact |
| C5687 | 12224 / 11704 | 5687 / 5507 | exact |
| E5679 | 12641 / 12093 | 5679 / 5515 | exact |

F/A/C/E were executed with the first producer snapshot. B's first attempt
conservatively rejected main-file macro USRs containing moved physical offsets.
The ordinal-only retry exposed a declaration-only libclang storage attribute
being queried on a preprocessing node; it also rejected before native compile.
Both failures remain outside Git. The final producer binds macro ordinal, exact
body tokens, and use edges without querying undefined declaration attributes.
Ten focused fixtures pass, including nested/self-initializer binding, alias
reuse across functions, macro arguments, same-name header/main macros, exact
macro-body signatures, static/member/string preservation, and asm exclusion.

No new engine, game, benchmark, or broad matrix was run. Native equality has no
metadata exception. Every measured whole remains above 4096 bytes. The separate
fixed-codec F composition is a separately measured result, not an additive
estimate or part of these original-codec measurements. Reports, executed
producer snapshots, exact offsets, diagnostics, sources, and binaries remain
outside Git; the final external inventory identifies them.
