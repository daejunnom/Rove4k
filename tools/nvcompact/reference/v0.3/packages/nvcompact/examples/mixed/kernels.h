#ifndef NVCOMPACT_KERNELS_H
#define NVCOMPACT_KERNELS_H

#include <stdint.h>

/* All 64 input bits are significant. The result is in [0, 64]. */
uint32_t nv_popcount64(uint64_t bits);

/* square = rank * 8 + file, with file/rank in [0, 7].
 * The caller must supply square in [0, 63]. Result is in [-6, 6].
 * Both functions are pure: no pointers, allocation, state or unwinding. */
int32_t nv_square_bonus(uint32_t square);

/* The wire format never depends on native struct packing or endianness. */
static inline uint32_t nv_load32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline void nv_store32(unsigned char *p, uint32_t value)
{
    unsigned int i;
    for (i = 0; i < 4; ++i)
        p[i] = (unsigned char)(value >> (8 * i));
}

static inline int nv_process(const unsigned char in[16], unsigned char out[8])
{
    uint32_t square = nv_load32(in + 8);
    uint64_t bits = (uint64_t)nv_load32(in)
        | ((uint64_t)nv_load32(in + 4) << 32);
    if (square >= 64 || nv_load32(in + 12) != 0)
        return 2;
    nv_store32(out, nv_popcount64(bits));
    /* Conversion to unsigned is defined modulo 2^32, including negatives. */
    nv_store32(out + 4, (uint32_t)nv_square_bonus(square));
    return 0;
}

#endif
