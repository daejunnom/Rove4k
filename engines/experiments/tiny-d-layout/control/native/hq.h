#ifndef TINY_D_HQ_H
#define TINY_D_HQ_H
#include <stdint.h>

/* Internal board adapter: valid 0x88 source, kind B/R/Q = 3/4/5.
 * Bitboards use a1=0, h8=63. The first blocker is included, origin excluded.
 * Occupancy may include or omit the source. No allocation or startup tables.
 * D_HQ=0 selects the scalar control; D_HQ=1 selects hyperbola quintessence.
 */
uint64_t d_occupancy(const int8_t [128]);
uint64_t d_sliding(uint64_t, unsigned, unsigned);
#endif
