#include "kernels.h"

uint32_t nv_popcount64(uint64_t bits)
{
    uint32_t count = 0;
    while (bits != 0) {
        bits &= bits - UINT64_C(1);
        ++count;
    }
    return count;
}
