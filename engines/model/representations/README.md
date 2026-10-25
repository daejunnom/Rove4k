# Exact E storage candidates

Current C production imports the pure `transform_sources` API below. Rust model
formats remain covered by small representation fixtures; the retired Rust
engines are preserved under `archive/engines` at the repository root. The
dual-language `prepare.py`, `measure.py` and `verify.py` campaign commands below
describe historical explicit snapshots. They require their original compatible
builder and source inputs; the current C-only engine builder rejects Rust.
See the [archive replay policy](../../../archive/README.md) before using those
historical commands.

These are explicit representation and code/data candidates for the same frozen,
hand-authored, **untrained** E model. They do not fit, quantize, prune, round or
change any of its 21 evaluation/ordering coefficients. `frozen.json` stays the
canonical parameter source and names the default reference codec. Alternative
generated headers and `representation.json` identify their actual runtime codec
separately rather than labeling scaled bytes as the reference varint format.

| Name | Declared payload | Exact supported parameter domain | Consumer |
|---|---:|---|---|
| `varint` | Current model 26 B | Signed 16-bit coefficients | Reference startup decoder |
| `int16` | 42 B | Signed 16-bit coefficients | Copy immutable table into existing decoded storage |
| `split8` | 26 B | First five signed 16-bit; remaining 16 signed 8-bit | Expand two typed tables into existing storage |
| `scaled8` | 21 B | First five divisible by 10 with signed-byte quotients; remaining signed bytes | Restore exact first-five scale 10 before inference |
| `scaled6` | 17 B | Same signed-byte material quotients; remaining coefficients in `[-32,31]` | Five signed bytes and 16 six-bit ZigZag values, then exact expansion |
| `static16` | 42 B | Signed 16-bit coefficients | Immutable direct table; C mutable storage/decoder and Rust `OnceLock` removed in this explicit candidate |

The current first-five material coefficients `[100,320,330,500,900]` factor
exactly to `[10,32,33,50,90]` with factor 10. The other 16 coefficients range from
-12 to 24. Scaled formats fail if replacement parameters do not satisfy their
declared domain. This is exact integer factorization, not a new score unit: the
expanded values remain the original centipawn coefficients.

Payload counts above describe declared logical storage. They do **not** predict
linked data, decoder size, initialization cost, padding, linker sharing, constant
propagation, compressed-file size or RAM. In particular the 17-byte format may
lose to a 42-byte direct table when its restoration code is included. `static16`
is measured separately from `int16`: keeping the old `OnceLock` and returning an
array of constants would not exercise immutable-data inference.

`generate.py` provides exact encode/decode, generated C/Rust headers, explicit
guarded consumer transforms for `static16`, and parameter/representation identity
metadata. The SIMD interface still reads 16 contiguous initialized `i16` weights.
It never casts compact byte storage into `i16` or changes arithmetic to a
saturating dot product. Expanded formats initialize before worker startup;
immutable tables need no publication step.

`prepare.py` copies source-only inputs from one frozen snapshot, checks that its
reference header matches the canonical model, and writes new candidate trees
outside Git. Every changed source and original hash is recorded. The real C/Rust
working-tree consumers are never modified by these experiments. The static
transform fails on an unrecognized source contract rather than applying an
approximate text rewrite.

The central builder can call the pure API without touching the filesystem:

```python
output, record = transform_sources(
    files, representation="static16", language="c", model=explicit_model_dict
)
```

Input names are engine-relative, values are immutable bytes, and model JSON is an
explicit argument. `varint` validates the canonical header and preserves every
input byte, including line endings. `static16` changes only the selected model
header and its matching consumer. Metadata records the changed source hashes.
Loading/freezing model JSON, validating the E/C+E profile and writing output are
the caller's responsibility.

`measure.py` invokes one explicitly selected frozen central builder for all six
trees. Its initial run uses `--no-smoke`: it records **observed** complete-file
costs with unperformed runtime checks. The selected candidates and baseline still
need real evaluation, ordering, UCI, exit and reproduction checks before adoption.
Do not reuse a mutable builder path across a campaign where another worker is
editing packaging code.

```sh
python3 -m unittest discover -s engines/model/representations -p 'test_*.py'
python3 engines/model/representations/prepare.py \
    --source-root /absolute/frozen/engines --out /absolute/new-candidates
python3 engines/model/representations/measure.py \
    --prepared /absolute/new-candidates/prepared.json \
    --builder /absolute/frozen-recipe/engines/scripts/build.py \
    --out /absolute/new-measurements --rustc /absolute/linux/rustc
python3 engines/model/representations/verify.py \
    --prepared /absolute/new-candidates/prepared.json \
    --formats varint,static16 --out /absolute/new-consumer-checks \
    --rustc /absolute/linux/rustc
```

For historical producer builds whose Rust test modules live outside production
sources, use `verify.py --build /absolute/build.json --fixtures-root
/absolute/frozen/engines/tests/rust` instead of `--prepared`. It verifies actual
producer source hashes, copies production Rust sources and explicitly supplied
fixtures into a separate validation tree, and records both input manifests. Test
fixtures are never added to producer inputs or runtime archives. `--build` accepts
both baseline and selected-format reports together when desired.

The stdlib tests compare exact restored vectors for the selected model and 6,000
random vectors within declared format domains. They check signed boundary values,
lattice/range restrictions, exact lengths and unchanged restored-parameter hashes.
Code generation rejects any replacement model whose evaluation/ordering can exceed
the existing signed-32 arithmetic bound, even if its coefficients fit the codec.
Production acceptance additionally reuses the model's hand-computed fixtures:
start position 10; e4 pawn 132 / Black perspective -112; doubled/isolated pawns 248;
connected pawns 270; bishop pair 694; raw dense promotion board 56,014 / final
clamp 20,000; EP ordering 1502; quiet/capture queen promotion 9602/17504; king
capture 1602. The model's signed-32 bounds remain 56,224 evaluation and 24,940
ordering for every representation.
