#ifndef ROVE_MODEL_H
#define ROVE_MODEL_H

#include "../model/frozen.h"
#if ROVE_VARIANT == 3 && ROVE_MODEL
#include "../model/simd.h"
#endif

/* E is a frozen, hand-initialized integer feature model, not a trained model.
 * Decode once before workers start; inference only reads these parameters. */
static int16_t rove_model_weights[ROVE_E_WEIGHT_COUNT];

static inline void rove_model_init(void)
{
    rove_e_weights(rove_model_weights);
}

static inline int rove_model_center(int square)
{
    int file = square & 7, rank = square >> 4;
    return (file < 4 ? file : 7 - file) + (rank < 4 ? rank : 7 - rank);
}

/* board uses 0x88 squares, a1=0, signed P/N/B/R/Q/K=1..6; side is +/-1.
 * Accumulation needs a 32-bit int: with exactly one king per side and arbitrary
 * promoted pieces the canonical conservative bound is 56224 centipawns. */
static inline int rove_model_eval_scalar(const int board[128], int side)
{
    const int16_t *w = rove_model_weights;
    uint8_t pawns[2][10] = {{0}}, bishops[2] = {0};
    int score = 0;
    for (int square = 0; square < 128; ++square) {
        if (square & 136) continue;
        int piece = board[square];
        if (!piece) continue;
        int black = piece < 0, kind = black ? -piece : piece;
        int value = (kind < 6 ? w[kind - 1] : 0)
                  + w[kind + 4] * rove_model_center(square);
        if (kind == 1) {
            ++pawns[black][(square & 7) + 1];
            value += w[11] * ((black ? 7 - (square >> 4) : square >> 4) - 1);
        }
        if (kind == 3) ++bishops[black];
        score += black ? -value : value;
    }
    for (int black = 0; black < 2; ++black) {
        int value = bishops[black] > 1 ? w[14] : 0;
        for (int file = 1; file <= 8; ++file) {
            int n = pawns[black][file];
            if (n) {
                value += w[12] * (n - 1);
                if (!pawns[black][file - 1] && !pawns[black][file + 1])
                    value += w[13] * n;
            }
        }
        score += black ? -value : value;
    }
    score = side * score + w[15];
    return score < -20000 ? -20000 : score > 20000 ? 20000 : score;
}

#if ROVE_VARIANT == 3 && ROVE_MODEL
/* Same canonical E features as the independent scalar polynomial above. */
static inline void rove_model_features(const int board[128], int side, int16_t x[16])
{
    uint8_t pawns[2][10] = {{0}}, bishops[2] = {0};
    for (unsigned i = 0; i < 16; ++i) x[i] = 0;
    for (int square = 0; square < 128; ++square) {
        if (square & 136) continue;
        int piece = board[square];
        if (!piece) continue;
        int black = piece < 0, sign = black ? -1 : 1;
        int kind = black ? -piece : piece;
        if (kind < 6) x[kind - 1] += sign;
        x[kind + 4] += sign * rove_model_center(square);
        if (kind == 1) {
            ++pawns[black][(square & 7) + 1];
            x[11] += sign * ((black ? 7 - (square >> 4) : square >> 4) - 1);
        }
        if (kind == 3) ++bishops[black];
    }
    for (unsigned black = 0; black < 2; ++black) {
        int sign = black ? -1 : 1;
        x[14] += sign * (bishops[black] >= 2);
        for (unsigned file = 1; file <= 8; ++file) {
            int n = pawns[black][file];
            if (n) {
                x[12] += sign * (n - 1);
                if (!pawns[black][file - 1] && !pawns[black][file + 1])
                    x[13] += sign * n;
            }
        }
    }
    x[15] = side;
}
#endif

static inline int rove_model_eval(const int board[128], int side)
{
#if ROVE_VARIANT == 3 && ROVE_MODEL
    int16_t x[16];
    rove_model_features(board, side, x);
    int score = side * rove_e_dot_avx2(x, rove_model_weights);
    return score < -20000 ? -20000 : score > 20000 ? 20000 : score;
#else
    return rove_model_eval_scalar(board, side);
#endif
}

/* Signed piece/capture and promotion kind (0 or N/B/R/Q). This predicts only
 * move priority; it never establishes a search bound. A conservative absolute
 * bound is 24940 = 16*900 + 900 + 12*800 + 2*6 + 4*7. */
static inline int rove_model_order(int piece, int captured, int from, int to, int promotion)
{
    const int16_t *w = rove_model_weights;
    int kind = piece < 0 ? -piece : piece;
    int victim = captured < 0 ? -captured : captured;
    int promoted = promotion < 0 ? -promotion : promotion;
    int score = w[19] * (rove_model_center(to) - rove_model_center(from));
    if (victim)
        score += w[16] * (victim < 6 ? w[victim - 1] : 0)
               + w[17] * (kind < 6 ? w[kind - 1] : 0);
    if (promoted) score += w[18] * (w[promoted - 1] - w[0]);
    if (kind == 1) score += w[20] * ((to >> 4) - (from >> 4)) * (piece < 0 ? -1 : 1);
    return score;
}

#endif
