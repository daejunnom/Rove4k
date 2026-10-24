# D completion-latch publication observation

This bounded check runs the exact unmodified scalar/HQ shipping files from the
completion-latch first cost: 7,457/7,707 bytes, with restored native images
8,092/8,480 bytes. It qualifies the changed output reservation at an actual
blocked publication boundary. It does not build a different runtime, alter
target memory/registers or change the kernel execution personality.

`publication.py` authenticates the literal first-cost receipt, both independent
whole/native copies and the existing independent chess oracle. Its ordinary
validator source closure is this script and
`engines/tests/chess_oracle.py`; the cost report and native/whole files are
explicit runtime inputs. They are never inputs to ordinary engine generation.
Reports and generated binaries remain outside Git.

For each form the parent initializes the engine and verifies three startup
TIDs, the own-loader identity, actual restored RX identity and zero RX padding,
RX/RW/guard permissions, nonexecutable stack and descriptors 0/1/2. It fills an
empty blocking stdout pipe with a known bounded filler, then queues a white GO,
`position startpos moves e2e4`, and a black GO.

While the result cannot fit in the full pipe, the read-only `/proc` observer
requires a worker blocked in the real `write(1, ...)` of a bestmove, main
blocked in private futex wait, and the futex word inside the native BSS equal
to **one**. Main's recorded futex expected argument may still be three: it
entered the wait before workers finished, and the reservation is released only
after output. That syscall argument is not misreported as the current word.

The parent drains only its filler. Two ordered results must be independently
legal on the original and replacement roots. The same pending address must
subsequently become zero, startup TIDs must persist, and quit must produce
physical process/group and output EOF settlement without forced cleanup.

The once-only scalar and HQ sessions pass: two actual wrappers, four GO
epochs, both observed pending values one, both futex expected arguments three,
both subsequent pending values zero, and all results legal. The exact runtime
receipt SHA is
`99320b49fefaa20644a1261bbe82fd29984e6d9d674367b2a6a3643a0c5b28bc`.
The immutable cost receipt remains
`628ea7e3eccae0c20ade39997836a838b03e60ed128dc1eadc8a0119fd556bca`,
with its original candidate-execution count zero. The new sessions are recorded
separately rather than backfilled into that earlier cost result.

Example for these preserved first-cost files:

```sh
python3 -I -B engines/experiments/tiny-d-completion-latch-proof/publication.py \
  --cost /absolute/preserved/completion-latch-whole/build.json \
  --out /absolute/new/D-publication
```

This is a publication-fence and physical-image observation. Initial BSS is
already live when inspected, so zero BSS before entry is not claimed. New
startup/partial-clone fault cases, general race freedom, cancellation causal
attribution, strength, scaling and 4KiB eligibility are not established. The
maintained D files are not replaced by this check. Their ordinary-source
promotion and newly bound pre-entry audits remain separate work.
