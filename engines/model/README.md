# Frozen E integer model

`frozen.json` is the human-authored integer parameter source for E. It is explicitly
**untrained**: this change does not prepare a dataset, fit coefficients, quantize a
floating-point model, or establish playing strength. Training and AWS are outside
the current task. The C and Rust E engines consume these exact coefficients for
evaluation and move ordering; ordering values are priorities, never TT bounds.

The model is a small structured linear score with pawn-file and bishop-pair
interactions. It has no hidden activation layer. Its coefficients were chosen by
hand, not produced by inference from training data.

## Feature ABI

Board coordinates are `a1=0`, file and rank in `0..7`. Each evaluation feature is
White minus Black. Material counts use `P,N,B,R,Q`; kings have no material value.
The returned reference score is in centipawns, from White's perspective.

| Index | Feature | Definition |
|---|---|---|
| 0..4 | material | Piece counts for P,N,B,R,Q. |
| 5..10 | center | Sum per P,N,B,R,Q,K of `7-(abs(2*f-7)+abs(2*r-7))/2`. The even numerator makes this exact integer division, and values range 0..6. |
| 11 | pawn advance | Sum of `relative_rank-1`; `relative_rank=r` for White and `7-r` for Black. |
| 12 | doubled pawn excess | Sum of `max(0,pawns_on_file-1)`. |
| 13 | isolated pawns | Each pawn whose side has no pawn on either adjacent file; edge files have one adjacent file. |
| 14 | bishop pair | One if the side has at least two bishops, otherwise zero. |
| 15 | tempo | +1 for White to move, -1 for Black to move. |

Ordering has a separate five-coefficient vector. It uses the evaluation's five
material values as units, independently of the ordering multipliers.

| Index | Feature | Definition |
|---|---|---|
| 16 | victim value | Captured material, including the pawn for en passant; zero on quiet moves. |
| 17 | attacker value if capture | Moving piece material only when a capture takes place. |
| 18 | promotion gain | New piece material minus pawn material; zero without promotion. |
| 19 | center delta | `center(to)-center(from)` for the moving piece. |
| 20 | pawn rank delta | Forward relative-rank change for pawns, zero for other pieces. |

The production engine multiplies the White evaluation by the side-to-move sign
and clamps to its ordinary score band below mate. `reference.py` returns raw
values so accumulation and clipping can be tested separately. Move legality is
the engine's responsibility; the ordering reference covers feature extraction,
including explicitly identified en passant, rather than implementing chess rules.

## Exact representation and regeneration

`codec.py` concatenates 16 evaluation and five ordering signed 16-bit integers,
maps each integer by zigzag (`2*x` for nonnegative, `-2*x-1` for negative), then
stores unsigned LEB128. The fixed model occupies 26 bytes rather than the 42-byte
plain signed-16 table. This is a lossless representation change of the selected
integer model. No coefficient is rounded, pruned, fitted, or changed.

`frozen.h` and `frozen.rs` are small deterministic generated source includes. Each
contains the stream and startup decoder, plus the canonical JSON SHA-256. They
have no file I/O, Python dependency, allocation, or external model lookup in the
engine. C calls `rove_e_weights(int16_t[21])`; Rust calls `model_weights()` once
before workers use the coefficients. The build-time decoder checks canonical
encoding and exact length; the runtime decodes its verified fixed stream.

```sh
python3 engines/model/codec.py generate
python3 engines/model/codec.py check
python3 -m unittest discover -s engines/model -p 'test_*.py'
python3 engines/model/reference.py '4k3/8/8/8/4P3/8/8/4K3 w - - 0 1'
```

The independent scalar polynomial and feature-vector dot product are compared on
hand-computed positions and 1,000 deterministic synthetic boards. The codec round
trips every signed 16-bit coefficient, and rejects truncation, overlong values,
out-of-range coefficients and changed feature ABI. These checks establish exact
representation and arithmetic; product-engine and search tests establish actual
integration separately.

## Accumulator range

Do not assume initial material counts: valid move histories can create promoted
pieces, and diagnostic FEN can contain arbitrary piece multiplicities. The bound
below covers at most 64 occupied squares with exactly one king per side, including
pawns on end ranks for diagnostic inputs. A pawn's absolute contribution is at
most `100+6*3+6*6+12+8=174`; the other non-king bounds are knight 368, bishop 360,
rook 512 and queen 906. At most 62 non-kings therefore contribute `62*906`.
The king-center difference adds at most 18, bishop-pair difference at most 24 and
tempo at most 10. Thus `abs(raw_evaluation)<=56,224`, safely inside signed 32-bit
but outside signed 16-bit and the engine's ordinary score band. The engine must
clip after 32-bit accumulation and before a score can be treated as non-mate.

Ordering's conservative triangle bound is
`16*900+1*900+12*800+2*6+4*7=24,940`. Its accumulator is also signed 32-bit. The
generator recomputes conservative bounds from any replacement integer parameters
and rejects models that may overflow the existing signed-32 arithmetic. A codec
round trip for arbitrary signed-16 parameters does not itself establish that a
replacement model's arithmetic fits; the range check is a separate requirement.

For a concrete overflow regression, 62 White queens plus two kings in
`QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQQQQQQ/QQQkQQQQ/QQQQQQQQ/QQQQQQQQ/KQQQQQQQ w`
produce raw White score 56,014. Product tests must observe the engine's ordinary
score clamp, rather than allowing this raw value to become a mate score.
