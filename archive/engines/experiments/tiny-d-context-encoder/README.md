# Independent fixed-model context encoder

This project-owned Python standard-library encoder implements the inverse of
the independently authored `tiny-d-context/decoder.h` ABI. No external engine,
upstream compressor implementation, binary, package or subprocess is a normal
encoding dependency. Native files are input data; the encoder never executes
them. All reports, fixtures and generated streams remain outside Git.

The production closure is three ordinary files: `encode.py`, `range_bits.py`
and `models.json`. The sibling arithmetic module is loaded by its own absolute
path, including under Python isolated mode. This README and `.gitattributes`
bring the source inventory to five files; no nested engine/control copy exists.

The two fixed21-model profiles use H24, base10, a zero32MiB byte-counter table,
and their declared header order. CRC32C uses reflected polynomial82f63b78 with
raw seed and no initial/final XOR. Each seed contains the high24 bits of the
entire weightmask state after consumption plus the model mask. Probabilities
are all collected before any update; duplicate slots still update once per
model in order, with unsigned-byte wrap and opposite-counter `>1` halving.
History is64bits, actual data bytes are coded MSB first, and a separate initial
coded1 sentinel uses history/prefix zero. No model search is performed.

`range_bits.py` uses explicit32-bit low/range arithmetic and wide product and
endpoint tests. Bit1 selects the lower interval. Delayed carry increments the
already emitted temporal prefix; the deterministic short finish selects a
point inside the final interval. Temporal stream bits are physically stored
LSB first within each byte. This implementation follows an independently
written interval note and the project-owned decoder, without upstream bodies.
Decoder compatibility does not uniquely require another encoder's endpoint;
old stream hashes are comparison evidence, not a pass condition.

The envelope is u32LE(8*N+1), u32LE(weightmask),21mask bytes, arithmetic body,
and four physical zero tail bytes. BCJ covers the entire native file starting
at file offset zero, including ELF headers. E8/E9 operands add offset+5 modulo
2**32 and consume5bytes. The inverse used for the local input check subtracts
that same value. The caller supplies explicit native/model SHA-256 pins.

```sh
encoder='/mnt/c/Users/강민수/Documents/Codex/rove4k-engines-af-20261020/engines/experiments/tiny-d-context-encoder'
python3 -I -B "$encoder/encode.py" \
  --models "$encoder/models.json" \
  --model-sha256 3101a5638551990cb2d5a33d6d28fbab436d04d301b676cc2e45afa63b7f6920 \
  --profile scalar-shipping \
  --native /absolute/frozen/scalar/native \
  --native-sha256 59829299f667cdb6682c5ed4a955fb50b76a5584209caf9e4bddf1c0ee2cd160 \
  --out /absolute/new/scalar.paq
```

Use `hq-shipping` with native SHA
`f1d6558ec5a13e400c2d6df182b01b3236bf1ee1e99f686e47f144a32d222c5c`
for the other fixed image. CLI paths are absolute, inputs are bounded, and a
new output outside Git is required. The normal encoder has no diagnostic or
upstream binary input. API callers can use `load_models(raw, profile)` then
`encode_native(native, model)`; the returned pair is payload bytes and metadata.
`encode_context(data, model)` instead accepts already transformed BCJ bytes.

Three fixed small vectors and both exact native images passed encode followed
by the existing independent C diagnostic. That binary includes the unchanged
decoder header and checks actual decoded BCJ bytes, input RO, guard pages,
output-prefix canary, anonymous zero table and successful unmaps. It was reused
without compilation. Two actual native encodes ran through isolated CLI copies
of only the three ordinary producer files, confirming the source closure.

| Fixed input | Native | Header | Body bits / bytes | Real zero tail | Payload |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scalar | 8092 | 29 | 40005 /5001 | 4 | 5034 |
| HQ | 8480 | 29 | 41709 /5214 | 4 | 5247 |

The new scalar payload SHA-256 is
`1f3d35025cd61edbbcd3d6ca8b0243969b0a52e435fd4763071b4cf4e3e6b00d`;
HQ is `5f03ce47b7039e15fcf85166dee04c1a09b929762d22de4709428159905aa197`.
Both happen to equal the old complete payload bytes. No parameters, source or
termination rule were searched or adjusted to obtain those comparisons.

Whole encoder checks are at
`/home/stemxstudio/rove4k-tiny-d-context-encoder-checks-20261020/results.json`,
SHA-256 `705e720ea01d5eb1f4254c6a8cda646e323d67bf9ffcc4653cb27841bae33b66`.
There were three small API encodes, two isolated CLI encodes and five existing
guarded diagnostic calls. Compiler invocations, engine-image executions and
upstream executions were zero. This is bounded codec evidence, not a new complete
ELF build, normal integration, runtime/strength acceptance or4KiB qualification.

The arithmetic component also passed12fixed probability traces against a
separate unbounded-integer invariant and bit decoder, plus6invalid calls. An
initial fixture wrongly classified a cut-zero probability pair as valid and
stopped in the test's precondition; its failed receipt remains external.
Reclassifying that fixture changed no encoder source. Component receipts are
separate from the five successful whole encoder/independent-decoder checks.
