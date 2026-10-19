# Rust source rewrite portfolios

NVCompact 0.4 performs notation and local C rewrites in Rust. It does not start the former Python modules. Clang is an optional C language frontend; `rustpython-parser` is a Rust parsing library, not a Python interpreter.

These are source candidate generators. Their `bytes` field describes source bytes, not the final TCEC submission. Keep the original candidate, compile for the declared target, compare complete submitted files, and apply the appropriate application verifier. Source shortening can leave machine code unchanged or make a compressed file larger.

## Public interfaces

```rust
notation::generate_variants(source, &NotationOptions { ... })
cflow::generate_variants(source, &CFlowOptions { ... })
```

Both return `Vec<notation::Variant>`. A variant contains its stable recipe ID, source data, byte count, SHA-256, applied edits, inapplicability notes, and the observation contract. JSON serialization omits `data`; consumers save the bytes separately. Equal-byte recipe IDs remain present for provenance. `raw` is always first.

The default `opaque` token contract produces identity without starting Clang. An explicit `no-token-observation` or eligible `preprocessed` contract allows rewriting. Such a declaration must be true for the target: source-file inspection, stringification, locations, diagnostic spellings and other source observations are not generally invariant under rewriting.

## Literal and trivia portfolios

`NotationOptions` contains language, target model, compaction selection, token contract and a bounded variant count. Recipes cover shortest, hexadecimal, decimal, scientific, octal and binary policies, optionally combined with trivia compaction. A policy may deliberately produce longer source if that spelling improves compression elsewhere; the complete-file portfolio determines acceptance.

| Language/model | Preserved properties |
| --- | --- |
| C11 LP64, C23 LP64, C++17 LP64 integers | Exact integer value and the standard literal type selected from base and suffix. `int`, `unsigned int`, `long`, `unsigned long`, `long long` and `unsigned long long` remain distinct. |
| C/C++ floating literals | Exact rational value and suffix/type. IEEE conversion evidence is recorded; the actual target compilation remains an acceptance condition. Long double is outside this model and remains unchanged. |
| Rust 2021 integers/floats | Exact literal value, explicit suffix or inference class. Tuple indices, macro token trees, attributes, lifetimes and documentation comments are protected. |
| Python | Parsed constant type/value, complete location-erased AST and exact binary64/complex component bits. Booleans, complex literal spelling, f-strings and nonconstant expressions are not reserialized as ordinary constants. |

For example, changing C `100000` to `1e5` changes an integer literal into a double literal. It is not a generally valid notation rewrite. C `100000.` can use `1e5` under the floating model. Likewise `2147483648` and `0x80000000` select different types on LP64; a candidate needs the appropriate suffix.

C-family compaction checks the complete significant token sequence and checks splice boundaries before removing whitespace. Directives, quoted tokens and protected macro arguments retain their spellings. Unprocessed splices, trigraphs and unsupported backslash tokens preserve identity. Unsupported source encodings preserve identity with a reason.

Python compaction edits source gaps instead of printing a new AST. It preserves shebangs, encoding cookies, BOMs, indentation, line endings, explicit continuations and quoted-token content. It compares the complete token sequence after trivia removal and reparses the complete candidate. The canonical AST erases only location ranges; it retains expression contexts, names, typed constants, string kinds and floating-point bits. A non-UTF-8 encoding outside the implemented contract is explicitly left unchanged. Parsing compatibility with a target Python runtime is still a target validation concern.

The local Python whitespace check supplies inert nesting context when lexing two adjacent tokens. A closing delimiter followed by a keyword, such as `)in`, must not be rejected merely because an isolated lexer fragment has no opening delimiter. This fixes the lexer precondition rather than adding exceptions for an engine or source line; the complete-file token and AST checks still decide whether the candidate is accepted.

## Native compilation and replay

A unit in a native manifest can declare `notation` with an explicit `language` and the optional typed fields `target`, `token_contract`, `compact` and `max_variants`. Its `sources` must be unique, same-language files in the declared input snapshot. During a packing search, NVCompact compiles the original unit first, generates correlated source recipes, and compiles each changed recipe in an isolated copy of all declared inputs. It uses the declared commands and flags. The command, source hashes, object hashes and rejection reason are retained beside the unit.

Only complete object-byte equality with the original permits a source recipe to be selected before linking. The original object remains the linker input even when a shorter source recipe passes. A source candidate with a different object is rejected by this gate; an object that differs only in an observed file path is still different. This is deliberately stricter than removing sections or comparing disassembly. Unobserved or normalized paths can allow acceptance, but the tool does not silently introduce a path-remapping compiler flag. The report distinguishes saved source bytes from the final executable size.

The audit appears in the native report and selected recipe. The final fresh build reconstructs the original native object and checks native and final-file hashes; it does not repeat a source search that cannot change the linker input. `build` without packing skips notation and codec generation. A malformed declaration is rejected on the path that consumes it, and unsupported source transformations retain the original with an explicit reason. Source reads are bounded before allocation and after reading to catch file growth.

Native manifests may declare `category: "4k"` or `category: "4k-elf"`. The packing path applies the minimum of the category's 4096-byte limit, a declared `max_bytes`, and an explicit caller limit. In `4k-elf`, only native ELF deployment and the raw codec are eligible; an explicit script-wrapper codec request is an error. A plain build reports the linked file and applies only its explicit caller cap. The envelope workflow also has its own category gate.

Replay resolves the tools needed by the selected implementation and their declared dependencies, not every compiler that participated in the original portfolio. Every required selected build tool must retain its recorded fingerprint. Reports preserve the full campaign tool set, while the winner recipe contains the selected closure. This avoids making an unused Rust compiler a replay prerequisite for a C winner. Adding verification explicitly to a plain build may introduce verifier-only tools; it does not allow an unrecorded build tool.

## Typed C portfolios

`CFlowOptions` selects Clang, C11/C17/GNU11/GNU17, frontend/ABI arguments, the source include directory, pass count, candidate count, and frontend budgets. Clang runs under owned process, wall-time, output and per-process address-space limits. The transformation does not execute the source program.

| Rule | Candidate and principal condition |
| --- | --- |
| `if-return` | Paired returns become a conditional expression when source operand types match before contextual return conversion. |
| `return-tail` | An `if` return followed by a return uses the same type condition. |
| `if-assignment` | Paired stores to the same ordinary plain binding use one conditional RHS; pre-assignment operand types must match. |
| `if-effect` | Same-type or void branch expressions become a discarded conditional expression. |
| `guard` | A conditional discarded integer/pointer expression can use short-circuit `&&`. |
| `boolean` | Conditional 0/1 forms and double negation preserve the exact C `int` result. |
| `zero-test` | Equality or inequality with zero can use logical negation while preserving one read and `int` result. |
| `truth` | Redundant tests are removed only in controlling or short-circuit truth contexts. |
| `negation` | Comparison complements and De Morgan preserve evaluation order; relational inversion excludes floating-point NaNs. |
| `compound` | A plain binding assigned its own binary expression can use compound assignment under the conversion and RHS-effect conditions. |
| `increment` | `+= 1`/`-= 1` can use prefix increment/decrement only for an exact source `int` literal 1. |
| `leaf-braces` | A single nondeclaration leaf can lose braces without changing label, dangling-else or lifetime scope. |
| `forever` | A nonzero integer-literal `while` condition can become `for(;;)` if `for` is not a macro. |

The generator emits `raw`, `c-all` and one candidate per rule. It chooses nonoverlapping shorter edits deterministically inside each pass, then reparses the changed file. This local choice is one candidate, not a claim of a global compression minimum.

The function protection gate excludes unsupported expressions, volatile/atomic access, aggregate call-result lifetimes, compound literals, statement expressions, generic/type-observing operations, inline assembly, returns-twice/context-observing calls and unresolved indirect calls. It rejects macro expansion source locations and also scans raw source identifiers against the union of all encountered macro definitions, including definitions later undefined. This catches empty macros and pragma effects that disappear from the AST. A newly protected function after a pass causes that pass to remain unapplied.

Source byte splices currently require supported ASCII identifier boundaries. Universal character escapes, non-ASCII identifiers and implementation-specific identifier characters are explicitly left unchanged; quoted Unicode and comments remain supported. This is an implementation boundary, not a permanent repository prohibition on richer parsers.

## Counterexamples retained in verification

An LP64 function returning `unsigned long` can return `-1` in one branch and `1U` in another. Combining those source operands with `?:` first converts them to unsigned int and changes the first result from `18446744073709551615` to `4294967295`. Comparing only the contextual return type misses this change.

For a NaN, `!(x < 0)` is true while `x >= 0` is false. Relational complement rewriting must exclude such floating operands.

Deleting a macro that expands to `_Pragma("pack(1)")` can change the layout of a later declaration even if both files parse. Removing braces around an unsupported identifier spelling can concatenate `else` with an identifier. These require source-token and preprocessing protection in addition to AST parsing.

Module tests contain project-owned small semantic fixtures, not third-party engines. One fixture separately exercises all thirteen rule families, compiles every generated candidate and compares execution with an independently calculated integer/NaN oracle. The tests also cover signed/unsigned conversion, macro/pragma disappearance, returns-twice and indirect calls, volatile access, unsupported identifier spellings, exact literal types and Python AST/trivia preservation. Actual external-engine results belong in the campaign evidence and must state whether execution was performed.

## Observed migration checks

On 2026-10-19, the Rust debug CLI generated all thirteen notation recipes for each of the three external source payloads below. Every one of the 39 generated source files matched the preserved Python reference byte-for-byte. The external inputs and generated sources remained outside this repository. [Parity evidence](../evidence/0.4/notation-parity.json) records input hashes, both output hashes, the Python reference hash and the Rust executable hash.

| External source payload | Language | Original source bytes | `shortest-compact` source bytes |
| --- | --- | ---: | ---: |
| Sunfish | Python | 5837 | 5825 |
| Moonfish | C | 10608 | 10591 |
| ice4 | C++ | 8750 | 8741 |

These numbers describe source payloads. Complete-file compression and actual engine execution have separate evidence. This source comparison used the archived Python implementation only as a development oracle; the Rust CLI did not invoke it.

The selected-tool replay correction was also exercised by the project-owned mixed example: all nine C/Rust implementation combinations, both link orders, and the `size-lto`/`compact` profiles produced 18 completed link candidates and 396 verified deployment/packing artifacts. The 504-byte selected ELF rebuilt byte-identically and passed the full independent scalar oracle with 199360 valid records and 22 test cases. Its recipe needed `cc`, `ld` and `python`; the original campaign additionally used `rustc`. [Mixed integration evidence](../evidence/0.4/mixed-selected-tool-replay.json) records the selection, hashes, tool sets and finite verification scope. This establishes the replay fix for a mixed portfolio; it makes no claim about engine compression or chess behavior.

## Reference basis

- [C11 draft N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf): integer constants, conditional operators, compound assignment, logical operators and preprocessing.
- [Clang AST introduction](https://clang.llvm.org/docs/IntroductionToTheClangAST.html): implicit conversions and source-level expression structure.
- [RustPython parser 0.4](https://docs.rs/rustpython-parser/0.4.0/rustpython_parser/) and [AST fold interface](https://docs.rs/rustpython-ast/0.4.0/rustpython_ast/fold/index.html): the exact parser dependency used by the Rust implementation.

These frontend gates establish bounded transformation conditions. They do not establish arbitrary whole-program equivalence, chess strength, TCEC resource compliance or a compression-ratio optimum.
