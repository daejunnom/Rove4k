#include "kernels.h"

uint32_t nv_popcount64(uint64_t bits)
{
    bits -= (bits >> 1) & UINT64_C(0x5555555555555555);
    bits = (bits & UINT64_C(0x3333333333333333))
        + ((bits >> 2) & UINT64_C(0x3333333333333333));
    bits = (bits + (bits >> 4)) & UINT64_C(0x0f0f0f0f0f0f0f0f);
    /* uint64_t multiplication intentionally wraps modulo 2^64. */
    return (uint32_t)((bits * UINT64_C(0x0101010101010101)) >> 56);
}
