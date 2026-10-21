# Whole-file C source portfolios

NVCompact can search alternative C spellings using the size of the complete
compressed submission. This is useful when the submitted payload contains C
source, either directly or inside an explicitly declared Python bytes constant.
The implementation is native Rust, with Clang as the typed C frontend and the
manifest's actual compiler as a separate acceptance gate.

The measured comparison results and their execution scope are recorded in
[PR #13 results](PR13-RESULTS.ko.md). Engine-specific changes are separated in the
[PR #12 handoff](PR12-HANDOFF.ko.md). This guide describes the implemented interface
and its contracts; it does not establish a compression optimum or tournament
qualification.

## 1. Three different sizes

| Measurement | What it establishes |
| --- | --- |
| Source bytes | The size of one spelling. Equal-length and longer spellings remain useful candidates. |
| Complete compiled native bytes | A strict acceptance check under one declared compiler recipe. It includes all output bytes, not just executable instructions. |
| Complete submitted file bytes | The compression objective: inspected loader/header plus the encoded whole payload and its framing. |

For example, different one-letter local names can have the same source length
and produce identical native code while producing different compressed source
sizes. A shorter conditional expression can produce identical machine code and
provide no reduction in a native ELF submission. Native equality does not mean
the linker ignores C semantics: the frontend and optimizer can lower different
source expressions to identical compiled output.

The source search retains alternatives by their source and rendered payload
identities. It does not discard a spelling because another spelling generated
the same ELF. It also does not choose a shorter source before measuring its
complete submission cost.

## 2. Generate candidates without choosing a submission

These commands read source and invoke the declared frontend. They do not execute
the generated source program. Portfolio directories must be new; keep generated
files outside the repository.

### `spell-c`: unranked names and literals

```sh
npm exec -- nvcompact spell-c \
  tools/nvcompact/examples/c-rewrites/program.c \
  --clang clang --standard c11 --target c11-lp64 \
  --token-contract no-token-observation \
  --max-candidates 256 --max-name-groups 36 --names-per-group 4 \
  --portfolio /absolute/external/c-spelling-portfolio
```

The command prints JSON metadata and, when `--portfolio` is provided, writes
`raw.c`, the changed candidate files, and `variants.json`. JSON metadata contains
source sizes, hashes, edits, assumptions and inapplicability notes; it omits the
source byte buffers. There is no `shortest` selection or `--output` shortcut for
this command. These are candidates that still require structural validation and
the actual submitted compiler check before adoption.

The current families are:

- **Automatic locals and parameters.** A group changes a declaration and its
  resolved references together. Replacement identifiers are fresh within the
  function, resolved references and encountered macro names. Existing one-letter
  names are eligible, so equal-length frequency redistribution is explored.
  Groups with more use sites are considered first; frequently occurring eligible
  letters elsewhere in the translation unit are considered before other letters.
- **Integer constants.** Decimal, hexadecimal, octal and supported suffix
  alternatives preserve the Clang-resolved value, signedness and rank in the
  declared C11 LP64 model. Same-value constants of different types are distinct.
- **Narrow character constants.** Supported single-character or escaped constants
  with resolved `int` values from 0 through 127 can use integer spellings. This
  does not generalize to wide, multicharacter or arbitrary execution-character-set
  constants.

`max_candidates` includes the raw candidate. The CLI defaults are shown above.
`--compiler-arg` is repeatable; use, for example, `--compiler-arg=-mavx2` only when
that matches the actual target. Include, macro and target arguments are validated
frontend inputs, not a way to pass arbitrary compiler plugins or output commands.

### `rewrite-c`: guarded expression and control-flow alternatives

```sh
npm exec -- nvcompact rewrite-c \
  tools/nvcompact/examples/c-rewrites/program.c \
  --clang clang --standard c11 \
  --token-contract no-token-observation \
  --include-nonshrinking --individual-edits 32 \
  --max-variants 64 --max-passes 2 \
  --portfolio /absolute/external/c-condition-portfolio
```

The default remains `include_nonshrinking=false`, `individual_edits=0`,
`max_variants=16`, and `max_passes=2`. The optional flags expose equal-length or
longer edits and individually applied alternatives for a caller that measures
compressed cost. They do not relax the semantic guards. `max_variants` limits the
whole portfolio, so leave room beyond the raw, all-rules and per-rule entries
when requesting individual edits.
Standalone bounds are 1–128 variants, 1–8 passes and 0–128 individual edits.

The fourteen rule families are `if-return`, `return-tail`, `if-assignment`,
`if-effect`, `guard`, `boolean`, `zero-test`, `truth`, `negation`, `compound`,
`increment`, `leaf-braces`, `forever`, and `boolean-domain`. The generator reparses
changed passes and retains function protection checks. `--output FILE --variant
ID` writes a specific generated recipe; choosing that ID does not establish that
it is the smallest submission. Without `--variant`, `--output` uses `c-all` when
present and otherwise `raw`.

The Boolean-domain rule illustrates the proof requirement. `x != 1` may become
`!x` only when the evaluated value is established to be either 0 or 1, such as
`_Bool`, an existing Boolean operator, or a supported unsigned-int one-bit field.
An ordinary `int` can be 2, and a signed one-bit field can be -1; neither is
accepted under that argument. The rule preserves one evaluation and the original
comparison's `int` result. Conditional returns also check operand types before
contextual return conversions: matching the function's return type alone is
insufficient. Relational complementation does not assume away floating NaNs.

The [rewrite guide](RUST-REWRITES.md) explains the original rule guards and their
counterexamples. The additional candidate controls above apply to the current
implementation.

## 3. Opt in through an inspected envelope manifest

The source search is an optional **top-level `source_search` object**, alongside
`language`, `compile_argv` and `envelope`. It is not nested inside `envelope`.
Existing manifests keep their original behavior when this object is absent.
`--no-notation` also disables source search.

Begin with an inspected external submission manifest that already pins the
original artifact, its header, decoder and `envelope.payload_codec`. Preserve
those measured fields. Add the source configuration below to that manifest;
these fragments do not replace the artifact/envelope declarations.

### Direct C payload

```json
{
  "language": "c",
  "compile_argv": [
    "cc", "-x", "c", "-", "-std=c11", "-Os", "-s",
    "-fno-ident", "-Wl,--build-id=none", "-o", "{output}"
  ],
  "source_search": {
    "candidates": {
      "target": "c11-lp64",
      "frontend": {
        "clang": "clang",
        "standard": "c11",
        "token_contract": "no-token-observation",
        "compiler_args": []
      },
      "max_candidates": 256,
      "max_name_groups": 36,
      "names_per_group": 4,
      "rename_locals": true,
      "integer_literals": true,
      "character_literals": true
    },
    "conditions": true,
    "max_rounds": 2,
    "max_evaluations": 2048,
    "max_seconds": 300
  }
}
```

The compiler invocation is an example for a self-contained C11 input. Replace
it with the actual submitted compilation recipe, including its target,
preprocessing, threading, language and optimization choices. Do not add stripping,
path-remapping or other options solely to make unequal outputs pass this check.

`compile_argv` receives source on standard input and must write its native output
to the required `{output}` placeholder. NVCompact invokes argv directly, without
implicit shell parsing. A compiler's child working directory is owned by the
run. Use explicit tool and include paths when the submission depends on external
files. The frontend's optional `source_path` establishes its source include
directory; it must identify an existing source path. The direct CLI sets this
from its input file. Manifest users must align the frontend's dialect, ABI,
macros and include context with the actual compiler recipe.

`no-token-observation` declares that changing these source spellings and source
locations is allowed. The alternative `preprocessed` contract is available for
inputs that actually satisfy it; it is not an instruction to silently preprocess
an arbitrary input. Standalone generators default to `opaque` and preserve raw
source. The combined search requires an explicit enabling token contract.

### C inside a Python bytes constant

Use `language: "python"`, keep the C `compile_argv`, and configure the same C
candidate frontend. Add `source_search.embedding` and set
`source_search.embedding_contract` to `"compile-input-only"`.

The embedding object has exactly these fields:

| Field | Meaning |
| --- | --- |
| `kind` | Must be `"python-bytes"`. |
| `start` | Zero-based byte offset of the entire selected literal in the decoded Python payload. Includes its `b`/`br` prefix and opening delimiter. |
| `end` | Exclusive byte offset after the selected literal's closing delimiter. |
| `sha256` | SHA-256 of the original payload bytes in `start..end`, including prefix, delimiters and escape spelling. This is not the hash of the decoded C value. |

Inspect the decoded original payload before supplying offsets. This optional
helper prints the declaration for an already inspected range; it reads a file
and hashes bytes without importing or executing the Python payload:

```sh
node --input-type=module - /absolute/external/original-payload 147 10324 <<'JS'
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const [file, first, last] = process.argv.slice(2);
const data = readFileSync(file);
const start = Number(first), end = Number(last);
if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) ||
    start < 0 || start >= end || end > data.length) {
  throw new Error('invalid inspected byte range');
}
console.log(JSON.stringify({
  kind: 'python-bytes', start, end,
  sha256: createHash('sha256').update(data.subarray(start, end)).digest('hex')
}, null, 2));
JS
```

Replace the example offsets with the measured offsets of your own input, then
put the printed object at `source_search.embedding`. The adapter independently
checks the exact hash, the whole Python AST range, and the literal's decoded
value. It does not select a literal by variable name or guess which bytes are C.
If adjacent literal tokens form one AST constant, the declared range must cover
that entire constant. Expressions that concatenate variables, decompress data or
compute a string are outside this adapter.

`compile-input-only` is an explicit observation contract for **both the selected
bytes and the surrounding Python wrapper**. The wrapper may pass the bytes to
the declared compiler. It must not inspect their spelling, length or hash, log
them, dispatch on them, or derive another observable result from them. Wrapper
source/token/location observations must also be absent: self-inspection, source
reads through `__file__`, traceback/line-number-dependent output or control flow,
and observers of the wrapper's literal spelling are incompatible with this
contract. Re-encoding a multiline literal can change later line locations even
when the location-erased Python AST is otherwise identical.

Declare the outer Python notation contract separately if enabling its own
notation transformations; it has the same source-observation obligations.
AST equality alone does not establish either observation contract. These are
assumptions to verify against the actual bootstrap and its deployment context.

The adapter preserves surrounding payload bytes exactly and verifies the whole
Python AST while allowing only the selected bytes constant's value to change.
It retains typed constants and exact floating/complex component bits outside
that value. The original literal spelling, applicable raw triple-quoted styles,
and escaped styles are compared. Inapplicable raw delimiters are skipped; an
escaped rendering that fails exact readback is an error. Python parsing uses a
Rust library, with no Python execution backend.

### Run and replay

```sh
npm exec -- nvcompact envelope /absolute/external/source-manifest.json \
  --artifact /absolute/external/original-submission \
  --output /absolute/external/source-search-run --jobs 2

npm exec -- nvcompact replay /absolute/external/source-search-run/summary.json \
  --output /absolute/external/source-search-replay --selection smallest
```

`--thorough` expands the final codec portfolio. `--jobs` controls its codec
workers; it does not parallelize source generation or candidate compilation.
The source-search bounds are manifest settings. The separate `--uci` option
requests actual final-artifact protocol probes and is not part of the commands
above. Resource-heavy engine execution retains the separate plan/start workflow.

## 4. Selection and preservation of the previous portfolio

Source exploration uses a fixed objective: recompress the **whole rendered
payload** with the manifest's inspected `envelope.payload_codec`, select the
supported header spelling for that decoder, and count the complete resulting
file. Header and framing bytes are included. Python literal escaping and all
unchanged bootstrap bytes are included. A candidate's raw source length is never
used as a cheaper substitute for this measurement.

Each round generates independent spelling groups, measures their applicable
payload renderings, and orders improving singles by complete-file cost with a
stable identifier tie-break. Compatible groups are combined greedily from that
round's input. Each combination is remeasured; individual savings are not summed.
An improving combination must pass the semantic gates before it becomes the
provisional incumbent. The selected combination becomes one replayable step.
Optional guarded C condition candidates are evaluated separately on the current
source; arbitrary condition edits are not composed as if independent.

The resulting source is one additional input to the final codec search. That
search preserves:

- The original complete submitted file and original compressed stream.
- Existing notation/source candidates and the existing codec seeds.
- The refinements that the legacy seeds would have selected, even when a new
  seed would otherwise displace a previously explored refinement family.
- The inspected submitted codec for changed sources, together with applicable
  additional seeds and refinements.

Consequently a source-search win under its fixed codec is not reported as the
final result until the complete final portfolio is compared. Another old source
or codec can still win. An unchanged selection is reported as preservation, not
new compression. The bounded greedy source search does not exhaust combinations
that become beneficial only together, or sources that improve only under some
other codec; there is no global-optimality claim.

For native ELF submissions, preserving complete native bytes necessarily
preserves that native file's size. This source-enveloping path applies to an
inspected source-containing general `4k` submission. The separate `4k-elf` path
continues to require native ELF candidates and excludes script envelopes.

## 5. Acceptance and exact replay

The original C source must compile successfully twice to identical complete
native bytes and identical compiler stdout/stderr. Every accepted changed source
then passes two kinds of checks:

1. **Source derivation.** Spelling edits are reconstructed from audited source
   spans and verified with the typed Clang AST, declaration/reference bindings
   and token boundaries. Typed constants retain value and type. Condition
   candidates use the guarded local rules and reparsing described above.
2. **Actual compilation and embedding.** The declared compiler must produce the
   same complete native SHA-256 and byte count, compiler executable identity,
   and stdout/stderr SHA-256 as the original. The payload adapter must reproduce
   the measured spelling and exact bytes. A changed diagnostic is a rejection,
   even if native code is equal.

A stripped or normalized comparison cannot substitute for complete native
identity. Different debug metadata, build identifiers, paths, warnings or output
bytes can reject a candidate. The implementation does not infer that a rejected
candidate is equivalent because a sample output happened to match.

Final acceptance freshly checks changed source compilation, exact payload
rendering and reproducibility of the selected complete-file cost. The envelope
then regenerates the selected codec result and checks deployed decoder readback.
No chess engine or Python bootstrap is executed by source search or ordinary
replay. Compiler and decoder subprocesses do run under their declared contracts.

The accepted recipe records input hashes, options, compiler argv, compiler and
frontend executable fingerprints, source-edit derivations, literal rendering
style and native receipts. `replay` reconstructs only the recorded accepted
spelling steps; recorded condition steps regenerate their bounded rule recipe
and select its exact audited ID/hash. It performs the source/native/adapter checks
again, then applies the selected final codec and requires exact final size and
hash. It does not repeat whole-file source exploration or codec optimization.

The envelope replay additionally pins the generating NVCompact executable and
codec runtime. A different executable is not silently substituted. Retain the
original artifact, summary, required source/header dependencies and declared
tools with the evidence needed for a future replay. Executable hashes are
explicit tool identities; they are not a claim that every shared library and
external include file has been independently snapshotted.

## 6. Bounds, reports and unsupported inputs

| Setting | Default | Supported range or scope |
| --- | ---: | --- |
| `source_search.max_rounds` | 2 | 1–8 rounds. |
| `source_search.max_evaluations` | 2048 | 1–16384 actual complete-file measurement calls. |
| `source_search.max_seconds` | 300 | Positive finite value up to 86400; scheduling deadline. |
| `candidates.max_candidates` | 256 | 1–512, including raw. |
| `candidates.max_name_groups` | 36 | 0–128. |
| `candidates.names_per_group` | 4 | 1–16. |
| `candidates.frontend.frontend_seconds` | 30 | Per frontend operation, positive and at most 300 seconds. |
| `candidates.frontend.frontend_memory_bytes` | 1073741824 | Per-process address-space limit, at least 64 MiB. |
| `candidates.frontend.ast_bytes` | 33554432 | 64 KiB–128 MiB captured frontend output. |
| `source_search.compile_limits` | Process defaults | `seconds`, `memory_bytes`, `output_bytes`, `cpu_seconds`, `file_bytes`. |

Compiler process defaults are 60 seconds wall time, 1 GiB address space, 16 MiB
captured output, 120 CPU seconds and 64 MiB output-file extent. If
`source_search.compile_limits` is absent, the envelope uses top-level
`compile_limits` when present. Conditions are enabled by default; their source
search portfolio uses `include_nonshrinking=true`, `individual_edits=32`, and
`max_variants=64`, with the configured frontend and pass settings.

The evaluation budget counts the original measurement, newly measured rendered
payloads and a fresh final measurement when output changes. Cached identical
payload measurements do not count again. A slot is reserved for final readback;
with a budget of one, the measured original remains the result. Previously
measured singles can still be verified after the cost-exploration budget is
exhausted; an unmeasured composition cannot be accepted by estimating its cost.

The time limit is checked between bounded operations. It is not a hard deadline
that interrupts an arbitrary codec callback; final acceptance can finish after
exploration stops. Compiler/frontend subprocesses have their own finite limits.
Limits apply per process rather than as a hard cgroup reservation for an
arbitrary process tree. Cancellation aborts the operation and reaps owned child
processes. Source generation and candidate compile work are currently serial.

Source/payload inputs are bounded to 8 MiB. The spelling generator retains at
most 64 MiB of candidate source buffers. Detailed search records are bounded to
32768 entries and 32 MiB; report-memory exhaustion stops further acceptance when
proof cannot be retained. These are separate bounds, not an aggregate process
memory guarantee.

The envelope summary embeds the accepted recipe and a compact source-search
report. Its `detail.path`, byte count and SHA-256 identify the detailed report
under the owned output directory. Records include generator notes/assumptions,
measured styles, native receipts, rejected candidates, accepted derivations and
budget exhaustion. Invalid configuration, generation failure, measurement error
or cancellation is not reported as successful baseline fallback. An individual
candidate that fails its gate can be rejected while the earlier validated
incumbent remains. Exhausting a budget does not prove that no better spelling
exists.

The current implementation intentionally has these boundaries:

- **Language/ABI:** the new spelling search supports C11/C17/GNU11/GNU17 and the
  checked C11 LP64 type model. It does not adapt C++ or Rust payloads to C. The
  existing notation and native build paths remain separate interfaces.
- **Source spelling:** the new spelling generator preserves identity for
  non-ASCII input, NUL, dollar identifiers, universal escapes, line splices or
  trigraph-like input. The condition generator has its own token-level boundary:
  quoted Unicode/comments can remain, but unsupported identifier/token splice
  boundaries are not rewritten.
- **Bindings and macros:** static/extern/TLS variables, public symbols and member
  names are not renamed. Non-main-file or macro-expanded edit ranges are not
  treated as ordinary token spans. Inline assembly and block constructs exclude
  local renaming in the affected function. Source-dependent macros are not
  neutralized by deleting them.
- **Condition semantics:** volatile/atomic access, unsupported lifetime/context
  constructs, attributes, macro/pragma effects, unresolved indirect calls and
  returns-twice/source-observing calls retain protection. The tool does not infer
  chess-specific ranges, board invariants, TT concurrency or memory ordering.
- **Python embedding:** only a whole declared bytes-constant range in supported
  UTF-8 Python source is accepted. Partial spans, non-bytes values, computed
  expressions and incompatible encoding declarations fail. Observation contracts
  cover the selected bytes and wrapper source/token/locations; masking one AST
  constant does not prove those contracts.
- **Deployment and behavior:** exact compiler output under one recipe is not a
  universal language-equivalence proof, UCI validation, memory-usage measurement,
  strength test or TCEC server acceptance. Those remain separately reported
  checks on the actual final artifact.

External engine sources, generated sources, binaries and raw campaign outputs
stay outside Git and npm packaging. Publish reviewed provenance, hashes,
commands and results; do not vendor comparison inputs to make the examples run.

## Implementation references

- [C spelling candidates and binding verification](../src/csource.rs)
- [Typed condition candidates](../src/cflow.rs)
- [Python bytes adapter](../src/source_payload.rs)
- [Whole-file search and exact source replay](../src/source_search.rs)
- [Envelope selection, preserved refinements and final replay](../src/envelope.rs)
- [Owned integration fixtures](../tests/source_search.rs)
