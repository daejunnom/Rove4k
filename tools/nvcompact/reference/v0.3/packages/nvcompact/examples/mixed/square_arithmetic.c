#include "kernels.h"

int32_t nv_square_bonus(uint32_t square)
{
    uint32_t file = square & 7;
    uint32_t rank = square >> 3;
    uint32_t from_file_edge = file < 4 ? file : 7 - file;
    uint32_t from_rank_edge = rank < 4 ? rank : 7 - rank;
    return 2 * (int32_t)(from_file_edge + from_rank_edge) - 6;
}
