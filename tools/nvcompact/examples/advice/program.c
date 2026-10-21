/* Owned, small diagnostic example; the optimizer never applies this advice. */
#include <stdio.h>

static unsigned long long even_bits(unsigned long long x) {
    return x & 0x5555555555555555ULL;
}
static unsigned long long alternate_bits(unsigned long long x) {
    return x & 6148914691236517205ULL;
}
static int unused_helper(int x) { return x + 1; }

static int inspect(unsigned input) {
    int flag = input & 1;
    int unused_local = 19;
    if (flag == 1) return flag != 1;
    return flag == 0;
}

int main(void) {
    unsigned sum = 0;
    for (unsigned x = 0; x < 16; ++x) {
        sum += inspect(x);
        if (even_bits(x) != alternate_bits(x)) return 1;
    }
    printf("%u\n", sum);
    return sum != 8;
}
