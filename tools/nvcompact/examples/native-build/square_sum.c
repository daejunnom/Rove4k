#include <stdint.h>

uint32_t square(uint32_t value) {
    uint32_t result = 0;
    for (uint32_t i = 0; i < value; ++i) result += value;
    return result;
}
