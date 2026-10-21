# Whole-file C source portfolios

NVCompact can search alternative C spellings using the size of the complete
compressed submission. This is useful when the submitted payload contains C
source, either directly or inside an explicitly declared Python bytes constant.
The implementation is native Rust, with Clang as the typed C frontend and the
manifest's actual compiler as a separate acceptance gate.

The measured comparison results and their execution scope are recorded in
[PR #13 results](PR13-RESULTS.ko.md). Engine-specific changes are tracked in
[PR #12](https://github.com/daejunnom/Rove4k/pull/12). This guide describes the implemented interface
and its contracts; it does not establish a compression optimum or tournament
qualification.
Those PR #13 results are historical measurements. The current
[search architecture](SEARCH-ARCHITECTURE.ko.md) explains the ownership, shared
evaluation and finite search space described below; it is not a new measurement
of those engines. The [external commit review](EXTERNAL-SIZE-COMMITS.ko.md) records
upstream techniques and failures separately. The [PR #16 results](PR16-RESULTS.ko.md)
record the new same-input regression runs, a separate bootstrap-byte-preserving
matrix and cost-reuse experiment. Their observation-contract qualifications
must be read alongside byte and native identity results.

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
comparison's `int` result. Clang's canonical `bool` spelling after `<stdbool.h>`
is recognized after type desugaring, including aliases and qualified Boolean
objects whose actual lvalue conversion produces `_Bool`. A user declaration such
as `typedef int bool` does not establish a Boolean range. The literal may occur
on either side, and later passes can simplify expressions that an earlier pass
made Boolean; each pass reparses the changed source. The rule does not infer a
Boolean range from a variable name, sampled values, or a later assignment to a
Boolean destination. Conditional returns also check operand types before
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
When enabled, the source search defaults to a submitted-codec strategy followed
by a codec-portfolio strategy. The optional top-level Boolean
`source_search_portfolio` defaults to `true`; setting it to `false` excludes the
second strategy while keeping the submitted-codec strategy. It is not a field
inside `source_search` and is not a CLI flag.

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
    "max_combinations": 16384,
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
Native identity and a smaller complete file do not establish those assumptions.
A particular winner may retain all observed line/position metadata while other
generated literal styles can change it; checking that winner alone does not
admit the entire automatic search domain under `compile-input-only`.

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

`--thorough` expands the codec policy used by the portfolio source strategy and
the final comparison. `--jobs` controls the shared evaluator's codec workers;
it does not parallelize source generation or candidate compilation.
The source-search bounds are manifest settings. The separate `--uci` option
requests actual final-artifact protocol probes and is not part of the commands
above. Resource-heavy engine execution retains the separate plan/start workflow.

## 4. Selection and preservation of the previous portfolio

Both source strategies compare the **whole rendered payload** plus the complete
inspected header for the selected decoder. Header and framing bytes, Python
literal escaping and all unchanged bootstrap bytes are included. A candidate's
raw source length is never used as a substitute for this measurement.

The strategies start from the same original payload in this order:

| Strategy | Cost objective | Result |
| --- | --- | --- |
| `source-search` | The manifest's inspected `envelope.payload_codec` and its complete supported header spelling. | Uses `legacy_priority`; preserves the earlier ordering and a distinct priority seed when needed. |
| `source-search-portfolio` | The minimum complete-file cost from the current codec policy. | Uses `interleaved_online`; also considers sources whose advantage depends on another codec, enabled by default. |

The submitted-codec strategy first runs its earlier improving-incumbent rounds:
measure applicable spelling renderings, order improving singles by whole-file
cost with a stable identifier tie-break, and admit compatible improvements and
guarded condition recipes. Its deferred pass then visits nontrivial spelling
subsets on the visited immutable bases. Losing or tied singles remain eligible.

The full-codec strategy alternates singleton and subset work and immediately
checks a measured improvement instead of scoring all singles before admission.
Registered condition alternatives use a singleton-only lane. Initial
round/family phases share the remaining time and unreserved evaluation budget;
these quanta limit new candidate starts. Paused queues resume afterward without
restarting their enumeration. Reaching the subset-attempt cap in this policy
leaves subsets incomplete but does not block remaining singletons or conditions.
The budget remains finite, and one expensive operation can still exhaust it.

Legacy deferred subsets and online work use a common generated-space
composition/measurement/admission path. Incompatible edit or binding combinations are recorded; compatible
combinations are measured as whole payloads. Individual savings are not summed.
Only a smaller, admitted and retained result can replace the incumbent. A
winning sibling restores its own immutable basis's accepted-step prefix rather
than appending a fictitious chain of sibling edits. Generator, combination,
measurement/time and evidence limits bound this work. Conditions retain their
registered recipes and bounded individual edits; this does not enumerate all
flow-edit combinations or all rewrite sequences. See the
[architecture and coverage definitions](SEARCH-ARCHITECTURE.ko.md) for the exact
finite domain, quantum allocation and completion fields.

The shared `WholeFileObjective` reuses successful codec work only for the same
payload identity and complete recipe inside its fixed inspected-envelope
context. The two strategies keep separate cost contexts and attempt archives.
Both winners enter the final codec comparison; identical payloads can share a
canonical final variant without losing their strategy-specific receipts.
The submitted-codec strategy also retains its pre-deferred priority winner when
it differs from both the original payload and the final source winner. It
reserves an additional fresh readback before deferred work when needed; if the
reservation and another new measurement cannot fit, deferred work does not
start. The common `SeedFinalizer` checks each retained seed under the same
contract. A priority snapshot is not a free or automatically accepted result.

The final comparison preserves:

- The original complete submitted file and original compressed stream.
- Existing notation/source candidates and the existing codec seeds.
- Both enabled source-strategy winners.
- A distinct validated `legacy-priority-seed` from the submitted-codec strategy.
- The refinements that the legacy seeds would have selected, even when a new
  seed would otherwise displace a previously explored refinement family.
- The inspected submitted codec for changed sources, together with applicable
  additional seeds and refinements.

Consequently a strategy's source winner is not reported as the final result
until the complete final portfolio is compared. Another source or codec can
still win. The default codec policy adds a submitted recipe to the legacy initial
domain and retains the union of earlier and augmented adaptive refinements. It
does not exhaust every codec option combination. The Rust API's
`CodecPortfolio::fixed(recipes)` instead defines an explicit finite list with no
adaptive refinement by default. This fixed-list API does not change the
envelope command's default policy.

An unchanged selection is reported as preservation, not new compression.
Keeping priority order and earlier candidates is not a guarantee of finding the
same minimum under every wall-clock budget or execution environment. No global
compression optimum is claimed.

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

A `SourceContext` separately retains the original source's preprocessing
observation across the search, independently of changing round bases and cached
AST lifetimes. It uses its own frontend session and needs neither an AST nor an
LP64 probe; opaque header bytes remain valid observation bytes. This does not
relax the spelling analyzer's type-model or encoding contract. Baseline native
compilations and initial cost, admission's actual compilation, final changed
native output and fresh cost are observed before and after the operation. An
operation wrapped by this guard is rechecked even when it fails; if context also
changed, the original operation error remains in the explanation and the typed
context failure remains fatal. A stale precondition prevents that operation
from starting.
Native observations preserve a completed compilation receipt before the
post-operation context check. Receipt persistence is inside that observed
operation, so a write failure cannot hide a simultaneous typed context failure.

The guard is not a preprocessing pass around every candidate cost measurement.
A final recheck also covers a search that inspected only non-improving choices
and retained the original. Candidate cost errors themselves still fail the run;
the interface does not promise that every such failure is reclassified as a
context change.

Final acceptance freshly checks changed source compilation, exact payload
rendering and reproducibility of the selected complete-file cost. The source
objective's fresh operation bypasses retained codec/header measurements. For the
portfolio strategy, this repeats the policy's full evaluation and adaptive seed
selection, not only the previously winning codec. An unchanged original payload
is identified as an unchanged-input baseline measurement. The envelope then
independently regenerates the final selected recipe and checks deployed decoder
readback.
No chess engine or Python bootstrap is executed by source search or ordinary
replay. Compiler and decoder subprocesses do run under their declared contracts.

The accepted recipe records input hashes, options, compiler argv, compiler and
frontend executable fingerprints, source-edit derivations, literal rendering
style and native receipts. `replay` reconstructs only the recorded accepted
spelling steps; recorded condition steps regenerate their bounded rule recipe
and select its exact audited ID/hash. It performs the source/native/adapter checks
again, then applies the selected final codec and requires exact final size and
hash. It does not repeat whole-file source exploration or codec optimization.
When accepted source steps exist, replay creates a new original-source context
guard and observes its baseline, step reconstruction/compilation and final
native boundaries. With no accepted source steps, replay uses the native and
embedding identity checks without claiming to have run that guard. The guard
checks consistency within the current replay; it is not a persisted snapshot
of every include dependency from the earlier search.

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
| `source_search.max_evaluations` | 2048 | 1–16384 complete-payload objective calls per strategy; one call may evaluate many codecs. |
| `source_search.max_combinations` | 16384 | 1–1048576 systematic subset attempts per strategy, including incompatible subsets. |
| `source_search.max_seconds` | 300 | Positive finite value up to 86400; per-strategy scheduling deadline. |
| `source_search.max_retained_source_bytes` | 67108864 | 0–536870912 additional deduplicated candidate-source snapshot bytes. |
| Serialized/API `source_search.scheduling` | `legacy_priority` | `legacy_priority` or `interleaved_online`; envelope assigns the effective policy by strategy, overriding this input field. |
| Top-level `source_search_portfolio` | `true` | Boolean; enables the second source strategy when `source_search` is active. |
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
payloads and fresh final measurements for changed retained seeds. Cached
identical payload measurements do not count again. One slot is initially
reserved for final readback; a second may be reserved before legacy deferred
work to preserve its priority seed. Reservations and actual fresh calls are
reported separately. With a budget of one, the measured original remains the
result. Previously
measured singles can still be verified after the cost-exploration budget is
exhausted; an unmeasured composition cannot be accepted by estimating its cost.

Each enabled strategy owns these limits independently. With both default
strategies, `source_search_budget` reports aggregate ceilings of 4096 payload
evaluations, 32768 combination attempts and 600 scheduling seconds. The shared
codec cache can reduce actual compression work without merging the strategies'
cost contexts. A strategy's priority seed shares its budget; it is not an extra
strategy. `retained_source_seeds` records seed count separately. Fresh source
seed readbacks count within those evaluation limits. Final envelope codec
comparison is separate work; in-flight operations and final acceptance can
extend beyond the scheduling deadlines. Native/codec scratch memory is not
covered by the retained-cache budgets.

The time limit is checked between bounded operations. It is not a hard deadline
that interrupts an arbitrary codec callback. Online phase quanta are checked
before starting candidates; their payload styles are still measured only while
the global exploration budget permits. A candidate started before the deadline
may finish bounded admission of an already measured improvement afterward.
This permission does not start another candidate or bypass cancellation,
retention failure or frontend-capacity stops. Final acceptance can also finish
after exploration stops. Compiler/frontend subprocesses have their own finite limits.
Limits apply per process rather than as a hard cgroup reservation for an
arbitrary process tree. Cancellation aborts the operation and reaps owned child
processes. Source generation and candidate compile work are currently serial.

Source/payload inputs are bounded to 8 MiB. The spelling generator retains at
most 64 MiB of candidate source buffers, and deferred subset plans separately
retain at most 64 MiB of source buffers. Detailed search records are bounded to
32768 entries and 32 MiB per strategy; report-memory exhaustion stops further
acceptance when proof cannot be retained. The shared evaluator has separate
bounded codec/header caches and at most `jobs` active codec workers. These are
separate bounds, not an aggregate process memory guarantee.

The envelope summary's `source_search_portfolio` array embeds each retained
strategy/seed's recipe, `seed_role`, scheduling policy and compact report;
`source_search` keeps the first entry as a compatibility view. A strategy can
have both `final-winner` and `legacy-priority-seed` entries sharing one detailed
report. Read work/evaluation totals once per strategy/report, not once per seed.
Each `detail.path`, byte count and SHA-256 identify its
detailed report under the owned output directory. Records include generator notes/assumptions,
measured styles, native receipts, rejected candidates, accepted derivations and
budget exhaustion. A frontend AST/preprocessing output cap has a specific bounded
stop path: NVCompact first performs a syntax-only check with the same language,
target and preprocessing arguments, finite limits, and executable identity.
Initial context capture or candidate analysis can use the bounded
`frontend-output-budget` stop only when that check succeeds. If the initial
observation cannot be captured, no context guard is established; baseline checks
and the unchanged-input path remain. The record explicitly marks frontend proof
as incomplete and states that truncated output was not accepted. A later
inability to revalidate an established original context, including output
exhaustion, is instead a fatal context failure. Version/ABI probe failures do not
take the optional capacity path. A syntax-check failure remains an error.

Coverage identifies each generated family's immutable basis, policy, choices,
declared subset count and attempted/incompatible/duplicate work. Online entries
also record `initial_quantum`, the first phase's `initial_progress`, and
`resumed_after_initial_phases`; the top-level report records `scheduling` and
`coverage.quantum`. `singles_attempted` includes singleton attempts and legacy
priority score starts, not completed payload styles or actual codec calls.
`unvisited_singles` and `unvisited_nontrivial_subsets` count remaining attempts.
`declared_basis_spaces_complete` aggregates the generated-space cost completion
flags, including online condition alternatives; those alternatives do not claim
to cover every flow sequence. The status distinguishes `completed`, `budget-exhausted`
and `space-incomplete`; its scope excludes undiscovered generator choices and
the separate flow/codec heuristics. Cached original AST proofs also require
preprocessing readback. A changed or unreadable original frontend context is a
fatal `FrontendContextChanged`, not a candidate-only semantic rejection or an
ordinary output-capacity stop.
The detailed report's `source_context` records the run-long observation and its
work separately from `frontend_work`. The latter covers the tracked
priority/interleaved-online/systematic and separate condition-generation
`PreparedSource` instances. Flow reuse of the same prepared basis accumulates
in that basis's round statistic instead of duplicating it. Temporary admission,
replay and other frontend calls remain outside that statistic. It is not the total
Clang workload and cannot by itself establish overall call reduction or speedup.
The initial `source-context` journal event retains the original preprocessing
hash and tool observation even when a later operation fails. Final accumulated
work statistics belong to the successful report; failure records do not claim
to contain those final totals.
`observation_contract` separately records the caller-established C/Python
source/token/location/traceback preconditions. Masked AST or native identity
does not prove those declarations valid for the actual wrapper.

The final report distinguishes unchanged C byte identity from accepted typed
derivations through `final.source_unchanged` and `final.source_proof`. An unchanged
C source can still use a separately checked Python literal spelling; that does
not claim a missing C AST proof passed. Ordinary generation/configuration errors,
baseline compilation failures, measurement errors and cancellation remain
failures. An individual candidate that fails its admission gate can be rejected
while the earlier validated incumbent remains. Replay does not downgrade a
required accepted-step proof to a capacity stop. Exhausting any budget does not
prove that no better spelling exists.

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

## 7. Preserve attempts and compare recorded measurements

Source search preserves attempted alternatives in its owned external output,
including candidates that were larger, equal in size, rejected by an admission
gate, or left unverified when a budget ended. A size-only measurement does not
establish semantic acceptance. These records retain evidence for reviewing a
failed transformation and for recognizing an alternative that may become useful
under another source or codec context.

Each fresh source search creates `attempts/` beside its detailed `report.json`.
For the envelope command above, the submitted-codec strategy keeps the existing
layout `source-search-run/source-search/source-search/attempts/`. The default
second strategy uses
`source-search-run/source-search-portfolio/source-search/attempts/`. Each contains:

| Artifact | Purpose |
| --- | --- |
| `context.json` | Immutable input, observation contract, tool/compiler and cost-objective context. |
| `objects/<sha256>` | Content-addressed original payload/source and retained candidate source snapshots. |
| `events.jsonl` | Append-only attempt events, derivations, measurements, admission outcomes and limits. |
| `index.json` | Sealed inventory with the hashes needed to check the retained evidence. |
| `comparison.json` | Automatically generated ranking of recorded complete-file measurements. |

Source identity, the round's input source, rendered payload identity and literal
style remain distinct. Two spellings that compile to the same ELF can have
different compressed costs; different Python literal encodings of the same C
source can also have different costs. Recorded failures remain part of the
history even when a later attempt succeeds.

The source snapshot budget is separate from the existing source/payload input
limits and the detailed-report bounds. `max_retained_source_bytes` limits
additional, deduplicated candidate source snapshots; the mandatory original
payload and source use their existing 8 MiB input limits. A value of zero leaves
no additional candidate snapshot budget. When an archive limit prevents retaining
new candidate evidence, search stops optional exploration and keeps its current
verified incumbent. Limits and unfinished work are recorded rather than reported
as evidence that no better candidate exists. Keep the complete owned archive
when preserving an attempt; a hash without the corresponding source or derivation
is insufficient to reconstruct the change.

Compare archives without running any saved command:

```sh
npm exec -- nvcompact compare-attempts \
  /absolute/external/source-search-run/source-search/source-search/attempts \
  /absolute/external/another-run/source-search/source-search/attempts/index.json \
  --output /absolute/external/attempt-comparison.json
```

The command accepts archive directories or `index.json` paths. It verifies
recorded hashes and retained source snapshots, reads at most 16 archives within
a 1 GiB aggregate read bound, and creates a new output file exclusively. An
existing comparison is not overwritten. Source search also generates a
comparison when sealing a completed or failed run, so inspecting one run does
not require this extra command. A crash or evidence-write error can leave an
unsealed directory; this command requires the sealed index and does not invent
the missing outcome. Preserve any partial journal and snapshots for diagnosis.

The comparison groups matching recorded input, compiler/frontend, NVCompact
executable, working directory, observation contract and complete-file cost
contexts. The inspected header, decoder and codec objective belong to that
context, together with the baseline's twice-reproducible native and diagnostic
observations. Mismatched contexts, including another NVCompact build, form
separate groups with no cross-group winner. A failed or incomplete baseline
cannot establish that cross-run context. A library caller using an arbitrary
cost callback without an explicit objective also gets run-local comparison only;
a numeric byte count alone is not a portable measurement contract.
In particular, submitted-codec and portfolio-objective archives form separate
groups even when their input and final payload happen to match.

Rows distinguish `size_relation` (`smaller`, `equal`, `larger`, or `unmeasured`)
from `semantic_status` (`recorded-verified`, `recorded-source-identity`,
`not-checked`, `rejected`, `compile-failed`, or `incomplete`). Being the smallest
measured row does not make it the selected or verified result. A smaller
candidate can still have failed its type, binding, native-output or diagnostic
checks. Admission evidence
and the selected incumbent are reported separately.

`compare-attempts` compares existing receipts. It does not recompress, compile,
execute an engine, import historical source edits, or re-admit a rejected
candidate. A new source search performs fresh bounded generation and checks
under its current input and objective, producing a separate history. Changing
the source, toolchain or codec never transfers an old offset, cost or acceptance
status into that new run. The normal `replay` command continues to reconstruct
only the recorded accepted recipe and enforce its existing exact checks.

## Implementation references

- [Current regression results and observation scope](PR16-RESULTS.ko.md)
- [Ownership, reuse and finite coverage](SEARCH-ARCHITECTURE.ko.md)
- [Shared Clang session and context observation](../src/c_frontend.rs)
- [C spelling candidates and binding verification](../src/csource.rs)
- [Typed condition candidates](../src/cflow.rs)
- [Python bytes adapter](../src/source_payload.rs)
- [Whole-file search and exact source replay](../src/source_search.rs)
- [Lazy spelling subset plan](../src/source_search/plan.rs)
- [Budget, evidence journal and run-local cost memo](../src/source_search/runtime.rs)
- [Attempt archives and recorded-cost comparison](../src/attempts.rs)
- [Complete-file cost ownership and bounded reuse](../src/envelope_cost.rs)
- [Independent envelope source strategies](../src/envelope_source.rs)
- [Fixed and adaptive codec policies](../src/codec.rs)
- [Envelope selection, preserved refinements and final replay](../src/envelope.rs)
- [Owned integration fixtures](../tests/source_search.rs)
