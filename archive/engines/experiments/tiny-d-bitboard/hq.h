#ifndef TINY_D_BITBOARD_HQ_H
#define TINY_D_BITBOARD_HQ_H
#include <stdint.h>
/* Absolute a1=0 bitboards. kind 2=B, 3=R, 4=Q. Include the first
 * blocker, exclude the source, whether occupancy includes the source or not. */
uint64_t d_sliding(uint64_t, unsigned, unsigned);
#endif
