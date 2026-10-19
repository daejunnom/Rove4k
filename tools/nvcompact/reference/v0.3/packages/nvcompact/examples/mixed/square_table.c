#include "kernels.h"

int32_t nv_square_bonus(uint32_t square)
{
    static const int8_t axis[8] = {-7, -5, -3, -1, -1, -3, -5, -7};
    return 8 + (int32_t)axis[square & 7] + (int32_t)axis[square >> 3];
}
