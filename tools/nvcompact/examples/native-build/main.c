#include <stdint.h>
#include <stdio.h>

uint32_t square(uint32_t value);

int main(void) {
    unsigned value;
    int parsed;
    while ((parsed = scanf("%u", &value)) == 1) {
        if (value > 255) return 64;
        printf("%u\n", (unsigned)square(value));
    }
    return parsed == EOF ? 0 : 64;
}
