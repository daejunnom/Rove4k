/* Development-only actual canonical C scalar/AVX2 parity; not linked into engines. */
#include <stdio.h>
#include <stdint.h>
#define ROVE_VARIANT 3
#define ROVE_MODEL 1
#include "../c/model.h"

static uint64_t random_state = UINT64_C(20261020);
static uint32_t next_random(void)
{
    random_state ^= random_state << 13;
    random_state ^= random_state >> 7;
    random_state ^= random_state << 17;
    return (uint32_t)random_state;
}

int main(void)
{
    if (!__builtin_cpu_supports("avx2")) {
        fputs("AVX2 comparison not run: development CPU has no AVX2\n", stderr);
        return 77;
    }
    rove_model_init();
    for (unsigned iteration = 0; iteration < 10000; ++iteration) {
        int board[128] = {0};
        for (unsigned square = 0; square < 128; ++square) {
            if (square & 136) continue;
            uint32_t r = next_random();
            board[square] = iteration == 0 ? 5 : r % 7 < 2 ? 0 :
                ((r >> 8) & 1 ? 1 : -1) * (int)(1 + r % 5);
        }
        board[0] = 6;
        board[55] = -6;
        for (int side = -1; side <= 1; side += 2) {
            int scalar = rove_model_eval_scalar(board, side);
            int vector = rove_model_eval(board, side);
            if (scalar != vector) {
                fprintf(stderr, "model SIMD mismatch at iteration %u side %d: %d/%d\n",
                        iteration, side, scalar, vector);
                return 1;
            }
            if (iteration == 0 && vector != side * 20000) {
                fputs("dense promoted-material clamp failed\n", stderr);
                return 1;
            }
        }
    }
    puts("model SIMD scalar/AVX2 parity: 10000 boards, both sides, dense clamp pass");
    return 0;
}
