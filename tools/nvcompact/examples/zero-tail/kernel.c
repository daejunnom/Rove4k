#include <stdint.h>

/* Contract: one process, index < 8192, no concurrent access. */
static volatile unsigned char state[8192] = {17};

uint32_t nv_probe(uint32_t index, uint32_t value)
{
    uint32_t before = state[index];
    state[index] = (unsigned char)value;
    return before;
}
