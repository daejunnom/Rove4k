#include <stdio.h>

/* This fixture has no source, path, token, section or self-file observation. */
static int bias(int flag, int x) {
    if (flag) { return x + 3; } else { return x - 3; }
}
static int sum_to(int n) {
    int acc = 0;
    while (1) {
        if (n == 0) { break; }
        acc = acc + n;
        n -= 1;
    }
    return acc;
}
static int gate(int flag, int x) {
    if (flag) { x = x + 1; }
    return x;
}
static int truth(int n) {
    return n ? 1 : 0;
}
int main(void) {
    for (int n = 0; n < 16; ++n) {
        int flag = n % 2;
        printf("%d %d %d %d\n", bias(flag, n), sum_to(n), gate(flag, n), truth(n));
    }
    return 0;
}
